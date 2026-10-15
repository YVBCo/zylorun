"""Tests for active continuous analyzer execution semantics and database persistence."""

import os
import shutil
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.main import app
from app.database.models import Base, User, Repository, AnalyzerRun


@pytest.fixture
def disposable_repo_dir():
    """Create a temporary git repository for testing analyzers."""
    temp_dir = tempfile.mkdtemp(prefix="test_analyzer_run_")
    import subprocess
    subprocess.run(["git", "init", temp_dir], check=True, capture_output=True)
    subprocess.run(["git", "-C", temp_dir, "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "-C", temp_dir, "config", "user.email", "tester@example.com"], check=True)

    # Create dummy app file
    app_py = os.path.join(temp_dir, "app.py")
    with open(app_py, "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/api/users')\ndef list_users():\n    return []\n")

    subprocess.run(["git", "-C", temp_dir, "add", "."], check=True)
    subprocess.run(["git", "-C", temp_dir, "commit", "-m", "Initial commit"], check=True)

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_analyzer_run_execution_and_persistence(disposable_repo_dir, monkeypatch):
    """Verify POST /analyzers/run actively executes analyzers and saves genuine AnalyzerRun records."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_owner", email="owner@test.com", is_active=True, hashed_password="pw")
        repo = Repository(
            id=42,
            name="test/repo",
            url=disposable_repo_dir,  # points to local git directory
            owner_id=1,
            default_branch="main",
            last_processed_sha="HEAD",
        )
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
            # 1. Trigger All 10 Analyzers
            run_res = await client.post("/repositories/42/hub/analyzers/run", json={"commit_sha": "HEAD"})
            assert run_res.status_code == 200
            run_data = run_res.json()

            assert run_data["overall_status"] in ("COMPLETED", "PARTIAL")
            assert "runs" in run_data or "analyzers" in run_data
            runs = run_data.get("analyzers", [])
            assert len(runs) >= 8  # all executed analyzers returned

            for r in runs:
                assert r["status"] in ("COMPLETED", "PARTIAL", "FAILED")
                assert r["duration_seconds"] >= 0
                assert "summary" in r
                assert "coverage_status" in r

            # 2. Verify rows were persisted in AnalyzerRun database table
            async with TestingSessionLocal() as db:
                db_runs = (
                    await db.execute(
                        select(AnalyzerRun).where(AnalyzerRun.repository_id == 42)
                    )
                ).scalars().all()
                assert len(db_runs) >= 8

                run_names = {r.analyzer_name for r in db_runs}
                assert "repository_dna" in run_names
                assert "security_and_secrets" in run_names

            # 3. Verify GET /analyzers reflects the freshly persisted runs
            get_res = await client.get("/repositories/42/hub/analyzers")
            assert get_res.status_code == 200
            get_data = get_res.json()
            analyzers_list = get_data["analyzers"]
            assert len(analyzers_list) == 10

            dna_entry = next((a for a in analyzers_list if a["name"] == "repository_dna"), None)
            assert dna_entry is not None
            assert dna_entry["status"] == "COMPLETED"
            assert dna_entry["id"] is not None

            # 4. Test selective execution of specific analyzer
            sel_res = await client.post(
                "/repositories/42/hub/analyzers/run",
                json={"analyzers": ["api_contract"], "commit_sha": "HEAD"},
            )
            assert sel_res.status_code == 200
            sel_data = sel_res.json()
            sel_runs = sel_data.get("analyzers", [])
            assert len(sel_runs) == 1
            assert sel_runs[0]["name"] == "api_contract"
    finally:
        app.dependency_overrides.clear()
