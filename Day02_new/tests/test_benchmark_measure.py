"""측정 도구의 지표, 분할, 답변 측정 기록. 손으로 계산한 값을 기준으로 삼고 모델은 부르지 않는다."""
import json
import os

import pytest

from benchmarks.allganize import Case
import argparse

from benchmarks.measure import (ANSWERS_OUT, RankCache, compare_ksq, in_gold_group, ksq_ranking, ranking_metrics, sample_train_ids, summarize_ksq, corroboration_file_runs, doc_ranking, file_source_view, FailingReranker, MemoReranker, TuneRun, answer_row, class_changes, compare_pages, follow_up_pairs, gate_summary, measure_answers,
                                parse_pair, doc_recall, done_pairs, first_rank, hit_at, outcome, page_chunks, page_documents, paired_bootstrap, plan_queries,
                                reciprocal_rank, row_key, run_answers, split_by_scope, summarize_answers, summarize_docs, summarize_pages, tune_cases,
                                two_phase_runners)
from benchmarks.measure import (KO_ANSWER_STRING, KO_EXCLUDED, KO_NAMED_ONE, KO_NAMED_TWO, KO_RUNS, KO_UNANSWERABLE, compare_ko, decompose_rows, ko_cases, ko_chunk_vectors, ko_documents, ko_metrics, ko_report, ko_runs,
                                ko_sample, probability_quartiles, split_ko_documents, title_mention_ranking, main)
from benchmarks.allganize import Page
from fakes import HashEmbeddings, ScriptedChatModel, ScriptedDecider
from rag_lab.corpus import load_corpus
from rag_lab.pipeline import retrieve
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT


def test_first_rank_counts_from_one_and_misses_are_none():
    assert first_rank(["a", "b", "c"], ["c", "b"]) == 2
    assert first_rank(["a", "b"], ["z"]) is None


def test_reciprocal_rank_is_zero_for_a_miss_and_beyond_depth():
    assert reciprocal_rank(["a", "b", "c"], ["b"], 3) == 0.5
    assert reciprocal_rank(["a", "b", "c"], ["z"], 3) == 0.0
    assert reciprocal_rank(["a", "b", "c", "d"], ["d"], 3) == 0.0


def test_doc_recall_is_fraction_of_expected_inside_top_k():
    assert doc_recall(["a", "x", "b"], ["a", "b"], 2) == 0.5
    assert doc_recall(["a", "x", "b"], ["a", "b"], 3) == 1.0


def test_hit_at_respects_cutoff():
    assert hit_at(["p1", "p2", "p3"], "p3", 2) == 0
    assert hit_at(["p1", "p2", "p3"], "p3", 3) == 1


def row(case_id, expected, ranked, in_scope=True):
    return {"id": case_id, "expected": expected, "ranked": ranked, "in_scope": in_scope}


def test_summarize_docs_counts_a_miss_as_zero_and_skips_rows_without_expected_docs():
    rows = [row("hit", ["a"], ["a", "b"]), row("late", ["b"], ["a", "b"]), row("miss", ["z"], ["a", "b"]),
            row("abstain", [], ["a"])]
    summary = summarize_docs(rows)
    assert summary["n"] == 3
    assert summary["recall@1"] == pytest.approx((1 / 3), abs=1e-4)
    assert summary["recall@2"] == pytest.approx((2 / 3), abs=1e-4)
    assert summary["mrr@3"] == pytest.approx(((1 + 0.5 + 0) / 3), abs=1e-4)


def test_split_by_scope_separates_out_of_scope_rows_and_drops_abstentions():
    rows = [row("inside", ["a"], ["a"]), row("outside", ["old"], ["a"], in_scope=False), row("abstain", [], ["a"])]
    inside, outside = split_by_scope(rows)
    assert [r["id"] for r in inside] == ["inside"]
    assert [r["id"] for r in outside] == ["outside"]


def test_row_key_orders_a_better_rank_above_a_worse_one():
    assert row_key(row("x", ["a"], ["a"])) > row_key(row("x", ["a"], ["b", "a"])) > row_key(row("x", ["a"], ["b"]))


def test_summarize_pages_reports_hits_mrr_and_context_type_counts():
    rows = [{"target": "p1", "context_type": "image", "ranked": ["p1"]},
            {"target": "p2", "context_type": "image", "ranked": ["p9", "p2"]},
            {"target": "p3", "context_type": "table", "ranked": ["p9"]}]
    summary = summarize_pages(rows)
    assert summary["hit@1"] == pytest.approx((1 / 3), abs=1e-4)
    assert summary["hit@3"] == pytest.approx((2 / 3), abs=1e-4)
    assert summary["mrr@10"] == pytest.approx(((1 + 0.5 + 0) / 3), abs=1e-4)
    assert summary["hit@5_by_context_type"] == {"image": "2/2", "table": "0/1"}


def test_tune_cases_excludes_every_other_split():
    def case(case_id, split):
        return Case(case_id, "d", "q", "a", "f.pdf", 1, "text", split)
    kept = tune_cases([case("a", "tune"), case("b", "other"), case("c", "tune")])
    assert [c.case_id for c in kept] == ["a", "c"]


def test_page_chunks_overlap_prefix_and_blank_pages():
    pages = [Page("doc.pdf", 1, "가" * 1000), Page("doc.pdf", 2, "")]
    documents = page_documents(pages, {"doc.pdf#2": "판독 글자"})
    first = page_chunks(documents["doc.pdf#1"])
    assert [len(c.text) for c in first] == [len("doc\n") + 800, len("doc\n") + 300]
    assert first[1].text == "doc\n" + "가" * 300 and first[1].start == 700
    assert page_chunks(page_documents(pages, None)["doc.pdf#2"]) == []
    assert "판독 글자" in page_chunks(documents["doc.pdf#2"])[0].text


# ---- 답변 측정 ----

SONNET = "claude-sonnet-5-5"
EVIDENCE = [{"evidence_id": "E-1", "doc_id": "sla-a-v2"}, {"evidence_id": "E-2", "doc_id": "sla-a-amendment"},
            {"evidence_id": "E-3", "doc_id": "runbook"}]


def answered(*evidence_ids):
    return {"skill": "grounded-qa", "status": "answered",
            "sections": [{"heading": "결론", "items": [{"text": "문장", "evidence_ids": list(evidence_ids)}]}]}


def run_record(**overrides):
    return {"run_id": "r1", "status": "answered", "validation": "passed", "errors": [], "answer": answered("E-1"),
            "evidence": EVIDENCE, "trace": {"counts": {"model": 4, "search": 1}, "events": []}} | overrides


def usage_row(calls=1, tokens_in=1000, tokens_out=100, cached=200, written=300, cost=0.5, model=SONNET):
    return {"model": model, "calls": calls, "input": tokens_in, "output": tokens_out, "cached": cached, "written": written, "cost": cost}


GOLD_SLA = {"expected_docs": ["sla-a-v2", "sla-a-amendment"], "abstain": False}
GOLD_ABSTAIN = {"expected_docs": [], "abstain": True}
CASE = {"id": "c1", "type": "simple"}


def build_row(record, gold=GOLD_SLA, usage=None):
    return answer_row("two_phase_auto", CASE, record, gold, usage or [usage_row()], 1.25)


@pytest.mark.parametrize("record, expected", [
    (run_record(), "passed"),
    (run_record(status="insufficient"), "passed"),
    (run_record(status="error", validation="failed", errors=["인용문에 없는 숫자: 30"]), "validation_failed"),
    (run_record(status="error", validation="failed", errors=["AnswerPayload가 없습니다."]), "validation_failed"),
    (run_record(status="error", errors=["grounded-qa/SKILL.md 전체 본문을 read_file로 읽어야 합니다."]), "validation_failed"),
    (run_record(status="error", errors=["BudgetExceeded: model 호출 한도를 초과했습니다."]), "errored"),
    (run_record(status="error", errors=["anthropic.BadRequestError: 400"]), "errored"),
])
def test_outcome_separates_exceptions_from_validation_failures(record, expected):
    assert outcome(record) == expected


def test_answer_row_maps_citations_to_documents_and_reports_partial_coverage():
    row = build_row(run_record())
    assert row["cited_doc_ids"] == ["sla-a-v2"]
    assert row["retrieved_doc_ids"] == ["runbook", "sla-a-amendment", "sla-a-v2"]
    assert row["expected_cited"] is False and row["expected_retrieved"] is True


def test_answer_row_coverage_is_null_for_a_case_without_expected_docs():
    row = build_row(run_record(status="insufficient"), gold=GOLD_ABSTAIN)
    assert row["expected_cited"] is None and row["expected_retrieved"] is None
    assert row["abstain_expected"] is True


def test_answer_row_does_not_count_citations_of_an_answer_that_was_not_released():
    row = build_row(run_record(status="error", validation="failed", errors=["x"], answer=answered("E-1", "E-2")))
    assert row["cited_doc_ids"] == [] and row["expected_cited"] is False


def test_answer_row_reports_ask_records_without_gate_or_verification_as_null():
    row = build_row(run_record())
    assert row["verification"] is None and row["gate_confidence"] is None
    assert row["decision_backend"] is None and row["decision_model"] is None and row["decision_calls"] == 0


def test_answer_row_reads_gate_verification_and_fast_phase_from_two_phase_records():
    gates = [{"gate": "decompose", "backend": "typesafe", "model": None, "probability": None},
             {"gate": "follow_up", "backend": "typesafe", "model": "jev-latest", "probability": 0.7}]
    record = run_record(verification="ran", gates=gates, citations_removed=[{"evidence_id": "E-9"}], diagnostics=["query-decomposition-fallback: x"],
                        fast_answer=answered("E-3"), phases=[{"name": "prefetch", "errors": []},
                                                             {"name": "fast", "errors": ["절 제목"]}])
    row = build_row(record)
    assert row["verification"] == "ran" and row["gate_confidence"] == 0.7
    assert (row["decision_backend"], row["decision_model"]) == ("typesafe", "jev-latest")
    assert row["citations_removed"] == 1 and row["diagnostics"] == ["query-decomposition-fallback: x"]
    assert row["fast_cited_doc_ids"] == ["runbook"] and row["fast_errors"] == ["절 제목"]


def test_answer_row_reads_warnings_and_budget_events_from_the_trace():
    trace = {"counts": {"model": 2}, "events": [{"event": "retrieval_warning", "warning": "rerank-failed: E"},
                                                {"event": "context_excluded", "doc_id": "a"},
                                                {"event": "context_excluded", "doc_id": "b"}]}
    row = build_row(run_record(trace=trace))
    assert row["retrieval_warnings"] == ["rerank-failed: E"] and row["context_excluded"] == 2
    assert row["model_calls"] == 2 and row["searches"] == 0


def test_answer_row_sums_usage_across_models_and_keeps_an_unknown_price_as_null():
    row = build_row(run_record(), usage=[usage_row(), usage_row(calls=2, tokens_in=10, tokens_out=1, cached=0, written=0, cost=0.25)])
    assert (row["usage_calls"], row["input_tokens"], row["output_tokens"]) == (3, 1010, 101)
    assert (row["cache_read_tokens"], row["cache_write_tokens"]) == (200, 300) and row["cost"] == 0.75
    assert build_row(run_record(), usage=[usage_row(cost=None)])["cost"] is None


def test_answer_row_with_no_usage_costs_nothing():
    record = run_record(status="error", errors=["BudgetExceeded: x"])
    row = answer_row("ask_hybrid", CASE, record, GOLD_SLA, [], 0.1)
    assert row["usage_calls"] == 0 and row["cost"] == 0


def test_done_pairs_reads_rows_and_ignores_stop_events_and_a_missing_file(tmp_path):
    path = tmp_path / "answers.jsonl"
    assert done_pairs(path) == set()
    path.write_text('{"config": "a", "case_id": "1"}\n{"event": "stopped", "reason": "cost_cap"}\n', encoding="utf-8")
    assert done_pairs(path) == {("a", "1")}


class Lab:
    """가짜 실행기를 꽂아 run_answers를 돈다. 실행기는 실제 UsageLog처럼 환경 변수의 파일에 사용량을 적는다."""
    def __init__(self, tmp_path, *, model=SONNET, output_tokens=100_000):
        self.out, self.usage_dir = tmp_path / "answers.jsonl", tmp_path / "usage"
        self.model, self.output_tokens, self.calls = model, output_tokens, []

    def runner(self, config):
        def run(case):
            self.calls.append((config, case["id"]))
            with open(os.environ["DAY02_USAGE_LOG"], "a", encoding="utf-8") as log:
                log.write(json.dumps({"model": self.model, "input_tokens": 0, "output_tokens": self.output_tokens,
                                      "cache_read_tokens": 0, "cache_write_tokens": 0}) + "\n")
            return run_record(status="error", errors=["BudgetExceeded: 한도"])
        return run

    def go(self, case_ids=("c1", "c2"), configs=("x", "y"), **kwargs):
        cases = [{"id": case_id, "type": "t"} for case_id in case_ids]
        runners = {config: self.runner(config) for config in configs}
        return run_answers(cases, runners, dict.fromkeys(case_ids, GOLD_SLA), self.out, self.usage_dir, **kwargs)

    def lines(self):
        return [json.loads(line) for line in self.out.read_text(encoding="utf-8").splitlines()]


def test_run_answers_keeps_a_failed_row_and_prices_it_from_the_usage_log(tmp_path):
    lab = Lab(tmp_path)
    assert lab.go(case_ids=("c1",), configs=("x",)) == "finished"
    row = lab.lines()[0]
    assert row["config"] == "x" and row["case_id"] == "c1" and row["outcome"] == "errored"
    assert row["usage_calls"] == 1 and row["cost"] == pytest.approx(1.0)  # 출력 10만 토큰 x $10/100만
    assert "DAY02_USAGE_LOG" not in os.environ


def test_run_answers_goes_case_by_case_so_a_stopped_run_stays_comparable(tmp_path):
    lab = Lab(tmp_path, output_tokens=1)
    lab.go()
    assert lab.calls == [("x", "c1"), ("y", "c1"), ("x", "c2"), ("y", "c2")]


def test_rerun_skips_recorded_pairs_and_spends_nothing_on_them(tmp_path):
    lab = Lab(tmp_path, output_tokens=1)
    lab.go(case_ids=("c1",))
    lab.calls.clear()
    lab.go(case_ids=("c1", "c2"))
    assert lab.calls == [("x", "c2"), ("y", "c2")]
    assert len(lab.lines()) == 4


def test_cost_cap_stops_before_the_next_row_and_records_the_stop(tmp_path):
    lab = Lab(tmp_path)  # 행마다 $1
    assert lab.go(cap=2.0) == "cost_cap"  # 둘째 행을 돌리면 $2.00에 닿으므로 첫 행 뒤에 멈춘다. 상한을 넘기지 않는다.
    assert len(lab.calls) == 1
    last = lab.lines()[-1]
    assert last["event"] == "stopped" and last["reason"] == "cost_cap" and last["spent"] == pytest.approx(1.0)


def test_cost_just_under_the_cap_runs_the_next_row(tmp_path):
    lab = Lab(tmp_path)
    assert lab.go(case_ids=("c1",), configs=("x", "y"), cap=2.01) == "finished"  # 첫 행 뒤 $1.00 + 다음 행 $1.00 < $2.01이라 둘째 행도 돈다.
    assert len(lab.calls) == 2


def test_spend_of_a_deleted_row_still_counts_toward_the_cap(tmp_path):
    lab = Lab(tmp_path)
    lab.go(case_ids=("c1",), configs=("x", "y"), cap=10.0)
    lab.out.unlink()  # 고친 결함 때문에 지운 행의 비용도 사용 기록에 남아 한도에 들어간다.
    lab.calls.clear()
    assert lab.go(case_ids=("c2",), configs=("x",), cap=2.0) == "cost_cap"
    assert lab.calls == []


def test_unpriced_usage_stops_the_run_rather_than_counting_as_free(tmp_path):
    lab = Lab(tmp_path, model="claude-unknown")
    assert lab.go() == "unpriced_usage"
    assert len(lab.calls) == 1 and lab.lines()[0]["cost"] is None
    assert lab.lines()[-1]["reason"] == "unpriced_usage"


def test_time_limit_ends_the_call_without_a_stop_record_and_a_rerun_continues(tmp_path):
    lab = Lab(tmp_path, output_tokens=1)
    assert lab.go(max_seconds=0) == "time_limit"
    assert lab.calls == [] and not lab.out.exists()
    assert lab.go() == "finished" and len(lab.calls) == 4


def test_summarize_answers_counts_each_outcome_and_ignores_stop_events():
    def row(config, result, **fields):
        return {"config": config, "case_id": "c", "outcome": result, "model_calls": 4, "seconds": 2.0, "cost": 0.5,
                "verification": None} | fields
    rows = [row("a", "passed", verification="ran", model_calls=6, seconds=4.0), row("a", "errored"),
            row("a", "validation_failed", cost=None), {"event": "stopped", "reason": "cost_cap"}]
    assert summarize_answers(rows) == {"a": {"rows": 3, "passed": 1, "errored": 1, "validation_failed": 1, "verification_ran": 1,
                                             "mean_model_calls": 14 / 3, "mean_seconds": 8 / 3, "cost": 1.0, "unpriced_rows": 1}}


def test_pairs_run_only_the_named_rows(tmp_path):
    lab = Lab(tmp_path, output_tokens=1)
    assert lab.go(case_ids=("c1", "c2"), configs=("x", "y"), pairs={("y", "c1"), ("x", "c2")}) == "finished"
    assert lab.calls == [("y", "c1"), ("x", "c2")]
    assert [(row["config"], row["case_id"]) for row in lab.lines()] == [("y", "c1"), ("x", "c2")]


def test_parse_pair_splits_config_and_case_and_rejects_a_missing_half():
    assert parse_pair("two_phase_always:simple-deadline-current") == ("two_phase_always", "simple-deadline-current")
    for bad in ("two_phase_always", ":c1", "x:"):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_pair(bad)


def test_measure_answers_with_out_writes_that_file_and_never_the_original(tmp_path):
    original = ANSWERS_OUT.read_bytes() if ANSWERS_OUT.exists() else None
    out, calls = tmp_path / "answers_2.jsonl", []

    def runner(config):
        def run(case):
            calls.append((config, case["id"]))
            return run_record(status="error", errors=["BudgetExceeded: 한도"])
        return run

    runners = {"ask_hybrid": runner("ask_hybrid"), "two_phase_always": runner("two_phase_always")}
    measure_answers(None, out, tmp_path / "usage", None, pairs={("two_phase_always", "single-renewal-notice")}, runners=runners)
    assert calls == [("two_phase_always", "single-renewal-notice")]
    assert [(row["config"], row["case_id"]) for row in map(json.loads, out.read_text(encoding="utf-8").splitlines())] == calls
    assert (ANSWERS_OUT.read_bytes() if ANSWERS_OUT.exists() else None) == original


def test_measure_answers_rejects_a_pair_with_an_unknown_config_before_any_call(tmp_path):
    with pytest.raises(SystemExit):
        measure_answers(None, tmp_path / "o.jsonl", tmp_path / "usage", None, pairs={("nope", "single-renewal-notice")},
                        runners={"ask_hybrid": lambda case: pytest.fail("호출되면 안 됩니다")})
    assert not (tmp_path / "o.jsonl").exists()


def test_two_phase_runners_pass_the_decider_and_differ_only_in_decomposition():
    decider = ScriptedDecider()
    runners = two_phase_runners(Retriever(load_corpus()), ScriptedChatModel(steps=[]), None, decider)
    assert set(runners) == {"two_phase_jev", "two_phase_jev_no_decompose"}
    case = {"id": "c1", "type": "simple", "question": "서비스 크레딧 신청 기한은?", "entity": "알파", "as_of": "2026-09-08"}
    records = {config: run(case) for config, run in runners.items()}
    for record in records.values():
        (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").unlink()
    assert [gate["gate"] for gate in records["two_phase_jev"]["gates"]] == ["decompose"]
    assert records["two_phase_jev_no_decompose"]["gates"] == []
    row = answer_row("two_phase_jev", case, records["two_phase_jev"], GOLD_ABSTAIN, [], 0.1)
    assert (row["decision_backend"], row["decision_model"]) == ("fake-backend", "fake-model") and row["decision_calls"] == 1


def test_old_two_phase_rows_stay_readable_in_the_summary():
    old = {"config": "two_phase_auto", "outcome": "passed", "verification": "skipped", "model_calls": 2, "seconds": 3.0, "cost": 0.05,
           "gate_confidence": 0.1}
    assert summarize_answers([old])["two_phase_auto"]["passed"] == 1


# ---- Jev 사용량: Claude 지출과 나눠 센다 ----

def jev_usage(calls=3, tokens_in=900, tokens_out=60):
    return usage_row(calls=calls, tokens_in=tokens_in, tokens_out=tokens_out, cached=0, written=0, cost=None, model="jev-1.14.0")


def test_answer_row_keeps_claude_cost_when_jev_reports_no_price():
    row = build_row(run_record(), usage=[usage_row(), jev_usage()])
    assert row["cost"] == 0.5 and (row["usage_calls"], row["input_tokens"], row["output_tokens"]) == (1, 1000, 100)
    assert (row["jev_calls"], row["jev_input_tokens"], row["jev_output_tokens"]) == (3, 900, 60)
    assert row["jev_cost"] is None


def test_answer_row_sums_jev_cost_only_when_the_provider_reported_it():
    assert build_row(run_record(), usage=[usage_row(), usage_row(cost=0.02, model="typesafe/jev-1.13")])["jev_cost"] == 0.02


def test_answer_row_records_gates_queries_and_removed_citations():
    gates = [{"gate": "decompose", "backend": "typesafe", "model": "jev-1.14.0", "probability": 0.8, "fallback": None}]
    removed = [{"evidence_id": "E-9", "doc_id": "toc", "probability": 0.03}]
    row = build_row(run_record(gates=gates, queries=["q", "q1"], citations_removed=removed))
    assert row["gates"] == gates and row["queries"] == ["q", "q1"]
    assert row["citations_removed"] == 1 and row["citations_removed_detail"] == removed


class JevLab(Lab):
    """Claude 한 줄과 Jev 한 줄을 함께 적는 실행기. 실제 두 단계 실행의 사용 기록과 같은 모양이다."""
    def runner(self, config):
        def run(case):
            self.calls.append((config, case["id"]))
            with open(os.environ["DAY02_USAGE_LOG"], "a", encoding="utf-8") as log:
                log.write(json.dumps({"model": self.model, "input_tokens": 0, "output_tokens": self.output_tokens,
                                      "cache_read_tokens": 0, "cache_write_tokens": 0}) + "\n")
                log.write(json.dumps({"model": "jev-1.14.0", "input_tokens": 400, "output_tokens": 20}) + "\n")
            return run_record()
        return run


def test_jev_usage_without_a_price_does_not_stop_the_run_and_the_cap_counts_only_claude(tmp_path):
    lab = JevLab(tmp_path, output_tokens=1)
    assert lab.go() == "finished" and len(lab.calls) == 4
    assert all(line["jev_calls"] == 1 and line["cost"] == pytest.approx(0.00001) for line in lab.lines())


def test_cap_still_stops_a_run_whose_claude_spend_reaches_it_with_jev_rows_present(tmp_path):
    lab = JevLab(tmp_path)  # 행마다 Claude $1
    assert lab.go(cap=2.0) == "cost_cap" and len(lab.calls) == 1


def test_an_unknown_claude_model_still_stops_the_run_when_jev_rows_are_present(tmp_path):
    lab = JevLab(tmp_path, model="claude-unknown")
    assert lab.go() == "unpriced_usage" and len(lab.calls) == 1


# ---- Jev 측정의 집계 ----

def test_paired_bootstrap_of_identical_runs_is_exactly_zero():
    assert paired_bootstrap([0.0] * 20) == {"mean": 0.0, "low": 0.0, "high": 0.0, "rounds": 10000, "seed": 20261101}


def test_paired_bootstrap_of_a_constant_difference_is_that_constant():
    result = paired_bootstrap([1.0] * 20)
    assert (result["mean"], result["low"], result["high"]) == (1.0, 1.0, 1.0)


def test_paired_bootstrap_interval_covers_the_mean_and_stays_inside_the_values():
    differences = [0.0] * 18 + [1.0, -1.0]
    result = paired_bootstrap(differences)
    assert result["mean"] == 0.0 and -1.0 <= result["low"] < 0.0 < result["high"] <= 1.0
    assert paired_bootstrap(differences) == result  # 시드가 고정이라 다시 계산해도 같다.


def test_paired_bootstrap_rejects_an_empty_comparison():
    with pytest.raises(ValueError):
        paired_bootstrap([])


def test_gate_summary_counts_fires_fallbacks_and_bins():
    rows = [{"id": "a", "probability": 0.05, "decision": False, "fallback": None},
            {"id": "b", "probability": 0.5, "decision": True, "fallback": None},
            {"id": "c", "probability": 1.0, "decision": True, "fallback": None},
            {"id": "d", "probability": None, "decision": False, "fallback": "query-decomposition-fallback"}]
    summary = gate_summary(rows)
    assert (summary["n"], summary["fired"], summary["rate"]) == (4, 2, 0.5)
    assert summary["fallback_ids"] == ["d"]
    assert summary["probability"]["min"] == 0.05 and summary["probability"]["median"] == 0.5 and summary["probability"]["max"] == 1.0
    assert summary["bins"]["0.0-0.1"] == 1 and summary["bins"]["0.5-0.6"] == 1 and summary["bins"]["0.9-1.0"] == 1
    assert sum(summary["bins"].values()) == 3


def test_plan_queries_uses_saved_subqueries_only_where_the_configuration_says():
    gates = {"open": {"decision": True}, "shut": {"decision": False}}
    saved = {"open": ["s1"], "shut": ["s2"]}
    assert plan_queries("no_decompose", "open", gates, saved) is None
    assert plan_queries("always_decompose", "shut", gates, saved) == ["s2"]
    assert plan_queries("gated_decompose", "open", gates, saved) == ["s1"]
    assert plan_queries("gated_decompose", "shut", gates, saved) is None


def test_failing_reranker_makes_retrieve_keep_the_merged_order_and_warn():
    retriever = Retriever(load_corpus())
    plain = retrieve("서비스 크레딧 신청 기한", retriever=retriever, scope=None, pool=10, top_n=10)
    failed = retrieve("서비스 크레딧 신청 기한", retriever=retriever, scope=None, reranker=FailingReranker(), pool=10, top_n=10)
    assert failed.chunk_ids == plain.chunk_ids and failed.warnings == ["rerank-failed: RuntimeError"]


class CountingReranker:
    def __init__(self):
        self.seen = []

    def score(self, query, texts):
        self.seen += [(query, text) for text in texts]
        return [float(len(text)) for text in texts]


def test_memo_reranker_scores_a_pair_once_and_keeps_input_order():
    inner = CountingReranker()
    memo = MemoReranker(inner)
    assert memo.score("q", ["aa", "b"]) == [2.0, 1.0]
    assert memo.score("q", ["b", "ccc", "aa"]) == [1.0, 3.0, 2.0]
    assert inner.seen == [("q", "aa"), ("q", "b"), ("q", "ccc")]
    assert memo.score("other", ["b"]) == [1.0] and inner.seen[-1] == ("other", "b")


def test_tune_run_names_differ_for_every_switch():
    names = {TuneRun("no_decompose", True, False).name, TuneRun("no_decompose", False, False).name, TuneRun("no_decompose", True, True).name}
    assert len(names) == 3


def page_row(case_id, target, ranked):
    return {"id": case_id, "target": target, "context_type": "text", "ranked": ranked}


def test_compare_pages_pairs_rows_by_id_and_names_every_changed_row():
    base = [page_row("up", "p", ["x", "x2", "p"]), page_row("down", "p", ["p"]), page_row("same", "p", ["p"])]
    other = [page_row("same", "p", ["p"]), page_row("down", "p", ["x", "p"]), page_row("up", "p", ["p"])]
    result = compare_pages(base, other)
    assert result["n"] == 3
    assert result["mrr@10"]["mean"] == pytest.approx(((1 - 1 / 3) + (0.5 - 1) + 0) / 3)
    assert result["hit@5"]["mean"] == 0.0
    assert [row["id"] for row in result["better"]] == ["up"] and [row["id"] for row in result["worse"]] == ["down"]
    assert result["better"][0]["base_rank"] == 3 and result["better"][0]["rank"] == 1


def test_compare_pages_treats_a_page_found_beyond_ten_as_a_miss_in_mrr_but_keeps_the_rank():
    ranked = [f"x{i}" for i in range(10)] + ["p"]
    result = compare_pages([page_row("late", "p", ranked)], [page_row("late", "p", ["p"])])
    assert result["mrr@10"]["mean"] == 1.0
    assert result["better"][0]["base_rank"] == 11


def test_follow_up_pairs_keep_rows_without_a_gate_and_read_fast_failures():
    def answer(case, probability, fast_errors, fallback=None):
        gates = [{"gate": "follow_up", "probability": probability, "fallback": fallback}] if probability is not None or fallback else []
        return {"config": "c", "case_id": case, "gates": gates, "fast_errors": fast_errors, "verification": "skipped"}
    pairs = follow_up_pairs([answer("ok", 0.1, []), answer("bad", 0.9, ["e"]), answer("nogate", None, ["AnswerPayload"]),
                             answer("down", None, [], fallback="follow-up-check-fallback"), {"event": "stopped"}])
    assert [(p["case_id"], p["probability"], p["fast_failed"]) for p in pairs] == [
        ("ok", 0.1, False), ("bad", 0.9, True), ("nogate", None, True), ("down", None, False)]
    assert pairs[3]["fallback"] == "follow-up-check-fallback"


def test_class_changes_names_worse_and_better_rows_and_counts_every_reordering():
    off = [row("up", ["a"], ["b", "a"]), row("down", ["a"], ["a", "b"]), row("same", ["a"], ["a", "b", "c"]), row("abstain", [], ["x", "y"])]
    on = [row("up", ["a"], ["a", "b"]), row("down", ["a"], ["b", "a"]), row("same", ["a"], ["a", "c", "b"]), row("abstain", [], ["y", "x"])]
    result = class_changes(off, on)
    assert [r["id"] for r in result["better"]] == ["up"] and [r["id"] for r in result["worse"]] == ["down"]
    assert result["ranking_changed"] == 4


# ---- 출처 보강도: 파일 출처 ----

class LengthReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(len(text)) for text in texts]


def small_retriever(corroboration=True):
    pages = [Page("a.pdf", 1, "환불 규정 열흘 안 신청 가능"), Page("a.pdf", 2, "환불 수수료 규정 표"), Page("a.pdf", 3, "환불 예외 규정"),
             Page("b.pdf", 1, "배송 규정 사흘"), Page("b.pdf", 2, "환불 안내 배송 규정")]
    return Retriever(page_documents(pages, None), chunker=page_chunks, mode="fusion", embeddings=HashEmbeddings(), corroboration=corroboration)


def test_file_source_view_gives_every_page_of_a_file_one_source_and_keeps_chunk_ids():
    retriever = small_retriever()
    view = file_source_view(retriever)
    sources = {}
    for chunk_id, chunk in view.chunks.items():
        sources.setdefault(chunk.doc_id, set()).add(retriever.chunks[chunk_id].doc_id)
    assert sources == {"a.pdf": {"a.pdf#1", "a.pdf#2", "a.pdf#3"}, "b.pdf": {"b.pdf#1", "b.pdf#2"}}
    assert view.chunks.keys() == retriever.chunks.keys()
    assert {c.doc_id for c in retriever.chunks.values()} == {"a.pdf#1", "a.pdf#2", "a.pdf#3", "b.pdf#1", "b.pdf#2"}  # 원래 검색기는 그대로다


def test_corroboration_file_runs_off_equals_the_plain_corroboration_off_retrieval():
    cases = [Case("c1", "d", "환불 규정", "", "a.pdf", 1, "paragraph", "tune"), Case("c2", "d", "배송 규정 사흘", "", "b.pdf", 1, "text", "tune")]
    runs = corroboration_file_runs(small_retriever(), LengthReranker(), cases)
    plain = small_retriever(corroboration=False)
    expected = [doc_ranking(plain, retrieve(case.question, retriever=plain, scope=None, reranker=LengthReranker(), pool=50, top_n=50).chunk_ids) for case in cases]
    assert [row["ranked"] for row in runs["off__rerank_normal"]] == expected
    assert set(runs) == {f"{source}__rerank_{rerank}" for source in ("off", "page_source", "file_source") for rerank in ("normal", "failed")}


def test_sample_train_ids_shuffles_the_sorted_ids_with_the_fixed_seed_whatever_the_input_order():
    assert sample_train_ids(["q3", "q1", "q5", "q2", "q4", "q6"], size=4) == ["q3", "q4", "q2", "q5"]  # random.Random(20261101)을 정렬한 q1..q6에 적용한 값
    assert sample_train_ids({"q6", "q5", "q4", "q3", "q2", "q1"}, size=6) == ["q3", "q4", "q2", "q5", "q1", "q6"]
    assert sample_train_ids(["q1", "q2"], size=300) == sample_train_ids(["q2", "q1"], size=300)


def ksq_row(query_id, gold, ndcg, recall10=0.0):
    return {"id": query_id, "gold": gold, "recall@5": 0.0, "recall@10": recall10, "recall@100": 0.0, "mrr@10": 0.0, "ndcg@10": ndcg}


def test_gold_count_split_puts_one_gold_and_several_gold_questions_in_their_own_groups():
    assert [in_gold_group(count, group) for group in ("all", "one_gold", "two_plus_gold") for count in (1, 2, 5)] == [
        True, True, True, True, False, False, False, True, True]
    rows = [ksq_row("a", 1, 1.0), ksq_row("b", 2, 0.5), ksq_row("c", 3, 0.0)]
    assert summarize_ksq(rows, "one_gold")["n"] == 1
    assert summarize_ksq(rows, "two_plus_gold") == {"recall@5": 0.0, "recall@10": 0.0, "recall@100": 0.0, "mrr@10": 0.0, "ndcg@10": 0.25, "n": 2}
    assert summarize_ksq([ksq_row("a", 1, 1.0)], "two_plus_gold") == {"n": 0}


def test_ranking_metrics_count_fractions_of_several_gold_and_normalize_ndcg_by_the_ideal_list():
    metrics = ranking_metrics(["x", "g1", "y", "g2"], {"g1", "g2"})
    assert metrics["recall@5"] == 1.0 and metrics["recall@10"] == 1.0
    assert metrics["mrr@10"] == 0.5
    assert metrics["ndcg@10"] == pytest.approx((1 / 1.5849625 + 1 / 2.3219281) / (1 + 1 / 1.5849625), abs=1e-6)  # log2(3), log2(5) / 이상적 순위 1, log2(3)
    assert ranking_metrics(["g1", "x"], {"g1", "g2"})["recall@5"] == 0.5
    assert ranking_metrics(["x"], {"g1"})["ndcg@10"] == 0.0


def test_compare_ksq_pairs_questions_by_id_and_restricts_to_group_and_ids():
    base = [ksq_row("a", 1, 0.2), ksq_row("b", 2, 0.4), ksq_row("c", 2, 0.4)]
    other = [ksq_row("c", 2, 0.4), ksq_row("a", 1, 0.2), ksq_row("b", 2, 0.9)]  # 순서가 달라도 ID로 짝짓는다
    both = compare_ksq(base, other, "two_plus_gold")
    assert both["n"] == 2 and both["ndcg@10"]["mean"] == pytest.approx(0.25) and (both["ndcg@10"]["better"], both["ndcg@10"]["same"]) == (1, 1)
    assert compare_ksq(base, other, "all", {"a", "c"})["ndcg@10"]["mean"] == 0.0
    assert compare_ksq(base, other, "one_gold", {"b"}) == {"n": 0}


class StubRetriever:
    """질의마다 정해진 순위를 돌려주고 불린 횟수를 센다."""
    def __init__(self, ranks):
        self.chunks = {key: type("C", (), {"text": key})() for ranking in ranks.values() for key in ranking}
        self.ranks, self.calls = ranks, 0

    def rank(self, query, scope, limit=6):
        self.calls += 1
        return self.ranks[query][:limit]


def test_rank_cache_computes_each_query_once_and_returns_a_prefix():
    stub = StubRetriever({"q": [f"d{i}" for i in range(120)]})
    cache = RankCache(stub)
    assert cache.rank("q", None, 3) == ["d0", "d1", "d2"] and cache.rank("q", None, 50) == [f"d{i}" for i in range(50)]
    assert stub.calls == 1
    with pytest.raises(ValueError):
        cache.rank("q", None, 101)


def test_ksq_ranking_appends_the_unreranked_tail_after_the_reranked_pool():
    ranking = [f"d{i}" for i in range(120)]
    cache = RankCache(StubRetriever({"q": ranking}))

    class ReverseReranker:
        def score(self, query, texts):
            return [-index for index in range(len(texts))][::-1]  # 마지막 후보가 가장 높다

    ranked = ksq_ranking("q", cache, ReverseReranker(), None)
    assert ranked[:50] == ranking[:50][::-1]
    assert ranked[50:] == ranking[50:100]


# ---- Ko-LongRAG: 합성 행만 쓴다. 데이터 글은 시험에도 넣지 않는다. ----

def ko_row(row_id, task, question, answer, *blocks):
    context = "".join(f"Title: {title} Text:{body}\n\n" for title, body in blocks)
    return {"id": row_id, "task": task, "question": question, "answer": answer, "titles": [title for title, _ in blocks], "context": context}


def test_split_strips_one_pair_of_wrapping_quotes_the_context_lacks():
    row = {"id": "r", "titles": ['"가나"', "다라"], "context": "Title: 가나 Text:첫째\n\nTitle: 다라 Text:둘째"}
    assert split_ko_documents(row) == [("가나", "첫째"), ("다라", "둘째")]


def test_split_matches_a_repeated_title_block_by_block_rather_than_through_a_dict():
    row = {"id": "r", "titles": ["가", "가"], "context": "Title: 가 Text:첫째 Title: 가 Text:둘째"}
    assert split_ko_documents(row) == [("가", "첫째"), ("가", "둘째")]


def test_split_does_not_cut_on_title_text_inside_a_body_or_on_blank_lines():
    row = {"id": "r", "titles": ["가", "나"], "context": "Title: 가 Text:Title: 없는 말\n\n둘째 문단 Title: 나 Text:끝"}
    assert split_ko_documents(row) == [("가", "Title: 없는 말\n\n둘째 문단"), ("나", "끝")]


def test_split_refuses_a_row_whose_title_block_is_missing():
    with pytest.raises(ValueError, match="r1"):
        split_ko_documents({"id": "r1", "titles": ["없음"], "context": "Title: 가 Text:본문"})


def test_gold_tier_two_named_titles_on_a_multidoc_row_keeps_both_documents_and_only_them():
    case = ko_cases([ko_row("m1", "multidocQA", "가나와 다라 중 어디가 큰가?", "예", ("가나", "a"), ("다라", "b"), ("마바", "c"))])[0]
    assert case.tier == KO_NAMED_TWO and len(case.gold) == 2


def test_gold_tier_one_named_title_on_a_single_row_keeps_that_document():
    documents = ko_documents([row := ko_row("s1", "singledocQA", "가나는 어디인가?", "답 아님", ("가나", "a"), ("다라", "b"))])
    case = ko_cases([row])[0]
    assert case.tier == KO_NAMED_ONE and [documents[doc_id].title for doc_id in case.gold] == ["가나"]


def test_gold_tier_answer_string_takes_the_documents_holding_the_answer():
    documents = ko_documents([row := ko_row("m2", "multidocQA", "그곳의 수도는?", "서울특별시.", ("가", "수도는 서울특별시"), ("나", "다른 말"), ("다", "서울특별시 근처"))])
    case = ko_cases([row])[0]
    assert case.tier == KO_ANSWER_STRING and sorted(documents[doc_id].title for doc_id in case.gold) == ["가", "다"]


@pytest.mark.parametrize("answer, question, bodies, why", [
    ("아니오", "그곳은 큰가?", ["아니오 라는 말"], "yes/no 답"),
    ("서울", "그곳은?", ["서울"], "세 글자 미만 답"),
    ("서울특별시", "서울특별시의 인구는?", ["서울특별시"], "질문에 이미 있는 답"),
    ("서울특별시", "그곳은?", ["없음"], "어느 문서에도 없는 답"),
    ("서울특별시", "그곳은?", ["서울특별시"] * 4, "네 문서 이상에 있는 답"),
])
def test_rows_without_defensible_gold_are_excluded_and_not_guessed(answer, question, bodies, why):
    blocks = [(f"제목{index}", body) for index, body in enumerate(bodies)]
    case = ko_cases([ko_row("x", "multidocQA", question, answer, *blocks)])[0]
    assert (case.tier, case.gold) == (KO_EXCLUDED, ()), why


def test_unanswerable_rows_are_marked_by_the_answer_text_even_when_a_title_is_named():
    case = ko_cases([ko_row("u", "multidocQA", "가나와 다라는?", KO_UNANSWERABLE + " 더 찾아보세요.", ("가나", "a"), ("다라", "b"))])[0]
    assert case.tier == "excluded_unanswerable" and case.gold == ()


def test_a_single_row_naming_two_titles_is_not_a_named_one_row():
    case = ko_cases([ko_row("s2", "singledocQA", "가나와 다라는?", "아니오", ("가나", "a"), ("다라", "b"))])[0]
    assert case.tier == KO_EXCLUDED


def test_corpus_is_the_union_of_unique_title_and_body_pairs_and_keeps_two_bodies_of_one_title_apart():
    rows = [ko_row("a", "multidocQA", "q", "예", ("가", "본문1"), ("나", "본문2")), ko_row("b", "multidocQA", "q", "예", ("가", "본문1"), ("가", "다른 본문"))]
    documents = ko_documents(rows)
    assert sorted((doc.title, doc.text) for doc in documents.values()) == [("가", "다른 본문"), ("가", "본문1"), ("나", "본문2")]
    assert not any("가" in doc_id or "나" in doc_id for doc_id in documents)


def test_sample_takes_every_answerable_multidoc_row_and_a_seeded_150_of_answerable_single_rows():
    multi = [ko_row(f"m{i}", "multidocQA", "q", "예", ("가", "a")) for i in range(3)] + [ko_row("mu", "multidocQA", "q", KO_UNANSWERABLE, ("가", "a"))]
    single = [ko_row(f"s{i:03}", "singledocQA", "q", "예", ("가", "a")) for i in range(200)] + [ko_row("su", "singledocQA", "q", KO_UNANSWERABLE, ("가", "a"))]
    picked = ko_sample(ko_cases(multi + single))
    assert {"m0", "m1", "m2"} <= set(picked) and "mu" not in picked and "su" not in picked
    assert sum(item.startswith("s") for item in picked) == 150 and len(picked) == 153
    assert picked == ko_sample(ko_cases(single + multi))


def test_all_of_metrics_count_a_fraction_of_the_gold_and_full_gold_needs_both_inside_ten():
    ranked = ["a"] + [f"x{i}" for i in range(10)] + ["b"]
    metrics = ko_metrics(ranked, ("a", "b"), KO_NAMED_TWO)
    assert metrics["recall@5"] == metrics["recall@10"] == 0.5 and metrics["recall@25"] == 1.0 and metrics["pool_recall@50"] == 1.0
    assert metrics["full_gold@10"] == 0 and metrics["mrr@10"] == 1.0
    assert metrics["ndcg@10"] == pytest.approx(1 / (1 + 1 / 1.5849625007))


def test_any_of_metrics_score_one_when_any_gold_document_is_found_and_count_only_the_first():
    metrics = ko_metrics(["x", "a", "b"], ("a", "b", "c"), KO_ANSWER_STRING)
    assert metrics["recall@5"] == 1.0 and metrics["full_gold@10"] == 1 and metrics["mrr@10"] == 0.5
    assert metrics["ndcg@10"] == pytest.approx(1 / 1.5849625007)


def test_a_miss_scores_zero_everywhere():
    metrics = ko_metrics(["x", "y"], ("a",), KO_NAMED_ONE)
    assert all(value == 0 for value in metrics.values())


def test_pool_recall_stops_at_fifty_ranked_documents():
    ranked = [f"x{i}" for i in range(50)] + ["a"]
    assert ko_metrics(ranked, ("a",), KO_NAMED_ONE)["pool_recall@50"] == 0


def test_title_mention_baseline_puts_longer_titles_first_and_keeps_only_titles_in_the_question():
    titles = {"d1": "가", "d2": "가나다", "d3": "없는 제목"}
    assert title_mention_ranking("가나다는 무엇인가?", titles) == ["d2", "d1"]


def test_compare_ko_names_improved_and_worsened_rows_and_gives_identical_runs_a_zero_interval():
    base = [{"id": name, "group": "g", "recall@10": 0.5, "full_gold@10": 0, "ndcg@10": 0.5, "pool_recall@50": 0.5} for name in ("a", "b", "c")] + [{"id": "z", "group": "other", "recall@10": 0.0, "full_gold@10": 0, "ndcg@10": 0.0, "pool_recall@50": 0.0}]
    other = [row | {"ndcg@10": {"a": 1.0, "b": 0.25, "c": 0.5}.get(row["id"], 1.0)} for row in base]
    compared = compare_ko(base, other, "g")
    assert compared["n"] == 3 and compared["ndcg@10"]["improved_ids"] == ["a"] and compared["ndcg@10"]["worsened_ids"] == ["b"]
    assert compared["recall@10"]["mean"] == compared["recall@10"]["low"] == compared["recall@10"]["high"] == 0


def test_compare_ko_of_an_empty_group_reports_no_rows_rather_than_failing():
    assert compare_ko([], [], "g") == {"n": 0}


def test_probability_quartiles_count_rows_and_opens_and_leave_out_a_row_without_a_judgment():
    rows = [{"probability": p, "decision": p >= 0.5} for p in (0.1, 0.2, 0.6, 0.9)] + [{"probability": None, "decision": False}]
    quartiles = probability_quartiles(rows)
    assert [(q["quartile"], q["n"], q["opened"]) for q in quartiles] == [("Q1", 1, 0), ("Q2", 1, 0), ("Q3", 1, 1), ("Q4", 1, 1)]
    assert probability_quartiles([{"probability": None, "decision": False}]) == []


def run_decompose(tmp_path, reply, ids=("a", "b"), saved=None, cap=1.0, max_seconds=None):
    return decompose_rows(list(ids), {name: f"질문 {name}" for name in ids}, reply, tmp_path / "d.json", saved if saved is not None else {"rows": {}, "stops": []},
                          tmp_path, cap=cap, max_seconds=max_seconds, backoff=0)


def test_decompose_rows_retries_a_failure_records_it_by_type_and_keeps_only_the_type_name(tmp_path):
    failures = {"a": 1}

    def reply(question):
        if question == "질문 a" and failures["a"]:
            failures["a"] -= 1
            raise TimeoutError("비밀 글")
        return ["하위 질의"]

    assert run_decompose(tmp_path, reply) == "finished"
    saved = json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))
    assert saved["rows"]["a"] == {"queries": ["하위 질의"], "attempts": 2, "errors": ["TimeoutError"], "fallback": False}
    assert saved["rows"]["b"]["attempts"] == 1


def test_decompose_rows_marks_the_question_only_reply_as_a_fallback(tmp_path):
    run_decompose(tmp_path, lambda question: [question], ids=("a",))
    assert json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))["rows"]["a"]["fallback"] is True


def test_decompose_rows_leaves_a_row_that_kept_failing_for_the_next_call_and_counts_its_attempts(tmp_path):
    def broken(question):
        raise TimeoutError

    saved = {"rows": {}, "stops": []}
    run_decompose(tmp_path, broken, ids=("a",), saved=saved)
    assert saved["rows"]["a"]["queries"] is None and saved["rows"]["a"]["errors"] == ["TimeoutError"] * 3
    run_decompose(tmp_path, lambda question: ["q"], ids=("a",), saved=saved)
    assert saved["rows"]["a"]["queries"] == ["q"] and saved["rows"]["a"]["attempts"] == 4


def test_decompose_rows_skips_rows_already_done(tmp_path):
    calls = []
    saved = {"rows": {"a": {"queries": ["q"], "attempts": 1, "errors": [], "fallback": False}}, "stops": []}
    run_decompose(tmp_path, lambda question: calls.append(question) or ["q"], saved=saved)
    assert calls == ["질문 b"]


def test_decompose_rows_stops_at_the_cap_before_a_batch_and_says_so(tmp_path):
    (tmp_path / "spent.usage.jsonl").write_text(json.dumps({"model": "claude-sonnet-5-5", "input_tokens": 1_000_000, "output_tokens": 0}) + "\n", encoding="utf-8")
    calls = []
    saved = {"rows": {}, "stops": []}
    assert run_decompose(tmp_path, lambda question: calls.append(question) or ["q"], saved=saved, cap=1.0) == "cost_cap"
    assert calls == [] and saved["stops"][0]["reason"] == "cost_cap"


def test_decompose_rows_time_limit_ends_the_call_without_a_stop_record(tmp_path):
    saved = {"rows": {}, "stops": []}
    assert run_decompose(tmp_path, lambda question: ["q"], saved=saved, max_seconds=0) == "time_limit"
    assert saved["stops"] == [] and saved["rows"] == {}


def ko_tiny():
    rows = [ko_row("m1", "multidocQA", "가나 왕국과 다라 왕국은 언제 세워졌나?", "예", ("가나 왕국", "세워진 해는 천 년이다."), ("다라 왕국", "세워진 해는 이천 년이다."), ("마바", "관련 없는 글")),
            ko_row("s1", "singledocQA", "마바는 무엇인가?", "답 아님", ("마바", "관련 없는 글"), ("사아", "다른 글"))]
    documents = ko_documents(rows)
    cases = ko_cases(rows)
    retriever = Retriever(documents, chunker=page_chunks, embeddings=HashEmbeddings(), mode="fusion")
    gates = {"m1": {"id": "m1", "probability": 0.9, "decision": True, "fallback": None, "model": "jev-x"}, "s1": {"id": "s1", "probability": 0.1, "decision": False, "fallback": None, "model": "jev-x"}}
    return rows, cases, retriever, gates


class ConstantReranker:
    def score(self, query, texts):
        return [0.0] * len(texts)


def test_ko_runs_score_the_gold_rows_keep_corroboration_off_to_multidoc_and_store_no_data_text(tmp_path):
    rows, cases, retriever, gates = ko_tiny()
    saved = {"m1": ["가나 왕국", "다라 왕국"], "s1": ["마바"]}
    report = {}
    assert ko_runs(report, tmp_path / "out.json", cases, retriever, ConstantReranker(), gates, saved, None) == "finished"
    by_run = report["runs"]
    assert {row["id"] for row in by_run["gated_decompose"]} == {"m1", "s1"} and {row["id"] for row in by_run["gated_decompose__corroboration_off"]} == {"m1"}
    assert {row["id"]: row["queries"] for row in by_run["gated_decompose"]} == {"m1": 3, "s1": 1}
    assert {row["id"]: row["queries"] for row in by_run["always_decompose"]} == {"m1": 3, "s1": 2}
    assert next(row for row in by_run["no_decompose"] if row["id"] == "m1")["recall@25"] == 1.0
    written = (tmp_path / "out.json").read_text(encoding="utf-8")
    for text in ("가나", "다라", "왕국", "마바", "세워진"):
        assert text not in written


def test_ko_runs_resume_row_by_row_without_recomputing_a_finished_row(tmp_path):
    _, cases, retriever, gates = ko_tiny()
    finished = {"id": "m1", "group": "kept", "queries": 1}
    report = {"runs": {name: [finished] for name in KO_RUNS}}
    ko_runs(report, tmp_path / "out.json", cases, retriever, ConstantReranker(), gates, {"m1": ["가"], "s1": ["나"]}, None)
    assert report["runs"]["no_decompose"][0] is finished and [row["id"] for row in report["runs"]["no_decompose"]] == ["m1", "s1"]


def test_ko_runs_stop_at_the_time_limit_and_a_later_call_finishes(tmp_path):
    _, cases, retriever, gates = ko_tiny()
    report = {}
    saved = {"m1": ["가"], "s1": ["나"]}
    assert ko_runs(report, tmp_path / "out.json", cases, retriever, ConstantReranker(), gates, saved, 0) == "time_limit"
    assert ko_runs(report, tmp_path / "out.json", cases, retriever, ConstantReranker(), gates, saved, None) == "finished"


def test_ko_report_gives_tables_per_group_gate_rates_per_task_and_stays_free_of_data_text(tmp_path):
    rows, cases, retriever, gates = ko_tiny()
    (tmp_path / "claude").mkdir()
    (tmp_path / "jev").mkdir()
    (tmp_path / "claude" / "d.usage.jsonl").write_text(json.dumps({"model": "claude-sonnet-5-5", "input_tokens": 1000, "output_tokens": 100, "cache_read_tokens": 0, "cache_write_tokens": 0}) + "\n", encoding="utf-8")
    (tmp_path / "jev" / "g.usage.jsonl").write_text(json.dumps({"model": "jev-1.14.0", "input_tokens": 300, "output_tokens": 5}) + "\n", encoding="utf-8")
    report = {"gates": {"rows": list(gates.values())}}
    decomposed = {"rows": {"m1": {"queries": ["가나 왕국", "다라 왕국"], "attempts": 2, "errors": ["TimeoutError"], "fallback": False}, "s1": {"queries": ["마바는 무엇인가?"], "attempts": 1, "errors": [], "fallback": True}}, "stops": []}
    saved = {name: row["queries"] for name, row in decomposed["rows"].items()}
    ko_runs(report, tmp_path / "out.json", cases, retriever, ConstantReranker(), gates, saved, None)
    ko_report(report, cases, ko_documents(rows), decomposed, tmp_path / "claude", tmp_path / "jev")
    group = f"multidocQA/{KO_NAMED_TWO}"
    assert report["summary"]["gated_decompose"][group]["n"] == 1 and report["summary"]["title_mention"][group]["recall@10"] == 1.0
    assert report["comparisons"]["gated_vs_no"][group]["n"] == 1
    assert report["gate"]["by_task"]["multidocQA"]["rate"] == 1.0 and report["gate"]["by_task"]["singledocQA"]["rate"] == 0.0
    assert report["decomposition"] == {"rows": 2, "fallback_ids": ["s1"], "retried_ids": ["m1"], "failed_ids": [], "error_types": {"TimeoutError": 1}, "stops": []}
    assert report["spend"]["claude_calls"] == 1 and report["spend"]["jev_calls"] == 1
    written = json.dumps(report, ensure_ascii=False)
    for text in ("가나", "다라", "왕국", "마바", "세워진"):
        assert text not in written


def test_ko_chunk_vectors_resume_from_the_saved_part_and_stop_at_the_time_limit(tmp_path):
    documents = ko_documents([ko_row("a", "multidocQA", "q", "예", ("가", "하나"), ("나", "둘"), ("다", "셋"))])
    chunks = [chunk for document in documents.values() for chunk in page_chunks(document)]
    path = tmp_path / "v.npy"
    assert ko_chunk_vectors(chunks, HashEmbeddings(), path, 0) is None
    whole = ko_chunk_vectors(chunks, HashEmbeddings(), path, None)
    assert whole.shape == (3, 256)

    class Refuses:
        def embed_documents(self, texts):
            raise AssertionError("이미 저장한 조각을 다시 계산했다")

    assert (ko_chunk_vectors(chunks, Refuses(), path, None) == whole).all()


def test_ko_longrag_subcommand_rejects_an_unknown_step_and_a_missing_work_dir(monkeypatch):
    for arguments in (["ko-longrag", "--work-dir", "w", "--only", "없는단계"], ["ko-longrag"]):
        monkeypatch.setattr("sys.argv", ["measure.py", *arguments])
        with pytest.raises(SystemExit) as stopped:
            main()
        assert stopped.value.code == 2
