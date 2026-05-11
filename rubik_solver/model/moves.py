"""
Move transformation tables for Rubik's Cube solver.

Defines 18 moves (6 faces × {1, 2, '}) using Kociemba coordinate convention.

Corner numbering: 0=URF 1=UFL 2=ULB 3=UBR 4=DFR 5=DLF 6=DBL 7=DRB
Edge numbering:   0=UR  1=UF  2=UL  3=UB  4=DR  5=DF  6=DL  7=DB
                  8=FR  9=FL  10=BL 11=BR
"""

from __future__ import annotations
from rubik_solver.model.cube import CubeState

# ---------------------------------------------------------------------------
# 18 move names
# ---------------------------------------------------------------------------

MOVE_NAMES: list[str] = [
    "U", "U2", "U'",
    "D", "D2", "D'",
    "R", "R2", "R'",
    "L", "L2", "L'",
    "F", "F2", "F'",
    "B", "B2", "B'",
]

# ---------------------------------------------------------------------------
# Base move tables
# Each entry: (corner_perm_map, corner_orient_delta, edge_perm_map, edge_orient_delta)
# ---------------------------------------------------------------------------

# U: rotates top face clockwise viewed from top
# Corner cycle: UBR→URF→UFL→ULB→UBR  (slot 3→0→1→2→3)
U_cp = [3, 0, 1, 2, 4, 5, 6, 7]
U_co = [0] * 8
U_ep = [3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11]
U_eo = [0] * 12

# D: rotates bottom face clockwise viewed from bottom
# Corner cycle: DLF→DFR→DRB→DBL→DLF  (slot 5→4→7→6→5)
D_cp = [0, 1, 2, 3, 5, 6, 7, 4]
D_co = [0] * 8
D_ep = [0, 1, 2, 3, 7, 4, 5, 6, 8, 9, 10, 11]
D_eo = [0] * 12

# R: rotates right face clockwise viewed from right
# Corner cycle: URF→DFR→DRB→UBR→URF  (slot 0→4→7→3→0)
R_cp = [4, 1, 2, 0, 7, 5, 6, 3]
R_co = [2, 0, 0, 1, 1, 0, 0, 2]
# Edge cycle: UR→BR→DR→FR→UR  (slot 0→11→4→8→0)
R_ep = [8, 1, 2, 3, 11, 5, 6, 7, 4, 9, 10, 0]
R_eo = [0] * 12

# L: rotates left face clockwise viewed from left
# Corner cycle: UFL→ULB→DBL→DLF→UFL  (slot 1→2→6→5→1)
L_cp = [0, 2, 6, 3, 4, 1, 5, 7]
L_co = [0, 1, 2, 0, 0, 2, 1, 0]
# Edge cycle: UL→BL→DL→FL→UL  (slot 2→10→6→9→2)
L_ep = [0, 1, 9, 3, 4, 5, 10, 7, 8, 6, 2, 11]
L_eo = [0] * 12

# F: rotates front face clockwise viewed from front
# Corner cycle: UFL→URF→DFR→DLF→UFL  (slot 1→0→4→5→1)
F_cp = [1, 5, 2, 3, 0, 4, 6, 7]
F_co = [1, 2, 0, 0, 2, 1, 0, 0]
# Edge cycle: UF→FR→DF→FL→UF  (slot 1→8→5→9→1)
F_ep = [0, 9, 2, 3, 4, 8, 6, 7, 1, 5, 10, 11]
F_eo = [0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0]

# B: rotates back face clockwise viewed from back
# Corner cycle: UBR→ULB→DBL→DRB→UBR  (slot 3→2→6→7→3)
B_cp = [0, 1, 3, 7, 4, 5, 2, 6]
B_co = [0, 0, 1, 2, 0, 0, 2, 1]
# Edge cycle: UB→BL→DB→BR→UB  (slot 3→10→7→11→3)
B_ep = [0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7]
B_eo = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1]

# Map face letter → (cp, co, ep, eo)
_BASE_MOVES: dict[str, tuple] = {
    "U": (U_cp, U_co, U_ep, U_eo),
    "D": (D_cp, D_co, D_ep, D_eo),
    "R": (R_cp, R_co, R_ep, R_eo),
    "L": (L_cp, L_co, L_ep, L_eo),
    "F": (F_cp, F_co, F_ep, F_eo),
    "B": (B_cp, B_co, B_ep, B_eo),
}


# ---------------------------------------------------------------------------
# Core application functions
# ---------------------------------------------------------------------------

def _apply_base(state: CubeState, face: str) -> CubeState:
    """Apply a single quarter-turn of *face* to *state*."""
    cp, co_d, ep, eo_d = _BASE_MOVES[face]
    new_cp = tuple(state.corner_perm[cp[i]] for i in range(8))
    new_co = tuple((state.corner_orient[cp[i]] + co_d[i]) % 3 for i in range(8))
    new_ep = tuple(state.edge_perm[ep[i]] for i in range(12))
    new_eo = tuple((state.edge_orient[ep[i]] + eo_d[i]) % 2 for i in range(12))
    return CubeState(new_cp, new_co, new_ep, new_eo)


def apply_move(state: CubeState, move_name: str) -> CubeState:
    """
    Apply a named move to *state* and return the new CubeState.

    Supported names: U U2 U' D D2 D' R R2 R' L L2 L' F F2 F' B B2 B'
    """
    if move_name.endswith("2"):
        base = move_name[0]
        state = _apply_base(state, base)
        return _apply_base(state, base)
    elif move_name.endswith("'"):
        base = move_name[0]
        state = _apply_base(state, base)
        state = _apply_base(state, base)
        return _apply_base(state, base)
    else:
        return _apply_base(state, move_name)
