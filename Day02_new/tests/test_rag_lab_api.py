"""DESIGN.md의 공개 이름 계약과 구조 규칙."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "rag_lab"
PUBLIC_NAMES = {
    "settings": {"ROOT", "Settings", "load_settings", "key_status", "require_key", "announce", "UsageLog", "make_model",
                 "make_embeddings", "make_reranker", "append_usage"},
    "corpus": {"Scope", "Document", "Chunk", "load_corpus", "load_cases", "fixed_chunks", "section_chunks",
               "count_cut_tables"},
    "retrieval": {"tokenize", "content_terms", "BM25Index", "DenseIndex", "rrf", "fuse_scores", "Retriever",
                  "SAME_SOURCE_CORROBORATION_BONUS", "MAX_CORROBORATION_BONUS", "corroborate"},
    "evidence": {"BudgetExceeded", "Budget", "Evidence", "Sufficiency", "assess_sufficiency", "RetrievalContext",
                 "make_search_tools"},
    "answer": {"NUMBER_HINT", "Statement", "Section", "AnswerPayload", "SupportReview", "skill_spec",
               "validate_answer", "review_support", "render_answer"},
    "agent": {"ALLOWED_TOOLS", "SYSTEM_PROMPT", "TrackedSkillsBackend", "allowlist_middleware", "check_skill_folder",
              "build_rag_agent", "Session", "ask", "write_run_record"},
    "embeddings": {"LocalE5Embeddings"},
    "rerank": {"CrossEncoderReranker"},
    "pages": {"IMAGE_AREA_THRESHOLD", "MIN_TEXT_CHARS", "RENDER_DPI", "JPEG_QUALITY", "needs_reading", "read_page"},
    "pipeline": {"Reranker", "RetrievalRun", "decompose_question", "interleave", "retrieve", "fit_context"},
    "decisions": {"Noul", "Choice", "Score", "Question", "Verdict", "Judgment", "DecisionError", "DecisionBackend",
                  "TypeSafeBackend", "OpenRouterBackend", "OpenAIDecisionsBackend", "AzureOpenAIDecisionsBackend", "BACKENDS", "make_decider"},
    "gates": {"DECOMPOSE_THRESHOLD", "FOLLOWUP_THRESHOLD", "CITATION_RELEVANCE_FLOOR", "GateResult", "CitedChunk", "MeteredDecider",
              "needs_decomposition", "needs_follow_up", "irrelevant_citations", "answer_text", "cited_chunks", "strip_citations"},
    "phases": {"ask_two_phase"},
    "evaluation": {"load_gold", "evaluate_retrieval", "recall_by_type", "mrr"},
}


def defined_names(path: Path) -> set[str]:
    names = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, ast.AnnAssign):
            names.add(node.target.id)
    return {name for name in names if not name.startswith("_")}


def test_public_names_match_the_design():
    assert {module: defined_names(SOURCE / f"{module}.py") for module in PUBLIC_NAMES} == PUBLIC_NAMES


def test_offline_module_is_gone():
    assert not (SOURCE / "offline.py").exists()


def test_package_init_is_empty():
    assert (SOURCE / "__init__.py").read_text(encoding="utf-8") == ""


def test_modules_stay_readable_in_class():
    """설계의 150줄 상한. 코드 줄은 DESIGN.md의 측정 정의대로 빈 줄을 뺀 줄 수다."""
    sizes = {p.name: sum(bool(line.strip()) for line in p.read_text(encoding="utf-8").splitlines())
             for p in SOURCE.glob("*.py")}
    assert max(sizes.values()) <= 150, sizes


def test_only_evaluation_module_touches_the_answer_key():
    readers = [p.name for p in SOURCE.glob("*.py") if "gold" in p.read_text(encoding="utf-8")]
    assert readers == ["evaluation.py"]
