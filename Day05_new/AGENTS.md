# AGENTS.md — Day05_new: Agent 평가·모니터링·Self-Improving 노트북 과정

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day05_new 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** 주문 취소·결제 환불·예약 재고 복원 업무 에이전트 하나를 두고, 그럴듯한 답이 왜 업무 성공의 근거가 못 되는지(01),
성공의 기준을 Golden Dataset으로 어떻게 고정하는지(02), 정답이 없는 운영 trace를 무엇으로 어떤 것부터 채점하는지와 궤적을 어떻게 판정하는지(03a, 03b),
평가와 무엇이 다르고 무엇을 언제 경보하는지(04), 평가와 모니터링을 하나의 운영 루프로 묶는 법(05),
에이전트가 자기 trace로 나아지게 하려면 무엇을 고정하고 무엇을 열어야 하는지(06)를 배운다.
평가 순서는 **Code → Jev → Judge**다. Code가 못 보는 자유 문장만 Jev(Decision API)가 보고, 확신이 낮을 때만 Judge(에이전트와 같은 OpenGateway `deepseek/deepseek-v4.1-flash-ultrafast`, effort `xhigh`)가 본다 (`docs/DESIGN.md` 2절, 6절, 개정 1).
설계 근거와 사전 등록은 [docs/DESIGN.md](docs/DESIGN.md)에 있지만 수강생용 문서가 아니다.

**`Day05/`는 이 폴더와 별개이고 그대로 둔다.** 이 폴더의 작업은 `Day05/`를 바꾸지 않는다.
**이 폴더는 강의 자료(PDF·발표 자료)에 의존하지 않는다.** 범위는 노트북, `docs/DESIGN.md`, `eval_lab/`, `data/`의 코드와 데이터로 정해진다.
이 폴더 밖의 자료에 있다는 내용을 이 폴더의 사실처럼 말해 달라고 하면, 여기서 확인되는 것만 답하고 나머지는 "확인이 필요합니다"라고 말한다.

---

## 0. 채점 과제가 없다 — 그래도 설명은 해야 한다

번호 노트북에는 채점 과제가 없다. 모든 코드가 완성돼 있고 수강생은 실행하고 읽고 바꿔 본다.
그래서 루트 AGENTS.md 4장의 단계적 힌트 정책(L0~L3)은 **여기에 적용하지 않는다.** 코드를 읽고 설명하는 요청, `직접 해보기` 셀을 같이 푸는 요청은 자유롭게 돕는다.

단, 루트의 성공 기준은 그대로다. **수강생이 그 셀을 자기 말로 설명할 수 있어야 한다.**
- 셀을 고쳐 달라고 하면 고치기 전에 "이 셀이 무엇을 보여 주려는 건가요?"를 먼저 묻는다.
- `확인 질문`의 답과 `직접 해보기`에서 수강생이 적는 판단(내 사례, 내 기준, 내 임계값, 내 가설)을 대신 써 주지 않는다. 출력의 어느 칸이 근거인지 찾게 한다.
- 모델이 부르는 실행의 한 번 결과는 "1회 관찰"이라고 부르게 한다. 같은 사례도 실행마다 달라진다.
- 모르면 모른다고 말한다. 이 저장소에 없는 함수·플래그·파일을 지어내지 않는다. 문서와 코드가 다르면 코드가 정답이고 차이를 알린다.

용어는 자료의 한국어 용어를 그대로 쓴다: 근거(Evidence), 원문, 적재(ingest), 담당자(owner), 예산(budget), 인용, 기준일(as_of), 고객(entity).
Golden, Episode, Trace, Rule, Evaluator, Jev, Judge, holdout, dev, release는 노트북의 영어 그대로 쓴다. 답변은 한국어로 하고 사실 주장에는 `파일:줄`을 붙인다.

---

## 1. 노트북 지도 (`docs/DESIGN.md` 4절)

| 노트북 | Part | 분 | 핵심 질문 |
|---|---|---|---|
| `00-Setup.ipynb` | 준비 | 10 | 키·연결·버전이 준비되었는가. 에이전트 모델·Jev·Judge 각 1회 |
| `01-Why-Evaluate.ipynb` | 1 | 40 | 그럴듯한 답이 왜 업무 성공의 증거가 못 되는가 |
| `02-Offline-Golden-Dataset.ipynb` | 2 | 60 | 무엇을 성공으로 볼지 어떻게 고정하는가 |
| `03a-Online-Eval-Trace-Selection.ipynb` | 3 | 45 | 정답이 없는 운영 trace를 무엇으로, 어떤 것부터 채점하는가 |
| `03b-Trajectory-Eval.ipynb` | 3 | 55 | 궤적의 순서를 어떻게 판정하고, 평가기는 어떻게 믿는가 |
| `04-Agent-Monitoring.ipynb` | 4 | 45 | 평가와 무엇이 다르고 무엇을 언제 경보하는가 |
| `05-Continuous-Operation.ipynb` | 5 | 45 | 평가와 모니터링을 어떻게 하나의 운영 루프로 묶는가 |
| `06-Lab-Self-Improving-Agent.ipynb` | 실습 | 90 | 자기 trace로 나아지게 하려면 무엇을 고정하고 무엇을 열어야 하는가 |

노트북은 00부터 번호 순서로 푼다. 건너뛰게 유도하지 않는다. 폴더에는 이 밖에 `eval_lab/`(지원 라이브러리), `data/`(시나리오·fixture·정책 문서), `docs/`, `tests/`(저자용)가 있다.

**Claude Code 실습 구성(`use_cc/`, 2026-11-05).** 수업 경로는 use_cc다. 같은 Part 1~5 + 실습을 Claude Code와 Langfuse 두 화면으로 하는 미션 카드(`use_cc/missions/m0`~`m6`)와 개념 문서(`use_cc/concepts/`, m0~m6, 노트북 하나에 문서 하나, 제목 번호는 노트북과 같다)로 진행하고, 노트북은 자습과 강사 시연용으로만 남는다. 수강생은 `use_cc/setup_sandbox.py`로 **저장소 밖**에 실습 폴더를 만들고 그 폴더에서 Claude Code를 연다. 실습 폴더에는 `concepts/`가 복사되고 노트북 사본은 없다. 실습 폴더의 규칙은 그 폴더의 `CLAUDE.md`(원본 `use_cc/sandbox/CLAUDE.md`)가 맡는다. 실습 폴더에는 holdout 내용이 없고(ID만), holdout은 `use_cc/tools/holdout_check.py`로만 연다. 수강생이 노트북 절을 물으면 같은 번호의 개념 문서 절(`use_cc/concepts/<id>.md`, 예: 노트북 02 3절은 `use_cc/concepts/m2.md` 3절)을 근거로 답한다. 이 저장소 안에서 수강생이 use_cc를 묻으면 `use_cc/README.md`를 가리킨다. **합성 배경 운영 로그(`synth_ops`).** 7일치 가상 운영 기록을 m0에서 한 번 수강생 본인의 Langfuse 프로젝트에 적재하고(`eval_lab/synth.py`가 오프라인 simulator Episode로 결정적으로 만들고 `use_cc/sandbox/tools/synth_load.py`가 올린다) m3a·m4·m5가 읽는다. 시간·지연·토큰·비용·generation은 합성이며 모델 이름은 `synthetic/deepseek-v4.1-flash-ultrafast`다. 합성 기록은 모델 성능이 아니고 m6의 replay 풀·holdout·PREREG P3·03b 메타평가에 쓰지 않는다(8장 6번).

---

## 2. 실행 규칙

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 한다. 이 폴더에는 `pyproject.toml`이 없고 `uv run`이 루트의 uv workspace 환경을 찾는다.

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day05_new
uv run jupyter lab          # 실행은 이 폴더에서
```

- 이 폴더 안에서 `uv sync`를 하지 않는다. 다른 Day에 필요한 패키지가 지워진다. 복구는 루트의 `uv sync --locked`다.
- `pyproject.toml`과 `uv.lock`을 이 폴더에 만들지 않는다.
- kernel의 작업 폴더가 `Day05_new`여야 `import eval_lab`이 된다.
- 실행 조건은 노트북 안의 변수와 셀이다(`RUN_EXERCISE`, `RUN_OPTIONAL`). 수강생 실습에는 명령행 플래그가 없다. `--flag`를 지어내 안내하지 않는다.
- 유료 스위치 `RUN_EXERCISE`, `RUN_OPTIONAL`은 기본 `False`다. 켜기 전에 그 셀의 `announce` 줄을 읽게 한다.
- 노트북의 모델·클라이언트는 `eval_lab.settings`, `eval_lab.decisions`, `eval_lab.notebook.langfuse_or_none`으로만 만든다. 이 규칙은 오프라인 실행기가 가짜로 갈아 끼우는 자리이기도 하다 (`tests/run_fake.py`).
- 산출물은 `outputs/`(`new_run_dir`, `eval_lab/notebook.py:55`)에 쓰고 git에서 제외한다 (`.gitignore`).

---

## 3. 키

`.env.example`을 `.env`로 복사해 **수강생이 직접** 채운다. 키는 `Day05_new/.env`에서 읽는다 (`eval_lab/settings.py:89`). 셸에 export한 키나 다른 Day의 키에 기대지 않는다. `.env`를 고친 뒤에는 kernel을 재시작한다.
`.env` 내용을 출력하지 않는다. 설정됨/미설정만 본다 (`key_status`, `eval_lab/settings.py:129`; `show_keys`, `eval_lab/notebook.py:78`). 키가 없어 실패하면 대신 넣어주지 않고 `.env.example`을 가리킨다 (`require`, `eval_lab/settings.py:139`).

| 키 | 필요한 곳 |
|---|---|
| `OPENGATEWAY_API_KEY` | 에이전트, Judge, 개선기 호출 전부. 모든 유료 셀. `DAY05_PROVIDER=anthropic`이면 대신 `ANTHROPIC_API_KEY` |
| Decision API 키 하나 (`TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` 중) | Jev 호출: 00, 02, 03a, 03b, 05. 01·04·06은 Jev를 부르지 않는다 |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (필요하면 `LANGFUSE_HOST`, 또는 Langfuse 화면의 `.env` 예시가 주는 `LANGFUSE_BASE_URL`. `LANGFUSE_HOST`가 우선) | Langfuse 셀에서만. 비어 있으면 노트북은 로컬 경로로 진행한다 (`langfuse_or_none`, `eval_lab/notebook.py:84`) |

- `DAY05_DECISION_BACKEND`가 비면 TYPESAFE, OPENROUTER, OPENAI, AZURE 순서로 키가 있는 첫 번째를 쓴다. 값을 정하면 그 백엔드만 본다. 에이전트 모델이 Jev를 대신하지 않는다 (`.env.example`).
- Azure는 키와 함께 `DAY05_AZURE_ENDPOINT`, `DAY05_AZURE_DEPLOYMENT`가 필요하다.
- 공급자: 기본 `opengateway`(`https://apis.opengateway.ai`, Anthropic Messages 호환). `DAY05_PROVIDER=anthropic`이면 `https://api.anthropic.com`과 `claude-sonnet-5-5`. 주소는 코드에 고정되어 있다 (`PROVIDERS`, `eval_lab/settings.py`).
- 기본값: 에이전트 `deepseek/deepseek-v4.1-flash-ultrafast` effort `medium`, Judge 같은 모델 effort `xhigh`, 개선기 effort `high`. `DAY05_MODEL`, `DAY05_EFFORT`, `DAY05_JUDGE_MODEL`, `DAY05_JUDGE_EFFORT`, `DAY05_IMPROVER_EFFORT`로 바꾼다 (`.env.example`).
- 다른 Day의 OpenRouter 키와 다른 키다. 모델 호출은 `max_retries=0`이라 429 같은 일시 오류가 숨지 않고 드러난다 (`eval_lab/settings.py:166`).
- 키를 로그·출력·결과 파일에 남기지 않는다. 저자용 `tests/check_secrets.py`가 `.env` 값이 폴더 안 파일에 들어갔는지 본다.

---

## 4. 비용

모든 모델 셀이 실제 호출이다. 유료 셀은 같은 셀 안에서 `announce`(`eval_lab/notebook.py:23`)가 실행 **직전에 규모를 한 줄로 고지**한다. 막지 않는다. 수강생이 자기 OpenGateway·Decision API 크레딧을 쓴다는 점을 상기시키고, 도우미가 대신 셀을 돌릴 때도 직전에 한 줄로 알린다.

**아래는 모두 예고 값이다. 저자 실측이 아니다.** 노트북 `announce` 인자를 읽은 상한 쪽 추정이며 아직 실제 키로 노트북을 끝까지 돌려 잰 적이 없다. "기본"은 `RUN_EXERCISE`, `RUN_OPTIONAL`이 모두 `False`인 실행이다. 칸은 에이전트 / Jev / Judge / 개선기 호출 수다.

| 노트북 | 기본 실행의 예고 | 스위치를 모두 켠 예고 |
|---|---|---|
| 00 | 1 / 1 / 1 / 0 | 1 / 2 / 4 / 0 |
| 01 | 0 / 0 / 0 / 0 | 12 / 0 / 0 / 0 |
| 02 | 72 / 12 / 36 / 0 | 72 / 12 / 36 / 0 |
| 03a | 0 / 20 / 60 / 0 | 96 / 30 / 90 / 0 |
| 03b | 0 / 4 / 36 / 0 | 0 / 4 / 48 / 0 |
| 04 | 0 / 0 / 0 / 0 (모든 셀 scripted) | 0 / 0 / 0 / 0 |
| 05 | 0 / 20 / 0 / 0 (backtest 셀) | 0 / 25 / 15 / 0 (`RUN_OPTIONAL`의 cascade 5건: Jev 5, Judge 15 추가) |
| 06 | 144 / 0 / 0 / 1 (pilot 72 + holdout 72) | 228 / 0 / 0 / 2 |

- 02는 두 스위치가 유료 호출을 만들지 않아 같은 값이다. 05의 `RUN_EXERCISE`도 무료다.
- **배경 운영 로그 적재(m0, `synth_load.py`)는 모델 호출 0회**다. Langfuse에는 trace 280개와 observation 약 4,796개(합 약 5,076 unit, `--dry-run`이 정확한 값을 먼저 보여 준다)가 들어가고, Hobby 플랜 한도는 월 50k unit이다. 한 번만 적재한다.
- 06의 holdout은 사례 3개 상한(72회)으로 고지한다. 현재 승인된 holdout 카드가 2개라 실제 상한은 이보다 24회 적다. 06은 의미 판정(Jev·Judge)을 부르지 않는다.
- `DESIGN.md` 13절의 계획 표는 노트북의 `announce` 인자를 옮겨 적은 것이다. 노트북이 바뀌면 그 셀의 `announce` 줄이 정답이다. 숫자를 말하기 전에 해당 셀의 `announce` 줄을 다시 본다.
- Decision API(Jev)는 질문과 state(요청·사건 요약·최종 상태·응답)를 공급자에게 보내고, Langfuse는 프롬프트·도구 입출력·점수를 받는다 (`docs/DESIGN.md` 14절). 서버 쪽 Judge를 켜면 수강생 키가 Langfuse LLM Connection에 저장된다. 켜기 전에 알린다.
- **DeepEval 텔레메트리는 꺼 둔다.** `eval_lab/__init__.py:7`이 `DEEPEVAL_TELEMETRY_OPT_OUT=1`을 `setdefault`로 설정한다(이미 정한 값은 그대로 둔다). 시험은 `tests/test_hygiene.py:28`이다. `eval_lab`을 import하기 전에 deepeval을 먼저 import하는 코드를 만들지 않는다. 노트북은 `tests/check_notebook.py`가 이 순서를 검사한다.

---

## 5. 확인되지 않은 것 (`docs/DESIGN.md` 16절)

실제 키로 돌린 노트북 결과는 아직 없다. 아래는 사실처럼 말하지 않는다.
- **00이 첫 실제 확인이다.** `ToolStrategy(Response)`가 `deepseek/deepseek-v4.1-flash-ultrafast`(`langchain-anthropic` 모델 프로필 없음)에서 구조화 응답을 반복해서 안정적으로 내는지(2026-11-05 1회 관찰에서는 냈다), Judge `max_tokens`가 충분한지(`_JUDGE_MAX_TOKENS = 32000`, `eval_lab/settings.py:43`; xhigh의 thinking이 한도를 답변과 나눠 쓴다)는 00의 한 번 호출로 처음 본다. 잘림이나 `StructuredOutputError`는 버그가 아니라 관찰 결과다.
- 실제 에이전트 모델·Jev·Judge 응답(Episode 1개 1회 관찰뿐), OpenGateway가 effort를 옮기는 방식, Langfuse 서버 쪽 동작(Rule·Evaluator 실행, Metrics API 응답, 집계 지연, 2026-11-16 이후 Cloud).
- DeepEval trace 필요 지표에 우리 원자료를 비공개 필드로 넣는 경로.
- scripted Episode가 실제 Langfuse에서 trace 하나로 묶이는지. OTel GenAI 규약의 안정화 여부. Dream-RSI 공식 코드 위치와 라이선스.
- 노트북 안에서 오프라인 가짜 모델로 돈 결과는 "구조가 끝까지 도는지"만 보여 준다. 가짜 출력으로 모델·정책의 우열을 말하지 않는다.

---

## 6. holdout 승인 게이트

`data/scenarios.json`의 holdout 카드 6개 중 **4개가 `review_status = "pending"` 초안**이다. 저자가 검수해 `approved`로 바꾸고 `reviewer`를 채우기 전에는 holdout 측정을 시작하지 않는다 (`docs/DESIGN.md` 12절 4번).
- `load_dataset(split="holdout")` 기본값은 **엄격**하다. 분할 안에 검수 전 카드가 하나라도 있으면 `ValueError("검수가 끝나지 않은 시나리오: ...")`를 던진다 (`eval_lab/dataset.py:22`, `eval_lab/dataset.py:54`). 저자 P3 측정이 이 기본값을 쓴다.
- `load_dataset(split="holdout", approved_only=True)`는 수업 시연용이다. 검수 전 카드를 건너뛰고 approved 카드만 돌려준다. 돌려주는 카드는 reviewer·source·review_reason·정책 버전 검사를 그대로 통과한다 (`eval_lab/dataset.py:29`, `eval_lab/dataset.py:45`). 06이 이 경로를 쓴다.
- `pending_ids(path, split=...)`는 초안 ID 목록을 준다 (`eval_lab/dataset.py:60`).
- 승인을 AI가 대신 하지 않는다. `review_status`나 `reviewer`를 고쳐 엄격 로드를 통과시키지 않는다. 사전 등록 P3은 holdout을 라운드 중 재생 풀·개선기 입력·임계값 선택에 쓰지 않고 마지막에 한 번만 연다고 정하고, P7은 holdout 사례를 개선기 입력에 넣지 않게 한다. 조교는 holdout 사례 내용을 수강생에게 보여 주거나 요약하지 않고, 실행 경로 밖에서 에이전트가 읽게 하지 않는다. 06은 승인된 카드를 마지막에 한 번, ID 수준(scenario_id, family_id, 최대 턴, 검수자)으로만 연다. 06.5는 P5 결과를 설명하려고 이어서 처리 카드 fixture의 상태(이미 취소 중이고 환불이 끝남)를 한 번 말한다. 카드의 요청 문장과 기대 상태는 보여 주지 않는다.

---

## 7. 저자용 도구 (수강생에게 권하지 않는다)

저장소 루트에서 실행한다. 명령은 모두 `uv run --no-sync python Day05_new/tests/<파일>` 형식이다.

- `check_prereg.py` — `docs/DESIGN.md`의 PREREG 블록이 `docs/prereg.sha256`과 같은지 본다. 종료 코드 0 일치, 1 불일치, 2 확인 불가 (`tests/check_prereg.py:1`). 호출 없음. 해시만 고쳐 통과시키지 않는다. 블록 밖(노트북 지도, 호출 규모 등)은 고쳐도 된다.
- `run_fake.py <노트북>... | --all` — 노트북을 가짜 모델·가짜 Langfuse·Langfuse 없음, 스위치 끔·켬 조합으로 끝까지 실행한다(노트북당 3회). 키와 네트워크 불필요. 마지막 줄 `run_fake: <ok>/<total> OK`.
- `check_notebook.py --all` 또는 `<노트북> --minutes N` — 구조 검사(시간표 합계, 표지, 유료 셀의 announce, 스위치 규칙, 키 패턴, deepeval보다 eval_lab을 먼저 import하는 순서, 저장된 출력). 호출 없음.
- `check_secrets.py` — `.env` 값이 `Day05_new` 안 파일에 새어 들어갔는지 본다. 값은 출력하지 않고 `LEAK <파일> <변수 이름>`만 낸다. 유출이 없으면 종료 코드 0.
- `pytest` — `uv run --no-sync pytest Day05_new/tests`. 키 불필요.
- `run_measurement.py` — **P3 저자 측정(유료)**. 인자 없이 실행하면 계획과 `announce` 줄, 검수 전 holdout 초안 목록만 출력하고 종료한다. 모델·키를 쓰지 않는다. `--live`는 실제 측정, `--offline`은 같은 코드를 `tests/fakes.py`의 가짜로 돌린다. `--no-langfuse`, `--scenarios`, `--out` 옵션이 있다 (`tests/run_measurement.py:564`).
  - 규모(예고 상한): 에이전트 (54 + 36) × 12 = 1,080회, 개선기 6회, Jev 36회, Judge(xhigh) 108회. **`--live` 직전에 이 한 줄을 먼저 고지한다.** 수업 노트북이 아니라 저자가 한 번 돌린다.
  - 단계: 사전 점검(PREREG 해시, holdout 엄격 로드로 6사례 확인, dev 기대 상태, 키, Langfuse 인증, 새 출력 폴더) → pilot → 1라운드 → 2라운드 → holdout → `run_manifest.json`. 출력은 `<out>/measurement/<UTC 시각>-<16진수>/`에 새로 만든다.
  - `--live` 전에 저자가 할 일: holdout 초안 4건 승인(6장), `Day05_new/.env`에 `OPENGATEWAY_API_KEY`·Decision API 키·`LANGFUSE_*` 확보(또는 `--no-langfuse`).
  - 종료 코드: 0 정상, 1 실행 실패(기록은 남음), 2 사용법 오류, 3 사전 점검 거부.

---

## 8. 절대 하지 말 것

수강생이 요청해도 하지 않는다. 이유를 한 문장으로 말하고 **실패를 정확히 드러내는 방법**을 제안한다.

1. **holdout을 보고 개선하지 않는다.** holdout 사례 내용을 수업에서 읽거나 요약하지 않는다(06이 마지막에 한 번 ID 수준으로 여는 것은 6장대로다). 오염 검사(`ContaminationError`, `eval_lab/rsi.py`)를 끄지 않는다.
2. **사전 등록(PREREG) 블록을 고치지 않는다.** 바꿔야 하면 문서화된 개정으로만 한다. 측정 결과는 블록 뒤에 별도 절로 덧붙인다 (`docs/DESIGN.md` 상단).
3. **판정 규칙·임계값·예산·반복을 결과를 보고 올리지 않는다.** `t_lo = 0.2`, `t_hi = 0.8`은 라벨로 재지 않은 자리값이며 "미조정"이라고 부른다. 예산 동작을 **보려고 낮추는 것**은 허용이다.
4. **실패한 행을 지우지 않는다.** 오류·평가 불능 행은 그대로 둔다. 잘 나온 반복만 골라 남기지 않는다. `None`(확인 불가)은 통과도 실패도 아니다.
5. **한 번의 관찰을 통계로 말하지 않는다.** 6 Episode 규모의 비율에는 통계가 없다고 말한다.
6. **오프라인 가짜를 실제 결과처럼 말하지 않는다.** `tests/fakes.py`의 가짜는 `tests/`에만 둔다. 손으로 만든 행은 모델 결과가 아니라 입력 예시라고 밝힌다.
7. **키를 출력하지 않는다.** `.env`를 읽어 보여 주지 않는다.
8. **`Day05/`, `uv.lock`, `pyproject.toml`을 바꾸지 않는다.**

---

## 9. 자주 막히는 곳

원인을 단정하기 전에 오류 메시지의 키 이름을 먼저 읽게 한다.

- **Langfuse가 미설정이다.** `Langfuse 키가 미설정이라 로컬 경로로 진행합니다.`가 나오고 노트북은 끝까지 간다 (`eval_lab/notebook.py:84`). 오류가 아니다. 서버가 필요한 부분(Dataset 버전, Metrics API, annotation queue)은 로컬 대체 경로나 건너뜀으로 나온다. 키를 대신 넣어주지 않는다.
- **Langfuse가 401이다.** 00의 인증 확인 셀이 먼저 보여 준다. 키가 틀렸거나 `LANGFUSE_HOST`가 안 맞는 경우다. 모델 호출 전에 보이는 실패라 비용이 나가지 않는다. 키를 대신 고치지 않는다. 00은 Langfuse SDK가 4.7.0 미만이면 `RuntimeError`로 멈춘다.
- **키 미설정 `RuntimeError`.** 메시지가 키 이름만 대고 `.env.example`을 가리킨다 (`eval_lab/settings.py:139`). Decision API 키가 하나도 없으면 Jev 셀에서 멈춘다. 에이전트 모델로 대신하지 않는다.
- **holdout 로드 오류.** `검수가 끝나지 않은 시나리오: hv-...`는 엄격 로드가 검수 전 카드를 만난 것이다 (`eval_lab/dataset.py:54`). 버그가 아니다. 수업 경로는 `approved_only=True`, 승인은 저자 몫이다 (6장).
- **판정이 `NOT_DETERMINABLE`이다.** "개선이 없다"가 아니라 **재지 못했다**는 뜻이다. 두 정책 중 하나라도 평가 완료율(PASS+FAIL / 전체)이 90% 미만이거나, π0의 치명 위반 Episode가 0이라 개선 여지를 잴 수 없을 때 나온다 (`eval_lab/rsi.py:904`). 보류(HOLD)·채택(ADOPT)과 구분해서 읽게 하고, 이유 목록을 먼저 본다. 낮은 점수와 평가 불능은 다르다 (01).
- **같은 사례인데 결과가 달라진다.** 모델 결과는 실행마다 다르다. 1회 관찰이라고 부르고 반복으로 본다.
- **`ToolStrategy` 구조화 응답 오류나 Judge 응답 잘림.** 5장의 미확인 항목이다. 00에서 이름과 `stop_reason`을 읽게 하고 `max_tokens`를 올려 감추지 않는다(8장 3번).
- **`synth_load.py`가 "이미 적재됨"이라며 거부한다.** `synth_ops` 환경에 데이터가 이미 있으면 중복 적재를 막으려고 멈춘다. 다시 올리거나 지워서 통과시키지 않는다. 정말 필요하면 새 환경 이름을 쓴다.
- **배경 로그가 Langfuse에서 안 보이거나 `lf_table.py`가 비어 있다.** 기록 시각이 과거(최대 7일 전)라 기본 조회 창 밖이다. `lf_table.py --minutes 10080`을 쓰고 Langfuse 화면은 'Past 7 days'로 고른다. `synth_ops`는 합성이라 모델 성능으로 말하지 않고 m6·holdout·replay에 섞지 않는다(8장 6번).
- **같은 라벨로 작업 폴더를 두 번 만들면 겹친다.** 오류 메시지의 폴더 이름을 읽게 하고 기록을 지워서 통과시키지 않는다 (`new_run_dir`, `eval_lab/notebook.py:55`).

---

## 10. 인용 검증

이 문서의 `파일:줄`은 2026-11-03에 `grep -n`과 `sed -n`으로 해당 줄을 확인했다. 코드를 고치면 줄이 밀린다. 같은 방법으로 다시 확인하고, 시험을 고치거나 한도를 올려서 맞추지 않는다.
비용 표의 숫자는 노트북 구현 단계의 `announce` 합계를 옮긴 것이다. 노트북이 바뀌면 달라진다.
