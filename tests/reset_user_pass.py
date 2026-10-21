import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Import ALL models to ensure SQLAlchemy registry has resolved everything
from app.models.user import User
from app.models.api_key import APIKey
from app.models.usage import UsageLog
from app.models.cached_prompt import CachedPrompt
from app.models.refresh_token import RefreshToken
from app.models.provider_metric import ProviderMetric
from app.models.request_trace import RequestTrace

from app.core import security

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        stmt = select(User).where(User.email == "sidra@example.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            print(f"Found user: {user.email}. Resetting password to 'password123'...")
            hashed = security.get_password_hash("password123")
            user.hashed_password = hashed
            await session.commit()
            print("[SUCCESS] Password has been reset!")
        else:
            print("User sidra@example.com not found. Creating it...")
            hashed = security.get_password_hash("password123")
            new_user = User(
                email="sidra@example.com",
                hashed_password=hashed,
                role="USER",
                is_active=True,
                plan_type="free"
            )
            session.add(new_user)
            await session.commit()
            print("[SUCCESS] User sidra@example.com has been created!")

if __name__ == "__main__":
    asyncio.run(main())
