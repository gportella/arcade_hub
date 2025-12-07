"""Pydantic schemas for request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import GameResult, GameStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    avatar_url: Optional[str] = Field(default=None, max_length=255)


class UserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    avatar_url: Optional[str] = Field(default=None, max_length=255)
    games_won: Optional[int] = Field(default=None, ge=0)
    games_lost: Optional[int] = Field(default=None, ge=0)
    games_drawn: Optional[int] = Field(default=None, ge=0)


class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    avatar_url: Optional[str]
    games_played: int
    games_won: int
    games_lost: int
    games_drawn: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GameCreate(BaseModel):
    white_player_id: int
    black_player_id: int
    initial_fen: Optional[str] = Field(default=None, max_length=100)


class GameRead(BaseModel):
    id: int
    white_player_id: int
    black_player_id: int
    status: GameStatus
    result: Optional[GameResult]
    started_at: datetime
    last_move_at: Optional[datetime]
    moves_count: int
    initial_fen: str
    pgn: str

    class Config:
        from_attributes = True


class MoveCreate(BaseModel):
    notation: str = Field(min_length=2, max_length=12)


class MoveRead(BaseModel):
    id: int
    game_id: int
    player_id: int
    move_number: int
    notation: str
    played_at: datetime

    class Config:
        from_attributes = True


class GameDetail(GameRead):
    moves: list[MoveRead] = Field(default_factory=list)


class GameFinishRequest(BaseModel):
    result: GameResult


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "chess-pit-backend"
