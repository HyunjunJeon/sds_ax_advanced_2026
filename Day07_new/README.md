# Day07_new — vLLM Local Model Serving 노트북 과정

`Day07/`(RunPod에 띄운 GLM-5.3-Flash 호출 실습)과 나란히 놓인 이론 중심 노트북 버전입니다. `Day07/`는 그대로 두며, 이 폴더는 병렬 선택지입니다.
vLLM v0.32.0(커밋 `5df63a7`)의 소스를 근거로, 서빙 기초·KV Cache·최근 모델의 KV 통제·서빙 파라미터와 측정·Quantization·KV 운영(LMCache 포함)·Agent 연결·Tool Calling 오류를 배웁니다 (`vllm_lab/__init__.py:6-7`).

- **GPU도, API 키도, RunPod도 필요 없습니다.** 모든 코드 셀은 이 폴더의 `vllm_lab/` 교육용 시뮬레이터와 저장된 실제 클래스 결과(`data/*.json`)만으로 끝까지 실행됩니다.
- 시뮬레이터는 **교육용 모델**입니다. 실제 vLLM 서버가 이렇게 동작한다는 증명이 아닙니다. 실제 클래스와 대조한 범위는 `docs/REFERENCE_RUN.md`에 있습니다.
- **저자가 CPU에서 실제로 돌린 것:** vLLM v0.32.0의 `KVCacheManager`, `Scheduler`, 실제 tokenizer를 쓴 Python 파서(스트리밍 포함), Rust 파서 crate, LMCache 연결 gating(connector 생성 가능 여부), LMCache v0.5.6의 CPU 저장입니다. 결과는 `data/reference_*.json`에 있고 범위는 `docs/REFERENCE_RUN.md`와 `docs/reference/`에 있습니다.
- **돌리지 않은 것:** GPU 서버, LMCache 위에서 도는 실제 모델, RunPod Pod입니다. 클래스를 직접 호출한 결과는 서버 실행이 아닙니다. LMCache는 설치 1차가 실패해 일부만 실행했고(`docs/reference/lmcache.md`), 지원 상태 표의 `문서 검증`은 문서가 그렇게 적었다는 뜻이며 저자가 확인한 것이 아닙니다.
- 서버에 접속하는 선택 셀은 05와 06에 있고 `RUN_POD = False`로 잠겨 있습니다. 켜는 것은 선택이며, 저자는 **Pod를 띄워 동작을 확인하지 않았습니다.** 그 셀들은 Pod에서 어떻게 보일지 검증되지 않았습니다.

## 설치와 실행

설치는 저장소 루트에서 한 번, 실행은 이 폴더에서 합니다. 이 폴더에는 `pyproject.toml`이 없고 `uv run`이 루트의 uv workspace 환경을 찾습니다.

```bash
uv sync --locked            # 저장소 루트에서 한 번만
cd Day07_new
uv run jupyter lab          # 실행은 이 폴더에서
```

이 폴더 안에서 `uv sync`를 하지 않습니다. 다른 Day에 필요한 패키지가 지워지며, 복구는 루트의 `uv sync --locked`입니다.
`.env`는 필요 없습니다. 05와 06의 선택 셀을 켤 때만 `.env.example`을 `.env`로 복사해 직접 채웁니다 (`.env.example:2`).

## 수업 시간표

앞 330분(01~04b)은 이론입니다. 00은 수업 전에 하는 10분 점검입니다. 노트북은 번호 순서로 풉니다.

| 노트북 | 분 | 누적 | 내용 |
|---|---:|---:|---|
| `00-Setup.ipynb` | 10 | - | 수업 전 점검. 환경, `vllm_lab` import, 키·서버가 필요 없다는 확인 |
| `01-Serving-Basics.ipynb` | 60 | 60 | Part 1. 서빙 기초: step, scheduler, 요청 경로, 서버 초기화 |
| `02a-KV-Blocks.ipynb` | 45 | 105 | Part 2 앞. KV block, block table, slot |
| `02b-KV-Sharing.ipynb` | 45 | 150 | Part 2 뒤. ref count, prefix cache hash, 반납과 preemption, speculative decoding |
| `02c-KV-Modern-Models.ipynb` | 45 | 195 | Part 2 보충. 최근 모델(GLM-5.3-Flash, DeepSeek-V4.1-Flash)이 KV cache를 줄이는 방법과 비용 |
| `03-Parameters-Measurement.ipynb` | 50 | 245 | Part 3. 서빙 파라미터, `vllm bench serve`, TTFT·ITL·TPOT, `/metrics` |
| `04-Quantization.ipynb` | 40 | 285 | Part 4. 가중치 양자화와 KV dtype의 구분 |
| `04b-KV-Operations.ipynb` | 45 | 330 | Part 4 보충. KV 용량 계산, prefix cache 한계, LMCache, hybrid 모델, 실패 정책, 지표 |
| `05-Agent-Integration.ipynb` | 60 | 390 | Part 5. 멀티턴 prefix caching, `cache_salt`, `cached_tokens`, Agent 연결 |
| `06-Tool-Calling-Errors.ipynb` | 60 | 450 | Part 6. glm47 파서, `finish_reason`, 잘림, 알 수 없는 도구 |

## 노트북이 읽는 방법

- `**먼저 예측하세요.**`는 실행 전에 결과를 자기 말로 예측합니다. `**관찰할 것.**`은 출력의 어느 칸을 볼지 알려 줍니다.
- `# 실패 재현:` 셀은 고치는 대상이 아니라 관찰 대상입니다.
- 근거 링크는 vLLM v0.32.0 소스의 줄 단위 permalink입니다. 근거가 없는 항목은 `미확인`이라고 적혀 있고 사실처럼 읽으면 안 됩니다.
- 블로그는 절 제목과 URL로만 가리킵니다. 노트북에 블로그 문장은 옮겨져 있지 않습니다.

## 기존 Day07 실습과의 관계

기존 `Day07/`의 `runpod_model_call.py`, `runpod_openai_reasoning.py`, `task.md`, `dcode_task.md`는 **그대로 실습 자료**입니다. Pod에 실제로 붙는 실습은 거기서 합니다. 이 폴더의 05·06에서 다루는 Pod 동작은 저자가 확인하지 않았습니다 (`docs/SOURCES.md`의 `## Pod 점검 항목`).

## 파일

| 경로 | 내용 |
|---|---|
| `00-Setup.ipynb` ~ `06-Tool-Calling-Errors.ipynb` | 수업 노트북 10개 (`02a`, `02b`, `02c`, `04b` 포함) |
| `vllm_lab/` | 교육용 모듈: `kv_sim.py`, `kv_math.py`, `kv_cases.py`, `tier_sim.py`, `sched_sim.py`, `agent_sim.py`, `view.py` |
| `data/reference_kv.json`, `reference_parser.json`, `reference_parser_stream.json`, `reference_parser_rust.json`, `reference_sched.json`, `reference_specs.json`, `reference_lmcache.json` | 실제 클래스를 CPU에서 돌려 저장한 결과. `data/model_configs.json`은 모델 설정 값 |
| `docs/SOURCES.md`, `docs/sources/` | 근거 대장(part1~8, pdf-diff). 노트북이 인용하는 사실의 출처 |
| `docs/REFERENCE_RUN.md` | 시뮬레이터와 실제 클래스를 대조한 범위 |
| `docs/reference/` | 추가 실행 기록: `sched.md`, `parser_stream.md`, `parser_rust.md`, `specs.md`, `lmcache.md` |
| `docs/script/` | 강사용 강의 대본: `01-02.md`, `03-04.md`, `05-06.md`. 절마다 보일 셀과 말할 글. 아직 리허설하지 않았음 |
| `docs/DESIGN.md` | 저자용 설계 계약(수강생용 아님) |
| `docs/TEACHING_PATH.md` | 강사용 동선. 330분 안에 말할 내용과 자습으로 넘길 내용 |
| `tests/` | 저자용 pytest와 검사기(`check_notebook.py`, `check_sources.py`) |
| `.env.example` | 선택 사항. 05·06 선택 셀용 |
