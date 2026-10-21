import asyncio
import asyncpg

async def create_db():
    # Connect to default postgres DB
    # Try password from .env first: sidra2004, fallback to postgres
    passwords = ["sidra2004", "postgres"]
    
    for pwd in passwords:
        try:
            print(f"Connecting to Postgres with password: {pwd}...")
            conn = await asyncpg.connect(
                user="postgres",
                password=pwd,
                host="localhost",
                port=5432,
                database="postgres"
            )
            
            # Check if llm_gateway exists
            db_exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'llm_gateway'"
            )
            
            if not db_exists:
                await conn.execute("CREATE DATABASE llm_gateway")
                print("Successfully created database 'llm_gateway'!")
            else:
                print("Database 'llm_gateway' already exists.")
                
            await conn.close()
            return
        except Exception as e:
            print(f"Connection attempt failed: {e}")

if __name__ == "__main__":
    asyncio.run(create_db())
