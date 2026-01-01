"""Game endpoints."""

from datetime import datetime
from typing import Annotated

import chess
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from ..api.deps import get_current_user
from ..config import EngineSpec, Settings, get_settings
from ..crud.games import append_move, create_game, finish_game, get_game, list_games
from ..crud.users import update_user_stats
from ..db import get_session
from ..models import DEFAULT_START_FEN, Game, GameResult, GameStatus, Move, User
from ..realtime import broadcast_game_finished, broadcast_move
from ..schemas import (
    EngineInfo,
    EngineMoveRequest,
    EngineMoveResponse,
    GameCreate,
    GameDetail,
    GameAnalysisRequest,
    GameAnalysisResponse,
    GameAnalysisSequenceRequest,
    GameAnalysisSequenceResponse,
    GameAnalysisStep,
    GameFinishRequest,
    GameRead,
    MoveCreate,
    MoveRead,
)
from ..services.engine_runner import (
    EngineMoveError,
    EngineProcessError,
    compute_analysis,
    compute_best_move,
)
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

    _update_ratings(session, white_player, black_player, result)

    session.refresh(game)
    return game


def _resolve_engine_spec(engine_key: str | None, settings: Settings | None = None) -> EngineSpec:
    settings = settings or get_settings()
    selected_key = engine_key or (settings.engine_specs[0].key if settings.engine_specs else None)
    if selected_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No engines configured",
        )
    for spec in settings.engine_specs:
        if spec.key == selected_key:
            return spec
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engine not found")


def _clamp_depth_for_spec(depth: int | None, spec: EngineSpec | None) -> int | None:
    if depth is None:
        return None
    cap = spec.max_depth if spec and spec.max_depth is not None else 64
    cap = max(1, min(cap, 64))
    return max(1, min(depth, cap))


def _resolve_analysis_context(
    payload_engine_key: str | None,
    payload_depth: int | None,
    game: Game,
    settings: Settings,
) -> tuple[EngineSpec, int]:
    spec = _resolve_engine_spec(payload_engine_key, settings)
    configured_depth = (
        payload_depth or game.engine_depth or spec.default_depth or settings.engine_default_depth
    )
    desired_depth = _clamp_depth_for_spec(configured_depth, spec) or settings.engine_default_depth
    depth = max(4, desired_depth)
    return spec, depth


def _match_move_by_fen(board: chess.Board, target_fen: str | None) -> chess.Move | None:
    if not target_fen:
        return None
    normalized_target = normalize_fen(target_fen)
    for candidate in board.legal_moves:
        board.push(candidate)
        fen_after = board.fen()
        board.pop()
        if normalize_fen(fen_after) == normalized_target:
            return candidate
    return None


def _expected_score(rating_a: int, rating_b: int) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))


def _score_for_result(player_color: str, result: GameResult) -> float:
    if result == GameResult.draw:
        return 0.5
    if player_color == "white":
        return 1.0 if result == GameResult.white else 0.0
    return 1.0 if result == GameResult.black else 0.0


def _update_ratings(
    session: Session,
    white_player: User | None,
    black_player: User | None,
    result: GameResult,
) -> None:
    if white_player is None or black_player is None:
        session.commit()
        return

    white_rating = white_player.rating if white_player.rating else 1200
    black_rating = black_player.rating if black_player.rating else 1200

    both_human = not white_player.is_engine and not black_player.is_engine
    k_factor_human = 32
    k_factor_engine = 24

    if both_human:
        white_score = _score_for_result("white", result)
        black_score = 1.0 - white_score
        expected_white = _expected_score(white_rating, black_rating)
        expected_black = _expected_score(black_rating, white_rating)
        white_delta = round(k_factor_human * (white_score - expected_white))
        black_delta = round(k_factor_human * (black_score - expected_black))
        white_player.rating = max(100, white_rating + white_delta)
        black_player.rating = max(100, black_rating + black_delta)
    else:
        if not white_player.is_engine:
            white_score = _score_for_result("white", result)
            expected_white = _expected_score(white_rating, black_rating)
            white_delta = round(k_factor_engine * (white_score - expected_white))
            white_player.rating = max(100, white_rating + white_delta)
        if not black_player.is_engine:
            black_score = _score_for_result("black", result)
            expected_black = _expected_score(black_rating, white_rating)
            black_delta = round(k_factor_engine * (black_score - expected_black))
            black_player.rating = max(100, black_rating + black_delta)

    session.add(white_player)
    session.add(black_player)
    session.commit()


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

    settings = get_settings()
    engine_depth = game_in.engine_depth
    initial_time = game_in.initial_time_seconds
    increment_time = game_in.increment_seconds
    engine_player: User | None = None
    if white_player.is_engine:
        engine_player = white_player
    elif black_player.is_engine:
        engine_player = black_player

    if engine_player and engine_player.engine_key:
        engine_spec = _resolve_engine_spec(engine_player.engine_key, settings)
        engine_depth = _clamp_depth_for_spec(engine_depth, engine_spec)
    else:
        engine_depth = _clamp_depth_for_spec(engine_depth, None)

    now = datetime.utcnow()
    white_clock = initial_time if initial_time is not None else None
    black_clock = initial_time if initial_time is not None else None
    turn_start_time = now if initial_time is not None else None

    game = Game(
        white_player_id=game_in.white_player_id,
        black_player_id=game_in.black_player_id,
        status=GameStatus.pending,
        initial_fen=initial_fen,
        current_fen=initial_fen,
        current_position_hash=position_hash,
        summary=game_in.summary or "Friendly challenge",
        engine_depth=engine_depth,
        time_control_initial_seconds=initial_time,
        time_control_increment_seconds=increment_time,
        white_time_remaining_seconds=white_clock,
        black_time_remaining_seconds=black_clock,
        turn_start_time=turn_start_time,
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

    now = datetime.utcnow()

    mover_color = "white" if current_user.id == game.white_player_id else "black"
    is_timed_game = game.time_control_initial_seconds is not None

    if is_timed_game:
        base_initial = game.time_control_initial_seconds or 0
        if game.white_time_remaining_seconds is None:
            game.white_time_remaining_seconds = base_initial
        if game.black_time_remaining_seconds is None:
            game.black_time_remaining_seconds = base_initial
        turn_start = game.turn_start_time or game.last_move_at or game.started_at or now
        elapsed = max(0, int((now - turn_start).total_seconds()))
        increment = game.time_control_increment_seconds or 0

        if mover_color == "white":
            remaining = game.white_time_remaining_seconds or 0
            remaining -= elapsed
            if remaining <= 0:
                game.white_time_remaining_seconds = 0
                game = _finalize_game(
                    session,
                    game,
                    GameResult.black,
                    summary_note="White flagged on time",
                )
                await broadcast_game_finished(game)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="White flagged on time",
                )
            remaining += increment
            game.white_time_remaining_seconds = remaining
        else:
            remaining = game.black_time_remaining_seconds or 0
            remaining -= elapsed
            if remaining <= 0:
                game.black_time_remaining_seconds = 0
                game = _finalize_game(
                    session,
                    game,
                    GameResult.white,
                    summary_note="Black flagged on time",
                )
                await broadcast_game_finished(game)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Black flagged on time",
                )
            remaining += increment
            game.black_time_remaining_seconds = remaining

        game.turn_start_time = now

    move = Move(
        game_id=game.id,
        player_id=current_user.id,
        move_number=game.moves_count + 1,
        notation=move_in.notation,
        played_at=now,
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


@router.post("/{game_id}/engine-move", response_model=EngineMoveResponse)
async def request_engine_move(
    game_id: int,
    payload: EngineMoveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EngineMoveResponse:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    if not current_user.is_admin and current_user.id not in {
        game.white_player_id,
        game.black_player_id,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access engine for this game",
        )

    try:
        board = chess.Board(game.current_fen)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid game position",
        ) from exc

    if board.is_game_over():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game is finished; no legal moves available",
        )

    session.refresh(game, attribute_names=["white_player", "black_player"])
    engine_player: User | None = None
    if game.white_player and game.white_player.is_engine:
        engine_player = game.white_player
    elif game.black_player and game.black_player.is_engine:
        engine_player = game.black_player

    settings = get_settings()
    desired_engine_key = payload.engine_key or (
        engine_player.engine_key if engine_player and engine_player.engine_key else None
    )
    spec = _resolve_engine_spec(desired_engine_key, settings)
    if engine_player and engine_player.engine_key and engine_player.engine_key != spec.key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requested engine does not match game configuration",
        )

    configured_depth = (
        payload.depth or game.engine_depth or spec.default_depth or settings.engine_default_depth
    )
    depth = _clamp_depth_for_spec(configured_depth, spec) or 1

    try:
        engine_move = await run_in_threadpool(
            compute_best_move,
            spec,
            board,
            depth=depth,
        )
    except EngineProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except EngineMoveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if engine_player and engine_player.id is not None:
        now = datetime.utcnow()

        mover_color = "white" if engine_player.id == game.white_player_id else "black"
        is_timed_game = game.time_control_initial_seconds is not None

        if is_timed_game:
            base_initial = game.time_control_initial_seconds or 0
            if game.white_time_remaining_seconds is None:
                game.white_time_remaining_seconds = base_initial
            if game.black_time_remaining_seconds is None:
                game.black_time_remaining_seconds = base_initial
            turn_start = game.turn_start_time or game.last_move_at or game.started_at or now
            elapsed = max(0, int((now - turn_start).total_seconds()))
            increment = game.time_control_increment_seconds or 0

            if mover_color == "white":
                remaining = game.white_time_remaining_seconds or 0
                remaining -= elapsed
                if remaining <= 0:
                    game.white_time_remaining_seconds = 0
                    game = _finalize_game(
                        session,
                        game,
                        GameResult.black,
                        summary_note="White flagged on time",
                    )
                    await broadcast_game_finished(game)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="White flagged on time",
                    )
                remaining += increment
                game.white_time_remaining_seconds = remaining
            else:
                remaining = game.black_time_remaining_seconds or 0
                remaining -= elapsed
                if remaining <= 0:
                    game.black_time_remaining_seconds = 0
                    game = _finalize_game(
                        session,
                        game,
                        GameResult.white,
                        summary_note="Black flagged on time",
                    )
                    await broadcast_game_finished(game)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Black flagged on time",
                    )
                remaining += increment
                game.black_time_remaining_seconds = remaining

            game.turn_start_time = now

        move = Move(
            game_id=game.id,
            player_id=engine_player.id,
            move_number=game.moves_count + 1,
            notation=engine_move.san,
            played_at=now,
            fen=engine_move.fen,
        )
        move = append_move(session, game, move)
        await broadcast_move(game, move)

        notation = move.notation or ""
        if notation.endswith("#"):
            winner = (
                GameResult.white if move.player_id == game.white_player_id else GameResult.black
            )
            winner_label = "White" if winner == GameResult.white else "Black"
            loser_label = "Black" if winner == GameResult.white else "White"
            game = _finalize_game(
                session,
                game,
                winner,
                summary_note=f"{winner_label} checkmated {loser_label}",
            )
            await broadcast_game_finished(game)

    return EngineMoveResponse(
        engine=EngineInfo(
            key=spec.key,
            name=spec.name,
            default_depth=spec.default_depth,
            max_depth=spec.max_depth,
        ),
        depth=depth,
        uci=engine_move.uci,
        san=engine_move.san,
        fen=engine_move.fen,
    )


@router.post("/{game_id}/analysis", response_model=GameAnalysisResponse)
async def analyze_game(
    game_id: int,
    payload: GameAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameAnalysisResponse:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    if not current_user.is_admin and current_user.id not in {
        game.white_player_id,
        game.black_player_id,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot analyze this game",
        )

    if game.status != GameStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis available after the game is completed",
        )

    settings = get_settings()
    spec, depth = _resolve_analysis_context(payload.engine_key, payload.depth, game, settings)

    try:
        board = chess.Board(game.current_fen or game.initial_fen)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid game position",
        ) from exc

    try:
        analysis = compute_analysis(spec, board, depth=depth)
    except EngineProcessError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return GameAnalysisResponse(
        engine=EngineInfo(
            key=spec.key,
            name=spec.name,
            default_depth=spec.default_depth,
            max_depth=spec.max_depth,
        ),
        depth=analysis.depth,
        evaluation_cp=analysis.evaluation_cp,
        mate_in=analysis.mate_in,
        best_move_uci=analysis.best_move_uci,
        best_move_san=analysis.best_move_san,
        line_uci=analysis.line_uci,
        line_san=analysis.line_san,
    )


@router.post("/{game_id}/analysis/sequence", response_model=GameAnalysisSequenceResponse)
async def analyze_game_sequence(
    game_id: int,
    payload: GameAnalysisSequenceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GameAnalysisSequenceResponse:
    game = get_game(session, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    if not current_user.is_admin and current_user.id not in {
        game.white_player_id,
        game.black_player_id,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot analyze this game",
        )

    if game.status != GameStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis available after the game is completed",
        )

    settings = get_settings()
    spec, depth = _resolve_analysis_context(payload.engine_key, payload.depth, game, settings)

    try:
        board = chess.Board(game.initial_fen)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid game position",
        ) from exc

    session.refresh(game, attribute_names=["moves"])
    ordered_moves = sorted(game.moves, key=lambda move: move.move_number)

    try:
        current_analysis = await run_in_threadpool(
            compute_analysis,
            spec,
            board.copy(),
            depth=depth,
        )
    except EngineProcessError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    steps: list[GameAnalysisStep] = []

    for index, move in enumerate(ordered_moves):
        turn_color = "white" if board.turn == chess.WHITE else "black"
        fen_before = board.fen()

        try:
            actual_move = board.parse_san(move.notation)
        except ValueError:
            actual_move = _match_move_by_fen(board, move.fen)

        if actual_move is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unable to replay move {move.move_number} for analysis",
            )

        played_san = board.san(actual_move)
        played_uci = actual_move.uci()
        board.push(actual_move)
        fen_after = board.fen()

        try:
            next_analysis = await run_in_threadpool(
                compute_analysis,
                spec,
                board.copy(),
                depth=depth,
            )
        except EngineProcessError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        steps.append(
            GameAnalysisStep(
                move_index=index,
                move_number=move.move_number,
                turn=turn_color,
                played_san=played_san,
                played_uci=played_uci,
                evaluation_before_cp=current_analysis.evaluation_cp,
                evaluation_after_cp=next_analysis.evaluation_cp,
                mate_before=current_analysis.mate_in,
                mate_after=next_analysis.mate_in,
                best_move_uci=current_analysis.best_move_uci,
                best_move_san=current_analysis.best_move_san,
                best_line_uci=current_analysis.line_uci,
                best_line_san=current_analysis.line_san,
                fen_before=fen_before,
                fen_after=fen_after,
            )
        )

        current_analysis = next_analysis

    return GameAnalysisSequenceResponse(
        engine=EngineInfo(
            key=spec.key,
            name=spec.name,
            default_depth=spec.default_depth,
            max_depth=spec.max_depth,
        ),
        depth=current_analysis.depth,
        steps=steps,
        final_evaluation_cp=current_analysis.evaluation_cp,
        final_mate_in=current_analysis.mate_in,
    )


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
