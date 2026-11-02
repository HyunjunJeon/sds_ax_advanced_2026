"""04의 답변을 사례별로 실행하고 사후 평가한다. 09의 청킹/검색 변형 비교와 별개다.

조건은 아래 상수에서 바꾼다. 먼저 00→01→02→03→04를 완료하고 같은 namespace를
사용한다. 여러 턴은 한 세션, 다른 사례/반복은 새 세션이다. 실패도 즉시 JSONL에 남긴다.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from day02.agents.rag import ask
from day02.corpus import load_corpus, sha256
from day02.evidence import Budget
from day02.evaluation import evaluate_answer, summarize_answers
from day02.models import make_model
from day02.settings import Settings, write_json

CORPUS = "official-2026-10"
CASE_IDS = ["tech-blob", "tech-unannounced"]
REPEATS = 1
JUDGE = True
ROOT = Path(__file__).resolve().parents[1]


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    corpus = load_corpus(ROOT, CORPUS)
    cases = {r["id"]: r for r in jsonl(corpus.cases_path)}
    if not CASE_IDS or len(CASE_IDS) != len(set(CASE_IDS)) or not set(CASE_IDS) <= set(cases) or REPEATS < 1:
        raise ValueError("CASE_IDS와 REPEATS를 확인하세요.")
    settings = Settings.load()
    settings.require_model_key()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "outputs/answer-evaluation" / run_id
    out.mkdir(parents=True)
    turns = sum(len(cases[c].get("turns", [cases[c]["question"]])) for c in CASE_IDS) * REPEATS
    print(f"[비용 고지] {len(CASE_IDS)}사례 × {REPEATS}회, 후속 턴 포함 {turns}턴. "
          f"턴당 모델 최대 10회 + 독립 Judge 최대 {len(CASE_IDS) * REPEATS if JUDGE else 0}회.", flush=True)
    rows = []
    conditions = {
        "corpus": corpus.provenance(), "cases": CASE_IDS, "repeats": REPEATS,
        "model": settings.model, "judge": JUDGE,
        "cases_sha256": sha256(corpus.cases_path), "lock_sha256": sha256(ROOT.parent / "uv.lock"),
    }
    write_json(out / "conditions.json", conditions)
    for repeat in range(REPEATS):
        for case_id in CASE_IDS:
            case = cases[case_id]
            questions = case.get("turns", [case["question"]])
            for turn, question in enumerate(questions):
                budget = Budget()
                try:
                    run = ask(settings, question, entity=case["entity"], as_of=date.fromisoformat(case["as_of"]),
                              namespace=CORPUS, answer_format="auto",
                              session=f"eval-{run_id}-{case_id}-{repeat}", budget=budget)
                except Exception as exc:
                    run = {"status": "error", "error_type": type(exc).__name__,
                           "trace": budget.report()}
                row = {"case_id": case_id, "repeat": repeat, "turn": turn, "run": run,
                       "evaluation_eligible": turn == len(questions) - 1}
                if row["evaluation_eligible"]:
                    # 정답 파일은 Agent 실행 후에만 읽는다.
                    expected = {g["id"]: g for g in jsonl(corpus.gold_path)}[case_id]
                    row["evaluation"] = evaluate_answer(run, expected)
                    if JUDGE and run["status"] != "error":
                        try:
                            row["evaluation"] = evaluate_answer(run, expected, make_model(settings))
                        except Exception as exc:
                            # Judge 생성 실패도 Agent 결과와 함께 보존한다.
                            row["evaluation"]["judge_error"] = type(exc).__name__
                rows.append(row)
                with (out / "runs.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"{case_id}/{turn + 1}: {run['status']}", flush=True)
    summary = summarize_answers(rows)
    conditions["gold_sha256"] = sha256(corpus.gold_path)
    write_json(out / "conditions.json", conditions)
    write_json(out / "summary.json", summary)
    (out / "REPORT.md").write_text(
        "# 답변 사후 평가\n\n" +
        "검색 recall·인용 ID 유효성·의미 지지는 서로 다르다. Judge는 사람의 원문 검토를 대체하지 않는다.\n\n" +
        "draft 기준의 결과는 검수 전 잠정 지표다. 실패 행과 평가 누락을 함께 읽는다.\n\n" +
        "```json\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    print(f"결과: {out / 'REPORT.md'}")
    return 1 if summary["errors"] or any(r.get("evaluation", {}).get("judge_error") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
