import uuid
from datetime import datetime, timezone
from typing import List
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    usage_logs: Mapped[List["UsageLog"]] = relationship(
        "UsageLog", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    request_traces: Mapped[List["RequestTrace"]] = relationship(
        "RequestTrace", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    prompt_templates: Mapped[List["PromptTemplate"]] = relationship(
        "PromptTemplate",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    prompt_versions: Mapped[List["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="user",
        cascade="all, delete-orphan"
    )
