"""Persistence layer for storing puzzle configurations."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Iterable

from .models import Exit, PuzzleState


@dataclass(frozen=True)
class PuzzleRecord:
    """Aggregated data describing a stored puzzle configuration."""

    id: int
    name: str
    size: int
    exit_row: int
    exit_col: int
    vehicle_count: int
    active: bool
    created_at: datetime
    payload: dict[str, object] | None = None

    def to_state(self) -> PuzzleState:
        if self.payload is None:
            msg = "Puzzle payload is missing; fetch the record with payload."
            raise ValueError(msg)
        return PuzzleState.model_validate(self.payload)

    def to_summary(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "exit": Exit(row=self.exit_row, col=self.exit_col),
            "vehicle_count": self.vehicle_count,
            "active": self.active,
            "created_at": self.created_at,
        }


class PuzzleRepository:
    """SQLite-backed repository for puzzle configurations."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()
        self._initialize()

    def _initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS puzzles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    size INTEGER NOT NULL,
                    exit_row INTEGER NOT NULL,
                    exit_col INTEGER NOT NULL,
                    vehicle_count INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_puzzles_active
                ON puzzles (active)
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def list_puzzles(self) -> list[PuzzleRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, size, exit_row, exit_col, vehicle_count, active, created_at
                FROM puzzles
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [self._row_to_record_basic(row) for row in rows]

    def save_puzzle(
        self, name: str, state: PuzzleState, *, activate: bool = True
    ) -> PuzzleRecord:
        payload = state.model_dump(mode="json")
        created_at = datetime.now(tz=timezone.utc).isoformat()
        vehicle_count = len(state.vehicles)

        with self._lock, self._connect() as conn:
            if activate:
                conn.execute("UPDATE puzzles SET active = 0 WHERE active = 1")

            cursor = conn.execute(
                """
                INSERT INTO puzzles (name, size, exit_row, exit_col, vehicle_count, active, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    state.size,
                    state.exit.row,
                    state.exit.col,
                    vehicle_count,
                    1 if activate else 0,
                    json.dumps(payload, separators=(",", ":")),
                    created_at,
                ),
            )
            puzzle_id = cursor.lastrowid
            conn.commit()

        if puzzle_id is None:
            msg = "Failed to determine inserted puzzle id."
            raise RuntimeError(msg)

        return self.get_puzzle(int(puzzle_id))

    def get_puzzle(self, puzzle_id: int) -> PuzzleRecord:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, size, exit_row, exit_col, vehicle_count, active, payload, created_at
                FROM puzzles
                WHERE id = ?
                """,
                (puzzle_id,),
            ).fetchone()

        if row is None:
            msg = f"Puzzle with id {puzzle_id} not found."
            raise KeyError(msg)

        return self._row_to_record_full(row)

    def activate_puzzle(self, puzzle_id: int) -> PuzzleRecord:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM puzzles WHERE id = ?",
                (puzzle_id,),
            ).fetchone()
            if row is None:
                msg = f"Puzzle with id {puzzle_id} not found."
                raise KeyError(msg)

            conn.execute("UPDATE puzzles SET active = 0 WHERE active = 1")
            conn.execute("UPDATE puzzles SET active = 1 WHERE id = ?", (puzzle_id,))
            conn.commit()

        return self.get_puzzle(puzzle_id)

    def get_active_state(self) -> PuzzleState | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload
                FROM puzzles
                WHERE active = 1
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None

        payload = json.loads(row["payload"])
        return PuzzleState.model_validate(payload)

    def delete_puzzles(self, puzzle_ids: Iterable[int]) -> None:
        ids = list(puzzle_ids)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"DELETE FROM puzzles WHERE id IN ({placeholders})",
                ids,
            )
            conn.commit()

    def _row_to_record_basic(self, row: sqlite3.Row) -> PuzzleRecord:
        created_at = datetime.fromisoformat(row["created_at"])
        return PuzzleRecord(
            id=row["id"],
            name=row["name"],
            size=row["size"],
            exit_row=row["exit_row"],
            exit_col=row["exit_col"],
            vehicle_count=row["vehicle_count"],
            active=bool(row["active"]),
            created_at=created_at,
        )

    def _row_to_record_full(self, row: sqlite3.Row) -> PuzzleRecord:
        created_at = datetime.fromisoformat(row["created_at"])
        payload = json.loads(row["payload"])
        record = PuzzleRecord(
            id=row["id"],
            name=row["name"],
            size=row["size"],
            exit_row=row["exit_row"],
            exit_col=row["exit_col"],
            vehicle_count=row["vehicle_count"],
            active=bool(row["active"]),
            created_at=created_at,
            payload=payload,
        )
        return record

    def update_puzzle(
        self,
        puzzle_id: int,
        state: PuzzleState,
        *,
        name: str | None = None,
        activate: bool | None = None,
    ) -> PuzzleRecord:
        payload = state.model_dump(mode="json")
        vehicle_count = len(state.vehicles)

        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, active
                FROM puzzles
                WHERE id = ?
                """,
                (puzzle_id,),
            ).fetchone()

            if row is None:
                msg = f"Puzzle with id {puzzle_id} not found."
                raise KeyError(msg)

            next_name = name or row["name"]
            next_active = bool(row["active"])

            if activate is True:
                conn.execute("UPDATE puzzles SET active = 0 WHERE active = 1")
                next_active = True
            elif activate is False:
                next_active = False

            conn.execute(
                """
                UPDATE puzzles
                SET name = ?,
                    size = ?,
                    exit_row = ?,
                    exit_col = ?,
                    vehicle_count = ?,
                    active = ?,
                    payload = ?
                WHERE id = ?
                """,
                (
                    next_name,
                    state.size,
                    state.exit.row,
                    state.exit.col,
                    vehicle_count,
                    1 if next_active else 0,
                    json.dumps(payload, separators=(",", ":")),
                    puzzle_id,
                ),
            )
            conn.commit()

        return self.get_puzzle(puzzle_id)

    def ensure_default_puzzle(self, name: str, state: PuzzleState) -> None:
        payload = state.model_dump(mode="json")
        vehicle_count = len(state.vehicles)

        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM puzzles WHERE name = ?",
                (name,),
            ).fetchone()

            if existing is None:
                conn.execute("UPDATE puzzles SET active = 0 WHERE active = 1")
                created_at = datetime.now(tz=timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT INTO puzzles
                        (name, size, exit_row, exit_col, vehicle_count, active, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        name,
                        state.size,
                        state.exit.row,
                        state.exit.col,
                        vehicle_count,
                        json.dumps(payload, separators=(",", ":")),
                        created_at,
                    ),
                )
            else:
                conn.execute("UPDATE puzzles SET active = 0 WHERE active = 1")
                conn.execute(
                    """
                    UPDATE puzzles
                    SET size = ?,
                        exit_row = ?,
                        exit_col = ?,
                        vehicle_count = ?,
                        active = 1,
                        payload = ?
                    WHERE id = ?
                    """,
                    (
                        state.size,
                        state.exit.row,
                        state.exit.col,
                        vehicle_count,
                        json.dumps(payload, separators=(",", ":")),
                        existing["id"],
                    ),
                )
            conn.commit()
