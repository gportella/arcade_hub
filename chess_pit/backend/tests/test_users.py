"""User endpoint tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_user_registration_login_and_update(client):
    create_payload = {
        "username": "alice",
        "password": "StrongPass123",
        "avatar_url": "https://example.com/avatar.png",
    }
    response = await client.post("/users", json=create_payload)
    assert response.status_code == 201
    user = response.json()
    assert user["username"] == "alice"
    assert user["avatar_url"] == "https://example.com/avatar.png"
    assert user["is_admin"] is False

    token_response = await client.post(
        "/auth/token",
        data={
            "username": "alice",
            "password": "StrongPass123",
            "grant_type": "password",
        },
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_response = await client.get("/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"

    list_response = await client.get("/users", headers=headers)
    assert list_response.status_code == 200
    users = list_response.json()
    assert any(u["username"] == "alice" for u in users)

    update_response = await client.patch(
        f"/users/{user['id']}",
        json={"avatar_url": "https://example.com/new.png"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["avatar_url"] == "https://example.com/new.png"
