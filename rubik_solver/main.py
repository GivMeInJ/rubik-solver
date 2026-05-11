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

    if args.no_db:
        print("패턴 DB 없이 실행 (느림)...")
        db = PatternDB(max_depth=5)
    else:
        _DB_DIR.mkdir(exist_ok=True)
        db = PatternDB.load_or_build(_CORNER_DB, _EDGE1_DB, _EDGE2_DB)

    print("IDA* 탐색 시작...")
    t0 = time.time()
    moves = ida_star(initial_state, db)
    elapsed = time.time() - t0

    print_solution(initial_state, moves, elapsed, node_count=0)

    if args.export:
        export_html(initial_state, moves, args.export)
        print(f"\n[HTML 생성 완료] 브라우저에서 열기: {args.export}")


if __name__ == "__main__":
    main()
