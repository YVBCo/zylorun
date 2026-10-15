"""Automated regression tests for server-side PDF generation and export endpoint."""

import io
import json
import pytest
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.models import Base, User, Repository, Commit, Scan, Finding, RiskScore
from app.services.pdf_report import generate_pdf_report


def test_pdf_generation_bytes_and_structure():
    """Verify that generate_pdf_report creates a valid, compact, professional PDF."""
    findings = [
        {
            "id": 1,
            "title": "Hardcoded API Secret Key",
            "category": "HARDCODED_SECRET",
            "severity": "High",
            "file_path": "backend/app/config.py",
            "line_number": 42,
            "description": "Found API key: sample_api_secret_key_abcdef12345 in configuration.",
            "status": "NEW",
            "classification": "Confirmed secret vulnerability",
            "remediation": "Move credentials to environment variables.",
            "code_snippet": "API_KEY = 'sample_api_secret_key_abcdef12345'",
        },
        {
            "id": 2,
            "title": "SQL Injection in User Lookup",
            "category": "SQL_INJECTION",
            "severity": "Critical",
            "file_path": "backend/app/db.py",
            "line_number": 105,
            "description": "User input concatenated directly into raw SQL query.",
            "status": "NEW",
            "classification": "Confirmed vulnerability",
            "remediation": "Use parameterized queries.",
            "code_snippet": "query = f'SELECT * FROM users WHERE id = {user_id}'",
        },
    ]

    changes = [
        {"file_path": "backend/app/config.py", "status": "MODIFIED", "additions": 10, "deletions": 2},
        {"file_path": "backend/app/db.py", "status": "MODIFIED", "additions": 5, "deletions": 1},
    ]

    impact = {
        "directly_changed_count": 2,
        "shared_dependencies_count": 1,
        "potentially_affected_count": 3,
    }

    coverage = {
        "status": "FULL",
        "scanned_files": 25,
        "scanners": ["SecurityScanner", "SecretScanner"],
    }

    commit = {
        "hash": "a1b2c3d4e5f678901234567890abcdef12345678",
        "short_hash": "a1b2c3d",
        "author_name": "Test Engineer",
        "author_email": "test@example.com",
        "committed_at": "2026-10-13T08:00:00Z",
        "message": "fix(auth): update session handling and database queries",
    }

    pdf_bytes = generate_pdf_report(
        findings=findings,
        changes=changes,
        impact=impact,
        coverage=coverage,
        commit=commit,
        repo_name="4mh24cs167-tech/gitflow",
        risk_score=68,
        previous_score=75,
        score_delta=-7,
    )

    # 1. Check valid PDF header
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # 2. Extract pages using pypdf
    reader = PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)

    # Must be clean, professional, compact (between 1 and 3 pages, NOT 19 pages!)
    assert 1 <= num_pages <= 3, f"Expected 1-3 pages, got {num_pages}"

    # 3. Verify extracted text content
    full_text = "\n".join(page.extract_text() for page in reader.pages)
    assert "GitFlow Security & Engineering Report" in full_text
    assert "4mh24cs167-tech/gitflow" in full_text
    assert "a1b2c3d" in full_text
    assert "Critical" in full_text
    assert "High" in full_text

    # 4. Secret redaction verification
    # The raw string 'sample_api_secret_key_abcdef12345' MUST NOT be visible in the output PDF!
    assert "sample_api_secret_key_abcdef12345" not in full_text
    assert "[REDACTED" in full_text


def test_pdf_report_with_clean_code_and_test_fixtures():
    """Verify that when a repository has 0 actionable production vulnerabilities and only test fixtures:
    1. Executive scorecard shows strictly 0 Critical, 0 High, 0 Medium, 0 Low, 0 Total findings.
    2. Zero Actionable Security Findings Detected banner is shown.
    3. Test fixtures are isolated into a clean, compact audit table.
    4. The PDF remains compact (2 pages, not 19 pages!).
    """
    findings = [
        {
            "id": 1,
            "title": "requests: CVE-2018-18074 (Sample / Test Fixture)",
            "category": "VULNERABLE_DEPENDENCY",
            "severity": "Critical",
            "file_path": "backend/app/benchmark/fixtures.py",
            "line_number": 1,
            "description": "Benchmark fixture simulating historical vulnerable dependency for testing.",
            "status": "NEW",
            "classification": "Intentional test fixture or demonstration example",
            "is_test_fixture": True,
            "remediation": "Test fixture retained for regression testing.",
            "code_snippet": "requests==2.19.1",
        },
        {
            "id": 2,
            "title": "Sample API Secret in test suite",
            "category": "HARDCODED_SECRET",
            "severity": "High",
            "file_path": "backend/tests/test_sample.py",
            "line_number": 10,
            "description": "Sample placeholder credentials in test suite.",
            "status": "NEW",
            "classification": "Intentional test fixture or demonstration example",
            "is_test_fixture": True,
            "remediation": "No action needed for test fixture.",
            "code_snippet": "KEY = 'test_sample_token_xyz'",
        },
    ]

    changes = [
        {"file_path": "backend/app/benchmark/fixtures.py", "status": "MODIFIED", "additions": 2, "deletions": 2},
    ]

    impact = {
        "directly_changed_count": 1,
        "shared_dependencies_count": 0,
        "potentially_affected_count": 0,
    }

    coverage = {
        "status": "FULL",
        "scanned_files": 45,
        "scanners": ["SecurityScanner", "SecretScanner", "DependencyScanner"],
    }

    commit = {
        "hash": "c0f6625a45df9e2a79364888c0118c75377d7083",
        "short_hash": "c0f6625",
        "author_name": "Senior Engineer",
        "author_email": "dev@example.com",
        "committed_at": "2026-10-13T09:00:00Z",
        "message": "chore: benchmark ground truth validation",
    }

    pdf_bytes = generate_pdf_report(
        findings=findings,
        changes=changes,
        impact=impact,
        coverage=coverage,
        commit=commit,
        repo_name="4mh24cs167-tech/gitflow",
        risk_score=100,
        previous_score=100,
        score_delta=0,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)

    # Must be compact (<= 3 pages, NOT 10-19 pages!)
    assert 1 <= num_pages <= 3, f"Expected 1-3 pages, got {num_pages}"

    full_text = "\n".join(page.extract_text() for page in reader.pages)

    # Verify Executive Summary cards show Actionable Security Exposures with 0 deductions
    assert "Actionable Security Exposures" in full_text
    assert "Critical" in full_text
    assert "Zero Actionable Security Findings Detected" in full_text
    assert "0 score deduction" in full_text

    # Verify Test Fixtures section exists and exactly 2 pages
    assert "Test & Benchmark Fixtures Audit Trail" in full_text
    assert num_pages == 2


@pytest.mark.asyncio
async def test_pdf_export_endpoint_authenticated():
    """Verify GET /repositories/{id}/scans/{id}/report.pdf endpoint."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_owner", email="owner@test.com", is_active=True, hashed_password="pw")
        repo = Repository(
            id=10,
            name="test-org/test-repo",
            url="https://github.com/test-org/test-repo.git",
            owner_id=1,
            default_branch="main",
            is_public=True,
        )
        commit = Commit(
            id=100,
            repository_id=10,
            hash="11223344556677889900aabbccddeeff11223344",
            message="feat: security patch",
            author_name="Dev Tester",
        )
        scan = Scan(
            id=500,
            commit_id=100,
            status="COMPLETED",
        )
        score = RiskScore(
            scan_id=500,
            score=82,
            score_delta=5,
        )
        finding = Finding(
            scan_id=500,
            fingerprint="fp1234567890abcdef",
            type="HARDCODED_SECRET",
            severity="Medium",
            file_path="src/api.py",
            line_number=12,
            description=json.dumps({
                "message": "Bearer secret_api_key_sample123456 detected",
                "remediation": "Redact secrets",
            }),
        )
        db.add_all([user, repo, commit, scan, score, finding])
        await db.commit()

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    async def override_get_current_user():
        return User(id=1, username="test_owner", is_active=True)

    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Existing scan export
            res = await client.get("/repositories/10/scans/500/report.pdf")
            assert res.status_code == 200
            assert res.headers["content-type"] == "application/pdf"
            assert "attachment;" in res.headers["content-disposition"]
            assert "gitflow-report-test-org_test-repo-1122334.pdf" in res.headers["content-disposition"]
            assert res.content.startswith(b"%PDF-")

            # Verify bytes can be parsed by pypdf
            reader = PdfReader(io.BytesIO(res.content))
            assert len(reader.pages) >= 1
            extracted = reader.pages[0].extract_text()
            assert "GitFlow Security & Engineering Report" in extracted

            # 2. Non-existent scan returns 404
            res_404 = await client.get("/repositories/10/scans/99999/report.pdf")
            assert res_404.status_code == 404
    finally:
        app.dependency_overrides.clear()
