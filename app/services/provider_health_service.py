import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_metric import ProviderMetric
from app.core.config import PROVIDER_METADATA

logger = logging.getLogger(__name__)

class ProviderHealthService:
    @staticmethod
    async def initialize_metrics(db: AsyncSession):
        """Pre-seed default metrics rows for all registered providers if they do not exist."""
        try:
            for provider in PROVIDER_METADATA.keys():
                stmt = select(ProviderMetric).where(ProviderMetric.provider == provider)
                result = await db.execute(stmt)
                metric = result.scalar_one_or_none()
                
                if not metric:
                    logger.info(f"Seeding default provider metrics for: {provider}")
                    new_metric = ProviderMetric(
                        provider=provider,
                        avg_latency_ms=1000,
                        success_rate=Decimal("100.00"),
                        consecutive_failures=0,
                        total_requests=0,
                        total_failures=0,
                        health_status="healthy",
                        last_failure_at=None
                    )
                    db.add(new_metric)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to initialize provider metrics: {e}")
            await db.rollback()

    @staticmethod
    async def record_success(provider: str, latency_ms: int, db: AsyncSession):
        """Record a successful request to a provider, recalculating EWMA latency and health status."""
        try:
            provider_lc = provider.lower()
            stmt = select(ProviderMetric).where(ProviderMetric.provider == provider_lc)
            result = await db.execute(stmt)
            metric = result.scalar_one_or_none()
            
            if not metric:
                # Fallback create if not pre-seeded
                metric = ProviderMetric(
                    provider=provider_lc,
                    avg_latency_ms=latency_ms,
                    success_rate=Decimal("100.00"),
                    consecutive_failures=0,
                    total_requests=1,
                    total_failures=0,
                    health_status="healthy"
                )
                db.add(metric)
            else:
                metric.total_requests += 1
                metric.consecutive_failures = 0
                
                # EWMA Latency update: 20% weight to current latency, 80% to historical average
                metric.avg_latency_ms = int(0.2 * latency_ms + 0.8 * metric.avg_latency_ms)
                
                # Recalculate success rate
                successes = metric.total_requests - metric.total_failures
                metric.success_rate = Decimal(str(round((successes / metric.total_requests) * 100, 2)))
                
                # Update status
                if metric.success_rate >= Decimal("80.00"):
                    metric.health_status = "healthy"
                else:
                    metric.health_status = "degraded"
                    
            metric.updated_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to record success metrics for {provider}: {e}")
            await db.rollback()

    @staticmethod
    async def record_failure(provider: str, db: AsyncSession):
        """Record a request failure for a provider, updating consecutive failures, success rate, and circuit breaker status."""
        try:
            provider_lc = provider.lower()
            stmt = select(ProviderMetric).where(ProviderMetric.provider == provider_lc)
            result = await db.execute(stmt)
            metric = result.scalar_one_or_none()
            
            now_time = datetime.now(timezone.utc)
            
            if not metric:
                metric = ProviderMetric(
                    provider=provider_lc,
                    avg_latency_ms=1000,
                    success_rate=Decimal("0.00"),
                    consecutive_failures=1,
                    total_requests=1,
                    total_failures=1,
                    health_status="degraded",
                    last_failure_at=now_time
                )
                db.add(metric)
            else:
                metric.total_requests += 1
                metric.total_failures += 1
                metric.consecutive_failures += 1
                metric.last_failure_at = now_time
                
                # Recalculate success rate
                successes = metric.total_requests - metric.total_failures
                metric.success_rate = Decimal(str(round((successes / metric.total_requests) * 100, 2)))
                
                # Update status based on circuit breaker rules:
                # Trigger unhealthy state if consecutive failures >= 3 or success rate falls below 50%
                if metric.consecutive_failures >= 3 or metric.success_rate < Decimal("50.00"):
                    metric.health_status = "unhealthy"
                else:
                    metric.health_status = "degraded"
                    
            metric.updated_at = now_time
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to record failure metrics for {provider}: {e}")
            await db.rollback()
