"""Tests for Safe Repository Deletion Feature (API, ownership, cascade cleanup, worker safety, webhooks)."""

import json
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.main import app
from app.database.models import (
    Base,
    User,
    Repository,
    Commit,
    Scan,
    Finding,
    RiskScore,
    CommitAnalysis,
    Notification,
    PullRequestCheck,
    WebhookDelivery,
)
from app.workers.scan_job import run_scan
from app.workers.pr_gate_job import run_pr_gate_job
from app.config import settings
import hmac
import hashlib


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


async def setup_test_db_and_users():
    """Sets up an in-memory SQLite database with User 1 and User 2 and dependency overrides."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as db:
        user_1 = User(id=1, username="owner_user", email="owner@test.com", is_active=True, hashed_password="pw")
        user_2 = User(id=2, username="other_user", email="other@test.com", is_active=True, hashed_password="pw")
        db.add_all([user_1, user_2])
        await db.commit()

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    async def override_get_current_user():
        return User(id=1, username="owner_user", is_active=True)

    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return TestingSessionLocal


@pytest.mark.asyncio
async def test_owner_can_delete_repository_with_complete_cascade():
    """Verifies that an owner can delete their repository and all associated child records

    are completely cleaned up, while unrelated repositories and records are preserved.
    """
    SessionLocal = await setup_test_db_and_users()

    async with SessionLocal() as db:
        # User 1's repository and associated records
        repo_1 = Repository(
            id=101,
            name="owner/repo-to-delete",
            url="https://github.com/owner/repo-to-delete",
            owner_id=1,
            monitoring_status="POLLING_ACTIVE",
        )
        db.add(repo_1)
        await db.flush()

        commit_1 = Commit(
            id=201,
            hash="1111111111111111111111111111111111111111",
            repository_id=repo_1.id,
            message="Commit 1",
        )
        db.add(commit_1)
        await db.flush()

        scan_1 = Scan(id=301, commit_id=commit_1.id, status="COMPLETED")
        db.add(scan_1)
        await db.flush()

        db.add_all([
            Finding(scan_id=scan_1.id, fingerprint="fp_1", type="SAST", description="SQLi", severity="High"),
            RiskScore(scan_id=scan_1.id, score=85, score_delta=-5, details="{}"),
            CommitAnalysis(scan_id=scan_1.id, changed_files="[]", impact_analysis="{}"),
            Notification(user_id=1, repository_id=repo_1.id, scan_id=scan_1.id, type="ALERT", title="High Risk", message="Alert"),
            PullRequestCheck(repository_id=repo_1.id, pr_number=1, head_sha="1111111111111111111111111111111111111111", status="COMPLETED"),
            WebhookDelivery(repository_id=repo_1.id, event_type="push", delivery_id="del_1", status="PROCESSED"),
        ])

        # User 2's repository and associated records (should NOT be deleted)
        repo_2 = Repository(
            id=102,
            name="other/unrelated-repo",
            url="https://github.com/other/unrelated-repo",
            owner_id=2,
            monitoring_status="POLLING_ACTIVE",
        )
        db.add(repo_2)
        await db.flush()

        commit_2 = Commit(
            id=202,
            hash="2222222222222222222222222222222222222222",
            repository_id=repo_2.id,
            message="Commit 2",
        )
        db.add(commit_2)
        await db.flush()

        scan_2 = Scan(id=302, commit_id=commit_2.id, status="COMPLETED")
        db.add(scan_2)
        await db.flush()

        db.add_all([
            Finding(scan_id=scan_2.id, fingerprint="fp_2", type="SAST", description="XSS", severity="Medium"),
            RiskScore(scan_id=scan_2.id, score=95, details="{}"),
            Notification(user_id=2, repository_id=repo_2.id, type="ALERT", title="Notice", message="Notice msg"),
        ])

        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/repositories/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Repository removed successfully"
        assert data["id"] == 101
        assert data["name"] == "owner/repo-to-delete"

    # Verify database state
    async with SessionLocal() as db:
        # All repo_1 records must be gone
        assert (await db.execute(select(Repository).where(Repository.id == 101))).scalars().first() is None
        assert (await db.execute(select(Commit).where(Commit.repository_id == 101))).scalars().first() is None
        assert (await db.execute(select(Scan).where(Scan.id == 301))).scalars().first() is None
        assert (await db.execute(select(Finding).where(Finding.scan_id == 301))).scalars().first() is None
        assert (await db.execute(select(RiskScore).where(RiskScore.scan_id == 301))).scalars().first() is None
        assert (await db.execute(select(CommitAnalysis).where(CommitAnalysis.scan_id == 301))).scalars().first() is None
        assert (await db.execute(select(Notification).where(Notification.repository_id == 101))).scalars().first() is None
        assert (await db.execute(select(PullRequestCheck).where(PullRequestCheck.repository_id == 101))).scalars().first() is None
        assert (await db.execute(select(WebhookDelivery).where(WebhookDelivery.repository_id == 101))).scalars().first() is None

        # User 2's records must remain completely intact
        repo_2_check = (await db.execute(select(Repository).where(Repository.id == 102))).scalars().first()
        assert repo_2_check is not None
        assert repo_2_check.name == "other/unrelated-repo"
        assert (await db.execute(select(Commit).where(Commit.repository_id == 102))).scalars().first() is not None
        assert (await db.execute(select(Scan).where(Scan.id == 302))).scalars().first() is not None
        assert (await db.execute(select(Finding).where(Finding.scan_id == 302))).scalars().first() is not None
        assert (await db.execute(select(RiskScore).where(RiskScore.scan_id == 302))).scalars().first() is not None
        assert (await db.execute(select(Notification).where(Notification.repository_id == 102))).scalars().first() is not None


@pytest.mark.asyncio
async def test_user_cannot_delete_another_users_repository():
    """Verifies that a user gets 404 when attempting to delete a repository owned by someone else."""
    SessionLocal = await setup_test_db_and_users()

    async with SessionLocal() as db:
        repo_2 = Repository(
            id=102,
            name="other/unrelated-repo",
            url="https://github.com/other/unrelated-repo",
            owner_id=2,
        )
        db.add(repo_2)
        await db.commit()

    # User 1 attempts to delete User 2's repo (ID 102)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/repositories/102")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Repository not found"

    # Verify repository still exists in database
    async with SessionLocal() as db:
        repo_check = (await db.execute(select(Repository).where(Repository.id == 102))).scalars().first()
        assert repo_check is not None


@pytest.mark.asyncio
async def test_delete_missing_repository_returns_404():
    """Verifies that deleting a non-existent repository ID returns 404."""
    await setup_test_db_and_users()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/repositories/999999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Repository not found"


@pytest.mark.asyncio
async def test_unauthenticated_delete_returns_401():
    """Verifies that unauthenticated DELETE requests return 401 Unauthorized."""
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/repositories/101")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_running_scan_job_exits_gracefully_when_repo_deleted():
    """Verifies that if a scan worker runs for a repository that was deleted, it exits cleanly without errors."""
    SessionLocal = await setup_test_db_and_users()

    # Create and then delete repository & commit, leaving an orphan scan ID to test worker guard
    async with SessionLocal() as db:
        repo = Repository(id=105, name="temp/deleted", url="https://github.com/temp/deleted", owner_id=1)
        db.add(repo)
        await db.flush()
        commit = Commit(id=205, hash="3333333333333333333333333333333333333333", repository_id=repo.id)
        db.add(commit)
        await db.flush()
        scan = Scan(id=305, commit_id=commit.id, status="QUEUED")
        db.add(scan)
        await db.commit()

        # Simulate deletion before worker picks up the job
        await db.delete(scan)
        await db.delete(commit)
        await db.delete(repo)
        await db.commit()

    # Run scan worker: should return cleanly without raising unhandled exception
    with patch("app.workers.scan_job.AsyncSessionLocal", SessionLocal):
        await run_scan(305)


@pytest.mark.asyncio
async def test_pr_gate_worker_exits_gracefully_when_repo_deleted():
    """Verifies that if a PR gate worker runs for a repository that was deleted, it exits cleanly without errors."""
    SessionLocal = await setup_test_db_and_users()

    async with SessionLocal() as db:
        pr_check = PullRequestCheck(id=501, repository_id=9999, head_sha="4444444444444444444444444444444444444444", status="QUEUED")
        db.add(pr_check)
        await db.commit()

    # Run PR gate job: repository 9999 does not exist
    with patch("app.workers.pr_gate_job.AsyncSessionLocal", SessionLocal):
        await run_pr_gate_job(501)


@pytest.mark.asyncio
async def test_subsequent_webhook_for_deleted_repo_does_not_recreate_it():
    """Verifies that once a repository is deleted, subsequent push and pull_request webhooks

    return 'Repository not tracked' and do NOT recreate the repository in GitFlow.
    """
    SessionLocal = await setup_test_db_and_users()
    settings.GITHUB_WEBHOOK_SECRET = "test-secret"

    def make_sig(body: bytes) -> str:
        h = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256)
        return "sha256=" + h.hexdigest()

    deleted_repo_url = "https://github.com/owner/previously-deleted-repo"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Push webhook for deleted repo
        push_body = json.dumps({
            "after": "5555555555555555555555555555555555555555",
            "repository": {"clone_url": deleted_repo_url},
        }).encode()
        headers = {
            "x-hub-signature-256": make_sig(push_body),
            "x-github-event": "push",
            "content-type": "application/json",
        }
        res_push = await client.post("/webhooks/github", content=push_body, headers=headers)
        assert res_push.status_code == 200
        assert res_push.json()["message"] == "Repository not tracked"

        # 2. Pull request webhook for deleted repo
        pr_body = json.dumps({
            "action": "opened",
            "repository": {"clone_url": deleted_repo_url},
            "pull_request": {
                "number": 1,
                "head": {"sha": "5555555555555555555555555555555555555555"},
                "base": {"sha": "6666666666666666666666666666666666666666"},
            },
        }).encode()
        headers_pr = {
            "x-hub-signature-256": make_sig(pr_body),
            "x-github-event": "pull_request",
            "content-type": "application/json",
        }
        res_pr = await client.post("/webhooks/github", content=pr_body, headers=headers_pr)
        assert res_pr.status_code == 200
        assert res_pr.json()["message"] == "Repository not tracked"

    # Verify repository was NOT recreated in DB
    async with SessionLocal() as db:
        repo_check = (await db.execute(select(Repository).where(Repository.url == deleted_repo_url))).scalars().first()
        assert repo_check is None
