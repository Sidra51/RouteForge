from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.providers.manager import ProviderManager
from app.core.database import get_db
from app.models.provider_metric import ProviderMetric

router = APIRouter()

@router.get("/status")
async def get_providers_status() -> List[Dict[str, Any]]:
    """
    Get the configuration health status and metadata of registered LLM providers.
    Checks if required API keys are configured in the environment.
    """
    keys_config = {
        "gemini": settings.GEMINI_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "deepseek": settings.DEEPSEEK_API_KEY,
        "groq": settings.GROQ_API_KEY
    }
    
    status_list = []
    for provider_name, provider_cls in ProviderManager.get_all_providers().items():
        api_key = keys_config.get(provider_name)
        is_configured = bool(api_key and api_key.strip())
        status_list.append({
            "provider": provider_name,
            "status": "healthy" if is_configured else "unconfigured",
            "models_supported": len(provider_cls.get_supported_models())
        })
        
    return status_list

@router.get("/models")
async def get_providers_models() -> Dict[str, List[str]]:
    """
    Get the list of supported models grouped by provider.
    This dynamically syncs front-end selections with the active backend providers.
    """
    models_mapping = {}
    for provider_name, provider_cls in ProviderManager.get_all_providers().items():
        models_mapping[provider_name] = provider_cls.get_supported_models()
    return models_mapping

@router.get("/health")
async def get_providers_health(db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get the rolling health metrics for all registered providers.
    Returns latencies, success rates, failure metrics, and circuit status.
    """
    stmt = select(ProviderMetric).order_by(ProviderMetric.provider)
    res = await db.execute(stmt)
    metrics = res.scalars().all()
    
    output = []
    for m in metrics:
        output.append({
            "provider": m.provider,
            "status": m.health_status,
            "avg_latency_ms": m.avg_latency_ms,
            "success_rate": float(m.success_rate),
            "total_requests": m.total_requests,
            "total_failures": m.total_failures,
            "consecutive_failures": m.consecutive_failures
        })
    return output
