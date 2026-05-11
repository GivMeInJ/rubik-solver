from __future__ import annotations
from rubik_solver.model.cube import CubeState
from rubik_solver.model.group import lehmer_encode, mixed_radix


def corner_index(state: CubeState) -> int:
    """코너 8개의 위치+방향을 단일 정수로 인코딩. 범위: 0 ~ 8!*3^7-1"""
    perm_idx = lehmer_encode(list(state.corner_perm))         # 0 ~ 8!-1 = 40319
    orient_idx = mixed_radix(list(state.corner_orient[:7]), base=3)  # 0 ~ 3^7-1 = 2186
    return perm_idx * (3 ** 7) + orient_idx


def _partial_edge_index(state: CubeState, edge_slots: list[int]) -> int:
    """엣지 6개 슬롯의 위치+방향을 인코딩. 범위: 0 ~ 6!*2^6-1 (≤ P(12,6)*2^6-1)

    각 슬롯의 큐블릿 값들을 상대 순위(relative rank)로 정규화한 뒤 Lehmer 인코딩.
    SOLVED 상태에서는 항상 0이 되는 것을 보장한다.
    """
    chosen = [state.edge_perm[i] for i in edge_slots]

    # 상대 순위 계산: sorted order 기준 각 원소의 위치
    sorted_chosen = sorted(chosen)
    relative = [sorted_chosen.index(v) for v in chosen]

    perm_idx = lehmer_encode(relative)   # 0 ~ 6!-1 = 719
    orient_idx = mixed_radix([state.edge_orient[i] for i in edge_slots], base=2)
    return perm_idx * (2 ** 6) + orient_idx


def edge1_index(state: CubeState) -> int:
    """엣지 슬롯 0~5번 기반 인덱스"""
    return _partial_edge_index(state, list(range(6)))


def edge2_index(state: CubeState) -> int:
    """엣지 슬롯 6~11번 기반 인덱스"""
    return _partial_edge_index(state, list(range(6, 12)))
