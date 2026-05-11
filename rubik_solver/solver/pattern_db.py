from __future__ import annotations
from rubik_solver.model.cube import CubeState
from rubik_solver.model.group import lehmer_encode, mixed_radix

_EDGE1_SLOTS = (0, 1, 2, 3, 4, 5)
_EDGE2_SLOTS = (6, 7, 8, 9, 10, 11)
_CORNER_ORIENT_MULT = 3 ** 7     # 2187
_EDGE_ORIENT_MULT   = 2 ** 6     # 64


def corner_index(state: CubeState) -> int:
    """코너 8개의 위치+방향을 단일 정수로 인코딩. 범위: 0 ~ 8!*3^7-1"""
    perm_idx = lehmer_encode(list(state.corner_perm))
    orient_idx = mixed_radix(list(state.corner_orient[:7]), base=3)
    return perm_idx * _CORNER_ORIENT_MULT + orient_idx


def _partial_edge_index(state: CubeState, edge_slots: list[int]) -> int:
    """엣지 6개 슬롯의 위치+방향을 인코딩.

    각 슬롯의 cubelet 값(0-11)을 12개 원소 우주에서 부분 순열 순위로 인코딩.
    범위: 0 ~ P(12,6)*2^6-1 = 42,577,919
    """
    chosen = [state.edge_perm[i] for i in edge_slots]

    # P(12,6) partial permutation rank over 12-element universe
    n = 12
    used = [False] * n
    perm_idx = 0
    for k, v in enumerate(chosen):
        cnt = sum(1 for j in range(v) if not used[j])
        perm_idx = perm_idx * (n - k) + cnt
        used[v] = True

    orient_idx = mixed_radix([state.edge_orient[i] for i in edge_slots], base=2)
    return perm_idx * _EDGE_ORIENT_MULT + orient_idx


def edge1_index(state: CubeState) -> int:
    """엣지 슬롯 0~5번 기반 인덱스"""
    return _partial_edge_index(state, _EDGE1_SLOTS)


def edge2_index(state: CubeState) -> int:
    """엣지 슬롯 6~11번 기반 인덱스"""
    return _partial_edge_index(state, _EDGE2_SLOTS)
