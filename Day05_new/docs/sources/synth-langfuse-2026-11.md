# 합성 Langfuse Trace 생성기 근거 노트 (2026-11-05)

합성 Trace 생성기를 만들기 전에 서버 동작, 공식 문서, 저자의 실제 DeepSeek 실행 분포를 모은다. 세 종류다.

- **서버 탐침**: 저자의 Langfuse Cloud(JP) 프로젝트에 backdated OTLP trace 2개를 보내 읽었다(2026-11-05). 출처는 `Day05_new/outputs/synth-probe/probe-otlp-notes.md`(이하 probe 노트).
- **분포 보정**: 저자의 실제 실행 기록을 읽기만 했다(모델·Jev·Judge 호출 0회). 출처는 `Day05_new/outputs/synth-probe/calibrate-live-notes.md`(이하 calibrate 노트)와 전체 live Episode 재보정 `Day05_new/outputs/synth-probe/calibrate-all-notes.md`(calibrate-all 노트)다. 처음 보정은 최근 10개 trace만 썼다.
- **웹 확인**: 공식 문서(접근일 2026-11-05). 출처는 `Day05_new/outputs/synth-probe/research-docs-notes.md`(이하 research 노트).

이 노트에 없는 사실을 생성기에 쓰지 않는다. `미확인` 표시가 붙은 행은 사실처럼 쓰지 않는다. 모든 숫자는 저자의 **1회 관찰**이며 성능 주장도, 통계도 아니다.

## 1. 목적

m3a, m4, m5 미션은 며칠에 걸친 운영 기록이 필요하지만, 지금의 scripted 트래픽은 몇 초 안에 만들어지고 토큰과 비용이 0이며(`Day05_new/eval_lab/episodes.py:121`의 `usage.update(input_tokens=0, output_tokens=0, cost_usd=0.0)`), 지연은 이 컴퓨터에서 scripted 실행에 걸린 ms 단위 값이라 모델 지연을 말할 수 없고(`Day05_new/use_cc/concepts/m4.md:185-186`), generation observation이 없다. 그래서 실제 실행 분포에 맞춘 7일치 backdated 합성 Trace를 공용 배경 운영 기록으로 두고, 수강생이 스크립트로 각자의 Langfuse 프로젝트에 적재한다(모델 호출 0회). 합성 데이터는 06의 replay pool, holdout, PREREG P3 측정, 03b meta-evaluation에 쓰지 않는다.

## 2. 서버 사실 (Langfuse Cloud JP, 2026-11-05 탐침)

모두 Episode 2개(A 6 observations 합계 7행 읽힘, B)를 보낸 **1회 관찰**이다.

| # | 사실 | 증거 | 출처 |
|---|---|---|---|
| Q1 | 과거 시각이 그대로 저장된다. 루트 start_time이 보낸 값(now-7d)과 같고 차이 0 ms, 거부·보정 없음(HTTP 200). `from_start_time` 없이 읽어도 D-7 루트가 나온다. 기본 시간 창의 상한은 확인하지 않았다 | startTime A=2026-10-29T10:59:13.000Z, B=2026-11-04T10:59:19.000Z, count(no from_start_time)=7 | probe 노트 Q1 |
| Q2 | 같은 trace·span id 재전송은 upsert로 수렴한다. 재전송 약 17초 뒤 약 17~32초 구간에 13건(중복)으로 보였다가 약 49초 뒤 7건, 12분 뒤에도 7건·루트 2개. 수렴 뒤 createdAt이 재전송 시각으로 바뀐다 | count=7 after settle (13 transient), Metrics root count=2 | probe 노트 Q2 |
| Q3 | 루트 output에 `episode_summary(artifact)`(schema day05-episode-summary-v1)를 JSON 문자열로 보내면 `fields="core,basic,io"`로 읽어 `artifact_from_root_observation`이 복원하고 `evaluate_trajectory`가 로컬과 같다(PASS, 치명 Rule 없음). 단 PASS 항목이라 Rule id 일치는 빈 목록끼리의 비교다 | rebuilt=True, remote=[PASS,[]] local=[PASS,[]] | probe 노트 Q3 |
| Q4 | 유형·level·status message가 보존된다(generation->GENERATION, check_cancel_policy->TOOL, **get_order->SPAN**, refund_payment level=ERROR statusMessage=TIMEOUT, turn-1/episode->AGENT). usage는 입력 1200·출력 150·total 1350(Langfuse가 합산). 비용은 보낸 값 유지(total 0.00027 합산), internalModelId 빈 값(가격 매칭 없음). 설치 SDK 4.15.1 v2 타입의 `providedModelName`은 항상 None(실제 SDK generation도 None)이고 모델명은 원 JSON의 `model` 키에 있다(`with_raw_response` 또는 필터 column). environment·version·sessionId·userId·tags·metadata는 루트에서만 나오고 자식은 environment만 갖는다(전파 없음). metadata에 resourceAttributes.*, attributes.* 원시 속성이 함께 들어온다 | usageDetails, costDetails.total=0.00027, raw model=synthetic/deepseek-v4.1-flash-ultrafast | probe 노트 Q4 |
| Q5 | Metrics v2(view observations)가 보낸 값과 같다: root 필터+environment count=2, environment만 count=7, sum totalCost=0.00027, inputTokens=1200, outputTokens=150(재전송 수렴 뒤) | metrics count_count=2 / 7 | probe 노트 Q5 |
| Q6 | 시작 시각이 ms 단위로 보존되고, API 기본 정렬은 start_time 내림차순이다. 뒤섞어 보내도 start_time 오름차순 정렬로 단계 순서가 된다 | order desc=refund 14.400, check 14.100, get_order 13.700, generation 13.100, turn-1 13.010, episode 13.000 | probe 노트 Q6 |
| Q7 | 첫 읽기(A 전송 38.7초 뒤)에 이미 7건이 보였다(상한 38.7초). 재전송 갱신은 17.4초 뒤 읽기에서 보였고 약 49초에 수렴. 0건 상태는 관찰하지 못했다 | first_seen_after_send<=38.7s, resend_visible_after=17.4s | probe 노트 Q7 |

### 탐침의 OTLP exporter 설정 (probe 노트 Exporter setup)

- endpoint 경로: `/api/public/otel/v1/traces` (base는 `LANGFUSE_HOST`), span 하나당 HTTP 1회(SimpleSpanProcessor).
- 인증: HTTP Basic(공개키:비밀키 base64). header 이름: `Authorization`, `x-langfuse-ingestion-version`(값 4). SDK가 보내는 `x-langfuse-sdk-name`, `x-langfuse-sdk-version`, `x-langfuse-public-key`는 탐침이 보내지 않아도 200이었다.
- 속성 키: `langfuse.observation.type`, `.input`, `.output`(JSON 문자열), `.level`, `.status_message`, `.model.name`, `.usage_details`(JSON), `.cost_details`(JSON), `langfuse.environment`, `langfuse.version`, `session.id`, `user.id`, `langfuse.trace.tags`(문자열 목록), `langfuse.trace.metadata.<key>`, `langfuse.observation.metadata.<key>`.
- 시간: OTel start_time/end_time(ns, ms 정밀도). id는 결정적(trace=sha256 앞 32자리, span=sha256 앞 16자리).

## 3. 문서 사실 (공식 문서, 2026-11-05 접근)

| # | 사실 | URL |
|---|---|---|
| R1 | **확인 필요.** 내장 "Agent Dashboard"와 위젯 필터를 설명하는 페이지를 찾지 못했다(`/docs/metrics/features/agent-dashboard`는 404, custom-dashboards 문서는 Latency·Cost·Usage만 나열). 2025-12 tool-call 기능은 dashboard 지표 `toolCalls`·`toolDefinitions`와 필터 `toolNames`를 더하지만, 이것이 generation output의 `tool_calls`에서 오는지 type `tool` observation에서 오는지 문서가 말하지 않는다. type `span`인 `service.<tool>`이 세어지는지는 미확인 | https://langfuse.com/changelog/2025-12-22-tool-calls-filtering-visualization ; https://langfuse.com/docs/metrics/features/custom-dashboards ; https://langfuse.com/changelog/2025-11-05-langfuse-for-agents |
| R2 | Hobby는 월 50k units(trace, observation, score가 각 1 unit이고 LLM-as-a-Judge·annotation queue·experiment가 만든 항목도 센다). 데이터 접근 30일, 보존 관리는 Hobby에서 불가. 한도 초과 시 차단인지 제한인지는 문서에 없다(확인 필요) | https://langfuse.com/pricing ; https://langfuse.com/docs/administration/billable-units |
| R3 | **확인 필요.** 과거·미래 timestamp 한도는 문서에 없다. start/end 한쪽이 없으면 다른 쪽을 복사하고 둘 다 없으면 ingest 시각이다(둘 다 보내길 권장). backdated 데이터가 dashboard·Metrics API에서 어떻게 보이는지는 문서에 없다. Hobby 데이터 접근이 30일이라 7일 창 안에 둔다 | https://langfuse.com/integrations/native/opentelemetry ; https://langfuse.com/integrations/native/opentelemetry/migration-to-v4 ; https://langfuse.com/pricing |
| R4 | 문서는 span ID를 다시 export하지 말라고 한다(중복 observation, metrics 부풀림, 조회 불일치 위험; legacy REST와 OTEL에 같은 id를 이중 전송 금지). 서버 dedup 동작은 코드를 읽지 않았다. **Q2 탐침과 충돌한다(아래 참고)** | https://langfuse.com/integrations/native/opentelemetry/migration-to-v4 |
| R5 | 보낸 `cost_details`가 우선이고, 없을 때만 model 정의의 단가 x usage로 ingestion 시 추론한다. 모델명은 정의별 regex `match_pattern`으로 매칭하고 사용자 정의 모델이 우선이다. `default-model-prices.json`은 266,154자 중 앞 100,000자만 읽었고 그 안에 deepseek·synthetic 패턴은 없었다(나머지 미확인). 가장 안전한 방법은 `cost_details` 명시 또는 사용자 정의 모델(예: `(?i)^synthetic/deepseek-v4\.1-flash-ultrafast$`) | https://langfuse.com/docs/model-usage-and-cost ; https://raw.githubusercontent.com/langfuse/langfuse/main/worker/src/constants/default-model-prices.json |
| R6 | 2026-11-16 Cloud는 v4 전용이 되어 legacy ingestion 엔드포인트와 deprecated 읽기 API가 사라진다(`/v2/observations`, `/v3/scores`, `/v2/metrics` 사용). `/api/public/otel/v1/traces`는 v3·v4 모두 동작한다. `x-langfuse-ingestion-version: 4`가 실시간 가시성을 주고, 없으면 10~15분 지연될 수 있다(페이지마다 다름). 이 header가 전환일에 필수가 되는지는 문서에 없다. trace-level input/output은 deprecated라 루트 span의 `langfuse.observation.input/output`에 넣는다. trace 전체 속성은 루트에서 상속되지 않으므로 모든 span에 복사한다. `langfuse.observation.type`의 허용값은 span, generation, event, embedding, agent, tool, chain, retriever, guardrail, evaluator이며 인식 못 하는 값은 거부 없이 바뀐다 | https://langfuse.com/docs/compatibility ; https://langfuse.com/integrations/native/opentelemetry ; https://langfuse.com/integrations/native/opentelemetry/migration-to-v4 ; https://langfuse.com/faq/all/upgrade-to-langfuse-v4 |

**Q2와 R4는 서로 다르다.** 탐침은 upsert 수렴(일시 중복 후)을 관찰했고(1회 관찰) 문서는 중복 위험을 경고한다. 둘 다 적는다. 재적재의 안전성은 미확인으로 두고 생성기는 빈 프로젝트에 한 번 적재하는 쪽을 기본으로 한다(결정 D2).

## 4. 분포 보정 (저자 DeepSeek 실제 실행, 1회 관찰)

모든 숫자는 1회 관찰이며 성능 주장이 아니다. 로컬 usage.jsonl 행의 출처는 calibrate 노트, Langfuse 행의 출처는 `Day05_new/outputs/synth-probe/calibrate-all-notes.md`(이하 calibrate-all 노트)이며 표본 크기(n)를 함께 적는다. 구간은 부트스트랩 2,000회 95%이고, n은 Episode별 행은 Episode 수, generation·service 행은 관측 수다. 처음 보정은 가장 최근 live trace 10개만 썼고 이 표는 그 값을 전체 live Episode 56개로 대체한 것이다.

| 항목 | 출처 | n | median | p90 | min | max |
|---|---|---|---|---|---|---|
| agent input tokens | local usage.jsonl | 87 | 265 | 363 | 133 | 1567 |
| agent output tokens | local usage.jsonl | 87 | 68 | 197 | 41 | 435 |
| agent cache_read tokens | local usage.jsonl | 87 | 1536 | 2048 | 0 | 2304 |
| generation latency ms (바깥 ChatAnthropic) | Langfuse live (56 Episodes, 95% 구간: median 243-291, p90 524-585) | 318 | 276 | 567 | 159 | 1315 |
| generation latency ms (안쪽 anthropic.messages.create) | Langfuse live (이전 10 traces, 재계산하지 않음) | 50 | 286 | 552 | 159 | 921 |
| generation input tokens (Langfuse 교차 확인) | Langfuse live (56 Episodes, 95% 구간: median 264-275, p90 345-372) | 318 | 268 | 358 | 130 | 1567 |
| generation output tokens (Langfuse 교차 확인) | Langfuse live (56 Episodes, 95% 구간: median 60-74, p90 179-207) | 318 | 60 | 197 | 41 | 476 |
| service span latency ms | Langfuse live (56 Episodes, 95% 구간: median 0-1, p90 1-1) | 274 | 0 | 1 | 0 | 2 |
| model calls per Episode | Langfuse live (56 Episodes, 95% 구간: median 3-8, p90 10-11) | 56 | 5 | 10 | 1 | 11 |
| tool calls per Episode | Langfuse live (56 Episodes, 95% 구간: median 2-8, p90 9-10) | 56 | 5 | 9 | 0 | 10 |
| root Episode latency ms | Langfuse live (56 Episodes, 95% 구간: median 1288-2572, p90 3101-3996) | 56 | 1988 | 3571 | 401 | 4466 |
| observations per trace | Langfuse live (56 Episodes, 95% 구간: median 18-51, p90 60-66) | 56 | 33 | 60 | 6 | 66 |
| Judge input tokens | local usage.jsonl (03a/03b만) | 37 | 672 | 1602 | 327 | 2055 |
| Judge output tokens | local usage.jsonl (03a/03b만) | 37 | 434 | 1610 | 129 | 6416 |
| improver output tokens | local usage.jsonl (06) | 1 | 15246 | 15246 | 15246 | 15246 |

주의:

- 에이전트 turn은 `stop=tool_use` 행 87건이다. Judge는 03a·03b의 `end_turn` 37건으로 분류했으나 파일 이름과 호출 구성에 근거한 **추정**이다. 02의 `end_turn` 23건은 에이전트 마지막 턴과 Judge가 섞여 어느 쪽에도 넣지 않았다. 06의 `end_turn` 1건은 개선기로 분류했고 n=1이라 분포가 아니다.
- 모델명이 비고 토큰이 0인 Claude 행 154건(live-verify 전체와 live 00의 2건)은 UNKNOWN usage이며 0이 아니다. 통계에서 뺐다. Jev 행 57건은 토큰이 없어 뺐다.
- 에이전트 cache_read의 min 0은 첫 턴이다.
- 모집단(calibrate-all 노트): 2026-11-04 이후 루트 `episode` 855개 중 mode=live 68개, holdout 12개 제외(`holdout` 태그는 0개였고 12개 모두 holdout 시나리오 ID와 `scenario_id`가 같아 제외, ID만 읽음), 사용 56개(`day05_new` 12, `day05-offline-eval` 12, `cc_m6` 12, `cc_ops` 20).
- Episode 단위 통계는 중앙값 구간이 넓어 불안정하다(model calls 3-8, root latency 1288-2572, observations per trace 18-51). 관측 단위(generation latency, tokens)는 구간이 좁다. 이전 10개 trace의 p90은 model calls 9, root latency 2792로 새 구간(10-11, 3101-3996) 밖이어서 10개가 꼬리를 낮게 잡았다. 중앙값 4개는 모두 새 구간 안이다.
- 환경별 중앙값(model calls, root latency ms): cc_m6 6, 1868 / cc_ops 5, 1646 / day05-offline-eval 8, 2518 / day05_new 6, 2060. 환경 차이가 있어 한 값으로 합치면 가려진다.
- `model calls per Episode`는 바깥 `ChatAnthropic`만 센 값이다. GENERATION을 모두 세면 두 배다.
- 제외 전 환경별 live 루트: day05_new 20, day05-offline-eval 12, cc_m6 16, cc_ops 20 (합 68). 제외 12개는 day05_new 8, cc_m6 4이며 이전 개수와의 뺄셈이다(노트에 직접 적힌 값은 아님).

## 5. 관찰된 live Trace 모양 (calibrate 노트)

관측 18개짜리 대표 trace. 깊이는 episode=0.

```
episode [AGENT]
  turn-1 [AGENT]
    LangGraph [CHAIN]
      model [CHAIN]
        ChatAnthropic [GENERATION]
          anthropic.messages.create [GENERATION]
      tools [CHAIN]
        get_order [TOOL]
          service.get_order [SPAN]
      model [CHAIN] ... (model / tools 반복)
```

- 모든 trace에 root `episode`와 `turn-1`(AGENT) 2개가 있다. 모델 호출 1회는 GENERATION 2개(바깥 `ChatAnthropic`, 안쪽 SDK `anthropic.messages.create`)로 기록된다.
- 도구는 `tools` 아래 도구 이름의 TOOL과 그 아래 `service.<도구>` SPAN이다. TOOL은 CallbackHandler, `service.*`는 서비스 코드가 직접 연 span이다.
- trace 10개의 유형 개수는 GENERATION 2~22, SPAN 0~10, TOOL 0~10, AGENT 항상 2(CHAIN은 GENERATION과 같거나 최대 2 많다). 에피소드 길이 분포가 넓다.

## 6. 생성기 결정

각 결정은 근거 행을 인용한다. 아직 코드로 확인되지 않은 부분은 7절 미확인에 둔다.

| # | 결정 | 근거 |
|---|---|---|
| D1 | OTLP exporter: endpoint `<LANGFUSE_HOST>/api/public/otel/v1/traces`, 인증은 HTTP Basic, header는 `Authorization`과 `x-langfuse-ingestion-version: 4`만 보낸다(값은 `.env`에서 읽고 출력하지 않는다). SDK의 `x-langfuse-sdk-*`·public-key header는 보내지 않아도 된다. start·end를 모두 보낸다 | Exporter setup, Q1, R3, R6 |
| D2 | 시간 창과 재적재: 합성 timestamp는 현재 기준 과거 7일 안에 둔다(Hobby 접근 30일 안, 한도 문서 없음). trace·span id는 결정적(sha256)으로 만들어 같은 입력이 같은 id가 되게 한다. 재적재는 서버가 upsert로 수렴함을 1회 관찰(Q2)했으나 문서는 중복 위험을 경고(R4)하므로, 로더의 기본은 빈 프로젝트에 한 번 적재이고 재실행 시 일시 중복(약 49초까지)을 안내한다 | Q1, Q2, R3, R4 |
| D3 | 유형: 모델 호출은 `generation`, 도구 호출은 `tool`(탐침에서 check_cancel_policy가 TOOL로 보존됨), 루트와 turn은 `agent`(Q4). Agent Dashboard 집계 조건은 R1이 미확인이므로 `service.<도구>`는 span으로 하되, 대시보드가 도구 호출을 세는지는 첫 적재 뒤 UI에서 확인한다. 호출당 GENERATION은 바깥 하나만 두고 안쪽 `anthropic.messages.create` generation과 CHAIN 래퍼는 만들지 않는다. 이는 근거 없는 잠정 설계 선택이다. calibrate-live가 모델 호출 수를 바깥 `ChatAnthropic` generation만으로 센 계수 기준(4절 비고)만 있고, 이 단순화가 Agent Dashboard·비용 집계에 주는 차이는 세 노트에 직접 근거가 없어 7절 미확인으로 남는다 | Q4, R1, R6, 5절 |
| D4 | 합성 표시: environment를 `synthetic`류의 전용 이름으로 정하고(예: 기존 `synth_probe` 탐침 environment와 구분), 모델명은 `synthetic/deepseek-v4.1-flash-ultrafast`, metadata에 `synthetic`·`generator`를 넣고 tags에 합성 표시를 단다. 트레이스 전체 속성(environment, version, session, user, tags)은 자식 span마다 복사한다 | Q4(전파 없음), R6 |
| D5 | 크기 예산: 길이 분포가 넓어(5절) 합성 trace의 평균 observation 수를 단정하지 않는다. unit은 trace+observation+score를 모두 센다(R2). 참고로 live Episode 56개(holdout 제외)의 observations per trace는 중앙값 33(95% 구간 18-51), p90 60이므로, live 모양의 280-Episode 로그라면 280 × 33 = 9,240 observations(중앙값 기준), p90 기준으로는 280 × 60 = 16,800이다. 평균은 calibrate-all 노트에 없어 쓰지 않는다. 이전 10개 trace 값(평균 31.2, 약 8,700)은 대체됐다. 계획한 합성 트리는 LangGraph·모델·도구 CHAIN 래퍼와 안쪽 SDK generation을 빼므로 이보다 적을 것이고, 정확한 합성 observation 수는 생성기가 정하고 테스트하므로 그때까지 미확인이다. Hobby는 월 50k units(R2)이지만, 수강생이 만드는 score·Judge 평가·experiment도 같은 한도를 쓰므로 합성 적재량에 여유를 남긴다. 초과 시 동작은 미확인이라 한도 가까이 채우지 않는다 | R2, 4절 |
| D6 | 읽기 도구: `wait_for_observations`와 `lf_table`의 시간 창은 backdated 데이터를 담도록 7일 이상(또는 `from_start_time` 없이)으로 넓힌다. 읽기 후 start_time 오름차순으로 정렬해 단계 순서를 만든다(API 기본은 내림차순). 적재 직후 읽기는 첫 읽기 38.7초에 이미 보였지만(상한) 재전송 수렴은 약 49초이므로 대기 시간을 두고 재시도한다. 모델명은 `with_raw_response`나 필터 column으로 읽는다(`providedModelName`은 None) | Q1, Q5, Q6, Q7, Q4 |
| D7 | 비용: `cost_details`를 항상 명시해 보낸다(보낸 값이 유지되고 재계산되지 않음). 모델 정의가 없어 internalModelId가 비는 것이 관찰됐고 가격 추론에 기대지 않는다. 사용자 정의 모델 등록은 선택(`(?i)^synthetic/deepseek-v4\.1-flash-ultrafast$`). 토큰은 4절 분포(agent input median 265, output median 68 등)에서 뽑고 합성 값임을 밝힌다 | Q4, R5, 4절 |
| D8 | 루트 요약: 루트 output에 `episode_summary`(day05-episode-summary-v1) JSON 문자열을 넣어 `artifact_from_root_observation`이 복원하게 한다. input/output은 trace-level이 아니라 루트 span의 `langfuse.observation.input/output`에 둔다. 실패 Episode에서 Rule id 일치는 미확인이라 FAIL 사례를 함께 한 번 적재해 확인한다 | Q3, R6 |
| D9 | 지연 분포: generation 지연은 4절(median 276 ms, p90 567 ms, n=318)에서, service span은 0~2 ms에서, 루트 Episode는 401~4466 ms 범위(median 1988, p90 3571, n=56)에서 뽑되 1회 관찰 표본임을 문서에 적는다 | 4절 지연 행 |

## 7. 미확인

- Agent Dashboard가 어떤 observation 유형·속성(`tool` 유형인지 generation의 `tool_calls`인지)을 도구 호출로 세는지, 합성 trace가 그 위젯에 나오는지 (R1). 첫 적재 뒤 UI 확인 필요.
- 재전송이 항상 upsert로 수렴하는지. 탐침은 1회 관찰만 있고(Q2) 문서는 중복 위험을 말한다(R4). 서버 코드는 읽지 않았다.
- 기본 시간 창의 상한과 과거 timestamp 한도(Q1, R3), backdated 데이터가 dashboard와 Metrics API에서 보이는 방식(R3). Metrics는 창 D-7 -1h~now+5m에서만 관찰했다(Q5).
- Hobby 한도 초과 시 차단인지 제한인지 (R2).
- `x-langfuse-ingestion-version: 4`가 2026-11-16 이후 필수인지, 없을 때 지연이 10분인지 15분인지 (R6). 탐침은 이 header를 보내서 지연 없는 상태만 봤다.
- `default-model-prices.json` 뒷부분 166,154자(전체 266,154자 중 앞 100,000자만 읽음)에 deepseek 또는 synthetic 패턴이 있는지 (R5). 탐침에서 internalModelId가 빈 것은 그 환경에서의 1회 관찰이다.
- FAIL Episode에서 `evaluate_trajectory`의 치명 Rule id가 로컬과 일치하는지 (Q3은 PASS 사례만).
- Q7의 실제 가시화 지연의 하한(0건 상태를 못 봄).
- GENERATION을 live처럼 호출당 2개로 둘지, 바깥 하나로 줄일지에 따른 Agent Dashboard·비용 집계 차이. 세 노트에 직접 근거가 없다.
- Judge 통계의 역할 분류는 추정이다(4절). improver는 n=1이다. 02의 Judge와 에이전트 마지막 턴은 분리하지 못했다.
- 분포의 대표성: 표본이 live Episode 56개(holdout 제외)와 저자 1일 실행이라 다른 실행·다른 모델에 일반화하지 않는다.
- 탐침의 노트가 쓴 environment `synth_probe`의 Episode 1개는 calibrate 환경 집계에 들어 있다(저자 프로젝트에 탐침 데이터가 남아 있다). 정리 여부는 이 노트가 정하지 않는다.

Source note status: COMPLETE
