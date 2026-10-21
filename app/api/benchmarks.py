import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.benchmark_job import BenchmarkJob
from app.services.benchmark_service import BenchmarkService

router = APIRouter()

# Pydantic Schemas
class BenchmarkJobCreate(BaseModel):
    name: str = Field(..., example="Customer Support Evaluation")
    prompt: str = Field(..., example="Draft a professional response to a customer requesting a refund.")
    target_models: Optional[List[Any]] = Field(
        default=None,
        example=[
            {"provider": "gemini", "model": "gemini-2.5-flash"},
            {"provider": "openai", "model": "gpt-4o-mini"},
            {"provider": "groq", "model": "llama-3.3-70b-versatile"},
            {"provider": "deepseek", "model": "deepseek-chat"}
        ]
    )
    trials_count: int = Field(default=3, ge=1, le=10)
    bypass_cache: bool = Field(default=True)
    run_guardrails: bool = Field(default=False)
    timeout_seconds: int = Field(default=15, ge=3, le=60)

# Endpoints
@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_benchmark_job(
    payload: BenchmarkJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Launch an automated, scientific Model Benchmark Job.
    Dispatches prompt trials concurrently across targeted providers (Gemini, OpenAI, Groq, DeepSeek),
    collects statistical latency percentiles (P50, P95, P99), throughput, cost, and evaluates quality via LLM-as-a-Judge.
    """
    try:
        return await BenchmarkService.create_and_execute_job(
            db=db,
            user_id=current_user.id,
            name=payload.name,
            prompt=payload.prompt,
            target_models=payload.target_models,
            trials_count=payload.trials_count,
            bypass_cache=payload.bypass_cache,
            run_guardrails=payload.run_guardrails,
            timeout_seconds=payload.timeout_seconds
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute benchmark job: {str(e)}"
        )

@router.get("/jobs")
async def list_benchmark_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical list of benchmark jobs for the authenticated user."""
    stmt = select(BenchmarkJob).where(BenchmarkJob.user_id == current_user.id).order_by(BenchmarkJob.created_at.desc())
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    return [
        {
            "id": str(j.id),
            "name": j.name,
            "prompt": j.prompt,
            "target_models": j.target_models,
            "trials_count": j.trials_count,
            "bypass_cache": j.bypass_cache,
            "run_guardrails": j.run_guardrails,
            "timeout_seconds": j.timeout_seconds,
            "status": j.status,
            "created_at": j.created_at.isoformat()
        }
        for j in jobs
    ]

@router.get("/jobs/{job_id}")
async def get_benchmark_job_details(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full statistical metrics, individual trial runs, and Phase 6 trace links for a benchmark job."""
    details = await BenchmarkService.get_job_details(db, current_user.id, job_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark job not found."
        )
    return details

@router.get("/leaderboard")
async def get_model_leaderboard(
    sort_by: str = Query("quality", regex="^(quality|fastest|p95|cheapest|reliability)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve objective multi-dimensional Model Leaderboard aggregated across all historical BenchmarkRuns.
    Filter and rank models by: 'quality' (default), 'fastest' (P50 latency), 'p95' (P95 latency), 'cheapest' (mean cost), or 'reliability'.
    """
    return await BenchmarkService.get_leaderboard(db, current_user.id, sort_by=sort_by)
