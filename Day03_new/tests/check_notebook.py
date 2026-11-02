"""수업 노트북 구조 검사기. 실행하지 않고 파일만 본다. 실제 실행은 run_live.py와 audit_live.py가 맡는다.

사용법: uv run --no-sync python Day03_new/tests/check_notebook.py <path.ipynb> --minutes N
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import nbformat
from nbformat.reader import NotJSONError

FLOORS = {60: {"cells": 46, "code": 24, "markdown": 11000, "observe": 6, "predict": 3, "failure": 3, "exercise": 4, "questions": 5},
          10: {"cells": 14, "code": 7, "markdown": 2500, "observe": 2, "predict": 0, "failure": 0, "exercise": 2, "questions": 2}}
REQUIRED_HEADINGS = ("## 직접 해보기", "## 확인 질문", "## 정리")
OBSERVE, PREDICT, FAILURE = "**관찰할 것.**", "**먼저 예측하세요.**", "# 실패 재현:"
KEY_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b")
BANNED_CODE = re.compile(r"\b(ScriptedChatModel|ScriptExhausted|fakes|DAY02_OFFLINE|live_cell|OPENROUTER\w*|langchain_openai|"
                         r"langgraph_supervisor|draw_mermaid_png|student_tasks|merge_attempts|select_context|gold\.jsonl)\b")
BANNED_WORDS = ("슬라이드", "채점", "WORKSHEET", "challenge_tests", "student_tasks")


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def timetable_problem(first_markdown: str, minutes: int) -> str | None:
    """첫 markdown 셀의 '수업 시간표' 표에서 분 칸의 합이 minutes와 같은지 본다."""
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


def _section(joined: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}.*?(?=^## |\Z)", joined, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def group_problems(cells: list) -> list[str]:
    """유료 호출 묶음과 실패 재현 묶음 뒤에 관찰 문단이 있는지 본다. 직접 해보기부터는 보지 않는다."""
    problems, open_group = [], None
    for index, cell in enumerate(cells):
        source = cell.source
        if cell.cell_type == "markdown":
            if source.lstrip().startswith("## 직접 해보기"):
                if open_group is not None:
                    problems.append(f"셀 {open_group}의 유료 호출·실패 재현 뒤에 관찰 문단이 없습니다.")
                return problems
            if OBSERVE in source:
                open_group = None
        elif "announce(" in source or FAILURE in source:
            open_group = index if open_group is None else open_group
    if open_group is not None:
        problems.append(f"셀 {open_group}의 유료 호출·실패 재현 뒤에 관찰 문단이 없습니다.")
    return problems


def static_problems(nb: nbformat.NotebookNode, minutes: int, floors: dict[str, int]) -> list[str]:
    markdown = [cell.source for cell in nb.cells if cell.cell_type == "markdown"]
    code = [cell for cell in nb.cells if cell.cell_type == "code"]
    joined = "\n".join(markdown)
    problems = []
    problem = timetable_problem(markdown[0], minutes) if markdown else "markdown 셀이 없습니다."
    problems += [problem] if problem else []
    problems += [f"markdown 제목이 없습니다: {h}" for h in REQUIRED_HEADINGS if not re.search(rf"^{re.escape(h)}", joined, re.MULTILINE)]
    problems += ["markdown에 '호출 규모' 문구가 없습니다."] if "호출 규모" not in joined else []
    measured = {"cells": len(nb.cells), "code": len(code), "markdown": sum(map(len, markdown)),
                "observe": joined.count(OBSERVE), "predict": joined.count(PREDICT),
                "failure": sum(FAILURE in c.source for c in code),
                "exercise": len(re.findall(r"^### 해보기 \d", _section(joined, "## 직접 해보기"), re.MULTILINE)),
                "questions": len(re.findall(r"^\d+\. ", _section(joined, "## 확인 질문"), re.MULTILINE))}
    problems += [f"{name} 하한 미달: {measured[name]} < {floor}" for name, floor in floors.items() if measured[name] < floor]
    problems += group_problems(nb.cells)
    for index, cell in enumerate(nb.cells):
        if cell.cell_type == "code" and cell.outputs:
            problems.append(f"셀 {index}에 저장된 출력이 있습니다.")
        if KEY_PATTERN.search(cell.source):
            problems.append(f"셀 {index} 소스에 키 형식 문자열이 있습니다.")
        if cell.cell_type == "code" and (found := BANNED_CODE.search(cell.source)):
            problems.append(f"셀 {index}에 쓰지 않기로 한 이름이 있습니다: {found.group(0)}")
        if "gold" in cell.source and cell.cell_type == "code" and "mas_lab.evaluation" not in cell.source and "gold" not in _allowed_gold(nb, index):
            problems.append(f"셀 {index}가 평가 모듈 없이 gold를 언급합니다.")
        problems += [f"셀 {index}에 금지 단어가 있습니다: {w}" for w in BANNED_WORDS if w in cell.source]
    return problems


def _allowed_gold(nb: nbformat.NotebookNode, index: int) -> str:
    """앞 셀에서 load_gold를 import했으면 그 변수를 평가 셀에서 쓸 수 있다."""
    earlier = "\n".join(c.source for c in nb.cells[:index] if c.cell_type == "code")
    return "gold" if "from mas_lab.evaluation import" in earlier else ""


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
    parser = argparse.ArgumentParser(description="Day03_new 수업 노트북 구조 검사")
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--minutes", type=int, required=True, choices=sorted(FLOORS))
    args = parser.parse_args(argv)
    problems = check(args.notebook, args.minutes, FLOORS[args.minutes])
    for problem in problems:
        print(f"FAIL {args.notebook}: {problem}", file=sys.stderr)
    if not problems:
        print(f"OK {args.notebook}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
