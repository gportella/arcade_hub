"""Health endpoints."""

from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse()
