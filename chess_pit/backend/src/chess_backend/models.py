"""SQLModel declarative models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

DEFAULT_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class GameStatus(str, Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    aborted = "aborted"


class GameResult(str, Enum):
    white = "white"
    black = "black"
    draw = "draw"


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, max_length=50)
    avatar_url: Optional[str] = Field(default=None, max_length=255)


class User(UserBase, table=True):  # type: ignore[call-arg]
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    games_played: int = Field(default=0, ge=0)
    games_won: int = Field(default=0, ge=0)
    games_lost: int = Field(default=0, ge=0)
    games_drawn: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    white_games: list["Game"] = Relationship(  # type: ignore[name-defined]
        back_populates="white_player",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    black_games: list["Game"] = Relationship(  # type: ignore[name-defined]
        back_populates="black_player",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    moves: list["Move"] = Relationship(  # type: ignore[name-defined]
        back_populates="player",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Game(SQLModel, table=True):  # type: ignore[call-arg]
    id: Optional[int] = Field(default=None, primary_key=True)
    white_player_id: int = Field(foreign_key="user.id")
    black_player_id: int = Field(foreign_key="user.id")
    status: GameStatus = Field(default=GameStatus.pending, index=True)
    result: Optional[GameResult] = Field(default=None)
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_move_at: Optional[datetime] = Field(default=None, index=True)
    moves_count: int = Field(default=0, ge=0)
    initial_fen: str = Field(default=DEFAULT_START_FEN, max_length=100)
    current_fen: str = Field(default=DEFAULT_START_FEN, max_length=100)
    current_position_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    summary: str = Field(default="Friendly challenge", max_length=255)
    pgn: str = Field(
        default="",
        sa_column=Column(Text, nullable=False),
    )

    white_player: "User" = Relationship(
        back_populates="white_games",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    black_player: "User" = Relationship(
        back_populates="black_games",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    moves: list["Move"] = Relationship(
        back_populates="game",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class Move(SQLModel, table=True):  # type: ignore[call-arg]
    __table_args__ = (UniqueConstraint("game_id", "move_number"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id", index=True)
    player_id: int = Field(foreign_key="user.id")
    move_number: int = Field(ge=1)
    notation: str = Field(max_length=12)
    played_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    fen: Optional[str] = Field(default=None, max_length=100)
    position_hash: Optional[str] = Field(default=None, max_length=64, index=True)

    game: "Game" = Relationship(back_populates="moves")
    player: "User" = Relationship(back_populates="moves")
