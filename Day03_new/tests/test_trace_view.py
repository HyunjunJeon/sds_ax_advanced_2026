import time

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from mas_lab.contracts import merge_results
from mas_lab.trace import ModelMeter, Trace, longest_path, overlap_seconds, timeline
from mas_lab.view import bars, flows_of, message_table

from typing import Annotated, TypedDict


class S(TypedDict, total=False):
    item: str
    results: Annotated[dict, merge_results]


def fan_out(trace):
    def work(state):
        with trace.span(state["item"], "worker"):
            time.sleep(0.15)
        return {"results": {state["item"]: "ok"}}

    graph = StateGraph(S)
    graph.add_node("work", work)
    graph.add_conditional_edges(START, lambda _: [Send("work", {"item": i}) for i in "abc"], ["work"])
    graph.add_edge("work", END)
    return graph.compile()


def test_send_runs_concurrently_and_max_concurrency_serializes():
    parallel, serial = Trace(), Trace()
    assert fan_out(parallel).invoke({})["results"] == {"a": "ok", "b": "ok", "c": "ok"}
    fan_out(serial).invoke({}, config={"max_concurrency": 1})
    assert overlap_seconds(parallel.spans) > 0.05 and overlap_seconds(serial.spans) == 0.0
    assert "#" in timeline(parallel.spans)


def test_overlap_and_longest_path():
    spans = [{"start": 0, "end": 2}, {"start": 1, "end": 3}, {"start": 5, "end": 6}]
    assert overlap_seconds(spans) == 1
    assert longest_path({"a": 1, "b": 2, "c": 3}, {"c": ["a", "b"]}) == 5


def test_meter_does_not_count_missing_usage_as_zero():
    meter = ModelMeter()
    assert meter.totals()["input_tokens"] is None
    meter.calls.append({"input_tokens": None, "output_tokens": None, "cache_read_tokens": None, "start": 0, "end": 1})
    assert meter.totals()["usage_missing"] == 1 and meter.totals()["input_tokens"] is None


def test_flows_of_detects_cycle_and_conditionals():
    graph = StateGraph(S)
    graph.add_node("a", lambda s: {})
    graph.add_node("b", lambda s: {})
    graph.add_edge(START, "a")
    graph.add_edge("a", "b")
    graph.add_conditional_edges("b", lambda s: "a", ["a", END])
    flows = flows_of(graph.compile())
    assert flows["순환"] and flows["조건부 간선"] == 2 and flows["노드"] == 2


def test_view_helpers():
    assert "##" in bars({"a": 10, "b": 5})
    assert message_table([]) == []
