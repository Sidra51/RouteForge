import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Loaded API Key starting with: {api_key[:10]}... (length: {len(api_key)})")

try:
    # Initialize Google GenAI client
    client = genai.Client(api_key=api_key)
    
    print("\n--- Trying to list models on v1beta (default) ---")
    models = list(client.models.list())
    print(f"Successfully retrieved {len(models)} models:")
    for model in models[:5]:  # print first 5 models
        print(f" - {model.name}")
        
except Exception as e:
    print(f"Failed on v1beta: {str(e)}")

try:
    # Try forcing API v1 instead of v1beta
    client_v1 = genai.Client(api_key=api_key, http_options={"api_version": "v1"})
    print("\n--- Trying to list models on v1 ---")
    models_v1 = list(client_v1.models.list())
    print(f"Successfully retrieved {len(models_v1)} models on v1:")
    for model in models_v1[:5]:
        print(f" - {model.name}")
except Exception as e:
    print(f"Failed on v1: {str(e)}")
