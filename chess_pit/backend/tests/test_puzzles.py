"""Puzzle endpoint tests."""

from __future__ import annotations

import pytest
import chess
from sqlmodel import Session

from chess_backend.models import DEFAULT_START_FEN, Puzzle, PuzzleAttempt, PuzzleDifficulty


async def _register_and_login(client, username: str, password: str) -> dict[str, str]:
    create_payload = {
        "username": username,
        "password": password,
    }
    response = await client.post("/users", json=create_payload)
    assert response.status_code == 201

    token_response = await client.post(
        "/auth/token",
        data={
            "username": username,
            "password": password,
            "grant_type": "password",
        },
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_puzzle_flow(client, engine):
    headers = await _register_and_login(client, "puzzle_player", "StrongPass123")

    with Session(engine) as session:
        puzzle = Puzzle(
            cool_id="training-knight-001",
            fen=DEFAULT_START_FEN,
            difficulty=PuzzleDifficulty.easy,
            source="test-suite",
            hint="Push the king pawn to open lines.",
            solution_moves=["e2e4"],
        )
        session.add(puzzle)
        session.commit()

    random_response = await client.get(
        "/puzzles/random",
        headers=headers,
        params={"difficulty": PuzzleDifficulty.easy.value},
    )
    assert random_response.status_code == 200
    random_payload = random_response.json()
    assert random_payload["cool_id"] == "training-knight-001"
    assert random_payload["current_points"] == 3
    assert random_payload["hint_available"] is True
    assert random_payload["side_to_move"] == "white"
    assert random_payload["remaining_moves"] == 1
    assert random_payload["correct_moves"] == ["e2e4"]

    attempt_id = random_payload["attempt_id"]
    cool_id = random_payload["cool_id"]

    hint_response = await client.post(
        f"/puzzles/{cool_id}/hint",
        headers=headers,
        json={"attempt_id": attempt_id},
    )
    assert hint_response.status_code == 200
    hint_payload = hint_response.json()
    assert hint_payload["current_points"] == 2
    assert "king pawn" in hint_payload["hint"].lower()
    assert hint_payload["move_uci"] == "e2e4"
    assert hint_payload["from_square"] == "e2"
    assert hint_payload["to_square"] == "e4"
    assert hint_payload["move_san"] == "e4"

    submit_response = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "e2e4"},
    )
    assert submit_response.status_code == 200
    submit_payload = submit_response.json()
    assert submit_payload["status"] == "solved"
    assert submit_payload["solved"] is True
    assert submit_payload["points_awarded"] == 2
    assert submit_payload["current_points"] == 2
    assert "e2e4" in submit_payload["correct_moves"]
    assert submit_payload["total_user_points"] >= 2
    assert (
        submit_payload["board_fen"] == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    )
    assert submit_payload["side_to_move"] == "black"
    assert submit_payload["submitted_moves"] == ["e2e4"]
    assert submit_payload["remaining_moves"] == 0

    repeat_hint = await client.post(
        f"/puzzles/{cool_id}/hint",
        headers=headers,
        json={"attempt_id": attempt_id},
    )
    assert repeat_hint.status_code == 409

    repeat_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "e2e4"},
    )
    assert repeat_submit.status_code == 409


@pytest.mark.asyncio
async def test_puzzle_wrong_move_fails_attempt(client, engine):
    headers = await _register_and_login(client, "puzzle_blunder", "StrongPass123")

    with Session(engine) as session:
        puzzle = Puzzle(
            cool_id="training-knight-002",
            fen=DEFAULT_START_FEN,
            difficulty=PuzzleDifficulty.easy,
            source="test-suite",
            hint=None,
            solution_moves=["e2e4"],
        )
        session.add(puzzle)
        session.commit()

    random_response = await client.get(
        "/puzzles/random",
        headers=headers,
        params={"difficulty": PuzzleDifficulty.easy.value},
    )
    assert random_response.status_code == 200
    attempt_id = random_response.json()["attempt_id"]
    cool_id = random_response.json()["cool_id"]

    submit_response = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "d2d4"},
    )
    assert submit_response.status_code == 200
    payload = submit_response.json()
    assert payload["status"] == "failed"
    assert payload["solved"] is False
    assert payload["points_awarded"] == 0
    assert payload["current_points"] == 0
    assert payload["board_fen"] == DEFAULT_START_FEN
    assert payload["side_to_move"] == "white"
    assert payload["submitted_moves"] == ["d2d4"]
    assert payload["remaining_moves"] == 0

    repeat_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "e2e4"},
    )
    assert repeat_submit.status_code == 409


@pytest.mark.asyncio
async def test_puzzle_multi_move_with_auto_reply(client, engine):
    headers = await _register_and_login(client, "tactics_master", "StrongPass123")

    with Session(engine) as session:
        puzzle = Puzzle(
            cool_id="combo-sequence-001",
            fen=DEFAULT_START_FEN,
            difficulty=PuzzleDifficulty.easy,
            source="test-suite",
            hint="Strike in the centre, then hunt the king.",
            solution_moves=["e2e4", "e7e5", "d1h5"],
        )
        session.add(puzzle)
        session.commit()

    random_response = await client.get(
        "/puzzles/random",
        headers=headers,
        params={"difficulty": PuzzleDifficulty.easy.value},
    )
    assert random_response.status_code == 200
    random_payload = random_response.json()
    assert random_payload["remaining_moves"] == 2

    attempt_id = random_payload["attempt_id"]
    cool_id = random_payload["cool_id"]

    first_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "e2e4"},
    )
    assert first_submit.status_code == 200
    first_payload = first_submit.json()
    assert first_payload["status"] == "in_progress"
    assert first_payload["remaining_moves"] == 1
    assert first_payload["opponent_move"] == "e7e5"
    assert first_payload["opponent_move_san"] == "e5"
    assert first_payload["side_to_move"] == "white"
    assert first_payload["correct_moves"] == ["e2e4", "e7e5", "d1h5"]

    expected_board = chess.Board()
    expected_board.push(chess.Move.from_uci("e2e4"))
    expected_board.push(chess.Move.from_uci("e7e5"))
    assert first_payload["board_fen"] == expected_board.fen()

    with Session(engine) as session:
        attempt = session.get(PuzzleAttempt, attempt_id)
        assert attempt is not None
        assert attempt.completed_at is None
        assert attempt.submitted_moves == ["e2e4", "e7e5"]

    final_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "d1h5"},
    )
    assert final_submit.status_code == 200
    final_payload = final_submit.json()
    assert final_payload["status"] == "solved"
    assert final_payload["solved"] is True
    assert final_payload["remaining_moves"] == 0
    assert final_payload["opponent_move"] is None
    assert final_payload["opponent_move_san"] is None
    assert final_payload["submitted_moves"] == ["e2e4", "e7e5", "d1h5"]
    assert final_payload["points_awarded"] == 3
    assert final_payload["correct_moves"] == ["e2e4", "e7e5", "d1h5"]

    repeat_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": attempt_id, "move": "f2f4"},
    )
    assert repeat_submit.status_code == 409


@pytest.mark.asyncio
async def test_puzzle_restart_creates_new_attempt(client, engine):
    headers = await _register_and_login(client, "puzzle_retry", "StrongPass123")

    board = chess.Board(DEFAULT_START_FEN)
    board.push_san("e4")
    black_to_move_fen = board.fen()

    with Session(engine) as session:
        puzzle = Puzzle(
            cool_id="retry-lesson-001",
            fen=black_to_move_fen,
            difficulty=PuzzleDifficulty.easy,
            source="test-suite",
            hint=None,
            solution_moves=["c7c5", "g2g3", "d7d6", "f1g2"],
        )
        session.add(puzzle)
        session.commit()

    random_response = await client.get(
        "/puzzles/random",
        headers=headers,
        params={"difficulty": PuzzleDifficulty.easy.value},
    )
    assert random_response.status_code == 200
    initial_payload = random_response.json()
    first_attempt_id = initial_payload["attempt_id"]
    cool_id = initial_payload["cool_id"]

    fail_response = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": first_attempt_id, "move": "a7a6"},
    )
    assert fail_response.status_code == 200
    assert fail_response.json()["status"] == "failed"

    restart_response = await client.post(
        f"/puzzles/{cool_id}/restart",
        headers=headers,
    )
    assert restart_response.status_code == 201
    restart_payload = restart_response.json()
    assert restart_payload["cool_id"] == cool_id
    assert restart_payload["remaining_moves"] == 2
    assert restart_payload["attempt_id"] != first_attempt_id

    retry_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": restart_payload["attempt_id"], "move": "c7c5"},
    )
    assert retry_submit.status_code == 200
    retry_payload = retry_submit.json()
    assert retry_payload["status"] == "in_progress"
    assert retry_payload["remaining_moves"] == 1
    assert retry_payload["submitted_moves"][:2] == ["c7c5", "g2g3"]

    final_submit = await client.post(
        f"/puzzles/{cool_id}/submit",
        headers=headers,
        json={"attempt_id": restart_payload["attempt_id"], "move": "d7d6"},
    )
    assert final_submit.status_code == 200
    assert final_submit.json()["status"] == "solved"
