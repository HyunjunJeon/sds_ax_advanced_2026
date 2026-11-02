# AGENTS.md — Day04_new: Agent Capability · Tool Interface · MCP · Skill 노트북 과정

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day04_new 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** 요구사항 인터뷰 에이전트 하나(`requirements-interview` Skill + MCP 서버의 도구 + Deep Agent)를 만들면서,
능력(capability)이 지침(Skill)·도구·실행 제어·상태로 이루어진다는 것, 도구 인터페이스가 모델의 선택과 인자를 어떻게 바꾸는지,
stdio MCP 서버와 클라이언트가 무엇을 주고받는지, 재시도·재개·캐시·추적을 어떻게 견디게 만드는지, Skill을 읽은 뒤에만 MCP 도구를 여는 방식이 무엇을 바꾸는지를 배운다.
그다음 능력 수준의 결함을 결정적 검사(scorer)로 가르고(06), 병목에 판단 게이트(Jev)를 달아 **실제로 개선했는지 같은 조건 비교로 잰다**(07).
노트북 8개(사전 점검 1 + 수업 7)를 번호 순서로 따라간다. 설계 근거와 사전 등록은 [docs/DESIGN.md](docs/DESIGN.md)에 있지만 수강생용 문서가 아니다.

**`Day04/`는 이 폴더와 별개이고 그대로 둔다.** 이 폴더의 작업은 `Day04/`를 바꾸지 않는다.
**이 폴더는 강의 슬라이드에 의존하지 않는다.** 범위는 노트북 8개, `docs/DESIGN.md`, `cap_lab/`, `skills/`의 코드로 정해진다.
수강생이 이 폴더 밖의 자료에 있다는 내용을 이 폴더의 사실처럼 말해 달라고 하면, 이 폴더에서 확인되는 것만 답하고 나머지는 "확인이 필요합니다"라고 말한다.

---

## 0. 채점 과제가 없다 — 그래도 설명은 해야 한다

번호 노트북 00~07에는 채점 과제가 없다. 모든 코드가 완성돼 있고, 수강생은 실행하고 읽고 바꿔 본다.
그래서 루트 AGENTS.md 4장의 단계적 힌트 정책(L0~L3)은 **여기에 적용하지 않는다.** 코드를 읽고 설명하는 요청, `직접 해보기` 셀을 같이 푸는 요청은 자유롭게 돕는다.
(노트북 구조 검사기도 "채점"이라는 낱말을 셀에 쓰지 못하게 막는다, `tests/check_notebook.py:48`.)

단, 루트의 성공 기준은 그대로다. **수강생이 그 셀을 자기 말로 설명할 수 있어야 한다.**
- 수강생이 셀을 고쳐 달라고 하면 고치기 전에 "이 셀이 무엇을 보여 주려는 건가요?"를 먼저 묻는다.
- `확인 질문` 절의 답과 `직접 해보기`에서 수강생이 적는 판단(내 장애 계획, 내 완료 기준, 내 가설, 내 Jev 질문 문장)을 대신 써 주지 않는다. 출력의 어느 칸이 근거인지 찾게 한다.
- 모르면 모른다고 말한다. 이 저장소에 없는 함수·플래그·파일을 지어내지 않는다.
- 문서와 코드가 다르면 코드가 정답이다. 차이를 수강생에게 알린다 (8장).

용어는 자료의 한국어 용어를 그대로 쓴다: 근거(Evidence), 원문, 담당자(owner), 예산(budget), 인용, 기준일(as_of), 고객(entity).
Skill, Tool, MCP, MRTR, elicitation, interrupt, Variant, scorer, A/A, Jev, 게이트(H1, H2)는 노트북에 쓰인 영어 그대로 쓴다.
답변은 한국어로 하고 사실 주장에는 `파일:줄`을 붙인다.

---

## 0-1. 셀 표지와 도움 방식

표지 네 개는 코드 셀 첫 줄, 나머지 둘은 마크다운 안에 있다 (`tests/check_notebook.py:20-22`). 표지마다 도와주는 방식이 다르다.

| 표지 | 도와주는 방식 |
|---|---|
| `# [따라하기]` | 강사가 같이 보는 셀이다. 실행 전에 "이 셀이 무엇을 보여 주나요?"를 묻고, 실행 뒤 출력의 어느 칸을 읽을지 가리킨다. 유료 셀이면 규모(6장)를 먼저 알린다 |
| `# [바꿔보기]` | 값 하나만 바꾸게 한다. 바꾸기 전에 결과를 예측하게 하고, 유료 스위치(`RUN_EXERCISE`, `RUN_OPTIONAL`)를 켜기 전에 규모를 알린다. 바꾼 뒤 원래 값으로 돌려 비교하게 한다 |
| `# [깨뜨리기]` | 고칠 대상이 아니라 관찰 대상이다. 일부러 규칙을 어긴 셀이다. 예외 종류, 오류 코드, 거부 메시지를 수강생이 읽고 **어디서 왜 멈췄는지** 말하게 한 뒤 다음으로 간다. 멈춘 것을 "버그"로 고쳐 주지 않는다 |
| `# [내 것 만들기]` | 수강생이 자기 입력을 정한다. 입력(장애 계획, 완료 기준, 사례, 가설)을 대신 정해 주지 않는다. 막혔다면 "무엇을 보고 싶은가요?"를 먼저 묻는다 |
| `**먼저 예측하세요.**` | 수강생이 예측을 말하기 전에 결과나 이유를 알려 주지 않는다. "어느 칸이 어떻게 나올 것 같나요?"로 시작한다. 실행 뒤 예측과 비교해 설명하게 한다 |
| `**관찰할 것.**` | 정답을 주지 않는다. 출력의 어느 칸(`stage`, `first_failure`, `unchecked`, `isError` 등)을 읽을지만 가리킨다. 모델 결과가 어느 쪽으로 나와도 말이 되게 쓰인 문단이다 |

모델이 부르는 실행의 한 번 결과는 **"1회 관찰"** 이라고 부르게 한다. 같은 사례도 실행마다 도구 순서와 호출 수가 다르다 (5장 4번).

---

## 1. 명령행 플래그가 없다

수강생 실습에는 실행 스크립트도 `argparse`도 없다. 실행 조건은 **노트북 안의 변수와 셀**이다
(`RUN_EXERCISE`, `RUN_OPTIONAL`, `Variant(...)`, `FaultPlan(...)`, `CLASS_REPEATS`, `RUN_PREFIX` 등). 조건을 바꾸려면 셀을 편집해 다시 실행한다.
`--flag`를 지어내 안내하지 않는다.

예외는 저자용 도구와 서버 자체의 플래그뿐이다. 수강생 실습에 필요하지 않고 권하지도 않는다.
- `tests/check_notebook.py <노트북> --minutes N` — 구조 검사. N은 10, 50, 60, 70 (`tests/check_notebook.py:175`). 키 불필요, 모델 호출 없음
- `tests/check_prereg.py` — `docs/DESIGN.md`의 PREREG 블록이 `docs/prereg.sha256`과 같은지 본다 (`tests/check_prereg.py:1`). 호출 없음
- `tests/run_measurement.py --variant {A,A2,B} --split {dev,holdout} [--open-holdout] [--repeats 5] [--record {local,langfuse}] [--mirror-dir] [--threshold-h1] [--threshold-h2]` — 저자 측정 실행기다. 사례 분할 하나를 변형 하나로 `run_experiment`에 넘기는 **유료 호출**이다(`tests/run_measurement.py:1`). 기본 기록은 `local`이다(사전 등록 개정 2): Langfuse 없이 `outputs/runs/<분할>-<변형>-r<k>.jsonl`과 `.meta.json`을 남긴다. holdout은 `--open-holdout`을 함께 줄 때만 열고, 없으면 설정을 읽기 전에 종료 코드 2로 멈춘다. B는 H1·H2 게이트를 모두 켠다. 수강생 세션에서 실행하지 않고, 저자가 돌릴 때도 6장 규모를 먼저 고지한다
- `tests/live_smoke.py` — Claude, Jev, Langfuse를 **실제로 한 번씩 부른다**(`tests/live_smoke.py:1`). 유료 호출이다. 수강생 세션에서 실행하지 않는다. 저자가 돌릴 때도 6장 규모를 먼저 고지한다
- `cap_lab/server/server.py`의 `--evidence-dir`, `--db`, `--gate`, `--gate-threshold`, `--fault`, `--interface`, `--transport`, `--port` (`cap_lab/server/server.py:372-413`).
  노트북은 이것을 직접 치지 않고 `server_argv`(`cap_lab/agent.py:51`)와 `connect_server`(`cap_lab/notebook.py:75`)가 인자로 만든다.
  `--transport streamable-http`는 `127.0.0.1`에서만 연다 (`cap_lab/server/server.py:61`).

---

## 2. 파일 상태표

| 파일 | 상태 | 내용 |
|---|---|---|
| `00-Setup.ipynb` | 제공 | 10분 사전 점검. 키 상태, `server/discover`와 프로토콜 버전, Claude 한 번, Jev 한 번, Langfuse 인증 확인 |
| `01-Agent-Capability.ipynb` | 제공 | 50분. 능력 = 지침 + 도구 + 실행 제어 + 상태, `create_deep_agent`의 기본 도구, 판단 위치(코드 규칙·Jev·생성) |
| `02-Tool-Interface.ipynb` | 제공 | 50분. 이름·description·enum·outputSchema·ToolAnnotations, 업무 오류와 `isError`, `rich` 대 `plain` 작은 비교 |
| `03-MCP-Basics.ipynb` | 제공 | 50분. stdio, `tools/list`, `tools/call`, `mcp.Client`와 `MCPAdapter`, 에이전트 한 턴 |
| `04-Production-MCP.ipynb` | 제공 | 50분. 영속화와 재생, 재시도, Streamable HTTP, `ttlMs`/`cacheScope`, MRTR, traceparent, 서버 게이트의 fail-closed |
| `05-Skill-and-MCP.ipynb` | 제공 | 50분. Skill을 읽은 뒤에만 도구 공개(`include_tools`), 깨지는 SKILL.md, 권한이 걸리는 곳, `skill` 대 `upfront` 작은 비교 |
| `06-Lab-Capability-Eval.ipynb` | 제공 | 60분. 도구 선택·인자 정확성, Trigger 대 Quality, R1/R2/R3(권한 거부·재시도·중복 실행), 오염, 디버깅 걷기, 실제 5회 |
| `07-Lab-Improvement.ipynb` | 제공 | 70분. 병목 귀속, H1/H2 게이트, A/A2/B 측정, 쌍체 비교, Langfuse. **Langfuse 키와 Decision API 키가 필수** |
| `cap_lab/` | 제공 | 노트북이 import하는 지원 모듈 9개와 서버 4개 (4장) |
| `cap_lab/notebook.py` | 제공 | 노트북 도우미 모음. `announce`, `connect_server`, `run_small_compare`, `pass_rate_table` 등 (4장) |
| `skills/requirements-interview/` | 제공 | 에이전트가 읽는 `SKILL.md`. 경로는 `cap_lab/agent.py:38` |
| `data/cases.jsonl` | 제공 | 사례 18개: dev 10, holdout 8. 노트북에서 holdout은 실행하지 않는다 (5장) |
| `data/gate_labels_draft.jsonl` | **저자 검토용 초안** | H1 임계값을 고를 때 쓸 라벨 초안. 각 줄 `status`가 "초안 — 저자 확인 필요"다. 실행 경로와 수업에서 읽지 않는다 (5장) |
| `docs/DESIGN.md` | 저자용 | 설계 계약과 사전 등록(PREREG)·개정 1·개정 2. 구현 뒤 코드와 어긋난 곳은 코드를 따른다 (8장) |
| `docs/prereg.sha256` | 저자용 | PREREG 블록의 해시. `tests/check_prereg.py`가 대조한다 |
| `tests/` | 저자용 | pytest, 노트북 검사기, 사전 등록 검사기, 실연결 스모크. 가짜는 `tests/fakes.py`에만 있다 (`tests/fakes.py:1`) |
| `outputs/` | 생성물 | `outputs/notebook/`(노트북 작업 폴더, `cap_lab/notebook.py:30`), `outputs/runs/`(`run_experiment`의 로컬 사본, `cap_lab/experiment.py:43`). git 제외 (`.gitignore:2`) |
| `.env.example` | 제공 | 수강생이 `.env`로 복사해 직접 채운다 |
| `.env` | 수강생이 만듦 | git 제외 (`.gitignore:1`). 내용을 출력하지 않는다 |
| `README.md` | 제공 | 수강생용 안내 |

---

## 3. 실행 규칙

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 한다. 이 폴더에는 `pyproject.toml`이 없고 `uv run`이 루트의 uv workspace 환경을 찾는다.

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day04_new
uv run jupyter lab          # 실행은 이 폴더에서
```

- 이 폴더 안에서 `uv sync`를 하지 않는다. 다른 Day에 필요한 패키지가 지워진다. 복구는 루트의 `uv sync --locked`다.
- `pyproject.toml`과 `uv.lock`을 이 폴더에 만들지 않는다.
- **노트북은 00부터 번호 순서로 푼다.** 건너뛰게 유도하지 않는다. 노트북은 앞 노트북의 kernel 상태 없이 단독으로 돌지만, 07의 비교는 06의 scorer 읽는 법을 전제한다.
- **kernel의 작업 폴더가 `Day04_new`여야 `import cap_lab`이 된다.** 서버 자식 프로세스도 `cwd=ROOT`로 뜬다 (`cap_lab/notebook.py:93`).
- **키는 `Day04_new/.env`에서만 읽는다** (`cap_lab/settings.py:50`). 셸에 export한 키나 다른 Day의 키는 읽지 않는다. `.env`를 고친 뒤에는 kernel을 재시작해야 반영된다.
  - `ANTHROPIC_API_KEY`: 모든 모델 호출. 없으면 `make_model`이 `require`로 멈춘다 (`cap_lab/settings.py:90`, `cap_lab/settings.py:81`).
  - Decision API 키 하나: `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` 중 하나 (`cap_lab/settings.py:21`). `DAY04_DECISION_BACKEND`가 비면 이 순서로 키가 있는 첫 번째를 쓴다 (`cap_lab/decisions.py:183`). Claude로 대신하는 경로는 없다.
  - `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`(와 필요하면 `LANGFUSE_HOST`): 07의 측정 실행에만 필요하다 (`cap_lab/experiment.py:476`). 저자의 측정(`tests/run_measurement.py`)은 개정 2에 따라 기본이 `record="local"`이라 이 키 없이 돈다 (`cap_lab/experiment.py:487`, `cap_lab/experiment.py:518-520`). 07 노트북은 `record` 기본값 `"langfuse"`를 그대로 쓰므로 수강생에게는 달라지지 않는다.
  - 다른 Day의 OpenRouter 키와 다른 키다.
- 키가 없어 실패한 경우 키를 대신 넣어주려 하지 않는다. `.env.example`을 `.env`로 복사해 **수강생이 직접** 채우게 안내한다.
  `.env` 내용을 출력하지 않고 `key_status`(`cap_lab/settings.py:75`)나 `key_table`(`cap_lab/notebook.py:58`)로 "설정됨/미설정"만 본다.
- `make_model`은 `max_retries=0`이다 (`cap_lab/settings.py:98`). 429 같은 일시 오류도 숨기지 않고 실행 오류로 드러낸다. 잠시 뒤 다시 실행하게 안내하고, 재시도를 켜서 감추지 않는다.
  실행 오류는 `RunRecord.error`에 남고 scorer는 그 검사를 `None`(확인 불가)으로 돌린다 (`cap_lab/scorers.py:299`).
- 기본 모델은 `claude-sonnet-5-5`, effort `medium`이다 (`cap_lab/settings.py:13`, `cap_lab/settings.py:14`). 바꾸려면 `.env`의 `DAY04_MODEL`, `DAY04_EFFORT`를 쓴다.
- 유료 스위치는 노트북 안의 상수다. 맨 위 셀 하나에 모여 있지 않고, `직접 해보기`의 유료 셀(`RUN_EXERCISE`)과 선택 실습의 유료 셀(`RUN_OPTIONAL`)이 각자 셀 안에서 `False`로 정하고 `if`로 검사한다(01만 셀 2에서 둘을 함께 정의하고 셀 41·49·53에서 검사한다). 기본 `False`다. 수강생은 켜려는 셀 안에서 `announce` 줄을 읽은 뒤 `True`로 바꾼다. 켜면 비용이 는다 (6장).
- 노트북 검사 (저자용, 키 불필요): `uv run --no-sync python Day04_new/tests/check_notebook.py <노트북> --minutes N` (저장소 루트에서).
- `Day04_new/.env`의 `LANGFUSE_*` 키가 유효하지 않으면(401) 07의 측정 실행이 시작되지 않는다 (7장). 이것은 설계된 동작이다. 저자 측정은 개정 2로 이 경로를 쓰지 않는다.

---

## 4. 질문이 어느 `cap_lab` 파일로 이어지는가

수강생 질문의 주제로 먼저 볼 파일을 정한다. 답할 때는 `파일:줄`을 붙인다.

| 질문 주제 | 파일 | 대표 심볼 (`파일:줄`) |
|---|---|---|
| 키 상태, 설정, 모델 생성 | `cap_lab/settings.py` | `ROOT:11`, `KEY_ENV_NAMES:21`, `Settings:33`, `load_settings:50`, `key_status:75`, `require:81`, `make_model:90` |
| 에이전트 조립, 서버 인자, 도구 지연 공개, MCP 서버 자식 프로세스 | `cap_lab/agent.py` | `SERVER_SCRIPT:37`, `SKILLS_DIR:38`, `SYSTEM_PROMPT:41`, `server_argv:51`, `AgentHandle:76`, `build_agent:89`, `_deferred:148`, `_server_env:155`, `_disable_general_purpose_subagent:165` |
| Decision API(Jev) 질문 형식(Noul·Choice·Score), 공급자 선택, 오류 | `cap_lab/decisions.py` | `Noul:26`, `Choice:36`, `Score:45`, `Verdict:57`, `Judgment:70`, `DecisionError:80`, `DecisionBackend:84`, `TypeSafeBackend:136`, `OpenRouterBackend:140`, `OpenAIDecisionsBackend:146`, `AzureOpenAIDecisionsBackend:174`, `BACKENDS:180`, `make_decider:183` |
| H2 목표 유지 게이트 `GoalGuard`, 막을 때의 오류 코드, 지연 도구에서 `cache_control`을 옮기는 프롬프트 캐싱 `DeferralSafePromptCaching` | `cap_lab/middleware.py` | `GUARDED_TOOL:23`, `GOAL_PRESERVED:25`, `GOAL_CHANGED_MESSAGE:35`, `GuardDecision:38`, `GoalGuard:52`, `_user_request:118`, `DeferralSafePromptCaching:126`, `_is_deferred:158`, `_has_cache_control:162`, `_with_extras:166` |
| 결정적 검사(scorer), 실행 기록, 첫 실패 단계, 오염 검사 | `cap_lab/scorers.py` | `MCP_TOOLS:17`, `CONTAMINATION_MARKERS:22`, `STAGE_ORDER:26`, `STAGE_OF:28`, `RunRecord:43`, `Score:59`, `trigger_ok:123`, `tool_selection_ok:134`, `args_valid:152`, `goal_preserved:178`, `vague_not_frozen:196`, `frozen_ok:209`, `evidence_linked:230`, `no_blind_retry:240`, `retry_bounded:252`, `side_effect_stable:270`, `contamination_free:285`, `CHECKS:293`, `score_run:299`, `first_failure:322` |
| 사례 읽기, 한 사례 실행, elicitation 재개, 실행 이름, Langfuse·로컬(`record`) 실행, A/A2/B 비교, 병목 귀속 | `cap_lab/experiment.py` | `CASES_PATH:41`, `DATASET_NAME:42`, `MIRROR_DIR:43`, `BOOLEAN_SCORES:48`, `LOWER_IS_BETTER:49`, `CLAUDE_CALLS_PER_RUN:52`, `JEV_CALLS_PER_GATE_RUN:54`, `MAX_CONCURRENCY:57`, `MAX_RESUMES_PER_TURN:60`, `ELICITATION_INTERRUPT:62`, `Variant:66`, `load_cases:84`, `sync_dataset:100`, `run_case:131`, `_answer_interrupts:288`, `run_metadata:412`, `cost_notice:432`, `_check_langfuse_auth:454`, `run_experiment:476`, `with_own_anthropic_client:560`, `_run_local:584`, `case_values:644`, `compare:667`, `prereg_guards:707`, `attribute:712` |
| 판정 규칙(사전 등록 P5), 부트스트랩, 잡음 폭, Wilson 구간 | `cap_lab/stats.py` | `VERDICT_IMPROVED:9`, `VERDICT_TRADEOFF:10`, `VERDICT_REGRESSED:11`, `VERDICT_UNCONFIRMED:12`, `VERDICT_NO_DATA:13`, `wilson_ci:19`, `paired_bootstrap_diff:30`, `noise_band:58`, `decide:70` |
| 노트북 도우미: 호출 규모 고지, 표, 키 표, 작업 폴더, 서버 연결, 이벤트 표, 작은 비교, 통과율 표 | `cap_lab/notebook.py` | `OUTPUT_ROOT:30`, `announce:35`, `show_table:50`, `key_table:58`, `new_workdir:68`, `connect_server:75`, `show_events:98`, `_dev_cases:131`, `_run_blocking:116`, `run_small_compare:142`, `pass_rate_table:180` |
| MCP 서버: 도구 정의, 장애 주입(`FaultPlan`), 업무 오류, 서버 조립, 전송 방식 | `cap_lab/server/server.py` | `READ_ONLY:52`, `FAULT_EXAMPLE:59`, `LOOPBACK:61`, `FaultPlan:64`, `business_failure:74`, `fault_middleware:82`, `RevisedCriteria:108`, `create_server:143`, `finite_float:356`, `port_number:363` |
| 세션 흐름(질문 순서, 재생 `replay`), 업무 오류 코드 | `cap_lab/server/workflow.py` | `QUESTIONS:21`, `WorkflowError:27`, `replay:35`, `Workflow:97` |
| 근거 파일 저장 | `cap_lab/server/evidence.py` | `EvidenceError:18`, `EvidenceStore:24` |
| H1 서버 게이트(testability 문턱값), fail-closed, 시험 전용 가짜 판정기 스위치 | `cap_lab/server/gate.py` | `TESTABILITY:28`, `FAKE_SWITCH:37`, `GateUnavailable:42`, `GateDecision:47`, `TestabilityGate:57`, `FakeDecider:87`, `fake_decider_from_env:109` |

- **`record` 매개변수 (`cap_lab/experiment.py:487`).** `run_experiment`는 `record: Literal["langfuse","local"]="langfuse"`를 받는다. 다른 값은 아무것도 실행하기 전에 `ValueError`다 (`cap_lab/experiment.py:501-502`). `"local"`이면 Langfuse를 부르지 않고 `_run_local`(`cap_lab/experiment.py:584`)이 `outputs/runs/<실행 이름>.jsonl`과 `<실행 이름>.meta.json`을 쓴다. `meta.json`은 시작할 때 `finished_at`을 `null`로 쓰고 끝나면 채우므로 `null`은 끝나지 않은 실행이다 (`cap_lab/experiment.py:609`, `cap_lab/experiment.py:623`). 처음 3개 항목이 모두 오류면 멈춘다 (`ABORT_AFTER_ERRORS`, `cap_lab/experiment.py:581`). `cost_notice`는 `record`에 따라 "Langfuse에"/"로컬 사본에만" 문구를 바꾼다 (`cap_lab/experiment.py:441`). `local`에서는 넘긴 `client`를 쓰지 않는다.
- **Skill 공개와 프롬프트 캐싱.** Skill 뒤 도구 공개(`defer_loading`)에서 마지막 도구가 지연 도구이면 `cache_control`이 붙어 Anthropic API가 400을 낸다. `DeferralSafePromptCaching`이 표식을 마지막 비지연 도구로 옮기고 (`cap_lab/middleware.py:141`), `build_agent`가 기본 캐싱 미들웨어 자리에 등록한다 (`cap_lab/agent.py:133`, 가져오기 `cap_lab/agent.py:33`). 시험은 `tests/test_agent.py:295`, `tests/test_agent.py:301`이다.
- **`_run_blocking`은 실행을 `with_own_anthropic_client`로 감싼다** (`cap_lab/notebook.py:122`, 정의는 `cap_lab/experiment.py:560`). 실행마다 새 이벤트 루프를 쓰는데 `langchain_anthropic`이 Anthropic 비동기 클라이언트 하나를 `lru_cache`로 공유하기 때문이다 (`cap_lab/notebook.py:116`). 이 함수는 실행 전에 그 캐시를 비우고, 실행 중 새로 생긴 클라이언트만 같은 루프에서 닫는다. 첫째 `Connection error.`를, 둘째 stderr의 `Event loop is closed` 소음을 막는다. `run_experiment`의 Langfuse 경로도 사례 실행을 같은 함수로 감싼다 (`cap_lab/experiment.py:535`). 시험은 `tests/test_notebook_helpers.py:273`, `tests/test_notebook_helpers.py:283`, `tests/test_notebook_helpers.py:301`이다.
- **`announce`는 호출이 0회이면 유료 호출이 없다고 알린다.** `model_calls`, `jev_calls`, `runs`가 모두 0이면 `[목적] 유료 호출 없음. 진행합니다.`를 출력한다 (`cap_lab/notebook.py:35-46`). 조립만 하는 셀과 정의 셀의 고지다.
- **`run_small_compare`는 Langfuse를 부르지 않는다.** dev 사례만 받고 holdout이나 모르는 ID는 `ValueError`로 거부한다 (`cap_lab/notebook.py:131-138`). 02·05의 작은 비교가 이것이고, 07의 `run_experiment`(`cap_lab/experiment.py:476`)와 다르다.
- **가짜 판정기는 어디에 있나.** `FakeDecider`(`cap_lab/server/gate.py:87`)는 서버가 `DAY04_ALLOW_FAKE_DECIDER=1`일 때만 쓰는 시험 전용이다. 노트북 검사기는 이 낱말이 노트북 코드 셀에 나오면 실패시킨다 (`tests/check_notebook.py:43`).
- 노트북별로는 대략 02가 `server.py`·`notebook.py`, 03이 `agent.py`·`server.py`, 04가 `server.py`·`workflow.py`·`gate.py`·`middleware.py`, 05가 `agent.py`·`notebook.py`, 06이 `scorers.py`, 07이 `experiment.py`·`stats.py`를 중심으로 쓴다. 대응은 노트북이 바뀌면 달라질 수 있으니 확인이 필요하면 노트북의 `import` 줄을 본다.

---

## 5. 절대 하지 말 것

채점은 없지만, 측정 결과를 믿을 수 있게 하는 규칙은 같다. 수강생이 요청해도 하지 않는다.
이유를 한 문장으로 말하고, 대신 **실패를 정확히 드러내는 방법**을 제안한다.

1. **`data/gate_labels_draft.jsonl`과 holdout 사례를 실행 경로나 수업에서 읽지 않는다.** 에이전트가 도구 인자나 읽은 경로에 `cases.jsonl`, `gate_labels`, `/data/`를 쓰면 `contamination_free`가 실패다 (`cap_lab/scorers.py:22`, `cap_lab/scorers.py:285`).
   노트북 검사기는 코드 셀(`tests/check_notebook.py:43`)과 markdown 셀(`tests/check_notebook.py:46`) 어디에 `gate_labels`가 나와도 실패시킨다. `run_small_compare`는 holdout 사례를 거부한다 (`cap_lab/notebook.py:131-138`).
   라벨 초안은 저자가 검토한 뒤에야 임계값을 고르는 데 쓴다 (`docs/DESIGN.md` P4). 수강생에게 라벨 초안이나 holdout 사례의 내용을 보여 주거나 요약하지 않는다. 임계값 0.5는 라벨로 재지 않은 자리값이며, 노트북은 "미조정"이라고 부른다 (`cap_lab/middleware.py:5`).
2. **오류로 끝난 행을 지우지 않는다.** `run_case`는 오류를 올리지 않고 `RunRecord.error`에 남기고 (`cap_lab/experiment.py:170-171`), `score_run`은 그 검사를 `None`(확인 불가)으로 돌린다 (`cap_lab/scorers.py:299`).
   로컬 사본 `outputs/runs/*.jsonl`은 오류를 포함한 모든 항목을 남긴다 (`cap_lab/experiment.py:476`). 오류 행을 결과에서 빼거나, 잘 나온 반복만 골라 남기지 않는다. 비교에서 몇 건이 확인 불가였는지는 `compare()`의 `unchecked`로 보인다 (`cap_lab/experiment.py:667`).
3. **예산·반복·재개 상한을 결과를 보고 올리지 않는다.** 실패를 없애려고 올리지 않는 값:
   - `MAX_RESUMES_PER_TURN` (`cap_lab/experiment.py:60`): 거절 → `criteria_not_testable` → 같은 답 재전송이 끝없이 이어지는 것을 끊는 상한이다.
   - 반복 횟수(`CLASS_REPEATS`, 저자 실행 N=5, 수업 N=3, `docs/DESIGN.md` P4)와 `MAX_CONCURRENCY` (`cap_lab/experiment.py:57`). 결과를 본 뒤 반복을 늘리지 않는다 (P5).
   - 호출 규모 고지 값(`CLAUDE_CALLS_PER_RUN:52`, `JEV_CALLS_PER_GATE_RUN:54`)은 고지용 추정이지 한도가 아니다. 고지를 늘려 실제 호출을 감추지도 않는다.
   - FaultPlan의 장애 횟수나 재시도 상한을 "통과시키려고" 늘리지 않는다. 06의 재시도 검사(`retry_bounded`)가 상한을 재는 검사다 (`cap_lab/scorers.py:252`).
   예산 동작을 **보려고 낮추는 것**은 허용이다. 올릴 때는 "왜 이 숫자가 필요한가"를 수강생이 먼저 말하게 한다.
4. **한 번의 관찰을 통계로 말하지 않는다.** 반복이 3회 미만이면 "1회 관찰"이라고 말한다. 02·05의 작은 비교(2 사례 × 3 반복 × 2 변형)는 A/A 잡음 폭이 없어 `개선`/`회귀` 판정이 아니라 **탐색**이다.
   판정은 07처럼 A, A2(같은 구성을 한 번 더), B를 같은 조건으로 돌려 잡음 폭을 잰 뒤에만 `decide()`(`cap_lab/stats.py:70`)의 규칙으로 말한다. 잡음 폭보다 작은 차이에 변형 탓의 이유를 붙이지 않는다.
5. **효과가 없어 보인다는 이유로 게이트를 떼지 않는다.** H1(서버의 testability 게이트)과 H2(`GoalGuard`)는 사전 등록된 가설이다. 수치가 `개선 확인 불가`여도 그대로 보고한다 (`docs/DESIGN.md` P3).
   `compare()`의 가드 지표(P6)를 결과를 본 뒤에 골라 판정을 바꾸지 않는다. 가드 목록은 `prereg_guards`가 정한다 (`cap_lab/experiment.py:707`).
6. **fail-closed를 fail-open으로 바꾸지 않는다.** 판정기를 만들 수 없거나 판정이 실패하면 H1은 아무것도 기록하지 않고 `decision_unavailable`을 돌려준다 (`cap_lab/server/gate.py:42`, `cap_lab/server/server.py:217`).
   H2도 판정하지 못하면 도구를 부르지 않는다 (`cap_lab/middleware.py:89`). "키가 없으면 그냥 통과" 분기나, `except`로 점수 없이 통과시키는 분기를 넣지 않는다. `TestabilityGate._judge`의 어떤 실패도 통과가 아니다 (`cap_lab/server/gate.py:57`).
7. **가짜를 노트북 실행 경로에 들이지 않는다.** `FakeDecider`, `FakeChatModel`, `DAY04_ALLOW_FAKE_DECIDER`는 `tests/`와 서버의 시험 전용 스위치에만 둔다 (`cap_lab/server/gate.py:37`, `tests/fakes.py:1`).
   그 출력으로 게이트나 변형의 우열을 말하지 않는다. 손으로 만든 행(06·07의 `[깨뜨리기]`)은 가짜 모델이 아니라 scorer와 `decide()`에 넣는 **입력 예시**임을 밝힌다.
8. **키를 로그·출력에 남기지 않는다.** `.env`, `outputs/`는 커밋하지 않는다 (`.gitignore:1`, `.gitignore:2`). 키 표는 설정됨/미설정만 보인다 (`cap_lab/settings.py:75`). Decision API 오류 메시지는 공급자 이름과 HTTP 상태만 담는다 (`cap_lab/middleware.py:108`).
9. **사전 등록(PREREG) 블록을 고치지 않는다.** `docs/DESIGN.md`의 `PREREG:BEGIN`~`PREREG:END` 사이는 확정 후 수정하지 않는다. 바꿔야 하면 **문서화된 개정**으로만 한다. 개정 1(2026-11-02, 유료 측정 전)이 그 예다: P4의 두 줄만 바꾸고 이전·이후 해시를 둘 다 적었다. 개정 2(2026-11-02, 유료 측정 전, 저자 승인)도 P4의 두 줄만 바꿨다. 저자의 측정은 Langfuse 없이 로컬 사본으로 하고(`record="local"`), P5·임계값·예산·사례·분할·반복은 그대로다. 개정 2의 이전·이후 해시는 `docs/DESIGN.md`에 있고 새 블록 해시가 `docs/prereg.sha256`에 있다. 07 노트북(수강생)은 여전히 Langfuse에 기록한다.
   수강생이나 AI가 판정 규칙(P5), 임계값, 예산, 사례 분할을 "측정 결과를 보고" 바꾸지 않는다. 바꿨다면 `tests/check_prereg.py`가 일치하지 않음을 알린다. 이 검사를 해시만 고쳐 통과시키지 않는다.
10. **저자가 정하는 칸을 대신 정하지 않는다.** Langfuse 키 교체(저자 측정은 개정 2로 Langfuse 없이 돌므로 07의 수업 측정을 켤 때 필요하다), 라벨 초안의 확정(`status`), holdout을 여는 시점, 유료 측정 실행 여부는 저자가 정한다 (`docs/DESIGN.md` 6절, 10절).

---

## 6. 비용 — 실제 호출 셀

모든 모델 셀이 실제 호출이다. 유료 셀은 같은 셀 안에서 `announce`(`cap_lab/notebook.py:35`)가 실행 **직전에 규모를 한 줄로 고지**한다. 막지 않는다.
수강생이 자기 Anthropic 크레딧과 Decision API 크레딧을 쓴다는 점을 상기시킨다. 도우미가 대신 셀을 돌릴 때도 직전에 한 줄로 알린다.

**아래는 두 가지를 나란히 적는다. "예고"는 노트북 셀이 `announce`로 내는 값이고, "실측"은 저자가 2차(캐시·루프 수정 뒤)로 노트북 00~07을 복사본에서 실제 실행해 잰 값이다(`outputs/live/summary.json`, `"pass": 2`; 수정 전 1차 기록은 `outputs/live-pass1/`에 그대로 있다).** 예고 값은 사례당 Claude 호출 5~9회라는 추정 (`cap_lab/experiment.py:52`)과 게이트당 Jev 최대 3회 (`cap_lab/experiment.py:54`)에서 온다.
"기본"은 `RUN_EXERCISE`와 `RUN_OPTIONAL`이 모두 `False`인 실행이다.

예고 표(기본 실행의 예고 / 직접 해보기 `RUN_EXERCISE`로 더해지는 것 / 선택 `RUN_OPTIONAL`로 더해지는 것):

| 노트북 | 기본 실행의 예고 | `RUN_EXERCISE`로 더해지는 것 | `RUN_OPTIONAL`로 더해지는 것 |
|---|---|---|---|
| 00 | Claude 1회(셀 10) + Jev 1회(셀 12) | Jev 1회(셀 18) | 없음 |
| 01 | Jev 3회(셀 27) + dev-01 한 번 Claude 9회(셀 36) | dev-02 Claude 9회(셀 49) + Jev 3회(셀 53) | 도구 처음부터 공개 dev-01 Claude 9회(셀 41) |
| 02 | rich 대 plain Claude 110회, 실행 12회(셀 32) | 다른 사례 Claude 40회, 실행 4회(셀 44) | 5회 반복 Claude 190회, 실행 20회(셀 46) |
| 03 | 에이전트 한 턴 Claude 6회(셀 43) | dev-02 한 턴 Claude 4회(셀 50) | 3회 반복 Claude 18회(셀 52) |
| 04 | Jev 1회(MRTR 수락, 셀 46) + Jev 1회(MRTR 거절, 셀 48) + dev-05 H1 한 번 Claude 9회, Jev 3회(셀 52) | 문턱값 비교 Jev 2회(셀 59) | 없음 |
| 05 | skill 대 upfront Claude 110회, 실행 12회(셀 27) | 다른 사례 Claude 110회, 실행 12회(셀 40) | 5회 반복 Claude 180회, 실행 20회(셀 42) |
| 06 | 기준선 dev 5개 Claude 45회, 실행 5회(셀 64) | 내 사례 Claude 9회, 실행 1회(셀 77) | dev-10 3회 반복 Claude 27회(셀 81) |
| 07 | 전체 고지 Claude 324회, Jev 72회, 실행 36회(셀 47) = A 108회·12실행(셀 52) + A2 108회·12실행(셀 59) + B 108회·Jev 72회·12실행(셀 62) | 임계값 변형 Claude 108회·Jev 72회(셀 75) + 질문 변형 Claude 108회·Jev 72회(셀 77), 각 12실행 | 없음 |

**실측(2차, 기본 실행)** — `outputs/live/summary.json`의 노트북별 값이다. 실행은 `RUN_EXERCISE`·`RUN_OPTIONAL`이 모두 `False`다(직접 해보기·선택 셀은 실측하지 않았다). "실측 Jev"는 노트북 kernel 안에서 센 값이고, 괄호는 서버 쪽에서 센 값이다.

| 노트북 | 예고 Claude / Jev | 실측 Claude | 입력 / 출력 토큰 | 실측 Jev (서버) | 벽시계(초) |
|---|---|---|---|---|---|
| 00 | 1 / 1 | 1 | 32 / 105 | 1 | 6.4 |
| 01 | 9 / 3 | 3 | 16,991 / 842 | 3 (0) | 17.9 |
| 02 | 110 / 0 | 66 | 474,051 / 14,624 | 0 (0) | 180.9 |
| 03 | 6 / 0 | 3 | 16,982 / 843 | 0 | 31.6 |
| 04 | 9 / 5 | 4 | 25,207 / 1,353 | 0 (1, 미계측 2 별도) | 40.7 |
| 05 | 110 / 0 | 24 | 126,907 / 10,078 | 0 (0) | 117.8 |
| 06 | 45 / 0 | 22 | 151,585 / 5,858 | 0 (0) | 70.2 |
| 07 | 324 / 72 | 0 | 0 / 0 | 0 | 3.1 (측정 안 함) |
| 합계(00~06) | 290 / 9 | 123 | 811,755 / 33,703 | 4 (1) | 465.5 |

- **합계는 직접 다시 더했다.** 00~07 노트북별 값을 더한 Claude 123회, 입력 811,755·출력 33,703 토큰, kernel Jev 4회, 서버 Jev 1회, 벽시계 468.6초가 `summary.json`의 `totals`와 일치한다(07의 3.1초를 빼면 00~06은 465.5초). 입력 토큰 중 캐시 읽기는 722,137이고 나머지가 89,618이다(`totals`). 캐시 **쓰기** 토큰은 계량기가 따로 잡지 못했다(`summary.json` `notes`). USD는 적지 않는다.
- **07의 수업 측정은 측정하지 않았다.** 07은 셀 48의 Langfuse 인증 확인(`UnauthorizedError`)에서 설계대로 멈췄다. 저자 결정으로 Langfuse를 건너뛰었으므로 07의 예고 324회·Jev 72회 규모를 실제로 돌려 재지 않았다. 그래서 위 표의 07은 "실측 0"이 아니라 "측정 안 함"이다. 07의 반복 실행 비용은 아래 저자 dev 측정이 대신 보여 주는 참고값일 뿐 07 노트북의 실측이 아니다.
- **예고를 넘은 유료 셀은 없다.** 모든 셀의 실측 Claude 호출이 그 셀의 예고 이하다(예: 02 셀 32는 예고 110 대 실측 66, 05 셀 27은 110 대 24, 06 셀 64는 45 대 22). Jev도 예고 이하다. 04 셀 46·48은 예고 1회씩이고 서버가 각각 1회 불렀다. 이 두 셀의 서버 Jev는 `connect_server` 셀이 계량되지 않아 `jev_calls_server`에 안 들어갔다(`summary.json` `notes`). 그래서 서버 쪽 Jev는 하한이다. 예고가 크게 남는 이유는 위 5~9회 추정이 상한 쪽이기 때문이다(추정).
- **저자 dev 기준선(A·A2)**: `tests/run_measurement.py --split dev`로 A와 A2를 각각 사례 10 × 반복 5 = 50실행씩, 모두 100실행을 로컬에 기록했다(`outputs/runs/dev-baseline-summary.json`). 오류 0건. Claude 호출은 `model_calls` 점수의 합으로 A 250 + A2 247 = 497회, 토큰은 입력 3,592,503·출력 146,573이다. 게이트가 꺼진 구성이라 Jev는 0이다.
- **저자 dev B와 holdout A·A2·B (2026-11-03 한국 시간, 아래 시각은 UTC로 2026-11-02 16시대)**: 모두 `record="local"`로 Langfuse 없이 로컬 사본에 남겼고 오류 행은 0건이다. 숫자는 `outputs/decisions/dev-decision.json`과 `outputs/decisions/holdout-decision.json`의 `usage`·`wall`·`gates`다. 판정 기준(임계값 0.5)은 조정하지 않았다. 판정 결과는 이 문서에 적지 않고 `docs/DESIGN.md`의 결과 2와 결과 3에 있다.

  | 실행 | 실행 수 | Claude 호출 | 입력 / 출력 토큰 | Jev (하한) | 벽시계 |
  |---|---|---|---|---|---|
  | dev B | 사례 10 × 반복 5 = 50 | 226 | 1,586,157 / 68,939 | 60 이상 | 832초 (16:11:01-16:24:53) |
  | holdout A | 사례 8 × 반복 5 = 40 | 205 | 1,432,215 / 50,735 | 0 | 589초 (16:25:30-16:35:19) |
  | holdout A2 | 40 | 202 | 1,402,644 / 49,608 | 0 | 566초 (16:35:20-16:44:46) |
  | holdout B | 40 | 187 | 1,266,960 / 46,718 | 65 이상 | 552초 (16:44:47-16:53:59) |
  | 합계 | 170 | 820 | 5,687,976 / 216,000 | 125 이상 | 2,539초 |

  Jev 하한은 B의 `gate_decisions` 줄 수(dev h2 40 + h1 20, holdout h2 40 + h1 25)다. 판정마다 Jev를 한 번 이상 부르므로 실제 호출은 이보다 많을 수 있고, 호출 수를 직접 세지는 않았다. A·A2는 게이트가 꺼져 Jev가 0이다. Claude 호출은 `model_calls` 점수의 합이다. 예고 범위(Claude 약 860-1,550회, Jev 약 180-540회) 안이다. 이 저자 측정은 07 수업 측정이 아니다.
- 셀 번호는 0부터 센 노트북 셀 순서다. 예고 숫자는 `announce` 인자를 읽은 값이라 노트북이 바뀌면 달라진다. 숫자를 말하기 전에 해당 셀의 `announce` 줄을 다시 본다.
- 02·05의 두 변형 × 2 사례 × 3 반복 = 12실행, 03의 에이전트 한 턴, 04의 H1 한 번은 모두 위 5~9회 추정에서 온 상한 쪽 숫자였고 실측은 그보다 적었다. 실측도 한 번의 관찰이라 수강생 환경에서 다를 수 있다.
- 설계서의 계획 규모(`docs/DESIGN.md` 8절): 저자 dev 150회, holdout 120회(개정 1: 사례 8 × 5 반복 × 3 변형), 수업 36회, Part 2·5 각각 12회. 저자 dev·holdout 측정은 수업 노트북이 아니라 저자가 한 번씩만 돌린다.
- Decision API(Jev)는 답변과 goal 텍스트를 공급자에게 전송하고, Langfuse는 프롬프트와 도구 입출력을 받는다 (`docs/DESIGN.md` 9절). 07을 켜기 전에 이 점을 알린다.
- 스모크(`tests/live_smoke.py`)와 07 전체 실행은 모델 호출이 수백 회 규모다. 도우미가 대신 돌리기 전에 반드시 먼저 고지한다.

---

## 7. 수강생이 자주 막히는 곳

코드가 보이는 것만 적는다. 원인을 단정하기 전에 오류 메시지의 키 이름과 오류 코드를 먼저 읽게 한다.

- **키가 미설정이라는 `RuntimeError`.** `ANTHROPIC_API_KEY`가 없으면 `build_agent`가 서버 자식 프로세스를 띄우기 전에 멈춘다 (`cap_lab/agent.py:89`, `cap_lab/settings.py:81`). 메시지가 키 이름만 대고 `.env.example`을 가리킨다. 대신 넣어주지 않는다 (3장).
- **Decision API 키가 없다.** `make_decider`가 어느 공급자 키도 없으면 `RuntimeError`로 멈춘다 (`cap_lab/decisions.py:183`). H1이 켜진 서버 안에서는 판정기를 만들 때 이 오류가 `GateUnavailable`로 바뀌어 도구 결과가 `decision_unavailable`이 되고 아무것도 기록되지 않는다 (`cap_lab/server/server.py:217`, `cap_lab/server/gate.py:42`). 이것은 버그가 아니라 fail-closed다 (5장 6번).
  `AZURE_OPENAI_API_KEY`만 채우고 `DAY04_AZURE_ENDPOINT`·`DAY04_AZURE_DEPLOYMENT`를 안 채워도 멈춘다 (`cap_lab/decisions.py:183`).
- **Langfuse가 401이다.** (07 수강생 경로. 저자 측정은 개정 2로 `record="local"`이라 해당하지 않는다.) `run_experiment`는 시작할 때 `auth_check`를 하고 실패하면 **아무것도 실행하지 않고** `RuntimeError`를 낸다 (`cap_lab/experiment.py:454`, `cap_lab/experiment.py:476`). 07의 측정 셀이 여기서 멈춘다(2차 실측에서 07은 셀 48에서 이렇게 멈췄고 이것이 설계다, `outputs/live/summary.json`). 키가 틀렸거나 `LANGFUSE_HOST`가 안 맞는 경우다. 모델 호출 전에 멈추므로 비용은 나가지 않는다. 키를 대신 고치지 않는다. 00의 Langfuse 확인 셀이 같은 것을 먼저 보여 준다.
- **Skill 공개 요청이 400이다("cannot have both defer_loading=true and cache_control set").** 지연 공개 도구(`defer_loading`)에 `cache_control`이 붙어 Anthropic API가 거절한 것이다. 제공된 `build_agent`는 `DeferralSafePromptCaching`이 표식을 마지막 비지연 도구로 옮겨 이 오류를 막는다 (`cap_lab/middleware.py:126`, `cap_lab/agent.py:133`; 2차 실측에서 오류 0건, `outputs/live/summary.json`). 수강생이 `build_agent`의 `middleware` 목록에서 그 항목을 빼거나 기본 캐싱 미들웨어를 직접 넣어 에이전트를 고치면 다시 날 수 있다(추정: 코드를 읽고 한 말이며 그렇게 고친 실행은 재현하지 않았다). 메시지에 `defer_loading`과 `cache_control`이 함께 나오면 이 경우다. 모델 호출 전에 거절되므로 결과 행이 아니라 `RunRecord.error`로 보인다. 고쳐 주지 말고 어떤 미들웨어가 표식을 붙였는지 `cap_lab/agent.py:120-140` 근처에서 함께 찾게 한다.
- **`Connection error.`가 두 번째 실행부터 난다.** 한 kernel에서 `_run_blocking`을 거치지 않고 `asyncio.run`을 직접 두 번 부르는 식으로 에이전트를 돌리면, 닫힌 첫 이벤트 루프에 묶인 Anthropic 비동기 클라이언트(`langchain_anthropic`이 `lru_cache`로 공유)를 두 번째 실행이 받아 이 오류가 난다. `run_small_compare`는 `_run_blocking`이 `with_own_anthropic_client`로 실행을 감싸 피한다 (`cap_lab/notebook.py:122`, `cap_lab/experiment.py:560`). 직접 만든 도우미나 고친 `_run_blocking`에서는 다시 날 수 있다. 첫 실행은 되고 이후만 실패하면 이 경우를 의심한다. `run_experiment`의 `record="langfuse"`에서 반복 2 이상이 같은 이유로 실패하던 것도 고쳤다. Langfuse는 반복마다 새 이벤트 루프를 돌고, 사례 실행을 `with_own_anthropic_client`로 감싼다 (`cap_lab/experiment.py:535`, 스레드 호출은 `cap_lab/experiment.py:544`). 시험은 `tests/test_notebook_helpers.py:301`이며 가짜 Langfuse로 오프라인에서만 돌렸다. 실제 Langfuse로는 아직 돌리지 않았다(키가 유효하지 않다). `record="local"`은 이 경로를 쓰지 않는다.
- **02 셀 32와 05 셀 27의 stderr에 나오던 `Task exception was never retrieved ... Event loop is closed` 블록(2차 실측에서 11개씩)은 고쳤다.** 원인은 캐시에서 버려진 클라이언트의 `__del__`이 그때 도는 루프에 `aclose()`를 예약하는 것이었다. `with_own_anthropic_client`가 실행 중 만든 클라이언트를 루프가 끝나기 전에 같은 루프에서 닫는다 (`cap_lab/experiment.py:560`, `cap_lab/notebook.py:122`). 시험은 `tests/test_notebook_helpers.py:283`이다. 고친 뒤의 노트북 전체 재실행은 하지 않았으므로 `outputs/live/summary.json`의 기록에는 옛 소음이 남아 있다. 06 셀 64는 kernel 루프에서 돌아 나오지 않았다. 다시 같은 경고가 보이면 점수가 `None`인지부터 보고, `None`이면 `RunRecord.error`를 먼저 본다. 2차 실측에서 이 외의 예상 밖 오류는 없었다(호출 오류 0, 429·529 없음).
- **`mcp_elicitation` interrupt가 와서 멈춘 것처럼 보인다.** 서버가 사용자에게 되묻는 질문(MRTR)이 LangGraph의 `interrupt`로 올라온 것이다. 실행기는 사례 파일에 적힌 응답으로 재개한다 (`cap_lab/experiment.py:288`). `mcp_elicitation`이 아닌 interrupt는 `RuntimeError`다 (`cap_lab/experiment.py:294`). 재개는 한 턴에 5번까지이고 넘으면 멈춘다 (`cap_lab/experiment.py:231-234`). 직접 에이전트를 돌리는 셀에서 `checkpointer`와 `thread_id` 없이 재개하려 하면 재개되지 않는다 (`cap_lab/agent.py:89`의 docstring).
- **`GoalGuard`가 `goal_changed`를 돌려준다.** `start_interview`의 `goal` 인자가 사용자가 말한 문장과 다르다고 Jev가 판단했거나(확률이 문턱값 미만) 판단하지 못한 경우(`decision_unavailable`)다 (`cap_lab/middleware.py:82-94`). 모델은 "목표 문장을 그대로 goal에 넣으세요"라는 메시지를 받고 다시 부를 수 있다. 문턱값 0.5는 재지 않은 자리값이다.
- **점수가 `False`가 아니라 `None`이다.** 실행 오류(`RunRecord.error`)가 있으면 그 검사는 `None`(확인 불가)이다 (`cap_lab/scorers.py:299`). 사례에 해당하지 않는 검사도 `None`일 수 있다. `None`은 통과도 실패도 아니고 통과율의 분모에 들어가지 않는다 (`cap_lab/notebook.py:180`). 통과율 표의 `unchecked` 칸이 그 수다. `first_failure`는 `False`만 센다 (`cap_lab/scorers.py:322`).
  `pass_rate_table`에 `model_calls` 같은 수치나 없는 점수 이름을 넘기면 `ValueError`다 (`cap_lab/notebook.py:188-190`).
- **실행 이름이 이미 있다는 `RuntimeError`.** `run_experiment`는 `<변형 이름>-r<k>`의 로컬 사본이나 작업 폴더가 있으면 시작하지 않는다 (`cap_lab/experiment.py:511-515`). 이어 쓰면 다른 실행이 섞이기 때문이다. 변형 이름을 바꾸거나 기존 기록을 다른 곳으로 옮기게 한다. 기록을 지워서 통과시키지 않는다 (5장 2번). 07은 이것을 `[깨뜨리기]` 셀로 보여 준다.
- **holdout 사례를 돌리려 한다.** `run_small_compare`가 dev 사례가 아니라고 `ValueError`를 낸다 (`cap_lab/notebook.py:131-138`). 의도된 거부다 (5장 1번).
- **같은 라벨로 작업 폴더를 두 번 만들면 `FileExistsError`.** 폴더 이름이 `<라벨>-<날짜-시각(초)>`이라 같은 초에 두 번 부르면 겹친다 (`cap_lab/notebook.py:68`).
- **서버가 응답하지 않거나 파싱 오류가 난다.** stdio 서버의 stdout은 MCP 통신 전용이다 (`cap_lab/server/server.py:435`). 서버 코드에 `print`를 넣으면 통신이 깨질 수 있다. 진단은 stderr에 쓴다.
- **같은 질문인데 결과가 달라진다.** 모델 결과는 실행마다 다르다. 1회 관찰이라고 부르고 반복으로 본다 (5장 4번).

---

## 8. 문서와 코드가 다른 곳

문서와 코드가 다르면 코드가 정답이다. 발견하면 수강생에게 알린다.

- `docs/DESIGN.md` 3절 노트북 지도의 04 행은 "영속화와 재생, 근거 파일, Streamable HTTP, ..., H1 서버 게이트(fail-closed)" 순서로 적는다. 노트북 04는 무료 절을 유료 절보다 앞에 두도록 순서를 바꿨다. 순서는 노트북이 정답이다.
- `docs/DESIGN.md` 5절은 `mcp_protocol_version`이 `unknown`으로 남았다고 적는다(스모크 스크립트의 결과). 00 노트북은 `client.protocol_version`을 읽는다. 노트북이 정답이다.
- `docs/DESIGN.md` 5절은 Langfuse 인증이 복사한 키로 실패했다고 적는다. 키 교체는 저자가 하며, 교체 전에는 07의 측정이 시작되지 않는다 (7장). 저자 측정은 개정 2로 Langfuse 없이 로컬 사본에 남기므로(`tests/run_measurement.py`) 이 경고와 별개다. 개정 2 반영은 `docs/DESIGN.md:73`과 `docs/DESIGN.md:123`에 있다.
- `docs/DESIGN.md` 8절은 holdout을 "8 × 5 × 3 = 120회"로 적는다. 개정 1 이후의 값이다. 개정 전 문서(P4 "holdout 6")를 보는 자료가 있으면 개정 1이 정답이다.
- 개정 2(2026-11-02)는 P4의 두 줄만 바꿨고, 개정 1·개정 2 이전 문서를 보는 자료는 `docs/DESIGN.md`의 개정 2 절이 정답이다. 그 해시는 `docs/prereg.sha256`이다.
- `docs/DESIGN.md` P4의 "저자 실행 N=5, 수업 N=3"은 저자 실행과 수업의 구분이다. 07 노트북의 반복은 3(`CLASS_REPEATS`)이다.
- `cap_lab/notebook.py`의 도우미 이름은 바뀔 수 있다. 07이 쓰는 `cost_notice`, `run_metadata`, `case_values`(`cap_lab/experiment.py:432`, `cap_lab/experiment.py:412`, `cap_lab/experiment.py:644`)는 공개 함수다. 줄 번호가 안 맞으면 파일을 다시 읽는다.
- 줄 번호는 이 문서를 쓴 시점의 코드 기준이다. `cap_lab/`을 고치면 어긋난다. 9장 방법으로 다시 확인한다.

---

## 9. 인용 검증

이 문서의 `파일:줄`은 2026-11-02에 `sed -n '<줄>p' <파일>`로 한 줄씩 확인했다. 4장 표의 `이름:줄`은 그 줄에 이름이 있다는 뜻이다(`Settings:33`이면 `cap_lab/settings.py`의 33번째 줄에 `class Settings`).
3b 단계에서 `cap_lab/experiment.py`, `agent.py`, `middleware.py`, `notebook.py`의 줄이 밀려 다시 확인했고, 3c 단계에서 `with_own_anthropic_client` 추가로 `experiment.py`와 `notebook.py`의 줄이 다시 밀려 고쳤다.
코드를 고친 뒤에는 같은 방법으로 다시 확인하고, 줄이 밀렸으면 이 문서를 고친다. 시험을 고치거나 한도를 올려서 맞추지 않는다.
노트북 안의 `파일:줄` 인용은 저자용 도구 `nb_citations.py`로 검사했다(저장소 밖 작업 폴더에 있어 이 저장소에는 없다. 확인이 필요하면 저자에게 묻는다).
확인된 것: 노트북 00~06을 수정(캐시·루프) 뒤에 실제 키로 끝까지 실행했고 호출 오류가 0건이었다. 07은 셀 48의 Langfuse 확인까지만 실행했고 거기서 설계대로 멈췄다(`outputs/live/summary.json`). 저자 dev 기준선 A·A2를 로컬 사본으로 측정했다(`outputs/runs/dev-baseline-summary.json`) 변형 B와 holdout(A·A2·B)도 2026-11-03에 로컬 사본으로 측정했다(`outputs/decisions/dev-decision.json`, `outputs/decisions/holdout-decision.json`).
확인되지 않은 것: 07의 측정 셀 전부(Langfuse 기록 포함)와 그 실제 비용(07의 수업 측정은 아직 측정하지 않았다), 고친 `with_own_anthropic_client`의 실제 Langfuse 경로 실행, `RUN_EXERCISE`·`RUN_OPTIONAL`을 켠 셀, 캐시 적중률과 캐시 쓰기 토큰, USD, Streamable HTTP의 장시간 동작, 위 7장에서 "추정"이라고 표시한 항목.
