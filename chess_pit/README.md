# Chess Pit Service

This folder hosts the backend service for the Chess Pit experience. The API is built with FastAPI
and SQLModel, storing persistent data in a SQLite database that is bind-mounted from the host.

## Local Development

```bash
cd chess_pit/backend
pip install -e .[dev]
uvicorn chess_backend.main:app --reload
```

Running the test suite requires the optional `dev` dependencies:

```bash
pytest
```

## Docker

To run only the Chess Pit backend locally:

```bash
cd chess_pit
docker compose up --build
```

The backend is also wired into the root `docker-compose.yml` so it participates in the wider Arcade
Hub deployment. The database lives in `backend/data/chess.db` within the container and is persisted
via the mounted volume.
