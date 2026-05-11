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
