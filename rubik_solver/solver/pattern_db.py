from __future__ import annotations
import os
import pickle
from collections import deque

from rubik_solver.model.cube import CubeState, SOLVED
from rubik_solver.model.moves import apply_move, MOVE_NAMES

_EDGE1_CUBELETS = tuple(range(6))
_EDGE2_CUBELETS = tuple(range(6, 12))
_CORNER_ORIENT_MULT = 3 ** 7
_EDGE_ORIENT_MULT   = 2 ** 6

# Precomputed rank tables: _RC8[mask][v]  = count of values < v not yet used (8-element universe)
#                          _RC12[mask][v] = same for 12-element universe
# Replaces the O(v) generator loop with O(1) table lookup.
_RC8  = [[v - bin(mask & ((1 << v) - 1)).count('1') for v in range(8)]
         for mask in range(256)]
_RC12 = [[v - bin(mask & ((1 << v) - 1)).count('1') for v in range(12)]
         for mask in range(4096)]


def corner_index(state: CubeState) -> int:
    mask = 0
    perm_idx = 0
    for k in range(8):
        v = state.corner_perm[k]
        perm_idx = perm_idx * (8 - k) + _RC8[mask][v]
        mask |= (1 << v)
    orient_idx = 0
    for d in state.corner_orient[:7]:
        orient_idx = orient_idx * 3 + d
    return perm_idx * _CORNER_ORIENT_MULT + orient_idx


def _partial_edge_index(state: CubeState, target_cubelets: tuple) -> int:
    """특정 cubelet 6개의 슬롯 위치+방향을 인코딩 (cubelet 추적 방식).

    슬롯 추적이 아닌 cubelet 추적: 각 cubelet의 새 위치는 해당 cubelet의
    이전 위치에만 의존하므로 BFS에서 Markov 성질을 보장한다.
    범위: 0 ~ P(12,6)*2^6-1 = 42,577,919
    """
    slot_of = [0] * 12
    orient_of = [0] * 12
    for slot in range(12):
        c = state.edge_perm[slot]
        slot_of[c] = slot
        orient_of[c] = state.edge_orient[slot]

    mask = 0
    perm_idx = 0
    for k, c in enumerate(target_cubelets):
        v = slot_of[c]
        perm_idx = perm_idx * (12 - k) + _RC12[mask][v]
        mask |= (1 << v)

    orient_idx = 0
    for c in target_cubelets:
        orient_idx = orient_idx * 2 + orient_of[c]
    return perm_idx * _EDGE_ORIENT_MULT + orient_idx


def edge1_index(state: CubeState) -> int:
    """엣지 cubelet 0~5번의 위치+방향 인덱스"""
    return _partial_edge_index(state, _EDGE1_CUBELETS)


def edge2_index(state: CubeState) -> int:
    """엣지 cubelet 6~11번의 위치+방향 인덱스"""
    return _partial_edge_index(state, _EDGE2_CUBELETS)


class PatternDB:
    """BFS로 목표 상태에서 역방향 탐색해 패턴 DB 구축.

    max_depth: 테스트용 BFS 깊이 제한 (None이면 완전 생성).
    255 = 미방문 sentinel.
    """
    CORNER_SIZE = 88_179_840   # 8! * 3^7
    EDGE_SIZE   = 42_577_920   # P(12,6) * 2^6

    def __init__(self, max_depth: int | None = None):
        self.corner_db = bytearray(b'\xff' * self.CORNER_SIZE)
        self.edge1_db  = bytearray(b'\xff' * self.EDGE_SIZE)
        self.edge2_db  = bytearray(b'\xff' * self.EDGE_SIZE)
        self._bfs(self.corner_db, corner_index, max_depth)
        self._bfs(self.edge1_db,  edge1_index,  max_depth)
        self._bfs(self.edge2_db,  edge2_index,  max_depth)

    @staticmethod
    def _bfs(db: bytearray, index_fn, max_depth: int | None) -> None:
        start_idx = index_fn(SOLVED)
        db[start_idx] = 0
        queue: deque = deque([(SOLVED, 0)])
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
        """admissible 휴리스틱: 세 DB 중 최댓값 (255=미방문 → 20으로 대체)"""
        def _lookup(db, idx):
            v = db[idx]
            return 20 if v == 255 else v
        return max(
            _lookup(self.corner_db, corner_index(state)),
            _lookup(self.edge1_db,  edge1_index(state)),
            _lookup(self.edge2_db,  edge2_index(state)),
        )

    def save(self, corner_path: str, edge1_path: str, edge2_path: str) -> None:
        for path, data in [(corner_path, self.corner_db),
                           (edge1_path,  self.edge1_db),
                           (edge2_path,  self.edge2_db)]:
            with open(path, "wb") as f:
                pickle.dump(bytes(data), f)

    @classmethod
    def load(cls, corner_path: str, edge1_path: str, edge2_path: str) -> "PatternDB":
        obj = cls.__new__(cls)
        for attr, path in [("corner_db", corner_path),
                            ("edge1_db",  edge1_path),
                            ("edge2_db",  edge2_path)]:
            with open(path, "rb") as f:
                setattr(obj, attr, bytearray(pickle.load(f)))
        return obj

    @classmethod
    def load_or_build(cls, corner_path: str, edge1_path: str,
                      edge2_path: str) -> "PatternDB":
        """캐시 파일이 있으면 로드, 없으면 병렬 BFS 생성 후 저장."""
        if all(os.path.exists(p) for p in [corner_path, edge1_path, edge2_path]):
            print("패턴 DB 로드 중...", end=" ", flush=True)
            db = cls.load(corner_path, edge1_path, edge2_path)
            print("완료")
            return db
        print("패턴 DB 생성 중... (30~40분 소요)")
        db = cls(max_depth=None)
        db.save(corner_path, edge1_path, edge2_path)
        print("패턴 DB 저장 완료")
        return db
