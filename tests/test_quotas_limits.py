import json
import urllib.request
import urllib.error
import uuid
import time

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
            status_code = response.status
            res_body = response.read().decode("utf-8")
            return status_code, json.loads(res_body) if res_body else None
    except urllib.error.HTTPError as e:
        status_code = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status_code, json.loads(res_body)
        except:
            return status_code, res_body
    except Exception as e:
        print(f"Connection error: {e}")
        return None, None

def run_tests():
    print("==================================================")
    print("LLM GATEWAY: PHASE 4 QUOTAS & LIMITS INTEGRATION TEST")
    print("==================================================")
    
    # 1. Register a new user
    email = f"quota_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecretpassword123"
    print(f"\n[Step 1] Registering user: {email}...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/register",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 201, f"Failed registration: {status} - {res}"
    print("[OK] User registered successfully.")

    # 2. Login
    print(f"\n[Step 2] Logging in...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 200, f"Failed login: {status} - {res}"
    access_token = res["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    print("[OK] Logged in successfully.")

    # 3. Check default quota (Free plan)
    print(f"\n[Step 3] Checking initial quota for 'free' plan...")
    status, res = make_request(
        f"{BASE_URL}/api/usage/quota",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching quota status: {status} - {res}"
    assert res["plan"] == "free", f"Expected free plan, got {res['plan']}"
    assert res["request_limit"] == 100, f"Expected 100 requests limit, got {res['request_limit']}"
    assert res["token_limit"] == 100000, f"Expected 100,000 token limit, got {res['token_limit']}"
    assert res["requests_today"] == 0, f"Expected 0 requests today, got {res['requests_today']}"
    assert res["tokens_this_month"] == 0, f"Expected 0 tokens this month, got {res['tokens_this_month']}"
    print(f"[OK] Initial quota is correct: plan={res['plan']}, requests_today={res['requests_today']}/{res['request_limit']}, tokens_this_month={res['tokens_this_month']}/{res['token_limit']}")

    # 4. Test plan upgrade (to Pro plan)
    print(f"\n[Step 4] Upgrading user plan to 'pro'...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/upgrade",
        method="PATCH",
        headers=auth_headers,
        data={"plan_type": "pro"}
    )
    assert status == 200, f"Failed upgrading plan: {status} - {res}"
    assert res["plan_type"] == "pro", f"Expected plan_type to be pro, got {res['plan_type']}"
    print("[OK] Plan upgraded to Pro database-side.")

    # Verify upgrade reflected in quota endpoint
    status, res = make_request(
        f"{BASE_URL}/api/usage/quota",
        method="GET",
        headers=auth_headers
    )
    assert status == 200
    assert res["plan"] == "pro"
    assert res["request_limit"] == 1000
    assert res["token_limit"] == 1000000
    print("[OK] Quota endpoint reflects Pro limits.")

    # 5. Create API key with a very low RPM override (2 RPM)
    print(f"\n[Step 5] Creating API Key with custom override: 2 RPM limit...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Low RPM Key", "rate_limit_rpm": 2}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    raw_key = res["api_key"]
    gateway_headers = {"Authorization": f"Bearer {raw_key}"}
    print(f"[OK] API Key created with override. rate_limit_rpm={res['rate_limit_rpm']}")

    # 6. Test Key RPM limits
    print(f"\n[Step 6] Verifying rate limit enforcement (2 RPM)...")
    chat_payload = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "message": "Hi, answer in 1 word",
        "temperature": 0.5,
        "max_tokens": 10,
        "bypass_cache": True
    }
    
    print("Sending Request 1 (should succeed)...")
    status1, res1 = make_request(f"{BASE_URL}/api/gateway/chat", method="POST", headers=gateway_headers, data=chat_payload)
    assert status1 == 200, f"Request 1 failed: status={status1}, res={res1}"
    print(f"[OK] Request 1 succeeded.")
    
    print("Sending Request 2 (should succeed)...")
    status2, res2 = make_request(f"{BASE_URL}/api/gateway/chat", method="POST", headers=gateway_headers, data=chat_payload)
    assert status2 == 200, f"Request 2 failed: status={status2}, res={res2}"
    print(f"[OK] Request 2 succeeded.")
    
    print("Sending Request 3 (should fail with HTTP 429)...")
    status3, res3 = make_request(f"{BASE_URL}/api/gateway/chat", method="POST", headers=gateway_headers, data=chat_payload)
    assert status3 == 429, f"Request 3 did not fail with 429: status={status3}, res={res3}"
    assert "error" in res3["detail"]
    assert res3["detail"]["error"]["code"] == "rate_limit_exceeded"
    print(f"[OK] Request 3 correctly blocked: {res3['detail']['error']['message']}")

    # 7. Create API key with a very low token quota (1 token)
    print(f"\n[Step 7] Creating API Key with custom override: 1 token quota...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Low Token Key", "monthly_token_quota": 1}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    low_token_raw_key = res["api_key"]
    low_token_headers = {"Authorization": f"Bearer {low_token_raw_key}"}
    print(f"[OK] API Key created with override. monthly_token_quota={res['monthly_token_quota']}")

    # 8. Test Key Token limits
    print(f"\n[Step 8] Verifying token quota enforcement (1 token limit)...")
    print("Sending Request 1 (should succeed since current usage is 0)...")
    status1, res1 = make_request(f"{BASE_URL}/api/gateway/chat", method="POST", headers=low_token_headers, data=chat_payload)
    assert status1 == 200, f"Request 1 failed: status={status1}, res={res1}"
    print(f"[OK] Request 1 succeeded. Used {res1['total_tokens']} tokens.")
    
    print("Sending Request 2 (should fail with HTTP 429 token_quota_exceeded since usage > 1)...")
    status2, res2 = make_request(f"{BASE_URL}/api/gateway/chat", method="POST", headers=low_token_headers, data=chat_payload)
    assert status2 == 429, f"Request 2 did not fail with 429: status={status2}, res={res2}"
    assert "error" in res2["detail"]
    assert res2["detail"]["error"]["code"] == "token_quota_exceeded"
    print(f"[OK] Request 2 correctly blocked: {res2['detail']['error']['message']}")

    # 9. Downgrade plan back to free
    print(f"\n[Step 9] Downgrading plan back to 'free'...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/upgrade",
        method="PATCH",
        headers=auth_headers,
        data={"plan_type": "free"}
    )
    assert status == 200
    assert res["plan_type"] == "free"
    print("[OK] User plan downgraded successfully.")

    print("\n==================================================")
    print("SUCCESS: ALL TESTS PASSED SUCCESSFULLY! Phase 4 works!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
