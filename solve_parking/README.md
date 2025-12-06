# Solve Parking

A lightweight Rush Hour inspired puzzle built with a Svelte + Vite frontend and a FastAPI backend managed via `uv`. The backend serves puzzle state and validates moves, while the frontend renders the board and lets players slide vehicles to clear the exit for the goal car.

## Project Layout

```
.
├── backend/         # FastAPI service (uv-managed)
└── frontend/        # Vite + Svelte single-page app
```

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for Python dependency management
- Node.js 20+ and npm

## Backend (FastAPI)

```bash
cd backend
uv sync                 # install runtime + dev dependencies
uv run uvicorn solve_parking_backend.main:app --reload
```

Endpoints:

- `GET /health` – service heartbeat
- `GET /api/puzzle` – current puzzle snapshot
- `POST /api/move` – apply a move `{ "vehicle_id": "X", "steps": 1 }`
- `POST /api/reset` – reset to the starter layout

Run unit tests with:

```bash
uv run pytest
```

## Frontend (Svelte)

```bash
cd frontend
npm install
npm run dev -- --host
```

During development the Vite dev server proxies `/api/*` requests to `http://127.0.0.1:8000`.

## Gameplay Notes

- Vehicles occupy contiguous tiles either horizontally or vertically.
- Only the goal vehicle (`X`, highlighted in orange) needs to reach the right-edge exit.
- Move controls become available once a vehicle is selected; invalid moves surface backend validation messages.

## Next Steps

- Persist puzzle progress per-session
- Add drag-and-drop controls and animations
- Support multiple puzzle layouts and difficulty levels
- Expose a solver endpoint for hints or auto-complete
