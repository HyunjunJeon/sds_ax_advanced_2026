# Rust GLM 파서 실행 결과 (vLLM v0.32.0)

원자료: `Day07_new/data/reference_parser_rust.json`. Python 쪽 기준은 `Day07_new/data/reference_parser.json`.

## 1. 무엇을 돌렸나

- 상태: `ran`. `rust/` 를 scratchpad에 복사해 `vllm-parser` crate만 빌드하고 테스트 1개로 8개 사례를 먹였습니다. 서버, GPU, 네이티브 의존성 문제는 없었고 빌드는 약 25초였습니다.
- 도구: cargo 1.97.1, rustc 1.97.1.
- 도구 파서: `Glm45MoeToolParser`(함수 이름 뒤 구분자가 개행 필수), `Glm47MoeToolParser`(공백, 개행, 바로 `<arg_key>` 허용) (`rust/src/parser/src/tool/glm_xml/mod.rs:39-46`).
- 추론 파서: `reasoning/mod.rs:69-70`이 `glm45`는 `Glm45ReasoningParser`, `glm47`은 `Glm47ReasoningParser`에 묶고, 후자는 `DeepSeekV3ReasoningParser`의 별칭입니다(`reasoning/mod.rs:62`).
- 한계: 토크나이저는 `<think>`, `</think>` 두 토큰만 가진 TestTokenizer입니다. 진짜 GLM tokenizer, chat 계층, tool_choice, unified 파서, HTTP 응답 모양은 실행하지 않았습니다.
- Rust 추론 파서는 프롬프트 토큰으로 시작 상태를 정합니다(`delimited.rs:123`). 그래서 두 가지로 돌렸습니다. `prompt_plain`은 프롬프트에 `<think>`가 없는 경우, `prompt_think_open`은 템플릿이 `<think>`를 미리 채운 경우입니다. 또 각 경우를 한 덩어리(whole)와 5글자씩 스트리밍(stream5)으로 돌렸고, **8개 사례 모두 두 방식의 결과가 같았습니다.**

## 2. 사례별 결과

표기: 호출 = 도구 호출 수, 오류 = 도구 파서가 오류를 돌려줌. glm47 열이 glm45와 같으면 "동일".

| 사례 | Python(reference_parser.json) | Rust prompt_plain, glm47 | Rust prompt_plain, glm45 | Rust prompt_think_open (glm45, glm47) |
|---|---|---|---|---|
| clean_call | 호출 1 (city=서울) | 호출 1 | 오류 (개행 구분자 없음) | 전부 reasoning, 호출 0, 오류 없음 |
| reasoning_then_call | reasoning 분리, 호출 1 | 추론 분리 없음(시작 상태가 본문), 그래도 호출 1 | 오류 | reasoning 분리됨. glm47 호출 1, glm45 오류 |
| malformed_markup | 호출 1 (부산만) | 오류 | 오류 | 전부 reasoning, 호출 0 |
| truncated_call | 호출 1, 인자 `{}` | 오류 `incomplete GLM MoE tool call` | 동일 | 전부 reasoning, 호출 0 |
| unknown_tool | 호출 0 (버려짐) | 호출 1 (`get_humidity`가 그대로 나옴) | 오류 | 전부 reasoning, 호출 0 |
| bad_arg_type | 호출 1, minutes="곧" | 호출 1, minutes="곧" | 오류 | 전부 reasoning, 호출 0 |
| no_call | reasoning과 content 분리 | 분리 안 됨, content에 `</think>` 포함 | 동일 | 분리됨 |
| no_call_missing_think_end | 전부 reasoning | 전부 content | 동일 | 전부 reasoning |

## 3. glm45와 glm47의 차이

- 도구 파서에서 갈립니다. 수업 사례는 이름 바로 뒤에 `<arg_key>`가 붙는 형태라 glm45(개행 필수)는 `tool parser parsing failed` 오류를 내고, glm47은 호출을 냅니다(`glm47_moe.rs:9-12` 주석, `mod.rs:39-46`).
- 추론 파서는 둘 다 `<think>`/`</think>` 분리를 하고, glm45만 시작 앞과 종료 뒤에 `\n`을 한 개 흡수합니다(`reasoning/glm45.rs:25-26`). `reasoning_then_call`에서 glm47의 content는 `\n<tool_call>...`로 개행이 남고, glm45는 개행이 지워집니다. 도구 파서는 두 경우 모두 앞 개행을 처리합니다.
- 일반 프롬프트에서는 8개 중 4개(`clean_call`, `reasoning_then_call`, `unknown_tool`, `bad_arg_type`)가 glm45 오류, glm47 호출로 갈렸고, 나머지 4개(호출 없는 2개와 두 이름 모두 오류인 `malformed_markup`, `truncated_call`)는 같았습니다. `<think>`를 연 프롬프트에서는 `reasoning_then_call` 1개만 갈렸습니다(`reference_parser_rust.json`의 `glm45_equals_glm47`).

## 4. Python 파서와 다른 점

1. **시작 상태.** Python 기록은 `</think>`가 있으면 앞을 reasoning으로, 없으면 전체를 reasoning으로 둡니다. Rust는 프롬프트가 `<think>`로 끝났는지로 정하고, 프롬프트에 경계가 없으면 본문 전체를 content로 봅니다. 그래서 같은 문자열이 프롬프트 상태에 따라 완전히 다르게 나뉩니다.
2. **잘린 호출.** Python은 `{}` 인자 호출을 만들었지만 Rust는 `incomplete GLM MoE tool call` 오류입니다(`mod.rs:136`).
3. **깨진 마크업.** Python은 마지막 호출(부산)을 살렸지만 Rust는 본문에 `<tool_call>`이 중첩되면 파싱 오류입니다.
4. **선언하지 않은 도구.** Python은 버렸지만 Rust 파서는 `get_humidity`를 호출로 내보냅니다. 파서 crate에도 `rust/src/chat/src`에도 이름 거르는 코드는 grep으로 못 찾았습니다(렌더러만 걸림). 다만 chat 계층을 끝까지 돌리지 않았으므로 "서버가 그렇게 동작한다"까지는 아닙니다.
5. **인자 직렬화.** Rust는 압축 JSON(`{"city":"서울"}`)이고 Python 기록은 공백이 있는 `{"city": "서울"}`입니다. 값은 같습니다. 잘못된 타입(`minutes="곧"`)은 양쪽 모두 문자열로 남깁니다.
6. **스트리밍.** Rust는 5글자 단위 스트리밍과 한 번에 주기가 8개 사례에서 같은 결과를 냈습니다. Python 쪽 스트리밍은 `reference_parser.json`에서 실행하지 않았으므로 비교 대상이 없습니다.

## 5. 01, 06 문장 중 코드 읽기에서 실행 근거로 올릴 수 있는 것

이 실행 당시의 목록입니다. 이후 06에 반영했고 줄 번호는 그때 기준입니다.

`06-Tool-Calling-Errors.ipynb`
- 2269행 근처, "끝에서 열린 호출이 남으면 `incomplete GLM MoE tool call` 오류" (P6-29): `truncated_call`로 실행 확인. 근거 종류를 "코드 읽기"에서 "Rust 파서 실행(TestTokenizer, 문자열 경로)"로 올릴 수 있습니다.
- 2355행 표의 "선언하지 않은 도구: 거르는 코드를 못 찾음, 같다고 말할 수 없음": `unknown_tool`에서 Rust 파서는 호출을 내보냈습니다. "파서 수준에서는 거르지 않음(실행 확인), chat 계층은 미실행"으로 올릴 수 있습니다.
- 610행 "Rust 파서는 돌리지 않았습니다": 이 문장은 이제 사실과 다릅니다. 문자열 경로는 돌렸다고 고쳐야 합니다.
- 올릴 수 없는 것: 상태 코드, 스트림 이벤트, `finish_reason`(P6-30), glm45와 glm47 이름 혼용의 서버 수준 영향(P6-04 중 파서 차이는 위 3절로 확인했지만 서버 동작은 미확인), 수업 Pod의 frontend.
- 새로 말할 수 있는 것: 수업 사례 형식(이름 바로 뒤 `<arg_key>`)에서는 glm45 이름을 쓰면 Rust 도구 파서가 오류를 냅니다.

`01-Serving-Basics.ipynb`
- Rust 관련 문장(33, 90, 908, 2875행)은 frontend 선택, API server 개수, 공식 README 소개에 관한 것이고 파서 동작 문장이 없습니다. 이번 실행으로 올릴 문장은 없습니다.
