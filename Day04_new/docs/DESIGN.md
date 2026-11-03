# Day04_new 설계와 사전 등록

작성일 2026-11-02. `Day04/`는 그대로 두고 `Day04_new/`를 노트북 과정으로 만든다. 이 문서는 설계와 사전 등록(pre-registration)을 한 곳에 둔다. 사전 등록 블록(`PREREG:BEGIN`~`PREREG:END`)은 이 문서가 확정된 뒤 수정하지 않는다. 측정 결과는 블록 뒤에 별도 절로 덧붙인다.

## 1. 목적과 저자 결정

저자가 정한 과정 개요(원문 그대로):

- Part 1. Advanced Agent Capability 설계 실습
- Part 2. Advanced Tool Interface 실습
- Part 3. MCP Client/Server 기본 구현 실습
- Part 4. Production MCP 심화 실습
- Part 5. Skill + MCP 통합 실습
- 실습: Agent Capability 평가와 Debugging (Tool 선택과 Argument Correctness / Trigger Eval과 Quality Eval 분리 / 권한 거부·오류·재시도·중복 실행 Test)

저자 결정(2026-11-02):

- 주 모델은 ChatAnthropic `claude-sonnet-5-5`, effort는 medium이며 `.env`로 지정한다.
- 키는 복사해서 쓴다. Anthropic과 TYPESAFE 키는 `Day02_new/.env`, LANGFUSE 키는 `Day05/.env`에서 가져왔다. Langfuse 키는 저자가 나중에 교체한다.
- 병목으로 측정된 곳의 판단(Decision)은 Jev를 거친다.
- 개선은 실제로 측정한다. 측정 기록은 Langfuse에 남긴다.
- 모든 코드는 제공하며 채점은 없다(Day03_new 방식).
- MRTR을 포함한다.
- 새 패키지는 추가하지 않는다(uv `exclude-newer` 2026-10-31). `langchain-typesafe`는 설치되어 있지 않으므로 Jev는 `Day02_new/rag_lab/decisions.py`를 맞게 고친 사본으로 호출한다.

## 2. 가정(바꿀 수 있음)

- 총 약 6.5시간. 분량은 00 Setup 10분, 01~05 각 50분, 06 60분, 07 70분.
- Part 2와 Part 5는 수업 중에 작은 실측 비교를 한다. 각각 2 사례 x 3 반복 x 2 변형.

## 3. 노트북 지도

| 노트북 | Part | 핵심 질문 | 기존 Day04에서 가져올 것 | 새로 만들 것 |
|---|---|---|---|---|
| 00 Setup | - | 키·서버·프로토콜 버전이 준비되었는가 | `Day04/build_mcp/reference/server.py` | 키 설정 상태 확인, server/discover, 프로토콜 버전 확인 |
| 01 Agent Capability | 1 | 능력은 무엇으로 이루어지고 판단은 어디에 두는가 | - | capability = 지침(Skill) + 도구 + 실행 제어 + 상태. `create_deep_agent` 기본 도구. 판단 위치 구분: 코드 규칙 vs 판단 모델(Jev) vs 생성(LLM) |
| 02 Tool Interface | 2 | 모델이 도구를 정확히 고르고 인자를 채우게 하려면 | `Day04/build_mcp/MCP_GUIDE.md` 7절, 스칼라만 다루는 한계(`Day04/build_mcp/MCP_GUIDE.md:74`) | 이름, description, Literal enum, JSON Schema 2020-12, outputSchema, ToolAnnotations(힌트일 뿐 강제 아님), 업무 오류 vs isError, 서버가 발급하는 핸들(SEP-2567) |
| 03 MCP 기본 | 3 | stdio 서버와 클라이언트는 무엇을 주고받는가 | `Day04/build_mcp/reference/server.py`, `verify.py` 1~3단계 | stdio, tools/list, tools/call, `mcp.Client` vs `langchain.mcp.MCPAdapter` |
| 04 Production MCP | 4 | 재시도·재개·캐시·추적을 어떻게 견디는가 | 멱등성 표(`Day04/build_mcp/MCP_GUIDE.md:167-175`) | 영속화와 재생, 근거 파일, Streamable HTTP, ttlMs/cacheScope, MRTR, `_meta`의 traceparent, H1 서버 게이트(fail-closed `decision_unavailable`), 인증은 개념만(CIMD) |
| 05 Skill + MCP | 5 | MCP 도구를 Skill이 읽힌 뒤에만 노출하면 | `Day04/build_mcp/script_runtime.py`의 execute | `metadata.include_tools`, MCP vs Skill 스크립트 비교 |
| 06 평가와 디버깅 | 실습 | 능력 수준의 결함을 어떻게 가르는가 | - | 도구 선택, 인자 정확성, Trigger Eval vs Quality Eval, 권한 거부, 오류, 재시도, 중복 실행. 결정적 scorer만 사용 |
| 07 개선과 측정 | 실습 | 병목은 어디이고 게이트가 실제로 개선하는가 | - | 병목 찾기, Jev 게이트, A/A와 쌍체 비교, Langfuse. 수강생이 dev에서 Jev 질문이나 임계값을 고치고 다시 측정 |

## 4. 경계

- SKILL.md 형식은 `Day02_new`의 03-Agent-Skills가 이미 가르친다. 링크하고 다시 가르치지 않는다.
- Day05는 업무 결과, DeepEval 지표, LLM judge, 회귀 승격을 맡는다. Day04_new는 능력 수준의 결정적 검사와 A/A + 쌍체 비교 방법을 맡는다.
- Day08은 가드레일 배치, HITL 승인, 주입 방어를 맡는다.

## 5. 확인한 사실

2026-11-02 키 없이 한 탐침. 설치 버전: mcp 2.3.0, deepagents 0.7.32, langchain 1.4.7, fastmcp 4.1.4, langfuse 4.15.1.

- `langchain.mcp.MCPAdapter`와 fastmcp `PythonStdioTransport`로 `Day04/build_mcp/reference/server.py`의 도구 7개가 field enum을 보존한 채 로드되고, `create_deep_agent`가 그것을 받는다.
- deepagents 기본 도구: ls, read_file, write_file, edit_file, delete, glob, grep, task. write_todos는 선택(opt-in).
- 도구 매개변수를 `Annotated[Model, Resolve(ask)]`로 선언하고 `ask`가 `Elicit(...)`을 돌려주면(`mcp/server/mcpserver/resolve.py`) 모델에 보이는 인자에 나타나지 않는다(탐침 결과 `['goal']`만 보임). 호출은 `{type: mcp_elicitation, ...}` interrupt를 올리고 `Command(resume={"responses": {key: {"action": "accept", "content": {...}}}})`로 재개된다. `create_agent`와 `create_deep_agent` 양쪽에서 확인.
- deepagents `SkillToolResolver`는 `.venv/lib/python3.13/site-packages/deepagents/middleware/skills.py:176`, description 길이 한도 1024는 `.venv/lib/python3.13/site-packages/deepagents/middleware/skills.py:173`.
- `FilesystemPermission`의 deny는 `.venv/lib/python3.13/site-packages/deepagents/middleware/filesystem.py:382`.
- ToolAnnotations 필드는 `.venv/lib/python3.13/site-packages/mcp_types/_v2026_07_28/__init__.py:1091-1118`.
- traceparent 도우미는 `.venv/lib/python3.13/site-packages/mcp/shared/_otel.py:39`, `.venv/lib/python3.13/site-packages/fastmcp/telemetry.py:152`.
- MCP 2026-07-28 변경: stateless(initialize 제거, 요청마다 `_meta`에 프로토콜 버전과 capabilities, SEP-2575), server/discover, Mcp-Session-Id 제거와 도구 인자로 쓰는 서버 발급 핸들(SEP-2567), MRTR `InputRequiredResult`가 서버 주도 elicitation/sampling/roots를 대체(SEP-2322), tasks는 확장으로 이동(SEP-2663), subscriptions/listen, ttlMs/cacheScope(SEP-2549), tools/list 순서 결정적, 스키마는 JSON Schema 2020-12(SEP-2106), Roots/Sampling/Logging 폐기 예정(SEP-2577), DCR은 Client ID Metadata Documents로 대체 예정.
- 실행 스모크(env-smoke, `Day04_new/.env`): Claude ok, Jev ok(`POST https://api.typesafe.ai/v1/systemone`, `noul` 질문, 확률은 `answers.judgeable.noul`). traceparent는 MCP 요청 `_meta`로 도착하고 Langfuse trace id와 일치한다(`traceparent_received` true, `traceparent_matches_langfuse` true). Langfuse 인증은 복사한 키로 실패했다(`langfuse_auth: fail: UnauthorizedError`, 401). `mcp_protocol_version`은 `unknown`으로 남았다.
- 기존 Day04 실행 기록으로는 병목을 찾을 수 없다. 검증 보고서가 4건뿐이고 2026-10-31 보고서는 1.91초 만에 ExceptionGroup(인프라)으로 실패했다. 병목은 새로 측정해야 한다.

## 6. 미확인

- MRTR과 `include_tools` 아래의 실제 모델 행동
- Streamable HTTP 실행
- tasks 확장
- agentskills.io 2026 명세에서 1024자 한도 외의 변경
- 유효한 키로 한 Langfuse 인증, 그리고 서버 쪽 span이 실제로 Langfuse에 내보내지는지

Langfuse 인증: 복사한 키가 401이므로 저자가 키를 교체한다. 개정 2에 따라 저자 측정(dev, holdout)은 Langfuse 없이 로컬로 돌리므로 키 교체는 그 측정의 선행 조건이 아니다. Langfuse에 기록하는 07 수업 측정만 인증 확인(`auth_check`가 True)이 시작 전에 통과해야 한다.

<!-- PREREG:BEGIN -->
## 사전 등록 (이 블록은 확정 후 수정하지 않는다)

### P1. 단계와 scorer

단계 순서: S1 Skill 트리거, S2 시작 인자(goal 유지), S3 모호한 답변을 명확히 함, S5 결과 확정(freeze), S6 근거 연결. S4는 동의 단계였고 H3와 함께 제거되었다. 견고성 검사: R1 권한 거부, R2 일시 오류, R3 중복 호출.

| scorer | 단계 | 종류 |
|---|---|---|
| trigger_ok | S1 | boolean |
| tool_selection_ok | S2 | boolean |
| args_valid | S2 | boolean |
| goal_preserved | S2 | boolean |
| vague_not_frozen | S3 | boolean |
| frozen_ok | S5 | boolean |
| evidence_linked | S6 | boolean |
| no_blind_retry | R1 | boolean |
| retry_bounded | R2 | boolean |
| side_effect_stable | R3 | boolean |
| contamination_free | 전체 | boolean |
| model_calls, tool_calls, latency_s, input_tokens, output_tokens | 전체 | 숫자 |

해당 없음은 null(검사 안 함)이며 false가 아니다.

### P2. 가설

H1 (S3): 서버는 테스트 가능성에 대한 Jev Score 질문이 임계값 이상일 때만 인수 기준(acceptance criterion)을 기록한다. 미만이면 서버가 MRTR로 사용자에게 직접 묻는다(모델은 그 인자를 보거나 채울 수 없다). 사용자가 거절하면 `criteria_not_testable`을 돌려준다. Jev가 어떤 이유로든 실패하면 `decision_unavailable`을 돌려주고 아무것도 기록하지 않는다(fail-closed). 목표 지표는 `vague_criteria` 사례의 `vague_not_frozen`.

H2 (S2): 에이전트 미들웨어 GoalGuard가 Jev Noul 질문으로 `start_interview`의 goal 인자가 사용자가 말한 목표를 바꾸지 않고 유지하는지 묻는다. 임계값 미만이면 호출을 `goal_changed`로 막는다. Jev가 실패하면 `decision_unavailable`(fail-closed). 목표 지표는 `goal_verbatim` 사례의 `goal_preserved`.

제거: H3 확정 전 동의(Day08의 HITL/행동 가드레일 소관), H4 Jev Skill 라우팅(Trigger Eval이 재는 대상을 바꾸게 된다).

교육용 반례로 남긴다: 재시도 라우팅은 구조화된 오류 코드(`Day04/build_mcp/MCP_GUIDE.md` 7절)로 하므로 Jev 판단이 아니라 코드 규칙이다.

### P3. 병목 귀속

각 실행의 실패는 S1..S6 순서에서 가장 먼저 실패한 단계에 귀속한다. 병목이 되려면 (1) 최초 실패 비중이 가장 크고, (2) 판단 형태의 문제이며, (3) 그것을 푸는 결정적 규칙이 없어야 한다. 기준선이 H1 또는 H2와 모순되면 게이트 위치를 바꾸기 전에 저자에게 묻는다. 수치에 효과가 없어 보인다는 이유로 게이트를 제거하지 않고 수치를 있는 그대로 보고한다.

### P4. 프로토콜

- 사례는 `Day04_new/data/cases.jsonl`이다(dev 10, holdout 8; metadata는 split, stage, kind). Langfuse에 기록하는 실행은 이 파일로 데이터셋 `day04_new-capability-v1`을 만든다.
- holdout은 최종 주장을 위해 한 번만 연다. holdout도 A, A2, B 세 변형으로 돌린다.
- 임계값은 저자가 검토한 뒤의 `Day04_new/data/gate_labels_draft.jsonl` dev 라벨로만 조정한다. 초기 임계값 0.5는 자리표시자이며 미조정으로 표시한다.
- 사례마다 사용자 발화와 elicitation 응답은 스크립트로 정해 둔다. LLM이 사용자를 흉내 내지 않는다.
- 변형: A(게이트 끔), A2(게이트 끔, A/A용 반복), B(H1과 H2 켬). 두 게이트는 서로 다른 단계를 겨냥하므로 목표 지표를 각각 따로 읽고, 상호작용 가능성은 주의사항으로 적는다.
- 반복 횟수: 저자 실행 N=5, 수업 N=3.
- 각 실행의 metadata에 모델, effort, SKILL.md sha256, 서버 코드 sha256, 게이트 플래그, 임계값, Jev 모델 id, 데이터셋 버전을 고정해 기록한다.
- 로컬 사본 `Day04_new/outputs/runs/*.jsonl`은 오류를 포함한 모든 항목을 남긴다.
- 저자 측정(dev, holdout)은 Langfuse에 기록하지 않고 로컬 사본과 `<실행 이름>.meta.json`에만 남긴다(개정 2). Langfuse에 기록하는 유료 실행(07 수업 측정)은 시작 전에 인증 확인이 통과해야 한다.

### P5. 판정 규칙 (`Day04_new/cap_lab/stats.py`의 `decide()`와 일치)

- 사례 단위 쌍체 부트스트랩: 10000회, seed 0, 95% 백분위 구간. 통계량은 사례별 (B 평균 - A 평균)의 평균이다.
- 지표별 잡음 폭 = A 대 A2 비교 구간의 max(|lo|, |hi|).
- 판정은 아래 순서로 첫 일치 조건을 따른다.
  1. 목표 지표 비교 결과가 없으면 `판정 불가: 데이터 부족`.
  2. 목표 구간 상한 hi < 0이면 `회귀`.
  3. 목표 구간 하한 lo <= 0이면 `개선 확인 불가`.
  4. 가드 지표의 비교 결과 또는 잡음 폭이 없으면 `판정 불가: 데이터 부족`.
  5. 가드 지표가 잡음 폭을 넘어 나빠졌으면(높을수록 좋은 지표는 diff < -잡음 폭, 낮을수록 좋은 지표는 diff > 잡음 폭) `교환`.
  6. 그 밖에는 `개선`.
- 결과를 본 뒤 반복을 늘리지 않고 예산(budget)을 올리지 않는다.

### P6. 가드 지표

목표 지표가 아닌 모든 boolean scorer와 model_calls, tool_calls, latency_s. 숫자 세 가지는 낮을수록 좋다.

### P7. 오염 방지

에이전트 프로세스는 `Day04_new/data/`를 읽지 않는다. 도구 인자나 읽은 경로에 `cases.jsonl`, `gate_labels`, `/data/` 중 하나라도 나오면 `contamination_free`는 실패다.
<!-- PREREG:END -->

## 사전 등록 개정 1 (2026-11-02, 유료 측정 전)

저자가 2026-11-02에 결정했다. PREREG 블록은 P4의 아래 두 줄만 바꾸었고 P5 판정 규칙을 포함한 나머지 바이트는 그대로다.

- 개정 전 블록 sha256: `39435e721a73580f0a7a46bf8c41770ecfb2567904ba9251869041c89441b745`
- 개정 후 블록 sha256: `0fd3e8062667bcb25495bcab949085baa08654fa7cd8de98b45445ce1a7c68fe` (`Day04_new/docs/prereg.sha256`에 기록)

바뀐 줄(P4):

```text
(전) - Langfuse 데이터셋 `day04_new-capability-v1`을 `Day04_new/data/cases.jsonl`에서 만든다(dev 10, holdout 6; metadata는 split, stage, kind).
(후) - Langfuse 데이터셋 `day04_new-capability-v1`을 `Day04_new/data/cases.jsonl`에서 만든다(dev 10, holdout 8; metadata는 split, stage, kind).
(전) - holdout은 최종 주장을 위해 한 번만 연다.
(후) - holdout은 최종 주장을 위해 한 번만 연다. holdout도 A, A2, B 세 변형으로 돌린다.
```

사례 추가: `ho-07`(R1 권한 거부, `freeze_seed` 거부)와 `ho-08`(R2 일시 오류, `start_interview` 1회 장애)를 `Day04_new/data/cases.jsonl`에 덧붙였다. 기존 사례는 바꾸지 않았다.

이유: 확정된 설계로는 holdout 판정이 구조적으로 항상 `판정 불가: 데이터 부족`이었다.

1. holdout을 A와 B로만 돌려(8절 6 x 5 x 2) A 대 A2 잡음 폭이 없었고, `compare()`는 가드마다 잡음 폭을 요구하므로 P5 4번이 모든 가드에서 걸렸다.
2. holdout에 R1, R2 사례가 없어 P6 가드 `no_blind_retry`, `retry_bounded`의 값이 없었고, 이것도 P5 4번을 걸었다.

저자는 "A2 + R1/R2 사례 추가"를 골랐다: holdout 8 사례 x 5 반복 x 3 변형 = 120회. P5 규칙, 임계값, 예산은 그대로다.

유료 측정이 없었다는 확인: 개정 시점에 `Day04_new/outputs/runs/` 폴더가 없다(로컬 사본 `*.jsonl` 없음). 사례 파일과 문서 외에 holdout 결과를 본 적이 없다.

## 사전 등록 개정 2 (2026-11-02, 유료 측정 전)

저자가 2026-11-02에 유료 측정 전에 승인했다. PREREG 블록은 P4의 아래 두 줄만 바꾸었고 P5 판정 규칙을 포함한 나머지 바이트는 그대로다.

- 개정 전 블록 sha256: `0fd3e8062667bcb25495bcab949085baa08654fa7cd8de98b45445ce1a7c68fe` (개정 1 이후)
- 개정 후 블록 sha256: `ee964af5717919128c9ccf1dd5adaace9da39b9f9f2b4c26f7565f2b8e939396` (`Day04_new/docs/prereg.sha256`에 기록)

바뀐 줄(P4):

```text
(전) - Langfuse 데이터셋 `day04_new-capability-v1`을 `Day04_new/data/cases.jsonl`에서 만든다(dev 10, holdout 8; metadata는 split, stage, kind).
(후) - 사례는 `Day04_new/data/cases.jsonl`이다(dev 10, holdout 8; metadata는 split, stage, kind). Langfuse에 기록하는 실행은 이 파일로 데이터셋 `day04_new-capability-v1`을 만든다.
(전) 모든 유료 실행 전에 Langfuse 인증 확인이 통과해야 한다.
(후) - 저자 측정(dev, holdout)은 Langfuse에 기록하지 않고 로컬 사본과 `<실행 이름>.meta.json`에만 남긴다(개정 2). Langfuse에 기록하는 유료 실행(07 수업 측정)은 시작 전에 인증 확인이 통과해야 한다.
```

이유: 저자가 2026-11-02에 이번 측정에는 Langfuse를 쓰지 않아도 된다고 결정했다. 복사한 Langfuse 키는 인증에서 401로 실패하고(5절), 저자가 나중에 교체한다. 판정은 로컬 사본을 `compare()`로 읽어서 하며 `compare()`는 Langfuse를 읽지 않는다.

바뀌지 않는 것: P5 판정 규칙, 임계값, 예산, 사례, 분할, 반복 횟수. 07 수강생 노트북은 그대로 Langfuse에 기록하며 인증이 실패하면 멈춘다(`run_experiment`의 기본 `record`는 `"langfuse"`).

실행기 지원: `run_experiment(..., record="local")`(`Day04_new/cap_lab/experiment.py:476`, 인자 `record` `:487`, 로컬 분기 `_run_local` `:584`)와 저자 스크립트 `Day04_new/tests/run_measurement.py`. 로컬 실행은 `outputs/runs/<실행 이름>.jsonl`과 `<실행 이름>.meta.json`(시작과 끝에 기록, 끝나지 않으면 `finished_at`이 null)을 남긴다.

키 교체 뒤 로컬 사본을 Langfuse에 올릴 수 있다. 그래도 판정은 계속 로컬 사본으로 한다.

유료 측정이 없었다는 확인: 개정 시점에 `Day04_new/outputs/runs/` 폴더가 없다(`ls`가 "No such file or directory"). 따라서 `dev-*`, `holdout-*` 사본이 없고 dev, holdout 결과를 본 적이 없다.

## 결과 1: dev 기준선 (A, A2), 2026-11-02

PREREG 블록과 개정 2 뒤에 덧붙인 결과다. 블록은 수정하지 않았다. 이 절은 dev 10사례의 기준선이며 B(게이트 켬)와 holdout은 이 절을 쓸 때 실행하지 않았다. 따라서 B에 대한 판정은 이 절에 없다(결과 2, 결과 3에 있다). 수치는 `Day04_new/outputs/runs/dev-baseline-summary.json`과 `dev-*.meta.json`에서 가져왔고, 실행 줄 수·호출 수·토큰은 `dev-*-r*.jsonl`에서 다시 합산해 일치를 확인했다.

### 설정과 실행 규모

- 설정(`dev-A-r1.meta.json`, 10개 meta 파일이 같은 설정): 모델 `claude-sonnet-5-5`, effort `medium`, interface `rich`, tool_disclosure `skill`, 게이트 H1·H2 `off`, `jev_model` `off`(Jev 사용 0회), record `local`(개정 2), SKILL.md sha256 `7c8e469a95b6c67af0387c810dca20f47bda59237ceba4fc350f34b12e79593b`, 서버 sha256 `82a13e69cde8197e39e820d5f6b487252d7b9a1f6bed4580970dc245dd39c79b`. A와 A2의 차이는 변형 이름뿐이다(A2는 A의 반복, 잡음 폭을 재는 용도).
- 실행: dev-A 5개 반복 x 10사례 = 50줄, dev-A2 50줄, 합계 100회. 오류 줄 0, 모든 meta의 `finished_at`이 채워짐(중단 없음).
- 규모: Claude 호출 497회(A 250, A2 247, `model_calls` 점수의 합), 입력 토큰 3,592,503, 출력 토큰 146,573, Jev 0회. 캐시 쓰기 토큰은 기록하지 않았다.

### 지표별 (통과/확인된 수, 미확인은 분모에서 제외; `compare()`와 같은 case_values 사용)

| 지표 | A | A2 | A2-A 차이 [95%] | 잡음 폭 | 미확인(A) |
|---|---|---|---|---|---|
| trigger_ok | 10/10 = 1.00 [0.72,1.00] | 10/10 | 0 | 0 | 40 |
| tool_selection_ok | 50/50 = 1.00 [0.93,1.00] | 50/50 | 0 | 0 | 0 |
| args_valid | 45/45 = 1.00 [0.92,1.00] | 45/45 | 0 | 0 | 5 |
| goal_preserved | 10/10 = 1.00 [0.72,1.00] | 10/10 | 0 | 0 | 40 |
| vague_not_frozen | 5/10 = 0.50 [0.24,0.76] | 4/10 = 0.40 [0.17,0.69] | -0.10 [-0.20,0.00] | 0.20 | 40 |
| frozen_ok | 10/20 = 0.50 [0.30,0.70] | 11/20 = 0.55 [0.34,0.74] | +0.05 [0.00,0.15] | 0.15 | 30 |
| evidence_linked | 10/10 = 1.00 [0.72,1.00] | 10/10 | 0 | 0 | 40 |
| no_blind_retry, retry_bounded, side_effect_stable | 각 5/5 | 각 5/5 | 0 | 0 | 45 |
| contamination_free | 50/50 | 50/50 | 0 | 0 | 0 |

수치 지표 평균 A / A2 (차이 [구간], 잡음 폭): model_calls 5.00 / 4.94 (-0.06 [-0.22,0.08], 0.22), tool_calls 4.66 / 4.62 (-0.04, 0.20), latency_s 15.16 / 14.63 (-0.53 [-1.38,0.27], 1.38), input_tokens 36,230 / 35,620 (-609, 2,282), output_tokens 1,476 / 1,455 (-21, 90). 모든 차이가 잡음 폭 안에 있다. 미확인은 그 사례에 해당 기대가 없어 채점하지 않은 실행이다(`scores`의 `value`가 null).

### P3 병목 귀속 (`attribute()`, 첫 실패 단계)

| 범위 | S1 | S2 | S3 | S5 | S6 | unchecked | no_failure |
|---|---|---|---|---|---|---|---|
| A | 0 | 0 | 5 | 5 | 0 | 0 | 40 |
| A2 | 0 | 0 | 6 | 4 | 0 | 0 | 40 |
| 합산 | 0 | 0 | 11 | 9 | 0 | 0 | 80 |

첫 실패가 있는 20회 중 S3 55%, S5 45%, S2 0%. 사례별: dev-05 A는 S5 x5, A2는 S3 x1 + S5 x4. dev-06은 A, A2 모두 S3 x5. 나머지 8사례는 10회 모두 실패 없음.

### H1/H2 목표 지표 (기준선)

H1은 S3 `vague_not_frozen`, H2는 S2 `goal_preserved`로 읽었다(위 P2).

| 목표 | 사례 | 통과율 |
|---|---|---|
| H1 vague_not_frozen (vague_criteria) | dev-05 A 5/5, A2 4/5; dev-06 A 0/5, A2 0/5; 합산 9/20 = 0.45 [0.26,0.66] | 미확인 0 |
| H2 goal_preserved (goal_verbatim) | dev-03 A 5/5, A2 5/5; dev-04 A 5/5, A2 5/5; 합산 20/20 = 1.00 [0.84,1.00] | 미확인 0 |

### P3 읽기

- 첫 실패 몫이 가장 큰 단계는 S3(11/20 = 55%)다. H1(S3)의 병목 전제와 맞는다. H1 목표 지표는 0.45(구간 0.26~0.66)라 올라갈 여지가 있다. 다만 그 실패는 사실상 dev-06 하나(10회 모두 실패)이고, dev-05는 10회 중 1회만 S3에서 실패한다(나머지 dev-05의 첫 실패는 S5).
- H2(S2)의 첫 실패는 0회이고 목표 지표 `goal_preserved`는 20/20 = 100%다. 기준선에 개선 여지가 없고 가장 큰 몫도 S2가 아니다. 이것은 P3이 말하는 "기준선이 H1 또는 H2와 모순"에 해당할 수 있다: 저자 확인 필요. P3은 이 경우 게이트 위치를 바꾸기 전에 저자에게 묻고, 효과가 없어 보인다는 이유로 게이트를 제거하지 않는다고 정한다. 이 문서는 어느 쪽도 결정하지 않았다. 저자 결정(2026-11-03): H2를 사전 등록대로 유지한다(P3: 게이트를 옮기거나 제거하지 않는다).
- S5 첫 실패 9회(45%)는 H1의 게이트가 꺼진 쪽이다. 아래 분석은 조정자가 2026-11-03에 dev-A*·dev-A2* jsonl을 `jq`로 직접 확인했다. S5 첫 실패 9회는 모두 dev-05다(`Day04_new/data/cases.jsonl:5`: kind `vague_criteria`, 기대 `frozen` true, 스크립트된 elicitation `acceptance_criteria`가 있다). 그 실행들에서 에이전트는 `freeze_seed`를 부르지 않았고 마지막 글에서 사용자에게 테스트할 수 있는 완료 기준을 달라고 물었다. 기준선 100회 모두 `interrupts`가 비어 있다. 스크립트된 답은 H1 게이트의 Elicit을 거쳐서만 에이전트에 닿는다(`Day04_new/cap_lab/server/server.py:242-246`, `:259-290`; 실행기가 답하는 곳은 `Day04_new/cap_lab/experiment.py`의 `_elicitation_response`, `:305`). 그리고 A와 A2는 게이트가 꺼져 있다. 따라서 게이트가 꺼진 dev-05는 S3(모호한 문장을 그대로 확정)에서 실패하거나 S5(`frozen_ok`, `Day04_new/cap_lab/scorers.py:209-216`)에서 실패할 수밖에 없다. `frozen_ok`를 통과한 A2의 한 실행이 바로 S3에서 실패한 실행이다. 그러므로 S5 몫은 별도의 병목이 아니라 H1 사례의 게이트 꺼진 쪽이다. 기준선 실패 20회가 모두 H1의 목표 사례 둘(dev-05, dev-06)에 있고, 가드인 `frozen_ok` 실패도 전부 이 두 사례에 있다. 이전에 적었던 S5에 대한 `저자 확인 필요`는 이 분석으로 해소되었다.
- 이 값은 dev 10사례(목표 사례는 H1 2개, H2 2개)이고 사례당 5회 반복이라 표본이 매우 작다. 위 신뢰구간이 넓다.
- 측정되지 않은 것: 기준선 시점에는 B(게이트 켬)와 holdout을 실행하지 않았다. 게이트의 효과는 이 절만으로 말할 수 없다(B와 holdout은 결과 2, 결과 3).

### 측정 전에 찾아 고친 코드 결함 세 가지

첫 번째 실제 실행(`Day04_new/outputs/live-pass1`, 노트북 00~07)이 측정 전에 코드 결함 두 가지(A, B)를 드러냈다. Claude 호출 39회 중 29회가 실패했다. 세 번째(C)는 2차 실행의 stderr 소음이며 3c 단계(2026-11-03)에서 (B)와 함께 고쳤다.

- (A) 모든 skill 공개 방식의 Claude 호출이 HTTP 400(`Tool 'save_evidence' cannot have both defer_loading=true and cache_control set.`)으로 실패했다. 기본 프롬프트 캐싱이 마지막 도구에 `cache_control`을 붙였는데 그 도구가 `defer_loading`이었다. 수정(cache-fix): `Day04_new/cap_lab/middleware.py:126`의 `DeferralSafePromptCaching`(`name` `:138`, `_apply_caching` `:141`)이 기본 미들웨어를 이름으로 대체하고 태그를 deferred가 아닌 마지막 도구(`grep`)로 옮긴다. 등록은 `Day04_new/cap_lab/agent.py:133`, 테스트는 `Day04_new/tests/test_agent.py:295`, `:301`. upfront 요청은 그대로이고 deferral도 끄지 않았다.
- (B) 한 프로세스에서 두 번째 이후의 `run_small_compare`가 `Connection error.`로 실패했다(원인은 추정이 아니라 수정 노드가 offline 테스트로 재현했다: 실행마다 새 이벤트 루프를 쓰는 `_run_blocking`과 `lru_cache`로 공유되는 비동기 클라이언트). 1차 수정은 `_run_blocking`에서 실행마다 캐시를 비웠다. 3c에서 이것을 `with_own_anthropic_client`(`Day04_new/cap_lab/experiment.py:560`)로 바꿨다. 이 도우미는 이번 이벤트 루프 안에서 Anthropic 비동기 클라이언트를 새로 만들어 쓰고 루프가 끝나기 전에 같은 루프에서 닫는다. `_run_blocking`(`Day04_new/cap_lab/notebook.py:116`)이 `:122`에서 부르고, 가져오기는 `:24`다. 같은 위험이 있던 Langfuse 경로(`record="langfuse"`, 반복 2 이상)는 `run_experiment`의 task가 `run_case`를 이 도우미로 감싸게 고쳤다(`Day04_new/cap_lab/experiment.py:535`; 스레드에서 Langfuse를 부르는 `asyncio.to_thread`는 `:544`). 이 task에서 `run_case`의 결과를 받던 지역 변수 `record`가 `run_experiment`의 인자 `record`(`:487`)를 가렸으므로 `run_record`로 이름을 바꿨다(`:535`, `:539`). 테스트: `Day04_new/tests/test_notebook_helpers.py:283`(`test_three_runs_in_a_notebook_cell_leave_no_unretrieved_task_exception`), `:301`(`test_run_experiment_langfuse_repeats_each_reach_the_api_from_their_own_event_loop`). Langfuse 반복 실패는 오프라인 가짜 API로 재현했다(수정 전 `[None, 'AnthropicConnectionError: Connection error.']`, 수정 뒤 `[None, None]`). 실제 Langfuse 기록으로는 확인하지 못했다(키가 무효). 이 줄의 이전 문구 "추정, 확인 필요"는 이 재현으로 해소되었다.
- (C) 02 셀 32와 05 셀 27의 stderr에 `Task exception was never retrieved ... RuntimeError('Event loop is closed')`가 나왔다(2차 실행, 11개씩, 결과에는 영향 없음). 원인은 `langchain_anthropic`의 `_AsyncHttpxClientWrapper.__del__`이 실행 중인 루프에 `aclose()`를 예약하는데 그 루프가 이미 닫혔기 때문이다. 이 가설을 오프라인 테스트가 재현했고(수정 전 `Task exception was never retrieved ... AsyncClient.aclose() ... RuntimeError('Event loop is closed')`가 한 건 이상 잡힘) (B)와 같은 도우미가 고친다. 테스트는 `Day04_new/tests/test_notebook_helpers.py:283`이다. 실제 확인: 한 `asyncio.run` 안에서 `run_small_compare`를 두 번(dev-01, dev-02, 반복 1) 불러 행 4개가 모두 `error` None이었고 stderr에 `Task exception was never retrieved`와 `Event loop is closed`가 0건이었다(stderr 2줄은 `LangChainBetaWarning`뿐). 이 실제 확인은 Claude 8호출이다(8장).

측정되는 경로는 바뀌지 않았다. 실행 전에 `check_measured`가 "measured path unchanged (38 objects)"를 확인했고 `SHA256SUMS`가 모두 일치했다(dev B, holdout 전).

기준선(dev-A, dev-A2)은 (A), (B)의 1차 수정 뒤에 실행했고, dev-B와 holdout은 (C)까지 고친 뒤에 실행했다. 2차 노트북 실행에서 오류 0이었다(8장).

## 결과 2: dev B 판정 (H1·H2), 2026-11-03

PREREG 블록은 수정하지 않았다. 수치는 `Day04_new/outputs/decisions/dev-decision.json`(`cap_lab`의 `compare()`와 `decide()` 반환값)과 `Day04_new/outputs/runs/dev-B-r*.meta.json`에서 가져왔다. 판정 낱말과 이유는 JSON 원문 그대로다. 잡음 폭은 dev A 대 A2다.

### 설정과 규모

- 설정(`dev-B-r1.meta.json`, 5개 meta가 같은 설정): 모델 `claude-sonnet-5-5`, effort `medium`, interface `rich`, tool_disclosure `skill`, 게이트 H1·H2 `on`, 임계값 0.5와 0.5, `jev_model` `typesafe:jev-latest`, record `local`.
- 임계값 0.5는 미조정이다. 저자 결정(2026-11-03)으로 라벨을 검토하지 않은 채 0.5를 유지했고 `Day04_new/data/gate_labels_draft.jsonl`은 읽지 않았다. 판정 JSON의 `thresholds.tuned`는 false다.
- 서버 sha256 `82a13e69cde8197e39e820d5f6b487252d7b9a1f6bed4580970dc245dd39c79b`와 SKILL.md sha256 `7c8e469a95b6c67af0387c810dca20f47bda59237ceba4fc350f34b12e79593b`는 dev A와 같다.
- 실행: 5개 반복 x 10사례 = 50줄. 오류 줄 0, `decision_unavailable` 줄 0, 모든 meta의 `finished_at`이 채워짐. 2026-11-02 16:11:01Z에서 16:24:53Z까지 13분 52초.
- 규모: Claude 호출 226회(`model_calls` 합), 입력 토큰 1,586,157, 출력 토큰 68,939. Jev는 `gate_decisions` 기록으로 센 하한 60회(h1 20, h2 40).

### 목표별 판정 (A 대 B)

| 목표 | 차이 [lo, hi] | n_cases | 잡음 폭 | 판정 | 이유(원문) |
|---|---|---|---|---|---|
| H1 vague_not_frozen | 0.5 [0.0, 1.0] | 2 | 0.2 | 개선 확인 불가 | 목표 지표 구간 하한 0.000이 0 이하라 개선을 확인할 수 없습니다. |
| H2 goal_preserved | 0.0 [0.0, 0.0] | 2 | 0.0 | 개선 확인 불가 | 목표 지표 구간 하한 0.000이 0 이하라 개선을 확인할 수 없습니다. |

두 목표 모두 가드 데이터가 빠진 것이 없다(`guards_without_data` 빈 목록).

### 움직인 가드 (A 대 B 차이 [lo, hi], 잡음 폭)

- `frozen_ok`: +0.25 [0.00, 0.75], n_cases 4, 잡음 0.15.
- `model_calls`: -0.48 [-1.10, -0.06], 잡음 0.22. `tool_calls`: -0.40 [-1.06, 0.06], 잡음 0.20. `latency_s`: -1.38 [-3.06, -0.11], 잡음 1.38. 세 수치는 낮을수록 좋은 방향이다.
- 나머지 가드(`trigger_ok`, `tool_selection_ok`, `args_valid`, `evidence_linked`, `no_blind_retry`, `retry_bounded`, `side_effect_stable`, `contamination_free`)의 차이는 모두 0이다. 판정이 교환·회귀로 가지 않았다.

### 사례별 통과/반복 (목표 사례)

| 사례 | A | A2 | B |
|---|---|---|---|
| dev-05 (H1) | 5/5 | 4/5 | 5/5 |
| dev-06 (H1) | 0/5 | 0/5 | 5/5 |
| dev-03 (H2) | 5/5 | 5/5 | 5/5 |
| dev-04 (H2) | 5/5 | 5/5 | 5/5 |

H1의 점추정 +0.5는 dev-06 한 사례에서 나온다. 목표 사례가 2개뿐이라 사례 단위 쌍체 부트스트랩의 하한이 0이 된다(`decide()`가 규칙대로 "개선 확인 불가"를 냈다). H2는 A에서 이미 20/20이라 올라갈 여지가 없었다.

### P3 병목 귀속 (첫 실패 단계, 50회 중)

| 변형 | S1 | S2 | S3 | S5 | S6 | unchecked | no_failure |
|---|---|---|---|---|---|---|---|
| A | 0 | 0 | 5 | 5 | 0 | 0 | 40 |
| A2 | 0 | 0 | 6 | 4 | 0 | 0 | 40 |
| B | 0 | 0 | 0 | 5 | 0 | 0 | 45 |

B에서 S3 첫 실패가 사라졌고 S5는 5회다. B의 S5 5회는 모두 dev-05다(조정자가 2026-11-03에 `dev-B-r*.jsonl`을 `jq`로 직접 확인). 5회 모두 도구 호출이 `read_file`, `start_interview`, `record_answer`, `record_answer` 순서로 끝났고 `freeze_seed`는 부르지 않았다. 각 실행에서 H1 게이트는 에이전트가 보낸 완료 기준을 0.14~0.17로 채점했고(임계값 0.5 아래), Elicit으로 받은 스크립트 답이 `source` `elicited`로 기록되었다. 두 번째 `record_answer` 결과는 5회 모두 `status` `ready`, `missing_fields` 빈 목록이고 완료 기준 칸에 elicit된 답이 들어 있다. 즉 도구는 기록이 끝났다고 알렸다. 그런데도 에이전트는 5회 모두 마지막 글에서 확정을 보류했고, 저장된 완료 기준이 자신이 보낸 문장과 다르고 사용자가 말한 적 없는 조건이라는 이유를 들었다. Elicit의 답은 대화를 거치지 않고 서버로 바로 들어가므로(결과 1의 P3 읽기) 에이전트는 그 답을 사용자의 말로 볼 근거가 없다. 이것이 S5가 남은 원인이라는 것은 추정이다(원인을 가르는 실험은 하지 않았다). 따라서 B는 dev-05의 S3 실패를 없앴지만 S5(확정) 실패는 그대로 남았다. 다음 반복의 병목 후보로 적어 두는 관찰이며, P3·P5에 따라 결과를 본 뒤 게이트나 Skill을 고치지 않았다.

### 게이트 기록 (B, 줄 수는 줄 안의 낱말 포함 수)

- `gate_decisions`: h2 40, h1 20. `decision_unavailable` 0줄, `criteria_not_testable` 5줄, `goal_changed` 45줄.
- `goal_changed` 45는 그 낱말이 들어 있는 줄 수다. 게이트가 꺼진 holdout A와 A2에도 같은 낱말이 35줄 있어(결과 3) 게이트가 막은 횟수가 아니다. 이 줄 수를 게이트 발동 횟수로 읽지 않는다.

### P2 주의

B는 H1과 H2 게이트를 함께 켠다. 한 목표 지표의 변화를 한 게이트의 효과로 나눌 수 없고 두 게이트의 효과가 서로 섞였을 수 있다(P4의 한계). 이 절은 게이트별 효과를 말하지 않는다.

### 저자 확인 필요

1. 목표 사례가 2개뿐이라 하한이 0이 되는 구조다. 점추정 +0.5를 어떻게 말할지는 저자가 정한다. 이 문서는 규칙의 판정 낱말만 적었다.
2. 임계값 0.5는 라벨 미검토 상태다.

## 결과 3: holdout 최종 판정, 2026-11-03

PREREG 블록은 수정하지 않았다. holdout은 P4대로 한 번만 열었다(A, A2, B 각각 한 번, 8사례 x 5반복 = 40줄씩, 종료 코드 0). 수치는 `Day04_new/outputs/decisions/holdout-decision.json`과 `Day04_new/outputs/runs/holdout-*-r*.meta.json`이다. 사례는 id와 개수만 적는다. 설정은 dev와 같고(임계값 0.5, 미조정, `tuned` false) 15개 meta가 dev A와 같은 서버·SKILL.md sha256을 가진다. 오류 줄 0, 모든 meta의 `finished_at`이 채워짐.

### 목표별 최종 판정 (A 대 B, 잡음 폭은 A 대 A2)

| 목표 | 차이 [lo, hi] | n_cases | 잡음 폭 | 판정 | 이유(원문) |
|---|---|---|---|---|---|
| H1 vague_not_frozen | 0.5 [0.0, 1.0] | 2 | 0.0 | 개선 확인 불가 | 목표 지표 구간 하한 0.000이 0 이하라 개선을 확인할 수 없습니다. |
| H2 goal_preserved | 0.2 [0.2, 0.2] | 1 | 0.2 | 개선 | 목표 지표 구간 하한 0.200이 0보다 크고 가드 지표는 잡음 폭 안입니다. |

`guards_without_data`는 두 목표 모두 빈 목록이다(ho-07, ho-08이 `no_blind_retry`, `retry_bounded` 값을 주었다, 각 n_cases 1).

### 목표 사례별 통과/반복

| 사례 | A | A2 | B |
|---|---|---|---|
| ho-03 (H1) | 5/5 | 5/5 | 5/5 |
| ho-04 (H1) | 0/5 | 0/5 | 5/5 |
| ho-02 (H2) | 4/5 | 5/5 | 5/5 |

### 움직인 가드 (A 대 B)

- `frozen_ok`: +0.2 [0.0, 0.6], n_cases 5, 잡음 0.0.
- `model_calls`와 `tool_calls`: 각각 -0.45 [-0.975, -0.10], 잡음 0.25. `latency_s`: -0.89 [-2.46, 0.29], 잡음 1.09.
- H1 판정표의 가드로서 `goal_preserved`는 +0.2, n_cases 1, 잡음 0.2였다. 나머지 가드의 차이는 0이다.

### P3 병목 귀속 (40회 중)

| 변형 | S1 | S2 | S3 | S5 | S6 | unchecked | no_failure |
|---|---|---|---|---|---|---|---|
| A | 0 | 1 | 5 | 5 | 0 | 0 | 29 |
| A2 | 0 | 0 | 5 | 5 | 0 | 0 | 30 |
| B | 0 | 0 | 0 | 5 | 0 | 0 | 35 |

dev와 같은 모양이다. B에서 S3가 사라지고 S5는 5회로 그대로다. holdout의 S5 첫 실패는 A, A2, B 모두 ho-03 한 사례에서 5회씩이다. B의 ho-03 5회도 결과 2의 dev-05와 같이 `freeze_seed`를 부르지 않았고(1회는 마지막에 `get_session`을 더 불렀다), H1 게이트가 에이전트의 완료 기준을 0.05~0.06으로 채점한 뒤 elicit된 답이 `source` `elicited`로 기록되었으며, 두 번째 `record_answer` 결과는 5회 모두 `status` `ready`였다(조정자가 2026-11-03에 `jq`로 확인).

### 게이트 기록과 규모 (줄 수는 줄 안의 낱말 포함 수)

| 변형 | gate_decisions | goal_changed | criteria_not_testable | decision_unavailable | Claude 호출 | 입력 / 출력 토큰 | 벽시계(UTC 2026-11-02) |
|---|---|---|---|---|---|---|---|
| A | 없음 | 35 | 0 | 0 | 205 | 1,432,215 / 50,735 | 16:25:30-16:35:19 (9분 49초) |
| A2 | 없음 | 35 | 0 | 0 | 202 | 1,402,644 / 49,608 | 16:35:20-16:44:46 (9분 26초) |
| B | h1 25, h2 40 | 35 | 5 | 0 | 187 | 1,266,960 / 46,718 | 16:44:47-16:53:59 (9분 12초) |

합계: Claude 호출 594회, 입력 4,101,819 / 출력 147,061 토큰, 벽시계 28분 29초, Jev 하한 65회(h1 25, h2 40). `goal_changed`는 게이트가 꺼진 A, A2에도 35줄이라 게이트가 막은 횟수가 아니다.

### 최종 주장 (P4)

holdout 판정이 최종 주장이다. H1은 `개선 확인 불가`다. H2는 `개선`이다. 두 판정 모두 B가 H1·H2 게이트를 함께 켠 것이라 한 게이트의 효과로 나눌 수 없다(P2 주의). 임계값은 미조정이다.

### dev와 holdout 비교

H1은 두 분할에서 같은 판정(`개선 확인 불가`)이고 차이도 0.5 [0.0, 1.0]로 같다. 점추정은 각 분할에서 한 사례(dev-06, ho-04)가 0/5에서 5/5로 바뀐 데서 나오며, 목표 사례가 2개뿐이라 하한이 0이다. H2는 판정이 다르다. dev는 `개선 확인 불가`(차이 0.0, A에서 이미 100%)이고 holdout은 `개선`(차이 0.2 [0.2, 0.2])이다. P4에 따라 holdout이 최종 주장이지만 이 두 분할의 불일치를 함께 적는다.

### 저자 확인 필요

1. H2 `개선`은 사례 1개(ho-02)와 차이 0.2에 기대고 있다. 이 차이는 A 대 A2의 잡음 폭 0.2(A 4/5, A2 5/5)와 같다. `decide()` 규칙은 하한 0.2가 0보다 크고 가드가 잡음 폭 안이라 `개선`을 냈다. n_cases 1이라 구간이 한 점이다. 이것을 주장으로 쓸지는 저자가 정한다.
2. H1은 ho-04의 0/5에서 5/5 변화가 있어도 목표 사례가 2개라 판정이 `개선 확인 불가`다. 문구는 저자가 정한다.
3. 임계값 0.5는 라벨 미검토 상태다(미조정).


## 8. 비용

유료 실행은 각각 한 번만 하며 검증 중에는 하지 않는다. 사례당 Claude 호출은 약 5~9회다(`Day04/build_mcp/README.md:262`는 4 사례에 20~35회라고 적는다).

| 실행 | 규모 | Claude 호출 |
|---|---|---|
| 저자 dev | 10 사례 x 5 반복 x 3 변형 = 150회 | 약 750~1,350 |
| holdout | 8 x 5 x 3 = 120회 | 약 600~1,080 |
| 수업 | 4 x 3 x 3 = 36회 | 약 180~330 |
| Part 2, Part 5 각각 | 2 x 3 x 2 = 12회 | 약 60~110 |

Jev는 게이트당 실행마다 1~3회 호출한다.

실제 값(2026-11-02, 위 계획값은 그대로 둔다. `outputs/runs/*.jsonl`, `outputs/live*/summary.json`에서 다시 합산):

| 실행 | 실제 | 비고 |
|---|---|---|
| dev 기준선 A, A2 | 100회(50+50), 오류 0. Claude 호출 497(250+247), 입력 3,592,503 / 출력 146,573 토큰, Jev 0. 벽시계 A 15분 13초(913초) + A2 14분 37초(877초) = 29분 50초(1,790초) | 계획(변형 3개 150회, 750~1,350호출) 중 변형 2개분. 사례당 약 4.97호출로 계획 범위의 아래쪽 5~9보다 낮다 |
| 노트북 2차(수정 후) | Claude 123호출, 오류 0, 입력 811,755(캐시 읽기 722,137) / 출력 33,703 토큰. 커널 Jev 4회 + 서버 측 계량 1회(미계량 약 2회). 합산 벽시계 468.6초 | 00~07 실행. 07은 Langfuse 확인에서 설계대로 멈춤(Langfuse 기록 0). 예고는 Claude 약 290회였고 실제가 낮다 |
| 노트북 1차(수정 전) | Claude 39호출 중 실패 29, 성공 10. 토큰 입력 52,570 / 출력 2,245. 벽시계 150.4초 | 결함 (A), (B)로 낭비. 실패 호출이 과금되었는지는 확인하지 못했다(추정 불가) |
| 수정 노드의 실제 확인 | cache-fix: dev-01 skill 공개 3호출(16,962 / 956 토큰). loop-fix: dev-01 3호출(17,000 / 817), dev-02 1호출(3,495 / 1,204) | 호출 합 7, 토큰 입력 37,457 / 출력 2,977 |
| 루프 정리 실제 확인(2026-11-03) | 한 `asyncio.run` 안에서 `run_small_compare` 2번(dev-01, dev-02, 반복 1, 행 4개). 오류 0. Claude 8호출, 입력 40,944 / 출력 3,629 토큰, Jev 0 | 행 지연 시간 합 35.9초(벽시계가 아니라 `latency_s` 합). stderr 소음 0건 |
| dev B (게이트 켬) | 50회, 오류 0. Claude 226호출, 입력 1,586,157 / 출력 68,939 토큰. Jev 하한 60(h1 20 + h2 40, `gate_decisions` 기록). 벽시계 13분 52초 | 계획(사례 10 x 5 x 변형 1)의 한 변형분. 사례당 약 4.52호출 |
| holdout A, A2, B | 120회(40 x 3), 오류 0. Claude 594호출(205 + 202 + 187), 입력 4,101,819 / 출력 147,061 토큰. Jev 하한 65(h1 25 + h2 40). 벽시계 9분 49초 + 9분 26초 + 9분 12초 = 28분 27초 | 변형별 기록은 결과 3. 세 변형의 시작과 끝 시각 차이는 28분 29초이고 합 28분 27초와 2초 다른 것은 변형 사이 대기다 |

기준선까지 합한 Claude 호출 계측 합계: 497 + 123 + 39 + 7 = 666(`outputs/live*`의 계측은 호출 시작 수이며 1차의 실패 29 포함). 예고한 범위(Claude 약 790~1,190)보다 낮다. 캐시 쓰기 토큰은 계측하지 않았고, 서버 측 Jev 약 2회는 계량하지 못했다.

3c 단독 계측 합계(2026-11-03): Claude 8(루프 정리 실제 확인) + 226(dev B) + 594(holdout) = 828호출. 3c 시작 전에 예고한 범위(Claude 약 860~1,550, Jev 약 180~540)와 비교하면 Claude 828회는 예고 하한보다 적다. Jev는 3c의 게이트 기록으로 센 하한이 60 + 65 = 125회로 예고 하한보다 적다. 게이트 한 번의 Jev 호출 수(1~3회)가 기록에 없어 실제 Jev 호출은 이보다 많을 수 있고, 그래서 Jev가 예고 범위 안이었는지는 알 수 없다: 저자 확인 필요. 기준선까지 합한 누적 계측 합계는 666 + 828 = 1,494호출이다. 07 노트북의 수업 측정(예고 Claude 324회, Jev 72회)은 측정하지 않았다.

## 9. 외부 전송

Langfuse는 프롬프트와 도구 입출력을 받는다. Decision API는 답변과 goal 텍스트를 받는다.

## 10. 진행 단계

1. run 1 기반: 환경, 이 문서, `cap_lab`, 오프라인 테스트.
2. run 2 노트북과 문서.
3. 저자 라벨 검토 관문. 저자 측정은 Langfuse 없이 로컬로 돌리므로 키 교체는 run 3의 선행 조건이 아니다(개정 2). 키 교체는 07의 Langfuse 기록에만 필요하다.
4. run 3 유료 측정. 결과 절은 PREREG 블록 뒤에 덧붙이고 블록 자체는 수정하지 않는다. 완료(2026-11-03): dev 기준선과 dev B(결과 1, 결과 2), holdout A, A2, B(결과 3). 07 노트북의 수업 측정(Langfuse 기록, Claude 324회, Jev 72회 예고)은 아직 측정하지 않았다.

## 11. 출처

- https://modelcontextprotocol.io/specification/2026-07-28/changelog
- https://docs.langchain.com/oss/python/langgraph/changelog-py
- https://docs.langchain.com/oss/python/deepagents/tools
