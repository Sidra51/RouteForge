import json
import urllib.request
import urllib.error
import uuid
import sys
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
        print(f"Connection error to {url}: {e}")
        return None, None

def run_tests():
    print("==================================================")
    print("LLM GATEWAY: PHASE 10 MODEL EVALUATION & BENCHMARK TEST")
    print("==================================================")
    
    # 1. Register/Login test user
    email = f"benchmark_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "benchmarkpassword123"
    print(f"\n[Step 1] Registering test user: {email}...")
    status, res = make_request(
        f"{BASE_URL}/api/auth/register",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 201, f"Failed registration: {status} - {res}"

    status, res = make_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"email": email, "password": password}
    )
    assert status == 200, f"Failed login: {status} - {res}"
    access_token = res["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print("[OK] User registered and logged in successfully.")

    # 2. Dispatch a Multi-Trial Scientific Model Benchmark Job
    print(f"\n[Step 2] Dispatching 3-trial benchmark across 4 providers (Gemini, OpenAI, Groq, DeepSeek)...")
    job_payload = {
        "name": "Multi-Model Scientific Benchmark Test",
        "prompt": "Explain the concept of quantum entanglement in two short bullet points.",
        "target_models": [
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            {"provider": "openai", "model": "gpt-4o-mini"},
            {"provider": "groq", "model": "llama-3.3-70b-versatile"},
            {"provider": "deepseek", "model": "deepseek-chat"}
        ],
        "trials_count": 3,
        "bypass_cache": True,
        "run_guardrails": False,
        "timeout_seconds": 15
    }
    
    status, job_res = make_request(
        f"{BASE_URL}/api/benchmarks/jobs",
        method="POST",
        headers=headers,
        data=job_payload
    )
    assert status == 201, f"Failed to create benchmark job: {status} - {job_res}"
    job_info = job_res["job"]
    job_id = job_info["id"]
    print(f"[OK] Benchmark Job created successfully. Job ID: {job_id}, Status: {job_info['status']}")

    # 3. Validate Trial Runs and Statistical Metrics
    runs = job_res["runs"]
    metrics_summary = job_res["metrics_summary"]
    print(f"\n[Step 3] Validating executed trial runs ({len(runs)} total runs)...")
    assert len(runs) == 12, f"Expected 12 runs (3 trials x 4 models), found {len(runs)}"

    for r in runs:
        assert r["trace_id"].startswith("trace_bm_"), f"Expected trace_id starting with 'trace_bm_', got {r['trace_id']}"
        assert r["is_success"] is True, f"Run trial {r['trial_number']} for {r['provider']} failed: {r['error_message']}"
    print("[OK] All 12 trial runs completed successfully with valid Phase 6 trace IDs.")

    # 4. Verify Statistical Aggregations (P50, P95, P99, Mean, Throughput, Quality)
    print(f"\n[Step 4] Verifying statistical percentiles and metrics...")
    assert len(metrics_summary) == 4, f"Expected metrics summary for 4 models, found {len(metrics_summary)}"

    for model_key, m in metrics_summary.items():
        print(f"\n --- Model: {m['provider']} / {m['model']} ---")
        print(f"   Success Rate: {m['success_rate']}% ({m['successful_trials']}/{m['total_trials']} trials)")
        print(f"   Latency: Mean={m['mean_latency_ms']}ms | P50={m['p50_latency_ms']}ms | P95={m['p95_latency_ms']}ms | P99={m['p99_latency_ms']}ms | StdDev={m['std_dev_latency_ms']}ms")
        print(f"   Throughput: Gen TPS={m['mean_generation_tps']} | E2E TPS={m['mean_e2e_tps']}")
        print(f"   Cost & Quality: Mean Cost=${m['mean_cost']} | Judge Score={m['mean_quality_score']}/5.0")

        assert m["total_trials"] == 3
        assert m["success_rate"] == 100.0
        assert m["p50_latency_ms"] > 0
        assert m["p95_latency_ms"] >= m["p50_latency_ms"]
        assert m["mean_quality_score"] > 0
    print("\n[OK] Statistical aggregations verified successfully.")

    # 5. Retrieve Job Details API
    print(f"\n[Step 5] Fetching Job Details by ID...")
    status, details_res = make_request(
        f"{BASE_URL}/api/benchmarks/jobs/{job_id}",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Failed to get job details: {status}"
    assert details_res["job"]["id"] == job_id
    assert len(details_res["runs"]) == 12
    print("[OK] Job details retrieved successfully.")

    # 6. Test Multi-Dimensional Model Leaderboard APIs
    print(f"\n[Step 6] Testing Multi-Dimensional Model Leaderboards...")
    
    # Sort by Quality
    status, lb_quality = make_request(
        f"{BASE_URL}/api/benchmarks/leaderboard?sort_by=quality",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Leaderboard quality request failed: {status}"
    assert len(lb_quality) >= 4
    top_quality = lb_quality[0]
    print(f"[OK] Leaderboard (Rank by Quality) Top Model: {top_quality['provider']}/{top_quality['model']} (Score: {top_quality['mean_quality_score']}/5.0)")

    # Sort by Fastest (P50 Latency)
    status, lb_fastest = make_request(
        f"{BASE_URL}/api/benchmarks/leaderboard?sort_by=fastest",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Leaderboard fastest request failed: {status}"
    top_fastest = lb_fastest[0]
    print(f"[OK] Leaderboard (Rank by Fastest P50) Top Model: {top_fastest['provider']}/{top_fastest['model']} (P50: {top_fastest['p50_latency_ms']} ms)")

    # Sort by P95 Latency
    status, lb_p95 = make_request(
        f"{BASE_URL}/api/benchmarks/leaderboard?sort_by=p95",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Leaderboard P95 request failed: {status}"
    top_p95 = lb_p95[0]
    print(f"[OK] Leaderboard (Rank by P95 Latency) Top Model: {top_p95['provider']}/{top_p95['model']} (P95: {top_p95['p95_latency_ms']} ms)")

    # Sort by Cheapest
    status, lb_cheapest = make_request(
        f"{BASE_URL}/api/benchmarks/leaderboard?sort_by=cheapest",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Leaderboard cheapest request failed: {status}"
    top_cheapest = lb_cheapest[0]
    print(f"[OK] Leaderboard (Rank by Cheapest) Top Model: {top_cheapest['provider']}/{top_cheapest['model']} (Mean Cost: ${top_cheapest['mean_cost']})")

    # Sort by Reliability
    status, lb_reliability = make_request(
        f"{BASE_URL}/api/benchmarks/leaderboard?sort_by=reliability",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Leaderboard reliability request failed: {status}"
    top_reliability = lb_reliability[0]
    print(f"[OK] Leaderboard (Rank by Reliability) Top Model: {top_reliability['provider']}/{top_reliability['model']} (Success: {top_reliability['success_rate']}%)")

    print("\n==================================================")
    print("[OK] All Phase 10 Model Evaluation & Benchmark tests passed successfully!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
