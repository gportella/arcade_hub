"""API route declarations for the Connect 4 backend."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from .datamodel import COLOR_NAMES, ColumnFullError, IllegalMoveError
from .game import Connect4Game, TurnOutcome, calculate_next_move
from .sessions import (
    DEFAULT_DIFFICULTY,
    DifficultyLevel,
    GameMode,
    SessionAlreadyExistsError,
    SessionFullError,
    SessionModeConflictError,
    create_session,
    discard_session,
    get_session,
    snapshot_sessions,
)
from .sessions import GameSession, SessionRegistryEntry

logger = logging.getLogger(__name__)

ENGINE_PLAYER_ID = "__engine__"

router = APIRouter()


class CreateGameRequest(BaseModel):
    """Request body for registering a new game session."""

    mode: GameMode = GameMode.MULTIPLAYER
    difficulty: DifficultyLevel = Field(default=DEFAULT_DIFFICULTY)
    game_id: str | None = Field(
        default=None,
        alias="gameId",
        min_length=1,
        max_length=64,
    )

    model_config = ConfigDict(populate_by_name=True)


class CreateGameResponse(BaseModel):
    """Response body for newly registered sessions."""

    game_id: str
    mode: GameMode
    difficulty: DifficultyLevel
    ai_depth: int


class GameDetailsResponse(BaseModel):
    """Snapshot of a running session."""

    game_id: str
    mode: GameMode
    players: list[str]
    capacity: int
    difficulty: DifficultyLevel
    ai_depth: int


@router.get("/health", tags=["system"])
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/games",
    response_model=CreateGameResponse,
    status_code=201,
    tags=["games"],
)
async def register_game(payload: CreateGameRequest) -> CreateGameResponse:
    game_id = payload.game_id or uuid4().hex
    difficulty = (
        payload.difficulty if payload.mode is GameMode.SOLO else DEFAULT_DIFFICULTY
    )
    try:
        entry = await create_session(game_id, payload.mode, difficulty)
    except SessionAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CreateGameResponse(
        game_id=game_id,
        mode=entry.mode,
        difficulty=entry.difficulty,
        ai_depth=entry.ai_depth,
    )


@router.get("/games", response_model=list[GameDetailsResponse], tags=["games"])
async def list_games() -> list[GameDetailsResponse]:
    snapshot = await snapshot_sessions()

    response: list[GameDetailsResponse] = []
    for game_id, entry in snapshot:
        players = await entry.session.player_ids()
        response.append(
            GameDetailsResponse(
                game_id=game_id,
                mode=entry.mode,
                players=players,
                capacity=entry.session.capacity,
                difficulty=entry.difficulty,
                ai_depth=entry.ai_depth,
            )
        )
    return response


@router.get(
    "/games/{game_id}/board_state",
    # response_model=GameDetailsResponse,
    tags=["games"],
)
async def get_board_state(game_id: str) -> List[List[str]]:
    # GameDetailsResponse:
    try:
        entry = await get_session(game_id, create_if_missing=False)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Game {game_id!r} not found"
        ) from exc

    return entry.board_state.board_schetch()


@router.get(
    "/games/{game_id}",
    response_model=GameDetailsResponse,
    tags=["games"],
)
async def get_game(game_id: str) -> GameDetailsResponse:
    try:
        entry = await get_session(game_id, create_if_missing=False)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Game {game_id!r} not found"
        ) from exc

    players = await entry.session.player_ids()
    return GameDetailsResponse(
        game_id=game_id,
        mode=entry.mode,
        players=players,
        capacity=entry.session.capacity,
        difficulty=entry.difficulty,
        ai_depth=entry.ai_depth,
    )


@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket, game_id: str, player_id: str
) -> None:
    mode_param = websocket.query_params.get("mode")
    requested_mode: GameMode | None = None
    if mode_param:
        try:
            requested_mode = GameMode(mode_param)
        except ValueError:
            await websocket.close(code=1008, reason="Invalid game mode")
            return

    try:
        entry = await get_session(game_id, mode=requested_mode)
    except SessionModeConflictError as exc:
        await websocket.close(code=1008, reason=str(exc))
        return

    game = Connect4Game(mode=entry.mode, state=entry.board_state)
    session = entry.session
    try:
        player_color = await session.connect(player_id, websocket)
    except SessionFullError:
        await websocket.close(code=1008, reason="Session is full")
        return

    join_payload = {
        "type": "player_joined",
        "gameId": game_id,
        "playerId": player_id,
        "color": COLOR_NAMES[player_color],
    }
    await session.broadcast(join_payload, sender_id=player_id, include_sender=True)

    await session.send_to(
        player_id,
        {
            "type": "session_state",
            "gameId": game_id,
            "players": await session.player_ids(),
            "colors": {
                pid: COLOR_NAMES[color]
                for pid, color in (await session.players_with_colors()).items()
            },
            "currentTurn": COLOR_NAMES[game.state.to_play],
        },
    )

    try:
        while True:
            incoming = await websocket.receive_json()
            include_sender = entry.mode is GameMode.SOLO

            if "column" in incoming:
                enriched = await _handle_player_move(
                    game_id,
                    player_id,
                    incoming,
                    websocket,
                    game,
                    session,
                )
                if enriched is None:
                    continue
                payload = enriched
            else:
                payload = {**incoming, "gameId": game_id, "playerId": player_id}

            await session.broadcast(
                payload, sender_id=player_id, include_sender=include_sender
            )
            await _maybe_trigger_ai_turn(game_id, game, entry, session)
    except WebSocketDisconnect:
        logger.info("Player %s disconnected from %s", player_id, game_id)
    except Exception:  # pragma: no cover - defensive safeguard
        logger.exception(
            "Unexpected error in game %s for player %s", game_id, player_id
        )
        await websocket.close(code=1011)
    finally:
        await session.disconnect(player_id)
        leave_payload = {
            "type": "player_left",
            "gameId": game_id,
            "playerId": player_id,
        }
        await session.broadcast(
            leave_payload, sender_id=player_id, include_sender=False
        )
        await discard_session(game_id, session)


__all__ = ["router"]


async def _handle_player_move(
    game_id: str,
    player_id: str,
    message: Dict[str, Any],
    websocket: WebSocket,
    game: Connect4Game,
    session: GameSession,
) -> Dict[str, Any] | None:
    column = message.get("column")
    if not isinstance(column, int):
        await websocket.send_json(
            {
                "type": "error",
                "gameId": game_id,
                "playerId": player_id,
                "detail": "column must be provided as an integer",
            }
        )
        return None

    player_color = await session.color_for(player_id)
    if player_color is not None and player_color != game.state.to_play:
        await websocket.send_json(
            {
                "type": "error",
                "gameId": game_id,
                "playerId": player_id,
                "detail": "Not your turn",
            }
        )
        return None

    try:
        outcome = game.play_turn(column)
    except (IllegalMoveError, ColumnFullError) as exc:
        await websocket.send_json(
            {
                "type": "error",
                "gameId": game_id,
                "playerId": player_id,
                "detail": str(exc),
            }
        )
        return None

    extra = {
        key: value
        for key, value in message.items()
        if key not in {"column", "gameId", "playerId"}
    }
    message_type = extra.pop("type", "move")

    return _build_move_payload(
        game_id=game_id,
        player_id=player_id,
        message_type=message_type,
        outcome=outcome,
        extra=extra,
    )


async def _maybe_trigger_ai_turn(
    game_id: str,
    game: Connect4Game,
    entry: SessionRegistryEntry,
    session: GameSession,
) -> None:
    if entry.mode is not GameMode.SOLO:
        return
    if game.is_over():
        return
    if game.ai_color is None or game.state.to_play != game.ai_color:
        return

    playable = list(game.state.playable_columns())
    if not playable:
        return

    logger.debug(
        "AI evaluating turn: game=%s to_play=%s depth=%d playable=%s",
        game_id,
        COLOR_NAMES[game.state.to_play],
        entry.ai_depth,
        playable,
    )

    try:
        preferred = calculate_next_move(game.state, depth=entry.ai_depth)
    except ColumnFullError:
        preferred = None

    if preferred in playable:
        playable.remove(preferred)
        playable.insert(0, preferred)
    elif preferred is not None:
        logger.warning(
            "AI suggested non-playable column %s in game %s", preferred, game_id
        )
    else:
        logger.debug("AI move selection raised ColumnFullError; using fallback")

    outcome: TurnOutcome | None = None
    chosen_column: int | None = None
    for column in playable:
        try:
            outcome = game.play_turn(column)
        except ColumnFullError:
            logger.warning(
                "AI caught column %s as full in game %s; retrying", column, game_id
            )
            continue
        else:
            chosen_column = column
            logger.debug(
                "AI played column %d in game %s (winner=%s draw=%s)",
                column,
                game_id,
                COLOR_NAMES[outcome.result.winner]
                if outcome.result.winner is not None
                else None,
                outcome.result.draw,
            )
            break

    if outcome is None or chosen_column is None:
        return

    payload = _build_move_payload(
        game_id=game_id,
        player_id=ENGINE_PLAYER_ID,
        message_type="ai_move",
        outcome=outcome,
    )

    await session.broadcast(payload, sender_id=None, include_sender=True)


def _build_move_payload(
    *,
    game_id: str,
    player_id: str,
    message_type: str,
    outcome: "TurnOutcome",
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": message_type,
        "gameId": game_id,
        "playerId": player_id,
        "column": outcome.result.column,
        "color": outcome.player,
        "colorName": outcome.player_name,
        "turnIndex": outcome.turn_index,
        "bit": outcome.result.bit,
        "winner": outcome.result.winner,
        "draw": outcome.result.draw,
    }

    if outcome.result.winner is not None:
        payload["winnerName"] = COLOR_NAMES[outcome.result.winner]

    if extra:
        payload.update(extra)

    return payload
