import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class GuardrailEvent(Base):
    __tablename__ = "guardrail_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    detector: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "regex", "llm", "size_validator"
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "prompt_injection", "jailbreak", "pii", "toxicity", "size_limit"
    action_taken: Mapped[str] = mapped_column(String(20), nullable=False) # e.g. "block", "mask", "warn"
    severity: Mapped[str] = mapped_column(String(20), nullable=False) # e.g. "low", "medium", "high", "critical"
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    matched_detail: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_preview: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )
