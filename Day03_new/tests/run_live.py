"""노트북을 실제 모델로 순서대로 실행하고 셀별 시간, 토큰, 호출 수를 남긴다. 유료 호출이므로 규모를 알고 실행한다.

사용법: uv run --no-sync python Day03_new/tests/run_live.py <path.ipynb> [--exercises]
--exercises: 임시 사본에서 RUN_EXERCISE와 RUN_OPTIONAL을 켜서 실행한다. 저장본은 바뀌지 않는다.
결과: Day03_new/outputs/live/<stem>[.exercises].json, .usage.jsonl, .executed.ipynb
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError
from nbformat.reader import NotJSONError

DAY03_NEW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY03_NEW))

from rag_lab.settings import _redact

CELL_TIMEOUT_SECONDS = 1800
# 셸에 남은 다른 키로 호출되거나 추적 서비스로 내용이 나가지 않게 kernel에 넘기지 않는다.
SECRET_NAME_PARTS = ("API_KEY", "TOKEN", "SECRET", "LANGFUSE", "LANGSMITH", "RUNPOD")
SWITCHES = re.compile(r"^(RUN_EXERCISE|RUN_OPTIONAL)\s*=\s*False", re.MULTILINE)


def kernel_environment(usage_log: Path) -> dict[str, str]:
    kept = {k: v for k, v in os.environ.items() if not any(part in k.upper() for part in SECRET_NAME_PARTS)}
    return {**kept, "DAY02_USAGE_LOG": str(usage_log)}


def usage_rows(usage_log: Path) -> list[dict]:
    lines = usage_log.read_text(encoding="utf-8").splitlines() if usage_log.exists() else []
    return [json.loads(line) for line in lines]


def usage_totals(usage_log: Path) -> dict[str, int]:
    rows = usage_rows(usage_log)
    return {"input_tokens": sum(row["input_tokens"] for row in rows),
            "output_tokens": sum(row["output_tokens"] for row in rows), "model_calls": len(rows)}


def write_atomic(path: Path, text: str) -> None:
    """폴링하는 쪽이 쓰다 만 파일을 읽지 않게 바꿔치기로 쓴다."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(_redact(text), encoding="utf-8")
    temporary.replace(path)


def run_cell(client: NotebookClient, cell: nbformat.NotebookNode, index: int) -> dict | None:
    """실패하면 오류 항목을, 성공하면 None을 돌려준다."""
    try:
        client.execute_cell(cell, index)
    except CellExecutionError as error:
        return {"index": index, "type": error.ename, "message": _redact(error.evalue)}
    except (CellTimeoutError, DeadKernelError) as error:
        return {"index": index, "type": type(error).__name__, "message": _redact(str(error))}
    return None


def switch_on(nb: nbformat.NotebookNode) -> int:
    changed = 0
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source, count = SWITCHES.subn(lambda m: f"{m.group(1)} = True", cell.source)
            changed += count
    return changed


def run(notebook: Path, exercises: bool = False) -> int:
    stem = notebook.stem + (".exercises" if exercises else "")
    live = DAY03_NEW / "outputs" / "live"
    live.mkdir(parents=True, exist_ok=True)
    usage_log = live / f"{stem}.usage.jsonl"
    usage_log.unlink(missing_ok=True)
    nb = nbformat.read(notebook, as_version=4)
    switched = switch_on(nb) if exercises else 0
    report = {"notebook": notebook.name, "exercises": exercises, "switched": switched, "cells": [], "errors": [], "finished": False,
              "total_seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "model_calls": 0}
    started = time.monotonic()

    def save() -> None:
        report.update(total_seconds=round(time.monotonic() - started, 3), **usage_totals(usage_log))
        write_atomic(live / f"{stem}.json", json.dumps(report, ensure_ascii=False, indent=2))

    save()
    client = NotebookClient(nb, kernel_name="python3", timeout=CELL_TIMEOUT_SECONDS, resources={"metadata": {"path": str(DAY03_NEW)}})
    with client.setup_kernel(env=kernel_environment(usage_log)):
        for index, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            before, cell_started = len(usage_rows(usage_log)), time.monotonic()
            error = run_cell(client, cell, index)
            report["cells"].append({"index": index, "seconds": round(time.monotonic() - cell_started, 3), "status": "error" if error else "ok",
                                    "model_calls": len(usage_rows(usage_log)) - before, "has_output": bool(cell.outputs),
                                    "announced": "announce(" in cell.source})
            report["errors"] += [error] if error else []
            save()
            if error:
                break
    write_atomic(live / f"{stem}.executed.ipynb", nbformat.writes(nb))
    report["finished"] = not report["errors"]
    save()
    if report["errors"]:
        print(f"LIVE RUN FAILED {stem} errors={len(report['errors'])}", file=sys.stderr)
        return 1
    print(f"LIVE RUN OK {stem} errors=0")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="노트북 실제 실행")
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--exercises", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.notebook.resolve(), args.exercises)
    except (OSError, NotJSONError) as error:
        print(f"노트북을 읽을 수 없습니다: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
