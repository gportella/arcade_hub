"""Application configuration and settings."""

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class EngineSpec(BaseModel):
    """Declarative information about a configured engine binary."""

    key: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    binary: str = Field(min_length=1)


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
    engine_specs: List[EngineSpec] = Field(
        default_factory=lambda: [EngineSpec(key="stockfish", name="Stockfish", binary="stockfish")],
        alias="CHESS_ENGINE_SPECS",
    )
    engine_timeout_seconds: float = Field(default=5.0, alias="CHESS_ENGINE_TIMEOUT_SECONDS", gt=0)
    engine_default_depth: int = Field(default=12, alias="CHESS_ENGINE_DEFAULT_DEPTH", ge=1, le=64)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "extra": "ignore",
    }

    @field_validator("engine_specs", mode="before")
    @classmethod
    def _parse_engine_specs(cls, value):
        if value is None or isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("CHESS_ENGINE_SPECS must be valid JSON") from exc
            return decoded
        if isinstance(value, dict):
            return [value]
        raise TypeError("Unsupported type for engine specs configuration")


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings instance."""

    return Settings()
