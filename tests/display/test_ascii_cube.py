from rubik_solver.model.cube import SOLVED
from rubik_solver.display.ascii_cube import render_cube, state_to_facelets

def test_render_returns_string():
    result = render_cube(SOLVED)
    assert isinstance(result, str)

def test_render_has_9_rows():
    result = render_cube(SOLVED)
    lines = result.strip().split("\n")
    assert len(lines) == 9

def test_state_to_facelets_solved_length():
    f = state_to_facelets(SOLVED)
    assert len(f) == 54

def test_state_to_facelets_solved_colors():
    f = state_to_facelets(SOLVED)
    # U면(0-8)=W, R면(9-17)=R, F면(18-26)=G, D면(27-35)=Y, L면(36-44)=O, B면(45-53)=B
    assert all(c == "W" for c in f[0:9])
    assert all(c == "R" for c in f[9:18])
    assert all(c == "G" for c in f[18:27])
    assert all(c == "Y" for c in f[27:36])
    assert all(c == "O" for c in f[36:45])
    assert all(c == "B" for c in f[45:54])

def test_render_contains_face_letters():
    result = render_cube(SOLVED)
    import re
    plain = re.sub(r'\x1b\[[0-9;]*m', '', result)
    assert "W" in plain
    assert "Y" in plain
