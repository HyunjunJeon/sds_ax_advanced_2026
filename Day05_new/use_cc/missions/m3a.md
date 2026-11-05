# M3a. 정답이 없는 운영 trace를 무엇으로, 어떤 것부터 채점하나 (Part 3 · 온라인 평가와 Trace 선정 · 50분)

> **핵심 질문: 운영 중에는 기대 정답이 없다. 무엇을 재고, 수천 건 중 어떤 trace부터 채점하나?**
>
> 강의는 `concepts/m3a.md` 1~6절(정답이 필요한 지표와 필요 없는 지표, 모의 운영 트래픽, 표본 선정 전략 4종, Rule과 Evaluator, 일괄 채점, 7일 매칭량과 비용)을 설명합니다.
> 이 미션은 선정 전략이 **무엇을 놓치는지**와 점수가 **Langfuse의 어느 observation에 붙는지**를 눈으로 봅니다.

## 이 미션의 비용

| 무엇 | 규모 | 누구의 비용 |
|---|---|---|
| 이 Claude Code 세션 | 약 10~25회(리허설 전 추정) | 내 Claude Code 계정 |
| 에이전트 모델 | 0회(트래픽은 scripted 모의 트래픽) | — |
| Jev, Judge | M3a-4: Jev 최대 10회, Judge(xhigh) 최대 30회. 저자 1회 관찰(노트북 03a, 20건): 의미 판정 60개 중 18개가 Judge로 넘어감 | Decision API 키, `OPENGATEWAY_API_KEY` |
| Langfuse | Episode 60개와 점수 | 내 Langfuse 프로젝트 |
| M3a-3b 배경 운영 로그 | 에이전트 모델 0회, Jev 0회, Judge 0회(m0에서 적재한 JSONL을 읽기만 함) | — |

Langfuse environment는 `cc_m3a`입니다.

---

## M3a-1. `[따라하기]` 이틀치 모의 운영 트래픽 (5분)

> `concepts/m3a.md` 2절처럼, 하루 30건씩 이틀치 모의 트래픽을 같은 2절의 `MISTAKE_RATES`, seed 7로 scripted 실행해 Langfuse `cc_m3a`(version `mock-baseline`)에 남기고, 날짜별 판정 요약 표를 보여 줘. `work/m3a_traffic.py`로.

**관찰할 것.** 2일차에 늘어난 사건 유형(표의 도구 오류 Episode, escalated 응답). Langfuse의 **Dashboards → Langfuse Agent Dashboard**에서 environment를 `cc_m3a`로 바꾸고 도구 호출 수와 도구 오류를 봅니다. 이것은 **모의 트래픽**이지 모델 성능이 아닙니다.

## M3a-2. 먼저 예측하세요 (3분)

`notes/m3a.md`에 적습니다.

1. random, stratified, signal(도구 오류·escalated·지연·규칙 위반 우선), novelty(Golden에 없는 요청 모양) 중 **치명 위반 Episode를 가장 많이** 뽑는 전략은?
2. signal 전략이 **놓치는** 위반은 어떤 모양일까요? 힌트: 도구 오류도, escalated 응답도 남기지 않는 위반이 있습니다.
3. "비율을 말할 수 있는" 표본을 주는 전략은 어느 것인가요?

## M3a-3. `[따라하기]` 네 전략으로 8건씩 뽑는다 → `[내 것 만들기]` 내 전략 (12분)

> `concepts/m3a.md` 3절처럼 네 전략으로 8건씩 고르고, 전략별로 치명 위반 Episode 수, 실수를 심은 Episode 수, 2일차 비율, 선정 이유(앞 5건)를 표로 보여 줘.

**관찰할 것.** 선정 이유 칸(`이유`). signal이 뽑은 것과 놓친 것의 차이를 예측 2와 비교합니다.

그다음 **내 선정 전략을 말로** 정합니다(예: "signal 5건 + 층화 3건", "2일차에 늘어난 사건 유형을 두 배로"). `notes/m3a.md`에 적고 Claude Code에게 `work/m3a_my_strategy.py`로 구현해 같은 표에 한 줄을 더해 달라고 합니다. `eval_lab/online.py`는 고정 부품이라 고치지 않고, `select_traces`의 결과를 조합하는 식으로 만듭니다.

## M3a-3b. `[바꿔보기]` 배경 운영 로그에서 선정 전략 비교 (5분)

m0에서 적재한 7일치 **합성 배경 운영 로그**(environment `synth_ops`)를 이 카드에서는 읽기만 합니다. 다시 적재하지 않습니다. 합성 데이터이므로 모델 성능이 아니며, `concepts/m3a.md` 7절이 왜 풀이 커지면 전략마다 놓치는 것이 달라지는지 설명합니다.

**먼저 예측하세요.** `notes/m3a.md`에 적습니다. 같은 k로 뽑을 때 (1) 5일차 결제 장애 시간대(14~16시)의 Episode를 가장 많이 담는 전략은? (2) 6일차 agent-v2 Episode를 가장 많이 담는 전략은? (3) 네 전략 모두 놓칠 것 같은 날은 언제입니까?

> m0에서 `./lab tools/synth_load.py`가 출력한 "로컬 기록" 경로의 JSONL을 `eval_lab.synth.read_local_records`로 읽고, `concepts/m3a.md` 7절처럼 `online.select_traces`를 random, stratified, signal, novelty로 같은 k와 seed로 돌려 줘. 전략별로 뽑힌 Episode가 덮는 story_day, family_id, version(agent-v1/agent-v2)의 개수와, 덮지 못한 story_day를 표로 보여 주고, 뽑힌 trace마다 Langfuse trace URL을 함께 출력해 줘. `work/m3a_background.py`로.

**관찰할 것.**

- 표에서 전략마다 덮지 못한 날과 version. 예측과 비교합니다.
- Langfuse **Tracing**에서 environment를 `synth_ops`, 시간 범위를 **Past 7 days**로 두고, 출력한 URL로 뽑힌 trace를 몇 개 엽니다. 5일차 시간대와 6일차 version이 trace에서 어떻게 보이는지 봅니다.
- 이 표는 선정이 덮는 범위이지 위반율이 아닙니다. signal 표본으로 전체 비율을 말하지 않습니다.

## M3a-4. `[따라하기]` 고른 trace를 일괄 채점하고 점수를 붙인다 (12분, 유료)

비용: Jev 최대 10회, Judge(xhigh) 최대 30회.

> 내 전략으로 고른 것 중 10건을 `concepts/m3a.md` 5절('선정 trace 20건을 일괄 채점한다' 코드 예시)처럼 채점해 줘: root 필터에 `traceId` "any of" 조건을 더하고, `wait_for_observations`로 집계를 기다린 뒤 `batch_evaluate`(v2 관측 API)로 `online_evaluators`(궤적 + 의미)를 돌려. 기다린 초, 가져온 건수, 점수 수, Judge로 넘어간 비율을 출력해 줘.

**관찰할 것 (Langfuse).**

- 출력의 "집계 지연: N초 기다려 …건이 읽힌다". 기록한 뒤 바로 읽으면 0건이 될 수 있다는 것을 숫자로 봅니다.
- 왼쪽 메뉴 **Scores**: 검색에 `name:trajectory_status`. 각 줄의 **Trace**·**Observation** 칸. 점수는 trace가 아니라 **root observation**(`episode`)에 붙어 있습니다.
- 점수가 붙은 trace를 열어 root를 누르고 **Scores** 탭: `trajectory_status`, `fatal_count`, `message_consistent` 등. 의미 점수의 comment와 metadata에서 Jev가 정했는지 Judge가 정했는지(`stage`).
- 같은 trace의 다른 observation(`turn-1`, `service.*`)에는 점수가 없는지.

## M3a-5. `[바꿔보기]` 7일 비용 (5분, 호출 없음)

**먼저 예측하세요.** 하루 5,000건, Judge를 하루 200건까지만 부를 수 있다면 샘플링 비율은 얼마여야 할까요? 곱셈으로 먼저 답하고 `concepts/m3a.md` 6절의 계산으로 확인합니다. M3a-4에서 잰 Judge 넘김 비율을 넣어 봅니다. 그 비율은 10건짜리 1회 관찰이라는 것을 함께 적습니다.

---

## 마치기 전에 확인

| 확인할 것 | 확인하는 법 |
|---|---|
| 내 선정 전략이 표에 있다 | `work/m3a_my_strategy.py` 출력 |
| 점수가 observation에 붙었다 | Langfuse Scores에서 `cc_m3a`의 `trajectory_status` 줄과 Observation 링크 |
| 예측과 내 전략 | `notes/m3a.md` |
| 배경 운영 로그에서 네 전략이 덮은 날과 version을 비교했다 | `work/m3a_background.py` 출력과 Langfuse `synth_ops` trace |

## 확인 질문

1. 운영 trace에 쓸 수 없는 지표와 쓸 수 있는 지표를 하나씩 들고, 그 차이를 "정답이 필요한가"로 설명하세요.
2. 내 선정 전략이 놓치는 위반은 무엇인가요? 그것을 보완하는 데 드는 비용은?
3. 점수를 trace가 아니라 root observation에 붙이는 이유는 무엇인가요? (힌트: Langfuse Cloud의 trace-level evaluator는 2026-11-16에 결과 생성을 멈춘다 — `concepts/m3a.md` 4절)
4. 기록 직후 채점하면 0건이 읽힐 수 있다는 것은, 자동 운영 루프를 설계할 때 무엇을 요구하나요?
5. 배경 운영 로그에서 한 전략이 5일차 결제 장애나 6일차 agent-v2를 놓쳤다면, 그 이유를 전략의 선정 기준으로 설명하세요. 이 결과가 에이전트 성능이 아닌 이유는 무엇입니까?
