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

def test_edge2_index_solved_is_nonzero():
    # Regression: relative-rank encoding wrongly gave 0; proper P(12,6) gives 23,442,432
    assert edge2_index(SOLVED) == 23_442_432

def test_corner_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert corner_index(state_r) != corner_index(SOLVED)

def test_edge1_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert edge1_index(state_r) != edge1_index(SOLVED)

def test_edge2_index_unique_after_move():
    state_r = apply_move(SOLVED, "R")
    assert edge2_index(state_r) != edge2_index(SOLVED)

import tempfile, os
from rubik_solver.solver.pattern_db import PatternDB

def test_pattern_db_build_small():
    """depth=2까지 BFS해도 SOLVED=0을 포함해야 함"""
    db = PatternDB(max_depth=2)
    assert db.corner_db[corner_index(SOLVED)] == 0
    assert db.edge1_db[edge1_index(SOLVED)] == 0
    assert db.edge2_db[edge2_index(SOLVED)] == 0

def test_pattern_db_heuristic_solved():
    db = PatternDB(max_depth=2)
    assert db.h(SOLVED) == 0

def test_pattern_db_heuristic_one_move():
    db = PatternDB(max_depth=2)
    state = apply_move(SOLVED, "R")
    assert db.h(state) >= 1

def test_pattern_db_save_load(tmp_path):
    db = PatternDB(max_depth=1)
    db.save(str(tmp_path / "corner.pkl"),
            str(tmp_path / "e1.pkl"),
            str(tmp_path / "e2.pkl"))
    db2 = PatternDB.load(str(tmp_path / "corner.pkl"),
                         str(tmp_path / "e1.pkl"),
                         str(tmp_path / "e2.pkl"))
    assert db2.h(SOLVED) == 0
    assert db2.corner_db[corner_index(SOLVED)] == 0


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


def test_edge2_index_changes_after_u_on_r_state():
    """Regression: slot-tracking incorrectly gave edge2_index(R)==edge2_index(R U)
    because U only moves slots 0-3 and slot-tracking edge2 watches slots 6-11.
    Cubelet-tracking fixes this: cubelet 8 moves from slot 0 to slot 1 under U."""
    from rubik_solver.model.moves import apply_move
    r_state = apply_move(SOLVED, "R")
    ru_state = apply_move(r_state, "U")
    assert edge2_index(r_state) != edge2_index(ru_state)


def test_pattern_db_admissible_rur_prime_u_prime():
    """Regression: slot-tracking BFS gave h=20 for R U R' U' (4-move state)
    because RU was never enqueued (edge2_index(R)==edge2_index(RU) under old scheme).
    Cubelet-tracking fixes admissibility: h must be <= 4."""
    from rubik_solver.model.moves import apply_move
    state = SOLVED
    for mv in ["R", "U", "R'", "U'"]:
        state = apply_move(state, mv)
    db = PatternDB(max_depth=5)
    assert db.h(state) <= 4
