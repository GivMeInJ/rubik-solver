from __future__ import annotations
import os
import pickle
from collections import deque

from rubik_solver.model.cube import CubeState, SOLVED
from rubik_solver.model.group import lehmer_encode, mixed_radix
from rubik_solver.model.moves import apply_move, MOVE_NAMES

_EDGE1_CUBELETS = tuple(range(6))      # cubelets 0-5
_EDGE2_CUBELETS = tuple(range(6, 12))  # cubelets 6-11
_CORNER_ORIENT_MULT = 3 ** 7     # 2187
_EDGE_ORIENT_MULT   = 2 ** 6     # 64


def corner_index(state: CubeState) -> int:
    """코너 8개의 위치+방향을 단일 정수로 인코딩. 범위: 0 ~ 8!*3^7-1"""
    perm_idx = lehmer_encode(list(state.corner_perm))
    orient_idx = mixed_radix(list(state.corner_orient[:7]), base=3)
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

    # P(12,6) partial permutation rank over 12-element universe
    n = 12
    used = [False] * n
    perm_idx = 0
    for k, c in enumerate(target_cubelets):
        v = slot_of[c]
        cnt = sum(1 for j in range(v) if not used[j])
        perm_idx = perm_idx * (n - k) + cnt
        used[v] = True

    orient_idx = mixed_radix([orient_of[c] for c in target_cubelets], base=2)
    return perm_idx * _EDGE_ORIENT_MULT + orient_idx


def edge1_index(state: CubeState) -> int:
    """엣지 cubelet 0~5번의 위치+방향 인덱스"""
    return _partial_edge_index(state, _EDGE1_CUBELETS)


def edge2_index(state: CubeState) -> int:
    """엣지 cubelet 6~11번의 위치+방향 인덱스"""
    return _partial_edge_index(state, _EDGE2_CUBELETS)


class PatternDB:
    """BFS로 목표 상태에서 역방향 탐색해 패턴 DB 구축.

    max_depth: 테스트용 BFS 깊이 제한 (None이면 완전 생성 — 수 분 소요).
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
        """캐시 파일이 있으면 로드, 없으면 전체 BFS 생성 후 저장."""
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
