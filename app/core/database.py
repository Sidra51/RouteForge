from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create async engine
# Note: DATABASE_URL in .env must start with postgresql+asyncpg:// for async pg driver
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True to log all SQL queries
    future=True
)

# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for declarative SQLAlchemy models
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for injecting database session into API endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
