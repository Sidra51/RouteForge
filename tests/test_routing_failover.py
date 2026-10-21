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
    print("LLM GATEWAY: PHASE 5 ROUTING & FAILOVER TEST SUITE")
    print("==================================================")
    
    # 1. Register a new user
    email = f"failover_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecretpassword123"
    print(f"\n[Step 1] Registering user: {email}...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/register",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 201, f"Failed registration: {status} - {res}"
    print("[OK] User registered.")

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

    # 3. Create API key for gateway queries
    print(f"\n[Step 3] Creating API Key...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Failover Test Key"}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    raw_key = res["api_key"]
    gateway_headers = {"Authorization": f"Bearer {raw_key}"}
    print("[OK] API Key created.")

    # 4. Check initial health states
    print(f"\n[Step 4] Querying provider metrics health endpoint...")
    status, res = make_request(
        f"{BASE_URL}/api/providers/health",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching health: {status} - {res}"
    print(f"[OK] Health endpoint returned: {len(res)} providers.")
    for metric in res:
        print(f"  - {metric['provider']}: status={metric['status']}, avg_latency={metric['avg_latency_ms']}ms, success={metric['success_rate']}%, requests={metric['total_requests']}, failures={metric['total_failures']}")
        assert metric["status"] in ["healthy", "degraded", "unhealthy"]
        assert metric["total_requests"] >= 0

    # 5. Test cheapest policy
    print(f"\n[Step 5] Routing request using 'cheapest' policy...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": "Hello, who are you?",
            "max_tokens": 10
        }
    )
    assert status == 200, f"Cheapest query failed: status={status}, res={res}"
    print(f"[OK] Routed to provider: {res['provider']} (Model: {res['model']})")

    # 6. Test best quality policy
    print(f"\n[Step 6] Routing request using 'best_quality' policy...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "best_quality",
            "message": "Hello, who are you?",
            "max_tokens": 10
        }
    )
    assert status == 200, f"Quality query failed: status={status}, res={res}"
    print(f"[OK] Routed to provider: {res['provider']} (Model: {res['model']})")
    # By configuration rankings: openai has quality_rank=1, so it should route to openai (gpt-4o-mini default)
    assert res["provider"] == "openai"

    # 7. Test Auto Policy
    print(f"\n[Step 7] Routing request using 'auto' policy (short prompt)...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "auto",
            "message": "Hi",
            "max_tokens": 10
        }
    )
    assert status == 200, f"Auto short query failed: status={status}, res={res}"
    print(f"[OK] Short prompt routed to: {res['provider']} (Model: {res['model']})")

    print(f"Routing request using 'auto' policy (long prompt >= 500 chars)...")
    long_msg = "Please write a comprehensive response. " * 20 # > 500 characters
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "auto",
            "message": long_msg,
            "max_tokens": 10
        }
    )
    assert status == 200, f"Auto long query failed: status={status}, res={res}"
    print(f"[OK] Long prompt routed to: {res['provider']} (Model: {res['model']})")
    assert res["provider"] == "openai", "Expected long prompt to route to OpenAI (best quality)"

    # 8. Test Automatic Provider Failover (Targeting Groq which should fail and fall back)
    print(f"\n[Step 8] Testing automatic failover (Targeting 'groq' directly, which should fail)...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "provider": "groq",
            "model": "non-existent-model-xyz",
            "message": "Hello, answer in one word.",
            "max_tokens": 10
        }
    )
    # The request should succeed overall (return 200) because it automatically falls back
    assert status == 200, f"Failover query failed: status={status}, res={res}"
    print(f"[OK] Request succeeded using fallback provider: {res['provider']} (Model: {res['model']})")
    # Verify it did NOT use groq
    assert res["provider"] != "groq"

    # 9. Verify metrics record the failure of groq
    print(f"\n[Step 9] Verifying circuit breaker health tracking...")
    status, res = make_request(
        f"{BASE_URL}/api/providers/health",
        method="GET",
        headers=auth_headers
    )
    assert status == 200
    groq_metric = next((m for m in res if m["provider"] == "groq"), None)
    assert groq_metric is not None, "Groq metrics missing."
    print(f"[OK] Groq metric: status={groq_metric['status']}, requests={groq_metric['total_requests']}, failures={groq_metric['total_failures']}")
    
    # Assert that Groq has logged requests and failures
    assert groq_metric["total_requests"] > 0
    assert groq_metric["total_failures"] > 0
    assert groq_metric["status"] in ["degraded", "unhealthy"]

    print("\n==================================================")
    print("SUCCESS: ALL TESTS PASSED SUCCESSFULLY! Phase 5 works!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
