
# Connect 4 Backend

FastAPI service scaffold for the Connect 4 multiplayer backend. It exposes a basic
REST health check and a WebSocket endpoint that keeps separate sessions per game
so multiple matches can run concurrently.

## Getting started

```sh
uv sync
```

Run the development server with uvicorn through the project entrypoint:

```sh
uv run backend
```

Alternatively, invoke uvicorn directly if you prefer to opt into reload mode:

```sh
uv run uvicorn connect4.app:app --reload
```

### Run the test suite

```sh
uv run -m pytest
```

## Available endpoints

- `GET /health` – lightweight readiness probe.
- `POST /games` – register a session; include `{ "mode": "solo" }` to start a
	single-player match (defaults to multiplayer when omitted).
- `GET /games` – list active sessions with player counts.
- `GET /games/{game_id}` – inspect a specific session.
- `WS /ws/{game_id}/{player_id}?mode={solo|multiplayer}` – joins the requested
	game; solo mode echoes messages to the same socket so the server can later
	drive AI turns.

Each WebSocket message sent by a client is enriched with the `gameId` and
`playerId` fields before the server broadcasts it to the rest of the session.