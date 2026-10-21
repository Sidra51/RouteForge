import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:9000"

def make_request(raw_key, payload):
    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {raw_key}"
    }
    req = urllib.request.Request(f"{BASE_URL}/api/gateway/chat", data=req_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        status_code = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status_code, json.loads(res_body)
        except:
            return status_code, res_body
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def main():
    if len(sys.argv) < 2:
        print("Usage: .\\venv\\Scripts\\python.exe -m tests.test_rpm_manual <YOUR_RAW_API_KEY>")
        return

    raw_key = sys.argv[1].strip()
    
    payload = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "message": "Hi, answer in 1 word.",
        "temperature": 0.7,
        "max_tokens": 10
    }

    print(f"Using Key: {raw_key[:15]}...")
    print("Firing 3 requests in rapid succession...\n")

    for i in range(1, 4):
        print(f"Sending Request {i}...")
        status, response = make_request(raw_key, payload)
        print(f"[Request {i}] Status Code: {status}")
        print(f"[Request {i}] Body: {response}\n")

if __name__ == "__main__":
    main()
