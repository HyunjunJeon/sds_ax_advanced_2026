"""Day07_new 수업 노트북 구조 검사기. 노트북을 실행하지 않고 파일만 본다.

사용법:
    uv run --no-sync python Day07_new/tests/check_notebook.py <nb.ipynb> --minutes N \
        --source <vllm v0.32.0 소스 트리> --ledger <근거 대장 폴더>

하한은 minutes에서 계산한다. 낮추지 않는다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import nbformat
from nbformat.reader import NotJSONError

COMMIT = "5df63a7203cdb9328d824a27b682e77c7b9928be"
LONG_CLASS_MINUTES = 40  # 이 분 이상이면 해보기 2개, 확인 질문 5개, 실패 재현 1개를 요구한다
REQUIRED_HEADINGS = ("## 직접 해보기", "## 확인 질문", "## 정리", "## 참고한 근거")
OBSERVE, PREDICT, FAILURE = "**관찰할 것.**", "**먼저 예측하세요.**", "# 실패 재현:"
UNCONFIRMED = "미확인"

PERMALINK = re.compile(r"github\.com/vllm-project/vllm/blob/([^/\s)]+)/([^\s)#`]+)#L(\d+)(?:-L(\d+))?")
LEDGER_ID = re.compile(r"\b(?:P[1-8]-\d\d|D-\d\d|R-\d\d)\b")
SECRETS = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{8,}|hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|rpa_[A-Za-z0-9]{16,}|"
    r"Bearer\s+[A-Za-z0-9._-]{20,})\b")
POD_HOST = re.compile(r"\b[a-z0-9]{10,}-\d{2,5}\.proxy\.runpod\.net\b")
POD_CONSOLE = re.compile(r"runpod\.io/console/pods/[a-z0-9]{10,}")
FORBIDDEN_IMPORT = re.compile(r"^\s*(?:from|import)\s+(vllm|torch)\b", re.MULTILINE)
RUN_POD_REF = re.compile(r"\bRUN_POD\b|RUNPOD_BASE_URL|proxy\.runpod\.net|base_url\s*=|localhost:\d+|127\.0\.0\.1")
RUN_POD_OFF = re.compile(r"^RUN_POD\s*=\s*False\s*(?:#.*)?$", re.MULTILINE)
RUN_POD_ON = re.compile(r"^\s*RUN_POD[ \t]*=(?!=)[ \t]*(?!False\b)\S", re.MULTILINE)
GUARD = re.compile(r"^if\s+RUN_POD\s*:", re.MULTILINE)
PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")  # 채워지지 않은 {이름} 자리표시자
FENCED_CODE = re.compile(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"(`+).+?\1", re.DOTALL)


def floors(minutes: int) -> dict[str, float]:
    long_class = minutes >= LONG_CLASS_MINUTES
    return {"cells": 0.75 * minutes, "code": 0.3 * minutes, "markdown": 230 * minutes,
            "observe": minutes / 10, "predict": minutes / 20,
            "exercise": 2 if long_class else 1, "questions": 5 if long_class else 2,
            "failure": 1 if long_class else 0}


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def timetable_problem(first_markdown: str, minutes: int) -> str | None:
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


def load_ledger(ledger: Path) -> dict[str, bool]:
    """대장 표의 행에서 ID -> 미확인 여부를 읽는다. 상태 또는 판정 열을 쓴다."""
    ids: dict[str, bool] = {}
    for path in sorted(ledger.glob("*.md")):
        status_col = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                status_col = None
                continue
            cells = _table_cells(line)
            if cells[0] == "ID":
                status_col = next((i for i, name in enumerate(cells) if name in ("상태", "판정")), None)
            elif status_col is not None and LEDGER_ID.fullmatch(cells[0]) and len(cells) > status_col:
                ids[cells[0]] = UNCONFIRMED in cells[status_col]
    return ids


def ledger_problems(nb: nbformat.NotebookNode, ids: dict[str, bool]) -> list[str]:
    problems = []
    for index, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        for found in sorted(set(LEDGER_ID.findall(cell.source))):
            if found not in ids:
                problems.append(f"셀 {index}의 근거 ID {found}가 대장에 없습니다.")
            elif ids[found] and UNCONFIRMED not in cell.source:
                problems.append(f"셀 {index}의 {found}는 대장에서 미확인인데 같은 셀에 '{UNCONFIRMED}'가 없습니다.")
    return problems


def permalink_problems(nb: nbformat.NotebookNode, source: Path) -> list[str]:
    problems, line_counts = [], {}
    for index, cell in enumerate(nb.cells):
        for sha, rel, first, last in PERMALINK.findall(cell.source):
            if sha != COMMIT:
                problems.append(f"셀 {index}의 permalink가 고정 커밋이 아닙니다: {sha}")
                continue
            target = source / rel
            if not target.is_file():
                problems.append(f"셀 {index}의 permalink 파일이 소스에 없습니다: {rel}")
                continue
            if target not in line_counts:
                line_counts[target] = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
            end = int(last or first)
            if not 1 <= int(first) <= end <= line_counts[target]:
                problems.append(f"셀 {index}의 줄 범위가 {rel}의 {line_counts[target]}줄 밖입니다: L{first}"
                                + (f"-L{last}" if last else ""))
    return problems


def run_pod_problems(code: list[tuple[int, str]]) -> list[str]:
    problems = []
    switched_off = any(RUN_POD_OFF.search(src) for _, src in code)
    for index, src in code:
        if RUN_POD_ON.search(src):
            problems.append(f"셀 {index}가 RUN_POD를 False가 아닌 값으로 둡니다.")
        if not RUN_POD_REF.search(src) or (RUN_POD_OFF.search(src) and not GUARD.search(src)):
            continue
        guard = GUARD.search(src)
        lines = src.splitlines()
        guard_line = src[:guard.start()].count("\n") if guard else len(lines)
        outside = [n for n, line in enumerate(lines)
                   if RUN_POD_REF.search(line) and not GUARD.match(line) and not RUN_POD_OFF.match(line)
                   and (n < guard_line or not line[:1].isspace())]
        if not switched_off:
            problems.append(f"셀 {index}가 RUN_POD = False 셀 없이 서버 설정을 씁니다.")
        elif guard is None or outside:
            problems.append(f"셀 {index}의 서버 URL 참조가 'if RUN_POD:' 안에 있지 않습니다.")
    return problems


def placeholder_problems(nb: nbformat.NotebookNode) -> list[str]:
    problems = []
    for index, cell in enumerate(nb.cells):
        if cell.cell_type != "markdown":
            continue
        prose = INLINE_CODE.sub("", FENCED_CODE.sub("", cell.source))
        problems += [f"셀 {index}에 채워지지 않은 자리표시자 {found}가 있습니다."
                     for found in dict.fromkeys(PLACEHOLDER.findall(prose))]
    return problems


def static_problems(nb: nbformat.NotebookNode, minutes: int, source: Path, ledger: Path) -> list[str]:
    markdown = [cell.source for cell in nb.cells if cell.cell_type == "markdown"]
    code = [(i, cell.source) for i, cell in enumerate(nb.cells) if cell.cell_type == "code"]
    joined = "\n".join(markdown)
    problems = []
    problem = timetable_problem(markdown[0], minutes) if markdown else "markdown 셀이 없습니다."
    problems += [problem] if problem else []
    problems += [f"markdown 제목이 없습니다: {h}" for h in REQUIRED_HEADINGS
                 if not re.search(rf"^{re.escape(h)}", joined, re.MULTILINE)]
    measured = {"cells": len(nb.cells), "code": len(code), "markdown": sum(map(len, markdown)),
                "observe": joined.count(OBSERVE), "predict": joined.count(PREDICT),
                "failure": sum(FAILURE in src for _, src in code),
                "exercise": len(re.findall(r"^### 해보기 \d", _section(joined, "## 직접 해보기"), re.MULTILINE)),
                "questions": len(re.findall(r"^\s*(?:\d+\.|[-*]) ", _section(joined, "## 확인 질문"), re.MULTILINE))}
    problems += [f"{name} 하한 미달: {measured[name]} < {floor:g}" for name, floor in floors(minutes).items()
                 if measured[name] < floor]
    problems += permalink_problems(nb, source)
    problems += ledger_problems(nb, load_ledger(ledger))
    problems += run_pod_problems(code)
    problems += placeholder_problems(nb)
    for index, cell in enumerate(nb.cells):
        for pattern, what in ((SECRETS, "키 형식 문자열"), (POD_HOST, "Pod 호스트"), (POD_CONSOLE, "Pod ID")):
            if pattern.search(cell.source):
                problems.append(f"셀 {index}에 {what}이 있습니다.")
    for index, src in code:
        if found := FORBIDDEN_IMPORT.search(src):
            problems.append(f"셀 {index}가 {found.group(1)}를 import합니다. 이 노트북은 vllm과 torch 없이 돌아야 합니다.")
    return problems


def check(path: Path, minutes: int, source: Path, ledger: Path) -> list[str]:
    try:
        nb = nbformat.read(path, as_version=4)
        nbformat.validate(nb)
    except OSError as error:
        return [f"노트북을 읽을 수 없습니다: {error}"]
    except (NotJSONError, nbformat.ValidationError) as error:
        return [f"nbformat 검증 실패: {error}"]
    return static_problems(nb, minutes, source, ledger)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day07_new 수업 노트북 구조 검사")
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--minutes", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True, help="vLLM v0.32.0 소스 트리")
    parser.add_argument("--ledger", type=Path, required=True, help="근거 대장 폴더")
    args = parser.parse_args(argv)
    problems = check(args.notebook, args.minutes, args.source, args.ledger)
    for problem in problems:
        print(f"FAIL {args.notebook}: {problem}", file=sys.stderr)
    if not problems:
        print(f"OK {args.notebook}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
