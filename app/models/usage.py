import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=False, 
        default=uuid.uuid4, 
        unique=True, 
        index=True, 
        nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Numeric supports sub-cent values (e.g. $0.00015) without floating point issues
    cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0.000000, nullable=False)
    cost_saved: Mapped[float] = mapped_column(Numeric(10, 6), default=0.000000, nullable=True)
    cache_type: Mapped[str] = mapped_column(String(20), default="none", nullable=True, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        index=True, 
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_logs")
    api_key: Mapped["APIKey"] = relationship("APIKey", back_populates="usage_logs")
