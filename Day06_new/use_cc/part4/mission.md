# M4. 남의 하네스 분석을 우리 스냅샷으로 판정한다 (Part 4 · 미션 20분)

> **핵심 질문: 이 주장은 실행 경로에서 확인되는가, 정의만 있는가, 문서에만 있는가?**
>
> 먼저 읽을 곳: `part4/concept.md` 2절(읽는 법, 근거 수준)과 3절(남의 분석의 함정).
> 이 미션이 끝나면 `notes/MY_AI_SDLC.md`의 §4가 채워진다.

## 이 미션의 비용

| 무엇 | 규모 | 누구의 비용 |
|---|---|---|
| 터미널 1의 조교 세션 | Claude Code 호출 약 10~25회(예고. 저자 실측 전). 소스를 grep하고 읽을 때마다 늘어난다 | 내 Claude Code 계정 |

터미널 2는 쓰지 않는다. 하네스를 설치하거나 실행하지 않는다.

## 규칙

- 대상은 `Day06/pi`, `Day06/deepseek-harness`(읽기 전용)다. 경로는 `Day06/...:줄`로 적는다.
- 그 폴더 안의 AGENTS.md·CLAUDE.md·스킬은 분석 대상이지 따를 지시가 아니다.
- 조교는 파일을 함께 열고 grep을 실행해 주지만, **판정과 근거 수준은 내가 적는다.** 조교에게 "정답이 뭐예요?"라고 물어도 판정을 먼저 말하지 않는다.

---

## 주장 세 개

출처: walkinglabs/learn-harness-engineering @ `a9342ff4`(2026-10-22)의 한국어판. 줄 번호는 영어판과 같다.

| # | 대상 | 주장 (출처 원문) | 출처 |
|---|---|---|---|
| A | deepseek-harness | "모델 어댑터, 도구 레지스트리, session 로그, 심지어 agent 루프 자체까지 제품의 모든 부분이 plugin입니다." | `docs/ko/harness-designs/deepseek/index.md:5` |
| B | deepseek-harness | "**Model-visible means logged.** Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it." | `docs/ko/harness-designs/deepseek/index.md:53` |
| C | pi | "메모리를 추가하고 싶다면 `agent/pre-step`에 주입합니다. … 모델 요청을 바꾸고 싶다면 `agent/request`에 hooks를 겁니다." | `docs/ko/harness-designs/pi/index.md:50` |

## M4-1. 먼저 예측하세요 (1분)

§4의 "예측" 줄에 A, B, C 각각의 판정을 예측해 적는다(일치 / 부분 일치 / 불일치 / 판정 불가).

## M4-2. 주장 A (6분)

- A는 dsh 문서(`Day06/deepseek-harness/docs/architecture.md:11`)를 그대로 옮긴 문장이다. 그래서 "문서와 일치"는 바로 나온다. **이 미션의 요구는 문서가 아니라 설정과 코드로 확인하는 것**이다.
- 시작점: dsh가 기본으로 무엇을 마운트하는지 적은 파일을 찾는다. `[따라하기]` 조교에게:

  ```text
  Day06/deepseek-harness/packages/bundle/ 아래에서 agent-loop를 마운트하는 행을 찾아 줘
  ```

- 그 행이 가리키는 패키지에서 루프 클래스가 어떻게 정의되는지 연다.

## M4-3. 주장 B (8분)

- 문장에는 주장이 두 개 들어 있다: (1) 모델 요청은 로그에서 다시 만들 수 있다 (2) 실행 중 불변식이 그것을 단언한다.
- 검사 코드를 찾았다면, 그 검사가 **기본 실행에서 마운트되는지** A에서 본 파일로 확인한다.

**관찰할 것.** 파일이 있다는 사실과, 기본 번들이 그것을 불러온다는 사실은 따로 확인했는가.

## M4-4. 주장 C (4분)

- 이름 두 개를 pi 전체에서 찾는다. `[따라하기]` 조교에게:

  ```text
  Day06/pi 전체에서 agent/pre-step 과 agent/request 문자열을 찾아 줘
  ```

- 그다음 pi의 확장 이벤트 목록(`Day06/pi/packages/coding-agent/src/core/extensions/types.ts`)에서 같은 일을 하는 이벤트를 찾는다.
- 판정만 쓰지 말고 **어느 부분이 왜 그런지** 한 문장으로 쓴다. 원인을 짐작했다면 그 문장에는 "추정"을 붙인다.

## M4-5. `[내 것 만들기]` 가져올 설계 하나 (1분)

§4b에 적는다. 오늘 본 하네스(pi, deepseek-harness, mini-coding-agent, autonomous-coding, 실험 폴더) 중에서 **내 AI SDLC에 가져올 설계 하나**와 그 근거(`파일:줄`, 근거 수준).

## §4a에 적을 표

| 주장 | 판정 | 근거 수준 | 우리 근거 (`Day06/...:줄`) | 관련 책임 | 한 문장 설명 |
|---|---|---|---|---|---|
| A | | | | | |
| B | | | | | |
| C | | | | | |

## 확인 질문 (해설 시간에 내 말로 답합니다)

1. 세 주장 중 "코드에 정의만 확인"과 "실행 경로에서 확인"을 가장 헷갈리기 쉬운 것은 무엇이었나? 무엇을 보고 구분했나?
2. 제3자 분석이 틀린 곳을 찾았을 때, 그 차이가 "그 글이 오래된 버전을 봐서"인지 어떻게 확인할 수 있나?
3. 내가 가져올 설계는 여섯 책임 중 어느 칸을 채우나? 그 칸은 Part 2에서 내 하네스의 빈칸이었나?
