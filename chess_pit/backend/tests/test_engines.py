"""Tests for engine integration endpoints."""

from __future__ import annotations

import chess
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
    assert payload[0]["default_depth"] == 3
    assert payload[0]["max_depth"] == 10


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
    assert engine_move["depth"] == 3

    detail_response = await client.get(f"/games/{game['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["moves_count"] == 2
    assert detail["moves"][1]["player_id"] == engine_opponent["id"]
    assert detail["moves"][1]["notation"] == engine_move["san"]


@pytest.mark.asyncio
async def test_game_engine_depth_applies_when_not_in_payload(client):
    player = await _register_user(client, "depth_requester")

    token = await _login(client, player["username"], "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    hub_response = await client.get("/hub", headers=headers)
    assert hub_response.status_code == 200
    opponents = hub_response.json().get("opponents", [])
    engine_opponent = next((item for item in opponents if item.get("engine_key") == "mock"), None)
    assert engine_opponent is not None

    desired_depth = 6
    create_response = await client.post(
        "/games",
        json={
            "white_player_id": player["id"],
            "black_player_id": engine_opponent["id"],
            "engine_depth": desired_depth,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    game = create_response.json()
    assert game["engine_depth"] == desired_depth

    engine_move_response = await client.post(
        f"/games/{game['id']}/engine-move",
        json={"engine_key": "mock"},
        headers=headers,
    )
    assert engine_move_response.status_code == 200
    payload = engine_move_response.json()
    assert payload["depth"] == desired_depth


@pytest.mark.asyncio
async def test_engine_depth_clamped_to_spec(client):
    player = await _register_user(client, "depth_clamper")

    token = await _login(client, player["username"], "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    hub_response = await client.get("/hub", headers=headers)
    assert hub_response.status_code == 200
    hub_payload = hub_response.json()
    opponents = hub_payload.get("opponents", [])
    engine_opponent = next((item for item in opponents if item.get("engine_key") == "mock"), None)
    assert engine_opponent is not None

    create_response = await client.post(
        "/games",
        json={
            "white_player_id": player["id"],
            "black_player_id": engine_opponent["id"],
            "engine_depth": 25,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    game = create_response.json()
    assert game["engine_depth"] == 10

    engine_move_response = await client.post(
        f"/games/{game['id']}/engine-move",
        json={"engine_key": "mock", "depth": 64},
        headers=headers,
    )
    assert engine_move_response.status_code == 200
    payload = engine_move_response.json()
    assert payload["depth"] == 10


@pytest.mark.asyncio
async def test_game_analysis_endpoint(client):
    white = await _register_user(client, "analysis_white")
    black = await _register_user(client, "analysis_black")

    token = await _login(client, white["username"], "StrongPass123")
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

    admin_token = await _login(client, "admin", "AdminPass123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    finish_response = await client.post(
        f"/games/{game['id']}/finish",
        json={"result": "white"},
        headers=admin_headers,
    )
    assert finish_response.status_code == 200

    analysis_response = await client.post(
        f"/games/{game['id']}/analysis",
        json={"engine_key": "mock", "depth": 12},
        headers=headers,
    )
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["engine"]["key"] == "mock"
    assert analysis["depth"] == 10
    assert analysis["evaluation_cp"] == 32
    assert analysis["line_uci"] in ([], ["e2e4"])


@pytest.mark.asyncio
async def test_game_analysis_sequence_endpoint(client):
    white = await _register_user(client, "sequence_white")
    black = await _register_user(client, "sequence_black")

    white_token = await _login(client, white["username"], "StrongPass123")
    white_headers = {"Authorization": f"Bearer {white_token}"}

    create_response = await client.post(
        "/games",
        json={
            "white_player_id": white["id"],
            "black_player_id": black["id"],
        },
        headers=white_headers,
    )
    assert create_response.status_code == 201
    game = create_response.json()

    board = chess.Board()

    first_move = board.parse_san("e4")
    board.push(first_move)
    move_one_fen = board.fen()
    first_move_response = await client.post(
        f"/games/{game['id']}/moves",
        json={"notation": "e4", "fen": move_one_fen},
        headers=white_headers,
    )
    assert first_move_response.status_code == 201

    black_token = await _login(client, black["username"], "StrongPass123")
    black_headers = {"Authorization": f"Bearer {black_token}"}

    second_move = board.parse_san("e5")
    board.push(second_move)
    move_two_fen = board.fen()
    second_move_response = await client.post(
        f"/games/{game['id']}/moves",
        json={"notation": "e5", "fen": move_two_fen},
        headers=black_headers,
    )
    assert second_move_response.status_code == 201

    admin_token = await _login(client, "admin", "AdminPass123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    finish_response = await client.post(
        f"/games/{game['id']}/finish",
        json={"result": "draw"},
        headers=admin_headers,
    )
    assert finish_response.status_code == 200

    analysis_response = await client.post(
        f"/games/{game['id']}/analysis/sequence",
        json={"engine_key": "mock", "depth": 8},
        headers=white_headers,
    )
    assert analysis_response.status_code == 200
    payload = analysis_response.json()

    assert payload["engine"]["key"] == "mock"
    assert payload["depth"] == 8
    assert payload["final_evaluation_cp"] == 32
    assert len(payload["steps"]) == 2

    first_step = payload["steps"][0]
    assert first_step["turn"] == "white"
    assert first_step["played_san"] == "e4"
    assert first_step["best_move_san"] in ("e4", None)
    assert first_step["evaluation_before_cp"] == 32

    second_step = payload["steps"][1]
    assert second_step["turn"] == "black"
    assert second_step["played_san"] == "e5"
    assert second_step["evaluation_before_cp"] == 32
