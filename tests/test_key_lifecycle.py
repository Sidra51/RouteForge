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
    print("LLM GATEWAY: PHASE 3 KEY LIFECYCLE INTEGRATION TEST")
    print("==================================================")
    
    # 1. Register a new user
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
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

    # 3. Create API key with expiration
    print(f"\n[Step 3] Creating API Key with name 'Initial Key' and 30 day expiration...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="POST",
        headers=auth_headers,
        data={"name": "Initial Key", "expires_in_days": 30}
    )
    assert status == 201, f"Failed key creation: {status} - {res}"
    key_id = res["id"]
    raw_key = res["api_key"]
    expires_at = res["expires_at"]
    print(f"[OK] Key generated: prefix={res['key_prefix']}, id={key_id}")
    assert expires_at is not None, "Expires_at should be populated."
    assert res["usage"]["total_requests"] == 0, "Initial usage requests should be 0."

    # 4. Rename API Key
    print(f"\n[Step 4] Renaming API Key to 'Renamed Key'...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys/{key_id}",
        method="PATCH",
        headers=auth_headers,
        data={"name": "Renamed Key"}
    )
    assert status == 200, f"Failed renaming: {status} - {res}"
    assert res["name"] == "Renamed Key", "Name did not update."
    print("[OK] Key renamed successfully.")

    # 5. List keys and check usage nesting
    print(f"\n[Step 5] Listing API keys to verify nested usage summary structure...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed listing: {status} - {res}"
    assert len(res) >= 1, "Keys list empty."
    target_key = next((k for k in res if k["id"] == key_id), None)
    assert target_key is not None, "Key not in list."
    assert "usage" in target_key, "Usage nested key missing."
    assert target_key["usage"]["total_requests"] == 0, "Usage count incorrect."
    print("[OK] List keys returns correct nested usage model.")

    # 6. Deactivate API Key
    print(f"\n[Step 6] Deactivating API Key...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys/{key_id}/deactivate",
        method="PATCH",
        headers=auth_headers
    )
    assert status == 200, f"Failed deactivation: {status} - {res}"
    assert res["is_active"] is False, "Key is still active."
    print("[OK] Key deactivated.")

    # 7. Test Gateway request blocks on deactivated key
    print(f"\n[Step 7] Testing that gateway blocks request with deactivated key...")
    gateway_headers = {"Authorization": f"Bearer {raw_key}"}
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "provider": "gemini",
            "model": "gemini-2.0-flash-lite-001",
            "message": "Hello",
            "temperature": 0.7,
            "max_tokens": 10
        }
    )
    assert status == 401, f"Deactivated key did not return 401: status={status}"
    print("[OK] Gateway request correctly blocked with 401 Unauthorized.")

    # 8. Activate API Key
    print(f"\n[Step 8] Reactivating API Key...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys/{key_id}/activate",
        method="PATCH",
        headers=auth_headers
    )
    assert status == 200, f"Failed activation: {status} - {res}"
    assert res["is_active"] is True, "Key is still inactive."
    print("[OK] Key reactivated.")

    # 9. Test Gateway request works on activated key
    print(f"\n[Step 9] Sending request through Gateway (mocking OpenAI provider)...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers=gateway_headers,
        data={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "message": "Explain quantum computing in 3 words.",
            "temperature": 0.5,
            "max_tokens": 20
        }
    )
    assert status == 200, f"Gateway request failed: status={status}, res={res}"
    print(f"[OK] Gateway query succeeded: response='{res['response_text']}'")

    # 10. Check key usage increments
    print(f"\n[Step 10] Verifying key usage aggregation has updated...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed listing: {status}"
    target_key = next((k for k in res if k["id"] == key_id), None)
    assert target_key is not None
    assert target_key["usage"]["total_requests"] == 1, f"Expected 1 request, got {target_key['usage']['total_requests']}"
    assert target_key["usage"]["total_cost"] > 0, f"Expected cost > 0, got {target_key['usage']['total_cost']}"
    print(f"[OK] Key usage stats logged successfully: requests={target_key['usage']['total_requests']}, cost={target_key['usage']['total_cost']}")

    # 11. Rotate key (verify expiration carryover)
    print(f"\n[Step 11] Rotating the API Key...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys/{key_id}/rotate",
        method="POST",
        headers=auth_headers
    )
    assert status == 200, f"Failed rotation: {status} - {res}"
    new_key_id = res["id"]
    new_raw_key = res["api_key"]
    new_expires_at = res["expires_at"]
    new_name = res["name"]
    print(f"[OK] Key rotated. New key prefix: {res['key_prefix']}")
    assert new_key_id != key_id, "Rotated key ID should be different."
    assert new_expires_at == expires_at, f"Expiration date mismatch: original={expires_at}, rotated={new_expires_at}"
    assert new_name == "Renamed Key", f"Name mismatch: expected 'Renamed Key', got '{new_name}'"
    print("[OK] Checked expiration and name carryover successfully.")

    # 12. Check old key deactivated/deleted and new key active
    print(f"\n[Step 12] Listing keys to confirm old key is removed/soft-deleted and new key is visible...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="GET",
        headers=auth_headers
    )
    assert status == 200, f"Failed listing: {status}"
    # The old key should not be in the list anymore (soft-deleted)
    assert not any(k["id"] == key_id for k in res), "Old rotated key is still in listing!"
    # The new key should be in the list
    new_key_meta = next((k for k in res if k["id"] == new_key_id), None)
    assert new_key_meta is not None, "New key is missing from listing."
    assert new_key_meta["is_active"] is True, "New rotated key is not active."
    print("[OK] Verified list reflects rotation.")

    # 13. Check old key authorization fails and new key succeeds
    print(f"\n[Step 13] Verifying authorization for old raw key fails...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers={"Authorization": f"Bearer {raw_key}"},
        data={"provider": "openai", "model": "gpt-4o-mini", "message": "Hi", "temperature": 0.5, "max_tokens": 10}
    )
    assert status == 401, f"Old key should be revoked, got status={status}"
    print("[OK] Old key properly rejected.")

    print(f"Verifying authorization for new rotated raw key succeeds...")
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers={"Authorization": f"Bearer {new_raw_key}"},
        data={"provider": "openai", "model": "gpt-4o-mini", "message": "Hi in one word", "temperature": 0.5, "max_tokens": 10}
    )
    assert status == 200, f"New rotated key query failed: status={status}, res={res}"
    print("[OK] New key properly authorized and routed.")

    # 14. Soft delete new key
    print(f"\n[Step 14] Soft-deleting the new API Key...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys/{new_key_id}",
        method="DELETE",
        headers=auth_headers
    )
    assert status == 204, f"Failed soft deletion: status={status}"
    print("[OK] Soft-delete request returned 204 No Content.")

    # 15. Verify listing is empty and new key fails
    print(f"\n[Step 15] Confirming soft-deleted key is removed from user listing and rejected by Gateway...")
    status, res = make_request(
        f"{BASE_URL}/api/api-keys",
        method="GET",
        headers=auth_headers
    )
    assert not any(k["id"] == new_key_id for k in res), "Soft deleted key is still in user listing!"
    
    status, res = make_request(
        f"{BASE_URL}/api/gateway/chat",
        method="POST",
        headers={"Authorization": f"Bearer {new_raw_key}"},
        data={"provider": "openai", "model": "gpt-4o-mini", "message": "Hi", "temperature": 0.5, "max_tokens": 10}
    )
    assert status == 401, f"Soft-deleted key authorized query! status={status}"
    print("[OK] Soft-deleted key successfully hidden from listing and blocked from routing.")

    print("\n==================================================")
    print("SUCCESS: ALL TESTS PASSED SUCCESSFULLY! Phase 3 works!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
