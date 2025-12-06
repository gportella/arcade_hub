"""Entry point for the Solve Parking FastAPI application."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import sqlite3
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from . import solver
from .models import (
    CreatePuzzleRequest,
    DeleteConfigResponse,
    ErrorResponse,
    Exit,
    MoveRequest,
    MoveResponse,
    PuzzleConfigResponse,
    PuzzleState,
    PuzzleSummary,
    SolveResponse,
    UpdatePuzzleRequest,
)
from .repository import PuzzleRecord, PuzzleRepository
from .services import (
    InvalidMoveError,
    InvalidPuzzleError,
    apply_move,
    initial_state,
    is_solved,
    validate_state,
)


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not any(
    isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers
):
    root_handler = logging.StreamHandler()
    root_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(root_handler)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = True
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

app = FastAPI(title="Solve Parking API", version="0.1.0")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "puzzles.sqlite3"
DEFAULT_PUZZLE_NAME = "Starter Puzzle"

SESSION_HEADER = "X-Session-ID"
SESSION_COOKIE = "sp-session-id"
SESSION_MAX_AGE = 60 * 60 * 24 * 30
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{8,128}$")

_session_id_ctx: ContextVar[str | None] = ContextVar("session_id", default=None)
_session_store_lock = threading.Lock()


@dataclass
class SessionData:
    state: PuzzleState
    completed: bool
    updated_at: float


def _session_store() -> dict[str, SessionData]:
    store = cast(
        Optional[dict[str, SessionData]], getattr(app.state, "session_store", None)
    )
    if store is None:
        store = {}
        app.state.session_store = store
    return store


def _generate_session_id() -> str:
    return secrets.token_urlsafe(24)


def _resolve_session_identifier(
    primary: str | None, fallback: str | None = None
) -> str:
    candidate = primary or fallback
    if candidate and _SESSION_ID_PATTERN.fullmatch(candidate):
        return candidate
    return _generate_session_id()


def _set_default_state(state: PuzzleState, completed: bool) -> None:
    app.state.default_state = state.model_copy(deep=True)
    app.state.default_completed = completed


def _default_state() -> tuple[PuzzleState, bool]:
    state = cast(Optional[PuzzleState], getattr(app.state, "default_state", None))
    completed = cast(Optional[bool], getattr(app.state, "default_completed", None))
    if state is None or completed is None:
        base = initial_state()
        completed_flag = is_solved(base)
        _set_default_state(base, completed_flag)
        state = cast(PuzzleState, app.state.default_state)
        completed = cast(bool, app.state.default_completed)
    return state.model_copy(deep=True), bool(completed)


def _ensure_session_entry(session_id: str) -> SessionData:
    store = _session_store()
    with _session_store_lock:
        entry = store.get(session_id)
        if entry is None:
            state, completed = _default_state()
            entry = SessionData(state=state, completed=completed, updated_at=time.time())
            store[session_id] = entry
    return entry


def _session_id() -> str:
    session_id = _session_id_ctx.get()
    if not session_id:
        raise RuntimeError("Session context missing.")
    return session_id


def _get_repository() -> PuzzleRepository:
    repo = cast(Optional[PuzzleRepository], getattr(app.state, "repository", None))
    if repo is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        repo = PuzzleRepository(DB_PATH)
        app.state.repository = repo
    return repo


def _record_to_summary(record: PuzzleRecord) -> PuzzleSummary:
    return PuzzleSummary(
        id=record.id,
        name=record.name,
        size=record.size,
        exit=Exit(row=record.exit_row, col=record.exit_col),
        vehicle_count=record.vehicle_count,
        active=record.active,
        created_at=record.created_at,
    )


def _record_to_response(record: PuzzleRecord) -> PuzzleConfigResponse:
    return PuzzleConfigResponse(
        id=record.id,
        name=record.name,
        state=record.to_state(),
        active=record.active,
        created_at=record.created_at,
    )


class StateBroadcaster:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            peers = self._connections.setdefault(session_id, set())
            peers.add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            peers = self._connections.get(session_id)
            if not peers:
                return
            peers.discard(websocket)
            if not peers:
                self._connections.pop(session_id, None)

    async def broadcast_state(
        self, session_id: str, state: PuzzleState, *, completed: bool
    ) -> None:
        payload = {
            "type": "state",
            "session": session_id,
            "state": state.model_dump(),
            "completed": completed,
            "timestamp": asyncio.get_running_loop().time(),
        }
        async with self._lock:
            recipients = list(self._connections.get(session_id, ()))

        if not recipients:
            return

        stale: list[WebSocket] = []
        for connection in recipients:
            logger.debug("Broadcasting state to %s", connection.client)
            try:
                await connection.send_json(payload)
            except Exception:
                logger.exception("Failed to send state update", exc_info=True)
                stale.append(connection)

        if stale:
            async with self._lock:
                peers = self._connections.get(session_id)
                if peers is None:
                    return
                for connection in stale:
                    peers.discard(connection)
                if not peers:
                    self._connections.pop(session_id, None)


broadcaster = StateBroadcaster()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[SESSION_HEADER],
)


@app.middleware("http")
async def _attach_session(request: Request, call_next):
    session_id = _resolve_session_identifier(
        request.headers.get(SESSION_HEADER), request.cookies.get(SESSION_COOKIE)
    )
    token = _session_id_ctx.set(session_id)
    _ensure_session_entry(session_id)
    try:
        response = await call_next(request)
    except Exception:
        _session_id_ctx.reset(token)
        raise

    response.headers[SESSION_HEADER] = session_id
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    _session_id_ctx.reset(token)
    return response


@app.on_event("startup")
def _initialize_state() -> None:
    repo = _get_repository()
    default_state = initial_state()
    repo.ensure_default_puzzle(DEFAULT_PUZZLE_NAME, default_state)
    state = repo.get_active_state()

    if state is None:
        state = default_state

    try:
        validate_state(state)
    except InvalidPuzzleError as exc:
        logger.warning("Invalid puzzle found in repository: %s", exc)
        state = default_state

    _set_default_state(state, completed=is_solved(state))


@app.get("/health", summary="Health check", response_model=dict[str, str])
def health() -> dict[str, str]:
    """Return a simple health response."""
    return {"status": "ok"}


@app.get(
    "/api/puzzle", response_model=PuzzleState, summary="Fetch current puzzle state"
)
async def get_puzzle() -> PuzzleState:
    """Return the latest puzzle snapshot."""

    state = _state()
    session_id = _session_id()
    await broadcaster.broadcast_state(session_id, state, completed=_completed())
    return state


@app.put(
    "/api/puzzle",
    response_model=MoveResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
    summary="Replace the current puzzle state",
)
async def set_puzzle(state: PuzzleState) -> MoveResponse:
    try:
        validate_state(state)
    except InvalidPuzzleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    completed = is_solved(state)
    _set_state(state, completed=completed)
    session_id = _session_id()
    await broadcaster.broadcast_state(session_id, state, completed=completed)
    return MoveResponse(state=state, completed=completed)


@app.get(
    "/api/configs",
    response_model=list[PuzzleSummary],
    summary="List stored puzzle configurations",
)
async def list_configs() -> list[PuzzleSummary]:
    records = _get_repository().list_puzzles()
    return [_record_to_summary(record) for record in records]


@app.post(
    "/api/configs",
    response_model=PuzzleConfigResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
    summary="Persist a new puzzle configuration",
)
async def create_config(request: CreatePuzzleRequest) -> PuzzleConfigResponse:
    try:
        validate_state(request.state)
    except InvalidPuzzleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    repo = _get_repository()
    try:
        record = repo.save_puzzle(
            request.name, request.state, activate=request.activate
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A puzzle with that name already exists.",
        ) from exc

    if record.active:
        state = record.to_state()
        completed = is_solved(state)
        _set_state(state, completed=completed, update_default=True)
        session_id = _session_id()
        await broadcaster.broadcast_state(session_id, state, completed=completed)

    return _record_to_response(record)


@app.put(
    "/api/configs/{config_id}",
    response_model=PuzzleConfigResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
    summary="Update a stored puzzle configuration",
)
async def update_config(
    config_id: int, request: UpdatePuzzleRequest
) -> PuzzleConfigResponse:
    try:
        validate_state(request.state)
    except InvalidPuzzleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    repo = _get_repository()
    try:
        record = repo.update_puzzle(
            config_id,
            request.state,
            name=request.name,
            activate=request.activate,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A puzzle with that name already exists.",
        ) from exc

    if record.active:
        state = record.to_state()
        completed = is_solved(state)
        _set_state(state, completed=completed, update_default=True)
        session_id = _session_id()
        await broadcaster.broadcast_state(session_id, state, completed=completed)

    return _record_to_response(record)


@app.delete(
    "/api/configs/{config_id}",
    response_model=DeleteConfigResponse,
    status_code=status.HTTP_200_OK,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Delete a stored puzzle configuration",
)
async def delete_config(config_id: int) -> DeleteConfigResponse:
    repo = _get_repository()
    try:
        target = repo.get_puzzle(config_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    repo.delete_puzzles([config_id])

    new_record: PuzzleRecord | None = None
    activated_name: str | None = None
    new_state: PuzzleState | None = None
    completed: bool | None = None
    was_active = target.active

    if was_active:
        remaining = repo.list_puzzles()
        active_candidate = next((item for item in remaining if item.active), None)

        if active_candidate is not None:
            new_record = repo.get_puzzle(active_candidate.id)
            activated_name = new_record.name
        elif remaining:
            try:
                new_record = repo.activate_puzzle(remaining[0].id)
            except KeyError:
                new_record = None
            else:
                activated_name = new_record.name
        else:
            default_state = initial_state()
            repo.ensure_default_puzzle(DEFAULT_PUZZLE_NAME, default_state)
            refreshed = repo.list_puzzles()
            active_candidate = next((item for item in refreshed if item.active), None)
            if active_candidate is not None:
                new_record = repo.get_puzzle(active_candidate.id)
                activated_name = new_record.name
            else:
                activated_name = DEFAULT_PUZZLE_NAME

        if new_record is not None:
            new_state = new_record.to_state()
        else:
            new_state = initial_state()

        try:
            validate_state(new_state)
        except InvalidPuzzleError as exc:
            logger.warning("Invalid puzzle after deletion: %s", exc)
            new_state = initial_state()
            activated_name = DEFAULT_PUZZLE_NAME
            repo.ensure_default_puzzle(DEFAULT_PUZZLE_NAME, new_state)
            refreshed = repo.list_puzzles()
            active_candidate = next((item for item in refreshed if item.active), None)
            if active_candidate is not None:
                try:
                    new_record = repo.get_puzzle(active_candidate.id)
                    activated_name = new_record.name
                except KeyError:
                    new_record = None

        completed = is_solved(new_state)
        _set_state(new_state, completed=completed, update_default=True)
        session_id = _session_id()
        await broadcaster.broadcast_state(session_id, new_state, completed=completed)

    active_after = repo.get_active_state() is not None

    return DeleteConfigResponse(
        removed_id=config_id,
        removed_name=target.name,
        active=active_after,
        activated_name=activated_name,
        state=new_state if was_active else None,
        completed=completed,
    )


@app.get(
    "/api/configs/{config_id}",
    response_model=PuzzleConfigResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Fetch a stored puzzle configuration",
)
async def get_config(config_id: int) -> PuzzleConfigResponse:
    repo = _get_repository()
    try:
        record = repo.get_puzzle(config_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _record_to_response(record)


@app.post(
    "/api/configs/{config_id}/activate",
    response_model=PuzzleConfigResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Activate a stored puzzle configuration",
)
async def activate_config(config_id: int) -> PuzzleConfigResponse:
    repo = _get_repository()
    try:
        record = repo.activate_puzzle(config_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    state = record.to_state()
    completed = is_solved(state)
    _set_state(state, completed=completed, update_default=True)
    session_id = _session_id()
    await broadcaster.broadcast_state(session_id, state, completed=completed)
    return _record_to_response(record)


@app.post(
    "/api/move",
    response_model=MoveResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
    summary="Apply a move to the puzzle",
)
async def move_vehicle(move: MoveRequest) -> MoveResponse:
    """Apply a move and persist the updated puzzle."""

    payload = move.model_dump() if hasattr(move, "model_dump") else move.dict()
    logger.info("Move request payload: %s", payload)
    state = _state()
    session_id = _session_id()
    try:
        result = apply_move(state, move)
    except InvalidMoveError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    _set_state(result.state, completed=result.completed)
    logger.debug("State after move: completed=%s", result.completed)
    await broadcaster.broadcast_state(
        session_id, result.state, completed=result.completed
    )
    return MoveResponse(state=result.state, completed=result.completed)


@app.post(
    "/api/randmove",
    response_model=MoveResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
    summary="Apply a random move",
)
async def move_random() -> MoveResponse:
    """Random move"""
    state = _state()
    session_id = _session_id()
    result = solver.move_random(state)
    _set_state(result.state, completed=result.completed)
    logger.debug("State after move: completed=%s", result.completed)
    await broadcaster.broadcast_state(
        session_id, result.state, completed=result.completed
    )
    return MoveResponse(state=result.state, completed=result.completed)


@app.post(
    "/api/solve",
    response_model=SolveResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
    summary="Attempt to solve the current puzzle",
)
async def solve_puzzle() -> SolveResponse:
    """Run the solver from the current state and return the resulting puzzle."""

    state = _state()
    session_id = _session_id()
    started = time.perf_counter()
    result, moves, path = solver.solve_it(state)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    _set_state(result.state, completed=result.completed)
    await broadcaster.broadcast_state(
        session_id, result.state, completed=result.completed
    )
    return SolveResponse(
        state=result.state,
        completed=result.completed,
        moves=moves,
        path=path,
        elapsed_ms=elapsed_ms,
    )


@app.post(
    "/api/reset", response_model=PuzzleState, summary="Reset puzzle to starting layout"
)
async def reset_puzzle() -> PuzzleState:
    """Restore the puzzle to its default configuration."""

    repo = _get_repository()
    state = repo.get_active_state()

    if state is None:
        state = initial_state()

    try:
        validate_state(state)
    except InvalidPuzzleError as exc:
        logger.warning("Invalid puzzle found during reset: %s", exc)
        state = initial_state()

    completed = is_solved(state)
    _set_state(state, completed=completed, update_default=True)
    session_id = _session_id()
    await broadcaster.broadcast_state(session_id, state, completed=completed)
    return state


@app.websocket("/ws/state")
async def puzzle_updates(websocket: WebSocket) -> None:
    session_token = websocket.query_params.get("session")
    session_id = _resolve_session_identifier(
        session_token or websocket.headers.get(SESSION_HEADER),
        websocket.cookies.get(SESSION_COOKIE),
    )
    token = _session_id_ctx.set(session_id)
    try:
        entry = _ensure_session_entry(session_id)
        await broadcaster.connect(session_id, websocket)
        try:
            await websocket.send_json(
                {
                    "type": "state",
                    "session": session_id,
                    "state": entry.state.model_dump(),
                    "completed": entry.completed,
                    "timestamp": asyncio.get_running_loop().time(),
                }
            )
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await broadcaster.disconnect(session_id, websocket)
    finally:
        _session_id_ctx.reset(token)


def _state() -> PuzzleState:
    entry = _ensure_session_entry(_session_id())
    return entry.state


def _set_state(
    state: PuzzleState,
    *,
    completed: bool,
    session_id: str | None = None,
    update_default: bool = False,
) -> None:
    target_id = session_id or _session_id()
    stored_state = state.model_copy(deep=True)
    entry = SessionData(
        state=stored_state, completed=completed, updated_at=time.time()
    )
    with _session_store_lock:
        _session_store()[target_id] = entry
    if update_default:
        _set_default_state(stored_state, completed)


def _completed() -> bool:
    entry = _ensure_session_entry(_session_id())
    return entry.completed
