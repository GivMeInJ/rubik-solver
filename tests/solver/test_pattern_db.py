from rubik_solver.model.cube import SOLVED
from rubik_solver.solver.pattern_db import corner_index, edge1_index, edge2_index


def test_corner_index_solved_is_zero():
    assert corner_index(SOLVED) == 0


def test_corner_index_range():
    idx = corner_index(SOLVED)
    assert 0 <= idx < 88179840  # 8! * 3^7


def test_edge1_index_solved_is_zero():
    assert edge1_index(SOLVED) == 0


def test_edge1_index_range():
    idx = edge1_index(SOLVED)
    assert 0 <= idx < 42577920  # P(12,6) * 2^6


def test_edge2_index_solved_is_zero():
    assert edge2_index(SOLVED) == 0


def test_edge2_index_range():
    idx = edge2_index(SOLVED)
    assert 0 <= idx < 42577920


def test_corner_index_unique_after_move():
    from rubik_solver.model.moves import apply_move
    state_r = apply_move(SOLVED, "R")
    assert corner_index(state_r) != corner_index(SOLVED)


def test_edge1_index_unique_after_move():
    from rubik_solver.model.moves import apply_move
    state_r = apply_move(SOLVED, "R")
    assert edge1_index(state_r) != edge1_index(SOLVED)
