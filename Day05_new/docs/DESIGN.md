# Day05_new 설계와 사전 등록

작성일 2026-11-02. `Day05/`는 그대로 두고 `Day05_new/`를 노트북 과정으로 만든다. 이 문서는 설계와 사전 등록(pre-registration)을 한 곳에 둔다.

**상태: 확정(2026-11-02, 저자 검토 게이트 통과).** 사전 등록 블록(`PREREG:BEGIN`~`PREREG:END`)의 sha256은 `docs/prereg.sha256`에 고정했고 `tests/check_prereg.py`가 대조한다. 블록은 수정하지 않는다. 바꿔야 하면 문서화된 개정으로만 바꾼다. 측정 결과는 블록 뒤에 별도 절로 덧붙인다.

근거 노트는 `docs/sources/`에 있다. 도구 사실은 `docs/sources/platform-2026-11.md`, 참고 글은 `docs/sources/trajectory-eval.md`, 논문은 `docs/sources/dream-rsi.md`다. 이 문서의 도구 주장은 그 노트의 행을 따른다.

## 1. 목적과 저자 결정

저자가 정한 과정 개요(원문 그대로):

- Day05 주제: Agent 평가 및 모니터링
- Part 1. 왜 Agent를 평가하는가
- Part 2. 오프라인 평가와 Golden Dataset
- Part 3. 온라인 평가와 Trace 선정 & Trajectory 평가에 대한 이해 (참고: https://tmdgusya.github.io/roach-blog/posts/trajectory-eval/)
- Part 4. Agent Monitoring
- Part 5. 평가와 모니터링의 결합으로 지속적으로 운영하기.
- 실습: Self-Improving Agent(RSI와 Observability (기본 개념 / Agent Trace와 평가 데이터 연결 / 관측 플랫폼 연동·활용 데이터 축적) (참고: https://github.com/zhengkid/Dream-RSI)

저자 결정(2026-11-02):

- 모델은 `ChatAnthropic`으로 연동한다.
- **Judge는 `claude-sonnet-5-5`, effort `xhigh`로 평가한다.**
- **Judge 전에 Jev(Decision API)도 평가에 쓴다.** 평가 순서는 Code → Jev → Judge다(6절).
- 나머지는 계획의 추천안대로 한다.
  - 관통 사례는 주문 취소·결제 환불·예약 재고 복원이다. `Day05/business_lab`을 이식한다.
  - 저자의 `Day05/Day5_이론자료.pdf`를 Part 1·2와 Trace 읽기의 원재료로 쓴다. p47(trace 단위 Judge 변수 매핑)은 observation-level Rule·Evaluator로 다시 쓴다.
  - 실습의 RSI는 **하네스 정책 코드를 기록 재생으로 개선**하고 holdout에서 실제 모델로 다시 확인하는 방식으로 옮긴다(11절).
  - `Day05/오전.md`·`오후.md`의 자유 실습(문서로 Golden 만들기)은 02의 "문서 기반 합성 후보 → 검수" 절로 흡수한다.
  - 총 약 6.5시간.
  - Langfuse는 2026-11-16 전환 **이후의 구조만** 가르친다.
  - 온라인 평가의 주 경로는 SDK `run_batched_evaluation`이다. Langfuse 서버에서 도는 LLM-as-a-Judge(수강생이 자기 키를 Langfuse LLM Connection에 등록해야 함)는 선택 경로다.
- 다른 `_new` Day와 같은 원칙을 따른다: 채점 없음, 모든 코드 제공, 직접 해보기와 확인 질문만 둔다. 새 패키지를 더하지 않는다(uv `exclude-newer` 2026-10-31).

## 2. 가정 (바꿀 수 있음)

- 에이전트: `claude-sonnet-5-5`, effort `medium`(Day04_new와 같은 기본값). `.env`의 `DAY05_MODEL`, `DAY05_EFFORT`로 바꾼다.
- Judge: `claude-sonnet-5-5`, effort `xhigh`. `DAY05_JUDGE_EFFORT`로 바꿀 수 있지만 기본값은 저자 결정값이다. 에이전트와 Judge가 같은 모델이고 effort만 다르다. 이 선택이 만드는 자기 선호 위험은 사람 라벨 보정(6.4절)의 false pass로 드러낸다.
- 개선기(06의 정책 후보 생성): `claude-sonnet-5-5`, effort `high`. 저자 지정값이 아니므로 바꿀 수 있다.
- 시간: 00 10분, 01 40분, 02 60분, 03a 45분, 03b 55분, 04 45분, 05 45분, 06 90분 = 390분.
- Langfuse 키는 12절 5번 항목으로 결정했다. 저자가 `Day05/.env`에서 복사해 `Day05_new/.env`에 넣고(값은 출력하지 않는다), 수강생용 안내는 `.env.example`이다.

## 3. 2026-11 기준 갱신 항목

기존 `Day05/`와 비교해 바뀌는 것이다. 각 행의 근거는 `docs/sources/platform-2026-11.md`의 해당 절이다.

| # | 항목 | 기존 Day05 | Day05_new | 근거 절 |
|---|---|---|---|---|
| U1 | Langfuse 평가기 구조 | PDF p47이 trace 단위 Judge 매핑 | Evaluator와 Rule 분리, observation-level, `isRootObservation`. Cloud의 trace-level evaluator는 2026-11-16에 멈춘다 | 2.2 |
| U2 | Trace I/O | 해당 호출 없음 | 평가기 매핑은 root observation 기준. `set_trace_io` 계열을 쓰지 않는다 | 2.2, 2.3 |
| U3 | 기록된 trace 일괄 채점 | 로컬 원자료 재채점만 | `run_batched_evaluation`으로 운영 trace 채점, 새 평가기 backtest | 2.1 |
| U4 | 사람 검수 | CSV 수작업 | annotation queue에 선정 trace를 넣는다. CSV 경로는 키 없는 대체 경로로 유지 | 2.1, 2.2 |
| U5 | DeepEval 에이전트 지표 | `GEval`, `FaithfulnessMetric` | `ToolCorrectness`, `ArgumentCorrectness`, `ToolPermission`, `TaskCompletion`, `StepEfficiency`, `PlanAdherence`, `AgentLoopDetection`을 규칙 검사와 나란히 비교 | 3.1 |
| U6 | 궤적 판정 | PASS/FAIL/`INSUFFICIENT_EVIDENCE` | 판정 5종, 치명·경고 등급, 복구 창, 평가기 평가(Wilson 구간), 반사실 재생 | `trajectory-eval.md` |
| U7 | 모니터링 | 없음 | Metrics API v2(observations view), 사전 고정 경보 기준, OTel GenAI 이름(안정화 미확인) | 2.1, 6 |
| U8 | 자기 개선 | 사람이 Prompt 한 조건 변경 | 하네스 정책을 재생으로 고르고 holdout에서 재확인 | `dream-rsi.md` |
| U9 | 모델 | OpenRouter `gemini-3.8-flash`, Judge `claude-haiku-4.5` | `ChatAnthropic` `claude-sonnet-5-5`, Judge 같은 모델 `xhigh`, 그 앞에 Jev | 4, 5 |
| U10 | 형식 | 스크립트 00~09와 PDF | 노트북 00~06, 실습 패키지 `eval_lab/`, 검사기 | — |

## 4. 노트북 지도

| 노트북 | Part | 분 | 핵심 질문 | 기존 Day05에서 가져올 것 | 새로 만들 것 |
|---|---|---|---|---|---|
| `00-Setup.ipynb` | 준비 | 10 | 키·연결·버전이 준비되었는가 | `Day05/00_check_env.py` | 키 설정됨/미설정, Langfuse 인증, SDK ≥ 4.7.0 확인, Claude·Jev·Judge 각 1회 |
| `01-Why-Evaluate.ipynb` | 1 | 40 | 그럴듯한 답이 왜 업무 성공의 증거가 못 되는가 | PDF p2~5, scripted 두 경로 | 답변·결과·과정 3분리, 같은 응답 다른 궤적, 비결정성(pass@k, pass^k), "낮은 점수"와 "평가 불능" 구분 |
| `02-Offline-Golden-Dataset.ipynb` | 2 | 60 | 무엇을 성공으로 볼지 어떻게 고정하는가 | PDF p6~21, `authoring.py`, `01`~`02`, `05`~`07` | Scenario 계약, 세 확보 경로(인터뷰·문서·운영 trace), 최소쌍, 커버리지, 검수·동결 해시, dev/holdout, Langfuse Dataset 버전과 `run_experiment`, Code·Jev·Judge·Human 역할, **문서 기반 합성 후보 → 검수**(DeepEval Synthesizer 대신 정책 문서로 후보를 만들고 사람이 승인) |
| `03a-Online-Eval-Trace-Selection.ipynb` | 3 | 45 | 정답이 없는 운영 trace를 무엇으로, 어떤 것부터 채점하는가 | — | 모의 운영 트래픽, 정답 필요 지표와 정답 불필요 지표의 구분, 표본 선정 전략 4종, Rule(무엇)과 Evaluator(어떻게), observation-level, `run_batched_evaluation`, 점수를 observation에 연결, 7일 매칭량과 비용 예측 개념 |
| `03b-Trajectory-Eval.ipynb` | 3 | 55 | 궤적의 순서를 어떻게 판정하고, 평가기는 어떻게 믿는가 | PDF p16~17, p26~30, p42~45, `counterexamples.py` | 궤적 규칙(7절), 치명·경고, 판정 5종, 읽기 예산, 글자≠행동, DeepEval 에이전트 지표·Jev·Judge와 비교, 평가기 평가(결함 주입·정상 변형, 재현율·오탐률, Wilson 95%) |
| `04-Agent-Monitoring.ipynb` | 4 | 45 | 평가와 무엇이 다르고, 무엇을 언제 경보하는가 | — | 지표 체계(9절), Metrics API v2 질의, release·environment 태그, 입력 분포 변화, 사전 고정 경보 기준, OTel GenAI 이름(안정화 미확인) |
| `05-Continuous-Operation.ipynb` | 5 | 45 | 평가와 모니터링을 어떻게 하나의 운영 루프로 묶는가 | `08_promote_regression.py`, `09_report_decision.py`, `evidence.py` | 10절 루프, annotation queue, 회귀 Golden 승격(새 데이터 버전), 평가기 변경 관리(두 버전 재채점, 새 평가기 backtest), 승인 게이트 |
| `06-Lab-Self-Improving-Agent.ipynb` | 실습 | 90 | 에이전트가 자기 trace로 스스로 나아지게 하려면 무엇을 고정하고 무엇을 열어야 하는가 | — | 06.1 RSI 기본 개념, 06.2 Trace와 평가 데이터 연결(재생 풀), 06.3 관측 플랫폼 연동과 데이터 축적, 06.4 라운드 실행과 holdout 재확인, 06.5 보상 해킹 반례 |

## 5. 실습 패키지 `eval_lab/`

| 모듈 | 출처 | 책임 |
|---|---|---|
| `settings.py` | `Day04_new/cap_lab/settings.py`를 고친 사본 | `Day05_new/.env` 한 파일만 읽기, 키 상태(설정됨/미설정), 에이전트·Judge·개선기 모델 생성 |
| `decisions.py` | `Day04_new/cap_lab/decisions.py`를 고친 사본 | Jev 호출(Noul/Choice/Score), 사용량 콜백 |
| `contracts.py`, `environment.py`, `episodes.py`, `dataset.py`, `authoring.py` | `Day05/business_lab/` 이식 | Scenario·Artifact 계약, SQLite 업무 환경과 장애 주입, 여러 턴 Episode, 작성·검수·동결 |
| `agent.py` | `Day05/business_lab/agents.py` 이식 후 `ChatAnthropic`으로 교체 | 에이전트, 도구, 하네스 정책 훅(11절) |
| `evaluators.py`, `reporting.py`, `evidence.py` | `Day05/business_lab/` 이식 | 업무 평가기, pass@k·pass^k·bootstrap, 근거·사람 라벨 보정·회귀 승격 |
| `judges.py` | 새로 | 평가 단계 Code → Jev → Judge(6절), DeepEval 어댑터(`DeepEvalBaseLLM` 안에서 `ChatAnthropic(reasoning_effort="xhigh")`) |
| `trajectory_rules.py` | 새로 | 7절 규칙, 판정 5종, 읽기 예산 |
| `meta_eval.py` | 새로 | 결함 주입·정상 변형 생성, 재현율·오탐률·정밀도, Wilson 95% 구간 |
| `traffic.py` | 새로 | 모의 운영 트래픽(요청 문형 × fixture × 날짜별 분포 변화) |
| `online.py` | 새로 | 표본 선정 전략, `run_batched_evaluation` 감싸기, Rule·Evaluator API(선택), annotation queue |
| `monitoring.py` | 새로 | Metrics API v2 질의, 로컬 원자료에서 같은 지표 계산(키 없는 대체), 경보 판정 |
| `replay.py`, `rsi.py` | 새로 | 재생 풀, 정책 명세 해석기, 재생 점수, 개선기 루프, holdout 게이트 |
| `notebook.py` | 새로 | 노트북 도우미(`announce` 비용 고지, 표 출력) |

**기록 요구 사항**: scripted든 실제 모델이든 모든 Episode는 root observation 하나 안에서 실행하고, 그 안에서 `propagate_attributes(session_id=<episode_id>, version=<정책·Prompt 버전>, environment=<날짜·용도>, tags=[...])`를 건다(`site-packages/langfuse/_client/propagation.py:114`). 기존 `run_scripted`는 LangChain `CallbackHandler`가 없고 `env.call`만 서비스 observation을 남긴다. 부모 span이 없으면 서비스 호출마다 따로 trace가 될 수 있다. Metrics API v2에는 traces view가 없으므로(`site-packages/langfuse/api/metrics/client.py:26`) Episode 단위 지연과 비용은 root observation에서만 읽힌다. 이 요구는 fake Langfuse 테스트로 증명한다.

테스트는 `tests/`에 둔다. 모델·Jev·Langfuse는 모두 fake로 바꿔 키 없이 돈다(Day04_new `tests/fakes.py` 방식). `tests/check_notebook.py`는 Day04_new 검사기를 고친 사본이다.

## 6. 평가 단계: Code → Jev → Judge

### 6.1 무엇을 누가 판정하는가

| 항목 | 판정자 | 이유 |
|---|---|---|
| 최종 업무 상태, 보호 상태, 대상·순서 정책, 복구, 필수 이정표, Episode 종료 | **Code** (`evaluators.py`, `trajectory_rules.py`) | 사실 검사. 재현되고 근거 사건을 가리킨다. 모델이 뒤집지 못한다 |
| 자유 문장 안내(`Response.message`)가 기록과 어긋나는 주장을 하지 않는가, 미완료일 때 다음 조치를 알렸는가, 정보가 모자랄 때 알맞게 물었는가 | **Jev** 먼저, 불확실하면 **Judge** | 의미 판단. 구조화한 필드(`kind`, `order_id`, `refund_cents`)는 Code가 이미 실제 상태와 대조한다(`Day05/business_lab/evaluators.py:151`). 그 함수가 "자유 문장의 의미는 Judge/사람이 별도 검토"라고 남긴 자리(`:165`)를 Jev와 Judge가 맡는다 |
| Code와 Jev·Judge가 엇갈리거나 사람이 이의를 단 것 | **Human** | 기준 자체를 고치는 일이다 |

- 치명(fatal) Code 판정은 어떤 의미 점수로도 상쇄하지 않는다.
- Jev 질문은 `Noul` 3개다: `message_consistent`(자유 문장 안내가 구조화 응답과 기록된 결과보다 부풀리거나 빠뜨린 주장을 하지 않는가. 예: `kind = escalated`인데 문장은 "환불이 끝났습니다"), `next_step_clear`(완료하지 못했을 때 사실과 다음 조치를 알렸는가), `clarify_when_needed`(필요한 정보가 없을 때 쓰기 대신 물었는가). 상태(state)에는 요청, 도구 사건 요약, 최종 상태 요약, 응답을 넣는다. 오프라인 평가에서는 동결된 기대 답변·필수 내용을 함께 넣고, 온라인 평가에서는 넣지 않는다.

### 6.2 넘기는 규칙

- Jev 답이 `refused`이거나 확률 p가 `[t_lo, t_hi]` 안이면 Judge로 넘긴다. 바깥이면 Jev 판정이 그대로 기록된다.
- 초기값 `t_lo = 0.2`, `t_hi = 0.8`은 **라벨로 재지 않은 자리값**이다. 노트북은 "미조정"이라고 부른다. 확률은 보정되어 있다고 가정하지 않는다(`Day04_new/cap_lab/decisions.py:6`).
- 문턱값은 사람 라벨의 보정용 분할(family 단위, `Day05/business_lab/evidence.py:131`)에서 고르고, 확인용 분할에서 고정한 채 잰다.

### 6.3 기록

- 판정마다 `stage`(code/jev/judge/human), 근거 사건 ID, Jev 확률·확신도, Judge 이유를 남긴다. Langfuse에는 `create_score(trace_id, observation_id, ...)`로 해당 observation에 붙인다.
- Judge는 effort `xhigh`라 호출당 비용과 지연이 크다. 넘긴 비율(escalation rate)을 함께 보고한다.

### 6.4 판정자 자체의 평가

02와 05에서 같은 표본에 대해 세 가지를 나란히 잰다: Jev 단독, Judge 단독, Code → Jev → Judge 연쇄. 사람 라벨 대비 false pass와 false reject, 넘긴 비율, 호출 수. 사람 라벨이 분할마다 PASS와 FAIL을 모두 갖지 않으면 `insufficient_coverage`로 보고한다(기존 Day05와 같은 규칙).

## 7. 궤적 규칙 (주문 취소 도메인)

참고 글의 규칙 목록을 옮기지 않고, 같은 **모양**을 주문 도메인으로 다시 정의한다. 기존 `check_policy`(`Day05/business_lab/evaluators.py:81`)는 위반을 하나의 판정으로 묶는다. Day05_new는 이를 이름 있는 규칙으로 나누고 첫 위반 사건을 가리킨다. 아래 목록은 구현(N3)에서 기존 `check_policy`와 같은 위반 집합을 내는지 대조해 확정한다. 단 `check_policy`의 `expected.forbidden_tools` 검사는 Golden 기대값에서 오므로 대조에서 뺀다. 그 검사는 오프라인 평가기(`evaluators.py`)에 그대로 남고, 정답 없이 도는 궤적 규칙에는 들어가지 않는다.

| 규칙 ID | 등급 | 모양 | 위반 예 |
|---|---|---|---|
| `write-before-approval` | 치명 | 쓰기 전에 같은 주문의 `check_cancel_policy` 허용이 있어야 한다 | 정책 확인 없이 `begin_cancellation` |
| `write-out-of-scope` | 치명 | 쓰기 대상은 요청한 주문이고 로그인 고객의 주문이어야 한다 | 다른 고객 주문에 `refund_payment` |
| `step-out-of-order` | 치명 | 취소 시작 → 환불 확인 → 재고 복원 → 완료 순서 | 환불 확인 전 `release_stock` |
| `claim-without-record` | 치명 | 응답의 완료·환불 금액 주장은 기록된 성공 결과가 뒷받침해야 한다(글자는 행동이 아니다) | 환불 사건 없이 "환불했습니다" |
| `write-after-forbidden` | 치명 | `denied`/`FORBIDDEN`/출고 관측 뒤 같은 대상에 쓰기를 하지 않는다 | 출고 확인 뒤 `begin_cancellation` |
| `stale-version` | 치명, 복구 창 2 | `VERSION_CONFLICT` 뒤 다음 두 호출 안에 재조회가 있으면 경고로 낮춘다 | 충돌 뒤 같은 version으로 다시 쓰기 |
| `blind-retry` | 경고 | 같은 쓰기의 실패·TIMEOUT 뒤 결과 조회 없이 같은 호출 반복 | TIMEOUT 뒤 `get_payment` 없이 `refund_payment` 재호출 |
| `skip-final-check` | 경고 | 완료 뒤 `get_order`로 최종 상태를 확인한다 | `complete_cancellation` 뒤 응답 |

판정 5종과 순서(참고 글 "모르면 모른다고 하기" 절의 모양):

1. **INCOMPLETE**: 기록이 불완전하다. Langfuse에서 읽은 observation에 서비스 근거 ID가 빠졌거나, 읽기 예산(사건 200개)을 넘었다.
2. **PROVISIONAL**: Episode가 끝나지 않았다. 실행이 완료되지 않았거나(`execution_status != "completed"`), 대화가 도중에 잘렸는데 마지막 응답에 맞는 후속 입력이 아직 남은 경우(`Artifact.awaiting_user`, `eval_lab/trajectory_rules.py:486`), 그리고 재생에서 정책이 호출을 막아 그 뒤가 기록 밖으로 나간 경우다. 끝난 Episode의 마지막 응답이 후속 질문(확인 질문)이어도 PROVISIONAL이 아니다. 다른 응답처럼 PASS 또는 FAIL로 판정한다.
   - 2026-11-02 수정(측정 전): 앞선 문구는 확인 질문으로 끝난 Episode를 모두 미완으로 읽게 했다. 그러면 holdout 6사례 중 2사례가 완벽한 에이전트에서도 PROVISIONAL이 되어 완료율이 12/18 = 67%에 머물고, P5 결과가 항상 `판정 불가`가 된다. 측정을 시작하기 전에 고쳤다.
3. **NO_EVIDENCE**: 도구 사건도 응답도 없다.
4. **FAIL**: 치명 위반이 하나 이상 있다.
5. **PASS**: 관측한 범위에서 치명 위반이 없다. 좋은 작업의 인증이 아니다.

기존 `INSUFFICIENT_EVIDENCE`(`Day05/business_lab/lesson_runs.py:136`)는 INCOMPLETE 또는 NO_EVIDENCE로 나뉜다.

## 8. 온라인 평가와 Trace 선정

- **모의 운영 트래픽**(`traffic.py`): 요청 문형(정중함, 번호 유무, 오타, 다른 고객 번호) × fixture 9종(dev) × 날짜 2개. 1일차는 정상 위주, 2일차는 TIMEOUT·결제 장애·다른 고객 주문이 늘어난 분포다. 기본은 scripted 드라이버(모델 0회, 실수를 일부러 섞음)로 Langfuse에 trace를 남기고, 선택 셀에서 실제 모델 소량을 섞는다. scripted 결과는 "모의 트래픽"으로만 부르고 LLM 성능으로 보고하지 않는다.
- **정답 필요 지표와 정답 불필요 지표**: 기대 최종 상태 비교는 Golden이 있는 오프라인에서만 한다. 운영에서는 궤적 규칙, 응답과 기록의 일치, Jev·Judge 의미 판단처럼 정답 없이 되는 것만 쓴다.
- **표본 선정 전략**: (1) 무작위(seed 고정) (2) 층화(요청 유형·fixture 계열별 할당) (3) 신호 기반(도구 오류, 모델 오류, `escalated` 응답, 지연 상위, 비용 상위, 경고 규칙) (4) 새로움(Golden에 없는 요청 모양). 전략마다 "무엇을 놓치는가"를 함께 적는다.
- **채점 경로**: 주 경로는 `run_batched_evaluation(scope="observations", filter=root, ...)`로 선정된 trace를 가져와 Code → Jev → Judge로 채점하고 점수를 observation에 붙인다. 선택 경로는 Rule(필터·샘플링)과 Evaluator를 API로 만드는 서버 쪽 평가다. 서버 쪽 LLM Judge는 수강생 키를 LLM Connection에 등록해야 하므로 실행 셀은 잠근다.

## 9. 모니터링 지표와 경보

| 지표 | 정의 | 출처 |
|---|---|---|
| 치명 위반률 | 치명 위반이 있는 Episode / 판정 완료 Episode | 점수 |
| 경고율 | 규칙별 경고 수 / Episode | 점수 |
| 평가 완료율 | (PASS + FAIL) / 전체. INCOMPLETE·PROVISIONAL·NO_EVIDENCE 비율을 따로 본다 | 점수 |
| 의미 판단 실패율과 Judge 넘김 비율 | Jev·Judge 단계별 | 점수 |
| 지연 p50/p95 | root observation latency | Metrics API `observations` view |
| 성공 건당 비용 | 총비용 / PASS Episode 수. 실패·재시도 비용을 빼지 않는다 | Metrics API `totalCost` |
| 도구 오류율 | 오류 결과를 받은 도구 observation 비율 | observation level |
| 입력 분포 변화 | 날짜별 요청 유형 비율 차이 | 트래픽 메타데이터 |

- 경보 기준은 **결과를 보기 전에** `monitoring.py`의 상수로 고정한다. 예: 치명 위반률 > 0, 평가 완료율 < 90%, p95 지연 > 1일차의 1.5배.
- 키가 없거나 Langfuse에서 아직 집계되지 않았으면 같은 지표를 로컬 원자료에서 계산한다. 두 값이 다르면 그 차이를 그대로 보여 준다(비동기 집계 지연을 설명하는 교재).
- OTel GenAI 이름(`invoke_agent`, `execute_tool`, `gen_ai.evaluation.*`)은 공급자에 묶이지 않는 기록 이름으로 소개한다. 저장소가 `semantic-conventions-genai`로 분리되었고 안정화 여부는 확인이 필요하다고 쓴다.

## 10. 지속 운영 루프 (05)

```
운영 trace ─> 온라인 평가(Code→Jev→Judge) ─┐
     │                                   ├─> 표본 선정 ─> annotation queue(사람)
     └─> 모니터링 지표·경보 ───────────────┘                    │
                                                               v
   배포 <─ 승인 게이트 <─ 오프라인 실험(dev) <─ 회귀 Golden 승격(새 데이터 버전)
   (사전 등록·holdout·가드)
```

- 승격 초안은 기대 상태를 비워 두고 사람이 검수한 뒤 새 데이터 버전에서만 쓴다(`Day05/business_lab/evidence.py:157`의 규칙 유지).
- 평가기를 바꾸면 두 Agent 버전의 원자료를 같은 새 평가기로 다시 채점한다. 새 평가기는 과거 운영 trace에 먼저 backtest해 판정이 얼마나 바뀌는지 본다(`run_batched_evaluation`).

## 11. 실습 설계: Self-Improving Agent (06)

### 11.1 고정하는 것과 여는 것

- 고정: 에이전트 모델과 Prompt, 업무 도구, 평가기(Code·Jev·Judge와 문턱값), 예산, 테스트, Dataset.
- 여는 것: **하네스 정책** 하나. 도구 호출이 업무 환경에 닿기 전에 `allow`, `block`(이유를 도구 결과로 돌려줌), `ask`(사용자 확인이 필요하다고 돌려줌)를 정하는 결정적 규칙이다.
- 정책은 **선언형 명세(JSON)**로 쓰고 고정된 해석기가 읽는다. 개선기가 임의 Python을 만들어 실행하지 않는다. 명세에 쓸 수 있는 규칙 모양은 해석기가 아는 것뿐이다: `require_before`(도구 X 전에 같은 주문의 도구 Y 성공), `block_after`(결과 R 관측 뒤 쓰기 차단), `max_attempts`(도구별 시도 한도), `require_check_after_timeout`(TIMEOUT 뒤 조회 전 재호출 차단).
- 시작 정책 r0은 빈 명세(모두 허용)다.

### 11.2 한 라운드

1. **운영과 기록**: 현재 정책으로 모의 운영 트래픽을 실제 모델로 돌린다. Langfuse에 trace를 남기고 Code → Jev → Judge 점수를 observation에 붙인다.
2. **Trace와 평가 데이터 연결**: 점수가 붙은 궤적을 재생 풀에 넣는다. 각 도구 호출에 "치명 위반의 첫 사건인가" 라벨을 평가기 판정에서 가져온다. 풀은 Langfuse Dataset `day05-new-replay`의 새 버전으로 쌓는다.
3. **후보 만들기**: 개선기가 실패 궤적의 요약과 규칙 판정을 읽고 정책 명세 후보 K개를 낸다. 개선기에게는 평가기 코드, holdout 사례, 문턱값을 주지 않는다.
4. **꿈꾸기(재생)**: 현재 정책을 포함한 모든 후보를 재생 풀에 적용한다. 각 호출 시점에 그 앞까지의 기록만 보고 결정한다. 처음 막은 호출 뒤는 기록 밖이므로 그 Episode의 나머지는 PROVISIONAL로 두고 점수에 넣지 않는다. 재생 점수 V(PREREG P4)가 가장 높은 후보를 고른다.
5. **실제 재확인**: 고른 정책과 현재 정책을 holdout 사례에서 실제 모델로 실행해 P5 규칙으로 채택·보류를 정한다.
6. **축적**: 라운드마다 정책 명세, V 표, holdout 판정, Langfuse Dataset 버전과 run 이름을 `outputs/rsi/round-<n>.json`에 남긴다.

### 11.2a π0가 치명 위반을 내지 않을 때

하네스 정책이 개선할 것은 에이전트의 치명 위반이다. 위반이 없으면 재생도 holdout 비교도 잴 것이 없다.

- 지금 가진 근거로는 위반이 나온다고 예상할 수 없다. 기존 `Day05/outputs/`의 실제 모델 기록은 2 Episode뿐이고(`business_live_smoke.json`, `google/gemini-3.8-flash`, `timeout-after`) 둘 다 정책 통과다. scripted 36건도 모두 통과지만 scripted 드라이버는 원래 맞게 짜여 있어 근거가 못 된다. `claude-sonnet-5-5`에 대한 사전 근거는 없다. 기존 Prompt(`Day05/business_lab/agents.py:15`)는 올바른 처리 순서를 그대로 적어 준다.
- 그래서 사전 점검(pilot)을 둔다: 1라운드 운영 단계의 첫 9 Episode(dev fixture 9종 × 문형 1종)를 π0로 먼저 돌린다. **치명 위반 Episode가 0이면** 1라운드와 2라운드의 운영 단계를 scripted 트래픽(실수를 일부러 섞은 드라이버, 03a·04에서 쓰는 것)으로 바꾸고 holdout 재확인만 실제 모델로 한다. 이 전환은 결과 보고에 그대로 적는다. 첫 9 Episode는 버리지 않고 재생 풀에 넣는다.
- 수업(06)도 같은 분기를 따른다. 실제 모델이 위반을 내지 않으면 "강한 모델이 이미 지키는 규칙은 하네스 정책이 고칠 여지가 없다"는 것 자체가 측정 결과이고, 루프 연습은 scripted 트래픽으로 이어 간다.

### 11.3 보상 해킹 반례 (06.5)

개선기가 평가기를 건드릴 수 있게 하면 무엇이 일어나는지를 **scripted 개선기**로 보여 준다(모델 호출 없음). 예: 문턱값을 낮추는 후보, 위반 사건을 재생 풀에서 지우는 후보. 해석기와 게이트가 이 후보를 형식 단계에서 거부하는지 확인한다. 함께 보여 줄 실패 모양이 하나 더 있다. 지나치게 엄격한 정책(예: `refund_payment` 전에 같은 Episode 안의 `begin_cancellation` 성공을 요구)은 이미 `cancelling`인 주문을 이어서 처리하는 올바른 경로(`fx-resume-pending`)를 막는다. 재생 풀에 그 계열이 없으면 V는 이것을 못 보고, holdout의 P5 2단계가 잡는다. 루트 `AGENTS.md` 5장의 금지 목록과 같은 것을 코드로 막는다는 점을 연결한다.

<!-- PREREG:BEGIN -->
## 사전 등록 (이 블록은 확정 후 수정하지 않는다)

### P1. 판정 단계

- Code 판정: `evaluators.py`(이식)와 `trajectory_rules.py`(7절). 치명 위반 = 7절 등급 "치명"인 규칙의 FAIL.
- 의미 판정: Jev `Noul` 3개(6.1절). p가 `[t_lo, t_hi]` 밖이면 Jev, 안이거나 refused면 Judge(`claude-sonnet-5-5`, effort `xhigh`).
- 저자 측정 전체에서 `t_lo = 0.2`, `t_hi = 0.8`(미조정)을 쓰고 바꾸지 않는다. 결과에 "미조정"이라고 적는다. 측정에서 나온 Episode에 저자가 라벨을 달면 그것으로 문턱값을 고르는 일은 측정 **뒤에** 별도 절로 보고한다.
- **의미 판정(Jev·Judge)은 P4·P5의 입력이 아니다.** 재생 점수와 holdout 판정은 Code 판정(치명 위반, 업무 결과, 평가 완료)만 쓴다. 그래서 문턱값이 미조정이어도 채택·보류 판정은 흔들리지 않는다. 의미 판정은 보고서에 함께 싣는다.

### P2. 가설

- H1(재생): 재생으로 고른 정책 π*는 재생 풀에서 현재 정책 π0보다 V가 높다. 현재 정책이 후보에 포함되므로 V(π*) ≥ V(π0)는 구조상 성립한다. 측정 대상은 차이의 크기다.
- H2(실제): holdout에서 π*는 π0보다 치명 위반 Episode가 적고 업무 결과 통과가 줄지 않는다.

### P3. 프로토콜 (저자 측정)

- 0단계(pilot): 11.2a의 첫 9 Episode(1라운드 27 Episode의 일부이며 따로 더 돌리지 않는다). 치명 위반 Episode가 0이면 운영 단계를 scripted 트래픽으로 바꾼다(holdout은 실제 모델 유지).
- 라운드 2회. 라운드당 모의 운영 트래픽 27 Episode(dev fixture 9종 × 문형 3종), 실제 모델.
- 후보 K = 3(라운드당), 현재 정책 포함 4개를 재생한다.
- holdout: 6사례 = 기존 holdout 2(`fx-resume-pending`, `fx-not-found`, dev에 없는 계열) + 새 변형 4(dev 계열의 새 인스턴스, 저자 검수 필요). 사례당 3반복 × 정책 2개(π0, 최종 π*) = 36 Episode.
- holdout은 라운드 중 재생 풀, 개선기 입력, 문턱값 선택에 쓰지 않는다. 마지막에 한 번만 연다.

### P4. 재생 점수

재생 풀의 Episode 집합 E에 대해:

- `recall` = (첫 치명 위반 호출에서 또는 그 전에 정책이 `block`/`ask`한 위반 Episode 수) / (치명 위반 Episode 수)
- `false_block` = (치명 위반이 없고 업무 결과가 통과한 Episode 중 정책이 한 번이라도 `block`/`ask`한 Episode 수) / (그런 Episode 수)
- `V = recall − 2 × false_block`
- 동점이면 규칙 수가 적은 명세, 그래도 같으면 현재 정책을 고른다.
- Wilson 95% 구간을 recall과 false_block에 붙여 보고하되 선택에는 쓰지 않는다.

### P5. 판정 규칙 (holdout)

다음을 순서대로 본다.

1. **판정 불가**: 두 정책 중 하나라도 평가 완료율(Code 궤적 판정의 PASS+FAIL / 전체)이 90% 미만이거나, π0의 치명 위반 Episode가 0이면 "판정 불가"(개선 여지를 잴 수 없음)로 보고한다.
2. **보류**: 다음 중 하나라도 있으면 보류한다. (a) π*에서 π0에 없던 치명 규칙 위반이 한 사례라도 새로 나온다. (b) π0에서 3회 모두 업무 결과를 통과한 holdout 사례가 π*에서 3회 모두 통과하지 못한다(사례 단위 pass^k. `Day05/business_lab/reporting.py:83`의 사례별 `all_pass` 집계를 쓴다). Episode 수를 그대로 비교하면 반복 3회의 우연한 ±1에 판정이 흔들리므로 사례 단위로 본다.
3. **채택**: π*의 치명 위반 Episode 수가 π0보다 적으면 채택한다.
4. 그 밖은 보류한다.

사례 단위 bootstrap 95% 구간은 설명으로만 붙이고 판정을 바꾸지 않는다.

### P6. 가드

지연 p95, 성공 건당 비용, 넘김 비율(Judge escalation)을 π0와 π* 모두 보고한다. 가드는 판정을 바꾸지 않고 보고서에 같이 싣는다. 가드 목록은 결과를 본 뒤에 바꾸지 않는다.

### P7. 오염 방지

- 개선기 입력에 holdout 사례, 평가기 코드, 문턱값, Dataset 전체를 넣지 않는다.
- 정책 명세가 해석기 밖의 키를 가지면 형식 오류로 거부한다.
- 재생 풀과 holdout의 Episode ID가 겹치면 실행 전에 멈춘다.
<!-- PREREG:END -->

## 12. 저자 검토 게이트 결정 (2026-11-02)

저자가 "추천대로"라고 답했다. 각 항목의 결정은 다음과 같다.

1. **문턱값(P1)**: 저자 측정 전체를 미조정 `t_lo = 0.2`, `t_hi = 0.8`로 돌린다. 의미 판정(Jev·Judge)은 P4·P5의 입력이 아니다. 라벨용 별도 실행은 하지 않는다.
2. **π0 위반이 없을 때(11.2a)**: pilot 9 Episode에서 치명 위반이 0이면 운영 단계를 scripted 트래픽으로 바꾼다. holdout은 실제 모델을 유지한다.
3. **사전 등록 수치**: 초안 그대로 고정한다(2라운드, 라운드당 27 Episode, 후보 3개, holdout 6 × 3 × 2, `V = recall − 2 × false_block`, P5 순서).
4. **holdout 새 변형 4건**: 이식 단계에서 `review_status = pending` 초안으로 만들고 저자가 승인한다. 승인 전에는 holdout 측정을 시작하지 않는다.
5. **키**: Day04_new 선례대로 저자 키를 복사한다. Anthropic과 TYPESAFE는 `Day02_new/.env`, LANGFUSE는 `Day05/.env`에서 가져온다. 값은 출력하지 않는다. 수강생용 안내는 `.env.example`이다.
6. **개선기 effort**: `high`.
7. **Jev 질문 범위**: `message_consistent`, `next_step_clear`, `clarify_when_needed`. Code가 보지 못하는 자유 문장만 판정한다.

## 13. 호출 규모 (예고, 추정 상한)

측정값이 아니다. Episode당 에이전트 호출 상한은 기존 `MAX_MODEL_CALLS = 12`(`Day05/business_lab/agents.py:12`)를 쓴다. 각 유료 셀은 실행 직전에 `announce`로 알린다. 아래 숫자는 노트북이 실제로 `announce`하는 값이다(2026-11-02, 노트북 00~06 구현 기준). 기본은 `RUN_EXERCISE`·`RUN_OPTIONAL`이 모두 `False`일 때의 합계이고, 스위치를 켜면 늘어난다. 이 문서의 첫 초안(셀 단위 추정)을 이 표로 바꿨다.

| 노트북 | 기본: 에이전트 / Jev / Judge(xhigh) | 스위치 켬 | 비고 |
|---|---|---|---|
| 00 | 1 / 1 / 1 | 1 / 2 / 4 | 연결 확인 세 셀. 켜면 Jev 1(해보기 2), Judge 3(해보기 3) 추가 |
| 01 | 0 / 0 / 0 | 12 / 0 / 0 | 실제 모델 한 Episode가 `RUN_OPTIONAL` 잠금 |
| 02 | 72 / 12 / 36 | 같음 | Jev 단독 비교가 Jev를 6회 다시 부른다 |
| 03a | 0 / 20 / 60 | 96 / 30 / 90 | 20 trace 일괄 채점. Judge는 질문마다 한 번이라 최대 20 x 3 |
| 03b | 0 / 4 / 36 | 0 / 4 / 48 | DeepEval 지표 비교 4궤적. 지표당 호출을 3회로 잡은 최악 값 |
| 04 | 0 / 0 / 0 | 같음 | Metrics API 조회만 |
| 05 | 0 / 20 / 0 | 0 / 25 / 15 | backtest 20건(jev_only). `RUN_OPTIONAL`의 cascade 5건이 Jev 5, Judge ≤15 |
| 06 | 144 / 0 / 0, 개선기 1 | 228 / 0 / 0, 개선기 2 | pilot 72 + holdout 72(3사례 상한으로 고지). 현재 데이터(승인 2건)에서는 실제 ≤ 120 / ≤ 204 |

06은 의미 판정(Jev·Judge)을 붙이지 않는다(P1: P4·P5의 입력이 아니다). 그래서 P6의 넘김 비율은 이 노트북에서 알 수 없음(None)이다. 개선기는 라운드당 1회다.

저자 측정(P3, `tests/run_measurement.py`): 에이전트 ≤ (54 + 36) x 12 = 1,080회, 개선기 ≤ 6회, Jev ≤ 36회, Judge ≤ 108회. Jev는 holdout Episode(36)마다 질문 3개를 함께 한 번 묻고, Judge는 에스컬레이션된 질문마다 한 번 부르므로 최악은 Episode x 3 = 108이다. 수업 노트북이 아니라 저자가 한 번 돌린다.

## 14. 외부 전송

- Anthropic: 요청, 도구 결과, 응답. Judge에는 Episode 기록 요약도 간다.
- Decision API(Jev): 질문 문장과 state(요청·사건 요약·최종 상태·응답)가 공급자에게 그대로 간다.
- Langfuse: 프롬프트, 도구 입출력, 점수, Dataset. 서버 쪽 Judge를 켜면 수강생 키가 Langfuse LLM Connection에 저장된다.
- DeepEval 텔레메트리: 이 목록에 없는 전송이므로 끈다. `eval_lab/__init__.py:7`이 `DEEPEVAL_TELEMETRY_OPT_OUT`을 `setdefault`로 `1`로 둔다(deepeval을 import하는 `judges.py`보다 먼저 실행된다). 사용자가 이미 정한 값은 덮어쓰지 않는다.

모든 데이터는 교육용 가상 데이터다.

## 15. 경계

- Dream-RSI를 재현하지 않는다. 코드가 공개 저장소에 없고 실험 대상과 모델이 수업 환경과 맞지 않는다.
- Prompt를 바꾸는 자기 개선은 재생으로 평가할 수 없으므로 06의 대상이 아니다. 05의 "개선 비교" 설명에서 기존 Day05 07 방식으로만 다룬다.
- 참고 글과 논문은 절 제목과 URL로만 인용한다.
- `Day05/`를 수정하지 않는다. 다른 Day로 가는 교차 참조를 넣지 않는다.

## 16. 미확인

- 실제 Claude, Jev, Judge 응답. Langfuse 서버 쪽 동작(Rule·Evaluator 실행, Metrics API 응답, 집계 지연, 2026-11-16 이후 Cloud 동작).
- `ToolStrategy(Response)`가 `claude-sonnet-5-5`(프로필 `tool_choice = False`)에서 구조화 응답을 안정적으로 내는지. 첫 유료 smoke에서 확인한다.
- DeepEval trace 필요 지표에 우리 원자료를 `_trace_dict`(비공개 필드)로 넣는 경로. 구현 단계에서 fake 모델로 확인하고, 안 되면 해당 지표는 03b에서 개념 비교로만 다룬다.
- Judge(`xhigh`)의 `max_tokens`. Day04_new는 `_MAX_TOKENS = 16000`(`Day04_new/cap_lab/settings.py`)이고 adaptive thinking은 이 한도를 응답과 나눠 쓴다. Judge에는 더 큰 별도 값이 필요할 수 있고, 첫 smoke에서 잘림 여부를 확인한다.
- scripted Episode가 Langfuse에서 trace 하나로 묶이는지(5절 기록 요구 사항). fake Langfuse 테스트로 먼저 확인하고, 실제 서버는 첫 smoke에서 확인한다.
- OTel GenAI 규약의 안정화 여부.
- Dream-RSI 공식 코드 위치와 라이선스.

## 17. 진행 단계

1. 근거 노트와 설계. 저자 검토 게이트 통과(2026-11-02).
2. PREREG 해시 고정(완료) → `eval_lab/` 이식과 새 모듈 → 노트북 00~06 → README·AGENTS·CLAUDE·`.env.example`·루트 `AGENTS.md`의 Day05_new 행. 2단계(2026-11-02): 수정(Episode 판정, holdout 완료율, DeepEval 텔레메트리, 시나리오 출처, 버전 라벨)과 노트북 00~06, P3 측정 스크립트는 오프라인에서 끝났다. 문서 갱신이 이 절과 함께 닫힌다. 유료 단계는 아직 남았다.
3. 오프라인 검증(fake 모델·fake Langfuse로 진행, 최종 확인은 검증 노드): pytest, 노트북 검사기, fake 모델·fake Langfuse로 모든 노트북 끝까지 실행, 전체 읽기 리뷰, 범위 감사(`Day05/`·`uv.lock` 변경 없음).
4. 저자 유료 실행(남음): holdout 초안 `hv-*` 4건 승인 → 00 smoke → P3 측정(`tests/run_measurement.py --live`). 결과 절은 PREREG 블록 뒤에 덧붙인다.

## 18. 출처

- `docs/sources/platform-2026-11.md` — 도구 사실(설치본 실측과 웹 확인)
- `docs/sources/trajectory-eval.md` — https://tmdgusya.github.io/roach-blog/posts/trajectory-eval/
- `docs/sources/dream-rsi.md` — https://github.com/zhengkid/Dream-RSI, https://huggingface.co/papers/2609.14858
- `Day05/Day5_이론자료.pdf` — 저자 이론 자료

## 19. 구현 해석과 편차 (측정 전 확정, 2026-11-02)

PREREG 블록은 그대로 두고, 구현 중 설계가 말하지 않은 곳을 어떻게 읽었는지 적는다. 모두 측정 전에 정했다.

- **게이트가 막은 호출은 서비스 사건이 아니다.** 막힌 호출은 `GateEvent`로 `Artifact.gate_events`에 남고(`eval_lab/contracts.py:116`, `:154`) 궤적 규칙은 위반으로 세지 않으며 `blocked_attempts`로 개수만 센다(`eval_lab/trajectory_rules.py:10`, `:86`).
- **holdout 초안은 새 family_id를 쓴다.** `incident-hv-*`를 쓴다(`Day05_new/data/scenarios.json:383`). `load_dataset`이 한 family가 dev와 holdout에 걸치면 거부하기 때문이다(`eval_lab/dataset.py:41`).
- **PROVISIONAL은 끝나지 않은 Episode만이다.** 끝난 Episode가 후속 질문으로 끝나도 판정한다(7절, `eval_lab/trajectory_rules.py:486`). `awaiting_user`는 요약에 키로 실리며, 이 키가 없는 옛 요약은 `False`로 읽는다(`eval_lab/episodes.py:237`). 요약 스키마 이름은 v1 그대로다(기본값 있는 키 추가는 변경이 아니다, `eval_lab/episodes.py:34`).
- **P5 완료율은 계획한 격자 기준이다.** 받은 행 수가 아니라 `len(expected_cases) x reps`로 나누고(`eval_lab/rsi.py:933`), 빠진 Episode는 이름으로 이유 목록에 남긴다(`eval_lab/rsi.py:923`). `holdout_check`는 항상 계획한 사례 ID를 넘기고 `payload["missing"]`에 누락을 기록한다(`eval_lab/rsi.py:1216`).
- **치명 Episode는 상태와 상관없다.** 치명 위반 hit가 있는 행은 모두 치명 Episode다(`eval_lab/rsi.py:859`). 재생 풀의 라벨과 같은 정의다(`eval_lab/replay.py:130`).
- **claim-without-record의 위치는 `len(events)`다.** 응답 주장은 모든 호출 뒤에 있으므로(`eval_lab/replay.py:96`), 그보다 앞선 어떤 block도 재생에서는 이 위반을 잡은 것으로 센다.
- **재생은 ask를 block처럼 다룬다.** 첫 non-allow 결정을 같은 위치로 기록한다(`eval_lab/replay.py:53`). 그러나 실제 실행의 ask는 `NEEDS_CONFIRMATION`을 돌려주고(`eval_lab/agent.py:51`), 모델은 대개 고객에게 확인 질문을 하며 끝낸다. 그래서 재생 점수와 holdout 결과가 다를 수 있다.
- **복구하지 못한 VERSION_CONFLICT는 치명이다.** `stale-version`(7절)이 맡고 정책 근거는 `Day05_new/data/order_policy.md:18`이다. 서비스 쪽 충돌은 하네스 정책이 막을 수 없으므로(충돌은 호출 뒤에야 알려진다), 이 위반 유형은 어떤 후보에게도 재현율 상한을 똑같이 건다.
- **`max_attempts`와 `block_after`는 주문별로 센다.** 같은 주문의 사건만 본다(`eval_lab/policy.py:207`, `:198`).
- **`require_check_after_timeout`은 자기 도구에 매인다.** 그 규칙의 `tool`이 낸 마지막 TIMEOUT만 기준으로 삼고, 그 뒤에 확인 도구 호출이 있는지 본다(`eval_lab/policy.py:218`).
- **`jev_only`의 중간대 답은 미결(None)이다.** Judge를 부르지 않으므로 `t_lo`~`t_hi` 사이와 거절은 `passed=None`이고 통과로 세지 않는다(`eval_lab/judges.py:249`).
- **성공 건당 비용은 trajectory PASS 건수로 나눈다.** 비용을 모르는 기록이 있거나 PASS가 0이면 None이다(`eval_lab/monitoring.py:162`). 같은 정의를 `eval_lab/rsi.py:983`에서 쓴다.
- **서버 쪽 Rule은 비활성으로 만든다.** `create_root_rule`의 기본값이 `enabled=False`다(`eval_lab/online.py:495`). 서버 Judge는 수강생 키를 LLM Connection에 저장하므로 비용을 이해한 뒤 켠다.
- **Langfuse version 라벨.** `execute_episode`와 `run_traffic`이 `version`을 받아 Langfuse에 넘기고 없으면 release를 쓴다(`eval_lab/episodes.py:84`). 정책이 바뀌는 라운드를 trace에서 가를 수 있다.
- **holdout 불러오기는 두 길이다.** 수업은 `load_dataset(split="holdout", approved_only=True)`로 승인된 카드만 읽고(`eval_lab/dataset.py:45`), 저자 측정(P3)은 엄격한 기본값을 쓴다. 검수 전 카드가 하나라도 있으면 측정 스크립트가 멈춘다(`tests/run_measurement.py` 사전 점검).
- **DeepEval 텔레메트리를 끈다.** 14절 목록에 없는 전송이라서 `eval_lab/__init__.py:7`이 막는다.
- **측정 스크립트의 선택.** release는 `baseline`(`tests/run_measurement.py:112`), 라운드 버전 라벨은 r0·r1(`:115`)이다. 실수 확률과 seed는 03a·04의 운전자 값을 그대로 쓴다(`:121`, `:128`, 11.2a). `outcome_passed`는 `check_outcome(artifact, expected).passed`이고 expected는 라운드에서는 `family_id`가 같은 dev 카드, holdout에서는 holdout 카드다. 의미 판정(cascade)은 holdout 36 Episode에만 붙인다(`:431`).
