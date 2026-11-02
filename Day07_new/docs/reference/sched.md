# 실제 Scheduler와 sched_sim 대조 (vLLM v0.32.0)

원자료: `Day07_new/data/reference_sched.json`. 검사: `Day07_new/tests/test_reference_sched.py`. 저자용 문서입니다.

한 줄 결론: 전체 입력 검사와 prefix cache를 모두 끈 실제 `Scheduler`는 38개 시나리오 전부에서 `sched_sim`과 행이 같습니다. 두 설정 중 하나라도 켜면 9개 시나리오에서 행이 달라지고, v0.32.0 기본값(전체 입력 검사 켜짐)에서 `doc_faq_chat`은 block 5~10개 어디서도 preempt가 나지 않습니다.

## 1. 무엇을 돌렸나

- 상태: `ran`. 대상은 `vllm.v1.core.sched.scheduler.Scheduler`입니다. 소스 트리의 git HEAD가 태그 `v0.32.0`, 커밋 `5df63a7`이고 변경이 없는 것을 실행 때 확인해 `source_git`에 남겼습니다.
- 환경: Python 3.12.14, torch 2.15.0, transformers 5.22.1, macOS arm64, CPU. 소스 트리를 `PYTHONPATH`로 올렸고 저장소 `.venv`와 `uv.lock`은 건드리지 않았습니다. 유료 호출 0회, GPU 없음, 모델 forward 없음.
- 생성: `tests/v1/core/utils.py`의 `create_scheduler`. Hugging Face에서 받은 것은 공개 `facebook/opt-125m`의 config 하나이고 tokenizer와 가중치는 받지 않았습니다(`skip_tokenizer_init=True`).
- 한 step: 도착 시각이 된 요청을 `add_request`로 넣고, `schedule()`을 부르고, 손으로 만든 `ModelRunnerOutput`을 `update_from_output()`에 넘깁니다. `num_computed_tokens`가 `num_tokens`에 닿은 요청에만 가짜 token 하나를 주고 나머지는 빈 목록입니다(`tests/v1/core/test_scheduler.py:674`의 방식).
- 대조 칸: `step`, `tokens`, `preempted`, `running_before`, `waiting_before`, `blocks_in_use`, `blocks_after`, `running_after`, `waiting_after`, `preemptions_total`. 시간 칸은 `sched_sim`에만 있고 실제 쪽에는 없으므로 대조하지 않습니다.
- 변형: 시나리오마다 `scheduler_reserve_full_isl`(isl)과 prefix cache를 켜고 끈 4개입니다. `sample_shared_prefix`와 `comeback_faq`는 적중을 보려는 입력이라 `prefix=on` 2개만 돌렸습니다. 합계 40개 시나리오, 156개 변형입니다.
- 결정성: 같은 실행을 두 번 돌려 파일이 바이트까지 같았습니다.

읽을 때 주의할 점이 넷 있습니다.

- `isl=on|prefix=on`은 서버 기본에 **가까운** 조합입니다. `scheduler_reserve_full_isl` 기본은 `True`이고(`vllm/config/scheduler.py:190`), `CacheConfig.enable_prefix_caching` 기본도 `True`입니다(`vllm/config/cache.py:141`). 다만 `vllm serve`의 기본은 모델이 지원하는지로 정해집니다(`vllm/engine/arg_utils.py:2991`, `:3021`). 서버를 띄워 확인한 것이 아닙니다.
- `create_scheduler`는 `enable_prefix_caching=False`와 `watermark=0.0`을 넣습니다. watermark 기본도 0.0입니다(`vllm/config/scheduler.py:196`). isl 인자는 없어서 만든 뒤 `scheduler.scheduler_reserve_full_isl`만 바꿨습니다(이 속성을 `vllm/v1/core/sched/scheduler.py:1270`이 읽습니다).
- `sched_sim`의 `num_blocks` N은 null block을 뺀 값이라 실제 쪽 `KVCacheConfig`에는 N+1을 넣고, 시작 때 free block이 N인지 확인했습니다.
- `max_model_len`은 실제 쪽이 2048입니다(opt-125m 한도). block 5개 pool은 실제 서버의 기동 검사(`vllm/v1/core/kv_cache_utils.py:1104-1132`)를 2048로는 통과하지 못합니다. 그래서 `preempt_blocks_5`(80), `preempt_blocks_8`(128), `self_preempt_tail`(48), `self_preempt_after_other`(48)를 pool이 담는 길이로 다시 돌렸고 16개 변형의 행이 모두 그대로였습니다(`probes.reachable_max_model_len`).

긴 표(24행 초과)는 앞 8행, preempt 행과 그 다음 행, 첫 차이 행과 그 다음 행만 저장하고 전체는 `core_sha256`으로 대조합니다.

## 2. 시나리오별 결과

`일치`는 4개 변형 전부 일치입니다. `prefix=on`만 돌린 시나리오는 2개 변형입니다.

| 과제 항목 | 시나리오 | 출처 셀 | 결과 |
|---|---|---|---|
| (a) | `doc_faq_chat_b32`, `doc_faq_chat_b16` | 01 셀 10, 61 | 일치 |
| - | `e1` | 03 셀 7 | 일치. 시작 running 상태는 큐 경로로 만들 수 없어 같은 칸을 직접 맞췄습니다 |
| (b) | `preempt_blocks_5` | 03 셀 36 | `isl=off` 2개 일치, `isl=on` 2개 차이 |
| (c) | `preempt_blocks_8` | 01 셀 50, 03 셀 36 | `isl=off|prefix=off`만 일치, 나머지 3개 차이 |
| - | `preempt_blocks_6` | 03 셀 36 | `isl=off` 2개 일치, `isl=on` 2개 차이 |
| - | `preempt_blocks_7`, `_9`, `_10` | 03 셀 36 | 일치 |
| (d) | `self_preempt_alone_decode` | 03 4절, 02b 4절 | 일치. 네 변형 모두 step 2에서 자기를 내보내고 멈춥니다 |
| (d) | `self_preempt_tail`, `self_preempt_after_other` | 03 4절, 02b 4절 | `prefix=off` 2개 일치, `prefix=on` 2개 차이 |
| (d) | `preempt_tail_by_head` | 02b 셀 36의 희생자 규칙 | 일치 |
| - | `waiting_skipped_then_head_blocks` | 02b 4절 표, 03 4절 | `prefix=off` 2개 일치, `prefix=on` 2개 차이 |
| - | `prompt_larger_than_pool` | `tests/test_sched_sim.py`의 멈춤 시험 모양 | `isl=off|prefix=off`만 일치, 나머지 3개 차이 |
| (e) | `threshold_alone`, `threshold_pair`, `threshold_pair_adaptive` | 03 셀 20 | 일치 |
| (e) | `mixed_threshold_0`, `_8`, `_16`, `_32`, `_48`, `_64` | 03 셀 18, 23, 64 | 일치 |
| (e) | `mixed_seqs_1`, `_2`, `_4`, `_6` | 03 셀 33, 66 | 일치 |
| - | `repeat_budget_16` ~ `_512` | 03 셀 26 | 일치 |
| - | `chunk_off_validated`, `chunk_off_boundary`, `chunk_off_unvalidated`, `chunk_off_unvalidated_same_arrival` | 03 셀 28, 29 | 일치 |
| prefix | `sample_shared_prefix` | 03 셀 52 | 2개 모두 차이(block 칸만) |
| prefix | `comeback_faq` | 02b 셀 39의 유사 시나리오 | 2개 모두 차이 |

### (a) `doc_faq_chat`, 예산 32, chunked, block 16

네 변형 모두 `sched_sim`과 같습니다. step별 token은 다음과 같습니다.

| step | doc | faq | chat |
|---:|---:|---:|---:|
| 1 | 32 | | |
| 2 | 22 | 10 | |
| 3 | 1 | 10 | 21 |
| 4 | 1 | 1 | 13 |
| 5~7 | 1 | 1 | 1 |
| 8 | 1 | 1 | |
| 9 | 1 | | |

### (b) block 5개

`isl=off`는 `sched_sim` 표와 같습니다. `isl=on`은 step 2부터 다르고 preempt가 없습니다.

| step | `sched_sim`과 `isl=off` | preempt | `isl=on` | preempt |
|---:|---|---|---|---|
| 1 | doc:32 | | doc:32 | |
| 2 | doc:22 faq:10 | | doc:22 | |
| 3 | doc:1 | faq | doc:1 | |
| 4~9 | doc:1 | | doc:1 | |
| 10 | faq:20 chat:12 | | faq:20 chat:12 | |
| 11 | faq:1 chat:22 | | faq:1 chat:22 | |
| 12~14 | faq:1 chat:1 | | faq:1 chat:1 | |
| 15 | faq:1 | | faq:1 | |

step 수는 15로 같지만 차이는 step 2, 3의 `faq:10`과 preempt입니다. `isl=off`의 step 3이 FCFS 자기 자신 preempt입니다.

### (c) 01의 `num_blocks=8`과 block 수 sweep

preempt 수입니다. 값 순서는 `isl=off|prefix=off`, `isl=off|prefix=on`, `isl=on|prefix=off`, `isl=on|prefix=on`입니다.

| block | 값 | 첫 칸이 03 셀 36의 `sched_sim` 값과 같은가 |
|---:|---|---|
| 5 | 1, 1, 0, 0 | 같음 |
| 6 | 0, 0, 0, 0 | 같음 |
| 7 | 0, 0, 0, 0 | 같음 |
| 8 | 3, 1, 0, 0 | 같음 |
| 9 | 0, 0, 0, 0 | 같음 |
| 10 | 0, 0, 0, 0 | 같음 |

block 8개에서 `chat`은 네 변형이 이렇게 갈립니다.

- `isl=off|prefix=off`: `sched_sim`과 같습니다. step 3에 21을 받고 step 4, 6, 8에 preempt되며 step 5, 7에 30을 받았다가 버린 뒤 step 9에 31을 받습니다.
- `isl=off|prefix=on`: step 4에 preempt 한 번으로 끝납니다. step 9에 복귀해 34 token 중 16을 적중으로 건지고 18만 계산합니다(`preempted_hits` 16).
- `isl=on`: preempt가 없습니다. `chat`은 step 8까지 waiting에 있다가 step 9에 입장합니다.

### (d) FCFS 자기 자신 preempt

- `self_preempt_tail`: step 2의 running이 `[a, b]`이고 `a`가 block을 받은 뒤 `b`가 받지 못합니다. `running[-1]`이 `b` 자신이라 자기를 내보내고 순회를 멈춥니다(`vllm/v1/core/sched/scheduler.py:802`, `:842`). 네 변형 모두 같습니다.
- `self_preempt_after_other`: step 2의 `preempted`가 `[c, b]`입니다. `a`가 `c`를 내보내 block을 받고, `b`가 자기를 내보냅니다.
- `self_preempt_alone_decode`: 혼자 있는 요청이 block 경계를 넘다 자기를 내보내고 그대로 멈춥니다. 실제 쪽은 예외 없이 빈 `schedule()`을 반복합니다. 이 pool은 기동 검사로 도달할 수 없는 상태입니다.
- `waiting_skipped_then_head_blocks`: step 2에 `B`가 자기를 내보내고 `C`는 자리가 있어도 들어가지 못합니다(`vllm/v1/core/sched/scheduler.py:900`). step 3, 4에는 맨 앞 `B`가 block이 모자라 `C`도 막힙니다. `prefix=off` 두 변형이 `sched_sim`과 같습니다.

### (e) threshold와 max_num_seqs

| 시나리오 | 첫 step | 전체 step |
|---|---|---:|
| `threshold_alone`(doc 혼자, 16) | doc:64 | 8 |
| `threshold_pair`(doc, faq, 16) | doc:16 faq:16 | 10 |
| `threshold_pair_adaptive` | doc:32 faq:30 | 9 |

`mixed_threshold_*`의 step 수는 threshold 0, 8, 16, 32, 48, 64에서 31, 48, 37, 27, 28, 31입니다. `mixed_seqs_*`의 step 수는 max_num_seqs 1, 2, 4, 6에서 82, 46, 31, 22입니다. 모두 네 변형이 `sched_sim`과 같습니다. `threshold`와 `max_num_seqs`만 보는 입력에는 공유 prefix가 없고 block도 넉넉해서 두 설정이 끼어들지 않은 결과입니다.

### prefix cache를 켠 `schedule()`

- `sample_shared_prefix`: `faq`와 `chat`이 `doc`의 앞 16, 32 token을 공유합니다. 입력에 적은 `cached_tokens`와 같은 적중이 실제로 나고(`prefix_hits` 48, `prefix_queries` 108) step별 token도 같습니다. 다른 것은 block 칸뿐입니다(step 3에 실제 6, `sched_sim` 9).
- `comeback_faq`: step 16에 `faq`, step 44에 `doc`이 밀려납니다. step 71에 둘이 돌아올 때 `doc`은 97 token 중 64를 적중으로 건져 33만 계산하고, `faq`는 적중 없이 35를 전부 계산합니다(적중 수만 관찰했고 그 block의 상태는 확인하지 않았습니다). 02b 셀 39의 두 경우를 한 실행에서 봅니다. 다만 입력이 다릅니다. 02b는 `KVManagerSim`에서 `doc`만 키우고, 이 실행은 세 요청이 모두 진행합니다.

## 3. 차이와 그 뜻

차이 있는 변형은 20개이고 `EXPECTED_DIFFERENCES`에 변형 이름과 원인으로 적었습니다. 원인은 다섯입니다.

### `reserve_full_isl`

대상: `preempt_blocks_5`, `preempt_blocks_6`, `preempt_blocks_8`의 `isl=on` 변형. 새 요청의 전체 입력이 들어갈 free block이 없으면 waiting에서 꺼내지 않습니다(`vllm/config/scheduler.py:190`, `vllm/v1/core/sched/scheduler.py:1270`, `vllm/v1/core/kv_cache_manager.py:522-539`). `sched_sim`은 기본값(`SchedConfig.reserve_full_isl=False`)이면 첫 chunk만 보므로 다르고, `SchedConfig(reserve_full_isl=True)`로 돌리면 같아집니다. `NOT_MODELED`에도 기본값을 따르지 않는다고 적혀 있습니다.

이 검사는 입장 때만 작동합니다. running 요청이 생성으로 block 경계를 넘을 때의 preempt는 막지 못합니다. `self_preempt_tail`의 `isl=on`에도 preempt가 있습니다. "기본 설정이면 preempt가 없다"가 아니라 "이 워크로드의 이 pool에서는 없다"로 읽어야 합니다.

`reserve_full_isl=True`를 켠 `sched_sim`은 `isl=on|prefix=off` 변형 38개 중 설정 오류로 끝나는 1개를 뺀 37개의 `core_sha256`을 재현합니다(`probes.isl_prototype`). 이 절의 8개 변형은 기본값(False)으로 돌린 `sched_sim`과의 차이이고, 검사 `FULL_INPUT_DIFFERENCES`는 True로 다시 돌린 행이 실제와 같은지도 확인합니다.

### `prefix_comeback`

대상: `self_preempt_tail`, `self_preempt_after_other`, `waiting_skipped_then_head_blocks`, `comeback_faq`의 `prefix=on` 변형. 복귀할 때 `num_computed_tokens == 0`이라 prefix cache를 조회합니다(`vllm/v1/core/sched/scheduler.py:959-967`). 예를 들어 `self_preempt_tail` step 4는 `sched_sim`이 `b:17`, 실제가 `b:1`입니다. `NOT_MODELED`에 적힌 한계입니다.

이 적중은 `vllm:prefix_cache_queries`와 `vllm:prefix_cache_hits`에 들어가지 않습니다. 복귀 요청은 `preempted_queries`, `preempted_hits`로 따로 쌓이고(`vllm/v1/metrics/stats.py:146-155`) 지표는 `queries`, `hits`만 더합니다(`vllm/v1/metrics/loggers.py:1167-1172`). 같은 실행의 `prefix_hits`가 0이고 `preempted_hits`가 16입니다. 그래서 prefix cache를 켠 변형의 마지막 조회 수와 적중 수는 `sched_sim`과 같습니다. 지표 쪽 연결은 코드 읽기이고 logger를 돌리지는 않았습니다.

### `evictable_admission`

대상: `preempt_blocks_8|isl=off|prefix=on`. `sched_sim`의 step 5는 `chat:30`인데 실제에는 `chat`이 없습니다. 적중한 block이 ref_cnt 0으로 free queue에 있으면 free 칸을 쓰는 수로 세기 때문입니다(`vllm/v1/core/single_type_kv_cache_manager.py:255-260`, `:265`). 적중 16 token이면 남은 18 token까지 한 번에 잡아 block 3개(적중 1, 새것 2)가 필요한데 free는 2개입니다. step 5 직전에 실제 `allocate_slots`를 불러 `None`을 확인했습니다(`probes.evictable_admission`).

그래서 prefix cache를 켜면 복귀 입장이 **늦어질** 수 있고, 이 입력에서는 그 덕분에 preempt가 3번에서 1번으로 줄었습니다. `NOT_MODELED`에 없는 효과입니다.

### `block_sharing`

대상: `sample_shared_prefix`. 다른 요청이 쥔 block에 적중하면 ref_cnt만 늘어납니다(`vllm/v1/core/single_type_kv_cache_manager.py:245-248`, `:267-278`). `sched_sim`은 `cached_tokens` 몫도 요청별 block으로 셉니다. token 칸은 같고 `blocks_in_use`, `blocks_after`만 다릅니다. `NOT_MODELED`의 "block 안의 부분 공유"와는 다른 내용이라 이 계산 방식은 아직 적혀 있지 않습니다.

`kv_cache_usage_perc`는 이 값에서 나오므로 step 3~8의 값이 부풀려집니다. 03 셀 52가 출력하는 step 2 표본(4/64)과 셀 54의 마지막 값(0)은 실제와 같아 지금 보이는 숫자는 바뀌지 않습니다.

### `pool_smaller_than_input`

대상: `prompt_larger_than_pool`의 `isl=off|prefix=on`, `isl=on` 2개. 64 token 입력에 block 2개 pool입니다.

- `isl=off|prefix=off`, `sched_sim`: 32 token을 넣고 밀어내기를 끝없이 반복합니다(둘 다 `step_cap`).
- `isl=on`: 0 token으로 처음부터 멈춥니다.
- `isl=off|prefix=on`: 한 번 밀려난 뒤 적중 block까지 세면 자리가 없어 멈춥니다.

실제 서버에서는 도달하지 못하는 상태입니다. KV가 `max_model_len` 한 건을 담지 못하면 기동 때 `ValueError`이기 때문입니다(`vllm/v1/core/kv_cache_utils.py:1104-1132`, 코드 읽기). `create_scheduler`가 이 검사를 지나가지 않아서 보인 상태이고, 스케줄러 동작의 교육 사례로 쓰면 안 됩니다.

### 조회 수 칸의 차이

`prefix=off`일 때 실제 `prefix_queries`는 0이고 `sched_sim`은 입장 때 prompt token을 더합니다(`vllm/v1/core/kv_cache_manager.py:253-256`). 행 대조 칸이 아니라 `PREFIX_OFF_COUNTER_DIFFERENCE`로 따로 검사합니다. `sched_sim`에는 prefix cache를 끄는 칸이 없습니다.

## 4. 노트북과 강사 문서에 미치는 영향

노트북과 문서는 이 작업에서 고치지 않았습니다. 셀 번호는 저장된 노트북의 0부터 세는 위치입니다.

### 01

- 셀 7: "이 스케줄러는 그 범위 밖" 문장이 맞지 않게 됩니다. 셀 10의 표는 실제 `Scheduler`의 네 변형과 행이 같습니다. "서버가 아니라 CPU 클래스 대조"라는 범위는 함께 적어야 합니다.
- 셀 49, 50: 추적은 `isl=off|prefix=off`일 때의 실제 행과 같습니다. 기본인 `isl=on`에서는 `chat`이 preempt되지 않습니다. "숫자 8은 preempt가 보이도록 수업이 고른 값"은 `sched_sim` 안에서만 맞습니다. "복귀한 요청이 전부 다시 계산"도 prefix cache를 끈 경우이고, 켜면 34 중 16을 건집니다.
- 셀 61: 예산 16도 네 변형이 같습니다. 바뀌는 주장은 없습니다.

### 02b

- 셀 35: 표의 "자기 자신이면", "그 step의 waiting", "복귀" 세 행이 실제 `Scheduler`로 확인됐습니다. 코드 읽기에서 실행 확인으로 올릴 수 있습니다.
- 셀 40: "이 표는 시뮬레이터 결과이며 실제 scheduler를 돌린 것이 아닙니다"는 그 표에 대해서는 여전히 맞습니다. 같은 현상을 `schedule()`에서 본 `comeback_faq`를 함께 가리킬 수 있지만 입력이 달라 표의 값 자체를 확인한 것은 아닙니다.
- 셀 32: `reference_kv.json`에 대한 문장이라 그대로 맞습니다.

### 03

- 셀 1: "`schedule()`은 그 범위에 없습니다", "어떤 step 표도 '실제 클래스와 같은 결과'라고 말하지 않습니다"가 맞지 않게 됩니다. 말할 수 있는 범위를 `isl`, prefix 조건과 함께 적어야 합니다.
- 셀 28, 29: 셀 29의 "짧은 `faq`까지 남아 있는 이유를 FCFS로 설명" 질문은 출력과 맞지 않습니다. 셀 28은 t=0에 멈추고 그때 `faq`는 아직 도착 전입니다. 실제 `stuck_state.waiting`도 `["doc"]`뿐입니다. `SimStuck` 메시지의 "남은 요청"은 도착 전 요청까지 포함합니다. FCFS로 막히는 장면은 모두 동시에 도착한 `chunk_off_unvalidated_same_arrival`에서 실제로 보입니다. `chunk_off_validated`의 실제 `ValueError`는 같은 비교에서 나옵니다(`vllm/config/scheduler.py:314-322`).
- 셀 31: "아래 표의 step 3이 이 경우입니다"는 `isl=off`일 때만 실제와 같습니다.
- 셀 35: "`faq:10`도 step 3의 preempt도 생기지 않습니다"가 `Scheduler` 실행으로 확인됐습니다. "코드 읽기와 `KVCacheManager` 호출" 부분을 올릴 수 있고 "서버를 띄워 본 것은 아닙니다"는 그대로 둡니다.
- 셀 36, 37, 39: 표 값 1, 0, 0, 3, 0, 0은 `isl=off|prefix=off`의 실제 값과 같습니다. 기본에서는 전부 0이고 `isl=off|prefix=on`은 1, 0, 0, 1, 0, 0입니다. 셀 39의 "실제 서버에서 같은 모양이 나온다는 뜻은 아닙니다"를 이 수치로 구체화할 수 있습니다. 서버라고 말하지 않고 클래스라고 말해야 합니다.
- 셀 50의 지표 표: `vllm:prefix_cache_queries`, `vllm:prefix_cache_hits` 행에 복귀 적중이 들어가지 않는다는 점을 더할 수 있습니다.
- 셀 7, 18, 20, 23, 26, 33, 64, 66: token과 step은 실제와 같습니다. 시간 칸(`toy ms`)은 여전히 수업 모델의 가정이고 `ttft_mean_ms` 같은 값은 실제 클래스가 낸 것이 아닙니다.
- 셀 52, 54: 조회 수와 적중 수는 실제와 같습니다(적중 48, 구간 조회 54). 지금 출력되는 수치는 바뀌지 않습니다.

### `docs/TEACHING_PATH.md`

- 45행(01의 셀 50): 사실은 맞습니다. 위 01 항목의 조건을 더할 수 있습니다.
- 79행(02b 4절): 복귀 조회를 실행 근거로 올릴 수 있습니다.
- 116행(03 4절): "코드 읽기와 실제 `KVCacheManager` 클래스 호출"을 `Scheduler` 실행으로 올릴 수 있습니다.

### 이 작업 범위 밖의 문서

`AGENTS.md:93`("`sched_sim`의 `schedule()`은 그 범위 밖이다"), `docs/REFERENCE_RUN.md:82`, `docs/REFERENCE_RUN.md:108`이 같은 이유로 바뀌어야 합니다.

## 5. `sched_sim`에 필요한 수정

`SchedConfig.reserve_full_isl`(기본 False)이 생겨 전체 입력 검사를 켤 수 있습니다. 규칙 옮김 자체의 결함은 찾지 못했습니다. `isl=off|prefix=off` 38개가 모두 일치합니다.

1. `NOT_MODELED`에 없는 것을 더합니다. `cached_tokens` 몫을 요청별 block으로 세어 `blocks_in_use`와 `kv_cache_usage_perc`가 커진다는 점(`block_sharing`), 적중 block이 free 칸을 쓰는 입장 규칙(`evictable_admission`), prefix cache를 끄는 칸이 없어 조회 수를 항상 센다는 점입니다.
2. `SimStuck` 메시지가 running, waiting과 도착 전 요청을 "남은 요청" 하나로 묶습니다. 나누어 적거나 03 셀 29의 질문을 고쳐야 합니다.
3. 전체 입력 검사 칸은 이미 `SchedConfig.reserve_full_isl`로 있습니다. 기본을 끔으로 둔 것은 기존 노트북 표를 바꾸지 않으려는 선택이고, 기본값 쪽 표를 노트북에서 보이려면 True로 돌리면 됩니다.

`tests/test_sched_sim.py`에서 함께 볼 것이 둘 있습니다.

- `test_stuck_when_request_can_never_fit`은 `max_steps` 10000에 닿아 통과합니다. 멈춤이 아니라 반복이고 메시지의 `big`만 맞춰 봅니다.
- `test_waiting_is_skipped_on_a_step_with_preemption_and_head_blocks_later_requests`의 `C`는 step 1에 끝나서(`{'A': 1, 'B': 1, 'C': 3}`) 두 assert가 그 규칙을 시험하지 못합니다. 이 파일의 `waiting_skipped_then_head_blocks`가 `C`를 step 2에 도착시킨 구성입니다.

## 6. 증명하지 않은 것

- 실제 서버, GPU, Day07 Pod의 동작. engine, worker, API server를 띄우지 않았고 모델 forward도 없습니다. 출력 token은 손으로 만들었습니다.
- 시간. TTFT, ITL, TPOT, step 시간은 실제 쪽에 없습니다. `sched_sim`의 `toy ms`는 여전히 가정입니다.
- `/metrics`. logger를 돌리지 않았습니다. 조회 수와 적중 수는 `PrefixCacheStats` 값이고 지표 연결은 코드 읽기입니다.
- async scheduling, PRIORITY 정책, speculative decoding, hybrid KV group, KV connector, watermark 0이 아닌 값. 모두 이 실행에 없습니다.
- 단일 full-attention group, block 16, opt-125m config만 썼습니다. 다른 모델의 동작이 아닙니다.

## 7. 다시 돌리기

저장소 `.venv`가 아니라 격리 venv에서 돌립니다. 저장소에 드라이버를 두지 않았습니다.

```bash
export PYTHONPATH=<v0.32.0 소스 트리>:<드라이버 폴더>
export VLLM_TARGET_DEVICE=cpu HF_HOME=<scratch> PYTHONDONTWRITEBYTECODE=1
<격리 venv>/bin/python run_sched.py fresh.json        # 약 6초
<격리 venv>/bin/python probe_evict.py                 # probe_evict.json
uv run --no-sync python proto_isl.py fresh.json       # proto_isl.json, 저장소 루트 환경
<격리 venv>/bin/python finalize.py fresh.json final.json
```

처음 한 번은 config를 받아야 하므로 `HF_HUB_OFFLINE=1`을 빼고 돌립니다. 저장된 결과는 `uv run --no-sync python -m pytest Day07_new/tests/test_reference_sched.py -q`가 대조합니다.
