from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://tension_user:devpassword123@localhost:5432/tension_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"

    # Scoring
    scoring_version: str = "v1.0"
    scoring_scale_factor: float = 20.0
    recalculate_lookback_days: int = 90

    # Admin
    admin_api_key: str = "dev_admin_key"

    # Data sources
    gdelt_enabled: bool = True
    acled_access_key: str = ""
    acled_email: str = ""
    newsapi_key: str = ""

    # AI / LLM
    llm_api_key: str = ""
    llm_model: str = "claude-3-7-sonnet-20250219"
    llm_prompt_version: str = "v1.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
