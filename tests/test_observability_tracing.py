import json
import urllib.request
import urllib.error
import uuid
import time

BASE_URL = "http://127.0.0.1:9000"

class CaseInsensitiveDict(dict):
    def __init__(self, d):
        super().__init__({k.lower(): v for k, v in d.items()})
    def get(self, key, default=None):
        return super().get(key.lower(), default)
    def __getitem__(self, key):
        return super().__getitem__(key.lower())
    def __contains__(self, key):
        return super().__contains__(key.lower())

def make_request_with_headers(url, method="GET", headers=None, data=None):
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
            res_headers = CaseInsensitiveDict(response.info())
            return status_code, json.loads(res_body) if res_body else None, res_headers
    except urllib.error.HTTPError as e:
        status_code = e.code
        res_body = e.read().decode("utf-8")
        res_headers = CaseInsensitiveDict(e.headers)
        try:
            return status_code, json.loads(res_body), res_headers
        except:
            return status_code, res_body, res_headers
    except Exception as e:
        print(f"Connection error: {e}")
        return None, None, CaseInsensitiveDict({})

def run_tests():
    print("==================================================")
    print("LLM GATEWAY: PHASE 6 OBSERVABILITY & TRACING TEST SUITE")
    print("==================================================")
    
    # 1. Register a new user
    email = f"trace_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecretpassword123"
    print(f"\n[Step 1] Registering user: {email}...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/auth/register",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 201, f"Failed registration: {status} - {res}"
    print("[OK] User registered.")

    # 2. Login
    print(f"\n[Step 2] Logging in...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 200, f"Failed login: {status} - {res}"
    access_token = res["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    print("[OK] Logged in successfully.")

    # 3. Test Invalid API Key authentication (Verify 401 and X-Trace-ID presence)
    print(f"\n[Step 3] Testing unauthorized chat request with invalid key...")
    status, res, headers = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers={"Authorization": "Bearer gw_live_invalidkey123"},
        data={"message": "Should fail", "max_tokens": 10}
    )
    assert status == 401, f"Expected 401 status, got {status} - {res}"
    trace_id_401 = headers.get("X-Trace-ID")
    print(f"[OK] Got 401 as expected. Header X-Trace-ID = {trace_id_401}")
    assert trace_id_401 is not None, "Missing X-Trace-ID header in 401 response"
    assert trace_id_401.startswith("trace_"), f"Unexpected trace ID format: {trace_id_401}"

    # 4. Create a valid API key
    print(f"\n[Step 4] Creating valid API Key...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Observability Test Key"}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    raw_key = res["api_key"]
    gateway_headers = {"Authorization": f"Bearer {raw_key}"}
    print("[OK] API Key created.")

    # 5. Make a successful chat completion request and verify headers
    print(f"\n[Step 5] Sending successful chat completion request...")
    status, res, headers = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": "Hello, how are you today?",
            "max_tokens": 10
        }
    )
    assert status == 200, f"Chat completion request failed: status={status}, res={res}"
    trace_id_200 = headers.get("X-Trace-ID")
    print(f"[OK] Response status 200. Header X-Trace-ID = {trace_id_200}")
    assert trace_id_200 is not None, "Missing X-Trace-ID header in 200 response"
    assert trace_id_200.startswith("trace_"), f"Unexpected trace ID format: {trace_id_200}"

    # 6. Retrieve Traces list from observability endpoint
    print(f"\n[Step 6] Fetching all traces from observability dashboard...")
    status, traces, _ = make_request_with_headers(
        f"{BASE_URL}/api/observability/traces",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed to fetch traces: status={status}"
    print(f"[OK] Retrieved {len(traces)} traces.")
    
    # We should have at least the successful trace. Note: the unauthorized trace
    # was requested with an invalid key, so it was associated with user_id=None,
    # and won't appear in the current user's list. That's correct and expected!
    matching_trace = [t for t in traces if t["trace_id"] == trace_id_200]
    assert len(matching_trace) > 0, f"Did not find trace {trace_id_200} in user trace list"
    t_summary = matching_trace[0]
    print(f"  - Trace Summary: {t_summary['trace_id']} -> latency={t_summary['total_latency_ms']}ms, attempts={t_summary['attempts_count']}")

    # 7. Fetch Trace Details for successful trace
    print(f"\n[Step 7] Querying detailed timeline and retry records for trace {trace_id_200}...")
    status, t_detail, _ = make_request_with_headers(
        f"{BASE_URL}/api/observability/traces/{trace_id_200}",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching trace details: status={status}"
    
    # Verify structured timeline stages schema
    print("[OK] Trace details retrieved successfully. Verifying schemas:")
    print(f"  - Timeline: {json.dumps(t_detail['timeline'])}")
    print(f"  - Attempts: {json.dumps(t_detail['attempts'])}")
    
    assert len(t_detail["timeline"]) >= 4, f"Expected timeline to contain stages, got {len(t_detail['timeline'])}"
    stages = [s["stage"] for s in t_detail["timeline"]]
    assert "received" in stages, "Missing 'received' stage"
    assert "limits_passed" in stages, "Missing 'limits_passed' stage"
    assert "routing_decision" in stages, "Missing 'routing_decision' stage"
    assert "response_returned" in stages, "Missing 'response_returned' stage"
    
    assert len(t_detail["attempts"]) >= 1, "Expected at least 1 attempt to be logged"
    attempt = t_detail["attempts"][0]
    assert attempt["attempt"] == 1
    assert attempt["status"] == "success"
    assert "provider" in attempt
    assert "model" in attempt
    assert "latency_ms" in attempt
    assert "cost" in attempt
    
    # 8. Fetch Metrics: Provider latency comparison
    print(f"\n[Step 8] Querying provider metrics compare endpoint...")
    status, provider_metrics, _ = make_request_with_headers(
        f"{BASE_URL}/api/observability/metrics/providers",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching provider metrics: status={status}"
    print(f"[OK] Provider compare metrics count: {len(provider_metrics)}")
    for m in provider_metrics:
        print(f"  - {m['provider']}: latency={m['avg_latency_ms']}ms, success={m['success_rate']}%")

    # 9. Fetch Metrics: Error Categories
    print(f"\n[Step 9] Fetching aggregated error categories counts...")
    status, error_counts, _ = make_request_with_headers(
        f"{BASE_URL}/api/observability/metrics/errors",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching error metrics: status={status}"
    print(f"[OK] Error categories counts: {error_counts}")
    assert "rate_limit_exceeded" in error_counts
    assert "token_quota_exceeded" in error_counts
    assert "provider_error" in error_counts
    assert "authentication_error" in error_counts

    # 10. Fetch Metrics: Throughput
    print(f"\n[Step 10] Fetching rolling throughput volumes...")
    status, throughput, _ = make_request_with_headers(
        f"{BASE_URL}/api/observability/metrics/throughput",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed fetching throughput metrics: status={status}"
    print(f"[OK] Throughput counts: {throughput}")
    assert throughput["today"] >= 1
    assert throughput["week"] >= 1
    assert throughput["month"] >= 1
    
    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! OBSERVABILITY HEALTHY")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
