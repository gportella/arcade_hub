"""Engine related endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..api.deps import get_current_user
from ..config import get_settings
from ..models import User
from ..schemas import EngineInfo

router = APIRouter(prefix="/engines", tags=["engines"])


@router.get("", response_model=list[EngineInfo])
async def list_engines(
    _: Annotated[User, Depends(get_current_user)],
) -> list[EngineInfo]:
    settings = get_settings()
    return [
        EngineInfo(key=spec.key, name=spec.name, default_depth=spec.default_depth)
        for spec in settings.engine_specs
    ]
