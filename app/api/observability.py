import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.request_trace import RequestTrace
from app.models.provider_metric import ProviderMetric
from app.models.usage import UsageLog

router = APIRouter()

async def _find_trace(trace_identifier: str, user_id: uuid.UUID, db: AsyncSession) -> Optional[RequestTrace]:
    """Helper to locate a RequestTrace by trace_id string, trace primary UUID, or UsageLog request_id UUID."""
    # 1. Direct match on trace_id string (e.g. trace_xxxx)
    stmt = select(RequestTrace).where(
        RequestTrace.trace_id == trace_identifier,
        RequestTrace.user_id == user_id
    )
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()
    if t:
        return t

    # 2. Match on RequestTrace.id UUID or UsageLog.request_id UUID
    try:
        val_uuid = uuid.UUID(trace_identifier)
        stmt = select(RequestTrace).where(
            RequestTrace.id == val_uuid,
            RequestTrace.user_id == user_id
        )
        res = await db.execute(stmt)
        t = res.scalar_one_or_none()
        if t:
            return t

        usage_stmt = select(UsageLog.trace_id).where(
            UsageLog.request_id == val_uuid,
            UsageLog.user_id == user_id
        )
        res = await db.execute(usage_stmt)
        matched_trace_id = res.scalar_one_or_none()
        if matched_trace_id:
            stmt = select(RequestTrace).where(
                RequestTrace.trace_id == matched_trace_id,
                RequestTrace.user_id == user_id
            )
            res = await db.execute(stmt)
            t = res.scalar_one_or_none()
            if t:
                return t
    except Exception:
        pass

    return None

@router.get("/traces")
async def get_traces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve trace logs list for the current authenticated user."""
    stmt = (
        select(RequestTrace)
        .where(RequestTrace.user_id == current_user.id)
        .order_by(RequestTrace.created_at.desc())
    )
    res = await db.execute(stmt)
    traces = res.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "trace_id": t.trace_id,
            "prompt": t.prompt,
            "response": t.response,
            "status_code": t.status_code,
            "error_type": t.error_type,
            "error_message": t.error_message,
            "total_latency_ms": t.total_latency_ms,
            "created_at": t.created_at.isoformat(),
            "attempts_count": len(t.attempts)
        }
        for t in traces
    ]

@router.get("/traces/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve structured stage timelines and failure retries details for a single trace."""
    t = await _find_trace(trace_id, current_user.id, db)
    
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Request trace not found."
        )
        
    return {
        "id": str(t.id),
        "trace_id": t.trace_id,
        "prompt": t.prompt,
        "response": t.response,
        "status_code": t.status_code,
        "error_type": t.error_type,
        "error_message": t.error_message,
        "timeline": t.timeline,
        "attempts": t.attempts,
        "total_latency_ms": t.total_latency_ms,
        "created_at": t.created_at.isoformat()
    }

@router.get("/metrics/providers")
async def get_provider_latency_comparison(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve latency and success metrics across all configured provider modules."""
    stmt = select(ProviderMetric).order_by(ProviderMetric.provider)
    res = await db.execute(stmt)
    metrics = res.scalars().all()
    
    return [
        {
            "provider": m.provider,
            "avg_latency_ms": m.avg_latency_ms,
            "success_rate": float(m.success_rate),
            "total_requests": m.total_requests,
            "total_failures": m.total_failures
        }
        for m in metrics
    ]

@router.get("/metrics/errors")
async def get_error_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Count and aggregate error categories for user trace diagnostics."""
    stmt = (
        select(RequestTrace.error_type, func.count(RequestTrace.id))
        .where(RequestTrace.user_id == current_user.id)
        .group_by(RequestTrace.error_type)
    )
    res = await db.execute(stmt)
    rows = res.all()
    
    counts = {
        "rate_limit_exceeded": 0,
        "token_quota_exceeded": 0,
        "provider_error": 0,
        "authentication_error": 0,
        "provider_unavailable": 0,
        "routing_error": 0
    }
    
    for error_type, count in rows:
        if error_type in counts:
            counts[error_type] = count
            
    return counts

@router.get("/metrics/throughput")
async def get_throughput_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve trace request volume metrics across today, this week, and this month."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    async def count_since(dt):
        stmt = select(func.count(RequestTrace.id)).where(
            RequestTrace.user_id == current_user.id,
            RequestTrace.created_at >= dt
        )
        r = await db.execute(stmt)
        return r.scalar_one() or 0
        
    requests_today = await count_since(today_start)
    requests_week = await count_since(week_start)
    requests_month = await count_since(month_start)
    
    return {
        "today": requests_today,
        "week": requests_week,
        "month": requests_month
    }

@router.post("/traces/{trace_id}/feedback")
async def submit_trace_feedback(
    trace_id: str,
    feedback_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save manual developer/user feedback rating (overall score 1.0 to 5.0) to request trace."""
    trace = await _find_trace(trace_id, current_user.id, db)
    
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Request trace not found."
        )
        
    rating = feedback_data.get("rating")
    if rating is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating is required."
        )
        
    try:
        rating_val = float(rating)
        if not (1.0 <= rating_val <= 5.0):
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be a numeric score between 1.0 and 5.0."
        )
        
    justification = feedback_data.get("justification", "Manual feedback rating.")
    
    trace.evaluation_scores = {
        "helpfulness": rating_val,
        "accuracy": rating_val,
        "safety": 5.0,
        "tone": rating_val,
        "completeness": rating_val,
        "overall": rating_val,
        "justification": justification,
        "is_manual": True
    }
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(trace, "evaluation_scores")
    await db.commit()
    return {"message": "Feedback submitted successfully.", "scores": trace.evaluation_scores}
