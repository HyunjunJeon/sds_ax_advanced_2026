# Claude Code 근거 대장 — 도구 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: 각 페이지의 `.md` 판을 `curl -sL https://code.claude.com/docs/en/<page>.md`로 내려받고, `python3 -I` 스크립트로 마크다운 링크 `[text](url)`를 text로 바꾸고 백틱·`**` 표시를 지우고 공백을 합친 뒤 인용문이 부분 문자열인지 대조했다. WebFetch(요약 모델)는 쓰지 않았다.
- 사용한 페이지: `tools-reference`, `mcp`, `plugins/overview`, `plugins/components`, `plugins/manifest-reference`, `plugins/security` (모두 `https://code.claude.com/docs/en/` 아래). 한국어 주소는 `https://code.claude.com/docs/_llms/ko.txt` 목록에 있는 것만 적었고 한국어 문장은 인용하지 않았다.
- `원문 확인`은 대조를 통과한 인용문에만 붙였다. `claude --version`은 2.1.318이고, 로컬 확인은 모델을 부르지 않는 `--help`만 썼다(`claude mcp --help`, `claude mcp add --help`, `claude plugin --help`, `claude plugin details --help`, `claude --help`). MCP 서버·플러그인은 추가·설치·삭제하지 않았다.
- 인용 뒤 괄호는 원문의 절 제목이다. 문서는 계속 바뀌므로 2026-11-06 기준이다.

## T1 내장 도구 목록과 권한 필요 여부

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `내장 도구의 정의` — `원문 확인` — "Claude Code has access to a set of built-in tools that help it understand and modify your codebase." (Tools reference)
- `읽기 도구` — `원문 확인` — "Reads the contents of files." (Tools reference › 표의 Read 행). 표의 "Permission required" 열이 `No`다.
- `쓰기·편집·실행 도구` — `원문 확인` — "Makes targeted edits to specific files." (Edit 행) / "Creates or overwrites files." (Write 행) / "Executes shell commands in your environment." (Bash 행). 세 행 모두 "Permission required" 열이 `Yes`다.
- `자동 모드에서는 표가 달라진다` — `원문 확인` — "In auto mode, a classifier decides most permission prompts instead of you." (Tools reference › 도입부 NOTE)
- 2.1.318 확인: `claude --help`에 `--allowedTools`, `--add-dir` 등 도구·권한 플래그가 있음을 확인했다. 도구 표 자체는 대화형 세션에서 쓰는 이름이라 로컬에서 목록을 뽑지 못했다(대화형 전용이라 미확인).
- 수업에 쓸 점: Read는 묻지 않고 Edit·Write·Bash는 묻는다는 구분이 "관찰은 자유, 변경은 승인"이라는 도구와 실행 제어의 경계다. 막으면 실수로 바뀌는 파일을 막는다. 책임: 도구.
- 주의: 표는 모델·플랫폼에 따라 달라진다(Glob·Grep은 기본 제외, Task 계열은 모델별). 수업 중 "도구 N개"처럼 숫자로 못 박지 않는다.

## T2 도구 이름은 권한 규칙의 키다

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `규칙 형식` — `원문 확인` — "All of these accept the same rule format, ToolName(specifier)." (Tools reference › Configure tools with permission rules and hooks)
- `도구 이름이 쓰이는 곳` — `원문 확인` — "in the --allowedTools and --disallowedTools CLI flags" (Tools reference › Configure tools with permission rules and hooks)
- 2.1.318 확인: `claude --help`에 `--allowedTools, --allowed-tools <tools...>`가 있다(로컬 확인).
- 수업에 쓸 점: 같은 도구 이름이 settings의 allow·deny, CLI 플래그, 스킬의 `allowed-tools`, 훅의 `if`에서 모두 쓰인다는 점을 보여 주면 도구와 실행 제어가 같은 이름으로 이어진다. 책임: 도구, 실행 제어.
- 주의: 이름은 대소문자까지 정확한 문자열이다. 규칙 문법의 세부(`Bash(...)` 패턴 등)는 이 페이지가 아니라 permissions 페이지 몫이며 이 대장에서 확인하지 않았다.

## T3 Glob·Grep은 macOS·Linux에서 기본 도구가 아니다

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `기본 목록에서 빠진다` — `원문 확인` — "On macOS, Linux, and WSL, Claude Code leaves Glob and Grep out of the default tool set, and Claude searches with find and grep through the Bash tool instead." (Tools reference › Glob tool behavior)
- `다시 켜는 방법` — `원문 확인` — "You name Glob or Grep in --tools or --allowedTools when you start the session" (Tools reference › Glob tool behavior)
- 2.1.318 확인: `claude --help`에 `--allowedTools`가 있고 `--tools`는 이 대장에서 따로 열어 보지 않았다(`--tools` 동작은 미확인).
- 수업에 쓸 점: 수강생 맥북에서는 "검색"이 Bash를 거치므로 Bash를 막으면 검색 도구도 사라진다. 도구 하나를 막았는데 다른 능력이 같이 사라지는 실패를 설명한다. 책임: 도구, 실행 제어.
- 주의: 같은 절은 `--restricted`나 Bash deny 규칙이 Bash를 세션에서 뺀다고 적는다. 수업 환경(macOS)과 Windows의 차이를 말할 때만 쓴다.

## T4 Bash 도구: 작업 디렉터리와 환경 변수는 어디까지 이어지나

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `명령마다 별도 프로세스` — `원문 확인` — "The Bash tool runs each command in a separate process." (Tools reference › Bash tool behavior)
- `환경 변수는 이어지지 않는다` — `원문 확인` — "Environment variables don't persist. An export in one command won't be available in the next." (Tools reference › Bash tool behavior › What persists between commands)
- `디렉터리는 프로젝트 안에서만 이어진다` — `원문 확인` — "If cd lands outside those directories, Claude Code resets to the project directory and appends Shell cwd was reset to <dir> to the tool result." (Tools reference › Bash tool behavior › What persists between commands)
- `환경 변수를 이어 주는 방법` — `원문 확인` — "To make environment variables persist across Bash commands, set CLAUDE_ENV_FILE to a shell script before launching Claude Code, or use a SessionStart hook to populate it dynamically." (Tools reference › Bash tool behavior › What persists between commands)
- 2.1.318 확인: `claude --help`에 `--add-dir <directories...>`가 있다(로컬 확인). Bash 동작 자체는 모델을 부르지 않고는 재현할 수 없어 미확인.
- 수업에 쓸 점: "export 했는데 다음 명령에서 사라진다"와 "cd 했는데 원래 폴더로 돌아온다"는 수강생이 반드시 만나는 실패다. 상태를 도구 호출 사이에 기대지 말고 파일·명령 한 줄에 담으라고 가르친다. 책임: 도구(상태와 맞닿음).
- 주의: 서브에이전트 세션은 작업 디렉터리 변경이 이어지지 않는다고 같은 절이 적는다. `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1`로 끌 수 있다.

## T5 Bash 도구: 시간 제한과 출력 한도

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `기본 시간 제한` — `원문 확인` — "BASH_DEFAULT_TIMEOUT_MS — the default when Claude passes no timeout; two minutes out of the box" (Tools reference › Bash tool behavior › Timeout and output limits)
- `상한` — `원문 확인` — "BASH_MAX_TIMEOUT_MS — with the default, sets the ceiling that caps whatever Claude requests: the effective ceiling is the larger of the two, ten minutes out of the box" (Tools reference › Bash tool behavior › Timeout and output limits)
- `시간 초과 시 중단이 아니라 백그라운드로 옮긴다` — `원문 확인` — "When a foreground command reaches its timeout without finishing, Claude Code moves it to the background instead of stopping it, unless the command starts with sleep." (Tools reference › Bash tool behavior › Foreground commands that move to the background)
- `출력 한도` — `원문 확인` — "Inline up to roughly 30,000 characters by default" (Tools reference › Bash tool behavior › Output limits, 표의 Valid 행) / "Inline up to roughly 10,000 characters" (같은 표의 Failure 행)
- `비대화형·무인 실행의 백그라운드 제한` — `원문 확인` — "A local session you work in from a terminal, the desktop app, or the VS Code extension has no time limit on background commands." (Tools reference › Bash tool behavior › Time limit for background commands)
- 2.1.318 확인: 대화형 전용이라 미확인(환경 변수 동작은 `claude --help`에 나오지 않는다).
- 수업에 쓸 점: 긴 테스트 로그를 읽는 에이전트가 앞부분만 보고 결론 내리는 실패(출력 잘림)와, 2분 넘는 명령이 조용히 백그라운드로 가서 "끝났다"고 착각하는 실패를 설명한다. 책임: 도구, 검증.
- 주의: 실패한 명령의 인라인 한도(약 10,000자)가 성공 때(약 30,000자)보다 작다. 백그라운드 시간 제한은 v2.1.285 이상 문서이며 `-p` 실행에서만 걸린다고 적혀 있다.

## T6 Read 도구의 한도

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `디렉터리는 못 읽는다` — `원문 확인` — "Read only reads files, not directories." (Tools reference › Read tool behavior)
- `큰 파일` — `원문 확인` — "refuses a whole file over 256 KB, so Claude reads a larger file in pages with offset and limit." (Tools reference › Read tool behavior › Large files)
- 2.1.318 확인: 해당 없음(도구 내부 한도라 --help에 나오지 않음).
- 수업에 쓸 점: 큰 로그나 세션 기록(JSONL)을 통째로 읽으려다 실패하거나 일부만 보고 판단하는 실패를 막는다. 세션 기록 진단 실습에서 "어디까지 읽었나"를 확인하는 근거다. 책임: 도구, 기록.
- 주의: 같은 절에 v2.1.296 이후 전체 읽기가 가능해지는 조건이 있으나(문장 일부만 확인) 이 대장은 그 조건을 인용하지 않았다.

## T7 서브에이전트가 쓸 수 있는 도구

- 공식 문서: https://code.claude.com/docs/en/tools-reference (한국어: https://code.claude.com/docs/ko/tools-reference.md)
- `충돌 규칙` — `원문 확인` — "Both set: disallowedTools takes precedence. A tool listed in both is removed." (Tools reference › Agent tool behavior)
- `실행 시점에 검사한다` — `원문 확인` — "Launching the subagent doesn't itself prompt for permission. Claude Code checks the subagent's own tool calls against your permission rules as it runs." (Tools reference › Agent tool behavior)
- `제한 방법` — `원문 확인` — "To limit what a subagent can reach in the first place, narrow its tools field, for example by leaving Bash off the list, or set deny rules in your settings." (Tools reference › Agent tool behavior)
- 2.1.318 확인: `claude --help`에 `--agents` 관련 옵션이 있음을 확인했을 뿐 서브에이전트 실행은 하지 않았다(대화형 전용이라 미확인).
- 수업에 쓸 점: 서브에이전트를 만들고 도구를 안 좁히면 부모와 같은 도구를 물려받는다. 읽기 전용 검토자에게 Bash를 남겨 두는 실수를 막는다. 책임: 도구, 실행 제어.
- 주의: 백그라운드 서브에이전트의 권한 질문은 메인 세션에 뜨고 Esc가 그 호출 하나만 거부한다고 같은 절에 적혀 있다.

## T8 MCP 설치 범위 세 가지와 저장 위치

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `세 범위` — `원문 확인` — "MCP servers can be configured at three scopes." (MCP installation scopes)
- `local은 기본값이고 ~/.claude.json에 저장` — `원문 확인` — "Local scope is the default." (MCP installation scopes › Local scope) / "Claude Code stores it in ~/.claude.json under that project's path, so the same server won't appear in your other projects." (Local scope)
- `project는 .mcp.json` — `원문 확인` — "Project-scoped servers enable team collaboration by storing configurations in a .mcp.json file at your project's root directory." (MCP installation scopes › Project scope)
- `user는 모든 프로젝트` — `원문 확인` — "User-scoped servers are stored in ~/.claude.json and provide cross-project accessibility" (MCP installation scopes › User scope)
- `이름이 같은 다른 설정` — `원문 확인` — "MCP local-scoped servers are stored in ~/.claude.json (your home directory), while general local settings use .claude/settings.local.json (in the project directory)." (MCP installation scopes › Local scope › NOTE)
- 2.1.318 확인: `claude mcp add --help`에 `-s, --scope <scope>  Configuration scope (local, user, or project)`가 있다(로컬 확인).
- 수업에 쓸 점: "내 컴퓨터에서는 되는데 팀원은 안 된다"는 실패는 서버를 local에 넣고 project에 안 넣었을 때 생긴다. 반대로 키가 든 서버를 project(.mcp.json, 버전 관리)에 넣으면 키가 새는 실패가 난다. 책임: 도구, 실행 제어.
- 주의: MCP의 local 범위(`~/.claude.json`)와 일반 설정의 `settings.local.json`은 다른 파일이다. 실습에서 `~/.claude.json` 내용은 열지 않는다(키·세션 정보가 있을 수 있음).

## T9 같은 서버가 여러 범위에 있을 때의 우선순위

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `하나만 연결` — `원문 확인` — "When the same server is defined in more than one place, Claude Code connects to it once, using the definition from the highest-precedence source." (MCP installation scopes › Scope hierarchy and precedence)
- `병합하지 않는다` — `원문 확인` — "The entire server entry from that source is used; fields are not merged across scopes." (MCP installation scopes › Scope hierarchy and precedence)
- 2.1.318 확인: `claude mcp list` / `claude mcp get`가 설정을 읽는 명령임은 `claude mcp --help`로 확인했다. 실제 실행은 서버 연결을 시도할 수 있어 하지 않았다(미확인).
- 수업에 쓸 점: project의 서버 설정을 고쳤는데 local에 같은 이름이 있어 반영되지 않는 실패를 설명한다. 순서는 local, project, user, 플러그인, claude.ai 커넥터다. 책임: 도구.
- 주의: 순서 목록(1~5)은 번호 목록이라 인용하지 않고 문서의 순서를 요약했다. 이름이 같을 때만 중복으로 본다.

## T10 프로젝트 `.mcp.json` 서버의 승인

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `대화형에서는 승인을 묻는다` — `원문 확인` — "For security reasons, Claude Code prompts for approval in interactive sessions before using project-scoped servers from .mcp.json files." (MCP installation scopes › Project scope)
- `승인 초기화` — `원문 확인` — "To reset those approval choices, run claude mcp reset-project-choices." (MCP installation scopes › Project scope)
- `비대화형에서는 묻지 않고 불러온다` — `원문 확인` — "Claude Code can't show that prompt: it loads project-scoped servers without asking." (MCP installation scopes › Project scope)
- `저장소가 스스로 승인할 수 없다` — `원문 확인` — "A cloned repository can't approve its own servers" (MCP › Managing your servers › Project server approvals and workspace trust)
- 2.1.318 확인: `claude mcp --help`에 `reset-project-choices`가 있고 `list`·`get`이 "Unapproved .mcp.json servers"를 보류 상태로 보여 준다고 적혀 있다(로컬 확인). 승인 대화상자 자체는 대화형 전용이라 미확인.
- 수업에 쓸 점: 남이 준 저장소의 `.mcp.json`은 승인 전에 읽어야 한다는 신뢰 경계다. 그러나 `claude -p`에서는 같은 서버가 묻지 않고 로드되므로, 비대화형 자동화에서 승인 절차가 사라지는 실패를 설명한다. 책임: 실행 제어, 도구.
- 주의: 문서는 `--strict-mcp-config`와 `disabledMcpjsonServers`로 막는 방법을 적는다. 이 대장은 그 옵션을 실행해 보지 않았다.

## T11 MCP 도구 이름과 128자 한도

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `이름 형태` — `원문 확인` — "Run /mcp in your session and select the tool to see its full name, such as mcp__<server>__<tool>." (MCP › Tools with names longer than 128 characters)
- `128자 초과 도구는 빠진다` — `원문 확인` — "Claude Code leaves an MCP tool out of the tools it sends to Claude when its full name is over 128 characters." (MCP › Tools with names longer than 128 characters)
- 2.1.318 확인: 대화형 전용이라 미확인(`/mcp` 패널).
- 수업에 쓸 점: 권한 규칙·훅 matcher·스킬 `allowed-tools`에 `mcp__<server>__<tool>` 이름을 정확히 써야 한다. 이름이 틀리면 규칙이 조용히 안 걸리는 실패가 난다. 책임: 도구, 실행 제어.
- 주의: 서버 이름이 길면 도구가 목록에서 사라져 "도구가 없다"로 보인다. 플러그인 서버는 이름 형태가 다르다(T18).

## T12 MCP 도구 검색(지연 로딩)

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `지연 로딩의 이유` — `원문 확인` — "Tool search keeps MCP context usage low by deferring tool definitions until Claude needs them." (MCP › Scale with MCP tool search)
- `시작 때 올라가는 것` — `원문 확인` — "Only tool names and server instructions load at session start, so adding more MCP servers has minimal impact on your context window." (MCP › Scale with MCP tool search)
- `기본값` — `원문 확인` — "Tool search is enabled by default: MCP tools are deferred and discovered on demand." (MCP › Scale with MCP tool search › Configure tool search)
- `서버 연결이 늦을 때` — `원문 확인` — "With tool search, the default: the wait happens inside the ToolSearch call." (MCP › Managing your servers › Tool availability)
- 2.1.318 확인: 대화형 전용이라 미확인(`ENABLE_TOOL_SEARCH`는 `--help`에 나오지 않는다).
- 수업에 쓸 점: MCP 서버를 많이 붙여도 컨텍스트가 바로 차지 않는 이유와, 반대로 도구가 "처음에는 이름만 보이는" 상태라는 점을 설명한다. 도구 설명이 부실하면 검색에서 못 찾는 실패가 난다. 책임: 도구, 상태.
- 주의: 이 도구 검색은 이전 모델에서는 꺼지고 모든 MCP 도구를 미리 올린다고 문서가 적는다. 수강생 모델에 따라 동작이 다를 수 있다.

## T13 MCP 출력 한도와 시간 제한

- 공식 문서: https://code.claude.com/docs/en/mcp (한국어: https://code.claude.com/docs/ko/mcp.md)
- `토큰 한도` — `원문 확인` — "Claude Code displays a warning when MCP tool output exceeds 10,000 tokens and limits output to 25,000 tokens by default." (MCP › Push messages with channels › Tips. 원문 구조상 이 절 밑에 붙어 있다)
- `파일로 저장` — `원문 확인` — "Unless the server raises a tool's own limit, successful text results longer than 50,000 characters are saved to a file regardless of this variable." (MCP › Push messages with channels › Tips)
- `서버 시작 시간 제한` — `원문 확인` — "Configure MCP server startup timeout using the MCP_TIMEOUT environment variable" (MCP › Push messages with channels › Tips)
- 2.1.318 확인: 해당 없음(환경 변수는 `--help`에 나오지 않는다).
- 수업에 쓸 점: MCP 도구가 긴 결과를 돌려줄 때 모델이 잘린 일부만 보고 답하는 실패를 설명한다. 도구 결과의 한도는 도구마다 다르다(Bash 약 3만 자, MCP 기본 25,000 토큰). 책임: 도구, 검증.
- 주의: 출력 한도 절 제목은 "MCP output limits and warnings"이며 그 절에서도 `MAX_MCP_OUTPUT_TOKENS`를 설명한다. 인용문 둘은 위치 때문에 위 절 제목으로 적었다.

## T14 플러그인이란 무엇이고 어떤 구성요소를 담는가

- 공식 문서: https://code.claude.com/docs/en/plugins/overview (한국어: https://code.claude.com/docs/ko/plugins/overview.md)
- `정의` — `원문 확인` — "A Claude Code plugin is a directory of skills, agents, hooks, MCP servers, or other components that Claude Code installs and loads as one unit." (Plugins overview)
- `설정과 달리 항상 켜진다` — `원문 확인` — "An enabled plugin is part of every session, not only the sessions where you use it." (Plugins overview › What an enabled plugin adds to your sessions)
- `패키지가 필요한 때` — `원문 확인` — "Use a plugin when you want several skills, subagents, hooks, or MCP servers packaged as one unit." (Plugins overview › Decide whether you need a plugin)
- 2.1.318 확인: `claude plugin --help`에 `install`, `list`, `details`, `validate`, `enable`, `disable`이 있다(로컬 확인). 설치는 하지 않았다.
- 수업에 쓸 점: 지침(스킬)·도구(MCP)·실행 제어(훅)를 한 묶음으로 배포하는 단위가 플러그인이다. 개별 설정과 달리 모든 세션에 컨텍스트 비용이 든다는 점도 같이 가르친다. 책임: 도구(지침·실행 제어에 걸침).
- 주의: 같은 페이지는 "hooks module"(mod)도 구성요소로 적는다. 수업에서 다룰지는 저자가 정한다.

## T15 매니페스트 위치와 표준 디렉터리 구조

- 공식 문서: https://code.claude.com/docs/en/plugins/manifest-reference (한국어: https://code.claude.com/docs/ko/plugins/manifest-reference.md)
- `선택 사항` — `원문 확인` — "The manifest is optional." (Plugin manifest reference › Manifest file)
- `위치` — `원문 확인` — "Save the manifest at .claude-plugin/plugin.json under the plugin root. Put every other plugin file at the plugin root, not inside .claude-plugin/." (Plugin manifest reference › Manifest file)
- `CLAUDE.md는 읽지 않는다` — `원문 확인` — "A CLAUDE.md at the plugin root isn't loaded as context, and claude plugin validate warns when it finds one." (Plugin manifest reference › Standard layout)
- `검증 명령` — `원문 확인` — "To check the component's file before loading it, run claude plugin validate . in your shell from the plugin directory." (Add components to a plugin; 같은 문서 components 페이지 도입부)
- 2.1.318 확인: `claude plugin --help`에 `validate [options] <path>  Validate a plugin or marketplace`가 있다(로컬 확인). 실행은 하지 않았다.
- 수업에 쓸 점: 가장 흔한 실패는 `skills/`·`hooks/`를 `.claude-plugin/` 안에 넣는 것과 플러그인 루트의 CLAUDE.md가 지침으로 로드된다고 믿는 것이다. 지침은 스킬로 써야 한다. 책임: 지침, 도구.
- 주의: 표준 위치는 표로 정리돼 있다(skills/, commands/, agents/, hooks/hooks.json, .mcp.json, .lsp.json, bin/ 등). 표 셀은 인용하지 않고 요약했다. 마지막 인용문의 출처는 components 페이지다.

## T16 플러그인 스킬의 이름 붙이기

- 공식 문서: https://code.claude.com/docs/en/plugins/components (한국어: https://code.claude.com/docs/ko/plugins/components.md)
- `명령 이름 규칙` — `원문 확인` — "Command name: /<plugin>:<directory>, so skills/review/SKILL.md in my-plugin is /my-plugin:review." (Add components to a plugin › Add each kind of component › Skills)
- `지침은 스킬로` — `원문 확인` — "To include instructions in a plugin, write them as a skill." (Add components to a plugin › Skills)
- `반드시 지켜야 하는 규칙은 훅으로` — `원문 확인` — "If a rule must hold every time, such as blocking edits to protected files, add it to the plugin as a hook rather than a skill." (Add components to a plugin › Skills)
- 2.1.318 확인: 대화형 전용이라 미확인(`/reload-plugins`, `/<plugin>:<skill>`).
- 수업에 쓸 점: 플러그인 스킬은 `/플러그인:스킬` 형태라서 같은 이름의 개인 스킬과 충돌하지 않는다. "스킬은 권고, 훅은 강제"를 공식 문서가 직접 말하는 근거다. 책임: 지침, 실행 제어.
- 주의: frontmatter에 `name`을 주면 마지막 구간이 바뀌고 플러그인 접두어는 유지된다.

## T17 플러그인 훅은 언제 로드되고 언제 도는가

- 공식 문서: https://code.claude.com/docs/en/plugins/components (한국어: https://code.claude.com/docs/ko/plugins/components.md)
- `파일 위치` — `원문 확인` — "Save the plugin's hooks in hooks/hooks.json at the plugin root, under a top-level "hooks" key, in the same shape as the hooks object in settings.json." (Add components to a plugin › Hooks)
- `스킬 사용과 무관하게 발동` — `원문 확인` — "A plugin's hooks don't wait for one of the plugin's skills or commands to be used." (Add components to a plugin › Hooks › When plugin hooks fire)
- `등록 시점` — `원문 확인` — "Claude Code registers them when a session loads the plugin, and they fire on their events from then on." (Add components to a plugin › Hooks › When plugin hooks fire)
- `두 곳 모두 로드` — `원문 확인` — "Hooks in hooks/hooks.json and in the hooks manifest key both load." (Add components to a plugin › Hooks)
- 2.1.318 확인: 대화형 전용이라 미확인. `claude --help`의 `--bare` 설명에 "skip hooks (those defined in settings and by installed plugins" 문구가 있음을 로컬에서 확인했다.
- 수업에 쓸 점: 플러그인을 켜는 순간 훅이 모든 세션에서 동작한다. 팀 규칙을 배포할 수는 있지만, 쓰는 사람이 모르는 사이에 명령이 실행되는 실패 원인이 되기도 한다. 책임: 실행 제어.
- 주의: 같은 이름의 플러그인이 둘 켜지면 한쪽의 `hooks/hooks.json` 훅이 빠진다고 문서가 적는다(어느 쪽인지는 loading 페이지 몫이며 이 대장에서 확인하지 않았다).

## T18 플러그인 MCP 서버의 로드와 이름

- 공식 문서: https://code.claude.com/docs/en/plugins/components (한국어: https://code.claude.com/docs/ko/plugins/components.md)
- `선언 위치` — `원문 확인` — "Declare it in .mcp.json at the plugin root, in the same shape as a project .mcp.json." (Add components to a plugin › MCP servers)
- `서버 이름` — `원문 확인` — "Server name: plugin:<plugin>:<server>, so the db server in my-plugin is plugin:my-plugin:db in /mcp." (Add components to a plugin › MCP servers › Server names, tool names, and reloads)
- `도구 이름` — `원문 확인` — "Tool names: mcp__plugin_<plugin>_<server>__<tool>, so a query tool on that db server is mcp__plugin_my-plugin_db__query." (Add components to a plugin › MCP servers › Server names, tool names, and reloads)
- `서버 이름만 쓴 matcher는 안 걸린다` — `원문 확인` — "A hook matcher written against the bare server key, such as mcp__database-tools__.*, never fires for a plugin-bundled server." (MCP › Plugin-provided MCP servers)
- 2.1.318 확인: 대화형 전용이라 미확인(`/mcp` 패널). `claude plugin details <name>`이 MCP 서버 목록(Component inventory)을 보여 준다고 security 문서가 적고 `claude plugin details --help`가 있음을 확인했으나 실행은 하지 않았다.
- 수업에 쓸 점: 플러그인에 든 MCP 도구에 권한 규칙이나 훅을 걸 때 `mcp__plugin_...` 전체 이름을 써야 한다. 일반 서버 이름 형태(T11)로 쓰면 규칙이 조용히 안 걸린다. 책임: 도구, 실행 제어.
- 주의: 우선순위에서 플러그인 서버는 local·project·user 아래다(T9). `${CLAUDE_PLUGIN_ROOT}`는 `command`, `args`, `env`에서 치환된다.

## T19 플러그인의 신뢰 경계와 보안 경고

- 공식 문서: https://code.claude.com/docs/en/plugins/security (한국어: https://code.claude.com/docs/ko/plugins/security.md)
- `권한` — `원문 확인` — "A plugin can carry content that runs code on your machine with your user privileges and content that enters Claude's context as instructions" (Plugin security and trust › Understand what a plugin can do)
- `권한 규칙과 샌드박스의 범위` — `원문 확인` — "Claude Code's permission rules and sandbox cover the tool calls Claude makes, not the code a plugin runs by itself" (Plugin security and trust › Understand what a plugin can do)
- `샌드박스 밖에서 실행` — `원문 확인` — "Claude Code runs hooks, monitors, MCP servers, LSP servers, and the processes a mod starts outside the sandbox." (Plugin security and trust › Understand what a plugin can do)
- `설치 전 경고 문구` — `원문 확인` — "Make sure you trust a plugin before installing, updating, or using it." (Plugin security and trust › Recognize when Claude Code refuses or warns › Trust warning before you install)
- `설치 전 점검` — `원문 확인` — "The Will install section shows that a hook exists but not what it runs, so read these files in the plugin's directory:" (Plugin security and trust › Review a plugin before you install)
- 2.1.318 확인: `claude plugin --help`에 `details [options] <name>  Show a plugin's component inventory and projected token cost`가 있다(로컬 확인). 설치·실행은 하지 않았다.
- 수업에 쓸 점: 훅과 MCP 서버는 Claude의 도구 호출이 아니라 플러그인이 직접 실행하므로 권한 규칙이 막지 못한다. "권한 규칙을 걸었으니 안전하다"는 착각을 막는 근거다. 책임: 실행 제어, 도구.
- 주의: 경고는 어느 마켓플레이스의 플러그인이든 같은 문구라고 문서가 적는다(요약이며 인용 대조는 하지 않았다).

## T20 플러그인의 bin/ 와 자동 업데이트

- 공식 문서: https://code.claude.com/docs/en/plugins/security (한국어: https://code.claude.com/docs/ko/plugins/security.md)
- `bin/ 는 PATH에 들어간다` — `원문 확인` — "Claude Code adds each enabled plugin's bin/ directory to the PATH of the Bash tool's shell, so Claude's Bash commands can run any executable there." (Plugin security and trust › Understand what a plugin can do)
- `검토한 파일이 바뀔 수 있다` — `원문 확인` — "when auto-update is on for the marketplace you installed a plugin from, Claude Code updates that plugin in the background, so the files you reviewed can change on disk." (Plugin security and trust › Understand what a plugin can do)
- `설치하면 켜진다` — `원문 확인` — "Installing a plugin also enables it" (Plugin security and trust › Understand what a plugin can do)
- 2.1.318 확인: 해당 없음(자동 업데이트·PATH는 세션 안 동작).
- 수업에 쓸 점: 도구가 늘어나는 경로가 MCP만이 아니라 `bin/` 실행 파일도 있다는 점과, 검토한 코드가 나중에 바뀌어도 검증이 남지 않는 실패를 설명한다. 책임: 도구, 기록.
- 주의: "Installing a plugin also enables it" 뒤에는 `defaultEnabled: false` 예외가 이어진다.

## T21 플러그인 설치 범위

- 공식 문서: https://code.claude.com/docs/en/plugins/overview (한국어: https://code.claude.com/docs/ko/plugins/overview.md)
- `사용자 범위` — `원문 확인` — "User scope: enabled for you in every project on this computer" (Plugins overview › Understand install scopes)
- `프로젝트 범위` — `원문 확인` — "Project scope: enabled for everyone who works in this repository, through the committed .claude/settings.json." (Plugins overview › Understand install scopes)
- `로컬 범위` — `원문 확인` — "Local scope: enabled for you in this repository only" (Plugins overview › Understand install scopes)
- 2.1.318 확인: `claude plugin install --help`의 `--scope`는 열어 보지 않았다(`claude plugin --help`에 `install`이 있음만 확인, 범위 플래그는 미확인).
- 수업에 쓸 점: MCP 범위(T8)와 이름은 같지만 저장 위치가 다르다. 프로젝트 범위로 켜도 각자 자기 컴퓨터에 설치해야 한다는 점이 "팀원은 안 된다" 실패의 원인이다. 책임: 도구, 상태.
- 주의: 설치 단계의 상세는 `plugins/install` 페이지 몫이며 이 대장에서 읽지 않았다.

## 수업에 쓸 때 주의

- 도구 표는 모델·플랫폼마다 다르다. "내장 도구는 N개"처럼 숫자를 외우게 하지 말고, 관찰 도구(Read)와 변경 도구(Edit·Write·Bash)의 권한 차이를 기준으로 가르친다.
- 이 대장의 Bash·Read·MCP 한도(2분·10분·약 30,000자·256 KB·25,000 토큰·128자)는 문서 값이다. 수강생 실습에서 실제로 걸리는지 확인한 값이 아니다(대화형·모델 호출이 필요해 하지 않았다).
- 승인 대화상자, `/mcp`, `/plugin`, `/reload-plugins`는 대화형 전용이라 이 대장에서 동작을 확인하지 못했다. `--help`로 확인한 것은 플래그와 하위 명령의 존재까지다.
- 플러그인 MCP 서버와 일반 MCP 서버는 도구 이름 형태가 다르다(`mcp__plugin_<plugin>_<server>__<tool>` 대 `mcp__<server>__<tool>`). 권한 규칙·훅 matcher 예제를 만들 때 구분한다.
- 실습에서 `~/.claude.json`, `.mcp.json`의 헤더·토큰, `.env`는 열거나 출력하지 않는다. 플러그인이나 MCP 서버를 수강생 환경에 설치하게 하는 실습은 신뢰 경계(T10, T19)를 먼저 가르친 뒤에만 한다.

Quotes verified: 78/78
