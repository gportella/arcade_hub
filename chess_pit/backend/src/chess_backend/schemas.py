"""Pydantic schemas for request and response bodies."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .models import GameResult, GameStatus, PuzzleDifficulty


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
    is_engine: bool
    engine_key: Optional[str]
    avatar_url: Optional[str]
    games_played: int
    games_won: int
    games_lost: int
    games_drawn: int
    rating: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminUserMetrics(BaseModel):
    id: int
    username: str
    avatar_url: Optional[str]
    is_admin: bool
    is_engine: bool
    engine_key: Optional[str]
    rating: int
    games_played: int
    games_won: int
    games_lost: int
    games_drawn: int
    active_games: int
    completed_games: int
    aborted_games: int
    last_game_at: Optional[datetime]
    puzzles_attempted: int
    puzzles_solved: int
    puzzles_failed: int
    last_puzzle_attempt_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GameCreate(BaseModel):
    white_player_id: int
    black_player_id: int
    initial_fen: Optional[str] = Field(default=None, max_length=100)
    summary: Optional[str] = Field(default=None, max_length=255)
    engine_depth: Optional[int] = Field(default=None, ge=1, le=64)
    initial_time_seconds: Optional[int] = Field(default=None, ge=0, le=86400)
    increment_seconds: Optional[int] = Field(default=None, ge=0, le=600)


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
    current_fen: str
    current_position_hash: Optional[str]
    summary: str
    pgn: str
    engine_depth: Optional[int]
    time_control_initial_seconds: Optional[int]
    time_control_increment_seconds: Optional[int]
    white_time_remaining_seconds: Optional[int]
    black_time_remaining_seconds: Optional[int]
    turn_start_time: Optional[datetime]

    class Config:
        from_attributes = True


class MoveCreate(BaseModel):
    notation: str = Field(min_length=2, max_length=12)
    fen: Optional[str] = Field(default=None, max_length=100)


class MoveRead(BaseModel):
    id: int
    game_id: int
    player_id: int
    move_number: int
    notation: str
    played_at: datetime
    fen: Optional[str]
    position_hash: Optional[str]

    class Config:
        from_attributes = True


class GameDetail(GameRead):
    moves: list[MoveRead] = Field(default_factory=list)


class OpponentSummary(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: Optional[str]
    is_engine: bool = False
    engine_key: Optional[str] = None
    rating: Optional[int] = None


class HubGameSummary(BaseModel):
    id: int
    opponent: OpponentSummary
    status: GameStatus
    result: Optional[GameResult]
    summary: str
    initial_fen: str
    current_fen: str
    current_position_hash: Optional[str]
    moves_count: int
    started_at: datetime
    last_updated: datetime
    your_color: str
    turn: str
    pgn: str
    engine_depth: Optional[int]
    time_control_initial_seconds: Optional[int]
    time_control_increment_seconds: Optional[int]
    white_time_remaining_seconds: Optional[int]
    black_time_remaining_seconds: Optional[int]
    turn_start_time: Optional[datetime]
    time_control_initial_seconds: Optional[int]
    time_control_increment_seconds: Optional[int]
    white_time_remaining_seconds: Optional[int]
    black_time_remaining_seconds: Optional[int]
    turn_start_time: Optional[datetime]


class HubResponse(BaseModel):
    user: UserRead
    games: list[HubGameSummary]
    opponents: list[OpponentSummary]
    engines: list[EngineInfo]


class GameFinishRequest(BaseModel):
    result: GameResult


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "chess-pit-backend"


class EngineInfo(BaseModel):
    key: str
    name: str
    default_depth: Optional[int] = None
    max_depth: Optional[int] = None


class EngineMoveRequest(BaseModel):
    engine_key: Optional[str] = Field(default=None, min_length=1, max_length=50)
    depth: Optional[int] = Field(default=None, ge=1, le=64)


class EngineMoveResponse(BaseModel):
    engine: EngineInfo
    depth: int
    uci: str
    san: str
    fen: str


class GameAnalysisRequest(BaseModel):
    engine_key: Optional[str] = Field(default=None, min_length=1, max_length=50)
    depth: Optional[int] = Field(default=None, ge=1, le=64)


class GameAnalysisResponse(BaseModel):
    engine: EngineInfo
    depth: int
    evaluation_cp: Optional[int]
    mate_in: Optional[int]
    best_move_uci: Optional[str]
    best_move_san: Optional[str]
    line_uci: list[str]
    line_san: list[str]


class GameAnalysisSequenceRequest(BaseModel):
    engine_key: Optional[str] = Field(default=None, min_length=1, max_length=50)
    depth: Optional[int] = Field(default=None, ge=1, le=64)


class GameAnalysisStep(BaseModel):
    move_index: int = Field(ge=0)
    move_number: int = Field(ge=1)
    turn: Literal["white", "black"]
    played_san: str
    played_uci: Optional[str]
    evaluation_before_cp: Optional[int]
    evaluation_after_cp: Optional[int]
    mate_before: Optional[int]
    mate_after: Optional[int]
    best_move_uci: Optional[str]
    best_move_san: Optional[str]
    best_line_uci: list[str]
    best_line_san: list[str]
    fen_before: str
    fen_after: str


class GameAnalysisSequenceResponse(BaseModel):
    engine: EngineInfo
    depth: int
    steps: list[GameAnalysisStep]
    final_evaluation_cp: Optional[int]
    final_mate_in: Optional[int]


class PuzzleSessionResponse(BaseModel):
    attempt_id: int
    cool_id: str
    fen: str
    difficulty: PuzzleDifficulty
    hint_available: bool
    max_points: int = 3
    current_points: int
    times_presented: int
    times_solved: int
    side_to_move: Literal["white", "black"]
    remaining_moves: int = Field(ge=0, default=1)
    correct_moves: list[str] = Field(default_factory=list)


class PuzzleHintRequest(BaseModel):
    attempt_id: int


class PuzzleHintResponse(BaseModel):
    attempt_id: int
    cool_id: str
    hint: Optional[str] = None
    current_points: int
    move_uci: Optional[str] = None
    move_san: Optional[str] = None
    from_square: Optional[str] = None
    to_square: Optional[str] = None


class PuzzleSubmitRequest(BaseModel):
    attempt_id: int
    move: str = Field(min_length=2, max_length=12)


class PuzzleSubmitResponse(BaseModel):
    attempt_id: int
    cool_id: str
    status: Literal["in_progress", "solved", "failed"]
    solved: bool
    points_awarded: int
    current_points: int
    correct_moves: list[str]
    total_user_points: int
    board_fen: str
    side_to_move: Literal["white", "black"]
    submitted_moves: list[str]
    remaining_moves: int = Field(ge=0, default=0)
    opponent_move: Optional[str] = None
    opponent_move_san: Optional[str] = None
