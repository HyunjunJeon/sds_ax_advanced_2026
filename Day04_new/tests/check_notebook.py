"""Day04_new 수업 노트북 구조 검사기. 실행하지 않고 파일만 본다.

사용법: uv run --no-sync python Day04_new/tests/check_notebook.py <path.ipynb> --minutes N   (N은 10, 50, 60, 70)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import nbformat
from nbformat.reader import NotJSONError

NOTEBOOKS = {"nb00": ("00-Setup.ipynb", 10), "nb01": ("01-Agent-Capability.ipynb", 50),
             "nb02": ("02-Tool-Interface.ipynb", 50), "nb03": ("03-MCP-Basics.ipynb", 50),
             "nb04": ("04-Production-MCP.ipynb", 50), "nb05": ("05-Skill-and-MCP.ipynb", 50),
             "nb06": ("06-Lab-Capability-Eval.ipynb", 60), "nb07": ("07-Lab-Improvement.ipynb", 70)}

FOLLOW, CHANGE, BREAK, MINE = "# [따라하기]", "# [바꿔보기]", "# [깨뜨리기]", "# [내 것 만들기]"
MARKERS = (FOLLOW, CHANGE, BREAK, MINE)
PREDICT, OBSERVE = "**먼저 예측하세요.**", "**관찰할 것.**"
REQUIRED_HEADINGS = ("## 직접 해보기", "## 확인 질문", "## 정리")
EXERCISE_HEADING = "## 직접 해보기"

# 분마다: cells, code, markdown(글자 수), observe, predict, breaks(# [깨뜨리기] 코드 셀), exercise, questions, marked(표지 셀 합)
FLOORS = {
    10: dict(cells=14, code=7, markdown=2500, observe=2, predict=0, breaks=0, exercise=2, questions=2, marked=4),
    50: dict(cells=38, code=20, markdown=9000, observe=5, predict=3, breaks=2, exercise=3, questions=4, marked=12),
    60: dict(cells=46, code=24, markdown=11000, observe=6, predict=3, breaks=3, exercise=4, questions=5, marked=14),
    70: dict(cells=54, code=28, markdown=13000, observe=7, predict=4, breaks=3, exercise=4, questions=6, marked=16),
}
# 분마다 표지별 최소 셀 수 (따라하기, 바꿔보기, 깨뜨리기, 내 것 만들기)
MARKER_FLOORS = {
    10: {FOLLOW: 2, CHANGE: 0, BREAK: 0, MINE: 0},
    50: {FOLLOW: 2, CHANGE: 3, BREAK: 2, MINE: 1},
    60: {FOLLOW: 2, CHANGE: 4, BREAK: 3, MINE: 1},
    70: {FOLLOW: 2, CHANGE: 4, BREAK: 3, MINE: 1},
}

PAID_CALL = re.compile(r"\b(?:build_agent|run_case|run_experiment|run_small_compare)\s*\(|\.(?:a?invoke|judge)\s*\(")
ANNOUNCE_CALLS = re.compile(r"\bmodel_calls\s*=\s*\d+\s*[,)]")
BANNED_CODE = re.compile(r"\b(?:fakes|FakeDecider|FakeChatModel|DAY04_ALLOW_FAKE_DECIDER|DAY04_FAKE_DECIDER|gate_labels)\b"
                         r"|\bho-\d\d")
# 저자 전용 라벨 파일 이름은 markdown 셀에도 쓰지 않는다. 한글 조사('gate_labels는') 앞에서도 잡으려고 \b 대신 ASCII 경계를 쓴다.
BANNED_EVERYWHERE = re.compile(r"(?<![A-Za-z0-9_])gate_labels(?![A-Za-z0-9_])")
KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
BANNED_WORDS = ("슬라이드", "채점")
DAY_PATH = re.compile(r"\bDay\d\d(?:_new)?/")
OWN_PATH = "Day04_new/"


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def timetable_problem(first_markdown: str, minutes: int) -> str | None:
    """첫 markdown 셀의 '수업 시간표' 표에서 마지막 분 칸의 합이 minutes와 같은지 본다."""
    if "수업 시간표" not in first_markdown:
        return "첫 markdown 셀에 '수업 시간표'가 없습니다."
    after = first_markdown.split("수업 시간표", 1)[1].split("\n## ", 1)[0]
    rows = [_table_cells(line) for line in after.splitlines() if line.strip().startswith("|")]
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


def _first_line(source: str) -> str:
    return (source.splitlines() or [""])[0]


def _section(joined: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}.*?(?=^## |\Z)", joined, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def _is_paid(source: str) -> bool:
    return PAID_CALL.search(source) is not None


def group_problems(cells: list) -> list[str]:
    """유료 호출 셀과 깨뜨리기 셀 뒤, 다음 '## ' 제목 전에 관찰 문단이 있는지 본다. 직접 해보기부터는 보지 않는다."""
    problems, open_group = [], None
    missing = "셀 {}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다."
    for index, cell in enumerate(cells):
        source = cell.source
        if cell.cell_type == "markdown":
            if re.search(rf"^{EXERCISE_HEADING}", source, re.MULTILINE):
                if open_group is not None:
                    problems.append(missing.format(open_group))
                return problems
            if OBSERVE in source:
                open_group = None
            elif open_group is not None and re.search(r"^## ", source, re.MULTILINE):
                problems.append(missing.format(open_group))
                open_group = None
        elif _is_paid(source) or _first_line(source).startswith(BREAK):
            open_group = index if open_group is None else open_group
    if open_group is not None:
        problems.append(missing.format(open_group))
    return problems


def cell_problems(index: int, cell) -> list[str]:
    """셀 하나에 대한 검사: 출력, 유료 고지, 금지 이름·문구, 키, 다른 Day 경로."""
    source, problems = cell.source, []
    if cell.cell_type == "code":
        if cell.outputs:
            problems.append(f"셀 {index}에 저장된 출력이 있습니다.")
        if _is_paid(source) and not ("announce(" in source and ANNOUNCE_CALLS.search(source)):
            problems.append(f"셀 {index}는 유료 호출인데 announce(…, model_calls=정수)가 없습니다.")
    banned = BANNED_CODE if cell.cell_type == "code" else BANNED_EVERYWHERE
    if found := banned.search(source):
        problems.append(f"셀 {index}에 쓰지 않기로 한 이름이 있습니다: {found.group(0)}")
    if KEY_PATTERN.search(source):
        problems.append(f"셀 {index} 소스에 키 형식 문자열이 있습니다.")
    problems += [f"셀 {index}에 금지 단어가 있습니다: {word}" for word in BANNED_WORDS if word in source]
    problems += [f"셀 {index}에 다른 Day 폴더 경로가 있습니다: {path}"
                 for path in dict.fromkeys(DAY_PATH.findall(source)) if path != OWN_PATH]
    return problems


def static_problems(nb: nbformat.NotebookNode, minutes: int) -> list[str]:
    markdown = [cell.source for cell in nb.cells if cell.cell_type == "markdown"]
    code = [cell for cell in nb.cells if cell.cell_type == "code"]
    joined = "\n".join(markdown)
    firsts = [_first_line(cell.source) for cell in code]
    marker_counts = {marker: sum(first.startswith(marker) for first in firsts) for marker in MARKERS}
    problems = []
    problem = timetable_problem(markdown[0], minutes) if markdown else "markdown 셀이 없습니다."
    problems += [problem] if problem else []
    problems += [f"markdown 제목이 없습니다: {h}" for h in REQUIRED_HEADINGS
                 if not re.search(rf"^{re.escape(h)}", joined, re.MULTILINE)]
    problems += ["markdown에 '호출 규모' 문구가 없습니다."] if "호출 규모" not in joined else []
    measured = {"cells": len(nb.cells), "code": len(code), "markdown": sum(map(len, markdown)),
                "observe": joined.count(OBSERVE), "predict": joined.count(PREDICT),
                "breaks": marker_counts[BREAK],
                "exercise": len(re.findall(r"^### 해보기 \d", _section(joined, EXERCISE_HEADING), re.MULTILINE)),
                "questions": len(re.findall(r"^\d+\. ", _section(joined, "## 확인 질문"), re.MULTILINE)),
                "marked": sum(first.startswith(MARKERS) for first in firsts)}
    problems += [f"{name} 하한 미달: {measured[name]} < {floor}" for name, floor in FLOORS[minutes].items()
                 if measured[name] < floor]
    problems += [f"{marker} 표지 셀 하한 미달: {marker_counts[marker]} < {floor}"
                 for marker, floor in MARKER_FLOORS[minutes].items() if marker_counts[marker] < floor]
    problems += group_problems(nb.cells)
    for index, cell in enumerate(nb.cells):
        problems += cell_problems(index, cell)
    return problems


def check(path: Path, minutes: int) -> list[str]:
    try:
        nb = nbformat.read(path, as_version=4)
        nbformat.validate(nb)
    except OSError as error:
        return [f"노트북을 읽을 수 없습니다: {error}"]
    except (NotJSONError, nbformat.ValidationError) as error:
        return [f"nbformat 검증 실패: {error}"]
    return static_problems(nb, minutes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day04_new 수업 노트북 구조 검사")
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--minutes", type=int, required=True, choices=sorted(FLOORS))
    args = parser.parse_args(argv)
    problems = check(args.notebook, args.minutes)
    for problem in problems:
        print(f"FAIL {args.notebook}: {problem}", file=sys.stderr)
    if not problems:
        print(f"OK {args.notebook}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
