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
