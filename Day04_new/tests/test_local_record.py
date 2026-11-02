"""run_experiment(record="local")와 저자 측정 스크립트(tests/run_measurement.py) 시험.

local 기록은 Langfuse를 만들지도 부르지도 않고, langfuse 기록과 같은 로컬 사본 줄과 <실행 이름>.meta.json을 남긴다.
키·네트워크·유료 호출은 없다. 모델은 가짜, 서버는 실제 server.py(stdio 자식 프로세스)다. 모든 쓰기는 tmp_path 아래에서만 한다.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cap_lab import experiment
from cap_lab.experiment import MIRROR_DIR, Variant, run_experiment
from cap_lab.settings import Settings
import run_measurement
from test_experiment import ConceptModel, FakeLangfuse, concept_case, mirror_lines, run_concepts

# 키 자리에 넣는 값. 접두어(sk-, pk-)가 없어 실제 키 모양 검사와 겹치지 않는다.
DUMMY_KEYS = {
    "anthropic_api_key": "dummy-anthropic-0001", "typesafe_api_key": "dummy-typesafe-0002",
    "openrouter_api_key": "dummy-openrouter-0003", "openai_api_key": "dummy-openai-0004",
    "azure_openai_api_key": "dummy-azure-0005", "langfuse_public_key": "dummy-public-0006",
    "langfuse_secret_key": "dummy-secret-0007",
}
META_KEYS = {
    "variant", "model", "effort", "skill_sha256", "server_sha256", "interface", "tool_disclosure", "gate_h1", "gate_h2",
    "threshold_h1", "threshold_h2", "jev_model", "dataset", "repeat", "record", "started_at", "finished_at", "case_ids",
}
CONCEPT_CASES = (("t-01", "MCP가 뭔가요?"), ("t-02", "장애가 났을 때 Seed는 뭔가요?"))


def refuse(name: str):
    def called(*args, **kwargs):
        raise AssertionError(f"local 기록에서 {name}을(를) 불렀습니다.")
    return called


@pytest.fixture
def no_langfuse(monkeypatch):
    """Langfuse SDK의 클라이언트와 LangChain 추적기를 만들면 바로 실패하게 한다(외부 SDK 경계)."""
    monkeypatch.setattr(experiment, "Langfuse", refuse("Langfuse"))
    monkeypatch.setattr(experiment, "CallbackHandler", refuse("CallbackHandler"))


def run_local(mirror_dir: Path, model: ConceptModel, cases: list[dict] | None = None, repeats: int = 1,
              settings: Settings | None = None) -> list[str]:
    cases = cases if cases is not None else [concept_case(*case) for case in CONCEPT_CASES]
    return asyncio.run(run_experiment(Variant("T"), cases, repeats, settings=settings or Settings(),
                                      mirror_dir=mirror_dir, model=model, record="local"))


def comparable(line: dict, base: Path) -> dict:
    """실행마다 달라지는 값(시간, 작업 폴더의 위치)을 뺀 줄. 근거 폴더는 base 기준 상대 경로로 바꾼다."""
    scores = [(s["name"], s["comment"]) if s["name"] == "latency_s" else s for s in line["scores"]]
    return {**line, "scores": scores, "evidence_dir": Path(line["evidence_dir"]).relative_to(base).as_posix()}


def test_an_unknown_record_value_is_refused_before_any_work(tmp_path, capsys):
    with pytest.raises(ValueError, match="record"):
        asyncio.run(run_experiment(Variant("T"), [concept_case("t-01", "MCP가 뭔가요?")], 1, settings=Settings(),
                                   mirror_dir=tmp_path / "runs", model=ConceptModel(messages=iter([])),
                                   record="langfus"))

    assert capsys.readouterr().out == ""
    assert not (tmp_path / "runs").exists()


def test_local_record_asks_only_for_the_anthropic_key_when_no_model_is_given(tmp_path):
    with pytest.raises(RuntimeError) as stopped:
        asyncio.run(run_experiment(Variant("T"), [concept_case("t-01", "MCP가 뭔가요?")], 1, settings=Settings(),
                                   mirror_dir=tmp_path / "runs", record="local"))

    assert str(stopped.value).startswith("ANTHROPIC_API_KEY가 미설정입니다.")
    assert not (tmp_path / "runs").exists()


def test_local_lines_have_the_same_keys_and_values_as_langfuse_lines_without_touching_langfuse(tmp_path, no_langfuse):
    run_concepts(tmp_path / "langfuse", ConceptModel(messages=iter([])), FakeLangfuse())
    assert run_local(tmp_path / "local" / "runs", ConceptModel(messages=iter([]))) == ["T-r1"]

    langfuse_lines = mirror_lines(tmp_path / "langfuse" / "runs" / "T-r1.jsonl")
    local_lines = mirror_lines(tmp_path / "local" / "runs" / "T-r1.jsonl")
    assert [set(line) for line in local_lines] == [set(line) for line in langfuse_lines]
    assert [comparable(line, tmp_path / "local") for line in local_lines] == [
        comparable(line, tmp_path / "langfuse") for line in langfuse_lines]
    assert [(line["case_id"], line["error"] is None) for line in local_lines] == [("t-01", True), ("t-02", False)]


def test_local_record_writes_one_line_per_case_per_repeat_in_case_order(tmp_path, no_langfuse):
    model = ConceptModel(messages=iter([]))
    assert run_local(tmp_path / "runs", model, repeats=2) == ["T-r1", "T-r2"]

    for repeat in (1, 2):
        lines = mirror_lines(tmp_path / "runs" / f"T-r{repeat}.jsonl")
        assert [(line["run_name"], line["repeat"], line["case_id"]) for line in lines] == [
            (f"T-r{repeat}", repeat, "t-01"), (f"T-r{repeat}", repeat, "t-02")]
    assert len(model.received) == 4
    assert sorted(path.name for path in (tmp_path / "work").iterdir()) == ["T-r1", "T-r2"]


def test_the_local_cost_notice_says_where_the_record_goes(tmp_path, no_langfuse, capsys):
    run_local(tmp_path / "runs", ConceptModel(messages=iter([])))

    assert capsys.readouterr().out.splitlines()[0] == (
        "이 실행은 사례 2 x 반복 1 = 2회, Claude 호출 약 10~18회(추정), Jev 호출 최대 0회(추정), 로컬 사본에만 기록합니다.")


def utc(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    assert moment.utcoffset() == timedelta(0), f"UTC가 아닌 시각입니다: {text}"
    return moment


def test_each_local_run_name_gets_a_meta_file_with_the_run_configuration_and_no_key_values(tmp_path, no_langfuse):
    run_local(tmp_path / "runs", ConceptModel(messages=iter([])), repeats=2, settings=Settings(**DUMMY_KEYS))

    texts = [(tmp_path / "runs" / f"T-r{repeat}.meta.json").read_text(encoding="utf-8") for repeat in (1, 2)]
    first, second = (json.loads(text) for text in texts)
    for repeat, meta in ((1, first), (2, second)):
        assert set(meta) == META_KEYS
        assert {key: meta[key] for key in ("variant", "model", "gate_h1", "gate_h2", "jev_model", "repeat", "record",
                                           "case_ids")} == {
            "variant": "T", "model": "injected:ConceptModel", "gate_h1": "off", "gate_h2": "off", "jev_model": "off",
            "repeat": repeat, "record": "local", "case_ids": ["t-01", "t-02"]}
        assert utc(meta["started_at"]) <= utc(meta["finished_at"])
    assert utc(first["finished_at"]) <= utc(second["started_at"])
    for text in texts:
        assert [value for value in DUMMY_KEYS.values() if value in text] == []


class FailingModel(ConceptModel):
    """부를 때마다 번호가 다른 모델 오류를 낸다. 받은 대화를 기록한다."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        raise RuntimeError(f"모델 장애 {len(self.received)}")


def numbered_cases(count: int) -> list[dict]:
    return [concept_case(f"t-{n:02d}", f"질문 {n}") for n in range(1, count + 1)]


def test_local_record_stops_after_three_errored_first_items_and_keeps_their_lines(tmp_path, no_langfuse):
    model = FailingModel(messages=iter([]))
    with pytest.raises(RuntimeError) as stopped:
        run_local(tmp_path / "runs", model, cases=numbered_cases(4), repeats=2)

    message = str(stopped.value)
    assert "T-r1" in message
    for n in (1, 2, 3):
        assert f"RuntimeError: 모델 장애 {n}" in message
    lines = mirror_lines(tmp_path / "runs" / "T-r1.jsonl")
    assert [(line["case_id"], line["error"]) for line in lines] == [
        (f"t-0{n}", f"RuntimeError: 모델 장애 {n}") for n in (1, 2, 3)]
    assert len(model.received) == 3
    assert json.loads((tmp_path / "runs" / "T-r1.meta.json").read_text(encoding="utf-8"))["finished_at"] is None
    assert not (tmp_path / "runs" / "T-r2.jsonl").exists()


def test_local_record_keeps_going_when_one_of_the_first_three_items_succeeds(tmp_path, no_langfuse):
    cases = [concept_case("t-01", "MCP가 뭔가요?"), *(concept_case(f"t-0{n}", f"장애 질문 {n}") for n in (2, 3, 4))]
    run_local(tmp_path / "runs", ConceptModel(messages=iter([])), cases=cases)

    lines = mirror_lines(tmp_path / "runs" / "T-r1.jsonl")
    assert [(line["case_id"], line["error"] is None) for line in lines] == [
        ("t-01", True), ("t-02", False), ("t-03", False), ("t-04", False)]


def test_langfuse_record_has_no_abort_guard(tmp_path):
    cases = numbered_cases(4)
    asyncio.run(run_experiment(Variant("T"), cases, 1, settings=Settings(), mirror_dir=tmp_path / "runs",
                               client=FakeLangfuse(), model=FailingModel(messages=iter([]))))

    assert [line["case_id"] for line in mirror_lines(tmp_path / "runs" / "T-r1.jsonl")] == [c["id"] for c in cases]


def test_local_record_refuses_an_existing_run_name_before_any_call(tmp_path, no_langfuse):
    (tmp_path / "work" / "T-r2").mkdir(parents=True)
    model = ConceptModel(messages=iter([]))
    with pytest.raises(RuntimeError, match=r"실행 기록 \['T-r2'\]"):
        run_local(tmp_path / "runs", model, repeats=2)

    assert model.received == []
    assert not (tmp_path / "runs").exists()
    assert [path.name for path in (tmp_path / "work").iterdir()] == ["T-r2"]


@pytest.fixture
def recorder(monkeypatch) -> list[dict]:
    """스크립트의 run_experiment와 load_settings 자리에 호출만 기록하는 대역을 넣는다. 반환: 기록 목록."""
    calls: list[dict] = []

    async def record_run(variant, cases, repeats, **options):
        calls.append({"variant": variant, "case_ids": [case["id"] for case in cases], "repeats": repeats, **options})
        return [f"{variant.name}-r{k}" for k in range(1, repeats + 1)]

    def record_settings():
        calls.append({"settings": "loaded"})
        return Settings()

    monkeypatch.setattr(run_measurement, "run_experiment", record_run)
    monkeypatch.setattr(run_measurement, "load_settings", record_settings)
    return calls


def test_holdout_without_open_holdout_exits_2_before_loading_settings_or_running(recorder, capsys):
    assert run_measurement.main(["--variant", "A", "--split", "holdout", "--repeats", "1"]) == 2

    assert recorder == []
    assert "--open-holdout" in capsys.readouterr().err


def test_defaults_record_locally_five_times_into_the_author_mirror_folder(recorder):
    assert run_measurement.main(["--variant", "A", "--split", "dev"]) == 0

    (call,) = [call for call in recorder if "variant" in call]
    assert (call["record"], call["repeats"], call["mirror_dir"]) == ("local", 5, MIRROR_DIR)
    assert call["case_ids"] == [f"dev-{n:02d}" for n in range(1, 11)]
    assert {"settings": "loaded"} in recorder


@pytest.mark.parametrize(("argv", "name", "gates"), [
    (["--variant", "A", "--split", "dev"], "dev-A", (False, False)),
    (["--variant", "A2", "--split", "dev"], "dev-A2", (False, False)),
    (["--variant", "B", "--split", "dev"], "dev-B", (True, True)),
    (["--variant", "B", "--split", "holdout", "--open-holdout"], "holdout-B", (True, True)),
])
def test_variant_names_carry_the_split_and_only_b_turns_both_gates_on(recorder, argv, name, gates):
    assert run_measurement.main([*argv, "--repeats", "1"]) == 0

    (call,) = [call for call in recorder if "variant" in call]
    assert (call["variant"].name, call["variant"].gate_h1, call["variant"].gate_h2) == (name, *gates)
    assert call["variant"].metadata["measurement"] == "author"


def test_an_opened_holdout_runs_the_holdout_cases_with_the_given_thresholds(recorder):
    argv = ["--variant", "B", "--split", "holdout", "--open-holdout", "--repeats", "2", "--record", "langfuse",
            "--threshold-h1", "0.7", "--threshold-h2", "0.4"]
    assert run_measurement.main(argv) == 0

    (call,) = [call for call in recorder if "variant" in call]
    assert call["case_ids"] == [f"ho-{n:02d}" for n in range(1, 9)]
    assert (call["repeats"], call["record"]) == (2, "langfuse")
    assert (call["variant"].threshold_h1, call["variant"].threshold_h2) == (0.7, 0.4)


def test_the_untuned_placeholder_threshold_is_named_as_such(recorder, capsys):
    run_measurement.main(["--variant", "B", "--split", "dev", "--threshold-h2", "0.6"])

    out = capsys.readouterr().out
    assert "H1 문턱값 0.5" in out and "미조정" in out
    assert "H2 문턱값" not in out


def test_the_script_exits_non_zero_when_the_run_raises(monkeypatch, capsys):
    async def stopped(*args, **options):
        raise RuntimeError("실행 기록 ['dev-A-r1']이(가) 이미 있습니다.")

    monkeypatch.setattr(run_measurement, "run_experiment", stopped)
    assert run_measurement.main(["--variant", "A", "--split", "dev"]) == 1
    assert "실행 기록 ['dev-A-r1']" in capsys.readouterr().err
