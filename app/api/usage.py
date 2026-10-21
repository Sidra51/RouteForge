from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.usage import UsageSummaryResponse, QuotaUsageResponse
from app.services.usage_service import UsageService
from app.services.rate_limiter import RateLimiterService
from app.core.config import PLANS

router = APIRouter()

@router.get("", response_model=UsageSummaryResponse)
async def get_usage_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve execution history logs and cumulative cost metrics for the authenticated user."""
    return await UsageService.get_user_usage(db, current_user.id)

@router.get("/quota", response_model=QuotaUsageResponse)
async def get_quota_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve details about the current plan and today's / this month's utilization counters."""
    plan_limits = PLANS.get(current_user.plan_type, PLANS["free"])
    stats = await RateLimiterService.get_usage_stats(current_user.id, db)
    
    return QuotaUsageResponse(
        plan=current_user.plan_type,
        requests_today=stats["requests_today"],
        request_limit=plan_limits["requests_per_day"],
        tokens_this_month=stats["tokens_this_month"],
        token_limit=plan_limits["tokens_per_month"]
    )
