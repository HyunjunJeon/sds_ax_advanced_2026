# Part 2. What is Agent Harness — 개념 정리

> **핵심 질문: 하네스는 무엇으로 이루어져 있고, 내가 쓰는 하네스에서는 어느 칸이 비어 있는가?**

근거는 `Day06_new/docs/SOURCES.md`와 그 대장에 있다. 코드 줄 번호는 `vendor/mini-coding-agent`(커밋 `717cae4f`) 기준이다.

---

## 1. 정의 세 가지

| 출처 | 정의 |
|---|---|
| Sebastian Raschka, *Components of A Coding Agent* (2026-04-04) | "Agent harness: the software scaffold around an agent that manages context, tool use, prompts, state, and control flow" |
| Birgitta Böckeler (martinfowler.com, 2026-04-02) | 하네스는 행동 **전에** 방향을 잡는 Guides(feedforward)와 행동 **뒤에** 관찰해 스스로 고치게 하는 Sensors(feedback)로 이루어진다 |
| shareAI-lab/learn-claude-code `README.md:162` | "The loop belongs to the agent. The mechanisms belong to the harness." |

Böckeler의 두 문장을 원문으로 본다.

> "Guides (feedforward controls) - anticipate the agent's behaviour and aim to steer it before it acts."
>
> "Sensors (feedback controls) - observe after the agent acts and help it self-correct."

한쪽만 있으면 어떻게 되는지도 적어 두었다.

> "an agent that keeps repeating the same mistakes (feedback-only) or an agent that encodes rules but never finds out whether they worked (feed-forward-only)."

## 2. 이 수업의 틀: 여섯 책임

하네스를 볼 때 이 수업은 여섯 책임 하나로 말한다.

| 책임 | 답할 질문 |
|---|---|
| 지침 | 목표·범위·완료 조건은 무엇인가? |
| 도구 | 관측과 변경을 어떻게 실행하는가? |
| 실행 제어 | 무엇을 허용·승인·중단하는가? |
| 상태 | 다음 세션이 무엇을 이어받는가? |
| 검증 | 어떤 근거로 완료를 인정하는가? |
| 기록 | 실패 원인과 변경을 설명할 수 있는가? |

폴더 이름(`tools/`, `session/`)과 책임을 1:1로 짝짓지 않는다. 한 모듈이 여러 책임을 맡기도 한다.

### 다른 자료의 틀과 맞춰 보기

오늘 보는 저장소들은 저마다 다른 틀을 쓴다. 같은 저장소 안에서도 틀이 둘인 경우가 있다.
아래 표는 **이 수업이 맞춘 대응(해석)** 이다. 원 저자가 이렇게 대응시킨 것이 아니다.

| 여섯 책임 | Raschka의 6 구성요소 (`mini-coding-agent/README.md:36-49`) | learn-harness-engineering 강의 L02의 5 하위 시스템 | learn-harness-engineering 하네스 분해 문서의 5 하위 시스템 | better-harness의 5 차원 | Böckeler |
|---|---|---|---|---|---|
| 지침 | 2 Prompt shape | Instructions, Scope | instructions | Task Understanding | Guides |
| 도구 | 1 Live repo context, 3 Structured tools | — | tools, environment | Controlled Execution | — |
| 실행 제어 | 3 validation and permissions, 6 bounded subagents | Scope | environment | Controlled Execution, Reliable Delivery | Guides·Sensors 중 강제하는 것 |
| 상태 | 4 Context reduction, 5 Transcripts·memory·resumption | State, Session lifecycle | state | Learning Capture | — |
| 검증 | (없음) | Verification | feedback | Change Validation | Sensors |
| 기록 | 5 Transcripts | Session lifecycle(인계 기록) | state | Learning Capture | — |

- learn-harness-engineering은 강의 L02에서 instructions·state·verification·scope·session lifecycle을, 하네스 분해 문서에서 instructions·tools·environment·state·feedback을 쓴다(`docs/sources/github.md` 6절). 같은 "다섯 하위 시스템"이라는 말이 두 가지 뜻이다.
- AHE(Agentic Harness Engineering) 논문 코드의 README는 진화시키는 하네스 구성요소로 system prompts, tool descriptions, tool implementations, middleware, skills, sub-agents, long-term memory를 든다(`README.md:37`). 다른 줄(`:194`)은 목록이 조금 다르다.
- 틀이 다르다는 것은 틀린 것이 아니다. **어느 틀로 말하는지 밝히고, 하나로 일관되게 말하는 것**이 중요하다.

## 3. 하네스 하나를 통째로 읽기: mini-coding-agent

`vendor/mini-coding-agent/mini_coding_agent.py`는 1,019줄짜리 파일 하나에 하네스 전체가 들어 있다. 모델은 로컬 Ollama다. 오늘은 실행하지 않고 읽는다.

### 진입점에서 따라가기

1. `main`(`:969`) → `build_agent`(`:912`)가 작업 폴더 정보, 세션 저장소, 모델 클라이언트를 만든다.
2. 요청 하나는 `MiniAgent.ask`(`:445`)가 처리한다.
3. `ask`의 루프(`:455-491`):
   - 단계 한도(`max_steps`, 기본 6, `:233`·`:962`) 안에서 모델을 부른다(`:457`).
   - 답이 도구 호출이면 `run_tool`(`:464`)로 실행하고 기록한다.
   - 답이 최종 답이면 기록하고 **그대로 끝낸다**(`:481-484`).
   - 한도에 걸리면 "멈췄다"는 문장을 돌려준다(`:486-491`).

### 여섯 책임으로 본 지도

| 책임 | 이 파일에서 맡는 곳 | 수준 |
|---|---|---|
| 지침 | 고정 규칙 문장(`:350-367`), 작업 폴더의 AGENTS.md·README.md 앞부분을 프롬프트에 넣기(`:14`, `:104-113`, `:373`) | 실행 경로에서 확인 |
| 도구 | 도구 표(`:282-328`)와 각 도구 함수(`:742-842`) | 실행 경로에서 확인 |
| 실행 제어 | 도구 관문 순서: 없는 도구 → 인자 검증 → 같은 호출 반복 거절 → 위험 도구 승인 → 실행·출력 자르기(`:496-515`). 승인 정책 ask/auto/never(`:602-613`). 파일 경로가 작업 폴더를 벗어나면 거절(`:734-740`). 하위 에이전트는 읽기 전용·깊이 1(`:847-866`) | 실행 경로에서 확인 |
| 상태 | 세션을 기록할 때마다 JSON으로 저장(`:146-164`, `:433-435`), 작은 작업 기억(task·files·notes, `:249-255`, `:437-443`), 오래된 기록 줄이기(`:390-417`), `--resume`(`:922-934`) | 실행 경로에서 확인 |
| 검증 | **없다.** 모델이 최종 답을 내면 끝이다(`:481-484`). `validate_tool`(`:536`)은 도구 **인자**를 검사할 뿐 작업 **결과**를 검사하지 않는다 | 실행 경로에서 확인 |
| 기록 | 세션 JSON에 대화와 도구 결과가 남는다. 승인 거절은 도구 결과 문자열("error: approval denied")로만 남는다(`:510-511`) | 실행 경로에서 확인 |

눈여겨볼 곳 두 개.

- **실행 제어는 승인에 기대고 격리는 없다.** `run_shell`은 `shell=True`로 작업 폴더에서 실행되고, 파일 도구와 달리 경로 검사가 없다(`:796-810`). 도움말은 `--approval auto`가 "grants the model arbitrary command execution and file writes"라고 적는다(`:960`).
- **"멈췄다"도 결과다.** 한도에 걸린 요청은 실패를 숨기지 않고 문장으로 돌려준다(`:486-491`). 미해결 종료는 정당한 결과다.

## 4. 내가 쓰는 하네스의 지도

Claude Code는 시작한 폴더에 따라 함께 싣는 것이 다르다(공식 문서, `docs/sources/web.md` 6(d)).

- 지침: "Claude Code loads CLAUDE.md and CLAUDE.local.md from your current working directory and every directory above it." 위 어디에도 CLAUDE.md가 없을 때만 AGENTS.md를 읽는다.
- 상태: auto memory는 `~/.claude/projects/<project>/memory/`에 있고, `<project>`는 git 저장소에서 정해진다. MEMORY.md의 앞 200줄(또는 25KB)이 매 대화 시작에 실린다.
- 기록: 세션은 `~/.claude/projects/<작업 폴더 경로를 바꾼 이름>/<세션 ID>.jsonl`에 남는다.

`tools/harness_inventory.py <폴더>`는 이 규칙대로 설정 파일을 읽어 **개수만** 센다. 실제로 실린 것은 그 폴더에서 연 세션 안의 `/context`와 `/memory`로 확인한다.
도구의 기본 출력에는 파일 경로, Skill 이름, MCP 서버 이름, 설정 값이 없다. 그래서 조교 세션에서 `!`로 실행해도 된다.

지도를 그릴 때 볼 것은 "무엇이 있나"보다 **"어느 칸이 비어 있나"** 다. better-harness의 README가 이 구분을 정확히 적는다.

> "configured assets can establish that a mechanism exists, but only linked task evidence can establish that it was used or improved an outcome." (`QoderAI/better-harness README.md:159-161`)

설정이 있다는 것은 장치가 **있다**는 증거일 뿐, 그 장치가 **쓰였거나 효과가 있었다**는 증거가 아니다. 그 증거는 실습에서 세션 기록으로 본다.

## 원문

- Sebastian Raschka, *Components of A Coding Agent* — https://magazine.sebastianraschka.com/p/components-of-a-coding-agent
- rasbt/mini-coding-agent — https://github.com/rasbt/mini-coding-agent (이 저장소 `vendor/mini-coding-agent`, `vendor/SNAPSHOTS.md`)
- Birgitta Böckeler — https://martinfowler.com/articles/harness-engineering.html
- walkinglabs/learn-harness-engineering(한국어판 `docs/ko/`) — https://github.com/walkinglabs/learn-harness-engineering
- QoderAI/better-harness — https://github.com/QoderAI/better-harness
- Claude Code 공식 문서 Memory — https://code.claude.com/docs/en/memory
