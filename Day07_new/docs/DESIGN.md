# Day07_new 설계 문서

이 문서는 수강생용이 아니라 **노트북과 `vllm_lab/`을 만드는 사람을 위한 계약**이다. 노트북 8개와 모듈 5개를 이 문서만 보고 만들 수 있어야 한다.

| 항목 | 값 |
|---|---|
| 기준 소스 | vLLM v0.32.0, 커밋 `5df63a7203cdb9328d824a27b682e77c7b9928be` |
| 사실의 출처 | `Day07_new/docs/SOURCES.md`, `Day07_new/docs/sources/part1.md`~`part6.md`, `pdf-diff.md`. 상태가 `미확인`인 행과 각 대장의 `수업에 쓰지 말 것` 절은 사실이 아니다 |
| 실행 증거 | 없음. 서버를 띄운 적이 없다. CPU에서 돌린 클래스 결과는 `real-diff` 노드가 `Day07_new/docs/REFERENCE_RUN.md`에 남기며, 그 파일이 말하는 범위까지만 쓴다 |
| 수강생 | GPU가 없는 기업 엔지니어. 앞 4시간은 이론으로 vLLM을 제대로 이해하는 시간이다 |

표기: 이 문서의 `vllm/...:N` 은 v0.32.0 소스 루트 기준 코드 위치다. 노트북에는 저작 규칙 2번의 permalink로 펼쳐 넣는다. `P3-17(미확인)`처럼 괄호가 붙은 ID는 대장 상태가 미확인이다.

---

## 수업 흐름

### 관통선: GLM-5.3-Flash 요청 한 건의 여정

수강생이 끝에 자기 말로 설명해야 하는 것은 하나다. **"요청 한 건이 서버 안에서 어디를 지나고, 각 정거장에서 무엇이 결정되는가."** 모든 Part는 이 여정의 한 구간을 확대한다.

| 정거장 | 어디서 | 무엇이 일어나나 | 객체 | 다루는 Part |
|---|---|---|---|---|
| 1 HTTP 수신 | API server | route가 요청을 받고 handler로 넘긴다 | `ChatCompletionRequest` | 1, 6 |
| 2 렌더링·tokenize | API server | chat template 렌더링, token 변환, 생성 한도 계산 | `EngineInput` | 1, 5, 6 |
| 3 ADD 전송 | API server → EngineCore | 결과 queue를 먼저 등록하고 ZMQ로 보낸다 | `EngineCoreRequest` | 1 |
| 4 대기 | EngineCore | `Request`로 바뀌어 waiting에 들어간다 | `Request` | 1, 3 |
| 5 schedule | EngineCore | 예산과 KV block을 배정한다. prefix cache를 조회한다 | `SchedulerOutput` | 2, 3 |
| 6 forward·sampling | GPU worker | KV를 쓰고 읽으며 계산한다. draft token도 여기서 검증된다 | `ModelRunnerOutput` | 2, 4 |
| 7 결과 반영 | EngineCore | 출력 token 반영, 틀린 draft 되감기, 종료 판정 | `EngineCoreOutputs` | 2 |
| 8 detokenize·파싱 | API server | 증분 detokenize, stop string 검사, reasoning·도구 파서, SSE | `RequestOutput` | 1, 3, 6 |
| 9 반납 | EngineCore | block 참조를 풀고 free queue로 되돌린다. KV 값은 남는다 | - | 2, 5 |
| 다음 턴 | client | 대화 전체를 담은 **새 요청**이 정거장 1부터 다시 시작한다 | - | 5, 6 |

### 시간표

`00`은 수업 전 10분이고, 01~04의 합 240분이 이론 블록이다.

| 파일 | Part | 분 | 묶음 |
|---|---|---:|---|
| `00-Setup.ipynb` | 사전 점검 | 10 | 수업 전 |
| `01-Serving-Basics.ipynb` | Part 1 vLLM 서빙 기초 | 60 | 이론 |
| `02a-KV-Blocks.ipynb` | Part 2 KV Cache 앞 절반 | 45 | 이론 |
| `02b-KV-Sharing.ipynb` | Part 2 KV Cache 뒤 절반 | 45 | 이론 |
| `03-Parameters-Measurement.ipynb` | Part 3 서빙 파라미터와 측정 | 50 | 이론 |
| `04-Quantization.ipynb` | Part 4 Quantization | 40 | 이론 |
| `05-Agent-Integration.ipynb` | Part 5 Local Model과 Agent | 60 | 연결 |
| `06-Tool-Calling-Errors.ipynb` | Part 6 Tool Calling 오류 | 60 | 연결 |

speculative decoding은 수업 서버가 MTP를 쓰므로 Part 2의 `02b`에 둔다. TP와 replica는 `03`에서 짧게 다룬다.

### 각 Part가 앞에서 물려받는 것

| Part | 물려받는 것 | 새로 더하는 것 | 다음으로 넘기는 것 |
|---|---|---|---|
| 1 | 없음 | 여정 지도, step, 프로세스 경계, 12개 상태 | "schedule 안에서 block을 받는다"는 빈칸 |
| 2a | 정거장 5·6의 빈칸 | block, block table, slot, packed batch, 쓰기와 읽기 | "block이 끝나면 어떻게 되나" |
| 2b | block과 block table | ref_cnt, free queue, hash 사슬, preempt, draft 되감기, hybrid | preempt와 prefix hit의 비용 |
| 3 | schedule의 빈칸과 preempt | 예산, 기본값, chunked prefill, 지표, `/metrics` | "block 하나의 byte 수가 용량을 정한다" |
| 4 | block byte 식과 용량 | 가중치와 KV dtype의 분리, 체크포인트 | 서버는 다 봤다. 이제 client 쪽 |
| 5 | hash 사슬, 반납 뒤 남는 KV | 턴마다 새 요청, 무엇이 재사용을 깨는가, `cached_tokens` | 도구 호출은 턴 경계를 만든다 |
| 6 | 정거장 2·8, 턴 경계 | 도구 호출을 층으로 진단 | Day07 실습 파일 |

### 고정 예제 (수업 자체의 숫자)

모든 노트북은 아래 이름과 숫자를 쓴다. 블로그의 request 이름과 숫자는 쓰지 않는다. 요청 이름은 `doc`, `faq`, `chat`이다. `doc`이 관통선의 GLM-5.3-Flash 요청이다(프롬프트를 token으로 바꾼 길이 54는 수업이 정한 값이고 실제 tokenizer 결과가 아니다).

**E1, 한 step (02a, 03).** `num_blocks=12`, `block_size=16`, 예산 `max_num_batched_tokens=32`, threshold 0. 직전 상태는 다음과 같다.

| 요청 | 전체 token | 계산한 token | block table | 위치 |
|---|---|---|---|---|
| `chat` | 34 | 33 | `[1, 2, 3]` | running |
| `doc` | 54 | 32 | `[4, 5]` | running |
| `faq` | 20 | 0 | `[]` | waiting |

running을 먼저 돌면 `chat` 1, `doc` 22(새 block `[6, 7]`), 남은 9는 `faq`(새 block `[8]`)다. 합 32다.

| 배열 | 값 |
|---|---|
| `query_start_loc` | `[0, 1, 23, 32]` |
| `positions` | `[33] + [32..53] + [0..8]` |
| `seq_lens` | `[34, 54, 9]` |
| slot 예 | `chat` 33 → 49, `doc` 32 → 96, `doc` 37 → 101, `doc` 48 → 112, `doc` 53 → 117, `faq` 0 → 128, `faq` 8 → 136 |

packed 배열 안의 요청 순서는 이 시뮬레이터가 배정한 순서다. 실제 순서는 대장에 없으므로 "확인이 필요합니다"라고 적는다.

**E2, hash (02b, 05).** `doc`(54 token)을 끝낸 뒤 같은 프롬프트: 적중 3 block 48 token, 다시 계산 6 token. 프롬프트가 정확히 48 token이면 상한 47 때문에 적중 2 block 32 token, 다시 계산 16 token. 20번째 token부터 다르면 적중 1 block. salt가 다르면 적중 0.

**E3, 반납 순서 (02b).** `doc`이 생성까지 마쳐 62 token, block table `[4, 5, 6, 7]`이고 앞 3개만 hash가 있다. 역순 반납이므로 7은 hash가 없어 queue 앞으로, 6, 5, 4는 이 순서로 queue 뒤로 간다. 꽉 차지 않은 7이 가장 먼저 재사용되고, hash가 있는 것 중에서는 꼬리 쪽 6이 먼저 쫓겨난다.

**E4, draft 되감기 (02b).** `K=5`(MTP). `doc`: 전체 62, 계산 61. 이번 step 계산은 `1 + 5 = 6` token이고, lookahead 5를 더해 `61 + 6 + 5 = 72`칸이 필요하므로 block 5개다. 계산 수는 67이 된다. 검증 결과 생성 token이 3개면 받아들인 draft 2, 거부 3이고 계산 수는 64, 전체 수는 65다. 다음 step은 position 64 한 token을 계산해 draft가 썼던 slot을 덮어쓴다. block은 돌려주지 않는다.

**E5, 메모리 (02a, 04).** 가상 모델 `toy-8L`: MHA, 8층, head 8, head 차원 64. GLM-5.3-Flash가 아니다. BF16 block 하나는 층당 `8 * 16 * (64 + 64) * 2 = 32768` byte이고 8층이면 262144 byte다. FP8은 그 절반이다. `2*B*L*T*n*d*b`에 `B=4, L=8, T=1024, n=8, d=64, b=2`를 넣으면 67108864 byte(64 MiB)다. 가상 GPU 24 GiB, 비율 0.92, 가중치 12 GiB, 나머지 2 GiB면 KV에 8675833937 byte가 남아 BF16은 33095 block 529520 token, FP8은 66191 block 1059056 token이다. 이 값들은 산수이고 측정이 아니다.

---

## 저작 규칙

아래는 모든 노트북을 묶는 규칙이다. 어기면 노트북 노드는 완료가 아니다.

### 내용 규칙

1. **순서.** 개념 하나는 `개념 → 공식 문서 → 코드 → 직접 관찰` 순서로 쓴다. 공식 문서가 대장에 없으면(대장 칸이 `-`, `확인 못 함`, `문서에서 못 찾음`) "공식 문서에는 이 설명이 없습니다"라고 쓰고 건너뛰지 않는다. 직접 관찰은 시뮬레이터, 계산, 또는 실제 파일 읽기다.
2. **코드 인용.** `https://github.com/vllm-project/vllm/blob/5df63a7203cdb9328d824a27b682e77c7b9928be/<path>#L<n>` 형식의 permalink로만 쓴다. 범위 표기(`#L10-L20`)는 쓰지 않고, 범위는 글로 적는다. 모든 permalink는 로컬 사본 `/private/tmp/claude-501/-Users-jhj-Desktop-sds-ax-advanced-class/aca08576-7575-49cb-bdcd-5b01102e5127/scratchpad/src/vllm-v0.32.0`에서 그 줄을 열어 확인한다. 줄 번호가 대장과 다르면 코드가 맞고 차이를 보고한다. `rust/`, `docs/` 경로도 같은 형식이다.
3. **블로그 인용.** 절 제목과 URL로만 가리킨다. 문장, 예시 request, 풀이, 그림 설명을 옮기거나 번역하지 않는다. 설명과 풀이는 전부 우리 말과 위 고정 예제로 쓴다. 블로그의 예시 request와 숫자는 어떤 형태로도 쓰지 않는다. 노트북 끝 근처에 아래 형식의 읽기 표를 둔다. **표 머리글은 정확히 `블로그 절`이어야 한다.** `tests/check_sources.py`는 이 이름의 열만 검사에서 뺀다. 절 제목을 표 밖 문장에 쓰면 검사가 실패할 수 있다. 검사는 41자 이상 연속 일치와 15자 이상 조각의 유사도 0.80을 본다. PR 문구를 인용하다가 걸리기도 하므로, 걸리면 인용을 우리 말로 풀어 쓴다. 검사 목록을 늘려 통과시키지 않는다.

   ```markdown
   ## 블로그 함께 읽기

   「Inside vLLM: 서버 시작부터 KV cache까지 소스 코드 톺아보기」, Jongsu Liam Kim, https://blog.liam.kim/posts/2026/10/Inside-vLLM/ (절 제목으로만 참조합니다).

   | 블로그 절 | 읽을 때 볼 점 |
   |---|---|
   ```

   블로그가 코드와 다른 행(`SOURCES.md`의 `블로그·코드 차이`)은 블로그 서술을 근거로 쓰지 않고 "읽을 때 볼 점"에 어느 쪽이 맞는지 적는다. `04`는 블로그에 양자화 절이 없으므로 이 절을 두지 않고 그 사실을 한 줄 적는다(`part4.md` 머리말).
4. **왜 이렇게 설계했나.** 각 번호 절은 `**왜 이렇게 설계했나.**`로 시작하는 문단으로 끝낸다. 대장에서 확인된 PR, 이슈, 코드 주석, 문서 문장만 쓴다. 이유를 확인하지 못했으면 지어내지 말고 "이유는 대장에서 확인되지 않았습니다"라고 쓴다. 부분 확인인 PR(#9826, #25266, #8204)은 확인된 범위만 말한다.
5. **근거 목록.** 각 노트북에 `## 참고한 근거`를 두고 쓴 ID를 모두 적는다(`P2-04` 형식). 미확인 ID는 같은 셀에 `미확인`이라는 단어가 함께 있어야 한다. 본문에서도 `P3-17(미확인)`처럼 붙여 쓴다.
6. **측정이 아닌 수.** 출처가 측정한 수가 아니면 측정처럼 쓰지 않는다. 출처가 측정한 수는 조건을 같이 적는다. 예: PR #6883의 표는 Llama-3-8B-Instruct, 1xH100, 10 QPS 조건이다.
7. **강사 메모.** Day07 README의 2026년 9월 값(`Day07/README.md:78-80` 등: 78초 크래시 루프, 15~20분 기동, 다운로드 약 300초)은 반드시 `2026-09-15 강사 메모, v0.28 dev`라는 표지와 함께만 쓴다. 약 306 GiB 가중치는 레시피에도 있으므로 R-06으로 인용해도 된다.
8. **Python frontend와 수업 서버.** 본문의 경로 설명은 v0.32.0의 Python frontend 기준이다. 수업 Pod는 `Day07/README.md:75` 기준 v0.28.1rc1 dev 빌드이고(R-01), 레시피 기본 명령은 Rust frontend를 켠다(P1-49). 수업 Pod의 frontend는 확인되지 않았다(`part6.md` 적용 범위 전제). `01`, `05`, `06`은 이 차이를 처음 나오는 곳에 callout으로 적는다. 노트북은 "수업 서버가 이렇게 동작한다"고 쓰지 않는다. 이 차이는 `### 문서와 코드가 다를 때`와 별개로 `### 수업 서버와의 차이` 제목으로 적는다.
9. **시뮬레이터는 교육용 모델이다.** `vllm_lab`의 결과를 보여 주는 첫 셀 앞 문단에 "이것은 vLLM이 아니라 수업용 모델입니다"라고 쓰고, 무엇을 모델링하지 않았는지 적는다. 시뮬레이터 출력은 "vLLM이 이렇게 동작했다"가 아니다. `reference_kv.json`이 `status: ran`이면 그 범위에서만 "실제 클래스와 같은 결과"라고 쓴다.
10. **네트워크와 키.** 코드 셀은 네트워크를 부르지 않고 키가 필요 없다. 예외는 `05`와 `06`의 `RUN_POD = False` 보호 셀뿐이다. 보호 셀 앞 문단에 "저자는 이 셀을 서버에 대고 실행해 본 적이 없습니다"라고 쓴다. `01`의 실패 재현은 루프백 소켓 `bind`만 하고 접속하지 않는다.
11. **슬라이드 비의존.** 노트북은 PDF 없이 읽혀야 한다. `### PDF에서는` 표로 장 번호를 가리킬 수 있고, 대장 `pdf-diff.md`와 다른 곳은 어느 쪽이 맞는지 쓴다.
12. **`.env`.** 값을 출력하지 않는다. `view.env_status`로 설정됨과 미설정만 말한다. 실제 RunPod 호스트 문자열은 자리 표시자로도 쓰지 않는다.
13. **용어.** 루트 `AGENTS.md` 2절의 한국어 용어를 쓴다. 근거, 원문, 적재, 예산, 인용 등이다. 대장 용어(`prefill`, `decode`, `preempt`, `token`, `block`, `slot`)는 영어 그대로 쓴다. 코드 이름은 번역하지 않는다.
14. **쓰지 않는 말.** 각 노트북을 쓰기 전에 해당 대장의 `수업에 쓰지 말 것`을 읽는다. 특히 "MRV2가 모든 모델의 기본", "async scheduling은 항상 켜짐", "FP8 KV로 메모리 2배", "cached_tokens를 바로 볼 수 있다", 실패 사례 후보를 "관찰됐다"고 쓰는 것을 금지한다.

### `문서와 코드가 다를 때` callout

`01`부터 `06`까지 각 노트북에 `### 문서와 코드가 다를 때` 제목의 셀을 하나 이상 둔다. 표 형식은 `| 문서가 말하는 것 | 코드가 말하는 것 | 근거 |`다. 어느 쪽이 맞는지 쓴다. 코드가 맞다. 넣을 행은 다음과 같다.

| 노트북 | 행 |
|---|---|
| 01 | P1-05 `AsyncLLMEngine` 위치, P1-08 world_size에 PCP가 곱해짐, P1-49 레시피 `glm5_next`, P1-23 worker 주석의 "opt-in" |
| 02a | P2-70 `paged_attention.md`는 역사 문서이고 가리키는 CUDA 파일이 없음, D-13 교육용 block 4와 실제 기본 16 |
| 02b | P2-69 "정확히 두 group"이 낡음, `vllm/config/vllm.py:2137` 주석의 없는 플래그(`part2.md` 수업에 쓰지 말 것 4번) |
| 03 | P3-07 0.9와 0.92, P3-11 부등호, P3-22 decode 먼저, P3-24 없는 경고 문구, P3-30 TPOT 두 식, P3-39 없는 지표 |
| 04 | P4-03 허용 dtype 목록, P4-07 "세 가지"인데 항목 둘 |
| 05 | P5-15 `reasoning` 이름 변경, P5-10 salt 길이 제한이 코드 안에서 둘로 갈림 |
| 06 | P6-07 required/named, P6-12 auto의 제약, P6-26 환경변수 |

### 셀 표지와 형식

`Day03_new/AGENTS.md` 0-1절과 같은 표지를 쓴다. 문자열이 정확해야 검사기가 센다.

| 표지 | 형식 | 규칙 |
|---|---|---|
| 예측 | markdown의 `**먼저 예측하세요.**` | 실행 전에 무엇을 적을지 구체적으로 말한다 |
| 관찰 | markdown의 `**관찰할 것.**` | 어느 칸을 읽을지 가리킨다. 답을 주지 않는다 |
| 실패 재현 | 코드 셀 첫 줄 `# 실패 재현: <무엇>` | 예외는 `try/except`로 잡아 종류와 메시지를 출력한다. 예외가 없는 실패(틀린 값, 사라지는 적중)는 틀린 값과 맞는 값을 나란히 출력한다. 다음 markdown에 `**관찰할 것.**`을 둔다. 셀이 멈추면 안 된다 |
| 직접 해보기 | `## 직접 해보기` 아래 `### 해보기 N` | 값 하나만 바꾼다. 예측을 먼저 적게 한다. 기본 실행으로 예외가 나면 안 된다 |
| 확인 질문 | `## 확인 질문` 아래 번호 목록 `1. ` | 답을 노트북에 적지 않는다 |
| 정리 | `## 정리` | 이 노트북이 넘기는 것 한 줄을 포함한다 |

첫 markdown 셀의 형식은 다음과 같다. 분 칸 합은 파일 시간과 정확히 같아야 한다. 제목에 `분`이 들어가는 열은 하나만 둔다.

```markdown
# 01. <제목>

<도입 문단>

## 학습 목표

- ...

## 수업 시간표

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | ... | 4 |

## 호출 규모

모델 호출 0회, 유료 API 호출 0회, 키와 GPU가 필요 없습니다. ...
```

노트북은 실행된 상태로 저장한다. 코드 셀에 출력이 남는 것이 정상이다. 그래서 `lab-core`의 `tests/check_notebook.py`는 `Day03_new/tests/check_notebook.py`의 "저장된 출력 금지"와 `BANNED_CODE`, `BANNED_WORDS` 목록을 **가져오지 않는다**. `05`는 `langchain_openai`를 쓰고 `04`는 PDF를 가리킨다. `확인 질문`은 번호 목록(`1. `)과 글머리표(`- `)를 모두 세게 만든다.

### 분량 하한과 목표

검사기 하한은 `lab-core` 노드에 고정돼 있다. 노트북 저자는 아래 **목표**를 맞춘다.

| 파일 | 분 | 셀 하한/목표 | 코드 하한/목표 | markdown 글자 하한/목표 | 관찰 | 예측 | 해보기 | 확인 질문 | 실패 재현 |
|---|---:|---|---|---|---:|---:|---:|---:|---:|
| 00 | 10 | 8 / 12 | 3 / 5 | 2300 / 3000 | 1 | 1 | 1 | 5 | 0 |
| 01 | 60 | 45 / 56 | 18 / 22 | 13800 / 17000 | 6 | 3 | 2 | 6 | 2 |
| 02a | 45 | 34 / 42 | 14 / 17 | 10350 / 12500 | 5 | 3 | 2 | 6 | 2 |
| 02b | 45 | 34 / 42 | 14 / 17 | 10350 / 12500 | 5 | 3 | 2 | 6 | 2 |
| 03 | 50 | 38 / 46 | 15 / 18 | 11500 / 14000 | 5 | 3 | 2 | 6 | 2 |
| 04 | 40 | 30 / 37 | 12 / 15 | 9200 / 11000 | 4 | 2 | 2 | 5 | 1 |
| 05 | 60 | 45 / 56 | 18 / 22 | 13800 / 17000 | 6 | 3 | 2 | 6 | 2 |
| 06 | 60 | 45 / 56 | 18 / 22 | 13800 / 17000 | 6 | 3 | 2 | 6 | 2 |

관찰, 예측, 해보기, 확인 질문, 실패 재현 칸은 이 설계가 요구하는 최소다. `00`의 확인 질문 5개는 검사기 하한(2)보다 많다. 이 설계가 정한 값이다.

### 모든 노트북의 공통 끝부분

순서는 `## 직접 해보기` → `## 확인 질문` → `## 블로그 함께 읽기`(04 제외) → `## 정리` → `## 참고한 근거`다.

---

## 노트북별 설계

각 절의 `근거`는 그 절에서 쓰는 대장 ID이고, `코드`는 permalink로 펼쳐 걸 위치이며, `왜`는 절 끝 `**왜 이렇게 설계했나.**` 문단의 재료다. `코드 셀`은 순서대로 만들 셀 목록이다. 셀 이름은 설명용이고 노트북에 그대로 쓸 필요는 없다.

### 00-Setup.ipynb (10분, 수업 전)

**목표.** 설치는 루트에서 한 번, 실행은 `Day07_new/`에서 한다는 구분을 말한다. 00~04에 키와 GPU가 필요 없다는 것을 확인한다. 시뮬레이터와 그림이 도는지 본다. `RUNPOD_BASE_URL`이 05, 06의 선택 셀에만 쓰인다는 것을 안다.

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 설치와 실행 위치 | 3 |
| 2 | 키와 GPU가 필요 없는 이유 | 2 |
| 3 | 시뮬레이터 불러오기 | 2 |
| 4 | 그림이 그려지는지 확인 | 1 |
| 5 | 시간표와 `RUNPOD_BASE_URL` | 2 |

- 절 1: 루트 `uv sync --locked`, `cd Day07_new`, `uv run jupyter lab`. `Day07_new/` 안에서 `uv sync`를 하지 않는다(루트 `AGENTS.md` 3절). `Day07_new`에는 `pyproject.toml`이 없고 루트 환경을 쓴다.
- 절 2: 호출 규모 0회. 설명용 서버가 없다는 사실, 코드는 읽기만 했다는 사실(`SOURCES.md` 고정한 기준), 수업 서버와 v0.32.0을 구분해 말한다는 예고(R-01).
- 절 5: `view.env_status("RUNPOD_BASE_URL")`만 출력한다. 값은 출력하지 않는다. 미설정이어도 정상이라고 쓴다. 파서 플래그 기록이 README에 없다는 점을 예고한다(R-04(미확인)).

**코드 셀.** (1) Python과 패키지 버전, `sys.prefix`, 작업 폴더 이름. (2) `import vllm_lab`과 5개 모듈 import, `vllm_lab.VLLM_VERSION`, `vllm_lab.VLLM_COMMIT` 출력. `sys.modules`에 `vllm`, `torch`가 없음을 출력. (3) `kv_sim.KVManagerSim`으로 `doc` 하나 스케줄하고 표 출력. (4) `view.block_grid`로 그 pool 그림. (5) `view.env_status`.

- **예측.** 셀 (3) 앞: 54 token 요청은 block 몇 개를 받고 첫 block ID는 몇인가.
- **관찰.** 표의 `block_table`, `new_block_ids` 칸. `미설정`이 실패가 아닌 이유.
- **해보기 1.** 셀 (3)의 token 수를 54에서 65로 바꾼다.
- **확인 질문.** (1) 왜 Day 폴더 안에서 `uv sync`를 하면 안 되는가. (2) 05, 06의 어떤 셀만 `.env`를 읽는가. (3) 시뮬레이터 결과와 실제 서버 결과의 차이는 무엇인가. (4) 수업 서버 버전과 이 자료의 기준 버전은 어떻게 다른가. (5) 54 token이 block 4개인 계산을 말로 설명하라.
- **블로그 함께 읽기.** 표에는 `Introduction` 한 행만 둔다.
- **근거.** P2-04, P2-08, R-01, R-04(미확인).

### 01-Serving-Basics.ipynb (60분, Part 1)

**목표.** 요청 한 건의 여정을 객체와 프로세스 이름으로 말한다. 왜 step 단위인지, 왜 프로세스를 나눴는지, 왜 포트 bind가 엔진보다 먼저인지, 왜 KV 크기를 profiling으로 정하는지 설명한다. 상태 12개를 PDF의 4개와 구분한다. MRV2와 async scheduling의 조건을 말한다.

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 요청 한 건의 지도 | 4 |
| 1 | step: 실행의 단위 | 8 |
| 2 | 프로세스 경계 | 8 |
| 3 | 서버 초기화 순서 | 11 |
| 4 | request 경로와 객체 사슬 | 11 |
| 5 | request 상태 12개 | 4 |
| 6 | Model Runner V2와 async scheduling | 5 |
| 7 | Python frontend와 수업 서버 | 3 |
| 8 | 직접 해보기, 확인 질문, 정리 | 6 |

**절 0.** 위 여정 표를 `view.lane_diagram`으로 그린다. lane은 `API server`, `EngineCore`, `GPU worker`다. 근거: P1-03, P1-27.

**절 1, step.** 개념: step은 GPU forward 한 번이고, 매 step `schedule → execute_model → sample_tokens → update_from_output`을 돈다. scheduler에는 prefill과 decode 단계가 없고 각 요청의 계산 수가 전체 수를 따라잡도록 token을 나눠 준다. 그래서 prefill 조각과 decode token이 한 step에 섞인다.
- 코드: `vllm/v1/engine/core.py:657`(`step`), `vllm/v1/engine/core.py:667`(`schedule` 호출), `vllm/v1/engine/core.py:668`(`execute_model`), `vllm/v1/engine/core.py:676`(`sample_tokens`), `vllm/v1/engine/core.py:681`(`update_from_output`), `vllm/v1/core/sched/scheduler.py:593`(단계 구분 없음 주석).
- 공식 문서: `docs/design/model_runner_v2.md:19`.
- 근거: P1-01, P1-02, P2-03.
- 왜: 이슈 #8779는 스케줄링이 공짜가 아니라는 점과 prefix caching을 일급 기능으로 둔다는 점을 밝힌다. 수치가 없으므로 수치 근거로 쓰지 않는다. `scheduler.py` 주석은 긴 프롬프트를 나누는 일, 캐시 적중, draft token이 모두 이 한 가지 틀 안에 든다고 적는다.

**절 2, 프로세스 경계.** 개념: API server, EngineCore(DP rank마다), GPU worker(GPU마다). `AsyncLLM`이 renderer, `InputProcessor`, `OutputProcessor`, EngineCore client를 만든다. EngineCore는 worker 위치를 모르고 `collective_rpc`에 메서드 이름만 넘긴다. world_size는 PP x TP x PCP이고 DP는 곱하지 않는다. 수업 서버 구성값 TP4를 넣어 계산한다(R-02, R-07).
- 코드: `vllm/v1/engine/utils.py:283`, `vllm/v1/engine/core_client.py:137`, `vllm/v1/engine/core_client.py:583`, `vllm/v1/engine/async_llm.py:158`, `vllm/v1/executor/uniproc_executor.py:90`, `vllm/v1/executor/multiproc_executor.py:164`, `vllm/config/parallel.py:945`.
- 공식 문서: `docs/design/arch_overview.md:67`, `docs/design/arch_overview.md:91`.
- 근거: P1-03, P1-04, P1-05, P1-07, P1-08, P1-09, P1-11, P1-17, R-02, R-07.
- 왜: 이슈 #6797(RFC), PR #6883의 표(Llama-3-8B-Instruct, 1xH100, 10 QPS 조건에서 `grpc` TPOT 64.15, TTFT 450.05 대 `zmq + pickle` 57.35, 298.09), PR #17546(API server 수와 engine 수를 따로 정함, 효과 수치는 쓰지 않음). PR #9826은 stop string 감지와 EngineCoreClient까지만 말한다. "EngineCore 분리 PR"이라고 단정하지 않는다.

**절 3, 서버 초기화.** 호출 순서를 그대로 걷는다. `ServeSubcommand.cmd` 모드 선택 → `setup_server`로 소켓 bind → `run_server_worker` → `build_async_engine_client`(`from_cli_args`, `create_engine_config`, `AsyncLLM.from_vllm_config`) → `MPClient.__init__`의 ROUTER, PULL bind와 `launch_core_engines` → HELLO, 소켓 주소, READY handshake → `EngineCore.__init__`(executor, KV cache, scheduler) → 입출력 thread와 READY → `run_busy_loop` → `build_and_serve`(`build_app`, `register_api_routers`, `init_app_state`, `serve_http`, `NoSignalServer`). KV 크기: `determine_available_memory` → `profile_run`, CUDA graph 추정 → KV 설정 → `compile_or_warm_up_model`. 예산은 `gpu_memory_utilization` × GPU 전체 메모리다.
- 그림: 순서만 보이는 `view.timeline`. 칸 너비는 같다. 시간이 아니라 순서라고 그림 아래에 쓴다.
- 코드: `vllm/entrypoints/cli/serve.py:54`, `vllm/entrypoints/launchers/launcher.py:378`, `vllm/entrypoints/launchers/launcher.py:391`, `vllm/entrypoints/launchers/api_server/entry.py:165`, `vllm/entrypoints/launchers/api_server/entry.py:36`, `vllm/engine/arg_utils.py:2205`, `vllm/v1/engine/core_client.py:660`, `vllm/v1/engine/utils.py:1198`, `vllm/v1/engine/utils.py:1361`, `vllm/v1/engine/core.py:1363`, `vllm/v1/engine/core.py:1340`, `vllm/v1/engine/core.py:144`, `vllm/v1/engine/core.py:261`, `vllm/v1/engine/core.py:1547`, `vllm/v1/worker/gpu_worker.py:634`, `vllm/v1/worker/gpu/model_runner.py:991`, `vllm/envs.py:328`, `vllm/entrypoints/launchers/api_server/entry.py:116`, `vllm/entrypoints/launchers/launcher.py:45`, `vllm/entrypoints/launchers/launcher.py:175`.
- 근거: P1-10, P1-12(미확인), P1-13, P1-14, P1-15, P1-16, P1-18, P1-19, P1-20, P1-21, P1-22, P1-23, P1-24, P1-25, P1-26, P1-51, D-02, D-03.
- 주의: listen 호출은 대장이 확인하지 못했다. "vLLM은 bind까지 하고 그 뒤는 Uvicorn"까지만 말한다(P1-12(미확인)). PDF 시작 로그는 설명용이고 세 숫자가 맞지 않는다는 점을 실제 로그 형식 `GPU KV cache size: N tokens, Maximum concurrency for M tokens per request: X.XXx`와 함께 보여 준다(D-02).
- 왜: 코드 주석이 Ray와의 race를 밝히고 이슈 #8204를 가리킨다(`launcher.py:391-393`, 이슈 본문은 시작 시 address in use 실패 보고). 호출 순서에서 포트 충돌이 무거운 초기화 전에 드러난다는 것이 따라 나온다. KV 크기 자동 결정은 PR #6(제목만 인용, 2023-03-12 병합), CUDA graph 메모리 반영은 PR #30515(처음엔 기본 꺼짐, v0.32.0은 `vllm/envs.py:328`에서 켜짐). Uvicorn signal은 PR #49668(race). 시작 대기 한도 600초와 레시피의 3600(P1-51). 기동 시간을 말하려면 `2026-09-15 강사 메모, v0.28 dev` 표지와 함께 15~20분을 적는다.

**절 4, request 경로.** 표로 객체 사슬을 잇는다: `ChatCompletionRequest` → `EngineInput` → `EngineCoreRequest` → `Request` → `SchedulerOutput` → `ModelRunnerOutput` → `EngineCoreOutputs` → `RequestOutput`. 각 행은 클래스 위치, 사는 프로세스, 만드는 함수다. tokenize는 API server(`render_chat_request` → `render_chat` → `get_max_tokens` → `to_sampling_params` → `generate`). 출력 쪽은 `output_handler` → `OutputProcessor.process_outputs` → `IncrementalDetokenizer`. 정상 종료는 EngineCore가, stop string과 연결 끊김은 API server가 abort로 알린다. `get_max_tokens`는 네 항의 최솟값 한 줄이고 항을 고르는 일은 생성자와 `get_diff_sampling_param`에 흩어져 있다.
- 코드: `vllm/entrypoints/openai/chat_completion/protocol.py:220`, `vllm/inputs/engine.py:266`, `vllm/v1/engine/__init__.py:109`, `vllm/v1/request.py:60`, `vllm/v1/core/sched/output.py:232`, `vllm/v1/outputs.py:267`, `vllm/v1/engine/__init__.py:259`, `vllm/outputs.py:129`, `vllm/entrypoints/openai/chat_completion/api_router.py:42`, `vllm/entrypoints/openai/chat_completion/serving.py:258`, `vllm/renderers/online_renderer.py:224`, `vllm/entrypoints/serve/utils/api_utils.py:169`, `vllm/v1/engine/async_llm.py:569`, `vllm/v1/engine/core.py:1089`, `vllm/v1/engine/async_llm.py:845`, `vllm/v1/engine/output_processor.py:412`, `vllm/v1/engine/detokenizer.py:62`, `vllm/v1/core/sched/scheduler.py:2714`.
- 근거: P1-27, P1-28, P1-29, P1-30, P1-31, P1-32, P1-33, P1-34, P1-35, P1-44, P1-45.
- 왜: 이슈 #6797 후속 과제에 증분 detokenize와 stop string의 API server 이전이 있다. PR #9826 본문의 "detokenizer에서 감지해 abort". 결과 queue를 먼저 등록하는 이유는 `vllm/v1/engine/async_llm.py:571` 주석(첫 await 전에 다른 task가 볼 수 있게)이다. 503 거절은 `vllm/exceptions.py:156` 설명대로 다른 인스턴스로 재시도하게 하려는 것이다(P3-14와 `part3.md` 설계 결정). 기본값은 거절하지 않는다(P1-34).

**절 5, 상태.** 12개 표: 대기 4, RUNNING, PREEMPTED, 종료 6. 값 비교로 종료를 판정한다는 점(`vllm/v1/request.py:391`), FinishReason 매핑(`vllm/v1/request.py:404`), preempt는 상태가 PREEMPTED이고 위치가 waiting 앞이라는 구분. 근거: P1-36, P1-37, P1-38, D-06. 왜: 코드 주석 "anything after PREEMPTED"(`vllm/v1/request.py:379`) 외의 이유는 확인되지 않았다고 쓴다.

**절 6, MRV2와 async.** `execute_model`이 hidden state를 저장하고 `None`을 돌려주면 `core.py`가 `sample_tokens`를 따로 부른다. 앞단은 `finish_requests`, `add_requests`, `update_requests`, `prepare_inputs`, `prepare_attn`이다. 조건: 환경변수가 비어 있으면 Triton이 있고 미지원 기능이 없을 때 V2. async scheduling은 None이면 자동 켜짐, 그러나 꺼지는 조합이 있다. batch queue는 PP만 써도 켜지므로 `step_with_batch_queue`가 async 전용이 아니다. 겹침은 `view.timeline`으로 그린 도식이다.
- 코드: `vllm/v1/worker/gpu/model_runner.py:1719`, `vllm/v1/worker/gpu/model_runner.py:2088`, `vllm/config/vllm.py:703`, `vllm/config/vllm.py:1585`, `vllm/v1/engine/core.py:698`, `vllm/v1/core/sched/async_scheduler.py:14`.
- 공식 문서: `docs/design/model_runner_v2.md:7`, `docs/design/model_runner_v2.md:43`.
- 근거: P1-39, P1-40, P1-41, P1-42, P1-43, D-08, D-09, D-10(미확인). 시점 "v0.29"는 D-10(미확인)이므로 P1-41의 릴리스 노트 범위까지만 말한다.
- 왜: PR #25266(도입, 본문은 persistent batch 제거와 GPU 상주 block table), PR #53183(기본값 전환, 일부 ROCm 예외), PR #19970(실험 기능, NanoFlow와 비슷한 접근), PR #27614(기본 켜기, v0.14.0).

**절 7, frontend.** `### 수업 서버와의 차이`로 쓴다. 이 노트북은 Python frontend 설명이다. Rust frontend는 `VLLM_USE_RUST_FRONTEND` 기본 0의 실험 기능이고, 켜면 tokenizer, detokenizer, 파서 주체가 Rust로 바뀌며 ZMQ 경계는 같다. 레시피 기본 명령과 v0.32.0의 차이, 수업 Pod가 어느 쪽인지 모른다는 것을 적는다. V0 제거는 사실만 쓰고 시점과 PR은 쓰지 않는다.
- 코드: `vllm/envs.py:170`, `rust/README.md:17`, `vllm/config/model.py:89`.
- 근거: P1-46, P1-47, P1-48, P1-49, R-01, R-14. 왜: 이슈 #40846, #44280(실험적, 기능 미완성), PR #62424가 v0.32.0 커밋보다 늦음. Rust 성능 수치는 쓰지 않는다.

**코드 셀(22).** (1) import와 기준 버전. (2) 여정 `lane_diagram`. (3) `doc_faq_chat()` 워크로드를 `sched_sim.run_sim`으로 돌린 step 표. (4) 그 표에서 step별 prefill/decode token 수를 뽑은 표. (5) `result.spans()` `timeline`. (6) world_size 함수(지역 함수, PP x TP x PCP)로 네 구성 표. (7) 프로세스별 책임 표. (8) 초기화 순서 표(순서, 함수, 프로세스, 줄). (9) 순서 `timeline`. (10) 실패 재현: 같은 포트 두 번 bind. (11) "bind 먼저와 나중"의 실패 비용 비교 표(순서 수를 세는 표, 시간 아님). (12) D-02의 로그 숫자 산수: `int(max_concurrency * max_model_len)`. (13) 객체 사슬 표. (14) 지역 함수 `get_max_tokens_like`(None 제외 최솟값)로 네 경우. (15) ADD 순서 표. (16) 실패 재현: 큐 한도를 넘는 admission을 지역 모사 함수로 재현(503, `max_num_queued_reqs`), "수업용 모사" 표기. (17) 12개 상태를 `enum.IntEnum`으로 옮겨 `is_finished` 확인. (18) 상태와 FinishReason 표. (19) `sched_sim`으로 preempt 사례를 돌려 한 요청의 상태 전이 event 표(`view.trace_table`). (20) MRV2 조건 표. (21) async 겹침 `timeline`(도식, 측정 아님). (22) frontend 비교 표.

- **예측(3개).** 셀 (3) 앞: `doc`의 첫 token은 몇 번째 step에 나오는가. 셀 (8) 앞: bind, 엔진 초기화, HTTP route 중 무엇이 먼저인가, 왜 그렇다고 생각하는가. 셀 (17) 앞: `FINISHED_ABORTED`와 `PREEMPTED` 중 어느 쪽이 값이 큰가.
- **관찰(6개).** step 표의 token 칸, world_size 표의 DP 행, 실패 재현의 오류 번호, 로그 산수의 비율, admission 모사의 메시지, 상태 전이 event의 `kind`.
- **실패 재현(2).** 셀 (10)과 (16).
- **해보기 1.** `max_num_batched_tokens`를 32에서 16으로 바꿔 셀 (3)을 다시 돈다. **해보기 2.** world_size 함수에서 PP를 2로 바꾼다. **해보기 3.** `get_max_tokens_like`의 override 항을 하나 바꾼다.
- **확인 질문.** (1) 프롬프트 token이 아직 남은 요청과 decode 중인 요청이 한 step에 같이 들어갈 수 있는 이유는 무엇인가. (2) `max_tokens` 초과와 stop string 종료를 판단하는 프로세스가 왜 다른가. (3) 포트가 이미 쓰이고 있을 때 어느 단계에서 실패하고 왜 그 순서가 유리한가. (4) KV 크기를 설정값이 아니라 profiling으로 정하면 무엇을 얻고 무엇이 뒤따르는가. (5) `AsyncLLMEngine` 코드를 찾는 동료에게 어느 파일을 보라고 할 것이고 왜 문서와 다른가. (6) "MRV2가 기본이다"를 정확하게 다시 말하라. (7) 수업 서버와 이 노트북의 설명이 어긋날 수 있는 지점 두 개를 들라.
- **PDF에서는.** 1장(요청 경로와 상태, Model Runner V2, 시작 로그). 고칠 곳: D-01(prefix caching은 기본 켜짐), D-02, D-06, D-08.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| step: LLM request를 쪼개는 단위 | 단계 구분이 없다는 말을 `doc` 표와 대조한다 |
| vLLM 컴포넌트 | API server와 EngineCore 수가 어떻게 정해지는지 P1-11과 비교한다 |
| 1. Server mode selection: vllm serve에서 run_server()까지 | 코드에는 `--grpc` 분기가 먼저 있다(P1-10) |
| 2. Socket bind: listen 전의 port 선점 | listen 부분은 확인되지 않았다(P1-12(미확인)) |
| 3. Engine config: CLI 인자에서 VllmConfig까지 | 03에서 다시 본다 |
| 5. EngineCore startup: model load, KV cache allocation, scheduler setup | 초기화 순서 표와 대조한다 |
| 계층별 request 객체 | 코드의 chat 경로는 `OnlineRenderer`에 위임한다(P1-27) |
| 생성 한도를 정하는 값들 | 함수 경계는 코드가 맞다(P1-32) |
| 설계 결정: 처음부터 다시 만든 Model Runner V2 | 기본값 전환 PR은 #53183이다(P1-41) |
| 설계 결정: API server에서 하는 detokenize와 stop string 검사 | 이슈 #6797과 PR #9826을 같이 본다 |

### 02a-KV-Blocks.ipynb (45분, Part 2 앞 절반)

**목표.** KV가 왜 필요한지 token 수로 말한다. block의 metadata와 값이 분리된 이유를 설명한다. position에서 slot을 손으로 계산한다. 한 step의 packed 배열을 읽는다. 쓰기 경로와 읽기 경로를 구분한다.

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 지도에서 확대: 정거장 5와 6 | 3 |
| 1 | KV가 왜 필요한가 | 5 |
| 2 | block과 `KVCacheBlock` | 7 |
| 3 | block table과 request의 연결 | 6 |
| 4 | slot 공식 | 8 |
| 5 | packed batch | 7 |
| 6 | 쓰기와 읽기, CUDA graph padding | 5 |
| 7 | 직접 해보기, 확인 질문, 정리 | 4 |

**절 1.** `kv_math.tokens_processed_without_kv(54, 8)`로 "KV 없이 매 step 전체를 다시 넣으면" 대 "KV를 쓰면"의 token 수를 센다. **이것은 수업의 산수다.** 연산량이 문맥 길이의 제곱으로 는다는 주장은 대장에 근거가 없다(P2-02(미확인)). 노트북은 제곱이라고 쓰지 않고 "다시 넣어야 할 token 수"까지만 말한다. 근거: P2-01, P2-02(미확인). 코드: `vllm/v1/attention/backends/flash_attn.py:1195`, `vllm/v1/attention/backends/flash_attn.py:1452`. 왜: 이유는 코드에 문장으로 적혀 있지 않다고 쓰고, 재사용 구조가 이후 모든 절의 전제라는 점을 말한다.

**절 2.** block 하나는 기본 16 token. `KVCacheBlock`은 값이 아니라 `block_id`, `ref_cnt`, hash, 연결 리스트 포인터, `pool`, `_block_hash_num_tokens`, `is_null`을 든다. 모든 block은 시작할 때 만들어지고 ID 0은 null block이라 할당은 1부터다. byte 식은 `num_kv_heads * block_size * (head_size + head_size_v) * dtype 크기`이고 `head_size_v`를 안 주면 `head_size`와 같다. tensor shape `[num_blocks, num_kv_heads, block_size, 2 * head_size]`. E5로 계산한다.
- 코드: `vllm/config/cache.py:72`, `vllm/config/cache.py:345`, `vllm/v1/core/kv_cache_utils.py:176`, `vllm/v1/core/block_pool.py:172`, `vllm/v1/core/block_pool.py:187`, `vllm/v1/kv_cache_interface.py:536`, `vllm/v1/kv_cache_interface.py:549`.
- 공식 문서: `docs/design/prefix_caching.md:105`, `docs/design/prefix_caching.md:122`.
- 근거: P2-04, P2-05, P2-06, P2-07, P2-08, P2-18, P2-32, D-12, D-13.
- `### 문서와 코드가 다를 때`와 `### PDF에서는`: PDF의 block 4는 교육용이고 기본은 16이다(D-13). 16이 backend별로 바뀌는 경로는 대장이 따라가지 않았다.
- 왜: `docs/design/prefix_caching.md:122`(미리 만든다), PR #9972(Python 객체를 새로 만들지 않음). #9972의 1.8배는 여기서 쓰지 않는다.

**절 3.** `Request`는 block 목록을 들지 않고 `block_hashes`와 `block_hasher`만 든다. 연결은 request ID 키다. dict는 group별 `SingleTypeKVCacheManager`가 든다. scheduler는 새 요청에 `NewRequestData.block_ids` 전체, 진행 중 요청에 `CachedRequestData.new_block_ids`만 보낸다. worker는 뒤에 붙인다. MRV2는 `BlockTables`, V1 runner는 `MultiGroupBlockTable`.
- 코드: `vllm/v1/request.py:225`, `vllm/v1/core/single_type_kv_cache_manager.py:125`, `vllm/v1/core/kv_cache_manager.py:851`, `vllm/v1/core/sched/output.py:41`, `vllm/v1/core/sched/output.py:138`, `vllm/v1/worker/gpu/block_table.py:110`, `vllm/v1/worker/gpu_input_batch.py:183`.
- 근거: P2-12, P2-13, P2-14, P2-15. 왜: PR #25266 본문의 GPU 상주 block table. 블로그 차이는 P2-12, P2-15.
- `### 문서와 코드가 다를 때`: `docs/design/paged_attention.md:3`은 스스로 역사 문서라고 밝히고, 가리키는 `csrc/attention/attention_kernels.cu`가 v0.32.0에 없다(P2-70). 개념 비유로만 쓴다.

**절 4.** 식 `block_table[position // block_size] * block_size + position % block_size`. 계산은 scheduler가 아니라 worker가 한다. MRV2는 Triton kernel `_compute_slot_mappings_kernel`, V1은 `BlockTable.compute_slot_mapping`이다. 연속이 아니어도 된다는 것을 E1의 `doc [4, 5, 6, 7]`로 본다. PDF의 예(block 4, slot 20~23, 4, 5)를 같은 함수로 재현해 D-14가 맞음을 확인한다. `slot_mapping`은 group마다 하나다.
- 코드: `vllm/v1/worker/gpu/block_table.py:273`, `vllm/v1/worker/gpu/block_table.py:348`, `vllm/v1/worker/block_table.py:153`, `vllm/v1/worker/gpu/model_runner.py:1568`.
- 근거: P2-16, P2-17, D-14. 왜: 이유 문장은 없다. block이 재사용되면 연속 배치를 유지할 수 없다는 것을 시뮬레이터로 보이고 "수업의 해석"이라고 표기한다.

**절 5.** E1을 그대로 쓴다. `kv_sim.packed_batch`로 배열을 만들고 `query_start_loc`, `positions`, `seq_lens`, `slot_mapping`, 계산할 token만 담긴 `input_ids`를 표로 본다. MRV2에서 prefill 구간은 `prepare_prefill_inputs`가, decode 구간은 직전 sampling token이 채운다. 코드: `vllm/v1/worker/gpu/model_runner.py:1430`, `vllm/v1/worker/gpu/model_runner.py:1461`, `vllm/v1/worker/gpu/input_batch.py:320`, `vllm/v1/worker/gpu/input_batch.py:374`. 근거: P2-19, P2-20, P1-02. 왜: 이미 계산한 token을 다시 넣지 않는 것이 KV의 목적이다. 그 밖의 이유는 확인되지 않았다고 쓴다.

**절 6.** 쓰기는 `slot_mapping`으로 새 K, V를 저장한다. 읽기는 kernel이 block table과 `seq_lens`로 찾는다. CUDA graph를 쓰면 token 수가 capture 크기로 올라가고 padding token의 slot은 `-1`이라 KV에 쓰이지 않는다. full 모드는 `query_start_loc`이 줄지 않게 채운다. padding이 graph에만 있는 것은 아니다. DP padding도 있다.
- 코드: `vllm/v1/attention/backends/flash_attn.py:1452`, `vllm/v1/worker/gpu/model_runner.py:1362`, `vllm/v1/worker/gpu/model_runner.py:1431`, `vllm/v1/attention/backends/utils.py:51`, `vllm/v1/worker/gpu/spec_decode/speculator.py:336`.
- 근거: P2-01, P2-21, P2-22, P2-23. 왜: FA3 등이 단조 증가를 요구한다는 `model_runner.py:1431` 주석.

**코드 셀(17).** (1) import. (2) `tokens_processed_without_kv` 표. (3) 여러 출력 길이 `view.sweep_chart`(산수, 측정 아님). (4) `BlockPool(12)` 생성, 첫 free ID와 null block. (5) `kv_math.block_bytes` E5. (6) `block_grid`(빈 pool). (7) 실패 재현: `pool.get_new_blocks(99)`로 `KVPoolExhausted`. (8) `kv_sim.reference_rows()`로 `sequential_allocate` 행. status가 ran이 아니면 "실행하지 못했다"를 그대로 보여 준다. (9) `KVManagerSim`에 `doc`, `faq`, `chat`을 E1 상태까지 스케줄한 표. (10) 그 pool `block_grid`. (11) `slot_id` 손계산 표. (12) 실패 재현: 연속이라고 가정한 잘못된 식과 맞는 식을 나란히 출력. (13) PDF 예 재현(block 4). (14) `packed_batch` 표. (15) `slot_mapping`과 block table의 대조 표. (16) `pad_to`를 준 packed batch로 `-1` 확인. (17) 체크포인트 없는 E5 메모리 표.

- **예측(3개).** 셀 (2) 앞: 54+8에서 KV 없을 때 token 수. 셀 (11) 앞: `doc` position 37의 slot을 손으로. 셀 (14) 앞: `query_start_loc`의 값.
- **관찰(5개).** 산수 표의 비율, 첫 free ID, 예외 메시지의 요청 수와 남은 수, 두 식의 차이가 시작되는 position, `-1`이 있는 칸.
- **실패 재현(2).** 셀 (7), (12).
- **해보기 1.** block 크기를 16에서 32로 바꿔 slot 표를 다시 낸다. **해보기 2.** E1의 예산을 32에서 24로 바꿔 packed 배열을 다시 낸다. **해보기 3.** `pad_to`를 40에서 64로 바꾼다.
- **확인 질문.** (1) `KVCacheBlock`에 KV 값이 없는 것이 왜 중요한가. (2) 할당 ID가 1부터인 이유는. (3) slot을 scheduler가 아니라 worker가 계산한다는 것을 코드 어디서 확인하나. (4) `doc` 53의 slot을 손으로 계산하고 위 표와 비교하라. (5) `paged_attention.md`를 어디까지 믿어도 되는가. (6) padding token이 KV를 망가뜨리지 않는 이유는. (7) 블로그의 어떤 서술이 코드와 다른가 하나를 들라.
- **PDF에서는.** 3장(KV 메모리 공식, 논리·물리 블록), 4장(Packed Token과 Slot Mapping). D-12, D-13, D-14.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| 1.1 request와 KV block의 자료구조 | `req_to_blocks` 위치는 코드가 맞다(P2-12) |
| 1.2 scheduler 출력: 한 step에 섞인 prefill과 decode | P2-14와 대조한다 |
| 1.3 step 안의 token packing | 우리 E1과 같은 배열 이름을 찾는다 |
| 1.4 block table: token 위치에서 KV cache 주소로 | P2-15의 조건을 염두에 둔다 |
| 7. CUDA graph: padding이 남는 유일한 곳 | 제목은 과장이다(P2-23) |

### 02b-KV-Sharing.ipynb (45분, Part 2 뒤 절반)

**목표.** `ref_cnt`로 공유와 반납을 설명한다. free queue의 앞과 뒤 규칙으로 eviction 순서를 예측한다. hash 사슬과 salt, 적중 상한을 손으로 계산한다. preempt가 항상 처음부터는 아니라는 것을 말한다. draft token의 되감기와 덮어쓰기를 추적한다. GLM-5.3-Flash에 왜 hybrid가 필요한지 말한다.

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 앞 노트북에서 넘어온 것 | 2 |
| 1 | `ref_cnt`: 공유와 반납 | 6 |
| 2 | free queue와 eviction | 7 |
| 3 | hash 사슬, salt, 적중 상한 | 8 |
| 4 | preempt와 recompute | 5 |
| 5 | speculative decoding과 MTP | 8 |
| 6 | hybrid KV와 GLM-5.3-Flash | 6 |
| 7 | 직접 해보기, 확인 질문, 정리 | 3 |

**절 1.** 새 block은 `get_new_blocks`에서 1, 공유되면 `touch`로 1씩 증가, `free_blocks`에서 1씩 감소. 0이 된 것만 queue로 간다. GPU 값은 지우지 않는다. 반납 경로 `_free_request` → `_free_blocks` → `KVCacheManager.free` → coordinator → group manager → `BlockPool.free_blocks`. 늦춰지는 경우(`delay_free`, async에서 GPU가 아직 쓰는 step)가 있다. 코드: `vllm/v1/core/block_pool.py:666`, `vllm/v1/core/block_pool.py:752`, `vllm/v1/core/block_pool.py:774`, `vllm/v1/core/sched/scheduler.py:2714`, `vllm/v1/core/sched/scheduler.py:2746`. 공식 문서: `docs/design/prefix_caching.md:146`. 근거: P2-31, P2-38, P2-39, P2-40, P1-45. 왜: `touch`의 주석(free 목록에 있으면 뺀다). 생성 중 새 요청이 block을 공유하는 사례(P2-48).

**절 2.** `FreeKVCacheBlockQueue`는 직접 만든 이중 연결 리스트로 중간 제거가 O(1)이다. hash 없는 block은 앞(`prepend_n`), hash 있는 block은 뒤(`append_n`). 한 요청 안에서는 역순 반납이라 꼬리가 먼저 쫓겨난다. eviction은 별도 단계가 아니라 재할당 시점에 `_maybe_evict_cached_block`이 hash를 지우는 일이다. E3를 그림으로 본다.
- 코드: `vllm/v1/core/kv_cache_utils.py:246`, `vllm/v1/core/kv_cache_utils.py:380`, `vllm/v1/core/kv_cache_utils.py:426`, `vllm/v1/core/kv_cache_utils.py:447`, `vllm/v1/core/block_pool.py:794`, `vllm/v1/core/block_pool.py:797`, `vllm/v1/core/block_pool.py:729`, `vllm/v1/core/kv_cache_manager.py:620`, `vllm/v1/core/single_type_kv_cache_manager.py:589`.
- 공식 문서: `docs/design/prefix_caching.md:124`, `docs/design/prefix_caching.md:143`.
- 근거: P2-09, P2-10, P2-11, P2-41.
- 왜: 앞쪽은 GPU locality의 LIFO, 뒤쪽은 LRU의 FIFO(주석). PR #9972의 O(1) `.remove()`와 객체를 만들지 않는 점. **#9972의 표를 연결 리스트 속도로 소개하지 않는다.** 17916.36에서 32258.08 tok/s로 오른 행은 캐시 적중 49%일 때 prefix caching 전체의 효과이고, 기준은 prefix caching이 없는 main이다. offline batch 조건이다.

**절 3.** block hash는 `(부모 hash, block의 token 튜플, 추가 key)`의 해시이고 첫 block의 부모는 `NONE_HASH`다. 그래서 같은 hash는 처음부터 그 block까지 같다는 뜻이다. salt는 시작 위치 0인 block의 추가 key에만 들어가 사슬을 타고 퍼진다. 꽉 찬 block만 hash를 얻고 등록은 `allocate_slots` 안에서 계산이 끝날 token까지 일어나므로 생성된 답변 block도 재사용된다. draft는 `request.num_tokens`까지만 세므로 들어가지 않는다. `get_computed_blocks`의 상한 `num_tokens - 1`과 block 정렬 때문에 프롬프트가 정확히 block 경계면 block 하나가 통째로 다시 계산된다. E2를 전부 돌린다.
- 코드: `vllm/v1/core/kv_cache_utils.py:647`, `vllm/v1/core/kv_cache_utils.py:695`, `vllm/v1/core/kv_cache_utils.py:941`, `vllm/config/cache.py:141`, `vllm/config/cache.py:143`, `vllm/v1/core/kv_cache_manager.py:264`, `vllm/v1/core/kv_cache_manager.py:295`, `vllm/v1/core/kv_cache_manager.py:607`, `vllm/v1/core/block_pool.py:226`, `vllm/v1/core/single_type_kv_cache_manager.py:845`.
- 공식 문서: `docs/design/prefix_caching.md:5`, `docs/design/prefix_caching.md:15`, `docs/design/prefix_caching.md:22`, `docs/design/prefix_caching.md:87`.
- 근거: P2-24, P2-25, P2-26, P2-27, P2-28, P2-29, P2-30, P2-42, P2-43, P2-44, P2-45, P2-47, P2-53, P5-05, P5-06, D-16. salt의 실제 길이 제한은 P5-10을 따른다(128자, `@ / \ NUL` 거부).
- 왜: `kv_cache_manager.py:289-294` 주석(마지막 token logits 때문, 정렬 요구, 앞으로 개선 여지). 이슈 #8779 "first-class". 기본 켜짐과 `hash_block_size`로 잘게 계산해 큰 block이 재사용하는 구조(P2-26).

**절 4.** `allocate_slots`가 `None`이면 FCFS는 `running[-1]`을 고른다. 고른 요청이 자기 자신이면 그 step에서 포기한다. `_preempt_request`는 block을 모두 반납하고 `num_computed_tokens=0`, draft 비움, 상태 PREEMPTED, waiting 앞. 그 step은 waiting을 보지 않는다. 복귀할 때 `num_computed_tokens == 0`이므로 prefix cache를 조회한다. 그래서 처음부터 전부 재계산은 최악의 경우다.
- 코드: `vllm/v1/core/sched/scheduler.py:778`, `vllm/v1/core/sched/scheduler.py:797`, `vllm/v1/core/sched/scheduler.py:842`, `vllm/v1/core/sched/scheduler.py:899`, `vllm/v1/core/sched/scheduler.py:959`, `vllm/v1/core/sched/scheduler.py:1571`.
- 공식 문서: `docs/configuration/optimization.md:47`.
- 근거: P2-34, P2-35, P2-36, P2-37, P3-23, D-07. P3-23의 "처음부터"는 P2-37로 보완해 가르친다.
- 왜: 문서가 V1 기본이 RECOMPUTE라고 밝힌다. 재계산이 더 싸다는 문장은 문서에서만 확인했고 PR은 못 봤다고 적는다(`part3.md` 설계 결정).

**절 5, speculative decoding과 MTP.** 수업 서버 구성값은 `{"method":"mtp","num_speculative_tokens":5}`이므로 여기서 다룬다(R-02). draft token은 `Request.spec_token_ids`에 붙고 `num_tokens_with_spec`에 포함돼 scheduler가 같은 틀로 계산 수를 맞춘다. `scheduled_spec_decode_tokens`를 타고 worker로 넘어가며, 줄 자리가 부족하면 뒷부분을 버리고 앞쪽만 보낸다. `allocate_slots`는 `num_lookahead_tokens`만큼 더 잡는다. 이 값은 `VllmConfig` property 한 곳에서 정하고 MTP는 K다. 추가 slot `max_num_new_slots_for_drafting`은 MTP가 0이다. 검증 뒤 `num_rejected`만큼 `num_computed_tokens`를 되돌리고, 값은 지우지 않으며 다음 step이 같은 slot을 덮어쓴다. stale 결과는 적용하지 않는다. E4를 돌린다. 방식별 표: `P2-57`.
- 코드: `vllm/v1/request.py:183`, `vllm/v1/request.py:299`, `vllm/v1/core/sched/scheduler.py:860`, `vllm/v1/core/sched/output.py:251`, `vllm/config/vllm.py:614`, `vllm/config/speculative.py:1887`, `vllm/config/speculative.py:1944`, `vllm/v1/core/sched/scheduler.py:2111`, `vllm/v1/worker/gpu/spec_decode/target_dependent_ar/speculator.py:204`, `vllm/v1/worker/gpu/attn_utils.py:139`.
- 근거: P2-49, P2-50, P2-51, P2-52, P2-53, P2-54, P2-56, P2-57, D-31, R-02. MTP가 target의 KV를 어떻게 공유하는지는 말하지 않는다. Gemma4 쪽 표는 P2-55(미확인)이고 대장은 "GLM의 MTP 층은 항상 MLA"(`part2.md` GLM 절)까지만 준다.
- 왜: 틀린 KV를 지우지 않는 이유는 주석 두 가지(거부 수를 모르는 CPU-GPU 동기화 회피, `query_start_loc`·`seq_lens` 재사용). `P2-52`는 EAGLE 계열 speculator의 주석이고 MTP는 `use_eagle`에 포함된다(P2-54). 자리 예약의 필요성은 PR #42971(첫 step에 lookahead block이 없어 DFlash drafter KV가 공유 block을 오염시킨 버그), PR #43733(scheduler 조건 수정). 예산에서 빼는 draft 자리는 PR #59468(DFlash/DSpark를 0으로, v0.32.0에는 없음).

**절 6, hybrid.** layer마다 `get_kv_cache_spec()`로 spec을 밝히고 엔진 코어가 group을 나눈다. spec이 모두 같으면 group 하나다. `KVCacheSpecKind`는 10개다. manager는 모두 `SingleTypeKVCacheManager`를 상속하고 갈리는 곳은 `get_num_skipped_tokens()`다. 메모리는 한 pool이고 block ID 하나는 한 번에 한 group만 소유하므로 같은 byte 영역을 겹쳐 쓴다. coordinator 선택 규칙과 hit 합의 반복. 끝으로 `part2.md` GLM 절의 네 층 표와 "`2*B*L*T*n*d*b`를 쓸 수 없는 다섯 이유"를 우리 말로 옮긴다. 층 구성 숫자는 대장에 없으므로 쓰지 않는다. `HybridPoolToy`와 `agreed_hit`으로 본다.
- 코드: `vllm/v1/kv_cache_interface.py:146`, `vllm/v1/core/kv_cache_utils.py:2159`, `vllm/v1/core/kv_cache_utils.py:1292`, `vllm/v1/core/kv_cache_utils.py:1428`, `vllm/v1/core/kv_cache_utils.py:1631`, `vllm/v1/core/single_type_kv_cache_manager.py:712`, `vllm/v1/core/kv_cache_coordinator.py:980`, `vllm/v1/core/kv_cache_coordinator.py:609`, `vllm/v1/core/kv_cache_coordinator.py:796`, `vllm/models/glm5next/common/kda.py:155`, `vllm/models/glm5next/common/attention.py:385`, `vllm/models/glm5next/common/attention.py:260`, `vllm/models/glm5next/common/attention.py:271`, `vllm/models/glm5next/common/model.py:130`.
- 공식 문서: `docs/design/hybrid_kv_cache_manager.md:55`, `docs/design/hybrid_kv_cache_manager.md:201`.
- 근거: P2-17, P2-58, P2-59, P2-60, P2-61, P2-62, P2-63, P2-64, P2-65, P2-66, P2-67, P2-68, P2-69, P2-71, D-38. 하이브리드 모델에서 prefix caching이 실제 켜지는지는 `SOURCES.md` Pod 점검 5번이 미확인으로 남긴다.
- 왜: 메모리는 하나, 규칙은 group마다(P2-63 docstring "Groups alias from byte 0"). 대가는 RFC #59117(hybrid 27B + DFlash, vLLM 0.30, 2xRTX5090 tp2에서 쓸 수 있는 KV 369,121에서 33,530 token, group 4에서 16)와 #58638. 둘 다 open인 제안이다. RFC #58638의 "GLM-5.3-Flash + DFlash2는 영향 없음"은 쓰지 않는다.

**코드 셀(17).** (1) import, 수업용 모델 고지. (2) `doc`과 같은 프롬프트의 `faq2`가 공유하는 `ref_cnt` 표. (3) 반납 뒤 표와 `block_grid`. (4) E3 반납 순서와 `free_queue_ids`. (5) event `trace_table`. (6) 압력을 주어 eviction을 일으키는 표. (7) 실패 재현: eviction 뒤 같은 요청의 적중이 줄어드는 것을 전후로 출력. (8) `request_block_hashes` 사슬 표(salt 유무). (9) E2 네 경우의 적중 표. (10) `reference_rows()`로 다섯 시나리오 표. (11) 실패 재현: pool을 줄여 `schedule`이 `None`을 돌려주면 `preempt`하는 흐름. (12) 복귀 시 적중이 있는 경우와 eviction으로 없는 경우 비교. (13) E4 draft 스케줄과 block 표. (14) `verify_drafts`와 `num_computed_tokens` 표. (15) 다음 step 덮어쓰기(`slot_contents`). (16) `HybridPoolToy` 그림과 소유 표. (17) `agreed_hit` 반복 표.

- **예측(3개).** 셀 (4) 앞: E3에서 다음에 할당될 block ID 세 개. 셀 (9) 앞: 48 token 프롬프트 재요청의 적중. 셀 (14) 앞: 받아들인 draft 2개일 때 계산 수.
- **관찰(5개).** `ref_cnt` 칸의 변화, `free_queue_ids`의 앞쪽, 적중 표의 `hit_tokens`, `num_computed_tokens`와 block table이 각각 바뀌는지, `agreed_hit`의 반복 횟수.
- **실패 재현(2).** 셀 (7), (11).
- **해보기 1.** salt 값 하나를 바꾼다. **해보기 2.** E4의 생성 token 수를 3에서 6으로 바꾼다. **해보기 3.** `num_blocks`를 12에서 20으로 바꿔 preempt가 사라지는지 본다.
- **확인 질문.** (1) block을 반납해도 다음 요청이 적중할 수 있는 이유는. (2) hash 없는 block을 앞에, 있는 block을 뒤에 두면 어떤 일이 일어나는가. (3) 프롬프트 49 token과 48 token의 재요청 적중이 어떻게 다른가. (4) preempt된 요청이 전부 다시 계산되지 않을 수 있는 조건은. (5) 틀린 draft를 왜 지우지 않는가, 그때 무엇을 믿고 덮어쓰는가. (6) `2*B*L*T*n*d*b`를 GLM-5.3-Flash에 넣으면 왜 틀린가. (7) "정확히 두 group" 문장을 어떻게 고쳐 읽어야 하는가.
- **PDF에서는.** 5장(Automatic Prefix Caching, Speculation), 3장·5장(Hybrid Attention). D-16, D-31, D-38.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| KVCacheManager: block을 나눠 주고 돌려받는 방식 | 복귀 시 재사용 여지는 P2-37이 맞다 |
| 설계 결정: 직접 만든 이중 연결 리스트인 free block queue | 수치 해석은 `part2.md` 수업에 쓰지 말 것 6번을 따른다 |
| 3. speculative decoding: draft token이 batch와 KV에 들어가는 방식 | P2-49부터 P2-53까지와 대조한다 |
| drafter별 KV cache | Gemma4 행은 P2-55(미확인)이다 |
| 설계 결정: 틀린 draft KV의 삭제 없는 덮어쓰기 | 코드 주석과 비교한다(P2-52) |
| 4. block 소유: scheduler의 할당과 worker의 쓰기 | E1과 연결한다 |
| 8. 여러 종류의 attention: KV cache group과 타입별 manager | P2-61, P2-62, P2-64의 차이를 먼저 본다 |
| 설계 결정: 메모리는 하나로, 규칙은 group마다 | RFC 두 개가 open이다 |

### 03-Parameters-Measurement.ipynb (50분, Part 3)

**목표.** `schedule()`이 한 step에 하는 일을 순서대로 말한다. 기본값이 하드웨어와 진입점에 따라 달라짐을 표로 읽는다. chunked prefill과 threshold의 교환 관계를 설명한다. TTFT, ITL, TPOT, E2EL을 코드 정의로 말하고 client와 서버 지표를 구분한다. `/metrics` 이름을 읽고 변화량으로 계산한다. 한 번에 한 변수만 바꾸는 실험을 설계한다.

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | `schedule()` 한 바퀴와 token budget | 8 |
| 2 | 기본값: 하드웨어와 진입점 | 6 |
| 3 | chunked prefill과 long prefill threshold | 8 |
| 4 | admission과 preemption | 6 |
| 5 | TTFT, ITL, TPOT, E2EL | 9 |
| 6 | `/metrics` 읽기 | 5 |
| 7 | `vllm bench serve`와 한 변수 실험 | 3 |
| 8 | TP, replica, `-O` | 2 |
| 9 | 직접 해보기, 확인 질문, 정리 | 3 |

**절 1.** `token_budget = max_num_scheduled_tokens`로 시작, running을 순회하며 `num_new_tokens = num_tokens_with_spec + num_output_placeholders - num_computed_tokens`, threshold와 남은 예산으로 자르고, `allocate_slots`, 실패하면 preempt. 그 step에 preempt가 없을 때만 waiting. waiting은 running 수가 상한이면 멈춘다. 코드의 상한 이름은 `max_num_active_reqs`이고 이것은 설정의 `max_num_seqs`에서 온다. E1을 sched_sim으로 재현한다.
- 코드: `vllm/v1/core/sched/scheduler.py:591`, `vllm/v1/core/sched/scheduler.py:593`, `vllm/v1/core/sched/scheduler.py:611`, `vllm/v1/core/sched/scheduler.py:657`, `vllm/v1/core/sched/scheduler.py:703`, `vllm/v1/core/sched/scheduler.py:899`, `vllm/v1/core/sched/scheduler.py:923`, `vllm/v1/core/sched/scheduler.py:132`, `vllm/v1/core/sched/scheduler.py:137`.
- 공식 문서: `docs/configuration/optimization.md:53`, `docs/configuration/optimization.md:60`.
- 근거: P3-01, P3-03, P3-20, P3-21, P3-22, D-17. D-17은 PDF 문구를 일치로 판정했지만 P3-22가 더 정확하다. 수업은 "running 큐 먼저, 그다음 waiting"으로 말한다.
- 왜: `scheduler.py:593-602` 주석. 이슈 #8779.

**절 2.** `max_num_batched_tokens`와 `max_num_seqs`의 기본값을 `part3.md` 파라미터 표에서 옮긴 지역 함수 `default_limits(memory_gib, device_name, entry)`로 조회한다. 진입점(`LLM_CLASS`, `OPENAI_API_SERVER`)별로 다르다. `SchedulerConfig`의 128, 2048은 테스트용이다. `--performance-mode throughput`은 안 준 값을 2배. chunked 끔일 때 올리고, `max_num_seqs*max_model_len`으로 상한. `--gpu-memory-utilization` 기본 0.92. `--max-model-len` 도출.
- 코드: `vllm/engine/arg_utils.py:2914`, `vllm/engine/arg_utils.py:2923`, `vllm/engine/arg_utils.py:2933`, `vllm/engine/arg_utils.py:2945`, `vllm/engine/arg_utils.py:3130`, `vllm/engine/arg_utils.py:3140`, `vllm/engine/arg_utils.py:3167`, `vllm/config/scheduler.py:43`, `vllm/config/cache.py:102`, `vllm/config/model.py:245`.
- 근거: P3-02, P3-04, P3-05, P3-06, P3-07, P3-08, P3-09, P1-16, D-03, D-04, D-20.
- 왜: PR #17885(코드 주석이 가리키는 PR. Llama 70B TP=2 1054.01에서 1438.49, TP=4 3053.03에서 2994.03. 본문은 원인을 말하지 않는다. 이 수치는 조건과 함께만 쓰고 "큰 값이 처리량을 낮춘다"로 일반화하지 않는다).

**절 3.** chunked prefill은 "항상 켜짐"이 아니라 모델이 지원하면 켜진다. 끄면 예산보다 긴 새 요청은 이번 step에 못 들어가고 waiting 순회가 멈춘다. 시작 때 `max_num_batched_tokens < max_model_len`이면 `ValueError`(같은 값은 허용). threshold는 기본 0이고, 경쟁자가 없으면 적용하지 않는다. adaptive는 공정 몫 아래로 내려가지 않는다. sweep으로 방향만 본다.
- 코드: `vllm/engine/arg_utils.py:2991`, `vllm/config/scheduler.py:292`, `vllm/config/scheduler.py:314`, `vllm/v1/core/sched/scheduler.py:640`, `vllm/v1/core/sched/scheduler.py:650`, `vllm/v1/core/sched/scheduler.py:708`, `vllm/v1/core/sched/scheduler.py:1155`, `vllm/v1/core/sched/scheduler.py:1159`.
- 공식 문서: `docs/configuration/optimization.md:53`, `docs/configuration/optimization.md:69`.
- 근거: P3-10, P3-11, P3-12, P3-13, D-17.
- 왜: `vllm/v1/core/sched/scheduler.py:640` 부근 주석(긴 prefill이 다른 요청을 굶기지 않게, 혼자면 전부 쓰게). 그림의 모든 값 옆에 "toy step, not measured"가 있다.

**절 4.** 두 층을 구분한다. API server의 admission(`--max-num-queued-reqs`, `--max-num-queued-tokens`, 503, 기본 None)과 scheduler의 preemption. 후자의 경로와 지표 `vllm:num_preemptions`(`log_stats` 켜짐 필요), `vllm:request_num_preemptions`. 문서의 경고 문구는 v0.32.0에 없다.
- 코드: `vllm/config/scheduler.py:92`, `vllm/config/scheduler.py:105`, `vllm/config/scheduler.py:121`, `vllm/v1/engine/async_llm.py:316`, `vllm/exceptions.py:156`, `vllm/v1/core/sched/scheduler.py:776`, `vllm/v1/core/sched/scheduler.py:1609`, `vllm/v1/metrics/loggers.py:738`, `vllm/v1/metrics/loggers.py:1010`.
- 공식 문서: `docs/serving/data_parallel_deployment.md:27`, `docs/configuration/optimization.md:34`, `docs/configuration/optimization.md:40`, `docs/configuration/optimization.md:45`.
- 근거: P3-14, P3-15, P3-23, P3-24, P3-25, P1-34, P2-37, D-07.
- 왜: 503은 다른 인스턴스로 재시도하게 하려는 선택(`vllm/exceptions.py:156-170`). `max_num_queued_tokens`의 과대 집계는 의도된 보수적 선택(`vllm/config/scheduler.py:121-132`).

**절 5, 지표.** 네 정의를 코드 그대로 쓴다.

| 지표 | client 정의(`vllm bench serve`) | 코드 |
|---|---|---|
| TTFT | 보낸 시각부터 `choices`가 있는 첫 데이터까지. text가 비어도 친다 | `vllm/benchmarks/lib/endpoint_request_func.py:436` |
| ITL | 연속한 두 chunk 간격. 같은 chunk 안의 token에 0을 만들지 않는다 | `vllm/benchmarks/lib/endpoint_request_func.py:270`, `vllm/benchmarks/serve.py:609` |
| TPOT | `(E2EL - TTFT) / (출력 token 수 - 1)`. 출력이 1개 이하면 TPOT 통계에서 빠지고 goodput에서만 0 | `vllm/benchmarks/serve.py:628` |
| E2EL | 마지막 token chunk 시각 - 시작 시각. usage 전용 chunk는 뺀다 | `vllm/benchmarks/lib/endpoint_request_func.py:443`, `vllm/benchmarks/lib/endpoint_request_func.py:462` |

서버 쪽은 측정 지점이 다르다. TTFT는 API server 도착 시각부터(`vllm/v1/metrics/stats.py:521`), ITL은 출력 이벤트 간격(`vllm/v1/metrics/stats.py:551`), TPOT은 `decode_time/(n-1)`이고 n이 1 이하면 0(`vllm/v1/metrics/stats.py:608`). MTP나 `--stream-interval` > 1이면 chunk 하나에 token이 여럿이다. 그래서 "ITL = token당 지연"은 쓰지 않는다. `sched_sim`의 `stream_interval`과 `toy_network_ms`로 차이를 만들어 보고, 같은 시각 열을 `kv_math.metrics_from_chunks`에 넣어 두 모듈 값이 같은지 확인한다.
- 공식 문서: `docs/benchmarking/cli.md:131`, `docs/benchmarking/cli.md:136`, `docs/benchmarking/cli.md:145`, `docs/design/metrics.md:55`, `docs/design/metrics.md:69`.
- 근거: P3-26, P3-27, P3-28, P3-29, P3-30, P3-31, D-36.
- 왜: `docs/benchmarking/cli.md:148-159`(0 표본을 만들지 않는 이유), `docs/design/metrics.md:75-80`(둘이 다를 수 있다).

**절 6, `/metrics`.** `part3.md` 메트릭 목록의 정확한 이름을 쓴다. Prometheus 텍스트는 수업이 **만든 표본**이고 `SimResult.to_prometheus_text()`가 만든다는 것을 셀 머리에 쓴다. 전후 스냅샷의 차이로 읽는다: `vllm:prefix_cache_hits ÷ vllm:prefix_cache_queries`(token 수 기준, 비율은 우리 해석), `vllm:time_to_first_token_seconds`의 `_sum` 변화량 ÷ `_count` 변화량. `_total` 접미사는 P3-38(미확인)이므로 `counter_suffix`로 두 형태 모두 파싱되는 것을 본다. `vllm:num_requests_swapped`는 없다. 코드: `vllm/entrypoints/serve/instrumentator/metrics.py:77`, `vllm/v1/metrics/loggers.py:499`, `vllm/v1/metrics/loggers.py:661`, `vllm/v1/metrics/loggers.py:619`, `vllm/v1/metrics/loggers.py:930`, `vllm/v1/metrics/stats.py:592`. 공식 문서: `docs/design/metrics.md:24`, `docs/design/metrics.md:58`, `docs/design/metrics.md:633`. 근거: P3-36, P3-37, P3-38(미확인), P3-39, P3-40. 왜: 이유는 확인되지 않았다고 쓴다. Prometheus Counter 이름은 라이브러리 몫이라 소스만으로 정해지지 않는다고 쓴다.

**절 7.** `--request-rate`(기본 inf), `--burstiness`, `--max-concurrency`, `--ramp-up-*`와 제약, `--percentile-metrics`, `--metric-percentiles`, `--goodput`. `--ignore-eos`. 명령 예는 실행하지 않고 텍스트로만 보인다. "한 번에 한 변수" 점검표를 표로 둔다(바꿀 값, 고정할 값, 볼 지표, 볼 카운터). `--num-prompts` 기본값은 대장이 확인하지 못했으므로 항상 명시하게 한다. 코드: `vllm/benchmarks/serve.py:1698`, `vllm/benchmarks/serve.py:1631`, `vllm/benchmarks/serve.py:1917`, `vllm/benchmarks/serve.py:1800`, `vllm/benchmarks/serve.py:1820`, `vllm/benchmarks/serve.py:803`. 공식 문서: `docs/benchmarking/cli.md:704`, `docs/benchmarking/cli.md:1255`. 근거: P3-32, P3-33, P3-34, P3-35, D-11.

**절 8.** TP는 한 모델을 쪼갠다. 기본 1. 모델이 한 장에 안 들어갈 때(P3-16). replica는 문서 안내 수준이다. DP 내부 동작을 코드로 따라가지 않았다는 것을 같은 셀에 쓴다(P3-17(미확인)). `-O`는 기본 O2, O3는 현재 O2와 같다(P3-18, D-18). attention backend는 시작 로그로 본다(P3-19, D-05, D-15). 코드: `vllm/config/parallel.py:141`, `vllm/config/vllm.py:427`, `vllm/platforms/cuda.py:446`. 공식 문서: `docs/serving/parallelism_scaling.md:8`, `docs/design/optimization_levels.md:5`. NCCL, 통신 비용, TP별 수치는 쓰지 않는다. 왜: 문서의 일반 안내까지만 확인됐다고 쓴다.

**코드 셀(18).** (1) import와 수업용 고지. (2) `e1_workload()`를 `SchedConfig(max_num_batched_tokens=32, num_blocks=11)`로 재현한 step 표(`kv_sim`의 `num_blocks=12`에서 null block을 뺀 값이다). (3) `default_limits` 표(메모리, 이름, 진입점 조합 6개). (4) `throughput` 2배와 상한 산수. (5) `mixed_workload()`를 threshold 0으로 돌린 표. (6) threshold sweep `sweep_chart`. (7) 예산 sweep `sweep_chart`. (8) 실패 재현: chunked 끔 + `max_num_batched_tokens < max_model_len`의 `ValueError`, 이어서 `validate=False`의 `SimStuck`. (9) `max_num_seqs` sweep 표. (10) pool을 줄인 preempt 표와 카운터. (11) preempt `timeline`. (12) 지표 손계산 사례: chunk 시각을 손으로 준 표를 `metrics_from_chunks`로 계산. (13) `stream_interval`을 1과 4로 비교한 ITL·TPOT 표. (14) `toy_network_ms`로 client와 서버 TTFT 차이 표. (15) `to_prometheus_text`로 만든 표본 앞부분 출력. (16) `metrics_report`로 변화량 표(`_total` 유무 둘 다). (17) 실패 재현: 없는 지표 `vllm:num_requests_swapped`가 0이 아니라 `None`. (18) 한 변수 실험 계획 표.

- **예측(3개).** 셀 (2) 앞: `faq`가 첫 step에 몇 token을 받는가. 셀 (6) 앞: threshold를 줄이면 짧은 요청의 TTFT와 긴 요청의 TTFT가 각각 어느 쪽으로 가는가. 셀 (13) 앞: `stream_interval`을 4로 하면 ITL 표본 수와 TPOT이 어떻게 되는가.
- **관찰(5개).** step 표의 예산 칸, sweep의 두 선, 예외 메시지의 비교 값, 카운터 표의 `vllm:num_preemptions`, 만든 표본의 라벨.
- **실패 재현(2).** 셀 (8), (17).
- **해보기 1.** `long_prefill_token_threshold`를 0에서 16으로 바꾼다. **해보기 2.** `max_num_seqs`를 4에서 2로 바꾼다. **해보기 3.** `toy_ms_per_token`을 0으로 바꿔 예산 sweep의 교환 관계가 왜 사라지는지 본다(이 값이 가정이라는 점을 확인한다).
- **확인 질문.** (1) "decode를 전부 먼저"가 왜 부정확한가. (2) H200급에서 `vllm serve`의 기본 예산을 어떻게 찾고, `SchedulerConfig`의 값은 왜 답이 아닌가. (3) threshold가 혼자 있는 요청에는 왜 적용되지 않는가. (4) MTP 서버에서 client ITL을 token당 지연으로 읽으면 무엇이 틀리는가. (5) 서버 TTFT와 client TTFT가 다른 것은 왜 정상인가. (6) `_total`을 코드에 고정하면 안 되는 이유는. (7) 503과 preempt는 각각 어느 프로세스의 어떤 결정인가.
- **PDF에서는.** 1장 최소 실행, 2장 프로파일별 병목, 4장 Token Budget과 Chunked Prefill, Compile, Performance Mode. D-03, D-04, D-11, D-17, D-18, D-19, D-20, D-21(미확인). 표의 시점 "v0.17.0 이상"은 D-21(미확인)이다.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| 3. Engine config: CLI 인자에서 VllmConfig까지 | 표에 없는 보정이 있다(P3-06) |
| 설계 결정: 진입점마다 다른 batch 기본값 | PR #17885 수치의 조건을 확인한다 |
| 4. Schedule: step마다 계산할 token 배정 | P3-22와 대조한다 |
| 설계 결정: prefill과 decode의 구분 없는 scheduling | `doc` 표로 다시 설명해 본다 |
| 2. chunked prefill: 긴 prompt를 여러 step에 나누기 | P3-10의 조건을 덧붙인다 |
| SSE: 응답을 조금씩 보내는 방식 | 지표 표와 잇는다 |

블로그는 측정 지표 정의와 `vllm bench serve`를 다루지 않는다(`part3.md` 블로그 절 열). 이 부분은 코드와 문서만 근거다.

### 04-Quantization.ipynb (40분, Part 4)

**목표.** 가중치 양자화와 KV dtype이 별개 결정임을 말한다. FP8 KV가 줄이는 것과 줄이지 못하는 것을 계산으로 보인다. 방법별 v0.32.0 상태를 구분한다. GLM-5.3-Flash 체크포인트를 읽고, H200 KV dtype 판단이 관찰이 아니라 코드와 레시피의 추론임을 말한다. 품질 점검표를 방법으로 쓴다.

| 절 | 내용 | 분 |
|---|---|---:|
| 1 | 두 결정: 가중치와 KV dtype | 6 |
| 2 | FP8이 줄이는 것과 못 줄이는 것 | 7 |
| 3 | KV dtype 값과 보정 | 7 |
| 4 | 가중치 양자화 방법의 현황 | 7 |
| 5 | GLM-5.3-Flash 체크포인트와 H200 | 6 |
| 6 | Quality Gate 점검표 | 4 |
| 7 | 직접 해보기, 확인 질문, 정리 | 3 |

**절 1.** `quantization_config`는 체크포인트와 모델 로드 쪽이고, KV는 `--kv-cache-dtype`(`CacheConfig.cache_dtype`)이다. 기본 `auto`는 모델 dtype을 쓴다. "INT4 모델이면 KV도 INT4"가 아닌 이유. 코드: `vllm/config/cache.py:122`, `vllm/config/cache.py:39`. 공식 문서: `docs/features/quantization/README.md:8`, `docs/features/quantization/quantized_kvcache.md:39`. 근거: P4-01, P4-02, D-29. 왜: 설정이 다른 층에 있다는 코드 사실. 설계 이유 문장은 대장에서 확인되지 않았다고 쓴다.

**절 2.** `kv_math.block_bytes`와 `capacity_from_budget`로 E5를 돌린다. dtype이 절반이면 block payload만 절반이고 가중치, activation, CUDA graph 몫은 그대로다. KV 예산이 고정인 toy에서 block 수가 약 두 배가 되는 것과 "전체 메모리 절감 2배"는 다른 말이다. 전체 절감 비율은 이 자료로 계산할 수 없다. 코드: `vllm/v1/kv_cache_interface.py:549`, `vllm/utils/torch_utils.py:87`, `vllm/v1/worker/utils.py:724`. 공식 문서: `docs/features/quantization/quantized_kvcache.md:5`. 근거: P4-10, P2-05, P3-08, D-12, D-30. 왜: 위 식 자체가 이유다. "dtype 크기" 항 하나에만 작용한다.

**절 3.** 허용 값 표(문서에 설명 있는 `auto`, `fp8`, `fp8_e4m3`, `fp8_e5m2`와 코드에만 있는 값을 구분). `fp8`은 `fp8_e4m3`과 같다. `--kv-cache-dtype-skip-layers`. 보정 없이 쓰면 scale이 모두 1.0이고 경고 로그가 나온다. 보정은 llm-compressor를 문서가 권장한다. `calculate_kv_scales`는 v0.32.0 `CacheConfig`에 없다. 언제 지워졌는지는 쓰지 않는다. 문서에 설명 없는 dtype을 검증된 선택지처럼 제시하지 않는다. 코드: `vllm/config/cache.py:123`, `vllm/config/cache.py:166`, `vllm/config/cache.py:364`, `vllm/engine/arg_utils.py:1384`, `vllm/models/kimi_k3/nvidia/mla.py:465`, `vllm/model_executor/layers/attention/attention.py:300`. 공식 문서: `docs/features/quantization/quantized_kvcache.md:18`, `docs/features/quantization/quantized_kvcache.md:23`, `docs/features/quantization/quantized_kvcache.md:29`, `docs/features/quantization/quantized_kvcache.md:43`, `docs/features/quantization/quantized_kvcache.md:73`. 근거: P4-03, P4-04, P4-05, P4-06, P4-07, P4-08, P4-09, D-24, D-25, D-26(미확인). 왜: 보정이 필요한 이유는 문서 서술(값 분포와 표현 범위, `quantized_kvcache.md:18-19`). PDF의 "v0.28에서 제거"는 시점이 D-26(미확인)이다.

**절 4.** 표: 방법, v0.32.0 상태, 근거. LLM Compressor(FP8 W8A8, INT4 W4A16 등), GPTQModel, AutoAWQ(deprecated, llm-compressor AWQ 권장), BitsAndBytes(`vllm-bnb-plugin` 필요), GGUF(매우 실험적), ModelOpt와 NVFP4(Blackwell), 그 밖 목록. FP8 문서의 "2배, 1.6배"는 조건이 없어 수치로 인용하지 않는다. 공식 문서: `docs/features/quantization/README.md:10`, `docs/features/quantization/auto_awq.md:3`, `docs/features/quantization/gptqmodel.md:3`, `docs/features/quantization/bnb.md:3`, `docs/features/quantization/gguf.md:4`, `docs/features/quantization/llm_compressor/fp8.md:3`, `docs/features/quantization/modelopt.md:19`. 코드: `vllm/model_executor/layers/quantization/` 목록과 `vllm/model_executor/kernels/linear/mxfp4/marlin.py:1`. 근거: P4-12, P4-13, P4-14, P4-15, P4-16, P4-17, D-27(미확인), D-28. 왜: 문서가 밝힌 상태까지만 쓴다. 이유는 확인되지 않았다고 쓴다.

**절 5.** 체크포인트 `quantization_config`: `quant_method` fp8, `fmt` e4m3, `activation_scheme` dynamic, `modules_to_not_convert`의 존재, `dtype` bfloat16. 가중치 약 306 GiB는 FP8 체크포인트 기준이고 런타임과 KV는 별도, BF16 변형은 약 2배. H200: `GlmMoeDsaForCausalLM`만 Blackwell에서 자동 승격되고 `Glm5Next*`는 `MODELS_CONFIG_MAP`에 없다, `FLASHMLA_SPARSE`는 head_size 512를 SM90에서 `auto/bfloat16/float16/fp8_ds_mla`만 받는다, 레시피는 Hopper가 이 모델에서 FP8 KV를 지원하지 않는다고 적는다. **결론은 "H200에서는 `--kv-cache-dtype`을 넣지 않는다"이고 이것은 기동 로그로 확인하지 않은 추론이라고 같은 셀에 쓴다.** 다른 backend가 SM90에서 `fp8`을 받는지는 대장이 읽지 않았다. NVFP4 변형은 H200 실습에 쓰지 않는다. 레시피의 14.92M, 8.87M 비교는 체크포인트 비교라는 경고만 하고 P4-11(미확인) 표기를 붙인다. 코드: `vllm/model_executor/models/config.py:43`, `vllm/model_executor/models/config.py:1063`, `vllm/v1/attention/backends/mla/flashmla_sparse.py:219`, `vllm/v1/attention/backends/mla/flashmla_sparse.py:250`. 근거: P4-15, P4-18, P4-19, P4-11(미확인), D-24, R-06, R-07. 왜: 레시피 문장과 코드의 부재 확인이 근거의 전부라고 쓴다.

**절 6.** 양자화 전후 비교 점검표(같은 입력 묶음, 품질 지표, 같은 부하의 지연, KV 사용률, preempt 수, 통과 기준을 미리 적기)를 표로 둔다. 빈 칸이 있는 **양식**이고 수치를 채우지 않는다. "이것은 vLLM 기능이 아니라 수업의 방법입니다"라고 쓴다(P4-20(미확인)). `kv_math.metrics_report` 칸과 잇는다. 왜: 이 절은 방법론이라 설계 이유 대신 "왜 수업에 넣었나"를 쓴다.

**코드 셀(15).** (1) import. (2) 두 결정 대조 표. (3) `block_bytes` BF16과 FP8. (4) `raw_kv_bytes` MHA, GQA, MQA와 dtype 표. (5) 실패 재현: `raw_kv_bytes(head_type="glm5next", ...)`가 `UnsupportedKVShape`를 내고 `glm53_kv_note()`를 가리킴. (6) `capacity_from_budget` E5 BF16, FP8. (7) GPU 메모리 구성 `bar_chart`(가상 숫자, 측정 아님). (8) 가중치만 바꾼 경우와 KV만 바꾼 경우 표. (9) 로그 형식 문자열 비교. (10) dtype 허용 값 표. (11) 보정 경로 결정 표. (12) 방법 현황 표. (13) GLM 체크포인트 config 발췌 표. (14) H200 추론 사슬 표(사실, 출처, 관찰 여부 칸). (15) Quality Gate 양식.

- **예측(2개).** 셀 (3) 앞: FP8로 바꾸면 block byte가 어떻게 되는가. 셀 (6) 앞: 가중치 12 GiB가 그대로일 때 KV 용량은 몇 배인가, 전체 메모리는.
- **관찰(4개).** dtype 칸만 바뀌는지, 예외 메시지가 가리키는 곳, `log_line`의 비율, H200 표의 `관찰 여부` 칸.
- **실패 재현(1).** 셀 (5).
- **해보기 1.** E5의 `num_kv_heads`를 8에서 2(GQA)로 바꾼다. **해보기 2.** `gpu_memory_utilization`을 0.92에서 0.85로 바꾼다.
- **확인 질문.** (1) "FP8 모델을 쓰니 KV도 FP8이다"가 왜 틀리는가. (2) FP8 KV로 block 수가 늘어도 가중치 몫이 그대로인 것을 식으로 보여라. (3) H200에서 왜 `--kv-cache-dtype fp8`을 뺐고 이 판단의 약한 고리는 무엇인가. (4) 레시피의 14.92M, 8.87M을 왜 KV dtype 효과로 말하면 안 되는가. (5) Quality Gate가 vLLM 기능이 아니라면 어디서 어떻게 돌리는가. (6) 보정 없는 `fp8`에서 일어나는 일을 문서와 코드에서 찾아라.
- **PDF에서는.** 5장(FP8 KV Cache, Weight와 KV Quantization, Weight 축소). D-24, D-25, D-26(미확인), D-27(미확인), D-28, D-29. 맞는 쪽: D-24는 Hopper 단서를 덧붙이는 쪽, D-29는 값이 더 많다는 코드 쪽.
- **블로그.** 양자화 절이 없다. 이 노트북은 블로그를 근거로 쓰지 않는다.

### 05-Agent-Integration.ipynb (60분, Part 5)

**목표.** 에이전트 루프를 서버 시점에서 설명한다. 턴마다 무엇이 재사용되고 무엇이 재사용을 깨는지 예측한다. `cached_tokens`를 보려면 어떤 조건이 필요한지 말한다. `create_deep_agent`가 매 턴 무엇을 보내는지 기록으로 본다. Day07 실습 파일에 연결한다.

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | Part 4에서 넘어온 것 | 3 |
| 1 | 서버가 보는 에이전트 | 8 |
| 2 | prefix 재사용과 깨지는 조건 | 11 |
| 3 | `create_deep_agent`가 매 턴 보내는 것 | 12 |
| 4 | `cached_tokens`와 usage | 8 |
| 5 | `cache_salt` | 5 |
| 6 | `reasoning` 필드와 effort | 6 |
| 7 | 서버로 바꿀 때 (`RUN_POD`) | 3 |
| 8 | 직접 해보기, 확인 질문, 정리 | 4 |

**절 1.** 서버에게 멀티턴은 턴마다 새 request다. client가 전체 대화를 다시 보낸다. 세션 개념은 `session_id` 필드가 있으나 KV 이벤트 메타데이터로만 가고 hash에 없다. 도구 호출을 낸 request는 거기서 정상 종료하고 다음 턴은 도구 결과를 붙인 새 요청이다. `length`로 잘린 응답은 예외다. 코드: `vllm/entrypoints/openai/chat_completion/protocol.py:223`, `vllm/entrypoints/openai/chat_completion/protocol.py:406`, `vllm/v1/core/kv_cache_utils.py:647`, `vllm/entrypoints/openai/chat_completion/serving.py:771`. 근거: P5-01, P5-02, P5-23, P6-33, P2-48. 왜: hash가 prefix를 잇는 구조라 세션이 없어도 재사용된다. 이슈 #8779 "first-class".

**절 2.** `agent_sim.run_scenario`의 시나리오를 차례로 본다: `append_only`, `system_change`, `tool_added`, `tool_order_change`, `salt_change`, `effort_in_system`, `pressure_evict`. 확정된 것과 아닌 것을 표로 구분한다.

| 깨는 조건 | 상태 | 근거 |
|---|---|---|
| 꽉 차지 않은 마지막 block (최대 15 token) | 확정 | P5-05, P2-43 |
| 전부 맞아도 상한 때문에 다시 계산 (block 경계면 16 token) | 확정 | P5-06, P2-30 |
| 첫 어긋난 block 뒤 전부 | 확정 | P2-45, P5-04 |
| system prompt 변경 | 확정 | P2-47 |
| eviction | 확정 | P2-41, P2-45 |
| 답변 재tokenize 어긋남, 턴 경계 특수 token | 미확인 | P5-07(미확인), P2-46(미확인) |
| tool 목록 변경, 순서 변경 | 미확인, toy는 tool을 앞에 렌더링한다고 가정 | P5-08(미확인) |
| effort 값 변경 | 미확인, 레시피 서술에서 나온 추론 | P5-13(미확인) |

코드: `vllm/v1/core/kv_cache_utils.py:695`, `vllm/v1/core/kv_cache_utils.py:709`, `vllm/v1/core/kv_cache_manager.py:289`, `vllm/config/cache.py:141`. 근거: P5-03, P5-04, P5-05, P5-06, P5-07(미확인), P5-08(미확인), P2-45, P2-47. 왜: 이것이 사슬 hash의 대가다. "앞이 같아야 뒤를 믿을 수 있다". 레시피 값이 prompt에 들어간다는 부분은 template을 열지 않았다고 쓴다.

**절 3.** 노트북 안에 `RecordingChatModel(BaseChatModel)`을 정의한다. `bind_tools`로 도구 스키마를 받고, `_generate`에서 `self.calls`에 system, tools, messages를 기록하고 스크립트의 `AIMessage`를 돌려준다. pydantic이 생성자에 넘긴 list를 복사하므로 **생성자에 준 변수가 아니라 `model.calls`를 읽는다.** 2026-11-01에 이 모양으로 `create_deep_agent(model=model, tools=[])`가 네트워크 없이 도는 것을 저자가 확인했다(deepagents 0.7.32, 기록된 도구 8개, system 메시지는 빈 문자열, 2번째 호출이 1번째 메시지를 앞에 그대로 둠). 노트북은 설치된 버전을 출력하고 기록을 그대로 보여 준다. `agent_sim.reuse_from_recorded(model.calls)`로 toy 적중을 계산한다. 다음 턴에 `reasoning`이 실리지 않는다는 것과 그 영향은 P5-22(미확인)이다. 요약 middleware 조건은 P5-21(미확인)이다. deepagents의 prompt caching middleware는 서버 prefix cache가 아니다(P5-25). `Day07/task.md`, `Day07/dcode_task.md:27`의 과제 1과 잇는다. 그 파일들을 수정하지 않는다. 근거: P5-19, P5-20, P5-21(미확인), P5-22(미확인), P5-23, P5-25. 왜: deepagents `graph.py`가 안내문을 넣지 않는 선택(`P5-20`), middleware 설명(`P5-25`).

**절 4.** 조건 세 겹: 서버의 `--enable-prompt-tokens-details`(없으면 `prompt_tokens_details`가 null), 스트리밍의 `stream_options.include_usage`(서버 `--enable-force-include-usage`로 강제 가능), `ChatOpenAI(base_url=...)`는 `stream_usage`가 켜지지 않으므로 `stream_usage=True`. `usage_metadata["input_token_details"]["cache_read"]`로 옮겨진다. 수업 Pod가 이 플래그를 켰는지는 기록이 없다. 조건을 판정 표로 보이는 `agent_sim.cached_tokens_visible(...)`. 코드: `vllm/entrypoints/launchers/cli_args.py:148`, `vllm/entrypoints/openai/chat_completion/serving.py:90`, `vllm/entrypoints/openai/chat_completion/serving.py:1164`, `vllm/entrypoints/serve/engine/protocol.py:121`, `vllm/entrypoints/serve/utils/api_utils.py:289`, `vllm/entrypoints/launchers/cli_args.py:154`. 근거: P5-11, P5-12, P5-17, D-01. 왜: 클라이언트 쪽은 `LC:1431-1450` 판단(대장의 `.venv` 경로 줄), 서버 쪽은 기본 False라는 코드 사실. 이유 문장은 확인되지 않았다고 쓴다.

**절 5.** salt는 시작 위치 0인 block의 추가 key에만 들어간다. 다른 salt는 아무 block도 공유하지 못한다. 실제 제한은 검증기 기준으로 128자 이하, `@ / \ NUL` 금지이고 필드 정의의 1024와 다르다. 비용: 사용자별 salt는 공통 system prompt 재사용도 없앤다(`salt_change` 시나리오). 코드: `vllm/entrypoints/generate/base/protocol.py:39`, `vllm/entrypoints/openai/chat_completion/protocol.py:485`, `vllm/v1/core/kv_cache_utils.py:647`. 공식 문서: `docs/design/prefix_caching.md:87`, `docs/usage/security.md:596`. 근거: P5-09, P5-10, P2-28. 왜: 문서의 보안 절이 격리 목적을 밝힌다.

**절 6.** v0.32.0 응답 필드는 `reasoning` 하나다. `reasoning_content`는 요청 쪽에서 바꿔 받는 호환 처리에만 있다. `ChatOpenAI`는 비표준 필드를 버리며 이것은 vLLM 버그가 아니라 클라이언트 설계다(P5-16). 그래서 사고 과정은 openai SDK로 본다. `extra_body`는 최상위로 합쳐진다. effort: 레시피 규칙(기본 max, low와 high 외는 max), `chat_template_kwargs`와 최상위 필드(P5-13(미확인), R-08, R-10). `clear_thinking`의 뜻은 설명하지 않는다(P5-14(미확인), R-09(미확인)). 수업 서버의 필드 이름은 응답으로 확인해야 한다(R-11). 첫 chunk가 `reasoning`일 수 있어 첫 visible과 TTFT가 다르다(D-36). 코드: `vllm/entrypoints/openai/chat_completion/protocol.py:79`, `vllm/entrypoints/generate/base/protocol.py:356`, `vllm/entrypoints/openai/chat_completion/protocol.py:576`, `vllm/renderers/params.py:36`. 공식 문서: `docs/features/reasoning_outputs.md:8`. 근거: P5-13(미확인), P5-14(미확인), P5-15, P5-16, P5-18, P5-22(미확인), R-08, R-09(미확인), R-10, R-11, R-12(미확인), D-36. R-12(미확인)는 P5-16의 실측으로 대체됐다고 쓴다. 왜: 문서의 이름 변경 경고.

**절 7, `RUN_POD`.** 셀 앞 문단에 "저자는 이 셀을 서버에 대고 실행해 본 적이 없습니다"를 쓴다. 첫 코드 셀은 정확히 `RUN_POD = False`로 시작한다. 뒤 셀은 전체를 `if RUN_POD:` 안에 둔다. 주소는 `view.read_env_value("RUNPOD_BASE_URL")`로만 읽고 출력하지 않는다. `ChatOpenAI(base_url=..., model="GLM-5.3-Flash", stream_usage=True, api_key="unused", timeout=95)`. `/v1/models`로 이름부터 확인하라고 쓴다(R-03). 프록시 100초는 강사 메모이고 대장에서 미확인이다(P5-24(미확인), R-13(미확인)). 파서 플래그 기록이 없다(R-04(미확인)). 왜: 수업 Pod 구성이 문서화되지 않았기 때문에 켜기 전에 확인할 항목을 `SOURCES.md` Pod 점검 항목으로 안내한다.

**코드 셀(22).** (1) import와 버전. (2) 턴별 요청 구조 표. (3) `session_id`와 hash 입력 비교 표. (4) `append_only` 표. (5) 적중 `sweep_chart`. (6) `system_change`. (7) `tool_added`, `tool_order_change`. (8) `effort_in_system`. (9) `pressure_evict`. (10) 깨는 조건 표. (11) `RecordingChatModel` 정의. (12) `create_deep_agent` 한 번 실행. (13) 호출별 도구와 메시지 표. (14) system과 tools의 sha256 전후 비교. (15) `reuse_from_recorded` 표. (16) `cached_tokens_visible` 판정 표. (17) 실패 재현: `base_url` 스트리밍에서 `stream_usage` 기본값 때문에 usage가 없는 경우를 판정 함수로, `ChatOpenAI` 객체를 만들어 `stream_usage` 값 확인(호출 없음). (18) `salt_change` 표. (19) 실패 재현: 지역 함수 `check_salt`(P5-10 규칙 옮김)에 129자와 `@`를 넣어 오류. (20) `reasoning` 필드 읽기 함수로 v0.32.0 형태 가짜 응답 처리. (21) `RUN_POD = False`와 설명. (22) `if RUN_POD:` 연결 셀.

- **예측(3개).** 셀 (4) 앞: 세 번째 턴의 적중은 전체의 얼마쯤인가. 셀 (6) 앞: system 첫 글자를 바꾸면 적중은. 셀 (15) 앞: deepagents 2번째 호출의 적중은.
- **관찰(6개).** `hit_tokens`와 `first_miss_block`, 시나리오별 차이, 기록된 도구 목록, sha256 일치 여부, `stream_usage` 값, 판정 표의 조건.
- **실패 재현(2).** 셀 (17), (19).
- **해보기 1.** `append_only`의 사용자 입력 길이를 바꾼다. **해보기 2.** `RecordingChatModel`의 스크립트에 도구 호출 하나를 더 넣는다. **해보기 3.** `cache_salt` 값을 턴 중간에 한 번 바꾼다.
- **확인 질문.** (1) 턴이 바뀌는데 서버가 대화를 기억하지 않아도 빨라질 수 있는 이유는. (2) `cached_tokens`가 null일 때 무엇부터 확인하나. (3) system prompt에 시각을 넣으면 어떻게 되나. (4) 사용자별 salt의 이득과 비용은. (5) `ChatOpenAI`로 사고 과정이 안 보이는 것이 버그가 아닌 이유는. (6) deepagents의 prompt caching middleware와 vLLM prefix cache의 차이는. (7) 이 노트북의 어떤 주장이 아직 미확인인가 두 개를 들라.
- **PDF에서는.** 6장 구조화 출력과 E2E 지연. D-36. README: R-08, R-10, R-11.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| 5. 멀티턴 대화: prefix caching을 통한 이전 턴 KV 재사용 | 세션 서술은 P5-02로 보완한다. 필드 이름은 P5-15 |
| 생성 중에 새 입력이 들어올 때 | P2-48과 대조한다 |
| 설계 결정: 기본으로 켜는 prefix caching | 조건은 P5-03 |

### 06-Tool-Calling-Errors.ipynb (60분, Part 6)

**목표.** 도구 호출을 chat template, 생성, parser, schema 검증, 실행, 네트워크 층으로 나눈다. 증상에서 층을 찾는다. GLM 파서 구조와 세 플래그의 관계를 설명한다. `finish_reason`이 스트리밍 여부에 따라 달라질 수 있음을 말한다. 실제 파서 결과와 코드 읽기 추론을 구분해 진단표를 쓴다.

| 절 | 내용 | 분 |
|---|---|---:|
| 0 | 여섯 층 지도 | 5 |
| 1 | 세 플래그의 조합 | 8 |
| 2 | 파서의 구조 | 8 |
| 3 | 구성 문자열로 본 파서 결과 | 12 |
| 4 | `tool_choice`와 strict 수준 | 7 |
| 5 | `finish_reason` | 5 |
| 6 | reasoning 파서와의 상호작용 | 4 |
| 7 | Python 경로와 Rust 경로 | 3 |
| 8 | 진단표와 `RUN_POD` | 5 |
| 9 | 직접 해보기, 확인 질문, 정리 | 3 |

**공통 표기.** `part6.md`의 모든 주장은 코드 읽기다. 각 결과에 근거 종류를 붙인다. `실제 GLM 파서, 구성 문자열, 모델 출력 아님, 라이브 서버 아님` 또는 `코드 읽기`. 후보 C1~C12를 "관찰됐다"고 쓰지 않는다.

**절 0.** 여섯 층을 `lane_diagram`으로 그린다. 정거장 2가 template, 6이 생성, 8이 parser이고 schema 검증과 실행은 client 몫이다. 근거: P6-32, `part6.md` 실패 사례 후보 머리말.

**절 1.** `agent_sim.flag_matrix()`로 네 조합과 요청 결과를 표로 본다. `--enable-auto-tool-choice`만: 시작 `TypeError`. `--tool-call-parser`만: 오류 없이 파싱이 꺼진다. 둘 다 없는 서버에 `tools` 요청: `tool_choice` 생략도 auto로 채워져 400 문구. `none`은 통과. 코드: `vllm/entrypoints/launchers/cli_args.py:523`, `vllm/parser/parser_manager.py:36`, `vllm/entrypoints/openai/chat_completion/protocol.py:951`, `vllm/renderers/online_renderer.py:253`, `vllm/renderers/online_renderer.py:669`. 공식 문서: `docs/features/tool_calling.md:163`. 근거: P6-03, P6-08, P6-09, P6-10, R-04(미확인), C1. 왜: 조용히 꺼지는 경우가 있다는 것이 진단의 함정이다. 설계 이유는 대장에서 확인되지 않았다.

**절 2.** `glm47_moe_tool_parser.py`는 14줄이고 세 값만 정한다. 파싱은 `ParserEngine` 위의 `Glm47MoeParser`다. 형식 `<tool_call>함수명<arg_key>키</arg_key><arg_value>값</arg_value></tool_call>`. `glm45`와 `glm47`은 Python에서 같은 클래스다. 파서는 API server에서 detokenize 뒤에 돈다. 엔진 기반 파서는 `skip_special_tokens`를 거짓으로 바꾼다. 인자 JSON은 파서가 만든다. 코드: `vllm/tool_parsers/__init__.py:61`, `vllm/reasoning/__init__.py:59`, `vllm/tool_parsers/glm47_moe_tool_parser.py:10`, `vllm/parser/glm47_moe.py:3`, `vllm/parser/glm47_moe.py:203`, `vllm/parser/engine/registered_adapters.py:95`, `vllm/parser/engine/adapters.py:235`, `vllm/parser/engine/parser_engine.py:227`, `vllm/entrypoints/openai/chat_completion/serving.py:666`, `vllm/entrypoints/openai/chat_completion/serving.py:997`. 근거: P6-01, P6-02, P6-05, P6-06, P6-18, P6-31, P6-32, P6-36. `hermes_tool_parser.py`로 설명하지 않는다. 왜: 선언형 엔진 위의 얇은 껍질 구조는 코드 사실. 이유 문장은 없다고 쓴다.

**절 3.** `agent_sim.reference_status()`로 상태를 먼저 본다. `status`가 `ran` 또는 `partial`이면 `parser_case_table()`을 보이고 각 행에 위 표지를 붙인다. `not_run`이면 그 이유를 그대로 출력하고 코드 읽기 표로 대신한다. 케이스 7개와 후보의 대응은 `vllm_lab 계약`의 표를 따른다. 설명: 전이표에 없는 조합은 현재 상태의 텍스트, 잘리면 `finish()`가 닫는다, 선언 안 된 이름은 조용히 버린다, 값 변환 실패는 문자열로 둔다, 필수 인자를 거절하는 코드는 읽은 범위에서 못 찾았다. 비스트리밍과 스트리밍이 같은 결과라는 보장은 없다. 코드: `vllm/parser/engine/streaming_parser_engine.py:294`, `vllm/parser/engine/streaming_parser_engine.py:310`, `vllm/parser/engine/streaming_parser_engine.py:412`, `vllm/parser/engine/parser_engine.py:415`, `vllm/parser/engine/parser_engine.py:1105`, `vllm/parser/engine/parser_engine.py:1130`, `vllm/parser/glm47_moe.py:54`, `vllm/parser/glm47_moe.py:66`, `vllm/tool_parsers/utils.py:356`, `vllm/tool_parsers/utils.py:1153`, `vllm/parser/abstract_parser.py:833`, `vllm/parser/abstract_parser.py:849`. 공식 문서: `docs/features/tool_calling.md:200`. 근거: P6-16, P6-17, P6-18, P6-19, P6-20, C2, C3, C4, C5, C6, C7. 잘린 호출을 "버려진다"고 단정하지 않는다(소스 주석과 코드 읽기가 다르다). 왜: 서버가 검증을 해 주지 않을 수 있으므로 client 쪽 검증을 설계한다(`agent_sim.validate_tool_args`).

**절 4.** `auto`, `required`, 이름 지정, `none`을 표로 비교한다. GLM은 `supports_required_and_named=False`라 `adjust_request`가 JSON 스키마 강제를 걸지 않는다. 대신 구조화 태그가 유일한 제약이다. `auto`도 파서 기본이 FUNCTION이라 껍데기가 제약된다. strict 도구만 인자 스키마가 고정된다. `--tool-strict-level`. `VLLM_ENFORCE_STRICT_TOOL_CALLING=0`이면 GLM의 required/named에 제약이 남지 않는다. 문법 마스크는 temperature와 무관하다. `tool_choice="none"`도 기본은 도구 정의를 프롬프트에 넣는다. 코드: `vllm/tool_parsers/abstract_tool_parser.py:50`, `vllm/tool_parsers/abstract_tool_parser.py:144`, `vllm/tool_parsers/abstract_tool_parser.py:189`, `vllm/parser/abstract_parser.py:394`, `vllm/parser/abstract_parser.py:503`, `vllm/parser/abstract_parser.py:521`, `vllm/parser/abstract_parser.py:597`, `vllm/tool_parsers/structural_tag_registry.py:175`, `vllm/tool_parsers/structural_tag_registry.py:1080`, `vllm/tool_parsers/tool_strict_level.py:7`, `vllm/envs.py:1861`, `vllm/entrypoints/launchers/cli_args.py:119`, `vllm/entrypoints/launchers/cli_args.py:131`. 공식 문서: `docs/features/tool_calling.md:88`, `docs/features/tool_calling.md:105`, `docs/features/tool_calling.md:116`, `docs/features/tool_calling.md:125`, `docs/features/tool_calling.md:137`, `docs/features/tool_calling.md:143`. 근거: P6-07, P6-11, P6-12, P6-13, P6-24, P6-25, P6-26, P6-27, P6-34, C9. 왜: 문서가 왜 그 경로를 두는지(`docs/features/tool_calling.md:112-125`).

**절 5.** `agent_sim.finish_reason_rule`로 표를 낸다. 비스트리밍: auto에서 호출이 추출되면 엔진이 `length`여도 `tool_calls`. required는 엔진 `stop`일 때 `tool_calls`. named는 엔진 값. 스트리밍: 도구 델타가 나갔고 named가 아니고 엔진이 `stop`일 때만 `tool_calls`. 그래서 같은 잘림이 두 방식에서 다르게 보일 수 있다(코드 읽기). 코드: `vllm/entrypoints/openai/chat_completion/serving.py:1016`, `vllm/entrypoints/openai/chat_completion/serving.py:1098`, `vllm/entrypoints/openai/chat_completion/serving.py:674`, `vllm/entrypoints/openai/chat_completion/serving.py:771`. 근거: P6-14, P6-15, P6-33. 왜: 코드 주석이 OpenAI API의 의미를 따른다고 밝힌다(`serving.py:1096-1098`).

**절 6.** 템플릿은 생각이 항상 켜지고 `enable_thinking=false`는 경고 후 무시된다. `--reasoning-parser`는 구조화 출력 설정에도 복사된다. 이 값이 없으면 문법이 첫 token부터 적용될 가능성이 있다(P6-23, 코드 읽기 가설, C8). `--reasoning-parser`가 없을 때 생각이 content에 섞이는지는 P6-21(미확인)이다. 응답 필드는 `reasoning`이다. 코드: `vllm/parser/glm47_moe.py:83`, `vllm/parser/glm47_moe.py:212`, `vllm/engine/arg_utils.py:2167`, `vllm/v1/structured_output/__init__.py:248`, `vllm/parser/abstract_parser.py:155`. 근거: P6-21(미확인), P6-22, P6-23, P6-31, C8. 왜: `abstract_parser.py:155` 설계 주석.

**절 7.** `### 수업 서버와의 차이`로 쓴다. Python은 부분 인자를 살릴 수 있는데 Rust는 완결된 호출이 파싱돼야 하고 `incomplete GLM MoE tool call` 오류를 돌려준다. 그 오류의 HTTP 모양은 P6-30(미확인)이다. 이름 혼용은 P6-04(미확인)이다. `glm5_next`의 뜻은 설명하지 않는다(P6-35(미확인)). 수업 Pod의 frontend를 모르므로 P6-16~P6-19를 Pod 동작으로 단정하지 않는다. 코드: `rust/src/parser/src/tool/glm_xml/mod.rs:130`, `rust/src/parser/src/tool/error.rs:14`, `rust/README.md:1`, `vllm/envs.py:1475`. 근거: P6-04(미확인), P6-28, P6-29, P6-30(미확인), P6-35(미확인), C10.

**절 8.** 진단표 `agent_sim.diagnosis_rows()`: 사례, 층, 증상(가설), 볼 곳, 근거 종류, 재현 조건. C1~C12 전체. C11의 렌더링 확인 엔드포인트는 존재를 확인하지 않았다고 쓴다. C12는 client 코드 문제다. 이어서 `RUN_POD = False` 셀과 `if RUN_POD:` 셀(더미 도구 하나, `SOURCES.md` Pod 점검 4번 모양, `tool_calls`와 `finish_reason`, `reasoning` 읽기). 앞 문단에 "저자는 이 셀을 서버에 대고 실행해 본 적이 없습니다"를 쓴다.

**코드 셀(23).** (1) import. (2) 여섯 층 `lane_diagram`. (3) `flag_matrix` 표. (4) 400 문구 찾기 표(코드 읽기 표지). (5) 파서 클래스 대응 표. (6) `glm47` 형식 문자열을 구성해 보여 주기(파서 실행 아님). (7) `reference_status`. (8) `parser_case_table`. (9) 케이스별 입력과 출력 비교 표. (10) 실패 재현: `get_parser_case`에 없는 ID, 또는 `tmp` 파일로 `not_run`을 만들어 `CaseNotRun`을 보임. (11) 잘림 사례를 두 표로(인자 쌍이 닫힌 위치별). (12) 선언 안 된 이름 사례. (13) `validate_tool_args`로 타입과 필수 인자 검증. (14) 실패 재현: 잘못된 인자를 검증 없이 도구로 넘겨 예외가 나는 지역 도구와, 검증을 끼운 뒤의 메시지 비교(C4, C5, C12). (15) `tool_choice` 비교 표. (16) strict 수준 표. (17) `finish_reason_rule` 표. (18) 잘림 상황의 스트리밍, 비스트리밍 대조. (19) reasoning 관계 표. (20) Python과 Rust 비교 표. (21) `diagnosis_rows` 표. (22) `RUN_POD = False`. (23) `if RUN_POD:` 더미 도구 호출.

- **예측(3개).** 셀 (3) 앞: `--tool-call-parser`만 주면 시작에 실패하는가. 셀 (9) 앞: `unknown_tool`은 어떤 결과인가. 셀 (17) 앞: 잘린 호출의 `finish_reason`을 두 방식에 대해 예상하라.
- **관찰(6개).** 조합별 실패 시점 칸, `근거 종류` 칸, `tool_calls` 개수, `arguments`의 값 타입, `finish_reason` 차이, 진단표의 `재현 조건`.
- **실패 재현(2).** 셀 (10), (14).
- **해보기 1.** `validate_tool_args`의 스키마에서 한 인자 타입을 바꾼다. **해보기 2.** `finish_reason_rule`에 `tool_choice="required"`를 넣는다. **해보기 3.** 진단표에 자기 조직에서 본 증상 한 줄을 층과 함께 추가한다.
- **확인 질문.** (1) `tool_calls`가 비었고 `completion_tokens`가 크다면 어느 층부터 보나. (2) `--tool-call-parser`만 준 서버의 함정은 무엇인가. (3) GLM에 문서의 required/named 설명이 맞지 않는 이유는. (4) 서버 200 응답의 인자를 그대로 도구에 넘기면 안 되는 이유는. (5) `finish_reason`이 `tool_calls`인데 인자가 잘렸을 수 있는 경로를 설명하라. (6) Rust frontend에서 이 노트북의 무엇을 그대로 믿으면 안 되는가. (7) 표의 어느 행이 실제 파서 결과이고 어느 행이 코드 읽기인가.
- **PDF에서는.** 6장 구조화 출력. D-36. README: R-04(미확인), R-08.

| 블로그 절 | 읽을 때 볼 점 |
|---|---|
| 6. Detokenize: token ID에서 응답까지 | 필드 이름은 `reasoning`이다(P6-31) |
| structured output: grammar bitmask로 출력 형식을 강제하는 방식 | P6-34와 대조한다 |
| 1. Server mode selection: vllm serve에서 run_server()까지 | Rust frontend는 기본 경로 밖이다(P6-28) |

---

## vllm_lab 계약

병렬 노드가 서로 묻지 않고 구현한다. 이름, 인자, 반환 모양은 이 절이 정답이다. 고쳐야 하면 노드를 실패로 끝내고 이 문서를 고친다.

### 공통 규칙

| 규칙 | 내용 |
|---|---|
| 의존성 | 표준 라이브러리, numpy, pandas, matplotlib만. `vllm`, `torch`, `IPython`을 import하지 않는다 |
| 모듈 사이 import | `view`는 `vllm_lab` 상수만. `kv_sim`, `sched_sim`, `kv_math`는 서로 import하지 않는다(`vllm_lab` 상수는 가능). `agent_sim`만 `kv_sim`을 import한다 |
| 파이썬 | 3.13 기준, `from __future__ import annotations` |
| docstring | `kv_sim`, `sched_sim`, `agent_sim` 모듈 docstring은 한국어로 교육용 모델임을 밝히고 영어 단어 `teaching`을 포함한다 |
| 주석 | 모델링한 규칙마다 `vllm/...:줄`을 인용한다. 줄은 로컬 사본에서 확인한다 |
| 오류 메시지 | 한국어. 무엇이 모자라는지 숫자를 포함한다 |
| 모델링하지 않은 것 | `kv_sim`, `sched_sim`, `agent_sim`은 `NOT_MODELED: tuple[str, ...]`(한국어 문장)을 공개한다. 노트북이 출력할 수 있다 |
| 측정 금지 | 모든 시간 값은 선언한 toy 상수의 결과다. 함수와 칸 이름에 `toy` 또는 `_ms`를 쓰고, 측정이라고 쓰지 않는다 |

### `vllm_lab/__init__.py`

하위 모듈을 import하지 않는다(병렬 노드가 쓰는 중이다).

```python
VLLM_VERSION = "0.32.0"
VLLM_COMMIT = "5df63a7203cdb9328d824a27b682e77c7b9928be"
DEFAULT_BLOCK_SIZE = 16
ROOT: pathlib.Path  # Day07_new 폴더
DATA_DIR: pathlib.Path  # ROOT / "data"
```

### trace event 모양

`kv_sim`과 `sched_sim`의 `events`는 아래 dict의 list다. 키는 정확히 다섯이다.

```python
{"step": int, "actor": str, "kind": str, "request_id": str | None, "detail": dict}
```

- `kv_sim`의 `step`은 관리자 호출 순번이고 `actor`는 `"BlockPool"` 또는 `"KVManagerSim"`이다. `kind`는 `hit`, `touch`, `alloc`, `alloc_failed`, `hash_register`, `evict`, `free_front`, `free_back`, `preempt`, `draft_write`, `rollback`, `overwrite` 중 하나다.
- `sched_sim`의 `step`은 scheduler step 번호이고 `actor`는 `"Scheduler"`다. `kind`는 `arrive`, `schedule_running`, `schedule_waiting`, `chunk`, `preempt`, `first_token`, `finish`, `stop_waiting_seqs_cap`, `stop_waiting_budget`, `stop_waiting_preempted`, `stop_waiting_no_chunk` 중 하나다.

### `vllm_lab/view.py`

import할 때 `pd.set_option`으로 `display.max_colwidth=120`, `display.max_rows=200`, `display.max_columns=40`, `display.width=200`을 설정한다.

**그림 글자는 ASCII만이다.** 글꼴에 한글이 없어도 그림이 깨지지 않게 하기 위해서다. 그림 함수에 비ASCII 문자열을 넘기면 `ValueError`를 낸다. 한국어 설명은 그림 앞뒤 markdown에 쓴다. 그림 함수는 `plt.subplots`로 만들고 `plt.close(fig)` 뒤 `matplotlib.figure.Figure`를 돌려준다. 셀 마지막 줄에 두거나 `display(fig)`로 보인다. `tests/conftest.py`는 `os.environ.setdefault("MPLBACKEND", "Agg")`를 둔다.

```python
def table(rows: list[dict] | pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """행을 빠뜨리지 않고 DataFrame으로 돌려준다. display를 호출하지 않는다."""

def trace_table(events: list[dict]) -> pd.DataFrame:
    """열 step, actor, kind, request_id, detail. detail은 json.dumps(ensure_ascii=False) 문자열."""

def permalink(path: str, line: int) -> str:
    """https://github.com/vllm-project/vllm/blob/<VLLM_COMMIT>/<path>#L<line>. path가 절대 경로이거나 line<1이면 ValueError."""

def cite(path: str, line: int, label: str | None = None) -> str:
    """markdown 링크 문자열 '[label](permalink)'. label 기본값은 f"{path}:{line}"."""

def block_grid(cells: list[dict], *, ncols: int = 8, title: str | None = None,
               mark: dict[int, str] | None = None) -> Figure:
    """cells[i]: {"block_id": int, "state": str, "label": str}. state는 null, free, cached, used, shared.
    칸에 block_id와 label을 쓰고 state별 색과 범례를 둔다. mark는 block_id별 추가 ASCII 표시."""

def timeline(spans: list[dict], *, title: str | None = None, x_label: str = "toy ms",
             note: str = "teaching model, not measured") -> Figure:
    """spans[i]: {"lane": str, "start": float, "end": float, "label": str, "kind": str}.
    kind는 prefill, decode, preempted, wait, order, other. lane은 처음 나온 순서로 위에서 아래로. note를 그림 아래에 쓴다."""

def sweep_chart(rows: list[dict], x: str, ys: list[str], *, note: str, title: str | None = None) -> Figure:
    """x축 x, 선 ys. note가 비면 ValueError. 측정이 아니라는 문구를 그림 안에 강제하기 위해서다."""

def bar_chart(values: dict[str, float], *, unit: str = "", note: str = "", title: str | None = None) -> Figure:
    """가로 막대. 키 순서 유지."""

def lane_diagram(lanes: dict[str, list[str]], arrows: list[tuple[str, str, str]] = (),
                 *, title: str | None = None) -> Figure:
    """lane별 상자. arrows는 (출발 상자, 도착 상자, 글자). 없는 상자 이름이면 ValueError."""

def env_status(name: str, env_path: pathlib.Path | None = None) -> str:
    """Day07_new/.env만 읽어 '설정됨' 또는 '미설정'. 값이 비었거나 파일이 없으면 미설정. os.environ을 읽지 않는다."""

def read_env_value(name: str, env_path: pathlib.Path | None = None) -> str | None:
    """같은 파일에서 값을 돌려준다. 출력과 로그를 하지 않는다. RUN_POD 보호 셀 전용."""
```

### `vllm_lab/kv_sim.py`

**범위.** `vllm/v1/core/block_pool.py`, `kv_cache_manager.py`, `kv_cache_utils.py`, `single_type_kv_cache_manager.py`, `vllm/v1/worker/gpu/block_table.py`의 규칙을 한 group, `block_size == hash_block_size`로 모델링한다. `NOT_MODELED`에 다음을 적는다: watermark, sliding window와 skipped block, KV connector, partial tail 등록, `max_model_len` 상한, `hash_block_size` 분리, 실제 KV 값, 실제 hash 값(hash 값은 vLLM과 다르고 구조만 같다).

```python
NONE_HASH = "NONE_HASH"
PAD_SLOT_ID = -1

class KVPoolExhausted(ValueError):
    requested: int
    free: int

def hash_block_tokens(parent_hash: str | None, token_ids: Sequence[int],
                      extra_keys: tuple | None = None) -> str:
    """sha256(repr((parent_hash or NONE_HASH, tuple(token_ids), extra_keys)))의 hex 앞 12자."""

def request_block_hashes(token_ids: Sequence[int], block_size: int = 16,
                         cache_salt: str | None = None) -> list[str]:
    """꽉 찬 block만. salt는 start_token_idx == 0인 block의 extra_keys에만 (("cache_salt", salt),)."""

def slot_id(block_table: Sequence[int], position: int, block_size: int = 16) -> int:
    """block_table[position // block_size] * block_size + position % block_size.
    position이 표 밖이면 IndexError(한국어 메시지)."""

def slot_mapping(block_table: Sequence[int], start: int, num_tokens: int, block_size: int = 16,
                 pad_to: int | None = None) -> list[int]:
    """pad_to가 있으면 뒤를 PAD_SLOT_ID로 채운다."""

def packed_batch(entries: list[dict], block_size: int = 16, pad_to: int | None = None) -> dict:
    """entries[i]: {"request_id": str, "token_ids": list[int], "num_computed_tokens": int, "block_table": list[int]}.
    token_ids는 이번 step에 계산할 token만. 주어진 순서대로 이어 붙인다.
    반환 키: request_ids, input_ids, query_start_loc, positions, seq_lens, slot_mapping, num_tokens, num_tokens_after_padding.
    query_start_loc = 누적합(앞에 0), 길이 len(entries)+1. pad_to는 slot_mapping에만 -1을 채운다."""

@dataclass
class KVBlock:
    block_id: int
    ref_cnt: int = 0
    block_hash: str | None = None
    block_hash_num_tokens: int | None = None
    is_null: bool = False
    prev_free: KVBlock | None = None
    next_free: KVBlock | None = None

class FreeQueue:
    """직접 만든 이중 연결 리스트. vllm/v1/core/kv_cache_utils.py:246."""
    def __init__(self, blocks: list[KVBlock]) -> None: ...
    def __len__(self) -> int: ...
    def popleft(self) -> KVBlock: ...
    def popleft_n(self, n: int) -> list[KVBlock]: ...
    def remove(self, block: KVBlock) -> None: ...
    def prepend_n(self, blocks: list[KVBlock]) -> None:  # 주어진 순서가 앞에서부터의 순서
    def append_n(self, blocks: list[KVBlock]) -> None: ...
    def ids(self) -> list[int]: ...

class BlockPool:
    def __init__(self, num_blocks: int, enable_caching: bool = True,
                 events: list[dict] | None = None) -> None:
        """블록 전부 생성, 첫 popleft를 null block(ID 0, is_null=True)으로."""
    blocks: list[KVBlock]
    null_block: KVBlock
    free_queue: FreeQueue
    def num_free(self) -> int: ...
    def usage(self) -> float:          # 1 - num_free / (num_blocks - 1), vllm/v1/core/block_pool.py:877
    def get_cached_block(self, block_hash: str) -> KVBlock | None: ...
    def get_new_blocks(self, n: int) -> list[KVBlock]:
        """부족하면 KVPoolExhausted. 앞에서 꺼내고, hash가 있으면 지우고(evict), ref_cnt=1."""
    def touch(self, blocks: Sequence[KVBlock]) -> None:
        """ref_cnt==0이고 null이 아니면 queue 중간에서 빼고, ref_cnt += 1."""
    def free_blocks(self, ordered_blocks: Iterable[KVBlock]) -> None:
        """ref_cnt -= 1. 0이 된 것 중 hash 없음(또는 caching 꺼짐)은 prepend_n, hash 있음은 append_n."""
    def cache_block(self, block: KVBlock, block_hash: str, num_tokens: int) -> None:
        """같은 hash를 여러 block이 가질 수 있다. get_cached_block은 먼저 들어간 것을 돌려준다."""

@dataclass
class SimRequest:
    request_id: str
    token_ids: list[int]
    cache_salt: str | None = None
    num_prompt_tokens: int = 0       # 생성 시 len(token_ids)
    num_computed_tokens: int = 0
    spec_token_ids: list[int] = field(default_factory=list)
    status: str = "WAITING"          # WAITING, RUNNING, PREEMPTED, FINISHED
    num_preemptions: int = 0
    @property
    def num_tokens(self) -> int: ...
    @property
    def num_tokens_with_spec(self) -> int: ...
    def block_hashes(self, block_size: int = 16) -> list[str]: ...

@dataclass
class ScheduleResult:
    request_id: str
    hit_tokens: int
    hit_block_ids: list[int]
    new_block_ids: list[int]
    block_table: list[int]
    num_computed_tokens: int
    num_scheduled_tokens: int
    num_lookahead_tokens: int
    evicted_block_ids: list[int]
    def to_row(self) -> dict: ...

class KVManagerSim:
    def __init__(self, num_blocks: int, block_size: int = 16, enable_caching: bool = True) -> None: ...
    pool: BlockPool
    block_size: int
    events: list[dict]
    requests: dict[str, SimRequest]

    def add_request(self, request_id: str, token_ids: Sequence[int], *, cache_salt: str | None = None) -> SimRequest:
        """같은 ID가 이미 있으면 ValueError."""
    def get_computed_blocks(self, request: SimRequest) -> tuple[list[KVBlock], int]:
        """상한 (num_tokens - 1) // block_size block. 사슬에서 처음 없는 곳에서 멈춘다. caching 꺼짐이면 ([], 0). touch하지 않는다."""
    def allocate_slots(self, request: SimRequest, num_new_tokens: int, *,
                       new_computed_blocks: Sequence[KVBlock] = (), num_new_computed_tokens: int = 0,
                       num_lookahead_tokens: int = 0) -> list[KVBlock] | None:
        """필요 칸 = ceil((num_computed + num_new_computed + num_new_tokens + lookahead) / block_size).
        필요 새 block + ref_cnt==0인 적중 block 수 > free면 None(vllm/v1/core/single_type_kv_cache_manager.py:255).
        아니면 touch, 새 block 할당, 그리고 min(num_computed + num_new_computed + num_new_tokens, num_tokens)까지의 꽉 찬 block에 hash 등록."""
    def schedule(self, request: SimRequest, num_new_tokens: int | None = None, *,
                 num_lookahead_tokens: int = 0) -> ScheduleResult | None:
        """num_computed_tokens == 0이면 적중 조회. num_new_tokens 기본은 num_tokens_with_spec - 적중 후 계산 수.
        allocate 실패면 None. 성공하면 상태 RUNNING, 계산 수 증가, slot에 쓰기 표지 기록. 남은 수보다 크게 주면 ValueError."""
    def append_output(self, request: SimRequest, token_ids: Sequence[int]) -> None: ...
    def free(self, request: SimRequest) -> None:
        """block을 역순으로 반납. 상태 FINISHED."""
    def preempt(self, request: SimRequest) -> dict:
        """역순 반납, num_computed_tokens=0, spec 비움, 상태 PREEMPTED, num_preemptions+1.
        반환 {"request_id", "freed_block_ids", "num_preemptions"}. waiting 큐는 sched_sim의 몫이다."""
    def set_draft_tokens(self, request: SimRequest, token_ids: Sequence[int]) -> None: ...
    def verify_drafts(self, request: SimRequest, generated_token_ids: Sequence[int]) -> dict:
        """vllm/v1/core/sched/scheduler.py:2111. num_accepted = max(len(generated)-1, 0), num_rejected = drafts - num_accepted.
        num_computed_tokens -= num_rejected, generated를 token_ids에 붙이고 spec을 비운다. block은 그대로.
        반환 키: num_drafts, num_accepted, num_rejected, num_computed_tokens, num_tokens, block_table."""
    def block_table(self, request: SimRequest) -> list[int]: ...
    def slot_contents(self, slot: int) -> dict | None:
        """{"request_id", "position", "token_id", "is_draft"}. KV 값이 아니라 표지다. 다시 쓰면 overwrite event."""
    def free_queue_ids(self) -> list[int]: ...
    def cached_block_ids(self) -> list[int]:  # hash가 있는 block ID 오름차순
    def ref_cnts(self) -> list[list[int]]:    # [[block_id, ref_cnt], ...] ref_cnt>0만, ID 오름차순
    def snapshot(self) -> list[dict]:
        """view.block_grid 입력. state: null, free(ref 0, hash 없음), cached(ref 0, hash 있음), used(ref 1), shared(ref 2 이상).
        label은 소유 요청 ID를 '+'로 이은 ASCII(최대 8자), 소유자 없으면 ''. 추가 키 ref_cnt, block_hash."""
    @classmethod
    def replay(cls, inputs: dict) -> list[dict]:
        """reference_kv.json의 inputs 실행. 아래 형식."""

@dataclass(frozen=True)
class GroupSpec:
    name: str
    kind: str                 # "full", "sliding_window", "mamba", "circular_buffer"
    num_layers: int = 1       # 장난감 값이다. 실제 층 수가 아니다
    window: int | None = None # sliding_window일 때 token 수

class HybridPoolToy:
    """한 pool을 여러 group이 나눠 쓴다. block ID 하나는 한 번에 한 group만 소유한다(vllm/v1/core/kv_cache_utils.py:1631)."""
    def __init__(self, num_blocks: int, groups: list[GroupSpec], block_size: int = 16) -> None: ...
    def allocate(self, request_id: str, num_tokens: int) -> dict[str, list[int]]:
        """full: ceil(num_tokens/block_size). sliding_window: 창 안에서 필요한 수. mamba: 1. circular_buffer: 처음 한 번 1.
        이미 가진 만큼 빼고 할당해 group 이름별 새 block ID를 돌려준다. 모자라면 KVPoolExhausted."""
    def advance(self, request_id: str, num_computed_tokens: int) -> dict[str, list[int]]:
        """get_num_skipped_tokens 규칙으로 앞 block을 푼다: full 0, sliding_window 창 앞, mamba num_computed-1(vllm/v1/core/single_type_kv_cache_manager.py:712). 푼 ID를 group별로."""
    def free(self, request_id: str) -> None: ...
    def owner_of(self, block_id: int) -> str | None: ...
    def snapshot(self) -> list[dict]:  # block_grid 입력, label은 group 이름 앞 3자

def agreed_hit(group_boundaries: dict[str, set[int]], max_length: int) -> dict:
    """모든 group이 동의하는 적중 길이. length = max_length부터, group마다 length 이하 최대 경계로 줄이기를 변화가 없을 때까지.
    길이는 줄기만 한다(vllm/v1/core/kv_cache_coordinator.py:837). 반환 {"length": int, "rounds": int, "history": list[dict]}."""

def glm_like_groups() -> list[GroupSpec]:
    """KDA, MLA, indexer, tail 네 종류를 가리키는 장난감 구성. 층 수는 임의 값이고 GLM의 실제 값이 아니다(대장에 숫자 없음)."""

def reference_rows(path: pathlib.Path | None = None) -> list[dict]:
    """기본 DATA_DIR/'reference_kv.json'. 행 {"name", "match", "status", "reason"}. status가 not_run이면 name '(전체)', match None 한 행.
    파일이 없으면 FileNotFoundError. 결과를 지어내지 않는다."""
```

### `vllm_lab/sched_sim.py`

**범위.** `vllm/v1/core/sched/scheduler.py`의 `schedule()`과 `_preempt_request`, 지표 정의를 FCFS, 한 프로세스로 모델링한다. KV는 이 모듈 안에서 block 수만 센다. `kv_sim`을 import하지 않는다. `NOT_MODELED`: prefix cache(입력 `cached_tokens` 제외), 복귀 시 prefix 적중, draft, async scheduling, PRIORITY 정책, draft slot, watermark, 실제 시간. 또한 `stream_interval`의 첫 chunk 시점은 toy 규칙이다. vLLM 동작으로 확인한 것이 아니므로 `stream_interval`에 따른 TTFT 차이를 vLLM 동작으로 읽지 않는다는 문장을 넣는다.

```python
class SimStuck(RuntimeError): ...

@dataclass(frozen=True)
class SchedConfig:
    max_num_batched_tokens: int = 32
    max_num_seqs: int = 4
    enable_chunked_prefill: bool = True
    long_prefill_token_threshold: int = 0
    long_prefill_token_threshold_adaptive: bool = False
    num_blocks: int = 64          # 할당 가능 수. null block을 뺀 값으로 쓴다
    block_size: int = 16
    max_model_len: int = 4096
    stream_interval: int = 1
    toy_step_ms: float = 10.0
    toy_ms_per_token: float = 0.5
    toy_network_ms: float = 0.0
    def validate(self) -> None:
        """chunked 끔이고 max_num_batched_tokens < max_model_len이면 ValueError(값 둘을 메시지에).
        같은 값은 허용(vllm/config/scheduler.py:314). threshold 음수면 ValueError."""

@dataclass(frozen=True)
class Req:
    request_id: str
    prompt_tokens: int
    max_tokens: int
    arrival_ms: float = 0.0
    cached_tokens: int = 0       # 첫 스케줄 때 계산한 것으로 치는 수. 16의 배수여야 한다
    start_running: bool = False  # True면 t=0에 running에서 시작
    start_computed: int = 0      # start_running일 때의 계산 수. 시작 block 규칙은 아래에 있다

@dataclass
class StepRecord:
    step: int
    start_ms: float
    end_ms: float
    tokens: dict[str, int]       # 스케줄 순서 유지
    running_before: list[str]
    waiting_before: list[str]
    preempted: list[str]
    blocks_in_use: int
    budget_left: int
    def to_row(self) -> dict: ...  # step, start_ms, end_ms, tokens(문자열), 합계, 남은 예산, 쓰는 block, preempt

@dataclass
class ReqMetrics:
    request_id: str
    prompt_tokens: int
    output_tokens: int
    num_chunks: int
    client_ttft_ms: float
    client_itl_ms: list[float]
    client_itl_mean_ms: float | None
    client_tpot_ms: float | None   # 출력 1개 이하면 None
    client_e2el_ms: float
    server_ttft_ms: float
    server_tpot_ms: float          # 출력 1개 이하면 0.0
    server_e2e_ms: float
    queue_ms: float
    num_preemptions: int
    chunk_times_ms: list[float]
    send_ms: float

class SimResult:
    steps: list[StepRecord]
    events: list[dict]
    config: SchedConfig
    def step_rows(self) -> list[dict]: ...
    def metrics(self) -> list[ReqMetrics]: ...
    def metrics_rows(self) -> list[dict]:  # client_itl_ms, chunk_times_ms 목록 칸은 뺀다
    def spans(self) -> list[dict]:
        """view.timeline 입력. lane=request_id, 대기 kind=wait, 계산 step은 kind prefill 또는 decode, preempt 뒤 kind preempted."""
    def counters(self, at_step: int | None = None) -> dict[str, float]:
        """키: vllm:num_preemptions, vllm:prefix_cache_queries, vllm:prefix_cache_hits, vllm:num_requests_running,
        vllm:num_requests_waiting, vllm:kv_cache_usage_perc. queries와 hits는 token 수."""
    def to_prometheus_text(self, at_step: int | None = None, *, counter_suffix: str = "",
                           model_name: str = "GLM-5.3-Flash", engine: str = "0") -> str:
        """첫 줄은 '# constructed teaching sample, not measured'. 위 counters와
        vllm:time_to_first_token_seconds, vllm:inter_token_latency_seconds, vllm:request_time_per_output_token_seconds,
        vllm:e2e_request_latency_seconds, vllm:request_queue_time_seconds의 _sum, _count(초). 모든 줄에 model_name, engine 라벨.
        at_step은 그 step까지 끝난 요청과 chunk만 센다."""

def run_sim(requests: list[Req], config: SchedConfig = SchedConfig(), *, validate: bool = True,
            max_steps: int = 10000) -> SimResult: ...

def sweep(requests: list[Req], param: str, values: list, base: SchedConfig = SchedConfig()) -> list[dict]:
    """param 하나만 바꾼다(dataclasses.replace). 행 키: param 이름, steps, num_preemptions, toy_tokens_per_s,
    ttft_mean_ms, ttft_p99_ms, itl_mean_ms, tpot_mean_ms, e2el_mean_ms, 그리고 요청 ID의 '-' 앞을 그룹으로 한 'ttft_mean_ms:<그룹>'."""

def doc_faq_chat() -> list[Req]:
    """[Req('doc', 54, 8), Req('faq', 20, 6), Req('chat', 34, 4)] 모두 arrival 0."""

def e1_workload() -> list[Req]:
    """[Req('chat', 34, 4, start_running=True, start_computed=33), Req('doc', 54, 8, start_running=True, start_computed=32), Req('faq', 20, 6)].
    SchedConfig(max_num_batched_tokens=32, num_blocks=11)이면 첫 step tokens는 {'chat': 1, 'doc': 22, 'faq': 9}, blocks_in_use는 8."""

def mixed_workload() -> list[Req]:
    """Req('doc', 400, 16)과 Req(f'faq-{i}', 30, 12, arrival_ms=10*i) i=1..5."""
```

`start_computed` 규칙은 다음과 같다. `start_running` 요청이 시작할 때 쥔 block 수는 `ceil(start_computed / block_size)`이고, 그 뒤 필요량은 일반 규칙으로 계산한다. E1의 `chat`은 33 계산이므로 시작 block 3개, 첫 step 필요량도 3개다.

**step 알고리즘(이 순서 그대로).**

1. `step += 1`. 시각이 된 요청을 waiting 끝으로 옮긴다(서버 도착 = `arrival_ms + toy_network_ms`). `arrive` event.
2. `budget = max_num_batched_tokens`. threshold 계산: `running + waiting` 수가 1이면 0, 아니면 설정값. adaptive이고 값이 0보다 크면 `max(값, max_num_batched_tokens // 요청 수)`(`vllm/v1/core/sched/scheduler.py:640`, `:650`).
3. **running 순회.** `budget > 0`인 동안 앞에서부터. `n = num_tokens - computed`. `0 < threshold < n`이면 `n = threshold`. `n = min(n, budget)`. 필요 block = `ceil((computed + n) / block_size)`, 새로 필요한 수가 남은 수보다 크면 `running[-1]`을 preempt한다. 이것을 맞을 때까지 되풀이한다. 희생자가 자기 자신이면 running 순회를 멈춘다(`vllm/v1/core/sched/scheduler.py:842`, `:846`). 성공이면 `budget -= n`.
4. **preempt.** block 모두 반납, `computed = 0`, 생성 token은 유지(그래서 `num_tokens`는 prompt+생성), waiting 맨 앞, `num_preemptions += 1`.
5. **waiting 순회.** 이번 step에 preempt가 하나도 없을 때만. `budget > 0`인 동안 앞에서부터. `len(running) >= max_num_seqs`면 `stop_waiting_seqs_cap`으로 멈춘다. `computed == 0`이고 첫 스케줄이면 `computed = cached_tokens`. `n = num_tokens - computed`. threshold 적용. chunked 끔이고 `n > budget`이면 `stop_waiting_no_chunk`로 멈춘다. `n = min(n, budget)`. block이 모자라면 멈춘다(waiting에서는 preempt하지 않는다). 성공이면 running 끝으로 옮기고 `budget -= n`.
6. **시간.** `tokens` 합이 0이면 다음 도착 시각으로 건너뛴다. 남은 도착이 없으면 `SimStuck`(메시지에 남은 요청과 이유). 아니면 `end = start + toy_step_ms + toy_ms_per_token * 합`.
7. **결과 반영.** `computed += n`. `computed == num_tokens`인 요청은 token 1개를 생성한다. 첫 token이면 `first_token` event. `stream_interval`개마다 또는 끝날 때 chunk를 낸다. chunk의 client 시각은 `end + toy_network_ms`, 서버 시각은 `end`. `max_tokens`에 닿으면 block을 반납하고 `finish`.

`run_sim`은 `validate=True`면 `config.validate()`를 먼저 부른다. `max_steps`를 넘으면 `SimStuck`.

**지표 식.** 시각은 ms. `send_ms = arrival_ms`.

| 칸 | 식 | 코드 |
|---|---|---|
| `client_ttft_ms` | 첫 chunk client 시각 - `send_ms` | `vllm/benchmarks/lib/endpoint_request_func.py:436` |
| `client_itl_ms` | 연속 chunk 간격 | `vllm/benchmarks/lib/endpoint_request_func.py:270` |
| `client_e2el_ms` | 마지막 chunk - `send_ms` | `vllm/benchmarks/lib/endpoint_request_func.py:462` |
| `client_tpot_ms` | `(e2el - ttft) / (output_tokens - 1)`, `output_tokens <= 1`이면 None | `vllm/benchmarks/serve.py:628` |
| `server_ttft_ms` | 첫 token `end` - 서버 도착 | `vllm/v1/metrics/stats.py:521` |
| `server_tpot_ms` | `(마지막 token - 첫 token) / (n - 1)`, n≤1이면 0.0 | `vllm/v1/metrics/stats.py:608` |
| `server_e2e_ms` | 마지막 token `end` - 서버 도착 | `vllm/v1/metrics/stats.py:590` |
| `queue_ms` | 처음 스케줄된 step의 `start` - 서버 도착 | `vllm/v1/metrics/stats.py:592` |

### `vllm_lab/kv_math.py`

```python
class UnsupportedKVShape(ValueError): ...

DTYPE_BYTES: dict[str, int] = {"float32": 4, "float16": 2, "bfloat16": 2, "fp8": 1, "fp8_e4m3": 1, "fp8_e5m2": 1}
HEAD_TYPES = ("MHA", "GQA", "MQA")
UNSUPPORTED_HEAD_TYPES = ("MLA", "recurrent", "glm5next")
METRIC_NAMES: dict[str, str]  # 짧은 이름 → part3.md의 정확한 이름. 키: prefix_queries, prefix_hits, kv_usage, preemptions,
                              # waiting, running, ttft, itl, tpot, e2e, queue

def tokens_processed_without_kv(prompt_tokens: int, output_tokens: int) -> dict:
    """{"without_kv": sum(P + i for i in range(n)), "with_kv": P + n - 1, "ratio": float}. 산수이고 연산량 주장이 아니다. P2-02(미확인)."""

def block_bytes(num_kv_heads: int, head_size: int, dtype: str = "bfloat16", block_size: int = 16,
                head_size_v: int | None = None) -> int:
    """num_kv_heads * block_size * (head_size + head_size_v) * dtype 크기. head_size_v 기본 head_size. 없는 dtype은 ValueError. P2-05."""

def raw_kv_bytes(*, batch: int, layers: int, tokens: int, head_type: str, num_heads: int,
                 head_dim: int, dtype: str = "bfloat16", num_kv_heads: int | None = None) -> int:
    """2*B*L*T*n*d*b. n: MHA는 num_heads, GQA는 num_kv_heads(필수), MQA는 1. D-12.
    UNSUPPORTED_HEAD_TYPES면 UnsupportedKVShape(메시지가 glm53_kv_note()를 가리킨다). TP 샤딩은 계산하지 않는다고 docstring에 쓴다."""

def glm53_kv_note() -> str:
    """이 식을 GLM-5.3-Flash에 쓸 수 없는 다섯 이유를 한국어로. 숫자를 만들지 않는다. docs/sources/part2.md GLM 절을 가리킨다."""

@dataclass(frozen=True)
class CapacityEstimate:
    budget_bytes: int
    kv_bytes: int
    num_blocks: int
    capacity_tokens: int
    max_concurrency: float
    log_line: str  # 'GPU KV cache size: 529,520 tokens, Maximum concurrency for 8,192 tokens per request: 64.64x' 형식

def capacity_from_budget(*, gpu_total_bytes: int, weights_bytes: int, other_bytes: int,
                         block_bytes_all_layers: int, block_size: int = 16,
                         gpu_memory_utilization: float = 0.92, max_model_len: int = 8192) -> CapacityEstimate:
    """budget = int(total * 비율), kv = budget - weights - other, blocks = kv // block_bytes_all_layers, capacity = blocks * block_size.
    kv <= 0이면 ValueError. 가상의 산수다. 실제 vLLM은 profiling으로 정한다(P1-22). E5의 값이 정확히 나와야 한다."""

def parse_prometheus(text: str) -> dict[tuple[str, tuple[tuple[str, str], ...]], float]:
    """'# '로 시작하는 줄과 빈 줄은 건너뛴다. 키는 (이름, 정렬한 라벨 튜플). 값은 float. 읽지 못하는 줄은 ValueError."""

def metric_value(samples: dict, name: str, **labels: str) -> float | None:
    """name과 라벨이 맞는 표본의 합. 없으면 name+'_total'을 찾는다(P3-38(미확인)이라 두 형태 모두). 둘 다 없으면 None. 0을 돌려주지 않는다."""

def metric_delta(before: dict, after: dict, name: str, **labels: str) -> float | None:
    """둘 중 하나라도 None이면 None."""

def histogram_mean_delta(before: dict, after: dict, name: str, **labels: str) -> float | None:
    """(_sum 변화량) / (_count 변화량). 변화량이 0이거나 표본이 없으면 None."""

def prefix_hit_rate_delta(before: dict, after: dict) -> float | None:
    """hits 변화량 / queries 변화량. queries 변화량이 0이면 None."""

def metrics_report(before: dict, after: dict) -> list[dict]:
    """METRIC_NAMES 전부. 행 {"항목", "이름", "종류", "값"}. Gauge는 after 값, Counter는 변화량, Histogram은 평균 변화량. 없으면 값 None."""

@dataclass(frozen=True)
class ChunkMetrics:
    ttft_s: float | None
    itl_s: list[float]
    e2el_s: float | None
    tpot_s: float | None
    output_tokens: int | None
    num_chunks: int
    first_visible_s: float | None
    warnings: list[str]

def metrics_from_chunks(send_ts: float, chunks: list[dict]) -> ChunkMetrics:
    """chunks[i]: {"t": float, "has_choices": bool, "content": str | None, "reasoning": str | None, "completion_tokens": int | None}.
    첫 has_choices 시각으로 TTFT, 비어도 친다(P3-26). ITL은 has_choices chunk 간격(P3-27). E2EL은 마지막 has_choices(P3-29). usage 전용 chunk는 시각을 옮기지 않고 completion_tokens만 준다.
    TPOT은 출력 수가 2 이상이고 알려졌을 때만. first_visible_s는 content가 있는 첫 chunk(D-36).
    출력 수 > chunk 수이면 warnings에 '한 chunk에 token이 여럿입니다. ITL은 token당 지연이 아닙니다'. 출력 수를 모르면 그 사실도 warnings에."""
```

E5 검산: `capacity_from_budget(gpu_total_bytes=24*2**30, weights_bytes=12*2**30, other_bytes=2*2**30, block_bytes_all_layers=262144, max_model_len=8192)`는 `num_blocks=33095`, `capacity_tokens=529520`을 낸다.

### `vllm_lab/agent_sim.py`

**범위.** 대화를 token 목록으로 바꾸는 장난감 렌더러와 `kv_sim`으로 prefix 재사용을 보인다. GLM의 tokenizer나 chat template이 아니다. `NOT_MODELED`: 실제 template, 실제 tokenizer, 답변 재tokenize 어긋남, 요약 middleware, 실제 서버 파서. tool을 앞에 렌더링하는 것은 toy의 가정이다(P5-08(미확인)).

```python
def toy_tokenize(text: str) -> list[int]:
    """re.findall(r"\w+|[^\w\s]", text)의 각 조각을 sha256 앞 6 hex의 정수로. 결정적이다."""

def render_prompt(system: str, tools: list[dict], messages: list[dict]) -> list[int]:
    """순서: <system> 토큰들, tools를 주어진 순서로 각각 <tool> json.dumps(sort_keys=True), messages를 각각 <role> content <end>.
    assistant의 tool_calls는 content 뒤에 json으로. 표지도 toy_tokenize로 바꾼다."""

@dataclass
class TurnResult:
    turn: int
    label: str
    prompt_tokens: int
    hit_tokens: int
    hit_blocks: int
    recomputed_tokens: int
    hit_ratio: float
    first_miss_block: int | None   # 적중이 hit_blocks이고 상한이 아니면 hit_blocks, 전부 맞으면 None
    assumption: str
    def to_row(self) -> dict: ...

class AgentReuseSim:
    def __init__(self, num_blocks: int = 512, block_size: int = 16) -> None: ...
    kv: KVManagerSim
    def send(self, system: str, tools: list[dict], messages: list[dict], *, cache_salt: str | None = None,
             output: str = "", label: str = "", assumption: str = "") -> TurnResult:
        """새 요청 하나: add_request, schedule, output token append 후 schedule, free. 턴마다 새 request(P5-01).
        pool 부족이면 KVPoolExhausted(한국어 메시지)."""
    def rows(self) -> list[dict]: ...

SCENARIOS = ("append_only", "system_change", "tool_added", "tool_order_change",
             "salt_change", "effort_in_system", "pressure_evict")

def run_scenario(name: str, *, user_words: int = 40, turns: int = 4, block_size: int = 16,
                 num_blocks: int = 512) -> list[dict]:
    """TurnResult.to_row() 목록. 없는 이름은 ValueError. tool_added, tool_order_change, effort_in_system의 assumption 칸에는
    'toy 렌더링 가정, 실제 template은 확인되지 않음(미확인)'을 넣는다. pressure_evict는 num_blocks를 줄이고 사이에 다른 요청을 넣는다."""

def reuse_from_recorded(calls: list[dict], *, block_size: int = 16, num_blocks: int = 512) -> list[dict]:
    """calls[i]: {"system": str, "tools": list, "messages": [{"role", "content"}]}. 기록을 render_prompt에 넣어 TurnResult 행을 낸다. output은 빈 문자열."""

def chatopenai_sends_include_usage(*, base_url_set: bool, stream_usage: bool | None) -> bool:
    """stream_usage가 None이 아니면 그 값, None이면 not base_url_set. P5-17."""

def cached_tokens_visible(*, server_flag: bool, stream: bool, client_sends_include_usage: bool,
                          force_include_usage: bool = False) -> dict:
    """{"visible": bool, "why": str}. server_flag가 거짓이면 불가(P5-11). stream이면 둘 중 하나가 참이어야 한다(P5-12)."""

def flag_matrix() -> list[dict]:
    """네 조합과 tools 요청. 칸: --enable-auto-tool-choice, --tool-call-parser, 시작 단계, tool_choice=auto 요청, 근거 ID, 근거 종류('코드 읽기')."""

def finish_reason_rule(*, engine_finish_reason: str | None, tool_choice: str, calls_extracted: bool, stream: bool) -> str:
    """tool_choice: auto, required, named, none. 비스트리밍: (auto이고 calls_extracted) 또는 (required이고 engine=='stop')이면 'tool_calls'.
    스트리밍: calls_extracted이고 named가 아니고 engine=='stop'이면 'tool_calls'. 그 밖은 engine 값 또는 'stop'.
    vllm/entrypoints/openai/chat_completion/serving.py:771, :1098. 코드를 옮긴 교육용 함수다. 실행 확인이 아니다."""

def validate_tool_args(schema: dict, arguments: str) -> list[str]:
    """client 쪽 검증. JSON 파싱 실패, required 누락, 타입 불일치(string, integer, number, boolean, array, object)를 한국어 문장 목록으로. 빈 목록이면 통과. vLLM 기능이 아니다."""

def diagnosis_rows(path: pathlib.Path | None = None) -> list[dict]:
    """C1~C12 12행. 칸: 사례, 층, 증상(가설), 볼 곳, 재현 조건, 근거 종류. part6.md 실패 사례 후보를 옮긴다.
    근거 종류는 파일에 그 후보를 candidates로 가진 ran 케이스가 있으면 '실제 GLM 파서, 구성 문자열', 없으면 '코드 읽기'. C12는 'client 코드'. 파일이 없으면 모두 '코드 읽기'."""

class ReferenceMissing(FileNotFoundError): ...
class CaseNotRun(RuntimeError): ...

@dataclass(frozen=True)
class ParserCase:
    id: str
    candidates: tuple[str, ...]
    layer: str
    title: str
    constructed: bool
    raw_text: str
    tools: tuple[str, ...]
    tool_choice: str
    mode: str
    status: str
    reason: str | None
    output: dict | None

def reference_status(path: pathlib.Path | None = None) -> dict:
    """예외를 내지 않는다. {"status": 'ran'|'partial'|'not_run'|'missing', "reason": str | None, "parser": dict | None}."""

def load_parser_cases(path: pathlib.Path | None = None) -> list[ParserCase]:
    """기본 DATA_DIR/'reference_parser.json'. 파일 없음은 ReferenceMissing. 최상위 status가 not_run이면 CaseNotRun(reason 포함)."""

def get_parser_case(case_id: str, path: pathlib.Path | None = None) -> ParserCase:
    """없는 ID는 KeyError. 그 케이스 status가 ran이 아니면 CaseNotRun. 결과를 지어내지 않는다."""

def parser_case_table(path: pathlib.Path | None = None) -> list[dict]:
    """행: id, 후보, 제목, 입력, reasoning, content, tool_calls, 근거 종류. not_run 케이스의 결과 칸은 '실행 안 함'. 파일 문제는 load_parser_cases와 같다."""
```

### 데이터 파일

`data/reference_kv.json`(`real-diff` 노드가 쓴다).

```json
{"status": "ran", "vllm": "0.32.0", "reason": null,
 "scenarios": [{"name": "sequential_allocate", "inputs": {"num_blocks": 12, "block_size": 16, "ops": []},
                "real": [], "sim": [], "match": true}]}
```

- `status`는 `ran` 또는 `not_run`. `not_run`이면 `reason`에 실제 오류를 쓰고 `scenarios`는 빈 목록이거나 `real`이 null이다.
- `ops`의 원소: `{"op": "schedule", "request_id": str, "token_ids": list[int], "cache_salt": str | null, "num_new_tokens": int | null}`, `{"op": "append_output", "request_id": str, "token_ids": list[int]}`, `{"op": "free", "request_id": str}`.
- `real`과 `sim`의 원소(ops 하나에 하나, `KVManagerSim.replay`의 반환과 같다): `{"op", "request_id", "returned_none": bool, "hit_tokens": int | null, "hit_block_ids": list | null, "new_block_ids": list | null, "block_table": list, "ref_cnts": [[id, n]], "free_queue": list, "cached_block_ids": list}`. `free`와 `append_output`의 앞 세 칸은 null이다. hash 값은 비교하지 않는다. 실제 쪽 `free_queue`는 queue를 순회해 만든다.

시나리오 6개는 이 이름과 입력으로 고정한다. token은 겹치지 않게 `list(range(1000, 1000+N))` 등으로 만든다.

| name | num_blocks | ops 요약 | 시뮬레이터가 내야 할 값 |
|---|---:|---|---|
| `sequential_allocate` | 12 | R1 54 token, R2 20 token schedule | R1 `[1,2,3,4]`, R2 `[5,6]` |
| `prefix_hit_repeat` | 12 | R1 54, free, R2 같은 token | R2 적중 48 token, `hit_block_ids` `[1,2,3]`, 새 block `[4]` |
| `hit_cap_num_tokens_minus_1` | 12 | R1 48, free, R2 같은 token | R2 적중 32 token |
| `different_salt` | 12 | R1 salt `s1` 54, free, R2 salt `s2` 같은 token | R2 적중 0 |
| `free_then_reuse_order` | 12 | R1 54, free, R2 다른 16 token, R3 다른 32 token | R2 `[4]`(hash 없는 꼬리), R3 `[5,6]` |
| `eviction_under_pressure` | 6 | R1 48, free, R2 다른 64 token, free, R3가 R1과 같은 token | R2 `[4,5,3,2]`, R3 적중 16 token block `[1]` |

실제 클래스 결과가 위 값과 다르면 `real-diff`는 값을 고치지 않고 그대로 기록한다(그 노드의 HONESTY 규칙).

`data/reference_parser.json`(`real-diff` 노드가 쓴다).

```json
{"status": "ran", "vllm": "0.32.0", "reason": null,
 "parser": {"tool": "glm47", "reasoning": "glm47", "tokenizer": "<쓴 tokenizer 또는 대체물>", "limit": "<그 대체물이 결과를 어떻게 제한하는가>"},
 "cases": [{"id": "clean_call", "candidates": [], "layer": "parser", "title": "깨끗한 호출", "constructed": true,
            "raw_text": "<구성 문자열>", "tools": ["get_temperature"], "tool_choice": "auto", "mode": "non_stream",
            "status": "ran", "reason": null,
            "output": {"reasoning": null, "content": null, "tool_calls": [{"name": "get_temperature", "arguments": "{\"city\": \"서울\"}"}], "error": null}}]}
```

- 최상위 `status`는 `ran`, `partial`, `not_run`. 케이스 `status`는 `ran`, `not_run`. `not_run` 케이스의 `output`은 null이고 `reason`이 있다.
- `constructed`는 항상 true다. 모델 출력이 아니다.
- `finish_reason`은 넣지 않는다. 그것은 파서가 아니라 `serving.py`가 정하므로 파서만 돌린 결과에 없다.

| id | candidates | 입력의 뜻 |
|---|---|---|
| `clean_call` | `[]` | 깨끗한 호출 하나 |
| `reasoning_then_call` | `[]` | 생각 구간 뒤 호출 |
| `malformed_markup` | `["C7"]` | `</tool_call>` 없이 다음 `<tool_call>` |
| `truncated_call` | `["C2", "C6"]` | 닫히지 않은 호출, `</arg_value>` 없음 |
| `unknown_tool` | `["C3"]` | `tools`에 없는 이름 |
| `bad_arg_type` | `["C4"]` | 정수 인자에 숫자 아닌 값 |
| `no_call` | `[]` | 호출 없는 일반 답변 |

### 모듈과 노트북의 대응

| 모듈 | 쓰는 노트북 |
|---|---|
| `view` | 00~06 전부 |
| `kv_sim` | 00, 02a, 02b |
| `sched_sim` | 01, 03 |
| `kv_math` | 02a, 03, 04 |
| `agent_sim` | 05, 06 |

---

## 사실 공백과 판단

### 빼거나 미확인으로 표시한 개념

| 개념 | 처리 | 근거 |
|---|---|---|
| attention 연산량이 문맥 길이의 제곱 | **뺐다.** 다시 넣을 token 수를 세는 산수로 대신한다 | P2-02(미확인) |
| GLM-5.3-Flash 층 구성, `kv_lora_rank`, `index_kpool` 숫자와 KV 용량 | **뺐다.** 구조만 쓴다. `kv_math`가 숫자를 거부한다 | `part2.md` GLM 절 |
| Gemma4 MTP의 KV 공유, MTP가 target KV를 어떻게 쓰는가 | **뺐다.** 대장은 lookahead K, 추가 slot 0까지만 준다 | P2-55(미확인) |
| chat template의 특수 token, 재tokenize 어긋남, tool 목록의 렌더링 위치 | 미확인으로 표시, toy는 가정이라고 쓴다 | P2-46(미확인), P5-07(미확인), P5-08(미확인) |
| effort 값이 prefix를 바꾸는가 | 미확인으로 표시 | P5-13(미확인) |
| `clear_thinking`의 뜻 | **뺐다.** "강사 스크립트가 쓰는 값"까지만 | P5-14(미확인), R-09(미확인) |
| Counter의 `_total` 이름 | 미확인으로 표시, 파서는 두 형태를 받는다 | P3-38(미확인) |
| replica(DP) 내부 동작 | 미확인으로 표시, 문서 안내까지만 | P3-17(미확인) |
| `listen`을 누가 부르는가 | 미확인으로 표시, "bind까지"만 말한다 | P1-12(미확인) |
| Rust 파서 오류의 HTTP 모양, 이름 혼용, `glm5_next`의 뜻 | 미확인으로 표시 | P6-04(미확인), P6-30(미확인), P6-35(미확인) |
| `--reasoning-parser` 없을 때 생각이 content에 섞이는가 | 미확인으로 표시 | P6-21(미확인) |
| RunPod 프록시 100초 | 미확인으로 표시, 강사 메모 | P5-24(미확인), R-13(미확인) |
| 하이브리드 모델에서 prefix caching이 실제 켜지는가 | 미확인으로 표시 | `SOURCES.md` Pod 점검 5번 |
| H200의 BF16 KV | 코드와 레시피의 추론이라고 표시, 관찰 아님 | `part4.md` H200 절 |
| 릴리스 시점(v0.17, v0.28, v0.29 등) | **뺐다.** 또는 미확인 표시 | D-10(미확인), D-21(미확인), D-26(미확인), D-27(미확인), D-37(미확인) |
| `watermark`, `scheduler_reserve_full_isl`, `max_num_active_seqs`의 동작 | **뺐다.** 선언만 확인됨 | `part3.md` 설계 결정 |
| `vllm bench serve --num-prompts` 기본값 | **뺐다.** 항상 명시하게 한다 | `part3.md` 파라미터 절 |
| Rust 이미지·비디오 입력 | **뺐다** | P1-50(미확인) |
| 수업 Pod의 frontend, 플래그, 서버 응답 | 모른다고 쓴다 | R-04(미확인), `part6.md` 적용 범위 전제 |
| packed 배열 안의 요청 순서, 16이 backend별로 바뀌는 경로 | "확인이 필요합니다" | P2-19에 순서 없음, D-13 |

### 대장끼리 어긋나는 곳과 이 문서의 판단

| 어긋나는 곳 | 판단 |
|---|---|
| P1-24는 PR #6 본문을 읽었다고 쓰고 `part1.md` 설계 결정 줄은 "제목만 확인"이다 | 제목과 병합일만 인용한다 |
| P2-28의 salt 길이 1~1024와 P5-10의 검증기 128자 | P5-10을 따른다. 코드의 검증기가 실제로 막는다 |
| P3-23 "처음부터 되풀이"와 P2-37 "일부 재사용 가능" | P2-37을 함께 가르친다 |
| D-17은 "Decode를 먼저"를 일치로 판정, P3-22는 부정확하다고 판정 | P3-22를 따른다 |
| R-12(미확인)는 클라이언트 코드를 보지 못한 판정이고, P5-16은 실측으로 일치 | P5-16을 쓰고 R-12(미확인)를 대체했다고 적는다 |
| P5-05 "최대 15 token"과 P5-06 "한 block 전체" | 둘 다 맞다. 전자는 부분 꼬리, 후자는 block 경계 프롬프트다. E2로 구분해 보인다 |
| `part5.md` 상태 집계 표(미확인 5)와 행 집계(미확인 7) | 행이 정답이다. `SOURCES.md` 색인과 같다 |


## 구축 후 정정

- 절 4(이 파일의 "자기 자신이면 그 step에서 포기한다")는 틀렸다. 고른 요청이 자기 자신이어도 `_preempt_request`가 먼저 실행되고 그다음에 break한다(`vllm/v1/core/sched/scheduler.py:834-844`).
- "모든 절은 `왜 이렇게 설계했나` 문단으로 끝낸다"는 규칙은 더 이상 성립하지 않는다. 대장에서 확인된 이유가 없는 문단은 지웠다.
- `vllm bench serve --num-prompts` 기본값은 1000으로 확인됐다(`vllm/benchmarks/datasets/datasets.py:70`, `:1589`). 위에서 "뺐다"고 한 판단은 이 정정으로 대체된다.
- 1315행은 `scheduler_reserve_full_isl`을 선언만 확인됐다고 해서 뺐지만, 기본값은 True이고 sched_sim 따라가기 예제는 이것이 모델링되지 않았다는 데 기대고 있다. 이제 그 사실을 밝혀 둔다.
- 02c(최근 모델의 KV 통제)와 04b(KV 운영, LMCache)는 저자의 요청으로 나중에 더했다. 두 노트북은 `docs/sources/part7.md`, `part8.md`를 근거로 하고 각 45분이며, 이론 블록은 이제 330분이다.

### 2026-11-02 정정: 실제 클래스 호출과 대장 감사로 대체된 줄

위 설계 줄은 그대로 두고, 아래 목록이 가리키는 줄의 서술은 이 목록으로 대체된다. 줄 번호는 이 정정을 덧붙이기 전 기준이다. 상태의 현재 값은 `docs/sources/`의 해당 행이 정답이다.

- 265-266, 300, 1308행: `P1-12(미확인)`과 "listen 호출은 확인하지 못했다"는 낡았다. P1-12는 `일치`다. 근거는 저장소 루트 환경의 uvicorn 0.54.0과 uvloop 코드이고, 블로그가 적은 0.52.4는 읽지 않았다. listen 위치는 경로마다 다르다. API server 하나면 Uvicorn이 넘겨받은 소켓에 listen을 걸고, API server 여러 개가 소켓을 공유하면 vLLM이 직접 `sock.listen`을 부른다. Uvicorn과 uvloop 코드는 고정한 v0.32.0 트리 밖이라는 단서를 붙인다.
- 396행: "P3-23의 '처음부터'는 P2-37로 보완"은 낡았다. P3-23이 `블로그·코드 차이`로 바뀌었다. 복귀 때 `num_computed_tokens`가 0이라 prefix cache를 다시 조회하고, 덮어써지지 않은 block은 재사용된다. 실제 `Scheduler` 실행에서 prefix를 켠 경우의 복귀 적중도 이를 보였고, prefix를 끄면 전부 다시 계산한다(`docs/reference/sched.md`).
- 401, 424, 1302행: `P2-55(미확인)`은 낡았다. P2-55는 `일치`이고 `수업에 쓰지 말 것`에서도 빠졌다. 근거는 코드 읽기(docstring, speculator 연결, lookahead 속성)뿐이고 실행으로 확인한 것은 아니다. "MTP가 target KV를 어떻게 공유하는지는 말하지 않는다"는 판단은 이 행이 허용하는 범위까지만 완화된다.
- 525행: "가중치, activation, CUDA graph 몫은 그대로다"는 낮췄다. P4-10은 이제 "식에 들어 있지 않을 뿐 바뀌지 않는다는 근거는 찾지 못했다(미확인)"이다. block 수가 두 배가 된다는 toy 설명과 전체 절감 2배가 다른 말이라는 요지는 그대로다.
- 1076-1077행: `glm53_kv_note`의 "다섯 이유"는 낡았다. `part2.md` GLM 절은 이유를 여섯으로 센다. MLA 쪽 저장 형식도 `fp8_ds_mla` 656, `nvfp4_ds_mla` 352가 더해졌다. 숫자를 만들지 않는 규칙은 그대로다.
- 1098행: `P3-38(미확인)`은 낡았다. P3-38은 `일치`다. prometheus_client 0.26.0에서 Counter를 만들어 단일 프로세스와 `PROMETHEUS_MULTIPROC_DIR` 두 레지스트리 모두 `_total`을 붙이는 것을 확인했다. 두 형태를 모두 찾는 방어 코드는 서버 출력으로 확인하기 전까지 그대로 둘 만하다. 서버를 띄운 출력은 아직 없다.
- 1301행: "GLM 층 구성과 숫자를 뺐다"는 범위가 달라졌다. `data/reference_specs.json`(status partial)이 실제 KV 규격 클래스를 CPU에서 호출해 record 크기(main 1024, `fp8_ds_mla` 656, indexer 132, KDA conv 147,456 등)를 준다. block 크기(BF16 TP1 4352, TP4 1152)는 대역 backend로 얻은 값이라 시작 로그가 아니다(`docs/reference/specs.md`). `kv_math`가 숫자를 거부하는 정책을 바꿀지는 이 정정이 정하지 않는다.
- 578행(요청 목록 밖): `P5-21(미확인)`, `P5-22(미확인)`은 낡았다. 둘은 실측 행으로 바뀌었고 P5-21은 `코드 전용`, P5-22는 `코드 전용`이다. 요약 middleware 조건과 `reasoning` 미전송 설명은 행의 범위로 읽는다.
- Part 8: `part8.md`의 "설치도 실행도 하지 않았다"는 낡았다. LMCache v0.5.6을 GPU 확장 없이 빌드해 게이팅, SCHEDULER 생성자, 가짜 텐서 저장을 CPU에서 실행했고, 모델별 지원 상태 표에 `실제 클래스 호출` 표지를 더했다. 모델을 LMCache에서 돌린 실행은 없다(`docs/reference/lmcache.md`).
