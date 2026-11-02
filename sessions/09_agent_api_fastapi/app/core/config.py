"""Settings read once from environment variables and the session `.env` (pydantic-settings)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[2]  # the session folder (holds .env, data/, output/)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    openai_api_key: SecretStr = Field(min_length=1)  # required and not empty: the app does not start without it
    tavily_api_key: SecretStr = Field(min_length=1)
    model: str = "openai:gpt-6-luna"
    run_timeout_s: int = 180  # a brief run normally takes 20-60 s
    users_file: Path = PROJECT_DIR / "data" / "users.json"
    data_dir: Path = PROJECT_DIR / "output"  # SQLite databases and saved briefs


@lru_cache
def get_settings() -> Settings:
    return Settings()
