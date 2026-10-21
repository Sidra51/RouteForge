import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:9000"

def make_request(url, method="GET", headers=None, data=None):
    if headers is None:
        headers = {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return 500, str(e)

def test_endpoints():
    print("Authenticating as sidra@example.com...")
    # Register/Login
    # Let's try login first, if login fails try registering
    status, res = make_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"email": "sidra@example.com", "password": "password123"}
    )
    if status != 200:
        # Try default/common password if user set it differently, or try register
        print(f"Login failed: {status} - {res}. Trying register...")
        status, res = make_request(
            f"{BASE_URL}/api/auth/register",
            method="POST",
            data={"email": "sidra@example.com", "password": "password123"}
        )
        if status not in (200, 201):
            print(f"Register failed: {status} - {res}")
            sys.exit(1)
        # Login now
        status, res = make_request(
            f"{BASE_URL}/api/auth/login",
            method="POST",
            data={"email": "sidra@example.com", "password": "password123"}
        )
        if status != 200:
            print("Login failed after register.")
            sys.exit(1)
            
    token = res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully. Access token retrieved.")
    
    endpoints = [
        ("/api/usage", "fetchUsageData"),
        ("/api/api-keys", "fetchKeysData"),
        ("/api/usage/quota", "fetchQuotaData"),
        ("/api/providers/health", "fetchProviderHealthData (health check)"),
        ("/api/observability/traces", "fetchObservabilityData"),
        ("/api/cache/stats", "fetchCacheStats")
    ]
    
    for path, label in endpoints:
        print(f"\nTesting endpoint: {path} ({label})...")
        status, res = make_request(f"{BASE_URL}{path}", headers=headers)
        if status == 200:
            print(f"[SUCCESS] Status: {status}")
        else:
            print(f"[FAILED] Status: {status} - Response: {res}")

if __name__ == "__main__":
    test_endpoints()
