"""Utilities for interacting with UCI-compatible chess engines."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import chess
import chess.engine

from ..config import EngineSpec

log = logging.getLogger(__name__)


class EngineProcessError(RuntimeError):
    """Raised when the underlying UCI engine fails to execute properly."""


class EngineMoveError(RuntimeError):
    """Raised when the engine cannot supply a legal move."""


@dataclass(slots=True)
class EngineMove:
    """Represents a move suggested by an engine."""

    uci: str
    san: str
    fen: str


def compute_best_move(
    spec: EngineSpec,
    board: chess.Board,
    *,
    depth: int,
) -> EngineMove:
    """Return the best move suggested by *spec* for *board* at a fixed depth."""

    try:
        with chess.engine.SimpleEngine.popen_uci(spec.binary) as engine:
            limit = chess.engine.Limit(depth=depth)
            result = engine.play(board, limit)
    except FileNotFoundError as exc:
        raise EngineProcessError(f"Engine binary '{spec.binary}' not found") from exc
    except chess.engine.EngineTerminatedError as exc:
        raise EngineProcessError("Engine terminated unexpectedly") from exc
    except chess.engine.EngineError as exc:
        raise EngineProcessError(str(exc)) from exc

    if result.move is None:
        raise EngineMoveError("Engine did not return a move")

    move = result.move
    san = board.san(move)
    board.push(move)
    fen = board.fen()

    log.debug("Engine '%s' produced move %s (SAN %s) at depth %s", spec.key, move.uci(), san, depth)
    return EngineMove(uci=move.uci(), san=san, fen=fen)
