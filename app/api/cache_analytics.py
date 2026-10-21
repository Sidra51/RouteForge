import logging
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.usage import UsageLog
from app.models.cached_prompt import CachedPrompt

logger = logging.getLogger(__name__)
router = APIRouter()

class CacheStatsResponse(BaseModel):
    total_requests: int
    exact_hits: int
    semantic_hits: int
    total_hits: int
    hit_rate: float
    tokens_saved: int
    spend_saved: float
    average_latency_saved_ms: float

class CachedPromptResponse(BaseModel):
    id: uuid.UUID
    prompt: str
    response: str
    provider: str
    model: str
    hit_count: int
    last_similarity_score: Optional[float] = None
    embedding_dimension: int
    embedding_model: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve prompt caching analytics for the authenticated user.
    Calculates hit rates, saved cost, saved tokens, and average latency saved.
    """
    try:
        stmt = select(UsageLog).where(UsageLog.user_id == current_user.id)
        res = await db.execute(stmt)
        logs = res.scalars().all()
        
        total_requests = len(logs)
        exact_hits = sum(1 for log in logs if log.cache_type == "exact")
        semantic_hits = sum(1 for log in logs if log.cache_type == "semantic")
        total_hits = exact_hits + semantic_hits
        
        hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
        tokens_saved = sum(log.total_tokens for log in logs if log.cache_type in ("exact", "semantic"))
        spend_saved = float(sum(log.cost_saved or 0.0 for log in logs if log.cache_type in ("exact", "semantic")))
        
        # Calculate Average Latency Saved
        # Average Latency of non-cached successful calls
        miss_logs = [log for log in logs if log.cache_type == "none" and log.status_code == 200]
        # Average Latency of cached calls
        hit_logs = [log for log in logs if log.cache_type in ("exact", "semantic")]
        
        avg_miss_latency = (sum(log.latency_ms for log in miss_logs) / len(miss_logs)) if miss_logs else 1000.0
        avg_hit_latency = (sum(log.latency_ms for log in hit_logs) / len(hit_logs)) if hit_logs else 0.0
        
        # Latency Saved = Non-cached average latency - Cached latency
        average_latency_saved = max(0.0, avg_miss_latency - avg_hit_latency) if hit_logs else 0.0
        
        return CacheStatsResponse(
            total_requests=total_requests,
            exact_hits=exact_hits,
            semantic_hits=semantic_hits,
            total_hits=total_hits,
            hit_rate=round(hit_rate, 4),
            tokens_saved=tokens_saved,
            spend_saved=round(spend_saved, 6),
            average_latency_saved_ms=round(average_latency_saved, 2)
        )
    except Exception as e:
        logger.error(f"Failed to fetch cache stats for user {current_user.id}: {e}")
        return CacheStatsResponse(
            total_requests=0,
            exact_hits=0,
            semantic_hits=0,
            total_hits=0,
            hit_rate=0.0,
            tokens_saved=0,
            spend_saved=0.0,
            average_latency_saved_ms=0.0
        )

@router.get("/list", response_model=List[CachedPromptResponse])
async def get_cached_prompts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all globally cached prompts.
    """
    try:
        stmt = select(CachedPrompt).order_by(CachedPrompt.created_at.desc()).limit(100)
        res = await db.execute(stmt)
        prompts = res.scalars().all()
        return prompts
    except Exception as e:
        logger.error(f"Failed to fetch cached prompts: {e}")
        return []
