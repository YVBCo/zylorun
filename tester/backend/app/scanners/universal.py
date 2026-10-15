import os
import re
import hashlib
import time
from typing import List, Dict, Any, Optional

from app.scanners.models import FindingItem, ToolCoverage, ScanCoverage
from app.scanners.sast import run_sast_scan
from app.scanners.secrets import run_secret_scan
from app.scanners.dependencies import run_dependency_scan
from app.scanners.licenses import run_license_scan
from app.scanners.quality import run_quality_scan

def generate_fingerprint(
    rule_or_category: str,
    file_path: str,
    location: str,
    message_or_rule: str,
    message: Optional[str] = None,
    category: Optional[str] = None,
    code_snippet: Optional[str] = None
) -> str:
    """Deterministic, line-shift resilient fingerprint generator.
    Compatible with both (rule, file_path, location, message) and
    (category, file_path, location, rule, message) call signatures.
    """
    if message is not None:
        cat = category or rule_or_category
        rule = message_or_rule
        msg = message
    else:
        cat = category or "Vulnerability"
        rule = rule_or_category
        msg = message_or_rule

    normalized_path = file_path.replace("\\", "/").strip().lower()
    if cat == "Secret":
        # Group overlapping regex matches for secrets at the same location
        fingerprint_string = f"{cat}:{normalized_path}:{location}"
    elif code_snippet:
        # Shift-resilient: if code snippet is available, preserve identity across line shifts
        norm_snippet = re.sub(r"\s+", " ", code_snippet.strip())
        fingerprint_string = f"{cat}:{normalized_path}:{rule}:{norm_snippet}"
    else:
        norm_msg = re.sub(r"\s+", " ", msg.strip().lower())
        fingerprint_string = f"{cat}:{normalized_path}:{rule}:{norm_msg}"
    return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()


class UniversalScanner:
    """Orchestrates comprehensive, layered static security and compliance analysis."""
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.findings: List[Dict[str, Any]] = []
        self.coverage: Optional[ScanCoverage] = None

    def scan(self) -> List[Dict[str, Any]]:
        start_time = time.time()
        all_finding_items: List[FindingItem] = []
        tools: Dict[str, ToolCoverage] = {}

        # 1. SAST Analysis
        sast_findings, sast_cov = run_sast_scan(self.repo_path, generate_fingerprint)
        all_finding_items.extend(sast_findings)
        tools["sast"] = sast_cov

        # 2. Secret Scanning (Working tree & Git history)
        secret_findings, secret_cov = run_secret_scan(self.repo_path, generate_fingerprint)
        all_finding_items.extend(secret_findings)
        tools["secrets"] = secret_cov

        # 3. Dependency Vulnerability Analysis (OSV)
        dep_findings, dep_cov = run_dependency_scan(self.repo_path, generate_fingerprint)
        all_finding_items.extend(dep_findings)
        tools["dependencies"] = dep_cov

        # 4. License Compliance
        lic_findings, lic_cov = run_license_scan(self.repo_path, generate_fingerprint)
        all_finding_items.extend(lic_findings)
        tools["licenses"] = lic_cov

        # 5. Code Quality & Hygiene
        qual_findings, qual_cov = run_quality_scan(self.repo_path, generate_fingerprint)
        all_finding_items.extend(qual_findings)
        tools["quality"] = qual_cov

        # Deduplicate findings by fingerprint (keeping highest severity if conflict)
        unique_findings_map: Dict[str, FindingItem] = {}
        severity_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Informational": 0}

        for item in all_finding_items:
            fp = item.fingerprint
            if fp not in unique_findings_map:
                unique_findings_map[fp] = item
            else:
                existing = unique_findings_map[fp]
                if severity_rank.get(item.severity, 0) > severity_rank.get(existing.severity, 0):
                    unique_findings_map[fp] = item

        self.findings = [f.to_dict() for f in unique_findings_map.values()]

        # Compute overall coverage status
        has_partial = any(t.status in ("PARTIAL", "SKIPPED", "FAILED") for t in tools.values())
        overall_status = "PARTIAL" if has_partial else "COMPLETED"

        # Detect examined languages
        detected_languages = set()
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "dist", "build"}]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                lang_map = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                    ".jsx": "React (JSX)", ".tsx": "React (TSX)", ".go": "Go",
                    ".java": "Java", ".c": "C", ".cpp": "C++", ".rs": "Rust"
                }
                if ext in lang_map:
                    detected_languages.add(lang_map[ext])

        total_files = sum(t.files_scanned for t in tools.values())
        total_duration = time.time() - start_time

        self.coverage = ScanCoverage(
            overall_status=overall_status,
            tools=tools,
            files_examined=total_files,
            files_skipped=0,
            supported_languages=list(detected_languages),
            total_duration_seconds=total_duration,
            is_provisional=(overall_status == "PARTIAL")
        )

        return self.findings

    def get_coverage(self) -> Dict[str, Any]:
        if not self.coverage:
            self.scan()
        return self.coverage.to_dict()
