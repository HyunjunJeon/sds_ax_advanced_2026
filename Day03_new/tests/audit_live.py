"""run_live.py의 기록을 읽어 고지 없는 유료 호출, 고지를 넘은 호출, 출력 없는 셀을 찾는다. 모델을 부르지 않는다.
고지의 model_calls는 그 셀의 상한이다(DESIGN 9.1.3). 한 셀에 고지가 여럿이면 합이 상한이다.
예고와 비교할 수 없는 유료 셀도 실패다: 실행본이 없으면 stem마다 한 줄, 고지에 model_calls 숫자가 없으면 그 셀마다 한 줄.

사용법: uv run --no-sync python Day03_new/tests/audit_live.py [stem ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import nbformat

DAY03_NEW = Path(__file__).resolve().parents[1]
LIVE = DAY03_NEW / "outputs" / "live"
MIN_OUTPUT_RATIO = {"00-Setup": 1.0}
DEFAULT_OUTPUT_RATIO = 0.9
_DECLARED = re.compile(r"model_calls=(\d+)")
SWITCHED = re.compile(r"^RUN_(?:EXERCISE|OPTIONAL)\s*=", re.MULTILINE)


def audit_report(report: dict, sources: dict[int, str] | None, stem: str) -> list[str]:
    problems = [f"{stem}: 끝까지 실행되지 않았습니다." ] if not report["finished"] else []
    problems += [f"{stem}: 셀 {e['index']} 오류 {e['type']}" for e in report["errors"]]
    if sources is None:
        problems.append(f"{stem}: 실행본({stem}.executed.ipynb)이 없어 셀의 모델 호출을 예고와 비교할 수 없습니다.")
    cells = report["cells"]
    for cell in cells:
        if cell["model_calls"] and not cell["announced"]:
            problems.append(f"{stem}: 셀 {cell['index']}가 고지 없이 모델을 {cell['model_calls']}회 불렀습니다.")
        if sources is None:
            continue
        declared = [int(n) for n in _DECLARED.findall(sources.get(cell["index"], ""))]
        if cell["model_calls"] and declared and cell["model_calls"] > sum(declared):
            problems.append(f"{stem}: 셀 {cell['index']} 예고 {sum(declared)}회, 실측 {cell['model_calls']}회로 예고를 넘습니다.")
        elif cell["model_calls"] and cell["announced"] and not declared:
            problems.append(f"{stem}: 셀 {cell['index']} 실측 {cell['model_calls']}회, 고지에 model_calls 숫자가 없어 비교할 수 없습니다.")
    ratio = sum(c["has_output"] for c in cells) / len(cells) if cells else 0
    floor = MIN_OUTPUT_RATIO.get(stem, DEFAULT_OUTPUT_RATIO)
    if ratio < floor:
        problems.append(f"{stem}: 출력 있는 코드 셀 비율 {ratio:.0%} < {floor:.0%}")
    return problems


def stale_cells(saved: nbformat.NotebookNode, executed: nbformat.NotebookNode, stem: str) -> list[str]:
    """실행본이 저장본과 같은 코드인지 본다. 스위치로 꺼 둔 직접 해보기와 선택 셀은 기본 실행에서 돌지 않으므로 뺀다."""
    def code(nb):
        return [c.source for c in nb.cells if c.cell_type == "code" and not SWITCHED.search(c.source)]
    return [] if code(saved) == code(executed) else [f"{stem}: 저장본의 코드가 실행본과 다릅니다. 다시 실행해야 합니다."]


def main(argv: list[str], live: Path = LIVE) -> int:
    stems = argv or sorted(p.stem for p in live.glob("*.json"))
    problems = []
    for stem in stems:
        report = json.loads((live / f"{stem}.json").read_text(encoding="utf-8"))
        nb = nbformat.read(live / f"{stem}.executed.ipynb", as_version=4) if (live / f"{stem}.executed.ipynb").exists() else None
        sources = {i: c.source for i, c in enumerate(nb.cells)} if nb else None
        problems += audit_report(report, sources, stem)
        saved = DAY03_NEW / report["notebook"]
        if nb and saved.exists() and not report.get("exercises"):
            problems += stale_cells(nbformat.read(saved, as_version=4), nb, stem)
        print(f"{stem}: 모델 {report['model_calls']}회, 입력 {report['input_tokens']:,}, 출력 {report['output_tokens']:,}, {report['total_seconds']:.0f}초")
    for problem in problems:
        print("FAIL", problem, file=sys.stderr)
    print("AUDIT OK" if not problems else f"AUDIT FAIL {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
