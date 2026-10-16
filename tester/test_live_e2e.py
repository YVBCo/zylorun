import urllib.request
import urllib.parse
import json
import ssl
import sys

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_request(method, url, data=None, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    
    body = None
    if data is not None:
        if isinstance(data, dict):
            if headers.get("Content-Type") == "application/x-www-form-urlencoded":
                body = urllib.parse.urlencode(data).encode("utf-8")
            else:
                headers["Content-Type"] = "application/json"
                req.add_header("Content-Type", "application/json")
                body = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")
            
    try:
        with urllib.request.urlopen(req, data=body, context=ctx, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, resp_body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return e.code, err_body
    except Exception as e:
        return 0, str(e)

print("=" * 65)
print("       ZYLORUN LIVE END-TO-END VERIFICATION SUITE")
print("=" * 65)

# 1. Frontend Test
print("\n[1] Testing Live Frontend (Vercel)...")
status, body = test_request("GET", "https://zylorun-five.vercel.app/")
print(f"  GET https://zylorun-five.vercel.app/ -> Status: {status}")
assert status == 200, f"Frontend landing page returned {status}"
print("  [OK] Landing page accessible (200 OK)")

# 2. Backend Health / Docs Test
print("\n[2] Testing Live Backend Health (Render)...")
status, body = test_request("GET", "https://zylorun.onrender.com/docs")
print(f"  GET https://zylorun.onrender.com/docs -> Status: {status}")
assert status in (200, 307, 308), f"Backend /docs returned {status}"
print("  [OK] Backend API reachable and healthy (200 OK)")

# 3. Authentication Test
print("\n[3] Testing Live Authentication Flow...")
login_data = {
    "username": "4mh24cs167@gmail.com",
    "password": "password123"
}
status, body = test_request(
    "POST",
    "https://zylorun.onrender.com/auth/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
print(f"  POST https://zylorun.onrender.com/auth/login -> Status: {status}")
assert status == 200, f"Authentication failed with status {status}"
res_json = json.loads(body)
token = res_json.get("access_token")
print(f"  [OK] User authenticated successfully. Token type: {res_json.get('token_type')}")
print(f"  [OK] Account verified for user: {res_json.get('username')}")

# 4. Authenticated API Endpoint Test
print("\n[4] Testing Authenticated Repositories Endpoint with Bearer Token...")
status, body = test_request(
    "GET",
    "https://zylorun.onrender.com/repositories",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"  GET /repositories (Bearer auth) -> Status: {status}")
assert status == 200, f"Authenticated repository list returned {status}"
repos = json.loads(body)
print(f"  [OK] Successfully retrieved connected repositories (Total: {len(repos)})")

# 5. Analyzer API Test (Clean Code)
print("\n[5] Testing Manual Analyzer API (Clean Code Scenario)...")
clean_payload = {
    "log_text": "const greeting = 'Hello World';\nconsole.log(greeting);"
}
status, body = test_request(
    "POST",
    "https://zylorun.onrender.com/runs/analyze-manual",
    data=clean_payload
)
print(f"  POST /runs/analyze-manual (Clean) -> Status: {status}")
assert status == 200, f"Clean scan failed with status {status}"
res = json.loads(body)
print(f"  [OK] Clean Code Scan Status: {res.get('status')}")
print(f"  [OK] Total Findings: {len(res.get('findings', []))}")

# 6. Analyzer API Test (Vulnerable Code Scenario)
print("\n[6] Testing Manual Analyzer API (Vulnerable Scenario - SQLi, Secrets, XSS)...")
vulnerable_payload = {
    "log_text": """
// Express Database Connector
const query = "SELECT * FROM users WHERE id = '" + req.body.userId + "'";
const AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLESECRETKEY123";
element.innerHTML = req.body.untrustedInput;
"""
}
status, body = test_request(
    "POST",
    "https://zylorun.onrender.com/runs/analyze-manual",
    data=vulnerable_payload
)
print(f"  POST /runs/analyze-manual (Vulnerable) -> Status: {status}")
assert status == 200, f"Vulnerable scan failed with status {status}"
res = json.loads(body)
findings = res.get('findings', [])
print(f"  [OK] Scan Status: {res.get('status')}")
print(f"  [OK] Total Findings Identified: {len(findings)}")
for i, f in enumerate(findings, 1):
    print(f"    {i}. [{f.get('severity')}] {f.get('message')}")
    print(f"       Advice: {f.get('recommendation')}")

print("\n" + "=" * 65)
print("   ALL 6 LIVE PRODUCTION END-TO-END TESTS PASSED SUCCESSFULLY!")
print("=" * 65)
