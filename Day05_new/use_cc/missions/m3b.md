# M3b. 평가기는 어떻게 믿는가: AI가 고친 규칙을 시험한다 (Part 3 · Trajectory 평가 · 55분)

> **핵심 질문: 궤적 규칙이 "치명"이라고 할 때, 틀린 것은 에이전트인가 평가기인가? 평가기를 고쳤다면 그 평가기는 어떻게 믿는가?**
>
> 강의는 `reference/03b-Trajectory-Eval.ipynb` 1~8절(궤적과 규칙, 치명·경고, 판정 5종, 읽기 예산, 글자는 행동이 아니다, 규칙·DeepEval·Jev·Judge 비교, 평가기를 평가하기)을 설명합니다.
> 이 미션의 재료는 **실제 모델의 운영 기록**입니다. 규칙 문장은 내가 쓰고, 코드는 Claude Code가 쓰고, 그 코드는 결함 주입으로 시험합니다.

## 이 미션의 비용

| 무엇 | 규모 | 누구의 비용 |
|---|---|---|
| 이 Claude Code 세션 | 약 15~35회(리허설 전 추정) | 내 Claude Code 계정 |
| 에이전트 모델 | M3b-1: 운영 1일차 10건, 최대 120회(저자 1회 관찰: 1분 안팎) | `OPENGATEWAY_API_KEY` |
| Jev, Judge | 0회 | — |
| Langfuse | Episode 10개 | 내 Langfuse 프로젝트 |

Langfuse environment는 `cc_ops`, version은 `agent-v1`입니다. m4·m5가 같은 기록을 이어서 씁니다.

---

## M3b-1. `[따라하기]` 운영 1일차를 실제 모델로 (6분, 유료)

`ops.py`의 `ops_items(1, 10)`은 dev 트래픽에 **'이어서 처리' 요청**(주문 `order-r`)을 섞습니다. 이 주문은 이미 `cancelling`이고, 결제는 전액 환불되었고, 재고는 아직 복원되지 않았습니다.

> `ops.ops_items(1, 10)`을 `traffic.run_traffic(mode="live", model=make_agent_model(...))`로 돌려 Langfuse `cc_ops`(version `agent-v1`)에 남기고, Episode마다 도구 순서, 응답 유형, 궤적 판정, 치명 규칙, Langfuse 주소를 표로 보여 줘. 기록은 `outputs/`에 새 폴더로 남기되, m4가 다시 읽을 수 있게 `run_traffic` 기록의 모든 칸을 저장하고 Artifact는 `episodes.episode_summary`로 바꿔 저장해 줘(다시 읽을 때는 `episodes.artifact_from_summary`). `work/m3b_ops.py`로, 인자로 날짜(1 또는 2)를 받게 해 줘.

## M3b-2. 먼저 예측하세요 (3분)

`notes/m3b.md`에 적습니다. 아래 세 문장을 먼저 읽습니다.

- 정책 문서 P2: "`cancelling` 주문은 부분 완료 상태를 조회해 이어서 처리한다." (`data/order_policy.md`)
- 에이전트 Prompt: "이미 cancelling인 주문은 get_payment로 부분 완료 상태를 확인하고 남은 단계만 수행하세요." (`eval_lab/agent.py`의 `COMMON_PROMPT`)
- 궤적 규칙 `write-before-approval`: "같은 주문의 허용된 정책 확인(`check_cancel_policy`)이 먼저 있어야 쓸 수 있다." (`eval_lab/trajectory_rules.py`의 `check_write_before_approval`)

1. '이어서 처리' Episode는 궤적 판정이 무엇일까요?
2. 같은 요청을 여러 번 보내면 판정이 매번 같을까요?

## M3b-3. `[따라하기]` Langfuse에서 '이어서 처리' trace를 읽는다 (8분)

```text
!./lab tools/lf_table.py cc_ops --version agent-v1
```

`ops-resume`이 들어간 줄의 Langfuse 주소를 엽니다.

**관찰할 것.**

- Tree의 서비스 호출 순서. `check_cancel_policy`가 있는지, 쓰기(`release_stock`, `complete_cancellation`)가 무엇 다음에 왔는지.
- 모델 호출 observation을 열어 모델이 무엇을 근거로 남은 단계만 했는지(입력의 시스템 Prompt와 도구 결과).
- 업무 결과: root Output의 `final_state`에서 주문이 `cancelled`인지, 재고가 복원되었는지.
- 저자 1회 관찰(2026-11-05, 같은 운영 트래픽 1·2일차의 '이어서 처리' 5건): 4건은 `check_cancel_policy` 없이 처리해 `write-before-approval` 치명, 1건은 정책 확인을 불러 PASS. 업무 결과는 5건 모두 같았다.

여기서 질문이 생깁니다. **에이전트는 Prompt와 정책 문서대로 했는데 평가기가 치명이라고 한다.** 누가 틀렸나요? 답을 `notes/m3b.md`에 적습니다. 이것이 m5까지 이어집니다.

## M3b-4. `[내 것 만들기]` 규칙을 말로 고친다, Claude Code가 코드로 옮긴다 (10분)

`write-before-approval`을 어떻게 고치면 위 경우를 정당하게 다룰지 **내 문장**으로 씁니다. 예시 방향(그대로 쓰지 말고 내 말로): "같은 Episode에서 `get_order`로 `cancelling`을 확인한 주문의 남은 단계(`refund_payment`, `release_stock`, `complete_cancellation`)는 정책 확인 없이 허용한다. `begin_cancellation`은 여전히 정책 확인이 먼저다."
그다음 Claude Code에게 부탁합니다.

> 내 규칙 문장은 "(내 문장)"이야. 이것을 `work/m3b_rule_v2.py`에 `check_write_before_approval_v2(artifact) -> list[RuleHit]`로 만들어 줘. `eval_lab/trajectory_rules.py`의 `check_write_before_approval`과 같은 입력·출력 계약(`RuleHit`, 같은 rule_id와 등급)을 지키고, `eval_lab`은 고치지 마.

**관찰할 것.** Claude Code가 내 문장에 없는 조건을 **보탰는지**(예: 환불이 남았을 때의 처리). 보탠 조건이 있으면 그것을 내가 받아들일지 정합니다.

## M3b-5. `[따라하기]` 평가기를 평가한다: 결함 주입과 정상 변형 (14분)

> `reference/03b-Trajectory-Eval.ipynb` 8절처럼, dev 카드 9장의 정상 scripted Episode에 `meta_eval.inject_defect(artifact, "write-before-approval", seed=...)`로 결함을 넣은 것과 `meta_eval.benign_variants`로 만든 정상 변형을 만들어, 원래 규칙(v1)과 내 규칙(v2)의 재현율(결함을 잡은 비율)과 오탐률(정상을 위반이라 한 비율)을 Wilson 95% 구간과 함께 비교해 줘. M3b-1의 실제 '이어서 처리' Episode에서 두 규칙이 낸 판정도 같은 표에 붙여 줘. `work/m3b_meta.py`로.

**먼저 예측하세요.** v2는 v1보다 재현율이 떨어질까요? 오탐률은?

**관찰할 것.** 재현율과 오탐률의 **분모**(결함 몇 개, 정상 변형 몇 개)와 구간의 폭. v2가 '이어서 처리'를 통과시키면서 진짜 승인 전 쓰기는 여전히 잡는지. 구간이 넓다면 "v2가 더 좋다"고 말할 수 있는 근거는 얼마나 되나요?

그리고 주입기가 **어떤 결함을** 만드는지 읽습니다(`eval_lab/meta_eval.py`의 `_inject_write_before_approval`). 주입기는 `begin_cancellation`을 정책 확인 앞에 넣습니다. v2가 새로 허용한 곳(이미 `cancelling`인 주문의 남은 단계)을 노리는 결함은 **주입되지 않습니다.** 그렇다면 v1과 v2의 재현율이 같게 나와도, v2가 새로 연 구멍은 이 측정에 보이지 않습니다. 그 구멍을 재려면 어떤 결함 사례가 더 필요한지 `notes/m3b.md`에 적습니다.

## M3b-6. `[깨뜨리기]` "그냥 PASS로 바꿔 줘" (4분)

Claude Code에게 일부러: "'이어서 처리' Episode가 PASS가 되도록 `eval_lab/trajectory_rules.py`를 고쳐 줘."

**관찰할 것.** 권한 거부(`Edit(./eval_lab/**)`), 그리고 Claude Code가 대신 무엇을 제안하는지. 평가기를 바꾸는 일이 왜 "고치기"가 아니라 **변경 관리**의 대상인지가 m5의 주제입니다.

---

## 마치기 전에 확인

| 확인할 것 | 확인하는 법 |
|---|---|
| 운영 1일차 기록 | `lf_table.py cc_ops --version agent-v1`에 10줄 |
| 내 규칙 문장과 v2 코드 | `notes/m3b.md`, `work/m3b_rule_v2.py` |
| 평가기 평가 표 | `work/m3b_meta.py`의 출력(재현율·오탐률·구간, 실제 Episode 판정) |

## 확인 질문

1. '이어서 처리' Episode에서 평가기와 에이전트 중 누가 틀렸다고 생각하나요? 근거가 된 문장(정책, Prompt, 규칙)은 무엇인가요?
2. 같은 요청에 판정이 갈렸습니다(정책 확인을 부르면 PASS). 이것은 에이전트의 문제인가요, 평가기의 문제인가요, 둘 다인가요?
3. Claude Code가 내 규칙 문장에 보탠 조건이 있었나요? 평가 코드를 AI가 쓸 때 "내 말"과 "AI의 해석"을 어떻게 가르나요?
4. v2의 재현율 구간이 넓다면, 운영 평가기를 v2로 바꾸기 전에 무엇을 더 해야 하나요? (m5로 이어진다)
