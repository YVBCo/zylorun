"""Tests for truthful AI status telemetry and diagnostic connection probe endpoints."""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.models import Base, User, Repository
from app.ai.provider import MockProvider, DisabledProvider
from app.ai.service import ai_service


@pytest.fixture(autouse=True)
def reset_ai_service():
    """Ensure AI service provider is reset after each test."""
    original = ai_service._custom_provider
    yield
    ai_service.set_provider(original)


@pytest.mark.asyncio
async def test_ai_status_endpoint_deterministic_mode(monkeypatch):
    """When no AI keys are configured, endpoint reports deterministic fallback mode without leaks."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MOCK_AI", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    ai_service.set_provider(None)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_owner", email="owner@test.com", is_active=True, hashed_password="pw")
        repo = Repository(id=1, name="test/repo", url="https://github.com/test/repo.git", owner_id=1, default_branch="main")
        db.add_all([user, repo])
        await db.commit()

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    async def override_get_current_user():
        return User(id=1, username="test_owner", is_active=True)

    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/repositories/1/hub/ai/status")
            assert res.status_code == 200
            data = res.json()

            # Verify required fields
            assert data["configured"] is False
            assert data["active_provider"] == "none"
            assert data["active_model"] == "none"
            assert data["key_present"] is False
            assert data["redaction_active"] is True
            assert isinstance(data["cache_size"], int)
            assert data["execution_mode"] == "deterministic_fallback"
            assert "deterministic" in data["status_message"].lower()

            # Verify connection test in fallback mode
            probe_res = await client.post("/repositories/1/hub/ai/test-connection")
            assert probe_res.status_code == 200
            probe_data = probe_res.json()
            assert probe_data["success"] is False
            assert "deterministic fallback mode" in probe_data["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_status_endpoint_mock_mode():
    """When MockProvider is configured, status and test connection report healthy diagnostic probe."""
    mock_p = MockProvider(default_response="Mock probe response")
    ai_service.set_provider(mock_p)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_owner", email="owner@test.com", is_active=True, hashed_password="pw")
        repo = Repository(id=1, name="test/repo", url="https://github.com/test/repo.git", owner_id=1, default_branch="main")
        db.add_all([user, repo])
        await db.commit()

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    async def override_get_current_user():
        return User(id=1, username="test_owner", is_active=True)

    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/repositories/1/hub/ai/status")
            assert res.status_code == 200
            data = res.json()

            assert data["configured"] is True
            assert data["active_provider"] == "mock"
            assert data["execution_mode"] == "mock_provider"
            assert data["redaction_active"] is True

            # Connection test in mock mode
            probe_res = await client.post("/repositories/1/hub/ai/test-connection")
            assert probe_res.status_code == 200
            probe_data = probe_res.json()
            assert probe_data["success"] is True
            assert probe_data["provider"] == "mock"
            assert probe_data["latency_ms"] >= 0
            assert "verified successfully" in probe_data["message"]
    finally:
        app.dependency_overrides.clear()
