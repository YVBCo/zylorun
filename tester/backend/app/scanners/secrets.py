import os
import re
import time
import json
import subprocess
from typing import List, Tuple
from app.scanners.models import FindingItem, ToolCoverage, is_test_or_benchmark_path

SECRET_PATTERNS = {

    "SEC-SECRET-AWS": {
        "title": "AWS Access Key Exposure",
        "pattern": re.compile(r'(?i)\b(AKIA[0-9A-Z]{16})\b'),
        "severity": "Critical",
        "confidence": "High",
        "remediation": "Revoke this AWS Access Key immediately in the AWS IAM Console, delete the hardcoded string, and use AWS IAM Roles or environment variables."
    },
    "SEC-SECRET-GITHUB": {
        "title": "GitHub Personal Access Token Exposure",
        "pattern": re.compile(r'\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})\b'),
        "severity": "Critical",
        "confidence": "High",
        "remediation": "Revoke this token immediately on GitHub Settings -> Developer settings -> Personal access tokens."
    },
    "SEC-SECRET-SLACK": {
        "title": "Slack API / Bot Token Exposure",
        "pattern": re.compile(r'\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b'),
        "severity": "Critical",
        "confidence": "High",
        "remediation": "Revoke this Slack token in the Slack API app management dashboard."
    },
    "SEC-SECRET-STRIPE": {
        "title": "Stripe Live Secret Key Exposure",
        "pattern": re.compile(r'\b(sk_live_[0-9a-zA-Z]{24})\b'),
        "severity": "Critical",
        "confidence": "High",
        "remediation": "Roll this key immediately in the Stripe Dashboard under Developers -> API keys."
    },
    "SEC-SECRET-GOOGLE": {
        "title": "Google API Key Exposure",
        "pattern": re.compile(r'\b(AIza[0-9A-Za-z\-_]{35})\b'),
        "severity": "High",
        "confidence": "High",
        "remediation": "Restrict or delete this API key in the Google Cloud Console under APIs & Services -> Credentials."
    },
    "SEC-SECRET-PRIVKEY": {
        "title": "Private Cryptographic Key Material Exposure",
        "pattern": re.compile(r'-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----'),
        "severity": "Critical",
        "confidence": "High",
        "remediation": "Remove the private key file, generate a new key pair, and revoke any authorized keys configured with this private key."
    },
    "SEC-SECRET-GENERIC": {
        "title": "Generic Secret or API Token Assignment",
        "pattern": re.compile(
            r'(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key|password|passwd)\s*[:=]\s*(?:[\'"]([0-9a-zA-Z\-_!@#$%^&*+=]{16,})[\'"]|([0-9a-zA-Z\-_!@#$%^&*+=]{16,})\s*$)'
        ),
        "severity": "High",
        "confidence": "Medium",
        "remediation": "Move this credential to an environment variable (.env) or a secret manager (AWS Secrets Manager / HashiCorp Vault)."
    }
}

KNOWN_SAMPLE_PATTERNS = {
    "EXAMPLE", "SAMPLE", "DUMMY", "PLACEHOLDER", "CHANGEME", "CHANGE_ME",
    "YOUR-SUPER-SECRET-KEY", "SUPER-SECRET", "SUPER_SECRET", "UNIQUE-SECRET", "UNIQUE-WEBHOOK-SECRET",
    "UNIQUE-ENCRYPTION-KEY", "UNIQUE-CRON-SECRET", "GHO_FAKE_TOKEN", "FAKE_TOKEN",
    "REPLACE_WITH_", "YOUR_SECURE_", "PASSPORT_PASSWORD", "SECRET_TOKEN",
    "TEST_TOKEN", "SAMPLE_KEY", "DUMMY_KEY", "TOKEN_123"
}

def is_sample_or_placeholder_credential(secret_str: str) -> bool:
    """Detects whether a detected secret string is a known non-functional documentation sample or test placeholder."""
    upper = secret_str.upper()
    if any(ind in upper for ind in KNOWN_SAMPLE_PATTERNS):
        return True
    if upper.startswith("AKIA") and upper.endswith("EXAMPLE"):
        return True
    if "${" in secret_str or "<" in secret_str or "{{" in secret_str:
        return True
    if secret_str.lower().startswith("super_secret") or "dummy" in secret_str.lower() or "sample" in secret_str.lower():
        return True
    return False

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "target", "vendor", "__pycache__"}
MAX_FILE_BYTES = 512 * 1024

def redact_secret(raw: str) -> str:
    """Mask credentials so complete secret values never appear in logs or API responses."""
    if len(raw) <= 8:
        return "****"
    return raw[:4] + "*" * (len(raw) - 8) + raw[-4:]

def run_secret_scan(repo_path: str, fingerprint_generator) -> Tuple[List[FindingItem], ToolCoverage]:
    start_time = time.time()
    findings: List[FindingItem] = []
    files_scanned = 0
    tool_name = "GitFlow Secret Detection Engine"

    # Check for Gitleaks
    gitleaks_available = False
    try:
        gl_check = subprocess.run(["gitleaks", "version"], capture_output=True, text=True, timeout=5)
        if gl_check.returncode == 0:
            gitleaks_available = True
            tool_name = f"Gitleaks {gl_check.stdout.strip()}"
    except Exception:
        gitleaks_available = False

    if gitleaks_available:
        try:
            gl_run = subprocess.run(
                ["gitleaks", "detect", "--source", repo_path, "--report-format", "json", "--no-banner"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if gl_run.stdout:
                gl_data = json.loads(gl_run.stdout)
                for item in gl_data:
                    file_path = os.path.relpath(item.get("File", ""), repo_path).replace("\\", "/")
                    line = item.get("StartLine")
                    rule_id = item.get("RuleID", "gitleaks-secret")
                    description = item.get("Description", "Exposed Secret")
                    secret_val = item.get("Secret", "")
                    redacted = redact_secret(secret_val) if secret_val else "****"
                    is_test_file = is_test_or_benchmark_path(file_path)
                    is_sample = is_sample_or_placeholder_credential(secret_val) or is_test_file
                    classification = (
                        "Intentional test fixture or demonstration example"
                        if is_sample
                        else "Confirmed vulnerability or exposure"
                    )
                    fp = fingerprint_generator("Secret", file_path, f"Line {line}" if line else "Repository", rule_id, description)

                    if not any(f.fingerprint == fp for f in findings):
                        findings.append(FindingItem(
                            fingerprint=fp,
                            rule_id=f"GL-{rule_id}",
                            title=f"Secret Detected: {description}" + (" (Sample / Test Fixture)" if is_sample else ""),
                            category="Secret",
                            severity="Critical",
                            confidence="Low" if is_sample else "High",
                            classification=classification,
                            file_path=file_path,
                            line_number=line,
                            message=f"Potential secret `{redacted}` detected by Gitleaks.",
                            code_snippet=redacted,
                            evidence=f"Matched Gitleaks rule `{rule_id}` at line {line}",
                            impact="Exposed credentials can grant unauthorized access to external cloud resources, APIs, or databases.",
                            remediation="Revoke and rotate the exposed credential immediately. Remove it from code and commit history.",
                            references=["https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure"]
                        ))
        except Exception:
            pass

    # Built-in working-tree secret scanning
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            try:
                if os.path.getsize(full_path) > MAX_FILE_BYTES:
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in {'.png', '.jpg', '.jpeg', '.pdf', '.zip', '.tar', '.gz', '.exe', '.dll', '.ico', '.db', '.sqlite', '.sqlite3', '.pyc', '.bin'}:
                    continue

                files_scanned += 1
                is_yaml = ext in {'.yaml', '.yml'}
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_idx, line in enumerate(fh, start=1):
                        # Skip YAML configuration property declarations
                        if is_yaml:
                            if re.match(r'^\s*-\s*key:\s*[A-Z0-9_]+', line) or re.match(r'^\s*envVarKey:\s*[A-Z0-9_]+', line):
                                continue

                        for rule_id, rule_info in SECRET_PATTERNS.items():
                            match = rule_info["pattern"].search(line)
                            if match:
                                raw_secret = (match.group(1) or (match.group(2) if len(match.groups()) > 1 else None) or match.group(0)).strip('\'"')
                                if '(' in raw_secret or ')' in raw_secret:
                                    continue

                                is_test_file = is_test_or_benchmark_path(rel_path)
                                is_sample = is_sample_or_placeholder_credential(raw_secret) or is_test_file
                                classification = (
                                    "Intentional test fixture or demonstration example"
                                    if is_sample
                                    else "Confirmed vulnerability or exposure"
                                )
                                confidence = "Low" if is_sample else rule_info["confidence"]
                                redacted = redact_secret(raw_secret)
                                clean_line = line.replace(raw_secret, redacted).strip()

                                fp = fingerprint_generator(
                                    "Secret", rel_path, f"Line {line_idx}",
                                    rule_id, rule_info["title"]
                                )

                                if not any(fi.fingerprint == fp for fi in findings):
                                    findings.append(FindingItem(
                                        fingerprint=fp,
                                        rule_id=rule_id,
                                        title=rule_info["title"] + (" (Sample / Test Fixture)" if is_sample else ""),
                                        category="Secret",
                                        severity=rule_info["severity"],
                                        confidence=confidence,
                                        classification=classification,
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        message=f"{rule_info['title']} {'sample' if is_sample else 'found'} in {rel_path}:{line_idx}",
                                        code_snippet=clean_line,
                                        evidence=(
                                            f"Matches known non-functional sample or placeholder credential (masked: `{redacted}`)"
                                            if is_sample
                                            else f"Matched secret pattern `{rule_id}` (masked: `{redacted}`)"
                                        ),
                                        impact="Known test/placeholder credential does not expose live systems, but should not be reused in production." if is_sample else "Exposed API keys or credentials allow unauthorized access to services and data.",
                                        remediation=(
                                            "Documented sample credential detected. Ensure this placeholder is replaced with a securely provisioned secret in production environments."
                                            if is_sample
                                            else rule_info["remediation"]
                                        ),
                                        references=["https://cwe.mitre.org/data/definitions/798.html"]
                                    ))
                                # Only report highest-severity secret on this exact line
                                break
            except Exception:
                continue

    # Historical Git commit secret scan (scans previous commits for secrets that were later deleted)
    try:
        git_log = subprocess.run(
            ["git", "-C", repo_path, "log", "-p", "-n", "20", "--diff-filter=D"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if git_log.returncode == 0 and git_log.stdout:
            current_commit = "history"
            current_file = "history"
            for line in git_log.stdout.splitlines():
                if line.startswith("commit "):
                    current_commit = line.split()[1][:7]
                elif line.startswith("--- a/"):
                    current_file = line[6:].strip()
                elif line.startswith("-") and not line.startswith("---"):
                    deleted_line = line[1:].strip()
                    for rule_id, rule_info in SECRET_PATTERNS.items():
                        if rule_id == "SEC-SECRET-GENERIC":
                            continue  # Only alert on high-confidence patterns in history
                        m = rule_info["pattern"].search(deleted_line)
                        if m:
                            raw_val = m.group(1) if m.groups() else m.group(0)
                            redacted = redact_secret(raw_val)
                            fp = fingerprint_generator(
                                "Secret", current_file, f"Commit {current_commit}",
                                rule_id, f"Historical {rule_info['title']}"
                            )
                            if not any(fi.fingerprint == fp for fi in findings):
                                findings.append(FindingItem(
                                    fingerprint=fp,
                                    rule_id=f"{rule_id}-HISTORICAL",
                                    title=f"Historical {rule_info['title']} in Commit {current_commit}",
                                    category="Secret",
                                    severity=rule_info["severity"],
                                    confidence="High",
                                    file_path=current_file,
                                    line_number=None,
                                    message=f"Secret was committed in history ({current_commit}) and subsequently deleted from the working tree.",
                                    code_snippet=deleted_line.replace(raw_val, redacted),
                                    evidence=f"Found in deleted line of commit {current_commit} (masked: `{redacted}`)",
                                    impact="Secrets committed to Git history remain accessible via Git history or repository clones even after deletion.",
                                    remediation="Rotate this credential immediately. Git history retains old commits; merely deleting the file does not secure the key.",
                                    references=["https://cwe.mitre.org/data/definitions/798.html"]
                                ))
                            break
    except Exception:
        pass

    duration = time.time() - start_time
    coverage = ToolCoverage(
        tool_name=tool_name,
        category="secrets",
        status="COMPLETED",
        duration_seconds=duration,
        files_scanned=files_scanned,
        findings_count=len(findings)
    )
    return findings, coverage
