import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    print("Testing connection to database...")
    async with engine.connect() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.commit()
            print("[SUCCESS] pgvector extension exists and is successfully activated!")
        except Exception as e:
            print("[FAILED] pgvector extension could not be enabled.")
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
