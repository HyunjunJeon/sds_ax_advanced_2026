# AGENTS.md — Day05 Agent Evaluation 수업

루트 `../AGENTS.md`의 규칙을 따른다. 현직 개발자 대상 실습이다.

- 주 흐름은 루트의 새 `00~09` 번호 파일이다. 항상 Day05에서 `uv run python <파일>`로 실행한다.
- 실행 조건은 `course_config.py`와 각 번호 파일 상단 상수다. 제공하지 않은 CLI 플래그를 만들지 않는다.
- 골든 데이터 초안·사람 검수·원자료·평가 결과는 서로 다르다. 검수자·판정·가설을 대신 지어내지 않는다.
- 작성 → 검수·동결 → 실행 → 근거 분석 → 평가 → 개선 비교의 결과물 연결을 유지한다.
- 수강생의 학습 성과는 근거를 자기 말로 설명하는 것이다. 평가 항목과 반례·가설을 먼저 확인한다.
- 모델에는 요청·가용한 대화와 업무 도구만 전달한다. 평가 정답·fixture 장애 설정은 전달하지 않는다.
- 실제 상태는 업무 환경에서 수집한다. Agent의 완료 주장을 실제 상태로 간주하지 않는다.
- 여러 턴은 같은 Episode 안에서 상태·대화를 유지하고, 새 반복은 초기화한다. 예산은 Episode 전체 기준이다.
- `scripted`는 모델 없는 계약 검증이다. 이 결과를 LLM 개선율로 보고하지 않는다.
- 실제 모델 실행 직전에 문항 × 반복 × 버전과 예상 호출 규모를 알린다. Langfuse 쓰기도 고지한다.
- `.env` 내용·키는 출력하지 않는다. 키가 없으면 `.env.example`을 보고 사용자가 직접 채우게 한다.
- 테스트 삭제, 실패 행 삭제, 기준·예산 완화, 미검수 승인으로 실패를 감추지 않는다.
- 기준을 바꿨다면 두 Agent 버전의 원자료를 같은 새 기준으로 다시 평가한다.
- Holdout은 최종 확인에만 사용한다. 회귀 승격 초안은 새 데이터 버전에서 검수한다.

## 수업 중 활동 (자유 실습)

`오전.md`·`오후.md`의 활동(`gold_agent.py`, `gold_agent_eval.py`, `economic_report_golden/`)은 **자유 실습**이다. 채점 대상이 아니므로 루트 `../AGENTS.md` 4절의 단계적 힌트(L0~L3)를 적용하지 않고, AI 조교는 구현까지 도울 수 있다. 다만 수강생이 코드를 자기 말로 설명할 수 있어야 한다.

- `오전.md`: 관심 분야 문서를 내려받아 DeepEval로 Golden Dataset을 만들고, 그 Golden Dataset에 답하는 Agent를 만든다.
- `오후.md`: `gold_agent.py`의 Langfuse 실행 기록을 보고 DeepEval 메트릭(예: FaithfulnessMetric) 설계를 상의하고, 기록 기반으로 `gold_agent.py` 개선점을 도출한다.
- `economic_report_golden/golden_dataset.csv`는 추적되는 **원본이며 읽기 전용**이다. 수정하지 않는다. `context`·`contexts.json`은 채점용 근거라 Agent에 주지 않는다.
- `gold_agent.py`는 원본을 읽어 답변을 `outputs/gold_agent/golden_dataset_answers.csv`에 쓴다(이미 채운 답은 이어받는다). 파일 상단의 `MAX_ROWS`로 처리 문항 수를 줄일 수 있다(`None`이면 전체, 10은 비용을 줄인 테스트 크기). `gold_agent_eval.py`는 같은 파일을 읽어 채점한다.
- 두 파일을 실행하면 모델·판사 호출과 Langfuse trace 쓰기가 일어난다. 실행 직전에 문항 수와 예상 호출 규모를 한 줄로 알린다.
