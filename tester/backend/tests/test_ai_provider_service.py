"""Unit tests for Centralized AI Provider and Service."""

import os
from unittest.mock import AsyncMock, patch
import pytest

from app.ai.provider import (
    AnthropicProvider,
    DisabledProvider,
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
)
from app.ai.service import (
    AIService,
    RevisionLRUCache,
    ai_service,
    redact_secrets,
)


@pytest.mark.asyncio
async def test_disabled_provider():
    provider = DisabledProvider("No key provided")
    result = await provider.generate_completion(prompt="Hello")
    assert result["ai_available"] is False
    assert result["text"] == ""
    assert result["model"] == "disabled"
    assert "No key provided" in result["error"]


@pytest.mark.asyncio
async def test_mock_provider():
    canned = {"architecture": "Repository follows modular FastAPI architecture."}
    provider = MockProvider(canned_responses=canned)
    res = await provider.generate_completion(prompt="Explain the architecture of this repo")

    assert res["ai_available"] is True
    assert res["provider"] == "mock"
    assert "modular FastAPI architecture" in res["text"]
    assert res["usage"]["total_tokens"] > 0
    assert len(provider.calls) == 1
    assert provider.calls[0]["prompt"] == "Explain the architecture of this repo"


@pytest.mark.asyncio
async def test_openai_provider_fallback_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(api_key="")
    res = await provider.generate_completion(prompt="Test prompt")
    assert res["ai_available"] is False
    assert "OPENAI_API_KEY is not configured" in res["error"]


@pytest.mark.asyncio
async def test_anthropic_provider_fallback_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key="")
    res = await provider.generate_completion(prompt="Test prompt")
    assert res["ai_available"] is False
    assert "ANTHROPIC_API_KEY is not configured" in res["error"]


@pytest.mark.asyncio
async def test_gemini_provider_fallback_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(api_key="")
    res = await provider.generate_completion(prompt="Test prompt")
    assert res["ai_available"] is False
    assert "GEMINI_API_KEY is not configured" in res["error"]


def test_secret_redaction():
    raw_text = (
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token123\n"
        "AWS credentials: AKIAIOSFODNN7EXAMPLE and aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
        "GitHub token: ghp_123456789012345678901234567890123456\n"
        "Database: postgres://user:SuperSecretPassword123@localhost:5432/mydb\n"
        "Config: api_key = 'sample_api_secret_key_abcdef' and password: 'MyPassword!'"
    )
    redacted = redact_secrets(raw_text)

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token123" not in redacted
    assert "[REDACTED" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted
    assert "ghp_123456789012345678901234567890123456" not in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "SuperSecretPassword123" not in redacted
    assert "sample_api_secret_key_abcdef" not in redacted
    assert "MyPassword!" not in redacted


def test_revision_lru_cache():
    cache = RevisionLRUCache(capacity=2)
    cache.set("repoA", "c1", "query1", {"answer": "ans1"})
    cache.set("repoA", "c1", "query2", {"answer": "ans2"})

    assert cache.get("repoA", "c1", "query1")["answer"] == "ans1"

    # Add 3rd item to evict oldest (query2 should be evicted since query1 was touched)
    cache.set("repoA", "c1", "query3", {"answer": "ans3"})
    assert cache.get("repoA", "c1", "query2") is None
    assert cache.get("repoA", "c1", "query1") is not None
    assert cache.get("repoA", "c1", "query3") is not None

    # Invalidate revision
    removed = cache.invalidate_revision("repoA", "c1")
    assert removed == 2
    assert cache.get("repoA", "c1", "query1") is None


@pytest.mark.asyncio
async def test_ai_service_disabled_fallback():
    service = AIService()
    # Force disabled provider
    service.set_provider(DisabledProvider())

    context = {
        "languages": {"Python": 100},
        "frameworks": ["FastAPI", "SQLAlchemy"],
        "routes": [{"path": "/api/users", "method": "GET", "function_name": "list_users"}],
        "models": [{"name": "User", "table_name": "users"}],
    }

    res = await service.ask(
        question="How do users authenticate and what are the user models?",
        repo_name="demo-repo",
        context=context,
        ai_enabled=True,
    )

    assert res["ai_available"] is False
    assert res["provider"] == "deterministic_fallback"
    assert "FastAPI" in res["answer"]
    assert "User" in res["answer"]


@pytest.mark.asyncio
async def test_ai_service_ask_with_mock_and_caching():
    service = AIService()
    mock_prov = MockProvider(default_response="Mocked architecture analysis.")
    service.set_provider(mock_prov)

    context = {"routes": [], "models": []}

    # First call - not cached
    res1 = await service.ask(
        question="What is the design?",
        repo_name="my-repo",
        context=context,
        ai_enabled=True,
    )
    assert res1["ai_available"] is True
    assert res1["cached"] is False
    assert res1["answer"] == "Mocked architecture analysis."
    assert len(mock_prov.calls) == 1

    # Second call - should hit LRU cache
    res2 = await service.ask(
        question="What is the design?",
        repo_name="my-repo",
        context=context,
        ai_enabled=True,
    )
    assert res2["cached"] is True
    assert res2["answer"] == "Mocked architecture analysis."
    assert len(mock_prov.calls) == 1  # No additional provider call!


@pytest.mark.asyncio
async def test_ai_service_answer_repository_question():
    service = AIService()
    service.set_provider(MockProvider(default_response="Repository analysis confirmed."))

    index_data = {
        "languages": {"Python": 100},
        "frameworks": ["FastAPI"],
        "routes": [{"path": "/repositories/{id}/scan", "method": "POST", "function_name": "trigger_scan"}],
        "models": [{"name": "Repository", "table_name": "repositories"}],
    }
    memories = [{"title": "ADR 001", "content": "Use asyncpg for all PostgreSQL connections"}]

    res = await service.answer_repository_question(
        question="How does scan trigger for repository?",
        repo_name="gitflow-hub",
        index_data=index_data,
        memories=memories,
        commit_sha="abcd123",
        ai_enabled=True,
    )

    assert res["ai_available"] is True
    assert res["answer"] == "Repository analysis confirmed."
    assert any("route:" in c for c in res["citations"]) or any("model:" in c for c in res["citations"])
