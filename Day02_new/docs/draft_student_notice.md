# 수업 전 안내 (초안, 학생에게 보내기 전에 저자가 고칠 것)

**초안입니다.** 대괄호로 표시한 `[저자 확인]` 자리는 이 저장소에서 확인하지 못한 내용이라 비워 두었습니다. 이 문서에는 키 값이 하나도 없습니다.

---

## Day02_new 수업 전에 준비할 것

수업 첫 시간에 바로 실습하려면 아래 네 가지를 **수업 전에** 끝내 두세요.

### 1. 키가 두 개 필요합니다

| 키 | 용도 | 어디서 받나 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude 모델 호출(01~06 전부) | 본인의 Anthropic 계정에서 직접 발급합니다. 다른 Day의 OpenRouter 키와 **다릅니다.** |
| Decision API 키 하나 | 04~06의 판정 호출(질문을 나눌지, 인용이 관련 있는지 등) | 아래 표 중 하나를 고릅니다. |

Decision API 키는 아래 중 **하나만** 있으면 됩니다. 이 호출은 Claude로 대신할 수 없습니다. 키가 없으면 `00-Setup`의 판정 API 셀에서 멈춥니다.

| 공급자 | `.env`에 쓸 이름 | 발급 |
|---|---|---|
| TypeSafe (기본) | `TYPESAFE_API_KEY` | [저자 확인: 수강생용 발급 절차 또는 강사 배포 방법. 공급자 사이트는 https://typesafe.ai/ 입니다] |
| OpenRouter | `OPENROUTER_API_KEY` | OpenRouter 계정에서 발급. 이 경로가 보내는 모델 id는 아직 확인하지 못했습니다(`.env.example`에 그렇게 적혀 있습니다). 쓰기 전에 `00-Setup`의 판정 셀이 통과하는지 먼저 보세요. |
| OpenAI | `OPENAI_API_KEY` | OpenAI 계정에서 발급 |
| Azure OpenAI | `AZURE_OPENAI_API_KEY`, 그리고 `DAY02_AZURE_ENDPOINT`, `DAY02_AZURE_DEPLOYMENT` | Azure 리소스에서 발급. 키만 넣으면 안 되고 엔드포인트와 배포 이름도 채워야 합니다. |

여러 개를 채웠다면 `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, Azure 순서로 키가 있는 첫 번째를 씁니다. 직접 고르려면 `DAY02_DECISION_BACKEND`에 `typesafe`, `openrouter`, `openai`, `azure` 중 하나를 씁니다.

### 2. 키는 이 파일에만 넣고 아무에게도 보여 주지 않습니다

```bash
cd Day02_new
cp .env.example .env
```

`Day02_new/.env`를 열어 본인 키를 **직접** 채웁니다. 이 폴더는 이 폴더의 `.env`만 읽습니다.

- 키를 채팅, 메신저, 이슈, 노트북 출력, 화면 공유에 붙여 넣지 않습니다.
- `.env`는 커밋하지 않습니다(`.gitignore`에 들어 있습니다). 키가 든 파일을 올렸다면 즉시 그 키를 폐기하고 새로 발급받으세요.
- 도움이 필요하면 키 값 대신 **어느 셀에서 어떤 메시지가 나왔는지**만 알려 주세요.

### 3. 질문과 근거 문서가 고른 공급자에게 전송됩니다

04~06의 판정 호출은 **질문 문장과 근거(원문 조각)를 그대로 고른 Decision API 공급자에게 보냅니다.** Claude 호출은 Anthropic으로 갑니다. 회사 기밀이나 개인정보가 든 내용은 실습 질문과 문서에 넣지 마세요. 공급자를 바꾸면 데이터가 가는 곳도 바뀝니다.

### 4. 모델 파일 두 개를 수업 전에 내려받아 둡니다

수업 중에 받으면 시간이 크게 듭니다. 연결이 좋은 곳에서 `00-Setup.ipynb`를 먼저 실행해 두세요.

| 모델 | 용도 | 크기 |
|---|---|---|
| `BAAI/bge-reranker-v2-m3` | 후보를 다시 줄 세우는 재순위(04~06) | 약 2.1GB |
| `intfloat/multilingual-e5-small` | dense 검색 임베딩(04~06) | 약 470MB |

두 모델은 내 컴퓨터(CPU)에서 돌고 키도 비용도 필요 없습니다. 한 번 받으면 캐시에 남습니다. 합쳐서 약 2.6GB이니 디스크 여유도 확인하세요.

---

## 예상 비용

`tests/cost_report.py`가 `outputs/live/`의 실행 기록에서 계산한 값입니다(2026-11-01 기준 저자 1회 실행, 기록한 토큰 수와 이 저장소에 적은 단가 기준). **학생 한 명이 01~06을 한 번씩 순서대로 돌릴 때와 같은 구성이지만, 학생마다 바꿔 보는 값과 모델 응답이 달라 실제 금액은 달라집니다.**

| 노트북 | 모델 호출 | 비용(USD) |
|---|---:|---:|
| 00-Setup | 3 | 0.0113 |
| 01-Agentic-AI-Basics | 24 | 0.0822 |
| 02-Function-Calling-and-Tools | 18 | 0.0487 |
| 03-Agent-Skills | 82 | 0.3306 |
| 04-Retrieval-Design | 7 | 0.0102 |
| 05-Production-Agentic-RAG | 34 | 0.1964 |
| 06-Lab-DeepAgents-RAG | 97 | 0.7221 |
| 합계 | 265 | **1.4015** |

- 이 합계에는 03의 선택 복사본(181회, 0.7864 USD)이 **들어 있지 않습니다.** 선택 실습을 하면 그만큼 더 듭니다.
- 비용의 대부분은 Claude입니다(Claude 1.3998 USD, Decision API 0.0017 USD). Decision API 금액은 TypeSafe의 입력 10억 토큰당 42 USD 단가로 계산했고 출력은 무료라는 가정입니다(`cost_report.py`의 주석). OpenRouter, OpenAI, Azure를 고르면 **그 계정의 청구서가 기준**이며 이 표의 값이 아닙니다.
- 06의 마지막 비교 셀은 `REPEATS = 1`일 때의 값입니다. 2로 올리면 훨씬 늘어납니다(이전 기록: 67회, 1.31 USD).
- 호출이 있는 셀은 실행 직전에 `announce`로 규모를 한 줄 알려 줍니다. 그 줄을 읽고 진행하세요.

[저자 확인: 수업 전에 이 표의 숫자를 `python tests/cost_report.py`의 최신 출력으로 다시 맞출 것. `--check-docs`는 `README.md`와 `AGENTS.md`만 검사하고 이 파일은 검사하지 않는다.]

---

## 수업 전 점검 순서

1. `uv sync --locked`를 저장소 루트에서 한 번 실행했습니다.
2. `Day02_new/.env`에 키 두 개를 채웠습니다(값은 누구에게도 보이지 않았습니다).
3. `Day02_new`에서 `00-Setup.ipynb`를 끝까지 실행했고, 판정 API 셀이 통과했으며 모델 파일 두 개를 받았습니다.
4. 막히면 오류 메시지가 나온 셀 번호와 메시지 문장을 가지고 질문합니다.
