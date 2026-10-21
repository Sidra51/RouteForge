import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite-001",
    "gemini-1.5-pro"
]

for m in models:
    print(f"\n--- Testing model: {m} ---")
    try:
        response = client.models.generate_content(
            model=m,
            contents="Hello, response test."
        )
        print(f"Success: {response.text}")
    except Exception as e:
        print(f"Error for {m}: {type(e).__name__}: {str(e)}")
