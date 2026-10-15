"""Base interface for all GitFlow Project Hub analyzers."""

import time
from typing import Any, Dict, List, Optional


class BaseAnalyzer:
    name: str = "base_analyzer"
    version: str = "1.0.0"
    description: str = "Base analyzer interface"

    def analyze(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Runs analysis deterministically and returns normalized result dictionary."""
        start_time = time.time()
        try:
            result = self._run(repo_dir, commit_sha, index, **kwargs)
            duration = round(time.time() - start_time, 2)
            result["duration_seconds"] = duration
            result["analyzer_name"] = self.name
            result["analyzer_version"] = self.version
            return result
        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            return {
                "analyzer_name": self.name,
                "analyzer_version": self.version,
                "status": "FAILED",
                "coverage_status": "PARTIAL",
                "files_analyzed": 0,
                "duration_seconds": duration,
                "summary": f"Analyzer failed with error: {str(exc)}",
                "findings_count": 0,
                "findings": [],
                "details": {"error": str(exc)},
                "limitations": [f"Execution failed: {str(exc)}"],
            }

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError
