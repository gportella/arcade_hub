"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from chess_backend import db as db_module
from chess_backend.config import get_settings
from chess_backend.db import get_session
from chess_backend.main import app


@pytest.fixture(autouse=True)
def configure_settings(tmp_path) -> Iterator[None]:
    os.environ.setdefault("CHESS_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("CHESS_DATABASE_URL", "sqlite://")
    os.environ.setdefault("CHESS_DATA_DIR", str(tmp_path / "data"))
    os.environ.setdefault("CHESS_RUN_MIGRATIONS", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest_asyncio.fixture()
async def client(engine) -> AsyncIterator[AsyncClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    db_module._engine = engine  # type: ignore[attr-defined]
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()
    db_module._engine = None  # type: ignore[attr-defined]
    get_settings.cache_clear()
