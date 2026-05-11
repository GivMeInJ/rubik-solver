from rubik_solver.model.cube import SOLVED
from rubik_solver.model.moves import apply_move
from rubik_solver.solver.pattern_db import corner_index, edge1_index, edge2_index

def test_corner_index_solved_is_zero():
    assert corner_index(SOLVED) == 0

def test_corner_index_range():
    assert 0 <= corner_index(SOLVED) < 88179840  # 8! * 3^7

def test_edge1_index_solved_is_zero():
    # edge1 tracks slots 0-5; in SOLVED state these have cubelets [0..5] → Lehmer=0
    assert edge1_index(SOLVED) == 0

def test_edge1_index_range():
    assert 0 <= edge1_index(SOLVED) < 42577920  # P(12,6) * 2^6

def test_edge2_index_solved_in_range():
    # edge2 tracks slots 6-11; SOLVED state has cubelets [6..11] → non-zero but valid
    idx = edge2_index(SOLVED)
    assert 0 <= idx < 42577920  # P(12,6) * 2^6

def test_edge2_index_deterministic():
    # Same state always gives same index
    assert edge2_index(SOLVED) == edge2_index(SOLVED)

def test_corner_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert corner_index(state_r) != corner_index(SOLVED)

def test_edge1_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert edge1_index(state_r) != edge1_index(SOLVED)

def test_edge2_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert edge2_index(state_r) != edge2_index(SOLVED)

def test_edge_index_no_collisions():
    """Different cubelets in slots must produce different indices (no relative-rank collisions)"""
    # Artificially create two states with different cubelets in slots 6-11
    from rubik_solver.model.cube import CubeState
    # State A: slots 6-11 have cubelets [6,7,8,9,10,11] (normal solved)
    state_a = SOLVED
    # State B: swap cubelets so slots 6-11 have cubelets [0,1,2,3,4,5] — artificially construct
    # (This is not a valid reachable cube state, but tests the encoding)
    state_b = CubeState(
        corner_perm=SOLVED.corner_perm,
        corner_orient=SOLVED.corner_orient,
        edge_perm=(6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5),  # swapped halves
        edge_orient=SOLVED.edge_orient,
    )
    # With relative rank, both would give index 0; with proper P(12,6), they must differ
    assert edge2_index(state_a) != edge2_index(state_b)
