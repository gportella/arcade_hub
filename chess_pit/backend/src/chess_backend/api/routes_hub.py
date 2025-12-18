"""Hub overview endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..api.deps import get_current_user
from ..config import Settings, get_settings
from ..crud.games import list_games
from ..db import get_session
from ..models import Game, User
from ..schemas import EngineInfo, HubGameSummary, HubResponse, OpponentSummary, UserRead
from ..utils.fen import active_color

router = APIRouter(prefix="/hub", tags=["hub"])


def _resolve_opponent(game: Game, current_user: User) -> User:
    if game.white_player_id == current_user.id:
        if game.black_player is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Game missing black player",
            )
        return game.black_player
    if game.black_player_id == current_user.id:
        if game.white_player is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Game missing white player",
            )
        return game.white_player
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not part of this game")


def _find_engine_spec(engine_key: str | None, settings: Settings | None = None):
    if not engine_key:
        return None
    settings = settings or get_settings()
    for spec in settings.engine_specs:
        if spec.key == engine_key:
            return spec
    return None


def _make_opponent_summary(opponent: User, settings: Settings | None = None) -> OpponentSummary:
    if opponent.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Opponent record missing identifier",
        )
    engine_spec = _find_engine_spec(opponent.engine_key, settings)
    display_name = engine_spec.name if engine_spec else opponent.username
    return OpponentSummary(
        id=opponent.id,
        username=opponent.username,
        display_name=display_name,
        avatar_url=opponent.avatar_url,
        is_engine=opponent.is_engine,
        engine_key=opponent.engine_key,
    )


def _make_game_summary(game: Game, current_user: User, settings: Settings) -> HubGameSummary:
    opponent = _resolve_opponent(game, current_user)
    last_updated = game.last_move_at or game.started_at
    your_color = "white" if game.white_player_id == current_user.id else "black"
    turn = active_color(game.current_fen or game.initial_fen)
    if game.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Game record missing identifier",
        )
    return HubGameSummary(
        id=game.id,
        opponent=_make_opponent_summary(opponent, settings),
        status=game.status,
        result=game.result,
        summary=game.summary,
        initial_fen=game.initial_fen,
        current_fen=game.current_fen,
        current_position_hash=game.current_position_hash,
        moves_count=game.moves_count,
        started_at=game.started_at,
        last_updated=last_updated,
        your_color=your_color,
        turn=turn,
        pgn=game.pgn,
    )


@router.get("", response_model=HubResponse)
async def get_hub_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> HubResponse:
    settings = get_settings()
    games = list_games(session)
    games = [
        game for game in games if current_user.id in {game.white_player_id, game.black_player_id}
    ]
    for game in games:
        session.refresh(game, attribute_names=["white_player", "black_player"])
    game_summaries = [_make_game_summary(game, current_user, settings) for game in games]
    game_summaries.sort(key=lambda summary: summary.last_updated, reverse=True)

    opponents_stmt = select(User).where(User.id != current_user.id).order_by(User.username)
    opponents = session.exec(opponents_stmt).all()
    opponent_summaries = [_make_opponent_summary(opponent, settings) for opponent in opponents]

    user_read = UserRead.model_validate(current_user)
    engine_infos = [
        EngineInfo(key=spec.key, name=spec.name, default_depth=spec.default_depth)
        for spec in settings.engine_specs
    ]
    return HubResponse(
        user=user_read,
        games=game_summaries,
        opponents=opponent_summaries,
        engines=engine_infos,
    )
