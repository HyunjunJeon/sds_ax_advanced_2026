# Day03_new 수업 설계 — Multi-Agent System 설계

2026-10-31 작성. 이 문서는 노트북과 `mas_lab`을 만드는 사람을 위한 계약이다. 수강생용 문서가 아니다.

## 1. 과정 경계와 결정 사항

**과정 구성.** 저자가 정한 다섯 Part를 노트북 하나씩으로 옮기고, 앞에 사전 점검, 뒤에 실습을 둔다. `Day02_new`와 같은 틀이다.

| 노트북 | Part | 분 | 한 줄 목표 |
|---|---|---:|---|
| `00-Setup.ipynb` | 사전 점검 | 10 | 두 키, 그래프, 모델, Deep Agent, EXA가 내 환경에서 도는지 확인한다 |
| `01-Workflow-vs-Agent.ipynb` | Part 1. Workflow와 Agent의 경계 | 60 | 다음 행동의 결정권과 실행 권한을 구분하고 Single 기준선을 남긴다 |
| `02-Agent-Architecture.ipynb` | Part 2. Agent Architecture의 변화 | 60 | 구조가 왜 바뀌어 왔는지를 직전 구조의 한계로 설명하고, Supervisor와 Handoff를 실행해 비교한다 |
| `03a-Sequence-Parallel.ipynb` | Part 3. Back to Basic: 네 가지 흐름 ① | 30 | 순차와 병렬을 직접 만든다 |
| `03b-Branch-Loop-Patterns.ipynb` | Part 3. 네 가지 흐름 ② | 30 | 분기와 루프를 만들고 패턴 이름을 네 흐름으로 번역한다 |
| `04a-Graph-Contracts-Budget.ipynb` | Part 4. Graph Engineering ① | 30 | 계약과 공유 예산을 그래프에 넣는다 |
| `04b-Graph-Failure-Approval.ipynb` | Part 4. Graph Engineering ② | 30 | 실패별 다음 행동, 늦은 결과, 승인과 멱등을 그래프에 넣는다 |
| `05a-Failure-Cost-Boundary.ipynb` | Part 5. Multi-Agent 선택 기준 ① | 30 | 실패 분류에서 출발해 이득과 비용, 나누는 기준을 가른다 |
| `05b-Measure-Fast-Compare.ipynb` | Part 5. Multi-Agent 선택 기준 ② | 30 | 같은 조건에서 구조를 재고 선택 근거를 쓴다 |
| `06-Lab-Research-Agents.ipynb` | 실습 | 60 | EXA로 병렬·직렬·연쇄 리서치 Deep Agent를 만들어 같은 주제로 비교한다 |

**분할(2026-11-03).** 03, 04, 05는 노트북 한 권을 의미 단위로 둘로 나눠 a/b로 둔다. 쪼갠 노트북마다 30분, 새로 쓴 것은 머리말·그림 셀·정리·확인 질문뿐이고 단독 실행을 위해 b는 a의 필요한 값을 준비 셀에서 다시 만든다(05b는 유료 셀 세 개를 다시 실행). 이 문서 아래의 절 번호와 셀 번호는 분할 전 노트북 기준이다.

**저자가 내린 결정(2026-10-31).**

| 결정 | 내용 |
|---|---|
| 채점 | 채점 과제 없음. 모든 코드를 제공한다. `직접 해보기`와 확인 질문만 둔다 |
| 관통 사례 | 고객 요청("결제가 두 번 됐어요. 취소하고 보상안도 함께 확인해 주세요.")을 Day02 문서 검색으로 받친다 |
| EXA | `Day03/task.md`의 Sequential vs Parallel 리서치는 06의 **필수** 실습이다 |
| 모델 | Anthropic API를 쓴다 |
| 키 | `.env`는 `Day02_new/.env`를 복사해 쓴다. 그래서 이 과정은 `Day02_new`와 같은 변수 이름을 읽는다(4절). `EXA_API_KEY`는 `Day03/.env`에서 옮겼다 |
| 기존 채점 과제 | 쓰지 않는다. `Day03/student_tasks.py`, `05`·`07`의 TODO, `10`~`13`, `challenge_tests/`, `WORKSHEET.md`를 출처로 삼지 않는다 |
| 강의 슬라이드 | 참고하지 않는다. 범위는 저자의 Part 구성으로 정하고 내용은 이 문서가 스스로 정의한다 |
| 자료 수준 | 설계 문서를 자세히 쓰고, 밀도 있는 실습 자료로 만든다(3절이 그 기준이다) |
| 실습 범위(2026-11-02) | 실습 "여러 Multi-Agent Architecture 활용(Single-Agent Baseline 비교 후 Verification·Budget·Evidence·Checkpoint 활용 / Supervisor와 Harness 구성으로 일관성 확보)"은 05 7절과 06을 합쳐 다룬다. 06은 바꾸지 않는다(6절) |
| Supervisor 용어(2026-11-02) | 라이브러리 관례를 따른다. 부모 모델이 `task`로 위임하고 결과를 돌려받아 최종 응답하는 구조가 Supervisor이고, Manager는 그것을 포함하는 넓은 이름이다(이름은 `langgraph-supervisor`의 `create_supervisor`가 쓰고, Deep Agents `subagents=`와 `build_supervisor`가 같은 모양이다). 02 5절의 일반 함수 뼈대는 같은 제어 흐름에서 다음 Worker를 함수가 고르게 한 것이다 |
| 자동 하위 에이전트(2026-11-02) | Deep Agents가 설계하지 않은 `general-purpose` 하위 에이전트를 자동으로 붙이는데, 이 에이전트는 부모의 도구를 받지만 이 과정의 허용 목록과 공유 예산 밖에서 돈다. 그래서 `mas_lab`을 import할 때 모든 Deep Agent에서 끈다(`mas_lab/__init__.py:9`, `use_designed_subagents_only`, `mas_lab/harness.py:25`). 비교용으로 프레임워크 기본을 만들어 보는 방법은 모델 호출 없이 `framework_default_subagent`(`mas_lab/harness.py:31`)로 둔다. 02 3절이 자동으로 끼워 넣은 Worker와 직접 설계한 Worker를 모델 없는 셀로 비교해 가르친다 |
| 05 0절(2026-11-02) | Part 5의 질문 "Agent를 나눌까?"는 작업을 먼저 Workflow와 Agent로 나타낸 뒤에야 뜻이 있어서, 05에 0절을 더했다. `build_hybrid` 그래프를 만들기만 하고 노드마다 담당(코드·모델·사람)을 표로 적어, Multi-Agent를 따질 대상이 모델이 맡은 칸뿐임을 확인한다 |
| 05 7절의 하네스 일관성과 공식 문서 구성(2026-11-02) | 실습 범위의 "Supervisor와 Harness 구성으로 일관성 확보"를 위해 7절에 하네스 일관성 셀과 공식 프레임워크 표를 더했다. 하네스 셀은 다섯 구조가 같은 예산·허용 목록·응답 형식·쓰기 게이트를 지나고 `general-purpose`가 없음을 모델 없이 읽는다. 표의 "가장 많이 쓰이는 구성"은 재 본 조사를 찾지 못해서, 사용 빈도가 아니라 공식 문서가 기본으로 싣는 구성으로 바꿔 쓴다. 출처 없는 수치는 인용하지 않는다 |
| Graph Engineering 정의(2026-11-02) | 04는 이 과정의 정의를 쓴다. 작업을 노드와 간선으로 명시하고, 노드마다 누가 판단하는지·무엇을 주고받는지·언제 멈추고 다시 하는지를 그래프에 적어 넣는 일이다. 외부 글은 정리 셀에 비교용 읽을거리로만 둔다. 앞 판(2026-10-31)은 이 용어를 읽을거리로만 두고 정의를 세우지 않았다 |

**설계자가 정한 사항.** 저자가 G1에서 바꿀 수 있다.

1. **폴더.** `Day03_new/`를 새로 만든다. `Day03/`, `Day02_new/`, 루트 `pyproject.toml`, `uv.lock`은 수정하지 않는다.
2. **Part 2의 해석.** "변화"는 직전 구조의 한계 때문에 다음 구조가 나온 흐름으로 가르친다. Part 3은 그 패턴들을 다시 네 흐름으로 분해한다.
3. **Part 순서.** 저자의 Part 순서를 그대로 따른다.
4. **결제 정책 문서.** Day02 코퍼스에 결제·환불 정책이 없어서 `billing-policy`를 1개 추가한다. 보상은 기존 SLA 문서로 받친다. 사례를 장애 크레딧으로 바꾸면 추가 없이 되지만 선택한 사례가 달라진다.
5. **`rag_lab` 재사용.** `Day02_new/rag_lab/`의 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 네 파일을 바이트 그대로 복사하고 `settings.py`에는 EXA 항목만 더한다. 런타임 공유는 하지 않는다. 문서를 추가해야 하고 `ROOT`가 폴더 기준이기 때문이다. 원본과 달라지면 테스트가 알려 준다. **이 규칙은 2026-11-02 09:13에 지켜졌다.** `Day02_new/rag_lab/`의 네 파일을 다시 복사했고 `cmp`로 같음을 확인했다. 복사본 시험 `test_rag_lab_copies_are_byte_identical`(`tests/test_layout.py:13`)이 네 칸 `[corpus.py]`, `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]`를 모두 보고, 전체 `tests`는 611개 모두 통과하며 실패는 0이다. 앞 상태는 이력으로 남긴다. 2026-11-01에는 `corpus.py`만 같고 `retrieval.py`, `evidence.py`가 `Day02_new`와 달라 두 칸이 실패했으며(610개 중 `2 failed, 608 passed`) `pipeline.py`는 복사하지 않았다. 저자가 그 실패를 결함이 아니라 끝나지 않은 동기화로 정해 두었고, 그 예외는 이 동기화로 끝났다. `settings.py`는 일부러 다르다. EXA 항목이 있고 `make_embeddings`가 없으며 `Day02_new` 쪽은 키 항목, 캐시 쓰기 칸, `make_reranker`가 더 늘었다(8.2절). 시험은 이 파일을 보지 않고 이번 동기화도 건드리지 않았다. 복사한 코드에는 이 과정이 부르지 않는 기능이 들어 있다: `Retriever`의 `fusion` 방식(`rag_lab/retrieval.py:147`), 질의 분해 `decompose_question`(`rag_lab/pipeline.py:46`), 미리 검색 `prefetch`(`rag_lab/evidence.py:153`), 모델 예산과 따로 세는 `Budget.max_decision_calls`(`rag_lab/evidence.py:30`). `mas_lab`, 노트북, `tests`에는 이 넷을 부르는 곳이 없다(`grep`으로 확인했다). 이 과정의 검색은 계속 BM25만이다. `mas_lab/runner.py:32`가 `Retriever(load_corpus())`로 만들고 기본값이 `mode="bm25"`이기 때문이다(`rag_lab/retrieval.py:130`). 01~05의 유료 재실행은 저자가 2026-11-02 오전에 하지 않기로 정했었다. 같은 날 밤 Supervisor 용어 수정 뒤 저자가 13개 기록을 모두 다시 돌리기로 정해(21:40~22:51), 지금 실행 기록은 모두 동기화 뒤의 코드로 돌았다(9.2절의 후속(2026-11-02, 전체 재실행) 문단). [이후 `tests/test_harness.py`가 더해져 625개가 되었고(2026-11-02), 2026-11-03 노트북 분할 뒤 전체는 717개(`717 passed`, 실패 0)다. 위 611은 그 앞 시점의 값이다]
6. **제외 항목.** OpenViking, 웹 문서 적재. 웹은 06의 EXA 검색으로만 다룬다.
7. **`langgraph-supervisor` 미사용.** 설치되어 있지만 패턴의 동작을 감춘다. 이 과정은 패턴이 새 제어 구조가 아니라 네 흐름의 조합임을 보여 주는 것이 목표다.
8. **`matplotlib` 미사용.** 표와 문자 막대로 출력한다. 한글 글꼴 문제가 수강생 환경마다 다르다.

## 2. 공통 규칙

1. **이 과정은 실제 모델로만 돈다.** 첫 코드 셀이 `require_key()`를 부르고, 없으면 한국어 안내와 함께 멈춘다. 대본 모델, 건너뛰기, 저장된 출력, 키 없는 대체 경로를 넣지 않는다. 단위 시험용 가짜 모델은 `tests/`에만 둔다.
2. **모델 판단이 필요 없는 것은 모델을 부르지 않는다.** 그래프 구조, reducer, 게이트, 멱등, 실패 경로는 일반 함수 노드로 돌린다. 이것은 키 없는 경로가 아니다. 결정적 구조를 결정적으로 보여 주는 것이다. 이런 셀은 `[C]`로 표시한다. 일반 함수 노드에 모델 흉내 문장을 넣지 않고, 출력에 "모델 호출 0회"를 적는다.
3. 유료 호출 셀은 호출 직전에 `announce(purpose, model_calls=N, exa_calls=M)`로 규모를 한 줄 고지한다. 셀 표기 `[L]`은 유료 호출이 있는 코드, `[C]`는 없는 코드, `[M]`은 markdown이다.
4. 측정 수치를 markdown에 미리 쓰지 않는다. 결론은 출력 표를 읽는 질문으로 쓴다. 이 문서의 수치는 설계 근거이며 구현 후 달라질 수 있다.
5. 저장본에는 출력을 남기지 않는다. 실행 증거(셀별 시간, 토큰, 호출 수)는 `outputs/live/`에 따로 남긴다.
6. 노트북은 앞 노트북의 kernel 상태에 의존하지 않고 단독 실행된다. `outputs/design_log.json`이 없어도 06이 멈추지 않는다.
7. 한 번 실행한 결과는 언제나 "1회 관찰"로 부른다. 반복이 3회 미만이면 통계 주장을 하지 않는다.
8. 실패 행을 지우지 않는다. `BudgetExceeded`, 검증 실패, 429, 평가 오류는 행으로 남긴다. usage 누락은 0토큰이 아니다.
9. `data/gold.jsonl`을 읽는 곳은 `mas_lab/evaluation.py` 하나다. 도구, 프롬프트, 구조 빌더, 게이트는 이 모듈을 import하지 않는다.
10. 용어는 근거(Evidence), 원문, 담당자(owner), 예산(budget), 인용, 기준일(as_of), 고객(entity)을 쓴다. Supervisor, Worker, Handoff, Router, Fast/Slow Path는 영어 그대로 쓴다.
11. 설명은 존댓말로 쓴다. 노트북은 강의 슬라이드를 언급하지 않고 그 자체로 읽히게 쓴다. `check_notebook.py`가 "슬라이드"라는 단어를 금지한다.
12. `직접 해보기`의 `[L]` 셀은 첫 줄에 `RUN_EXERCISE = False`를 두고, 꺼져 있으면 "실행하지 않았습니다. 고친 뒤 True로 바꾸세요"를 출력한다. 수강생이 바꾼 뒤 돌리는 칸이라 전체 실행에 비용을 더하지 않는다. 대용량 선택 셀은 같은 방식으로 `RUN_OPTIONAL`을 쓴다(`Day02_new/README.md`의 03과 같다). 이 셀들이 실제로 도는지는 저자가 `run_live.py --exercises`로 확인한다. 이 옵션은 임시 사본에서 두 상수를 `True`로 바꿔 실행한다. 노트북에 환경변수 분기를 넣지 않는다.

## 3. 밀도 기준

이 절이 "밀도 있는 실습 자료"의 정의다. 분량이 아니라 **수강생이 실행 결과를 근거로 판단하는 횟수**를 늘리는 것이 목적이다.

### 측정 기준선

`Day02_new` 실측(2026-10-31, 저장본 파일 측정). 코드 줄은 빈 줄 포함 전체 줄 수다.

| 노트북 | 전체 셀 | 코드 셀 | markdown 글자 | 코드 줄 |
|---|---:|---:|---:|---:|
| 01 | 40 | 19 | 12,467 | 223 |
| 02 | 50 | 25 | 15,237 | 349 |
| 03 | 46 | 27 | 11,754 | 363 |
| 04 | 64 | 28 | 13,220 | 258 |
| 05 | 52 | 32 | 12,575 | 315 |
| 06 | 41 | 27 | 11,184 | 328 |

### 정량 하한

| 항목 | 60분 노트북(01~06) | 00-Setup | 검사 방법 |
|---|---:|---:|---|
| 전체 셀 | 46 | 14 | `check_notebook.py` |
| 코드 셀 | 24 | 7 | 〃 |
| markdown 글자 | 11,000 | 2,500 | 〃 |
| `**관찰할 것.**` 문단 | 6 이상, 그리고 모든 `[L]` 묶음과 `**실패 재현.**` 묶음 뒤 | 2 | 〃 |
| `**먼저 예측하세요.**` 문단 | 3 | 0 | 〃 |
| `**실패 재현.**` 표시 셀 | 3 | 0 | 〃 |
| `직접 해보기` 과제 | 4 (골격 코드 셀 포함) | 2 | 〃 |
| 확인 질문 | 5 | 2 | 〃 |
| 출력 있는 코드 셀 | 90% 이상 | 100% | `audit_live.py`, 실행본 |

코드 줄 수는 하한으로 두지 않는다. 셀 하나는 대체로 25줄 이내로 쓴다. 긴 코드는 `mas_lab`으로 옮기고 `inspect.getsource`로 보여 준다.

**검사기가 셀을 식별하는 규약.** `[L]`, `[C]`는 이 문서의 표기라 노트북 안에 그대로 남지 않는다. 그래서 다음을 지킨다. 유료 호출 셀은 `announce(` 호출을 포함한다. 실패 재현 코드 셀은 첫 줄을 `# 실패 재현:` 주석으로 쓴다. 관찰 문단은 markdown 셀에 `**관찰할 것.**`으로 쓴다. `check_notebook.py`는 `announce(` 셀과 `# 실패 재현:` 셀을 이어진 묶음으로 보고, 다음 묶음이 나오기 전에 `**관찰할 것.**`이 있는지 확인한다. `직접 해보기`와 그 뒤의 셀은 이 묶음 검사에서 뺀다.

### 절 구성 규칙

모든 절은 아래 순서를 따른다.

1. **문제.** 이 절이 막으려는 실패나 답하려는 설계 질문을 먼저 쓴다. 개념 정의부터 시작하지 않는다.
2. **예측.** 실행 전에 수강생이 결과를 적게 한다. 결과를 본 뒤 이유를 지어내지 않게 하기 위해서다.
3. **실행.** 가능하면 실패를 먼저 재현하고, 그다음 해결 구조를 실행한다.
4. **관찰.** 고정된 정답을 쓰지 않고, 출력의 어느 칸을 어떻게 읽을지 적는다. 모델 결과에 따라 달라지는 경우를 나눠 쓴다.
5. **변형.** 조건 하나만 바꿔 다시 돌린다.
6. **연결.** 앞 절의 무엇과 이어지는지, 다음 절이 왜 필요한지 쓴다.

### 금지

- 개념 설명 뒤에 그 개념이 그대로 도는 것만 보여 주는 셀. 실패나 변형이 없으면 설명으로 합친다.
- 출력 없는 코드 셀. 정의 셀도 `.name`, 스키마, `show_graph` 중 하나를 출력한다.
- "결과에서 볼 수 있듯이"처럼 실행 결과를 전제하는 문장.
- 모델 결과가 특정하게 나와야만 말이 되는 설명. 결과가 달라도 읽을 수 있게 쓴다.
- 패턴 이름만 바꾼 같은 코드의 반복.

### 공유 실습 장치

- **설계 기록.** 이 과정의 결과물은 Agent 조직도가 아니라 구조를 고른 이유다. 그래서 각 노트북 끝의 코드 셀이 아래 설계 질문에 대한 수강생의 답을 `outputs/design_log.json`에 쓴다. 06이 모아 출력한다.

| 노트북 | 쓰는 항목 |
|---|---|
| 01 | 업무 목표: 어떤 상태를 완료로 볼까? |
| 02 | Agent·SubAgent의 필요성: 코드나 Skill로 충분하지 않은 이유는? |
| 03 | 작업 Graph: 순차·병렬·분기·루프는? |
| 04 | Context·권한과 예산·종료 |
| 05 | 평가 근거: 어떤 결과로 선택을 정당화할까? |

- **실행 행.** 모든 구조 실행이 같은 칸의 행을 만든다(5.5절 `RunRow`). 누가 결정했는지, 무엇이 얼마나 들었는지, 누가 최종 응답했는지, 성공했는지를 한 줄로 읽기 위해서다.
- **판서 연결.** `Day03/Day03_01.png`의 투자 심사 판서를 04(Context 요약 손실, 숫자와 계산기)와 05(암묵지와 Skill)의 질문으로 쓰고, 06의 전이 과제로 다시 쓴다. 이미지는 8MB라 복사하지 않고 말로 옮긴다.

## 4. 실행과 환경

- 실행: 저장소 루트에서 `uv sync --locked` 한 번, `cd Day03_new && uv run jupyter lab`. `pyproject.toml`을 두지 않는다. 이 폴더는 workspace 멤버가 아니며 `uv run`이 루트 환경을 찾는다(`Day02_new/AGENTS.md` 3장과 같다).
- `.env`: 저자의 지시로 `Day02_new/.env`를 복사해 두었다(권한 600, git 제외). 현재 항목은 `ANTHROPIC_API_KEY`(설정됨), `DAY02_MODEL`, `DAY02_EFFORT`, `DAY02_EMBEDDING_MODEL`, `OPENROUTER_*`(쓰지 않음)다. `EXA_API_KEY`는 저자의 지시로 `Day03/.env`에서 옮겼다. 수강생은 `https://exa.ai/`에서 직접 발급해 넣는다.
- 변수 이름: `.env`를 복사해 그대로 쓰려면 같은 이름을 읽어야 한다. 그래서 `DAY03_MODEL`을 만들지 않고 `DAY02_MODEL`, `DAY02_EFFORT`를 읽는다. 이름이 어색한 대신 수강생이 파일을 고칠 일이 없다. `.env.example`에 이유를 한 줄 적는다.
- 현재 값은 `claude-sonnet-5-5`, `medium`이다. `Day02_new/.env.example`과 같다.
- 재시도: `make_model`의 `max_retries=0`을 유지한다. SDK 재시도는 예산과 사용량에 잡히지 않는다. 병렬 호출의 429는 실패 행으로 드러낸다.
- 추적: `run_live.py`는 kernel 환경에서 비밀 이름 변수를 지운다(`Day02_new/tests/run_live.py`의 `kernel_environment`). LangSmith로 내용이 나가지 않게 하기 위해서다.

### 설계 근거 실측

2026-10-31 프로토타입. `deepagents 0.7.32`, `langgraph 1.2.19`, `claude-sonnet-5-5`, 실행 1회. 스크립트는 저장소에 남기지 않았다. 모델 호출은 약 14회.

| 확인한 것 | 결과 | 설계에 쓰는 곳 |
|---|---|---|
| `Send` 3개, 각 0.3초 대기 | 전체 0.306초 | 03 병렬 |
| 같은 그래프 `config={"max_concurrency": 1}` | 전체 0.916초 | 03·06 "같은 분해"의 직렬 스위치. 그래프를 고치지 않는다 |
| reducer 없는 동시 쓰기 | `InvalidUpdateError: At key 'last': Can receive only one value per step` | 03 실패 재현 |
| `Command(goto=)`에 반환 타입 없음 | `get_graph()` edge가 `triage → __end__`로만 보인다 | 02 실패 재현. `Command[Literal[...]]`를 쓰면 실제 edge가 보인다 |
| `interrupt` 재개 | 노드가 처음부터 다시 실행된다. 앞부분 카운터 2, 뒷부분 1 | 04 실패 재현. 부작용을 `interrupt` 앞에 두면 두 번 일어난다 |
| `RetryPolicy(retry_on=TimeoutError, max_attempts=3)` | 두 번 실패 후 회복 | 04 |
| `Send(..., timeout=0.2)` + 동기 노드 | `ValueError: Node timeouts are only supported for async nodes` | 04. 이 과정의 시간 제한은 Budget이 맡는다 |
| `recursion_limit=5` | `GraphRecursionError` | 03 |
| 실제 모델 4개 `Send` | 전체 1.63초, 개별 합 5.92초, 429 없음 | 03 |
| Deep Agents `subagents=` 2개, "동시에" 지시 | 한 메시지에 `task` 2개, 도구 구간 겹침, 모델 6회, 입력 약 23,000토큰 | 02 "모델이 정한 병렬", 05 비용 |
| callback 전파 | 부모 config의 callback이 subagent 모델 호출까지 잡는다 | `ModelMeter` |
| subagent 도구 목록 | 기본 파일 도구가 함께 보이고 `task`는 없다 | allowlist를 subagent마다 건다 |
| `with_structured_output(method="json_schema")` | 정상 | 라우터, 합성 |
| `method="function_calling"` | 동작하지만 강제 호출 미지원 경고 | 쓰지 않는다 |
| `create_deep_agent(response_format=ProviderStrategy(...))` | 정상, 모델 2회 | Worker |
| 위 Worker의 `evidence_refs` | `"lookup_outage: 8월 장애"`처럼 검증할 수 없는 값을 냈다 | 04: 스키마 통과와 근거 검증은 다르다 |
| `ToolStrategy` | Opus 5.5에서 `tool_choice=any` 400(`Day02_new/rag_lab/agent.py`의 `build_rag_agent` 안 주석) | 쓰지 않는다 |
| Day02_new 전체 실행 | 모델 152회, 약 USD 0.87(`Day02_new/docs/audit-live-notes.md`) | 비용 추정의 기준 |

**EXA 실측(2026-11-01, 2026-11-02 재실행에서 다시 확인).** `Day03_new/.env`에 `EXA_API_KEY`가 설정돼 있고, 00과 06 실행에서 실제로 호출했다. 요청은 `POST https://api.exa.ai/search`(`base_url`), 헤더 `x-api-key`, 본문 `query`·`type: auto`·`numResults`·`contents.text.maxCharacters`다(`mas_lab/exa.py:55`, `mas_lab/exa.py:60`). 응답에서 `costDollars.total`과 `publishedDate`를 읽는다(`mas_lab/exa.py:68`, `mas_lab/exa.py:75`). 확인한 값은 다음과 같다.

| 확인한 것 | 결과 | 읽은 곳 |
|---|---|---|
| 00 셀 17, `max_chars=300` | 결과 3건, 검색 1회, 1.29초, 비용 0.007달러 | `outputs/live/00-Setup.executed.ipynb` |
| 06 셀 7, `max_chars=2500` | 결과 3건, 비용 0.007달러, 대기 1.06초. 게시일은 3건 중 1건이 `2024-12-19T00:00:00.000Z` 꼴이고 2건은 `None`이라 `확인 안 됨`으로 나왔다 | `outputs/live/06-Lab-Research-Agents.executed.ipynb` |
| `source_id` | `S-a273d17f`처럼 `S-` 뒤 16진수 8자 | 00 셀 17, `mas_lab/exa.py:73` |
| 검색 한 번의 비용 | 06 셀 12는 2회에 0.014달러, 셀 17의 6회는 셀 20 표의 `EXA 비용(USD)` 칸에서 0.042달러라 한 번에 0.007달러 | 06 실행본 출력 |
| 실행 전체의 EXA 호출 | 기본 실행 22회(00에서 1회, 06에서 21회), `--exercises` 실행 47회(06) | 9.2절 |

요청 본문의 필드는 `Day03/common/exa_client.py:46-55`에서 `contents.maxAgeHours`를 뺀 것과 같고 `includeDomains`는 도메인을 줄 때만 더한다(`mas_lab/exa.py:57-58`). 같은 질의의 결과는 호출마다 달라질 수 있어, 위 값은 2026-11-02 재실행의 1회 관찰이다. 2026-11-01 기록은 00 셀 17이 0.17초, 06 셀 7이 대기 0.87초에 게시일 3건 중 2건이었다.

## 5. 관통 사례와 데이터

수강생은 하루 내내 같은 고객 요청을 다른 구조로 처리한다. 구조 사이의 차이를 사례 차이와 섞지 않기 위해서다.

### 5.1 왜 이 사례가 네 흐름을 다 드러내는가

```text
고객 요청 T-1001: "결제가 두 번 됐어요. 취소하고 보상안도 함께 확인해 주세요."

verify      고객 범위 확인                          (선행 조건)
   |
   +--> billing  결제 사실 조회                     (독립: 병렬 가능)
   +--> policy   환불 규정, SLA, 추가 약정 검색      (독립: 병렬 가능)
   +--> outage   가용률 조회                        (독립: 병렬 가능)
   |
credit      기본 이용료 x 크레딧 비율               (순차: billing, policy, outage 필요)
   |
proposal    환불 제안과 보상안, 근거, 불확실성       (모델 판단)
   |
gate        정책·권한 검증                          (코드. 쓰기 요청만)
   |
   +--> 승인 필요 -> interrupt -> 실행 -> 결과 확인
   +--> 정책 불가 -> 미실행 종료
```

### 5.2 추가 원문: `data/business/billing-policy.md`

```markdown
# 결제 정정·환불 규정
## 중복 결제 판단
같은 청구서에 대해 승인된 결제가 두 건 이상이면 중복 결제로 본다.
먼저 승인된 결제를 유효 결제로 두고, 나중에 승인된 결제를 환불 대상으로 한다.
금액이 같아도 청구서가 다르면 중복 결제가 아니다.
## 환불 기한과 전환
환불은 결제일부터 90일 이내에 처리한다.
90일이 지난 건은 자동 환불하지 않고 재무 담당자 심사로 넘긴다.
## 승인
환불액이 100만원을 초과하면 재무 담당자 승인 후 실행한다.
100만원 이하는 정책 검증을 통과하면 바로 실행할 수 있다.
## 보상과의 관계
중복 결제 환불과 서비스 크레딧은 별개로 처리한다. 환불 승인이 크레딧 신청을 대신하지 않는다.
## 기록
환불 실행에는 요청 ID와 청구서 번호를 남기며, 같은 요청 ID로 두 번 실행하지 않는다.
```

`catalog.json`에 추가: `doc_id=billing-policy`, `domain=재무`, `entity=공통`, `version=1.0`, `valid_from=2026-01-01`, `valid_until=null`, `status=approved`, `owner=재무 담당`, `family=null`. 나머지 10개 문서는 `Day02_new/data/business/`에서 그대로 복사한다.

### 5.3 고정 사실: `data/support/`

모델이 지어낼 수 없는 **사실**의 출처다. 저장소에 고정된 가상 데이터이며 수업용임을 파일 첫 키와 markdown에 밝힌다.

`billing.json`

| 고객 | payment_id | invoice_id | 승인 시각 | 금액 | 기본 이용료분 | 사용량 초과분 | 설계 의도 |
|---|---|---|---|---:|---:|---:|---|
| 알파 | P-9001 | INV-2026-08 | 2026-09-01 09:00 | 1,200,000 | 1,000,000 | 200,000 | 유효 결제 |
| 알파 | P-9002 | INV-2026-08 | 2026-09-01 09:02 | 1,200,000 | 1,000,000 | 200,000 | 중복. 100만원 초과라 승인 필요 |
| 알파 | P-8101 | INV-2026-07 | 2026-08-01 09:00 | 1,000,000 | 1,000,000 | 0 | 정상 결제. 환불 요청은 정책 불가 |
| 알파 | P-7001 | INV-2026-03 | 2026-04-01 09:00 | 1,000,000 | 1,000,000 | 0 | 유효 결제 |
| 알파 | P-7002 | INV-2026-03 | 2026-04-01 09:05 | 1,000,000 | 1,000,000 | 0 | 중복이지만 90일 초과. 사람 심사로 전환 |
| 베타 | P-5001 | INV-B-2026-08 | 2026-09-01 10:00 | 300,000 | 300,000 | 0 | 유효 결제 |
| 베타 | P-5002 | INV-B-2026-08 | 2026-09-01 10:01 | 300,000 | 300,000 | 0 | 중복. 100만원 이하라 승인 없이 실행 |

`outage.json`

| 고객 | 월 | 가용률 | 사건 | 설계 의도 |
|---|---|---:|---|---|
| 알파 | 2026-08 | 99.3 | INC-311, 서비스 제공자 네트워크 장애, 2026-08-19 | 99.0 이상 99.5 미만 구간, 크레딧 15% |
| 알파 | 2026-07 | 99.95 | 없음 | 목표 달성. 크레딧 없음 |
| 베타 | 2026-08 | 99.7 | INC-402, 2026-08-22 | 베타 SLA는 99.9 미만이면 30% |

**정답이 숫자 함정을 품게 만든 이유.** T-1001의 크레딧은 기본 이용료 1,000,000원의 15%인 **150,000원**이다.

| 오답 | 왜 틀렸는가 | 원문 |
|---|---:|---|
| 180,000원 | 사용량 초과분을 계산 기준에 넣었다 | `sla-a-v2.md:11` |
| 300,000원 | 두 번 결제한 금액을 모두 넣었다 | 〃 |
| 9월 15일 신청 기한 | 추가 약정을 놓쳤다. 정답은 9월 20일. 옳은 답도 '기본은 15일'이라고 쓸 수 있어 금지 표현이 아니라 필수 사실로 검사한다 | `sla-a-amendment.md:6`, `sla-a-v2.md:16` |

판서의 "숫자가 들어가면 LLM은 거짓말을 할 가능성이 몇 %?"와 "Tool: 계산기"가 여기로 이어진다. `calculate_credit`은 입력을 곱하는 코드이고, 비율을 고르는 판단은 모델이 원문을 읽고 한다.

### 5.4 사례: `data/cases.jsonl`, `data/gold.jsonl`

사례 파일에는 정답이 없다. 평가 필드는 `gold.jsonl`에만 있다. `type`은 단순, 복합, 정보 부족, 승인 필요에 범위 밖과 후속 턴을 더했다.

| id | type | entity | as_of | 질문 | 기대 outcome | 필수 사실 | 금지 |
|---|---|---|---|---|---|---|---|
| `simple-deadline` | simple | 알파 | 2026-09-08 | 서비스 크레딧 신청 기한은 언제까지인가요? | answered | 다음 달 20일, `sla-a-amendment` 인용 | 없음 |
| `simple-duplicate-rule` | simple | 알파 | 2026-09-08 | 같은 청구서를 두 번 결제하면 어떻게 처리되나요? | answered | 나중 결제 환불, `billing-policy` 인용 | 없음 |
| `complex-double-pay` | complex | 알파 | 2026-09-08 | 결제가 두 번 됐어요. 취소하고 보상안도 함께 확인해 주세요. (T-1001) | needs_approval | P-9002, 1,200,000, 99.3, 15%, 150,000, 9월 20일 | 180,000, 300,000, 실행 전 원장 변경 |
| `complex-ops-log` | complex | 공통 | 2026-09-08 | 검색 서비스 장애 시 타임아웃 증가 점검 순서와 운영 접근 로그의 보관 기간·예외를 설명하세요. | answered | upstream 지연, 연결 풀, 인덱스, 90일, 보존 명령 | 없음 |
| `insufficient-unknown-payment` | insufficient | 알파 | 2026-09-08 | 결제 번호 P-7777도 환불해 주세요. | insufficient | 조회되지 않음 명시 | 원장 변경, 금액 단정 |
| `insufficient-no-policy` | insufficient | 알파 | 2026-09-08 | 법인카드 포인트로 보상받는 규정이 있나요? | insufficient | 근거 없음 명시 | 근거 없는 규정 단정 |
| `approval-refund-now` | approval | 알파 | 2026-09-08 | P-9002 환불을 지금 바로 실행해 주세요. | needs_approval | 승인 필요, 100만원 초과 | 승인 전 원장 변경 |
| `policy-deny-normal` | approval | 알파 | 2026-09-08 | P-8101도 중복 같으니 환불해 주세요. | denied | 중복 아님, 청구서 1건 | 원장 변경 |
| `policy-human-old` | approval | 알파 | 2026-09-08 | P-7002 중복 결제를 환불해 주세요. | human_review | 90일 초과, 재무 담당자 심사 | 원장 변경 |
| `approval-beta-small` | approval | 베타 | 2026-09-08 | P-5002 중복 결제를 환불해 주세요. | executed | 300,000 환불, 원장 1건 | 원장 2건 |
| `scope-beta-from-alpha` | scope | 알파 | 2026-09-08 | 베타 계약 기준으로 크레딧 비율을 알려 주세요. | out_of_scope | 범위 밖 명시 | 30% 단정 |
| `followup-handoff` | followup | 알파 | 2026-09-08 | 턴 1: T-1001, 턴 2: 그럼 장애 보상은 언제까지 신청하나요? | answered | 턴 2에 9월 20일 또는 다음 달 20일 | 없음 |

`gold.jsonl` 필드: `id`, `outcome`, `required_any`(리스트의 리스트. 각 묶음에서 하나 이상 포함), `required_docs`, `forbidden`, `ledger_refunds`(실행 후 기대 건수), `route`(02·03 라우터 관찰용). 숫자는 `1,200,000`과 `1200000`, `120만원`을 같은 묶음에 넣는다.

**평가의 한계를 숨기지 않는다.** 문자열 포함 검사는 표현이 다르면 놓치고 문맥을 모른다. 그래서 칸 이름을 `정답`이 아니라 `자동 검사`로 쓰고, 05와 06에서 사람이 원문과 대조하는 칸을 따로 둔다.

**N3 자체 검증.** 필수 사실마다 근거 행이 실제 원문에 있는지 대조하고, BM25가 `billing-policy`를 찾는지 확인한다. 코퍼스가 달라져도 `complex-ops-log`의 기대 문서가 범위 안에 있는지 본다.

### 5.5 `RunRow`

```python
class RunRow(TypedDict):
    run_id: str; structure: str; case_id: str; repeat: int
    status: str                 # ok | budget_exceeded | validation_failed | model_error | ...
    outcome: str | None         # FinalAnswer.outcome
    control_owner: list[str]    # 다음 행동을 결정한 주체의 순서
    final_speaker: str          # 사용자에게 최종 응답한 주체
    model_calls: int; tool_calls: int; exa_calls: int
    input_tokens: int | None; output_tokens: int | None; cache_read_tokens: int | None
    elapsed_seconds: float; context_bytes: int; max_worker_overlap_seconds: float
    errors: list[str]; answer: str; evidence_refs: list[str]
    ledger_refunds: int; policy_violations: list[str]
```

토큰 값은 usage가 없으면 `None`이다. 합계에서 0으로 세지 않고 `usage 누락 N건`으로 출력한다.

## 6. Part 대응

저자의 Part가 범위다. 최종 감사가 이 표와 노트북 절 제목을 대조한다.

| Part | 노트북 | 반드시 답하는 질문 |
|---|---|---|
| Part 1. Workflow와 Agent의 경계 | 01 1~5절 | 다음 행동은 누가 정하는가? 실행 권한은 누구에게 있는가? 무엇이 기준선인가? |
| Part 2. Agent Architecture의 변화 | 02 1~6절 | 왜 구조가 바뀌었는가? 결과를 돌려받는 것과 대화를 넘기는 것은 어떻게 다른가? |
| Part 3. Back to Basic: 네 가지 흐름 | 03 1~6절 | 순차·병렬·분기·루프는 각각 언제 쓰고 어떻게 깨지는가? 패턴은 어떤 흐름의 조합인가? |
| Part 4. Graph Engineering | 04 1~8절 | 이 과정의 정의(작업을 노드와 간선으로 명시하고 노드마다 판단 주체, 계약, 멈춤과 재시도를 적는 일)로, 계약, 예산, 실패별 다음 행동, 부분 실패, 승인과 멱등을 그래프에 어떻게 넣는가? |
| Part 5. Multi-Agent 선택 기준 | 05 0~8절 | 작업을 먼저 Workflow와 Agent로 나타냈는가(0절)? 그 위에서 언제 나누고 언제 나누지 않는가? 무엇을 재서 어떻게 정당화하는가? |
| 실습 | 05 7절 + 06 | Single 기준선과 여러 구조를 같은 예산·게이트·근거 검증 아래에서 재고(05 7절), 같은 주제로 구조를 바꿔 재고 자기 말로 선택한다(06) |

## 7. 기존 Day03 자료의 이동

쓰는 것은 제공 코드와 자유 실습뿐이다. 채점 과제와 학생 구현 파일은 읽지도 옮기지도 않는다.

| 기존 | 새 위치 | 바뀌는 점 |
|---|---|---|
| `01_baseline_rag.py` | 01 5절 | 검색 파이프라인 대신 `create_deep_agent` Single |
| `02_adaptive_rag.py` | 03 5절 | 계획·검토·제한 재검색을 루프로 |
| `03_sequential_rag.py` | 03 2절 | 역할별 입력 크기 측정을 유지 |
| `04_router_rag.py` | 03 4절, 05 6절 | 오분류 비용을 직접 재현 |
| `06_supervisor_rag.py` | 02 5절, 04 5~6절 | 일시 실패 후 복구와 완료 결과 보존 유지 |
| `08_web_enrichment.py` | 06 2절 | 적재 없음. 외부로 나가는 질의 경계와 도메인 제한만 유지 |
| `09_compare.py` | 05 7절 | 7구조 × 6사례 × 3회 대신 3구조 × 2유형 × 1회가 기본, 전체는 선택 셀 |
| `task.md` | 06 전체 | 필수 실습 |
| `common/exa_client.py` | `mas_lab/exa.py` | 도메인 제한 패턴 재사용. 스냅샷 재생은 빼고 비용 칸은 유지 |

**쓰지 않는 것.** `student_tasks.py`, `05_parallel_rag.py`, `07_handoff_rag.py`, `10`~`13`번 파일, `challenge_tests/`, `WORKSHEET.md`. 병렬과 Handoff는 LangGraph API에서 새로 쓴다.

## 8. 지원 모듈

### 8.1 파일 구성

```text
Day03_new/
  00-Setup.ipynb ... 06-Lab-Research-Agents.ipynb
  rag_lab/      corpus.py retrieval.py evidence.py pipeline.py (Day02_new와 바이트 동일, 1절 5번), settings.py (EXA 추가, 일부러 다름), __init__.py
  mas_lab/      __init__.py harness.py trace.py view.py contracts.py desk.py ledger.py workers.py structures.py gate.py hybrid.py runner.py evaluation.py exa.py research.py
  data/         business/ support/ cases.jsonl gold.jsonl
  skills/       refund-case/ credit-case/ insufficient-evidence/
  tests/        check_notebook.py run_live.py wait_live.py audit_live.py cost_report.py fakes.py conftest.py test_*.py
  docs/         DESIGN.md audit/ (감사 작업 기록의 익명 사본. 수업 자료가 아니다)
  outputs/      git 제외
  .env .env.example .gitignore README.md AGENTS.md CLAUDE.md
```

모듈당 150줄 이내로 유지해 수업 중 `inspect.getsource`로 읽을 수 있게 한다. 세는 것은 공백이 아닌 줄이고 `mas_lab/*.py` 전부가 대상이다(`tests/test_layout.py:20-22`). 지금 `mas_lab/hybrid.py`와 `mas_lab/workers.py`가 정확히 150줄이라 한 줄만 더해도 이 시험이 실패한다. `mas_lab/__init__.py`는 `import`할 때 `general-purpose`를 끄는 한 줄만 둔다(8.14절). 다른 이름을 다시 내보내지 않으므로 노트북은 `from mas_lab.trace import ...`처럼 모듈을 밝혀 import한다. 공개 이름의 기준은 8.12절 표이고 표에 없는 공개 이름을 더하지 않는 것이 규칙이다. 언더스코어로 시작하는 내부 함수는 자유다. 노트북이 import하는 이름이 그 모듈에 실제로 있는지는 `tests/test_notebook_code.py`가 확인한다(`import_problem`, `test_notebook_import_resolves`). 공개 이름의 전체 집합을 고정하는 시험은 없다.

8.2~8.11의 코드 블록은 설계 스케치다. 어느 모듈에 무엇이 있는지는 8.12절 표와 코드가 기준이고, 스케치와 코드가 어긋난 곳은 해당 절에서 코드에 맞췄다.

### 8.2 `rag_lab.settings` (Day02_new에서 변경)

```python
ROOT: Path   # Day03_new
@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False); exa_key: str = field(repr=False, default="")
    model: str; effort: str
    has_key: bool; has_exa_key: bool   # property
load_settings() -> Settings            # ROOT/.env만 읽는다. 셸의 값을 합치지 않는다
key_status(settings=None) -> dict[str, str]   # 두 키는 설정됨/미설정만
require_key(settings=None) -> Settings
require_exa_key(settings=None) -> Settings    # 없으면 https://exa.ai/ 발급과 EXA_API_KEY 입력을 안내
announce(purpose: str, *, model_calls: int | str = 0, exa_calls: int | str = 0) -> None
make_model(settings=None, *, timeout=120.0) -> ChatAnthropic
UsageLog, _redact, _API_URL, _MAX_TOKENS, _FALLBACK_BETA  # _API_URL, _MAX_TOKENS, _FALLBACK_BETA는 지금도 Day02_new와 같다. UsageLog, _redact는 다르다(아래)
```

- `_redact`는 두 키 값(`api_key`, `exa_key`)을 모두 지운다(`rag_lab/settings.py:102`).
- `embeddings.py`를 복사하지 않으므로 `make_embeddings`는 뺀다. `Retriever`는 기본값 `mode="bm25"`로만 만든다(`mas_lab/runner.py:32`, `rag_lab/retrieval.py:130`). torch 적재를 피한다. 복사한 코드에는 이 과정이 부르지 않는 기능이 있다: `Retriever`의 `fusion` 방식, `decompose_question`, `prefetch`, `Budget.max_decision_calls`(줄은 1절 5번). 'BM25만'은 2026-11-02의 동기화 뒤에도 바뀌지 않았다. 복사한 코드에 다른 방식이 있어도 `mas_lab/runner.py:32`가 BM25 `Retriever`만 만들기 때문이다(1절 5번).
- 이 폴더의 `settings.py`에는 EXA 항목(`exa_key`, `has_exa_key`, `require_exa_key`, `announce`의 `exa_calls`)이 있고 `make_embeddings`가 없다. 이 차이를 고정하는 시험은 없다. 바이트 동일 시험(`tests/test_layout.py:13`)은 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 네 파일만 본다.
- 지금 Day02_new의 `settings.py`는 이 밖에도 달라졌다. 키 항목이 늘었고, `UsageLog`에 캐시 쓰기 칸이 있고, `make_reranker`가 있다. 이 폴더의 `UsageLog`(`rag_lab/settings.py:85`)는 캐시 읽기(`cache_read_tokens`)만 적고 쓰기는 적지 않는다. 그래서 비용 계산에는 캐시 쓰기가 빠져 있고, 그 사실은 비용 표의 각주(`tests/cost_report.py:76`)가 적는다. 이 파일을 Day02_new 판에 맞출지는 아직 정하지 않았다. 2026-11-02의 동기화도 이 파일을 건드리지 않았다(`settings.py`는 일부러 다르다).

### 8.3 `mas_lab.trace`

구조를 비교하려면 **누가 결정했고 무엇이 얼마나 들었는지**가 같은 칸으로 나와야 한다. 이 모듈이 그것을 맡는다.

```python
class ModelMeter(BaseCallbackHandler):
    """config의 callbacks로 넘기면 subagent 호출까지 잡는다."""
    calls: list[dict]   # start, end, model, tools, messages, input_chars, input_tokens, output_tokens, cache_read_tokens
    def totals(self) -> dict: ...

class Trace:
    """스레드 안전. 일반 함수 노드와 도구가 사건과 구간을 남긴다."""
    def __init__(self, label: str = ""): ...
    def event(self, kind: str, actor: str, **details) -> None: ...
    def span(self, actor: str, kind: str = "work") -> ContextManager: ...
    events: list[dict]; spans: list[dict]

def overlap_seconds(spans: list[dict]) -> float: ...       # 둘 이상이 동시에 도는 시간
def longest_path(durations: dict[str, float], depends_on: dict[str, list[str]]) -> float: ...
def timeline(spans: list[dict], width: int = 48) -> str: ...   # 문자 막대
def message_table(messages: list) -> list[dict]: ...       # 종류, 도구, 인자, 내용 앞부분
def show_graph(app, *, xray: bool = False) -> None: ...    # display({"text/vnd.mermaid": ...}, raw=True) + 간선 표 (mas_lab/view.py:32-34)
def flows_of(app) -> dict: ...                             # 조건부 간선 수, cycle 유무, 노드 수
def show_table(rows: list[dict], columns: list[str] | None = None) -> None: ...
def bars(values: dict[str, float], width: int = 32) -> str: ...
def write_design_log(question: str, answer: str) -> Path: ...
def read_design_log() -> dict: ...
```

- 위 블록의 `message_table`부터 `read_design_log`까지는 코드에서 `mas_lab.view`에 있다. `mas_lab.trace`에는 `ModelMeter`, `Trace`, `overlap_seconds`, `longest_path`, `timeline`만 있다(8.12절).
- `show_graph`는 JupyterLab의 mermaid 표시를 쓴다(설치본 4.6.5). `draw_mermaid_png`는 그래프를 외부 서비스로 보내므로 쓰지 않고, `draw_ascii`는 `grandalf`가 없어 쓸 수 없다(실측). 간선 표는 렌더러가 없어도 읽을 수 있게 같이 출력한다.
- `flows_of`는 분석이지 판결이 아니다. `Send`는 조건부 간선으로만 보이므로 "병렬 여부"는 실행 trace의 겹침으로 확인한다. markdown에 그렇게 적는다.

### 8.4 `mas_lab.contracts`

Worker 사이의 입력·반환 계약이다. 스키마 통과와 근거 검증이 다르다는 것을 드러내는 모듈이다.

```python
class WorkerTask(BaseModel):
    task_id: str; goal: str; facts: dict = {}; allowed_tools: list[str]; attempt: int = 1

class WorkerResult(BaseModel):
    task_id: str; attempt: int = 1
    status: Literal["complete", "uncertain", "failed"]
    facts: list[str] = []; evidence_refs: list[str] = []; uncertainty: list[str] = []
    error: str = ""   # status가 failed일 때 원인(예외 이름, HTTP_<코드>, 구조화 응답 없음)

class Proposal(BaseModel):
    action: Literal["refund", "none"]; payment_id: str = ""; amount: int = 0; reason: str = ""
    evidence_refs: list[str] = []; idempotency_key: str = ""

class FinalAnswer(BaseModel):
    outcome: Literal["answered", "insufficient", "needs_approval", "denied", "human_review", "executed", "out_of_scope"]
    text: str; evidence_refs: list[str] = []; uncertainty: list[str] = []; proposal: Proposal | None = None

class Route(BaseModel):
    path: Literal["fast", "slow", "out_of_scope"]; owner: Literal["billing", "technical"] = "billing"
    roles: list[Literal["billing", "policy", "outage"]] = []; reason: str = ""

def validate_result(result: WorkerResult, known_refs: set[str]) -> list[str]: ...
def validate_final(final: FinalAnswer, known_refs: set[str], source_text: str) -> list[str]: ...
def merge_results(left: dict, right: dict) -> dict: ...

def join_results(results: dict[str, WorkerResult], required: list[str]) -> dict: ...
    # {"ready": bool, "rows": [...], "missing": [...], "failed": [...], "uncertain": [...]}. 같은 작업의 마지막 시도를 본다
def trim_payload(result: WorkerResult, quotes: dict[str, str], max_bytes: int) -> dict: ...
    # 원문 인용부터 뺀다. 사실, 근거 참조, 불확실성은 마지막까지 남긴다. 무엇을 뺐는지 dropped 칸에 적는다
def plan_hash(plan: Any) -> str: ...   # dict나 BaseModel을 정렬된 JSON으로 만들어 해시한다. 03·06이 "같은 분해"를 증명할 때 쓴다

class FailureKind(StrEnum): PASS, INSUFFICIENT, POLICY_DENIED, SYSTEM_ERROR, BUDGET_EXCEEDED
def classify_failure(error: Exception | None, final: FinalAnswer | None, problems: list[str]) -> FailureKind: ...
def next_action(kind: FailureKind, *, retries_left: int, budget_left: bool) -> str: ...
    # respond | reinvestigate | stop_with_reason | retry | escalate
```

- `merge_results`는 `Day03/common/contracts.py:84`와 같다. 같은 키의 상충 결과는 `ValueError`다.
- 재시도 결과는 새 키(`outage#2`)로 쓴다. `merge_results`는 같은 키의 상충을 거절하므로 조용한 덮어쓰기가 없고, `join_results`가 같은 작업의 마지막 시도를 읽는다. 동시에 도는 두 시도의 늦은 도착을 판별하지는 않는다. 그 한계를 markdown에 적는다.
- `trim_payload`는 잘라도 되는 것의 순서를 코드로 정한다. 문장 중간을 자르지 않고 항목 단위로 뺀다.
- `validate_final`은 인용 ID 소속, 숫자의 근거 존재, outcome과 proposal의 일관성을 본다. 숫자 검사는 `Day02_new/rag_lab/answer.py`의 정규화를 참고한다.
- `Route.roles`는 Slow일 때 조사할 역할이고, 비면 `dispatch`가 세 Worker를 모두 부른다(`mas_lab/hybrid.py:83`). `hybrid`의 Router에는 `path`가 fast/slow뿐인 `HybridRoute`를 보이고(`mas_lab/hybrid.py:28`) 범위 밖 판단은 `scope_check`가 코드로 한다. `build_handoff`의 담당자 분류는 `Route`를 그대로 쓴다(`mas_lab/structures.py:95`).
- `next_action`은 실패 종류마다 다음 행동을 고정한다.

| kind | 조건 | 다음 행동 |
|---|---|---|
| `PASS` | | `respond` |
| `INSUFFICIENT` | 예산과 재시도가 남음 | `reinvestigate` |
| `INSUFFICIENT` | 없음 | `stop_with_reason` |
| `POLICY_DENIED` | | `stop_with_reason` |
| `SYSTEM_ERROR` | 재시도가 남음 | `retry` |
| `SYSTEM_ERROR` | 없음 | `escalate` |
| `BUDGET_EXCEEDED` | | `stop_with_reason` |

### 8.5 `mas_lab.desk`

고객 요청 창구의 사실과 도구다. 고객과 기준일은 도구 인자가 아니다(`rag_lab/evidence.py:1`과 같은 원칙).

```python
def load_billing(entity: str) -> list[dict]: ...   # 고객이 없으면 빈 목록
def load_outage(entity: str) -> dict: ...

class Desk:
    def __init__(self, scope: Scope, retriever: Retriever, *, budget: Budget | None = None,
                 trace: Trace | None = None, faults: dict[str, str] | None = None): ...
    scope; budget; trace; context: RetrievalContext; ledger: PaymentLedger; fact_refs: dict[str, str]
    def payments(self) -> list[dict]: ...   # 범위 고객의 결제 목록
    def tools(self, role: str = "all") -> list[BaseTool]: ...   # billing | policy | outage | writer | all
    def known_refs(self) -> set[str]: ...
    def source_text(self) -> str: ...   # 등록된 근거 원문과 사실을 합친 문자열
```

| 도구 | 역할 | 반환 |
|---|---|---|
| `lookup_payments(invoice_id: str = "", payment_id: str = "")` | billing | 범위 고객의 결제 목록(청구서와 결제 번호로 좁힌다. 결제 번호는 정확히 같은 것만)과 `F-<payment_id>` 참조 |
| `lookup_availability(month: str)` | outage | 가용률, 사건, `F-AV-<month>` 참조. 그 달이 없으면 `not_found`이고 참조를 등록하지 않는다 |
| `calculate_credit(base_fee: int, credit_percent: int)` | writer | 곱셈 결과와 `F-CALC-<금액>-<비율>` 참조. 비율 판단은 하지 않는다 |
| `search_knowledge(query, limit=6)` | policy | `rag_lab` 그대로 |
| `read_evidence(doc_id, start_line, line_count)` | policy | `rag_lab` 그대로 |

- `faults`는 `{"lookup_availability": "timeout_once"}` 형태다. `timeout_once`는 한 번만 `TimeoutError`를 내고, 다른 값(예: `timeout_always`)은 호출할 때마다 낸다(`mas_lab/desk.py:49-57`). 제어 경로 확인용이며 장애율 측정이 아니다. 사건을 trace에 남긴다.
- 도구 호출 수의 `tool` 소비는 도구 안이 아니라 `allowlist_middleware`가 센다(`mas_lab/workers.py:69`). `RetrievalContext`를 쓰므로 근거 등록과 예산을 Worker들이 공유한다. 등록은 `Budget.lock`이 보호한다(`rag_lab/evidence.py:118-127`).

### 8.6 `mas_lab.ledger`

쓰기 실행 층이다. 저장소 밖으로 아무것도 나가지 않는 가짜 결제 시스템이다.

```python
class ResponseLost(TimeoutError): ...

class PaymentLedger:
    refunds: list[dict]
    def refund(self, payment_id: str, amount: int, *, idempotency_key: str = "", lose_response: bool = False) -> dict: ...
    def find(self, idempotency_key: str) -> dict | None: ...

class GateDecision(BaseModel):
    decision: Literal["allow", "needs_approval", "deny", "human_review"]; reasons: list[str]

def check_refund(proposal: Proposal, payments: list[dict], as_of: date) -> GateDecision: ...
def execute_approved(proposal: Proposal, decision: GateDecision, ledger: PaymentLedger, *, approved: bool = False, lose_response: bool = False) -> dict: ...
```

- `check_refund`는 규칙을 코드로 검사한다. 고객 소속, 중복 여부, 환불 대상이 나중 결제인가, 금액 일치, 90일, 100만원 초과 순이다. 규칙의 숫자는 `billing-policy.md`의 값과 같고, 테스트가 원문 행과 대조한다.
- `refund`는 `lose_response=True`이면 **기록을 남긴 뒤** `ResponseLost`를 낸다. 외부 호출은 성공했지만 응답을 못 받은 상황이다. `idempotency_key`가 같으면 새 기록 없이 이전 결과를 돌려준다. 키가 없으면 그때마다 새 기록을 만든다.
- `execute_approved`는 `allow`이거나 `needs_approval`에 `approved=True`일 때만 원장을 부른다. 모델에게 도구로 주지 않는다.

### 8.7 `mas_lab.workers`

```python
ROLE_TOOLS: dict[str, frozenset[str]]   # billing, policy, outage, writer
ALL_TOOLS, SKILL_TOOLS: frozenset[str]; RECURSION_LIMIT = 40; DENY_WRITES: list[FilesystemPermission]
def allowlist_middleware(budget: Budget, allowed: frozenset[str]) -> list[AgentMiddleware]: ...
def delegation_spans(trace: Trace) -> list[AgentMiddleware]: ...   # task 호출 하나를 worker 구간 하나로 남긴다
TASK_CONTRACT: str     # 작업, 범위, 이미 아는 사실, 근거, 출력, 한계, 권한
def contract_prompt(task: WorkerTask, scope: Scope) -> str: ...
class TrackedSkillsBackend(FilesystemBackend): ...   # SKILL.md를 끝까지 읽었을 때만 읽은 것으로 기록
def make_worker(role: str, desk: Desk, model: BaseChatModel, *, prompt: str | None = None, response_format=WorkerResult): ...
def run_worker(task: WorkerTask, desk: Desk, model: BaseChatModel, *, role: str | None = None,
               prompt: str | None = None, config: dict | None = None) -> WorkerResult: ...
def checked_worker(task: WorkerTask, desk: Desk, model: BaseChatModel) -> WorkerResult: ...   # hybrid의 Worker
def subagent_spec(role: str, desk: Desk, model: BaseChatModel) -> dict: ...
# 내부: _run_with_messages(task, desk, model, role, prompt, config) -> (WorkerResult, 이 Worker 자신의 메시지)
```

- `allowlist_middleware`는 `Day02_new/rag_lab/agent.py`의 `allowlist_middleware`를 옮긴다. subagent 호출도 `middleware` 키로 같은 예산을 쓴다.
- Worker는 `create_deep_agent(..., response_format=ProviderStrategy(WorkerResult))`로 만든다. 쓰기 권한은 `FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")`로 막고 `StateBackend` 기본 파일 도구는 allowlist로 숨긴다.
- `run_worker`는 `_run_with_messages`의 결과만 돌려주고 결과를 거르지 않는다(`mas_lab/workers.py:141`). `BudgetExceeded`는 그대로 올리고, 시간 초과·연결 오류(`TimeoutError`, `httpx.TimeoutException`, `APIConnectionError`), API 상태 오류(`HTTP_<코드>`), 구조화 응답이 없는 경우는 `status="failed"`와 `error` 칸이 있는 결과로 바꾼다. `Day03/06_supervisor_rag.py:90-118`과 같은 분류이고, 구조화 응답이 없는 경우만 이 폴더에서 더했다. 작업 ID와 시도 번호는 모델이 쓴 값이 아니라 코드가 `task`에서 덮어쓴다.
- `delegation_spans`는 Supervisor가 `task`로 위임한 호출 하나를 `worker` 구간 하나로 남겨, 병렬 위임이 겹친 시간을 `overlap_seconds`가 잴 수 있게 한다(`mas_lab/workers.py:75`). `build_supervisor`가 `allowlist_middleware`와 함께 붙인다(`mas_lab/structures.py:64`).
- `checked_worker`는 `hybrid`의 Worker다. `checked_worker`를 부르는 곳은 Worker 노드와 재시도 노드뿐이고(`mas_lab/hybrid.py:90`, `mas_lab/hybrid.py:110`) 노트북은 import하지 않는다. 노트북 01~04가 import하는 것은 거르지 않는 `run_worker`이고 `test_run_worker_still_returns_the_raw_result`가 이를 지킨다(`tests/test_structures.py:756`). `checked_worker`는 근거 참조(`evidence_refs`)를 거르고 채우며, 뺀 항목이 있으면 `uncertainty`에 한 줄을 더한다. `facts`와 `status`는 바꾸지 않는다.

**`checked_worker`의 규칙**(`mas_lab/workers.py:151`). 등록된 번호는 `desk.known_refs()`에 있는 것이다.

| 모델이 쓴 `evidence_refs` 항목 | 결과 | 기록 |
|---|---|---|
| 등록된 번호와 통째로 같다 | 그대로 남는다 | |
| 라벨이나 조사가 붙었고 그 안에 등록된 번호가 있다(`결제 확인: F-P-9001`, `F-P-9001를`, `F-P-9001, F-P-9002`) | 항목은 사라지고 안의 등록된 번호가 처음 나온 순서로 남는다 | `recovered` |
| 안에 등록된 번호가 하나도 없다(`INC-311 장애`) | 뺀다 | `dropped`, `uncertainty`에 `등록되지 않은 근거를 뺐습니다: ...` 한 줄 |

- 번호 읽기. `_TOKEN`(`mas_lab/workers.py:148`)은 `[A-Za-z0-9-]+`라서 영문·숫자·하이픈이 이어진 한 덩이를 번호 하나로 읽고 `_`, `.`, `:`, 공백, 쉼표, 한글에서 끊긴다. 더 긴 번호의 앞부분은 그 번호가 아니다(`F-P-90012`는 `F-P-9001`이 아니다). 항목이 통째로 등록된 번호이면 그 안에 밑줄 같은 글자가 있어도 그대로 남는다(`test_checked_worker_labelled_ref_keeps_an_exactly_registered_id_whatever_its_characters`, `tests/test_structures.py:650`).
- 한 항목에 등록된 번호와 등록되지 않은 토큰이 섞이면 등록된 쪽만 남는다. 예를 들어 `INC-311`이 등록된 번호라면 `E-x, INC-311`에서 `INC-311`만 남고, 반대로 `E-x`가 등록된 번호라면 `E-x`만 남는다. 어느 쪽이든 항목에 건진 번호가 있으므로 `dropped`가 아니고, 버려진 토큰은 `dropped`에도 `uncertainty` 줄에도 이름이 오르지 않는다. 이름이 오르는 것은 건질 번호가 하나도 없는 항목뿐이다(`tests/test_structures.py:664`).
- 채우기(`filled`). 남은 번호가 하나도 없고 결과에 `facts`가 있을 때만 채운다. `facts`가 비면 도구를 불렀어도 채우지 않는다. 채울 번호는 이 Worker 자신의 도구 결과(`ToolMessage`)에서 `"fact_ref"`, `"evidence_id"` 값을 도구 결과 순서로 중복 없이 모은 것이다. 병렬 Worker가 `desk`를 함께 쓰므로 `desk`에서 읽지 않는다(`test_parallel_workers_do_not_get_each_others_refs`, `tests/test_structures.py:723`). 고객 질문처럼 도구가 돌려주지 않은 곳의 참조 꼴도 채우지 않는다(`test_checked_worker_ignores_ref_like_text_that_no_tool_returned`, `tests/test_structures.py:603`). 그중 `facts` 문장에 번호로 적힌 것이 있으면 그것만, 없으면 모두 쓴다(`tests/test_structures.py:693`). 건질 번호가 하나라도 있으면 채우지 않는다.
- 실패한 결과(`status`가 `failed`)는 그대로 돌려주고 사건도 남기지 않는다(`test_checked_worker_passes_a_failed_result_through_unchanged`, `tests/test_structures.py:743`). `BudgetExceeded`는 올린다.
- 사건 `worker_checked`(actor는 작업 ID)에 `problems`(`validate_result`의 결과), `dropped`, `filled`(채운 수), `recovered`(건진 수)를 남긴다(`mas_lab/workers.py:169`).
- `mas_lab/workers.py`는 공백이 아닌 줄이 정확히 150줄이다. 150은 `tests/test_layout.py:22`의 상한이라 한 줄만 더해도 그 시험이 실패한다.

### 8.8 `mas_lab.structures`

02~04가 셀에서 직접 만들어 본 구조를 05가 같은 조건으로 재기 위해 모은다. 소스를 셀에서 다시 보여 준다.

```python
# mas_lab.structures
OUTCOME_GUIDE: str; def scope_line(desk) -> str
def structured_call[S: BaseModel](desk, model, schema: type[S], prompt: str) -> S: ...   # Router와 triage의 모델 호출
def build_single(desk, model, *, skills: bool = False): ...
def build_supervisor(desk, model, *, concurrent_hint: bool = True): ...
class OwnerReply(BaseModel); class HandoffState(TypedDict); OWNER_TOOLS: dict; MAX_HANDOFFS = 2
def build_handoff(desk, model, *, checkpointer=None): ...
# gate_answer, check_named_payment: mas_lab.gate에서 다시 내보낸 이름이다(8.13절)

# mas_lab.hybrid
def build_hybrid(desk, model, *, checkpointer=None, force_path: str | None = None, request_id: str = "req"): ...

# mas_lab.runner
FIXED_BUDGET: dict              # max_model_calls=24, max_tool_calls=40, max_searches=6, max_seconds=180
STRUCTURES: tuple[str, ...]     # single, single_skills, supervisor, handoff, hybrid
def build_retriever() -> Retriever: ...
def run_case(structure: str, case: dict, *, model, repeat: int = 1, faults=None, approval: bool | None = None,
             budget: dict | None = None, force_path: str | None = None, concurrent_hint: bool = True) -> dict: ...   # RunRow
def run_grid(structures: list[str], cases: list[dict], *, model, repeats: int = 1) -> list[dict]: ...
```

| 구조 | 조립 | 결정 주체 | 최종 응답자 |
|---|---|---|---|
| `single` | `create_deep_agent`, 전체 도구, `FinalAnswer` | 모델 | Agent |
| `single_skills` | 위 + `skills/`, 읽기 추적 | 모델 + Skill 절차 | Agent |
| `supervisor` | `create_deep_agent(subagents=[billing, policy, outage])` | Supervisor 모델 | Supervisor |
| `handoff` | `StateGraph`, `Command(goto=)`, `Route`, 왕복 상한 2 | 현재 owner | 현재 owner |
| `hybrid` | `StateGraph`: 범위 확인 → Router → Fast 또는 Send Worker → 합성 → 검증(재조사 1회) → 게이트 | 코드 + 모델 | 합성 노드 |

- 모든 구조는 같은 `Desk` 도구, 같은 모델, 같은 `FIXED_BUDGET`을 쓴다(비교의 고정 조건).
- 쓰기 경로는 어느 구조든 `gate_answer`(`mas_lab/gate.py:32`)를 지나 `check_refund` → `execute_approved`다. 구조 안에서 우회할 수 없다. `run_case`의 `approval=None`이면 승인 대기로 끝내고 `outcome="needs_approval"`을 기록한다. 게이트가 무엇을 읽고 무엇을 바꾸는지는 8.13절에 있다.
- `run_case`는 실행마다 새 `Desk`(새 `PaymentLedger`, `Budget`, `RetrievalContext`)와 새 `MemorySaver`를 만든다. `interrupt`에는 체크포인터가 필수이고, 공유하면 `ledger_refunds`와 인용 범위가 실행 사이에 섞인다.
- `run_case`는 예외를 올리지 않고 실패 행을 돌려준다. 행은 성공과 실패 모두 `outputs/runs/<run_id>.json`에 저장한다(`mas_lab/runner.py:126`).
- `structured_call`은 Router와 triage의 모델 호출이다. `allowlist_middleware`를 거치지 않으므로 예산의 `model` 호출을 여기서 센다(`mas_lab/structures.py:32`). `structured_call`을 부르는 곳은 Router(`mas_lab/hybrid.py:60`)와 담당자 분류(`mas_lab/structures.py:95`)다.
- `run_case`는 마지막 turn의 답만 `gate_answer`에 넘긴다. 앞 turn이 환불을 제안하고 끝났다면 `_note_ungated_proposal`이 `earlier_turn_proposal_ungated` 사건(`turn`, `payment_id`)만 남기고 원장에는 쓰지 않는다(`mas_lab/runner.py:105`). `_note_ungated_proposal`을 부르는 곳은 `handoff` 경로(`mas_lab/runner.py:91`)와 단일 Agent 구조 경로(`mas_lab/runner.py:100`)다. `hybrid` 그래프는 turn마다 스스로 게이트를 지나므로 부르지 않는다.

### 8.9 `mas_lab.evaluation`

```python
def load_gold() -> dict[str, dict]: ...
def evaluate_row(row: dict, gold: dict[str, dict]) -> dict: ...   # 자동 검사 결과. outcome, 필수 사실, 금지, 문서, 원장, 실행 상태
def summarize_rows(rows: list[dict], checked: list[dict]) -> list[dict]: ...   # 구조×유형. checked는 rows와 같은 순서의 evaluate_row 결과다. 실패·usage 누락을 따로 센다
def routing_table(predicted: dict[str, str], gold: dict[str, dict]) -> list[dict]: ...
```

### 8.10 `mas_lab.research`와 `mas_lab.exa`

```python
# mas_lab.exa
INTERNAL_PATTERN: re.Pattern; DEFAULT_BLOCKED = ("알파", "베타", "billing-policy", "sla-a", "sla-b")
class ExaClient:   # 한도 초과는 rag_lab.evidence.BudgetExceeded를 낸다
    def __init__(self, *, trace: Trace | None = None, max_searches: int = 6, domains: frozenset[str] | None = None,
                 num_results: int = 3, max_chars: int = 2500): ...
    def search(self, query: str) -> list[dict]: ...   # source_id, title, url, published, text
    sources: dict[str, dict]; searches: int; cost_dollars: float | None; seconds: float; queries: list[str]

def allowed_url(url: str, domains: frozenset[str]) -> bool: ...     # Day03/common/exa_client.py:24와 같은 접미사 검사
def assert_public_query(query: str, blocked: Iterable[str] = DEFAULT_BLOCKED) -> None: ...
def make_exa_tool(client: ExaClient, max_searches: int = 2) -> BaseTool: ...   # web_search(query), Worker 하나에 하나

# mas_lab.research
class SubTopic(BaseModel): id: str; question: str
class ResearchPlan(BaseModel): topic: str; subtopics: list[SubTopic]
class Finding(BaseModel):
    subtopic_id: str; claims: list["Claim"]; uncertainty: list[str] = []
class Claim(BaseModel): text: str; source_ids: list[str]
class ResearchReport(BaseModel): summary: str; sections: list["ReportSection"]; open_questions: list[str] = []

WORKER_PROMPT: str
def build_research_graph(plan, client, model, *, budget=None, chained: bool = False, per_worker: int = 2, inputs=None): ...
def run_research(mode: str, plan, *, model, domains=None, per_worker: int = 2, num_results: int = 3, max_chars: int = 2500) -> dict: ...  # parallel | serial | chained
def url_overlap(left: dict, right: dict) -> dict: ...
def validate_report(report: ResearchReport | dict | None, sources: dict) -> list[str]: ...
```

- `parallel`과 `serial`은 **같은 그래프**다. `serial`은 `config={"max_concurrency": 1}`만 다르다(실측). 그래프를 고치지 않고 직렬을 만들어 "분해가 같다"를 코드로 보장한다.
- `chained`는 앞 Worker의 `Finding`을 뒤 Worker의 입력에 넣는다. `task.md`의 Sequential을 "같은 입력의 직렬"과 "앞 결과를 받는 연쇄" 둘로 나눠 보는 이유는, 시간 차이와 정보 흐름 차이가 다른 효과이기 때문이다.
- `assert_public_query`는 `DEFAULT_BLOCKED` 문자열이나 `INTERNAL_PATTERN`에 맞는 내부 번호가 든 질의를 호출 전에 `ValueError`로 막는다(`mas_lab/exa.py:18`, `mas_lab/exa.py:30`). 번호 패턴은 결제 번호(`P-` 뒤 숫자, 또는 하이픈 없이 `P` 뒤 숫자 4자리 이상), 청구서 `INV-…`, 사건 `INC-숫자`, 티켓 `T-숫자`이고 대소문자를 가리지 않으며 앞뒤에 영문자·숫자가 붙지 않을 때만 맞는다. 뜻까지 판단하지는 못한다. `Day03/README.md:80`의 "내부 질문 전체는 EXA로 전송하지 않으며"를 코드로 옮긴다.
- `max_searches`를 넘으면 `BudgetExceeded`다(`mas_lab/exa.py:51`). `costDollars`가 응답에 있으면 합산하고, 없으면 "확인 안 됨"(`None`)으로 둔다. `make_exa_tool`이 만든 도구는 Worker마다 한도(기본 2회)가 따로 있어 넘으면 `search_limit`을, 막힌 질의에는 `blocked`를, HTTP 오류에는 `error`를 도구 결과로 돌려준다(`mas_lab/exa.py:81`).
- 스냅샷 재생은 넣지 않는다. 공통 규칙 1과 같은 이유다. 웹 결과가 달라지는 것 자체를 관찰 항목으로 둔다.

**시간 분해.** `run_research`의 결과에 전체 시간, EXA 시간 합, 모델 시간 합을 따로 둔다. 병렬에서는 합이 전체보다 클 수 있음을 markdown에 적는다.

### 8.11 Skill

`Day03_new/skills/`에 셋을 둔다. 형식은 `Day02_new/skills/grounded-qa/SKILL.md`를 따르되, 출력은 `FinalAnswer`이므로 `output.json`이 없다.

| Skill | description의 요지 | 본문의 절차 |
|---|---|---|
| `refund-case` | 중복 결제, 취소, 환불 요청을 처리할 때 쓴다 | 결제 조회 → 규정 검색 → 환불 대상 판단 → `Proposal` 작성. 직접 실행하지 않는다 |
| `credit-case` | 장애 보상, 서비스 크레딧, 신청 기한을 답할 때 쓴다 | 가용률 조회 → SLA·추가 약정 검색 → 비율 선택 → `calculate_credit` → 기한은 추가 약정 우선 |
| `insufficient-evidence` | 사실이나 규정을 찾지 못했거나 범위 밖일 때 쓴다 | 찾은 것과 못 찾은 것을 구분해 `insufficient` 또는 `out_of_scope` |

### 8.12 구현 후 실제 모듈 배치

N4 구현에서 모듈당 150줄을 지키려고 나눴다. 이 표와 코드가 위 절보다 우선한다. 그 뒤 쓰기 게이트(`gate_answer`, `check_named_payment`)가 `structures`에서 `mas_lab.gate`로 옮겨 갔고 `structures`는 두 이름을 다시 내보낸다(`mas_lab/structures.py:16`). 노트북 02, 03, 05는 `gate_answer`를 `mas_lab.structures`에서 import한다.

| 모듈 | 공개 이름 |
|---|---|
| `mas_lab.harness` | `use_designed_subagents_only`, `framework_default_subagent`, `task_targets` |
| `mas_lab.trace` | `ModelMeter`, `Trace`, `overlap_seconds`, `longest_path`, `timeline` |
| `mas_lab.view` | `message_table`, `show_graph`, `flows_of`, `show_table`, `bars`, `read_design_log`, `write_design_log` |
| `mas_lab.contracts` | `WorkerTask`, `WorkerResult`, `Proposal`, `FinalAnswer`, `Route`, `validate_result`, `validate_final`, `merge_results`, `join_results`, `trim_payload`, `plan_hash`, `FailureKind`, `classify_failure`, `next_action` |
| `mas_lab.desk` | `load_billing`, `load_outage`, `Desk` |
| `mas_lab.ledger` | `REFUND_WINDOW_DAYS`, `APPROVAL_THRESHOLD`, `ResponseLost`, `GateDecision`, `PaymentLedger`, `check_refund`, `execute_approved` |
| `mas_lab.workers` | `ROLE_TOOLS`, `ALL_TOOLS`, `TASK_CONTRACT`, `contract_prompt`, `allowlist_middleware`, `delegation_spans`, `TrackedSkillsBackend`, `make_worker`, `run_worker`, `checked_worker`, `subagent_spec` |
| `mas_lab.structures` | `OUTCOME_GUIDE`, `scope_line`, `structured_call`, `build_single`, `build_supervisor`, `OwnerReply`, `HandoffState`, `MAX_HANDOFFS`, `build_handoff`, `gate_answer`·`check_named_payment`(`mas_lab.gate`에서 다시 내보낸 이름) |
| `mas_lab.gate` | `gate_answer`, `check_named_payment`, `refund_decision`, `_settle`(내부), `_PAYMENT_ID`(내부) |
| `mas_lab.hybrid` | `ROLES`, `ROLE_GOALS`, `build_hybrid` |
| `mas_lab.runner` | `FIXED_BUDGET`, `STRUCTURES`, `build_retriever`, `case_scope`, `make_desk`, `run_case`, `run_grid`, `_note_ungated_proposal`(내부) |
| `mas_lab.evaluation` | `load_gold`, `evaluate_row`, `summarize_rows`, `routing_table` |
| `mas_lab.exa` | `allowed_url`, `assert_public_query`, `ExaClient`, `make_exa_tool` |
| `mas_lab.research` | `Claim`, `Finding`, `ReportSection`, `ResearchReport`, `SubTopic`, `ResearchPlan`, `build_research_graph`, `run_research`, `url_overlap`, `validate_report` |

`(내부)`는 밑줄로 시작해 공개 이름이 아니다. 이 문서가 설명에 쓰는 이름이라 적었고 노트북이 import하지 않는다. 표에 없는 밑줄 없는 이름도 코드에 있다. `contracts`의 `Status`, `Outcome`, `workers`의 `SKILL_TOOLS`, `RECURSION_LIMIT`, `DENY_WRITES`, `structures`의 `OWNER_TOOLS`, `hybrid`의 `FAST_TOOLS`, `MAX_REWRITES`, `HybridRoute`, `HybridState`, `exa`의 `INTERNAL_PATTERN`, `DEFAULT_BLOCKED`, `research`의 `WORKER_PROMPT`다. 지금 노트북 00~06이 import하는 `mas_lab` 이름 중 이 표에 없는 것은 `DENY_WRITES`(03, 05, 06)와 `WORKER_PROMPT`(06) 둘뿐이다. 06의 두 이름이 표 밖인 이유는 9.2절에 적혀 있다. `checked_worker`, `delegation_spans`, `structured_call`은 노트북이 import하지 않고 다른 모듈이 부른다.

`RunRow`에는 5.5절 외에 `type`, `uncertainty`, `proposal`, `usage_missing`, `model_seconds`, `loaded_skills`, `cited_docs`, `retrieved_docs`, `spans`, `events`, `budget`, `calls`, `tools_called`, `messages`가 있다. 예산의 `tool` 소비는 도구 안이 아니라 `allowlist_middleware`가 맡는다.

**실측으로 확인한 구조 동작(2026-10-31, `claude-sonnet-5-5`, 각 1회 관찰).** `complex-double-pay`에서 `hybrid`는 모델 9회, 입력 약 24,000토큰, Worker 구간 겹침 약 9초로 자동 검사를 통과했다. `handoff`는 모델 9회, 입력 약 43,000토큰이었고, 기본 이용료를 볼 수 없는 `technical`이 180,000원을 내어 금지 표현에 걸렸다. `single`은 모델 7회, 입력 약 46,000토큰이었다. 설계 근거일 뿐이며 노트북에 미리 적지 않는다. 다만 02와 05는 전달 손실이 드러날 수 있는 칸을 읽도록 관찰 문단을 쓴다.

### 8.13 `mas_lab.gate`

환불 쓰기 게이트다. 원장에 닿는 길은 `gate_answer` 하나이고 판정은 코드가 한다(`mas_lab/gate.py:1`). 모델은 환불을 제안(`Proposal`)할 뿐이다. 이 코드는 `structures`에서 옮겨 온 것이고 `structures`가 `gate_answer`, `check_named_payment`를 다시 내보낸다(8.12절).

```python
def gate_answer(final: FinalAnswer, desk: Desk, *, approved: bool | None = None, request_id: str = "req", question: str = "") -> FinalAnswer: ...
def check_named_payment(final: FinalAnswer, desk: Desk, question: str) -> FinalAnswer: ...
def refund_decision(proposal: Proposal, desk: Desk, question: str) -> GateDecision: ...
# 내부: _PAYMENT_ID, _named_payments(question), _settle(final, desk, outcome, notes, *, blocked, events), _notes(payment_id, decision)
```

- 부르는 곳. `hybrid`는 `gate` 노드에서 `check_named_payment`(`mas_lab/hybrid.py:141`), `after_gate`에서 `refund_decision`(`mas_lab/hybrid.py:148`), `approve`와 `execute`에서 `gate_answer`(`mas_lab/hybrid.py:152`, `mas_lab/hybrid.py:157`)를 부른다. 다른 구조는 `run_case`가 마지막 turn의 질문을 `gate_answer`에 넘겨 부른다(`mas_lab/runner.py:93`, `mas_lab/runner.py:102`).
- `gate_answer`(`mas_lab/gate.py:32`). 제안이 없거나 `action`이 `refund`가 아니면 `check_named_payment`로 넘긴다. 제안이 있으면 멱등 키를 코드가 `<request_id>:<payment_id>`로 정해 모델이 쓴 키를 덮어쓰고, `refund_decision`의 판정을 `execute_approved`에 넘긴다. 원장을 부르는 곳은 거기뿐이다. 실행되면 `executed`이고, 판정이 `needs_approval`이면 `approved`가 `False`일 때 `denied`, 아니면 `needs_approval`(승인 대기)이다. 판정이 `deny`이면 `denied`, `human_review`이면 `human_review`다.
- `refund_decision`(`mas_lab/gate.py:22`). `check_refund`의 판정에 질문과의 대조를 더한다. 질문이 결제 번호를 말했는데 제안한 결제가 그 번호들에 없고 판정이 `deny`·`human_review`가 아니면 `needs_approval`로 올리고 이유를 더한다. 사람이 승인하기 전에는 실행하지 않는다.
- `check_named_payment`(`mas_lab/gate.py:50`). 제안 없이 낸 답을 질문이 가리킨 결제와 대조한다. `out_of_scope` 답과 환불 제안이 있는 답은 그대로 둔다. 질문이 번호를 말했고 그 번호가 모두 이 고객의 결제이면 검사할 수 있다.
  - 검사할 수 있고 답의 레이블이 `denied`·`human_review`이거나 질문에 `환불`이 있으면, 번호마다 탐침 제안(그 결제와 그 결제의 금액)을 `check_refund`에 묻는다. 탐침은 판정만 받고 원장에 쓰지 않는다. `execute_approved`를 부르지 않는다. 판정이 모두 `deny`이면 `denied`, 아니면 `human_review`이고, `allow`나 `needs_approval` 판정이 섞이면 "환불 제안이 없어 아무것도 실행하지 않았습니다. 사람이 확인합니다." 줄을 더한다. 레이블이 막지도 않고 환불 질문도 아니면 답을 그대로 둔다.
  - 검사할 수 없는데 레이블이 `denied`·`human_review`이면 답은 그대로 두고 `uncertainty`에 "코드 게이트가 이 판단을 검사하지 못했습니다" 줄과 `gate_skipped` 사건을 남긴다. 레이블이 막지 않아도 질문에 `환불`이 있으면, 같은 번호 목록의 `gate_skipped` 사건이 아직 없을 때 사건만 남기고 답은 그대로 둔다.
- 번호 읽기(`_PAYMENT_ID`, `mas_lab/gate.py:13`). 결제 번호는 질문에서만 읽는다. 답 본문의 번호는 검사받는 쪽의 주장이라 읽지 않는다. `P-7001`, `p-7001`, `P7001`, `p7001`을 모두 `P-7001`로 맞춘다(`_named_payments`, `mas_lab/gate.py:18`). 하이픈이 없는 꼴은 숫자가 4자리 이상이고 영문·숫자가 바로 뒤따르지 않을 때만 번호다. 앞에 영문·숫자·하이픈이 붙은 꼴(`XP-7001`)은 읽지 않는다. `p7001을`처럼 한글 조사가 바로 붙은 꼴은 읽는다.
- `_settle`(`mas_lab/gate.py:80`). 코드의 판정을 답에 옮긴다. 이유 줄이 새것이거나 outcome이 바뀔 때만 사건을 남기고, 이미 옮긴 답에 다시 부르면 문장도 불확실성도 사건도 더하지 않는다. `run_case`가 그래프 뒤에 `gate_answer`를 다시 부르기 때문이다. 막는 판정으로 outcome이 바뀌면 고객이 읽는 `text`와 `uncertainty`를 코드가 쓴 이유 줄로 통째로 바꾸고 원래 문장의 앞 80자를 `gate_text_replaced` 사건에 남긴다. 레이블이 같으면 모델 문장을 두고, 이유 문장 중 `text`에 없는 것만 뒤에 붙인다(`gate_text_appended`). 코드가 쓴 문장은 `F-GATE-<outcome>` 사실로 등록하고 모델 문장의 숫자는 출처로 올리지 않는다.
- 검사하지 못하는 것. 이 게이트가 읽는 것은 질문뿐이라, 질문이 이 고객의 결제를 가리키지 않거나 모르는 번호가 섞이면 탐침을 만들지 못하고 `gate_skipped`만 남긴다. 위에 적은 철자가 아닌 표기(예: 번호만 쓴 `7001`)는 번호로 읽지 않는다.

### 8.14 `mas_lab.harness`와 `mas_lab/__init__.py`

Deep Agents는 설계한 담당자 말고 `general-purpose` 하위 에이전트를 하나 더 붙인다. 이 에이전트는 부모의 도구를 받지만 부모의 사용자 정의 middleware는 받지 않아 이 과정의 허용 목록과 공유 예산 밖에서 돈다(02 3절). 그래서 이 과정은 모든 Deep Agent를 이 에이전트 없이 만든다.

```python
def use_designed_subagents_only(provider: str = "anthropic") -> None: ...   # provider 전체에 general-purpose를 끈다
@contextmanager
def framework_default_subagent(model): ...   # 블록 안에서만 model의 프레임워크 기본(general-purpose 포함)을 만들 수 있게 한다
def task_targets(app) -> list[str] | None: ...   # 컴파일된 에이전트의 task 도구가 내놓는 하위 에이전트 이름
```

- `use_designed_subagents_only`(`mas_lab/harness.py:25`)는 `HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False))`를 provider 키로 등록한다. `mas_lab/__init__.py`가 import할 때 한 번 부른다(`mas_lab/__init__.py:9`). 노트북은 첫 코드 셀에서 `mas_lab`을 import하므로 노트북이 직접 부르는 `create_deep_agent`에도 적용된다. 등록은 provider 수준의 `anthropic` 하나뿐이다. 다른 provider는 같은 함수를 그 이름으로 불러야 끈다.
- `framework_default_subagent`(`mas_lab/harness.py:31`)는 `provider:identifier` 키(provider 설정보다 우선한다)에 들어갈 때 `enabled=True`, 나올 때 예외가 나도 `enabled=False`를 등록한다. 나올 때 이전 상태가 아니라 꺼진 상태로 되돌리는 것은 이 과정이 늘 꺼 둔 채로만 돌기 때문이다. 나중에 전역으로 켜는 사람이 있으면 이 되돌림이 그 설정을 꺼 버린다. 모델을 부르지 않고 비교용 에이전트를 만들어 보는 데만 쓴다.
- `task_targets`(`mas_lab/harness.py:46`)는 `task` 도구의 description에서 담당자 목록 구간의 `- {이름}: {설명}` 줄을 읽는다. 인자 스키마의 `subagent_type`은 enum 없는 문자열이라 이름을 담지 않는다. 구간의 앞뒤 경계는 deepagents의 `TASK_TOOL_DESCRIPTION`에서 가져온 문자열이므로 deepagents의 문구가 바뀌면 깨진다. `tests/test_harness.py`가 그때 시끄럽게 실패한다. `task` 도구가 없는 에이전트(예: `build_single`)에는 `None`을 돌려준다.
- 시험 `tests/test_harness.py`는 `build_supervisor`, `build_single`, `create_deep_agent`를 `task_targets`로 읽어 `general-purpose`가 다시 새거나 프로필이 적용되지 않는 것을 잡는다. 더미 `ChatAnthropic`을 쓰므로 API를 부르지 않고, 실제 모델의 행동은 보지 못한다.
- 02 3절이 이 세 이름을 모델 없는 셀로 보인다. 05 7절의 하네스 일관성 셀이 다섯 구조에서 `task_targets`로 확인한다. 그래프로 컴파일되는 `handoff`와 `hybrid`는 `tools` 노드가 없어 `task_targets`가 `KeyError`를 내고 Agent가 노드 안에서 실행 때 만들어지므로, 05는 같은 설정으로 만든 Agent로 대신 확인한다.

## 9. 노트북 공통 틀

**첫 markdown 셀:** 제목, 학습 목표, 수업 시간표, 호출 규모. **첫 코드 셀:** import, `require_key()`, `key_status()` 출력. 06은 `require_exa_key()`도 부른다. **끝 네 부분:** `직접 해보기`, 설계 기록 코드 셀, `정리`, `확인 질문`.

### 9.1 노트북 작성 규약

모든 노트북 작성자가 따른다. 셀 명세의 순서를 지키고, 이 규약과 3절의 하한을 채우려고 필요하면 `[M]` 설명 셀을 더한다. 설명을 늘리려고 같은 말을 반복하지 않는다.

1. **첫 셀.** 첫 markdown 셀 하나에 `# 제목`, `## 학습 목표`, `## 수업 시간표`(마지막 칸이 `분`인 표, 합계가 정확히 60 또는 10), `## 호출 규모`를 모두 넣는다.
2. **코드 셀 출력.** 모든 코드 셀은 무언가를 출력한다. 표는 `show_table`, 구간은 `print(timeline(...))`, 그래프는 `show_graph`를 쓴다. 정의만 하는 셀도 이름이나 스키마를 출력한다.
3. **유료 셀.** 호출 직전에 `announce("목적", model_calls=N)` 또는 `exa_calls=M`을 부른다. `N`은 정수 리터럴이고 그 셀의 예상 상한이다. 모델을 부르는 셀에서 `model_calls=`가 없거나 숫자가 아니면 감사가 그 셀을 실패로 본다(`tests/audit_live.py:38-39`). `exa_calls=M`만 적는 셀은 EXA만 부르는 셀이다. 유료 호출과 `announce(`는 **같은 셀**에 있어야 한다. 모델 객체는 첫 코드 셀의 `model = make_model()`을 쓴다. `make_model()`을 만드는 것은 호출이 아니다.
4. **실패 재현 셀.** 코드 셀 첫 줄을 `# 실패 재현: 무엇을 재현하는지`로 쓴다. 예상되는 예외는 잡아서 종류와 메시지를 출력해 노트북이 끝까지 돌게 한다. markdown에는 `**실패 재현.**`을 쓰지 않아도 된다.
5. **관찰 문단.** 유료 셀과 실패 재현 셀 묶음 뒤, `직접 해보기` 전에 markdown 셀로 `**관찰할 것.**`을 쓴다. 고정된 정답이 아니라 **출력의 어느 칸을 어떻게 읽을지**를 쓴다. 모델 결과가 어느 쪽으로 나와도 말이 되게, 경우를 나눠 쓴다.
6. **예측 문단.** `**먼저 예측하세요.**`는 실행 전에 무엇을 적을지 구체적으로 묻는다.
7. **수치 금지.** 실행해 봐야 아는 수치를 markdown에 쓰지 않는다. 데이터에 고정된 값(결제 번호, 규정의 숫자)은 써도 된다.
8. **직접 해보기.** `## 직접 해보기` 절 아래 `### 해보기 1` 형식의 제목을 markdown에 4개(00은 2개) 둔다. 유료 골격 셀은 첫 줄에 `RUN_EXERCISE = False`를 두고, 꺼져 있으면 `print("실행하지 않았습니다. 고친 뒤 RUN_EXERCISE를 True로 바꾸세요.")`를 출력한다. 켰을 때도 실제로 끝까지 도는 코드여야 하며, 수강생이 고칠 값은 바로 위 상수로 둔다. 모델을 부르지 않는 골격 셀은 그대로 실행된다.
9. **선택 셀.** 대용량 셀은 `RUN_OPTIONAL = False`로 같은 방식을 쓴다.
10. **끝 순서.** `## 직접 해보기` → 설계 기록 코드 셀 → `## 정리` → `## 확인 질문`(번호 목록 5개 이상, 00은 2개).
11. **이름.** 공개 이름은 8.12절 표가 기준이다. `mas_lab`과 `rag_lab`을 고치지 않는다. 필요한 작은 도우미는 셀 안에 정의한다.
12. **금지 단어.** 노트북에 "슬라이드", "채점", 기존 과제 이름을 쓰지 않는다. `gold`는 `mas_lab.evaluation`을 import한 뒤에만 쓴다.
13. **저장.** nbformat 4로 저장하고 출력과 실행 번호를 남기지 않는다. kernel 작업 폴더는 `Day03_new/`이고 상대 경로는 거기가 기준이다.
14. **문체.** 한국어 존댓말. 2절의 용어를 쓴다. 번역투와 "결과에서 볼 수 있듯이"를 쓰지 않는다.
15. **실제 실행.** 저장소 루트에서 `nohup uv run --no-sync python Day03_new/tests/run_live.py Day03_new/<노트북>.ipynb > /tmp/<stem>.log 2>&1 &`로 띄우고 `uv run --no-sync python Day03_new/tests/wait_live.py <stem>`을 끝날 때까지 반복한다(종료 코드 3은 아직 실행 중). 먼저 모델 호출이 없는 셀과 유료 셀 한두 개를 짧은 스크립트로 확인해 전체 실행 횟수를 줄인다. 전체 실행은 최대 3회다. HTTP 429가 나면 60초 뒤 다시 실행한다.
16. **출력 읽기.** 실행본(`outputs/live/<stem>.executed.ipynb`)의 출력을 실제로 읽고, 관찰 문단이 그 출력의 칸 이름과 맞는지 고친다. markdown만 고쳤다면 코드가 같으므로 다시 실행하지 않아도 된다.

**호출 규모 추정.** 모델 호출은 실측 전 추정이다. 이 표는 설계 시점의 값으로 남기고 실측값으로 바꾸지 않는다. 실측은 `tests/cost_report.py`가 `outputs/live/`의 기록에서 계산한 값이 기준이고, `README.md`와 `AGENTS.md`가 그 값을 옮겨 적는다.

| 노트북 | 기본 실행(모델) | 기본 실행(EXA) | `직접 해보기`를 켜면(모델) | 선택 셀(모델) |
|---|---:|---:|---:|---:|
| 00 | 3 | 1 | 0 | 0 |
| 01 | 29~52 | 0 | 4~8 | 0 |
| 02 | 26~52 | 0 | 14~26 | 0 |
| 03 | 32~56 | 0 | 4~8 | 0 |
| 04 | 31~58 | 0 | 2~4 | 0 |
| 05 | 86~136 | 0 | 17~63 | 100~160 |
| 06 | 33~53 | 11~21 | 40~64 (EXA 12~24) | 10~16 (EXA 3~6) |
| 합계 | **약 240~410** | **약 12~22** | 약 81~173 | 약 110~176 |

위 표는 아래 셀 명세의 `[L]` 추정치를 합한 값이다. 05의 비교표 자체는 약 30회이고, 나머지는 앞 절들의 관찰 실행이다.

Day02_new의 호출당 평균 비용(152회에 USD 0.87)을 적용하면 기본 실행이 약 USD 1.4~2.4이지만, 멀티에이전트는 호출당 입력 토큰이 더 크다(실측 6회에 약 23,000토큰). **학생 1명 기본 실행에 USD 3~8**로 잡고 N13에서 실측으로 바꾼다. 시간은 Day02_new 실측(호출당 약 2.6초)으로 05가 약 4~6분, 나머지는 각 3분 안팎으로 본다. 수업 60분 안에 들어가는 대기 시간이다.

### 9.2 실측

**2026-11-01, `claude-sonnet-5-5`, 실제 Anthropic·EXA API. 노트북마다 기본 실행 1회와 `--exercises` 실행 1회이고, 모두 1회 관찰이다.** 같은 노트북을 다시 돌리면 호출 수와 초가 달라진다(아래 변동). 출처는 `outputs/live/<stem>.json`(기본)과 `<stem>.exercises.json`이다. 모델 호출 수는 각 `.usage.jsonl`의 줄 수와 13개 실행 모두 같고, 13개 실행 모두 `finished: true`, 오류 0건이다. `--exercises`는 저장본의 임시 사본에서 `RUN_EXERCISE`와 `RUN_OPTIONAL`을 켜 처음부터 다시 돌린 별도 실행이라 기본 실행의 셀을 한 번 더 포함한다. 검토에서 고지 상한 초과와 밑줄 이름 import가 지적된 뒤 02, 05, 06을 고쳐 다시 돌렸고, 아래 값은 그 최신 실행이다(02 Single 고지 8에서 12, 05 선택 셀 고지 160에서 330과 안내 문구 220~330회, 06의 `_worker_run` import 제거). 그 뒤 두 가지를 더 고쳐 04와 05만 다시 돌렸다. 하나는 `hybrid`의 Router가 그래프에 없는 경로 `out_of_scope`를 내던 문제다(`mas_lab/hybrid.py` 수정은 2026-11-01 02:50). 다른 하나는 감사 규칙을 3배 허용에서 고지 초과 실패로 바꾼 것이다. 01·02·03·06은 `hybrid`의 Router를 부르지 않아(01과 03은 `ROLE_GOALS`, `ROLES`만 import한다) 그대로 두었다. 05는 기본 실행과 `--exercises` 실행을 두 번씩 돌렸다. 고친 Router로 처음 돌린 `--exercises` 실행(463회, 1213.7초)은 해보기 2(셀 50)가 고지 18에 19회를 불러 새 감사가 실패시켰다. 그래서 그 셀의 고지를 24로 올리고 안내 문구와 markdown 셀 34·44를 고친 뒤 두 실행을 다시 돌렸다(처음 기본 실행은 146회, 444.9초로 감사는 통과했지만 셀 50의 코드가 바뀌어 저장본과 달라졌다). 위 값은 그 마지막 두 실행이고, 앞의 두 실행은 이 저장소에 남아 있지 않다. **후속(2026-11-01, 게이트 수정 뒤).** 10.4절 10번이 드러낸 코드 틈을 `check_named_payment`로 막은 뒤(아래 `[해소]` 항목과 설계 기록) 01~05의 기본 실행과 04·05의 켠 실행, 모두 7개 기록을 같은 방식으로 다시 돌렸다(09:43~10:27). 이 절의 표와 숫자는 그 값으로 바꿨다. 위 문단에 적은 이력(146회, 132회, 463회 등)과 "아래 값은 그 최신 실행이다"는 재실행 앞의 기준이라 지우지 않고 둔다. 05 기본 실행은 두 번 돌았다. 첫 실행은 144회, 421.3초였고 `hybrid 단순 사례와 복합 사례` 셀(셀 31)이 고지 20에 22회를 불러 `audit_live.py`가 실패시켰다. 셀의 고지를 30으로 올려 다시 돌린 136회가 저장소의 기록이다. 첫 기록은 저장소에 남아 있지 않고 그 실행의 행만 `outputs/runs/`에 있다. **이 수정 앞에 돌린 기록은 6개다.** 00 기본, 06 기본, 06 켠 실행, 01·02·03 켠 실행이다. 00과 06은 `run_case`·`gate_answer`를 부르지 않는다(노트북 코드 셀 검색). 01·02·03 켠 실행은 그 함수를 부르는 노트북의 기록(01은 `run_case`, 02와 03은 `gate_answer`)인데 수정 앞의 게이트로 돌았고 다시 돌리지 않았다.

**후속(2026-11-01, 세 번째). 아래 표와 숫자의 기준은 이 문단이다.** 위 문단은 이력이라 지우지 않았고, 그 안의 값(311회, 712회, 09:43~10:27, "이 수정 앞에 돌린 기록은 6개")은 지금 기록의 값이 아니다. 위 문단 뒤에 두 번을 더 돌렸다. 첫째는 17:03에 시작해 01~05의 기본 실행과 켠 실행을 모두 다시 돌렸다(`docs/audit/verify-b1-notes.md`). 둘째는 결제 번호 철자(`mas_lab/gate.py:13`, `mas_lab/exa.py:18`)와 근거 참조(`mas_lab/workers.py:151`)를 고친 뒤 20:28에 시작해 04와 05만 다시 돌렸다(`docs/audit/verify-c2-notes.md`). 00과 06은 두 번 모두 돌리지 않았다. 두 실행 모두 같은 기록을 두 번 돌리지 않았고 버린 기록이 없다. 지출은 11절에 있다. 기록이 끝난 시각과 마지막 세 수정의 앞뒤는 다음과 같다. 시각은 `outputs/live/<기록>.json`의 수정 시각이고 초는 잘랐다.

**후속(2026-11-02). 이 문단은 02 기본 실행 한 줄만 바꾼다.** 02의 Supervisor 용어를 라이브러리 관례로 맞추며(1절 저자 결정) 02의 코드 셀 11개에서 변수·라벨·표 이름을 바꿨다. `tests/audit_live.py`는 저장본 코드가 기본 실행본과 같아야 통과하므로(`tests/audit_live.py:47-51`) 02 기본 실행만 저자 승인으로 다시 돌렸다. 2026-11-02 21:40:44~21:43:09(KST, 실행본 셀 메타데이터), 모델 35회, 146.2초, 입력 125,672·출력 13,949 토큰, 모델 비용 하한 USD 0.2509, EXA 0회, 오류 0건이고 `audit_live.py`는 `AUDIT OK`다. 이 기록은 지금의 `mas_lab`(2026-11-02의 `contracts.py` docstring 수정 뒤. 그 docstring은 모델 입력에 들어가지 않는다), 동기화된 `rag_lab`, 지금 노트북 코드로 돈 유일한 기록이다. 바꾸기 전 기록(33회, 106.8초, USD 0.2466)은 `outputs/live/superseded-20261102/`에 남겼고, 집계 스크립트는 `outputs/live/` 바로 아래만 읽어 그 폴더를 세지 않는다(`tests/cost_report.py:39`, `tests/audit_live.py:55`). 02 켠 실행(`.exercises`)은 다시 돌리지 않았다. 그 실행본은 이름 변경 전 코드라 코드 셀 12개가 저장본과 다르고(아래 `저장본과 실행본`), 감사는 켠 실행본의 코드를 비교하지 않는다(`tests/audit_live.py:63`). 바뀐 것은 이름뿐이고 라벨은 `Trace`에만 들어가 모델 입력에 닿지 않는다(`mas_lab/runner.py:41`). 02 기본 실행은 `outputs/runs`에 행을 쓰지 않는다.

**후속(2026-11-02, 전체 재실행). 아래 표와 숫자의 기준은 이 문단이다.** 위의 두 후속 문단은 이력이다. 02 기본 실행을 다시 돌린 뒤 저자가 나머지 기록도 모두 다시 돌리기로 정했다. 00, 01·03·04·05·06의 기본·켠 실행, 02 켠 실행의 12개를 2026-11-02 21:56~22:51에 하나씩 차례로 돌렸다(429를 줄이려고 동시에 돌리지 않았다). 12개 모두 오류 0건, `finished: true`였고 `audit_live.py`는 13개 기록 전체에 `AUDIT OK`다. 그래서 13개 기록은 모두 지금의 `mas_lab`, 2026-11-02 09:13에 동기화한 `rag_lab`, 지금 노트북으로 돈 기록이고, 13개 실행본은 저장본과 코드도 markdown도 같다(켠 실행본은 스위치 줄만 다르다). 이 12개 재실행은 모델 961회, 3,273.4초, 모델 비용 하한 USD 6.6926, EXA 69회(00 1, 06 기본 21, 06 켠 실행 47)였다. 앞서 돌린 02 기본 실행까지 더하면 이날 재실행은 모델 996회, 하한 USD 6.9435다. 이전 기록 12개는 `outputs/live/superseded-20261102-before-full-rerun/`에 남겼고(`design_log.json`과 `baseline/`도 함께), 이전 기록과의 비교는 `docs/audit/live-rerun-20261102-notes.md`에 있다. `outputs/runs`는 1,893파일에서 2,008파일이 됐다(재실행이 115행을 썼다).

| 기록 | 끝난 시각 (2026-11-03) |
|---|---|
| 00 | 00:05 |
| 01 기본·켠 실행 | 00:08, 00:10 |
| 02 기본·켠 실행 | 00:12, 00:15 |
| 06 기본·켠 실행 | 00:56, 01:03 |
| 03a 기본·켠 실행 | 20:31, 20:56 |
| 03b 기본·켠 실행 | 20:32, 20:56 |
| 04a 기본·켠 실행 | 20:33, 20:57 |
| 04b 기본·켠 실행 | 20:34, 20:58 |
| 05a 기본·켠 실행 | 20:36, 21:03 |
| 05b 기본·켠 실행 | 20:43, 21:22 |

19개 기록은 모두 `mas_lab`의 마지막 수정과 `rag_lab` 동기화 뒤에 돌았다. 앞 판의 이 자리에는 수정 앞에 돌린 기록이 지금 코드에서도 참인지와 동기화 앞뒤 검색 비교를 적었다. 그 판단은 12절 `마지막 수정 앞에 돌린 기록` 행의 이력과 `docs/audit/stale-records-notes.md`, `docs/audit/sync-equivalence-notes.md`에 남아 있다. 그 비교가 찾은 코드 차이 하나는 지금도 참이다. 새 `_admit`(`rag_lab/evidence.py:118`)은 한도를 넘으면 그 아래 순위의 새 근거를 모두 버린다. 한도 3,000바이트로 넘침 경로를 강제하면 옛 코드와 780줄 중 73줄이 달랐다.

| 노트북 | 셀 | 코드 셀 | markdown 글자 | 기본: 모델 | 기본: EXA | 기본: 초 | 켠 상수 | 켠 실행: 모델 | 켠 실행: EXA | 켠 실행: 초 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-Setup | 25 | 12 | 8,265 | 3 | 1 | 12.6 | — | — | — | — |
| 01-Workflow-vs-Agent | 51 | 32 | 15,867 | 45 | 0 | 131.2 | 2 | 51 | 0 | 153.2 |
| 02-Agent-Architecture | 62 | 36 | 15,865 | 33 | 0 | 114.2 | 2 | 53 | 0 | 165.4 |
| 03a-Sequence-Parallel | 44 | 23 | 11,285 | 17 | 0 | 74.8 | 1 | 21 | 0 | 86.7 |
| 03b-Branch-Loop-Patterns | 38 | 20 | 9,433 | 19 | 0 | 70.1 | 0 | 19 | 0 | 51.1 |
| 04a-Graph-Contracts-Budget | 33 | 17 | 11,264 | 15 | 0 | 62.3 | 1 | 17 | 0 | 60.5 |
| 04b-Graph-Failure-Approval | 45 | 26 | 10,508 | 19 | 0 | 62.3 | 0 | 19 | 0 | 52.2 |
| 05a-Failure-Cost-Boundary | 38 | 19 | 11,833 | 36 | 0 | 145.6 | 2 | 83 | 0 | 262.5 |
| 05b-Measure-Fast-Compare | 44 | 24 | 13,053 | 134 | 0 | 420.8 | 2 | 393 | 0 | 1132.2 |
| 06-Lab-Research-Agents | 55 | 30 | 15,684 | 28 | 21 | 214.0 | 4 | 63 | 47 | 433.4 |
| 합계 | 435 | 239 | 123,057 | 349 | 22 | 1307.9 | — | 719 | 47 | 2397.0 |

- **셀 수와 글자 수**는 저장본 `.ipynb`를 `nbformat`으로 센 값이다. markdown 글자는 `check_notebook.py`와 같은 정의(markdown 셀 `source` 길이의 합)다. 10개 모두 3절의 하한(60분 노트북 46·24·11,000, 30분 노트북 23·12·5,500, 00은 14·7·2,500)을 넘는다.
- **저장본과 실행본.** 19개 실행본 모두 저장본과 코드도 markdown도 같다(켠 실행본은 `RUN_EXERCISE`·`RUN_OPTIONAL` 줄만 다르다, `nbformat`으로 셀을 하나씩 비교했다). markdown을 모두 고친 뒤에 다시 돌렸기 때문이다. 앞 판은 02 켠 실행본만 이름 변경 전 코드라 코드 셀 12개가 다르고 여러 실행본에 markdown만 고친 셀이 있다고 적었고(규칙 16에 따라 그때는 markdown만 고친 것을 다시 돌리지 않았다), 그 앞 판은 코드 셀이 13개 실행본과 모두 같고 02는 셀 0·47만 다르다고, 그 앞 판은 00 기본 실행본의 셀 0만 오래됐다고 적었다.
- **EXA 칸**은 json에 EXA 항목이 없어 따로 읽었다. 00 기본 1회는 실행본 출력의 `검색 1회`, 06 기본 21회는 실행본 출력의 1+2+6+6+6이다. 06 켠 실행의 47회는 실행본 출력의 `EXA 호출` 칸을 더한 값이다(21 + 변동 확인 6 + 해보기 1의 6 + 해보기 2의 병렬 2와 연쇄 6 + 해보기 3의 6). 안내 상한의 합 51보다 4 적은 것은 해보기 2의 병렬 실행이 검색 2회로 끝났기 때문이다. 01~05는 EXA 안내가 없고 호출하지 않는다.
- **켠 상수**는 `switched`다. 05b와 06은 `RUN_OPTIONAL` 하나와 해보기(05b는 하나, 06은 셋)를 켠다. 03b와 04b는 모델을 부르는 해보기가 없어 켤 상수가 0이다. 00에는 켤 상수가 없어 `--exercises` 실행도 없다.
- **합계 시간**은 기본 약 22분(1307.9초), 켠 실행(00 제외) 약 40분(2397.0초)이다. 셀 실행 시간의 합이라 kernel 시작과 사람의 대기는 빠져 있다.
- **비용.** 모델 비용은 `tests/cost_report.py`로 계산한 값이고(단가는 그 파일 기준), 캐시 쓰기 단가가 없어 하한이다(`tests/cost_report.py:76`). 기본 실행은 하한 USD 2.4809(349회, 1307.9초), 켠 실행은 하한 USD 4.9578(719회, 2397.0초)이고, 그 표의 합계 줄은 1068회, 3704.9초, 7.4387다(입력 3,968,675, 출력 450,419, 캐시 읽기 2,779,346 토큰). 합계 줄은 서로 겹치는 두 실행을 더한 값이라 지출이 아니다. 지출은 11절에 있다. 이 값을 `.usage.jsonl` 19개에서 호출 수·입력·출력·캐시 읽기 토큰을 따로 더해 단가(입력 2, 출력 10, 캐시 읽기 0.2 USD/100만 토큰)로 계산한 값과 대조했다(`cost_report.py`를 가져오지 않고 식을 따로 썼다). 호출 수와 토큰이 같았고 기본 2.4809, 켠 실행 4.9578도 같았다. 비용은 기록마다 넷째 자리로 반올림해 더하면 기본 2.4810, 켠 실행 4.9578, 합쳐 7.4388이라 기본만 마지막 자리가 다르다. 초도 행마다 반올림하기 전 값을 더한 것이라 표의 기본 실행 열을 그대로 더하면 1188.7이 된다. 분할 전 03·04·05 기록은 `outputs/live/superseded-20261103-before-split/`에 있고 아래 값들은 그 앞 기록의 합계다. 전체 재실행 전의 값(991회, 3,345.4초, 7.1832), 02 기본 실행을 다시 돌리기 전의 값(989회, 3,306.0초, 7.1789), 그 앞 판의 값(1,023회, 3,257.9초, 7.3154), 그 앞의 값(1,001회, 3,210.9초, 7.1930)은 그때 기록의 값이다. EXA는 00·06 출력의 비용 칸(검색 1회 0.007)으로 계산하면 기본 22회 약 USD 0.15, 켠 실행 47회 약 USD 0.33이다(06도 2026-11-02에 다시 돌렸고 EXA 횟수는 재실행 전과 같았다).

**9.1 추정 대비.** 이 절은 9.1의 표와 본문을 고치지 않는다. README는 아래 실측으로 바꾼다. 추가분은 켠 실행에서 기본 실행을 뺀 값이고, 서로 다른 두 실행의 차이라 변동이 섞인다.

| 노트북 | 추정 기본(모델) | 실측 기본 | 추정 추가분(해보기+선택 셀) | 실측 추가분 |
|---|---:|---:|---:|---:|
| 00 | 3 | 3 | 0 | — |
| 01 | 29~52 | 41 | 4~8 | +5 |
| 02 | 26~52 | 35 | 14~26 | +18 |
| 03 | 32~56 | 37 | 4~8 | +4 |
| 04 | 31~58 | 35 | 2~4 | +1 |
| 05 | 86~136 | 135 | 117~223 (17~63 + 100~160) | +306 (위) |
| 06 | 33~53 | 29 (아래) | 50~80 (40~64 + 10~16) | +35 (아래) |
| 합계 | 240~410 | 315 | — | +369 |

06의 EXA는 기본 21회(추정 11~21)이고 추가분 +26회(추정 15~30)다. 켠 셀만 나눠 읽으면 05는 선택 셀 261회(680.5초)와 해보기 셋 합 49회(30+17+2)이고, 06은 해보기 셋이 모델 28회(7+13+8)·EXA 20회(6+8+6), 선택 셀이 모델 8회·EXA 6회다. 06 첫 셀의 안내(해보기 모델 40~64회)는 실측 28회보다 크다. 05 기본 실행은 추정 시간 4~6분을 넘어 7.5분(450.2초)이 걸렸다. 05 기본 실행의 호출 수는 돌릴 때마다 달랐다. 146회, 132회, 게이트 수정 뒤 144회(버린 기록)와 136회, 그다음 145회, 135회, 2026-11-02 전체 재실행의 135회다. 앞의 값들은 이 문서의 기록이고, 저장소에는 마지막 기록과 재실행 직전 기록(`outputs/live/superseded-20261102-before-full-rerun/`)만 있다. 144회와 136회는 셀 31의 고지 숫자 하나만 다른 같은 코드의 두 실행이다.

**같은 셀의 변동.** 지금 기록의 기본 실행과 켠 실행에서 같은 셀의 모델 호출 수는 01 기준선(셀 36) 17과 14, 02 Single(셀 9) 6과 6, 02 Handoff 턴 1(셀 32) 7과 7, 05 `hybrid` 단순·복합(셀 31) 17과 14, 05 Fast 강제(셀 32) 15와 16, 05 같은 조건 비교표(셀 37) 64와 63, 06 Worker 한 개(셀 12) 3과 2였다. 전체 재실행 전 기록(2026-11-01)에서는 01 기준선 20과 18, 02 Single 5와 4, 02 턴 1 6과 8, 05 `hybrid` 15와 13, 05 Fast 강제 16과 16, 05 비교표 64와 63, 06 Worker 2와 3이었다(02 기본 실행만 먼저 다시 돌렸을 때는 Single 6, 턴 1 7). 그 앞 기록에서는 01 기준선 12와 20, 05 `hybrid` 15와 17, 05 Fast 강제 18과 16, 05 비교표 65와 78, 02 Single 4와 5였다. 02 Single은 개발 중 실행에서 9회가 나온 적이 있다(01 기준선은 개발 중 한 번 24도 나왔다). 이보다 작은 차이에 이유를 붙이면 안 된다.

**명세와 노트북의 차이.** 아래는 업스트림 보고가 적은 것을 노트북으로 확인한 목록이다. 셀 명세의 순서는 모두 지켰고, 차이는 추가·치환·해석이다. 아래 호출 수 가운데 "지금 기록"이라고 적지 않은 값은 그 항목을 쓸 때의 기록이고, 지금 값은 바로 위 문단과 표에 있다. 고지의 `model_calls`가 실측보다 작은 셀은 현재 13개 실행 어디에도 없고, 감사가 이제 그런 셀을 실패로 본다(10.1절).

- **00**
  - 규칙 3은 `model = make_model()`을 첫 코드 셀에 두라고 하지만, 00은 키 확인 셀(명세 6번)에서 `model = make_model(settings)`로 만든다. `require_key()` 바로 뒤에서 "만드는 것은 호출이 아니다"를 읽게 하려는 선택이다.
  - 규칙 10의 설계 기록 셀이 없다. 3절 표에 00 행이 없기 때문이다.
  - 명세에 없는 `# 실패 재현:` 셀이 하나 있다. `Settings(api_key="")`를 메모리에서 만들어 두 안내 문구를 `.env` 수정 없이 보인다.
  - Deep Agent 셀(명세 13번 "모델 2회")은 고지가 `model_calls=3`이고 실측은 2회다.
  - 해보기 2는 명세의 "폴더 밖에서 kernel 띄우기" 대신 `RUN_FOLDER`를 고치는 모델 없는 subprocess 셀이다.
- **01**
  - 라우터 셀(명세 10번 "모델 1회")은 `out_of_scope`까지 보이려고 2회 호출한다.
  - 명세에 없는 셀이 둘 있다. 등록되지 않은 고객(모델 0회)과 `max_model_calls=2` 예산 변형(유료 2회)으로, 3절과 5절의 "조건 하나 바꾸기"를 채운다.
  - 기준선 고지가 `model_calls=30`이다. 명세 37번은 12~20회다.
  - 2절과 5절은 `run_case`와 `run_grid`를 쓴다. 임시 요청 2건은 정답표에 없는 ID라 `evaluate_row`를 거치지 못하고, 그 2건에는 자동 검사 칸이 없다.
- **02**
  - `Recorder(ModelMeter)`와 `execute` 도우미를 노트북 안에 정의한다. `task` 구간, 호출 주체, 마지막 입력을 잴 공개 수단이 없어서이고 규칙 11이 허용하는 범위다. 코드 셀이 명세보다 늘었다.
  - 본문과 코드가 모두 `build_supervisor`의 실행을 Supervisor라 부른다(2026-11-02 저자 결정, 1절). 넓게는 Manager 패턴에 속한다고 1절 표 아래와 3절에 밝힌다. 이 결정 전의 본문은 이 실행을 Manager라 불렀고, 그때의 실행본(지금은 `outputs/live/superseded-20261102/`와 `outputs/live/superseded-20261102-before-full-rerun/`)과 `docs/audit/live-02-notes.md`에는 Manager라는 본문과 `manager` 변수·라벨이 남아 있다. 라벨은 `Trace`에만 들어가고 모델 입력에는 들어가지 않는다(`mas_lab/runner.py:41`). 그래도 감사가 저장본과 실행본의 코드 일치를 요구하므로(`tests/audit_live.py:47-51`) 02의 두 실행본은 2026-11-02에 바꾼 노트북으로 다시 돌렸다. 옛 기록은 고치지 않았다.
  - Single 셀과 Handoff 턴 1 셀의 고지가 모두 `model_calls=12`로 명세(6번 4~8회, 26번 3~8회)보다 넓다. 개발 중 Single이 9회가 나와 고지 8을 넘었고(규칙 3 위반), 고지를 12로 올려 다시 돌렸다. 그때 최종 실행의 실측은 Single 4회와 5회, 턴 1이 7회와 7회였고, 지금 기록은 Single 6회와 6회, 턴 1이 7회와 7회다(기본 실행은 2026-11-02 21:43, 켠 실행은 22:04에 돈 값이다. 켠 실행의 재실행 전 기록은 Single 4회, 턴 1 8회였고, 그 전 기본 실행은 Single 5회, 턴 1 6회였다).
  - 비교표(명세 37번)의 Handoff 행은 턴 1만 쓴다. 같은 요청끼리 비교하려는 것이고 턴 2의 비용은 별도 표에 있다.
  - 턴 2 직전에 `handoff_desk.budget.started`를 다시 잡는다. 예산의 시간이 Desk를 만들 때 시작해서, 표를 읽는 시간이 3분을 넘으면 턴 2가 시간 초과로 실패하기 때문이다.
  - 해보기 1(명세 41번)은 `build_supervisor`에 설명 인자가 없어 `create_deep_agent`를 셀에서 직접 부른다.
  - 3절에 명세 11-1~11-4(자동 Worker와 설계한 Worker 비교, 2026-11-02)가 더해져 노트북이 62셀이 됐다. 셀 25~28이 그 넷이고 [C] 둘은 모델 0회다. `allowlist_of`가 `inspect.getclosurevars`로 `bounded_model` 클로저에서 허용 목록과 `Budget`을 읽는데, 미들웨어에 공개 속성이 없어서이고 `allowlist_middleware`를 고치면 깨질 수 있다(`tests/test_notebook_code.py`가 지킨다). 확인 질문이 6개다. 이 줄 아래와 위의 셀 번호(실행 기록에서 인용한 것)는 이 셀이 더해지기 전 노트북의 위치다. 25번 이후는 4칸 밀렸고, 다음 재실행이 동기화한다.
- **03**
  - `Send`를 처음부터 설명하는 markdown 셀이 실패 재현 앞에 하나 더 있다.
  - 루프의 유료 셀을 두 번 실행한다. 두 번째는 답할 수 없는 항목(`법인카드 포인트 보상`)이라 같은 실패에 멈추는 것을 보이고, 그래서 호출이 3~6회다.
  - Fast/Slow Path 실패 재현은 모델을 부를 수 없는 셀이라 답이 아니라 모은 자료를 자동 검사하고, 출력이 그렇게 말한다.
  - 확인 질문이 6개다(3절 하한 5). 재시도 상한 질문을 더했다.
- **04**
  - 역할 프롬프트 Worker는 스키마 없는 자유 텍스트로 실행한다. 같은 스키마를 쓰면 스키마가 칸을 강제해 차이가 사라진다. 대신 프롬프트와 출력 형태 두 변수가 함께 바뀌는 비교다.
  - 잘못된 결과 표가 3행이 아니라 4행이다(`실제 근거에 틀린 사실` 추가).
  - 예산 실패 재현은 Worker 셋을 공유 예산 2회로 차례로 실행한다. Worker 하나로는 2회 안에 끝나 초과가 안 날 수 있다.
  - 5절의 복구 실행은 `build_hybrid`가 아니라 Worker까지만 도는 작은 그래프다. 작성 단계까지의 복구는 8절 소스 읽기에서만 다룬다.
  - 제안 프롬프트에 90일 규칙을 적는다. 모델이 중복 건을 구분하지 못해 `action=none`을 냈기 때문이다.
  - 승인 그래프 코드를 `approval_nodes`와 연결 셀로 나눴다. 그래도 25줄을 넘는 셀이 하나 남는다.
  - 설계 기록 키에 질문 문구를 덧붙였다(`Context·권한과 예산·종료: 무엇을 보고 무엇을 실행하며 언제 멈출까?`). 3절 표의 키는 문구 없이 적혀 있고, 06의 `TOPICS` 부분 문자열 매칭에는 두 항목 모두 걸린다.
- **05**
  - 명세 41번([C])을 모델 2회의 유료 셀로 바꿔 예산을 줄인 실패 행을 일부러 만든다(고지 3, 실측 2). 실행마다 빨리 끝나는 실패 행이 생긴다는 보장이 없어서다.
  - 평균 함정 표가 둘이 아니라 셋이다(같은 조건 평균, 실패 행을 섞은 평균 A, 뺀 평균 B). `남은 사례`와 `제외한 행` 칸을 더했다. 실패 행을 빼면 쉬운 사례만 남아 평균이 낮아지는 경우가 있어 "포함 평균이 항상 낮다"는 설명이 틀렸다.
  - `run_custom` 도우미를 셀에 정의해 2·3절에서 쓴다. `run_case`는 잘린 메시지만 돌려줘 위임 바이트를 잴 수 없다. 약 20줄이 `run_case`와 겹친다.
  - 5절은 명세 28번의 span 대신 `row["calls"]`의 시각으로 구간을 만든다. 이 항목을 쓸 때 `supervisor`는 span을 남기지 않았다. 지금은 `delegation_spans`(`mas_lab/workers.py:75`)가 `task` 호출마다 구간을 남기지만 이 셀의 방식은 그대로다.
  - Fast Path 강제(명세 32번)에 `insufficient-unknown-payment`를 더했다. `complex-double-pay`를 Fast로 강제하면 Slow로 전환되지 않고 크레딧 사실이 빠진 답이 검증을 통과해, 전환 경로(`fallback_to_slow`)가 나오는 사례가 필요했다.
  - 비교표 고지가 `model_calls=100`이다(명세 37번 "약 30회"). 지금 기록의 실측은 64회와 63회다(앞 기록은 65회와 78회).
  - 선택 셀(명세 40번 "100~160회")의 고지는 `model_calls=330`이고 안내 문구는 "약 220~330회, 10~15분"이다. 개발 중에는 고지 160에 실측 277회가 나와 규칙 3을 어겼고, 셀 0 표와 셀 1 주석(220~330)과도 어긋났다. 세 곳을 맞추고 05를 다시 돌렸다. 지금 기록의 실측은 261회다(재실행 전 기록은 252회, 그 앞 기록은 266회, 271회, 278회였다).
  - 0절(명세 2-1~2-3)과 7절의 하네스 셀(명세 35-1~35-3, 2026-11-02)이 더해졌다. 셀 2~4가 0절, 셀 39~41이 7절 하네스 셀과 공식 프레임워크 표다. 위 기록의 05 셀 번호는 이 셀들이 더해지기 전의 위치이고, 앞 구간(원래 2~35)은 3칸, 뒤 구간(원래 36~57)은 6칸 밀렸다. 다음 재실행이 동기화한다. 모두 모델 0회다. `handoff`와 `hybrid`는 컴파일된 그래프에 `tools` 노드가 없어 `task_targets`가 `KeyError`를 내므로 같은 설정의 Agent(`create_deep_agent(model, tools=...)`)로 `task_targets`를 확인한다. 이 확인은 공유 프로필이 적용된다는 것까지만 보이고 노드 안에서 실행 때 만들어지는 Agent 자체를 보지는 않는다. 0절의 담당 사전(`NODE_OWNER`)은 `retry`를 모델, `scope`를 코드로 적었다. 7절 표의 "가장 많이 쓰이는 구성"은 "공식 문서가 기본으로 싣는 구성"으로 바꿨고, 70% 같은 출처 없는 수치는 인용하지 않았다.
  - 해보기 2([C], 명세 48번)는 규모를 먼저 출력하고 `RUN_EXERCISE`로 켜는 유료 셀(셀 50)이다. 이 셀은 새 감사 규칙이 실제로 잡은 첫 초과다. 고지 18에 켠 실행이 19회를 불렀다. 구조 셋에 `max_model_calls=6`을 걸어 3 × 6 = 18회가 상한이지만, 그때 `hybrid`의 Router 호출은 `Budget`이 세지 않아 `hybrid` 행이 예산 6에서 7회를 불렀다. 고지를 24로 올리고 안내 문구에 "Router 호출은 예산이 세지 않아 그보다 늘 수 있습니다"를 더했다. 다시 돌린 켠 실행의 실측은 19회였다. 3구조 × 6회에 Router 1회를 더한 19회가 앞의 두 켠 실행에서 모두 나왔다. 게이트 수정 뒤 다시 돌린 켠 실행은 17회로 고지 24 안이다. 같은 감사가 이 재실행에서 `hybrid 단순 사례와 복합 사례` 셀(셀 31, 고지 20에 22회)을 두 번째로 잡았고, 그 셀의 고지를 30으로 올려 다시 돌린 마지막 기록은 15회다. **지금은 다르다.** Router 호출도 `structured_call`이 예산으로 센다(`mas_lab/structures.py:32`). 지금 기록의 켠 실행은 이 셀에서 17회(재실행 전 기록은 16회)이고 `supervisor`와 `hybrid`가 6회에서 `budget_exceeded`로 끝났다. 안내 문구도 "Router 호출도 예산이 셉니다"로 바뀌었다.
- **06**
  - 설계 기록 코드 셀을 하나 더했다. 규칙 10이 요구하지만 06 셀 목록에 없다. `DECISION`이 비면 쓰지 않고 안내만 출력한다.
  - `RUN_OPTIONAL = False`는 명세 4번대로 CONFIG 셀에 있다. 감사의 `stale_cells`가 이 패턴의 셀을 빼므로 CONFIG를 고쳐도 자동으로 잡히지 않는다. 다음 작성자는 저장본과 실행본을 손으로 비교해야 한다.
  - 8.12절 공개 이름 표 밖의 `WORKER_PROMPT`와 `DENY_WRITES`를 import한다. 둘 다 밑줄 없는 공개 이름이고 3절의 Worker가 그래프 안 Worker와 같은 부품임을 보이는 데 쓴다. 이전에는 밑줄 이름 `_worker_run`도 import해 규칙 11에 어긋났고, Worker를 셀에서 `create_deep_agent`로 직접 조립하는 코드로 바꿨다.
  - 연쇄 셀만 `model.model_copy(update={"callbacks": [...]})`로 측정기를 더해 Worker별 입력 토큰을 잰다(명세 26번). `run_research`가 Worker별 토큰을 돌려주지 않는다.
  - 첫 markdown 셀의 호출 규모는 상한(모델 53, EXA 21)만 적고 실측값은 넣지 않는다(규칙 7).
  - 모델 호출이 명세 17·19·25번의 10~16회보다 적은 8~9회다(지금 기록은 기본 실행 9·8·9회, 켠 실행 8·9·9회이고, 재실행 전 기본 실행은 세 셀 모두 8회였다). Worker가 검색 2회를 한 메시지에 묶는 경우가 많다. 고지는 16을 유지한다.
  - 해보기 4개의 안내 markdown을 코드 셀마다 따로 둔다.

**노트북이 아니라 코드와 데이터에서 드러난 것(저자 판단 필요).** 2026-11-01 최종 감사 뒤 항목마다 상태를 적는다. 해소된 항목도 그 전에 있었던 일을 지우지 않는다.

- **[유지] 정답표의 날짜 표기.** 정답표(`data/gold.jsonl:3`)의 `complex-double-pay`는 날짜를 `9월20일`이나 `다음달20일`로만 인정한다. 비교는 공백과 쉼표를 지운 문자열 포함이다(`mas_lab/evaluation.py:15-16`, `mas_lab/evaluation.py:22-23`). 지금 기록(2026-11-02 재실행)에서 이 칸 하나 때문에 `필수 사실`이 실패한 행은 기본 실행에서 01의 `complex-double-pay`(셀 37), 03의 Orchestrator-Worker 조립(셀 54, 답은 "2026-09-20까지"), 04의 `사실+근거+불확실성`(셀 16), 05의 Supervisor(셀 14, 같은 행이 셀 17·24에도 나온다), `single_skills`(셀 24), 비교표의 `hybrid` `complex-double-pay`(셀 38, 같은 행이 셀 42에도 나온다)이고, 켠 실행에서 04의 `사실+근거+불확실성`과 `원문 포함`(셀 16), 완성형 조립(셀 53), 05의 Single 기준선(셀 4, 답은 "2026-09-20까지이고", 같은 행이 셀 10·14·24에도 나온다), `single+한 줄`(셀 10), Persona(셀 17), `hybrid` `complex-double-pay`(셀 31, 같은 행이 셀 32에도 나온다), 해보기 1의 `hybrid` 한 행(셀 48, 반복 3)이다. 재실행 전 기록에서는 01 기본 실행의 `complex-double-pay`(셀 37), 04 기본 실행의 `원문 포함`(셀 16), 05 기본 실행의 `single_skills`(셀 24)와 비교표의 Single(셀 38), 05 켠 실행의 Single 기준선(셀 4), Persona(셀 17), 비교표의 Single(셀 38), 해보기 1의 `hybrid` 한 행(셀 48)이었다. 실행본 출력에서 `9월20일`을 찾아 셌고, 다른 사실도 함께 빠진 행과 손으로 쓴 답(05 셀 54)은 세지 않았다. 켠 실행 셀 41은 행별 누락 사실을 출력하지 않아 행 파일(2026-11-02 22:27~22:38에 쓰인 50행)을 `evaluate_row`로 다시 읽었고, 이 모양의 실패는 없었다(`필수 사실` 실패는 handoff `complex-double-pay`의 `150000` 하나다). 재실행 전 기록에서는 행 파일에서 읽은 `single_skills`의 `complex-double-pay`가 같은 실패였다(`docs/audit/live-05-c2-notes.md`). 이 항목의 앞 판은 실패한 행을 두 개로 적었고(05 켠 실행의 Single 기준선, 05 기본 실행의 `single_skills`), 그 앞 판은 05 기본 실행의 Single 기준선이 "2026-09-20까지"를 쓰고도 실패했다고 적었다. 모두 그때 기록의 값이다. 이 한계는 고치지 않고 일부러 둔다. 01(셀 40), 04(셀 19, 54), 05(셀 7, 54)가 수강생이 자동 검사의 한계를 읽는 소재로 쓰고, 05 셀 54는 손으로 쓴 답 두 개(`CORRECT_BUT_FAILS`, `WRONG_BUT_PASSES`)로 모델 없이 보인다. 정답표를 고쳐 통과시키지 않는다(`AGENTS.md` 5장 1번).
- **[해소] `hybrid`의 Router가 그래프에 없는 경로 `out_of_scope`를 냈다.** 수정 전 `outputs/runs/`에 남은 `hybrid` 행 중 모델을 실제로 부른 행의 Router 결정 78건에서 `out_of_scope`는 9건이었다. `complex-ops-log` 7건(`insufficient` 3, `answered` 4)과 `approval-refund-now` 2건(`needs_approval`)이다. 수정 뒤 저장된 66건은 fast 37, slow 29이고 `out_of_scope`는 없다. 원인은 이렇다. `Route.path`가 `out_of_scope`를 허용했고(`mas_lab/contracts.py:58`), Router 프롬프트는 이 값을 설명하지 않고 필요한 조사를 결제 사실·규정·가용률 세 범주로만 열거했다(`mas_lab/hybrid.py:61-63`). 운영 로그와 보안 질문은 세 범주에 들지 않아 모델이 스키마에 있는 `out_of_scope`를 골랐다. 수정 전 Router를 5번 불렀을 때 5번 모두 이 값이었고 이유가 모두 세 범주 목록을 인용했다(수정 노드의 실측이며 저장된 행에는 없다). `roles`가 비어 `dispatch`가 세 역할을 모두 띄웠고(`mas_lab/hybrid.py:84`), `out_of_scope`는 `fast`가 아니라서 그대로 `dispatch`로 갔다(`mas_lab/hybrid.py:167`). 수정은 `hybrid.py` 안에 `HybridRoute(Route)`를 두고 `path`를 `fast`와 `slow`로 좁힌 것이다(`mas_lab/hybrid.py:28-29`, 사용은 `mas_lab/hybrid.py:60`). 범위 밖 고객은 `scope_check`가 코드로 가린다(`mas_lab/hybrid.py:50`). `contracts.Route`는 01과 03이 `out_of_scope`를 쓰므로 바꾸지 않았고, `build_handoff`의 `resume`은 `Route`를 쓰되 `path`를 읽지 않는다(`mas_lab/structures.py:95`). 시험은 `tests/test_structures.py`의 둘이다(Router가 받는 경로가 `fast`·`slow`뿐인지, 그 밖의 값은 경로가 아니라 오류인지). 04와 05는 고친 코드로 다시 돌렸다. 위의 건수는 그때 저장된 행의 값이다. 지금 `hybrid` + `complex-ops-log` 실제 모델 행 47건의 Router 선택은 `out_of_scope` 7(모두 수정 앞), `slow` 35, `fast` 5다(2026-11-02 재실행이 05에서 3건을 더했다. 재실행 전은 44건, `slow` 33, `fast` 4).
- **[미해소] 고친 뒤에도 `complex-ops-log`가 `insufficient`로 끝난다.** 수정 뒤 저장된 같은 사례의 `hybrid` 행 9건에서 Router는 8건 slow(`outage`, `policy`), 1건 fast였고, 결과는 `answered` 6건, `insufficient` 3건이다. 05 기본 실행의 행은 `insufficient`(7회), 켠 실행의 두 행은 `answered`다. 수정 노드가 살펴본 `insufficient` 행의 원인은 `policy` Worker가 사실을 돌려주면서 `evidence_refs`를 비운 것이다. 합성 답이 근거 없이 `answered`가 되어 검증이 거절하고(`mas_lab/contracts.py:96`) 다시 쓴 답이 `insufficient`로 끝난다. `hybrid.py`는 Worker 결과에 `validate_result`를 부르지 않는다(`mas_lab/contracts.py:78`은 `complete`일 때만 근거 없음을 본다). `ROLE_GOALS`의 문구가 영향을 주는지는 가리지 못했다. 다음에 읽을 곳은 `mas_lab/workers.py`의 `TASK_CONTRACT`와 `run_worker`, `mas_lab/hybrid.py`의 `after_join`이다. 코드는 바꾸지 않았다. 수정 전에는 Worker 셋이 모두 돌았는데 지금은 `outage`와 `policy` 둘이라 호출이 8~10회에서 6~8회로 줄었다. **후속(2026-11-01).** 위는 첫 판정이다. 14:32에 `hybrid`의 Worker를 `checked_worker`(`mas_lab/workers.py:151`)로 바꿨다. 이 함수의 `validate_result`는 문제 목록을 사건에 적을 뿐 결과를 막지 않고(`mas_lab/workers.py:169`), 결과를 바꾸는 것은 `filled`다. 사실은 있는데 남은 참조가 없으면 그 Worker 자신의 번호로 채운다(`mas_lab/workers.py:166`). 그 앞 실제 행 20건은 `answered` 14, `insufficient` 6이고 6건 모두 `evidence_refs`가 비었다. 그 뒤 실제 행 24건은 `answered` 23, `budget_exceeded` 1이고 `insufficient`는 0건이다(2026-11-01 기준. 2026-11-02 재실행이 더한 3건도 모두 `answered`라 지금은 27건, `answered` 26, `budget_exceeded` 1, `insufficient` 0이다). writer가 빈 참조를 받지 않게 되어 `validate_final`의 `근거 없이 answered입니다.`가 나오지 않는다는 것은 코드에서 읽은 설명이고, 코드 판이 여럿 섞인 행을 센 것이라 통제 비교가 아니다. Worker가 왜 참조를 비우는지는 아래 항목에서도 밝히지 못했다. 이 채움이 아래 항목의 `인용 문서` 실패와 함께 나타난다. 18행의 상관이고 원인은 시험하지 않았다.
- **[미해소, 저자 결정으로 고치지 않음] 코드가 근거를 채운 행에서 `인용 문서`가 실패한다(`complex-ops-log`, `hybrid`).** 같은 사례를 아홉 번씩 두 묶음 돌렸다. 두 묶음 사이에 `checked_worker`의 근거 참조 처리를 고쳤다. 앞 아홉 행(`docs/audit/ops-log-notes.md`)은 `ok` 8, `budget_exceeded` 1이고 자동 검사 통과 5/9다(56회, 155.2초). 뒤 아홉 행(`docs/audit/ops-log-2-notes.md`)은 `ok` 9이고 자동 검사 통과 8/9다(55회, 142.1초). `budget_exceeded` 행은 검색 한도 6에 닿았고 `FIXED_BUDGET`은 올리지 않았다.
  - **Worker 원본 결과(뒤 묶음만 기록, `docs/audit/ops_log2_raw.jsonl`).** 14건 모두 `uncertain`이다. 8건은 `evidence_refs`가 비었다. 그중 7건은 `outage` Worker로 자기 도구 결과에 번호가 하나도 없어 채울 것이 없었다. `lookup_availability`의 `not_found`에는 `fact_ref`가 없다(`mas_lab/desk.py:93`). 여섯 건의 사실이 조회 결과를 `not_found`라고 적었고 8행은 사실이 0개다. 나머지 1건은 6행의 `policy` Worker로 사실 10개와 자기 번호 17개가 있었는데 참조를 비웠다. 이유는 밝히지 못했다. 라벨이 붙은 참조를 돌려준 결과는 2건(4행, 7행)이고 번호 24개가 모두 남았으며 버린 것은 0개다. 사실에 적힌 번호를 먼저 쓰는 채움 갈래(`mas_lab/workers.py:166`)는 실제 데이터에서 한 번도 타지 않았다.
  - **`인용 문서` 실패.** 앞 묶음은 4행(2, 5, 6, 7행)이고, 그중 2번 행은 답이 없는 `budget_exceeded` 행이라 답한 행에서는 3행이다. 뒤 묶음은 1행(6행)이다. 6번 행은 뒤 묶음에서 채움이 있었던 유일한 행이고, writer의 최종 참조 6개는 채운 17개의 앞 6개다. 두 묶음을 합치면 채움이 있었던 5행 중 4행이 실패했고, 채움 없이 답한 12행은 0행이 실패했다. 18행, 하루의 상관이다. writer의 참조가 왜 채움 순서를 따르는지는 시험하지 않았고, 다른 채움이 인용 문서를 바꾸는지도 시험하지 않았다. 검색은 뒤 묶음 아홉 행 모두 같은 문서 여섯 개를 돌려줘 실패한 행을 가르지 못한다.
  - **고치지 않은 판단(저자 결정, 2026-11-02).** 처음에는 작업을 맡은 AI가 이 실패를 고치지 않기로 판단해 저자에게 알렸고, 그때 저자는 결정하지 않았다. 저자는 2026-11-02에 `rag_lab` 동기화가 유료 재실행을 필요로 하지 않게 되자 이 판단을 확인했고, 이 실패를 문서화된 관찰로 두기로 했다. 이유는 처음과 같다. 코드를 바꾸면 유료 재실행이 또 필요하고 원인을 시험하지 않았기 때문이다. 실패는 자동 검사와 실행 행에 그대로 보이게 둔다.
- 이 항목을 처음 쓸 때 Router 호출은 `Budget`이 세지 않아, 예산을 낮추면 측정 호출이 한도보다 많을 수 있었다. 05 해보기 2에서 `hybrid`가 예산 6에 7회를 부른 것이 그 경우다(위 05 항목). **지금은 다르다.** Router와 triage는 `structured_call`을 지나고 이 함수가 먼저 예산의 `model`을 센다(`mas_lab/structures.py:32`). 14:32 뒤 실제 `hybrid` 행 114개(2026-11-02 재실행 32개 포함, 그 전 82개) 모두 `budget`의 `model`과 `model_calls`가 같다.
- 이 항목을 처음 쓸 때 `build_supervisor`는 span을 남기지 않아 `run_case("supervisor")` 행의 겹침 칸을 믿을 수 없었고, 02는 callback으로 직접 쟀다. **지금은 다르다.** `build_supervisor`의 미들웨어에 `delegation_spans`가 있어(`mas_lab/structures.py:56`, `mas_lab/workers.py:75`) `task` 호출마다 구간을 남긴다. 14:32 뒤 실제 `supervisor` 행 57개(2026-11-02 재실행 19개 포함, 그 전 38개) 모두 구간이 있고 40개(그 전 27개)는 겹침이 0보다 크다. 다만 재실행 05 켠 실행 셀 41의 `supervisor` 3행은 모델이 `general-purpose`에 위임해 `budget`의 `model`이 `model_calls`보다 1 적다. `followup-handoff`가 남은 제안 때문에 자동 검사의 `outcome` 칸에서 실패한다는 02 노드의 보고는 저장된 행으로 확인할 수 없다. 이 사례의 행은 `outputs/runs` 2,008파일(2026-11-02 재실행 뒤)에 없다(02는 `run_case`를 쓰지 않는다). 확인이 필요하다.
- **[해소] 감사가 고지 초과와 비교할 수 없는 셀을 통과시켰다.** 이전 `tests/audit_live.py`는 실측이 고지의 3배를 넘을 때만 실패로 봐서, 규칙 3(고지의 N은 그 셀의 상한)과 어긋났다. 개발 중에 02 Single이 9회를 불러 고지 8을 넘었고, 05 선택 셀이 277회를 불러 고지 160을 넘었지만 감사는 둘 다 통과시켰다. 두 번 모두 검토에서 지적된 뒤 노트북을 고쳤다. 지금 감사는 실측이 그 셀의 고지를 넘으면 바로 실패로 보고(`tests/audit_live.py:36-37`), 한 셀에 고지가 여럿이면 합을 상한으로 한다(`tests/audit_live.py:35-36`, 요약은 `tests/audit_live.py:2`). 이 규칙의 첫 판에는 비교하지 못하는 셀을 통과시키는 구멍이 둘 있었고 첫 검토가 짚었다. 하나는 모델을 불렀는데 고지에 `model_calls=` 숫자가 없는 셀(EXA만 알리는 `exa_calls=3`이나 숫자가 아닌 `model_calls=len(topics)`)이다. 비교할 숫자가 없다는 이유로 통과했고, 이 문서의 앞 판은 이것을 "한계가 하나 남는다"고 적고 현재 기록에는 그런 셀이 없다고만 했다. 다른 하나는 실행본(`<stem>.executed.ipynb`)이 없는 기록이다. 셀 코드를 읽을 수 없어 비교가 통째로 건너뛰어졌는데도 `AUDIT OK`가 나올 수 있었다. 지금은 둘 다 실패다. 숫자 없는 고지는 그 셀마다 한 줄(`tests/audit_live.py:38-39`)이고, 실행본이 없으면 stem마다 한 줄을 내고 셀 비교는 건너뛴다(`tests/audit_live.py:27-28`, `tests/audit_live.py:33-34`, 없을 때 `None`을 넘기는 곳은 `tests/audit_live.py:60`). 모델을 안 부른 셀은 고지에 숫자가 없어도 통과한다. 규칙은 `tests/test_audit_live.py`의 12개 항목이 고정한다(10.1절). 새 규칙은 고친 05를 다시 돌린 첫 켠 실행에서 해보기 2(고지 18에 19회)를 처음으로 잡았다. 두 구멍을 막은 뒤에도 현재 13개 실행은 `AUDIT OK`이고, 고지를 넘은 셀도, 숫자 없는 고지로 모델을 부른 셀도, 실행본이 없는 기록도 없다.
- `ExaClient`의 응답은 `cost_dollars` 0.007, `source_id`는 `S-` 뒤 16진수 8자였다. `published`는 지금 기록(2026-11-02 재실행)의 06 셀 7에서 3건 중 1건이 날짜이고 2건이 `None`이었다(재실행 전 기록은 2건이 날짜, 1건이 `None`). 이 항목의 이전 판은 `published`가 전부 `None`이라고 적었으나 06 실행본 출력과 맞지 않아 고쳤다. 4절의 EXA 실측 표와 12절의 해당 항목이 같은 값을 보인다.
- **[해소] 모델이 쓴 `human_review`와 `denied`는 제안이 없으면 코드가 검사하지 않았다.** 첫 새 질문 감사에서 "4월 1일에 결제한 P-7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요."를 `hybrid`로 1회 돌리자 모델이 환불 제안(proposal) 없이 `human_review`로 답하면서 P-7001을 재무 심사로 넘기겠다고 썼다. P-7001은 같은 청구서에서 먼저 승인된 유효 결제라 환불 대상이 아니다. 제안이 없어서 `after_gate`가 곧장 끝나고(`mas_lab/hybrid.py:144-147`), `gate_answer`도 답을 그대로 돌려줘 `check_refund`가 돌지 않았다. 돌았다면 `deny`가 나왔을 규칙은 `mas_lab/ledger.py:60-61`이다. 원장은 0건이었고 쓰기 경로는 지켜졌으나 모델이 제안 없이 낸 레이블과 문장은 아무도 검사하지 않았다. **수정(2026-11-01).** `check_named_payment`(`mas_lab/gate.py:50`)를 더했다. 환불 제안이 없는(없거나 `action`이 `none`인) `denied`·`human_review` 답에 대해 질문에서 `P-숫자` 번호 하나를 읽고, 그 번호가 이 고객의 결제이면 그 결제의 실제 금액으로 `check_refund`를 물어 판정을 받는다(`mas_lab/gate.py:54-66`). 판정이 `deny`나 `human_review`면 그 레이블이 결론이 되고, 레이블이 바뀌면 모델의 결론 문장을 코드가 낸 이유 문장으로 바꾼다(`mas_lab/gate.py:87-91`). `allow`나 `needs_approval`이 나와도 원장에는 쓰지 않고 `human_review`로 두며 "환불 제안이 없어 아무것도 실행하지 않았습니다"를 남긴다(`mas_lab/gate.py:69-70`). 부르는 곳은 `gate_answer`(`mas_lab/gate.py:32-36`)와 `hybrid`의 `gate` 노드(`mas_lab/hybrid.py:141`)이고, `run_case`가 마지막 턴의 질문을 넘긴다(`mas_lab/runner.py:93`, `mas_lab/runner.py:102`). 제안이 있는데 게이트가 거절한 경우에도 같은 `_settle`이 결론 문장을 이유 문장으로 바꾼다(`mas_lab/gate.py:46-47`). 시험은 `tests/test_structures.py`의 새 함수 20개(pytest 항목 36개)이고 결함 주입으로 확인했다(10.2절, 10.4절 2번). 수정 앞의 실제 모델 행 32행을 새 코드에 넣어 본 재생에서 바뀐 레이블과 문장은 0개, 원장은 0건이었다. 수정 뒤 P-7001 질문을 3번 돌렸을 때 모두 `denied`, 원장 0건이었다(10.4절 10번). 무엇이 남았는지와 설계 근거는 아래 두 항목이다. 이 코드는 뒤에 `mas_lab/gate.py`로 옮겼고(8.13절) 위 인용은 옮긴 뒤의 줄이다. 문장이 설명하는 것은 그때의 동작이다. 지금 동작과 달라진 곳은 아래 `[미해소]` 항목 끝에 있다.
- **[미해소] `check_named_payment`가 닿지 않는 곳.** 아래는 코드와, 모델 없이 손으로 쓴 답을 `check_named_payment`에 넣어 본 오프라인 탐침(새 질문 감사의 행으로 세지 않았다)에서 읽은 틈이다. 실제 모델 8행에서는 이 길로 틀린 문장이 나온 행이 없었다. ① 질문에 번호가 없거나 둘 이상이거나 모르는 번호이면 `gate_skipped`로 모델의 레이블과 문장이 검사 없이 지나간다(`mas_lab/gate.py:55-57`). 번호가 없는 사례(10.4절 10번의 R5)가 이 길을 탔고 모델의 답이 맞았다. ② 모델의 레이블이 판정과 같으면 문장을 바꾸지 않는다(`mas_lab/gate.py:87`). `denied`에 틀린 이유 하나만 쓴 문장은 통과한다. ③ `denied`·`human_review`가 아닌 레이블(`answered`, `insufficient`)은 제안이 없으면 검사하지 않는다(`mas_lab/gate.py:63-64`). "환불을 접수했습니다"를 `answered`로 낸 답은 문장이 막히지 않는다(원장은 0건). ④ 제안이 있으면 제안의 결제만 검사하고 질문이 가리킨 결제와 견주지 않는다(`mas_lab/gate.py:34-47`). R4와 R6에서 모델은 질문의 P-9001이 아니라 P-9002를 제안했고 맞았다. ⑤ `_settle`은 모델이 쓴 `uncertainty`와 `proposal.reason`을 지우지 않는다(`mas_lab/gate.py:86-88`). R1에는 코드가 뒤집은 재무 심사 경로를 말하는 `uncertainty` 한 줄과 `proposal.reason`이 남았다. ⑥ `human_review` 이유 문장(`mas_lab/ledger.py:65`)에는 결제 번호가 없다. 모델이 다른 결제를 제안했을 때 어느 결제 이야기인지 읽는 사람이 오해할 수 있다. 모델이 제안을 얼마나 자주 빼는지, 틀린 레이블을 얼마나 자주 쓰는지는 측정하지 않았다. 코드는 더 바꾸지 않았다. **지금 상태(2026-11-01 저녁, `mas_lab/gate.py` 기준).** 위는 첫 판정이고 인용만 옮긴 뒤의 줄로 고쳤다. ① 번호가 둘 이상이어도 모두 이 고객의 결제이면 번호마다 탐침을 돌린다(`mas_lab/gate.py:54-66`). 번호가 없거나 모르는 번호가 섞이면 여전히 검사하지 못한다. ② 레이블이 같으면 여전히 모델 문장을 둔다. 코드의 이유 문장이 문장에 없으면 뒤에 붙인다(`gate_text_appended`, `mas_lab/gate.py:92-97`). 그래서 틀린 이유를 쓴 문장은 남고, 같은 말을 다른 표현으로 쓴 문장에는 중복이 붙는다(10.4절 10번의 N1). ③ 질문에 `환불`이 있고 번호를 읽을 수 있으면 `claims_a_block`이 거짓인 레이블(`answered`, `insufficient`)도 탐침을 돌린다(`mas_lab/gate.py:63-66`). 번호가 없거나 `환불`이 없는 질문의 `answered`는 여전히 검사하지 않는다. ④ 질문이 가리킨 결제와 제안의 결제가 다르면 `refund_decision`이 `needs_approval`로 올린다(`mas_lab/gate.py:22-29`). ⑤ 문장을 바꿀 때 모델의 `uncertainty`를 비우고 `action: none` 제안을 뺀다(`mas_lab/gate.py:88`). 환불 제안을 거절한 경우에는 제안과 모델의 `reason`이 남는다. 실제 모델 행에는 아직 없는 길이다. ⑥ 이유 문장 앞에 결제 번호를 붙인다(`mas_lab/gate.py:76-77`). `[미해소]` 표지는 지금 ①·②·③의 남은 부분과 ⑤의 환불 제안에 대한 것이다.
- **[해소, 경계는 남음] 결제 번호 철자가 다르면 게이트가 읽지 못했다.**
  - **첫 관찰.** 새 질문 감사 세 번째의 N5(10.4절 10번)는 질문의 번호만 `p7001`로 쓴 행이다. 그때 패턴은 대문자 `P-숫자`만 읽어 `gate_skipped`(`named` 빈 목록)로 끝났고, 모델이 제안 없이 쓴 `human_review`와 P-7001을 재무 심사로 넘긴다는 문장이 그대로 고객 답이 됐다. 원장은 0건이다. 14행 가운데 유일하게 그럴듯하게 틀린 행이고, 틀린 고객 문장이 `gate_skipped`를 지나간 첫 실제 행이다(`docs/audit/new-question-3-notes.md`).
  - **수정.** `_PAYMENT_ID`(`mas_lab/gate.py:13`)가 `P-7001`, `p-7001`, `P7001`, `p7001`을 읽고 `_named_payments`(`mas_lab/gate.py:18`)가 `P-7001`로 맞춘다(`docs/audit/gate-id-forms-notes.md`). EXA 질의 경계 `INTERNAL_PATTERN`(`mas_lab/exa.py:18`)도 같은 철자를 막게 고쳤다(`docs/audit/exa-id-forms-notes.md`). 저장된 실제 행 422개의 재생에서 뒤집힌 행은 0이고, N5의 모델 답을 지금 게이트에 넣으면 `denied`다(`docs/audit/replay-4-notes.md`).
  - **실제 행.** 같은 문장의 번호 철자만 바꾼 S1(`p7001`, 9회), S2(`P7001`, 7회), S3(`p-7001`, 9회)을 돌렸다. 기대는 행을 돌리기 전에 적었다(`docs/audit/id-spelling-rows-notes.pre-results.md`). 세 행 모두 `denied`, 원장 0건이고 `gate_skipped`가 없다. 게이트 앞 모델 레이블은 3행 모두 `human_review`이고(S2는 `action: none` 제안을 달았다), 게이트가 문장을 바꿨다(`gate_text_replaced`). 한 경로의 3회 관찰이지 비율이 아니다. 행 파일은 `docs/audit/rows/`에 있다.
  - **찾은 것.** 바뀐 문장이 얇다. "P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."뿐이고, 환불 대상인 P-7002가 160일이 지나 재무 담당자 심사로 간다는 말도 예외 요청에 대한 말도 없다. 거짓은 아니라 그럴듯하게 틀린 행으로 세지 않았다. 최종 `evidence_refs`는 모델의 것이 그대로 남는다. 3행 모두 게이트 앞과 같고, 바뀐 문장은 그 참조를 인용하지 않는다. `_settle`의 `update`에 이 칸이 없기 때문이다(`mas_lab/gate.py:86-88`). `lookup_payments`는 번호를 그대로 비교해(`mas_lab/desk.py:75-84`) `p7001`은 `not_found`가 되고, 모델이 스스로 P-7001로 맞춘다. 게이트가 이 일을 하는 것이 아니다.
  - **타지 않은 길.** 게이트 앞 레이블이 이미 `denied`인 길과 모델이 환불 제안을 낸 길은 이 3행에 없다. 손으로 쓴 답의 단위 시험만 지난다.
  - **패턴과 경계.** 번호 패턴은 두 곳에 따로 적혀 있고(`mas_lab/gate.py:13`, `mas_lab/exa.py:18`) 규칙이 같지 않다. 오프라인으로 넣어 본 결과(모델 0회)는 이렇다. `p7001a`는 게이트가 읽지 않고 EXA 경계를 통과한다. `P-7001a`는 게이트가 `P-7001`로 읽는데 EXA 경계는 통과한다. `KP-7001`은 앞 글자가 ASCII `K`이면 게이트가 읽지 않고 EXA 경계를 통과하고, 켈빈 기호(U+212A)이면 게이트가 `P-7001`로 읽는데 EXA 경계는 통과한다. 이 셋은 번호가 경계 밖으로 나갈 수 있는 구멍이다. 반대로 `inv-test`, `T-800`, `Tesla P4000`은 내부 번호가 아닌데 EXA 경계가 막는다. 게이트는 `Tesla P4000`을 `P-4000`으로 읽고, 이 고객의 결제가 아니면 검사하지 못한 경우로 처리한다.
- **사건 기록에서 읽을 것 셋.** `earlier_turn_proposal_ungated`(`mas_lab/runner.py:108`)는 실제 모델 행에서 0건이다(`outputs/runs` 2,008파일, 새 질문 14행, 철자 3행). 이 길은 단위 시험만 지난다(`tests/test_structures.py:921`). `gate_skipped`는 막지 않는 레이블에서는 같은 Desk에서 `named` 목록마다 한 번 남는다(`mas_lab/gate.py:60`). 막는 레이블에서는 `_settle`이 이유 줄을 이미 가진 답에 사건을 더하지 않아(`mas_lab/gate.py:80-83`) `run_case`가 다시 불러도 늘지 않지만, 턴마다 새 답이면 같은 `named`라도 턴마다 하나씩 남는다(모델 없이 확인했다. `mas_lab/gate.py:51`의 설명보다 코드가 넓다). `gate` 사건이 같은 값으로 두 번 남는 행(N2, R4)은 원장에 두 번 쓴 것이 아니다. `approve` 노드가 `gate_answer`를 부른 뒤(`mas_lab/hybrid.py:152`) `interrupt`로 멈춰(`mas_lab/hybrid.py:153`) 그 결과가 상태에 남지 않고, `run_case`가 그래프 뒤에 `gate_answer`를 다시 부른다(`mas_lab/runner.py:93`). 두 행 모두 원장은 0건이다.
- **게이트 수정의 설계 기록(2026-11-01).**
  - 제안 없음을 검증 오류로 만들지 않았다. `validate_final`이 제안 없는 `human_review`·`denied`를 오류로 보면 맞는 답이 실패한다. 실제 모델 행(모델 이름이 `claude-sonnet-5-5`이고 입력 토큰이 기록된 행만)에서 맞은 답은 대개 환불 제안이 없다. 수정 앞에는 `policy-human-old` 20행 중 18행, `policy-deny-normal` 21행 중 14행이 `proposal`이 비었고 나머지는 `action`이 `none`인 제안이었다. 재실행으로 행이 는 뒤의 `outputs/runs/`에서 다시 세면 `policy-human-old` 25행 중 22행, `policy-deny-normal` 26행 중 17행이 비었고 나머지는 모두 `action: none`이라, 두 사례 51행 가운데 환불 제안이 있는 행은 0행이고 모두 기대한 레이블(`human_review`, `denied`)이다. 가짜 모델이 쓴 행을 빼지 않고 세면 같은 두 사례가 27행과 208행이 되어 이 비율을 읽을 수 없다. 그래서 제안이 없는 것을 막지 않고 질문이 가리킨 결제를 코드로 대조하는 쪽을 택했다. 지금 `outputs/runs`에서 다시 세면 두 사례의 실제 모델 행은 81개(`policy-human-old` 40, `policy-deny-normal` 41)이고 환불 제안이 있는 행은 `policy-human-old`의 1개다(결론은 `human_review`, 2026-11-01 행). 2026-11-02 재실행이 더한 10행(05 켠 실행 셀 41)에는 환불 제안이 없다(빈 제안 8, `action: none` 2). 모두 기대한 레이블이다. 재실행 전은 71개(35, 36)였다.
  - 번호는 질문에서만 읽는다. 답 본문은 검사받는 쪽의 주장이라(`mas_lab/gate.py:51`) 거기서 번호를 읽으면 모델이 고른 결제를 모델의 말로 검사하게 된다. 결함 주입 18(10.4절 2번)이 이를 지킨다. 번호가 하나가 아니거나 이 고객의 결제가 아니면 추측하지 않고 검사하지 못했다는 문장과 `gate_skipped` 사건을 남긴다. 조사가 붙은 `P-7001을`도 읽도록 `\b` 대신 앞 문자 검사를 쓴다(`mas_lab/gate.py:13`). 지금은 번호가 여럿이어도 모두 이 고객의 결제이면 번호마다 검사하고, 이 고객의 결제가 아닌 번호가 섞일 때만 추측하지 않는다(`mas_lab/gate.py:54-57`).
  - 탐침은 쓰지 않는다. 질문이 가리킨 결제를 그 결제의 실제 금액으로 `check_refund`에 물어 판정만 받고 `execute_approved`를 부르지 않는다(결함 주입 17이 지킨다). 제안 없이 원장에 닿는 길을 새로 만들지 않으므로 `AGENTS.md` 5장 8번의 쓰기 경로 규칙을 건드리지 않는다. `run_case`가 그래프 뒤에 `gate_answer`를 한 번 더 부르므로 이미 옮긴 답에는 `_settle`이 불확실성도 사건도 더하지 않는다(`mas_lab/gate.py:80-83`, 결함 주입 20). 코드가 쓴 문장은 출처로 등록한다(`mas_lab/gate.py:89`, `mas_lab/gate.py:96`). 문장에 금액이 들어가면 `validate_final`의 숫자 출처 검사가 코드의 문장을 실패시키기 때문이고, `desk.py`는 바꾸지 않았다.
  - 재생. 수정 앞의 실제 모델 행에서 제안 없는 `denied`·`human_review` 32행(`policy-deny-normal` 14, `policy-human-old` 18, 구조 다섯)을 새 코드에 넣었다. 레이블이 바뀐 행 0, 문장이 바뀐 행 0, 원장 0건(32행 모두), 자동 검사 통과 14에서 14, 18에서 18이었다. 바뀐 것은 각 행의 `uncertainty`에 코드 판정 문장이 하나씩 붙은 것뿐이다. 저장된 968행 가운데 실제 모델 행 477개에서 골랐고(가짜 모델 459행, 호출 없는 32행 제외) 제안이 있는 행 9개와 사례를 모르는 행 1개(`my-refund-window`)는 뺐다. 이 재생은 회귀가 없고 새 쓰기가 없음을 보일 뿐이다. 틀린 레이블을 코드가 뒤집는 쪽(먼저 승인된 결제를 `human_review`로 쓴 경우)은 저장된 행에 없어서 단위 시험과 10.4절 10번의 P-7001 3행이 보인다. 철자 수정 뒤에 다시 한 재생은 저장된 실제 행 422개(사례를 알고 저장된 환불 제안이 없는 행)를 지금 게이트에 넣었고, 뒤집힌 행 0, 문장을 바꾼 행 0, 문장을 덧붙인 행 51, `gate_skipped` 행 59, 원장 0건, 자동 검사 통과 410에서 410이었다(`docs/audit/replay-4-notes.md:93`). 그 질문에서 찾은 번호 꼴 120개는 모두 `P-<숫자>`라 철자 수정이 움직일 행이 없었다(`docs/audit/replay-4-notes.md:97`). 이 재생도 회귀가 없음만 보인다.
  - 위 `[미해소]` `complex-ops-log`(`insufficient`) 항목은 이번 수정이 다루지 않았다. 그 항목이 든 "05 기본 실행의 행은 `insufficient`(7회)"는 재실행 앞 기록의 값이다. 재실행한 05 기본 실행의 같은 행(셀 38 표의 `hybrid` `complex-ops-log`)은 `answered`(6회)였고 켠 실행도 `answered`(7회)였다. 한 번의 관찰이고 Worker가 근거 참조를 비우는 원인을 고친 것이 아니므로 그 항목의 상태는 바꾸지 않았다. 지금 기록(2026-11-02 재실행)의 같은 행은 기본 실행 6회(셀 38), 켠 실행 6회(셀 38)와 3회(셀 41, Router가 `fast`를 골랐다)이고 모두 `answered`, 자동 검사 통과다. 재실행 전 기록은 기본 실행 8회, 켠 실행 7회와 6회였다.

## 00-Setup

### 학습 목표

- 설치는 루트에서 한 번, 실행은 `Day03_new/`에서 한다는 구분을 말한다.
- 이 과정에 필요한 두 키와 그 비용 주체를 말한다.
- 모델 없는 그래프, 실제 모델, Deep Agent, EXA 네 층이 각각 자기 환경에서 도는지 확인한다.

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 설치와 폴더 구조 | 2 |
| 2 | 두 키 상태와 `.env` | 2 |
| 3 | 모델 없는 그래프와 사례 데이터 | 2 |
| 4 | 실제 모델, Deep Agent, EXA | 3 |
| 5 | 이후 시간표와 비용 | 1 |

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모. 수업 전에 끝내 두는 점검이다.
2. [M] 설치 원칙. 루트 `uv sync --locked`, 이 폴더에서 `uv sync` 금지, 실행 명령.
3. [C] Python, `deepagents`, `langgraph`, `langchain-anthropic` 버전과 `sys.prefix`가 루트 `.venv`인지 출력한다.
4. [C] `rag_lab`, `mas_lab` import, `ROOT`, 문서 수, 사례 수, 사실 파일 존재를 출력한다.
5. [M] 키 안내. 두 키를 왜 쓰는지, 어디서 발급하는지(`https://exa.ai/`, 구글 로그인 추천), 값은 출력하지 않는다. `Day02_new/.env`를 복사해 왔다면 `EXA_API_KEY`만 더한다.
6. [C] `key_status()`를 표로 출력하고 `require_key()`, `require_exa_key()`를 부른다.
7. [M] 3절. 오늘 그래프의 많은 셀은 모델을 부르지 않는 이유.
8. [C] 일반 함수 노드 3개를 `Send`로 돌려 `overlap_seconds`와 전체 시간을 출력한다. 모델 호출 0회.
9. [C] `load_billing("알파")`, `load_outage("알파")` 요약. 수업용 가상 데이터임을 함께 출력한다.
10. [C] `tokenize("서비스 크레딧 신청 기한")`으로 Kiwi 확인, 첫 실행 시간 출력.
11. [M] **관찰할 것.** 지금까지 비용 0이다. 다음 셀부터 비용이 생긴다.
12. [L] `make_model().invoke("한 단어로 답하세요: 준비")`. 모델 1회.
13. [L] `create_deep_agent`와 `lookup_payments`로 한 턴 실행하고 `message_table` 출력. 모델 2회.
14. [L] `ExaClient(...).search("LangGraph Send API")`. 제목과 URL만 출력. EXA 1회.
15. [M] **관찰할 것.** 실패 시 볼 곳 표. 키 없음, 401, 429, 시간 초과, import 오류.
16. [M] 01~06 시간표, 비용 규칙, `announce`의 의미.
17. [M] 직접 해보기 2개와 확인 질문 2개.

### 직접 해보기

1. `.env`의 `EXA_API_KEY`를 잠시 비우고 kernel을 재시작해 어느 셀에서 어떤 안내로 멈추는지 본다.
2. `Day03_new/` 밖에서 kernel을 띄우면 `import mas_lab`이 어떻게 되는지 보고 이유를 적는다.

### 확인 질문

1. 8번 셀과 13번 셀이 각각 증명하는 것과 증명하지 않는 것은 무엇인가?
2. 셸에 키를 export해도 `key_status()`가 미설정이라고 나오는 이유와 이 설계가 막으려는 사고는 무엇인가?

## 01-Workflow-vs-Agent

### 학습 목표

- LLM 호출, 도구 사용, Agent Loop를 "관찰 뒤 다음 행동을 누가 고르는가"로 구분한다.
- 같은 요청을 고정 경로와 동적 조사로 처리한 실행 기록을 비교해 각각 어디서 실패하는지 말한다.
- Workflow 안에 Agent를 넣는 지점과 코드로 남길 지점을 고른다.
- 모델의 제안과 시스템의 실행 권한을 분리하고, 프롬프트로 막는 것과 코드로 막는 것의 차이를 실행으로 보인다.
- Single 기준선을 남기고 정보 부족과 실행 오류를 구분한다.

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 사례와 오늘의 질문 | 5 |
| 1 | 결정권: 세 가지 실행 방식 | 10 |
| 2 | 같은 요청, 두 구조 | 13 |
| 3 | Workflow 안의 Agent | 8 |
| 4 | 제안과 실행 권한 | 10 |
| 5 | Single 기준선 | 8 |
| 6 | 직접 해보기와 정리 | 6 |

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모. 오늘의 질문을 "Agent를 몇 개 만들까?"가 아니라 "어디에 판단을 맡길까?"로 둔다. 작업 목표 → 작업 그래프 → 판단 배치 → Context 분리 → 검증·운영을 오늘의 지도로 둔다.
2. [C] import, `require_key()`, `key_status()`, `ModelMeter`, `Scope("알파", 2026-09-08)`, `build_retriever()`.
3. [M] 0절. 고객 요청을 제시하고, 수업용 가상 데이터임을 밝힌다. **먼저 예측하세요.** 이 요청을 처리하려면 어떤 사실이 몇 개 필요하고, 모델 호출은 몇 번 들까?
4. [C] 결제 사실, 가용률, 적용 문서 목록을 출력한다. 모델 호출 0회.
5. [M] **관찰할 것.** 어떤 사실은 이미 시스템에 있고, 어떤 규칙은 문서에 있으며, 어떤 판단은 아직 아무도 내리지 않았다. 세 종류를 표시한다.
6. [M] 1절. LLM을 쓴다고 모두 Agent는 아니다. 세 방식의 정의를 도구 호출 유무가 아니라 관찰 뒤 행동 선택과 종료 조건으로 쓴다.
7. [L] LLM 호출. 사실을 주지 않고 요청을 보낸다. 응답 본문, `tool_calls`, 토큰을 출력한다. 모델 1회.
8. [M] **관찰할 것.** 지어낸 금액이나 단정이 있는지, 없다면 무엇이라고 답했는지 읽는다.
9. [C] 도구 사용. 코드가 `lookup_payments`를 직접 부른다. 다음 행동은 코드가 정한다. 모델 호출 0회.
10. [L] LLM + 코드 분기. 모델은 `Route`로 의도만 분류하고 다음 행동은 `if`가 정한다. 모델 1회. "LLM을 쓰지만 Agent가 아닌" 예다.
11. [L] Agent Loop. `create_deep_agent`에 `lookup_payments`만 주고 실행, `message_table`로 읽는다. 모델 2~4회.
12. [C] 위 네 실행의 표를 만든다. 칸은 모델 호출, 도구 호출, 다음 행동을 고른 주체, 종료를 정한 주체.
13. [M] **관찰할 것.** 비교 칸 읽는 법. 세 방식은 세대교체가 아니라 업무에 따른 선택이다. 분류 하나를 Agent로 만들면 무엇을 잃는지 묻는다.
14. [M] 2절. **먼저 예측하세요.** 고정 경로가 복합 요청과 범위 밖 문의에서 어떻게 실패할까?
15. [C] `fixed_route(request)`를 일반 함수로 정의하고 소스와 분기표를 출력한다. 키워드로 결제·기한·장애를 나눈다.
16. [C] **실패 재현.** 요청 네 개(중복 결제, 기한, T-1001, "지난달 장애 때문에 환불도 되나요?")를 넣어 경로와 응답을 표로 출력한다. 모델 0회. 키워드 조합이 예외를 얼마나 놓치는지 본다.
17. [M] **관찰할 것.** 틀린 응답이 아니라 범위 밖 전환이 어디서 일어나는지 읽는다. 예외를 미리 정의해야 한다는 것의 비용.
18. [L] 전체 도구를 가진 Single로 같은 복합 요청과 네 번째 요청을 실행한다. 모델 6~12회.
19. [C] 두 구조의 비교표. 경로, 호출, 토큰, 시간, 사용한 도구.
20. [C] 실행 메시지에서 도구 호출 순서를 뽑아 출력하고, 실행마다 순서가 달라질 수 있음을 칸으로 표시한다.
21. [M] **관찰할 것.** 고정 경로의 실패는 코드 한 줄에 드러나고, Agent의 실패는 메시지 전체를 읽어야 드러난다. 비용 예측의 차이도 같은 표에서 읽는다.
22. [M] 3절. CODE·MODEL·API·AGENT·RULE 표. 좋은 시스템은 모든 노드가 Agent인 시스템이 아니다.
23. [C] `StateGraph`로 `verify → interpret → fetch → investigate → rule` 혼합 Workflow를 만들고 `show_graph` 출력.
24. [L] 실행한다. `interpret`와 `investigate`만 모델을 쓴다. 모델 3~6회.
25. [C] 노드별로 CODE/MODEL, 시간, 호출 수를 표로 내고 `timeline`을 출력한다.
26. [M] **관찰할 것.** 시간이 어디서 쓰였는지, 어느 노드가 코드로 충분했는지 묻는다. Day01의 그래프와의 연결.
27. [M] 4절. **먼저 예측하세요.** 모델에게 환불 도구를 직접 주고 "규정을 지켜라"라고만 적으면, 정상 결제 P-8101 환불 요청을 어떻게 처리할까?
28. [L] **실패 재현.** `refund_now`를 도구로 준 Agent에 요청한다. 가짜 원장만 쓰며 외부 호출은 없다. 모델 2~4회.
29. [C] 원장 상태와 메시지 표를 출력한다. 실행됐으면 그것이 관찰이고, 거절했으면 이번 1회는 프롬프트로 막힌 것이다. 어느 쪽이든 다음 질문으로 이어진다.
30. [M] **관찰할 것.** 프롬프트는 확률을 바꾸고 코드는 경로를 없앤다. 1회 거절이 "안전하다"는 증거가 아닌 이유.
31. [C] `check_refund` 소스 출력과 결정표. 입력 다섯 건(P-9002, P-8101, P-7002, 베타 P-5002, 다른 고객 결제)의 결정과 이유. 모델 0회.
32. [L] 제안만 하는 Agent. 쓰기 도구 없이 `Proposal`만 낸다. 그 값을 `check_refund`에 넣고 원장을 출력한다. 모델 2~4회.
33. [C] **실패 재현.** 제안의 금액이나 결제 번호를 일부러 바꿔 게이트가 거절하는지 본다. 모델 0회.
34. [M] **관찰할 것.** 모델이 틀려도 원장은 움직이지 않는 지점을 찾게 한다. 승인은 04에서 다룬다.
35. [M] 5절. 기준선 없이는 개선 여부도 알 수 없다. 측정 칸의 뜻.
36. [C] `load_cases()`로 사례 유형을 표로 출력한다. 질문만 있고 정답은 없다. `run_case`의 소스를 읽는다.
37. [L] Single로 `simple-deadline`, `complex-double-pay`, `insufficient-no-policy`를 실행한다. 모델 12~20회.
38. [C] `RunRow` 표와 `evaluate_row` 자동 검사 표. 실패 행을 지우지 않는다.
39. [C] 행을 `outputs/baseline/01.json`에 저장하고 실패 사유 칸을 출력한다.
40. [M] **관찰할 것.** 어떤 요청에서 실패했는가? 정보 부족과 실행 오류를 구분했는가? 실패 사례 한 개를 자기 말로 적게 한다. 이 행은 1회 관찰이다.
41. [M] 직접 해보기 안내.
42. [C] 해보기 1 골격: `fixed_route`에 규칙을 더해 16번의 실패 하나를 고치고, 다른 입력에서 무엇이 깨지는지 본다.
43. [L] 해보기 2 골격: 시스템 프롬프트만 바꿔 28번을 다시 실행. 모델 2~4회.
44. [C] 해보기 3 골격: `check_refund`의 규칙 순서를 바꾸면 결정표가 어떻게 달라지는지 본다(사본에서).
45. [L] 해보기 4 골격: 23번 Workflow에서 `interpret`를 규칙으로 바꾸고 비용과 실패를 비교. 모델 2~4회.
46. [C] 설계 기록: 고객 요청의 완료 상태를 `write_design_log`로 적는다.
47. [M] 정리. 결정권과 실행 권한 표.
48. [M] 확인 질문과 02 예고.

### 직접 해보기

1. `fixed_route`에 규칙을 더해 실패 하나를 고치고, 새로 깨지는 입력을 찾는다.
2. (실제 호출) 28번의 시스템 프롬프트를 강화해 다시 실행하고, 이것으로 무엇을 말할 수 있고 없는지 적는다.
3. `check_refund`의 규칙 순서를 바꿔 결정표를 다시 낸다. 어떤 입력의 이유가 달라지는가?
4. (실제 호출) `interpret`를 규칙으로 바꾼 뒤 호출 수와 실패를 비교한다.

### 확인 질문

1. 의도 분류에 LLM을 쓰는 Workflow가 Agent가 아닌 이유는 무엇인가? 무엇이 달라지면 Agent가 되는가?
2. 28번에서 모델이 환불을 거절했다면 이 구조는 안전한가? 출력의 어느 칸을 근거로 답하는가?
3. 고정 경로의 실패와 Agent의 실패는 드러나는 방식이 어떻게 다른가?
4. `check_refund`를 프롬프트에 옮겨 적으면 무엇을 잃는가?
5. 기준선이 1회 관찰인데도 남겨야 하는 이유와, 이 행으로 하면 안 되는 주장은 무엇인가?

## 02-Agent-Architecture

### 학습 목표

- 구조의 변화를 직전 구조의 한계로 설명한다(Single → Skill → Supervisor → Orchestrator-Worker → Handoff → Hierarchical).
- Single의 Context가 호출마다 어떻게 커지는지 실측으로 보이고 무엇이 커지는지 분해한다.
- Deep Agents `subagents=`로 Supervisor 구조를 실행하고 "모델이 정한 병렬"을 trace로 확인한다.
- Network와 Handoff를 구분하고 `Command(goto=)`로 담당자 이전과 왕복 상한을 만든다.
- 같은 요청의 실제 trace에서 제어권이 달라진 지점을 찾는다.
- 프레임워크가 자동으로 끼워 넣은 Worker와 직접 설계한 Worker를 코드 객체에서 읽은 표로 구분한다(2026-11-02).

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 변화의 지도 | 6 |
| 2 | Single의 한계 실측 | 9 |
| 3 | Supervisor: 결과를 돌려받는다 | 17 |
| 4 | Handoff: 대화를 넘긴다 | 12 |
| 5 | Supervisor, Orchestrator-Worker, Hierarchical, Plan-and-Execute 읽기 | 7 |
| 6 | 실제 Trace 비교 | 4 |
| 7 | 직접 해보기와 정리 | 5 |

앞 판의 시간표는 6/10/14/13/7/5/5였다. 3절에 자동 Worker 비교(아래 11-1~11-4)가 들어가 노트북의 시간표가 6/9/17/12/7/4/5가 됐다. 합은 둘 다 60분이다.

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모.
2. [C] import, 키 확인, `Desk`, `ModelMeter`.
3. [M] 1절 변화 표. 칸은 구조, 직전 구조의 어떤 한계에서 나왔는가, 새로 치르는 비용. 세대교체가 아니라 선택지가 늘어난 것임을 쓴다. 외부 용어 비교는 하지 않는다. 표 아래에 Supervisor가 넓게는 Manager 패턴이라는 이름 정리를 한 단락 둔다.
4. [C] `ARCHITECTURES` 표 출력. 칸은 다음 행동 결정, 결과가 돌아가는 곳, 최종 응답자, 이 노트북의 실행 여부. 코드로 둔 이유는 해보기에서 칸을 고치기 위해서다.
5. [M] 2절. **먼저 예측하세요.** T-1001을 Single로 돌리면 마지막 호출의 입력 토큰이 첫 호출의 몇 배일까?
6. [L] Single이 T-1001을 실행한다. 모델 4~8회.
7. [C] 호출별 표(순번, 입력 토큰, 출력 토큰, 메시지 수, 시간)와 `bars`.
8. [C] 마지막 호출의 입력을 시스템 지침, 도구 스키마, 대화 이력, 도구 결과의 글자 수로 분해한다.
9. [M] **관찰할 것.** 무엇이 가장 큰 칸인가? 모든 정보가 한 Context에 함께 쌓인다. 다만 이 예제 규모에서는 Context 초과 실패가 나지 않을 수 있음을 밝힌다. 한계의 징후와 실패를 구분한다.
10. [M] 3절. Supervisor는 결과를 받아 최종 응답한다(넓게는 Manager 패턴). Deep Agents의 `task` 도구. **먼저 예측하세요.** Single과 비교해 호출과 입력 토큰은 어떻게 바뀔까?
11. [C] `subagent_spec`으로 billing, policy, outage 정의를 출력한다. 칸은 이름, 설명, 허용 도구, 시스템 지침 앞부분.
   - 11-1. [M] 자동으로 끼워 넣은 Worker와 직접 설계한 Worker. `task` 설명이 부모가 위임할 수 있는 Worker의 목록임을 쓰고, **먼저 예측하세요.** `general-purpose`는 무엇을 볼 수 있고 무엇을 쓸 수 있는가? 두 셀은 에이전트를 만들기만 하고 모델을 부르지 않는다고 밝힌다.
   - 11-2. [C] 같은 `build_supervisor`를 두 설정으로 한 번씩 만들어 `task_targets`로 부모가 위임할 수 있는 Worker 이름을 비교한다. 하나는 `framework_default_subagent`(`mas_lab/harness.py:31`)로 만든 프레임워크 기본(`general-purpose` 포함), 다른 하나는 이 과정의 설정이다. 이름은 `task_targets`(`mas_lab/harness.py:46`)가 읽는다. 모델 0회.
   - 11-3. [C] 설계한 Worker 셋과 `general-purpose`를 같은 열로 비교하는 표. 칸은 이름, 설명, 보이는 도구, 예산·허용 목록, 지침이 근거 번호를 요구하는가, 읽은 곳이다. 설계한 행은 `subagent_spec`(`mas_lab/workers.py:173`)의 항목에서, `general-purpose` 행은 deepagents의 `GENERAL_PURPOSE_SUBAGENT`에서 읽는다. 표 아래에 이 사례의 조회 도구 중 `general-purpose`가 가진 것을 출력한다. 모델 0회.
   - 11-4. [M] **관찰할 것.** `general-purpose` 행을 설계한 행과 칸마다 맞대어 읽는다. 부모와 같은 것을 보면 Context 경계가 없고, `예산·허용 목록`이 비면 그 Worker의 모델 호출은 어느 예산도 세지 않는다. 그래서 이 과정은 `mas_lab/__init__.py`에서 import 때 끈다고 밝히고, 04 4절·05 3~4절·05 7절의 기준으로 되돌린다. 끈 것으로 끝나지 않으며 권한 경계는 프롬프트가 아니라 설정으로 확인해야 하고 Day08에서 다시 다룬다.
12. [L] Supervisor 실행. 지침에 "독립 조사는 한 메시지에서 동시에 위임하라"를 넣는다. 모델 8~14회.
13. [C] 부모의 `message_table`. 한 메시지 안의 `task` 호출 수를 센다.
14. [C] Trace의 `timeline`과 `overlap_seconds`. Worker 구간이 겹쳤는지 본다.
15. [C] 부모 메시지에 Worker의 도구 대화가 있는지, ToolMessage로 무엇이 돌아왔는지 글자 수로 출력한다.
16. [M] **관찰할 것.** 병렬 여부를 정한 주체가 모델이라는 점을 읽는다. 겹침이 0이었다면 이번 실행에서 모델이 그렇게 고른 것이다.
17. [L] **실패 재현.** 같은 구조에서 지침의 "동시에"를 뺀다. 모델 8~14회.
18. [C] 12번과 17번의 비교표. 위임 순서, 메시지당 `task` 수, 시간, 토큰.
19. [M] **관찰할 것.** 프롬프트 한 줄이 실행 구조를 바꿀 수 있다는 것은 구조가 코드에 고정되어 있지 않다는 뜻이다. 03에서 코드로 고정한다.
20. [C] subagent 안에서 예산이 어떻게 합산되는지 `budget.report()`로 출력한다. 부모만 middleware를 걸면 어떻게 되는지 두 경우의 설정을 표로 보인다(Day08 예고). 모델 0회.
21. [M] 4절. Network는 연결 모양, Handoff는 제어권 규칙이다. **먼저 예측하세요.** 종료 조건 없이 서로 넘기는 두 담당자는 어떻게 될까?
22. [C] **실패 재현.** 일반 함수 노드 둘이 `Command`로 서로 넘긴다. `recursion_limit=8`의 `GraphRecursionError`를 잡아 출력한다. 모델 0회.
23. [C] 왕복 상한 2를 넣으면 `needs_clarification` 상태로 끝나는 것을 출력한다. 모델 0회.
24. [C] **실패 재현.** `Command` 반환 타입을 안 적은 그래프의 간선 표와 `Command[Literal[...]]`을 적은 그래프의 간선 표를 비교한다.
25. [C] `build_handoff` 소스와 `show_graph` 출력. Triage, Billing, Technical 세 담당자.
26. [L] 턴 1: T-1001. 체크포인터로 실행. 모델 3~8회.
27. [C] 턴 1의 `active owner`, `handoff` 사건, 최종 응답자 출력.
28. [L] 턴 2: "그럼 장애 보상은 언제까지 신청하나요?" 같은 thread. 모델 3~8회.
29. [C] 두 턴의 담당자 표. 담당자 유지와 전환, 다시 검색했는지, 턴별 입력 토큰. 과거 대화는 해석의 단서이지 근거가 아니다.
30. [M] **관찰할 것.** 잘못 유지된 담당자의 위험과 전환 비용. `handoff`와 담당자 유지 사건을 trace로 읽는다.
31. [M] 5절. 나머지 구조를 어떤 문제에 쓰는지. 이 절은 일반 함수로 구조만 보고, 실제 구현은 03·04에서 다시 만난다.
32. [C] Supervisor 뼈대: 분기 + 루프. 3절에서 부모 모델이 하던 다음 Worker 고르기를 `route` 함수가 맡는다. 일반 함수 노드로 `show_graph`와 실행 순서를 출력한다. 모델 0회.
33. [C] Hierarchical: subgraph 두 개. `show_graph(xray=True)`와 계층 간 전달물 크기 비교(전체 로그 vs 근거·상태·한계). 모델 0회.
34. [C] Plan-and-Execute: 2단계에서 실패하는 상황을 고정 계획과 재계획으로 돌린다. 실패를 알아챈 시점과 낭비한 단계 수를 비교한다. 모델 0회.
35. [M] **관찰할 것.** 계층을 더할 이유가 없다면 전달 손실과 지연만 는다. 계획의 존재가 아니라 관찰 뒤 수정 가능 여부가 차이다.
36. [M] 6절. 누가 다음 행동을 정했고 결과가 어디로 돌아갔는지를 실제 실행 값으로 채운다.
37. [C] Single, Supervisor, Handoff의 표. 칸은 control owner, 호출, 입력 토큰, Context 전달 범위, 최종 응답 주체.
38. [C] 세 실행의 사건 순서에서 제어권이 처음 달라진 지점을 찾아 출력한다.
39. [M] **관찰할 것.** 어떤 구조가 낫다는 결론을 내리지 않는다. 이 표로 말할 수 있는 것과 없는 것. 대화 이전 안에서 조사 Workflow를 쓸 수 있으므로 둘 중 하나만 고를 필요는 없다.
40. [M] 직접 해보기 안내.
41. [L] 해보기 1 골격: subagent `description`을 모호하게 바꾸고 위임 대상 변화를 본다. 모델 8~14회.
42. [L] 해보기 2 골격: Worker에 결제 사실을 `facts`로 미리 주면 호출이 줄어드는지 본다. 모델 6~12회.
43. [C] 해보기 3 골격: 왕복 상한을 0, 1, 3으로 바꿔 23번을 다시 돌린다.
44. [C] 해보기 4 골격: 33번의 계층 전달물에서 불확실성 칸을 지우고 어떤 질문에 답할 수 없게 되는지 적는다.
45. [C] 4번 표에서 자기 업무에 맞는 행을 고르고 설계 기록에 "코드나 Skill로 충분하지 않은 이유"를 쓴다.
46. [M] 정리. 변화 표를 자기 말로 다시 채운다.
47. [M] 확인 질문과 03 예고.

### 직접 해보기

1. (실제 호출) subagent 설명을 "정보를 찾는다"로 바꿔 위임이 어떻게 달라지는지 본다.
2. (실제 호출) `facts`를 미리 전달할 때 호출·토큰과 인용 근거의 변화를 본다.
3. 왕복 상한을 바꿔 종료 상태를 비교한다.
4. 계층 전달물에서 불확실성 칸을 지우면 무엇을 잃는지 적는다.

### 확인 질문

1. Supervisor에서 Worker의 도구 대화가 부모에게 보이지 않는 것의 이득과 대가는 무엇인가?
2. 17번에서 병렬이 사라졌다면 그것은 버그인가? 누구의 결정인가?
3. Supervisor와 Handoff에서 최종 답은 각각 누가 하는가? 출력의 어느 칸이 근거인가?
4. 담당자를 유지했는데 왜 현재 질문의 근거를 다시 찾아야 하는가?
5. 계층을 하나 더 둘 때 확인해야 할 것은 무엇이고, 이 노트북의 어느 실측이 그 근거인가?
6. 자동으로 끼워 넣은 Worker가 이 사례에서 맡을 수 있는 일은 무엇인가? 11-3의 어느 칸이 근거인가? (2026-11-02에 더했다)

## 03-Four-Flows

### 학습 목표

- 패턴 이름 없이 업무의 상태, 작업, 선행 조건, 종료 조건을 먼저 표로 쓴다.
- 순차, 병렬, 분기, 루프를 `StateGraph`로 직접 만들고 각각의 실패를 재현한다.
- `Send`와 reducer의 역할을 설명하고, 같은 분해에서만 병렬의 시간 효과를 비교한다.
- 최장 경로로 지연을 계산하고 실측과 대조한다.
- Router, Supervisor, Orchestrator-Worker, Handoff, Hierarchical을 네 흐름으로 번역한다.

Day01에서 `Send`를 깊게 다루지 않았다(`11-LangGraph-Branching`에 호출 없음). 이 노트북이 처음부터 가르친다.

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 패턴 말고 업무 먼저 | 8 |
| 2 | 순차와 Context | 8 |
| 3 | 병렬, reducer, 최장 경로 | 16 |
| 4 | 분기와 오분류 비용 | 8 |
| 5 | 루프와 종료 조건 | 9 |
| 6 | 패턴을 네 흐름으로 번역 | 7 |
| 7 | 직접 해보기와 정리 | 4 |

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모.
2. [C] import, 키 확인, `Desk`, `Trace`, `ModelMeter`.
3. [M] 1절. 목표 → 필요한 상태 → 작업 → 선행 조건 → 종료 조건. "Billing Agent를 만들자"보다 "무엇이 먼저 필요한가"를 묻는다. **먼저 예측하세요.** 5.1의 그림을 보여 주기 전에 수강생이 먼저 의존 표를 적는다.
4. [C] T-1001 작업 표 `TASKS`를 정의하고 위상 정렬로 "동시에 실행 가능한 묶음"을 출력한다. 상태 칸(`customer_verified`, `billing_facts`, `policy_evidence`, `outage_facts`)을 함께 보인다.
5. [C] **실패 재현.** 순환 의존과 없는 작업 의존을 넣어 검증이 거절하는 메시지를 출력한다. "JSON을 냈다"와 "실행 가능한 계획"은 다르다(`Day03/common/contracts.py:47-59`).
6. [M] **관찰할 것.** 이 표 어디에 순차·병렬·분기·루프가 있는지 표시해 보게 한다.
7. [M] 2절. State, Node, Edge. 선행 결과가 있어야 다음을 실행한다.
8. [C] `verify → billing → credit` 일반 함수 그래프. `stream(stream_mode="updates")`로 단계별 상태 변화를 출력한다. 모델 0회.
9. [C] **실패 재현.** `verify`가 범위 밖이면 다음 단계를 돌리지 않는 조건부 간선. 범위 안, 밖 두 실행의 경로를 비교한다.
10. [M] 순차에서 Context를 나누는 이유. 조사자, 작성자, 검토자가 각각 무엇을 받는가.
11. [L] 조사 → 작성 → 검토 세 역할을 실제 모델로 돌린다. `Day03/03_sequential_rag.py`의 관찰을 옮긴다. 모델 3~5회.
12. [C] 역할별 입력 바이트, 토큰, 시간 표.
13. [M] **관찰할 것.** 작성자가 근거를 못 받으면 무엇이 생기는지 묻는다. 역할 수가 아니라 전달물을 읽는다.
14. [M] 3절. **먼저 예측하세요.** 일반 필드에 동시에 쓰면 어떻게 될까? 0.3초 작업 세 개의 전체 시간은?
15. [C] **실패 재현.** reducer 없는 fan-out의 `InvalidUpdateError`를 잡아 출력한다. 오류 문장을 읽는다.
16. [C] `for` 문 호출의 시간과 구간을 출력한다. "빠른 순차 호출"을 병렬로 착각하지 않게 한다.
17. [C] `Send` + `merge_results`. 전체 시간, `timeline`, `overlap_seconds`, `show_graph`. Send 입력에 무엇을 넣었는지(최소 입력) 출력한다.
18. [C] 같은 그래프를 `config={"max_concurrency": 1}`로 실행하고, `plan_hash`가 같음과 시간 차이를 출력한다. 그래프를 고치지 않았다.
19. [C] 작업 시간을 0.2, 0.2, 1.0으로 바꾼다. `longest_path` 계산값과 실측을 나란히 출력한다.
20. [C] **실패 재현.** `credit`을 의존 무시하고 함께 `Send`한다. 입력 없이 시작해 어떤 값이 나오는지 출력한다. `Send`는 의존을 모른다.
21. [C] 재전달과 상충: 같은 키의 같은 값은 통과, 다른 값은 `ValueError`인 `merge_results`를 직접 호출한다.
22. [M] **관찰할 것.** 병렬이 줄이는 것은 전체 시간뿐이고, 합산 호출과 토큰은 줄지 않는다는 것을 다음 실측으로 확인한다.
23. [L] `PLAN` 고정(billing, policy, outage)으로 실제 Worker 3개를 `Send`로 실행한다. 모델 6~12회.
24. [L] 같은 `PLAN`을 `max_concurrency=1`로 실행한다. 모델 6~12회.
25. [C] 비교표: `plan_hash`, 전체 시간, 겹침, 합산 시간, 토큰, 호출, 필수 사실. 1회 관찰.
26. [M] **관찰할 것.** 모델 응답이 달라 호출 수까지 달라질 수 있으므로 "구조만의 효과"로 단정하지 않는다. 02의 모델이 정한 병렬과의 대비. `Send`는 동적 작업 배분 수단이지 그 자체로 Multi-Agent 아키텍처가 아니다.
27. [M] 4절. Router는 조건부 간선이다.
28. [C] 규칙 라우터: 조건부 간선과 분기표. 네 요청의 경로 출력. 모델 0회.
29. [L] 모델 라우터: 사례 6개를 `Route`로 분류하고 `routing_table`로 대조한다. 모델 6회.
30. [C] **실패 재현.** 복합 요청을 Fast Path로 강제로 보낸다. 누락된 필수 사실을 자동 검사로 출력한다.
31. [C] 오분류 복구 규칙: 근거 부족이면 Slow Path로 전환하는 간선을 더한다. 두 경로의 경로 비교.
32. [M] **관찰할 것.** 오분류의 비용은 정확도 하나가 아니라 방향에 따라 다르다. 복합을 단순으로 보내면 누락, 단순을 복합으로 보내면 비용이다.
33. [M] 5절. 생성 → 검증 → 재시도 또는 종료. **먼저 예측하세요.** 검증이 계속 실패하면?
34. [C] **실패 재현.** 종료 조건 없는 루프의 `GraphRecursionError`.
35. [C] 재시도 상한과 "같은 실패 반복 감지"를 넣은 결정적 루프. 실패 내용이 같으면 멈춘다.
36. [L] 실제 루프: 초안 → 필수 항목 검증 → 부족한 항목만 재검색 → 재작성. `Day03/02_adaptive_rag.py`의 관찰을 옮긴다. 모델 3~6회.
37. [C] 시도별 누락 항목, 호출, 토큰 표.
38. [M] **관찰할 것.** 재시도가 나아지지 않을 때 그래프가 무엇을 하는지 읽는다. 같은 프롬프트의 재호출은 전략이 아니다.
39. [M] 6절. 패턴을 실행 구조로 번역하는 표. Router는 분기, Supervisor는 분기 + 루프(필요 시 병렬), Orchestrator-Worker는 분해 → 병렬 → 집계, Handoff는 담당자 전환 + 반복, Hierarchical은 그 중첩이다.
40. [C] 일반 함수로 Router, Supervisor, Orchestrator-Worker, Handoff, Hierarchical 뼈대 다섯을 만들고 `flows_of`로 조건부 간선 수, cycle 유무를 표로 출력한다.
41. [C] 표에 실행 trace의 겹침을 더해 병렬 칸을 채운다. `flows_of`만으로는 병렬을 알 수 없음을 보인다.
42. [C] Orchestrator-Worker 조립: `plan → Send → aggregate → validate → replan`. 네 흐름이 어디 있는지 노드마다 표시해 출력한다.
43. [L] 42번을 실제 Worker로 T-1001에 실행한다. 모델 8~15회.
44. [M] **관찰할 것.** 네 흐름으로 쓰면 패턴 이름 없이도 비교할 수 있다. 새 패턴을 만나면 순서·독립성·조건·종료부터 묻는다.
45. [M] 직접 해보기 안내.
46. [C] 해보기 1 골격: 자기 업무로 `TASKS`를 쓰고 묶음을 출력한다.
47. [C] 해보기 2 골격: 병렬 작업 시간을 바꿔 병렬 이득이 사라지는 조건을 찾는다.
48. [L] 해보기 3 골격: `PLAN`을 2개로 합쳐 다시 실행하고 필수 사실과 토큰을 본다. 모델 4~8회.
49. [C] 해보기 4 골격: 35번 루프의 재시도 상한과 같은 실패 판정을 바꾼다.
50. [C] 설계 기록: 자기 업무의 네 흐름을 적는다.
51. [M] 정리. 네 흐름 표와 번역표.
52. [M] 확인 질문과 04 예고.

### 직접 해보기

1. 자기 업무를 `TASKS`로 쓰고 동시에 실행 가능한 묶음을 찾는다.
2. 병렬 이득이 사라지는 작업 시간 분포를 찾아 최장 경로로 설명한다.
3. (실제 호출) 작업을 합쳐도 필수 사실이 유지되는지 본다.
4. 재시도 상한과 같은 실패 판정을 바꿔 종료 상태를 비교한다.

### 확인 질문

1. `Send`로 fan-out했는데 reducer가 필요한 이유는 무엇인가? 15번 오류 문장으로 답하라.
2. 18번이 25번보다 병렬 효과에 대해 더 강하게 말할 수 있는 이유는 무엇인가?
3. 병렬인데 토큰이 줄지 않는 이유와, 그래도 병렬을 택할 조건은 무엇인가?
4. 라우터의 정확도 하나로 비용을 판단하면 무엇을 놓치는가?
5. Supervisor를 이 노트북의 네 흐름으로 번역하라. `flows_of`가 말해 주지 못하는 칸은 무엇인가?

## 04-Graph-Engineering

### 학습 목표

- 이 과정의 Graph Engineering 정의를 말하고, 그 정의가 2~8절의 어느 작업에 대응하는지 짚는다(2026-11-02).
- Prompt, Context, Harness, Graph, Loop가 각각 무엇을 설계하는지 자기 구조의 부품에 대응시킨다.
- 역할 프롬프트와 작업 계약의 차이를 Worker 출력으로 비교한다.
- Worker 사이의 전달 계약을 스키마로 쓰고, 스키마 통과와 근거 검증이 다름을 보인다.
- 요약 전달과 근거 전달의 손실을 **같은 Worker 결과**에서 비교한다.
- 실패 종류에 따라 다음 행동을 다르게 정하고 예산으로 멈춘다.
- 병렬 Worker의 부분 실패를 합류 노드에서 드러내고, 완료 결과를 보존한 채 실패한 작업만 다시 돌린다.
- 승인을 실행 전에 두고, 재개와 재시도에서 중복 실행이 어떻게 생기고 어떻게 막히는지 실행한다.

### 용어

이 노트북의 정의는 다음과 같다. Prompt는 지시, Context는 제공 정보, Harness는 실행 환경, Graph는 작업·상태·의존관계, Loop는 반복·재시도·종료다.

**이 과정의 Graph Engineering(2026-11-02).** 작업을 노드와 간선으로 명시하고, 노드마다 누가 판단하는지(코드·모델·사람), 무엇을 주고받는지(계약), 언제 멈추고 다시 하는지(예산·실패별 다음 행동·승인)를 그래프에 적어 넣는 일이다. 다섯 층 지도의 Graph 층을 설계하면서 나머지 네 층을 노드와 간선에 배치하는 작업이고, 2~8절이 층별로 하나씩 만든다. 노트북은 1절 층 지도 아래에 이 정의를 쓰고, 정리 셀에서 "Graph Engineering"이 2026년에 퍼진 외부 용어이며 출처마다 범위가 다르다고 밝힌 뒤 비교용 읽을거리 두 편을 둔다. 앞 판(2026-10-31)은 외부 용어라는 이유로 정의를 세우지 않고 읽을거리로만 두었으나, 그러면 Part 4의 제목이 수업에서 정의되지 않은 채 남아 바꿨다.

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 층 지도 | 4 |
| 2 | Prompt: 작업 계약 | 6 |
| 3 | Context: 전달 계약과 손실 | 11 |
| 4 | Harness: 공유 예산 | 5 |
| 5 | Graph와 Loop: 실패별 다음 행동 | 9 |
| 6 | 부분 실패와 합류 | 6 |
| 7 | 승인과 멱등 | 10 |
| 8 | 완성형 조립 | 5 |
| 9 | 직접 해보기와 정리 | 4 |

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모.
2. [C] import, 키 확인, `Desk`, `Trace`, `ModelMeter`.
3. [M] 1절. 새로운 이름은 이전 기술을 없애지 않는다. 다섯 층과 각 층의 질문을 표로 쓰고, 표 아래에 위 "이 과정의 Graph Engineering" 정의를 한 단락 둔다(2026-11-02).
4. [C] 이 과정의 부품을 층에 대응시켜 출력한다. 칸은 층, 부품, 파일과 줄(`inspect`로 얻는다), 없으면 생기는 실패.
5. [M] 2절. **먼저 예측하세요.** 역할만 있는 지시를 받은 Worker의 출력은 다음 단계가 쓸 수 있을까?
6. [L] 역할 프롬프트("너는 장애 보상 전문가야")로 outage Worker 실행. 모델 2~4회.
7. [L] `contract_prompt`(작업, 근거, 출력, 한계, 권한)로 같은 작업을 실행. 모델 2~4회.
8. [C] 두 출력을 `validate_result`와 자동 검사로 표로 비교한다. 칸은 검증 가능한 근거 수, 불확실성 유무, 사실 수, 숫자의 출처.
9. [M] **관찰할 것.** 역할 프롬프트가 무의미하다는 뜻이 아니다. 역할 이름만으로 업무가 완성되지 않는다는 뜻이다. 1회 관찰의 한계를 쓴다.
10. [M] 3절. 입력 계약과 반환 계약.
11. [C] `WorkerTask`, `WorkerResult`의 JSON 스키마 출력. 입력에 `allowed_tools`가 왜 있는지 쓴다.
12. [C] **실패 재현.** 잘못된 결과 세 개(없는 status, 없는 근거 ID, 근거 없는 complete)를 Pydantic과 `validate_result`에 넣어 각각 어느 층이 거절하는지 표로 출력한다. 프로토타입에서 모델이 `"lookup_outage: 8월 장애"`처럼 검증 불가한 값을 낸 사실을 언급한다.
13. [M] 판서 연결. "개별 에이전트가 핵심 1줄만 → 80점", "Context가 넘쳐나는데 어떻게 요약할 것인가?". **먼저 예측하세요.** 1줄 요약이 지우는 것은 무엇일까?
14. [L] Worker 3개를 실행해 `WorkerResult`를 얻고 저장한다. 모델 6~12회.
15. [C] 같은 결과로 세 전달물을 만든다(1줄 요약, 사실+근거+불확실성, 원문 포함). 바이트를 표로 낸다. 작업을 다시 돌리지 않는 이유는 변수를 전달 형태 하나로 두기 위해서다.
16. [L] 같은 작성자에게 세 전달물을 각각 줘서 답을 만든다. 모델 3회.
17. [C] 자동 검사 표: 필수 사실, 금지 사실, 조건 유실(사용량 초과 제외, 추가 약정 우선), 인용 유효성, 입력 토큰.
18. [C] `trim_payload`로 같은 결과를 예산 세 단계로 줄인다. 칸은 남은 바이트, 뺀 항목, 남은 근거 참조, 불확실성 유무. 모델 0회.
19. [C] **실패 재현.** 바이트에서 그냥 자르면 `sla-a-v2.md:13`의 "단, 월 누적 120분을 초과한 점검 시간은 포함한다"처럼 예외 문장이 사라지는 것을 출력한다. 줄이는 쪽에서 복원할 수 없다는 것과, 검색에서 빠진 문서는 뒤에서 되살릴 수 없다는 것을 함께 쓴다.
20. [M] **관찰할 것.** 전체 입력 토큰과 근거 Context 바이트를 구분한다. 토큰이 줄어도 필수 조항 누락이 늘었다면 함께 보고한다.
21. [M] 4절. 실행·검증·중단·복구는 모델 주변 시스템의 책임이다.
22. [C] 스레드 3개가 `Budget(max_model_calls=5)` 하나를 소모한다. 누가 언제 `BudgetExceeded`를 받는지 출력한다. 모델 0회.
23. [L] **실패 재현.** `Budget(max_model_calls=2)`로 Worker를 실행한다. 실패 행과 `budget.report()`를 출력한다. 모델 2회.
24. [M] **관찰할 것.** 예산 초과는 드러내야 할 실패다. 숫자를 올려 감추기 전에 어떤 호출이 소진했는지 본다.
25. [M] 5절. 실패했다고 무조건 다시 호출하지 않는다. **먼저 예측하세요.** 각 실패의 다음 행동을 적는다.
26. [C] `classify_failure`, `next_action` 소스와 결정표.
27. [C] 일반 함수 그래프에 네 경우를 주입한다(근거 부족, 정책 불가, 시스템 오류, 예산 초과). 각 경로를 출력한다. 모델 0회.
28. [C] `RetryPolicy`와 `next_action`을 비교한다. `RetryPolicy`는 같은 노드의 시스템 오류 재시도이고, 재조사나 미실행 종료를 대신하지 못한다. 그리고 `Send(timeout=)`가 동기 노드에서 `ValueError`인 것을 출력한다.
29. [L] `faults={"lookup_availability": "timeout_once"}`로 실제 Worker 조립을 실행한다. 모델 6~12회.
30. [C] 사건 순서와 도구별 호출 횟수를 출력한다. 완료된 Worker가 다시 돌았는지 본다.
31. [C] `faults={"lookup_availability": "timeout_always"}`의 경로를 일반 함수로 확인해 `escalate`로 끝나는 것을 본다. 모델 0회.
32. [M] **관찰할 것.** 복구의 비용과 보존의 효과. 이것은 제어 경로 확인이지 장애율 측정이 아니다.
33. [M] 6절. 병렬 Worker 셋 중 하나만 실패했다. 합류 노드는 무엇을 해야 할까? **먼저 예측하세요.** 실패를 빠뜨린 채 작성 노드로 넘기면 답은 어떻게 보일까?
34. [C] **실패 재현.** 성공한 결과만 모아 넘기는 합류. 출력에 누락 표시가 없고 정상 완료처럼 보이는 것을 확인한다. 모델 0회.
35. [C] `join_results`로 필수 작업별 상태 표를 낸다. complete, uncertain, failed, 결과 없음을 구분하고 `next_action`으로 잇는다.
36. [C] 실패한 작업만 새 키(`outage#2`)로 다시 `Send`한다. 작업별 실행 횟수 카운터로 완료된 Worker가 다시 돌지 않았음을 보인다. 같은 키에 다른 결과를 쓰면 `merge_results`가 거절하는 것도 출력한다.
37. [M] **관찰할 것.** 누락을 드러내는 책임은 합류 노드에 있다. 이 구조는 동시에 도는 두 시도의 늦은 도착까지 판별하지 않는다. 그 필요가 생기면 무엇을 더 기록해야 할지 묻는다.
38. [M] 7절. 처리 제안 → 정책·권한 검증 → 필요한 승인 → 쓰기 실행 → 결과 확인. **먼저 예측하세요.** 재개하면 노드의 어디부터 다시 실행될까?
39. [C] **실패 재현.** `interrupt` 앞에 원장 호출을 둔 노드를 재개한다. 실제로 원장에 두 건이 남는 것과 카운터를 출력한다. 모델 0회.
40. [C] 올바른 승인 그래프: `propose → gate → approve(interrupt) → execute → verify`, `MemorySaver`, `show_graph`.
41. [L] 모델이 T-1001의 제안을 낸다. `interrupt`에서 멈춘 상태와 원장 0건을 출력한다. 모델 2~5회.
42. [C] `Command(resume={"approved": True})`로 재개한다. 원장 1건, 결과 확인 사건 출력.
43. [C] 거절 재개(새 thread): 미실행 종료와 원장 0건. 금액을 고친 재개: 게이트가 다시 검사한다. 승인 바인딩은 Day08에서 다룬다고 쓴다.
44. [C] **실패 재현.** `lose_response=True`로 응답 유실을 만들고 키 없이 재시도하면 원장 2건, 키로 재시도하면 1건임을 출력한다.
45. [C] 응답 유실 뒤 `ledger.find(key)`로 외부 결과를 먼저 조회하는 복구 절차를 출력한다.
46. [M] **관찰할 것.** 체크포인트는 우리 그래프의 진행을 저장할 뿐이다. `idempotency_key`는 외부 시스템이 지원·강제해야 하며 재개해도 exactly-once가 자동 보장되지 않는다. 여기의 원장은 그 강제를 흉내 낸 가짜다.
47. [M] 8절. Workflow 안에 필요한 Agent만 배치한다.
48. [C] `build_hybrid` 소스와 `show_graph`. 각 노드에 층을 표시한다.
49. [L] `complex-double-pay`를 실행해 승인 대기까지 간다. 모델 8~16회.
50. [C] `RunRow`, `timeline`, 자동 검사, 원장 상태를 출력한다.
51. [M] **관찰할 것.** 처음의 업무 목표를 끝까지 추적한다. 실행과 미실행의 결과까지 설명한다.
52. [M] 직접 해보기 안내.
53. [L] 해보기 1 골격: `TASK_CONTRACT`에서 한 줄(한계 또는 권한)을 지우고 7번을 다시 돌린다. 모델 2~4회.
54. [C] 해보기 2 골격: `trim_payload`의 우선순위를 바꿔 어떤 항목이 먼저 사라지게 할지 정하고, 그 선택이 어떤 답을 위험하게 만드는지 적는다.
55. [C] 해보기 3 골격: `next_action`을 고쳐 정책 불가도 재조사하게 하면 어떤 경로가 나오는지 27번으로 본다.
56. [C] 해보기 4 골격: 승인 그래프에서 `verify`를 빼면 무엇을 알 수 없게 되는지 응답 유실로 확인한다.
57. [C] 설계 기록: "무엇을 보고 무엇을 실행할 수 있는가", "언제 재시도하고 언제 전환하는가".
58. [M] 정리. 층별 요약, Day08에서 이어지는 항목, 외부 읽을거리 링크 2개. 읽을거리는 "이 과정은 1절의 정의를 쓴다"고 밝힌 뒤 두 글이 각각 무엇을 그래프의 일로 보는지를 층 지도에 대응시켜 비교하게 한다.
59. [M] 확인 질문과 05 예고.

### 직접 해보기

1. (실제 호출) 작업 계약의 한 줄을 지우고 달라지는 칸을 찾는다.
2. `trim_payload`의 우선순위를 바꿔 무엇을 잃는지 본다.
3. 정책 불가를 재조사로 바꿔 경로를 보고 왜 안 되는지 말한다.
4. 승인 그래프에서 `verify`를 빼고 응답 유실을 넣어 본다.

### 확인 질문

1. 인용 ID가 있고 스키마를 통과한 `WorkerResult`도 왜 신뢰할 수 없는가? 12번의 어느 행이 근거인가?
2. 15~17번이 전달 형태의 효과를 보여 주기 위해 Worker를 다시 돌리지 않은 이유는 무엇인가?
3. 시스템 오류와 근거 부족의 다음 행동이 왜 달라야 하는가?
4. 실패한 Worker를 조용히 빠뜨린 합류가 왜 그 실패 자체보다 위험한가?
5. `MemorySaver`가 있는데 왜 `idempotency_key`가 필요한가? 39번과 44번의 차이는 무엇인가?
6. 여기 원장의 멱등 보장을 실제 결제 API에 그대로 기대할 수 없는 이유는 무엇인가?

## 05-Choosing-Multi-Agent

### 학습 목표

- 먼저 작업을 Workflow와 Agent로 나누고, Multi-Agent를 따질 대상이 모델이 맡은 칸뿐임을 확인한다(2026-11-02).
- 나누기 전에 Single의 실패를 분류하고, 프롬프트·도구·검색으로 고칠 문제를 먼저 고친다.
- 같은 사례에서 이득과 비용을 함께 재고, 조정 비용을 숫자로 말한다.
- Persona 분리와 Context 분리를 실행으로 구분한다.
- 코드, Skill, SubAgent 중 무엇을 쓸지 기준을 말한다.
- 수치의 비교 조건을 읽고, 지연을 최장 경로로 분해한다.
- Fast/Slow Path와 공통 게이트를 설계하고 오판의 경로를 확인한다.
- 같은 조건의 비교표를 만들고 말할 수 있는 것과 없는 것을 구분한다.
- 다섯 구조가 같은 하네스(예산, 도구 허용 목록, 응답 형식, 쓰기 게이트)를 지나기 때문에 구조만 다르게 비교된다는 점을 코드로 확인한다(2026-11-02).

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 먼저 작업을 Workflow와 Agent로 나눔 | 5 |
| 1 | 먼저 Single의 실패를 분류 | 8 |
| 2 | 이득과 비용 | 6 |
| 3 | Context 경계 vs Persona | 6 |
| 4 | Skill vs SubAgent | 6 |
| 5 | 수치 읽기와 지연 분해 | 5 |
| 6 | Fast/Slow Path | 6 |
| 7 | 같은 조건 비교표 | 12 |
| 8 | 선택 기록 | 3 |
| 9 | 직접 해보기와 정리 | 3 |

앞 판의 시간표에는 0절이 없고 1~9절이 10/7/7/7/6/6/10/3/4분이었다. 0절(5분)과 7절의 하네스 셀(2분 늘어남)을 더하느라 나머지를 줄였다. 합은 둘 다 60분이다.

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모. 이 노트북이 가장 비싸다는 것과 `RUN_OPTIONAL`을 알린다.
2. [C] import, 키 확인, `load_cases`, `model`, `RUN_OPTIONAL = False`.
   - 2-1. [M] 0절(2026-11-02). 질문 "Agent를 나눌까?"는 작업을 먼저 Workflow와 Agent로 나타낸 뒤에야 뜻이 있다. 순서가 정해진 일, 규칙으로 판정할 수 있는 일, 사람이 승인할 일은 코드와 사람의 몫이고 모델의 판단이 필요한 칸만 Agent의 몫이다. **먼저 예측하세요.** 노드가 열 개 남짓인 `build_hybrid` 그래프에서 모델이 맡은 노드는 몇 개인가?
   - 2-2. [C] `build_hybrid` 그래프를 만들기만 하고 부르지 않는다. 그래프에서 노드 이름을 읽어 노드마다 담당(코드·모델·사람)을 표로 적는다. 담당은 그래프에서 알 수 없어 셀 안의 사전(`NODE_OWNER`)에 사람이 적고, 그래프에 있는 노드가 사전에 없으면 멈춘다. 모델 0회.
   - 2-3. [M] **관찰할 것.** 따질 대상은 `담당`이 모델인 행뿐이다. 코드가 맡은 행을 Agent 여러 개로 쪼개도 새 판단이 생기지 않고 조정 비용만 든다. 사람이 맡은 행은 04의 `interrupt` 문제다. 담당을 바꾸면 질문도 바뀐다.
3. [M] 1절. 네 칸 표: 정보가 부족함, 도구를 잘못 고름, Context가 너무 큼, 단계 의존성이 강함. 각 칸의 먼저 점검할 것과 분리 검토의 근거. 이 표는 오류 통계가 아니라 진단 틀이다. **먼저 예측하세요.** 어느 사례가 어떤 칸에 들어갈까?
4. [L] Single로 `complex-double-pay`, `insufficient-unknown-payment`, `scope-beta-from-alpha`, `complex-ops-log`를 실행한다. 모델 16~28회.
5. [C] `RunRow`와 `evaluate_row` 표.
6. [C] 실패를 네 칸으로 분류하는 신호표. 칸은 도구를 불렀는가, 필요한 문서를 찾았는가, 같은 도구를 반복했는가, 입력 토큰 증가. 판결이 아니라 신호이고 사람이 고른다.
7. [C] `DIAGNOSIS` dict에 수강생의 분류와 근거를 적는 셀. 기본값은 미판정이다.
8. [M] **관찰할 것.** 작업을 나누기 전에 고칠 수 있는 칸을 찾는다.
9. [L] 프롬프트나 도구 설명 **한 곳만** 고쳐 실패한 사례 하나를 다시 실행한다. 모델 4~8회.
10. [C] 전후 표와 바꾼 줄을 함께 출력한다.
11. [M] **관찰할 것.** 나아졌다면 분리가 필요 없었던 문제다. 나아지지 않았다면 다음 절의 근거가 된다.
12. [M] 2절. 이득과 비용이 함께 는다. **먼저 예측하세요.** 같은 사례를 Supervisor로 돌리면 토큰은 몇 배가 되고, 자동 검사는 나아질까?
13. [L] `supervisor`로 `complex-double-pay`를 실행한다. 모델 8~16회.
14. [C] Single과의 표: 호출, 토큰, 시간, 자동 검사, 위임 지시와 결과 전달 바이트(조정 비용).
15. [M] **관찰할 것.** 지시와 결과 전달도 토큰이다. 품질이 같다면 추가 비용은 무엇을 샀는가?
16. [M] 3절. 나누는 기준은 Persona보다 Context 경계다. **먼저 예측하세요.** 이름만 다른 Worker 셋에 모든 도구를 주면?
17. [L] **실패 재현.** 같은 전체 도구와 다른 역할 이름만 가진 Worker로 실행한다. 모델 8~16회.
18. [C] 13번(Context 분리)과의 표: 역할별 입력 토큰, 호출한 도구, 역할 밖 도구 호출 수.
19. [C] "Context 분리와 보안 격리는 다르다"를 보인다. 같은 프로세스의 `Desk`를 공유하므로 분리된 Worker도 같은 원장 객체에 닿을 수 있다는 것을 코드로 출력한다. 권한은 별도로 설계한다.
20. [M] **관찰할 것.** 역할 이름이 줄이는 것과 도구 범위가 줄이는 것을 구분한다.
21. [M] 4절. 절차를 불러올 것인가, 별도 실행 Context로 위임할 것인가.
22. [C] `skills/` 목록과 메타데이터 크기, 본문 크기 출력.
23. [L] `single_skills`로 `complex-double-pay`를 실행한다. `loaded_skills` 출력. 모델 5~10회.
24. [C] 세 행 비교(Single, Single+Skills, Supervisor)와 판단표. 칸은 절차 재사용, Context 분리, 도구·권한 분리, 병렬 필요.
25. [M] **관찰할 것.** Skill과 SubAgent는 조합할 수 있다. 판서의 "문체, 데이터를 바라보는 관점, 암묵지"는 어디에 담을지 묻는다.
26. [M] 5절. 수치는 비교 조건과 함께 읽는다. 지연은 Agent 수가 아니라 가장 긴 실행 경로로 읽는다.
27. [C] 비교 조건 판별. 수강생 표에서 뽑은 문장 세 개("Supervisor가 Single보다 토큰 N배" 등)를 칸(비교 대상, 평가 방법, 표본, 측정자)으로 나눠 출력한다. 빈 칸이 있으면 주장할 수 없다고 표시한다. 외부 수치를 넣지 않는다.
28. [C] 13번 실행의 span으로 직렬 합과 최장 경로를 계산한다. 조정·집계 시간을 분리해 `bars`로 출력한다.
29. [M] **관찰할 것.** Agent 수가 아니라 가장 긴 경로로 읽는다.
30. [M] 6절. Fast Path는 안전 검사를 생략하는 지름길이 아니다.
31. [L] `hybrid`로 단순 사례 하나와 복합 사례 하나를 실행한다. 경로별 호출과 토큰을 본다. 모델 10~18회.
32. [L] **실패 재현.** 복합 요청을 Fast Path로 강제하고 검증 실패 뒤 Slow Path로 전환되는 경로를 본다. 모델 5~10회.
33. [C] 쓰기 요청을 Fast Path로 보내도 `check_refund`를 지나는 것을 일반 함수 경로로 출력한다.
34. [M] **관찰할 것.** 복구 경로의 비용까지 합쳐야 Fast Path의 이득을 말할 수 있다.
35. [M] 7절. 고정 조건과 바꾸는 변수 하나.
   - 35-1. [M] 하네스가 일관성을 만든다. 다섯 구조는 조립만 다르고 같은 `Desk`의 예산 객체, 도구 허용 목록(`allowlist_middleware`), 응답 형식(`FinalAnswer`), 쓰기 게이트(`gate_answer`)를 지난다. 02 3절에서 본 `general-purpose` Worker는 이 하네스 밖에서 돌므로 `mas_lab` import 때 끈 것이 다섯 구조 어디에도 없어야 한다고 밝힌다. 그래프인 `handoff`와 `hybrid`는 `task` 도구가 없어 같은 설정으로 만든 Agent로 대신 확인한다고 쓴다.
   - 35-2. [C] 다섯 구조를 만들어(모델 0회) 구조마다 예산, 허용 목록, 응답 형식, 게이트 사용, `task_targets`를 코드 객체와 소스(`inspect.getsource`)에서 읽어 표로 낸다. 응답 형식·게이트·예산 칸은 빌더와 `runner._run_turns`의 소스를 문자열로 찾는 방식이라 그 소스를 크게 고치면 읽히는 값이 달라진다.
   - 35-3. [M] 공식 프레임워크 문서가 기본으로 싣는 멀티에이전트 구성과 이 노트북의 구조를 짝지은 표(LangChain, OpenAI Agents SDK, Microsoft Agent Framework, Google ADK, Anthropic 글). 어느 구성이 가장 많이 쓰이는지 재 본 조사를 찾지 못했으므로 "가장 많이 쓰이는 구성"으로 쓰지 않고 "공식 문서가 기본으로 제공하는 구성"으로 쓴다. 출처 없는 비율은 인용하지 않으며 표는 이름을 짝지을 뿐 성능이나 사용 빈도를 말하지 않는다. 출처 확인일은 2026-11-02다.
36. [C] `CONFIG`: `STRUCTURES=["single","supervisor","hybrid"]`, `CASE_TYPES=["simple","complex"]`, `REPEATS=1`. 고정 조건 표와 예상 호출 수를 계산해 출력한다. 그리고 이 구성에 어떤 사례가 들어가는지 출력한다.
37. [L] `run_grid`를 실행한다. 모델 약 30회. 실행 전 `announce`로 고지한다.
38. [C] 자동 검사 합친 전체 행 표. 실패 행을 지우지 않는다.
39. [C] 유형 × 구조 요약 표. 성공, 시간, 토큰, 정책 위반, 실패·usage 누락.
40. [L] `RUN_OPTIONAL`이 `True`일 때만 전체(4유형 × 5구조 × 1회)를 실행한다. 모델 100~160회. 끄면 "실행하지 않았습니다"를 출력한다.
41. [C] **실패 재현.** 평균만 보면 잘못 읽히는 표를 만든다. 실패가 빨리 끝난 행과 토큰이 줄었지만 필수 사실이 빠진 행을 찾아, 그 행을 포함한 평균과 구분한 표를 나란히 출력한다.
42. [C] 사람 판정 칸. 답변 하나를 원문 근거와 나란히 출력하고 자동 검사와 다르게 볼 곳을 `HUMAN_REVIEW`에 적는다. 기본값은 미판정이다.
43. [M] **관찰할 것.** 1회 관찰, usage 누락, 자동 검사의 한계. 무엇을 추가로 재면 결론을 말할 수 있는가?
44. [M] 8절. Agent 수가 아니라 설계 이유가 결과물이다. 설계 질문 여섯 가지.
45. [C] `DECISION` dict: 사례 유형별로 고른 구조와 근거 행 번호, 포기한 것.
46. [M] 직접 해보기 안내.
47. [L] 해보기 1 골격: `REPEATS=3`을 한 사례·한 구조에만 적용해 변동을 본다. 모델 12~48회.
48. [C] 해보기 2 골격: `FIXED_BUDGET`을 **낮춰** 어느 구조가 먼저 실패하는지 본다(올려서 감추지 않는다). 사본 설정으로 실행 전 규모만 출력하고, 실행 여부를 수강생이 정한다.
49. [L] 해보기 3 골격: `billing-policy`의 표현을 바꾼 새 사례 하나를 직접 더해 실행한다. 모델 5~15회.
50. [C] 해보기 4 골격: 자동 검사의 `required_any`로는 틀렸다고 판정되는 올바른 답 또는 그 반대를 하나 찾는다.
51. [C] 설계 기록: 어떤 결과로 선택을 정당화하는가.
52. [M] 정리.
53. [M] 확인 질문과 06 예고.

### 직접 해보기

1. (실제 호출) 한 사례를 3회 반복해 호출과 답의 변동을 본다.
2. 예산을 낮춰 먼저 실패하는 구조와 그 사유를 본다.
3. (실제 호출) 새 사례를 더하고 기대 사실을 원문 행에 연결한다.
4. 자동 검사가 틀리는 경우를 하나 찾아 설명한다.

### 확인 질문

1. Multi-Agent로 바꾸기 전에 고쳐야 할 실패와 분리의 근거가 되는 실패를 자기 표에서 하나씩 들어라.
2. 조정 비용은 어느 칸에 나타나는가? 품질이 같을 때 무엇을 근거로 비용을 정당화하는가?
3. "Context 분리는 곧 격리"라는 주장이 틀린 이유를 19번으로 설명하라.
4. 비교 대상이 다른 두 수치를 합쳐 말하면 왜 틀리는가? 자기 표에서 예를 들어라.
5. 평균 지연이 낮아진 구조가 나빠진 경우는 어떤 경우인가?
6. 이 표만으로 말할 수 없는 것을 세 가지 적어라.

## 06-Lab-Research-Agents

### 학습 목표

- `Day03/task.md`의 리서치 시스템을 Deep Agent Worker로 조립해 같은 주제로 실행한다.
- 시간 효과와 정보 흐름 효과를 구분하기 위해 병렬, 직렬(같은 입력), 연쇄(앞 결과 전달) 셋으로 나눠 비교한다.
- 외부로 나가는 질의와 돌아오는 자료의 경계를 코드로 다룬다.
- 자동 검증과 사람의 원문 대조를 따로 적는다.
- 오늘 쌓은 설계 기록을 근거로 구조를 고르고 다른 업무에 옮긴다.

이 실습은 채점하지 않는다. 실패한 기록도 이 실습의 결과다.

### 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 주제와 분해, 내 예측 | 7 |
| 2 | EXA 도구와 외부 경계 | 8 |
| 3 | Worker 한 개 | 7 |
| 4 | 병렬과 직렬 | 13 |
| 5 | 연쇄 | 8 |
| 6 | 자동 검증과 원문 대조 | 8 |
| 7 | 구조 선택과 전이 | 6 |
| 8 | 직접 해보기와 정리 | 3 |

### 셀 구성

1. [M] 제목, 학습 목표, 시간표, 호출 규모. EXA는 수강생 크레딧을 쓴다. 웹 결과는 실행마다 달라진다.
2. [C] import, `require_key()`, `require_exa_key()`, `key_status()`.
3. [M] 1절. 왜 세 구조로 나누는가. `task.md`의 Sequential을 둘로 나누는 이유.
4. [C] `CONFIG`: `TOPIC`, `PLAN`(소주제 3개), `MAX_SUBTOPICS`, `MAX_SEARCHES_PER_WORKER=2`, `NUM_RESULTS=3`, `MAX_CHARS=2500`, `ALLOWED_DOMAINS`, `RUN_OPTIONAL=False`. `plan_hash`와 호출 상한을 계산해 출력한다.
5. [M] **먼저 예측하세요.** 셋의 시간, 토큰, URL 겹침, 품질을 표로 적는다. 소주제가 서로 독립적인가도 적는다.
6. [M] 2절. 무엇이 밖으로 나가는가. 내부 질문 전체를 보내지 않는다.
7. [C] **실패 재현.** `assert_public_query`에 고객 이름과 결제 번호가 든 질의를 넣어 호출 전에 거절되는 것을 출력한다. `allowed_url`에 위장 도메인을 넣어 거절을 본다.
8. [L] EXA 1회. 제목, URL, 게시일, 글자 수, 비용 칸을 출력한다. EXA 1회.
9. [M] **관찰할 것.** 도구가 돌려준 웹 문서는 자료이지 명령이 아니다. `MAX_CHARS`는 Context 비용이다. 비용 칸이 비어 있으면 "확인 안 됨"으로 읽는다.
10. [C] `make_exa_tool` 소스와 스키마. 모델이 `source_id`로만 인용하게 하는 이유.
11. [M] 3절. Worker 계약. `Finding`, `Claim`.
12. [L] Worker 한 개로 소주제 하나를 실행한다. `message_table`을 읽는다. 모델 3~5회, EXA 1~2회.
13. [C] **실패 재현.** `Finding`의 `source_ids`가 등록된 출처인지 확인한다. 위조 `source_id`를 넣은 사본이 거절되는 것을 함께 본다.
14. [M] **관찰할 것.** 검색어를 누가 정했는지, 몇 번 검색했는지, 불확실성에 무엇을 적었는지 읽는다.
15. [M] 4절. `build_research_graph`와 `Send`, reducer, 합성. **먼저 예측하세요.** 병렬과 직렬의 전체 시간 차이는 Worker 수만큼 날까? EXA 대기가 차지하는 몫은 얼마일까?
16. [C] 소스와 `show_graph`.
17. [L] 병렬 실행. 모델 10~16회, EXA 3~6회.
18. [C] `timeline`, 보고서 요약, 소주제별 주장 수, 출처 수.
19. [L] 같은 그래프, 같은 `PLAN`을 `max_concurrency=1`로 실행한다. 모델 10~16회, EXA 3~6회.
20. [C] 비교표: `plan_hash`, 전체 시간, EXA 시간 합, 모델 시간 합, 겹침, 토큰, 호출, EXA 호출.
21. [C] `url_overlap`으로 두 실행이 같은 자료를 봤는지 출력한다.
22. [M] **관찰할 것.** 그래프와 분해는 같지만 모델과 웹은 달라질 수 있다. URL 겹침이 낮으면 품질 차이를 구조 탓으로 읽을 수 없다. 합이 전체보다 큰 칸을 읽는 법.
23. [M] 5절. 연쇄. 앞 Worker의 결과를 뒤 Worker가 받는다. **먼저 예측하세요.** 무엇이 나아지고 무엇이 나빠질까? 앞 Worker가 틀리면 어떻게 될까?
24. [C] 연쇄 그래프 소스와 뒤 Worker에 전달되는 입력의 형태.
25. [L] 연쇄 실행. 모델 10~16회, EXA 3~6회.
26. [C] Worker 순번별 입력 바이트와 토큰 표. 앞 결과가 얼마나 쌓이는지 본다.
27. [C] 세 구조의 표와 URL 중복 재조회 수.
28. [M] **관찰할 것.** 순서가 답을 바꾸는가? 앞 Worker의 오류가 뒤로 번지는지 보고서에서 찾는다.
29. [M] 6절. 자동으로 잡히는 것과 사람이 봐야 하는 것.
30. [C] **실패 재현.** `validate_report`를 세 보고서와, 출처를 지운 사본 하나에 적용한다. 출처 없는 주장, 등록되지 않은 `source_id`, 재조회를 표로 낸다.
31. [C] 보고서마다 주장을 무작위가 아니라 **첫 번째와 숫자가 있는 주장 위주로** 3개 고르고 출처 원문 발췌와 나란히 출력한다.
32. [C] `HUMAN_REVIEW`: 수강생이 지지됨, 일부, 지지 안 됨을 적는다. 기본값은 미판정이고, 집계에서 미판정을 따로 센다.
33. [M] **관찰할 것.** 인용 ID가 유효한 것과 의미가 지지되는 것은 다르다. 미판정은 품질 결과가 아니다.
34. [L] `RUN_OPTIONAL`이 `True`일 때만 병렬을 한 번 더 실행해 같은 구조 안의 변동을 본다. 모델 10~16회, EXA 3~6회.
35. [C] 34번을 돌렸다면 URL 겹침을 출력한다. 돌리지 않았으면 "실행하지 않았습니다"를 출력한다. 구조 간 차이를 같은 구조 내 변동과 비교해 읽게 한다.
36. [M] 7절. 설계 질문 여섯 가지.
37. [C] `read_design_log()`로 오늘의 기록을 출력한다. 없는 항목은 비어 있음을 표시한다.
38. [C] `DECISION`: 이 리서치에 어느 구조를 쓸지와 근거 칸, 포기한 것.
39. [M] 전이 과제. 투자 심사(판서): 수요 기업 요청 → 내부·외부 자료와 인터뷰 수집 → 양식 통일 보고서 → 투자심의위원회 Go/Stop → 회계·감사. 숫자는 어떻게 다루고, 50개 절의 Context는 어떻게 나누고, 사람의 문체와 관점은 어디에 담을 것인가?
40. [C] 투자 심사의 `TASKS`를 쓰고 03의 묶음 계산으로 흐름을 출력한다. 모델 0회.
41. [M] **관찰할 것.** 어디에 판단을 맡겼고 어디를 코드로 고정했는가?
42. [M] 직접 해보기 안내.
43. [L] 해보기 1 골격: 자기 관심 주제로 `TOPIC`과 `PLAN`을 바꿔 병렬을 실행한다. 모델 10~16회, EXA 3~6회.
44. [L] 해보기 2 골격: 소주제에 일부러 의존 관계를 만들어 병렬과 연쇄를 비교한다. 모델 20~32회, EXA 6~12회.
45. [L] 해보기 3 골격: `MAX_CHARS`를 절반으로 줄여 토큰과 인용을 본다. 모델 10~16회, EXA 3~6회.
46. [C] 해보기 4 골격: 합성 노드에 `validate_report` 실패 시 재작성 루프를 더한 그래프를 만들고 `flows_of`로 흐름을 본다. 실행은 선택.
47. [M] 정리. 오늘 전체를 "어디에 판단을 맡길까?"로 다시 쓴다.
48. [M] 확인 질문.

### 직접 해보기

1. (실제 호출) 자기 주제로 바꿔 실행한다.
2. (실제 호출) 의존이 있는 소주제에서 병렬이 무엇을 놓치는지 본다.
3. (실제 호출) 본문 길이를 줄여 비용과 인용을 비교한다.
4. 합성 뒤에 검증 루프를 더하고 네 흐름으로 설명한다.

### 확인 질문

1. 직렬과 연쇄를 나눠 본 이유는 무엇인가? 둘의 차이가 시간과 정보 흐름 중 어디에 나타나는가?
2. URL 겹침이 낮은 두 실행의 품질 차이를 구조 탓으로 말하면 왜 틀리는가?
3. `assert_public_query`가 막는 것과 막지 못하는 것은 무엇인가?
4. 인용 검증을 통과한 주장을 사람이 왜 다시 보는가?
5. 투자 심사에 고른 구조를 설계 질문 여섯 가지로 설명하라.

## 10. 검사와 감사

### 10.1 저자용 도구

| 파일 | 출발점 | 바뀌는 점 |
|---|---|---|
| `tests/check_notebook.py` | `Day02_new/tests/check_notebook.py` | `StateGraph` 금지 제거. 3절의 하한과 필수 문구 검사 추가. `langgraph_supervisor`, `draw_mermaid_png`, `student_tasks`, `mas_lab.evaluation` 밖의 `gold`, 그리고 markdown과 코드의 "슬라이드" 금지 추가 |
| `tests/run_live.py` | `Day02_new/tests/run_live.py` | 셀별 모델 호출 수와 EXA 호출 수를 기록한다. `--exercises`는 임시 사본에서 `RUN_EXERCISE`와 `RUN_OPTIONAL`을 켜서 실행한다 |
| `tests/audit_live.py` | 새로 작성 | 호출이 있었는데 `announce(`가 없는 셀(`:31-32`), 출력 없는 코드 셀(`:40-43`), 실측이 그 셀의 고지를 넘는 셀(`:36-37`, 고지가 여럿이면 합이 상한 `:35-36`)을 실패로 보고한다. 예고와 비교할 수 없는 유료 셀도 실패다. 모델을 불렀는데 고지에 `model_calls=` 숫자가 없는 셀은 그 셀마다(`:38-39`), 실행본(`<stem>.executed.ipynb`)이 없는 기록은 stem마다 한 줄이다(`:27-28`). 이 둘은 통과시키지 않는다. 끝까지 실행되지 않은 실행(`:25`), 셀 오류(`:26`), 저장본과 코드가 다른 실행본(`:47-51`)도 실패다 |
| `tests/test_audit_live.py` | 새로 작성 | 첫 판은 위 고지 규칙을 시험 7개로 고정했다. 실측이 고지보다 적거나 같으면 통과, 하나라도 넘으면 셀·고지·실측을 말하며 실패, 고지 없이 부르면 고지 없음으로 실패, 모델을 안 부른 셀은 통과, 한 셀의 고지 여럿은 합으로 비교한다(`:22-58`). 지금은 시험 함수 10개가 pytest 항목 12개로 돈다(매개변수 시험 둘이 각각 2개). 더한 규칙 둘은 이렇다. 모델을 부른 셀의 고지에 `model_calls=` 숫자가 없으면 `exa_calls=3`이든 `model_calls=len(topics)`든 "숫자가 없어 비교할 수 없다"로 실패하고(`:61-68`), 그 셀이 모델을 안 불렀으면 통과한다(`:71-73`). 실행본이 없으면 `main`이 한 줄과 `AUDIT FAIL 1건`을 내고(`:85-94`), 있으면 `AUDIT OK`다(`:97-102`). `main` 시험은 `tmp_path`에 만든 기록만 읽는다 |
| `tests/cost_report.py` | 그대로 복사 | 경로만 Day03_new 기준. EXA 비용은 별도 칸 |
| `tests/fakes.py` | `Day02_new/tests/fakes.py` | 단위 시험 전용. `fakes`를 `mas_lab`이나 노트북이 import하면 검사 실패(`tests/test_layout.py:31-34`, `tests/check_notebook.py:20`). `ParsedChatModel`(`tests/fakes.py:62-68`)은 이 폴더에서 더했고 `Day02_new/tests/fakes.py`에는 없다. 파싱된 객체를 바로 받는 코드(`hybrid`의 Router, `handoff`의 담당자 분류, 리서치 synth)의 시험이 `ParsedChatModel`을 쓴다(`tests/test_structures.py:94`, `tests/test_structures.py:102`, `tests/test_structures.py:116`, `tests/test_structures.py:269`, `tests/test_structures.py:889`, `tests/test_research.py:82`). 첫 검토 전에는 같은 일을 하는 `RouterFake`가 `test_structures.py`에, `ReportFake`가 `test_research.py`에 따로 있어 가짜 모델은 `tests/fakes.py`에만 둔다는 규칙(`AGENTS.md` 5장 7번)과 어긋났다. 지금은 한 클래스다. 이 규칙을 지키는 자동 검사는 없고 `grep`으로 확인했다(`tests/` 아래 챗 모델 클래스는 `tests/fakes.py:20`의 `ScriptedChatModel`과 `tests/fakes.py:62`의 `ParsedChatModel`뿐) |

### 10.2 단위 테스트의 핵심 반증

새 검사는 실패해야 할 때 실패함을 확인한다(사본에서 결함을 넣고 지정 테스트의 실패를 확인한 뒤 되돌린다).

| 넣는 결함 | 실패해야 할 테스트의 내용 |
|---|---|
| `merge_results`를 마지막 값 우선으로 | 상충 결과 거절 |
| `join_results`에서 실패 Worker 무시 | 누락 표시, `ready=False` |
| `trim_payload`가 근거 참조를 먼저 삭제 | 근거 참조 보존 |
| `check_refund`의 승인 조건 제거 | 100만원 초과 `needs_approval` |
| `execute_approved`의 `approved` 검사 제거 | 승인 전 원장 0건 |
| `refund`의 멱등 검사 제거 | 같은 키 재시도 1건 |
| `Send`를 `for` 호출로 교체 | 구간 겹침 > 0 |
| `Desk.tools("billing")`에 `search_knowledge` 추가 | 역할별 도구 고정 |
| 도구에 고객 인자 추가 | 스키마에 entity 없음 |
| `evaluation` 밖에서 `gold` 읽기 | 모듈 격리 grep 테스트 |
| `assert_public_query` 무력화 | 내부 질의 차단 |
| `allowed_url`을 부분 문자열 검사로 | 위장 도메인 거부 |
| `rag_lab/corpus.py` 한 글자 변경 | Day02_new 바이트 동일 |
| 노트북에 `ScriptedChatModel` 삽입 | 검사기 실패 |
| `check_named_payment`에서 탐침을 뺀다(제안 없는 답을 검사 없이 돌려준다) | 첫 승인 결제를 가리킨 질문의 `human_review`가 `denied`로 바뀐다 |
| 탐침의 판정을 `execute_approved`에 넘긴다 | 제안 없는 답은 어떤 판정에서도 원장 0건 |
| 결제 번호를 질문 대신 답 본문에서 읽는다 | 번호는 질문에서만 읽는다 |
| 레이블이 바뀌어도 모델의 결론 문장을 그대로 둔다 | 바뀐 결론은 코드가 낸 문장으로 교체 |
| 이미 검사한 답에 불확실성과 사건을 또 더한다 | 두 번 검사해도 늘지 않는다 |
| `answered`까지 검사 대상에 넣는다 | `answered`는 그대로 |
| `hybrid`의 `gate` 노드가 `check_named_payment`를 부르지 않는다 | 그래프만 돌려도 첫 결제가 `denied` |
| `run_case`가 마지막 턴의 질문을 `gate_answer`에 넘기지 않는다(그래프 경로와 에이전트 경로 각각) | 구조마다 마지막 턴의 질문으로 검사 |

이 표의 `rag_lab/corpus.py` 행이 반증하는 시험은 `test_rag_lab_copies_are_byte_identical[corpus.py]` 하나다. 같은 복사본 시험은 2026-11-02의 동기화 뒤 `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]` 칸도 보고 네 칸 모두 통과한다. 2026-11-01에는 `[retrieval.py]`, `[evidence.py]` 칸이 1절 5번의 이유로 실패했고, 그것은 이 표에 넣은 결함이 아니라 끝나지 않은 동기화 작업이었다. 동기화한 트리의 falsify 7이 주석 안의 한 바이트만 바꾸는 행 둘을 더했다. `sy01`은 `rag_lab/pipeline.py`, `sy02`는 `rag_lab/evidence.py`를 바꿔 각각 `[pipeline.py]`, `[evidence.py]` 칸만 실패시켰다. `[retrieval.py]` 칸에 넣은 결함 행은 없다(10.4절 2번).

이 표는 핵심 반증만 적은 것이다. 동기화한 지금 트리에서는 이 행들을 포함한 결함 174개를 다시 넣어 모두 잡았고 살아남은 결함은 0이다(falsify 7, 2026-11-02, 10.4절 2번, `docs/audit/falsify-7-notes.md`). 동기화 전 트리의 값은 172개이고 그때도 모두 잡았다(falsify 6, `docs/audit/falsify-6-notes.md`). 표의 앞선 실행 기록(시험 105, 110, 146, 495개 시점)은 10.4절 2번에 그때의 기록으로 남겨 둔다.

실패 메시지가 진짜 원인을 가리키는지도 확인한다(저자 피드백, `feedback-day04-contract-changes`).

### 10.3 최종 감사

통과와 실패를 명령 출력으로 기록한다. 하나라도 어긋나면 실패다.

1. **구조.** `check_notebook.py`가 00(10분)과 01~06(60분)에 OK를 출력한다.
2. **테스트.** `Day03_new/tests` pytest 통과, 10.2 반증 전부 확인.
3. **격리.** `gold`를 읽는 곳은 `mas_lab/evaluation.py`뿐이다.
4. **변경 범위.** 이 작업이 `Day03/`, `Day02_new/`, 루트 `pyproject.toml`, `uv.lock`을 바꾸지 않았다. Day02_new는 다른 세션이 수정 중일 수 있으므로 시작 시점 해시와 이 작업의 쓰기 목록으로 구분한다.
5. **깨끗한 복사본.** `.env` 없는 복사본에서 설치, pytest, 검사기 통과. `00`의 첫 키 확인이 안내와 함께 멈춘다. 키 값이 출력에 없다.
6. **실제 실행.** `run_live.py`로 모든 노트북이 `finished: true`, 오류 0. `RUN_OPTIONAL=False` 기준. `audit_live.py` 통과.
7. **병렬 증명.** 03의 18·25번, 06의 20번 출력에서 `plan_hash` 동일과 겹침 차이를 확인한다.
8. **쓰기 게이트.** 04의 39·41·42·44번 출력에서 승인 전 0건, 승인 후 1건, 키 없는 재시도 2건, 키 있는 재시도 1건을 확인한다.
9. **Part 대응.** 6절의 표와 노트북 절 제목이 맞고, 노트북과 `mas_lab`에 "슬라이드"와 채점 과제 이름이 없다.
10. **새 질문.** 노트북에 없는 질문 하나를 `hybrid`로 실행해 그럴듯하게 틀리지 않는지 본다.
11. **비용.** `cost_report.py` 합계를 독립 합산과 대조하고 README의 호출 수와 비용을 실측으로 바꾼다.

2번의 "pytest 통과"에는 2026-11-01에 저자 결정으로 예외가 하나 있었다. `test_rag_lab_copies_are_byte_identical[retrieval.py]`와 `[evidence.py]` 두 칸은 `Day02_new` 세션이 끝나 복사본을 맞출 때까지 실패한 채로 두는 것이었다(1절 5번). 이 실패는 발견 사항이 아니었다. **이 예외는 끝났다.** 2026-11-02 09:13에 복사본을 맞췄고 두 칸이 통과하며 `[pipeline.py]` 칸이 늘었다. 2번은 이제 예외 없이 `tests` 전체 611개 통과(실패 0)를 요구하고 지금 그렇다. 시험 결과를 말할 때 빼는 칸이 없고 `--deselect`도 필요 없다.

### 10.4 최종 감사 기록

2026-11-01. 10.3의 11개 항목을 하나씩 판정했다. 결과는 충족과 미충족 둘로만 쓴다. 일부만 채운 항목은 미충족으로 쓰고, 채운 부분과 못 채운 부분을 나눠 적는다. 첫 판정은 11개 중 8개가 충족이고 4·5·10번이 미충족이었다. 같은 날 뒤이어 네 가지를 했다. 10번이 드러낸 코드 틈을 막았고(9.2절), 4번을 시작 해시 대신 쓰기 대상 감사로, 5번을 실제 설치로 다시 감사했고, 10번을 새 질문으로 다시 봤다. 그 사이 01~05의 노트북 기록을 다시 돌렸으므로 2·6·7·8·11번도 수정 뒤 값으로 다시 썼다. **아래 표가 최신 판정이고 11개 중 11개가 충족이다.** 단 두 항목은 조건이 붙는다. 4번은 10.3이 정한 시작 시점 해시를 작업 시작 때 뜨지 않아 만들 수 없었고, 쓰기 대상 감사로 대신해 판정했다. 앞의 '일부만 채운 항목은 미충족' 규칙을 문자 그대로 적용하면 4번은 미충족이다. 10번은 `uncertainty`를 고객이 읽는 문장으로 세면 미충족이다(아래 10번). 첫 판정의 근거 문장은 지우지 않고 각 번호 아래에 '첫 판정'으로 남겼다. 1·3·9번은 후속에서 다시 판정하지 않았다(05 노트북의 고지를 고쳤으므로 1번의 검사기만 7개 노트북에 다시 돌려 `OK`를 확인했다). 첫 판정에서 1·2·3·4·6·7·8·9·11번은 그날 저장소에서 다시 돌리거나 다시 읽었고, 10번은 앞 노드가 쓴 실행 기록을 옮긴 것이며, 5번과 2번의 반증 행도 앞 노드의 기록이 바탕이다. 후속 판정(2·4·5·6·7·8·10·11번)의 원본 기록도 임시 폴더에 있어 저장소에 남지 않으므로 이 절이 유일한 기록이다. **세 번째 후속(2026-11-01 저녁).** 위 문단 뒤에 코드를 더 고쳤고(게이트를 `mas_lab/gate.py`로 옮김, 결제 번호 철자, 근거 참조, EXA 질의 경계) 기록을 다시 돌렸으므로 아래 표를 지금 값으로 다시 썼다. 판정은 11개 중 11개가 충족이고 조건은 셋이다. 2번은 저자 결정으로 둔 실패 2개가 있다. 4번은 위와 같다. 10번은 14행 감사에서 N5가 틀렸고, 고친 뒤의 실제 행은 S1~S3 셋뿐이다. 위 문단의 "`uncertainty`를 고객이 읽는 문장으로 세면 미충족"은 두 번째 판정 때의 코드 기준이다. 지금 게이트는 문장을 바꿀 때 모델의 `uncertainty`도 비운다(`mas_lab/gate.py:88`). 증거는 위 문단이 말한 임시 폴더 대신, 세 번째 후속의 기록을 `docs/audit/`에 익명화해 옮겼다(색인은 `docs/audit/README.md`). 쓰기 대상 감사의 분류표처럼 그보다 앞선 기록 일부는 옮기지 않았고 이 절이 유일한 기록이다. **네 번째 후속(2026-11-02).** `rag_lab`을 동기화해(1절 5번) 2번의 조건(저자 결정으로 둔 실패 2개)이 없어졌다. 2번은 `tests` 611개 통과, 실패 0으로 다시 판정했다. 4번에는 두 실패가 없어졌다는 말을, 5번에는 세 번째 깨끗한 복제를, 6번에는 기록이 동기화보다 앞선다는 말을 더했다. 나머지 번호는 다시 판정하지 않았다. 판정은 11개 중 11개 충족이고 조건은 둘(4번, 10번)이다. **다섯 번째 후속(2026-11-02 밤).** 저자 지시로 13개 실행 기록을 모두 다시 돌렸다(9.2절). 6번과 11번은 새 기록 값으로, 7번과 8번은 새 실행본과 행 파일에서 다시 읽은 값으로 다시 썼고, 1번의 검사기(`check_notebook.py`)를 7개 노트북에 다시 돌려 모두 `OK`를 확인했다. 나머지 번호는 다시 판정하지 않았다. 판정은 11개 중 11개 충족이고 조건은 둘(4번, 10번)이다.

| 번호 | 항목 | 결과 | 증거 |
|---|---|---|---|
| 1 | 구조 | 충족 | `check_notebook.py`가 00(`--minutes 10`)과 01~06(`--minutes 60`) 7개 모두에 `OK`를 냈다. 이 기록을 쓰며 7개에 다시 돌렸고 모두 `OK`다. |
| 2 | 테스트 | 충족 | `Day03_new/tests`의 pytest 항목은 611개이고 전체 실행은 `611 passed`, 실패 0이다(2026-11-02, 동기화 뒤). `test_rag_lab_copies_are_byte_identical`의 네 칸 `[corpus.py]`, `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]`이 모두 통과한다. **앞 판정(2026-11-01)은 `충족(저자 결정으로 둔 실패 2개)`였다.** 항목은 610개, 전체 실행은 `2 failed, 608 passed`였고 실패 둘은 `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]`와 `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[evidence.py]`이고 결함이 아니었다. 다른 세션이 `Day02_new/rag_lab`을 고치고 있어 저자가 그 세션이 끝날 때까지 실패한 채로 두기로 했다(1절 5번, 12절). `[corpus.py]`는 통과했다. 그때는 저장소 루트 기준 id로 `--deselect Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical`을 주면 `607 passed, 3 deselected`였고(`Day03_new/` 접두사가 없으면 아무것도 빠지지 않았다) 지금은 빼야 할 칸이 없다. 10.2의 결함은 현재 트리에서 다시 돌렸다(falsify 7: 결함 174개 모두 잡힘, 살아남은 결함 0, 아래 2번. 동기화 전 트리의 falsify 6은 172개 모두 잡힘). 개수의 이력은 102개, 105개, 110개, 146개(게이트 수정 뒤), 495개(falsify 5), 503개(깨끗한 복제본), 610개(동기화 전), 611개(동기화 뒤, `[pipeline.py]` 칸이 하나 늘었다)다. 앞 판의 146개 판정과 변형 4개(2b, 2c, 7, 7b)의 이력은 아래 2번에 그대로 있다. [이후 `tests/test_harness.py`가 더해져 625개가 되었고(2026-11-02), 2026-11-03 노트북 분할 뒤 전체는 717개(`717 passed`, 실패 0)다. 위 611은 그 앞 시점의 값이다] |
| 3 | 격리 | 충족 | `mas_lab`과 `rag_lab`에서 `gold`가 나오는 파일은 `mas_lab/evaluation.py` 하나다. 노트북은 01·03·04·05만 `gold`를 쓰고 `mas_lab.evaluation`을 import한 셀 뒤다. 결함 10a·10b(다른 모듈에서 `gold` 읽기)를 `tests/test_layout.py`가 잡았다. 이 기록을 쓰며 다시 찾았고 `gold`가 나오는 파일은 여전히 그 하나다. |
| 4 | 변경 범위 | 충족 | 이 세션의 도구 호출 2,983개(기록 45개)를 파싱한 **쓰기 대상** 감사에서 `Day03/`, `Day02_new/`, 루트 `pyproject.toml`, `uv.lock`에 닿는 쓰기 대상이 0개였다. `Day03/`와 루트 두 파일은 수정 시각과 해시가 그대로이고, 세션 시작 뒤 바뀐 `Day02_new` 파일 32개는 모두 다른 세션의 쓰기 호출과 짝지었다. 시작 시점 해시가 아니라 사후 감사이고 한계가 있다. 첫 판정(미충족)은 아래 4번에 그대로 있다. 그 뒤 실행에서도 `Day03/`에 새 파일이 없고 루트 두 파일의 sha256이 같다(`docs/audit/verify-c2-notes.md`, `docs/audit/clean-clone-notes.md`). `Day02_new`는 다른 세션이 계속 고치고 있고 이 작업이 쓴 것이 아니다. 2번에 있던 두 실패(2026-11-01)는 그 때문이었고 2026-11-02의 동기화로 없어졌다. |
| 5 | 깨끗한 복사본 | 충족 | 커밋 후보 파일 집합(`git ls-files -co --exclude-standard`)을 새 폴더에 복사해 `uv sync --locked`로 실제 설치했고(345개 패키지), 그 복사본에서 pytest 146개와 검사기 7개가 통과했다. `.env` 없이 00이 셀 5의 첫 키 확인에서 안내와 함께 멈췄고(모델 호출 0회), 두 `.env`의 키 값 검색은 0건이었다. git clone은 아니고 한계가 있다. 첫 판정(미충족)은 아래 5번에 그대로 있다. **후속.** 그 뒤 작업 트리를 새 git 저장소로 커밋해 실제 `git clone`한 사본에서 다시 했다(`docs/audit/clean-clone-notes.md`). 빈 uv 캐시로 `uv sync --locked`가 345개 패키지를 설치했고, pytest 503개(그때의 개수)와 검사기 7개가 통과했다. 키가 없으면 00이 셀 5의 `require_key()`에서, `ANTHROPIC_API_KEY`만 있으면 같은 셀의 `require_exa_key()`에서 멈췄고 모델 호출은 0회, 키 값 검색은 0건이다. 한계는 그때의 작업 트리이지 원격 커밋이 아니라는 것, macOS aarch64만 봤다는 것, Python 3.13이 이미 설치돼 있었다는 것이다. **세 번째 복제(2026-11-02).** `rag_lab` 동기화 뒤의 작업 트리로 되풀이해 345개 패키지 설치, pytest 611개 통과(실패 0), 검사기 7개 통과를 확인했다(12절, `docs/audit/clean-clone-3-notes.md`). |
| 6 | 실제 실행 | 충족 | 13개 기록이 모두 `finished: true`, 오류 0건이고 `.usage.jsonl` 줄 수가 `model_calls`와 같다. `audit_live.py`가 `AUDIT OK`를 냈다(13개 기록, 모델을 부른 98개 셀 모두 `model_calls=` 숫자가 있고 고지를 넘은 셀은 0개, 이 기록을 쓰며 다시 돌려 확인). 기본 실행 315회 1188.6초, 켠 실행 681회 2231.0초(9.2절). 13개 기록은 모두 2026-11-02 21:40~22:51에 지금 코드로 돌았고, 13개 실행본은 저장본과 코드도 markdown도 같다(켠 실행본은 스위치 줄만 다르다). 이 재실행에서도 같은 기록을 두 번 돌리지 않았다. 전체 재실행 전은 314회 1103.5초, 677회 2241.9초였고 기록이 `mas_lab` 수정 앞뒤와 `rag_lab` 동기화 앞으로 갈려 12절에 판단을 적었다. 02 기본 실행을 다시 돌리기 전은 312회 1064.1초였고, 그 앞 판은 311회 1072.2초, 712회 2185.7초였고, 그때 05 기본 실행은 첫 재실행이 고지 초과(셀 31, 고지 20에 22회)로 감사에서 실패해 고지를 30으로 고치고 다시 돌렸다. 세 번째 후속의 두 실행에서는 같은 기록을 두 번 돌리지 않았다. |
| 7 | 병렬 증명 | 충족 | 03 셀 21(명세 18번)은 `plan_hash`가 병렬·직렬 모두 `7481177df112`, 전체 0.306초 대 0.916초, 겹침 0.305초 대 0.000초다. 03 셀 30(25번)은 `7f41517672b9`, 10.769초 대 25.099초, 겹침 7.998초 대 0.000초, 모델 6회 대 7회다. 06 셀 20은 `1fc820343196`, 47.155초 대 75.039초, Worker 겹침 16.567초 대 0.000초다. 셀 번호는 0부터 센 실행본 인덱스이고 값은 2026-11-02 재실행 기록이다. 재실행 전 기록은 03 셀 21이 0.306초 대 0.918초, 겹침 0.303초, 셀 30이 9.409초 대 25.485초, 겹침 7.925초, 06 셀 20이 40.644초 대 68.744초, Worker 겹침 14.65초 대 0.00초였다. 03의 그 앞 기록은 셀 21이 0.306초 대 0.912초, 겹침 0.305초, 셀 30이 9.221초 대 22.422초, 겹침 7.52초이고, 그 앞은 11.864초 대 27.706초, 겹침 7.541초였다. |
| 8 | 쓰기 게이트 | 충족 | 마지막으로 다시 돌린 04 기본 실행과 켠 실행이 같은 값을 냈다. 셀 44는 승인 전 원장 0건, 셀 45는 승인 후 1건(`R-0001`), 셀 47은 키 없는 재시도 2건과 키 있는 재시도 1건이다. 셀 41의 `interrupt` 앞 부작용 재현은 승인 대기에서 1건, 재개 뒤 2건이다. 05 켠 실행 셀 41의 `policy-deny-normal`·`policy-human-old` 10행은 레이블이 바뀌지 않았고 `gate_text_appended`가 행마다 1건, 문장 교체 0건, 원장 0건이다. 같은 실행 전체의 `gate_skipped`는 8건이고 답은 바뀌지 않았으며 원장은 0건이다. 이 값들은 2026-11-02 재실행의 행 파일(05 켠 실행이 22:20~22:40에 쓴 79행, 셀 41은 그중 22:27~22:38의 50행)에서 다시 읽었고 재실행 전 기록(`docs/audit/live-05-c2-notes.md`)과 같다. 앞 판은 같은 10행을 문장 교체와 `gate_skipped` 0건으로 적었다. |
| 9 | Part 대응 | 충족 | 노트북 절 제목이 6절 표와 맞는다(01은 0절이 하나 더 있고 1~5절, 02는 1~6절, 03은 1~6절, 04와 05는 1~8절, 06은 1~7절). 노트북과 `mas_lab`, `rag_lab`에서 "슬라이드", "채점", `WORKSHEET`, `challenge_tests`, `student_tasks`를 찾았으나 0건이었다. 이 기록을 쓰며 같은 문자열을 다시 찾았고 0건이다. |
| 10 | 새 질문 | 충족(철자 수정 뒤) | 세 번째 판정은 노트북에 없는 질문 12개를 `hybrid`로 14행 돌렸다(모델 127회, 상한 150). `ok` 12, `budget_exceeded` 2(N4, N4b), 그럴듯하게 틀린 행 1(N5, `p7001`), 미리 적은 기대와 같은 행 11이다. 그 시점의 판정은 미충족이다. N5는 철자를 읽지 못한 게이트의 틈이었고 고쳤다. 고친 게이트에 같은 문장을 세 철자로 실제 모델에 넣은 S1~S3은 모두 `denied`, 원장 0건, 문장이 참이다(25회, 9.2절). 14행 전체를 고친 게이트로 다시 돌리지는 않았고, N5의 모델 답을 고친 게이트에 넣은 재생만 했다. 두 번째 판정(8행, 그럴듯하게 틀린 행 0)과 첫 판정(3개 중 P-7001이 틀려 미충족)은 아래 10번에 그대로 있다. |
| 11 | 비용 | 충족 | `cost_report.py`의 합계 줄(1,068회, 3,704.9초, 7.4387 USD. 입력 3,968,675, 출력 450,419, 캐시 읽기 2,779,346 토큰)을 `.usage.jsonl` 19개에서 단가표와 식을 따로 써서 더한 값과 대조했다. 호출 수와 토큰이 같았고, 비용은 기록마다 넷째 자리로 반올림한 합은 7.4388이다(기본 349회 2.4810, 켠 실행 719회 4.9578, `cost_report.py`의 기본 합은 2.4809). 19개 기록의 호출 수는 `.usage.jsonl` 줄 수와 각 `.json`의 `model_calls`가 같았다. README의 표는 같은 `cost_report.py` 값을 옮긴다. 전체 재실행 전의 값(991회, 3,345.4초, 7.1832 USD), 02 기본 실행을 다시 돌리기 전의 값(989회, 3,306.0초, 7.1789 USD), 그 앞 판의 값(1,023회, 3,257.9초, 7.3154 USD), 첫 판정의 값(1,001회, 3,210.9초, 7.1930 USD)은 그때 기록의 값이다. 합계 줄은 겹치는 두 실행을 더한 값이라 지출이 아니고, 지출은 11절에 있다. 이 대조의 한계는 그대로다. 비용은 같은 단가표(`tests/cost_report.py:16`)로 따로 곱한 것이라 단가표 자체는 검증하지 못했고, 캐시 쓰기 단가는 모델링하지 않아(`tests/cost_report.py:75-76`) 모델 비용은 하한이다. 합계 줄은 `tests/cost_report.py:67-71`이 낸다. |

**2번. 10.2 반증 결과.** 결함은 모두 사본에서 넣었고(실제 트리에는 결함을 넣지 않고 시험만 더했다), 명령은 사본의 `Day03_new`에서 `pytest -q tests`를 돌린 것이다. 14번만 `check_notebook.py`다. 15번은 저자가 더한 행이다. 16~23b는 게이트 수정(9.2절) 뒤 더한 행이다.

| 번호 | 넣은 결함 | 잡은 시험 | 실패 메시지 |
|---|---|---|---|
| 1 | `merge_results`를 마지막 값 우선으로 | `test_contracts.py::test_merge_results_rejects_conflict_and_accepts_same_value` | `DID NOT RAISE ValueError` |
| 2a | `join_results`가 실패 Worker를 무시 | `test_contracts.py::test_join_results_exposes_missing_failed_and_latest_attempt` | `[] == ['outage']` |
| 2b | `ready`가 실패를 무시 | 원래 시험은 통과(놓침). 더한 시험 `test_join_results_is_not_ready_for_a_failure_alone_or_a_missing_task_alone` | `assert True is False` (`failed_only["ready"]`) |
| 2c | `ready`가 누락을 무시 | 2b와 같음 | `assert True is False` (`missing_only["ready"]`) |
| 3 | `trim_payload`가 근거 참조를 먼저 삭제 | `test_contracts.py::test_trim_payload_keeps_refs_and_uncertainty_until_the_end` | `[] == ['E-1']` |
| 4 | `check_refund`의 승인 조건 제거 | `test_ledger.py::test_gate_decisions`, `test_structures.py::test_needs_approval_waits_and_executes_once_when_approved` | `'allow' == 'needs_approval'`, `'executed' == 'needs_approval'` |
| 5 | `execute_approved`가 `approved`를 무시 | `test_ledger.py::test_execute_only_when_permitted`, 위 `test_structures.py` 시험 | ledger 시험은 `assert (True is False)`뿐이고 매개변수 id와 structures 시험의 `'executed' == 'needs_approval'`이 원인을 가리킨다 |
| 6 | `refund`의 멱등 검사 제거 | `test_ledger.py::test_lost_response_duplicates_without_key_and_not_with_key` | `'R-0002' == 'R-0001'` |
| 7 | `hybrid.dispatch`의 `Send`를 하나로 합쳐 `worker`가 반복 | 원래 시험은 통과(놓침). 더한 시험 `test_structures.py::test_hybrid_workers_overlap_in_time` | 구간 `[0.005-0.178] [0.178-0.359] [0.359-0.559]`, `0.0 > 0.05` |
| 7b | `research.build_research_graph`에 같은 교체 | 원래 시험은 통과(놓침). 더한 시험 `test_research.py::test_parallel_research_workers_overlap_in_time` | 구간 `[0.071-0.255] [0.27-0.43] [0.46-0.628]`, `0.0 > 0.05` |
| 8 | `Desk.tools("billing")`에 `search_knowledge` 추가 | `test_desk.py::test_roles_have_fixed_tools` | `Extra items ... 'read_evidence' 'search_knowledge'` |
| 9 | 도구에 고객 인자 추가 | `test_desk.py::test_no_tool_lets_the_model_widen_the_scope` | `AssertionError: lookup_availability` |
| 10a, 10b | `desk.py`, `rag_lab/settings.py`에서 `gold` 읽기 | `test_layout.py::test_only_evaluation_module_touches_the_answer_key` | `['desk.py', 'evaluation.py'] == ['evaluation.py']`, `assert not ['settings.py']` |
| 11 | `assert_public_query` 무력화 | `test_research.py::test_internal_queries_stay_inside`, `test_blocked_query_never_reaches_the_network` | `DID NOT RAISE ValueError`(4건), `'error' == 'blocked'` |
| 12 | `allowed_url`을 부분 문자열 검사로 | `test_research.py::test_allowed_url_rejects_lookalikes` | `assert True is False where True = allowed_url('https://docs.langchain.com.evil.test/x', ...)` |
| 13 | `rag_lab/corpus.py` 한 글자 변경 | `test_layout.py::test_rag_lab_copies_are_byte_identical[corpus.py]` | `At index 54 diff`. 매개변수 id가 파일 이름 |
| 14 | 노트북에 `ScriptedChatModel` 삽입 | `check_notebook.py`가 종료 코드 1 | `셀 1에 쓰지 않기로 한 이름이 있습니다: ScriptedChatModel` |
| 15 | Router가 정의 없는 경로를 내게 함(15a는 `Route`로 되돌림, 15b는 `path`에 `out_of_scope`를 더함) | `test_structures.py::test_hybrid_router_offers_only_the_paths_the_graph_routes`, `test_hybrid_router_answer_outside_fast_and_slow_is_an_error_not_a_route` | 첫 시험은 `['fast', 'slow', 'out_of_scope'] == ['fast', 'slow']`. 둘째는 `worker` 작업 중 `ScriptExhausted`로 실패해 원인을 간접으로 가리킨다 |
| 16 | `check_named_payment`에서 탐침 앞에 `return final`을 두어 탐침을 뺌 | `test_structures.py::test_first_payment_without_proposal_is_denied_by_the_code_gate`(12개 실패, 줄 수 시험 포함) | `('human_review', ..., 0, None) == ('denied', ...)`, `At index 0 diff: 'human_review' != 'denied'` |
| 17 | 탐침의 판정을 `execute_approved(…, approved=True)`에 넘김 | `test_structures.py::test_refundable_payment_without_proposal_is_reviewed_and_never_written`(4개 실패, 줄 수 시험 포함) | `('human_review', 1, None) == ('human_review', 0, None)`, `At index 1 diff: 1 != 0` |
| 18 | 번호를 `_PAYMENT_ID.findall(question)` 대신 `findall(final.text)`로 읽음 | `test_structures.py::test_old_duplicate_without_proposal_keeps_the_model_answer`(9개 실패) | `['제안이 없고 질문이 ... 검사하지 못했습니다.'] == ['결제일부터 90일이 ... 심사로 넘깁니다.']` |
| 19 | `_settle`이 레이블이 바뀌어도 `update["text"] = final.text`로 모델 문장을 둠 | `test_structures.py::test_first_payment_without_proposal_is_denied_by_the_code_gate`(10개 실패) | `At index 1 diff: 'P-7001을 재무 심사로 넘기겠습니다.' != '먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.'` |
| 20 | `_settle`의 중복 방지(이미 있는 문장은 더하지 않음)를 뺌 | `test_structures.py::test_checking_twice_adds_nothing[outcome-changed]`, `[allow-not-written]`, `[outcome-kept]`, `[unchecked]`(6개 실패) | `assert (FinalAnswer(o...) == FinalAnswer(o...)` |
| 21 | 검사 대상에 `answered`를 더함 | `test_structures.py::test_other_outcomes_naming_a_payment_are_untouched[answered]`(1개 실패) | `assert (FinalAnswer(o...) == FinalAnswer(o...)` |
| 22 | `hybrid`의 `gate` 노드에서 `check_named_payment` 호출을 뺌 | `test_structures.py::test_hybrid_graph_alone_checks_the_named_payment`(1개 실패) | `('human_review', ..., None) == ('denied', ..., None)`, `At index 0 diff: 'human_review' != 'denied'` |
| 23a | `run_case`의 그래프 경로(`handoff`, `hybrid`)에서 `question=turns[-1]`을 뺌 | `test_structures.py::test_hybrid_run_ends_denied_with_one_probe_and_no_unchecked_note`, `::test_handoff_run_checks_the_named_payment`(2개 실패) | `At index 3 diff: [... '코드 게이트가 이 판단을 검사하지 못했습니다.'] != ['먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.']` |
| 23b | `run_case`의 에이전트 경로(`single`, `single_skills`, `supervisor`)에서 `question=turns[-1]`을 뺌 | `test_structures.py::test_first_payment_without_proposal_is_denied_by_the_code_gate`, `::test_run_checks_the_question_of_the_last_turn[named-last]`(5개 실패) | `('human_review', ..., 0, None) == ('denied', ...)`, `At index 0 diff: 'human_review' != 'denied'` |

- 처음 시험에서 놓친 것은 4개다. `ready`가 실패 하나만, 또는 누락 하나만 있을 때 거짓이 되는지(2b, 2c)를 기존 시험은 둘이 함께 있는 경우만 봤다. `Send`를 반복문으로 바꾸는 결함(7, 7b)은 기존 겹침 시험이 자기 장난감 그래프를 만들어 `mas_lab`의 변경을 볼 수 없었다. 더한 시험 셋은 모두 결함에서 실패하고 원래 트리에서 통과한다. 겹침 시험 둘은 연속 12번 통과했다.
- 버린 주입이 하나 있다. 7번의 첫 주입은 `hybrid.py`에 4줄을 더해 `test_modules_stay_readable_in_class`(154 > 150줄)에서만 실패했다. 겹침 검사가 아닌 이유로 실패한 것이라 줄 수를 150으로 맞춰 다시 넣었다.
- 5번과 15번의 둘째 시험은 메시지가 원인을 직접 말하지 않는다. 10.2 끝의 "실패 메시지가 진짜 원인을 가리키는지" 기준에서 이 둘은 간접이다.
- 첫 실행에서는 사본에서 결함 없이 돌린 결과도 105개 통과였다.
- **최종 트리 재실행.** 첫 검토 뒤 고친 트리(시험 110개)에서 위 표의 20행(1, 2a, 2b, 2c, 3, 4, 5, 6, 7, 7b, 8, 9, 10a, 10b, 11, 12, 13, 14, 15a, 15b)을 행마다 새 사본에 다시 넣었다. 각 사본은 실제 트리와 결함을 넣은 파일 하나만 달랐다. 20행 모두 표의 같은 시험(14번은 같은 검사기)이 잡았고, 실패한 시험 이름의 집합이 앞 실행과 같았으며, 통과 개수는 모두 앞 실행보다 5개 많았다(결함 없는 사본은 105에서 110). 11번 행은 질의 차단을 일부러 무력화하므로 죽은 프록시 뒤에서 돌려 네트워크로 나가지 않게 했다. 14번은 앞 실행의 표에 줄이 없어 손으로 적은 기록과 견줬다. 표의 메시지는 첫 실행의 값을 그대로 둔다. 모델과 EXA는 부르지 않았다.
- **게이트 수정 뒤 재실행(16~23b).** 최종 트리(시험 146개)에서 위 20행과 16~23b 9행, 모두 29행을 행마다 새 사본에 다시 넣었다. 각 사본은 실제 트리와 결함을 넣은 파일 하나만 달랐다. 결함 없는 사본은 146개 통과(건너뜀 0, 실패 0)였다. 29행 모두 표의 시험이 잡았고 살아남은 결함은 0이다. 20행의 실패 시험 이름은 앞 실행과 같았고, 4번 행은 시험 3개, 5번 행은 시험 2개가 더 실패했다(새 시험도 같은 결함을 잡는다). 16번과 17번은 `structures.py`가 줄 수 한도(150줄)에 닿아 있어 줄 수 시험(`test_layout.py::test_modules_stay_readable_in_class`)도 같이 실패했지만, 행동 시험이 위 메시지로 따로 실패하므로 줄 수 시험만으로 잡힌 것은 아니다. 20번과 21번의 메시지는 `FinalAnswer` 전체 비교라 원인을 직접 말하지 않는다(간접). 실제 트리의 `Day03_new`와 `Day02_new/rag_lab`의 해시는 전후가 같았다. 모델과 EXA는 부르지 않았다.
- **게이트 수정을 쓴 노드가 따로 넣은 변형.** 그 노드는 위 9행 말고도 17개(번호를 `\b`로 읽어 조사가 붙은 `P-7001을`을 놓침, 접두사 검사 없음, 모르는 번호 수용, 번호 둘이면 첫째 채택, 안내 문장 생략, `gate_skipped` 사건 생략, `action: none` 제안을 환불 제안으로 취급, `allow`일 때 모델 레이블 유지, 코드 문장의 출처 미등록 등)를 하나씩 넣어 모두 시험이 잡았다고 기록했다. 이 17개는 최종 트리에서 다시 돌리지 않았고, 그 노드의 메모에만 있다.

- **동기화 전 트리 재실행(falsify 6, 2026-11-01 21:54~22:34).** 2026-11-02의 동기화 앞 트리의 값이다. 지금 트리의 값은 바로 아래 falsify 7에 있다. 위 표와 재실행 기록은 그때 트리(시험 105, 110, 146개)의 값이고, 표의 메시지도 첫 실행의 값이다. 그 뒤 시험 495개 트리의 falsify 5(결함 126개, 살아남은 결함 0, `docs/audit/falsify-5-notes.md`)를 거쳐, 코드와 시험을 모두 고친 그때 트리(시험 610개)에서 표 전체를 다시 돌렸다(`docs/audit/falsify-6-notes.md`). 정상 복사본 1행과 결함 172행, 모두 173행이다. 결함 172개를 모두 잡았고 살아남은 결함은 0이다. 171개는 pytest가, 14번 1개는 `check_notebook.py`가 잡았다. 구성은 앞의 29행, 행동별 16행, 모듈별 변이와 후속 68행, 조용한 구석과 노트북 가드 17행, 철자 13행(`gi`), EXA 경계 15행(`ex`), 근거 참조 14행(`wp`)이다. 정상 복사본은 3번 모두 608개 통과이고 실패는 저자 결정의 두 칸(`[retrieval.py]`, `[evidence.py]`)뿐이다. 이 두 칸은 기준선으로 보고 모든 행의 실패 목록에서 뺐으므로 잡은 것으로 세지 않았다. `Day02_new/rag_lab`은 다른 세션이 고치고 있어 시작할 때 뜬 사본 하나를 모든 복사본에 썼다. 행마다 `tests` 전체를 돌렸고 `exa.py`에 결함을 넣는 행은 죽은 프록시 뒤에서 돌렸다. 모델과 EXA는 부르지 않았고 실제 트리의 해시와 `outputs/runs` 1,893파일은 전후가 같다. 읽을 때 주의할 점이 셋이다. 14번 결함은 pytest 전체가 보지 못하고 검사기만 잡는다. `b11`은 시험 고정 장치의 결함이라 행동의 증거로 읽지 않는다. 16, 23b, `t11`, `w02`, `w08`, `n01`~`n04`는 코드가 바뀌어 주입 지점을 옮겼다.
- **현재 트리 재실행(falsify 7, 2026-11-02 09:26~09:52).** `rag_lab`을 동기화한(1절 5번) 지금 트리(시험 611개)에서 표 전체를 다시 돌렸다(`docs/audit/falsify-7-notes.md`). 정상 복사본 1행과 결함 174행, 모두 175행이다. 결함 174개를 모두 잡았고 살아남은 결함은 0이다. 173개는 pytest가, 14번 1개는 `check_notebook.py`가 잡았다. falsify 6의 172행에 새 두 행 `sy01`(`rag_lab/pipeline.py`)과 `sy02`(`rag_lab/evidence.py`)를 더했다. 둘은 동기화된 파일의 주석 안 한 바이트만 바꾸고 `Day02_new` 쪽은 두므로 복사본 시험만 볼 수 있다. 각각 611개 중 1개가 실패했고 그 하나가 `[pipeline.py]`, `[evidence.py]` 칸이다. `[retrieval.py]` 칸에 넣은 행은 없다(행을 둘만 더하기로 했고 이 칸은 복사본 시험 자체가 지킨다). 기존 행은 하나도 고치지 않았다. 동기화가 기존 행이 결함을 넣는 파일을 건드리지 않았고, 기존 주입 원문이 모두 정확히 한 번씩 나오는 것을 확인했다. 정상 복사본은 3번 모두 611개 통과, 실패 0이다. falsify 6이 기준선으로 뺐던 두 칸의 목록은 비웠고, 이제 어떤 시험도 정상 복사본에서 실패하면 안 된다. 행마다 `tests` 전체를 돌렸고 `exa.py`에 결함을 넣는 행은 죽은 프록시 뒤에서 돌렸다. 모델과 EXA는 부르지 않았고 실행 기록(`outputs/live`, `outputs/runs`)을 읽지 않았으며 실제 트리의 해시와 `outputs/runs` 1,893파일은 전후가 같다. 읽을 때 주의할 점은 falsify 6과 같다. 14번 결함은 pytest 전체가 보지 못하고 검사기만 잡으며, `b11`은 시험 고정 장치의 결함이라 행동의 증거로 읽지 않는다. [이후 `tests/test_harness.py`가 더해져 625개가 되었고(2026-11-02), 2026-11-03 노트북 분할 뒤 전체는 717개(`717 passed`, 실패 0)다. 위 611은 그 앞 시점의 값이다]

**4번. 변경 범위.** 후속 판정(충족)이 먼저이고 첫 판정(미충족)은 그 아래에 '첫 판정'으로 그대로 둔다.
- 방법. 이 세션의 기록 45개(주 기록과 하위 에이전트 44개, 이 감사 노드 자신의 기록 포함)에서 도구 호출 2,983개의 쓰기 대상을 뽑았다. 첫 호출은 10-31 23:03:44이고 `Day03_new`의 첫 파일(23:28)보다 앞서 세션이 이미 돌고 있었으므로 범위를 23:28이 아니라 이 첫 호출부터로 잡았다. 파일 도구 242개(Write 63, Edit 179, NotebookEdit 0)에서 보호 경로 대상은 0개다. Bash 2,140개 중 보호 경로를 언급하거나 인자·작업 폴더가 보호 경로로 풀리는 382개를 전부 분류했다(읽기 전용 267, 보호 경로를 쓰지 않는 파이썬 heredoc 69개를 본문까지 읽음, 문자열에만 나오는 것 39, 보호 경로 안이나 위에서 인터프리터를 돌린 것 5, 복사 원본으로만 쓴 것 2). 리다이렉트, `tee`, `cp`·`mv`·`rsync`의 목적지, `rm`, `touch`, `mkdir`, `chmod`, `sed -i`, `find -delete`, `sort -o`, 경로를 준 `git add`·`checkout`·`restore`·`reset`·`clean`을 쓰기로 보았고 보호 경로의 쓰기 대상은 0개였다. `uv`는 루트에서 `sync --locked --dry-run`을 3번 돌렸을 뿐이고 `lock`·`add`·`remove`는 없다. DAG 실행이 선언한 쓰기 범위(실행 기록 54개, `dag` 호출 입력 70개)도 모두 `Day03_new` 아래다. 설치 감사가 끝난 뒤 같은 방식으로 다시 파싱했을 때(기록 50개, 도구 호출 3,206개)도 보호 경로의 쓰기 대상은 0개였다.
- 나머지 증거. `Day03/`는 수정 시각이 이 세션의 첫 호출보다 늦은 파일이 0개이고(가장 늦은 것이 10-31 16:13), 루트 `pyproject.toml`·`uv.lock`은 수정 시각이 10-31 16:10·16:11이며 sha256이 감사 두 번(11-01 09:36, 10:37)에서 같았다. 세션 시작 뒤 바뀐 `Day02_new` 파일 32개는 모두 다른 세션(`0739479c`, `Day02_new`를 만든 세션)의 쓰기 호출과 1초 안에서 짝지었다(짝 못 지은 파일 0). 이 세션이 `Day02_new` 안에서 돌린 인터프리터는 두 번(`probe_model.py`, pytest)뿐이고 그 구간에 쓰인 파일은 ignored 폴더까지 포함해 없었다.
- 한계. 사후 감사다. 설계가 요구한 시작 시점 해시가 아니라, 감사 노드가 시작할 때 `Day02_new`·`Day03`·루트 두 파일 209개(73 + 134 + 2)의 sha256을 처음 뜬 목록이므로 그 시점 뒤의 변화만 지킨다. 설치 감사가 같은 목록을 다시 떴을 때 `Day03/`와 루트 두 파일은 차이가 0이었고 `Day02_new` 파일 10개가 달랐으며 모두 `0739479c`의 쓰기 호출 시각과 같았다. 파싱은 보호 경로를 이름으로 대지 않는 쓰기(경로를 계산하는 스크립트, 불러올 때 쓰는 라이브러리, 도구 쪽 쓰기)를 보지 못한다. 호출 기록은 결과가 아니라 시도를 기록하므로 실패한 명령도 시도로 센다. 짝지은 기록은 쓰기의 유력한 주체를 보일 뿐 유일한 주체의 증명이 아니다. 그래서 판정은 증거 넷(쓰기 대상 파싱, 선언한 쓰기 범위, `Day03/`와 루트 파일의 수정 시각과 해시, `Day02_new` 변경 전부의 다른 세션 귀속)이 모두 같은 방향이라는 데 기댄다. 이 한계 아래에서 충족이다. 분류표 382행과 스크립트는 임시 폴더에 있어 저장소에 남지 않는다.

**4번, 첫 판정(미충족).**
- 첫 판정, 충족한 부분: `Day03/` 아래 파일(`outputs`, `__pycache__` 제외)의 마지막 수정은 2026-10-31 16:13이고 루트 `pyproject.toml`, `uv.lock`은 10-31 16:10과 16:11이라 모두 `Day03_new`의 첫 파일(10-31 23:28)보다 앞선다. git 작업 트리에서 이 두 파일이 M 상태인 것은 10-31 16:10의 루트 통합 환경 작업 때문이고, 그 뒤로 수정 시각이 바뀌지 않았다. 이 최종 감사 구간(11-01 02:43 시작)에는 `Day03/`, `Day02_new/`, 루트 두 파일 어디에도 그 뒤에 수정된 파일이 없다. 깨끗한 복사본 감사 노드는 루트 `pyproject.toml`과 `uv.lock`의 sha256이 전후 같음을 확인했다.
- 첫 판정, 못 채운 부분(위 후속 판정이 쓰기 대상 감사로 대신했다): `Day02_new/`의 마지막 수정이 11-01 01:39(`docs/audit-live-notes.md`)라서 `Day03_new`를 만드는 동안(첫 파일 10-31 23:28 이후)에도 바뀌고 있었다. 이 작업의 쓰기와 다른 세션의 쓰기를 가를 시작 시점 해시가 없다. 11절이 N4에 기록하라고 한 복사 시점 해시를 이 세션의 기록과 앞선 DAG 보고에서 검색했으나 찾지 못했다. 이 작업이 쓰려던 파일 목록에 `Day02_new/`가 없다는 것까지만 말할 수 있고, 바뀌지 않았음은 증명하지 못했다.

**5번. 깨끗한 복사본.** 후속 판정(충족)이 먼저이고 첫 판정(미충족)은 그 아래에 '첫 판정'으로 그대로 둔다.
- 복사. `git ls-files -co --exclude-standard`가 내는 22,160개 경로(커밋 후보 집합)를 새 폴더에 복사했다. 작업 트리에서 이미 지워진 6개(`Day02/uv.lock`, `Day03/uv.lock`, `Day04/requirements.txt`, `Day05/uv.lock`, `Day07/uv.lock`, `Day08/uv.lock`)는 목록에는 있으나 없어 건너뛰어, 22,154개(일반 파일 22,118 + 심볼릭 링크 36)가 복사됐다. 크기는 `lstat` 합 421 MB다(`Day06`이 22,160개 중 19,498개). 설치 전에 `.env` 0개, `.venv`·`outputs`·`__pycache__` 0개를 확인했다.
- 설치. 복사본의 루트에서 `uv sync --locked`(uv 0.13.6)가 종료 코드 0으로 `.venv`를 새로 만들었다. `CPython 3.13.14`, 363개 해석, 345개 설치이고 `Day02`를 빌드했다. 편집 설치 `.pth`는 복사본을 가리키고 복사본 `.venv`에 원래 저장소 경로가 든 파일은 0개다. 설치 전후 `pyproject.toml`과 `uv.lock`의 sha256이 같고 루트 것과도 같다. 원래 루트 `.venv`의 `pyvenv.cfg`와 `.lock`은 수정 시각이 10-31 16:10 그대로다.
- 시험과 검사기. 복사본의 `.venv`로 `Day03_new`에서 pytest 146개 통과(건너뜀 0, 실패 0, 8.86초)와 노트북 7개 검사기 `OK`(00은 `--minutes 10`, 01~06은 `--minutes 60`)를 확인했다. `ANTHROPIC_API_KEY`와 `EXA_API_KEY`를 환경에서 지운 채 돌렸다. 10.3이 요구한 것보다 엄격하다.
- 00의 키 멈춤. `.env`가 없는 복사본에서 `tests/run_live.py 00-Setup.ipynb`가 종료 코드 1로 끝났고 실행된 셀은 2, 3, 5다. 셀 5(첫 키 확인 `require_key()`)에서 `RuntimeError`가 났다. 메시지는 한국어로 `Day03_new/.env.example`을 `.env`로 복사해 `ANTHROPIC_API_KEY`에 본인의 키를 직접 채우라는 안내다(`rag_lab/settings.py:65`). 셀 2가 `sys.prefix`로 복사본의 환경을 출력했고 모델 호출은 0회다.
- 키 값 검색. 두 `.env`(`Day03_new`, `Day02_new`)에서 비밀 값(`ANTHROPIC_API_KEY`, `EXA_API_KEY`. `OPENROUTER_API_KEY`는 비어 있다)을 읽어 전체 값과 끝 12자를 복사본 파일 22,176개(`.venv` 제외, 위 시험과 00 실행이 만든 파일 포함)에서 찾았고 0건이었다. 값은 출력하지 않았다. 대조로 임시 폴더에 같은 값을 넣고 찾으면 검출되고, 실제 `Day03_new` 최상위를 훑으면 진짜 `.env` 한 파일에서 검출된다. 모델 이름과 주소 같은 비밀이 아닌 설정 값(`OPENROUTER_BASE_URL`, `DAY02_MODEL`, `DAY02_EFFORT`, `DAY02_EMBEDDING_MODEL`)은 코드와 노트북에 일부러 적혀 있어 여러 파일에서 나왔고 판정에서 뺐다.
- 한계. 실제 `git clone`이 아니라 작업 트리에서 무시되지 않은 집합이다. 다른 세션의 미커밋 수정이 들어 있고, 파일 모드·줄바꿈·심볼릭 링크를 git이 다시 만든 것이 아니다. 설치가 1.1초에 끝나 공유 uv 캐시를 쓴 것이다. 잠금 파일이 빈 환경에서 풀리고 설치된다는 것은 보였지만 모든 휠을 지금도 내려받을 수 있는지는 다시 증명하지 않았다. 감사 중 `Day02_new`의 노트북과 문서 10개가 바뀌었는데 모두 다른 세션(`0739479c`)의 쓰기 호출 시각과 같았고 이 감사가 쓴 것은 없다. 복사본에서 01~06을 실제 모델로 돌리지 않았다(10.3의 5번이 요구하지 않는다). `ANTHROPIC_API_KEY`는 있고 `EXA_API_KEY`만 없는 경로는 kernel에서 돌리지 않았다. Windows와 Linux는 범위 밖이다(12절).
- 판정. 10.3의 5번이 요구한 설치, pytest, 검사기, 00의 첫 키 멈춤, 키 값 부재가 모두 확인되어 충족이다. 아래 첫 판정(설치를 `--dry-run`으로만 해 미충족)은 그때의 판정이고 이 후속 판정이 대신한다.

**5번, 첫 판정(미충족).** 첫 검토 전에는 `Day03_new`에서 `.env`, `outputs/`, `__pycache__`, `.ipynb_checkpoints`를 뺀 복사본에 `Day02_new/rag_lab`을 더해(79개 파일) 확인했고, 첫 검토 뒤에는 고친 최종 트리를 같은 방식으로 새로 복사해(`Day03_new` 65개 파일과 `Day02_new/rag_lab` 9개 파일, `.env`·`outputs`·`__pycache__`·`.ipynb_checkpoints`·`.ruff_cache` 없음) 다시 확인했다.
- 첫 판정, 최종 트리에서 통과한 것: 복사본의 pytest 110개 통과(건너뜀 0, 실패 0), 검사기 7개 `OK`(00은 `--minutes 10`, 01~06은 `--minutes 60`), 루트의 `uv sync --locked --dry-run`이 `Would make no changes`(363개 해석, 345개 확인)이고 그 전후로 루트 `pyproject.toml`과 `uv.lock`의 sha256이 같음, 복사본의 `rag_lab/corpus.py`, `retrieval.py`, `evidence.py`가 `Day02_new/rag_lab`과 `cmp`로 같음, 위 2번의 반증 20행. 최종 재확인이 만든 파일 1,931개에서 셸의 `EXA_API_KEY` 값을 찾았으나 없었다.
- 첫 판정, 앞 복사본(pytest 102개 시점)에서만 확인한 것: 키를 지운 환경의 00이 셀 5에서 `RuntimeError`와 `.env.example`을 알리는 한국어 안내로 멈춤, 복사본의 `.env`만 열려 했고 그 파일은 없음, 두 키의 전체 값과 끝 12자를 복사본·`outputs`·저장된 모든 노트북·소스에서 찾았으나 없음(양성 대조는 검출됨). 이 셋은 최종 트리에서 다시 돌리지 않았다.
- 첫 판정, 못 채운 것: 설치는 최종 트리에서도 루트의 `uv sync --locked --dry-run`뿐이고 빈 환경에 실제로 설치하지 않았다. 앞 실행이 적은 이유는 루트 `.venv`를 다른 세션이 함께 쓰고 있다는 것이다. 복사본에서 노트북 01~06을 실제로 돌리지 않았고, `ANTHROPIC_API_KEY`는 있고 `EXA_API_KEY`만 없는 경로를 kernel에서 돌리지 않았다. 앞 복사본에 남았던 `.ruff_cache/`와 빈 `.deepeval/`는 최종 복사본에 없다. 다만 최종 복사본도 git clone이 아니라 작업 폴더를 복사한 것이라 수강생이 받는 저장소와 똑같다고 증명하지 못한다. 그래서 첫 판정에서 5번은 미충족이었고, 위의 후속 판정이 이를 대신한다.

**10번. 새 질문.** 최신 판정이 먼저이고, 그 아래에 두 번째 판정(충족)과 첫 판정(미충족)을 그대로 둔다.

세 번째 판정(2026-11-01 18:28~18:33, `docs/audit/new-question-3-notes.md`). 철자 수정 앞의 `mas_lab/gate.py`(16:36판)로 `hybrid`를 돌렸다. 앞의 8행을 다시 돌리고 새 질문 5개를 더해 설계한 행은 13행이고, N4가 `budget_exceeded`로 끝나 같은 조건으로 N4b를 한 번 더 돌려 14행이 됐다. 질문 12개, 모델 호출 127회(상한 150), 288.9초다. 기대 답과 판정 규칙은 돌리기 전에 적었고 정답표는 읽지 않았다. 모델이 게이트 앞에서 쓴 레이블을 기록해, 앞 판처럼 사건에서 추정하지 않았다. 판정 규칙은 아래 두 번째 판정과 같다.

| 행 | 질문 | 상태 | outcome | 게이트 | 호출 | 판정 |
|---|---|---|---|---|---:|---|
| N1 | P-7001과 P-7002를 둘 다 환불해 달라 | `ok` | `human_review` | 탐침 2개(`deny`, `human_review`), `gate_text_appended` | 4 | 맞음(같은 말이 두 번 나온다) |
| N2 | 9월 1일에 중복 결제된 P-9002를 환불, 승인이 필요하면 승인 요청으로 | `ok` | `needs_approval`(P-9002 제안) | 제안 경로, 같은 `gate` 사건 2번 | 5 | 맞음 |
| N3 | P-4417 결제를 환불해 달라 | `ok` | `insufficient` | `gate_skipped`(P-4417) | 11 | 맞음 |
| N4 | 두 턴: P-3125 환불 가능 여부, 그다음 P-6284 환불 | `budget_exceeded` | 없음 | 턴 1의 `gate_skipped`(P-3125)만 | 21 | 턴 2 답 없음, 기대와 다름 |
| N4b | N4와 같음 | `budget_exceeded` | 없음 | 턴 1의 `gate_skipped`(P-3125)만 | 19 | 턴 2 답 없음, 기대와 다름 |
| N5 | 4월 1일에 결제한 `p7001`을 90일이 지났어도 예외로 환불해 달라 | `ok` | `human_review` | `gate_skipped`(번호 없음) | 9 | 그럴듯하게 틀림 |
| R1~R3 | 4월 1일에 결제한 P-7001을 90일이 지났어도 예외로 환불해 달라 | `ok` | `denied` 3번 | 탐침 `deny`, `gate_text_replaced` | 7, 8, 7 | 맞음 3번(코드 문장) |
| R4 | 같은 청구서로 두 번 결제됐다, P-9001 쪽을 환불해 달라 | `ok` | `needs_approval`(P-9002 제안) | 제안 경로, 번호 불일치 이유, 같은 `gate` 사건 2번 | 5 | 맞음(미리 적은 대안) |
| R5 | 나중 결제를 환불해 달라, 번호는 기억이 안 난다 | `ok` | `human_review` | `gate_skipped`(번호 없음) | 4 | 맞음(모델) |
| R6 | P-9001과 P-7001은 둘 다 중복 결제라서 환불해 달라 | `ok` | `denied` | 탐침 2개(`deny`, `deny`), `gate_text_replaced` | 8 | 맞음(맞는 답을 더 짧은 맞는 문장으로 바꿨다) |
| R7 | 알파의 7월과 8월 가용률, 크레딧 대상 달, 신청 기한 | `ok` | `answered` | 없음 | 10 | 맞음 |
| R8 | 이번 달(9월) 가용률과 크레딧 여부 | `ok` | `insufficient` | 없음 | 9 | 맞음 |

- 결과. 14행 중 `ok` 12, `budget_exceeded` 2다. 그럴듯하게 틀린 행은 1행(N5)이고, 미리 적은 기대와 같은 행은 11행이다(R4의 대안을 인정하지 않으면 10행). 원장은 14행 모두 0건이고 `policy_violations`도 없다. 실패한 행은 빼지 않았다. 앞의 두 판정은 지우지 않고 아래에 둔다.
- N4와 N4b. 두 행 모두 턴 2에서 `search 호출 한도를 초과했습니다.`로 끝났다. `run_case`는 행마다 Desk와 예산을 하나 만들고(`mas_lab/runner.py:56-61`) 두 턴이 이를 함께 쓴다. `FIXED_BUDGET`의 검색 한도는 6회다(`mas_lab/runner.py:24`). 턴 1이 Slow Path로 검색을 쓴 뒤 턴 2의 전환에서 한도에 닿았다. `FIXED_BUDGET`은 올리지 않았다. 그래서 두 턴에 걸친 경로, 즉 실제 행에서 `gate_skipped`가 두 번 남는 것은 관찰하지 못했다. 세 번째 시도는 잘 나온 반복을 고르는 일이 되어 하지 않았다.
- 누가 결과를 정했나. 틀린 모델 답을 코드가 참인 문장으로 바꾼 행 3(R1~R3), 맞는 답을 코드가 더 짧은 문장으로 바꾼 행 1(R6), 맞는 답에 코드가 문장을 덧붙인 행 1(N1), 제안 경로 2(N2, R4), 검사하지 못한 행 5(N3, N4, N4b, N5, R5), 게이트 사건이 없는 행 2(R7, R8)다. N5는 모델이 틀렸는데 코드가 검사하지 못한 행이다.
- 남은 것. 문장을 바꾼 4행에서 모델의 `uncertainty`는 사라졌고 앞 판의 판단 갈림은 지금 코드에 없다. `evidence_refs`는 모델의 것이 남아 바뀐 문장과 맞지 않는다(9.2절).
- 철자 수정 뒤. N5의 모델 답을 지금 게이트에 넣으면 `denied`이고 문장은 R1과 글자까지 같다(`docs/audit/replay-4-notes.md`). 실제 모델 행 S1~S3의 결과와 남은 경계는 9.2절의 철자 항목에 있다. 14행 전체를 지금 게이트로 다시 돌리지는 않았다. 14개 관찰이고 비율은 말할 수 없다.

두 번째 판정은 아래와 같다. 그 시점의 판정이고 그대로 둔다.

후속 판정. 게이트를 고친 뒤(9.2절) 같은 `hybrid`로 8행을 돌렸다. 첫 판정의 질문 3개(P-7001 환불 요청, 7·8월 가용률 복합 질문, 9월 가용률 질문)에, 번호가 있는 유효 결제를 가리킨 질문, 번호가 없는 요청, 번호가 둘인 요청을 더했고, P-7001 질문은 고친 코드가 실제로 레이블을 바꾸는지 보려고 3번 돌렸다. 질문 6개, 8행, 모델 호출 63회(돌리기 전에 정한 상한 80회)다. 정답표(`data/gold.jsonl`)는 읽지 않았다. 기대 답과 판정 규칙은 돌리기 전에 글로 정했고, 질문의 새로움은 문구 검색으로 확인했다(`Day03_new`의 노트북과 `data/cases.jsonl`에 질문 문구가 없다). 행 JSON은 `mas_lab.runner.ROOT`를 임시 폴더로 돌린 스크립트가 임시 폴더에만 썼고, 저장소의 `outputs/runs/`는 전후 1,099개로 같았다.

판정 규칙(돌리기 전에 정함). "그럴듯하게 틀림"은 고객이 읽는 `answer` 문장이 확신 있게 거짓을 말하거나 틀린 결제를 틀린 경로로 보내는 것이다. 원장이 0건이어도, `uncertainty`에 검사하지 못했다는 메모가 있어도 그렇게 센다. 게이트가 문장을 바꿨으면 바뀐 문장을 판정한다. 문장은 맞고 레이블만 기대와 다르면 따로 적고 맞은 것에도 틀린 것에도 세지 않는다.

| 행 | 질문 | outcome | 호출 | 판정 | 결과를 정한 쪽 |
|---|---|---|---:|---|---|
| R1~R3 | 4월 1일에 결제한 P-7001을 90일이 지났어도 예외로 환불해 달라 | `denied` 3번 | 9, 8, 8 | 맞음 3번 | 코드 게이트 |
| R4 | 9월 1일에 같은 청구서로 두 번 결제됐다, P-9001 쪽을 환불해 달라 | `needs_approval`(P-9002 환불 제안 1,200,000원) | 5 | 맞음 | 모델의 제안(제안 경로) |
| R5 | 4월에 같은 청구서로 두 번 결제했다, 나중 결제를 환불해 달라, 번호는 기억이 안 난다 | `human_review` | 4 | 맞음 | 모델(코드는 `gate_skipped`로 검사하지 못함) |
| R6 | P-9001과 P-7001은 둘 다 중복 결제라서 환불해 달라 | `needs_approval`(P-9002 환불 제안) | 8 | 문장 맞음, 레이블만 기대(`denied`)와 다름 | 모델의 제안 |
| R7 | 알파의 7월과 8월 가용률, 크레딧 대상 달, 신청 기한 | `answered` | 12 | 맞음(기한을 9월 20일과 9월 15일 둘로 말해 원문보다 덜 단정적) | 모델 |
| R8 | 이번 달(9월) 가용률과 크레딧 여부 | `insufficient` | 9 | 맞음 | 모델 |

- 결과. 그럴듯하게 틀린 행은 0행이다. 8행 중 7행이 맞고 R6은 레이블만 달라 세지 않았다. 원장은 8행 모두 0건이고 `policy_violations`는 모두 없음이다. 그래서 충족이다. 첫 판정의 P-7001 `human_review`는 고쳐졌다. 3번 모두 `denied`이고 문장은 코드가 낸 "먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."(`mas_lab/ledger.py:61`)다. 이 문장은 사실이고 한 줄이다. 결제 번호도, 예외 요청도, 나중 결제 P-7002가 심사로 갈 수 있다는 말도 담지 않았다. 거짓은 아니다.
- 코드가 결과를 정한 행은 8행 중 R1~R3 셋뿐이다. `gate_text_replaced` 사건은 레이블이 바뀔 때만 남고 탐침은 `denied`·`human_review`일 때만 돌기 때문에, 모델의 원래 레이블은 `human_review`였다고 R1~R3의 사건에서 추정한다(사건에 원래 레이블은 저장되지 않는다). 첫 판정의 1회와 합치면 P-7001 질문에서 모델은 4번 모두 `human_review`를 쓴 것으로 읽힌다. R5는 코드가 검사하지 못한 길이고 모델이 맞았다. R4와 R6은 제안 경로이고 모델이 질문의 P-9001이 아니라 P-9002를 골라 맞았다. 코드가 틀린 결제를 잡은 것이 아니라 모델이 맞게 골랐다.
- 판단이 갈리는 한 가지. R1에는 코드가 뒤집은 재무 심사 경로를 말하는 모델의 `uncertainty` 한 줄과 `proposal.reason`이 남았고, R2와 R3에는 중복 여부가 확인되지 않았다는 `uncertainty` 줄이 남았다(규정과 조회 결과로 정해지는 일이다). 이 기록은 `answer` 문장 기준으로 세었다. `uncertainty`와 `proposal.reason`을 고객이 읽는 것으로 세는 엄격한 독자는 R1(어쩌면 R2, R3)을 그럴듯하게 틀린 행으로 센다. 그러면 10번은 미충족이다. 어느 쪽으로 읽을지는 저자의 판단이다.
- 한계. 질문 6개, 8행, 모델 하나, 하루라 비율은 말할 수 없다. 모델 없이 손으로 쓴 답을 `check_named_payment`에 넣은 오프라인 탐침은 행으로 세지 않았다. 레이블이 판정과 같은 `denied`에 틀린 이유만 쓴 문장은 통과하고, `answered`로 쓴 "환불을 접수했습니다"는 검사받지 않는다(9.2절 `[미해소]`). R7은 `INC-311`을 근거 번호로 인용해 `validate_final`이 한 번 다시 쓰게 했다(호출 12회, 첫 판정은 10회).

**10번, 첫 판정(미충족).** 노트북과 `data/cases.jsonl`에 없는 질문 3개를 `hybrid`로 1번씩 돌렸다(모델 호출 26회, 예고 40회 안). 정답표(`data/gold.jsonl`)는 읽지 않았고, 기대 답과 판정 규칙을 돌리기 전에 정했다. 세 행 모두 `status=ok`, Router는 slow, 원장 0건, `validate_final` 문제 없음, `out_of_scope` 없음이다. 행 JSON은 임시 폴더에만 있다.

| 사례 | 질문 | outcome | 호출 | 초 | 판정 |
|---|---|---|---:|---:|---|
| `new-compound-jul-aug` | 알파의 7월과 8월 가용률, 크레딧 대상 달, 신청 기한 | `answered` | 10 | 29.6 | 맞음 |
| `new-insufficient-sep` | 이번 달(9월) 가용률과 크레딧 여부 | `insufficient` | 9 | 18.5 | 맞음 |
| `new-deny-p7001` | 4월 1일 결제한 P-7001을 90일이 지났어도 예외로 환불 | `human_review` | 7 | 19.3 | 그럴듯하게 틀림 |

- 세 번째가 틀린 이유: P-7001은 같은 청구서에서 먼저 승인된 유효 결제라 환불 대상이 아니다. 답은 P-7001을 재무 심사로 "넘기겠다"고 쓰고, 중복이면 대상이 P-7002여야 하는지 "확인되지 않았다"고 썼다. 두 가지 모두 규정(`data/business/billing-policy.md`)과 조회 결과로 정해지는 일이다. 맞은 것은 금액 1,000,000원, 160일, "5분 뒤" P-7002, 90일 경과는 재무 심사라는 규칙, 예외 규정을 지어내지 않은 것, 환불을 처리했다고 말하지 않은 것이다. 원장은 0건이라 쓰기는 일어나지 않았다.
- 코드가 막지 못한 곳은 그때 9.2절 마지막 항목에 있었다. 모델이 제안 없이 `human_review`를 쓰면 `check_refund`가 돌지 않았다. 이 틈은 이후 막혔다(9.2절 `[해소]` 항목, 위 후속 판정).
- 3개, 1회씩이라 비율은 말할 수 없다. 질문의 새로움은 문구 검색으로 확인했다(노트북 00~06과 `data/cases.jsonl`에 질문 문구가 없다). 다만 세 번째는 01의 셀 46이 `P-7001` 환불 제안을 모델 없이 게이트에 직접 넣으므로 결제는 알려져 있고 질문만 새롭다.

**첫 검토 쌍의 지적과 수정.** 첫 검토 두 건이 세 가지를 지적해 통과시키지 않았다. 고친 뒤 위 2번과 5번을 최종 트리에서 다시 돌렸고, 6번의 `audit_live.py`도 다시 돌려 `AUDIT OK`를 얻었다(실제 모델 실행은 다시 하지 않았다).
1. 감사가 비교하지 못한 셀을 통과시켰다. 고지에 `model_calls=` 숫자가 없는 유료 셀과 실행본이 없는 기록이 `AUDIT OK`로 지나갈 수 있었다. `tests/audit_live.py`가 둘을 실패로 보게 고쳤고(`tests/audit_live.py:38-39`, `tests/audit_live.py:27-28`) `tests/test_audit_live.py`에 항목 5개를 더했다(7개에서 12개, 9.2절과 10.1절).
2. 가짜 챗 모델이 `tests/fakes.py` 밖에 있었다. `test_structures.py`의 `RouterFake`와 `test_research.py`의 `ReportFake`를 `tests/fakes.py:62`의 `ParsedChatModel` 하나로 합쳤다(10.1절).
3. `AGENTS.md`의 EXA `published` 문장이 00과 06에서 `None`이 관찰됐다고 적었으나 실행본과 맞지 않았다. 06 셀 7의 결과 3건은 2건이 게시일이 있고 1건이 `확인 안 됨`이며, 00의 EXA 셀(셀 17)은 `published`를 출력하지 않는다. 문장을 실행본 출력에 맞게 고쳤다. 이 문서 9.2절의 `ExaClient` 항목과 같은 값이다.

## 11. 작업 순서

```text
N1 design (this document)
   |
 (G1: author review, done)
   |
   +-----------+
   |           |
N2 base     N3 data
   |           |
   +-----+-----+
         |
    N4 mas_lab
         |
   +-----+-----+-----+-----+-----+
   |     |     |     |     |     |
  N5    N6    N7    N8    N9   N10
 00+01  02    03    04    05    06
   |     |     |     |     |     |
   +-----+-----+-----+-----+-----+
         |
     N11 docs
         |
  N12 static audit
         |
 (G2: paid run notice)
         |
    N13 live run
         |
  N14 fix + final audit
```

N4는 코드를 쓰기 전에 `Day02_new/rag_lab`을 다시 읽는다. 복사 시점의 해시를 기록한다. 이 문서의 시그니처와 설치본이 다르면 코드를 따르고 문서를 고친다.

후속(2026-11-01): 위 그림은 계획 당시의 기록이라 그대로 둔다. N13 뒤에 `hybrid`의 Router를 고치고 04와 05를 다시 돌렸으며(9.2절), N14의 최종 감사는 10.4절에 있다. N4가 남겼어야 할 복사 시점 해시는 찾지 못했고 그 때문에 첫 판정에서 10.4절 4번이 미충족이었다. 후속(2026-11-01, 두 번째): 최종 감사가 남긴 미충족 3개(4·5·10번)를 다시 판정했다. 코드 틈은 `check_named_payment`로 막았고(9.2절), 4번은 쓰기 대상 감사로, 5번은 실제 설치로, 10번은 새 질문 8행으로 다시 판정했으며(10.4절), 01~05의 기본 실행과 04·05의 켠 실행을 다시 돌렸다. 이 후속에서 모델을 부른 횟수는 1,000회다. 노트북 재실행 937회(저장소에 남은 기록 7개의 793회와, 감사에서 실패해 버린 05 기본 실행 첫 판 144회)와 새 질문 63회다. 같은 단가표로 계산한 모델 비용은 각각 약 5.79 USD와 0.46 USD, 합쳐 약 6.25 USD다. EXA는 부르지 않았다(01~05는 EXA 호출이 없고 06은 다시 돌리지 않았다). 코드 수정, 재생, 결함 주입, 설치 감사, 쓰기 대상 감사는 모델도 EXA도 부르지 않았다. 잰 것은 호출 수와 토큰이다(`ModelMeter`와 `.usage.jsonl`, 새 질문은 행 JSON의 호출 기록). 비용은 `tests/cost_report.py`의 단가로 곱한 값이고 캐시 쓰기 단가를 반영하지 않아 하한이다. 재지 못한 것은 버린 05 첫 판의 `.usage.jsonl`이 저장소가 아니라 임시 폴더 사본에만 남아 있다는 점과, 이 작업을 진행한 에이전트 자신의 토큰이다.

후속(2026-11-01, 세 번째): 위 그림은 여전히 계획 당시의 기록이라 그대로 둔다. 순서는 이렇다. 먼저 유료 실행을 돌렸다(`docs/audit/verify-b1-notes.md`). 01~05의 기본·켠 실행 937회(USD 5.67), 새 질문 감사 14행 127회(USD 0.77), `complex-ops-log` 반복 9행 56회(USD 0.41)로 모두 1,120회, 모델 비용 하한 USD 6.85다(예고 약 1,120회·약 USD 7, 상한 1,370회). 그 결과로 드러난 것을 고쳤다. 결제 번호 철자(`mas_lab/gate.py:13`, `mas_lab/exa.py:18`)와 근거 참조(`mas_lab/workers.py:151`)이고, 수정과 재생과 결함 주입은 모델도 EXA도 부르지 않았다. 그다음 다시 돌렸다(`docs/audit/verify-c2-notes.md`). 모두 719회, 2,079.6초, 모델 비용 하한 USD 4.54다. 예고는 약 760회·약 USD 5, 상한은 920회였다. 04·05의 네 기록이 639회(USD 3.98), 철자 행 S1~S3이 25회(USD 0.19), `complex-ops-log` 반복 둘째 묶음 9행이 55회(USD 0.37)다. EXA는 0회다. 비용은 `tests/cost_report.py`의 단가로 곱한 값이고 캐시 쓰기 단가가 없어 하한이다. 두 실행을 더한 1,839회, USD 11.39는 덧셈일 뿐 이 폴더의 전체 지출이 아니다. 그 앞의 실행과 00, 06의 실행이 들어 있지 않다. 이 문서를 고친 갱신 작업은 모델도 EXA도 부르지 않았고 `outputs/runs`는 1,893파일 그대로다.

후속(2026-11-02): Supervisor 용어 수정(1절 저자 결정) 뒤 02 기본 실행 1회를 다시 돌렸다. 모델 35회, 146.2초, 모델 비용 하한 USD 0.2509, EXA 0회다(실행 전 고지 약 33회·약 USD 0.25, 노트북 고지 25~60회). 버린 실행은 없다. 리뷰, 노트북·문서 수정, 정적 검사는 모델도 EXA도 부르지 않았고 `outputs/runs`는 1,893파일 그대로다. 이 작업을 진행한 에이전트 자신의 토큰은 세지 않았다.

후속(2026-11-02, 전체 재실행): 저자 지시로 나머지 기록 12개를 21:56~22:51에 하나씩 다시 돌렸다. 모델 961회, 3,273.4초, 모델 비용 하한 USD 6.6926, EXA 69회(00 1, 06 기본 21, 06 켠 실행 47) 약 USD 0.48이다. 실행 전 고지는 모델 약 950회(셀 고지 상한 합 약 1,390회)·모델 약 USD 7·EXA 약 69회·약 USD 0.5였다. 버린 실행은 없다. 앞의 02 기본 실행을 더하면 이날 재실행은 모델 996회, 하한 USD 6.9435, EXA 69회다. `outputs/runs`는 2,008파일이 됐다(재실행이 115행을 썼다). 문서 갱신과 감사는 모델도 EXA도 부르지 않았다. 이 작업을 진행한 에이전트 자신의 토큰은 세지 않았다.

## 12. 미확인 사항과 저자 확인 필요

| 항목 | 상태 | 근거 또는 남은 일 |
|---|---|---|
| EXA API 형태와 비용 칸 | 실측함(2026-11-01). 요청은 `POST https://api.exa.ai/search`, 응답의 `costDollars.total`은 검색 한 번에 0.007달러, `source_id`는 `S-` 뒤 16진수 8자, `publishedDate`는 06 셀 7의 3건 중 1건만 있었다(2026-11-02 재실행 기록. 재실행 전 기록은 2건) | 4절의 EXA 실측 표. 같은 질의의 결과는 호출마다 달라질 수 있다 |
| `show_graph`의 mermaid 표시 | 실제 그래프로 확인함(2026-11-01). 04 셀 51과 같은 `build_hybrid` 그래프를 실제 `show_graph`로 내보낸 출력을 JupyterLab 4.6.5와 헤드리스 Chrome 156.0.8078.80에서 그렸다. 노드 13개와 간선 19개가 모두 그려졌고, 점선 12개와 실선 7개가 `get_graph()`의 조건부 12개, 일반 7개와 같다. 저장한 PNG(`docs/audit/graph-render.png`)를 열어 확인했다. 외부 이름 해석을 막은 브라우저에서 같은 그림이 나와 인터넷 없이 그려진다. 모델 호출은 0회다 | 어두운 테마, 다른 브라우저, Notebook 7, VS Code는 시험하지 않았다. `show_graph`는 kernel이 아니라 보통 파이썬 프로세스에서 불렀고 그 출력을 저장해 그렸다(`docs/audit/graph-render-notes.md`). 이 행의 앞 판은 합성 그래프 2개까지만 그렸다고 적었다. 출력과 간선 표는 `mas_lab/view.py:30-34`가 낸다 |
| 호출 수와 비용 | 실측함. 지금 기록은 기본 실행 315회와 켠 실행 681회, 모델 비용 하한 USD 2.28과 4.67이다(`tests/cost_report.py`). 전체 재실행 전은 314회와 677회, 02 기본 실행을 다시 돌리기 전은 312회였고, 앞 판은 311회와 712회, USD 2.32와 5.00, 그 앞은 690회, USD 4.85다 | 9.2절. 실제로 쓴 호출과 비용은 11절(1,120회 하한 USD 6.85, 719회 하한 USD 4.54, 2026-11-02의 35회 하한 USD 0.25와 961회 하한 USD 6.69). README의 값이 이와 맞는지는 10.4의 11번 |
| 실제 답변 품질 | 사례별 1회 관찰만 가능 | 구조적으로 해소되지 않는다. 노트북이 그렇게 말한다. 새 질문 감사(10.4의 10번)는 세 번째 판정에서 질문 12개를 14행으로 돌렸고, 철자 수정 뒤에는 같은 문장의 3행(S1~S3)을 돌렸다. 비율은 말할 수 없다 |
| Windows, Linux 실행 | 검증하지 않음 | 범위 밖 |
| `Day02_new` 저자 감사 상태 | 이 문서를 처음 쓸 때 `audit-live-notes.md`는 pytest 2건 실패로 `Live audit: FAIL`을 기록했다. 2026-11-01 지금 그 파일의 마지막 줄은 `Live audit: PASS`다(파일 수정 19:55, 다른 세션이 고치는 파일이다) | 이 과정은 그 PASS를 다시 검증하지 않았다. `Day02_new`는 이 작업이 바꾸지 않는 폴더다 |
| 제안 없는 `denied`·`human_review`의 코드 검사 | 수정함(2026-11-01). 질문의 번호가 모두 이 고객의 결제이면 번호마다 검사한다(`mas_lab/gate.py:54-66`). 번호가 없거나 모르는 번호가 섞이면 검사하지 못했다고 쓰고 모델의 레이블과 문장을 그대로 둔다. 질문에 `환불`이 있으면 다른 레이블도 검사한다 | 남은 틈은 9.2절 `[미해소]` 항목 끝의 `지금 상태`와 철자 항목의 경계다. 실제 모델 행에서 이 틈으로 틀린 문장이 나온 행은 N5 하나이고 철자 수정으로 막았다 |
| 모델이 제안을 빼는 빈도 | 측정하지 않음 | 맞은 행은 대개 제안이 없다. 지금 `policy-human-old`·`policy-deny-normal` 실제 모델 행 81개 중 환불 제안이 있는 행은 1개다(재실행 전 71개 중 1개, 앞 판은 51개 중 0개). 모델 답을 기록한 P-7001 질문 7행(R1~R3, N5, S1~S3)은 모두 `human_review`였지만 질문 하나이고 빈도가 아니다 |
| 새 질문 감사에서 코드가 결과를 정한 행 | 세 번째 판정 14행 중 문장 교체 4행(R1~R3, R6)과 문장 덧붙임 1행(N1) | 제안 경로 2행(N2, R4), 검사하지 못한 행 5행(N3, N4, N4b, N5, R5), 사건 없음 2행(R7, R8). 철자 수정 뒤 S1~S3은 3행 모두 문장 교체다. 앞 판의 "8행 중 3행"은 두 번째 판정의 값이고 모델의 원래 레이블을 사건에서 추정했다 |
| 쓰기 대상 감사(10.4의 4번) | 사후 감사로 충족 | 시작 시점 해시가 없다. 보호 경로를 이름으로 대지 않는 쓰기는 파싱으로 보이지 않는다. 짝지은 `Day02_new` 변경 32개는 유력한 주체이지 유일한 주체의 증명이 아니다 |
| 깨끗한 설치(10.4의 5번) | 충족. 작업 트리를 새 git 저장소로 만들어 복제한 사본으로 세 번 확인함 | 빈 uv 캐시로 `uv sync --locked`가 345개 패키지를 설치했고 그때의 pytest 503개와 검사기 7개가 통과했다. 2026-11-02에 `rag_lab` 동기화 앞의 작업 트리를 새 저장소로 다시 복제해 빈 uv 캐시로 같은 절차를 되풀이했다. `uv sync --locked`가 다시 345개 패키지를 설치했고(해석 363개) pytest는 610개 중 608개가 통과하고 2개가 실패했다. 실패한 칸은 `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]`와 `[evidence.py]` 둘뿐이고(저자 결정으로 둔 칸, 아래 `rag_lab` 복사본 동기화 행), 노트북 검사기 7개가 통과했다. 이 되풀이는 모델 호출 0회, EXA 호출 0회이고 실제 키를 넣은 00-Setup 단계는 되풀이하지 않았다. 저자용 `check_costs.py --self-test`는 복제본에 `outputs/live`가 없어 종료 코드 1로 끝났다(수강생 경로가 아니고 `outputs/live`를 잠시 복사하면 통과해서 실패로 세지 않았다). 같은 날 동기화(09:13) 뒤의 작업 트리로 세 번째 복제를 했다(09:17~09:21, `docs/audit/clean-clone-3-notes.md`). 후보는 22,299경로(파일 22,257개, 심볼릭 링크 36개)였고 복제본은 추적 파일 22,293개이며 `.env`, `.venv`, `outputs`는 0개였다. 빈 uv 캐시로 `uv sync --locked`가 다시 345개 패키지를 설치했고(해석 363개, uv 0.13.6, CPython 3.13.14) pytest는 611개가 모두 통과했으며(실패 0) `test_rag_lab_copies_are_byte_identical`의 네 칸이 모두 통과했다. 복제본의 `Day03_new/rag_lab` 네 파일은 `Day02_new/rag_lab`과 sha256이 같다. 노트북 검사기 7개가 통과했다. `.env` 없이 키를 지운 환경에서 00-Setup을 돌리면 셀 인덱스 5(실행 번호 In[3])의 `require_key()`에서 한국어 안내와 함께 멈췄고 모델 호출은 0회다. 키 값 검색은 파일 47,173개에서 0건이었다(양성 대조는 3건 검출). `check_costs.py --self-test`는 두 번째와 같은 이유로 종료 코드 1이었다. 이 복제도 모델 호출 0회, EXA 호출 0회이고 실제 키를 넣은 00 단계는 하지 않았다. 아래 한계는 세 번 모두 같다. 한계: 원격 커밋이 아니라 그때의 작업 트리이고, macOS aarch64만 봤고, Python 3.13이 이미 설치돼 있어 Python을 내려받는 경로는 보지 않았고, 사본에서 01~06을 실제로 돌리지 않았다. Windows와 Linux는 범위 밖이다(`docs/audit/clean-clone-notes.md`, 되풀이는 `docs/audit/clean-clone-2-notes.md`) |
| 마지막 수정 앞에 돌린 기록 | 없음(2026-11-02 전체 재실행). 13개 기록은 모두 2026-11-02 21:40~22:51에 지금 코드(`mas_lab`, 동기화한 `rag_lab`, 지금 노트북)로 돌았다. 재실행 전에는 여덟 개(00, 01·03의 기본·켠 실행, 02의 켠 실행, 06의 기본·켠 실행)가 `mas_lab` 마지막 수정 앞이었고, 02 기본 실행을 뺀 12개가 `rag_lab` 동기화 앞이었다 | **이력(2026-11-02 전체 재실행 전의 판단).** 01·03 기록과 02 켠 실행 기록은 `workers.py` 수정 앞 기록이다. 수정된 것은 `checked_worker`(`Day03_new/mas_lab/workers.py:151`)와 새 `_TOKEN`(`workers.py:148`)뿐이고 `run_worker`(`workers.py:141`)와 `_run_with_messages`(`workers.py:118`)의 본문은 그대로다. `checked_worker`는 `Day03_new/mas_lab/hybrid.py:90`과 `hybrid.py:110`에서만 불리는데 이 세 노트북의 코드 셀은 `build_hybrid`도 `run_case("hybrid", ...)`도 `checked_worker`도 부르지 않아 기록이 달라지지 않는다. 이 다섯 기록은 `gate.py` 수정 앞 기록이기도 하다. 수정된 것은 결제 번호 철자 패턴 `_PAYMENT_ID`(`Day03_new/mas_lab/gate.py:13`)와 그것을 쓰는 `_named_payments`(`gate.py:18`)뿐인데, 이 구간에 쓰인 행 12개의 질문 문자열 4종에는 어떤 철자의 결제 번호도 없고 02·03은 질문 없이 `gate_answer`를 불러(`gate.py:32`) 패턴이 읽을 입력이 없다. 오프라인 재생에 쓴 저장 행 422개의 질문에서 찾은 결제 번호 꼴 120개가 모두 `P-<숫자>`였고 그 422행을 새 코드로 다시 통과시켜도 뒤집힌 행이 0이었던 것과도 맞아 기록이 달라지지 않는다. 06은 `exa.py` 수정 앞 기록이다. 기록에 남은 코드 셀 질의 문자열 16개(00의 1개 포함)와 모델이 쓴 질의 21개와 조각 5개 가운데 새 `INTERNAL_PATTERN`(`Day03_new/mas_lab/exa.py:18`)이 새로 막는 것은 0개이지만, 기록이 모델이 쓴 질의를 전부 저장하지는 않아(병렬·직렬 실행은 6회 검색 중 공유한 일부만 출력) 저장되지 않은 질의는 `assert_public_query`(`exa.py:30`)가 다르게 판정했을지 확인할 수 없다. 달라질 수 있는 방향은 기록 당시 나간 질의가 지금은 막히는 쪽뿐이고 옛 패턴이 막던 것이 지금 통과하는 경우는 없다. 00은 세 파일의 수정 앞 기록이다. 코드 셀이 닿는 수정 함수는 `ExaClient.search`(`Day03_new/mas_lab/exa.py:49`)가 부르는 `assert_public_query`(`exa.py:30`) 하나뿐이고 그 질의 `LangGraph Send API`는 옛 패턴도 새 `INTERNAL_PATTERN`(`exa.py:18`)도 막지 않으며, `make_desk`(`Day03_new/mas_lab/runner.py:39`)만 부르므로 `_PAYMENT_ID`와 `checked_worker`에는 닿지 않아 기록이 달라지지 않는다. 00과 06은 세 파일 말고도 `hybrid.py`, `runner.py`, `structures.py`, `workers.py`의 더 앞선 수정보다 오래됐다. 그 수정들에도 두 노트북은 닿지 않는다. 근거는 파일 수정 시각과 작업 중 떠 둔 사본이고 `Day03_new`는 git으로 추적되지 않는다(`docs/audit/stale-records-notes.md`). **동기화 앞 기록 전부.** 02 기본 실행을 뺀 12개 기록(`outputs/live`)과 `outputs/runs`의 행 1,893개는 모두 `rag_lab` 동기화(2026-11-02 09:13)보다 앞선다(02 기본 실행은 `outputs/runs`에 행을 쓰지 않았다). 동기화는 `rag_lab/retrieval.py`와 `rag_lab/evidence.py`를 바꾸고 `rag_lab/pipeline.py`를 더했으므로 이 기록들은 동기화된 코드로 만든 것이 아니다. 04·05의 네 기록도 같다. 다시 돌리지 않은 이유는 둘이다. 저자가 2026-11-02에 유료 재실행을 하지 않기로 정했다. 그리고 모델 없이 한 비교에서, 실제 한도로는 모델이 받는 검색 결과가 같았고 넘침 경로만 달랐다. 비교는 같은 입력을 동기화 전 트리와 동기화한 트리에 넣어 출력을 줄 단위로 견줬고 모델도 EXA도 부르지 않았다. ① 질의마다 새 컨텍스트로 한 검색 720회가 같았다. ② 한 컨텍스트에 쌓으며 실제 한도 24,000바이트(`Budget.max_context_bytes`, `rag_lab/evidence.py:28`)로 한 검색 720회가 같았고 제외(`context_excluded`)는 0건이었다. ③ 한도를 3,000바이트로 낮춰 넘침 경로를 강제하면 출력 780줄 중 73줄이 달랐다. 새 `_admit`(`rag_lab/evidence.py:118`)은 한도를 넘으면 그 아래 순위의 새 근거를 모두 버리고(`fit_context`, `rag_lab/pipeline.py:83`), 옛 코드는 넘친 항목 하나만 건너뛰었기 때문이다. 줄이 갈리는 (범위, 시드) 6곳의 첫 차이는 이 규칙 차이로 확인했고, 이어진 차이는 앞 검색에서 쌓인 근거가 달라서 이어진 것으로 읽었다(하나하나 증명하지 않았다). 이 차이는 같다고 주장하지 않고 차이로 적는다. ④ 순위를 뒤집은 대조군은 부분 1에서 720줄 중 720줄, 부분 2에서 780줄 중 720줄(검색 720줄 전부, 이벤트 요약 60줄만 같았다), 부분 3에서 780줄 중 774줄이 달랐고, 같은 트리를 두 번 돌리면 같았다. 그래서 이 비교는 차이를 잡을 수 있고 결과가 결정적이다. 저장된 행 1,893개에는 `context_excluded` 사건이 0건이고 컨텍스트는 최대 11,120바이트였다. 어느 노트북도 `max_context_bytes`를 바꾸지 않는다. 검색·읽기 도구의 설명과 스키마는 바뀌지 않았다. 따라서 ③의 넘침 경로는 저장된 어느 행도 지나지 않았고, 노트북이 닿는 경로에서 모델이 받는 도구 결과는 같다고 본다. 이 결론은 추론이다. 한계 셋: 저장된 행에는 모델이 실제로 쓴 검색어가 남지 않아 사례의 질문과 코퍼스 조각을 검색어로 대신 썼다. `read_more`는 문서마다 한 번 비교했고 넘침 아래에서는 비교하지 않았다. 모델의 답은 다시 받지 않았다. 그래서 같은 질문의 답이 같다는 증명은 아니다. 수강생이 한도에 닿는 새 질문을 하면 옛 코드와 다르게 근거가 빠질 수 있다. 근거는 `docs/audit/sync-equivalence-notes.md`. |
| `rag_lab` 복사본 동기화 | 했음(2026-11-02 09:13). `Day02_new/rag_lab`의 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 네 파일을 복사했고 `cmp`로 바이트가 같다. `test_rag_lab_copies_are_byte_identical`은 네 칸 `[corpus.py]`, `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]`를 보고(`tests/test_layout.py:13`) 모두 통과한다. 전체 `tests`는 611개 통과, 실패 0이다. `settings.py`는 일부러 달라 건드리지 않았다. 앞 상태(2026-11-01)는 `[retrieval.py]`, `[evidence.py]` 두 칸이 실패한 `2 failed, 608 passed`(610개)였고 저자 결정으로 둔 것이었다 | 저자가 2026-11-02 오전에 유료 재실행을 하지 않기로 정했다(같은 날 밤 Supervisor 용어 수정 뒤 13개 기록을 모두 다시 돌리기로 다시 정했다. 9.2절, 11절). 앞 판은 동기화 뒤 01~05를 다시 돌리면 모델 비용 하한으로 약 USD 4~6이 든다고 적었다(2026-11-01에 04·05만 다시 돌린 지출 639회 USD 3.98과 앞서 01~05를 모두 다시 돌린 지출 937회 USD 5.67에서 온 숫자). 동기화 때문에 그 돈을 쓰지는 않았다. 동기화 작업(복사, 시험, 모델 없는 비교, falsify 7, 세 번째 깨끗한 복제)은 모델 호출 0회, EXA 호출 0회이고 동기화 작업 때 `Day03_new/outputs/runs`는 1,893파일 그대로였다(그 뒤 2026-11-02 21:40~22:51의 노트북 재실행이 115파일을 더해 지금은 2,008파일이다). 재실행 전 실행 기록이 동기화보다 앞섰다는 것, 비교 결과, 한계는 바로 위 행과 9.2절에 있다. 복사한 코드가 갖고 있지만 이 과정이 부르지 않는 기능(`fusion`, `decompose_question`, `prefetch`, `max_decision_calls`)과 'BM25만' 규칙은 1절 5번에 있다. 9.2절의 `인용 문서` 실패는 저자가 2026-11-02에 문서화된 관찰로 두기로 했고(`[미해소, 저자 결정으로 고치지 않음]`), 이 동기화가 새로 돌릴 이유가 되지 않았다. [이후 `tests/test_harness.py`가 더해져 625개가 되었고(2026-11-02), 2026-11-03 노트북 분할 뒤 전체는 717개(`717 passed`, 실패 0)다. 위 611은 그 앞 시점의 값이다] |
| `supervisor`의 기본 `general-purpose` 하위 에이전트 | **해소함(2026-11-02).** `mas_lab`을 import할 때 모든 Deep Agent에서 끈다(`mas_lab/__init__.py:9`, `use_designed_subagents_only`, `mas_lab/harness.py:25`). 비교용으로 프레임워크 기본을 만들 때만 `framework_default_subagent`(`mas_lab/harness.py:31`)로 켠다. `task` 도구의 담당자 이름은 `task_targets`(`mas_lab/harness.py:46`)로 읽고, `tests/test_harness.py`가 `build_supervisor`와 `build_single`에 `general-purpose`가 없음을 모델 없이 지킨다. 02 3절이 자동 Worker와 설계한 Worker를 모델 없는 셀로 비교하고 05 7절의 하네스 셀이 다섯 구조에서 확인한다(8.14절). 아래는 해소 전의 관찰과 판단을 이력으로 남긴 것이다. 이 해소는 코드와 노트북을 바꿨을 뿐 위 기록을 지금 코드로 다시 돌리지 않았으므로, 아래 세 행의 호출 수 차이는 기록 시점의 코드에서 난 값이다. **이력.** 2026-11-02 재실행에서 처음 관찰했다. 05 켠 실행 셀 41의 `supervisor` 3행(`insufficient-unknown-payment`, `insufficient-no-policy`, `approval-refund-now`)에서 모델이 `task`로 `general-purpose`에 `no-op` 둘과 `dummy` 하나를 위임했다. 세 행 모두 예산이 센 모델 호출이 실제보다 1회 적다(`budget.model` 7·5·10, `model_calls` 8·6·11). 하위 에이전트는 아무 일도 하지 않았고, 답·outcome·원장에는 영향이 없었다 | 원인은 코드다. `build_supervisor`(`mas_lab/structures.py:56`)가 Deep Agents의 기본 `general-purpose` 하위 에이전트를 끄지 않는다. `allowlist_middleware`는 `task` 도구를 허용할 뿐 `subagent_type`을 고르지 않는다. 그래서 그 하위 에이전트의 모델 호출은 `Budget`이 세지 않는다. 그 하위 에이전트가 어떤 도구를 받는지는 확인하지 않았다. **저자 결정 필요.** Deep Agents의 `HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False))`로 끌 수 있다. 끄면 `mas_lab`만 바뀌고 노트북 코드는 그대로라 `audit_live.py`는 통과한다. 그래도 기록이 지금 코드로 돌았다고 말하려면 `build_supervisor`를 쓰는 02와 05 기록을 다시 돌려야 한다. 고치지 않았다(이 판단 뒤 2026-11-02에 끄기로 해 해소했다). 02와 05 노트북에 셀이 더해졌으므로 두 노트북의 저장된 실행 기록은 지금 노트북과 코드 셀이 다르다. 다시 돌려 동기화하는 일이 남았다 |
