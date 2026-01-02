#!/usr/bin/env python3
"""Import EPD puzzle files into the Chess Pit database."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import chess

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from chess_backend.crud.puzzles import get_puzzle_by_cool_id, slugify_cool_id  # noqa: E402
from chess_backend.db import init_db, session_context  # noqa: E402
from chess_backend.models import Puzzle, PuzzleDifficulty  # noqa: E402


def _infer_difficulty_from_rating(
    rating: int | None, default: PuzzleDifficulty
) -> PuzzleDifficulty:
    if rating is None or rating <= 0:
        return default
    if rating < 1400:
        return PuzzleDifficulty.easy
    if rating < 1700:
        return PuzzleDifficulty.medium
    if rating < 2000:
        return PuzzleDifficulty.hard
    return PuzzleDifficulty.expert


def _extract_hint(operations: dict[str, object]) -> str | None:
    for key in ("c0", "c1", "c2", "c3", "c4"):
        value = operations.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _iter_epd_lines(path: Path) -> Iterable[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            content = raw_line.strip()
            if not content or content.startswith("#"):
                continue
            board = chess.Board()
            try:
                operations = board.set_epd(content)
            except ValueError as exc:
                print(f"Skipping invalid EPD on {path} line {line_number}: {exc}", file=sys.stderr)
                continue

            best_moves = operations.get("bm") or []
            if not best_moves:
                print(
                    f"Skipping puzzle without best move on {path} line {line_number}",
                    file=sys.stderr,
                )
                continue

            solutions = [move.uci() for move in best_moves if isinstance(move, chess.Move)]
            if not solutions:
                continue

            puzzle_id = operations.get("id")
            if isinstance(puzzle_id, list) and puzzle_id:
                puzzle_id = puzzle_id[0]
            if isinstance(puzzle_id, chess.Move):
                puzzle_id = puzzle_id.uci()

            yield {
                "fen": board.fen(),
                "solutions": solutions,
                "tag": str(puzzle_id) if puzzle_id else None,
                "hint": _extract_hint(operations),
                "difficulty": None,
                "source": None,
            }


def _iter_csv_rows(
    path: Path,
    *,
    default_difficulty: PuzzleDifficulty,
    source_label: str,
) -> Iterable[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=1):
            fen = (row.get("FEN") or "").strip()
            moves_text = (row.get("Moves") or "").strip()
            if not fen or not moves_text:
                continue
            solution_moves = [token.lower() for token in moves_text.split() if token]
            if not solution_moves:
                continue
            puzzle_id = (row.get("PuzzleId") or "").strip() or None
            hint = (row.get("Hint") or "").strip() or None
            rating_value = row.get("Rating") or row.get("PuzzleRating")
            try:
                rating = int(rating_value) if rating_value is not None else None
            except ValueError:
                rating = None
            difficulty = _infer_difficulty_from_rating(rating, default_difficulty)
            source_value = (row.get("GameUrl") or row.get("Source") or "").strip()
            yield {
                "fen": fen,
                "solutions": solution_moves,
                "tag": puzzle_id,
                "hint": hint,
                "difficulty": difficulty,
                "source": source_value or source_label,
                "row": row_number,
            }


def import_puzzle_files(
    files: list[Path],
    *,
    default_difficulty: PuzzleDifficulty,
    source: str | None,
    limit: int | None,
    dry_run: bool,
    overwrite: bool,
) -> None:
    init_db()
    inserted = 0
    skipped = 0

    with session_context() as session:
        for file_path in files:
            resolved = file_path.expanduser().resolve()
            if not resolved.exists():
                print(f"File not found: {resolved}", file=sys.stderr)
                continue

            source_label = source or resolved.stem
            suffix = resolved.suffix.lower()
            if suffix == ".epd":
                iterator = _iter_epd_lines(resolved)
            elif suffix == ".csv":
                iterator = _iter_csv_rows(
                    resolved,
                    default_difficulty=default_difficulty,
                    source_label=source_label,
                )
            else:
                print(f"Skipping unsupported puzzle format: {resolved}", file=sys.stderr)
                continue

            for index, payload in enumerate(iterator, start=1):
                if limit is not None and inserted >= limit:
                    break

                tag = payload.get("tag") or f"{index:04d}"
                base_identifier = f"{source_label}-{tag}"
                desired_id = slugify_cool_id(base_identifier)

                existing = get_puzzle_by_cool_id(session, desired_id)
                if existing and not overwrite:
                    skipped += 1
                    continue

                hint = payload.get("hint")
                solutions = payload.get("solutions") or []
                fen = payload.get("fen")
                if not fen or not solutions:
                    continue

                puzzle_difficulty = payload.get("difficulty") or default_difficulty
                puzzle_source = payload.get("source") or source_label

                if dry_run:
                    action = "Update" if existing else "Create"
                    print(
                        f"{action}: {desired_id} | difficulty={puzzle_difficulty.value} | fen={fen} | moves={solutions}",
                    )
                    inserted += 1
                    continue

                if existing and overwrite:
                    existing.fen = fen
                    existing.difficulty = puzzle_difficulty
                    existing.source = puzzle_source
                    existing.hint = hint
                    existing.solution_moves = solutions
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                else:
                    puzzle = Puzzle(
                        cool_id=desired_id,
                        fen=fen,
                        difficulty=puzzle_difficulty,
                        source=puzzle_source,
                        hint=hint,
                        solution_moves=solutions,
                    )
                    session.add(puzzle)

                inserted += 1

            if limit is not None and inserted >= limit:
                break

    if dry_run:
        print(
            f"Dry run complete. Previewed {inserted} puzzles, skipped {skipped} existing records."
        )
    else:
        print(f"Imported {inserted} puzzles. Skipped {skipped} existing records.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import chess puzzles from EPD files.")
    parser.add_argument("files", nargs="+", type=Path, help="EPD files to import")
    parser.add_argument(
        "--difficulty",
        choices=[item.value for item in PuzzleDifficulty],
        required=True,
        help="Difficulty rating to assign to the imported puzzles",
    )
    parser.add_argument(
        "--source",
        help="Optional label describing the puzzle source (defaults to file stem)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of puzzles to process across all files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview puzzles without writing to the database",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Update existing puzzles when a matching identifier is found",
    )
    args = parser.parse_args()

    difficulty = PuzzleDifficulty(args.difficulty)
    files = [Path(entry) for entry in args.files]

    import_puzzle_files(
        files,
        default_difficulty=difficulty,
        source=args.source,
        limit=args.limit,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
