# GitHub 근거 대장 (확인일 2026-11-05)

- 방법: `gh api repos/X/commits/HEAD`로 기본 브랜치 HEAD를 고정하고, `contents/PATH?ref=SHA`로 받은 원문에 `grep -n`을 써서 줄 번호를 붙였다. 모든 `path:line`은 아래 표의 SHA 기준이다.
- 커밋일은 HEAD 커밋의 committer 날짜(UTC)다. ★는 2026-11-05 API 조회값이다.
- 라이선스는 `gh api repos/X --jq .license.spdx_id` 값이다. null이면 "표기 없음"으로 적었다.
- 인용은 원문 언어 그대로 두고, 요약은 한국어로 적었다. "추론"이라고 표시한 줄은 원문에 직접 쓰여 있지 않은 해석이다.

| 저장소 | SHA | 커밋일 | 라이선스 | ★ |
|---|---|---|---|---|
| obra/superpowers | `22f0b463` | 2026-11-03 | MIT | 312,540 |
| github/spec-kit | `ec9a6f3b` | 2026-11-04 | MIT | 147,413 |
| humanlayer/advanced-context-engineering-for-coding-agents | `da16ab73` | 2026-10-16 | 표기 없음 | 2,821 |
| (참고) humanlayer/humanlayer | `f9bd7353` | 2026-11-02 | Apache-2.0 | 12,807 |
| QoderAI/better-harness | `b605532f` | 2026-10-20 | MIT | 2,441 |
| china-qijizhifeng/agentic-harness-engineering | `182ea06e` | 2026-10-30 | MIT | 960 |
| walkinglabs/learn-harness-engineering | `a9342ff4` | 2026-10-22 | MIT | 23,166 |
| rasbt/mini-coding-agent | `717cae4f` | 2026-04-07 | Apache-2.0 | 1,222 |
| shareAI-lab/learn-claude-code | `7226f555` | 2026-10-27 | MIT | 79,896 |
| mokevnin/agentic-coding-design-patterns | `b96cbedd` | 2026-10-31 | NOASSERTION (LICENSE 본문은 CC BY-SA 4.0) | 265 |
| jh941213/ADLC-harness | `e9843a1c` | 2026-10-28 | 표기 없음 | 125 |
| JinHo-von-Choi/anti-samcheonpo | `89533e0d` | 2026-11-04 | MIT | 127 |
| Dominic-DK/harness-map | `40deadb2` | 2026-10-05 | MIT | 79 |
| woowabros/ramo-harness | `3485937e` | 2026-10-20 | MIT | 30 |
| revfactory/harness | `92d9f1b2` | 2026-09-28 | Apache-2.0 | 9,324 |
| anthropics/claude-quickstarts | `8ef47d71` | 2026-11-02 | MIT | 19,110 |
| anthropics/claude-plugins-official (`plugins/ralph-loop`) | `1aa4a4b1` | 2026-11-06 | Apache-2.0 | 46,253 |

전체 SHA:

```text
obra/superpowers                                          22f0b463e7a5e579904dd6211a520321035526f7
github/spec-kit                                           ec9a6f3b94c0aa856f77e550785a1ddde1993de1
humanlayer/advanced-context-engineering-for-coding-agents da16ab73624cd48ace04d0d0474b2957d8e7c741
humanlayer/humanlayer                                     f9bd73534a9fb7099a274f951b698b1297122fd9
QoderAI/better-harness                                    b605532fcf1014bcb48d3e6940a5bc64e80cddd5
china-qijizhifeng/agentic-harness-engineering             182ea06e578df7b1d503eca537503c1e4c5a8a58
walkinglabs/learn-harness-engineering                     a9342ff471f2c0e60be0c08b9f4a7c502df4e442
rasbt/mini-coding-agent                                   717cae4ff10d01773bd12951f62a575825053414
shareAI-lab/learn-claude-code                             7226f555d48900076eba126acf37c9ed5f002b5d
mokevnin/agentic-coding-design-patterns                   b96cbedd5fffe32b3ce3b663f6dcfdd26ac0197d
jh941213/ADLC-harness                                     e9843a1cd9bf5329e8b1901d5363f5fe4e36a270
JinHo-von-Choi/anti-samcheonpo                            89533e0dffa44feaa3b1ba0f1b8c25522b44e76e
Dominic-DK/harness-map                                    40deadb2070f896e310bc92cbd8153d07344b189
woowabros/ramo-harness                                    3485937edac23f4a78c42429c4b4dd866a1e9b9f
revfactory/harness                                        92d9f1b29e7af81acebf51a9fcd1832e739a1414
anthropics/claude-quickstarts                             8ef47d719eba5379ff8f38133f5defcc499e856f
anthropics/claude-plugins-official                        1aa4a4b10e6c5e8694d0f72a03dbac4e93bcafd8
```

## 1. obra/superpowers

SHA `22f0b463e7a5e579904dd6211a520321035526f7`

### README의 기본 흐름 (7단계)

- `README.md:308` — 기본 흐름 절 제목 — "## The Basic Workflow"
- `README.md:310` — 1단계 brainstorming. 만들기 전에 질문으로 원하는 것과 이유를 끌어낸다 — "**brainstorming** - Activates before building anything. Draws out what you actually want, and why, through questions that get you describing it"
- `README.md:312` — 2단계 using-git-worktrees. 설계 승인 뒤 격리된 작업 공간 — "Activates after design approval. Creates isolated workspace on new branch, runs project setup, verifies clean test baseline."
- `README.md:314` — 3단계 writing-plans. README에는 2–5분 태스크와 완성 코드라고 적혀 있다(아래 SKILL.md와 다르다) — "Breaks work into bite-sized tasks (2-5 minutes each). Every task has exact file paths, complete code, verification steps."
- `README.md:316` — 4단계 subagent-driven-development 또는 executing-plans — "Either dispatches a fresh subagent per task with a review after each (most thorough), or implements every task inline in the current session with one fresh review of the whole branch at the end (cheapest)."
- `README.md:318` — 5단계 test-driven-development — "Enforces RED-GREEN-REFACTOR: write failing test, watch it fail, write minimal code, watch it pass, commit. Deletes code written before tests."
- `README.md:320` — **6단계 requesting-code-review (TDD와 finishing 사이의 단계)** — "**requesting-code-review** - Activates between tasks. Reviews against plan, reports issues by severity. Critical issues block progress."
- `README.md:322` — 7단계 finishing-a-development-branch — "Activates when tasks complete. Verifies tests, presents options (merge/PR/keep/discard), cleans up worktree."
- `README.md:324` — 흐름은 권고가 아니라 의무 — "**The agent checks for relevant skills before any task.** Mandatory workflows, not suggestions."
- `README.md:349` — verification-before-completion은 기본 흐름 7단계에 없고 스킬 목록에만 있다 — "**verification-before-completion** - Ensure it's actually fixed"
- `README.md:355` — executing-plans 한 줄 정의 — "**executing-plans** - Inline plan execution: one context, one final review"
- `README.md:361` — subagent-driven-development 한 줄 정의 — "**subagent-driven-development** - Fast iteration with two-stage review (spec compliance, then code quality)"

### skills/writing-plans/SKILL.md

- `skills/writing-plans/SKILL.md:10` — 대상 독자는 코드베이스를 모르는 구현자이고, 계획은 그가 알 수 없는 결정을 적는 문서다 — "What they cannot know is what you decided: which files, which names and signatures, which values from the spec, which tests prove each task."
- `skills/writing-plans/SKILL.md:16` — 계획 파일 위치·이름 형식 — "**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`"
- `skills/writing-plans/SKILL.md:17` — 사용자 선호가 기본 위치보다 우선 — "(User preferences for plan location override this default)"
- `skills/writing-plans/SKILL.md:36-37` — 태스크 크기 기준은 시간이 아니라 자기 테스트 주기와 리뷰 단위다 — "A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate."
- `skills/writing-plans/SKILL.md:40-41` — 태스크 끝 조건 — "Each task ends with an independently testable deliverable."
- `skills/writing-plans/SKILL.md:45` — 스텝 크기 기준 — "**Each step is one action with a checkable result:**"
- `skills/writing-plans/SKILL.md:54` — 계획 문서 헤더 필수. 헤더 항목은 Goal(`:61`), Architecture(`:63`), Tech Stack(`:65`), Spec(`:67`), Global Constraints(`:70`), Review Focus(`:77`) — "**Every plan MUST start with this header:**"
- `skills/writing-plans/SKILL.md:97-100` — 태스크마다 정확한 파일 경로(생성·수정 줄 범위·테스트) — "- Create: `exact/path/to/file.py`" / "- Modify: `exact/path/to/existing.py:123-145`" / "- Test: `tests/exact/path/to/test.py`"
- `skills/writing-plans/SKILL.md:102-106` — 태스크 사이 계약인 Interfaces 블록 — "- Consumes: [what this task uses from earlier tasks — exact signatures]"
- `skills/writing-plans/SKILL.md:108-132` — 태스크의 5스텝: 실패 테스트 작성 → 실패 확인 → 구현 → 통과 확인 → 커밋 — "- [ ] **Step 1: Write the failing test**" … "- [ ] **Step 5: Commit**"
- `skills/writing-plans/SKILL.md:148-151` — 코드 스텝은 시그니처까지만 쓰고 본문은 구현자가 쓴다(완성 코드가 아니다) — "the exact signature (name, parameters, return type), the file it lives in, and the specific values the spec pins. The implementer writes the body."
- `skills/writing-plans/SKILL.md:152-153` — 검증 스텝은 명령과 통과 출력 — "**A verification step:** the command to run and the output that means it passed."
- `skills/writing-plans/SKILL.md:157-158` — 계획이 코드보다 길면 실패 — "A plan is the set of decisions the implementer cannot make alone. A plan longer than the code it describes has written the code instead."
- `skills/writing-plans/SKILL.md:191-192` — 실행 방식 두 가지 제시(Subagent-driven / Native) — "**Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts"
- 이력(같은 저장소, 참고): 현재 SKILL.md에는 "minute"이 한 번도 나오지 않는다(`grep -n -i minute` 결과 0건). 직전 버전 `5bf4e780`(v6.4.1, 2026-09-19)의 `skills/writing-plans/SKILL.md:47`에는 "**Each step is one action (2-5 minutes):**"가 있었고, `8ca22dba`(v6.4.2 "leaner plans from writing-plans", 2026-09-25)에서 빠졌다. 즉 2–5분은 원래 태스크가 아니라 스텝 기준이었고, 현재 README:314에만 남아 있다.

### executing-plans와 subagent-driven-development의 차이

- `skills/executing-plans/SKILL.md:8-10` — 같은 세션에서 직접 구현, 태스크별 서브에이전트·리뷰어 없음, 끝에 전체 리뷰 1회 — "Execute the plan yourself, task by task, in this session: no implementer subagent per task, no reviewer per task. One fresh-context review of the whole branch at the end."
- `skills/executing-plans/SKILL.md:12-14` — 인라인을 고르는 이유는 비용 — "Subagent-driven development pays for a fresh implementer and a fresh reviewer on every task, each re-reading the codebase from zero."
- `skills/subagent-driven-development/SKILL.md:8` — 태스크마다 새 구현 서브에이전트 + 태스크 리뷰 + 끝에 전체 리뷰 — "Execute plan by dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end."
- `skills/subagent-driven-development/SKILL.md:12` — 핵심 원칙 — "**Core principle:** Fresh subagent per task + task review (spec + quality) + broad final review = high quality, fast iteration"

### skills/verification-before-completion/SKILL.md

- `skills/verification-before-completion/SKILL.md:10` — 핵심 원칙 — "**Core principle:** Evidence before claims, always."
- `skills/verification-before-completion/SKILL.md:17` — 철칙 — "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"
- `skills/verification-before-completion/SKILL.md:20` — 이번 메시지에서 실행하지 않았으면 통과라고 말할 수 없다 — "If you haven't run the verification command in this message, you cannot claim it passes."
- `skills/verification-before-completion/SKILL.md:27-33` — 게이트 다섯 단계 — "1. IDENTIFY … 2. RUN … 3. READ … 4. VERIFY … 5. ONLY THEN: Make the claim"
- `skills/verification-before-completion/SKILL.md:47` — 에이전트의 성공 보고는 근거가 아니다 — "| Agent completed | VCS diff shows changes | Agent reports \"success\" |"

### skills/brainstorming/SKILL.md

- `skills/brainstorming/SKILL.md:10-11` — 목적: 만들기 전에 원하는 것과 이유를 알아낸다 — "This skill is for finding out what they actually want, and why, before anything gets built."
- `skills/brainstorming/SKILL.md:26-32` — 구현 전 순서: 접근안 제시·선택 → 설계 문서 → 승인 → writing-plans — "Before you start implementing, you must, in order: 1. Lay out the approaches … 2. Write the design doc … 3. Get their approval … 4. Invoke the superpowers:writing-plans skill."
- `skills/brainstorming/SKILL.md:78-79` — 요청이 불분명하면 가장 큰 미정 사항에 대해 열린 질문 하나 — "one open question, in their own terms, about the biggest thing their request leaves unsettled."
- `skills/brainstorming/SKILL.md:101-102` — 질문 조건 — "Ask a question only when the answer would change what gets built and neither the request nor the project answers it."
- `skills/brainstorming/SKILL.md:106` — 한 번에 하나씩 — "Ask one at a time."
- `skills/brainstorming/SKILL.md:245-246` — 설계 문서 위치 — "`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, committed."
- `skills/brainstorming/SKILL.md:268-269` — HARD-GATE: 설계 문서 승인 전에는 아무것도 만들지 않는다 — "Nothing gets built until your human partner approves the design doc"

## 2. github/spec-kit

SHA `ec9a6f3b94c0aa856f77e550785a1ddde1993de1`

### README 최소 흐름

- `README.md:105-107` — 헌법은 프로젝트당 한 번, 나머지는 기능마다, 한 단계씩 결과를 검토하며 — "Create a constitution once per project and repeat the remaining steps for each feature. … one at a time, reviewing each result before continuing."
- `README.md:113` — "/speckit-constitution Create principles focused on code quality, testing, and maintainability."
- `README.md:114` — "/speckit-specify Build a photo organizer with albums grouped by date and a tile preview of each album."
- `README.md:115` — "/speckit-plan Use Vite with vanilla JavaScript. Keep images local and store metadata in SQLite."
- `README.md:116` — "/speckit-tasks"
- `README.md:117` — "/speckit-implement"
- `README.md:118` — "/speckit-converge"
- `README.md:121` — 수렴 반복 — "Repeat implement and converge until convergence reports `Converged`."
- `docs/quickstart.md:40` — 전체 경로는 clarify·checklist·analyze를 품질 게이트로 더한다 — "**Full path** — for production features, adding `/speckit-clarify`, `/speckit-checklist`, and `/speckit-analyze` as quality gates:"
- `docs/reference/agentic-sdd.md:15` — 전체 명령 사슬 — "/speckit.constitution -> /speckit.specify -> /speckit.clarify -> /speckit.plan -> /speckit.checklist -> /speckit.tasks -> /speckit.analyze -> /speckit.implement -> /speckit.converge"
- `templates/commands/converge.md:2` — converge가 하는 일: 코드와 spec·plan·tasks를 대조해 남은 일을 tasks.md에 덧붙인다 — "Assess the current codebase against the feature's spec, plan, and tasks, then append any remaining unbuilt work as new tasks to tasks.md"
- `docs/reference/agentic-sdd.md:157` — Converged의 뜻 — "**Converged** — no gaps found. `tasks.md` is left byte-for-byte unchanged"
- `docs/reference/agentic-sdd.md:158` — 틈이 있으면 태스크를 덧붙이고 implement로 돌아간다 — "Run `/speckit.implement` again to complete them, then `/speckit.converge` once more."

### 헌법(constitution)

- `docs/reference/agentic-sdd.md:39` — 헌법의 정의 — "the guiding principles that every later phase is evaluated against — and keeps dependent templates in sync."
- `spec-driven.md:276` — 불변 원칙 집합, 위치는 `memory/constitution.md` — "At the heart of SDD lies a constitution—a set of immutable principles that govern how specifications become code."
- `templates/constitution-template.md:17-19` — 예시 원칙에 Test-First(NON-NEGOTIABLE)가 있다. 예시일 뿐 고정 원칙은 아니다 — "<!-- Example: III. Test-First (NON-NEGOTIABLE) -->"
- `templates/plan-template.md:39-43` — 계획 안의 헌법 게이트 — "*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*"

### templates/plan-template.md (계획이 담는 칸)

- `templates/plan-template.md:3` — 브랜치·날짜·spec 링크 — "**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]"
- `templates/plan-template.md:21-37` — Technical Context 칸: Language/Version, Primary Dependencies, Storage, Testing, Target Platform, Project Type, Performance Goals, Constraints, Scale/Scope. 모르면 표시 — "**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]"
- `templates/plan-template.md:50-56` — 기능 문서 묶음: plan.md, research.md, data-model.md, quickstart.md, contracts/, tasks.md — "└── tasks.md             # Phase 2 output (__SPECKIT_COMMAND_TASKS__ command - NOT created by __SPECKIT_COMMAND_PLAN__)"
- `templates/plan-template.md:61-64` — 소스 구조는 실제 경로로 채운다 — "expand the chosen structure with real paths (e.g., apps/admin, packages/something)."
- `templates/plan-template.md:103` — 구조 결정 기록 — "**Structure Decision**: [Document the selected structure and reference the real directories captured above]"
- `templates/plan-template.md:108` — 헌법 위반 정당화 표 — "**Fill ONLY if Constitution Check has violations that must be justified**"

### templates/tasks-template.md (태스크가 담는 칸)

- `templates/tasks-template.md:12` — **테스트 태스크는 선택**이다 — "**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification."
- `templates/tasks-template.md:16` — 태스크 형식 — "## Format: `[ID] [P?] [Story] Description`"
- `templates/tasks-template.md:18` — [P] 병렬 표시 — "**[P]**: Can run in parallel (different files, no dependencies)"
- `templates/tasks-template.md:20` — 정확한 파일 경로 — "Include exact file paths in descriptions"
- `templates/tasks-template.md:39-42` — 사용자 스토리 단위로 나눠 독립 구현·독립 테스트·MVP 증분 — "Tasks MUST be organized by user story so each story can be: - Implemented independently - Tested independently - Delivered as an MVP increment"
- `templates/tasks-template.md:73` — 체크포인트 — "**Checkpoint**: Foundation ready - user story implementation can now begin in parallel"
- `templates/tasks-template.md:85` — 테스트를 넣는 경우 먼저 쓰고 실패를 확인 — "**NOTE: Write these tests FIRST, ensure they FAIL before implementation**"
- `templates/tasks-template.md:182-186` — 스토리 안 순서 — "Tests (if included) MUST be written and FAIL before implementation" / "Models before services" / "Services before endpoints"
- `templates/tasks-template.md:250-251` — 커밋·체크포인트 — "Commit after each task or logical group" / "Stop at any checkpoint to validate story independently"
- `templates/tasks-template.md:252` — 피할 것 — "Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence"

## 3. humanlayer/advanced-context-engineering-for-coding-agents

SHA `da16ab73624cd48ace04d0d0474b2957d8e7c741`. 저장소 트리에 LICENSE 파일이 없고 GitHub 라이선스 값도 null이다.

- `ace-fca.md:12` — 기법 이름 — "We use a family of techniques I call \"frequent intentional compaction\" - deliberately structuring how you feed context to the AI throughout the development process."
- `ace-fca.md:60` — 40–60% 범위와 사람 리뷰 지점 — "keeping utilization in the 40-60% range, and building in high-leverage human review at exactly the right points."
- `ace-fca.md:218` — 정의 — "designing your ENTIRE WORKFLOW around context management, and keeping utilization in the 40%-60% range (depends on complexity of the problem )."
- `ace-fca.md:220-222` — 세 단계(대략)이고 리서치를 건너뛰거나 여러 번 할 때도 있다 — "split into three (ish) steps." / "sometimes we skip the research and go straight to planning"
- `ace-fca.md:228` — Research — "Understand the codebase, the files relevant to the issue, and how information flows, and perhaps potential causes of a problem."
- `ace-fca.md:237` — Plan — "Outline the exact steps we'll take to fix the issue, and the files we'll need to edit and how, being super precise about the testing / verification steps in each phase."
- `ace-fca.md:244` — Implement — "Step through the plan, phase by phase. For complex work, I'll often compact the current status back into the original plan file after each implementation phase is verified."
- `ace-fca.md:248` — worktree는 구현 단계에만 — "this is the only step that needs to be done in a worktree. We tend to do everything else on main."
- `ace-fca.md:266-267` — 틀린 리서치를 버린 사례 — "Claude decided the bug was invalid and the codebase was correct." / "I threw that research out and kicked off a new one, with more steering."
- `ace-fca.md:302` — 절 제목 — "### This is not Magic"
- `ace-fca.md:304` — 사람이 깊이 관여해야 한다 — "You have to engage with your task when you're doing this or it WILL NOT WORK."
- `ace-fca.md:306` — 마법 프롬프트는 없다 — "There's a certain type of person who is always looking for the one magic prompt that will solve all their problems. It doesn't exist."
- `ace-fca.md:308` — 어려운 문제에 충분한 이유는 사람 리뷰 — "what makes it **good enough for hard problems** is that you build high-leverage human review into your pipeline."
- `ace-fca.md:323-324` — 계획·리서치 한 줄의 레버리지 — "a bad line of **research**, a misunderstanding of how the codebase works … could land you with thousands of bad lines of code."
- `ace-fca.md:230`, `:239`, `:246` — 링크된 프롬프트: `humanlayer/humanlayer/blob/main/.claude/commands/research_codebase.md`, `create_plan.md`, `implement_plan.md`

### 링크된 프롬프트 파일의 현재 위치 (humanlayer/humanlayer `f9bd73534a9fb7099a274f951b698b1297122fd9`)

- 세 경로 모두 현재 기본 브랜치에 **없다**. recursive 트리(6,817개, truncated=false)에서 `research_codebase`, `create_plan`, `.claude/commands`를 찾았으나 없었다. 현재 `.claude/`에는 `hooks/`, `settings.json`, `skills/`만 있다.
- 삭제 커밋: `d8197bab`(2026-10-22, "HumanLayer: the desktop app, daemon, CLI, web UI, API, and plugins")의 파일 목록에서 세 파일이 모두 `removed`다.
- 삭제 전 마지막 수정 커밋(원문을 고정해 인용하려면 이 SHA를 쓴다): `research_codebase.md` → `c2c31d65`(2025-10-15), `create_plan.md` → `77c7fe99`(2025-11-12), `implement_plan.md` → `1c150cc0`(2025-10-15).
- 이름이 비슷한 현재 파일: `apps/riptide-rpi-claude-plugin/skills/create-research/SKILL.md`, `.../create-plan/SKILL.md`, `.../implement-plan/SKILL.md`(같은 이름이 `apps/riptide-pi-extension/skills/` 아래에도 있다). 세 파일의 `:3`은 모두 "description: Only use when the user explicitly invokes this skill by name."이다. 원래 프롬프트를 옮긴 것인지는 **내용을 대조하지 않아 확인하지 못했다**.

## 4. QoderAI/better-harness

SHA `b605532fcf1014bcb48d3e6940a5bc64e80cddd5`

- `README.md:16-18` — 무엇을 하나: 코딩 에이전트를 통해 돌고 프로젝트·세션 근거를 개선 항목으로 바꾼다 — "It runs through your Coding Agent and turns project and session evidence into prioritized improvements and verifiable next steps. Missing evidence stays explicit."
- `README.md:112-115` — feedforward·feedback 고리(Martin Fowler 글 링크) — "Better Harness uses a [feedforward-and-feedback](…) loop that combines guidance available before work starts with signals available after the agent acts:"
- `README.md:117-118` — Feedforward — "**Feedforward guides** — `AGENTS.md`, specs, Skills, and acceptance criteria steer the agent before it acts."
- `README.md:119-120` — Feedback — "**Feedback sensors** — linters, tests, Hooks, and evaluation agents observe results and help the agent self-correct."
- `README.md:122` — 다섯 차원 = Agent Work Loop — "it evaluates five parts of delivery — the **Agent Work Loop**:"
- `README.md:128` — Task Understanding — "Does the agent know the goal and what \"done\" means? | Rules, `AGENTS.md`, specs, `DESIGN.md`"
- `README.md:129` — Controlled Execution — "Is the work on supported, repeatable paths? | Skills, commands, MCP tools, sandbox boundaries"
- `README.md:130` — Change Validation — "Is there evidence the change actually works? | Tests, lint, Hooks, observable diagnostics"
- `README.md:131` — Reliable Delivery — "Does AI speed bypass quality checks or acceptance? | Human review, approvals, CI/CD, recovery paths"
- `README.md:132` — Learning Capture — "Does the next task benefit from this one? | Loop Discovery, reusable SDLC Skills, Memory"
- `README.md:141-143` — 요청한 문장 — "Passing a current check proves that the intervention was exercised; only a comparable later result can prove that the loop improved."
- `README.md:159-161` — 설정 존재와 사용 증거의 구분 — "configured assets can establish that a mechanism exists, but only linked task evidence can establish that it was used or improved an outcome."
- `README.md:167-169` — 근거 영역 셋은 리드 에이전트가 합치기 전까지 독립 — "The architecture keeps the three evidence domains independent until unified analysis by the lead agent."

### 세션을 읽는 방식

- `README.md:207-209` — Claude Code에서는 같은 작업 폴더의 로컬 세션을 포함한다 — "Workspace-matching local Claude sessions are included when available; missing evidence stays explicit rather than being inferred."
- `README.md:428-432` — 세션을 읽지 않는 실행 — "inspect repository evidence without reading local sessions:" / "node scripts/better-harness.mjs report --no-sessions"
- `skills/better-harness/SKILL.md:34-38` — 먼저 로컬 CLI가 근거 묶음을 만든다 — "Before delegation, collect one versioned evidence bundle per authorized provider:" / "<cli> harness evidence-bundle --platform <provider> …"
- `skills/better-harness/SKILL.md:71-73` — 그다음 새 읽기 전용 에이전트 셋이 병렬로 판단한다 — "Launch exactly three fresh, read-only agents in parallel."
- `skills/better-harness/SKILL.md:80-81` — 세션 에이전트에는 원 세션이 아니라 facts 요약만 준다 — "Do not pass the complete bundle, collection reference, debug output, or raw sessions to Agent 1."
- 추론: 별도 외부 API를 부른다는 문장은 없다. 다만 분석 주체가 호스트 코딩 에이전트(`README.md:16-17`)와 그 하위 에이전트(`SKILL.md:71`)이므로, 세션에서 뽑은 facts는 호스트 에이전트가 쓰는 모델의 컨텍스트에 들어간다. "세션 내용을 모델에 보낸다/안 보낸다"를 명시한 문장은 찾지 못했다.

### Claude Code 설치

- `README.md:183` — "/plugin marketplace add QoderAI/better-harness"
- `README.md:189` — "/plugin install better-harness@better-harness"
- `README.md:195` — 확인 — "claude plugin details better-harness@better-harness"
- `README.md:202` — 실행 — "/better-harness analyze this project's AI coding workflow and generate an evidence-backed report"
- `README.md:205-206` — 출력 위치 — "Claude Code defaults to a self-contained `report.html` with paired `report.md` and `findings.json` under the repository's `.claude/better-harness` report root."

## 5. china-qijizhifeng/agentic-harness-engineering

SHA `182ea06e578df7b1d503eca537503c1e4c5a8a58`

- `README.md:6`, `README.md:30` — arXiv 번호 **2604.25850**(2026-04-28 공개) — "Paper released on arXiv: [Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/abs/2604.25850)"
- `README.md:37` — 모델은 고정하고 하네스 구성 요소만 진화시킨다. 구성 요소 나열 — "The base model is held fixed; what evolves are the harness components — system prompts, tool descriptions, tool implementations, middleware, skills, sub-agents, and long-term memory."
- `README.md:39` — "AHE rests on three observability layers:"
- `README.md:41` — 구성 요소 관측 — "**Component observability** — [**NexAU**](…) decomposes the harness into seven orthogonal, file-level components, each git-tracked so every edit is auditable and revertible."
- `README.md:42` — 경험 관측 — "**Experience observability** — *Agent Debugger* distills ~10M-token raw traces into layered, sourced reports"
- `README.md:43` — 결정 관측 — "**Decision observability** — *Evolve Agent* proposes evidence-backed edits, predicts their impact, and is automatically falsified by the next iteration's flipped tasks."
- `README.md:45` — 69.7% → 77.0% — "Across ten `evaluate → analyze → improve` iterations, **AHE** … lifts Terminal-Bench 2 pass@1 from **69.7% to 77.0%** on GPT-5.4, surpasses the hand-written Codex (71.9%)"
- `README.md:194` — 일곱 구성 요소의 파일 목록 — "the seven NexAU components: `systemprompt.md`, `code_agent.yaml`, `tool_descriptions/`, `tools/`, `middleware/`, `skills/`, `sub_agents/` (plus `LongTermMEMORY.md`)."
- `README.md:196-199` — 편집마다 남겨야 하는 네 칸: Failure evidence, Root cause, Targeted fix, Predicted impact — "4. **Predicted impact** — which tasks should flip to pass, and which are at risk"
- `README.md:190` — Agent Debugger는 일부만 공개 — "The current release ships a *partially* open-sourced Agent Debugger"
- 주의: 일곱 구성 요소 목록이 두 곳에서 다르다. `:37`은 system prompts·tool descriptions·tool implementations·middleware·skills·sub-agents·long-term memory(7개)이고, `:194`는 `systemprompt.md`·`code_agent.yaml`·`tool_descriptions/`·`tools/`·`middleware/`·`skills/`·`sub_agents/`(7개)에 `LongTermMEMORY.md`를 "plus"로 따로 둔다. 차이는 `code_agent.yaml`과 long-term memory의 자리다.

## 6. walkinglabs/learn-harness-engineering

SHA `a9342ff471f2c0e60be0c08b9f4a7c502df4e442`

### 두 가지 "다섯 하위 시스템"

- `README.md:189` — 강의 쪽 정의 — "A harness has five subsystems:"
- `README.md:195` — 그림 대체 텍스트 — "Five harness subsystems: instructions, state, verification, scope, and session lifecycle."
- `README.md:237-241` — 각 하위 시스템의 일: Instructions, State, Verification, Scope, Session Lifecycle — "**Verification** — Only a passing test suite counts as evidence. The agent cannot declare victory without runnable proof."
- `README.md:453` — L02 행 — "Five subsystems: instructions, state, verification, scope, lifecycle"
- `README.md:46` — **Harness Design Breakdowns는 다른 다섯 개를 쓴다** — "Apply the course's five-subsystem framework (instructions, tools, environment, state, feedback) to reverse-engineer how four frontier products build real harnesses."
- `README.md:47-50` — 분석 대상 넷: Pi, Claude Code, Codex, DeepSeek

### 강의 L01–L14 (`README.md:452-465`, 각 행의 핵심 질문)

- `:452` L01 — "Why do strong models still fail on real tasks?"
- `:453` L02 — "What does \"harness\" actually mean?"
- `:454` L03 — "Why must the repo be the single source of truth?"
- `:455` L04 — "Why does one giant instruction file fail?"
- `:456` L05 — "Why do long-running tasks lose continuity?"
- `:457` L06 — "Why does initialization need its own phase?"
- `:458` L07 — "Why do agents overreach and under-finish?"
- `:459` L08 — "Why are feature lists harness primitives?"
- `:460` L09 — "Why do agents declare victory too early?"
- `:461` L10 — "Why does end-to-end testing change results?"
- `:462` L11 — "Why does observability belong inside the harness?"
- `:463` L12 — "Why must every session leave a clean state?"
- `:464` L13 — "Why do you need to stop prompting your agent?"
- `:465` L14 — "Why does a single loop grow into a graph?"

### 프로젝트 P01–P08 (`README.md:471-478`)

- `:471` P01 — "Run the same task twice: prompt-only vs. rules-first | Minimal harness: AGENTS.md + init.sh + feature_list.json"
- `:472` P02 — "Restructure the repo so the agent can read it"
- `:473` P03 — "Make the agent pick up from where it left off"
- `:474` P04 — "Stop the agent from doing too much or too little"
- `:475` P05 — "Make the agent verify its own work"
- `:476` P06 — "Build a complete harness from scratch (capstone)"
- `:477` P07 — "Build your first automated loop"
- `:478` P08 — "Draw your workflow as a graph"
- 주의: `README.md:287-288`은 "13 conceptual units"와 "7 hands-on projects"라고 적어, 같은 README의 14강·8프로젝트(`:31-32`, `:446`, `:467`)와 맞지 않는다.

### 템플릿

- `README.md:289` — 자료실 — "Copy-ready templates (`AGENTS.md`, `feature_list.json`, `init.sh`, etc.) to use in your own repositories today."
- `README.md:300-305` — 프로젝트 루트 파일 — "├── AGENTS.md <-- the agent's operating manual" … "├── claude-progress.md <-- session progress (historical filename; agent-agnostic)"
- `README.md:309` — "Four files, and your agent sessions will already be significantly more stable than running on prompts alone."
- 트리 기준 `docs/en/resources/templates/`의 파일 10개: `AGENTS.md`, `CLAUDE.md`, `claude-progress.md`, `clean-state-checklist.md`, `evaluator-rubric.md`, `feature_list.json`, `index.md`, `init.sh`, `quality-document.md`, `session-handoff.md`.

### 한국어 번역

- `README.md:15` — 한국어 README 링크 `docs-readme/ko-KR/README.md`(트리에 있음).
- `docs/ko/` 아래에 `lectures/`(lecture-01~14 폴더 14개), `projects/`(project-01~08), `harness-designs/`(`index.md`, `claude-code/`, `codex/`, `deepseek/`, `pi/`), `resources/templates/`(영문과 같은 10개)가 있다. 트리 비교에서 `docs/ko`는 파일 127개, `docs/en`은 128개다. 한국어에 없는 것은 `lectures/lecture-14-graph-engineering/code/index.md`와 `code/maker_checker_graph.py`이고, 한국어에만 있는 것은 `resources/reference/glossary.md`다.
- `docs/ko/lectures/lecture-02-what-a-harness-actually-is/index.md:6` — 강의 02 한국어 제목 — "# 강의 02. 하네스란 실제로 무엇인가"
- `docs/ko/lectures/lecture-02-what-a-harness-actually-is/index.md:10` — "하네스는 명확한 책임과 평가 기준을 가진 다섯 가지 하위 시스템으로 구성됩니다."
- `docs/ko/harness-designs/index.md:1` — "# 최전선 Harness 분석"
- `docs/ko/harness-designs/index.md:3` — 분석 쪽 다섯 개의 한국어 표기 — "명령, 도구, 환경, 상태, 피드백의 다섯 가지 하위 시스템"
- `docs/ko/resources/templates/index.md:7-12` — 처음 복사할 네 파일 — "1. `AGENTS.md` 또는 `CLAUDE.md`" / "2. `init.sh`" / "3. `claude-progress.md`" / "4. `feature_list.json`"

## 7. rasbt/mini-coding-agent

SHA `717cae4ff10d01773bd12951f62a575825053414`(예상한 `717cae4f…`와 일치, 2026-04-07 커밋)

- `README.md:18` — 모델 백엔드는 Ollama — "The model backend is currently based on Ollama."
- `README.md:95` — 기본 모델과 호출 지점 — "The default in this project is `qwen3.5:4b`. … The agent just sends prompts to Ollama's `/api/generate` endpoint."
- `README.md:36` — "This coding harness is organized around six practical building blocks:"
- `README.md:38-39` — 1. Live repo context — "The agent collects stable workspace facts upfront, such as repo layout, instructions, and git state."
- `README.md:40-41` — 2. Prompt shape and cache reuse — "A stable prompt prefix, which is separate from the changing request, transcript, and memory"
- `README.md:42-43` — 3. Structured tools, validation, and permissions — "named tools with checked inputs, workspace path validation, and approval gates instead of free-form arbitrary actions."
- `README.md:44-45` — 4. Context reduction and output management — "Long outputs are clipped, repeated reads are deduplicated, and older transcript entries are compressed"
- `README.md:46-47` — 5. Transcripts, memory, and resumption — "keeps both a full durable transcript and a smaller working memory so sessions can be resumed"
- `README.md:48-49` — 6. Delegation and bounded subagents — "Scoped subtasks can be delegated to helper agents that inherit enough context to help (but operate within limits)."

## 8. shareAI-lab/learn-claude-code

SHA `7226f555d48900076eba126acf37c9ed5f002b5d`

- `README.md:172-173` — 현재 정본은 루트의 s01–s17 — "The root-level `s01_*` ... `s17_*` folders are the canonical version."
- `README.md:183-195` — 옛 번호와 새 번호가 다르다. 예: 옛 s03 TodoWrite → 새 s05, 옛 s05 Skill Loading → 새 s07, 옛 s07 Task System → 새 s10, s03(Permission)·s17(Goal Loop) 등은 새로 생긴 장 — "| new only | s03, s04, s09, s12, s14, s15, s16, s17 | Permission, Hooks, Memory, Cron, MCP, Integrated Harness, Workflow Runtime, Goal Loop |"
- `README.md:209` — s01 — "*\"One loop & Bash is all you need\"* — one tool + one loop = one agent"
- `README.md:213` — s03 (Permission) — "*\"Set boundaries first, then grant freedom\"* — check what can run, what must stop, and what needs approval"
- `README.md:217` — s05 (TodoWrite) — "*\"An agent without a plan drifts\"* — list the steps before starting; completion rate doubles"
- `README.md:221` — s07 (Skill Loading) — "*\"Load knowledge on demand, not upfront\"* — list skills first, expand them only when needed"
- `README.md:223` — s08 (Context Compact) — "*\"Context always fills up -- have a way to make room\"* — four compaction steps reduce tool results first, then summarize history"
- `README.md:227` — s10 (Task System) — "*\"Big goals break into small tasks, ordered, persisted to disk\"* — a file-backed task graph"
- `README.md:241` — s17 (Goal Loop) — "*\"A goal decides when the loop may stop\"* — an independent evaluator reviews each proposed stop"
- `README.md:162` — 루프와 메커니즘의 구분 — "The loop belongs to the agent. The mechanisms belong to the harness."

## 9. mokevnin/agentic-coding-design-patterns

SHA `b96cbedd5fffe32b3ce3b663f6dcfdd26ac0197d`

### book/en/SUMMARY.md 목차

- `book/en/SUMMARY.md:7` "## Task Setting" — `:9` Four Phases, `:10` Agent-Led Interview, `:11` Grilling, `:12` Design It Twice, `:13` Tracer-Bullet Tickets
- `book/en/SUMMARY.md:15` "## Spec-Driven Development" — `:17` Overview; `:19` "### Tool Profiles" — `:21` OpenSpec, `:22` Superpowers, `:23` Matt Pocock's Skills
- `book/en/SUMMARY.md:25` "## Working with Context" — `:27` Context Engineering, `:28` Project Memory, `:29` Domain Vocabulary, `:30` Progress Journal, `:31` Session Handoff, `:32` Context Forking, `:33` Executable Guardrails
- `book/en/SUMMARY.md:35` "## Verification" — `:37` Feedback Loop, `:38` Quality Gates, `:39` TDD with an Agent, `:40` Hypothesis-Driven Debugging, `:41` Reflection, `:42` Writer and Reviewer, `:43` Throwaway Prototype, `:44` Agent Workflow Evals
- `book/en/SUMMARY.md:46` "## Project Organization" — `:48` Feature List, `:49` One Feature at a Time, `:50` Investigation Map, `:51` Issue Triage, `:52` Skills, `:53` Reproducible Agent Bootstrap, `:54` Isolated Parallel Work, `:55` Scheduled Maintenance
- `book/en/SUMMARY.md:57` "## Anti-patterns" — `:59` Premature Specification, `:60` Big Spec Up Front, `:61` Premature Success, `:62` Bloated Memory, `:63` Private Memory, `:64` Vibe Coding, `:65` One-Shotting
- `book/en/SUMMARY.md:67` "## Appendix" — `:69` Glossary, `:70` Phrases for AGENTS.md, `:71` Useful Links; `:73` "## Future Chapters" — `:75` Candidates and voting

### 라이선스

- `README.md:51` — "Text and diagrams — [CC BY-SA 4.0](LICENSE); code samples — CC0."
- `LICENSE:1-3` — "This work — the text and diagrams of the \"Agentic Design Patterns\" catalog — is licensed under the Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)."
- GitHub API의 SPDX 값은 `NOASSERTION`이다(자동 판별 실패). 실제 조건은 위 두 줄이 기준이다.

## 10. jh941213/ADLC-harness

SHA `e9843a1cd9bf5329e8b1901d5363f5fe4e36a270`

- `README.md:5` — 여덟 단계 루프 — "**AI SDLC 루프**(의도 → 설계 → 계획 → 구현 → 검증 → 리뷰 → 출시 → 학습)를 Claude Code·Codex·GitHub Copilot CLI에서 같은 방식으로 돌리는 개발 하네스 플러그인이다."
- `README.md:7` — 사람 승인 게이트 네 곳 — "사람은 의도·설계·계획·출시 게이트에서만 승인하고, 단계마다 문서와 승인 기록이 커밋으로 남는다."
- `README.md:8` — 완료 주장 규칙 — "완료는 이번에 실행한 검증 출력으로만 말한다."
- `README.md:76` — `/loopeng` — "`/loopeng <요청>`은 위 단계를 의도 → 설계 → 계획 → 구현 → 검증 → 리뷰 → 출시 → 학습 순서로 끝까지 돌린다."
- `README.md:78` — 게이트 — "**게이트**: 의도·설계·계획·출시(푸시·PR)에서만 멈추고 승인을 받는다. 그 사이의 구현·검증·리뷰는 묻지 않고 이어 간다."
- `README.md:79` — 세 번 실패하면 멈춤 — "검증이나 리뷰에서 실패하면 구현으로 돌아간다. 같은 원인으로 세 번 실패하면 멈추고 보고한다."
- `README.md:80` — 상태 판단 근거 — "작업 폴더의 문서, `승인:` 줄, plan 체크, `loop.md`(단계마다 한 줄씩 붙이는 기록)로 판단한다."
- `README.md:70` — git 기록이 승인 기록 — "승인한 문서에는 `승인: 날짜`를 적고 커밋하므로 git 기록이 곧 승인 기록이다."
- `README.md:95` — 메모리 기록과 hits — "같은 교정이 다시 나오면 기존 메모의 `hits`를 올린다."
- `README.md:96` — 승격 규칙 — "**승격**: `hits`가 2 이상이거나 사용자가 \"항상/절대\"라고 하면 AGENTS.md나 `~/.claude/CLAUDE.md`로 올리고 메모는 지운다. 장기 층을 바꿀 때는 diff를 보여 주고 승인받는다."

### 라이선스 확인

- GitHub API `license` 값: null.
- 루트 목록(`git/trees/SHA`): `.agents/`, `.claude-plugin/`, `.codex-plugin/`, `.gitattributes`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `agents/`, `assets/`, `commands/`, `hooks/`, `package.json`, `rtk/`, `scripts/`, `semgrep-rules/`, `skills/`, `test/`. **LICENSE·COPYING 파일 없음**(recursive 트리 전체에서도 없음). `package.json`에도 `license` 필드가 없다.
- `README.md:185-187` — "## 라이선스 고지" 절은 저장소 자체 라이선스가 아니라 포함된 외부 MIT 자료의 고지만 가리킨다 — "포함된 외부 MIT 자료의 저작권 고지는 [`skills/NOTICE.md`](skills/NOTICE.md)에 있다."
- `skills/NOTICE.md:5-7` — superpowers v7.0.1에서 가져온 스킬 목록(brainstorming, systematic-debugging, writing-plans, test-driven-development, verification-before-completion, receiving-code-review) — "## superpowers v7.0.1"

## 11. JinHo-von-Choi/anti-samcheonpo

SHA `89533e0dffa44feaa3b1ba0f1b8c25522b44e76e`

- `README.md:7` — 한 줄 정의 — "**AI 코딩 에이전트의 반복 작업과 실패를 기록하고, 필요하면 경고하거나 실행을 막는 로컬 도구**"
- `README.md:14` — 살피는 행동 — "**같은 검사 반복, 같은 오류 재시도, 요청 범위를 벗어난 수정** 같은 행동을 살펴봅니다."
- `README.md:35` — audit은 모델을 부르지 않는다 — "**1. 지난 기록을 분석합니다.** 에이전트 연결 없이 실행할 수 있습니다. 모델을 호출하지 않으며 분석 결과는 로컬 원장에 저장합니다."
- `README.md:38` — README의 예시 명령(codex만 보임) — "samcheonpo audit --agent codex --since 7d"
- `docs/getting-started.md:57` — 같은 내용 — "실시간 연결 전에 기존 Claude Code·Codex 기록을 분석할 수 있습니다. 모델 호출은 없고, 결과를 로컬 원장에 저장합니다."
- `docs/getting-started.md:65` — **`--agent claude` 지원** — "`audit --agent claude`는 Claude Code, `--agent all`은 두 종류의 기록을 분석합니다."
- `internal/cli/cli.go:158` — audit 명령 설명 — "Short: \"과거 세션 기록으로 멍청비용 영수증을 낸다\""
- `internal/cli/cli.go:288-289` — 기본값: 기간 30d, 에이전트 all — "\"since\", \"30d\"" / "\"agent\", \"all\", \"claude | codex | mcode | all\""
- `README.md:94` — 실시간 연결 쪽에는 선택 사항으로 외부 판정 모델이 있다 — "기록은 기본적으로 로컬에 저장합니다. 외부 판정 모델과 알림 전송은 설정에서 선택할 수 있습니다."
- `docs/reference.md:182` — 판정 모델 설정 키 — "판정 모델(`detectors.s3_drift.judge`)"
- 부분 코드 확인: `internal/analyze/analyze.go:5-22`의 import와 audit 경로가 쓰는 `internal/{detect,classify,contract,cost,rulepack,sources}`, `internal/cli/cli.go` 상단 import에서 `internal/judge`나 `net/http`를 찾지 못했다. 전이 의존성 전체는 보지 않았다.
- audit이 무엇을 "탐지"하는지 README에는 "지난 기록을 분석"(`README.md:35`)까지만 있다. 분류 버킷은 `internal/analyze/analyze.go:29-33`의 progress·explore·waste·other·watch다.

## 12. Dominic-DK/harness-map

SHA `40deadb2070f896e310bc92cbd8153d07344b189`

- `README.md:3` — 한 줄 정의 — "Claude Code 하네스를 읽어 한 장의 조립도로 보여 주는 도구이다."
- `README.md:5` — 읽는 대상 — "지시 파일(CLAUDE.md), 자동 기억, 도구(MCP, 스킬), 권한, 훅이 여기에 들어간다."
- `README.md:20` — "Python 3 가 필요하다. 추가 패키지는 필요 없다."
- `README.md:27-28` — 1단계: 설정 파일 읽기와 대화 기록 집계 — "설정 파일 읽기와 대화 기록 집계로 할 수 있는 점검도 이때 함께 수행한다." / "python3 harness-map.py --cwd ~/work/a --cwd ~/work/b -o harness.json"
- `README.md:31` — 2단계 — "python3 harness-map.py --probe-plan"
- `README.md:33-34` — 3단계는 에이전트가 하고 건너뛸 수 있다 — "(에이전트) 2단계의 안내대로 점검을 수행하고 결과를 probes.json 에 기록한다."
- `README.md:37` — 4단계 — "python3 harness-map.py --cwd ~/work/a --cwd ~/work/b --probes probes.json -o harness.json"
- `README.md:40-41` — 5단계 — "python3 build.py harness.json" / "open harness-map.html"
- `README.md:44` — 대화 기록 집계 기간 — "대화 기록 집계 기간은 기본 30일이며 `--days` 로 바꿀 수 있다."
- `README.md:55` — 읽기 전용 — "스크립트는 파일을 읽기만 하고 어떤 설정도 바꾸지 않는다."
- `README.md:59-63` — 남기는 것과 남기지 않는 것(본문·환경변수 값·명령 인자·토큰 제외) — "| MCP 서버 | 이름, 출처 | 명령, 인자, 헤더, 토큰 |"
- `README.md:79` — 점검 방법 셋 — "설정 파일을 읽는 방법, 대화 기록에서 개수를 세는 방법, 임시 폴더 안에서 실제로 시험해 보는 방법이다."
- `README.md:82` — "대화 기록은 개수만 센다. 대화 본문, 명령 내용, 파일 내용은 결과에 옮기지 않는다."
- `README.md:76` — 성숙도 여섯 분야 — "지시 설계, 기억과 위치, 도구 범위, 사전 차단, 사후 검증과 관측, 위임 설계이다."
- `README.md:88` — Python이 없으면 에이전트가 직접 읽는다 — "`PROMPT.md` 를 에이전트에 그대로 붙여 넣는다. 에이전트가 설정 파일을 직접 읽어 같은 형식의 JSON 을 만들고"
- `README.md:92` — 근거 버전 — "2026년 10월 2일에 확인한 공식 문서를 따른다. 확인한 버전은 Claude Code 2.1.287 이다."
- `harness-map.py:932-933` — 읽는 대화 기록 위치 — "\"main\": \"~/.claude/projects/*/*.jsonl\"," / "\"subagent\": \"~/.claude/projects/*/*/subagents/*.jsonl\","
- 모델 호출: README에 명시 문장은 없다. 코드상 `harness-map.py:20-31`의 import에 네트워크 라이브러리가 없고, `subprocess.run`은 `git`(`:121`, `:1769`)과 `claude --version`(`:2051`) 세 곳뿐이다. 따라서 스크립트(1·2·4단계)는 모델을 부르지 않는다. 3단계 점검과 `PROMPT.md` 경로는 에이전트(모델)가 수행한다.

## 13. woowabros/ramo-harness

SHA `3485937edac23f4a78c42429c4b4dd866a1e9b9f`

- `README.md:3-5` — 데이터 사이언스용 Claude Code 하네스, 8단계(+선택 0단계) — "Claude Code 안에서 8단계 파이프라인(과 그 앞의 선택 단계 0 research)을 도메인 서브에이전트, 강제된 출력 형식, 재현성 게이트로 반복 가능하게 만듦."
- `README.md:7-9` — 훅 강제 — "프롬프트 모음이 아니라 **강제 기구가 붙은 구성**임. 훅이 서브에이전트의 출력 형식과 재현성 증거(seed, split 경계, 데이터 스냅샷, 피처 명세)를 검사해 누락되면 막고"
- `README.md:14` — 흐름 — "(0 research) → 1 interview → 2 eda → 3 plan → 4 run → 5 verify → 6 diagnose → 7 doc → 8 mr"
- `README.md:20` — 0 `/ramo:research` — "(선택) 코드·논문·기술 블로그를 웹에서 모아 사람이 고르고, 주제별로 짧게 정리"
- `README.md:21` — 1 `/ramo:interview` — "문제를 6차원으로 질문해 확정"
- `README.md:22` — 2 `/ramo:eda` — "후보 테이블 해소, 타깃과의 관계 측정, 피처 후보와 누수 후보 분리"
- `README.md:23` — 3 `/ramo:plan` — "계획 작성 후 좌석별 병렬 리뷰와 개선 루프"
- `README.md:24` — 4 `/ramo:run` — "실행표의 태스크를 도메인 에이전트에 위임해 구현"
- `README.md:25` — 5 `/ramo:verify` — "바뀐 파일을 독립 팀이 검증하고 결함을 고침"
- `README.md:26` — 6 `/ramo:diagnose` — "오차를 슬라이스로 분해하고 다음 실험 후보를 순위화"
- `README.md:27` — 7 `/ramo:doc` — "오래 쓸 지식을 문서로 승격"
- `README.md:28` — 8 `/ramo:mr` — "사이클의 코드로 PR/MR 생성 (verify PASS 필요)"
- `README.md:30-31` — 사람 배턴 — "각 단계는 사람의 확인(배턴)을 거쳐 다음으로 넘어감. 자동 연쇄가 아니고, 한 단계가 끝나면 다음에 무엇을 치면 되는지가 화면에 나옴."
- `README.md:62` — run 단계 훅 차단 — "서브에이전트가 재현성 증거를 빠뜨리면 훅이 막음."
- `README.md:123` — verify는 자기보고를 믿지 않는다 — "`/ramo:verify` 가 검증 대상을 `git diff --name-only` 로 확정함. 자기보고를 믿지 않음"

## 14. revfactory/harness

SHA `92d9f1b29e7af81acebf51a9fcd1832e739a1414`

- `README.md:21` — 한 줄 정의 — "**Harness is a team-architecture factory for Claude Code.** One sentence — **\"build a harness for this project\"** · **\"하네스 구성해줘\"** — and the plugin turns your domain description into an agent team and the skills they use."
- `README.md:39` — 여섯 아키텍처 패턴 — "six architecture patterns (Pipeline, Fan-out/Fan-in, Expert Pool, Producer-Reviewer, Supervisor, Hierarchical Delegation), each mapped to its best v2 execution mode"
- `README.md:34` — `/harness:evolve` — "**`/harness:evolve` actually ships.** … it captures the delta between your initial and current harness, generalizes feedback, and feeds it back into agents/skills/orchestrators."
- `README.md:43` — "**Evolution** — `/harness:evolve` turns usage feedback into measurable next-generation improvements"
- `README.md:48-55` — Phase 0~7 흐름, 마지막이 유지보수 — "Phase 7: Maintenance — evolution via /harness:evolve"
- `README.md:121` — v1 수치는 저자 측정 — "mean quality 49.5 → 79.3 (+60%), 15/15 win rate … Treat these as author-measured numbers; run your own pilot for adoption decisions."
- `README.md:19` — 한국어 README(`README_KO.md`, 트리에 있음)

## 15. anthropics/claude-quickstarts

SHA `8ef47d719eba5379ff8f38133f5defcc499e856f`(예상한 `8ef47d71…`와 일치). 아래는 `autonomous-coding/README.md`만 인용했다. 코드는 읽지 않았다.

- `autonomous-coding/README.md:3` — 두 에이전트 패턴 — "This demo implements a two-agent pattern (initializer + coding agent) that can build complete applications over multiple sessions."
- `autonomous-coding/README.md:55` — 초기화 에이전트 — "**Initializer Agent (Session 1):** Reads `app_spec.txt`, creates `feature_list.json` with 200 test cases, sets up project structure, and initializes git."
- `autonomous-coding/README.md:57` — 코딩 에이전트 — "**Coding Agent (Sessions 2+):** Picks up where the previous session left off, implements features one by one, and marks them as passing in `feature_list.json`."
- `autonomous-coding/README.md:43` — 기능 수 200 — "The agent generates a `feature_list.json` with 200 test cases."
- `autonomous-coding/README.md:49` — 줄일 수 있다 — "you can modify `prompts/initializer_prompt.md` to reduce the feature count (e.g., 20-50 features for a quicker demo)."
- `autonomous-coding/README.md:61-64` — 세션 이어 가기 — "Each session runs with a fresh context window" / "Progress is persisted via `feature_list.json` and git commits" / "The agent auto-continues between sessions (3 second delay)" / "Press `Ctrl+C` to pause; run the same command to resume"
- `autonomous-coding/README.md:103` — feature_list.json의 위상 — "├── feature_list.json         # Test cases (source of truth)"
- `autonomous-coding/README.md:105-106` — 생성물에 init.sh와 진행 파일 — "├── init.sh                   # Environment setup script" / "├── claude-progress.txt       # Session progress notes"
- `autonomous-coding/README.md:68` — 보안 모델 — "This demo uses a defense-in-depth security approach (see `security.py` and `client.py`):"
- `autonomous-coding/README.md:70-72` — 세 겹: OS 샌드박스, 파일 시스템 제한, bash 허용 목록 — "**Bash Allowlist:** Only specific commands are permitted:"
- `autonomous-coding/README.md:73-76` — 허용 명령: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `npm`, `node`, `git`, `ps`, `lsof`, `sleep`, `pkill`(dev processes only)
- `autonomous-coding/README.md:78` — "Commands not in the allowlist are blocked by the security hook."
- `autonomous-coding/README.md:148` — 허용 목록 위치 — "Edit `security.py` to add or remove commands from `ALLOWED_COMMANDS`."
- `autonomous-coding/README.md:134` — 기본 모델 — "| `--model` | Claude model to use | `claude-sonnet-4-5-20250929` |"
- 주의: `autonomous-coding/README.md:163`은 "Internal Anthropic use."라고 적었지만 저장소 라이선스는 MIT다(API 값). 진행 파일 이름은 여기서 `claude-progress.txt`이고 learn-harness-engineering은 `claude-progress.md`다. 진행 저장 수단으로 `:62`는 `feature_list.json`과 git 커밋만 들고, `claude-progress.txt`는 생성물 목록(`:106`)에만 나온다.

## 16. anthropics/claude-plugins-official (`plugins/ralph-loop`)

SHA `1aa4a4b10e6c5e8694d0f72a03dbac4e93bcafd8`(SHA7 `1aa4a4b`, 커밋일 2026-11-06, 라이선스 Apache-2.0은 2026-11-06 API 조회값)

- 이 저장소는 `plugins/ralph-loop` 폴더만 `vendor/ralph-loop/`에 사본으로 두었다(`../../vendor/SNAPSHOTS.md`). 이 사본은 Part 4의 주 사례다.
- 줄 인용은 `plugins/ralph-loop/` 아래 경로이고 모두 위 SHA 기준이다. 줄 번호와 해석은 `claude_code/08_plugin_candidates.md`의 P3 절이 갖는다: `commands/ralph-loop.md:4`·`:16`·`:18`, `commands/cancel-ralph.md:3`, `hooks/hooks.json:4`, `hooks/stop-hook.sh:4`·`:13`·`:60-63`·`:135-136`·`:185`, `scripts/setup-ralph-loop.sh:140-143`.
- 라이선스: `plugins/ralph-loop/LICENSE`는 Apache-2.0 전문이고 저작권자 줄은 틀 그대로 "Copyright [yyyy] [name of copyright owner]"다. NOTICE 파일은 없다. 이 저장소의 MIT와 다르다.

## 확인 못 한 것

- **superpowers**: README:314의 "2-5 minutes each"와 "complete code"는 현재 `skills/writing-plans/SKILL.md`와 맞지 않는다. SKILL.md에는 시간 기준이 없고 코드 스텝은 시그니처만 쓴다(`:148-151`). README가 이전 표기를 남긴 것으로 보이지만 저자의 의도는 확인하지 않았다.
- **better-harness**: 세션 내용이 모델에 들어가는지 명시한 문장은 README와 SKILL.md에서 찾지 못했다. 4절의 결론은 "호스트 에이전트가 facts를 읽는다"는 구조에서 끌어낸 추론이다. `docs/specs/2026-07-31-security-reliability-boundaries.md` 등 세부 문서는 읽지 않았다.
- **anti-samcheonpo**: audit이 모델을 부르지 않는다는 근거는 문서(`README.md:35`, `docs/getting-started.md:57`)와 직접 의존 패키지의 import 확인뿐이다. 전이 의존성과 실행 동작은 확인하지 않았다.
- **humanlayer**: `apps/riptide-rpi-claude-plugin/skills/*`가 `ace-fca.md`가 링크한 원래 프롬프트를 이은 것인지는 내용을 대조하지 않아 모른다. 원래 프롬프트는 삭제 전 커밋(`c2c31d65`, `77c7fe99`, `1c150cc0`)으로 고정해 읽어야 한다.
- **agentic-harness-engineering**: arXiv 2604.25850 논문 본문은 열지 않았다. 일곱 구성 요소 목록은 README 두 곳(`:37`, `:194`)만 대조했고 둘이 다르다.
- **learn-harness-engineering**: 한국어 번역이 영문 최신본과 같은 시점의 내용인지(번역 지연 여부)는 파일 목록만 비교했고 본문은 대조하지 않았다.
- **claude-quickstarts**: 지시대로 `autonomous-coding`의 코드(`security.py`, `client.py`, `prompts/*`)는 읽지 않았다. README의 허용 명령 목록이 실제 `ALLOWED_COMMANDS`와 같은지는 코드 쪽 확인이 필요하다.
- **claude-plugins-official**: `plugins/ralph-loop` 밖(다른 plugin 40여 개, 마켓플레이스 카탈로그)은 `08_plugin_candidates.md`의 후보 비교용으로 열어 보았을 뿐 이 대장에서 인용하지 않는다.
- **★ 수**는 2026-11-05 조회 시점 값이라 바뀔 수 있다.
