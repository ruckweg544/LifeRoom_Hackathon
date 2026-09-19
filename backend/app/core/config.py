"""
Application configuration.

Reads from environment variables (see .env.example). Falls back to a local
SQLite database when DATABASE_URL is not set, so the app runs immediately
without any cloud/database credentials.
"""
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import SecretStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="", pattern=r"^[a-zA-Z0-9.\-]*$")
    ai_timezone: str = "America/New_York"

    app_name: str = "LifeRoom API"
    environment: str = "development"

    # Falls back to a local SQLite file if no external DATABASE_URL is provided.
    # This lets the whole app run with zero external services.
    database_url: str = "sqlite:///./liferoom.db"

    # Comma-separated list of allowed CORS origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("ai_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("AI_TIMEZONE must be an IANA timezone") from exc
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
