"""User endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..api.deps import get_current_user
from ..crud.users import create_user, get_user_by_username
from ..db import get_session
from ..models import User
from ..schemas import UserCreate, UserRead, UserUpdate
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
