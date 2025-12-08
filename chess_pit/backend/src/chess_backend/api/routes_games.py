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
from ..utils.fen import active_color, fen_hash, normalize_fen

router = APIRouter(prefix="/games", tags=["games"])


def _finalize_game(
    session: Session,
    game: Game,
    result: GameResult,
    *,
    summary_note: str | None = None,
) -> Game:
    game = finish_game(session, game, result)

    note = (summary_note or "").strip()
    if note:
        current_summary = game.summary or ""
        if note.lower() not in current_summary.lower():
            game.summary = f"{current_summary} · {note}".strip(" ·") if current_summary else note

    session.add(game)

    white_player = session.get(User, game.white_player_id)
    black_player = session.get(User, game.black_player_id)

    if white_player:
        if result == GameResult.white:
            update_user_stats(session, white_player, won=True)
        elif result == GameResult.black:
            update_user_stats(session, white_player, lost=True)
        else:
            update_user_stats(session, white_player, draw=True)

    if black_player:
        if result == GameResult.white:
            update_user_stats(session, black_player, lost=True)
        elif result == GameResult.black:
            update_user_stats(session, black_player, won=True)
        else:
            update_user_stats(session, black_player, draw=True)

    session.refresh(game)
    return game


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

    if current_user.id not in {game.white_player_id, game.black_player_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot move for this game",
        )

    if game.status in {GameStatus.completed, GameStatus.aborted}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game is no longer active",
        )

    default_turn = "white" if game.moves_count % 2 == 0 else "black"
    expected_turn = active_color(game.current_fen, default=default_turn)
    parity_player_id = game.white_player_id if game.moves_count % 2 == 0 else game.black_player_id
    expected_player_id = parity_player_id
    if expected_player_id not in {game.white_player_id, game.black_player_id}:
        expected_player_id = (
            game.white_player_id if expected_turn == "white" else game.black_player_id
        )
    if current_user.id != expected_player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your turn",
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

    notation = move.notation or ""
    if notation.endswith("#"):
        winner = GameResult.white if move.player_id == game.white_player_id else GameResult.black
        winner_label = "White" if winner == GameResult.white else "Black"
        loser_label = "Black" if winner == GameResult.white else "White"
        game = _finalize_game(
            session,
            game,
            winner,
            summary_note=f"{winner_label} checkmated {loser_label}",
        )
        await broadcast_game_finished(game)

    return MoveRead.model_validate(move)


@router.post("/{game_id}/resign", response_model=GameRead)
async def resign_game(
    game_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameRead:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    if current_user.id not in {game.white_player_id, game.black_player_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot resign this game",
        )

    if game.status in {GameStatus.completed, GameStatus.aborted}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game is no longer active",
        )

    resigning_color = "White" if current_user.id == game.white_player_id else "Black"
    result = GameResult.black if resigning_color == "White" else GameResult.white
    game = _finalize_game(
        session,
        game,
        result,
        summary_note=f"{resigning_color} resigned",
    )
    await broadcast_game_finished(game)
    return GameRead.model_validate(game)


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

    game = _finalize_game(session, game, payload.result)
    await broadcast_game_finished(game)
    return GameRead.model_validate(game)
