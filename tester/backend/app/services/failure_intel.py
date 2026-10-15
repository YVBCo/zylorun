"""Production Failure & Regression Intelligence Service for GitFlow Project Hub.

Provides:
- Build and CI failure log parsing (GitHub Actions, pytest, npm, Docker, compiler output)
- Extraction of failed pipeline steps and stack trace frames
- Cross-referencing against commit changed files to identify regression origin
- Root cause categorization and confidence ranking
- Step-by-step recommended investigation order and local reproduction commands
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Patterns for extracting traces and errors
_PY_TRACE_RE = re.compile(r'File ["\']([^"\']+)["\'], line (\d+)(?:, in (\w+))?')
_JS_TRACE_RE = re.compile(r'at (?:.*?\()?([a-zA-Z0-9_\-\.\/\\]+\.(?:ts|tsx|js|jsx|vue)):(\d+):(\d+)\)?')
_COMPILER_RE = re.compile(r'([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+):(\d+):(?:\d+:)?\s*(error|fatal error|FAILED):\s*(.+)', re.IGNORECASE)
_PYTEST_FAIL_RE = re.compile(r'FAILED\s+([a-zA-Z0-9_\-\.\/\\]+\.py)::([a-zA-Z0-9_]+)')
_GITHUB_ACTION_ERR_RE = re.compile(r'##\[error\](.*)')
_DOCKER_ERR_RE = re.compile(r'Step \d+/\d+\s*:\s*(.*)\s*--->\s*Running.*?(The command .* returned a non-zero code: \d+)', re.S)


class FailureIntelService:
    """Production Failure & Regression Intelligence analyzer."""

    def __init__(self) -> None:
        pass

    def _extract_failed_steps(self, log: str) -> List[Dict[str, Any]]:
        """Identify discrete failed CI/build steps and stages from the log."""
        steps: List[Dict[str, Any]] = []

        # Check for GitHub Actions error annotations
        for match in _GITHUB_ACTION_ERR_RE.finditer(log):
            msg = match.group(1).strip()
            if msg:
                steps.append({
                    "stage": "GitHub Actions",
                    "step_name": "Pipeline Step",
                    "detail": msg[:200],
                })

        # Check for pytest failed test suites
        for match in _PYTEST_FAIL_RE.finditer(log):
            test_file, test_fn = match.groups()
            steps.append({
                "stage": "Test Suite (pytest)",
                "step_name": f"{test_file}::{test_fn}",
                "detail": f"Test assertion or execution failed in {test_fn}",
            })

        # Check for Docker step failures
        for match in _DOCKER_ERR_RE.finditer(log):
            step_cmd, err_desc = match.groups()
            steps.append({
                "stage": "Container Build (Docker)",
                "step_name": step_cmd.strip()[:100],
                "detail": err_desc.strip(),
            })

        # Fallback: scan for generic exit codes or error lines if no structured steps matched
        if not steps:
            for line in log.splitlines():
                if any(w in line.lower() for w in ("command failed with exit code", "process completed with exit code", "npm err!", "yarn run failed")):
                    steps.append({
                        "stage": "Process Execution",
                        "step_name": "Build Command",
                        "detail": line.strip()[:200],
                    })
                    if len(steps) >= 5:
                        break

        return steps

    def _categorize_error(self, message: str) -> Tuple[str, float]:
        """Classify error string into a root-cause category with base confidence."""
        msg_lower = message.lower()

        if "syntaxerror" in msg_lower or "unexpected token" in msg_lower:
            return "SYNTAX_ERROR", 0.95
        elif "modulenotfounderror" in msg_lower or "importerror" in msg_lower or "cannot find module" in msg_lower:
            return "IMPORT_ERROR", 0.90
        elif "assertionerror" in msg_lower or "assert " in msg_lower:
            return "ASSERTION_FAILURE", 0.85
        elif "typeerror" in msg_lower or "attributeerror" in msg_lower or "undefined is not a function" in msg_lower:
            return "TYPE_ERROR", 0.80
        elif "connection refused" in msg_lower or "operationalerror" in msg_lower or "relation" in msg_lower and "does not exist" in msg_lower:
            return "DATABASE_MIGRATION_OR_CONN", 0.85
        elif "timed out" in msg_lower or "timeoutexpired" in msg_lower:
            return "TIMEOUT", 0.75
        elif "permission denied" in msg_lower or "eacces" in msg_lower:
            return "PERMISSION_DENIED", 0.80
        elif "package not found" in msg_lower or "no matching distribution" in msg_lower:
            return "DEPENDENCY_RESOLUTION", 0.85

        return "GENERAL_EXECUTION_FAILURE", 0.50

    def analyze_build_or_ci_failure(
        self,
        failure_log: str,
        changed_files: Optional[List[str]] = None,
        commit_sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze a CI/build failure log, pinpoint regressions, and rank root causes.

        Args:
            failure_log: Raw log output from CI/CD pipeline or build tool.
            changed_files: Optional list of files modified in the offending commit/PR.
            commit_sha: Optional SHA identifier.

        Returns:
            Structured intelligence report with ranked causes and investigation steps.
        """
        if not failure_log or not failure_log.strip():
            return {
                "status": "NO_LOG_PROVIDED",
                "total_errors_detected": 0,
                "failed_steps": [],
                "correlated_changed_files": [],
                "ranked_root_causes": [],
                "recommended_investigation_order": ["Provide build failure logs for intelligence triage."],
                "reproduction_command": "",
            }

        normalized_changed_files = [f.replace("\\", "/").lower() for f in (changed_files or [])]

        failed_steps = self._extract_failed_steps(failure_log)
        detected_frames: List[Dict[str, Any]] = []

        # 1. Parse Python stack traces
        for match in _PY_TRACE_RE.finditer(failure_log):
            f_path, line_no, func = match.groups()
            norm_f = f_path.replace("\\", "/")
            detected_frames.append({
                "file": norm_f,
                "line": int(line_no),
                "function": func or "unknown",
                "language": "python",
            })

        # 2. Parse JS/TS stack traces
        for match in _JS_TRACE_RE.finditer(failure_log):
            f_path, line_no, col = match.groups()
            norm_f = f_path.replace("\\", "/")
            detected_frames.append({
                "file": norm_f,
                "line": int(line_no),
                "function": "unknown",
                "language": "javascript/typescript",
            })

        # 3. Parse compiler/linter error lines
        for match in _COMPILER_RE.finditer(failure_log):
            f_path, line_no, err_type, err_msg = match.groups()
            norm_f = f_path.replace("\\", "/")
            detected_frames.append({
                "file": norm_f,
                "line": int(line_no),
                "function": "global",
                "language": "compiler",
                "error_detail": err_msg.strip(),
            })

        # Cross-reference frames with changed files
        correlated_files: List[str] = []
        raw_causes: List[Dict[str, Any]] = []

        # Find error descriptions from the lines immediately following stack traces
        error_lines = [
            line.strip() for line in failure_log.splitlines()
            if any(term in line.lower() for term in ("error:", "exception:", "failed:", "fatal:"))
        ]
        primary_error_summary = error_lines[-1] if error_lines else "Pipeline step exited with non-zero status"
        cat, base_confidence = self._categorize_error(primary_error_summary)

        # Build candidates from frames (prioritize most recent frames)
        for frame in reversed(detected_frames):
            file_name = frame["file"]
            is_correlated = any(
                file_name.endswith(chg) or chg.endswith(file_name) or os.path.basename(file_name) == os.path.basename(chg)
                for chg in normalized_changed_files
            )
            if is_correlated and file_name not in correlated_files:
                correlated_files.append(file_name)

            confidence = base_confidence + (0.15 if is_correlated else 0.0)
            confidence = min(0.99, confidence)

            raw_causes.append({
                "category": cat,
                "summary": frame.get("error_detail") or primary_error_summary,
                "file": file_name,
                "line": frame["line"],
                "correlated_with_change": is_correlated,
                "confidence": round(confidence, 2),
            })

        # Fallback if no specific file frames were extracted
        if not raw_causes:
            raw_causes.append({
                "category": cat,
                "summary": primary_error_summary,
                "file": "Pipeline/Build Configuration",
                "line": 1,
                "correlated_with_change": False,
                "confidence": round(base_confidence, 2),
            })

        # Deduplicate and sort by confidence descending
        unique_causes: Dict[str, Dict[str, Any]] = {}
        for c in raw_causes:
            key = f"{c['file']}:{c['line']}:{c['category']}"
            if key not in unique_causes or c["confidence"] > unique_causes[key]["confidence"]:
                unique_causes[key] = c

        sorted_causes = sorted(unique_causes.values(), key=lambda x: (x["correlated_with_change"], x["confidence"]), reverse=True)
        ranked_causes = []
        for idx, item in enumerate(sorted_causes[:5], start=1):
            item["rank"] = idx
            ranked_causes.append(item)

        # Generate prioritized recommendations
        recommendations: List[str] = []
        top_cause = ranked_causes[0] if ranked_causes else None

        if top_cause and top_cause["file"] != "Pipeline/Build Configuration":
            recom_1 = f"1. Inspect `{top_cause['file']}` at line {top_cause['line']} where `{top_cause['category']}` occurred."
            if top_cause["correlated_with_change"]:
                recom_1 += " (Directly modified in recent changes)."
            recommendations.append(recom_1)

            if top_cause["category"] == "IMPORT_ERROR":
                recommendations.append("2. Verify module export signatures and ensure required dependencies are listed in manifest.")
            elif top_cause["category"] == "ASSERTION_FAILURE":
                recommendations.append("2. Review unit test assertions and mock fixture expectations against recent API changes.")
            elif top_cause["category"] == "SYNTAX_ERROR":
                recommendations.append("2. Validate syntax using local linter or language compiler before re-committing.")
            else:
                recommendations.append("2. Trace recent git commit history touching this subsystem to verify breaking changes.")
        else:
            recommendations.append(f"1. Check CI build command and environment logs for '{cat}'.")
            recommendations.append("2. Verify environment secrets, service dependencies, or Dockerfile base images.")

        # Suggest local reproduction command
        repro_cmd = ""
        test_frame = next((f for f in detected_frames if "test" in f["file"].lower()), None)
        if test_frame:
            if test_frame["language"] == "python":
                repro_cmd = f"pytest {test_frame['file']}"
            else:
                repro_cmd = f"npm test -- {test_frame['file']}"
        elif ranked_causes and ranked_causes[0]["file"] != "Pipeline/Build Configuration":
            if ranked_causes[0]["file"].endswith(".py"):
                repro_cmd = f"pytest {ranked_causes[0]['file']}"
            else:
                repro_cmd = "pytest tests/"
        else:
            repro_cmd = "pytest tests/"

        recommendations.append(f"3. Run local reproduction: `{repro_cmd}`")

        return {
            "status": "ANALYZED",
            "total_errors_detected": len(ranked_causes),
            "failed_steps": failed_steps,
            "correlated_changed_files": correlated_files,
            "ranked_root_causes": ranked_causes,
            "recommended_investigation_order": recommendations,
            "reproduction_command": repro_cmd,
        }


# Global singleton instance
failure_intel_service = FailureIntelService()
