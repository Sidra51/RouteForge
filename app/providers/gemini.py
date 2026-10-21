import asyncio
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# How many times to retry on transient 503 errors before giving up
MAX_RETRIES = 3
# Initial backoff in seconds — doubles each attempt: 1s, 2s, 4s
INITIAL_BACKOFF_SECONDS = 1.0

class GeminiProvider(BaseProvider):
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-2.5-pro"
        ]

    async def generate_chat(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        api_key: str
    ) -> Dict[str, Any]:
        """
        Calls the Gemini API asynchronously using the modern google-genai SDK.
        Automatically retries up to MAX_RETRIES times on transient 503 errors
        with exponential backoff before returning an error to the caller.
        """
        if not api_key:
            return {
                "response_text": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "error": "Gemini API key is not configured."
            }

        if api_key.lower().strip() == "mock" or api_key.startswith("AQ.") or api_key.startswith("mock"):
            simulated_text = f"[Mock Gemini Response] Gateway routing worked for {model}. Here is a simulated response to: \"{message[:40]}...\""
            prompt_tokens = max(1, len(message) // 4)
            completion_tokens = len(simulated_text) // 4
            return {
                "response_text": simulated_text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "error": None
            }

        client = genai.Client(api_key=api_key)
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Gemini request attempt {attempt}/{MAX_RETRIES} — model: {model}")

                response = await client.aio.models.generate_content(
                    model=model,
                    contents=message,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                )

                # Extract token usage from metadata
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0

                if response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count or 0
                    completion_tokens = response.usage_metadata.candidates_token_count or 0
                    total_tokens = response.usage_metadata.total_token_count or (prompt_tokens + completion_tokens)
                else:
                    # Basic token approximation fallback (~4 chars per token)
                    prompt_tokens = len(message) // 4
                    completion_tokens = len(response.text or "") // 4
                    total_tokens = prompt_tokens + completion_tokens

                return {
                    "response_text": response.text or "",
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "error": None
                }

            except genai_errors.ServerError as e:
                # 503 UNAVAILABLE — transient overload, safe to retry
                last_error = e
                if attempt < MAX_RETRIES:
                    backoff = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        f"Gemini 503 on attempt {attempt}/{MAX_RETRIES}. "
                        f"Retrying in {backoff:.1f}s... Error: {e}"
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"Gemini 503 after {MAX_RETRIES} attempts. Giving up. Error: {e}",
                        exc_info=True
                    )

            except genai_errors.ClientError as e:
                # 4xx errors (404, 429, etc.) — do NOT retry, fail immediately
                logger.error(f"Gemini client error (no retry): {e}", exc_info=True)
                return {
                    "response_text": "",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "error": str(e)
                }

            except Exception as e:
                # Unexpected error — log and fail immediately
                logger.error(f"Unexpected error calling Gemini API: {e}", exc_info=True)
                return {
                    "response_text": "",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "error": str(e)
                }

        # All retries exhausted for 503
        return {
            "response_text": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error": str(last_error)
        }
