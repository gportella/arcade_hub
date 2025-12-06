"""High-level game loop helpers built on the bitboard data model."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional

from .datamodel import (
    RED,
    YELLOW,
    BitboardState,
    Color,
    COLOR_NAMES,
    ColumnFullError,
    MoveResult,
    other_color,
)
from .sessions import GameMode


logger = logging.getLogger(__name__)


class TurnRole(str, Enum):
    """Describes the participant responsible for the turn."""

    HUMAN = "human"
    AI = "ai"
    PLAYER_ONE = "player_one"
    PLAYER_TWO = "player_two"


@dataclass(slots=True)
class TurnOutcome:
    """Outcome for a single turn within a game loop."""

    player: Color
    result: MoveResult
    turn_index: int
    role: Optional[TurnRole]

    @property
    def player_name(self) -> str:
        return COLOR_NAMES[self.player]


class Connect4Game:
    """Minimal turn-based loop built on top of ``BitboardState``."""

    __slots__ = ("state", "mode", "turn_index", "human_color", "ai_color")

    def __init__(
        self,
        *,
        mode: GameMode = GameMode.MULTIPLAYER,
        human_color: Color = YELLOW,
        state: BitboardState | None = None,
    ) -> None:
        self.state = state or BitboardState()
        self.mode = mode
        self.turn_index = 0
        if self.mode is GameMode.SOLO:
            self.human_color = human_color
            self.ai_color = other_color(human_color)
        else:
            self.human_color = None
            self.ai_color = None

    def legal_columns(self) -> tuple[int, ...]:
        return tuple(self.state.playable_columns())

    def legal_columns_iter(self) -> Iterator[int]:
        return self.state.playable_columns()

    def play_turn(self, column: int) -> TurnOutcome:
        player = self.state.to_play
        logger.debug(
            "Turn %d: %s attempting column %d",
            self.turn_index + 1,
            COLOR_NAMES[player],
            column,
        )
        result = self.state.drop(column)
        self.turn_index += 1
        board_snapshot = _format_board(self.state)
        logger.debug(
            "Turn %d result: column=%d winner=%s draw=%s next=%s move_count=%d board=%s",
            self.turn_index,
            column,
            COLOR_NAMES[result.winner] if result.winner is not None else None,
            result.draw,
            COLOR_NAMES[self.state.to_play],
            self.state.move_count,
            board_snapshot,
        )
        return TurnOutcome(
            player=player,
            result=result,
            turn_index=self.turn_index,
            role=self._role_for_color(player),
        )

    def is_over(self) -> bool:
        last = self.state.last_result
        return bool(last and (last.winner is not None or last.draw))

    def winner(self) -> Color | None:
        last = self.state.last_result
        return last.winner if last else None

    def reset(self) -> None:
        self.state = BitboardState()
        self.turn_index = 0

    def _role_for_color(self, color: Color) -> Optional[TurnRole]:
        if self.mode is GameMode.MULTIPLAYER:
            if color == YELLOW:
                return TurnRole.PLAYER_ONE
            return TurnRole.PLAYER_TWO
        # Solo match
        if self.human_color == color:
            return TurnRole.HUMAN
        return TurnRole.AI


def minimax_move(state: BitboardState, depth: int) -> tuple[Optional[int], float]:
    """Evaluate the board state using a minimax algorithm with alpha/beta pruning to a given depth."""
    playable = tuple(state.playable_columns())
    logger.debug(
        "minimax_move entry: depth=%d to_play=%s playable=%s",
        depth,
        COLOR_NAMES[state.to_play],
        playable,
    )
    if not playable:
        logger.debug("minimax_move: board full -> draw")
        return None, 0.0

    maximizing = state.to_play == YELLOW
    best_score = float("-inf") if maximizing else float("inf")
    best_move: Optional[int] = None
    alpha = float("-inf")
    beta = float("inf")

    for column in playable:
        result = state.drop(column)
        score = _terminal_score(result)
        if score is None:
            if depth <= 1:
                score = 0.0
            else:
                score = _minimax_score(state, depth - 1, alpha, beta)
        logger.debug(
            "minimax_move: depth=%d column=%d result=(winner=%s draw=%s) score=%.3f",
            depth,
            column,
            COLOR_NAMES[result.winner] if result.winner is not None else None,
            result.draw,
            score,
        )
        state._last_result = result  # restore for undo
        state.undo_last_move()

        updated = False
        if maximizing:
            if score > best_score or best_move is None:
                best_score = score
                best_move = column
                updated = True
            alpha = max(alpha, best_score)
        else:
            if score < best_score or best_move is None:
                best_score = score
                best_move = column
                updated = True
            beta = min(beta, best_score)

        if updated:
            logger.debug(
                "minimax_move: new best column=%d score=%.3f alpha=%.3f beta=%.3f",
                best_move,
                best_score,
                alpha,
                beta,
            )

        if beta <= alpha:
            logger.debug(
                "minimax_move: prune at column=%d depth=%d alpha=%.3f beta=%.3f",
                column,
                depth,
                alpha,
                beta,
            )
            break

    logger.debug(
        "minimax_move: selected column=%s score=%.3f",
        best_move,
        best_score,
    )
    return best_move, best_score


def calculate_next_move(state: BitboardState, *, depth: int = 6) -> int:
    """Determine best move for the current player given the board state."""
    playable = tuple(state.playable_columns())
    if not playable:
        raise ColumnFullError("Board is full")

    if state.move_count == 0:
        logger.debug("calculate_next_move: opening move -> center column")
        return 3  # Always play center column if first move

    best_move, score = minimax_move(state, depth)
    logger.debug(
        "calculate_next_move: depth=%d best_move=%s score=%.3f playable=%s",
        depth,
        best_move,
        score,
        playable,
    )
    if best_move is not None:
        return best_move
    logger.debug(
        "calculate_next_move: fallback to first playable column=%d",
        playable[0],
    )
    return playable[0]  # Fallback to first available column


__all__ = ["Connect4Game", "TurnOutcome", "TurnRole"]


def _minimax_score(
    state: BitboardState, depth: int, alpha: float, beta: float
) -> float:
    playable = tuple(state.playable_columns())
    maximizing = state.to_play == YELLOW

    if not playable:
        logger.debug("_minimax_score: depth=%d no playable columns -> draw", depth)
        return 0.0
    if depth == 0:
        logger.debug(
            "_minimax_score: depth=0 heuristic fallback for player=%s",
            COLOR_NAMES[state.to_play],
        )
        return 0.0

    best_score = float("-inf") if maximizing else float("inf")

    for column in playable:
        result = state.drop(column)
        score = _terminal_score(result)
        if score is None:
            score = _minimax_score(state, depth - 1, alpha, beta)
        state._last_result = result  # restore for undo
        state.undo_last_move()

        if maximizing:
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
        else:
            best_score = min(best_score, score)
            beta = min(beta, best_score)

        logger.debug(
            "_minimax_score: depth=%d column=%d score=%.3f alpha=%.3f beta=%.3f",
            depth,
            column,
            score,
            alpha,
            beta,
        )

        if beta <= alpha:
            logger.debug(
                "_minimax_score: prune at depth=%d column=%d alpha=%.3f beta=%.3f",
                depth,
                column,
                alpha,
                beta,
            )
            break

    return best_score


def _terminal_score(result: MoveResult) -> float | None:
    if result.winner == YELLOW:
        return 1.0
    if result.winner == RED:
        return -1.0
    if result.draw:
        return 0.0
    return None


def _format_board(state: BitboardState) -> str:
    rows = ["".join(row) for row in state.board_schetch()]
    return "/".join(rows)
