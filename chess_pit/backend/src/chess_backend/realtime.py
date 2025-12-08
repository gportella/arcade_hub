"""Websocket connection management for real-time game updates."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, DefaultDict, Dict, Iterable, Set

from fastapi import WebSocket

from .models import Game, Move


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class GameConnectionManager:
    """Manage websocket connections keyed by game identifier."""

    def __init__(self) -> None:
        self._connections: DefaultDict[int, Set[WebSocket]] = defaultdict(set)

    async def connect(self, game_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[game_id].add(websocket)

    def disconnect(self, game_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(game_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(game_id, None)

    async def broadcast(self, game_id: int, payload: Dict[str, Any]) -> None:
        connections = list(self._connections.get(game_id, ()))
        if not connections:
            return
        message = json.dumps(payload, default=_json_default)
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:  # pragma: no cover - connection errors are best-effort
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(game_id, websocket)

    def active_connections(self, game_id: int) -> Iterable[WebSocket]:
        return tuple(self._connections.get(game_id, ()))


_manager = GameConnectionManager()


def get_manager() -> GameConnectionManager:
    return _manager


async def broadcast_move(game: Game, move: Move) -> None:
    if game.id is None:
        return
    payload = {
        "type": "move",
        "game_id": game.id,
        "move_number": move.move_number,
        "notation": move.notation,
        "player_id": move.player_id,
        "fen": move.fen,
        "position_hash": move.position_hash,
        "played_at": move.played_at,
    }
    await _manager.broadcast(game.id, payload)


async def broadcast_game_finished(game: Game) -> None:
    if game.id is None:
        return
    payload = {
        "type": "game_finished",
        "game_id": game.id,
        "result": game.result,
        "pgn": game.pgn,
        "completed_at": game.last_move_at,
    }
    await _manager.broadcast(game.id, payload)
