import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.api_key import APIKey
from app.models.guardrail_event import GuardrailEvent
from app.services.guardrails.guardrail_service import GuardrailService

logger = logging.getLogger(__name__)
router = APIRouter()

# Schema definitions
class GuardrailTestRequest(BaseModel):
    prompt: str
    policies: Optional[Dict[str, Any]] = None

class GuardrailViolationDetail(BaseModel):
    event_type: str
    matched_detail: str
    matched_text: str
    confidence: float
    severity: str
    action_taken: str
    detector: str

class GuardrailTestResponse(BaseModel):
    allowed: bool
    violations: List[GuardrailViolationDetail]
    masked_prompt: str

class GuardrailStatsResponse(BaseModel):
    total_blocked: int
    total_warned: int
    total_masked: int
    top_violations: List[Dict[str, Any]]
    most_triggered_key: Optional[str] = None
    most_triggered_user: Optional[str] = None
    trend_7days: List[Dict[str, Any]]

# Endpoints
@router.post("/test", response_model=GuardrailTestResponse)
async def test_guardrails(
    payload: GuardrailTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Developer Sandbox Endpoint. 
    Allows developers to dry-run prompts against custom policies without writing audits to database.
    """
    masked_prompt, violations = await GuardrailService.evaluate_request(
        db=None,
        user_id=current_user.id,
        api_key_id=None,
        request_id=None,
        trace_id=None,
        prompt=payload.prompt,
        policy=payload.policies,
        dry_run=True
    )
    
    is_allowed = not any(v["action_taken"] == "block" for v in violations)
    return {
        "allowed": is_allowed,
        "violations": violations,
        "masked_prompt": masked_prompt
    }

@router.get("/stats", response_model=GuardrailStatsResponse)
async def get_guardrail_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Exposes aggregated metrics, trendlines, and violation charts for content safety UI cards."""
    # 1. Action totals
    stmt_blocked = select(func.count(GuardrailEvent.id)).where(
        GuardrailEvent.user_id == current_user.id,
        GuardrailEvent.action_taken == "block"
    )
    stmt_warned = select(func.count(GuardrailEvent.id)).where(
        GuardrailEvent.user_id == current_user.id,
        GuardrailEvent.action_taken == "warn"
    )
    stmt_masked = select(func.count(GuardrailEvent.id)).where(
        GuardrailEvent.user_id == current_user.id,
        GuardrailEvent.action_taken == "mask"
    )
    
    total_blocked = (await db.execute(stmt_blocked)).scalar() or 0
    total_warned = (await db.execute(stmt_warned)).scalar() or 0
    total_masked = (await db.execute(stmt_masked)).scalar() or 0
    
    # 2. Top Violations type distribution
    stmt_types = (
        select(GuardrailEvent.event_type, func.count(GuardrailEvent.id))
        .where(GuardrailEvent.user_id == current_user.id)
        .group_by(GuardrailEvent.event_type)
    )
    res_types = await db.execute(stmt_types)
    top_violations = [{"event_type": row[0], "count": row[1]} for row in res_types.all()]
    
    # 3. Most triggered API Key
    stmt_key = (
        select(APIKey.name, func.count(GuardrailEvent.id))
        .join(APIKey, APIKey.id == GuardrailEvent.api_key_id)
        .where(GuardrailEvent.user_id == current_user.id)
        .group_by(APIKey.name)
        .order_by(func.count(GuardrailEvent.id).desc())
        .limit(1)
    )
    res_key = await db.execute(stmt_key)
    row_key = res_key.first()
    most_triggered_key = f"{row_key[0]} ({row_key[1]} hits)" if row_key else "None"
    
    # Most triggered User (always the logged-in user in this user-scoped Gateway, but format for dashboard UI display)
    most_triggered_user = f"{current_user.email} (Total hits)" if (total_blocked + total_warned + total_masked) > 0 else "None"

    # 4. 7-Day Trend Graph Calculation (done in Python to remain DB engine agnostic)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=6)
    stmt_trend = (
        select(GuardrailEvent.created_at)
        .where(
            GuardrailEvent.user_id == current_user.id,
            GuardrailEvent.created_at >= seven_days_ago
        )
    )
    res_trend = await db.execute(stmt_trend)
    events_dates = res_trend.scalars().all()
    
    # Initialize dictionary for 7 days
    daily_counts = {}
    for i in range(7):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts[day] = 0
        
    for dt in events_dates:
        day_str = dt.strftime("%Y-%m-%d")
        if day_str in daily_counts:
            daily_counts[day_str] += 1
            
    trend_7days = [{"date": k, "count": v} for k, v in sorted(daily_counts.items())]

    return {
        "total_blocked": total_blocked,
        "total_warned": total_warned,
        "total_masked": total_masked,
        "top_violations": top_violations,
        "most_triggered_key": most_triggered_key,
        "most_triggered_user": most_triggered_user,
        "trend_7days": trend_7days
    }

@router.get("/events")
async def get_guardrail_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch paginated safety log entries joined with name references for auditing."""
    stmt = (
        select(GuardrailEvent, APIKey.name.label("api_key_name"))
        .outerjoin(APIKey, APIKey.id == GuardrailEvent.api_key_id)
        .where(GuardrailEvent.user_id == current_user.id)
        .order_by(GuardrailEvent.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.all()
    
    out = []
    for row in rows:
        evt = row[0]
        key_name = row[1] or "Playground/Session"
        out.append({
            "id": str(evt.id),
            "request_id": str(evt.request_id),
            "trace_id": evt.trace_id,
            "detector": evt.detector,
            "event_type": evt.event_type,
            "action_taken": evt.action_taken,
            "severity": evt.severity,
            "confidence": evt.confidence,
            "matched_detail": evt.matched_detail,
            "prompt_preview": evt.prompt_preview,
            "api_key_name": key_name,
            "created_at": evt.created_at
        })
    return out
