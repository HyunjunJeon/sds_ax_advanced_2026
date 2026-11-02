# Day02_new — Agentic RAG 노트북 과정

Day01처럼 노트북을 위에서 아래로 실행하며 배우는 새 버전의 Day02입니다. 한 교시가 노트북 하나이고, 노트북마다 한 가지만 가르칩니다. 이 폴더는 기존 `../Day02/`와 **나란히 놓인 새 버전**입니다. `../Day02/`는 그대로 남아 있고 이 폴더가 그것을 대체하거나 고치지 않습니다.

## 이 과정이 가르치는 것

Agentic AI의 기본 개념에서 출발해 도구 호출, Agent Skills, 검색(Retrieval) 설계를 차례로 익히고, 마지막에 `create_deep_agent`로 사내 문서 질의응답 RAG Agent를 직접 조립합니다. 근거(Evidence)를 찾아 인용하고, 고객(entity)과 기준일(as_of)로 범위를 걸고, 예산(budget) 안에서만 검색하는 것이 이 과정이 내내 쓰는 틀입니다. 검색 인덱스는 메모리 안에서 만들고 별도 서버는 필요 없습니다.

## 설치와 실행

설치는 **저장소 루트에서 한 번**, 실행은 **`Day02_new/`에서** 합니다.

```bash
# 저장소 루트에서 (한 번만)
uv sync --locked

# 이 폴더에서
cd Day02_new
uv run jupyter lab
```

- 이 폴더 안에서 `uv sync`를 실행하지 않습니다. 환경은 루트에 하나만 있습니다.
- 이 폴더에는 `pyproject.toml`이 없습니다. `uv run`이 루트 환경을 찾아 씁니다.

## API 키 설정 (필수)

이 과정은 실제 모델만 씁니다. **키가 둘 필요합니다: `ANTHROPIC_API_KEY` 하나와 Decision API 키 하나(`TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY` 중 하나, 또는 Azure OpenAI).** 둘 다 `Day02_new/.env`에 **본인이 직접** 채웁니다. 키가 없으면 노트북은 해당 셀에서 한국어 안내와 함께 멈춥니다. 키 없이 도는 경로, 건너뛰기, 대체 경로는 없습니다. Anthropic 키만 있어서는 00의 판정 API 셀부터 멈춥니다. 수업 전에 보낼 안내문 초안은 [docs/draft_student_notice.md](docs/draft_student_notice.md)에 있습니다(저자가 `[저자 확인]` 자리를 채우기 전에는 보내지 않습니다).

- Claude 쪽 제공자는 Anthropic이고 `ChatAnthropic`으로 부릅니다. 기본 모델은 `claude-sonnet-5-5`, 기본 추론 깊이(effort)는 `medium`입니다(`.env.example`의 `DAY02_MODEL`, `DAY02_EFFORT`).
- 다른 Day는 OpenRouter를 쓰지만 이 폴더는 같은 키를 읽지 않습니다. `ANTHROPIC_API_KEY`는 **따로** 발급받아야 하고, `.env`는 이 폴더의 것만 읽습니다.
- **Decision API(판정 API)는 Claude로 대신할 수 없습니다.** 질문 하나에 참/거짓 확률을 숫자로 돌려주는 호출이라 문턱값(gate)을 코드로 걸 수 있습니다. 04~06에서 쓰고, `rag_lab/decisions.py`의 `make_decider`가 `DAY02_DECISION_BACKEND` 또는 TYPESAFE, OPENROUTER, OPENAI, AZURE 순서로 키가 있는 첫 공급자를 고릅니다. **Azure OpenAI는 선택지입니다.** 키(`AZURE_OPENAI_API_KEY`)에 더해 엔드포인트(`DAY02_AZURE_ENDPOINT`)와 배포 이름(`DAY02_AZURE_DEPLOYMENT`)도 `.env`에 채워야 하며, 하나라도 비면 `make_decider`가 멈춥니다. Azure와 OpenRouter 경로는 모의 전송(단위 시험)으로만 확인했고 **실제 호출로는 확인하지 않았습니다.** **질문 문장과 근거(원문 조각)가 고른 공급자에게 전송됩니다.** 외부로 보내면 안 되는 내용은 넣지 않습니다. 키가 비어 있으면 00의 판정 API 셀에서 멈춥니다.
- 재순위(reranker)는 로컬 교차 인코더 `BAAI/bge-reranker-v2-m3`를 내 컴퓨터(CPU)에서 돌립니다. 키가 필요 없고 처음 쓸 때 모델 파일 **약 2.1GB**를 내려받으므로 `00-Setup.ipynb`에서 수업 전에 미리 받아 둡니다. CPU float32에서 질문 하나당 0.68초(후보 평균 18개), 후보 50개면 5.42초를 쟀습니다(한 대의 컴퓨터, `docs/retrieval_benchmarks.md`의 52행과 54행).
- Anthropic에는 임베딩 API가 없습니다. dense 검색은 로컬 임베딩 `intfloat/multilingual-e5-small`을 내 컴퓨터(CPU)에서 돌립니다. 키가 필요 없고, 처음 쓸 때 모델 파일 약 470MB를 내려받습니다(이후에는 캐시).

```bash
cp .env.example .env
```

`.env`를 열어 `ANTHROPIC_API_KEY`와 Decision API 키 하나에 **본인의 키를 직접 입력**합니다. `.env`는 커밋하지 않으며, 값을 노트북 출력이나 채팅에 붙여 넣지 않습니다. 실제 호출이 있는 셀은 실행 직전에 `announce`로 규모를 한 줄 알려 주고, Claude 비용은 본인 Anthropic 키로, Decision API 비용은 고른 공급자의 본인 계정으로 청구됩니다.

## 셀 표지: 따라하기 · 바꿔보기 · 깨뜨리기 · 내 것 만들기

코드 셀 위의 설명 줄에 표지가 붙어 있습니다. 한 개념을 쉬운 것에서 어려운 것 순서로 오르는 사다리입니다.

| 표지 | 하는 일 | 쓰는 법 |
|---|---|---|
| `[따라하기]` | 있는 그대로 실행합니다 | 실행하기 전에 출력이 어떨지 한 줄로 예측하고, 실행 후 맞았는지 봅니다 |
| `[바꿔보기]` | 값 하나만 바꿔 다시 실행합니다 | 바꾼 값과 달라진 출력을 짝지어 말해 봅니다 |
| `[깨뜨리기]` | 일부러 실패시켜 어디서 멈추는지 봅니다 | 오류는 실패가 아니라 관찰입니다. 왜 그 지점에서 멈췄는지 설명합니다 |
| `[내 것 만들기]` | 내 질문·내 도구·내 값으로 직접 만듭니다 | 쓰기 전에 결과를 먼저 예측하고, 실행 후 예측과 비교합니다 |

첫 `[따라하기]`는 SLA 코퍼스나 숨은 도우미 함수 없이 시작하도록 만들었습니다. 도우미는 쓰이기 직전의 보이는 셀에서 정의됩니다.

## 수업 구성

수업은 다섯 개의 Part와 하나의 실습으로 나뉘고, 각각 노트북 하나에 대응합니다.

| 수업 구성 | 노트북 |
|---|---|
| Part 1. Agentic AI의 기본 구성 | `01-Agentic-AI-Basics.ipynb` |
| Part 2. Function Calling과 Tool 기본 | `02-Function-Calling-and-Tools.ipynb` |
| Part 3. Agent Skills 이론과 기본 실습 | `03-Agent-Skills.ipynb` |
| Part 4. 왜 아직도 RAG인가와 검색 설계 | `04-Retrieval-Design.ipynb` |
| Part 5. Production Agentic RAG 설계 | `05-Production-Agentic-RAG.ipynb` |
| 실습: Tool + Skill + RAG 기본 통합 (최소 Agentic RAG Loop, Search Tool과 RAG-Answer 도메인 지식 Skill 연결, Skill Trigger와 Tool Calling 동작 확인) | `06-Lab-DeepAgents-RAG.ipynb` |

`00-Setup.ipynb`는 수업 전에 하는 사전 점검이라 Part에 들어가지 않습니다.

실습(06)의 범위는 노트북의 실제 구성을 따릅니다. 6단계 중 **1~3단계가 기본 통합**입니다. 1단계에서 검색 도구를 만들고, 2단계에서 Agent를 만들고, 3단계에서 Skill을 연결한 뒤 Agent가 어떤 도구를 불렀는지 확인합니다. **4~6단계는 그 위에 얹는 확장**입니다. 4단계는 검증, 5단계는 기록 읽기, 6단계는 `ask_two_phase`(Jev 게이트와 질문 분해)입니다. Skill 트리거 테스트(트리거되어야 하는 질문과 near-miss)는 06이 아니라 `03-Agent-Skills.ipynb`의 6절과 7절에 있습니다. 06의 6단계 빠른 경로에서 `loaded_skills`는 모델이 Skill을 트리거해 읽었다는 뜻이 아니라 코드가 주입했다는 뜻입니다.

2026-11-02에 00~06의 모든 코드 셀을 자세하고 따라가기 쉽게 다시 썼습니다(단계 주석, 이름 붙인 중간 변수, 한국어 docstring). 호출하는 모델, 도구, 인자와 순서는 같게 유지했습니다.

## 노트북 순서

번호 순서대로 진행합니다. 분은 각 노트북 첫 셀의 값입니다. 호출 수와 비용은 아래 "실측 비용"의 한 번 실행 값입니다.

| 노트북 | 분 | 주제 |
|---|---:|---|
| `00-Setup.ipynb` | 10 | 수업 전 사전 점검: 키 상태(Anthropic + Decision API), 판정 API 한 번(`make_decider`), `rag_lab`, Kiwi, Deep Agents 동작 확인 |
| `01-Agentic-AI-Basics.ipynb` | 60 | LLM 호출, workflow, Agent의 차이와 `create_deep_agent` 첫 실행. 2절에서 같은 질문을 도구 없이, 도구 하나 묶기, 직접 실행으로 세 번 물어봅니다 |
| `02-Function-Calling-and-Tools.ipynb` | 60 | 모델은 요청하고 코드가 실행한다: `@tool`, 스키마, 실패(8절: 오류 정보를 돌려주는 도구와 예외를 던지는 도구). 호출 예산과 허용 목록은 02에서 다루지 않고 05의 결정 1과 결정 2에서 다룹니다 |
| `03-Agent-Skills.ipynb` | 60 | `SKILL.md` 형식, 점진적 공개, 트리거 테스트(6절 near-miss, 7절 읽으면 안 되는 질문) |
| `04-Retrieval-Design.ipynb` | 60 | 1절 왜 여전히 RAG인가(전체 문서를 프롬프트에 넣는 시도를 [깨뜨리기]로 확인), 청킹, 범위 필터, BM25·dense·RRF, 어려운 질문 recall·MRR, 넓은 후보와 원 질문 재순위, Jev 관문(질문 분해, 출처 보강), AutoRAG와 다른 점, PDF 쪽 판독 |
| `05-Production-Agentic-RAG.ipynb` | 60 | 운영형 설계 결정 아홉 가지(인용 검증, 후속 턴, 실행 기록)와 선택 결정: 빠른 답변과 Jev 게이트 세 개(분해, 인용 관련성, 추가 확인)의 비용 측정, 게이트가 실패하면 검증으로 기우는 [깨뜨리기] |
| `06-Lab-DeepAgents-RAG.ipynb` | 60 | 실습: 1~3단계가 기본 통합(융합 검색+재순위 도구, Agent, Skill 연결, 도구 호출 확인), 4~6단계가 확장(검증, 기록 읽기, `ask_two_phase`의 Jev 게이트와 질문 분해). 한 조건만 바꿔 다시 재기. 05 11절의 완성된 조립을 여기서는 직접 조립합니다 |

두 가지 상수가 규모를 정합니다.

- 03의 `RUN_OPTIONAL`: 기본 `False`입니다. 경쟁 Skill 셋 비교 셀(약 70회)은 이 상수와 관계없이 기본 경로에서 돕니다. 전체 트리거 측정(2026-11-02 `03-optional-copy` 실행에서 79회)과 Skill 있음/없음 비교(같은 실행에서 17회)는 `True`로 바꿔야 돌고, 돌지 않으면 "실행하지 않았습니다"라고 출력합니다. 한 시간 수업에서 기다릴 수 없는 규모라 돌리지 않기로 한 선택입니다.
- 06의 `MAX_CASES`: 기본 `3`이고, 대표 사례 셀과 내 질문 셀의 호출 수가 이 값에 비례합니다. 전후 비교 셀은 `MAX_CASES`가 아니라 `REPEATS`(기본 `1`)와 질문 수에 비례합니다. 올리면 사례 수에 비례해 시간과 비용이 늘어납니다. 사례 3개는 관찰이지 통계가 아닙니다.

같은 질문도 실행마다 다르게 끝날 수 있습니다. 모델이 어떤 도구를 부르고 어디서 멈추는지가 매번 달라서, 한 번의 결과를 결론으로 삼지 않고 "1회 관찰"로 읽습니다.

## 실측 비용

아래 표는 저장소 루트에서 다음 명령(`cost_report`)을 실행한 결과를 그대로 옮긴 것입니다.

```bash
uv run --no-sync python Day02_new/tests/cost_report.py
```

| 노트북 | 모델 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |
|---|---|---:|---:|---:|---:|---:|
| 00-Setup | claude-sonnet-5-5 | 2 | 16.1 | 3898 | 133 | 0.0024 |
| 00-Setup | jev-1.14.0 | 1 |  | 348 | 22 | 0.0000 |
| 01-Agentic-AI-Basics | claude-sonnet-5-5 | 29 | 51.9 | 87454 | 2685 | 0.0970 |
| 02-Function-Calling-and-Tools | claude-sonnet-5-5 | 23 | 42.2 | 36678 | 1857 | 0.0691 |
| 03-Agent-Skills | claude-sonnet-5-5 | 87 | 126.3 | 459078 | 17272 | 0.3553 |
| 03-optional-copy | claude-sonnet-5-5 | 184 | 422.0 | 959902 | 48400 | 0.7235 |
| 04-Retrieval-Design | claude-sonnet-5-5 | 3 | 112.0 | 5535 | 932 | 0.0204 |
| 04-Retrieval-Design | jev-1.14.0 | 5 |  | 1861 | 110 | 0.0001 |
| 05-Production-Agentic-RAG | claude-sonnet-5-5 | 42 | 132.1 | 252098 | 11058 | 0.3142 |
| 05-Production-Agentic-RAG | jev-1.14.0 | 4 |  | 3237 | 159 | 0.0001 |
| 06-Lab-DeepAgents-RAG | claude-sonnet-5-5 | 54 | 259.8 | 616554 | 20679 | 0.7703 |
| 06-Lab-DeepAgents-RAG | jev-1.14.0 | 54 |  | 40126 | 1985 | 0.0017 |
| **합계** | | 304 | 740.4 | 1506867 | 56892 | **1.6307** |
| **선택 측정** (수업 합계에서 제외) | | 184 | 422.0 | 959902 | 48400 | **0.7235** |

- **표의 모든 행은 2026-11-02에 개정한 노트북을 실제 API로 다시 실행한 기록입니다.** 00~06과 `03-optional-copy`가 같은 날 한 번씩 돌았고, 실행 오류는 없었습니다(`finished` true, `errors` 비어 있음). 이전 기록은 `outputs/live/history/`에 보존되어 있습니다. 이번 재실행에서 노트북 소스를 고친 곳은 없습니다.
- **같은 노트북도 실행마다 값이 다릅니다.** 모델이 도구를 부르는 횟수가 달라서, 예를 들어 03의 본문은 기본 실행에서 87회, `03-optional-copy`에서 88회였습니다. 표의 값은 한 번의 관찰이지 보장이 아닙니다.
- 한 번 실행한 값이고 한 대의 컴퓨터에서 쟀습니다(1회 실행, 1대). 평균이나 보장이 아닙니다.
- **수업 합계는 00~06 노트북의 합(304회, 1.6307달러)입니다.** 304회에는 Decision API 64회(`jev-1.14.0` 행: 00이 1, 04가 5, 05가 4, 06이 54)가 들어 있고 Claude 호출은 240회입니다. 1.6307달러는 Claude 비용과 Decision API 입력 비용(약 0.0019달러)을 합한 값입니다. `03-optional-copy` 행은 03의 복사본에서 `RUN_OPTIONAL = True`로 돌린 **선택 측정**이고(184회, 0.7235달러), 수업 합계에 넣지 않았습니다. 마지막 줄이 그 값을 따로 보여 줍니다. 03 본 행은 `RUN_OPTIONAL = False`, 06은 `MAX_CASES = 3`일 때의 값입니다.
- **Decision API(`jev-*`) 비용은 공식 단가로 계산했지만 출력 단가는 가정입니다.** 입력 10억 토큰당 $42(출처: https://typesafe.ai/, 2026-11-01)를 적용했습니다. 공식 페이지에 출력 단가가 없고, 2차 출처(https://www.eesel.ai/blog/typesafe-jev-pricing)가 출력은 무료라고 하므로 출력은 0으로 계산했습니다. 출력 단가가 실제로 붙으면 Decision API 비용은 표보다 큽니다. 이 단가가 맞는지는 TypeSafe 청구서가 기준입니다. OpenRouter, OpenAI, Azure를 고르면 그 계정의 청구서가 기준이며, 이 표의 `jev-1.14.0` 행 단가를 그 공급자에 쓰지 않습니다. 단가표에 없는 다른 모델 이름은 계속 `단가 미확인`입니다.
- 비용은 사용 기록에 남은 모델 기준으로 계산됩니다. 모델이나 effort를 바꾸면 값이 달라지며, 위 명령이 그 기록으로 다시 계산합니다.
- "초"는 그 컴퓨터에서 노트북이 돈 기계 시간일 뿐입니다. 학생이 읽고 생각하는 시간은 들어 있지 않으며, 60분 수업 시간에 맞는지는 리허설하지 않았습니다(60분은 검증되지 않은 설계값입니다).
- Claude 단가는 Anthropic 1차 API 요금(2026-10 기준)이고, 기록된 입력 토큰에 든 캐시 읽기와 캐시 쓰기를 각각 캐시 단가(sonnet-5-5는 100만 토큰당 $0.2, $2.5)로 따로 계산합니다. 이번 기록에서 캐시 쓰기는 관찰되었습니다(전체 271,563 토큰, 그중 1시간 TTL 0). 값은 실제로 기록된 토큰으로 계산한 측정값입니다. 캐시 쓰기 필드가 없는 예전 기록 64줄은 0으로 계산되어 실제보다 적을 수 있습니다(이 64줄에는 캐시 필드가 원래 없는 Decision API 줄도 센 것이라 실제 영향은 그보다 작습니다). 자세한 단가는 명령 출력 하단에 나옵니다.

### 예상 호출 수와 실제 호출 수

"예상"은 각 노트북의 코드 셀이 `announce`로 알리는 `model_calls` 값을 더한 추정이고, "실제"는 위 표의 2026-11-02 기록입니다. 예상은 모델이 도구를 몇 번 부르느냐에 따라 어긋납니다.

| 노트북 | 예상 호출(announce 기준) | 실제 Claude | 실제 Decision API |
|---|---|---:|---:|
| 00-Setup | 3회(판정 API 1회 포함) | 2 | 1 |
| 01-Agentic-AI-Basics | 약 30회 | 29 | 0 |
| 02-Function-Calling-and-Tools | 약 25회 | 23 | 0 |
| 03-Agent-Skills | 약 132회 | 87 | 0 |
| 03-optional-copy | 약 232회 | 184 | 0 |
| 04-Retrieval-Design | 최대 4회(Claude) | 3 | 5 |
| 05-Production-Agentic-RAG | 약 58회 | 42 | 4 |
| 06-Lab-DeepAgents-RAG | 약 77회 | 54 | 54 |

- 차이가 큰 곳은 03(132 대비 87), 03-optional-copy(232 대비 184), 05(58 대비 42), 06(77 대비 54)입니다. 모두 실제가 예상보다 적고, 기록에서 확인되는 것은 모델이 도구를 부르는 횟수가 `announce`가 가정한 상한보다 적었다는 점까지입니다. 정확한 원인은 기록만으로는 가리지 못합니다.
- 03-optional-copy의 184회 중 본문이 88회, 선택 측정 두 셀이 96회입니다(트리거 측정 79회, Skill 있음/없음 비교 17회).
- 이번 재실행에서 소스를 고친 live 실행은 없습니다.

## 채점은 없습니다

이 과정에는 채점하는 과제가 없습니다. 각 노트북의 "직접 해보기"와 확인 질문은 자기 결과를 자기 말로 설명해 보기 위한 것입니다. 06 실습도 채점하지 않고, 실패한 기록도 그 실습의 결과입니다. 잘 나온 반복만 남기거나 실패한 행을 지우지 않습니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `rag_lab/` | 노트북이 가져다 쓰는 부품(코퍼스, 검색기, 근거, 예산, 검증, 모델·임베딩 생성, 판정 API `decisions.py`와 게이트 `gates.py`) |
| `skills/` | 노트북이 읽는 Skill 폴더 |
| `data/` | 사내 문서(`business/`)와 사례(`cases.jsonl`) |
| `data/cases_hard.jsonl`, `data/gold_hard.jsonl`, `data/cases_hard2.jsonl`, `data/gold_hard2.jsonl` | 04가 쓰는 동결한 어려운 질문 14개(`cases_hard`)와 두 번째 묶음 22개(`cases_hard2`: 키워드 없음, 일상어, 여러 문서, 순위 구분)와 각 정답표. 04는 두 번째 묶음에서 recall과 함께 MRR(`rag_lab/evaluation.py`의 `mrr`)을 잽니다. **평가 전용**이고 정답표는 **검토 전 초안**(`review_status: draft`)입니다. 실행 경로(Agent, 도구, 프롬프트)에서 읽지 않으며, 결과에 맞추려고 고치지 않습니다 |
| `benchmarks/` | 저자용 측정 도구(`measure.py`, `allganize.py`, `make_sample_pdf.py`, 판정 API 점검 `check_decider.py`). 수강생 실습에 필요하지 않습니다 |
| `tests/` | 저자용: 단위 테스트, 노트북 검사기, 실제 실행기(`run_live.py`), 비용 계산(`cost_report.py`: 표, `--cells`, `--check-docs`). 가짜 모델은 `tests/fakes.py`에만 있고 단위 테스트 전용 |
| `docs/DESIGN.md` | 과정 설계 문서 |
| `docs/gold_review_sheet.md` | 저자용 gold 검수 시트. AI가 원문과 교차 확인한 초안이며 모든 판정이 `미검수`입니다. 사람이 검수하기 전에는 gold를 확정으로 취급하지 않습니다 |
| `docs/rehearsal_sheet.md` | 저자용 60분 리허설 시트. 계획 분만 채워져 있고 `실제 분`은 비어 있습니다. 아직 아무도 리허설하지 않았습니다 |
| `outputs/` | 실행 기록(커밋하지 않음) |
| `docs/draft_student_notice.md`, `docs/draft_check_questions.md` | 저자용 초안: 수업 전 학생 안내문, 다시 쓴 확인 질문. 저자가 검수하기 전에는 확정이 아닙니다 |
| `.env.example` | 키 양식(`ANTHROPIC_API_KEY`와 Decision API 키 하나: `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, 또는 Azure의 키·엔드포인트·배포 이름) |
