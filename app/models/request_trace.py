import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class RequestTrace(Base):
    __tablename__ = "request_traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )
    
    # Previews of input/output to prevent DB bloating (500 chars max if STORE_FULL_PAYLOAD is False)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Outcome metadata
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=True)  # rate_limit_exceeded, token_quota_exceeded, etc.
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timeline stages list following structured format:
    # [{"stage": "...", "timestamp": "...", "duration_ms": ...}]
    timeline: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    
    # Retry execution attempts:
    # [{"attempt": 1, "provider": "...", "model": "...", "status": "...", "latency_ms": ..., "cost": ..., "error": "..."}]
    attempts: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Phase 9: Prompt Versioning & Evaluations
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    evaluation_scores: Mapped[dict] = mapped_column(JSON, nullable=True)  # {"helpfulness": 4.5, "accuracy": 4.0, ...}
    is_success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_guardrail_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        index=True, 
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="request_traces")
    prompt_version: Mapped["PromptVersion"] = relationship("PromptVersion", back_populates="request_traces")
    experiment: Mapped["PromptExperiment"] = relationship("PromptExperiment", back_populates="request_traces")

