"""수업 노트북 구조 검사기. 실행하지 않고 파일만 본다. 실제 실행은 run_live.py가 맡는다.

사용법: uv run --no-sync python Day02_new/tests/check_notebook.py <path.ipynb> --minutes N
        [--min-cells C --min-code K --min-md M]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import nbformat
from nbformat.reader import NotJSONError

# docs/DESIGN.md "Day01 size baseline"의 60분 노트북 하한. 10분 사전 점검에는 하한을 두지 않는다.
FLOORS_60_MINUTES = {"cells": 36, "code": 16, "markdown": 7000}
# 60분 노트북의 따라하기/바꿔보기/깨뜨리기/내 것 만들기 셀 표지(코드 셀 첫 줄 접두사)와 분량 조건.
MARKERS = ("# [따라하기]", "# [바꿔보기]", "# [깨뜨리기]", "# [내 것 만들기]")
MIN_MARKED_CELLS = 12
MIN_PER_MARKER = {"# [바꿔보기]": 4}  # 표에 없는 표지는 DEFAULT_MIN_PER_MARKER
DEFAULT_MIN_PER_MARKER = 2
FIRST_FOLLOW_ALONG_FORBIDDEN = ("load_corpus", "ask(", "build_rag_agent", "retriever", "data/business")
REQUIRED_HEADINGS = ("## 직접 해보기", "## 확인 질문", "## 정리")
REQUIRED_PHRASE = "호출 규모"
KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
# 키 없이 도는 경로와 이전 제공자의 이름. 코드 셀에 다시 나타나면 안 된다.
REMOVED_SYMBOLS = re.compile(r"\b(ScriptedChatModel|ScriptExhausted|OfflineHashEmbeddings|DAY02_OFFLINE|"
                             r"CONNECTION_CHECK_LABEL|rag_script|live_cell|OPENROUTER\w*|langchain_openai)\b"
                             r"|\brag_lab\.offline\b")


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def timetable_problem(first_markdown: str, minutes: int) -> str | None:
    """첫 markdown 셀의 '수업 시간표' 표에서 분 칸의 합이 minutes와 같은지 본다."""
    if "수업 시간표" not in first_markdown:
        return "첫 markdown 셀에 '수업 시간표'가 없습니다."
    after_title = first_markdown.split("수업 시간표", 1)[1]
    rows = [_table_cells(line) for line in after_title.splitlines() if line.strip().startswith("|")]
    if len(rows) < 3:
        return "'수업 시간표' 아래에 표가 없습니다."
    header, body = rows[0], rows[2:]
    columns = [index for index, name in enumerate(header) if "분" in name]
    if not columns:
        return f"'수업 시간표' 표에 분 칸이 없습니다: {header}"
    total = 0
    for row in body:
        value = re.fullmatch(r"(\d+)\s*분?", row[columns[-1]]) if len(row) == len(header) else None
        if value is None:
            return f"'수업 시간표'의 분 칸을 읽을 수 없습니다: {row}"
        total += int(value.group(1))
    return None if total == minutes else f"'수업 시간표'의 분 합계가 {total}분입니다. {minutes}분이어야 합니다."


def marker_problems(code: list[nbformat.NotebookNode]) -> list[str]:
    """60분 노트북 전용: 표지 셀 수, 종류별 최소 개수(바꿔보기 4, 나머지 2), 첫 따라하기의 금지 이름."""
    firsts = [(cell.source.splitlines() or [""])[0] for cell in code]
    counts = {marker: sum(first.startswith(marker) for first in firsts) for marker in MARKERS}
    total = sum(counts.values())
    problems = []
    if total < MIN_MARKED_CELLS:
        problems.append(f"표지 셀이 {total}개입니다. {MIN_MARKED_CELLS}개 이상이어야 합니다.")
    for marker, count in counts.items():
        needed = MIN_PER_MARKER.get(marker, DEFAULT_MIN_PER_MARKER)
        if count == 0:
            problems.append(f"{marker} 표지 셀이 없습니다.")
        elif count < needed:
            problems.append(f"{marker} 표지 셀이 {count}개입니다. {needed}개 이상이어야 합니다.")
    first_follow = next((cell for cell, first in zip(code, firsts) if first.startswith(MARKERS[0])), None)
    if first_follow is not None:
        problems += [f"첫 {MARKERS[0]} 셀에 금지된 이름이 있습니다: {name}"
                     for name in FIRST_FOLLOW_ALONG_FORBIDDEN if name in first_follow.source]
    return problems


def static_problems(nb: nbformat.NotebookNode, minutes: int, floors: dict[str, int]) -> list[str]:
    """조건을 모두 모은다."""
    markdown = [cell.source for cell in nb.cells if cell.cell_type == "markdown"]
    code = [cell for cell in nb.cells if cell.cell_type == "code"]
    problems = []
    problem = timetable_problem(markdown[0], minutes) if markdown else "markdown 셀이 없습니다."
    problems += [problem] if problem else []
    joined = "\n".join(markdown)
    problems += [f"markdown 제목이 없습니다: {h}" for h in REQUIRED_HEADINGS
                 if not re.search(rf"^{re.escape(h)}", joined, re.MULTILINE)]
    if REQUIRED_PHRASE not in joined:
        problems.append(f"markdown에 '{REQUIRED_PHRASE}' 문구가 없습니다.")
    measured = {"cells": len(nb.cells), "code": len(code), "markdown": sum(map(len, markdown))}
    problems += [f"{name} 하한 미달: {measured[name]} < {floor}" for name, floor in floors.items() if measured[name] < floor]
    if minutes == 60:
        problems += marker_problems(code)
    problems += [f"셀 {i}에 저장된 출력이 있습니다." for i, cell in enumerate(nb.cells)
                 if cell.cell_type == "code" and cell.outputs]
    problems += [f"셀 {i}에서 LangGraph StateGraph를 사용합니다." for i, cell in enumerate(nb.cells)
                 if cell.cell_type == "code" and re.search(r"\bStateGraph\b", cell.source)]
    problems += [f"셀 {i} 소스에 sk- 키 형식 문자열이 있습니다." for i, cell in enumerate(nb.cells)
                 if KEY_PATTERN.search(cell.source)]
    problems += [f"셀 {i}에 삭제된 이름이 있습니다: {found.group(0)}" for i, cell in enumerate(nb.cells)
                 if cell.cell_type == "code" and (found := REMOVED_SYMBOLS.search(cell.source))]
    return problems


def check(path: Path, minutes: int, floors: dict[str, int]) -> list[str]:
    try:
        nb = nbformat.read(path, as_version=4)
        nbformat.validate(nb)
    except OSError as error:
        return [f"노트북을 읽을 수 없습니다: {error}"]
    except (NotJSONError, nbformat.ValidationError) as error:
        return [f"nbformat 검증 실패: {error}"]
    return static_problems(nb, minutes, floors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day02_new 수업 노트북 구조 검사")
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--minutes", type=int, required=True)
    parser.add_argument("--min-cells", type=int)
    parser.add_argument("--min-code", type=int)
    parser.add_argument("--min-md", type=int)
    args = parser.parse_args(argv)
    floors = dict(FLOORS_60_MINUTES) if args.minutes == 60 else {}
    given = {"cells": args.min_cells, "code": args.min_code, "markdown": args.min_md}
    floors.update({name: value for name, value in given.items() if value is not None})
    problems = check(args.notebook, args.minutes, floors)
    for problem in problems:
        print(f"FAIL {args.notebook}: {problem}", file=sys.stderr)
    if not problems:
        print(f"OK {args.notebook}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
