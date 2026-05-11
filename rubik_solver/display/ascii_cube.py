from __future__ import annotations
from rubik_solver.model.cube import CubeState

_ANSI = {
    "W": "\x1b[47m",
    "Y": "\x1b[43m",
    "R": "\x1b[41m",
    "O": "\x1b[48;5;208m",
    "B": "\x1b[44m",
    "G": "\x1b[42m",
}
_RESET = "\x1b[0m"

_CORNER_FACELETS = [
    (8,  9,  20),
    (6,  18, 38),
    (0,  36, 47),
    (2,  45, 11),
    (29, 26, 15),
    (27, 24, 44),
    (33, 53, 42),
    (35, 17, 51),
]

_CORNER_COLORS = [
    ("W", "R", "G"),
    ("W", "G", "O"),
    ("W", "O", "B"),
    ("W", "B", "R"),
    ("Y", "G", "R"),
    ("Y", "G", "O"),
    ("Y", "B", "O"),
    ("Y", "R", "B"),
]

_EDGE_FACELETS = [
    (5,  10), (7,  19), (3,  37), (1,  46),
    (32, 16), (28, 25), (30, 43), (34, 52),
    (23, 12), (21, 41), (50, 39), (48, 14),
]

_EDGE_COLORS = [
    ("W", "R"), ("W", "G"), ("W", "O"), ("W", "B"),
    ("Y", "R"), ("Y", "G"), ("Y", "O"), ("Y", "B"),
    ("G", "R"), ("G", "O"), ("B", "O"), ("B", "R"),
]


def state_to_facelets(state: CubeState) -> str:
    facelets = ["?"] * 54
    centers = [4, 13, 22, 31, 40, 49]
    face_colors = ["W", "R", "G", "Y", "O", "B"]
    for i, pos in enumerate(centers):
        facelets[pos] = face_colors[i]

    for slot_idx, positions in enumerate(_CORNER_FACELETS):
        cubelet_id = state.corner_perm[slot_idx]
        orient = state.corner_orient[slot_idx]
        colors = _CORNER_COLORS[cubelet_id]
        rotated = colors[-orient:] + colors[:-orient]
        for k, pos in enumerate(positions):
            facelets[pos] = rotated[k]

    for slot_idx, positions in enumerate(_EDGE_FACELETS):
        cubelet_id = state.edge_perm[slot_idx]
        orient = state.edge_orient[slot_idx]
        colors = _EDGE_COLORS[cubelet_id]
        rotated = colors[orient:] + colors[:orient]
        for k, pos in enumerate(positions):
            facelets[pos] = rotated[k]

    return "".join(facelets)


def _colored(char: str) -> str:
    return f"{_ANSI.get(char, '')}{char}{_RESET}"


def render_cube(state: CubeState) -> str:
    f = state_to_facelets(state)
    faces = [f[i*9:(i+1)*9] for i in range(6)]
    U, R, F, D, L, B = faces

    lines = []
    indent = "       "
    for row in range(3):
        cells = [_colored(U[row*3+col]) for col in range(3)]
        lines.append(indent + " ".join(cells))

    for row in range(3):
        l_cells = " ".join(_colored(L[row*3+col]) for col in range(3))
        f_cells = " ".join(_colored(F[row*3+col]) for col in range(3))
        r_cells = " ".join(_colored(R[row*3+col]) for col in range(3))
        b_cells = " ".join(_colored(B[row*3+col]) for col in range(3))
        lines.append(f"{l_cells}  {f_cells}  {r_cells}  {b_cells}")

    for row in range(3):
        cells = [_colored(D[row*3+col]) for col in range(3)]
        lines.append(indent + " ".join(cells))

    return "\n".join(lines)
