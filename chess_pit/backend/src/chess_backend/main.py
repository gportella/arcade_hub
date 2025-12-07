"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from .api import routes_auth, routes_games, routes_health, routes_users
from .lifespan import app_lifespan

log = logging.getLogger(__name__)
app = FastAPI(title="Chess Pit Backend", version="0.1.0", lifespan=app_lifespan)


@app.get("/", tags=["health"])
async def root() -> dict[str, Any]:
    return {"status": "ok"}


app.include_router(routes_health.router)
app.include_router(routes_auth.router)
app.include_router(routes_users.router)
app.include_router(routes_games.router)
