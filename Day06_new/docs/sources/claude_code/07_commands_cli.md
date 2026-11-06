# Claude Code 근거 대장 — 명령·CLI·키 조작 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 대상 문서: `commands`, `cli-reference`, `interactive-mode`. 각각 `curl -sL https://code.claude.com/docs/en/<page>.md`로 마크다운 판을 내려받았다(`https://code.claude.com/docs/en/commands.md`, `.../cli-reference.md`, `.../interactive-mode.md`). 한국어판은 `https://code.claude.com/docs/_llms/ko.txt`에 세 쪽 모두 올라 있다: `https://code.claude.com/docs/ko/commands.md`, `https://code.claude.com/docs/ko/cli-reference.md`, `https://code.claude.com/docs/ko/interactive-mode.md`. 인용은 영어판 기준이다.
- 대조: 마크다운 링크 `[글](주소)`를 글만 남기고 공백을 한 칸으로 줄인 뒤, 이 대장에 큰따옴표로 실은 영어 인용문이 문서 전체 정규화 텍스트의 부분 문자열인지 `python3 -I` 스크립트로 확인했다. WebFetch(요약 모델)는 쓰지 않았다.
- 표의 인용은 해당 행의 첫 문장(또는 첫 절)이다. 설명이 더 길어도 이 대장은 첫 문장만 근거로 삼는다.
- 로컬 확인은 `claude --version`과 `claude --help`만 했다. 모델을 부르는 `claude -p`와 대화형 실행은 하지 않았다. 그래서 명령 표의 2.1.318 칸은 "문서 확인, 대화형 미확인"이다.
- 문서 쪽 최신 버전과 로컬 2.1.318이 다를 수 있다. 문서와 `--help`가 다르면 `--help`(코드)를 따른다.

## K1 내장 명령

commands 쪽에는 내장 명령 외에 번들 스킬(`/code-review`, `/doctor`, `/simplify` 등)과 워크플로도 같은 표에 있다. 아래 "문서 설명"이 `**Skill**`로 시작하는 행은 스킬이다.

| 명령 | 문서 설명 | 2.1.318 | 수업 Part |
|---|---|---|---|
| `/context` | "Visualize current context usage as a colored grid." | 문서 확인, 대화형 미확인 | Part 2·3 |
| `/memory` | "Edit `CLAUDE.md` files, enable or disable auto memory, and view auto memory entries" | 문서 확인, 대화형 미확인 | Part 2 |
| `/permissions` | "Manage allow, ask, and deny rules for tool permissions." | 문서 확인, 대화형 미확인 | Part 2 |
| `/hooks` | "View hook configurations" | 문서 확인, 대화형 미확인 | Part 2 |
| `/agents` | "Print a reminder to ask Claude to create or manage subagents, or to edit `.claude/agents/` or `~/.claude/agents/` directly." | 문서 확인, 대화형 미확인 | Part 2 |
| `/rewind` | "Rewind the conversation and/or code to a previous point, or summarize from a selected message." | 문서 확인, 대화형 미확인 | Part 3 |
| `/compact` | "Free up context by summarizing the conversation so far." | 문서 확인, 대화형 미확인 | Part 3 |
| `/clear` | "Start a new conversation with empty context." | 문서 확인, 대화형 미확인 | Part 3 |
| `/resume` | "Resume a conversation by ID or name, or open the session picker." | 문서 확인, 대화형 미확인 | Part 3 |
| `/rename` | "Rename the current session and show the name on the prompt bar." | 문서 확인, 대화형 미확인 | Part 3 |
| `/branch` | "Create a branch of the current conversation at this point, so you can try a different direction without losing the conversation as it stands." | 문서 확인, 대화형 미확인 | Part 3 |
| `/plan` | "Enter plan mode directly from the prompt." | 문서 확인, 대화형 미확인 | Part 5 |
| `/insights` | "Generate an HTML report analyzing your recent sessions on this machine: which projects you work in, how you use Claude Code, where things go wrong, and features to try." | 문서 확인, 대화형 미확인 | Part 4 |
| `/code-review` | "**Skill.** Review the current diff, or a PR number, branch, or path you pass, for correctness bugs." | 문서 확인, 대화형 미확인 | Part 4 |
| `/goal` | "Set a goal: Claude keeps working across turns until the condition is met or the goal clears for another reason." | 문서 확인, 대화형 미확인 | Part 5 |
| `/init` | "Initialize project with a `CLAUDE.md` guide." | 문서 확인, 대화형 미확인 | Part 2 |
| `/config` | "Open the Settings interface to adjust theme, model, output style, and other preferences." | 문서 확인, 대화형 미확인 | Part 2 |
| `/status` | "Open the Settings interface on the Status tab, showing version, model, account, and connectivity." | 문서 확인, 대화형 미확인 | Part 1 |
| `/cost` | "Alias for `/usage`" | 문서 확인, 대화형 미확인 | Part 1 |
| `/usage` | "Show session cost, plan usage limits, and activity stats." | 문서 확인, 대화형 미확인 | Part 1 |
| `/doctor` | "**Skill.** Run a setup checkup that diagnoses installation, settings, extension, and `CLAUDE.md` problems and proposes fixes that Claude applies after you confirm." | 문서 확인, 대화형 미확인 | Part 1 |
| `/mcp` | "Manage MCP server connections and OAuth authentication." | 문서 확인, 대화형 미확인 | Part 2 |
| `/plugin` | "Manage Claude Code plugins." | 문서 확인, 대화형 미확인 | Part 2 |
| `/skills` | "List available skills." | 문서 확인, 대화형 미확인 | Part 2 |
| `/output-style` | "List output styles or switch to one, for example `/output-style concise`." | 문서 확인, 대화형 미확인 | 참고 |
| `/model` | "Switch the AI model and save it as your default for new sessions." | 문서 확인, 대화형 미확인 | Part 1 |
| `/add-dir` | "Add a working directory for file access during the current session." | 문서 확인, 대화형 미확인 | Part 2 |
| `/export` | "Export the current conversation as plain text." | 문서 확인, 대화형 미확인 | Part 4 |
| `/security-review` | "Analyze the changes on your current branch for security vulnerabilities." | 문서 확인, 대화형 미확인 | Part 4 |
| `/review` | "Alias of `/code-review`: reviews the current diff, or a PR number, branch, or path you pass, such as `/review 1234`, and takes the same effort levels and flags." | 문서 확인, 대화형 미확인 | Part 4 |

commands 문서에 없음: `/todos`

## K2 CLI 플래그

| 플래그 | 문서 설명 | --help에 있음 |
|---|---|---|
| `-p, --print` | "Print response without interactive mode (see Agent SDK documentation for programmatic usage details)." | 있음 |
| `--continue, -c` | "Load the most recent conversation in the current directory, including a background session that has finished; opening finished background sessions requires Claude Code v2.1.257 or later." | 있음 |
| `--resume, -r` | "Resume a specific session by ID or name, or show an interactive picker to choose a session." | 있음 |
| `--fork-session` | "When resuming, create a new session ID instead of reusing the original (use with `--resume` or `--continue`)" | 있음 |
| `--permission-mode` | "Begin in a specified permission mode." | 있음 |
| `--allowedTools` | "Tools that execute without prompting for permission, apart from reads from network paths." | 있음 |
| `--disallowedTools` | "Deny rules." | 있음 |
| `--settings` | "Path to a settings JSON file or an inline JSON string." | 있음 |
| `--setting-sources` | "Comma-separated list of setting sources to load (`user`, `project`, `local`)." | 있음 |
| `--agents` | "Define custom subagents dynamically via JSON." | 있음 |
| `--agent` | "Specify an agent for the current session (overrides the `agent` setting)" | 있음 |
| `--worktree, -w` | "Start Claude in an isolated git worktree at `<repo>/.claude/worktrees/<name>`." | 있음 |
| `--model` | "Sets the model for the current session with a model alias such as `sonnet`, `opus`, `haiku`, or `fable`, or a model's full name." | 있음 |
| `--add-dir` | "Add additional working directories for Claude to read and edit files." | 있음 |
| `--mcp-config` | "Load MCP servers from JSON files or strings (space-separated)." | 있음 |
| `--strict-mcp-config` | "Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations." | 있음 |
| `--append-system-prompt` | "Append custom text to the end of the default system prompt" | 있음 |
| `--system-prompt` | "Replace the entire system prompt with custom text" | 있음 |
| `--output-format` | "Specify output format for print mode (options: `text`, `json`, `stream-json`)" | 있음 |
| `--max-turns` | "Limit the number of agentic turns (print mode only)." | 없음 |
| `--max-budget-usd` | "Stop the run once estimated spend on API calls reaches this amount (print mode only)." | 있음 |
| `--verbose` | "Enable verbose logging, shows full turn-by-turn output." | 있음 |
| `--tools` | "Restrict which built-in tools Claude can use." | 있음 |
| `--permission-prompt-tool` | "Specify an MCP tool to handle permission prompts in non-interactive mode." | 있음 |
| `--dangerously-skip-permissions` | "Skip permission prompts." | 있음 |
| `--allow-dangerously-skip-permissions` | "Add `bypassPermissions` to the `Shift+Tab` mode cycle without starting in it." | 있음 |
| `--name, -n` | "Set a display name for the session, shown in `/resume` and the terminal title." | 있음 |
| `--session-id` | "Use a specific session ID for the conversation (must be a valid UUID)" | 있음 |
| `--no-session-persistence` | "Disable session persistence so sessions are not saved to disk and cannot be resumed." | 있음 |
| `--bare` | "Minimal mode: skip auto-discovery of hooks, skills, custom commands, subagents, installed plugins, MCP servers, auto memory, and CLAUDE.md so scripted calls start faster." | 있음 |
| `--safe-mode` | "Start with all customizations disabled to troubleshoot a broken configuration: CLAUDE.md, skills, plugins, hooks, MCP servers, custom commands and agents, output styles, workflows, custom themes, custom keybindings, status line and file-suggestion commands," | 있음 |
| `--from-pr` | "Open the session picker filtered to sessions linked to a specific pull request." | 있음 |
| `--init-only` | "Run Setup and `SessionStart` hooks, then exit without starting a conversation" | 없음 |

## K3 키 조작

| 키 | 문서 설명 | 맥락 |
|---|---|---|
| Esc | "Interrupt Claude, or close a dialog" | "Stop the current response or tool call mid-turn so you can redirect." |
| Esc Esc | "Clear input draft, or rewind" | "When the prompt input contains text, double `Esc` clears it and saves the draft to history so `Up` recalls it." |
| Shift+Tab | "Cycle permission modes" | "Cycle through `default` (labeled Manual in the mode indicator), `acceptEdits`, `plan`, and, when available, `bypassPermissions` and then `auto`." |
| `!` (줄 맨 앞) | "Shell mode" | "Run a command directly, add its output to the session, and have Claude respond to it" |
| Ctrl+O | "Toggle transcript viewer" | "Shows detailed tool usage and execution, with a timestamp and the model used on each assistant message." |
| Ctrl+B | "Background running tasks" | "Backgrounds Bash commands and agents." |
| Ctrl+T | "Toggle Claude's task checklist" | "Show or hide Claude's to-do checklist in the status area." |
| 셸 모드 | (본문) | "Adds the command and its output to the conversation context" |
| 셸 모드 진입 | (본문) | "Run shell commands directly without going through Claude by prefixing your input with `!`:" |
| 트랜스크립트 보기 종료 | (본문) | "Exit transcript view." |
| 트랜스크립트 보기 열기 | (본문) | "When the transcript viewer is open (toggled with `Ctrl+O`), these shortcuts are available." |
| 메모리 단축키(`#`로 CLAUDE.md에 추가) | 문서에 없음 | 문서에 없음 |

## 2.1.318 로컬 확인

- `claude --version` 출력: `2.1.318 (Claude Code)`
- `claude --help`에서 각 K2 플래그 문자열 검색 결과:

| 플래그 | claude --help |
|---|---|
| `-p, --print` | present |
| `--continue, -c` | present |
| `--resume, -r` | present |
| `--fork-session` | present |
| `--permission-mode` | present |
| `--allowedTools` | present |
| `--disallowedTools` | present |
| `--settings` | present |
| `--setting-sources` | present |
| `--agents` | present |
| `--agent` | present |
| `--worktree, -w` | present |
| `--model` | present |
| `--add-dir` | present |
| `--mcp-config` | present |
| `--strict-mcp-config` | present |
| `--append-system-prompt` | present |
| `--system-prompt` | present |
| `--output-format` | present |
| `--max-turns` | absent |
| `--max-budget-usd` | present |
| `--verbose` | present |
| `--tools` | present |
| `--permission-prompt-tool` | present |
| `--dangerously-skip-permissions` | present |
| `--allow-dangerously-skip-permissions` | present |
| `--name, -n` | present |
| `--session-id` | present |
| `--no-session-persistence` | present |
| `--bare` | present |
| `--safe-mode` | present |
| `--from-pr` | present |
| `--init-only` | absent |

## 수업에 쓸 때 주의

- `/todos`는 commands 문서에 없다. 현재 수업 텍스트(`Day06_new/use_cc/`)는 `/todos`를 쓰지 않는다. 앞으로도 쓰지 말고, 할 일 목록은 interactive-mode의 `Ctrl+T`나 `/tasks`로 안내한다.
- 현재 수업 텍스트가 쓰는 슬래시 명령 중 내장이 아닌 것이 둘 있다. `/mission`은 2026-11-06까지 수업이 `Day06_new/use_cc/.claude/skills/mission/SKILL.md`에 정의한 프로젝트 스킬이었고(commands 문서에 없는 것이 정상), 2026-11-06에 안내 문서 `Day06_new/use_cc/MISSION_GUIDE.md`(`use_cc/CLAUDE.md`가 불러옴)로 교체되었다(저자 결정). `/speckit-constitution`은 `Day06_new/use_cc/part5/concept.md:62`에 나오는 spec-kit의 명령이며 Claude Code 내장이 아니다. `/insights`, `/memory`, `/plan`, `/context`, `/clear`, `/exit`는 모두 commands 문서에 있다.
- `--max-turns`는 cli-reference에 있지만 2.1.318의 `claude --help`에는 없다(`--max-budget-usd`는 있다). 미션 카드에 쓰려면 먼저 확인이 필요하고, 모델을 부르는 확인이라 이 대장에서는 하지 않았다. `--init-only`도 같은 상태다.
- `/agents`는 문서 기준으로 서브에이전트 안내 문구를 출력하는 명령이다(v2.1.197 이하에서는 대화형 화면). `/code-review`, `/doctor`는 번들 스킬이고 `/review`는 `/code-review`의 별칭, `/cost`는 `/usage`의 별칭이다. 수강생에게 보이는 화면은 대화형으로 따로 확인해야 한다.
- 메모리 단축키(`#`로 CLAUDE.md에 추가)는 interactive-mode 문서에 없다. 수업에서 가르치지 말고 `/memory`로 안내한다.
- 이 대장의 명령 행은 모두 "문서 확인, 대화형 미확인"이다. 미션 카드가 화면 출력을 설명하려면 저자가 대화형 세션에서 직접 확인해야 한다. `Esc Esc`, `Shift+Tab`, `!`, `Ctrl+O`도 마찬가지로 문서 기준이다.

Quotes verified: 81/81