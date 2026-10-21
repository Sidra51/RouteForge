import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, delete, text, func, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cached_prompt import CachedPrompt
from app.core.config import settings
from app.services.rate_limiter import RateLimiterService

logger = logging.getLogger(__name__)

# Local in-memory exact cache fallback if Redis is disabled
_local_exact_cache = {}
_local_cache_expires = {}

class CacheService:
    @staticmethod
    def _get_hash(text: str) -> str:
        """Compute SHA-256 hash of stripped prompt text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def check_exact_match(cls, prompt: str, db: AsyncSession) -> Optional[dict]:
        """
        Check exact prompt match in the Redis cache.
        If Redis is not active, falls back to a local memory cache.
        On success, returns the cached metadata and response, and increments hit counters.
        """
        if not settings.CACHE_ENABLED:
            return None

        prompt_hash = cls._get_hash(prompt)
        redis_key = f"cache:exact:{prompt_hash}"
        cached_data_str = None

        # Try Redis
        if RateLimiterService._use_redis and RateLimiterService._redis_client:
            try:
                cached_data_str = await RateLimiterService._redis_client.get(redis_key)
            except Exception as e:
                logger.error(f"Redis exact cache lookup failed: {e}")
        else:
            # Local memory fallback
            now = datetime.now(timezone.utc).timestamp()
            if prompt_hash in _local_exact_cache:
                if _local_cache_expires.get(prompt_hash, 0) > now:
                    cached_data_str = _local_exact_cache[prompt_hash]
                else:
                    # Prune expired key
                    _local_exact_cache.pop(prompt_hash, None)
                    _local_cache_expires.pop(prompt_hash, None)

        if not cached_data_str:
            return None

        try:
            cached_data = json.loads(cached_data_str)
            
            # Increment hit_count in database in background
            try:
                stmt = select(CachedPrompt).where(CachedPrompt.prompt_hash == prompt_hash)
                res = await db.execute(stmt)
                db_prompt = res.scalar_one_or_none()
                if db_prompt:
                    db_prompt.hit_count += 1
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to increment hit count for exact cache hit: {e}")
                await db.rollback()

            return cached_data
        except Exception as e:
            logger.error(f"Failed to parse exact cache content: {e}")
            return None

    @classmethod
    async def check_semantic_match(
        cls, 
        prompt: str, 
        embedding: list[float], 
        embedding_model: str,
        db: AsyncSession
    ) -> Optional[Tuple[dict, float]]:
        """
        Perform database-level semantic similarity search using PL/pgSQL function.
        Filters candidates by embedding_dimension and embedding_model.
        Orders by similarity descending, fetches candidates, and checks against the threshold.
        On hit, returns the matching response and the cosine similarity score.

        FUTURE UPGRADE PATH:
        JSON Embeddings -> pgvector -> HNSW Indexes
        To scale vector similarity search to millions of rows, replace this JSON PL/pgSQL implementation 
        with pgvector's vector column type: `embedding vector(768)`. Enable indexing by creating 
        an HNSW or IVFFlat index on the embedding:
        `CREATE INDEX ON cached_prompts USING hnsw (embedding vector_cosine_ops);`
        """
        if not settings.CACHE_ENABLED or not embedding:
            return None

        try:
            # Search database candidates ordered by similarity
            # Cut off at 30 days (retention policy limit)
            retention_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            
            stmt = (
                select(
                    CachedPrompt,
                    func.cosine_similarity_json(
                        cast(CachedPrompt.embedding, JSONB),
                        cast(embedding, JSONB)
                    ).label("similarity")
                )
                .where(
                    CachedPrompt.created_at >= retention_cutoff,
                    CachedPrompt.embedding_model == embedding_model,
                    CachedPrompt.embedding_dimension == len(embedding)
                )
                .order_by(text("similarity DESC"))
                .limit(5)
            )
            res = await db.execute(stmt)
            candidates = res.all()
            
            if not candidates:
                return None
                
            # Pick top candidate
            top_record, similarity = candidates[0]
            
            # Check threshold
            if similarity >= settings.SEMANTIC_CACHE_THRESHOLD:
                logger.info(f"Semantic cache hit! Similarity: {similarity:.4f}")
                
                # Increment hit count and update similarity score
                try:
                    top_record.hit_count += 1
                    top_record.last_similarity_score = similarity
                    await db.commit()
                except Exception as e:
                    logger.error(f"Failed to update semantic hit count/similarity: {e}")
                    await db.rollback()
                    
                cached_data = {
                    "response_text": top_record.response,
                    "provider": top_record.provider,
                    "model": top_record.model,
                    "prompt_tokens": top_record.prompt_tokens,
                    "completion_tokens": top_record.completion_tokens,
                    "total_tokens": top_record.total_tokens,
                    "estimated_cost": top_record.estimated_cost
                }
                return cached_data, similarity
                
        except Exception as e:
            logger.error(f"Semantic cache search failed: {e}")
            
        return None

    @classmethod
    async def write_cache(
        cls,
        prompt: str,
        response: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        embedding: list[float],
        embedding_model: str,
        db: AsyncSession
    ):
        """
        Write the prompt generation outcome to both Redis (exact) and PostgreSQL (semantic) caches.
        """
        if not settings.CACHE_ENABLED:
            return

        prompt_hash = cls._get_hash(prompt)
        cache_value = {
            "response_text": response,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost": float(cost)
        }
        cache_str = json.dumps(cache_value)

        # 1. Write to Exact Cache
        if RateLimiterService._use_redis and RateLimiterService._redis_client:
            try:
                redis_key = f"cache:exact:{prompt_hash}"
                await RateLimiterService._redis_client.set(
                    name=redis_key,
                    value=cache_str,
                    ex=settings.CACHE_TTL_SECONDS
                )
            except Exception as e:
                logger.error(f"Failed to write exact cache to Redis: {e}")
        else:
            # Local memory cache write
            _local_exact_cache[prompt_hash] = cache_str
            _local_cache_expires[prompt_hash] = datetime.now(timezone.utc).timestamp() + settings.CACHE_TTL_SECONDS

        # 2. Write to PostgreSQL Semantic Cache
        if embedding:
            try:
                cached_record = CachedPrompt(
                    prompt=prompt.strip(),
                    prompt_hash=prompt_hash,
                    response=response,
                    embedding=embedding,
                    provider=provider,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    estimated_cost=float(cost),
                    hit_count=0,
                    embedding_dimension=len(embedding),
                    embedding_model=embedding_model
                )
                db.add(cached_record)
                await db.commit()
            except Exception as e:
                # Handle unique constraint collision if same prompt was cached concurrently
                logger.warning(f"Failed to write prompt to semantic database cache (possible duplicates): {e}")
                await db.rollback()

    @classmethod
    async def run_cache_cleanup(cls, db: AsyncSession):
        """
        Evict database cache entries older than 30 days to prevent infinite growth.
        Should be invoked via background tasks or startup lifecycle.
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = delete(CachedPrompt).where(CachedPrompt.created_at < cutoff)
            res = await db.execute(stmt)
            await db.commit()
            logger.info(f"Cache cleanup complete. Dropped stale database entries.")
        except Exception as e:
            logger.error(f"Cache cleanup execution failed: {e}")
            await db.rollback()
