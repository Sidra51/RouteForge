import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class BenchmarkJob(Base):
    __tablename__ = "benchmark_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    target_models: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    trials_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    bypass_cache: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    run_guardrails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="benchmark_jobs")
    runs: Mapped[List["BenchmarkRun"]] = relationship("BenchmarkRun", back_populates="job", cascade="all, delete-orphan")
