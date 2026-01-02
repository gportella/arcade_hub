"""Administrative endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from ..api.deps import get_current_user
from ..db import get_session
from ..models import Game, GameStatus, PuzzleAttempt, User
from ..schemas import AdminUserMetrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserMetrics])
async def admin_list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[AdminUserMetrics]:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    users = session.exec(select(User)).all()
    if not users:
        return []

    user_ids = [user.id for user in users if user.id is not None]
    if not user_ids:
        return []

    metrics: dict[int, dict[str, object]] = {
        user_id: {
            "active_games": 0,
            "completed_games": 0,
            "aborted_games": 0,
            "last_game_at": None,
            "puzzles_attempted": 0,
            "puzzles_solved": 0,
            "last_puzzle_attempt_at": None,
        }
        for user_id in user_ids
    }

    game_rows = session.exec(
        select(
            Game.white_player_id,
            Game.black_player_id,
            Game.status,
            Game.started_at,
            Game.last_move_at,
            func.coalesce(Game.last_move_at, Game.started_at).label("activity"),
        ).where(or_(Game.white_player_id.in_(user_ids), Game.black_player_id.in_(user_ids)))
    ).all()

    for row in game_rows:
        activity_ts = row.activity or row.last_move_at or row.started_at
        participants = (row.white_player_id, row.black_player_id)
        for participant in participants:
            if participant not in metrics:
                continue
            data = metrics[participant]
            status_value = row.status
            if isinstance(status_value, str):
                try:
                    status_value = GameStatus(status_value)
                except ValueError:
                    status_value = None
            if status_value in (GameStatus.pending, GameStatus.active):
                data["active_games"] = int(data["active_games"]) + 1
            elif status_value == GameStatus.completed:
                data["completed_games"] = int(data["completed_games"]) + 1
            elif status_value == GameStatus.aborted:
                data["aborted_games"] = int(data["aborted_games"]) + 1
            if activity_ts:
                current_last = data["last_game_at"]
                if current_last is None or activity_ts > current_last:
                    data["last_game_at"] = activity_ts

    solved_case = case((PuzzleAttempt.solved.is_(True), 1), else_=0)
    attempt_rows = session.exec(
        select(
            PuzzleAttempt.user_id,
            func.count(PuzzleAttempt.id).label("attempted"),
            func.coalesce(func.sum(solved_case), 0).label("solved"),
            func.max(
                func.coalesce(PuzzleAttempt.completed_at, PuzzleAttempt.started_at)
            ).label("last_attempt"),
        )
        .where(PuzzleAttempt.user_id.in_(user_ids))
        .group_by(PuzzleAttempt.user_id)
    ).all()

    for row in attempt_rows:
        user_id = row.user_id
        if user_id not in metrics:
            continue
        data = metrics[user_id]
        attempted = int(row.attempted or 0)
        solved = int(row.solved or 0)
        data["puzzles_attempted"] = attempted
        data["puzzles_solved"] = solved
        data["last_puzzle_attempt_at"] = row.last_attempt

    response: list[AdminUserMetrics] = []
    for user in users:
        if user.id is None:
            continue
        data = metrics[user.id]
        attempted = int(data["puzzles_attempted"])
        solved = int(data["puzzles_solved"])
        puzzles_failed = max(attempted - solved, 0)
        last_game_at = data["last_game_at"]
        last_puzzle_attempt_at = data["last_puzzle_attempt_at"]
        last_activity = None
        for candidate in (last_game_at, last_puzzle_attempt_at, user.updated_at):
            if candidate is None:
                continue
            if last_activity is None or candidate > last_activity:
                last_activity = candidate
        response.append(
            AdminUserMetrics(
                id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
                is_admin=user.is_admin,
                is_engine=user.is_engine,
                engine_key=user.engine_key,
                rating=user.rating,
                games_played=user.games_played,
                games_won=user.games_won,
                games_lost=user.games_lost,
                games_drawn=user.games_drawn,
                active_games=int(data["active_games"]),
                completed_games=int(data["completed_games"]),
                aborted_games=int(data["aborted_games"]),
                last_game_at=last_game_at,
                puzzles_attempted=attempted,
                puzzles_solved=solved,
                puzzles_failed=puzzles_failed,
                last_puzzle_attempt_at=last_puzzle_attempt_at,
                last_activity_at=last_activity,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )

    response.sort(
        key=lambda entry: (entry.last_activity_at or entry.created_at),
        reverse=True,
    )
    return response
