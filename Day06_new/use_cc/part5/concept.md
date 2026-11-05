# Part 5. 계획 구체화와 실행 구조 — 개념 정리

> **핵심 질문: 좋은 계획에는 무엇이 들어가고, 그 계획을 누가 어떤 단위로 실행하는가?**

근거는 `Day06_new/docs/SOURCES.md`와 그 대장(`docs/sources/github.md` 1~3절, `web.md` 1절·6(b))에 있다. 저장소 줄 번호는 대장에 고정한 커밋 기준이다.

---

## 1. 계획이란 무엇을 적는 문서인가

obra/superpowers의 계획 작성 Skill(`skills/writing-plans/SKILL.md`, 커밋 `22f0b463`)은 계획을 이렇게 정의한다.

> "A plan is the set of decisions the implementer cannot make alone. A plan longer than the code it describes has written the code instead." (`:157-158`)

계획은 코드를 미리 쓰는 문서가 아니다. **구현하는 쪽(사람이든 에이전트든)이 혼자 정할 수 없는 결정**을 적는다.

> "What they cannot know is what you decided: which files, which names and signatures, which values from the spec, which tests prove each task." (`:10`)

## 2. 계획 전에 조사한다: Research → Plan → Implement

HumanLayer 저장소의 글 *Advanced Context Engineering for Coding Agents*(`ace-fca.md`, 커밋 `da16ab73`)는 일을 세 단계로 나눈다.

| 단계 | 원문 (`ace-fca.md`) |
|---|---|
| Research | "Understand the codebase, the files relevant to the issue, and how information flows, and perhaps potential causes of a problem." (`:228`) |
| Plan | "Outline the exact steps we'll take to fix the issue, and the files we'll need to edit and how, being super precise about the testing / verification steps in each phase." (`:237`) |
| Implement | "Step through the plan, phase by phase. For complex work, I'll often compact the current status back into the original plan file after each implementation phase is verified." (`:244`) |

이 글은 문맥 사용량을 40~60%로 유지하는 것을 목표로 든다(`:218`). 그리고 조사가 틀렸던 실제 사례를 숨기지 않는다.

> "Claude decided the bug was invalid and the codebase was correct." / "I threw that research out and kicked off a new one, with more steering." (`:266-267`)

> "You have to engage with your task when you're doing this or it WILL NOT WORK." (`:304`)

조사 한 줄이 틀리면 그 뒤 계획과 구현이 모두 틀린다(`:323-324`). 그래서 **사람이 가장 많이 보는 곳은 조사와 계획**이다.

참고: 이 글이 링크한 프롬프트 파일 세 개는 2026-10-22에 원 저장소에서 삭제되었다(`docs/sources/github.md` 3절).

## 3. 좋은 계획의 칸

| 칸 | 근거 | 왜 필요한가 |
|---|---|---|
| 조사 결과(지금 상태) | RPI의 Research | 지금 무엇이 통과·실패하는지 모르고 세운 계획은 거짓 Checkpoint를 그대로 믿는다(Part 3) |
| 작업 단위 | "A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate." (`writing-plans/SKILL.md:36-37`) | 작업마다 자기 검사가 있어야 끝났는지 안다 |
| 정확한 파일 | "Create: `exact/path/to/file.py`" / "Modify: `exact/path/to/existing.py:123-145`" (`:97-100`) | 바꿀 범위가 곧 실행 제어의 경계다 |
| 먼저 실패하는 검사 | "Step 1: Write the failing test" … "Step 5: Commit" (`:108-132`) | 실패를 먼저 봐야 통과가 의미 있다 |
| 통과의 뜻 | "A verification step: the command to run and the output that means it passed." (`:152-153`) | "됐다"를 명령과 출력으로 정한다 |
| 멈출 조건 | ADLC-harness: "같은 원인으로 세 번 실패하면 멈추고 보고한다." (`README.md:79`) | 무한 반복 대신 사람에게 넘긴다 |
| 사람 확인 지점 | 플레이북: "Nothing is implemented without an accepted plan." / superpowers brainstorming: "Nothing gets built until your human partner approves the design doc" (`skills/brainstorming/SKILL.md:270`) | 승인 없이 넘어가면 안 되는 곳을 정한다 |

주의할 점 두 가지.

- superpowers README(`README.md:314`)에는 "2-5 minutes each"라는 작업 크기가 남아 있지만, 지금의 `writing-plans/SKILL.md`에는 시간 기준이 없다. 원래는 작업이 아니라 **스텝**의 기준이었고 v6.4.2에서 빠졌다(`docs/sources/github.md` 1절). 시간이 아니라 **자기 검사 주기**로 자른다.
- github/spec-kit의 작업 템플릿은 테스트를 **선택**으로 둔다: "Tests are OPTIONAL - only include them if explicitly requested in the feature specification." (`templates/tasks-template.md:12`, 커밋 `ec9a6f3b`). 도구마다 기본값이 다르다. 검증 칸을 넣을지는 내가 정한다.

## 4. 같은 일, 세 가지 계획 도구

| 도구 | 흐름 | 계획이 남는 곳 |
|---|---|---|
| Claude Code plan mode | 편집 없이 조사하고 계획을 쓴다. 승인 전에는 편집이 막힌다(bypass 권한이 있는 대화형 세션은 예외). Shift+Tab 또는 `/plan` | `~/.claude/plans/` (공식 문서) |
| superpowers | brainstorming → using-git-worktrees → writing-plans → subagent-driven-development 또는 executing-plans → test-driven-development → requesting-code-review → finishing-a-development-branch (`README.md:310-322`) | `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` (`writing-plans/SKILL.md:16`) |
| spec-kit | `/speckit-constitution` → `-specify` → `-plan` → `-tasks` → `-implement` → `-converge`, "Repeat implement and converge until convergence reports `Converged`." (`README.md:113-121`) | 기능 폴더의 `plan.md`, `tasks.md` 등 (`templates/plan-template.md:50-56`) |

플레이북은 plan mode의 계획을 `plan.md`로 커밋하라고 한다: "Commit the approved plan as plan.md." 계획이 `~/.claude/plans/`에만 있으면 다음 세션과 다른 사람이 읽기 어렵다.

## 5. 실행 구조: 누가, 어떤 단위로 실행하나

| 구조 | 근거 | 대가 |
|---|---|---|
| 한 세션에서 작업을 차례로(인라인) | superpowers executing-plans: "Execute the plan yourself, task by task, in this session: no implementer subagent per task, no reviewer per task. One fresh-context review of the whole branch at the end." (`skills/executing-plans/SKILL.md:8-10`) | 싸다. 문맥이 쌓인다 |
| 작업마다 새 하위 에이전트 + 작업 리뷰 | superpowers subagent-driven-development: "dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end." (`skills/subagent-driven-development/SKILL.md:8`) | 독립적이고 깨끗하다. 비싸다: "pays for a fresh implementer and a fresh reviewer on every task, each re-reading the codebase from zero." (`executing-plans/SKILL.md:12-14`) |
| 단계마다 사람이 넘겨 준다(배턴) | woowabros/ramo-harness: "각 단계는 사람의 확인(배턴)을 거쳐 다음으로 넘어감. 자동 연쇄가 아니고" (`README.md:30-31`) | 사람이 매 단계 본다. 느리지만 도메인 판단을 놓치지 않는다 |
| 정해진 게이트에서만 멈춘다 | ADLC-harness: "의도·설계·계획·출시(푸시·PR)에서만 멈추고 승인을 받는다. 그 사이의 구현·검증·리뷰는 묻지 않고 이어 간다." (`README.md:78`) | 사람의 시간을 게이트에 모은다 |

정답은 없다. **작업의 위험과 크기, 내가 쓸 수 있는 시간과 비용**으로 고른다. 오늘 실습에서는 내 작업에 맞는 구조 하나를 고르고 이유를 적는다.

ramo-harness의 검증 단계는 실행 구조와 검증이 어떻게 맞물리는지 보여 준다.

> "`/ramo:verify` 가 검증 대상을 `git diff --name-only` 로 확정함. 자기보고를 믿지 않음" (`README.md:123`)

## 원문

- obra/superpowers — https://github.com/obra/superpowers
- humanlayer/advanced-context-engineering-for-coding-agents — https://github.com/humanlayer/advanced-context-engineering-for-coding-agents
- github/spec-kit — https://github.com/github/spec-kit
- woowabros/ramo-harness — https://github.com/woowabros/ramo-harness
- jh941213/ADLC-harness — https://github.com/jh941213/ADLC-harness
- Claude Code 공식 문서 Permission modes(plan mode) — https://code.claude.com/docs/en/permission-modes
