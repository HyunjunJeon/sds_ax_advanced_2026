# LMCache와 connector 관문 실행 결과 (vLLM v0.32.0, LMCache v0.5.6)

원자료: `Day07_new/data/reference_lmcache.json`. 테스트: `Day07_new/tests/test_reference_lmcache.py`. 대조 대상: `Day07_new/docs/sources/part8.md`의 `## 모델별 지원 상태`.

상태는 `partial`입니다. 관문(게이팅)과 스케줄러 쪽 생성자, 가짜 텐서 저장은 돌렸고, worker 쪽과 실제 모델은 돌리지 못했습니다. 이 문서의 값은 새 venv와 빈 출력 폴더에서 돌린 실행(2026-11-02 09:40~09:43 KST)에서만 나왔습니다. 끊긴 이전 시도의 결과 파일은 쓰지 않았습니다.

**어떤 모델도 LMCache에서 돌리지 않았습니다.** 가짜 텐서 저장이 된다는 것은 서버와 클라이언트의 저장 경로에 대한 사실입니다. `constructed`도 스케줄러 쪽 `__init__`이 끝났다는 뜻일 뿐, KV를 저장하거나 복원한 것이 아닙니다.

## 1. 무엇을 돌렸나

| 항목 | 값 |
|---|---|
| 게이팅 환경 | `lmrun`(lmcache 있음), `lmrun` + `LMCACHE_USE_UPSTREAM_MP=1`(내장판 강제), `refrun`(lmcache 없음) |
| 설치 1차 | `uv pip install lmcache==0.5.6` 실패. `not_run` |
| 설치 2차 | 클론 복사본을 `NO_GPU_EXT=1`로 빌드. 소스 수정 없음, 네이티브 확장 3개, cupy 없음 |
| 공통 | Python 3.12.14, darwin arm64, torch 2.15.0, `VLLM_TARGET_DEVICE=cpu`, vLLM은 소스 트리를 `PYTHONPATH`로 import |
| transformers | `lmrun` 5.19.0(vLLM `requirements/common.txt:10`의 `>=5.16.1,<5.20.0` 안), `refrun` 5.22.1(범위 밖) |
| 모델 모양 | GLM-5.3-Flash, GLM-5.2, DeepSeek-V4-Flash, DeepSeek-V4.1-Flash, Kimi-K3 |

PyPI 실패 줄 (0.5.6은 manylinux wheel과 sdist만 있습니다):

```text
cause: Because all versions of cupy-cuda13x have no wheels with a matching platform tag (e.g., `macosx_27_0_arm64`) and lmcache==0.5.6 depends on cupy-cuda13x, we can conclude that lmcache==0.5.6 cannot be used.
```

입력의 성격: 함수와 클래스는 진짜입니다. `_promote_local_kv_cache_specs`, `unify_hybrid_kv_cache_specs`, `get_kv_cache_groups`, `generate_scheduler_kv_cache_config`, `KVConnectorFactory`, 층 클래스의 `get_kv_cache_spec`을 그대로 불렀습니다. 다만 층 객체는 `object.__new__`로 만들어 가중치가 없고, byte 치수는 config와 코드를 읽어 맞춘 값입니다. 진짜 모델이 만든 spec이 아닙니다. Kimi-K3는 이 저장소에 config 스냅샷이 없어 치수가 가정값이며, 표에 쓴 결과는 spec 타입만으로 정해지는 것들입니다.

재현 순서 (`<scratch>/lmrun`, 저장소 밖):

```bash
NO_GPU_EXT=1 uv pip install --python .venv/bin/python ./lmcache-copy 'transformers>=5.16.1,<5.20.0' torchvision ...
export PYTHONPATH=<scratch>/src/vllm-v0.32.0 VLLM_TARGET_DEVICE=cpu
.venv/bin/python run_gating.py out/gating_external.json
LMCACHE_USE_UPSTREAM_MP=1 .venv/bin/python run_gating.py out/gating_upstream.json
<scratch>/refrun/.venv/bin/python run_gating.py out/gating_refrun.json
.venv/bin/python run_storage.py out/storage.json
RUN_MODE=external .venv/bin/python run_connectors.py out/conn_external.json hf   # offload, v1, upstream도 같은 방식
```

## 2. 결과

### 관문 표

칸 값은 `get_kv_cache_groups`와 `create_connector`까지의 결과입니다. `통과`는 관문을 지났다는 뜻이지 동작한다는 뜻이 아닙니다.

| 모델 | connector | 기본값 | `--disable-hybrid-kv-cache-manager` | `--no-disable-hybrid-kv-cache-manager` |
|---|---|---|---|---|
| GLM-5.3-Flash, Kimi-K3 | `LMCacheConnectorV1` | `ValueError` `kv_cache_utils.py:1760` | 같음 | `ValueError` `factory.py:57` |
| GLM-5.3-Flash, Kimi-K3 | 외부 `LMCacheMPConnector`, `OffloadingConnector` | 통과 | `ValueError` `kv_cache_utils.py:1760` | 통과 |
| GLM-5.3-Flash, Kimi-K3 | 내장 `LMCacheMPConnectorUpstream` | `ValueError` `kv_cache_utils.py:1760` | 같음 | `ValueError` `factory.py:57` |
| DeepSeek-V4-Flash, V4.1-Flash | `LMCacheConnectorV1` | **`TypeError` `kv_cache_interface.py:138`** | 같음 | `ValueError` `factory.py:57` |
| DeepSeek-V4-Flash, V4.1-Flash | 외부 `LMCacheMPConnector`, `OffloadingConnector` | 통과 | **`TypeError` `kv_cache_interface.py:138`** | 통과 |
| DeepSeek-V4-Flash, V4.1-Flash | 내장 `LMCacheMPConnectorUpstream` | **`TypeError` `kv_cache_interface.py:138`** | 같음 | `ValueError` `factory.py:57` |
| GLM-5.2 | `LMCacheConnectorV1`, 내장판 | 통과 (HMA 자동 꺼짐) | 통과 | `ValueError` `factory.py:57` |
| GLM-5.2 | 외부 `LMCacheMPConnector`, `OffloadingConnector` | 통과 | 통과 | 통과 |

`refrun`(lmcache 없음)의 결과는 `LMCacheMPConnector` 줄만 다릅니다. 그 줄은 `ModuleNotFoundError`(`vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:11`)입니다.

### 표에 없던 발견: `SlidingWindowMLASpec` 승격은 `TypeError`로 끝납니다

`replace_as`는 `SlidingWindowMLASpec`을 `MLAAttentionSpec`으로 바꿀 때 `drop=("extra_retained_tokens",)`만 넘깁니다(`vllm/v1/core/kv_cache_utils.py:1746`). 그런데 원본에는 `bounded_replay` 필드(`vllm/v1/kv_cache_interface.py:956`)도 있고 대상 클래스에는 없습니다. 그래서 생성자가 `kv_cache_interface.py:138`에서 `TypeError`를 냅니다. `replace_as` 설명은 drop에 적지 않은 필드는 대상에 있어야 한다고 적습니다.

원인을 가른 탐침입니다. 모델 모양 없이 기본 생성자로 만들었습니다.

| 입력 | 결과 |
|---|---|
| MLA + SlidingWindowMLA, `bounded_replay=False` | `TypeError`, `:1746` → `:138` |
| MLA + SlidingWindowMLA, `bounded_replay=True` | 같음 |
| MLA + CircularBuffer (슬라이딩 윈도우 없음) | `ValueError` `kv_cache_utils.py:1760` |
| Full + SlidingWindow (non-MLA 승격) | 성공 |

connector 없이 `--disable-hybrid-kv-cache-manager`만 줘도 DeepSeek-V4-Flash, V4.1-Flash 둘 다 같은 `TypeError`입니다. 즉 connector 문제가 아니라 HMA를 끈 경로의 문제입니다. `_try_get_full_allocation_fallback_groups`의 `except ValueError`(`kv_cache_utils.py:1786`)도 이 예외를 잡지 않습니다. 이 동작이 v0.32.0 이후에 고쳐졌는지는 확인하지 않았습니다.

### 생성자까지 (SCHEDULER 역할)

생성자에는 engine core와 같이 `generate_scheduler_kv_cache_config` 결과를 넘겼습니다(`vllm/v1/engine/core.py:339`). 외부 MP는 localhost의 실제 `lmcache server`에 접속합니다.

| 경우 | 결과 |
|---|---|
| GLM-5.3-Flash, chunk 256 | `ValueError` `lmcache/integration/vllm/vllm_multi_process_adapter.py:780` ("must be a multiple of") |
| GLM-5.3-Flash, `--no-enable-prefix-caching` | `ValueError` `lmcache/integration/vllm/kv_cache_group_edits.py:168` |
| GLM-5.3-Flash, batched token < block | `ValueError` `lmcache/integration/vllm/lmcache_mp_connector.py:421` |
| GLM-5.2, `lazy_offload` + prefix caching 끔 | `ValueError` `lmcache/integration/vllm/lmcache_mp_connector.py:722` |
| 서버 없음 | `ConnectionError` `lmcache/integration/vllm/vllm_multi_process_adapter.py:332` |
| GLM-5.3-Flash BLHNC, chunk = scheduler block, `--separate-object-groups` | 생성됨. 폭 `[4352×5, 0]`, 마지막 tail은 저장 안 함 |
| 같은 조건, `--separate-object-groups` 없음 | 생성됨 (P8-19의 셋째 조건은 생성자가 검사하지 않음) |
| DeepSeek-V4.1-Flash BLHNC | 생성됨. 저장 대상은 폭 64 group 하나, scheduler block 64 |
| DeepSeek-V4-Flash BLHNC | 생성됨. 폭 `[64, 64, 256, 4, 8]`, scheduler block 256. 값의 집합이 P8-21이 옮긴 코드 주석 256/64/8/4와 같음 |
| GLM-5.2 LBHNC | 생성됨. 폭 `[16]`, group이 하나라 `report_request_errors`가 거짓 |
| `OffloadingConnector`, GLM-5.3-Flash LBHNC | 생성됨. 대상 group은 0~5, scratch tail 제외 |
| `OffloadingConnector`, GLM-5.2 LBHNC | 생성됨. 대상 group은 0 |
| `LMCacheConnectorV1`, GLM-5.2, 외부 어댑터 | 생성됨 |
| `LMCacheConnectorV1`, GLM-5.2, `use_native` | `ImportError` `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_integration/multi_process_adapter.py:12` (`CudaIPCWrapper` 없음) |
| 내장판 `reformat_block_ids`, group 2개 | `RuntimeError` `vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector.py:78` |

단축 플래그: `--kv-offloading-size 2`는 `OffloadingConnector`와 `cpu_bytes_to_use: 2147483648`로, `--kv-offloading-backend lmcache`를 더하면 `LMCacheMPConnector`와 빈 extra로 풀립니다(크기를 넘기지 않음, P8-03). `backend`만 주면 connector가 없습니다.

layout에 따라 갈리는 것: `OffloadingConnector`와 외부 MP는 DeepSeek-V4-Flash, V4.1-Flash에서 BLHNC면 생성되고 LBHNC면 `NotImplementedError` `kv_cache_utils.py:1347`(indexer `k_cache` page)입니다. 이는 **bf16 기본값 산술**의 결과입니다. 서빙 dtype과 GPU backend의 page 정렬을 재현하지 않았으므로 "V4 offloading이 막힌다"는 근거로 쓰면 안 됩니다. GLM-5.3-Flash는 LBHNC에서 scheduler block이 69632로 커집니다. 실제 `resolve_kv_cache_layout`은 모든 worker가 모든 layout을 지원한다고 **가정**하고 불렀고 다섯 모델 모두 LBHNC를 골랐습니다. GPU worker 목록에서 무엇을 고르는지는 미확인입니다.

N 값: 실제 `Platform._align_hybrid_block_size`를 GLM-5.3-Flash config로 불러 TP1 4352, TP4 1152가 나왔습니다. `FLASHINFER_MLA`를 import하지 못해 `FLASH_ATTN`을 대역으로 넣은 값입니다. **GPU의 N이 아닙니다.** 진짜 값은 P8-20대로 시작 로그에서 읽어야 합니다.

### 가짜 텐서 저장 (`lmcache server` + ZMQ 클라이언트)

어떤 모델도 관여하지 않습니다. 1 chunk는 4096 byte인 부동소수 텐서입니다.

| 시나리오 | 결과 |
|---|---|
| 왕복, `--chunk-size 16` | 저장 전 hit 0, chunk 3개 저장 뒤 hit 3, 넣은 값이 그대로 돌아옴. 남은 5 token은 저장 안 함 |
| 다른 `cache_salt` | hit 0 |
| 앞부분만 같은 token | 온전히 겹치는 chunk 1개만 hit |
| L1 축출, `--eviction-policy LRU`, L1 약 105 KB | 60개를 모두 저장한 뒤 맨 처음 chunk는 없고 가장 최근 chunk는 있음. 남은 것은 최근 쪽 연속 구간 |
| `--chunk-size 32 --separate-object-groups` | 왕복 성공. 단 클라이언트가 group 하나만 등록해 **나누기 자체는 실행되지 않음** |
| `--chunk-size 0` | 서버가 뜨고 `/status`가 정상. 거부되지 않음 |

살아남은 chunk 수는 실행마다 다릅니다(12개, 13개를 봤습니다). 축출 제어기가 초 단위로 돌기 때문으로 보이며 테스트는 개수가 아니라 모양을 봅니다.

## 3. 돌리지 못한 것 (`not_run`)

| 항목 | 이유 |
|---|---|
| PyPI wheel 설치 | 위 `cupy-cuda13x` 줄 |
| worker 역할 connector, `register_kv_caches`, KV 저장·복원 | 실행 중인 모델의 KV tensor가 필요 |
| 실제 모델, 가중치, 요청 | GPU 없음, vLLM 서버 없음 |
| `FLASHINFER_MLA` 등 GPU backend | `ModuleNotFoundError: No module named 'flashinfer'` |
| GPU worker가 고르는 실제 layout | `get_supported_kv_cache_layouts`가 GPU backend를 요구 |
| `--separate-object-groups`의 실제 나누기 | 가짜 클라이언트가 group 하나만 등록 |
| Kimi-K3 connector 생성자 | config 스냅샷 없음 |
| FlashKDA checkpoint block 저장·복원 (P8-26) | worker 쪽 저장과 복원이 필요 |
| L2 계층, gRPC, CacheBlend, PD | 이 실행 범위 밖 |

## 4. 표 칸을 어떻게 바꿀 수 있나

`실제 클래스 호출`은 **"이 칸의 관문이나 생성자를 실제 클래스로 돌려 봤다"**는 뜻입니다. 동작 보증이 아닙니다. `내장 prefix cache`와 `PD 분리` 열은 이번 실행과 무관해 그대로 둡니다.

| 모델 | 열 | 지금 | 다음 표지 | 적을 내용 |
|---|---|---|---|---|
| GLM-5.2 | 내장 offloading | `코드 읽기` | `코드 읽기`, `실제 클래스 호출` | SCHEDULER 생성까지 |
| GLM-5.2 | `LMCacheConnectorV1` | `미확인` | `실제 클래스 호출` | HMA 자동 꺼짐, 외부 어댑터 생성까지. `use_native`는 `ImportError` |
| GLM-5.2 | `LMCacheMPConnector` | `문서 검증` | `문서 검증`, `실제 클래스 호출` | 문서의 버전은 그대로, v0.32.0 + v0.5.6 생성까지 |
| GLM-5.3-Flash | 내장 offloading | `문서 검증` | `문서 검증`, `실제 클래스 호출` | commit 표기는 그대로, v0.32.0 생성까지 |
| GLM-5.3-Flash | `LMCacheConnectorV1` | `코드가 막음` | `코드가 막음`, `실제 클래스 호출` | 인용 줄 그대로 확인 |
| GLM-5.3-Flash | `LMCacheMPConnector` | `코드 읽기` | `실제 클래스 호출` | 생성까지. 거부 네 경우 실행. P8-26은 계속 미확인 |
| DeepSeek-V4 | 내장 offloading | `코드 읽기` | `코드 읽기` | layout에 따라 갈리고 dtype을 재현 못 함 |
| DeepSeek-V4 | `LMCacheConnectorV1` | `미확인` | `코드가 막음`, `실제 클래스 호출` | `TypeError`, `:1746` → `:138` |
| DeepSeek-V4 | `LMCacheMPConnector` | `문서 검증` | `문서 검증` | 덧붙임은 BLHNC 한정 |
| DeepSeek-V4.1-Flash | 내장 offloading | `문서 검증` | `문서 검증` | 덧붙임은 BLHNC 한정 |
| DeepSeek-V4.1-Flash | `LMCacheConnectorV1` | `코드가 막음` | `코드가 막음`, `실제 클래스 호출` | **인용 줄을 고침.** `:1756-1760`이 아니라 `TypeError` `:1746` → `:138` |
| DeepSeek-V4.1-Flash | `LMCacheMPConnector` | `문서 검증` | `문서 검증` | 덧붙임은 BLHNC 한정 |
| Kimi-K3 | 내장 offloading | `코드 읽기` | `코드 읽기` | 관문만 통과, 생성자 실행 안 함 |
| Kimi-K3 | `LMCacheConnectorV1` | `코드가 막음` | `코드가 막음`, `실제 클래스 호출` | 인용 줄 그대로 확인 |
| Kimi-K3 | `LMCacheMPConnector` | `문서 검증` | `문서 검증` | 관문만 통과, 생성자 실행 안 함 |

## 5. 대장 문장을 고칠 곳

| ID | 대장 | 실행 결과 |
|---|---|---|
| P8-15 | `SlidingWindowMLASpec`은 MLA로 승격 | MLA와 섞이면 `TypeError`로 끝납니다. non-MLA 승격만 성공합니다 |
| P8-05 | `ImportError`면 내장으로 물러남 | `lmcache`가 아예 없으면 `lmcache_mp_connector.py:11`에서 모듈이 실패해 물러나지 못합니다. 하위 모듈만 없을 때 물러납니다 |
| P8-09 | chunk 비배수는 `lmcache_mp_connector.py:811-820` | scheduler block의 배수가 아니면 `vllm_multi_process_adapter.py:780`에서 먼저 납니다 |
| P8-04 | `use_native` 참이면 동봉 구현 | LMCache v0.5.6과 함께면 `ImportError`로 멈춥니다. 그 버전은 `DeviceIPCWrapper`만 있습니다 |
| P8-19 | 셋째 조건은 문서상 요구 | 일치합니다. 생성자는 검사하지 않습니다. 필요 없다는 뜻은 아닙니다 |

`AGENTS.md`의 "LMCache(v0.5.6)는 설치도 실행도 하지 않았다"와 `part8.md` 머리말의 같은 취지 문장도 함께 고쳐야 합니다. 설치와 가짜 텐서 저장, 관문, 스케줄러 쪽 생성자는 돌렸고, 모델 경로는 여전히 돌리지 않았습니다. 이 문서는 그 파일들을 고치지 않았습니다.
