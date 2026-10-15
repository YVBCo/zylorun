"""Analyzer 1: Repository DNA Analyzer.

Maps repository architecture, detected stacks, project topology, entry points,
and module structure into an evidence-backed navigable repository map.
"""

from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index


class RepositoryDNAAnalyzer(BaseAnalyzer):
    name = "repository_dna"
    version = "1.0.0"
    description = "Analyzes repository architecture, stack DNA, entry points, and project topology."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        file_count = index.get("file_count", 0)
        languages = index.get("languages", {})
        frameworks = index.get("frameworks", [])
        entry_points = index.get("entry_points", [])
        api_routes = index.get("api_routes", [])
        db_models = index.get("database_models", [])
        test_files = index.get("test_files", [])
        ci_cd_files = index.get("ci_cd_files", [])
        dependencies = index.get("dependencies", [])

        # Categorize layers
        layers = {
            "presentation": [ep for ep in entry_points if any(x in ep for x in ["frontend", "src", "html", "tsx", "jsx"])],
            "api_routing": [r["file"] for r in api_routes[:15]],
            "database_orm": [m["file"] for m in db_models[:15]],
            "test_suite": test_files[:15],
            "ci_cd_deployment": ci_cd_files,
        }

        # Primary language
        primary_lang = list(languages.keys())[0] if languages else "Unknown"

        summary = (
            f"Repository contains {file_count} files across {len(languages)} detected languages "
            f"(Primary: {primary_lang}). Identified {len(frameworks)} frameworks and libraries "
            f"({', '.join(frameworks[:5]) if frameworks else 'None'}), {len(api_routes)} API routes, "
            f"and {len(db_models)} database models."
        )

        details = {
            "primary_language": primary_lang,
            "languages": languages,
            "frameworks": frameworks,
            "entry_points": entry_points,
            "layers": layers,
            "dependency_count": len(dependencies),
            "routes_count": len(api_routes),
            "models_count": len(db_models),
            "tests_count": len(test_files),
        }

        limitations = []
        if file_count == 0:
            limitations.append("Repository working directory contains no readable files.")
        if not frameworks:
            limitations.append("No known framework manifests (package.json, requirements.txt, pyproject.toml) detected.")

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if file_count > 0 else "UNSUPPORTED",
            "files_analyzed": file_count,
            "summary": summary,
            "findings_count": 0,
            "findings": [],
            "details": details,
            "limitations": limitations,
        }
