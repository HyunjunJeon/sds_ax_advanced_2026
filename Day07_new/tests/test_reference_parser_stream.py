"""저장된 스트리밍 파서 실행(data/reference_parser_stream.json)과 Rust 파서 실행(data/reference_parser_rust.json)을
읽어 형태와 06의 서술을 대조한다.

실제 클래스는 여기서 돌리지 않는다. 실행 방법과 범위는 docs/reference/parser_stream.md, docs/reference/parser_rust.md에 있다.
xfail은 쓰지 않는다. status가 not_run일 때만 건너뛴다.
"""
import json
import pathlib

import pytest

from vllm_lab.agent_sim import finish_reason_rule

ROOT = pathlib.Path(__file__).resolve().parent.parent
STREAM_PATH = ROOT / "data" / "reference_parser_stream.json"
STUB_PATH = ROOT / "data" / "reference_parser.json"
RUST_PATH = ROOT / "data" / "reference_parser_rust.json"
NOTEBOOK_06 = ROOT / "06-Tool-Calling-Errors.ipynb"

MARKUP_IDS = {"<think>": 154841, "</think>": 154842, "<tool_call>": 154843, "</tool_call>": 154844,
              "<arg_key>": 154847, "</arg_key>": 154848, "<arg_value>": 154849, "</arg_value>": 154850}
ROW_KEYS = {"id", "candidates", "constructed", "raw_text", "tools", "token_ids", "tokens", "engine_finish", "stop_token_id",
            "decoded_equals_raw", "deltas_in", "stream", "non_stream", "same", "grammar", "finish_reason_by_engine_finish",
            "variants", "status", "reason"}
RESULT_KEYS = {"reasoning", "content", "tool_calls", "finish_reason", "error", "arguments_json_valid"}
# 8개 중 스트리밍과 비스트리밍의 값이 갈린 곳. 새로 갈리거나 사라지면 실패한다.
TOOL_CALLS_DIFFER = {"malformed_markup", "truncated_call"}
FINISH_REASON_DIFFERS = {"truncated_call"}


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _doc() -> dict:
    doc = _load(STREAM_PATH)
    if doc["status"] == "not_run":
        pytest.skip(f"reference_parser_stream.json이 not_run입니다: {doc.get('reason')}")
    return doc


def _ran_rows(doc: dict) -> list[dict]:
    return [row for row in doc["cases"] + doc["extra_cases"] if row["status"] == "ran"]


def _rows() -> dict[str, dict]:
    return {row["id"]: row for row in _ran_rows(_doc())}


def test_file_has_true_status():
    doc = _load(STREAM_PATH)
    assert doc["status"] in ("ran", "partial", "not_run")
    assert doc["vllm"] == "0.32.0"
    assert doc["evidence"] and doc["limit"]
    if doc["status"] != "ran":
        assert doc["reason"]


def test_tokenizer_is_the_real_one_without_weights():
    tokenizer = _doc()["tokenizer"]
    assert tokenizer["status"] == "real"
    assert tokenizer["source"] == "zai-org/GLM-5.3-Flash"
    assert len(tokenizer["revision"]) == 40
    assert set(tokenizer["files_sha256"]) == {"tokenizer.json", "tokenizer_config.json", "chat_template.jinja"}
    assert all(len(value) == 64 for value in tokenizer["files_sha256"].values())
    assert tokenizer["weights_downloaded"] is False
    assert tokenizer["fast_detokenizer"] is True


def test_cases_are_the_eight_of_the_parser_record_in_order():
    doc, stub = _doc(), _load(STUB_PATH)
    assert [row["id"] for row in doc["cases"]] == [case["id"] for case in stub["cases"]]
    for row, case in zip(doc["cases"], stub["cases"]):
        assert (row["raw_text"], row["tools"], row["candidates"]) == (case["raw_text"], case["tools"], case["candidates"])
    assert all(row["constructed"] is True for row in doc["cases"] + doc["extra_cases"])


def test_rows_have_contract_keys():
    doc = _doc()
    assert doc["status"] == "ran"
    for row in doc["cases"] + doc["extra_cases"]:
        assert ROW_KEYS <= set(row), row["id"]
        assert RESULT_KEYS <= set(row["stream"]), row["id"]
        assert RESULT_KEYS <= set(row["non_stream"]), row["id"]
        assert set(row["finish_reason_by_engine_finish"]) == {"stop", "length"}, row["id"]


def test_deltas_are_real_tokens_that_rebuild_the_input():
    for row in _ran_rows(_doc()):
        stop = [row["stop_token_id"]] if row["stop_token_id"] is not None else []
        assert [i for delta in row["deltas_in"] for i in delta["ids"]] == row["token_ids"] + stop, row["id"]
        assert "".join(delta["text"] for delta in row["deltas_in"]) == row["raw_text"], row["id"]
        assert row["decoded_equals_raw"] is True, row["id"]
        for marker, token_id in MARKUP_IDS.items():
            assert row["token_ids"].count(token_id) == row["raw_text"].count(marker), (row["id"], marker)


def test_stream_went_through_parse_delta_and_extract_tool_calls_streaming():
    rows = _rows()
    for row in rows.values():
        assert row["stream"]["calls"]["parse_delta"] == len(row["deltas_in"]), row["id"]
    assert rows["clean_call"]["stream"]["calls"]["extract_tool_calls_streaming"] > 0
    assert rows["no_call_missing_think_end"]["stream"]["calls"]["extract_tool_calls_streaming"] == 0


def test_saved_same_flags_agree_with_rows():
    for row in _ran_rows(_doc()):
        stream, non_stream, same = row["stream"], row["non_stream"], row["same"]
        assert same["tool_calls_same"] == (stream["tool_calls"] == non_stream["tool_calls"]), row["id"]
        assert same["tools_called_same"] == (stream["tools_streamed"] == non_stream["tools_called"]), row["id"]
        assert same["reasoning_same"] == (stream["reasoning"] == non_stream["reasoning"]), row["id"]
        assert same["content_same"] == (stream["content"] == non_stream["content"]), row["id"]
        assert same["finish_reason_same"] == (stream["finish_reason"] == non_stream["finish_reason"]), row["id"]


def test_saved_json_validity_agrees_with_arguments():
    def valid(text: str) -> bool:
        try:
            json.loads(text)
        except ValueError:
            return False
        return True

    for row in _ran_rows(_doc()):
        for mode in ("stream", "non_stream"):
            result = row[mode]
            assert result["arguments_json_valid"] == [valid(call["arguments"]) for call in result["tool_calls"]], row["id"]


def test_only_the_recorded_cases_differ_between_paths():
    doc = _doc()
    assert {row["id"] for row in doc["cases"] if not row["same"]["tool_calls_same"]} == TOOL_CALLS_DIFFER
    assert {row["id"] for row in doc["cases"] if not row["same"]["finish_reason_same"]} == FINISH_REASON_DIFFERS
    for row in doc["cases"]:
        assert row["same"]["tools_called_same"] and row["same"]["reasoning_same"] and row["same"]["content_same"], row["id"]


def test_non_stream_with_real_tokenizer_equals_the_stub_record():
    stub = {case["id"]: case["output"] for case in _load(STUB_PATH)["cases"]}
    for row in _doc()["cases"]:
        result = row["non_stream"]
        assert (result["reasoning"], result["content"], result["tool_calls"]) == (
            stub[row["id"]]["reasoning"], stub[row["id"]]["content"], stub[row["id"]]["tool_calls"]), row["id"]
        assert row["non_stream_equals_stub_record"] is True, row["id"]


def test_split_size_and_token_ids_do_not_change_the_result():
    for row in _ran_rows(_doc()):
        assert {(v["chunk_tokens"], v["delta_token_ids"]) for v in row["variants"]} == {(4, True), ("all", True), (1, False)}
        assert all(v["same_as_primary"] and v["result"] is None for v in row["variants"]), row["id"]


def test_course_finish_reason_rule_matches_the_real_generators():
    for row in _ran_rows(_doc()):
        for engine, seen in row["finish_reason_by_engine_finish"].items():
            if row["id"] == "omitted_tools_call":
                continue  # tools 없는 요청은 finish_reason_rule의 tool_choice 네 값 밖이다.
            assert seen["stream"] == finish_reason_rule(engine_finish_reason=engine, tool_choice="auto", stream=True,
                                                        calls_extracted=row["stream"]["tools_streamed"]), row["id"]
            assert seen["non_stream"] == finish_reason_rule(engine_finish_reason=engine, tool_choice="auto", stream=False,
                                                            calls_extracted=row["non_stream"]["tools_called"]), row["id"]


def test_reasoning_end_is_decided_by_token_id():
    checks = _doc()["token_id_checks"]
    assert {t: checks["vocab"][t]["id"] for t in MARKUP_IDS} == MARKUP_IDS
    assert not any(checks["vocab"][t]["in_all_special_tokens"] for t in MARKUP_IDS)
    assert checks["vocab"]["<|observation|>"]["in_all_special_tokens"] is True
    assert checks["skip_special_tokens_true_keeps_markup"] == "<tool_call>x<arg_key>a</arg_key></tool_call>"
    assert checks["reasoning_end_token_ids"] == [MARKUP_IDS["</think>"], MARKUP_IDS["<tool_call>"]]
    decided = {row["input"]: row["is_reasoning_end"] for row in checks["rows"]}
    assert decided == {
        "프롬프트만 (끝이 <think>)": False,
        "프롬프트 + 생각 중": False,
        "프롬프트 + 생각 + </think>": True,
        "프롬프트 + 생각 + </think> + 답": True,
        "프롬프트 + <tool_call> (</think> 없음)": True,
        "이전 턴에 </think>가 있고 새 프롬프트가 <think>로 끝남": False,
        "<|assistant|>로 끝남 (<think> 없음)": False,
        "빈 목록": False,
    }


def test_stream_reasoning_count_misses_tokens_with_empty_text():
    for row in _doc()["token_id_checks"]["count_reasoning_tokens"]:
        assert row["non_stream"] == row["tokens_before_think_end"]
        assert row["stream"] == row["tokens_before_think_end"] - row["empty_text_tokens_before_think_end"]
        assert row["empty_text_tokens_before_think_end"] > 0


def test_real_template_is_always_thinking():
    always = _doc()["always_thinks"]
    assert always["chat_template_type"] == "str"
    assert always["always_thinks"] is True
    assert all(always["conditions"].values())
    assert all(render["ends_with_think"] for render in always["prompt_render"].values())
    assert all(parser["thinking_enabled"] for parser in always["parser_with_real_template"].values())
    assert "Ignoring enable_thinking/thinking" in always["warning_captured"][0]
    assert always["control_template_with_switch"] == {"always_thinks": False, "thinking_enabled": False}
    assert always["enable_thinking_false_on_plain_answer"]["content"] is None


def test_structural_tag_and_grammar_rows():
    doc = _doc()
    for tag in doc["structural_tag"]:
        assert tag["error"] is None
        assert (tag["skip_special_tokens_before"], tag["skip_special_tokens_after"]) == (True, False)
        assert tag["structural_tag"]["format"]["triggers"] == ["<tool_call>"]
    timer = doc["structural_tag"][1]["structural_tag"]["format"]["tags"][0]
    assert timer["begin"] == "<tool_call>set_timer"
    assert {"type": "integer"} in [element.get("json_schema") for branch in timer["content"]["content"]["elements"]
                                   for element in branch["elements"]]
    accepted = {row["id"]: row["grammar"]["accepted"] for row in doc["cases"]}
    assert accepted == {"clean_call": True, "reasoning_then_call": True, "malformed_markup": False, "truncated_call": True,
                        "unknown_tool": False, "bad_arg_type": False, "no_call": True, "no_call_missing_think_end": True}


def test_empty_tools_never_reach_the_name_check_through_a_request():
    doc = _doc()
    assert doc["tools_empty_array_request"]["rejected"] is True
    assert "must not be an empty array" in doc["tools_empty_array_request"]["error"]
    assert doc["tools_empty_parser_direct"]["tool_calls"][0]["name"] == "get_humidity"
    omitted = _rows()["omitted_tools_call"]
    assert omitted["stream"]["tool_calls"] == omitted["non_stream"]["tool_calls"] == []


def test_without_reasoning_parser_thoughts_stay_in_content():
    rows = {row["id"]: row for row in _doc()["tool_parser_without_reasoning_parser"]}
    assert set(rows) == {"reasoning_then_call", "no_call", "no_call_missing_think_end"}
    for row in rows.values():
        assert row["stream"]["reasoning"] is None and row["non_stream"]["reasoning"] is None
    assert "</think>" in rows["no_call"]["stream"]["content"]
    assert "</think>" in rows["no_call"]["non_stream"]["content"]
    assert rows["reasoning_then_call"]["stream"]["content"] != rows["reasoning_then_call"]["non_stream"]["content"]


def _call(rows: dict[str, dict], case: str, mode: str) -> list[dict]:
    return rows[case][mode]["tool_calls"]


# 06의 문장과 그 문장이 맞으려면 행이 보여야 하는 것. 문장을 고쳐 표현이 사라지면 그 항목은 건너뛰고,
# 표현이 남아 있는데 행과 어긋나면 실패한다.
NOTEBOOK_CLAIMS = {
    "스트리밍에서는 `length`": lambda r: (r["truncated_call"]["stream"]["finish_reason"], r["truncated_call"]["non_stream"]["finish_reason"]) == ("length", "tool_calls"),
    "엔진이 `length`면 `length`로 남습니다": lambda r: all(row["finish_reason_by_engine_finish"]["length"]["stream"] == "length" for row in r.values()),
    "비스트리밍은 인자 `{}`": lambda r: _call(r, "truncated_call", "non_stream")[0]["arguments"] == "{}",
    "닫히지 않은 JSON": lambda r: r["truncated_call"]["stream"]["arguments_json_valid"] == [False],
    "이름 델타를 내보내지 않고": lambda r: r["unknown_tool"]["stream"]["tools_streamed"] is False and r["unknown_tool"]["stream"]["deltas"] == [],
    "이름이 선언 목록과 맞지 않아 호출이 버려진다": lambda r: _call(r, "truncated_mid_name", "stream") == _call(r, "truncated_mid_name", "non_stream") == [],
    "이름이 선언 목록과 맞으면 인자 {}인 호출이 나간다": lambda r: _call(r, "truncated_after_name", "stream")[0]["arguments"] == _call(r, "truncated_after_name", "non_stream")[0]["arguments"] == "{}",
    "닫힌 쌍만으로 호출이 나가고": lambda r: json.loads(_call(r, "truncated_after_closed_pair", "non_stream")[0]["arguments"]) == {"minutes": 5},
    "전부 reasoning": lambda r: r["no_call_missing_think_end"]["stream"]["content"] is None and r["no_call_missing_think_end"]["non_stream"]["content"] is None,
    "`tool_calls`이면서 인자가 JSON이 아닙니다": lambda r: r["malformed_markup"]["engine_finish"] == "stop" and r["malformed_markup"]["stream"]["finish_reason"] == "tool_calls" and r["malformed_markup"]["stream"]["arguments_json_valid"] == [False],
    "비스트리밍은 뒤 값(`부산`), 스트리밍은 앞 값(`서울`)": lambda r: "부산" in _call(r, "malformed_markup", "non_stream")[0]["arguments"] and "서울" in _call(r, "malformed_markup", "stream")[0]["arguments"] and "부산" not in _call(r, "malformed_markup", "stream")[0]["arguments"],
    "`기본 태그 문법 통과` 칸이 거짓입니다": lambda r: r["malformed_markup"]["grammar"]["accepted"] is False,
    "기본 구조화 태그의 문법은 `malformed_markup`, `unknown_tool`, `bad_arg_type`을 거절했습니다": lambda r: not any(r[case]["grammar"]["accepted"] for case in ("malformed_markup", "unknown_tool", "bad_arg_type")),
    "두 번째 `<tool_call>`에서": lambda r: r["malformed_markup"]["grammar"]["rejected_token"] == "<tool_call>",
}

# 기록의 다른 칸을 보는 문장. 값은 token_id_checks, always_thinks 등 행 밖에 있다.
RECORD_CLAIMS = {
    "12개 중 11개": lambda d: (d["token_id_checks"]["count_reasoning_tokens"][0]["tokens_before_think_end"], d["token_id_checks"]["count_reasoning_tokens"][0]["stream"]) == (12, 11),
    "15개 중 13개": lambda d: (d["token_id_checks"]["count_reasoning_tokens"][1]["tokens_before_think_end"], d["token_id_checks"]["count_reasoning_tokens"][1]["stream"]) == (15, 13),
    "비스트리밍은 12와 15로 맞습니다": lambda d: [row["non_stream"] for row in d["token_id_checks"]["count_reasoning_tokens"]] == [12, 15],
    "`all_special_tokens`에 들지 않습니다": lambda d: not any(d["token_id_checks"]["vocab"][marker]["in_all_special_tokens"] for marker in MARKUP_IDS),
    "`</think>` 없이도 생각 구간이 끝납니다": lambda d: {row["input"]: row["is_reasoning_end"] for row in d["token_id_checks"]["rows"]}["프롬프트 + <tool_call> (</think> 없음)"] is True,
    "새 프롬프트가 `<think>`로 끝나면 거짓입니다": lambda d: {row["input"]: row["is_reasoning_end"] for row in d["token_id_checks"]["rows"]}["이전 턴에 </think>가 있고 새 프롬프트가 <think>로 끝남"] is False,
    "요청 검증에서 `tools: []`를 거절합니다": lambda d: d["tools_empty_array_request"]["rejected"] is True,
    "여섯 조건이 모두 맞았습니다": lambda d: len(d["always_thinks"]["conditions"]) == 6 and all(d["always_thinks"]["conditions"].values()),
    "생각 글이 `</think>` 문자열까지 포함해 content에 들어갑니다": lambda d: all("</think>" in row[mode]["content"] for row in d["tool_parser_without_reasoning_parser"] if row["id"] != "no_call_missing_think_end" for mode in ("stream", "non_stream")),
    "비스트리밍 결과는 8개 모두 가짜 vocab 기록과 같았습니다": lambda d: len(d["cases"]) == 8 and all(row["non_stream_equals_stub_record"] for row in d["cases"]),
}


def _rust_differ(doc: dict, prompt: str) -> list[str]:
    return [row["id"] for row in doc["rows"] if not row["glm45_equals_glm47"][prompt]]


def _rust(doc: dict, case: str, variant: str) -> dict:
    return next(row["rust"][variant] for row in doc["rows"] if row["id"] == case)


# Rust 파서 기록을 보는 문장.
RUST_CLAIMS = {
    "일반 프롬프트에서 8개 중 4개(`clean_call`, `reasoning_then_call`, `unknown_tool`, `bad_arg_type`)": lambda d: _rust_differ(d, "prompt_plain") == ["clean_call", "reasoning_then_call", "unknown_tool", "bad_arg_type"],
    "`<think>`를 연 프롬프트에서 1개(`reasoning_then_call`)": lambda d: _rust_differ(d, "prompt_think_open") == ["reasoning_then_call"],
    "2개(`malformed_markup`, `truncated_call`)는 두 이름 모두 오류입니다": lambda d: all(_rust(d, case, f"{name}/prompt_plain/whole")["error"] for case in ("malformed_markup", "truncated_call") for name in ("glm45", "glm47")),
    "`clean_call`을 일반 프롬프트의 `glm45`로 넣으면 `tool parser parsing failed` 오류입니다": lambda d: _rust(d, "clean_call", "glm45/prompt_plain/whole")["error"].startswith("tool parser parsing failed") and _rust(d, "clean_call", "glm47/prompt_plain/whole")["tool_calls"][0]["name"] == "get_temperature",
    "선언하지 않은 이름도 거르지 않습니다": lambda d: _rust(d, "unknown_tool", "glm47/prompt_plain/whole")["tool_calls"][0]["name"] == "get_humidity",
    "`incomplete GLM MoE tool call` 오류를 돌려줍니다": lambda d: "incomplete GLM MoE tool call" in _rust(d, "truncated_call", "glm47/prompt_plain/whole")["error"],
}


def _notebook_text() -> str:
    return "\n".join("".join(cell["source"]) for cell in _load(NOTEBOOK_06)["cells"])


def _check_claims(claims: dict, value: object, name: str) -> None:
    text = _notebook_text()
    present = {phrase: check for phrase, check in claims.items() if phrase in text}
    assert present, f"06에서 서술을 하나도 찾지 못했습니다. {name}를 현재 문장에 맞추세요."
    wrong = [phrase for phrase, check in present.items() if not check(value)]
    assert not wrong, f"06의 서술이 저장된 기록과 어긋납니다: {wrong}"


def test_notebook_06_statements_match_rows():
    _check_claims(NOTEBOOK_CLAIMS, _rows(), "NOTEBOOK_CLAIMS")


def test_notebook_06_statements_match_the_record():
    _check_claims(RECORD_CLAIMS, _doc(), "RECORD_CLAIMS")


def test_notebook_06_statements_match_the_rust_record():
    _check_claims(RUST_CLAIMS, _load(RUST_PATH), "RUST_CLAIMS")


def test_notebook_06_reads_both_records():
    text = _notebook_text()
    assert "reference_parser_stream" in text and "reference_parser_rust" in text


def test_rust_saved_flags_agree_with_rows():
    doc = _load(RUST_PATH)
    assert doc["status"] == "ran"
    assert len(doc["rows"]) == 8
    for row in doc["rows"]:
        for prompt in ("prompt_plain", "prompt_think_open"):
            same = all(row["rust"][f"glm45/{prompt}/{mode}"] == row["rust"][f"glm47/{prompt}/{mode}"] for mode in ("whole", "stream5"))
            assert row["glm45_equals_glm47"][prompt] == same, (row["id"], prompt)
            for name in ("glm45", "glm47"):
                whole_same = row["rust"][f"{name}/{prompt}/whole"] == row["rust"][f"{name}/{prompt}/stream5"]
                assert whole_same == row["whole_equals_stream5_in_all_variants"], (row["id"], name, prompt)
