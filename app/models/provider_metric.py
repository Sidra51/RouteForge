import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class ProviderMetric(Base):
    __tablename__ = "provider_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    success_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health_status: Mapped[str] = mapped_column(String(20), default="healthy", nullable=False) # healthy, degraded, unhealthy
    last_failure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
