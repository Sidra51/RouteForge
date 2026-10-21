import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

candidate_models = [
    "gemini-2.0-flash-lite-001",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

print("Starting model connectivity tests...\n")

for model in candidate_models:
    print(f"Testing model: {model}...")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say 'Hello' back."
        )
        print(f"[SUCCESS] Response: '{response.text.strip()}'\n")
    except Exception as e:
        print(f"[FAILED] Error: {str(e)}\n")
