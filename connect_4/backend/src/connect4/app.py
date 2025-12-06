"""FastAPI application instance for the Connect 4 backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(title="Connect 4 Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/swagger", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    """Serve the Swagger UI under a prettier endpoint."""

    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} – Swagger UI",
    )


__all__ = ["app"]
