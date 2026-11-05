"""Langfuse에 남은 Episode(root observation)를 표로 본다. 모델을 부르지 않는다.

사용법 (실습 폴더에서):
    ./lab tools/lf_table.py cc_m1                     environment가 cc_m1인 최근 Episode
    ./lab tools/lf_table.py cc_ops --version agent-v1  version 라벨로 거른다
    ./lab tools/lf_table.py cc_ops --limit 50 --minutes 120

칸: 시작 시각, 사례(scenario_id), version, 응답 유형, Code 궤적 판정, 치명 규칙, Langfuse 주소.
Code 궤적 판정은 Langfuse에 저장된 Episode 요약(root output)으로 eval_lab.trajectory_rules를 다시 돌린 값이다(점수를 읽는 것이 아니다).
Langfuse v2 관측 API만 쓴다. v1(trace 목록·관측 목록)은 Langfuse Cloud에서 2026-11-16에 없어진다.
방금 실행한 Episode가 안 보이면 집계 지연이다. 1~2분 뒤 다시 실행한다.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

from eval_lab.notebook import langfuse_or_none
from eval_lab.online import artifact_from_root_observation, root_filter
from eval_lab.trajectory_rules import evaluate_trajectory


def main() -> None:
    parser = argparse.ArgumentParser(description="Langfuse의 Episode를 표로 본다(모델 호출 없음)")
    parser.add_argument("environment", help="Langfuse environment 이름(예: cc_m1, cc_ops)")
    parser.add_argument("--version", help="이 version 라벨만")
    parser.add_argument("--limit", type=int, default=30, help="최대 행 수(기본 30)")
    parser.add_argument("--minutes", type=int, default=240, help="최근 몇 분(기본 240)")
    arguments = parser.parse_args()

    langfuse = langfuse_or_none()
    if langfuse is None:
        raise SystemExit("Langfuse 키가 없습니다. ./lab tools/keys.py 로 상태를 보세요.")

    # 1단계: environment와 root(episode) 조건, 필요하면 version 조건을 더한다.
    conditions = json.loads(root_filter(arguments.environment))
    if arguments.version:
        conditions.append({"type": "string", "column": "version", "operator": "=", "value": arguments.version})
    since = datetime.now(UTC) - timedelta(minutes=arguments.minutes)
    response = langfuse.api.observations.get_many(fields="core,basic,io", limit=arguments.limit,
                                                  filter=json.dumps(conditions), from_start_time=since)

    # 2단계: 행마다 요약을 Artifact로 되살려 Code 궤적 판정을 다시 계산한다. 되살리지 못하면 그 이유를 적는다.
    rows = []
    for item in response.data:
        artifact, reason = artifact_from_root_observation(item)
        if artifact is None:
            verdict, fatal, kind, scenario = "읽지 못함", reason, "-", "-"
        else:
            result = evaluate_trajectory(artifact)
            verdict = result.status
            fatal = ",".join(hit.rule_id for hit in result.fatal) or "-"
            kind = artifact.response.kind if artifact.response else "-"
            scenario = artifact.scenario_id
        rows.append((item.start_time.strftime("%H:%M:%S"), scenario, item.version or "-", kind, verdict, fatal,
                     langfuse.get_trace_url(trace_id=item.trace_id)))

    # 3단계: 출력한다. 오래된 것부터.
    print(f"environment={arguments.environment} version={arguments.version or '(전체)'} 최근 {arguments.minutes}분, {len(rows)}건")
    print("(방금 실행한 것이 없으면 집계 지연이다. 1~2분 뒤 다시 실행한다.)")
    for row in sorted(rows):
        print(" | ".join(str(cell) for cell in row))


if __name__ == "__main__":
    main()
