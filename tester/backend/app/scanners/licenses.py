import os
import time
from typing import List, Tuple
from app.scanners.models import FindingItem, ToolCoverage

ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0", "Unlicense"}

def run_license_scan(repo_path: str, fingerprint_generator) -> Tuple[List[FindingItem], ToolCoverage]:
    start_time = time.time()
    findings: List[FindingItem] = []
    
    license_filename = next(
        (name for name in ('LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING')
         if os.path.exists(os.path.join(repo_path, name))),
        None
    )

    if not license_filename:
        fp = fingerprint_generator("License", "Repository", "Root", "LIC-MISSING", "No license file found")
        findings.append(FindingItem(
            fingerprint=fp,
            rule_id="LIC-MISSING",
            title="Missing Software License",
            category="License",
            severity="Medium",
            confidence="High",
            file_path="Repository",
            line_number=None,
            message="No standard LICENSE, LICENSE.md, or COPYING file found in the repository root.",
            code_snippet=None,
            evidence="Repository root lacks a recognizable LICENSE file.",
            impact="Absence of a license file defaults to 'all rights reserved', creating legal uncertainty for contributors and consumers.",
            remediation="Add an open-source license (such as MIT or Apache 2.0) to the repository root.",
            references=["https://choosealicense.com/"]
        ))
    else:
        try:
            full_path = os.path.join(repo_path, license_filename)
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                is_recognized = any(lic in content for lic in ["MIT License", "Apache License", "BSD", "ISC License", "Mozilla Public License"])
                if not is_recognized:
                    fp = fingerprint_generator("License", license_filename, "Root", "LIC-CUSTOM", "Unrecognized license")
                    findings.append(FindingItem(
                        fingerprint=fp,
                        rule_id="LIC-CUSTOM",
                        title="Unrecognized or Custom License",
                        category="License",
                        severity="Low",
                        confidence="Medium",
                        file_path=license_filename,
                        line_number=None,
                        message=f"License file `{license_filename}` detected but could not be categorized as a standard permissive license.",
                        code_snippet=content[:200],
                        evidence=f"Text in {license_filename} does not match standard open-source license templates.",
                        impact="Non-standard licenses may introduce compliance or commercial reuse restrictions.",
                        remediation="Verify that the license terms align with your project's distribution requirements.",
                        references=["https://choosealicense.com/licenses/"]
                    ))
        except Exception:
            pass

    coverage = ToolCoverage(
        tool_name="GitFlow License Compliance Scanner",
        category="license",
        status="COMPLETED",
        duration_seconds=time.time() - start_time,
        files_scanned=1 if license_filename else 0,
        findings_count=len(findings)
    )
    return findings, coverage
