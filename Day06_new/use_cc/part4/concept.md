# Part 4. 오픈소스 Agent Harness 구조 분석 — 개념 정리

> **핵심 질문: 남이 쓴 하네스 분석을, 소스로 확인하기 전에 믿어도 되는가?**

이 Part는 `Day06/`에 있는 하네스 스냅샷 세 개를 **읽기 전용으로** 본다. 실행하거나 고치지 않는다(`Day06_new/AGENTS.md` 2장).

---

## 1. 세 하네스, 세 가지 설계

| 폴더 | 스냅샷 | 한 줄로 | 루프 본체 |
|---|---|---|---|
| `Day06/pi` | earendil-works/pi `71dca871` (2026-09-11) | 코어는 작게, 나머지는 확장으로 | `Day06/pi/packages/agent/src/agent-loop.ts:156` `runLoop` (파일 전체 803줄) |
| `Day06/deepseek-harness` | deepseek-ai/deepseek-harness `c291e796` (2026-09-10) | 루프까지 모든 것이 plugin | `Day06/deepseek-harness/packages/core/agent-loop/src/agent.ts:72` `ReactLoopAgent` |
| `Day06/ouroboros` | Q00/ouroboros `97098488` (2026-09-13) | 루프를 직접 돌리지 않고 기존 에이전트를 런타임으로 부르는 바깥 계층 | `Day06/ouroboros/src/ouroboros/orchestrator/runner.py:8454` `execute_seed` |

pi의 README는 **넣지 않은 것**을 먼저 적는다(`Day06/pi/packages/coding-agent/README.md:499-507`).

| 넣지 않은 것 | pi가 권하는 대안 |
|---|---|
| "**No MCP.**" | README가 딸린 CLI 도구(Skill) 또는 확장 |
| "**No sub-agents.**" | tmux로 pi 여러 개, 또는 확장 |
| "**No permission popups.**" | 컨테이너에서 실행, 또는 확장으로 확인 흐름 |
| "**No plan mode.**" | "Write plans to files", 또는 확장 |

"pi 코어에는 서브에이전트가 없다"와 "pi로는 서브에이전트를 쓸 수 없다"는 다른 말이다. 기능을 물으면 **코어·기본 번들·예제·확장**을 나눠 답한다.

deepseek-harness의 문서는 반대 방향을 적는다(`Day06/deepseek-harness/docs/architecture.md:11`).

> "Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself, so each is replaceable from configuration."

## 2. 읽는 법: 진입점에서 호출을 따라간다

1. **진입점을 정한다.** CLI의 `main`이나 부팅 함수, 또는 위 표의 루프 본체.
2. **호출을 따라간다.** 함수 이름으로 grep하고, 그 함수가 부르는 것을 연다. 수만 줄짜리 파일을 통째로 읽지 않는다.
3. **근거 수준을 붙인다.**

   | 수준 | 뜻 |
   |---|---|
   | 실행 경로에서 확인 | 진입점에서 호출을 따라가 도달했다 |
   | 코드에 정의만 확인 | 정의는 있지만, 기본 실행 경로에 연결됐는지는 따라가지 않았다 |
   | 문서에만 있음 | README·docs에만 있고 코드로 확인하지 않았다 |
   | 추정 | 이름이나 구조로 짐작했다 |

4. **"정의돼 있다"와 "동작한다"를 구분한다.** 파일이 있고 이름이 그럴듯해도, 기본 설정에서 그것을 불러오지 않으면 동작하지 않는다.

## 3. 남의 분석을 검증한다

walkinglabs/learn-harness-engineering(MIT, 한국어 번역 있음)은 Pi·Claude Code·Codex·DeepSeek의 하네스를 분해한 글을 공개했다(2026-08).
좋은 자료다. 그런데 이런 글에는 세 가지 함정이 있다.

- **어느 버전을 분석했는지 밝히지 않는다.** 두 분석 글 모두 대상 커밋을 적지 않았다. 우리 스냅샷은 그 글보다 3~4주 늦다.
- **문서를 인용한 문장은 코드 확인이 아니다.** 문서 문장을 그대로 옮긴 주장은 "문서와 일치"일 뿐이다.
- **고유명사가 섞인다.** 여러 하네스를 연달아 분석하면 한 하네스의 이벤트 이름이 다른 하네스의 설명에 들어갈 수 있다.

그래서 이 Part의 미션은 그 글의 주장 세 개를 **우리 스냅샷으로** 판정하는 것이다. 판정은 네 가지 중 하나다: 일치 / 부분 일치 / 불일치 / 스냅샷으로 판정 불가.

## 4. 판정을 여섯 책임으로 옮긴다

주장 하나를 판정하면, 그 주장이 여섯 책임 중 무엇에 관한 것인지도 함께 적는다. 예를 들어 "요청 메시지를 로그에서 다시 만든다"는 기록 책임이고,
"그것을 실행 중에 단언한다"는 검증 책임이다. 한 문장 안에 책임이 둘 들어 있으면, 둘을 따로 판정할 수 있다.

## 원문

- walkinglabs/learn-harness-engineering 하네스 분해 문서(한국어) — https://github.com/walkinglabs/learn-harness-engineering/tree/a9342ff471f2c0e60be0c08b9f4a7c502df4e442/docs/ko/harness-designs
- earendil-works/pi — https://github.com/earendil-works/pi
- deepseek-ai/deepseek-harness — https://github.com/deepseek-ai/deepseek-harness
- Q00/ouroboros — https://github.com/Q00/ouroboros
