# Part 7 근거 대장: 최근 모델은 KV cache를 어떻게 통제하는가

Part 7 노트북이 인용할 사실만 모은 대장이다. 근거는 세 종류다. (1) 논문 원문: PDF를 직접 열어 절과 식을 확인했다. (2) 모델의 `config.json`: Hugging Face `raw/main`에서 2026-11-02에 받아 값을 읽었다. (3) vLLM v0.32.0(commit 5df63a7) 소스 루트 기준 `경로:줄`: 인용한 줄은 모두 열어 확인했다. 논문 문장은 옮기지 않고 모두 다시 풀어 썼으며, 따옴표 인용은 15단어 미만이다. 블로그(Inside vLLM)는 8절에서 이 모델들의 층과 KV 구성을 짧게 소개할 뿐 논문 수치와 설계 근거는 다루지 않으므로 이 대장의 근거로 쓰지 않고, `블로그 절` 열은 모두 `—`이다.

상태 정의(Part 2 대장과 같은 말): 일치(원문·config·코드에서 직접 확인했고 서로 어긋남 없음), 문서·코드 차이(문서가 코드보다 낡음), 논문·코드 차이(논문의 주장이나 배치가 코드와 다름. 코드를 따른다), 코드 전용(논문에 없고 코드나 config에서만 확인), 미확인(이 노드에서 근거를 못 봄 또는 재현 못 함).

표기 규칙: 주장 끝의 `(자체 보고)`는 모델 제작사가 자기 논문이나 문서에서 스스로 낸 수치이고 제3자가 재현하지 않았다는 뜻이다. `(자체 계산)`은 이 대장 작성자가 원문 숫자로 산수한 값이다. `근거 위치` 열은 논문의 절·표·그림 또는 config 필드 이름이다.

읽은 원문과 절 목록은 맨 아래 `읽은 원문 목록`에 있다.

## A. 세 곱셈 차원 (DeepSeek-V4.1-Flash §2.3)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-01 | 긴 문맥의 KV 저장과 attention 연산 비용은 서로 곱해지는 세 차원에서 줄일 수 있다고 논문은 정리한다. 첫째는 항목(entry) 크기다. GQA는 KV head 수를 줄이고 MLA는 head들이 작은 잠재 벡터 하나를 공유한다. | — | arXiv 2609.19969 §2.3 첫 단락 | — | 일치 |
| P7-02 | 둘째는 시퀀스 차원이다. token m개를 항목 하나로 압축한다(V4의 CSA와 HCA). 셋째는 층 차원이다. 어떤 층은 자기 캐시를 두지 않고 앞 층의 캐시와 선택 결과를 재사용하거나, 더 효율적인 층으로 통째로 바뀐다. | — | 2609.19969 §2.3 첫 단락 | — | 일치 |
| P7-03 | 층 차원의 선행 연구로 논문은 IndexCache(top-k 재사용), YOIO(sparse 경로를 한 번만 계산), HySparse(sparse 층이 dense 층의 KV를 재사용)를 든다. 인덱스만 재사용하면 main KV 저장은 줄지 않고, 세 차원을 모두 다루는 방법은 없었다는 것이 논문의 CSA2 동기다. | — | 2609.19969 §2.3 | — | 일치 |

## B. MLA (DeepSeek-V2 §2.1.2~2.1.4)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-04 | MLA는 은닉 상태 h_t를 하향 투영해 잠재 벡터 c_t^KV(차원 d_c)를 만들고, K와 V는 이것에서 상향 투영으로 복원한다. 추론 중 캐시에 두는 것은 c_t^KV뿐이라 KV cache는 토큰당 d_c * l개 원소(l은 층 수)다. 상향 투영 행렬은 Q와 출력 투영에 흡수되어 K, V를 실제로 만들 필요가 없다. | — | arXiv 2405.04434 §2.1.2, 식 (9)~(11) | `vllm/v1/kv_cache_interface.py:686-698`(MLA는 잠재 벡터 하나, 별도 V 없음) | 일치 |
| P7-05 | RoPE는 위치에 민감해서 K의 상향 투영 앞에 끼면 흡수가 깨지고, 그러면 prefix 토큰의 K를 매번 다시 계산해야 한다. 해결책이 decoupled RoPE다. RoPE를 싣는 별도 query(head별)와 공유 key(차원 d_h^R)를 두고 이 key는 캐시한다. 그래서 토큰당 캐시는 (d_c + d_h^R) * l개 원소다. | — | 2405.04434 §2.1.3, 식 (14)~(19) | — | 일치 |
| P7-06 | 원소 수 비교(표 1): MHA는 2 n_h d_h l, GQA는 2 n_g d_h l, MQA는 2 d_h l, MLA는 (d_c + d_h^R) l 로 대략 d_h l의 4.5배다. V2에서 d_c = 4 d_h, d_h^R = d_h / 2 이므로 GQA 그룹 2.25개와 같은 크기다. 단위는 저장 정밀도와 무관한 원소 개수다. | — | 2405.04434 §2.1.4, 표 1 | — | 일치 |
| P7-07 | V2의 실제 설정은 층 60, head 128개, head 차원 d_h 128, d_c 512, d_h^R 64다. 여기에 식을 대입하면 MHA 상당은 2*128*128*60 = 1,966,080 원소, MLA는 (512+64)*60 = 34,560 원소로 약 1.76%다 (자체 계산, 두 식은 P7-06). | — | 2405.04434 §3.1.2 | — | 일치 |
| P7-08 | V2가 DeepSeek 67B와 비교해 KV cache를 93.3% 줄였다는 요약 수치는 논문 초록과 서론에 있다 (자체 보고). 기준은 같은 크기의 MHA 모델이 아니라 DeepSeek 67B다. | — | 2405.04434 초록, §1 | — | 일치 |

## C. DSA (DeepSeek-V3.2-Exp)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-09 | lightning indexer는 질의 토큰 t와 앞선 토큰 s의 색인 점수 I_{t,s}를 계산한다. 식은 indexer head j에 대해 가중치 w * ReLU(q_j . k_s)를 더한 값이다. head 수가 적고 FP8로 구현할 수 있다고 논문이 설명한다. 같은 절의 식 (2)는 그 점수의 상위 k개에 해당하는 key-value 항목만 골라 attention을 한다는 식이다. | — | DeepSeek-V3.2-Exp 보고서 §1 Architecture, 식 (1), (2) | — | 일치 |
| P7-10 | 토큰 선택 단계는 색인 점수 상위 k개의 KV 항목만 읽어 attention을 계산한다. 희소 학습 단계에서 질의마다 2048개를 고른다. 논문은 핵심 attention 복잡도가 O(L^2)에서 O(Lk)로 줄고, indexer 자체는 여전히 O(L^2)이지만 MLA보다 훨씬 가볍다고 쓴다. | — | V3.2-Exp §1 식 (2), §2.1 Sparse Training Stage, §3 Inference Costs | `vllm/model_executor/models/deepseek_v2.py:697`(`topk_tokens = config.index_topk`) | 일치 |
| P7-11 | DSA는 MLA의 MQA 모드 위에 올린다. 잠재 벡터(MLA의 KV 항목) 하나를 질의 토큰의 모든 head가 공유한다. 이 논문은 KV 바이트 수를 따로 제시하지 않는다. DSA가 줄이는 것은 읽는 항목 수와 연산이지 캐시 크기가 아니다. | — | V3.2-Exp §1 "Instantiate DSA Under MLA", 그림 1 | — | 일치 |
| P7-12 | indexer가 쓰는 K도 캐시가 필요하다. vLLM은 MLA main KV와 별도로 indexer용 캐시 층을 `MLAAttentionSpec`(head 1개, `tokens_per_state` 기본값 1)로 등록한다. | — | — | `vllm/model_executor/models/deepseek_v2.py:638`(클래스), `:659`(spec) | 코드 전용 |

## D. DeepSeek-V4 (CSA, HCA, SWA, 캐시 배치)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-13 | CSA는 m개 token의 KV를 항목 하나로 압축한 뒤 DSA를 적용해 질의마다 압축 항목 k개만 읽는다. Flash는 m = 4, 색인 질의 head 64개, 색인 head 차원 128, top-k 512다(Pro는 top-k 1024). 압축 항목 하나를 만들 때 이웃과 겹치는 2m개 항목을 쓴다. | — | arXiv 2606.19348 §2.3, §2.3.1, §4.2.1 | `vllm/models/deepseek_v4/attention.py:865-880`(`tokens_per_state=compress_ratio`) | 일치 |
| P7-14 | HCA는 훨씬 큰 압축률 m' = 128로 token을 압축하고 겹침 압축과 sparse 선택을 쓰지 않는다. Flash 설정의 층 배치는 첫 두 층이 순수 SWA이고 이후 CSA와 HCA가 번갈아 온다. config의 `compress_ratios`는 4와 128이 교대로 나오고 앞의 두 값과 끝 값이 0이다(44개 원소: 4가 21개, 128이 20개, 0이 3개). | — | 2606.19348 §2.3.2, §4.2.1; `DeepSeek-V4-Flash/config.json`의 `compress_ratios` | `vllm/models/deepseek_v4/attention.py:865-880`(HCA도 같은 spec에 ratio만 다름) | 일치 |
| P7-15 | CSA와 HCA에는 SWA 보조 가지가 붙는다. 압축 블록 안의 같은 블록 token은 인과성 때문에 볼 수 없으므로, 질의마다 최근 n_win개 token의 압축하지 않은 KV를 따로 만들어 함께 쓴다. Flash와 Pro 모두 n_win = 128이고 config의 `sliding_window`도 128이다. | — | 2606.19348 §2.3.3 "Additional Branch of Sliding Window Attention", §4.2.1; Flash config의 `sliding_window` | `vllm/v1/attention/backends/mla/sparse_swa.py:116-130`(SWA 캐시는 `SlidingWindowMLASpec`) | 일치 |
| P7-16 | KV 항목 저장은 혼합 정밀도다. RoPE를 적용하는 마지막 64차원은 BF16, 나머지는 FP8이어서 순수 BF16보다 크기가 거의 절반이 된다. indexer 안의 attention 연산은 FP4다. 논문은 V4 계열 KV cache가 1M 문맥에서 BF16 GQA8(head 차원 128) 기준의 약 2%라고 쓴다 (자체 보고, 기준선은 논문이 정한 것). | — | 2606.19348 §2.3.3 "Partial Rotary Positional Embedding", §2.3.4 | `vllm/models/deepseek_v4/attention.py:876`(주석 448B NoPE + 128B RoPE + 8B scale = 584B), `:878`(`state_content_bytes=584`) | 일치 |
| P7-17 | 캐시 배치(그림 6)는 둘로 나뉜다. 일반 KV cache는 CSA와 HCA의 압축 KV를 담고 요청마다 여러 블록을 쓴다. 상태 캐시(state cache)는 SWA의 최근 n_win개 항목과, 아직 압축할 준비가 안 된 꼬리 token의 압축 전 상태를 담고, 요청마다 고정 크기 블록 하나를 받는다. 논문은 SWA와 꼬리를 상태 공간 모델의 상태처럼 취급한다고 설명한다. | — | 2606.19348 §3.5.1, 그림 6 | `vllm/models/deepseek_v4/compressor.py:179-193`(꼬리 상태 캐시, `SlidingWindowMLASpec`) | 일치 |
| P7-18 | 한 블록이 담는 원래 token 수는 lcm(m, m')의 배수여야 한다. 일반 블록 하나는 lcm(m, m')개의 원래 token을 덮고 CSA 압축 항목 k1 = lcm/m개와 HCA 압축 항목 k2 = lcm/m'개를 만든다. Flash 값으로는 lcm(4, 128) = 128이므로 k1 = 32, k2 = 1이다 (자체 계산). 다만 vLLM v0.32.0의 V4 sparse MLA 백엔드가 선언하는 kernel block은 256이어서(`vllm/models/deepseek_v4/sparse_mla.py:60`, CPU에서 실제 클래스를 호출해 확인) 실제 block은 CSA 압축 항목 64개, HCA 압축 항목 2개를 담고 lcm 128과 같지 않다. 이유는 PagedAttention의 두 가정(층마다 같은 캐시 정책, kernel이 요구하는 고정 정렬)이 깨지기 때문이라고 논문이 설명한다. | — | 2606.19348 §3.5.1 그림 6 설명, "Sparse Attention Kernel Co-Design" | `vllm/models/deepseek_v4/attention.py:865-880`(블록 크기와 정렬 `alignment`), `vllm/models/deepseek_v41/attention.py:1234-1238`(`math.lcm(512, page_alignment)`는 kernel stride 정렬이며 token 수의 lcm과는 별개) | 일치 |
| P7-19 | 디스크 저장(§3.5.2): CSA와 HCA의 압축 KV는 전부 저장하고, 마지막 완전한 압축 블록까지 읽어 재사용한다. 꼬리의 미완성 블록은 다시 계산한다. SWA KV는 모든 층에 있고 압축이 안 되어 압축 KV보다 약 8배 크다. SWA에는 세 전략이 있다. Full SWA Caching(전부 저장, 쓰기 위주 접근이 되어 SSD에 비효율), Periodic Checkpointing(p token마다 마지막 n_win개 저장), Zero SWA Caching(저장 안 함, 적중 시 n_win * L개 token을 다시 계산). | — | 2606.19348 §3.5.2 | — | 일치 |

## E. DeepSeek-V4.1-Flash (arXiv 2609.19969)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-20 | CED(Causal Encoder-Decoder): 40층을 인코더 20층과 디코더 20층으로 나누고, 디코더의 global KV는 자기 은닉 상태가 아니라 인코더 마지막 층(L/2번째) 은닉 상태에서 층별 투영 가중치로 만든다. 그래서 prefill에서는 앞 절반 층만 돌려도 위쪽 층의 global KV를 얻는다. 길이 N이 n_win보다 훨씬 길면 prefill 복잡도가 O(NL)에서 약 O(NL/2)가 된다. SWA KV는 모든 층에서 층별로 계산한다. 활성 파라미터는 prefill 8B, decode 16B다 (자체 보고). | — | 2609.19969 §2.1, §2.2, 식 (1) | `vllm/models/deepseek_v41/nvidia/model.py:805`(`cut = max(config.kv_source_layer_ids)`로 prefill을 자르는 지점 계산) | 일치 |
| P7-21 | CSA2는 층마다 세 모드 중 하나로 정적으로 배정된다. Full은 자기 main KV와 indexer Q를 만들고 indexer K를 main KV에서 투영해 새 top-k를 만든다. Reindex는 앞 Full 층의 main KV와 indexer K를 재사용하되 자기 indexer Q로 다시 점수를 매겨 새 top-k를 뽑는다. Reuse는 main KV와 top-k 인덱스를 모두 재사용하고 indexer를 돌리지 않는다. 세 모드 모두 자기 query와 SWA KV는 자기 층에서 만든다. | — | 2609.19969 §2.3.1, 그림 4 | `vllm/models/deepseek_v41/attention.py:307-340`(`kv_source_layer_ids`와 `index_source_layer_ids`로 소유 층 결정), `:1138-1150`(소스 층만 압축 KV 캐시 spec) | 일치 |
| P7-22 | V4.1은 CSA와 HCA 혼합이 아니라 순수 CSA2다. 압축률 1(압축 없음)도 특수한 경우로 포함한다. CSA와 달리 압축 때 겹침과 절대 위치 임베딩을 없앴고, indexer K를 hidden에서 따로 압축하지 않고 main KV를 투영해 얻는다. | — | 2609.19969 §1, §2.3 | — | 일치 |
| P7-23 | config의 `compress_ratios`는 43개 값이다(0이 5개, 2가 18개, 1이 20개). 인덱스 0, 1은 SWA만, 2번부터 19번까지는 비율 2(인코더), 20번부터 39번까지는 비율 1(디코더), 뒤 3개는 MTP 쪽 0이다. `kv_source_layer_ids`는 [2, 8, 14, 20], `index_source_layer_ids`는 [2, 8, 14, 20, 24, 28, 32, 36]이다. 이 둘이 Full과 Reindex 층에 대응한다는 해석은 논문 그림 3과 코드 주석에서 나온 추정이다. | — | `DeepSeek-V4.1-Flash/config.json`의 `compress_ratios`, `kv_source_layer_ids`, `index_source_layer_ids`; 2609.19969 그림 3 | `vllm/models/deepseek_v41/attention.py:323-333` | 일치 |
| P7-24 | Hierarchical Sparse Indexer(디코더에서만, post-training에서 도입): 디코더의 첫 Full 층이 전체 문맥을 훑어 top-k를 만들고, 블록별 최대 점수로 블록을 골라 후보 풀을 만든다. 예시로 8개 위치 블록 2,048개를 고르면 후보가 16,384개다. 이후 Reindex 층은 이 풀 안에서만 점수를 매겨 자기 top-k를 고르므로, 풀 크기를 고정하면 층당 점수 계산 수가 문맥 길이와 무관해진다. 첫 Full 층의 전체 훑기는 남는다. config 필드는 `candidate_topk_blocks` 2048, `candidate_block_size` 8, `index_topk` 512다. | — | 2609.19969 §2.3.2, 그림 5; V4.1 config 같은 이름 필드 | — | 일치 |
| P7-25 | FP4 main KV cache: post-training에서 QAT로 main KV를 FP4(E2M1, 16채널마다 E4M3 scale 하나, 2차 전역 scale 없음)로 저장한다. RoPE 적용 뒤에 양자화하고, RoPE 부분과 비RoPE 부분이 같은 형식을 쓴다. SWA KV는 양자화에 민감해 FP8로 남긴다. V4의 FP8 main KV보다 저장 공간이 거의 반이다 (자체 보고). attention 전에 역양자화하므로 그 형식의 행렬곱을 하드웨어가 직접 지원하지 않아도 쓸 수 있다고 논문이 설명한다. | — | 2609.19969 §2.4.4 | `vllm/models/deepseek_v41/attention.py:513-518`(`nvfp4_ds_mla` 압축 record는 288B, SWA record는 SM100에서 528B, 그 외 584B), `:1160-1162`(그 값을 spec에 전달), `:520-527`(`nvfp4_ds_mla`는 SM100 전용 오류 처리) | 일치 |
| P7-26 | Single-Pass mHC는 메모리와 닿는 부분만 인용한다. 잔차 스트림 n개를 쓰는 mHC의 활성 메모리 입출력은 기존 구현이 (4n+4)d, 하한이 (2n+2)d다. 입력 섞임 계수를 한 블록 늦춰 쓰면 배포용 단일 kernel로 하한에 도달해 활성 메모리 트래픽이 절반이 된다 (자체 보고). 이것은 활성 값의 트래픽이고 KV cache 크기와는 무관하다. | — | 2609.19969 §2.4.1, 식 (6) | — | 일치 |
| P7-27 | 영속 KV cache(SSD와 host 메모리)가 V4의 약 1/8이 되는 이유는 두 곱이다. SWA KV를 영속 캐시에서 빼서 크기가 거의 절반이 되고, 남은 global KV가 V4의 1/4이 된다. SWA KV는 host DRAM의 10%로 만든 분산 메모리 풀에 몇 분 단위 TTL로 두고, global KV는 영속 캐시에 최소 72시간 보장한다 (자체 보고). | — | 2609.19969 초록, §1, §3.2.1 | — | 일치 |
| P7-28 | SWA Bounded Replay: SWA 의존이 층마다 쌓이므로 정확한 복원은 L * n_win개 token을 다시 돌려야 한다. 이 방법은 최근 n_win개만 다시 돌려 근사하고 SWA를 재생 구간으로 자른다. Encoder 쪽은 영속 캐시에서 SWA를 빼도 되게 하고, Decoder 쪽은 prefill마다 마지막 n_win개 token만 디코더에 통과시켜 디코더 SWA KV를 만든다. 품질 영향은 미미하다고 논문이 주장한다 (자체 보고, 근사라서 수학적 동일성은 없다고 논문도 인정). | — | 2609.19969 §2.2, §3.2.2, §6 한계 | `vllm/v1/kv_cache_interface.py:949-974`(`SlidingWindowMLASpec.bounded_replay`, `prefix_cacheable`은 replay가 켜지면 False), `vllm/models/deepseek_v41/attention.py:529-567`(model runner V2가 없으면 끔), `vllm/config/cache.py:250`(`swa_bounded_replay` 기본 True) | 일치 |
| P7-29 | 그림 1(b)의 토큰당 global KV 크기(바이트): DeepSeek-V1 389,120, V3.2 48,068, V4-Flash 3,514, V4.1-Flash 890. 그림이 적은 감소 배율은 V1에서 V3.2까지 8.1배, V3.2에서 V4까지 13.7배, V4에서 V4.1까지 3.9배다. 본문은 V4.1이 V4-Flash 대비 약 4배, V1 대비 437배라고 쓴다 (자체 보고). 890바이트와 약 1/4은 초록 텍스트에도 있다. 나머지 바이트 값과 감소 배율은 텍스트 층에 없고 그림 이미지에서 읽었다. 자체 계산: 389,120 / 890 = 437.2, 3,514 / 890 = 3.95. | — | 2609.19969 그림 1(b)와 설명, 초록 | — | 일치 |
| P7-30 | 그림 2: 토큰 하나를 만드는 decode FLOPs를 문맥 길이별로 비교한다. BF16, FP8, FP4 연산에 가중치 1, 0.5, 0.25를 곱해 정밀도를 반영한다. 본문은 문맥이 4K에서 1M으로 256배 늘 때 V4.1의 decode FLOPs는 1/4만 늘고 V4-Flash의 증가보다 훨씬 작다고 쓴다 (자체 보고). 그래프의 개별 값은 읽어 적지 않는다. | — | 2609.19969 §1, 그림 2 | — | 일치 |
| P7-31 | V4.1 config의 KV 관련 값: `num_key_value_heads` 1, `head_dim` 512, `qk_rope_head_dim` 64, `sliding_window` 128, `index_n_heads` 32, `index_head_dim` 128, `index_topk` 512, `max_position_embeddings` 1,048,576, `num_hidden_layers` 40. V4-Flash는 `index_n_heads` 64, `num_hidden_layers` 43이다. | — | 두 모델의 `config.json`(`text_config` 안, V4-Flash는 최상위) | `vllm/models/deepseek_v41/attention.py:1138-1160` | 일치 |

## F. GLM-5 (arXiv 2602.15763)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-32 | GLM-5 논문은 MLA가 576차원 잠재 KV cache를 쓰면 Muon으로 학습할 때 GQA-8(2048차원 KV)의 품질을 못 따라간다고 쓴다. 해법으로 Muon Split(up-projection 행렬을 head별로 쪼개 직교화)을 쓰면 MLA가 GQA-8과 비슷해진다(표 1). 여기서 576은 512 + 64로 V2의 d_c + d_h^R과 같은 합이다. | — | arXiv 2602.15763 §2.1 "Multi-latent Attention", 표 1 | — | 일치 |
| P7-33 | MLA-256: MLA는 decode에서 576차원 내적을 하므로 GQA의 128차원보다 연산이 크다. 그래서 MHA 방식으로 계산하는 학습과 prefill 구간의 head 차원을 192에서 256으로 키우고 head 수를 1/3 줄인다. 학습 연산과 파라미터 수는 같고 decode 연산은 줄며, 표 1에서 Muon Split 적용 MLA와 같은 수준이다. 논문은 이 변경이 KV cache 크기를 바꾼다고 쓰지 않는다. | — | 2602.15763 §2.1, 표 1 | — | 일치 |
| P7-34 | GLM-5는 DSA를 도입한다. dense warm-up 1,000 step과 sparse 적응 200억 token으로 MLA 기반 모델과 장문 성능을 맞췄다(표 3). 논문은 긴 시퀀스에서 attention 연산이 대략 1.5~2배 준다고 쓴다 (자체 보고). KV cache 크기 감소에 대한 수치는 없다. | — | 2602.15763 §2.1.1, 표 3 | — | 일치 |
| P7-35 | 효율 attention 대안 비교(GLM-9B, 64K 연속 학습, 전체의 절반을 효율 층으로): SWA를 단순 교대로 넣으면 RULER 128K가 75.28에서 44.93으로 떨어지고, 탐색으로 고른 SWA 패턴은 69.59, GDN은 64.00, SimpleGDN은 67.03이다(표 5). 논문은 DSA가 "lossless by construction"이라는 이유로 GLM-5가 이 대안들 대신 DSA를 쓴다고 쓴다. GLM-4.7-Flash에 DSA를 붙인 소규모 실험은 RULER 128K가 79.21에서 78.86이다(표 6) (자체 보고). | — | 2602.15763 §2.1.2, 표 4~6 | — | 일치 |
| P7-36 | 섹션 5(중국 칩 적응): Prefix Cache는 KV 저장 공간을 시스템 RAM까지 넓혀 재사용하게 하는 기능이고 RadixCache는 prefix 공유 기능이다. Lightning Indexer(점수, ReLU, TopK를 한 kernel로)와 Sparse Flash Attention(KV에서 TopK 선택과 sparse attention을 병렬로)을 fused kernel로 만들었다. 장문 시퀀스 배포 비용을 50% 줄인다는 문장은 KV 크기가 아니라 한 노드 대 두 GPU 클러스터 비교이므로 KV 근거로 쓰지 않는다 (자체 보고). | — | 2602.15763 §5 | — | 일치 |
| P7-37 | RL rollout 서빙(§3.6.2): MLA를 DP-attention으로 서빙하면 rank 사이에 KV를 복사하지 않아도 되고, 큐 없이 요청을 받으려면 KV 용량이 많이 필요해 EP64와 DP64를 8노드에 얹은 분산 KV 배치를 쓴다. | — | 2602.15763 §3.6.2 | — | 일치 |

## G. GLM-5.2 IndexShare

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-38 | GLM-5.2는 IndexShare를 쓴다. 4개 층마다 가벼운 indexer 하나를 공유하고, indexer는 4개 층 중 첫 층에 두며 그 top-k를 4개 층이 쓴다. indexer의 내적과 top-k 연산이 줄어서 1M 문맥에서 토큰당 FLOPs가 2.9배 준다고 Z.ai가 쓴다 (자체 보고). 이 글에는 wall-clock 속도 향상 수치가 없다. | — | Hugging Face 블로그 `zai-org/glm-52-blog`(Z.ai, 제목 GLM-5.2 소개 글)의 Improved Architecture 요약과 "Architecture for 1M Context" 절 | `vllm/model_executor/models/deepseek_v2.py:1140-1156`(`index_topk_freq`, `index_topk_pattern`의 "S" 층이 top-k 계산을 건너뜀), `:1168`(건너뛴 층은 `Indexer`를 만들지 않으므로 그 층의 indexer K 저장도 없음. MTP 층은 항상 만듦) | 일치 |
| P7-39 | 같은 글은 GLM-5.2가 토큰당 FLOPs는 줄이지만 토큰당 KV cache 크기는 그에 비례해 줄이지 못한다고 인정한다. 그래서 더 긴 문맥과 높은 동시성은 KV 용량, 장문 kernel 비용, CPU 쪽 부담에 걸린다고 설명한다. KV 감소량은 수치로 주지 않는다. IndexShare는 연산 최적화이고 캐시 크기 최적화가 아니라는 근거다. | — | `glm-52-blog`의 추론 엔진 과제를 설명하는 단락 | — | 일치 |
| P7-40 | 기준 모델 GLM-5.3의 config는 `num_hidden_layers` 78, `kv_lora_rank` 512, `qk_rope_head_dim` 64, `qk_nope_head_dim` 192, `v_head_dim` 256이고 `index_topk_freq` 4, `index_skip_topk_offset` 3이고 `indexer_types`는 앞 3개가 full이고 그 뒤로 shared 3개와 full 1개가 반복된다(78개 중 full 21개, shared 57개). 같은 IndexShare 구조가 GLM-5.3 쪽에도 있음을 config로 확인했다. | — | `zai-org/GLM-5.3/config.json`의 `num_hidden_layers`, `kv_lora_rank`, `qk_rope_head_dim`, `index_topk_freq`, `index_skip_topk_offset`, `indexer_types` | `vllm/model_executor/models/deepseek_v2.py:1140-1156` | 일치 |

## H. GLM-5.3-Flash

값은 모두 `https://huggingface.co/zai-org/GLM-5.3-Flash/raw/main/config.json`의 `text_config`에서 읽었다. 이 값들이 Part 2 대장(`part2.md`)이 미확인으로 두었던 숫자다.

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-41 | 층 구성: `num_hidden_layers` 45, `layer_types`는 `linear_attention` 34개와 `deepseek_sparse_attention` 11개다. `linear_attn_config.full_attn_layers`는 [3, 7, 11, ..., 43](4층마다 하나, 11개)이고 `kda_layers`는 나머지 34개(마지막 44층 포함)다. 앞 3층은 dense MLP(`first_k_dense_replace` 3)다. | — | Flash config의 `layer_types`, `linear_attn_config`, `num_hidden_layers` | `vllm/models/glm5next/common/model.py:130-136`, `:370-371`(`layer_types[layer_idx] == "linear_attention"`로 분기) | 일치 |
| P7-42 | MLA 쪽 값: `kv_lora_rank` 512, `qk_rope_head_dim` 0, `qk_nope_head_dim` 256, `v_head_dim` 256, `num_attention_heads` 64, `mla_use_nope` true, `q_lora_rank` 1536. RoPE 차원이 0이므로 잠재 항목 하나가 512 원소다. V2나 GLM-5.3의 d_c + d_h^R = 576과 다르다. | — | Flash config의 같은 이름 필드 | `vllm/v1/attention/backends/mla/flashmla_sparse.py:220-221`(주석이 GLM5Next NoPE의 `kv_lora_rank == 512`를 적음), `vllm/models/glm5next/common/attention.py:554-565` | 일치 |
| P7-43 | indexer 값: `index_kpool` 4, `index_kpool_compress` true, `index_kpool_always_select_tail` true, `index_topk` 2048, `index_n_heads` 32, `index_head_dim` 128, `indexer_types`는 45개 모두 full(공유 층 없음), `index_share_for_mtp_iteration` true. | — | Flash config의 같은 이름 필드 | `vllm/models/glm5next/common/attention.py:79-122`, `:260-266`(`tokens_per_state = index_kpool`) | 일치 |
| P7-44 | 선형 attention 값: `linear_attn_config`의 `num_heads` 64, `head_dim` 128, `short_conv_kernel_size` 4, `gate_lower_bound` -5.0이다. 이 구조가 Kimi Linear의 KDA와 같은 계열이라는 것은 vLLM 소스가 클래스를 `kda.py`에 두고 `MambaSpec`으로 등록한다는 사실로 알 수 있다. Z.ai 문서가 KDA라는 이름을 직접 쓰는지는 이 노드에서 확인하지 못했다. | — | Flash config의 `linear_attn_config` | `vllm/models/glm5next/common/kda.py:163-176`, `vllm/model_executor/layers/mamba/abstract.py:65-84` | 일치 |
| P7-45 | transformers 문서가 보여 주는 `index_kpool` 기본값 16은 이 체크포인트의 값이 아니다. 이 체크포인트의 config는 4다(P7-43). 수업에서 숫자를 쓸 때는 문서 기본값이 아니라 config 값을 쓴다. 문서 쪽 16은 작업 지시서가 알려 준 값이고 이 노드는 해당 문서 페이지를 직접 열지 않았지만, 검토자가 `huggingface.co/docs/transformers/main/en/model_doc/glm5_next`에서 기본값 16을 확인했다. | — | Flash config의 `index_kpool` | — | 일치 |
| P7-46 | Z.ai는 GLM-5.3-Flash가 GLM-5.3 대비 attention 연산을 3.01배, KV cache를 4.44배 줄인다고 쓴다 (자체 보고). 본문에서는 같은 쌍이 3.0배와 4.4배로 반올림된다. 측정 방법은 head당 층당 attention 연산과 층당 평균 KV cache 크기(BF16)이고, 비교 대상은 GLM-5.3, DeepSeek-V4-Flash, Kimi-K3다. 문서는 KV 크기가 Kimi-K3와 DeepSeek-V4-Flash보다 아직 약간 크다고 스스로 쓴다. 측정한 문맥 길이, 하드웨어, batch는 문서에 없다. | — | `https://docs.z.ai/guides/vlm/glm-5.3-flash`의 Model Overview와 Architecture 절 | — | 일치 |
| P7-47 | 위 4.44배를 config로 재현하려는 시도: 층당 평균 잠재 KV 원소를 GLM-5.3은 576(512+64, 78층 모두 MLA)로, Flash는 11개 sparse 층의 512를 45층에 나눈 125.2로 보면 비는 약 4.6이다 (자체 계산). 4.44와 정확히 같지 않다. indexer 캐시와 선형 층 state를 어떻게 셌는지 문서에 없어서 재현은 되지 않았다. 4.44를 수업에서 쓰려면 반드시 자체 보고로 표시하고 산식은 보이지 않는다. | — | 위 두 config와 P7-46의 방법 설명 | — | 미확인 |
| P7-48 | GLM-5.3-Flash 전용 기술 보고서(논문)는 찾지 못했다. `z.ai/blog/glm-5.3-flash` 페이지는 가져왔을 때 본문이 비어 있었다. 웹 검색에서 모델 카드가 인용하는 논문은 GLM-5 보고서(arXiv 2602.15763)뿐이었다. 따라서 이 모델의 KV 구조 근거는 config(P7-41~44)와 docs.z.ai 문서(P7-46), vLLM 소스(Part 2 대장)로 한정한다. | — | 검색 결과, `z.ai/blog/glm-5.3-flash` 응답 | — | 미확인 |

## I. Kimi Linear와 Kimi K3

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-49 | KDA(Kimi Delta Attention)는 델타 규칙 재귀에 채널별 망각 게이트를 붙인 선형 attention이다. 토큰이 늘어도 커지는 KV 대신 head마다 d_k x d_v 크기의 재귀 상태 S_t 하나를 유지한다. 문맥 길이와 무관하게 크기가 고정이다. | — | arXiv 2510.26692 §3(KDA 정의), §6.3 Complexity Analysis("fixed-sized state" 문장), Kimi K3 보고서 §5.1 | `vllm/v1/kv_cache_interface.py:1035-1045`(`MambaSpec`), `vllm/models/kimi_k3/nvidia/kda.py:829-837` | 일치 |
| P7-50 | Kimi Linear는 KDA 층과 전역 attention(MLA) 층을 3:1로 균일하게 섞는다. 이 혼합이 긴 시퀀스 생성에서 메모리와 KV cache 사용을 최대 75% 줄인다고 쓴다 (자체 보고, 48B 규모). 같은 학습 조건에서 전체 MLA를 앞선다고도 주장한다. | — | 2510.26692 초록, §1 | — | 일치 |
| P7-51 | drop-in 주장은 두 겹이다. 초록은 Kimi Linear가 전체 attention 구조를 대체할 수 있다고 쓴다. §1은 공개한 KDA kernel이 기존 전체 attention 파이프라인과 호환되어 캐시와 스케줄링 인터페이스를 고치지 않아도 된다고 쓴다. 이 두 번째 문장은 논문의 주장이고, vLLM에서는 오히려 `MambaSpec`과 hybrid KV cache manager를 새로 거쳐야 했다(P7-62, Part 2의 P2-61, P2-62). 수업에서 인터페이스 변경이 없었다고 가르치지 않는다. | — | 2510.26692 초록, §1 | `vllm/v1/kv_cache_interface.py:1035` | 논문·코드 차이 |
| P7-52 | Kimi K3는 3개 KDA 층과 1개 Gated MLA 층을 한 블록으로 반복하고 맨 끝에 Gated MLA 층을 하나 더 둔다(3:1). MLA 층은 NoPE(위치 인코딩 없음)다. config는 `num_hidden_layers` 93, KDA 69개와 전역 attention 24개, `kv_lora_rank` 512, `qk_rope_head_dim` 64, `linear_attn_config.head_dim` 128이다. config에 RoPE 차원이 64로 남아 있지만 보고서는 MLA에 위치 인코딩을 적용하지 않는다고 하므로, 이 값이 실제로 쓰이는지는 확인하지 못했다. | — | Kimi K3 보고서(`MoonshotAI/Kimi-K3`의 `k3_tech_report.pdf`) §2.1, §2.1.2; `moonshotai/Kimi-K3/config.json`의 같은 이름 필드 | `vllm/models/kimi_k3/nvidia/mla.py:417-431`(MLA 층 `MLAAttentionSpec`, `fp8_ds_mla`는 656B) | 일치 |
| P7-53 | K3 서빙의 prefix cache(§5.4.1): KDA 재귀 상태를 MLA KV와 같은 paged 블록 풀에 넣고 페이지 바이트 크기를 통일한다. 블록 해시 방식은 모든 층이 같은 블록 크기를 써야 하는데, KDA 상태는 큰 스냅샷이라 드문 경계에서만 저장할 수 있어 공유 블록이 1024~6144 token으로 강제된다. 그래서 물리 블록(예: 6144 token)과 해시 블록(예: 512 token)을 분리하고 KDA 체크포인트는 해시 경계 일부에서만 저장한다. 적중 경계는 둘 다 만족하는 가장 긴 지점이다. | — | Kimi K3 보고서 §5.4.1과 그림 12 | `vllm/v1/kv_cache_interface.py:1035-1045`(`MambaSpec`의 `tokens_per_state`), `vllm/models/kimi_k3/nvidia/kda.py:829-837`(prefill 체크포인트 정렬 필드를 `MambaSpec`에 덧붙임) | 일치 |
| P7-54 | K3 RL 롤아웃의 외부 KV cache 풀(§5.3.1): 1M 문맥에서 prefix 미스는 비용이 크므로, 활성 decode 블록은 GPU에 두고 GPU에서 밀려나는 재사용 가능한 idle prefix만 CPU DRAM의 외부 풀에 write-back 방식으로 쓴다. 다음 재사용 전에 다시 가져오고, KDA 상태도 해당 MLA 블록과 함께 내리고 올려 수명을 맞춘다. | — | Kimi K3 보고서 §5.3.1 "External KV cache pool" | — | 일치 |

## J. IndexCache (arXiv 2603.12201)

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-55 | IndexCache는 DSA 층을 F(Full)와 S(Shared)로 나눈다. F 층은 indexer를 유지해 새 top-k를 계산하고, S 층은 indexer가 없고 앞쪽 가장 가까운 F 층의 top-k 인덱스를 재사용한다. 첫 층은 항상 F다. | — | 2603.12201 §3 | `vllm/model_executor/models/deepseek_v2.py:1140-1156`(주석에 이 논문의 arXiv 번호가 있음, `"S"` 층은 top-k 건너뜀) | 일치 |
| P7-56 | 재사용 비율: 탐욕 탐색으로 고른 패턴은 indexer의 1/4만 남겨 indexer 연산의 75%를 없앤다. 실험한 유지 비율은 1/2, 1/4, 1/8이다(훈련 없는 방식은 세 값, 훈련 인지 방식은 1/2과 1/4). 품질 저하는 무시할 만하다고 논문이 주장한다 (자체 보고). | — | 2603.12201 초록, §4.3, §4.4 | — | 일치 |
| P7-57 | 속도 향상: 30B DSA 모델, H100과 SGLang에서 문맥 200K일 때 prefill이 19.5초에서 10.7초(1.82배)로, 요청당 decode가 58에서 86 tok/s(1.48배)로 빨라진다. 744B GLM-5의 예비 실험은 100K를 넘는 문맥에서 prefill과 decode 모두 최소 1.3배다. 그림 1은 indexer 연산 50% 제거에서 약 1.2배 end-to-end라고도 적는다. 모델, 문맥, 하드웨어가 모두 다른 세 설정이므로 한 숫자로 합치지 않는다 (자체 보고). | — | 2603.12201 초록, §4.2, 표 1, 그림 1 | — | 일치 |
| P7-58 | IndexCache는 연산 최적화이다. 이미 저장한 main KV를 줄이는 것이 아니라 indexer 점수 계산을 줄인다. V4.1 논문도 인덱스 재사용만으로는 main KV 저장이 줄지 않는다고 쓴다(P7-03). | — | 2603.12201 §3; 2609.19969 §2.3 | — | 일치 |

## K. vLLM v0.32.0의 spec 클래스와 모델 대응

원문 세계의 "캐시 종류"가 vLLM에서 어떤 `KVCacheSpec`으로 바뀌는지를 정리한다. 모든 줄은 v0.32.0 소스를 열어 확인했다.

| ID | 주장 | 블로그 절 | 근거 위치 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P7-59 | `MLAAttentionSpec`은 head 1개짜리 잠재 벡터 캐시이고 별도 V가 없다(`head_size_v = 0`). `tokens_per_state`가 N이면 블록 안 상태 수는 `block_size // N`이다. 이 값이 압축 비율과 직접 이어지는 필드다. 기본값은 1(token마다 상태 하나)이다. | — | — | `vllm/v1/kv_cache_interface.py:210-233`(`tokens_per_state`, `num_states` 계산), `:528`(기본값 1), `:686-698`(`MLAAttentionSpec`) | 코드 전용 |
| P7-60 | 모델별 대응(1): DeepSeek-V3.2는 main MLA를 `MLAAttentionSpec`으로, indexer 캐시를 별도 `MLAAttentionSpec`으로 등록한다. DeepSeek-V4는 압축 KV를 `tokens_per_state = compress_ratio`인 `MLAAttentionSpec`으로, SWA 캐시와 압축 꼬리 상태를 `SlidingWindowMLASpec`으로 등록한다. 꼬리 상태는 main 압축기(CSA 21층, HCA 20층)뿐 아니라 indexer 압축기 21층에도 있다. 이를 모두 센 하한은 8행 기준 12,206,080B이고 main만 센 11,862,016B는 344,064B 모자라다(실제 클래스 호출로 얻은 spec 값, `docs/reference/specs.md`). | — | — | V3.2: `vllm/model_executor/layers/attention/mla_attention.py:1350-1380`, `vllm/model_executor/models/deepseek_v2.py:659`. V4: `vllm/models/deepseek_v4/attention.py:856-880`(압축 KV), `:907-925`(indexer), `vllm/models/deepseek_v4/compressor.py:179-193`(꼬리 상태), `vllm/v1/attention/backends/mla/sparse_swa.py:116-130`(SWA) | 코드 전용 |
| P7-61 | 모델별 대응(2): DeepSeek-V4.1은 압축 KV를 `MLAAttentionSpec`(`tokens_per_state = compress_ratio`, kv source 층에만), indexer를 `MLAAttentionSpec`, SWA 캐시를 `bounded_replay` 옵션이 있는 `SlidingWindowMLASpec`으로 등록한다. V4에서 `SlidingWindowMLASpec`이던 압축 꼬리 상태는 V4.1에서 `CircularBufferSpec`(요청당 블록 하나짜리 링)으로 바뀐다. | — | — | `vllm/models/deepseek_v41/attention.py:1138-1160`, `:1206-1230`, `:529-567`; `vllm/models/deepseek_v41/compressor.py:159-170`(`CircularBufferSpec`); `vllm/v1/kv_cache_interface.py:909-946`(`CircularBufferSpec`), `:949-974`(`SlidingWindowMLASpec`) | 코드 전용 |
| P7-62 | 모델별 대응(3): GLM-5.3-Flash의 선형 attention 층은 `MambaSpec`, sparse 층은 `MLAAttentionSpec`(indexer 캐시는 `tokens_per_state = index_kpool`), 미완성 꼬리는 `CircularBufferSpec`이다(Part 2 대장의 GLM 절과 같은 근거). Kimi K3의 KDA 층은 `MambaSpec`(`GatedDeltaNetAttention`을 상속해 prefill 체크포인트 필드를 덧붙임), MLA 층은 `MLAAttentionSpec`이다. `MambaSpec`은 문맥 길이 T를 포함하지 않는 request당 고정 상태다. | — | — | GLM: `vllm/models/glm5next/common/kda.py:163-176`, `common/attention.py:79-122`, `:125-181`, `:554-565`. K3: `vllm/models/kimi_k3/nvidia/kda.py:829-837`, `vllm/models/kimi_k3/nvidia/mla.py:417-431`. 공통: `vllm/model_executor/layers/mamba/abstract.py:65-84`, `vllm/v1/kv_cache_interface.py:1035-1045` | 코드 전용 |
| P7-63 | 논문의 Figure 6(상태 캐시 대 일반 KV cache)과 vLLM의 spec 대응은 비슷하지만 같지는 않다. 논문의 상태 캐시는 요청당 블록 하나에 SWA와 꼬리를 함께 담는 별도 배치다. vLLM v0.32.0은 SWA와 꼬리를 각각 별도 `KVCacheSpec`으로 등록하고 hybrid KV cache manager가 group으로 묶는다. 따라서 "vLLM이 논문의 배치를 그대로 구현한다"고 말하지 않는다. | — | 2606.19348 §3.5.1 그림 6 설명 대 위 P7-60, P7-61의 코드 | `vllm/models/deepseek_v4/compressor.py:179-193`, `vllm/models/deepseek_v41/compressor.py:159-170` | 논문·코드 차이 |

## 수업에 쓰지 말 것

1. 제작사 자체 보고 수치를 "측정된 사실"로 소개하기. 93.3%(V2, P7-08), 약 2%(V4, P7-16), 1/4와 1/8과 890바이트(V4.1, P7-27, P7-29), decode FLOPs 1/4 증가(P7-30), 3.01배와 4.44배(GLM-5.3-Flash, P7-46), 2.9배(GLM-5.2, P7-38), 75%(Kimi Linear, P7-50), 1.82배와 1.48배(IndexCache, P7-57)는 모두 논문 또는 문서의 자체 보고다. 반드시 "제작사 주장"이라고 표시한다.
2. GLM-5.3-Flash의 4.44배를 자체 산식으로 맞춰 보이기(P7-47). config로 재현되지 않았다. 측정 문맥 길이도 문서에 없다.
3. IndexShare 2.9배나 IndexCache 1.82배를 "KV cache가 줄었다"는 뜻으로 소개하기. 둘 다 indexer 연산 감소이고 캐시 크기 감소가 아니다(P7-39, P7-58).
4. "KDA는 인터페이스 변경 없이 drop-in"을 vLLM 구현에 대한 사실로 가르치기(P7-51). 논문의 주장이고, vLLM에서는 `MambaSpec`과 hybrid manager를 거친다.
5. 논문의 상태 캐시 배치(그림 6)를 vLLM의 구현이라고 말하기(P7-63). 대응하지만 같지 않다.
6. Kimi K3 토큰당 KV 약 27KB 같은 숫자. SGLang 날 0 지원 글 등 2차 글에서만 본 값이라 이 노드에서 원문을 못 봤다. 원문(K3 보고서)에는 토큰당 KV 바이트 수가 없었다.
7. GLM-5.3-Flash를 KDA 기반이라고 단정하기. config와 vLLM 클래스 이름으로 같은 계열임은 알 수 있지만 Z.ai 문서가 이름을 직접 쓰는지는 확인하지 못했다(P7-44). 전용 보고서도 없다(P7-48).
8. transformers 문서의 `index_kpool` 기본값 16(P7-45), V4와 V4.1의 `compress_ratios`를 서로 섞어 인용하기(V4는 4와 128, V4.1은 2와 1이다).
9. 논문에서 읽지 못한 부분: DeepSeek-V4.1 그림 2의 개별 곡선 값, 이 대장에는 적지 않았으니 수업에서 필요하면 원문에서 직접 확인한다.

## 읽은 원문 목록

| 원문 | 읽은 절·표·그림 |
|---|---|
| DeepSeek-V4.1-Flash, arXiv 2609.19969 | 초록, §1, §2.1, §2.2, §2.3, §2.3.1, §2.3.2, §2.4.1, §2.4.4, §3.2, §3.2.1, §3.2.2, §6, 그림 1~5 |
| DeepSeek-V4, arXiv 2606.19348 | §2.3, §2.3.1~2.3.4, §3.5.1, §3.5.2, §4.2.1, 그림 6 |
| DeepSeek-V2, arXiv 2405.04434 | 초록, §1, §2.1, §2.1.2~2.1.4, §3.1.2, 표 1, 표 9 |
| DeepSeek-V3.2-Exp 보고서 | §1, §2.1, §2.2, §3, 식 (1)~(4), 그림 1 |
| GLM-5, arXiv 2602.15763 | §2.1, §2.1.1, §2.1.2, §3.6.2, §5, 표 1~6 |
| Kimi Linear, arXiv 2510.26692 (HTML) | 초록, §1, §3, §6.3 |
| IndexCache, arXiv 2603.12201 (HTML) | 초록, §3, §4.2부터 §4.4까지, 표 1부터 표 3까지, 그림 1 |
| Kimi K3 기술 보고서(`MoonshotAI/Kimi-K3`의 `k3_tech_report.pdf`) | §2.1, §2.1.1, §2.1.2, §5.1, §5.3.1, §5.4.1, 그림 12 |
| GLM-5.2 블로그(`huggingface.co/blog/zai-org/glm-52-blog`) | Improved Architecture 요약, "Architecture for 1M Context" 절, 추론 엔진 과제 단락 |
| Z.ai 문서(`docs.z.ai/guides/vlm/glm-5.3-flash`) | Model Overview, Architecture 절 |
| config.json | `zai-org/GLM-5.3-Flash`, `zai-org/GLM-5.3`, `deepseek-ai/DeepSeek-V4.1-Flash`, `deepseek-ai/DeepSeek-V4-Flash`, `moonshotai/Kimi-K3` |
