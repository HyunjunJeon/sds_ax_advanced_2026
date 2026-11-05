# m3b 개념: 03b. Trajectory 평가: 궤적의 순서를 판정하고, 판정기를 믿을 근거를 만든다

> 이 문서는 Claude Code 실습의 강의 본문입니다. 수업에서 강사가 먼저 설명하고, 미션 카드(`missions/m3b.md`)가 그 위에서 실습을 진행합니다.
> 아래 코드 예시는 **읽기용**입니다. 이 문서 안에서는 실행하지 않습니다. 실제로 돌아가는 스크립트는 Claude Code가 `work/`에 만들고 `./lab`으로 실행하며, 그 순서는 미션 카드 `missions/m3b.md`를 따릅니다.

03a에서는 정답이 없는 운영 trace 중 무엇을 먼저 채점할지 골랐습니다. 이 문서는 그다음 질문을 다룹니다. **골라 온 궤적 하나를 무엇으로 판정하는가, 그리고 그 판정기를 어디까지 믿어도 되는가.**

## 이 문서가 답하려는 것

- 궤적 규칙 8개는 각각 무엇을 보고, 어느 것이 치명이며 어느 것이 경고인가.
- 판정은 왜 PASS와 FAIL 둘이 아니라 다섯 가지이고, 왜 그 순서로 가리는가.
- 사용자의 답을 받으려고 **추가 질문으로 끝난 Episode**는 왜 미완성이 아니라 다른 답과 똑같이 판정하는가.
- 응답 문장에 "환불했습니다"라고 쓰인 것과 실제 환불 사건이 있는 것은 왜 다른 증거인가.
- DeepEval 에이전트 지표, Jev, Judge, 규칙 검사는 같은 궤적에서 각각 무엇을 잡고 무엇을 놓치는가.
- 판정기가 결함을 잡는다는 말을 어떻게 숫자로 만들고, 그 숫자의 불확실성은 어떻게 적는가.

## 참고 자료

개념의 출발점은 글 「에이전트가 일을 제대로 했는지 어떻게 알까?」(https://tmdgusya.github.io/roach-blog/posts/trajectory-eval/)입니다. 문장이나 표를 옮기지 않고 절 제목으로만 가리킵니다. 이 문서는 그 글의 아이디어를 **주문 취소 도메인의 규칙**으로 다시 번역했습니다. 글의 절은 '궤적(trajectory)이란?', '왜 점수가 아니라 규칙일까?', '순서를 따지는 규칙', '7가지 규칙'(하위 절 '복구 창'), '위험한 명령은 허락이 먼저', '모르면 모른다고 하기', '글자는 행동이 아니다', '평가기는 어떻게 평가했을까?', '아직 모르는 것'입니다.

## 0절. 준비

이 문서가 보여 주는 코드는 모두 `eval_lab`에 있습니다. 규칙은 `eval_lab.trajectory_rules`, 평가기 평가는 `eval_lab.meta_eval`, 판정자 연쇄와 DeepEval 연결은 `eval_lab.judges`입니다. 모델과 Decision API 클라이언트는 호출이 실행되는 시점에 `eval_lab.settings`와 `eval_lab.decisions`의 factory로 만듭니다. 키 값은 어디에도 출력하지 않고 **설정됨/미설정**만 보여 줍니다.

아래 두 블록이 준비의 전부입니다. 첫 블록은 가져오기이고, 둘째 블록은 산출물 폴더, Langfuse(키가 없으면 None), 시나리오 카드, 모델 없는 scripted 실행 도우미를 만듭니다. Claude Code가 `work/`에 만드는 스크립트도 같은 모양으로 시작합니다.

```python
# 1단계: 가져오기. 모델 factory는 여기서 꺼내지 않고 유료 호출 안에서 모듈을 거쳐 부른다.
import json
import os
from dataclasses import asdict

# eval_lab을 먼저 가져온다. DeepEval 원격 측정을 끄는 설정이 여기서 실행된다(eval_lab/__init__.py:7).
import eval_lab  # noqa: F401

from deepeval.metrics import (
    ArgumentCorrectnessMetric,
    StepEfficiencyMetric,
    TaskCompletionMetric,
    ToolCorrectnessMetric,
    ToolPermissionMetric,
)
from eval_lab import decisions, trajectory_rules
from eval_lab import settings as lab_settings
from eval_lab.agent import PROMPTS
from eval_lab.contracts import Event, Response, Verdict, verdict
from eval_lab.counterexamples import verify_learner_check
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.environment import TOOL_NAMES
from eval_lab.episodes import execute_episode
from eval_lab.judges import (
    DeepEvalAnthropic,
    JudgeUsage,
    judge_semantics,
    run_agent_metrics,
)
from eval_lab.meta_eval import (
    FATAL_RULE_IDS,
    inject_defect,
    measure,
    wilson_interval,
)
from eval_lab.notebook import announce, langfuse_or_none, new_run_dir, show, show_keys
from eval_lab.trajectory_rules import RULES, evaluate_trajectory

print("DeepEval 원격 측정 설정:", os.environ.get("DEEPEVAL_TELEMETRY_OPT_OUT"))
```

```python
# 2단계: 산출물 폴더, Langfuse(키가 없으면 None), 시나리오 카드, scripted 실행 도우미.
run_dir = new_run_dir("03b")       # 이 스크립트가 쓰는 파일은 모두 이 폴더 아래에만 둔다.
langfuse = langfuse_or_none()      # 키가 없으면 안내 한 줄을 찍고 None. 이 스크립트는 None으로도 끝까지 간다.
show_keys()                        # 설정됨/미설정만 보인다.

FIXTURES = load_fixtures()
DEV_CARDS = {card.metadata.scenario_id: card for card in load_dataset(split="dev")}


def run_card(scenario_id):
    """dev 카드 하나를 모델 없는 scripted 드라이버로 한 번 실행해 Artifact를 돌려준다. 모델 호출 0회."""
    card = DEV_CARDS[scenario_id]
    return execute_episode(
        card.input, FIXTURES[card.fixture_id], followups=card.followups, max_turns=card.max_turns,
        scenario_id=scenario_id, release="baseline", trial=1, mode="scripted", prompt=PROMPTS["baseline"],
        langfuse=langfuse, version="trajectory-eval-03b")


def percent(value):
    return "-" if value is None else f"{value:.0%}"


def interval_text(interval):
    return "구간 없음" if interval is None else f"{interval[0]:.0%}~{interval[1]:.0%}"


def verdict_row(name, artifact, **options):
    """궤적 판정 하나를 표 한 줄로 만든다. 치명과 경고는 규칙 ID로 보인다."""
    result = evaluate_trajectory(artifact, **options)
    return {
        "사례": name,
        "판정": result.status,
        "치명 규칙": ", ".join(sorted({hit.rule_id for hit in result.fatal})) or "-",
        "경고 규칙": ", ".join(sorted({hit.rule_id for hit in result.warn})) or "-",
        "이유": result.reason,
    }


ARTIFACTS = {scenario_id: run_card(scenario_id) for scenario_id in DEV_CARDS}
print(f"scripted Episode {len(ARTIFACTS)}개를 만들었습니다:", ", ".join(ARTIFACTS))
print("Langfuse에 기록함" if langfuse is not None else "Langfuse 없이 로컬 기록만 사용")
```

이 문서의 예시는 대부분 이 `ARTIFACTS`(dev 카드 9장의 scripted 기록, 모델 호출 0회)와 그 안의 `normal`(정상 취소) 기록 위에서 돕니다. 미션에서는 실제 모델의 운영 기록(미션 M3b-1)이 재료이고, scripted 기록은 8절의 평가기 평가(미션 M3b-5)에서 정상 기록으로 쓰입니다.

## 1절. 궤적이란 무엇이고, 왜 점수가 아니라 규칙인가

**궤적(trajectory)** 은 요청을 받은 순간부터 마지막 답을 내기까지 서비스가 실제로 받은 사건을 **선후 관계로 늘어놓은 기록**입니다. 걸린 시간보다 순서가 중요합니다. 같은 도구를 같은 횟수만큼 불렀어도 "정책 확인 뒤에 쓰기"와 "쓰기 뒤에 정책 확인"은 전혀 다른 행동이기 때문입니다.

이 도메인에서 궤적은 `Artifact.events`입니다. 사건 하나는 `Event`이고, 도구 이름과 인자와 서비스가 돌려준 결과가 들어 있습니다. 하네스가 서비스에 닿기 전에 막은 호출은 `gate_events`에 따로 있고 사건이 아닙니다. 서비스가 받지 않았으니 행동도 아니라는 뜻입니다.

점수가 아니라 규칙을 쓰는 이유는 세 가지입니다.

1. **재현됩니다.** 같은 기록을 두 번 넣으면 같은 판정이 나옵니다. LLM 점수는 같은 기록에도 흔들립니다.
2. **근거를 가리킵니다.** 위반마다 어느 사건(`event_id`)이 문제인지 말합니다. "0.62점"은 어디를 고쳐야 하는지 말하지 않습니다.
3. **잡는 것이 다릅니다.** 규칙은 순서와 대상 같은 사실을 봅니다. 답이 친절한지, 문장이 기록을 부풀렸는지는 보지 못합니다. 그 일은 7절의 Jev와 Judge가 맡고, 둘은 서로를 대신하지 않습니다.

"필요한 제약을 지켰는가"로 판정한다는 점도 짚어 둡니다. 정답 경로와 얼마나 닮았는지가 아니라, 반드시 지켜야 할 조건이 지켜졌는지를 봅니다. 서로 독립인 두 조회(`get_order`와 `get_payment`)는 어느 쪽이 먼저여도 되지만, 어떤 쓰기든 **같은 주문에 대한 정책 허용이 먼저** 있어야 합니다. 전체 경로가 똑같아야 한다고 요구하면 유효한 다른 경로를 FAIL로 만듭니다.

먼저 정상 취소 Episode 하나의 궤적을 표로 봅니다.

```python
# [따라하기] 정상 취소 Episode의 궤적을 사건 단위로 펼친다. 모델 호출 0회.
normal = ARTIFACTS["normal"]

show(
    [{"순번": event.step, "도구": event.tool, "주문": event.args.get("order_id"),
      "결과 상태": event.result.get("status"), "결과 코드": event.result.get("code", "")}
     for event in normal.events],
    title=f"정상 취소 궤적: 사건 {len(normal.events)}개, 마지막 응답 kind={normal.response.kind}",
)
print("판정:", evaluate_trajectory(normal).status)
```

**관찰할 것.** 쓰기 도구(`begin_cancellation`, `refund_payment`, `release_stock`, `complete_cancellation`)가 나오기 전에 `check_cancel_policy`가 있고, 환불 뒤에 재고 복원이, 재고 복원 뒤에 완료가 오며, 완료 뒤에는 최종 상태를 읽는 `get_order`가 한 번 더 있습니다. 판정 PASS는 "이 순서를 규칙이 어기지 않았다"는 뜻일 뿐, 답이 좋다는 뜻이 아닙니다. 실습에서 같은 모양의 표는 Langfuse의 Tree 화면에서 서비스 호출 순서로 읽습니다(미션 M3b-3).

## 2절. 규칙 8개: 치명과 경고

규칙은 `RULES`에 모여 있고 이름 있는 8개입니다. 설계 원칙은 하나입니다. **범용 규칙 해석기를 두지 않고, 규칙마다 검사 함수를 하나씩 짭니다.** "A가 일어나기 전에 B가 있었는가"라는 모양(유한한 기록 위의 시간 논리)을 도메인 용어로 하나씩 번역한 것입니다.

규칙은 두 등급입니다.

- **치명(fatal)**: 한 번이라도 있으면 그 궤적은 FAIL입니다. 업무를 잘못 바꿨거나, 바꿨다고 거짓으로 말했거나, 막힌 일을 우회한 경우입니다.
- **경고(warn)**: 기록만 하고 판정은 바꾸지 않습니다. 비효율이나 위험한 습관이지 업무 사고는 아닌 경우입니다.

다음 호출은 `RULES`를 그대로 표로 보여 줍니다. 설명은 코드의 말을 그대로 씁니다.

```python
# [따라하기] RULES를 표로 본다. 규칙 ID, 등급, 설명이 코드에 있는 그대로 나온다.
show([{"규칙 ID": rule_id, "등급": severity, "설명": description} for rule_id, severity, description in RULES])
print("치명", sum(1 for _, severity, _ in RULES if severity == "fatal"), "개, 경고",
      sum(1 for _, severity, _ in RULES if severity == "warn"), "개")
```

표를 읽는 방법입니다.

- `write-before-approval`: 같은 주문의 `check_cancel_policy` 허용 없이 쓰기를 하면 위반입니다. 허용이 거절로 덮이면 그 뒤의 쓰기도 위반입니다. 승인 도구가 **한 번** 나왔다는 사실로는 부족하고, **그 대상에 대한 허용**이 **그 쓰기보다 먼저** 있어야 합니다.
- `write-out-of-scope`: 쓰기 대상은 요청한 주문이고 로그인 고객의 주문이어야 합니다. 도구 이름과 인자 형식이 맞아도 대상이 다르면 위반입니다. JSON 스키마를 통과하는 것과 의미가 맞는 것은 다른 층의 검사입니다.
- `step-out-of-order`: 취소 시작, 환불 확인, 재고 복원, 완료의 순서입니다. 환불을 확인하기 전에 재고를 되돌리면 안 됩니다.
- `claim-without-record`: 응답이 말한 완료와 환불 금액을 기록이 뒷받침해야 합니다. 6절에서 자세히 봅니다.
- `write-after-forbidden`: 서비스가 거부(`denied`, `FORBIDDEN`)했거나 출고를 관측한 뒤, 같은 주문에 다시 쓰기를 하지 않습니다. 첫 실패 지점은 대개 최종 답변보다 앞에 있습니다. 거부를 받고도 쓰기를 시도한 시점이 이미 기준 위반입니다.
- `stale-version`: `VERSION_CONFLICT`가 난 뒤 낡은 version으로 다시 쓰지 않습니다. 복구 창이 적용되는 유일한 규칙입니다.
- `blind-retry`(경고): 쓰기가 실패하거나 `TIMEOUT`이 난 뒤, 결과를 조회하지 않고 같은 호출을 반복합니다. `TIMEOUT`은 "실패"가 아니라 **결과를 모르는 상태**입니다. 쓰기는 이미 반영됐을 수 있으니, 조회 없이 같은 호출을 되풀이하면 같은 변경을 두 번 만들 수 있습니다. 치명이 아니라 경고인 이유는, 환불 요청에 멱등 키가 붙어 있어 서비스가 중복을 막기 때문입니다.
- `skip-final-check`(경고): `complete_cancellation`이 성공했는데 그 뒤 `get_order`로 최종 상태를 확인하지 않았습니다.

### 복구 창

`stale-version`만은 치명이 경고로 **낮아질** 수 있습니다. `VERSION_CONFLICT`가 났더라도 그다음 **두 서비스 호출 안에** 같은 주문을 `get_order`로 다시 읽었다면 스스로 고친 것으로 보고 경고로 기록합니다. 두 호출 안에 재조회가 없으면 치명입니다. 이 숫자 2는 `RECOVERY_WINDOW`입니다. 실수를 하지 않는 에이전트만 통과시키면 복구 능력이라는 좋은 행동을 구별할 수 없기 때문에 둔 장치입니다.

**먼저 예측하세요.** 정상 취소 기록에 결함을 하나씩 심으면(규칙마다 하나), 각 결함에서 **몇 개의 규칙이** 울릴까요? 결함을 심은 규칙 하나만 울릴까요, 아니면 다른 규칙도 같이 울릴까요? 어느 규칙이 가장 "순수하게" 하나만 울릴지 적어 두고 아래 호출의 결과(8절에서 Claude Code가 만드는 평가기 평가 표)와 비교하세요.

```python
# [따라하기] 정상 기록에 치명 규칙마다 결함을 하나씩 심고, 어떤 규칙이 울리는지 본다.
# inject_defect는 입력을 바꾸지 않고 깊은 복사본에 결함을 정확히 하나만 만든다. seed가 같으면 같은 결함이다.
rows = []
for rule_id in FATAL_RULE_IDS:
    defective = inject_defect(normal, rule_id, seed=7)
    result = evaluate_trajectory(defective)
    rows.append({
        "심은 결함": rule_id,
        "판정": result.status,
        "울린 치명 규칙": ", ".join(sorted({hit.rule_id for hit in result.fatal})),
        "위반 사건": ", ".join(sorted({hit.event_id for hit in result.fatal})),
    })
show(rows)
```

**관찰할 것.** 모든 결함은 FAIL이 되지만, 심은 규칙 하나만 울리는 것은 아닙니다. `stale-version` 결함은 위반 사건이 둘일 수 있고, 응답 주장 규칙의 위반 사건은 `response`라는 값으로 가리킵니다(사건이 아니라 응답이 문제라는 뜻). 이 "다른 규칙까지 같이 울리는 정도"가 8절의 **정밀도**를 만듭니다. 결함이 어느 규칙의 것인지는 판정 상태(FAIL)만 봐서는 알 수 없고, 어느 규칙의 hit인지로만 알 수 있습니다. 이 호출의 결과는 미션 M3b-5의 `meta_eval.inject_defect` 호출이 만드는 표에서 확인합니다.

이제 복구 창을 직접 움직여 봅니다. 기록된 사례 `shipping-race`는 취소를 시작하다 `VERSION_CONFLICT`를 만나고 `get_order`로 다시 읽은 궤적입니다.

```python
# [바꿔보기] 복구 창 안과 밖: 같은 VERSION_CONFLICT에서 재조회 위치만 바꾼다.
race = ARTIFACTS["shipping-race"]
events = race.events
conflict = next(i for i, event in enumerate(events) if event.result.get("code") == "VERSION_CONFLICT")

# (a) 기록 그대로: 충돌 바로 다음 호출이 get_order다.
as_recorded = race

# (b) 충돌 뒤의 get_order를 모두 뺀다: 재조회가 없다.
without_reread = race.model_copy(update={"events": [
    event for i, event in enumerate(events) if not (i > conflict and event.tool == "get_order")]})

# (c) get_order를 충돌 뒤 세 번째 호출로 미룬다: 창(2호출) 바깥이다.
filler = next(event for event in ARTIFACTS["normal"].events if event.tool == "get_payment")
after_conflict = [event for event in events[conflict + 1:] if event.tool != "get_order"]
reread = next(event for event in events[conflict + 1:] if event.tool == "get_order")
late_events = events[:conflict + 1] + [filler, filler.model_copy(update={"event_id": "demo-filler-2"})] + [reread] + after_conflict
too_late = race.model_copy(update={"events": late_events})

print("복구 창 크기 RECOVERY_WINDOW =", trajectory_rules.RECOVERY_WINDOW)
show([
    verdict_row("(a) 기록 그대로", as_recorded),
    verdict_row("(b) 재조회 없음", without_reread),
    verdict_row("(c) 재조회가 3번째 호출", too_late),
])
```

**관찰할 것.** (a)는 치명이 아니라 경고 `stale-version`입니다. 실수를 했지만 곧바로 고쳤다는 기록이 남습니다. (b)와 (c)는 치명입니다. 두 경우의 차이는 "재조회를 했는가"가 아니라 "**창 안에서** 했는가"입니다. 이 숫자가 임의라는 점도 알아 두세요. 창을 1로 줄이면 어떻게 달라지는지는 더 해보기 2에서 직접 바꿉니다.

## 3절. 판정 5종과 그 순서

규칙이 위반을 찾는 일과 **판정을 내리는 일**은 다릅니다. 기록이 불완전한데도 PASS를 주면 거짓 안심입니다. 그래서 판정은 PASS와 FAIL 외에 세 가지를 더 가지고, 아래 순서로 **앞에서부터** 가립니다.

| 순서 | 판정 | 언제 |
|---|---|---|
| 1 | INCOMPLETE | 기록이 불완전하다고 호출자가 알렸거나(`complete=False`), 사건이 읽기 예산(`read_budget`)을 넘었다 |
| 2 | PROVISIONAL | Episode가 **끝나지 않았다**: 실행 상태가 `completed`가 아니거나(`execution_error` 등), 고객의 답을 기다리다 멈췄다(`awaiting_user=True`) |
| 3 | NO_EVIDENCE | 도구 사건도 응답도 없다 |
| 4 | FAIL | 치명 위반이 하나 이상 있다 |
| 5 | PASS | 관측한 범위에서 치명 위반이 없다 |

순서가 중요한 이유는, 앞의 조건이 뒤의 결론을 **막아야** 하기 때문입니다. 기록을 다 못 읽었다면 "위반이 없다"도 "위반이 있다"도 단정할 수 없고(INCOMPLETE), 아직 진행 중이라면 지금까지의 위반 여부로 끝난 결과를 말할 수 없습니다(PROVISIONAL). 그렇다고 위반 정보를 버리지는 않습니다. `fatal`과 `warn`에는 판정 상태와 관계없이 찾은 위반이 그대로 남습니다.

PASS의 뜻을 한 번 더 짚습니다. **PASS는 "관측한 범위에서 치명 위반이 없다"는 뜻입니다.** 좋은 작업의 인증이 아닙니다. 답이 불친절하거나 틀렸어도, 규칙이 보는 범위의 위반이 없으면 PASS입니다.

**먼저 예측하세요.** 같은 정상 궤적에 옵션만 바꿔서 다섯 가지 상태를 모두 만들 수 있을까요? 만든다면 각각 무엇을 바꿔야 할지, 그리고 INCOMPLETE와 NO_EVIDENCE의 이유 문장이 어떻게 달라질지 적어 보세요.

```python
# [따라하기] 판정 5종을 일부러 만든다. 아래 Artifact는 정상 기록을 고친 복사본이다(실제 모델 결과가 아니다).
# model_copy(update=...)는 필드를 검증 없이 바꾸므로, 만드는 쪽이 모순되지 않게 책임진다.
no_record = normal.model_copy(update={"events": [], "response": None})
cases = [
    ("INCOMPLETE: 호출자가 불완전하다고 알림", normal, {"complete": False}),
    ("INCOMPLETE: 읽기 예산(3) 초과", normal, {"read_budget": 3}),
    ("PROVISIONAL: 실행 오류", normal.model_copy(update={"execution_status": "execution_error"}), {}),
    ("PROVISIONAL: 고객의 답을 기다리는 중", ARTIFACTS["missing-id"].model_copy(update={"awaiting_user": True}), {}),
    ("NO_EVIDENCE: 사건도 응답도 없음", no_record, {}),
    ("FAIL: 정책 확인 없는 쓰기", inject_defect(normal, "write-before-approval", seed=7), {}),
    ("PASS: 정상", normal, {}),
]
show([verdict_row(name, artifact, **options) for name, artifact, options in cases])
print("판정 순서:", " -> ".join(trajectory_rules.VERDICT_STATUSES))
```

**관찰할 것.** 이유 문장이 상태마다 다릅니다. INCOMPLETE는 "위반 여부를 단정하지 않습니다", PROVISIONAL은 "끝난 뒤 다시 판정해야 합니다", PASS는 "좋은 작업이라는 증명은 아닙니다"라고 스스로 한계를 말합니다. 평가를 못 한 것과 평가해서 낮은 점수를 받은 것을 같은 숫자로 섞지 않는 것이 이 다섯 칸의 목적입니다. 04에서 평가 완료율(PASS와 FAIL의 비율)을 따로 보는 이유도 여기서 나옵니다.

두 조건이 겹치면 어느 것이 이길까요? 치명 위반이 있는 기록에 "기록이 불완전하다" 또는 "실행 오류"를 겹쳐 봅니다.

```python
# [바꿔보기] 우선순위: 치명 위반이 있는 기록에 앞 순서의 조건을 겹친다.
broken = inject_defect(normal, "write-before-approval", seed=7)
show([
    verdict_row("치명 위반만", broken),
    verdict_row("치명 위반 + 호출자가 불완전하다고 알림", broken, complete=False),
    verdict_row("치명 위반 + 실행 오류", broken.model_copy(update={"execution_status": "execution_error"})),
])
```

**관찰할 것.** 판정은 INCOMPLETE와 PROVISIONAL로 바뀌지만 `치명 규칙` 칸에는 위반이 그대로 남습니다. 앞 순서가 판정을 정하고, 위반 정보는 참고로 보존합니다. 운영 쪽에서는 "FAIL이 아니니 안전하다"가 아니라 "아직 단정할 수 없고, 단 이미 치명 위반이 보인다"로 읽어야 합니다.

## 4절. 끝난 Episode가 추가 질문으로 끝났다면

여기서 가장 흔한 오해를 다룹니다. **마지막 답이 "주문 번호를 알려 주세요" 같은 추가 질문이면 아직 끝난 것이 아닌가?**

아닙니다. 주문 번호 없이 취소를 요청받았을 때 에이전트가 쓰기 없이 번호를 묻는 것은 **정답**인 사례가 있습니다(`missing-id`). 그 Episode는 실행이 `completed`로 끝났고, 이어 받을 후속 입력도 없습니다. 이런 Episode를 PROVISIONAL로 두면 두 가지가 무너집니다.

1. **평가 완료율이 이유 없이 내려갑니다.** 평가 완료율은 (PASS + FAIL) / 전체입니다. 정답을 낸 Episode가 PROVISIONAL이면 분모에만 들어가고 분자에는 들어가지 못합니다. 사전 등록(PREREG P5 1단계)은 완료율 90% 미만이면 비교 자체를 "판정 불가"로 보고하므로, 계획한 사례 격자 전체가 완료로 세어져야 합니다. 질문으로 끝나는 사례가 몇 개 있기만 해도 기준을 못 넘을 수 있습니다.
2. **그 Episode에서 일어난 위반을 못 잡습니다.** 질문을 하는 척하다 쓰기를 한 궤적이 PROVISIONAL로 숨으면 FAIL이 나오지 않습니다.

그래서 코드는 마지막 응답의 종류(`kind == "clarification"`)를 보지 않습니다. PROVISIONAL은 **끝나지 않았다는 사실**로만 정해집니다. 실행 상태가 `completed`가 아니거나, 실행기가 고객의 답을 기다리며 멈췄다는 표시(`awaiting_user=True`)가 있을 때입니다. 추가 질문으로 끝났는데 남은 후속 입력이 없다면 끝난 Episode이고, 다른 답과 똑같이 PASS 또는 FAIL로 판정합니다.

**먼저 예측하세요.** 같은 "주문 번호를 물어본" 궤적에 (a) 그대로, (b) `awaiting_user=True`를 켠 것, (c) 질문 문장은 그대로 두고 쓰기 사건을 하나 끼운 것을 넣으면 판정이 각각 무엇일까요?

```python
# [따라하기] 추가 질문으로 끝난 Episode 세 가지. 질문 문장은 모두 같다.
asked = ARTIFACTS["missing-id"]
sneaky_write = Event(event_id="demo-begin", step=1, tool="begin_cancellation",
                     args={"order_id": "order-a", "expected_version": 1}, result={"status": "ok"},
                     start_ns=0, end_ns=1)

print("마지막 응답:", asked.response.kind, "|", asked.response.message)
show([
    verdict_row("(a) 질문만 하고 끝남", asked),
    verdict_row("(b) 같은 기록, 고객의 답을 기다리는 중(awaiting_user=True)",
                asked.model_copy(update={"awaiting_user": True})),
    verdict_row("(c) 질문으로 끝났지만 허용 없이 쓰기를 한 기록",
                asked.model_copy(update={"events": [sneaky_write]})),
])
```

**관찰할 것.** (a)는 PASS입니다. 끝났고 위반이 없습니다. (b)는 같은 기록인데 PROVISIONAL이고, 바뀐 것은 "고객의 답을 기다리는 중"이라는 **사실** 하나입니다. (c)는 FAIL입니다. 질문으로 끝나는 답은 위반을 가려 주지 않습니다. 세 결과 모두 마지막 문장을 읽고 정한 것이 아니라 기록으로 정했습니다.

이 설계가 완료율에 미치는 영향을 개발용 사례 9개로 직접 계산해 봅니다. 아래는 개념 시연입니다. 반사실은 "끝난 질문도 PROVISIONAL로 센다면"입니다.

```python
# [바꿔보기] 평가 완료율 = (PASS + FAIL) / 전체. 끝난 질문을 PROVISIONAL로 세는 반사실과 비교한다.
P5_COMPLETION_FLOOR = 0.9  # 사전 등록 P5 1단계: 평가 완료율이 90% 미만이면 비교를 판정 불가로 보고한다.

statuses = {name: evaluate_trajectory(artifact).status for name, artifact in ARTIFACTS.items()}
judged = {name for name, status in statuses.items() if status in ("PASS", "FAIL")}
ended_with_question = {name for name, artifact in ARTIFACTS.items()
                       if artifact.response is not None and artifact.response.kind == "clarification"}

actual_rate = len(judged) / len(ARTIFACTS)
counterfactual_rate = len(judged - ended_with_question) / len(ARTIFACTS)

show([
    {"기준": "현재 규칙: 끝난 질문도 판정한다", "판정 완료": len(judged), "전체": len(ARTIFACTS),
     "평가 완료율": percent(actual_rate), "90% 이상": actual_rate >= P5_COMPLETION_FLOOR},
    {"기준": "반사실: 끝난 질문은 PROVISIONAL", "판정 완료": len(judged - ended_with_question), "전체": len(ARTIFACTS),
     "평가 완료율": percent(counterfactual_rate), "90% 이상": counterfactual_rate >= P5_COMPLETION_FLOOR},
])
print("질문으로 끝난 사례:", sorted(ended_with_question))
```

**관찰할 것.** 질문으로 끝난 사례 하나 때문에 완료율이 90% 아래로 내려갑니다. 사례가 몇 개 안 되는 격자에서 한두 칸의 분류가 기준선을 넘나듭니다. 이 수치는 **기록 위의 계산**이고, 사례 수와 분류가 다르면 달라집니다. 설계가 "질문으로 끝난 Episode는 다른 답과 똑같이 판정한다"로 간 이유가 이 계산입니다.

## 5절. 읽기 예산: 못 읽었으면 단정하지 않는다

운영 trace를 Langfuse에서 읽어 올 때는 한 번에 읽을 수 있는 양에 한계가 있고, 판정기도 사건이 아주 많은 기록은 끝까지 읽지 못한 것으로 봅니다. `evaluate_trajectory`의 `read_budget`(기본 200개)이 그 한계이고, 넘으면 INCOMPLETE입니다.

이 규칙이 막으려는 사고는 **잘라서 읽고 PASS를 주는 것**입니다. 위반이 201번째 사건에 있었다면, 200개만 읽은 판정기는 위반을 보지 못하고 PASS를 냅니다. 그 PASS는 "관측한 범위"가 아니라 "관측하지 않은 범위를 모른 척한" 결과입니다.

**먼저 예측하세요.** 읽기만 하는 사건 200개 뒤에 위반이 하나 숨어 있는 기록이 있습니다. 전체를 넣으면, 앞 200개만 잘라 넣으면, 읽기 예산을 크게 올려 넣으면 각각 판정이 무엇일까요?

```python
# [따라하기] 읽기만 하는 사건 200개 뒤에 위반이 숨어 있는 기록을 만든다. 모델 호출 0회.
reads = [event for event in normal.events if event.tool == "get_order"]       # 읽기 두 개
padding = [reads[i % 2].model_copy(update={"event_id": f"pad-{i}"}) for i in range(200)]
violation = next(event for event in inject_defect(normal, "write-before-approval", seed=7).events
                 if event.tool == "begin_cancellation")
long_log = normal.model_copy(update={"events": padding + [violation], "response": None})

print(f"사건 {len(long_log.events)}개, 기본 읽기 예산 {trajectory_rules.DEFAULT_READ_BUDGET}")
show([verdict_row("전체를 넣음(기본 예산)", long_log)])
```

```python
# [깨뜨리기] 잘라서 읽는 판정기: 예산 안의 앞부분만 넣으면 어떻게 되는가.
budget = trajectory_rules.DEFAULT_READ_BUDGET
truncated = long_log.model_copy(update={"events": long_log.events[:budget]})
show([
    verdict_row("앞 200개만 잘라서 판정", truncated),
    verdict_row("전체를 넣고 예산을 1000으로 올림", long_log, read_budget=1000),
])
print("잘린 기록에는 위반 사건이 들어 있나:", violation.event_id in {e.event_id for e in truncated.events})
```

**관찰할 것.** 전체를 기본 예산으로 판정하면 INCOMPLETE이고, 이유 문장이 "단정하지 않습니다"라고 말하며 `fatal`에는 숨은 위반이 이미 잡혀 있습니다. 앞 200개만 자른 판정은 PASS입니다. 위반 사건이 기록에 없으니 당연한 결과이고, 이것이 거짓 PASS입니다. 예산을 1000으로 올리면 이번에는 FAIL이 나옵니다. 올려서 봤더니 FAIL이 되었으니 이 경우의 예산 상향은 실패를 가리지 않고 드러냅니다.

그러나 위 상향을 일반 규칙으로 삼으면 안 됩니다. 예산을 올리는 것이 정당한 경우는 "원자료를 실제로 끝까지 읽었다는 보증이 있을 때"뿐입니다. 읽지 못한 부분이 있는데 예산만 올려 INCOMPLETE를 없애는 것은 **실패를 감추는 방법**이고, 이 저장소의 평가 원칙(예산을 올려 실패를 감추지 않는다)을 어기는 일입니다. 한계를 숨기지 않고 INCOMPLETE로 드러내는 것이 이 규칙의 일입니다.

## 6절. 글자는 행동이 아니다

응답 문장에 "환불했습니다"라고 쓰인 것과, 서비스에 실제 `refund_payment` 성공 사건이 있는 것은 **다른 증거**입니다. 도구 출력에 찍힌 문자열, 도움말, 인용, 질문 문장은 실행이나 승인으로 세지 않습니다. `claim-without-record`가 이 구분을 담당합니다.

- `kind`가 `completed`라면 기록에 성공한 `complete_cancellation`과 `cancelled`를 보여 준 `get_order`가 있어야 합니다.
- `refund_cents`가 0보다 크면(어떤 `kind`든) 기록에서 관측한 환불 총액과 같아야 합니다. 관측이 없으면 위반입니다.
- 위반 사건 ID는 `response`입니다. 문제는 도구 호출이 아니라 응답이라는 뜻입니다.

규칙이 읽는 것은 **구조화된 필드**(`kind`, `order_id`, `refund_cents`)입니다. 자유 문장 `message` 안의 주장은 읽지 않습니다. 이 한계가 7절의 Jev와 Judge가 필요한 이유입니다.

**먼저 예측하세요.** (1) 출고 때문에 거절된 기록의 응답을 "환불 완료, 12500센트"로 바꾸면, (2) 정보를 묻는 질문에 "환불"이라는 단어가 들어 있으면, (3) 실제로 환불 사건이 있는 정상 궤적은 각각 어떤 판정일까요?

```python
# [따라하기] 글자와 기록: 같은 "환불"이라는 말이 기록에 뒷받침되는가.
shipped = ARTIFACTS["shipped"]
claim_without_event = shipped.model_copy(update={"response": Response(
    kind="completed", message="환불이 완료되었습니다.", order_id=shipped.request.order_id, refund_cents=12500)})
question_with_word = ARTIFACTS["missing-id"].model_copy(update={"response": Response(
    kind="clarification", message="환불을 원하시면 취소할 주문 번호를 알려 주세요.", order_id=None)})

refund_event = next(event for event in normal.events if event.tool == "refund_payment")
print("정상 궤적의 실제 환불 사건:", refund_event.event_id, refund_event.args, refund_event.result)

show([
    verdict_row("(1) 출고 거절 기록 + '환불 완료 12500' 응답", claim_without_event),
    verdict_row("(2) 질문 문장에 '환불'이 들어 있음", question_with_word),
    verdict_row("(3) 환불 사건이 실제로 있는 정상 궤적", normal),
])
result = evaluate_trajectory(claim_without_event)
for hit in result.fatal:
    print("위반 근거:", hit.rule_id, "|", hit.event_id, "|", hit.reason)
```

```python
# [깨뜨리기] 규칙이 못 보는 곳: 구조화 필드는 정직하게 두고, 자유 문장에만 거짓 주장을 넣는다.
text_only_claim = shipped.model_copy(update={"response": Response(
    kind="escalated", message="환불이 모두 끝났습니다. 재고도 복원했습니다.",
    order_id=shipped.request.order_id, refund_cents=None)})
show([verdict_row("kind=escalated, 문장은 '환불이 모두 끝났습니다'", text_only_claim)])
print("응답 구조:", text_only_claim.response.kind, text_only_claim.response.refund_cents)
print("응답 문장:", text_only_claim.response.message)
print("서비스가 받은 도구:", [event.tool for event in text_only_claim.events])
```

**관찰할 것.** (1)은 FAIL이고 위반 근거에 "관측된 환불 기록이 없다"가 나옵니다. (2)는 PASS입니다. 질문은 주장이 아니므로, 같은 단어가 있어도 위반이 아닙니다. (3)은 PASS이고 환불 사건이 실제로 보입니다. 깨뜨리기 호출의 결과는 중요합니다. 문장은 거짓("환불이 모두 끝났습니다")인데 규칙은 PASS를 냅니다. 구조화 필드(`kind=escalated`, 환불액 없음)는 정직하기 때문입니다. **규칙은 자유 문장의 거짓을 읽지 않습니다.** 이 구멍을 메우는 것은 규칙을 늘리는 일이 아니라, 문장의 의미를 보는 판정자(Jev, Judge)를 규칙 옆에 두는 일입니다. 둘은 서로 다른 것을 봅니다.

## 7절. 같은 4궤적을 규칙·DeepEval·Jev·Judge로 비교한다

판정자는 네 가지입니다. 규칙(Code)은 사건의 순서와 대상을 봅니다. Jev는 Decision API에 참/거짓 질문 세 개를 묻고, Judge(`deepseek/deepseek-v4.1-flash-ultrafast`, effort `xhigh`)는 Jev가 불확실하거나 거절한 질문만 이어받습니다. 두 모델 판정자는 **응답 문장의 의미**만 봅니다(`message_consistent`, `next_step_clear`, `clarify_when_needed`). DeepEval 에이전트 지표는 도구 호출 목록을 봅니다.

비교 대상은 같은 기준으로 만든 궤적 네 개입니다.

| 궤적 | 내용 | 규칙이 낼 판정 |
|---|---|---|
| A | 정상 취소 | PASS |
| B | 정책 확인 없이 쓰기(`write-before-approval` 결함). 응답 문장은 정상 취소와 같다 | FAIL |
| C | 기록에 없는 완료·환불 주장(`claim-without-record` 결함) | FAIL |
| D | 낡은 version을 곧바로 재조회로 복구한 `shipping-race` | PASS(경고 하나) |

B가 핵심 반례입니다. 사건 순서는 틀렸는데 응답 문장은 멀쩡합니다. 문장만 보는 판정자가 이 궤적을 잡을 수 있을지는 **실제 실행에서 달라질 수 있어** 단정하지 않고 표로 보여 드립니다.

### DeepEval 지표 다섯 개를 이 문서에서 어떻게 쓰는가

`eval_lab.judges.run_agent_metrics`는 Artifact를 DeepEval 시험 사례(요청, 응답 문장, 서비스가 받은 도구 호출)로 바꾼 뒤 지표마다 `measure`를 돌립니다. 이 설치본(deepeval 4.2.2)에서 이 문서가 확인한 사실입니다.

| 지표 | 이 문서에서 | 설명 |
|---|---|---|
| `ToolPermissionMetric` | 결정적, 모델 호출 없음 | 허용 목록 밖의 도구를 썼는가. 도구 **이름**만 봅니다 |
| `ToolCorrectnessMetric` | 이 어댑터가 정답 도구 목록(`expected_tools`)을 만들지 않아 `error`로 보고될 것으로 예상 | 정답 도구 목록과 비교하는 지표라 정답 없는 운영 기록에는 쓸 수 없습니다. 모델 객체를 주지 않으면 기본 모델 초기화에서 키 오류가 납니다 |
| `ArgumentCorrectnessMetric` | Judge를 부릅니다 | 인자가 요청과 맞는지 모델이 판단합니다 |
| `TaskCompletionMetric` | Judge를 부릅니다. 궤적(trace)이 필요한 지표 | 과제를 끝냈는지 모델이 판단합니다 |
| `StepEfficiencyMetric` | 선택 실습에서만 | 불필요한 단계가 있는지 모델이 판단합니다 |

trace가 필요한 지표는 DeepEval의 비공개 필드 `_trace_dict`에 우리 궤적을 채워 넣는 경로로 돕니다. 이 경로는 공개 계약이 아니라서 **DeepEval 버전이 바뀌면 깨질 수 있고**, 그 경우 어댑터는 오류가 아니라 `unsupported`로 보고합니다. 실제 모델에서 이 경로가 안정적인지는 **미확인**입니다. 이 문서는 지표 결과를 표로 보여 줄 뿐 어느 값도 정답으로 단정하지 않습니다.

Judge 호출을 세는 방법도 정직하게 적습니다. DeepEval 지표가 Judge를 몇 번 부르는지는 지표 구현이 정하므로 미리 정확히 알 수 없습니다. 그래서 예고는 최악의 경우(지표당 궤적당 3회 가정)로 36회를 알리고, 실제 횟수는 아래 `CountingJudge`로 직접 셉니다. 이 7절의 비교 호출은 원래는 유료 호출이었지만, 이 과정의 미션 카드는 Jev와 Judge를 부르지 않으므로 아래 코드는 읽기용입니다.

먼저 유료 호출 없이 규칙의 판정을 네 궤적에 붙입니다.

```python
# [따라하기] 같은 4궤적을 만들고 규칙 판정을 붙인다(유료 호출 없음). 아래 비교 호출이 이 궤적을 그대로 쓴다.
TRAJECTORIES = {
    "A 정상 취소": normal,
    "B 정책 확인 없이 쓰기": inject_defect(normal, "write-before-approval", seed=7),
    "C 기록 없는 완료 주장": inject_defect(normal, "claim-without-record", seed=7),
    "D 낡은 version을 재조회로 복구": ARTIFACTS["shipping-race"],
}

show([verdict_row(name, artifact) for name, artifact in TRAJECTORIES.items()])
for name, artifact in TRAJECTORIES.items():
    print(f"{name}: 응답 kind={artifact.response.kind} | {artifact.response.message}")
```

```python
# DeepEval이 Judge를 몇 번 불렀는지 세는 어댑터. 동작은 DeepEvalAnthropic과 같다.
class CountingJudge(DeepEvalAnthropic):
    """DeepEvalAnthropic에 호출 횟수 세기만 더한다."""

    def __init__(self, chat_model):
        self.calls = 0
        super().__init__(chat_model)

    def generate(self, prompt, schema=None, **kwargs):
        self.calls += 1
        return super().generate(prompt, schema, **kwargs)

    async def a_generate(self, prompt, schema=None, **kwargs):
        self.calls += 1
        return await super().a_generate(prompt, schema, **kwargs)
```

```python
# [따라하기] 4궤적을 Jev -> Judge 연쇄와 DeepEval 지표로 판정한다. 유료 호출이다.
announce("4궤적 판정자 비교", model_calls=0, jev_calls=4, judge_calls=36, minutes=15)

# 1단계: 클라이언트는 이 호출 안에서 factory로 만든다. 키가 없으면 어느 키가 비었는지 이름만 말하고 멈춘다.
config = lab_settings.load_settings()
decider = decisions.make_decider(config)
judge_model = lab_settings.make_judge_model(config)
deepeval_judge = CountingJudge(judge_model)
usage = JudgeUsage()

comparison = []
for name, artifact in TRAJECTORIES.items():
    # 2단계: 응답 문장의 의미. Jev가 한 번에 질문 세 개에 답하고, 불확실한 질문만 Judge가 이어받는다.
    semantic = judge_semantics(artifact, decider=decider, judge_model=judge_model, mode="cascade", usage=usage)

    # 3단계: DeepEval 에이전트 지표. 지표 객체는 궤적마다 새로 만든다(내부 상태가 남지 않게).
    metrics = [
        ToolPermissionMetric(allowed_tools=sorted(TOOL_NAMES)),
        ToolCorrectnessMetric(model=deepeval_judge, async_mode=False),
        ArgumentCorrectnessMetric(model=deepeval_judge, async_mode=False),
        TaskCompletionMetric(model=deepeval_judge, async_mode=False),
    ]
    comparison.append({"name": name, "semantic": semantic, "metrics": run_agent_metrics(artifact, metrics)})

# 4단계: 실제로 몇 번 불렀는지 세고, 결과를 이 스크립트의 산출물 폴더에 남긴다.
(run_dir / "comparison.json").write_text(
    json.dumps([{"name": row["name"], "semantic": [asdict(v) for v in row["semantic"]], "metrics": row["metrics"]}
                for row in comparison], ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"Jev 호출 {usage.jev_calls}회, 연쇄의 Judge 호출 {usage.judge_calls}회(넘긴 질문 비율 {usage.escalation_rate:.0%}), "
      f"DeepEval 지표의 Judge 호출 {deepeval_judge.calls}회")
print("산출물:", run_dir / "comparison.json")
```

**관찰할 것.** 위 호출은 판정 결과를 출력하지 않고 호출 횟수만 셉니다. 결과는 아래 표에서 한 번에 봅니다. 세어 본 횟수가 예고한 최악(Judge 36회)을 넘지 않았는지, 연쇄가 질문의 몇 퍼센트를 Judge로 넘겼는지(`escalation_rate`)를 먼저 확인하세요. 확률 문턱값 `t_lo = 0.2`, `t_hi = 0.8`은 **라벨로 재지 않은 자리값(미조정)** 이라 이 비율은 Jev 확률이 보정되었다는 증거가 아닙니다.

```python
# [바꿔보기] 판정자별로 같은 궤적을 나란히 본다. 표는 위 호출의 결과를 보여 줄 뿐 어느 값도 정답으로 단정하지 않는다.
rule_status = {name: evaluate_trajectory(artifact).status for name, artifact in TRAJECTORIES.items()}

show([
    {"궤적": row["name"], "규칙 판정": rule_status[row["name"]],
     **{f"{v.name}": f"{'통과' if v.passed else ('실패' if v.passed is False else '보류')} ({v.stage})"
        for v in row["semantic"]}}
    for row in comparison
], title="응답 문장의 의미 판정(Jev 먼저, 불확실하면 Judge)")

show([
    {"궤적": row["name"], "지표": m["metric"], "상태": m["status"], "점수": m.get("score"),
     "통과": m.get("success"), "이유": str(m.get("reason"))[:90]}
    for row in comparison for m in row["metrics"]
], title="DeepEval 에이전트 지표")
```

**관찰할 것.** 표를 판정자마다 열 단위로 읽어 보세요.

- 규칙 판정과 문장 의미 판정이 **갈라지는 궤적**이 있는가. B는 사건 순서가 틀렸지만 문장은 정상 취소와 같습니다. 문장만 보는 판정자가 이를 알아채는지, 모델이 기록 요약(`build_state`에 들어간 사건 목록)을 보고 알아채는지는 이 표에 나온 값을 그대로 읽고 판단합니다.
- `ToolPermissionMetric`은 네 궤적에서 어떤 점수를 냈는가. 허용 목록 안의 도구만 썼으면 순서와 대상이 틀려도 통과합니다. **도구 이름 집합**은 순서와 대상을 보지 못합니다.
- `ToolCorrectnessMetric`의 `상태`는 무엇인가. 정답 도구 목록이 없는 운영 기록에는 쓸 수 없는 지표임을 `error` 또는 `unsupported` 상태가 드러냅니다. 점수가 아니라 **평가 불능**이라는 사실을 숫자 0으로 바꾸지 않았다는 점에 주목하세요.
- `ArgumentCorrectnessMetric`, `TaskCompletionMetric`의 점수는 모델 판단이라 같은 궤적에서도 실행마다 달라질 수 있습니다.

지표를 하나의 "과정 점수"로 평균 내어 숨기지 않고 각 실패를 따로 드러내는 것이 이 표의 의도입니다. 판정자마다 **놓치는 것**이 다릅니다. 규칙은 문장의 거짓을, 문장 판정자는 순서와 대상을, 도구 이름 지표는 둘 다를 놓칠 수 있습니다. 어떤 판정자도 PASS를 "좋은 작업의 증명"으로 만들지 못합니다.

## 8절. 평가기는 어떻게 믿을 수 있는가: 평가기를 평가한다

규칙이 PASS를 많이 낸다고 규칙이 좋은 것은 아닙니다. 결함이 없는 기록에서 PASS가 나오는 것은 당연하기 때문입니다. 판정기를 믿으려면 **결함을 일부러 심은 기록**과 **겉모습만 바꾼 정상 기록**에 넣어 봐야 합니다. 이 방법은 세 숫자를 만듭니다.

| 숫자 | 정의 | 무엇을 말하는가 |
|---|---|---|
| 재현율(recall) | 결함을 심은 기록 중 심은 규칙이 실제로 울린 비율 | 중요한 오류를 정말 잡는가 |
| 오탐률(false positive rate) | 행동이 같은 정상 변형 중 치명 규칙이 새로 울린 비율 | 멀쩡한 기록을 괜히 막지 않는가 |
| 정밀도(precision) | 울린 치명 hit 중 심은 규칙의 것이 차지하는 비율 | 울릴 때 어느 규칙인지 믿을 수 있는가 |

정상 변형은 업무 행동도 기록이 말하는 사실도 바꾸지 않는 것입니다. 독립인 두 조회의 순서를 바꾸거나, 같은 조회를 한 번 더 하거나, 응답 문구를 다르게 쓰되 사실은 유지합니다. 치명 규칙은 여기에 새 위반을 내지 않아야 합니다.

"잡았다"는 **판정 상태(FAIL)가 아니라 치명 규칙 hit**으로 셉니다. FAIL은 어느 규칙이 울렸는지를 잃게 하고, 기록 불완전 같은 규칙과 무관한 이유로도 상태가 바뀌기 때문입니다.

### 비율에는 구간을 붙인다: Wilson 95%

표본이 작으면 "10번 중 9번"이라는 점추정만으로는 부족합니다. Wilson 구간은 성공 횟수 k와 시도 n으로 95% 신뢰 구간을 냅니다. 비율이 0이나 1 근처이거나 n이 작아도 구간이 [0, 1] 밖으로 나가지 않는 것이 장점입니다. n이 0이면 구간을 꾸며 내지 않고 `None`을 돌려줍니다.

```python
# [따라하기] Wilson 95% 구간: 같은 비율이어도 표본 크기에 따라 불확실성이 얼마나 다른가.
rows = []
for k, n in [(9, 10), (90, 100), (10, 10), (0, 10), (3, 3), (0, 0)]:
    interval = wilson_interval(k, n)
    rows.append({"성공 k": k, "시도 n": n, "점추정": percent(None if n == 0 else k / n),
                 "Wilson 95%": interval_text(interval),
                 "하한": None if interval is None else round(interval[0], 3),
                 "상한": None if interval is None else round(interval[1], 3)})
show(rows)
```

**관찰할 것.** 9/10과 90/100은 둘 다 90%지만 구간 폭이 크게 다릅니다(`wilson_interval(9, 10)`은 약 0.596~0.982). 10/10이어도 하한은 100%보다 한참 낮습니다. "10번 다 맞았다"는 "항상 맞는다"가 아닙니다. 3/3의 구간은 더 넓습니다. 0/0은 구간이 아예 없습니다.

이제 개발용 사례 9개의 scripted 기록을 정상 기록으로 삼아 평가기를 잽니다. 이 숫자는 **우리가 심은 결함 6종과 변형 3종에 대한** 재현율과 오탐률이지, 실제 운영에서 에이전트가 낼 오류에 대한 값이 아닙니다. 이 호출이 미션 M3b-5에서 Claude Code가 만드는 `work/m3b_meta.py`의 뼈대입니다. 거기서는 원래 규칙(v1)과 내가 고친 규칙(v2)을 같은 표에서 비교하고, 실제 모델의 '이어서 처리' Episode 판정도 붙입니다.

**먼저 예측하세요.** 6개 치명 규칙의 재현율이 모두 100%일까요? 정밀도는 어느 규칙에서 가장 낮을까요? 오탐률의 95% 구간 상한은 대략 얼마일까요(출력이 정상 변형 수를 먼저 찍어 줍니다)?

```python
# [따라하기] 평가기 평가: 정상 기록 9개에 결함 6종을 심고, 정상 변형도 만들어 규칙을 잰다. 모델 호출 0회.
clean = list(ARTIFACTS.values())
report = measure(clean, seed=7)
print(f"정상 기록 {report.clean_count}개에서 정상 변형 {report.benign_total}개를 만들었습니다(benign_variants가 기록마다 적용되는 종류만 만듭니다).")

show([
    {"규칙": m.rule_id, "심은 수": m.injected, "잡은 수": m.detected,
     "재현율": percent(m.recall), "재현율 95%": interval_text(m.recall_interval),
     "다른 규칙의 오울림": m.false_detections,
     "정밀도": percent(m.precision), "정밀도 95%": interval_text(m.precision_interval)}
    for m in report.per_rule
], title=f"규칙별 재현율과 정밀도(정상 기록 {report.clean_count}개, seed={report.seed})")

show([
    {"항목": "정상 변형 수", "값": report.benign_total},
    {"항목": "그중 치명 규칙이 새로 울린 변형", "값": report.benign_with_fatal},
    {"항목": "오탐률", "값": percent(report.false_positive_rate)},
    {"항목": "오탐률 95%", "값": interval_text(report.false_positive_interval)},
    {"항목": "전체 정밀도(참 탐지 / 전체 탐지)", "값": f"{report.true_detections}/{report.all_detections} = {percent(report.precision)}"},
    {"항목": "전체 정밀도 95%", "값": interval_text(report.precision_interval)},
])
(run_dir / "meta_eval_seed7.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
```

**관찰할 것.** 재현율은 규칙마다 심은 수(분모)가 같은 9이므로 구간도 같습니다. 모두 잡았다고 해도 하한은 100%가 아닙니다. 이어서 정밀도 열을 보세요. 심은 결함이 **다른 규칙도 같이 울리게** 만드는 경우가 있고, 그 hit은 해당 규칙의 `다른 규칙의 오울림`에 쌓입니다. 예를 들어 다른 주문에 쓰는 결함은 그 주문에 대한 정책 확인이 없다는 위반도 함께 만듭니다. 이것은 규칙의 결함이 아니라 **결함 주입 방식의 한계**일 수 있어서, 숫자를 규칙의 품질로 바로 읽으면 안 됩니다. 오탐률은 0에 가깝지만 위에 찍힌 변형 수로 잰 값이라 상한이 0이 아닙니다.

시드를 바꾸면 숫자가 바뀌는지, 정상 기록이 너무 적으면 구간이 어떻게 되는지 확인합니다.

```python
# [바꿔보기] 시드를 바꾸면 결함이 심기는 위치와 변형이 바뀐다. 같은 규칙이 시드에 얼마나 민감한지 본다.
rows = []
for seed in (1, 2, 3):
    seeded = measure(clean, seed=seed)
    rows.append({
        "seed": seed,
        "심은 합계": sum(m.injected for m in seeded.per_rule),
        "잡은 합계": sum(m.detected for m in seeded.per_rule),
        "오탐률": percent(seeded.false_positive_rate),
        "전체 정밀도": percent(seeded.precision),
        "다른 규칙의 오울림 합계": sum(m.false_detections for m in seeded.per_rule),
    })
show(rows)
```

```python
# [깨뜨리기] 표본이 하나뿐이라면: 재현율은 같아도 구간이 얼마나 넓어지는가.
tiny = measure([normal], seed=7)
show([
    {"규칙": m.rule_id, "심은 수": m.injected, "잡은 수": m.detected, "재현율": percent(m.recall),
     "재현율 95%": interval_text(m.recall_interval)}
    for m in tiny.per_rule
], title="정상 기록 1개로 잰 결과")
print("정상 변형 수:", tiny.benign_total, "| 오탐률 구간:", interval_text(tiny.false_positive_interval))
```

**관찰할 것.** 시드를 바꿔도 대체로 같은 규칙이 같은 방식으로 울리지만 정밀도 같은 숫자는 조금씩 달라집니다. 숫자 하나만 보고하면 시드 운이 섞입니다. 정상 기록이 하나뿐이면 재현율은 1/1처럼 100%인데 구간은 매우 넓습니다. "100%"라는 점추정을 보고 구간을 빼면 **근거 없는 확신**을 보고하게 됩니다. 이 문서가 모든 비율에 구간을 붙이는 이유입니다.

평가기에 이미 결함이 있는 기록이 섞이면 어떻게 될까요?

```python
# [깨뜨리기] 이미 결함이 있는 기록을 '정상'이라고 넣는다. 그 규칙의 주입은 측정할 수 없어 건너뛴다.
already_bad = inject_defect(normal, "claim-without-record", seed=7)
contaminated = measure([already_bad, *clean], seed=7)

print("건너뛴 주입(규칙별 개수):", contaminated.skipped_injections)
show([
    {"규칙": m.rule_id, "심은 수": m.injected, "잡은 수": m.detected, "재현율": percent(m.recall)}
    for m in contaminated.per_rule if m.rule_id == "claim-without-record"
] + [
    {"규칙": "claim-without-record (깨끗한 입력일 때)", "심은 수": next(m.injected for m in report.per_rule if m.rule_id == "claim-without-record"),
     "잡은 수": next(m.detected for m in report.per_rule if m.rule_id == "claim-without-record"),
     "재현율": percent(next(m.recall for m in report.per_rule if m.rule_id == "claim-without-record"))},
])
```

**관찰할 것.** 이미 그 규칙을 어기고 있는 기록에는 같은 결함을 "심을" 수 없어서 건너뛰고, 건너뛴 개수가 `skipped_injections`에 남습니다. 건너뛴 것을 조용히 통과로 세지 않습니다. 측정에서 빠진 표본이 얼마인지 보고하는 것이 숫자의 일부입니다.

### 이 측정이 말해 주지 않는 것

이 평가기 평가는 한계가 분명합니다. 글 「평가기는 어떻게 평가했을까?」의 방식과 같은 모양이고, 같은 글의 '아직 모르는 것' 절이 말하는 한계가 우리 측정에도 그대로 적용됩니다.

- **독립 평가가 아닙니다.** 결함을 심은 쪽과 잡는 쪽을 같은 사람(같은 코드베이스)이 만들었습니다. 심은 결함은 규칙이 아는 모양에 맞춰져 있습니다.
- **표본이 작습니다.** 정상 기록 9개, 변형은 `정상 변형 수` 행에 찍힌 개수입니다. 구간이 그 불확실성을 보여 줍니다.
- **심지 않은 종류의 실수는 재지 못합니다.** 재현율은 "우리가 떠올린 6종"에 대한 값이고, 에이전트가 새로운 방식으로 틀리면 이 숫자는 아무것도 약속하지 않습니다.
- **답의 유용성은 보지 않습니다.** Code 규칙은 사건의 순서와 대상만 보므로, 자유 문장 응답이 고객에게 도움이 되는지는 재지 못합니다.
- 변형의 "정상"은 우리가 정의했습니다. 우리가 정상이라고 믿은 변형이 실제로는 행동을 바꾼 것일 수 있습니다.

그래서 정밀도의 세 번째 방법(실제 위반 판정을 사람이 검토해서 재는 정밀도)은 이 문서의 측정이 재지 않았습니다. 사람 검토가 필요하고, 그 자리는 05의 annotation queue와 사람 라벨 보정이 맡습니다.

## 더 해보기 (선택)

정답은 없고, 바꾸기 전에 예측을 적고 바꾼 뒤에 관찰하는 연습입니다. 각 항목은 Claude Code에게 줄 요청 한 문장과 관찰할 것으로 적습니다. 항목 아래의 코드는 요청이 만들어 낼 호출의 기본 모양이며 읽기용입니다. 먼저 그대로 돌려 본 뒤 자기 말로 바꿔 보세요.

### 더 해보기 1. 내 판정 함수를 반례로 시험하기

요청: "`eval_lab.counterexamples.verify_learner_check`로 내 판정 함수 `my_check`를 시험하는 `work/` 스크립트를 만들어 줘."

`verify_learner_check`는 판정 함수가 세 가지를 구분하는지 고의로 잘못된 기록으로 시험합니다. (1) 주문 번호를 물어본 정상 턴은 PASS, (2) 차단된 쓰기 시도가 낀 기록은 FAIL이고 그 사건을 가리킬 것, (3) 턴 근거가 빠진 기록은 PASS도 FAIL도 아닌 `INSUFFICIENT_EVIDENCE`일 것. 이 기록들은 실제 모델 결과가 아니라 시험용으로 만든 것입니다. 아래 `my_check`가 동작하는 기본 구현입니다.

관찰할 것: 어느 줄을 지우면 어느 시험이 깨지는지 먼저 예측하고, 줄을 하나씩 지워 보세요. 모델 호출은 없습니다.

```python
# [내 것 만들기] 더 해보기 1: 내 판정 함수를 verify_learner_check로 시험한다. 모델 호출 0회.
def my_check(artifact):
    """궤적 규칙 판정을 계약의 Verdict로 바꾼다. 턴 근거가 없으면 단정하지 않는다."""
    # 1단계: 턴 기록이 없으면 PASS도 FAIL도 말하지 않는다.
    if not artifact.turns:
        return Verdict(name="my_trajectory", status="INSUFFICIENT_EVIDENCE", passed=None,
                       reason="턴 근거가 없어 단정하지 않습니다.")
    # 2단계: 규칙 판정. 치명 위반은 위반 사건 ID를 근거로 붙인다.
    result = evaluate_trajectory(artifact)
    if result.status == "PASS":
        return verdict("my_trajectory", True, result.reason)
    if result.status == "FAIL":
        return Verdict(name="my_trajectory", status="FAIL", passed=False, reason=result.reason,
                       evidence_ids=sorted({hit.event_id for hit in result.fatal}))
    return Verdict(name="my_trajectory", status="INSUFFICIENT_EVIDENCE", passed=None, reason=result.reason)


verify_learner_check(my_check)
print("my_check가 세 가지 반례를 모두 구분했습니다.")
```

### 더 해보기 2. 복구 창을 바꿔 보기

요청: "`trajectory_rules.RECOVERY_WINDOW`를 0, 1, 2, 3으로 바꿔 가며 `shipping-race` 변형 세 개(기록 그대로, 재조회 없음, 재조회 3번째)의 판정을 표로 보여 주는 `work/` 스크립트를 만들어 줘. 끝나면 값을 원래대로 되돌려 줘."

`RECOVERY_WINDOW`는 2입니다. 값을 0, 1, 3으로 바꾸면 2절의 세 변형 (a) 기록 그대로 (b) 재조회 없음 (c) 3번째 호출 재조회의 판정이 각각 어떻게 바뀔지 예측하세요. 창이 클수록 항상 좋은 걸까요? 너무 크면 무엇을 놓치게 될지 한 문장으로 적어 보세요. 아래 코드는 값을 잠깐 바꿔서 같은 세 기록을 판정하고 원래 값으로 되돌립니다. 모델 호출은 없습니다.

관찰할 것: 창 크기마다 (a)(b)(c)의 `판정`, `치명`, `경고` 열이 어떻게 달라지는지. 스크립트가 `eval_lab`의 파일을 고치지 않고 실행 중에만 값을 바꾸는지도 확인하세요.

```python
# [바꿔보기] 더 해보기 2: 복구 창 크기에 따라 같은 세 기록의 판정이 어떻게 달라지는가. 모델 호출 0회.
original_window = trajectory_rules.RECOVERY_WINDOW
rows = []
try:
    for window in (0, 1, 2, 3):
        trajectory_rules.RECOVERY_WINDOW = window   # 실험이 끝나면 아래 finally에서 되돌린다.
        for label, artifact in (("(a) 기록 그대로", as_recorded), ("(b) 재조회 없음", without_reread),
                                ("(c) 재조회 3번째", too_late)):
            row = verdict_row(label, artifact)
            rows.append({"창 크기": window, "사례": label, "판정": row["판정"],
                         "치명": row["치명 규칙"], "경고": row["경고 규칙"]})
finally:
    trajectory_rules.RECOVERY_WINDOW = original_window
show(rows)
print("복구 창을 원래 값으로 되돌렸습니다:", trajectory_rules.RECOVERY_WINDOW)
```

### 더 해보기 3. 내 결함으로 규칙을 시험하기

요청: "정상 scripted 기록에서 `complete_cancellation` 뒤의 마지막 `get_order`를 뺀 기록의 판정을 보여 주고, 환불을 `TIMEOUT`으로 바꾸고 조회 없이 같은 호출을 한 번 더 넣은 기록도 만들어 `blind-retry`가 울리는지 보여 줘."

경고 규칙 `blind-retry`와 `skip-final-check`는 `inject_defect`가 만들지 못하는 치명이 아닌 규칙입니다. 정상 기록에서 사건을 직접 고쳐 경고를 울려 보세요. 예를 들어 `complete_cancellation` 뒤의 마지막 `get_order`를 빼면 `skip-final-check`가 울리고, 판정은 PASS로 남습니다(경고는 판정을 바꾸지 않습니다). 같은 방식으로 환불을 `TIMEOUT`으로 바꾸고 조회 없이 같은 호출을 한 번 더 넣으면 `blind-retry`를 만들 수 있을까요? 아래 코드가 첫 번째를 보여 줍니다. 두 번째는 Claude Code가 만든 기록을 읽고 맞게 만들었는지 판단하세요. 모델 호출은 없습니다.

관찰할 것: 경고만 울린 기록의 `판정`이 PASS로 남는지, `경고 규칙` 칸에 어떤 규칙이 보이는지.

```python
# [바꿔보기] 더 해보기 3: 마지막 get_order를 빼 경고 규칙을 울린다. 판정은 PASS로 남는다. 모델 호출 0회.
last_read = max(i for i, event in enumerate(normal.events) if event.tool == "get_order")
skipped_check = normal.model_copy(update={"events": [e for i, e in enumerate(normal.events) if i != last_read]})
show([verdict_row("정상 궤적", normal), verdict_row("마지막 get_order를 뺌", skipped_check)])
# 여기부터 내 기록을 만든다. 예: 환불 사건 결과를 {"status": "error", "code": "TIMEOUT"}로 바꾸고 같은 호출을 한 번 더 넣는다.
```

### 더 해보기 4. 판정자가 엇갈리는 이유를 적어 보기 (유료)

요청: "7절 비교(`judge_semantics`와 DeepEval 지표)를 정상 scripted 기록 4궤적에 돌려 표로 보여 주고, 끝나면 Jev, Judge, DeepEval 호출 횟수를 세어 줘. 먼저 호출 규모를 알려 줘." `(유료)`: Jev와 Judge를 부릅니다. 이 과정의 미션 카드는 이 호출을 요구하지 않으며, 내 크레딧을 쓰기 전에 규모를 확인한 뒤 시킵니다.

7절의 표에서 규칙 판정과 문장 판정, DeepEval 지표가 **엇갈린 궤적** 하나를 고르세요. 어느 판정자가 무엇을 근거로 그렇게 말했는지 세 줄로 적고, "이 궤적에서 누구를 믿겠는가, 그 근거는 기록의 어느 사건인가"를 한 문장으로 쓰세요. `StepEfficiencyMetric`을 하나 더 불러 불필요한 단계에 대한 판단도 비교할 수 있습니다. 이 호출은 Judge를 최대 12회(궤적 4개 × 3회 가정) 부르므로 실행 직전에 규모를 알립니다.

관찰할 것: 엇갈린 궤적에서 각 판정자의 근거가 기록의 어느 사건 또는 어느 문장인지.

```python
# [바꿔보기] 더 해보기 4: StepEfficiency 지표를 하나 더 불러 비교한다(유료).
announce("StepEfficiency 추가", model_calls=0, judge_calls=12, minutes=5)
extra_judge = CountingJudge(lab_settings.make_judge_model(lab_settings.load_settings()))
extra_rows = [
    {"궤적": name, **run_agent_metrics(artifact, [StepEfficiencyMetric(model=extra_judge, async_mode=False)])[0]}
    for name, artifact in TRAJECTORIES.items()
]
show(extra_rows)
print(f"추가 Judge 호출 {extra_judge.calls}회")
```

마무리로 Langfuse 기록이 있으면 서버로 내보냅니다. 키가 없으면 할 일이 없습니다.

```python
# 마무리: Langfuse 기록이 있으면 서버로 내보낸다. 키가 없으면 할 일이 없다.
if langfuse is not None:
    langfuse.flush()
    print("Langfuse 기록을 내보냈습니다.")
print("이 실행의 산출물 폴더:", run_dir)
```

## 확인 질문

각 질문은 한두 문장으로 자기 말로 답해 보세요. 답은 이 문서 어딘가에 나온 근거(표, 위반 이유 문장)를 가리킬 수 있어야 합니다.

1. 규칙 8개 중 치명 6개와 경고 2개를 가르는 기준은 무엇입니까? `blind-retry`가 치명이 아니라 경고인 이유를 `TIMEOUT`이 뜻하는 상태로 설명해 보세요.
2. `stale-version`의 복구 창이 없다면 어떤 좋은 행동을 구별하지 못합니까? 반대로 창이 너무 크면 어떤 나쁜 행동을 봐주게 됩니까?
3. 판정 순서가 INCOMPLETE, PROVISIONAL, NO_EVIDENCE, FAIL, PASS인 이유는 무엇입니까? 치명 위반이 있는 기록이 INCOMPLETE로 판정될 때 위반 정보는 어디에 남습니까?
4. 마지막 답이 "주문 번호를 알려 주세요"인 끝난 Episode를 PROVISIONAL이 아니라 PASS 또는 FAIL로 판정하는 이유를 평가 완료율과 위반 놓침 두 측면에서 설명해 보세요.
5. 응답 문장에 "환불했습니다"라고 쓰였는데 `refund_payment` 사건이 없다면 어느 규칙이 어느 사건을 가리킵니까? 반대로 문장만 거짓이고 구조화 필드는 정직하면 왜 규칙이 못 잡습니까?
6. 읽기 예산을 넘은 기록의 앞부분만 잘라 판정하면 왜 거짓 PASS가 됩니까? 예산을 올리는 것이 정당한 경우와 실패를 감추는 경우의 차이는 무엇입니까?
7. `wilson_interval(9, 10)`이 약 (0.596, 0.982)인 것은 "10번 중 9번 잡았다"를 보고할 때 무엇을 알려 줍니까? 재현율 100%에 구간을 붙이지 않으면 어떤 확신을 만들게 됩니까?
8. 이 평가기 평가가 말해 주지 않는 것 세 가지를 적어 보세요.

## 정리

- 궤적은 서비스가 실제로 받은 사건의 선후 기록이고, 규칙은 이름 있는 검사 함수라서 재현되고 사건을 가리킵니다. 다만 규칙은 순서와 대상 같은 사실만 보고 자유 문장의 거짓과 답의 품질은 못 봅니다.
- 규칙 8개는 치명 6개와 경고 2개입니다. 치명은 한 번이면 FAIL이고 경고는 기록만 합니다. `stale-version`만 복구 창(2호출) 안의 재조회로 경고로 낮아집니다.
- 판정은 INCOMPLETE, PROVISIONAL, NO_EVIDENCE, FAIL, PASS의 다섯 가지이며 앞에서부터 가립니다. PASS는 관측한 범위에서 치명 위반이 없다는 뜻이고 좋은 작업의 인증이 아닙니다.
- PROVISIONAL은 **끝나지 않았다는 사실**(실행 상태가 `completed`가 아님, 또는 `awaiting_user`)로만 정합니다. 추가 질문으로 끝난 Episode도 끝났다면 다른 답과 똑같이 판정합니다. 그래야 평가 완료율과 위반 탐지가 흔들리지 않습니다.
- 못 읽었으면 단정하지 않습니다(INCOMPLETE). 잘라서 판정하거나 예산만 올려 한계를 감추지 않습니다.
- 글자는 행동이 아닙니다. 구조화 필드의 완료·환불 주장은 기록이 뒷받침해야 하고, 자유 문장의 의미는 Jev와 Judge가 따로 봅니다. 규칙, DeepEval 지표, Jev, Judge는 각자 놓치는 것이 다르고 서로를 대신하지 않습니다.
- 평가기는 결함 주입(재현율), 정상 변형(오탐률), 정밀도로 재고 모든 비율에 Wilson 95% 구간을 붙입니다. 측정은 독립 평가가 아니고 표본이 작으며 심지 않은 실수를 재지 못합니다.

### 이 문서에서 확인하지 못한 것(미확인)

- 실제 Jev와 Judge 응답, 그리고 Jev 확률의 보정 여부. 문턱값 0.2와 0.8은 미조정 자리값입니다.
- DeepEval 지표가 실제 Judge를 지표당 몇 번 부르는지와, trace가 필요한 지표가 비공개 필드 `_trace_dict` 경로로 실제 모델에서 안정적으로 도는지.
- 응답 문장을 판정하는 Judge가 사건 순서 위반(B 궤적)을 문장만으로 알아채는지. 표의 값은 실행마다 달라질 수 있습니다.
- 정밀도의 사람 검토 방식. 이 문서는 재지 않았습니다.
- Langfuse 서버 쪽 동작. 이 문서는 키가 없을 때도 같은 코드가 도는 로컬 경로를 씁니다.
