"""Tests for engine integration endpoints."""

from __future__ import annotations

import pytest


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
async def test_list_engines(client):
    user = await _register_user(client, "engine_viewer")
    token = await _login(client, user["username"], "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/engines", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["key"] == "mock"


@pytest.mark.asyncio
async def test_engine_move_succeeds(client):
    white = await _register_user(client, "white_engine")
    black = await _register_user(client, "black_engine")

    token = await _login(client, "white_engine", "StrongPass123")
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

    engine_response = await client.post(
        f"/games/{game['id']}/engine-move",
        json={"engine_key": "mock", "depth": 4},
        headers=headers,
    )
    assert engine_response.status_code == 200
    move_payload = engine_response.json()

    assert move_payload["engine"]["key"] == "mock"
    assert move_payload["depth"] == 4
    assert move_payload["uci"] == "e2e4"
    assert move_payload["san"] == "e4"
    assert move_payload["fen"].startswith("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b")


@pytest.mark.asyncio
async def test_engine_game_records_move(client):
    player = await _register_user(client, "engine_challenger")

    token = await _login(client, player["username"], "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    hub_response = await client.get("/hub", headers=headers)
    assert hub_response.status_code == 200
    hub_payload = hub_response.json()
    engines = hub_payload.get("engines")
    assert engines
    mock_engine = next((item for item in engines if item["key"] == "mock"), None)
    assert mock_engine is not None

    opponents = hub_payload.get("opponents")
    assert opponents
    engine_opponent = next((item for item in opponents if item.get("engine_key") == "mock"), None)
    assert engine_opponent is not None
    assert engine_opponent["is_engine"] is True

    create_response = await client.post(
        "/games",
        json={
            "white_player_id": player["id"],
            "black_player_id": engine_opponent["id"],
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    game = create_response.json()

    human_move_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    move_response = await client.post(
        f"/games/{game['id']}/moves",
        json={"notation": "e4", "fen": human_move_fen},
        headers=headers,
    )
    assert move_response.status_code == 201

    engine_move_response = await client.post(
        f"/games/{game['id']}/engine-move",
        json={"engine_key": mock_engine["key"]},
        headers=headers,
    )
    assert engine_move_response.status_code == 200
    engine_move = engine_move_response.json()
    assert engine_move["engine"]["key"] == "mock"

    detail_response = await client.get(f"/games/{game['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["moves_count"] == 2
    assert detail["moves"][1]["player_id"] == engine_opponent["id"]
    assert detail["moves"][1]["notation"] == engine_move["san"]
