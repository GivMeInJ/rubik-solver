from __future__ import annotations
from rubik_solver.model.cube import CubeState, is_solved
from rubik_solver.model.moves import apply_move, MOVE_NAMES

_FOUND = object()

_INVERSE = {}
for _face in "URFDLB":
    _INVERSE[_face] = _face + "'"
    _INVERSE[_face + "'"] = _face
    _INVERSE[_face + "2"] = _face + "2"

_FACE_GROUP = {}
for _face in "URFDLB":
    for _suffix in ("", "2", "'"):
        _FACE_GROUP[_face + _suffix] = _face

_OPPOSITE = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}


def _allowed_moves(prev_move: str | None, prev_prev_move: str | None) -> list[str]:
    allowed = []
    for mv in MOVE_NAMES:
        face = _FACE_GROUP[mv]
        if prev_move is not None:
            prev_face = _FACE_GROUP[prev_move]
            if mv == _INVERSE[prev_move]:
                continue
            if face == prev_face:
                continue
            if prev_prev_move is not None:
                ppface = _FACE_GROUP[prev_prev_move]
                if _OPPOSITE.get(face) == prev_face and ppface == face:
                    continue
        allowed.append(mv)
    return allowed


def _dfs(
    state: CubeState,
    g: int,
    threshold: int,
    path: list[str],
    db,
) -> int | object:
    f = g + db.h(state)
    if f > threshold:
        return f
    if is_solved(state):
        return _FOUND
    min_t = float("inf")
    prev = path[-1] if path else None
    prev_prev = path[-2] if len(path) >= 2 else None
    for mv in _allowed_moves(prev, prev_prev):
        new_state = apply_move(state, mv)
        path.append(mv)
        result = _dfs(new_state, g + 1, threshold, path, db)
        if result is _FOUND:
            return _FOUND
        if isinstance(result, (int, float)):
            min_t = min(min_t, result)
        path.pop()
    return min_t


def ida_star(start: CubeState, db) -> list[str]:
    """Return optimal move sequence to solve start. Returns [] if already solved."""
    if is_solved(start):
        return []
    threshold = db.h(start)
    path: list[str] = []
    while True:
        result = _dfs(start, 0, threshold, path, db)
        if result is _FOUND:
            return list(path)
        if result == float("inf"):
            raise RuntimeError("No solution found — cube state may be invalid")
        threshold = result
