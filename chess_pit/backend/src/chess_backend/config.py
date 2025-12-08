"""Application configuration and settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralised application settings loaded from environment variables."""

    database_url: str = Field(default="sqlite:///./data/chess.db", alias="CHESS_DATABASE_URL")
    secret_key: Optional[str] = Field(default=None, alias="CHESS_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, alias="CHESS_ACCESS_TOKEN_EXPIRE_MINUTES")
    admin_username: Optional[str] = Field(default=None, alias="CHESS_ADMIN_USERNAME")
    admin_password: Optional[str] = Field(default=None, alias="CHESS_ADMIN_PASSWORD")
    data_dir: Path = Field(default=Path("./data"), alias="CHESS_DATA_DIR")
    run_migrations: bool = Field(default=False, alias="CHESS_RUN_MIGRATIONS")
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        alias="CHESS_CORS_ORIGINS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""

    return Settings()
