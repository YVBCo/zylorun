import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.routes.repositories import queue_scan
from app.auth.security import decrypt_token
from app.config import settings
from app.database.models import PullRequestCheck, Repository, User, WebhookDelivery
from app.database.session import get_db
from app.utils.github import get_canonical_github_url
from app.utils.github_publisher import publish_github_check_start
from app.workers.pr_gate_job import run_pr_gate_job
from app.workers.scan_job import run_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(payload_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    if not signature_header:
        return False
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    signature = request.headers.get("x-hub-signature-256")
    body = await request.body()

    if not verify_signature(body, signature, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook payload")

    event_type = request.headers.get("x-github-event")
    delivery_id = request.headers.get("x-github-delivery")

    # 1. Deduplicate by delivery_id if provided by GitHub
    if delivery_id:
        existing_delivery = (
            await db.execute(
                select(WebhookDelivery).where(WebhookDelivery.delivery_id == delivery_id)
            )
        ).scalars().first()
        if existing_delivery:
            logger.info("Ignoring duplicate webhook delivery: %s", delivery_id)
            return {"message": "Duplicate delivery ignored", "delivery_id": delivery_id}

    if event_type == "push":
        repo_url = payload.get("repository", {}).get("clone_url") or payload.get("repository", {}).get("html_url")
        commit_sha = payload.get("after")
        try:
            canonical_url, _, _ = get_canonical_github_url(repo_url)
        except Exception:
            canonical_url = repo_url

        if repo_url and commit_sha:
            result = await db.execute(select(Repository).where(Repository.url == canonical_url))
            repo = result.scalars().first()
            if repo:
                owner = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().first()
                if not owner:
                    raise HTTPException(status_code=404, detail="Repository owner not found")

                if delivery_id:
                    db.add(WebhookDelivery(
                        repository_id=repo.id,
                        event_type="push",
                        delivery_id=delivery_id,
                        status="PROCESSED",
                        payload_sha=commit_sha,
                    ))
                    await db.commit()

                scan, created = await queue_scan(repo.id, commit_sha, owner, db)
                if created:
                    background_tasks.add_task(run_scan, scan.id)
                return {"message": "Scan queued" if created else "Duplicate delivery ignored", "scan_id": scan.id}
            else:
                return {"message": "Repository not tracked"}

    elif event_type == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        repo_url = payload.get("repository", {}).get("clone_url") or payload.get("repository", {}).get("html_url")
        try:
            canonical_url, _, _ = get_canonical_github_url(repo_url)
        except Exception:
            canonical_url = repo_url

        if action == "closed":
            return {"message": "Pull request closed; no check queued", "action": "closed"}

        if action in ("opened", "synchronize", "reopened"):
            base_sha = pr.get("base", {}).get("sha")
            head_sha = pr.get("head", {}).get("sha")
            pr_number = pr.get("number")

            if canonical_url and head_sha:
                result = await db.execute(select(Repository).where(Repository.url == canonical_url))
                repo = result.scalars().first()
                if repo:
                    owner = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().first()
                    if not owner:
                        raise HTTPException(status_code=404, detail="Repository owner not found")

                    # Record delivery
                    if delivery_id:
                        db.add(WebhookDelivery(
                            repository_id=repo.id,
                            event_type="pull_request",
                            delivery_id=delivery_id,
                            status="PROCESSED",
                            payload_sha=head_sha,
                        ))

                    # Create PullRequestCheck record
                    pr_check = PullRequestCheck(
                        repository_id=repo.id,
                        pr_number=pr_number,
                        base_sha=base_sha,
                        head_sha=head_sha,
                        status="QUEUED",
                    )
                    db.add(pr_check)
                    await db.commit()
                    await db.refresh(pr_check)

                    # Queue standard commit scan for repository scan timeline (if valid SHA)
                    scan = None
                    try:
                        scan, created = await queue_scan(repo.id, head_sha, owner, db)
                        if created:
                            background_tasks.add_task(run_scan, scan.id)
                    except HTTPException as e:
                        logger.warning("Could not queue commit scan for %s: %s", head_sha, e.detail)

                    # Publish in-progress status to GitHub Checks API
                    oauth_token = decrypt_token(owner.github_access_token or "")
                    if oauth_token:
                        check_run_id = await publish_github_check_start(
                            repo_url=repo.url,
                            head_sha=head_sha,
                            token=oauth_token,
                        )
                        if check_run_id:
                            pr_check.github_check_run_id = str(check_run_id)
                            await db.commit()

                    # Queue PR Gate evaluation background worker
                    background_tasks.add_task(run_pr_gate_job, pr_check.id)

                    return {
                        "message": "Pull request security gate queued",
                        "pr_check_id": pr_check.id,
                        "scan_id": scan.id if scan else None,
                        "action": action,
                        "pr_number": pr_number,
                        "base_sha": base_sha,
                        "head_sha": head_sha,
                    }
                else:
                    return {"message": "Repository not tracked"}

    return {"message": "Event ignored"}
