"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_auth,
    routes_engines,
    routes_games,
    routes_health,
    routes_hub,
    routes_realtime,
    routes_users,
)
from .config import get_settings
from .lifespan import app_lifespan

log = logging.getLogger(__name__)
app = FastAPI(title="Chess Pit Backend", version="0.1.0", lifespan=app_lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
async def root() -> dict[str, Any]:
    return {"status": "ok"}


app.include_router(routes_health.router)
app.include_router(routes_auth.router)
app.include_router(routes_users.router)
app.include_router(routes_games.router)
app.include_router(routes_engines.router)
app.include_router(routes_hub.router)
app.include_router(routes_realtime.router)
