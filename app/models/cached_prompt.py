import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class CachedPrompt(Base):
    __tablename__ = "cached_prompts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Store coordinates as a list of floats in a JSON column
    embedding: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-embedding-2")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        index=True, 
        nullable=False
    )
