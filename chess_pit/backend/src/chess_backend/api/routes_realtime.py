"""Websocket endpoints for live game updates."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..realtime import get_manager

router = APIRouter()
_manager = get_manager()


@router.websocket("/ws/games/{game_id}")
async def subscribe_game(websocket: WebSocket, game_id: int) -> None:
    await _manager.connect(game_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        _manager.disconnect(game_id, websocket)
    except Exception:
        _manager.disconnect(game_id, websocket)
        raise
