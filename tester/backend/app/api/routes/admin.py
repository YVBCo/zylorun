import asyncio
import hmac
import subprocess
import logging
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select, text, func, desc, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.database.session import AsyncSessionLocal, get_db
from app.database.models import Repository, Scan, Commit, User, VisitorLog, SystemErrorLog
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url, git_environment
from app.auth.security import decrypt_token
from app.auth.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def verify_cron_secret(request: Request) -> None:
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=503, detail="Cron secret not configured")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, settings.CRON_SECRET):
        raise HTTPException(status_code=401, detail="Invalid cron secret")

# ---------------------------------------------------------------------------
# Database-level concurrency lock
# ---------------------------------------------------------------------------

async def acquire_poll_lock(db) -> bool:
    """Acquire a robust database lock. Fails safely on DB error."""
    try:
        is_pg = db.bind.dialect.name == "postgresql"
        if is_pg:
            # Native PostgreSQL advisory lock (session-level)
            res = await db.execute(text("SELECT pg_try_advisory_lock(13371337)"))
            return bool(res.scalar())
        else:
            # Atomic row-based lease for SQLite
            await db.execute(text("CREATE TABLE IF NOT EXISTS polling_lock (id INTEGER PRIMARY KEY, locked_at TEXT)"))
            await db.execute(text("INSERT OR IGNORE INTO polling_lock (id, locked_at) VALUES (1, NULL)"))
            await db.commit()
            
            now_str = datetime.now(timezone.utc).isoformat()
            stale_seconds = settings.MAX_POLLING_RUNTIME_SECONDS + 60
            stale_time = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).isoformat()
            
            res = await db.execute(text(
                "UPDATE polling_lock SET locked_at = :now WHERE id = 1 AND (locked_at IS NULL OR locked_at < :stale)"
            ), {"now": now_str, "stale": stale_time})
            await db.commit()
            return res.rowcount > 0
    except Exception as e:
        logger.exception("Polling lock acquisition failed")
        raise HTTPException(
            status_code=503,
            detail="Polling is unavailable because its database lock could not be acquired",
        ) from e

async def release_poll_lock(db):
    try:
        is_pg = db.bind.dialect.name == "postgresql"
        if is_pg:
            await db.execute(text("SELECT pg_advisory_unlock(13371337)"))
        else:
            await db.execute(text("UPDATE polling_lock SET locked_at = NULL WHERE id = 1"))
            await db.commit()
    except Exception as e:
        logger.error("Lock release failed: %s", e)

# ---------------------------------------------------------------------------
# Core Monitoring Logic
# ---------------------------------------------------------------------------

def resolve_remote_head(url: str, oauth_token: str | None = None) -> tuple[str, str | None] | None:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--symref", url, "HEAD"],
            capture_output=True, text=True, timeout=15,
            env=git_environment(oauth_token)
        )
        if result.returncode == 0 and result.stdout.strip():
            sha = None
            branch = None
            for line in result.stdout.splitlines():
                value, _, ref = line.partition("\t")
                if ref == "HEAD" and value.startswith("ref: refs/heads/"):
                    branch = value.removeprefix("ref: refs/heads/")
                elif ref == "HEAD" and len(value) == 40:
                    sha = value.lower()
            if sha:
                return sha, branch
    except Exception as e:
        logger.warning("git ls-remote failed for %s: %s", url, e)
    return None

async def fetch_missing_commits(
    owner: str, repo_name: str, default_branch: str, last_processed_sha: str | None, max_commits: int, bare_repo_dir: str,
    oauth_token: str | None = None,
) -> dict:
    import asyncio

    url = f"https://github.com/{owner}/{repo_name}.git"
    env = git_environment(oauth_token)

    async def run_git(*args: str) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            "git", *args, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=settings.SCAN_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise TimeoutError("Git repository update timed out")
        return proc.returncode, stdout, stderr

    # Fetch only the monitored branch and omit file contents until a scan needs them.
    clone_args = ("clone", "--bare", "--filter=blob:none", "--single-branch", "--branch", default_branch, url, bare_repo_dir)
    return_code, _, _ = await run_git(*clone_args)
    if return_code != 0:
        return {"status": "api_error", "commits": []}

    if not last_processed_sha:
        # First run: get just the latest commit
        log_cmd = ["git", "-C", bare_repo_dir, "log", default_branch, "-n", "1", "--format=%H|%s"]
    else:
        # Check if anchor exists
        return_code, _, _ = await run_git("-C", bare_repo_dir, "cat-file", "-e", f"{last_processed_sha}^{{commit}}")
        if return_code != 0:
            return {"status": "anchor_not_found", "commits": []}
            
        # Get commits between anchor and HEAD
        log_cmd = ["git", "-C", bare_repo_dir, "log", f"{last_processed_sha}..{default_branch}", "--format=%H|%s"]

    return_code, stdout, _ = await run_git(*log_cmd[1:])
    if return_code != 0:
        return {"status": "api_error", "commits": []}

    commits = []
    lines = stdout.decode('utf-8').strip().split('\n')
    for line in lines:
        if not line: continue
        parts = line.split('|', 1)
        if len(parts) == 2:
            commits.append({"sha": parts[0], "message": parts[1]})

    if last_processed_sha:
        # log outputs newest first, so we reverse it to get chronological order (oldest to newest)
        commits.reverse()
        commits = commits[:max_commits]

    return {"status": "success", "commits": commits}

async def process_one_repository(repo_id: int, semaphore: asyncio.Semaphore, deadline: float) -> dict:
    result = {"repo_id": repo_id, "changed": False, "commits_discovered": 0, "commits_queued": 0, "error": None, "partial": False}

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.id == repo_id))).scalars().first()
        if not repo or repo.monitoring_status not in {"POLLING_ACTIVE", "ERROR"}:
            return result
        if repo.monitoring_status == "ERROR":
            if (repo.last_poll_error or "").startswith("ANCHOR_NOT_FOUND:"):
                return result
            repo.monitoring_status = "POLLING_ACTIVE"
            repo.last_poll_error = None
            await db.commit()

        now = datetime.now(timezone.utc)
        import tempfile
        import shutil
        bare_repo_dir = tempfile.mkdtemp(prefix="gitflow_shared_bare_")
        try:
            canonical_url, owner, repo_name = get_canonical_github_url(repo.url)
            branch = repo.default_branch or "main"

            user = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().first()
            oauth_token = decrypt_token(user.github_access_token or "") if user else ""
            remote_state = await asyncio.to_thread(resolve_remote_head, f"{canonical_url}.git", oauth_token)
            if not remote_state and oauth_token:
                # Public repositories remain monitorable if a user's GitHub token expires.
                remote_state = await asyncio.to_thread(resolve_remote_head, f"{canonical_url}.git")
                if remote_state:
                    repo.is_public = True
                oauth_token = ""
            if not remote_state:
                if not oauth_token and not repo.is_public:
                    repo.last_poll_error = "GitHub authentication required for this private repository"
                    repo.last_polled_at = now
                    await db.commit()
                    result["error"] = repo.last_poll_error
                    return result
                repo.last_poll_error = "git ls-remote failed"
                repo.last_polled_at = now
                await db.commit()
                result["error"] = "git ls-remote failed"
                return result

            remote_head, remote_branch = remote_state
            if remote_branch:
                branch = remote_branch
                repo.default_branch = remote_branch

            repo.last_seen_sha = remote_head
            repo.last_polled_at = now

            last_processed_sha = repo.last_processed_sha
            if not last_processed_sha:
                last_successful_scan = (await db.execute(
                    select(Scan).join(Commit)
                    .where(Commit.repository_id == repo.id, Scan.status == "COMPLETED")
                    .order_by(Scan.created_at.desc()).limit(1)
                )).scalars().first()
                if last_successful_scan:
                    last_commit = (await db.execute(select(Commit).where(Commit.id == last_successful_scan.commit_id))).scalars().first()
                    if last_commit:
                        last_processed_sha = last_commit.hash
                        repo.last_processed_sha = last_processed_sha

            if remote_head == last_processed_sha:
                repo.last_poll_error = None
                repo.last_successful_poll_at = now
                await db.commit()
                return result

            result["changed"] = True
            fetch_result = await fetch_missing_commits(owner, repo_name, branch, last_processed_sha, settings.MAX_COMMITS_PER_POLL, bare_repo_dir, oauth_token)
            
            if fetch_result["status"] in ("rate_limited", "api_error"):
                repo.last_poll_error = "Git could not fetch repository history"
                await db.commit()
                result["error"] = fetch_result["status"]
                return result
                
            if fetch_result["status"] == "anchor_not_found":
                repo.last_poll_error = "ANCHOR_NOT_FOUND: history rewrite detected"
                repo.monitoring_status = "ERROR"
                await db.commit()
                result["error"] = "anchor_not_found"
                return result

            missing_commits = fetch_result["commits"]
            oauth_token = None
            result["commits_discovered"] = len(missing_commits)

            for commit_data in missing_commits:
                # Runtime budget reservation: Do we have enough time for a scan?
                remaining = deadline - time.time()
                SAFETY_MARGIN_SECONDS = 15
                if remaining <= (settings.SCAN_TIMEOUT_SECONDS + SAFETY_MARGIN_SECONDS):
                    result["partial"] = True
                    break

                sha = commit_data["sha"]
                commit = (await db.execute(select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha))).scalars().first()

                if not commit:
                    # Savepoint (nested transaction) to safely catch IntegrityError
                    async with db.begin_nested():
                        try:
                            commit = Commit(repository_id=repo.id, hash=sha, message=commit_data["message"])
                            db.add(commit)
                            await db.flush()
                        except IntegrityError:
                            # Safely caught, rollback only this sub-transaction
                            pass
                    if not commit.id:
                        commit = (await db.execute(select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha))).scalars().first()
                        if not commit:
                            continue

                existing_scan = (await db.execute(select(Scan).where(Scan.commit_id == commit.id))).scalars().first()

                if existing_scan:
                    if existing_scan.status == "COMPLETED":
                        repo.last_processed_sha = sha
                        await db.commit()
                        continue
                    elif existing_scan.status in ("QUEUED", "RUNNING"):
                        # Active legitimate scan by another worker/trigger: preserve it and stop here for this repo
                        await db.commit()
                        return result
                    
                    # FAILED scan retry: delete it so we can create a fresh QUEUED scan without IntegrityError on commit_id
                    await db.delete(existing_scan)
                    await db.flush()

                new_scan = Scan(commit_id=commit.id, status="QUEUED")
                async with db.begin_nested():
                    try:
                        db.add(new_scan)
                        await db.flush()
                    except IntegrityError:
                        pass
                
                if not new_scan.id:
                    continue
                    
                await db.commit() # Commit transaction so run_scan's independent DB session can see the scan

                result["commits_queued"] += 1

                async with semaphore:
                    await run_scan(new_scan.id, shared_repo_dir=bare_repo_dir)

                await db.refresh(new_scan)
                if new_scan.status == "COMPLETED":
                    # Persist cursor immediately
                    repo.last_processed_sha = sha
                    repo.last_poll_error = None
                    repo.last_successful_poll_at = now
                    await db.commit()
                else:
                    repo.last_poll_error = f"Scan failed for {sha[:7]}"
                    await db.commit()
                    # A failed commit must halt processing for this repo to maintain chronological order
                    return result

        except Exception as e:
            logger.exception("Error polling repo %s", repo_id)
            try:
                repo.last_poll_error = "Repository polling failed. Check repository access and try again."
                repo.monitoring_status = "ERROR"
                await db.commit()
            except Exception:
                pass
            result["error"] = repo.last_poll_error
        finally:
            shutil.rmtree(bare_repo_dir, ignore_errors=True)

    return result

# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

async def execute_polling_cycle() -> dict:
    """Executes a single cycle of repository polling across active monitored repositories.
    Acquires database lock, processes repositories, fetches new commits, and runs scans.
    Safe to call from background in-process workers or external cron endpoints.
    """
    async with AsyncSessionLocal() as lock_db:
        locked = await acquire_poll_lock(lock_db)
        if not locked:
            return {"status": "skipped", "reason": "Another polling run is in progress or lock failed"}

        try:
            start_time = time.time()
            deadline = start_time + settings.MAX_POLLING_RUNTIME_SECONDS

            async with AsyncSessionLocal() as db:
                retryable_error = and_(
                    Repository.monitoring_status == "ERROR",
                    or_(
                        Repository.last_poll_error.is_(None),
                        ~Repository.last_poll_error.startswith("ANCHOR_NOT_FOUND:"),
                    ),
                )
                repo_ids = (await db.execute(
                    select(Repository.id).where(
                        or_(Repository.monitoring_status == "POLLING_ACTIVE", retryable_error)
                    )
                )).scalars().all()

            semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCANS)
            results = []
            
            status = "completed"
            batch_size = max(1, settings.MAX_CONCURRENT_SCANS)
            for start in range(0, len(repo_ids), batch_size):
                if time.time() > deadline:
                    status = "partial"
                    break

                batch = repo_ids[start:start + batch_size]
                batch_results = await asyncio.gather(*(
                    process_one_repository(repo_id, semaphore, deadline) for repo_id in batch
                ))
                results.extend(batch_results)
                if any(res.get("partial") for res in batch_results) or time.time() > deadline:
                    status = "partial"
                    break

            summary = {
                "status": status,
                "repositories_checked": len(results),
                "repositories_changed": sum(1 for r in results if r["changed"]),
                "commits_discovered": sum(r["commits_discovered"] for r in results),
                "commits_queued": sum(r["commits_queued"] for r in results),
                "errors": sum(1 for r in results if r["error"]),
            }
            if summary["errors"] and summary["status"] == "completed":
                summary["status"] = "completed_with_errors"
            return summary

        finally:
            await release_poll_lock(lock_db)


@router.post("/polling/run")
async def run_polling(request: Request):
    verify_cron_secret(request)
    summary = await execute_polling_cycle()
    if summary.get("status") != "completed":
        return JSONResponse(status_code=503, content=summary)
    return summary


# ---------------------------------------------------------------------------
# Admin Telemetry, Visitors, Users, & Error Logging Endpoints
# ---------------------------------------------------------------------------

class TrackVisitPayload(BaseModel):
    visitor_id: Optional[str] = None
    path: Optional[str] = "/"
    referrer: Optional[str] = None
    user_agent: Optional[str] = None


class LogErrorPayload(BaseModel):
    error_type: str = "FRONTEND_EXCEPTION"
    severity: str = "ERROR"
    message: str
    stack_trace: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None


@router.post("/track-visit")
async def track_visitor(
    request: Request,
    payload: TrackVisitPayload,
    db: AsyncSession = Depends(get_db)
):
    """Tracks anonymous and authenticated visitors browsing the software."""
    try:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
        else:
            ip = "unknown"

        ua = payload.user_agent or request.headers.get("user-agent", "Unknown Device")
        
        username = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header.removeprefix("Bearer ").strip()
                data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = data.get("sub")
            except Exception:
                pass

        visit = VisitorLog(
            visitor_id=payload.visitor_id or ip,
            ip_address=ip,
            user_agent=ua[:255] if ua else None,
            path=payload.path or "/",
            referrer=payload.referrer[:255] if payload.referrer else None,
            username=username,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(visit)
        await db.commit()
        return {"status": "ok", "tracked": True}
    except Exception as e:
        logger.warning("track_visitor error: %s", e)
        return {"status": "skipped", "error": str(e)}


@router.get("/visitors/stats")
async def get_visitor_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns analytics on the number of visitors and application traffic."""
    try:
        total_res = await db.execute(select(func.count(VisitorLog.id)))
        total_visits = total_res.scalar() or 0

        unique_res = await db.execute(select(func.count(func.distinct(VisitorLog.visitor_id))))
        unique_visitors = unique_res.scalar() or 0

        cutoff_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        today_res = await db.execute(select(func.count(VisitorLog.id)).where(VisitorLog.created_at >= cutoff_24h))
        today_visits = today_res.scalar() or 0

        cutoff_15m = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)
        active_res = await db.execute(select(func.count(func.distinct(VisitorLog.visitor_id))).where(VisitorLog.created_at >= cutoff_15m))
        active_visitors = active_res.scalar() or 0

        top_res = await db.execute(
            select(VisitorLog.path, func.count(VisitorLog.id).label("count"))
            .group_by(VisitorLog.path)
            .order_by(desc("count"))
            .limit(8)
        )
        top_paths = [{"path": row[0], "count": row[1]} for row in top_res.all()]

        recent_res = await db.execute(
            select(VisitorLog).order_by(VisitorLog.id.desc()).limit(50)
        )
        recent_rows = recent_res.scalars().all()
        recent_visits = [
            {
                "id": v.id,
                "visitor_id": v.visitor_id,
                "ip_address": v.ip_address,
                "user_agent": v.user_agent,
                "path": v.path,
                "referrer": v.referrer,
                "username": v.username,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in recent_rows
        ]

        return {
            "total_visits": total_visits,
            "unique_visitors": unique_visitors,
            "today_visits": today_visits,
            "active_visitors": active_visitors,
            "top_paths": top_paths,
            "recent_visits": recent_visits
        }
    except Exception as e:
        logger.exception("Failed to load visitor stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def get_all_users_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all registered users, roles, active status, and current session."""
    try:
        users_res = await db.execute(select(User).order_by(User.id.asc()))
        users = users_res.scalars().all()

        repo_counts_res = await db.execute(
            select(Repository.owner_id, func.count(Repository.id).label("count"))
            .group_by(Repository.owner_id)
        )
        repo_map = {row[0]: row[1] for row in repo_counts_res.all()}

        user_list = []
        for u in users:
            user_list.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "has_github": bool(u.github_access_token),
                "repositories_count": repo_map.get(u.id, 0),
                "created_at": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
                "last_login_at": u.last_login_at.isoformat() if getattr(u, "last_login_at", None) else None,
                "is_current": (u.id == current_user.id)
            })

        return {
            "total_users": len(user_list),
            "active_users": sum(1 for u in user_list if u["is_active"]),
            "admin_users": sum(1 for u in user_list if u["role"] == "Admin"),
            "current_user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role,
            },
            "users": user_list
        }
    except Exception as e:
        logger.exception("Failed to fetch users")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-error")
async def log_software_error(
    payload: LogErrorPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Logs frontend or backend errors occurring in the software."""
    try:
        username = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header.removeprefix("Bearer ").strip()
                data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = data.get("sub")
            except Exception:
                pass

        err_entry = SystemErrorLog(
            error_type=payload.error_type or "SOFTWARE_ERROR",
            severity=payload.severity or "ERROR",
            message=payload.message,
            stack_trace=payload.stack_trace,
            path=payload.path or request.url.path,
            method=payload.method or request.method,
            status_code=payload.status_code or 500,
            username=username,
            resolved=False,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(err_entry)
        await db.commit()
        await db.refresh(err_entry)
        return {"status": "logged", "error_id": err_entry.id}
    except Exception as e:
        logger.warning("log_software_error failed: %s", e)
        return {"status": "skipped", "error": str(e)}


@router.get("/errors")
async def get_system_errors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns telemetry of software errors and exceptions."""
    try:
        total_res = await db.execute(select(func.count(SystemErrorLog.id)))
        total_errors = total_res.scalar() or 0

        crit_res = await db.execute(select(func.count(SystemErrorLog.id)).where(SystemErrorLog.severity == "CRITICAL"))
        critical_errors = crit_res.scalar() or 0

        warn_res = await db.execute(select(func.count(SystemErrorLog.id)).where(SystemErrorLog.severity == "WARNING"))
        warning_errors = warn_res.scalar() or 0

        recent_res = await db.execute(
            select(SystemErrorLog).order_by(SystemErrorLog.id.desc()).limit(100)
        )
        rows = recent_res.scalars().all()
        errors_list = [
            {
                "id": r.id,
                "error_type": r.error_type,
                "severity": r.severity,
                "message": r.message,
                "stack_trace": r.stack_trace,
                "path": r.path,
                "method": r.method,
                "status_code": r.status_code,
                "username": r.username,
                "resolved": r.resolved,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

        return {
            "total_errors": total_errors,
            "critical_errors": critical_errors,
            "warning_errors": warning_errors,
            "errors": errors_list
        }
    except Exception as e:
        logger.exception("Failed to fetch error logs")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/errors")
async def clear_system_errors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Purges the system error log."""
    try:
        await db.execute(delete(SystemErrorLog))
        await db.commit()
        return {"status": "cleared", "message": "All error logs successfully cleared."}
    except Exception as e:
        logger.exception("Failed to clear error logs")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/errors/test")
async def create_test_system_error(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Simulates a test warning/error to verify live error monitoring."""
    try:
        sample_error = SystemErrorLog(
            error_type="DIAGNOSTIC_SIMULATION",
            severity="WARNING",
            message=f"Simulated test error generated by user '{current_user.username}' from Admin Dashboard.",
            stack_trace="Traceback (most recent call last):\n  File 'app/api/routes/admin.py', in create_test_system_error\n    raise DiagnosticSimulation('Verification event for real-time error monitor')\nDiagnosticSimulation: Telemetry pipeline operational.",
            path="/admin/errors/test",
            method="POST",
            status_code=200,
            username=current_user.username,
            resolved=False,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(sample_error)
        await db.commit()
        await db.refresh(sample_error)
        return {"status": "test_error_created", "error_id": sample_error.id}
    except Exception as e:
        logger.exception("Failed to create test error")
        raise HTTPException(status_code=500, detail=str(e))


