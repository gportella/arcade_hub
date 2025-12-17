"""CRUD helpers for user resources."""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import User


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_user_by_engine_key(session: Session, engine_key: str) -> Optional[User]:
    statement = select(User).where(User.engine_key == engine_key)
    return session.exec(statement).first()


def create_user(session: Session, user: User) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_stats(
    session: Session,
    user: User,
    *,
    won: bool = False,
    lost: bool = False,
    draw: bool = False,
) -> None:
    if won:
        user.games_won += 1
    if lost:
        user.games_lost += 1
    if draw:
        user.games_drawn += 1
    user.games_played = user.games_won + user.games_lost + user.games_drawn
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
