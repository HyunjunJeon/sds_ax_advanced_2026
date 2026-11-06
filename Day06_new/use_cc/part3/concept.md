# Part 3. Evidence·Checkpoint·Plan (개념 15분 + 시연 10분)

## 핵심 질문

> **다음 세션이나 되감기 뒤에 이어받는 것은 무엇이고, 완료는 무엇으로 인정하는가?**

이 문서의 Claude Code 사실은 `Day06_new/docs/sources/claude_code/`의 근거 대장에 항목이 있는 것만 적는다. 문장 뒤의 `S13` 같은 표시는 그 항목 번호이고, 누르면 대장 파일로 간다. 대장에 없는 것은 쓰지 않았고, 확인하지 못한 것은 "확인 필요"로 적었다. 항목의 제목과 공식 문서 주소는 맨 끝 "근거"에 있다. 이 Part의 미션은 `mission.md`에 있다. 코드 줄 번호는 `vendor/autonomous-coding`(claude-quickstarts 커밋 `8ef47d71`) 기준이다.

---

## 1. 문제: 긴 일은 여러 세션에 걸치고, 세션은 기억하지 못한다

세션은 서로 독립이고, 새 세션은 빈 맥락으로 시작한다 ([S9](../../docs/sources/claude_code/04_state.md), [I9](../../docs/sources/claude_code/01_instructions.md)). 긴 일을 이어 가려면 다음 세션이 읽을 것을 파일로 남겨야 한다.

Anthropic의 Justin Young은 *Effective harnesses for long-running agents*(2025-11-26)에서 여러 맥락 창에 걸쳐 앱 하나를 만들게 하는 실험을 보고한다. 압축만으로는 부족했다고 적는다.

> "However, compaction isn’t sufficient."

글이 든 실패 양상과 이 수업의 말은 다음과 같다.

| 실패 양상 (원문 표) | 이 수업의 말로 |
|---|---|
| "Claude declares victory on the entire project too early." | 일부를 보고 전체를 끝났다고 한다 |
| "Claude leaves the environment in a state with bugs or undocumented progress." | 다음 세션이 이어받을 수 없는 상태로 끝난다 |
| "Claude marks features as done prematurely." | 확인하지 않고 완료 표시를 한다 |
| "Claude has to spend time figuring out how to run the app." | 매 세션이 실행 방법부터 다시 찾는다 |

## 2. 세 단어 = 세 파일

| 단어 | 답하는 질문 | 글과 예제의 파일 | 여섯 책임 |
|---|---|---|---|
| **Plan** | 무엇이 남았고, 각각 무엇이면 완료인가 | 기능 목록 JSON(예제 이름 `feature_list.json`). 기능마다 `passes` 칸 | 지침 |
| **Checkpoint** | 다음 세션은 어디서부터 이어 가나 | 진행 기록, git 커밋, 실행 스크립트 | 상태 |
| **Evidence** | 무엇을 근거로 완료라고 하나 | `passes` 표시와, 표시 전에 실행한 검사 | 검증·기록 |

이 수업이 쓰는 정의는 이렇다.

- **Plan**: 요구사항 목록과 각 요구사항의 완료 기준. 실험 폴더에서는 `feature_list.json`(R1~R7)이다.
- **Checkpoint**: 다음 세션이 이어받는 진행 기록(`progress.md`)과 git 커밋.
- **Evidence**: 완료를 인정하는 근거. 에이전트가 적은 `passes` 표시가 아니라, 지금 다시 돌린 검사의 결과다 (`tools/check_evidence.py`).

원문이 정한 규칙은 이렇다: 기능 목록은 처음에 모두 실패로 표시한다. 코딩 에이전트는 `passes` 칸만 바꾼다("We prompt coding agents to edit this file only by changing the status of a passes field"). JSON을 고른 이유는 "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files."이다. 한 번에 기능 하나만 맡긴다. `feature_list.json`은 글 본문이 아니라 예시 세션 기록과 동반 예제 README에 나오는 이름이다.

## 3. Checkpoint라는 말의 두 뜻

같은 단어가 두 가지를 가리킨다. 나란히 놓고 본다.

| | 이 수업의 Checkpoint | Claude Code의 checkpoint |
|---|---|---|
| 정체 | 진행 기록(`progress.md`) + git 커밋 | 턴을 시작하는 프롬프트마다 자동으로 생기는 되감기 스냅샷 ([S13](../../docs/sources/claude_code/04_state.md)) |
| 누가 만드나 | 에이전트 또는 사람이 의도해서 | Claude Code가 자동으로 |
| 어디에 저장되나 | 작업 폴더와 git | 대화와 함께 저장되어, 세션을 재개한 뒤에도 `/rewind`가 된다 ([S13](../../docs/sources/claude_code/04_state.md)) |
| 얼마나 가나 | git 커밋은 영구 | 세션당 최근 100개, 마지막 저장 뒤 기본 약 30일 ([S16](../../docs/sources/claude_code/04_state.md)) |
| 원격 작업 | 해당 없음 | 데이터베이스·API·배포 같은 원격 작업은 대상이 아니다 ([S13](../../docs/sources/claude_code/04_state.md)) |

공식 문서는 checkpoint가 "빠른 세션 단위 복구"를 위한 것이고, 영구한 이력과 협업에는 git 같은 버전 관리를 계속 쓰라고 적는다 ([S15](../../docs/sources/claude_code/04_state.md)). 오래가는 쪽은 git 커밋이다. 큰 변경 전에는 커밋부터 한다.

## 4. 되감기: `/rewind`와 Esc Esc

- 여는 법: `/rewind`, 또는 입력창이 비어 있을 때 Esc를 두 번 ([S14](../../docs/sources/claude_code/04_state.md), [K1](../../docs/sources/claude_code/07_commands_cli.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)). 입력창에 글이 있으면 Esc 두 번은 글을 지운다 ([S14](../../docs/sources/claude_code/04_state.md)).
- 고르는 것 다섯 ([S14](../../docs/sources/claude_code/04_state.md)):

| 선택 | 하는 일 |
|---|---|
| 1 Restore code and conversation (코드와 대화) | 코드와 대화를 그 지점으로 되돌린다 |
| 2 Restore conversation (대화만) | 그 메시지로 되감되 현재 코드는 둔다 |
| 3 Restore code (코드만) | 파일 변경만 되돌리고 대화는 둔다 |
| 4 Summarize from here (여기서부터 요약) | 그 지점부터의 대화를 요약해 맥락 창을 비운다. 파일은 바꾸지 않는다 |
| 5 Summarize up to here (여기까지 요약) | 그 지점까지의 대화를 요약한다. 파일은 바꾸지 않는다 |

화면의 경고 문구: "Restored files go back whole, losing later changes by anyone. Bash changes to other files are not undone." (2.1.318 대화형 화면, 저자 확인)

- 고르는 기준은 실패 유형이다. 코드만 틀렸으면 코드만 되감아 대화의 맥락을 지키고, 대화가 틀어졌으면 대화를 되감는다.
- 코드 복원 선택지는 그 지점 뒤에 추적된 파일 변경이 있을 때만 나온다 ([S14](../../docs/sources/claude_code/04_state.md)).
- checkpoint가 무엇을 되돌리고 무엇을 못 되돌리는지의 경계는 실험 4에서 먼저 예측해 보고, 이 문서 맨 끝 "실험 4 뒤에 읽는다"에서 맞춰 본다.

## 5. 세션: 이어받기, 이름, 분기

| 하고 싶은 일 | 방법 | 근거 |
|---|---|---|
| 같은 세션을 이어서 | `claude --continue`(현재 폴더의 가장 최근 세션), `claude --resume`. 같은 세션 ID에 새 메시지를 이어 붙인다 | [S8](../../docs/sources/claude_code/04_state.md) |
| 다음에 찾기 쉽게 | 이름 붙이기: `-n`, `/rename`. 기본 이름은 재개 손잡이가 아니다 | [S10](../../docs/sources/claude_code/04_state.md), [K1](../../docs/sources/claude_code/07_commands_cli.md) |
| 원래 세션을 지키며 다른 접근 시험 | 분기: `--continue`나 `--resume`에 `--fork-session`을 붙이거나 `/branch`. 새 세션 ID로 대화를 복사하고 원본은 그대로 | [S11](../../docs/sources/claude_code/04_state.md), [K1](../../docs/sources/claude_code/07_commands_cli.md) |
| 관련 없는 일로 넘어갈 때 | `/clear`는 빈 맥락으로 새로 시작하고 비용이 들지 않는다 | [S6](../../docs/sources/claude_code/04_state.md), [S7](../../docs/sources/claude_code/04_state.md) |

- 재개해도 처음 실행 때의 플래그가 전부 돌아오지는 않는다 ([S9](../../docs/sources/claude_code/04_state.md)).
- `claude -p`로 만든 세션은 `--continue` 목록에 없다 ([S8](../../docs/sources/claude_code/04_state.md)). 실험 5의 `--continue`는 대화형으로 연 세션을 가리킨다.
- 분기는 대화를 복사할 뿐 작업 폴더의 파일을 복사하지 않는다 ([S11](../../docs/sources/claude_code/04_state.md)). 파일은 git이 지킨다.

## 6. 압축 뒤에 남는 것

맥락 창이 차면 Claude Code가 대화를 요약한다. 요약은 요청과 핵심 코드 조각을 남기지만, 대화 초반의 자세한 지시는 잃을 수 있다 ([S5](../../docs/sources/claude_code/04_state.md)).

| 항목 | 압축 뒤 | 근거 |
|---|---|---|
| 루트 CLAUDE.md | 디스크에서 다시 읽어 다시 주입한다 | [S4](../../docs/sources/claude_code/04_state.md), [I9](../../docs/sources/claude_code/01_instructions.md) |
| 하위 폴더 CLAUDE.md, `paths` 규칙 | 메시지 기록에 실렸던 것이라 요약되어 사라진다. 그 파일을 다시 읽거나 고칠 때 다시 실린다 | [S4](../../docs/sources/claude_code/04_state.md) |
| 대화로만 준 지시 | 사라질 수 있다. CLAUDE.md에 적어야 남는다 | [I9](../../docs/sources/claude_code/01_instructions.md) |
| Skill 본문 | 다시 주입되지만 한도가 있다 | [S4](../../docs/sources/claude_code/04_state.md) |

- `/compact <초점>`처럼 초점을 주면 요약이 사람이 고른 것을 남긴다 ([S6](../../docs/sources/claude_code/04_state.md)).
- `/compact`는 요약할 대화를 읽으므로 큰 맥락에서는 그 자체가 큰 요청이다 ([S7](../../docs/sources/claude_code/04_state.md)). 그래서 수업에서 돌리지 않는다.
- 결론: 지켜야 할 약속은 대화가 아니라 파일(CLAUDE.md, `progress.md`)에 둔다.

## 7. auto memory: 저절로 쌓이는 기록

- 로컬 세션에서 기본으로 켜져 있다 ([S17](../../docs/sources/claude_code/04_state.md)).
- 매 대화를 시작할 때 `MEMORY.md`의 앞 200줄 또는 앞 25KB 중 먼저 오는 쪽만 싣는다. 주제 파일은 시작 때 싣지 않는다 ([S17](../../docs/sources/claude_code/04_state.md)).
- 이 기계 안에만 있다 ([S17](../../docs/sources/claude_code/04_state.md)). 위치는 `~/.claude/projects/<project>/memory/`로 저장소 밖이다. 같은 저장소의 worktree는 한 디렉터리를 나눠 쓴다. 팀과 공유되지 않는다.
- `/memory`로 본다 ([I7](../../docs/sources/claude_code/01_instructions.md), [K1](../../docs/sources/claude_code/07_commands_cli.md)). 실험 3 뒤에 조교 세션이 아니라 터미널 2(실험 대상 세션)에서 열어 실험 세션이 무언가 썼는지 확인한다.
- 이어받을 계약은 저장소 파일에 둔다. 기억에 맡기면 다른 기계에서 사라진다.

## 8. 시작할 때 읽기를 모델에 맡기지 않는 길: SessionStart hook

실험 폴더의 CLAUDE.md에는 "시작할 때" 단계가 있다. 기록을 읽고, `git log`를 보고, 검사를 돌리라는 문장이다. 이것은 모델이 따르기를 바라는 지침이다 ([I8](../../docs/sources/claude_code/01_instructions.md)).

SessionStart hook은 세션이 시작될 때 돌고, 그 stdout을 Claude의 맥락에 더한다 ([C20](../../docs/sources/claude_code/03_control.md)). matcher로 시작 원인(`startup`, `resume`, `clear`, `compact`)을 가를 수 있어서, 압축 뒤에도 같은 맥락을 다시 넣을 수 있다 ([C20](../../docs/sources/claude_code/03_control.md)). 모델의 순응이 아니라 결정적으로 같은 내용이 들어간다.

- 한계: 이 hook은 모델을 막지 못하고 맥락만 더한다 ([C15](../../docs/sources/claude_code/03_control.md), [C20](../../docs/sources/claude_code/03_control.md)).
- 이 Part에서는 개념만 다루고 실험은 하지 않는다. 직접 만들어 보는 것은 실습의 장치 시작 틀이다.

## 9. 완료를 선언하는 쪽과 인정하는 쪽을 나눈다

같은 회사의 다른 글(*Harness design for long-running application development*, Prithvi Rajasekaran, 2026-03-24)은 만든 쪽과 평가하는 쪽을 나눈다.

> "But tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work"

에이전트의 "완료"는 주장이다. 인정하려면 주장과 무관한 쪽이 다시 확인해야 한다. 이 수업은 그 확인을 네 가지로 본다.

| 확인 | 질문 | 실패하면 |
|---|---|---|
| 필수 검사가 있는가 | 요구사항마다 검사가 실제로 존재하는가 | 검사 없음 |
| 기준을 충족하는가 | **지금** 실행한 검사가 통과하는가 | 거짓 통과 주장 |
| 현재 산출물과 일치하는가 | 확인한 코드와 지금 코드가 같은가 | 오래된 증거 |
| 신뢰 기반이 그대로인가 | 검사 자체가 바뀌지 않았는가 | 신뢰 기반 변경 |

`tools/check_evidence.py`는 이 네 가지를 실험 폴더에서 확인하는 작은 완료 Gate다. 모델을 부르지 않는다. 종료 코드는 0 통과, 1 불통과, 2 확인 불가다 (`use_cc/CLAUDE.md` 2절). 여기서 "현재 산출물"은 코드다. 기록 파일만 바뀐 커밋은 코드의 리비전을 바꾸지 않으므로, `verified_at`(통과를 확인한 코드 커밋)을 "코드를 마지막으로 바꾼 커밋"과 비교한다.

## 10. Stop hook으로 완료 Gate를 강제한다

Stop hook은 메인 에이전트가 응답을 마쳤을 때 돈다. 막으면 Claude는 멈추지 않고 이어서 일한다 ([C16](../../docs/sources/claude_code/03_control.md)).

- 막는 방법은 두 가지다. exit 2로 끝내거나, JSON으로 block 결정을 낸다. exit 2일 때 stderr 문장이 "왜 계속해야 하는지"로 Claude에게 간다 ([C15](../../docs/sources/claude_code/03_control.md), [C16](../../docs/sources/claude_code/03_control.md)).
- 막는 것은 exit 2뿐이다. 다른 종료 코드는 막지 않는 오류다 ([C15](../../docs/sources/claude_code/03_control.md)).
- 영원히 막지 않도록: 입력의 `stop_hook_active`가 참이면 이미 hook 때문에 이어 가는 중이다. 이때는 다시 막지 않는다. 연속 8회 이어 가면 Claude Code가 다음 막기를 무시하고 턴을 끝낸다 ([C16](../../docs/sources/claude_code/03_control.md)).
- 사용자가 중단한 경우에는 돌지 않는다 ([C16](../../docs/sources/claude_code/03_control.md)). 그래서 이 관문은 "항상" 보장이 아니다.

### 왜 감싸개(`stop_gate.py`)가 필요한가

`check_evidence.py`는 0 통과, 1 불통과, 2 확인 불가를 낸다. 그대로 Stop hook에 걸면 이렇게 어긋난다.

| `check_evidence.py` | 뜻 | Stop hook이 받으면 |
|---|---|---|
| 0 | 통과 | 막지 않는다 (맞음) |
| 1 | **불통과** | 막지 않는 오류라 **그냥 끝난다** (틀림) |
| 2 | 확인 불가 | **막아 버린다** (틀림) |

`use_cc/part3/stop_gate.py`가 코드를 바꿔 준다: 불통과(1)는 2로 바꿔 막고, 통과(0)와 확인 불가(2)는 0으로 막지 않는다(확인 불가는 stderr에 알림만 남긴다). 입력의 `stop_hook_active`가 참이면 바로 0으로 끝낸다. 검사할 폴더는 입력의 `cwd`, 없으면 환경 변수 `CLAUDE_PROJECT_DIR`, 그것도 없으면 현재 폴더다. 막을 때는 stderr에 첫 줄과 불통과 이유를 최대 5줄 쓴다. 이 어긋남을 겪어야 "막는 것은 exit 2뿐"이 몸에 붙는다.

### 대조: `/goal`

`/goal`은 "매 턴이 끝나면 모델이 조건이 충족됐는지 판정하는" 세션 한정 Stop hook이다 ([X10](../../docs/sources/claude_code/05_execution.md), [C16](../../docs/sources/claude_code/03_control.md)).

| | `stop_gate.py` | `/goal` |
|---|---|---|
| 판정하는 것 | 코드. 검사를 다시 돌린다 | 작은 새 모델 |
| 보는 것 | 파일과 git 상태 | 대화에 드러난 것만. 명령을 돌리거나 파일을 읽지 않는다 |

같은 문서가 둘을 구분한다. 다시 돌린 검사로 인정하려면 코드 쪽이고, `/goal`은 증거를 대화에 보여 주는 조건일 때 쓴다 ([X10](../../docs/sources/claude_code/05_execution.md)).

## 11. 대조군: autonomous-coding (5분 이내)

동반 예제를 읽으면, 세 파일 중 무엇이 코드로 강제되고 무엇이 부탁인지가 갈린다. 미션에는 쓰지 않고 읽기만 한다.

| 장치 | 근거 | 강제인가 부탁인가 |
|---|---|---|
| 반복마다 새 문맥(새 클라이언트) | `agent.py:158-159` | 코드 |
| 첫 반복은 초기화 프롬프트, 이후는 코딩 프롬프트. `feature_list.json`이 있으면 이어 가는 것으로 본다 | `agent.py:126`, `:162-166` | 코드 |
| "passes만 바꿔라. 기능을 지우거나 고치는 것은 CATASTROPHIC" | `prompts/initializer_prompt.md:53-57`, `prompts/coding_prompt.md:108` | **부탁(프롬프트)**. 이 파일의 편집을 막는 장치는 없다. 등록된 hook은 Bash 허용 목록 하나다 (`client.py:113-117`) |
| 새 작업 전에 통과한 기능 1~2개를 다시 검사 | `prompts/coding_prompt.md:46-59` | 부탁(프롬프트) |
| 통과 수 집계 | `progress.py:32` | 코드. 단 **적힌 값을 그대로 센다**. 다시 검사하지 않는다 |
| 언제 멈추나 | `agent.py:150-153` | 코드. `max_iterations`에서만 멈춘다. 모든 기능이 통과해도 하네스는 멈추지 않는다 |

정리: 이 예제에서 Evidence는 에이전트가 스스로 쓰는 표시이고, 하네스는 그것을 세기만 한다. 우리 실험 폴더는 거기에 `check_evidence.py`로 다시 돌린 검사와 Stop hook을 더해, 완료 판정을 부탁에서 코드로 옮긴 것이다.

## 12. 오늘의 실험 폴더: 회의실 예약 서비스

`setup_sandbox.py`는 저장소 밖에 작은 예약 서비스와 이전 두 세션이 남긴 기록을 만든다.

| 커밋 | 내용 |
|---|---|
| `2a12049` | 초기 설정: 작업 규칙(`CLAUDE.md`), 요구사항 R1~R7(`feature_list.json`), 검사(`test_reservation.py`) |
| `8d702a4` | R1·R2·R7 코드: 사용자마다 파일 하나에 저장 |
| `eded468` | 기록: R1·R2·R7 통과 (`verified_at` = `8d702a4`) |
| `0f09a2a` | R3 코드: `list`에 `include_others` 옵션 추가 |
| `1b53d8c` | 기록: R3 완료 (`verified_at` = `0f09a2a`). 진행 기록의 근거는 "직접 확인함" |

R1~R7은 이 과정 이론 강의의 회의실 예약 사례에서 왔다. R3는 "독립된 사용자 B가 조회하면 A가 등록한 같은 예약이 표시된다"이다. 이 폴더의 하네스는 위 예제를 작게 줄인 것이다.

- Plan: `feature_list.json`(R1~R7, `passes`, `verified_at`)
- Checkpoint: `progress.md`, git 커밋
- Evidence: `passes`와 `verified_at`, 그리고 `check_evidence.py`가 지금 다시 돌린 검사
- 실행 제어: `.claude/settings.json`이 검사·git 조회 명령을 허용하고, PreToolUse hook이 `test_reservation.py` 편집을 막는다. exit 2로 막는다 ([C15](../../docs/sources/claude_code/03_control.md))

## 13. 실패 → 책임 → 장치 → 확인

| 실패 | 책임 | Claude Code 장치 | 동작 확인 |
|---|---|---|---|
| 되감았는데 파일 하나가 안 돌아왔다 | 상태 | 큰 변경 전 git 커밋. checkpoint의 한계 ([S15](../../docs/sources/claude_code/04_state.md), [I18](../../docs/sources/claude_code/01_instructions.md)) | 실험 4의 `git status` |
| 이전 세션이 "완료"라고 남겼는데 거짓이다 | 검증 | 다시 돌리는 검사(`tools/check_evidence.py`)와 Stop hook 관문 ([C16](../../docs/sources/claude_code/03_control.md)) | `check_evidence.py` 종료 코드, 실험 6 |
| 긴 세션 중 초기 지시를 잊었다 | 상태·지침 | 지시를 CLAUDE.md·`progress.md`로 옮긴다 ([S4](../../docs/sources/claude_code/04_state.md), [S5](../../docs/sources/claude_code/04_state.md), [I9](../../docs/sources/claude_code/01_instructions.md)) | 설명만. `/compact`는 큰 요청이라 수업에서 돌리지 않는다 ([S7](../../docs/sources/claude_code/04_state.md)) |
| 어제 세션을 못 찾는다 | 상태 | 이름(`-n`, `/rename`)과 `--resume` ([S10](../../docs/sources/claude_code/04_state.md), [K1](../../docs/sources/claude_code/07_commands_cli.md), [S8](../../docs/sources/claude_code/04_state.md)) | `claude --resume` 목록 |
| Stop hook이 끝없이 막거나, 오류 코드로 막은 줄 알았다 | 실행 제어 | `stop_hook_active`와 8회 상한 ([C16](../../docs/sources/claude_code/03_control.md)), 막는 것은 exit 2뿐 ([C15](../../docs/sources/claude_code/03_control.md)) | 실험 6에서 이어진 차례 수 |
| hook이 막았는데 같은 차례의 Bash가 사실이 아닌 기록을 썼다 | 실행 제어 ≠ 기록 | 막는 hook은 막은 행동 하나만 막는다. 2.1.318에서 저자가 1회 관찰했다 (`use_cc/CLAUDE.md` 6절 저자 실측 표, 84행) | 실험 5의 `git log` |

## 14. 시연 (10분)

강사가 화면으로 보여 준다. 수강생은 손들어 예측만 한다.

1. **실험 폴더 만들기** (2분): `!uv run python setup_sandbox.py ~/day06-p3`, `!uv run python tools/check_evidence.py ~/day06-p3`. 이전 세션의 주장을 다시 확인하면 어떤 판정이 나오는지 본다. §12의 커밋 다섯 개를 `git log --oneline`으로 대조한다.
2. **두 가지 checkpoint** (3분): 이 수업의 Checkpoint(`progress.md`와 커밋)를 열어 보고, 같은 터미널에서 `/rewind` 메뉴를 열어 Claude Code의 checkpoint 목록과 복원 선택지 넷을 보여 준다 ([S14](../../docs/sources/claude_code/04_state.md)). 되돌릴 지점은 고르지 않고 닫는다.
3. **실험 6, Stop hook 완료 관문** (5분, [유료]): 실험 폴더 사본에 `.claude/settings.json`으로 Stop hook 하나를 건다. 명령은 `use_cc/part3/stop_gate.py`의 절대 경로다 ([C18](../../docs/sources/claude_code/03_control.md)). 수강생은 "Claude가 끝이라고 할 때 몇 번 더 일하게 될까"를 손들어 예측한다. 완료 Gate가 불통과이면 exit 2로 한 번 더 일하게 하고, `stop_hook_active`가 참이면 놓아준다 ([C16](../../docs/sources/claude_code/03_control.md)). 확인은 `show_session.py`에서 이어진 차례와 hook의 stderr 문장이다. 막을 때마다 차례가 이어지므로 상한은 8회이고, 모델 호출이 늘어난다.

## 잘 다루기 습관

1. 큰 변경 전에는 git 커밋. `/rewind`는 버전 관리가 아니다 ([S15](../../docs/sources/claude_code/04_state.md)).
2. 대화로만 한 약속은 파일(CLAUDE.md, `progress.md`)로 옮긴다 ([I9](../../docs/sources/claude_code/01_instructions.md), [S4](../../docs/sources/claude_code/04_state.md)).
3. 관련 없는 일 사이에는 `/clear`, 돌아올 세션에는 이름을 붙인다 ([S6](../../docs/sources/claude_code/04_state.md), [S10](../../docs/sources/claude_code/04_state.md)).
4. 완료는 말이 아니라 다시 돌린 검사로 인정한다. 강제하려면 Stop hook이고, 막는 조건이 영원히 참이 되지 않게 `stop_hook_active`를 본다 ([C16](../../docs/sources/claude_code/03_control.md), [I17](../../docs/sources/claude_code/01_instructions.md)).

## 실험 4 뒤에 읽는다

미션 M3-5에서 세 변경을 예측하고 `/rewind`로 코드만 복원한 뒤에 읽는다. 공식 문서의 한계 목록이다 ([S15](../../docs/sources/claude_code/04_state.md)).

- **Bash만 바꾼 파일은 추적되지 않고 그대로 남는다.** 되돌리려면 git 같은 버전 관리를 쓴다.
- **Claude가 이미 편집 도구로 고친 파일은, 그 뒤 Bash가 바꾼 내용도 함께 되감긴다.** 같은 `sed -i`라도 어떤 파일에 했느냐로 갈린다. "Bash 변경은 전부 안 돌아온다"로 단순화하면 틀린다.
- 사용자가 Claude Code 밖에서 한 수동 변경과 다른 동시 세션의 편집은 보통 잡히지 않는다.
- symlink와 hard link된 파일은 되감지 않는다.
- 하위 에이전트의 편집은 일부 종류만 따로 다루고, 그 밖의 하위 에이전트에 대해서는 대화에서 Claude가 이미 편집한 파일만 복원한다.

그래서 큰 변경 전의 git 커밋이 상태의 진짜 안전판이다 ([I18](../../docs/sources/claude_code/01_instructions.md)도 같은 한계를 적는다). 저자는 2.1.318 대화형에서 이 실험을 1회 돌려 보았다(2026-11-06). 세 변경 모두 위 문서의 서술대로였다(S15의 서술과 같다). 코드만 복원(3 Restore code)은 모델을 부르지 않았고(`/rewind` 전후 세션 비용이 같았다), 세션 기록(jsonl)에도 표식을 남기지 않았다. 1회 관찰이다. 본인 화면에서는 실험 4의 `git status`와 `git diff`로 확인한다.

## 근거

Claude Code 사실의 출처다. 항목은 `Day06_new/docs/sources/claude_code/`의 대장에서 `## <번호>`로 찾는다.

- [S4](../../docs/sources/claude_code/04_state.md) compaction 뒤에 남는 것과 다시 읽히는 것 — https://code.claude.com/docs/en/context-window.md
- [S5](../../docs/sources/claude_code/04_state.md) auto-compaction — https://code.claude.com/docs/en/how-claude-code-works.md
- [S6](../../docs/sources/claude_code/04_state.md) `/compact` 지시문, `/clear` — https://code.claude.com/docs/en/costs.md
- [S7](../../docs/sources/claude_code/04_state.md) 컨텍스트와 비용(costs) — https://code.claude.com/docs/en/costs.md
- [S8](../../docs/sources/claude_code/04_state.md) `--continue`, `--resume` — https://code.claude.com/docs/en/sessions.md
- [S9](../../docs/sources/claude_code/04_state.md) 재개된 세션이 되살리는 것과 못 되살리는 것 — https://code.claude.com/docs/en/sessions.md
- [S10](../../docs/sources/claude_code/04_state.md) 세션 이름 붙이기 — https://code.claude.com/docs/en/sessions.md
- [S11](../../docs/sources/claude_code/04_state.md) 세션 분기(fork) — https://code.claude.com/docs/en/sessions.md
- [S13](../../docs/sources/claude_code/04_state.md) checkpoint가 추적하는 것 — https://code.claude.com/docs/en/checkpointing.md
- [S14](../../docs/sources/claude_code/04_state.md) 되감기: `/rewind`, `Esc Esc`와 복원 대상 — https://code.claude.com/docs/en/checkpointing.md
- [S15](../../docs/sources/claude_code/04_state.md) checkpoint의 문서화된 한계 — https://code.claude.com/docs/en/checkpointing.md
- [S16](../../docs/sources/claude_code/04_state.md) checkpoint 보존 기간 — https://code.claude.com/docs/en/checkpointing.md
- [S17](../../docs/sources/claude_code/04_state.md) auto memory — https://code.claude.com/docs/en/memory.md
- [I7](../../docs/sources/claude_code/01_instructions.md) `/init`, `/memory`, `/context all`, `/doctor` — https://code.claude.com/docs/en/memory.md
- [I8](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md는 맥락이지 강제가 아니다 — https://code.claude.com/docs/en/memory.md
- [I9](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md와 auto memory, compaction 뒤의 지침 — https://code.claude.com/docs/en/memory.md
- [I17](../../docs/sources/claude_code/01_instructions.md) 검증 기준을 지침으로 주기 — https://code.claude.com/docs/en/best-practices.md
- [I18](../../docs/sources/claude_code/01_instructions.md) 설계, 조기 교정 — https://code.claude.com/docs/en/best-practices.md
- [C15](../../docs/sources/claude_code/03_control.md) 종료 코드 2의 의미 — https://code.claude.com/docs/en/hooks.md
- [C16](../../docs/sources/claude_code/03_control.md) Stop hook은 완료 관문이 될 수 있다 — https://code.claude.com/docs/en/hooks.md
- [C18](../../docs/sources/claude_code/03_control.md) hook을 설정하는 위치와 /hooks 명령 — https://code.claude.com/docs/en/hooks.md
- [C20](../../docs/sources/claude_code/03_control.md) SessionStart hook: 시작 원인 matcher와 맥락 주입 — https://code.claude.com/docs/en/hooks.md
- [X10](../../docs/sources/claude_code/05_execution.md) /goal: 완료 조건과 판정 방식 — https://code.claude.com/docs/en/goal.md
- [K1](../../docs/sources/claude_code/07_commands_cli.md) 내장 명령 — https://code.claude.com/docs/en/commands.md
- [K3](../../docs/sources/claude_code/07_commands_cli.md) 키 조작 — https://code.claude.com/docs/en/interactive-mode.md

그 밖의 원문:

- Anthropic, *Effective harnesses for long-running agents* — https://www.anthropic.com/research/effective-harnesses-for-long-running-agents
- Anthropic, *Harness design for long-running application development* — https://www.anthropic.com/research/harness-design-long-running-apps
- anthropics/claude-quickstarts `autonomous-coding` — https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding (이 저장소 `vendor/autonomous-coding`, `vendor/SNAPSHOTS.md`)
