import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_job import BenchmarkJob
from app.models.benchmark_run import BenchmarkRun
from app.services.benchmark_executor import BenchmarkExecutor
from app.services.benchmark_metrics import BenchmarkMetrics
from app.services.prompt_evaluator import PromptEvaluator
from app.core.config import PROVIDER_METADATA

logger = logging.getLogger(__name__)

# Default model benchmark matrix if none provided
DEFAULT_MODEL_TARGETS = [
    {"provider": "gemini", "model": "gemini-2.5-flash"},
    {"provider": "openai", "model": "gpt-4o-mini"},
    {"provider": "groq", "model": "llama-3.3-70b-versatile"},
    {"provider": "deepseek", "model": "deepseek-chat"}
]

class BenchmarkService:
    @classmethod
    def _normalize_targets(cls, target_models: Optional[List[Any]]) -> List[Dict[str, str]]:
        """Normalize target models list into standard dict format: [{'provider': '...', 'model': '...'}]"""
        if not target_models:
            return DEFAULT_MODEL_TARGETS

        normalized = []
        for item in target_models:
            if isinstance(item, dict) and "provider" in item and "model" in item:
                normalized.append({"provider": item["provider"].lower(), "model": item["model"]})
            elif isinstance(item, str):
                # E.g. "gemini-2.5-flash" or "openai/gpt-4o-mini" or "gemini::gemini-2.5-flash"
                if "::" in item:
                    p, m = item.split("::", 1)
                    normalized.append({"provider": p.lower(), "model": m})
                elif "/" in item:
                    p, m = item.split("/", 1)
                    normalized.append({"provider": p.lower(), "model": m})
                else:
                    # Guess provider from model name
                    model_lc = item.lower()
                    if "gemini" in model_lc:
                        normalized.append({"provider": "gemini", "model": item})
                    elif "gpt" in model_lc or "o1" in model_lc or "o3" in model_lc:
                        normalized.append({"provider": "openai", "model": item})
                    elif "llama" in model_lc or "mixtral" in model_lc:
                        normalized.append({"provider": "groq", "model": item})
                    elif "deepseek" in model_lc:
                        normalized.append({"provider": "deepseek", "model": item})
                    else:
                        normalized.append({"provider": "gemini", "model": item})
        return normalized or DEFAULT_MODEL_TARGETS

    @classmethod
    async def create_and_execute_job(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        prompt: str,
        target_models: Optional[List[Any]] = None,
        trials_count: int = 3,
        bypass_cache: bool = True,
        run_guardrails: bool = False,
        timeout_seconds: int = 15
    ) -> Dict[str, Any]:
        """
        Creates a BenchmarkJob, dispatches N trials x M models concurrently with isolated timeouts,
        scores quality via PromptEvaluator, saves BenchmarkRuns to DB, and computes statistical aggregations.
        """
        targets = cls._normalize_targets(target_models)
        trials_n = max(1, min(10, trials_count))
        timeout_s = max(3, min(60, timeout_seconds))

        job = BenchmarkJob(
            user_id=user_id,
            name=name,
            prompt=prompt,
            target_models=targets,
            trials_count=trials_n,
            bypass_cache=bypass_cache,
            run_guardrails=run_guardrails,
            timeout_seconds=timeout_s,
            status="running"
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        raw_run_results: List[Dict[str, Any]] = []

        # Execute trials loops
        for trial_idx in range(1, trials_n + 1):
            tasks = []
            for target in targets:
                tasks.append(
                    BenchmarkExecutor.execute_provider_trial(
                        provider_name=target["provider"],
                        model_name=target["model"],
                        prompt=prompt,
                        trial_number=trial_idx,
                        timeout_seconds=timeout_s,
                        bypass_cache=bypass_cache,
                        run_guardrails=run_guardrails,
                        user_id=user_id
                    )
                )
            
            # Execute target providers concurrently for this trial loop
            trial_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in trial_results:
                if isinstance(res, dict):
                    raw_run_results.append(res)
                elif isinstance(res, Exception):
                    logger.error(f"Trial execution error: {res}")

        # Quality evaluation step for successful trial outputs
        db_run_objects: List[BenchmarkRun] = []
        for r_dict in raw_run_results:
            quality_score = None
            dimension_scores = None

            if r_dict.get("is_success") and r_dict.get("response_text"):
                eval_res = await PromptEvaluator.evaluate_prompt_response(prompt, r_dict["response_text"])
                if eval_res:
                    quality_score = float(eval_res.get("overall", 0.0))
                    dimension_scores = eval_res
                    r_dict["quality_score"] = quality_score
                    r_dict["dimension_scores"] = dimension_scores

            run_obj = BenchmarkRun(
                job_id=job.id,
                provider=r_dict["provider"],
                model=r_dict["model"],
                trial_number=r_dict["trial_number"],
                trace_id=r_dict.get("trace_id"),
                started_at=r_dict["started_at"],
                completed_at=r_dict["completed_at"],
                latency_ms=r_dict["latency_ms"],
                generation_tokens_per_sec=r_dict["generation_tokens_per_sec"],
                end_to_end_tokens_per_sec=r_dict["end_to_end_tokens_per_sec"],
                prompt_tokens=r_dict["prompt_tokens"],
                completion_tokens=r_dict["completion_tokens"],
                total_tokens=r_dict["total_tokens"],
                cost=r_dict["cost"],
                cache_hit=r_dict["cache_hit"],
                guardrail_status=r_dict["guardrail_status"],
                is_success=r_dict["is_success"],
                error_type=r_dict.get("error_type"),
                error_message=r_dict.get("error_message"),
                response_text=r_dict.get("response_text"),
                quality_score=quality_score,
                dimension_scores=dimension_scores
            )
            db.add(run_obj)
            db_run_objects.append(run_obj)

        # Determine overall job status
        successful_count = sum(1 for r in raw_run_results if r.get("is_success"))
        total_runs_count = len(raw_run_results)

        if successful_count == total_runs_count and total_runs_count > 0:
            job.status = "completed"
        elif successful_count > 0:
            job.status = "partial_failure"
        else:
            job.status = "failed"

        await db.commit()
        await db.refresh(job)

        # Compute statistical aggregations
        aggregated_metrics = BenchmarkMetrics.aggregate_model_metrics(raw_run_results)

        return {
            "job": {
                "id": str(job.id),
                "name": job.name,
                "prompt": job.prompt,
                "target_models": job.target_models,
                "trials_count": job.trials_count,
                "bypass_cache": job.bypass_cache,
                "run_guardrails": job.run_guardrails,
                "timeout_seconds": job.timeout_seconds,
                "status": job.status,
                "created_at": job.created_at.isoformat()
            },
            "metrics_summary": aggregated_metrics,
            "runs": [
                {
                    "id": str(r.id),
                    "provider": r.provider,
                    "model": r.model,
                    "trial_number": r.trial_number,
                    "trace_id": r.trace_id,
                    "latency_ms": r.latency_ms,
                    "generation_tokens_per_sec": r.generation_tokens_per_sec,
                    "end_to_end_tokens_per_sec": r.end_to_end_tokens_per_sec,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                    "cost": float(r.cost),
                    "cache_hit": r.cache_hit,
                    "guardrail_status": r.guardrail_status,
                    "is_success": r.is_success,
                    "error_type": r.error_type,
                    "error_message": r.error_message,
                    "response_text": r.response_text,
                    "quality_score": r.quality_score,
                    "dimension_scores": r.dimension_scores
                }
                for r in db_run_objects
            ]
        }

    @classmethod
    async def get_job_details(cls, db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve details and statistical metrics for a single BenchmarkJob."""
        stmt = select(BenchmarkJob).where(BenchmarkJob.id == job_id, BenchmarkJob.user_id == user_id)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            return None

        runs_stmt = select(BenchmarkRun).where(BenchmarkRun.job_id == job.id).order_by(BenchmarkRun.trial_number, BenchmarkRun.provider)
        runs_res = await db.execute(runs_stmt)
        runs = runs_res.scalars().all()

        runs_dict_list = [
            {
                "id": str(r.id),
                "provider": r.provider,
                "model": r.model,
                "trial_number": r.trial_number,
                "trace_id": r.trace_id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "latency_ms": r.latency_ms,
                "generation_tokens_per_sec": r.generation_tokens_per_sec,
                "end_to_end_tokens_per_sec": r.end_to_end_tokens_per_sec,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost": float(r.cost),
                "cache_hit": r.cache_hit,
                "guardrail_status": r.guardrail_status,
                "is_success": r.is_success,
                "error_type": r.error_type,
                "error_message": r.error_message,
                "response_text": r.response_text,
                "quality_score": r.quality_score,
                "dimension_scores": r.dimension_scores
            }
            for r in runs
        ]

        metrics_summary = BenchmarkMetrics.aggregate_model_metrics(runs_dict_list)

        return {
            "job": {
                "id": str(job.id),
                "name": job.name,
                "prompt": job.prompt,
                "target_models": job.target_models,
                "trials_count": job.trials_count,
                "bypass_cache": job.bypass_cache,
                "run_guardrails": job.run_guardrails,
                "timeout_seconds": job.timeout_seconds,
                "status": job.status,
                "created_at": job.created_at.isoformat()
            },
            "metrics_summary": metrics_summary,
            "runs": runs_dict_list
        }

    @classmethod
    async def get_leaderboard(cls, db: AsyncSession, user_id: uuid.UUID, sort_by: str = "quality") -> List[Dict[str, Any]]:
        """
        Retrieve multi-dimensional Model Leaderboard aggregated across all historical BenchmarkRuns.
        Supports sorting by 'quality', 'fastest', 'p95', 'cheapest', or 'reliability'.
        """
        stmt = (
            select(BenchmarkRun)
            .join(BenchmarkJob)
            .where(BenchmarkJob.user_id == user_id)
        )
        res = await db.execute(stmt)
        runs = res.scalars().all()

        runs_dict_list = [
            {
                "provider": r.provider,
                "model": r.model,
                "latency_ms": r.latency_ms,
                "generation_tokens_per_sec": r.generation_tokens_per_sec,
                "end_to_end_tokens_per_sec": r.end_to_end_tokens_per_sec,
                "cost": float(r.cost),
                "is_success": r.is_success,
                "quality_score": r.quality_score
            }
            for r in runs
        ]

        aggregated = BenchmarkMetrics.aggregate_model_metrics(runs_dict_list)
        leaderboard_list = list(aggregated.values())

        # Sorting logic
        sort_key = sort_by.lower()
        if sort_key == "fastest" or sort_key == "latency_p50" or sort_key == "p50":
            leaderboard_list.sort(key=lambda x: (x["p50_latency_ms"] if x["p50_latency_ms"] > 0 else 999999))
        elif sort_key == "p95" or sort_key == "latency_p95":
            leaderboard_list.sort(key=lambda x: (x["p95_latency_ms"] if x["p95_latency_ms"] > 0 else 999999))
        elif sort_key == "cheapest" or sort_key == "cost":
            leaderboard_list.sort(key=lambda x: x["mean_cost"])
        elif sort_key == "reliability" or sort_key == "success_rate":
            leaderboard_list.sort(key=lambda x: x["success_rate"], reverse=True)
        else: # Default: quality score descending
            leaderboard_list.sort(key=lambda x: x["mean_quality_score"], reverse=True)

        return leaderboard_list
