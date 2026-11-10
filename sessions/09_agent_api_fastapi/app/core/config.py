"""Settings read once from environment variables and the session `.env` (pydantic-settings).

Used by: main.py (startup), core/security.py (JWT), agent/tools.py (Tavily key, data folder)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[2]  # the session folder (holds .env, data/, output/)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", extra="ignore")

    openai_api_key: SecretStr = Field(min_length=1)  # required and not empty: the app does not start without it
    tavily_api_key: SecretStr = Field(min_length=1)
    jwt_secret: SecretStr = Field(min_length=32)  # signs the access tokens; generate with `openssl rand -hex 32`
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    model: str = "openai:gpt-6-luna"
    run_timeout_s: int = 180  # a brief run normally takes 20-60 s
    data_dir: Path = PROJECT_DIR / "output"  # the SQLite database and saved briefs

    @property
    def db_path(self) -> Path:
        """One SQLite file for the conversations (checkpoints) and the thread and user records (store)."""
        return self.data_dir / "agent.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
