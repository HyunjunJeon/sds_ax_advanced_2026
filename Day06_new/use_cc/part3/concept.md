# Part 3. Evidence·Checkpoint·Plan — 개념 정리

> **핵심 질문: 세션이 바뀌어도 일이 이어지고, "완료"가 거짓이 아니게 하려면 무엇을 파일로 남겨야 하는가?**

근거는 `Day06_new/docs/SOURCES.md`와 그 대장에 있다. 코드 줄 번호는 `vendor/autonomous-coding`(claude-quickstarts 커밋 `8ef47d71`) 기준이다.

---

## 1. 문제: 긴 일은 여러 세션에 걸치고, 세션은 기억하지 못한다

Anthropic의 Justin Young은 *Effective harnesses for long-running agents*(2025-11-26)에서 여러 문맥 창에 걸쳐 앱 하나를 만들게 하는 실험을 보고한다.
압축(compaction)만으로는 부족했다고 적는다.

> "However, compaction isn’t sufficient."

글의 표는 실패 양상 네 가지를 정리한다(본문은 2+1가지로 서술한다).

| 실패 양상 (원문 표) | 이 수업의 말로 |
|---|---|
| "Claude declares victory on the entire project too early." | 일부를 보고 전체를 끝났다고 한다 |
| "Claude leaves the environment in a state with bugs or undocumented progress." | 다음 세션이 이어받을 수 없는 상태로 끝난다 |
| "Claude marks features as done prematurely." | 확인하지 않고 완료 표시를 한다 |
| "Claude has to spend time figuring out how to run the app." | 매 세션이 실행 방법부터 다시 찾는다 |

해법은 두 역할이다.

> "an initializer agent that sets up the environment on the first run, and a coding agent that is tasked with making incremental progress in every session, while leaving clear artifacts for the next session."

## 2. 세 단어 = 세 파일

| 단어 | 답하는 질문 | 글과 예제의 파일 | 여섯 책임 |
|---|---|---|---|
| **Plan** | 무엇이 남았고, 각각 무엇이면 완료인가 | 기능 목록 JSON(예제 이름 `feature_list.json`). 기능마다 `passes` 칸 | 지침 |
| **Checkpoint** | 다음 세션은 어디서부터 이어 가나 | 진행 기록(`claude-progress.txt`), git 커밋, 실행 스크립트(`init.sh`) | 상태 |
| **Evidence** | 무엇을 근거로 완료라고 하나 | `passes` 표시와, 그 표시 전에 실행한 E2E 검사 | 검증·기록 |

원문에서 확인한 규칙들.

- 기능 목록은 처음에 모두 실패로 표시한다: "These features were all initially marked as “failing”"
- 코딩 에이전트는 `passes` 칸만 바꾼다: "We prompt coding agents to edit this file only by changing the status of a passes field"
- JSON을 고른 이유: "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files."
- 한 번에 하나: "the next iteration of the coding agent was then asked to work on only one feature at a time."

파일 이름에 대한 주의: 글 본문은 "feature list file"이라고만 부른다. `feature_list.json`은 예시 세션 기록과 동반 예제 README에 나오는 이름이다(`docs/sources/web.md` 2절 항목 6).

## 3. 동반 예제의 코드를 읽으면 보이는 것

글이 링크한 예제(`vendor/autonomous-coding`)를 읽으면, 세 파일 중 **무엇이 코드로 강제되고 무엇이 부탁인지**가 갈린다.

| 장치 | 근거 | 강제인가 부탁인가 |
|---|---|---|
| 반복마다 새 문맥(새 클라이언트) | `agent.py:158-159` | 코드(실행 경로) |
| 첫 반복은 초기화 프롬프트, 이후는 코딩 프롬프트. `feature_list.json`이 있으면 이어 가는 것으로 본다 | `agent.py:124-126`, `:161-166` | 코드 |
| "passes만 바꿔라. 기능을 지우거나 고치는 것은 CATASTROPHIC" | `prompts/initializer_prompt.md:53-57`, `prompts/coding_prompt.md:106-126` | **부탁(프롬프트)**. 이 파일의 편집을 막는 장치는 없다. 등록된 hook은 Bash 허용 목록 하나다(`client.py:113-117`) |
| 새 작업 전에 이미 통과한 기능 1~2개를 다시 검사 | `prompts/coding_prompt.md:46-59` | 부탁(프롬프트) |
| 통과 수 집계 | `progress.py:22-34` | 코드. 단, **적힌 값을 그대로 센다**. 다시 검사하지 않는다 |
| 언제 멈추나 | `agent.py:149-153` | 코드. `max_iterations`에서만 멈춘다. 모든 기능이 통과해도 하네스는 멈추지 않는다 |

정리하면, 이 예제에서 **Evidence는 에이전트가 스스로 쓰는 표시**다. 하네스는 그 표시를 세기만 한다.
그래서 같은 글은 마지막 실패 양상으로 "확인 없이 완료 표시하기"를 든다.

> "One final major failure mode that we observed was Claude’s tendency to mark a feature as complete without proper testing."

문서와 코드가 다른 곳도 하나 있다. README의 Bash 허용 명령 목록(`README.md:73-76`)에는 `cp`, `mkdir`, `chmod`, `pwd`, `init.sh`가 없지만 코드의 `ALLOWED_COMMANDS`(`security.py:15-41`)에는 있다. 문서와 코드가 다르면 코드를 따른다.

## 4. 완료를 선언하는 쪽과 인정하는 쪽을 나눈다

같은 회사의 다른 글(*Harness design for long-running application development*, Prithvi Rajasekaran, 2026-03-24)은 만든 쪽과 평가하는 쪽을 나눈다.

> "But tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work"

에이전트의 "완료"는 **주장**이다. 완료로 **인정**하려면 주장과 무관한 쪽이 다시 확인해야 한다. 이 수업은 그 확인을 네 가지로 본다.

| 확인 | 질문 | 실패하면 |
|---|---|---|
| 필수 검사가 있는가 | 요구사항마다 검사가 실제로 존재하는가 | 검사 없음 |
| 기준을 충족하는가 | **지금** 실행한 검사가 통과하는가 | 거짓 통과 주장 |
| 현재 산출물과 일치하는가 | 확인한 코드와 지금 코드가 같은가 | 오래된 증거 |
| 신뢰 기반이 그대로인가 | 검사 자체가 바뀌지 않았는가 | 신뢰 기반 변경 |

`tools/check_evidence.py`는 이 네 가지를 실험 폴더에서 확인하는 작은 완료 Gate다. 모델을 부르지 않는다.
여기서 "현재 산출물"은 **코드**다. 기록 파일만 바뀐 커밋은 코드의 리비전을 바꾸지 않는다. 그래서 `verified_at`(통과를 확인한 코드 커밋)을 "코드를 마지막으로 바꾼 커밋"과 비교한다.

## 5. 오늘의 실험 폴더: 회의실 예약 서비스

`setup_sandbox.py`는 저장소 밖에 작은 예약 서비스와 **이전 두 세션이 남긴 기록**을 만든다.

| 커밋 | 내용 |
|---|---|
| `2a12049` | 초기 설정: 작업 규칙(`CLAUDE.md`), 요구사항 R1~R7(`feature_list.json`), 검사(`test_reservation.py`) |
| `8d702a4` | R1·R2·R7 코드: 사용자마다 파일 하나에 저장 |
| `eded468` | 기록: R1·R2·R7 통과 (`verified_at` = `8d702a4`) |
| `0f09a2a` | R3 코드: `list`에 `include_others` 옵션 추가 |
| `1b53d8c` | 기록: R3 완료 (`verified_at` = `0f09a2a`). 진행 기록의 근거는 "직접 확인함" |

R1~R7은 이 과정 이론 강의의 회의실 예약 사례에서 왔다. R3는 "독립된 사용자 B가 조회하면 A가 등록한 같은 예약이 표시된다"이다.

이 폴더의 하네스는 위 예제를 작게 줄인 것이다.

- Plan: `feature_list.json`(R1~R7, `passes`, `verified_at`)
- Checkpoint: `progress.md`, git 커밋
- Evidence: `passes`와 `verified_at`. 그리고 `check_evidence.py`가 지금 다시 돌린 검사
- 실행 제어: `.claude/settings.json`이 검사·git 조회 명령을 허용하고, PreToolUse hook이 `test_reservation.py` 편집을 막는다. Hook은 종료 코드 2로 막는다(공식 문서: "Exit with code 2 to block the action.")

## 원문

- Anthropic, *Effective harnesses for long-running agents* — https://www.anthropic.com/research/effective-harnesses-for-long-running-agents
- anthropics/claude-quickstarts `autonomous-coding` — https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding (이 저장소 `vendor/autonomous-coding`, `vendor/SNAPSHOTS.md`)
- Anthropic, *Harness design for long-running application development* — https://www.anthropic.com/research/harness-design-long-running-apps
- Claude Code 공식 문서 Hooks — https://code.claude.com/docs/en/hooks
