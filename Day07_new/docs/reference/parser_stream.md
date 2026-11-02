# 실제 GLM 파서 스트리밍 실행 (저자용)

## 결과: 실행됨

`data/reference_parser_stream.json`의 `status`는 `ran`이다. 앞선 실행(`docs/REFERENCE_RUN.md` 대상 B)이 비워 둔 세 경로를 돌렸다. 스트리밍, 진짜 tokenizer의 token ID 판정, 진짜 chat template의 "생각 항상 켜짐" 판정이다.

읽는 범위를 먼저 정한다. 입력은 전부 사람이 만든 문자열이고 엔진과 모델은 돌리지 않았다. 엔진 종료(`stop`, `length`)와 종료 token도 사람이 정했다. 파서, tokenizer, detokenizer, `chat_completion_stream_generator`, `chat_completion_full_generator`는 v0.32.0(커밋 `5df63a7`)의 실제 코드다. **표의 근거 종류는 `실제 GLM 파서, 실제 tokenizer, 실제 serving 제너레이터, 구성 문자열, 모델 출력 아님, 라이브 서버 아님`이다.** Rust 파서는 돌리지 않았다.

## 환경과 입력

| 항목 | 값 |
|---|---|
| 실행 위치 | scratchpad의 `refrun/.venv` (저장소 `.venv`, `uv.lock`은 건드리지 않음). vLLM은 소스 트리를 `sys.path`에 넣어 import |
| tokenizer | `zai-org/GLM-5.3-Flash`, revision `46a050bec13002ad29ee795c16e61cf4fa3c4a9c`. 공개 저장소이고 gated가 아니라 접근 거부 없음 |
| 받은 파일 | `tokenizer.json`, `tokenizer_config.json`, `chat_template.jinja` 세 개. sha256은 JSON의 `tokenizer.files_sha256`. 가중치는 받지 않음 |
| 버전 | transformers 5.22.1, tokenizers 0.23.3, xgrammar 0.2.8 (`requirements/common.txt:29`의 고정값과 같음) |
| 유료 호출 | 없음 |

실행 스크립트는 `REFERENCE_RUN.md`와 같은 방식으로 scratchpad에만 두었다(`realrun/scripts/run_parser_stream.py`). 저장소에는 결과 JSON과 이를 재생하는 테스트만 있다.

```bash
cd refrun
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -P ../realrun/scripts/run_parser_stream.py \
  <scratchpad>/src/vllm-v0.32.0 <scratchpad>/realrun/glm53 \
  <저장소>/Day07_new/data/reference_parser.json <저장소>/Day07_new/data/reference_parser_stream.json
uv run --no-sync python -m pytest Day07_new/tests/test_reference_parser_stream.py -q   # 저장소 루트
```

흐름은 서버가 하는 순서를 따른다.

1. `ParserManager.get_parser("glm47", "glm47", enable_auto_tools=True, ...)`로 파서 클래스를 만든다(`vllm/entrypoints/openai/chat_completion/serving.py:161`). 진짜 tokenizer로 시작 검증(`validate_parser_tokenizer`)까지 통과했다.
2. `apply_chat_template`로 프롬프트를 렌더링하고 `adjust_request`를 부른다.
3. `tok.encode(raw)`의 token을 하나씩 실제 `FastIncrementalDetokenizer`에 넣어 `delta_text`를 얻고, 그 조각을 `RequestOutput`으로 싸서 실제 제너레이터에 넣는다. 제너레이터가 `parse_delta`를 부르고, `parse_delta`가 `extract_tool_calls_streaming`을 부른다. 호출 횟수는 행의 `stream.calls`에 있다. 8개 중 `no_call_missing_think_end`만 도구 단계에 들어가지 않아 0이다.
4. SSE 조각을 client처럼 모아 최종 `reasoning`, `content`, `tool_calls`, `finish_reason`을 만들고, 같은 입력의 `chat_completion_full_generator` 결과와 비교한다.

조각 크기를 4 token, 전체 한 번으로 바꿔도, `delta_token_ids`를 비워 텍스트 경로만 태워도 결과가 같았다(`variants`). 단 ID 없는 조각은 서빙에 없는 입력이고, 빈 마지막 조각이 `serving.py:661`의 분기로 버려져 `finish_reason`은 비교에서 뺐다.

## 8개 케이스

`엔진 종료`는 사람이 정한 값이다. 호출이 있는 문자열의 `stop`은 `<|observation|>`(154829), 없는 문자열은 `<|user|>`(154827)로 끝냈다. 둘 다 `generation_config.json`의 `eos_token_id`에 있다.

| id | 후보 | 엔진 종료 | 스트리밍 인자 | 비스트리밍 인자 | 스트리밍 `finish_reason` | 비스트리밍 `finish_reason` | 같은가 |
|---|---|---|---|---|---|---|---|
| `clean_call` | - | stop | `{"city": "서울"}` | `{"city": "서울"}` | `tool_calls` | `tool_calls` | 같음 |
| `reasoning_then_call` | - | stop | `{"city": "서울"}` | `{"city": "서울"}` | `tool_calls` | `tool_calls` | 같음 |
| `malformed_markup` | C7 | stop | `{"city": "서울` (닫히지 않음) | `{"city": "부산"}` | `tool_calls` | `tool_calls` | **인자 다름** |
| `truncated_call` | C2, C6 | length | `{"city": "서울` (닫히지 않음) | `{}` | `length` | `tool_calls` | **인자, `finish_reason` 다름** |
| `unknown_tool` | C3 | stop | 호출 없음 | 호출 없음 | `stop` | `stop` | 같음 |
| `bad_arg_type` | C4 | stop | `{"minutes": "곧", "label": "라면"}` | 같음 | `tool_calls` | `tool_calls` | 같음 |
| `no_call` | - | stop | 호출 없음 | 호출 없음 | `stop` | `stop` | 같음 |
| `no_call_missing_think_end` | - | stop | 호출 없음 (전부 reasoning) | 호출 없음 (전부 reasoning) | `stop` | `stop` | 같음 |

`reasoning`, `content`, 호출 존재 여부는 8개 모두 두 경로가 같다. 비스트리밍 결과는 8개 모두 가짜 vocab으로 돌린 `reference_parser.json`과 같다. 즉 앞선 실행의 비스트리밍 표는 진짜 tokenizer에서도 그대로다.

### 엔진 종료를 바꿔 넣은 `finish_reason`

호출이 추출된 행(8개 중 `clean_call`, `reasoning_then_call`, `malformed_markup`, `truncated_call`, `bad_arg_type` 5개와 아래 추가 케이스 `truncated_after_name`, `truncated_after_closed_pair`)에서 엔진 종료가 `stop`이면 두 경로 모두 `tool_calls`, `length`이면 스트리밍 `length`, 비스트리밍 `tool_calls`였다. 호출이 없으면 엔진 값이 그대로 나온다. `vllm_lab.agent_sim.finish_reason_rule`의 `auto` 규칙은 모든 행에서 실제 제너레이터와 같았다(`test_course_finish_reason_rule_matches_the_real_generators`).

### 잘린 위치 (06 셀 23의 네 위치)

| 위치 | id | 스트리밍 인자 | 비스트리밍 인자 | `finish_reason` (엔진 `length`) |
|---|---|---|---|---|
| 함수명 중간 | `truncated_mid_name` | 호출 없음 | 호출 없음 | 둘 다 `length` |
| 함수명 뒤 | `truncated_after_name` | `{}` | `{}` | 스트리밍 `length`, 비스트리밍 `tool_calls` |
| 첫 값 중간 | `truncated_call` | `{"city": "서울` | `{}` | 스트리밍 `length`, 비스트리밍 `tool_calls` |
| 닫힌 쌍 뒤 | `truncated_after_closed_pair` | `{"minutes": 5, "label": "라` | `{"minutes": 5}` | 스트리밍 `length`, 비스트리밍 `tool_calls` |

## 비스트리밍과 다른 점

1. **잘린 호출의 인자.** 비스트리밍은 닫힌 쌍만 남겨 올바른 JSON을 낸다. 스트리밍은 값을 먼저 내보내므로 닫히지 않은 JSON으로 끝난다. 최종 변환 결과가 이미 보낸 것보다 짧아 더 보낼 것이 없기 때문이다(`vllm/parser/engine/parser_engine.py:1076` 부근).
2. **`</tool_call>` 없이 다음 `<tool_call>`이 온 경우.** 비스트리밍은 뒤 호출(부산)이 남고 스트리밍은 앞 호출(서울)이 닫히지 않은 채 남는다. 남는 값이 반대다. 최종 변환 결과가 이미 보낸 접두사로 시작하지 않으면 나머지를 보내지 않는다(`parser_engine.py:1077`). 그리고 이때 `finish_reason`은 `tool_calls`다. **`tool_calls`로 정상 종료한 스트림의 인자도 JSON이 아닐 수 있다.**
3. **`finish_reason`.** 엔진 `length`에서 호출이 있으면 두 경로가 다르다(`serving.py:771-780`, `serving.py:1099-1103`).
4. **reasoning token 수.** 스트리밍의 `count_reasoning_tokens`는 `</think>` 앞 token 수보다 적다. 12개 중 11개, 15개 중 13개를 셌고, 모자란 수는 text가 빈 조각(한글 한 글자가 token 둘로 갈려 앞 token의 `delta_text`가 빈 경우)의 수와 같다. 비스트리밍은 12, 15로 맞다. 원인은 `vllm/parser/engine/streaming_parser_engine.py:252-256`에서 빈 조각의 token 수가 사라지는 것으로 읽힌다(코드 읽기, 실행으로 분리하지는 않음).

## token ID 판정

| 입력 | `is_reasoning_end` |
|---|---|
| 프롬프트만 (끝이 `<think>`) | 거짓 |
| 프롬프트 + 생각 중 | 거짓 |
| 프롬프트 + 생각 + `</think>` | 참 |
| 프롬프트 + 생각 + `</think>` + 답 | 참 |
| 프롬프트 + `<tool_call>` (`</think>` 없음) | 참 |
| 이전 턴에 `</think>`가 있고 새 프롬프트가 `<think>`로 끝남 | 거짓 |
| `<\|assistant\|>`로 끝남 (`<think>` 없음) | 거짓 |
| 빈 목록 | 거짓 |

- 생각 구간을 끝내는 token은 둘이다. `reasoning_end_token_ids`가 `</think>`(154842)와 `<tool_call>`(154843)이다. `find_reasoning_end`로 보면 앞의 것은 content가 아니고 뒤의 것은 content에 든다.
- `<think>`(154841)부터 `</arg_value>`(154850)까지 마크업은 한 token씩이고 `all_special_tokens`에 **들지 않는다.** 18개 특수 token은 `<|user|>`, `<|observation|>` 같은 것들이다. `skip_special_tokens=True`로 decode해도 마크업이 남고, `<|observation|>`만 사라진다. 근거 표 P6-36이 같은 결과를 싣는다.
- `adjust_request`는 `skip_special_tokens`를 참에서 거짓으로 바꿨다(P6-36의 코드 읽기와 같음).

## 항상 생각 판정

`_glm53_always_thinks(진짜 tokenizer)`는 참이다. 여섯 조건을 각각 확인했다(`vllm/parser/glm47_moe.py:88-97`). 렌더링한 프롬프트는 `enable_thinking=False`나 `thinking=False`를 넘겨도 `<|assistant|><think>`로 끝나며 템플릿에 스위치가 없다(`chat_template.jinja:256`). `Glm47MoeParser`에 두 값을 넣어도 `thinking_enabled`는 참이고 경고가 실제로 찍힌다. 대조군으로 템플릿에 `enable_thinking` 문자열을 더하면 판정이 거짓이 되고 파서가 생각 추출을 끈다. `enable_thinking=False`를 넣어도 `</think>` 없는 일반 답변은 전부 reasoning이다.

## 구조화 태그와 문법

`adjust_request`가 모델 없이 태그를 만들었다. GLM 기본 수준(`FUNCTION`)의 태그 그대로다. `get_temperature`의 `city`는 자유 텍스트, `set_timer`의 `minutes`는 `{"type": "integer"}` JSON 스키마다. 이 태그를 xgrammar로 컴파일해 입력 token을 하나씩 넣어 본 결과는 다음과 같다.

| id | 문법 통과 | 거절된 위치 |
|---|---|---|
| `clean_call`, `reasoning_then_call`(`</think>` 뒤), `no_call`(`</think>` 뒤), `no_call_missing_think_end` | 통과 | - |
| `truncated_call`, 잘린 위치 세 건 | 접두사까지 통과 | 끝까지 가기 전에 끊긴 것이라 문법 위반이 아니다 |
| `malformed_markup` | 거절 | 두 번째 `<tool_call>` token |
| `unknown_tool` | 거절 | `<tool_call>get` 뒤 `_h` |
| `bad_arg_type` | 거절 | `<arg_value>` 뒤 `곧`의 첫 token |

한계: 컴파일과 token 수락만 시험했다. 엔진의 sampling 마스크로 집행한 것이 아니고, 문법이 언제 켜지는지(P6-23)도 돌리지 않았다. `TokenizerInfo`의 `vocab_size`는 `len(get_vocab())`로 넘겼다.

## `tools`가 빈 경우와 reasoning 파서가 없는 경우

- `tools: []` 요청은 `ChatCompletionRequest`가 `VLLMValidationError`로 거절한다(`vllm/entrypoints/openai/chat_completion/protocol.py:946`). 파서까지 가지 않는다. `tools`를 아예 빼면 스트리밍, 비스트리밍 모두 호출도 content도 나오지 않는다(`omitted_tools_call`). 파서 클래스에 `tools=[]`를 직접 주면 이름 검사 없이 `get_humidity` 호출이 나온다.
- `--reasoning-parser` 없이 `--tool-call-parser glm47`만 쓰면 생각 글이 `</think>` 문자열까지 포함해 content에 그대로 들어간다(`tool_parser_without_reasoning_parser`). 호출 앞 공백 처리는 다르다. `reasoning_then_call`의 content 끝이 스트리밍은 `</think>\n`, 비스트리밍은 `</think>`다.

## 이 실행 당시 06에서 바꿀 곳 (이후 06과 근거 표에 반영함)

이 절의 셀 번호와 `지금` 칸은 이 실행 당시 기준이다. 이후 06의 셀 번호가 바뀌었다.

06의 스트리밍 주장 중 **행과 어긋나는 것은 없다.** 표지가 약하거나 빠진 것이 있고, 틀린 행 하나는 스트리밍이 아니라 요청 검증 쪽이다.

셀 번호는 노트북 JSON `cells` 배열의 0부터 센 인덱스다.

| 셀 | 지금 | 바꿀 내용 |
|---|---|---|
| 1 | `<tool_call>`이 특수 token인지 확인되지 않음 | 한 token이지만 `all_special_tokens`에 없음 (실행) |
| 13 | token ID 경로, chat template 판정, 스트리밍을 돌리지 않음 | `reference_parser.json`에 대해서만 맞는 문장이다. 이 기록을 함께 안내 |
| 22, 23 | 네 위치 중 하나만 돌림, 나머지 `코드 읽기` | 네 위치 모두 실행 결과, 스트리밍 칸 추가 |
| 25 | 스트리밍 선언되지 않은 이름 `코드 읽기` | 실행 결과 |
| 25 | `tools`가 빈 목록이면 이름 검사를 안 함 | **요청으로는 도달하지 못함.** 빈 배열은 요청 검증에서 거절된다. 파서 클래스에서만 맞다 |
| 30 | 비스트리밍에서는 JSON이 깨지지 않음 | 스트리밍에서는 깨진다는 실행 결과를 나란히 둘 수 있다 |
| 35 | 얕은 태그가 키와 값 타입을 고정 (`코드 읽기`) | 태그 JSON은 실제 코드 출력이고 xgrammar가 `곧`을 거절함. 엔진 집행은 여전히 미확인 |
| 38, 39, 40 | `finish_reason` 차이와 닫히지 않은 JSON이 `코드 읽기`, 스트리밍 인자는 이 표로 말할 수 없음 | 실제 제너레이터 결과. 엔진 종료는 가정이라는 단서는 유지 |
| 41 | 항상 생각 판정을 검증하지 못함, `</think>` 없는 일반 답변은 전부 reasoning | 실행 결과. 서버 관찰은 아니라는 단서 유지. `</think>` 없이 `<tool_call>`이 와도 생각 구간이 끝난다는 점(token ID 표) 추가 |
| 42 | reasoning 파서 없을 때 섞이는지 미확인(P6-21) | 파서 층에서는 섞임 (구성 문자열) |
| 48 | C3, C4, C7은 태그 없는 서버에서만 나올 것으로 읽힘 | 문법이 세 입력을 거절함을 실행으로 확인. 엔진 집행은 미확인 |
| 57 | `finish_reason` 차이는 코드 읽기, 구성 문자열 요약 | 실행 결과로 표지 변경. `malformed_markup`이 스트리밍에서는 서울 쪽이 닫히지 않은 채 남는다는 점 추가 |

새로 가르칠 만한 사실은 하나다. **`finish_reason`이 `tool_calls`여도 스트리밍 인자가 JSON이 아닐 수 있다(`malformed_markup`).** 코드 읽기 단계의 06은 `length`로 잘린 경우만 닫히지 않은 JSON을 말했다. 다만 이 입력은 기본 태그의 문법이 거절하는 입력이므로 태그가 없는 서버의 이야기다.

근거 표에서 영향을 받는 행은 P6-17(빈 `tools`), P6-19, P6-20, P6-21, P6-22, P6-36, C2, C3, C4, C6, C7이다. 이 실행 당시에는 고치지 않았고 이후 반영했다. `REFERENCE_RUN.md`의 "tokenizer 다운로드 없음"(14행)과 "tokenizer 대체물과 한계"(66-71행)도 이 기록과 함께 읽어야 한다.

## 증명한 것과 증명하지 않은 것

증명한 것
- 위 구성 문자열을 진짜 tokenizer의 token으로 잘라 넣었을 때 v0.32.0 Python 파서와 serving 제너레이터가 낸 값, 그리고 token ID 판정과 템플릿 판정.
- GLM 기본 태그를 컴파일한 문법이 위 입력 token을 받거나 거절한 위치.

증명하지 않은 것
- 실제 모델이 이런 문자열을 낸다는 것, 수업 Pod나 GPU 서버가 이렇게 동작한다는 것.
- 엔진이 문법을 집행해 이 입력들이 실제로 생성되지 않는다는 것.
- Rust 파서(`VLLM_USE_RUST_FRONTEND=1`) 동작. 레시피가 그 경로를 쓰므로 이 결과를 그대로 옮기지 않는다.
- `tool_choice`가 `required`, 이름 지정, `none`일 때의 스트리밍. `auto`만 돌렸다.

## 테스트

`tests/test_reference_parser_stream.py`는 저장된 JSON의 형태, 비교 칸의 재계산, 가짜 vocab 기록과의 일치, `finish_reason_rule`과의 일치, 06 문장과 행의 일치를 본다. 06 문장 대조는 표현이 남아 있을 때만 그 표현을 행과 맞춰 보고, 전부 사라지면 실패한다. 건너뛰기는 `status`가 `not_run`일 때뿐이다. JSON을 15가지로 망가뜨린 사본에서 15건 모두 해당 검사가 실패했다.
