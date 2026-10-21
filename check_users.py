import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.api_key import APIKey
from app.models.usage import UsageLog
from app.core.database import Base

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        print(f"Users in DB: {[u.email for u in users]}")

if __name__ == "__main__":
    asyncio.run(main())
