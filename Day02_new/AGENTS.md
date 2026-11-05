# AGENTS.md — Day02_new: Agentic RAG 노트북 과정

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day02_new 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** Agentic AI 기초 → Function Calling과 도구 → Agent Skills → 검색 설계 →
운영형 Agentic RAG → DeepAgents RAG 실습을 노트북 7개(사전 점검 1 + 수업 6)로 따라간다.
LangGraph 루프를 손으로 짜지 않고 곧바로 `create_deep_agent`로 간다. 검색 인덱스는 메모리 안에서 만든다
(OpenViking 서버 없음). 모델은 Anthropic(`ChatAnthropic`)의 실제 모델과, 04~06의 판단 게이트용 실제 Decision API(TypeSafe, OpenRouter, OpenAI, Azure OpenAI 중 하나)만 쓴다. 설계 근거는 [docs/DESIGN.md](docs/DESIGN.md)에 있다.

> `Day02/`는 이 폴더와 별개의 이전 자료다. 이 폴더의 작업이 `Day02/`를 바꾸지 않고, 둘의 파일 구성은
> 다르다. 혼동하면 `Day02/AGENTS.md`의 규칙을 이쪽에 적용하지 않는다.

---

## 0. 채점 과제가 없다 — 그래도 설명은 해야 한다

번호 노트북 00~06에는 채점 과제가 없다. 모든 코드가 완성돼 있고, 수강생은 실행하고 읽고 바꿔 본다.
그래서 루트 AGENTS.md 4장의 단계적 힌트 정책(L0~L3)은 **여기에 적용하지 않는다.** 코드를 읽고 설명하는
요청, `직접 해보기` 셀을 같이 푸는 요청은 자유롭게 돕는다.

단, 루트의 성공 기준은 그대로다. **수강생이 그 셀을 자기 말로 설명할 수 있어야 한다.**
- 수강생이 셀을 고쳐 달라고 하면 고치기 전에 "이 셀이 무엇을 보여 주려는 건가요?"를 먼저 묻는다.
- `확인 질문` 절의 답을 대신 써 주지 않는다. 노트북 출력의 어느 줄이 근거인지 찾게 한다.
- 모르면 모른다고 말한다. 이 저장소에 없는 함수·플래그·파일을 지어내지 않는다.
- 문서와 코드가 다르면 코드가 정답이다. 차이를 수강생에게 알린다 (예: `docs/DESIGN.md`와 설치된
  deepagents 동작이 다를 수 있다).

용어는 자료의 한국어 용어를 그대로 쓴다: 근거(Evidence), 원문, 담당자(owner), 예산(budget), 인용,
기준일(as_of), 고객(entity).

---

## 0-1. 셀 표지와 [내 것 만들기] 도움

노트북 셀에는 `[따라하기]`, `[바꿔보기]`, `[깨뜨리기]`, `[내 것 만들기]` 표지가 있다. 순서대로 실행, 값 하나 변경, 일부러 실패, 내 것으로 만들기다.
- `[내 것 만들기]`를 도울 때는 코드를 주기 전에 **수강생이 결과를 먼저 예측**하게 한다("이 셀을 돌리면 무엇이 몇 개 나올 것 같나요?"). 실행 후 예측과 비교해 설명하게 한다.
- `[깨뜨리기]`의 오류는 고칠 대상이 아니라 관찰 대상이다. 고치기 전에 어디서 왜 멈췄는지 묻는다.

---

## 1. 실행은 노트북이 기본, 실행기는 보조

노트북 00~06이 수업 경로다. 실행 조건은 **노트북 안의 변수와 셀**이다
(`CONFIG`, `Budget(...)`, `Scope(...)` 등). 조건을 바꾸려면 셀을 편집해 다시 실행한다.
노트북에 없는 `--flag`를 지어내 안내하지 않는다.

`run_pipeline.py`는 노트북 대신 전체 파이프라인을 Python 코드로 한 번에 돌리는 보조 실행기다(2026-11-05 추가).
기본 모델은 OpenGateway의 `deepseek/deepseek-v4.1-flash-ultrafast`고 `.env`의 `OPENGATEWAY_API_KEY`가 필요하다.
`--provider anthropic`이면 노트북과 같은 Anthropic Claude를 쓴다. 게이트 판정은 노트북과 같은 Decision API다.
검색 구성도 `.env` 파일로 정한다: `DAY02_RETRIEVAL_MODE`(`fusion` 기본, `bm25`면 로컬 임베딩을 적재하지 않음)와
`DAY02_RERANKER`(`on` 로컬 교차 인코더 기본, `off`, `jev`는 Decision API가 후보별 관련 확률로 재순위, 판단 호출 유료).
실행 인자 `--retrieval`, `--rerank`가 `.env`보다 우선한다. `--mode fs`는 검색 도구 없이 내장 파일 도구
(`ls`·`glob`·`grep`·`read_file`)로 `outputs/fs_corpus/`(고객/도메인 폴더 + INDEX.md + frontmatter)를
뒤지는 경로다. `--mode fs_jev`는 파일 선택을 Jev가 발췌별 관련 확률로 하고 커버리지 판정으로 모은 발췌의
적절함을 검증하며(불충분하면 fs 에이전트로 폴백), 답 뒤 추가 확인 게이트로 재검증한다. 기록은 `outputs/runs/`.
`--dataset`(`--cases-file`·`--gold-file`로 hard 세트 지정, `--corpus allganize`·`--split tune|hold`로 올거나이즈
실측 PDF 지정)은 사례 전체를 돌려 품질을 잰다. 정답표는 실행이 끝난 뒤에만 읽고(`load_gold`), 기대 문서가
범위 밖인 행은 따로 세며 실패 행을 지우지 않는다. 올거나이즈처럼 클 때는 `--stage1-files N`(문서 요약으로 먼저
좁히는 2단계 선택, 커버리지 실패 시 전체 발췌 재시도 → 에이전트 폴백 사다리)로 판단 호출을 줄인다.
유료 호출 직전에 `announce`로 규모를 고지한다. 저장소 루트에서
`uv run --no-sync python Day02_new/run_pipeline.py`로 돌리며 `--question`, `--entity`, `--as-of`,
`--mode ask|two_phase|fs|fs_jev|both`, `--provider opengateway|anthropic`을 받는다.

그 밖의 예외는 저자용 도구뿐이며, 수강생 실습에 필요하지 않다. 수강생이 쓰지 않으니 안내하지도 않는다.
- `tests/check_notebook.py`: 노트북 검사기 (3장 참고).
- `benchmarks/measure.py`: `rag_lab`을 부품별로 재는 도구. `retrieval`은 API를 부르지 않고, `answers`는 실제 Claude를 부르는 유료다 (`--out`, 반복 `--pair 구성:문항ID`, `--cap` 예산 상한 지원).
- `benchmarks/check_decider.py`: 고른 Decision API가 지금 응답하는지 `Noul` 하나로 확인한다. **실제 Decision API를 한 번 부르는 유료 호출**이고 키 값은 출력하지 않는다 (저장소 루트에서 `uv run --no-sync python Day02_new/benchmarks/check_decider.py`). 상태 코드 401·403이면 키, 404면 주소나 모델 id를 확인하라고 안내한다.
- `benchmarks/measure.py`의 `ksq-gated`: 정답이 여러 개인 시험에서 Jev 분해 게이트를 잰다 (결과는 `docs/retrieval_benchmarks.md`의 `Jev 관문 측정`). 실제 Decision API를 부른다. 같은 파일의 `ko-longrag`: 문서 여러 개를 합치는 Ko-LongRAG에서 분해 게이트를 잰다 (결과는 `docs/retrieval_benchmarks.md`의 `분해: Ko-LongRAG`). 실제 Claude(문항마다 1회, `--cap` 상한)와 Decision API를 부르는 유료다. pyarrow는 프로젝트 의존성이 아니라 저장소 루트에서 `uv run --no-sync --with pyarrow python Day02_new/benchmarks/measure.py ko-longrag --work-dir <임시 폴더>`로 실행한다. **데이터 라이선스가 CC BY-NC 4.0과 OpenAI 이용 약관이다.** 문단과 질문 글은 저장소에 넣지 않고 git 제외 폴더 `outputs/benchmarks/ko_longrag/`에만 두며, 결과에는 ID와 지표만, 문서에는 질문 글 없이 적는다.
- `tests/cost_report.py`: 인자 없이 비용 표, `--cells <노트북>`은 셀별 비용(보고서 JSON의 `usage_lines`), `--check-docs`는 README·AGENTS의 비용 표가 기록과 다르면 불일치를 찍고 1로 끝난다. API를 부르지 않는다. `tests/run_live.py`는 유료 실행기이고, 다시 실행할 때 앞선 기록을 `outputs/live/history/<UTC 시각>/`에 먼저 복사한다.
- `benchmarks/allganize.py`: 올거나이즈 문항과 PDF를 받아 검색 측정에 쓰는 도구 (`fetch`, `status`).
- `benchmarks/make_sample_pdf.py`: 04가 쓰는 표본 PDF `data/pdf/credit-trend-chart.pdf`를 만든다.

---

## 2. 파일 상태표

| 파일 | 상태 | 내용 |
|---|---|---|
| `00-Setup.ipynb` | 제공 | 10분 사전 점검. 키 상태(Anthropic + Decision API), 판정 API 한 번(`make_decider`), 모델 호출, Deep Agents 한 턴. `announce` 합 3회(Claude 2회, Decision API 1회). 2026-11-02 실제 호출은 같은 3회(Claude 2, Decision API 1), 16.1초 |
| `01-Agentic-AI-Basics.ipynb` | 제공 | Agent가 일반 LLM 호출과 다른 점(단일 호출, 고정 workflow, Agent), 같은 질문 세 번(도구 없이, 도구 하나, 직접 실행), 메시지가 곧 상태라는 점, 존재하지 않는 도구와 반복 한도. 2절 제목 셀이 따로 있다. `기본 경로의 announce` 합은 약 30회(추정). 2026-11-02 실제 호출은 Claude 29회, 51.9초 |
| `02-Function-Calling-and-Tools.ipynb` | 제공 | 도구 왕복 4단계, 도구 설명·스키마, `Pydantic` 입력 범위, 도구 선택·병렬 호출, 도구 실패 세 유형, 오류 정보를 돌려주는 도구 vs 예외를 던지는 도구(8절), `tool_choice`·`strict`. 예산과 허용 목록은 여기서 가르치지 않고 05(결정 2)에서 다룬다. `announce` 합은 약 25회(추정). 2026-11-02 실제 호출은 Claude 23회, 42.2초 |
| `03-Agent-Skills.ipynb` | 제공 | `SKILL.md` 구조, 트리거 측정, 설명 수정 전후. **Skill 트리거 테스트(양성과 near-miss)는 6절-7절**이다. `RUN_OPTIONAL = False` 기본 경로의 `announce` 합은 약 132회, 선택 측정 두 셀은 약 100회(모두 추정). 2026-11-02 실제 호출은 기본 경로 Claude 87회(126.3초), `RUN_OPTIONAL = True` 복사본은 184회(422.0초) |
| `04-Retrieval-Design.ipynb` | 제공 | 청킹, BM25·dense·RRF, recall·MRR 측정, 넓은 후보와 원 질문 재순위, Jev 관문(질문 분해와 출처 보강), 아키텍처 선택 비교, PDF 쪽 판독. 1절에 `[깨뜨리기]` 셀 세 개(전체 문서를 한 프롬프트에 넣었을 때의 크기, 같은 이름의 여러 버전, 기준일을 넣은 전체 문서 질문)가 있다. 기본 경로의 Claude 호출은 최대 4회, Decision API는 5회(추정). 2026-11-02 실제 호출은 Claude 3회, Decision API 5회, 112.0초 |
| `05-Production-Agentic-RAG.ipynb` | 제공 | 설계 결정 아홉 가지(근거 검증, 지지 검토, 실행 기록)와 선택 결정(빠른 답변과 Jev 게이트 세 개의 비용 측정, 게이트 실패 [깨뜨리기]). 예산은 3절(`MAX_SEARCHES`의 `[바꿔보기]` 셀), 허용 목록은 결정 2(적용 전 `[따라하기]`, `MENU_ALLOWED`의 `[바꿔보기]`, `ALLOWED_TOOLS`의 `[깨뜨리기]`)에서 가르친다. 근거 상태별 행동 표(충분·일부·모호·부재·충돌·timeout)가 있다. `announce` 합은 Claude 약 58회(`[내 것 만들기]` 11회 제외 약 47회, 추정). 2026-11-02 실제 호출은 Claude 42회와 Decision API 4회, 132.1초 |
| `06-Lab-DeepAgents-RAG.ipynb` | 제공 | 융합 검색+재순위 도구로 조립, 6단계 `ask_two_phase`(Jev 게이트, 분해 기본 켬), 한 설정을 측정하고 한 가지만 바꿔 전후 비교. 1~3단계가 Tool + Skill + RAG 기본 통합(최소 Agentic RAG 루프, 검색 도구와 Skill 연결, 도구 호출과 `loaded_skills` 관찰)이고 4~6단계는 확장이다. Skill 트리거 테스트 자체는 03의 6절-7절에 있다. `announce` 합은 약 77회(추정). 2026-11-02 실제 호출은 Claude 54회와 Decision API 54회, 259.8초(`MAX_CASES = 3`) |
| `rag_lab/` | 제공 | 노트북이 import하는 지원 모듈 (4장 참고) |
| `run_pipeline.py` | 제공 | 보조 실행기. 노트북 없이 단일 단계 `ask`와 2단계 `ask_two_phase`를 Python 코드로 한 번씩 돌린다. 기본 모델은 OpenGateway DeepSeek(키 `OPENGATEWAY_API_KEY`), `--provider anthropic`이면 Claude. Decision API 키도 필요하다(2단계 게이트) |
| `docs/gold_review_sheet.md` | 제공 | `data/gold_hard*.jsonl`과 `gold.jsonl:3`(`versioned-deadline-june`) 검수 시트. AI 교차 확인 초안이고 모든 판정이 `미검수`다. 사람 검수 전에는 gold를 확정이라 말하지 않는다 |
| `docs/rehearsal_sheet.md` | 제공 | 60분 리허설 시트. `실제 분`이 비어 있고 리허설은 아직 하지 않았다 |
| `data/cases_hard2.jsonl`, `data/gold_hard2.jsonl` | 제공 | 04의 두 번째 어려운 질문 22개와 정답표(평가 전용, 동결). 04가 recall과 MRR을 잰다 |
| `skills/` | 제공 | `SKILL.md` 폴더 6개: comparison, grounded-answer, grounded-qa, insufficient-evidence, procedure, table-analysis |
| `data/business/` | 제공 | 원문 11개 (md 10, `catalog.json`) |
| `data/cases.jsonl` | 제공 | 질문 사례 |
| `data/gold.jsonl` | **평가 전용** | 정답표. 5장 규칙 참고 |
| `data/cases_hard.jsonl` | 평가 전용 | 04의 동결한 어려운 질문 14개 (paraphrase, decoy, abbreviation, two-doc, version-trap, abstain-trap) |
| `data/gold_hard.jsonl` | **평가 전용·초안** | `cases_hard`의 정답표. `review_status: draft`로 저자 검토 전이다. 실행 경로에서 읽지 않고, 결과에 맞추려고 고치지 않는다 |
| `benchmarks/` | 저자용 | `measure.py`, `allganize.py`, `make_sample_pdf.py`, `check_decider.py`와 `allganize_pinned.json`. 노트북과 `rag_lab`은 import하지 않는다 |
| `data/pdf/` | 제공 | 04가 쓰는 표본 PDF `credit-trend-chart.pdf` (글자층 없는 차트 한 쪽) |
| `tests/` | 저자용 | pytest, 노트북 검사기, `run_live.py`, `cost_report.py`. 가짜 모델·임베딩은 `tests/fakes.py`에만 있고 단위 시험 전용이다. `rag_lab`과 노트북은 import하지 않는다 |
| `docs/draft_student_notice.md`, `docs/draft_check_questions.md` | 제공(초안) | 저자용 초안: 수업 전 학생 안내문(`[저자 확인]` 자리가 남아 있다), 다시 쓴 확인 질문. 저자 검수 전에는 확정이라 말하지 않는다 |
| `outputs/` | 생성물 | 실행 기록 `outputs/runs/`, Skill 샌드박스. git 제외 (`outputs/live/`는 실제 실행 증거, `outputs/live/history/`는 재실행 전 기록 사본) |
| `.env.example` | 제공 | 수강생이 `.env`로 복사해 `ANTHROPIC_API_KEY`와 Decision API 키 하나(`TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY` 중, 또는 Azure의 키·엔드포인트·배포 이름)를 직접 채운다 |

`skills/grounded-answer/`는 다른 다섯 폴더와 달리 `output.json`이 없다 (`answer.py`의 `skill_spec`가 읽는
쪽이다). 이 점을 질문받으면 노트북 03 출력과 `rag_lab/answer.py:46`을 같이 보게 한다.

---

## 3. 실행 규칙

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 한다. 루트 `pyproject.toml`의 uv workspace가 환경 하나를
쓴다 (`day02-deepagents-rag`가 멤버, `deepagents==0.7.32`).

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day02_new
uv run jupyter lab          # 실행은 이 폴더에서 (00-Setup.ipynb 안내와 같다)
```

- 이 폴더 안에서 `uv sync`를 하지 않는다. 다른 Day에 필요한 패키지가 지워진다. 복구는 루트의
  `uv sync --locked`다.
- `pyproject.toml`과 `uv.lock`을 이 폴더에 만들지 않는다.
- **노트북은 00부터 번호 순서로 푼다.** 건너뛰게 유도하지 않는다.
- **키가 둘 필수다.** `ANTHROPIC_API_KEY`와 Decision API 키 하나(`TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`,
  `OPENAI_API_KEY` 중, 또는 Azure의 `AZURE_OPENAI_API_KEY`)다. Anthropic 키가 없으면 `require_key`(`rag_lab/settings.py:86`)가, Decision API 키가
  없으면 `make_decider`(`rag_lab/decisions.py:175`)가 한국어 안내와 함께 `RuntimeError`로 멈춘다. 키 없이 도는
  경로, 건너뛰기, 대체 경로, Claude로 판정을 대신하는 경로는 없다. 보조 실행기 `run_pipeline.py`의 기본 경로는
  `ANTHROPIC_API_KEY` 대신 `OPENGATEWAY_API_KEY`다(노트북에는 필요 없고 `--provider anthropic`이면 Anthropic 키를 쓴다).
- **질문 문장과 근거 텍스트가 선택한 Decision API 공급자에게 전송된다.** 04~06의 게이트 셀이 그렇다.
  외부에 보내면 안 되는 내용은 넣지 않게 안내한다. 여러 키가 있으면 `DAY02_DECISION_BACKEND`로 고르고,
  비어 있으면 TYPESAFE, OPENROUTER, OPENAI, AZURE 순서의 첫 키를 쓴다 (`rag_lab/decisions.py:175`). Azure는 키에 더해 `DAY02_AZURE_ENDPOINT`와 `DAY02_AZURE_DEPLOYMENT`가 모두 있어야 하고 하나라도 비면 `make_decider`가 `RuntimeError`로 멈춘다 (`rag_lab/decisions.py:190`). `DAY02_OPENROUTER_MODEL`은 OpenRouter가 보낼 모델 id를 바꾸고 비우면 코드의 고정값을 쓴다. **Azure와 OpenRouter 경로는 실제 호출로 확인되지 않았다.** 모의 전송 단위 시험만 있으니 수강생에게 "동작 확인됨"이라 말하지 않는다. `benchmarks/check_decider.py`(1장)로 고른 공급자를 한 번 불러 볼 수 있다.
- 제공자는 Anthropic이고 기본은 `claude-sonnet-5-5`, effort `medium`이다 (`rag_lab/settings.py:21`,
  `rag_lab/settings.py:22`). 다른 Day의 OpenRouter 키와 이 폴더의 `ANTHROPIC_API_KEY`는 다르다. `.env`는 이 폴더의 것만 읽는다.
- 키가 없어 실패한 경우 키를 대신 넣어주려 하지 않는다. `.env.example`을 `.env`로 복사해
  `ANTHROPIC_API_KEY`와 Decision API 키 하나를 **수강생이 직접** 채우게 안내한다. `.env` 내용을 출력하지 않고
  `key_status`(`rag_lab/settings.py:71`)로 "설정됨/미설정"만 본다.
- dense 검색의 임베딩은 로컬 `intfloat/multilingual-e5-small`(`rag_lab/embeddings.py`의
  `LocalE5Embeddings`)이다. Anthropic에 임베딩 API가 없어서이며, 처음 쓸 때 약 470MB를 내려받는다.
- 재순위는 로컬 `BAAI/bge-reranker-v2-m3`(`rag_lab/settings.py:24`)이고 첫 실행에 약 2.1GB를 내려받는다 (API 호출·비용 없음). 00이 미리 받아 둔다. CPU에서 문항당 0.68초(후보 평균 18개)로 쟀다 (`docs/retrieval_benchmarks.md:52`).
- 03의 `RUN_OPTIONAL`(기본 `False`)과 06의 `MAX_CASES`(기본 3)가 실행 규모를 정한다. 같은 질문도
  실행마다 다르게 끝날 수 있으니 한 번의 결과를 "1회 관찰"로 읽게 한다.
- 노트북 검사 (저자용, 키 불필요):
  `uv run --no-sync python Day02_new/tests/check_notebook.py <노트북> --minutes N` (저장소 루트에서).
  `rag_lab`을 import하므로 이 폴더가 작업 폴더가 되는지 확인한다.

---

## 4. 질문이 어느 `rag_lab` 파일로 이어지는가

수강생 질문의 주제로 먼저 볼 파일을 정한다. 답할 때는 `파일:줄`을 붙인다.

| 질문 주제 | 파일 | 대표 심볼 |
|---|---|---|
| 키 상태, 모델·임베딩 생성, 실제 호출 관문, 비용 고지 | `rag_lab/settings.py` | `load_settings`, `key_status`, `require_key`, `announce`, `UsageLog`, `make_model`, `make_embeddings`, `make_reranker`(`rag_lab/settings.py:162`) |
| 로컬 임베딩 | `rag_lab/embeddings.py` | `LocalE5Embeddings` |
| 원문 적재, 고객·기준일 범위, 청킹, 표가 잘리는지 | `rag_lab/corpus.py` | `Scope`, `Document`, `Chunk`, `load_corpus`, `load_cases`, `fixed_chunks`, `section_chunks`, `count_cut_tables` |
| 토크나이저, BM25, dense, RRF, 융합 점수 | `rag_lab/retrieval.py` | `tokenize`, `BM25Index`, `DenseIndex`, `rrf`, `fuse_scores`(`rag_lab/retrieval.py:104`), `corroborate`(`rag_lab/retrieval.py:111`), `Retriever` |
| 예산, 근거(Evidence), 충분성 판정, 검색·읽기 도구 | `rag_lab/evidence.py` | `Budget`, `BudgetExceeded`, `Evidence`, `assess_sufficiency`, `RetrievalContext`, `make_search_tools` |
| Agent 조립, 허용 도구 목록, Skill 읽기 추적, 한 턴 실행, 실행 기록 | `rag_lab/agent.py` | `ALLOWED_TOOLS`, `SYSTEM_PROMPT`, `allowlist_middleware`, `check_skill_folder`, `build_rag_agent`, `Session`, `ask`, `write_run_record` |
| 답변 형식, 인용 검증, 지지 검토, 렌더링 | `rag_lab/answer.py` | `AnswerPayload`, `Section`, `Statement`, `skill_spec`, `validate_answer`, `review_support`, `render_answer` |
| 교차 인코더 재순위(로컬 모델, 키 불필요) | `rag_lab/rerank.py` | `CrossEncoderReranker`(`rag_lab/rerank.py:13`), 생성은 `make_reranker`(`rag_lab/settings.py:162`) |
| 질문 분해, 다중 질의 검색 합치기, 컨텍스트 바이트 자르기 | `rag_lab/pipeline.py` | `retrieve`(`:63`), `decompose_question`(`:46`), `interleave`(`:58`), `fit_context`(`:83`) |
| Decision API 공급자 선택, 질문 형식(Noul·Choice·Score), 실패 | `rag_lab/decisions.py` | `Noul`(`:20`), `Choice`, `Score`, `Verdict`, `Judgment`, `DecisionError`(`:74`), `DecisionBackend`(`:78`), `TypeSafeBackend`, `OpenRouterBackend`, `OpenAIDecisionsBackend`, `AzureOpenAIDecisionsBackend`, `make_decider`(`:175`) |
| Jev 게이트 세 개(분해, 추가 확인, 인용 관련성), 문턱값, 실패 기본값 | `rag_lab/gates.py` | `GateResult`(`:42`), `MeteredDecider`(`:65`), `needs_decomposition`(`:93`), `needs_follow_up`(`:98`), `irrelevant_citations`(`:114`), `strip_citations`(`:154`), `DECOMPOSE_THRESHOLD`(`:18`) |
| 두 단계 실행(빠른 답 → 게이트 → 검증), 질의 계획, 필수 `decider` | `rag_lab/phases.py` | `ask_two_phase`(`:125`, `decider` 필수, `decompose=True` 기본) |
| PDF 쪽 판독(글자층 없는 쪽을 골라 모델이 글자로 옮김) | `rag_lab/pages.py` | `needs_reading`(`:38`), `read_page`(`:44`), 임계값 `IMAGE_AREA_THRESHOLD`, `MIN_TEXT_CHARS` |
| 검색 recall·MRR 측정, 유형별 집계 | `rag_lab/evaluation.py` | `load_gold`, `evaluate_retrieval`, `recall_by_type`, `mrr` |

노트북별로는 대략 02는 `rag_lab`보다 노트북 안에서 정의한 도구를 중심으로 하고, 05가 `agent.py`·`evidence.py`(예산·허용 목록)를, 03이 `agent.py`·`answer.py`(Skill),
04가 `corpus.py`·`retrieval.py`·`evaluation.py`·`pipeline.py`·`rerank.py`·`pages.py`에 더해 `decisions.py`·`gates.py`(Jev 관문 셀), 00은 `decisions.py`(판정 API 한 번), 05가 `phases.py`·`gates.py`·`decisions.py`도 쓰고 `answer.py`·`agent.py`, 06이 전체를 쓴다.
이 대응은 노트북이 바뀌면 달라질 수 있으니 확인이 필요하면 `grep`으로 import를 본다.

---

## 5. 절대 하지 말 것

채점은 없지만, 측정 결과를 믿을 수 있게 하는 규칙은 같다. 수강생이 요청해도 하지 않는다.
이유를 한 문장으로 말하고, 대신 **실패를 정확히 드러내는 방법**을 제안한다.

1. **`data/gold.jsonl`, `data/gold_hard.jsonl`, `data/gold_hard2.jsonl`을 실행 경로에서 읽지 않는다.** 읽는 곳은 `rag_lab/evaluation.py`의 `load_gold`
   (`rag_lab/evaluation.py:14`) 하나이며, Agent 실행 경로(`ask`, `build_rag_agent`, 도구)는 이
   모듈을 import하지 않는다 (`rag_lab/evaluation.py:1`). 측정 셀(04, 06의 recall)에서만 쓴다.
   `agent.py`나 도구, 프롬프트에 정답 문서를 넣어 주지 않는다.
2. **실패한 행을 지우지 않는다.** 실행 기록의 실패 행, `BudgetExceeded`, 검증 오류, 놓친 recall 행을
   결과에서 빼거나 잘 나온 반복만 골라 남기지 않는다. 05의 실행 기록이 실패를 남기는 것이 의도다.
3. **예산을 올려 실패를 감추지 않는다.** `Budget`의 `max_tool_calls`, `max_model_calls`, `max_searches`,
   `max_reads`, `max_context_bytes`, `max_seconds`, `max_decision_calls`(`rag_lab/evidence.py:23`, 판단 호출 한도는 `:30`)와 `_RECURSION_LIMIT`
   (`rag_lab/agent.py:28`)을 실패를 없애려고 올리지 않는다. 05 3절의 `# [바꿔보기]` 셀(`MAX_SEARCHES = 1`을 2로 바꿔 몇 번째 검색에서 멈추는지 보는 셀)처럼 **예산 동작을 보려고
   낮추는 것**은 허용이다. 올릴 때는 "왜 이 숫자가 필요한가"를 수강생이 먼저 말하게 한다.
4. **가짜 모델을 실행 경로에 들이지 않는다.** 가짜 모델·임베딩은 `tests/fakes.py`에만 두고 단위 시험
   전용으로 쓴다. `rag_lab`과 노트북이 import하지 않으며, 그 출력으로 정확도나 recall을 말하지 않는다.
   06의 `compare_runs`는 나아진 행, 같은 행, 나빠진 행을 모두 출력한다. 나빠진 행을 숨기지 않는다.
5. **측정 숫자를 지어내지 않는다.** 노트북이 출력하지 않은 recall, 시간, 비용을 기억에서 말하지 않는다.
   수강생 환경에서 출력된 값만 인용한다. 비용은 `tests/cost_report.py`로 다시 계산한 값만 쓴다. 반복이 1회면 "1회 관찰"이라고 말한다.
6. **키를 로그·출력에 남기지 않는다.** Decision API 키 셋도 같다. `.env`, `outputs/`는 커밋하지 않는다 (`.gitignore`).

---

## 6. 비용 — 실제 호출 셀

모든 모델 셀이 실제 호출이다. `announce`(`rag_lab/settings.py:95`)가 실행 **직전에 규모를 한 줄로
고지**한다. 막지 않는다. 다만 수강생이 자기 Anthropic 크레딧과 Decision API 계정을 쓴다는 점을 상기시킨다. 질문 하나(`ask`)는
모델 호출을 최소 4회 이상 쓴다. `announce`는 Claude 호출 수만 알리므로 Decision API 호출은 셀 머리글의 "판단 약 N회"와
`Budget.max_decision_calls`(기본 6)를 보게 한다.

비용은 사용 기록(`DAY02_USAGE_LOG`, `UsageLog`는 `rag_lab/settings.py:119`)에 남은 모델 기준으로
`tests/cost_report.py`가 계산한다. 저장소 루트에서 `uv run --no-sync python Day02_new/tests/cost_report.py`를
실행하면 노트북별 모델 호출, 초, 토큰, 비용이 나온다. 아래는 한 번 실행·한 대의 컴퓨터 값이며, 모델이
바뀌면 위 명령으로 다시 계산한다 (03은 `RUN_OPTIONAL = False`, 06은 `MAX_CASES = 3`).

**2026-11-02 주의:** 아래 표의 모든 행은 2026-11-02에 개정한 노트북 00~06(코드 셀을 같은 호출을 유지한 채 자세히 풀어 쓴 판)을 실제로 다시 돌린 기록이다. 이전 기록은 `outputs/live/history/`에 보관했다. `announce` 합은 셀이 실행 직전에 알리는 `model_calls`를 더한 **추정치**이고, 아래 표가 측정값이다. 계획(추정) 대 측정은 다음과 같다: 00 약 3회 대 3회(Claude 2, Decision API 1), 01 약 30회 대 29회, 02 약 25회 대 23회, 03 약 132회 대 87회, 04 Claude 최대 4회와 Decision API 5회 대 3회와 5회, 05 Claude 약 58회(`[내 것 만들기]` 제외 약 47회)와 Decision API 약 4~7회 대 42회와 4회, 06 약 77회 대 Claude 54회와 Decision API 54회, 선택 측정 복사본 약 232회 대 184회. 대부분 추정보다 적게 나왔다. 추정은 상한에 가까운 값이고 모델이 도구를 덜 부르면 호출이 줄기 때문이다. 코드 셀은 한 줄씩 읽도록 풀어 썼으니 수강생에게도 줄 단위로 읽게 안내한다.

| 노트북 | 모델 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |
|---|---|---:|---:|---:|---:|---:|
| 00-Setup | claude-sonnet-5-5 | 2 | 16.1 | 3898 | 133 | 0.0024 |
| 00-Setup | jev-1.14.0 | 1 |  | 348 | 22 | 0.0000 |
| 01-Agentic-AI-Basics | claude-sonnet-5-5 | 29 | 51.9 | 87454 | 2685 | 0.0970 |
| 02-Function-Calling-and-Tools | claude-sonnet-5-5 | 23 | 42.2 | 36678 | 1857 | 0.0691 |
| 03-Agent-Skills | claude-sonnet-5-5 | 87 | 126.3 | 459078 | 17272 | 0.3553 |
| 03-optional-copy | claude-sonnet-5-5 | 184 | 422.0 | 959902 | 48400 | 0.7235 |
| 04-Retrieval-Design | claude-sonnet-5-5 | 3 | 112.0 | 5535 | 932 | 0.0204 |
| 04-Retrieval-Design | jev-1.14.0 | 5 |  | 1861 | 110 | 0.0001 |
| 05-Production-Agentic-RAG | claude-sonnet-5-5 | 42 | 132.1 | 252098 | 11058 | 0.3142 |
| 05-Production-Agentic-RAG | jev-1.14.0 | 4 |  | 3237 | 159 | 0.0001 |
| 06-Lab-DeepAgents-RAG | claude-sonnet-5-5 | 54 | 259.8 | 616554 | 20679 | 0.7703 |
| 06-Lab-DeepAgents-RAG | jev-1.14.0 | 54 |  | 40126 | 1985 | 0.0017 |
| **합계** | | 304 | 740.4 | 1506867 | 56892 | **1.6307** |
| **선택 측정** (수업 합계에서 제외) | | 184 | 422.0 | 959902 | 48400 | **0.7235** |

(한 번 실행·한 대의 컴퓨터 값이다. 모든 행이 2026-11-02 실행이다. `03-optional-copy`는 03을 `RUN_OPTIONAL = True`로 돌린 복사본의 **선택 측정**이라 합계에서 제외하고 마지막 줄에 따로 적었다. **같은 노트북도 실행마다 값이 다르다.** 호출 수가 모델의 도구 선택에 따라 달라지므로 이 표를 정답 호출 수로 외우게 하지 않는다. `합계` 304회에는 Decision API 64회(`jev-1.14.0` 행)가 들어 있고 Claude는 240회다. **Decision API(`jev-*`)는 입력 10억 토큰당 $42(https://typesafe.ai/, 2026-11-01)로 계산했다. 공식 페이지에 출력 단가가 없고 2차 출처(https://www.eesel.ai/blog/typesafe-jev-pricing)가 출력 무료라고 해서 출력은 0으로 둔 가정이다.** 출력 단가가 붙으면 Decision API 비용은 더 크다. 이 단가를 다른 공급자(OpenRouter, OpenAI, Azure)에 쓰지 않고, 그 공급자의 비용은 수강생의 청구서를 보게 하며 추정치를 지어내지 않는다. 단가표에 없는 모델은 계속 `단가 미확인`이다. 입력 토큰에는 캐시 읽기와 캐시 쓰기가 들어 있고, 비용은 각각 캐시 단가로 계산한다. 캐시 쓰기는 이번 기록에서 관찰되었다(전체 271,563 토큰, 1시간 TTL 0). 캐시 쓰기 필드가 없는 옛 기록 64줄은 0으로 계산되어 실제보다 적을 수 있다(여기에는 캐시 필드가 원래 없는 Decision API 줄도 들어 있다).)

"초"는 기계 시간일 뿐이고 60분 수업 시간은 리허설하지 않았다. 04의 임베딩과 재순위는 로컬 모델이라 API
비용이 없고, 04의 비용은 Claude 호출 3회(0.0204달러)가 전부이며(어느 셀의 호출인지는 `outputs/live/04-Retrieval-Design.usage.jsonl`에서 확인한다) Jev 관문 5회는 입력 단가만 적용한 0.0001달러다. 03의 `RUN_OPTIONAL`을 `True`로 하면 선택 측정 두 셀(예상 호출 약 100회)이 더해지고, 06의 `MAX_CASES`(와 `REPEATS`, 질문 수)를 올리면 대표 사례 셀(4 x `MAX_CASES`), 내 질문 셀, 전후 비교 셀(4 x 질문 수 x `REPEATS` x 2)이 비례해 늘어 이 값을 넘는다. 그런 셀은
실행 전에 한 번 더 고지한다. 정확한 호출 수는 `Budget.counts`와 실행 기록(`outputs/runs/`)에서 확인한다.

---

## 7. 수강생이 자주 막히는 곳

- **"첫 셀에서 멈춰요"**: `ANTHROPIC_API_KEY`가 미설정이다. `key_status`로 설정됨/미설정만 확인하고 `.env`를 직접 채우게 안내한다. 00의 판정 API 셀에서 멈추면 Decision API 키 셋(`TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, 또는 Azure의 `AZURE_OPENAI_API_KEY`) 중 하나가 비어 있는 것이다(`rag_lab/decisions.py:175`). Claude로 대신하는 경로는 없다.
- **dense·hybrid가 오류를 낸다**: `Retriever`는 임베딩 없이 두 방식을 만들면 `ValueError`를 낸다
  (`rag_lab/retrieval.py:134`). 조용히 대체하지 않는 것이 설계다. `make_embeddings()`로 만든 임베딩을 넘기거나 `mode="bm25"`로 간다.
- **도구를 추가했는데 Agent가 못 쓴다**: `allowlist_middleware`가 허용 목록 밖의 도구를 숨기고 거부한다
  (`rag_lab/agent.py:54`). 05 결정 2의 `[바꿔보기]` 셀(`MENU_ALLOWED`)처럼 허용 집합에 추가한다. 우회하려고 미들웨어를 빼지 않게 이유부터 묻는다.
- **`BudgetExceeded`**: 예산 한도에 걸린 정상 동작이다. 3번 규칙대로 숫자를 올리기 전에 어떤 호출이 한도를
  소진했는지 `Budget.events`를 보게 한다.
- **Skill이 안 읽힌다**: `SKILL.md`의 `description`이 트리거를 결정한다. `check_skill_folder`
  (`rag_lab/agent.py:79`)의 오류 목록과 03의 측정 셀을 본다.
- **import 오류**: 작업 폴더가 `Day02_new`인지, 루트에서 `uv sync --locked`를 했는지 확인한다.

---

## 8. 인용 검증

이 문서의 `파일:줄` 인용과 심볼은 `grep -n`으로 확인한다. 코드가 바뀌어 줄이 움직이면 고친다. 답할 때 쓰는 인용도 먼저 grep으로 확인한다.
