"""수업 노트북이 import하는 작은 도우미. 반복되는 고지·폴더·키 확인·표 출력만 모았다.

- 키 값은 어디에도 출력하지 않는다(설정됨/미설정만).
- 모델 factory는 import 시점에 가져오지 않고 호출 시점에 eval_lab.settings를 거쳐 찾는다.
"""
from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from IPython.display import display
from pydantic import BaseModel

from eval_lab import settings as _settings
from eval_lab.settings import ROOT, Settings

_OUTPUT_ROOT_VARIABLE = "DAY05_OUTPUT_ROOT"


def announce(
    purpose: str,
    *,
    model_calls: int,
    jev_calls: int = 0,
    judge_calls: int = 0,
    improver_calls: int = 0,
    minutes: int | None = None,
) -> None:
    """유료 호출 직전에 규모를 한 줄로 알린다. 알리기만 하고 멈추지 않는다. 0인 항목은 적지 않는다."""
    parts = [
        text for count, text in (
            (model_calls, f"에이전트 모델 약 {model_calls}회"),
            (jev_calls, f"Jev 최대 {jev_calls}회"),
            (judge_calls, f"Judge(xhigh) 최대 {judge_calls}회"),
            (improver_calls, f"개선기 약 {improver_calls}회"),
        ) if count
    ]
    if not parts:
        print("이 실행은 유료 모델 호출이 없습니다.")
        return
    if minutes is not None:
        parts.append(f"{minutes}분")
    print(f"[{purpose}] 이 실행은 {', '.join(parts)} 예상입니다. 진행합니다.")


def output_root() -> Path:
    """노트북 산출물 루트. DAY05_OUTPUT_ROOT가 있으면 그 경로, 없으면 outputs/notebook. 호출 시점에 정한다."""
    override = os.environ.get(_OUTPUT_ROOT_VARIABLE)
    return Path(override) if override else ROOT / "outputs" / "notebook"


def new_run_dir(stem: str) -> Path:
    """<output_root>/<stem>/<UTC 시각>-<6자리 16진수> 폴더를 새로 만든다. 이미 있는 폴더는 돌려주지 않는다."""
    base = output_root() / stem
    base.mkdir(parents=True, exist_ok=True)
    while True:
        path = base / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path


def show(rows: list[dict] | list[BaseModel], columns: list[str] | None = None, *, title: str | None = None) -> None:
    """dict 또는 pydantic 모델 목록을 줄이지 않고 표로 보여 준다."""
    records = [row.model_dump() if isinstance(row, BaseModel) else row for row in rows]
    if title:
        print(title)
    with pd.option_context("display.max_rows", None, "display.max_columns", None,
                           "display.width", 200, "display.max_colwidth", None):
        display(pd.DataFrame(records, columns=columns))


def show_keys(settings: Settings | None = None) -> None:
    """키가 설정됐는지만 표로 보여 준다. 값, 앞자리, 길이는 보여 주지 않는다."""
    status = _settings.key_status(settings)
    show([{"환경 변수": name, "상태": state} for name, state in status.items()])


def langfuse_or_none(settings: Settings | None = None):
    """Langfuse 클라이언트를 만든다. 키가 미설정이면 안내하고 None을 돌려준다. 다른 오류는 그대로 올린다."""
    try:
        return _settings.make_langfuse(settings)
    except RuntimeError:
        print("Langfuse 키가 미설정이라 로컬 경로로 진행합니다.")
        return None
