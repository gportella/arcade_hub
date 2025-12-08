"""CRUD helpers for game and move resources."""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import Game, GameResult, GameStatus, Move
from ..utils.fen import fen_hash, normalize_fen, set_active_color


def _append_pgn(existing: str, move: Move) -> str:
    turn = (move.move_number + 1) // 2
    if move.move_number % 2 == 1:
        snippet = f"{turn}. {move.notation}"
    else:
        snippet = move.notation
        if not existing.strip():
            snippet = f"{turn}... {move.notation}"
    return (existing + " " + snippet).strip()


def create_game(session: Session, game: Game) -> Game:
    game.initial_fen = normalize_fen(game.initial_fen, game.initial_fen)
    game.current_fen = normalize_fen(game.current_fen, game.initial_fen)
    game.current_position_hash = fen_hash(game.current_fen)
    session.add(game)
    session.commit()
    session.refresh(game)
    return game


def get_game(session: Session, game_id: int) -> Optional[Game]:
    statement = select(Game).where(Game.id == game_id)
    return session.exec(statement).first()


def list_games(session: Session) -> list[Game]:
    statement = select(Game).order_by(Game.started_at.desc())
    return list(session.exec(statement))


def append_move(session: Session, game: Game, move: Move) -> Move:
    move_fen = normalize_fen(move.fen, game.current_fen)
    if move_fen is None:
        move_fen = game.current_fen
    next_color = "black" if move.player_id == game.white_player_id else "white"
    move.fen = set_active_color(move_fen, next_color)
    move.position_hash = fen_hash(move.fen)
    session.add(move)
    game.moves_count += 1
    game.last_move_at = move.played_at
    if game.status == GameStatus.pending:
        game.status = GameStatus.active
    game.pgn = _append_pgn(game.pgn, move)
    game.current_fen = move.fen or game.current_fen
    game.current_position_hash = fen_hash(game.current_fen)
    session.add(game)
    session.commit()
    session.refresh(move)
    session.refresh(game)
    return move


def finish_game(session: Session, game: Game, result: GameResult) -> Game:
    game.status = GameStatus.completed
    game.result = result
    game.last_move_at = datetime.utcnow()
    if result == GameResult.white:
        outcome = "1-0"
    elif result == GameResult.black:
        outcome = "0-1"
    else:
        outcome = "1/2-1/2"
    game.pgn = (game.pgn + f" {outcome}").strip()
    game.current_position_hash = fen_hash(game.current_fen)
    session.add(game)
    session.commit()
    session.refresh(game)
    return game
