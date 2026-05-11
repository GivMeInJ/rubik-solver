import pytest
from rubik_solver.model.cube import SOLVED, is_solved
from rubik_solver.model.moves import apply_move
from rubik_solver.solver.ida_star import ida_star
from rubik_solver.solver.pattern_db import PatternDB

@pytest.fixture(scope="module")
def small_db():
    return PatternDB(max_depth=7)

def test_solve_already_solved(small_db):
    result = ida_star(SOLVED, small_db)
    assert result == []

def test_solve_one_move(small_db):
    state = apply_move(SOLVED, "R")
    moves = ida_star(state, small_db)
    assert len(moves) <= 3  # optimal is 1 (R' or R3)
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)

def test_solve_two_moves(small_db):
    state = apply_move(apply_move(SOLVED, "R"), "U")
    moves = ida_star(state, small_db)
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)
    assert len(moves) <= 4

def test_solve_sexy_move_once(small_db):
    # R U R' U' → 1 application, solve within 6 moves
    state = SOLVED
    for mv in ["R", "U", "R'", "U'"]:
        state = apply_move(state, mv)
    moves = ida_star(state, small_db)
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)
