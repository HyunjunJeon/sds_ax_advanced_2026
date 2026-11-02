# Day05_new — Agent 평가 및 모니터링

주문 취소·결제 환불·예약 재고 복원 업무를 하는 Agent를 하나 두고, 그 Agent를 **어떻게 평가하고, 운영 중에 어떻게 지켜보고, 그 기록으로 어떻게 개선하는가**를 노트북 00~06으로 배웁니다. 모델은 `ChatAnthropic`(`claude-sonnet-5-5`)이고, 평가는 Code → Jev → Judge 순서로 진행합니다(Judge는 effort `xhigh`).

채점은 없습니다. 모든 코드가 제공되고, 각 노트북 끝의 **직접 해보기**와 **확인 질문**으로 자기 말로 설명할 수 있는지 확인합니다.

## 노트북 순서와 시간 (총 390분)

| 노트북 | 분 | 핵심 질문 |
|---|---|---|
| `00-Setup.ipynb` | 10 | 키·연결·버전이 준비되었는가 |
| `01-Why-Evaluate.ipynb` | 40 | 그럴듯한 답이 왜 업무 성공의 증거가 못 되는가 |
| `02-Offline-Golden-Dataset.ipynb` | 60 | 무엇을 성공으로 볼지 어떻게 고정하는가 |
| `03a-Online-Eval-Trace-Selection.ipynb` | 45 | 정답이 없는 운영 trace를 무엇으로, 어떤 것부터 채점하는가 |
| `03b-Trajectory-Eval.ipynb` | 55 | 궤적의 순서를 어떻게 판정하고, 평가기는 어떻게 믿는가 |
| `04-Agent-Monitoring.ipynb` | 45 | 평가와 무엇이 다르고, 무엇을 언제 경보하는가 |
| `05-Continuous-Operation.ipynb` | 45 | 평가와 모니터링을 어떻게 하나의 운영 루프로 묶는가 |
| `06-Lab-Self-Improving-Agent.ipynb` | 90 | 에이전트가 자기 trace로 스스로 나아지게 하려면 무엇을 고정하고 무엇을 열어야 하는가 |

번호 순서대로 진행합니다. 뒤 노트북은 앞 노트북의 개념과 `eval_lab` 함수를 이어서 씁니다.

## 준비

1. 저장소 루트에서 한 번 `uv sync --locked`를 실행합니다. 이 폴더에서는 `uv sync`를 하지 않습니다.
2. 이 폴더에서 `.env.example`을 `.env`로 복사하고 **본인의 키**를 채웁니다. `.env`는 커밋하지 않습니다.
3. `00-Setup.ipynb`를 실행하면 키가 **설정됨/미설정**으로만 표시됩니다(값은 출력하지 않습니다).

필요한 키(자세한 변수 목록과 기본값은 `.env.example`):

- 필수: `ANTHROPIC_API_KEY`
- Decision API(Jev)용 키 하나: `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` 중. `DAY05_DECISION_BACKEND`를 비워 두면 이 순서에서 값이 있는 첫 번째를 씁니다. Claude가 Jev를 대신하지는 않습니다.
- Langfuse(`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`): Langfuse 셀에만 필요합니다. 없으면 노트북은 로컬 경로로 계속 진행합니다.

두 스위치 `RUN_EXERCISE`, `RUN_OPTIONAL`은 노트북 안에서 기본 `False`입니다. 직접 해보기와 선택 실습 중 호출이 더 드는 셀이 이 스위치 뒤에 있습니다.

## 비용

유료 셀(Claude 에이전트, Jev, Judge, 개선기)은 실행 직전에 `announce`로 호출 규모를 한 줄로 알립니다. 아래는 노트북이 예고하는 **상한 추정**이며 측정값이 아닙니다. 본인 크레딧이 쓰입니다.

| 노트북 | 기본 실행 | 스위치를 켠 실행 |
|---|---|---|
| 00 | Claude 1, Jev 1, Judge 1 | Jev 2, Judge 4 |
| 01 | 호출 없음 | Claude 12 |
| 02 | Claude 72, Jev 12, Judge 36 | 같음 |
| 03a | Jev 20, Judge 60 | Claude 96, Jev 30, Judge 90 |
| 03b | Jev 4, Judge 36 | Jev 4, Judge 48 |
| 04 | 호출 없음 | 호출 없음 |
| 05 | 각 셀의 `announce` 줄을 확인 | 각 셀의 `announce` 줄을 확인 |
| 06 | Claude 144 이하, 개선기 1 | Claude 228 이하, 개선기 2 |

06의 holdout 구간은 사례 3개 상한으로 예고하므로 현재 승인된 카드 수에서는 실제가 더 적습니다. 합계는 노트북을 고치면 달라지므로, 최종 규모는 각 셀의 `announce` 출력을 따릅니다.

외부로 나가는 데이터: Anthropic에는 요청·도구 결과·응답과 Judge용 Episode 기록 요약, Decision API 공급자에는 질문 문장과 state, Langfuse에는 프롬프트·도구 입출력·점수·Dataset이 갑니다. 모든 데이터는 교육용 가상 데이터입니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `00`~`06` 노트북 | 수업 본문 |
| `eval_lab/` | 노트북이 import하는 실습 패키지(Episode 실행, Golden Dataset, Code·Jev·Judge 평가, 궤적 규칙, 모니터링, 정책·재생, RSI 등) |
| `data/` | 주문 정책 문서, 인터뷰, 시나리오와 fixture |
| `docs/` | 설계와 사전 등록(`DESIGN.md`), 근거 노트(`docs/sources/`) |
| `tests/` | 오프라인 테스트와 검사 스크립트(가짜 모델로 노트북 전체를 돌려 보는 `run_fake.py` 포함) |
| `outputs/` | 노트북이 실행할 때 만드는 결과(실행 시 생성, 커밋하지 않음) |

## 이 과정이 주장하지 않는 것

- **실제 모델 응답은 저자가 아직 측정하지 않았습니다.** 노트북은 가짜 모델로 끝까지 도는 것만 확인되었고, 실제 Claude·Jev·Judge 응답과 그 점수는 수업에서 처음 나옵니다.
- Langfuse 서버 쪽 동작(Rule·Evaluator 실행, Metrics API 응답, 집계 지연, 2026-11-16 전환 이후 Cloud 동작)은 확인되지 않았습니다.
- `ToolStrategy(Response)`가 `claude-sonnet-5-5`에서 구조화 응답을 안정적으로 내는지, Judge의 `max_tokens`가 충분한지는 첫 유료 실행에서 확인할 항목입니다.
- OTel GenAI 규약의 안정화 여부와 Dream-RSI 공식 코드의 위치·라이선스도 확인되지 않았습니다. Dream-RSI는 재현하지 않고 개념만 인용합니다.
- 작은 표본(수 건~수십 건)의 비율에는 통계적 의미가 없습니다.

노트북의 "미확인" 표시는 위 목록과 `docs/DESIGN.md` 16절을 따릅니다. 문서와 코드가 다르면 코드가 정답입니다.
