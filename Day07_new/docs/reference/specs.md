# KV spec 실제 클래스 호출 결과 (vLLM v0.32.0)

원자료: `Day07_new/data/reference_specs.json`. 대조 테스트: `Day07_new/tests/test_reference_specs.py`. 대조 대상: `Day07_new/vllm_lab/kv_cases.py`.

## 1. 무엇을 돌렸나

- 상태: `partial`. CPU에서 실제 층 클래스의 `__init__`과 `get_kv_cache_spec`을 meta device로 불렀습니다. 가중치도 forward도 서버도 없습니다.
- 환경: macOS arm64, Python 3.12.14, torch 2.15.0, transformers 5.22.1, GPU 없음, vLLM 소스 트리 v0.32.0(`5df63a7`).
- 입력: Hugging Face의 config.json 세 개(2026-11-02 받음). sha256은 원자료에 있고, 필드 값은 `data/model_configs.json` 스냅샷과 같았습니다. `max_model_len`은 8192로 두었습니다.
- 흐름: 실제 층 생성, `Platform.update_block_size_for_backend`(`vllm/platforms/interface.py:750`), `attn_utils.get_kv_cache_spec`(`vllm/v1/worker/gpu/attn_utils.py:139`), `resolve_kv_cache_layout`, `get_kv_cache_groups`(`vllm/v1/core/kv_cache_utils.py:2159`), `get_kv_cache_configs`(100 GiB를 임의로 넣어 block 수와 stride를 얻음) 순서입니다.
- block 크기 단계는 CPU 플랫폼의 재정의(`vllm/platforms/cpu.py:533`)를 일부러 건너뛰고 기본 구현을 불렀습니다. `vllm/platforms/cuda.py`에는 재정의가 없어 CUDA도 이 구현을 쓰고, CPU 재정의는 Phase 1을 하지 않아 GPU 쪽 block 크기가 나오지 않기 때문입니다.
- 패치와 우회 10개(원자료 `patches`에 그대로 있음): SM 값 고정, backend를 시나리오 값으로 지정, `torch.cuda.Stream`/`Event` 무동작 클래스, FP8 weight 커널 mock, FlashInfer 유무 함수를 True로, torchvision stub, flashkda를 `__init__` 뒤 지정, align 값을 `VllmConfig` 뒤 지정, `speculative_config`를 값만 든 객체로 지정, 위 block 크기 단계의 기본 구현 호출.
- 시나리오 33개 중 29개가 끝까지 돌았습니다. 나머지 4개 중 3개는 코드가 거부한 조합이고(4절) 1개는 환경 한계입니다(5절).
- 실행 스크립트는 scratch에만 있고 저장소에 넣지 않았습니다.

## 2. 결과

### record와 토큰당 값 (kv_cases가 가정한 조건)

| 모델, 조건 | 항목 | spec 클래스 | 층 수 | record(B) | tokens_per_state | page(B) | 토큰당, record 기준 | 토큰당, page 기준 |
|---|---|---|---|---:|---:|---:|---:|---:|
| GLM-5.3-Flash, BF16, FLASHMLA_SPARSE, block 4352 | main | `MLAAttentionSpec` | 11 | 1024 | 1 | 4,456,448 | 11,264 | 11,264 |
| | indexer | `MLAAttentionSpec` | 11 | 132 | 4 | 143,616 | 363 | 363 |
| DeepSeek-V4-Flash, `fp8_ds_mla`, mxfp4 indexer, SM100, block 256 | CSA main | `MLAAttentionSpec` | 21 | 584 | 4 | 37,440 | 3,066 | 3,071.25 |
| | HCA main | `MLAAttentionSpec` | 20 | 584 | 128 | 1,728 | 91.25 | 135 |
| | indexer | `MLAAttentionSpec` | 21 | 68 | 4 | 4,608 | 357 | 378 |
| DeepSeek-V4.1-Flash, `nvfp4_ds_mla`, mxfp4 indexer, SM100, block 128 | main (2) | `MLAAttentionSpec` | 3 | 288 | 2 | 18,432 | 432 | 432 |
| | main (1) | `MLAAttentionSpec` | 1 | 288 | 1 | 36,864 | 288 | 288 |
| | indexer (2) | `MLAAttentionSpec` | 3 | 68 | 2 | 4,608 | 102 | 108 |
| | indexer (1) | `MLAAttentionSpec` | 1 | 68 | 1 | 8,704 | 68 | 68 |

합계는 다음과 같습니다. stride는 `tensor_bytes / num_blocks / block_size`입니다.

| 모델 | kv_cases 합 | 실제 record 합 | 실제 stride 기준 |
|---|---:|---:|---:|
| GLM-5.3-Flash | 11,627 | 11,627 | 11,631.53 |
| DeepSeek-V4-Flash | 3,514.25 | 3,514.25 | 3,584.25 |
| DeepSeek-V4.1-Flash | 890 | 890 | 896 |

### 저장 형식별 main record

| 모델 | 조건 | 해석된 형식 | record(B) | indexer(B) | block |
|---|---|---|---:|---:|---:|
| GLM | FLASHMLA_SPARSE, `auto`, SM90 | BF16 | 1024 | 132 | 4352 |
| GLM | FLASHINFER_MLA_SPARSE_SM90, `auto` | BF16 | 1024 | 132 | 4352 |
| GLM | FLASHINFER_MLA_SPARSE_SM90, `fp8` | `fp8` | 512 | 132 | 8576 |
| GLM | FLASHINFER_MLA_SPARSE, `fp8`, SM100 | `fp8` | 512 | 132 | 8576 |
| GLM | FLASHMLA_SPARSE, `fp8_ds_mla`, SM90 | `fp8_ds_mla` | 656 | 132 | 8576 |
| GLM | FLASHMLA_SPARSE, `nvfp4_ds_mla`, SM100 | `nvfp4_ds_mla` | 352 | 132 | 8576 |
| GLM | FLASHINFER_MLA_SPARSE_SM120, `auto`와 `fp8` | `fp8_ds_mla` | 656 | 132 | 8704 |
| V4 | FlashMLA, `auto`, SM90 | `fp8_ds_mla` | 584 | 132 | 256 |
| V4 | FlashInfer, `auto`, SM90 | BF16 | 1024 | 132 | 256 |
| V4 | FlashInfer, `fp8`, SM90 | `fp8` | 512 | 132 | 256 |
| V4 | FlashInfer SM120, `auto` | `fp8_ds_mla` | 584 | 132 | 256 |
| V4.1 | FlashMLA, `auto`, SM90 | `fp8_ds_mla` | 584 | 132 | 64 |
| V4.1 | FlashMLA, `auto`, SM100 | `fp8_ds_mla` | 528 | 132 | 128 |
| V4.1 | FlashMLA, `nvfp4_ds_mla`, SM100 | `nvfp4_ds_mla` | 288 | 132 | 128 |
| V4.1 | FlashInfer, `auto`, SM90 | BF16 | 1024 | 132 | 128 |
| V4.1 | FlashInfer SM120, `auto` | `fp8_ds_mla` | 584 | 132 | 128 |

indexer의 68B는 `indexer_kv_dtype=mxfp4`를 준 SM100 시나리오에서만 나왔습니다. V4.1 Mega attention은 만들지 못했지만(5절), `packed_kv_cache_dtype`과 `_resolve_dsv4_kv_cache_dtype`을 직접 불러 `auto`가 `nvfp4_ds_mla`로 풀리는 것은 확인했습니다.

### GLM-5.3-Flash KDA 고정 state (`MambaSpec`, 34층)

conv dtype은 bfloat16, recurrent dtype은 float32입니다. `MambaStateShapeCalculator`와 `MambaStateDtypeCalculator`를 직접 불러도 같은 값입니다.

| num_spec | 모드 | checkpoint | conv(B) | recurrent(B) | 잔류 벌 수 | 층당 page(B) | 요청당, padding 없음 | 요청당, 실제 page |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | none | 0 | 147,456 | 4,194,304 | 1 | 4,456,448 | 147,619,840 | 151,519,232 |
| 0 | none | 1 | 147,456 | 4,194,304 | 1 | 4,456,448 | 147,619,840 | 151,519,232 |
| 5 | none | 0 | 393,216 | 4,194,304 | 6 | 4,587,520 | 935,854,080 | 935,854,080 |
| 0 | align | 0 | 147,456 | 4,194,304 | 2 | 4,456,448 | 295,239,680 | 303,038,464 |
| 5 | align | 0 | 393,216 | 4,194,304 | 7 | 4,587,520 | 1,091,829,760 | 1,091,829,760 |
| 0 | align | 1 | 147,456 | 4,194,304 | 3 | 4,456,448 | 442,859,520 | 454,557,696 |
| 5 | align | 1 | 393,216 | 4,194,304 | 8 | 4,587,520 | 1,247,805,440 | 1,247,805,440 |

num_spec 5에서 padding이 사라지는 것은 block이 4480으로 올라 main page와 state가 정확히 같아지기 때문입니다.

TP4(TP 그룹만 `world_size=4`로 바꾼 호출)에서는 conv 모양 `[3, 6144]`, recurrent 모양 `[16, 128, 128]`, state 1,085,440B, page 1,179,648B, block 1152입니다. 네 rank를 더한 요청당 값은 padding 없이 147,619,840B, 실제 page로 160,432,128B이고, align과 checkpoint 1이면 442,859,520B와 481,296,384B입니다.

### kv_cases가 세지 않는 층 (참고값)

| 모델 | 층 종류 | 클래스 | 층 수 | block | record(B) | page(B) | 창 또는 ring |
|---|---|---|---:|---:|---:|---:|---|
| GLM, BF16 | tail ring | `CircularBufferSpec` | 11 | 4 | 256 × head 2 | 2,048 | spec 5면 block 16, page 8,192 |
| V4, `fp8_ds_mla` | SWA | `SlidingWindowMLASpec` | 43 | 64 | 584 | 37,440 | 창 128 |
| V4 | CSA 압축 상태 | `SlidingWindowMLASpec` | 21 | 4 | 8,192 | 32,832 | 창 8 |
| V4 | HCA 압축 상태 | `SlidingWindowMLASpec` | 20 | 8 | 4,096 | 32,832 | 창 128 |
| V4 | indexer 압축 상태 | `SlidingWindowMLASpec` | 21 | 4 | 2,048 | 8,640 | 창 8 |
| V4.1, SM100 | SWA | `SlidingWindowMLASpec` | 40 | 32 | 528 | 16,896 | 창 128 |
| V4.1, SM90 | SWA | `SlidingWindowMLASpec` | 40 | 32 | 584 | 19,008 | 창 128 |
| V4.1 | 압축 상태 | `CircularBufferSpec` | 3 | 8 | 4,096 | 32,768 | ring 8행 |

## 3. KV cache group 수

`get_kv_cache_groups`를 그대로 불렀습니다. 모든 group이 `UniformTypeKVCacheSpecs`이므로 packed 경로(`_get_packed_kv_cache_groups`, `vllm/v1/core/kv_cache_utils.py:1860`)가 값을 돌려준 것이고 `unify_kv_cache_spec_page_size`까지는 가지 않았습니다. layout은 모든 시나리오에서 `BLHNC`였습니다. 괄호는 group별 층 수입니다.

| 모델 | 조건 | group 수 | 구성 |
|---|---|---:|---|
| GLM | BF16, none 또는 align, spec 0 또는 5, TP1 또는 TP4 | 6 | KDA 4개(9, 9, 8, 8), main과 indexer 1개(22), tail 1개(11) |
| GLM | `fp8`, FlashInfer | 6 | KDA 4개(9, 9, 8, 8), 22, 11 |
| GLM | `fp8_ds_mla` (FlashMLA, SM120) | 5 | KDA 3개(12, 11, 11), 22, 11 |
| GLM | `nvfp4_ds_mla` | 7 | KDA 5개(7, 7, 7, 7, 6), 22, 11 |
| V4 | 모든 형식 | 5 | SWA 2개(22, 21), main과 indexer 1개(62), 압축 상태 2개(42, 20) |
| V4.1 | `fp8_ds_mla` SM90, 또는 `nvfp4_ds_mla`와 mxfp4 | 9 | SWA 7개(6, 6, 6, 6, 6, 5, 5), 8, 3 |
| V4.1 | `nvfp4_ds_mla`와 fp8 indexer | 7 | SWA 5개(8 × 5), 8, 3 |
| V4.1 | `fp8_ds_mla` SM100, BF16, SM120 | 6 | SWA 4개(10 × 4), 8, 3 |

- group 수는 저장 형식에 따라 움직입니다. "모델당 몇 group"이라는 단일 값은 없습니다. 코드의 docstring은 층을 묶음으로 나눌 때 padding이 가장 적은 반복 수를 고르고, Mamba 묶음은 attention이 이미 요구한 block에 맞춰 더 나눈다고 적습니다(`vllm/v1/core/kv_cache_utils.py:1866-1871`). 형식별 수가 왜 그 값인지를 이 실행에서 분해해 확인하지는 않았습니다.
- main과 indexer는 어떤 시나리오에서도 한 group에 들어갔습니다. spec 종류가 넷(KDA, main, indexer, tail)이어도 group 구성은 그 수와 다릅니다.
- group별 block 크기도 다릅니다. GLM BF16 none은 KDA 8192(`max_model_len`), main 4352, tail 4입니다. align은 KDA도 4352입니다. V4는 SWA 64, main 256, 압축 상태 4와 8입니다.

## 4. 코드가 거부한 조합

환경 문제가 아니라 코드의 검사가 낸 결과입니다.

| 조합 | 오류 | 위치 |
|---|---|---|
| V4, SM90, `indexer_kv_dtype=mxfp4` | `ValueError`: SM10x만 받는다 | `vllm/v1/attention/backends/mla/indexer.py:91` |
| V4.1 FlashMLA, SM90, `nvfp4_ds_mla` | `ValueError`: SM100에서만 해석한다 | `vllm/models/deepseek_v41/attention.py:524` |
| V4.1 FlashInfer, SM100, `fp8_ds_mla` | `ValueError`: plain row backend는 packed 형식을 받지 않는다 | `vllm/models/deepseek_v41/attention.py:164` |

## 5. 만들지 못한 것

| 대상 | 이유 | 대신 한 것 |
|---|---|---|
| GLM 모델 클래스 전체 | `tilelang` 없음(mHC 커널) | attention 층 45개만 생성 |
| V4 모델 클래스 전체 | CPU 경로에서 MXFP4 MoE backend 없음 | attention 층 43개만 생성 |
| V4.1 모델 클래스 전체 | CUDA 없는 torch | attention 층 40개만 생성 |
| V4.1 Mega attention | `__init__`이 `weight_scale`을 읽는데 weight 커널을 mock으로 막아 없음 | `auto` 해석 함수만 호출 |

CUDA 플랫폼 클래스로 바꾸어 돌리는 길은 import 단계(`_C_stable_libtorch`, flash attention, `cutlass_scaled_mm_supports_block_fp8`)에서 막혀 CPU 플랫폼에 SM 값만 얹었습니다. MTP drafter 층은 만들지 않았으므로 spec 5 시나리오의 group 수에 drafter 층은 들어 있지 않습니다.

## 6. 증명한 것과 증명하지 않은 것

**증명한 것.** 이 소스의 실제 층 클래스에 실제 config를 넣으면 record, tokens_per_state, 층 지도, KDA 모양과 dtype, 잔류 벌 수가 kv_cases와 맞습니다. page와 block 크기, group 수는 패치한 조건에서 실제 함수가 돌려준 값입니다. GLM BF16의 TP1 4352와 TP4 1152는 vLLM의 자체 테스트 상수와도 같습니다(`tests/v1/attention/test_kpool_indexer_block_sizes.py:26`). V4의 256은 그 backend가 선언한 값입니다(`vllm/models/deepseek_v4/sparse_mla.py:60`).

**증명하지 않은 것.**

- 서버를 띄우지 않았습니다. 시작 로그의 값이 이와 같다고 말할 수 없습니다.
- 메모리를 재지 않았습니다. 모든 byte 값은 spec 속성과 config 계산이고 profiling이 없습니다. stride의 100 GiB는 임의의 입력입니다.
- backend는 코드의 선택 경로가 아니라 시나리오로 정했습니다. 어느 GPU에서 어느 backend가 실제로 잡히는지는 이 실행의 결과가 아닙니다. FlashInfer와 FlashMLA 커널 유무 검사도 지났습니다.
- TP4는 TP 그룹을 값만 든 객체로 바꾼 호출입니다. 실제 4-GPU 분산 실행이 아닙니다.
- SWA의 `max_memory_usage_bytes`는 `max_in_flight_tokens`(이 실행은 8192)에 달려 있어 이 표에 넣지 않았습니다.

## kv_cases와 다른 점

record 기준 값은 모두 맞습니다. 다른 것은 page와 stride 기준 값 15행이고 전부 `EXPECTED_DIFFERENCES`에 값과 이유로 있습니다. kv_cases는 padding을 세지 않는다고 적었으므로(`vllm_lab/kv_cases.py:82`, `:93`) 계산 오류가 아니라 범위의 차이입니다. kv_cases는 고치지 않았습니다.

| 값 | kv_cases | 실제 | 원인 |
|---|---:|---:|---|
| V4 합, 토큰당 | 3,514.25 | 3,584.25 | page를 576B 배수로 올림. stride는 그 page의 합 |
| V4 CSA main 몫 | 3,066 | 3,071.25 | 37,376이 37,440으로 |
| V4 HCA main 몫 | 91.25 | 135 | 1,168이 1,728로. 층당 48% 증가 |
| V4 indexer 몫 | 357 | 378 | 4,352가 4,608로 |
| V4.1 합, 토큰당 | 890 | 896 | 압축률 2인 indexer page 4,352가 512 배수 4,608로 |
| V4.1 indexer 압축률 2 몫 | 102 | 108 | 같음 |
| GLM 합, 토큰당 | 11,627 | 11,631.53 | page 합 50,600,704를 `block_stride_alignment` 8,448과 1,024의 최소공배수 33,792의 배수로 올려 stride 50,620,416(`vllm/v1/core/kv_cache_utils.py:1551`) |
| GLM KDA 요청당, none | 147,619,840 | 151,519,232 | KDA page 4,341,760이 attention page 4,456,448로 |
| GLM KDA 요청당, align | 295,239,680 | 303,038,464 | 같음 |
| GLM KDA 요청당, align, checkpoint 1 | 442,859,520 | 454,557,696 | 같음 |
| GLM KDA 요청당, TP4, 네 rank 합 | 147,619,840 | 160,432,128 | rank당 1,085,440이 1,179,648로. padding 8.7% |
| GLM KDA 요청당, TP4, align, checkpoint 1 | 442,859,520 | 481,296,384 | 같음 |
| 교차 문맥, none | 12,696 | 13,027 | 위 두 값의 비 |
| 교차 문맥, align, checkpoint 1 | 38,089 | 39,080 | 같음. TP4에서는 41,330 |

`_min_block_size`는 값이 아니라 배수 관계만 맞춥니다. 실제 block은 kv_cases의 최소값(GLM 4, V4 128, V4.1 2)의 배수이지만 크기는 훨씬 큽니다. kv_cases는 이 점을 `_CAPACITY_ASSUMPTIONS`에 적었습니다.

## 02c, 04b 글과 다른 점

셀 번호는 0부터 셉니다. 노트북은 고치지 않았습니다.

| 위치 | 글 또는 코드 | 실제 결과 |
|---|---|---|
| 02c 셀 54, 56 | V4 꼬리를 CSA 21층과 HCA 20층으로 세어 11,862,016B | indexer 압축 상태 21층이 빠져 있음. 같은 하한 계산이면 8행 × 2,048B × 21층 = 344,064B가 더 붙어 12,206,080B |
| 02c 셀 23, 69 | V4 block을 압축률 최소공배수 128로 보여 줌(보고서 기준) | vLLM backend는 256을 선언. CSA 64개, HCA 2개 |
| 02c 셀 44 | mxfp4를 opt-in으로 설명 | SM10x 조건이 빠져 있음. V4는 SM90에서 거부되는 것을 실행으로 확인(3,514.25의 68B). V4.1은 실행하지 않았지만 같은 함수 `dsa_indexer_uses_fp4`를 지난다(`vllm/v1/attention/backends/mla/indexer.py:59`, `:91`) |
| 02c 셀 57, 04b 셀 36 | GLM의 실제 block 크기가 자료에 없다고 적음 | 클래스 호출 값이 생김. BF16 TP1 4352, TP4 1152, spec 5 TP1 4480, FP8 8576 또는 8704. 시작 로그 확인은 여전히 아님 |
| 04b 셀 6, 8, 14 | GLM `BLOCK = 128` (수업이 정한 값) | 이 조건의 실제 block과 다름. 토큰당 계산에는 영향이 없고 block 수만 달라짐 |
| 04b 셀 11 | 교차 문맥 약 38,089 | padding을 넣으면 39,080, TP4에서 41,330 |

04b 셀 11의 표(SM10x `fp8` 512, SM90 FlashInfer `fp8` 512, SM120 656, SM90 `fp8_ds_mla` 656), 04b 셀 13의 token당 11,627, 5,995, 7,579, 04b 셀 15의 V4.1 528과 584, 02c 셀 15의 record 표, 02c 셀 54의 V4.1과 GLM 꼬리 값은 record 기준으로 일치합니다.
