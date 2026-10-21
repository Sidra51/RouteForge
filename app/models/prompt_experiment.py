import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class PromptExperiment(Base):
    __tablename__ = "prompt_experiments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    variants: Mapped[list] = mapped_column(JSON, nullable=False)  # list of {"version_id": str, "weight": float}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    template: Mapped["PromptTemplate"] = relationship("PromptTemplate", back_populates="experiments")
    request_traces: Mapped[list["RequestTrace"]] = relationship(
        "RequestTrace",
        back_populates="experiment"
    )
