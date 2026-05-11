import pytest
from rubik_solver.model.cube import CubeState, SOLVED, is_solved, from_facelets

def test_solved_state_is_solved():
    assert is_solved(SOLVED)

def test_new_cubestate_equality():
    s1 = CubeState(
        corner_perm=list(range(8)),
        corner_orient=[0]*8,
        edge_perm=list(range(12)),
        edge_orient=[0]*12,
    )
    assert s1 == SOLVED

def test_cubestate_hashable():
    s = {SOLVED}
    assert SOLVED in s

def test_from_facelets_solved():
    # 표준 전개도: U=W, R=R, F=G, D=Y, L=O, B=B (각 9칸)
    facelets = "W"*9 + "R"*9 + "G"*9 + "Y"*9 + "O"*9 + "B"*9
    state = from_facelets(facelets)
    assert is_solved(state)

def test_from_facelets_wrong_length():
    with pytest.raises(ValueError, match="54"):
        from_facelets("W" * 53)
