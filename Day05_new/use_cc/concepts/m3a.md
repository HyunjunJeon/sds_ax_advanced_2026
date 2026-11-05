# m3a 개념: 03a. 온라인 평가와 Trace 선정

> 이 문서는 Claude Code 실습 과정에서 강사가 미션 앞에 설명하는 강의 본문입니다. 여기에 실린 코드 예시는 **읽기 위한 것**이며 이 문서 안에서 실행하지 않습니다. 실행 가능한 스크립트는 미션 카드 `missions/m3a.md`를 따라 Claude Code가 `work/`에 만들고 `./lab`으로 돌립니다.

정답이 없는 운영 trace를 **무엇으로**, **어떤 것부터** 채점하는가를 배웁니다. 이 문서는 Part 3의 앞 절반이고, 뒤 절반(궤적을 어떻게 판정하고 평가기를 어떻게 믿는가)은 다음 문서(`concepts/m3b.md`)에서 이어 갑니다.

## 이 문서가 답하는 것

운영에 나간 에이전트는 매일 수백, 수천 건의 Episode를 남깁니다. 그 전부를 사람이 읽을 수는 없고, 전부를 Judge(`deepseek/deepseek-v4.1-flash-ultrafast`, effort `xhigh`)에게 맡기면 비용과 시간이 큽니다. 그래서 두 가지를 정해야 합니다.

1. 운영에는 기대 답이 없습니다. 무엇으로 채점할 수 있습니까?
2. 채점 예산이 정해져 있다면 어떤 trace부터 채점합니까? 그 선택이 어떤 숫자를 믿을 수 없게 만듭니까?

## 먼저 알아 둘 것

- 이 과정의 트래픽은 모두 **모의 트래픽**입니다. scripted 드라이버가 실수를 일부러 섞어 만든 입력이며, **모델 성능이 아닙니다.** 여기서 나온 비율을 "에이전트가 몇 퍼센트 틀린다"로 읽으면 안 됩니다.
- 모든 데이터는 교육용 가상 데이터입니다.
- Langfuse 키가 없으면 같은 코드가 로컬 경로로 돕니다. Jev 키(Decision API)와 OpenGateway 키가 없으면 채점 단계에서 키 이름만 대고 멈춥니다. 키 값은 어디에도 출력하지 않습니다.
- 모든 산출물은 실행마다 새로 만드는 폴더 한 곳에만 씁니다.

## 1. 정답이 필요한 지표와 필요 없는 지표

오프라인 평가(Part 2)는 Golden Dataset의 **기대 최종 상태**와 비교했습니다. "주문이 `cancelled`가 되어야 한다"는 정답이 있어야 말할 수 있는 지표입니다. 운영에서 들어온 요청에는 그 정답이 없습니다. 운영에서 쓸 수 있는 것은 정답 없이 되는 지표뿐입니다.

| 구분 | 지표 | 판정자 | 운영에서 쓸 수 있는가 |
|---|---|---|---|
| 정답 필요 | 기대 최종 상태와 일치하는가 | Code | 아니오. 오프라인에서만 |
| 정답 필요 | 기대 답변의 필수 내용이 들어 있는가 | Code, Judge | 아니오. 오프라인에서만 |
| 정답 불필요 | 궤적 규칙을 지켰는가(승인 전 쓰기, 범위 밖 쓰기, 순서) | Code | 예 |
| 정답 불필요 | 응답의 주장이 기록과 맞는가("환불했습니다"에 환불 사건이 있는가) | Code | 예 |
| 정답 불필요 | 자유 문장이 기록보다 부풀리거나 빠뜨리지 않았는가 | Jev 먼저, Judge | 예 |

운영 평가기는 입력으로 **Episode 기록 하나**(요청, 도구 사건, 최종 상태, 응답)만 받습니다. `eval_lab.online`은 기대 상태나 정답표를 읽는 길이 아예 없습니다. 평가기에 정답이 들어가는 순간 그것은 운영 평가가 아니라 오프라인 평가입니다.

정답이 없다는 것은 **판정을 못 내릴 때가 있다**는 뜻이기도 합니다. 기록이 비었거나 잘렸다면 PASS를 주면 안 됩니다. 참고 글 "모르면 모른다고 하기" 절(https://tmdgusya.github.io/roach-blog/posts/trajectory-eval/)이 같은 이유를 설명합니다. 이 저장소의 판정 5종(INCOMPLETE, PROVISIONAL, NO_EVIDENCE, FAIL, PASS)은 그 생각을 주문 도메인에 옮긴 것이고, 다음 문서(`concepts/m3b.md`)에서 자세히 다룹니다.

아래 코드 예시는 이 과정에서 쓰는 이름과 고정값을 한곳에 모은 준비 부분입니다. 원래 교재에는 유료 호출이 들어 있는 선택 실습을 열고 닫는 스위치가 있었으나, 이 과정에서는 각 미션 카드가 비용을 먼저 알리므로 스위치를 두지 않습니다.

준비: 가져오는 이름, 고정값, 확률표, 산출물 폴더와 Langfuse 클라이언트

```python
# 1단계: 필요한 것을 모두 eval_lab에서 가져온다. 모델과 Langfuse는 아래에서 실행 시점에 만든다.
import functools
import json
from collections import Counter

from eval_lab import decisions, settings
from eval_lab.dataset import load_dataset
from eval_lab.notebook import announce, langfuse_or_none, new_run_dir, show, show_keys
from eval_lab.online import (
    SIGNAL_PRIORITY,
    batch_evaluate,
    count_observations,
    create_root_rule,
    evaluate_records_locally,
    online_evaluators,
    push_scores,
    root_filter,
    select_traces,
    wait_for_observations,
)
from eval_lab.traffic import MISTAKES, make_mistake_driver, make_traffic, run_traffic
from eval_lab.trajectory_rules import evaluate_trajectory, run_rules

# 2단계: 이 과정의 고정값. 바꾸면 모든 표가 달라지므로 한곳에 모아 둔다.
SEED = 7               # 트래픽, 실수 추첨, 무작위 선정이 모두 이 seed를 쓴다
DAY_SIZE = 30          # 하루치 모의 Episode 수
ENV = "traffic-03a"            # Langfuse environment 이름(소문자, 숫자, -, _)
ENV_LIVE = "traffic-03a-live"  # 실제 모델 트래픽은 따로 모아 scripted 기록과 섞지 않는다

# 3단계: 실수를 섞는 확률. 아래 확률표의 이유는 2절의 표에 있다.
MISTAKE_RATES = {
    "write_before_approval": 0.05,
    "blind_retry": 0.50,
    "claim_without_record": 0.08,
    "write_out_of_scope": 0.04,
    "skip_final_check": 0.10,
}

# 4단계: 산출물 폴더, 키 상태, Langfuse 클라이언트. 키는 설정됨/미설정만 표로 보인다.
OUT_DIR = new_run_dir("03a")
CONFIG = settings.load_settings()
show_keys(CONFIG)
LANGFUSE = langfuse_or_none(CONFIG)
print("산출물 폴더:", OUT_DIR.name)
print("Langfuse:", "연결됨" if LANGFUSE is not None else "없음(로컬 경로)")
```

## 2. 모의 운영 트래픽

운영 trace를 연습할 입력이 필요합니다. 실제 고객 요청을 쓸 수 없으니 **모의 트래픽**을 만듭니다. `make_traffic(day, n, seed=...)`가 날짜별 분포에 맞춰 요청 n건을 만듭니다.

- 요청은 세 문형(정중, 짧게, 오타)으로 다시 쓰고, 업무 내용(주문 번호, fixture)은 그대로 둡니다.
- 1일차는 정상 주문이 많습니다. 2일차는 환불 TIMEOUT, 결제 장애, 다른 고객 주문이 늘어난 분포입니다. 분포가 바뀌는 것이 운영 감시(Part 4)의 소재가 됩니다.
- 항목은 dev 시나리오의 **입력**만 가져옵니다. 기대 상태는 담지 않습니다.

그다음 `make_mistake_driver`가 만드는 **scripted 드라이버**로 항목을 실행합니다. 드라이버는 정상 흐름을 따라가다가 정해진 확률로 실수를 실제 도구 호출로 끼워 넣습니다. 실수는 말로만 적지 않고 도구를 실제로 불러 만들기 때문에 Event와 업무 상태에 남습니다. 평가기가 잡아야 하는 것은 이 기록입니다.

| 심는 실수 | 확률 | 이 값을 고른 이유 |
|---|---|---|
| `write_before_approval` | 0.05 | 정책 확인 없이 취소를 시작한다. 드물지만 치명적인 위반이다 |
| `blind_retry` | 0.50 | TIMEOUT을 만난 Episode에서만 일어난다. TIMEOUT 자체가 드물어서 높게 잡아야 몇 건이라도 나온다 |
| `claim_without_record` | 0.08 | 기록에 없는 완료 주장. 조용히 틀리는 유형이라 선정 전략의 약점을 보여 준다 |
| `write_out_of_scope` | 0.04 | 다른 고객 주문에 쓰기를 시도한다 |
| `skip_final_check` | 0.10 | 완료 뒤 최종 확인을 생략한다. 경고 등급 위반이다 |

seed는 7로 고정합니다. 같은 seed는 같은 항목과 같은 실수 선택을 만들어서 다시 돌려도 같은 표가 나옵니다. 확률은 수업용으로 정한 값이고 실제 운영의 실수 비율과 관계가 없습니다. **이 비율로 모델 성능을 말하지 않습니다.** 위 준비 코드의 `MISTAKE_RATES`가 이 표의 확률을 그대로 담은 상수이며, 미션 M3a-1에서 Claude Code가 같은 상수로 드라이버를 만듭니다.

먼저 두 날의 분포가 실제로 다른지 봅니다.

1일차와 2일차 모의 요청을 만들고 가족(family)별 개수를 나란히 본다. 모델 호출은 없다. 이 호출은 미션 M3a-1에서 Claude Code가 만든다.

```python
# [따라하기] 1일차와 2일차 모의 요청을 만들고 가족(family)별 개수를 나란히 본다. 모델 호출은 없다.
day_items = {day: make_traffic(day, DAY_SIZE, seed=SEED) for day in (1, 2)}

# 1단계: 날짜마다 가족별 개수를 센다.
counts = {day: Counter(item.family_id for item in items) for day, items in day_items.items()}

# 2단계: 두 날을 한 표에 놓고, 2일차가 얼마나 늘었는지 차이를 적는다.
families = sorted(set(counts[1]) | set(counts[2]))
show([{"가족": family, "1일차": counts[1][family], "2일차": counts[2][family],
       "차이": counts[2][family] - counts[1][family]} for family in families],
     title=f"날짜별 모의 요청 {DAY_SIZE}건의 가족 분포")

# 3단계: 첫 요청 하나를 문형별로 읽어 본다. 주문 번호가 없는 요청도 섞여 있다.
show([{"item_id": item.item_id, "문형": item.style, "문장": item.request.message}
      for item in day_items[1][:4]])
```

**먼저 예측하세요.** 이틀치 분포에서 2일차에 늘어난 가족은 무엇이고, 그 가족들은 Episode에서 어떤 도구 오류(TIMEOUT, 결제 장애, 소유자 거절)를 만들겠습니까? 이 분포 변화가 뒤에 나오는 판정 요약 표(미션 M3a-1의 날짜별 표)의 "도구 오류가 있는 Episode" 개수에 어떻게 보일지도 `notes/m3a.md`에 적어 보세요.

**관찰할 것.** 가족 이름은 코드가 아니라 요청이 바뀐 결과로 보입니다. 같은 `DAY_SIZE`인데 날짜에 따라 가족의 비중이 다릅니다. 이 차이는 정답 없이 요청 입력만 보고도 알 수 있습니다. 운영에서 "오늘 요청 유형이 어제와 다르다"는 신호가 입력 분포 변화입니다. 미션 M3a-1에서는 Claude Code가 만든 표의 가족 열과 차이 열을 보세요.

이제 두 날의 항목을 드라이버로 실행합니다. 모든 Episode는 root observation 하나 안에서 실행되고 Langfuse가 있으면 `environment`, `version`, 태그가 붙습니다. Episode가 끝나면 root observation의 output에 **Episode 요약**이 들어갑니다. 뒤에서 운영 평가기가 읽는 것은 이 요약 하나입니다.

Langfuse v4부터 trace의 입출력은 root observation에서 옵니다. 그래서 root observation의 output을 비워 두면 평가기는 읽을 근거가 없습니다. 그 경우 PASS를 지어내지 않고 NO_EVIDENCE로 남기는 것이 올바른 동작입니다.

두 날의 모의 트래픽을 scripted 드라이버로 실행한다. 모델 호출 0회. 이 호출은 미션 M3a-1에서 Claude Code가 만든다(환경 `cc_m3a`, version `mock-baseline`).

```python
# [따라하기] 두 날의 모의 트래픽을 scripted 드라이버로 실행한다. 모델 호출 0회.
driver = make_mistake_driver(MISTAKE_RATES, seed=SEED)

RECORDS = []
for day, items in day_items.items():
    # 1단계: 날짜별 항목을 Episode로 실행한다. langfuse가 None이면 기록 없이 실행만 한다.
    RECORDS += run_traffic(items, mode="scripted", driver=driver, langfuse=LANGFUSE,
                           environment_tag=ENV, version="mock-baseline")

# 2단계: Langfuse가 있으면 보내지 못한 span이 남지 않게 비운다.
if LANGFUSE is not None:
    LANGFUSE.flush()

# 3단계: 정답 없이 되는 판정(궤적 규칙)을 Episode마다 한 번씩 계산해 둔다.
VERDICTS = [evaluate_trajectory(record["artifact"]) for record in RECORDS]

rows = []
for day in (1, 2):
    members = [i for i, record in enumerate(RECORDS) if record["day"] == day]
    rows.append({
        "일차": day,
        "Episode": len(members),
        "PASS": sum(VERDICTS[i].status == "PASS" for i in members),
        "FAIL": sum(VERDICTS[i].status == "FAIL" for i in members),
        "그 밖의 판정": sum(VERDICTS[i].status not in {"PASS", "FAIL"} for i in members),
        "치명 위반 Episode": sum(bool(VERDICTS[i].fatal) for i in members),
        "도구 오류 Episode": sum(any(e.result.get("status") in {"error", "denied"}
                                    for e in RECORDS[i]["artifact"].events) for i in members),
        "escalated 응답": sum(RECORDS[i]["artifact"].response is not None
                              and RECORDS[i]["artifact"].response.kind == "escalated" for i in members),
    })
show(rows, title="모의 트래픽의 정답 없는 판정 요약 (모델 성능이 아니다)")
print("Langfuse에 보낸 trace가 있는 Episode:", sum(record["trace_id"] is not None for record in RECORDS))
```

**관찰할 것.** 판정 요약 표의 모든 열이 정답표 없이 계산됩니다. 판정, 치명 위반, 도구 오류, 응답 유형은 모두 Episode 기록에서 나옵니다. 2일차의 도구 오류와 escalated가 1일차보다 많다면 분포 변화가 그대로 보이는 것입니다. 단, 이 표의 FAIL 비율은 **심어 둔 실수의 확률이 만든 값**입니다. 같은 표를 실제 모델 트래픽에 그대로 쓰려면 실수가 어디서 오는지부터 다시 말해야 합니다. 미션 M3a-1에서는 Claude Code가 출력한 날짜별 표에서 이 열들을 읽고, Langfuse의 Dashboards → Langfuse Agent Dashboard에서 도구 호출 수와 도구 오류가 같은 방향으로 늘었는지 맞춰 봅니다.

심어 둔 실수와 궤적 규칙이 실제로 잡은 것을 맞춰 본다. 운영에서는 "심은 실수" 열이 없다. 이 호출은 필수 미션 단계에는 없으며, 읽는 것만으로 충분합니다.

```python
# [따라하기] 심어 둔 실수와 궤적 규칙이 실제로 잡은 것을 맞춰 본다. 운영에서는 이 열("심은 실수")이 없다.
RULE_OF = {
    "write_before_approval": "write-before-approval",
    "blind_retry": "blind-retry",
    "claim_without_record": "claim-without-record",
    "write_out_of_scope": "write-out-of-scope",
    "skip_final_check": "skip-final-check",
}

rows = []
for mistake in MISTAKES:
    # 1단계: 이 실수를 실제로 시도한 Episode의 위치.
    planted = [i for i, record in enumerate(RECORDS) if mistake in record["injected_mistakes"]]
    # 2단계: 그중 대응하는 규칙이 위반을 찾아낸 Episode.
    caught = [i for i in planted
              if RULE_OF[mistake] in {hit.rule_id for hit in run_rules(RECORDS[i]["artifact"])}]
    rows.append({"심은 실수": mistake, "대응 규칙": RULE_OF[mistake],
                 "심은 Episode": len(planted), "그 규칙이 잡은 Episode": len(caught)})
show(rows, title="심은 실수와 규칙 판정의 대응")

# 3단계: 심은 실수와 관계없이 규칙이 잡은 위반도 있다. 규칙별 위반 Episode 수를 센다.
rule_counts = Counter(hit.rule_id for record in RECORDS for hit in run_rules(record["artifact"]))
print("규칙별 위반 건수:", dict(sorted(rule_counts.items())))
```

**관찰할 것.** "심은 Episode"와 "그 규칙이 잡은 Episode"가 같은 줄이 있고, 심지 않았는데 위반으로 잡힌 규칙이 아래 줄에 있을 수 있습니다. 후자는 평가기의 오류가 아니라 드라이버의 정상 흐름이 서비스 장애(버전 충돌, 출고 관측) 뒤에 만든 궤적입니다. 두 가지를 구별하는 일이 `concepts/m3b.md`의 평가기 평가입니다. 여기서는 규칙 판정이 정답 없이 돈다는 것만 확인합니다.

## 3. 표본 선정 전략 4종

Episode가 60건이면 전부 채점할 수 있습니다. 운영에서는 하루에 수천 건이 쌓이므로 **예산**(Judge 호출 수, 사람이 읽을 시간)에 맞춰 일부를 골라야 합니다. `select_traces(records, strategy, k, seed=...)`는 같은 입력과 같은 seed면 항상 같은 trace를 고릅니다. 전략마다 놓치는 것이 다릅니다.

| 전략 | 어떻게 고르는가 | 잘 잡는 것 | **놓치는 것** |
|---|---|---|---|
| `random` | seed 고정 무작위 | 전체 비율의 불편 추정 | 드문 문제. 전체의 2%만 문제라면 k건 중 평균 0.02k건만 잡힌다 |
| `stratified` | (가족, 날짜) 층마다 한 건씩 돌아가며 | 층별 최소 표본 | 층 안의 발생률 차이. 층은 우리가 아는 분류라서 분류에 없는 새 유형은 층에 숨는다 |
| `signal` | 도구 오류, 모델 오류, escalated, 지연 상위, 비용 상위, 규칙 위반 순 | 이미 신호가 있는 문제 | **신호 없이 조용히 틀린 trace.** 그리고 표본이 편향되어 있어 **전체 비율을 말하는 데 쓰면 안 된다** |
| `novelty` | 요청 모양이 Golden에 없는 것 | 새 입력에서 생기는 문제 | Golden에 있는 모양에서 생긴 회귀. Golden 모양 목록이 있어야 한다 |

`signal`의 우선순위는 코드에서 `SIGNAL_PRIORITY`로 고정되어 있습니다. 앞쪽 신호가 있는 trace를 먼저 뽑습니다.

random과 stratified로 8건씩 고른다. 같은 seed는 같은 결과다. 이 호출은 미션 M3a-3에서 Claude Code가 만든다.

```python
# [따라하기] random과 stratified로 8건씩 고른다. 같은 seed는 같은 결과다.
print("signal 우선순위:", " > ".join(SIGNAL_PRIORITY))


def profile(label, selections):
    """선정 결과가 무엇을 담았는지 센다. 치명 위반 수와 심은 실수 수는 이 수업의 모의 트래픽이라 셀 수 있다."""
    picked = [RECORDS[s.record_index] for s in selections]
    return {
        "전략": label,
        "선정": len(selections),
        "치명 위반 Episode": sum(bool(VERDICTS[s.record_index].fatal) for s in selections),
        "실수를 심은 Episode": sum(bool(record["injected_mistakes"]) for record in picked),
        "2일차": sum(record["day"] == 2 for record in picked),
    }


# 1단계: 두 전략으로 8건씩 고른다.
random_pick = select_traces(RECORDS, "random", 8, seed=SEED)
stratified_pick = select_traces(RECORDS, "stratified", 8, seed=SEED)

# 2단계: 전체를 한 줄로 두고 비교한다. 선정은 전체의 일부일 뿐이다.
population = {"전략": "전체(참고)", "선정": len(RECORDS),
              "치명 위반 Episode": sum(bool(v.fatal) for v in VERDICTS),
              "실수를 심은 Episode": sum(bool(r["injected_mistakes"]) for r in RECORDS),
              "2일차": sum(r["day"] == 2 for r in RECORDS)}
show([population, profile("random", random_pick), profile("stratified", stratified_pick)])

# 3단계: 뽑힌 이유를 읽는다. 층화는 층 이름이, 무작위는 seed가 이유다.
show([{"전략": "stratified", "item": RECORDS[s.record_index]["item_id"], "이유": s.reason}
      for s in stratified_pick[:4]])
```

signal과 novelty로 8건씩 고른다. novelty는 비교할 Golden 모양이 있어야 한다. 이 호출도 미션 M3a-3에서 Claude Code가 만든다.

```python
# [따라하기] signal과 novelty로 8건씩 고른다. novelty는 비교할 Golden 모양이 있어야 한다.
# Golden 모양 = (주문 번호 유무, 문형, 가족). dev 카드의 입력과 가족만 읽고 기대값은 열지 않는다.
# 문장 문형은 Golden이 모두 정중한 표현이라고 가정해 "정중"으로 둔다(이 가정은 수업용이다).
GOLDEN_SHAPES = {
    (card.input.order_id is not None, "정중", card.metadata.family_id)
    for card in load_dataset(split="dev")
}

signal_pick = select_traces(RECORDS, "signal", 8, seed=SEED)
novelty_pick = select_traces(RECORDS, "novelty", 8, seed=SEED, golden_shapes=GOLDEN_SHAPES)
show([population, profile("signal", signal_pick), profile("novelty", novelty_pick)])

# signal이 뽑은 이유는 신호의 이름과 개수다. 규칙 위반은 우선순위가 가장 낮다.
show([{"item": RECORDS[s.record_index]["item_id"], "이유": s.reason} for s in signal_pick])
```

random의 seed를 0~9로 바꿔 가며 8건 안의 치명 위반 수가 얼마나 흔들리는지 본다. 이 호출은 필수 미션 단계에 없고 `## 더 해보기 (선택)`에서 Claude Code에게 요청할 수 있습니다.

```python
# [바꿔보기] random의 seed를 0~9로 바꿔 가며 8건 안의 치명 위반 수가 얼마나 흔들리는지 본다.
fatal_by_seed = {}
for seed in range(10):
    pick = select_traces(RECORDS, "random", 8, seed=seed)
    fatal_by_seed[seed] = sum(bool(VERDICTS[s.record_index].fatal) for s in pick)
print("seed별 치명 위반 Episode 수:", fatal_by_seed)
print("전체의 치명 위반 비율:", f"{sum(bool(v.fatal) for v in VERDICTS)}/{len(VERDICTS)}")
```

**먼저 예측하세요.** 8건 안의 치명 위반 수가 seed마다 같습니까? `signal`로 뽑은 8건에는 치명 위반이 몇 건이나 들어 있겠습니까? 신호 우선순위의 맨 앞이 "도구 오류"라는 점을 생각해 보세요. (미션 M3a-2에서 `notes/m3a.md`에 적는 예측과 같은 질문입니다.)

**관찰할 것.** `random`은 seed에 따라 표본의 치명 위반 수가 흔들립니다. 기대값은 전체 비율에 가깝지만 한 번의 8건은 우연의 영향을 받습니다. `signal`은 신호가 있는 trace만 모읍니다. 그 신호가 치명 위반과 겹치는 정도는 우선순위를 어떻게 정했느냐에 달려 있고, "신호가 많다"가 "치명 위반이 많다"를 뜻하지 않을 수 있습니다. 미션 M3a-3에서는 네 전략의 표에서 `이유` 칸과 치명 위반 Episode 열을 비교합니다.

novelty에 golden_shapes를 주지 않는다. 비교할 Golden이 없으면 "새롭다"를 말할 수 없어 ValueError가 난다. 이 호출은 필수 미션 단계에 없고 읽는 것만으로 충분합니다.

```python
# [깨뜨리기] novelty에 golden_shapes를 주지 않는다. 비교할 Golden이 없으면 "새롭다"를 말할 수 없어 ValueError가 난다.
try:
    select_traces(RECORDS, "novelty", 8, seed=SEED)
except ValueError as error:
    print("막힌 이유:", error)

# 모르는 전략 이름도 조용히 무작위로 바꾸지 않고 멈춘다.
try:
    select_traces(RECORDS, "top-severity", 8, seed=SEED)
except ValueError as error:
    print("막힌 이유:", error)
```

signal로 뽑은 표본의 비율을 "전체 비율"처럼 읽으면 어떻게 틀리는지 숫자로 본다. 이 호출은 필수 미션 단계에 없고 `## 더 해보기 (선택)`에서 요청할 수 있습니다.

```python
# [깨뜨리기] signal로 뽑은 표본의 비율을 "전체 비율"처럼 읽으면 어떻게 틀리는지 숫자로 본다.
signal_all = select_traces(RECORDS, "signal", len(RECORDS), seed=SEED)
flagged = len(signal_all)
fatal_among_flagged = sum(bool(VERDICTS[s.record_index].fatal) for s in signal_all)
fatal_overall = sum(bool(v.fatal) for v in VERDICTS)

print(f"신호가 있는 Episode: {flagged}/{len(RECORDS)}")
print(f"신호 표본 안의 치명 위반 비율: {fatal_among_flagged}/{flagged}")
print(f"전체의 치명 위반 비율:        {fatal_overall}/{len(RECORDS)}")
print("신호가 없는 Episode 안의 치명 위반:",
      fatal_overall - fatal_among_flagged, "건 (signal 전략은 이것을 한 건도 뽑지 못한다)")
```

**관찰할 것.** 신호 표본 안의 비율과 전체 비율은 다른 질문의 답입니다. 신호 표본의 비율은 "신호가 있는 Episode 중 치명 위반이 몇 건"일 뿐이고, 마지막 줄의 "신호가 없는 Episode 안의 치명 위반"은 이 전략이 구조적으로 보지 못하는 부분입니다(이 줄이 0이면 이 모의 데이터에서는 우연히 겹친 것이며, 그것으로 전략이 안전하다고 말할 수는 없습니다). 운영 감시에서 **비율**을 말할 때는 `random`이나 `stratified`처럼 선정 규칙을 알고 있는 표본만 씁니다. `signal`은 사람이 읽을 후보를 고르는 용도입니다.

정리하면 `signal`과 `novelty`는 "무엇을 먼저 볼까"에, `random`과 `stratified`는 "비율이 얼마인가"에 답합니다. 한 전략으로 둘 다 하려고 하면 둘 중 하나가 틀립니다.

## 4. Rule(무엇)과 Evaluator(어떻게), observation-level

Langfuse는 2026-08-22에 평가 구성을 둘로 나눴습니다(https://langfuse.com/changelog/2026-08-22-reusable-evaluators-and-rules).

- **Rule**: **무엇을** 채점할지 정합니다. 환경, 필터, 샘플링 비율입니다.
- **Evaluator**: **어떻게** 채점할지 정합니다. Judge 프롬프트와 모델, 점수 이름입니다.

한 Evaluator를 여러 Rule에 재사용할 수 있고, Rule을 저장하기 전에 실제 observation으로 Evaluator를 시험하고 최근 7일 매칭량과 예상 비용을 볼 수 있습니다. 이 과정의 `select_traces`와 `batch_evaluate`는 SDK 쪽에서 같은 일을 합니다. 선정이 Rule의 필터와 샘플링이고, `online_evaluators`가 Evaluator입니다.

**observation-level**이 이 구조의 핵심입니다. 예전 trace-level evaluator는 trace 하나를 평가 대상으로 삼았습니다. trace-level evaluator는 v4에서 deprecated이고 **Langfuse Cloud에서는 2026-11-16 전환 시점에 결과 생성을 멈춥니다**(https://langfuse.com/faq/all/llm-as-a-judge-migration). 새 구조는 매칭되는 observation마다 점수를 만들고 기본 필터가 `isRootObservation = true`입니다. 이 저장소의 Episode는 root observation 하나 안에서 실행되고 output에 요약이 남기 때문에, **root observation 하나가 Episode 하나**입니다. 평가기는 trace가 아니라 root observation의 `output`을 읽습니다.

전환 뒤 달라지는 점은 이렇습니다. SDK를 올린 뒤에는 trace input/output이 자동으로 기록되지 않고, 값은 root observation에서 옵니다. 그래서 이 저장소는 `set_trace_io` 계열을 쓰지 않고 root observation에 output을 직접 넣습니다.

`root_filter(environment)`는 이 조건을 JSON으로 만든 것입니다.

환경이 ENV이고 이름이 root observation(episode)인 observation만 고르는 필터를 읽는다. 이 필터는 미션 M3a-4에서 Claude Code가 `traceId` 조건을 더할 때 바탕으로 씁니다.

```python
# [따라하기] 환경이 ENV이고 이름이 root observation(episode)인 observation만 고르는 필터를 읽는다.
print(json.dumps(json.loads(root_filter(ENV)), ensure_ascii=False, indent=2))

# 1단계: Langfuse가 있으면 이 필터에 걸리는 observation 수를 서버에 묻는다.
if LANGFUSE is None:
    print("Langfuse가 없어 서버에는 묻지 않는다. 로컬 기록은", len(RECORDS), "건이다.")
else:
    # v2 관측 API로 센다(count_observations). v1 관측 API는 Langfuse Cloud에서 2026-11-16에 없어진다.
    matched = count_observations(LANGFUSE, root_filter(ENV))
    print(f"필터에 걸린 root observation: {matched}건 (Episode {len(RECORDS)}건)")
    print("방금 기록했다면 집계 지연으로 적게 나올 수 있다. 1~2분 뒤 이 호출만 다시 실행해 본다.")
```

**관찰할 것.** 필터에 걸린 수와 Episode 수가 같다면 "Episode 하나 = root observation 하나"가 지켜진 것입니다. 실제 서버에서는 방금 보낸 기록이 집계되기까지 시간이 걸릴 수 있어서 이 수가 더 작게 나올 수도 있습니다. 그 지연은 이 저장소에서 확인하지 못했습니다(**미확인**). 미션 M3a-4의 출력 "집계 지연: N초 기다려 …건이 읽힌다"가 이 지연을 숫자로 보여 줍니다.

다음 코드 예시는 서버 쪽 Rule 초안을 만드는 선택 경로입니다. 두 가지를 알아 두세요.

- Evaluator를 서버에 만들고 Rule에 묶는 것은 Langfuse 화면이나 API로 따로 해야 합니다. 아래 `EVALUATOR_ID`는 **자리값**이어서 실제 서버에서 쓰려면 화면에서 만든 Evaluator의 ID로 바꿔야 합니다. 자리값 그대로면 서버가 거절할 수 있습니다(서버 쪽 동작은 **미확인**).
- 서버에서 도는 LLM Judge를 쓰면 **수강생 본인의 모델 키가 Langfuse의 LLM Connection에 저장됩니다.** 그래서 이 경로는 `enabled=False` 초안만 만들고, 이 과정의 필수 미션 단계에서는 실행하지 않습니다. 이 과정의 주 경로는 SDK의 `batch_evaluate`이며 서버 쪽 Judge는 선택입니다.

서버 쪽 Rule 초안을 enabled=False로 만든다. 모델 호출은 없고 Langfuse에 Rule이 하나 생긴다. 필수 미션 단계에는 없으며 읽는 것만으로 충분합니다.

```python
# [바꿔보기] 서버 쪽 Rule 초안을 enabled=False로 만든다. 모델 호출은 없고 Langfuse에 Rule이 하나 생긴다.
EVALUATOR_ID = "evaluator-id-from-langfuse-ui"  # 자리값. 화면에서 만든 Evaluator ID로 바꾼다.
SAMPLING = 0.05                                  # 매칭된 root observation 중 5%만 평가한다.

if LANGFUSE is None:
    print("Langfuse가 없어 Rule 초안을 만들 수 없다.")
else:
    rule = create_root_rule(LANGFUSE, evaluator_id=EVALUATOR_ID, environment=ENV, sampling=SAMPLING, enabled=False)
    print("Rule 초안을 만들었다(enabled=False):", rule)
```

## 5. 선정한 trace를 일괄 채점하고 점수를 붙이기

채점 경로는 둘입니다.

- **Langfuse가 있으면**: `batch_evaluate`가 Langfuse의 v2 관측 API에서 root observation을 가져와 (SDK의 `run_batched_evaluation(scope="observations")`과 같은 계약입니다. 설치된 SDK의 그 함수는 v1 관측 API를 쓰는데, Langfuse Cloud가 v1을 2026-11-16에 없애므로 같은 일을 v2 위에서 직접 합니다) `online_evaluators`가 만든 평가기 둘(궤적 평가기, 의미 평가기)을 돌리고, 점수는 Langfuse가 해당 observation에 붙입니다. 선정한 trace만 채점하려고 root 필터에 `traceId` 조건을 더합니다. `max_items`는 한 번에 채점할 양, 곧 비용의 상한입니다.
- **Langfuse가 없으면**: `evaluate_records_locally`가 로컬 기록에 **같은 평가기**를 돌립니다. Episode를 요약으로 바꿔 평가기에 넘기므로 같은 코드 길을 지납니다.

두 경로의 평가기가 읽는 입력은 root observation output의 **Episode 요약 하나**입니다. 기대 상태는 없습니다(`expected_output=None`). 요약이 비었거나 잘렸으면 평가기는 Artifact를 지어내지 않고 `NO_EVIDENCE` 또는 `INCOMPLETE`로 남깁니다.

평가기가 내는 점수는 이렇습니다.

| 평가기 | 점수 이름 | 값 |
|---|---|---|
| 궤적 평가기(Code) | `trajectory_status` | PASS, FAIL, INCOMPLETE, PROVISIONAL, NO_EVIDENCE |
| | `fatal_count`, `warn_count` | 치명·경고 위반 수 |
| | `blocked_attempts` | 게이트가 막거나 확인을 요청한 시도 수 |
| 의미 평가기(Jev 먼저, 불확실하면 Judge) | `message_consistent`, `next_step_clear`, `clarify_when_needed` | PASS, FAIL, UNDECIDED |

의미 평가기는 응답이 없는 Episode에서는 점수를 내지 않습니다. Jev가 확률 0.2~0.8 사이로 답하면(초기값이며 **미조정**입니다) Judge로 넘어가고, 그 밖이면 Jev 판정이 그대로 기록됩니다. 문턱값은 사람 라벨로 재지 않은 자리값입니다.

먼저 채점할 20건을 고릅니다. 전략은 `STRATEGY` 하나로 바꿀 수 있고 기본은 `stratified`입니다. 비율을 말할 수 있는 표본이기 때문입니다. (미션 M3a-4에서는 M3a-3에서 정한 내 전략으로 고른 것 중 10건을 채점합니다.)

채점할 20건을 고른다. 전략을 바꾸려면 STRATEGY만 고친다. 모델 호출은 없다. 이 호출은 미션 M3a-3의 내 전략 단계에서 Claude Code가 같은 형태로 만든다.

```python
# [따라하기] 채점할 20건을 고른다. 전략을 바꾸려면 STRATEGY만 고친다. 모델 호출은 없다.
STRATEGY = "stratified"   # random, stratified, signal, novelty 중 하나
BATCH_SIZE = 20

SELECTED = select_traces(RECORDS, STRATEGY, BATCH_SIZE, seed=SEED, golden_shapes=GOLDEN_SHAPES)
show([profile(STRATEGY, SELECTED)])
show([{"item": RECORDS[s.record_index]["item_id"], "trace": s.trace_id, "이유": s.reason} for s in SELECTED[:5]],
     title="선정 이유(앞 5건)")

# 선정 결과는 나중에 다시 볼 수 있게 폴더에 적는다. 키나 원문 전체는 담지 않는다.
(OUT_DIR / "selection.json").write_text(json.dumps(
    [{"item_id": RECORDS[s.record_index]["item_id"], "trace_id": s.trace_id, "reason": s.reason} for s in SELECTED],
    ensure_ascii=False, indent=2))
```

선정 trace를 일괄 채점한다. 유료: 원래 규모는 Jev 최대 20회, Judge 최대 60회이고, 미션 M3a-4는 10건으로 줄여 Jev 최대 10회, Judge 최대 30회를 씁니다. 이 호출은 미션 M3a-4에서 Claude Code가 만든다.

```python
# [따라하기] 선정 trace 20건을 일괄 채점한다. 유료: Jev 최대 20회, Judge 최대 60회.
announce("선정 trace 20건 일괄 채점", model_calls=0, jev_calls=20, judge_calls=60)

# 1단계: 평가기가 쓸 Jev와 Judge를 이 시점에 만든다. 키가 없으면 여기서 이름만 대고 멈춘다.
decider = decisions.make_decider(CONFIG)
judge_model = settings.make_judge_model(CONFIG)
selected_records = [RECORDS[s.record_index] for s in SELECTED]
trace_index = {record["trace_id"]: i for i, record in enumerate(RECORDS) if record["trace_id"]}

if LANGFUSE is not None:
    # 2단계(Langfuse 경로): 평가기가 낸 점수를 표로도 보려고 얇은 기록기로 감싼다. 점수는 그대로 서버에 붙는다.
    CAPTURED = []

    def recording(evaluator):
        @functools.wraps(evaluator)
        def run(**kwargs):
            evaluations = evaluator(**kwargs)
            info = kwargs.get("metadata") or {}
            for evaluation in evaluations:
                CAPTURED.append({"trace_id": info.get("trace_id"), "observation_id": info.get("observation_id"),
                                 "name": evaluation.name, "value": evaluation.value,
                                 "stage": (evaluation.metadata or {}).get("stage"), "comment": evaluation.comment})
            return evaluations
        return run

    evaluators = [recording(evaluator) for evaluator in online_evaluators(decider=decider, judge_model=judge_model)]

    # 3단계: root 필터에 traceId 조건을 더해 선정한 trace만 가져오게 하고, max_items로 상한을 건다.
    only_selected = {"type": "stringOptions", "column": "traceId", "operator": "any of",
                     "value": [s.trace_id for s in SELECTED]}
    filter_json = json.dumps(json.loads(root_filter(ENV)) + [only_selected])
    # 집계는 비동기다. 방금 보낸 trace가 Langfuse에서 읽힐 때까지 최대 3분 기다리고, 기다린 시간을 숨기지 않는다.
    ready, waited = wait_for_observations(LANGFUSE, filter_json, expected=len(SELECTED))
    print(f"집계 지연: {waited}초 기다려 선정한 {len(SELECTED)}건 중 {ready}건이 Langfuse에서 읽힌다")
    result = batch_evaluate(LANGFUSE, evaluators=evaluators, environment=ENV, max_items=BATCH_SIZE,
                            filter_json=filter_json)
    print(f"가져온 root observation {result.total_items_fetched}건, 채점 {result.total_items_processed}건, "
          f"점수 {result.total_scores_created}개, 평가기 실패 {result.total_evaluations_failed}건")
    SCORE_ROWS = [{**row, "record_index": trace_index.get(row["trace_id"])} for row in CAPTURED]
else:
    # 2단계(로컬 경로): 같은 평가기를 로컬 기록에 돌린다. 점수를 붙일 서버가 없다.
    local_rows = evaluate_records_locally(selected_records, decider=decider, judge_model=judge_model)
    SCORE_ROWS = [{"trace_id": row["trace_id"], "observation_id": row["observation_id"],
                   "record_index": SELECTED[row["record_index"]].record_index, "name": row["name"],
                   "value": row["value"], "stage": (row["metadata"] or {}).get("stage"),
                   "comment": row["comment"]} for row in local_rows]
    print(f"로컬 채점 {len(selected_records)}건, 점수 {len(SCORE_ROWS)}개")

(OUT_DIR / "scores.json").write_text(json.dumps(SCORE_ROWS, ensure_ascii=False, indent=2, default=str))
```

**관찰할 것.** Langfuse 경로에서는 "가져온 root observation" 수가 선정한 건수와 같아야 합니다. `traceId` 조건이 먹지 않았다면 환경 전체가 채점 대상이 되고 `max_items`가 비용을 막아 줍니다(이 조건이 실제 서버에서 받아들여지는지는 **미확인**입니다). "평가기 실패"가 0이 아니면 평가기가 항목 하나에서 예외를 낸 것이며 배치는 계속 돕니다. 평가기 실패를 점수 0으로 세지 않습니다. 미션 M3a-4에서는 Claude Code의 출력(기다린 초, 가져온 건수, 점수 수)과 Langfuse의 Scores 화면을 함께 봅니다.

모델 응답은 이 문서가 단정하지 않습니다. 아래 코드 예시는 점수를 표로 **보여 줄 뿐**입니다.

점수를 요약한다. 이 표는 선정한 건 안의 개수이며 전체 비율이 아니다. 미션 M3a-4의 마지막 출력(점수 수, Judge로 넘어간 비율)에 해당합니다.

```python
# [따라하기] 점수를 요약한다. 이 표는 선정한 20건 안의 개수이며 전체 비율이 아니다.
counts = Counter((row["name"], row["value"]) for row in SCORE_ROWS)
show([{"점수 이름": name, "값": value, "개수": count}
      for (name, value), count in sorted(counts.items(), key=lambda item: str(item[0]))],
     title=f"점수 요약 ({STRATEGY} 표본 {len(SELECTED)}건 안의 개수)")

# 의미 점수가 어느 단계에서 정해졌는지: Jev가 확신했는가, Judge로 넘어갔는가.
semantic = [row for row in SCORE_ROWS if row["stage"] is not None]
judged = sum(row["stage"] == "judge" for row in semantic)
print(f"의미 점수 {len(semantic)}개 중 Judge가 정한 것 {judged}개 (넘김 비율 {judged}/{len(semantic)})")
```

선정 전략을 점수로 기록한다. "이 trace는 어떤 전략으로 뽑혔다"가 없으면 나중에 비율을 잘못 읽는다. root observation ID는 방금 채점에서 받은 것을 쓴다. Langfuse가 없으면 붙일 곳이 없어 모두 건너뛴다. 이 호출은 필수 미션 단계에 없고, 필요하면 Claude Code에게 요청할 수 있습니다.

```python
# [따라하기] 선정 전략을 점수로 기록한다. "이 trace는 어떤 전략으로 뽑혔다"가 없으면 나중에 비율을 잘못 읽는다.
# root observation ID는 방금 채점에서 받은 것을 쓴다. Langfuse가 없으면 붙일 곳이 없어 모두 건너뛴다.
observation_of = {row["trace_id"]: row["observation_id"] for row in SCORE_ROWS if row["trace_id"]}

provenance = [
    {"trace_id": s.trace_id, "observation_id": observation_of.get(s.trace_id), "name": "selected_by",
     "value": STRATEGY, "data_type": "CATEGORICAL", "comment": s.reason}
    for s in SELECTED
]
outcome = push_scores(LANGFUSE, provenance)
print("붙인 점수:", outcome["pushed"], "건, 붙일 곳이 없어 건너뛴 점수:", outcome["skipped"], "건")
```

**관찰할 것.** `push_scores`는 `trace_id`가 없는 점수를 조용히 버리지 않고 **건너뛴 수를 돌려줍니다.** Langfuse 없이 돌렸다면 전부 건너뛴 쪽에 들어갑니다. 점수는 `observation_id`로 root observation에 붙습니다. 이 trace가 `stratified`로 뽑혔다는 사실을 점수로 남겨 두면, 나중에 누군가 이 점수들의 평균을 낼 때 표본이 어떻게 만들어졌는지 되돌아볼 수 있습니다. `signal`로 뽑은 trace에는 이 기록이 특히 중요합니다.

## 6. 7일 매칭량과 비용 예측

Langfuse 화면에서 Rule을 저장하기 전에 "최근 7일 동안 매칭된 observation 수와 예상 비용"을 보여 줍니다. 같은 계산을 우리 숫자로 직접 해 봅니다. 곱셈 몇 번이면 됩니다.

- 7일 매칭량 = 하루 root observation 수 × 7
- 채점 건수 = 7일 매칭량 × 샘플링 비율
- Jev 호출 수 = 채점 건수 × (Episode당 Jev 호출 평균)
- Judge 호출 수 = 채점 건수 × (Episode당 Judge 호출 평균)

Episode당 호출 평균은 방금 채점한 건에서 읽습니다. 의미 점수가 있는 Episode마다 Jev를 한 번 불렀고, `stage`가 `judge`인 점수 하나마다 Judge를 한 번 불렀습니다. **호출당 가격은 이 저장소에서 측정한 값이 없어서 비워 둡니다.** 가격을 알면 `PRICE_*` 두 값을 채우세요. 비워 두면 호출 수만 계산합니다. 이 계산은 미션 M3a-5에서 Claude Code가 만든 함수로 확인하며, M3a-4에서 잰 Judge 넘김 비율을 넣습니다.

하루 요청 수와 샘플링 비율을 바꿔 7일 채점 호출 수를 계산한다. 모델 호출은 없다. 이 호출은 미션 M3a-5에서 Claude Code가 만든다.

```python
# [바꿔보기] 하루 요청 수와 샘플링 비율을 바꿔 7일 채점 호출 수를 계산한다. 모델 호출은 없다.
PRICE_JEV_USD = None     # Jev 호출 1회 가격(달러). 모르면 None으로 둔다.
PRICE_JUDGE_USD = None   # Judge 호출 1회 가격(달러). xhigh는 비싸다. 모르면 None으로 둔다.

# 1단계: 채점한 건에서 Episode당 호출 평균을 읽는다.
scored_episodes = {row["record_index"] for row in SCORE_ROWS if row["stage"] is not None}
judge_calls_seen = sum(row["stage"] == "judge" for row in SCORE_ROWS)
jev_per_episode = 1.0 if scored_episodes else 0.0
judge_per_episode = judge_calls_seen / len(scored_episodes) if scored_episodes else 0.0
print(f"관측: 의미 점수가 있는 Episode {len(scored_episodes)}건, Judge 호출 {judge_calls_seen}회 "
      f"(Episode당 Judge {judge_per_episode:.2f}회)")


def estimate_week(episodes_per_day, sampling, days=7):
    """하루 요청 수와 샘플링 비율로 7일 매칭량과 채점 호출 수를 계산한다. 곱셈뿐이다."""
    matched = episodes_per_day * days
    scored = matched * sampling
    jev_calls = scored * jev_per_episode
    judge_calls = scored * judge_per_episode
    row = {"하루 요청": episodes_per_day, "샘플링": sampling, "7일 매칭": matched, "채점 건수": round(scored),
           "Jev 호출": round(jev_calls), "Judge 호출": round(judge_calls)}
    if PRICE_JEV_USD is not None and PRICE_JUDGE_USD is not None:
        row["예상 비용(USD)"] = round(jev_calls * PRICE_JEV_USD + judge_calls * PRICE_JUDGE_USD, 2)
    return row


# 2단계: 하루 요청 수는 우리 모의 트래픽(하루 DAY_SIZE건)과 가상의 운영 규모 둘을 놓고 본다.
show([estimate_week(DAY_SIZE, 1.0), estimate_week(1000, 0.05), estimate_week(1000, 0.20), estimate_week(10000, 0.05)],
     title="7일 매칭량과 채점 호출 수 (가격 미입력이면 호출 수만)")
```

다음 코드 예시는 실제 모델 `deepseek/deepseek-v4.1-flash-ultrafast`로 소량의 트래픽을 만드는 선택 경로입니다. Episode 8개이고 에이전트 호출은 Episode당 상한 12회를 곱한 96회 이하입니다. scripted 기록과 섞이지 않게 `ENV_LIVE` 환경에 따로 모읍니다. 실제 모델은 드라이버처럼 실수를 일부러 섞지 않으므로 결과가 scripted 표와 직접 비교되지 않습니다. 이 과정의 필수 미션 단계에는 없고 `## 더 해보기 (선택)`에서 요청할 수 있습니다.

실제 모델로 모의 요청 8건을 처리한다. 유료: 에이전트 최대 96회.

```python
# [바꿔보기] 실제 모델로 모의 요청 8건을 처리한다. 에이전트 최대 96회.
announce("실제 모델 모의 트래픽 8 Episode", model_calls=96)
agent_model = settings.make_agent_model(CONFIG)
LIVE_RECORDS = run_traffic(make_traffic(2, 8, seed=SEED), mode="live", model=agent_model,
                           langfuse=LANGFUSE, environment_tag=ENV_LIVE, version="live-baseline")
if LANGFUSE is not None:
    LANGFUSE.flush()
live_verdicts = [evaluate_trajectory(record["artifact"]) for record in LIVE_RECORDS]
show([{"item": record["item_id"], "실행 상태": record["execution_status"],
       "응답 유형": record["artifact"].response.kind if record["artifact"].response else None,
       "모델 호출": record["model_calls"], "비용(USD)": record["cost_usd"], "궤적 판정": verdict.status}
      for record, verdict in zip(LIVE_RECORDS, live_verdicts)], title="실제 모델 트래픽 8 Episode (표시만 한다)")
```

**관찰할 것.** 이 표의 값은 모두 **표시만** 합니다. 실제 모델이 어떻게 답할지 이 문서는 단정하지 않으며 같은 요청에도 응답이 달라질 수 있습니다. 비용 열이 `None`이면 모르는 값을 0으로 바꾸지 않은 것입니다. 이 8건의 `궤적 판정`을 위 scripted 표와 같은 방식으로 읽을 수 있다는 점이 요점입니다. 평가기는 기록의 출처가 드라이버인지 모델인지 묻지 않습니다.

## 확인하지 못한 것

아래는 이 저장소에서 확인하지 못했고 사실처럼 말하지 않습니다.

- 실제 에이전트 모델, Jev, Judge의 응답과 Jev 확률의 보정 정도. 문턱값 0.2~0.8은 **미조정**입니다.
- 실제 Langfuse 서버의 동작: Rule과 Evaluator 실행, 2026-11-16 이후 Cloud 동작. (2026-11-05 저자 1회 실행에서 확인한 것: v2 관측 API가 `traceId` "any of" 조건을 받았고, 기록 직후에는 0건이 읽히다가 약 10초~몇 분 뒤 전부 읽혔다.)
- 서버 쪽 Judge의 비용과 LLM Connection 저장 동작.

## 더 해보기 (선택)

네 가지를 해 봅니다. 각 항목은 Claude Code에게 줄 요청 한 문장과 관찰할 것으로 되어 있습니다. 모델 호출이 있는 항목은 `(유료)`로 표시했으며, Claude Code는 실행 직전에 규모를 한 줄로 알립니다. 코드 예시는 읽기용이고 실행 가능한 스크립트는 Claude Code가 `work/`에 만듭니다.

### 해보기 1. 조용히 틀리는 유형에서 signal이 놓치는 것을 직접 잰다

요청: "`claim_without_record`만 30% 심은 하루치 새 트래픽을 Langfuse 없이 만들고, signal 8건과 random 8건이 `claim-without-record` 규칙에 걸린 Episode를 몇 건씩 뽑는지 세어 줘. `work/`에 스크립트로 만들어 줘."

관찰할 것: signal이 신호로 모은 전체 건수 안에서 해당 Episode가 몇 건인지, random 8건과 비교해 어느 쪽이 더 많이 뽑았는지. `EXERCISE_RATES`와 `K`를 바꿔 달라고 하면 결과가 어떻게 달라지는지도 봅니다. 모델 호출은 없습니다.

```python
# [바꿔보기] claim_without_record만 30% 심은 하루치 트래픽에서 signal이 뽑은 8건 안의 해당 Episode 수를 센다.
EXERCISE_RATES = {"claim_without_record": 0.30}
K = 8

# 1단계: 새 트래픽을 Langfuse 없이 만든다(기본 기록과 섞지 않는다).
exercise_records = run_traffic(make_traffic(1, DAY_SIZE, seed=SEED + 1), mode="scripted",
                               driver=make_mistake_driver(EXERCISE_RATES, seed=SEED + 1))

# 2단계: 해당 규칙이 위반으로 잡은 Episode와 signal이 뽑은 것을 비교한다.
claim_hit = {i for i, record in enumerate(exercise_records)
             if "claim-without-record" in {hit.rule_id for hit in run_rules(record["artifact"])}}
signal_k = {s.record_index for s in select_traces(exercise_records, "signal", K, seed=SEED)}
signal_all_k = {s.record_index for s in select_traces(exercise_records, "signal", len(exercise_records), seed=SEED)}
random_k = {s.record_index for s in select_traces(exercise_records, "random", K, seed=SEED)}

print(f"기록 없는 주장으로 잡힌 Episode: {len(claim_hit)}건")
print(f"signal {K}건이 뽑은 것: {len(claim_hit & signal_k)}건, signal이 신호로 모은 전체 {len(signal_all_k)}건 중: "
      f"{len(claim_hit & signal_all_k)}건")
print(f"random {K}건이 뽑은 것: {len(claim_hit & random_k)}건")
```

### 해보기 2. 두 전략을 섞은 나만의 선정 전략

`signal`은 후보를 먼저 보고 `random`은 비율을 말할 근거를 줍니다. 둘을 반반 섞는 함수를 만들고, 섞은 표본이 한 전략만 쓴 것보다 무엇을 얻고 무엇을 잃는지 표로 확인합니다.

요청: "signal 앞쪽 절반과 random 절반을 섞어 8건을 고르는 함수를 `work/`에 만들고, 전체·random·signal·내 혼합을 한 표에 놓아 줘. 겹치는 trace는 한 번만 넣고 random에서 더 채워 줘."

관찰할 것: 혼합 표본의 선정 이유 종류, 그리고 치명 위반 Episode 열이 signal만 쓴 것과 random만 쓴 것 사이 어디에 놓이는지. 혼합 표본으로 전체 비율을 말할 수 있는지 스스로 설명해 보세요. 모델 호출은 없습니다.

```python
# [내 것 만들기] signal 절반과 random 절반을 섞는 선정 함수. 함수 안의 숫자와 규칙을 마음대로 바꿔 본다.
def mixed_selection(records, k, *, seed):
    """signal 앞쪽 k/2건 + random k/2건. 같은 trace가 겹치면 한 번만 넣고 random에서 더 채운다."""
    half = k // 2
    first = select_traces(records, "signal", half, seed=seed)
    taken = {s.record_index for s in first}
    rest = [s for s in select_traces(records, "random", len(records), seed=seed) if s.record_index not in taken]
    return first + rest[: k - len(first)]


mixed = mixed_selection(RECORDS, 8, seed=SEED)
show([population, profile("random", random_pick), profile("signal", signal_pick), profile("내 혼합", mixed)])
print("혼합 표본의 선정 이유 종류:", Counter(s.reason.split(":")[0] for s in mixed))
```

### 해보기 3. 7일 비용 예측 값을 바꿔 보기

`estimate_week`로 여러분의 가상 운영 규모를 넣어 봅니다. 하루 요청이 5,000건이고 Judge를 하루에 200건까지만 돌릴 수 있다면 샘플링 비율은 얼마여야 합니까? 곱셈으로 먼저 답하고 함수로 확인하세요. 이 항목은 미션 M3a-5와 같습니다.

요청: "하루 5000건, Judge 하루 상한 200건이면 샘플링 상한이 얼마인지, 방금 잰 Judge 넘김 비율로 계산하고 그 샘플링으로 본 7일 호출 수 표를 보여 줘."

관찰할 것: Episode당 Judge 호출 평균이 표본 크기에 따라 바뀐다는 점. 그 평균이 Judge를 한 번도 부르지 않은 표본에서는 계산되지 않는다는 점. 모델 호출은 없습니다.

```python
# [바꿔보기] 하루 5000건, Judge 하루 상한 200건이면 샘플링은 얼마인가. 곱셈으로 먼저 답하고 함수로 확인한다.
EPISODES_PER_DAY = 5000
JUDGE_PER_DAY_LIMIT = 200

if judge_per_episode > 0:
    sampling_limit = JUDGE_PER_DAY_LIMIT / (EPISODES_PER_DAY * judge_per_episode)
    print(f"Episode당 Judge 호출 평균 {judge_per_episode:.2f}회 -> 샘플링 상한 {sampling_limit:.3f}")
    show([estimate_week(EPISODES_PER_DAY, min(1.0, sampling_limit))], title="그 샘플링으로 본 7일")
else:
    print("방금 채점에서 Judge가 한 번도 불리지 않아 Judge 호출 평균을 알 수 없다. 이 값은 표본에 따라 바뀐다.")
```

### 해보기 4. 다른 전략으로 뽑은 10건을 채점해 비교한다 (유료)

같은 모의 트래픽에서 전략만 바꿔 10건을 채점하고 판정 분포가 얼마나 달라지는지 봅니다. 표본 안의 개수이며 전체 비율이 아닙니다. Jev 최대 10회, Judge 최대 30회를 쓰는 유료 호출입니다.

요청: "내 전략이 아닌 다른 전략(예: signal) 10건을 `evaluate_records_locally`로 채점하고 점수 이름과 값별 개수 표를 보여 줘."

관찰할 것: 전략을 바꾸면 `trajectory_status`와 의미 점수의 분포가 어떻게 달라지는지, 그리고 그 차이를 전체 비율로 읽으면 안 되는 이유.

```python
# [바꿔보기] 다른 전략으로 뽑은 10건을 채점한다. Jev 최대 10회, Judge 최대 30회.
EXERCISE_STRATEGY = "signal"   # random, stratified, signal, novelty 중 하나

announce("다른 전략 10건 채점", model_calls=0, jev_calls=10, judge_calls=30)
other = select_traces(RECORDS, EXERCISE_STRATEGY, 10, seed=SEED, golden_shapes=GOLDEN_SHAPES)
other_rows = evaluate_records_locally([RECORDS[s.record_index] for s in other],
                                      decider=decisions.make_decider(CONFIG),
                                      judge_model=settings.make_judge_model(CONFIG))
other_counts = Counter((row["name"], row["value"]) for row in other_rows)
show([{"점수 이름": name, "값": value, "개수": count}
      for (name, value), count in sorted(other_counts.items(), key=lambda item: str(item[0]))],
     title=f"{EXERCISE_STRATEGY} 표본 {len(other)}건 안의 점수 개수 (전체 비율이 아니다)")
```

추가로 해 볼 수 있는 선택 요청이 둘 더 있습니다.

- (유료) 실제 모델 모의 트래픽: "2일차 모의 요청 8건을 실제 에이전트 모델로 처리해 `traffic-03a-live` 환경에 따로 모으고 궤적 판정을 표로 보여 줘." 6절의 마지막 코드 예시에 해당하며 에이전트 호출이 최대 96회입니다. 관찰할 것은 scripted 표와 같은 방식으로 궤적 판정을 읽을 수 있다는 점이고, 이 결과로 모델 성능을 말하지 않습니다.
- seed 흔들림: "random의 seed를 0~9로 바꿔 8건 안의 치명 위반 수를 보여 줘." 3절의 코드 예시에 해당하며 호출이 없습니다. 관찰할 것은 같은 전략이라도 한 번의 8건이 우연의 영향을 받는다는 점입니다.

## 확인 질문

답은 이 문서가 알려 주지 않습니다. 자기 말로 설명할 수 있어야 합니다.

1. 운영 trace를 채점할 때 "기대 최종 상태와 일치하는가"를 쓸 수 없는 이유를 말하세요. 그럼 운영에서 쓸 수 있는 정답 불필요 지표 세 가지는 무엇이고 판정자는 각각 누구입니까?
2. `signal`로 뽑은 20건에서 치명 위반이 6건 나왔습니다. "치명 위반률이 30%"라고 보고해도 됩니까? 그렇지 않다면 어떤 표본이 필요합니까?
3. Rule과 Evaluator는 각각 무엇을 정합니까? trace-level evaluator가 observation-level evaluator로 바뀌면 이 저장소의 평가기는 어디에서 입력을 읽습니까?
4. 평가기에 넘긴 Episode 요약이 잘려서 JSON으로 읽히지 않을 때, 평가기는 왜 PASS가 아니라 INCOMPLETE를 돌려줘야 합니까?
5. 모의 트래픽의 FAIL 비율이 25%라는 숫자를 "에이전트가 25% 틀린다"로 말하면 무엇이 틀립니까?
6. 서버 쪽 LLM Judge를 켜기 전에 확인해야 할 비용과 키 문제는 무엇입니까?

## 정리

- 운영 trace에는 정답이 없다. 쓸 수 있는 것은 궤적 규칙, 응답과 기록의 일치, Jev·Judge 의미 판단이다. 기대 상태 비교는 오프라인에서만 한다.
- 표본 선정은 예산 때문에 하는 선택이고 전략마다 놓치는 것이 다르다. `random`과 `stratified`는 비율을, `signal`과 `novelty`는 "무엇을 먼저 볼까"를 말한다. `signal` 표본으로 전체 비율을 말하지 않는다.
- Rule은 무엇을, Evaluator는 어떻게 채점할지 정한다. observation-level에서는 root observation 하나가 Episode 하나이고 평가기는 그 output의 요약을 읽는다. Langfuse Cloud의 trace-level evaluator는 2026-11-16에 결과 생성을 멈춘다.
- 주 경로는 SDK의 `batch_evaluate`와 `online_evaluators`이고, Langfuse가 없으면 `evaluate_records_locally`가 같은 평가기를 돌린다. 점수는 `push_scores`로 observation에 붙이고 건너뛴 수를 숨기지 않는다.
- 7일 매칭량과 비용은 곱셈으로 미리 계산한다. 호출당 가격은 측정한 값이 없으면 비워 둔다.
- 이 과정의 트래픽은 모의 트래픽이다. 모델 성능을 말하지 않는다. 확인하지 못한 것(실제 모델 응답, Langfuse 서버 쪽 동작)은 **미확인**으로 남긴다.

다음 문서(`concepts/m3b.md`)에서는 궤적 규칙 자체를 어떻게 정하고 어떻게 믿는지(평가기 평가)를 다룹니다.

## 7. 배경 운영 로그에서 선정 전략을 다시 본다

앞 절의 풀은 이틀치 60건이었습니다. 운영의 풀은 며칠에 걸쳐 쌓이고 사건이 특정 시간대와 특정 배포 버전에 몰려 있습니다. 이 과정은 그 모양을 흉내 낸 **합성 배경 운영 로그** 7일치(environment `synth_ops`)를 m0에서 한 번 적재합니다. 이야기는 이렇습니다. 1~4일차는 평소, 5일차 14~16시에 결제 도구가 느려지는 장애, 6일차에 agent-v2 canary, 7일차에 ops-resume 요청이 몰립니다. 이 로그는 **합성 데이터이지 모델 성능이 아닙니다.** 여기서 나온 비율과 지연을 "에이전트가 이렇다"로 읽지 않습니다.

풀이 커지고 시간에 퍼지면 같은 k건이 덮는 범위가 달라집니다.

- `random`: 풀 전체에서 k건이라 사건이 몰린 하루(5일차 시간대)는 k가 작으면 한 건도 안 들어올 수 있습니다.
- `stratified`: (family, day) 층마다 돌아가므로 날짜는 고르게 덮지만, 하루 안의 시간대와 version은 층에 숨습니다. 층은 우리가 아는 분류입니다.
- `signal`: 도구 오류, 지연 상위, 규칙 위반이 몰린 날과 version을 먼저 뽑습니다. 장애와 canary 같은 사건은 잘 찾지만, 신호가 없는 조용한 위반과 평소 날의 비율은 놓칩니다.
- `novelty`: Golden에 없는 요청 모양을 뽑습니다. 7일차의 새 요청 모양은 찾지만 날짜나 version의 문제는 보지 않습니다.

그래서 "어느 전략이 낫다"가 아니라 "이 풀에서 이 전략이 무엇을 덮고 무엇을 놓쳤는가"를 표로 확인합니다. 아래는 읽기용 예시이며 미션 M3a-3b에서 Claude Code가 `work/`에 만들어 돌립니다. 모델 호출은 없습니다.

```python
# [바꿔보기] 배경 운영 로그를 읽어 네 전략이 덮는 날과 version을 센다. 모델 호출 0회.
from collections import Counter
from pathlib import Path

from eval_lab import synth
from eval_lab.online import request_shape, select_traces

# 1단계: m0에서 synth_load가 출력한 "로컬 기록" 경로를 넣는다.
RECORDS = synth.read_local_records(Path("PRINTED_PATH/episodes.jsonl"))  # PRINTED_PATH는 출력된 폴더로 바꾼다
K, SEED = 20, 7
# novelty는 비교할 Golden 모양이 필요하다. 여기서는 처음 이틀의 모양을 기준으로 둔다(수업용 가정).
golden_shapes = {request_shape(r) for r in RECORDS if r["story_day"] <= 2}

# 2단계: 같은 k와 seed로 네 전략을 돌리고, 덮은 날과 version을 센다.
for strategy in ("random", "stratified", "signal", "novelty"):
    picks = select_traces(RECORDS, strategy, K, seed=SEED,
                          golden_shapes=golden_shapes if strategy == "novelty" else None)
    picked = [RECORDS[p.record_index] for p in picks]
    days = Counter(r["story_day"] for r in picked)
    versions = Counter(r["version"] for r in picked)
    missed = sorted(set(range(1, 8)) - set(days))
    print(strategy, len(picks), "건", "날", dict(sorted(days.items())), "version", dict(versions), "덮지 못한 날", missed)
```

확인할 것은 두 가지입니다. 뽑힌 건수가 k보다 적은 전략(signal)이 있는지, 그리고 덮지 못한 날이 어느 전략에서 나오는지입니다. 이 표본의 비율을 전체 비율로 말하지 않습니다.
