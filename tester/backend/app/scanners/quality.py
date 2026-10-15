import os
import time
from typing import List, Tuple
from app.scanners.models import FindingItem, ToolCoverage

SUSPICIOUS_EXTENSIONS = {".p12", ".pem", ".key", ".pkcs12", ".pfx"}
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "target", "vendor", "__pycache__"}

def run_quality_scan(repo_path: str, fingerprint_generator) -> Tuple[List[FindingItem], ToolCoverage]:
    start_time = time.time()
    findings: List[FindingItem] = []
    files_scanned = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            if not os.path.isfile(full_path):
                continue

            files_scanned += 1
            ext = os.path.splitext(f)[1].lower()

            # Suspicious extension: private keys and certificates committed to git
            if ext in SUSPICIOUS_EXTENSIONS:
                fp = fingerprint_generator("Quality", rel_path, "File", "QUAL-SUSP-EXT", f"Suspicious extension {ext}")
                findings.append(FindingItem(
                    fingerprint=fp,
                    rule_id="QUAL-SUSP-EXT",
                    title="Suspicious Key/Certificate File Extension",
                    category="Quality",
                    severity="Medium",
                    confidence="High",
                    file_path=rel_path,
                    line_number=None,
                    message=f"File extension `{ext}` indicates sensitive certificate or key material that should not be committed.",
                    code_snippet=None,
                    evidence=f"File `{f}` has suspicious extension `{ext}`.",
                    impact="Committing certificate or private key files exposes cryptographic infrastructure.",
                    remediation="Add this file type to .gitignore and remove it from repository tracking.",
                    references=[]
                ))

    coverage = ToolCoverage(
        tool_name="GitFlow Code Quality Scanner",
        category="quality",
        status="COMPLETED",
        duration_seconds=time.time() - start_time,
        files_scanned=files_scanned,
        findings_count=len(findings)
    )
    return findings, coverage
