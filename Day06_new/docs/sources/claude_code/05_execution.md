# Claude Code 근거 대장 — 계획과 실행 구조 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: `https://code.claude.com/docs/en/<page>.md`를 `curl -sL`로 내려받아(sub-agents, agents, worktrees, agent-teams, workflows, goal, headless, common-workflows 8쪽) 마크다운 링크 `[글](주소)`를 글만 남기고, 백틱과 `**` 표시를 지우고, 공백을 하나로 합친 뒤 `python3 -I` 스크립트로 모든 인용문이 원문의 부분 문자열인지 대조했다. WebFetch(요약 모델)는 쓰지 않았다.
- 괄호 안은 `쪽 이름: 가장 가까운 절 제목`이다. 한국어 주소는 `https://code.claude.com/docs/_llms/ko.txt`에 실린 것만 적었고(8쪽 모두 목록에 있었다) 한국어 본문은 인용하지 않았다. 표의 인용은 셀 안의 문장이다.
- 수준 표기: `원문 확인`은 대조를 통과한 인용문뿐이다. 문서에 없는 것은 `미확인`으로 사유를 적었다. 로컬은 `claude --version`이 `2.1.318 (Claude Code)`였고, `claude --help`와 `claude agents --help`만 썼다. 모델을 부르는 명령은 하나도 실행하지 않았다.


## X1 내장 서브에이전트 (Explore, Plan, General-purpose)

- 공식 문서: https://code.claude.com/docs/en/sub-agents.md (한국어: https://code.claude.com/docs/ko/sub-agents.md)
- `내장 서브에이전트는 부모의 권한 규칙을 물려받는다` — `원문 확인` — "Claude Code includes built-in subagents that Claude automatically uses when appropriate. Each inherits the parent conversation's permission rules; most run with a restricted tool set." (sub-agents: Built-in subagents)
- `Explore` — `원문 확인` — "A fast, read-only agent optimized for searching and analyzing codebases." (sub-agents: Built-in subagents)
- `Plan` — `원문 확인` — "A research agent used during plan mode to gather context before presenting a plan." (sub-agents: Built-in subagents)
- `General-purpose` — `원문 확인` — "A capable agent for complex, multi-step tasks that require both exploration and action." (sub-agents: Built-in subagents)
- `Explore와 Plan은 CLAUDE.md 없이 시작한다` — `원문 확인` — "Explore and Plan start without your CLAUDE.md files and the git status snapshot to keep research fast and inexpensive." (sub-agents: Built-in subagents)
- 2.1.318 확인: 해당 없음(내장 서브에이전트 목록은 `--help`에 나오지 않는다). `claude --help`의 `--agents <json-or-file>` 설명이 사용자 정의 에이전트 JSON을 받는다는 점만 확인했다.
- 수업에 쓸 점: 조사만 하는 일꾼은 읽기 전용이라 편집이 막힌다. 실행 제어(편집 금지)와 도구(관찰만) 책임을 한 문장으로 보여 준다.
- 주의: 내장 목록에는 이 밖에 `claude`, `statusline-setup`, `claude-code-guide`가 있다("Other" 탭). Explore의 모델은 연결 방식(구독, Bedrock 등)에 따라 달라진다고 문서가 적는다. 모델 이름은 바뀌기 쉽다.

## X2 사용자 정의 서브에이전트의 위치와 frontmatter

- 공식 문서: https://code.claude.com/docs/en/sub-agents.md (한국어: https://code.claude.com/docs/ko/sub-agents.md)
- `정의 형식` — `원문 확인` — "Configure a subagent with YAML frontmatter between --- markers at the top of its file, and write its system prompt as Markdown after the closing ---. Only name and description are required." (sub-agents: Frontmatter reference)
- `description 필드` — `원문 확인` — "When Claude should delegate to this subagent" (sub-agents: Frontmatter reference)
- `tools 필드` — `원문 확인` — "Inherits every tool available to subagents if omitted." (sub-agents: Frontmatter reference)
- `tools 필드 형식` — `원문 확인` — "as a comma-separated string such as Read, Grep, Bash or a YAML list." (sub-agents: Frontmatter reference)
- `model 필드` — `원문 확인` — "When you omit it, Claude Code picks the model in the subagent model order" (sub-agents: Frontmatter reference)
- `프로젝트 위치` — `원문 확인` — "Project subagents are discovered by walking up from the current working directory, so every .claude/agents/ between there and the repository root is scanned." (sub-agents: Choose the subagent scope)
- `오타난 필드는 조용히 무시된다` — `원문 확인` — "Claude Code ignores a field it doesn't recognize without reporting an error." (sub-agents: Frontmatter reference)
- 2.1.318 확인: `claude --help`에 `--agents <json-or-file>`("JSON object defining custom agents")이 있다. `claude agents`는 서브에이전트가 아니라 백그라운드 에이전트(agent view) 관리 명령이다(`claude agents --help`: "Manage background agents").
- 수업에 쓸 점: `tools`를 줄이면 권한 없는 일꾼이 만들어지고, `description`이 위임 시점을 정한다. 지침(역할 범위)과 실행 제어(도구 한정) 책임이 한 파일에 같이 적힌다.
- 주의: 프로젝트 위치는 `.claude/agents/`, 개인 위치는 `~/.claude/agents/`다(Choose the subagent scope 절). 필드명이 틀려도 오류가 나지 않으므로 수강생이 `tools:`를 `tool:`로 쓰면 제한 없이 도는 일꾼이 된다. 위 `/agents` 명령은 위치 안내만 출력한다(agents 쪽 문서).

## X3 서브에이전트의 별도 컨텍스트와 돌아오는 것

- 공식 문서: https://code.claude.com/docs/en/sub-agents.md (한국어: https://code.claude.com/docs/ko/sub-agents.md)
- `별도 컨텍스트 창` — `원문 확인` — "Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions." (sub-agents: Create custom subagents)
- `요약만 돌아온다` — `원문 확인` — "the subagent does that work in its own context and returns only the summary." (sub-agents: Create custom subagents)
- `큰 출력은 서브에이전트 안에 남는다` — `원문 확인` — "By delegating these to a subagent, the verbose output stays in the subagent's context while only the relevant summary returns to your main conversation." (sub-agents: Isolate high-volume operations)
- 2.1.318 확인: 대화형 전용이라 미확인(서브에이전트 실행은 모델 호출이 필요해 실행하지 않았다).
- 수업에 쓸 점: 메인 대화의 컨텍스트가 로그로 넘치는 실패를 막는다. 반대로 요약만 돌아오므로 검증 근거가 요약 문장으로 줄어드는 위험이 있다(검증·기록 책임).
- 주의: "서브에이전트는 독립"이라는 말은 컨텍스트 기준이다. 권한은 부모 규칙을 물려받고(X1), 한도는 같은 사용량이다(X4).

## X4 서브에이전트의 비용과 중첩 깊이

- 공식 문서: https://code.claude.com/docs/en/sub-agents.md (한국어: https://code.claude.com/docs/ko/sub-agents.md)
- `요청이 같은 사용량 한도에 잡힌다` — `원문 확인` — "It also sends its own requests, which count toward the same usage limits as your main conversation." (sub-agents: Create custom subagents)
- `많이 돌리면 컨텍스트와 토큰이 는다` — `원문 확인` — "Running many subagents that each return detailed results can consume significant context, and each subagent spends tokens of its own while it runs." (sub-agents: Run parallel research)
- `중첩 깊이` — `원문 확인` — "By default, a subagent can spawn subagents of its own, up to three layers below the main conversation." (sub-agents: Let subagents spawn their own subagents)
- `경량 모델로 라우팅` — `원문 확인` — "Control costs by routing tasks to faster, lower-cost models like Haiku" (sub-agents: Create custom subagents)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: "에이전트를 늘리면 빨라진다"는 오해를 막는다. 비용 문장이 서브에이전트 쪽에 이미 있으므로 Part 5 비교표의 비용 칸에 쓴다.
- 주의: 문서에 수치(토큰 배수)는 없다. 중첩 한도 3단계는 기본값이라고만 적혀 있다.

## X5 Run agents in parallel: 다섯 가지 병렬 방식

- 공식 문서: https://code.claude.com/docs/en/agents.md (한국어: https://code.claude.com/docs/ko/agents.md)
- `다섯 가지 방식` — `원문 확인` — "Claude Code has five ways to work on several tasks at once" (agents: Run agents in parallel)
- `서브에이전트의 정의` — `원문 확인` — "Delegated workers inside one session that do a side task in their own context and return a summary" (agents: Run agents in parallel)
- `에이전트 팀의 정의` — `원문 확인` — "Multiple coordinated sessions with a shared task list and inter-agent messaging, managed by a lead. Experimental and disabled by default" (agents: Run agents in parallel)
- `동적 워크플로우의 정의` — `원문 확인` — "A script that runs many subagents and cross-checks their results, for work too big to coordinate one turn at a time or that needs more than a single pass" (agents: Run agents in parallel)
- `모든 방식의 일꾼은 Claude 세션이다` — `원문 확인` — "In every approach the workers are Claude sessions." (agents: Run agents in parallel)
- `독립성 질문: 누가 서로 말하는가` — `원문 확인` — "Subagents report results back to the conversation that spawned them, and agent view sessions report results only to you." (agents: Choose an approach)
- `같은 파일을 건드리면` — `원문 확인` — "Agent teams don't isolate teammates in worktrees, so partition the work so each teammate owns a different set of files." (agents: Choose an approach)
- `비용` — `원문 확인` — "Running several sessions or subagents at once multiplies token usage." (agents: Run agents in parallel)
- 2.1.318 확인: `claude agents --help`가 동작한다("Manage background agents"). `claude --help`에 `--worktree`가 있다. 프로젝트와 agent view는 이 대장의 범위 밖이고 agent view는 문서에 Research preview로 적혀 있다.
- 수업에 쓸 점: 누가 조율하는가, 일꾼끼리 말하는가, 같은 파일을 건드리는가라는 세 질문이 구조 선택표의 열이 된다. 어느 구조도 기본값이 아니라는 점이 요점이다.
- 주의: `/agents`(서브에이전트 위치 안내)와 `claude agents`(백그라운드 세션 화면)는 이름만 비슷한 다른 기능이라고 문서가 적는다. 수업에서 혼동하기 쉽다.

## X6 Worktree로 병렬 세션 실행 (--worktree, -w)

- 공식 문서: https://code.claude.com/docs/en/worktrees.md (한국어: https://code.claude.com/docs/ko/worktrees.md)
- `worktree의 정의` — `원문 확인` — "A git worktree is a separate working directory with its own files and branch, sharing the same repository history and remote as your main checkout." (worktrees: Run parallel sessions with worktrees)
- `시작 명령` — `원문 확인` — "Pass --worktree or -w with a name to create an isolated worktree and start Claude in it." (worktrees: Start Claude in a worktree)
- `두 번째 세션` — `원문 확인` — "Run the command again with a different name in another terminal to start a second isolated session." (worktrees: Start Claude in a worktree)
- `-p는 신뢰 확인을 건너뛴다` — `원문 확인` — "Non-interactive runs with -p skip the trust check, so claude -p --worktree proceeds without it." (worktrees: Start Claude in a worktree)
- `커밋이 하나 이상 있어야 한다` — `원문 확인` — "so the repository needs at least one commit first." (common-workflows: Run parallel sessions with worktrees)
- 2.1.318 확인: `claude --help`에 `-w, --worktree [name]`("Create a new git worktree for this session (optionally specify a name)")과 `--tmux`("requires --worktree")가 있다. `/EnterWorktree` 도구는 대화형이라 미확인.
- 수업에 쓸 점: 두 세션이 같은 파일을 덮어쓰는 실패를 막는다. 상태 책임에서 "무엇이 다음 세션으로 넘어가는가"를 파일 격리로 보여 준다.
- 주의: 이 저장소가 쓰는 `git worktree add`와 `--worktree` 플래그는 별개의 진입 경로다. 격리 규칙은 둘 다에 같다고 문서가 적는다(X7). 기본 경로는 `.claude/worktrees/<name>/`, 브랜치는 `worktree-<name>`이다.

## X7 Worktree가 공유하는 것과 격리하는 것

- 공식 문서: https://code.claude.com/docs/en/worktrees.md (한국어: https://code.claude.com/docs/ko/worktrees.md)
- `공유 목록의 머리말` — `원문 확인` — "A worktree gets its own files and branch, but it shares the following with the main checkout:" (worktrees: What worktrees share with the main checkout)
- `.git 공유` — `원문 확인` — "git commands in a worktree write to the main repository's shared .git directory" (worktrees: What worktrees share with the main checkout)
- `격리 검사의 한계` — `원문 확인` — "None of them tracks which files a shell command writes, so a command that writes into the main checkout without running git there, such as cp or a shell redirect, isn't refused by them." (worktrees: How Claude Code enforces isolation)
- `서브에이전트별 워크트리` — `원문 확인` — "Subagents can run in their own worktrees so parallel edits don't conflict." (worktrees: Isolate subagents with worktrees)
- `격리된 세션에서 막히는 것` — `원문 확인` — "Claude Code blocks an Edit, Write, or NotebookEdit that targets a path in the main checkout." (worktrees: How Claude Code enforces isolation)
- 2.1.318 확인: 대화형 전용이라 미확인(검사 동작은 도구 호출이 필요하다).
- 수업에 쓸 점: "격리됐으니 안전하다"는 과신을 막는다. 파일은 격리되지만 `.git`, 권한 승인, 플러그인은 공유된다. 실행 제어 책임의 경계를 정확히 말하게 한다.
- 주의: 승인 공유("Permission approvals" 항목)는 워크트리에서 한 번 누른 "don't ask again"이 다른 워크트리에도 적용된다는 뜻이다. 저장 위치가 저장소 루트를 쓰지 않는 경우(Windows 등)에는 예외가 있다.

## X8 에이전트 팀 (Agent teams)

- 공식 문서: https://code.claude.com/docs/en/agent-teams.md (한국어: https://code.claude.com/docs/ko/agent-teams.md)
- `실험 기능이며 기본 꺼짐` — `원문 확인` — "Agent teams are experimental and disabled by default." (agent-teams: Orchestrate teams of Claude Code sessions)
- `켜는 방법` — `원문 확인` — "Enable them by setting CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in your settings.json or environment." (agent-teams: Orchestrate teams of Claude Code sessions)
- `정의` — `원문 확인` — "One session acts as the team lead, coordinating work, assigning tasks, and synthesizing results. Teammates work independently, each in its own context window, and communicate directly with each other." (agent-teams: Orchestrate teams of Claude Code sessions)
- `비용 경고` — `원문 확인` — "Agent teams add coordination overhead and use significantly more tokens than a single session." (agent-teams: When to use agent teams)
- `토큰이 선형으로 는다` — `원문 확인` — "Token costs scale linearly: each teammate has its own context window and consumes tokens independently." (agent-teams: Choose an appropriate team size)
- `서브에이전트와의 비용 비교` — `원문 확인` — "Higher: each teammate is a separate Claude instance" (agent-teams: Compare with subagents)
- `같은 파일 충돌` — `원문 확인` — "Two teammates editing the same file leads to overwrites." (agent-teams: Avoid file conflicts)
- 2.1.318 확인: `--teammate-mode`는 "experimental and doesn't appear in claude --help"라고 문서가 적는다. 로컬 `claude --help`에서 `teammate`를 찾지 못했다(확인 명령 결과). 팀 동작 자체는 대화형이라 미확인.
- 수업에 쓸 점: 일꾼끼리 직접 말하는 구조는 서브에이전트보다 독립성이 높고 비용도 높다. 순차 작업이나 같은 파일 편집에는 맞지 않는다는 문서의 판단을 근거로 "쓰지 않는 선택"도 정답으로 가르친다.
- 주의: 실험 기능이므로 문서가 "known limitations around session resumption, task coordination, and shutdown behavior"를 따로 적는다. 수업 필수 실습에는 넣지 않고 시연 또는 읽기 자료로만 쓴다.

## X9 동적 워크플로우 (Dynamic workflows)

- 공식 문서: https://code.claude.com/docs/en/workflows.md (한국어: https://code.claude.com/docs/ko/workflows.md)
- `정의` — `원문 확인` — "A dynamic workflow is a JavaScript script that orchestrates many subagents at once." (workflows: Orchestrate subagents at scale with dynamic workflows)
- `계획이 코드로 이동한다` — `원문 확인` — "A workflow script holds the loop, the branching, and the intermediate results itself, so Claude's context holds only the final answer." (workflows: When to use a workflow)
- `중간 결과의 위치` — `원문 확인` — "Intermediate results stay in script variables instead of landing in Claude's context." (workflows: How a workflow runs)
- `Pro에서는 켜야 한다` — `원문 확인` — "On Pro, turn them on from the Dynamic workflows row in /config." (workflows: Orchestrate subagents at scale with dynamic workflows)
- `요청하면 그것이 옵트인이다` — `원문 확인` — "Claude treats a direct request as the same opt-in." (workflows: Ask for a workflow in your prompt)
- `실행 전 승인` — `원문 확인` — "Claude Code asks whether to allow the workflow." (workflows: Run a bundled workflow)
- `비용` — `원문 확인` — "A workflow spawns many agents, so a single run can use meaningfully more tokens than working through the same task in conversation." (workflows: Cost)
- `대형 실행 경고` — `원문 확인` — "When a workflow schedules more than 25 agents, or its projected token total passes 1.5 million, its progress line in the task panel below the input box shows a Large workflow warning." (workflows: Cost)
- 2.1.318 확인: 대화형 전용이라 미확인(`/workflows`, `ultracode`는 `--help`에 나오지 않는다). 끄는 설정 `disableWorkflows`, 환경 변수 `CLAUDE_CODE_DISABLE_WORKFLOWS=1`은 문서 기준이다.
- 수업에 쓸 점: 오케스트레이션을 Claude의 매 턴 판단이 아니라 스크립트에 넣어 재현 가능하게 만든다. 실행 제어 책임(승인)과 기록 책임(재실행)이 구조에 들어 있다. 작은 조각으로 먼저 돌려 비용을 가늠하라는 권고를 따른다.
- 주의: 비용이 가장 커질 수 있는 구조다. 한도 수치(25개, 150만 토큰)는 경고가 뜨는 기준이지 상한이 아니다. 수강생 계정에서 대형 실행을 시키지 않는다.

## X10 /goal: 완료 조건과 판정 방식

- 공식 문서: https://code.claude.com/docs/en/goal.md (한국어: https://code.claude.com/docs/ko/goal.md)
- `하는 일` — `원문 확인` — "After each turn, a model checks whether the condition holds. If the model judges it not yet met, Claude starts another turn instead of returning control to you." (goal: Keep Claude working toward a goal)
- `종료 조건 세 가지` — `원문 확인` — "The goal clears automatically once the condition is met, if the model judges the condition impossible to satisfy, or if a turn fails on an error you have to fix." (goal: Keep Claude working toward a goal)
- `평가자는 대화만 본다` — `원문 확인` — "The evaluator judges your condition against what Claude has surfaced in the conversation. It doesn't run commands or read files independently" (goal: Write an effective condition)
- `판정은 새 모델이 한다` — `원문 확인` — "completion is decided by a fresh model rather than the one doing the work." (goal: Compare ways to keep a session running)
- `조건에 반복 상한을 넣는다` — `원문 확인` — "To bound how long a goal runs, include a turn or time clause in the condition, such as or stop after 20 turns." (goal: Write an effective condition)
- `평가 비용` — `원문 확인` — "Evaluation tokens are billed on the small fast model configured for your provider and are typically negligible compared to main-turn spend." (goal: Evaluation model and cost)
- `신뢰 규칙` — `원문 확인` — "Claude Code makes /goal available under the same workspace trust rule as hooks in settings files, because the evaluator is part of the hooks system." (goal: Requirements)
- 2.1.318 확인: 대화형 전용이라 미확인(`/goal`은 슬래시 명령이고 `--help`에 없다). 문서는 `claude -p "/goal <조건>"`으로 비대화형 실행도 된다고 적는다. 실행하면 모델을 호출하므로 하지 않았다.
- 수업에 쓸 점: "끝났다"를 만든 모델이 아니라 다른 모델이 판정하게 해서 자기 평가 편향을 줄인다. 검증 책임을 완료 조건 문장으로 쓰는 연습이 된다. 단 평가자는 도구를 부르지 않으므로 증거를 대화에 보여 주는 조건이어야 한다.
- 주의: 완료 판정은 코드 검사가 아니라 모델 판정이다. 같은 페이지가 Stop hook은 "deterministic checks"용 스크립트를 돌릴 수 있다고 비교한다. 수업에서 둘을 구분한다.

## X11 headless -p: 출력 형식, 세션 이어가기, 비용 보고

- 공식 문서: https://code.claude.com/docs/en/headless.md (한국어: https://code.claude.com/docs/ko/headless.md)
- `기본형` — `원문 확인` — "claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"" (headless: Run Claude Code programmatically)
- `text 형식` — `원문 확인` — "text (default): plain text output" (headless: Get structured output)
- `json 형식` — `원문 확인` — "json: structured JSON with result, session ID, and metadata" (headless: Get structured output)
- `stream-json 형식` — `원문 확인` — "stream-json: newline-delimited JSON for real-time streaming" (headless: Get structured output)
- `최근 대화 이어가기` — `원문 확인` — "Use --continue to continue the most recent conversation, or --resume with a session ID to continue a specific conversation." (headless: Continue conversations)
- `json 출력의 비용 필드` — `원문 확인` — "With --output-format json, the response payload includes total_cost_usd and a per-model cost breakdown" (headless: Pipe data through Claude)
- 2.1.318 확인: `claude --help`가 `--output-format <format>`을 "only works with --print"로 보이며 선택지는 text(기본), json, stream-json이다. `-c, --continue`, `-r, --resume`, `--max-budget-usd`도 목록에 있다. 이 대장에서는 `-p`를 실행하지 않았다.
- 수업에 쓸 점: 결과를 사람이 읽는 글이 아니라 json의 `result`, `session_id`, 비용으로 받으면 기록 책임(무엇이 얼마에 일어났나)을 남길 수 있다. `--resume <session_id>`는 상태 책임(다음 세션이 이어받는 것)의 가장 단순한 예다.
- 주의: 문서 예시는 파일 `auth.py`를 쓴다. 수업 자료에서는 수강생 폴더의 파일로 바꾼다. `-p`는 모델을 호출하므로 비용이 든다.

## X12 headless -p의 권한: --allowedTools, --permission-mode

- 공식 문서: https://code.claude.com/docs/en/headless.md (한국어: https://code.claude.com/docs/ko/headless.md)
- `allowedTools의 역할` — `원문 확인` — "Use --allowedTools to let Claude use certain tools without prompting." (headless: Auto-approve tools)
- `승인이 필요한 호출은 거부된다` — `원문 확인` — "In a Manual mode claude -p run, a call that needs approval is denied unless something approves it" (headless: Auto-approve tools)
- `기본 모드(버전 조건)` — `원문 확인` — "With Claude Code v2.1.302 or later, claude -p runs start in Manual mode when nothing sets a permission mode." (headless: Auto-approve tools)
- `모드로 기준선 설정` — `원문 확인` — "To set a baseline for the whole session instead of listing individual tools, pass a permission mode with --permission-mode, such as auto, dontAsk, or acceptEdits:" (headless: Auto-approve tools)
- `--permission-prompts none` — `원문 확인` — "Anything that would prompt is denied unless a PermissionRequest hook allows it" (headless: Turn off permission prompts in unattended runs)
- `규칙 문법` — `원문 확인` — "The --allowedTools flag uses permission rule syntax." (headless: Create a commit)
- 2.1.318 확인: `claude --help`의 `--permission-mode` 선택지는 acceptEdits, auto, bypassPermissions, manual, dontAsk, plan이고, `--permission-prompts <target>`은 "host" 또는 "none"(--print와 함께)이다. `--allowedTools`와 `--disallowedTools`도 있다.
- 수업에 쓸 점: 물어볼 사람이 없는 실행에서 어떤 호출이 허용되고 어떤 호출이 거부되는지를 목록으로 정하게 한다. 실행 제어 책임(허용, 승인, 중지)을 가장 직접 보여 주는 장면이다. 필요한 도구만 `Bash(git diff *)`처럼 접두사로 허용한다.
- 주의: 로컬 2.1.318은 v2.1.302 이상이므로 문서의 Manual 시작 규칙이 적용된다. 위 `--allowedTools` 접두사 규칙은 공백 위치(`Bash(git diff *)`와 `Bash(git diff*)`)가 다르게 동작한다고 문서가 따로 경고한다.

## X13 headless -p와 신뢰하지 않은 폴더, --bare

- 공식 문서: https://code.claude.com/docs/en/headless.md (한국어: https://code.claude.com/docs/ko/headless.md)
- `신뢰 대화상자가 없다` — `원문 확인` — "A -p session shows no workspace trust dialog and no per-server approval prompt." (headless: Start faster with bare mode)
- `신뢰하지 않은 폴더에서도 hooks와 MCP가 돈다` — `원문 확인` — "Without --bare, a -p session runs the hooks in a project's .claude/settings.json and connects the servers in its .mcp.json, even in a folder you've never trusted." (headless: Start faster with bare mode)
- `--bare의 효과` — `원문 확인` — "Add --bare to reduce startup time by skipping auto-discovery of hooks, skills, custom commands, subagents, installed plugins, MCP servers, auto memory, and CLAUDE.md." (headless: Start faster with bare mode)
- `--bare 권장` — `원문 확인` — "--bare is the recommended mode for scripted and SDK calls, and will become the default for -p in a future release." (headless: Start faster with bare mode)
- 2.1.318 확인: `claude --help`에 `--bare`("Minimal mode: skip hooks ...")가 있다. 실제 `-p` 실행은 하지 않았다.
- 수업에 쓸 점: 낯선 저장소를 `-p`로 열면 그 저장소의 hooks가 확인 없이 실행될 수 있다는 점은 실행 제어 책임의 경계다. 남이 준 폴더를 분석하는 수업 장면에서 `--bare`를 먼저 말한다.
- 주의: `--bare`는 CLAUDE.md와 skills도 건너뛴다. 수강생 실습 폴더의 CLAUDE.md 가이드가 읽히지 않으므로 `--bare`와 가이드 문서 방식은 함께 쓸 수 없다. 문서는 v2.1.286 이전에는 이 제한이 부분적이었다고 적는다.

## X14 common-workflows: 계획 모드, 조사 위임

- 공식 문서: https://code.claude.com/docs/en/common-workflows.md (한국어: https://code.claude.com/docs/ko/common-workflows.md)
- `plan mode의 효과` — `원문 확인` — "For changes you want to review before they touch disk, switch to plan mode. Claude reads files and proposes a plan but makes no edits until you approve." (common-workflows: Plan before editing)
- `plan mode 시작` — `원문 확인` — "You can also press Shift+Tab mid-session until the status bar shows ⏸ plan mode on." (common-workflows: Plan before editing)
- `조사 위임` — `원문 확인` — "Exploring a large codebase fills your context with file reads. Delegate the exploration so only the findings come back." (common-workflows: Delegate research to subagents)
- `서브에이전트가 요약을 돌려준다` — `원문 확인` — "The subagent reads files in its own context window and reports a summary." (common-workflows: Delegate research to subagents)
- `병렬 세션 안내` — `원문 확인` — "Work on a feature in one terminal while Claude fixes a bug in another, without the edits colliding." (common-workflows: Run parallel sessions with worktrees)
- 2.1.318 확인: `claude --help`의 `--permission-mode` 선택지에 plan이 있다(위 X12). plan mode 화면과 Shift+Tab은 대화형 전용이라 미확인.
- 수업에 쓸 점: 탐색, 계획, 구현, 커밋의 순서를 지키려면 계획 승인 전 편집이 막혀야 한다. 지침(목표, 범위)을 승인 가능한 문서로 바꾸는 단계가 plan mode다.
- 주의: 미확인 — "explore, plan, implement, commit"라는 이름의 네 단계 패턴은 이 8쪽 중 common-workflows에서 찾지 못했다. 이 쪽에는 `Plan before editing`, `Delegate research to subagents`, `Create pull requests` 절이 따로 있을 뿐이다. 그 4단계 표현이 필요하면 best-practices 쪽을 다른 노드에서 대조해야 한다.

## X15 /batch와 포크: 서브에이전트를 묶는 변형

- 공식 문서: https://code.claude.com/docs/en/agents.md (한국어: https://code.claude.com/docs/ko/agents.md)
- `/batch` — `원문 확인` — "is a skill that has Claude split one large change into 5 to 30 worktree-isolated subagents." (agents: Run agents in parallel)
- `포크한 서브에이전트` — `원문 확인` — "A forked subagent is a subagent that inherits your full conversation context instead of starting fresh." (agents: Run agents in parallel)
- `백그라운드 bash는 에이전트가 아니다` — `원문 확인` — "A background bash command runs one shell command without blocking the conversation. It doesn't spawn an agent." (agents: Run agents in parallel)
- 2.1.318 확인: 대화형 전용이라 미확인(`/batch`, `/subtask`, `/fork`는 슬래시 명령).
- 수업에 쓸 점: `/batch`는 별도 조율 방식이 아니라 서브에이전트와 워크트리의 묶음 사용이라는 문서의 정리를 따라, 구조를 새로 늘리지 않고 조합으로 설명한다.
- 주의: `/batch`를 "5 to 30"으로 돌리면 비용이 커진다. 시연은 작은 변경에만 한다.

## X16 구조 비교: 누가 다음에 할 일을 정하는가

- 공식 문서: https://code.claude.com/docs/en/workflows.md (한국어: https://code.claude.com/docs/ko/workflows.md)
- `서브에이전트와 워크플로우의 조율자` — `원문 확인` — "With subagents, skills, and agent teams, Claude is the orchestrator: it decides turn by turn what to spawn or assign next, and every result goes into a context window." (workflows: When to use a workflow)
- `독립 에이전트의 교차 검토` — `원문 확인` — "it can have independent agents adversarially review each other's findings before they're reported" (workflows: When to use a workflow)
- `규모` — `원문 확인` — "Dozens to hundreds of agents per run" (workflows: When to use a workflow)
- `팀 쪽의 같은 구분` — `원문 확인` — "Agent teams are most effective for tasks where parallel exploration adds real value." (agent-teams: When to use agent teams)
- 2.1.318 확인: 해당 없음.
- 수업에 쓸 점: Part 5의 독립성 대 비용 비교표를 만들 때 "누가 다음 일을 정하는가"와 "중간 결과가 어디에 사는가"라는 문서 자신의 비교 축을 그대로 쓴다. 실행 구조를 기능 이름이 아니라 책임 배치로 비교하게 한다.
- 주의: 이 비교표는 workflows 쪽 문서의 자기 소개이므로 workflows에 유리한 서술일 수 있다. 수업에서는 비용(X4, X8, X9) 문장과 같이 읽힌다.

## 수업에 쓸 때 주의

- 이 대장의 구조들은 모두 "독립성이 늘수록 비용이 는다"는 한 축에 놓인다. 서브에이전트(요약만 돌아옴), 워크트리(파일만 격리), 에이전트 팀(별도 인스턴스), 동적 워크플로우(수십~수백 에이전트) 순서로 비용 문장이 강해진다. 비용은 수업에서 표로 비교하되 숫자는 문서에 없으므로 적지 않는다.
- 격리의 범위를 구분해서 말한다. 워크트리는 파일 편집을 격리하지만 `.git` 디렉터리, 플러그인, 권한 승인(`.claude/settings.local.json`)은 공유한다. `cp`나 셸 리다이렉트는 격리 검사가 막지 않는다고 문서가 적는다(X7).
- `/goal`의 평가자는 도구를 부르지 않고 대화에 드러난 내용만 본다. 그래서 완료 조건은 "Claude의 출력으로 보여줄 수 있는 것"이어야 한다. 검증 책임이 코드 검사가 아니라 모델 판정이라는 점을 수강생에게 분명히 한다(X10).
- `claude -p`는 신뢰 대화상자가 없고, `--bare` 없이는 프로젝트 hooks와 `.mcp.json`이 신뢰하지 않은 폴더에서도 돈다. 수강생 실습 폴더에서 `-p`를 시연하기 전에 이 문장을 먼저 읽힌다(X13).
- 에이전트 팀은 실험 기능이고 기본 꺼짐이며 `--teammate-mode`는 `--help`에 없다. 대화형 전용 기능(`/goal`, `/workflows`, `/agents`, 팀)은 이 대장에서 로컬 `--help`로 확인하지 못했다. 시연 전에 직접 켜 보고 동작을 확인한다.
- 문서는 계속 바뀐다. 모델 이름, 버전 조건(v2.1.302 등), 기본 모델은 수업 직전에 다시 대조한다.


Quotes verified: 87/87