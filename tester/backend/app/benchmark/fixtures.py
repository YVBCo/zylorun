"""Independent Security Benchmark Fixtures.
Defines ground-truth test cases across supported vulnerability classes,
secret patterns, dependency manifests, and false-positive controls.

Ground-truth expectations are derived from authoritative sources:
- OWASP Top 10 & CWE definitions
- GitHub Advisory Database (GHSA) and PyPI Advisories (PYSEC)
- Official vendor documentation (e.g. AWS sample credentials)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class BenchmarkFixture:
    fixture_id: str
    name: str
    category: str
    file_path: str
    content: str
    expected_findings_count: int
    expected_rule_id: Optional[str] = None
    expected_category: Optional[str] = None
    expected_severity: Optional[str] = None
    expected_classification: Optional[str] = None
    is_vulnerable: bool = True
    uncertainty_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


BENCHMARK_FIXTURES: List[BenchmarkFixture] = [
    # =========================================================================
    # 1. SQL Injection (Python & JavaScript) - Vulnerable Variants
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-SQLI-001",
        name="SQL Injection via String Concatenation (Python)",
        category="Vulnerability",
        file_path="app/legacy_user_repo.py",
        content=(
            "def get_user_by_name(cursor, name):\n"
            "    query = cursor.execute('SELECT * FROM users WHERE username = ' + name)\n"
            "    return query\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Direct string concatenation in cursor.execute."
    ),
    BenchmarkFixture(
        fixture_id="VULN-SQLI-FSTRING-001",
        name="SQL Injection via f-string Formatting (Python)",
        category="Vulnerability",
        file_path="app/catalog_service.py",
        content=(
            "def search_catalog(session, category):\n"
            '    return session.execute(f"SELECT * FROM products WHERE cat = \'{category}\'")\n'
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Python f-string inside session.execute allows SQL injection."
    ),
    BenchmarkFixture(
        fixture_id="VULN-SQLI-JS-001",
        name="SQL Injection via Template Literal (JavaScript)",
        category="Vulnerability",
        file_path="src/database/users.js",
        content=(
            "async function findUserById(db, userId) {\n"
            "    return db.execute(`SELECT * FROM users WHERE id = ${userId}`);\n"
            "}\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="JavaScript template literal interpolation inside db.execute."
    ),

    # =========================================================================
    # 2. SQL Injection Controls - Safe Parameterized & ORM Variants
    # =========================================================================
    BenchmarkFixture(
        fixture_id="CLEAN-SQLI-PARAM-001",
        name="Safe Parameterized SQL Query (Python)",
        category="Clean Code",
        file_path="app/safe_user_repo.py",
        content=(
            "def get_user(cursor, user_id: int):\n"
            "    cursor.execute('SELECT id, name FROM users WHERE id = %s', (user_id,))\n"
            "    return cursor.fetchall()\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Parameterized query with tuple placeholder is safe."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-SQLI-ORM-001",
        name="Safe ORM Query Builder (Python)",
        category="Clean Code",
        file_path="app/orm_service.py",
        content=(
            "def get_active_account(session, account_name):\n"
            "    return session.query(Account).filter_by(name=account_name).first()\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="ORM method chaining does not use raw dynamic SQL strings."
    ),
    BenchmarkFixture(
        fixture_id="BENIGN-COMMENT-SQLI-001",
        name="Benign Code Comment Mentioning SQL Injection Pattern",
        category="Clean Code",
        file_path="app/docs_reference.py",
        content=(
            "# Avoid unsafe patterns such as: cursor.execute('SELECT * FROM users WHERE id = ' + uid)\n"
            "# Always use parameterized statements instead.\n"
            "def placeholder():\n"
            "    pass\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Vulnerable syntax inside a comment must NOT trigger a false positive."
    ),

    # =========================================================================
    # 3. Command Injection (Python) - Vulnerable & Safe Variants
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-CMDI-001",
        name="Command Injection via os.system",
        category="Vulnerability",
        file_path="app/diagnostics.py",
        content=(
            "import os\n"
            "def run_health_check(ip_address):\n"
            "    os.system('ping -c 1 ' + ip_address)\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-CMDI-001",
        expected_category="Vulnerability",
        expected_severity="Critical",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="os.system call concatenating untrusted IP input."
    ),
    BenchmarkFixture(
        fixture_id="VULN-CMDI-SHELL-001",
        name="Command Injection via subprocess shell=True",
        category="Vulnerability",
        file_path="app/backup.py",
        content=(
            "import subprocess\n"
            "def backup_folder(folder_path):\n"
            "    subprocess.run('tar -czf backup.tar.gz ' + folder_path, shell=True)\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-CMDI-001",
        expected_category="Vulnerability",
        expected_severity="Critical",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="subprocess.run with shell=True and dynamic input."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-CMDI-LIST-001",
        name="Safe Subprocess with Argument List",
        category="Clean Code",
        file_path="app/safe_diagnostics.py",
        content=(
            "import subprocess\n"
            "def run_health_check(ip_address: str):\n"
            "    return subprocess.run(['ping', '-c', '1', ip_address], capture_output=True, check=True)\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Subprocess using argument array without shell execution is safe."
    ),

    # =========================================================================
    # 4. Cross-Site Scripting (XSS) (JavaScript) - Vulnerable & Safe Variants
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-XSS-001",
        name="DOM-Based XSS via innerHTML",
        category="Vulnerability",
        file_path="src/vulnerable_view.js",
        content=(
            "function displayBanner(userHtml) {\n"
            "    const container = document.getElementById('banner');\n"
            "    container.innerHTML = userHtml;\n"
            "}\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-XSS-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Direct assignment to innerHTML without sanitization."
    ),
    BenchmarkFixture(
        fixture_id="VULN-XSS-REACT-001",
        name="React XSS via dangerouslySetInnerHTML",
        category="Vulnerability",
        file_path="src/components/RawHtmlBlock.jsx",
        content=(
            "export function RawHtmlBlock({ untrustedContent }) {\n"
            "    return <div dangerouslySetInnerHTML={{ __html: untrustedContent }} />;\n"
            "}\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-XSS-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="React dangerouslySetInnerHTML bypasses React escaping."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-XSS-DOM-001",
        name="Safe DOM Manipulation via textContent",
        category="Clean Code",
        file_path="src/safe_profile.js",
        content=(
            "function displayProfile(username) {\n"
            "    const el = document.getElementById('username');\n"
            "    el.textContent = username;\n"
            "}\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="textContent automatically encodes all entities as text."
    ),

    # =========================================================================
    # 5. Unsafe Deserialization (Python)
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-DESER-001",
        name="Unsafe Object Deserialization via pickle.loads",
        category="Vulnerability",
        file_path="app/cache_loader.py",
        content=(
            "import pickle\n"
            "def load_cached_object(raw_payload):\n"
            "    return pickle.loads(raw_payload)\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-DESER-001",
        expected_category="Vulnerability",
        expected_severity="Critical",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="pickle.loads executes arbitrary code upon deserialization."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-DESER-JSON-001",
        name="Safe Structured Data Deserialization via json.loads",
        category="Clean Code",
        file_path="app/safe_cache_loader.py",
        content=(
            "import json\n"
            "def load_payload(raw_json: str):\n"
            "    return json.loads(raw_json)\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="json.loads is safe from arbitrary code execution."
    ),

    # =========================================================================
    # 6. Weak Cryptography (Python)
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-CRYP-001",
        name="Weak Cryptographic Hash via hashlib.md5",
        category="Vulnerability",
        file_path="app/token_gen.py",
        content=(
            "import hashlib\n"
            "def generate_etag(content: bytes) -> str:\n"
            "    return hashlib.md5(content).hexdigest()\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-CRYP-001",
        expected_category="Vulnerability",
        expected_severity="Medium",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="MD5 is cryptographically broken and prone to collision attacks."
    ),
    BenchmarkFixture(
        fixture_id="VULN-CRYP-SHA1-001",
        name="Weak Cryptographic Hash via hashlib.sha1",
        category="Vulnerability",
        file_path="app/fingerprint.py",
        content=(
            "import hashlib\n"
            "def hash_signature(data: bytes) -> str:\n"
            "    return hashlib.sha1(data).hexdigest()\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-CRYP-001",
        expected_category="Vulnerability",
        expected_severity="Medium",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="SHA-1 is deprecated and vulnerable to practical collision attacks."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-CRYP-SHA256-001",
        name="Strong Cryptographic Hash via hashlib.sha256",
        category="Clean Code",
        file_path="app/safe_crypto.py",
        content=(
            "import hashlib\n"
            "def generate_secure_digest(data: bytes) -> str:\n"
            "    return hashlib.sha256(data).hexdigest()\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="SHA-256 meets standard cryptographic collision resistance requirements."
    ),

    # =========================================================================
    # 7. Path Traversal (Python)
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-PATH-001",
        name="Path Traversal via Unvalidated Path Construction",
        category="Vulnerability",
        file_path="app/file_viewer.py",
        content=(
            "import os\n"
            "def read_user_file(request):\n"
            "    with open(os.path.join('/var/data', request.args.get('filename')), 'r') as fh:\n"
            "        return fh.read()\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-TRAV-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="open() with unvalidated request parameters allows ../ directory traversal."
    ),
    BenchmarkFixture(
        fixture_id="CLEAN-PATH-SAFE-001",
        name="Safe Path Traversal Defense with Boundary Verification",
        category="Clean Code",
        file_path="app/safe_file_viewer.py",
        content=(
            "import os\n"
            "BASE_DIR = '/var/data'\n"
            "def read_user_file(filename: str) -> str:\n"
            "    clean_name = os.path.basename(filename)\n"
            "    full_path = os.path.abspath(os.path.join(BASE_DIR, clean_name))\n"
            "    if not full_path.startswith(BASE_DIR):\n"
            "        raise PermissionError('Path traversal detected')\n"
            "    return full_path\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Proper boundary validation prevents traversal."
    ),

    # =========================================================================
    # 8. Hardcoded Secrets & Credentials
    # =========================================================================
    BenchmarkFixture(
        fixture_id="VULN-SECRET-REAL-001",
        name="Realistic Synthetic Stripe Live Secret Key",
        category="Secret",
        file_path="app/billing_config.py",
        content=(
            "# Synthetic test Stripe live secret key format\n"
            f'stripe_live_key = "{"sk_live_"}{"51A2B3C4D5E6F7G8H9I0J1K2"}"\n'
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SECRET-STRIPE",
        expected_category="Secret",
        expected_severity="Critical",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Synthetic active secret format. Must be detected as confirmed exposure."
    ),
    BenchmarkFixture(
        fixture_id="SAMPLE-SECRET-001",
        name="Documented AWS Sample Placeholder Credential",
        category="Secret",
        file_path="docs/sample_setup.py",
        content=(
            "# AWS documentation default sample key\n"
            'AWS_SAMPLE_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SECRET-AWS",
        expected_category="Secret",
        expected_severity="Critical",
        expected_classification="Intentional test fixture or demonstration example",
        is_vulnerable=False,
        uncertainty_notes="Documented non-functional sample key. Must be classified as Test Fixture with 0 score deduction."
    ),
    BenchmarkFixture(
        fixture_id="NON-SECRET-001",
        name="Non-Secret Identifiers, UUIDs, Hashes and Config Keys",
        category="Clean Code",
        file_path="app/identifiers.py",
        content=(
            "# UUIDs, commit SHAs and function assignments must NOT trigger secret alerts\n"
            'TRANSACTION_ID = "123e4567-e89b-12d3-a456-426614174000"\n'
            'BUILD_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"\n'
            'access_token = create_access_token(data={"sub": str(user_id)})\n'
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Non-secret strings that resemble credentials in length but represent UUIDs or hashes."
    ),

    # =========================================================================
    # 9. Authoritative Dependency Benchmarks (PyPI & npm)
    # =========================================================================
    # Advisory CVE-2018-18074 / GHSA-x84v-xcm2-53pg:
    # Requests before 2.20.0 sends Authorization header upon HTTP redirect.
    # Affected range: < 2.20.0 (e.g. 2.19.1). Fixed release: 2.20.0.
    BenchmarkFixture(
        fixture_id="VULN-DEP-REQUESTS-001",
        name="Vulnerable Dependency: Requests 2.19.1 (CVE-2018-18074 / GHSA-x84v-xcm2-53pg)",
        category="Dependency",
        file_path="requirements.txt",
        content="requests==2.19.1\n",
        expected_findings_count=1,
        expected_rule_id="DEP-GHSA-x84v-xcm2-53pg",
        expected_category="Dependency",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Requests 2.19.1 is confirmed vulnerable to CVE-2018-18074 / GHSA-x84v-xcm2-53pg."
    ),
    BenchmarkFixture(
        fixture_id="CONTROL-DEP-REQUESTS-001",
        name="Fixed-Version Control Case: Requests 2.20.0 (CVE-2018-18074 Fixed Release)",
        category="Clean Code",
        file_path="requirements.txt",
        content="requests==2.20.0\n",
        expected_findings_count=0,
        expected_rule_id="DEP-GHSA-x84v-xcm2-53pg",
        is_vulnerable=False,
        uncertainty_notes="Requests 2.20.0 fixed CVE-2018-18074; it must NOT receive DEP-GHSA-x84v-xcm2-53pg."
    ),
    BenchmarkFixture(
        fixture_id="SAFE-DEP-CERTIFI-001",
        name="Safe Dependency Package: certifi 2024.8.30 (Zero Active Advisories)",
        category="Clean Code",
        file_path="requirements.txt",
        content="certifi==2024.8.30\n",
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="certifi 2024.8.30 has 0 active advisories in OSV database."
    ),
    BenchmarkFixture(
        fixture_id="SCOPED-NPM-001",
        name="Scoped npm Package: @jridgewell/gen-mapping@0.3.13",
        category="Clean Code",
        file_path="package-lock.json",
        content=(
            '{\n'
            '  "name": "benchmark-scoped",\n'
            '  "version": "1.0.0",\n'
            '  "lockfileVersion": 3,\n'
            '  "packages": {\n'
            '    "": { "name": "benchmark-scoped", "version": "1.0.0" },\n'
            '    "node_modules/@jridgewell/gen-mapping": {\n'
            '      "version": "0.3.13"\n'
            '    }\n'
            '  }\n'
            '}\n'
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Must preserve @jridgewell/ scope without triggering unscoped malware alerts."
    ),
    BenchmarkFixture(
        fixture_id="MALFORMED-MANIFEST-001",
        name="Malformed Dependency Manifest Handling",
        category="Clean Code",
        file_path="requirements.txt",
        content=(
            "# Malformed requirements file lines\n"
            "invalid===syntax??\n"
            "--unknown-pip-flag\n"
        ),
        expected_findings_count=0,
        is_vulnerable=False,
        uncertainty_notes="Malformed syntax must be handled gracefully without crashing or emitting false alarms."
    ),

    # =========================================================================
    # 10. Context & Line-Shift Stability
    # =========================================================================
    BenchmarkFixture(
        fixture_id="FIXTURE-STR-001",
        name="Vulnerability Pattern inside Test String Literal",
        category="Vulnerability",
        file_path="tests/test_mock_scanner.py",
        content=(
            "def test_sqli_detection():\n"
            '    fixture_payload = """cursor.execute("SELECT * FROM users WHERE id = " + user_input)"""\n'
            "    assert 'SELECT' in fixture_payload\n"
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Intentional test fixture or demonstration example",
        is_vulnerable=False,
        uncertainty_notes="Code inside string literal within a test file. Must be classified as Test Fixture with 0 pt deduction."
    ),
    BenchmarkFixture(
        fixture_id="EXEC-CODE-001",
        name="Same Vulnerability Pattern in Executable Runtime Code",
        category="Vulnerability",
        file_path="app/production_query.py",
        content=(
            "def fetch_user_data(cursor, user_input):\n"
            '    return cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n'
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Executable code in production runtime. Must be classified as Confirmed vulnerability."
    ),
    BenchmarkFixture(
        fixture_id="SHIFT-CODE-001",
        name="Same Code Pattern with Added Header Lines (Line Shift)",
        category="Vulnerability",
        file_path="app/production_query_shifted.py",
        content=(
            "# Header documentation comment 1\n"
            "# Header documentation comment 2\n"
            "# Header documentation comment 3\n"
            "# Header documentation comment 4\n"
            "# Header documentation comment 5\n"
            "def fetch_user_data(cursor, user_input):\n"
            '    return cursor.execute("SELECT * FROM users WHERE id = " + user_input)\n'
        ),
        expected_findings_count=1,
        expected_rule_id="SEC-SQLI-001",
        expected_category="Vulnerability",
        expected_severity="High",
        expected_classification="Confirmed vulnerability or exposure",
        is_vulnerable=True,
        uncertainty_notes="Line shifted from line 2 to line 7. Code snippet fingerprint must match identically."
    ),
]
