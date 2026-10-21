from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/pult"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    github_token: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    check_interval_sec: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
