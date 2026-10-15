import json
import re
import subprocess
import tempfile
import shutil
import logging
from urllib.parse import urlparse
from app.utils.github import get_canonical_github_url, git_environment
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
import jwt
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.config import settings
from app.database.models import (
    Commit,
    Repository,
    Scan,
    User,
    Finding,
    CommitAnalysis,
    PullRequestCheck,
    Notification,
    WebhookDelivery,
    RiskScore,
    RepositoryIndex,
    AnalyzerRun,
    ProjectMemory,
    RepositoryIssue,
    ReleaseRecord,
    CrossRepoDependency,
)
from app.auth.security import decrypt_token
from app.database.session import get_db
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    PRGatePolicyUpdate,
    PRGatePolicyResponse,
)
from app.workers.scan_job import run_scan
from app.scanners.models import is_test_or_benchmark_path
from pydantic import BaseModel

class ScanRequest(BaseModel):
    commit_sha: str

class PRCheckRequest(BaseModel):
    base_sha: str
    head_sha: str
    policy_override: dict | None = None

router = APIRouter(prefix="/repositories", tags=["repositories"])
logger = logging.getLogger(__name__)
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")

def public_scan_error(message: str | None, scan_id: int) -> str | None:
    if not message:
        return None
    if message in {
        "The repository operation timed out. Try again shortly.",
        "The scan encountered an unexpected error. Please retry; contact support if it happens again.",
        "GitHub authentication is required to scan this private repository",
    } or re.fullmatch(r"Git could not read the repository \(exit code \d+\)\. Check repository access and try again\.", message):
        return message
    # Older scans may contain tracebacks or raw Git output; never expose those to the browser.
    return f"This scan failed. Retry it, or contact support with scan ID {scan_id}."


def public_poll_error(message: str | None) -> str | None:
    if not message:
        return None
    safe_values = {
        "git ls-remote failed",
        "Git could not fetch repository history",
        "ANCHOR_NOT_FOUND: history rewrite detected",
        "GitHub authentication required for this private repository",
        "Repository polling failed. Check repository access and try again.",
    }
    if message in safe_values or re.fullmatch(r"Scan failed for [0-9a-fA-F]{7}", message):
        return message
    return "Repository polling failed. Check repository access and try again."



async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username or payload.get("type") != "access": raise JWTError("invalid access token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    user = (await db.execute(select(User).where(User.username == username, User.is_active.is_(True)))).scalars().first()
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

async def owned_repository(repository_id: int, current_user: User, db: AsyncSession) -> Repository:
    repo = (await db.execute(select(Repository).where(Repository.id == repository_id, Repository.owner_id == current_user.id))).scalars().first()
    if not repo: raise HTTPException(status_code=404, detail="Repository not found")
    return repo

async def queue_scan(repository_id: int, commit_sha: str, current_user: User, db: AsyncSession) -> tuple[Scan, bool]:
    sha = commit_sha.lower()
    
    if sha == "head":
        repo = await db.execute(select(Repository).where(Repository.id == repository_id))
        repo = repo.scalars().first()
        
        path = urlparse(repo.url).path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        path = path.strip("/")
        
        try:
            import subprocess
            cmd = ["git", "ls-remote", repo.url, "HEAD"]
            oauth_token = decrypt_token(current_user.github_access_token or "")
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10,
                env=git_environment(oauth_token),
            )
            oauth_token = None
            output = result.stdout.strip()
            if output:
                sha = output.split()[0].lower()
            else:
                raise ValueError("No output from git ls-remote")
        except Exception as e:
            print(f"Failed to resolve HEAD via git ls-remote: {e}")
            raise HTTPException(status_code=503, detail="Failed to resolve HEAD commit using native Git")

    if not SHA_RE.fullmatch(sha): 
        raise HTTPException(status_code=422, detail="commit_sha must be a full 40-character Git commit SHA")
        
    commit = (await db.execute(select(Commit).where(Commit.repository_id == repository_id, Commit.hash == sha))).scalars().first()
    if not commit:
        commit = Commit(repository_id=repository_id, hash=sha, message="Commit scan"); db.add(commit); await db.flush()
    scan = (await db.execute(select(Scan).where(Scan.commit_id == commit.id).order_by(Scan.created_at.desc()))).scalars().first()
    if scan and scan.status == "COMPLETED": 
        return scan, False
    
    if scan and scan.status in ["FAILED", "QUEUED", "RUNNING"]:
        scan.status = "QUEUED"
        await db.commit()
        await db.refresh(scan)
        return scan, True
        
    scan = Scan(commit_id=commit.id, status="QUEUED"); db.add(scan); await db.commit(); await db.refresh(scan)
    return scan, True

from datetime import datetime
def parse_date(d: str):
    return datetime.fromisoformat(d.replace('Z', '+00:00'))
@router.post("/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    canonical_url, owner, repo_name = get_canonical_github_url(repo.url)
    existing = (await db.execute(select(Repository).where(Repository.owner_id == current_user.id, Repository.url == canonical_url))).scalars().first()
    if existing: return existing
    
    # Fetch public metadata
    try:
        import subprocess
        token = decrypt_token(current_user.github_access_token) if current_user.github_access_token else None
        command = ["git", "ls-remote", "--symref", canonical_url, "HEAD"]
        # Try public access first so a connected GitHub account does not cause public
        # repositories to be mislabeled as private or send credentials unnecessarily.
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=git_environment())
        repository_is_public = result.returncode == 0
        if result.returncode != 0 and token:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=git_environment(token))
        token = None
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail="Repository not found, is private, or requires authentication.")
            
        default_branch = "main" # fallback
        for line in result.stdout.splitlines():
            if line.startswith("ref: refs/heads/"):
                parts = line.split("\t")
                if len(parts) > 1 and parts[1] == "HEAD":
                    default_branch = parts[0].replace("ref: refs/heads/", "")
                    break
                    
        db_repo = Repository(
            name=f"{owner}/{repo_name}",
            url=canonical_url,
            owner_id=current_user.id,
            provider="github",
            github_owner=owner,
            default_branch=default_branch,
            is_public=repository_is_public,
            github_created_at=None,
            github_updated_at=None,
            monitoring_status="POLLING_ACTIVE"
        )
        db.add(db_repo)
        await db.commit()
        await db.refresh(db_repo)
        return db_repo
        
    except HTTPException:
        raise
    except Exception:
        logger.exception("Repository connection failed for user %s", current_user.id)
        raise HTTPException(status_code=503, detail="Could not connect to GitHub. Check the repository URL and your access, then try again.")


@router.get("", response_model=list[RepositoryResponse])
@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repos = list((await db.execute(select(Repository).where(Repository.owner_id == current_user.id))).scalars())
    for repo in repos:
        repo.last_poll_error = public_poll_error(repo.last_poll_error)
    return repos


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await owned_repository(repository_id, current_user, db)
    repo_name = repo.name

    try:
        # 1. Identify all commits associated with this repository
        commit_ids = (
            await db.execute(
                select(Commit.id).where(Commit.repository_id == repository_id)
            )
        ).scalars().all()

        if commit_ids:
            # 2. Identify all scans associated with these commits
            scan_ids = (
                await db.execute(
                    select(Scan.id).where(Scan.commit_id.in_(commit_ids))
                )
            ).scalars().all()

            if scan_ids:
                # 3. Clean up scan child records
                await db.execute(delete(Finding).where(Finding.scan_id.in_(scan_ids)))
                await db.execute(delete(RiskScore).where(RiskScore.scan_id.in_(scan_ids)))
                await db.execute(delete(CommitAnalysis).where(CommitAnalysis.scan_id.in_(scan_ids)))
                await db.execute(delete(Notification).where(Notification.scan_id.in_(scan_ids)))
                await db.execute(delete(Scan).where(Scan.id.in_(scan_ids)))

            # 4. Clean up commits
            await db.execute(delete(Commit).where(Commit.id.in_(commit_ids)))

        # 5. Clean up repository-level records
        await db.execute(delete(Notification).where(Notification.repository_id == repository_id))
        await db.execute(delete(PullRequestCheck).where(PullRequestCheck.repository_id == repository_id))
        await db.execute(delete(WebhookDelivery).where(WebhookDelivery.repository_id == repository_id))
        await db.execute(delete(RepositoryIndex).where(RepositoryIndex.repository_id == repository_id))
        await db.execute(delete(AnalyzerRun).where(AnalyzerRun.repository_id == repository_id))
        await db.execute(delete(ProjectMemory).where(ProjectMemory.repository_id == repository_id))
        await db.execute(delete(RepositoryIssue).where(RepositoryIssue.repository_id == repository_id))
        await db.execute(delete(ReleaseRecord).where(ReleaseRecord.repository_id == repository_id))
        await db.execute(delete(CrossRepoDependency).where((CrossRepoDependency.upstream_repo_id == repository_id) | (CrossRepoDependency.downstream_repo_id == repository_id)))

        # 6. Delete repository record itself
        await db.execute(delete(Repository).where(Repository.id == repository_id))

        await db.commit()
        from app.events.bus import clear_repository_events
        clear_repository_events(repository_id)
        logger.info(
            "Successfully removed repository %s (ID %s) for user %s",
            repo_name,
            repository_id,
            current_user.id,
        )
        return {
            "message": "Repository removed successfully",
            "id": repository_id,
            "name": repo_name,
        }
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to delete repository %s: %s", repository_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete repository")

@router.get("/github")
async def list_github_repositories(current_user: User = Depends(get_current_user)):
    if not current_user.github_access_token: 
        raise HTTPException(status_code=409, detail="GitHub authentication required")
        
    plain_token = decrypt_token(current_user.github_access_token)
    if not plain_token:
        raise HTTPException(status_code=409, detail="GitHub authentication required (invalid token)")
        
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://api.github.com/user/repos?per_page=100&sort=updated", headers={"Authorization": f"Bearer {plain_token}", "Accept": "application/vnd.github+json"})
    except httpx.HTTPError: raise HTTPException(status_code=503, detail="GitHub is unavailable")
    if response.status_code in {401, 403}: raise HTTPException(status_code=409, detail="GitHub authentication or repository access is required")
    if response.status_code != 200: raise HTTPException(status_code=503, detail="GitHub repository listing is unavailable")
    
    # Securely discard plain token
    del plain_token
    
    return [{"id": r["id"], "name": r["full_name"], "url": r["clone_url"], "language": r.get("language"), "updated_at": r.get("updated_at"), "created_at": r.get("created_at"), "default_branch": r.get("default_branch"), "private": r.get("private")} for r in response.json()]

@router.post("/{repository_id}/scan")
async def trigger_manual_scan(repository_id: int, request: ScanRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scan, created = await queue_scan(repository_id, request.commit_sha, current_user, db)
    if created: background_tasks.add_task(run_scan, scan.id)
    
    msg = f"Scan #{scan.id} queued for commit {request.commit_sha[:7] if len(request.commit_sha) >= 7 else request.commit_sha}." if created else f"Commit {request.commit_sha[:7] if len(request.commit_sha) >= 7 else request.commit_sha} was previously scanned (Scan #{scan.id})."
    return {
        "scan_id": scan.id,
        "status": scan.status,
        "queued": created,
        "commit_sha": request.commit_sha,
        "message": msg
    }

def is_fixture_finding(f) -> bool:
    if is_test_or_benchmark_path(f.file_path):
        return True
    desc = f.description or ""
    if "Intentional test fixture" in desc or '"is_test_fixture": true' in desc:
        return True
    return False

@router.get("/{repository_id}/scans")
async def get_repository_scans(repository_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scans = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Commit.repository_id == repository_id).order_by(Scan.created_at.desc()))).scalars().all()
    out = []
    for s in scans:
        act_count = sum(1 for f in s.findings if not is_fixture_finding(f))
        out.append({
            "id": s.id,
            "commit_sha": s.commit.hash,
            "status": s.status,
            "score": s.risk_score.score if s.risk_score else None,
            "score_details": s.risk_score.details if s.risk_score else None,
            "created_at": s.created_at,
            "findings_count": act_count,
            "actionable_findings_count": act_count,
            "test_fixtures_count": len(s.findings) - act_count,
            "total_findings_count": len(s.findings),
            "error_message": public_scan_error(s.error_message, s.id)
        })
    return out

@router.get("/{repository_id}/risk-history")
async def get_risk_history(repository_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    from sqlalchemy.orm import selectinload
    from app.database.models import Notification
    scans = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Commit.repository_id == repository_id, Scan.status.in_(["COMPLETED", "PARTIAL"])).order_by(Scan.completed_at.asc()))).scalars().all()
    notifications_by_scan: dict[int, list] = {}
    if scans:
        scan_ids = [scan.id for scan in scans]
        notifications = (await db.execute(select(Notification).where(Notification.scan_id.in_(scan_ids)))).scalars().all()
        for notification in notifications:
            notifications_by_scan.setdefault(notification.scan_id, []).append(notification)

    result = []
    for s in scans:
        notifications = notifications_by_scan.get(s.id, [])
        act_count = sum(1 for f in s.findings if not is_fixture_finding(f))
        result.append({
            "id": s.id,
            "commit_sha": s.commit.hash, 
            "short_sha": s.commit.hash[:7], 
            "risk_score": s.risk_score.score if s.risk_score else None, 
            "score_delta": s.risk_score.score_delta if s.risk_score else None, 
            "scanned_at": s.completed_at, 
            "commit_message": s.commit.message,
            "findings_count": act_count,
            "actionable_findings_count": act_count,
            "test_fixtures_count": len(s.findings) - act_count,
            "total_findings_count": len(s.findings),
            "alerts": [n.title for n in notifications]
        })
    return result

from app.database.models import CommitAnalysis

@router.get("/{repository_id}/scans/{scan_id}")
async def get_scan_audit(repository_id: int, scan_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scan = (await db.execute(select(Scan)
        .join(Scan.commit)
        .options(selectinload(Scan.findings), selectinload(Scan.risk_score), selectinload(Scan.commit), selectinload(Scan.commit_analysis))
        .where(Scan.id == scan_id, Commit.repository_id == repository_id)
    )).scalars().first()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    # Handle non-completed lifecycle states cleanly
    if scan.status in ["QUEUED", "RUNNING"]:
        human_summary = f"Scan #{scan.id} is currently {scan.status.lower()} for commit {scan.commit.hash[:7]}. Security analysis is in progress and results will update automatically once completed."
        score_explanation = f"Security score calculation will complete when the scan finishes."
        return {
            "id": scan.id,
            "commit_sha": scan.commit.hash,
            "message": scan.commit.message,
            "author": scan.commit.author_name or "Unknown",
            "timestamp": scan.commit.committed_at.isoformat() if scan.commit.committed_at else None,
            "status": scan.status,
            "findings": [],
            "changes": [],
            "impact": {},
            "coverage": {},
            "risk_score": None,
            "previous_score": None,
            "score_delta": None,
            "score_details": {},
            "previous_commit": None,
            "actions_detected": [],
            "human_summary": human_summary,
            "score_explanation": score_explanation,
            "error_message": None,
            "notifications": []
        }
    elif scan.status == "FAILED":
        human_summary = f"Scan #{scan.id} failed to complete. Error: {public_scan_error(scan.error_message, scan.id)}. You can retry this scan."
        score_explanation = "Security score could not be calculated because the scan failed."
        return {
            "id": scan.id,
            "commit_sha": scan.commit.hash,
            "message": scan.commit.message,
            "author": scan.commit.author_name or "Unknown",
            "timestamp": scan.commit.committed_at.isoformat() if scan.commit.committed_at else None,
            "status": "FAILED",
            "findings": [],
            "changes": [],
            "impact": {},
            "coverage": {},
            "risk_score": None,
            "previous_score": None,
            "score_delta": None,
            "score_details": {},
            "previous_commit": None,
            "actions_detected": [],
            "human_summary": human_summary,
            "score_explanation": score_explanation,
            "error_message": public_scan_error(scan.error_message, scan.id),
            "notifications": []
        }

    analysis = scan.commit_analysis
    import json
    
    actions_detected = []
    if analysis and analysis.actions_detected:
        actions_detected = json.loads(analysis.actions_detected)
        
    changes = []
    if analysis and analysis.changed_files:
        changes = json.loads(analysis.changed_files)
    impact = {}
    if analysis and analysis.impact_analysis:
        impact = json.loads(analysis.impact_analysis)
    
    coverage = impact.get("coverage", {}) if isinstance(impact, dict) else {}
        
    from app.database.models import Notification
    notifications = (await db.execute(select(Notification).where(Notification.scan_id == scan.id))).scalars().all()
    
    score_delta = scan.risk_score.score_delta if scan.risk_score else None
    current_score = scan.risk_score.score if scan.risk_score else None
    previous_score = current_score - score_delta if score_delta is not None and current_score is not None else None
        
    previous_commit_obj = None
    if previous_score is not None:
        prev_scan = (await db.execute(
            select(Scan).join(Scan.commit).options(selectinload(Scan.commit))
            .where(Commit.repository_id == repository_id, Scan.status.in_(["COMPLETED", "PARTIAL"]), Scan.id != scan.id, Scan.completed_at < scan.completed_at)
            .order_by(Scan.completed_at.desc()).limit(1)
        )).scalars().first()
        
        if prev_scan:
            previous_commit_obj = {
                "sha": prev_scan.commit.hash,
                "short_sha": prev_scan.commit.hash[:7],
                "message": prev_scan.commit.message,
                "author": prev_scan.commit.author_name or "Unknown",
                "timestamp": prev_scan.commit.committed_at.isoformat() if prev_scan.commit.committed_at else None,
                "score": previous_score
            }

    status_map = {"A": "adds", "M": "modifies", "D": "deletes", "R": "renames"}
    file_actions = {}
    for c in changes:
        st = c.get("status", "M")[0]
        if st not in file_actions: file_actions[st] = []
        
        if st == "R" and c.get("old_path"):
            file_actions[st].append(f"`{c['old_path']}` to `{c['file']}`")
        else:
            file_actions[st].append(f"`{c.get('file', '')}`")
    
    parts = []
    for st, verb in [("A", "adds"), ("M", "modifies"), ("D", "deletes"), ("R", "renames")]:
        if st in file_actions:
            if len(file_actions[st]) <= 2:
                parts.append(f"{verb} {', '.join(file_actions[st])}")
            else:
                parts.append(f"{verb} {len(file_actions[st])} files")
    
    human_summary = "This commit " + ", and ".join(parts) + "." if parts else "This commit contains no detectable file changes."
    
    if actions_detected:
        human_summary += f" Overall, the changes appear to include: {', '.join(a.lower() for a in actions_detected)}."
    
    if previous_score is None:
        human_summary += f"\n\nThis is a baseline scan. All issues present in the repository at this commit are recorded as baseline. The initial score is {current_score}."
    else:
        new_findings = [f for f in scan.findings if f.status == "NEW"]
        resolved_findings = [f for f in scan.findings if f.status == "RESOLVED"]
        
        actionable_new = [
            f for f in new_findings
            if not is_test_or_benchmark_path(f.file_path) and "Intentional test fixture" not in (f.description or "")
        ]
        actionable_resolved = [
            f for f in resolved_findings
            if not is_test_or_benchmark_path(f.file_path) and "Intentional test fixture" not in (f.description or "")
        ]
        
        finding_desc = ""
        if actionable_new:
            worst = max(actionable_new, key=lambda x: {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(x.severity, 0))
            issue_type = worst.type
            finding_desc = f"It introduces a {worst.severity} {issue_type} finding in `{worst.file_path}`"
            if worst.line_number: finding_desc += f" on line {worst.line_number}"
            if len(actionable_new) > 1: finding_desc += f", along with {len(actionable_new)-1} other new issue(s)."
            else: finding_desc += "."
        elif actionable_resolved:
            best = actionable_resolved[0]
            finding_desc = f"It resolves a {best.type} finding in `{best.file_path}`"
            if len(actionable_resolved) > 1: finding_desc += f", along with {len(actionable_resolved)-1} other finding(s)."
            else: finding_desc += "."
        elif new_findings:
            finding_desc = "No new production security vulnerabilities were introduced (new items are isolated test/benchmark fixtures with 0 score deduction)."
        else:
            finding_desc = "No new risk-scoring findings were introduced."
            
        score_desc = ""
        if current_score != previous_score and previous_score is not None:
            direction = "decreased" if current_score < previous_score else "improved"
            score_desc = f"As a result, the risk score {direction} from {previous_score} to {current_score}."
        else:
            score_desc = f"The score remained {current_score}."
            
        human_summary += f"\n\n{finding_desc} {score_desc}"

    score_explanation = ""
    if previous_score is None:
        score_explanation = "This is a baseline scan. No previous risk score is available to compare."
    elif score_delta == 0:
        if actionable_new:
            score_explanation = "The security score remained unchanged, likely because the minimum risk score limit was reached, despite new issues being introduced."
        else:
            score_explanation = "The security score remained unchanged because no risk-scoring findings were added or resolved between the two completed scans."
    else:
        score_explanation = f"The security score {'decreased' if score_delta < 0 else 'improved'} by {abs(score_delta)} points. "
        score_explanation += "Risk changed because this commit "
        reasons = []
        if actionable_new: reasons.append(f"introduced {len(actionable_new)} new actionable issue(s)")
        if actionable_resolved: reasons.append(f"resolved {len(actionable_resolved)} previous finding(s)")
        if not reasons: reasons.append("had structural changes affecting risk calculations")
        score_explanation += " and ".join(reasons) + "."

    # Format findings with rich metadata
    formatted_findings = []
    for f in scan.findings:
        title = f.type
        rule_id = f.type
        desc_text = f.description
        confidence = "High"
        code_snippet = None
        evidence = None
        impact_text = None
        remediation = None
        references = []
        classification = "Valid heuristic finding requiring manual verification"

        if f.description:
            try:
                parsed = json.loads(f.description)
                if isinstance(parsed, dict):
                    desc_text = parsed.get("message", f.description)
                    title = parsed.get("title", f.type)
                    rule_id = parsed.get("rule_id", f.type)
                    confidence = parsed.get("confidence", "High")
                    classification = parsed.get("classification", "Valid heuristic finding requiring manual verification")
                    code_snippet = parsed.get("code_snippet")
                    evidence = parsed.get("evidence")
                    impact_text = parsed.get("impact")
                    remediation = parsed.get("remediation")
                    references = parsed.get("references", [])
            except (json.JSONDecodeError, TypeError):
                pass

        is_fixture = (
            classification == "Intentional test fixture or demonstration example"
            or is_test_or_benchmark_path(f.file_path)
            or "(Sample / Test Fixture)" in title
            or "(Test Fixture)" in title
        )
        if is_fixture:
            classification = "Intentional test fixture or demonstration example"
            confidence = "Low"

        formatted_findings.append({
            "id": f.id,
            "fingerprint": f.fingerprint,
            "title": title,
            "rule_id": rule_id,
            "category": f.type,
            "description": desc_text,
            "severity": f.severity,
            "confidence": confidence,
            "classification": classification,
            "is_test_fixture": is_fixture,
            "status": f.status or ("BASELINE" if previous_score is None else "NEW"),
            "file_path": f.file_path,
            "line_number": f.line_number,
            "code_snippet": code_snippet,
            "evidence": evidence,
            "impact": impact_text,
            "remediation": remediation,
            "references": references
        })

    score_details_dict = json.loads(scan.risk_score.details) if scan.risk_score and scan.risk_score.details else {}
    category_scores = score_details_dict.get("category_scores", {})

    return {
        "id": scan.id,
        "commit_sha": scan.commit.hash,
        "message": scan.commit.message,
        "author": scan.commit.author_name or "Unknown",
        "timestamp": scan.commit.committed_at.isoformat() if scan.commit.committed_at else None,
        "status": scan.status,
        "findings": formatted_findings,
        "findings_count": sum(1 for f in formatted_findings if not f.get("is_test_fixture")),
        "actionable_findings_count": sum(1 for f in formatted_findings if not f.get("is_test_fixture")),
        "test_fixtures_count": sum(1 for f in formatted_findings if f.get("is_test_fixture")),
        "total_findings_count": len(formatted_findings),
        "changes": changes,
        "impact": impact,
        "coverage": coverage,
        "risk_score": current_score,
        "category_scores": category_scores,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "score_details": score_details_dict,
        "previous_commit": previous_commit_obj,
        "actions_detected": actions_detected,
        "human_summary": human_summary,
        "score_explanation": score_explanation,
        "error_message": public_scan_error(scan.error_message, scan.id),
        "notifications": [{"id": n.id, "type": n.type, "title": n.title, "message": n.message} for n in notifications]
    }


@router.get("/{repository_id}/scans/{scan_id}/audit")
async def get_scan_audit_alias(
    repository_id: int,
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_scan_audit(repository_id=repository_id, scan_id=scan_id, current_user=current_user, db=db)


@router.get("/{repository_id}/scans/{scan_id}/report.pdf")
async def export_scan_pdf_report(
    repository_id: int,
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await owned_repository(repository_id, current_user, db)
    scan = (
        await db.execute(
            select(Scan)
            .join(Scan.commit)
            .options(
                selectinload(Scan.findings),
                selectinload(Scan.risk_score),
                selectinload(Scan.commit),
                selectinload(Scan.commit_analysis),
            )
            .where(Scan.id == scan_id, Commit.repository_id == repository_id)
        )
    ).scalars().first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    from app.services.pdf_report import generate_scan_pdf_report

    try:
        pdf_bytes = generate_scan_pdf_report(
            repo=repo,
            scan=scan,
            commit=scan.commit,
            findings=scan.findings,
            risk_score=scan.risk_score,
            commit_analysis=scan.commit_analysis,
        )
    except Exception as exc:
        logger.exception("Failed to generate PDF report for scan %s: %s", scan_id, exc)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")

    safe_repo_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", repo.name)
    commit_short = scan.commit.hash[:7] if scan.commit and scan.commit.hash else "HEAD"
    filename = f"gitflow-report-{safe_repo_name}-{commit_short}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


class AskRequest(BaseModel):
    question: str

@router.post("/{repository_id}/scans/{scan_id}/ask")
async def ask_scan_question(repository_id: int, scan_id: int, request: AskRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    from sqlalchemy.orm import selectinload
    from app.database.models import Notification
    import json
    
    scan = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Scan.id == scan_id, Commit.repository_id == repository_id))).scalars().first()
    if not scan: raise HTTPException(status_code=404, detail="Scan not found")
        
    analysis = (await db.execute(select(CommitAnalysis).where(CommitAnalysis.scan_id == scan.id))).scalars().first()
    notifications = (await db.execute(select(Notification).where(Notification.scan_id == scan.id))).scalars().all()
    
    actions = json.loads(analysis.actions_detected) if analysis and analysis.actions_detected else []
    changes = json.loads(analysis.changed_files) if analysis and analysis.changed_files else []
    impact = json.loads(analysis.impact_analysis) if analysis and analysis.impact_analysis else []
    findings = scan.findings
    
    # Intent normalization
    q = request.question.lower().strip()
    
    intents = {
        "what_changed": ["what changed", "what was changed", "tell me what changed", "what did this commit modify", "which files changed", "what changed in this commit", "files modified"],
        "why_risk": ["why did risk increase", "why is the score lower", "why did my score change", "why did the risk score change", "why risk", "score delta", "risk score"],
        "impact": ["what can this affect", "what modules may be affected", "what is affected", "impact", "indirectly affected", "what could be affected indirectly", "affected"],
        "security": ["was anything security related changed", "security", "security-sensitive", "secrets", "auth"],
        "dependencies": ["did dependencies change", "dependencies", "packages"],
        "review": ["what should i review", "review", "which files should i review"],
        "explain": ["explain this commit", "summarize this commit", "explain", "simply", "summary"],
        "alerts": ["what alerts were triggered", "alerts", "notifications"]
    }
    
    matched_intent = None
    for intent, variants in intents.items():
        if any(v in q for v in variants):
            matched_intent = intent
            break
            
    answer = ""
    facts = []
    sources = []
    
    # Score Delta Convention: current_score - previous_score
    # Negative delta = risk decreased (improved)
    # Positive delta = risk increased (worsened)
    
    if matched_intent == "what_changed":
        answer = f"VERIFIED FACT:\nThis commit modified {len(changes)} files."
        if changes:
            answer += "\n\nFiles changed:\n" + "\n".join([f"- {c.get('file', c) if isinstance(c, dict) else c}" for c in changes])
        facts.append(f"{len(changes)} files modified.")
        sources.append("CommitAnalysis.changed_files")
        
    elif matched_intent == "why_risk":
        if not scan.risk_score:
            answer = "VERIFIED FACT:\nRisk score is currently unavailable for this commit."
        else:
            score_delta = scan.risk_score.score_delta or 0
            current_score = scan.risk_score.score
            previous_score = current_score - score_delta
            
            if score_delta == 0:
                answer = f"VERIFIED FACT:\nThe risk score did not change (remained at {current_score})."
            else:
                direction = "decreased" if score_delta < 0 else "increased"
                answer = f"VERIFIED FACT:\nThe risk score {direction} by {abs(score_delta)} points (from {previous_score} to {current_score})."
            if findings:
                answer += "\n\nContributing findings (VERIFIED FACT):\n" + "\n".join([f"- {f.description}" for f in findings])
        facts.append(f"Score delta: {score_delta}")
        sources.append("RiskScore.score_delta")
        
    elif matched_intent == "impact":
        if impact:
            answer = "POTENTIAL IMPACT:\nThe following modules could be indirectly affected by this change based on structural dependency rules:\n" + "\n".join([f"- {i}" for i in impact])
            facts.append(f"{len(impact)} modules potentially affected.")
        else:
            answer = "VERIFIED FACT:\nNo indirect module impact was deterministically detected."
        sources.append("CommitAnalysis.impact_analysis")
            
    elif matched_intent == "security":
        sec_actions = [a for a in actions if "auth" in a.lower() or "security" in a.lower()]
        sec_findings = [f.description for f in findings if "secur" in f.type.lower() or f.severity.lower() in ("high", "critical")]
        if sec_actions or sec_findings:
            answer = "VERIFIED FACT:\nSecurity-sensitive events detected:\n"
            if sec_actions:
                answer += "\nActions:\n" + "\n".join([f"- {a}" for a in sec_actions])
            if sec_findings:
                answer += "\n\nFindings:\n" + "\n".join([f"- {f}" for f in sec_findings])
            facts.append("Security modifications/findings present.")
        else:
            answer = "VERIFIED FACT:\nNo explicit security-sensitive changes were detected."
        sources.append("CommitAnalysis.actions_detected")
        sources.append("Findings")
        
    elif matched_intent == "dependencies":
        dep_actions = [a for a in actions if "dependenc" in a.lower()]
        if dep_actions:
            answer = "VERIFIED FACT:\nDependency changes detected:\n" + "\n".join([f"- {a}" for a in dep_actions])
            facts.append("Dependencies modified.")
        else:
            answer = "VERIFIED FACT:\nNo dependency manifest changes were detected."
        sources.append("CommitAnalysis.actions_detected")
        
    elif matched_intent == "review":
        answer = "POTENTIAL IMPACT:\nYou should review files that triggered alerts or direct structural changes."
        if changes:
            answer += "\n\nModified files requiring review:\n" + "\n".join([f"- {c.get('file', c) if isinstance(c, dict) else c}" for c in changes])
        sources.append("CommitAnalysis.changed_files")
        
    elif matched_intent == "alerts":
        if notifications:
            answer = "VERIFIED FACT:\nThe following alerts were triggered:\n" + "\n".join([f"- {n.title}: {n.message}" for n in notifications])
            facts.append(f"{len(notifications)} alerts triggered.")
        else:
            answer = "VERIFIED FACT:\nNo alerts were triggered for this commit."
        sources.append("Notification")
        
    elif matched_intent == "explain":
        answer = f"VERIFIED FACT:\nThis commit by {scan.commit.author} changed {len(changes)} files. "
        if actions:
            answer += f"It performed the following actions: {', '.join(actions)}. "
        if notifications:
            answer += f"It triggered {len(notifications)} alerts."
        sources.append("Commit metadata")
        sources.append("CommitAnalysis.actions_detected")
        
    else:
        answer = "I can answer questions about this commit's changes, risk, impact, security changes, dependencies, alerts, and review areas."
        
    return {
        "question": request.question,
        "answer": answer,
        "facts": facts,
        "sources": sources,
        "confidence": "deterministic"
    }


@router.get("/{repository_id}/pr-policy", response_model=PRGatePolicyResponse)
async def get_pr_policy(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await owned_repository(repository_id, current_user, db)
    return PRGatePolicyResponse(
        pr_gate_enabled=repo.pr_gate_enabled,
        pr_gate_block_critical=repo.pr_gate_block_critical,
        pr_gate_block_high=repo.pr_gate_block_high,
        pr_gate_block_medium=repo.pr_gate_block_medium,
        pr_gate_block_incomplete=repo.pr_gate_block_incomplete,
    )


@router.put("/{repository_id}/pr-policy", response_model=PRGatePolicyResponse)
async def update_pr_policy(
    repository_id: int,
    policy_update: PRGatePolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await owned_repository(repository_id, current_user, db)
    if policy_update.pr_gate_enabled is not None:
        repo.pr_gate_enabled = policy_update.pr_gate_enabled
    if policy_update.pr_gate_block_critical is not None:
        repo.pr_gate_block_critical = policy_update.pr_gate_block_critical
    if policy_update.pr_gate_block_high is not None:
        repo.pr_gate_block_high = policy_update.pr_gate_block_high
    if policy_update.pr_gate_block_medium is not None:
        repo.pr_gate_block_medium = policy_update.pr_gate_block_medium
    if policy_update.pr_gate_block_incomplete is not None:
        repo.pr_gate_block_incomplete = policy_update.pr_gate_block_incomplete
    await db.commit()
    await db.refresh(repo)
    return PRGatePolicyResponse(
        pr_gate_enabled=repo.pr_gate_enabled,
        pr_gate_block_critical=repo.pr_gate_block_critical,
        pr_gate_block_high=repo.pr_gate_block_high,
        pr_gate_block_medium=repo.pr_gate_block_medium,
        pr_gate_block_incomplete=repo.pr_gate_block_incomplete,
    )


@router.post("/{repository_id}/pull-requests/check")
async def check_pull_request(
    repository_id: int,
    request: PRCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await owned_repository(repository_id, current_user, db)
    base_sha = request.base_sha.lower().strip()
    head_sha = request.head_sha.lower().strip()

    policy = {
        "enabled": repo.pr_gate_enabled,
        "block_critical": repo.pr_gate_block_critical,
        "block_high": repo.pr_gate_block_high,
        "block_medium": repo.pr_gate_block_medium,
        "block_incomplete": repo.pr_gate_block_incomplete,
    }
    if request.policy_override:
        policy.update(request.policy_override)

    # Fetch DB scans if they exist
    base_scan = (await db.execute(
        select(Scan).join(Scan.commit)
        .where(Commit.repository_id == repo.id, Commit.hash == base_sha, Scan.status.in_(["COMPLETED", "PARTIAL"]))
    )).scalars().first()

    head_scan = (await db.execute(
        select(Scan).join(Scan.commit)
        .where(Commit.repository_id == repo.id, Commit.hash == head_sha, Scan.status.in_(["COMPLETED", "PARTIAL"]))
    )).scalars().first()

    pre_base_findings = None
    if base_scan:
        b_findings = (await db.execute(select(Finding).where(Finding.scan_id == base_scan.id, Finding.status != "RESOLVED"))).scalars().all()
        pre_base_findings = []
        for f in b_findings:
            try:
                desc = json.loads(f.description)
            except Exception:
                desc = {"message": f.description}
            pre_base_findings.append({
                "fingerprint": f.fingerprint,
                "category": f.type,
                "severity": f.severity,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "rule_id": desc.get("rule_id", ""),
                "classification": desc.get("classification", ""),
                "message": desc.get("message", ""),
                "evidence": desc.get("evidence", ""),
                "remediation": desc.get("remediation", ""),
            })

    pre_head_findings = None
    pre_coverage = None
    if head_scan:
        h_findings = (await db.execute(select(Finding).where(Finding.scan_id == head_scan.id, Finding.status != "RESOLVED"))).scalars().all()
        pre_head_findings = []
        for f in h_findings:
            try:
                desc = json.loads(f.description)
            except Exception:
                desc = {"message": f.description}
            pre_head_findings.append({
                "fingerprint": f.fingerprint,
                "category": f.type,
                "severity": f.severity,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "rule_id": desc.get("rule_id", ""),
                "classification": desc.get("classification", ""),
                "message": desc.get("message", ""),
                "evidence": desc.get("evidence", ""),
                "remediation": desc.get("remediation", ""),
            })
        if head_scan.commit_analysis and head_scan.commit_analysis.impact_analysis:
            try:
                imp = json.loads(head_scan.commit_analysis.impact_analysis)
                pre_coverage = imp.get("coverage")
            except Exception:
                pass

    temp_dir = tempfile.mkdtemp(prefix="gitflow_pr_check_")
    try:
        oauth_token = decrypt_token(current_user.github_access_token or "")
        env = git_environment(oauth_token)
        subprocess.run(
            ["git", "clone", "--bare", repo.url, temp_dir],
            check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env
        )
        oauth_token = None

        from app.analysis.pr_gate import run_pr_security_check
        result = run_pr_security_check(
            repo_dir=temp_dir,
            base_sha=base_sha,
            head_sha=head_sha,
            policy=policy,
            precomputed_head_findings=pre_head_findings,
            precomputed_base_findings=pre_base_findings,
            precomputed_coverage=pre_coverage,
        )
        return result
    except Exception as e:
        logger.error(f"PR security check error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check pull request: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/{repository_id}/pr-checks")
async def get_repository_pr_checks(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await owned_repository(repository_id, current_user, db)
    checks = (
        await db.execute(
            select(PullRequestCheck)
            .where(PullRequestCheck.repository_id == repo.id)
            .order_by(PullRequestCheck.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id": c.id,
            "pr_number": c.pr_number,
            "base_sha": c.base_sha,
            "head_sha": c.head_sha,
            "status": c.status,
            "conclusion": c.conclusion,
            "policy_decision": c.policy_decision,
            "coverage_status": c.coverage_status,
            "newly_introduced_count": c.newly_introduced_count,
            "resolved_count": c.resolved_count,
            "github_check_run_id": c.github_check_run_id,
            "details_url": c.details_url,
            "created_at": c.created_at,
            "completed_at": c.completed_at,
        }
        for c in checks
    ]


@router.get("/{repository_id}/pr-checks/{check_id}")
async def get_repository_pr_check_detail(
    repository_id: int,
    check_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await owned_repository(repository_id, current_user, db)
    check = (
        await db.execute(
            select(PullRequestCheck).where(
                PullRequestCheck.repository_id == repo.id,
                PullRequestCheck.id == check_id,
            )
        )
    ).scalars().first()
    if not check:
        raise HTTPException(status_code=404, detail="PR check not found")
    return {
        "id": check.id,
        "pr_number": check.pr_number,
        "base_sha": check.base_sha,
        "head_sha": check.head_sha,
        "status": check.status,
        "conclusion": check.conclusion,
        "policy_decision": check.policy_decision,
        "coverage_status": check.coverage_status,
        "newly_introduced_count": check.newly_introduced_count,
        "resolved_count": check.resolved_count,
        "summary_markdown": check.summary_markdown,
        "github_check_run_id": check.github_check_run_id,
        "details_url": check.details_url,
        "created_at": check.created_at,
        "completed_at": check.completed_at,
    }
