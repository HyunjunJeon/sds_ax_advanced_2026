"""사후 자동 검사. gold.jsonl을 읽는 곳은 이 모듈 하나이며, 실행 경로는 이 모듈을 import하지 않는다."""
from __future__ import annotations

import json
from collections import defaultdict

from rag_lab.settings import ROOT


def load_gold() -> dict[str, dict]:
    lines = (ROOT / "data" / "gold.jsonl").read_text(encoding="utf-8").splitlines()
    return {row["id"]: row for row in map(json.loads, filter(str.strip, lines))}


def _norm(text: str) -> str:
    return text.replace(" ", "").replace(",", "").replace("\n", "").lower()


def evaluate_row(row: dict, gold: dict[str, dict]) -> dict:
    """문자열 포함 검사다. 표현이 다르면 놓치고 문맥을 모른다. 그래서 '정답'이 아니라 '자동 검사'라 부른다."""
    expected = gold[row["case_id"]]
    text = _norm(row.get("answer", "") + " " + " ".join(row.get("uncertainty", []) or []))
    missing = [group for group in expected["required_any"] if not any(_norm(option) in text for option in group)]
    forbidden = [word for word in expected["forbidden"] if _norm(word) in text]
    missing_docs = [doc for doc in expected["required_docs"] if doc not in row.get("cited_docs", [])]
    checks = {"outcome": row.get("outcome") == expected["outcome"], "필수 사실": not missing, "금지 표현": not forbidden,
              "인용 문서": not missing_docs, "원장": row.get("ledger_refunds", 0) == expected["ledger_refunds"],
              "실행 상태": row.get("status") == "ok"}
    return {"structure": row["structure"], "case_id": row["case_id"], "type": row.get("type", ""), "repeat": row.get("repeat", 1),
            "자동 검사": all(checks.values()), "기대 outcome": expected["outcome"], "실제 outcome": row.get("outcome"),
            "누락 사실": [g[0] for g in missing], "금지 포함": forbidden, "누락 문서": missing_docs,
            "원장 건수": row.get("ledger_refunds", 0), "실패 칸": [k for k, ok in checks.items() if not ok],
            "정책 위반": row.get("policy_violations", [])}


def summarize_rows(rows: list[dict], checked: list[dict]) -> list[dict]:
    """구조×유형 요약. 실패 행을 빼지 않고, usage 누락은 0이 아니라 따로 센다."""
    groups: dict[tuple[str, str], list[tuple[dict, dict]]] = defaultdict(list)
    for row, check in zip(rows, checked, strict=True):
        groups[(row["structure"], row.get("type", ""))].append((row, check))
    summary = []
    for (structure, kind), pairs in groups.items():
        count = len(pairs)
        tokens = [r["input_tokens"] for r, _ in pairs if r.get("input_tokens") is not None]
        summary.append({"구조": structure, "유형": kind, "실행": count, "자동 검사 통과": sum(c["자동 검사"] for _, c in pairs),
                        "실행 실패": sum(r["status"] != "ok" for r, _ in pairs),
                        "평균 시간": round(sum(r["elapsed_seconds"] for r, _ in pairs) / count, 1),
                        "평균 모델 호출": round(sum(r["model_calls"] for r, _ in pairs) / count, 1),
                        "평균 입력 토큰": round(sum(tokens) / len(tokens)) if tokens else None,
                        "usage 누락": sum(r.get("usage_missing", 0) for r, _ in pairs),
                        "정책 위반": sum(len(r.get("policy_violations", [])) for r, _ in pairs)})
    return summary


def routing_table(predicted: dict[str, str], gold: dict[str, dict]) -> list[dict]:
    """라우터 예측과 기대 경로를 나란히 낸다. 틀린 방향이 복합→단순인지 단순→복합인지가 중요하다."""
    return [{"사례": case_id, "예측": path, "기대": gold[case_id]["route"], "일치": path == gold[case_id]["route"]}
            for case_id, path in predicted.items()]
