"""노트북의 코드 셀이 가리키는 mas_lab·rag_lab 이름과 소스 조각 표식이 지금도 있는지 모델 호출 없이 확인한다.

check_notebook.py는 파일 구조만 보고, 코드를 고친 뒤 노트북 셀이 깨지는 것은 유료 재실행에서야 드러났다.
여기서는 셀을 실행하지 않고 두 가지만 본다.
1. 셀의 `from mas_lab.x import 이름`, `from rag_lab.x import 이름`이 지금 import된다.
2. `inspect.getsource` 결과를 `변수.index("표식")`으로 자르는 셀의 표식이 그 소스에 있다.
"""
import ast
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import NamedTuple

import nbformat
import pytest
from mas_lab import research, runner, structures

DAY03_NEW = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted(DAY03_NEW.glob("0*.ipynb"))
LAB_PACKAGES = ("mas_lab", "rag_lab")
# 소스 조각 셀의 `변수.index("표식")`에서 변수가 가리키는 대상. 새 셀이 소스를 자르면 여기에 한 줄을 더해야 한다.
SOURCE_VARIABLES = {
    ("01-Workflow-vs-Agent.ipynb", "runner_source"): runner,
    ("02-Agent-Architecture.ipynb", "source"): inspect.getmodule(structures.build_handoff),
    ("06-Lab-Research-Agents.ipynb", "graph_source"): research.build_research_graph,
}
# `[..].index(..)`, `"..".index(..)`처럼 받는 쪽이 리터럴이면 소스 조각이 아니라 평범한 list·str 사용이다.
PLAIN_RECEIVERS = (ast.List, ast.Tuple, ast.Constant, ast.JoinedStr)


class ImportCase(NamedTuple):
    notebook: str
    cell: int
    cell_id: str
    module: str
    name: str | None

    @property
    def label(self) -> str:
        return f"{self.notebook}:cell{self.cell}({self.cell_id}):{self.module}.{self.name}"


class SliceCase(NamedTuple):
    notebook: str
    cell: int
    cell_id: str
    receiver: str
    marker: str | None

    @property
    def label(self) -> str:
        return f"{self.notebook}:cell{self.cell}({self.cell_id}):{self.receiver}.index({self.marker!r})"


def parse_cell(source: str) -> list[ast.Module]:
    """셀 소스를 파싱한다. IPython 매직 때문에 안 되면 줄마다 따로 파싱해 되는 줄만 남긴다."""
    try:
        return [ast.parse(source)]
    except SyntaxError:
        trees = []
        for line in source.splitlines():
            try:
                trees.append(ast.parse(line.strip()))
            except SyntaxError:
                continue
        return trees


def without_magic(source: str) -> str:
    """IPython 매직(`%`, `!`)으로 시작하는 줄을 빈 줄로 바꾼다. 오류의 줄 번호가 셀의 줄 번호와 같게 줄 수는 그대로 둔다."""
    return "\n".join("" if line.lstrip().startswith(("%", "!")) else line for line in source.splitlines())


def syntax_problems(cells) -> list[str]:
    """(노트북, 셀 번호, 셀 id, 소스) 묶음마다 셀 전체를 한 번에 파싱하고, 파싱되지 않는 셀을 위치와 함께 돌려준다."""
    problems = []
    for notebook, index, cell_id, source in cells:
        try:
            ast.parse(without_magic(source))
        except SyntaxError as error:
            problems.append(f"{notebook}:cell{index}({cell_id}) {error.lineno}행: {error.msg}")
    return problems


def lab_imports(source: str) -> list[tuple[str, str | None]]:
    """셀이 mas_lab·rag_lab에서 가져오는 (모듈, 이름)을 순서대로 중복 없이 돌려준다. `import 모듈` 꼴의 이름은 None이다."""
    found = []
    for tree in parse_cell(source):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.split(".")[0] in LAB_PACKAGES:
                found += [(node.module, alias.name) for alias in node.names]
            elif isinstance(node, ast.Import):
                found += [(alias.name, None) for alias in node.names if alias.name.split(".")[0] in LAB_PACKAGES]
    return list(dict.fromkeys(found))


def index_calls(source: str) -> list[tuple[str, str | None]]:
    """셀의 `받는쪽.index(인자)` 호출을 (받는쪽 코드, 문자열 리터럴 인자 또는 None)으로 돌려준다. 리터럴 list·str 사용은 뺀다."""
    found = []
    for tree in parse_cell(source):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "index" and not isinstance(node.func.value, PLAIN_RECEIVERS):
                first = node.args[0] if node.args else None
                marker = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
                found.append((ast.unparse(node.func.value), marker))
    return found


def code_cells() -> list[tuple[str, int, str, str]]:
    cells = []
    for path in NOTEBOOKS:
        for index, cell in enumerate(nbformat.read(path, as_version=4).cells):
            if cell.cell_type == "code":
                cells.append((path.name, index, cell.get("id", ""), cell.source))
    return cells


def import_cases() -> list[ImportCase]:
    return [ImportCase(notebook, index, cell_id, module, name) for notebook, index, cell_id, source in code_cells() for module, name in lab_imports(source)]


def slice_cases() -> list[SliceCase]:
    return [SliceCase(notebook, index, cell_id, receiver, marker) for notebook, index, cell_id, source in code_cells() for receiver, marker in index_calls(source)]


def import_problem(case: ImportCase) -> str | None:
    try:
        loaded = importlib.import_module(case.module)
    except ImportError as error:
        return f"{case.label}: {case.module}을 import할 수 없습니다 ({error})"
    if case.name in (None, "*") or hasattr(loaded, case.name):
        return None
    # `from 패키지 import 하위모듈`은 속성이 없어도 import된다. 일반 모듈에는 하위 모듈이 없으므로 패키지일 때만 찾는다.
    if hasattr(loaded, "__path__") and importlib.util.find_spec(f"{case.module}.{case.name}"):
        return None
    return f"{case.label}: {case.module}에 {case.name}이 없습니다"


def slice_problem(case: SliceCase) -> str | None:
    target = SOURCE_VARIABLES.get((case.notebook, case.receiver))
    if target is None:
        return (f"{case.label}: `{case.receiver}.index(...)`의 `{case.receiver}`가 SOURCE_VARIABLES에 없습니다. inspect.getsource 결과라면 "
                f"({case.notebook!r}, {case.receiver!r})을 그 대상 객체와 함께 추가하세요. 평범한 list나 str 변수라면 이 검사가 구분하지 못하니 index_calls에 그 제외 규칙을 더해야 합니다.")
    if case.marker is None:
        return f"{case.label}: 표식이 문자열 리터럴이 아니라서 `{case.receiver}`의 소스에서 찾을 수 없습니다"
    if case.marker not in inspect.getsource(target):
        return f"{case.label}: 표식 {case.marker!r}이 {target.__name__}의 소스에 없습니다"
    return None


def test_all_notebooks_are_read():
    """번호 노트북이 모두 읽히는지 본다. 03은 03a(순차·병렬)와 03b(분기·루프·패턴 번역)로, 04는 04a(계약·예산)와 04b(실패·승인)로, 05는 05a(실패 분류·나누는 기준)와 05b(수치·Fast/Slow·비교표)로 나뉘어 있다."""
    assert [path.name.split("-")[0] for path in NOTEBOOKS] == ["00", "01", "02", "03a", "03b", "04a", "04b", "05a", "05b", "06"], [path.name for path in NOTEBOOKS]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda path: path.name)
def test_every_code_cell_parses(path):
    """코드 셀이 모두 Python으로 파싱되는지 본다. parse_cell은 SyntaxError가 나면 줄 단위 파싱으로 넘어가므로 아래 import·표식 검사는 깨진 셀도 통과시킨다.
    2026-11-03 문구 다듬기가 01 코드 셀 5개와 02 코드 셀 2개의 문자열 속 `\\n`을 실제 줄바꿈으로 바꿨을 때 그 검사들이 통과했고, 유료 재실행에서야 드러났다."""
    problems = syntax_problems(cell for cell in code_cells() if cell[0] == path.name)
    assert not problems, "\n".join(problems)


def test_real_newline_inside_string_literal_is_reported():
    broken = ("02-Agent-Architecture.ipynb", 43, "abc", 'print("첫 줄\n둘째 줄")')
    fixed = ("02-Agent-Architecture.ipynb", 43, "abc", 'print("첫 줄\\n둘째 줄")')
    assert syntax_problems([broken]) == ["02-Agent-Architecture.ipynb:cell43(abc) 1행: unterminated string literal (detected at line 1)"]
    assert syntax_problems([fixed]) == []


def test_ipython_magic_lines_do_not_count_as_syntax_errors():
    assert syntax_problems([("00-Setup.ipynb", 1, "abc", "%load_ext autoreload\n!ls outputs\nvalue = 1")]) == []


@pytest.mark.parametrize("case", [pytest.param(case, id=case.label) for case in import_cases()])
def test_notebook_import_resolves(case):
    assert (problem := import_problem(case)) is None, problem


@pytest.mark.parametrize("case", [pytest.param(case, id=case.label) for case in slice_cases()])
def test_source_slice_marker_exists_in_source(case):
    assert (problem := slice_problem(case)) is None, problem


def test_cell_with_ipython_magic_still_yields_its_imports():
    source = "%matplotlib inline\nfrom mas_lab.view import show_table\n    from rag_lab.settings import ROOT\nimport mas_lab.trace"
    assert lab_imports(source) == [("mas_lab.view", "show_table"), ("rag_lab.settings", "ROOT"), ("mas_lab.trace", None)]


def test_unregistered_index_receiver_fails_naming_the_variable():
    calls = index_calls("lines = text.splitlines()\nlines.index('x')\nmystery[mystery.index('a'):]")
    cases = [SliceCase("02-Agent-Architecture.ipynb", 3, "abc", receiver, marker) for receiver, marker in calls]
    assert [case.receiver for case in cases] == ["lines", "mystery"]
    assert all(f"`{case.receiver}`가 SOURCE_VARIABLES에 없습니다" in slice_problem(case) for case in cases)


def test_index_on_literal_list_or_string_is_a_plain_use():
    assert index_calls("[1, 2].index(2)\n'abc'.index('b')\n(1, 2).index(1)") == []


def test_registered_variable_with_missing_or_non_literal_marker_fails():
    missing = SliceCase("06-Lab-Research-Agents.ipynb", 24, "a5f89ff5", "graph_source", "    if no_such_branch:")
    assert "표식 '    if no_such_branch:'" in slice_problem(missing)
    non_literal = [SliceCase("06-Lab-Research-Agents.ipynb", 24, "a5f89ff5", receiver, marker) for receiver, marker in index_calls("graph_source.index(marker)")]
    assert "문자열 리터럴이 아니라서" in slice_problem(non_literal[0])
