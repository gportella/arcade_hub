"""Unit tests for puzzle move logic."""

from fastapi.testclient import TestClient

from solve_parking_backend.main import app
from solve_parking_backend.services import initial_state


def test_initial_state_valid() -> None:
    state = initial_state()
    assert state.size == 6
    assert any(vehicle.goal for vehicle in state.vehicles)


def test_move_goal_path() -> None:
    client = TestClient(app)
    client.post("/api/reset")

    # Move blocker (vehicle B) three tiles down to free the goal path.
    for _ in range(3):
        response = client.post("/api/move", json={"vehicle_id": "B", "steps": 1})
        assert response.status_code == 200

    # Now move the goal vehicle to the exit.
    goal_steps = [1, 1, 1]
    completed = False
    for step in goal_steps:
        response = client.post("/api/move", json={"vehicle_id": "X", "steps": step})
        assert response.status_code == 200
        completed = response.json()["completed"]

    assert completed is True


def test_invalid_move_blocked() -> None:
    client = TestClient(app)
    client.post("/api/reset")

    response = client.post("/api/move", json={"vehicle_id": "C", "steps": -1})
    assert response.status_code == 400
    data = response.json()
    assert "blocks the path" in data["detail"]
