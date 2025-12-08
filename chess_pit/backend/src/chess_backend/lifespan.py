"""Application lifespan management."""

from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from alembic import command
from alembic.config import Config as AlembicConfig

from .config import Settings, get_settings
from .crud.users import get_user_by_username
from .db import init_db, session_context
from .models import User
from .security import hash_password

log = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
ALEMBIC_DIR = BACKEND_ROOT / "alembic"


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _prepare_data_dir(settings)
    _ensure_secret_key(settings)
    if settings.run_migrations:
        _run_migrations(settings)
    init_db()
    _bootstrap_admin(settings)
    yield


def _prepare_data_dir(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)


def _ensure_secret_key(settings: Settings) -> None:
    if settings.secret_key:
        return
    generated = secrets.token_urlsafe(48)
    object.__setattr__(settings, "secret_key", generated)
    log.warning(
        "CHESS_SECRET_KEY was not provided; generated ephemeral key. Tokens will reset on restart.",
    )


def _run_migrations(settings: Settings) -> None:
    if not ALEMBIC_INI.exists() or not ALEMBIC_DIR.exists():
        log.warning("Skipping migrations; Alembic configuration not found at %s", ALEMBIC_INI)
        return

    alembic_cfg = AlembicConfig(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")


def _bootstrap_admin(settings: Settings) -> None:
    if not settings.admin_username or not settings.admin_password:
        return

    with session_context() as session:
        if get_user_by_username(session, settings.admin_username):
            return
        admin = User(
            username=settings.admin_username,
            hashed_password=hash_password(settings.admin_password),
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        log.info("Created admin user '%s'", settings.admin_username)
