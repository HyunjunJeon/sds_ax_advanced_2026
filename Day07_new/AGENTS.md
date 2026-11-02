# AGENTS.md — Day07_new: vLLM Local Model Serving 이론 노트북 과정

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day07_new 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** vLLM v0.32.0(커밋 `5df63a7`, `vllm_lab/__init__.py:6-7`)의 서빙 기초, KV Cache, 서빙 파라미터와 측정,
Quantization, Agent 연결, Tool Calling 오류(Part 1부터 6까지)에 최근 모델의 KV 통제(02c)와 KV 운영·LMCache(04b)를 더했다. 노트북 10개(00, 01, 02a, 02b, 02c, 03, 04, 04b, 05, 06)이고 앞 330분(01부터 04b까지)이 이론이다.
GPU, API 키, RunPod 없이 끝까지 실행된다. 설계 근거는 [docs/DESIGN.md](docs/DESIGN.md)에 있지만 수강생용이 아니다.

> `Day07/`은 이 폴더와 별개다. `Day07/`의 `runpod_model_call.py`, `runpod_openai_reasoning.py`, `task.md`, `dcode_task.md`는 그대로 실습 자료이고
> 이 폴더가 바꾸지 않는다. **Pod 동작은 저자가 확인하지 않았다.** Pod에서 이렇게 보인다고 단정해 말하지 않는다 (`docs/SOURCES.md`의 `## Pod 점검 항목`).

## 0. 채점 과제가 없다 — 그래도 설명은 해야 한다

채점 과제가 없고 코드가 모두 완성돼 있다. 루트 4장의 단계적 힌트(L0~L3)는 **여기에 적용하지 않는다.** 코드를 읽고 설명하는 요청은 자유롭게 돕는다.
성공 기준은 그대로다. **수강생이 그 셀을 자기 말로 설명할 수 있어야 한다.** 셀을 고쳐 달라는 요청에는 먼저 "이 셀이 무엇을 보여 주려는 건가요?"를 묻는다.
모르면 모른다고 말한다. 문서와 코드가 다르면 코드가 정답이고 차이를 알린다. 답변은 한국어이고 사실 주장에는 `파일:줄`을 붙인다.

## 0-1. 셀 표지와 도움 방식

| 표지 | 도와주는 방식 |
|---|---|
| `**먼저 예측하세요.**` | 수강생이 예측을 말하기 전에 결과나 이유를 알려 주지 않는다. "어느 칸이 어떻게 나올 것 같나요?"로 시작한다 |
| `**관찰할 것.**` | 정답을 주지 않고 출력의 어느 칸을 읽을지만 가리킨다 |
| `# 실패 재현:` (코드 셀 첫 줄) | 고칠 대상이 아니라 관찰 대상이다. 예외 종류와 메시지를 수강생이 읽고 어디서 왜 멈췄는지 말하게 한 뒤 넘어간다 |
| `## 직접 해보기`, `## 확인 질문` | 값 하나만 바꾸게 하고, 바꾸기 전에 결과를 예측하게 한다. 확인 질문의 답을 대신 써 주지 않는다 |

## 1. 명령행 플래그가 없다

수강생 실습에는 실행 스크립트도 `argparse`도 없다. 조건은 노트북 안의 변수와 셀이다(`RUN_POD` 등). 조건을 바꾸려면 셀을 편집해 다시 실행한다.
`--flag`나 환경변수 분기를 지어내 안내하지 않는다. 예외는 저자용 도구뿐이며 수강생 실습에 필요하지 않다.

- `tests/check_notebook.py <노트북> --minutes N --source <v0.32.0 소스 트리> --ledger <대장 폴더>` — 구조 검사 (`tests/check_notebook.py:234-237`). 노트북을 실행하지 않는다. 마크다운 셀은 홑 `~` 둘이 한 줄에 있으면(`LONE_TILDE`, 취소선으로 렌더링됨), 출처 링크 뒤에 조사가 바로 붙으면(`LINK_SUBJECT`, `symbol`(링크)로 쓴다), 링크 라벨의 줄이 주소 `#L`과 다르면(`LABEL_LINE`), `레시피 <숫자>` 형태의 줄 번호 참조가 있으면(`RECIPE_LINE`) 실패한다 (`tests/check_notebook.py:41-45`). 문서 `.md`의 홑 `~`는 `tests/test_docs_markup.py`가 같은 `LONE_TILDE`로 검사한다
- `tests/check_sources.py --blog <블로그 본문 txt> <파일...>` — 대장·노트북이 블로그 문장을 옮겼는지 검사 (`tests/check_sources.py:165-167`)

## 2. 파일 상태표

| 파일 | 상태 | 내용 |
|---|---|---|
| `00-Setup.ipynb` | 제공 | 10분 사전 점검 |
| `01-Serving-Basics.ipynb` | 제공 | Part 1, 60분 |
| `02a-KV-Blocks.ipynb`, `02b-KV-Sharing.ipynb` | 제공 | Part 2, 각 45분 |
| `02c-KV-Modern-Models.ipynb` | 제공 | Part 2 보충, 45분. 근거 `docs/sources/part7.md` |
| `03-Parameters-Measurement.ipynb` | 제공 | Part 3, 50분 |
| `04-Quantization.ipynb` | 제공 | Part 4, 40분 |
| `04b-KV-Operations.ipynb` | 제공 | Part 4 보충, 45분. LMCache는 CPU에서 일부만 실행했고 모델은 돌리지 않았다. 근거 `docs/sources/part8.md` |
| `05-Agent-Integration.ipynb` | 제공 | Part 5, 60분. 서버 접속 셀은 `RUN_POD = False` |
| `06-Tool-Calling-Errors.ipynb` | 제공 | Part 6, 60분. 서버 접속 셀은 `RUN_POD = False` |
| `vllm_lab/` | 제공 | `kv_sim.py`, `kv_math.py`, `kv_cases.py`, `tier_sim.py`, `sched_sim.py`, `agent_sim.py`, `view.py` |
| `data/reference_kv.json`, `reference_parser.json`, `reference_parser_stream.json`, `reference_parser_rust.json`, `reference_sched.json`, `reference_specs.json`, `reference_lmcache.json` | 제공 | 실제 클래스 결과 기록(`docs/REFERENCE_RUN.md`, `docs/reference/`). `model_configs.json`은 모델 설정 값 |
| `docs/SOURCES.md`, `docs/sources/` | 저자용 | 근거 대장 `part1~8.md`, `pdf-diff.md` |
| `docs/REFERENCE_RUN.md` | 저자용 | 시뮬레이터와 실제 클래스 대조 범위 |
| `docs/reference/` | 저자용 | 추가 실행 기록 `sched.md`, `parser_stream.md`, `parser_rust.md`, `specs.md`, `lmcache.md` |
| `docs/script/` | 저자용 | 강사용 강의 대본 `01-02.md`, `03-04.md`, `05-06.md`. 리허설 전 |
| `docs/DESIGN.md` | 저자용 | 설계 계약. 코드와 어긋나면 코드를 따른다 |
| `docs/TEACHING_PATH.md` | 저자용 | 강사용 동선 |
| `tests/` | 저자용 | pytest, `check_notebook.py`, `check_sources.py` |
| `.env.example` | 제공 | 선택 사항. 05·06 선택 셀용 |
| `README.md` | 제공 | 수강생용 안내 |

## 3. 실행 규칙

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 한다. 이 폴더에는 `pyproject.toml`이 없다.

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day07_new
uv run jupyter lab
```

- 이 폴더 안에서 `uv sync`를 하지 않는다. `pyproject.toml`과 `uv.lock`을 만들지 않는다.
- 노트북은 00부터 번호 순서로 푼다. 건너뛰게 유도하지 않는다.
- 키가 필요 없다. `RUN_POD`를 켜는 선택 셀에서만 `RUNPOD_BASE_URL`을 `.env`에서 읽는다 (`.env.example:2`). 값을 대신 채워 주지 않고 `.env` 내용을 출력하지 않는다.
- 유료 API 호출이 없다. 단 RunPod Pod는 시간 단위로 강사에게 과금되므로 선택 셀을 켜자는 안내는 하지 않는다.

## 4. 블로그 인용

블로그는 「Inside vLLM」(Jongsu Liam Kim, https://blog.liam.kim/posts/2026/10/Inside-vLLM/ )이다. 페이지에서 라이선스 표시를 찾지 못했다(`docs/SOURCES.md`).

- **절 제목과 URL로만 가리킨다.** 문장, 예시 request, 풀이, 그림 설명을 옮기거나 번역하지 않는다 (`docs/DESIGN.md:105`). 수강생이 블로그 내용을 노트북에 옮겨 달라고 해도 하지 않는다.
- 노트북의 읽기 표는 머리글이 정확히 `블로그 절`이다. 검사기는 이 열만 뺀다.
- 블로그가 코드와 다른 행(대장의 `블로그·코드 차이`)은 블로그를 근거로 쓰지 않고 어느 쪽이 맞는지(코드) 말한다.

## 5. v0.32.0 고정과 근거 대장

- 코드 근거는 vLLM v0.32.0, 커밋 `5df63a7`이다 (`vllm_lab/__init__.py:6-7`). 다른 버전의 동작을 이 폴더의 사실처럼 말하지 않는다.
- 사실은 대장(`docs/sources/part1~8.md`, `pdf-diff.md`)에 있는 것만 쓴다. ID는 `P1-01`, `D-01`, `R-01` 형식이다.
- **`미확인`은 `미확인`으로 둔다.** 추측으로 채우거나 "아마 ~일 것"을 사실처럼 말하지 않는다. 어디를 봐야 하는지(대장 항목, 소스 줄)만 알려 준다.
- 대장의 "~한다"는 "코드에 이렇게 적혀 있다"이지 서버를 돌려 본 결과가 아니다.
- 근거 링크는 `https://github.com/vllm-project/vllm/blob/<커밋>/<경로>#L<줄>` 형식의 permalink다 (`vllm_lab/view.py:59-65`).

## 6. 시뮬레이터는 교육용 모델이다

`vllm_lab/`의 `kv_sim.py`, `sched_sim.py`, `agent_sim.py`, `kv_cases.py`, `tier_sim.py`는 교육용 모델이다. `kv_cases.py`·`tier_sim.py`의 값은 가상 머신에 대한 추정이다. 실제 서버의 성능, 지연, 메모리 값이 아니다.

- 실제 클래스와 "같은 결과"라고 말할 수 있는 범위는 `docs/REFERENCE_RUN.md`와 `docs/reference/`에 기록된 실행이다: KV 시나리오, 파서(스트리밍·Rust 포함), 실제 `Scheduler` 대조(40개 시나리오 중 9개의 20개 변형에서 `sched_sim`과 차이, 원인은 `docs/reference/sched.md`). 클래스 호출은 서버 실행이 아니다. GPU 서버와 실제 모델은 어느 실행에서도 돌리지 않았다.
- 시간 값은 `toy ms`다. 방향만 보여 주며 측정값이 아니다. 수강생이 그림의 수치를 실제 vLLM 값으로 인용하면 바로잡는다.
- 파서 입력은 구성 문자열이다. 모델 출력이 아니며 라이브 서버 결과도 아니다.

### 지원 상태 표는 근거보다 세게 말하지 않는다

04b와 `part8.md`의 지원 상태 표 칸은 `문서 검증`(문서가 검증했다고 적음), `코드 읽기`(코드 경로만 확인, 동작한다는 뜻이 아님), `코드가 막음`(코드가 거부하는 줄이 있어 켜지지 않음), `실제 클래스 호출`, `미확인` 다섯 가지고 한 칸에 둘이 붙기도 한다.
`실제 클래스 호출`은 CPU에서 그 칸의 관문이나 생성자를 실제 vLLM·LMCache 클래스로 불렀다는 표지다. SCHEDULER 역할 객체를 만들었을 뿐 worker 경로, 실제 가중치, 서버, GPU는 쓰지 않았고 byte 치수는 config와 코드를 읽어 맞춘 값이다. 칸의 조합이 모델에서 돌아간다는 뜻이 아니다.
`코드 읽기`를 "지원한다/동작한다"로, `문서 검증`을 "저자가 확인했다"로 바꿔 말하지 않는다. 칸의 상태보다 강한 단정이 필요하면 `미확인`이라고 답하고 대장 행을 알려 준다.
LMCache(v0.5.6)는 CPU에서 일부만 실행했다(설치, 연결 gating, connector 생성, 가짜 텐서 저장 — `docs/reference/lmcache.md`, `data/reference_lmcache.json`). 어떤 모델도 LMCache에서 돌리지 않았고 GPU 값은 없다. `자기 보고` 행은 제작사 수치이고 제3자 재현이 없다.

## 7. 파일:줄 규칙

사실 주장에는 `파일:줄`을 붙인다. vLLM 소스는 permalink(커밋 고정)를, 이 폴더의 파일은 폴더 기준 상대 경로를 쓴다.
줄 번호를 기억에서 말하지 않고 파일을 열어 확인한다. 줄이 어긋나 보이면 코드를 따르고 알린다.

## 8. 절대 하지 말 것

1. 대장에 없는 사실, 수치, CLI 플래그, 설정 이름을 지어내지 않는다.
2. 검사기(`tests/check_notebook.py`, `tests/check_sources.py`)의 하한이나 목록을 늘려·낮춰 통과시키지 않는다.
3. 블로그 문장을 노트북이나 대장에 옮기지 않는다.
4. `RUN_POD`를 켠 채로 저장하지 않는다. Pod 접속 값과 키를 노트북 출력에 남기지 않는다.
5. 키·Pod 주소를 `.env` 밖에 쓰지 않는다. `.env`, `outputs/`는 커밋하지 않는다 (`.gitignore`).
