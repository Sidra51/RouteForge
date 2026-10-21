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
    print("LLM GATEWAY: PHASE 9 PROMPT REGISTRY & EVAL TEST")
    print("==================================================")
    
    # 1. Register/Login test user
    email = f"prompt_eval_{uuid.uuid4().hex[:8]}@example.com"
    password = "evalpassword123"
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
    token = res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] User registered and logged in successfully.")

    # 2. Create Prompt Template
    print(f"\n[Step 2] Creating Prompt Template...")
    template_name = f"support_replier_{uuid.uuid4().hex[:6]}"
    status, template = make_request(
        f"{BASE_URL}/api/prompts",
        method="POST",
        headers=headers,
        data={
            "name": template_name,
            "description": "Customer support reply assistant",
            "tags": ["support", "billing"]
        }
    )
    assert status == 201, f"Failed template creation: {status} - {template}"
    template_id = template["id"]
    print(f"[OK] Prompt template '{template_name}' registered. ID: {template_id}")

    # 3. Create Version 1 (Active Default)
    print(f"\n[Step 3] Registering Version 1 (Active default)...")
    status, v1 = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/versions",
        method="POST",
        headers=headers,
        data={
            "version": "v1",
            "description": "Standard greeting reply template",
            "system_prompt": "You are a support agent named {{support_agent}}.",
            "user_prompt": "Help customer {{customer_name}} with request: {{customer_query}}.",
            "is_active": True
        }
    )
    assert status == 201, f"Failed v1 creation: {status} - {v1}"
    print(f"[OK] Version 1 registered as active default. ID: {v1['id']}")

    # 4. Create Version 2 (Inactive)
    print(f"\n[Step 4] Registering Version 2 (Inactive)...")
    status, v2 = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/versions",
        method="POST",
        headers=headers,
        data={
            "version": "v2",
            "description": "Formal greeting reply template",
            "system_prompt": "You are a professional representative for support. Agent name: {{support_agent}}.",
            "user_prompt": "Please assist customer {{customer_name}} regarding: {{customer_query}}.",
            "is_active": False
        }
    )
    assert status == 201, f"Failed v2 creation: {status} - {v2}"
    print(f"[OK] Version 2 registered. ID: {v2['id']}")

    # 5. Dry-run Variable Validation & Rendering Preview API
    print(f"\n[Step 5] Testing Playground Render/Validation Preview endpoint...")
    status, preview = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/preview",
        method="POST",
        headers=headers,
        data={
            "system_prompt": v1["system_prompt"],
            "user_prompt": v1["user_prompt"],
            "variables": {
                "support_agent": "John",
                "customer_name": "Alice",
                "customer_query": "Change my email billing settings"
            }
        }
    )
    assert status == 200, f"Preview failed: {status} - {preview}"
    assert preview["valid"] is True, f"Preview should be valid: {preview}"
    assert "John" in preview["rendered_system"]
    assert "Alice" in preview["rendered_user"]
    print("[OK] Valid variables render preview test passed successfully.")

    # 5b. Verify validation errors for missing/unused/empty variables
    print(f"\n[Step 5b] Verifying variable validation errors...")
    status, preview_invalid = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/preview",
        method="POST",
        headers=headers,
        data={
            "system_prompt": v1["system_prompt"],
            "user_prompt": v1["user_prompt"],
            "variables": {
                "support_agent": "", # empty value
                "customer_name": "Alice",
                "extra_var": "unused" # unknown/unused variable
                # "customer_query" is missing entirely
            }
        }
    )
    assert status == 200, f"Preview failed: {status}"
    assert preview_invalid["valid"] is False, "Preview should report validation failure"
    errors = preview_invalid["errors"]
    assert "missing" in errors
    assert "empty" in errors
    assert "unknown" in errors
    print("[OK] Prompt variables validation checks failed and reported correctly as expected.")

    # 6. Create Gateway API Key
    print(f"\n[Step 6] Creating API Key for routing requests...")
    status, key_res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=headers,
        data={"name": "Eval testing key"}
    )
    assert status == 201, f"Failed API Key creation: {status}"
    gateway_token = key_res["api_key"]
    gateway_headers = {"Authorization": f"Bearer {gateway_token}"}
    print(f"[OK] Gateway Key created: {gateway_token[:15]}...")


    # 7. Execute Request with default active version (v1)
    print(f"\n[Step 7] Routing request using prompt template default version (v1)...")
    status, chat_res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "prompt_template_name": template_name,
            "variables": {
                "support_agent": "Marcus",
                "customer_name": "Bob",
                "customer_query": "Reset my gateway password"
            }
        }
    )
    assert status == 200, f"Gateway chat failed: {status} - {chat_res}"
    req_id = chat_res["request_id"]
    print(f"[OK] Gateway template request completed. Trace request ID: {req_id}")

    # 8. Submit manual evaluation feedback rating (4.5 stars)
    print(f"\n[Step 8] Logging manual developer feedback to the request trace...")
    status, feedback = make_request(
        f"{BASE_URL}/api/observability/traces/{req_id}/feedback",
        method="POST",
        headers=headers,
        data={
            "rating": 4.5,
            "justification": "Manual prompt playground rating."
        }
    )
    assert status == 200, f"Feedback submission failed: {status} - {feedback}"
    print(f"[OK] Feedback logged to RequestTrace: {feedback['scores']}")

    # 9. Setup A/B Split Experiment (50% v1, 50% v2)
    print(f"\n[Step 9] Deploying A/B Split Experiment...")
    status, experiment = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/experiment",
        method="POST",
        headers=headers,
        data={
            "name": "Version 1 vs Version 2 A/B Split",
            "is_active": True,
            "variants": [
                {"version_id": v1["id"], "weight": 0.5},
                {"version_id": v2["id"], "weight": 0.5}
            ]
        }
    )
    assert status == 200, f"Failed experiment deployment: {status} - {experiment}"
    print(f"[OK] A/B Experiment deployed. Variants splits: 50% v1, 50% v2")

    # 10. Execute A/B test calls to test weighted split choice
    print(f"\n[Step 10] Executing 6 split gateway requests to record metrics for both versions...")
    v1_count = 0
    v2_count = 0
    
    for i in range(6):
        status, chat_res = make_request(
            f"{BASE_URL}/api/gateway/chat",
            method="POST",
            headers=gateway_headers,
            data={
                "prompt_template_name": template_name,
                "variables": {
                    "support_agent": "Marcus",
                    "customer_name": "Bob",
                    "customer_query": f"Query iteration {i}"
                }
            }
        )
        assert status == 200, f"Gateway chat failed at index {i}"
        
        # Wait a short moment for async task evaluator to register simulated judge scores
        time.sleep(0.5)

    # 11. Fetch evaluation metrics analytics comparison
    print(f"\n[Step 11] Retrieving comparative performance analytics...")
    status, metrics = make_request(
        f"{BASE_URL}/api/prompts/{template_id}/eval",
        method="GET",
        headers=headers
    )
    assert status == 200, f"Failed to retrieve evaluation analytics: {status}"
    
    print("\n================ EVALUATION SUMMARY ================")
    for v in metrics["versions"]:
        print(f"Version: {v['version_str']}")
        print(f" - Total calls logged: {v['total_calls']}")
        print(f" - Success rate: {v['success_rate']}%")
        print(f" - Avg Latency: {v['avg_latency_ms']} ms")
        print(f" - Avg Cost: ${v['avg_cost']:.6f}")
        print(f" - Judge Ratings (Overall Score): {v['avg_overall_score']:.2f} / 5.0")
        print(f" - Judge Dimensions -> Helpfulness: {v['avg_helpfulness']:.2f}, Accuracy: {v['avg_accuracy']:.2f}, Safety: {v['avg_safety']:.2f}")
    print("====================================================")
    
    assert any(v["total_calls"] > 0 for v in metrics["versions"]), "Some versions should have logged calls"
    print("\n[OK] All Phase 9 prompt registry & evaluation tests passed successfully!")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as ae:
        print(f"\n[FAIL] Test assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
