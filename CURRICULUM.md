# SDS AX 심화 과정 Day01\~08 커리큘럼

2026-10-31 기준

## 과정 개요

이 과정은 8일 동안 LangGraph 기초에서 출발해 RAG, 멀티에이전트, 평가, 하네스 분석, 추론 서빙, Guardrail까지 다룹니다. 성공 기준은 코드가 돌아가는 것이 아니라 수강생이 그 코드를 자기 말로 설명하는 것입니다(`AGENTS.md:7-8`). 진도는 Day01부터 번호 순서로 진행합니다(`AGENTS.md:10`).

**공통 환경:** 설치는 저장소 루트에서 `uv sync --locked`를 한 번 실행하고, 실습은 각 Day 폴더에서 `uv run`으로 합니다(`AGENTS.md:28`, `AGENTS.md:37-40`). 예외는 두 가지입니다. Day06은 Python 프로젝트가 없는 소스 읽기 과제이고, OpenViking은 `Day02/runtime/openviking`의 별도 환경을 씁니다(`AGENTS.md:32-33`).

**Day02_new:** `Day02_new/`는 Day02와 나란히 놓인 새 버전으로 노트북 `00-Setup`~`06-Lab-DeepAgents-RAG`(00~06)를 따라가며 Agentic RAG를 배웁니다. 아래 Day02 항목은 그대로 두며, Day02_new는 병렬 선택지입니다. 루트 환경을 쓰고 `ANTHROPIC_API_KEY`를 `Day02_new/.env`에 따로 둡니다(`Day02_new/README.md`).

**Day03_new:** `Day03_new/`는 Day03과 나란히 놓인 새 버전으로 노트북 `00-Setup`~`06-Lab-Research-Agents`(00~06)를 따라가며 Workflow와 Agent의 경계부터 Multi-Agent 선택 기준까지 배웁니다. 아래 Day03 항목은 그대로 두며, Day03_new는 병렬 선택지이고 채점 과제는 없습니다. 루트 환경을 쓰고 `ANTHROPIC_API_KEY`와 `EXA_API_KEY`를 `Day03_new/.env`에 둡니다. 00의 키 확인 셀이 두 키를 모두 확인하고 EXA는 06의 필수 실습에서 씁니다(`Day03_new/README.md`).

**읽는 법:** 학습 항목은 Day가 아니라 내용으로 묶었고, 번호는 전 과정에서 하나로 이어집니다. 앞서 정리한 항목 1\~20은 번호를 그대로 두고, Day04\~08 내용을 항목 21부터 추가했습니다. 각 Day의 확인 질문은 저자 제안이며 수업 자료에 있는 문구가 아닙니다.

## 학습 항목 지도

학습 항목은 11단계 41개입니다. 1\~6단계(항목 1\~20)는 주로 Day01\~03이, 7\~11단계(항목 21\~41)는 Day04\~08이 맡습니다. 아래 표에서 ●는 그 단계를 주로 가르치는 Day, ○는 입문하거나 다시 쓰는 Day입니다.

| 단계 | 항목 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 그래프 기본기 | 1\~3 | ● | ○ | ○ |  |  |  |  |  |
| 2. 근거 있는 RAG | 4\~10 | ○ | ● | ○ |  |  |  |  |  |
| 3. Deep Agents와 Skills | 11\~13 |  | ● |  | ○ | ○ |  | ○ | ○ |
| 4. 멀티에이전트 구조 | 14\~18 | ○ |  | ● |  |  |  |  |  |
| 5. 운영 안전성 | 19 |  | ○ | ● |  | ○ |  |  | ○ |
| 6. 효과 입증 | 20 |  | ● | ● |  | ○ |  |  | ○ |
| 7. Skills와 MCP 연결 | 21\~24 | ○ |  |  | ● |  |  |  |  |
| 8. Agent 평가 | 25\~28 |  |  | ○ |  | ● |  |  |  |
| 9. Harness 분석 | 29\~31 |  |  |  |  |  | ● | ○ | ○ |
| 10. 모델 서빙 | 32\~34 |  |  |  |  |  |  | ● | ○ |
| 11. Guardrail | 35\~41 | ○ |  |  |  |  |  |  | ● |

항목별 자료 위치는 다음과 같습니다. **굵은 파일**은 학생이 직접 구현하는 파일입니다.

| # | 학습 항목 | 먼저 만나는 곳 | 핵심 실습 | 다시 쓰는 곳 |
| --- | --- | --- | --- | --- |
| 1 | State, 노드, 엣지, 조건부 분기 | Day01 `03-LangGraph-Building-Graphs` | Day01 같은 노트북 | Day03 `02_adaptive_rag.py` |
| 2 | 도구 호출과 에이전트 루프 | Day01 `02-LangGraph-Tools`, `01-LangGraph-Agents` | Day01 같은 노트북 | Day02 `04_rag_with_skills.py` |
| 3 | 구조화된 출력 | Day01 `05-LangGraph-Structured-Output` | Day01 같은 노트북 | Day02 `src/day02/agents/factory.py` |
| 4 | 기본 RAG 흐름 | Day01 `02-LangGraph-Naive-RAG` | Day03 `01_baseline_rag.py` | Day02 `04_rag_with_skills.py` |
| 5 | 전처리와 청킹 | Day01 `10-LangGraph-Retrieval` | Day02 `01_preprocess.py` | Day02 `09_compare.py` |
| 6 | 적재와 중복 방지 | Day02 `02_ingest.py` | Day02 `02_ingest.py` | Day03 `08_web_enrichment.py` |
| 7 | 하이브리드 검색과 합류 | Day02 `03_search.py` | **Day02 `07_fusion_student.py`** | Day02 `09_compare.py` |
| 8 | 근거 검증과 인용 | Day01 `03-LangGraph-Add-Groundedness-Check` | **Day02 `08_citation_student.py`** | Day03 `common/evaluation.py` |
| 9 | 기준일과 문서 버전 | Day02 `day02 ask --as-of` | **Day02 `10_version_challenge.py`** | Day03 `entity`·`as_of`·`thread` scope |
| 10 | 표와 멀티모달 근거 | Day02 `06_multimodal.py` | **Day02 `11_table_challenge.py`** | - |
| 11 | `create_deep_agent` | Day02 `src/day02/agents/factory.py` | Day04 `coding_skills/agent.py` | Day07 `task.md`, Day08 `00_baseline_agent.py` |
| 12 | Skills로 답변 형식 분리 | Day02 `04_rag_with_skills.py` | Day02 `skills/` | Day04 `SKILLS_GUIDE.md` |
| 13 | 세션과 턴별 재검색 | Day01 `01-LangGraph-Add-Memory` | **Day02 `12_refresh_challenge.py`** | Day05 여러 턴 Episode, Day08 `04_memory_permissions.py` |
| 14 | 순차 구조와 Context 분리 | Day03 `03_sequential_rag.py` | Day03 같은 파일 | Day03 `task.md` |
| 15 | 라우터 | Day01 조건부 엣지 | Day03 `04_router_rag.py` | - |
| 16 | 병렬 fan-out과 reducer | Day01 `03-LangGraph-Building-Graphs`, `11-LangGraph-Branching`, `08-LangGraph-State-Customization` | **Day03 `05_parallel_rag.py`** | Day03 `task.md` |
| 17 | Supervisor와 재계획 | Day01 `01-LangGraph-Supervisor` | Day03 `06_supervisor_rag.py` | **Day03 `11_recovery_challenge.py`** |
| 18 | Handoff와 담당자 유지 | Day01 `02-LangGraph-Multi-Agent-Collaboration` | **Day03 `07_handoff_rag.py`** | - |
| 19 | 예산, Context 선택, 지연 결과, 동시 적재 | Day02 `src/day02/evidence.py` `Budget` | **Day03 `10`·`11`·`12_*_challenge.py`** | Day05 Episode 한도, Day08 `guardlab/budget.py` |
| 20 | 통제 실험과 짝 비교 | Day02 `09_compare.py` | **Day02·Day03 `13_mini_pjt.py`** | Day05 `07_compare_candidate.py`, Day08 `06_compare.py` |
| 21 | Skill 작성과 선택 | Day04 `SKILLS_GUIDE.md` | Day04 `coding_skills/skills/`, `실습.md` | Day08 `project_guide.md` |
| 22 | 실행 근거 저장과 답변 대조 | Day04 `coding_skills/run_files.py` | Day04 `evidence/` 대조 | Day08 `outputs/<번호>/<run_id>/runs.jsonl` |
| 23 | MCP 서버와 도구 계약 | Day01 `01-LangGraph-MCP-Tutorial` | **Day04 `work/my-mcp/server.py`** | - |
| 24 | 질문 강화와 업무 상태 | Day04 `build_mcp/README.md` | **Day04 `work/my-mcp/workflow.py`, `evidence.py`, `skills/requirements-interview/SKILL.md`** | - |
| 25 | 정책을 시나리오로 작성·검수·동결 | Day05 `01_draft_scenarios.py` | Day05 `01b_refine_goldens.py`, `02_freeze_dataset.py` | Day05 `오전.md` |
| 26 | 실행 기록과 원인 가설 | Day05 `03_record_baseline.py` | Day05 `04_inspect_traces.py` | Day05 `오후.md` |
| 27 | 평가기와 Judge 검수 | Day05 `05_evaluate_runs.py` | Day05 `learner_evaluator.py`, `06_review_judge.py` | Day05 `gold_agent_eval.py` |
| 28 | 개선 비교, 회귀, 최종 확인 | Day05 `07_compare_candidate.py` | Day05 `08_promote_regression.py`, `09_report_decision.py` | - |
| 29 | 여섯 책임으로 소스 읽기 | Day06 `HARNESSES.md` | Day06 하네스 4종 | Day08 `guardlab/harness.py` |
| 30 | 근거 수준 구분 | Day06 `AGENTS.md` §3 | Day06 하네스 4종 | - |
| 31 | Claude Code·GJC 개발환경 구성 | Day06 `task.md` | Day06 Mini PJT | 최종 프로젝트 작업 경로 |
| 32 | vLLM 서버 호출과 reasoning 분리 | Day07 `runpod_model_call.py` | Day07 `runpod_openai_reasoning.py` | Day07 `task.md` |
| 33 | 추론 속도 최적화 | Day07 강의 PDF | Day07 강의 PDF | - |
| 34 | dcode 설정 | Day07 `dcode_task.md` | Day07 과제 4개 | Day08 `dcode-analysis/` |
| 35 | Input Guard 검사 범위 | Day01 `04-LangGraph-Guardrail` | Day08 `01_input_guard.py` | Day08 `task.md` |
| 36 | 권한 검사 위치 | Day08 `02_action_guard.py` | Day08 같은 파일 | Day08 `06_compare.py` |
| 37 | 공개 경계 검사 | Day08 `03_output_guard.py` | Day08 같은 파일 | Day08 `07_lfm_encoders.py` |
| 38 | 파일 권한과 메모리 오염 | Day08 `04_memory_permissions.py` | Day08 같은 파일 | - |
| 39 | HITL 승인 바인딩 | Day01 `02-LangGraph-Human-In-The-Loop` | Day08 `05_hitl_approval.py` | - |
| 40 | Guard 모델 비교 | Day08 `08_guard_models.py` | Day08 `task.md` | - |
| 41 | 방어를 빼고 비교하기 | Day08 `06_compare.py` | Day08 같은 파일 | - |

## Day01\~Day03: 기본기에서 멀티에이전트까지

Day01은 LangGraph API를 익히고, Day02는 RAG 하나를 끝까지 만들며, Day03은 같은 RAG를 7가지 구조로 확장해 비교합니다. 채점 과제는 Day02와 Day03에 있습니다.

### Day01. LangGraph 기본기

**목표:** 그래프, 도구, 에이전트, 메모리, 멀티에이전트의 기본 API를 직접 실행합니다. 원본은 외부 튜토리얼이고 출처는 `Day01/UPSTREAM.md`에 있습니다.

**배울 항목:** 1, 2, 3 중심. 4, 5, 8, 13, 15\~18, 23, 35, 39를 입문합니다.

아래 우선순위는 뒤 Day에서 쓰는지를 기준으로 한 제안입니다. Day01 README의 권장 순서는 PART 01\~05 뒤 Appendix라서(`Day01/README.md:185`), RAG 노트북은 마지막에 나옵니다.

| 우선순위 | 노트북 | 다음 Day와의 연결 |
| --- | --- | --- |
| 필수 | `03-LangGraph-Building-Graphs`, `11-LangGraph-Branching`, `08-LangGraph-State-Customization` | Day03 fan-out과 reducer |
| 필수 | `01-LangGraph-Agents`, `02-LangGraph-Tools`, `05-LangGraph-Structured-Output` | Day02 Agent |
| 필수 | `02-LangGraph-Naive-RAG`, `03-LangGraph-Add-Groundedness-Check`, `10-LangGraph-Retrieval` | Day02 RAG |
| 필수 | `01-LangGraph-Supervisor`, `02-LangGraph-Multi-Agent-Collaboration` | Day03 Supervisor, Handoff |
| 권장 | `01-LangGraph-MCP-Tutorial`, `04-LangGraph-Guardrail`, `02-LangGraph-Human-In-The-Loop` | Day04, Day08 |
| 뒤로 미룸 | `02-LangGraph-Memory-Postgres`, `Agent-Chat-UI-OSS`, `C-GraphRAG/`, `B-Use-Cases/` | 확인한 범위에서 뒤 Day의 선수 자료가 아님 |

**평가:** 채점 자료가 없습니다.

**확인 질문:**

- 이 분기는 어떤 상태값으로 갈리는가?
- 모델이 도구를 고르는 것과 코드가 실행하는 것은 어떻게 다른가?
- 형식이 틀린 응답은 어떻게 처리되는가?

### Day02. 근거 있는 RAG 한 개 완성

**목표:** 전처리, 적재, 검색, 답변 형식 선택, 인용 검증까지 RAG 하나를 Python으로 끝까지 만듭니다. Agent는 DeepAgents, 저장소는 로컬 OpenViking, 답변 형식은 Skills입니다(`Day02/AGENTS.md:5-7`).

**배울 항목:** 5\~13, 20.

| 순서 | 파일 | 상태 | 항목 |
| --- | --- | --- | --- |
| 1 | `00_prepare.py`\~`03_search.py` | 제공 | 5, 6, 7 |
| 2 | `04_rag_with_skills.py`\~`06_multimodal.py` | 제공 | 10, 11, 12, 13 |
| 3 | `07_fusion_student.py`, `08_citation_student.py` | 학생 구현, 선행 과제 | 7, 8 |
| 4 | `09_compare.py` | 제공 | 20 |
| 5 | `10`·`11`·`12_*_challenge.py` | 학생 구현, 과제 A·B·C | 9, 10, 13 |
| 6 | `13_mini_pjt.py` | 학생 실행, 과제 D | 20 |

**평가:** A 25 + B 25 + C 30 + D 20 = 100점입니다(`Day02/AGENTS.md:26`). 공개 테스트 통과는 계약만 검증하고, 나머지 점수는 실제 연결, 추가 반례, 분석에서 나옵니다(`Day02/AGENTS.md:41-42`). `task.md`는 채점 없는 자유 실습입니다.

**비용:** `day02 ask`는 한 번에 모델 호출 최대 10회입니다. `pytest`와 과제 파일 실행은 API를 부르지 않습니다(`Day02/AGENTS.md:198-200`).

**확인 질문:**

- 단순 합산 순위가 깨지는 반례는 무엇인가?
- 같은 질문의 답이 기준일에 따라 왜 달라지는가?
- 후속 질문에서 왜 이전 근거를 재사용하면 안 되는가?

### Day03. 멀티에이전트 구조 비교

**목표:** Day02의 RAG를 7가지 구조로 확장하고, 어떤 실패가 왜 개선됐고 추가 비용이 무엇인지 통제 실험으로 설명합니다. 역할 수를 늘리는 것 자체는 목표가 아닙니다(`Day03/AGENTS.md:5-7`).

**배울 항목:** 14\~20.

| 순서 | 파일 | 상태 | 항목 |
| --- | --- | --- | --- |
| 1 | `00_prepare.py`\~`04_router_rag.py` | 제공 | 1, 4, 14, 15 |
| 2 | `05_parallel_rag.py`, `07_handoff_rag.py` | 학생 구현, 배점 없는 선수 실습 | 16, 18 |
| 3 | `06_supervisor_rag.py`, `08_web_enrichment.py` | 제공 | 6, 17 |
| 4 | `09_compare.py` | 제공 | 20 |
| 5 | `10`·`11`·`12_*_challenge.py` | 학생 구현, 과제 A·B·C | 19 |
| 6 | `13_mini_pjt.py` | 학생 실행, 과제 D | 20 |

**평가:** A 25 + B 30 + C 25 + D 20 = 100점입니다(`Day03/AGENTS.md:61`). 공개 함수 테스트에 해당하는 점수는 28점뿐입니다(`Day03/WORKSHEET.md:151`). 개선되지 않은 결과도 통제된 실험과 정확한 원인 분석이 있으면 분석 점수를 받습니다. `task.md`는 채점 없는 자유 실습입니다.

**비용:** `09_compare.py` 기본 설정은 7구조 × 6사례 × 3회 + judge로 수백 회, 수십 분입니다. 처음에는 `CASES=["simple"]`, `REPEATS=1`로 시작합니다(`Day03/AGENTS.md:212-216`).

**확인 질문:**

- 동시에 쓴 결과는 어떻게 합쳐지는가?
- Supervisor와 달리 Handoff에서 최종 답은 누가 하는가?
- 늦게 도착한 성공 결과나 오래된 Worker의 쓰기를 왜 거절하는가?

## Day04\~Day06: 연결, 평가, 소스 분석

Day04는 절차와 실제 도구를 연결하고, Day05는 그 결과를 업무 기준으로 평가하며, Day06은 실제 하네스의 소스를 읽습니다. 세 Day 모두 점수를 매기는 채점표는 없습니다.

### Day04. Skills와 MCP로 만드는 두 Deep Agent

**목표:** 코딩 에이전트와 질문 강화형 에이전트를 만들며, 업무 절차를 Skill로 분리하고 MCP 도구·상태 저장·근거 파일과 연결합니다(`Day04/README.md:3-5`).

**배울 항목:** 21\~24. 11, 12를 다시 씁니다.

| 순서 | 자료 | 하는 일 | 항목 |
| --- | --- | --- | --- |
| 1 | `coding_skills/prepare.py`, `agent.py` | 실패하는 CSV 집계 테스트를 재현하고 고친다 | 11, 22 |
| 2 | `실습.md` 연습 문제 6개 | Skill 선택 조건을 바꾸고 새 Skill을 만든다 | 12, 21 |
| 3 | `build_mcp/README.md` 1\~4단계 | 함수를 MCP 도구로 공개하고, 답변 기록·확정 조건·재시작 유지를 만든다 | 23, 24 |
| 4 | `build_mcp/README.md` 5\~6단계 | 근거 파일을 모으고 그 파일을 읽는 Skill을 작성한다 | 21, 22, 24 |
| 5 | `coding_skills/task.md`, `build_mcp/task.md` | 자유 실습 | 21, 23 |

**평가:** 채점 과제가 없고 제출물은 다섯 줄 기록입니다. 요청, 관찰한 호출·결과, 수정 위치와 이유, 재실행 결과, 아직 확인하지 못한 것을 남깁니다(`Day04/README.md:111`). 단, `work/my-mcp/`의 네 파일은 직접 쓰는 것이 학습 목표라 힌트 정책을 적용합니다(`Day04/AGENTS.md:37-42`).

**비용:** `coding_skills/verify_agent.py`는 모델 약 25\~45회, `build_mcp/verify_agent.py`는 약 20\~35회입니다(`Day04/AGENTS.md:87-88`). `build_mcp/verify.py`와 `verify_scripts.py`는 모델을 부르지 않습니다.

**확인 질문:**

- 발견한 Skill과 실제 사용한 Skill을 어떻게 구분하는가?
- 명세 확정 조건을 모델이 아니라 서버에서 검사하는 이유는 무엇인가?
- 검사가 통과한 것과 Skill 절차를 따른 것은 어떻게 다른가?

### Day05. 업무 기준의 Agent 평가

**목표:** 주문 취소·결제 환불·예약 재고 복원 사례로 평가 기준을 만들고, 실패 근거를 읽은 뒤 한 조건을 바꿔 개선과 회귀를 설명합니다(`Day05/README.md:3-4`). 수업 시간은 6시간으로 가정합니다(`Day05/README.md:25`).

**배울 항목:** 25\~28. 13, 19, 20을 다시 씁니다.

| 순서 | 파일 | 수강생의 판단 | 항목 |
| --- | --- | --- | --- |
| 1 | `00`·`01`·`01b`·`02` | 정책을 기대 상태와 금지 행동으로 어떻게 바꾸고 검수할 것인가 | 25 |
| 2 | `03`·`04` | Agent가 실제로 무엇을 했고, 원인 가설과 대안 가설은 무엇인가 | 26 |
| 3 | `05`·`06` | 평가기가 중요한 오류를 잡고, Judge가 사람의 실패 판정을 통과시키지 않는가 | 27 |
| 4 | `07`·`08`·`09` | 한 조건의 변경으로 무엇이 좋아지고 나빠졌고, 승인할 근거가 있는가 | 20, 28 |
| 자유 | `오전.md`, `오후.md` | 관심 문서로 Golden Dataset과 Agent를 만들고 Langfuse 기록으로 개선점을 찾는다 | 11, 25, 27 |

**평가:** 점수표는 없고 `09_report.md`가 결과물입니다. 평가 기준, 원인 가설, 한 조건의 변경, 개선과 회귀, 남은 미확인을 포함합니다(`Day05/README.md:200`). `HOLD`의 사유는 오류, 회귀, 정책 위반, 검수 미완료, 최종 확인 부족입니다(`Day05/README.md:197`).

**비용:** 기본 3문항 × 2회에서 `03`은 Agent 최대 약 72회, `07`은 후보 Agent 최대 약 72회에 Judge 약 12\~36회입니다(`Day05/README.md:210-212`). Langfuse에도 기록이 쓰입니다.

**확인 질문:**

- 응답, 업무 상태, 정책 준수는 어떻게 다른가?
- 관찰한 사실과 원인 가설을 왜 나눠 적는가?
- `scripted` 결과를 개선율로 보고하면 안 되는 이유는 무엇인가?

### Day06. AI Agent Harness 소스 분석

**목표:** 하네스 4종의 소스를 읽고, 여섯 책임(지침·도구·실행 제어·상태·검증·기록)을 어느 모듈이 맡고 무엇이 비어 있는지 근거와 함께 설명합니다. 하네스 순위를 매기는 것은 목표가 아닙니다(`Day06/AGENTS.md:5-9`).

**배울 항목:** 29\~31.

| 순서 | 폴더 | 볼 것 | 루프 시작점 |
| --- | --- | --- | --- |
| 1 | `pi/` | 최소 루프 | `pi/packages/agent/src/agent-loop.ts:156` |
| 2 | `gajae-code/` | 그 위에 얹은 워크플로 | `gajae-code/packages/agent/src/agent-loop.ts:3612` |
| 3 | `deepseek-harness/` | 루프를 플러그인으로 나눈 구조 | `deepseek-harness/packages/core/agent-loop/src/agent.ts:72` |
| 4 | `ouroboros/` | 루프 바깥의 여러 에이전트 조율 | `ouroboros/src/ouroboros/orchestrator/runner.py:8454` |

분석은 읽기가 기본이고 설치·실행 없이 할 수 있습니다. 분석 세션은 클론 폴더가 아니라 `Day06/`이나 저장소 루트에서 시작합니다(`Day06/AGENTS.md:33`). 오후 Mini PJT는 수업 폴더 밖의 WSL 경로에 Claude Code와 GJC 개발환경을 구성합니다(`Day06/AGENTS.md:172`).

**평가:** 채점 대상 파일이 없습니다(`Day06/AGENTS.md:158`). 다만 여섯 책임 정리본은 수강생이 직접 읽고 쓰며, AI 조교는 근거 수준을 점검합니다(`Day06/AGENTS.md:184-186`).

**비용:** 읽기만 하면 없습니다. 하네스를 실행하면 수강생의 구독이나 API 크레딧을 쓰고, 특히 ouroboros 진화 루프는 최대 30세대까지 돕니다(`Day06/AGENTS.md:92`).

**확인 질문:**

- 이 기능은 실행 경로에서 확인했는가, 정의만 확인했는가?
- worktree가 왜 보안 격리가 아닌가?
- 모델의 완료 요청과 검증된 완료는 어떻게 다른가?

## Day07\~Day08: 모델 서빙과 Guardrail

Day07은 모델을 직접 서빙하는 쪽의 구조와 속도를 다루고, Day08은 Agent 방어를 어디에 둘지 비교합니다. 두 Day 모두 수업 실습은 채점하지 않고, 최종 프로젝트는 Day08에서 별도로 안내합니다.

### Day07. vLLM 기초와 추론 속도 최적화

**목표:** RunPod에 띄운 vLLM(GLM-5.3-Flash)을 호출하고, Deep Agent와 dcode를 그 환경에서 써 봅니다(`Day07/README.md:3`).

**배울 항목:** 32\~34. 11을 다시 씁니다.

| 순서 | 자료 | 다루는 내용 | 항목 |
| --- | --- | --- | --- |
| 1 | 강의 PDF 1장 | vLLM 실행 형태, 요청 경로, 샘플링 | 32 |
| 2 | 강의 PDF 2\~3장 | 성능 지표, Prefill과 Decode, KV Cache | 33 |
| 3 | 강의 PDF 4\~6장 | Continuous Batching, Prefix Caching, Quantization, Speculative Decoding, 분산 실행 | 33 |
| 4 | `runpod_model_call.py`, `runpod_openai_reasoning.py` | `ChatOpenAI` 호출, reasoning과 content 분리, 스트리밍 | 32 |
| 5 | `task.md` | GLM-5.3-Flash와 EXA Tool로 Deep Agent 만들기 | 11, 32 |
| 6 | `dcode_task.md` | Prompt Caching, 모델별 Harness Profile, 메모리, Self-Improving Middleware | 34 |

**평가:** 채점 과제가 없습니다(`Day07/README.md:5`). `dcode_task.md`는 OpenAI·Anthropic·Google 모델 호출을 허용하지 않고 WSL에서만 진행합니다(`Day07/README.md:56-58`).

**비용:** RunPod Pod는 시간당 약 $18.36이고 강사가 부담합니다(`Day07/README.md:74`, `Day07/AGENTS.md:26`). EXA와 OpenRouter 호출은 수강생 크레딧을 씁니다.

**Day07_new:** `Day07_new/`는 Day07과 나란히 놓인 이론 중심 새 버전으로 노트북 `00-Setup`~`06-Tool-Calling-Errors`(00, 01, 02a, 02b, 02c, 03, 04, 04b, 05, 06)를 따라갑니다. 앞 330분(01~04b: 서빙 기초 60, KV block 45, KV 공유 45, 최근 모델의 KV 통제 `02c` 45, 파라미터와 측정 50, Quantization 40, KV 운영과 LMCache `04b` 45)이 이론이고 이어서 Agent 연결 60분, Tool Calling 오류 60분을 다룹니다. 위 Day07 항목과 `Day07/`의 스크립트·`task.md`·`dcode_task.md`는 그대로 실습 자료이며, Day07_new는 병렬 선택지입니다. GPU·API 키·RunPod 없이 실행되고, 서버 접속 셀은 `RUN_POD = False`로 잠겨 있으며 Pod 동작은 저자가 확인하지 않았습니다(`Day07_new/README.md`).

**확인 질문:**

- Prefill과 Decode는 각각 어떤 지표에 영향을 주는가?
- Prefix Caching이 줄이는 시간과 줄이지 못하는 시간은 무엇인가?
- `ChatOpenAI`로는 reasoning이 왜 보이지 않는가?

### Day08. Guardrail 방어 위치 비교

**목표:** 같은 보고 Agent에 같은 공격을 넣고 방어 배치만 바꿔, 공격이 어느 경로로 들어와 어느 경계에서 막혔는지 실행 결과로 봅니다. 근거는 Agent의 답변이 아니라 전송함·초안·실행 기록·정책 파일 상태입니다(`Day08/README.md:7-8`). 수업 시간은 순수 6시간입니다(`Day08/README.md:26`).

**배울 항목:** 35\~41. 11, 13, 19, 20을 다시 씁니다.

| 파일 | 시간 | 눈으로 보는 것 | 항목 |
| --- | --- | --- | --- |
| `00_baseline_agent.py` | 25분 | 정상 업무 완료와 평가기가 읽는 상태 | 11 |
| `01_input_guard.py` | 55분 | 검사 범위를 도구 결과로 넓혔을 때의 차이와 과잉 차단 | 35 |
| `02_action_guard.py` | 65분 | 부모 middleware가 놓치는 Subagent 경로와 도구 래퍼 | 36 |
| `03_output_guard.py` | 55분 | 최종 답변만 검사할 때 전송함·초안에 남는 유출 | 37 |
| `04_memory_permissions.py` | 45분 | 두 세션 사이의 메모리 오염과 권한 규칙 순서 | 13, 38 |
| `05_hitl_approval.py` | 45분 | 승인 뒤 인자 변경과 중복 전달, 바인딩 | 39 |
| `06_compare.py` | 50분 | 방어를 하나 뺄 때 열리는 경로 | 20, 41 |
| `07_lfm_encoders.py` | 선택 20분 | 전용 탐지기의 토큰 분절과 놓친 구간 | 37 |
| `08_guard_models.py` | 선택 20분 | 분류기 6종의 미탐·오탐·UNKNOWN·지연 | 40 |

**평가:** 번호 파일에는 채점 과제가 없고, `task.md`는 채점 없는 연습입니다(`Day08/AGENTS.md:6`). 자체 평가 기준을 가진 최종 프로젝트는 `project_guide.md`에 있으며, dcode 소스로 Coding Assistant를 만듭니다(`Day08/project_guide.md:3-4`).

**비용:** `06_compare.py` 기본 상수는 6실행, 모델 60\~90회입니다. `pytest`, `scripted`, `05`, `07`은 모델 호출이 없습니다(`Day08/AGENTS.md:79-83`).

**확인 질문:**

- 부모 middleware는 왜 Subagent의 도구 호출을 못 보는가?
- 탐지가 실패해도 방어가 성공할 수 있는 이유는 무엇인가?
- approve 클릭만 믿으면 어떤 일이 생기는가?

## 커리큘럼 공백과 미확인 사항

가장 큰 공백은 Day01에 Deep Agents와 Skills 입문이 없는데 Day02가 바로 쓴다는 점입니다. Skill 작성 기준은 Day04에서야 나옵니다.

| 공백 | 근거 | 영향 |
| --- | --- | --- |
| Deep Agents·Skills 입문 없음 | Day01 노트북 54개 검색 결과 해당 호출 0건. Day02 `src/day02/agents/factory.py`는 `create_deep_agent` 기반 | Day02 첫 Agent 예제에서 개념이 처음 나온다 |
| 하이브리드 검색 입문 없음 | Day01 노트북에서 BM25·RRF·rerank 검색 0건 | 채점 선행 과제 07이 Day02에서 처음 만나는 개념이다 |
| HITL이 중간에 끊김 | `Day02/src/day02/agents`, `Day03/common`, `Day04/build_mcp`, `Day04/coding_skills`, `Day05/business_lab`에서 `interrupt(` 호출과 checkpointer 연결 0건. `Day04/build_mcp/agent.py:129`는 checkpointer를 주입하지 않는다고 적음 | Day01에서 배운 뒤 이 폴더들에서는 쓰지 않고, Day08 `05_hitl_approval.py`에서 다시 나온다 |
| Day03 문서와 코드 차이 | `Day03/README.md:3`은 DeepAgents 0.7.32 기준 환경이라고 쓰지만, `Day03/*.py`와 `Day03/common`에 import가 없고 `common/day02_bridge.py`는 검색·근거 계약만 가져옴 | 수강생이 Day03에서 `create_deep_agent`를 찾게 된다 |
| 키와 기록 방식 전환 | Day01 `.env.example`은 OpenAI·LangSmith, Day04는 OpenRouter, Day05는 Langfuse | Day마다 `.env`를 다시 설정해야 한다 |
| 강의 링크가 git 제외 경로 | `Day05/README.md:5`, `Day08/README.md:5`가 `Lecture_Note/`를 가리킴 | 저장소만 받은 수강생에게는 링크가 열리지 않는다 |

**아직 확인하지 못한 것:**

- Day01 노트북은 키워드 검색과 README 목차로 연결했고, 본문을 끝까지 읽거나 실행하지 않았습니다.
- Day07은 강의 PDF의 목차와 제목만 확인했습니다. 다른 Day의 강의 PDF는 이 문서에 반영하지 않았습니다.
- 루트 공용 환경(`deepagents` 0.7.32)에서 실제 모델 호출은 이번 환경 통합 검증에서 성공을 확인하지 못했습니다. Day04 MCP 실제 검증은 키 인증 오류(401)로 멈춰 있습니다.
- Windows와 Linux 설치는 검증하지 않았습니다.
