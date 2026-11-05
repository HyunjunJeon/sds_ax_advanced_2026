"""수업 노트북이 import하는 도우미. 노트북 셀을 짧게 두려고 반복되는 출력·연결·실행을 한곳에 모았다.

- 키 값은 어디에도 출력하지 않는다(설정됨/미설정만).
- run_small_compare는 dev 사례만 돌리고 Langfuse에 연결하지 않는다. 기록은 로컬 rows.jsonl뿐이다.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator, Coroutine
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
from IPython.display import display
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from cap_lab.agent import SERVER_SCRIPT, server_argv
from cap_lab.experiment import Variant, load_cases, run_case, with_own_anthropic_client
from cap_lab.scorers import RunRecord, first_failure, score_run
from cap_lab.server.server import FaultPlan
from cap_lab.settings import ROOT, Settings, key_status, load_settings
from cap_lab.stats import wilson_ci

OUTPUT_ROOT = ROOT / "outputs" / "notebook"
_ENV_FILE_VARIABLE = (
    "DAY04_ENV_FILE"  # 서버가 load_settings로 키를 읽을 .env를 가리키는 변수다.
)
_SCORE_VALUE_KEYS = (
    "variant",
    "repeat",
    "case_id",
    "first_failure",
    "error",
    "evidence_dir",
)


def announce(
    purpose: str, *, model_calls: int, jev_calls: int = 0, runs: int = 0
) -> None:
    """유료 호출 직전에 규모를 한 줄로 알린다. 알리기만 하고 멈추지 않는다."""
    parts = [
        text
        for count, text in (
            (model_calls, f"Claude 약 {model_calls}회"),
            (jev_calls, f"Jev 최대 {jev_calls}회"),
            (runs, f"실행 {runs}회"),
        )
        if count
    ]
    if not parts:
        print(f"[{purpose}] 유료 호출 없음. 진행합니다.")
        return
    print(f"[{purpose}] 호출 규모: {', '.join(parts)}입니다. 진행합니다.")


def show_table(rows: list[dict], columns: list[str] | None = None) -> None:
    """행을 줄이지 않고 표로 보여 준다."""
    frame = pd.DataFrame(rows, columns=columns)
    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.width",
        200,
        "display.max_colwidth",
        None,
    ):
        display(frame)


def key_table(settings: Settings | None = None) -> None:
    """실습에 쓰는 키가 설정됐는지만 보여 준다. 값, 앞자리, 길이는 보여 주지 않는다."""
    settings = settings or load_settings()
    status = key_status(settings)
    names = (
        "ANTHROPIC_API_KEY",
        "TYPESAFE_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    )
    rows = [{"환경 변수": name, "상태": status[name]} for name in names]
    rows.append(
        {
            "환경 변수": "LANGFUSE_HOST",
            "상태": "설정됨" if settings.langfuse_host.strip() else "미설정",
        }
    )
    show_table(rows)


def new_workdir(label: str) -> Path:
    """outputs/notebook/<label>-<날짜-시각>/ 폴더를 만들어 돌려준다."""
    path = OUTPUT_ROOT / f"{label}-{datetime.now():%Y%m%d-%H%M%S}"
    path.mkdir(parents=True, exist_ok=False)
    return path


@asynccontextmanager
async def connect_server(
    workdir: Path | str,
    *,
    gate: str = "off",
    threshold: float = 0.5,
    fault: FaultPlan | None = None,
    interface: str = "rich",
    elicitation_callback=None,
) -> AsyncIterator[Client]:
    """cap_lab/server/server.py를 stdio로 띄워 연결한 mcp.Client를 준다. DB와 근거는 workdir 아래에 쓴다.

    서버가 사용자에게 묻는 질문(elicitation)에는 elicitation_callback(context, params)이 답한다.
    """
    workdir = Path(workdir)
    args = server_argv(
        workdir / "sessions.sqlite3",
        workdir / "evidence",
        gate=gate,
        threshold=threshold,
        fault=fault,
        interface=interface,
    )
    env = (
        {_ENV_FILE_VARIABLE: os.environ[_ENV_FILE_VARIABLE]}
        if _ENV_FILE_VARIABLE in os.environ
        else {}
    )
    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER_SCRIPT), *args], env=env, cwd=str(ROOT)
    )
    async with Client(params, elicitation_callback=elicitation_callback) as client:
        yield client


def show_events(evidence_dir: Path | str) -> None:
    """서버가 근거 폴더에 쓴 이벤트를 세션별로 보여 준다. 세션은 앞 8자리, 시간은 파일로 내보낸 시각이다."""
    rows = []
    for path in sorted(Path(evidence_dir).glob("*/event-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        content = record["content"]
        rows.append(
            {
                "세션": record["session_id"][:8],
                "이벤트": content["event"],
                "필드": content["payload"].get("field", ""),
                "시간": record["exported_at"],
            }
        )
    if rows:
        show_table(rows)
    else:
        print(f"근거 이벤트가 없습니다: {evidence_dir}")


def _run_blocking(coroutine: Coroutine[None, None, RunRecord]) -> RunRecord:
    """노트북 셀은 이미 이벤트 루프 안이라 asyncio.run을 바로 못 쓴다. 그때는 별도 스레드에서 돌린다.

    실행마다 새 이벤트 루프를 쓰므로 with_own_anthropic_client가 그 루프 안에서 Anthropic 클라이언트를 새로 만들어
    쓰고 루프가 끝나기 전에 닫는다. 닫힌 루프에 묶인 공유 클라이언트가 다음 실행에 넘어가지 않게 하기 위해서다.
    """
    runner = with_own_anthropic_client(coroutine)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(runner)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, runner).result()


def _dev_cases(case_ids: list[str]) -> list[dict]:
    """홀드아웃 사례는 수업 중 반복 실행으로 눈에 익히지 않도록 거부한다. 실행 전에 모든 ID를 검사한다."""
    by_id = {case["id"]: case for case in load_cases()}
    for case_id in case_ids:
        if case_id not in by_id:
            raise ValueError(
                f"사례 {case_id}가 없습니다. dev-01부터 dev-10까지만 쓸 수 있습니다."
            )
        if by_id[case_id]["split"] != "dev":
            raise ValueError(
                f"{case_id}는 dev 사례가 아닙니다. 수업 중 비교는 dev 사례만 실행합니다."
            )
    return [by_id[case_id] for case_id in case_ids]


def run_small_compare(
    variants: list[Variant],
    case_ids: list[str],
    repeats: int,
    *,
    label: str,
    model=None,
    decider=None,
) -> list[dict]:
    """dev 사례를 변형 x 반복 x 사례 순서로 하나씩 실행하고 채점한다. Langfuse에는 연결하지 않는다.

    한 실행마다 outputs/notebook/<label>-<시각>/rows.jsonl에 한 줄을 덧붙인다. 오류가 난 실행도 행으로 남는다.
    model과 decider는 시험에서 가짜를 넣는 용도다. 수업에서는 주지 않는다.
    """
    cases = _dev_cases(case_ids)
    settings = load_settings()
    workdir = new_workdir(label)
    rows = []
    for repeat in range(1, repeats + 1):
        for variant in variants:
            for case in cases:
                record = _run_blocking(
                    run_case(
                        case,
                        variant=variant,
                        settings=settings,
                        workdir=workdir,
                        repeat=repeat,
                        model=model,
                        decider=decider,
                    )
                )
                scores = score_run(record)
                row = {
                    "variant": variant.name,
                    "repeat": repeat,
                    "case_id": case["id"],
                    **{score.name: score.value for score in scores},
                    "first_failure": first_failure(scores),
                    "error": record.error,
                    "evidence_dir": str(record.evidence_dir),
                }
                with (workdir / "rows.jsonl").open("a", encoding="utf-8") as rows_file:
                    rows_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                rows.append(row)
                print(
                    f"[{label}] {variant.name} 반복 {repeat} {case['id']}: "
                    f"{'오류' if record.error else '완료'}"
                )
    return rows


def pass_rate_table(rows: list[dict], scores: list[str]) -> list[dict]:
    """변형과 검사별 통과 수, 확인한 수, 확인 불가(None) 수, 통과율, Wilson 95% 구간.

    None은 통과로도 실패로도 세지 않는다. 확인 수가 0이면 통과율과 구간도 None이다.
    """
    for name in scores:
        values = [row[name] for row in rows if name in row]
        if rows and not values:
            raise ValueError(
                f"{name}은 어느 행에도 없는 점수입니다. 이름을 확인하세요."
            )
        if any(value is not None and not isinstance(value, bool) for value in values):
            raise ValueError(
                f"{name}은 참/거짓 검사가 아닙니다. 통과율은 참/거짓 검사만 셉니다."
            )
    table = []
    for variant in dict.fromkeys(row["variant"] for row in rows):
        for name in scores:
            values = [row.get(name) for row in rows if row["variant"] == variant]
            passed = values.count(True)
            checked = passed + values.count(False)
            interval = wilson_ci(passed, checked)
            table.append(
                {
                    "variant": variant,
                    "score": name,
                    "passed": passed,
                    "checked": checked,
                    "unchecked": values.count(None),
                    "rate": passed / checked if checked else None,
                    "ci_low": interval[0] if interval else None,
                    "ci_high": interval[1] if interval else None,
                }
            )
    return table
