"""API contract tests for the Connect 4 backend."""

from __future__ import annotations

from fastapi.testclient import TestClient

from connect4.app import app

client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/health")
    parsed = response.json()

    assert response.status_code == 200
    assert parsed == {"status": "ok"}


def test_create_game_defaults_to_multiplayer() -> None:
    response = client.post("/games", json={})

    assert response.status_code == 201
    payload = response.json()
    assert payload["mode"] == "multiplayer"
    assert payload["game_id"]
    assert payload["difficulty"] == "standard"
    assert payload["ai_depth"] == 5


def test_create_game_respects_requested_id() -> None:
    response = client.post(
        "/games",
        json={"gameId": "match-1", "mode": "solo"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload == {
        "game_id": "match-1",
        "mode": "solo",
        "difficulty": "standard",
        "ai_depth": 5,
    }


def test_create_game_accepts_custom_difficulty() -> None:
    response = client.post(
        "/games",
        json={"gameId": "depth-test", "mode": "solo", "difficulty": "expert"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload == {
        "game_id": "depth-test",
        "mode": "solo",
        "difficulty": "expert",
        "ai_depth": 9,
    }


def test_duplicate_game_id_returns_conflict() -> None:
    first = client.post(
        "/games",
        json={"gameId": "duplicate", "mode": "multiplayer"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/games",
        json={"gameId": "duplicate", "mode": "solo"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"].startswith("Game 'duplicate' already exists")


def test_list_games_contains_created_session() -> None:
    client.post("/games", json={"gameId": "list-me", "mode": "solo"})

    response = client.get("/games")
    assert response.status_code == 200

    sessions = response.json()
    assert any(
        session["game_id"] == "list-me"
        and session["difficulty"] == "standard"
        and session["ai_depth"] == 5
        for session in sessions
    )


def test_get_missing_game_returns_404() -> None:
    response = client.get("/games/non-existent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game 'non-existent' not found"
