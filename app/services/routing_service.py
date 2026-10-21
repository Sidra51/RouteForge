import logging
import time
import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.gateway import ChatRequest, ChatResponse
from app.core.config import settings, PLANS, PROVIDER_METADATA
from app.providers.pricing import MODEL_PRICING
from app.providers.manager import ProviderManager
from app.models.provider_metric import ProviderMetric
from app.services.provider_health_service import ProviderHealthService
from app.services.cost_service import CostService
from app.services.usage_service import UsageService
from app.services.rate_limiter import RateLimiterService

logger = logging.getLogger(__name__)

class RoutingService:
    @classmethod
    async def select_provider_and_model(
        cls, 
        message: str, 
        policy: Optional[str], 
        fallback_chain: Optional[List[str]], 
        db: AsyncSession
    ) -> Tuple[str, str]:
        """
        Select the target provider and model based on the routing policy or fallback chain.
        Returns a tuple of (provider_name, model_name).
        """
        # 1. Identify all active configured providers (having valid API Keys in environment)
        keys_config = {
            "openai": settings.OPENAI_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "groq": settings.GROQ_API_KEY
        }
        configured_providers = [p for p, val in keys_config.items() if val and val.strip()]
        
        if not configured_providers:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No upstream LLM providers are configured on this server."
            )
            
        # 2. Fetch rolling database metrics to check healthy statuses
        stmt = select(ProviderMetric)
        res = await db.execute(stmt)
        metrics = {m.provider: m for m in res.scalars().all()}
        
        # Determine healthy providers (exclude unhealthy circuit breakers)
        healthy_providers = [
            p for p in configured_providers 
            if p not in metrics or metrics[p].health_status != "unhealthy"
        ]
        
        # Safe fallback: if everything is unhealthy, attempt routing to all configured options
        if not healthy_providers:
            healthy_providers = configured_providers

        # 3. Resolve Fallback Chain if explicitly defined
        if fallback_chain:
            # Find the first configured healthy provider in the fallback chain
            for p in fallback_chain:
                p_lc = p.lower()
                if p_lc in healthy_providers:
                    meta = PROVIDER_METADATA.get(p_lc, PROVIDER_METADATA["gemini"])
                    return p_lc, meta["default_model"]
            # Fall back to first option in chain if no healthy options found
            first_chain_p = fallback_chain[0].lower()
            meta = PROVIDER_METADATA.get(first_chain_p, PROVIDER_METADATA["gemini"])
            return first_chain_p, meta["default_model"]

        # 4. Resolve policy-based routing
        policy_lc = policy.lower() if policy else "cheapest"
        
        # CHEAPEST POLICY
        if policy_lc == "cheapest":
            return CostService.get_cheapest_model_for_providers(healthy_providers)
            
        # FASTEST POLICY
        elif policy_lc == "fastest":
            best_provider = None
            min_latency = float("inf")
            for p in healthy_providers:
                lat = metrics[p].avg_latency_ms if p in metrics else 1000
                if lat < min_latency:
                    min_latency = lat
                    best_provider = p
            provider = best_provider or healthy_providers[0]
            meta = PROVIDER_METADATA.get(provider, PROVIDER_METADATA["gemini"])
            return provider, meta["default_model"]
            
        # BEST QUALITY POLICY
        elif policy_lc == "best_quality":
            best_provider = None
            min_quality_rank = float("inf")
            for p in healthy_providers:
                rank = PROVIDER_METADATA.get(p, {}).get("quality_rank", 99)
                if rank < min_quality_rank:
                    min_quality_rank = rank
                    best_provider = p
            provider = best_provider or healthy_providers[0]
            meta = PROVIDER_METADATA.get(provider, PROVIDER_METADATA["gemini"])
            return provider, meta["default_model"]
            
        # AUTO POLICY (Length-based classification)
        elif policy_lc == "auto":
            prompt_len = len(message)
            if prompt_len < 100:
                # Short prompts -> cheapest
                return CostService.get_cheapest_model_for_providers(healthy_providers)
            elif prompt_len < 500:
                # Medium prompts -> balanced (Gemini)
                if "gemini" in healthy_providers:
                    return "gemini", PROVIDER_METADATA["gemini"]["default_model"]
                return CostService.get_cheapest_model_for_providers(healthy_providers)
            else:
                # Long/complex prompts -> best quality (OpenAI)
                if "openai" in healthy_providers:
                    return "openai", PROVIDER_METADATA["openai"]["default_model"]
                # Fallback to next best quality
                best_provider = None
                min_quality_rank = float("inf")
                for p in healthy_providers:
                    rank = PROVIDER_METADATA.get(p, {}).get("quality_rank", 99)
                    if rank < min_quality_rank:
                        min_quality_rank = rank
                        best_provider = p
                provider = best_provider or healthy_providers[0]
                meta = PROVIDER_METADATA.get(provider, PROVIDER_METADATA["gemini"])
                return provider, meta["default_model"]

        # Default fallback
        provider = healthy_providers[0]
        meta = PROVIDER_METADATA.get(provider, PROVIDER_METADATA["gemini"])
        return provider, meta["default_model"]

    @classmethod
    async def route_request(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        api_key_id: Optional[uuid.UUID],
        request_data: ChatRequest,
        trace_id: str,
        langfuse_trace,
        ip_address: Optional[str] = None
    ) -> ChatResponse:
        """
        Execute the primary request and implement the automatic failover retry loop.
        Logs metrics and updates circuit breakers on success/failure.
        """
        from app.services.trace_service import TraceService
        from app.services.langfuse_service import LangfuseService

        # Record routing decision stage
        await TraceService.append_timeline_stage(trace_id, "routing_decision", db)

        # 1. Resolve Primary Target
        primary_provider = None
        primary_model = None
        
        # If user explicitly targeted a provider/model, honor that as primary
        if request_data.provider:
            primary_provider = request_data.provider.lower()
            primary_model = request_data.model
        else:
            primary_provider, primary_model = await cls.select_provider_and_model(
                message=request_data.message,
                policy=request_data.routing_policy,
                fallback_chain=request_data.fallback_chain,
                db=db
            )
            
        # Standardize primary model defaults
        if not primary_model:
            meta = PROVIDER_METADATA.get(primary_provider, PROVIDER_METADATA["gemini"])
            primary_model = meta["default_model"]

        # 2. Build Fallback Attempt Chain
        keys_config = {
            "openai": settings.OPENAI_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "groq": settings.GROQ_API_KEY
        }
        configured_providers = [p for p, val in keys_config.items() if val and val.strip()]
        
        stmt = select(ProviderMetric)
        res = await db.execute(stmt)
        metrics = {m.provider: m for m in res.scalars().all()}
        
        # Fallbacks ordered list (exclude primary, prefer healthy configured providers)
        fallback_providers = [
            p for p in configured_providers 
            if p != primary_provider and (p not in metrics or metrics[p].health_status != "unhealthy")
        ]
        
        # Append even unhealthy ones at the very end as a last resort
        unhealthy_providers = [
            p for p in configured_providers 
            if p != primary_provider and p in metrics and metrics[p].health_status == "unhealthy"
        ]
        fallback_providers.extend(unhealthy_providers)

        # Final sequence: [Primary, Fallback 1, Fallback 2, ...]
        execution_chain = [(primary_provider, primary_model)]
        for p in fallback_providers:
            meta = PROVIDER_METADATA.get(p, PROVIDER_METADATA["gemini"])
            execution_chain.append((p, meta["default_model"]))

        # 3. Failover Loop execution
        errors_logged = []
        
        for attempt, (provider_name, model_name) in enumerate(execution_chain):
            request_id = uuid.uuid4()
            logger.info(f"Gateway execution attempt {attempt + 1}: routing to {provider_name} ({model_name})")
            
            # Log stage provider_call
            await TraceService.append_timeline_stage(trace_id, f"provider_call:{provider_name}", db)
            
            # Map provider to correct API key
            api_key = keys_config.get(provider_name, "")
            
            start_time = time.perf_counter()
            try:
                provider_instance = ProviderManager.get_provider(provider_name)
                result = await provider_instance.generate_chat(
                    model=model_name,
                    message=request_data.message,
                    temperature=request_data.temperature if request_data.temperature is not None else 0.7,
                    max_tokens=request_data.max_tokens if request_data.max_tokens is not None else 1000,
                    api_key=api_key
                )
            except Exception as e:
                result = {"error": f"Internal gateway exception: {str(e)}"}
                
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Check for downstream execution failure
            if result.get("error"):
                error_msg = result["error"]
                logger.warning(f"Attempt {attempt + 1} ({provider_name}) failed: {error_msg}")
                errors_logged.append(f"{provider_name}: {error_msg}")
                
                # Record failover attempt in trace
                await TraceService.record_attempt(
                    trace_id=trace_id,
                    attempt_idx=attempt + 1,
                    provider=provider_name,
                    model=model_name,
                    status="failed",
                    latency_ms=latency_ms,
                    cost=0.0,
                    error_msg=error_msg,
                    db=db
                )
                
                # Passive failure metric reporting
                await ProviderHealthService.record_failure(provider_name, db)
                
                # Log transaction failure to database
                await UsageService.log_usage(
                    db=db,
                    user_id=user_id,
                    api_key_id=api_key_id,
                    request_id=request_id,
                    provider=provider_name,
                    model=model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost=0.0,
                    latency_ms=latency_ms,
                    status_code=502,
                    error_message=error_msg,
                    trace_id=trace_id,
                    ip_address=ip_address
                )
                
                # Continue fallback loop
                continue
                
            # SUCCESS
            logger.info(f"Attempt {attempt + 1} ({provider_name}) succeeded.")
            
            # Calculate cost
            cost = CostService.calculate_token_cost(
                model=model_name,
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"]
            )
            
            # Record successful attempt in trace
            await TraceService.record_attempt(
                trace_id=trace_id,
                attempt_idx=attempt + 1,
                provider=provider_name,
                model=model_name,
                status="success",
                latency_ms=latency_ms,
                cost=cost,
                error_msg=None,
                db=db
            )
            
            # Log generation metadata to Langfuse
            LangfuseService.log_generation(
                trace_obj=langfuse_trace,
                provider=provider_name,
                model=model_name,
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                input_text=request_data.message,
                output_text=result["response_text"],
                latency_ms=latency_ms,
                cost=cost
            )
            
            # Passive success metric reporting
            await ProviderHealthService.record_success(provider_name, latency_ms, db)
            
            # Log successful query to database
            await UsageService.log_usage(
                db=db,
                user_id=user_id,
                api_key_id=api_key_id,
                request_id=request_id,
                provider=provider_name,
                model=model_name,
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                cost=cost,
                latency_ms=latency_ms,
                status_code=200,
                error_message=None,
                trace_id=trace_id,
                ip_address=ip_address
            )
            
            # Update trace with final output
            await TraceService.update_trace(
                trace_id=trace_id,
                response=result["response_text"],
                status_code=200,
                error_type="none",
                error_message=None,
                db=db
            )
            
            # Increment rate limit cache values
            await RateLimiterService.increment_usage(
                user_id=user_id,
                key_id=api_key_id or user_id,
                tokens_used=result["total_tokens"]
            )
            
            return ChatResponse(
                request_id=request_id,
                provider=provider_name,
                model=model_name,
                response_text=result["response_text"],
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                cost=round(cost, 6),
                latency_ms=latency_ms
            )

        # 4. Out of options (All fallbacks exhausted)
        logger.error("All providers in the routing fallback chain failed.")
        error_diagnostic = f"All upstream providers failed. Diagnostics: {', '.join(errors_logged)}"
        
        await TraceService.update_trace(
            trace_id=trace_id,
            response="[Bad Gateway]",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_type="provider_unavailable",
            error_message=error_diagnostic,
            db=db,
            is_success=False
        )

        LangfuseService.log_error(langfuse_trace, error_diagnostic)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_diagnostic
        )
