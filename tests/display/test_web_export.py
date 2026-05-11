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
    assert "__CUBE_DATA__" not in content.replace("const CUBE_DATA = __CUBE_DATA__;", "").replace("__CUBE_DATA__", "REPLACED")

def test_export_valid_json_in_html(tmp_path):
    out = str(tmp_path / "solution.html")
    export_html(SOLVED, ["R"], out)
    content = open(out).read()
    marker = "const CUBE_DATA = "
    start = content.find(marker) + len(marker)
    end = content.find(";\n", start)
    data = json.loads(content[start:end])
    assert "initial" in data
    assert "moves" in data
    assert data["moves"] == ["R"]
    assert len(data["initial"]) == 54
