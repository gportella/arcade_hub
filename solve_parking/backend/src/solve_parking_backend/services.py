"""Domain logic for the Solve Parking puzzle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import MoveRequest, Orientation, PuzzleState, Vehicle


class InvalidMoveError(ValueError):
    """Raised when a vehicle cannot be moved as requested."""


class InvalidPuzzleError(ValueError):
    """Raised when a puzzle layout fails validation."""


@dataclass
class MoveResult:
    """Immutable container for a move application."""

    state: PuzzleState
    completed: bool


def initial_state(hard: bool = False) -> PuzzleState:
    """Return the default puzzle layout (6x6 board)."""

    return PuzzleState(
        size=6,
        exit={"row": 2, "col": 5},
        vehicles=[
            Vehicle(id="C", row=0, col=0, length=3, orientation=Orientation.vertical),
            Vehicle(id="A", row=0, col=3, length=2, orientation=Orientation.vertical),
            Vehicle(id="B", row=0, col=4, length=3, orientation=Orientation.vertical),
            Vehicle(id="D", row=3, col=2, length=2, orientation=Orientation.horizontal),
            Vehicle(id="E", row=4, col=1, length=3, orientation=Orientation.horizontal),
            Vehicle(id="F", row=3, col=5, length=2, orientation=Orientation.vertical),
            Vehicle(id="G", row=5, col=0, length=2, orientation=Orientation.horizontal),
            Vehicle(id="H", row=5, col=2, length=2, orientation=Orientation.horizontal),
            Vehicle(
                id="X",
                row=2,
                col=1,
                length=2,
                orientation=Orientation.horizontal,
                goal=True,
            ),
        ],
    )




def generate_stop_positions(
    state: "PuzzleState", vehicle_id: str
) -> Iterable["PuzzleState"]:
    """
    Yield all legal 'stop' positions for the given vehicle: slide left/right or up/down
    until just before hitting a blocker/boundary. Does not yield intermediate non-stop steps.
    """
    # Build occupancy excluding the vehicle to move
    vehicles = {v.id: v.model_copy(deep=True) for v in state.vehicles}
    v = vehicles[vehicle_id]
    board = _board_from(state.vehicles, state.size, exclude_id=v.id)

    row, col = v.row, v.col
    size = state.size

    # Helper: clone state with vehicle at (row, col)
    def clone_with(rc_row: int, rc_col: int) -> "PuzzleState":
        v.row, v.col = rc_row, rc_col
        updated = [vehicles[x.id] if x.id == v.id else x for x in state.vehicles]
        return state.model_copy(update={"vehicles": updated}, deep=True)

    if v.orientation is Orientation.horizontal:
        # Slide left: stop when next cell left is blocked or boundary
        c = col
        while c > 0 and board[row][c - 1] is None:
            c -= 1
        if c != col:
            yield clone_with(row, c)
        # Slide right: stop when cell after the right end is blocked or boundary
        c = col
        while (c + v.length) < size and board[row][c + v.length] is None:
            c += 1
        if c != col:
            yield clone_with(row, c)
    else:
        # Slide up
        r = row
        while r > 0 and board[r - 1][col] is None:
            r -= 1
        if r != row:
            yield clone_with(r, col)
        # Slide down
        r = row
        while (r + v.length) < size and board[r + v.length][col] is None:
            r += 1
        if r != row:
            yield clone_with(r, col)


def generate_all_moves_stops(state: "PuzzleState") -> Iterable["MoveResult"]:
    """
    Expand children by stop positions for every vehicle. Uses your is_solved and MoveResult.
    """
    for v in state.vehicles:
        for new_state in generate_stop_positions(state, v.id):
            yield MoveResult(state=new_state, completed=is_solved(new_state))


def apply_move(state: PuzzleState, move: MoveRequest) -> MoveResult:
    """Attempt to move a vehicle and return the updated puzzle state."""

    vehicles = {vehicle.id: vehicle.model_copy(deep=True) for vehicle in state.vehicles}
    target = vehicles.get(move.vehicle_id)
    if target is None:
        raise InvalidMoveError(f"Vehicle '{move.vehicle_id}' does not exist.")

    step_count = abs(move.steps)
    direction = 1 if move.steps > 0 else -1

    board = _board_from(state.vehicles, state.size, exclude_id=target.id)

    row = target.row
    col = target.col

    for _ in range(step_count):
        if target.orientation is Orientation.horizontal:
            next_col = col + target.length if direction > 0 else col - 1
            _ensure_within_bounds(next_col, state.size, axis="col")
            if board[row][next_col] is not None:
                raise InvalidMoveError("Another vehicle blocks the path.")
            col += direction
        else:
            next_row = row + target.length if direction > 0 else row - 1
            _ensure_within_bounds(next_row, state.size, axis="row")
            if board[next_row][col] is not None:
                raise InvalidMoveError("Another vehicle blocks the path.")
            row += direction

    target.row = row
    target.col = col

    updated = [vehicles[v.id] if v.id == target.id else v for v in state.vehicles]
    new_state = state.model_copy(update={"vehicles": updated}, deep=True)

    return MoveResult(state=new_state, completed=is_solved(new_state))


def validate_state(state: PuzzleState) -> None:
    """Ensure the provided puzzle layout adheres to board rules."""

    if state.size < 2:
        raise InvalidPuzzleError("Board size must be at least 2.")

    if state.exit.row < 0 or state.exit.row >= state.size:
        raise InvalidPuzzleError("Exit row is outside the board bounds.")
    if state.exit.col < 0 or state.exit.col >= state.size:
        raise InvalidPuzzleError("Exit column is outside the board bounds.")
    if state.exit.col != state.size - 1:
        raise InvalidPuzzleError("Exit column must be on the right edge of the board.")

    board: list[list[str | None]] = [
        [None for _ in range(state.size)] for _ in range(state.size)
    ]
    goal_count = 0
    seen_ids: set[str] = set()

    for vehicle in state.vehicles:
        if vehicle.id in seen_ids:
            raise InvalidPuzzleError(
                f"Duplicate vehicle identifier '{vehicle.id}' is not allowed."
            )
        seen_ids.add(vehicle.id)

        if vehicle.orientation is Orientation.horizontal:
            if vehicle.col + vehicle.length > state.size:
                raise InvalidPuzzleError(
                    f"Vehicle {vehicle.id} extends beyond the board horizontally."
                )
        else:
            if vehicle.row + vehicle.length > state.size:
                raise InvalidPuzzleError(
                    f"Vehicle {vehicle.id} extends beyond the board vertically."
                )

        if vehicle.goal:
            goal_count += 1
            if vehicle.orientation is not Orientation.horizontal:
                raise InvalidPuzzleError("Goal vehicle must be horizontal.")

        for row, col in _cells(vehicle):
            if row >= state.size or col >= state.size:
                raise InvalidPuzzleError(
                    f"Vehicle {vehicle.id} occupies a cell outside the board."
                )
            if board[row][col] is not None:
                raise InvalidPuzzleError("Overlapping vehicles in puzzle state.")
            board[row][col] = vehicle.id

    if goal_count != 1:
        raise InvalidPuzzleError("Puzzle must contain exactly one goal vehicle.")


def _board_from(
    vehicles: Iterable[Vehicle], size: int, exclude_id: str | None = None
) -> list[list[str | None]]:
    """Build a board occupancy map that ignores the given vehicle id."""

    board: list[list[str | None]] = [[None for _ in range(size)] for _ in range(size)]
    for vehicle in vehicles:
        if vehicle.id == exclude_id:
            continue
        for row, col in _cells(vehicle):
            if board[row][col] is not None:
                raise ValueError("Overlapping vehicles in puzzle state.")
            board[row][col] = vehicle.id
    return board


def _cells(vehicle: Vehicle) -> list[tuple[int, int]]:
    """Return every grid coordinate occupied by the vehicle."""

    coords: list[tuple[int, int]] = []
    for offset in range(vehicle.length):
        if vehicle.orientation is Orientation.horizontal:
            coords.append((vehicle.row, vehicle.col + offset))
        else:
            coords.append((vehicle.row + offset, vehicle.col))
    return coords


def _ensure_within_bounds(value: int, size: int, *, axis: str) -> None:
    if value < 0 or value >= size:
        raise InvalidMoveError(
            f"Move would push vehicle beyond the board on the {axis} axis."
        )


def is_solved(state: PuzzleState) -> bool:
    """Check whether the goal vehicle has reached the exit."""

    for vehicle in state.vehicles:
        if not vehicle.goal:
            continue
        if vehicle.orientation is not Orientation.horizontal:
            return False
        tail_col = vehicle.col + vehicle.length - 1
        if vehicle.row == state.exit.row and tail_col == state.exit.col:
            return True
    return False
