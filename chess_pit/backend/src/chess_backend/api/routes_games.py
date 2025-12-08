"""Game endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..api.deps import get_current_user
from ..crud.games import append_move, create_game, finish_game, get_game, list_games
from ..crud.users import update_user_stats
from ..db import get_session
from ..models import DEFAULT_START_FEN, Game, GameResult, GameStatus, Move, User
from ..realtime import broadcast_game_finished, broadcast_move
from ..schemas import GameCreate, GameDetail, GameFinishRequest, GameRead, MoveCreate, MoveRead
from ..utils.fen import fen_hash, normalize_fen

router = APIRouter(prefix="/games", tags=["games"])


@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
async def create_new_game(
    game_in: GameCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameRead:
    white_player = session.get(User, game_in.white_player_id)
    black_player = session.get(User, game_in.black_player_id)
    if white_player is None or black_player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    if not current_user.is_admin and current_user.id not in {
        game_in.white_player_id,
        game_in.black_player_id,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create games for other users",
        )

    initial_fen = normalize_fen(game_in.initial_fen, DEFAULT_START_FEN)
    position_hash = fen_hash(initial_fen)

    game = Game(
        white_player_id=game_in.white_player_id,
        black_player_id=game_in.black_player_id,
        status=GameStatus.pending,
        initial_fen=initial_fen,
        current_fen=initial_fen,
        current_position_hash=position_hash,
        summary=game_in.summary or "Friendly challenge",
    )
    game = create_game(session, game)
    return GameRead.model_validate(game)


@router.get("", response_model=list[GameRead])
async def get_games(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[GameRead]:
    games = list_games(session)
    if not current_user.is_admin:
        games = [g for g in games if current_user.id in {g.white_player_id, g.black_player_id}]
    return [GameRead.model_validate(game) for game in games]


@router.get("/{game_id}", response_model=GameDetail)
async def get_game_detail(
    game_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameDetail:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if not current_user.is_admin and current_user.id not in {
        game.white_player_id,
        game.black_player_id,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access game")
    session.refresh(game, attribute_names=["moves"])
    game_data = GameRead.model_validate(game)
    move_reads = [MoveRead.model_validate(move) for move in game.moves]
    return GameDetail(**game_data.model_dump(), moves=move_reads)


@router.post("/{game_id}/moves", response_model=MoveRead, status_code=status.HTTP_201_CREATED)
async def record_move(
    game_id: int,
    move_in: MoveCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> MoveRead:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    if (
        current_user.id not in {game.white_player_id, game.black_player_id}
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot move for this game",
        )

    move = Move(
        game_id=game.id,
        player_id=current_user.id,
        move_number=game.moves_count + 1,
        notation=move_in.notation,
        played_at=datetime.utcnow(),
        fen=move_in.fen,
    )
    move = append_move(session, game, move)
    await broadcast_move(game, move)
    return MoveRead.model_validate(move)


@router.post("/{game_id}/finish", response_model=GameRead)
async def mark_game_finished(
    game_id: int,
    payload: GameFinishRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameRead:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    game = finish_game(session, game, payload.result)

    white_player = session.get(User, game.white_player_id)
    black_player = session.get(User, game.black_player_id)
    if white_player and black_player:
        if payload.result == GameResult.white:
            update_user_stats(session, white_player, won=True)
            update_user_stats(session, black_player, lost=True)
        elif payload.result == GameResult.black:
            update_user_stats(session, white_player, lost=True)
            update_user_stats(session, black_player, won=True)
        else:
            update_user_stats(session, white_player, draw=True)
            update_user_stats(session, black_player, draw=True)
    await broadcast_game_finished(game)
    return GameRead.model_validate(game)
