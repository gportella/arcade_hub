"""CRUD helpers for puzzle resources."""

from __future__ import annotations

import re
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from ..models import Puzzle, PuzzleAttempt, PuzzleDifficulty, User

_ADJECTIVES = [
    "amber",
    "brisk",
    "clever",
    "daring",
    "eager",
    "fierce",
    "glimmer",
    "heroic",
    "lively",
    "mystic",
    "nimble",
    "proud",
    "quartz",
    "royal",
    "swift",
    "vivid",
]

_NOUNS = [
    "bishop",
    "castle",
    "dragon",
    "falcon",
    "gambit",
    "knight",
    "lancer",
    "mirage",
    "phoenix",
    "queen",
    "rook",
    "sentinel",
    "tactician",
    "unicorn",
    "vanguard",
    "wizard",
]


def slugify_cool_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "puzzle"


def generate_cool_id(session: Session, *, seed: Optional[str] = None, attempts: int = 8) -> str:
    base_slug = slugify_cool_id(seed) if seed else None
    for attempt in range(attempts):
        if attempt == 0 and base_slug:
            candidate = base_slug
        else:
            adjective = secrets.choice(_ADJECTIVES)
            noun = secrets.choice(_NOUNS)
            suffix = secrets.randbelow(1000)
            candidate = f"{adjective}-{noun}-{suffix:03d}"
        exists = session.exec(select(Puzzle).where(Puzzle.cool_id == candidate)).first()
        if exists is None:
            return candidate
        base_slug = None
    raise RuntimeError("Unable to generate unique puzzle identifier")


def get_puzzle_by_cool_id(session: Session, cool_id: str) -> Optional[Puzzle]:
    statement = select(Puzzle).where(Puzzle.cool_id == cool_id)
    return session.exec(statement).first()


def get_random_puzzle(
    session: Session, difficulty: PuzzleDifficulty | None = None
) -> Optional[Puzzle]:
    length_expr = func.coalesce(func.json_array_length(Puzzle.solution_moves), 0)
    statement = select(Puzzle)
    if difficulty is not None:
        statement = statement.where(Puzzle.difficulty == difficulty)
    statement = statement.order_by(length_expr.desc(), func.random())
    statement = statement.where(length_expr >= 4)
    puzzle = session.exec(statement).first()
    if puzzle:
        return puzzle

    # Fallback to any puzzle if none meet the minimum length (e.g., sparse datasets).
    statement = select(Puzzle)
    if difficulty is not None:
        statement = statement.where(Puzzle.difficulty == difficulty)
    statement = statement.order_by(length_expr.desc(), func.random())
    return session.exec(statement).first()


def create_puzzle(session: Session, puzzle: Puzzle) -> Puzzle:
    if not puzzle.cool_id:
        puzzle.cool_id = generate_cool_id(session)
    session.add(puzzle)
    session.commit()
    session.refresh(puzzle)
    return puzzle


def create_attempt(session: Session, *, puzzle: Puzzle, user: User) -> PuzzleAttempt:
    puzzle.presented_count += 1
    puzzle.updated_at = datetime.utcnow()
    attempt = PuzzleAttempt(puzzle_id=puzzle.id, user_id=user.id)
    session.add(puzzle)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    session.refresh(puzzle)
    return attempt


def get_attempt_for_user(
    session: Session, attempt_id: int, user_id: int
) -> Optional[PuzzleAttempt]:
    statement = select(PuzzleAttempt).where(
        PuzzleAttempt.id == attempt_id,
        PuzzleAttempt.user_id == user_id,
    )
    return session.exec(statement).first()


def register_hint_usage(
    session: Session, *, attempt: PuzzleAttempt, puzzle: Puzzle
) -> PuzzleAttempt:
    attempt.hint_count += 1
    puzzle.hint_count += 1
    puzzle.updated_at = datetime.utcnow()
    session.add(attempt)
    session.add(puzzle)
    session.commit()
    session.refresh(attempt)
    session.refresh(puzzle)
    return attempt


def complete_attempt(
    session: Session,
    *,
    attempt: PuzzleAttempt,
    puzzle: Puzzle,
    solved: bool,
    submitted_moves: list[str],
    points_awarded: int,
) -> PuzzleAttempt:
    now = datetime.utcnow()
    attempt.completed_at = now
    attempt.solved = solved
    attempt.submitted_moves = submitted_moves
    attempt.points_awarded = points_awarded
    puzzle.updated_at = now
    if solved:
        puzzle.solve_count += 1
    else:
        puzzle.fail_count += 1
    session.add(attempt)
    session.add(puzzle)
    session.commit()
    session.refresh(attempt)
    session.refresh(puzzle)
    return attempt


def get_user_total_points(session: Session, user_id: int) -> int:
    statement = select(func.coalesce(func.sum(PuzzleAttempt.points_awarded), 0)).where(
        PuzzleAttempt.user_id == user_id
    )
    result = session.exec(statement).first()
    return int(result or 0)
