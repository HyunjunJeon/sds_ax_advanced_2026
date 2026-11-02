from __future__ import annotations

import json

import pytest

from vllm_lab import agent_sim
from vllm_lab.agent_sim import (
    AgentReuseSim, CaseNotRun, ReferenceMissing, cached_tokens_visible, chatopenai_sends_include_usage,
    diagnosis_rows, finish_reason_rule, flag_matrix, get_parser_case, load_parser_cases, parser_case_table,
    reference_status, render_prompt, reuse_from_recorded, run_scenario, toy_tokenize, validate_tool_args,
)
from vllm_lab.kv_sim import KVPoolExhausted

BLOCK = 16
SYSTEM = "You are a helper. " + " ".join(f"rule{i}" for i in range(40))
TOOL_A = {"name": "alpha", "description": "first tool " + " ".join(f"a{i}" for i in range(20))}
TOOL_B = {"name": "beta", "description": "second tool " + " ".join(f"b{i}" for i in range(20))}


def user(text_id: str, words: int = 40) -> dict:
    return {"role": "user", "content": " ".join(f"{text_id}w{i}" for i in range(words))}


def common_prefix(left: list[int], right: list[int]) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def expected_hit(previous: list[int], current: list[int]) -> int:
    """독립 계산: 앞 요청과 겹치는 앞부분을 block 단위로 내림하고 마지막 token 상한을 적용한다."""
    cap = (len(current) - 1) // BLOCK
    return BLOCK * min(common_prefix(previous, current) // BLOCK, cap)


# --------------------------------------------------------------------------- 렌더링

def test_toy_tokenize_splits_words_and_punctuation_deterministically():
    assert len(toy_tokenize("a, b")) == 3
    assert toy_tokenize("a, b") == toy_tokenize("a, b")
    assert toy_tokenize("a") != toy_tokenize("b")
    assert toy_tokenize("서울 날씨") != toy_tokenize("부산 날씨")


def test_render_prompt_depends_on_tool_order_but_not_dict_key_order():
    tools = [TOOL_A, TOOL_B]
    assert render_prompt("s", tools, []) != render_prompt("s", tools[::-1], [])
    reordered_keys = {"description": TOOL_A["description"], "name": TOOL_A["name"]}
    assert render_prompt("s", [TOOL_A], []) == render_prompt("s", [reordered_keys], [])


# --------------------------------------------------------------------------- 재사용 규칙

def test_append_only_turns_grow_the_hit_by_the_previous_prompt():
    sim = AgentReuseSim()
    messages: list[dict] = []
    prompts: list[list[int]] = []
    hits: list[int] = []
    for index in range(4):
        messages = messages + [user(f"q{index}")]
        prompts.append(render_prompt(SYSTEM, [TOOL_A], messages))
        hits.append(sim.send(SYSTEM, [TOOL_A], messages, output="ok done").hit_tokens)
        messages = messages + [{"role": "assistant", "content": "ok done"}]
    assert hits[0] == 0
    assert hits[1:] == [expected_hit(prompts[i - 1], prompts[i]) for i in range(1, 4)]
    assert hits[1] < hits[2] < hits[3]


def test_system_prompt_change_breaks_the_hit_from_the_first_block():
    sim = AgentReuseSim()
    messages = [user("q0")]
    sim.send(SYSTEM, [TOOL_A], messages)
    same = sim.send(SYSTEM, [TOOL_A], messages + [user("q1")])
    changed = sim.send("Answer briefly. " + SYSTEM, [TOOL_A], messages + [user("q1")])
    assert same.hit_tokens > 0
    assert (changed.hit_tokens, changed.first_miss_block) == (0, 0)


def test_adding_a_tool_keeps_only_the_blocks_before_the_new_tool():
    sim = AgentReuseSim()
    messages = [user("q0")]
    first = render_prompt(SYSTEM, [TOOL_A], messages)
    sim.send(SYSTEM, [TOOL_A], messages)
    follow = messages + [user("q1")]
    result = sim.send(SYSTEM, [TOOL_A, TOOL_B], follow)
    assert result.hit_tokens == expected_hit(first, render_prompt(SYSTEM, [TOOL_A, TOOL_B], follow))
    assert 0 < result.hit_tokens < len(first) // BLOCK * BLOCK


def test_tool_order_change_breaks_the_hit_at_the_first_tool():
    sim = AgentReuseSim()
    sim.send(SYSTEM, [TOOL_A, TOOL_B], [user("q0")])
    swapped = sim.send(SYSTEM, [TOOL_B, TOOL_A], [user("q0")])
    system_blocks = len(render_prompt(SYSTEM, [], [])) // BLOCK
    assert 0 < swapped.hit_blocks <= system_blocks + 1
    assert swapped.hit_blocks < len(render_prompt(SYSTEM, [TOOL_A, TOOL_B], [user("q0")])) // BLOCK - 1


def test_different_cache_salt_shares_no_block_and_same_salt_does():
    sim = AgentReuseSim()
    messages = [user("q0")]
    sim.send(SYSTEM, [TOOL_A], messages, cache_salt="user-a")
    other = sim.send(SYSTEM, [TOOL_A], messages + [user("q1")], cache_salt="user-b")
    same = sim.send(SYSTEM, [TOOL_A], messages + [user("q1")], cache_salt="user-a")
    assert other.hit_tokens == 0
    assert same.hit_tokens > 0


def test_fully_cached_prompt_still_recomputes_the_last_block():
    sim = AgentReuseSim()
    messages = [user("q0")]
    sim.send(SYSTEM, [], messages)
    again = sim.send(SYSTEM, [], messages)
    assert again.hit_tokens == (again.prompt_tokens - 1) // BLOCK * BLOCK
    assert again.first_miss_block is None
    assert again.recomputed_tokens == again.prompt_tokens - again.hit_tokens
    assert again.hit_ratio == again.hit_tokens / again.prompt_tokens


def test_pool_too_small_raises_korean_error_with_numbers():
    sim = AgentReuseSim(num_blocks=3)
    with pytest.raises(KVPoolExhausted) as caught:
        sim.send(SYSTEM, [TOOL_A, TOOL_B], [user("q0")])
    assert (caught.value.requested, caught.value.free) == (caught.value.requested, 2)
    assert caught.value.requested > 2
    assert str(caught.value.requested) in str(caught.value) and "2" in str(caught.value)


# --------------------------------------------------------------------------- 시나리오

def hits(name: str) -> list[int]:
    return [row["hit_tokens"] for row in run_scenario(name)]


def test_scenario_names_are_fixed_and_unknown_name_is_rejected():
    assert agent_sim.SCENARIOS == ("append_only", "system_change", "tool_added", "tool_order_change",
                                   "salt_change", "effort_in_system", "pressure_evict")
    with pytest.raises(ValueError):
        run_scenario("nope")


def test_append_only_scenario_has_growing_hits():
    result = hits("append_only")
    assert result[0] == 0 and result[1] < result[2] < result[3]


def test_system_change_scenario_zero_hit_at_change_then_recovers():
    result = hits("system_change")
    assert result[1] > 0 and result[2] == 0 and result[3] > 0


def test_salt_change_scenario_zero_hit_at_change_then_recovers():
    result = hits("salt_change")
    assert result[1] > 0 and result[2] == 0 and result[3] > 0


@pytest.mark.parametrize("name", ["tool_added", "tool_order_change", "effort_in_system"])
def test_partial_break_scenarios_hit_less_than_append_only_but_not_zero(name):
    changed, baseline = hits(name), hits("append_only")
    assert 0 < changed[2] < baseline[2]
    assert changed[3] > changed[2]


@pytest.mark.parametrize("name", ["tool_added", "tool_order_change", "effort_in_system"])
def test_unverified_render_scenarios_carry_the_toy_assumption(name):
    assert all(row["assumption"] == "toy 렌더링 가정, 실제 template과 tool 위치가 다름(P5-08)"
               for row in run_scenario(name))


def test_scenarios_that_do_not_depend_on_rendering_assumption_leave_it_empty():
    assert all(row["assumption"] == "" for row in run_scenario("system_change"))


def test_pressure_evict_loses_hits_that_append_only_keeps():
    rows = run_scenario("pressure_evict")
    turns = [row for row in rows if row["label"].startswith("턴")]
    baseline = hits("append_only")
    assert len(rows) > len(turns)
    assert all(t["hit_tokens"] < b for t, b in zip(turns[1:], baseline[1:]))


def test_reuse_from_recorded_matches_direct_sends():
    first = {"system": SYSTEM, "tools": [TOOL_A], "messages": [user("q0")]}
    second = {"system": SYSTEM, "tools": [TOOL_A],
              "messages": first["messages"] + [{"role": "assistant", "content": "ok"}, user("q1")]}
    rows = reuse_from_recorded([first, second])
    assert rows[0]["hit_tokens"] == 0
    assert rows[1]["hit_tokens"] == expected_hit(render_prompt(**first), render_prompt(**second))


# --------------------------------------------------------------------------- 서버 조건 표

@pytest.mark.parametrize(("base_url_set", "stream_usage", "expected"), [
    (True, None, False), (False, None, True), (True, True, True), (False, False, False)])
def test_chatopenai_include_usage_follows_stream_usage_then_base_url(base_url_set, stream_usage, expected):
    assert chatopenai_sends_include_usage(base_url_set=base_url_set, stream_usage=stream_usage) is expected


@pytest.mark.parametrize(("flag", "stream", "client", "force", "visible"), [
    (False, False, True, True, False), (True, False, False, False, True),
    (True, True, False, False, False), (True, True, True, False, True), (True, True, False, True, True)])
def test_cached_tokens_visible_conditions(flag, stream, client, force, visible):
    result = cached_tokens_visible(server_flag=flag, stream=stream, client_sends_include_usage=client,
                                   force_include_usage=force)
    assert result["visible"] is visible and result["why"]


def test_flag_matrix_has_four_combinations_marked_as_code_reading():
    rows = flag_matrix()
    assert {(r["--enable-auto-tool-choice"], r["--tool-call-parser"]) for r in rows} == {
        (True, True), (True, False), (False, True), (False, False)}
    assert {r["근거 종류"] for r in rows} == {"코드 읽기"}
    only_enable = next(r for r in rows if r["--enable-auto-tool-choice"] and not r["--tool-call-parser"])
    assert "TypeError" in only_enable["시작 단계"]


@pytest.mark.parametrize(("engine", "choice", "extracted", "stream", "expected"), [
    ("length", "auto", True, False, "tool_calls"),
    ("length", "auto", True, True, "length"),
    ("stop", "auto", True, True, "tool_calls"),
    ("stop", "required", False, False, "tool_calls"),
    ("length", "required", True, False, "length"),
    ("stop", "named", True, False, "stop"),
    ("stop", "named", True, True, "stop"),
    (None, "none", False, False, "stop"),
    ("stop", "auto", False, False, "stop"),
])
def test_finish_reason_rule_table(engine, choice, extracted, stream, expected):
    assert finish_reason_rule(engine_finish_reason=engine, tool_choice=choice,
                              calls_extracted=extracted, stream=stream) == expected


def test_finish_reason_rule_rejects_unknown_tool_choice():
    with pytest.raises(ValueError):
        finish_reason_rule(engine_finish_reason="stop", tool_choice="any", calls_extracted=True, stream=False)


SCHEMA = {"type": "object", "required": ["city", "days"],
          "properties": {"city": {"type": "string"}, "days": {"type": "integer"}, "hot": {"type": "boolean"}}}


def test_validate_tool_args_passes_a_good_call():
    assert validate_tool_args(SCHEMA, '{"city": "서울", "days": 3, "hot": true}') == []


def test_validate_tool_args_reports_each_defect():
    assert len(validate_tool_args(SCHEMA, "{not json")) == 1
    assert len(validate_tool_args(SCHEMA, "[1]")) == 1
    missing = validate_tool_args(SCHEMA, '{"city": "서울"}')
    assert len(missing) == 1 and "days" in missing[0]
    wrong = validate_tool_args(SCHEMA, '{"city": "서울", "days": "three"}')
    assert len(wrong) == 1 and "days" in wrong[0]


def test_validate_tool_args_does_not_treat_bool_as_integer_or_number():
    assert validate_tool_args(SCHEMA, '{"city": "x", "days": true}') != []
    number = {"properties": {"x": {"type": "number"}}}
    assert validate_tool_args(number, '{"x": 1.5}') == []
    assert validate_tool_args(number, '{"x": false}') != []


# --------------------------------------------------------------------------- Part 6 기록 읽기

def case(case_id: str, *, candidates=(), status: str = "ran", output="default", reason=None) -> dict:
    if output == "default":
        output = {"reasoning": None, "content": None, "error": None,
                  "tool_calls": [{"name": "get_temperature", "arguments": "{\"city\": \"서울\"}"}]}
    return {"id": case_id, "candidates": list(candidates), "layer": "parser", "title": f"제목 {case_id}",
            "constructed": True, "raw_text": f"<tool_call>{case_id}", "tools": ["get_temperature"],
            "tool_choice": "auto", "mode": "non_stream", "status": status, "reason": reason,
            "output": output if status == "ran" else None}


def write_reference(tmp_path, cases, *, status="ran", reason=None):
    path = tmp_path / "reference_parser.json"
    path.write_text(json.dumps({"status": status, "vllm": "0.32.0", "reason": reason,
                                "parser": {"tool": "glm47", "tokenizer": "대체물", "limit": "제한"},
                                "cases": cases}), encoding="utf-8")
    return path


def test_valid_reference_loads_cases_with_every_field(tmp_path):
    path = write_reference(tmp_path, [case("clean_call"), case("truncated_call", candidates=["C2", "C6"])])
    cases = load_parser_cases(path)
    assert [c.id for c in cases] == ["clean_call", "truncated_call"]
    assert cases[1].candidates == ("C2", "C6")
    assert cases[0].tools == ("get_temperature",) and cases[0].constructed is True
    assert get_parser_case("clean_call", path).output["tool_calls"][0]["name"] == "get_temperature"
    assert reference_status(path)["status"] == "ran"
    assert reference_status(path)["parser"]["tool"] == "glm47"


def test_unknown_case_id_is_a_key_error(tmp_path):
    path = write_reference(tmp_path, [case("clean_call")])
    with pytest.raises(KeyError):
        get_parser_case("nope", path)


def test_missing_file_raises_reference_missing_and_status_reports_it(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(ReferenceMissing) as caught:
        load_parser_cases(path)
    assert "absent.json" in str(caught.value)
    with pytest.raises(ReferenceMissing):
        parser_case_table(path)
    assert reference_status(path)["status"] == "missing"
    assert {row["근거 종류"] for row in diagnosis_rows(path) if not row["사례"].startswith("C12")} == {"코드 읽기"}


def test_top_level_not_run_raises_case_not_run_with_the_recorded_reason(tmp_path):
    path = write_reference(tmp_path, [], status="not_run", reason="GLM 파서 import 실패: 모듈 없음")
    with pytest.raises(CaseNotRun) as caught:
        load_parser_cases(path)
    assert "GLM 파서 import 실패: 모듈 없음" in str(caught.value)
    status = reference_status(path)
    assert (status["status"], status["reason"]) == ("not_run", "GLM 파서 import 실패: 모듈 없음")


def test_not_run_case_raises_and_table_shows_not_run_cells(tmp_path):
    path = write_reference(tmp_path, [case("clean_call"), case("bad_arg_type", status="not_run", reason="토크나이저 없음")],
                           status="partial")
    with pytest.raises(CaseNotRun) as caught:
        get_parser_case("bad_arg_type", path)
    assert "토크나이저 없음" in str(caught.value)
    rows = {row["id"]: row for row in parser_case_table(path)}
    skipped = rows["bad_arg_type"]
    assert (skipped["reasoning"], skipped["content"], skipped["tool_calls"]) == ("실행 안 함",) * 3
    assert skipped["근거 종류"] == "실행 안 함"
    assert rows["clean_call"]["근거 종류"] == "실제 GLM 파서, 구성 문자열"
    assert rows["clean_call"]["tool_calls"][0]["name"] == "get_temperature"
    assert reference_status(path)["status"] == "partial"


def test_ran_case_without_output_is_rejected_instead_of_invented(tmp_path):
    bad = case("clean_call")
    bad["output"] = None
    path = write_reference(tmp_path, [bad])
    with pytest.raises(ValueError):
        load_parser_cases(path)


def test_case_missing_a_field_names_the_field(tmp_path):
    broken = case("clean_call")
    del broken["raw_text"]
    path = write_reference(tmp_path, [broken])
    with pytest.raises(ValueError) as caught:
        load_parser_cases(path)
    assert "raw_text" in str(caught.value)


def test_malformed_json_never_looks_like_a_result(tmp_path):
    path = tmp_path / "reference_parser.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError):
        load_parser_cases(path)
    assert reference_status(path)["status"] == "not_run"


def test_default_path_is_data_dir_reference_parser(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_sim, "DATA_DIR", tmp_path)
    with pytest.raises(ReferenceMissing) as caught:
        load_parser_cases()
    assert str(tmp_path / "reference_parser.json") in str(caught.value)
    write_reference(tmp_path, [case("clean_call")])
    assert [c.id for c in load_parser_cases()] == ["clean_call"]


def test_diagnosis_rows_mark_evidence_only_for_candidates_with_a_ran_case(tmp_path):
    path = write_reference(tmp_path, [
        case("truncated_call", candidates=["C2", "C6"]),
        case("unknown_tool", candidates=["C3"], status="not_run", reason="없음"),
    ], status="partial")
    rows = {row["사례"].split(".")[0]: row for row in diagnosis_rows(path)}
    assert len(rows) == 12 and list(rows) == [f"C{i}" for i in range(1, 13)]
    assert rows["C2"]["근거 종류"] == rows["C6"]["근거 종류"] == "실제 GLM 파서, 구성 문자열"
    assert rows["C3"]["근거 종류"] == "코드 읽기"
    assert rows["C1"]["근거 종류"] == "코드 읽기"
    assert rows["C12"]["근거 종류"] == "client 코드"
    assert set(rows["C1"]) == {"사례", "층", "증상(가설)", "볼 곳", "재현 조건", "근거 종류"}


def test_not_modeled_is_a_tuple_of_korean_sentences():
    assert isinstance(agent_sim.NOT_MODELED, tuple) and agent_sim.NOT_MODELED
    assert all(isinstance(s, str) and any("가" <= ch <= "힣" for ch in s) for s in agent_sim.NOT_MODELED)


def test_flag_matrix_says_tools_requests_fail_and_keeps_none_note_within_display_limit():
    rows = flag_matrix()
    parser_only = next(r for r in rows if not r["--enable-auto-tool-choice"] and r["--tool-call-parser"])
    assert "400 문구가 난다" in parser_only["tool_choice=auto 요청"]
    neither = next(r for r in rows if not r["--enable-auto-tool-choice"] and not r["--tool-call-parser"])
    assert neither["tool_choice=auto 요청"].index("tool_choice=none은 통과") < 120


def test_diagnosis_scopes_c6_to_non_streaming_and_c3_c4_c7_to_servers_without_structural_tag():
    rows = {row["사례"].split(".")[0]: row for row in diagnosis_rows(None)}
    assert rows["C6"]["증상(가설)"].startswith("비스트리밍에서는")
    for code in ("C3", "C4", "C7"):
        assert "VLLM_ENFORCE_STRICT_TOOL_CALLING=0" in rows[code]["재현 조건"]


def test_settled_rows_do_not_carry_stale_unverified_marks():
    text = " ".join(agent_sim.NOT_MODELED)
    assert "P5-08, 미확인" not in text and "P5-21, 미확인" not in text
    assert "(P5-21)" in text and "(P5-08)" in text
    assert "미확인" not in agent_sim.TOY_ASSUMPTION


def test_diagnosis_c5_c10_c11_match_the_failure_case_list():
    rows = {row["사례"].split(".")[0]: row for row in diagnosis_rows(None)}
    assert rows["C10"]["층"] == "parser"
    assert "/tokenize" in rows["C11"]["재현 조건"] and "확인하지 않았다" not in rows["C11"]["재현 조건"]
    assert "기본 구성의 문법이 막지 않으므로 나올 수 있다" in rows["C5"]["재현 조건"]
