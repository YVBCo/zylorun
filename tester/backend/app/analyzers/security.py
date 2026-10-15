"""Analyzer 2: Security and Secret Analyzer.

Wraps deterministic SAST, secret detection, dependency CVE advisory matching,
and license compliance verification into the Project Hub analyzer interface.
"""

from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer
from app.scanners.universal import UniversalScanner


class SecurityAnalyzer(BaseAnalyzer):
    name = "security_and_secrets"
    version = "1.0.0"
    description = "Deterministic SAST, API secret scanning, dependency CVE matching, and license compliance."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        scanner = UniversalScanner(repo_dir)
        raw_findings = scanner.scan()
        coverage = scanner.coverage

        normalized_findings: List[Dict[str, Any]] = []
        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}

        for f in raw_findings:
            sev = f.get("severity", "Medium")
            if sev in severity_counts:
                severity_counts[sev] += 1

            normalized_findings.append({
                "rule_id": f.get("rule_id", "security_rule"),
                "category": f.get("category", "Vulnerability"),
                "severity": sev,
                "confidence": f.get("confidence", "High"),
                "classification": f.get("classification", "Valid heuristic finding requiring manual verification"),
                "file_path": f.get("file_path", ""),
                "line_number": f.get("line_number"),
                "fingerprint": f.get("fingerprint", ""),
                "title": f.get("title") or f.get("category", "Issue"),
                "description": f.get("message") or f.get("description", ""),
                "evidence": f.get("evidence"),
                "remediation": f.get("remediation"),
                "impact": f.get("impact"),
                "code_snippet": f.get("code_snippet"),
            })

        total_findings = len(normalized_findings)
        summary = (
            f"Security scan identified {total_findings} finding(s) across completed analyzers "
            f"({severity_counts['Critical']} Critical, {severity_counts['High']} High, "
            f"{severity_counts['Medium']} Medium, {severity_counts['Low']} Low)."
        )

        tools_dict = {}
        files_examined = 0
        if coverage and hasattr(coverage, "tools"):
            files_examined = getattr(coverage, "files_examined", 0)
            for tool_k, tool_v in coverage.tools.items():
                tools_dict[tool_k] = {
                    "tool_name": getattr(tool_v, "tool_name", tool_k),
                    "status": getattr(tool_v, "status", "COMPLETED"),
                    "files_scanned": getattr(tool_v, "files_scanned", 0),
                    "duration_seconds": getattr(tool_v, "duration_seconds", 0),
                    "findings_count": getattr(tool_v, "findings_count", 0),
                }

        details = {
            "severity_counts": severity_counts,
            "tools": tools_dict,
            "files_examined": files_examined,
            "overall_status": getattr(coverage, "overall_status", "COMPLETED") if coverage else "COMPLETED",
        }

        limitations = []
        if getattr(coverage, "overall_status", "COMPLETED") == "PARTIAL":
            limitations.append("One or more tool analyzers timed out or could not run to completion.")

        return {
            "status": "COMPLETED",
            "coverage_status": getattr(coverage, "overall_status", "COMPLETED") if coverage else "COMPLETED",
            "files_analyzed": files_examined,
            "summary": summary,
            "findings_count": total_findings,
            "findings": normalized_findings,
            "details": details,
            "limitations": limitations,
        }
