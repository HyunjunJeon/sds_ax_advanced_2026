"""문서(.md)에 홑 ~ 둘이 한 줄에 있으면 marked가 사이를 취소선으로 그린다. 노트북 검사기와 같은 규칙을 문서에 건다."""
from __future__ import annotations

from pathlib import Path

from check_notebook import FENCED_CODE, INLINE_CODE, LONE_TILDE

ROOT = Path(__file__).resolve().parents[1]


def _blank(match) -> str:
    """코드 영역을 지우되 줄 수는 남겨 줄 번호가 어긋나지 않게 한다."""
    return "\n" * match.group(0).count("\n")


def lone_tilde_lines(path: Path) -> list[int]:
    prose = INLINE_CODE.sub(_blank, FENCED_CODE.sub(_blank, path.read_text(encoding="utf-8")))
    return [number for number, line in enumerate(prose.splitlines(), 1) if LONE_TILDE.search(line)]


def doc_files() -> list[Path]:
    return [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").rglob("*.md"))]


def test_two_lone_tildes_on_one_line_are_found(tmp_path: Path):
    doc = tmp_path / "sample.md"
    doc.write_text("정상 줄\n01~04b와 Part 1~6\n`a~b c~d` 코드는 제외\n```\nx~y z~w\n```\n한 개만 ~ 있음\n", encoding="utf-8")
    assert lone_tilde_lines(doc) == [2]


def test_no_doc_has_two_lone_tildes_on_a_line():
    hits = [f"{path.relative_to(ROOT)}:{number}" for path in doc_files() for number in lone_tilde_lines(path)]
    assert hits == [], f"한 줄에 홑 ~ 둘(취소선으로 렌더링됨): {hits}"
