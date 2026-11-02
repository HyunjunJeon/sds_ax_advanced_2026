"""설치된 deepagents 위에서 Agent 경로의 경계를 가짜 모델로 시험한다. 실제 모델 확인은 live_smoke.py가 맡는다."""
import json
from datetime import date

import pytest
from deepagents import __version__ as deepagents_version
from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, ToolMessage
from fakes import ScriptedChatModel, ScriptExhausted, rag_script, tool_call
from langchain_core.messages import HumanMessage
from rag_lab.agent import ALLOWED_TOOLS, Session, allowlist_middleware, ask, build_rag_agent, check_skill_folder
from rag_lab.corpus import Scope, load_corpus
from rag_lab.evidence import Budget, BudgetExceeded, RetrievalContext
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT

QUESTION = "알파 서비스 크레딧 신청 기한은 언제인가요?"
ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))
FINISH = AIMessage(content=json.dumps({"skill": "grounded-qa", "status": "answered", "sections": []}))


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(load_corpus())


@pytest.fixture
def run_ask(retriever, skills_dir):
    """ask를 부르고, 저장된 기록 파일을 시험 뒤에 지운다."""
    records = []

    def run(steps, *, question=QUESTION, **kwargs):
        options = {"max_attempts": 1, **kwargs}
        record = ask(question, retriever=retriever, scope=ALPHA_NOW,
                     model=ScriptedChatModel(steps=steps), skills_dir=skills_dir, **options)
        records.append(record)
        return record

    yield run
    for record in records:
        (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").unlink(missing_ok=True)


def tool_messages(result: dict) -> list[ToolMessage]:
    return [m for m in result["messages"] if isinstance(m, ToolMessage)]


def test_installed_deepagents_version_is_the_one_the_design_measured():
    assert deepagents_version == "0.7.32"


def test_model_sees_only_allowlisted_tools(retriever, skills_dir):
    model = ScriptedChatModel(steps=[FINISH])
    build_rag_agent(RetrievalContext(retriever, ALPHA_NOW), model=model, skills_dir=skills_dir).invoke(
        {"messages": [{"role": "user", "content": QUESTION}]})
    assert set(model.bound_tool_names) == ALLOWED_TOOLS


def test_agent_asks_for_native_format_and_never_forces_a_tool(retriever, skills_dir):
    """Opus 5.5는 tool_choice any/tool을 400으로 거부한다. ToolStrategy로 돌아가면 여기서 잡힌다."""
    model = ScriptedChatModel(steps=[FINISH])
    build_rag_agent(RetrievalContext(retriever, ALPHA_NOW), model=model, skills_dir=skills_dir).invoke(
        {"messages": [{"role": "user", "content": QUESTION}]})
    assert model.bound_kwargs["response_format"]["type"] == "json_schema"
    assert model.bound_kwargs.get("tool_choice") in {None, "auto"}


def test_without_allowlist_model_sees_write_tools():
    """위 시험이 의미 있으려면 필터가 없을 때 쓰기 도구가 보여야 한다."""
    model = ScriptedChatModel(steps=[AIMessage(content="끝")])
    create_deep_agent(model=model).invoke({"messages": [{"role": "user", "content": "안녕"}]})
    assert {"write_file", "edit_file", "task"} <= set(model.bound_tool_names)


def test_hidden_tool_is_denied_and_never_runs(retriever, skills_dir):
    context = RetrievalContext(retriever, ALPHA_NOW)
    steps = [tool_call("write_file", {"file_path": "/만든파일.md", "content": "x"}), FINISH]
    result = build_rag_agent(context, model=ScriptedChatModel(steps=steps), skills_dir=skills_dir).invoke(
        {"messages": [{"role": "user", "content": QUESTION}]})
    denied = tool_messages(result)[0]
    assert denied.status == "error" and "허용하지 않는 도구" in denied.text
    assert not (skills_dir / "만든파일.md").exists()
    assert [e["name"] for e in context.budget.report()["events"] if e["event"] == "tool_denied"] == ["write_file"]


def test_custom_allowlist_hides_tool(retriever, skills_dir):
    model = ScriptedChatModel(steps=[FINISH])
    allowed = ALLOWED_TOOLS - {"grep"}
    build_rag_agent(RetrievalContext(retriever, ALPHA_NOW), model=model, allowed=allowed, skills_dir=skills_dir).invoke(
        {"messages": [{"role": "user", "content": QUESTION}]})
    assert "grep" not in model.bound_tool_names and "glob" in model.bound_tool_names


def test_middleware_stops_run_when_model_budget_is_spent():
    budget = Budget(max_model_calls=1)
    steps = [tool_call("없는도구", {}), AIMessage(content="끝")]
    agent = create_deep_agent(model=ScriptedChatModel(steps=steps), middleware=allowlist_middleware(budget))
    with pytest.raises(BudgetExceeded):
        agent.invoke({"messages": [{"role": "user", "content": "안녕"}]})


def test_system_prompt_lists_skill_metadata_not_body(retriever, skills_dir):
    model = ScriptedChatModel(steps=[FINISH])
    build_rag_agent(RetrievalContext(retriever, ALPHA_NOW), model=model, skills_dir=skills_dir).invoke(
        {"messages": [{"role": "user", "content": QUESTION}]})
    system = model.calls[0][0].text
    assert "grounded-qa의 답변 절차를 안내한다." in system and "알파" in system and "2026-09-08" in system
    assert "절차 149" not in system


def test_ask_end_to_end_with_script_passes_validation(run_ask):
    record = run_ask(rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한"))
    assert record["status"] == "answered" and record["validation"] == "passed" and record["errors"] == []
    assert record["loaded_skills"] == ["grounded-qa"]
    assert record["support_review"] == "skipped"
    assert "label" not in record
    assert record["trace"]["counts"]["model"] == 4
    assert record["markdown"].startswith("## 결론") and " · L" in record["markdown"]
    assert record["evidence"]
    assert (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").is_file()


def test_ask_insufficient_script_is_a_normal_result(run_ask):
    record = run_ask(rag_script(skill="insufficient-evidence", query="화성 지사 주소"), question="알파 고객의 화성 지사 주소는?")
    assert record["status"] == "insufficient" and record["validation"] == "passed"
    assert record["answer"]["missing"]


def test_ask_records_skill_not_read_as_error(run_ask):
    steps = rag_script(skill="grounded-qa", query="서비스 크레딧")[1:]
    record = run_ask(steps)
    assert record["status"] == "error" and record["validation"] == "failed"
    assert "grounded-qa/SKILL.md 전체 본문을 read_file로 읽어야 합니다." in record["errors"]


def test_ask_budget_overrun_returns_error_record_instead_of_raising(run_ask):
    steps = [tool_call("search_knowledge", {"query": "기한"}), tool_call("search_knowledge", {"query": "기한"})]
    record = run_ask(steps, budget=Budget(max_searches=1))
    assert record["status"] == "error"
    assert record["errors"] == ["BudgetExceeded: search 호출 한도를 초과했습니다."]
    assert record["trace"]["counts"]["search"] == 1


def test_ask_script_exhaustion_is_visible(run_ask):
    record = run_ask(rag_script(skill="grounded-qa", query="기한")[:1])
    assert record["status"] == "error" and record["errors"][0].startswith(ScriptExhausted.__name__)


def test_ask_records_non_json_final_reply_as_error(run_ask):
    record = run_ask([AIMessage(content="JSON이 아닌 답")])
    assert record["status"] == "error" and record["errors"][0].startswith("StructuredOutputValidationError")


def test_validation_retry_keeps_history_append_only(retriever, skills_dir):
    """이력을 고치면 Opus 5.5가 thinking 블록을 거부한다. 재시도는 앞선 메시지 뒤에 덧붙이기만 해야 한다."""
    good = rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한")
    model = ScriptedChatModel(steps=[FINISH, *good])
    record = ask(QUESTION, retriever=retriever, scope=ALPHA_NOW, model=model, skills_dir=skills_dir, max_attempts=2)
    (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").unlink()
    first, retry = model.calls[0], model.calls[1]
    assert [m.text for m in retry[:len(first)]] == [m.text for m in first]
    assert retry[len(first)].text == FINISH.text
    assert isinstance(retry[len(first) + 1], HumanMessage) and retry[len(first) + 1].text.startswith("검증 실패")


def test_ask_retries_with_validation_errors_in_messages(run_ask):
    good = rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한")
    steps = [good[3], *good]
    record = run_ask(steps, max_attempts=2)
    assert record["status"] == "answered"
    assert any(e["event"] == "validation_retry" for e in record["trace"]["events"])


def test_reviewer_failure_blocks_answer_and_is_recorded(run_ask):
    reviewer = ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": False, "reasons": ["지지 안 됨"]}))])
    record = run_ask(rag_script(skill="grounded-qa", query="서비스 크레딧"), reviewer=reviewer)
    assert record["status"] == "error" and record["validation"] == "passed"
    assert record["support_review"] == "failed" and record["errors"] == ["지지 안 됨"]


def test_reviewer_pass_is_recorded(run_ask):
    reviewer = ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": True}))])
    record = run_ask(rag_script(skill="grounded-qa", query="서비스 크레딧"), reviewer=reviewer)
    assert record["status"] == "answered" and record["support_review"] == "passed"


def test_session_keeps_only_text_and_evidence_restarts(run_ask):
    session = Session("s1", ALPHA_NOW)
    first = run_ask(rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한"), session=session)
    assert [m["role"] for m in session.history] == ["user", "assistant"]
    model_steps = rag_script(skill="grounded-qa", query="가용률")
    second = run_ask(model_steps, session=session, question="그럼 가용률은?")
    assert len(session.history) == 4
    assert second["trace"]["counts"]["search"] == 1
    assert first["evidence"] != second["evidence"]
    assert "evidence_id" not in str(session.history)


def test_failed_turn_is_not_added_to_session(run_ask):
    session = Session("s1", ALPHA_NOW)
    run_ask(rag_script(skill="grounded-qa", query="기한")[:1], session=session)
    assert session.history == []


def test_session_scope_mismatch_raises(retriever):
    session = Session("s1", ALPHA_NOW)
    with pytest.raises(ValueError):
        ask(QUESTION, retriever=retriever, scope=Scope("베타", date(2026, 9, 8)),
            model=ScriptedChatModel(steps=[]), session=session)


def test_fake_model_does_not_wrap_around():
    model = ScriptedChatModel(steps=[AIMessage(content="한 번")])
    assert model.invoke("가").text == "한 번"
    with pytest.raises(ScriptExhausted):
        model.invoke("나")


def test_fake_step_can_build_reply_from_messages():
    model = ScriptedChatModel(steps=[lambda messages: AIMessage(content=f"받은 메시지 {len(messages)}개")])
    assert model.invoke("가").text == "받은 메시지 1개"


@pytest.mark.parametrize("frontmatter, expected", [
    ("name: Bad_Name\ndescription: 설명", "name은 소문자"),
    ("name: other\ndescription: 설명", "폴더 이름과 다릅니다"),
    ("name: my-skill", "description은 1~1024자"),
    (f"name: my-skill\ndescription: {'가' * 1025}", "description은 1~1024자"),
])
def test_check_skill_folder_reports_each_violation(tmp_path, frontmatter, expected):
    folder = tmp_path / "my-skill"
    folder.mkdir()
    (folder / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n본문\n", encoding="utf-8")
    assert any(expected in problem for problem in check_skill_folder(folder))


def test_check_skill_folder_passes_good_and_flags_missing(tmp_path, skills_dir):
    assert check_skill_folder(skills_dir / "grounded-qa") == []
    assert "SKILL.md" in check_skill_folder(tmp_path)[0]
