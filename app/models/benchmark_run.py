import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Text, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmark_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    trial_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trace_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    generation_tokens_per_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    end_to_end_tokens_per_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guardrail_status: Mapped[str] = mapped_column(String(20), default="passed", nullable=False)
    
    is_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    job: Mapped["BenchmarkJob"] = relationship("BenchmarkJob", back_populates="runs")
