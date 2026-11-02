"""저장된 실제 vLLM 0.32.0 참조 실행(data/reference_*.json)을 시뮬레이터와 대조한다.

실제 클래스는 여기서 돌리지 않는다. 저장된 `real`을 읽고, 같은 `inputs`를 `kv_sim`에 다시 넣는다.
xfail은 쓰지 않는다. 기록된 차이는 EXPECTED_DIFFERENCES에 이름과 이유로 적는다. 거기 없는 새 차이는 실패한다.
"""
import json
import pathlib

import pytest

from vllm_lab.kv_sim import KVManagerSim, reference_rows

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
KV_PATH = DATA / "reference_kv.json"
PARSER_PATH = DATA / "reference_parser.json"

# 시나리오 이름 -> 차이 이유. 2026-11-01 실행에서는 6개 모두 일치해서 비어 있다.
# real-diff가 차이를 기록하면 여기에 이름과 이유를 적는다. 이 목록을 늘려 새 차이를 감추지 않는다.
EXPECTED_DIFFERENCES: dict[str, str] = {}

SCENARIOS = ("sequential_allocate", "prefix_hit_repeat", "hit_cap_num_tokens_minus_1",
             "different_salt", "free_then_reuse_order", "eviction_under_pressure")
ROW_KEYS = {"op", "request_id", "returned_none", "hit_tokens", "hit_block_ids", "new_block_ids",
            "block_table", "ref_cnts", "free_queue", "cached_block_ids"}


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _kv_doc() -> dict:
    doc = _load(KV_PATH)
    if doc["status"] == "not_run":
        pytest.skip(f"reference_kv.json이 not_run입니다: {doc.get('reason')}")
    return doc


def _roundtrip(rows: list[dict]) -> list[dict]:
    """JSON을 거치면 tuple이 list가 되므로 같은 길을 지나게 해서 비교한다."""
    return json.loads(json.dumps(rows))


def test_kv_file_has_true_status():
    doc = _load(KV_PATH)
    assert doc["status"] in ("ran", "not_run")
    assert doc["vllm"] == "0.32.0"
    if doc["status"] == "not_run":
        assert doc["reason"]


def test_kv_scenarios_are_the_six_fixed_names():
    doc = _kv_doc()
    assert tuple(s["name"] for s in doc["scenarios"]) == SCENARIOS


def test_kv_saved_rows_have_contract_keys():
    for s in _kv_doc()["scenarios"]:
        assert len(s["real"]) == len(s["inputs"]["ops"]) == len(s["sim"]), s["name"]
        for row in s["real"] + s["sim"]:
            assert set(row) == ROW_KEYS, s["name"]


def test_kv_sim_replay_matches_saved_real_except_listed():
    for s in _kv_doc()["scenarios"]:
        sim_now = _roundtrip(KVManagerSim.replay(s["inputs"]))
        same = sim_now == s["real"]
        if s["name"] in EXPECTED_DIFFERENCES:
            assert not same, f"{s['name']}: 차이가 사라졌습니다. EXPECTED_DIFFERENCES에서 지우세요."
        else:
            assert same, f"{s['name']}: 시뮬레이터가 저장된 실제 결과와 다릅니다."


def test_kv_recorded_match_flag_agrees_with_rows():
    for s in _kv_doc()["scenarios"]:
        assert s["match"] == (s["real"] == s["sim"]), s["name"]
        assert s["match"] == (s["name"] not in EXPECTED_DIFFERENCES), s["name"]


def test_kv_saved_sim_equals_current_sim():
    for s in _kv_doc()["scenarios"]:
        assert _roundtrip(KVManagerSim.replay(s["inputs"])) == s["sim"], s["name"]


def test_kv_reference_rows_reports_every_scenario():
    rows = reference_rows(KV_PATH)
    assert [r["name"] for r in rows] == list(SCENARIOS)
    assert all(r["match"] is (r["name"] not in EXPECTED_DIFFERENCES) for r in rows)


def test_kv_design_values_hold_in_real_rows():
    """DESIGN의 표 값이 실제 쪽에서도 나왔는지 확인한다. 값을 코드에 박는 것이 아니라 저장된 real을 읽는다."""
    by_name = {s["name"]: s for s in _kv_doc()["scenarios"]}
    seq = by_name["sequential_allocate"]["real"]
    assert [seq[0]["new_block_ids"], seq[1]["new_block_ids"]] == [[1, 2, 3, 4], [5, 6]]
    assert by_name["prefix_hit_repeat"]["real"][2]["hit_tokens"] == 48
    assert by_name["hit_cap_num_tokens_minus_1"]["real"][2]["hit_tokens"] == 32
    assert by_name["different_salt"]["real"][2]["hit_tokens"] == 0
    assert by_name["eviction_under_pressure"]["real"][4]["hit_tokens"] == 16


def test_parser_file_has_true_status():
    doc = _load(PARSER_PATH)
    assert doc["status"] in ("ran", "partial", "not_run")
    assert doc["vllm"] == "0.32.0"
    if doc["status"] == "not_run":
        pytest.skip(f"reference_parser.json이 not_run입니다: {doc.get('reason')}")
    assert doc["parser"]["tokenizer"] and doc["parser"]["limit"]
    ids = [c["id"] for c in doc["cases"]]
    assert {"clean_call", "reasoning_then_call", "malformed_markup", "truncated_call",
            "unknown_tool", "bad_arg_type", "no_call"} <= set(ids)


def test_parser_cases_are_labeled_constructed_and_consistent():
    doc = _load(PARSER_PATH)
    if doc["status"] == "not_run":
        pytest.skip(f"reference_parser.json이 not_run입니다: {doc.get('reason')}")
    for c in doc["cases"]:
        assert c["constructed"] is True, c["id"]
        assert c["status"] in ("ran", "not_run"), c["id"]
        if c["status"] == "ran":
            assert c["output"] is not None and "tool_calls" in c["output"], c["id"]
            assert c["reason"] is None, c["id"]
        else:
            assert c["output"] is None and c["reason"], c["id"]
        assert "finish_reason" not in (c["output"] or {}), c["id"]
    expected_top = "ran" if all(c["status"] == "ran" for c in doc["cases"]) else "partial"
    assert doc["status"] == expected_top
