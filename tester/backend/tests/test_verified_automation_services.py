"""Unit tests for Verified Automation Services."""

from datetime import datetime, timedelta, timezone
import json
import os
import shutil
import tempfile
import pytest

from app.services.cloud_preview import CloudPreviewService, cloud_preview_service
from app.services.cross_repo import CrossRepoService, cross_repo_service
from app.services.failure_intel import FailureIntelService, failure_intel_service
from app.services.fix_agent import FixAgent, fix_agent


# ---------------- Fix Agent Tests ---------------- #

def test_fix_agent_path_traversal_protection():
    agent = FixAgent()
    temp_dir = tempfile.mkdtemp()
    try:
        # Attempt to escape working tree
        res = agent.generate_candidate_fix(
            repo_dir=temp_dir,
            file_path="../../etc/passwd",
            line_number=1,
            category="secret",
            description="Leaked credential",
            severity="High",
        )
        assert res["status"] == "UNVALIDATED"
        assert res["validated"] is False
        assert "Path traversal" in res["explanation"] or "Security" in res["explanation"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fix_agent_git_internals_protection():
    agent = FixAgent()
    temp_dir = tempfile.mkdtemp()
    try:
        git_dir = os.path.join(temp_dir, ".git")
        os.makedirs(git_dir, exist_ok=True)
        config_file = os.path.join(git_dir, "config")
        with open(config_file, "w") as f:
            f.write("[core]\n")

        res = agent.generate_candidate_fix(
            repo_dir=temp_dir,
            file_path=".git/config",
            line_number=1,
            category="config",
            description="Git config update",
            severity="Low",
        )
        assert res["status"] == "UNVALIDATED"
        assert res["validated"] is False
        assert ".git" in res["explanation"] or "forbidden" in res["explanation"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fix_agent_remediate_secret_with_syntax_validation():
    agent = FixAgent()
    temp_dir = tempfile.mkdtemp()
    try:
        py_file = os.path.join(temp_dir, "client.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write('def get_client():\n    api_key = "super_secret_token_123"\n    return api_key\n')

        res = agent.generate_candidate_fix(
            repo_dir=temp_dir,
            file_path="client.py",
            line_number=2,
            category="secret",
            description="Hardcoded API key detected",
            severity="Critical",
        )

        assert res["status"] == "VALIDATED"
        assert res["validated"] is True
        assert res["requires_explicit_authorization"] is True
        assert "os.getenv(" in res["diff"]
        assert "import os" in res["diff"]
        assert len(res["validation_errors"]) == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fix_agent_remediate_eval_with_syntax_validation():
    agent = FixAgent()
    temp_dir = tempfile.mkdtemp()
    try:
        py_file = os.path.join(temp_dir, "evaluator.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write('def parse_input(raw):\n    return eval(raw)\n')

        res = agent.generate_candidate_fix(
            repo_dir=temp_dir,
            file_path="evaluator.py",
            line_number=2,
            category="sast",
            description="Unsafe eval injection finding",
            severity="High",
        )

        assert res["status"] == "VALIDATED"
        assert res["validated"] is True
        assert "ast.literal_eval" in res["diff"]
        assert "import ast" in res["diff"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fix_agent_syntax_validation_failure():
    agent = FixAgent()
    broken_code = "def invalid_syntax(\n    return 42\n"
    is_valid, errors = agent.validate_syntax("test.py", broken_code)
    assert is_valid is False
    assert len(errors) > 0
    assert "SyntaxError" in errors[0]


def test_fix_agent_explicit_authorization_enforced():
    agent = FixAgent()
    temp_dir = tempfile.mkdtemp()
    try:
        target_file = os.path.join(temp_dir, "app.py")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write('KEY = "123"\n')

        patch = 'import os\nKEY = os.getenv("KEY", "")\n'

        # Without authorization: must reject mutation
        rejected = agent.apply_patch(
            repo_dir=temp_dir,
            file_path="app.py",
            patch_content=patch,
            user_authorized=False,
        )
        assert rejected["applied"] is False
        assert rejected["status"] == "REJECTED_UNAUTHORIZED"

        # Content must remain unchanged on disk
        with open(target_file, "r", encoding="utf-8") as f:
            assert f.read() == 'KEY = "123"\n'

        # With explicit authorization: succeeds
        authorized = agent.apply_patch(
            repo_dir=temp_dir,
            file_path="app.py",
            patch_content=patch,
            user_authorized=True,
            actor="admin_user",
        )
        assert authorized["applied"] is True
        assert authorized["status"] == "APPLIED"

        with open(target_file, "r", encoding="utf-8") as f:
            assert "os.getenv" in f.read()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------- Cloud Preview Tests ---------------- #

def test_cloud_preview_contract_creation():
    service = CloudPreviewService()
    contract = service.create_isolated_preview_contract(
        repo_id=1,
        repo_name="demo-service",
        commit_sha="a1b2c3d4e5f67890123456789012345678901234",
        user_id=42,
    )

    assert contract["status"] == "READY"
    assert contract["preview_id"].startswith("prev_")
    assert contract["contract"]["max_cpu_cores"] == 1
    assert contract["contract"]["max_memory_mb"] == 512
    assert contract["contract"]["max_runtime_seconds"] == 30
    assert contract["contract"]["max_storage_mb"] == 100
    assert contract["log_sanitization_enabled"] is True
    assert os.path.exists(contract["ephemeral_worktree"])

    # Cleanup preview
    service.cleanup_preview(contract["preview_id"])
    assert not os.path.exists(contract["ephemeral_worktree"])


def test_cloud_preview_execution_and_log_sanitization():
    service = CloudPreviewService()
    contract = service.create_isolated_preview_contract(
        repo_id=2,
        repo_name="demo-logs",
        commit_sha="HEAD",
        user_id=42,
    )
    pid = contract["preview_id"]

    try:
        # Run command that echoes simulated secrets
        res = service.execute_preview_command(
            preview_id=pid,
            command=["python", "-c", "print('Bearer eyJhbGciOiJIUzI1NiJ9.token12345678')"],
        )
        assert res["success"] is True
        assert "eyJhbGciOiJIUzI1NiJ9.token12345678" not in res["stdout"]
        assert "[REDACTED_TOKEN]" in res["stdout"]
    finally:
        service.cleanup_preview(pid)


def test_cloud_preview_expiration_cleanup():
    service = CloudPreviewService()
    contract = service.create_isolated_preview_contract(
        repo_id=3,
        repo_name="expired-preview",
        commit_sha="HEAD",
        user_id=10,
    )
    pid = contract["preview_id"]

    # Artificially expire the session
    service.active_sessions[pid]["expires_at_dt"] = datetime.now(timezone.utc) - timedelta(minutes=1)

    cleaned = service.cleanup_expired()
    assert cleaned == 1
    assert pid not in service.active_sessions


# ---------------- Failure Intelligence Tests ---------------- #

def test_failure_intel_parse_pytest_stack_trace():
    service = FailureIntelService()
    mock_log = (
        "============================= FAILURES =============================\n"
        "___________________ ERROR collecting tests/test_auth.py ____________________\n"
        "ImportError while importing test module 'tests/test_auth.py'.\n"
        "Traceback:\n"
        '  File "backend/app/auth/security.py", line 32, in <module>\n'
        "    from app.config import settings\n"
        "ImportError: cannot import name 'settings' from 'app.config'\n"
        "FAILED tests/test_auth.py::test_login - AssertionError: assert False\n"
        "=========================== short test summary info ===========================\n"
    )

    report = service.analyze_build_or_ci_failure(
        failure_log=mock_log,
        changed_files=["backend/app/auth/security.py"],
    )

    assert report["status"] == "ANALYZED"
    assert report["total_errors_detected"] > 0
    assert len(report["failed_steps"]) > 0
    assert "backend/app/auth/security.py" in report["correlated_changed_files"]

    top_cause = report["ranked_root_causes"][0]
    assert top_cause["file"] == "backend/app/auth/security.py"
    assert top_cause["line"] == 32
    assert top_cause["correlated_with_change"] is True
    assert top_cause["confidence"] > 0.8
    assert len(report["recommended_investigation_order"]) >= 2
    assert "pytest" in report["reproduction_command"]


# ---------------- Cross Repo Radar Tests ---------------- #

def test_cross_repo_detect_version_drifts():
    service = CrossRepoService()
    manifests = {
        "repo-auth": {"pydantic": "2.5.0", "fastapi": "0.104.0"},
        "repo-billing": {"pydantic": "2.8.2", "fastapi": "0.104.0"},
        "repo-gateway": {"pydantic": "2.5.0", "fastapi": "0.111.0"},
    }

    drifts = service.detect_version_drifts(manifests)
    drift_pkgs = {d["package"] for d in drifts}

    assert "pydantic" in drift_pkgs
    assert "fastapi" in drift_pkgs


def test_cross_repo_calculate_blast_radius():
    service = CrossRepoService()
    connected = [
        {"downstream_repo_id": 2, "downstream_repo_name": "billing_service", "dependency_type": "API"},
        {"downstream_repo_id": 3, "downstream_repo_name": "notification_worker", "dependency_type": "API"},
        {"downstream_repo_id": 4, "downstream_repo_name": "frontend_app", "dependency_type": "PACKAGE"},
    ]

    report = service.calculate_change_blast_radius(
        upstream_repo_id=1,
        changed_files=["backend/app/api/routes/users.py", "requirements.txt"],
        diff_content="+ def update_user(): pass",
        connected_repos=connected,
    )

    assert report["blast_radius_level"] == "HIGH"
    assert report["total_affected_count"] == 3
    assert len(report["recommended_actions"]) > 0
