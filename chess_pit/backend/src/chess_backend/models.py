"""SQLModel declarative models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
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
    is_engine: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="0"),
    )
    engine_key: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), unique=True, nullable=True),
    )
    games_played: int = Field(default=0, ge=0)
    games_won: int = Field(default=0, ge=0)
    games_lost: int = Field(default=0, ge=0)
    games_drawn: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    white_games: list["Game"] = Relationship(
        sa_relationship=relationship(
            "Game",
            back_populates="white_player",
            lazy="selectin",
            foreign_keys="Game.white_player_id",
        )
    )
    black_games: list["Game"] = Relationship(
        sa_relationship=relationship(
            "Game",
            back_populates="black_player",
            lazy="selectin",
            foreign_keys="Game.black_player_id",
        )
    )
    moves: list["Move"] = Relationship(
        sa_relationship=relationship(
            "Move",
            back_populates="player",
            lazy="selectin",
        )
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
        sa_relationship=relationship(
            "User",
            back_populates="white_games",
            lazy="joined",
            foreign_keys="Game.white_player_id",
        )
    )
    black_player: "User" = Relationship(
        sa_relationship=relationship(
            "User",
            back_populates="black_games",
            lazy="joined",
            foreign_keys="Game.black_player_id",
        )
    )
    moves: list["Move"] = Relationship(
        sa_relationship=relationship(
            "Move",
            back_populates="game",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
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

    game: "Game" = Relationship(
        sa_relationship=relationship(
            "Game",
            back_populates="moves",
        )
    )
    player: "User" = Relationship(
        sa_relationship=relationship(
            "User",
            back_populates="moves",
        )
    )
