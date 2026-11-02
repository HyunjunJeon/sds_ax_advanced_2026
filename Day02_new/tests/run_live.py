"""노트북을 실제 모델로 순서대로 실행하고 셀별 시간과 토큰을 남긴다. 유료 호출이므로 규모를 알고 실행한다.

사용법: uv run --no-sync python Day02_new/tests/run_live.py <path.ipynb>
결과: Day02_new/outputs/live/<stem>.json(셀마다 갱신), <stem>.usage.jsonl, <stem>.executed.ipynb
다시 실행하면 앞선 세 파일을 outputs/live/history/<UTC 시각>/에 먼저 복사한다(지출 기록이 사라지지 않게).
보고서의 cells[].usage_lines는 그 셀이 만든 사용량 줄의 [시작, 끝) 범위(0부터, 끝 제외)다.
분리 실행: nohup uv run --no-sync python Day02_new/tests/run_live.py <path.ipynb> > 로그 2>&1 &
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError
from nbformat.reader import NotJSONError

DAY02_NEW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY02_NEW))

from rag_lab.settings import _redact

CELL_TIMEOUT_SECONDS = 1800
# 셸에 남은 다른 키로 호출되거나 추적 서비스로 내용이 나가지 않게 kernel에 넘기지 않는다.
SECRET_NAME_PARTS = ("API_KEY", "TOKEN", "SECRET", "LANGFUSE", "LANGSMITH", "RUNPOD")


def kernel_environment(usage_log: Path) -> dict[str, str]:
    kept = {k: v for k, v in os.environ.items() if not any(part in k.upper() for part in SECRET_NAME_PARTS)}
    return {**kept, "DAY02_USAGE_LOG": str(usage_log)}


def usage_totals(usage_log: Path) -> dict[str, int]:
    lines = usage_log.read_text(encoding="utf-8").splitlines() if usage_log.exists() else []
    rows = [json.loads(line) for line in lines]
    return {"input_tokens": sum(row["input_tokens"] for row in rows),
            "output_tokens": sum(row["output_tokens"] for row in rows), "model_calls": len(rows)}


def usage_line_count(usage_log: Path) -> int:
    return len(usage_log.read_text(encoding="utf-8").splitlines()) if usage_log.exists() else 0


def archive_previous_run(live: Path, stem: str) -> Path | None:
    """앞선 실행의 사용량 기록·보고서·실행본을 history/<UTC 시각>/에 복사한다. 복사할 것이 없으면 None."""
    previous = [live / f"{stem}{suffix}" for suffix in (".usage.jsonl", ".json", ".executed.ipynb")]
    existing = [path for path in previous if path.exists()]
    if not existing:
        return None
    destination = live / "history" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir(parents=True)
    for path in existing:
        shutil.copy2(path, destination / path.name)
    return destination


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


def run(notebook: Path) -> int:
    stem = notebook.stem
    live = DAY02_NEW / "outputs" / "live"
    live.mkdir(parents=True, exist_ok=True)
    usage_log = live / f"{stem}.usage.jsonl"
    archive_previous_run(live, stem)
    usage_log.unlink(missing_ok=True)
    nb = nbformat.read(notebook, as_version=4)
    report = {"notebook": notebook.name, "cells": [], "errors": [], "finished": False, "total_seconds": 0.0,
              "input_tokens": 0, "output_tokens": 0, "model_calls": 0}
    started = time.monotonic()

    def save() -> None:
        report.update(total_seconds=round(time.monotonic() - started, 3), **usage_totals(usage_log))
        write_atomic(live / f"{stem}.json", json.dumps(report, ensure_ascii=False, indent=2))

    save()
    client = NotebookClient(nb, kernel_name="python3", timeout=CELL_TIMEOUT_SECONDS,
                            resources={"metadata": {"path": str(DAY02_NEW)}})
    with client.setup_kernel(env=kernel_environment(usage_log)):
        for index, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            cell_started = time.monotonic()
            lines_before = usage_line_count(usage_log)
            error = run_cell(client, cell, index)
            report["cells"].append({"index": index, "seconds": round(time.monotonic() - cell_started, 3),
                                    "status": "error" if error else "ok",
                                    "usage_lines": [lines_before, usage_line_count(usage_log)]})
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
    if len(argv) != 1:
        print("사용법: run_live.py <path.ipynb>", file=sys.stderr)
        return 2
    try:
        return run(Path(argv[0]).resolve())
    except (OSError, NotJSONError) as error:
        print(f"노트북을 읽을 수 없습니다: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
