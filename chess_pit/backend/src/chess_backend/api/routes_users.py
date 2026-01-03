"""User endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from ..api.deps import get_current_user
from ..crud.users import create_user, get_user_by_username
from ..db import get_session
from ..models import Game, PuzzleAttempt, User
from ..schemas import LeaderboardEntry, UserCreate, UserRead, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    session: Annotated[Session, Depends(get_session)],
) -> UserRead:
    if get_user_by_username(session, user_in.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        username=user_in.username,
        avatar_url=user_in.avatar_url,
        hashed_password=hash_password(user_in.password),
    )
    user = create_user(session, user)
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[UserRead]:
    users = session.exec(select(User)).all()
    return [UserRead.model_validate(user) for user in users]


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def read_leaderboard(
    session: Annotated[Session, Depends(get_session)],
    limit: int = 10,
) -> list[LeaderboardEntry]:
    bounded_limit = max(1, min(limit, 50))
    stmt = (
        select(User)
        .where(User.is_engine.is_(False))
        .order_by(User.rating.desc())
        .limit(bounded_limit)
    )
    users = session.exec(stmt).all()
    if not users:
        return []

    user_ids = [user.id for user in users if user.id is not None]
    if not user_ids:
        return []

    activity: dict[int, dict[str, object]] = {
        user_id: {
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
            func.coalesce(Game.last_move_at, Game.started_at).label("activity"),
        ).where(or_(Game.white_player_id.in_(user_ids), Game.black_player_id.in_(user_ids)))
    ).all()

    for row in game_rows:
        activity_ts = row.activity
        for participant in (row.white_player_id, row.black_player_id):
            if participant in activity:
                current_last = activity[participant]["last_game_at"]
                if current_last is None or (activity_ts is not None and activity_ts > current_last):
                    activity[participant]["last_game_at"] = activity_ts

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
        if row.user_id not in activity:
            continue
        info = activity[row.user_id]
        attempted = int(row.attempted or 0)
        solved = int(row.solved or 0)
        info["puzzles_attempted"] = attempted
        info["puzzles_solved"] = solved
        info["last_puzzle_attempt_at"] = row.last_attempt

    leaderboard: list[LeaderboardEntry] = []
    for user in users:
        if user.id is None:
            continue
        games_played = int(user.games_played or 0)
        wins = int(user.games_won or 0)
        losses = int(user.games_lost or 0)
        draws = int(user.games_drawn or 0)
        win_rate = wins / games_played if games_played > 0 else 0.0
        info = activity.get(user.id, {})
        last_game_at = info.get("last_game_at") if info else None
        last_puzzle_attempt_at = info.get("last_puzzle_attempt_at") if info else None
        attempted_puzzles = int(info.get("puzzles_attempted", 0)) if info else 0
        solved_puzzles = int(info.get("puzzles_solved", 0)) if info else 0
        puzzles_failed = max(attempted_puzzles - solved_puzzles, 0)
        last_activity = last_game_at
        for candidate in (last_puzzle_attempt_at, user.updated_at):
            if candidate is not None and (last_activity is None or candidate > last_activity):
                last_activity = candidate
        leaderboard.append(
            LeaderboardEntry(
                id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
                rating=int(user.rating or 0),
                games_played=games_played,
                games_won=wins,
                games_lost=losses,
                games_drawn=draws,
                last_game_at=last_game_at,
                last_activity_at=last_activity,
                win_rate=win_rate,
                puzzles_attempted=attempted_puzzles,
                puzzles_solved=solved_puzzles,
                puzzles_failed=puzzles_failed,
                last_puzzle_attempt_at=last_puzzle_attempt_at,
            )
        )

    return leaderboard


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> UserRead:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> UserRead:
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    db_user = session.get(User, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_update.password:
        db_user.hashed_password = hash_password(user_update.password)
    if user_update.avatar_url is not None:
        db_user.avatar_url = user_update.avatar_url
    if current_user.is_admin:
        if user_update.games_won is not None:
            db_user.games_won = user_update.games_won
        if user_update.games_lost is not None:
            db_user.games_lost = user_update.games_lost
        if user_update.games_drawn is not None:
            db_user.games_drawn = user_update.games_drawn
        db_user.games_played = db_user.games_won + db_user.games_lost + db_user.games_drawn
    db_user.updated_at = datetime.utcnow()
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return UserRead.model_validate(db_user)
