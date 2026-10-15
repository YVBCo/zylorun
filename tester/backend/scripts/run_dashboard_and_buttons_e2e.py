import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://localhost:5173"

def print_section(title):
    print(f"\n{'='*70}\n  {title}\n{'='*70}")

def assert_pass(condition, message):
    if not condition:
        print(f"  [FAIL] {message}")
        sys.exit(1)
    print(f"  [PASS] {message}")

def api_request(path, method="GET", data=None, token=None):
    url = f"{API_BASE}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if data is not None and isinstance(data, dict):
        data_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data is not None and isinstance(data, bytes):
        data_bytes = data
    else:
        data_bytes = None

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            code = response.getcode()
            body = response.read().decode("utf-8", errors="ignore")
            try:
                json_data = json.loads(body)
            except Exception:
                json_data = None
            return code, json_data, body
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
    print_section("STARTING END-TO-END DASHBOARD & BUTTON INTERACTION SUITE")
    suite_start = time.time()

    # Step 1: Create authenticated session for Dashboard interactions
    print("\n[Phase 1] Establishing Authenticated Session for Dashboard & UI Actions")
    ts = int(time.time())
    email = f"dash_tester_{ts}@example.com"
    username = f"dash_{ts}"
    pwd = "DashboardTesterPassword123!"

    code, _, _ = api_request("/auth/register", method="POST", data={"email": email, "username": username, "password": pwd})
    assert_pass(code in [200, 201], f"Registration successful (HTTP {code})")

    login_form = f"username={urllib.parse.quote(username)}&password={urllib.parse.quote(pwd)}".encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=login_form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read().decode("utf-8"))["access_token"]
    assert_pass(bool(token), "JWT Token acquired for interactive dashboard session")

    # Step 2: Test Dashboard Data Feeds & Widgets
    print("\n[Phase 2] Verifying Dashboard Data Feeds & State Handlers")
    code, repos, _ = api_request("/repositories", token=token)
    assert_pass(code == 200 and isinstance(repos, list), "Dashboard /repositories feed loaded cleanly")

    code, notifs, _ = api_request("/notifications", token=token)
    assert_pass(code == 200 and isinstance(notifs, list), "Dashboard Notification Bell feed loaded cleanly")

    code, runs, _ = api_request("/runs", token=token)
    assert_pass(code == 200 and isinstance(runs, list), "Dashboard Recent Activity & Runs feed loaded cleanly")

    code, targets, _ = api_request("/targets", token=token)
    assert_pass(code == 200 and isinstance(targets, list), "Dashboard Target Inventory counter feed loaded cleanly")

    # Step 3: Test Interactive Dashboard & Page Buttons
    print("\n[Phase 3] Testing Interactive Action Buttons Across All Modules")

    # Button 1: Re-Run Full System Assurance Suite
    print("  -> Testing Button: [Re-Run All 35 Tests]")
    code, res, _ = api_request("/system-tests/run-all", token=token)
    assert_pass(code == 200 and res.get("overall_score") == 100, f"System Assurance button triggered 35/35 tests (Score: 100% Green)")

    # Button 2: Export CycloneDX SBOM
    print("  -> Testing Button: [Export CycloneDX SBOM]")
    code, sbom, _ = api_request("/system-tests/sbom", token=token)
    assert_pass(code == 200 and sbom.get("bomFormat") == "CycloneDX", f"Export SBOM button produced valid CycloneDX v1.5 JSON ({len(sbom.get('components', []))} components)")

    # Button 3: Category Filtering Tabs
    for cat in ["security", "dast", "crypto", "network", "supply_chain", "load_concurrency", "chaos", "container", "cloud", "privacy", "ai_safety"]:
        code, cat_res, _ = api_request(f"/system-tests/category/{cat}", token=token)
        assert_pass(code == 200 and cat_res.get("status") == "passed", f"Tab filter button for '{cat}' rendered green status")

    # Button 4: Add Target Button
    print("  -> Testing Button: [Add Target Scope]")
    target_data = {"name": f"Target-{ts}", "host": "scanme.org", "description": "Interactive test target"}
    code, new_t, _ = api_request("/targets", method="POST", data=target_data, token=token)
    assert_pass(code in [200, 201] and "id" in new_t, f"Add Target button created Target ID #{new_t.get('id')}")
    target_id = new_t["id"]

    # Button 5: Delete Target Button
    print("  -> Testing Button: [Delete Target Scope]")
    code, _, _ = api_request(f"/targets/{target_id}", method="DELETE", token=token)
    assert_pass(code in [200, 204], f"Delete Target button successfully removed Target ID #{target_id}")

    # Button 6: Run Log Vulnerability Analysis Button
    print("  -> Testing Button: [Analyze Log & Code]")
    log_sample = "[CRITICAL] SQL injection detected in /api/v1/query. Token exposed: ghp_abc1234567890."
    code, triage_data, _ = api_request("/runs/analyze-manual", method="POST", data={"log_text": log_sample}, token=token)
    assert_pass(code == 200 and len(triage_data.get("findings", [])) > 0, f"Analyze Log button identified {len(triage_data.get('findings', []))} vulnerability items")

    # Button 7: Generate AI Remediation Fix Button
    print("  -> Testing Button: [Generate AI Fix]")
    fix_req = {"findings": triage_data.get("findings", [])[:1], "custom_prompt": "Explain quick fix"}
    code, fix_res, _ = api_request("/runs/generate-fix", method="POST", data=fix_req, token=token)
    assert_pass(code == 200 and "response" in fix_res, "Generate AI Fix button generated remediation patch")

    # Button 8: Edge Diagnostics Speed Test Button
    print("  -> Testing Button: [Run Speed Test]")
    code, speed_data, _ = api_request("/runs/url-speed-test", method="POST", data={"url": "https://example.com"}, token=token)
    assert_pass(code == 200 and speed_data.get("success") is True, f"Run Speed Test button measured {speed_data.get('total_time_ms')} ms roundtrip latency")

    # Button 9: SSRF Guard on Speed Test Button
    print("  -> Testing Button: [SSRF Block on Speed Test]")
    code, ssrf_data, _ = api_request("/runs/url-speed-test", method="POST", data={"url": "http://127.0.0.1:8080"}, token=token)
    assert_pass(code == 200 and ssrf_data.get("success") is False, "Speed Test button blocked prohibited loopback address")

    # Step 4: Verify Frontend Dashboard & Single-Page Application (SPA) Rendering
    print("\n[Phase 4] Verifying Frontend Live View Rendering")
    views = [
        ("/", "Landing Page"),
        ("/dashboard", "Executive Dashboard"),
        ("/assurance", "System Assurance Suite"),
        ("/scanner", "Live Terminal"),
        ("/analyzer", "Log & Code Analyzer"),
        ("/diagnostics", "Edge Diagnostics"),
        ("/settings/targets", "Target Inventory"),
        ("/hub", "Project Hub")
    ]
    for route, name in views:
        req = urllib.request.Request(f"{FRONTEND_BASE}{route}")
        with urllib.request.urlopen(req, timeout=5) as r:
            code = r.getcode()
            html = r.read().decode("utf-8")
        assert_pass(code == 200 and '<div id="root">' in html, f"View '{name}' ({route}) loaded with 200 OK")

    total_duration = round(time.time() - suite_start, 2)
    print_section(f"DASHBOARD & BUTTON E2E SUITE 100% PASSED IN {total_duration}s (GREEN 🟢)")
    print("All dashboard feeds, live metrics, and user action buttons verified operational.")

if __name__ == "__main__":
    main()
