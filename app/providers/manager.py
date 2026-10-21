from app.providers.base import BaseProvider
from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAIProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.groq import GroqProvider

class ProviderManager:
    _providers = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
        "groq": GroqProvider
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> BaseProvider:
        """Return an instance of the requested provider."""
        provider_cls = cls._providers.get(provider_name.lower())
        if not provider_cls:
            raise ValueError(f"Unsupported provider: {provider_name}")
        return provider_cls()

    @classmethod
    def get_all_providers(cls) -> dict:
        """Return the mapping of all registered provider names to their classes."""
        return cls._providers
