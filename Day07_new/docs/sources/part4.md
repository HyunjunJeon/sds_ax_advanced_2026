# Part 4 근거 대장

Part 4(Quantization 전략)에서 수업이 인용할 주장만 모았다. 코드 줄은 vLLM v0.32.0(커밋 5df63a7) 트리에서 직접 열어 확인했다. 블로그는 "Inside vLLM: 서버 시작부터 KV cache까지"(`inside-vllm.txt`)이고, 레시피는 GLM-5.3-Flash 레시피 텍스트(`recipe-glm53.txt`)다. 블로그에는 양자화 절이 없다(`quantiz|양자화|fp8|awq|gptq` grep 결과 0건). 블로그에서 dtype를 다루는 곳은 줄 159, 216, 449뿐이다.

상태 값: 일치 / 문서·코드 차이 / 코드 전용 / 미확인.

| ID | 주장 | 블로그 절 | 공식 문서 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P4-01 | 가중치 양자화(체크포인트가 가진 `quantization_config`)와 KV cache dtype은 서로 다른 설정이다. 가중치는 모델 로드 쪽, KV는 `--kv-cache-dtype`(`CacheConfig.cache_dtype`)이 정한다. 다만 `auto`이면 체크포인트 config가 KV dtype을 정하는 경로가 둘 있다. `quant_method`가 `modelopt`로 시작하고 KV 키가 있을 때와, 일반 attention 층의 `kv_cache_scheme`이다. 가중치가 양자화됐다는 사실만으로는 KV가 바뀌지 않고, 명시한 flag가 이긴다. | 없음 | `docs/features/quantization/README.md:8-24` 가 양자화 형식 목록과 "Quantized KV Cache"를 별도 항목으로 나열 | `vllm/config/cache.py:122` (`cache_dtype`는 CacheConfig 필드); `vllm/utils/torch_utils.py:466-475,512-530`, `vllm/model_executor/layers/attention/attention.py:282-291` (`auto`일 때만 체크포인트 값을 쓰고 명시 선택이 이김) | 일치 |
| P4-02 | `cache_dtype` 기본값은 `auto`이고, `auto`는 기본으로 모델 dtype을 쓴다. 문서는 여기까지만 적지만 코드에는 예외가 있다. P4-01의 두 경로와 모델별 설정(`GlmMoeDsaForCausalLM`을 SM10x에서 돌릴 때)이다. 명시한 flag는 이를 이긴다. GLM-5.3-Flash 체크포인트는 `quant_method`가 `fp8`이고 MLA 층을 쓰므로 체크포인트 경로 둘에 해당하지 않는다(MLA 층 코드에 `kv_cache_scheme` 처리가 없다). 블로그의 dtype 표도 `auto`면 config에 적힌 dtype을 쓴다고 하나, 이는 모델 dtype 설명이지 KV dtype 설명은 아니다. | 서버 초기화 표 (`inside-vllm.txt:159`, KVCacheSpec 안의 dtype은 `:216`) | `quantized_kvcache.md:39` (`auto`: 모델 기본 dtype) | `vllm/config/cache.py:122-123`; `vllm/utils/torch_utils.py:466-475,512-530,536-538`; `vllm/model_executor/layers/attention/attention.py:282-291`; `vllm/model_executor/layers/attention/mla_attention.py:487-528`; `vllm/model_executor/models/config.py:43-55` | 문서·코드 차이 |
| P4-03 | `cache_dtype`의 허용 값은 `auto, float16, bfloat16, fp8, fp8_e4m3, fp8_e5m2, fp8_inc, fp8_ds_mla, nvfp4_ds_mla, turboquant_*, ultraquant_4bit, *_per_token_head, nvfp4, nvfp4_4over6` 등이다. KV 전용 문서(`quantized_kvcache.md`)는 `auto, fp8, fp8_e4m3, fp8_e5m2`만 설명한다. | 없음 | `quantized_kvcache.md:29, 39-41` (네 값만) | `vllm/config/cache.py:39-58` (Literal 전체 목록) | 문서·코드 차이 |
| P4-04 | `fp8_e4m3`은 CUDA 11.8+와 ROCm, `fp8_e5m2`는 CUDA 11.8+에서 지원한다고 문서가 적는다. `fp8`은 `fp8_e4m3`과 같다고 코드 주석이 말한다. 단 MLA의 `FLASHMLA_SPARSE`는 받은 양자화 dtype을 `fp8_ds_mla` 형식으로 바꾼다(`nvfp4_ds_mla` 제외). | 없음 | `quantized_kvcache.md:40-41` | `vllm/config/cache.py:123-124` (docstring: fp8 = fp8_e4m3), `vllm/model_executor/layers/attention/mla_attention.py:363-368` | 일치 |
| P4-05 | `--kv-cache-dtype-skip-layers`는 지정한 층을 모델 기본 dtype으로 남기고 나머지만 양자화한다. 층 번호나 `sliding_window` 같은 attention 종류 이름을 받는다. MLA 층 코드는 층 번호만 본다. | 없음 | `quantized_kvcache.md:43-57` | `vllm/config/cache.py:166-168` (필드와 설명), `vllm/engine/arg_utils.py:1383-1385` (CLI 등록), 분기 `vllm/model_executor/layers/attention/attention.py:300-315`, `vllm/model_executor/layers/attention/mla_attention.py:493-498` | 일치 |
| P4-06 | FP8 KV를 "보정 없이" 쓰면(`kv_cache_dtype="fp8"`) 모든 스케일이 1.0이다. 코드는 양자화 dtype이면 보정 여부와 상관없이 적절한 스케일 없이는 정확도가 떨어질 수 있다는 정보(info) 로그를 낸다. 경고나 오류가 아니다. | 없음 | `quantized_kvcache.md:25-30, 73-75` | `vllm/config/cache.py:360-366` (`logger.info`, 문구 364행), 기본 스케일 `vllm/model_executor/layers/attention/attention.py:133-144` | 일치 |
| P4-07 | 문서는 스케일 계산 방식이 "세 가지"라고 쓰지만 실제로 번호가 붙은 항목은 두 개(기본 스케일 1.0, llm-compressor 보정)뿐이다. 세 번째로 예전에 있던 런타임 계산 항목이 문서에서 지워진 흔적으로 보이지만, 이는 추정이다. | 없음 | `quantized_kvcache.md:23-35` ("three"라 쓰고 항목 2개) | 해당 없음 | 문서·코드 차이 |
| P4-08 | `calculate_kv_scales` 옵션은 v0.32.0의 `CacheConfig`와 `arg_utils.py`에 없다. 소스 전체에서 이 이름은 주석 한 곳에만 남아 있고, 그 주석은 Kimi K3 모델 이야기("K3 has no runtime calculate_kv_scales path")다. 제거 시점은 이 트리만으로는 알 수 없다. 별개로 `*_per_token_head` dtype은 런타임에 스케일을 계산한다고 코드가 적는다. | 없음 | `quantized_kvcache.md`에 언급 없음 | `vllm/models/kimi_k3/nvidia/mla.py:465` (유일한 언급). `vllm/config/cache.py` 전체에 없음(grep). `*_per_token_head` `vllm/config/cache.py:353-359` | 코드 전용 |
| P4-09 | 문서는 정확도와 품질을 위해 데이터셋 보정(llm-compressor)을 권장하고(`quantized_kvcache.md:33, 94`) 헤드별 스케일은 Flash Attention 백엔드에서 보정 경로가 있어야 한다고 한다. 값 분포와 FP8 범위로 보정을 설명하는 문장은 문서에 없다. 스케일 없이 쓰면 정확도가 떨어질 수 있다는 로그만 코드에 있다(`vllm/config/cache.py:364`). 분포와 범위로 푸는 설명은 쓴다면 수업의 해석이라고 표시한다. | 없음 | `quantized_kvcache.md:18-19, 32-35, 92-94` | `vllm/config/cache.py:364` | 일치 |
| P4-10 | FP8 KV가 줄이는 것은 KV 캐시 블록의 원시 payload(요소당 바이트 수)다. 가중치는 KV dtype과 별개다. activation과 CUDA graph 몫은 이 식에 없을 뿐이고, KV dtype이 그 값을 바꾸지 않는다고 코드로 확인하지는 않았다. 블로그는 일반 attention 블록 크기를 `2 * block_size * num_kv_heads * head_size * dtype 크기`로 쓰므로, dtype 크기가 절반이 되면 이 항만 절반이다. 전체 메모리 절감 비율은 이 자료만으로 계산할 수 없다. | KV cache 관리 절 (`inside-vllm.txt:449`), 메모리 예산 (`:216`) | `quantized_kvcache.md:5` ("memory footprint 감소"라고만 서술) | `vllm/v1/kv_cache_interface.py:544-553` (일반 attention의 page 크기); `vllm/utils/torch_utils.py:87-92` (`is_quantized_kv_cache`가 fp8 계열을 양자화로 분류) | 일치 |
| P4-11 | 레시피의 "TP=4에서 FP8 체크포인트 KV pool 14.92M 토큰, BF16 체크포인트 8.87M 토큰"은 체크포인트(가중치)를 바꾼 비교이고, 두 경우의 KV dtype을 레시피가 적지 않았다. 14.92/8.87은 약 1.68배이며, 이를 "FP8 KV의 이득"으로 인용하면 틀린다. 두 수치는 레시피의 AMD Instinct 절(TP=4, 128K context)에 있어 H200 값도 아니다(`recipe-glm53.txt:260`, `:277`, `:279-281`). 측정 방법은 미확인이다. | 없음 | 해당 없음 | 해당 없음 (레시피 `recipe-glm53.txt:279-281`) | 미확인 |
| P4-12 | 문서가 소개하는 양자화 방법: AutoAWQ, BitsAndBytes, GPTQModel, Intel Neural Compressor, LLM Compressor(FP8 W8A8, INT4 W4A16, INT8 W4A8, INT8 W8A8), ModelOpt, 온라인 양자화, Quark, Quantized KV Cache, TorchAO, FP8 ViT. | 없음 | `docs/features/quantization/README.md:10-24` | 해당 없음 | 일치 |
| P4-13 | AWQ: 문서가 AutoAWQ 라이브러리를 deprecated로 표시하고 llm-compressor의 AWQ 예제를 권장한다. GPTQ는 GPTQModel을 쓰며 INT4/INT8을 만들고 Marlin·Machete 커널을 활용할 수 있다고 한다. | 없음 | `auto_awq.md:3-5`, `gptqmodel.md:3-8` | 해당 없음 | 일치 |
| P4-14 | FP8(llm-compressor)은 Ada Lovelace, Hopper, Blackwell에서 W8A8을 지원하고(`fp8.md:4`), 문서는 "메모리 2배 절감, 처리량 최대 1.6배"를 주장하지만 측정 조건이 그 줄에 없어 수업에서 수치로 인용하지 않는다. | 없음 | `llm_compressor/fp8.md:4`(GPU 세대), `:6`(수치) | 해당 없음 | 일치 |
| P4-15 | NVFP4: 문서는 ModelOpt NVFP4 체크포인트를 `quantization="modelopt_fp4"`로 쓰고, llm-compressor도 NVFP4를 지원 목록에 둔다. GLM-5.3-Flash의 NVFP4 변형(`RedHatAI/GLM-5.3-Flash-NVFP4`)은 레시피상 MoE 전문가가 4비트이며 NVIDIA Blackwell이 필요하다. H200(Hopper)에는 맞지 않는다. | 없음 | `modelopt.md:19-21`, `llm_compressor/README.md:23`. 레시피 `recipe-glm53.txt:52-56` | 해당 없음(`nvfp4_ds_mla` KV는 `vllm/v1/attention/backends/mla/flashmla_sparse.py:250-254`에서 SM100 전용이지만 이는 KV 이야기) | 일치 |
| P4-16 | BitsAndBytes는 보정이 필요 없고, v0.32.0에서는 외부 플러그인 `vllm-bnb-plugin`을 설치해야 쓴다. 즉 vLLM 본체 내장이 아니다. | 없음 | `bnb.md:3-9` | 해당 없음 | 일치 |
| P4-17 | GGUF는 문서가 "매우 실험적이고 최적화가 덜 되었으며 다른 기능과 호환되지 않을 수 있다"고 쓴다. 현재로서는 메모리 사용량을 줄이는 방법으로 쓸 수 있다고 적는다. GGUF 지원은 외부 `vllm-gguf-plugin`으로 옮겨졌고 GGUF 모델을 서빙하기 전에 설치해야 한다(`docs/features/quantization/gguf.md:6-7`). | 없음 | `gguf.md:4`, `:6-7` | 해당 없음 | 일치 |
| P4-18 | GLM-5.3-Flash 체크포인트 자체의 `quantization_config`: `quant_method`는 `fp8`, `fmt`는 `e4m3`, `activation_scheme`은 `dynamic`, `weight_block_size`가 있다. `kv_cache_scheme`과 `kv_cache_quant_algo` 키는 없다. `modules_to_not_convert`에는 `attn_mha`, `attn_mqa`, `dt_bias`, `hyper_connection`, `lm_head`, `mapping_proj`, `model.embed_tokens` 등과 층별 `hc_attn_*` 항목이 들어 있어 이들은 양자화에서 제외된다. 같은 config의 `dtype`은 `bfloat16`이다. (HF `config.json`, 줄 8, 290-302, 1804-1805를 원문 그대로 읽음) | 없음 | 해당 없음 | 해당 없음 | 코드 전용 |
| P4-19 | Flash 기본 체크포인트(FP8)는 가중치만 약 306 GiB이며 런타임과 KV 여유분은 별도다. BF16 변형은 약 2배의 가중치 메모리가 든다고 레시피가 적는다. 기본 모델 ID `zai-org/GLM-5.3-Flash`가 FP8 체크포인트다. | 없음 | 해당 없음 | 해당 없음 (레시피 `recipe-glm53.txt:45-52`) | 일치 |
| P4-20 | PDF의 Quality Gate(양자화 전후 품질 비교) 아이디어는 vLLM 기능이 아니라 수업용 점검표다. v0.32.0 문서와 코드에 그런 기능은 확인되지 않았다. | 없음 | 해당 없음 | 해당 없음 | 미확인 |

## H200에서 GLM-5.3-Flash의 KV dtype

코드에서 확인한 것:

- `cache_dtype=auto`를 `fp8_e4m3`으로 바꿔 주는 모델별 설정은 `GlmMoeDsaForCausalLM`에만 있고, 그것도 SM10x(Blackwell)일 때뿐이다(`vllm/model_executor/models/config.py:43-55`, 등록 `:1078`). `Glm5Next*` 아키텍처는 이 `MODELS_CONFIG_MAP`(`:1063`)에 없다(파일 안 `Glm5Next` grep 0건). 체크포인트 경로도 타지 않는다. `quant_method`가 `fp8`이라 `modelopt` 분기에 들지 않고(`vllm/utils/torch_utils.py:466-467`), config에 KV 키가 없으며(P4-18), MLA 층에는 `kv_cache_scheme` 처리가 없다(`vllm/model_executor/layers/attention/mla_attention.py:487-528`). 따라서 Hopper SM90에서 Glm5Next의 `auto`는 코드상 자동으로 FP8이 되지 않고 모델 dtype(config상 bfloat16)을 따른다(`torch_utils.py:536-538`). 이 결론은 코드 읽기에서 나온 것으로, 실제 기동 로그로는 확인하지 않았다.
- sparse MLA 백엔드 `FLASHMLA_SPARSE`는 head_size 512(GLM5Next NoPE)를 SM90에서 `auto/bfloat16/float16/fp8_ds_mla`일 때만 받고, 일반 `fp8`은 이 백엔드에서 거절한다(`vllm/v1/attention/backends/mla/flashmla_sparse.py:219-249`).
- 그런데 코드에는 SM90에서 일반 `fp8`을 받는 백엔드가 있다. `FLASHINFER_MLA_SPARSE_SM90`은 `auto, bfloat16, fp8, fp8_e4m3`을 허용 목록에 두고(`vllm/v1/attention/backends/mla/flashinfer_mla_sparse_sm90.py:148-153`), SM90 전용이며(`:189-190`), FlashInfer 0.6.18 이상과 `kv_lora_rank=512`, `qk_rope_head_dim`이 0 또는 64일 것을 요구한다(`:205-223`). 모듈 설명은 GLM-5.3-Flash NoPE와 FP8 E4M3 KV를 SM90에서 지원한다고 적고(`:3-9`), head_size 512면 SM90 sparse 후보의 맨 앞에 놓인다(`vllm/platforms/cuda.py:142-144`). 이 값이 실제로 동작하는지는 실행하지 않아 미확인이다.

레시피가 말하는 것: Hopper는 이 모델에서 FP8 KV cache를 지원하지 않으며 BF16 KV로 돌려야 한다(`recipe-glm53.txt:87-90`). 위 코드 경로와 어긋나는 문장이고 어느 쪽이 맞는지는 이 자료로 가릴 수 없다. `--kv-cache-dtype fp8`을 쓰는 예시는 GB200(Blackwell) 예시다(`:72-79`). 4xH200(TP4) 검증 기록은 `:318-319`에 있다.

4x H200에서 쓸 플래그: `--kv-cache-dtype`을 넣지 않는다(기본 `auto`, BF16 KV). 근거는 레시피 문장과, H200에서 FP8 KV를 돌려 본 기록이 없다는 점이다. 코드가 막는다는 뜻이 아니다. 레시피의 `--kv-cache-dtype fp8` 줄은 H200 명령에서 빼야 한다. 코드의 `fp8_ds_mla`도 허용 목록에 있으나 레시피가 BF16 KV를 지시하므로 수업에서 쓰지 않는다.

## 수업에 쓰지 말 것

- "FP8 KV로 H200에서 메모리 2배" 같은 문장. 이 자료에는 H200 + Glm5Next + FP8 KV를 측정한 근거가 없고, 레시피는 지원하지 않는다고 한다. 반대로 "코드가 H200 FP8 KV를 막는다"고 말하는 것도 틀린다(위 H200 절).
- 레시피의 14.92M / 8.87M 토큰 비교를 KV dtype 효과로 소개하는 것(P4-11, 체크포인트 비교다).
- `--kv-cache-dtype fp8`을 H200 서빙 명령에 넣는 것.
- `--calculate-kv-scales`가 있다는 설명, 또는 `fp8` KV의 스케일을 런타임에 계산한다는 설명. 그 옵션은 v0.32.0 `CacheConfig`에 없다(P4-08). 런타임 스케일은 `*_per_token_head` dtype에만 해당한다.
- `fp8_e5m2`, `fp8_ds_mla`, `turboquant_*` 등 문서에 설명이 없는 dtype을 효과가 검증된 선택지처럼 제시하는 것.
- FP8 문서의 "2x, 1.6x"를 이 모델의 수치로 옮기는 것(P4-14, 조건 불명).
- NVFP4 변형을 H200 실습에 쓰는 것(Blackwell 필요, P4-15).
- Quality Gate를 vLLM이 제공하는 기능처럼 말하는 것(P4-20).
- 위 표에 없는 속도 향상 수치. 이 대장은 어떤 속도 측정치도 확인하지 않았다.
