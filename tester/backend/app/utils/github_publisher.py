"""GitHub Check Runs and Status Publisher.

Implements GitHub App Checks API publication (Option A) with support
for rich check lifecycle (queued, in_progress, completed), conclusions
(success, failure, neutral), Markdown review summaries, and line annotations.
Provides seamless fallback to the Commit Status API (Option B) if token
permissions do not include checks:write.
"""

import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from app.utils.github import get_canonical_github_url

logger = logging.getLogger(__name__)


def redact_secrets_from_log(msg: str) -> str:
    """Redacts potential tokens and bearer headers from log strings."""
    return re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1[REDACTED]", msg)


async def publish_github_check_start(
    repo_url: str,
    head_sha: str,
    token: Optional[str] = None,
    check_name: str = "GitFlow Security Gate",
) -> Optional[int]:
    """Publishes an initial in-progress Check Run to GitHub."""
    if not token or not repo_url or not head_sha:
        return None

    try:
        _, owner, repo = get_canonical_github_url(repo_url)
    except Exception as e:
        logger.warning(f"Could not parse canonical repository URL for GitHub Checks: {e}")
        return None

    api_url = f"https://api.github.com/repos/{owner}/{repo}/check-runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GitFlow-Security-Gate/1.0",
    }
    payload = {
        "name": check_name,
        "head_sha": head_sha,
        "status": "in_progress",
        "output": {
            "title": "GitFlow Security Gate: Analyzing",
            "summary": "Analyzing pull request diff, scanning changed files, and checking security policies...",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(api_url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                check_id = data.get("id")
                logger.info(f"Created GitHub check run {check_id} for {owner}/{repo}@{head_sha[:8]}")
                return check_id
            elif resp.status_code in (403, 404):
                logger.info(
                    f"Checks API returned {resp.status_code} (checks:write not available on token). "
                    "Will publish via Commit Status API on completion."
                )
                return None
            else:
                logger.warning(f"GitHub Checks API returned unexpected status {resp.status_code}: {resp.text}")
                return None
    except Exception as e:
        logger.warning(redact_secrets_from_log(f"Failed to post check run start to GitHub: {e}"))
        return None


async def publish_github_check_complete(
    repo_url: str,
    head_sha: str,
    token: Optional[str],
    conclusion: str,  # 'success', 'failure', or 'neutral'
    title: str,
    summary_markdown: str,
    details_url: Optional[str] = None,
    annotations: Optional[List[Dict[str, Any]]] = None,
    check_run_id: Optional[int] = None,
    check_name: str = "GitFlow Security Gate",
) -> Dict[str, Any]:
    """Publishes completion to GitHub via Checks API (Option A) or Commit Status (Option B)."""
    if not token or not repo_url or not head_sha:
        return {
            "success": False,
            "method": "none",
            "error": "Missing token, repo_url, or head_sha",
        }

    try:
        _, owner, repo = get_canonical_github_url(repo_url)
    except Exception as e:
        return {"success": False, "method": "none", "error": f"Invalid repo URL: {e}"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GitFlow-Security-Gate/1.0",
    }

    # Format annotations for GitHub Checks API (max 50 per batch)
    formatted_annotations = []
    if annotations:
        for a in annotations[:50]:
            line = a.get("line_number") or a.get("line") or 1
            path = a.get("file_path") or a.get("file") or "app"
            sev = a.get("severity", "High").title()
            level = "failure" if sev in ("Critical", "High") else ("warning" if sev == "Medium" else "notice")
            formatted_annotations.append({
                "path": path,
                "start_line": line,
                "end_line": line,
                "annotation_level": level,
                "message": a.get("message") or a.get("title") or "Security alert",
                "title": f"GitFlow: {a.get('rule_id') or 'Security Finding'}",
            })

    output_payload = {
        "title": title[:255],
        "summary": summary_markdown[:65000],
    }
    if formatted_annotations:
        output_payload["annotations"] = formatted_annotations

    # 1. Attempt Option A: GitHub Checks API
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if check_run_id:
                patch_url = f"https://api.github.com/repos/{owner}/{repo}/check-runs/{check_run_id}"
                patch_payload = {
                    "name": check_name,
                    "status": "completed",
                    "conclusion": conclusion,
                    "details_url": details_url or "https://gitflow-rose-eight.vercel.app/",
                    "output": output_payload,
                }
                resp = await client.patch(patch_url, headers=headers, json=patch_payload)
                if resp.status_code == 200:
                    logger.info(f"Updated check run {check_run_id} to completed ({conclusion})")
                    return {"success": True, "method": "checks_api", "check_run_id": check_run_id}

            # If no check_run_id or update failed, try creating a completed check run
            post_url = f"https://api.github.com/repos/{owner}/{repo}/check-runs"
            post_payload = {
                "name": check_name,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": conclusion,
                "details_url": details_url or "https://gitflow-rose-eight.vercel.app/",
                "output": output_payload,
            }
            resp = await client.post(post_url, headers=headers, json=post_payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                cid = data.get("id")
                logger.info(f"Created completed check run {cid} ({conclusion})")
                return {"success": True, "method": "checks_api", "check_run_id": cid}

            # 2. Fallback to Option B: Commit Status API
            # Checks API not authorized or not supported by token; use Commit Status API
            logger.info("Checks API unavailable for token; publishing via Commit Status API fallback.")
            status_url = f"https://api.github.com/repos/{owner}/{repo}/statuses/{head_sha}"
            status_state = "success" if conclusion in ("success", "neutral") else "failure"
            status_desc = f"{title[:100]} (Status: {conclusion.upper()})"
            status_payload = {
                "state": status_state,
                "target_url": details_url or "https://gitflow-rose-eight.vercel.app/",
                "description": status_desc[:140],
                "context": "gitflow/security-gate",
            }
            status_resp = await client.post(status_url, headers=headers, json=status_payload)
            if status_resp.status_code in (200, 201):
                logger.info(f"Published commit status {status_state} for {owner}/{repo}@{head_sha[:8]}")
                return {"success": True, "method": "status_api", "state": status_state}
            else:
                return {
                    "success": False,
                    "method": "status_api",
                    "error": f"Status API returned HTTP {status_resp.status_code}",
                }
    except Exception as e:
        safe_msg = redact_secrets_from_log(str(e))
        logger.error(f"Error publishing security check result to GitHub: {safe_msg}")
        return {"success": False, "method": "error", "error": safe_msg}
