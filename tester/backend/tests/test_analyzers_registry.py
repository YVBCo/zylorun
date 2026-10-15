"""Tests for all 10 GitFlow Project Hub Analyzers and Central Registry."""

import os
import tempfile
import pytest

from app.analyzers.base import BaseAnalyzer
from app.analyzers.registry import (
    DEFAULT_ANALYZERS,
    get_analyzer,
    list_analyzers,
    run_analyzers,
    resolve_analyzers_for_changes,
)
from app.analyzers.api_contract import ApiContractAnalyzer
from app.analyzers.database import DatabaseMigrationAnalyzer
from app.analyzers.cicd import CicdDeploymentAnalyzer
from app.analyzers.accessibility import UiAccessibilityAnalyzer
from app.analyzers.docs import DocsOnboardingAnalyzer


EXPECTED_ANALYZER_NAMES = [
    "repository_dna",
    "security_and_secrets",
    "change_impact",
    "test_intelligence",
    "code_quality",
    "api_contract",
    "database_migration",
    "cicd_deployment",
    "ui_accessibility",
    "docs_onboarding",
]


def test_registry_registers_all_ten_analyzers():
    """Verifies that all 10 required analyzers are registered with expected interfaces."""
    for name in EXPECTED_ANALYZER_NAMES:
        assert name in DEFAULT_ANALYZERS, f"Analyzer {name} missing from DEFAULT_ANALYZERS"
        analyzer = get_analyzer(name)
        assert analyzer is not None, f"Failed to instantiate {name}"
        assert isinstance(analyzer, BaseAnalyzer)
        assert analyzer.name == name
        assert isinstance(analyzer.version, str)
        assert isinstance(analyzer.description, str)

    listed = list_analyzers()
    assert len(listed) == 10
    listed_names = [a["name"] for a in listed]
    for name in EXPECTED_ANALYZER_NAMES:
        assert name in listed_names


def test_resolve_analyzers_for_changes():
    """Verifies incremental execution routing based on file paths and extensions."""
    # Markdown only
    md_analyzers = resolve_analyzers_for_changes(["README.md"])
    assert "docs_onboarding" in md_analyzers
    assert "database_migration" not in md_analyzers

    # SQL only
    sql_analyzers = resolve_analyzers_for_changes(["schema.sql"])
    assert "database_migration" in sql_analyzers
    assert "ui_accessibility" not in sql_analyzers

    # TSX template
    tsx_analyzers = resolve_analyzers_for_changes(["frontend/src/Button.tsx"])
    assert "ui_accessibility" in tsx_analyzers
    assert "api_contract" in tsx_analyzers

    # CI workflow
    ci_analyzers = resolve_analyzers_for_changes([".github/workflows/ci.yml"])
    assert "cicd_deployment" in ci_analyzers


def test_api_contract_analyzer_routes_and_mismatches():
    """Tests API contract discovery and consumer mismatch detection."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Backend FastAPI routes
        os.makedirs(os.path.join(tmp_dir, "backend", "app"), exist_ok=True)
        with open(os.path.join(tmp_dir, "backend", "app", "routes.py"), "w", encoding="utf-8") as f:
            f.write("""
from fastapi import APIRouter

router = APIRouter()

@router.get("/users/{user_id}")
def get_user(user_id: str):
    return {"id": user_id}

@router.post("/auth/login")
def login(payload: dict):
    return {"token": "xyz"}
""")

        # Frontend client calls (one matching, one wrong method, one missing route)
        os.makedirs(os.path.join(tmp_dir, "frontend", "src"), exist_ok=True)
        with open(os.path.join(tmp_dir, "frontend", "src", "api.ts"), "w", encoding="utf-8") as f:
            f.write("""
import axios from 'axios';

export async function loadUser(id: string) {
    return axios.get(`/users/${id}`);
}

export async function loginAttempt() {
    // Incorrect method: backend expects POST, frontend invokes GET
    return axios.get('/auth/login');
}

export async function nonExistentCall() {
    return axios.delete('/missing/endpoint');
}
""")

        analyzer = ApiContractAnalyzer()
        result = analyzer.analyze(tmp_dir, "commit_123")

        assert result["status"] == "COMPLETED"
        assert result["analyzer_name"] == "api_contract"
        assert "duration_seconds" in result
        assert result["files_analyzed"] >= 2
        assert len(result["details"]["routes"]) >= 2
        assert len(result["details"]["frontend_calls"]) >= 3

        # Check findings
        rule_ids = [f["rule_id"] for f in result["findings"]]
        assert "API-METHOD-MISMATCH" in rule_ids
        assert "API-MISSING-ENDPOINT" in rule_ids

        # Check classification disclosure (verified vs heuristic)
        mismatch_finding = next(f for f in result["findings"] if f["rule_id"] == "API-METHOD-MISMATCH")
        assert "Verified" in mismatch_finding["classification"] or "heuristic" in mismatch_finding["classification"].lower()


def test_database_migration_analyzer_hazards():
    """Tests SQLAlchemy model inspection, dropped column hazards, and safe migration plans."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Model with unindexed foreign key and missing migration
        os.makedirs(os.path.join(tmp_dir, "models"), exist_ok=True)
        with open(os.path.join(tmp_dir, "models", "user.py"), "w", encoding="utf-8") as f:
            f.write("""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(100), nullable=False)
""")

        # Migration dropping a column and adding not null column
        os.makedirs(os.path.join(tmp_dir, "alembic", "versions"), exist_ok=True)
        with open(os.path.join(tmp_dir, "alembic", "versions", "001_rev.py"), "w", encoding="utf-8") as f:
            f.write("""
revision = '001_rev'
down_revision = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('organizations', sa.Column('id', sa.Integer, primary_key=True))
    op.drop_column('organizations', 'legacy_status')
    op.add_column('organizations', sa.Column('tier', sa.String, nullable=False))
""")

        analyzer = DatabaseMigrationAnalyzer()
        result = analyzer.analyze(tmp_dir, "commit_123")

        assert result["status"] == "COMPLETED"
        assert result["analyzer_name"] == "database_migration"
        rule_ids = [f["rule_id"] for f in result["findings"]]

        assert "DB-HAZARD-DROPPED-COL" in rule_ids
        assert "DB-HAZARD-NOT-NULL-ADD" in rule_ids
        assert "DB-HAZARD-UNINDEXED-FK" in rule_ids
        assert "DB-HAZARD-DANGEROUS-CASCADE" in rule_ids

        # Check safe migration plan
        plan = result["details"]["safe_migration_plan"]
        assert "Expand-Contract" in plan["recommended_strategy"]
        assert len(plan["steps"]) >= 2


def test_cicd_deployment_analyzer_workflow_and_docker():
    """Tests CI/CD workflow security, unpinned actions, and Dockerfile root execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Workflow with missing permissions and unpinned action
        os.makedirs(os.path.join(tmp_dir, ".github", "workflows"), exist_ok=True)
        with open(os.path.join(tmp_dir, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
            f.write("""
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build
        run: echo "building"
""")

        # Dockerfile running as root and unpinned image
        with open(os.path.join(tmp_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write("""
FROM python:latest
WORKDIR /app
COPY . /app
CMD ["python", "main.py"]
""")

        analyzer = CicdDeploymentAnalyzer()
        result = analyzer.analyze(tmp_dir, "commit_123")

        assert result["status"] == "COMPLETED"
        assert result["analyzer_name"] == "cicd_deployment"
        rule_ids = [f["rule_id"] for f in result["findings"]]

        assert "CICD-MISSING-PERMISSIONS" in rule_ids
        assert "CICD-UNPINNED-ACTION" in rule_ids
        assert "CICD-NO-TEST-STEP" in rule_ids
        assert "DOCKER-ROOT-USER" in rule_ids
        assert "DOCKER-UNPINNED-IMAGE" in rule_ids


def test_ui_accessibility_analyzer_wcag():
    """Tests WCAG static analysis on frontend templates."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # TSX template with missing alt, button aria-label, input label, and interactive div
        os.makedirs(os.path.join(tmp_dir, "src"), exist_ok=True)
        with open(os.path.join(tmp_dir, "src", "Dashboard.tsx"), "w", encoding="utf-8") as f:
            f.write("""
export default function Dashboard() {
    return (
        <div>
            <img src="/avatar.png" />
            <button onClick={() => {}}><svg /></button>
            <input type="text" placeholder="Search..." />
            <div onClick={() => console.log('clicked')}>Click Me</div>
        </div>
    );
}
""")

        # HTML file missing lang
        with open(os.path.join(tmp_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>Test</title></head><body></body></html>")

        analyzer = UiAccessibilityAnalyzer()
        result = analyzer.analyze(tmp_dir, "commit_123")

        assert result["status"] == "COMPLETED"
        assert result["analyzer_name"] == "ui_accessibility"
        rule_ids = [f["rule_id"] for f in result["findings"]]

        assert "A11Y-IMG-NO-ALT" in rule_ids
        assert "A11Y-BUTTON-NO-NAME" in rule_ids
        assert "A11Y-FORM-INPUT-NO-LABEL" in rule_ids
        assert "A11Y-INTERACTIVE-ELEMENT" in rule_ids
        assert "A11Y-HTML-NO-LANG" in rule_ids
        assert "accessibility_score" in result["details"]


def test_docs_onboarding_analyzer():
    """Tests documentation analysis, broken relative links, and undocumented env vars."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Python file accessing undocumented env var
        os.makedirs(os.path.join(tmp_dir, "app"), exist_ok=True)
        with open(os.path.join(tmp_dir, "app", "config.py"), "w", encoding="utf-8") as f:
            f.write("""
import os
SECRET_TOKEN = os.getenv("APP_SUPER_SECRET_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
""")

        # README referencing non-existent file and broken link
        with open(os.path.join(tmp_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("""
# Project
Check out [Architecture Guide](./docs/non_existent.md).
Copy `.env.example` before starting.
Configured with `DATABASE_URL`.
""")

        analyzer = DocsOnboardingAnalyzer()
        result = analyzer.analyze(tmp_dir, "commit_123")

        assert result["status"] == "COMPLETED"
        assert result["analyzer_name"] == "docs_onboarding"
        rule_ids = [f["rule_id"] for f in result["findings"]]

        assert "DOCS-BROKEN-RELATIVE-LINK" in rule_ids
        assert "DOCS-MISSING-REFERENCED-FILE" in rule_ids
        assert "DOCS-UNDOCUMENTED-ENV-VAR" in rule_ids

        # Onboarding guide data synthesized
        guide = result["details"]["onboarding_guide"]
        assert "installation_steps" in guide
        assert "development_commands" in guide


def test_run_analyzers_end_to_end():
    """Tests orchestrating all 10 analyzers with run_analyzers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create minimal python app with readme
        os.makedirs(os.path.join(tmp_dir, "app"), exist_ok=True)
        with open(os.path.join(tmp_dir, "app", "main.py"), "w", encoding="utf-8") as f:
            f.write("def hello(): return 'world'")

        with open(os.path.join(tmp_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Hello World\nWelcome to tester.")

        # Run all 10 analyzers
        results = run_analyzers(tmp_dir, "commit_all")

        assert results["overall_status"] in ["COMPLETED", "PARTIAL"]
        assert len(results["analyzers_executed"]) == 10
        assert "repository_dna" in results["analyzers"]
        assert "security_and_secrets" in results["analyzers"]
        assert "change_impact" in results["analyzers"]
        assert "test_intelligence" in results["analyzers"]
        assert "code_quality" in results["analyzers"]
        assert "api_contract" in results["analyzers"]
        assert "database_migration" in results["analyzers"]
        assert "cicd_deployment" in results["analyzers"]
        assert "ui_accessibility" in results["analyzers"]
        assert "docs_onboarding" in results["analyzers"]

        # Run with requested_analyzers filter
        filtered_results = run_analyzers(
            tmp_dir,
            "commit_filtered",
            requested_analyzers=["api_contract", "docs_onboarding"]
        )
        assert len(filtered_results["analyzers_executed"]) == 2
        assert "api_contract" in filtered_results["analyzers"]
        assert "docs_onboarding" in filtered_results["analyzers"]
        assert "cicd_deployment" not in filtered_results["analyzers"]
