import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse

# Ensure utf-8 encoding for console output if supported, else safe ASCII
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://localhost:5173"

def print_step(step_num, title):
    print(f"\n[{step_num}/8] === {title} ===")

def assert_true(condition, message):
    if not condition:
        print(f"  [FAIL] {message}")
        sys.exit(1)
    print(f"  [PASS] {message}")

def make_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    if data is not None and isinstance(data, dict):
        data_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data is not None and isinstance(data, str):
        data_bytes = data.encode("utf-8")
    elif data is not None and isinstance(data, bytes):
        data_bytes = data
    else:
        data_bytes = None

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8", errors="ignore")
            try:
                json_data = json.loads(body)
            except Exception:
                json_data = None
            return status_code, json_data, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            json_data = json.loads(body)
        except Exception:
            json_data = None
        return e.code, json_data, body
    except Exception as e:
        return 0, None, str(e)

def main():
    print("=" * 70)
    print("  EXECUTING COMPLETE END-TO-END (E2E) TEST SUITE")
    print("  Testing: Backend API, Auth, Runner, Triage, SSRF, System Tests & UI")
    print("=" * 70)
    total_start = time.time()

    # Step 1: Health & API Discovery
    print_step(1, "Testing Backend Health & Documentation Endpoints")
    code, json_data, _ = make_request(f"{API_BASE}/health")
    assert_true(code == 200, f"Backend /health returned HTTP {code}")
    assert_true(json_data.get("status") == "healthy", "Health check payload reports healthy status")

    code, _, _ = make_request(f"{API_BASE}/docs")
    assert_true(code == 200, "Swagger UI /docs is reachable and returning HTTP 200")

    # Step 2: Authentication & User Registration E2E Lifecycle
    print_step(2, "Testing User Registration & JWT Authentication Flow")
    timestamp = int(time.time())
    test_email = f"e2e_user_{timestamp}@example.com"
    test_user = f"e2e_{timestamp}"
    test_pwd = "E2ePassword123!"

    reg_payload = {"email": test_email, "username": test_user, "password": test_pwd}
    code, json_data, body = make_request(f"{API_BASE}/auth/register", method="POST", data=reg_payload)
    assert_true(code in [200, 201], f"User registration returned HTTP {code}")
    assert_true(json_data and "id" in json_data, f"New user created with ID {json_data.get('id') if json_data else 'unknown'}")

    # Login to obtain JWT
    login_data = f"username={urllib.parse.quote(test_user)}&password={urllib.parse.quote(test_pwd)}".encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_payload = json.loads(resp.read().decode("utf-8"))
    
    access_token = token_payload.get("access_token")
    assert_true(bool(access_token), "JWT access token successfully acquired from /auth/login")
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Step 3: Target Inventory Management
    print_step(3, "Testing Target Scope & Whitelist Management")
    target_payload = {
        "name": f"E2E Target {timestamp}",
        "host": "scanme.nmap.org",
        "description": "Automated E2E target scope item"
    }
    code, json_data, body = make_request(f"{API_BASE}/targets", method="POST", data=target_payload, headers=auth_headers)
    assert_true(code in [200, 201], f"Target creation returned HTTP {code}")
    target_id = json_data.get("id")
    assert_true(bool(target_id), f"Target persisted in database with ID {target_id}")

    code, targets_list, _ = make_request(f"{API_BASE}/targets", headers=auth_headers)
    assert_true(code == 200 and any(t["id"] == target_id for t in targets_list), "Target list correctly returns newly created target")

    # Step 4: Security Command Runner & Preset Verification
    print_step(4, "Testing Security Command Configuration & Run History")
    code, commands, _ = make_request(f"{API_BASE}/commands", headers=auth_headers)
    assert_true(code == 200 and len(commands) > 0, f"Command presets loaded ({len(commands)} commands available)")
    
    cmd_names = [c["name"] for c in commands]
    assert_true("Ping Latency Diagnostic" in cmd_names, "Ping Latency Diagnostic preset verified")
    assert_true("HTTPS TLS Header Audit" in cmd_names, "HTTPS TLS Header Audit preset verified")
    assert_true("Nmap Security Port Scan" in cmd_names, "Nmap Security Port Scan preset verified")

    code, runs_list, _ = make_request(f"{API_BASE}/runs", headers=auth_headers)
    assert_true(code == 200 and isinstance(runs_list, list), "Run history endpoint accessible and returns list")

    # Step 5: Log & ZIP Archive Triage
    print_step(5, "Testing Log & Code Vulnerability Triage")
    sample_log = """
    [ERROR] 2026-10-15 11:42:01 Database connection failed: SQL syntax error near 'SELECT * FROM users WHERE name = '' OR '1'='1''
    [WARN] Insecure legacy protocol detected on port 21/open (FTP)
    [INFO] Server listening on 0.0.0.0:8000
    """
    triage_payload = {
        "log_text": sample_log
    }
    code, triage_res, _ = make_request(f"{API_BASE}/runs/analyze-manual", method="POST", data=triage_payload, headers=auth_headers)
    assert_true(code == 200, f"Manual log triage returned HTTP {code}")
    assert_true(triage_res and "findings" in triage_res and len(triage_res["findings"]) > 0, f"Triage rules engine identified {len(triage_res.get('findings', []))} security findings")

    # Step 6: Edge Diagnostics & SSRF Protection
    print_step(6, "Testing Edge Latency Diagnostics & SSRF Protection")
    # Legitimate URL
    code, speed_res, _ = make_request(
        f"{API_BASE}/runs/url-speed-test",
        method="POST",
        data={"url": "https://example.com"},
        headers=auth_headers
    )
    assert_true(code == 200 and speed_res.get("success") is True, f"Edge diagnostic benchmark returned HTTP 200 (Latency: {speed_res.get('total_time_ms') if speed_res else 'N/A'} ms)")

    # Malicious Loopback URL (SSRF Prevention)
    code, ssrf_res, _ = make_request(
        f"{API_BASE}/runs/url-speed-test",
        method="POST",
        data={"url": "http://127.0.0.1:22"},
        headers=auth_headers
    )
    assert_true(code == 200 and ssrf_res.get("success") is False, "SSRF Protection actively blocked loopback address (Rejected)")
    assert_true("SSRF Protection" in ssrf_res.get("status_text", ""), "Response payload explicitly cites SSRF Protection enforcement")

    # Step 7: System Assurance Suite Verification
    print_step(7, "Testing System Assurance & Diagnostic Test Suite")
    code, suite_res, _ = make_request(f"{API_BASE}/system-tests/run-all")
    assert_true(code == 200, f"System Assurance Suite returned HTTP {code}")
    assert_true(suite_res.get("overall_status") == "passed", "Overall status is 'passed'")
    assert_true(suite_res.get("overall_score") == 100, f"Assurance score is {suite_res.get('overall_score')}% (Optimal Green)")
    assert_true(suite_res.get("passed_tests") == suite_res.get("total_tests"), f"All {suite_res.get('total_tests')} system tests passing")

    # Step 8: Frontend Client & Single Page Routing Assurance
    print_step(8, "Testing Frontend Client & Deep Link Routes")
    code, _, html_content = make_request(FRONTEND_BASE)
    assert_true(code == 200 and '<div id="root">' in html_content, "Frontend root loads successfully with React root element")

    for route in ["/assurance", "/scanner", "/analyzer", "/diagnostics", "/settings/targets", "/dashboard"]:
        code, _, content = make_request(f"{FRONTEND_BASE}{route}")
        assert_true(code == 200 and '<div id="root">' in content, f"Deep route {route} renders cleanly with 200 OK")

    total_time = round(time.time() - total_start, 2)
    print("\n" + "=" * 70)
    print(f"  [SUCCESS] ALL END-TO-END (E2E) TESTS PASSED IN {total_time}s!")
    print("  Platform Status: 100% Fully Verified, Secure, and Operational (Green)")
    print("=" * 70)

if __name__ == "__main__":
    main()
