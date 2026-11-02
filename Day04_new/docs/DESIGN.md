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
- deepagents `SkillToolResolver`는 `.venv/lib/python3.13/site-packages/deepagents/middleware/skills.py:176`, description 길이 한도 1024는 `skills.py:173`.
- `FilesystemPermission`의 deny는 `deepagents/middleware/filesystem.py:382`.
- ToolAnnotations 필드는 `mcp_types/_v2026_07_28/__init__.py:1091-1118`.
- traceparent 도우미는 `mcp/shared/_otel.py:39`, `fastmcp/telemetry.py:152`.
- MCP 2026-07-28 변경: stateless(initialize 제거, 요청마다 `_meta`에 프로토콜 버전과 capabilities, SEP-2575), server/discover, Mcp-Session-Id 제거와 도구 인자로 쓰는 서버 발급 핸들(SEP-2567), MRTR `InputRequiredResult`가 서버 주도 elicitation/sampling/roots를 대체(SEP-2322), tasks는 확장으로 이동(SEP-2663), subscriptions/listen, ttlMs/cacheScope(SEP-2549), tools/list 순서 결정적, 스키마는 JSON Schema 2020-12(SEP-2106), Roots/Sampling/Logging 폐기 예정(SEP-2577), DCR은 Client ID Metadata Documents로 대체 예정.
- 실행 스모크(env-smoke, `Day04_new/.env`): Claude ok, Jev ok(`POST https://api.typesafe.ai/v1/systemone`, `noul` 질문, 확률은 `answers.judgeable.noul`). traceparent는 MCP 요청 `_meta`로 도착하고 Langfuse trace id와 일치한다(`traceparent_received` true, `traceparent_matches_langfuse` true). Langfuse 인증은 복사한 키로 실패했다(`langfuse_auth: fail: UnauthorizedError`, 401). `mcp_protocol_version`은 `unknown`으로 남았다.
- 기존 Day04 실행 기록으로는 병목을 찾을 수 없다. 검증 보고서가 4건뿐이고 2026-10-31 보고서는 1.91초 만에 ExceptionGroup(인프라)으로 실패했다. 병목은 새로 측정해야 한다.

## 6. 미확인

- MRTR과 `include_tools` 아래의 실제 모델 행동
- Streamable HTTP 실행
- tasks 확장
- agentskills.io 2026 명세에서 1024자 한도 외의 변경
- 유효한 키로 한 Langfuse 인증, 그리고 서버 쪽 span이 실제로 Langfuse에 내보내지는지

Langfuse 인증: 복사한 키가 401이므로 저자가 키를 교체한다. 교체한 키로 Langfuse 인증 확인(`auth_check`가 True)이 통과하는 것이 run 3의 모든 유료 측정의 선행 조건이다.

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

- Langfuse 데이터셋 `day04_new-capability-v1`을 `Day04_new/data/cases.jsonl`에서 만든다(dev 10, holdout 6; metadata는 split, stage, kind).
- holdout은 최종 주장을 위해 한 번만 연다.
- 임계값은 저자가 검토한 뒤의 `Day04_new/data/gate_labels_draft.jsonl` dev 라벨로만 조정한다. 초기 임계값 0.5는 자리표시자이며 미조정으로 표시한다.
- 사례마다 사용자 발화와 elicitation 응답은 스크립트로 정해 둔다. LLM이 사용자를 흉내 내지 않는다.
- 변형: A(게이트 끔), A2(게이트 끔, A/A용 반복), B(H1과 H2 켬). 두 게이트는 서로 다른 단계를 겨냥하므로 목표 지표를 각각 따로 읽고, 상호작용 가능성은 주의사항으로 적는다.
- 반복 횟수: 저자 실행 N=5, 수업 N=3.
- 각 실행의 metadata에 모델, effort, SKILL.md sha256, 서버 코드 sha256, 게이트 플래그, 임계값, Jev 모델 id, 데이터셋 버전을 고정해 기록한다.
- 로컬 사본 `Day04_new/outputs/runs/*.jsonl`은 오류를 포함한 모든 항목을 남긴다.
- 모든 유료 실행 전에 Langfuse 인증 확인이 통과해야 한다.

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

## 8. 비용

유료 실행은 각각 한 번만 하며 검증 중에는 하지 않는다. 사례당 Claude 호출은 약 5~9회다(`Day04/build_mcp/README.md:262`는 4 사례에 20~35회라고 적는다).

| 실행 | 규모 | Claude 호출 |
|---|---|---|
| 저자 dev | 10 사례 x 5 반복 x 3 변형 = 150회 | 약 750~1,350 |
| holdout | 6 x 5 x 2 = 60회 | 약 300~540 |
| 수업 | 4 x 3 x 3 = 36회 | 약 180~330 |
| Part 2, Part 5 각각 | 2 x 3 x 2 = 12회 | 약 60~110 |

Jev는 게이트당 실행마다 1~3회 호출한다.

## 9. 외부 전송

Langfuse는 프롬프트와 도구 입출력을 받는다. Decision API는 답변과 goal 텍스트를 받는다.

## 10. 진행 단계

1. run 1 기반: 환경, 이 문서, `cap_lab`, 오프라인 테스트.
2. run 2 노트북과 문서.
3. 저자 라벨 검토 관문과 Langfuse 키 교체.
4. run 3 유료 측정. 결과 절은 PREREG 블록 뒤에 덧붙이고 블록 자체는 수정하지 않는다.

## 11. 출처

- https://modelcontextprotocol.io/specification/2026-07-28/changelog
- https://docs.langchain.com/oss/python/langgraph/changelog-py
- https://docs.langchain.com/oss/python/deepagents/tools
