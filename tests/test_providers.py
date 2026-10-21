import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Add project root to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.providers.manager import ProviderManager
from app.core.config import settings

async def test_provider(provider_name: str, model_name: str):
    print(f"\n--- Testing Provider: {provider_name} (Model: {model_name}) ---")
    try:
        # 1. Resolve Provider via Manager
        provider = ProviderManager.get_provider(provider_name)
        print(f"[OK] Resolved provider class: {provider.__class__.__name__}")
        
        # 2. Check Supported Models
        supported = provider.get_supported_models()
        print(f"[OK] Supported models: {supported}")
        assert model_name in supported, f"Model {model_name} is not in supported list!"

        # 3. Resolve API Key
        api_keys_map = {
            "gemini": settings.GEMINI_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "groq": settings.GROQ_API_KEY
        }
        api_key = api_keys_map.get(provider_name, "")
        
        # 4. Generate Chat (Will return config error if key is empty)
        print(f"Calling generate_chat (API Key exists: {bool(api_key and api_key.strip())})...")
        response = await provider.generate_chat(
            model=model_name,
            message="Say hello in exactly 3 words.",
            temperature=0.7,
            max_tokens=20,
            api_key=api_key
        )
        
        print(f"Response: {response}")
        if response.get("error"):
            print(f"[WARNING] Provider returned error (expected if key is unconfigured): {response['error']}")
        else:
            print(f"[SUCCESS] Successful response: {response['response_text']}")
            print(f"[SUCCESS] Tokens used: {response['total_tokens']} (In: {response['prompt_tokens']}, Out: {response['completion_tokens']})")
            
    except Exception as e:
        print(f"[ERROR] Failed test for {provider_name}: {e}")

async def main():
    print("Starting Multi-Provider LLM Gateway Test Suite")
    
    # Test Gemini
    await test_provider("gemini", "gemini-2.5-flash")
    
    # Test OpenAI
    await test_provider("openai", "gpt-4o-mini")
    
    # Test DeepSeek
    await test_provider("deepseek", "deepseek-chat")

    # Test Groq
    await test_provider("groq", "llama-3.1-8b-instant")

if __name__ == "__main__":
    asyncio.run(main())
