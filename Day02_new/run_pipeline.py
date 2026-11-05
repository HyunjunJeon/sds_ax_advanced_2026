"""Day02_new 전체 파이프라인 실행기. 노트북 없이 Python 코드만으로 질문 하나를 끝까지 돌린다.

아키텍처는 노트북 04~06과 같다: 융합 검색(BM25+Dense) → 교차 인코더 재순위(원 질문 기준) →
2단계 판단 게이트 아키텍처(분해 게이트 → 미리 검색 → 빠른 답변 → 인용 관련성 게이트 →
추가 확인 게이트 → 검증 턴). 모델은 기본으로 OpenGateway의 deepseek/deepseek-v4.1-flash-ultrafast를
부르고(Anthropic Messages 호환 주소), --provider anthropic 을 주면 노트북과 같은 Anthropic Claude를 쓴다.
게이트 판정은 노트북과 같은 Decision API(rag_lab/decisions.py)가 맡는다.

사용법(저장소 루트에서):
    uv run --no-sync python Day02_new/run_pipeline.py
    uv run --no-sync python Day02_new/run_pipeline.py --question "서비스 크레딧 신청 기한은?" --mode two_phase
    uv run --no-sync python Day02_new/run_pipeline.py --provider anthropic --mode ask

검색 구성은 .env 파일(파일 시스템 설정)로 정한다. DAY02_RETRIEVAL_MODE=bm25 로 두면 로컬 임베딩
모델(e5, 약 470MB)을 적재하지 않고 형태소 검색만 쓰고, DAY02_RERANKER=off 면 재순위 모델(약 2.1GB)도
적재하지 않는다. DAY02_RERANKER=jev 는 재순위를 Decision API(Jev)가 맡는다(로컬 모델 없음).
--mode fs 는 검색 도구 대신 에이전트의 내장 파일 도구(ls·glob·grep·read_file)로 outputs/fs_corpus
트리를 뒤져 답하는 경로다. 실행 인자 --retrieval, --rerank 가 .env 값보다 우선한다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import uuid4

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemPermission
from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from rag_lab.agent import allowlist_middleware, ask, write_run_record  # noqa: E402
from rag_lab.corpus import Scope, load_cases, load_corpus  # noqa: E402
from rag_lab.decisions import Noul, make_decider  # noqa: E402
from rag_lab.evidence import Budget  # noqa: E402
from rag_lab.evaluation import load_gold  # noqa: E402
from rag_lab.gates import needs_follow_up  # noqa: E402
from rag_lab.phases import ask_two_phase  # noqa: E402
from rag_lab.retrieval import Retriever  # noqa: E402
from rag_lab.settings import announce, make_embeddings, make_reranker  # noqa: E402

# 모델 공급자 두 곳. 주소는 코드에 고정한다(셸의 ANTHROPIC_BASE_URL 같은 값으로 키가 다른 곳에 가지 않게).
PROVIDERS = {
    "opengateway": {"base_url": "https://apis.opengateway.ai", "key_env": "OPENGATEWAY_API_KEY",
                    "model": "deepseek/deepseek-v4.1-flash-ultrafast", "label": "OpenGateway DeepSeek"},
    "anthropic": {"base_url": "https://api.anthropic.com", "key_env": "ANTHROPIC_API_KEY",
                  "model": "claude-sonnet-5-5", "label": "Anthropic Claude"},
}

# 검색 방식. bm25 는 임베딩 없이 형태소 검색만 쓴다(나머지 셋은 로컬 임베딩 모델이 필요하다).
RETRIEVAL_MODES = ("bm25", "dense", "hybrid", "fusion")
RERANK_CHOICES = ("on", "off", "jev")

# Jev 재순위가 한 번의 judge에 묶는 후보 수. 인용 게이트(rag_lab/gates.py)처럼 Noul 여러 개를 한 번에 묻는다.
_JEV_BATCH = 20
_RELEVANT_TRUE = "The passage states something the question asks about or helps answer it."
_RELEVANT_FALSE = "The passage is about something else: another topic, navigation, boilerplate, or a table of contents."


def retrieval_plan(values: dict[str, str | None], cli_mode: str | None, cli_rerank: str | None) -> tuple[str, str]:
    """검색 구성을 정한다. .env의 DAY02_RETRIEVAL_MODE/DAY02_RERANKER가 기본이고 실행 인자가 우선이다."""
    mode = (cli_mode or values.get("DAY02_RETRIEVAL_MODE") or "fusion").strip().lower()
    rerank = (cli_rerank or values.get("DAY02_RERANKER") or "on").strip().lower()
    if mode not in RETRIEVAL_MODES:
        raise RuntimeError(f"DAY02_RETRIEVAL_MODE는 {', '.join(RETRIEVAL_MODES)} 중 하나여야 합니다: {mode!r}")
    if rerank not in RERANK_CHOICES:
        raise RuntimeError(f"DAY02_RERANKER는 {', '.join(RERANK_CHOICES)} 중 하나여야 합니다: {rerank!r}")
    return mode, rerank


class JevReranker:
    """교차 인코더 대신 Decision API(Jev)로 후보별 관련 확률을 매기는 재순위기. rag_lab.pipeline.Reranker 프로토콜을 따른다.

    후보마다 Noul 하나를 만들어 judge 한 번에 묻는다(인용 게이트와 같은 방식). 로컬 모델을 적재하지 않아
    시작이 빠르다. 답이 없는 후보가 있으면 예외를 낸다 — retrieve()가 rerank-failed 경고를 남기고
    1차 검색 순서로 돌아간다. 판단 예산(Budget.max_decision_calls)과는 따로 세니 호출 수를 calls로 본다."""

    def __init__(self, decider):
        self.decider = decider
        self.calls = 0
        self.questions = 0

    def score(self, query: str, texts: list[str]) -> list[float]:
        scores: list[float] = []
        state = f"User question: {json.dumps(query, ensure_ascii=False)}"
        for start in range(0, len(texts), _JEV_BATCH):
            batch = texts[start:start + _JEV_BATCH]
            nouls = [Noul(f"chunk_{start + index}",
                          "Does the passage below help answer the user question?\n"
                          f"Passage: {json.dumps(text[:1500], ensure_ascii=False)}",
                          _RELEVANT_TRUE, _RELEVANT_FALSE)
                     for index, text in enumerate(batch)]
            self.calls += 1
            self.questions += len(batch)
            judgment = self.decider.judge(state, nouls)
            for noul in nouls:
                probability = judgment.verdicts[noul.name].probability
                if probability is None:
                    raise RuntimeError(f"jev rerank: 판단이 답하지 않은 후보가 있습니다({noul.name})")
                scores.append(probability)
        return scores


# 파일 시스템 코퍼스: 임베딩 없이 에이전트의 내장 파일 도구로 뒤지는 문서 트리. Agent Memory 프로젝트처럼
# 뿌리에 색인(INDEX.md), 아래에 고객/도메인 폴더, 파일마다 메타데이터 frontmatter를 둔다.
FS_CORPUS = ROOT / "outputs" / "fs_corpus"

FS_AGENT_PROMPT = """당신은 사내 문서 파일 시스템에서 답을 찾는 한국어 질의응답 에이전트입니다.
문서 트리의 뿌리에 INDEX.md가 있습니다. 먼저 INDEX.md를 읽어 문서 목록을 파악하세요.
질문의 고객은 {entity}이고 기준일은 {as_of}입니다. 다른 고객의 문서와 이 기준일에 적용되지 않는 문서
(상태가 approved 가 아님, 적용 시작일이 기준일 이후, 적용 종료일이 기준일 이하)은 근거로 쓰지 마세요.
각 문서 파일의 머리 frontmatter에 고객·버전·상태·적용 기간·담당자가 있습니다. glob과 grep으로 후보를
좁히고 read_file로 원문을 읽으세요. 답할 때 문서 경로와 근거 문장을 인용하고, 문서에 없는 내용은 없다고 답하세요."""

FS_AGENT_PROMPT_OPEN = """당신은 문서 파일 시스템에서 답을 찾는 한국어 질의응답 에이전트입니다.
문서 트리의 뿌리에 INDEX.md가 있습니다. 먼저 INDEX.md를 읽어 문서 목록을 파악하세요.
glob과 grep으로 후보를 좁히고 read_file로 원문을 읽으세요. 답할 때 문서 경로와 근거 문장을 인용하고,
문서에 없는 내용은 없다고 답하세요."""


def build_fs_corpus(target: Path = FS_CORPUS) -> Path:
    """코퍼스(catalog.json)를 파일 시스템 트리로 편다. 다시 실행하면 트리를 지우고 다시 만든다."""
    documents = dict(sorted(load_corpus().items()))
    if target.exists():
        shutil.rmtree(target)
    rows = []
    for doc in documents.values():
        folder = target / doc.entity / doc.domain
        folder.mkdir(parents=True, exist_ok=True)
        valid_until = doc.valid_until.isoformat() if doc.valid_until else "없음(계속)"
        frontmatter = {"doc_id": doc.doc_id, "title": doc.title, "entity": doc.entity, "domain": doc.domain,
                       "version": doc.version, "status": doc.status, "valid_from": doc.valid_from.isoformat(),
                       "valid_until": valid_until, "owner": doc.owner, "source": doc.source}
        # 값은 JSON 문자열로 감싸 YAML 스칼라를 안전하게 지킨다.
        header = "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in frontmatter.items()) + "---\n\n"
        path = folder / f"{doc.doc_id}.md"
        path.write_text(header + doc.text, encoding="utf-8")
        rows.append(f"| `{doc.doc_id}.md` | {doc.title} | {doc.entity} | {doc.domain} | {doc.version} | "
                    f"{doc.status} | {doc.valid_from.isoformat()} ~ {valid_until} | {doc.owner} | `{folder.relative_to(target)}` |")
    index = ["# 사내 문서 색인 (INDEX)", "",
             "폴더는 `고객/도메인` 두 단계다. 파일 이름은 문서 ID(doc_id)와 같다.",
             "후보 좁히기 예: 전체에서 단어 찾기 `grep -i \"기한\"`, 한 고객의 문서만 보기 `glob 알파/**/*.md`.",
             "각 파일 머리 frontmatter에 고객·버전·상태·적용 기간·담당자가 있으니 read_file로 확인하고,",
             "상태가 approved 이고 기준일이 적용 기간 안에 드는 버전만 근거로 쓴다.", "",
             "| 파일 | 제목 | 고객 | 도메인 | 버전 | 상태 | 적용 기간 | 담당자 | 폴더 |",
             "|---|---|---|---|---|---|---|---|---|", *rows, ""]
    (target / "INDEX.md").write_text("\n".join(index), encoding="utf-8")
    return target


def _fs_sections(path: Path) -> list[str]:
    """파일 본문(frontmatter 뒤)을 나눈다. '## ' 제목이 있면 제목 기준(section_chunks와 같은 규칙),
    없으면(올거나이즈 쪽처럼) Jev 판독 상한과 같은 1500자 고정 창으로 자른다."""
    text = path.read_text(encoding="utf-8")
    body = text.split("---\n", 2)[2] if text.startswith("---\n") else text
    if not any(line.startswith("## ") for line in body.splitlines()):
        return [body[start:start + 1500].strip() for start in range(0, len(body), 1500)
                if body[start:start + 1500].strip()]
    sections, current = [], []
    for line in body.splitlines(keepends=True):
        if line.startswith("## ") and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))
    return [section for section in sections if section.strip()]


def _frontmatter(path: Path) -> dict:
    """파일 머리 frontmatter를 읽는다. 값은 JSON 문자열로 썼으니 그대로 파싱하고 실패하면 생 문자열로 둔다."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    fields: dict[str, object] = {}
    for line in text.split("---\n", 2)[1].splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        try:
            fields[key.strip()] = json.loads(value.strip())
        except ValueError:
            fields[key.strip()] = value.strip().strip('"')
    return fields


def _applies(metadata: dict, scope: Scope) -> bool:
    """frontmatter 메타데이터가 범위에 들어오는지 본다. rag_lab.corpus.Document.applies와 같은 규칙이다."""
    if metadata.get("status") != "approved":
        return False
    if metadata.get("entity") not in {scope.entity, "공통"}:
        return False
    try:
        if date.fromisoformat(str(metadata.get("valid_from", ""))) > scope.as_of:
            return False
        until = metadata.get("valid_until")
        if until and str(until) not in {"없음(계속)", ""} and date.fromisoformat(str(until)) <= scope.as_of:
            return False
    except ValueError:
        return False
    return True


def _fs_candidates(fs_root: Path, scope: Scope | None = None) -> list[tuple[Path, str]]:
    """코퍼스 트리의 (파일, 발췌) 후보. scope가 있으면 frontmatter 메타데이터로 범위를 먼저 건다(없으면 전체)."""
    candidates = []
    for path in sorted(fs_root.rglob("*.md")):
        if path.name == "INDEX.md" or (scope is not None and not _applies(_frontmatter(path), scope)):
            continue
        candidates.extend((path, section) for section in _fs_sections(path))
    return candidates


# 커버리지 판정: 고른 발췌가 답에 필요한 정보를 실제로 담고 있는지 묻는다(관련 있지만 불충분한 경우를 가린다).
_COVERAGE_TRUE = "The collected passages state the specific fact or facts the question asks for."
_COVERAGE_FALSE = ("The passages are related to the topic but do not state what the question asks, "
                   "or the question needs information that is not present.")

_FS_JEV_PROMPT = """당신은 사내 문서에서 모은 발췌로 답하는 한국어 질의응답 도우미입니다.
아래 발췌에 없는 내용은 쓰지 마세요. 답할 때 각 근거의 파일 경로와 원문 문장을 인용하세요.
발췌에 답이 없으면 없다고 답하세요.
근거 문서의 버전과 적용 기준일을 답에 밝히고, 선택한 발췌에 아직 적용되지 않은 추가 약정이나 다른 버전의 같은 조항이 언급되어 있으면 그 내용과 적용 시점을 한 줄로 덧붙이세요."""


def run_fs_agent(model, question: str, scope: Scope | None, fs_root: Path) -> dict:
    """LLM이 내장 파일 도구(ls·glob·grep·read_file)로 트리를 뒤지는 에이전트. fs 모드와 fs_jev의 폴백이 쓴다.

    예산 초과 등 실행 중 실패는 올리지 않고 status="error" 기록으로 돌려 데이터셋 루프가 멈추지 않게 한다
    (rag_lab/phases.py와 같은 규칙). 큰 트리(올거나이즈 1,008쪽)에서는 도구 예산을 넉넉히 준다."""
    budget = Budget(max_model_calls=8, max_tool_calls=60)
    system = (FS_AGENT_PROMPT.format(entity=scope.entity, as_of=scope.as_of.isoformat()) if scope
              else FS_AGENT_PROMPT_OPEN)
    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=str(fs_root), virtual_mode=True),
        middleware=allowlist_middleware(budget, frozenset({"ls", "read_file", "glob", "grep"})),
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        system_prompt=system,
    )
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config={"recursion_limit": 40})
    except Exception as error:  # BudgetExceeded 포함. 실패 행이 사라지지 않고 기록으로 남게 한다.
        return {"tools": [], "answer": "", "counts": budget.report()["counts"], "status": "error",
                "errors": [f"{type(error).__name__}: {error}"]}
    tools = [call["name"] for message in result["messages"] for call in getattr(message, "tool_calls", [])]
    answer = next((message.text for message in reversed(result["messages"]) if message.type == "ai" and message.text), "")
    return {"tools": tools, "answer": answer, "counts": budget.report()["counts"], "status": "answered"}


def _diversify(ranked: list[tuple[float, tuple[Path, str]]], top_k: int, per_file_cap: int | None) -> list[tuple[float, tuple[Path, str]]]:
    """점수 순서를 지키되 한 파일이 후보를 독점하지 못하게 한다(per_file_cap). None이면 그대로 자른다."""
    if per_file_cap is None:
        return ranked[:top_k]
    picked, per_file = [], {}
    for score, (path, section) in ranked:
        if len(picked) >= top_k:
            break
        if per_file.get(path, 0) < per_file_cap:
            picked.append((score, (path, section)))
            per_file[path] = per_file.get(path, 0) + 1
    return picked


def run_fs_jev(model, decider, question: str, scope: Scope | None, fs_root: Path, *, top_k: int = 6,
               per_file_cap: int | None = None, coverage_floor: float = 0.5, stage1_files: int | None = None,
               verbose: bool = True) -> dict:
    """Jev 파일 탐색 한 턴: (선택) 1단계 파일 요약 점수 → 발췌 선택 → 커버리지 판정 → 모델 답변 → 추가 확인 게이트.

    stage1_files를 주면 파일 단위 요약으로 먼저 좁힌 뒤(에이전트가 INDEX.md를 먼저 읽는 것과 같은 순서)
    그 파일들의 발췌만 점수 매긴다 — 대규모 코퍼스에서 판단 호출을 크게 줄인다. 커버리지가 못 미치면 fs
    에이전트로 폴백한다. gold를 읽지 않는다 — 채점은 호출자가 모든 실행이 끝난 뒤에 한다."""
    candidates = _fs_candidates(fs_root, scope)
    selector = JevReranker(decider)

    def _select(cands: list[tuple[Path, str]]) -> tuple[list, float | None]:
        """후보에서 top_k 발췌를 고르고 커버리지를 판정한다. 판정 점수는 gates에 남긴다."""
        scores = selector.score(question, [section for _, section in cands])
        ranked = sorted(zip(scores, cands), key=lambda pair: -pair[0])
        top = _diversify(ranked, top_k, per_file_cap)
        evidence = [section[:1500] for _, (_, section) in top]
        coverage_noul = Noul("coverage",
                             "Do the collected passages below contain the information needed to answer the user question?\n"
                             f"Question: {json.dumps(question, ensure_ascii=False)}\n"
                             f"Passages: {json.dumps(evidence, ensure_ascii=False)}",
                             _COVERAGE_TRUE, _COVERAGE_FALSE)
        covered = decider.judge("Judge whether the collected evidence answers the question.",
                                [coverage_noul]).verdicts["coverage"].probability
        return top, covered

    selection_mode = "flat"
    if stage1_files:
        by_doc: dict[Path, list[str]] = {}
        for path, section in candidates:
            by_doc.setdefault(path.parent, []).append(section)
        summaries = [f"문서: {doc.name}\n{next((s for s in sections if len(s) >= 80), sections[0])[:400]}"
                     for doc, sections in by_doc.items()]
        doc_scores = selector.score(question, summaries)
        top_docs = {doc for _, doc in sorted(zip(doc_scores, by_doc), key=lambda pair: -pair[0])[:stage1_files]}
        narrowed = [(path, section) for path, section in candidates if path.parent in top_docs]
        if verbose:
            print(f"  1단계: 문서 {len(by_doc)}개 → 상위 {len(top_docs)}개로 좁힘(발췌 {len(narrowed)}개)")
        top, covered = _select(narrowed)
        selection_mode = "stage1"
        if covered is None or covered < coverage_floor:
            # 2단계에서 놓친 경우 전체 발췌로 다시 시도한다(문서 좁힘 → 전체 → 에이전트 순서).
            top, covered = _select(candidates)
            selection_mode = "flat_retry"
            if verbose:
                print("    1단계 선택이 커버리지에 못 미쳐 전체 발췌로 다시 골랐습니다.")
    else:
        top, covered = _select(candidates)
    if verbose:
        for score, (path, _) in top[:4]:
            print(f"    {score:.2f}  {path.name}")
        if covered is not None:
            print(f"    커버리지 P={covered:.2f}")

    gates = [{"gate": "coverage", "probability": covered, "selection": selection_mode}]
    fallback = covered is None or covered < coverage_floor
    follow = None
    errors: list[str] = []
    status = "answered"
    if fallback:
        if verbose:
            print("    커버리지 불충분 → 파일 탐색 에이전트 폴백")
        run = run_fs_agent(model, question, scope, fs_root)
        answer, model_calls = run["answer"], run["counts"].get("model", 0)
        status = "fallback" if run.get("status", "answered") != "error" else "error"
        errors = run.get("errors", [])
    else:
        passages = [{"path": str(path.relative_to(fs_root)), "text": section}
                    for path, sections in _group_by_file(top).items() for section in sections]
        payload = {"question": question, "passages": passages}
        if scope:
            payload.update(entity=scope.entity, as_of=scope.as_of.isoformat())
        answer = model.invoke([{"role": "system", "content": _FS_JEV_PROMPT},
                               {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]).text
        model_calls = 1
        follow = needs_follow_up(decider, question, answer)
        gates.append(asdict(follow))
        if follow.decision:  # 추가 확인이 필요하면 한 번만 고쳐 쓴다.
            answer = model.invoke([{"role": "system", "content": _FS_JEV_PROMPT},
                                   {"role": "user", "content": json.dumps({**payload,
                                       "지시": "앞선 답에서 부족하거나 불확실한 부분을 발췌 안에서 다시 확인해 답을 다시 쓰세요."},
                                       ensure_ascii=False)}]).text
            model_calls = 2
    scope_json = {"entity": scope.entity, "as_of": scope.as_of.isoformat()} if scope else {"corpus": str(fs_root.name)}
    return {"run_id": uuid4().hex, "mode": "fs_jev", "question": question, "scope": scope_json,
            "model": getattr(model, "model", type(model).__name__), "status": status,
            "selection": selection_mode, "errors": errors,
            "gates": gates, "fallback": fallback, "jev_judge_calls": selector.calls + 2,
            "model_calls": model_calls,
            "selected": [{"path": str(path.relative_to(fs_root)), "doc_id": str(_frontmatter(path).get("doc_id", path.stem)),
                          "score": round(score, 3)} for score, (path, _) in top],
            "answer_text": answer}


def _group_by_file(top: list[tuple[float, tuple[Path, str]]]) -> dict[Path, list[str]]:
    grouped: dict[Path, list[str]] = {}
    for _, (path, section) in top:
        grouped.setdefault(path, []).append(section)
    return grouped


def score_dataset(rows: list[dict], gold: dict[str, dict]) -> list[dict]:
    """실행이 끝난 행에 정답표를 붙인다. 기대 문서가 사례 범위 밖이면 구조적으로 못 찾으므로 따로 표시한다
    (docs/retrieval_benchmarks.md의 '범위 안/밖' 구분과 같은 기준이다). 범위 없는 코퍼스(올거나이즈)는 전부 범위 안이다."""
    corpus = load_corpus()
    for row in rows:
        entry = gold.get(row["case_id"], {})
        expected = set(entry.get("expected_docs") or [])
        if row["scope"].get("entity"):
            scope = Scope(row["scope"]["entity"], date.fromisoformat(row["scope"]["as_of"]))
            out_of_scope = {doc for doc in expected if doc in corpus and not corpus[doc].applies(scope)}
        else:
            out_of_scope = set()
        in_scope = expected - out_of_scope
        selected = {item.get("doc_id") or Path(item["path"]).stem for item in row.get("selected", [])}
        answer = row.get("answer_text") or ""
        cited = {doc for doc in in_scope if doc in answer or f"{doc}.md" in answer
                 or (doc.split("#")[0][:-4] if doc.split("#")[0].lower().endswith(".pdf") else doc) in answer}
        row["expected_docs"] = sorted(expected)
        row["expected_out_of_scope"] = sorted(out_of_scope)
        row["abstain_expected"] = bool(entry.get("abstain"))
        row["hit_all"] = (expected <= selected) if expected else None
        row["hit_any"] = bool(expected & selected) if expected else None
        row["hit_in_scope"] = (in_scope <= selected) if in_scope else None
        row["cited_any"] = bool(cited) if in_scope else None
    return rows


FS_CORPUS_ALLGANIZE = ROOT / "outputs" / "fs_corpus_allganize"


def _slug(name: str) -> str:
    """파일 이름을 폴더 이름으로 쓸 수 있게 다듬는다(확장자 제거, 경로 문자 제거, 60자)."""
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", re.sub(r"\.pdf$", "", name)).strip("_")
    return cleaned[:60] or "doc"


def build_fs_corpus_allganize(target: Path = FS_CORPUS_ALLGANIZE) -> Path:
    """올거나이즈 PDF를 '쪽 = 파일' 트리로 편다. 글자층 뒤에 vision_pages.json의 판독 글자를 덧붙이고
    공백 연속은 하나로 줄인다(measure.py의 page_documents와 같은 전처리). 빈 쪽은 파일을 만들지 않는다."""
    from benchmarks.allganize import load_pages

    reading_path = ROOT / "outputs/benchmarks/allganize/vision_pages.json"
    reading = json.loads(reading_path.read_text(encoding="utf-8")) if reading_path.is_file() else {}
    if target.exists():
        shutil.rmtree(target)
    rows, pages_written = [], 0
    for page in load_pages():
        extra = reading.get(f"{page.file}#{page.page_no}")
        body = re.sub(r"[ \t]+", " ", page.text if extra is None else page.text + "\n" + extra).strip()
        if not body:
            continue
        folder = target / _slug(page.file)
        folder.mkdir(parents=True, exist_ok=True)
        frontmatter = {"doc_id": f"{page.file}#{page.page_no}", "file_name": page.file, "page_no": page.page_no}
        header = "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
                                   for key, value in frontmatter.items()) + "---\n\n"
        (folder / f"p{page.page_no:03d}.md").write_text(header + body, encoding="utf-8")
        pages_written += 1
        rows.append((page.file, page.page_no))
    files = sorted({file for file, _ in rows})
    index = ["# 올거나이즈 문서 색인 (쪽 = 파일)", "",
             f"문서 파일 {len(files)}개, 쪽 {pages_written}개. 폴더는 원본 PDF 이름, 파일은 `p<쪽번호>.md`다.",
             "각 파일 머리 frontmatter의 `doc_id`가 `원본파일#쪽번호`다.", "",
             "| 문서(PDF) | 쪽 수 |", "|---|---:|"]
    for name in files:
        index.append(f"| {name} | {sum(1 for f, _ in rows if f == name)} |")
    (target / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return target


def make_runner_model(provider: str, values: dict[str, str | None]) -> ChatAnthropic:
    """고른 공급자의 모델을 만든다. 키가 비어 있으면 이름만 대고 멈춘다(재시도 없음, 120초 상한)."""
    spec = PROVIDERS[provider]
    api_key = (values.get(spec["key_env"]) or "").strip()
    if not api_key:
        raise RuntimeError(f"{spec['key_env']}가 미설정입니다. Day02_new/.env.example을 .env로 복사한 뒤 "
                           "본인의 키를 직접 채우세요.")
    return ChatAnthropic(model=spec["model"], api_key=api_key, base_url=spec["base_url"],
                         reasoning_effort="medium", max_tokens=16000, timeout=120.0, max_retries=0)


def summarize(record: dict) -> None:
    """실행 기록의 요약을 출력한다. 답변은 앞부분만, 키 값은 어디에도 남기지 않는다."""
    print(f"  status={record['status']} | 검증={record['validation']} | 지지검토={record['support_review']}")
    print(f"  모델 호출={record['trace']['counts'].get('model', 0)}회 | 판단 호출={record['trace']['counts'].get('decision', 0)}회"
          f" | 읽은 Skill={record['loaded_skills'] or '없음'}")
    if record["errors"]:
        print(f"  errors={record['errors'][:3]}")
    if record.get("gates") is not None:
        for gate in record["gates"]:
            probability = f"P={gate['probability']:.2f}" if gate["probability"] is not None else "P=없음"
            print(f"  게이트 {gate['gate']}: {probability} (문턱값 {gate['threshold']}) -> {gate['decision']}")
    if record.get("phases"):
        print("  단계: " + " → ".join(f"{phase['name']}({phase['seconds']}초)" for phase in record["phases"]))
    print(f"  실행 기록: {ROOT / 'outputs' / 'runs' / (record['run_id'] + '.json')}")
    if record["markdown"]:
        print("  답변 앞부분:")
        for line in record["markdown"].splitlines()[:12]:
            print(f"    {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Day02_new 전체 파이프라인 실행기")
    parser.add_argument("--question", default="", help="질문. 비우면 data/cases.jsonl의 첫 사례를 쓴다.")
    parser.add_argument("--entity", default="알파", help="고객(entity). 기본 알파.")
    parser.add_argument("--as-of", default="2026-09-08", help="기준일(as_of, YYYY-MM-DD). 기본 2026-09-08.")
    parser.add_argument("--mode", choices=["ask", "two_phase", "fs", "fs_jev", "both"], default="both", help="실행할 단계.")
    parser.add_argument("--provider", choices=list(PROVIDERS), default="opengateway", help="모델 공급자.")
    parser.add_argument("--retrieval", choices=list(RETRIEVAL_MODES), default=None,
                        help="검색 방식. 비우면 .env의 DAY02_RETRIEVAL_MODE(기본 fusion).")
    parser.add_argument("--rerank", choices=list(RERANK_CHOICES), default=None,
                        help="재순위: on(로컬 교차 인코더)·off·jev(Decision API). 비우면 .env의 DAY02_RERANKER(기본 on).")
    parser.add_argument("--dataset", action="store_true",
                        help="cases.jsonl 전 사례를 --mode 경로(fs_jev|fs)로 돌려 품질을 잰다. 실패 행도 모두 남긴다.")
    parser.add_argument("--limit", type=int, default=0, help="데이터셋에서 앞 N사례만(0이면 전부).")
    parser.add_argument("--repeats", type=int, default=2, help="사례당 반복 수(기본 2).")
    parser.add_argument("--top-k", type=int, default=6, help="fs_jev가 Jev 점수로 고를 발췌 수(기본 6).")
    parser.add_argument("--per-file-cap", type=int, default=None,
                        help="fs_jev 선택에서 한 파일의 발췌 상한(다양성 확보). 기본 제한 없음.")
    parser.add_argument("--cases-file", default=None, help="사례 JSONL 경로(기본 data/cases.jsonl).")
    parser.add_argument("--gold-file", default=None, help="정답표 JSONL 경로(기본 data/gold.jsonl). 측정이 끝난 뒤에만 읽는다.")
    parser.add_argument("--corpus", choices=["business", "allganize"], default="business",
                        help="fs 코퍼스 원본. business는 catalog+cases 파일, allganize는 올거나이즈 PDF(쪽=파일, tune/hold 분할).")
    parser.add_argument("--split", choices=["tune", "hold"], default="tune",
                        help="allganize 분할. tune은 조정용, hold는 구성을 고정한 뒤 한 번만 읽는다.")
    parser.add_argument("--stage1-files", type=int, default=None,
                        help="2단계 선택: 1단계에서 파일 요약 점수로 좁힐 파일 수(예: 5). 기본은 전체 발췌를 한 번에 점수 매긴다.")
    args = parser.parse_args()

    # [1단계] 이 폴더의 .env만 읽는다. 키는 설정됨/미설정만 확인하고 값을 출력하지 않는다.
    values = dotenv_values(ROOT / ".env")
    case = load_cases()[0]
    question = args.question.strip() or case["question"]
    scope = Scope(args.entity, date.fromisoformat(args.as_of))
    spec = PROVIDERS[args.provider]
    print(f"질문: {question}")
    print(f"범위: 고객={scope.entity} 기준일={scope.as_of} | 모델={spec['label']}({spec['model']})")

    # [2단계] 모델·판정 API·검색 부품을 만든다. fs 모드는 검색 스택을 아예 만들지 않고(로컬 모델 미적재)
    # bm25 모드는 로컬 임베딩을, 재순위 off/jev는 로컬 재순위 모델을 적재하지 않는다.
    model = make_runner_model(args.provider, values)
    retriever = reranker = decider = None
    if args.mode == "fs":
        print("검색: 파일 시스템 탐색(내장 파일 도구 ls·glob·grep·read_file) | 재순위: 해당 없음")
    elif args.mode == "fs_jev":
        decider = make_decider()  # 판단 API가 파일 선택·커버리지·추가 확인을 맡는다.
        print("검색: 파일 시스템 + Jev 선택(에이전트 왕복 없음) | 재순위: Jev(Decision API)")
    else:
        decider = make_decider()  # Decision API 키가 없으면 한국어 안내와 함께 여기서 멈춘다.
        mode, rerank = retrieval_plan(values, args.retrieval, args.rerank)
        embeddings = make_embeddings() if mode != "bm25" else None
        retriever = Retriever(load_corpus(), embeddings=embeddings, mode=mode)
        reranker = {"on": lambda: make_reranker(), "off": lambda: None, "jev": lambda: JevReranker(decider)}[rerank]()
        rerank_label = {"on": "켬(로컬 교차 인코더)", "off": "끔", "jev": "Jev(Decision API)"}[rerank]
        print(f"검색: {mode}({'로컬 임베딩 사용' if embeddings else '로컬 임베딩 없음'}) | 재순위: {rerank_label}")

    if args.dataset:
        # [3단계] 데이터셋 평가: cases.jsonl 사례마다 --mode 경로(fs_jev|fs)를 --repeats번 돌리고,
        # 실행이 모두 끝난 뒤에만 정답표(load_gold)를 붙여 채점한다. 실패 행은 지우지 않는다.
        if args.mode not in {"fs_jev", "fs"}:
            raise RuntimeError("--dataset 는 --mode fs_jev 또는 fs 와 함께 씵니다. (--mode fs_jev 권장)")
        if args.corpus == "allganize":
            from benchmarks.allganize import load_cases as load_allganize
            usable, _ = load_allganize()
            picked = [case for case in usable if case.split == args.split]
            picked = picked[:args.limit] if args.limit else picked
            cases = [{"id": case.case_id, "type": case.context_type, "question": case.question,
                      "scope": None, "expected": [f"{case.file}#{case.page_no}"]} for case in picked]
            fs_root = build_fs_corpus_allganize()
            gold_map = {row["id"]: {"expected_docs": row["expected"], "abstain": False} for row in cases}
        else:
            cases_path = Path(args.cases_file) if args.cases_file else None
            loaded = load_cases(cases_path)
            cases = [{"id": case["id"], "type": case["type"], "question": case["question"],
                      "scope": Scope(case["entity"], date.fromisoformat(case["as_of"])), "expected": None}
                     for case in (loaded[:args.limit] if args.limit else loaded)]
            fs_root = build_fs_corpus()
            gold_map = None  # business 정답표는 실행이 모두 끝난 뒤에만 읽는다(아래 score_dataset 직전).
        runs = len(cases) * args.repeats
        per_run_models = 2 if args.mode == "fs_jev" else 8
        announce(f"데이터셋 평가({args.mode}/{args.corpus}, {len(cases)}사례 x {args.repeats}반복)",
                 model_calls=per_run_models * runs)
        sections = len(_fs_candidates(fs_root, cases[0]["scope"] if cases else None))
        if args.mode == "fs_jev":
            batches = -(-sections // _JEV_BATCH) + 2
            print(f"각 실행은 Decision API 호출도 사용합니다(1단계 없이는 발췌 {sections}개 → 판단 약 {batches}회,"
                  f" 커버리지·추가확인 포함). --stage1-files 로 줄일 수 있습니다.")
        rows = []
        for case in cases:
            case_scope = case["scope"]
            for repeat in range(1, args.repeats + 1):
                started = time.perf_counter()
                if args.mode == "fs_jev":
                    record = run_fs_jev(model, decider, case["question"], case_scope, fs_root,
                                        top_k=args.top_k, per_file_cap=args.per_file_cap,
                                        stage1_files=args.stage1_files, verbose=False)
                else:
                    run = run_fs_agent(model, case["question"], case_scope, fs_root)
                    scope_json = ({"entity": case_scope.entity, "as_of": case_scope.as_of.isoformat()}
                                  if case_scope else {"corpus": fs_root.name})
                    record = {"run_id": uuid4().hex, "mode": "fs", "question": case["question"], "scope": scope_json,
                              "model": getattr(model, "model", type(model).__name__),
                              "status": run.get("status", "answered"), "errors": run.get("errors", []),
                              "gates": [], "fallback": False, "jev_judge_calls": 0,
                              "model_calls": run["counts"].get("model", 0), "selected": [], "tools": run["tools"],
                              "answer_text": run["answer"]}
                record.update(case_id=case["id"], type=case["type"], repeat=repeat,
                              seconds=round(time.perf_counter() - started, 3))
                write_run_record(record)
                rows.append(record)
                picked = ",".join(str(item.get("doc_id") or Path(item["path"]).stem)
                                  for item in record["selected"][:3])
                follow = next((g for g in record["gates"] if g["gate"] == "follow_up"), None)
                follow_mark = "-" if follow is None else ("열림" if follow["decision"] else "닫힘")
                print(f"  {case['id'][:26]:26} r{repeat} {record['status']:8} {record['seconds']:6.1f}초"
                      f" 모델{record['model_calls']} 판단{record['jev_judge_calls']} 추가확인{follow_mark} [{picked}]")
        if gold_map is None:
            gold_map = load_gold(Path(args.gold_file) if args.gold_file else None)  # 이제 실행이 끝났으니 읽는다.
        rows = score_dataset(rows, gold_map)
        out = ROOT / "outputs" / "runs" / f"dataset_{args.mode}_{args.corpus}_{time.strftime('%Y%m%dT%H%M%S')}.jsonl"
        with out.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        scored = [row for row in rows if row["hit_all"] is not None]
        inscope = [row for row in rows if row["hit_in_scope"] is not None]
        outside = [row for row in rows if row["expected_out_of_scope"]]
        abstain = [row for row in rows if row["abstain_expected"]]
        print(f"\n== 데이터셋 평가 요약 ({len(rows)}행, 결과: {out.name}) ==")
        print(f"  범위 안 기대 문서 있는 행 {len(inscope)}: hit_in_scope {sum(r['hit_in_scope'] for r in inscope)}/{len(inscope)}"
              f" | 답변 인용 {sum(r['cited_any'] for r in inscope)}/{len(inscope)}")
        misses = [r for r in inscope if not r["hit_in_scope"]]
        if misses:
            print("  hit_in_scope 빠진 행:")
            for row in misses:
                print(f"    {row['case_id']} r{row['repeat']}({row['type']}) 기대={row['expected_docs']}"
                      f" 선택={[Path(i['path']).stem for i in row['selected']]}")
        if outside:
            print(f"  범위 밖 기대(구조적으로 못 찾음) {len(outside)}행: "
                  + ", ".join(f"{r['case_id']}" for r in outside) + " — 답이 범위 밖임을 말하는지 사람이 확인")
        if abstain:
            print(f"  보류 기대 행 {len(abstain)}: " + ", ".join(f"{r['case_id']} r{r['repeat']}" for r in abstain)
                  + " (답이 '없음'인지 사람이 확인)")
        print(f"  상태: answered {sum(r['status'] == 'answered' for r in rows)} | fallback {sum(r['fallback'] for r in rows)}"
              f" | 평균 {sum(r['seconds'] for r in rows) / len(rows):.1f}초"
              f" | 모델 합 {sum(r['model_calls'] for r in rows)}회 | 판단 합 {sum(r['jev_judge_calls'] for r in rows)}회")
        return 0

    if args.mode in {"ask", "both"}:
        # [3단계] 단일 단계 ask: Deep Agent가 검색 도구를 불러 답변 하나를 완성한다. 상한은 Budget 기본값(모델 10회).
        announce("단일 단계 ask", model_calls=10)
        started = time.perf_counter()
        record = ask(question, retriever=retriever, scope=scope, model=model, budget=Budget(), reranker=reranker)
        print(f"\n== 단일 단계 ask ({time.perf_counter() - started:.1f}초) ==")
        summarize(record)
        if isinstance(reranker, JevReranker):
            print(f"  Jev 재순위: judge {reranker.calls}회 / 후보 {reranker.questions}개")

    if args.mode in {"two_phase", "both"}:
        # [4단계] 2단계 ask_two_phase: 빠른 답변 → 게이트 3개 → 필요할 때만 검증 턴. 판단 호출은 별도 상한 6회.
        announce("2단계 ask_two_phase", model_calls=10)
        print("이 실행은 Decision API 호출도 최대 6회(Budget.max_decision_calls)까지 합니다.")
        started = time.perf_counter()
        record = ask_two_phase(question, retriever=retriever, scope=scope, model=model, decider=decider,
                               budget=Budget(), reranker=reranker)
        print(f"\n== 2단계 ask_two_phase ({time.perf_counter() - started:.1f}초) ==")
        summarize(record)
        if isinstance(reranker, JevReranker):
            print(f"  Jev 재순위: judge {reranker.calls}회 / 후보 {reranker.questions}개")

    if args.mode == "fs":
        # [5단계] 파일 시스템 탐색 에이전트: 검색 도구 없이 내장 파일 도구(ls·glob·grep·read_file)만으로
        # outputs/fs_corpus 트리에서 답을 찾는다. 답은 일반 텍스트로 받는다(구조화 출력 안 함).
        fs_root = build_fs_corpus()
        print(f"파일 시스템 코퍼스: {fs_root} (문서 {len(list(fs_root.rglob('*.md'))) - 1}개 + INDEX.md)")
        announce("파일 시스템 탐색 에이전트", model_calls=8)
        started = time.perf_counter()
        run = run_fs_agent(model, question, scope, fs_root)
        print(f"\n== 파일 시스템 탐색 에이전트 ({time.perf_counter() - started:.1f}초) ==")
        print(f"  도구 호출: {run['tools']}")
        print(f"  모델 호출={run['counts'].get('model', 0)}회 | 도구 호출={run['counts'].get('tool', 0)}회")
        print("  답변:")
        for line in run["answer"].splitlines()[:15]:
            print(f"    {line}")

    if args.mode == "fs_jev":
        # [6단계] Jev 파일 탐색: 발췌 선택 → 커버리지 판정 → 모델 답변 → 추가 확인 게이트. 자세한 흐름은 run_fs_jev.
        fs_root = build_fs_corpus()
        announce("Jev 파일 탐색", model_calls=2)
        print("이 실행은 Decision API 호출도 사용합니다(선택 배치 + 커버리지 + 추가 확인, 약 3~5회).")
        started = time.perf_counter()
        record = run_fs_jev(model, decider, question, scope, fs_root, top_k=args.top_k,
                            per_file_cap=args.per_file_cap, stage1_files=args.stage1_files)
        record["seconds"] = round(time.perf_counter() - started, 3)
        write_run_record(record)
        print(f"\n== Jev 파일 탐색 ({record['seconds']}초) ==")
        print(f"  Jev judge {record['jev_judge_calls']}회 | 모델 {record['model_calls']}회 | 폴백: {'예' if record['fallback'] else '아니요'}")
        print(f"  실행 기록: {ROOT / 'outputs' / 'runs' / (record['run_id'] + '.json')}")
        print("  답변:")
        for line in record["answer_text"].splitlines()[:15]:
            print(f"    {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
