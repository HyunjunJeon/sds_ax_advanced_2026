"""사례 파일이 사전 등록 P5·P6의 가드 지표를 모두 재도록 짜였는지 확인한다.

사례 분할(dev, holdout)마다 목표 지표와 그 가드 지표가 적용되는 사례가 하나 이상 있어야 한다.
없으면 compare()가 P5 4번(가드 데이터 없음)으로 '판정 불가: 데이터 부족'을 낸다.
적용 여부는 scorers.py가 정한다. 사례 하나로 채점해 값이 None이 아니면 적용되는 사례다.
DAY04_CASES_FILE로 다른 사례 파일을 가리켜 이 시험이 낡은 데이터에서 실패하는지 확인할 수 있다.
"""
import json
import os
from pathlib import Path

import pytest

from cap_lab.experiment import CASES_PATH, compare, load_cases, prereg_guards
from cap_lab.scorers import RunRecord, score_run

CASES_FILE = os.environ.get("DAY04_CASES_FILE", CASES_PATH)
TARGETS = ("vague_not_frozen", "goal_preserved")
NO_DATA = "판정 불가: 데이터 부족"
# args_valid는 에이전트가 MCP 도구를 하나라도 부를 때 적용되므로 호출 하나가 있는 기록으로 채점한다.
MCP_CALL = {"name": "start_interview", "args": {}, "result": {}, "ok": True}


def applicable_metrics(case: dict, tmp_path: Path) -> set[str]:
    record = RunRecord(case=case, evidence_dir=tmp_path, tool_calls=[MCP_CALL])
    return {score.name for score in score_run(record) if score.value is not None}


@pytest.fixture(scope="module")
def applies(tmp_path_factory) -> dict[str, set[str]]:
    """사례 ID -> 그 사례에 적용되는 지표."""
    empty = tmp_path_factory.mktemp("evidence")
    return {case["id"]: applicable_metrics(case, empty) for case in load_cases(CASES_FILE)}


@pytest.mark.parametrize("split", ["dev", "holdout"])
@pytest.mark.parametrize("target", TARGETS)
def test_every_metric_of_the_decision_rule_has_a_case_in_each_split(split, target, applies):
    split_ids = [case["id"] for case in load_cases(CASES_FILE, split=split)]
    uncovered = [
        metric
        for metric in [target, *prereg_guards(target)]
        if not any(metric in applies[case_id] for case_id in split_ids)
    ]
    assert uncovered == [], f"{split} 사례에 {target} 판정의 지표 {uncovered}를 재는 사례가 없다"


def write_variant_mirror(path: Path, cases: list[dict], applies: dict[str, set[str]], target: str, target_value: float) -> Path:
    """holdout 사례마다 적용되는 모든 지표를 채운 로컬 사본. 목표 지표 값만 변형별로 다르다."""
    lines = []
    for case in cases:
        scores = {metric: 1.0 for metric in applies[case["id"]]}
        if target in scores:
            scores[target] = target_value
        lines.append({
            "case_id": case["id"], "split": "holdout", "error": None, "first_failure": None,
            "scores": [{"name": name, "value": value, "comment": ""} for name, value in scores.items()],
        })
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


@pytest.mark.parametrize("target", TARGETS)
def test_the_holdout_compared_as_a_a2_and_b_reaches_a_verdict(target, applies, tmp_path):
    holdout = load_cases(CASES_FILE, split="holdout")
    a = write_variant_mirror(tmp_path / "A.jsonl", holdout, applies, target, 0.0)
    a2 = write_variant_mirror(tmp_path / "A2.jsonl", holdout, applies, target, 0.0)
    b = write_variant_mirror(tmp_path / "B.jsonl", holdout, applies, target, 1.0)

    result = compare([a], [a2], [b], target=target, guards=prereg_guards(target), split="holdout")

    assert result["guards_without_data"] == []
    assert result["verdict"] != NO_DATA
