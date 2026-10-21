import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from redis.asyncio import Redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings, PLANS
from app.models.usage import UsageLog

logger = logging.getLogger(__name__)

class MemoryStore:
    def __init__(self):
        self._data = {}
        self._expires = {}

    def get(self, key: str) -> Optional[int]:
        self._prune()
        return self._data.get(key)

    def set(self, key: str, value: int, expire: int = None):
        self._data[key] = value
        if expire:
            self._expires[key] = time.time() + expire
        self._prune()

    def incrby(self, key: str, amount: int = 1, expire: int = None) -> int:
        self._prune()
        val = self._data.get(key, 0)
        new_val = val + amount
        self._data[key] = new_val
        if expire and key not in self._expires:
            self._expires[key] = time.time() + expire
        return new_val

    def _prune(self):
        now = time.time()
        expired_keys = [k for k, exp in self._expires.items() if exp < now]
        for k in expired_keys:
            self._data.pop(k, None)
            self._expires.pop(k, None)


class RateLimiterService:
    _redis_client: Optional[Redis] = None
    _memory_store: Optional[MemoryStore] = None
    _use_redis: bool = False

    @classmethod
    async def init(cls):
        """Initialize connection pool to Redis or setup memory store fallback."""
        if settings.REDIS_REQUIRED:
            try:
                cls._redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
                await cls._redis_client.ping()
                cls._use_redis = True
                logger.info("Successfully connected to Redis (Required).")
            except Exception as e:
                logger.error(f"Redis connection failed but REDIS_REQUIRED is True: {e}")
                raise e
        else:
            try:
                cls._redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
                await cls._redis_client.ping()
                cls._use_redis = True
                logger.info("Connected to Redis (Fallback allowed).")
            except Exception as e:
                logger.warning(f"Redis connection failed. Falling back to local memory store: {e}")
                cls._memory_store = MemoryStore()
                cls._use_redis = False

    @classmethod
    async def close(cls):
        """Close Redis client connection pool."""
        if cls._redis_client:
            await cls._redis_client.close()

    @classmethod
    async def check_rate_limit(
        cls, 
        user_id: uuid.UUID, 
        key_id: uuid.UUID, 
        plan_rpm: int, 
        key_rpm_override: Optional[int]
    ) -> bool:
        """
        Increment and check requests per minute (RPM) limits.
        If user RPM or key override RPM is exceeded, return False.
        """
        minute_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        user_key = f"ratelimit:user:{user_id}:{minute_str}"
        key_key = f"ratelimit:key:{key_id}:{minute_str}"
        
        # Determine effective limits
        effective_key_rpm = key_rpm_override if key_rpm_override is not None else plan_rpm
        
        if cls._use_redis:
            # Check User RPM
            user_count = await cls._redis_client.incr(user_key)
            if user_count == 1:
                await cls._redis_client.expire(user_key, 60)
            if user_count > plan_rpm:
                return False
                
            # Check Key Override RPM
            if key_rpm_override is not None:
                key_count = await cls._redis_client.incr(key_key)
                if key_count == 1:
                    await cls._redis_client.expire(key_key, 60)
                if key_count > key_rpm_override:
                    return False
        else:
            # Check User RPM (Memory Fallback)
            user_count = cls._memory_store.incrby(user_key, expire=60)
            if user_count > plan_rpm:
                return False
                
            # Check Key Override RPM (Memory Fallback)
            if key_rpm_override is not None:
                key_count = cls._memory_store.incrby(key_key, expire=60)
                if key_count > key_rpm_override:
                    return False
                    
        return True

    @classmethod
    async def check_daily_request_quota(
        cls, 
        user_id: uuid.UUID, 
        daily_limit: int, 
        db: AsyncSession
    ) -> bool:
        """
        Check if the user has exceeded their plan's daily request limit.
        """
        day_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        quota_key = f"quota:user:requests:{user_id}:{day_str}"
        
        current_val = await cls._get_cached_value(quota_key)
        if current_val is None:
            # Load count from DB and populate cache
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(func.count(UsageLog.id)).where(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= today_start
            )
            res = await db.execute(stmt)
            current_val = res.scalar_one() or 0
            await cls._set_cached_value(quota_key, current_val, expire=86400)
            
        return current_val < daily_limit

    @classmethod
    async def check_monthly_token_quota(
        cls, 
        user_id: uuid.UUID, 
        key_id: uuid.UUID, 
        plan_token_limit: int, 
        key_token_override: Optional[int], 
        db: AsyncSession
    ) -> bool:
        """
        Check monthly token limit consumption for both user plan and key override.
        """
        month_str = datetime.now(timezone.utc).strftime("%Y%m")
        user_key = f"quota:user:tokens:{user_id}:{month_str}"
        key_key = f"quota:key:tokens:{key_id}:{month_str}"
        
        # 1. Verify User Plan Token Limit
        user_tokens = await cls._get_cached_value(user_key)
        if user_tokens is None:
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            stmt = select(func.sum(UsageLog.total_tokens)).where(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= month_start
            )
            res = await db.execute(stmt)
            user_tokens = res.scalar_one() or 0
            await cls._set_cached_value(user_key, user_tokens, expire=2592000) # 30 days
            
        if user_tokens >= plan_token_limit:
            return False
            
        # 2. Verify Key Override Token Limit
        if key_token_override is not None:
            key_tokens = await cls._get_cached_value(key_key)
            if key_tokens is None:
                month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                stmt = select(func.sum(UsageLog.total_tokens)).where(
                    UsageLog.api_key_id == key_id,
                    UsageLog.created_at >= month_start
                )
                res = await db.execute(stmt)
                key_tokens = res.scalar_one() or 0
                await cls._set_cached_value(key_key, key_tokens, expire=2592000)
                
            if key_tokens >= key_token_override:
                return False
                
        return True

    @classmethod
    async def increment_usage(cls, user_id: uuid.UUID, key_id: uuid.UUID, tokens_used: int):
        """
        Increment usage caches in Redis or Memory.
        Consumes 1 daily request and records token counts.
        """
        day_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        month_str = datetime.now(timezone.utc).strftime("%Y%m")
        
        req_key = f"quota:user:requests:{user_id}:{day_str}"
        user_tok_key = f"quota:user:tokens:{user_id}:{month_str}"
        key_tok_key = f"quota:key:tokens:{key_id}:{month_str}"
        
        if cls._use_redis:
            # Increment daily requests
            await cls._redis_client.incr(req_key)
            await cls._redis_client.expire(req_key, 86400)
            
            # Increment user monthly tokens
            await cls._redis_client.incrby(user_tok_key, tokens_used)
            await cls._redis_client.expire(user_tok_key, 2592000)
            
            # Increment key monthly tokens override
            await cls._redis_client.incrby(key_tok_key, tokens_used)
            await cls._redis_client.expire(key_tok_key, 2592000)
        else:
            cls._memory_store.incrby(req_key, amount=1, expire=86400)
            cls._memory_store.incrby(user_tok_key, amount=tokens_used, expire=2592000)
            cls._memory_store.incrby(key_tok_key, amount=tokens_used, expire=2592000)

    @classmethod
    async def get_usage_stats(cls, user_id: uuid.UUID, db: AsyncSession) -> dict:
        """Get today's requests and this month's token count for the user."""
        day_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        month_str = datetime.now(timezone.utc).strftime("%Y%m")
        
        req_key = f"quota:user:requests:{user_id}:{day_str}"
        tok_key = f"quota:user:tokens:{user_id}:{month_str}"
        
        # 1. Daily requests
        requests_today = await cls._get_cached_value(req_key)
        if requests_today is None:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(func.count(UsageLog.id)).where(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= today_start
            )
            res = await db.execute(stmt)
            requests_today = res.scalar_one() or 0
            await cls._set_cached_value(req_key, requests_today, expire=86400)
            
        # 2. Monthly tokens
        tokens_this_month = await cls._get_cached_value(tok_key)
        if tokens_this_month is None:
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            stmt = select(func.sum(UsageLog.total_tokens)).where(
                UsageLog.user_id == user_id,
                UsageLog.created_at >= month_start
            )
            res = await db.execute(stmt)
            tokens_this_month = res.scalar_one() or 0
            await cls._set_cached_value(tok_key, tokens_this_month, expire=2592000)
            
        return {
            "requests_today": requests_today,
            "tokens_this_month": int(tokens_this_month)
        }

    @classmethod
    async def _get_cached_value(cls, key: str) -> Optional[int]:
        """Utility getter for cache keys."""
        if cls._use_redis:
            val = await cls._redis_client.get(key)
            return int(val) if val is not None else None
        else:
            return cls._memory_store.get(key)

    @classmethod
    async def _set_cached_value(cls, key: str, value: int, expire: int):
        """Utility setter for cache keys."""
        if cls._use_redis:
            await cls._redis_client.set(key, value, ex=expire)
        else:
            cls._memory_store.set(key, value, expire=expire)
