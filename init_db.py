import asyncio
from app.core.database import engine, Base

# Import all models to ensure they register with Base.metadata
from app.models.user import User
from app.models.api_key import APIKey
from app.models.usage import UsageLog
from app.models.refresh_token import RefreshToken
from app.models.request_trace import RequestTrace
from app.models.provider_metric import ProviderMetric
from app.models.cached_prompt import CachedPrompt
from app.models.guardrail_event import GuardrailEvent
from app.models.prompt_template import PromptTemplate
from app.models.prompt_version import PromptVersion
from app.models.prompt_experiment import PromptExperiment
from app.models.benchmark_job import BenchmarkJob
from app.models.benchmark_run import BenchmarkRun

async def init_db():
    print("Creating all database tables via SQLAlchemy metadata...")
    async with engine.begin() as conn:
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            print(f"Notice (pgvector): {e}")
        await conn.run_sync(Base.metadata.create_all)
    print("All database tables successfully created in 'llm_gateway'!")

if __name__ == "__main__":
    asyncio.run(init_db())
