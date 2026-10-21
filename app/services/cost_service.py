from typing import Tuple, List
from app.providers.pricing import MODEL_PRICING

class CostService:
    @staticmethod
    def calculate_token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate USD transaction cost for a model and token counts."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("gemini-2.5-flash"))
        input_cost = prompt_tokens * pricing["input"]
        output_cost = completion_tokens * pricing["output"]
        return input_cost + output_cost

    @staticmethod
    def get_cheapest_model_for_providers(providers: List[str]) -> Tuple[str, str]:
        """
        Find the model with the lowest average (input + output) cost per token among the given providers.
        Returns a tuple of (provider_name, model_name).
        """
        from app.providers.manager import ProviderManager
        
        cheapest_provider = "gemini"
        cheapest_model = "gemini-2.5-flash"
        min_cost = float("inf")
        
        for provider_name in providers:
            provider_lc = provider_name.lower()
            provider_cls = ProviderManager.get_all_providers().get(provider_lc)
            if not provider_cls:
                continue
            for model in provider_cls.get_supported_models():
                pricing = MODEL_PRICING.get(model)
                if pricing:
                    # Determine average cost per token
                    avg_cost = (pricing["input"] + pricing["output"]) / 2.0
                    if avg_cost < min_cost:
                        min_cost = avg_cost
                        cheapest_model = model
                        cheapest_provider = provider_lc
                        
        return cheapest_provider, cheapest_model
