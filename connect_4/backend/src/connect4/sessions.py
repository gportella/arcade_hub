"""Session management utilities for the Connect 4 backend."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping

from fastapi import WebSocket

from src.connect4.datamodel import BitboardState, Color, YELLOW, other_color

logger = logging.getLogger(__name__)


class GameMode(str, Enum):
    """Supported game modes."""

    SOLO = "solo"
    MULTIPLAYER = "multiplayer"


class DifficultyLevel(str, Enum):
    """AI difficulty presets."""

    CASUAL = "casual"
    STANDARD = "standard"
    CHALLENGER = "challenger"
    EXPERT = "expert"


DIFFICULTY_DEPTH: Dict[DifficultyLevel, int] = {
    DifficultyLevel.CASUAL: 3,
    DifficultyLevel.STANDARD: 5,
    DifficultyLevel.CHALLENGER: 7,
    DifficultyLevel.EXPERT: 9,
}

DEFAULT_DIFFICULTY = DifficultyLevel.STANDARD


def _default_ai_depth() -> int:
    return DIFFICULTY_DEPTH[DEFAULT_DIFFICULTY]


_next_starting_color: Color = YELLOW


def _cycle_starting_color() -> Color:
    global _next_starting_color
    current = _next_starting_color
    _next_starting_color = other_color(current)
    return current


class SessionFullError(Exception):
    """Raised when attempting to join a full session."""


class SessionModeConflictError(Exception):
    """Raised when attempting to reuse a game identifier with another mode."""

    def __init__(self, game_id: str, actual: GameMode, requested: GameMode) -> None:
        message = (
            f"Game {game_id!r} already exists with mode {actual.value!r},"
            f" requested {requested.value!r}."
        )
        super().__init__(message)
        self.game_id = game_id
        self.actual = actual
        self.requested = requested


class SessionAlreadyExistsError(Exception):
    """Raised when attempting to explicitly create an already registered session."""

    def __init__(self, game_id: str) -> None:
        super().__init__(f"Game {game_id!r} already exists")
        self.game_id = game_id


@dataclass(slots=True)
class SessionRegistryEntry:
    """Stores metadata for active sessions."""

    mode: GameMode
    session: "GameSession"
    board_state: BitboardState
    difficulty: DifficultyLevel = DEFAULT_DIFFICULTY
    ai_depth: int = field(default_factory=_default_ai_depth)
    starting_color: Color = YELLOW


class GameSession:
    """In-memory session manager for a single Connect 4 match."""

    def __init__(
        self,
        mode: GameMode,
        *,
        capacity: int | None = None,
        starting_color: Color = YELLOW,
    ) -> None:
        self.mode = mode
        self._capacity = capacity or (1 if mode is GameMode.SOLO else 2)
        self._players: Dict[str, WebSocket] = {}
        self._player_colors: Dict[str, Color] = {}
        self._color_slots: Dict[Color, str | None] = {
            starting_color: None,
            other_color(starting_color): None,
        }
        self._lock = asyncio.Lock()

    @property
    def capacity(self) -> int:
        return self._capacity

    async def connect(self, player_id: str, websocket: WebSocket) -> Color:
        close_previous: WebSocket | None = None
        assigned_color: Color | None = None
        async with self._lock:
            existing = self._players.get(player_id)
            if existing is None and len(self._players) >= self._capacity:
                raise SessionFullError()
            if existing is not None and existing is not websocket:
                close_previous = existing
            if player_id in self._player_colors:
                assigned_color = self._player_colors[player_id]
            else:
                for color, occupant in self._color_slots.items():
                    if occupant is None:
                        self._color_slots[color] = player_id
                        assigned_color = color
                        break
                if assigned_color is None:
                    raise SessionFullError()
                self._player_colors[player_id] = assigned_color
            self._players[player_id] = websocket
            logger.debug("Player %s joined session", player_id)

        if close_previous is not None:
            await close_previous.close(code=1012)

        await websocket.accept()
        return assigned_color if assigned_color is not None else YELLOW

    async def disconnect(self, player_id: str) -> None:
        async with self._lock:
            if player_id in self._players:
                self._players.pop(player_id)
                logger.debug("Player %s left session", player_id)
            if player_id in self._player_colors:
                color = self._player_colors.pop(player_id)
                if self._color_slots.get(color) == player_id:
                    self._color_slots[color] = None

    async def send_to(self, player_id: str, message: Mapping[str, Any]) -> None:
        async with self._lock:
            websocket = self._players.get(player_id)

        if websocket is None:
            return

        await websocket.send_json(dict(message))

    async def broadcast(
        self,
        message: Mapping[str, Any],
        *,
        sender_id: str | None = None,
        include_sender: bool = False,
    ) -> None:
        async with self._lock:
            recipients = [
                websocket
                for pid, websocket in self._players.items()
                if include_sender or pid != sender_id
            ]
        if not recipients:
            return

        payload = dict(message)
        coros = tuple(recipient.send_json(payload) for recipient in recipients)
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning("WebSocket broadcast error: %s", result)

    async def is_empty(self) -> bool:
        async with self._lock:
            return not self._players

    async def player_ids(self) -> list[str]:
        async with self._lock:
            return list(self._players.keys())

    async def color_for(self, player_id: str) -> Color | None:
        async with self._lock:
            return self._player_colors.get(player_id)

    async def players_with_colors(self) -> Dict[str, Color]:
        async with self._lock:
            return dict(self._player_colors)


sessions: Dict[str, SessionRegistryEntry] = {}
sessions_lock = asyncio.Lock()


async def create_session(
    game_id: str,
    mode: GameMode,
    difficulty: DifficultyLevel | None = None,
) -> SessionRegistryEntry:
    async with sessions_lock:
        if game_id in sessions:
            raise SessionAlreadyExistsError(game_id)
        chosen_difficulty = difficulty or DEFAULT_DIFFICULTY
        starting_color = (
            _cycle_starting_color() if mode is GameMode.MULTIPLAYER else YELLOW
        )
        board_state = BitboardState(to_play=starting_color)
        entry = SessionRegistryEntry(
            mode=mode,
            session=GameSession(mode, starting_color=starting_color),
            board_state=board_state,
            difficulty=chosen_difficulty,
            ai_depth=DIFFICULTY_DEPTH[chosen_difficulty],
            starting_color=starting_color,
        )
        sessions[game_id] = entry
        return entry


async def get_session(
    game_id: str,
    *,
    mode: GameMode | None = None,
    difficulty: DifficultyLevel | None = None,
    create_if_missing: bool = True,
) -> SessionRegistryEntry:
    async with sessions_lock:
        entry = sessions.get(game_id)
        if entry is None:
            if not create_if_missing:
                raise KeyError(game_id)
            new_mode = mode or GameMode.MULTIPLAYER
            chosen_difficulty = difficulty or DEFAULT_DIFFICULTY
            starting_color = (
                _cycle_starting_color() if new_mode is GameMode.MULTIPLAYER else YELLOW
            )
            board_state = BitboardState(to_play=starting_color)
            entry = SessionRegistryEntry(
                mode=new_mode,
                session=GameSession(new_mode, starting_color=starting_color),
                board_state=board_state,
                difficulty=chosen_difficulty,
                ai_depth=DIFFICULTY_DEPTH[chosen_difficulty],
                starting_color=starting_color,
            )
            sessions[game_id] = entry
        elif mode is not None and entry.mode is not mode:
            raise SessionModeConflictError(game_id, entry.mode, mode)
        elif (
            difficulty is not None
            and entry.mode is GameMode.SOLO
            and entry.difficulty is not difficulty
        ):
            logger.debug(
                "Requested difficulty %s does not match session difficulty %s for game %s",
                difficulty,
                entry.difficulty,
                game_id,
            )
        return entry


async def discard_session(game_id: str, session: GameSession) -> None:
    async with sessions_lock:
        entry = sessions.get(game_id)
        if entry and entry.session is session and await session.is_empty():
            sessions.pop(game_id)
            logger.debug("Removed empty session for game %s", game_id)


async def snapshot_sessions() -> list[tuple[str, SessionRegistryEntry]]:
    async with sessions_lock:
        return list(sessions.items())


__all__ = [
    "GameMode",
    "DifficultyLevel",
    "GameSession",
    "SessionAlreadyExistsError",
    "SessionFullError",
    "SessionModeConflictError",
    "SessionRegistryEntry",
    "DIFFICULTY_DEPTH",
    "DEFAULT_DIFFICULTY",
    "create_session",
    "discard_session",
    "get_session",
    "snapshot_sessions",
]
