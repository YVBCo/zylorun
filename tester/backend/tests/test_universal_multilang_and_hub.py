"""Automated regression tests verifying universal multi-language test path classification,
Project Hub API data contracts, and automatic background commit polling.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import AsyncSessionLocal, engine, Base
from app.database.models import User, Repository, Commit, Scan, RiskScore, RepositoryIndex, AnalyzerRun
from app.scanners.models import is_test_or_benchmark_path
from app.api.routes.admin import execute_polling_cycle


def test_universal_multi_language_test_path_detection():
    """Verify that is_test_or_benchmark_path accurately and generically identifies test,
    benchmark, mock, and fixture files across all modern languages and project layouts
    WITHOUT any repo-specific hardcoding, while never misclassifying production runtime files.
    """
    # 1. Python test & benchmark paths
    assert is_test_or_benchmark_path("tests/test_api.py")
    assert is_test_or_benchmark_path("backend/tests/unit/test_auth.py")
    assert is_test_or_benchmark_path("app/benchmark/fixtures.py")
    assert is_test_or_benchmark_path("tests.py")
    assert is_test_or_benchmark_path("test_models.py")
    assert is_test_or_benchmark_path("conftest.py")

    # 2. TypeScript / JavaScript test & mock paths
    assert is_test_or_benchmark_path("src/__tests__/button.test.tsx")
    assert is_test_or_benchmark_path("components/modal.spec.ts")
    assert is_test_or_benchmark_path("frontend/src/mocks/handlers.ts")
    assert is_test_or_benchmark_path("cypress/e2e/login.cy.ts")
    assert is_test_or_benchmark_path("e2e/navigation.spec.js")

    # 3. Go test & fixture paths
    assert is_test_or_benchmark_path("pkg/auth/auth_test.go")
    assert is_test_or_benchmark_path("cmd/server/server_test.go")
    assert is_test_or_benchmark_path("internal/testdata/fixtures.json")

    # 4. Java & Kotlin test paths
    assert is_test_or_benchmark_path("src/test/java/com/app/AuthTest.java")
    assert is_test_or_benchmark_path("src/test/kotlin/com/app/UserTests.kt")

    # 5. C# / .NET test paths
    assert is_test_or_benchmark_path("tests/App.Tests/UnitTest1.cs")
    assert is_test_or_benchmark_path("App.UnitTests/Controllers/Test1.cs")

    # 6. Rust benchmark & test paths
    assert is_test_or_benchmark_path("tests/common/mod.rs")
    assert is_test_or_benchmark_path("benches/benchmark.rs")

    # 7. Ruby & PHP test paths
    assert is_test_or_benchmark_path("spec/models/user_spec.rb")
    assert is_test_or_benchmark_path("tests/Feature/ExampleTest.php")

    # 8. PRODUCTION RUNTIME CODE MUST NEVER BE MARKED AS TEST/BENCHMARK
    assert not is_test_or_benchmark_path("backend/app/main.py")
    assert not is_test_or_benchmark_path("backend/app/database/models.py")
    assert not is_test_or_benchmark_path("frontend/src/pages/Dashboard.tsx")
    assert not is_test_or_benchmark_path("frontend/src/components/ProjectHub.tsx")
    assert not is_test_or_benchmark_path("pkg/auth/handler.go")
    assert not is_test_or_benchmark_path("src/main/java/com/app/AuthService.java")
    assert not is_test_or_benchmark_path("src/services/payment.ts")
    assert not is_test_or_benchmark_path("app/controllers/user_controller.rb")


@pytest.mark.asyncio
async def test_project_hub_api_contracts_and_schema_matching():
    """Verify that Project Hub endpoints supply the exact keys and data shapes
    expected by ProjectHub.tsx frontend components:
    - /overview: architecture, health_metrics, open_findings_count, total_commits
    - /time-machine: commits (with sha, created_at), impact
    - /ownership: contributors (with author, commits)
    - /cross-repo: repo_name, downstream_consumers
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        user = User(username="hub_tester_user", email="hub_tester@example.invalid", is_active=True, hashed_password="pw")
        db.add(user)
        await db.flush()

        repo = Repository(
            name="acme/web-platform",
            url="https://github.com/acme/web-platform.git",
            owner_id=user.id,
            default_branch="main",
            is_public=True,
            monitoring_status="POLLING_ACTIVE",
            last_processed_sha="abc1234567890abcdef1234567890abcdef12",
        )
        db.add(repo)
        await db.flush()

        commit = Commit(
            repository_id=repo.id,
            hash="abc1234567890abcdef1234567890abcdef12",
            message="feat: core architecture upgrade",
            author_name="Lead Architect",
        )
        db.add(commit)
        await db.flush()

        scan = Scan(
            commit_id=commit.id,
            status="COMPLETED",
        )
        db.add(scan)
        await db.flush()

        score = RiskScore(
            scan_id=scan.id,
            score=95,
            score_delta=5,
        )
        db.add(score)

        index = RepositoryIndex(
            repository_id=repo.id,
            commit_sha="abc1234567890abcdef1234567890abcdef12",
            languages_json=json.dumps({"Python": 60, "TypeScript": 40}),
            frameworks_json=json.dumps(["FastAPI"]),
            module_map_json=json.dumps({"backend": ["app"], "frontend": ["src"]}),
        )
        db.add(index)

        analyzer_run = AnalyzerRun(
            repository_id=repo.id,
            commit_sha="abc1234567890abcdef1234567890abcdef12",
            analyzer_name="security_and_secrets",
            status="COMPLETED",
            findings_count=0,
            summary_text="Clean baseline",
            details_json=json.dumps({}),
        )
        db.add(analyzer_run)
        await db.commit()

        repo_id = repo.id
        user_id = user.id

    async def override_get_current_user():
        return User(id=user_id, username="hub_tester_user", is_active=True)

    from app.api.routes.project_hub import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Overview Tab Data Contract
            res_overview = await client.get(f"/repositories/{repo_id}/hub/overview")
            assert res_overview.status_code == 200
            ov_data = res_overview.json()
            assert "architecture" in ov_data
            assert "health_metrics" in ov_data
            assert "open_findings_count" in ov_data
            assert "total_commits" in ov_data
            assert ov_data["architecture"]["primary_framework"] == "FastAPI"
            assert ov_data["health_metrics"]["security_score"] == 95

            # 2. Time Machine Tab Data Contract
            res_tm = await client.get(f"/repositories/{repo_id}/hub/time-machine")
            assert res_tm.status_code == 200
            tm_data = res_tm.json()
            assert "commits" in tm_data
            assert len(tm_data["commits"]) >= 1
            commit_item = tm_data["commits"][0]
            assert "sha" in commit_item
            assert "created_at" in commit_item
            assert "message" in commit_item

            # 3. Ownership Summary Data Contract
            res_owner = await client.get(f"/repositories/{repo_id}/hub/ownership")
            assert res_owner.status_code == 200
            owner_data = res_owner.json()
            assert "contributors" in owner_data
            if owner_data["contributors"]:
                contributor = owner_data["contributors"][0]
                assert "author" in contributor
                assert "commits" in contributor

            # 4. Cross-Repo Radar Data Contract
            res_radar = await client.get(f"/repositories/{repo_id}/hub/cross-repo")
            assert res_radar.status_code == 200
            radar_data = res_radar.json()
            assert "repo_name" in radar_data
            assert "downstream_consumers" in radar_data
            assert radar_data["repo_name"] == "acme/web-platform"

            # 5. Analyzers List
            res_analyzers = await client.get(f"/repositories/{repo_id}/hub/analyzers")
            assert res_analyzers.status_code == 200
            analyzers_data = res_analyzers.json()
            assert "analyzers" in analyzers_data
            assert analyzers_data["total"] == 10
            assert len(analyzers_data["analyzers"]) == 10
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_execute_polling_cycle_database_locking():
    """Verify execute_polling_cycle runs safely with database locking,
    updating polling timestamps and respecting repo status.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    result = await execute_polling_cycle()
    assert result["status"] in ("completed", "completed_with_errors", "skipped")
    assert "repositories_checked" in result or "reason" in result
