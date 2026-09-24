"""Application settings.

Every value comes from environment variables (or a local .env file in development).
Required secrets have no defaults, so the app refuses to start without them instead
of silently running with an insecure fallback.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Environment ---
    environment: str = Field(default="development", pattern="^(development|test|production)$")
    log_level: str = "INFO"

    # --- LLM (Groq, OpenAI-compatible endpoint) ---
    groq_api_key: str = Field(min_length=1)
    groq_base_url: str = "https://api.groq.com/openai/v1"
    model_name: str = "openai/gpt-oss-120b"
    max_tokens: int = 1500
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    max_tool_iterations: int = 6
    history_window: int = 30  # messages of past context sent to the LLM per request

    # --- Auth ---
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # --- Database ---
    database_url: str = "sqlite:///./fitcoach.db"

    # --- HTTP ---
    cors_origins: list[str] = ["http://localhost:5173"]
    rate_limit_storage_uri: str = "memory://"  # use redis://... when running several instances
    login_rate_limit: str = "5/minute"
    chat_rate_limit: str = "20/minute"

    # --- Reminders worker ---
    reminder_poll_seconds: int = 30
    default_timezone: str = "UTC"
    # Free hosting tiers often allow only one service. When true, the API process also
    # runs the reminder loop in a background thread (safe with several processes, since
    # each reminder is claimed atomically).
    run_reminder_worker_in_api: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        # Hosts like Neon and Render hand out postgres:// URLs; SQLAlchemy needs the driver name.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @field_validator("jwt_secret")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if "change" in value.lower() and "production" in value.lower():
            raise ValueError("JWT_SECRET is still the placeholder value; generate a real secret")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()