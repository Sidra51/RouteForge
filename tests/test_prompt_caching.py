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
    print("LLM GATEWAY: PHASE 7 PROMPT CACHING TEST SUITE")
    print("==================================================")
    
    # 1. Register a new user
    email = f"cache_test_{uuid.uuid4().hex[:8]}@example.com"
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

    # 3. Create a valid API key
    print(f"\n[Step 3] Creating valid API Key...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Cache Test Key"}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    raw_key = res["api_key"]
    gateway_headers = {"Authorization": f"Bearer {raw_key}"}
    print("[OK] API Key created.")

    # 4. First Chat Request (Cache Miss)
    suffix = uuid.uuid4().hex
    prompt = f"Explain the concept of {suffix} in detail."
    print(f"\n[Step 4] Sending first prompt (Cache Miss): '{prompt}'...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": prompt,
            "max_tokens": 10
        }
    )
    assert status == 200, f"First chat request failed: {res}"
    assert "cache" in res, "Missing cache metadata in response"
    assert res["cache"]["hit"] is False, f"Expected cache hit False, got {res['cache']}"
    print(f"[OK] Cache missed. Upstream model: {res['provider']} ({res['model']}) used.")

    # 5. Second Chat Request (Exact Cache Hit)
    print(f"\n[Step 5] Sending exact same prompt (Exact Cache Hit)...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": prompt,
            "max_tokens": 10
        }
    )
    assert status == 200, f"Second chat request failed: {res}"
    assert res["cache"]["hit"] is True, f"Expected cache hit True, got {res['cache']}"
    assert res["cache"]["type"] == "exact", f"Expected cache type 'exact', got {res['cache']}"
    assert res["cost"] == 0.0, f"Expected cached cost to be 0.0, got {res['cost']}"
    print(f"[OK] Exact cache hit! Served instantly with 0 cost.")

    # 6. Third Chat Request (Semantic Cache Hit)
    similar_prompt = f"Explain the concept of {suffix} in detail?!"
    print(f"\n[Step 6] Sending semantically similar prompt (Semantic Cache Hit): '{similar_prompt}'...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": similar_prompt,
            "max_tokens": 10
        }
    )
    assert status == 200, f"Third chat request failed: {res}"
    assert res["cache"]["hit"] is True, f"Expected cache hit True, got {res['cache']}"
    assert res["cache"]["type"] == "semantic", f"Expected cache type 'semantic', got {res['cache']}"
    assert res["cache"]["similarity"] >= 0.90, f"Expected similarity >= 0.90, got {res['cache']}"
    assert res["cost"] == 0.0, f"Expected cached cost to be 0.0, got {res['cost']}"
    print(f"[OK] Semantic cache hit! Similarity: {res['cache']['similarity']:.4f}")

    # 7. Fourth Chat Request (Bypass Cache)
    print(f"\n[Step 7] Sending prompt with bypass_cache=True...")
    status, res, _ = make_request_with_headers(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "routing_policy": "cheapest",
            "message": prompt,
            "max_tokens": 10,
            "bypass_cache": True
        }
    )
    assert status == 200, f"Bypass cache request failed: {res}"
    assert res["cache"]["hit"] is False, f"Expected cache hit False with bypass, got {res['cache']}"
    assert res["cost"] > 0.0, f"Expected cost to be > 0.0 since cache was bypassed, got {res['cost']}"
    print(f"[OK] Caching successfully bypassed.")

    # 8. Check Cache Stats
    print(f"\n[Step 8] Querying Cache Stats...")
    status, stats, _ = make_request_with_headers(
        f"{BASE_URL}/api/cache/stats",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Stats request failed: {stats}"
    print(f"[OK] Cache Stats retrieved: {stats}")
    assert stats["total_requests"] == 4, f"Expected 4 requests logged, got {stats['total_requests']}"
    assert stats["exact_hits"] == 1, f"Expected 1 exact hit, got {stats['exact_hits']}"
    assert stats["semantic_hits"] == 1, f"Expected 1 semantic hit, got {stats['semantic_hits']}"
    assert stats["total_hits"] == 2, f"Expected 2 total hits, got {stats['total_hits']}"
    assert stats["hit_rate"] == 0.5, f"Expected 0.5 hit rate, got {stats['hit_rate']}"
    assert stats["spend_saved"] > 0.0, f"Expected spend saved to be > 0.0, got {stats['spend_saved']}"
    assert stats["average_latency_saved_ms"] >= 0.0, f"Expected latency saved to be >= 0.0, got {stats['average_latency_saved_ms']}"

    # 9. Check Cache List
    print(f"\n[Step 9] Querying Cache List...")
    status, cache_list, _ = make_request_with_headers(
        f"{BASE_URL}/api/cache/list",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"List request failed: {cache_list}"
    assert len(cache_list) >= 1, "Expected cache list to have entries"
    # Find matching cached prompt
    entry = [e for e in cache_list if e["prompt"] == prompt][0]
    print(f"[OK] Cached entry found in global list: hit_count={entry['hit_count']}, last_similarity={entry['last_similarity_score']}, model={entry['embedding_model']}, dim={entry['embedding_dimension']}")
    assert entry["hit_count"] >= 1, f"Expected hit count >= 1, got {entry['hit_count']}"
    assert entry["embedding_dimension"] in (768, 1536, 3072), f"Unexpected embedding dimension: {entry['embedding_dimension']}"
    
    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! PROMPT CACHING IS LIVE")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
