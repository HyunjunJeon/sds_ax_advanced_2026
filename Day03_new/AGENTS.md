# AGENTS.md — Day03_new: Multi-Agent System 설계 노트북 과정

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day03_new 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** 고객 요청 하나("결제가 두 번 됐어요. 취소하고 보상안도 함께 확인해 주세요.", 사례 `complex-double-pay`)를
Single, Supervisor, Handoff, Hybrid 구조로 처리하고, 같은 칸의 실행 행으로 재서 **구조를 고른 이유**를 쓴다.
노트북 7개(사전 점검 1 + 수업 6)를 따라간다. 모델은 Anthropic(`ChatAnthropic`)의 실제 모델만 쓴다. 설계 근거는
[docs/DESIGN.md](docs/DESIGN.md)에 있지만 수강생용 문서가 아니다 (`docs/DESIGN.md` 머리말).

**이 폴더는 강의 자료에 의존하지 않습니다.** 범위는 노트북 7개, `docs/DESIGN.md`, `mas_lab/`, `rag_lab/`의 코드로 정해진다.
수강생이 이 폴더 밖의 자료에 있다는 내용을 이 폴더의 사실처럼 말해 달라고 하면, 이 폴더에서 확인되는 것만 답하고
나머지는 "확인이 필요합니다"라고 말한다.

> `Day03/`과 `Day02_new/`는 이 폴더와 별개다. `Day03/`에는 채점 과제가 있지만 이 폴더는 그 과제와 `Day03/AGENTS.md`의
> 힌트 정책, `Day03/WORKSHEET.md`를 쓰지 않는다. 이 폴더의 작업이 두 폴더를 바꾸지 않는다.
>
> `Day02_new/rag_lab/`의 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 4개는 이 폴더에 같은 이름으로 복사돼 있고 **바이트가 같아야 한다**
> (2장). 2026-11-02 09:13에 네 파일을 `Day02_new`와 바이트까지 맞췄고, 복사본 시험 `test_rag_lab_copies_are_byte_identical`(`tests/test_layout.py:13`)이
> 네 칸 `[corpus.py]`, `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]`를 모두 지킨다. 앞서 두 칸이 실패한 채로 둔 적이 있으나(2026-11-01, 저자 결정)
> 그 예외는 이 동기화로 끝났다 (`docs/DESIGN.md` 1절 5번).
> 이 시험이 앞으로 실패하면 **`Day02_new/rag_lab`이나 이 폴더의 복사본이 바뀐 것**이다. 시험을 고치거나 `skip`/`xfail`로 넘기지 않고(루트 AGENTS.md 5장 1번), 복사본을 `Day02_new`와
> 다르게 고쳐 통과시키지도 않는다. 이 폴더의 복사본을 고친 것이면 되돌리고, `Day02_new/rag_lab`이 바뀐 것이면 복사본을 다시 맞춘다. 다시 맞추는 일은 실행 기록을 만든 코드를 바꾸므로 저자가 정한다 (6장 "기록이 만들어진 때").
> `settings.py`는 일부러 다르고 이 시험이 보지 않는다.

---

## 0. 채점 과제가 없다 — 그래도 설명은 해야 한다

번호 노트북 00~06에는 채점 과제가 없다. 모든 코드가 완성돼 있고, 수강생은 실행하고 읽고 바꿔 본다.
그래서 루트 AGENTS.md 4장의 단계적 힌트 정책(L0~L3)은 **여기에 적용하지 않는다.** 코드를 읽고 설명하는
요청, `직접 해보기` 셀을 같이 푸는 요청은 자유롭게 돕는다.

단, 루트의 성공 기준은 그대로다. **수강생이 그 셀을 자기 말로 설명할 수 있어야 한다.**
- 수강생이 셀을 고쳐 달라고 하면 고치기 전에 "이 셀이 무엇을 보여 주려는 건가요?"를 먼저 묻는다.
- `확인 질문` 절의 답과 설계 기록 셀의 답을 대신 써 주지 않는다. 노트북 출력의 어느 칸이 근거인지 찾게 한다.
  설계 기록은 `outputs/design_log.json`에 쓰이고(`mas_lab/view.py:69`) 06이 모아 보여 주므로, AI가 채우면 06이 수강생이 아니라 AI의 선택 이유를 보여 준다.
- 모르면 모른다고 말한다. 이 저장소에 없는 함수·플래그·파일을 지어내지 않는다.
- 문서와 코드가 다르면 코드가 정답이다. 차이를 수강생에게 알린다 (8장).

용어는 자료의 한국어 용어를 그대로 쓴다: 근거(Evidence), 원문, 담당자(owner), 예산(budget), 인용,
기준일(as_of), 고객(entity). Supervisor, Worker, Handoff, Router, Fast/Slow Path는 영어 그대로 쓴다.
답변은 한국어로 하고 사실 주장에는 `파일:줄`을 붙인다.

---

## 0-1. 셀 표지와 도움 방식

노트북에는 다음 표지가 있다. 표지마다 도와주는 방식이 다르다.

| 표지 | 도와주는 방식 |
|---|---|
| `**먼저 예측하세요.**` | 수강생이 예측을 말하기 전에 결과나 이유를 알려 주지 않는다. "어느 칸이 어떻게 나올 것 같나요?"로 시작한다. 실행 뒤 예측과 비교해 설명하게 한다 |
| `**관찰할 것.**` | 정답을 주지 않는다. 출력의 어느 칸(`겹친 시간(초)`, `원장 건수`, `실패 칸` 등)을 읽을지만 가리킨다. 모델 결과가 어느 쪽으로 나와도 말이 되게 쓰인 문단이다 |
| `# 실패 재현:` (코드 셀 첫 줄) | 고칠 대상이 아니라 관찰 대상이다. 예외 종류와 메시지를 수강생이 읽고 어디서 왜 멈췄는지 말하게 한 뒤에 다음으로 간다 |
| `## 직접 해보기`, `### 해보기 N` | 값 하나만 바꾸게 한다. 켜기 전에 결과를 예측하게 하고 규모(6장)를 알린다. 유료 셀은 `RUN_EXERCISE = False`로 꺼져 있다 |
| 설계 기록 셀, `확인 질문` | 수강생의 판단이다. 대신 쓰지 않는다 |

---

## 1. 명령행 플래그가 없다

수강생 실습에는 실행 스크립트도 `argparse`도 없다. 실행 조건은 **노트북 안의 변수와 셀**이다
(`RUN_EXERCISE`, `RUN_OPTIONAL`, `Budget(...)`, `force_path`, `faults` 등). 조건을 바꾸려면 셀을 편집해 다시 실행한다.
환경변수로 분기하는 셀도 없다. `--flag`를 지어내 안내하지 않는다.

예외는 저자용 도구 셋뿐이다. 수강생 실습에 필요하지 않고 권하지도 않는다.
- `tests/check_notebook.py --minutes N` — 구조 검사. N은 10 또는 60 (`tests/check_notebook.py:123`)
- `tests/run_live.py <노트북> --exercises` — 노트북을 **실제 모델로 끝까지** 돌린다 (`tests/run_live.py:120`). 수강생 세션에서 실행하지 않는다. 저자가 돌릴 때도 6장 규모를 먼저 고지한다
- `tests/wait_live.py <stem> --seconds N` — 위 실행이 끝나기를 기다린다 (`tests/wait_live.py:26`)

---

## 2. 파일 상태표

| 파일 | 상태 | 내용 |
|---|---|---|
| `00-Setup.ipynb` | 제공 | 10분 사전 점검. 두 키 상태, 모델 없는 그래프, 모델 호출, Deep Agent 한 턴, EXA 검색 한 번 |
| `01-Workflow-vs-Agent.ipynb` | 제공 | 다음 행동의 결정권과 실행 권한, Single 기준선 |
| `02-Agent-Architecture.ipynb` | 제공 | Single → Supervisor → Handoff. 결과를 돌려받는 것과 대화를 넘기는 것. 3절에서 프레임워크가 자동으로 붙이는 `general-purpose`와 설계한 Worker를 모델 없이 비교 |
| `03-Four-Flows.ipynb` | 제공 | 순차·병렬(`Send`)·분기·루프, reducer, 재귀 한도 |
| `04-Graph-Engineering.ipynb` | 제공 | 계약, 예산, 실패별 다음 행동, 승인(`interrupt`)과 멱등. 첫머리에서 Graph Engineering을 과정의 정의로 세운다 |
| `05-Choosing-Multi-Agent.ipynb` | 제공 | 같은 조건 비교표, 평균의 함정, 선택 근거. 0절에서 Workflow와 Agent 전제를 노드 담당자 표로 확인하고, 7절에 harness 일관성 표와 공식 프레임워크 표를 둔다 |
| `06-Lab-Research-Agents.ipynb` | 제공 | EXA로 병렬·직렬·연쇄 리서치 Deep Agent 비교. **EXA 키 필수** |
| `mas_lab/` | 제공 | 노트북이 import하는 지원 모듈 14개 (4장). 쓰기 게이트가 `gate.py`로, 하위 에이전트 설정이 `harness.py`로 나뉘어 늘었다. 파일마다 비공백 150줄 이하여야 하고 (`tests/test_layout.py:20-22`의 `test_modules_stay_readable_in_class`), `workers.py`와 `hybrid.py`는 지금 정확히 150줄이라 줄을 하나라도 더하면 이 시험이 실패한다 |
| `rag_lab/` | 제공 | `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 4개는 `Day02_new/rag_lab/`에서 복사한 파일이고 바이트가 같다 (2026-11-02 09:13에 맞췄다. `tests/test_layout.py:13`의 `test_rag_lab_copies_are_byte_identical`이 네 칸을 모두 지킨다). 실패하면 `Day02_new`나 이 폴더의 복사본이 바뀐 것이다(위 머리말). `settings.py`는 EXA 키 항목이 더해진 판이라 일부러 다르고 동기화도 건드리지 않았다 (`rag_lab/settings.py:70`). 복사한 코드에는 이 과정이 부르지 않는 기능이 들어 있다(3장) |
| `data/business/` | 제공 | 원문 md 11개와 `catalog.json`. 고객(entity)별로 알파 4, 베타 1, 공통 6 |
| `data/support/` | 제공 | `billing.json`, `outage.json`. 수업용 가상 사실이며 파일 첫 키 `_note`가 그렇게 밝힌다 |
| `data/cases.jsonl` | 제공 | 질문 사례 12개. 정답 필드가 없다 |
| `data/gold.jsonl` | **평가 전용** | 정답표 12행. 5장 규칙 참고 |
| `skills/` | 제공 | `SKILL.md` 폴더 3개: refund-case, credit-case, insufficient-evidence. `single_skills` 구조가 `_skill_kwargs`로 불러 읽는다 (`mas_lab/structures.py:38`) |
| `docs/DESIGN.md` | 저자용 | 설계 계약. 구현 뒤 코드와 어긋난 곳은 코드를 따른다 (8장). `docs/audit/`에는 저자가 익명화해 둔 증거 기록이, `docs/audit/tools/`에는 문서 검사 도구, 결함 주입 도구, 동기화 비교 도구가 있다. 수강생은 읽지 않아도 된다 |
| `tests/` | 저자용 | pytest, 노트북 검사기, 실제 실행(`run_live.py`, `wait_live.py`), 감사(`audit_live.py`), 비용(`cost_report.py`). 가짜 모델은 `tests/fakes.py`에만 있고 단위 시험 전용이다 (`tests/fakes.py:1`). 복사본 시험은 네 칸이고, `Day03_new/tests` 전체 실행은 `625 passed`(실패 0)다 (2026-11-02, `tests/test_harness.py` 추가 뒤. 9장) |
| `outputs/` | 생성물 | `runs/`(실행 행 JSON, `_finish_row`가 쓴다, `mas_lab/runner.py:111`), `design_log.json`, `baseline/01.json`, `live/`(저자의 실제 실행 증거). `design_log.json`과 `baseline/01.json`은 그 노트북을 마지막으로 돌린 실행이 덮어쓴다(6장). git 제외 (`.gitignore:2`) |
| `.env.example` | 제공 | 수강생이 `.env`로 복사해 직접 채운다 |
| `README.md` | 제공 | 수강생용 안내 |

---

## 3. 실행 규칙

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 한다. 이 폴더에는 `pyproject.toml`이 없고 `uv run`이 루트의 uv workspace 환경을 찾는다.

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day03_new
uv run jupyter lab          # 실행은 이 폴더에서
```

- 이 폴더 안에서 `uv sync`를 하지 않는다. 다른 Day에 필요한 패키지가 지워진다. 복구는 루트의 `uv sync --locked`다.
- `pyproject.toml`과 `uv.lock`을 이 폴더에 만들지 않는다.
- **노트북은 00부터 번호 순서로 푼다.** 건너뛰게 유도하지 않는다. 노트북은 앞 노트북의 kernel 상태 없이 단독으로 돌지만,
  06은 앞 노트북이 남긴 설계 기록을 모아 보여 준다. 기록이 없어도 멈추지 않는다 (`mas_lab/view.py:64`).
- **키가 필수다.** `ANTHROPIC_API_KEY`가 없으면 `require_key`(`rag_lab/settings.py:61`)가, `EXA_API_KEY`가 없으면
  `require_exa_key`(`rag_lab/settings.py:70`)가 한국어 안내와 함께 `RuntimeError`로 멈춘다. 00의 키 확인 셀이 두 키를 모두
  요구하고, EXA는 06에서 쓴다. 키 없이 도는 경로, 건너뛰기, 대체 경로는 없다.
- 키는 `Day03_new/.env`에서만 읽는다 (`rag_lab/settings.py:41`). 셸에 export한 키나 다른 Day의 키는 읽지 않는다.
  `.env`를 고친 뒤에는 kernel을 재시작해야 반영된다.
- 키가 없어 실패한 경우 키를 대신 넣어주려 하지 않는다. `.env.example`을 `.env`로 복사해 **수강생이 직접** 채우게 안내한다.
  `.env` 내용을 출력하지 않고 `key_status`(`rag_lab/settings.py:50`)로 "설정됨/미설정"만 본다.
- 모델 변수 이름이 `DAY02_MODEL`, `DAY02_EFFORT`인 것은 오류가 아니다 (`rag_lab/settings.py:44`). `Day02_new/.env`를 고치지 않고 복사해
  쓰게 하려는 선택이다. 기본은 `claude-sonnet-5-5`, effort `medium`이다 (`rag_lab/settings.py:16`, `rag_lab/settings.py:17`).
- `make_model`은 `max_retries=0`이다 (`rag_lab/settings.py:117`). 429 같은 일시 오류도 숨기지 않고 실패 행(`status="model_error"`,
  `mas_lab/runner.py:78`)으로 드러낸다. 잠시 뒤 다시 실행하게 안내하고, 재시도를 켜서 감추지 않는다.
- 검색은 BM25만 쓴다 (`mas_lab/runner.py:31`). 임베딩 모델을 내려받지 않는다. 복사한 코드에는 `Retriever`의 `fusion` 방식(`rag_lab/retrieval.py:147`), 질의 분해 `decompose_question`(`rag_lab/pipeline.py:46`), 미리 검색 `prefetch`(`rag_lab/evidence.py:153`)도 있지만 `mas_lab`, 노트북, `tests`에는 이를 부르는 곳이 없고(`grep`으로 확인했다) 기본값이 `mode="bm25"`라서 (`rag_lab/retrieval.py:130`) 임베딩, 재순위 모델, Decision API 키가 필요하지 않다.
- kernel의 작업 폴더가 `Day03_new`여야 `import mas_lab`이 된다. 00이 작업 폴더와 `sys.prefix`를 출력한다.
- 실행 규모 스위치는 노트북 안의 상수다. `RUN_EXERCISE`는 `직접 해보기`의 유료 셀마다, `RUN_OPTIONAL`은 05의 첫 코드 셀과 06의 설정 셀에 있고 기본 `False`다.
  켜면 비용이 는다 (6장). 같은 질문도 실행마다 다르게 끝날 수 있으니 한 번의 결과는 "1회 관찰"이라고 부르게 한다.
- 노트북 검사 (저자용, 키 불필요): `uv run --no-sync python Day03_new/tests/check_notebook.py <노트북> --minutes N` (저장소 루트에서).

---

## 4. 질문이 어느 `mas_lab` 파일로 이어지는가

수강생 질문의 주제로 먼저 볼 파일을 정한다. 답할 때는 `파일:줄`을 붙인다.

| 질문 주제 | 파일 | 대표 심볼 (`파일:줄`) |
|---|---|---|
| Worker 입출력 계약, 스키마 통과 뒤의 검증, 결과 병합·join, 실패 종류별 다음 행동 | `mas_lab/contracts.py` | `WorkerTask:18`, `WorkerResult:27`, `Proposal:38`, `FinalAnswer:48`, `Route:56`, `validate_result:78`, `validate_final:88`, `merge_results:103`, `join_results:119`, `trim_payload:137`, `plan_hash:153`, `classify_failure:167`, `next_action:179` |
| 고객 범위의 사실과 도구, 역할별 도구, 오류 주입 | `mas_lab/desk.py` | `load_billing:22`, `load_outage:27`, `Desk:32`, `_inject:49`, `known_refs:63`, `tools:70` |
| Worker 조립, 허용 도구, 모델·도구 호출 수 세기, Skill 읽기 추적, 병렬 위임을 구간으로 남기기(`delegation_spans`), hybrid Worker의 근거 번호 검사(`checked_worker`) | `mas_lab/workers.py` | `ROLE_TOOLS:25`, `DENY_WRITES:34`, `TASK_CONTRACT:36`, `allowlist_middleware:50`, `delegation_spans:75`, `TrackedSkillsBackend:87`, `_run_with_messages:118`, `run_worker:141`, `_TOKEN:148`, `checked_worker:151`, `subagent_spec:173` |
| 모든 Deep Agent에서 프레임워크 자동 `general-purpose`를 끄기(`use_designed_subagents_only`), 비교용으로 프레임워크 기본을 잠시 켜기(`framework_default_subagent`), `task` 도구가 내놓는 하위 에이전트 이름 읽기(`task_targets`). `mas_lab/__init__.py:7-9`가 import 때 anthropic provider에 한 번 적용한다 | `mas_lab/harness.py` | `use_designed_subagents_only:25`, `framework_default_subagent:31`, `task_targets:46` |
| Single·Supervisor·Handoff 구조, Router·triage의 모델 호출 세기(`structured_call`) | `mas_lab/structures.py` | `OUTCOME_GUIDE:20`, `structured_call:32`, `_skill_kwargs:38`, `build_single:46`, `build_supervisor:56`, `MAX_HANDOFFS:87`, `build_handoff:90` |
| 쓰기 게이트(`gate_answer`), 제안 없이 낸 `denied`·`human_review`의 결제 대조(`check_named_payment`), 질문의 결제 번호 철자(`_PAYMENT_ID`), 검사하지 못한 질문의 `gate_skipped` 사건, 코드 판정을 답에 옮기기(`_settle`) | `mas_lab/gate.py` | `_BLOCKED:10`, `_PAYMENT_ID:13`, `_named_payments:18`, `refund_decision:22`, `gate_answer:32`, `check_named_payment:50`, `_settle:80` |
| Router, Fast/Slow Path, `Send` 병렬, 재시도, 승인 대기(`interrupt`), 게이트 노드(`check_named_payment` 호출) | `mas_lab/hybrid.py` | `HybridRoute:28`, `build_hybrid:45`, `scope_check:50`, `router:59`, `dispatch:83`, `worker:88`, `after_join:95`, `retry:106`, `after_validate:125`, `gate:139`, `after_gate:144`, `approve:150`, `execute:156`, 그래프 조립 `:160-177` |
| 환불 정책 검사, 가짜 결제 원장, 멱등, 응답 유실 | `mas_lab/ledger.py` | `REFUND_WINDOW_DAYS:12`, `APPROVAL_THRESHOLD:13`, `ResponseLost:16`, `PaymentLedger:25`, `check_refund:46`, `execute_approved:71` |
| 같은 조건 실행, 고정 예산, 실행 행, 실패 행, 마지막 turn의 답만 게이트에 넘기는 규칙과 앞 turn의 환불 제안이 게이트를 지나지 않았다는 흔적(`earlier_turn_proposal_ungated` 사건) | `mas_lab/runner.py` | `FIXED_BUDGET:24`, `STRUCTURES:25`, `make_desk:39`, `run_case:56`, `_run_turns:82`, `_note_ungated_proposal:105`, `_finish_row:111`, `_violations:132`, `run_grid:142` |
| 모델 호출 수·토큰·구간·겹침 시간·가장 긴 경로 | `mas_lab/trace.py` | `ModelMeter:13`, `totals:45`, `Trace:57`, `overlap_seconds:80`, `longest_path:91`, `timeline:103` |
| 표·그래프 출력, 설계 기록 | `mas_lab/view.py` | `message_table:13`, `show_graph:30`, `flows_of:37`, `show_table:50`, `read_design_log:64`, `write_design_log:69` |
| 자동 검사, 구조×유형 요약, 라우터 일치표 | `mas_lab/evaluation.py` | `load_gold:10`, `evaluate_row:19`, `summarize_rows:36`, `routing_table:55` |
| EXA 호출, 외부로 나가는 질의 차단(`INTERNAL_PATTERN`은 `P-7001`, `p7001`, `P7001`, `INV-…` 같은 내부 번호를 대소문자와 하이픈 유무, 바로 붙은 한글 조사와 상관없이 막고 `p99`, `gpt-4`는 막지 않는다), 도메인 제한 | `mas_lab/exa.py` | `INTERNAL_PATTERN:18`, `DEFAULT_BLOCKED:19`, `allowed_url:22`, `assert_public_query:30`, `ExaClient:37`, `make_exa_tool:81` |
| 리서치 그래프(병렬·직렬·연쇄), 보고서 검증, URL 겹침 | `mas_lab/research.py` | `WORKER_PROMPT:54`, `_worker_run:66`, `build_research_graph:80`, `run_research:123`, `url_overlap:146`, `validate_report:152` |
| 키 상태, 모델 생성, 비용 고지, 키 가리기 | `rag_lab/settings.py` | `load_settings:39`, `key_status:50`, `require_key:61`, `require_exa_key:70`, `announce:79`, `UsageLog:85`, `_redact:102`, `make_model:109` |
| 예산 한도, 근거(Evidence) 등록(한도를 넘으면 낮은 순위부터 버리기), 검색·읽기 도구 | `rag_lab/evidence.py` | `BudgetExceeded:18`, `Budget:23`, `consume:42`, `RetrievalContext:106`, `_admit:118`, `make_search_tools:173` |
| 고객·기준일 범위, 원문 적재, 검색 방식 | `rag_lab/corpus.py`, `rag_lab/retrieval.py` | `Scope:16`, `load_corpus:62`, `Retriever:126` |
| 검색 순위 합치기와 컨텍스트 한도에 맞춰 자르기 (`RetrievalContext`가 `retrieve`와 `fit_context`를 부른다, `rag_lab/evidence.py:135`, `rag_lab/evidence.py:123`) | `rag_lab/pipeline.py` | `retrieve:63`, `fit_context:83` |

- **`gate_answer`가 어디 있느냐는 질문.** 정의는 `mas_lab/gate.py`(`gate_answer:32`, `check_named_payment:50`)다. `mas_lab/structures.py:16`은 노트북이 `mas_lab.structures`에서 import하므로
  `gate_answer`와 `check_named_payment`를 다시 내보내기만 한다. `structures.py`에서 정의를 찾으면 없다.
- **`checked_worker`를 부르는 곳.** hybrid의 `worker`와 `retry` 노드뿐이다 (`mas_lab/hybrid.py:90`, `mas_lab/hybrid.py:110`). 01~03 노트북은 hybrid를 만들지 않으므로 이 함수를 부르지 않는다.
  `delegation_spans`는 Supervisor 한 곳에서 쓴다 (`mas_lab/structures.py:64`).
- **150줄 상한.** `workers.py`와 `hybrid.py`는 비공백 150줄로 상한에 닿아 있다 (`tests/test_layout.py:22`). 줄을 더하는 수정은 `test_modules_stay_readable_in_class`를 깨뜨린다.
  상한을 올려 통과시키지 않고(5장 3번과 같은 이유) 저자에게 묻는다.

노트북별로는 대략 02가 `structures.py`·`trace.py`, 03이 `hybrid.py`·`contracts.py`·`trace.py`, 04가 `contracts.py`·`ledger.py`·`workers.py`·`hybrid.py`,
05가 `runner.py`·`evaluation.py`, 06이 `research.py`·`exa.py`를 중심으로 쓴다. 이 대응은 노트북이 바뀌면 달라질 수 있으니 확인이 필요하면
노트북의 `import` 줄을 본다.

---

## 5. 절대 하지 말 것

채점은 없지만, 측정 결과를 믿을 수 있게 하는 규칙은 같다. 수강생이 요청해도 하지 않는다.
이유를 한 문장으로 말하고, 대신 **실패를 정확히 드러내는 방법**을 제안한다.

1. **`data/gold.jsonl`을 실행 경로에서 읽지 않는다.** 읽는 곳은 `mas_lab/evaluation.py`의 `load_gold`(`mas_lab/evaluation.py:10`) 하나이고,
   실행 경로(도구, 프롬프트, 구조 빌더, 게이트, 실행 함수)는 이 모듈을 import하지 않는다고 모듈 머리말이 밝힌다 (`mas_lab/evaluation.py:1`). 테스트는 `mas_lab`에서 `gold`가 적힌 모듈이 `evaluation.py` 하나뿐이고 `rag_lab` 모듈에는 `gold.jsonl`이 적혀 있지 않은지를 지킨다
   (`tests/test_layout.py:25`). 노트북에서도 `mas_lab.evaluation`을 import한 뒤의 평가 셀에서만 `gold`를 쓴다 (`tests/check_notebook.py:97`).
   프롬프트나 도구에 정답 문서·금액·날짜를 넣어 주지 않는다. `Day03/data/gold.jsonl`(옛 폴더)도 읽지 않는다.
   정답표와 자동 검사가 어긋나 보여도 정답표를 고쳐 통과시키지 않는다 (7장 "자동 검사가 실패인데 답은 맞아 보여요").
2. **실패한 행을 지우지 않는다.** `run_case`는 `BudgetExceeded`와 그 밖의 예외를 올리지 않고 실패 행으로 남기고 (`mas_lab/runner.py:75-78`), `summarize_rows`는 실패 행을 빼지 않으며
   usage 누락을 0으로 세지 않는다 (`mas_lab/evaluation.py:37`, `mas_lab/trace.py:46`). `BudgetExceeded`, 검증 실패, 429, 자동 검사 실패 행을
   결과에서 빼거나 잘 나온 반복만 골라 남기지 않는다. 평균을 낼 때 실패 행을 섞거나 빼면 평균이 달라지므로, 무엇이 평균에 들어갔는지 05의 `남은 사례`, `제외한 행` 칸으로 보인다.
3. **예산을 올려 실패를 감추지 않는다.** 다음 값을 실패를 없애려고 올리지 않는다.
   - `Budget`의 `max_tool_calls`, `max_model_calls`, `max_searches`, `max_reads`, `max_context_bytes`, `max_seconds` (`rag_lab/evidence.py:23`)와 동기화로 들어온 `max_decision_calls` (`rag_lab/evidence.py:30`, 모델 호출과 따로 센다). 이 폴더에는 이 종류를 소비하는 코드가 없어 올릴 이유가 없고, 올려서 실패를 감추지 않는 규칙은 같다
   - `FIXED_BUDGET` (`mas_lab/runner.py:24`), `RECURSION_LIMIT` (`mas_lab/workers.py:33`), `MAX_HANDOFFS` (`mas_lab/structures.py:87`), `MAX_REWRITES` (`mas_lab/hybrid.py:25`)
   - EXA 검색 한도 `max_searches` (`mas_lab/exa.py:40`, `mas_lab/exa.py:81`)
   04·05의 `직접 해보기`처럼 **예산 동작을 보려고 낮추는 것**은 허용이다. 올릴 때는 "왜 이 숫자가 필요한가"를 수강생이 먼저 말하게 한다.
   `allowlist_middleware`(`mas_lab/workers.py:50`)를 빼서 도구 거부를 없애는 것도 같은 이유로 하지 않는다.
4. **한 번의 관찰을 통계로 말하지 않는다.** 반복이 3회 미만이면 "1회 관찰"이라고 말한다. 같은 질문을 두 번 돌려도 호출 수와 토큰이 다르다 (7장).
   변동 폭보다 작은 차이에 구조 탓의 이유를 붙이지 않는다.
5. **측정 숫자를 지어내지 않는다.** 노트북이 출력하지 않은 호출 수, 시간, 토큰, 비용을 기억에서 말하지 않는다. 비용은 `tests/cost_report.py`로 다시
   계산한 값만 쓴다. 수강생 환경에서 출력된 값만 인용하고, 이 문서 6장의 값은 저자 환경의 1회 실측임을 밝힌다.
6. **키를 로그·출력에 남기지 않는다.** `.env`, `outputs/`는 커밋하지 않는다 (`.gitignore:1`, `.gitignore:2`). 실행 행 파일은 `_redact`를 거쳐 쓴다 (`mas_lab/runner.py:128`).
7. **가짜 모델을 실행 경로에 들이지 않는다.** 가짜 모델은 `tests/fakes.py`에만 두고 단위 시험 전용으로 쓴다. `rag_lab`, `mas_lab`, 노트북이 import하지 않으며,
   그 출력으로 구조의 우열을 말하지 않는다.
8. **쓰기 경로를 우회하지 않는다.** 환불을 모델에게 도구로 주지 않는다. 모든 구조의 쓰기는 `gate_answer`를 지난다 (`mas_lab/gate.py:32`). 제안 없이 낸 `denied`·`human_review`는
   `check_named_payment`가 질문이 가리킨 결제와 대조하고 (`mas_lab/gate.py:50`) 이 검사는 `check_refund`만 부른다 (`mas_lab/gate.py:65`). 원장에 쓰는 `execute_approved`는 정의가 `mas_lab/ledger.py:71`이고
   부르는 곳은 `gate_answer` 안의 `execute_approved(...)` 호출 한 줄뿐이다 (`mas_lab/gate.py:39`). `mas_lab/structures.py:16`은 `gate_answer`를 다시 내보내기만 하니 게이트의 정의는 `gate.py`에서 찾는다. `interrupt` 앞에 부작용을 두지 않는다. 재개하면 노드가 처음부터 다시 돈다 (`mas_lab/hybrid.py:140`).
   멱등 키를 빼거나 실제 결제 API가 원장과 같은 멱등을 준다고 가정하지 않는다 (`mas_lab/ledger.py:26`).
9. **외부로 나가는 질의의 경계를 풀지 않는다.** 고객 이름과 내부 번호가 든 질의를 막는 패턴 `INTERNAL_PATTERN`(`mas_lab/exa.py:18`)과 이름 목록 `DEFAULT_BLOCKED`(`mas_lab/exa.py:19`), 이를 질의에 적용하는 `assert_public_query`(`mas_lab/exa.py:30`),
   URL 검사 함수 `allowed_url`(`mas_lab/exa.py:22`)을 검색이 안 된다는 이유로 비우거나 완화하지 않는다. 내부 번호의 철자(`P-7001`, `p7001`, `P7001`)를 모두 막도록 넓힌 패턴을 `P-7001` 한 가지로 되돌려 좁히지도 않는다. EXA 검색은 본인 크레딧을 쓰고 질의가 회사 밖으로 나간다.
   06의 `ALLOWED_DOMAINS`와 `직접 해보기` 1의 `MY_DOMAINS`는 위의 검사 함수와 달리 수강생이 주제에 맞게 고르는 **연구 범위 값**이라 바꿀 수 있다. 다만 검색 결과가 적다는 이유만으로
   목록을 비우거나 넓히지 않고, 넓힌다면 그 도메인을 왜 믿을 수 있는지 수강생이 먼저 말하게 한다 (노트북의 `해보기 1` 안내도 같은 기준이다).
10. **사람이 판정하는 칸을 대신 채우지 않는다.** 06의 `HUMAN_REVIEW`는 수강생이 원문 발췌와 주장을 나란히 보고 정한다. 비어 있으면 비율이 `확인 안 됨`으로 나오는 것이 정상이다.

---

## 6. 비용 — 실제 호출 셀

모든 모델 셀이 실제 호출이다. 유료 셀은 같은 셀 안에서 `announce`(`rag_lab/settings.py:79`)가 실행 **직전에 규모를 한 줄로 고지**한다. 막지 않는다.
다만 수강생이 자기 Anthropic 크레딧과 EXA 크레딧을 쓴다는 점을 상기시킨다. 도우미가 대신 셀을 돌릴 때도 직전에 한 줄로 알린다.

아래는 `Day03_new/outputs/live/*.json`과 `tests/cost_report.py`에서 읽은 **저자 컴퓨터의 1회 실측**이다(`claude-sonnet-5-5`, 2026-11-03 기준 기록 13개). 저자가 노트북을 다시 실행하면 값이 바뀌므로
두 곳에서 다시 읽은 값이 이 표보다 우선한다. `hybrid`의 Router를 실제 모델로 돌리는 노트북은 04와 05뿐이다(01과 03은 `hybrid`에서 `ROLE_GOALS`, `ROLES` 상수만 import한다).
어느 기록이 어느 코드로 돌았고 어느 기록을 다시 돌리지 않았는지는 아래 "기록이 만들어진 때"가 말한다.
기본 실행은 `RUN_EXERCISE`와 `RUN_OPTIONAL`이 모두 `False`인 실행이다. "초"는 기계 시간이고 수업 시간 리허설 값이 아니다.
모델 비용(USD)은 입력·출력·캐시 읽기 토큰에 값을 매긴 **하한**이다. 캐시 쓰기 단가는 `tests/cost_report.py`가 계산하지 않고 기록에도 캐시 쓰기 토큰이 없어서 (`tests/cost_report.py:76`) 실제 비용은 이보다 클 수 있다. 이 문서는 캐시 쓰기를 추정해 더하지 않는다.

| 노트북 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |
|---|---:|---:|---:|---:|---:|
| 00-Setup | 3 | 12.6 | 7,582 | 388 | 0.0128 |
| 01-Workflow-vs-Agent | 45 | 131.2 | 186,251 | 12,153 | 0.2198 |
| 02-Agent-Architecture | 33 | 114.2 | 113,267 | 13,640 | 0.2312 |
| 03-Four-Flows | 38 | 131.7 | 86,025 | 16,247 | 0.2543 |
| 04-Graph-Engineering | 35 | 107.8 | 94,303 | 15,855 | 0.2334 |
| 05-Choosing-Multi-Agent | 142 | 402.8 | 549,206 | 53,185 | 0.9222 |
| 06-Lab-Research-Agents | 28 | 214.0 | 147,993 | 32,660 | 0.4886 |
| 합계 | 324 | 1,114.3 | 1,184,627 | 144,128 | 2.3623 |

이 표의 합계는 반올림 전 값을 더해 한 번 반올림한 값이다. 이 표는 행의 초(1,114.3)와 비용(2.3623)을 그대로 더해도 합계와 같다. 같은 방법으로 `.exercises` 6개를 더한 표가 아래다. 켠 실행에는 00이 없다(00에는 켜는 스위치가 없다).

| 노트북 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |
|---|---:|---:|---:|---:|---:|
| 01-Workflow-vs-Agent.exercises | 51 | 153.2 | 208,926 | 14,008 | 0.2489 |
| 02-Agent-Architecture.exercises | 53 | 165.4 | 166,118 | 20,325 | 0.3215 |
| 03-Four-Flows.exercises | 44 | 138.4 | 110,580 | 18,015 | 0.2538 |
| 04-Graph-Engineering.exercises | 36 | 115.0 | 90,778 | 16,866 | 0.2394 |
| 05-Choosing-Multi-Agent.exercises | 451 | 1,237.5 | 1,713,172 | 145,338 | 2.6182 |
| 06-Lab-Research-Agents.exercises | 63 | 433.4 | 295,148 | 73,650 | 1.0886 |
| 합계 | 698 | 2,242.8 | 2,584,722 | 288,202 | 4.7704 |

이 표의 합계도 반올림 전 값을 더해 한 번 반올림한 값이다. 행의 초를 그대로 더하면 2,242.9라 마지막 자리가 하나 다르고, 비용은 행을 더해도 4.7704로 같다. `cost_report.py`가 맨 아래 한 줄로 내는 합계
(1,022회, 3,357.1초, 7.1327 USD)는 기록 13개를 모두 더한 값, 곧 위 두 표의 합계를 더한 값이다. 하위 에이전트를 끄기 전 기록(2026-11-02 21:40~22:51)은 996회, 3,419.6초, 6.9435 USD였다. 기본 실행과 `.exercises` 실행은 같은 셀을 겹쳐 돌렸으므로 이 값을 지출로 말하지 않는다.

**기록이 만들어진 때.** 13개 기록은 모두 2026-11-03 00:05~01:03에 지금 코드로 다시 돌린 것이다. 13개를 하나씩 차례로 돌렸다(시각은 `outputs/live/<기록>.json`의 수정 시각, 곧 기록이 끝난 시각이다. 시작 표지는 00:05:29이고 마지막 기록은 01:03:38에 끝났다). 그때의 코드는 모든 Deep Agent에서 프레임워크가 자동으로 붙이는 `general-purpose` 하위 에이전트를 끈 지금의 `mas_lab`(`mas_lab/__init__.py:7-9`, 쓰기 게이트는 `mas_lab/gate.py`, `gate_answer:32`), 2026-11-02 09:13에 `Day02_new`와 맞춘 `rag_lab`, 지금 노트북이다. 13개 실행본은 저장본과 코드도 markdown도 같다(켠 실행본은 스위치 줄만 다르다).

| 기록 | 끝난 시각 (2026-11-03) |
|---|---|
| 00 | 00:05 |
| 01 기본·켠 실행 | 00:08, 00:10 |
| 02 기본·켠 실행 | 00:12, 00:15 |
| 03 기본·켠 실행 | 00:18, 00:20 |
| 04 기본·켠 실행 | 00:22, 00:24 |
| 05 기본·켠 실행 | 00:31, 00:52 |
| 06 기본·켠 실행 | 00:56, 01:03 |

**이전 기록(이력).** 재실행 전의 기록은 2026-11-01에 만들어졌다. 그 사이에 `mas_lab`의 `gate.py`(19:24), `workers.py`(19:39), `exa.py`(20:04)가 바뀌어 기록이 수정 앞뒤로 갈렸고, 모두 `rag_lab` 동기화(2026-11-02 09:13)보다 앞섰다. 그때는 다시 돌리지 않았다. 대신 모델과 EXA를 부르지 않는 두 비교로 기록을 유지했다.
- 노트북의 코드 셀이 고친 함수에 닿지 않는다는 코드 비교(`docs/audit/stale-records-notes.md`).
- 동기화 앞뒤의 검색 결과 비교(`docs/audit/sync-equivalence-notes.md`). 실제 한도에서 검색 720회와 720회가 같았고, 한도를 3,000바이트로 낮춰 넘침 경로를 강제한 780줄 중에서만 73줄이 달랐다. 새 `_admit`(`rag_lab/evidence.py:118`)은 한도를 넘으면 그 아래 순위의 새 근거를 모두 버리고, 옛 코드는 넘친 항목 하나만 건너뛰었기 때문이다.

2026-11-02 Supervisor 용어 수정으로 02의 코드가 바뀌자, 저자가 02 기본 실행을 먼저 다시 돌리게 했다. 그 뒤 나머지 기록도 모두 다시 돌리기로 정했다. 이전 기록은 `outputs/live/superseded-20261102-before-full-rerun/`(12개)과 `outputs/live/superseded-20261102/`(02 기본 실행)에 남겼고, 재실행 경위와 이전 기록과의 비교는 `docs/audit/live-rerun-20261102-notes.md`에 있다.

그 재실행(2026-11-02 21:40~22:51)에서는 `create_deep_agent`가 자동으로 붙이는 `general-purpose` 하위 에이전트가 켜져 있었다. 그래서 모델이 일을 그쪽에 맡긴 `supervisor` 행이 3개 있었다(7장 `max_model_calls`를 낮췄는데 측정 호출이 더 많다는 항목). 저자가 이 하위 에이전트를 끈 뒤(`mas_lab/__init__.py:7-9`) 13개 기록을 한 번 더 돌린 것이 지금 기록이고, 하위 에이전트를 끄기 전 기록은 `outputs/live/superseded-20261102-before-subagent-off/`에 남겼다. 이전 기록과의 비교는 `docs/audit/live-rerun-20261102b-notes.md`에 있다. 새 노트북 셀이 더해져 하위 에이전트를 끄기 전 기록의 셀 번호는 지금보다 02의 25번 이상이 4칸, 05의 2~35번이 3칸, 36~57번이 6칸 작다. 이 문서의 02·05 셀 번호는 모두 지금 기록 기준이다.

- **오프라인 재생 (모델 호출 없이 저장된 행을 게이트에 다시 통과시킨 것).** 날짜가 있는 기록이고, 코드가 바뀌면 다시 돌려야 한다.
  - 첫 재생 (2026-11-01 09:41, 쓰기 게이트가 `mas_lab/structures.py` 안에 있던 때): 그때의 `outputs/runs`(968파일)에서 실제 모델 호출이 기록된 477행 중 제안 없이 `denied`·`human_review`로 끝난 행은 33개였고, 사례 id가 `data/cases.jsonl`에 없는 1개를 뺀 32행(`policy-deny-normal` 14, `policy-human-old` 18)을 새 게이트에 통과시켰다.
    outcome이 바뀐 행 0, 답 본문이 바뀐 행 0, 원장 기록 0이었고 자동 검사 통과 수도 같았다(14→14, 18→18). 바뀐 것은 `uncertainty`에 게이트 이유 한 줄이 더해진 것뿐이었다. 이 값은 그때 게이트의 값이다.
  - 그 뒤 쓰기 게이트가 `mas_lab/gate.py`로 옮겨진 판으로 같은 방법의 재생을 세 번 더 했고(14:50, 15:45, 16:38, 각 350행) 모두 뒤집힌 행 0, 원장 기록 0, 자동 검사 통과 수 342→342였다.
  - 재생 4 (2026-11-01 20:12, 지금의 `gate.py`): 그때의 `outputs/runs` 1781파일 중 실제 모델 호출이 기록된 732행에서 제안이 없고 사례 id가 `data/cases.jsonl`에 있는 **422행**을 지금 게이트에 통과시켰다. outcome이 뒤집힌 행 **0**, 원장 기록 **0**,
    자동 검사 통과 수는 **410에서 410**이었고 어느 사례·구조 칸도 통과 수가 줄지 않았다. 답을 통째로 바꾼 행(`gate_text_replaced`)은 0, 게이트 이유 문장이 답 끝에 덧붙은 행(`gate_text_appended`)은 51, 답은 두고 `gate_skipped` 사건만 남은 행은 59였다.
- **재생이 보이지 못하는 것.** 재생은 저장된 답이 새 게이트를 지나도 달라지지 않는다는 것, 곧 **회귀가 없다는 것만** 보인다. 제안이 있었던 행은 게이트를 지난 뒤의 outcome만 저장돼 있어 재생할 수 없다(재생 4에서 249행).
  저장된 질문에서 찾은 결제 번호 꼴 120개는 모두 `P-<숫자>`라서 `p7001`, `P7001`, `p-7001` 같은 철자를 새로 읽는지도, 유효 결제를 제안 없이 `human_review`로 낸 모양(P-7001)을 잡는지도 재생으로는 보이지 못한다.
  이 부분은 단위 테스트(`tests/test_structures.py:163`의 `test_first_payment_without_proposal_is_denied_by_the_code_gate`, `tests/test_structures.py:968`의 `test_payment_id_spellings_all_name_the_same_payment`)와 7장 P-7001 항목의 새 질문 실행으로만 확인했다.
- **코드 일치 검사.** 기본 실행 기록 7개는 `audit_live.py`가 실행본의 코드 셀과 현재 저장본이 같음을 확인한다(스위치 줄이 든 셀은 뺀다, `tests/audit_live.py:47`). 켠 실행 기록은 이 검사에서 빠진다 (`tests/audit_live.py:63`). 2026-11-03 재실행 직후에는 켠 실행본 6개도 저장본과 코드가 같았다(스위치 줄만 다르다). 노트북 코드를 고치면 기본 실행이 감사에서 실패하고, 켠 실행본은 감사 없이 어긋나므로 둘 다 다시 돌린다.
- **05의 이력.** 05 기본 실행을 처음 돌렸을 때 `hybrid 단순 사례와 복합 사례` 셀이 22회를 불러 고지 20회를 넘었고 감사가 실패시켰다. 그 셀의 고지를 `model_calls=30`으로 고치고(고지는 예고 숫자이지 `Budget`이 아니다, `rag_lab/settings.py:79`) 다시 돌려 통과한 기록만 `outputs/live/`에 남겼다.
  그 첫 시도의 기록 파일은 같은 이름으로 덮어써졌고 그 실행의 행 파일은 `outputs/runs/`에 있다. 그 기록도 그 뒤 세 파일을 고친 다음인 2026-11-01 20:38~21:06에 다시 돌린 것이었고, 지금 `outputs/live/`의 05 기록은 2026-11-03에 다시 돌린 것이다(기본 실행이 00:31, 켠 실행이 00:52에 끝났다).
- **덮어써지는 파일.** `outputs/baseline/01.json`은 01의 셀 38이 쓰고, `outputs/design_log.json`은 노트북마다 설계 기록 셀이 `write_design_log`(`mas_lab/view.py:69`)로 질문 하나씩 덧쓴다. 둘 다 그 노트북을 마지막으로 돌린 실행이 덮어쓴다.
  01은 기본 실행(2026-11-03 00:08) 뒤에 `.exercises` 실행(00:10)을 돌렸으므로 지금 `baseline/01.json`(00:10 마지막 쓰기)에는 `.exercises` 실행의 행이 들어 있고 기본 실행의 행은 `outputs/live/01-Workflow-vs-Agent.executed.ipynb`에 있다.
  `design_log.json`의 마지막 쓰기는 2026-11-03 00:52, 곧 05 `.exercises` 실행의 끝이다. 그 뒤에 돈 06은 `DECISION`이 비어 있어 셀 52가 기록하지 않았다.

EXA는 별도다. 기본 실행에서 00이 1회, 06이 21회(1+2+6+6+6) 부른다. 06이 출력한 검색당 비용은 0.007 USD이므로 합쳐 22회, 약 0.15 USD(0.154)다. `.exercises` 06은 47회, 약 0.33 USD다.
`cost_report.py`는 캐시 쓰기 단가를 계산하지 않으므로 모델 비용은 정확값이 아니라 하한이다 (`tests/cost_report.py:76`).

**스위치를 켜면 더 드는 규모** (기본 기록에서 모델 호출이 0이고 `.exercises` 기록에서 0보다 큰 셀만 읽은 값. 모델 호출 / 초):

| 켜는 것 | 모델 호출 | 초 | EXA |
|---|---:|---:|---:|
| 01 `직접 해보기` 2, 4 | 3 + 3 | 4.4 + 16.2 | 0 |
| 02 `직접 해보기` 1, 2 | 10 + 8 | 30.6 + 21.9 | 0 |
| 03 `직접 해보기` 3 | 6 | 12.5 | 0 |
| 04 `직접 해보기` 1 | 2 | 4.5 | 0 |
| 05 `전체 비교` 셀 (`RUN_OPTIONAL`) | **265** | **694.7** | 0 |
| 05 `직접 해보기` 1, 2, 3 | 29 + 17 + 5 | 84.9 + 46.8 + 12.6 | 0 |
| 06 `같은 구조 안의 변동` 셀 (`RUN_OPTIONAL`) | 7 | 43.5 | 6 |
| 06 `직접 해보기` 1, 2, 3 | 7 + 12 + 9 | 30.7 + 96.6 + 39.2 | 6 + 8 + 6 |

모두 켠 실행의 합은 01~06의 `.exercises` 기록 기준 모델 698회, 2,242.8초, 약 4.77 USD(4.7704)다(00의 3회, 12.6초, 0.0128 USD를 더하면 701회, 2,255.4초, 약 4.78 USD). EXA는 06이 47회, 00이 1회로 48회, 약 0.34 USD다. 05가 모델 호출의 65%(698회 중 451회)를 차지한다.
이 6개 기록은 모두 2026-11-03에 같은 코드로 돌렸다(위 "기록이 만들어진 때"). 켠 칸을 더한 값과 두 기록의 총합 차이는 다를 수 있다. 켠 실행은 기본 셀도 다시 돌리므로 같은 셀의 호출 수가 조금 다르다(02는 켠 칸이 18회인데 총합은 33회에서 53회로 20회 늘었다).

- **05의 `전체 비교` 셀이 이 표에서 가장 큰 단일 셀이다.** 이 실행 기록에서 265회, 694.7초(약 11.6분)였고 고지는 330회였다. 05의 첫 코드 셀 주석은 모델 약 220~330회, 10~15분이라고 적는다.
  이 셀을 켜자는 요청에는 이 규모를 알려 준다.
- 고지의 숫자는 예고 상한이다. 감사는 실측이 그 셀의 고지를 **넘으면 바로 실패**로 본다 (`tests/audit_live.py:36-37`). 한 셀에 고지가 여럿이면 그 합이 상한이다
  (`tests/audit_live.py:2`, `tests/audit_live.py:35-36`). 고지 없이 모델을 부른 셀도 실패다 (`tests/audit_live.py:31-32`). 배수로 봐주는 허용치는 없다.
  예고와 비교할 수 없는 유료 셀도 실패다. 비교하는 숫자는 셀 코드의 `model_calls=N`이므로 (`tests/audit_live.py:20`), 모델을 불러 놓고 고지에 이 숫자가 없는 셀은
  (EXA만 알리는 고지, `model_calls=len(topics)`처럼 숫자가 아닌 값) 그 셀마다 실패다 (`tests/audit_live.py:38-39`). 비교할 셀 코드가 든 실행본(`<stem>.executed.ipynb`)이 없는 기록도
  stem마다 실패다 (`tests/audit_live.py:27-28`, `tests/audit_live.py:59-60`). 이 규칙은 `tests/test_audit_live.py`가 지킨다. 지금 기록 13개에서 모델을 부른 98개 셀은
  모두 `model_calls=` 숫자가 있어 비교됐고, 넘은 셀은 없고, 실행본이 없는 기록도 없다(`uv run --no-sync python Day03_new/tests/audit_live.py`가 `AUDIT OK`). 그중 15개 셀은 실측이 고지와 같다(여유 0).
  수강생 환경에서는 모델이 도구를 몇 번 부르느냐에 따라 넘을 수 있다. 고지와 실측이 다르면 실측을 말한다.
- 호출 수는 실행마다 다르다. 05의 `hybrid 단순 사례와 복합 사례` 셀(고지 30회)은 지금 기본 실행 기록에서 모델 16회, `.exercises` 기록에서 14회였고(하위 에이전트를 끄기 전 기록은 17회와 14회), 05를 처음 돌린 시도에서는 22회였다(위 "05의 이력").
- 수강생 자신의 실행 비용은 실행 행의 `model_calls`, `input_tokens`, `usage_missing`(`mas_lab/runner.py:117-119`)과 EXA 결과의 `cost_dollars`로 본다. `cost_report.py`는 `DAY02_USAGE_LOG`가 설정된
  저자 실행의 기록(`rag_lab/settings.py:89`)을 읽는 도구라 수강생 환경에는 기록이 없다.
---

## 7. 수강생이 자주 막히는 곳

실제 실행(`outputs/live/`)에서 관찰된 것과 코드에서 읽은 것을 나눠 적었다. 관찰은 1회 관찰이다. "기본 실행 기록"은 `<노트북>.executed.ipynb`, "`.exercises` 기록"은 `<노트북>.exercises.executed.ipynb`이고, 셀 번호는 실행본 `cells`를 0부터 센 위치다. 기록이 끝난 시각은 6장 "기록이 만들어진 때"에 있다(모두 2026-11-03이고 00:05~01:03). `outputs/runs`의 수는 지금 있는 2,123개 행 파일 가운데 실제 모델을 부른 1,074개(하위 에이전트를 끄기 전 재실행이 쓴 115개와 이번 재실행이 쓴 115개 포함)를 다시 센 값이고, 저자가 다시 돌리면 늘어난다. 근거 노트는 `docs/audit/`에 있다. 이 장의 05 기록 관찰은 하위 에이전트를 끈 뒤의 지금 기록이고, 끄기 전 기록(2026-11-02 21:40~22:51)과 다른 곳은 그렇게 적었다.

- **"00의 키 확인 셀에서 멈춰요"**: `ANTHROPIC_API_KEY`나 `EXA_API_KEY`가 미설정이다. 멈춘 줄이 `require_key()`인지 `require_exa_key()`인지가 어느 키인지 알려 준다. `.env`를 직접 채우고 kernel을 재시작하게 한다.
- **`ModuleNotFoundError: mas_lab`**: kernel의 작업 폴더가 `Day03_new`가 아니거나 루트에서 `uv sync --locked`를 하지 않았다. 00의 첫 코드 셀 출력(`kernel 작업 폴더`, `sys.prefix`)을 보게 한다.
- **`BudgetExceeded: 턴 실행 시간 한도`가 두 번째 실행에서 나온다**: `Budget.started`는 만들 때 시작한다 (`rag_lab/evidence.py:31`). 한 `Desk`를 `max_seconds`(180초) 넘게 재사용하면 실패한다
  (`remaining`, `rag_lab/evidence.py:36-39`). 유료 셀마다 `make_desk`로 새 `Desk`를 만든다 (`mas_lab/runner.py:39`). 숫자를 올리기 전에 `Budget.events`를 보게 한다 (5장 3번).
- **같은 질문을 두 번 돌렸는데 호출 수와 토큰이 달라요**: 정상 변동이다. 01의 같은 질문 비교(기본 실행 기록 셀 38, 2절 T-1001과 기준선 `complex-double-pay`)에서 두 행은 모델 4회·22,488 입력 토큰과 6회·37,972로, 호출 수·토큰·도구 호출(5회와 7회)이 모두 달랐다.
  같은 셀의 `.exercises` 기록은 6회·37,020(도구 7회)과 5회·29,551(도구 6회)로 역시 갈렸다.
  05의 `twins` 셀(기본 실행 기록 셀 46)에서는 Single이 5회·29,765(도구 6회)와 6회·38,013(도구 7회), supervisor가 10회·28,091과 9회·22,482, hybrid가 9회·24,536(도구 7회)과 11회·41,703(도구 10회)으로 갈렸다.
  자동 검사는 Single과 supervisor의 앞 실행이 `False`, 뒤 실행이 `True`였고 hybrid는 반대로 앞 실행이 `True`, 뒤 실행이 `False`(`필수 사실`)였다. `.exercises` 기록의 같은 셀은 Single이 4회·22,847(도구 6회, `False`)과 7회·46,529(도구 9회, `True`), supervisor가 9회·23,841과 9회·22,161(둘 다 `True`, 도구 10회와 9회), hybrid가 10회·32,615(도구 9회, `False`)와 10회·33,734(도구 9회, `False`)다.
  구조 비교에서 이 폭보다 작은 차이에 이유를 붙이지 않는다.
- **자동 검사가 실패인데 답은 맞아 보여요**: `evaluate_row`는 문자열 포함 검사다 (`mas_lab/evaluation.py:20`). 공백과 쉼표를 지우고 비교하지만 (`mas_lab/evaluation.py:15`) `complex-double-pay`의 날짜 묶음은
  `9월20일`, `다음달20일`만 인정해서 (`data/gold.jsonl` 3행) 답이 `2026-09-20`이나 `9/20`으로 쓰면 `필수 사실` 칸이 실패한다. 현재 기록에서 이 모양이 나온 곳: 04 기본 실행 기록 셀 16의 `원문 포함` 행(`누락 사실`이 `9월20일`인데 `답에 20일 기한`은 True, 셀 15의 그 행 답은 `알파의 추가 약정 A-01에 따라 신청 기한은 다음 달인 2026-09-20까지입니다`),
  04 `.exercises` 기록 셀 16의 `사실+근거+불확실성` 행(셀 15의 답이 `신청 기한은 추가 약정 A-01에 따라 2026-09-20까지입니다`),
  05 기본 실행 기록 셀 7의 Single 기준선 `complex-double-pay` 행(답이 `신청 기한은 2026-09-20까지입니다`, 같은 행이 셀 13, 17, 27, 46에도 나온다)과 셀 44의 `hybrid` `complex-double-pay` 행(입력 토큰 41,703, 답이 `신청 기한은 2026-09-20까지로 보입니다`, 셀 46, 48에도 나온다),
  05 `.exercises` 기록 셀 7의 Single 기준선(답이 `알파 개별 약정에 따라 신청 기한은 2026-09-20까지입니다`, 같은 행이 셀 13, 17, 27, 46에도 나온다)과 셀 34의 `hybrid` 행(입력 토큰 32,615, 답이 `신청 기한은 개별 약정 A-01에 따라 장애 다음 달인 2026-09-20까지입니다`, 셀 35, 46에도 나온다), 셀 44의 `hybrid` 행(입력 토큰 33,734, 답이 `신청 기한은 2026-09-20로 보입니다`, 셀 46, 48에도 나온다), 셀 54 반복 3회(입력 토큰 32,689, 32,729, 24,581, 답이 모두 `2026-09-20`으로 쓴다).
  같은 사례가 통과한 곳은 01 두 기록(셀 37, 답이 `9월 20일까지`), 03 두 기록(셀 54, 답이 `장애 다음 달 20일, 즉 2026-09-20`이고 `.exercises` 기록은 날짜가 아니라 `인용 문서` 칸에서 실패했다), 04 기본 실행 기록의 `사실+근거+불확실성` 행(셀 16)과 `.exercises` 기록의 `원문 포함` 행(셀 16), 04 두 기록의 완성형 조립 행(셀 53), 05 두 기록의 비교표(셀 44)의 `single`·`supervisor` 행(기본 실행 기록의 답은 `9월 20일까지`, `.exercises` 기록의 답은 `장애 다음 달 20일, 즉 2026-09-20까지`)이다. 모델이 날짜를 어떻게 쓰느냐에 따라 실행마다 갈린다.
  하위 에이전트를 끄기 전 기록(2026-11-02 21:40~22:51)에서는 01 기본 실행 기록 셀 37과 03 기본 실행 기록 셀 54의 행도 이 모양으로 실패했으나 이번 재실행에서는 통과했다. 05 기본 실행 기록의 supervisor 행(셀 17, 20, 27)과 `persona` 행(셀 20)도 `누락 사실 [9월20일]`이지만 그 답 본문은 실행본과 `outputs/runs` 어디에도 남지 않아 표기는 확인하지 못했다.
  **이 실패는 의도된 것이다.** 01(셀 40), 04(셀 19, 54), 05(셀 10, 37)가 "표기만 다른 답이 `필수 사실`로 실패하는 경우"를 직접 읽게 하고, 05의 `CORRECT_BUT_FAILS`(셀 60)는 `2026-09-20`을 쓴 맞는 답이
  실패하는 것을 보이는 손으로 쓴 답이라 정답표가 그 표기를 받지 않는다는 데 기댄다. 그래서 정답표에 표기를 더하거나 `evaluate_row`를 풀어 통과시키지 않는다 (5장 1번).
  답이 틀렸다는 뜻이 아니라 검사의 한계이므로 원문(`data/business/sla-a-amendment.md`)과 사람이 대조하게 한다.
- **`hybrid`가 `complex-ops-log`에서 `insufficient`로 끝나기도 해요**: 저장된 `insufficient` 6건은 모두 `checked_worker`가 생기기 전 행이다. 원인 하나는 고쳤고, 다른 하나는 증상이 가려졌을 뿐 일부 원인을 아직 모른다. `outputs/runs`에서 이 조합의 실제 행은 50건이다(`answered` 43, `insufficient` 6, `budget_exceeded` 1).
  - **고친 것: Router의 `out_of_scope`.** Router가 `out_of_scope`를 고른 7건(행 `events`의 `router` `decision` 사건)은 모두 수정 전 행이다(파일 수정 시각 00:27~02:22). `Route.path`가 이 값을 허용했고 (`mas_lab/contracts.py:58`)
    Router 프롬프트는 fast와 slow, 결제·규정·장애 세 조사만 설명할 뿐 이 값은 설명하지 않았는데 (`mas_lab/hybrid.py:61-63`), 운영 문서(runbook, security) 질문이 그 범주 밖으로 읽혀 골라진 것으로 추정한다.
    `out_of_scope`를 고른 7건은 모두 `roles`가 비었고, `roles`가 비면 `dispatch`가 세 Worker를 모두 불러서 (`mas_lab/hybrid.py:84`) 모델 호출이 8~10회였다. 수정: Router에게는 `path`가 fast/slow뿐인
    `HybridRoute`를 보이고 (`mas_lab/hybrid.py:28-29`, `mas_lab/hybrid.py:60`), 범위 밖 판단은 코드가 한다(`scope_check`, `mas_lab/hybrid.py:50`). 그 뒤 43건(11-01 02:51~11-03 00:48)은 Router가 slow 37건, fast 6건이고 `out_of_scope`는 없으며
    slow 37건은 모델 6~10회, fast 6건은 3회였다. `test_hybrid_router_offers_only_the_paths_the_graph_routes`(`tests/test_structures.py:93`)가 Router에게 보이는 값이 fast/slow뿐임을, `test_hybrid_router_answer_outside_fast_and_slow_is_an_error_not_a_route`(`tests/test_structures.py:100`)가 그 밖의 값이 오류임을 지킨다. 프롬프트 문구는 고치지 않았고,
    slow 37건 모두 `roles`가 `outage`와 `policy`라 이 질문에도 가용률 조회 Worker가 하나 더 돈다. `build_handoff`의 triage는 여전히 `Route`를 쓴다 (`mas_lab/structures.py:95`).
  - **`insufficient` 6건의 길.** `out_of_scope` 7건 중 3건과 Router가 slow를 고른 3건(02:51~03:59)이다. 6건 모두 같은 길을 탔다. writer가 처음에 `answered`로 썼고, `validate_final`(`mas_lab/contracts.py:88`)이 `근거 없이 answered입니다.`를 내서 한 번 다시 쓰고 `insufficient`가 됐다(행 `events`의 `validate` 사건 둘).
    그 검사는 `answered`인데 `evidence_refs`가 빌 때 걸린다 (`mas_lab/contracts.py:96-97`). 6건 모두 `evidence_refs`가 0개였고 답 본문이 근거 번호(fact_ref, evidence_id)를 받지 못했다고 말한다. `answered` 40건은 모두 `evidence_refs`가 있었다(가장 적은 행이 2개). 즉 직접 원인은 **Worker 결과가 근거 참조 없이 writer에게 넘어온 것**이었다.
  - **지금 코드가 하는 일.** `checked_worker`(`mas_lab/workers.py:151`)가 `hybrid`의 Worker 결과를 받아 라벨이 붙은 참조에서 등록된 번호를 되살리고, 참조가 비었는데 `facts`가 있으면 이 Worker 자신의 도구 결과로 채운다(사건의 뜻은 아래 `worker_checked` 항목). 예전에는 `mas_lab/` 안에서 `validate_result`를 부르는 곳이 없었지만 지금은 `checked_worker`가 부른다 (`mas_lab/workers.py:169`). 다만 `validate_result`는 `complete`인데 근거가 없을 때만 문제로 보고 (`mas_lab/contracts.py:81`), 아래 원본 결과 14개는 모두 `uncertain`이라 `problems`가 비었다.
    이 코드가 들어간 뒤의 30건(11-01 17:49~11-03 00:48)은 `answered` 29, `budget_exceeded` 1이고 `insufficient`는 0이다. **이 27건은 원인이 없어졌다는 증거가 아니다.** 채움이 증상을 가렸을 수 있다.
  - **Worker가 실제로 돌려준 것.** 수정 뒤 두 번째 아홉 행(`docs/audit/ops-log-2-notes.md`, 원본 `docs/audit/ops_log2_raw.jsonl`)의 Worker 원본 결과 14개 가운데 8개가 `evidence_refs`가 비었다. 7개는 outage Worker다. 이 사례의 고객(`entity`)이 `공통`이고 (`data/cases.jsonl:4`) `load_outage`에 그 고객의 자료가 없어 (`mas_lab/desk.py:91`) `lookup_availability`가 `not_found`를 돌려주고, 그 결과에는 `fact_ref`가 없어 (`mas_lab/desk.py:93`) 채울 번호도 없다. 이 부분은 원인을 안다.
    나머지 1개는 정책(policy) Worker다. `facts` 10개와 자기 도구 결과의 번호 17개가 있었는데도 참조를 비웠고 (6번 행), 왜 비웠는지는 확인되지 않았다. 라벨이 붙은 참조를 낸 결과는 2개(4번, 7번 행, 모두 policy)이고 번호 24개가 되살아났다. 그래서 정책 Worker가 참조를 비우는 원인은 여전히 모른다고 말한다. 아홉 행은 비율을 말하지 못한다.
    더 보려면 `TASK_CONTRACT`(`mas_lab/workers.py:36`), `_run_with_messages`(`mas_lab/workers.py:118`), `after_join`(`mas_lab/hybrid.py:95`)을 읽고 행의 `events`, `evidence_refs`, `answer`를 본다. 05 기본 실행 기록의 비교표(셀 44)에서 hybrid `complex-ops-log`는 9회, `answered`, 자동 검사 `True`였고
    `.exercises` 기록의 같은 표(셀 44)에서는 3회(fast), `answered`, `True`였다(셀 47 전체 비교의 같은 사례 행은 7회, `answered`, 통과). 05 셀 50이 `insufficient`이면서 `인용 문서`가 어긋나는 모양을 짚는데, 이번 두 기록의 이 사례 행에는 그 모양이 없다.
- **`complex-ops-log`의 `hybrid` 행이 `인용 문서` 칸에서 실패해요**: 답은 맞는데 인용한 문서가 어긋나는 모양이다. 같은 사례를 아홉 번씩 두 번 돌린 기록(`docs/audit/ops-log-notes.md`, `docs/audit/ops-log-2-notes.md`)이 있다.
  - 첫 아홉 행은 4행이 실패했고, 그중 1행(2번)은 `budget_exceeded`라 답이 없으니 답이 있는 행으로는 3행(5, 6, 7번)이다. 두 번째 아홉 행은 1행(6번)이 실패했고 이 행이 그 묶음에서 채움(`filled`)이 있는 유일한 행이다. 그 행에서 writer의 최종 참조 6개는 채운 17개의 앞 6개였다.
  - 18행을 합치면 채움이 있는 5행 중 4행이 실패했고, 채움이 없고 답이 있는 12행은 0행이 실패했다. 첫 아홉의 채움 4행 중 둘(7, 8번)은 라벨 붙은 참조가 버려진 뒤의 채움이고, 지금 코드는 그 참조를 되살린다.
  - 18행, 하루의 상관관계다. writer의 참조가 왜 채운 순서를 따르는지는 시험하지 않았다. 검색은 18행 모두 같은 문서 여섯 개를 돌려줬으니 검색으로는 실패 행과 통과 행이 갈리지 않는다.
  - **고치지 않은 판단.** 이 실패는 코드를 고치지 않고 문서화된 관찰로 둔다. 처음에는 작업을 맡은 AI가 그렇게 판단해 저자에게 알렸고, 저자는 2026-11-02에 `rag_lab` 동기화가 유료 재실행을 필요로 하지 않게 되자 이를 확인했다. 코드를 바꾸면 유료 재실행이 또 필요하고 원인을 시험하지 않았기 때문이다 (`docs/DESIGN.md` 9.2절). 실패는 자동 검사와 실행 행에 그대로 보인다.
  - **수강생에게.** 행 `events`의 `worker_checked`에서 `filled`를 먼저 읽고 `cited_docs`와 대조하게 한다. 예산을 올리거나 `data/gold.jsonl`을 고쳐서 칸을 통과시키지 않는다 (5장 1번, 3번).
- **행의 `worker_checked` 사건은 무엇을 말하나요**: `hybrid`의 Worker마다 `checked_worker`가 하나 남긴다 (`mas_lab/workers.py:169`). 이 칸들은 19:39 수정 뒤 행에만 다 있다(그 앞 행에는 `recovered`가 없다). 실제 행 59개의 사건 158개에서 읽은 값이다(재실행 전 행 25개·사건 64개, 하위 에이전트를 끄기 전 기록 행 17개·사건 47개, 이번 재실행 행 17개·사건 47개).
  - `dropped`: 등록된 번호가 하나도 없어 뺀 참조 문자열 목록이다 (`mas_lab/workers.py:162`). 뺀 것은 `uncertainty`에도 적는다. 실제 값은 모두 outage Worker의 `INC-311`이고 8건이다. 재실행 전 행에 1건, 하위 에이전트를 끄기 전 기록에 4건(05 `.exercises` 기록의 전체 비교 `insufficient-no-policy` 행 하나와 반복 세 행), 이번 재실행에 3건이다(05 기본 실행 기록 셀 35의 Fast 강제 `insufficient-unknown-payment` 행, 05 `.exercises` 기록 셀 35의 같은 행과 셀 47 전체 비교의 `insufficient-no-policy` 행).
  - `recovered`: 라벨이 붙은 참조에서 등록된 번호를 찾아 살린 수다. Worker가 번호 그대로 쓴 것은 세지 않는다 (`mas_lab/workers.py:163`). 실제 값은 9(두 번), 10, 12(세 번)이고 모두 policy Worker다. 재실행 전 행의 값은 9(그때의 04 기본 실행 기록), 10(그때의 05 `.exercises` 기록), 12(그때의 05 기본 실행 기록과 두 번째 아홉 행의 4번·7번)다. 두 번째 아홉 행의 두 값을 합한 것이 위의 24개다. 하위 에이전트를 끄기 전 기록 행 17개에서는 모두 0이었고, 이번 재실행 행 17개에서는 04 `.exercises` 기록 셀 53의 `complex-double-pay` 행 한 건이 9이고 나머지는 0이다.
  - `filled`: 참조가 하나도 남지 않았고 `facts`가 있을 때 이 Worker의 도구 결과에서 채운 수다 (`mas_lab/workers.py:166`). 실제 값은 17(두 번째 아홉 행의 6번), 하위 에이전트를 끄기 전 기록의 14, 16, 14(그때의 05 기본 실행 기록의 `complex-double-pay`와 Fast 강제 `insufficient-unknown-payment`, 05 `.exercises` 기록의 전체 비교 `insufficient-no-policy`), 이번 재실행의 9다(05 `.exercises` 기록 셀 47 전체 비교의 hybrid `complex-ops-log` 행). 모두 policy Worker다. 이번 재실행에서 채움이 있는 행은 이 한 건뿐이다. 수정 앞 행의 값은 15, 16, 17, 18이다.
  - `filled`는 `facts`에 적힌 번호를 먼저 쓰고 없으면 전부 쓴다 (`mas_lab/workers.py:166`). 재실행 전 행에서는 앞 가지를 탄 적이 없다. 그때의 유일한 채움에서 `facts`에 번호가 하나도 없어 전부(17개)를 썼다. 하위 에이전트를 끄기 전 기록의 채움 세 건과 이번 재실행의 한 건(9)은 행에 Worker의 `facts`와 도구 결과가 남지 않아 어느 가지였는지 확인하지 못했다. 앞 가지는 `test_checked_worker_fill_prefers_ids_named_in_facts`로만 지켜진다.
  - 알려진 틈: `E-x, INC-311`처럼 한 문자열에 등록된 번호와 등록되지 않은 말이 함께 있으면 등록된 번호(`E-x`)만 남고, 떨어져 나간 `INC-311`은 `dropped`에도 `uncertainty`에도 적히지 않는다 (`mas_lab/workers.py:160-162`). 등록된 번호가 하나도 없을 때만 그 문자열이 `dropped`에 들어간다. `docs/audit/worker-refs-precision-notes.md`에 결정으로 적혀 있다.
- **`hybrid`가 유효 결제 P-7001을 재무 심사로 넘기겠다고 해요**: 고쳤다. 다만 코드가 덮는 범위는 정해져 있고 나머지는 모델이 맞히는 데 기댄다. 처음에 저자가 새 질문 감사에서
  "4월 1일에 결제한 P-7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요."를 `hybrid`로 1회 돌리자 모델이 환불 제안(proposal) 없이 `human_review`로 끝냈고, 답 본문은 P-7001을 재무 심사로 넘기겠다고 썼다.
  P-7001은 같은 청구서(`INV-2026-03`)에서 P-7002보다 먼저 승인된 유효 결제라 환불 대상이 아니다 (규칙 `data/business/billing-policy.md:3-4`, 결제 행 `data/support/billing.json:32-38`, P-7002는 `data/support/billing.json:41-47`).
  그때는 제안이 없으면 답을 그대로 돌려줘서 `check_refund`가 돌지 않았다. 돌았다면 `deny`가 나왔을 규칙은 `mas_lab/ledger.py:60-61`이다.
  쓰기 경로는 그때도 지켜졌다(원장 0건, 5장 8번). 지켜지지 않은 것은 모델이 제안 없이 낸 레이블과 문장이었다.
  - **지금 코드가 하는 일.** 제안이 없거나 `action`이 `refund`가 아닌 답은 `gate_answer`가 `check_named_payment`로 보낸다 (`mas_lab/gate.py:35-36`). `hybrid`는 `gate` 노드에서 `check_named_payment`를 부르고 (`mas_lab/hybrid.py:141`), `run_case`는 그래프가 끝난 뒤(`hybrid`, Handoff, `mas_lab/runner.py:93`)나 Agent가 끝난 뒤(나머지 구조, `mas_lab/runner.py:102`) 마지막 turn의 질문을 `gate_answer`에 넘겨 부른다.
    결제 번호는 **질문**에서만 `_PAYMENT_ID`로 읽는다 (`mas_lab/gate.py:13`, `mas_lab/gate.py:18-19`). `P-7001`, `p-7001`, `P7001`, `p7001`(하이픈이 없으면 숫자 네 자리 이상)은 모두 `P-7001`로 읽고, `p99`, `p50`, `p7001a`는 번호로 읽지 않는다 (`_PAYMENT_ID`, `mas_lab/gate.py:12-13`). 철자 표는 `test_payment_id_spellings_all_name_the_same_payment`(`tests/test_structures.py:968`)와 `test_payment_id_spellings_decide_which_numbers_the_gate_names`(`tests/test_structures.py:983`)가 지킨다.
    답 본문이 부른 번호는 검사받는 쪽의 주장이라 읽지 않는다 (`test_payment_is_read_from_the_question_not_the_answer_text`, `tests/test_structures.py:385`).
    질문의 번호가 모두 이 고객의 아는 결제이면 (`checkable`, `mas_lab/gate.py:55`) 번호마다 그 결제와 그 결제의 금액으로 탐침 제안을 만들어 `check_refund`에 묻는다 (`mas_lab/gate.py:65-66`). 탐침은 답이 `denied`·`human_review`이거나 질문에 `환불`이 있을 때 돈다 (`claims_a_block`, `mas_lab/gate.py:63`). 그래서 환불 질문이면 `answered` 레이블도 뒤집힌다 (`test_refund_question_under_another_label_is_overruled`, `tests/test_structures.py:205`). P-7001이면 `deny`다 (`test_first_payment_without_proposal_is_denied_by_the_code_gate`, `tests/test_structures.py:163`).
    탐침은 **원장에 쓰지 않는다.** `check_refund`만 부르고 `execute_approved`는 부르지 않으며, 탐침이 모두 `deny`면 `denied`, 그 밖이면 `human_review`로 두고 (`decisions`, `mas_lab/gate.py:72`) 판정에 `allow`나 `needs_approval`이 있으면 `_NOT_EXECUTED` 문장 "환불 제안이 없어 아무것도 실행하지 않았습니다"를 붙인다
    (`_NOT_EXECUTED`, `mas_lab/gate.py:69-70`, `test_refundable_payment_without_proposal_is_reviewed_and_never_written`, `tests/test_structures.py:177`). 판정이 모델의 outcome과 다르면 고객이 읽는 `text`와 `uncertainty`를 코드가 쓴 문장으로 **통째로** 바꾸고 `action`이 `refund`가 아닌 제안도 지운다 (`update`, `mas_lab/gate.py:87-88`). 원래 문장 앞 80자와 지운 불확실성은
    `gate_text_replaced` 사건의 `replaced`, `dropped_uncertainty` 칸에 남는다 (`mas_lab/gate.py:90`). 판정이 같은 레이블이면 모델 문장을 두고 그 안에 없는 코드 이유만 뒤에 붙인다(`gate_text_appended`, `mas_lab/gate.py:92-97`).
    이미 옮긴 답에 다시 부르면 불확실성도 사건도 더하지 않는다 (`_settle`, `mas_lab/gate.py:80-83`). `run_case`가 그래프를 지난 답에 `gate_answer`를 다시 부르기 때문이다 (`mas_lab/runner.py:93`).
    `hybrid` 그래프만 불러도 (`test_hybrid_graph_alone_checks_the_named_payment`, `tests/test_structures.py:524`), gate 노드가 없는 Handoff도 (`test_handoff_run_checks_the_named_payment`, `tests/test_structures.py:543`) 같은 결과가 나온다.
    환불 제안이 있으면 `refund_decision`이 제안의 결제를 판정하고, 질문이 가리킨 결제와 다르면 정책을 통과해도 `needs_approval`로 둔다 (`mas_lab/gate.py:22-29`). 질문에 번호가 없으면 비교할 것이 없어 제안의 판정이 그대로 간다 (`named`, `mas_lab/gate.py:26`).
  - **철자의 기록.** 첫 관찰은 새 질문 감사 세 번째 판정의 N5다(`docs/audit/new-question-3-notes.md`). 같은 문장에서 번호만 `p7001`로 쓴 질문을 옛 게이트는 읽지 못해 `gate_skipped`(`named` 빈 목록)로 끝났고, 모델의 틀린 문장(P-7001을 재무 심사로 넘기는 문장)이 고객에게 그대로 갔다. 철자를 고친 뒤(`docs/audit/gate-id-forms-notes.md`) 같은 문장을 실제 모델로 세 번 돌렸다(`docs/audit/id-spelling-rows-notes.md`, 행 파일 `docs/audit/rows/`). S1 `p7001`, S2 `P7001`, S3 `p-7001` 모두 `denied`, 원장 0, `gate_skipped` 없음이다. 게이트 앞 레이블은 모두 `human_review`였고(S2는 `action`이 `none`인 제안 포함), 문장은 코드가 바꿨다. 경로를 세 번 관찰한 것이지 비율이 아니다.
    `lookup_payments`는 `payment_id`를 정확히 일치로만 찾아서 (`mas_lab/desk.py:81`) `p7001`로는 `not_found`가 나오고, 세 행에서 모델이 스스로 `P-7001`로 바꿔 읽었다. 코드가 쓴 문장 `P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.`는 참이지만 얇다. P-7001이 대상이 아니라는 것만 말하고, P-7002가 심사로 간다는 것도 `예외` 요청에 대한 답도 없다. 최종 `evidence_refs`는 모델 것 그대로다(`update`에 그 칸이 없다, `mas_lab/gate.py:86-88`). 이 세 행에서 타지 않은 길은 게이트 앞 `denied`와 모델의 환불 제안이다.
  - **코드가 덮지 못하는 것.** 아래는 코드와 손으로 쓴 답(오프라인, 모델 호출 0회)으로 확인한 것이고, 실제 행에서 본 것은 그렇게 표시했다.
    질문이 이 고객의 아는 결제만 가리키지 않으면(번호 없음, 모르는 번호가 하나라도 섞임, `_PAYMENT_ID`가 읽지 않는 꼴) 검사하지 못한다. 막는 레이블이면 모델의 outcome과 문장을 그대로 두고 `uncertainty`에
    "코드 게이트가 이 판단을 검사하지 못했습니다" 줄과 `gate_skipped` 사건을 남기고 (`_UNCHECKED`, `mas_lab/gate.py:56-57`), 다른 레이블의 환불 질문이면 답을 그대로 두고 `gate_skipped` 사건만 남긴다 (`mas_lab/gate.py:58-62`). 이 사건은 서로 다른 `named` 목록마다 한 번만 기록된다 (`named`, `mas_lab/gate.py:60`).
    실제 행: 세 번째 판정의 R5는 모델이 맞혔고, N5는 위의 틀린 문장이 지나갔다.
    후속 turn이 번호를 말하지 않는 경우("그럼 어떻게 되나요?")도 마지막 turn의 질문만 보므로 여기에 든다 (`test_run_checks_the_question_of_the_last_turn`, `tests/test_structures.py:552`).
    `환불`을 말하지 않은 질문의 `answered` 같은 레이블은 보지 않는다 (`claims_a_block`, `mas_lab/gate.py:63`). 번호를 읽지 못한 질문에서 환불을 접수했다는 문장이 `answered`로 나오면 지나가고, `validate_final`도 이 문장은 보지 않는다 (`evidence_refs`, `mas_lab/contracts.py:96-99`).
    레이블이 같으면 문장은 모델 것으로 남아 `denied`인데 이유가 틀린 문장도 코드 이유가 뒤에 붙을 뿐 지워지지 않는다 (`missing`, `mas_lab/gate.py:92-95`, `test_same_label_with_a_wrong_reason_gets_the_code_reason_appended`, `tests/test_structures.py:344`). 실제 행 N1은 맞는 답에 같은 사실이 다른 말로 두 번 적혔다.
    문장을 바꾸면 참인 정보도 함께 사라진다 (`update`, `mas_lab/gate.py:88`). 실제 행 R6은 P-9002와 P-7002의 다음 단계를 맞게 적은 모델 답이 "둘 다 환불 대상이 아니다"라는 문장만으로 바뀌었다. 한 답에 크레딧 설명이 함께 있어도 그 문장은 사라진다.
    `evidence_refs`와 `cited_docs`는 사라진 문장을 설명하는 채로 남고, 거부된 환불 제안은 `proposal`과 모델의 `reason`이 남는다 (`test_overrule_on_the_proposal_path_keeps_the_rejected_proposal_and_drops_stale_lines`, `tests/test_structures.py:305`, 실제 행 없음).
    모델이 제안 없이 레이블을 틀리게 내는 빈도는 모른다.
    앞 turn의 환불 제안은 게이트를 지나지 않는다. `_note_ungated_proposal`이 `earlier_turn_proposal_ungated` 사건만 남기고 (`mas_lab/runner.py:105-108`) 원장에는 쓰지 않는다. 이 사건은 저장된 실제 행에 0건이고 단위 시험(`test_handoff_records_the_refund_proposal_of_an_earlier_turn_that_no_gate_saw`, `tests/test_structures.py:921`)으로만 확인했다.
    두 turn에서 서로 다른 번호로 `gate_skipped`가 두 번 남는 길도 실제 행에서는 보지 못했다. 세 번째 판정의 N4와 N4b가 turn 2에서 `budget_exceeded`로 끝났다. `run_case`는 Desk와 예산을 행마다 하나만 만들어 (`make_desk`, `mas_lab/runner.py:61`) 두 turn이 검색 한도 6회를 나눠 쓰기 때문이다 (`FIXED_BUDGET`, `mas_lab/runner.py:24`). 게이트 결함이 아니고, `FIXED_BUDGET`을 올려서 보지 않았다.
    제안 경로의 행에는 같은 `gate` 사건이 둘 남는다(세 번째 판정의 N2, R4, 05 셀 35의 `complex-double-pay`). `approve` 노드의 `gate_answer`가 사건을 남긴 뒤 `interrupt`가 올라가 그 결과가 버려지고 (`mas_lab/hybrid.py:152-153`), `run_case`가 게이트 전 답으로 `gate_answer`를 다시 부르기 때문이다 (`mas_lab/runner.py:93`). 원장에는 쓰지 않는다.
  - **새 질문 감사에서 관찰한 것.** 첫 판정은 이 항목 처음의 관찰이다(질문 3개 중 P-7001이 틀려 미충족). 두 번째 판정은 고친 직후의 감사다. `hybrid`에 질문 6종을 8행(P-7001 질문 3회 포함) 돌렸고 모델 호출 63회(한도 80회), 모든 행의 상태는 `ok`, 원장은 0건이었다. 그럴듯하게 틀린 행은 8행 중 0행, 미리 적은 기대와 같은 행은 7행이고, P-9001·P-7001을 함께 말한 행은 레이블만 다른 편차로 셌다. 그때 판정은 "게이트가 일했다고 말할 수 있는 것은 P-7001 3행뿐"이었다. 그 행 파일은 지금 `outputs/runs`에 없고 `docs/DESIGN.md` 10.4절에 기록이 있다.
    세 번째 판정(`docs/audit/new-question-3-notes.md`)은 철자 수정 전의 게이트(`mas_lab/gate.py`)로 앞의 8행 질문과 새 경계 질문을 돌린 14행(13행 + N4 재관찰 N4b, 질문 12종)이다. 모델 호출 127회(한도 150회), `ok` 12행, `budget_exceeded` 2행(N4, N4b), 원장 0건이다. 표본이 이만큼이라 비율은 말하지 않는다. 그럴듯하게 틀린 행은 N5 1행이고, 미리 적은 기대와 같은 행은 11행이다(N4, N4b, N5가 아니다). 정확한 레이블만 인정하면 10행이다.
    누가 일했는지는 게이트 앞 답을 기록해 직접 읽었다. 틀린 답을 참인 문장으로 바꾼 행이 3(R1~R3, P-7001 질문, 게이트 앞은 모두 `human_review`), 참인 답을 더 짧은 참인 문장으로 바꾼 행이 1(R6), 참인 답에 문장을 덧붙인 행이 1(N1), `uncertainty` 줄만 더한 행이 제안 경로 2(N2, R4)와 검사하지 못했다는 표시 2(R5, N5), `gate_skipped` 사건만 남긴 행이 3(N3, N4, N4b), 사건이 없는 행이 2(R7, R8)다. 두 번째 판정 때 모델 `uncertainty`가 뒤집힌 재무 심사 경로를 그대로 설명하던 흔적은 `gate_text_replaced` 4행에서 사라졌다.
    05 켠 실행의 전체 비교(`RUN_OPTIONAL`, 지금 `.exercises` 기록 셀 47)에서 `policy-deny-normal`과 `policy-human-old`는 5개 구조 10행이고, 10행 모두 탐침을 지났고 환불 제안 경로를 탄 행은 없다. 모두 모델의 레이블과 판정이 같아(`denied` 5, `human_review` 5) 문장 교체 0건, `gate_skipped` 0건, 원장 0건이고 10행 모두 코드 이유가 덧붙었다(`gate_text_appended`). `action`이 `none`인 제안을 단 행이 1이다(`single_skills`의 `policy-deny-normal`). 기본 실행 기록 01~05의 행에는 탐침을 지난 행이 없다.
  - **수강생에게.** `denied`나 `human_review` 행은 `events`의 `gate` 사건에 `probe: True`가 있는지 먼저 보게 한다. 있으면 코드가 질문의 결제를 검사한 행이고, `gate_skipped`가 있으면 코드가 검사하지 못한 행이며, `gate_text_replaced`가 있으면 고객 문장을 코드가 바꾼 행이다.
    "게이트가 막은 것"과 "게이트가 보지 않은 것"을 나눠 읽게 한다. 노트북 02(셀 5, 39), 03(셀 54), 05(셀 36)는 `gate_answer`를 `question=` 없이 부르고, 이 셀들은 기본 실행 기록과 `.exercises` 기록 모두에서 돌았다. 05 셀 11은 `question=`을 넘긴다. 제안 없는 `denied`·`human_review`가 이 셀들을 지나면
    같은 "검사하지 못했습니다" 줄이 붙는다 (`test_gate_answer_without_a_question_reports_unchecked`, `tests/test_structures.py:422`). 현재 실행본 13개의 출력에는 이 줄이 한 번도 나오지 않았고, `outputs/runs` 실제 행의 `uncertainty`에도 없다. 감사 기록은 `docs/DESIGN.md` 10.4절 10번에 있다.
- **Fast를 강제했는데 Slow로 안 넘어가요**: `force_path`는 Router의 판단만 덮어쓴다 (`mas_lab/hybrid.py:64`). Slow 전환(`fallback_to_slow`)은 검증 문제가 `reinvestigate`로 분류될 때만 일어난다
  (`mas_lab/hybrid.py:132`). `validate_final`은 인용 소속, 금액 출처, outcome 일관성만 보고 빠진 사실을 검사하지 않는다 (`mas_lab/contracts.py:88`). 그래서 05는 전환 경로가 실제로 나오는 사례를 따로 쓴다.
  05의 `Fast Path 강제`(셀 35, 기본 실행 기록과 `.exercises` 기록 모두)에서 `complex-double-pay`는 전환 없이 끝났고(`Slow 전환` False, 자동 검사 `False`) `insufficient-unknown-payment`는 전환했다(`Slow 전환` True).
- **`supervisor` 행의 `max_worker_overlap_seconds`가 0이에요**: 지금 코드에서는 위임이 겹치지 않았다는 뜻이다. `delegation_spans`가 `task` 호출 하나를 `worker` 구간 하나로 남기고 (`mas_lab/workers.py:75`, 붙이는 곳 `mas_lab/structures.py:64`), 행의 칸은 `overlap_seconds`로 잰다 (`mas_lab/runner.py:120`).
  `overlap_seconds`는 구간 둘 이상이 동시에 도는 시간이다 (`mas_lab/trace.py:80-81`). `task`로 묶인 시간만 재므로 Supervisor의 판단과 최종 응답 시간은 들어가지 않고, 겹친 동안 Worker들이 실제로 무엇을 했는지도 말하지 않는다. 병렬 여부는 모델이 정한다 (`build_supervisor`, `mas_lab/structures.py:57`).
  `outputs/runs`의 실제 `supervisor` 행 182개 중 이 코드 뒤의 76행(11-01 17:46~)은 모두 구간이 있고 53행이 0보다 크다. 0인 23행은 위임이 1번인 행 18개와 차례로 위임한 행 5개다(그중 하위 에이전트를 끄기 전 기록의 `insufficient-no-policy` 행은 두 구간 중 하나가 아래의 `general-purpose` 위임이다). 그 앞의 106행은 구간이 없어 모두 0이니 겹침이 없었다는 근거가 되지 못한다. 05 비교표(셀 44)의 `supervisor` 네 행은 기본 실행 기록에서 0, 4.590, 7.206, 0초, `.exercises` 기록에서 0, 5.333, 8.667, 5.463초다.
- **`max_model_calls`를 낮췄는데 측정 호출이 더 많아요**: 지금 코드에서는 Router와 triage 호출도 예산으로 센다. `structured_call`의 설명은 "Router와 triage의 모델 호출. allowlist_middleware를 거치지 않으므로 예산의 model 호출로 여기서 센다."이고 다음 줄이 `desk.budget.consume("model")`이다 (`mas_lab/structures.py:33-34`). hybrid Router는 `route = structured_call(desk, model, HybridRoute,`로 (`mas_lab/hybrid.py:60`), Handoff triage는 `route = structured_call(desk, model, Route,`로 (`mas_lab/structures.py:95`) 이 함수를 부른다. 나머지 호출은 `allowlist_middleware`의 `bounded_model`이 센다 (`mas_lab/workers.py:53-54`).
  실제 행의 `budget["model"]`과 `model_calls`(`mas_lab/runner.py:117`)는 세 번째 판정 14행 중 14행, 두 번째 아홉 행 중 9행에서 같았고, `outputs/runs`에서 11-01 10:27 뒤의 실제 행 467개 가운데 464개가 같다. 다른 3행은 모두 하위 에이전트를 끄기 전 기록(2026-11-02 21:40~22:51)의 05 `.exercises` 기록 supervisor 행이고 `budget["model"]`이 1 적다(아래). 이번 재실행 115행은 모두 같다. 그 앞에는 `budget["model"]`이 1 적은 행이 237개 있다(hybrid 184, handoff 52, supervisor 1). 이 항목의 앞 판이 적은 "Router와 triage는 세지 않는다"는 그때의 코드다.
  두 수는 세는 곳이 달라 지금도 어긋날 수 있다. `ModelMeter`는 콜백으로 모든 모델 호출의 시작을 세고 (`on_chat_model_start`, `mas_lab/trace.py:19`), `Budget`은 위의 두 곳만 센다. `create_deep_agent`가 자동으로 더하는 `general-purpose` 서브에이전트에는 `allowlist_middleware`가 물려지지 않는다(`deepagents/graph.py`의 `gp_middleware`). 지금 코드는 `mas_lab`을 import할 때 anthropic provider 전체에서 이것을 끈다(`mas_lab/__init__.py:7-9`가 `use_designed_subagents_only`를 부른다, `use_designed_subagents_only`의 정의는 `mas_lab/harness.py:25`). `build_supervisor`(`mas_lab/structures.py:56`)를 포함해 노트북이 직접 부르는 `create_deep_agent`에도 적용된다. 켠 상태와 끈 상태의 비교는 02 3절이 모델 없이 보여 준다(`framework_default_subagent:31`, `task_targets:46`). 끈 뒤에 돌린 이번 재실행(2026-11-03 00:05~01:03)의 새 행 115개 가운데 `supervisor` 19행에는 `general-purpose`에 위임한 행이 0이고, 19행 모두 `budget["model"]`이 `model_calls`와 같다. 하위 에이전트를 끄기 전 기록(2026-11-02 21:40~22:51)에는 `supervisor` 19행 중 3행(05 `.exercises` 기록의 전체 비교 `insufficient-unknown-payment`, `insufficient-no-policy`, `approval-refund-now`)에서 모델이 `general-purpose`에 `no-op` 둘과 `dummy` 하나를 위임했고, 세 행 모두 `budget["model"]`이 `model_calls`보다 1 적었다(7과 8, 5와 6, 10과 11). 그 행들과 03:19의 supervisor 1행(모델이 `general-purpose`에 `no-op`을 위임)이 지금 `outputs/runs`에서 `general-purpose`가 든 행의 전부이고, 모두 이 설정 전에 돈 것이다. 라이브러리 안의 다른 호출(요약 미들웨어 등)은 실행으로 확인하지 못했다.
- **도구를 추가했는데 Agent가 못 써요**: `allowlist_middleware`의 `bounded_model`이 허용 목록 밖의 도구를 숨기고 (`mas_lab/workers.py:53-55`) `bounded_tool`이 호출도 거부한다 (`mas_lab/workers.py:63-65`). `ROLE_TOOLS`(`mas_lab/workers.py:25`)나
  `OWNER_TOOLS`(`mas_lab/structures.py:85`)에 추가한다. 우회하려고 미들웨어를 빼지 않게 이유부터 묻는다.
- **`InvalidUpdateError`, `GraphRecursionError`**: 03의 `# 실패 재현:` 셀이 일부러 내는 오류다. 전자는 reducer 없이 동시에 같은 키를 쓸 때(`merge_results`가 있는 이유, `mas_lab/contracts.py:103`), 후자는 재귀 한도를 넘을 때다.
- **승인 뒤 원장이 두 건이에요**: 04의 `interrupt` 앞 부작용 재현(셀 41)에서 승인 대기 시점 1건, 재개 뒤 2건이 나온다. 재개하면 노드가 처음부터 다시 돌기 때문이다 (`mas_lab/hybrid.py:140`).
  응답 유실 뒤 키 없이 재시도하면 `R-0001`, `R-0002` 두 건, 멱등 키로 재시도하면 한 건이다(셀 47, `refund`, `mas_lab/ledger.py:35`, 게이트의 `idempotency_key`는 `mas_lab/gate.py:37`에서 만든다).
- **Worker가 낸 `evidence_refs`가 통과했는데 근거가 아니에요**: 스키마 통과와 근거 검증은 다른 검사다 (`mas_lab/contracts.py:79`). 등록된 근거만 인정하는 곳은 `validate_result`(`mas_lab/contracts.py:78`)이고, 숫자의 출처는 `validate_final`이 본다.
  `validate_final`은 금액과 비율만 보며 날짜나 문장의 뜻은 보지 않는다 (`validate_final`, `mas_lab/contracts.py:88-92`).
- **05 평균이 이상해요**: 실패 행을 섞거나 빼면 평균이 달라진다. 05의 평균 표 셋(`평균 0`, `평균 A`, `평균 B`, 셀 48)에서 `남은 사례`, `제외한 행` 칸으로 무엇이 평균에 들어갔는지 확인하게 한다.
  Single의 평균 호출은 기본 실행 기록에서 4.0회(평균 0), 3.3회(평균 A, 빨리 끝난 실패 행 포함), 4.0회(평균 B, 실패 행 제외), `.exercises` 기록에서 4.5회, 3.7회, 4.5회였다. 두 기록 모두 Single의 평균 B는 `제외한 행`이 1이고 `남은 사례`가 그대로라 평균 0으로 돌아갔다. 두 기록 모두 hybrid는 평균 B에서 `제외한 행`이 2이고 `남은 사례`가 `complex-ops-log` 하나라 다른 사례의 평균이 된다(평균 호출은 기본 실행 기록에서 10.0회, 7.7회, 9.0회, `.exercises` 기록에서 6.5회, 5.3회, 3.0회). 하위 에이전트를 끄기 전 `.exercises` 기록에는 `남은 사례`가 바뀐 구조가 없었다.
- **`followup-handoff`의 `outcome`이 실패로 나와요**: 확인이 필요하다. `outputs/runs`에 이 사례의 행은 0건이고(가짜 모델 행 포함), `run_case`로 돌린 기록이 없다. 05의 전체 비교도 이 유형을 넣지 않는다. 같은 `turns`를 돌린 기록은 02의 셀 36, 38뿐이며 행을 남기지 않는다.
  02 셀 39에서 턴 1은 담당자가 `answered`, 게이트 뒤 `needs_approval`, 턴 2는 담당자도 게이트 뒤도 `answered`였고 원장 0건이다(기본 실행 기록과 `.exercises` 기록 모두). 턴 2가 `needs_approval`로 바뀐 앞 기록의 모양은 지금 두 기록에 없다.
  코드: Handoff는 한 턴 안에서만 앞 담당자의 제안을 넘기고 (`proposal`, `mas_lab/structures.py:115`) 새 고객 턴을 여는 triage가 비운다 (`proposal`, `mas_lab/structures.py:100`). 가짜 모델로는 `test_new_customer_turn_is_not_relabelled_by_the_refund_proposed_in_the_earlier_turn`(`tests/test_structures.py:878`)이 이 흐름을 지킨다. 행이 나오면 `proposal`과 `events`의 `gate`, `earlier_turn_proposal_ungated` 사건을 먼저 보게 한다.
- **06에서 직렬이 병렬의 세 배로 안 나와요**: 합성(synth) 구간은 병렬에서 전체의 절반을 넘고 직렬에서는 세 Worker가 차례로 도는 시간에 더해진다. 1회 관찰에서 병렬 44.8초, 직렬 71.3초였고 (`마지막 Worker 이후 초` 25.6초와 20.6초), 모델 호출은 병렬 8회, 직렬 8회였다. `.exercises` 기록에서는 병렬 40.0초, 직렬 77.4초였다.
  `Worker 1개로 소주제 하나 조사` 셀(셀 12)은 두 기록 모두 모델 3회였다. 첫 호출이 검색 둘을 함께 불렀고 세 번째 검색은 `search_limit`으로 거절됐다. 하위 에이전트를 끄기 전 `.exercises` 기록에서는 같은 셀이 모델 2회로 검색 2회를 끝냈다. 또 `max_concurrency=1`은 직렬 모드에서 Worker 안의 도구 호출까지 직렬로 만들지만 연쇄 모드에는 이 설정이 없다 (`mas_lab/research.py:131`).
  직렬과 연쇄의 차이는 입력 외에도 이 점이 다르다.
- **06에서 품질 차이가 구조 때문인가요**: 세 실행이 본 URL의 겹침(Jaccard)이 기본 실행 기록에서 0.19~0.65(병렬-직렬 0.65, 직렬-연쇄 0.19, 병렬-연쇄 0.27), `.exercises` 기록에서 0.28~0.50(병렬-직렬 0.50, 직렬-연쇄 0.28, 병렬-연쇄 0.33)였다. 겹침이 낮은 쌍은 다른 자료를 읽은 것이므로 구조 탓이라고 단정하지 않는다 (`mas_lab/research.py:146`).
- **EXA 결과의 `published`가 비어 있어요**: 06 기본 실행 기록 셀 7(EXA 검색 1회)에서 결과 3건 중 1건만 게시일이 있었고 2건이 `None`이었다. 오류가 아니고 06의 출처 표에는 `확인 안 됨`으로 나온다.
  00의 EXA 셀(셀 17)은 `published`를 출력하지 않아 이 칸을 볼 수 없다. 이 항목의 이전 판은 00 쪽에서도 게시일이 비어 있었다고 적었으나 실행본 출력과 맞지 않아 고쳤다 (`published`, `docs/DESIGN.md:892`).
  같은 질의도 호출마다 결과가 달라질 수 있으므로 몇 건이 비는지는 1회 관찰이다.
- **EXA 질의가 거부돼요**: 고객 이름과 내부 문서 이름(`DEFAULT_BLOCKED`, `mas_lab/exa.py:19`)이나 내부 번호가 든 질의는 호출 전에 `assert_public_query`가 막고 (`mas_lab/exa.py:30`), 메시지는 `내부 정보가 든 질의는 외부로 보내지 않습니다: [...]`이다 (`found`, `mas_lab/exa.py:34`). 번호 패턴 `INTERNAL_PATTERN`(`mas_lab/exa.py:18`)은 `P-7001`, `p-7001`, `P7001`, `p7001`과 `INV-`, `INC-`, `T-` 번호를 대소문자 없이 읽고, 번호 뒤에 한글 조사가 붙어도(`p7001을`) 막는다.
  틈이 양쪽에 있다. `KP-7001`, `P-7001a`, `p7001a`는 통과하고, 번호가 아닌 `inv-test`, `T-800`, `Tesla P4000`은 막힌다(모델과 EXA 호출 없이 `assert_public_query`에 넣어 확인한 값이다). 의도된 동작이다. 질의를 일반적인 표현으로 바꾸게 한다 (5장 9번).
- **`single_skills`가 왜 더 비싸요**: Skill 본문을 읽으면 입력이 는다. 05 셀 27에서 첫 호출 입력이 `single_skills` 5,678토큰, Single 2,410토큰이었다(두 기록 모두). 1회 관찰이므로 Skill이 낫거나 나쁘다고 결론 내리지 않는다.

---

## 8. 문서와 코드가 다른 곳

`docs/DESIGN.md`는 구현 전의 설계 계약이다. 수치는 설계 근거이며 구현 뒤 달라질 수 있다고 스스로 밝히고(2절 4번), 공개 이름 표(8.12절)와
코드가 다르면 코드가 우선한다고도 적는다. 수강생이 설계 문서의 숫자나 이름을 근거로 물으면 다음 순서로 확인한다.
- 호출 수, 시간, 비용: 6장의 실측과 노트북 출력. 설계 문서의 호출 규모 추정은 실측 전 값이다 (예: 05의 비교표 셀은 설계 추정보다 실측이 크다).
- 이름과 위치: 4장의 줄 번호와 `grep -n`. 설계 문서의 모듈 설명보다 코드가 우선한다.
- 설계 시점에 "확인하지 못했다"고 적힌 항목(예: EXA 응답 형태)은 00과 06 실행에서 확인된 값이 있는지 노트북 출력을 먼저 본다.

---

## 9. 인용 검증

이 문서의 `파일:줄` 인용과 심볼은 `sed -n '<줄>p' <파일>`이나 `grep -n`으로 확인한다. 코드가 바뀌어 줄이 움직이면 고친다. 저자는 저장소 루트에서 인용은 `docs/audit/tools/check_citations.py`로, 비용표는 `docs/audit/tools/check_costs.py`로 검사한다(전체 경로는 `Day03_new/docs/audit/tools/...`). 검사기가 통과해도 백틱 식별자가 없는 문장, 접두사 없이 적어 다른 폴더를 뜻하는 인용이나 저장소 밖 인용, 문장이 말하는 내용은 확인되지 않으니 손으로 읽는다(`docs/audit/tools/README.md`).
답할 때 쓰는 인용도 먼저 확인한다. 6장의 숫자는 `outputs/live/*.json`과 `tests/cost_report.py`를 다시 돌려 대조한다. 7장의 실제 행 수는 `outputs/runs`와 `docs/audit/`의 노트로 다시 센다.
시험 결과는 나온 그대로 말한다. 저장소 루트에서 `uv run --no-sync python -m pytest Day03_new/tests -q`로 전체를 돌리면 지금 `625 passed`(실패 0)이고 (2026-11-02, `tests/test_harness.py` 추가 뒤), 복사본 시험의 네 칸도 모두 통과한다. 빼고 세는 칸이 없으므로 `--deselect`를 쓰지 않는다. 일부만 돌린 결과를 전체 통과로 말하지 않고, 실패가 나오면 지우거나 빼지 않고 실패로 그대로 말한다. 복사본 시험이 실패하면 머리말의 규칙을 따른다. 이 숫자는 시험이 늘거나 줄면 달라지므로 말하기 전에 다시 돌려 확인한다.
