import time
import uuid
import logging
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.gateway import ChatRequest, ChatResponse, CacheMetadata
from app.providers.manager import ProviderManager
from app.providers.pricing import MODEL_PRICING
from app.services.usage_service import UsageService
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.prompt_service import PromptService
from app.services.prompt_evaluator import PromptEvaluator
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    @staticmethod
    def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate request cost in USD based on decoupled model pricing coefficients."""
        # Fallback to gemini-2.5-flash pricing if model is not specifically registered
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gemini-2.5-flash"])
        input_cost = prompt_tokens * pricing["input"]
        output_cost = completion_tokens * pricing["output"]
        return input_cost + output_cost

    @staticmethod
    async def route_request(
        db: AsyncSession,
        user_id: uuid.UUID,
        api_key_id: Optional[uuid.UUID],
        request_data: ChatRequest,
        trace_id: str,
        ip_address: Optional[str] = None,
        background_tasks: Optional[Any] = None
    ) -> ChatResponse:
        """Route prompt to the correct provider, track metrics, log transaction, and return answer."""
        from app.services.trace_service import TraceService
        from app.services.langfuse_service import LangfuseService
        
        prompt_version = None
        prompt_experiment = None

        # Phase 9: Load & route template prompts
        if request_data.prompt_template_name:
            try:
                prompt_version, prompt_experiment, rendered_user, rendered_system = await PromptService.route_template_request(
                    db=db,
                    template_name=request_data.prompt_template_name,
                    version_str=request_data.prompt_template_version,
                    variables=request_data.variables
                )
                if rendered_system:
                    request_data.message = f"System: {rendered_system}\n\nUser: {rendered_user}"
                else:
                    request_data.message = rendered_user
            except ValueError as val_err:
                err_msg = str(val_err)
                await TraceService.start_trace(
                    trace_id=trace_id, 
                    user_id=user_id, 
                    prompt=request_data.message or f"[Invalid Template request: {request_data.prompt_template_name}]", 
                    db=db,
                    prompt_version_id=None,
                    experiment_id=None
                )
                await TraceService.update_trace(
                    trace_id=trace_id,
                    response="[Prompt template validation/routing error]",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_type="routing_error",
                    error_message=err_msg,
                    db=db,
                    is_success=False
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": {
                            "code": "template_error",
                            "message": err_msg
                        }
                    }
                )
        elif not request_data.message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'message' or 'prompt_template_name' must be provided."
            )

        # 1. Fetch API Key settings
        guardrail_policy = None
        if api_key_id:
            from sqlalchemy import select
            from app.models.api_key import APIKey
            stmt = select(APIKey.guardrail_settings).where(APIKey.id == api_key_id)
            res = await db.execute(stmt)
            guardrail_policy = res.scalar_one_or_none()
            
        # 2. Run Guardrail checks
        from app.services.guardrails.guardrail_service import GuardrailService
        request_id = uuid.uuid4()
        
        modified_message, violations = await GuardrailService.evaluate_request(
            db=db,
            user_id=user_id,
            api_key_id=api_key_id,
            request_id=request_id,
            trace_id=trace_id,
            prompt=request_data.message,
            policy=guardrail_policy
        )
        
        # Apply PII redactions
        if modified_message != request_data.message:
            request_data.message = modified_message
            
        block_violations = [v for v in violations if v["action_taken"] == "block"]
        if block_violations:
            first_v = block_violations[0]
            err_msg = f"Request blocked due to content safety policy ({first_v['event_type']}): {first_v['matched_detail']}"
            
            # Start trace and mark as rejected
            await TraceService.start_trace(
                trace_id=trace_id, 
                user_id=user_id, 
                prompt=request_data.message, 
                db=db,
                prompt_version_id=prompt_version.id if prompt_version else None,
                experiment_id=prompt_experiment.id if prompt_experiment else None
            )
            await TraceService.update_trace(
                trace_id=trace_id,
                response=f"[Blocked: {first_v['event_type']}]",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type="guardrail_blocked",
                error_message=err_msg,
                db=db,
                is_success=False,
                is_guardrail_blocked=True
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "guardrail_blocked",
                        "message": err_msg,
                        "category": first_v["event_type"]
                    }
                }
            )

        # 3. Initialize Tracing records
        await TraceService.start_trace(
            trace_id=trace_id, 
            user_id=user_id, 
            prompt=request_data.message, 
            db=db,
            prompt_version_id=prompt_version.id if prompt_version else None,
            experiment_id=prompt_experiment.id if prompt_experiment else None
        )
        langfuse_trace = LangfuseService.create_trace(trace_id, user_id, "gateway-chat", request_data.message)

        
        # 2. Cache interception block
        embedding = None
        emb_model = "text-embedding-3-small" if settings.EMBEDDING_PROVIDER.lower() == "openai" else "gemini-embedding-2"
        
        if settings.CACHE_ENABLED and not request_data.bypass_cache:
            start_cache_time = time.perf_counter()
            await TraceService.append_timeline_stage(trace_id, "cache_lookup", db)
            
            # A. Exact Cache Check
            cached_data = await CacheService.check_exact_match(request_data.message, db)
            if cached_data:
                cache_latency = int((time.perf_counter() - start_cache_time) * 1000)
                await TraceService.append_timeline_stage(trace_id, "cache_hit:exact", db)
                
                # Log usage (cost is 0.0, save estimated cost to cost_saved)
                request_id = uuid.uuid4()
                await UsageService.log_usage(
                    db=db,
                    user_id=user_id,
                    api_key_id=api_key_id,
                    request_id=request_id,
                    provider=cached_data["provider"],
                    model=cached_data["model"],
                    prompt_tokens=cached_data["prompt_tokens"],
                    completion_tokens=cached_data["completion_tokens"],
                    total_tokens=cached_data["total_tokens"],
                    cost=0.0,
                    latency_ms=cache_latency,
                    status_code=200,
                    error_message=None,
                    trace_id=trace_id,
                    ip_address=ip_address,
                    cache_type="exact",
                    cost_saved=cached_data["estimated_cost"]
                )
                
                # Finalize Trace in DB
                await TraceService.update_trace(
                    trace_id=trace_id,
                    response=cached_data["response_text"],
                    status_code=200,
                    error_type="none",
                    error_message=None,
                    db=db
                )
                
                return ChatResponse(
                    request_id=request_id,
                    provider=cached_data["provider"],
                    model=cached_data["model"],
                    response_text=cached_data["response_text"],
                    prompt_tokens=cached_data["prompt_tokens"],
                    completion_tokens=cached_data["completion_tokens"],
                    total_tokens=cached_data["total_tokens"],
                    cost=0.0,
                    latency_ms=cache_latency,
                    cache=CacheMetadata(hit=True, type="exact")
                )
            
            # B. Fetch embedding & Semantic Cache Check
            embedding = await EmbeddingService.get_embedding(request_data.message, settings.EMBEDDING_PROVIDER)
            if embedding:
                semantic_res = await CacheService.check_semantic_match(request_data.message, embedding, emb_model, db)
                if semantic_res:
                    cached_data, similarity = semantic_res
                    cache_latency = int((time.perf_counter() - start_cache_time) * 1000)
                    await TraceService.append_timeline_stage(trace_id, "cache_hit:semantic", db)
                    
                    # Log usage (cost is 0.0, save estimated cost to cost_saved)
                    request_id = uuid.uuid4()
                    await UsageService.log_usage(
                        db=db,
                        user_id=user_id,
                        api_key_id=api_key_id,
                        request_id=request_id,
                        provider=cached_data["provider"],
                        model=cached_data["model"],
                        prompt_tokens=cached_data["prompt_tokens"],
                        completion_tokens=cached_data["completion_tokens"],
                        total_tokens=cached_data["total_tokens"],
                        cost=0.0,
                        latency_ms=cache_latency,
                        status_code=200,
                        error_message=None,
                        trace_id=trace_id,
                        ip_address=ip_address,
                        cache_type="semantic",
                        cost_saved=cached_data["estimated_cost"]
                    )
                    
                    # Finalize Trace in DB
                    await TraceService.update_trace(
                        trace_id=trace_id,
                        response=cached_data["response_text"],
                        status_code=200,
                        error_type="none",
                        error_message=None,
                        db=db
                    )
                    
                    return ChatResponse(
                        request_id=request_id,
                        provider=cached_data["provider"],
                        model=cached_data["model"],
                        response_text=cached_data["response_text"],
                        prompt_tokens=cached_data["prompt_tokens"],
                        completion_tokens=cached_data["completion_tokens"],
                        total_tokens=cached_data["total_tokens"],
                        cost=0.0,
                        latency_ms=cache_latency,
                        cache=CacheMetadata(hit=True, type="semantic", similarity=round(similarity, 4))
                    )
            
            # C. Cache Miss (both exact and semantic missed)
            await TraceService.append_timeline_stage(trace_id, "cache_miss", db)

        # 3. Fetch User Plan limits
        from app.models.user import User
        from sqlalchemy import select
        
        user_stmt = select(User.plan_type).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        plan_type = user_res.scalar_one_or_none() or "free"
        
        from app.core.config import PLANS
        plan_limits = PLANS.get(plan_type, PLANS["free"])
        
        plan_rpm = plan_limits["rate_limit_rpm"]
        daily_limit = plan_limits["requests_per_day"]
        plan_token_limit = plan_limits["tokens_per_month"]
        
        # 4. Fetch custom key override limits (if using API Key auth)
        key_rpm_override = None
        key_token_override = None
        
        if api_key_id:
            from app.models.api_key import APIKey
            key_stmt = select(APIKey.rate_limit_rpm, APIKey.monthly_token_quota).where(APIKey.id == api_key_id)
            key_res = await db.execute(key_stmt)
            key_row = key_res.first()
            if key_row:
                key_rpm_override = key_row.rate_limit_rpm
                key_token_override = key_row.monthly_token_quota

        # 5. Enforce Rate Limiting & Quotas checks
        from app.services.rate_limiter import RateLimiterService
        
        # Check RPM
        rpm_allowed = await RateLimiterService.check_rate_limit(
            user_id=user_id,
            key_id=api_key_id or user_id,
            plan_rpm=plan_rpm,
            key_rpm_override=key_rpm_override
        )
        if not rpm_allowed:
            err_msg = "Requests per minute limit exceeded. Please slow down."
            await TraceService.update_trace(
                trace_id=trace_id,
                response="[Rate Limit Exceeded]",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                error_type="rate_limit_exceeded",
                error_message=err_msg,
                db=db
            )
            LangfuseService.log_error(langfuse_trace, err_msg)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": err_msg
                    }
                }
            )
            
        # Check Daily Request Limit
        daily_allowed = await RateLimiterService.check_daily_request_quota(
            user_id=user_id,
            daily_limit=daily_limit,
            db=db
        )
        if not daily_allowed:
            err_msg = f"Daily request quota limit of {daily_limit} requests has been exceeded."
            await TraceService.update_trace(
                trace_id=trace_id,
                response="[Daily Requests Quota Exceeded]",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                error_type="token_quota_exceeded",
                error_message=err_msg,
                db=db
            )
            LangfuseService.log_error(langfuse_trace, err_msg)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "daily_requests_exceeded",
                        "message": err_msg
                    }
                }
            )
            
        # Check Monthly Token Limit
        monthly_allowed = await RateLimiterService.check_monthly_token_quota(
            user_id=user_id,
            key_id=api_key_id or user_id,
            plan_token_limit=plan_token_limit,
            key_token_override=key_token_override,
            db=db
        )
        if not monthly_allowed:
            err_msg = "Monthly token quota exceeded. Please upgrade your plan."
            await TraceService.update_trace(
                trace_id=trace_id,
                response="[Monthly Token Quota Exceeded]",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                error_type="token_quota_exceeded",
                error_message=err_msg,
                db=db
            )
            LangfuseService.log_error(langfuse_trace, err_msg)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "token_quota_exceeded",
                        "message": err_msg
                    }
                }
            )
            
        # Quota checks passed successfully
        await TraceService.append_timeline_stage(trace_id, "limits_passed", db)
            
        # 6. Delegate prompt routing and execution (with failovers) to RoutingService
        from app.services.routing_service import RoutingService
        response = await RoutingService.route_request(
            db=db,
            user_id=user_id,
            api_key_id=api_key_id,
            request_data=request_data,
            trace_id=trace_id,
            langfuse_trace=langfuse_trace,
            ip_address=ip_address
        )
        
        # 7. Cache Write Block for Cache Misses
        if settings.CACHE_ENABLED and response and response.response_text:
            if not embedding:
                embedding = await EmbeddingService.get_embedding(request_data.message, settings.EMBEDDING_PROVIDER)
            try:
                await CacheService.write_cache(
                    prompt=request_data.message,
                    response=response.response_text,
                    provider=response.provider,
                    model=response.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost=response.cost,
                    embedding=embedding,
                    embedding_model=emb_model,
                    db=db
                )
            except Exception as e:
                logger.error(f"Failed to save generated query into prompt caches: {e}")
                
        response.cache = CacheMetadata(hit=False)

        # Trigger Judge LLM Evaluation asynchronously in background
        if background_tasks and response and response.response_text:
            background_tasks.add_task(
                PromptEvaluator.evaluate_trace_async,
                trace_id=trace_id,
                prompt=request_data.message,
                response_text=response.response_text
            )

        return response

