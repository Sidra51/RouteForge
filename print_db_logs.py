import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.api_key import APIKey
from app.models.usage import UsageLog

# Force load
from app.models.refresh_token import RefreshToken
from app.core.database import Base

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Get last 5 successful logs
        stmt = select(UsageLog).where(UsageLog.status_code == 200).order_by(UsageLog.created_at.desc()).limit(5)
        result = await session.execute(stmt)
        logs = result.scalars().all()
        
        print(f"Found {len(logs)} recent logs:")
        for log in logs:
            print(f"ID: {log.id}")
            print(f"  Created: {log.created_at}")
            print(f"  Model: {log.model}")
            print(f"  Tokens: {log.total_tokens} (Prompt: {log.prompt_tokens}, Completion: {log.completion_tokens})")
            print(f"  Cost: {log.cost} (type: {type(log.cost)})")
            print(f"  Latency: {log.latency_ms} ms")
            print(f"  Status: {log.status_code}")
            print(f"  Error: {log.error_message}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
