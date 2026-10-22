from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_REQUIRED: bool = False
    STORE_FULL_PAYLOAD: bool = True
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # Prompt Caching Configurations
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 86400
    SEMANTIC_CACHE_THRESHOLD: float = 0.90
    EMBEDDING_PROVIDER: str = "gemini"

    # Evaluator (Judge) Configurations
    EVALUATOR_PROVIDER: str = "gemini"
    EVALUATOR_MODEL: str = "gemini-2.0-flash"

settings = Settings()


PLANS = {
    "free": {
        "requests_per_day": 100,
        "tokens_per_month": 100000,
        "rate_limit_rpm": 60
    },
    "pro": {
        "requests_per_day": 1000,
        "tokens_per_month": 1000000,
        "rate_limit_rpm": 300
    },
    "enterprise": {
        "requests_per_day": 99999999,
        "tokens_per_month": 99999999,
        "rate_limit_rpm": 1000
    }
}

PROVIDER_METADATA = {
    "openai": {
        "quality_rank": 1,
        "speed_rank": 3,
        "default_model": "gpt-4o-mini"
    },
    "gemini": {
        "quality_rank": 2,
        "speed_rank": 2,
        "default_model": "gemini-2.5-flash"
    },
    "deepseek": {
        "quality_rank": 3,
        "speed_rank": 4,
        "default_model": "deepseek-chat"
    },
    "groq": {
        "quality_rank": 4,
        "speed_rank": 1,
        "default_model": "qwen/qwen3.8-27b"
    }
}
