# Claude Code 근거 대장 — 실행 제어 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: 각 페이지의 마크다운 판(`https://code.claude.com/docs/en/<page>.md`)을 `curl -sL`로 내려받고, 마크다운 링크 `[글](url)`은 글만 남기고 백틱과 `**`를 지우고 공백을 하나로 접은 뒤 `python3 -I` 스크립트로 인용문이 부분 문자열인지 대조했다. 인용 뒤 괄호는 원문 절 제목이다. 표 행은 `|`를 그대로 두고 칸 일부를 인용했다. WebFetch(요약 모델)는 쓰지 않았다.
- 쓴 페이지: `permissions`, `permission-modes`, `sandboxing`, `hooks`, `hooks-guide`, `settings`(모두 `https://code.claude.com/docs/en/<page>.md`). 한국어 URL은 `https://code.claude.com/docs/_llms/ko.txt` 목록에 있는 것만 적었고 한국어 문장은 인용하지 않았다.
- 로컬 확인: `claude --version`은 2.1.318(Claude Code), `claude --help`만 사용했다. 모델을 부르는 실행(`claude -p`, 대화형 실행)과 설정 파일 변경은 하지 않았다.
- `원문 확인`은 위 대조를 통과한 인용문이다. 문서는 계속 바뀌므로 확인일 2026-11-06 기준이다. 항목 끝 `Quotes verified`는 이 파일의 큰따옴표 인용문 수와 통과 수다.

## C1 권한 규칙 문법 (Tool, Tool(specifier), mcp__)

- 공식 문서: https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/permissions.md)
- `기본 형식` — `원문 확인` — "Permission rules follow the format Tool or Tool(specifier)." (Permission rule syntax)
- `도구 전체 일치` — `원문 확인` — "Bash(*) is equivalent to Bash and matches all Bash commands." (Match all uses of a tool)
- `Bash 규칙` — `원문 확인` — "Bash rules match the whole command text, with * standing in for any text." (Bash)
- `Read·Edit 범위` — `원문 확인` — "Edit rules apply to all built-in tools that edit files." (What Read and Edit rules cover)
- `Read 거부 규칙 예` — `원문 확인` — "add a Read deny rule for its path, such as Read(./.env) or Read(./secrets/**)" (Read and Edit)
- `WebFetch` — `원문 확인` — "WebFetch rules use a domain: prefix and match against the hostname of the requested URL." (WebFetch)
- `MCP 서버 전체` — `원문 확인` — "To match every tool from an MCP server, write mcp__<server>__*." (MCP)
- `MCP 도구 하나` — `원문 확인` — "mcp__puppeteer__puppeteer_navigate matches the puppeteer_navigate tool provided by the puppeteer server" (MCP)
- 2.1.318 확인: `claude --help`에 `--allowedTools, --allowed-tools <tools...>`와 `--disallowedTools, --disallowed-tools <tools...>` 플래그가 있다.
- 수업에 쓸 점: "무엇을 허용하고 막았는가"를 규칙 문자열 한 줄로 적게 해서, 지침 문서에만 적은 금지가 실제로는 집행되지 않는 실패를 막는다. 실행 제어.
- 주의: 도구의 화면 표시 이름과 규칙에 쓰는 이름이 다를 수 있다(문서는 `Stop Task`와 `TaskStop` 예를 든다). 규칙 문법은 도구 이름 기준이라 새 도구가 추가되면 표가 달라진다.

## C2 평가 순서: deny, ask, allow, 그리고 모델이 아닌 Claude Code가 집행한다

- 공식 문서: https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/permissions.md)
- `평가 순서` — `원문 확인` — "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order." (Manage permissions)
- `허용은 거부의 예외가 못 된다` — `원문 확인` — "An allow rule can't carve an exception out of a deny rule." (Manage permissions)
- `ask도 allow보다 앞선다` — `원문 확인` — "a matching ask rule prompts even when a more specific allow rule also matches the same call." (Manage permissions)
- `집행 주체` — `원문 확인` — "Permission rules are enforced by Claude Code, not by the model." (Manage permissions)
- `프롬프트와 CLAUDE.md의 한계` — `원문 확인` — "Instructions in your prompt or CLAUDE.md shape what Claude tries to do, but they don't change what Claude Code allows." (Manage permissions)
- `규칙 확인 화면` — `원문 확인` — "You can view and manage Claude Code's tool permissions with /permissions." (Manage permissions)
- 2.1.318 확인: `/permissions`는 대화형 명령이라 미확인(`claude --help`에는 나오지 않는다).
- 수업에 쓸 점: 지침(CLAUDE.md)과 실행 제어를 구분해서, "CLAUDE.md에 쓰면 막힌다"는 오해를 반례로 보여 준다. 실행 제어.
- 주의: 이 순서는 규칙 사이의 순서다. 모드, 훅, 샌드박스가 따로 더해지므로 최종 결과는 C6~C10, C13~C17과 함께 읽어야 한다.

## C3 Bash 규칙과 복합 명령

- 공식 문서: https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/permissions.md)
- `연산자를 안다` — `원문 확인` — "Claude Code is aware of shell operators, so a rule like Bash(safe-cmd *) won't give it permission to run the command safe-cmd && other-cmd." (Compound commands)
- `하위 명령 전부` — `원문 확인` — "Every subcommand must be allowed for a compound command to run without a prompt" (Compound commands)
- `deny·ask는 하나만 걸려도` — `원문 확인` — "Deny and ask rules apply when any subcommand matches them" (Compound commands)
- `규칙의 한계` — `원문 확인` — "It doesn't match the same program invoked in a different form, so a deny or ask rule covers the invocation Claude usually produces and isn't a security boundary around the program." (What a Bash rule doesn't match)
- `대안` — `원문 확인` — "For filesystem and network enforcement that doesn't depend on the command text, use sandboxing." (What a Bash rule doesn't match)
- 2.1.318 확인: 해당 없음(규칙 해석 동작은 모델 호출 없이 확인할 수 없다).
- 수업에 쓸 점: `Bash(curl *)` 거부가 `/usr/bin/curl`이나 `sh -c`로 우회되는 반례를 보여 주어, 규칙이 막는 것과 막지 못하는 것을 구분하게 한다. 실행 제어.
- 주의: 문서가 든 우회 예(`/bin/rm`, `bash -c`, `git -C . push`)는 문서 표의 것이다. 이 대장에서 직접 실행해 보지 않았다.

## C4 설정 위치와 우선순위 (managed, command line, local, project, user)

- 공식 문서: https://code.claude.com/docs/en/settings.md, https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/settings.md, https://code.claude.com/docs/ko/permissions.md)
- `우선순위` — `원문 확인` — "Settings precedence, highest first: managed settings, command line, project local, shared project, user." (Settings precedence)
- `사용자 파일` — `원문 확인` — "~/.claude/settings.json | You, in every project on this machine" (Settings files and who they affect)
- `공유 프로젝트 파일` — `원문 확인` — ".claude/settings.json | Everyone working in the folder that contains it." (Settings files and who they affect)
- `프로젝트 로컬 파일` — `원문 확인` — ".claude/settings.local.json | You, in this one project only." (Settings files and who they affect)
- `목록은 합쳐진다` — `원문 확인` — "When you set the same list key, such as permissions.allow, in more than one file, Claude Code combines the lists instead of picking one" (Lists merge instead of overriding)
- `거부는 어느 수준에서든` — `원문 확인` — "If a tool is denied at any level, no other level can allow it." (Settings precedence)
- `관리형 규칙` — `원문 확인` — "no other level, including command line arguments, can override a managed permission rule." (Settings precedence)
- `사용자 allow가 프로젝트 deny를 못 이김` — `원문 확인` — "if user settings allow a permission and project settings deny it, the deny rule blocks it." (Settings precedence)
- 2.1.318 확인: `claude --help`에 `--settings <file-or-json>`과 `--setting-sources <sources>`가 있다.
- 수업에 쓸 점: "내 설정에서 허용했는데 왜 막히는가"를 위치별로 추적하게 해서, 규칙의 출처를 모른 채 고치는 실패를 막는다. 실행 제어.
- 주의: 같은 페이지의 첫 문장은 "four files"라고 쓰지만 표는 사용자·공유 프로젝트·프로젝트 로컬·관리형 네 행이다. 우선순위 문장은 키 단위 값 덮어쓰기이고, 규칙 목록은 합쳐진다는 점이 따로 적혀 있으니 섞어 말하지 않는다.

## C5 폴더 신뢰(workspace trust) 대화상자가 바꾸는 것

- 공식 문서: https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/permissions.md)
- `allow는 신뢰 뒤에만` — `원문 확인` — "permissions.allow rules and permissions.additionalDirectories entries in a project's .claude/settings.json grant capability, so Claude Code applies them only after you accept the workspace trust dialog for that folder." (Project allow rules and workspace trust)
- `deny·ask는 영향 없음` — `원문 확인` — "deny and ask rules aren't affected, since they only restrict." (Project allow rules and workspace trust)
- `대화형에서만` — `원문 확인` — "Claude Code shows the trust dialog in interactive sessions only." (Project allow rules and workspace trust)
- `-p에서는 allow가 안 쓰인다` — `원문 확인` — "Not used. Claude Code prints a this workspace has not been trusted warning to stderr" (What runs before you trust a folder)
- `훅은 신뢰와 별개로 쓰인다` — `원문 확인` — "Hooks in settings files, the env block and helper commands such as apiKeyHelper, and a project skill's hooks and allowed-tools | Used | Used." (What runs before you trust a folder)
- 2.1.318 확인: 대화형 전용(신뢰 대화상자)이라 미확인.
- 수업에 쓸 점: 수강생이 받은 저장소의 `.claude/settings.json`에 적힌 allow가 신뢰 확인 전에는 효력이 없다는 것을 알려 주어, 설정을 복사했는데 동작이 다르다는 혼란을 막는다. 실행 제어.
- 주의: 위 표의 마지막 인용(훅이 Used로 적힌 행)은 부모 폴더만 신뢰한 경우와 `-p`/SDK 경우의 두 열이다. 저장소가 제공한 훅이 신뢰 대화상자 없이도 쓰이는 조건이므로, 낯선 저장소를 열 때의 위험을 설명할 때 이 행을 직접 읽게 한다.

## C6 권한 모드 표: default, acceptEdits

- 공식 문서: https://code.claude.com/docs/en/permission-modes.md (한국어: https://code.claude.com/docs/ko/permission-modes.md)
- `모드는 편의와 감독의 교환` — `원문 확인` — "Each mode makes a different tradeoff between convenience and oversight." (Available modes)
- `default` — `원문 확인` — "default | Reads only | Reviewing every action yourself, sensitive work" (Available modes)
- `acceptEdits` — `원문 확인` — "Reads, file edits, and common filesystem commands (mkdir, touch, mv, cp, etc.) | Iterating on code you're reviewing" (Available modes)
- `이름과 설정값` — `원문 확인` — "Its config value is default, which is what hooks and SDK integrations use." (Available modes)
- `acceptEdits가 자동 승인하는 Bash` — `원문 확인` — "In addition to file edits, acceptEdits mode auto-approves common filesystem Bash commands: mkdir, touch, rm, rmdir, mv, cp, and sed." (Auto-approve file edits with acceptEdits mode)
- `그래도 묻는 것` — `원문 확인` — "All other Bash commands except the built-in read-only set" (Auto-approve file edits with acceptEdits mode)
- `deny는 모든 모드에서` — `원문 확인` — "Deny rules block in every mode, including bypassPermissions." (Available modes)
- 2.1.318 확인: `claude --help`의 `--permission-mode <mode>` 선택지는 "acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan"이다(`default`는 선택지에 없고 `manual`이 별칭이다).
- 수업에 쓸 점: 모드를 "많이 믿는 순서"가 아니라 "무엇이 묻지 않고 실행되는가"의 표로 읽게 해서, acceptEdits에서 `rm`·`mv`가 묻지 않는 것을 놓치는 실패를 막는다. 실행 제어.
- 주의: 문서는 화면과 `--help`에서는 Manual, 설정값은 `default`라고 적는다. 표의 `rm`은 acceptEdits 절 문장에는 있고 표의 예 목록(`mkdir, touch, mv, cp, etc.`)에는 없다. 절의 문장이 더 자세하다.

## C7 plan 모드

- 공식 문서: https://code.claude.com/docs/en/permission-modes.md (한국어: https://code.claude.com/docs/ko/permission-modes.md)
- `정의` — `원문 확인` — "Plan mode tells Claude to research and propose changes without making them." (Analyze before you edit with plan mode)
- `동작` — `원문 확인` — "Claude reads files, runs shell commands to explore, and writes a plan, but does not edit your source." (Analyze before you edit with plan mode)
- `편집 차단과 예외` — `원문 확인` — "Except in interactive terminal sessions with bypass permissions available, edits stay blocked until you approve the plan." (Analyze before you edit with plan mode)
- `진입` — `원문 확인` — "Enter plan mode by pressing Shift+Tab or prefixing a single prompt with /plan." (Analyze before you edit with plan mode)
- `나가기` — `원문 확인` — "Press Shift+Tab again to leave plan mode without approving a plan." (Analyze before you edit with plan mode)
- `계획 중 셸 명령` — `원문 확인` — "the classifier reviews shell commands other than critical-path removals instead of prompting you." (Analyze before you edit with plan mode)
- 2.1.318 확인: `claude --help`의 `--permission-mode` 선택지에 "plan"이 있다. 모드 전환 화면은 대화형 전용이라 미확인.
- 수업에 쓸 점: 계획 단계에서 소스 편집이 막힌다는 것을 "승인 전 변경 없음"의 근거로 쓰되, 계획 중 셸 명령은 분류기나 질문을 거친다는 점도 같이 보여 준다. 실행 제어와 지침의 경계.
- 주의: `useAutoModeDuringPlan`이 기본 켜짐이면 plan 모드에서도 분류기가 셸 명령을 승인할 수 있다(위 인용의 앞 문장 조건). "plan은 아무것도 실행하지 않는다"고 가르치면 틀린다.

## C8 auto 모드: 누가 결정하는가와 비용

- 공식 문서: https://code.claude.com/docs/en/permission-modes.md (한국어: https://code.claude.com/docs/ko/permission-modes.md)
- `결정 주체` — `원문 확인` — "A separate classifier model reviews actions before they run, blocking anything that escalates beyond your request, targets unrecognized infrastructure, or appears driven by hostile content Claude read." (Eliminate permission prompts with auto mode)
- `안전을 보장하지 않는다` — `원문 확인` — "Auto mode reduces permission prompts but does not guarantee safety." (Eliminate permission prompts with auto mode)
- `ask 규칙은 유지` — `원문 확인` — "Explicit ask rules still force a prompt." (Eliminate permission prompts with auto mode)
- `평가 순서` — `원문 확인` — "Each action goes through a fixed decision order. The first matching step wins:" (How auto mode evaluates actions)
- `분류기가 보는 것` — `원문 확인` — "Tool results are stripped from those requests, so hostile content in a file or web page can't manipulate the classifier directly." (How auto mode evaluates actions)
- `넓은 allow 제거` — `원문 확인` — "On entering auto mode, broad allow rules that grant arbitrary code execution are dropped:" (How auto mode evaluates actions)
- `비용` — `원문 확인` — "classifier calls count toward your token usage. Each check sends a portion of the transcript plus the pending action, adding a round-trip before execution." (How auto mode evaluates actions)
- `비용이 생기는 곳` — `원문 확인` — "Reads and working-directory edits outside protected paths skip the classifier, so the overhead comes mainly from shell commands and network operations." (How auto mode evaluates actions)
- `설정 파일 제한` — `원문 확인` — "auto doesn't take effect from those files. Move it to ~/.claude/settings.json." (Eliminate permission prompts with auto mode)
- 2.1.318 확인: `claude --help`의 `--permission-mode` 선택지에 "auto"가 있다. 분류기 판단 자체는 모델 호출이 필요해 미확인.
- 수업에 쓸 점: auto 모드를 "승인 없는 모드"가 아니라 "분류기가 승인하는 모드"로 설명해서, 지침에 쓴 경계를 분류기가 읽는다는 점(CLAUDE.md도 분류기 입력)과 비용이 든다는 점을 같이 고지하게 한다. 실행 제어.
- 주의: 비용 문장은 Enterprise와 API 계정 등 일부 계정에 대한 서술이다. 수강생 계정에서 분류기 호출이 어떻게 과금되는지는 이 문서만으로 확정할 수 없다. 모델 요건과 사용 가능 조건은 계정·공급자마다 달라 버전 민감하다.

## C9 dontAsk와 bypassPermissions

- 공식 문서: https://code.claude.com/docs/en/permission-modes.md (한국어: https://code.claude.com/docs/ko/permission-modes.md)
- `dontAsk` — `원문 확인` — "Claude Code auto-denies every tool call that would otherwise prompt you" (Allow only pre-approved tools with dontAsk mode)
- `dontAsk 용도` — `원문 확인` — "File reads inside your working directories and pre-approved tools; anything that would prompt is denied" (Available modes)
- `bypassPermissions` — `원문 확인` — "bypassPermissions mode disables permission prompts and safety checks so tool calls execute immediately, including writes to protected paths." (Skip all checks with bypassPermissions mode)
- `허용 규칙 무효` — `원문 확인` — "Allow rules have no effect in bypassPermissions." (Available modes)
- `권장 환경` — `원문 확인` — "Everything | Isolated containers and VMs only" (Available modes)
- `보호 경로` — `원문 확인` — "Writes to a small set of paths are never auto-approved, except in bypassPermissions mode" (Protected paths)
- 2.1.318 확인: `claude --help`에 `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions` 플래그가 있고 `--permission-mode` 선택지에 "dontAsk", "bypassPermissions"가 있다.
- 수업에 쓸 점: 무인 실행에서 묻는 대신 거부되는 모드(dontAsk)와 모두 통과시키는 모드(bypassPermissions)를 구분해서, 격리 환경 없이 bypassPermissions를 쓰는 실패를 막는다. 실행 제어.
- 주의: 실습에서 `--dangerously-skip-permissions`를 안내하지 않는 쪽이 안전하다. `.git`, `.claude` 같은 보호 경로 쓰기는 모드마다 다르다(문서 표 참고).

## C10 모드 전환과 시작 모드

- 공식 문서: https://code.claude.com/docs/en/permission-modes.md (한국어: https://code.claude.com/docs/ko/permission-modes.md)
- `Shift+Tab 순환` — `원문 확인` — "press Shift+Tab to cycle permission modes. From auto, the first press switches to default, and the cycle then runs default → acceptEdits → plan." (Switch permission modes)
- `순환에 없는 모드` — `원문 확인` — "dontAsk: never appears in the cycle; set it with --permission-mode dontAsk" (Switch permission modes)
- `시작 시 지정` — `원문 확인` — "The same --permission-mode flag works with -p for non-interactive runs." (Switch permission modes)
- `시작 모드 우선순위` — `원문 확인` — "The --permission-mode flag, or --dangerously-skip-permissions" (Which mode a session starts in)
- `기본값이 auto` — `원문 확인` — "With Claude Code v2.1.283 or later, auto mode is the built-in starting permission mode for interactive terminal and VS Code sessions." (Available modes)
- `manual 별칭` — `원문 확인` — "The CLI accepts manual as an alias wherever you type the value" (Available modes)
- `프로젝트 설정의 auto 무시` — `원문 확인` — "the value doesn't take effect, and Claude Code then uses the built-in default rather than a defaultMode from ~/.claude/settings.json." (Which mode a session starts in)
- 2.1.318 확인: `claude --permission-mode <mode>`는 `--help`로 확인했다(선택지는 C6 참고). `Shift+Tab` 순환은 대화형 전용이라 미확인.
- 수업에 쓸 점: 수강생 세션이 어느 모드로 시작했는지 상태 줄로 먼저 확인하게 해서, "default인 줄 알았는데 auto였다"는 오해를 막는다. 실행 제어.
- 주의: 이 문서대로면 2.1.318의 터미널 세션은 기본이 auto다(`default`가 아니다). 이 저장소 수업 문서가 기본을 Manual로 적었다면 문서가 현재 문서와 다르다. 대화형에서 상태 줄을 직접 보고 확인해야 한다. 같은 페이지에 "2.1.228 이상이 필요하고 그 전은 Manual"이라는 버전 단서가 있다.

## C11 샌드박스가 격리하는 것 (파일 시스템, 네트워크)

- 공식 문서: https://code.claude.com/docs/en/sandboxing.md (한국어: https://code.claude.com/docs/ko/sandboxing.md)
- `정의` — `원문 확인` — "The Bash sandbox is a boundary that the operating system enforces around the shell commands Claude runs on your machine." (Configure the sandboxed Bash tool)
- `범위` — `원문 확인` — "The sandbox covers shell commands only. Claude's file tools, MCP servers, and hooks run outside it." (Configure the sandboxed Bash tool)
- `기본은 꺼짐` — `원문 확인` — "The sandbox is off by default." (What the sandbox restricts)
- `쓰기 기본값` — `원문 확인` — "The working directory, a per-user temp directory, and directories you've added." (What the sandbox restricts)
- `읽기 기본값` — `원문 확인` — "Most of the machine, including credential files such as ~/.ssh and ~/.aws/credentials" (What the sandbox restricts)
- `네트워크 기본값` — `원문 확인` — "No direct route out. Connections go through a proxy on your machine that checks each host against your allowed domains, which start empty." (What the sandbox restricts)
- `지원 환경` — `원문 확인` — "The sandbox runs on macOS, Linux, and WSL2. On native Windows, Claude Code runs commands unsandboxed." (Configure the sandboxed Bash tool)
- `파일 도구는 대상 밖` — `원문 확인` — "A denyRead entry doesn't stop the Read tool, and allowedDomains doesn't limit WebFetch" (What runs outside the sandbox)
- `탈출구` — `원문 확인` — "Claude can ask to run a command unsandboxed, usually after it fails in the sandbox" (What runs outside the sandbox)
- 2.1.318 확인: `/sandbox`는 대화형 명령이라 미확인. `claude --help`는 샌드박스 전용 플래그를 보이지 않았다(설정 `sandbox.enabled`로 켠다).
- 수업에 쓸 점: Bash로 `.ssh`를 읽는 실패는 샌드박스가 아니라 읽기 기본값(넓게 읽힘) 때문임을 보여, 파일 도구 규칙과 샌드박스를 따로 설정해야 함을 알린다. 실행 제어.
- 주의: 읽기 기본값이 기기 대부분이라는 점이 직관과 반대다. 샌드박스는 macOS, Linux, WSL2에서만 동작한다. 수강생 환경이 Windows면 효과가 없다.

## C12 샌드박스와 권한 규칙의 관계

- 공식 문서: https://code.claude.com/docs/en/sandboxing.md, https://code.claude.com/docs/en/permissions.md (한국어: https://code.claude.com/docs/ko/sandboxing.md, https://code.claude.com/docs/ko/permissions.md)
- `집행 방식 차이` — `원문 확인` — "The operating system enforces the sandbox boundary on the running process, so it holds regardless of what the model chose to run and even if an allowed command does more than its name suggests." (Permission rules)
- `병합` — `원문 확인` — "Paths and domains from both sandbox settings and permission rules are merged into the final sandbox configuration." (Permission rules)
- `모드가 아니다` — `원문 확인` — "/sandbox is not a permission mode." (Permission modes)
- `겹쳐 쓰기` — `원문 확인` — "Use both for defense-in-depth, since sandbox restrictions still apply even if a prompt injection bypasses Claude's decision-making." (How permissions interact with sandboxing)
- `auto-allow` — `원문 확인` — "Claude Code approves a command automatically, with no prompt, when the command runs inside the sandbox." (Auto-allow mode)
- `ask 규칙 유지` — `원문 확인` — "Content-scoped ask rules like Bash(git push *) still force a prompt even for sandboxed commands" (Auto-allow mode)
- 2.1.318 확인: 대화형 전용(`/sandbox`)이라 미확인.
- 수업에 쓸 점: 권한 규칙은 "명령 문자열"을, 샌드박스는 "실행된 프로세스"를 막는다는 차이를 대비 실험으로 보여, 규칙 우회 실패를 OS 수준에서 막는 층이 따로 있음을 알린다. 실행 제어.
- 주의: 샌드박스 auto-allow와 권한 모드의 auto는 이름이 비슷하지만 다르다(문서가 직접 구분한다). 수업 용어에서 섞지 않는다.

## C13 훅 이벤트 목록 (수업에서 쓸 이벤트)

- 공식 문서: https://code.claude.com/docs/en/hooks.md (한국어: https://code.claude.com/docs/ko/hooks.md)
- `SessionStart` — `원문 확인` — "SessionStart | When a session begins or resumes" (Hook lifecycle)
- `UserPromptSubmit` — `원문 확인` — "UserPromptSubmit | When a prompt is submitted, before Claude processes it." (Hook lifecycle)
- `PreToolUse` — `원문 확인` — "PreToolUse | Before a tool call executes. Can block it" (Hook lifecycle)
- `PostToolUse` — `원문 확인` — "PostToolUse | After a tool call succeeds" (Hook lifecycle)
- `PostToolUseFailure` — `원문 확인` — "PostToolUseFailure | After a tool call fails" (Hook lifecycle)
- `Stop` — `원문 확인` — "Stop | When Claude finishes responding" (Hook lifecycle)
- `SubagentStop` — `원문 확인` — "SubagentStop | When a subagent finishes" (Hook lifecycle)
- `TaskCompleted` — `원문 확인` — "TaskCompleted | When a task is being marked as completed" (Hook lifecycle)
- `PreCompact` — `원문 확인` — "PreCompact | Before context compaction" (Hook lifecycle)
- `SessionEnd` — `원문 확인` — "SessionEnd | When a session terminates" (Hook lifecycle)
- `세 가지 주기` — `원문 확인` — "per turn: UserPromptSubmit, Stop, and StopFailure" (Hook lifecycle)
- 2.1.318 확인: 해당 없음(이벤트 목록은 문서에만 있다. `/hooks` 메뉴의 `All events`로 대화형에서 볼 수 있으나 미확인).
- 수업에 쓸 점: 지침·상태 주입(SessionStart, UserPromptSubmit), 실행 제어(PreToolUse), 검증(PostToolUse, Stop, TaskCompleted), 기록(SessionEnd)으로 이벤트별 책임을 나눠 읽게 한다. PostToolUse를 검증으로 두는 근거는 C21, Stop은 C16이다.
- 주의: 이벤트 수가 30개를 넘고 버전마다 늘어난다. 수업에서는 위 열 개만 쓰고 나머지는 참조로 돌린다. `PreCompact`는 문서에 있다(이 목록에서 빠진 이벤트가 없다는 뜻은 아니다).

## C14 matcher는 무엇을 거르는가

- 공식 문서: https://code.claude.com/docs/en/hooks.md, https://code.claude.com/docs/en/hooks-guide.md (한국어: https://code.claude.com/docs/ko/hooks.md, https://code.claude.com/docs/ko/hooks-guide.md)
- `정의` — `원문 확인` — "The matcher field filters when hooks fire." (Matcher patterns)
- `정확 일치 예` — `원문 확인` — "Bash matches only the Bash tool" (Matcher patterns)
- `정규식 예` — `원문 확인` — "mcp__memory__.* matches every tool from the memory server" (Matcher patterns)
- `PreToolUse 대상` — `원문 확인` — "Matches on any tool name except EndConversation" (PreToolUse)
- `도구 호출 때만 돈다` — `원문 확인` — "PreToolUse runs only when Claude calls a tool." (PreToolUse)
- `쓰기 방식에 무관한 대안` — `원문 확인` — "To run a hook when a specific file changes on disk, whatever wrote it, use FileChanged instead of matching file-editing tools by name." (PreToolUse)
- `FileChanged는 막지 못한다` — `원문 확인` — "Unlike PreToolUse, Claude Code runs FileChanged hooks after the change, and they have no decision control, so they can't block the write." (PreToolUse)
- `Bash가 파일을 고치는 경우` — `원문 확인` — "To reformat a specific file however it changes, including when a Bash command rewrites it, use a FileChanged hook instead." (Auto-format code after edits)
- `하위 에이전트에서도` — `원문 확인` — "Hooks from settings files, managed policy settings, and plugins also run inside subagents." (Hook locations)
- 2.1.318 확인: 해당 없음(훅 매칭은 대화형 세션의 도구 호출이 있어야 관찰된다).
- 수업에 쓸 점: `Edit|Write` 훅이 파일을 지키는 줄 알았는데 Bash 리다이렉트로 뚫리는 실패를 반례로 설계하게 한다. 실행 제어.
- 주의: **추론**이다. matcher가 도구 이름을 거르고(위 인용) FileChanged가 "whatever wrote it"에 쓰인다는 문서 문장에서, `Edit`만 매칭한 PreToolUse 훅은 파일을 쓰는 Bash 명령을 보지 못한다고 읽을 수 있다. 문서에 이 상황을 직접 적은 문장은 찾지 못했고 이 대장에서 실행해 확인하지도 않았다. 수업 전에 실제 세션에서 반례로 확인해야 한다.

## C15 종료 코드 2의 의미

- 공식 문서: https://code.claude.com/docs/en/hooks.md, https://code.claude.com/docs/en/hooks-guide.md (한국어: https://code.claude.com/docs/ko/hooks.md, https://code.claude.com/docs/ko/hooks-guide.md)
- `기본 의미` — `원문 확인` — "Exit with code 2 to block the action." (Exit code 2)
- `예` — `원문 확인` — "a PreToolUse hook blocks the tool call, for example, and a UserPromptSubmit hook rejects the prompt." (Exit code 2)
- `사유는 stderr` — `원문 확인` — "The message that comes with the block is your hook's stderr." (Exit code 2)
- `JSON이 있어도 막힌다` — `원문 확인` — "Exit 2 blocks even when your hook prints JSON:" (Exit code 2)
- `Stop` — `원문 확인` — "Stop | Yes | Prevents Claude from stopping, continues the conversation" (Exit code 2 behavior per event)
- `SubagentStop` — `원문 확인` — "SubagentStop | Yes | Prevents the subagent from stopping" (Exit code 2 behavior per event)
- `PreCompact` — `원문 확인` — "PreCompact | Yes | Blocks compaction" (Exit code 2 behavior per event)
- `PostToolUse는 막지 못함` — `원문 확인` — "PostToolUse | No | Shows stderr to Claude; the tool already ran" (Exit code 2 behavior per event)
- `SessionStart는 막지 못함` — `원문 확인` — "SessionStart | No | Shows stderr to user only" (Exit code 2 behavior per event)
- `그 밖의 종료 코드` — `원문 확인` — "Non-blocking error: your hook exits with any other code, or fails in some other way, such as not starting or printing invalid JSON." (Exit code output)
- `exit 0은 승인이 아니다` — `원문 확인` — "if you exit 0 from a PreToolUse hook, the tool call still goes through the normal permission flow, because exit 0 doesn't approve it." (Hook output)
- 2.1.318 확인: 해당 없음(종료 코드 동작은 훅이 실제로 도는 세션에서만 관찰된다).
- 수업에 쓸 점: 훅 스크립트가 오류로 1을 내고 끝나면 막히지 않고 통과한다는 점을 보여 주어, "막으려면 반드시 2"를 지키지 않아 생기는 실패를 막는다. 실행 제어.
- 주의: 막힐 수 있는 이벤트와 아닌 이벤트가 표로 갈린다. `PostToolUse`는 이미 실행된 뒤라 되돌리지 못한다.

## C16 Stop 훅은 완료 관문이 될 수 있다

- 공식 문서: https://code.claude.com/docs/en/hooks.md (한국어: https://code.claude.com/docs/ko/hooks.md)
- `언제 도는가` — `원문 확인` — "Runs when the main Claude Code agent has finished responding." (Stop)
- `사용자 중단에는 안 돈다` — `원문 확인` — "Does not run if the stoppage occurred due to a user interrupt." (Stop)
- `block 결정` — `원문 확인` — "prevents Claude from stopping. Omit to allow Claude to stop" (Stop decision control)
- `exit 2와 같은 경로` — `원문 확인` — "A hook that blocks by exiting 2 routes the same way as reason: Claude receives the stderr message as the explanation for why it should continue." (Stop decision control)
- `무한 반복 방지 입력` — `원문 확인` — "The stop_hook_active field is true when Claude Code is already continuing as a result of a stop hook. Check this value or process the transcript to avoid blocking on a condition that will never resolve." (Stop input)
- `연속 상한` — `원문 확인` — "Claude Code applies an 8-consecutive-continuation cap: after stop hooks have continued the turn eight times in a row, Claude Code overrides the next block and ends the turn." (Stop input)
- `/goal` — `원문 확인` — "The /goal command is a built-in shortcut for a session-scoped prompt-based Stop hook." (Stop)
- `SubagentStop` — `원문 확인` — "Runs when a Claude Code subagent has finished responding." (SubagentStop)
- 2.1.318 확인: 해당 없음(Stop 훅은 대화형 또는 모델이 도는 세션이 있어야 관찰된다).
- 수업에 쓸 점: "테스트가 통과했다는 증거가 없으면 끝내지 못하게 한다"를 Stop 훅으로 구현하는 실습의 근거다. 모델이 말로 끝났다고 선언하는 실패를 막는 검증 관문이다. 검증과 실행 제어.
- 주의: 완료 관문이 "항상" 보장되는 것은 아니다. 사용자 중단에는 훅이 돌지 않고, 연속 8회 상한 뒤에는 Claude Code가 막기를 무시하고 턴을 끝낸다. 훅이 거짓 조건에서 영원히 막지 않도록 `stop_hook_active`를 확인해야 한다.

## C17 PreToolUse 결정 값과 권한 규칙의 우선순위

- 공식 문서: https://code.claude.com/docs/en/hooks.md, https://code.claude.com/docs/en/permissions.md, https://code.claude.com/docs/en/hooks-guide.md (한국어: https://code.claude.com/docs/ko/hooks.md, https://code.claude.com/docs/ko/permissions.md, https://code.claude.com/docs/ko/hooks-guide.md)
- `네 가지 결과` — `원문 확인` — "This gives it richer control: four outcomes (allow, deny, ask, or defer) plus the ability to modify tool input before execution." (PreToolUse decision control)
- `defer 조건` — `원문 확인` — "ends the turn so the tool can be resumed later, and requires non-interactive mode with the -p flag." (PreToolUse decision control)
- `폐기된 값` — `원문 확인` — "The deprecated values "approve" and "block" map to "allow" and "deny" respectively." (PreToolUse decision control)
- `여러 훅의 우선순위` — `원문 확인` — "When multiple PreToolUse hooks return different decisions, precedence is deny > defer > ask > allow." (PreToolUse decision control)
- `훅은 규칙을 우회하지 못한다` — `원문 확인` — "Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns: a matching deny rule blocks the call" (Precedence among rules, hooks, and mods)
- `결정론적 통제` — `원문 확인` — "which gives you deterministic control: certain actions always happen rather than relying on the LLM to choose to run them." (Automate actions with hooks)
- 2.1.318 확인: 해당 없음.
- 수업에 쓸 점: 훅이 allow를 내도 deny 규칙이 이긴다는 순서를 보여 주어, 훅으로 규칙을 풀어 줄 수 있다는 오해를 막는다. 실행 제어.
- 주의: `defer`는 `claude -p` 비대화형에서만 동작하므로 수업의 대화형 실습에서는 쓰지 않는다. 폐기된 `approve`/`block` 값을 쓴 오래된 예제가 인터넷에 있을 수 있다.

## C18 훅을 설정하는 위치와 /hooks 명령

- 공식 문서: https://code.claude.com/docs/en/hooks.md, https://code.claude.com/docs/en/hooks-guide.md (한국어: https://code.claude.com/docs/ko/hooks.md, https://code.claude.com/docs/ko/hooks-guide.md)
- `사용자 위치` — `원문 확인` — "~/.claude/settings.json | All your projects | No, local to your machine" (Hook locations)
- `프로젝트 위치` — `원문 확인` — ".claude/settings.json | Single project | Yes, can be committed to the repo" (Hook locations)
- `로컬 위치` — `원문 확인` — ".claude/settings.local.json | Single project | No, gitignored when Claude Code saves a setting to it" (Hook locations)
- `병합` — `원문 확인` — "Hook entries merge across settings levels rather than replacing each other" (Hook locations)
- `/hooks 메뉴` — `원문 확인` — "Type /hooks in Claude Code to open a read-only browser for your configured hooks." (The /hooks menu)
- `가이드의 확인법` — `원문 확인` — "Type /hooks at the Claude Code prompt to open the hooks browser." (Set up your first hook)
- `끄기` — `원문 확인` — "To temporarily disable all hooks without removing them, set" (Disable or remove hooks)
- 2.1.318 확인: `/hooks`는 대화형 명령이라 미확인.
- 수업에 쓸 점: 훅이 어디에 적혀 있는지 `/hooks`에서 출처 라벨로 확인하게 해서, "내 훅이 왜 안 도는가" 또는 "누가 넣은 훅이 도는가"를 모른 채 쓰는 실패를 막는다. 실행 제어와 기록.
- 주의: `/hooks`는 읽기 전용 브라우저라 훅을 추가하지 못한다. 훅은 설정 파일을 고쳐서 넣는다. 임시로 끄는 설정 키는 `disableAllHooks`이고, 프로젝트 설정이 사용자 설정을 덮을 수 있다는 점은 같은 절에 적혀 있다.

## C19 hook 입력 JSON: tool_name, tool_input.command, cwd

- 공식 문서: https://code.claude.com/docs/en/hooks.md (한국어: https://code.claude.com/docs/ko/hooks.md)
- `공통 입력 필드 cwd` — `원문 확인` — "cwd | Current working directory when the hook is invoked" (hooks: Common input fields)
- `PreToolUse가 받는 필드` — `원문 확인` — "PreToolUse hooks receive tool_name, tool_input, and tool_use_id." (hooks: PreToolUse input)
- `Bash의 tool_input.command` — `원문 확인` — "The shell command to execute" (hooks: Bash)
- Stop 입력의 `stop_hook_active`는 C16의 인용문을 따른다.
- 수업에 쓸 점: Part 2의 `no_history_rewrite.py`는 stdin JSON의 `tool_input.command`를 읽어 되돌리기 위험 명령을 거르고, Part 3의 `stop_gate.py`는 `cwd`를 읽어 어느 폴더의 산출물을 검사할지 정한다. 훅 스크립트가 무엇을 입력으로 받는지 필드 이름 단위로 말하게 한다. 실행 제어.
- 주의: `tool_input`의 필드는 도구마다 다르다. `command`는 Bash 표의 필드이고 Edit·Write는 `file_path`를 쓴다. `cwd`는 훅이 호출된 시점의 값이라 Claude가 `cd`한 뒤에는 바뀔 수 있다.

## C20 SessionStart hook: 시작 원인 matcher와 맥락 주입

- 공식 문서: https://code.claude.com/docs/en/hooks.md (한국어: https://code.claude.com/docs/ko/hooks.md)
- `matcher의 뜻` — `원문 확인` — "The matcher value corresponds to how the session was initiated:" (hooks: SessionStart)
- `startup` — `원문 확인` — "| startup | New session |" (hooks: SessionStart)
- `resume` — `원문 확인` — "| resume | --resume, --continue, or /resume |" (hooks: SessionStart)
- `clear` — `원문 확인` — "| clear | /clear |" (hooks: SessionStart)
- `compact` — `원문 확인` — "| compact | Auto or manual compaction |" (hooks: SessionStart)
- `stdout이 맥락이 된다` — `원문 확인` — "Claude Code adds a SessionStart hook's plain-text stdout to Claude's context." (hooks: SessionStart decision control)
- `JSON으로 넣기` — `원문 확인` — "hookSpecificOutput.additionalContext adds context for Claude." (hooks: Add context for Claude)
- `첫 응답 전에 끝난다` — `원문 확인` — "Claude's first response still waits for the hooks to finish, so their context reaches Claude." (hooks: SessionStart)
- 2.1.318 확인: 훅 실행은 세션 안에서만 일어나므로 미확인이다.
- 수업에 쓸 점: Part 3에서 실험용 CLAUDE.md의 "시작할 때" 읽기 단계(파일을 읽으라는 문장)를 결정적으로 대신한다. 지침은 모델이 따르기를 바라는 문장이고 SessionStart 훅은 매 시작마다 같은 맥락을 넣는다. 압축 뒤에는 `compact` 시작 원인으로 같은 맥락을 다시 넣을 수 있다. 실행 제어와 상태.
- 주의: 이 훅은 모델을 막지 못하고 맥락만 더한다(차단 제어 없음). matcher를 생략하면 모든 시작 원인에서 돈다고 가정하지 말고 `/hooks`에서 확인한다. 정적인 내용은 문서도 CLAUDE.md를 권한다.

## C21 PostToolUse hook: 실행 뒤 피드백

- 공식 문서: https://code.claude.com/docs/en/hooks.md (한국어: https://code.claude.com/docs/ko/hooks.md)
- `언제 도는가` — `원문 확인` — "Runs immediately after a tool completes successfully." (hooks: PostToolUse)
- `이벤트 표` — `원문 확인` — "| PostToolUse | After a tool call succeeds |" (hooks: Hook events)
- `이미 실행된 뒤` — `원문 확인` — "PostToolUse hooks fire after a tool has already executed successfully." (hooks: PostToolUse input)
- `exit 2의 뜻` — `원문 확인` — "| PostToolUse | No | Shows stderr to Claude; the tool already ran |" (hooks: Exit code 2 behavior per event)
- `경고를 Claude에게` — `원문 확인` — "exit 2 instead so Claude sees the stderr even though the tool already ran." (hooks: Exit code 0)
- `원래 출력은 남는다` — `원문 확인` — "Claude still sees the original output; to replace it, use updatedToolOutput" (hooks: PostToolUse decision control)
- 2.1.318 확인: 훅 실행은 세션 안에서만 일어나므로 미확인이다.
- 수업에 쓸 점: 실습에서 편집 직후 검사(예: 테스트나 형식 확인)를 훅으로 돌려, 검사 결과를 Claude가 같은 턴에 읽고 고치게 한다. 사전 차단(PreToolUse, C19)과 사후 피드백의 차이를 같은 실패 사례로 비교한다. 실행 제어와 검증.
- 주의: 도구가 이미 실행됐으므로 exit 2는 되돌리지 못하고 stderr를 Claude에게 보일 뿐이다. 도구가 실패한 호출에는 돌지 않는다(PostToolUseFailure). Bash 명령이 파일을 고친 경우 `Edit|Write` matcher는 돌지 않는다는 문서 문장이 같은 절에 있다(C14와 함께 읽는다).

## 수업에 쓸 때 주의

- 이 문서들은 매 릴리스 바뀐다. 모드 기본값(C10), 지원 모델(C8), 이벤트 수(C13)는 버전 민감하므로 수업 당일 `claude --version`과 상태 줄로 직접 확인하게 한다.
- `/permissions`, `/hooks`, `/sandbox`, Shift+Tab 순환, 신뢰 대화상자는 대화형 전용이라 이 대장에서 실행해 확인하지 못했다. 수강생 화면에서 확인하는 단계를 실습에 넣는다.
- 규칙(C1~C3)은 명령 문자열을, 샌드박스(C11~C12)는 프로세스를, 훅(C13~C21)은 사건 시점을 다룬다. 세 층은 서로 대신하지 못한다는 점을 같은 실패 사례로 비교해 보여 준다.
- C14의 "Edit 훅은 Bash 쓰기를 보지 못한다"는 추론이다. 수업에서 사실로 말하기 전에 실제 세션에서 재현한다.
- auto 모드(C8)와 `/goal` 같은 모델 호출이 생기는 기능은 저장소 AGENTS.md의 비용 고지 규칙에 맞춰 실행 직전에 규모를 말한다.

Quotes verified: 151/151
