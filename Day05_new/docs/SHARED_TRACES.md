# SHARED_TRACES — 공통 trace 배포·채점 설계 (저자용)

수강생 전원이 **같은 실제 trace를 채점**하게 하기 위한 구현 참고 자료다. 이 문서를 읽는 코딩 에이전트는
2장의 확인된 사실을 재조사하지 말고, 3~6장의 규격대로 구현한 뒤 8장의 검증을 통과시킨다.

**하지 않는 것:** Langfuse API 키를 수강생에게 나눠 주는 방식은 쓰지 않는다. 한 프로젝트에 전원의
trace가 섞이고(04의 environment 필터 비교가 오염됨), 쓰기·삭제 권한과 비용 책임이 통째로 공유되며,
`.env`를 수강생이 직접 채운다는 이 폴더의 원칙(`../AGENTS.md` 3장)이 깨진다. 공통 소재는 **git으로
배포하고**, Langfuse 화면이 필요하면 수강생이 **각자 자기 프로젝트**에 올린다(6장).

---

## 1. 목적과 개요

- 03a·03b의 채점 실습 소재를 수강생마다 다르게 생성하지 않고, **저자가 1회 녹화한 동일 파일**로 맞춘다.
- 기대 효과: (a) Code 궤적 판정은 결정적이라 전원이 같은 표를 얻는다("재현됩니다", 03b 1절의 실증),
  (b) Jev·Judge 유료 채점은 같은 입력에서도 판정이 갈릴 수 있어 "1회 관찰" 문화를 그대로 실습한다,
  (c) 수강생끼리 판정이 갈린 Episode를 비교할 수 있다.
- 흐름: **녹화(강사 1회, 유료) → `data/`에 JSON 배포(git) → 수강생 노트북이 파일을 읽어 records 복원 →
  기존 선정·채점 코드를 그대로 실행**. 새 평가 코드는 만들지 않는다.

## 2. 확인된 사실 (2026-11-05 기준, 줄이 밀리면 다시 확인)

`../AGENTS.md` 10장 관례에 따라 근거를 적는다.

| 사실 | 근거 |
|---|---|
| `run_traffic`가 record 목록을 돌려준다. record 키는 `artifact, item_id, day, style, family_id, fixture_id, latency_ms, model_calls, input_tokens, output_tokens, cost_usd, trace_id, execution_status, injected_mistakes` | `eval_lab/traffic.py:399`(`record_from_artifact`), `eval_lab/traffic.py:425`(`run_traffic`) |
| record의 모든 소비자(`select_traces`, `evaluate_records_locally`, `local_metrics`)는 이 dict를 그대로 받는다 | `eval_lab/online.py:149`, `eval_lab/online.py:525`, `eval_lab/monitoring.py:112` |
| `Artifact`는 pydantic `Contract`라 `model_dump()` 직렬화·`model_validate()` 복원이 된다 | `eval_lab/contracts.py:131`. JSON 왕복은 06 재생 풀이 이미 증명(`eval_lab/replay.py:145,166`) |
| 채점 진입 함수는 `Artifact` 모델을 받는다 → 로드 셀에서 복원 필수 | `eval_lab/episodes.py:185`(`episode_summary`), `eval_lab/trajectory_rules.py:450`(`evaluate_trajectory`) |
| `make_traffic`은 **dev 시나리오의 입력만** 가져온다. 기대 상태·holdout을 담지 않는다 | 03a 노트북 2절 md |
| 모델·판정기 클라이언트는 `eval_lab.settings` / `eval_lab.decisions` factory로만 만든다. 오프라인 실행기(`tests/run_fake.py`)가 이 자리를 갈아 끼운다 | `../AGENTS.md` 2장. 노트북 실제 사용례: `settings.make_judge_model(CONFIG)`, `decisions.make_decider(CONFIG)` (`eval_lab/decisions.py:183`) |
| 유료 셀은 실행 직전 `announce`로 규모를 고지해야 한다(구조 검사 대상) | `eval_lab/notebook.py:23`, `tests/check_notebook.py`(검사: 유료 고지·스위치 규칙·키 패턴·금지 문구·저장된 출력) |
| 녹화·배포 기록은 "저자의 1회 관찰"로 라벨한다. 가짜/녹화를 실제 결과처럼 말하지 않는다 | `../AGENTS.md` 8장 6번 |
| (선택) 재생 풀을 Langfuse Dataset으로 올리는 도구가 이미 있다 | `eval_lab/replay.py:271`(`to_langfuse_dataset`) |

## 3. 배포 파일 규격

- **경로**: `data/shared_traces/<label>-v<버전>.json` (예: `data/shared_traces/live-baseline-v1.json`).
  `data/`는 git에 포함되고 수강생이 읽는 곳이다. `outputs/`는 git 제외라 쓰지 않는다.
- **최상위 구조**:

```json
{
  "schema": "day05-shared-traces/1",
  "label": "live-baseline-v1",
  "recorded_at_utc": "2026-11-05T…",
  "model": "deepseek/deepseek-v4.1-flash-ultrafast",
  "effort": "medium",
  "release": "baseline",
  "policy_version": "order-policy-v1",
  "seed": 7,
  "counts": {"total": 20, "live": 20, "scripted": 0},
  "notes": "저자의 1회 관찰 녹화입니다. 실행마다 달라지는 모델의 한 번 결과이며 재현 원자료가 아닙니다.",
  "records": [ { …record… }, … ]
}
```

- **record 한 줄**: `run_traffic`가 돌려준 dict에서 `artifact`만 `model_dump(mode="json")`한 것.
  나머지 키는 그대로 둔다. `injected_mistakes`는 live 녹화에서 빈 리스트로 남긴다(지우지 않는다).
- **scripted 트래픽을 섞으면** 반드시 `source: "live" | "scripted"` 필드를 record마다 붙이고
  `counts`에 둘을 나눠 적는다. live를 "실제 모델 trace"로 부를 수 있는 건 `source: "live"` 행뿐이다.
- **금지**: holdout 카드에서 온 입력·기대 상태·`family_id`가 `hv-*`인 어떤 값도 파일에 들어가면 안 된다
  (`make_traffic`이 dev 입력만 쓰므로 정상 경로에서는 발생하지 않는다. 저장 전에 `hv-` 접두사 검사).
- **키·비밀**: 파일에 `.env` 값이나 trace URL의 토큰이 들어가면 안 된다. 커밋 전 `tests/check_secrets.py`를 돌린다.

## 4. 녹화 절차 (강사 1회, 유료 — 실행 직전 규모 고지 필수)

일회성 도구로 진행한다(도구는 커밋하지 않아도 된다). 절차:

1. **트래픽 생성**: `make_traffic(day, n, seed=…)`(`eval_lab/traffic.py:137`). 위험이 많은 2일차 분포를
   포함시킨다(환불 TIMEOUT·결제 장애·타 고객 주문 가족).
2. **실행**: `run_traffic(items, mode="live", model=lab_settings.make_agent_model(SETTINGS),
   langfuse=langfuse_or_none(SETTINGS), environment_tag="day05_shared", version="<label>")`
   (`eval_lab/traffic.py:425`). `environment_tag`을 배포 라벨과 다르게 남겨야 나중에 강사 프로젝트에서
   이 녹화만 골라 볼 수 있다.
3. **저장**: 3장 규격대로 JSON으로 쓴다.
4. **위반 밀도 확인(필수)**: 실제 모델은 실수를 일부러 섞지 않는다(03a 노트북 "이 노트북에서 확인하지
   못한 것" 위 참조). 저장 전에 `evaluate_trajectory(artifact)`로 치명 위반 건수를 센다.
   - 치명 위반이 0건이면 채점 실습이 단조로워진다. 대응은 둘 중 하나: (a) 2일차·위험 가족 비중을 높여
     재녹화, (b) `make_mistake_driver` scripted 트래픽을 섞고 `source`로 라벨(3장).
   - 기준은 정하지 않는다. 저자가 표를 보고 판단한다(위반 0건 + 경고만 몇 건이면 재검토 권장).
5. **규모 예시**: n=20 live 녹화는 에이전트 호출 상한 20×12=240회(에피소드당 상한 `MAX_MODEL_CALLS` 12,
   실측은 그보다 적다). 실행 직전 한 줄로 고지한다.

## 5. 노트북 반영 규격 (03a에 절 추가를 권장)

03a의 "5. 선정한 trace를 일괄 채점" 뒤에 "공통 trace로 같은 소재 채점하기" 절을 넣는다. 셀 구성:

**① 안내 md 셀** — 목적(전원 같은 소재), 파일 출처와 "저자의 1회 관찰 녹화" 라벨, Code 판정은 무료·
Jev/Judge는 유료라는 고지.

**② 로드 셀(무료)** — 계약:

```python
import json
from eval_lab.contracts import Artifact

with open(ROOT / "data" / "shared_traces" / "live-baseline-v1.json", encoding="utf-8") as f:
    SHARED = json.load(f)
SHARED_RECORDS = [dict(r, artifact=Artifact.model_validate(r["artifact"])) for r in SHARED["records"]]
# 검증: 라벨·개수·hv- 없음을 assert로 확인하고 실패를 조용히 넘기지 않는다.
```

- record 개수·라벨이 md의 안내와 다르면 `ValueError`로 멈춘다(조용히 넘기지 않는다).
- 무료 셀이어도 `announce("공통 trace 로드", model_calls=0)` 한 줄을 남겨 규칙을 맞춘다.

**③ Code 채점 셀(무료, 기본 경로)** — `evaluate_trajectory(record["artifact"], complete=True)`를
records마다 돌려 표 출력. **어떤 모델도 부르지 않는다.** 전원이 같은 판정을 얻는 것이 이 절의 요점이므로
md에 "같은 파일, 같은 판정 — 규칙은 재현됩니다"를 명시한다.

**④ Jev/Judge 채점 셀(유료, `RUN_EXERCISE` 뒤 권장)** — 기존 패턴 그대로:

```python
announce("공통 trace 의미 판정", model_calls=0, jev_calls=<N>, judge_calls=<3N>)
rows = evaluate_records_locally(SHARED_RECORDS, decider=decisions.make_decider(CONFIG),
                                judge_model=settings.make_judge_model(CONFIG))
```

- `judge_calls` 산식은 03a cell 26의 관례(질문 3개 × 건수)를 따른다. `announce` 숫자는 실제 셀 파라미터와
  함께 고친다(02 노트북 6절: "고지는 숫자를 대신 계산해 주지 않는다").
- 유료 셀의 모델·판정기는 반드시 `eval_lab.settings`·`eval_lab.decisions` factory로만 만든다.
  그래야 `tests/run_fake.py`의 가짜 갈아끼우기가 통과한다.
- 스위치 배치(`RUN_EXERCISE`/`RUN_OPTIONAL`)와 announce 형식은 `tests/check_notebook.py` 검사를
  통과해야 한다. 애매하면 기존 유료 셀(03a cell 26, 03b 7절)과 같은 모양으로 맞춘다.

**⑤ 확인 질문 1~2개 추가** — 예: "같은 파일을 채점한 옆 사람의 Code 판정 표와 다른 점이 있는가?
Jev·Judge 판정은 어떤가? 어느 쪽 차이가 왜 생기는지 자기 말로."

## 6. (선택) Langfuse 화면 실습

공통 소재를 각자 자기 Langfuse 프로젝트의 Dataset으로 올린다. `to_langfuse_dataset`
(`eval_lab/replay.py:271`)이 풀을 Dataset으로 올리는 도구다. 주의:

- 이 함수는 `PoolEpisode`(events + 판정 라벨)를 올린다. 공통 trace 파일에서 풀 모양으로 바꾸려면
  `build_pool`(`eval_lab/replay.py:112`)을 쓰거나 같은 모양으로 변환한다.
- 셀은 `langfuse_or_none` 경로를 따르고(키 없으면 "로컬 경로" 안내 후 건너뛴다), 채점 비용은 발생하지
  않는다(기록 업로드만).
- 수강생이 자기 키로만 올린다는 안내 문장을 넣는다. 강사 키·강사 프로젝트는 쓰지 않는다.

## 7. 원칙 준수 체크리스트

- [ ] 파일에 `hv-*`(holdout) 값이 없다.
- [ ] 파일에 키·토큰·`.env` 값이 없다(`tests/check_secrets.py` 통과).
- [ ] 라벨에 "저자의 1회 관찰 녹화"가 들어 있다. scripted 혼합 시 `source`로 구분했다.
- [ ] 유료 셀은 `announce` 직전 고지, 스위치 규칙, factory 경로를 지켰다.
- [ ] 채점 결과에서 실패·판정 불능 행을 지우거나 골라 내지 않는다(`../AGENTS.md` 8장).
- [ ] `PREREG` 블록(`docs/DESIGN.md`)은 건드리지 않는다. 이 기능은 사전 등록 측정(P3)과 무관한
  수업 소재 배포다. 측정에는 절대 이 공통 파일을 쓰지 않는다(P3은 노트북 06/`tests/run_measurement.py`
  경로만).

## 8. 완료 검증

구현 뒤 저장소 루트에서 아래를 모두 통과시킨다. 하나라도 깨지면 원인을 고쳐 통과시키고, 검사를 고치거나
한도를 올려서 맞추지 않는다.

```bash
uv run --no-sync pytest Day05_new/tests -q        # 유닛 테스트 전체
uv run --no-sync python Day05_new/tests/check_notebook.py --all   # 노트북 구조 검사(새 셀 포함)
uv run --no-sync python Day05_new/tests/run_fake.py <바뀐 노트북> # 가짜 모델로 3패스 통과
uv run --no-sync python Day05_new/tests/check_secrets.py          # data/ 신규 파일 포함 유출 검사
```

마지막으로 실제 키로 바뀐 노트북을 1회 실행해: 로드 셀의 검증 통과, Code 채점 표가 무료로 완성,
유료 셀의 announce 대비 실제 호출 수가 상한 이내인지를 확인하고 결과를 이 문서 아래에 날짜와 함께
덧붙인다.

## 9. 이 문서의 근거 유효 기간

2장의 `파일:줄`은 2026-11-05에 확인했다. 코드를 고치면 줄이 밀린다(`../AGENTS.md` 10장 관례).
노트북을 고치면 예고 숫자(announce 인자)도 같이 고쳐야 하며, 최종 규모는 노트북의 `announce` 줄이
정답이다.
