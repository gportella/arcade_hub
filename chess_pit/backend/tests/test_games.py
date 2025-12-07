"""Game endpoint tests."""

from __future__ import annotations

import pytest

from chess_backend.config import get_settings


async def _register_user(client, username: str) -> dict[str, object]:
    response = await client.post(
        "/users",
        json={
            "username": username,
            "password": "StrongPass123",
        },
    )
    assert response.status_code == 201
    return response.json()


async def _login(client, username: str, password: str) -> str:
    response = await client.post(
        "/auth/token",
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_game_and_record_moves(client):
    white = await _register_user(client, "white_player")
    black = await _register_user(client, "black_player")

    token = await _login(client, "white_player", "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/games",
        json={
            "white_player_id": white["id"],
            "black_player_id": black["id"],
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    game = create_response.json()
    assert game["status"] == "pending"
    assert game["initial_fen"].startswith("rnbqkbnr")
    assert game["pgn"] == ""

    move_response = await client.post(
        f"/games/{game['id']}/moves",
        json={"notation": "e4"},
        headers=headers,
    )
    assert move_response.status_code == 201
    move = move_response.json()
    assert move["move_number"] == 1

    detail_response = await client.get(f"/games/{game['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["moves_count"] == 1
    assert detail["moves"][0]["notation"] == "e4"
    assert detail["pgn"] == "1. e4"


@pytest.fixture()
def admin_env(monkeypatch):
    monkeypatch.setenv("CHESS_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CHESS_ADMIN_PASSWORD", "AdminPass123")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("CHESS_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("CHESS_ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_finishes_game_updates_stats(admin_env, client):
    white = await _register_user(client, "champion")
    black = await _register_user(client, "contender")

    admin_token = await _login(client, "admin", "AdminPass123")
    headers_user = {"Authorization": f"Bearer {await _login(client, 'champion', 'StrongPass123')}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    game_resp = await client.post(
        "/games",
        json={
            "white_player_id": white["id"],
            "black_player_id": black["id"],
        },
        headers=headers_user,
    )
    assert game_resp.status_code == 201
    game_id = game_resp.json()["id"]

    finish_resp = await client.post(
        f"/games/{game_id}/finish",
        json={"result": "white"},
        headers=headers_admin,
    )
    assert finish_resp.status_code == 200
    assert finish_resp.json()["status"] == "completed"
    assert finish_resp.json()["pgn"] == "1. e4 1-0"

    user_resp = await client.get(f"/users/{white['id']}", headers=headers_admin)
    assert user_resp.status_code == 200
    user_data = user_resp.json()
    assert user_data["games_won"] == 1
    assert user_data["games_played"] == 1

    loser_resp = await client.get(f"/users/{black['id']}", headers=headers_admin)
    assert loser_resp.status_code == 200
    loser_data = loser_resp.json()
    assert loser_data["games_lost"] == 1
    assert loser_data["games_played"] == 1
