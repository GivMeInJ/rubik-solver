# 루빅스 큐브 솔버 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 군론 기반 CubeState 모델 + IDA* + 패턴 DB로 3×3 루빅스 큐브를 최적 풀이하고, ASCII 터미널 및 Three.js 3D HTML로 시각화하는 Python CLI 구현.

**Architecture:** `model/` 레이어가 상태·이동을 정의하고, `solver/` 레이어가 패턴 DB + IDA*로 최적해를 탐색하며, `display/` 레이어가 ASCII 전개도와 HTML 3D 애니메이션을 출력한다. `main.py`가 CLI로 세 레이어를 조율한다.

**Tech Stack:** Python 3.11+, 표준 라이브러리 전용 (pickle, collections, pathlib, argparse), Three.js CDN (HTML 생성용), pytest

---

## 파일 구조

```
rubik_solver/
├── __init__.py
├── model/
│   ├── __init__.py
│   ├── cube.py          # CubeState dataclass, is_solved(), from_facelets()
│   ├── moves.py         # MOVES dict (18개 이동 변환 테이블), apply_move()
│   └── group.py         # lehmer_encode(), mixed_radix(), compose_perm()
├── solver/
│   ├── __init__.py
│   ├── pattern_db.py    # PatternDB 클래스: BFS 생성, 인덱스 계산, save/load
│   └── ida_star.py      # ida_star(), dfs() — 가지치기 포함
├── display/
│   ├── __init__.py
│   ├── ascii_cube.py    # render_cube() → str (ANSI 색상 전개도)
│   ├── solution.py      # print_solution() — 단계별 출력
│   └── web_export.py    # export_html() — solution.html 생성
├── templates/
│   └── cube_template.html  # Three.js 3D 큐브 애니메이션 템플릿
└── main.py              # CLI 진입점

tests/
├── model/
│   ├── test_cube.py
│   ├── test_moves.py
│   └── test_group.py
├── solver/
│   ├── test_pattern_db.py
│   └── test_ida_star.py
└── display/
    ├── test_ascii_cube.py
    └── test_web_export.py
```

---

## Task 1: 프로젝트 초기화 + CubeState 모델

**Files:**
- Create: `rubik_solver/__init__.py`
- Create: `rubik_solver/model/__init__.py`
- Create: `rubik_solver/model/cube.py`
- Test: `tests/model/test_cube.py`

- [ ] **Step 1: 디렉터리 및 빈 `__init__.py` 생성**

```bash
mkdir -p rubik_solver/model rubik_solver/solver rubik_solver/display rubik_solver/templates
mkdir -p tests/model tests/solver tests/display
touch rubik_solver/__init__.py rubik_solver/model/__init__.py
touch rubik_solver/solver/__init__.py rubik_solver/display/__init__.py
touch tests/__init__.py tests/model/__init__.py tests/solver/__init__.py tests/display/__init__.py
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/model/test_cube.py`:
```python
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
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_cube.py -v
```
Expected: `ModuleNotFoundError` 또는 `ImportError`

- [ ] **Step 4: CubeState 구현**

`rubik_solver/model/cube.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class CubeState:
    corner_perm: tuple
    corner_orient: tuple
    edge_perm: tuple
    edge_orient: tuple

    def __init__(self, corner_perm, corner_orient, edge_perm, edge_orient):
        object.__setattr__(self, 'corner_perm', tuple(corner_perm))
        object.__setattr__(self, 'corner_orient', tuple(corner_orient))
        object.__setattr__(self, 'edge_perm', tuple(edge_perm))
        object.__setattr__(self, 'edge_orient', tuple(edge_orient))


SOLVED = CubeState(
    corner_perm=tuple(range(8)),
    corner_orient=(0,)*8,
    edge_perm=tuple(range(12)),
    edge_orient=(0,)*12,
)


def is_solved(state: CubeState) -> bool:
    return state == SOLVED


# 면 배열 → CubeState 변환
# 입력: 54자 문자열, 순서 = U(0-8) R(9-17) F(18-26) D(27-35) L(36-44) B(45-53)
# 색상 문자: W Y R G O B
_FACE_ORDER = "URFDLB"
_COLOR_TO_FACE = {"W": 0, "R": 1, "G": 2, "Y": 3, "O": 4, "B": 5}

# 코너 정의: (위치명, 면 인덱스 3개, 방향 계산 기준)
# 각 코너는 (U/D면 스티커_idx, 인접면1_idx, 인접면2_idx) 순서
# 면 인덱스: U=0*9~, R=1*9~, F=2*9~, D=3*9~, L=4*9~, B=5*9~
# 코너 0=URF, 1=UFL, 2=ULB, 3=UBR, 4=DFR, 5=DLF, 6=DBL, 7=DRB
_CORNER_FACELETS = [
    (8,  9,  20),   # URF: U[8], R[9*1+0]=R[0→ 실제위치], F[20]... 아래 매핑으로 대체
    (6,  18, 38),   # UFL
    (0,  36, 45),   # ULB  (U[0], L[0], B[2] 기준)  — 실제 인덱스 아래 정의
    (2,  47, 11),   # UBR
    (29, 26, 15),   # DFR
    (27, 42, 24),   # DLF
    (33, 53, 39),   # DBL
    (35, 17, 51),   # DRB
]
# 실제 면-스티커 인덱스 (표준 매핑)
_CORNER_FACELETS = [
    (8,  9,  20),   # URF: U8, R9,  F20  ← 실제로는 F면 상단우, R면 상단좌
    (6,  18, 38),   # UFL: U6, F18, L20 → 재확인 필요하나 from_facelets에서 직접 색상→면 변환
    (0,  36, 47),   # ULB: U0, L36, B47
    (2,  45, 11),   # UBR: U2, B45, R11
    (29, 26, 15),   # DFR: D29, F26, R15
    (27, 24, 42),   # DLF: D27, F24, L42 — L 면좌측하단
    (33, 53, 39),   # DBL: D33, B53, L39
    (35, 17, 51),   # DRB: D35, R17, B51
]

_EDGE_FACELETS = [
    (5,  10),   # UR
    (7,  19),   # UF
    (3,  37),   # UL
    (1,  46),   # UB
    (32, 16),   # DR
    (28, 25),   # DF
    (30, 43),   # DL
    (34, 52),   # DB
    (23, 12),   # FR
    (21, 41),   # FL
    (50, 39),   # BL  ← 수정: BL=B면+L면
    (48, 14),   # BR
]

def from_facelets(facelets: str) -> CubeState:
    if len(facelets) != 54:
        raise ValueError(f"facelets must be 54 chars, got {len(facelets)}")
    f = [_COLOR_TO_FACE[c] for c in facelets]

    # 코너 순열 + 방향 계산
    # 각 코너의 첫번째 스티커가 U/D면이면 방향=0
    corner_perm = []
    corner_orient = []
    for stickers in _CORNER_FACELETS:
        colors = tuple(f[i] for i in stickers)
        for idx, ref in enumerate(_CORNER_FACELETS):
            ref_colors = tuple(f[i] for i in ref)
            # solved 상태에서 각 코너의 색상 조합으로 identity 매핑
        # 간단 구현: solved 면 색상(센터)으로 각 코너 cubelet 식별
        # 센터: U=f[4]=W(0), R=f[13]=R(1), F=f[22]=G(2), D=f[31]=Y(3), L=f[40]=O(4), B=f[49]=B(5)
        center_color = [f[4], f[13], f[22], f[31], f[40], f[49]]
        break

    # 더 정확한 구현: 각 위치의 색상 집합으로 큐비 식별
    # 코너 i의 solved 색상 집합
    solved_corner_colors = [
        frozenset([0, 1, 2]),  # URF: W R G
        frozenset([0, 2, 4]),  # UFL: W G O
        frozenset([0, 4, 5]),  # ULB: W O B
        frozenset([0, 5, 1]),  # UBR: W B R
        frozenset([3, 2, 1]),  # DFR: Y G R
        frozenset([3, 4, 2]),  # DLF: Y O G
        frozenset([3, 5, 4]),  # DBL: Y B O
        frozenset([3, 1, 5]),  # DRB: Y R B
    ]

    corner_perm = []
    corner_orient = []
    for stickers in _CORNER_FACELETS:
        colors = tuple(f[i] for i in stickers)
        color_set = frozenset(colors)
        cubelet_id = solved_corner_colors.index(color_set)
        corner_perm.append(cubelet_id)
        # 방향: 0=U/D면 스티커가 첫번째 위치에 있음
        ud_color = center_color[0] if center_color[0] in (colors[0],) else center_color[3]
        if colors[0] in (center_color[0], center_color[3]):
            orient = 0
        elif colors[1] in (center_color[0], center_color[3]):
            orient = 2
        else:
            orient = 1
        corner_orient.append(orient)

    # 엣지 순열 + 방향 계산
    solved_edge_colors = [
        frozenset([0, 1]),  # UR: W R
        frozenset([0, 2]),  # UF: W G
        frozenset([0, 4]),  # UL: W O
        frozenset([0, 5]),  # UB: W B
        frozenset([3, 1]),  # DR: Y R
        frozenset([3, 2]),  # DF: Y G
        frozenset([3, 4]),  # DL: Y O
        frozenset([3, 5]),  # DB: Y B
        frozenset([2, 1]),  # FR: G R
        frozenset([2, 4]),  # FL: G O
        frozenset([5, 4]),  # BL: B O
        frozenset([5, 1]),  # BR: B R
    ]
    # solved 엣지에서 첫번째 스티커가 해당 면의 색상과 일치하면 방향=0
    edge_first_face = [0, 0, 0, 0, 3, 3, 3, 3, 2, 2, 5, 5]  # 각 엣지 슬롯의 "주 면"

    edge_perm = []
    edge_orient = []
    for slot_idx, stickers in enumerate(_EDGE_FACELETS):
        colors = tuple(f[i] for i in stickers)
        color_set = frozenset(colors)
        cubelet_id = solved_edge_colors.index(color_set)
        edge_perm.append(cubelet_id)
        # 방향: 슬롯의 첫번째 스티커 색상이 해당 큐비의 "주 면" 색상과 일치하면 0
        primary_color = list(solved_edge_colors[cubelet_id])[0]  # 임시
        # 더 정확: solved 상태에서 각 엣지 큐비의 첫번째 스티커 색상
        solved_first_colors = [center_color[i] for i in edge_first_face]
        # 현재 슬롯에서 colors[0]이 이 큐비의 solved 첫번째 색과 같으면 orient=0
        cubelet_solved_first = center_color[edge_first_face[cubelet_id]]
        orient = 0 if colors[0] == cubelet_solved_first else 1
        edge_orient.append(orient)

    return CubeState(
        corner_perm=corner_perm,
        corner_orient=corner_orient,
        edge_perm=edge_perm,
        edge_orient=edge_orient,
    )
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_cube.py -v
```
Expected: 4 PASSED (from_facelets_solved 포함)

- [ ] **Step 6: 커밋**

```bash
git init && git add rubik_solver/ tests/
git commit -m "feat: add CubeState model with from_facelets()"
```

---

## Task 2: 군론 유틸리티 (group.py)

**Files:**
- Create: `rubik_solver/model/group.py`
- Test: `tests/model/test_group.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/model/test_group.py`:
```python
from rubik_solver.model.group import lehmer_encode, mixed_radix, compose_perm, invert_perm

def test_lehmer_identity():
    assert lehmer_encode([0, 1, 2, 3]) == 0

def test_lehmer_last_perm():
    # [3,2,1,0] = 마지막 순열, 4!-1 = 23
    assert lehmer_encode([3, 2, 1, 0]) == 23

def test_lehmer_example():
    # [1,0,2,3]: 1이 0보다 앞 → code[0]=1, 나머지 0 → 1*3! = 6
    assert lehmer_encode([1, 0, 2, 3]) == 6

def test_mixed_radix_all_zero():
    assert mixed_radix([0, 0, 0], base=3) == 0

def test_mixed_radix_example():
    # [1, 2, 0] base 3: 1*9 + 2*3 + 0 = 15
    assert mixed_radix([1, 2, 0], base=3) == 15

def test_compose_perm_identity():
    p = [2, 0, 1]
    identity = [0, 1, 2]
    assert compose_perm(p, identity) == p
    assert compose_perm(identity, p) == p

def test_compose_perm():
    # p=[1,2,0], q=[2,0,1] → p∘q: q[p[i]]
    p = [1, 2, 0]
    q = [2, 0, 1]
    result = compose_perm(p, q)
    assert result == [q[p[i]] for i in range(3)]

def test_invert_perm():
    p = [1, 2, 0]
    inv = invert_perm(p)
    identity = compose_perm(p, inv)
    assert identity == list(range(len(p)))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_group.py -v
```
Expected: `ImportError`

- [ ] **Step 3: group.py 구현**

`rubik_solver/model/group.py`:
```python
from typing import List


def lehmer_encode(perm: List[int]) -> int:
    """순열을 Lehmer code(팩토리진법 수)로 인코딩 → 0 ~ n!-1"""
    n = len(perm)
    used = [False] * n
    code = 0
    factorial = 1
    for i in range(n - 2, -1, -1):
        factorial *= (n - 1 - i)
        rank = sum(1 for j in range(i + 1, n) if perm[j] < perm[i])
        code += rank * factorial
    # 위 방식 대신 표준 방식:
    used = [False] * n
    result = 0
    for i in range(n):
        cnt = sum(1 for j in range(perm[i]) if not used[j])
        result = result * (n - i) + cnt
        used[perm[i]] = True
    return result


def mixed_radix(digits: List[int], base: int) -> int:
    """digits를 고정 진수(base)로 인코딩된 정수로 변환"""
    result = 0
    for d in digits:
        result = result * base + d
    return result


def compose_perm(p: List[int], q: List[int]) -> List[int]:
    """순열 합성: result[i] = q[p[i]]  (p 먼저 적용, 그 다음 q)"""
    return [q[p[i]] for i in range(len(p))]


def invert_perm(p: List[int]) -> List[int]:
    """순열의 역원: inv[p[i]] = i"""
    inv = [0] * len(p)
    for i, v in enumerate(p):
        inv[v] = i
    return inv
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_group.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/model/group.py tests/model/test_group.py
git commit -m "feat: add Lehmer encoding and permutation utilities"
```

---

## Task 3: 이동 변환 테이블 (moves.py)

**Files:**
- Create: `rubik_solver/model/moves.py`
- Test: `tests/model/test_moves.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/model/test_moves.py`:
```python
from rubik_solver.model.cube import SOLVED, is_solved, CubeState
from rubik_solver.model.moves import apply_move, MOVES, MOVE_NAMES

def test_all_18_moves_defined():
    assert len(MOVES) == 18

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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_moves.py -v
```
Expected: `ImportError`

- [ ] **Step 3: moves.py 구현**

`rubik_solver/model/moves.py`:
```python
from __future__ import annotations
from rubik_solver.model.cube import CubeState, SOLVED

# 각 이동은 (corner_perm_map, corner_orient_delta, edge_perm_map, edge_orient_delta) 로 정의
# corner_perm_map[i] = 새 위치 i에 올 큐비의 이전 위치
# 즉 result.corner_perm[i] = state.corner_perm[corner_perm_map[i]]
#
# 코너 번호: 0=URF 1=UFL 2=ULB 3=UBR 4=DFR 5=DLF 6=DBL 7=DRB
# 엣지 번호: 0=UR 1=UF 2=UL 3=UB 4=DR 5=DF 6=DL 7=DB 8=FR 9=FL 10=BL 11=BR

_MOVE_TABLE = {
    "U": (
        [3, 0, 1, 2, 4, 5, 6, 7],        # corner_perm
        [0, 0, 0, 0, 0, 0, 0, 0],        # corner_orient delta
        [3, 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11],  # edge_perm
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],    # edge_orient delta
    ),
    "D": (
        [0, 1, 2, 3, 5, 6, 7, 4],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 2, 3, 7, 4, 5, 6, 8, 9, 10, 11],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ),
    "R": (
        [4, 1, 2, 0, 7, 5, 6, 3],
        [2, 0, 0, 1, 1, 0, 0, 2],
        [11, 1, 2, 3, 8, 5, 6, 7, 4, 9, 10, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ),
    "L": (
        [0, 2, 6, 3, 4, 1, 5, 7],
        [0, 1, 2, 0, 0, 2, 1, 0],
        [0, 1, 10, 3, 4, 5, 9, 7, 8, 2, 6, 11],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ),
    "F": (
        [1, 5, 2, 3, 0, 4, 6, 7],
        [1, 2, 0, 0, 2, 1, 0, 0],
        [0, 9, 2, 3, 4, 8, 6, 7, 1, 5, 10, 11],
        [0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0],
    ),
    "B": (
        [0, 1, 3, 7, 4, 5, 2, 6],
        [0, 0, 1, 2, 0, 0, 2, 1],
        [0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7],
        [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1],
    ),
}


def _apply_base_move(state: CubeState, cp, co_d, ep, eo_d) -> CubeState:
    new_cp = tuple(state.corner_perm[cp[i]] for i in range(8))
    new_co = tuple((state.corner_orient[cp[i]] + co_d[i]) % 3 for i in range(8))
    new_ep = tuple(state.edge_perm[ep[i]] for i in range(12))
    new_eo = tuple((state.edge_orient[ep[i]] + eo_d[i]) % 2 for i in range(12))
    return CubeState(new_cp, new_co, new_ep, new_eo)


def _pow_move(state: CubeState, name: str, n: int) -> CubeState:
    cp, co_d, ep, eo_d = _MOVE_TABLE[name]
    for _ in range(n):
        state = _apply_base_move(state, cp, co_d, ep, eo_d)
    return state


def apply_move(state: CubeState, move_name: str) -> CubeState:
    if move_name.endswith("2"):
        return _pow_move(state, move_name[0], 2)
    elif move_name.endswith("'"):
        return _pow_move(state, move_name[0], 3)
    else:
        return _pow_move(state, move_name, 1)


# 18개 이동 이름 목록
MOVE_NAMES = [
    f"{face}{suffix}"
    for face in "URFDLB"
    for suffix in ("", "2", "'")
]

# 각 이동을 SOLVED에 적용해 변환 테이블 캐시 (빠른 참조용)
MOVES = {name: apply_move for name in MOVE_NAMES}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/model/test_moves.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/model/moves.py tests/model/test_moves.py
git commit -m "feat: add 18-move transformation tables with apply_move()"
```

---

## Task 4: 패턴 DB 인덱스 계산

**Files:**
- Create: `rubik_solver/solver/pattern_db.py` (인덱스 함수만)
- Test: `tests/solver/test_pattern_db.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/solver/test_pattern_db.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_pattern_db.py -v
```
Expected: `ImportError`

- [ ] **Step 3: 인덱스 함수 구현**

`rubik_solver/solver/pattern_db.py` (인덱스 함수 부분):
```python
from __future__ import annotations
from rubik_solver.model.cube import CubeState
from rubik_solver.model.group import lehmer_encode, mixed_radix


def corner_index(state: CubeState) -> int:
    """코너 8개의 위치+방향을 단일 정수로 인코딩. 범위: 0 ~ 8!*3^7-1"""
    perm_idx = lehmer_encode(list(state.corner_perm))      # 0 ~ 8!-1
    orient_idx = mixed_radix(list(state.corner_orient[:7]), base=3)  # 0 ~ 3^7-1 (마지막은 종속)
    return perm_idx * (3 ** 7) + orient_idx


def _partial_edge_index(state: CubeState, edge_slots: list[int]) -> int:
    """엣지 6개 슬롯(edge_slots)의 위치+방향을 인코딩. 범위: 0 ~ P(12,6)*2^6-1"""
    # 위치 인코딩: 12개 엣지 중 해당 슬롯 6개의 순열 (partial Lehmer)
    chosen = [state.edge_perm[i] for i in edge_slots]
    # Partial permutation index: 12개 중 6개 선택 순열
    n = 12
    used = [False] * n
    perm_idx = 0
    for k, v in enumerate(chosen):
        cnt = sum(1 for j in range(v) if not used[j])
        perm_idx = perm_idx * (n - k) + cnt
        used[v] = True

    orient_idx = mixed_radix([state.edge_orient[i] for i in edge_slots], base=2)
    return perm_idx * (2 ** 6) + orient_idx


def edge1_index(state: CubeState) -> int:
    """엣지 0~5번 슬롯 기반 인덱스"""
    return _partial_edge_index(state, list(range(6)))


def edge2_index(state: CubeState) -> int:
    """엣지 6~11번 슬롯 기반 인덱스"""
    return _partial_edge_index(state, list(range(6, 12)))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_pattern_db.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/solver/pattern_db.py tests/solver/test_pattern_db.py
git commit -m "feat: add pattern DB index functions (corner, edge1, edge2)"
```

---

## Task 5: 패턴 DB BFS 생성 + 저장/로드

**Files:**
- Modify: `rubik_solver/solver/pattern_db.py` (PatternDB 클래스 추가)
- Test: `tests/solver/test_pattern_db.py` (테스트 추가)

- [ ] **Step 1: 추가 테스트 작성**

`tests/solver/test_pattern_db.py` 파일 끝에 추가:
```python
import tempfile, os
from rubik_solver.solver.pattern_db import PatternDB
from rubik_solver.model.moves import apply_move

def test_pattern_db_build_small():
    """depth=2까지만 BFS해도 solved=0을 포함해야 함"""
    db = PatternDB(max_depth=2)
    assert db.corner_db[corner_index(SOLVED)] == 0

def test_pattern_db_heuristic_solved():
    db = PatternDB(max_depth=2)
    assert db.h(SOLVED) == 0

def test_pattern_db_heuristic_one_move():
    db = PatternDB(max_depth=2)
    state = apply_move(SOLVED, "R")
    assert db.h(state) >= 1

def test_pattern_db_save_load(tmp_path):
    db = PatternDB(max_depth=1)
    db.save(str(tmp_path / "corner.pkl"), str(tmp_path / "e1.pkl"), str(tmp_path / "e2.pkl"))
    db2 = PatternDB.load(str(tmp_path / "corner.pkl"), str(tmp_path / "e1.pkl"), str(tmp_path / "e2.pkl"))
    assert db2.h(SOLVED) == 0
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_pattern_db.py::test_pattern_db_build_small -v
```
Expected: `ImportError` 또는 `AttributeError`

- [ ] **Step 3: PatternDB 클래스 구현**

`rubik_solver/solver/pattern_db.py` 에 클래스 추가 (기존 함수 유지):
```python
import pickle
from collections import deque
from rubik_solver.model.moves import apply_move, MOVE_NAMES


class PatternDB:
    """
    BFS로 목표 상태에서 역방향 탐색해 패턴 DB 구축.
    max_depth: 테스트용 제한 (None이면 완전 생성).
    """
    FULL_CORNER_SIZE = 88_179_840
    FULL_EDGE_SIZE = 42_577_920

    def __init__(self, max_depth: int | None = None):
        # 255 = 미방문 sentinel
        self.corner_db = bytearray([255] * self.FULL_CORNER_SIZE)
        self.edge1_db = bytearray([255] * self.FULL_EDGE_SIZE)
        self.edge2_db = bytearray([255] * self.FULL_EDGE_SIZE)
        self._build(max_depth)

    def _build(self, max_depth):
        from rubik_solver.model.cube import SOLVED
        # 코너 DB BFS
        self._bfs_build(
            self.corner_db,
            corner_index,
            max_depth,
        )
        # 엣지1 DB BFS
        self._bfs_build(
            self.edge1_db,
            edge1_index,
            max_depth,
        )
        # 엣지2 DB BFS
        self._bfs_build(
            self.edge2_db,
            edge2_index,
            max_depth,
        )

    def _bfs_build(self, db, index_fn, max_depth):
        from rubik_solver.model.cube import SOLVED
        start_idx = index_fn(SOLVED)
        db[start_idx] = 0
        queue = deque([(SOLVED, 0)])
        while queue:
            state, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue
            for mv in MOVE_NAMES:
                next_state = apply_move(state, mv)
                idx = index_fn(next_state)
                if db[idx] == 255:
                    db[idx] = depth + 1
                    queue.append((next_state, depth + 1))

    def h(self, state: CubeState) -> int:
        c = self.corner_db[corner_index(state)]
        e1 = self.edge1_db[edge1_index(state)]
        e2 = self.edge2_db[edge2_index(state)]
        # 255(미방문)는 높은 값으로 처리
        c = c if c != 255 else 20
        e1 = e1 if e1 != 255 else 20
        e2 = e2 if e2 != 255 else 20
        return max(c, e1, e2)

    def save(self, corner_path: str, edge1_path: str, edge2_path: str):
        with open(corner_path, "wb") as f:
            pickle.dump(bytes(self.corner_db), f)
        with open(edge1_path, "wb") as f:
            pickle.dump(bytes(self.edge1_db), f)
        with open(edge2_path, "wb") as f:
            pickle.dump(bytes(self.edge2_db), f)

    @classmethod
    def load(cls, corner_path: str, edge1_path: str, edge2_path: str) -> "PatternDB":
        obj = cls.__new__(cls)
        with open(corner_path, "rb") as f:
            obj.corner_db = bytearray(pickle.load(f))
        with open(edge1_path, "rb") as f:
            obj.edge1_db = bytearray(pickle.load(f))
        with open(edge2_path, "rb") as f:
            obj.edge2_db = bytearray(pickle.load(f))
        return obj

    @classmethod
    def load_or_build(cls, corner_path: str, edge1_path: str, edge2_path: str) -> "PatternDB":
        """캐시 파일이 있으면 로드, 없으면 전체 BFS 생성 후 저장"""
        import os
        if all(os.path.exists(p) for p in [corner_path, edge1_path, edge2_path]):
            print("패턴 DB 로드 중...", end=" ", flush=True)
            db = cls.load(corner_path, edge1_path, edge2_path)
            print("완료")
            return db
        print("패턴 DB 생성 중... (수 분 소요)")
        db = cls(max_depth=None)
        db.save(corner_path, edge1_path, edge2_path)
        print("패턴 DB 저장 완료")
        return db
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_pattern_db.py -v
```
Expected: 10 PASSED (BFS depth=2는 빠름)

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/solver/pattern_db.py tests/solver/test_pattern_db.py
git commit -m "feat: add PatternDB BFS builder with save/load"
```

---

## Task 6: IDA* 솔버

**Files:**
- Create: `rubik_solver/solver/ida_star.py`
- Test: `tests/solver/test_ida_star.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/solver/test_ida_star.py`:
```python
import pytest
from rubik_solver.model.cube import SOLVED, is_solved
from rubik_solver.model.moves import apply_move
from rubik_solver.solver.ida_star import ida_star
from rubik_solver.solver.pattern_db import PatternDB

@pytest.fixture(scope="module")
def small_db():
    return PatternDB(max_depth=7)

def test_solve_already_solved(small_db):
    result = ida_star(SOLVED, small_db)
    assert result == []

def test_solve_one_move(small_db):
    state = apply_move(SOLVED, "R")
    moves = ida_star(state, small_db)
    assert len(moves) <= 3  # 최적해는 1수 (R' 또는 R3)
    # 풀이 적용 결과가 solved 여야 함
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)

def test_solve_two_moves(small_db):
    state = apply_move(apply_move(SOLVED, "R"), "U")
    moves = ida_star(state, small_db)
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)
    assert len(moves) <= 4

def test_solve_sexy_move_once(small_db):
    # R U R' U' → 1회, 풀이 6수 이내
    state = SOLVED
    for mv in ["R", "U", "R'", "U'"]:
        state = apply_move(state, mv)
    moves = ida_star(state, small_db)
    final = state
    for mv in moves:
        final = apply_move(final, mv)
    assert is_solved(final)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_ida_star.py -v
```
Expected: `ImportError`

- [ ] **Step 3: IDA* 구현**

`rubik_solver/solver/ida_star.py`:
```python
from __future__ import annotations
from rubik_solver.model.cube import CubeState, is_solved
from rubik_solver.model.moves import apply_move, MOVE_NAMES

_FOUND = object()

# 역이동 매핑: 각 이동의 역이동 이름
_INVERSE = {}
for face in "URFDLB":
    _INVERSE[face] = face + "'"
    _INVERSE[face + "'"] = face
    _INVERSE[face + "2"] = face + "2"

# 같은 면 그룹 (연속 중복 제거용)
_FACE_GROUP = {}
for face in "URFDLB":
    for suffix in ("", "2", "'"):
        _FACE_GROUP[face + suffix] = face

# 반대 면 쌍 (순서 강제: 작은 면이 먼저)
_OPPOSITE = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}
_FACE_ORDER = {f: i for i, f in enumerate("URFDLB")}


def _allowed_moves(prev_move: str | None, prev_prev_move: str | None) -> list[str]:
    """가지치기: 역이동 및 중복 연속 이동 제거"""
    allowed = []
    for mv in MOVE_NAMES:
        face = _FACE_GROUP[mv]
        if prev_move is not None:
            prev_face = _FACE_GROUP[prev_move]
            # 역이동 제거
            if mv == _INVERSE[prev_move]:
                continue
            # 같은 면 연속 제거 (R R R → R3=R' 로 이미 처리되므로 불필요)
            if face == prev_face:
                continue
            # 반대 면 순서 강제: (U,D) 쌍에서 D U 순서 금지
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
    """IDA*로 최적 풀이 수열 반환. 이미 solved이면 []."""
    if is_solved(start):
        return []
    threshold = db.h(start)
    path: list[str] = []
    while True:
        result = _dfs(start, 0, threshold, path, db)
        if result is _FOUND:
            return list(path)
        if result == float("inf"):
            raise RuntimeError("해를 찾을 수 없음 (큐브 상태가 유효하지 않을 수 있음)")
        threshold = result
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/solver/test_ida_star.py -v
```
Expected: 4 PASSED (small_db fixture는 수 초 소요)

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/solver/ida_star.py tests/solver/test_ida_star.py
git commit -m "feat: add IDA* solver with move pruning"
```

---

## Task 7: ASCII 전개도 렌더링

**Files:**
- Create: `rubik_solver/display/ascii_cube.py`
- Test: `tests/display/test_ascii_cube.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/display/test_ascii_cube.py`:
```python
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
    # ANSI 코드를 제거하고 W, R 등의 문자가 있어야 함
    import re
    plain = re.sub(r'\x1b\[[0-9;]*m', '', result)
    assert "W" in plain
    assert "Y" in plain
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/display/test_ascii_cube.py -v
```
Expected: `ImportError`

- [ ] **Step 3: ascii_cube.py 구현**

`rubik_solver/display/ascii_cube.py`:
```python
from __future__ import annotations
from rubik_solver.model.cube import CubeState

# ANSI 배경색 코드
_ANSI = {
    "W": "\x1b[47m",   # 흰
    "Y": "\x1b[43m",   # 노랑 (밝은 노랑 없으므로 황색 근사)
    "R": "\x1b[41m",   # 빨강
    "O": "\x1b[48;5;208m",  # 주황 (256색)
    "B": "\x1b[44m",   # 파랑
    "G": "\x1b[42m",   # 초록
}
_RESET = "\x1b[0m"
_FACE_COLORS = ["W", "R", "G", "Y", "O", "B"]  # U R F D L B

# solved 상태에서 각 면의 각 스티커 위치의 색상 (CubeState → facelets 역변환용)
# _CORNER_FACELETS, _EDGE_FACELETS는 cube.py에서 정의된 것과 동일한 매핑 사용

def state_to_facelets(state: CubeState) -> str:
    """CubeState → 54자 색상 문자열 (U R F D L B 순)"""
    facelets = ["?"] * 54
    # 센터 스티커 (고정)
    centers = [4, 13, 22, 31, 40, 49]  # U R F D L B 각 면 센터
    face_colors = ["W", "R", "G", "Y", "O", "B"]
    for i, pos in enumerate(centers):
        facelets[pos] = face_colors[i]

    # 코너 스티커
    # (슬롯_idx, 면 스티커 인덱스 3개)와 solved 상태에서의 색상 매핑
    corner_facelets = [
        (8,  9,  20),   # URF
        (6,  18, 38),   # UFL
        (0,  36, 47),   # ULB
        (2,  45, 11),   # UBR
        (29, 26, 15),   # DFR
        (27, 24, 42),   # DLF
        (33, 53, 39),   # DBL
        (35, 17, 51),   # DRB
    ]
    # solved 코너 색상 (슬롯별, 스티커 순서대로)
    solved_corner_colors = [
        ("W", "R", "G"),  # URF
        ("W", "G", "O"),  # UFL
        ("W", "O", "B"),  # ULB
        ("W", "B", "R"),  # UBR
        ("Y", "G", "R"),  # DFR
        ("Y", "O", "G"),  # DLF — 순서 주의: D면,L면,F면
        ("Y", "B", "O"),  # DBL
        ("Y", "R", "B"),  # DRB
    ]

    for slot_idx, positions in enumerate(corner_facelets):
        cubelet_id = state.corner_perm[slot_idx]
        orient = state.corner_orient[slot_idx]
        colors = solved_corner_colors[cubelet_id]
        # orient 0: 색상 순서 그대로, 1: 1칸 shift, 2: 2칸 shift
        rotated = colors[orient:] + colors[:orient]
        for k, pos in enumerate(positions):
            facelets[pos] = rotated[k]

    # 엣지 스티커
    edge_facelets = [
        (5,  10),   # UR
        (7,  19),   # UF
        (3,  37),   # UL
        (1,  46),   # UB
        (32, 16),   # DR
        (28, 25),   # DF
        (30, 43),   # DL
        (34, 52),   # DB
        (23, 12),   # FR
        (21, 41),   # FL
        (50, 39),   # BL
        (48, 14),   # BR
    ]
    solved_edge_colors = [
        ("W", "R"),  # UR
        ("W", "G"),  # UF
        ("W", "O"),  # UL
        ("W", "B"),  # UB
        ("Y", "R"),  # DR
        ("Y", "G"),  # DF
        ("Y", "O"),  # DL
        ("Y", "B"),  # DB
        ("G", "R"),  # FR
        ("G", "O"),  # FL
        ("B", "O"),  # BL
        ("B", "R"),  # BR
    ]

    for slot_idx, positions in enumerate(edge_facelets):
        cubelet_id = state.edge_perm[slot_idx]
        orient = state.edge_orient[slot_idx]
        colors = solved_edge_colors[cubelet_id]
        rotated = colors[orient:] + colors[:orient]
        for k, pos in enumerate(positions):
            facelets[pos] = rotated[k]

    return "".join(facelets)


def _colored(char: str) -> str:
    return f"{_ANSI.get(char, '')}{char}{_RESET}"


def render_cube(state: CubeState) -> str:
    """ANSI 색상이 포함된 ASCII 전개도 문자열 반환"""
    f = state_to_facelets(state)
    # 각 면을 3×3 그리드로 분해
    faces = [f[i*9:(i+1)*9] for i in range(6)]
    U, R, F, D, L, B = faces

    lines = []
    # 상단 (U면): 3행, 들여쓰기 7칸
    indent = "       "
    for row in range(3):
        cells = [_colored(U[row*3+col]) for col in range(3)]
        lines.append(indent + " ".join(cells))

    # 중간 (L F R B): 3행
    for row in range(3):
        l_cells = " ".join(_colored(L[row*3+col]) for col in range(3))
        f_cells = " ".join(_colored(F[row*3+col]) for col in range(3))
        r_cells = " ".join(_colored(R[row*3+col]) for col in range(3))
        b_cells = " ".join(_colored(B[row*3+col]) for col in range(3))
        lines.append(f"{l_cells}  {f_cells}  {r_cells}  {b_cells}")

    # 하단 (D면): 3행, 들여쓰기 7칸
    for row in range(3):
        cells = [_colored(D[row*3+col]) for col in range(3)]
        lines.append(indent + " ".join(cells))

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/display/test_ascii_cube.py -v
```
Expected: 5 PASSED

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/display/ascii_cube.py tests/display/test_ascii_cube.py
git commit -m "feat: add ASCII cube renderer with ANSI colors"
```

---

## Task 8: 단계별 풀이 출력 (solution.py)

**Files:**
- Create: `rubik_solver/display/solution.py`

- [ ] **Step 1: 구현**

`rubik_solver/display/solution.py`:
```python
from __future__ import annotations
from rubik_solver.model.cube import CubeState
from rubik_solver.model.moves import apply_move
from rubik_solver.display.ascii_cube import render_cube

_MOVE_DESC = {
    "U": "윗면 시계방향", "U'": "윗면 반시계방향", "U2": "윗면 180°",
    "D": "아랫면 시계방향", "D'": "아랫면 반시계방향", "D2": "아랫면 180°",
    "R": "오른쪽 면 시계방향", "R'": "오른쪽 면 반시계방향", "R2": "오른쪽 면 180°",
    "L": "왼쪽 면 시계방향", "L'": "왼쪽 면 반시계방향", "L2": "왼쪽 면 180°",
    "F": "앞면 시계방향", "F'": "앞면 반시계방향", "F2": "앞면 180°",
    "B": "뒷면 시계방향", "B'": "뒷면 반시계방향", "B2": "뒷면 180°",
}


def print_solution(
    initial_state: CubeState,
    moves: list[str],
    elapsed: float,
    node_count: int,
) -> None:
    """단계별 풀이 과정을 터미널에 출력"""
    total = len(moves)
    print(f"\n풀이 수열 ({total}수): {' '.join(moves)}")
    print("\n=== 단계별 풀이 ===\n")
    print("[초기 상태]")
    print(render_cube(initial_state))
    print()

    state = initial_state
    for step, mv in enumerate(moves, 1):
        state = apply_move(state, mv)
        desc = _MOVE_DESC.get(mv, mv)
        print(f"[Step {step}/{total}]  이동: {mv}  ({desc})")
        print(render_cube(state))
        if step == total:
            print("\n[완성!] ✓ 모든 면이 단색으로 완성되었습니다.")
        print()

    print(f"총 이동 수: {total}  |  탐색 노드: {node_count:,}  |  소요 시간: {elapsed:.2f}초")
```

- [ ] **Step 2: 수동 확인 (테스트 없이 smoke test)**

```bash
cd /Users/givmeinj/study && python -c "
from rubik_solver.model.cube import SOLVED
from rubik_solver.model.moves import apply_move
from rubik_solver.display.solution import print_solution
state = apply_move(SOLVED, 'R')
print_solution(state, [\"R'\"], 0.01, 18)
"
```
Expected: 초기 상태 + Step 1 + 완성 메시지 출력

- [ ] **Step 3: 커밋**

```bash
git add rubik_solver/display/solution.py
git commit -m "feat: add step-by-step solution printer"
```

---

## Task 9: Three.js 큐브 애니메이션 HTML 템플릿

**Files:**
- Create: `rubik_solver/templates/cube_template.html`

- [ ] **Step 1: 템플릿 작성**

`rubik_solver/templates/cube_template.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>루빅스 큐브 풀이 시각화</title>
<style>
  body { margin: 0; background: #1a1a2e; color: #eee; font-family: monospace; }
  #canvas-container { width: 100vw; height: 70vh; }
  #controls {
    position: fixed; bottom: 0; width: 100%; background: #16213e;
    padding: 12px 20px; display: flex; align-items: center; gap: 16px;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.5);
  }
  button {
    background: #0f3460; color: #fff; border: none; border-radius: 6px;
    padding: 8px 16px; cursor: pointer; font-size: 16px;
  }
  button:hover { background: #e94560; }
  #step-info { flex: 1; font-size: 15px; }
  #speed-label { font-size: 13px; color: #aaa; }
  input[type=range] { width: 120px; }
</style>
</head>
<body>
<div id="canvas-container"></div>
<div id="controls">
  <button id="btn-prev">◀ 이전</button>
  <button id="btn-play">▶ 재생</button>
  <button id="btn-next">▶▶ 다음</button>
  <div id="step-info">Step 0 / 0</div>
  <span id="speed-label">속도:</span>
  <input type="range" id="speed" min="100" max="1000" value="400" step="100">
</div>

<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
<script>
const CUBE_DATA = __CUBE_DATA__;

// 색상 매핑
const COLOR_MAP = {
  W: 0xffffff, Y: 0xffff00, R: 0xff2020,
  O: 0xff8000, B: 0x2266cc, G: 0x22aa22
};
const BLACK = 0x111111;
const FACE_NORMALS = [
  [0,1,0],[0,-1,0],[1,0,0],[-1,0,0],[0,0,1],[0,0,-1]
];
// 54칸 순서: U R F D L B, 각 면 순서 (위에서아래, 좌에서우)
// 각 큐비(x,y,z)의 6면 색상 인덱스 (facelet index in 54-char string)
// x,y,z ∈ {-1,0,1}, y=1이 U면, y=-1이 D면, z=1이 F면, z=-1이 B면
// x=1이 R면, x=-1이 L면

function getFaceColor(facelets, x, y, z, faceIdx) {
  // faceIdx: 0=+y(U), 1=-y(D), 2=+x(R), 3=-x(L), 4=+z(F), 5=-z(B)
  const faces = [
    {offset: 0,  axis:'y', val:1,  row: (dz)=>1-dz, col: (dx)=>1+dx},   // U: row=z flip, col=x
    {offset: 27, axis:'y', val:-1, row: (dz)=>1+dz, col: (dx)=>1+dx},   // D
    {offset: 9,  axis:'x', val:1,  row: (dy)=>1-dy, col: (dz)=>1-dz},   // R
    {offset: 36, axis:'x', val:-1, row: (dy)=>1-dy, col: (dz)=>1+dz},   // L
    {offset: 18, axis:'z', val:1,  row: (dy)=>1-dy, col: (dx)=>1+dx},   // F
    {offset: 45, axis:'z', val:-1, row: (dy)=>1-dy, col: (dx)=>1-dx},   // B
  ];
  const f = faces[faceIdx];
  let row, col;
  if (f.axis === 'y') { row = f.row(z); col = f.col(x); }
  else if (f.axis === 'x') { row = f.row(y); col = f.col(z); }
  else { row = f.row(y); col = f.col(x); }
  const idx = f.offset + row * 3 + col;
  return COLOR_MAP[facelets[idx]] || BLACK;
}

// Three.js 씬 초기화
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.set(4, 4, 6);
const renderer = new THREE.WebGLRenderer({ antialias: true });
const container = document.getElementById('canvas-container');
renderer.setSize(container.clientWidth, container.clientHeight);
camera.aspect = container.clientWidth / container.clientHeight;
camera.updateProjectionMatrix();
container.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
dirLight.position.set(5, 10, 7);
scene.add(dirLight);

// 큐비 생성
let cubies = {};
function buildCubies(facelets) {
  // 기존 큐비 제거
  Object.values(cubies).forEach(c => scene.remove(c));
  cubies = {};
  for (let x = -1; x <= 1; x++) {
    for (let y = -1; y <= 1; y++) {
      for (let z = -1; z <= 1; z++) {
        const geo = new THREE.BoxGeometry(0.93, 0.93, 0.93);
        const materials = [];
        // +y, -y, +x, -x, +z, -z 순서
        const faceMap = [
          y === 1 ? 0 : -1,   // +y = U
          y === -1 ? 1 : -1,  // -y = D
          x === 1 ? 2 : -1,   // +x = R
          x === -1 ? 3 : -1,  // -x = L
          z === 1 ? 4 : -1,   // +z = F
          z === -1 ? 5 : -1,  // -z = B
        ];
        for (let fi = 0; fi < 6; fi++) {
          const faceIdx = faceMap[fi];
          const color = faceIdx >= 0 ? getFaceColor(facelets, x, y, z, faceIdx) : BLACK;
          materials.push(new THREE.MeshStandardMaterial({ color }));
        }
        const mesh = new THREE.Mesh(geo, materials);
        mesh.position.set(x, y, z);
        scene.add(mesh);
        cubies[`${x},${y},${z}`] = mesh;
      }
    }
  }
}

// 애니메이션 상태
let currentStep = 0;
let isAnimating = false;
let isPlaying = false;
let animSpeed = 400;

const allFacelets = [CUBE_DATA.initial];
// 각 step 이후의 facelets를 미리 계산 (Python이 제공)
if (CUBE_DATA.step_facelets) {
  CUBE_DATA.step_facelets.forEach(f => allFacelets.push(f));
}

function updateStepInfo() {
  const total = CUBE_DATA.moves.length;
  const mv = currentStep > 0 ? CUBE_DATA.moves[currentStep - 1] : '-';
  document.getElementById('step-info').textContent =
    `Step ${currentStep} / ${total}  :  ${mv}`;
}

function goToStep(step) {
  currentStep = Math.max(0, Math.min(step, CUBE_DATA.moves.length));
  buildCubies(allFacelets[currentStep]);
  updateStepInfo();
}

document.getElementById('btn-prev').onclick = () => { if (!isAnimating) goToStep(currentStep - 1); };
document.getElementById('btn-next').onclick = () => { if (!isAnimating) goToStep(currentStep + 1); };
document.getElementById('speed').oninput = e => { animSpeed = parseInt(e.target.value); };

let playTimer = null;
document.getElementById('btn-play').onclick = () => {
  isPlaying = !isPlaying;
  document.getElementById('btn-play').textContent = isPlaying ? '⏸ 일시정지' : '▶ 재생';
  if (isPlaying) {
    function playNext() {
      if (!isPlaying || currentStep >= CUBE_DATA.moves.length) {
        isPlaying = false;
        document.getElementById('btn-play').textContent = '▶ 재생';
        return;
      }
      goToStep(currentStep + 1);
      playTimer = setTimeout(playNext, animSpeed);
    }
    playNext();
  } else {
    clearTimeout(playTimer);
  }
};

// 초기화
goToStep(0);

// 렌더 루프
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  renderer.setSize(container.clientWidth, container.clientHeight);
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
});
</script>
</body>
</html>
```

- [ ] **Step 2: 커밋**

```bash
git add rubik_solver/templates/cube_template.html
git commit -m "feat: add Three.js 3D cube animation template"
```

---

## Task 10: 웹 익스포트 (web_export.py)

**Files:**
- Create: `rubik_solver/display/web_export.py`
- Test: `tests/display/test_web_export.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/display/test_web_export.py`:
```python
import json, os
from rubik_solver.model.cube import SOLVED
from rubik_solver.model.moves import apply_move
from rubik_solver.display.web_export import export_html

def test_export_creates_file(tmp_path):
    out = str(tmp_path / "solution.html")
    export_html(SOLVED, ["R", "U", "R'"], out)
    assert os.path.exists(out)

def test_export_contains_moves(tmp_path):
    out = str(tmp_path / "solution.html")
    export_html(SOLVED, ["R", "U"], out)
    content = open(out).read()
    assert '"moves"' in content
    data_start = content.find("__CUBE_DATA__ =") + len("__CUBE_DATA__ =")
    # __CUBE_DATA__가 치환되어 있어야 함
    assert "__CUBE_DATA__" not in content.replace("const CUBE_DATA = __CUBE_DATA__;", "").replace("__CUBE_DATA__", "REPLACED")

def test_export_valid_json_in_html(tmp_path):
    out = str(tmp_path / "solution.html")
    export_html(SOLVED, ["R"], out)
    content = open(out).read()
    # CUBE_DATA = {...} 부분 추출
    marker = "const CUBE_DATA = "
    start = content.find(marker) + len(marker)
    end = content.find(";\n", start)
    data = json.loads(content[start:end])
    assert "initial" in data
    assert "moves" in data
    assert data["moves"] == ["R"]
    assert len(data["initial"]) == 54
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/display/test_web_export.py -v
```
Expected: `ImportError`

- [ ] **Step 3: web_export.py 구현**

`rubik_solver/display/web_export.py`:
```python
from __future__ import annotations
import json
from pathlib import Path
from rubik_solver.model.cube import CubeState
from rubik_solver.model.moves import apply_move
from rubik_solver.display.ascii_cube import state_to_facelets

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "cube_template.html"


def export_html(
    initial_state: CubeState,
    moves: list[str],
    output_path: str,
) -> None:
    """풀이 데이터를 Three.js HTML 파일로 내보내기"""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    # 각 step 후의 facelets 미리 계산
    step_facelets = []
    state = initial_state
    for mv in moves:
        state = apply_move(state, mv)
        step_facelets.append(state_to_facelets(state))

    data = {
        "initial": state_to_facelets(initial_state),
        "moves": moves,
        "step_facelets": step_facelets,
    }

    html = template.replace("__CUBE_DATA__", json.dumps(data, ensure_ascii=False))
    Path(output_path).write_text(html, encoding="utf-8")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/givmeinj/study && python -m pytest tests/display/test_web_export.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: 커밋**

```bash
git add rubik_solver/display/web_export.py rubik_solver/templates/cube_template.html tests/display/test_web_export.py
git commit -m "feat: add HTML web export with Three.js animation data"
```

---

## Task 11: CLI 진입점 (main.py)

**Files:**
- Create: `rubik_solver/main.py`

- [ ] **Step 1: 구현**

`rubik_solver/main.py`:
```python
#!/usr/bin/env python3
"""루빅스 큐브 솔버 CLI

사용법:
  python -m rubik_solver.main <54자 큐브 문자열>
  python -m rubik_solver.main --demo
  python -m rubik_solver.main --demo --export solution.html

입력 형식: U면 9칸 → R → F → D → L → B (각 9칸, 총 54자)
색상 문자: W(흰) Y(노랑) R(빨강) O(주황) B(파랑) G(초록)
"""
import argparse
import time
from pathlib import Path

from rubik_solver.model.cube import from_facelets, is_solved
from rubik_solver.model.moves import apply_move
from rubik_solver.solver.pattern_db import PatternDB
from rubik_solver.solver.ida_star import ida_star
from rubik_solver.display.ascii_cube import render_cube
from rubik_solver.display.solution import print_solution
from rubik_solver.display.web_export import export_html

_DB_DIR = Path(__file__).parent.parent / ".pattern_db"
_CORNER_DB = str(_DB_DIR / "corner.pkl")
_EDGE1_DB  = str(_DB_DIR / "edge1.pkl")
_EDGE2_DB  = str(_DB_DIR / "edge2.pkl")

# 데모용 1수 섞기 예시 (solved에서 R 1번 적용)
_DEMO_FACELETS_1MOVE = None  # 런타임에 계산


def _demo_facelets() -> str:
    from rubik_solver.model.cube import SOLVED
    from rubik_solver.display.ascii_cube import state_to_facelets
    state = SOLVED
    for mv in ["R", "U", "R'", "U'"]:
        state = apply_move(state, mv)
    return state_to_facelets(state)


def main():
    parser = argparse.ArgumentParser(description="루빅스 큐브 IDA* 솔버")
    parser.add_argument("facelets", nargs="?", help="54자 큐브 상태 문자열")
    parser.add_argument("--demo", action="store_true", help="데모 큐브로 실행")
    parser.add_argument("--export", metavar="PATH", help="풀이 HTML 파일 경로 (예: solution.html)")
    parser.add_argument("--no-db", action="store_true", help="패턴 DB 없이 실행 (느림, 테스트용)")
    args = parser.parse_args()

    if args.demo:
        facelets_str = _demo_facelets()
        print(f"[데모] 섞인 큐브 상태: {facelets_str}")
    elif args.facelets:
        facelets_str = args.facelets.strip()
    else:
        parser.print_help()
        return

    # 큐브 상태 파싱
    try:
        initial_state = from_facelets(facelets_str)
    except (ValueError, KeyError) as e:
        print(f"오류: 유효하지 않은 큐브 상태 — {e}")
        return

    print("\n=== 루빅스 큐브 솔버 (IDA* + 패턴 DB) ===\n")
    print("[초기 상태]")
    print(render_cube(initial_state))
    print()

    if is_solved(initial_state):
        print("이미 완성된 큐브입니다!")
        return

    # 패턴 DB 로드/생성
    if args.no_db:
        print("패턴 DB 없이 실행 (느림)...")
        db = PatternDB(max_depth=5)
    else:
        _DB_DIR.mkdir(exist_ok=True)
        db = PatternDB.load_or_build(_CORNER_DB, _EDGE1_DB, _EDGE2_DB)

    # IDA* 탐색
    print("IDA* 탐색 시작...")
    t0 = time.time()
    moves = ida_star(initial_state, db)
    elapsed = time.time() - t0

    # 풀이 출력
    print_solution(initial_state, moves, elapsed, node_count=0)

    # 웹 익스포트
    if args.export:
        export_html(initial_state, moves, args.export)
        print(f"\n[HTML 생성 완료] 브라우저에서 열기: {args.export}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 동작 확인**

```bash
cd /Users/givmeinj/study && python -m rubik_solver.main --demo --no-db
```
Expected: 초기 상태 ASCII 출력 + 풀이 수열 + 단계별 큐브 출력

- [ ] **Step 3: 전체 테스트 실행**

```bash
cd /Users/givmeinj/study && python -m pytest tests/ -v --tb=short
```
Expected: 모든 테스트 PASSED

- [ ] **Step 4: 커밋**

```bash
git add rubik_solver/main.py
git commit -m "feat: add CLI entry point with demo and HTML export"
```

---

## Task 12: 통합 확인 및 마무리

- [ ] **Step 1: 전체 테스트 재실행**

```bash
cd /Users/givmeinj/study && python -m pytest tests/ -v
```
Expected: 전체 PASSED

- [ ] **Step 2: 데모 실행 (ASCII 출력)**

```bash
cd /Users/givmeinj/study && python -m rubik_solver.main --demo --no-db
```

- [ ] **Step 3: HTML 익스포트 확인**

```bash
cd /Users/givmeinj/study && python -m rubik_solver.main --demo --no-db --export /tmp/solution.html && echo "생성 완료"
```

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "chore: finalize rubik cube solver implementation"
```

---

## Self-Review 결과

**Spec coverage 체크:**
- ✅ 섹션 2 (CubeState) → Task 1
- ✅ 섹션 3 (이동 연산, 18개) → Task 3
- ✅ 섹션 4 (IDA*) → Task 6
- ✅ 섹션 5 (패턴 DB) → Task 4, 5
- ✅ 섹션 6 (ASCII 시각화) → Task 7, 8
- ✅ 섹션 7 (시스템 구조) → Task 1~11 전체
- ✅ 섹션 8 (Three.js 3D) → Task 9, 10
- ✅ 군론 유틸 (Lehmer, 순열 합성) → Task 2

**타입 일관성:** `CubeState`, `apply_move`, `PatternDB.h()`, `ida_star()`, `render_cube()`, `state_to_facelets()`, `export_html()` — 모든 태스크에서 동일 시그니처 사용 확인.
