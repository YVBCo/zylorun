import asyncio
import json
import os
import subprocess
import time
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.session import AsyncSessionLocal, engine, Base
from app.database.models import User, Repository, Commit, Scan
from app.api.routes.repositories import get_scan_audit
from app.api.routes.admin import process_one_repository
from app.workers.scan_job import run_scan

import tempfile

mock_repo_dir = tempfile.mkdtemp(prefix="gitflow_mock_repo_")

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        user = User(username="testuser", email="test@test.com", hashed_password="hash")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        repo = Repository(
            name="mock-repo",
            url=f"file://{mock_repo_dir}",
            owner_id=user.id,
            provider="github",
            monitoring_status="POLLING_ACTIVE",
            default_branch="main"
        )
        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        
        # Init git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=mock_repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=mock_repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=mock_repo_dir, check=True)
        
        return user, repo

def run_git(cmd):
    subprocess.run(cmd, cwd=mock_repo_dir, shell=True, check=True)

async def trigger_scan(repo):
    async with AsyncSessionLocal() as db:
        import tempfile
        from app.api.routes.admin import fetch_missing_commits
        
        bare_repo_dir = tempfile.mkdtemp(prefix="gitflow_bare_")
        subprocess.run(["git", "clone", "--bare", repo.url, bare_repo_dir], check=True)
        
        # Get latest SHA
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=mock_repo_dir, capture_output=True, text=True, check=True)
        sha = result.stdout.strip()
        
        print(f"Scanning {sha}...")
        
        from app.database.models import Commit, Scan
        commit = Commit(repository_id=repo.id, hash=sha, message="Test commit")
        db.add(commit)
        await db.commit()
        await db.refresh(commit)
        
        scan = Scan(commit_id=commit.id, status="QUEUED")
        db.add(scan)
        await db.commit()
        
        await run_scan(scan.id, bare_repo_dir)

async def get_audit_report(repo_id, scan_id, user):
    async with AsyncSessionLocal() as db:
        audit = await get_scan_audit(repo_id, scan_id, user, db)
        return audit

async def main():
    user, repo = await setup_db()
    print("DB setup complete.")
    
    # COMMIT A: Baseline
    run_git('echo %RANDOM% > test_file.txt && echo Del > to_delete.txt && git add test_file.txt to_delete.txt && git commit -m "chore: Commit A"')
    await trigger_scan(repo)
    
    # COMMIT B: Issue
    run_git('echo AWS_KEY = "AKIA1234567890ABCDEF" > test_secrets.py && git add test_secrets.py && git commit -m "feat: Commit B"')
    await trigger_scan(repo)
    
    # COMMIT C: Fix
    run_git('echo AWS_KEY = os.getenv("AWS_KEY") > test_secrets.py && git add test_secrets.py && git commit -m "fix: Commit C"')
    await trigger_scan(repo)
    
    # COMMIT D: Harmless + Rename + Delete + Add
    # Modifying test_secrets.py, Renaming test_file.txt -> renamed.txt, Adding new.txt, Deleting some file? Let's just create a temp file in A and delete it in D.
    run_git('git rm to_delete.txt && git mv test_file.txt renamed.txt && echo # comment >> test_secrets.py && echo New file > new.txt && git add renamed.txt test_secrets.py new.txt && git commit -m "docs: Commit D"')
    await trigger_scan(repo)
    
    async with AsyncSessionLocal() as db:
        scans = (await db.execute(select(Scan).join(Commit).where(Commit.repository_id == repo.id).order_by(Scan.completed_at.asc()))).scalars().all()
        
    for scan in scans:
        audit = await get_audit_report(repo.id, scan.id, user)
        print(f"\n{'='*50}\nTEST REPORT FOR: {audit['commit_sha'][:7]} ({audit['message']})\n{'='*50}")
        print(f"Previous SHA: {audit['previous_commit']['short_sha'] if audit['previous_commit'] else 'None'}")
        print(f"Files changed: {len(audit['changes'])}")
        for c in audit['changes']:
            print(f"  - [{c['status']}] {c.get('old_path') + ' -> ' if c.get('old_path') else ''}{c['file']} (+{c['additions']}/-{c['deletions']})")
            if c.get('patch'): print(f"    Patch included: {len(c['patch'])} bytes")
        print(f"Findings: {len(audit['findings'])}")
        for f in audit['findings']:
            print(f"  - [{f['status']}] {f['title']} in {f['file_path']}:{f.get('line_number')}")
        print(f"Previous score: {audit['previous_score']}")
        print(f"Current score: {audit['risk_score']}")
        print(f"Score delta: {audit['score_delta']}")
        print(f"Generated human summary:\n{audit['human_summary']}\n")
        print(f"Score Explanation:\n{audit['score_explanation']}")

asyncio.run(main())
