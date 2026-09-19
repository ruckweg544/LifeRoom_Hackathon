"""
Application configuration.

Reads from environment variables (see .env.example). Falls back to a local
SQLite database when DATABASE_URL is not set, so the app runs immediately
without any cloud/database credentials.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LifeRoom API"
    environment: str = "development"

    # Falls back to a local SQLite file if no external DATABASE_URL is provided.
    # This lets the whole app run with zero external services.
    database_url: str = "sqlite:///./liferoom.db"

    # Comma-separated list of allowed CORS origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
