import logging
from typing import Dict, Any, List
import openai
from openai import AsyncOpenAI
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

class DeepSeekProvider(BaseProvider):
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return ["deepseek-chat", "deepseek-reasoner"]

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
            simulated_text = f"[Mock DeepSeek Response] Gateway routing worked for {model}. Here is a simulated response to: \"{message[:40]}...\""
            prompt_tokens = len(message) // 4
            completion_tokens = len(simulated_text) // 4
            return {
                "response_text": simulated_text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "error": None
            }

        # DeepSeek API utilizes the OpenAI SDK configured with DeepSeek's base URL
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": max_tokens
            }
            
            # DeepSeek reasoner (R1) does not support temperature/top_p parameter customization in the same way,
            # or it should be set to 1. We will only apply temperature for deepseek-chat.
            if model != "deepseek-reasoner":
                kwargs["temperature"] = temperature

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
            logger.error(f"DeepSeek API error: {e}", exc_info=True)
            return {
                "response_text": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error calling DeepSeek API: {e}", exc_info=True)
            return {
                "response_text": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "error": str(e)
            }
