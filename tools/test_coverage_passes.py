"""Coverage·passes 페이지의 경계값 회귀 검사."""
import ast
from pathlib import Path
import sys

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_function(path: Path, name: str, namespace: dict):
    """페이지를 실행하지 않고 실제 함수 정의만 불러온다."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


season_span = load_function(ROOT / "views" / "coverage.py", "season_span", {})
pass_length_distribution = load_function(
    ROOT / "views" / "passes.py", "pass_length_distribution", {"pd": pd}
)

assert season_span([]) == "시즌 비귀속"

# 실제 경계값이 첫 구간에 들어가고 제외 사유가 서로 섞이지 않는지 확인한다.
edge = pd.DataFrame({"length": [0, 10, 200, None, -1, 201],
                     "complete": [True, True, False, True, False, False]})
edge_agg, edge_missing, edge_outside = pass_length_distribution(edge)
assert int(edge_agg["size"].sum()) == 3
assert int(edge_agg.loc["~10", "size"]) == 2
assert edge_missing == 1
assert edge_outside == 2

# 배포 데이터도 유효 행 수와 구간 합계가 정확히 일치해야 한다.
passes = pd.read_parquet(ROOT / "data" / "statsbomb" / "passes.parquet")
agg, missing, outside = pass_length_distribution(passes)
lengths = pd.to_numeric(passes["length"], errors="coerce")
zeros = int(lengths.eq(0).sum())
assert zeros == 38, f"zero-length expected 38, got {zeros}"
assert int(agg["size"].sum()) + missing + outside == len(passes)

# 실제 페이지 출력에서 비시즌 자료의 범위 표기가 유지되는지 확인한다.
coverage = AppTest.from_file(str(ROOT / "views" / "coverage.py"), default_timeout=120)
coverage.run()
assert not coverage.exception
tables = [element.value for element in coverage.dataframe]
freshness = next(table for table in tables if "범위" in table.columns)
transfermarkt = freshness[freshness["소스"] == "Transfermarkt"]
assert len(transfermarkt) == 1
assert transfermarkt.iloc[0]["범위"] == "시즌 비귀속"

print(f"PASS: zero={zeros}, missing={missing}, outside={outside}, "
      f"binned={int(agg['size'].sum())}, total={len(passes)}")
