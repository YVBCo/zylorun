"""Background Worker for Pull Request Security Gate Job.

Clones/fetches the repository, runs base-vs-head diff analysis and policy
evaluation, attributes findings to changed lines, publishes Check Run
lifecycle and line annotations to GitHub, and updates PullRequestCheck records.
"""

from datetime import datetime, timezone
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from sqlalchemy import select

from app.analysis.pr_gate import run_pr_security_check
from app.auth.security import decrypt_token
from app.config import settings
from app.database.models import PullRequestCheck, Repository, User
from app.database.session import AsyncSessionLocal
from app.utils.github import git_environment
from app.utils.github_publisher import (
    publish_github_check_complete,
    redact_secrets_from_log,
)

logger = logging.getLogger(__name__)


async def run_pr_gate_job(pr_check_id: int):
    """Executes PR Security Gate evaluation and publishes results to GitHub."""
    temp_dir: Optional[str] = None
    async with AsyncSessionLocal() as db:
        stmt = select(PullRequestCheck).where(PullRequestCheck.id == pr_check_id)
        pr_check = (await db.execute(stmt)).scalars().first()
        if not pr_check or pr_check.status != "QUEUED":
            return

        pr_check.status = "IN_PROGRESS"
        await db.commit()

        try:
            repo_stmt = select(Repository).where(Repository.id == pr_check.repository_id)
            repo = (await db.execute(repo_stmt)).scalars().first()
            if not repo:
                logger.info("Repository %s no longer exists; aborting PR gate check", pr_check.repository_id)
                return

            user_stmt = select(User).where(User.id == repo.owner_id)
            user = (await db.execute(user_stmt)).scalars().first()
            if not user:
                logger.info("Owner for repo %s no longer exists; aborting PR gate check", repo.id)
                return

            oauth_token = decrypt_token(user.github_access_token or "")
            if not oauth_token and not getattr(repo, "is_public", False):
                raise RuntimeError("GitHub authentication is required to scan this private repository")

            temp_dir = tempfile.mkdtemp(prefix="gitflow_pr_gate_")
            env = git_environment(oauth_token)

            # Clone repository without checkout
            clone_cmd = ["git", "clone", "--no-checkout", repo.url, temp_dir]
            subprocess.run(
                clone_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=settings.SCAN_TIMEOUT_SECONDS,
                env=env,
            )

            # Ensure both base_sha and head_sha are present locally
            for sha in (pr_check.base_sha, pr_check.head_sha):
                if sha:
                    try:
                        subprocess.run(
                            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=temp_dir,
                            capture_output=True,
                            check=True,
                        )
                    except subprocess.CalledProcessError:
                        # Fetch the commit from origin
                        subprocess.run(
                            ["git", "fetch", "origin", sha],
                            cwd=temp_dir,
                            capture_output=True,
                            timeout=30,
                            env=env,
                        )

            # Checkout head_sha
            subprocess.run(
                ["git", "checkout", "--detach", pr_check.head_sha],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                timeout=settings.SCAN_TIMEOUT_SECONDS,
            )

            # Build policy dictionary from repository configuration
            policy = {
                "enabled": repo.pr_gate_enabled,
                "block_critical": repo.pr_gate_block_critical,
                "block_high": repo.pr_gate_block_high,
                "block_medium": repo.pr_gate_block_medium,
                "block_incomplete": repo.pr_gate_block_incomplete,
            }

            # Run PR security check
            check_result = run_pr_security_check(
                repo_dir=temp_dir,
                base_sha=pr_check.base_sha or "",
                head_sha=pr_check.head_sha,
                policy=policy,
            )

            # Map policy status to GitHub check conclusion
            policy_status = check_result["status"]
            if policy_status == "PASSED":
                conclusion = "success"
            elif policy_status == "FAILED":
                conclusion = "failure"
            else:
                conclusion = "neutral"

            details_url = (
                f"https://gitflow-rose-eight.vercel.app/repositories/{repo.id}"
                f"/scans/pr/{pr_check.pr_number or pr_check.head_sha[:8]}"
            )

            # Publish result to GitHub (Checks API Option A or Commit Status API Option B)
            check_run_id_val = None
            if pr_check.github_check_run_id and pr_check.github_check_run_id.isdigit():
                check_run_id_val = int(pr_check.github_check_run_id)

            pub_result = await publish_github_check_complete(
                repo_url=repo.url,
                head_sha=pr_check.head_sha,
                token=oauth_token,
                conclusion=conclusion,
                title=f"GitFlow Security Gate: {policy_status}",
                summary_markdown=check_result["summary_markdown"],
                details_url=details_url,
                annotations=check_result["newly_introduced_actionable"],
                check_run_id=check_run_id_val,
            )

            # Re-verify PR check still exists before persisting
            current_check = (
                await db.execute(
                    select(PullRequestCheck).where(PullRequestCheck.id == pr_check_id)
                )
            ).scalars().first()
            if not current_check:
                logger.info("PR check %s was removed before completion; exiting", pr_check_id)
                return

            if pub_result.get("check_run_id"):
                current_check.github_check_run_id = str(pub_result["check_run_id"])

            current_check.status = "COMPLETED"
            current_check.conclusion = conclusion
            current_check.policy_decision = policy_status
            current_check.coverage_status = check_result["coverage"].get("overall_status", "COMPLETED")
            current_check.newly_introduced_count = check_result["newly_introduced_actionable_count"]
            current_check.resolved_count = check_result["resolved_count"]
            current_check.summary_markdown = check_result["summary_markdown"]
            current_check.details_url = details_url
            current_check.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()

        except Exception as exc:
            err_msg = redact_secrets_from_log(str(exc))
            logger.exception("PR Gate job for check %s failed: %s", pr_check_id, err_msg)
            current_check = (
                await db.execute(
                    select(PullRequestCheck).where(PullRequestCheck.id == pr_check_id)
                )
            ).scalars().first()
            if current_check:
                current_check.status = "FAILED"
                current_check.conclusion = "failure"
                current_check.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                current_check.summary_markdown = f"GitFlow PR Security Gate encountered an execution error:\n\n`{err_msg}`"
                await db.commit()
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
