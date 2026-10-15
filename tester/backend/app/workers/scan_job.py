import json
import shutil
import subprocess
import tempfile
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from app.auth.security import decrypt_token
from app.config import settings
from app.database.models import (
    Commit,
    Finding,
    Repository,
    RiskScore,
    Scan,
    User,
    RepositoryIndex,
    AnalyzerRun,
)
from app.database.session import AsyncSessionLocal
from app.utils.github import git_environment
from app.scanners.universal import UniversalScanner
from app.scanners.models import is_test_or_benchmark_path
from app.scoring.engine import calculate_risk_score
from app.analysis.indexer import build_repository_index
from app.analyzers.registry import run_analyzers
from app.events.bus import emit_event

logger = logging.getLogger(__name__)

def safe_error(exc: Exception) -> str:
    """Return actionable user-safe errors; detailed traces belong in server logs."""
    if isinstance(exc, subprocess.TimeoutExpired):
        return "The repository operation timed out. Try again shortly."
    if isinstance(exc, subprocess.CalledProcessError):
        return f"Git could not read the repository (exit code {exc.returncode}). Check repository access and try again."
    if isinstance(exc, RuntimeError) and str(exc) == "GitHub authentication is required to scan this private repository":
        return str(exc)
    return "The scan encountered an unexpected error. Please retry; contact support if it happens again."

def calculate_score_delta(current_score: int, previous_score: int | None) -> int | None:
    """Return a persisted history delta; the first completed scan has no baseline."""
    return None if previous_score is None else current_score - previous_score

async def previous_completed_score(db, repository_id: int, current_scan_id: int) -> int | None:
    """Return only the score for the immediately preceding completed scan."""
    previous = (await db.execute(
        select(Scan).join(Scan.commit)
        .where(Commit.repository_id == repository_id, Scan.status == "COMPLETED", Scan.id != current_scan_id)
        .order_by(Scan.completed_at.desc()).limit(1)
    )).scalars().first()
    if not previous:
        return None
    score = (await db.execute(select(RiskScore).where(RiskScore.scan_id == previous.id))).scalars().first()
    return score.score if score else None

async def run_scan(scan_id: int, shared_repo_dir: str = None):
    temp_dir = None
    async with AsyncSessionLocal() as db:
        scan = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().first()
        if not scan or scan.status != "QUEUED": return
        scan.status = "RUNNING"; await db.commit()
        try:
            scan = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().first()
            if not scan:
                logger.info("Scan %s was removed before processing; exiting", scan_id)
                return
            commit = (await db.execute(select(Commit).where(Commit.id == scan.commit_id))).scalars().first()
            if not commit:
                logger.info("Commit for scan %s was removed; exiting", scan_id)
                return
            repo = (await db.execute(select(Repository).where(Repository.id == commit.repository_id))).scalars().first()
            if not repo:
                logger.info("Repository for scan %s was removed; exiting", scan_id)
                return
            user = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().first()
            if not user:
                logger.info("User for repo %s was removed; exiting", repo.id)
                return
            oauth_token = decrypt_token(user.github_access_token or "")
            if not oauth_token and not getattr(repo, 'is_public', False):
                raise RuntimeError("GitHub authentication is required to scan this private repository")
            
            temp_dir = tempfile.mkdtemp(prefix="risk_passport_scan_")
            
            env = git_environment(oauth_token)

            if shared_repo_dir:
                # Reuse the bare clone from the polling invocation. 
                # This guarantees zero duplicate object fetches across B/C/D!
                subprocess.run(["git", "-C", shared_repo_dir, "worktree", "add", "--detach", temp_dir, commit.hash], check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env)
            else:
                # Do not use --depth: an older webhook commit must remain fetchable after
                # newer commits reach the branch. --no-checkout prevents hooks/scripts.
                subprocess.run(["git", "clone", "--no-checkout", repo.url, temp_dir], check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env)
            
            oauth_token = None
            env.pop("GIT_CONFIG_VALUE_0", None)
            env.pop("GIT_CONFIG_COUNT", None)
            env.pop("GIT_CONFIG_KEY_0", None)
            if not shared_repo_dir:
                subprocess.run(["git", "-C", temp_dir, "checkout", "--detach", commit.hash], check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env)
                
            checked_out = subprocess.run(["git", "-C", temp_dir, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10, env=env).stdout.strip().lower()
            if checked_out != commit.hash: raise RuntimeError("checked out revision did not match requested SHA")
            
            # Fetch metadata
            metadata_raw = subprocess.run(["git", "-C", temp_dir, "log", "-1", "--format=%s%n%an%n%ae%n%cI%n%P", commit.hash], check=True, capture_output=True, text=True, timeout=10, env=env).stdout.strip().split("\n")
            if len(metadata_raw) >= 4:
                commit.message = metadata_raw[0]
                commit.author_name = metadata_raw[1]
                commit.author_email = metadata_raw[2]
                try:
                    commit.committed_at = datetime.fromisoformat(metadata_raw[3]).replace(tzinfo=None)
                except Exception as e:
                    print("Date parsing failed:", e)
                if len(metadata_raw) > 4 and metadata_raw[4]:
                    commit.parent_shas = metadata_raw[4].replace(" ", ",")
            
            # 1. Standard Universal Scan with Coverage
            scanner_instance = UniversalScanner(temp_dir)
            raw_findings = scanner_instance.scan()
            coverage_data = scanner_instance.get_coverage()
            
            # 2. Structural & Impact Analysis
            from app.analysis.impact import analyze_commit_changes, analyze_structural_changes, build_dependency_graph, analyze_impact
            from app.database.models import CommitAnalysis
            
            changed_files_data = analyze_commit_changes(temp_dir, commit.hash)
            structural_changes_data = analyze_structural_changes(temp_dir, commit.hash)
            dep_graph = build_dependency_graph(temp_dir)
            changed_file_paths = [cf.get('file', '') for cf in changed_files_data if cf.get('status', '') in ('A', 'M', 'R') or cf.get('status', '').startswith('R')]
            impact_data = analyze_impact(changed_file_paths, dep_graph)
            impact_data["coverage"] = coverage_data
            
            actions_detected = []
            has_sensitive_change = False
            for cf in changed_files_data:
                filepath = cf.get("file", "").lower()
                status = cf.get("status", "")
                if "auth" in filepath or "security" in filepath:
                    actions_detected.append("Authentication logic modified" if status != "A" else "Authentication logic added")
                    has_sensitive_change = True
                if "migration" in filepath or "alembic" in filepath or "schema" in filepath:
                    actions_detected.append("Database schema modified")
                if ("api" in filepath or "route" in filepath) and ("controller" in filepath or "router" in filepath or "endpoints" in filepath or "api" in filepath):
                    actions_detected.append("API endpoint modified" if status != "A" else "API endpoint added")
            actions_detected = list(set(actions_detected))
            
            db.add(CommitAnalysis(
                scan_id=scan.id,
                changed_files=json.dumps(changed_files_data),
                structural_changes=json.dumps(structural_changes_data),
                dependency_graph=json.dumps(dep_graph),
                impact_analysis=json.dumps(impact_data),
                actions_detected=json.dumps(actions_detected)
            ))

            # 2b. Comprehensive Repository Indexing for Project Hub
            index_data = None
            try:
                index_dict = build_repository_index(temp_dir, commit.hash)
                index_data = index_dict
                existing_index = (await db.execute(
                    select(RepositoryIndex).where(
                        RepositoryIndex.repository_id == repo.id,
                        RepositoryIndex.commit_sha == commit.hash
                    )
                )).scalars().first()
                if not existing_index:
                    db.add(RepositoryIndex(
                        repository_id=repo.id,
                        commit_sha=commit.hash,
                        file_count=index_dict.get("file_count", 0),
                        languages_json=json.dumps(index_dict.get("languages", {})),
                        frameworks_json=json.dumps(index_dict.get("frameworks", [])),
                        entry_points_json=json.dumps(index_dict.get("entry_points", [])),
                        module_map_json=json.dumps(index_dict.get("module_map", {})),
                        routes_json=json.dumps(index_dict.get("api_routes", [])),
                        models_json=json.dumps(index_dict.get("database_models", [])),
                        tests_json=json.dumps(index_dict.get("test_files", [])),
                        dependencies_json=json.dumps(index_dict.get("dependencies", [])),
                        ci_cd_json=json.dumps(index_dict.get("ci_cd_files", [])),
                    ))
            except Exception as e:
                logger.warning("Repository indexing encountered non-fatal error: %s", e)

            # 2c. Execute continuous analyzers and persist analyzer runs
            try:
                analyzer_results = run_analyzers(
                    repo_dir=temp_dir,
                    commit_sha=commit.hash,
                    index=index_data
                )
                now_ar = datetime.now(timezone.utc).replace(tzinfo=None)
                for a_name, a_res in analyzer_results.get("analyzers", {}).items():
                    existing_run = (await db.execute(
                        select(AnalyzerRun).where(
                            AnalyzerRun.repository_id == repo.id,
                            AnalyzerRun.commit_sha == commit.hash,
                            AnalyzerRun.analyzer_name == a_name
                        )
                    )).scalars().first()
                    if existing_run:
                        existing_run.status = a_res.get("status", "COMPLETED")
                        existing_run.coverage_status = a_res.get("coverage_status", "FULL")
                        existing_run.files_analyzed = a_res.get("files_analyzed", 0)
                        existing_run.duration_seconds = int(round(a_res.get("duration_seconds", 0)))
                        existing_run.summary_text = a_res.get("summary", "")
                        existing_run.findings_count = a_res.get("findings_count", len(a_res.get("findings", [])))
                        existing_run.details_json = json.dumps(a_res.get("details", {}))
                        existing_run.completed_at = now_ar
                    else:
                        db.add(AnalyzerRun(
                            repository_id=repo.id,
                            commit_sha=commit.hash,
                            analyzer_name=a_name,
                            analyzer_version=a_res.get("analyzer_version", "1.0.0"),
                            status=a_res.get("status", "COMPLETED"),
                            coverage_status=a_res.get("coverage_status", "FULL"),
                            files_analyzed=a_res.get("files_analyzed", 0),
                            duration_seconds=int(round(a_res.get("duration_seconds", 0))),
                            summary_text=a_res.get("summary", ""),
                            findings_count=a_res.get("findings_count", len(a_res.get("findings", []))),
                            details_json=json.dumps(a_res.get("details", {})) if isinstance(a_res.get("details"), dict) else "{}",
                            created_at=now_ar,
                            completed_at=now_ar,
                        ))
            except Exception as e:
                logger.warning("Continuous analyzer execution encountered non-fatal error: %s", e)
            
            from app.database.models import Notification
            if has_sensitive_change:
                db.add(Notification(
                    user_id=repo.owner_id,
                    repository_id=repo.id,
                    scan_id=scan.id,
                    type="SENSITIVE_CHANGE",
                    title="Sensitive Code Modified",
                    message=f"Commit {commit.hash[:7]} modified sensitive authentication or security files."
                ))
            
            # Real security alerts for actionable production vulnerabilities only (exclude test fixtures)
            for finding in raw_findings:
                f_path = finding.get("file_path") or finding.get("file")
                is_test_finding = (
                    finding.get("classification") == "Intentional test fixture or demonstration example"
                    or is_test_or_benchmark_path(f_path)
                    or "(Sample / Test Fixture)" in (finding.get("title") or "")
                )
                if not is_test_finding and finding.get("severity", "").upper() in ("CRITICAL", "HIGH"):
                    db.add(Notification(
                        user_id=repo.owner_id,
                        repository_id=repo.id,
                        scan_id=scan.id,
                        type="SECURITY_ALERT",
                        title=f"{finding.get('severity')} Risk: {finding.get('category')}",
                        message=finding.get("message", "Security risk detected in scan.")
                    ))

            # 3. Calculate Risk with Category Separation
            cov_status = coverage_data.get("overall_status", "COMPLETED")
            score_breakdown = calculate_risk_score(raw_findings, coverage_status=cov_status)
            
            # Determine lineage using Git parent first
            parent_shas_list = [p.strip() for p in (commit.parent_shas or "").split(",") if p.strip()]
            previous = None
            if parent_shas_list:
                previous = (await db.execute(
                    select(Scan).join(Scan.commit)
                    .where(Commit.repository_id == repo.id, Commit.hash.in_(parent_shas_list), Scan.status.in_(["COMPLETED", "PARTIAL"]), Scan.id != scan.id)
                    .order_by(Scan.completed_at.desc()).limit(1)
                )).scalars().first()
            if not previous:
                previous = (await db.execute(
                    select(Scan).join(Scan.commit)
                    .where(Commit.repository_id == repo.id, Scan.status.in_(["COMPLETED", "PARTIAL"]), Scan.id != scan.id)
                    .order_by(Scan.completed_at.desc()).limit(1)
                )).scalars().first()

            is_baseline = (previous is None)
            previous_score = None
            if previous:
                prev_rs = (await db.execute(select(RiskScore).where(RiskScore.scan_id == previous.id))).scalars().first()
                previous_score = prev_rs.score if prev_rs else None

            previous_findings = [] if not previous else list(
                (await db.execute(select(Finding).where(Finding.scan_id == previous.id, Finding.status != "RESOLVED"))).scalars()
            )
            previous_by_fingerprint = {f.fingerprint: f for f in previous_findings}
            current = {f["fingerprint"]: f for f in raw_findings}

            for fingerprint, finding in current.items():
                line_num = finding.get("line_number")
                if line_num is None and finding.get("location", "").startswith("Line "):
                    try: line_num = int(finding["location"].split(" ")[1])
                    except ValueError: pass

                if is_baseline:
                    finding_status = "BASELINE"
                elif fingerprint in previous_by_fingerprint:
                    finding_status = "UNCHANGED"
                else:
                    finding_status = "NEW"

                f_path = finding.get("file_path") or finding.get("file") or "Repository"
                is_fixture = (
                    finding.get("classification") == "Intentional test fixture or demonstration example"
                    or is_test_or_benchmark_path(f_path)
                    or "(Sample / Test Fixture)" in (finding.get("title") or "")
                )
                classification = (
                    "Intentional test fixture or demonstration example"
                    if is_fixture
                    else finding.get("classification", "Valid heuristic finding requiring manual verification")
                )

                # Persist rich finding payload for explainability and remediation
                desc_obj = {
                    "message": finding.get("message") or finding.get("description", "Finding"),
                    "title": finding.get("title", finding.get("rule", "Finding")),
                    "rule_id": finding.get("rule_id") or finding.get("rule", ""),
                    "confidence": "Low" if is_fixture else finding.get("confidence", "High"),
                    "classification": classification,
                    "is_test_fixture": is_fixture,
                    "code_snippet": finding.get("code_snippet"),
                    "evidence": finding.get("evidence"),
                    "impact": finding.get("impact"),
                    "remediation": finding.get("remediation"),
                    "references": finding.get("references", [])
                }

                db.add(Finding(
                    scan_id=scan.id,
                    fingerprint=fingerprint,
                    status=finding_status,
                    type=finding.get("category", "Vulnerability"),
                    description=json.dumps(desc_obj),
                    file_path=f_path,
                    line_number=line_num,
                    severity=finding.get("severity", "Medium")
                ))

            # Mark resolved findings only when previous scan existed and current scan succeeded
            if not is_baseline:
                for fingerprint, finding in previous_by_fingerprint.items():
                    if fingerprint not in current:
                        db.add(Finding(
                            scan_id=scan.id,
                            fingerprint=fingerprint,
                            status="RESOLVED",
                            type=finding.type,
                            description=finding.description,
                            file_path=finding.file_path,
                            line_number=finding.line_number,
                            severity=finding.severity
                        ))

            final_scan_status = "PARTIAL" if cov_status == "PARTIAL" else "COMPLETED"
            db.add(RiskScore(
                scan_id=scan.id,
                score=score_breakdown["final_score"],
                score_delta=calculate_score_delta(score_breakdown["final_score"], previous_score),
                details=json.dumps(score_breakdown)
            ))
            scan.status = final_scan_status
            scan.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            scan.error_message = None

            # Emit live activity event for Project Hub Watchtower
            try:
                emit_event(
                    "scan_completed",
                    repo.id,
                    {
                        "scan_id": scan.id,
                        "commit_sha": commit.hash[:7] if commit.hash else "HEAD",
                        "status": final_scan_status,
                        "score": score_breakdown["final_score"],
                    }
                )
            except Exception:
                pass
        except Exception as exc:
            logger.exception("Scan %s failed", scan_id)
            current_scan = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().first()
            if current_scan:
                current_scan.status = "FAILED"
                current_scan.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                current_scan.error_message = safe_error(exc)
                await db.commit()
        finally:
            if temp_dir:
                if shared_repo_dir:
                    subprocess.run(["git", "-C", shared_repo_dir, "worktree", "remove", "--force", temp_dir], check=False, capture_output=True)
                shutil.rmtree(temp_dir, ignore_errors=True)
        # Commit any pending clean state if scan exists
        final_scan_check = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().first()
        if final_scan_check:
            await db.commit()
