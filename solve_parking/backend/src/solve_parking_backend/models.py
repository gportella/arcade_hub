"""Data models shared across the Solve Parking backend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Orientation(str, Enum):
    """Allowed vehicle orientations."""

    horizontal = "horizontal"
    vertical = "vertical"


class Vehicle(BaseModel):
    """Represents a vehicle occupying one-by-N tiles on the grid."""

    id: str = Field(min_length=1, max_length=3)
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    length: int = Field(ge=2, le=3)
    orientation: Orientation
    goal: bool = False

    def __hash__(self) -> int:
        return hash((self.id, self.row, self.col, self.length, self.orientation))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vehicle):
            return False
        return (self.id, self.row, self.col, self.length, self.orientation) == (
            other.id,
            other.row,
            other.col,
            other.length,
            other.orientation,
        )


class Exit(BaseModel):
    """Location of the board exit (the goal vehicle must reach this column)."""

    row: int = Field(ge=0)
    col: int = Field(ge=0)


class PuzzleState(BaseModel):
    """Snapshot of the whole puzzle grid."""

    size: int = Field(ge=2, le=12)
    exit: Exit
    vehicles: list[Vehicle]

    def __hash__(self) -> int:
        vehicle_positions = tuple(
            sorted(
                (veh.id, veh.row, veh.col, veh.orientation, veh.length)
                for veh in self.vehicles
            )
        )
        return hash((self.size, self.exit.row, self.exit.col, vehicle_positions))

    def __eq__(self, other) -> bool:
        if not isinstance(other, PuzzleState):
            return False
        return (
            self.size == other.size
            and self.exit.row == other.exit.row
            and self.exit.col == other.exit.col
            and tuple(
                sorted(
                    (v.id, v.orientation, v.length, v.row, v.col) for v in self.vehicles
                )
            )
            == tuple(
                sorted(
                    (v.id, v.orientation, v.length, v.row, v.col)
                    for v in other.vehicles
                )
            )
        )


class MoveRequest(BaseModel):
    """Incoming move operation for a given vehicle."""

    vehicle_id: str
    steps: int = Field(ne=0)


class MoveResponse(BaseModel):
    """Result of applying a move."""

    state: PuzzleState
    completed: bool


class SolveResponse(BaseModel):
    """Response payload for solving a puzzle."""

    state: PuzzleState
    completed: bool
    moves: int
    path: list[PuzzleState] | None = None
    elapsed_ms: float | None = None


class ErrorResponse(BaseModel):
    """Standard API error payload."""

    detail: str


class PuzzleSummary(BaseModel):
    """Compact representation of a stored puzzle configuration."""

    id: int
    name: str
    size: int
    exit: Exit
    vehicle_count: int
    active: bool
    created_at: datetime


class PuzzleConfigResponse(BaseModel):
    """Detailed representation of a stored puzzle configuration."""

    id: int
    name: str
    state: PuzzleState
    active: bool
    created_at: datetime


class DeleteConfigResponse(BaseModel):
    """Payload returned when removing a stored configuration."""

    removed_id: int
    removed_name: str
    active: bool
    activated_name: str | None = None
    state: PuzzleState | None = None
    completed: bool | None = None


class CreatePuzzleRequest(BaseModel):
    """Payload for creating a new puzzle configuration."""

    model_config = {"populate_by_name": True}

    name: str = Field(min_length=1, max_length=120)
    state: PuzzleState = Field(alias="state")
    activate: bool = True


class UpdatePuzzleRequest(BaseModel):
    """Payload for updating an existing puzzle configuration."""

    model_config = {"populate_by_name": True}

    state: PuzzleState = Field(alias="state")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    activate: bool | None = None
