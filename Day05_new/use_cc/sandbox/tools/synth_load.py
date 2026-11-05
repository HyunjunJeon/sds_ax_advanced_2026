"""합성 7일치 배경 운영 기록을 내 Langfuse 프로젝트에 한 번 적재한다. 모델을 부르지 않는다(모델 호출 0회).

사용법 (실습 폴더에서):
    ./lab tools/synth_load.py --dry-run                 보내지 않고 계획·로컬 JSONL·요약표만 만든다(Langfuse 키 불필요)
    ./lab tools/synth_load.py                           environment synth_ops에 한 번 적재한다
    ./lab tools/synth_load.py --environment synth_ops_2   이미 한 번 적재했다면 새 이름으로 다시 만든다

기록은 주문 시뮬레이터가 만든 실제 Episode에 합성 시각·지연·토큰·비용·generation observation을 입힌 것이다.
LLM 성능이 아니다. 같은 id를 다시 보내면 중복이 보일 수 있으므로, 비어 있지 않은 environment에는 보내지 않고
아무것도 지우지 않는다.

로컬 기록이 남는 곳:
    outputs/notebook/synth-ops/<실행>/episodes.jsonl          실제로 적재한 기록. m3a·m4·m5가 읽는다
    outputs/notebook/synth-ops/<실행>/load.json               적재 표지(environment, seed, 날짜 범위, 보낸 수, 읽힌 root 수)
    outputs/notebook/synth-ops-dryrun/<실행>/...              --dry-run 기록. 보내지 않았으므로 미션이 읽지 않는다
--dry-run 기록을 따로 두는 이유: 날짜는 실행한 날을 기준으로 정해지므로, 다른 날 만든 연습 기록은
Langfuse에 올라간 기록과 날짜가 어긋난다. "synth-ops의 가장 최근 기록"이 항상 실제 적재 기록이 되게 한다.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from eval_lab import online, synth
from eval_lab.notebook import announce, langfuse_or_none, new_run_dir
from eval_lab.trajectory_rules import evaluate_trajectory

WAIT_TIMEOUT_S = 300  # Langfuse 집계는 비동기라, 적재 뒤 root가 다 읽힐 때까지 최대 이만큼 기다린다.
CAUTION = ("주의: 합성 배경 기록입니다. 사건(도구 호출·결과)은 주문 시뮬레이터에서 나왔고, "
           "시각·지연·토큰·비용은 합성 값입니다. 모델 성능이 아닙니다.")
LOADED_STEM = "synth-ops"  # 실제로 적재한 기록의 폴더 이름. 미션은 이 폴더만 읽는다.
DRY_RUN_STEM = "synth-ops-dryrun"  # --dry-run 기록의 폴더 이름. 보내지 않았으므로 미션이 읽지 않는다.
MARKER_NAME = "load.json"  # 실행 폴더마다 남기는 적재 표지.


def check_environment_is_empty(client, environment: str) -> int:
    """environment에 이미 root(episode)가 있으면 보내지 않고 멈춘다. 비어 있으면 0을 돌려준다.

    같은 id를 다시 보내면 중복이 보일 수 있다. 그래서 기존 기록을 지우거나 덮지 않고, 새 environment 이름을 권한다.
    """
    existing_root_count = synth.existing_root_count(client, environment)
    if existing_root_count > 0:
        raise SystemExit(
            f"environment {environment}에 이미 Episode가 {existing_root_count}건 이상 있어 보내지 않았습니다. "
            "같은 id를 다시 보내면 중복 데이터가 생길 수 있습니다. 아무것도 지우지 않았습니다. "
            f"다시 만들려면 새 이름을 쓰세요: ./lab tools/synth_load.py --environment {environment}_2")
    return existing_root_count


def write_marker(folder: Path, *, environment: str, seed: int, records: list[dict], exported: bool,
                 sent_spans: int | None = None, rejected_spans: int | None = None,
                 roots_counted: int | None = None) -> Path:
    """실행 폴더에 적재 표지(load.json)를 남긴다. 나중 미션이 '어느 기록이 실제로 올라갔는가'를 이 파일로 안다.

    exported가 False면 --dry-run 기록이다. 보낸 수·읽힌 root 수를 모르면 None으로 둔다(0으로 채우지 않는다).
    키 값은 담지 않는다.
    """
    dates = sorted({record["date"] for record in records})
    marker = {
        "environment": environment,
        "seed": seed,
        "story_id": synth.STORY_ID,
        "written_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "episodes": len(records),
        "exported": exported,
        "sent_spans": sent_spans,
        "rejected_spans": rejected_spans,
        "roots_counted": roots_counted,
        "records": "episodes.jsonl",
    }
    path = folder / MARKER_NAME
    path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def summarize_by_date(records: list[dict]) -> list[dict]:
    """로컬 기록을 날짜별로 묶는다: 날짜, story_day, Episode 수, 버전별 수, 궤적 PASS·FAIL, 도구 오류가 있던 Episode 수."""
    days: dict[str, dict] = {}
    for record in records:
        row = days.setdefault(record["date"], {"date": record["date"], "story_day": record["story_day"],
                                               "episodes": 0, "versions": Counter(), "verdicts": Counter(),
                                               "tool_error_episodes": 0})
        artifact = record["artifact"]
        row["episodes"] += 1
        row["versions"][record["version"]] += 1
        row["verdicts"][evaluate_trajectory(artifact).status] += 1
        if any(event.result.get("status") == "error" for event in artifact.events):
            row["tool_error_episodes"] += 1
    return sorted(days.values(), key=lambda row: row["date"])


def print_summary(rows: list[dict]) -> None:
    print("날짜 | story_day | Episodes | agent-v1 | agent-v2 | 궤적 PASS | 궤적 FAIL | 도구 오류가 있던 Episode")
    for row in rows:
        print(f"{row['date']} | {row['story_day']} | {row['episodes']} | {row['versions']['agent-v1']} | "
              f"{row['versions']['agent-v2']} | {row['verdicts']['PASS']} | {row['verdicts']['FAIL']} | "
              f"{row['tool_error_episodes']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="합성 7일 배경 기록을 Langfuse에 한 번 적재한다(모델 호출 0회)")
    parser.add_argument("--environment", default=synth.DEFAULT_ENVIRONMENT, help="Langfuse environment(기본 synth_ops)")
    parser.add_argument("--seed", type=int, default=synth.DEFAULT_SEED, help="이야기 시드(기본 7)")
    parser.add_argument("--dry-run", action="store_true", help="보내지 않고 로컬 기록만 만든다")
    arguments = parser.parse_args()

    # 1단계: environment 이름을 검사하고, 오늘을 기준일로 7일 계획을 세워 옷을 입힌다(모델 호출 없음).
    try:
        environment = synth.validate_environment(arguments.environment)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    import ops  # 실습 폴더의 ops.py. 이어서 처리 요청(fx-ops-resume)을 만든다.

    plans = synth.plan_episodes(synth.DEFAULT_STORY, seed=arguments.seed, anchor=datetime.now(UTC),
                                resume_factory=ops.resume_item)
    dressed = synth.dress(synth.simulate(plans), environment=environment)

    # 2단계: 규모를 알린다. Hobby 요금제는 trace + observation + score를 한 달 5만 unit으로 센다.
    estimate = synth.estimate_observations(dressed)
    announce(f"합성 배경 기록 적재(environment {environment})", model_calls=0)
    print(f"Langfuse에는 trace {estimate['traces']}개 + observation {estimate['observations']}개 = "
          f"약 {estimate['units']} unit이 듭니다. Hobby 요금제는 trace·observation·score를 합쳐 월 5만 unit을 셉니다.")

    # 3단계: 보내기 전에 빈 environment인지 확인한다. 키가 없으면 멈춘다.
    client = None
    if not arguments.dry_run:
        client = langfuse_or_none()
        if client is None:
            raise SystemExit("Langfuse 키가 없습니다. ./lab tools/keys.py 로 상태를 보고, .env를 직접 채우세요.")
        check_environment_is_empty(client, environment)

    # 4단계: 로컬 JSONL을 쓴다. 실제 적재는 synth-ops/, --dry-run은 synth-ops-dryrun/ 아래에 둔다.
    records = synth.local_records(dressed)
    stem = DRY_RUN_STEM if arguments.dry_run else LOADED_STEM
    path = synth.write_local_records(new_run_dir(stem) / "episodes.jsonl", records)
    print(f"로컬 기록: {path} ({len(records)}건)")

    # 5단계: 적재하고 집계를 기다린다. 모자라면 모자란 대로 보여 준다. 끝나면 적재 표지(load.json)를 남긴다.
    trace_url = None
    if arguments.dry_run:
        write_marker(path.parent, environment=environment, seed=arguments.seed, records=records, exported=False)
        print("--dry-run: Langfuse로 보내지 않았습니다. 이 기록은 연습용이라 m3a·m4·m5가 읽지 않습니다.")
    else:
        from eval_lab.settings import load_settings

        outcome = synth.export_otlp(dressed, settings=load_settings(), environment=environment)
        print(f"보냄: span {outcome['exported']}개, 거절 {outcome['failed']}개 (trace {outcome['traces']}, "
              f"observation {outcome['observations']})")
        counted, waited = online.wait_for_observations(client, online.root_filter(environment),
                                                       expected=len(dressed), timeout_s=WAIT_TIMEOUT_S)
        print(f"집계 대기 {waited}초, 읽힌 root {counted}/{len(dressed)}건"
              + ("" if counted >= len(dressed) else " (모자랍니다. 집계 지연일 수 있으니 몇 분 뒤 다시 확인하세요)"))
        marker = write_marker(path.parent, environment=environment, seed=arguments.seed, records=records,
                              exported=True, sent_spans=outcome["exported"], rejected_spans=outcome["failed"],
                              roots_counted=counted)
        print(f"적재 표지: {marker} (m3a·m4·m5는 이 폴더의 episodes.jsonl을 읽습니다)")
        trace_url = client.get_trace_url(trace_id=dressed[0].trace_id)

    # 6단계: 날짜별 요약, 보는 법, 주의 문구.
    print_summary(summarize_by_date(records))
    if trace_url:
        print(f"trace 하나: {trace_url}")
    print(f"보는 법: Langfuse Tracing에서 environment {environment}, 시간 범위를 'Past 7 days' 이상으로 고르세요. "
          f"표로는 ./lab tools/lf_table.py {environment} --minutes 10080")
    print(CAUTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
