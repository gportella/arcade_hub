"""CRUD helpers for game and move resources."""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import Game, GameResult, GameStatus, Move


def _append_pgn(existing: str, move: Move) -> str:
    turn = (move.move_number + 1) // 2
    if move.move_number % 2 == 1:
        snippet = f"{turn}. {move.notation}"
    else:
        snippet = f"{turn}... {move.notation}"
    return (existing + " " + snippet).strip()


def create_game(session: Session, game: Game) -> Game:
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
    session.add(move)
    game.moves_count += 1
    game.last_move_at = move.played_at
    if game.status == GameStatus.pending:
        game.status = GameStatus.active
    game.pgn = _append_pgn(game.pgn, move)
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
    session.add(game)
    session.commit()
    session.refresh(game)
    return game
