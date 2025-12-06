"""Bitboard-backed data model for a Connect 4 board."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Sequence

BOARD_WIDTH = 7
BOARD_HEIGHT = 6
BOARD_STRIDE = BOARD_HEIGHT + 1

BOARD_CAPACITY = BOARD_WIDTH * BOARD_HEIGHT

Color = int
YELLOW: Color = 0
RED: Color = 1

COLOR_NAMES: Sequence[str] = ("yellow", "red")

COLUMN_BOTTOM_MASK = tuple(
    1 << (column * BOARD_STRIDE) for column in range(BOARD_WIDTH)
)
COLUMN_TOP_MASK = tuple(
    1 << (column * BOARD_STRIDE + BOARD_HEIGHT) for column in range(BOARD_WIDTH)
)
COLUMN_TOP_SLOT_MASK = tuple(
    1 << (column * BOARD_STRIDE + BOARD_HEIGHT - 1) for column in range(BOARD_WIDTH)
)
COLUMN_MASK = tuple(
    ((1 << BOARD_STRIDE) - 1) << (column * BOARD_STRIDE)
    for column in range(BOARD_WIDTH)
)


class IllegalMoveError(ValueError):
    """Raised when a move references an invalid column index."""


class ColumnFullError(RuntimeError):
    """Raised when a move attempts to play into a saturated column."""


def other_color(color: Color) -> Color:
    """Return the opposing color."""
    return RED if color == YELLOW else YELLOW


@dataclass(slots=True)
class MoveResult:
    """Lightweight container describing the result of a move."""

    column: int
    bit: int
    winner: Color | None
    draw: bool

    @property
    def is_win(self) -> bool:
        return self.winner is not None


@dataclass(slots=True)
class BitboardState:
    """Mutable bitboard state for a Connect 4 match."""

    to_play: Color = YELLOW
    _boards: list[int] = field(default_factory=lambda: [0, 0])
    mask: int = 0
    move_count: int = 0
    _last_result: MoveResult | None = None

    def board(self, color: Color) -> int:
        return self._boards[color]

    @property
    def last_result(self) -> MoveResult | None:
        return self._last_result

    def playable_columns(self) -> Iterator[int]:
        for column in range(BOARD_WIDTH):
            if not self.mask & COLUMN_TOP_SLOT_MASK[column]:
                yield column

    def is_column_playable(self, column: int) -> bool:
        self._validate_column(column)
        return not self.mask & COLUMN_TOP_SLOT_MASK[column]

    def drop(self, column: int) -> MoveResult:
        self._validate_column(column)
        if self.mask & COLUMN_TOP_SLOT_MASK[column]:
            raise ColumnFullError(f"Column {column} is full")

        move_bit = (self.mask + COLUMN_BOTTOM_MASK[column]) & COLUMN_MASK[column]
        if move_bit == 0 or move_bit & COLUMN_TOP_MASK[column]:
            raise ColumnFullError(f"Column {column} is full")

        current_board = self._boards[self.to_play] | move_bit
        self._boards[self.to_play] = current_board
        self.mask |= move_bit
        self.move_count += 1

        winner: Color | None = self.to_play if has_connect_four(current_board) else None
        draw = winner is None and self.move_count >= BOARD_CAPACITY

        result = MoveResult(column=column, bit=move_bit, winner=winner, draw=draw)
        self._last_result = result

        self.to_play = other_color(self.to_play)
        return result

    def undo_last_move(self) -> None:
        last = self._last_result
        if last is None:
            raise RuntimeError("No moves to undo")

        self.to_play = other_color(self.to_play)
        self._boards[self.to_play] &= ~last.bit
        self.mask &= ~last.bit
        self.move_count -= 1
        self._last_result = None

    def _validate_column(self, column: int) -> None:
        if not 0 <= column < BOARD_WIDTH:
            raise IllegalMoveError(
                f"Column must be in [0, {BOARD_WIDTH - 1}], got {column}"
            )

    def board_schetch(self) -> List[List[str]]:
        """Return a 2D list representation of the board for display purposes."""

        grid: List[List[str]] = [
            ["." for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)
        ]
        for column in range(BOARD_WIDTH):
            for row in range(BOARD_HEIGHT):
                bit = 1 << (column * BOARD_STRIDE + row)
                if self._boards[YELLOW] & bit:
                    grid[row][column] = "Y"
                elif self._boards[RED] & bit:
                    grid[row][column] = "R"
        return grid


def has_connect_four(bitboard: int) -> bool:
    """Return True when the supplied bitboard contains a four-in-a-row."""

    for shift in (1, BOARD_STRIDE, BOARD_STRIDE - 1, BOARD_STRIDE + 1):
        sequence = bitboard & (bitboard >> shift)
        if sequence & (sequence >> (2 * shift)):
            return True
    return False


__all__ = [
    "BitboardState",
    "BOARD_CAPACITY",
    "BOARD_HEIGHT",
    "BOARD_STRIDE",
    "BOARD_WIDTH",
    "COLUMN_MASK",
    "COLUMN_TOP_MASK",
    "COLUMN_TOP_SLOT_MASK",
    "ColumnFullError",
    "Color",
    "COLOR_NAMES",
    "IllegalMoveError",
    "MoveResult",
    "RED",
    "YELLOW",
    "has_connect_four",
    "other_color",
]
