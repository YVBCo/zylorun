# Security Audit & Risk Assessment

## Executive Summary
A comprehensive security review was performed on both original projects (`software-testing-main` and `tester`). Multiple high-priority vulnerabilities and architectural risks were identified and addressed in the unified application design.

---

## 1. Vulnerability & Risk Matrix

| Risk ID | Vulnerability / Issue | Original Project | Severity | Remediation Strategy | Verification Status |
|---|---|---|---|---|---|
| **SEC-01** | **Potential Command Injection in Subprocess Execution:** `subprocess.Popen` invoked with dynamic target strings and arguments. | Project A | **Critical** | Prohibit `shell=True`. Enforce strict regex validation on target hosts (`^[a-zA-Z0-9.-]+$`). Restrict executable and argument pairs to an approved allowlist. | **Remediated** |
| **SEC-02** | **Hardcoded Backend URLs in Client:** Render URLs hardcoded across multiple JSX components. | Project A | **Medium** | Replaced all hardcoded endpoints with dynamic `apiClient` using `VITE_API_BASE_URL` or relative origin. | **Remediated** |
| **SEC-03** | **Missing Target Ownership / Tenant Isolation:** Any authenticated user could trigger scans against any target. | Project A | **High** | Added `user_id` foreign key with cascade deletion to `Target` and `RunHistory`, enforcing ownership checks on all CRUD operations. | **Remediated** |
| **SEC-04** | **Unrestricted In-Memory Log Accumulation / Zip Bomb Risk:** Large zip files could crash browser or backend memory. | Project A | **Medium** | Maintained safe browser-side `fflate` streaming extraction with 500KB output limit and strict file type allowlisting. | **Remediated** |
| **SEC-05** | **SSRF Risk in URL Speed Test:** Arbitrary URL requests without scheme or host restrictions. | Project A | **High** | Enforce HTTP/HTTPS protocol check. Disallow requests targeting private/internal network ranges (`127.0.0.1`, `localhost`, `10.0.0.0/8`, `192.168.0.0/16`, `169.254.169.254`). | **Remediated** |
| **SEC-06** | **Missing Alembic Migration Infrastructure:** Database models initialized using raw `create_all()`. | Project A | **Medium** | Integrated all models into Project B's Alembic migration tree. | **Remediated** |
| **SEC-07** | **Exposed Test SQLite DB & Artifacts in Project Root:** `sql_app.db`, `temp_bare/`, and `clone_test/` committed in source. | Project B | **Low** | Cleaned up temporary test artifacts; configured `.gitignore` to prevent database and bare-repo leakage. | **Remediated** |
| **SEC-08** | **Secret Redaction in Log Files:** Secrets could appear in raw scanner logs. | Both | **Medium** | Enforce `redact_secrets_from_log()` on scanner output before persistence and export. | **Remediated** |

---

## 2. Safe Subprocess Containment Implementation

In `services/runner.py`, the unified application uses defense-in-depth controls for command execution:
1. **Executable Whitelist:** Only pre-approved executables registered in the database can run.
2. **Argument Validation:** All runtime arguments must be exact elements from the verified `allowed_args` JSON list.
3. **Host Sanitation:**
   ```python
   HOSTNAME_REGEX = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|(?:\d{1,3}\.){3}\d{1,3}$'
   ```
4. **Execution Sandbox:** Uses `shell=False`, enforces non-blocking async streaming, and kills processes after `timeout_seconds`.
