from __future__ import annotations

import pytest

from connect4.datamodel import (
    BOARD_CAPACITY,
    BOARD_WIDTH,
    COLUMN_TOP_MASK,
    BitboardState,
    ColumnFullError,
    RED,
    YELLOW,
    has_connect_four,
)
from connect4.game import Connect4Game, TurnRole, calculate_next_move
from connect4.sessions import GameMode


def test_connect4_game_tracks_turns_and_roles() -> None:
    game = Connect4Game(mode=GameMode.MULTIPLAYER)

    outcome = game.play_turn(0)

    assert outcome.turn_index == 1
    assert outcome.role is TurnRole.PLAYER_ONE

    outcome_second = game.play_turn(1)

    assert outcome_second.turn_index == 2
    assert outcome_second.role is TurnRole.PLAYER_TWO


def test_calculate_next_move_prefers_center_first_turn() -> None:
    state = BitboardState()

    assert calculate_next_move(state) == 3


def test_calculate_next_move_identifies_immediate_win() -> None:
    state = BitboardState()

    # Build a position where RED has three vertically in column 0
    state.drop(1)  # YELLOW
    state.drop(0)  # RED (1)
    state.drop(2)  # YELLOW
    state.drop(0)  # RED (2)
    state.drop(3)  # YELLOW
    state.drop(0)  # RED (3)
    state.drop(6)  # YELLOW elsewhere to hand turn to RED

    assert state.to_play == RED

    assert calculate_next_move(state) == 0


def test_calculate_next_move_blocks_vertical_threat() -> None:
    state = BitboardState()

    # Build a position where RED threatens a vertical connect four in column 0
    state.drop(1)  # YELLOW
    state.drop(0)  # RED (1)
    state.drop(3)  # YELLOW
    state.drop(0)  # RED (2)
    state.drop(5)  # YELLOW
    state.drop(0)  # RED (3)

    assert state.to_play == YELLOW

    assert calculate_next_move(state) == 0


def test_logged_sequence_does_not_prematurely_end_game() -> None:
    game = Connect4Game(mode=GameMode.SOLO)
    human_moves = [3, 2, 4, 4, 1, 0, 2, 5, 4, 3, 5]
    ai_moves: list[int] = []

    for move in human_moves:
        human_outcome = game.play_turn(move)
        if human_outcome.result.winner is not None:
            break
        if human_outcome.result.draw:
            break

        column = calculate_next_move(game.state)
        ai_moves.append(column)
        ai_outcome = game.play_turn(column)
        if ai_outcome.result.winner is not None or ai_outcome.result.draw:
            break

    board_rows = ["".join(row) for row in game.state.board_schetch()]
    last_result = game.state.last_result
    yellow_board = game.state.board(YELLOW)
    red_board = game.state.board(RED)

    assert game.is_over(), (
        "Game should have concluded",
        human_moves,
        ai_moves,
        board_rows,
        last_result,
        has_connect_four(yellow_board),
        has_connect_four(red_board),
    )
    assert game.winner() == RED


def test_calculate_next_move_raises_when_board_full() -> None:
    state = BitboardState()
    state.mask = 0
    for column in range(BOARD_WIDTH):
        state.mask |= COLUMN_TOP_MASK[column]
    state.move_count = BOARD_CAPACITY

    with pytest.raises(ColumnFullError):
        calculate_next_move(state)
