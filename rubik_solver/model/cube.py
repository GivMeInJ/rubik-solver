"""
CubeState model for Rubik's Cube solver.

Coordinate system:
  Faces: U=0, R=1, F=2, D=3, L=4, B=5
  Colors: W=0, R=1, G=2, Y=3, O=4, B=5

  Corners (0-7): URF UFL ULB UBR DFR DLF DBL DRB
  Edges  (0-11): UR  UF  UL  UB  DR  DF  DL  DB  FR  FL  BL  BR
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Sticker index tables
# ---------------------------------------------------------------------------

# Each corner slot: (first_sticker, second_sticker, third_sticker)
# Indices into the 54-char facelet string (U[0-8] R[9-17] F[18-26] D[27-35] L[36-44] B[45-53])
_CORNER_FACELETS = [
    (8,  9,  20),   # 0 URF: U[8], R[0], F[2]
    (6,  18, 38),   # 1 UFL: U[6], F[0], L[2]
    (0,  36, 47),   # 2 ULB: U[0], L[0], B[2]
    (2,  45, 11),   # 3 UBR: U[2], B[0], R[2]
    (29, 26, 15),   # 4 DFR: D[2], F[8], R[6]
    (27, 24, 44),   # 5 DLF: D[0], F[6], L[8] -- L[8]=44
    (33, 53, 42),   # 6 DBL: D[6], B[8], L[6] -- L[6]=42
    (35, 17, 51),   # 7 DRB: D[8], R[8], B[6]
]

# Each edge slot: (first_sticker, second_sticker)
_EDGE_FACELETS = [
    (5,  10),   #  0 UR:  U[5], R[1]
    (7,  19),   #  1 UF:  U[7], F[1]
    (3,  37),   #  2 UL:  U[3], L[1]
    (1,  46),   #  3 UB:  U[1], B[1]
    (32, 16),   #  4 DR:  D[5], R[7]
    (28, 25),   #  5 DF:  D[1], F[7]
    (30, 43),   #  6 DL:  D[3], L[7]
    (34, 52),   #  7 DB:  D[7], B[7]
    (23, 12),   #  8 FR:  F[5], R[3]
    (21, 41),   #  9 FL:  F[3], L[5]
    (50, 39),   # 10 BL:  B[5], L[3]  -- B[5]=50, L[3]=39
    (48, 14),   # 11 BR:  B[3], R[5]
]

# Solved colors for each corner cubelet (matches corner numbering above)
_SOLVED_CORNER_COLORS = [
    ("W", "R", "G"),  # 0 URF
    ("W", "G", "O"),  # 1 UFL
    ("W", "O", "B"),  # 2 ULB
    ("W", "B", "R"),  # 3 UBR
    ("Y", "G", "R"),  # 4 DFR
    ("Y", "O", "G"),  # 5 DLF
    ("Y", "B", "O"),  # 6 DBL
    ("Y", "R", "B"),  # 7 DRB
]

# Solved colors for each edge cubelet
_SOLVED_EDGE_COLORS = [
    ("W", "R"),  #  0 UR
    ("W", "G"),  #  1 UF
    ("W", "O"),  #  2 UL
    ("W", "B"),  #  3 UB
    ("Y", "R"),  #  4 DR
    ("Y", "G"),  #  5 DF
    ("Y", "O"),  #  6 DL
    ("Y", "B"),  #  7 DB
    ("G", "R"),  #  8 FR
    ("G", "O"),  #  9 FL
    ("B", "O"),  # 10 BL
    ("B", "R"),  # 11 BR
]

# Pre-build frozenset lookup for fast identification
_CORNER_COLOR_SETS = [frozenset(c) for c in _SOLVED_CORNER_COLORS]
_EDGE_COLOR_SETS   = [frozenset(e) for e in _SOLVED_EDGE_COLORS]


# ---------------------------------------------------------------------------
# CubeState dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CubeState:
    """
    Immutable, hashable representation of a Rubik's Cube state.

    corner_perm  : tuple[int, 8]   – which cubelet sits in each corner slot
    corner_orient: tuple[int, 8]   – orientation of that cubelet (0/1/2)
    edge_perm    : tuple[int, 12]  – which cubelet sits in each edge slot
    edge_orient  : tuple[int, 12]  – flip state (0 = unflipped, 1 = flipped)
    """
    corner_perm:   tuple
    corner_orient: tuple
    edge_perm:     tuple
    edge_orient:   tuple

    def __post_init__(self) -> None:
        # frozen=True means we must use object.__setattr__ to normalise
        # list inputs to tuples so the instance is always hashable.
        object.__setattr__(self, "corner_perm",   tuple(self.corner_perm))
        object.__setattr__(self, "corner_orient", tuple(self.corner_orient))
        object.__setattr__(self, "edge_perm",     tuple(self.edge_perm))
        object.__setattr__(self, "edge_orient",   tuple(self.edge_orient))
        if len(self.corner_perm) != 8:
            raise ValueError(f"corner_perm must have 8 elements, got {len(self.corner_perm)}")
        if len(self.corner_orient) != 8:
            raise ValueError(f"corner_orient must have 8 elements, got {len(self.corner_orient)}")
        if len(self.edge_perm) != 12:
            raise ValueError(f"edge_perm must have 12 elements, got {len(self.edge_perm)}")
        if len(self.edge_orient) != 12:
            raise ValueError(f"edge_orient must have 12 elements, got {len(self.edge_orient)}")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SOLVED = CubeState(
    corner_perm=tuple(range(8)),
    corner_orient=(0,) * 8,
    edge_perm=tuple(range(12)),
    edge_orient=(0,) * 12,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def is_solved(state: CubeState) -> bool:
    """Return True iff *state* is the identity (solved) position."""
    return state == SOLVED


def from_facelets(facelets: str) -> CubeState:
    """
    Convert a 54-character colour string into a CubeState.

    Input order: U(0-8) R(9-17) F(18-26) D(27-35) L(36-44) B(45-53)
    Colour chars: W R G Y O B

    Raises ValueError if *facelets* is not exactly 54 characters.
    """
    if len(facelets) != 54:
        raise ValueError(
            f"facelets string must be exactly 54 characters, got {len(facelets)}"
        )

    f = facelets  # shorthand

    # Centre colours define face identity
    center_colors = [f[4], f[13], f[22], f[31], f[40], f[49]]  # U R F D L B
    ud_colors = {center_colors[0], center_colors[3]}            # typically W, Y

    # --- Corners ---
    corner_perm   = [0] * 8
    corner_orient = [0] * 8

    for slot, stickers in enumerate(_CORNER_FACELETS):
        colors = tuple(f[i] for i in stickers)
        color_set = frozenset(colors)

        try:
            cubelet_id = _CORNER_COLOR_SETS.index(color_set)
        except ValueError:
            raise ValueError(
                f"Corner slot {slot} has unrecognised colour set {color_set!r}"
            )

        corner_perm[slot] = cubelet_id

        # Orientation: which twist position holds a U/D-face colour?
        if colors[0] in ud_colors:
            orient = 0
        elif colors[1] in ud_colors:
            orient = 1
        else:
            orient = 2
        corner_orient[slot] = orient

    # --- Edges ---
    edge_perm   = [0] * 12
    edge_orient = [0] * 12

    for slot, stickers in enumerate(_EDGE_FACELETS):
        colors = tuple(f[i] for i in stickers)
        color_set = frozenset(colors)

        try:
            cubelet_id = _EDGE_COLOR_SETS.index(color_set)
        except ValueError:
            raise ValueError(
                f"Edge slot {slot} has unrecognised colour set {color_set!r}"
            )

        edge_perm[slot] = cubelet_id

        # Orientation: 0 if first sticker matches solved-first colour, else 1
        solved_first = _SOLVED_EDGE_COLORS[cubelet_id][0]
        edge_orient[slot] = 0 if colors[0] == solved_first else 1

    return CubeState(
        corner_perm=corner_perm,
        corner_orient=corner_orient,
        edge_perm=edge_perm,
        edge_orient=edge_orient,
    )
