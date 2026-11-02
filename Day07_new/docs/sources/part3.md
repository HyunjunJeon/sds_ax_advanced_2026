# Part 3 근거 대장

범위: 서빙 파라미터와 성능 측정. 기준 코드는 vLLM v0.32.0(커밋 5df63a7)이며 읽기만 했고 실행하지 않았다.
표기: 코드 경로는 `vllm/...:줄`, 문서 경로는 `docs/...:줄`(둘 다 v0.32.0 저장소 기준). 블로그는 절 제목만 적는다.
블로그 절 이름은 "Inside vLLM: 서버 시작부터 KV cache까지 소스 코드 톺아보기"의 소제목이다.
상태 값: 일치, 문서·코드 차이, 블로그·코드 차이, 코드 전용, 미확인. 문서와 코드가 다르면 코드를 따른다.

| ID | 주장 | 블로그 절 | 공식 문서 | v0.32.0 코드 | 상태 |
|---|---|---|---|---|---|
| P3-01 | 실행 중(running) 요청 수가 상한에 닿으면 waiting에서 더 꺼내지 않는다. 입력을 기다리는 streaming 세션도 이 수에 든다. 상한은 기본적으로 `max_num_seqs`다. | 요청 처리 4. Schedule | `docs/serving/data_parallel_deployment.md:27` (`--max-num-seqs`는 DP rank마다 적용) | `vllm/v1/core/sched/scheduler.py:132-136`(admission 상한이 `max_num_active_seqs` 없으면 `max_num_seqs`), `scheduler.py:922-923` | 일치 |
| P3-02 | `SchedulerConfig`의 `max_num_seqs=128`은 테스트 편의용이고, 실제 서버 값은 엔진 인자 단계에서 하드웨어·진입점별로 채워진다. GPU는 메모리 160GiB 이상이거나, 70GiB 이상이면서 이름에 a100이 없으면 1024이고, 그 외(80GB A100 포함)는 256이다. CPU는 LLM 클래스 256·world_size, `vllm serve` 128·world_size다. | 서버 초기화 3. Engine config (표는 batched tokens만 다룸) | 확인 못 함(문서에 기본값 표 없음) | `vllm/config/scheduler.py:43,62-67`, `vllm/engine/arg_utils.py:2923-2953,2975-2982,3113-3121` | 코드 전용 |
| P3-03 | 한 step의 token budget은 둘이다. `token_budget`은 `max_num_scheduled_tokens`에서 시작하고, 이 값을 따로 주지 않으면 `max_num_batched_tokens`와 같다. `input_budget`은 `max_num_batched_tokens`에서 시작한다. 배정할 때마다 둘 다 빼며, speculative decoding이면 `input_budget`에서 요청마다 draft 슬롯 몫을 더 뺀다. | 서버 초기화 5. Scheduler 소제목, 요청 처리 4. Schedule | `docs/configuration/optimization.md:60-66` | `vllm/v1/core/sched/scheduler.py:137-141`(초기값 결정), `scheduler.py:611,613-614`(두 budget과 draft 슬롯), `scheduler.py:856-857`, `scheduler.py:1366-1367`(차감), `vllm/config/scheduler.py:55-60`, `vllm/config/vllm.py:2263-2264`, 플래그 `vllm/engine/arg_utils.py:1710` | 일치 |
| P3-04 | `max_num_batched_tokens` 기본값: 메모리 160GiB 이상은 LLM 클래스 16384/서버 16384, 70GiB 이상이면서 이름에 a100이 없으면 16384/8192, 그 외 8192/2048. | 서버 초기화 3. Engine config, 설계 결정 "진입점마다 다른 batch 기본값" | 확인 못 함 | `vllm/engine/arg_utils.py:2923-2953` | 일치 |
| P3-05 | A100을 따로 빼는 이유가 PR #17885(큰 값이 처리량을 낮춤)라는 설명. | 설계 결정 "진입점마다 다른 batch 기본값" | 확인 못 함 | 코드 주석이 PR 번호만 가리킨다: `vllm/engine/arg_utils.py:2920-2922`. PR #17885 제목과 본문을 `gh pr view`로 읽었다. 본문은 A100의 성능 회귀를 고친다고 쓰고 Llama 70B 처리량을 TP=2 1054.01에서 1438.49(+36%), TP=4 3053.03에서 2994.03(-2%)로 적는다. 원인 설명 문장은 본문에 없다 | 일치 |
| P3-06 | 사용자가 값을 안 줬을 때 추가 보정이 있다. `performance_mode=throughput`이면 두 값을 2배, chunked prefill가 꺼져 있으면 `max_model_len` 이상으로 올리고, 멀티모달 prefix-LM 모델은 항목 하나가 들어가도록 올리며, 마지막에 `max_num_seqs*max_model_len`으로 상한을 둔다. | 서버 초기화 3 (표에 없는 보정) | 확인 못 함 | `vllm/engine/arg_utils.py:3130-3134`, `arg_utils.py:3140-3144`, `arg_utils.py:3150-3162`, `arg_utils.py:3167-3170` | 코드 전용 |
| P3-07 | `--gpu-memory-utilization` 기본값은 0.92다(예전 0.9가 아님). | 서버 초기화 5. EngineCore startup (곱하는 방식만 설명, 값은 안 적음) | `docs/design/metrics.md:386`의 예시 출력은 `gpu_memory_utilization="0.9"` | `vllm/config/cache.py:102-104`(기본 0.92, 설명 문구에도 0.92) | 문서·코드 차이 |
| P3-08 | 메모리 예산은 GPU 전체 메모리에 이 비율을 곱해 정하고, 인스턴스별 한도다. `--kv-cache-memory-bytes`를 주면 KV 크기는 이 비율을 보지 않는다. | 서버 초기화 5. EngineCore startup | `docs/configuration/optimization.md:40` (preemption이 잦으면 올리라고 안내) | `vllm/v1/worker/utils.py:724-726`, `vllm/config/cache.py:102-111`, `vllm/config/cache.py:257-264`, 플래그 `vllm/engine/arg_utils.py:1363` | 일치 |
| P3-09 | `--max-model-len`을 안 주면 모델 config에서 정하고, `-1`/`auto`면 메모리에 들어가는 최대 길이를 고른다. | 서버 초기화 3. Engine config (표의 max_model_len 행) | 확인 못 함 | `vllm/config/model.py:245-257`, `vllm/engine/arg_utils.py:966` | 일치 |
| P3-10 | chunked prefill는 "항상 True"가 아니라 모델이 지원하면 켜진다. 생성 모델은 보통 켜지고, 임베딩 계열 일부와 encoder-decoder는 꺼진다. | 요청 처리 / 실행 batch와 KV cache 2. chunked prefill | `docs/configuration/optimization.md:53` ("whenever possible") | `vllm/engine/arg_utils.py:695,2990,2993-2994`, `vllm/config/model.py:2175-2218`, `vllm/config/scheduler.py:292-300`. `SchedulerConfig.enable_chunked_prefill=True`(`vllm/config/scheduler.py:134`)는 테스트 편의용 기본값. | 일치 |
| P3-11 | chunked prefill를 끄면 budget보다 긴 새 요청은 이번 step에 못 들어가고 waiting 순회가 멈춘다. 시작 시 `max_num_batched_tokens < max_model_len`이면 ValueError인데, 값을 직접 줬을 때만 닿는다(안 주면 P3-06의 보정으로 올라간다). 문서는 "greater than"이라 쓰지만 코드는 같은 값을 허용한다. 지원 모델에서 손으로 끄면 코드가 충돌이나 잘못된 출력을 경고한다. | 실행 batch와 KV cache 2. chunked prefill | `docs/configuration/optimization.md:69-71` | `vllm/v1/core/sched/scheduler.py:1159-1166`, `vllm/config/scheduler.py:314-326`, `vllm/engine/arg_utils.py:3000-3009`, `arg_utils.py:3140-3144` | 문서·코드 차이 |
| P3-12 | `--long-prefill-token-threshold`는 기본 0(끔)이고, 요청 하나가 한 step에 받는 prefill token을 이 값으로 자른다. 경쟁 요청이 없으면(eligible 1개) 적용하지 않는다. | 실행 batch와 KV cache 2. chunked prefill | 확인 못 함 | `vllm/config/scheduler.py:79-84`, `vllm/v1/core/sched/scheduler.py:640-648`, 적용 지점 `scheduler.py:708-709`(running)과 `scheduler.py:1155-1156`(waiting), 검증 `vllm/config/scheduler.py:352-356` | 일치 |
| P3-13 | `--long-prefill-token-threshold-adaptive`는 `--long-prefill-token-threshold`가 0이 아닐 때만 동작하고, 켜면 컷오프가 `max_num_batched_tokens/(running+waiting 수)` 아래로 내려가지 않는다. | 언급 없음 | 확인 못 함 | `vllm/config/scheduler.py:86-90`, `vllm/v1/core/sched/scheduler.py:650-655`, 플래그 `vllm/engine/arg_utils.py:1738-1740` | 코드 전용 |
| P3-14 | `--max-num-queued-reqs`는 기본 None(제한 없음)이고, 넘으면 API server가 HTTP 503으로 거절한다. 미완료 요청(waiting+running) 기준이며 DP rank를 합쳐 센다. `n>1` 요청은 n개로 친다. 검사는 `AsyncLLM` 경로에만 있어 `LLM` 클래스에는 적용되지 않는다. | 요청 처리 3. ZMQ ADD | `docs/serving/data_parallel_deployment.md:27-29` | `vllm/config/scheduler.py:92-103`, `vllm/v1/engine/async_llm.py:316-350`, `vllm/engine/protocol.py:71`, `vllm/exceptions.py:156-175`, 플래그 `vllm/engine/arg_utils.py:1727-1728` | 일치 |
| P3-15 | `--max-num-queued-tokens`는 prefill 중인 요청의 prompt token 합에 거는 한도(TTFT 목표용)이고, 그 합이 이미 한도 이상이면 거절한다(새 요청의 token은 더해 보지 않는다). chunk 진행분과 prefix cache 적중을 빼지 않아 실제보다 많이 센다. | 요청 처리 3. ZMQ ADD | `docs/serving/data_parallel_deployment.md:29` | `vllm/config/scheduler.py:105-132`, `vllm/v1/engine/async_llm.py:325-333`, `async_llm.py:362-374`, `vllm/v1/engine/output_processor.py:532-541` | 일치 |
| P3-16 | `--tensor-parallel-size` 기본값은 1이다. 문서는 모델이 GPU 한 장에 안 들어가고 한 노드에는 들어갈 때 TP를 쓰라고 안내하고, GPU당 메모리 부담을 덜어 KV cache 자리를 늘릴 때도 쓴다고 적는다. | 다루지 않음(블로그는 multi-GPU NCCL을 미룸) | `docs/serving/parallelism_scaling.md:8`, `docs/configuration/optimization.md:86-102` | `vllm/config/parallel.py:141`, 플래그 `vllm/engine/arg_utils.py:1177` | 일치 |
| P3-17 | replica(복제본)는 DP로 가중치를 통째로 복제해 독립 batch를 처리한다. DP rank마다 KV cache가 따로이고, `--max-num-seqs`는 rank별, admission 한도는 서버 전체 기준이다. 단 MoE 모델은 rank가 완전히 독립이 아니다(expert 층이 forward마다 동기화). TP는 한 모델을 쪼개는 것이라 목적이 다르다. | 설계 결정 "API server와 EngineCore의 독립 확장"(DP를 한 줄 언급) | `docs/serving/data_parallel_deployment.md:3,9,15,17,25-29`, `docs/serving/parallelism_scaling.md:5-11` | 플래그 `vllm/engine/arg_utils.py:1209`. DP 내부 동작은 이 노드에서 코드를 따라가지 않았다. | 미확인 |
| P3-18 | `-O0`~`-O3`은 시작 시간과 성능을 맞바꾸는 단계이고 기본은 O2다. `-O3`은 현재 O2와 같다. `-O2`, `-O 2`, `-O=2` 모두 `--optimization-level`로 바뀐다. | 다루지 않음 | `docs/design/optimization_levels.md:5-10` | `vllm/config/vllm.py:123-136,427-431`, `vllm/utils/argparse_utils.py:358-368` | 일치 |
| P3-19 | 시작 로그에서 attention backend를 볼 수 있다. 사용자가 고르면 `Using <backend> backend.`, 자동 선택이면 `Using <이름> attention backend out of potential backends: [...]`. 선택 플래그는 `--attention-backend`. | 다루지 않음 | 확인 못 함 | `vllm/platforms/cuda.py:446`, `vllm/platforms/cuda.py:506-512`, `vllm/engine/arg_utils.py:1086` | 코드 전용 |
| P3-20 | 한 step의 순서는 running 먼저, 그다음 waiting이다. waiting은 이번 step에 preempt가 없었을 때만 본다(모든 요청을 멈춘 `PAUSED_ALL` 상태에서도 보지 않는다). | 요청 처리 4. Schedule | `docs/configuration/optimization.md:53` | `vllm/v1/core/sched/scheduler.py:657-659`(running 순회), `scheduler.py:899-912`(waiting, `not preempted_reqs` 조건과 budget 조건) | 일치 |
| P3-21 | scheduler에는 prefill 단계/decode 단계 구분이 없고, 요청마다 "아직 계산 안 한 token 수"만 본다. chunked prefill은 그 결과로 나온다. 예외로 DP prefill balancing은 `is_prefill_chunk`를 보고 prefill을 미룬다. | 설계 결정 "prefill과 decode의 구분 없는 scheduling" | 확인 못 함 | `vllm/v1/core/sched/scheduler.py:593-602`(주석), 예외 `scheduler.py:634-638,686`, `scheduler.py:1113-1116` | 일치 |
| P3-22 | 문서는 "decode를 모두 먼저 batch하고 그다음 prefill"이라 쓴다. 코드는 decode/prefill이 아니라 running 큐 전체를 먼저 순회하며, 아직 prompt가 남은 running 요청도 그 안에서 chunk를 받는다. | 요청 처리 4. Schedule (running 먼저, 남은 prompt는 chunk로) | `docs/configuration/optimization.md:53` | `vllm/v1/core/sched/scheduler.py:657-712` | 문서·코드 차이 |
| P3-23 | preempt 경로: KV block 할당 실패 → FCFS면 running의 마지막 요청을 희생양으로 고름(priority 정책이면 `(priority, arrival_time)`이 최대인 것, 곧 우선순위가 가장 낮고 같으면 가장 늦게 온 것) → block 반납, `num_computed_tokens=0`, 상태 PREEMPTED, `num_preemptions+1`, waiting 맨 앞에 되돌림. 고른 요청이 자기 자신이면 running 순회를 멈춘다. 복귀 때는 계산 수가 0이라 prefix cache를 조회하므로, 덮어써지지 않은 block은 재사용하고 나머지 token(이미 생성한 출력 포함)을 계산한다. prompt 전체 재계산은 적중이 없을 때뿐이다(P2-37). KV connector가 block 반납을 미루는 중이면 preempt 없이 멈출 수 있다. | 요청 처리 4. Schedule의 KVCacheManager 소제목 | `docs/configuration/optimization.md:47` (V1 기본은 RECOMPUTE) | `vllm/v1/core/sched/scheduler.py:776-803`, `scheduler.py:788-792,805-806`(connector), `scheduler.py:842-844`, `scheduler.py:1571-1614`, 복귀 `scheduler.py:960-967`, `scheduler.py:1126-1129` | 블로그·코드 차이 |
| P3-24 | 문서가 보여 주는 preempt 경고 문구(`Sequence group 0 is preempted by PreemptionMode.RECOMPUTE ...`)는 v0.32.0 코드에 없다. 저장소 전체를 grep하면 `PreemptionMode`와 `Sequence group`은 이 문서 파일에서만 나온다. | 다루지 않음 | `docs/configuration/optimization.md:34` | `vllm/` 전체 검색 결과 없음(확인한 방법: grep) | 문서·코드 차이 |
| P3-25 | preempt 횟수는 `vllm:num_preemptions`로 센다. 근거 이벤트(PREEMPTED)는 통계 수집(`log_stats`)이 켜져 있을 때만 기록된다. `vllm serve`는 기본으로 켜져 있고 `LLM` 클래스는 기본으로 꺼져 있다. 요청별 횟수는 `vllm:request_num_preemptions` 히스토그램. | 다루지 않음 | `docs/configuration/optimization.md:45` | `vllm/v1/core/sched/scheduler.py:1609-1610`, `vllm/v1/metrics/stats.py:576-577`, `vllm/v1/metrics/loggers.py:738-741,1010-1014,1259-1261`, `--disable-log-stats` 기본 False `vllm/engine/arg_utils.py:612`, `LLM` 클래스 기본 True `vllm/entrypoints/llm.py:226-227` | 코드 전용 |
| P3-26 | 클라이언트 TTFT = 요청을 보낸 시각부터 `choices`가 있는 첫 SSE 데이터까지의 시간. 첫 chunk의 text가 비어 있어도 TTFT로 친다. | 요청 처리 1. HTTP POST의 "SSE" 소제목 | `docs/benchmarking/cli.md:131-132` | `vllm/benchmarks/lib/endpoint_request_func.py:255-266`(completions), `endpoint_request_func.py:438`(chat, `:436`은 `if not first_chunk_received`) | 일치 |
| P3-27 | 클라이언트 ITL = 연속한 두 chunk 사이의 간격이다. token 단위가 아니다. 한 chunk에 token이 여러 개 있어도 ITL 표본은 하나이고, 0짜리 간격을 만들어 넣지 않는다. 서버가 `--stream-interval` > 1이거나 speculative decoding을 쓰면 chunk 하나에 여러 token이 담긴다. | 요청 처리 1. HTTP POST의 "SSE" 소제목 | `docs/benchmarking/cli.md:133-135,145-159` | `vllm/benchmarks/lib/endpoint_request_func.py:267-272`, 주석 `vllm/benchmarks/serve.py:613-616`, `vllm/config/scheduler.py:213-217` | 일치 |
| P3-28 | TPOT = (요청의 E2EL − TTFT) / (출력 token 수 − 1). 출력이 1개 이하인 요청은 TPOT 통계에서 빠진다(goodput 계산에서만 0으로 취급). 출력 token 수는 서버 usage 값, 없으면 토크나이저로 세고, 토크나이저도 없으면 1로 둔다. | 다루지 않음 | `docs/benchmarking/cli.md:136-143` | `vllm/benchmarks/serve.py:601-631`, usage 수집 `endpoint_request_func.py:273-277` | 일치 |
| P3-29 | 클라이언트 E2EL = 마지막으로 token이 담긴 chunk의 시각 − 요청 시작 시각. 뒤따르는 usage 전용 chunk는 끝 시각에 반영하지 않는다. | 다루지 않음 | `docs/benchmarking/cli.md:136-143`(식에 end-to-end latency라고만 씀). `:1329`의 "TTFT + decode time"은 Multimodal Processor Benchmark 절(`:1309`) 설명이라 근거로 쓰지 않는다 | `vllm/benchmarks/lib/endpoint_request_func.py:287`, `endpoint_request_func.py:447,462`(`:447`이 `most_recent_timestamp = timestamp`), 집계 `vllm/benchmarks/serve.py:634`(`e2els.append(outputs[i].latency)`) | 일치 |
| P3-30 | 서버(Prometheus) 쪽 TPOT는 `decode_time/(생성 token 수−1)`이고 decode_time은 EngineCore 출력 시각으로 잰 첫 token~마지막 token 간격이다. 문서는 같은 지표를 `(E2E−TTFT)/(n−1)`로 적는다. 코드의 E2E와 TTFT는 API server의 iteration 시각으로 재므로 구간은 같아도 시계가 다르다. 클라이언트 벤치마크는 같은 모양의 식을 쓰지만 측정 지점이 또 다르다. | 다루지 않음 | `docs/design/metrics.md:55,69-80` | `vllm/v1/metrics/stats.py:596-612`, 시계 `stats.py:478,501-503,521,549-554,590`, 관측 `vllm/v1/metrics/loggers.py:1324-1325`, 클라이언트 `vllm/benchmarks/serve.py:626-628` | 문서·코드 차이 |
| P3-31 | 서버 TTFT는 API server가 요청을 받은 시각(arrival_time)부터 첫 출력이 처리된 iteration 시각까지다. 서버 ITL은 출력 이벤트마다 직전 출력과의 간격을 한 표본으로 기록하고(요청당 한 표본이 아니다), EngineCore 출력 시각으로 잰다. | 다루지 않음 | `docs/design/metrics.md:54,69-72` | `vllm/v1/metrics/stats.py:501-503,521-523`, `stats.py:548-554`, 도착 시각 `vllm/v1/engine/input_processor.py:414-415` | 일치 |
| P3-32 | `vllm bench serve`의 `--request-rate` 기본은 inf(전부 시각 0에 전송)이고, 유한값이면 Poisson(또는 `--burstiness`에 따른 gamma) 도착 간격이다. `--max-concurrency`는 동시 실행 상한이라 실제 요청률이 더 낮아질 수 있다. | 다루지 않음 | `docs/benchmarking/cli.md:704-708` | `vllm/benchmarks/serve.py:1698-1712`, `serve.py:1631-1644` | 일치 |
| P3-33 | `--ramp-up-strategy`는 `linear`/`exponential`만 받고 `--ramp-up-start-rps`, `--ramp-up-end-rps`가 둘 다 필요하다. 이때 `--request-rate`를 유한값으로 같이 주면 에러(기본 inf는 괜찮다), start가 end보다 크면 에러, exponential에서 start 0도 에러. | 다루지 않음 | `docs/benchmarking/cli.md:658-671` (제약은 문서에 없음) | `vllm/benchmarks/serve.py:1917-1941`, 검증 `serve.py:2030-2047`, 계산식 `serve.py:385-398` | 일치 |
| P3-34 | `--percentile-metrics` 허용 이름은 ttft, tpot, itl, e2el, client_queue_time, e2el_including_client_queue이고 생략하면 생성 모델은 `ttft,tpot,itl`. `--metric-percentiles` 기본은 `"99"`. | 다루지 않음 | `docs/benchmarking/cli.md:706`(일부만 언급). `:1330-1331`은 Multimodal Processor Benchmark 절이라 `vllm bench serve` 근거가 아니다 | `vllm/benchmarks/serve.py:1800-1818`, 기본값 적용 `serve.py:2207-2215` | 코드 전용 |
| P3-35 | `--goodput`은 `KEY:VALUE`(ms) 쌍을 여러 개 받고 키는 ttft, tpot, e2el만 허용한다. 요청이 모든 SLO를 동시에 만족할 때만 good으로 센다. | 다루지 않음 | 확인 못 함(`docs/benchmarking/cli.md`에서 goodput 언급 없음) | `vllm/benchmarks/serve.py:1820-1830`, `serve.py:1473-1492`, `serve.py:639-663` | 코드 전용 |
| P3-36 | `GET /metrics`는 Prometheus 텍스트 형식으로 `vllm:` 접두 지표를 내보낸다. `--disable-log-stats`면 기본 stat logger를 만들지 않아 엔진 지표가 등록되지 않는다. | 다루지 않음 | `docs/design/metrics.md:24` | `vllm/entrypoints/serve/instrumentator/metrics.py:77`, `vllm/v1/engine/async_llm.py:196-204` | 일치 |
| P3-37 | 엔진 지표는 대부분 라벨 `model_name`, `engine`을 가진다. 예외로 `vllm:admission_rejections`는 `model_name`, `reason`만 갖고 `engine`이 없다(`vllm/v1/metrics/loggers.py:847-853`). LoRA를 켰을 때만 생기는 `vllm:lora_requests_info`도 다른 라벨을 쓴다(`loggers.py:1103-1111`). 일부는 라벨이 더 붙는다(`reason`, `finished_reason`, `source`, `status`, `stage`). | 다루지 않음 | `docs/design/metrics.md` 예시 출력(라벨 이름이 옛 형태) | `vllm/v1/metrics/loggers.py:499-504`, 추가 라벨 `loggers.py:557,811,790,649,582` | 코드 전용 |
| P3-38 | Counter는 노출될 때 `_total`이 붙는다(코드 등록 이름에는 없음). 이 동작은 prometheus_client 라이브러리 몫이고, 저장소 환경의 0.26.0에서 `vllm:num_preemptions` Counter를 만들어 확인했다. 단일 프로세스 레지스트리와 `PROMETHEUS_MULTIPROC_DIR` 레지스트리 모두 `vllm:num_preemptions_total`을 내고, 단일 프로세스는 `_created` 줄도 낸다. vLLM 서버를 띄워 본 출력은 아니다. | 다루지 않음 | `docs/design/metrics.md:633-636` | 등록 이름 `vllm:num_preemptions` 등 `loggers.py:739`, 클래스 `vllm/v1/metrics/loggers.py:9,475`, 레지스트리 `vllm/v1/metrics/prometheus.py:47-53`, 요구 버전 `requirements/common.txt:21`(0.18.0 이상. 실행은 0.26.0만) | 일치 |
| P3-39 | 문서가 `vllm:num_requests_*`에 `_swapped`가 있다고 쓰지만 v1 지표 코드에는 swapped 지표가 없다. | 다루지 않음 | `docs/design/metrics.md:57` | `vllm/v1/metrics/` 검색 결과 없음(grep), 등록된 목록 `loggers.py:527-557` | 문서·코드 차이 |
| P3-40 | 요청 대기 시간 지표 `vllm:request_queue_time_seconds`는 첫 QUEUED 이벤트부터 첫 SCHEDULED까지다(요청마다 완료 시점에 한 번 기록). preempt 뒤 다시 기다린 시간은 들어가지 않는다. | 요청 처리 3 (waiting queue에서 TTFT가 늘어난다는 설명) | `docs/design/metrics.md:62` ("Queue time"만 적음) | `vllm/v1/metrics/stats.py:572-574,592-593`, `vllm/v1/metrics/loggers.py:970-974,1296-1298` | 일치 |
| P3-41 | 같은 서버에 `vllm bench serve`를 반복해서 돌리면 앞 실행이 prefix cache에 남긴 prompt가 재사용돼 처리량이 부풀려질 수 있다. 재현 가능한 dataset이면 어느 것이든 해당한다. | 다루지 않음 | `docs/benchmarking/cli.md:114` | 이 경고는 문서 문장이고 이 노드에서 실행해 보지 않았다. 재사용되는 쪽의 코드는 P2-29, P2-31(`vllm/v1/core/kv_cache_manager.py:264-300`). | 일치 |

## 파라미터 기본값

"문맥"은 엔진을 만든 진입점이다. `vllm serve`는 `OPENAI_API_SERVER`(`vllm/entrypoints/cli/serve.py:191`), `LLM` 클래스는 `LLM_CLASS`(`vllm/entrypoints/llm.py:343`).
메모리 구분은 `get_device_total_memory()` 값과 장치 이름으로 한다(`vllm/engine/arg_utils.py:2913-2918`에서 조회 실패 시 "그 외" 값을 쓴다).

| 플래그 | 기본값 | 문맥·하드웨어 | 근거 |
|---|---|---|---|
| `--max-num-batched-tokens` | 16384 | LLM 클래스, 메모리 160GiB 이상 | `vllm/engine/arg_utils.py:2923-2927` |
| 〃 | 16384 | `vllm serve`, 메모리 160GiB 이상 | 〃 |
| 〃 | 16384 / 8192 | LLM 클래스 / `vllm serve`, 메모리 70GiB 이상이고 이름에 a100 없음(H100·H200 등) | `arg_utils.py:2933-2937` |
| 〃 | 8192 / 2048 | LLM 클래스 / `vllm serve`, 그 외(A100 포함, 조회 실패 포함) | `arg_utils.py:2945-2948` |
| 〃 | 4096·world_size / 2048·world_size | CPU | `arg_utils.py:2975-2978` |
| 〃 | 위 값이 TPU 종류에 따라 덮어써짐(V6E 2048/1024, V5E 1024/512, V5P 512/256) | TPU | `arg_utils.py:2956-2972` |
| 〃 | 256 | batched DP MoE 사용 시 | `arg_utils.py:3113-3117`, `vllm/config/scheduler.py:42` |
| 〃 | 2048 | `SchedulerConfig` 자체 기본(테스트용) | `vllm/config/scheduler.py:41,48` |
| `--max-num-seqs` | 1024 | 메모리 160GiB 이상, 또는 70GiB 이상 비 A100(두 진입점 모두) | `arg_utils.py:2928-2931,2938-2941` |
| 〃 | 256 | 그 외(두 진입점 모두) | `arg_utils.py:2949-2952` |
| 〃 | 256·world_size(LLM) / 128·world_size(serve) | CPU | `arg_utils.py:2979-2982` |
| 〃 | 128 | `SchedulerConfig` 자체 기본(테스트용) | `vllm/config/scheduler.py:43` |
| `--performance-mode throughput` | 위 두 값을 사용자가 안 줬을 때 2배 | 모든 곳 | `arg_utils.py:3130-3134` (기본 모드는 `balanced`, `vllm/config/vllm.py:433`) |
| `--gpu-memory-utilization` | 0.92 | 모든 곳, 범위 0 초과 1 이하 | `vllm/config/cache.py:102` |
| `--max-model-len` | 모델 config에서 도출. `-1`/`auto`는 메모리에 맞춰 선택 | 모든 곳 | `vllm/config/model.py:245-257` |
| `--enable-chunked-prefill` | 모델이 지원하면 켜짐(None에서 결정). encoder-decoder는 강제 끔 | 모든 곳 | `arg_utils.py:695,2990,2993-2994`, `vllm/config/scheduler.py:292-300` |
| `--long-prefill-token-threshold` | 0(끔) | 모든 곳 | `vllm/config/scheduler.py:79` |
| `--long-prefill-token-threshold-adaptive` | False | 모든 곳 | `vllm/config/scheduler.py:86` |
| `--max-num-queued-reqs` | None(제한 없음) | 모든 곳 | `vllm/config/scheduler.py:92` |
| `--max-num-queued-tokens` | None(제한 없음) | 모든 곳 | `vllm/config/scheduler.py:105` |
| `--stream-interval` | 1 | 모든 곳 | `vllm/config/scheduler.py:213` |
| `--tensor-parallel-size` | 1 | 모든 곳 | `vllm/config/parallel.py:141` |
| `-O` / `--optimization-level` | 2 | 모든 곳 | `vllm/config/vllm.py:427` |
| `--disable-log-stats` | False(통계 수집 켜짐) | `vllm serve`. `LLM` 클래스는 따로 안 주면 True(꺼짐) | `vllm/engine/arg_utils.py:612`, `vllm/entrypoints/llm.py:226-227` |
| `vllm bench serve --request-rate` | inf | 클라이언트 | `vllm/benchmarks/serve.py:1698-1701` |
| `vllm bench serve --burstiness` | 1.0 | 클라이언트 | `serve.py:1707-1710` |
| `vllm bench serve --metric-percentiles` | "99" | 클라이언트 | `serve.py:1811-1814` |

`vllm bench serve --num-prompts`의 기본값은 1000이다. 인자는 `vllm/benchmarks/datasets/datasets.py:1587`에서 `default=DEFAULT_NUM_PROMPTS`로 정의되고 `vllm/benchmarks/datasets/datasets.py:70`에서 `DEFAULT_NUM_PROMPTS = 1000`이다. `vllm/benchmarks/serve.py:1591`의 `add_dataset_parser(parser)`가 이 인자를 붙인다. 사용법 주석(`vllm/benchmarks/serve.py:18`)도 1000이다.

## 메트릭 목록

모든 이름은 `vllm/v1/metrics/loggers.py`에 등록된 문자열이다. 공통 라벨은 `model_name`, `engine`(`loggers.py:499`). Counter는 `/metrics` 출력에서 `_total`이 붙는다(P3-38). Histogram은 `_bucket`, `_sum`, `_count`로 갈라져 나온다.

| 항목 | 정확한 이름 | 종류·추가 라벨 | 의미 | 줄 |
|---|---|---|---|---|
| prefix cache 조회 | `vllm:prefix_cache_queries` | Counter, 추가 라벨 없음 | 조회한 token 수(요청 수가 아님) | `loggers.py:661-666` |
| prefix cache 적중 | `vllm:prefix_cache_hits` | Counter, 추가 라벨 없음 | 캐시에서 찾은 token 수. 적중률은 hits ÷ queries로 계산(우리의 해석) | `loggers.py:672-675` |
| (참고) 외부 connector | `vllm:external_prefix_cache_queries`, `vllm:external_prefix_cache_hits` | Counter | KV connector 쪽 prefix cache. 단일 인스턴스 실습에서는 쓰지 않음 | `loggers.py:685-706` |
| KV 사용률 | `vllm:kv_cache_usage_perc` | Gauge | 1이 100% | `loggers.py:619-623`, 값 `loggers.py:1165`, 출처 `vllm/v1/core/sched/scheduler.py:2950` |
| preemption 누적 | `vllm:num_preemptions` | Counter | 엔진이 preempt한 횟수 누적 | `loggers.py:738-741`, 증가 `loggers.py:1259-1261` |
| 요청별 preemption | `vllm:request_num_preemptions` | Histogram | 요청 하나가 preempt된 횟수 분포 | `loggers.py:1010-1014` |
| waiting | `vllm:num_requests_waiting` | Gauge | 처리 대기 요청 수 | `loggers.py:537-541` |
| waiting 사유별 | `vllm:num_requests_waiting_by_reason` | Gauge, 추가 라벨 `reason`(`capacity`, `deferred`) | 사유별 대기 수. 합이 waiting과 같다고 코드 설명에 적혀 있음 | `loggers.py:547-557` |
| running | `vllm:num_requests_running` | Gauge | 실행 batch에 들어 있는 요청 수 | `loggers.py:527-531` |
| TTFT | `vllm:time_to_first_token_seconds` | Histogram | 서버 도착 시각~첫 출력(초) | `loggers.py:930-934`, 계산 `vllm/v1/metrics/stats.py:521-522` |
| ITL | `vllm:inter_token_latency_seconds` | Histogram | 연속한 출력 이벤트 사이 간격(초). 출력 하나에 token이 여럿이면 token당 값이 아님 | `loggers.py:940-944`, 계산 `stats.py:551-552` |
| TPOT(서버) | `vllm:request_time_per_output_token_seconds` | Histogram | 요청당 `decode_time/(생성 수−1)`. 생성 수가 1 이하면 0 | `loggers.py:950-954`, 계산 `stats.py:608-612` |
| E2E | `vllm:e2e_request_latency_seconds` | Histogram | 서버 도착~완료(초) | `loggers.py:960-964`, 계산 `stats.py:590` |
| 대기 시간 | `vllm:request_queue_time_seconds` | Histogram | 처음 WAITING에 머문 시간(QUEUED~첫 SCHEDULED). preempt 뒤 재대기는 넣지 않음 | `loggers.py:970-974`, 계산 `stats.py:572-574,592-593` |
| (참고) prefill/decode/추론 | `vllm:request_prefill_time_seconds`, `vllm:request_decode_time_seconds`, `vllm:request_inference_time_seconds` | Histogram | 각각 PREFILL, DECODE, RUNNING 구간 시간. preempt 시간이 구간에 포함됨 | `loggers.py:980-1004`, 주석 `stats.py:595-603` |

## 설계 결정과 PR

코드나 문서에서 확인한 것만 적는다. PR 본문은 아래에 읽었다고 적은 것만 열어 보았다.

- 단계 구분이 없는 scheduler: 요청마다 `num_computed_tokens`가 `num_tokens_with_spec`를 따라잡도록 token을 나눠 준다는 주석이 근거다. `vllm/v1/core/sched/scheduler.py:593-602`. 블로그의 설계 결정 절과 같은 내용이다.
- preempt는 swap이 아니라 recompute: 문서가 V1 기본이 RECOMPUTE라고 밝히고(`docs/configuration/optimization.md:47`), 코드는 `num_computed_tokens=0`으로 되돌린다(`scheduler.py:1593`). 이유(재계산이 더 싸다)는 문서 문장만 확인했고 PR은 못 봤다.
- 503 거절은 다른 인스턴스로 재시도하게 하려는 선택이다. 예외 클래스 설명에 직접 적혀 있다. `vllm/exceptions.py:156-170`.
- `max_num_queued_tokens`의 과대 집계는 의도된 보수적 선택이다. `vllm/config/scheduler.py:121-132`, `vllm/v1/engine/async_llm.py:325-333`.
- ITL에서 같은 출력 안의 token은 간격 0짜리 표본을 만들지 않는다. 문서가 spec decode 예시로 설명한다. `docs/benchmarking/cli.md:148-159`.
- Prometheus TPOT는 token이 1개 이하인 요청도 0으로 기록하는 반면 벤치마크는 그런 요청을 TPOT 통계에서 제외한다. 그래서 두 값이 다를 수 있다고 문서가 적었고 코드와 맞는다. `docs/design/metrics.md:75-80`, `vllm/v1/metrics/stats.py:608-612`, `vllm/benchmarks/serve.py:624-629`.
- A100 예외와 PR #17885: 코드 주석이 PR 번호를 가리킨다(`vllm/engine/arg_utils.py:2920-2922`). PR 본문을 읽어 확인함: Llama 70B TP=2 +36%, TP=4 -2%(`part1.md`의 #17885 줄과 같다). 원인 분석은 본문에 없다.
- 블로그가 근거로 드는 PR #17546(`--api-server-count`)과 이슈 #8779("Scheduling is not cheap")는 본문을 읽어 제목과 범위를 확인했다(`part1.md`, `part2.md` P2 이슈 줄). 확인하지 못한 것은 이 둘이 말하는 효과 수치이고, #17546 본문에 벤치마크 표는 있으나 블로그의 수치와 대조하지 않았으므로 미확인이다. #6883(ZMQ vs gRPC)은 PR 본문을 읽어 확인했다(`part1.md`의 #6883 줄: TPOT 64.15 대 57.35, TTFT 450.05 대 298.09).
- 코드에 있지만 블로그가 안 다루는 admission 관련 설정(`watermark`, `scheduler_reserve_full_isl`, `max_num_active_seqs`)은 선언만 확인했다. `vllm/config/scheduler.py:69-77,190-201`. 동작을 따라가지 않았으므로 수업에 쓰려면 별도 확인이 필요하다.

## 수업에 쓰지 말 것

- "`--gpu-memory-utilization` 기본은 0.9": v0.32.0은 0.92다. `docs/design/metrics.md:386`의 예시 출력을 근거로 삼지 않는다(P3-07).
- "`vllm serve`의 `max_num_seqs` 기본은 128, `max_num_batched_tokens`는 2048": `SchedulerConfig`의 테스트용 기본을 서버 기본으로 말하는 것이다. 실제 값은 GPU와 진입점에 따라 달라지고, 70GiB 미만 GPU의 2048이나 CPU의 128·world_size처럼 숫자가 우연히 겹치는 구성이 있을 뿐이다(P3-02, P3-04).
- 문서의 preempt 경고 로그 문장을 실제 출력이라고 보여 주는 것(P3-24). 실습에서 preempt를 보여 주려면 `vllm:num_preemptions`를 `/metrics`에서 읽는다.
- "decode를 전부 먼저 batch하고 그다음 prefill"이라는 문서식 설명(P3-22). 수업에서는 "running 큐를 먼저, 그다음 waiting"으로 설명한다.
- "chunked prefill를 끄려면 `max_num_batched_tokens`가 `max_model_len`보다 커야 한다"를 엄격한 부등호로 가르치는 것. 코드는 같은 값을 허용한다(P3-11).
- `vllm:num_requests_swapped` 지표(P3-39). 존재하지 않는다.
- "ITL = token당 지연": 한 chunk에 token이 여럿일 수 있고 그 경우 ITL 표본은 하나다. "TPOT 평균 = ITL 평균"도 항상 맞지 않는다(P3-27, P3-30).
- 서버 지표와 `vllm bench serve` 지표를 같은 정의로 섞어 비교하는 것. 서버 TTFT는 API server 도착 기준, 벤치마크 TTFT는 클라이언트 전송 기준이다(P3-26, P3-31).
- 코드에 등록된 Counter 이름을 `/metrics`에서 그대로 찾는 것. 노출 이름에는 `_total`이 붙는다(P3-38). 라이브러리로 확인했고 vLLM 서버 출력으로 본 것은 아니므로, 노트북에서는 두 형태를 모두 읽는다.
- A100에서 큰 `max_num_batched_tokens`가 처리량을 낮춘다는 말을 모델·TP 조건 없이 하는 것. PR 표는 Llama 70B TP=2 +36%, TP=4 -2%다(P3-05).
- multi-GPU의 NCCL, 통신 비용, TP 크기별 성능 수치: 블로그가 다루지 않고 이 노드도 문서의 일반 안내까지만 확인했다(P3-16, P3-17).
- #17546과 #8779의 효과 수치를 대조 없이 인용하는 것(제목과 범위만 확인됨). #17885와 #6883은 PR 본문 수치를 조건과 함께 인용할 때만 쓴다.
