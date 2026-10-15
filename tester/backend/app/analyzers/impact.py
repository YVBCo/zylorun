"""Analyzer 3: Change Impact and Regression Analyzer.

Calculates blast radius, directly changed files, lines, structural function/class changes,
and downstream affected files via reverse dependency import mapping.
"""

from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer
from app.analysis.impact import (
    analyze_commit_changes,
    analyze_structural_changes,
    build_dependency_graph,
    analyze_impact,
)


class ChangeImpactAnalyzer(BaseAnalyzer):
    name = "change_impact"
    version = "1.0.0"
    description = "Determines directly modified code, structural changes, and downstream blast radius."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        changed_files_list = analyze_commit_changes(repo_dir, commit_sha)
        structural = analyze_structural_changes(repo_dir, commit_sha)

        file_paths = [c["file"] for c in changed_files_list]
        dep_graph = build_dependency_graph(repo_dir)
        impact = analyze_impact(file_paths, dep_graph)

        added_structures = structural.get("added_structures", [])
        removed_structures = structural.get("removed_structures", [])
        affected_files = impact.get("potentially_affected_files", [])

        # Determine overall blast radius severity
        if any("auth" in f or "security" in f or "secret" in f for f in file_paths):
            blast_severity = "HIGH"
        elif len(affected_files) > 5 or len(file_paths) > 10 or removed_structures:
            blast_severity = "MEDIUM"
        else:
            blast_severity = "LOW"

        summary = (
            f"Commit directly modifies {len(file_paths)} file(s). "
            f"Structural analysis found {len(added_structures)} added and {len(removed_structures)} removed symbols. "
            f"Downstream dependency graph identified {len(affected_files)} potentially affected files "
            f"(Blast radius: {blast_severity})."
        )

        details = {
            "blast_severity": blast_severity,
            "directly_changed_files": file_paths,
            "added_structures": added_structures,
            "removed_structures": removed_structures,
            "potentially_affected_files": affected_files,
            "changed_files_stats": [
                {
                    "file": c["file"],
                    "status": c["status"],
                    "additions": c["additions"],
                    "deletions": c["deletions"],
                }
                for c in changed_files_list[:50]
            ],
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL",
            "files_analyzed": len(file_paths),
            "summary": summary,
            "findings_count": 0,
            "findings": [],
            "details": details,
            "limitations": [],
        }
