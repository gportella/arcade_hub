"""Connect 4 backend package entrypoints."""

from __future__ import annotations

import os

import uvicorn

from .app import app

__all__ = ["app", "main"]


def main() -> None:
    """Run the Connect 4 FastAPI application with uvicorn."""

    host = os.getenv("CONNECT4_HOST", "0.0.0.0")
    port = int(os.getenv("CONNECT4_PORT", "8000"))
    reload = os.getenv("CONNECT4_RELOAD", "0").lower() in {"1", "true", "yes"}
    log_level = os.getenv("CONNECT4_LOG_LEVEL", "info")

    uvicorn.run(
        "connect4.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
