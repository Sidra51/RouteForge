import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import our configuration settings
from app.core.config import settings

# Import our database metadata base
from app.core.database import Base

# Import all SQLAlchemy models to register them with Base.metadata
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.api_key import APIKey
from app.models.usage import UsageLog
from app.models.provider_metric import ProviderMetric
from app.models.request_trace import RequestTrace
from app.models.cached_prompt import CachedPrompt
from app.models.guardrail_event import GuardrailEvent
from app.models.prompt_template import PromptTemplate
from app.models.prompt_version import PromptVersion
from app.models.prompt_experiment import PromptExperiment
from app.models.benchmark_job import BenchmarkJob
from app.models.benchmark_run import BenchmarkRun


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Dynamically set the SQLAlchemy URL in configuration from our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    """Run migrations synchronously inside the async connection context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async SQLAlchemy connections."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
