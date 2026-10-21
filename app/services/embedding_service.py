import logging
import hashlib
import asyncio
from typing import List
from google import genai
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    @staticmethod
    def _generate_mock_embedding(text: str, dimensions: int = 768) -> List[float]:
        """
        Generate a deterministic mock vector embedding of unit length.
        Combines character frequency structures (so similar texts get similar vectors)
        with a hash signature to allow testing semantic matches offline.
        """
        # Character frequency distribution
        freq = [0.0] * dimensions
        for c in text:
            idx = ord(c) % dimensions
            freq[idx] += 1.0
            
        # Hashing component to ensure fine-grained deterministic variance
        hash_val = hashlib.sha256(text.encode("utf-8")).digest()
        random_v = []
        for i in range(dimensions):
            mix_val = hashlib.sha256(hash_val + str(i).encode("utf-8")).hexdigest()
            val = int(mix_val[:8], 16) / 4294967295.0
            random_v.append(val - 0.5)
            
        # Combine: 80% character distribution + 20% random hash signature
        combined = [0.8 * freq[i] + 0.2 * random_v[i] for i in range(dimensions)]
        
        # Normalize to unit length
        norm = sum(x * x for x in combined) ** 0.5
        if norm == 0.0:
            return [0.0] * dimensions
        return [x / norm for x in combined]

    @classmethod
    async def get_embedding(cls, text: str, provider: str = None) -> List[float]:
        """
        Fetch the embedding vector for the given text based on config/provider settings.
        Falls back to the mock generator if the API key is missing or set to 'mock'.
        """
        prov = (provider or settings.EMBEDDING_PROVIDER).lower()
        
        if prov == "openai":
            api_key = settings.OPENAI_API_KEY
            if not api_key or api_key.lower().strip() == "mock":
                logger.debug("Using mock embedding vector for OpenAI.")
                return cls._generate_mock_embedding(text, dimensions=1536)
            
            try:
                client = AsyncOpenAI(api_key=api_key)
                response = await client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Failed to generate OpenAI embedding: {e}. Falling back to mock.")
                return cls._generate_mock_embedding(text, dimensions=1536)
                
        # Default/Gemini fallback
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key.lower().strip() == "mock":
            logger.debug("Using mock embedding vector for Gemini.")
            return cls._generate_mock_embedding(text, dimensions=768)
            
        try:
            client = genai.Client(api_key=api_key)
            # Use aio.models to ensure async execution
            response = await client.aio.models.embed_content(
                model="gemini-embedding-2",
                contents=text
            )
            # embed_content returns a list of embedding structures, extract values list
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to generate Gemini embedding: {e}. Falling back to mock.")
            return cls._generate_mock_embedding(text, dimensions=768)
