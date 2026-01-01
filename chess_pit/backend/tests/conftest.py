"""Shared pytest fixtures."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator

import chess
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from chess_backend import db as db_module
from chess_backend.api import routes_games
from chess_backend.config import get_settings
from chess_backend.crud.users import get_user_by_engine_key, get_user_by_username
from chess_backend.db import get_session
from chess_backend.main import app
from chess_backend.models import User
from chess_backend.security import hash_password
from chess_backend.services import engine_runner


@pytest.fixture(autouse=True)
def configure_settings(tmp_path) -> Iterator[None]:
    os.environ.setdefault("CHESS_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("CHESS_DATABASE_URL", "sqlite://")
    os.environ.setdefault("CHESS_DATA_DIR", str(tmp_path / "data"))
    os.environ.setdefault("CHESS_RUN_MIGRATIONS", "false")
    os.environ.setdefault("CHESS_ADMIN_USERNAME", "admin")
    os.environ.setdefault("CHESS_ADMIN_PASSWORD", "AdminPass123")

    mock_specs = json.dumps(
        [
            {
                "key": "mock",
                "name": "Mock Engine",
                "binary": "mock-binary",
                "default_depth": 3,
                "max_depth": 10,
            }
        ]
    )
    os.environ.setdefault("CHESS_ENGINE_SPECS", mock_specs)
    get_settings.cache_clear()

    original_compute = engine_runner.compute_best_move
    original_route_compute = routes_games.compute_best_move
    original_analysis = engine_runner.compute_analysis
    original_route_analysis = routes_games.compute_analysis

    def _fake_compute(spec, board, *, depth):
        """Return a deterministic opening move for tests."""

        trial_board = board.copy()
        move = chess.Move.from_uci("e2e4")
        if move not in trial_board.legal_moves:
            legal = next(iter(trial_board.legal_moves), None)
            if legal is None:
                raise RuntimeError("No legal moves available in test mock")
            move = legal
        san = trial_board.san(move)
        trial_board.push(move)
        return engine_runner.EngineMove(uci=move.uci(), san=san, fen=trial_board.fen())

    def _fake_analyse(spec, board, *, depth):
        """Return a deterministic principal variation for tests."""

        trial_board = board.copy()
        line_moves: list[chess.Move] = []
        preferred = chess.Move.from_uci("e2e4")
        if preferred in trial_board.legal_moves:
            line_moves.append(preferred)
        else:
            try:
                first_legal = next(iter(trial_board.legal_moves))
                line_moves.append(first_legal)
            except StopIteration:
                line_moves = []

        pv_san: list[str] = []
        temp_board = board.copy()
        for move in line_moves:
            pv_san.append(temp_board.san(move))
            temp_board.push(move)

        best_uci = line_moves[0].uci() if line_moves else None
        best_san = pv_san[0] if pv_san else None
        mate_in = 0 if not line_moves and trial_board.is_game_over() else None

        return engine_runner.EngineAnalysis(
            depth=depth,
            best_move_uci=best_uci,
            best_move_san=best_san,
            evaluation_cp=32,
            mate_in=mate_in,
            line_uci=[move.uci() for move in line_moves],
            line_san=pv_san,
        )

    engine_runner.compute_best_move = _fake_compute  # type: ignore[assignment]
    routes_games.compute_best_move = _fake_compute  # type: ignore[assignment]
    engine_runner.compute_analysis = _fake_analyse  # type: ignore[assignment]
    routes_games.compute_analysis = _fake_analyse  # type: ignore[assignment]

    yield

    engine_runner.compute_best_move = original_compute  # type: ignore[assignment]
    routes_games.compute_best_move = original_route_compute  # type: ignore[assignment]
    engine_runner.compute_analysis = original_analysis  # type: ignore[assignment]
    routes_games.compute_analysis = original_route_analysis  # type: ignore[assignment]
    get_settings.cache_clear()
    os.environ.pop("CHESS_ENGINE_SPECS", None)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            if not get_user_by_username(session, "admin"):
                admin_user = User(
                    username="admin",
                    hashed_password=hash_password("AdminPass123"),
                    is_admin=True,
                )
                session.add(admin_user)

            settings = get_settings()
            for spec in settings.engine_specs:
                if get_user_by_engine_key(session, spec.key):
                    continue
                engine_user = User(
                    username=f"engine_{spec.key}",
                    hashed_password=hash_password("EnginePass123!"),
                    is_admin=False,
                    is_engine=True,
                    engine_key=spec.key,
                    rating=2000,
                )
                session.add(engine_user)

            session.commit()
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
