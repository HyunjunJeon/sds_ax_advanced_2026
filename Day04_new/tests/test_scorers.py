"""채점기 시험. 근거 폴더는 서버의 Workflow·EvidenceStore를 직접 구동해 만들어 형식이 어긋나지 않게 한다."""

import json

import pytest

from cap_lab.scorers import (
    STAGE_OF,
    RunRecord,
    Score,
    contamination_free,
    evidence_linked,
    first_failure,
    frozen_ok,
    goal_preserved,
    args_valid,
    no_blind_retry,
    retry_bounded,
    score_run,
    side_effect_stable,
    tool_selection_ok,
    trigger_ok,
    vague_not_frozen,
)
from cap_lab.server.evidence import EvidenceStore
from cap_lab.server.workflow import Workflow

SKILL = "/skills/requirements-interview/SKILL.md"
GOAL = "회의실 예약이 잡히면 참석자에게 알림 메일을 보내는 기능"
CLEAR = "샘플 50건 중 45건 이상 일치하면 완료"
VAGUE = "분류가 잘 되면 완료"


class Lab:
    """임시 폴더 하나에 서버와 같은 코드로 세션을 만든다."""

    def __init__(self, tmp_path):
        self.dir = tmp_path / "evidence"
        self.store = EvidenceStore(self.dir)
        self.wf = Workflow(tmp_path / "lab.db", self.store)

    def start(self, goal=GOAL):
        return self.wf.start_interview(goal)["session_id"]

    def answer(self, sid, criteria=CLEAR):
        self.wf.record_answer(sid, "constraints", "없음")
        self.wf.record_answer(sid, "acceptance_criteria", criteria)

    def full(self, goal=GOAL, criteria=CLEAR):
        sid = self.start(goal)
        self.answer(sid, criteria)
        seed_id = self.wf.freeze_seed(sid)["seed_evidence_id"]
        return sid, seed_id

    def record(self, expect=None, fault=None, calls=(), **fields):
        case = {"id": "x", "split": "dev", "stage": "S1", "kind": "k", "turns": ["t"],
                "elicitation": {}, "fault": fault, "requires": None, "expect": expect or {}}
        return RunRecord(case=case, evidence_dir=self.dir, tool_calls=list(calls), **fields)


@pytest.fixture
def lab(tmp_path):
    return Lab(tmp_path)


def call(name, args=None, result=None):
    return {"name": name, "args": args or {}, "result": result or {"success": True}, "ok": True}


# trigger_ok
def test_trigger_ok_passes_when_skill_read_matches_expectation(lab):
    assert trigger_ok(lab.record({"skill_read": True}, skill_reads=[SKILL])).value is True


def test_trigger_ok_fails_when_skill_not_read(lab):
    score = trigger_ok(lab.record({"skill_read": True}, skill_reads=["/other/README.md"]))
    assert score.value is False and "읽지 않음" in score.comment


def test_trigger_ok_fails_when_skill_read_but_should_not(lab):
    assert trigger_ok(lab.record({"skill_read": False}, skill_reads=[SKILL])).value is False


def test_trigger_ok_is_none_without_expectation(lab):
    assert trigger_ok(lab.record({"must_call": ["a"]})).value is None


# tool_selection_ok
def test_tool_selection_passes(lab):
    record = lab.record({"must_call": ["start_interview"], "must_not_call": ["freeze_seed"]},
                        calls=[call("start_interview")])
    assert tool_selection_ok(record).value is True


def test_tool_selection_fails_on_missing_required_tool(lab):
    score = tool_selection_ok(lab.record({"must_call": ["start_interview"]}, calls=[call("read_file")]))
    assert score.value is False and "start_interview" in score.comment


def test_tool_selection_fails_on_forbidden_tool(lab):
    score = tool_selection_ok(lab.record({"must_not_call": ["start_interview"]}, calls=[call("start_interview")]))
    assert score.value is False and "부르면 안 되는데" in score.comment


def test_tool_selection_none_without_lists(lab):
    assert tool_selection_ok(lab.record({"skill_read": True})).value is None


# args_valid
def test_args_valid_passes_with_real_session(lab):
    sid = lab.start()
    record = lab.record(calls=[call("start_interview", {"goal": GOAL}), call("get_session", {"session_id": sid})])
    assert args_valid(record).value is True


def test_args_valid_fails_on_validation_error_result(lab):
    bad = {"isError": True, "content": [{"type": "text", "text": "1 validation error for call[start_interview]"}]}
    score = args_valid(lab.record(calls=[call("start_interview", {}, bad)]))
    assert score.value is False and "검증 오류" in score.comment


def test_args_valid_fails_on_invented_session_id(lab):
    lab.start()
    score = args_valid(lab.record(calls=[call("get_session", {"session_id": "f" * 32})]))
    assert score.value is False and "session_id" in score.comment


def test_args_valid_none_without_mcp_calls(lab):
    assert args_valid(lab.record(calls=[call("read_file", {"file_path": SKILL})])).value is None


# goal_preserved
def test_goal_preserved_passes_ignoring_whitespace(lab):
    lab.start("  회의실 예약이 잡히면  참석자에게 알림 메일을\n보내는 기능 ")
    assert goal_preserved(lab.record({"goal_verbatim": GOAL})).value is True


def test_goal_preserved_fails_when_goal_was_paraphrased(lab):
    lab.start("회의실 예약 알림 기능")
    score = goal_preserved(lab.record({"goal_verbatim": GOAL}))
    assert score.value is False and "다름" in score.comment


def test_goal_preserved_fails_without_session(lab):
    score = goal_preserved(lab.record({"goal_verbatim": GOAL}))
    assert score.value is False and "세션이 없음" in score.comment


def test_goal_preserved_none_without_expectation(lab):
    assert goal_preserved(lab.record({})).value is None


# vague_not_frozen
def test_vague_not_frozen_passes_when_replaced_by_clear_answer(lab):
    lab.full(criteria=CLEAR)
    assert vague_not_frozen(lab.record({"vague_answer": VAGUE})).value is True


def test_vague_not_frozen_passes_when_nothing_frozen(lab):
    lab.start()
    assert vague_not_frozen(lab.record({"vague_answer": VAGUE})).value is True


def test_vague_not_frozen_fails_when_vague_answer_is_frozen(lab):
    lab.full(criteria=f" {VAGUE} ")
    score = vague_not_frozen(lab.record({"vague_answer": VAGUE}))
    assert score.value is False and "확정 명세" in score.comment


def test_vague_not_frozen_none_without_expectation(lab):
    assert vague_not_frozen(lab.record({})).value is None


# frozen_ok
def test_frozen_ok_passes_both_directions(lab):
    lab.full()
    assert frozen_ok(lab.record({"frozen": True})).value is True


def test_frozen_ok_passes_when_not_frozen_as_expected(lab):
    lab.start()
    assert frozen_ok(lab.record({"frozen": False})).value is True


def test_frozen_ok_fails_when_expected_frozen_but_missing(lab):
    lab.start()
    score = frozen_ok(lab.record({"frozen": True}))
    assert score.value is False and "없음" in score.comment


def test_frozen_ok_fails_when_frozen_against_expectation(lab):
    lab.full()
    assert frozen_ok(lab.record({"frozen": False})).value is False


def test_frozen_ok_none_without_expectation(lab):
    assert frozen_ok(lab.record({})).value is None


# evidence_linked
def test_evidence_linked_passes_with_artifact_from_seed(lab):
    sid, seed_id = lab.full()
    lab.store.save(sid, "요약", "본문", seed_id)
    assert evidence_linked(lab.record({"evidence_linked": True})).value is True


def test_evidence_linked_fails_when_artifact_has_no_source(lab):
    sid, _ = lab.full()
    lab.store.save(sid, "요약", "본문")
    score = evidence_linked(lab.record({"evidence_linked": True}))
    assert score.value is False and "없음" in score.comment


def test_evidence_linked_fails_when_source_points_to_missing_id(lab):
    sid, seed_id = lab.full()
    saved = lab.store.save(sid, "요약", "본문", seed_id)
    # 연결 대상 파일이 사라진 상태를 만든다.
    (lab.dir / sid / f"{seed_id}.json").unlink()
    assert saved["success"] and evidence_linked(lab.record({"evidence_linked": True})).value is False


def test_evidence_linked_none_without_expectation(lab):
    assert evidence_linked(lab.record({})).value is None


# no_blind_retry
def denied_case(lab, calls, expect=None):
    return lab.record(expect or {"max_same_call": 1}, fault={"permission_denied": ["save_evidence"]}, calls=calls)


def test_no_blind_retry_passes_when_agent_changes_args_or_stops(lab):
    calls = [call("save_evidence", {"title": "a"}), call("save_evidence", {"title": "b"})]
    assert no_blind_retry(denied_case(lab, calls)).value is True


def test_no_blind_retry_fails_on_identical_repeat(lab):
    calls = [call("save_evidence", {"title": "a"})] * 2
    score = no_blind_retry(denied_case(lab, calls))
    assert score.value is False and "save_evidence" in score.comment


def test_no_blind_retry_honors_max_same_call(lab):
    calls = [call("save_evidence", {"title": "a"})] * 2
    assert no_blind_retry(denied_case(lab, calls, {"max_same_call": 2})).value is True


def test_no_blind_retry_none_without_permission_fault(lab):
    assert no_blind_retry(lab.record({}, fault={"transient": {"record_answer": 1}})).value is None


# retry_bounded
def transient_case(lab, n_calls):
    calls = [call("record_answer", {"i": i}) for i in range(n_calls)]
    return lab.record({}, fault={"transient": {"record_answer": 1}}, calls=calls)


def test_retry_bounded_passes_within_limit_with_answer_recorded(lab):
    lab.answer(lab.start())
    assert retry_bounded(transient_case(lab, 3)).value is True


def test_retry_bounded_fails_above_limit(lab):
    lab.answer(lab.start())
    score = retry_bounded(transient_case(lab, 4))
    assert score.value is False and "상한 3" in score.comment


def test_retry_bounded_fails_when_answer_not_recorded(lab):
    lab.start()
    score = retry_bounded(transient_case(lab, 2))
    assert score.value is False and "기록되지 않음" in score.comment


def test_retry_bounded_none_without_transient_fault(lab):
    assert retry_bounded(lab.record({}, fault=None)).value is None


# side_effect_stable
def test_side_effect_stable_passes(lab):
    lab.full()
    assert side_effect_stable(lab.record({"event_count": 4})).value is True


def test_side_effect_stable_fails_on_duplicate_events(lab):
    sid = lab.start()
    lab.answer(sid)
    lab.wf.record_answer(sid, "constraints", "개인정보 제외")  # 수정 답변이 이벤트를 하나 더 만든다
    score = side_effect_stable(lab.record({"event_count": 3}))
    assert score.value is False and "4개" in score.comment


def test_side_effect_stable_none_without_expectation(lab):
    assert side_effect_stable(lab.record({})).value is None


# contamination_free
def test_contamination_free_passes_on_clean_calls(lab):
    assert contamination_free(lab.record(calls=[call("read_file", {"file_path": SKILL})])).value is True


@pytest.mark.parametrize("path", ["Day04_new/data/cases.jsonl", "x/gate_labels.json", "/repo/data/dev.json"])
def test_contamination_free_fails_on_tool_argument(lab, path):
    score = contamination_free(lab.record(calls=[call("read_file", {"file_path": path})]))
    assert score.value is False and "표지" in score.comment


def test_contamination_free_fails_on_skill_read_path(lab):
    assert contamination_free(lab.record(skill_reads=["/a/gate_labels/x.md"])).value is False


# 오류·수치·단계
def test_error_record_turns_checks_into_none_but_keeps_contamination(lab):
    lab.full()
    clean = score_run(lab.record({"frozen": True}, error="타임아웃"))
    by_name = {s.name: s for s in clean}
    assert by_name["frozen_ok"].value is None and "타임아웃" in by_name["frozen_ok"].comment
    dirty = score_run(lab.record({"frozen": True}, calls=[call("read_file", {"file_path": "cases.jsonl"})], error="x"))
    assert {s.name: s for s in dirty}["contamination_free"].value is False


def test_numeric_scores_come_from_record(lab):
    record = lab.record(calls=[call("a"), call("b")], model_calls=3, input_tokens=100, output_tokens=20, latency_s=1.5)
    by_name = {s.name: s.value for s in score_run(record)}
    assert (by_name["model_calls"], by_name["tool_calls"], by_name["latency_s"],
            by_name["input_tokens"], by_name["output_tokens"]) == (3, 2, 1.5, 100, 20)


def test_score_run_reports_every_named_scorer(lab):
    names = {s.name for s in score_run(lab.record())}
    assert set(STAGE_OF) | {"contamination_free", "model_calls"} <= names


def test_first_failure_returns_earliest_stage_in_order():
    scores = [Score("frozen_ok", False, ""), Score("vague_not_frozen", False, ""), Score("trigger_ok", True, "")]
    assert first_failure(scores) == "S3"
    assert first_failure([Score("evidence_linked", False, ""), Score("goal_preserved", False, "")]) == "S2"


def test_first_failure_ignores_none_and_r_stages():
    scores = [Score("trigger_ok", None, ""), Score("no_blind_retry", False, ""), Score("frozen_ok", True, "")]
    assert first_failure(scores) is None


def test_scores_are_json_serializable(lab):
    json.dumps([vars(s) for s in score_run(lab.record())])
