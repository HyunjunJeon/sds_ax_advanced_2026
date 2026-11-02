# Day07_new 근거 대장

Day07_new 노트북(Part 1~8)이 인용할 사실은 이 문서가 색인하는 대장에 있는 것만이다. 대장에 없거나 `미확인`인 주장은 노트북에서 사실처럼 쓰지 않는다. 문서와 코드가 다르면 코드가 정답이다.

## 고정한 기준

| 항목 | 값 |
|---|---|
| vLLM | v0.32.0, 커밋 `5df63a7` (2026-10-17). 코드 줄은 이 소스 루트 기준 `vllm/...:줄`, `rust/...:줄` |
| 공식 문서 | 같은 소스 트리의 `docs/` 와 GitHub 이슈·PR 본문. 온라인 docs.vllm.ai는 열어 보지 않았다 |
| 공식 레시피 | https://recipes.vllm.ai/zai-org/GLM-5.3-Flash (2026-10-19 갱신본 텍스트) |
| 블로그 | 「Inside vLLM: 서버 시작부터 KV cache까지 소스 코드 톺아보기」, Jongsu Liam Kim, https://blog.liam.kim/posts/2026/10/Inside-vLLM/ . 페이지에서 라이선스 표시를 찾지 못했다 |
| 확인 방식 | 코드는 읽기가 기본이다. 일부 행은 CPU에서 실제 vLLM·LMCache 클래스나 라이브러리를 호출해 확인했고 행 안에 그 범위를 적었다(`docs/REFERENCE_RUN.md`, `docs/reference/`). 모델을 올린 vLLM 서버, GPU, Pod는 쓰지 않았다. 대장의 "~한다"는 "코드에 이렇게 적혀 있다" 또는 "CPU 호출에서 이렇게 나왔다"로 읽는다. Pod에서 확인하는 항목은 아래 `## Pod 점검 항목`에 있다 |
| 상태 값 | 일치 / 문서·코드 차이 / 블로그·코드 차이 / 코드 전용 / 미확인, Part 8은 자기 보고 / 문서 전용을 더한다 (PDF 대조는 일치 / 표현 주의 / 버전 차이 / 오류 / 미확인) |

## 대장 색인

모든 파일은 `Day07_new/docs/sources/` 아래에 있다. 행 수와 상태별 개수는 각 파일의 표 행을 세어 적었다.

| 파일 | 범위 | 행 수 | 일치 | 문서·코드 차이 | 블로그·코드 차이 | 코드 전용 | 미확인 | 자기 보고 | 문서 전용 |
|---|---|---|---|---|---|---|---|---:|---:|
| `part1.md` | Part 1 vLLM 서빙 기초: step, 컴포넌트, 서버 초기화 순서, request 경로, 상태, V0 제거, MRV2·async scheduling 기본값, Rust frontend | 51 | 39 | 4 | 4 | 3 | 1 | 0 | 0 |
| `part2.md` | Part 2 KV Cache: block, block table, slot, prefix cache hash, 할당·해제·preemption, speculative decoding, hybrid KV cache group, GLM-5.3-Flash KV | 74 | 52 | 2 | 7 | 11 | 2 | 0 | 0 |
| `part3.md` | Part 3 서빙 파라미터와 측정: scheduler 순서, 기본값 표, `vllm bench serve`, TTFT·ITL·TPOT 정의, `/metrics` 이름 | 41 | 25 | 6 | 1 | 8 | 1 | 0 | 0 |
| `part4.md` | Part 4 Quantization: 가중치 양자화와 KV dtype 구분, `--kv-cache-dtype`, H200에서 GLM-5.3-Flash KV dtype | 20 | 13 | 3 | 0 | 2 | 2 | 0 | 0 |
| `part5.md` | Part 5 Local Model과 Agent: 멀티턴 prefix caching, `cache_salt`, `cached_tokens`, `reasoning` 필드, langchain-openai·deepagents 동작 | 25 | 12 | 1 | 1 | 9 | 2 | 0 | 0 |
| `part6.md` | Part 6 Tool Calling 오류: glm47 파서, finish_reason, 잘림, 알 수 없는 도구, strict 수준, Rust 파서 차이, 실패 사례 후보 12개 | 36 | 11 | 5 | 1 | 19 | 0 | 0 | 0 |
| `part7.md` | Part 7 최근 모델의 KV 통제: 세 곱셈 차원, MLA, DSA·IndexShare, CSA·HCA, KDA, 비용 비교 (논문 원문·config·v0.32.0 코드) | 63 | 54 | 0 | 2 | 5 | 2 | 0 | 0 |
| `part8.md` | Part 8 LMCache를 포함한 KV cache 운영: 켜는 법, hybrid 게이트, 지원 상태, 실패 정책, 지표, 오프로딩, PD, 격리 (`## 모델별 지원 상태` 포함) | 56 | 20 | 8 | 0 | 17 | 4 | 6 | 1 |
| `pdf-diff.md` | 강의 PDF(D-01부터 D-38까지)와 `Day07/` README·AGENTS·스크립트(R-01부터 R-14까지)를 v0.32.0·레시피와 대조. 판정 어휘가 달라 열이 맞지 않는다 | 52 | 27 | - | - | - | 9 | - | - |

- `part7.md`의 `블로그·코드 차이` 열 2는 이 대장의 상태어 `논문·코드 차이`(P7-51, P7-63)이며 블로그와 무관하다.
- Part 1부터 Part 8까지 합계는 366행이다(Part 1부터 Part 6까지 247행, `part7.md` 63행, `part8.md` 56행). `part8.md`의 `자기 보고` 6행과 `문서 전용` 1행은 자기 보고·문서 전용 열에 센다. `pdf-diff.md`는 52행(D 38, R 14)이고 판정 어휘가 달라 위 표의 열에 그대로 맞지 않는다. 일치 27은 D 23 + R 4, 미확인 9는 D 5 + R 4이고, 나머지 16행은 표현 주의 13과 버전 차이 3이다.
- 상태는 한 행에 하나만 붙는다. 차이가 있어도 세부는 주장 칸에 있다.
- 각 파일 끝의 `수업에 쓰지 말 것` 절은 노트북이 피해야 할 문장 목록이다. 노트북을 쓰기 전에 해당 Part 것을 먼저 읽는다.

## 차이 모음

한 줄에 ID, 무엇이 어긋나는지를 적었다. 세부 근거는 각 대장의 해당 행에 있다.

### 문서·코드 차이

- P1-03 (`part1.md`): 프로세스 구성 서술은 GPU 하나인 UniProcExecutor 경로에서 worker가 EngineCore 프로세스 안에 있어 문서의 "GPU마다 worker 프로세스 1개"와 다르다.
- P1-05 (`part1.md`): 문서는 `AsyncLLMEngine` 코드가 `vllm/engine/async_llm_engine.py`라고 하지만 그 파일은 별칭 한 줄이고 구현은 `vllm/v1/engine/async_llm.py`다.
- P1-08 (`part1.md`): world_size는 PP x TP x PCP의 곱(`vllm/config/parallel.py:945-949`)인데 문서와 docstring은 TP x PP만 적는다.
- P1-49 (`part1.md`): 레시피의 `--tokenizer-mode glm5_next` 명령은 v0.32.0 TokenizerMode에 없다. 지원 PR #62424는 v0.32.0 커밋보다 늦게 병합됐다.
- P2-69 (`part2.md`): 설계 문서와 `kv_cache_utils.py` docstring은 "정확히 두 group"이라 쓰지만 코드의 coordinator는 attention 종류 개수 제한이 없다.
- P2-70 (`part2.md`): `docs/design/paged_attention.md`는 스스로 역사 문서라 밝히고 가리키는 CUDA 커널 파일이 v0.32.0에 없다.
- P3-07 (`part3.md`): `--gpu-memory-utilization` 기본은 0.92인데 `docs/design/metrics.md`의 예시는 0.9다.
- P3-11 (`part3.md`): 문서는 `max_num_batched_tokens`가 `max_model_len`보다 "커야" 한다고 쓰지만 코드는 같은 값도 허용한다.
- P3-22 (`part3.md`): 문서는 "decode 먼저, 그다음 prefill"이라 쓰지만 코드는 running 큐 전체를 먼저 순회한다.
- P3-24 (`part3.md`): 문서의 preempt 경고 문구(`PreemptionMode.RECOMPUTE` 등)가 v0.32.0 코드에 없다.
- P3-30 (`part3.md`): 문서의 TPOT 식 `(E2E−TTFT)/(n−1)`은 클라이언트 벤치마크 식이고 서버 지표 TPOT는 `decode_time/(n−1)`이다.
- P3-39 (`part3.md`): 문서가 `vllm:num_requests_swapped`를 적지만 v1 지표 코드에는 없다.
- P4-03 (`part4.md`): 문서는 KV dtype 네 값만 설명하는데 코드의 허용 목록은 훨씬 길다.
- P4-07 (`part4.md`): 문서는 스케일 계산 방식이 "세 가지"라 쓰지만 번호 항목은 둘이다.
- P4-02 (`part4.md`): 문서는 `cache_dtype=auto`가 모델 dtype이라고만 적지만 모델별 설정(`GlmMoeDsaForCausalLM`을 SM10x에서 돌릴 때)과 체크포인트 경로의 예외가 있다. 명시한 flag가 이긴다.
- P5-15 (`part5.md`): 응답 필드는 `reasoning` 하나이고 `reasoning_content`는 사라졌다. 공식 문서가 이름 변경을 경고하는데 `Day07/README.md:67` 서술은 버전별 두 이름을 가정한다.
- P6-07 (`part6.md`): 문서의 required/named JSON 스키마 강제 설명이 GLM 파서(`supports_required_and_named=False`)에는 해당하지 않는다.
- P6-12 (`part6.md`): GLM은 `strict`를 주지 않아도 `auto`에서 호출 껍데기가 제약된다. 문서의 "auto는 strict 도구에만 제약"과 다르다.
- P6-26 (`part6.md`): `VLLM_ENFORCE_STRICT_TOOL_CALLING=0`이면 GLM의 required/named에 제약이 남지 않는다. 문서의 "스키마 기반 제약 유지" 문장과 다르다.
- P6-27 (`part6.md`): 문서는 strict가 없는 도구를 "넓은 문법 제약" 또는 "제약 없음"으로 적지만 GLM은 평범한 object 스키마에서도 문서에 없는 키 이름과 기본 값 타입까지 고정한다(xgrammar 시험).
- P6-35 (`part6.md`): 레시피의 `--tokenizer-mode glm5_next`는 v0.32.0에서 Python은 `ValueError`, Rust는 `unknown renderer` 오류로 거부된다(Python 쪽은 레지스트리 호출을 실행해 확인).

### 블로그·코드 차이

- P1-32 (`part1.md`): 블로그는 `get_max_tokens` 안에서 3단계를 한다고 쓰지만 코드의 `get_max_tokens`는 최솟값 한 줄이고 나머지는 생성자와 `get_diff_sampling_param`에 흩어져 있다. 결과는 같다.
- P1-35 (`part1.md`): schedule()의 token budget 차감은 block을 실제로 얻은 뒤에만 한다(`scheduler.py:856`). 블로그의 순서 서술과 조건이 다르다.
- P1-36 (`part1.md`): preempt된 request는 다시 들어올 때 prefix cache를 조회하므로 "prompt부터 다시 계산"은 최악의 경우다(P2-37과 같은 판정).
- P1-40 (`part1.md`): MRV2가 "모든 model의 기본"이라는 서술은 조건부다. Triton이 없거나 미지원 기능이면 V1 runner다(P2-15와 같은 판정).
- P2-12 (`part2.md`): `req_to_blocks`는 `KVCacheManager`가 아니라 group별 `SingleTypeKVCacheManager`가 들고 있다.
- P2-15 (`part2.md`): MRV2가 "모든 model의 기본 경로"라는 서술은 조건부다(Triton 부재나 미지원 기능이면 V1 runner).
- P2-23 (`part2.md`): "padding은 CUDA graph에만 남는다"는 과장이다. DP padding도 있다.
- P2-37 (`part2.md`): preempt된 request가 "prompt부터 다시 계산"은 최악의 경우이고 prefix cache hit로 일부가 재사용될 수 있다.
- P2-61 (`part2.md`): `unify_kv_cache_spec_page_size`는 MLA 등에서 예외를 내지만 상위 함수가 잡아 대체 경로를 먼저 시도한다.
- P2-62 (`part2.md`): group 크기를 "가장 적은 종류의 layer 수"로 잡는다는 서술은 부분적으로만 맞다(1.5배 규칙과 padding layer).
- P2-64 (`part2.md`): "buffer k를 각 group의 k번째 layer가 공유"는 layer-outer 배치만의 설명이고 코드는 `KVCacheLayout`으로 일반화돼 있다.
- P3-23 (`part3.md`): preempt 복귀 때 계산 수가 0이라 prefix cache를 조회하므로 덮어써지지 않은 block은 재사용된다. 블로그의 "처음부터" 서술은 최악의 경우다.
- P5-02 (`part5.md`): "대화 세션 개념이 없다"고 하지만 `session_id` 필드가 있다. block hash에는 들어가지 않아 블로그의 요지는 유지된다.
- P6-31 (`part6.md`): 블로그는 parser가 `reasoning_content`를 떼어 낸다고 쓰지만 v0.32.0 응답 필드는 `reasoning`이다.

### PDF 대조의 오류와 버전 차이

- 오류 판정은 없다. 의심 값(D-02의 8.00x, D-13의 block 4)은 PDF가 "설명용 예시"·"교육용"이라 밝혀 표현 주의로 뒀다.
- R-01 (`pdf-diff.md`): README는 이미지를 "v0.28.1rc1 dev 빌드"로 적고, 레시피는 0.29.0+와 GLM5Next 포함 이미지를 요구한다. 소스(v0.32.0)와 수업 서버 버전을 구분해 써야 한다.
- R-11 (`pdf-diff.md`): README는 응답 필드를 `reasoning` 또는 `reasoning_content`로 적는다. v0.32.0은 `reasoning` 하나다. 수업 서버가 어느 쪽인지는 실제 응답으로 확인한다.
- R-14 (`pdf-diff.md`): README는 `--tokenizer-mode`, Rust frontend, autotune 플래그를 적지 않는다. 레시피의 이 세 가지는 v0.32.0에서 그대로 쓸 수 없다(`glm5_next`와 `--disable-flashinfer-autotune` 플래그 모두 없음).
- 참고로 표현 주의 13개는 D-01, D-02, D-06, D-08, D-11, D-13, D-15, D-22, D-24, D-29, R-02, R-03, R-07이다.
- R-09는 뜻은 P5-14가 템플릿에서 정했지만 Pod의 template을 확인하지 못해 미확인으로 둔다. 각 행의 "저자에게 제안" 칸이 고칠 문구를 준다.

## 블로그 인용 규칙

블로그는 저자의 저작물이고 페이지에서 라이선스 표시를 찾지 못했다. 사용 허락을 받았다고 가정하지 않는다.

1. 절 제목과 URL로만 가리킨다. 예: 「Inside vLLM」의 "서버 초기화" 절, https://blog.liam.kim/posts/2026/10/Inside-vLLM/ .
2. 블로그의 문장, 예시 request, 풀이 과정(worked example), 그림 설명을 그대로 옮기거나 번역해 싣지 않는다. 사실은 코드 줄과 대장 행에서 우리 말로 다시 쓴다.
3. 블로그가 맞는지는 대장의 "블로그 절" 열과 상태로 판단한다. 블로그가 코드와 다른 행(위 `블로그·코드 차이`)은 블로그 서술을 근거로 쓰지 않는다.
4. 예시가 필요하면 Day07_new 자체의 숫자와 코드로 만든다. 블로그의 숫자(예: block 크기와 token 수 조합)를 재사용하지 않는다.
5. 노트북 첫 셀 또는 해당 절 끝에 출처 줄을 둔다: 제목, 저자, URL, "절 제목으로만 참조". 수강생에게 원문을 읽으라고 안내하는 것은 허용되지만 전문을 재배포하지 않는다.
6. 저자 또는 블로그 게시자에게 허락을 받으면 이 절을 바꾼다. 그 전까지 위 규칙이 기본이다.

## Pod 기동 제안

이 절은 **제안**이다. 아무것도 띄우지 않았고, 아래 명령은 실행해 본 적이 없다. 각 플래그 옆의 ID는 근거 행이다. `미확인`은 대장에 근거 행이 없다는 뜻이다.

### 결정 요약

- **Rust frontend는 쓰지 않는다.** 레시피 기본 명령의 `VLLM_USE_RUST_FRONTEND=1`과 `--tokenizer-mode glm5_next`는 v0.32.0에서 동작한다고 말할 수 없다(P1-49, R-14). 지원 PR #62424는 v0.32.0 커밋보다 늦다. 레시피도 "구 빌드에서는 Python frontend와 `--tokenizer-mode auto`"를 안내한다(`recipe-glm53.txt` Frontends 절, P6-35).
- **블로그 기반 설명과의 관계.** 블로그와 Part 1·6 대장의 Python 경로 행은 Python API server 기준이다. Python frontend를 쓰면 `tokenize`(P1-30)와 `detokenize`(P1-44)와 도구·reasoning 파서가 모두 API server 프로세스에서 돌아(P6-32) 노트북 설명이 그대로 Pod에 맞는다. Rust를 쓰면 이 부분이 Rust crate로 바뀌어(P1-48) 설명이 달라지고, 파서 오류 응답과 `glm45`/`glm47` 혼용은 확인되지 않았다(P6-04, P6-29, P6-30).
- **`/metrics`와 Rust.** Python frontend에서는 `/metrics`가 `vllm/entrypoints/serve/instrumentator/metrics.py:77`에서 `vllm:` 접두 지표를 낸다(P3-36). Rust frontend가 같은 경로와 같은 이름을 노출하는지는 대장에 근거가 없다(미확인). Part 3 노트북이 `/metrics` 이름에 의존하므로 Python frontend가 안전하다.
- **`--kv-cache-dtype`는 넣지 않는다.** 레시피는 Hopper가 이 모델의 FP8 KV cache를 지원하지 않고 BF16 KV로 돌려야 한다고 적고, `--kv-cache-dtype fp8` 예시는 GB200 예시다(`part4.md` "H200에서 GLM-5.3-Flash의 KV dtype" 절, P4-01, P4-02, D-24). 기본값 `auto`가 BF16 KV다. 이 H200 BF16 판단은 코드와 레시피 문장으로 추정한 것이고 시작 로그로 확인하지 않았다. 레시피와 코드는 부딪친다. 레시피는 Hopper가 FP8 KV를 지원하지 않는다고 적지만 `vllm/v1/attention/backends/mla/flashinfer_mla_sparse_sm90.py:3-9`는 SM90에서 일반 `fp8`(E4M3) KV를 커널 안 역양자화로 읽는다고 적고 허용 목록에도 `fp8`이 있다(P4 대장 H200 절). 어느 쪽이 맞는지는 이 자료로 가릴 수 없어, 수업은 `--kv-cache-dtype`을 넣지 않는 쪽을 유지한다. 코드가 막는다고 말하지도 않는다.
- **`--disable-flashinfer-autotune`는 넣지 않는다.** v0.32.0에 이 CLI 플래그가 없다(R-14).

### 제안 명령

4x H200 한 Pod, 이미지 `vllm/vllm-openai:v0.32.0`. 컨테이너 환경변수와 `vllm serve` 인자를 아래처럼 준다.

```bash
export NCCL_NVLS_ENABLE=0
export VLLM_ENGINE_READY_TIMEOUT_S=3600
export VLLM_USE_RUST_FRONTEND=0

vllm serve zai-org/GLM-5.3-Flash \
  --served-model-name GLM-5.3-Flash \
  --host 0.0.0.0 \
  --port 8000 \
  --tokenizer-mode auto \
  --tensor-parallel-size 4 \
  --speculative-config '{"method":"mtp","num_speculative_tokens":5}' \
  --tool-call-parser glm47 \
  --enable-auto-tool-choice \
  --reasoning-parser glm47 \
  --enable-prompt-tokens-details \
  --max-model-len 65536
```

### 환경변수

| 변수 | 값 | 이유 | 근거 ID |
|---|---|---|---|
| `NCCL_NVLS_ENABLE` | `0` | 강사가 2026-09-15에 측정한 메모: 없으면 H200x4에서 `ncclCommInitRank` 크래시 루프. 레시피·소스 어디에도 없음. 노트북에는 인용하지 말고 "강사 메모"로 쓴다 | R-05 (미확인) |
| `VLLM_ENGINE_READY_TIMEOUT_S` | `3600` | 기본 600초. 레시피가 3600을 주고 수업도 유지한다. 코드 읽기상 Python frontend(`VLLM_USE_RUST_FRONTEND=0`)에서는 이 값이 가중치 적재를 제한하지 않는다(client가 등록 메시지를 기다리는 한도이고 Rust frontend에서만 같은 메시지를 기다린다). 관찰하지 않았다 | P1-51, P1-19, P1-20 |
| `VLLM_USE_RUST_FRONTEND` | `0` | Rust frontend를 끄는 명시값. 기본이 0이라 생략해도 같지만 선택을 드러내려고 적는다 | P1-47 |

### 플래그와 근거

| 플래그 | 값 | 이유 | 근거 ID |
|---|---|---|---|
| 이미지 | `vllm/vllm-openai:v0.32.0` | 대장의 기준 버전과 같은 이미지. GLM5Next 지원이 이 이미지에 충분한지는 확인되지 않았다(아래 외삽) | P1-49, R-01 |
| 모델 | `zai-org/GLM-5.3-Flash` | 레시피 기본 FP8 체크포인트(가중치 약 306 GiB) | R-06 |
| `--served-model-name` | `GLM-5.3-Flash` | 강사 스크립트가 쓰는 이름. 레시피 예시는 `zai-org/GLM-5.3-Flash`라서 복사하면 404가 난다. `/v1/models`로 먼저 확인 | R-03 |
| `--host 0.0.0.0` | - | 플래그 자체는 대장에 근거 행이 없다 | 미확인 |
| `--port 8000` | - | 이 포트 지정은 대장에 근거 행이 없다. 소켓 bind 순서만 확인됨 | 미확인 (bind 순서 P1-12, P1-14) |
| `--tokenizer-mode auto` | - | `glm5_next`는 v0.32.0 목록에 없다. Python frontend 기본값 | P1-49, P6-35, R-14 |
| `--tensor-parallel-size 4` | - | 수업 서버는 4x H200 TP4. 레시피 기본은 8x H200 TP8이고 TP4는 GB200 예시와 H200 KV 오프로딩 검증에만 나온다 | R-07, R-02 |
| `--speculative-config` | `{"method":"mtp","num_speculative_tokens":5}` | 레시피 TP4 + MTP 구성의 JSON 그대로. MTP에서 `num_lookahead_tokens`는 K(=5) | R-02, P2-54 |
| `--tool-call-parser glm47` | - | 레시피 명령에 있고 레지스트리에 이름이 있다. `glm45`와 `glm47`은 Python에서 같은 클래스 | P6-03, P6-01 |
| `--enable-auto-tool-choice` | - | 도구 호출 필수 플래그. 파서 없이 단독으로 주면 시작 실패, 파서만 주면 파서가 None이 되어 `tools`를 실은 요청은 오류 응답(P6-09, P6-10). 없이 `tools`를 보내도 400 | P6-03, 실패 사례 C1 (`part6.md`) |
| `--reasoning-parser glm47` | - | 레시피 명령에 있고 응답에서 `reasoning` 필드를 분리한다. 생각이 항상 켜진 모델이라 없으면 구조화 출력 쪽 reasoner도 빈다 | P6-03, P6-23, P5-15 |
| `--enable-prompt-tokens-details` | - | 이 플래그가 있어야 `usage.prompt_tokens_details.cached_tokens`가 채워진다. Day07 README에는 기록이 없다 | P5-11 |
| `--max-model-len 65536` | - | **수업 선택값이고 대장에 근거 행이 없다.** 레시피 기본은 1,048,576이다. 시작 로그의 KV 용량을 읽는 Part 2 실습을 위해 줄이는 제안이며, 실제 값은 Pod 시작 로그를 보고 정한다 | 미확인 (R-07, D-02) |

**일부러 넣지 않은 것:** `--kv-cache-dtype`(위 결정 요약, P4-01), `--disable-flashinfer-autotune`(R-14), `--enable-prefix-caching`(기본 켜짐, `vllm/config/cache.py:141`, P5-03, D-01), `--gpu-memory-utilization`(기본 0.92, P3-07), `--max-num-seqs`와 `--max-num-batched-tokens`(기본값 사용, P3-02, 기본값 표 `part3.md`). 예산을 올려 문제를 가리지 않으려고 기본값으로 시작하고, Part 3에서 바꿔 본다.

### 외삽이라는 점 (읽기 전에 반드시)

레시피가 TP4 + MTP(5)를 **검증한 곳은 GB200 한 tray뿐**이다(`--kv-cache-dtype fp8`을 쓰는 FP8 + TP4 + MTP 예시). 4x H200의 TP4는 레시피에서 KV 오프로딩 검증 환경으로만 나오고, 그것도 MTP 없이 `--enforce-eager`, `--max-model-len 16384`, `--max-num-seqs 16`, `--max-num-batched-tokens 8192`를 같이 쓴 구성이다(R-07). 따라서 위 명령은 다음을 외삽한 것이다.

1. **H200에서 TP4 + MTP(5)** 가 기동하고 동작하는가: 레시피에 검증 기록이 없다. 대장에도 근거가 없다.
2. **BF16 KV로 이 조합이 메모리에 들어가는가**: 가중치 약 306 GiB(R-06)를 4장에 나누고 남는 용량으로 KV와 CUDA graph를 감당해야 한다. 계산은 시작 로그의 KV 용량으로 하고 이 문서는 숫자를 주지 않는다.
3. **v0.32.0 이미지가 GLM5Next를 충분히 지원하는가**: 모델 클래스는 registry에 있으나(R-01) 레시피는 "native GLM5Next 지원(#62424)을 포함한 이미지"를 요구하고 그 PR은 v0.32.0 이후다(P1-49). 또 FlashInfer 0.6.17 이상이 필요하다고 레시피가 적는다. 이 이미지로 기동이 안 되면 기존 강사 이미지(`vllm/vllm-openai:glm53-flash`, `Day07/README.md:75`)와 같은 태그를 쓰는 것이 대안이다. 그때는 Python frontend와 `--tokenizer-mode auto`를 유지하고, 서버가 보고하는 버전을 `/version`으로 기록한다(R-01).
4. **`--tool-call-parser glm47`과 `--reasoning-parser glm47`의 조합**: 레시피 조합이라 안전하나 Python에서의 실제 응답은 Pod에서 확인한 적이 없다(P6 대장의 "관찰했다고 말하지 말 것").
5. **기동 시간**: 강사 메모는 15~20분이다. `VLLM_ENGINE_READY_TIMEOUT_S`는 레시피를 따라 3600으로 줬다. 코드 읽기상 Python frontend에서는 이 값이 가중치 적재 시간을 제한하지 않는다(P1-51, 관찰하지 않음).

## Pod 점검 항목

Pod가 뜬 뒤에 순서대로 돌린다. `BASE`는 Pod 프록시 주소다(예: `https://<pod-id>-8000.proxy.runpod.net`). 이 서버는 `--api-key` 없이 띄운다는 가정이다. 키가 필요한 환경이면 헤더만 추가한다. 키 값은 로그나 결과 파일에 남기지 않는다. RunPod 프록시가 약 100초에서 연결을 끊는다는 Day07 메모(R-13)는 미확인이므로, 긴 응답은 스트리밍으로 받는다.

```bash
export BASE="https://<pod-id>-8000.proxy.runpod.net"
```

### 1. /version

```bash
curl -s "$BASE/version"
```

- 기대 증거: JSON 한 줄에 버전 문자열. `0.32.0`이면 대장의 기준 버전과 같다. 다르면(예: `0.28.1rc1`) 그 값을 노트북 첫 셀에 기록하고, 이후 모든 `reasoning` 필드와 파서 점검을 그 버전 기준으로 다시 본다(R-01, R-11).
- 대장에 `/version` 엔드포인트를 확인한 행은 없다(미확인). 404면 시작 로그의 첫 줄에서 버전을 읽는다.

### 2. /v1/models

```bash
curl -s "$BASE/v1/models"
```

- 기대 증거: `data[0].id`가 `GLM-5.3-Flash`. `zai-org/GLM-5.3-Flash`가 보이면 `--served-model-name`이 적용되지 않은 것이다(R-03). 이 id를 이후 요청의 `model`에 그대로 쓴다.

### 3. /metrics 이름

```bash
curl -s "$BASE/metrics" | grep -E '^(# TYPE )?vllm:(prefix_cache_queries|prefix_cache_hits|kv_cache_usage_perc|num_preemptions|num_requests_waiting|num_requests_running|time_to_first_token_seconds|inter_token_latency_seconds|request_time_per_output_token_seconds|e2e_request_latency_seconds|request_queue_time_seconds)' | sort -u
```

- 기대 증거: 위 이름이 `vllm:` 접두로 나온다(P3-36 및 `part3.md` 메트릭 목록). 모든 줄에 `model_name`, `engine` 라벨이 있다(P3-37).
- Counter가 `_total`을 붙여 노출되는 것은 prometheus_client 라이브러리를 호출해 확인했다(P3-38, 일치). 다만 vLLM 서버를 띄운 출력은 아니다. 위 grep은 접두어 일치라 두 형태 모두 잡는다. Pod에서는 실제로 찍힌 이름을 적어 노트북에 쓴다.
- `vllm:num_requests_swapped`는 나오지 않아야 한다(P3-39). 나오면 대장을 고친다.
- `/metrics`가 404거나 `vllm:` 이름이 아니면 Rust frontend로 떠 있는 것이다. 이 경우 이 문서의 Python 경로 설명이 맞지 않는다.

### 4. 더미 도구로 도구 호출

```bash
curl -s "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d '{
  "model": "GLM-5.3-Flash",
  "messages": [{"role": "user", "content": "서울의 현재 기온을 get_temperature 도구로 알아봐줘."}],
  "tools": [{"type": "function", "function": {
    "name": "get_temperature",
    "description": "도시의 현재 기온(섭씨)을 돌려준다.",
    "parameters": {"type": "object",
      "properties": {"city": {"type": "string"}},
      "required": ["city"]}}}],
  "tool_choice": "auto",
  "max_tokens": 2048
}'
```

- 기대 증거: `choices[0].message.tool_calls[0].function.name == "get_temperature"`이고 `arguments`가 JSON 문자열이다. `finish_reason`은 `tool_calls` 또는 `stop`(P6-33). 사고 과정은 `message.reasoning`에 있다(P5-15, P6-31). `reasoning_content`만 있으면 구버전 서버다(R-11).
- 실패 읽기: 400에 `"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set`이면 플래그가 빠진 것이다(실패 사례 C1, `part6.md`). 200인데 `tool_calls`가 비고 `content`에 `<tool_call>` 같은 마크업이 보이면 파서가 붙지 않은 것이다. `max_tokens`를 작게 줄이면 잘림 사례(C2)를 재현할 수 있다.
- 이 응답은 이 대장에서 "관찰한 사실"로 처음 올라온다. 결과를 `part6.md`에 옮기기 전에는 가설로 남는다.

### 5. cache_salt

`cached_tokens`는 `--enable-prompt-tokens-details`가 있어야 채워진다(P5-11). 프롬프트는 block 하나(기본 16 token, P2-04)보다 충분히 길게 만든다. 전부 적중해도 마지막 token은 다시 계산한다(P5-06). `cache_salt`는 128자 이하이고 `@ / \` 와 NUL을 쓰지 않는다(P5-10).

```bash
LONG=$(python3 -c "print('가나다라마바사 ' * 300)")
req() { curl -s "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d "{
  \"model\": \"GLM-5.3-Flash\",
  \"messages\": [{\"role\": \"user\", \"content\": \"$LONG 위 글자를 세지 말고 한 단어로 답해.\"}],
  \"cache_salt\": \"$1\", \"max_tokens\": 16 }" | python3 -c "import sys,json; u=json.load(sys.stdin)['usage']; print(u['prompt_tokens'], u['prompt_tokens_details'])"; }
req salt-A; req salt-A; req salt-B
```

- 기대 증거: 세 줄 모두 `prompt_tokens`가 같다. 두 번째 줄(`salt-A` 재요청)의 `cached_tokens`가 0보다 크고, 세 번째 줄(`salt-B`)은 `cached_tokens`가 0이거나 `None`이다. salt가 첫 block hash에만 섞여 다른 salt는 어떤 block도 공유하지 못한다(P5-09).
- 두 번째 줄도 0이면 바로 "캐시가 안 된다"고 결론내리지 않는다. 이 모델이 하이브리드(KDA + sparse MLA) 구조라 prefix caching이 이 모델에서 켜진 채로 뜨는지는 실행으로 확인하지 않았다(P5-03은 코드가 강제로 끄는 구성만 정한다). `/metrics`의 `vllm:prefix_cache_queries`와 `vllm:prefix_cache_hits` 차이와 시작 로그를 같이 본다.
- `prompt_tokens_details`가 `null`이면 서버에 `--enable-prompt-tokens-details`가 없는 것이다(P5-11).

### 6. 캐시 적중 token 수 (스트리밍)

```bash
curl -sN "$BASE/v1/chat/completions" -H 'Content-Type: application/json' -d '{
  "model": "GLM-5.3-Flash",
  "messages": [{"role": "user", "content": "한 문장으로 인사해줘."}],
  "stream": true,
  "stream_options": {"include_usage": true},
  "max_tokens": 64
}' | tail -n 4
```

- 기대 증거: 마지막 `data:` 청크(그 뒤에 `data: [DONE]`)에 `usage`가 있고, `usage.prompt_tokens_details.cached_tokens`가 보인다(P5-12). `stream_options.include_usage`가 없으면 usage 청크가 오지 않는다. langchain-openai는 `base_url`을 주면 `stream_usage`가 꺼지므로 `stream_usage=True`를 명시해야 한다(P5-17).

### 7. 스트리밍으로 TTFT와 ITL 재기

```bash
python3 - <<'PY'
import json, os, time, httpx
base = os.environ["BASE"]
body = {"model": "GLM-5.3-Flash",
        "messages": [{"role": "user", "content": "간단히 3문장으로 vLLM을 소개해줘."}],
        "stream": True, "stream_options": {"include_usage": True},
        "max_tokens": 512}
t0 = time.perf_counter(); stamps = []; first_text = None
with httpx.stream("POST", f"{base}/v1/chat/completions", json=body, timeout=95) as r:
    for line in r.iter_lines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        ch = json.loads(line[6:])
        if not ch.get("choices"):
            continue
        d = ch["choices"][0]["delta"]
        now = time.perf_counter(); stamps.append(now)
        if first_text is None and d.get("content"):
            first_text = now - t0
ttft = stamps[0] - t0
itl = [b - a for a, b in zip(stamps, stamps[1:])]
print("chunks", len(stamps), "TTFT_s", round(ttft, 3),
      "first_visible_s", None if first_text is None else round(first_text, 3))
print("ITL_ms mean/max", round(1000 * sum(itl) / len(itl), 1), round(1000 * max(itl), 1))
PY
```

- 기대 증거: `chunks`가 생성 token 수보다 적거나 같다. MTP(speculative decoding)이거나 `--stream-interval`이 1보다 크면 chunk 하나에 token이 여럿 담겨, ITL은 token 간격이 아니라 chunk 간격이다(P3-27). 클라이언트 TTFT는 첫 SSE chunk까지의 시간이고 서버 지표 `vllm:time_to_first_token_seconds`와 측정 기준이 다르다(P3-31, 서버는 API server 도착 기준). 생각이 항상 켜져 있어 첫 chunk가 `reasoning`일 수 있으므로 `first_visible_s`를 같이 낸다(D-36).
- 대조: 측정 전후로 `/metrics`의 `vllm:time_to_first_token_seconds_sum` 증가분을 `_count` 증가분으로 나눈 값과 클라이언트 값을 비교한다. 두 값이 다른 것이 정상이다(P3-26, P3-31).
- RunPod 프록시의 100초 제한은 미확인이다(R-13). `timeout=95`는 Day07 스크립트와 맞춘 값이고, 이 점검에서 연결이 끊기면 `max_tokens`를 줄여 다시 한다.

### 점검 결과 기록

점검이 끝나면 각 항목의 실제 출력(키 값 제외)을 해당 대장의 `미확인` 행 옆에 근거로 옮긴다. 옮기기 전에는 노트북이 "관찰했다"고 쓰지 않는다. 특히 닫아야 하는 항목은 P3-38(`_total` 이름은 라이브러리 호출로만 확인, 서버 출력은 아직), R-04(파서 플래그), R-05(`NCCL_NVLS_ENABLE`), P5-03(하이브리드 모델에서 prefix caching이 켜진 채로 뜨는지), `/version`과 H200 BF16 KV 판단이다.
