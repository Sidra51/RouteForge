import logging
from typing import Dict, Any, List
import openai
from openai import AsyncOpenAI
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

class GroqProvider(BaseProvider):
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]

    async def generate_chat(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        api_key: str
    ) -> Dict[str, Any]:
        if not api_key or api_key.lower().strip() in ["mock", ""]:
            import asyncio
            await asyncio.sleep(0.3)  # simulate latency
            simulated_text = f"[Mock Groq Response] Gateway routing worked for {model}. Here is a simulated response to: \"{message[:40]}...\""
            prompt_tokens = len(message) // 4
            completion_tokens = len(simulated_text) // 4
            return {
                "response_text": simulated_text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "error": None
            }

        # Groq's API is compatible with the OpenAI Python SDK
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            response = await client.chat.completions.create(**kwargs)

            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
            else:
                prompt_tokens = len(message) // 4
                completion_tokens = len(response.choices[0].message.content or "") // 4
                total_tokens = prompt_tokens + completion_tokens

            return {
                "response_text": response.choices[0].message.content or "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "error": None
            }

        except openai.OpenAIError as e:
            logger.error(f"Groq API error: {e}", exc_info=True)
            return {
                "response_text": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}", exc_info=True)
            return {
                "response_text": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }
