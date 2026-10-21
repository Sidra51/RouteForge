import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.providers.manager import ProviderManager
from app.providers.pricing import MODEL_PRICING
from app.core.config import PROVIDER_METADATA, settings
from app.services.cost_service import CostService
from app.services.trace_service import TraceService
from app.services.guardrails.guardrail_service import GuardrailService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class BenchmarkExecutor:
    @classmethod
    async def execute_provider_trial(
        cls,
        provider_name: str,
        model_name: str,
        prompt: str,
        trial_number: int,
        timeout_seconds: int,
        bypass_cache: bool,
        run_guardrails: bool,
        user_id: uuid.UUID,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Executes a single benchmark trial for a provider/model with isolated timeout handling,
        dedicated task DB session context for greenlet safety in asyncio.gather, Phase 6 trace linkage,
        metrics calculation, and exception boundary protection.
        """
        trace_id = f"trace_bm_{uuid.uuid4().hex[:10]}"
        started_at = datetime.now(timezone.utc)
        start_time = time.perf_counter()

        # Open dedicated async database session for this concurrent task
        async with async_session() as task_db:
            # 1. Initialize Phase 6 Trace record
            await TraceService.start_trace(
                trace_id=trace_id,
                user_id=user_id,
                prompt=prompt,
                db=task_db
            )

            effective_prompt = prompt
            guardrail_status = "passed"

            # 2. Optional Guardrails check
            if run_guardrails:
                try:
                    masked_prompt, violations = await GuardrailService.evaluate_request(
                        db=task_db,
                        user_id=user_id,
                        api_key_id=None,
                        request_id=uuid.uuid4(),
                        trace_id=trace_id,
                        prompt=prompt,
                        policies={"pii": "mask", "prompt_injection": "block"}
                    )
                    effective_prompt = masked_prompt
                    if any(v["action_taken"] == "block" for v in violations):
                        guardrail_status = "blocked"
                        completed_at = datetime.now(timezone.utc)
                        latency_ms = int((time.perf_counter() - start_time) * 1000)
                        
                        err_msg = "Blocked by guardrail policy"
                        await TraceService.update_trace(
                            trace_id=trace_id,
                            response="[Blocked by Guardrail]",
                            status_code=400,
                            error_type="guardrail_blocked",
                            error_message=err_msg,
                            db=task_db,
                            is_success=False
                        )
                        return {
                            "provider": provider_name,
                            "model": model_name,
                            "trial_number": trial_number,
                            "trace_id": trace_id,
                            "started_at": started_at,
                            "completed_at": completed_at,
                            "latency_ms": latency_ms,
                            "generation_tokens_per_sec": 0.0,
                            "end_to_end_tokens_per_sec": 0.0,
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                            "cost": 0.0,
                            "cache_hit": False,
                            "guardrail_status": guardrail_status,
                            "is_success": False,
                            "error_type": "guardrail_blocked",
                            "error_message": err_msg,
                            "response_text": None,
                        }
                except Exception as e:
                    logger.warning(f"Guardrail evaluation error in benchmark: {e}")

            # 3. Optional Cache check
            cache_hit = False
            if not bypass_cache and settings.CACHE_ENABLED:
                cached_data = await CacheService.check_exact_match(effective_prompt, task_db)
                if cached_data:
                    cache_hit = True
                    completed_at = datetime.now(timezone.utc)
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    
                    await TraceService.update_trace(
                        trace_id=trace_id,
                        response=cached_data["response_text"],
                        status_code=200,
                        error_type="none",
                        db=task_db
                    )
                    return {
                        "provider": cached_data["provider"],
                        "model": cached_data["model"],
                        "trial_number": trial_number,
                        "trace_id": trace_id,
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "latency_ms": latency_ms,
                        "generation_tokens_per_sec": 0.0,
                        "end_to_end_tokens_per_sec": 0.0,
                        "prompt_tokens": cached_data["prompt_tokens"],
                        "completion_tokens": cached_data["completion_tokens"],
                        "total_tokens": cached_data["total_tokens"],
                        "cost": 0.0,
                        "cache_hit": True,
                        "guardrail_status": guardrail_status,
                        "is_success": True,
                        "error_type": None,
                        "error_message": None,
                        "response_text": cached_data["response_text"],
                    }

            # 4. Resolve API key configuration
            keys_config = {
                "openai": settings.OPENAI_API_KEY,
                "gemini": settings.GEMINI_API_KEY,
                "deepseek": settings.DEEPSEEK_API_KEY,
                "groq": settings.GROQ_API_KEY
            }
            api_key = keys_config.get(provider_name.lower(), "mock")

            # 5. Execute Provider call inside timeout boundary
            try:
                provider_instance = ProviderManager.get_provider(provider_name)
                
                gen_start_time = time.perf_counter()
                result = await asyncio.wait_for(
                    provider_instance.generate_chat(
                        model=model_name,
                        message=effective_prompt,
                        temperature=0.7,
                        max_tokens=1000,
                        api_key=api_key
                    ),
                    timeout=float(timeout_seconds)
                )
                gen_duration = time.perf_counter() - gen_start_time
                total_duration = time.perf_counter() - start_time
                latency_ms = int(total_duration * 1000)
                completed_at = datetime.now(timezone.utc)

                if result.get("error"):
                    error_msg = result["error"]
                    await TraceService.update_trace(
                        trace_id=trace_id,
                        response=f"[Provider Error: {error_msg}]",
                        status_code=502,
                        error_type="provider_error",
                        error_message=error_msg,
                        db=task_db,
                        is_success=False
                    )
                    return {
                        "provider": provider_name,
                        "model": model_name,
                        "trial_number": trial_number,
                        "trace_id": trace_id,
                        "started_at": started_at,
                        "completed_at": completed_at,
                        "latency_ms": latency_ms,
                        "generation_tokens_per_sec": 0.0,
                        "end_to_end_tokens_per_sec": 0.0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "cost": 0.0,
                        "cache_hit": False,
                        "guardrail_status": guardrail_status,
                        "is_success": False,
                        "error_type": "provider_error",
                        "error_message": error_msg,
                        "response_text": None,
                    }

                # Successful Execution Metrics Calculation
                prompt_tokens = result.get("prompt_tokens", 0)
                completion_tokens = result.get("completion_tokens", 0)
                total_tokens = result.get("total_tokens", prompt_tokens + completion_tokens)
                response_text = result.get("response_text", "")

                cost = CostService.calculate_token_cost(model_name, prompt_tokens, completion_tokens)
                
                gen_tps = round(completion_tokens / max(0.001, gen_duration), 2)
                e2e_tps = round(completion_tokens / max(0.001, total_duration), 2)

                await TraceService.update_trace(
                    trace_id=trace_id,
                    response=response_text,
                    status_code=200,
                    error_type="none",
                    db=task_db,
                    is_success=True
                )

                return {
                    "provider": provider_name,
                    "model": model_name,
                    "trial_number": trial_number,
                    "trace_id": trace_id,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "latency_ms": latency_ms,
                    "generation_tokens_per_sec": gen_tps,
                    "end_to_end_tokens_per_sec": e2e_tps,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": round(cost, 6),
                    "cache_hit": False,
                    "guardrail_status": guardrail_status,
                    "is_success": True,
                    "error_type": None,
                    "error_message": None,
                    "response_text": response_text,
                }

            except asyncio.TimeoutError:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                completed_at = datetime.now(timezone.utc)
                err_msg = f"Provider request timed out after {timeout_seconds} seconds"
                
                await TraceService.update_trace(
                    trace_id=trace_id,
                    response="[Timeout]",
                    status_code=504,
                    error_type="timeout",
                    error_message=err_msg,
                    db=task_db,
                    is_success=False
                )
                return {
                    "provider": provider_name,
                    "model": model_name,
                    "trial_number": trial_number,
                    "trace_id": trace_id,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "latency_ms": latency_ms,
                    "generation_tokens_per_sec": 0.0,
                    "end_to_end_tokens_per_sec": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "cache_hit": False,
                    "guardrail_status": guardrail_status,
                    "is_success": False,
                    "error_type": "timeout",
                    "error_message": err_msg,
                    "response_text": None,
                }
            except Exception as e:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                completed_at = datetime.now(timezone.utc)
                err_msg = str(e)
                
                await TraceService.update_trace(
                    trace_id=trace_id,
                    response=f"[Exception: {err_msg}]",
                    status_code=500,
                    error_type="internal_error",
                    error_message=err_msg,
                    db=task_db,
                    is_success=False
                )
                return {
                    "provider": provider_name,
                    "model": model_name,
                    "trial_number": trial_number,
                    "trace_id": trace_id,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "latency_ms": latency_ms,
                    "generation_tokens_per_sec": 0.0,
                    "end_to_end_tokens_per_sec": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0,
                    "cache_hit": False,
                    "guardrail_status": guardrail_status,
                    "is_success": False,
                    "error_type": "internal_error",
                    "error_message": err_msg,
                    "response_text": None,
                }
