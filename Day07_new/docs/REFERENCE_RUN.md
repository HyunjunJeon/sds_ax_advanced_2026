## 결과: 실행됨

GPU, API 키, RunPod 없이 vLLM v0.32.0 소스(커밋 `5df63a7`)의 실제 CPU 클래스를 돌려 시뮬레이터와 대조했다. 대상 A(KV)와 대상 B(파서) 모두 `status: ran`이다. 이 문서가 증명하는 범위는 아래 "증명한 것"에 적은 것까지이고, GPU 서버가 이렇게 동작한다는 뜻은 아니다.

## 환경

| 항목 | 값 |
|---|---|
| 위치 | scratchpad의 `refrun/` (저장소 `.venv`, `uv.lock`은 건드리지 않음) |
| Python | 3.12.14 (`uv venv --python 3.12`) |
| torch / transformers | CPU torch 2.15.0, transformers 5.22.1 |
| vLLM | 설치하지 못함. 소스 트리를 `PYTHONPATH`로 import (`vllm/_version.py` 없음, 버전 경고가 뜨지만 무시) |
| 추가 패키지 | pyzmq, py-cpuinfo, prometheus_client, xgrammar, llguidance, ijson, tiktoken, cbor2, uvloop, pillow 등 import가 요구한 것 |
| 네트워크 | 패키지 설치만. 모델 다운로드 없음, 유료 호출 없음, tokenizer 다운로드 없음 |

`uv pip install vllm==0.32.0`은 실패했다. `vllm>=0.32.0`이 `pynvvideocodec==2.0.4`를 요구하는데 이 패키지의 wheel이 macOS arm64에 없기 때문이다(`manylinux`와 `win_amd64`만 있음). 그래서 소스 트리 import로 넘어갔다. 이때 생긴 함정 하나: PyPI의 `zmq`는 `0.0.0`짜리 가짜 패키지다. `pyzmq`를 설치해야 한다.

## 명령

```bash
cd refrun
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python vllm==0.32.0        # 실패 (위 이유)
uv pip install --python .venv/bin/python torch transformers numpy pydantic ...   # import가 요구하는 만큼 반복
PYTHONPATH=<scratchpad>/src/vllm-v0.32.0 .venv/bin/python run_kv.py     <저장소>/Day07_new/data/reference_kv.json
PYTHONPATH=<scratchpad>/src/vllm-v0.32.0 .venv/bin/python run_parser.py <저장소>/Day07_new/data/reference_parser.json
uv run --no-sync python -m pytest Day07_new/tests/test_reference.py -q   # 저장소 루트
```

실행 스크립트 `run_kv.py`, `run_parser.py`는 scratchpad에만 있고 저장소에는 넣지 않았다. 저장소에는 결과 JSON과 이를 재생하는 테스트만 있다.

## 대상 A: KV (`data/reference_kv.json`, status ran)

실제 `KVCacheManager`(`vllm/v1/core/kv_cache_manager.py`)에 단일 full-attention group, `block_size=16`, 해시 함수 sha256으로 `Request`를 직접 만들어 넣었다. 각 요청은 `get_computed_blocks` 다음 `allocate_slots`를 부르고, 성공하면 `num_computed_tokens`를 올린다. 같은 `inputs`를 `KVManagerSim.replay`에 넣어 행 단위로 비교했다. hash 값은 비교하지 않는다.

| 시나리오 | num_blocks | 실제 결과 요약 | 일치 |
|---|---:|---|---|
| `sequential_allocate` | 12 | R1 `[1,2,3,4]`, R2 `[5,6]` | 일치 |
| `prefix_hit_repeat` | 12 | R2 적중 48 token, `[1,2,3]`, 새 block `[4]` | 일치 |
| `hit_cap_num_tokens_minus_1` | 12 | R2 적중 32 token (`[1,2]`), 새 block `[4]` | 일치 |
| `different_salt` | 12 | R2 적중 0, 새 block `[4,5,6,7]` | 일치 |
| `free_then_reuse_order` | 12 | R2 `[4]`, R3 `[5,6]` | 일치 |
| `eviction_under_pressure` | 6 | R2 `[4,5,3,2]`, R3 적중 16 token `[1]` | 일치 |

6개 모두 `real == sim`이다. 불일치 행은 없다. 실제 쪽 free queue를 보면 R1 반납 직후 `[4,5,...,11,3,2,1]`로 꼬리 block이 앞에, 해시가 있는 block이 뒤에 (역순으로) 붙는다. 시뮬레이터가 같은 순서를 낸다.

## 대상 B: 파서 (`data/reference_parser.json`, status ran)

실제 reasoning parser `glm47`(`ReasoningParserManager`)과 tool parser `glm47`(`ToolParserManager`)을 서빙의 비스트리밍 경로 순서대로 불렀다. 먼저 `extract_reasoning(raw)`로 (reasoning, content)를 얻고, content를 `extract_tool_calls`에 넣는다(`vllm/parser/abstract_parser.py:841-846`의 순서). 비교용으로 `Glm47MoeParser.parse()` 통합 경로도 `unified_parse` 칸에 같이 남겼고, 모든 케이스에서 같은 결과였다. 입력은 모두 **구성 문자열**이며 모델 출력이 아니다. `finish_reason`은 파서가 아니라 `serving.py`의 몫이라 넣지 않았다.

| id | 후보 | 실제 결과 한 줄 |
|---|---|---|
| `clean_call` | - | 호출 1개 `get_temperature {"city": "서울"}`, reasoning/content 없음 |
| `reasoning_then_call` | - | reasoning `사용자가 서울 기온을 묻는다.`, 호출 1개, content 없음 |
| `malformed_markup` | C7 | `</tool_call>` 없이 다음 `<tool_call>`이 오면 **앞 호출(서울)은 사라지고** 뒤 호출(부산)만 남는다 |
| `truncated_call` | C2, C6 | `</arg_value>` 없이 끊긴 호출이 **인자 `{}`인 호출 1개**로 나온다(`tools_called: true`) |
| `unknown_tool` | C3 | 선언하지 않은 이름은 **호출도 content도 남기지 않고** 사라진다 (`tool_calls: []`, content 없음) |
| `bad_arg_type` | C4 | 정수 인자에 `곧`을 넣어도 파서는 거르지 않고 `{"minutes": "곧", ...}` 문자열로 넘긴다 |
| `no_call` | - | `</think>` 뒤 일반 답변이 content, 앞은 reasoning, 호출 없음 |
| `no_call_missing_think_end` (추가) | - | `</think>` 없는 일반 답변은 **전부 reasoning**이 되고 content는 없다 |

마지막 줄은 계약의 7개 id에 없는 추가 케이스다. 기본값(`thinking` 미지정)에서 reasoning parser의 시작 상태가 REASONING이기 때문에(`vllm/parser/glm47_moe.py:152`의 `initial_state`) `</think>`가 없으면 content가 비는 것을 보이려고 넣었다. 코드 읽기가 아니라 실행 결과다.

### tokenizer 대체물과 한계

진짜 GLM tokenizer를 받지 않았다. 대신 `<think>`, `</think>`, `<tool_call>`, `<arg_key>` 등 특수 토큰 14개만 가진 가짜 vocab `StubTokenizer`(`get_vocab`, `all_special_tokens`, `all_special_ids`)를 썼다. 따라서:

- 문자열 경로(텍스트 lexer)만 검증했다. 진짜 vocab의 token ID로 판정하는 경로(`is_reasoning_end`, 토큰 ID 기반 종료 판정)는 이 기록에서 돌리지 않았다. 이후 `data/reference_parser_stream.json`(status ran)이 실행했다(`docs/reference/parser_stream.md`).
- `_glm53_always_thinks`가 보는 chat template가 없어서(`chat_template=None`) GLM-5.3의 "생각 항상 켜짐" 판정은 이 기록에서 검증하지 못했다(이후 `reference_parser_stream.json`이 실행해 참으로 확인). 이 실행의 thinking 기본값은 `Glm47MoeParser.__init__`의 기본(켜짐)이다.
- 스트리밍 경로(`extract_tool_calls_streaming`)는 이 기록에서 돌리지 않았다. 이후 `reference_parser_stream.json`이 실행했고, 비스트리밍 결과를 스트리밍에 그대로 옮기지 않는다.
- Python 파서 기준이다. 레시피가 쓰는 `VLLM_USE_RUST_FRONTEND=1`의 Rust 파서는 이 기록에서 돌리지 않았다(`docs/sources/part6.md` 적용 범위 전제). 이후 `data/reference_parser_rust.json`(status ran)이 파서 crate만 실행했다(`docs/reference/parser_rust.md`).

## 증명한 것과 증명하지 않은 것

증명한 것
- v0.32.0 소스의 `KVCacheManager`/`BlockPool`이 위 6개 입력에서 낸 block ID, 적중 token 수, ref count, free queue 순서, 해시 등록 block 목록이 `kv_sim`과 같다.
- v0.32.0 소스의 GLM 파서(Python)가 위 구성 문자열에서 낸 reasoning, content, tool_calls.

증명하지 않은 것
- GPU 서버나 Day07 Pod가 이렇게 동작한다는 것. 실제 서버는 이 실행에 없다.
- 실제 모델이 이런 문자열을 낸다는 것. 입력은 사람이 만들었다.
- `kv_math`와 `agent_sim`의 토이 렌더링은 이 실행의 대상이 아니다. `sched_sim`도 이 실행의 대상이 아니었고, 이후 `data/reference_sched.json`(status ran)이 실제 `Scheduler`와 대조해 40개 시나리오 중 9개의 20개 변형에서 차이를 냈다(원인은 `docs/reference/sched.md`). `agent_sim`의 파서 쪽은 이후 `data/reference_parser_stream.json`이 스트리밍까지 대조했다.
- 이 대상 A의 6개 입력은 단일 full-attention group만 돌렸다. hybrid(KDA, MLA 등) 규격의 record, 쪽, block 크기와 group 수는 이후 `data/reference_specs.json`(status partial)이 클래스 호출로 다룬다. 이 대상 A에서 돌리지 않은 것은 여러 group 조정의 할당 경로, speculative decoding, 비동기 스케줄링이다.
- block 해시 값 자체. 비교에서 뺐다.

## 시뮬레이터와 다른 점

없다. 시나리오 6개 모두 일치해서 `Day07_new/tests/test_reference.py`의 `EXPECTED_DIFFERENCES`는 비어 있다. 새 차이가 생기면 그 테스트가 실패한다. 파서 쪽은 시뮬레이터가 없으므로 비교 대상이 없고, `agent_sim.diagnosis_rows()`가 이 파일을 읽어 C2, C3, C4, C6, C7의 근거 종류를 '실제 GLM 파서, 구성 문자열'로 바꾼다.

## 노트북 저자가 알아둘 점

- 파서 실행 결과는 코드 읽기 추론과 다른 곳이 있을 수 있다. 특히 `unknown_tool`(조용히 사라짐), `malformed_markup`(앞 호출 소실), `truncated_call`(빈 인자 호출 성립)은 "관찰했다"고 쓸 수 있는 범위가 **v0.32.0 파서에 구성 문자열을 넣었을 때**로 한정된다.
- 이 JSON의 `output`에는 계약 외 칸 `tools_called`, `content_after_reasoning_before_tool_parser`, `unified_parse`가 더 있다. 무시해도 된다.

## 추가 실행: 전체 입력 검사

노트북 03 저장 셀 35의 `scheduler_reserve_full_isl` 주장이 기대는 실행이다. 서버나 스케줄러가 아니라 CPU에서 `KVCacheManager` 클래스(vLLM v0.32.0, 커밋 `5df63a7`)를 직접 호출했다.

- 입력: block 6개(block 크기 16, full-attention group 하나). `doc`은 54 token이고 32 token, 이어서 22 token을 계산해 54 token을 모두 계산했다. `faq`는 20 token이고 10 token을 요청했다(`has_scheduled_reqs=True`). `full_sequence_must_fit`만 `True`와 `False`로 바꿨다.
- 실행: scratchpad의 `refrun/.venv`(저장소 `.venv`가 아님)에서 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python dump2b/real_isl.py`. vLLM은 설치하지 않고 소스 트리를 `sys.path`에 넣어 import했다. 2026-11-01에 다시 실행했고 아래가 실제 출력이다(경고 줄은 뺌).

```
full_sequence_must_fit True free 1 faq allocate -> None
full_sequence_must_fit False free 0 faq allocate -> [5]
```

- 읽는 법: `True`이면 `faq`의 전체 입력이 들어갈 자리가 없어 `allocate_slots`가 `None`을 돌려주고 free block 1개가 남는다. `False`이면 요청한 10 token 몫만 보고 block `[5]`를 내주어 free block이 0개가 된다.
- 한계: 이 실행은 `KVCacheManager` 클래스 호출이다. 이 실행에서는 `schedule()` 루프를 돌리지 않았다. `schedule()` 루프는 이후 `data/reference_sched.json`이 실제 `Scheduler`로 돌렸고(`scheduler_reserve_full_isl` 켬·끔 변형 포함), GPU 서버와 실제 모델은 어느 쪽도 돌리지 않았다.

## 추가 실행 목록

상태는 각 데이터 파일의 `status` 값이다.

| 실행 | 상태 | 문서 | 데이터 | 증명하는 것 / 증명하지 않는 것 |
|---|---|---|---|---|
| specs | partial | `docs/reference/specs.md` | `data/reference_specs.json` | 실제 KV 규격 클래스가 세 모델의 record, 쪽 크기, block 크기를 `kv_cases`와 대조해 계산한다. 전체 모델 생성, GPU 기동 로그는 아니다 |
| sched | ran | `docs/reference/sched.md` | `data/reference_sched.json` | 실제 `Scheduler`를 40개 시나리오로 돌려 `sched_sim`과 대조한다(`isl=off|prefix=off` 38개 일치, 차이 20개 변형). GPU 서버와 실제 모델은 아니다 |
| parser_stream | ran | `docs/reference/parser_stream.md` | `data/reference_parser_stream.json` | 스트리밍, token ID, `finish_reason`을 실제 파서와 serving 제너레이터로 확인한다. 엔진 문법 집행, 실제 모델 출력은 아니다 |
| parser_rust | ran | `docs/reference/parser_rust.md` | `data/reference_parser_rust.json` | Rust 파서 crate의 glm45/glm47 결과를 Python과 대조한다. 상태 코드, 스트림 이벤트, 서버 층은 아니다 |
| lmcache | partial | `docs/reference/lmcache.md` | `data/reference_lmcache.json` | 설치, 연결 gating, connector 생성, 저장을 CPU에서 실행했다. worker와 모델 경로, GPU 값은 실행하지 않았다 |
