"""에이전트 멀티턴 요청의 prefix 재사용과 tool calling 진단을 보여 주는 교육용 모델(teaching model)이다.

대화를 token 목록으로 바꾸는 렌더러는 GLM의 tokenizer나 chat template이 아니라, 이 파일이 선언한
장난감(toy) 규칙이다. 재사용 판정만 `kv_sim.KVManagerSim`(v0.32.0 block 해시 규칙을 옮긴 모델)에 맡긴다.
시간 값은 만들지 않는다. 파서 시험 결과는 `data/reference_parser.json`에서 읽을 뿐 지어내지 않는다.
모델링하지 않은 것은 `NOT_MODELED`에 적었다.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass

from vllm_lab import DATA_DIR, DEFAULT_BLOCK_SIZE
from vllm_lab.kv_sim import KVManagerSim, KVPoolExhausted

NOT_MODELED: tuple[str, ...] = (
    "실제 chat template과 실제 tokenizer는 쓰지 않습니다. 렌더링은 이 파일의 toy 규칙입니다.",
    "앞 턴의 답변이 문자열로 돌아와 다시 tokenize될 때 생기는 token 어긋남은 모델링하지 않았습니다(P5-07, 미확인).",
    "요약 middleware와 도구 인자 줄이기가 앞 messages를 바꾸는 경우는 모델링하지 않았습니다(P5-21).",
    "tools를 system 뒤, messages 앞에 렌더링하는 것은 toy의 가정이고 실제 GLM-5.3-Flash template의 위치와 다릅니다(P5-08).",
    "실제 서버의 tool 파서 실행은 하지 않습니다. 파서 결과는 reference_parser.json을 읽을 때만 나옵니다.",
)

CACHE_SALT_NOTE = "cache_salt는 첫 block hash에만 섞인다(vllm/v1/core/kv_cache_utils.py:647-650)."
TOY_ASSUMPTION = "toy 렌더링 가정, 실제 template과 tool 위치가 다름(P5-08)"
TOOL_CHOICES = ("auto", "required", "named", "none")
PARSER_EVIDENCE = "실제 GLM 파서, 구성 문자열"
CODE_READING_EVIDENCE = "코드 읽기"
NOT_RUN_CELL = "실행 안 함"

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")
_ID_HEX_DIGITS = 6
_PRESSURE_EXTRA_BLOCKS = 3  # null block 1개와 여유 2개


# --------------------------------------------------------------------------- 렌더링

def toy_tokenize(text: str) -> list[int]:
    """re.findall(r"\\w+|[^\\w\\s]", text)의 각 조각을 sha256 앞 6 hex의 정수로. 결정적이다."""
    return [int(hashlib.sha256(piece.encode()).hexdigest()[:_ID_HEX_DIGITS], 16)
            for piece in _TOKEN_PATTERN.findall(text)]


def _as_text(content: object) -> str:
    return content if isinstance(content, str) else json.dumps(content, sort_keys=True, ensure_ascii=False)


def render_prompt(system: str, tools: list[dict], messages: list[dict]) -> list[int]:
    """순서: <system> 토큰들, tools를 주어진 순서로 각각 <tool> json.dumps(sort_keys=True), messages를 각각 <role> content <end>.
    assistant의 tool_calls는 content 뒤에 json으로. 표지도 toy_tokenize로 바꾼다."""
    tokens = toy_tokenize("<system>") + toy_tokenize(system)
    for tool in tools:
        tokens += toy_tokenize("<tool>") + toy_tokenize(json.dumps(tool, sort_keys=True, ensure_ascii=False))
    for message in messages:
        tokens += toy_tokenize(f"<{message['role']}>") + toy_tokenize(_as_text(message.get("content", "")))
        if message.get("tool_calls"):
            tokens += toy_tokenize(json.dumps(message["tool_calls"], sort_keys=True, ensure_ascii=False))
        tokens += toy_tokenize("<end>")
    return tokens


# --------------------------------------------------------------------------- 턴 재사용

@dataclass
class TurnResult:
    turn: int
    label: str
    prompt_tokens: int
    hit_tokens: int
    hit_blocks: int
    recomputed_tokens: int
    hit_ratio: float
    first_miss_block: int | None
    assumption: str

    def to_row(self) -> dict:
        return {
            "turn": self.turn, "label": self.label, "prompt_tokens": self.prompt_tokens,
            "hit_tokens": self.hit_tokens, "hit_blocks": self.hit_blocks,
            "recomputed_tokens": self.recomputed_tokens, "hit_ratio": self.hit_ratio,
            "first_miss_block": self.first_miss_block, "assumption": self.assumption,
        }


class AgentReuseSim:
    def __init__(self, num_blocks: int = 512, block_size: int = DEFAULT_BLOCK_SIZE) -> None:
        self.kv = KVManagerSim(num_blocks, block_size)
        self._results: list[TurnResult] = []

    def send(self, system: str, tools: list[dict], messages: list[dict], *, cache_salt: str | None = None,
             output: str = "", label: str = "", assumption: str = "") -> TurnResult:
        """새 요청 하나: add_request, schedule, output token append 후 schedule, free. 턴마다 새 request(P5-01).
        pool 부족이면 KVPoolExhausted(한국어 메시지)."""
        block_size = self.kv.block_size
        turn = len(self._results) + 1
        tokens = render_prompt(system, tools, messages)
        request = self.kv.add_request(f"turn-{turn}", tokens, cache_salt=cache_salt)
        scheduled = self.kv.schedule(request)
        if scheduled is None:
            raise KVPoolExhausted(-(-len(tokens) // block_size), self.kv.pool.num_free())
        output_tokens = toy_tokenize(output)
        if output_tokens:
            self.kv.append_output(request, output_tokens)
            if self.kv.schedule(request) is None:
                needed = -(-request.num_tokens // block_size)
                self.kv.free(request)
                raise KVPoolExhausted(needed, self.kv.pool.num_free())
        self.kv.free(request)
        hit_blocks = scheduled.hit_tokens // block_size
        max_hit_blocks = (len(tokens) - 1) // block_size  # vllm/v1/core/kv_cache_manager.py:295
        result = TurnResult(
            turn, label, len(tokens), scheduled.hit_tokens, hit_blocks, len(tokens) - scheduled.hit_tokens,
            scheduled.hit_tokens / len(tokens), None if hit_blocks == max_hit_blocks else hit_blocks, assumption,
        )
        self._results.append(result)
        return result

    def rows(self) -> list[dict]:
        return [result.to_row() for result in self._results]


# --------------------------------------------------------------------------- 시나리오

SCENARIOS = ("append_only", "system_change", "tool_added", "tool_order_change",
             "salt_change", "effort_in_system", "pressure_evict")

_BASE_SYSTEM_WORDS = 40
_OUTPUT_WORDS = 8
_BASE_SYSTEM = "You are a support agent. " + " ".join(f"rule{i}" for i in range(_BASE_SYSTEM_WORDS))
_CHANGED_SYSTEM = "Answer briefly. " + " ".join(f"rule{i}" for i in range(_BASE_SYSTEM_WORDS))
_BASE_TOOLS = [
    {"type": "function", "function": {
        "name": "search_docs", "description": "Search the knowledge base for a short query",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "get_order", "description": "Look up one order by its number",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}},
]
_EXTRA_TOOL = {"type": "function", "function": {
    "name": "send_mail", "description": "Send a short mail to the customer",
    "parameters": {"type": "object", "properties": {"body": {"type": "string"}}, "required": ["body"]}}}
_ASSUMPTION_SCENARIOS = ("tool_added", "tool_order_change", "effort_in_system")


def _words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}w{i}" for i in range(count))


def _turn_plan(name: str, user_words: int, turns: int) -> list[dict]:
    """턴마다 send 인자를 만든다. 바뀌는 것은 change_at 번째(0부터) 턴부터다."""
    change_at = max(1, turns // 2)
    plan = []
    messages: list[dict] = []
    for index in range(turns):
        changed = index >= change_at
        messages = messages + [{"role": "user", "content": _words(f"q{index}", user_words)}]
        output = _words(f"a{index}", _OUTPUT_WORDS)
        system, tools, salt = _BASE_SYSTEM, list(_BASE_TOOLS), None
        label = f"턴 {index + 1}"
        if name == "system_change" and changed:
            system = _CHANGED_SYSTEM
        elif name == "tool_added" and changed:
            tools = tools + [_EXTRA_TOOL]
        elif name == "tool_order_change" and changed:
            tools = tools[::-1]
        elif name == "salt_change":
            salt = "user-b" if changed else "user-a"
        elif name == "effort_in_system":
            system = f"{_BASE_SYSTEM} Reasoning Effort: {'low' if changed else 'max'}"
        if index == change_at and name not in ("append_only", "pressure_evict"):
            label += " (변경)"
        plan.append({"system": system, "tools": tools, "messages": list(messages), "cache_salt": salt,
                     "output": output, "label": label,
                     "assumption": TOY_ASSUMPTION if name in _ASSUMPTION_SCENARIOS else ""})
        messages = messages + [{"role": "assistant", "content": output}]
    return plan


def _pressure_pool(plan: list[dict], block_size: int) -> int:
    most = max(-(-(len(render_prompt(t["system"], t["tools"], t["messages"])) + len(toy_tokenize(t["output"])))
                 // block_size) for t in plan)
    return most + _PRESSURE_EXTRA_BLOCKS


def _filler_messages(num_blocks: int, block_size: int) -> list[dict]:
    fixed = len(render_prompt("", [], [{"role": "user", "content": ""}]))
    return [{"role": "user", "content": _words("fill", num_blocks * block_size - fixed)}]


def run_scenario(name: str, *, user_words: int = 40, turns: int = 4, block_size: int = 16,
                 num_blocks: int = 512) -> list[dict]:
    """TurnResult.to_row() 목록. 없는 이름은 ValueError. tool_added, tool_order_change, effort_in_system의 assumption 칸에는
    'toy 렌더링 가정, 실제 template과 tool 위치가 다름(P5-08)'을 넣는다. pressure_evict는 num_blocks를 줄이고 사이에 다른 요청을 넣는다."""
    if name not in SCENARIOS:
        raise ValueError(f"알 수 없는 시나리오 {name!r}입니다. 가능한 이름: {', '.join(SCENARIOS)}")
    if turns < 2 or user_words < 1:
        raise ValueError(f"turns는 2 이상, user_words는 1 이상이어야 합니다: turns={turns}, user_words={user_words}")
    plan = _turn_plan(name, user_words, turns)
    if name != "pressure_evict":
        sim = AgentReuseSim(num_blocks, block_size)
        for step in plan:
            sim.send(**step)
        return sim.rows()
    pool_blocks = min(num_blocks, _pressure_pool(plan, block_size))
    sim = AgentReuseSim(pool_blocks, block_size)
    filler_blocks = pool_blocks - 2  # null block 1개를 빼고 free 하나를 남긴다
    for index, step in enumerate(plan):
        sim.send(**step)
        if index < len(plan) - 1:
            sim.send("", [], _filler_messages(filler_blocks, block_size), label="filler (다른 요청)")
    return sim.rows()


def reuse_from_recorded(calls: list[dict], *, block_size: int = 16, num_blocks: int = 512) -> list[dict]:
    """calls[i]: {"system": str, "tools": list, "messages": [{"role", "content"}]}. 기록을 render_prompt에 넣어 TurnResult 행을 낸다. output은 빈 문자열."""
    sim = AgentReuseSim(num_blocks, block_size)
    for index, call in enumerate(calls):
        sim.send(call["system"], call["tools"], call["messages"], label=f"기록 {index + 1}",
                 assumption=TOY_ASSUMPTION)
    return sim.rows()


# --------------------------------------------------------------------------- 서버 조건 표

def chatopenai_sends_include_usage(*, base_url_set: bool, stream_usage: bool | None) -> bool:
    """stream_usage가 None이 아니면 그 값, None이면 not base_url_set. P5-17."""
    return stream_usage if stream_usage is not None else not base_url_set


def cached_tokens_visible(*, server_flag: bool, stream: bool, client_sends_include_usage: bool,
                          force_include_usage: bool = False) -> dict:
    """{"visible": bool, "why": str}. server_flag가 거짓이면 불가(P5-11). stream이면 둘 중 하나가 참이어야 한다(P5-12)."""
    if not server_flag:
        return {"visible": False,
                "why": "서버에 --enable-prompt-tokens-details가 없으면 prompt_tokens_details가 null입니다(P5-11)."}
    if stream and not (client_sends_include_usage or force_include_usage):
        return {"visible": False,
                "why": "스트리밍은 stream_options.include_usage를 보내거나 서버가 강제해야 usage 청크가 옵니다(P5-12)."}
    return {"visible": True, "why": "서버 플래그가 켜져 있고 usage가 응답에 실립니다."}


def flag_matrix() -> list[dict]:
    """네 조합과 tools 요청. 칸: --enable-auto-tool-choice, --tool-call-parser, 시작 단계, tool_choice=auto 요청, 근거 ID, 근거 종류('코드 읽기')."""
    rows = [
        (True, True, "정상 시작", "파서가 호출을 추출한다", "P6-03"),
        (True, False, "TypeError로 시작 실패(cli_args.py:523)", "서버가 뜨지 않아 요청할 수 없다", "P6-08"),
        (False, True, "오류 없이 시작(parser_manager.py:36)", "도구 파싱이 꺼진다. tools가 있으면 400 문구가 난다(P6-10)", "P6-09"),
        (False, False, "오류 없이 시작", "tool_choice=none은 통과. 그 밖에는 400 BadRequestError, \"auto\" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set", "P6-10"),
    ]
    return [{"--enable-auto-tool-choice": auto, "--tool-call-parser": parser, "시작 단계": start,
             "tool_choice=auto 요청": request, "근거 ID": source, "근거 종류": CODE_READING_EVIDENCE}
            for auto, parser, start, request, source in rows]


def finish_reason_rule(*, engine_finish_reason: str | None, tool_choice: str, calls_extracted: bool, stream: bool) -> str:
    """tool_choice: auto, required, named, none. 비스트리밍: (auto이고 calls_extracted) 또는 (required이고 engine=='stop')이면 'tool_calls'.
    스트리밍: calls_extracted이고 named가 아니고 engine=='stop'이면 'tool_calls'. 그 밖은 engine 값 또는 'stop'.
    vllm/entrypoints/openai/chat_completion/serving.py:771, :1098. 코드를 옮긴 교육용 함수다. 실행 확인이 아니다."""
    if tool_choice not in TOOL_CHOICES:
        raise ValueError(f"tool_choice는 {TOOL_CHOICES} 중 하나여야 합니다: {tool_choice!r}")
    engine_stopped = engine_finish_reason == "stop"
    if stream:
        becomes_tool_calls = calls_extracted and tool_choice != "named" and engine_stopped
    else:
        becomes_tool_calls = (tool_choice == "auto" and calls_extracted) or (tool_choice == "required" and engine_stopped)
    return "tool_calls" if becomes_tool_calls else (engine_finish_reason or "stop")


# --------------------------------------------------------------------------- client 쪽 검증

def _type_matches(expected: str, value: object) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def validate_tool_args(schema: dict, arguments: str) -> list[str]:
    """client 쪽 검증. JSON 파싱 실패, required 누락, 타입 불일치(string, integer, number, boolean, array, object)를 한국어 문장 목록으로. 빈 목록이면 통과. vLLM 기능이 아니다."""
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as error:
        return [f"arguments가 JSON이 아닙니다: {error.msg} (위치 {error.pos})"]
    if not isinstance(parsed, dict):
        return [f"arguments는 JSON 객체여야 하는데 {type(parsed).__name__}입니다."]
    problems = [f"필수 인자 {key!r}가 없습니다." for key in schema.get("required", []) if key not in parsed]
    for key, rule in schema.get("properties", {}).items():
        expected = rule.get("type")
        if key in parsed and expected and not _type_matches(expected, parsed[key]):
            problems.append(f"인자 {key!r}는 {expected}여야 하는데 {type(parsed[key]).__name__} 값 {parsed[key]!r}입니다.")
    return problems


# --------------------------------------------------------------------------- Part 6 기록 읽기

class ReferenceMissing(FileNotFoundError):
    pass


class CaseNotRun(RuntimeError):
    pass


@dataclass(frozen=True)
class ParserCase:
    id: str
    candidates: tuple[str, ...]
    layer: str
    title: str
    constructed: bool
    raw_text: str
    tools: tuple[str, ...]
    tool_choice: str
    mode: str
    status: str
    reason: str | None
    output: dict | None


_FILE_STATUSES = ("ran", "partial", "not_run")
_CASE_STATUSES = ("ran", "not_run")
_CASE_FIELDS = ("id", "candidates", "layer", "title", "constructed", "raw_text", "tools", "tool_choice", "mode", "status")


def _read_reference(path: pathlib.Path | None) -> tuple[pathlib.Path, dict]:
    path = path or DATA_DIR / "reference_parser.json"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ReferenceMissing(f"{path} 파일이 없습니다. 파서 시험 기록이 없어 결과를 보일 수 없습니다.") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}가 JSON이 아닙니다: {error.msg} (위치 {error.pos})") from error
    if not isinstance(data, dict) or data.get("status") not in _FILE_STATUSES:
        raise ValueError(f"{path}의 최상위 status는 {_FILE_STATUSES} 중 하나여야 합니다.")
    return path, data


def _parse_case(raw: dict, path: pathlib.Path) -> ParserCase:
    missing = [field for field in _CASE_FIELDS if field not in raw]
    if missing:
        raise ValueError(f"{path}의 케이스 {raw.get('id', '?')!r}에 필드가 없습니다: {', '.join(missing)}")
    if raw["status"] not in _CASE_STATUSES:
        raise ValueError(f"{path}의 케이스 {raw['id']!r} status는 {_CASE_STATUSES} 중 하나여야 합니다: {raw['status']!r}")
    output = raw.get("output")
    if raw["status"] == "ran" and not isinstance(output, dict):
        raise ValueError(f"{path}의 케이스 {raw['id']!r}는 ran인데 output이 없습니다. 결과를 지어내지 않습니다.")
    return ParserCase(
        raw["id"], tuple(raw["candidates"]), raw["layer"], raw["title"], bool(raw["constructed"]), raw["raw_text"],
        tuple(raw["tools"]), raw["tool_choice"], raw["mode"], raw["status"], raw.get("reason"), output,
    )


def reference_status(path: pathlib.Path | None = None) -> dict:
    """예외를 내지 않는다. {"status": 'ran'|'partial'|'not_run'|'missing', "reason": str | None, "parser": dict | None}."""
    try:
        _, data = _read_reference(path)
    except ReferenceMissing as error:
        return {"status": "missing", "reason": str(error), "parser": None}
    except ValueError as error:
        return {"status": "not_run", "reason": f"기록 형식 오류: {error}", "parser": None}
    return {"status": data["status"], "reason": data.get("reason"), "parser": data.get("parser")}


def load_parser_cases(path: pathlib.Path | None = None) -> list[ParserCase]:
    """기본 DATA_DIR/'reference_parser.json'. 파일 없음은 ReferenceMissing. 최상위 status가 not_run이면 CaseNotRun(reason 포함)."""
    path, data = _read_reference(path)
    if data["status"] == "not_run":
        raise CaseNotRun(f"파서 시험을 실행하지 못했습니다: {data.get('reason') or '이유가 기록되지 않았습니다'}")
    return [_parse_case(raw, path) for raw in data.get("cases", [])]


def get_parser_case(case_id: str, path: pathlib.Path | None = None) -> ParserCase:
    """없는 ID는 KeyError. 그 케이스 status가 ran이 아니면 CaseNotRun. 결과를 지어내지 않는다."""
    for case in load_parser_cases(path):
        if case.id == case_id:
            if case.status != "ran":
                raise CaseNotRun(f"케이스 {case_id!r}는 실행되지 않았습니다: {case.reason or '이유가 기록되지 않았습니다'}")
            return case
    raise KeyError(f"케이스 {case_id!r}가 기록에 없습니다.")


def parser_case_table(path: pathlib.Path | None = None) -> list[dict]:
    """행: id, 후보, 제목, 입력, reasoning, content, tool_calls, 근거 종류. not_run 케이스의 결과 칸은 '실행 안 함'. 파일 문제는 load_parser_cases와 같다."""
    rows = []
    for case in load_parser_cases(path):
        ran = case.status == "ran" and case.output is not None
        output = case.output or {}
        rows.append({
            "id": case.id, "후보": list(case.candidates), "제목": case.title, "입력": case.raw_text,
            "reasoning": output.get("reasoning") if ran else NOT_RUN_CELL,
            "content": output.get("content") if ran else NOT_RUN_CELL,
            "tool_calls": output.get("tool_calls") if ran else NOT_RUN_CELL,
            "근거 종류": PARSER_EVIDENCE if ran else NOT_RUN_CELL,
        })
    return rows


# --------------------------------------------------------------------------- 진단표

_DIAGNOSIS = (
    ("C1", "플래그 없이 tools 요청", "네트워크", "400 BadRequestError와 \"auto\" tool choice requires 문구",
     "vllm/renderers/online_renderer.py:253-270, vllm/entrypoints/openai/chat_completion/protocol.py:951-954",
     "서버 플래그 필요(두 플래그 없이 띄운 서버)"),
    ("C2", "max_tokens로 호출 중간에 잘림", "생성", "부분 인자로 호출이 나가고 비스트리밍은 tool_calls, 스트리밍은 length",
     "vllm/parser/engine/streaming_parser_engine.py:310-327, vllm/entrypoints/openai/chat_completion/serving.py:1099-1119",
     "가능(max_tokens를 작게, 두 방식 모두)"),
    ("C3", "선언하지 않은 도구 이름 호출", "parser", "호출이 사라지고 content도 비며 오류가 없다",
     "vllm/parser/engine/parser_engine.py:415-423, vllm/tool_parsers/utils.py:356-374",
     "기본 구성에서는 구조화 태그가 함수명을 제약하는 것으로 읽힌다(코드 읽기). 태그가 없는 서버(VLLM_ENFORCE_STRICT_TOOL_CALLING=0)에서 나올 수 있고 미확인"),
    ("C4", "정수 인자에 숫자가 아닌 값", "schema 검증", "변환 실패 시 문자열이 arguments에 남고 서버는 거절하지 않는다",
     "vllm/tool_parsers/utils.py:1153-1238, vllm/parser/engine/parser_engine.py:388-413",
     "기본 구성에서는 얕은 태그가 정수 칸의 타입을 제약하는 것으로 읽힌다(코드 읽기). 태그가 없는 서버(VLLM_ENFORCE_STRICT_TOOL_CALLING=0)에서 나올 수 있고 미확인"),
    ("C5", "필수 인자 누락", "schema 검증", "서버가 필수 필드를 검사하지 않아 빠진 채로 도구 실행까지 간다(검사 코드를 못 찾았을 뿐)",
     "vllm/parser/glm47_moe.py:66-80, vllm/parser/engine/parser_engine.py:388-413",
     "기본 구성의 문법이 막지 않으므로 나올 수 있다. 모델이 실제로 필수 인자를 빼는지는 미확인"),
    ("C6", "</arg_value> 없이 끊김", "parser", "비스트리밍에서는 마지막 인자가 조용히 사라지고 앞 인자만 남은 호출이 나간다",
     "vllm/parser/glm47_moe.py:54-58, vllm/parser/glm47_moe.py:66-80", "가능(max_tokens로 끊어 본다)"),
    ("C7", "</tool_call> 누락 후 다음 <tool_call>", "parser", "두 번째 호출이 첫 호출의 인자 텍스트로 흡수되어 하나만 남는다",
     "vllm/parser/engine/streaming_parser_engine.py:412-421, vllm/parser/glm47_moe.py:167-194",
     "기본 구성에서는 구조화 태그가 닫는 태그를 제약하는 것으로 읽힌다(코드 읽기). 태그가 없는 서버(VLLM_ENFORCE_STRICT_TOOL_CALLING=0)에서 나올 수 있고 미확인"),
    ("C8", "--reasoning-parser 없이 required/named", "생성", "구조화 태그가 생각 구간부터 걸려 출력이 비정상일 수 있다. 영향 크기는 모른다",
     "vllm/v1/structured_output/__init__.py:248-267, vllm/engine/arg_utils.py:2167-2168",
     "서버 플래그 필요(--reasoning-parser를 뺀 서버)"),
    ("C9", "VLLM_ENFORCE_STRICT_TOOL_CALLING=0", "생성", "required/named에 제약이 남지 않아 호출 대신 일반 텍스트가 나올 수 있다",
     "vllm/tool_parsers/abstract_tool_parser.py:144-145, vllm/tool_parsers/abstract_tool_parser.py:189-190",
     "서버 플래그 필요(환경변수를 바꿔 다시 띄운다)"),
    ("C10", "Rust frontend에서 잘린 호출", "parser", "incomplete GLM MoE tool call 오류. HTTP나 스트림에서 어떻게 보이는지는 모른다",
     "rust/src/parser/src/tool/glm_xml/mod.rs:130-143, rust/src/parser/src/tool/error.rs:14-15",
     "서버 플래그 필요(VLLM_USE_RUST_FRONTEND=1)"),
    ("C11", "이전 턴의 도구 호출·결과를 템플릿으로 다시 렌더링", "template", "과거 tool_calls와 tool 메시지가 어긋나 모델이 호출 형식을 잃을 수 있다",
     "템플릿은 체크포인트에 있어 v0.32.0 소스에 없다. 렌더링 호출은 vllm/renderers/online_renderer.py:224- 부근",
     "가능(여러 턴 에이전트 루프). 렌더링 결과는 /tokenize로 비교한다"),
    ("C12", "도구 실행 예외와 시간 초과", "실행", "올바른 호출이 client 도구 코드에서 실패해 에이전트 루프가 멈춘다",
     "vLLM 코드 경로 없음. 에이전트 client 코드의 문제다", "가능(도구 함수에 일부러 예외를 던진다)"),
)


def diagnosis_rows(path: pathlib.Path | None = None) -> list[dict]:
    """C1~C12 12행. 칸: 사례, 층, 증상(가설), 볼 곳, 재현 조건, 근거 종류. part6.md 실패 사례 후보를 옮긴다.
    근거 종류는 파일에 그 후보를 candidates로 가진 ran 케이스가 있으면 '실제 GLM 파서, 구성 문자열', 없으면 '코드 읽기'. C12는 'client 코드'. 파일이 없으면 모두 '코드 읽기'."""
    try:
        verified = {candidate for case in load_parser_cases(path) if case.status == "ran" for candidate in case.candidates}
    except (ReferenceMissing, CaseNotRun, ValueError):
        verified = set()
    rows = []
    for code, title, layer, symptom, where, repro in _DIAGNOSIS:
        if code == "C12":
            evidence = "client 코드"
        else:
            evidence = PARSER_EVIDENCE if code in verified else CODE_READING_EVIDENCE
        rows.append({"사례": f"{code}. {title}", "층": layer, "증상(가설)": symptom, "볼 곳": where,
                     "재현 조건": repro, "근거 종류": evidence})
    return rows
