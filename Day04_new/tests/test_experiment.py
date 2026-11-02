"""experiment.py 시험. 실제 server.py를 stdio 자식 프로세스로 띄우고 모델·판정기·Langfuse는 가짜를 쓴다.

키·네트워크·유료 호출은 없다. 모든 쓰기는 tmp_path 아래에서만 한다.
"""
import asyncio
import hashlib
import itertools
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langfuse import Evaluation
from langfuse.api import NotFoundError
from pydantic import Field

from cap_lab.agent import SKILLS_DIR
from cap_lab.experiment import (
    DATASET_NAME,
    Variant,
    attribute,
    compare,
    load_cases,
    prereg_guards,
    run_case,
    run_experiment,
    sync_dataset,
)
from cap_lab.scorers import score_run
from cap_lab.settings import Settings
from fakes import FakeChatModel

SKILL = "/requirements-interview/SKILL.md"
USAGE = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}
FAKE_H1_LOW = {"DAY04_ALLOW_FAKE_DECIDER": "1", "DAY04_FAKE_DECIDER": '{"testability": 0.2}'}
CALL_IDS = itertools.count(1)


def case_of(case_id: str) -> dict:
    return next(case for case in load_cases() if case["id"] == case_id)


def call(name: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{next(CALL_IDS)}",
                                              "type": "tool_call"}], usage_metadata=USAGE)


def reply(text: str) -> AIMessage:
    return AIMessage(content=text, usage_metadata=USAGE)


def last_result(history: list[BaseMessage], name: str) -> dict:
    return [m for m in history if isinstance(m, ToolMessage) and m.name == name][-1].artifact["structured_content"]


class ScriptedModel(FakeChatModel):
    """steps의 함수가 지금까지의 대화를 받아 다음 AIMessage를 만든다. 받은 대화를 모두 기록한다."""

    steps: list[Callable[[list[BaseMessage]], AIMessage]] = Field(default_factory=list)
    received: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.steps.pop(0)(messages))])


def scripted(*steps: Callable[[list[BaseMessage]], AIMessage]) -> ScriptedModel:
    return ScriptedModel(messages=iter([]), steps=list(steps))


def full_flow_steps(memo: dict) -> list[Callable[[list[BaseMessage]], AIMessage]]:
    """dev-07: Skill 읽기, 시작, 답변 2개, 확정, 요약 저장. 확정한 세션과 명세 ID를 memo에 남긴다."""

    def freeze(history):
        memo["session_id"] = last_result(history, "start_interview")["session_id"]
        return call("freeze_seed", session_id=memo["session_id"])

    def save(history):
        memo["seed_evidence_id"] = last_result(history, "freeze_seed")["seed_evidence_id"]
        return call("save_evidence", session_id=memo["session_id"], title="최종 요약",
                    content="월별 정산표 명세를 확정했다.", source_evidence_id=memo["seed_evidence_id"])

    return [
        lambda _: call("read_file", file_path=SKILL),
        lambda _: call("start_interview", goal="출장 영수증을 모아 월별 정산표를 만드는 도구"),
        lambda h: call("record_answer", session_id=last_result(h, "start_interview")["session_id"],
                       field="constraints", answer="영수증 원본 이미지는 외부로 보내지 않는다"),
        lambda h: call("record_answer", session_id=last_result(h, "start_interview")["session_id"],
                       field="acceptance_criteria",
                       answer="한 달치 샘플 영수증 20장을 넣으면 합계가 수기 정산표와 1원 단위까지 일치하는 월별 표가 나온다"),
        freeze,
        save,
        lambda _: reply("명세를 확정하고 최종 요약을 저장했습니다."),
    ]


def check_values(record) -> dict:
    return {score.name: score.value for score in score_run(record)}


def test_load_cases_splits_dev_and_holdout():
    assert [c["id"] for c in load_cases(split="dev")] == [f"dev-{n:02d}" for n in range(1, 11)]
    assert [c["id"] for c in load_cases(split="holdout")] == [f"ho-{n:02d}" for n in range(1, 9)]
    assert len(load_cases()) == 18


def test_full_case_runs_against_the_real_server_and_every_applicable_check_passes(tmp_path):
    model = scripted(*full_flow_steps({}))
    record = asyncio.run(run_case(case_of("dev-07"), variant=Variant("A"), settings=Settings(),
                                  workdir=tmp_path, repeat=1, model=model))

    assert record.error is None
    assert record.evidence_dir == tmp_path / "A-r1" / "dev-07" / "evidence"
    assert [(c["name"], c["ok"]) for c in record.tool_calls] == [
        ("read_file", True), ("start_interview", True), ("record_answer", True), ("record_answer", True),
        ("freeze_seed", True), ("save_evidence", True)]
    assert record.skill_reads == [SKILL]
    assert (record.model_calls, record.input_tokens, record.output_tokens) == (7, 700, 70)
    assert record.final_text == "명세를 확정하고 최종 요약을 저장했습니다."
    assert record.latency_s > 0
    values = check_values(record)
    assert {name: values[name] for name in (
        "trigger_ok", "tool_selection_ok", "args_valid", "goal_preserved", "vague_not_frozen", "frozen_ok",
        "evidence_linked", "no_blind_retry", "retry_bounded", "side_effect_stable", "contamination_free")} == {
        "trigger_ok": None, "tool_selection_ok": True, "args_valid": True, "goal_preserved": None,
        "vague_not_frozen": None, "frozen_ok": True, "evidence_linked": True, "no_blind_retry": None,
        "retry_bounded": None, "side_effect_stable": True, "contamination_free": True}
    assert values["tool_calls"] == 6.0


def test_only_successful_reads_of_a_skill_file_count_as_skill_reads(tmp_path):
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS_DIR, skills)
    (skills / "requirements-interview" / "notes.md").write_text("참고 메모", encoding="utf-8")
    model = scripted(
        lambda _: call("read_file", file_path="/no-such-skill/SKILL.md"),
        lambda _: call("read_file", file_path="/requirements-interview/notes.md"),
        lambda _: call("read_file", file_path=SKILL),
        lambda _: reply("끝."),
    )
    record = asyncio.run(run_case(case_of("dev-01"), variant=Variant("A", skills_dir=skills), settings=Settings(),
                                  workdir=tmp_path / "work", repeat=1, model=model))

    assert [(c["name"], c["ok"]) for c in record.tool_calls] == [
        ("read_file", False), ("read_file", True), ("read_file", True)]
    assert record.skill_reads == [SKILL]


def vague_steps(constraints: str, vague: str, *, then_freeze: bool) -> list[Callable[[list[BaseMessage]], AIMessage]]:
    def session(history):
        return last_result(history, "start_interview")["session_id"]

    steps = [
        lambda _: call("read_file", file_path=SKILL),
        lambda _: call("start_interview", goal="목표"),
        lambda h: call("record_answer", session_id=session(h), field="constraints", answer=constraints),
        lambda h: call("record_answer", session_id=session(h), field="acceptance_criteria", answer=vague),
    ]
    if then_freeze:
        steps.append(lambda h: call("freeze_seed", session_id=session(h)))
    return [*steps, lambda _: reply("끝.")]


def test_h1_elicitation_is_answered_from_the_case_and_the_seed_keeps_the_users_criterion(tmp_path):
    case = case_of("dev-05")
    model = scripted(*vague_steps("없음", "분류가 잘 되면 완료", then_freeze=True))
    record = asyncio.run(run_case(case, variant=Variant("B", gate_h1=True), settings=Settings(), workdir=tmp_path,
                                  repeat=1, model=model, server_env=FAKE_H1_LOW))

    assert record.error is None
    (asked,) = record.interrupts
    assert (asked["tool_name"], asked["action"]) == ("record_answer", "accept")
    assert asked["content"] == {"acceptance_criteria": case["elicitation"]["acceptance_criteria"]}
    assert "분류가 잘 되면 완료" in asked["message"]
    (gate,) = record.gate_decisions
    assert {key: gate[key] for key in ("gate", "field", "score", "threshold", "source", "original")} == {
        "gate": "h1", "field": "acceptance_criteria", "score": 0.2, "threshold": 0.5,
        "source": "elicited", "original": "분류가 잘 되면 완료"}
    values = check_values(record)
    assert (values["vague_not_frozen"], values["frozen_ok"]) == (True, True)
    freeze = next(c for c in record.tool_calls if c["name"] == "freeze_seed")
    assert freeze["result"]["seed"]["acceptance_criteria"] == case["elicitation"]["acceptance_criteria"]


def test_h1_elicitation_the_case_cannot_answer_is_declined_and_nothing_is_recorded(tmp_path):
    model = scripted(*vague_steps("개인정보 제외", "보기 좋게 요약되면 끝", then_freeze=False))
    record = asyncio.run(run_case(case_of("dev-06"), variant=Variant("B", gate_h1=True), settings=Settings(),
                                  workdir=tmp_path, repeat=1, model=model, server_env=FAKE_H1_LOW))

    assert record.error is None
    assert [a["action"] for a in record.interrupts] == ["decline"]
    answer = [c for c in record.tool_calls if c["name"] == "record_answer"][-1]
    assert (answer["ok"], answer["result"]["error"]) == (False, "criteria_not_testable")
    assert record.gate_decisions == []
    values = check_values(record)
    assert (values["vague_not_frozen"], values["frozen_ok"]) == (True, True)


def test_a_model_that_keeps_resending_a_declined_answer_is_stopped_at_the_resume_cap(tmp_path):
    def session(history):
        return last_result(history, "start_interview")["session_id"]

    resend = [lambda h: call("record_answer", session_id=session(h), field="acceptance_criteria",
                             answer="보기 좋게 요약되면 끝")] * 7
    model = scripted(
        lambda _: call("read_file", file_path=SKILL),
        lambda _: call("start_interview", goal="주간 매출 요약 보고 도구"),
        lambda h: call("record_answer", session_id=session(h), field="constraints", answer="개인정보 제외"),
        *resend,
    )
    record = asyncio.run(run_case(case_of("dev-06"), variant=Variant("B", gate_h1=True), settings=Settings(),
                                  workdir=tmp_path, repeat=1, model=model, server_env=FAKE_H1_LOW))

    assert record.error.startswith("RuntimeError: 한 턴에서 elicitation 재개가 5번을 넘었습니다")
    assert [a["action"] for a in record.interrupts] == ["decline"] * 5
    assert len(model.steps) == 1  # 여섯 번째 재전송에서 멈추고 일곱 번째는 보내지 않았다.
    assert check_values(record)["vague_not_frozen"] is None


def test_turns_go_in_order_to_one_thread_and_a_repeated_answer_adds_no_event(tmp_path):
    case = case_of("ho-06")
    criteria = "점검 기록 10건을 입력하면 설비별 최근 점검일이 정확히 조회된다"

    def answer(field, text):
        return lambda h: call("record_answer", session_id=last_result(h, "start_interview")["session_id"],
                              field=field, answer=text)

    model = scripted(
        lambda _: call("read_file", file_path=SKILL),
        lambda _: call("start_interview", goal="설비 점검 기록을 남기는 앱"),
        answer("constraints", "없음"),
        answer("acceptance_criteria", criteria),
        lambda _: reply("기록만 했습니다."),
        answer("acceptance_criteria", criteria),
        lambda _: reply("같은 문구로 다시 기록했습니다."),
    )
    record = asyncio.run(run_case(case, variant=Variant("A"), settings=Settings(), workdir=tmp_path, repeat=1,
                                  model=model))

    assert record.error is None
    users = [m.text for m in model.received[-1] if isinstance(m, HumanMessage)]
    assert users == case["turns"]
    assert record.model_calls == 7 and record.final_text == "같은 문구로 다시 기록했습니다."
    values = check_values(record)
    assert (values["side_effect_stable"], values["frozen_ok"], values["tool_selection_ok"]) == (True, True, True)


def test_a_required_case_runs_first_in_the_same_evidence_folder_and_is_not_counted(tmp_path):
    memo: dict = {}
    model = scripted(
        *full_flow_steps(memo),
        lambda _: call("read_file", file_path=SKILL),
        lambda _: call("read_evidence", session_id=memo["session_id"], evidence_id=memo["seed_evidence_id"]),
        lambda _: call("save_evidence", session_id=memo["session_id"], title="구현 계획", content="계획 본문",
                       source_evidence_id=memo["seed_evidence_id"]),
        lambda _: reply("계획을 저장했습니다."),
    )
    record = asyncio.run(run_case(case_of("dev-08"), variant=Variant("A"), settings=Settings(),
                                  workdir=tmp_path, repeat=2, model=model))

    assert record.error is None
    assert [c["name"] for c in record.tool_calls] == ["read_file", "read_evidence", "save_evidence"]
    assert record.model_calls == 4
    values = check_values(record)
    assert (values["tool_selection_ok"], values["args_valid"], values["evidence_linked"]) == (True, True, True)
    assert sorted(p.name for p in (tmp_path / "A-r2" / "dev-08").iterdir()) == [
        "evidence", "prerequisite.sqlite3", "sessions.sqlite3"]


def test_a_failed_required_case_stops_the_main_case_and_is_recorded_as_its_error(tmp_path):
    record = asyncio.run(run_case(case_of("dev-08"), variant=Variant("A"), settings=Settings(),
                                  workdir=tmp_path, repeat=1, model=scripted()))

    assert record.error.startswith("RuntimeError: 선행 사례 dev-07 실행 오류(")
    assert record.tool_calls == [] and record.model_calls == 0
    assert not (tmp_path / "A-r1" / "dev-08" / "sessions.sqlite3").exists()


@dataclass
class FakeItem:
    id: str
    input: dict
    expected_output: dict
    metadata: dict
    dataset_id: str = "fake-dataset"


@dataclass
class FakeDataset:
    items: list[FakeItem]


@dataclass
class FakeItemResult:
    item: FakeItem
    output: dict
    evaluations: list[Evaluation] = field(default_factory=list)


class FakeLangfuse:
    """Langfuse 클라이언트 중 experiment.py가 쓰는 부분만 흉내 낸다. 네트워크 없이 호출을 기록한다.

    run_experiment는 실제처럼 동기 함수이고 안에서 새 이벤트 루프로 task를 돌린다.
    """

    def __init__(self) -> None:
        self.datasets: dict[str, dict[str, FakeItem]] = {}
        self.item_writes: list[str] = []
        self.experiments: list[dict] = []
        self.scores: list[dict] = []

    def auth_check(self) -> bool:
        return True

    def get_dataset(self, name: str) -> FakeDataset:
        if name not in self.datasets:
            raise NotFoundError(body={"message": "Dataset not found"})
        return FakeDataset(list(self.datasets[name].values()))

    def create_dataset(self, *, name: str, description: str, metadata: dict) -> None:
        self.datasets[name] = {}

    def create_dataset_item(self, *, dataset_name: str, id: str, input: dict, expected_output: dict,
                            metadata: dict) -> None:
        self.item_writes.append(id)
        self.datasets[dataset_name][id] = FakeItem(id, input, expected_output, metadata)

    def run_experiment(self, *, name, run_name, description, data, task, evaluators, run_evaluators,
                       max_concurrency, metadata):
        async def run_items():
            return [await task(item=item) for item in data]

        results = [FakeItemResult(item, output) for item, output in zip(data, asyncio.run(run_items()))]
        for result in results:
            for evaluator in evaluators:
                result.evaluations += evaluator(input=result.item.input, output=result.output,
                                                expected_output=result.item.expected_output,
                                                metadata=result.item.metadata)
            self.scores += [{"run_name": run_name, "item": result.item.id, "name": e.name, "value": e.value,
                             "data_type": e.data_type} for e in result.evaluations]
        run_evaluations = [e for evaluator in run_evaluators for e in evaluator(item_results=results)]
        self.experiments.append({"name": name, "run_name": run_name, "metadata": metadata,
                                 "max_concurrency": max_concurrency, "run_evaluations": run_evaluations})


class ConceptModel(FakeChatModel):
    """개념 질문에 바로 답하는 모델. 사용자 발화에 '장애'가 있으면 모델 오류를 낸다. 받은 대화를 기록한다."""

    received: list[list[BaseMessage]] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        if any("장애" in m.text for m in messages if isinstance(m, HumanMessage)):
            raise RuntimeError("모델 장애 흉내")
        return ChatResult(generations=[ChatGeneration(message=reply("개념만 설명합니다."))])


EXPECT_ONLY = "기대값에만-있는-문장-7f3a"


def concept_case(case_id: str, turn: str) -> dict:
    return {"id": case_id, "split": "dev", "stage": "S1", "kind": "should_not_trigger", "turns": [turn],
            "elicitation": {}, "fault": None, "requires": None,
            "expect": {"skill_read": False, "must_not_call": ["start_interview"], "vague_answer": EXPECT_ONLY}}


def run_concepts(tmp_path: Path, model: ConceptModel, client: FakeLangfuse) -> list[str]:
    cases = [concept_case("t-01", "MCP가 뭔가요?"), concept_case("t-02", "장애가 났을 때 Seed는 뭔가요?")]
    return asyncio.run(run_experiment(Variant("T"), cases, 1, settings=Settings(), mirror_dir=tmp_path / "runs",
                                      client=client, model=model))


def mirror_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_run_experiment_prints_the_cost_notice_first(tmp_path, capsys):
    run_concepts(tmp_path, ConceptModel(messages=iter([])), FakeLangfuse())

    assert capsys.readouterr().out.splitlines()[0] == (
        "이 실행은 사례 2 x 반복 1 = 2회, Claude 호출 약 10~18회(추정), Jev 호출 최대 0회(추정), Langfuse에 기록합니다.")


def test_the_mirror_keeps_an_errored_item_and_langfuse_gets_only_checked_scores(tmp_path):
    client = FakeLangfuse()
    assert run_concepts(tmp_path, ConceptModel(messages=iter([])), client) == ["T-r1"]

    good, errored = mirror_lines(tmp_path / "runs" / "T-r1.jsonl")
    assert (good["case_id"], good["error"], good["first_failure"]) == ("t-01", None, None)
    assert errored["case_id"] == "t-02" and "모델 장애 흉내" in errored["error"]
    assert errored["first_failure"] is None
    assert {s["name"]: s["value"] for s in errored["scores"]}["trigger_ok"] is None
    sent = {(s["item"], s["name"]): (s["value"], s["data_type"]) for s in client.scores}
    assert sent[("t-01", "trigger_ok")] == (1.0, "BOOLEAN")
    assert sent[("t-01", "model_calls")] == (1.0, "NUMERIC")
    # 오류로 끝난 모델 호출은 model 갱신을 남기지 않으므로 세지 않는다. 숫자 점수는 None이 아니라 보낸다.
    assert ("t-02", "trigger_ok") not in sent and sent[("t-02", "model_calls")] == (0.0, "NUMERIC")
    (experiment,) = client.experiments
    rates = {e.name: e for e in experiment["run_evaluations"]}
    assert rates["trigger_ok_pass_rate"].value == 1.0
    assert "1/1 통과" in rates["trigger_ok_pass_rate"].comment and "확인 불가 1건" in rates["trigger_ok_pass_rate"].comment
    assert experiment["max_concurrency"] == 1


def test_run_metadata_pins_the_run_configuration(tmp_path):
    client = FakeLangfuse()
    run_concepts(tmp_path, ConceptModel(messages=iter([])), client)

    (experiment,) = client.experiments
    metadata = experiment["metadata"]
    assert experiment["run_name"] == "T-r1"
    assert {key: metadata[key] for key in ("dataset", "gate_h1", "gate_h2", "threshold_h1", "threshold_h2",
                                           "jev_model", "effort", "repeat")} == {
        "dataset": DATASET_NAME, "gate_h1": "off", "gate_h2": "off", "threshold_h1": "0.5", "threshold_h2": "0.5",
        "jev_model": "off", "effort": "medium", "repeat": "1"}
    assert metadata["skill_sha256"] == hashlib.sha256((SKILLS_DIR / "requirements-interview" / "SKILL.md")
                                                      .read_bytes()).hexdigest()
    assert len(metadata["server_sha256"]) == 64
    assert all(isinstance(value, str) for value in metadata.values())


def test_the_model_never_receives_the_expected_output(tmp_path):
    client = FakeLangfuse()
    model = ConceptModel(messages=iter([]))
    run_concepts(tmp_path, model, client)

    assert EXPECT_ONLY in json.dumps(client.datasets[DATASET_NAME]["t-01"].expected_output, ensure_ascii=False)
    seen = "\n".join(str(m.content) for conversation in model.received for m in conversation)
    assert "MCP가 뭔가요?" in seen
    for leaked in (EXPECT_ONLY, "must_not_call", "skill_read", "expected_output"):
        assert leaked not in seen


def test_missing_langfuse_keys_without_a_client_stop_with_guidance(tmp_path):
    with pytest.raises(RuntimeError) as stopped:
        asyncio.run(run_experiment(Variant("T"), [concept_case("t-01", "MCP가 뭔가요?")], 1,
                                   settings=Settings(anthropic_api_key="offline-test"), mirror_dir=tmp_path / "runs"))

    assert "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY가 미설정입니다" in str(stopped.value)
    assert "Day04_new/.env.example" in str(stopped.value)
    assert not (tmp_path / "runs").exists()


def test_an_existing_run_record_stops_before_any_run_and_the_notice_counts_prerequisites(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "B-r2.jsonl").write_text("", encoding="utf-8")
    client = FakeLangfuse()
    with pytest.raises(RuntimeError, match=r"실행 기록 \['B-r2'\]"):
        asyncio.run(run_experiment(Variant("B", gate_h1=True, gate_h2=True), [case_of("dev-07"), case_of("dev-08")],
                                   3, settings=Settings(), mirror_dir=tmp_path / "runs", client=client,
                                   model=scripted()))

    assert capsys.readouterr().out.splitlines()[0] == (
        "이 실행은 사례 2 x 반복 3 = 6회(선행 사례 실행 3회 별도), Claude 호출 약 45~81회(추정), "
        "Jev 호출 최대 54회(추정), Langfuse에 기록합니다.")
    assert client.datasets == {} and client.experiments == []


def test_sync_dataset_writes_each_case_once_and_rewrites_only_changed_cases():
    client = FakeLangfuse()
    cases = load_cases()
    assert sync_dataset(client, cases) == [c["id"] for c in cases]
    assert sync_dataset(client, cases) == []

    item = client.datasets[DATASET_NAME]["dev-03"]
    assert item.input == {"id": "dev-03", "turns": case_of("dev-03")["turns"]}
    assert item.expected_output == case_of("dev-03")["expect"]
    assert item.metadata == {"split": "dev", "stage": "S2", "kind": "goal_verbatim"}
    changed = [dict(c, expect={**c["expect"], "frozen": True}) if c["id"] == "dev-04" else c for c in cases]
    assert sync_dataset(client, changed) == ["dev-04"]


def write_mirror(path: Path, rows: list[tuple[str, dict[str, float | bool | None]]], error: str | None = None) -> Path:
    lines = [{"case_id": case_id, "split": "dev", "error": error, "first_failure": None,
              "scores": [{"name": name, "value": value, "comment": ""} for name, value in scores.items()]}
             for case_id, scores in rows]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


CASES = [f"c{n}" for n in range(1, 7)]


def variant_mirror(path: Path, target: bool, model_calls: float = 5.0) -> Path:
    return write_mirror(path, [(c, {"vague_not_frozen": target, "model_calls": model_calls}) for c in CASES])


def test_compare_finds_an_improvement_when_the_target_rises_and_guards_stay_inside_the_noise(tmp_path):
    result = compare([variant_mirror(tmp_path / "A-r1.jsonl", False)], [variant_mirror(tmp_path / "A2-r1.jsonl", False)],
                     [variant_mirror(tmp_path / "B-r1.jsonl", True)], target="vague_not_frozen", guards=["model_calls"])

    assert result["verdict"] == "개선"
    assert result["comparisons"]["vague_not_frozen"]["diff"] == 1.0
    assert result["guards_without_data"] == []


def test_compare_cannot_confirm_an_improvement_when_the_target_does_not_move(tmp_path):
    result = compare([variant_mirror(tmp_path / "A-r1.jsonl", False)], [variant_mirror(tmp_path / "A2-r1.jsonl", False)],
                     [variant_mirror(tmp_path / "B-r1.jsonl", False)], target="vague_not_frozen", guards=["model_calls"])

    assert result["verdict"] == "개선 확인 불가"


def test_compare_pools_repeats_and_counts_none_and_errored_lines_as_unchecked(tmp_path):
    a1 = variant_mirror(tmp_path / "A-r1.jsonl", False)
    a2_repeat = write_mirror(tmp_path / "A-r2.jsonl", [("c1", {"vague_not_frozen": True, "model_calls": 5.0})])
    b = write_mirror(tmp_path / "B-r1.jsonl", [(c, {"vague_not_frozen": True, "model_calls": 5.0}) for c in CASES[:4]]
                     + [("c5", {"vague_not_frozen": None, "model_calls": 5.0})])
    b_errored = write_mirror(tmp_path / "B-r2.jsonl", [("c6", {"vague_not_frozen": None, "model_calls": 1.0})],
                             error="RuntimeError: 모델 장애")
    result = compare([a1, a2_repeat], [variant_mirror(tmp_path / "AA-r1.jsonl", False)], [b, b_errored],
                     target="vague_not_frozen", guards=["model_calls"])

    # c1의 A 평균은 (0 + 1) / 2 = 0.5, c2~c4는 0. B는 c1~c4가 1. 차이 평균 = (0.5 + 1 + 1 + 1) / 4.
    assert result["comparisons"]["vague_not_frozen"]["n_cases"] == 4
    assert result["comparisons"]["vague_not_frozen"]["diff"] == pytest.approx(0.875)
    assert result["unchecked"]["B"] == {"vague_not_frozen": 2, "model_calls": 1}
    assert result["comparisons"]["model_calls"]["n_cases"] == 5


def test_compare_keeps_the_preregistered_no_data_rule_for_a_guard_without_values(tmp_path):
    result = compare([variant_mirror(tmp_path / "A-r1.jsonl", False)], [variant_mirror(tmp_path / "A2-r1.jsonl", False)],
                     [variant_mirror(tmp_path / "B-r1.jsonl", True)], target="vague_not_frozen",
                     guards=["model_calls", "no_blind_retry"])

    assert result["verdict"] == "판정 불가: 데이터 부족"
    assert result["guards_without_data"] == ["no_blind_retry"]


def test_prereg_guards_are_every_other_check_plus_the_three_cost_metrics():
    guards = prereg_guards("goal_preserved")
    assert "goal_preserved" not in guards
    assert set(guards) == {"trigger_ok", "tool_selection_ok", "args_valid", "vague_not_frozen", "frozen_ok",
                           "evidence_linked", "no_blind_retry", "retry_bounded", "side_effect_stable",
                           "contamination_free", "model_calls", "tool_calls", "latency_s"}


def test_attribute_counts_first_failures_by_stage_and_errored_runs_as_unchecked(tmp_path):
    path = tmp_path / "A-r1.jsonl"
    rows = [("S1", None), ("S2", None), ("S2", None), (None, "RuntimeError: x"), (None, None)]
    path.write_text("".join(json.dumps({"first_failure": stage, "error": error}) + "\n" for stage, error in rows),
                    encoding="utf-8")

    assert attribute([path]) == {"S1": 1, "S2": 2, "S3": 0, "S5": 0, "S6": 0, "unchecked": 1, "no_failure": 1}
