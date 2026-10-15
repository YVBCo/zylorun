from enum import Enum
from typing import List, Dict, Any
from app.scanners.models import is_test_or_benchmark_path

class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

# Standard deterministic scoring deductions per severity
SEVERITY_DEDUCTIONS = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFORMATIONAL: 0
}

def calculate_risk_score(findings: List[Dict[str, Any]], coverage_status: str = "COMPLETED") -> Dict[str, Any]:
    """Calculates defensible, category-separated risk scores.
    The primary Security Score represents genuine security exposures
    (Vulnerabilities, Secrets, Dependencies) and is not penalized by
    unrelated concerns like missing optional licenses or file size.
    """
    security_score = 100
    secrets_score = 100
    vulns_score = 100
    deps_score = 100
    quality_score = 100
    licenses_score = 100

    deductions = []

    # Ensure deduplication by fingerprint
    unique_findings = {f.get("fingerprint") or repr(sorted(f.items())): f for f in findings}

    for finding in unique_findings.values():
        category = finding.get("category", "Vulnerability").capitalize()
        cat_lower = category.lower()
        severity_str = finding.get("severity", "Medium")

        try:
            severity = Severity(severity_str.capitalize())
        except ValueError:
            severity = Severity.MEDIUM

        # Check if finding is an intentional test fixture, sample credential, or architectural size metric
        is_non_security_or_fixture = (
            finding.get("classification") == "Intentional test fixture or demonstration example"
            or finding.get("is_test_fixture") is True
            or is_test_or_benchmark_path(finding.get("file_path") or finding.get("file"))
            or "(Test Fixture)" in (finding.get("title") or "")
            or "(Sample / Test Fixture)" in (finding.get("title") or "")
            or finding.get("rule_id") in {"QUAL-HIGH-COMPLEXITY", "QUAL-LARGE-FILE"}
        )
        if is_non_security_or_fixture:
            deductions.append({
                "category": cat_lower,
                "severity": severity.value,
                "description": finding.get("message") or finding.get("description", "Finding"),
                "points": 0,
                "reason": "Intentional test fixture / sample credential (traceable audit trail, 0 deduction)",
                "fingerprint": finding.get("fingerprint", "")
            })
            continue

        deduction = SEVERITY_DEDUCTIONS.get(severity, 8)

        # Categorize deductions
        if cat_lower in ("secret", "secrets"):
            secrets_score -= deduction
            security_score -= deduction
        elif cat_lower in ("vulnerability", "vulnerabilities", "sast"):
            vulns_score -= deduction
            security_score -= deduction
        elif cat_lower in ("dependency", "dependencies", "dependencyscan"):
            deps_score -= deduction
            security_score -= deduction
        elif cat_lower in ("quality",):
            quality_score -= deduction
        elif cat_lower in ("license", "licenses"):
            licenses_score -= deduction
        else:
            # Fallback category
            security_score -= deduction

        deductions.append({
            "category": cat_lower,
            "severity": severity.value,
            "description": finding.get("message") or finding.get("description", "Finding"),
            "points": -deduction,
            "fingerprint": finding.get("fingerprint", "")
        })

    # Clamp all scores between 0 and 100
    final_security_score = max(0, min(100, security_score))

    return {
        "base_score": 100,
        "final_score": final_security_score,
        "is_provisional": (coverage_status == "PARTIAL"),
        "category_scores": {
            "security": final_security_score,
            "secrets": max(0, min(100, secrets_score)),
            "vulnerabilities": max(0, min(100, vulns_score)),
            "dependencies": max(0, min(100, deps_score)),
            "quality": max(0, min(100, quality_score)),
            "licenses": max(0, min(100, licenses_score))
        },
        "deductions": deductions
    }
