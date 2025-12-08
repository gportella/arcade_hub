import logging
import random
from typing import Dict, Tuple

from .graph import Graph, Vertex
from .services import (
    InvalidMoveError,
    MoveResult,
    _board_from,
    apply_move,
    generate_all_moves_stops,
    is_solved,
)
from .models import MoveRequest, Orientation, PuzzleState
from collections import deque

MAX_ITER = 1000000


logger = logging.getLogger(__name__)

# todo --> the goal vehicle is so important would be
# best to have a more direct way of detecting it


def exit_d(state: PuzzleState):
    goal_veh = next(iter([veh for veh in state.vehicles if veh.goal]))
    d = 100
    if goal_veh.orientation is Orientation.horizontal:
        d = state.exit.col - goal_veh.col - goal_veh.length + 1
    else:
        d = state.exit.row - goal_veh.row - goal_veh.length + 1
    return d


def move_random(state: PuzzleState) -> MoveResult:
    ha = Vertex(state)
    goal_veh = next(iter([veh for veh in state.vehicles if veh.goal]))
    chose = random.choice([cand for cand in state.vehicles if not cand.goal])
    _board_from(state.vehicles, state.size, exclude_id=chose)
    jump = exit_d(state)
    try:
        haha = apply_move(state, MoveRequest(vehicle_id=goal_veh.id, steps=jump))
        return haha
    except Exception:
        return MoveResult(state=state, completed=False)


def generate_all_moves(state: PuzzleState):
    for vh in state.vehicles:
        if vh.orientation is Orientation.horizontal:
            max_pos = state.size - (vh.col + vh.length)
            max_neg = vh.col
        else:
            max_pos = state.size - (vh.row + vh.length)
            max_neg = vh.row

        for mv_d in range(-max_neg, max_pos + 1):
            if mv_d == 0:
                continue
            try:
                try_move = apply_move(state, MoveRequest(vehicle_id=vh.id, steps=mv_d))
                yield try_move
            except InvalidMoveError:
                continue
                # return MoveResult(state=state, completed=False)


def canonical_key(state: "PuzzleState") -> Tuple:
    vehicles_key = tuple(
        sorted(
            (veh.id, veh.orientation, veh.length, veh.row, veh.col)
            for veh in state.vehicles
        )
    )
    return (state.size, state.exit.row, state.exit.col, vehicles_key)


def solve_it(state: PuzzleState) -> tuple[MoveResult, int, list[PuzzleState]]:
    puzzle_gp = Graph()
    start = Vertex(state)
    start.distance = 0
    start.previous = None
    queue = deque([start])
    solution = MoveResult(state=state, completed=False)
    min_moves = 0
    iterations = 0
    visited: Dict[Tuple, int] = {canonical_key(state): 0}

    while queue:
        iterations += 1
        if iterations > MAX_ITER:
            logger.error("Too many iterations during solve search")
            break

        next_vert = queue.popleft()
        for mv in generate_all_moves_stops(next_vert.key):
            puzzle_gp.addEdge(next_vert.key, mv.state)
            child_key = canonical_key(mv.state)
            g_cost = next_vert.distance + 1
            # Depth-aware duplicate pruning
            best = visited.get(child_key)
            if best is not None and g_cost >= best:
                continue  # already seen at equal or lower cost
            # Record improved visit
            visited[child_key] = g_cost

            # puzzle_gp.addEdge(next_vert.key, mv.state)
            puzzle_gp.addEdge(next_vert.key, mv.state)
            if mv.completed:
                min_moves = next_vert.distance + 1
                logger.info("Solved in %s moves", min_moves)
                goal_vertex = puzzle_gp.getVertex(mv.state)
                if goal_vertex is not None:
                    goal_vertex.previous = next_vert
                    goal_vertex.distance = min_moves
                    goal_vertex.color = "black"
                solution = mv
                queue.clear()
                break

        if solution.completed:
            break

        the_vertex = puzzle_gp.getVertex(next_vert.key)
        if the_vertex is None:
            continue

        for vertex in the_vertex.getConnections():
            if vertex.color == "white":
                vertex.color = "gray"
                vertex.distance = next_vert.distance + 1
                vertex.previous = next_vert
                queue.append(vertex)
        next_vert.color = "black"

        if solution.completed:
            break

    print("solution ", is_solved(solution.state))
    raw_path = puzzle_gp.traverse(solution.state, show_path=True)
    path: list[PuzzleState] = list(reversed(raw_path)) if raw_path else []
    return solution, min_moves, path
