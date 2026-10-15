"""Analyzer 4: Test Intelligence Analyzer.

Discovers test frameworks, test-to-source file mappings, untested critical modules,
coverage gaps, and execution configuration.
"""

import os
import re
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index


class TestIntelligenceAnalyzer(BaseAnalyzer):
    name = "test_intelligence"
    version = "1.0.0"
    description = "Discovers test frameworks, test-to-source mappings, and untested critical components."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        frameworks = index.get("frameworks", [])
        test_files = index.get("test_files", [])
        py_routes = index.get("api_routes", [])

        # Detect test runner commands
        detected_runners = []
        if "pytest" in frameworks or any(f.endswith(".py") for f in test_files):
            detected_runners.append({"framework": "pytest", "command": "pytest backend/tests"})
        if any(f.endswith((".ts", ".tsx", ".js", ".jsx")) for f in test_files) or "Vite" in frameworks:
            detected_runners.append({"framework": "vitest / npm test", "command": "npm test"})

        # Map tests to source modules
        source_to_test_map = {}
        for tf in test_files:
            base_name = os.path.basename(tf)
            clean_name = re.sub(r"^(test_|tests_)|(_test|\.test|\.spec)\.[a-z0-9]+$", "", base_name)
            source_to_test_map[clean_name] = tf

        # Identify untested critical components
        critical_untested = []
        for route in py_routes:
            route_f = route["file"]
            base = os.path.splitext(os.path.basename(route_f))[0]
            if base not in source_to_test_map and f"test_{base}" not in [os.path.basename(t) for t in test_files]:
                if any(x in route["path"] for x in ["auth", "token", "password", "delete", "admin", "webhook"]):
                    critical_untested.append({
                        "file": route_f,
                        "endpoint": f"{route['method']} {route['path']}",
                        "reason": "Sensitive endpoint without direct dedicated test file match",
                    })

        summary = (
            f"Test suite contains {len(test_files)} test file(s) across {len(detected_runners)} detected framework(s). "
            f"Identified {len(source_to_test_map)} mapped test suites. "
            f"{len(critical_untested)} sensitive API component(s) flagged for regression test verification."
        )

        details = {
            "test_files_count": len(test_files),
            "test_files": test_files[:30],
            "detected_runners": detected_runners,
            "source_to_test_map": source_to_test_map,
            "critical_untested": critical_untested[:10],
            "recommendations": [
                "Ensure integration tests cover authenticated and error branches.",
                "Maintain deterministic regression tests for all critical API endpoints.",
            ],
        }

        limitations = []
        if not test_files:
            limitations.append("No automated test files matching common patterns (test_*.py, *.test.ts) were discovered.")

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if test_files else "PARTIAL",
            "files_analyzed": len(test_files),
            "summary": summary,
            "findings_count": len(critical_untested),
            "findings": [
                {
                    "rule_id": "TEST-GAP-001",
                    "category": "Quality",
                    "severity": "Medium",
                    "confidence": "Medium",
                    "classification": "Valid heuristic finding requiring manual verification",
                    "file_path": item["file"],
                    "line_number": None,
                    "title": f"Test Coverage Gap: {item['endpoint']}",
                    "description": f"Endpoint {item['endpoint']} in {item['file']} has no matching test file pattern.",
                    "evidence": item["reason"],
                    "remediation": f"Add regression tests targeting {item['endpoint']}.",
                }
                for item in critical_untested[:5]
            ],
            "details": details,
            "limitations": limitations,
        }
