import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class LangfuseService:
    _client = None
    _enabled = False

    @classmethod
    def init(cls):
        """Initialize the Langfuse client if API keys exist in the environment."""
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                from langfuse import Langfuse
                cls._client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                cls._enabled = True
                logger.info("Langfuse Tracing Client initialized successfully.")
            except ImportError:
                logger.warning("langfuse package is not installed but API keys are configured.")
                cls._enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse client: {e}")
                cls._enabled = False
        else:
            cls._enabled = False

    @classmethod
    def get_client(cls):
        """Return the initialized Langfuse client or None if disabled."""
        if not cls._enabled:
            return None
        return cls._client

    @classmethod
    def create_trace(cls, trace_id: str, user_id: str, name: str, input_text: str):
        """Create an overall request trace in Langfuse."""
        if not cls._enabled or not cls._client:
            return None
        try:
            return cls._client.trace(
                id=trace_id,
                name=name,
                user_id=str(user_id) if user_id else None,
                input=input_text
            )
        except Exception as e:
            logger.error(f"Langfuse failed to log trace creation: {e}")
            return None

    @classmethod
    def log_generation(
        cls,
        trace_obj,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        input_text: str,
        output_text: str,
        latency_ms: int,
        cost: float
    ):
        """Log an LLM generation run event inside the trace."""
        if not cls._enabled or not trace_obj:
            return
        try:
            trace_obj.generation(
                name=f"{provider}-{model}",
                model=model,
                input=input_text,
                output=output_text,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "unit": "TOKENS"
                },
                metadata={
                    "provider": provider,
                    "latency_ms": latency_ms,
                    "cost_usd": cost
                }
            )
        except Exception as e:
            logger.error(f"Langfuse failed to log generation step: {e}")

    @classmethod
    def log_error(cls, trace_obj, error_msg: str):
        """Log trace failure updates to Langfuse."""
        if not cls._enabled or not trace_obj:
            return
        try:
            trace_obj.update(
                output=f"Error: {error_msg}",
                metadata={
                    "error": True,
                    "error_message": error_msg
                }
            )
        except Exception as e:
            logger.error(f"Langfuse failed to log trace error: {e}")
