"""Utilities for interacting with UCI-compatible chess engines."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

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


@dataclass(slots=True)
class EngineAnalysis:
    """Represents an engine evaluation for a given board state."""

    depth: int
    best_move_uci: Optional[str]
    best_move_san: Optional[str]
    evaluation_cp: Optional[int]
    mate_in: Optional[int]
    line_uci: List[str]
    line_san: List[str]


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


def compute_analysis(
    spec: EngineSpec,
    board: chess.Board,
    *,
    depth: int,
) -> EngineAnalysis:
    """Return a principal variation and evaluation for *board* at a fixed depth."""

    try:
        with chess.engine.SimpleEngine.popen_uci(spec.binary) as engine:
            limit = chess.engine.Limit(depth=depth)
            info = engine.analyse(board, limit, multipv=1)
    except FileNotFoundError as exc:
        raise EngineProcessError(f"Engine binary '{spec.binary}' not found") from exc
    except chess.engine.EngineTerminatedError as exc:
        raise EngineProcessError("Engine terminated unexpectedly") from exc
    except chess.engine.EngineError as exc:
        raise EngineProcessError(str(exc)) from exc

    # python-chess returns a list when multipv > 1 or some engines always emit arrays.
    if isinstance(info, list):
        info = info[0] if info else {}

    score = info.get("score")
    white_score = score.white() if score is not None else None
    evaluation_cp: Optional[int]
    mate_in: Optional[int]
    if white_score is None:
        evaluation_cp = None
        mate_in = None
    else:
        mate_in = white_score.mate()
        evaluation_cp = white_score.score()

    pv_moves = list(info.get("pv") or [])
    line_uci = [move.uci() for move in pv_moves]
    board_for_san = board.copy()
    line_san: list[str] = []
    for move in pv_moves:
        line_san.append(board_for_san.san(move))
        board_for_san.push(move)

    best_move = pv_moves[0] if pv_moves else None
    best_move_san = board.san(best_move) if best_move else None

    log.debug(
        "Engine '%s' analysis depth %s, score %s, mate %s, best %s",
        spec.key,
        depth,
        evaluation_cp,
        mate_in,
        best_move.uci() if best_move else None,
    )

    return EngineAnalysis(
        depth=depth,
        best_move_uci=best_move.uci() if best_move else None,
        best_move_san=best_move_san,
        evaluation_cp=evaluation_cp,
        mate_in=mate_in,
        line_uci=line_uci,
        line_san=line_san,
    )
