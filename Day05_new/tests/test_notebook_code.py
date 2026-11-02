"""노트북 00~06 각각의 구조, 코드 셀 문법, eval_lab import를 실행 없이 본다. `-k nb03a`로 하나만 고른다."""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

import nbformat
import pytest
from check_notebook import NOTEBOOKS, check

DAY05_ROOT = Path(__file__).resolve().parents[1]


def code_cells(path: Path) -> list[tuple[int, str]]:
    nb = nbformat.read(path, as_version=4)
    return [(index, cell.source) for index, cell in enumerate(nb.cells) if cell.cell_type == "code"]


def without_magics(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.startswith(("%", "!")))


@pytest.fixture(params=sorted(NOTEBOOKS), ids=sorted(NOTEBOOKS))
def notebook(request) -> tuple[Path, int]:
    name, minutes = NOTEBOOKS[request.param]
    return DAY05_ROOT / name, minutes


def test_notebook_exists(notebook):
    path, _ = notebook
    assert path.is_file(), f"{path.name} 파일이 없습니다."


def test_notebook_passes_structure_check(notebook):
    path, minutes = notebook
    assert check(path, minutes) == []


def test_code_cells_compile(notebook):
    path, _ = notebook
    for index, source in code_cells(path):
        try:
            compile(without_magics(source), f"{path.name}[셀 {index}]", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        except SyntaxError as error:
            pytest.fail(f"{path.name} 셀 {index} 문법 오류: {error}")


def eval_lab_imports(source: str) -> list[tuple[str, list[str]]]:
    """(모듈, 가져오는 이름들). `import eval_lab.x`는 이름이 빈 목록이다. 컴파일이 안 되는 셀은 건너뛴다(문법 시험이 잡는다)."""
    try:
        tree = compile(without_magics(source), "<cell>", "exec", flags=ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(alias.name, []) for alias in node.names if alias.name.split(".")[0] == "eval_lab"]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").split(".")[0] == "eval_lab":
            found.append((node.module, [alias.name for alias in node.names]))
    return found


def test_eval_lab_imports_resolve(notebook):
    path, _ = notebook
    for index, source in code_cells(path):
        for module_name, names in eval_lab_imports(source):
            module = importlib.import_module(module_name)
            for name in names:
                assert hasattr(module, name) or _is_submodule(module_name, name), \
                    f"{path.name} 셀 {index}: {module_name}에 {name}이 없습니다."


def _is_submodule(module_name: str, name: str) -> bool:
    try:
        importlib.import_module(f"{module_name}.{name}")
    except ModuleNotFoundError:
        return False
    return True


def test_code_cells_have_no_saved_outputs(notebook):
    path, _ = notebook
    nb = nbformat.read(path, as_version=4)
    saved = [index for index, cell in enumerate(nb.cells) if cell.cell_type == "code" and cell.outputs]
    assert saved == [], f"{path.name} 출력이 저장된 셀: {saved}"


def test_notebook_ids_are_the_eight_day05_notebooks():
    assert sorted(NOTEBOOKS) == ["nb00", "nb01", "nb02", "nb03a", "nb03b", "nb04", "nb05", "nb06"]
    assert NOTEBOOKS["nb06"] == ("06-Lab-Self-Improving-Agent.ipynb", 90)
