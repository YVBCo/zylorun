"""Central Registry and Orchestrator for GitFlow Project Hub Analyzers.

Registers all 10 core analyzers:
1. repository_dna
2. security_and_secrets
3. change_impact
4. test_intelligence
5. code_quality
6. api_contract
7. database_migration
8. cicd_deployment
9. ui_accessibility
10. docs_onboarding

Provides get_analyzer(), list_analyzers(), and run_analyzers() supporting
incremental execution based on changed file extensions.
"""

import os
import time
from typing import Any, Dict, List, Optional, Set, Type, Union

from app.analyzers.base import BaseAnalyzer
from app.analyzers.dna import RepositoryDNAAnalyzer
from app.analyzers.security import SecurityAnalyzer
from app.analyzers.impact import ChangeImpactAnalyzer
from app.analyzers.test_intel import TestIntelligenceAnalyzer
from app.analyzers.quality import CodeQualityAnalyzer
from app.analyzers.api_contract import ApiContractAnalyzer
from app.analyzers.database import DatabaseMigrationAnalyzer
from app.analyzers.cicd import CicdDeploymentAnalyzer
from app.analyzers.accessibility import UiAccessibilityAnalyzer
from app.analyzers.docs import DocsOnboardingAnalyzer
from app.analysis.indexer import build_repository_index

# Registered analyzer classes
DEFAULT_ANALYZERS: Dict[str, Type[BaseAnalyzer]] = {
    "repository_dna": RepositoryDNAAnalyzer,
    "security_and_secrets": SecurityAnalyzer,
    "change_impact": ChangeImpactAnalyzer,
    "test_intelligence": TestIntelligenceAnalyzer,
    "code_quality": CodeQualityAnalyzer,
    "api_contract": ApiContractAnalyzer,
    "database_migration": DatabaseMigrationAnalyzer,
    "cicd_deployment": CicdDeploymentAnalyzer,
    "ui_accessibility": UiAccessibilityAnalyzer,
    "docs_onboarding": DocsOnboardingAnalyzer,
}

# Extension / pattern affinity for incremental execution
ANALYZER_EXTENSIONS_MAP: Dict[str, Set[str]] = {
    "repository_dna": {"*"},  # Always relevant for architecture topology
    "security_and_secrets": {"*"},  # Always relevant for vulnerability checks
    "change_impact": {"*"},  # Always relevant for blast radius
    "test_intelligence": {".py", ".ts", ".tsx", ".js", ".jsx", ".test", ".spec"},
    "code_quality": {".py", ".ts", ".tsx", ".js", ".jsx"},
    "api_contract": {".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".html"},
    "database_migration": {".py", ".sql", "alembic", "migration", "model"},
    "cicd_deployment": {".yml", ".yaml", "dockerfile", "docker-compose", "render.yaml", "vercel.json", "procfile", "netlify.toml"},
    "ui_accessibility": {".tsx", ".jsx", ".html", ".vue", ".svelte"},
    "docs_onboarding": {".md", ".rst", ".txt", ".env", ".env.example", "readme"},
}

# Instantiated analyzers cache
_ANALYZER_INSTANCES: Dict[str, BaseAnalyzer] = {}


def register_analyzer(name: str, analyzer_cls_or_instance: Union[Type[BaseAnalyzer], BaseAnalyzer]) -> None:
    """Registers or overrides an analyzer in the central registry."""
    if isinstance(analyzer_cls_or_instance, type):
        DEFAULT_ANALYZERS[name] = analyzer_cls_or_instance
        if name in _ANALYZER_INSTANCES:
            del _ANALYZER_INSTANCES[name]
    elif isinstance(analyzer_cls_or_instance, BaseAnalyzer):
        _ANALYZER_INSTANCES[name] = analyzer_cls_or_instance
        DEFAULT_ANALYZERS[name] = type(analyzer_cls_or_instance)


def get_analyzer(name: str) -> Optional[BaseAnalyzer]:
    """Retrieves an instantiated analyzer by name."""
    if name in _ANALYZER_INSTANCES:
        return _ANALYZER_INSTANCES[name]

    cls = DEFAULT_ANALYZERS.get(name)
    if cls:
        instance = cls()
        _ANALYZER_INSTANCES[name] = instance
        return instance

    return None


def list_analyzers() -> List[Dict[str, Any]]:
    """Returns metadata for all 10 registered analyzers."""
    result = []
    for name in DEFAULT_ANALYZERS:
        analyzer = get_analyzer(name)
        if analyzer:
            result.append({
                "name": analyzer.name,
                "version": analyzer.version,
                "description": analyzer.description,
            })
    return result


def resolve_analyzers_for_changes(changed_files: List[str]) -> List[str]:
    """Determines the minimal set of analyzers to execute based on changed files and extensions."""
    if not changed_files:
        return list(DEFAULT_ANALYZERS.keys())

    selected: Set[str] = set()

    for file_path in changed_files:
        norm_p = file_path.replace("\\", "/").lower()
        _, ext = os.path.splitext(norm_p)

        for analyzer_name, patterns in ANALYZER_EXTENSIONS_MAP.items():
            if "*" in patterns:
                selected.add(analyzer_name)
                continue

            for pat in patterns:
                if pat.startswith(".") and ext == pat:
                    selected.add(analyzer_name)
                    break
                elif not pat.startswith(".") and pat in norm_p:
                    selected.add(analyzer_name)
                    break

    # Preserve consistent ordering matching DEFAULT_ANALYZERS
    return [name for name in DEFAULT_ANALYZERS if name in selected]


def run_analyzers(
    repo_dir: str,
    commit_sha: str,
    requested_analyzers: Optional[List[str]] = None,
    index: Optional[Dict[str, Any]] = None,
    changed_files: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Executes registered analyzers deterministically with shared indexing and incremental filtering.

    Args:
        repo_dir: Path to the target git repository.
        commit_sha: Revision commit SHA.
        requested_analyzers: Optional explicit list of analyzer names to run.
        index: Precomputed repository index; if None, built once and shared across analyzers.
        changed_files: Optional list of modified file paths for incremental execution.
        **kwargs: Additional options forwarded to analyzers.

    Returns:
        Consolidated dictionary with overall summary, individual analyzer results, and findings.
    """
    start_time = time.time()

    # 1. Build or reuse shared index
    if not index:
        index = build_repository_index(repo_dir, commit_sha)

    # 2. Determine which analyzers to execute
    if requested_analyzers is not None:
        target_names = [name for name in requested_analyzers if name in DEFAULT_ANALYZERS]
    elif changed_files is not None:
        target_names = resolve_analyzers_for_changes(changed_files)
    else:
        target_names = list(DEFAULT_ANALYZERS.keys())

    analyzers_results: Dict[str, Any] = {}
    all_findings: List[Dict[str, Any]] = []
    total_files_analyzed = 0
    failed_analyzers: List[str] = []

    # 3. Run each target analyzer
    for name in target_names:
        analyzer = get_analyzer(name)
        if not analyzer:
            continue

        try:
            res = analyzer.analyze(repo_dir, commit_sha, index=index, **kwargs)
            analyzers_results[name] = res

            if res.get("status") == "FAILED":
                failed_analyzers.append(name)

            findings_list = res.get("findings", [])
            all_findings.extend(findings_list)
            total_files_analyzed = max(total_files_analyzed, res.get("files_analyzed", 0))

        except Exception as exc:
            failed_analyzers.append(name)
            analyzers_results[name] = {
                "analyzer_name": name,
                "analyzer_version": "1.0.0",
                "status": "FAILED",
                "coverage_status": "PARTIAL",
                "files_analyzed": 0,
                "duration_seconds": 0.0,
                "summary": f"Execution crashed: {str(exc)}",
                "findings_count": 0,
                "findings": [],
                "details": {"error": str(exc)},
                "limitations": [str(exc)],
            }

    duration = round(time.time() - start_time, 2)

    # 4. Formulate consolidated status and summary
    if failed_analyzers and len(failed_analyzers) == len(target_names):
        overall_status = "FAILED"
    elif failed_analyzers:
        overall_status = "PARTIAL"
    else:
        overall_status = "COMPLETED"

    summary = (
        f"Executed {len(target_names)} analyzer(s) in {duration}s. "
        f"Found {len(all_findings)} total finding(s) across {total_files_analyzed} file(s) analyzed. "
        f"Overall status: {overall_status}."
    )

    return {
        "commit_sha": commit_sha,
        "overall_status": overall_status,
        "total_findings": len(all_findings),
        "files_analyzed": total_files_analyzed,
        "duration_seconds": duration,
        "summary": summary,
        "analyzers_executed": target_names,
        "failed_analyzers": failed_analyzers,
        "analyzers": analyzers_results,
        "findings": all_findings,
    }
