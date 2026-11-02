from day02.evaluation import evaluate_answer, summarize_answers


def test_existing_citation_id_does_not_imply_semantic_support():
    run = {"status": "answered", "validation": "passed",
           "answer": {"sections": [{"items": [{"text": "잘못된 결론", "evidence_ids": ["e1"]}]}]},
           "evidence": [{"evidence_id": "e1", "document_id": "d1", "quote": "원문"}]}
    result = evaluate_answer(run, {"expected_docs": ["d1"], "review_status": "draft"})
    assert result["citation_ids_valid"] is True
    assert result["claim_citation_coverage"] == 1
    assert result["semantic_quality"] is None
    assert result["evaluation_basis"] == "draft"


def test_retrieved_document_is_not_necessarily_cited():
    run = {"status": "answered", "answer": {"sections": [{"items": [{"evidence_ids": ["missing"]}]}]},
           "evidence": [{"evidence_id": "e1", "document_id": "d1"}]}
    result = evaluate_answer(run, {"expected_docs": ["d1"]})
    assert result["required_document_recall"] == 1
    assert result["cited_document_recall"] == 0
    assert result["citation_ids_valid"] is False


def test_failed_execution_is_not_abstention_or_zero_cost():
    run = {"status": "error"}
    evaluation = evaluate_answer(run, {"expected_docs": [], "abstain": True})
    row = {"run": run, "evaluation_eligible": True, "evaluation": evaluation}
    summary = summarize_answers([row])
    assert evaluation["observed_abstention"] is None
    assert summary["errors"] == 1
    assert summary["model_calls"] is None
    assert summary["judge_coverage"] == 0
    assert summary["judged_accuracy"] is None
