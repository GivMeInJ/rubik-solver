import pytest
from rubik_solver.model.cube import SOLVED, is_solved
from rubik_solver.model.moves import apply_move, MOVE_NAMES

def test_all_18_moves_defined():
    assert len(MOVE_NAMES) == 18

def test_move_names_defined():
    expected = {"U","U2","U'","D","D2","D'","R","R2","R'",
                "L","L2","L'","F","F2","F'","B","B2","B'"}
    assert set(MOVE_NAMES) == expected

def test_r_move_changes_state():
    state = apply_move(SOLVED, "R")
    assert not is_solved(state)

def test_r4_returns_solved():
    state = SOLVED
    for _ in range(4):
        state = apply_move(state, "R")
    assert is_solved(state)

def test_u4_returns_solved():
    state = SOLVED
    for _ in range(4):
        state = apply_move(state, "U")
    assert is_solved(state)

def test_sexy_move_returns_solved():
    # (R U R' U') × 6 = identity
    state = SOLVED
    for _ in range(6):
        for mv in ["R", "U", "R'", "U'"]:
            state = apply_move(state, mv)
    assert is_solved(state)

def test_r2_equals_r_r():
    s1 = apply_move(apply_move(SOLVED, "R"), "R")
    s2 = apply_move(SOLVED, "R2")
    assert s1 == s2

def test_r_prime_equals_r3():
    state = SOLVED
    for _ in range(3):
        state = apply_move(state, "R")
    s_r3 = state
    s_rprime = apply_move(SOLVED, "R'")
    assert s_r3 == s_rprime


@pytest.mark.parametrize("face", ["U", "D", "R", "L", "F", "B"])
def test_face_order_4(face):
    state = SOLVED
    for _ in range(4):
        state = apply_move(state, face)
    assert is_solved(state)


@pytest.mark.parametrize("face", ["U", "D", "R", "L", "F", "B"])
def test_face_inverse(face):
    state = apply_move(apply_move(SOLVED, face), face + "'")
    assert is_solved(state)


def test_apply_move_invalid():
    with pytest.raises(ValueError, match="Unknown move"):
        apply_move(SOLVED, "X")
    with pytest.raises(ValueError, match="Unknown move"):
        apply_move(SOLVED, "U2'")
