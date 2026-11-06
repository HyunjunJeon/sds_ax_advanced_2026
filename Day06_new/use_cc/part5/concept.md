# Part 5. 계획 구체화와 실행 구조 (개념 12분 + 시연 6분)

## 핵심 질문

> **계획을 얼마나 구체화하고, 어떤 실행 구조(혼자, 하위 에이전트, 병렬 세션)에 실행과 검토를 맡길 것인가?**

이 문서의 Claude Code 사실은 `Day06_new/docs/sources/claude_code/` 근거 대장에 항목이 있는 것만 적는다. 문장 뒤의 `X3` 같은 표시는 그 항목 번호이고, 누르면 대장 파일로 간다. Claude Code가 아닌 도구(superpowers, spec-kit, ramo-harness)의 사실은 `docs/sources/github.md`의 인용과 줄 번호를 따른다. 대장에 없는 것은 "확인 필요"로 적는다. 단계는 `mission.md`에 있다.

---

## 1. plan mode: 고치기 전에 조사하고 계획한다

plan mode에서 Claude는 파일을 읽고, 탐색용 셸 명령을 돌리고, 계획을 쓴다. 소스는 고치지 않는다 ([C7](../../docs/sources/claude_code/03_control.md)). 계획을 승인하기 전에는 편집이 막힌다. 예외는 bypass 권한을 쓸 수 있는 대화형 터미널 세션이다 ([C7](../../docs/sources/claude_code/03_control.md)). 들어가는 방법은 Shift+Tab을 누르거나, 프롬프트 앞에 `/plan`을 붙이는 것이다 ([C7](../../docs/sources/claude_code/03_control.md), [X14](../../docs/sources/claude_code/05_execution.md), [K1](../../docs/sources/claude_code/07_commands_cli.md)). 계획 중의 셸 명령은 분류기가 검토한다 ([C7](../../docs/sources/claude_code/03_control.md)).

"디스크에 닿기 전에 보고 싶은 변경"이 plan mode를 쓰는 때다 ([X14](../../docs/sources/claude_code/05_execution.md)). 계획 파일은 plan mode 중에 Write 도구가 `~/.claude/plans/<세 단어>.md`로 쓰고, 승인 화면에도 그 경로가 표시된다 (저자 확인 1회 (2026-11-06, 대화형, Claude Code 2.1.318)). 이 위치는 근거 대장에 항목이 없다. 그래서 승인한 계획은 내 저장소의 파일로 옮겨 둔다.

## 2. 하위 에이전트: 내장과 사용자 정의

| 구분 | 내용 | 근거 |
|---|---|---|
| 내장 | Explore(읽기 전용 탐색), Plan(plan mode 중 맥락 수집), General-purpose(탐색과 실행이 모두 필요한 복잡한 작업) | [X1](../../docs/sources/claude_code/05_execution.md) |
| 상속 | 내장 하위 에이전트는 부모 대화의 권한 규칙을 물려받는다. Explore와 Plan은 CLAUDE.md 없이 시작한다 | [X1](../../docs/sources/claude_code/05_execution.md) |
| 사용자 정의 | `.claude/agents/`의 파일. YAML frontmatter에서 `name`과 `description`만 필수이고 `tools`, `model`은 선택이다 | [X2](../../docs/sources/claude_code/05_execution.md) |
| description | Claude가 언제 이 하위 에이전트에게 맡길지를 적는다 | [X2](../../docs/sources/claude_code/05_execution.md) |
| tools | 생략하면 하위 에이전트가 쓸 수 있는 도구를 모두 물려받는다. 쉼표로 이은 문자열(`Read, Grep, Bash`) 또는 YAML 목록이다 | [X2](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md) |
| 모르는 필드 | 오류 없이 조용히 무시한다. `tools:`를 `tool:`로 쓰면 제한 없는 일꾼이 된다 | [X2](../../docs/sources/claude_code/05_execution.md) |

도구를 좁히는 방법은 `tools`에서 빼거나 설정에 deny 규칙을 두는 것이다. `tools`와 `disallowedTools`를 둘 다 적으면 `disallowedTools`가 우선한다 ([T7](../../docs/sources/claude_code/02_tools.md)). 하위 에이전트를 띄울 때 권한을 묻지는 않고, 하위 에이전트의 도구 호출을 실행 중에 권한 규칙으로 검사한다 ([T7](../../docs/sources/claude_code/02_tools.md)).

## 3. 하위 에이전트는 자기 맥락에서 일하고 요약을 돌려준다

하위 에이전트는 자기 맥락 창에서 일하고 요약만 돌려준다 ([X3](../../docs/sources/claude_code/05_execution.md)). 긴 탐색 결과가 내 대화를 채우지 않는 것이 장점이다 ([X3](../../docs/sources/claude_code/05_execution.md), [X14](../../docs/sources/claude_code/05_execution.md)). 반대로 내가 볼 수 있는 근거가 요약 한 문단으로 줄어든다. 독립이라는 말은 맥락에 대한 말이다. 권한은 부모에게서 물려받는다 ([X1](../../docs/sources/claude_code/05_execution.md)).

비용 쪽도 있다. 하위 에이전트의 요청은 메인 대화와 같은 사용량 한도에 잡히고 ([X4](../../docs/sources/claude_code/05_execution.md)), 상세한 결과를 돌려주는 하위 에이전트를 많이 돌리면 맥락과 토큰이 는다 ([X4](../../docs/sources/claude_code/05_execution.md)). 기본값으로 하위 에이전트는 메인 대화 아래 세 단계까지 다시 하위 에이전트를 띄울 수 있다 ([X4](../../docs/sources/claude_code/05_execution.md)). 문서에 토큰 배수는 없으므로 숫자는 적지 않는다.

## 4. 검토는 대화를 못 본 새 하위 에이전트에게

검토를 내 대화를 본 같은 세션에 맡기면 내 가정을 그대로 이어받는다. 공식 문서의 권고는 대화를 한 번도 못 본 새 하위 에이전트에게 diff를 검토시키는 것이다 ([I17](../../docs/sources/claude_code/01_instructions.md)). 한 가지 주의가 같은 문서에 있다. 문제를 찾으라고 지시받은 검토자는 늘 뭔가를 찾는다 ([I17](../../docs/sources/claude_code/01_instructions.md)). 그러니 "문제가 몇 개 나왔나"가 아니라 "검사를 돌렸는가, 근거가 있는가"를 본다. 검토자가 고쳐 버리지 않게 `tools`를 좁힌다 ([X2](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md)).

## 5. worktree: 병렬 세션의 파일을 나눈다

`--worktree` 또는 `-w`에 이름을 주면 격리된 worktree를 만들고 그 안에서 Claude를 시작한다. 다른 터미널에서 다른 이름으로 다시 실행하면 두 번째 격리 세션이 된다 ([X6](../../docs/sources/claude_code/05_execution.md), [K2](../../docs/sources/claude_code/07_commands_cli.md)). 기본 경로는 `.claude/worktrees/<name>/`이다 ([X6](../../docs/sources/claude_code/05_execution.md)). 저장소에 커밋이 하나 이상 있어야 한다 ([X6](../../docs/sources/claude_code/05_execution.md)).

| 공유한다 | 격리한다 |
|---|---|
| main checkout의 `.git` 디렉터리 ([X7](../../docs/sources/claude_code/05_execution.md)), 권한 승인(한 worktree에서 누른 "don't ask again"이 다른 worktree에도 적용) ([X7](../../docs/sources/claude_code/05_execution.md)) | 파일과 브랜치 ([X6](../../docs/sources/claude_code/05_execution.md)). 격리 세션에서 main checkout 경로를 향한 Edit, Write, NotebookEdit는 막힌다 ([X7](../../docs/sources/claude_code/05_execution.md)) |

격리 검사는 셸 명령이 쓰는 파일을 추적하지 않는다. `cp`나 셸 리다이렉트로 main checkout에 쓰는 것은 막지 못한다 ([X7](../../docs/sources/claude_code/05_execution.md)). "격리됐으니 안전하다"는 말은 파일 편집에만 맞다.

## 6. 병렬 방식은 토큰을 곱한다

Claude Code에는 여러 일을 한꺼번에 하는 방법이 다섯 가지 있고, 모든 방식에서 일꾼은 Claude 세션이다 ([X5](../../docs/sources/claude_code/05_execution.md)). 세션이나 하위 에이전트를 여러 개 동시에 돌리면 토큰 사용량이 곱해진다 ([X5](../../docs/sources/claude_code/05_execution.md)). 아래는 이름과 비용 문장만 읽고 넘어간다. 직접 돌리지 않는다.

- 에이전트 팀: 실험 기능이고 기본 꺼짐이다. 한 세션이 lead가 되고, 팀원은 각자 맥락 창에서 일하며 서로 직접 소통한다. 단일 세션보다 토큰을 훨씬 더 쓰고, 팀원마다 토큰이 선형으로 는다 ([X5](../../docs/sources/claude_code/05_execution.md), [X8](../../docs/sources/claude_code/05_execution.md)).
- 동적 워크플로: 많은 하위 에이전트를 스크립트가 조율한다. 에이전트가 25개를 넘거나 예상 토큰이 150만을 넘으면 큰 실행 경고가 뜬다. 상한이 아니라 경고 기준이다 ([X9](../../docs/sources/claude_code/05_execution.md)).
- `/batch`: 큰 변경 하나를 worktree로 격리한 하위 에이전트 5~30개로 나눈다 ([X15](../../docs/sources/claude_code/05_execution.md)).

## 7. headless `-p`: 출력, 비용, 권한, 신뢰

- 출력 형식은 text(기본), json, stream-json이다 ([X11](../../docs/sources/claude_code/05_execution.md)). json 출력에는 `total_cost_usd`와 모델별 비용이 들어 있다 ([X11](../../docs/sources/claude_code/05_execution.md)). 이전 대화는 `--continue`, 또는 세션 ID와 `--resume`으로 이어 간다 ([X11](../../docs/sources/claude_code/05_execution.md)).
- 권한: v2.1.302 이상의 `-p`는 권한 모드를 정하지 않으면 Manual로 시작하고, 승인이 필요한 호출은 거부된다. 쓸 도구는 `--allowedTools`로, 기준 모드는 `--permission-mode`로 정한다 ([X12](../../docs/sources/claude_code/05_execution.md)).
- 신뢰: `-p` 세션에는 폴더 신뢰 대화상자가 없다. `--bare` 없이 실행하면 처음 보는 폴더에서도 그 프로젝트의 `.claude/settings.json`에 있는 hook이 돌고 `.mcp.json`의 서버가 연결된다 ([X13](../../docs/sources/claude_code/05_execution.md)). 낯선 폴더는 설정부터 읽는다.

## 8. /goal: 끝났다는 판정을 다른 모델에게

`/goal`은 매 턴이 끝날 때 모델이 조건이 충족됐는지 확인하고, 아니면 Claude가 다음 턴을 시작하게 한다. 완료 판정은 일하는 모델이 아니라 새 모델이 한다 ([X10](../../docs/sources/claude_code/05_execution.md)). 평가자는 명령을 실행하거나 파일을 읽지 않고 대화에 드러난 것만 본다. 그래서 조건은 대화에서 보이는 증거로 써야 한다. 반복 상한(예: "20턴 뒤 중단")도 조건에 넣는다 ([X10](../../docs/sources/claude_code/05_execution.md)). 코드로 확인하는 검사는 Stop hook의 일이고, `/goal`은 모델 판정이라는 점이 다르다 ([X10](../../docs/sources/claude_code/05_execution.md), [I17](../../docs/sources/claude_code/01_instructions.md)).

## 9. 비교 축: 누가 다음 할 일을 정하고, 중간 결과는 어디에 사는가

하위 에이전트, Skill, 에이전트 팀에서는 Claude가 매 턴 다음에 무엇을 맡길지 정하고 모든 결과가 맥락 창에 들어간다. 동적 워크플로에서는 스크립트가 반복과 분기와 중간 결과를 쥐고 Claude의 맥락에는 최종 답만 온다 ([X16](../../docs/sources/claude_code/05_execution.md), [X9](../../docs/sources/claude_code/05_execution.md)). 이 비교는 workflows 쪽 문서가 자기를 소개한 것이므로 비용 문장([X4](../../docs/sources/claude_code/05_execution.md), [X8](../../docs/sources/claude_code/05_execution.md), [X9](../../docs/sources/claude_code/05_execution.md))과 같이 읽는다.

## 10. 다른 도구는 계획을 어디에 남기나 (대조군)

| 도구 | 흐름 | 계획이 남는 곳 |
|---|---|---|
| Claude Code plan mode | 편집 없이 조사하고 계획을 쓴다. 승인 전에는 편집이 막힌다. Shift+Tab 또는 `/plan` | `~/.claude/plans/<세 단어>.md` (저자 확인 1회 (2026-11-06, 대화형, Claude Code 2.1.318)) |
| superpowers | brainstorming → using-git-worktrees → writing-plans → subagent-driven-development 또는 executing-plans → test-driven-development → requesting-code-review → finishing-a-development-branch (`README.md:310-322`) | `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` (`writing-plans/SKILL.md:16`) |
| spec-kit | `/speckit-constitution` → `-specify` → `-plan` → `-tasks` → `-implement` → `-converge`, "Repeat implement and converge until convergence reports `Converged`." (`README.md:113-121`) | 기능 폴더의 `plan.md`, `tasks.md` 등 (`templates/plan-template.md:50-56`) |

플레이북은 plan mode의 계획을 `plan.md`로 커밋하라고 한다: "the approved version is committed as plan.md for later stages to check against." (`docs/sources/web.md:33`)

## 11. 실행 구조: 누가, 어떤 단위로 실행하나 (대조군)

| 구조 | 근거 | 대가 |
|---|---|---|
| 한 세션에서 작업을 차례로(인라인) | superpowers executing-plans: "Execute the plan yourself, task by task, in this session: no implementer subagent per task, no reviewer per task. One fresh-context review of the whole branch at the end." (`skills/executing-plans/SKILL.md:8-10`) | 싸다. 문맥이 쌓인다 |
| 작업마다 새 하위 에이전트 + 작업 리뷰 | superpowers subagent-driven-development: "dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end." (`skills/subagent-driven-development/SKILL.md:8`) | 독립적이고 깨끗하다. 비싸다: "pays for a fresh implementer and a fresh reviewer on every task, each re-reading the codebase from zero." (`executing-plans/SKILL.md:12-14`) |
| 단계마다 사람이 넘겨 준다(배턴) | woowabros/ramo-harness: "각 단계는 사람의 확인(배턴)을 거쳐 다음으로 넘어감. 자동 연쇄가 아니고" (`README.md:30-31`) | 사람이 매 단계 본다. 느리지만 도메인 판단을 놓치지 않는다 |
| 정해진 게이트에서만 멈춘다 | ADLC-harness: "의도·설계·계획·출시(푸시·PR)에서만 멈추고 승인을 받는다. 그 사이의 구현·검증·리뷰는 묻지 않고 이어 간다." (`README.md:78`) | 사람의 시간을 게이트에 모은다 |

정답은 없다. 작업의 위험과 크기, 쓸 수 있는 시간과 비용으로 고른다. ramo-harness의 검증 단계는 실행 구조와 검증이 맞물리는 예다: "`/ramo:verify` 가 검증 대상을 `git diff --name-only` 로 확정함. 자기보고를 믿지 않음" (`README.md:123`). 줄 번호는 `../../docs/sources/github.md`에 고정한 커밋 기준이다.

## 12. 실패 → 책임 → 장치 → 확인

| 실패 | 책임 | Claude Code 장치 | 동작 확인 |
|---|---|---|---|
| 계획 승인 전에 파일이 바뀌었다 | 실행 제어 | plan mode ([C7](../../docs/sources/claude_code/03_control.md), [X14](../../docs/sources/claude_code/05_execution.md)) | 실험 7의 `git status` |
| 계획이 세션 밖에 남지 않는다 | 상태 | 승인한 계획을 저장소 파일로 옮긴다 (`docs/sources/web.md:33`). 세션은 계획을 `~/.claude/plans/<세 단어>.md`에 쓴다(저자 확인 1회 (2026-11-06, 대화형, Claude Code 2.1.318)) | `plans/` 폴더 |
| 검토자가 내 대화의 편향을 그대로 이어받았다 | 검증 | 대화를 못 본 별도 맥락 하위 에이전트 ([X3](../../docs/sources/claude_code/05_execution.md), [I17](../../docs/sources/claude_code/01_instructions.md)) | 실험 8의 검토 요약 |
| 검토자가 고쳐 버렸다 | 도구, 실행 제어 | `tools`를 좁힌다 ([X2](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md)) | 확장된 `show_session.py`의 하위 에이전트 줄과 `git status` |
| `tools:`를 오타 내 제한 없는 일꾼이 됐다 | 실행 제어 | 틀린 필드명은 조용히 무시된다 ([X2](../../docs/sources/claude_code/05_execution.md)) | `harness_inventory.py`의 agents 개수와 파일 읽기 |
| 병렬 세션 두 개가 같은 파일을 덮어썼다 | 상태 | worktree ([X6](../../docs/sources/claude_code/05_execution.md), [X7](../../docs/sources/claude_code/05_execution.md)) | 실험 9(시연) |
| 에이전트를 늘리면 빨라질 줄 알았다 | 실행 제어(예산) | 토큰이 곱해진다 ([X4](../../docs/sources/claude_code/05_execution.md), [X5](../../docs/sources/claude_code/05_execution.md), [X8](../../docs/sources/claude_code/05_execution.md), [X9](../../docs/sources/claude_code/05_execution.md)) | 비용 표 |
| "끝났다"를 다른 모델이 판정하게 했는데 근거가 대화에 없었다 | 검증 | `/goal` 평가자는 대화만 본다 ([X10](../../docs/sources/claude_code/05_execution.md)). 스크립트 검사는 Stop hook ([C16](../../docs/sources/claude_code/03_control.md)) | 실험 10(시연) |

## 시연 (6분, 강사만)

강사 화면으로 두 가지를 보여 준다. 수강생은 직접 돌리지 않는다.

1. 실험 9: worktree 두 세션. `-w`로 이름을 달리해 두 세션을 띄우고, 같은 파일을 각자 고쳐도 덮어쓰지 않는 것, 그리고 `.git`은 공유되는 것을 본다 ([X6](../../docs/sources/claude_code/05_execution.md), [X7](../../docs/sources/claude_code/05_execution.md)).
2. 실험 10: `claude -p --output-format json`의 `total_cost_usd` 칸을 읽고, `/goal`의 조건에 턴 상한을 넣는 모습을 본다 ([X11](../../docs/sources/claude_code/05_execution.md), [X10](../../docs/sources/claude_code/05_execution.md)). 모델 호출이 일어나므로 직전에 규모를 말한다.

에이전트 팀, 동적 워크플로, `/batch`는 시연하지 않고 6절의 비용 문장만 읽는다.

## 잘 다루기 습관

1. 디스크에 닿기 전에 봐야 할 변경은 plan mode로 시작하고, 승인한 계획은 저장소 파일로 옮긴다([C7](../../docs/sources/claude_code/03_control.md), [X14](../../docs/sources/claude_code/05_execution.md)).
2. 검토는 대화를 못 본 하위 에이전트에게 맡기고 도구를 좁힌다([X3](../../docs/sources/claude_code/05_execution.md), [X2](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md), [I17](../../docs/sources/claude_code/01_instructions.md)).
3. 병렬은 독립성과 비용을 같이 본다. 일꾼을 늘리면 토큰이 곱해진다([X5](../../docs/sources/claude_code/05_execution.md), [X4](../../docs/sources/claude_code/05_execution.md)).
4. `-p`에는 신뢰 대화상자가 없다. 낯선 폴더에서는 먼저 설정을 읽는다([X13](../../docs/sources/claude_code/05_execution.md)).

## 근거

Claude Code (`docs/sources/claude_code/`, 확인일 2026-11-06, 2.1.318):

- [C7](../../docs/sources/claude_code/03_control.md) plan 모드 · [C16](../../docs/sources/claude_code/03_control.md) Stop hook 완료 관문
- [K1](../../docs/sources/claude_code/07_commands_cli.md) 내장 명령(`/plan`) · [K2](../../docs/sources/claude_code/07_commands_cli.md) CLI 플래그(`--worktree`)
- [T7](../../docs/sources/claude_code/02_tools.md) 하위 에이전트가 쓸 수 있는 도구 · [I17](../../docs/sources/claude_code/01_instructions.md) 검증 기준을 지침으로 주기
- [X1](../../docs/sources/claude_code/05_execution.md) 내장 하위 에이전트 · [X2](../../docs/sources/claude_code/05_execution.md) 사용자 정의 하위 에이전트 · [X3](../../docs/sources/claude_code/05_execution.md) 별도 컨텍스트 · [X4](../../docs/sources/claude_code/05_execution.md) 비용과 중첩
- [X5](../../docs/sources/claude_code/05_execution.md) 병렬 다섯 방식 · [X6](../../docs/sources/claude_code/05_execution.md) worktree · [X7](../../docs/sources/claude_code/05_execution.md) 공유와 격리 · [X8](../../docs/sources/claude_code/05_execution.md) 에이전트 팀 · [X9](../../docs/sources/claude_code/05_execution.md) 동적 워크플로
- [X10](../../docs/sources/claude_code/05_execution.md) /goal · [X11](../../docs/sources/claude_code/05_execution.md) headless 출력 · [X12](../../docs/sources/claude_code/05_execution.md) headless 권한 · [X13](../../docs/sources/claude_code/05_execution.md) 신뢰와 `--bare` · [X14](../../docs/sources/claude_code/05_execution.md) 계획 모드, 조사 위임 · [X15](../../docs/sources/claude_code/05_execution.md) /batch · [X16](../../docs/sources/claude_code/05_execution.md) 구조 비교

Claude Code 밖의 도구 (`docs/sources/github.md`, 줄 번호는 대장에 고정한 커밋 기준):

- obra/superpowers: `skills/executing-plans/SKILL.md:8-10, 12-14`, `skills/subagent-driven-development/SKILL.md:8` (`github.md:89-91`)
- github/spec-kit: `README.md:113-121` (`github.md:119-125`)
- woowabros/ramo-harness: `README.md:30-31, 123` (`github.md:425, 427`)
- jh941213/ADLC-harness: `README.md:78` (`github.md:355`)
- 플레이북 plan.md 인용: `docs/sources/web.md:33`
