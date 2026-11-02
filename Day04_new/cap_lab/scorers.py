"""에이전트 한 번 실행의 기록으로 계산하는 결정적 채점기. 모델 판정은 쓰지 않는다.

입력은 RunRecord(호출 기록·근거 폴더·최종 답변)이고, 점수는 코드가 파일과 호출에서 센다.
Score.value가 None이면 "해당 없음 또는 확인 불가"이며 False(실패)로 읽으면 안 된다.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SKILL_SUFFIX = "requirements-interview/SKILL.md"
# 서버가 제공하는 도구. 에이전트 호출 중 MCP 호출을 가려내는 기준이다.
MCP_TOOLS = frozenset(
    {"start_interview", "record_answer", "get_session", "freeze_seed",
     "list_evidence", "read_evidence", "save_evidence"}
)
# 채점 정답표·사례 파일을 에이전트가 건드렸는지 가리는 표지.
CONTAMINATION_MARKERS = ("cases.jsonl", "gate_labels", "/data/")
SESSION_DIR = re.compile(r"[0-9a-f]{32}")
EVENT_KINDS = ("interview_started", "answer_recorded", "seed_frozen")
# 첫 실패를 찾는 순서. R 단계는 별도로 보고한다.
STAGE_ORDER = ("S1", "S2", "S3", "S5", "S6")

STAGE_OF = {
    "trigger_ok": "S1",
    "tool_selection_ok": "S2",
    "args_valid": "S2",
    "goal_preserved": "S2",
    "vague_not_frozen": "S3",
    "frozen_ok": "S5",
    "evidence_linked": "S6",
    "no_blind_retry": "R1",
    "retry_bounded": "R2",
    "side_effect_stable": "R3",
}


@dataclass
class RunRecord:
    case: dict
    evidence_dir: Path
    tool_calls: list[dict] = field(default_factory=list)  # {name, args, result, ok}, 호출 순서
    skill_reads: list[str] = field(default_factory=list)  # read_file로 읽은 경로
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    final_text: str = ""
    gate_decisions: list[dict] = field(default_factory=list)
    interrupts: list[dict] = field(default_factory=list)  # 답한 elicitation 내용
    error: str | None = None


@dataclass
class Score:
    name: str
    value: bool | float | None
    comment: str


def _norm(text: object) -> str:
    return " ".join(str(text).split())


def _dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _load(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _sessions(evidence_dir: Path) -> dict[str, Path]:
    """서버가 만든 세션. 첫 이벤트 파일이 있는 폴더만 센다."""
    if not evidence_dir.is_dir():
        return {}
    return {
        folder.name: folder
        for folder in sorted(evidence_dir.iterdir())
        if folder.is_dir()
        and SESSION_DIR.fullmatch(folder.name)
        and (folder / "event-00000001.json").is_file()
    }


def _records(folder: Path, prefix: str) -> list[dict]:
    loaded = (_load(path) for path in sorted(folder.glob(f"{prefix}-*.json")))
    return [record for record in loaded if record is not None]


def _events(folder: Path) -> list[dict]:
    """이벤트 content(sequence·event·payload) 목록."""
    contents = (record.get("content") for record in _records(folder, "event"))
    return [content for content in contents if isinstance(content, dict)]


def _seeds(record: RunRecord) -> list[dict]:
    seeds = []
    for folder in _sessions(record.evidence_dir).values():
        for seed in _records(folder, "seed"):
            if isinstance(seed.get("content"), dict):
                seeds.append(seed["content"])
    return seeds


def _calls_of(record: RunRecord, name: str) -> list[dict]:
    return [call for call in record.tool_calls if call.get("name") == name]


def _args(call: dict) -> dict:
    args = call.get("args")
    return args if isinstance(args, dict) else {}


def trigger_ok(record: RunRecord) -> Score:
    expected = record.case["expect"].get("skill_read")
    if expected is None:
        return Score("trigger_ok", None, "skill_read 기대가 없는 사례")
    read = any(_norm(path).endswith(SKILL_SUFFIX) for path in record.skill_reads)
    verdict = "읽음" if read else "읽지 않음"
    if read == expected:
        return Score("trigger_ok", True, f"스킬 본문 {verdict}, 기대와 같음")
    return Score("trigger_ok", False, f"스킬 본문 {verdict}, 기대는 {'읽음' if expected else '읽지 않음'}")


def tool_selection_ok(record: RunRecord) -> Score:
    expect = record.case["expect"]
    must_call, must_not = expect.get("must_call"), expect.get("must_not_call")
    if not must_call and not must_not:
        return Score("tool_selection_ok", None, "must_call/must_not_call 기대가 없는 사례")
    called = {call.get("name") for call in record.tool_calls}
    missing = [name for name in must_call or [] if name not in called]
    forbidden = [name for name in must_not or [] if name in called]
    if missing or forbidden:
        causes = []
        if missing:
            causes.append(f"호출해야 하는데 안 부른 도구: {missing}")
        if forbidden:
            causes.append(f"부르면 안 되는데 부른 도구: {forbidden}")
        return Score("tool_selection_ok", False, "; ".join(causes))
    return Score("tool_selection_ok", True, "필수 도구를 모두 부르고 금지 도구는 부르지 않음")


def args_valid(record: RunRecord) -> Score:
    mcp_calls = [call for call in record.tool_calls if call.get("name") in MCP_TOOLS]
    if not mcp_calls:
        return Score("args_valid", None, "MCP 호출이 없음")
    rejected = [
        call["name"] for call in mcp_calls if "validation error" in _dumps(call.get("result")).lower()
    ]
    if rejected:
        return Score("args_valid", False, f"입력 검증 오류가 난 호출: {rejected}")
    created = set(_sessions(record.evidence_dir))
    unknown = [
        _args(call)["session_id"]
        for call in mcp_calls
        if "session_id" in _args(call) and _args(call)["session_id"] not in created
    ]
    if unknown:
        return Score("args_valid", False, f"서버가 만들지 않은 session_id 인자: {unknown}")
    return Score("args_valid", True, "입력 검증 오류 없음, session_id가 모두 근거 폴더의 세션")


def goal_preserved(record: RunRecord) -> Score:
    expected = record.case["expect"].get("goal_verbatim")
    if expected is None:
        return Score("goal_preserved", None, "goal_verbatim 기대가 없는 사례")
    sessions = _sessions(record.evidence_dir)
    if not sessions:
        return Score("goal_preserved", False, "만들어진 세션이 없음")
    goals = []
    for folder in sessions.values():
        first = _load(folder / "event-00000001.json") or {}
        content = first.get("content")
        payload = content.get("payload") if isinstance(content, dict) else None
        goals.append(payload.get("goal") if isinstance(payload, dict) else None)
    if any(goal is not None and _norm(goal) == _norm(expected) for goal in goals):
        return Score("goal_preserved", True, "첫 이벤트의 목표가 원문과 같음")
    return Score("goal_preserved", False, f"저장된 목표 {goals}가 원문 {expected!r}와 다름")


def vague_not_frozen(record: RunRecord) -> Score:
    vague = record.case["expect"].get("vague_answer")
    if vague is None:
        return Score("vague_not_frozen", None, "vague_answer 기대가 없는 사례")
    frozen_vague = [
        seed for seed in _seeds(record)
        if _norm(seed.get("acceptance_criteria", "")) == _norm(vague)
    ]
    if frozen_vague:
        return Score("vague_not_frozen", False, f"모호한 답 {vague!r}가 그대로 확정 명세가 됨")
    return Score("vague_not_frozen", True, "모호한 답이 확정 명세의 완료 기준이 되지 않음")


def frozen_ok(record: RunRecord) -> Score:
    expected = record.case["expect"].get("frozen")
    if expected is None:
        return Score("frozen_ok", None, "frozen 기대가 없는 사례")
    frozen = bool(_seeds(record))
    if frozen == expected:
        return Score("frozen_ok", True, f"확정 명세 {'있음' if frozen else '없음'}, 기대와 같음")
    return Score("frozen_ok", False, f"확정 명세 {'있음' if frozen else '없음'}, 기대는 {'있음' if expected else '없음'}")


def _linked_artifacts(record: RunRecord) -> int:
    count = 0
    for folder in _sessions(record.evidence_dir).values():
        ids = {path.stem for path in folder.glob("*.json")}
        count += sum(
            1 for artifact in _records(folder, "artifact")
            if artifact.get("source_evidence_id") in ids
        )
    return count


def evidence_linked(record: RunRecord) -> Score:
    expected = record.case["expect"].get("evidence_linked")
    if expected is None:
        return Score("evidence_linked", None, "evidence_linked 기대가 없는 사례")
    linked = _linked_artifacts(record) > 0
    if linked == expected:
        return Score("evidence_linked", True, f"근거에 연결된 산출물 {'있음' if linked else '없음'}, 기대와 같음")
    return Score("evidence_linked", False, f"근거에 연결된 산출물 {'있음' if linked else '없음'}, 기대는 {'있음' if expected else '없음'}")


def no_blind_retry(record: RunRecord) -> Score:
    denied = (record.case.get("fault") or {}).get("permission_denied")
    if not denied:
        return Score("no_blind_retry", None, "permission_denied 장애가 없는 사례")
    limit = record.case["expect"].get("max_same_call", 1)
    for tool in denied:
        same = Counter(_dumps(_args(call)) for call in _calls_of(record, tool))
        if same and max(same.values()) > limit:
            return Score("no_blind_retry", False, f"거부된 {tool}을 같은 인자로 {max(same.values())}번 호출(허용 {limit})")
    return Score("no_blind_retry", True, f"거부된 도구를 같은 인자로 {limit}번 넘게 부르지 않음")


def retry_bounded(record: RunRecord) -> Score:
    transient = (record.case.get("fault") or {}).get("transient")
    if not transient:
        return Score("retry_bounded", None, "transient 장애가 없는 사례")
    for tool, failures in transient.items():
        calls = len(_calls_of(record, tool))
        if calls > failures + 2:
            return Score("retry_bounded", False, f"{tool} 호출 {calls}번이 상한 {failures + 2}를 넘음")
    recorded = any(
        event.get("event") == "answer_recorded"
        for folder in _sessions(record.evidence_dir).values()
        for event in _events(folder)
    )
    if not recorded:
        return Score("retry_bounded", False, "재시도 뒤에도 답변이 이벤트에 기록되지 않음")
    return Score("retry_bounded", True, "재시도가 상한 안이고 답변이 이벤트에 기록됨")


def side_effect_stable(record: RunRecord) -> Score:
    expected = record.case["expect"].get("event_count")
    if expected is None:
        return Score("side_effect_stable", None, "event_count 기대가 없는 사례")
    count = sum(
        1
        for folder in _sessions(record.evidence_dir).values()
        for event in _events(folder)
        if event.get("event") in EVENT_KINDS
    )
    if count == expected:
        return Score("side_effect_stable", True, f"상태 이벤트 {count}개, 기대와 같음")
    return Score("side_effect_stable", False, f"상태 이벤트 {count}개, 기대는 {expected}개")


def contamination_free(record: RunRecord) -> Score:
    surfaces = [_dumps(_args(call)) for call in record.tool_calls] + [str(p) for p in record.skill_reads]
    hits = sorted({m for text in surfaces for m in CONTAMINATION_MARKERS if m in text})
    if hits:
        return Score("contamination_free", False, f"도구 인자나 읽은 경로에 평가 자료 표지 {hits}가 있음")
    return Score("contamination_free", True, "평가 자료를 가리키는 인자나 경로가 없음")


CHECKS = (
    trigger_ok, tool_selection_ok, args_valid, goal_preserved, vague_not_frozen, frozen_ok,
    evidence_linked, no_blind_retry, retry_bounded, side_effect_stable, contamination_free,
)


def score_run(record: RunRecord) -> list[Score]:
    """검사 점수와 수치 점수를 순서대로 반환한다.

    record.error가 있으면 중간에 멈춘 실행이라 기록이 불완전하다. 적용되는 검사는 None으로 돌리고
    오류를 comment에 남긴다. 단, 평가 자료를 건드린 사실(contamination_free=False)은 그대로 둔다.
    """
    scores = [check(record) for check in CHECKS]
    if record.error:
        scores = [
            score if score.value is None or (score.name == "contamination_free" and score.value is False)
            else Score(score.name, None, f"실행 오류로 확인 불가: {record.error}")
            for score in scores
        ]
    scores += [
        Score("model_calls", float(record.model_calls), "모델 호출 수"),
        Score("tool_calls", float(len(record.tool_calls)), "도구 호출 수"),
        Score("latency_s", float(record.latency_s), "실행 시간(초)"),
        Score("input_tokens", float(record.input_tokens), "입력 토큰"),
        Score("output_tokens", float(record.output_tokens), "출력 토큰"),
    ]
    return scores


def first_failure(scores: list[Score]) -> str | None:
    """S1, S2, S3, S5, S6 순서로 가장 이른 실패 단계. 실패가 없거나 None뿐이면 None."""
    failed = {STAGE_OF[s.name] for s in scores if s.value is False and s.name in STAGE_OF}
    return next((stage for stage in STAGE_ORDER if stage in failed), None)
