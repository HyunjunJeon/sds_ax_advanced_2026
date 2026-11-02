from common.evaluation import evaluate, summarize


def test_summary_reports_missing_judges_and_unknown_usage():
    def row(status, quality=None):
        return {"architecture": "baseline", "result": {"status": status}, "evaluation_eligible": True,
                "metrics": {"calls": {}, "elapsed_s": 1, "input_tokens": None, "output_tokens": None,
                            "usage_complete": False},
                "evaluation": {"semantic_quality": quality, "evaluation_basis": "draft"}}

    summary = summarize([row("complete", {"correct": True}), row("failed")])[0]
    assert summary["runs"] == 2 and summary["errors"] == 1
    assert summary["final_turns"] == 2 and summary["judged_final_turns"] == 1
    assert summary["judge_coverage"] == 0.5
    assert summary["mean_input_tokens"] is None
    assert summary["draft_evaluations"] == 2


def test_uncited_retrieval_is_not_citation_recall():
    result = {"status": "complete", "evidence": [{"evidence_id": "e1", "doc_id": "d1"}],
              "answer": {"claims": [{"text": "결론", "evidence_ids": ["unknown"]}]}}
    observation = evaluate(result, {"required_docs": ["d1"], "review_status": "draft"})
    assert observation["required_document_recall"] == 1
    assert observation["cited_document_recall"] == 0
    assert observation["claim_citation_coverage"] == 0
    assert observation["semantic_quality"] is None
