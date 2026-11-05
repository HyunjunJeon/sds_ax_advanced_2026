"""구현된 rag_lab을 부품별로 재는 저자 전용 도구. 수강생 노트북은 쓰지 않는다.

retrieval은 수업 문서(범위 필터 켬)와 올거나이즈 조정용 분할에서 hybrid, fusion, fusion_rerank를 잰다. 모델 API를 부르지 않는다.
answers는 data/cases.jsonl 12문항을 네 구성으로 실제 Claude와 Decision API에 물어 행마다 한 줄씩 남긴다. 유료다. 다시 실행하면 이미 있는 행은 건너뛴다.
실패한 행은 지우지 않고 id와 함께 모두 결과에 남긴다. 정답표는 측정 코드에서만 읽는다.
옛 jsonl의 two_phase_auto, two_phase_always는 Claude 게이트 시절의 행이다. 집계로 그대로 읽히지만 지금 코드로 다시 돌지 않는다.

    uv run --no-sync python Day02_new/benchmarks/measure.py retrieval
    uv run --no-sync python Day02_new/benchmarks/measure.py answers --usage-dir <사용량 폴더> [--cases ID ...] [--max-seconds N]
    uv run --no-sync python Day02_new/benchmarks/measure.py answers --usage-dir <새 폴더> --out <새 파일> --pair 구성:문항ID [--pair ...] --cap 0.50
    uv run --no-sync python Day02_new/benchmarks/measure.py jev --usage-dir <사용량 폴더> [--only gates tune class report] [--max-seconds N]

ksq-gated는 Ko-StrategyQA train 300문항(정답이 여러 개인 문항 포함)에서 분해 게이트를 잰다. Jev를 질문마다 한 번 부르고 Claude는 부르지 않는다. 읽는 분할은 train뿐이다.

    uv run --no-sync python Day02_new/benchmarks/measure.py ksq-gated --data-dir <ko-strategyqa 폴더> --vectors <e5_docs.npy> --usage-dir <사용량 폴더> [--max-seconds N]

ko-longrag는 Ko-LongRAG에서 분해 게이트를 잰다. 답할 수 있는 다문서 문항 전부와 단일 문서 150문항을 Claude로 분해하고(상한 --cap) Jev를 문항마다 한 번 부른다. 유료다.
라이선스(CC BY-NC 4.0, OpenAI 약관) 때문에 데이터는 git 제외 폴더에만 두고 결과에는 ID와 지표만 쓴다. pyarrow가 프로젝트 의존성이 아니라 --with로 넣는다.

    uv run --no-sync --with pyarrow python Day02_new/benchmarks/measure.py ko-longrag --work-dir <임시 폴더> [--only gates decompose runs report] [--cap 1.0] [--max-seconds N]

jev는 Jev 관문을 잰다. gates만 Jev를 부르고(질문마다 한 번) tune은 그 결정과 저장된 분해 질의를 읽어 Claude를 부르지 않는다. 다시 실행하면 끝난 단위는 건너뛴다.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import pickle
import random
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 직접 실행해도 rag_lab과 benchmarks를 찾게 한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))  # 비용은 tests/cost_report.py로만 계산한다.

from benchmarks.allganize import Case, Page, load_cases as load_allganize_cases, load_pages  # noqa: E402
from cost_report import read_rows, render  # noqa: E402
from rag_lab.agent import ask  # noqa: E402
from rag_lab.corpus import Chunk, Document, Scope, load_cases, load_corpus  # noqa: E402
from rag_lab.decisions import DecisionBackend, make_decider  # noqa: E402
from rag_lab.evaluation import load_gold  # noqa: E402
from rag_lab.gates import needs_decomposition  # noqa: E402
from rag_lab.phases import ask_two_phase  # noqa: E402
from rag_lab.pipeline import Reranker, decompose_question, retrieve  # noqa: E402
from rag_lab.retrieval import Retriever  # noqa: E402
from rag_lab.settings import ROOT, announce, load_settings, make_embeddings, make_model, make_reranker  # noqa: E402

DEFAULT_OUT = ROOT / "outputs/benchmarks/results/measure_retrieval.json"
VISION_PAGES = ROOT / "outputs/benchmarks/allganize/vision_pages.json"
CLASS_SETS = [("basic", "cases.jsonl", "gold.jsonl"), ("hard", "cases_hard.jsonl", "gold_hard.jsonl"),
              ("hard2", "cases_hard2.jsonl", "gold_hard2.jsonl")]
TUNE_SPLIT = "tune"  # 이 도구는 조정용 분할만 읽는다.
CLASS_CONFIGS = ("hybrid", "fusion", "fusion_rerank")
POOL = 50  # docs/retrieval_benchmarks.md의 재순위 후보 수
CHUNK_SIZE, CHUNK_OVERLAP = 800, 100  # docs/retrieval_benchmarks.md의 공통 조각
ANSWERS_OUT = ROOT / "outputs/benchmarks/results/measure_answers.jsonl"
COST_CAP_USD = 2.00  # 저자가 고지한 지출 상한
CALLS_PER_ROW = 5  # 고지용 어림값. 실제 호출 수는 행의 model_calls에 남는다.
FILE_SOURCE_OUT = ROOT / "outputs/benchmarks/results/measure_corroboration_file.json"
KSQ_OUT = ROOT / "outputs/benchmarks/results/measure_ksq_gated.json"
KSQ_SUBQUERIES = ROOT / "outputs/benchmarks/results/decomposed.json"  # 앞선 벤치마크가 Ko-StrategyQA train 300문항에서 만든 분해 질의
KSQ_SAMPLE, KSQ_RECALL_DEPTH = 300, 100
JEV_OUT = ROOT / "outputs/benchmarks/results/measure_jev.json"
JEV_ANSWERS = ROOT / "outputs/benchmarks/results/measure_answers_3.jsonl"
EARLIER_ANSWERS = (ANSWERS_OUT, ROOT / "outputs/benchmarks/results/measure_answers_2.jsonl")
SAVED_SUBQUERIES = ROOT / "outputs/benchmarks/allganize/decomposed_allganize_tune.json"  # 앞선 벤치마크가 조정용 분할에서 만든 분해 질의
BOOTSTRAP_ROUNDS, BOOTSTRAP_SEED = 10_000, 20261101
_EXCEPTION_ERROR = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*: ")  # ask와 ask_two_phase가 예외를 "타입: 내용"으로 적는다. 검증 오류는 한국어로 시작한다.


# ---- 지표 (순수 함수) ----

def first_rank(ranked: list[str], relevant: set[str] | list[str]) -> int | None:
    """relevant 중 하나가 처음 나온 순위(1부터). 없으면 None."""
    return next((rank for rank, item in enumerate(ranked, 1) if item in relevant), None)


def reciprocal_rank(ranked: list[str], relevant: set[str] | list[str], depth: int) -> float:
    """상위 depth개 안의 첫 정답 순위의 역수. depth 밖이거나 없으면 0이다."""
    rank = first_rank(ranked, relevant)
    return 1 / rank if rank is not None and rank <= depth else 0.0


def doc_recall(ranked: list[str], expected: list[str], k: int) -> float:
    """기대 문서 중 상위 k개 안에 든 비율."""
    return len(set(expected) & set(ranked[:k])) / len(expected)


def hit_at(ranked: list[str], target: str, k: int) -> int:
    return int(target in ranked[:k])


def split_by_scope(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(기대 문서가 모두 범위 안인 행, 하나라도 범위 밖인 행). 기대 문서가 없는 행은 어느 쪽에도 넣지 않는다."""
    scored = [row for row in rows if row["expected"]]
    return [r for r in scored if r["in_scope"]], [r for r in scored if not r["in_scope"]]


def tune_cases(cases: list[Case]) -> list[Case]:
    return [case for case in cases if case.split == TUNE_SPLIT]


def summarize_docs(rows: list[dict]) -> dict:
    """recall@1,2,3와 MRR@3의 평균. 기대 문서가 없는 행은 제외하고 센 행 수를 n에 적는다."""
    scored = [row for row in rows if row["expected"]]
    if not scored:
        return {"n": 0}
    n = len(scored)
    summary = {f"recall@{k}": round(sum(doc_recall(r["ranked"], r["expected"], k) for r in scored) / n, 4) for k in (1, 2, 3)}
    summary["mrr@3"] = round(sum(reciprocal_rank(r["ranked"], r["expected"], 3) for r in scored) / n, 4)
    return summary | {"n": n}


def summarize_pages(rows: list[dict]) -> dict:
    """page hit@1,3,5,10, MRR@10, 문맥 유형별 hit@5. 못 찾은 행은 0으로 센다."""
    n = len(rows)
    summary = {f"hit@{k}": round(sum(hit_at(r["ranked"], r["target"], k) for r in rows) / n, 4) for k in (1, 3, 5, 10)}
    summary["mrr@10"] = round(sum(reciprocal_rank(r["ranked"], [r["target"]], 10) for r in rows) / n, 4)
    by_type = defaultdict(list)
    for row in rows:
        by_type[row["context_type"]].append(hit_at(row["ranked"], row["target"], 5))
    summary["hit@5_by_context_type"] = {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_type.items())}
    return summary | {"n": n}


def row_key(row: dict) -> tuple[float, float]:
    """행 하나의 품질. recall@3가 먼저, 같으면 첫 정답의 역순위(상위 3개)."""
    return doc_recall(row["ranked"], row["expected"], 3), reciprocal_rank(row["ranked"], row["expected"], 3)


# ---- 수업 문서 ----

def doc_ranking(retriever: Retriever, chunk_ids: list[str]) -> list[str]:
    return list(dict.fromkeys(retriever.chunks[chunk_id].doc_id for chunk_id in chunk_ids))


def class_rows() -> list[dict]:
    documents = load_corpus()
    rows = []
    for name, case_file, gold_file in CLASS_SETS:
        gold = load_gold(ROOT / "data" / gold_file)
        for case in load_cases(ROOT / "data" / case_file):
            scope = Scope(case["entity"], date.fromisoformat(case["as_of"]))
            expected = gold[case["id"]]["expected_docs"]
            rows.append({"set": name, "id": case["id"], "type": case["type"], "question": case["question"],
                         "scope": scope, "expected": expected,
                         "in_scope": all(documents[d].applies(scope) for d in expected),
                         "draft": gold[case["id"]].get("review_status") == "draft"})
    return rows


def timed(action: Callable[[], list[str]]) -> tuple[list[str], float, float]:
    """(결과, CPU 초, 벽시계 초). CPU 초는 프로세스 전체라 torch 스레드 합이 들어간다."""
    cpu, wall = time.process_time(), time.perf_counter()
    result = action()
    return result, time.process_time() - cpu, time.perf_counter() - wall


def public_class_row(row: dict) -> dict:
    return {"id": row["id"], "set": row["set"], "type": row["type"], "expected": row["expected"], "top3": row["ranked"][:3],
            "in_scope": row["in_scope"], "draft": row["draft"]}


def class_summary(measured: list[dict]) -> dict:
    """전체, 범위 안, 범위 밖 행과 r@3가 1 미만인 행."""
    inside, outside = split_by_scope(measured)
    return {"all": summarize_docs(measured), "in_scope": summarize_docs(inside),
            "out_of_scope": {"n": len(outside), "rows": [public_class_row(r) for r in outside]},
            "failing_rows": [public_class_row(r) for r in measured if r["expected"] and doc_recall(r["ranked"], r["expected"], 3) < 1]}


def measure_class() -> dict:
    documents = load_corpus()
    hybrid = Retriever(documents, embeddings=make_embeddings(), mode="hybrid")
    fusion = copy.copy(hybrid)  # 같은 색인을 공유한다. 임베딩을 두 번 계산하지 않으려는 것이고 rank는 mode만 본다.
    fusion.mode = "fusion"
    reranker = make_reranker()
    everything = len(hybrid.chunks)
    runners = {
        "hybrid": lambda r: hybrid.rank(r["question"], r["scope"], limit=everything),
        "fusion": lambda r: fusion.rank(r["question"], r["scope"], limit=everything),
        "fusion_rerank": lambda r: retrieve(r["question"], retriever=fusion, scope=r["scope"], reranker=reranker,
                                           pool=POOL, top_n=POOL).chunk_ids,
    }
    rows = class_rows()
    per_config: dict[str, list[dict]] = {}
    seconds = {}
    for config, run in runners.items():
        measured, cpu_total, wall_total = [], 0.0, 0.0
        for row in rows:
            chunk_ids, cpu, wall = timed(lambda: run(row))
            cpu_total, wall_total = cpu_total + cpu, wall_total + wall
            measured.append(row | {"ranked": doc_ranking(hybrid, chunk_ids)})
        per_config[config] = measured
        seconds[config] = {"cpu_per_question": round(cpu_total / len(rows), 3), "wall_per_question": round(wall_total / len(rows), 3)}
        print(f"class {config} done", flush=True)

    result: dict = {"chunks": everything, "questions": len(rows), "pool": POOL, "seconds": seconds,
                    "draft_gold_rows": sum(r["draft"] for r in rows),
                    "draft_note": "정답표의 review_status가 draft인 행을 draft: true로 표시했다.",
                    "no_expected_docs": [r["id"] for r in rows if not r["expected"]],
                    "out_of_scope_ids": [r["id"] for r in split_by_scope(per_config["hybrid"])[1]],
                    "configs": {}, "vs_hybrid": {}}
    for config, measured in per_config.items():
        result["configs"][config] = class_summary(measured)
    base = {r["id"]: r for r in per_config["hybrid"]}
    for config in ("fusion", "fusion_rerank"):
        worse, better = [], []
        for row in per_config[config]:
            if not row["expected"]:
                continue
            old, new = row_key(base[row["id"]]), row_key(row)
            entry = {"id": row["id"], "expected": row["expected"], "hybrid_top3": base[row["id"]]["ranked"][:3],
                     "top3": row["ranked"][:3], "in_scope": row["in_scope"]}
            (worse if new < old else better if new > old else []).append(entry)
        result["vs_hybrid"][config] = {"worse": worse, "better": better}
    return result


# ---- 올거나이즈 조정용 분할 ----

def page_documents(pages: list[Page], reading: dict[str, str] | None) -> dict[str, Document]:
    """페이지 하나를 문서 하나로 만든다. reading이 있으면 글자층 뒤에 판독 글자를 덧붙인다. 공백 연속은 하나로 줄인다."""
    documents = {}
    for page in pages:
        extra = (reading or {}).get(f"{page.file}#{page.page_no}")
        text = re.sub(r"[ \t]+", " ", page.text if extra is None else page.text + "\n" + extra)
        doc_id = f"{page.file}#{page.page_no}"
        documents[doc_id] = Document(doc_id=doc_id, title=page.file, source=page.file, domain="", entity="공통", version="",
                                     valid_from=date.min, valid_until=None, status="approved", owner="", family=None, text=text)
    return documents


def page_chunks(doc: Document) -> list[Chunk]:
    """800자, 겹침 100으로 자르고 파일 이름(.pdf 제외)을 조각 앞에 붙인다. 공백뿐인 조각은 버린다."""
    prefix = re.sub(r"\.pdf$", "", doc.title) + "\n"
    chunks = []
    for start in range(0, max(1, len(doc.text)), CHUNK_SIZE - CHUNK_OVERLAP):
        part = doc.text[start:start + CHUNK_SIZE]
        if part.strip():
            line = doc.text.count("\n", 0, start) + 1
            chunks.append(Chunk(f"{doc.doc_id}#{len(chunks)}", doc.doc_id, "", prefix + part, start, start + len(part),
                                line, line + part.count("\n")))
        if start + CHUNK_SIZE >= len(doc.text):
            break
    return chunks


def pick_device() -> str:
    import torch  # 저자 전용 도구라 쓸 수 있는 가속기를 쓴다. 수업 기본(cpu)과 다르다.
    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


def measure_tune() -> dict:
    from rag_lab.embeddings import LocalE5Embeddings
    from rag_lab.rerank import CrossEncoderReranker

    settings, device = load_settings(), pick_device()
    embeddings = LocalE5Embeddings(settings.embedding_model, device=device)
    reranker = CrossEncoderReranker(settings.rerank_model, device=device)
    cases = tune_cases(load_allganize_cases()[0])
    pages = load_pages()
    reading = json.loads(VISION_PAGES.read_text(encoding="utf-8"))
    result: dict = {"device": device, "cases": len(cases), "pages": len(pages), "pool": POOL,
                    "chunker": f"{CHUNK_SIZE}자, 겹침 {CHUNK_OVERLAP}, 파일 이름 접두", "configs": {}, "seconds": {}}
    for label, texts in (("text", None), ("page_reading", reading)):
        hybrid = Retriever(page_documents(pages, texts), chunker=page_chunks, embeddings=embeddings, mode="hybrid")
        fusion = copy.copy(hybrid)  # 같은 색인 공유
        fusion.mode = "fusion"
        everything = len(hybrid.chunks)
        runners = {
            f"fusion_rerank_{label}": lambda c: retrieve(c.question, retriever=fusion, scope=None, reranker=reranker,
                                                        pool=POOL, top_n=POOL).chunk_ids,
        }
        if texts is None:
            runners = {"hybrid_text": lambda c: hybrid.rank(c.question, None, limit=everything)} | runners
        for config, run in runners.items():
            rows, cpu_total, wall_total = [], 0.0, 0.0
            for case in cases:
                chunk_ids, cpu, wall = timed(lambda: run(case))
                cpu_total, wall_total = cpu_total + cpu, wall_total + wall
                rows.append({"target": f"{case.file}#{case.page_no}", "context_type": case.context_type,
                             "ranked": doc_ranking(hybrid, chunk_ids)})
            result["configs"][config] = summarize_pages(rows) | {"chunks": everything}
            result["seconds"][config] = {"cpu_per_question": round(cpu_total / len(cases), 3),
                                         "wall_per_question": round(wall_total / len(cases), 3)}
            print("tune", config, result["configs"][config], flush=True)
    return result


# ---- 답변 측정 (유료) ----

def is_decision_usage(row: dict) -> bool:
    """Jev 호출 줄인가. Jev는 비용도 단가도 알려 주지 않아 Claude 지출과 따로 센다. 다른 미지의 모델은 그대로 지출 검사에 걸린다."""
    return "jev-" in row["model"]


def outcome(record: dict) -> str:
    """passed는 답이 나간 행(answered, insufficient), errored는 예외로 끝난 행, validation_failed는 검증을 끝내 통과하지 못한 행."""
    if record["status"] != "error":
        return "passed"
    return "errored" if any(_EXCEPTION_ERROR.match(error) for error in record["errors"]) else "validation_failed"


def cited_doc_ids(answer: dict | None, evidence: list[dict]) -> list[str]:
    documents = {item["evidence_id"]: item["doc_id"] for item in evidence}
    cited = {documents[reference] for section in (answer or {}).get("sections", []) for statement in section["items"]
             for reference in statement["evidence_ids"] if reference in documents}
    return sorted(cited)


def covers(expected: list[str], found: list[str]) -> bool | None:
    """기대 문서가 없는 문항은 판단할 수 없으므로 None이다. True로 두면 빈 조건이 성공으로 읽힌다."""
    return set(expected) <= set(found) if expected else None


def answer_row(config: str, case: dict, record: dict, gold: dict, usage: list[dict], seconds: float) -> dict:
    """실행 기록과 사용량 행을 결과 한 줄로 만든다. ask 기록에는 게이트와 검증 단계가 없어 None으로 남는다."""
    released = record["answer"] if record["status"] != "error" else None  # 내보내지 않은 답의 인용은 인용으로 세지 않는다.
    cited = cited_doc_ids(released, record["evidence"])
    retrieved = sorted({item["doc_id"] for item in record["evidence"]})
    counts, events = record["trace"]["counts"], record["trace"]["events"]
    jev = [row for row in usage if is_decision_usage(row)]
    usage = [row for row in usage if not is_decision_usage(row)]
    costs = [row["cost"] for row in usage]
    jev_costs = [row["cost"] for row in jev]
    fast_phase = next((phase for phase in record.get("phases", []) if phase["name"] == "fast"), None)
    gates = record.get("gates", [])
    return {
        "config": config, "case_id": case["id"], "type": case["type"], "run_id": record["run_id"], "outcome": outcome(record),
        "status": record["status"], "validation": record["validation"], "errors": record["errors"],
        "verification": record.get("verification"), "gate_confidence": next((gate["probability"] for gate in gates if gate["gate"] == "follow_up"), None),
        "decision_backend": gates[0]["backend"] if gates else None, "decision_model": next((gate["model"] for gate in gates if gate["model"]), None),
        "decision_calls": counts.get("decision", 0), "citations_removed": len(record.get("citations_removed", [])),
        "diagnostics": record.get("diagnostics", []),
        "model_calls": counts.get("model", 0), "usage_calls": sum(row["calls"] for row in usage), "searches": counts.get("search", 0),
        "reads": counts.get("read", 0), "tool_calls": counts.get("tool", 0),
        "retrieval_warnings": [event["warning"] for event in events if event["event"] == "retrieval_warning"],
        "context_excluded": sum(event["event"] == "context_excluded" for event in events),
        "cited_doc_ids": cited, "retrieved_doc_ids": retrieved, "expected_docs": gold["expected_docs"], "abstain_expected": gold["abstain"],
        "expected_cited": covers(gold["expected_docs"], cited), "expected_retrieved": covers(gold["expected_docs"], retrieved),
        "fast_errors": fast_phase["errors"] if fast_phase else None,
        "fast_cited_doc_ids": cited_doc_ids(record.get("fast_answer"), record["evidence"]) if fast_phase else None,
        "seconds": round(seconds, 3), "input_tokens": sum(row["input"] for row in usage), "output_tokens": sum(row["output"] for row in usage),
        "cache_read_tokens": sum(row["cached"] for row in usage), "cache_write_tokens": sum(row["written"] for row in usage),
        "cost": None if None in costs else sum(costs),
        "gates": gates, "queries": record.get("queries"), "citations_removed_detail": record.get("citations_removed", []),
        "jev_calls": sum(row["calls"] for row in jev), "jev_input_tokens": sum(row["input"] for row in jev), "jev_output_tokens": sum(row["output"] for row in jev),
        "jev_cost": None if None in jev_costs else sum(jev_costs),
    }


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def done_pairs(path: Path) -> set[tuple[str, str]]:
    return {(row["config"], row["case_id"]) for row in read_lines(path) if "config" in row}


def _append(path: Path, line: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as output:
        output.write(json.dumps(line, ensure_ascii=False) + "\n")


def _spending_stop(usage_dir: Path, cap: float, reserve: float = 0.0) -> tuple[str, float] | None:
    """사용량 폴더 전체로 지출을 잰다. 결과 줄을 지웠거나 행 도중 프로세스가 죽어도 쓴 돈은 여기 남는다.

    reserve는 다음 행 하나가 쓸 만한 돈이다. 지출에 더해 상한을 넘을 것 같으면 그 행을 시작하지 않는다."""
    rows = [row for row in read_rows(usage_dir) if not is_decision_usage(row)]
    spent = sum(row["cost"] or 0 for row in rows)
    if any(row["cost"] is None for row in rows):
        return "unpriced_usage", spent
    return ("cost_cap", spent) if spent + reserve >= cap else None


def run_answers(cases: list[dict], runners: dict[str, Callable[[dict], dict]], gold: dict[str, dict], out: Path, usage_dir: Path,
                *, cap: float = COST_CAP_USD, max_seconds: float | None = None, pairs: set[tuple[str, str]] | None = None) -> str:
    """문항 순서로 구성마다 한 번씩 돈다. 중간에 멈춰도 구성끼리 같은 문항을 비교하게 하려는 순서다. 멈춘 이유를 돌려준다.

    max_seconds는 이번 호출의 시간이다. 넘으면 다음 행을 시작하지 않고, 다시 실행하면 이어서 돈다.
    pairs가 있으면 (구성, 문항 ID)가 그 안에 든 행만 돈다.
    """
    usage_dir.mkdir(parents=True, exist_ok=True)
    done, started = done_pairs(out), time.monotonic()
    for case in cases:
        for config, run in runners.items():
            if (config, case["id"]) in done or (pairs is not None and (config, case["id"]) not in pairs):
                continue
            reserve = max((r["cost"] or 0 for r in read_lines(out) if "config" in r), default=0.0)  # 지금까지 가장 비싼 행
            stop = _spending_stop(usage_dir, cap, reserve)
            if stop:
                _append(out, {"event": "stopped", "reason": stop[0], "spent": stop[1], "next": [config, case["id"]]})
                return stop[0]
            if max_seconds is not None and time.monotonic() - started >= max_seconds:
                return "time_limit"
            stem = f"{config}__{case['id']}__{uuid4().hex[:8]}"
            os.environ["DAY02_USAGE_LOG"] = str(usage_dir / f"{stem}.usage.jsonl")
            try:
                row_started = time.monotonic()
                record = run(case)
                seconds = time.monotonic() - row_started
            finally:
                del os.environ["DAY02_USAGE_LOG"]
            usage = [row for row in read_rows(usage_dir) if row["notebook"] == stem]
            row = answer_row(config, case, record, gold[case["id"]], usage, seconds)
            _append(out, row)
            print(config, case["id"], row["outcome"], row["status"], f"호출 {row['model_calls']}", f"{row['seconds']:.0f}초", f"${row['cost']}", flush=True)
    return "finished"


def summarize_answers(rows: list[dict]) -> dict[str, dict]:
    """구성별 집계. 가격을 모르는 행의 비용은 합에 넣지 않고 unpriced_rows로 드러낸다."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if "config" in row:
            grouped[row["config"]].append(row)
    summary = {}
    for config, members in grouped.items():
        n = len(members)
        results = [member["outcome"] for member in members]
        summary[config] = {"rows": n, "passed": results.count("passed"), "errored": results.count("errored"),
                           "validation_failed": results.count("validation_failed"),
                           "verification_ran": sum(member["verification"] == "ran" for member in members),
                           "mean_model_calls": sum(member["model_calls"] for member in members) / n,
                           "mean_seconds": sum(member["seconds"] for member in members) / n,
                           "cost": sum(member["cost"] or 0 for member in members),
                           "unpriced_rows": sum(member["cost"] is None for member in members)}
    return summary


def case_scope(case: dict) -> Scope:
    return Scope(case["entity"], date.fromisoformat(case["as_of"]))


def two_phase_runners(retriever: Retriever, model: BaseChatModel, reranker: Reranker | None,
                      decider: DecisionBackend) -> dict[str, Callable[[dict], dict]]:
    """분해 게이트를 켠 구성과 끈 구성. 둘 다 verify="auto"다."""
    def two_phase(decompose: bool) -> Callable[[dict], dict]:
        return lambda case: ask_two_phase(case["question"], retriever=retriever, scope=case_scope(case), model=model, decider=decider,
                                          reranker=reranker, decompose=decompose, verify="auto")

    return {"two_phase_jev": two_phase(True), "two_phase_jev_no_decompose": two_phase(False)}


def answer_runners() -> dict[str, Callable[[dict], dict]]:
    """네 구성. budget을 넘기지 않아 행마다 기본 Budget을 쓴다. Decision API 키가 없으면 make_decider에서 멈춘다."""
    hybrid = Retriever(load_corpus(), embeddings=make_embeddings(), mode="hybrid")
    fusion = copy.copy(hybrid)  # 같은 색인 공유
    fusion.mode = "fusion"
    reranker, model = make_reranker(), make_model()

    return {
        "ask_hybrid": lambda case: ask(case["question"], retriever=hybrid, scope=case_scope(case), model=model),
        "ask_fusion_rerank": lambda case: ask(case["question"], retriever=fusion, scope=case_scope(case), model=model, reranker=reranker),
        **two_phase_runners(fusion, model, reranker, make_decider()),
    }


def parse_pair(text: str) -> tuple[str, str]:
    """'구성:문항ID'를 (구성, 문항ID)로 나눈다. 구성 이름에는 ':'가 없다."""
    config, separator, case_id = text.partition(":")
    if not (config and separator and case_id):
        raise argparse.ArgumentTypeError(f"구성:문항ID 형식이어야 합니다: {text}")
    return config, case_id


def measure_answers(case_ids: list[str] | None, out: Path, usage_dir: Path, max_seconds: float | None, *,
                    pairs: set[tuple[str, str]] | None = None, cap: float = COST_CAP_USD,
                    runners: dict[str, Callable[[dict], dict]] | None = None) -> None:
    runners = runners or answer_runners()
    unknown = sorted({config for config, _ in pairs or set()} - set(runners))
    if unknown:
        raise SystemExit(f"알 수 없는 구성: {unknown}. 가능한 구성: {sorted(runners)}")
    cases = [case for case in load_cases(ROOT / "data/cases.jsonl")
             if (case_ids is None or case["id"] in case_ids) and (pairs is None or case["id"] in {c for _, c in pairs})]
    done = done_pairs(out)
    pending = sum((config, case["id"]) not in done and (pairs is None or (config, case["id"]) in pairs)
                  for case in cases for config in runners)
    announce("measure answers", model_calls=pending * CALLS_PER_ROW)
    print("멈춘 이유:", run_answers(cases, runners, load_gold(ROOT / "data/gold.jsonl"), out, usage_dir,
                                 cap=cap, max_seconds=max_seconds, pairs=pairs))
    summary = summarize_answers(read_lines(out))
    if not summary:
        print("기록된 행이 없습니다:", out)
    for config, body in summary.items():
        print(config, body)
    print(render(read_rows(usage_dir)))


# ---- Jev 관문 측정 ----

def paired_bootstrap(differences: list[float], *, rounds: int = BOOTSTRAP_ROUNDS, seed: int = BOOTSTRAP_SEED) -> dict:
    """문항별 차이를 문항 단위로 복원 추출해 평균의 95% 백분위 구간을 낸다."""
    if not differences:
        raise ValueError("비교할 문항이 없습니다.")
    values = np.asarray(differences, dtype=float)
    picks = np.random.default_rng(seed).integers(0, len(values), (rounds, len(values)))
    low, high = np.percentile(values[picks].mean(axis=1), [2.5, 97.5])
    return {"mean": float(values.mean()), "low": float(low), "high": float(high), "rounds": rounds, "seed": seed}


def gate_summary(rows: list[dict]) -> dict:
    """열린 비율과 확률 분포. 판단 없이 기본값을 쓴 행은 분포에서 빼고 ID로 드러낸다."""
    probabilities = [row["probability"] for row in rows if row["probability"] is not None]
    fired = sum(row["decision"] for row in rows)
    bins = {f"0.{tenth}-{'1.0' if tenth == 9 else f'0.{tenth + 1}'}": 0 for tenth in range(10)}
    for probability in probabilities:
        bins[list(bins)[min(int(probability * 10), 9)]] += 1
    stats = dict(zip(("min", "q25", "median", "q75", "max"), map(float, np.quantile(probabilities, [0, .25, .5, .75, 1])), strict=True)) if probabilities else {}
    return {"n": len(rows), "fired": fired, "rate": fired / len(rows), "probability": stats, "bins": bins,
            "fallback_ids": [row["id"] for row in rows if row["fallback"]]}


def plan_queries(decomposition: str, case_id: str, gates: dict[str, dict], saved: dict[str, list[str]]) -> list[str] | None:
    """구성별로 쓸 분해 질의. None이면 원 질문 하나로 검색한다. 판단이 실패한 게이트의 decision은 False다."""
    if decomposition == "always_decompose" or (decomposition == "gated_decompose" and gates[case_id]["decision"]):
        return saved[case_id]
    return None


class FailingReranker:
    """재순위 실패를 만든다. retrieve가 합친 순서를 유지하므로 합친 순서만 남은 상태를 잴 수 있다."""
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("측정용 재순위 실패")


class MemoReranker:
    """구성마다 같은 (질문, 조각)을 다시 계산하지 않는다. 재순위는 원 질문으로만 하므로 구성 사이에 점수가 같다."""
    def __init__(self, reranker: Reranker) -> None:
        self.reranker, self.scores = reranker, {}

    def score(self, query: str, texts: list[str]) -> list[float]:
        missing = [text for text in dict.fromkeys(texts) if (query, text) not in self.scores]
        if missing:
            self.scores.update(zip(((query, text) for text in missing), self.reranker.score(query, missing), strict=True))
        return [self.scores[query, text] for text in texts]


class TuneRun(NamedTuple):
    decomposition: str
    corroboration: bool
    rerank_fails: bool

    @property
    def name(self) -> str:
        return f"{self.decomposition}__corroboration_{'on' if self.corroboration else 'off'}{'__rerank_failed' if self.rerank_fails else ''}"


TUNE_RUNS = (TuneRun("no_decompose", True, False), TuneRun("gated_decompose", True, False), TuneRun("always_decompose", True, False),
             TuneRun("no_decompose", False, False), TuneRun("gated_decompose", False, False),
             TuneRun("no_decompose", True, True), TuneRun("no_decompose", False, True),
             TuneRun("gated_decompose", True, True), TuneRun("gated_decompose", False, True))
DECOMPOSITION_PAIRS = (("gated_vs_no__corroboration_on", TUNE_RUNS[0], TUNE_RUNS[1]), ("always_vs_no__corroboration_on", TUNE_RUNS[0], TUNE_RUNS[2]),
                       ("gated_vs_no__corroboration_off", TUNE_RUNS[3], TUNE_RUNS[4]), ("gated_vs_no__rerank_failed_corroboration_on", TUNE_RUNS[5], TUNE_RUNS[7]))
CORROBORATION_PAIRS = (("no_decompose", TUNE_RUNS[3], TUNE_RUNS[0]), ("gated_decompose", TUNE_RUNS[4], TUNE_RUNS[1]))
RERANK_FAILED_PAIRS = (("no_decompose", TUNE_RUNS[6], TUNE_RUNS[5]), ("gated_decompose", TUNE_RUNS[8], TUNE_RUNS[7]))


def compare_pages(base: list[dict], other: list[dict]) -> dict:
    """other − base를 문항별로 짝지어 비교한다. 정답 페이지의 순위가 바뀐 행은 모두 이름을 남긴다."""
    by_id = {row["id"]: row for row in base}
    mrr, hits, better, worse, reordered = [], [], [], [], 0
    for row in other:
        old, target = by_id[row["id"]], [row["target"]]
        mrr.append(reciprocal_rank(row["ranked"], target, 10) - reciprocal_rank(old["ranked"], target, 10))
        hits.append(hit_at(row["ranked"], row["target"], 5) - hit_at(old["ranked"], row["target"], 5))
        reordered += row["ranked"] != old["ranked"]
        old_rank, new_rank = first_rank(old["ranked"], target), first_rank(row["ranked"], target)
        if old_rank != new_rank:
            entry = {"id": row["id"], "context_type": row["context_type"], "base_rank": old_rank, "rank": new_rank}
            found_earlier = new_rank is not None and (old_rank is None or new_rank < old_rank)
            (better if found_earlier else worse).append(entry)
    return {"n": len(other), "mrr@10": paired_bootstrap(mrr), "hit@5": paired_bootstrap(hits), "ranking_changed": reordered,
            "better": better, "worse": worse}


def follow_up_pairs(rows: list[dict]) -> list[dict]:
    """행마다 (추가 확인 확률, 빠른 답변의 검증 실패). 게이트가 돌지 않았거나 판단이 없던 행도 None으로 남긴다."""
    pairs = []
    for row in rows:
        if "config" not in row:
            continue
        gate = next((gate for gate in row["gates"] if gate["gate"] == "follow_up"), {})
        pairs.append({"config": row["config"], "case_id": row["case_id"], "probability": gate.get("probability"),
                      "fast_failed": bool(row["fast_errors"]), "fallback": gate.get("fallback"), "verification": row["verification"]})
    return pairs


def _save(out: Path, report: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def jev_gates(report: dict, out: Path, usage_dir: Path) -> None:
    """분해 게이트를 질문마다 한 번 묻는다. tune 단계가 이 결정을 읽어 Jev를 다시 부르지 않는다."""
    groups = {"allganize_tune": [(case.case_id, case.question) for case in tune_cases(load_allganize_cases()[0])],
              "class_corpus": [(row["id"], row["question"]) for row in class_rows()]}
    pending = [name for name in groups if name not in report.setdefault("decomposition_gate", {})]
    announce("Jev 분해 게이트(Claude 호출 없음, Jev 호출은 질문마다 1회)", model_calls=sum(len(groups[name]) for name in pending))
    decider = make_decider()
    usage_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DAY02_USAGE_LOG"] = str(usage_dir / "jev_gates.usage.jsonl")
    try:
        for name in pending:
            rows = []
            for case_id, question in groups[name]:
                gate = needs_decomposition(decider, question)
                rows.append({"id": case_id, "probability": gate.probability, "decision": gate.decision, "fallback": gate.fallback,
                             "reason": gate.reason, "model": gate.model})
            report["decomposition_gate"][name] = gate_summary(rows) | {"rows": rows}
            _save(out, report)
            print(name, {k: v for k, v in report["decomposition_gate"][name].items() if k != "rows"}, flush=True)
    finally:
        del os.environ["DAY02_USAGE_LOG"]


def jev_tune(report: dict, out: Path, max_seconds: float | None) -> str:
    """구성 하나가 끝날 때마다 저장한다. 시간을 넘기면 다음 구성을 시작하지 않고 다시 실행하면 이어서 돈다."""
    from rag_lab.embeddings import LocalE5Embeddings
    from rag_lab.rerank import CrossEncoderReranker

    finished = report.setdefault("tune_runs", {})
    if all(run.name in finished for run in TUNE_RUNS):
        return "finished"
    settings, device, started = load_settings(), pick_device(), time.monotonic()
    gates = {row["id"]: row for row in report["decomposition_gate"]["allganize_tune"]["rows"]}
    saved = json.loads(SAVED_SUBQUERIES.read_text(encoding="utf-8"))
    cases = tune_cases(load_allganize_cases()[0])
    reading = json.loads(VISION_PAGES.read_text(encoding="utf-8"))
    retriever = Retriever(page_documents(load_pages(), reading), chunker=page_chunks, mode="fusion",
                          embeddings=LocalE5Embeddings(settings.embedding_model, device=device))
    reranker = MemoReranker(CrossEncoderReranker(settings.rerank_model, device=device))
    report["tune_setup"] = {"device": device, "cases": len(cases), "chunks": len(retriever.chunks), "pool": POOL, "text": "page_reading"}
    for run in TUNE_RUNS:
        if run.name in finished:
            continue
        if max_seconds is not None and time.monotonic() - started >= max_seconds:
            return "time_limit"
        view = copy.copy(retriever)  # 같은 색인 공유
        view.corroboration = run.corroboration
        rows = []
        for case in cases:
            found = retrieve(case.question, retriever=view, scope=None, reranker=FailingReranker() if run.rerank_fails else reranker,
                             queries=plan_queries(run.decomposition, case.case_id, gates, saved), pool=POOL, top_n=POOL)
            rows.append({"id": case.case_id, "target": f"{case.file}#{case.page_no}", "context_type": case.context_type,
                         "ranked": doc_ranking(retriever, found.chunk_ids), "queries": len(found.queries), "warnings": found.warnings})
        finished[run.name] = rows
        _save(out, report)
        print(run.name, summarize_pages(rows), f"{time.monotonic() - started:.0f}초", flush=True)
    return "finished"


def file_source_view(retriever: Retriever) -> Retriever:
    """출처를 파일로 보는 검색기. 조각의 doc_id만 파일 이름으로 바꿔 Retriever.rank의 출처 보강도가 같은 파일의 쪽들을 한 출처로 센다.
    조각 ID와 본문은 그대로라 색인과 재순위는 같고, 순위를 쪽으로 되돌리는 doc_ranking은 원래 검색기로 한다."""
    view = copy.copy(retriever)
    view.chunks = {chunk_id: replace(chunk, doc_id=retriever.documents[chunk.doc_id].source) for chunk_id, chunk in retriever.chunks.items()}
    return view


def corroboration_file_runs(retriever: Retriever, reranker: Reranker, cases: list[Case]) -> dict[str, list[dict]]:
    """분해 없이 보강도 끔, 쪽 출처, 파일 출처를 재순위 정상·실패로 잰 여섯 구성의 행."""
    page_view, file_view, off_view = copy.copy(retriever), file_source_view(retriever), copy.copy(retriever)
    off_view.corroboration = False
    runs = {}
    for rerank_name, chosen in (("normal", reranker), ("failed", FailingReranker())):
        for source, view in (("off", off_view), ("page_source", page_view), ("file_source", file_view)):
            runs[f"{source}__rerank_{rerank_name}"] = [
                {"id": case.case_id, "target": f"{case.file}#{case.page_no}", "context_type": case.context_type,
                 "ranked": doc_ranking(retriever, retrieve(case.question, retriever=view, scope=None, reranker=chosen, pool=POOL, top_n=POOL).chunk_ids)}
                for case in cases]
    return runs


def measure_corroboration_file(out: Path) -> dict:
    """올거나이즈 조정용 분할을 쪽 판독 글자로 잰다. 로컬 임베딩과 로컬 재순위만 쓰고 모델 API는 부르지 않는다."""
    from rag_lab.embeddings import LocalE5Embeddings
    from rag_lab.rerank import CrossEncoderReranker

    settings, device = load_settings(), pick_device()
    reading = json.loads(VISION_PAGES.read_text(encoding="utf-8"))
    retriever = Retriever(page_documents(load_pages(), reading), chunker=page_chunks, mode="fusion",
                          embeddings=LocalE5Embeddings(settings.embedding_model, device=device))
    cases = tune_cases(load_allganize_cases()[0])
    runs = corroboration_file_runs(retriever, MemoReranker(CrossEncoderReranker(settings.rerank_model, device=device)), cases)
    file_source = {"setup": {"device": device, "cases": len(cases), "chunks": len(retriever.chunks), "pool": POOL, "text": "page_reading", "decomposition": "none"},
                   "configs": {name: summarize_pages(rows) for name, rows in runs.items()},
                   "versus_off": {f"{source}__rerank_{rerank}": compare_pages(runs[f"off__rerank_{rerank}"], runs[f"{source}__rerank_{rerank}"])
                                  for rerank in ("normal", "failed") for source in ("page_source", "file_source")}}
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    _save(out, report | {"file_source": file_source})
    return file_source


def class_changes(base: list[dict], other: list[dict]) -> dict:
    """other − base. row_key가 나빠진 행, 좋아진 행과 문서 순위만 바뀐 행 수."""
    by_id = {row["id"]: row for row in base}
    worse, better, reordered = [], [], 0
    for row in other:
        old = by_id[row["id"]]
        reordered += row["ranked"] != old["ranked"]
        if row["expected"]:
            entry = {"id": row["id"], "expected": row["expected"], "off_top3": old["ranked"][:3], "on_top3": row["ranked"][:3], "in_scope": row["in_scope"]}
            (worse if row_key(row) < row_key(old) else better if row_key(row) > row_key(old) else []).append(entry)
    return {"worse": worse, "better": better, "ranking_changed": reordered}


def jev_class() -> dict:
    """fusion_rerank와 재순위 없는 fusion을 보강도 켬·끔으로 잰다. 분해 질의는 Claude가 필요해 쓰지 않는다."""
    documents = load_corpus()
    retriever = Retriever(documents, embeddings=make_embeddings(), mode="fusion")
    reranker = MemoReranker(make_reranker())
    rows, runs = class_rows(), {}
    for corroboration, label in ((True, "on"), (False, "off")):
        view = copy.copy(retriever)
        view.corroboration = corroboration
        for name, chosen in (("fusion_rerank", reranker), ("fusion", None)):
            runs[f"{name}__corroboration_{label}"] = [
                row | {"ranked": doc_ranking(retriever, retrieve(row["question"], retriever=view, scope=row["scope"], reranker=chosen, pool=POOL, top_n=POOL).chunk_ids)}
                for row in rows]
    return {"chunks": len(retriever.chunks), "questions": len(rows), "pool": POOL, "configs": {name: class_summary(measured) for name, measured in runs.items()},
            "no_expected_docs": [row["id"] for row in rows if not row["expected"]],
            "on_minus_off": {name: class_changes(runs[f"{name}__corroboration_off"], runs[f"{name}__corroboration_on"]) for name in ("fusion_rerank", "fusion")}}


def jev_report(report: dict, usage_dir: Path) -> None:
    """저장된 행에서 표를 다시 계산한다. 모델을 부르지 않는다."""
    runs = report.get("tune_runs", {})
    if all(run.name in runs for run in TUNE_RUNS):
        report["allganize_tune"] = {
            "configs": {name: summarize_pages(rows) | {"rerank_warning_rows": sum(bool(row["warnings"]) for row in rows),
                                                       "mean_queries": sum(row["queries"] for row in rows) / len(rows),
                                                       "missed_at_5": [row["id"] for row in rows if not hit_at(row["ranked"], row["target"], 5)]}
                        for name, rows in runs.items()},
            "decomposition": {name: compare_pages(runs[base.name], runs[other.name]) for name, base, other in DECOMPOSITION_PAIRS}}
        report.setdefault("corroboration", {})["allganize_tune"] = {name: compare_pages(runs[base.name], runs[other.name]) for name, base, other in CORROBORATION_PAIRS}
        report["corroboration"]["allganize_tune_rerank_failed"] = {name: compare_pages(runs[base.name], runs[other.name]) for name, base, other in RERANK_FAILED_PAIRS}
    if "class_corpus" in report:
        report.setdefault("corroboration", {})["class_corpus"] = report["class_corpus"]["on_minus_off"]
    answers = read_lines(JEV_ANSWERS)
    earlier = [row | {"source": path.name} for path in EARLIER_ANSWERS for row in read_lines(path) if row.get("config") in ("two_phase_auto", "ask_fusion_rerank")]
    answer_usage = read_rows(usage_dir / "answers")
    gate_usage = read_rows(usage_dir / "gates")
    jev_rows = [row for row in answer_usage + gate_usage if is_decision_usage(row)]
    report["answers"] = {"summary": summarize_answers(answers), "stops": [row for row in answers if "event" in row], "earlier_summary": summarize_answers(earlier),
                         "follow_up_pairs": follow_up_pairs(answers),
                         "claude_cost": sum(row["cost"] or 0 for row in answer_usage if not is_decision_usage(row)),
                         "claude_calls": sum(row["calls"] for row in answer_usage if not is_decision_usage(row)), "cost_report": render([row for row in answer_usage if not is_decision_usage(row)])}
    report["jev_usage"] = {"calls": sum(row["calls"] for row in jev_rows), "input_tokens": sum(row["input"] for row in jev_rows), "output_tokens": sum(row["output"] for row in jev_rows),
                           "gate_sweep_calls": sum(row["calls"] for row in gate_usage), "answer_calls": sum(row["calls"] for row in answer_usage if is_decision_usage(row)),
                           "reported_cost": None if any(row["cost"] is None for row in jev_rows) else sum(row["cost"] for row in jev_rows)}


def measure_jev(steps: list[str], out: Path, usage_dir: Path, max_seconds: float | None) -> None:
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    if "gates" in steps:
        jev_gates(report, out, usage_dir / "gates")
    if "tune" in steps:
        print("tune 멈춘 이유:", jev_tune(report, out, max_seconds))
    if "class" in steps and "class_corpus" not in report:
        report["class_corpus"] = jev_class()
        _save(out, report)
    if "report" in steps:
        jev_report(report, usage_dir)
        _save(out, report)
        print(report["jev_usage"])
        for pair in report["answers"]["follow_up_pairs"]:
            print(pair)


# ---- Ko-StrategyQA train: 정답이 여러 개인 문항에서 분해 게이트 ----

KSQ_RUNS = tuple(TuneRun(decomposition, corroboration, False) for decomposition, corroboration in
                 (("no_decompose", True), ("no_decompose", False), ("gated_decompose", True), ("gated_decompose", False), ("always_decompose", True)))
KSQ_COMPARISONS = (("gated_vs_no__corroboration_on", KSQ_RUNS[0], KSQ_RUNS[2]), ("always_vs_no__corroboration_on", KSQ_RUNS[0], KSQ_RUNS[4]),
                   ("gated_vs_no__corroboration_off", KSQ_RUNS[1], KSQ_RUNS[3]))
KSQ_GROUPS = ("all", "one_gold", "two_plus_gold")


def sample_train_ids(query_ids: set[str] | list[str], *, size: int = KSQ_SAMPLE, seed: int = BOOTSTRAP_SEED) -> list[str]:
    """정렬한 질문 ID를 random.Random(seed)로 섞어 앞에서 size개. 입력 순서와 무관하고 bench3.py의 표본과 같다."""
    ordered = sorted(query_ids)
    random.Random(seed).shuffle(ordered)
    return ordered[:size]


def in_gold_group(gold_count: int, group: str) -> bool:
    """정답이 하나인 문항, 둘 이상인 문항, 전체."""
    return {"all": True, "one_gold": gold_count == 1, "two_plus_gold": gold_count >= 2}[group]


def ranking_metrics(ranked: list[str], gold: set[str]) -> dict[str, float]:
    """문항 하나의 recall@5,10,100(정답 중 든 비율), MRR@10, nDCG@10(이진 관련도)."""
    metrics = {f"recall@{k}": len(gold & set(ranked[:k])) / len(gold) for k in (5, 10, KSQ_RECALL_DEPTH)}
    metrics["mrr@10"] = reciprocal_rank(ranked, gold, 10)
    gain = sum(1 / math.log2(rank + 1) for rank, item in enumerate(ranked[:10], 1) if item in gold)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(10, len(gold)) + 1))
    metrics["ndcg@10"] = gain / ideal
    return metrics


def summarize_ksq(rows: list[dict], group: str) -> dict:
    """group에 드는 문항의 지표 평균과 문항 수."""
    members = [row for row in rows if in_gold_group(row["gold"], group)]
    if not members:
        return {"n": 0}
    return {name: round(sum(row[name] for row in members) / len(members), 4) for name in ("recall@5", "recall@10", f"recall@{KSQ_RECALL_DEPTH}", "mrr@10", "ndcg@10")} | {"n": len(members)}


def compare_ksq(base: list[dict], other: list[dict], group: str, ids: set[str] | None = None) -> dict:
    """other − base를 문항별로 짝지어 nDCG@10, 재현율@10의 평균 차이와 부트스트랩 구간을 낸다. ids가 있으면 그 문항만."""
    by_id = {row["id"]: row for row in base}
    pairs = [(by_id[row["id"]], row) for row in other if in_gold_group(row["gold"], group) and (ids is None or row["id"] in ids)]
    if not pairs:
        return {"n": 0}
    result = {"n": len(pairs)}
    for name in ("ndcg@10", "recall@10"):
        differences = [new[name] - old[name] for old, new in pairs]
        result[name] = paired_bootstrap(differences) | {"better": sum(d > 1e-12 for d in differences), "worse": sum(d < -1e-12 for d in differences),
                                                      "same": sum(abs(d) <= 1e-12 for d in differences)}
    return result


class PrecomputedDocuments(Embeddings):
    """문서 벡터는 같은 e5 모델로 미리 계산해 둔 행렬에서 글로 찾고, 질의는 주어진 임베딩으로 계산한다."""
    def __init__(self, vectors: dict[str, np.ndarray], query_embeddings: Embeddings) -> None:
        self.vectors, self.query_embeddings = vectors, query_embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors[text].tolist() for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.query_embeddings.embed_query(text)


class RankCache:
    """같은 질의의 순위를 다시 계산하지 않는다. 항상 KSQ_RECALL_DEPTH까지 구해 앞에서 limit개를 돌려주며 순위는 limit과 무관한 앞부분이다."""
    def __init__(self, retriever: Retriever) -> None:
        self.retriever, self.chunks, self.ranks = retriever, retriever.chunks, {}

    def rank(self, query: str, scope: Scope | None, limit: int = 6) -> list[str]:
        if limit > KSQ_RECALL_DEPTH:
            raise ValueError(f"limit은 {KSQ_RECALL_DEPTH} 이하여야 합니다.")
        if query not in self.ranks:
            self.ranks[query] = self.retriever.rank(query, scope, limit=KSQ_RECALL_DEPTH)
        return self.ranks[query][:limit]


def ksq_ranking(question: str, cache: RankCache, reranker: Reranker, queries: list[str] | None) -> list[str]:
    """재순위한 상위 POOL개 뒤에 재순위하지 않은 합친 순서의 나머지(KSQ_RECALL_DEPTH까지)를 붙인다. recall@100용이다."""
    reranked = retrieve(question, retriever=cache, scope=None, reranker=reranker, queries=queries, pool=POOL, top_n=POOL).chunk_ids
    merged = retrieve(question, retriever=cache, scope=None, queries=queries, pool=KSQ_RECALL_DEPTH, top_n=KSQ_RECALL_DEPTH).chunk_ids
    placed = set(reranked)
    return reranked + [chunk_id for chunk_id in merged if chunk_id not in placed]


def load_ksq(data_dir: Path) -> tuple[list[dict], dict[str, str], dict[str, set[str]]]:
    """(말뭉치 문단, 질문 글, 질문별 정답 문단 ID). 정답표는 train 분할 파일 하나만 읽는다."""
    corpus = read_lines(data_dir / "corpus.jsonl")
    questions = {row["_id"]: row["text"] for row in read_lines(data_dir / "queries.jsonl")}
    gold: dict[str, set[str]] = defaultdict(set)
    for row in read_lines(data_dir / "qrels" / "train.jsonl"):
        gold[row["query-id"]].add(row["corpus-id"])
    return corpus, questions, {query_id: ids for query_id, ids in gold.items() if query_id in questions}


def ksq_documents(corpus: list[dict]) -> dict[str, Document]:
    """문단 하나를 문서 하나로 만든다. 출처는 제목이다."""
    return {row["_id"]: Document(doc_id=row["_id"], title=row["title"], source=row["title"], domain="", entity="공통", version="",
                                 valid_from=date.min, valid_until=None, status="approved", owner="", family=None, text=f"{row['title']}\n{row['text']}")
            for row in corpus}


def whole_document(doc: Document) -> list[Chunk]:
    return [Chunk(doc.doc_id, doc.doc_id, "", doc.text, 0, len(doc.text), 1, doc.text.count("\n") + 1)]


def sweep_gates(report: dict, out: Path, usage_log: Path, ids: list[str], questions: dict[str, str], max_seconds: float | None, dataset: str) -> str:
    """분해 게이트를 질문마다 한 번 묻는다. 20문항마다 저장하고 다시 실행하면 이어서 한다."""
    rows = report.setdefault("gates", {}).setdefault("rows", [])
    asked = {row["id"] for row in rows}
    pending = [query_id for query_id in ids if query_id not in asked]
    if not pending:
        return "finished"
    announce(f"Jev 분해 게이트, {dataset}(Claude 호출 없음, Jev 호출은 질문마다 1회)", model_calls=len(pending))
    decider, started = make_decider(), time.monotonic()
    usage_log.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DAY02_USAGE_LOG"] = str(usage_log)
    try:
        for count, query_id in enumerate(pending, 1):
            if max_seconds is not None and time.monotonic() - started >= max_seconds:
                _save(out, report)
                return "time_limit"
            gate = needs_decomposition(decider, questions[query_id])  # reason에는 질문 글이나 오류 글이 들어갈 수 있어 저장하지 않는다.
            rows.append({"id": query_id, "probability": gate.probability, "decision": gate.decision, "fallback": gate.fallback, "model": gate.model})
            if count % 20 == 0:
                _save(out, report)
                print("게이트", len(rows), "/", len(ids), flush=True)
    finally:
        del os.environ["DAY02_USAGE_LOG"]
    _save(out, report)
    return "finished"


def ksq_runs(report: dict, out: Path, data_dir: Path, vectors_file: Path, ids: list[str], max_seconds: float | None) -> str:
    """구성 하나가 끝날 때마다 저장한다. 시간을 넘기면 다음 구성을 시작하지 않는다."""
    from rag_lab.embeddings import LocalE5Embeddings
    from rag_lab.rerank import CrossEncoderReranker

    finished = report.setdefault("runs", {})
    if all(run.name in finished for run in KSQ_RUNS):
        return "finished"
    corpus, questions, gold = load_ksq(data_dir)
    settings, device, started = load_settings(), pick_device(), time.monotonic()
    documents = ksq_documents(corpus)
    matrix = np.load(vectors_file)
    if len(matrix) != len(corpus):
        raise SystemExit(f"문서 벡터 파일의 행 수 {len(matrix)}가 말뭉치 {len(corpus)}와 다릅니다.")
    vectors = {documents[row["_id"]].text: matrix[index] for index, row in enumerate(corpus)}
    embeddings = PrecomputedDocuments(vectors, LocalE5Embeddings(settings.embedding_model, device=device))
    base = Retriever(documents, chunker=whole_document, mode="fusion", embeddings=embeddings)
    caches = {}
    for corroboration in (True, False):
        view = file_source_view(base)  # 출처 보강도가 같은 제목의 문단을 한 출처로 센다.
        view.corroboration = corroboration
        caches[corroboration] = RankCache(view)
    reranker = MemoReranker(CrossEncoderReranker(settings.rerank_model, device=device))
    saved = json.loads(KSQ_SUBQUERIES.read_text(encoding="utf-8"))
    gates = {row["id"]: row for row in report["gates"]["rows"]}
    report["setup"] = {"device": device, "questions": len(ids), "paragraphs": len(corpus), "pool": POOL, "recall_depth": KSQ_RECALL_DEPTH, "source": "제목",
                       "gold_counts": {group: sum(in_gold_group(len(gold[query_id]), group) for query_id in ids) for group in KSQ_GROUPS},
                       "saved_subquery_ids_match_sample": set(saved) == set(ids)}
    for run in KSQ_RUNS:
        if run.name in finished:
            continue
        if max_seconds is not None and time.monotonic() - started >= max_seconds:
            return "time_limit"
        rows = []
        for query_id in ids:
            queries = plan_queries(run.decomposition, query_id, gates, saved)
            ranked = ksq_ranking(questions[query_id], caches[run.corroboration], reranker, queries)
            rows.append({"id": query_id, "gold": len(gold[query_id]), "queries": 1 + len(set(queries or []) - {questions[query_id]}),
                         **ranking_metrics(ranked, gold[query_id])})
        finished[run.name] = rows
        _save(out, report)
        print(run.name, summarize_ksq(rows, "all"), f"{time.monotonic() - started:.0f}초", flush=True)
    return "finished"


def ksq_report(report: dict, usage_dir: Path) -> None:
    """저장된 행에서 표를 다시 계산한다. 모델을 부르지 않는다."""
    runs = report["runs"]
    gate_rows = report["gates"]["rows"]
    report["gate"] = gate_summary(gate_rows) | {"fallback_count": sum(row["fallback"] is not None for row in gate_rows)}
    report["summary"] = {name: {group: summarize_ksq(rows, group) for group in KSQ_GROUPS} for name, rows in runs.items()}
    opened = {row["id"] for row in gate_rows if row["decision"]}
    report["comparisons"] = {name: {group: compare_ksq(runs[base.name], runs[other.name], group) for group in KSQ_GROUPS} for name, base, other in KSQ_COMPARISONS}
    report["gate_open_only"] = {name: {group: compare_ksq(runs[base.name], runs[other.name], group, opened) for group in KSQ_GROUPS}
                                for name, base, other in KSQ_COMPARISONS[:2]}
    report["gate_closed_only"] = {"gated_vs_no__corroboration_on": compare_ksq(runs[KSQ_RUNS[0].name], runs[KSQ_RUNS[2].name], "all", {row["id"] for row in gate_rows} - opened)}
    open_gold = [row["gold"] for row in runs[KSQ_RUNS[0].name] if row["id"] in opened]
    report["gate_open_gold_counts"] = {"one_gold": sum(count == 1 for count in open_gold), "two_plus_gold": sum(count >= 2 for count in open_gold)}
    report["mean_queries"] = {name: round(sum(row["queries"] for row in rows) / len(rows), 3) for name, rows in runs.items()}
    jev = [row for row in read_rows(usage_dir) if is_decision_usage(row)]
    report["jev_usage"] = {"calls": sum(row["calls"] for row in jev), "input_tokens": sum(row["input"] for row in jev), "output_tokens": sum(row["output"] for row in jev),
                           "reported_cost": None if any(row["cost"] is None for row in jev) else sum(row["cost"] for row in jev)}
    report["note"] = "Ko-StrategyQA train 300문항은 조정용 분할이다. dev와 비교할 수 없다. 이 파일에는 지표와 ID만 있다."


def measure_ksq(data_dir: Path, vectors_file: Path, out: Path, usage_dir: Path, max_seconds: float | None) -> None:
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    _, questions, gold = load_ksq(data_dir)
    ids = sample_train_ids(gold)
    print("게이트 멈춘 이유:", sweep_gates(report, out, usage_dir / "gates" / "ksq_gates.usage.jsonl", ids, questions, max_seconds, "Ko-StrategyQA train"))
    if len(report["gates"]["rows"]) < len(ids):
        return
    print("검색 멈춘 이유:", ksq_runs(report, out, data_dir, vectors_file, ids, max_seconds))
    if all(run.name in report["runs"] for run in KSQ_RUNS):
        ksq_report(report, usage_dir / "gates")
        _save(out, report)
        print(json.dumps({key: report[key] for key in ("gate", "summary", "comparisons", "jev_usage")}, ensure_ascii=False, indent=1))


# ---- Ko-LongRAG: 문서 여러 개를 합치는 질문에서 분해 게이트 ----

KO_MULTI, KO_SINGLE = "multidocQA", "singledocQA"
KO_NAMED_TWO, KO_NAMED_ONE, KO_ANSWER_STRING = "gold_named_two_titles_all_of", "gold_named_one_title", "gold_answer_string_any_of"
KO_EXCLUDED, KO_EXCLUDED_UNANSWERABLE = "excluded_no_defensible_gold", "excluded_unanswerable"
KO_GROUPS = (f"{KO_MULTI}/{KO_NAMED_TWO}", f"{KO_MULTI}/{KO_ANSWER_STRING}", f"{KO_SINGLE}/{KO_NAMED_ONE}", f"{KO_SINGLE}/{KO_ANSWER_STRING}")
KO_UNANSWERABLE = "주어진 문서내에서 답할 수 있는 정보가 충분하지 않습니다."
KO_YES_NO = {"예", "네", "아니오", "아니요"}
KO_MIN_ANSWER_CHARS, KO_MAX_ANSWER_DOCS = 3, 3  # 등급 규칙. outputs/benchmarks/ko_longrag/inspect.json의 gold_definition과 같다.
KO_SINGLE_SAMPLE, KO_CONCURRENCY, KO_TRIES, KO_BACKOFF_SECONDS = 150, 6, 3, 2.0
KO_SAVE_EVERY, KO_VECTOR_BATCH = 20, 2048
KO_COST_CAP_USD = 1.00  # 저자가 고지한 지출 상한
KO_RUNS = {"no_decompose": TuneRun("no_decompose", True, False), "no_decompose__corroboration_off": TuneRun("no_decompose", False, False),
           "gated_decompose": TuneRun("gated_decompose", True, False), "gated_decompose__corroboration_off": TuneRun("gated_decompose", False, False),
           "always_decompose": TuneRun("always_decompose", True, False)}
KO_COMPARISONS = (("gated_vs_no", "no_decompose", "gated_decompose"), ("always_vs_no", "no_decompose", "always_decompose"),
                  ("gated_vs_no__corroboration_off", "no_decompose__corroboration_off", "gated_decompose__corroboration_off"),
                  ("corroboration_on_vs_off__no_decompose", "no_decompose__corroboration_off", "no_decompose"),
                  ("corroboration_on_vs_off__gated", "gated_decompose__corroboration_off", "gated_decompose"))
KO_METRICS = ("recall@5", "recall@10", "recall@25", "full_gold@10", "mrr@10", "ndcg@10", "pool_recall@50")
KO_COMPARED = ("recall@10", "full_gold@10", "ndcg@10", "pool_recall@50")
KO_RAW = ROOT / "outputs/benchmarks/ko_longrag/raw/test.parquet"
KO_DECOMPOSED = ROOT / "outputs/benchmarks/ko_longrag/decomposed.json"
KO_OUT = ROOT / "outputs/benchmarks/results/measure_ko_longrag.json"


class KoCase(NamedTuple):
    id: str
    task: str
    tier: str
    question: str
    gold: tuple[str, ...]

    @property
    def group(self) -> str:
        return f"{self.task}/{self.tier}"


def split_ko_documents(row: dict) -> list[tuple[str, str]]:
    """context를 (제목, 본문)으로 나눈다. titles 순서대로 다음 "Title: <제목> Text:"를 찾으므로 같은 제목이 반복돼도 구역별로 맞는다."""
    context, cursor, found = row["context"], 0, []
    for raw_title in row["titles"]:
        title = raw_title[1:-1] if len(raw_title) > 1 and raw_title[0] == raw_title[-1] == '"' else raw_title  # 제목에만 있고 본문 머리글에는 없는 따옴표
        marker = f"Title: {title} Text:"
        start = context.find(marker, cursor)
        if start < 0:
            raise ValueError(f"{row['id']}: 제목 구역을 찾지 못했습니다.")
        cursor = start + len(marker)
        found.append((title, start, cursor))
    ends = [start for _, start, _ in found[1:]] + [len(context)]
    return [(title, context[body:end].strip()) for (title, _, body), end in zip(found, ends, strict=True)]


def ko_doc_id(title: str, body: str) -> str:
    """제목과 본문의 해시. 결과 파일에 데이터 글이 들어가지 않고, 본문이 다른 같은 제목 둘이 섞이지 않는다."""
    return hashlib.sha1(f"{title}\0{body}".encode()).hexdigest()[:16]


def ko_gold(row: dict, blocks: list[tuple[str, str]]) -> tuple[str, list[int]]:
    """(등급, 정답 구역 번호). ko-inspect가 정한 규칙이고 데이터셋 자체의 정답이 아니다. 맞는 규칙이 없으면 제외하고 지어내지 않는다."""
    if row["answer"].startswith(KO_UNANSWERABLE):
        return KO_EXCLUDED_UNANSWERABLE, []
    question = row["question"]
    named = [index for index, (title, _) in enumerate(blocks) if title in question]
    if row["task"] == KO_MULTI and len(named) == 2:
        return KO_NAMED_TWO, named
    if row["task"] == KO_SINGLE and len(named) == 1:
        return KO_NAMED_ONE, named
    answer = row["answer"].strip().rstrip(".").strip()
    holding = [] if answer in KO_YES_NO or len(answer) < KO_MIN_ANSWER_CHARS or answer in question else [index for index, (_, body) in enumerate(blocks) if answer in body]
    return (KO_ANSWER_STRING, holding) if 1 <= len(holding) <= KO_MAX_ANSWER_DOCS else (KO_EXCLUDED, [])


def ko_cases(rows: list[dict]) -> list[KoCase]:
    cases = []
    for row in rows:
        blocks = split_ko_documents(row)
        tier, gold = ko_gold(row, blocks)
        cases.append(KoCase(row["id"], row["task"], tier, row["question"], tuple(dict.fromkeys(ko_doc_id(*blocks[index]) for index in gold))))
    return cases


def ko_documents(rows: list[dict]) -> dict[str, Document]:
    """모든 행의 문서를 (제목, 본문) 기준으로 합친다. 행마다 있던 문서 묶음이 한 말뭉치가 되므로 원래 시험보다 찾기 어렵다."""
    documents = {}
    for row in rows:
        for title, body in split_ko_documents(row):
            doc_id = ko_doc_id(title, body)
            documents[doc_id] = Document(doc_id=doc_id, title=title, source=title, domain="", entity="공통", version="",
                                         valid_from=date.min, valid_until=None, status="approved", owner="", family=None, text=body)
    return documents


def ko_sample(cases: list[KoCase]) -> list[str]:
    """답할 수 있는 다문서 문항 전부와 답할 수 있는 단일 문서 문항에서 시드로 뽑은 150개. 정답 등급을 보지 않고 뽑는다."""
    answerable = [case for case in cases if case.tier != KO_EXCLUDED_UNANSWERABLE]
    return sorted(case.id for case in answerable if case.task == KO_MULTI) + sample_train_ids([case.id for case in answerable if case.task == KO_SINGLE], size=KO_SINGLE_SAMPLE)


def ko_metrics(ranked: list[str], gold: tuple[str, ...], tier: str) -> dict[str, float]:
    """문항 하나의 지표. 답 문자열 등급은 근거 일부만 아는 정답이라 하나만 찾아도 찾은 것으로 세고, nDCG@10도 첫 정답만 센다."""
    expected = set(gold)
    any_of = tier == KO_ANSWER_STRING

    def recall(k: int) -> float:
        hits = len(expected & set(ranked[:k]))
        return float(hits > 0) if any_of else hits / len(expected)

    positions = [rank for rank, item in enumerate(ranked[:10], 1) if item in expected]
    wanted = positions[:1] if any_of else positions
    ideal = range(1, 2) if any_of else range(1, min(10, len(expected)) + 1)
    return {**{f"recall@{k}": recall(k) for k in (5, 10, 25)}, "full_gold@10": int(recall(10) == 1), "mrr@10": reciprocal_rank(ranked, expected, 10),
            "ndcg@10": sum(1 / math.log2(rank + 1) for rank in wanted) / sum(1 / math.log2(rank + 1) for rank in ideal), "pool_recall@50": recall(POOL)}


def title_mention_ranking(question: str, titles: dict[str, str]) -> list[str]:
    """제목이 질문에 글자 그대로 든 문서만, 긴 제목부터. 명명 등급은 이 규칙으로 정답을 정했으므로 이 기준선은 순환이다."""
    return sorted((doc_id for doc_id, title in titles.items() if title in question), key=lambda doc_id: (-len(titles[doc_id]), doc_id))


def compare_ko(base: list[dict], other: list[dict], group: str, ids: set[str] | None = None) -> dict:
    """other − base를 문항별로 짝지어 지표마다 부트스트랩 구간과 좋아진·나빠진 문항 ID를 낸다. ids가 있으면 그 문항만."""
    by_id = {row["id"]: row for row in base}
    pairs = [(by_id[row["id"]], row) for row in other if row["group"] == group and row["id"] in by_id and (ids is None or row["id"] in ids)]
    if not pairs:
        return {"n": 0}
    result: dict = {"n": len(pairs)}
    for name in KO_COMPARED:
        differences = {new["id"]: new[name] - old[name] for old, new in pairs}
        result[name] = paired_bootstrap(list(differences.values())) | {"improved_ids": sorted(key for key, value in differences.items() if value > 1e-12),
                                                                        "worsened_ids": sorted(key for key, value in differences.items() if value < -1e-12)}
    return result


def probability_quartiles(rows: list[dict]) -> list[dict]:
    """게이트 확률의 사분위 구간마다 문항 수와 열린 수. 판단이 없던 행은 구간을 정할 수 없어 뺀다(gate_summary의 fallback_ids가 드러낸다)."""
    judged = [row for row in rows if row["probability"] is not None]
    if not judged:
        return []
    edges = np.quantile([row["probability"] for row in judged], [0, .25, .5, .75, 1])
    buckets = [{"quartile": f"Q{index + 1}", "low": float(edges[index]), "high": float(edges[index + 1]), "n": 0, "opened": 0} for index in range(4)]
    for row in judged:
        bucket = buckets[int(np.searchsorted(edges[1:4], row["probability"], side="left"))]
        bucket["n"] += 1
        bucket["opened"] += row["decision"]
    return buckets


def _decompose_with_retries(question: str, decompose: Callable[[str], list[str]], earlier: dict, backoff: float) -> dict:
    """make_model은 SDK 재시도를 끄므로 여기서 다시 묻고 예외의 타입 이름만 남긴다. 예외 내용에는 질문 글이 들어갈 수 있다."""
    attempts, errors = earlier.get("attempts", 0), list(earlier.get("errors", []))
    for tries in range(KO_TRIES):
        attempts += 1
        try:
            queries = decompose(question)
        except Exception as error:  # 공급자 오류는 종류가 많고, 어떤 오류든 기록하고 다시 묻는다.
            errors.append(type(error).__name__)
            time.sleep(backoff * 2 ** tries)
            continue
        return {"queries": queries, "attempts": attempts, "errors": errors, "fallback": queries == [question]}
    return {"queries": None, "attempts": attempts, "errors": errors, "fallback": False}


def _batch_reserve(usage_dir: Path, size: int) -> float:
    """다음 묶음이 쓸 만한 돈: 지금까지의 호출당 평균의 두 배."""
    rows = read_rows(usage_dir)
    calls = sum(row["calls"] for row in rows)
    return 2 * size * sum(row["cost"] or 0 for row in rows) / calls if calls else 0.0


def decompose_rows(ids: list[str], questions: dict[str, str], decompose: Callable[[str], list[str]], path: Path, saved: dict, usage_dir: Path,
                   *, cap: float, max_seconds: float | None, backoff: float = KO_BACKOFF_SECONDS) -> str:
    """KO_CONCURRENCY개씩 묶어 묻고 묶음마다 저장한다. 묶음 전에 지출과 시간을 본다. 끝내 실패한 행은 queries가 None이고 다음 호출에서 다시 묻는다."""
    pending = [row_id for row_id in ids if saved["rows"].get(row_id, {}).get("queries") is None]
    started = time.monotonic()
    with ThreadPoolExecutor(KO_CONCURRENCY) as pool:
        for begin in range(0, len(pending), KO_CONCURRENCY):
            batch = pending[begin:begin + KO_CONCURRENCY]
            if max_seconds is not None and time.monotonic() - started >= max_seconds:
                return "time_limit"
            stop = _spending_stop(usage_dir, cap, _batch_reserve(usage_dir, len(batch)))
            if stop:
                saved["stops"].append({"reason": stop[0], "spent": stop[1], "remaining": len(pending) - begin})
                _save(path, saved)
                return stop[0]
            replies = pool.map(lambda row_id: _decompose_with_retries(questions[row_id], decompose, saved["rows"].get(row_id, {}), backoff), batch)
            saved["rows"].update(zip(batch, replies, strict=True))
            _save(path, saved)
            print("분해", len(saved["rows"]), "/", len(ids), flush=True)
    return "finished"


def ko_runs(report: dict, out: Path, cases: list[KoCase], retriever: Retriever, reranker: Reranker, gates: dict[str, dict], saved: dict[str, list[str]], max_seconds: float | None) -> str:
    """정답이 있는 문항만 잰다. 보강도 끔은 다문서 문항만이다. 행 단위로 이어서 돌 수 있다. 결과 행에는 ID와 지표만 쓴다."""
    views = {}
    for corroboration in (True, False):
        view = copy.copy(retriever)
        view.corroboration = corroboration
        views[corroboration] = RankCache(view)
    finished, started = report.setdefault("runs", {}), time.monotonic()
    scored = [case for case in cases if case.gold]
    for name, run in KO_RUNS.items():
        rows = finished.setdefault(name, [])
        done = {row["id"] for row in rows}
        pending = [case for case in scored if case.id not in done and (run.corroboration or case.task == KO_MULTI)]
        for count, case in enumerate(pending, 1):
            if max_seconds is not None and time.monotonic() - started >= max_seconds:
                _save(out, report)
                return "time_limit"
            found = retrieve(case.question, retriever=views[run.corroboration], scope=None, reranker=reranker, queries=plan_queries(run.decomposition, case.id, gates, saved), pool=POOL, top_n=POOL)
            rows.append({"id": case.id, "group": case.group, "queries": len(found.queries), "rerank_failed": bool(found.warnings),
                         **ko_metrics(doc_ranking(retriever, found.chunk_ids), case.gold, case.tier)})
            if count % KO_SAVE_EVERY == 0:
                _save(out, report)
                print(name, len(rows), f"{time.monotonic() - started:.0f}초", flush=True)
        _save(out, report)
    return "finished"


def summarize_ko(rows: list[dict], group: str) -> dict:
    members = [row for row in rows if row["group"] == group]
    if not members:
        return {"n": 0}
    return {name: round(sum(row[name] for row in members) / len(members), 4) for name in KO_METRICS} | {"n": len(members), "mean_queries": round(sum(row["queries"] for row in members) / len(members), 3)}


def ko_report(report: dict, cases: list[KoCase], documents: dict[str, Document], decomposed: dict, claude_dir: Path, jev_dir: Path) -> None:
    """저장된 행에서 표를 다시 계산한다. 모델을 부르지 않는다."""
    runs, gate_rows, by_id = report["runs"], report["gates"]["rows"], {case.id: case for case in cases}
    measured = {row["id"] for row in runs["no_decompose"]}
    titles = {doc_id: document.title for doc_id, document in documents.items()}
    baseline = [{"id": case.id, "group": case.group, "queries": 0, **ko_metrics(title_mention_ranking(case.question, titles), case.gold, case.tier)} for case in cases if case.id in measured]
    tables = {**runs, "title_mention": baseline}
    report["summary"] = {name: {group: summarize_ko(rows, group) for group in KO_GROUPS} for name, rows in tables.items()}
    opened = {row["id"] for row in gate_rows if row["decision"]}
    report["comparisons"] = {name: {group: compare_ko(runs[base], runs[other], group) for group in KO_GROUPS} for name, base, other in KO_COMPARISONS}
    report["gate_open_only"] = {group: compare_ko(runs["no_decompose"], runs["gated_decompose"], group, opened) for group in KO_GROUPS}
    by_task = {task: [row for row in gate_rows if by_id[row["id"]].task == task] for task in (KO_MULTI, KO_SINGLE)}
    groups = sorted({by_id[row["id"]].group for row in gate_rows})
    report["gate"] = {"by_task": {task: gate_summary(rows) | {"quartiles": probability_quartiles(rows)} for task, rows in by_task.items() if rows},
                      "by_group": {group: {"n": sum(by_id[row["id"]].group == group for row in gate_rows),
                                           "opened": sum(by_id[row["id"]].group == group and row["decision"] for row in gate_rows)} for group in groups}}
    rows = decomposed["rows"]
    report["decomposition"] = {"rows": len(rows), "fallback_ids": sorted(key for key, row in rows.items() if row["fallback"]),
                               "retried_ids": sorted(key for key, row in rows.items() if row["attempts"] > 1),
                               "failed_ids": sorted(key for key, row in rows.items() if row["queries"] is None),
                               "error_types": dict(Counter(error for row in rows.values() for error in row["errors"])), "stops": decomposed["stops"]}
    claude, jev = read_rows(claude_dir), read_rows(jev_dir)
    report["spend"] = {"claude_calls": sum(row["calls"] for row in claude), "claude_cost": sum(row["cost"] or 0 for row in claude), "claude_unpriced": sum(row["cost"] is None for row in claude),
                       "jev_calls": sum(row["calls"] for row in jev), "jev_input_tokens": sum(row["input"] for row in jev), "jev_output_tokens": sum(row["output"] for row in jev),
                       "jev_cost": sum(row["cost"] or 0 for row in jev), "cost_report": render(claude + jev)}
    report["setup"] = report.get("setup", {}) | {"tier_counts": dict(sorted(Counter(case.group for case in cases).items())),
                                                 "pool": POOL, "chunker": f"{CHUNK_SIZE}자, 겹침 {CHUNK_OVERLAP}, 제목 접두",
                                                 "note": "정답은 저자 규칙으로 만든 값이고 데이터셋의 정답이 아니다. 나눈 분할 없이 모든 행을 한 번만 읽었고 아무것도 조정하지 않았다. 이 파일에는 ID와 지표만 있다."}


def ko_chunk_vectors(chunks: list[Chunk], embeddings: Embeddings, path: Path, max_seconds: float | None) -> np.ndarray | None:
    """조각 벡터를 묶음마다 저장한다. 시간을 넘기면 None을 돌려주고 다시 실행하면 이어서 계산한다."""
    done = np.load(path) if path.exists() else np.empty((0, 0), dtype=np.float32)
    started = time.monotonic()
    while len(done) < len(chunks):
        if max_seconds is not None and time.monotonic() - started >= max_seconds:
            return None
        part = np.asarray(embeddings.embed_documents([chunk.text for chunk in chunks[len(done):len(done) + KO_VECTOR_BATCH]]), dtype=np.float32)
        done = np.vstack([done, part]) if len(done) else part
        with open(path.with_suffix(".tmp"), "wb") as output:
            np.save(output, done)
        path.with_suffix(".tmp").replace(path)
        print("조각 벡터", len(done), "/", len(chunks), f"{time.monotonic() - started:.0f}초", flush=True)
    return done


def ko_retriever(documents: dict[str, Document], work_dir: Path, device: str, max_seconds: float | None) -> Retriever | None:
    """색인을 작업 폴더에 저장해 다음 호출이 Kiwi 토큰화와 임베딩을 다시 하지 않게 한다. 파일은 이 도구가 쓴 것만 읽는다."""
    from rag_lab.embeddings import LocalE5Embeddings

    cached = work_dir / "retriever.pickle"
    if cached.exists():
        with open(cached, "rb") as source:
            return pickle.load(source)
    query_embeddings = LocalE5Embeddings(load_settings().embedding_model, device=device)
    chunks = [chunk for document in documents.values() for chunk in page_chunks(document)]
    vectors = ko_chunk_vectors(chunks, query_embeddings, work_dir / "chunk_vectors.npy", max_seconds)
    if vectors is None:
        return None
    by_text = {chunk.text: vector for chunk, vector in zip(chunks, vectors, strict=True)}
    retriever = Retriever(documents, chunker=page_chunks, mode="fusion", embeddings=PrecomputedDocuments(by_text, query_embeddings))
    retriever.dense.embeddings = query_embeddings  # 문서 벡터는 이미 색인에 있어 글로 찾는 표를 색인 파일에 담지 않는다.
    with open(cached, "wb") as output:
        pickle.dump(retriever, output)
    return retriever


def load_ko_rows(path: Path) -> list[dict]:
    """pyarrow는 프로젝트 의존성이 아니다. uv run --no-sync --with pyarrow로 실행할 때만 쓴다."""
    import pyarrow.parquet

    return pyarrow.parquet.read_table(path).to_pylist()


def _read_json(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def ko_decompose(ids: list[str], questions: dict[str, str], decomposed_path: Path, usage_dir: Path, cap: float, max_seconds: float | None) -> str:
    saved = _read_json(decomposed_path, {"rows": {}, "stops": []})
    pending = sum(saved["rows"].get(row_id, {}).get("queries") is None for row_id in ids)
    announce("Ko-LongRAG 질문 분해", model_calls=pending)
    model = make_model()
    usage_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DAY02_USAGE_LOG"] = str(usage_dir / "ko_decompose.usage.jsonl")
    try:
        return decompose_rows(ids, questions, lambda question: decompose_question(model, question), decomposed_path, saved, usage_dir, cap=cap, max_seconds=max_seconds)
    finally:
        del os.environ["DAY02_USAGE_LOG"]


def measure_ko(raw: Path, decomposed_path: Path, work_dir: Path, out: Path, steps: list[str], cap: float, max_seconds: float | None) -> None:
    rows = load_ko_rows(raw)
    cases = ko_cases(rows)
    ids, documents = ko_sample(cases), ko_documents(rows)
    questions = {case.id: case.question for case in cases}
    report = _read_json(out, {})
    work_dir.mkdir(parents=True, exist_ok=True)
    if "gates" in steps:
        print("게이트 멈춘 이유:", sweep_gates(report, out, work_dir / "usage_jev" / "ko_gates.usage.jsonl", ids, questions, max_seconds, "Ko-LongRAG"))
    if "decompose" in steps:
        print("분해 멈춘 이유:", ko_decompose(ids, questions, decomposed_path, work_dir / "usage_claude", cap, max_seconds))
    decomposed = _read_json(decomposed_path, {"rows": {}, "stops": []})
    if "runs" in steps:
        from rag_lab.rerank import CrossEncoderReranker

        device, started = pick_device(), time.monotonic()
        retriever = ko_retriever(documents, work_dir, device, max_seconds)
        if retriever is None:
            print("검색 멈춘 이유: 조각 벡터 계산 중 time_limit")
            return
        report["setup"] = {"device": device, "documents": len(documents), "chunks": len(retriever.chunks), "questions_decomposed": len(ids)}
        print("색인 준비", f"{time.monotonic() - started:.0f}초", "조각", len(retriever.chunks), flush=True)
        left = None if max_seconds is None else max(0.0, max_seconds - (time.monotonic() - started))
        chosen = set(ids)
        saved = {row_id: decomposed["rows"].get(row_id, {}).get("queries") or [] for row_id in ids}
        reranker = MemoReranker(CrossEncoderReranker(load_settings().rerank_model, device=device))
        gates = {row["id"]: row for row in report["gates"]["rows"]}
        print("검색 멈춘 이유:", ko_runs(report, out, [case for case in cases if case.id in chosen], retriever, reranker, gates, saved, left))
    if "report" in steps:
        ko_report(report, cases, documents, decomposed, work_dir / "usage_claude", work_dir / "usage_jev")
        _save(out, report)
        print(json.dumps({key: report[key] for key in ("setup", "summary", "gate", "decomposition", "spend")}, ensure_ascii=False, indent=1))


def print_class(report: dict) -> None:
    print(f"조각 {report['chunks']}개, 질문 {report['questions']}개, draft 정답 {report['draft_gold_rows']}행")
    for config, body in report["configs"].items():
        print(f"{config:14} all {body['all']} | in_scope {body['in_scope']} | out_of_scope n={body['out_of_scope']['n']}")
    print("범위 밖:", report["out_of_scope_ids"], "기대 문서 없음:", report["no_expected_docs"])
    for config, body in report["configs"].items():
        print(f"-- 실패 행 {config} ({len(body['failing_rows'])})")
        for row in body["failing_rows"]:
            print("  ", row["id"], "기대", row["expected"], "검색", row["top3"], "범위안" if row["in_scope"] else "범위밖", "draft" if row["draft"] else "")
    for config, body in report["vs_hybrid"].items():
        print(f"-- {config} vs hybrid 나빠짐 {[r['id'] for r in body['worse']]} 좋아짐 {[r['id'] for r in body['better']]}")
    print("초/질문", report["seconds"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    retrieval = sub.add_parser("retrieval", help="수업 문서와 올거나이즈 조정용 분할의 검색을 잰다")
    retrieval.add_argument("--only", choices=("class", "tune"), help="한쪽만 잰다. 결과 파일의 다른 쪽은 유지한다")
    retrieval.add_argument("--out", type=Path, default=DEFAULT_OUT)
    answers = sub.add_parser("answers", help="12문항을 네 구성으로 실제 Claude와 Decision API에 묻는다(유료). 이미 있는 행은 건너뛴다")
    answers.add_argument("--usage-dir", type=Path, required=True, help="행별 사용량 기록 폴더. 지출 한도가 이 폴더 전체로 계산된다")
    answers.add_argument("--cases", nargs="+", help="이 문항만 돈다")
    answers.add_argument("--max-seconds", type=float, help="이번 호출에서 다음 행을 시작하지 않을 경과 초")
    answers.add_argument("--out", type=Path, default=ANSWERS_OUT, help="결과 줄 파일. 정하면 기본 파일은 건드리지 않는다")
    answers.add_argument("--pair", action="append", type=parse_pair, metavar="구성:문항ID", help="이 (구성, 문항) 행만 돈다. 여러 번 쓸 수 있다")
    answers.add_argument("--cap", type=float, default=COST_CAP_USD, help="지출 상한(USD). 사용량 폴더 전체로 계산한다")
    jev = sub.add_parser("jev", help="Jev 관문, 게이트 분해, 출처 보강을 잰다. gates만 Jev를 부른다. 끝난 단위는 건너뛴다")
    jev.add_argument("--usage-dir", type=Path, required=True, help="gates/에 게이트 사용량을 쓰고, answers/에서 답변 사용량을 읽는다")
    jev.add_argument("--only", nargs="+", choices=("gates", "tune", "class", "report"), default=["gates", "tune", "class", "report"])
    jev.add_argument("--max-seconds", type=float, help="tune에서 다음 구성을 시작하지 않을 경과 초")
    jev.add_argument("--out", type=Path, default=JEV_OUT)
    file_source = sub.add_parser("corroboration-file", help="출처 보강도를 쪽 출처와 파일 출처로 잰다(올거나이즈 조정용 분할, 모델 호출 없음)")
    file_source.add_argument("--out", type=Path, default=FILE_SOURCE_OUT)
    ksq = sub.add_parser("ksq-gated", help="Ko-StrategyQA train 300문항에서 분해 게이트를 잰다(Jev 질문마다 1회, Claude 호출 없음). 끝난 단위는 건너뛴다")
    ksq.add_argument("--data-dir", type=Path, required=True, help="corpus.jsonl, queries.jsonl, qrels/train.jsonl이 든 폴더")
    ksq.add_argument("--vectors", type=Path, required=True, help="같은 e5 모델로 미리 계산한 문단 벡터(.npy, corpus.jsonl 순서)")
    ksq.add_argument("--usage-dir", type=Path, required=True)
    ksq.add_argument("--max-seconds", type=float)
    ksq.add_argument("--out", type=Path, default=KSQ_OUT)
    ko = sub.add_parser("ko-longrag", help="Ko-LongRAG에서 분해 게이트를 잰다(Claude 문항마다 1회, 상한 --cap, Jev 문항마다 1회). 끝난 단위는 건너뛴다. pyarrow가 필요하다")
    ko.add_argument("--raw", type=Path, default=KO_RAW, help="ko-inspect가 받은 parquet")
    ko.add_argument("--decomposed", type=Path, default=KO_DECOMPOSED, help="분해 질의를 저장할 파일. 데이터 글이 들어가므로 git 제외 폴더에 둔다")
    ko.add_argument("--work-dir", type=Path, required=True, help="사용량 기록, 조각 벡터, 색인을 두는 임시 폴더")
    ko.add_argument("--only", nargs="+", choices=("gates", "decompose", "runs", "report"), default=["gates", "decompose", "runs", "report"])
    ko.add_argument("--cap", type=float, default=KO_COST_CAP_USD, help="Claude 지출 상한(USD)")
    ko.add_argument("--max-seconds", type=float, help="이번 호출에서 다음 단위를 시작하지 않을 경과 초")
    ko.add_argument("--out", type=Path, default=KO_OUT)
    args = parser.parse_args()
    if args.command == "ko-longrag":
        measure_ko(args.raw, args.decomposed, args.work_dir, args.out, args.only, args.cap, args.max_seconds)
        return
    if args.command == "ksq-gated":
        measure_ksq(args.data_dir, args.vectors, args.out, args.usage_dir, args.max_seconds)
        return
    if args.command == "corroboration-file":
        print(json.dumps(measure_corroboration_file(args.out)["configs"], ensure_ascii=False, indent=1))
        return
    if args.command == "jev":
        measure_jev(args.only, args.out, args.usage_dir, args.max_seconds)
        return
    if args.command == "answers":
        measure_answers(args.cases, args.out, args.usage_dir, args.max_seconds, pairs=set(args.pair) if args.pair else None, cap=args.cap)
        return
    report = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    if args.only in (None, "class"):
        report["class_corpus"] = measure_class()
        print_class(report["class_corpus"])
    if args.only in (None, "tune"):
        report["allganize_tune"] = measure_tune()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
