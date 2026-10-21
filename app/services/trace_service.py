import logging
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.request_trace import RequestTrace
from app.core.config import settings

logger = logging.getLogger(__name__)

class TraceService:
    @staticmethod
    def _truncate_payload(text: str) -> str:
        """Truncate payload to 500 characters if STORE_FULL_PAYLOAD is False."""
        if not text:
            return text
        if not settings.STORE_FULL_PAYLOAD and len(text) > 500:
            return text[:500] + "... [truncated]"
        return text

    @classmethod
    async def start_trace(
        cls, 
        trace_id: str, 
        user_id: uuid.UUID, 
        prompt: str, 
        db: AsyncSession,
        prompt_version_id: Optional[uuid.UUID] = None,
        experiment_id: Optional[uuid.UUID] = None
    ) -> RequestTrace:
        """Create and initialize a new request trace in the database."""
        try:
            now = datetime.now(timezone.utc)
            prompt_preview = cls._truncate_payload(prompt)
            
            initial_timeline = [
                {
                    "stage": "received",
                    "timestamp": now.isoformat(),
                    "duration_ms": 0
                }
            ]
            
            trace = RequestTrace(
                trace_id=trace_id,
                user_id=user_id,
                prompt=prompt_preview,
                response=None,
                status_code=0,
                error_type="none",
                error_message=None,
                timeline=initial_timeline,
                attempts=[],
                total_latency_ms=0,
                prompt_version_id=prompt_version_id,
                experiment_id=experiment_id,
                is_success=True,
                is_guardrail_blocked=False,
                created_at=now
            )
            
            db.add(trace)
            await db.commit()
            return trace
        except Exception as e:
            logger.error(f"Failed to start request trace {trace_id}: {e}")
            await db.rollback()
            return None


    @classmethod
    async def append_timeline_stage(
        cls, 
        trace_id: str, 
        stage_name: str, 
        db: AsyncSession
    ):
        """Append a stage log to the trace timeline with computed latency offset."""
        try:
            stmt = select(RequestTrace).where(RequestTrace.trace_id == trace_id)
            res = await db.execute(stmt)
            trace = res.scalar_one_or_none()
            
            if trace:
                now = datetime.now(timezone.utc)
                elapsed_ms = int((now - trace.created_at).total_seconds() * 1000)
                
                trace.timeline.append({
                    "stage": stage_name,
                    "timestamp": now.isoformat(),
                    "duration_ms": elapsed_ms
                })
                
                flag_modified(trace, "timeline")
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to append stage '{stage_name}' to trace {trace_id}: {e}")
            await db.rollback()

    @classmethod
    async def record_attempt(
        cls,
        trace_id: str,
        attempt_idx: int,
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
        cost: float,
        error_msg: str,
        db: AsyncSession
    ):
        """Record attempt statistics (failovers) inside the trace attempts list."""
        try:
            stmt = select(RequestTrace).where(RequestTrace.trace_id == trace_id)
            res = await db.execute(stmt)
            trace = res.scalar_one_or_none()
            
            if trace:
                trace.attempts.append({
                    "attempt": attempt_idx,
                    "provider": provider,
                    "model": model,
                    "status": status,
                    "latency_ms": latency_ms,
                    "cost": float(cost),
                    "error": error_msg or ""
                })
                
                flag_modified(trace, "attempts")
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to record attempt for trace {trace_id}: {e}")
            await db.rollback()

    @classmethod
    async def update_trace(
        cls,
        trace_id: str,
        response: str,
        status_code: int,
        error_type: str = "none",
        error_message: Optional[str] = None,
        db: AsyncSession = None,
        is_success: Optional[bool] = None,
        is_guardrail_blocked: Optional[bool] = None
    ):
        """Finalize the request trace logging prompt output and execution latency."""
        try:
            stmt = select(RequestTrace).where(RequestTrace.trace_id == trace_id)
            res = await db.execute(stmt)
            trace = res.scalar_one_or_none()
            
            if trace:
                now = datetime.now(timezone.utc)
                elapsed_ms = int((now - trace.created_at).total_seconds() * 1000)
                
                trace.response = cls._truncate_payload(response)
                trace.status_code = status_code
                trace.error_type = error_type or "none"
                trace.error_message = error_message
                trace.total_latency_ms = elapsed_ms
                
                if is_success is not None:
                    trace.is_success = is_success
                if is_guardrail_blocked is not None:
                    trace.is_guardrail_blocked = is_guardrail_blocked
                
                # Append final returned stage if not already logged
                stages = [s["stage"] for s in trace.timeline]
                if "response_returned" not in stages:
                    trace.timeline.append({
                        "stage": "response_returned",
                        "timestamp": now.isoformat(),
                        "duration_ms": elapsed_ms
                    })
                    flag_modified(trace, "timeline")
                    
                await db.commit()

        except Exception as e:
            logger.error(f"Failed to finalize trace {trace_id}: {e}")
            await db.rollback()
