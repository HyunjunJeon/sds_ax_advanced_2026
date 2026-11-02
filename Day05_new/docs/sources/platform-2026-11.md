# 플랫폼 실측 노트 (2026-11-02)

Day05_new 설계가 전제로 삼는 도구 사실을 모은다. 두 종류로 나눈다.

- **설치본 실측**: 저장소 루트 `.venv`에 설치된 패키지를 직접 읽어 확인했다. 키와 네트워크 없이 확인했다. 경로의 `site-packages/`는 `.venv/lib/python3.13/site-packages/`를 줄인 것이다.
- **웹 확인**: 공급자 문서에서 읽었다. 날짜와 URL을 붙인다. 서버 쪽 동작이라 이 저장소에서 재현하지 않았다.

이 노트에 없는 사실을 노트북에 쓰지 않는다. `미확인` 표시가 붙은 행은 사실처럼 쓰지 않는다.

## 1. 고정된 버전

| 패키지 | 버전 | 근거 |
|---|---|---|
| langfuse | 4.15.1 | `uv.lock` (`name = "langfuse"`) |
| deepeval | 4.2.2 | `site-packages/deepeval/_version.py:1` |
| langchain-anthropic | 1.7.7 | `uv.lock` |
| langchain | 1.4.7 | `uv.lock` |
| langgraph | 1.2.19 | `uv.lock` |
| opentelemetry-sdk / semconv | 1.45.2 / 0.66b2 | `uv.lock`, `site-packages/opentelemetry_semantic_conventions-0.66b2.dist-info` |

루트 `pyproject.toml`의 `exclude-newer = "2026-10-31T00:00:00Z"` 때문에 새 패키지를 더하지 않는다. 아래 기능은 모두 이미 설치되어 있다.

## 2. Langfuse

### 2.1 설치본 실측 (SDK 4.15.1)

| 기능 | 위치 | Day05_new에서 쓰는 곳 |
|---|---|---|
| `run_experiment(name, run_name, task, evaluators, run_evaluators, max_concurrency, metadata)` | `site-packages/langfuse/_client/client.py:2613`, `site-packages/langfuse/_client/datasets.py:81` | 02 오프라인 실험 |
| `create_score(trace_id, observation_id, name, value, data_type, comment)` | `site-packages/langfuse/_client/client.py:1913` | 03a, 05, 06 — 점수를 observation에 붙인다 |
| `run_batched_evaluation(scope="traces"\|"observations", mapper, filter, max_items, evaluators, composite_evaluator, max_concurrency, resume_from)` | `site-packages/langfuse/_client/client.py:3256` | 03a 온라인 평가 주 경로, 05 새 평가기 backtest |
| 일괄 평가 모듈 설명: 배포 후 운영 trace 평가, 과거 데이터로 새 지표 backtest, 주기적 평가 | `site-packages/langfuse/batch_evaluation.py:1` | 03a 설명 |
| `propagate_attributes(user_id, session_id, metadata, version, tags, trace_name, environment, prompt)` | `site-packages/langfuse/_client/propagation.py:114` | 03a·04 — release·환경·세션 태그 |
| Metrics API v2 `metrics(query=...)`. view는 `observations`, `scores-numeric`, `scores-boolean`, `scores-categorical`이고 **traces view는 지원하지 않는다**. `isRootObservation` 차원이 있다. 측정값: count, latency, inputTokens/outputTokens/totalTokens, totalCost, timeToFirstToken, countScores | `site-packages/langfuse/api/metrics/client.py:26` | 04 모니터링 |
| Evaluation Rule `create(name, enabled, evaluator_assignments, sampling, filter)`. Rule은 **어떤** observation을 평가할지 정한다. `sampling`을 빼면 전부 평가한다 | `site-packages/langfuse/api/evaluation_rules/client.py:35` | 03a (선택 경로) |
| Evaluator `create`, `list_versions` | `site-packages/langfuse/api/evaluators/client.py:34`, `:270` | 03a (선택 경로) |
| Annotation queue `create_queue`, `create_queue_item`, `create_queue_assignment` | `site-packages/langfuse/api/annotation_queues/client.py:87`, `:282`, `:438` | 05 사람 검수 |
| LLM Connection `upsert` (서버 쪽 Judge가 쓸 모델 키 등록) | `site-packages/langfuse/api/llm_connections/client.py:76` | 03a — 수강생 키를 Langfuse에 등록해야 하므로 선택 경로로 둔다 |

### 2.2 웹 확인

| 사실 | 출처 |
|---|---|
| 2026-08-22: Evaluator(어떻게 채점)와 Rule(무엇을 채점)이 분리되었다. 저장 전에 실제 observation으로 Evaluator를 시험하고, 최근 7일 매칭량과 예상 비용을 본 뒤 샘플링을 정한다 | https://langfuse.com/changelog/2026-08-22-reusable-evaluators-and-rules |
| trace-level evaluator는 v4에서 deprecated. **Langfuse Cloud에서는 2026-11-16 v4 전환 시점에 결과 생성을 멈춘다.** observation-level evaluator는 매칭되는 observation마다 점수를 만들고 기본 필터는 `isRootObservation = true`다 | https://langfuse.com/faq/all/llm-as-a-judge-migration |
| 전환 요구: Python SDK ≥ 4.7.0(설치본 4.15.1이라 충족). SDK를 올린 뒤에는 trace input/output이 자동 기록되지 않는다. `set_current_trace_io()`, `span.set_trace_io()`는 Python SDK v5에서 제거되고 값은 root observation에서 온다 | 같은 FAQ |
| 2026-10-22: 예약 내보내기(S3, GCS, Azure)에 점수의 출처(annotation queue, 설정, evaluator ID)를 담을 수 있다 | https://langfuse.com/changelog/2026-10-22-blob-storage-score-field-groups |
| annotation queue는 trace, session, observation을 담고 API로 관리한다 | https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues |

### 2.3 기존 Day05 코드와의 관계

- `Day05/` 코드에는 `set_current_trace_io`, `set_trace_io`, `update_current_trace` 호출이 없다(grep 0건). 전환의 직접 영향은 없다.
- 기존 `Day05/business_lab/langfuse_adapter.py`는 `run_experiment`와 `create_score(observation_id=...)`를 쓴다. 이미 observation 단위로 점수를 붙이는 구조다.
- 영향을 받는 것은 자료다. `Day05/Day5_이론자료.pdf` p47의 "Langfuse Judge 변수 매핑"은 trace 단위 Judge 설정을 전제로 한다. Day05_new는 이 절을 observation-level Rule과 Evaluator로 다시 쓴다.

## 3. DeepEval 4.2.2

### 3.1 에이전트 지표 (설치본 실측)

| 지표 | 필요한 입력 | 모델 사용 | 위치 |
|---|---|---|---|
| `ToolCorrectnessMetric` | INPUT, TOOLS_CALLED, EXPECTED_TOOLS | 기본은 비교, 모델 초기화 있음 | `site-packages/deepeval/metrics/tool_correctness/tool_correctness.py:30`, `:55` |
| `ArgumentCorrectnessMetric` | INPUT, TOOLS_CALLED | LLM | `site-packages/deepeval/metrics/argument_correctness/argument_correctness.py:31` |
| `ToolPermissionMetric(allowed_tools, denied_tools)` | TOOLS_CALLED | **결정적, 모델 없음** | `site-packages/deepeval/metrics/tool_permission/tool_permission.py:34`, `:60` |
| `TaskCompletionMetric` | INPUT, ACTUAL_OUTPUT + **trace 필요** | LLM | `site-packages/deepeval/metrics/task_completion/task_completion.py:64` |
| `StepEfficiencyMetric` | INPUT, ACTUAL_OUTPUT + trace 필요 | LLM | `site-packages/deepeval/metrics/step_efficiency/step_efficiency.py:50` |
| `PlanAdherenceMetric` | INPUT, ACTUAL_OUTPUT + trace 필요 | LLM | `site-packages/deepeval/metrics/plan_adherence/plan_adherence.py:58` |
| `AgentLoopDetectionMetric` | INPUT, ACTUAL_OUTPUT + trace 필요 | LLM | `site-packages/deepeval/metrics/agent_loop_detection/agent_loop_detection.py:147` |
| 그 밖에 `GoalAccuracyMetric`(대화형), `PlanQualityMetric`, `MCPUseMetric`, `DAGMetric` | — | — | `site-packages/deepeval/metrics/` |

- trace가 필요한 지표는 `test_case._trace_dict`를 읽는다(`site-packages/deepeval/test_case/llm_test_case.py:435`, `site-packages/deepeval/metrics/step_efficiency/step_efficiency.py:156`). 이 필드는 `PrivateAttr`라 공개 계약이 아니다. DeepEval 자체 tracing(`@observe`) 없이 우리 원자료로 채우는 경로는 **구현 단계에서 fake 모델로 확인해야 한다(미확인)**.
- 기존 `Day05/`는 `GEval`(`Day05/business_lab/evaluators.py` 쪽)과 `FaithfulnessMetric`(`Day05/gold_agent_eval.py`)만 쓴다.

### 3.2 Judge 모델 연결

- DeepEval 내장 `AnthropicModel`(`site-packages/deepeval/models/llms/anthropic_model.py:41`)은 thinking budget 방식이다(`:127`~`:150`). Sonnet 5.5는 `budget_tokens` 대신 `output_config.effort`를 쓰므로(`site-packages/langchain_anthropic/chat_models.py:1484` 주석) 이 클래스로는 effort `xhigh`를 지정할 수 없다.
- 그래서 기존 `Day05/business_lab/models.py`처럼 `DeepEvalBaseLLM`을 상속한 어댑터를 만들고 안에서 `ChatAnthropic(reasoning_effort="xhigh")`를 부른다. 추상 메서드는 `load_model`, `generate`, `a_generate`, `get_model_name`이다(`site-packages/deepeval/models/base_model.py:84`, `:93`).

## 4. Anthropic 모델 (langchain-anthropic 1.7.7)

| 사실 | 근거 |
|---|---|
| `reasoning_effort: Literal["max", "xhigh", "high", "medium", "low"]`, 별칭 `effort`. `output_config.effort`로 전달된다 | `site-packages/langchain_anthropic/chat_models.py:1523` |
| `claude-sonnet-5-5` 프로필: `reasoning_effort_levels = [low, medium, high, xhigh, max]`, `temperature = False`, `tool_choice = False`, `structured_output = True`, 출시일 2026-09-28 | `ChatAnthropic(model="claude-sonnet-5-5").profile` 출력 (키 없이 생성만) |
| Day04_new는 `reasoning_effort`만 보내고 temperature와 thinking은 보내지 않는다. `max_retries=0`으로 SDK 재시도를 호출 수에 드러낸다 | `Day04_new/cap_lab/settings.py` `make_model` |

**미확인**: 기존 `Day05` 에이전트는 `create_agent(..., response_format=ToolStrategy(Response))`를 쓴다(`Day05/business_lab/agents.py:146`). 프로필의 `tool_choice = False`가 ToolStrategy의 구조화 응답에 영향을 주는지는 실제 호출 없이 확인할 수 없다. 첫 유료 smoke에서 확인할 항목으로 남긴다.

## 5. Jev (Decision API)

- Day04_new의 사본 `Day04_new/cap_lab/decisions.py`를 다시 고쳐 쓴다(바이트 동일 사본이 아님). 질문 형식은 `Noul`(`:26`), `Choice`, `Score`이고 답은 `Verdict`(`:57`)의 `probability`, `confidence`, `refused`다.
- 공급자는 `make_decider`(`:183`)가 TYPESAFE, OPENROUTER, OPENAI, AZURE 순으로 키가 있는 첫 번째를 고른다. Claude로 대신하는 경로는 없다.
- 확률은 보정(calibration)을 가정하지 않는다(`Day04_new/cap_lab/decisions.py:6`). 문턱값은 사람 라벨로 재서 정한다.
- 질문 문장과 근거(state)는 공급자에게 그대로 전송된다.

## 6. OpenTelemetry GenAI semantic conventions

| 사실 | 근거 |
|---|---|
| 연산 이름에 `create_agent`, `invoke_agent`, `execute_tool`, `invoke_workflow`가 있다 | `site-packages/opentelemetry/semconv/_incubating/attributes/gen_ai_attributes.py:335`~`:351` |
| 평가 결과 속성 `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value`, `gen_ai.evaluation.score.label`, `gen_ai.evaluation.explanation` | 같은 파일 `:49`~`:64` |
| 설치본 0.66b2는 `gen_ai.*` 속성을 "OpenTelemetry GenAI semantic conventions 저장소(`open-telemetry/semantic-conventions-genai`)로 이동"했다고 표시한다(같은 문구 65곳) | 같은 파일 `:9`~`:11`, `:99`~`:101` |
| **안정화 여부는 미확인**. 2026-05·2026-08 2차 자료는 Development 상태라 하고, 2026-06 2차 자료 하나는 안정화를 주장한다. 1차 출처로 확인하지 못했다 | https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions, https://www.truefoundry.com/blog/opentelemetry-genai-semantic-conventions, https://businesstechnavigator.com/news/opentelemetry-genai-semantic-conventions-agents-2026 |

노트북은 "표준 이름이 있다. 저장소가 분리되었다. 안정화 여부는 확인 필요"까지만 쓴다.

## 7. 이식할 기존 Day05 자산

| 자산 | 위치 | 비고 |
|---|---|---|
| 업무 환경(SQLite, 장애 주입) | `Day05/business_lab/environment.py:22`, 쓰기 도구 `:17`, 도구 한도 `:19` | 그대로 이식 |
| 여러 턴 Episode | `Day05/business_lab/episodes.py:12` | 그대로 |
| Scenario·Artifact·Verdict 계약 | `Day05/business_lab/contracts.py:54`, `:104`, `:129` | 판정 상태를 늘린다(03b) |
| 업무 평가기 | `Day05/business_lab/evaluators.py:39`~`:203` | 그대로, 궤적 규칙은 새 모듈 |
| 반복·회귀 집계(pass@k, pass^k, bootstrap) | `Day05/business_lab/reporting.py:38`, `:81`~`:83`, `:103` | 그대로 |
| 사람 라벨 보정(family 분할) | `Day05/business_lab/evidence.py:131` | Jev·Judge 두 단계로 넓힌다 |
| 회귀 초안 승격 | `Day05/business_lab/evidence.py:157` | 05에서 사용 |
| 반례 검사 | `Day05/business_lab/counterexamples.py:12` | 03b 평가기 평가의 씨앗 |
| 사례 11개(dev 9, holdout 2), fixture 11개 | `Day05/business_lab/data/scenarios.json`, `fixtures.json` | 모의 운영 트래픽의 바탕 |
| 에이전트(LangChain `create_agent`, OpenRouter) | `Day05/business_lab/agents.py:146` | `ChatAnthropic`으로 바꾼다 |
