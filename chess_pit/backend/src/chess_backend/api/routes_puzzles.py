"""Puzzle training endpoints."""

from __future__ import annotations

import csv
import random
from datetime import datetime
from pathlib import Path
from typing import Annotated

import chess
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from ..api.deps import get_current_user
from ..crud.puzzles import (
    complete_attempt,
    create_attempt,
    create_puzzle,
    get_attempt_for_user,
    get_puzzle_by_cool_id,
    get_random_puzzle,
    get_user_total_points,
    register_hint_usage,
)
from ..db import get_session
from ..models import Puzzle, PuzzleAttempt, PuzzleDifficulty, User
from ..schemas import (
    PuzzleHintRequest,
    PuzzleHintResponse,
    PuzzleSessionResponse,
    PuzzleSubmitRequest,
    PuzzleSubmitResponse,
)

router = APIRouter(prefix="/puzzles", tags=["puzzles"])

_MAX_POINTS = 3
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PUZZLE_CSV = _PROJECT_ROOT.parent / "puzzles" / "puzzles.csv"


def _ensure_puzzle(puzzle: Puzzle | None) -> Puzzle:
    if puzzle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puzzle not found")
    return puzzle


def _ensure_attempt(attempt: PuzzleAttempt | None) -> PuzzleAttempt:
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def _normalize_move(board: chess.Board, move_text: str) -> str | None:
    candidate = move_text.strip()
    if not candidate:
        return None
    try:
        move = board.parse_uci(candidate)
        return move.uci()
    except ValueError:
        try:
            move = board.parse_san(candidate)
            return move.uci()
        except ValueError:
            return None


def _remaining_player_moves(
    solution_moves: list[str], played_count: int, initial_turn_white: bool
) -> int:
    if played_count >= len(solution_moves):
        return 0

    remaining = 0
    for index in range(played_count, len(solution_moves)):
        is_player_turn = (index % 2 == 0) if initial_turn_white else (index % 2 == 1)
        if is_player_turn:
            remaining += 1
    return remaining


def _infer_difficulty_from_rating(rating: int) -> PuzzleDifficulty:
    if rating < 1400:
        return PuzzleDifficulty.easy
    if rating < 1700:
        return PuzzleDifficulty.medium
    if rating < 2000:
        return PuzzleDifficulty.hard
    return PuzzleDifficulty.expert


def _load_any_puzzle_from_csv(
    session: Session, requested: PuzzleDifficulty | None
) -> Puzzle | None:
    if not _PUZZLE_CSV.exists():
        return None

    with _PUZZLE_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        return None

    random.shuffle(rows)

    def _row_to_puzzle(entry: dict[str, str]) -> Puzzle | None:
        cool_id = (entry.get("PuzzleId") or "").strip() or None
        if cool_id:
            existing = get_puzzle_by_cool_id(session, cool_id)
            if existing:
                return existing

        fen = (entry.get("FEN") or "").strip()
        moves_text = (entry.get("Moves") or "").strip()
        if not fen or not moves_text:
            return None
        solution_moves = [token.lower() for token in moves_text.split() if token]
        if not solution_moves:
            return None

        try:
            rating = int(entry.get("Rating") or 0)
        except ValueError:
            rating = 0
        difficulty = _infer_difficulty_from_rating(rating)

        if requested and difficulty != requested:
            return None

        puzzle = Puzzle(
            cool_id=cool_id or entry.get("PuzzleId") or f"seeded-{random.randint(100000, 999999)}",
            fen=fen,
            difficulty=difficulty,
            source=entry.get("GameUrl") or "puzzles.csv",
            hint=None,
            solution_moves=solution_moves,
        )
        return create_puzzle(session, puzzle)

    # Try matching requested difficulty first.
    for row in rows:
        seeded = _row_to_puzzle(row)
        if seeded is not None:
            return seeded

    # Fallback to any difficulty if none matched.
    for row in rows:
        fen = (row.get("FEN") or "").strip()
        moves_text = (row.get("Moves") or "").strip()
        if not fen or not moves_text:
            continue
        existing = get_puzzle_by_cool_id(session, (row.get("PuzzleId") or "").strip())
        if existing:
            return existing
        solution_moves = [token.lower() for token in moves_text.split() if token]
        if not solution_moves:
            continue
        try:
            rating = int(row.get("Rating") or 0)
        except ValueError:
            rating = 0
        puzzle = Puzzle(
            cool_id=(row.get("PuzzleId") or "seeded" + str(random.randint(100000, 999999))).strip(),
            fen=fen,
            difficulty=_infer_difficulty_from_rating(rating),
            source=row.get("GameUrl") or "puzzles.csv",
            hint=None,
            solution_moves=solution_moves,
        )
        return create_puzzle(session, puzzle)

    return None


def _build_session_response(puzzle: Puzzle, attempt: PuzzleAttempt) -> PuzzleSessionResponse:
    board = chess.Board(puzzle.fen)
    initial_turn_white = board.turn == chess.WHITE
    solution_moves = [move.lower() for move in puzzle.solution_moves if move]
    remaining_moves = _remaining_player_moves(
        solution_moves,
        played_count=len(attempt.submitted_moves),
        initial_turn_white=initial_turn_white,
    )
    current_points = max(0, _MAX_POINTS - attempt.hint_count)
    return PuzzleSessionResponse(
        attempt_id=attempt.id,
        cool_id=puzzle.cool_id,
        fen=puzzle.fen,
        difficulty=puzzle.difficulty,
        hint_available=bool(solution_moves),
        max_points=_MAX_POINTS,
        current_points=current_points,
        times_presented=puzzle.presented_count,
        times_solved=puzzle.solve_count,
        side_to_move="white" if initial_turn_white else "black",
        remaining_moves=remaining_moves,
        correct_moves=solution_moves,
    )


@router.get("/random", response_model=PuzzleSessionResponse)
async def fetch_random_puzzle(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    difficulty: Annotated[PuzzleDifficulty | None, Query()] = None,
) -> PuzzleSessionResponse:
    puzzle = get_random_puzzle(session, difficulty)
    if puzzle is None:
        puzzle = _load_any_puzzle_from_csv(session, difficulty)
    puzzle = _ensure_puzzle(puzzle)

    attempt = create_attempt(session, puzzle=puzzle, user=current_user)
    return _build_session_response(puzzle, attempt)


@router.post("/{cool_id}/restart", response_model=PuzzleSessionResponse, status_code=status.HTTP_201_CREATED)
async def restart_puzzle_attempt(
    cool_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PuzzleSessionResponse:
    puzzle = _ensure_puzzle(get_puzzle_by_cool_id(session, cool_id))
    attempt = create_attempt(session, puzzle=puzzle, user=current_user)
    return _build_session_response(puzzle, attempt)


@router.post("/{cool_id}/hint", response_model=PuzzleHintResponse)
async def request_puzzle_hint(
    cool_id: str,
    payload: PuzzleHintRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PuzzleHintResponse:
    puzzle = _ensure_puzzle(get_puzzle_by_cool_id(session, cool_id))

    attempt = _ensure_attempt(get_attempt_for_user(session, payload.attempt_id, current_user.id))
    if attempt.puzzle_id != puzzle.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mismatched puzzle")
    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already completed"
        )
    if attempt.hint_count >= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hint already used")

    attempt = register_hint_usage(session, attempt=attempt, puzzle=puzzle)
    current_points = max(0, _MAX_POINTS - attempt.hint_count)

    move_uci: str | None = None
    move_san: str | None = None
    from_square: str | None = None
    to_square: str | None = None

    solution_moves = [move.lower() for move in puzzle.solution_moves if move]
    if solution_moves:
        board = chess.Board(puzzle.fen)
        for prior_move in attempt.submitted_moves:
            try:
                board.push(chess.Move.from_uci(prior_move))
            except ValueError:
                continue

        expected_index = len(attempt.submitted_moves)
        if expected_index < len(solution_moves):
            target_move_text = solution_moves[expected_index]
            try:
                target_move = chess.Move.from_uci(target_move_text)
            except ValueError:
                target_move = None
            if target_move is not None:
                move_uci = target_move.uci()
                from_square = move_uci[:2]
                to_square = move_uci[2:4]
                try:
                    move_san = board.san(target_move)
                except ValueError:
                    move_san = None

    return PuzzleHintResponse(
        attempt_id=attempt.id,
        cool_id=puzzle.cool_id,
        hint=puzzle.hint,
        current_points=current_points,
        move_uci=move_uci,
        move_san=move_san,
        from_square=from_square,
        to_square=to_square,
    )


@router.post("/{cool_id}/submit", response_model=PuzzleSubmitResponse)
async def submit_puzzle_solution(
    cool_id: str,
    payload: PuzzleSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PuzzleSubmitResponse:
    puzzle = _ensure_puzzle(get_puzzle_by_cool_id(session, cool_id))
    attempt = _ensure_attempt(get_attempt_for_user(session, payload.attempt_id, current_user.id))

    if attempt.puzzle_id != puzzle.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mismatched puzzle")
    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already completed"
        )
    if not puzzle.solution_moves:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Puzzle solution missing"
        )

    original_board = chess.Board(puzzle.fen)
    initial_turn_white = original_board.turn == chess.WHITE
    solution_moves = [move.lower() for move in puzzle.solution_moves if move]
    if not solution_moves:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Puzzle solution missing",
        )

    board = chess.Board(puzzle.fen)
    for prior_move in attempt.submitted_moves:
        try:
            board.push(chess.Move.from_uci(prior_move))
        except ValueError:
            continue

    expected_index = len(attempt.submitted_moves)
    if expected_index >= len(solution_moves):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already completed"
        )

    move_uci = _normalize_move(board, payload.move)
    if move_uci is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid move notation")

    normalized_move = move_uci.lower()
    expected_move = solution_moves[expected_index]

    submitted_moves = [*attempt.submitted_moves, move_uci]

    if normalized_move != expected_move:
        attempt = complete_attempt(
            session,
            attempt=attempt,
            puzzle=puzzle,
            solved=False,
            submitted_moves=submitted_moves,
            points_awarded=0,
        )
        total_points = get_user_total_points(session, current_user.id)
        starting_board = chess.Board(puzzle.fen)
        side_to_move = "white" if starting_board.turn == chess.WHITE else "black"
        return PuzzleSubmitResponse(
            attempt_id=attempt.id,
            cool_id=puzzle.cool_id,
            status="failed",
            solved=False,
            points_awarded=0,
            current_points=0,
            correct_moves=puzzle.solution_moves,
            total_user_points=total_points,
            board_fen=puzzle.fen,
            side_to_move=side_to_move,
            submitted_moves=submitted_moves,
            remaining_moves=0,
            opponent_move=None,
        )

    # Apply the player's move
    board.push(chess.Move.from_uci(move_uci))

    opponent_move: str | None = None
    opponent_move_san: str | None = None
    if len(submitted_moves) < len(solution_moves):
        auto_move_text = solution_moves[len(submitted_moves)]
        try:
            auto_move = chess.Move.from_uci(auto_move_text)
            if auto_move in board.legal_moves:
                opponent_move_san = board.san(auto_move)
                board.push(auto_move)
                submitted_moves.append(auto_move_text)
                opponent_move = auto_move_text
        except ValueError:
            opponent_move = None

    remaining_player_moves = _remaining_player_moves(
        solution_moves,
        played_count=len(submitted_moves),
        initial_turn_white=initial_turn_white,
    )

    side_to_move = "white" if board.turn == chess.WHITE else "black"

    if remaining_player_moves == 0:
        points = max(_MAX_POINTS - attempt.hint_count, 0)
        attempt = complete_attempt(
            session,
            attempt=attempt,
            puzzle=puzzle,
            solved=True,
            submitted_moves=submitted_moves,
            points_awarded=points,
        )
        total_points = get_user_total_points(session, current_user.id)
        current_points = max(0, _MAX_POINTS - attempt.hint_count)
        return PuzzleSubmitResponse(
            attempt_id=attempt.id,
            cool_id=puzzle.cool_id,
            status="solved",
            solved=True,
            points_awarded=points,
            current_points=current_points,
            correct_moves=puzzle.solution_moves,
            total_user_points=total_points,
            board_fen=board.fen(),
            side_to_move=side_to_move,
            submitted_moves=submitted_moves,
            remaining_moves=0,
            opponent_move=opponent_move,
            opponent_move_san=opponent_move_san,
        )

    # Persist in-progress attempt without completing it
    attempt.submitted_moves = submitted_moves
    session.add(attempt)
    puzzle.updated_at = datetime.utcnow()
    session.add(puzzle)
    session.commit()
    session.refresh(attempt)
    session.refresh(puzzle)

    total_points = get_user_total_points(session, current_user.id)
    current_points = max(0, _MAX_POINTS - attempt.hint_count)

    return PuzzleSubmitResponse(
        attempt_id=attempt.id,
        cool_id=puzzle.cool_id,
        status="in_progress",
        solved=False,
        points_awarded=0,
        current_points=current_points,
        correct_moves=puzzle.solution_moves,
        total_user_points=total_points,
        board_fen=board.fen(),
        side_to_move=side_to_move,
        submitted_moves=submitted_moves,
        remaining_moves=remaining_player_moves,
        opponent_move=opponent_move,
        opponent_move_san=opponent_move_san,
    )
