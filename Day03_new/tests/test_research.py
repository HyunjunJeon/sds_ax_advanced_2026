import re
import time
from types import SimpleNamespace

import pytest
from fakes import ParsedChatModel
from langchain_core.messages import AIMessage

import mas_lab.exa
from mas_lab.exa import ExaClient, allowed_url, assert_public_query, make_exa_tool
from mas_lab.research import ResearchPlan, ResearchReport, build_research_graph, url_overlap, validate_report
from mas_lab.trace import Trace, overlap_seconds
from rag_lab.evidence import BudgetExceeded


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(mas_lab.exa, "require_exa_key", lambda: SimpleNamespace(exa_key="test"))
    return ExaClient(trace=Trace(), max_searches=1)


@pytest.mark.parametrize(("url", "ok"), [("https://docs.langchain.com/x", True), ("https://docs.langchain.com.evil.test/x", False),
                                         ("https://evil.test/docs.langchain.com", False), ("file:///etc/passwd", False),
                                         ("https://user:pw@docs.langchain.com/", False), ("https://langchain.com/", False)])
def test_allowed_url_rejects_lookalikes(url, ok):
    assert allowed_url(url, frozenset({"docs.langchain.com"})) is ok


@pytest.mark.parametrize("query", ["알파 고객 크레딧 기한", "P-9002 환불", "INV-2026-08 내역", "베타 SLA"])
def test_internal_queries_stay_inside(query):
    with pytest.raises(ValueError):
        assert_public_query(query)


def test_public_query_passes():
    assert_public_query("multi-agent orchestration patterns")


def test_blocked_query_never_reaches_the_network(client):
    result = make_exa_tool(client).invoke({"query": "알파 고객 계약"})
    assert result["status"] == "blocked" and client.searches == 0 and "알파" not in result["message"]


def test_budget_stops_before_the_network(client):
    client.searches = 1
    with pytest.raises(BudgetExceeded):
        client.search("public topic")


def test_worker_limit_is_returned_to_the_model(client):
    tool = make_exa_tool(client, max_searches=0)
    assert tool.invoke({"query": "public topic"})["status"] == "search_limit"


def test_validate_report_flags_missing_and_unknown_sources():
    report = ResearchReport(summary="s", sections=[{"heading": "h", "claims": [{"text": "출처 없음", "source_ids": []}, {"text": "위조", "source_ids": ["S-x"]},
                                                                               {"text": "정상", "source_ids": ["S-1"]}]}])
    problems = validate_report(report, {"S-1": {}})
    assert len(problems) == 2 and "출처 없는" in problems[0] and "S-x" in problems[1]
    assert validate_report(None, {}) == ["보고서가 없습니다."]


def test_url_overlap():
    left = {"sources": {"a": {"url": "u1"}, "b": {"url": "u2"}}}
    right = {"sources": {"c": {"url": "u2"}, "d": {"url": "u3"}}}
    assert url_overlap(left, right) == {"왼쪽": 2, "오른쪽": 2, "겹침": 1, "Jaccard": 0.33}


def test_plan_schema():
    plan = ResearchPlan(topic="t", subtopics=[{"id": "a", "question": "q"}])
    assert plan.subtopics[0].id == "a"


def sleeping_finding(_messages):
    time.sleep(0.15)
    return AIMessage(content='{"claims": []}')


def test_parallel_research_workers_overlap_in_time(client):
    """Send 대신 for로 Worker를 부르면 구간 겹침이 0이 된다. 가짜 모델은 web_search를 부르지 않아 EXA 호출이 없다."""
    plan = ResearchPlan(topic="t", subtopics=[{"id": name, "question": "q"} for name in "abc"])
    model = ParsedChatModel(steps=[*[sleeping_finding] * 3, AIMessage(content='{"summary": "s"}')])
    build_research_graph(plan, client, model).invoke({})
    workers = [s for s in client.trace.spans if s["kind"] == "worker"]
    assert len(workers) == 3 and overlap_seconds(workers) > 0.05, workers
    assert client.searches == 0


@pytest.mark.parametrize("query", ["P-7001", "P-7001을", "p-7001", "P7001", "p7001", "p7001을", "INV-2026-03", "inv-2026-03", "INV-2026-03번",
                                   "INC-311", "inc-311의", "T-12", "t-12는", "고객P-7001은 환불", "p1000", "P-７００１ 환불", "P-٧٠٠١ refund", "T-１２",
                                   "INV-２０２６", "INV-가나다", "customer_P-7001"])
def test_internal_id_spellings_are_blocked(query):
    with pytest.raises(ValueError):
        assert_public_query(query)


@pytest.mark.parametrize("query", ["multi-agent orchestration patterns", "p99 latency", "p50 지연", "gpt-4 evaluation", "T cell", "t-test",
                                   "inv에 대한 설명", "python 3.13", "p999 latency"])
def test_internal_id_spellings_leave_ordinary_queries_alone(query):
    assert_public_query(query)


@pytest.mark.parametrize(("query", "spelled", "particle"), [("P-7001을 환불", "P-7001", "을"), ("p7001을 환불", "p7001", "을"),
                                                          ("INV-2026-03번 내역", "INV-2026-03", "번"), ("inc-311의 원인", "inc-311", "의"),
                                                          ("t-12는 무엇", "t-12", "는")])
def test_internal_id_spellings_message_names_the_id_without_the_particle(query, spelled, particle):
    with pytest.raises(ValueError) as error:
        assert_public_query(query)
    message = str(error.value)
    assert spelled in message and spelled + particle not in message


# 옛 INTERNAL_PATTERN을 글자 그대로 옮겨 둔다. exa.py에서 가져오면 패턴을 좁혀도 같이 좁아져 이 시험이 잡지 못한다.
OLD_INTERNAL_PATTERN = re.compile(r"\b(?:P-\d+|INV-[\w-]+|INC-\d+|T-\d+)\b")
OLD_BLOCKED = ["P-9002 환불", "INV-2026-08 내역", "INC-311", "T-12", "(P-7001)", "P-7001, P-7002", "고객: P-7001 환불", "Re: INV-2026-03", "INV-2026-03-",
               "INV-abc", "INV-2026- 내역", "INV-2026-03번 내역", "INV-2026_03", "INV-_x", "P-1", "P-７００１ 환불", "P-٧٠٠١ refund", "T-１２", "INC-３１１",
               "INV-２０２６", "INV-가나다", "P-7001٧"]


@pytest.mark.parametrize("query", OLD_BLOCKED)
def test_internal_id_spellings_keep_everything_the_old_pattern_blocked(query):
    assert OLD_INTERNAL_PATTERN.search(query), "표본이 옛 패턴에 막히지 않으면 이 시험의 전제가 깨진다"
    with pytest.raises(ValueError):
        assert_public_query(query)
