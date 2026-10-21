from typing import Dict, Any, List

class BaseProvider:
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Return a list of models supported by this provider."""
        raise NotImplementedError

    async def generate_chat(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        api_key: str
    ) -> Dict[str, Any]:
        """
        Execute chat completion against the provider.
        
        Returns:
            Dict containing:
            - response_text: str
            - prompt_tokens: int
            - completion_tokens: int
            - total_tokens: int
            - error: Optional[str]
        """
        raise NotImplementedError
