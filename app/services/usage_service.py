import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage import UsageLog
from app.schemas.usage import UsageLogResponse, UsageSummaryResponse

class UsageService:
    @staticmethod
    async def log_usage(
        db: AsyncSession,
        user_id: uuid.UUID,
        api_key_id: Optional[uuid.UUID],
        request_id: uuid.UUID,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        latency_ms: int,
        status_code: int,
        error_message: Optional[str] = None,
        trace_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        cache_type: str = "none",
        cost_saved: float = 0.0
    ) -> UsageLog:
        """Create and persist a usage log entry in the database."""
        db_log = UsageLog(
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            status_code=status_code,
            error_message=error_message,
            trace_id=trace_id,
            ip_address=ip_address,
            cache_type=cache_type,
            cost_saved=cost_saved
        )
        db.add(db_log)
        await db.commit()
        await db.refresh(db_log)
        return db_log

    @staticmethod
    async def get_user_usage(
        db: AsyncSession, 
        user_id: uuid.UUID
    ) -> UsageSummaryResponse:
        """Retrieve the usage history and compute aggregate statistics for a user."""
        # Query all logs for this user, ordered by newest first
        stmt = select(UsageLog).where(UsageLog.user_id == user_id).order_by(UsageLog.created_at.desc())
        result = await db.execute(stmt)
        logs_list = list(result.scalars().all())
        
        total_requests = len(logs_list)
        total_prompt_tokens = sum(log.prompt_tokens for log in logs_list)
        total_completion_tokens = sum(log.completion_tokens for log in logs_list)
        total_tokens = sum(log.total_tokens for log in logs_list)
        total_cost = float(sum(log.cost for log in logs_list))
        
        avg_latency = 0.0
        if total_requests > 0:
            avg_latency = sum(log.latency_ms for log in logs_list) / total_requests

        serialized_logs = [
            UsageLogResponse.model_validate(log)
            for log in logs_list
        ]
        
        return UsageSummaryResponse(
            total_requests=total_requests,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 6),
            average_latency_ms=round(avg_latency, 2),
            logs=serialized_logs
        )
