"""Unit and integration tests for the Pull Request Security Gate."""

import os
import shutil
import tempfile
import unittest
import subprocess

from app.analysis.pr_gate import (
    parse_diff_changed_lines,
    categorize_finding_for_pr,
    evaluate_pr_gate_policy,
    generate_pr_summary_markdown,
    run_pr_security_check,
)
from app.benchmark.corpus import run_cmd


def init_git_repo(target_dir: str):
    run_cmd(["git", "init"], cwd=target_dir)
    run_cmd(["git", "config", "user.email", "benchmark@gitflow.test"], cwd=target_dir)
    run_cmd(["git", "config", "user.name", "GitFlow Benchmark Bot"], cwd=target_dir)


class TestPullRequestSecurityGate(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="gitflow_pr_gate_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_diff_changed_lines(self):
        diff_text = """diff --git a/app/service.py b/app/service.py
index 1234567..89abcdef 100644
--- a/app/service.py
+++ b/app/service.py
@@ -10,0 +11,3 @@
+def new_feature():
+    pass
+    return True
@@ -25,2 +29 @@
-old line 1
-old line 2
+modified line
diff --git a/app/old_name.py b/app/new_name.py
similarity index 100%
rename from app/old_name.py
rename to app/new_name.py
diff --git a/app/deleted.py b/app/deleted.py
deleted file mode 100644
--- a/app/deleted.py
+++ /dev/null
diff --git a/app/added.py b/app/added.py
new file mode 100644
--- /dev/null
+++ b/app/added.py
@@ -0,0 +1,2 @@
+print("hello")
+print("world")
"""
        changed_lines, file_statuses, renames = parse_diff_changed_lines(diff_text)

        self.assertEqual(file_statuses.get("app/service.py"), "MODIFIED")
        self.assertEqual(file_statuses.get("app/new_name.py"), "RENAMED")
        self.assertEqual(file_statuses.get("app/deleted.py"), "DELETED")
        self.assertEqual(file_statuses.get("app/added.py"), "ADDED")

        # Check line ranges
        self.assertEqual(changed_lines.get("app/service.py"), {11, 12, 13, 29})
        self.assertEqual(changed_lines.get("app/added.py"), {1, 2})
        self.assertEqual(renames.get("app/old_name.py"), "app/new_name.py")

    def test_categorize_finding_for_pr(self):
        changed_lines = {
            "app/auth.py": {15, 16, 17},
            "app/utils.py": {5},
        }
        file_statuses = {
            "app/auth.py": "MODIFIED",
            "app/utils.py": "MODIFIED",
            "app/new_feature.py": "ADDED",
        }
        base_fingerprints = {"fp_existing_1"}

        # 1. Actionable finding on a changed line
        finding_actionable = {
            "fingerprint": "fp_actionable_1",
            "file_path": "app/auth.py",
            "line_number": 16,
            "severity": "Critical",
            "classification": "Confirmed vulnerability or exposure",
        }
        cat = categorize_finding_for_pr(finding_actionable, changed_lines, file_statuses, base_fingerprints, True)
        self.assertEqual(cat, "PR_INTRODUCED_ACTIONABLE")

        # 2. Finding on unchanged line in modified file
        finding_unchanged_line = {
            "fingerprint": "fp_unchanged_line",
            "file_path": "app/auth.py",
            "line_number": 50,
            "severity": "High",
            "classification": "Confirmed vulnerability or exposure",
        }
        cat = categorize_finding_for_pr(finding_unchanged_line, changed_lines, file_statuses, base_fingerprints, True)
        self.assertEqual(cat, "EXISTING")

        # 3. Pre-existing finding in baseline (even if on touched file)
        finding_in_base = {
            "fingerprint": "fp_existing_1",
            "file_path": "app/auth.py",
            "line_number": 15,
            "severity": "High",
            "classification": "Confirmed vulnerability or exposure",
        }
        cat = categorize_finding_for_pr(finding_in_base, changed_lines, file_statuses, base_fingerprints, True)
        self.assertEqual(cat, "EXISTING")

        # 4. Finding in a completely untouched file
        finding_untouched = {
            "fingerprint": "fp_untouched",
            "file_path": "app/unrelated.py",
            "line_number": 10,
            "severity": "Critical",
        }
        cat = categorize_finding_for_pr(finding_untouched, changed_lines, file_statuses, base_fingerprints, True)
        self.assertEqual(cat, "EXISTING")

        # 5. Intentional test fixture match (never blocks)
        finding_fixture = {
            "fingerprint": "fp_fixture",
            "file_path": "tests/test_sqli.py",
            "line_number": 12,
            "severity": "High",
            "classification": "Intentional test fixture or demonstration example",
        }
        cat = categorize_finding_for_pr(finding_fixture, {"tests/test_sqli.py": {12}}, {"tests/test_sqli.py": "ADDED"}, set(), True)
        self.assertEqual(cat, "INFORMATIONAL_FIXTURE")

        # 6. Newly added file -> all lines are attributed to PR
        finding_new_file = {
            "fingerprint": "fp_new_file",
            "file_path": "app/new_feature.py",
            "line_number": 100,
            "severity": "High",
            "classification": "Confirmed vulnerability or exposure",
        }
        cat = categorize_finding_for_pr(finding_new_file, changed_lines, file_statuses, base_fingerprints, True)
        self.assertEqual(cat, "PR_INTRODUCED_ACTIONABLE")

    def test_evaluate_pr_gate_policy(self):
        critical_finding = [{"severity": "Critical", "classification": "Confirmed vulnerability or exposure"}]
        high_finding = [{"severity": "High", "classification": "Confirmed vulnerability or exposure"}]
        medium_finding = [{"severity": "Medium", "classification": "Confirmed vulnerability or exposure"}]

        # 1. Enforcement disabled (monitoring mode) -> NEUTRAL
        disabled_policy = {"enabled": False, "block_critical": True, "block_high": True}
        status, reason = evaluate_pr_gate_policy(critical_finding, "COMPLETED", disabled_policy)
        self.assertEqual(status, "NEUTRAL")

        # 2. Enforcement enabled, block critical -> FAILED
        active_policy = {"enabled": True, "block_critical": True, "block_high": True, "block_medium": False, "block_incomplete": True}
        status, reason = evaluate_pr_gate_policy(critical_finding, "COMPLETED", active_policy)
        self.assertEqual(status, "FAILED")
        self.assertIn("Critical", reason)

        # 3. Enforcement enabled, block high -> FAILED
        status, reason = evaluate_pr_gate_policy(high_finding, "COMPLETED", active_policy)
        self.assertEqual(status, "FAILED")
        self.assertIn("High", reason)

        # 4. Medium finding with block_medium=False -> PASSED
        status, reason = evaluate_pr_gate_policy(medium_finding, "COMPLETED", active_policy)
        self.assertEqual(status, "PASSED")

        # 5. Incomplete scanner coverage -> FAILED
        status, reason = evaluate_pr_gate_policy([], "PARTIAL", active_policy)
        self.assertEqual(status, "FAILED")
        self.assertIn("incomplete", reason.lower())

    def test_end_to_end_disposable_repo_pr_security_check(self):
        """Creates a disposable Git repo, commits clean base, introduces SQL injection in a branch,
        and verifies the PR security check identifies newly introduced findings on changed lines."""
        repo_dir = self.test_dir
        init_git_repo(repo_dir)

        # Base commit: Clean code
        with open(os.path.join(repo_dir, "LICENSE"), "w", encoding="utf-8") as f:
            f.write("MIT License\n")
        with open(os.path.join(repo_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("def safe_func():\n    return 42\n")

        run_cmd(["git", "add", "."], cwd=repo_dir)
        run_cmd(["git", "commit", "-m", "Clean baseline"], cwd=repo_dir)
        base_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

        # Head commit: Introduce SQL injection
        with open(os.path.join(repo_dir, "app.py"), "a", encoding="utf-8") as f:
            f.write("def search_user(cursor, username):\n    cursor.execute('SELECT * FROM users WHERE name = ' + username)\n")

        run_cmd(["git", "add", "."], cwd=repo_dir)
        run_cmd(["git", "commit", "-m", "Introduce SQL injection in PR"], cwd=repo_dir)
        head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

        # Check PR security with policy active
        policy = {
            "enabled": True,
            "block_critical": True,
            "block_high": True,
            "block_medium": False,
            "block_incomplete": True,
        }
        res = run_pr_security_check(repo_dir=repo_dir, base_sha=base_sha, head_sha=head_sha, policy=policy)

        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["newly_introduced_actionable_count"], 1)
        self.assertEqual(res["newly_introduced_actionable"][0]["rule_id"], "SEC-SQLI-001")
        self.assertIn("## 🛡️ GitFlow Pull Request Security Gate", res["summary_markdown"])
        self.assertIn("SEC-SQLI-001", res["summary_markdown"])

        # Remediation commit: Fix the SQL injection
        with open(os.path.join(repo_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write("def safe_func():\n    return 42\ndef search_user(cursor, username):\n    cursor.execute('SELECT * FROM users WHERE name = %s', (username,))\n")

        run_cmd(["git", "add", "."], cwd=repo_dir)
        run_cmd(["git", "commit", "-m", "Remediate SQL injection"], cwd=repo_dir)
        fixed_head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

        # Compare head_sha (vulnerable) with fixed_head_sha
        res_fix = run_pr_security_check(repo_dir=repo_dir, base_sha=head_sha, head_sha=fixed_head_sha, policy=policy)
        self.assertEqual(res_fix["status"], "PASSED")
        self.assertEqual(res_fix["newly_introduced_actionable_count"], 0)
        self.assertEqual(res_fix["resolved_count"], 1)
        self.assertEqual(res_fix["resolved_findings"][0]["rule_id"], "SEC-SQLI-001")
        self.assertIn("Resolved Findings", res_fix["summary_markdown"])

    def test_missing_baseline_attributes_only_changed_lines(self):
        """When baseline commit is missing/unreachable, preexisting findings in untouched
        files must NOT be classified as newly introduced."""
        changed_lines = {"app/feature.py": {5, 6}}
        file_statuses = {"app/feature.py": "MODIFIED"}

        preexisting_finding = {
            "fingerprint": "fp_preexisting",
            "file_path": "legacy/old_code.py",
            "line_number": 42,
            "severity": "High",
            "classification": "Confirmed vulnerability or exposure",
        }
        # has_valid_baseline = False
        cat = categorize_finding_for_pr(
            preexisting_finding,
            changed_lines_by_file=changed_lines,
            file_statuses=file_statuses,
            base_fingerprints=set(),
            has_valid_baseline=False
        )
        self.assertEqual(cat, "EXISTING")

        new_finding = {
            "fingerprint": "fp_new",
            "file_path": "app/feature.py",
            "line_number": 5,
            "severity": "High",
            "classification": "Confirmed vulnerability or exposure",
        }
        cat_new = categorize_finding_for_pr(
            new_finding,
            changed_lines_by_file=changed_lines,
            file_statuses=file_statuses,
            base_fingerprints=set(),
            has_valid_baseline=False
        )
        self.assertEqual(cat_new, "PR_INTRODUCED_ACTIONABLE")

    def test_deleted_file_removes_vulnerability_as_resolved(self):
        """When a vulnerable file is deleted in a PR, the vulnerability must be recognized as resolved."""
        repo_dir = self.test_dir
        init_git_repo(repo_dir)

        with open(os.path.join(repo_dir, "LICENSE"), "w", encoding="utf-8") as f:
            f.write("MIT License\n")
        with open(os.path.join(repo_dir, "vuln.py"), "w", encoding="utf-8") as f:
            f.write("def bad(cursor, val):\n    cursor.execute('SELECT * FROM x WHERE y = ' + val)\n")

        run_cmd(["git", "add", "."], cwd=repo_dir)
        run_cmd(["git", "commit", "-m", "Base with vuln"], cwd=repo_dir)
        base_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

        # Delete the vulnerable file in PR
        run_cmd(["git", "rm", "vuln.py"], cwd=repo_dir)
        run_cmd(["git", "commit", "-m", "Delete vuln.py"], cwd=repo_dir)
        head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).stdout.strip()

        policy = {"enabled": True, "block_critical": True, "block_high": True, "block_medium": False, "block_incomplete": True}
        res = run_pr_security_check(repo_dir=repo_dir, base_sha=base_sha, head_sha=head_sha, policy=policy)

        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["newly_introduced_actionable_count"], 0)
        self.assertEqual(res["resolved_count"], 1)
        self.assertEqual(res["resolved_findings"][0]["rule_id"], "SEC-SQLI-001")


# ==============================================================================
# Async Tests: GitHub Publisher, Webhooks & PR Gate Worker Integration
# ==============================================================================

import hmac
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.database.session import AsyncSessionLocal, engine, Base
from app.database.models import User, Repository, PullRequestCheck, WebhookDelivery
from app.utils.github_publisher import (
    publish_github_check_start,
    publish_github_check_complete,
)
from app.workers.pr_gate_job import run_pr_gate_job


def make_github_sig(body: bytes, secret: str) -> str:
    h = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    return "sha256=" + h.hexdigest()


@pytest.mark.asyncio
async def test_github_publisher_checks_api_lifecycle():
    """Verifies Checks API start and complete publication with annotations and markdown."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.patch", new_callable=AsyncMock) as mock_patch:

        # 1. Start check run
        start_resp = MagicMock()
        start_resp.status_code = 201
        start_resp.json.return_value = {"id": 12345}
        mock_post.return_value = start_resp

        cid = await publish_github_check_start(
            repo_url="https://github.com/test-org/test-repo",
            head_sha="abcdef1234567890abcdef1234567890abcdef12",
            token="ghp_test_token_secret",
        )
        assert cid == 12345
        assert mock_post.called
        call_url = str(mock_post.call_args[0][0])
        assert "/repos/test-org/test-repo/check-runs" in call_url

        # 2. Complete check run via PATCH
        patch_resp = MagicMock()
        patch_resp.status_code = 200
        patch_resp.json.return_value = {"id": 12345, "status": "completed"}
        mock_patch.return_value = patch_resp

        res = await publish_github_check_complete(
            repo_url="https://github.com/test-org/test-repo",
            head_sha="abcdef1234567890abcdef1234567890abcdef12",
            token="ghp_test_token_secret",
            conclusion="failure",
            title="GitFlow PR Security Gate: FAILED",
            summary_markdown="## Security Findings Found",
            details_url="https://gitflow-rose-eight.vercel.app/details",
            annotations=[{
                "file_path": "app/auth.py",
                "line_number": 42,
                "severity": "Critical",
                "rule_id": "SEC-SQLI-001",
                "message": "SQL Injection",
            }],
            check_run_id=12345,
        )
        assert res["success"] is True
        assert res["method"] == "checks_api"
        assert res["check_run_id"] == 12345


@pytest.mark.asyncio
async def test_github_publisher_fallback_to_commit_status():
    """Verifies that 403 Forbidden on Checks API falls back to Commit Status API."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call to check-runs returns 403 Forbidden
        checks_resp = MagicMock()
        checks_resp.status_code = 403
        checks_resp.text = "Checks API not authorized for token"

        # Second call to statuses returns 201 Created
        status_resp = MagicMock()
        status_resp.status_code = 201
        status_resp.json.return_value = {"state": "failure"}

        mock_post.side_effect = [checks_resp, status_resp]

        res = await publish_github_check_complete(
            repo_url="https://github.com/test-org/test-repo",
            head_sha="abcdef1234567890abcdef1234567890abcdef12",
            token="ghp_pat_with_no_checks_write",
            conclusion="failure",
            title="GitFlow PR Security Gate: FAILED",
            summary_markdown="## Security Policy Failed",
        )
        assert res["success"] is True
        assert res["method"] == "status_api"
        assert res["state"] == "failure"


@pytest.mark.asyncio
async def test_webhook_delivery_deduplication_and_closed_pr():
    """Verifies x-github-delivery deduplication and graceful handling of closed PRs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings.GITHUB_WEBHOOK_SECRET = "test-webhook-secret"

    async with AsyncSessionLocal() as db:
        user = User(username="wh_user", email="wh@example.com", hashed_password="pw")
        db.add(user)
        await db.flush()
        repo = Repository(name="wh_repo", url="https://github.com/test-org/wh-repo", owner_id=user.id)
        db.add(repo)
        await db.commit()

    with patch("app.api.routes.webhooks.run_pr_gate_job") as mock_gate_job, \
         patch("app.api.routes.webhooks.run_scan") as mock_scan_job:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. PR closed event -> no check queued
            closed_payload = {
                "action": "closed",
                "repository": {"clone_url": "https://github.com/test-org/wh-repo"},
                "pull_request": {"number": 10, "head": {"sha": "head123"}, "base": {"sha": "base123"}},
            }
            body_bytes = json.dumps(closed_payload).encode()
            sig = make_github_sig(body_bytes, settings.GITHUB_WEBHOOK_SECRET)
            headers = {
                "x-hub-signature-256": sig,
                "x-github-event": "pull_request",
                "x-github-delivery": "delivery-closed-1",
                "content-type": "application/json",
            }
            resp = await client.post("/webhooks/github", content=body_bytes, headers=headers)
            assert resp.status_code == 200
            assert resp.json()["message"] == "Pull request closed; no check queued"

            # 2. PR opened event -> queues check
            valid_head_sha = "0123456789abcdef0123456789abcdef01234567"
            valid_base_sha = "abcdef0123456789abcdef0123456789abcdef01"
            opened_payload = {
                "action": "opened",
                "repository": {"clone_url": "https://github.com/test-org/wh-repo"},
                "pull_request": {"number": 11, "head": {"sha": valid_head_sha}, "base": {"sha": valid_base_sha}},
            }
            body_opened = json.dumps(opened_payload).encode()
            sig_opened = make_github_sig(body_opened, settings.GITHUB_WEBHOOK_SECRET)
            headers_opened = {
                "x-hub-signature-256": sig_opened,
                "x-github-event": "pull_request",
                "x-github-delivery": "delivery-opened-uuid-1",
                "content-type": "application/json",
            }
            resp_opened = await client.post("/webhooks/github", content=body_opened, headers=headers_opened)
            assert resp_opened.status_code == 200
            assert resp_opened.json()["message"] == "Pull request security gate queued"
            pr_check_id = resp_opened.json()["pr_check_id"]

            # 3. Duplicate delivery with identical x-github-delivery header
            resp_dup = await client.post("/webhooks/github", content=body_opened, headers=headers_opened)
            assert resp_dup.status_code == 200
            assert resp_dup.json()["message"] == "Duplicate delivery ignored"

            # Verify DB check record was created once
            async with AsyncSessionLocal() as db:
                prc = (await db.execute(PullRequestCheck.__table__.select().where(PullRequestCheck.id == pr_check_id))).first()
                assert prc is not None
                assert prc.head_sha == valid_head_sha
                assert prc.status == "QUEUED"


@pytest.mark.asyncio
async def test_worker_run_pr_gate_job_e2e(tmp_path):
    """Verifies that run_pr_gate_job clones repo, runs analysis, evaluates policy, and updates DB."""
    repo_path = str(tmp_path / "test_repo")
    os.makedirs(repo_path, exist_ok=True)
    init_git_repo(repo_path)

    # Base commit: clean code
    with open(os.path.join(repo_path, "LICENSE"), "w", encoding="utf-8") as f:
        f.write("MIT License\n")
    with open(os.path.join(repo_path, "main.py"), "w", encoding="utf-8") as f:
        f.write("print('clean')\n")
    run_cmd(["git", "add", "."], cwd=repo_path)
    run_cmd(["git", "commit", "-m", "Base commit"], cwd=repo_path)
    base_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path).stdout.strip()

    # Head commit: introduces SQL injection on changed line
    with open(os.path.join(repo_path, "main.py"), "a", encoding="utf-8") as f:
        f.write("def login(cursor, u):\n    cursor.execute('SELECT * FROM u WHERE n = ' + u)\n")
    run_cmd(["git", "add", "."], cwd=repo_path)
    run_cmd(["git", "commit", "-m", "PR commit"], cwd=repo_path)
    head_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path).stdout.strip()

    async with AsyncSessionLocal() as db:
        user = User(username="worker_u", email="worker_u@test.local", hashed_password="pw")
        db.add(user)
        await db.flush()
        repo = Repository(
            name="worker_repo",
            url=repo_path,
            owner_id=user.id,
            is_public=True,
            pr_gate_enabled=True,
            pr_gate_block_critical=True,
            pr_gate_block_high=True,
        )
        db.add(repo)
        await db.flush()

        pr_check = PullRequestCheck(
            repository_id=repo.id,
            pr_number=42,
            base_sha=base_sha,
            head_sha=head_sha,
            status="QUEUED",
        )
        db.add(pr_check)
        await db.commit()
        pr_check_id = pr_check.id

    with patch("app.workers.pr_gate_job.publish_github_check_complete", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = {"success": True, "method": "checks_api", "check_run_id": 999}
        await run_pr_gate_job(pr_check_id)
        assert mock_pub.called
        call_kwargs = mock_pub.call_args[1]
        assert call_kwargs["conclusion"] == "failure"
        assert len(call_kwargs["annotations"]) >= 1

    async with AsyncSessionLocal() as db:
        check = (await db.execute(PullRequestCheck.__table__.select().where(PullRequestCheck.id == pr_check_id))).first()
        assert check.status == "COMPLETED"
        assert check.conclusion == "failure"
        assert check.policy_decision == "FAILED"
        assert check.newly_introduced_count >= 1
        assert "SEC-SQLI-001" in check.summary_markdown
