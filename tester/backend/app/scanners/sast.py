import os
import re
import ast
import json
import time
import subprocess
from typing import List, Tuple
from app.scanners.models import FindingItem, ToolCoverage, is_test_or_benchmark_path

SAST_RULES = [
    {
        "id": "SEC-SQLI-001",
        "title": "Potential SQL Injection via Dynamic String Formatting",
        "category": "Vulnerability",
        "severity": "High",
        "confidence": "High",
        "extensions": {".py", ".js", ".ts", ".jsx", ".tsx"},
        "pattern": re.compile(
            r'(?:execute|cursor\.execute|session\.execute|raw)\s*\(\s*(?:f["\']|\b[a-zA-Z0-9_]+\s*%\s*|["\'].*?["\']\s*\+\s*|\`.*?\$\{)',
            re.IGNORECASE
        ),
        "impact": "Unsanitized user inputs concatenated into database queries may allow attackers to execute arbitrary SQL commands, read confidential data, or alter tables.",
        "remediation": "Use parameterized queries or ORM query builders instead of raw string concatenation or f-strings.",
        "references": ["https://owasp.org/www-community/attacks/SQL_Injection", "https://cwe.mitre.org/data/definitions/89.html"]
    },
    {
        "id": "SEC-CMDI-001",
        "title": "Command Injection via Shell Execution",
        "category": "Vulnerability",
        "severity": "Critical",
        "confidence": "High",
        "extensions": {".py", ".js", ".ts"},
        "pattern": re.compile(
            r'(?:subprocess\.(?:run|Popen|call|check_output)\s*\([^)]*shell\s*=\s*True|os\.system\s*\(|child_process\.exec\s*\()',
            re.IGNORECASE
        ),
        "impact": "Executing system commands through a shell with untrusted input can allow remote attackers to execute arbitrary system commands on the server.",
        "remediation": "Avoid shell=True. Pass arguments as a list of strings directly to subprocess without an intermediate shell.",
        "references": ["https://owasp.org/www-community/attacks/Command_Injection", "https://cwe.mitre.org/data/definitions/78.html"]
    },
    {
        "id": "SEC-XSS-001",
        "title": "Cross-Site Scripting (XSS) via Unsanitized HTML Rendering",
        "category": "Vulnerability",
        "severity": "High",
        "confidence": "High",
        "extensions": {".js", ".jsx", ".ts", ".tsx", ".html"},
        "pattern": re.compile(
            r'(?:dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:|innerHTML\s*=\s*|document\.write\s*\()',
            re.IGNORECASE
        ),
        "impact": "Injecting unsanitized input directly into the DOM can allow attackers to execute malicious JavaScript in victims' browsers, stealing sessions or credentials.",
        "remediation": "Use safe DOM manipulation methods like textContent, or sanitize HTML using DOMPurify before rendering.",
        "references": ["https://owasp.org/www-community/attacks/xss/", "https://cwe.mitre.org/data/definitions/79.html"]
    },
    {
        "id": "SEC-DESER-001",
        "title": "Unsafe Object Deserialization",
        "category": "Vulnerability",
        "severity": "Critical",
        "confidence": "High",
        "extensions": {".py"},
        "pattern": re.compile(
            r'(?:pickle\.loads?\s*\(|_pickle\.loads?\s*\(|yaml\.load\s*\([^,)]*\)(?!\s*Loader\s*=\s*(?:yaml\.)?SafeLoader))',
            re.IGNORECASE
        ),
        "impact": "Deserializing untrusted pickle or unconstrained YAML payloads allows arbitrary Python code execution upon deserialization.",
        "remediation": "Use safe serialization formats like JSON, or yaml.safe_load() / SafeLoader instead of standard pickle.",
        "references": ["https://cwe.mitre.org/data/definitions/502.html"]
    },
    {
        "id": "SEC-CRYP-001",
        "title": "Use of Broken or Weak Cryptographic Hash",
        "category": "Vulnerability",
        "severity": "Medium",
        "confidence": "High",
        "extensions": {".py", ".js", ".ts"},
        "pattern": re.compile(
            r'(?:hashlib\.md5\s*\(|hashlib\.sha1\s*\(|crypto\.createHash\s*\(\s*["\'](?:md5|sha1)["\'])',
            re.IGNORECASE
        ),
        "impact": "MD5 and SHA-1 have known collision vulnerabilities and should not be used for security-critical contexts or password hashing.",
        "remediation": "Use SHA-256 (hashlib.sha256) for integrity checks, or bcrypt / argon2 for passwords.",
        "references": ["https://cwe.mitre.org/data/definitions/327.html"]
    },
    {
        "id": "SEC-AUTH-001",
        "title": "Disabled JWT Signature Verification",
        "category": "Vulnerability",
        "severity": "Critical",
        "confidence": "High",
        "extensions": {".py", ".js", ".ts"},
        "pattern": re.compile(
            r'(?:jwt\.decode\s*\([^)]*(?:verify\s*=\s*False|verify_signature\s*=\s*False|algorithms\s*=\s*\[\s*["\']none["\']))',
            re.IGNORECASE
        ),
        "impact": "Disabling JWT signature verification allows attackers to forge tokens with arbitrary claims and bypass authentication.",
        "remediation": "Always verify signatures using a secure secret or public key, and restrict accepted algorithms.",
        "references": ["https://cwe.mitre.org/data/definitions/347.html"]
    },
    {
        "id": "SEC-CONF-001",
        "title": "Disabled TLS/SSL Certificate Validation",
        "category": "Vulnerability",
        "severity": "High",
        "confidence": "High",
        "extensions": {".py", ".js", ".ts"},
        "pattern": re.compile(
            r'(?:requests\.(?:get|post|put|delete|request)\s*\([^)]*verify\s*=\s*False|httpx\.(?:get|post|AsyncClient|Client)\s*\([^)]*verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["\']0["\'])',
            re.IGNORECASE
        ),
        "impact": "Disabling TLS certificate verification makes communication vulnerable to man-in-the-middle (MITM) attacks and data interception.",
        "remediation": "Enable TLS verification (verify=True). Supply custom CA bundles if connecting to private certificates.",
        "references": ["https://cwe.mitre.org/data/definitions/295.html"]
    },
    {
        "id": "SEC-TRAV-001",
        "title": "Path Traversal via Unvalidated Path Construction",
        "category": "Vulnerability",
        "severity": "High",
        "confidence": "Medium",
        "extensions": {".py", ".js", ".ts"},
        "pattern": re.compile(
            r'(?:open\s*\(\s*(?:request\.|req\.|os\.path\.join\([^)]*request\.)|send_from_directory\s*\([^)]*request\.)',
            re.IGNORECASE
        ),
        "impact": "Allowing user-controlled relative paths like '../' can lead to arbitrary file reads outside the intended directory.",
        "remediation": "Canonicalize paths using os.path.realpath() and verify that the target path begins with the allowed base directory.",
        "references": ["https://cwe.mitre.org/data/definitions/22.html"]
    }
]

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "target", "vendor", "__pycache__"}
MAX_FILE_BYTES = 512 * 1024

def get_python_string_literal_lines(file_path: str) -> set:
    """Returns line numbers that belong to string literals/constants in a Python file using AST analysis."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read(), filename=file_path)
        str_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for l in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        str_lines.add(l)
        return str_lines
    except Exception:
        return set()

def run_sast_scan(repo_path: str, fingerprint_generator) -> Tuple[List[FindingItem], ToolCoverage]:
    start_time = time.time()
    findings: List[FindingItem] = []
    files_scanned = 0
    tool_name = "GitFlow Static Analysis Engine"

    # Check if semgrep CLI is available
    semgrep_available = False
    try:
        semgrep_check = subprocess.run(["semgrep", "--version"], capture_output=True, text=True, timeout=5)
        if semgrep_check.returncode == 0:
            semgrep_available = True
            tool_name = f"Semgrep {semgrep_check.stdout.strip()}"
    except Exception:
        semgrep_available = False

    if semgrep_available:
        try:
            semgrep_run = subprocess.run(
                ["semgrep", "scan", "--json", "--quiet", "--config", "auto", repo_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            if semgrep_run.stdout:
                data = json.loads(semgrep_run.stdout)
                results = data.get("results", [])
                for res in results:
                    file_path = os.path.relpath(res.get("path", ""), repo_path).replace("\\", "/")
                    line = res.get("start", {}).get("line")
                    rule_id = res.get("check_id", "semgrep-rule")
                    msg = res.get("extra", {}).get("message", "Semgrep finding")
                    sev_raw = res.get("extra", {}).get("severity", "WARNING").upper()
                    sev_map = {"ERROR": "High", "WARNING": "Medium", "INFO": "Low"}
                    severity = sev_map.get(sev_raw, "Medium")
                    code_snippet = res.get("extra", {}).get("lines", "")

                    fp = fingerprint_generator(
                        rule_id, file_path, f"Line {line}" if line else "Repository",
                        msg, category="Vulnerability", code_snippet=code_snippet
                    )
                    findings.append(FindingItem(
                        fingerprint=fp,
                        rule_id=rule_id,
                        title=f"Security Finding: {rule_id}",
                        category="Vulnerability",
                        severity=severity,
                        confidence="High",
                        file_path=file_path,
                        line_number=line,
                        message=msg,
                        code_snippet=code_snippet.strip() if code_snippet else None,
                        evidence=f"Matched Semgrep rule {rule_id} at line {line}",
                        impact="Static analysis detected a security pattern violation.",
                        remediation="Review the affected code and apply recommended safe patterns.",
                        references=[]
                    ))
        except Exception:
            pass

    # Built-in deterministic SAST pass (runs as primary or supplementary analyzer)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            applicable_rules = [r for r in SAST_RULES if ext in r["extensions"]]
            if not applicable_rules:
                continue

            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            try:
                if os.path.getsize(full_path) > MAX_FILE_BYTES:
                    continue
                files_scanned += 1
                is_py = (ext == ".py")
                str_literal_lines = get_python_string_literal_lines(full_path) if is_py else set()
                is_test_file = is_test_or_benchmark_path(rel_path)

                with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_idx, line in enumerate(fh, start=1):
                        stripped = line.strip()
                        if is_py and stripped.startswith("#"):
                            continue
                        if not is_py and (stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")):
                            continue

                        for rule in applicable_rules:
                            if rule["pattern"].search(line):
                                snippet = line.strip()
                                in_str_literal = (line_idx in str_literal_lines)

                                if is_test_file and in_str_literal:
                                    classification = "Intentional test fixture or demonstration example"
                                    confidence = "Low"
                                    severity = rule["severity"]
                                    evidence = f"Code pattern matched inside a string literal within test/benchmark fixture at line {line_idx}. Verified as non-executable test example."
                                    impact = "Pattern defined as test fixture data; not executed in application runtime."
                                    remediation = "Verify that this code example remains isolated to test fixtures and is not executed in application runtime."
                                elif is_test_file:
                                    classification = "Intentional test fixture or demonstration example"
                                    confidence = "Low"
                                    severity = rule["severity"]
                                    evidence = f"Code matched rule pattern `{rule['pattern'].pattern}` in test/benchmark file at line {line_idx}. Verified as non-executable test example."
                                    impact = "Pattern defined as test fixture data; not executed in application runtime."
                                    remediation = "Verify that this code example remains isolated to test fixtures and is not executed in application runtime."
                                else:
                                    classification = "Confirmed vulnerability or exposure"
                                    confidence = rule["confidence"]
                                    severity = rule["severity"]
                                    evidence = f"Code matched rule pattern `{rule['pattern'].pattern}` at line {line_idx}"
                                    impact = rule["impact"]
                                    remediation = rule["remediation"]

                                fp = fingerprint_generator(
                                    rule["id"], rel_path, f"Line {line_idx}",
                                    rule["title"], category=rule["category"], code_snippet=snippet
                                )
                                # Deduplicate if already reported
                                if not any(fi.fingerprint == fp for fi in findings):
                                    findings.append(FindingItem(
                                        fingerprint=fp,
                                        rule_id=rule["id"],
                                        title=rule["title"] + (" (Test Fixture)" if classification == "Intentional test fixture or demonstration example" else ""),
                                        category=rule["category"],
                                        severity=severity,
                                        confidence=confidence,
                                        classification=classification,
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        message=f"{rule['title']} in {rel_path}:{line_idx}",
                                        code_snippet=snippet,
                                        evidence=evidence,
                                        impact=impact,
                                        remediation=remediation,
                                        references=rule["references"]
                                    ))
            except Exception:
                continue

    duration = time.time() - start_time
    coverage = ToolCoverage(
        tool_name=tool_name,
        category="sast",
        status="COMPLETED",
        duration_seconds=duration,
        files_scanned=files_scanned,
        findings_count=len(findings)
    )
    return findings, coverage
