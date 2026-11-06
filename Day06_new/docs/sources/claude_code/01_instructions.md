# Claude Code 근거 대장 — 지침 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: 각 페이지의 `.md` 판(`https://code.claude.com/docs/en/<page>.md`)을 `curl -sL`로 내려받고, `python3 -I` 스크립트로 마크다운 링크 `[글](url)`를 글자만 남기고, 백틱과 `*` 강조 표지를 지우고, 공백을 한 칸으로 합친 뒤 인용문을 부분 문자열로 대조했다. WebFetch(요약 모델)는 쓰지 않았다.
- 사용한 페이지: `memory`, `skills`, `output-styles`, `claude-directory`, `features-overview`, `best-practices` (모두 `https://code.claude.com/docs/en/` 아래). 한국어 주소는 `https://code.claude.com/docs/_llms/ko.txt` 목록에 있는 것만 적었고 한국어 문장은 인용하지 않았다.
- 수준 표기: `원문 확인`은 위 대조를 통과한 인용문에만 붙였다. 2.1.318 칸은 `claude --version`(2.1.318)과 모델을 부르지 않는 `claude --help`로 본 것만 적고, 대화형 명령(`/memory`, `/init`, `/output-style` 등)은 실행하지 않았으므로 `대화형 전용이라 미확인`으로 적었다.
- 인용 뒤 괄호는 원문 절 제목이다. 문서는 계속 바뀌므로 확인일 2026-11-06 기준이다.

## I1 CLAUDE.md 파일 위치와 범위

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `적재 순서의 정의` — `원문 확인` — "The table below lists them in load order, from broadest scope to most specific, so a project instruction appears in context after a user instruction." (Choose where to put CLAUDE.md files)
- `관리 정책 파일 위치(macOS)` — `원문 확인` — "macOS: /Library/Application Support/ClaudeCode/CLAUDE.md" (Choose where to put CLAUDE.md files)
- `사용자 파일` — `원문 확인` — "~/.claude/CLAUDE.md" (Choose where to put CLAUDE.md files)
- `프로젝트 파일은 두 위치 중 하나` — `원문 확인` — "A project CLAUDE.md can be stored in either ./CLAUDE.md or ./.claude/CLAUDE.md." (Set up a project CLAUDE.md)
- `개인용 로컬 파일` — `원문 확인` — "Personal project-specific preferences; add to .gitignore" (Choose where to put CLAUDE.md files)
- 2.1.318 확인: 대화형 전용이라 미확인. `claude --help`의 `--bare`는 "CLAUDE.md auto-discovery"를 건너뛴다고 적혀 있다(도움말 `--bare` 항목).
- 수업에 쓸 점: 지침이 어느 범위(조직·개인·프로젝트·로컬)에서 오는지 구분하지 않으면 "내 컴퓨터에서만 되는 규칙"이 팀 저장소에 섞인다. 책임: 지침.
- 주의: 관리 정책 파일은 OS마다 경로가 다르다(Linux는 `/etc/claude-code/CLAUDE.md`, Windows는 `C:\Program Files\ClaudeCode\CLAUDE.md`, 같은 표). 이 컴퓨터의 관리 정책 파일은 확인하지 않았다.

## I2 CLAUDE.md 적재 순서: 상위 폴더는 시작 때, 하위 폴더는 필요할 때

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `상위 폴더` — `원문 확인` — "Claude Code loads CLAUDE.md and CLAUDE.local.md from your current working directory and every directory above it." (How CLAUDE.md files load)
- `덮어쓰지 않고 이어 붙인다` — `원문 확인` — "All discovered files are concatenated into context rather than overriding each other." (How CLAUDE.md files load)
- `순서` — `원문 확인` — "Across the directory tree, content is ordered from the filesystem root down to your working directory." (How CLAUDE.md files load)
- `같은 폴더 안의 순서` — `원문 확인` — "Within each directory, CLAUDE.local.md is appended after CLAUDE.md, so your personal notes are the last thing Claude reads at that level." (How CLAUDE.md files load)
- `하위 폴더는 필요할 때` — `원문 확인` — "Instead of loading them at launch, Claude Code loads each one once Claude reads, writes, or edits another file in that subdirectory." (How CLAUDE.md files load)
- `추가 폴더` — `원문 확인` — "By default, CLAUDE.md files from these directories are not loaded." (Load from additional directories)
- `사람용 주석` — `원문 확인` — "Block-level HTML comments (<!-- maintainer notes -->) in CLAUDE.md files are stripped before the content is injected into Claude's context." (How CLAUDE.md files load)
- 2.1.318 확인: 대화형 전용이라 미확인. `claude --help`에서 `--add-dir <directories...>`("Additional directories to allow tool access to")가 있음을 확인했다. 환경 변수 `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`는 도움말에 없고 문서 근거만 있다.
- 수업에 쓸 점: 하위 폴더 CLAUDE.md는 시작 때 보이지 않으므로 "규칙이 안 먹는다"를 보면 먼저 무엇이 언제 적재됐는지 본다. 책임: 지침.
- 주의: 하위 폴더 파일은 `/context all`의 Memory files 목록에 나오지 않는다(memory 문서 문제 해결 절). 이 저장소처럼 `Day06_new/` 같은 하위 폴더에서 세션을 시작하면 위 폴더의 CLAUDE.md도 함께 적재된다.

## I3 AGENTS.md 대체 읽기

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `기본 규칙` — `원문 확인` — "By default, Claude reads AGENTS.md only when you have no CLAUDE.md in your working directory or above it." (When Claude Code reads AGENTS.md)
- `버전 조건` — `원문 확인` — "Reading AGENTS.md directly requires Claude Code v2.1.277 or later." (AGENTS.md)
- `CLAUDE.local.md의 함정` — `원문 확인` — "Because CLAUDE.local.md counts, adding one to keep your own uncommitted instructions in a project that relies on AGENTS.md stops Claude from reading AGENTS.md for you." (When Claude Code reads AGENTS.md)
- `import로 공유` — `원문 확인` — "Keeping the import never makes Claude read AGENTS.md twice, whichever Project instructions value you use." (Remove an earlier AGENTS.md workaround)
- `읽지 않는 파일` — `원문 확인` — "Not read: AGENTS.local.md, AGENTS.override.md, or anything under a .agents/ directory" (When Claude Code reads AGENTS.md)
- 2.1.318 확인: `claude --version`이 2.1.318이므로 v2.1.277 조건은 충족한다. 설정 화면 `/config`의 Project instructions 항목은 대화형 전용이라 미확인.
- 수업에 쓸 점: 이 저장소는 `CLAUDE.md`가 `@AGENTS.md`를 불러오는 방식이라, 한 파일에 쓴 지침이 Claude Code와 다른 도구에 함께 닿는다. 책임: 지침.
- 주의: 같은 경로에 CLAUDE.md와 AGENTS.md가 둘 다 있으면 기본값은 CLAUDE.md만 읽는다. AGENTS.md 내용이 보이게 하려면 import가 필요하다.

## I4 `@` import

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `문법` — `원문 확인` — "CLAUDE.md files can import additional files using @path/to/import syntax." (Import additional files)
- `상대 경로 기준` — `원문 확인` — "Relative paths resolve relative to the file containing the import, not the working directory." (Import additional files)
- `깊이 제한` — `원문 확인` — "Imported files can recursively import other files, with a maximum depth of four hops." (Import additional files)
- `코드 블록 안은 건너뜀` — `원문 확인` — "Import parsing skips Markdown code spans and fenced code blocks." (Import additional files)
- `바깥 경로는 승인 대화상자` — `원문 확인` — "The first time Claude Code encounters external imports in a project, it shows an approval dialog listing the files." (Import additional files)
- `맥락 비용은 줄지 않는다` — `원문 확인` — "Imports help you organize a long file but don't reduce its context cost, because imported files load together with the CLAUDE.md that imports them." (Write effective instructions)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: `@`로 불러온 문서도 매 세션 맥락에 그대로 들어가므로 "길어서 import로 나눴다"는 크기 문제의 해결이 아니다. 책임: 지침.
- 주의: 글에서 경로를 언급만 하고 싶으면 백틱으로 감싸야 한다(같은 절). 따옴표로 감싼 경로는 import되지 않는다.

## I5 `.claude/rules/`와 경로 한정 규칙

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `기본 적재` — `원문 확인` — "Rules without paths frontmatter are loaded at launch with the same priority as .claude/CLAUDE.md." (Set up rules)
- `경로 한정 규칙의 적재 시점` — `원문 확인` — "A path-scoped rule loads when Claude uses the Read, Write, or Edit tool on a matching file." (Path-specific rules)
- `유일한 필드` — `원문 확인` — "paths is the only field Claude Code reads from a rule; any other field is ignored without an error." (Rule frontmatter reference)
- `skills와의 구분` — `원문 확인` — "Rules load into context every session or when matching files are opened." (Organize rules with .claude/rules/)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: 한 부분에만 해당하는 규칙을 CLAUDE.md에서 분리하면 항상 적재되는 지침이 짧아진다. 책임: 지침.
- 주의: 철자가 틀린 필드는 오류 없이 무시된다. 경로 한정 규칙도 파일 크기 상한이 있다(I6).

## I6 CLAUDE.md 크기와 내용에 대한 공식 조언

- 공식 문서: https://code.claude.com/docs/en/memory.md, https://code.claude.com/docs/en/best-practices.md (한국어: https://code.claude.com/docs/ko/memory.md, https://code.claude.com/docs/ko/best-practices.md)
- `200줄 목표` — `원문 확인` — "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." (Write effective instructions)
- `검증 가능한 문장` — `원문 확인` — "Write instructions that are concrete enough to verify:" (Write effective instructions)
- `모순` — `원문 확인` — "if two instructions contradict each other, Claude may pick one arbitrarily." (Write effective instructions)
- `4 MiB 상한` — `원문 확인` — "Claude Code skips a file over 4 MiB." (My CLAUDE.md is too large)
- `매 작업에 주의를 쓴다` — `원문 확인` — "every line in it takes a little of Claude's attention on every task, whether it's relevant or not." (Keep CLAUDE.md short)
- `담을 내용 1` — `원문 확인` — "How to confirm work in this repo: the exact test, typecheck, and lint commands, and how to run a single test file" (Keep CLAUDE.md short)
- `담을 내용 2` — `원문 확인` — "Anything you've had to correct twice already" (Keep CLAUDE.md short)
- `구조 설명은 이제 쓰지 않는다` — `원문 확인` — "Claude reads the repo itself. Only write down what isn't in there." (What you can stop doing)
- 2.1.318 확인: 대화형 전용이라 미확인. 시작 때 길이 경고는 대화형에서만 보인다.
- 수업에 쓸 점: 담을 것은 "코드를 읽어도 모르는 것"(검사 명령, 함정, 저장소 밖 결정)이고 디렉터리 구조 설명은 아니다. 책임: 지침, 검증.
- 주의: `best-practices`는 "아키텍처와 파일 배치를 CLAUDE.md에 설명하라"는 옛 조언을 이제 필요 없다고 분류한다. 수업 자료가 CLAUDE.md에 구조 설명을 넣으라고 가르치고 있다면 이 점과 어긋난다.

## I7 `/init`, `/memory`, `/context all`, `/doctor`

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `/init` — `원문 확인` — "Run /init to generate a starting CLAUDE.md automatically." (Set up a project CLAUDE.md)
- `/init은 덮어쓰지 않는다` — `원문 확인` — "If a CLAUDE.md already exists, /init suggests improvements rather than overwriting it." (Set up a project CLAUDE.md)
- `새 /init 흐름` — `원문 확인` — "set the CLAUDE_CODE_NEW_INIT environment variable to 1 before you run /init." (Set up a project CLAUDE.md)
- `/memory` — `원문 확인` — "The /memory command lists your CLAUDE.md, CLAUDE.local.md, and other memory file locations across user and project scopes." (View and edit with /memory)
- `적재 확인` — `원문 확인` — "To confirm the file loaded, run /context all in a session and check the list under Memory files." (Set up a project CLAUDE.md)
- `/doctor prompt-audit` — `원문 확인` — "To have Claude check your instruction files for outdated or conflicting content, run /doctor prompt-audit in a session." (Audit your instruction files)
- `버전 조건` — `원문 확인` — "/doctor prompt-audit requires Claude Code v2.1.283 or later." (Audit your instruction files)
- 2.1.318 확인: 대화형 전용이라 미확인. 모델을 부르는 명령이 섞여 있어 실행하지 않았다.
- 수업에 쓸 점: "Claude가 내 지침을 실제로 읽었는가"는 `/context all`의 Memory files로 본다. 읽혔는지 모르는 채 지침이 나쁘다고 판단하면 원인을 놓친다. 책임: 지침, 기록.
- 주의: `/doctor prompt-audit`는 `/claude-api` 번들 Skill로 돌아가므로 그 Skill을 끄면 안 된다(같은 절). 모델 호출 비용이 든다고 문서가 직접 말하지는 않았으나 모델이 읽는 방식이므로 먼저 고지하는 편이 안전하다.

## I8 CLAUDE.md는 맥락이지 강제가 아니다

- 공식 문서: https://code.claude.com/docs/en/memory.md, https://code.claude.com/docs/en/best-practices.md (한국어: https://code.claude.com/docs/ko/memory.md, https://code.claude.com/docs/ko/best-practices.md)
- `맥락, 강제 설정 아님` — `원문 확인` — "To block an action regardless of what Claude decides, use a PreToolUse hook instead." (CLAUDE.md vs auto memory)
- `전달 방식` — `원문 확인` — "CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself." (Claude isn't following my CLAUDE.md)
- `비결정적 지침` — `원문 확인` — "Non-deterministic: you write the instruction, and Claude (the model) reads it." (Deterministic and non-deterministic instructions)
- `결정적 지침` — `원문 확인` — "Deterministic: you configure the instruction, and Claude Code (the harness) has to execute this." (Deterministic and non-deterministic instructions)
- `강조를 늘려도 안 되면` — `원문 확인` — "If you keep adding emphasis to a CLAUDE.md line and Claude still misses it, that's a sign the line belongs in a hook." (Deterministic and non-deterministic instructions)
- `예외 없는 규칙` — `원문 확인` — "CLAUDE.md is for guidelines, and Claude is allowed to decide a guideline doesn't apply." (Enforce the rules that can't have exceptions)
- 2.1.318 확인: 해당 없음(문서 서술). 훅의 실제 동작은 다른 대장에서 다룬다.
- 수업에 쓸 점: 지침(CLAUDE.md)과 실행 제어(훅·deny 규칙)를 구분하는 근거다. "반드시"를 CLAUDE.md에 쓰는 실패를 막는다. 책임: 지침, 실행 제어.
- 주의: 같은 문서의 표는 "무엇을 하는가"뿐 아니라 "언제 끝났는가"(`/goal`, `Stop` 훅), "누가 마지막 말을 하는가"까지 결정적/비결정적으로 나눈다. 이 표를 6책임 분석의 보조 표로 쓸 수 있으나 표 자체의 인용은 이 대장에서 하지 않았다.

## I9 CLAUDE.md와 auto memory, compaction 뒤의 지침

- 공식 문서: https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/memory.md)
- `세션은 빈 맥락으로 시작` — `원문 확인` — "Each Claude Code session begins with a fresh context window." (How Claude remembers your project)
- `auto memory` — `원문 확인` — "Auto memory: notes Claude writes itself based on your corrections and preferences" (How Claude remembers your project)
- `compaction` — `원문 확인` — "Project-root CLAUDE.md survives compaction: after /compact, Claude re-reads it from disk and re-injects it into the session." (Instructions seem lost after /compact)
- `대화에서만 준 지침` — `원문 확인` — "Add conversation-only instructions to CLAUDE.md to make them persist." (Instructions seem lost after /compact)
- `auto memory 위치(.claude 디렉터리 문서)` — `원문 확인` — "Auto memory: Claude's notes to itself across sessions" (File reference)
- 2.1.318 확인: 대화형 전용이라 미확인. `claude --help`의 `--bare` 설명에 "auto-memory"를 건너뛴다는 말이 있다(도움말 `--bare` 항목).
- 수업에 쓸 점: 다음 세션이 이어받는 것(상태)과 지침이 섞이는 곳이다. 대화로만 한 약속은 압축이나 새 세션에서 사라진다. 책임: 지침, 상태.
- 주의: 이 대장은 지침 책임 담당이라 auto memory의 저장 위치와 200줄/25KB 한도 같은 세부는 인용하지 않았다. 상태 책임 쪽 대장에서 다룬다.

## I10 Skills의 위치

- 공식 문서: https://code.claude.com/docs/en/skills.md (한국어: https://code.claude.com/docs/ko/skills.md)
- `위치가 적재를 결정` — `원문 확인` — "Where you save a skill decides which sessions load it." (Choose where skills load)
- `개인` — `원문 확인` — "~/.claude/skills/<skill-name>/SKILL.md" (Choose where skills load)
- `프로젝트` — `원문 확인` — "Sessions in this repository, but not cloud threads in a project. Commit it so your team gets it too" (Choose where skills load)
- `플러그인` — `원문 확인` — "Wherever the plugin is enabled, as /plugin-name:skill-name" (Choose where skills load)
- `상위 폴더` — `원문 확인` — "Claude Code loads project skills from .claude/skills/ in the directory where you start it and in every parent directory up to the repository root" (Load skills in monorepos and subdirectories)
- `하위 폴더` — `원문 확인` — "Skills in a .claude/skills/ directory below where you started don't load at startup." (Load skills in monorepos and subdirectories)
- `프로젝트 경로` — `원문 확인` — "| Project | .claude/skills/<skill-name>/SKILL.md |" (Choose where skills load)
- `같은 이름` — `원문 확인` — "Enterprise over personal, and personal over project." (Resolve skills that share a name)
- 2.1.318 확인: `claude --help`에 `--disable-slash-commands`("Disable all skills and commands")가 있다. 위치별 적재는 대화형 전용이라 미확인.
- 수업에 쓸 점: 같은 Skill이 어디에 있느냐에 따라 팀 전체의 규칙이 되기도 하고 내 컴퓨터의 습관이 되기도 한다. 책임: 지침.
- 주의: 이름이 겹치면 개인 Skill이 프로젝트 Skill을 이긴다. 수강생 저장소의 프로젝트 Skill이 개인 Skill에 가려질 수 있다.

## I11 Skills의 적재 시점: 시작 때는 설명, 쓸 때 본문

- 공식 문서: https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/features-overview.md (한국어: https://code.claude.com/docs/ko/skills.md, https://code.claude.com/docs/ko/features-overview.md)
- `관련될 때 Claude가 쓴다` — `원문 확인` — "Claude uses skills when relevant, or you can invoke one directly with /skill-name." (Extend Claude with skills)
- `본문은 쓸 때만` — `원문 확인` — "Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it." (Extend Claude with skills)
- `설명만 항상` — `원문 확인` — "In a regular session, skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked." (Control who invokes a skill)
- `한 번 들어오면 남는다` — `원문 확인` — "When you or Claude invoke a skill, the rendered SKILL.md content enters the conversation as a single message and stays there across later turns." (Skill content lifecycle)
- `다시 읽지 않는다` — `원문 확인` — "Claude Code does not re-read the skill file on later turns, so write guidance that should apply throughout a task as standing instructions rather than one-time steps." (Skill content lifecycle)
- `설명 길이 상한` — `원문 확인` — "the combined description and when_to_use text is truncated at 1,536 characters in the skill listing to reduce context usage." (Frontmatter reference)
- `설명이 모호하면` — `원문 확인` — "If descriptions are vague or overlap, Claude may load the wrong skill or miss one that would help." (Understand how features load)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: Skill 설명(description)이 곧 "언제 쓰는가"의 지침이다. 설명이 흐리면 Skill이 뜨지 않거나 잘못 뜬다. 책임: 지침.
- 주의: 압축 때 Skill은 최근 호출분부터 호출당 앞 5,000토큰, 합계 25,000토큰 예산으로 다시 붙는다(skills 문서 Skill content lifecycle). 오래된 Skill은 압축 뒤에 빠질 수 있다.

## I12 Skills의 호출 제어와 도구 frontmatter

- 공식 문서: https://code.claude.com/docs/en/skills.md (한국어: https://code.claude.com/docs/ko/skills.md)
- `기본 필드` — `원문 확인` — "Only description is recommended so Claude knows when to use the skill." (Frontmatter reference)
- `모르는 필드는 조용히 무시` — `원문 확인` — "Claude Code ignores a field it doesn't recognize without reporting an error." (Frontmatter reference)
- `사람만 호출` — `원문 확인` — "disable-model-invocation: true: Claude can't invoke the skill on its own." (Control who invokes a skill)
- `모델만 호출` — `원문 확인` — "user-invocable: false: Only Claude can invoke the skill." (Control who invokes a skill)
- `차단 동작` — `원문 확인` — "If Claude tries anyway, Claude Code blocks the call and instructs it not to reproduce the deploy steps another way, so expect Claude to suggest running /deploy yourself." (Control who invokes a skill)
- `설명이 맥락에 있는가` — `원문 확인` — "Description not in context, full skill loads when invoked" (Control who invokes a skill)
- `도구 사전 승인` — `원문 확인` — "The grant clears when you send your next message, even though the skill content stays in context" (Pre-approve tools for a skill)
- `도구 제한이 아니다` — `원문 확인` — "It does not restrict which tools are available: every tool remains callable" (Pre-approve tools for a skill)
- `도구 제거` — `원문 확인` — "Tools removed from Claude's available pool while this skill is active." (Frontmatter reference)
- `저장소 Skill의 위험` — `원문 확인` — "A skill can grant itself broad tool access, so review the allowed-tools of skills checked into a repository before you run Claude Code there." (Pre-approve tools for a skill)
- `서브에이전트에서 실행` — `원문 확인` — "Set to fork to run in a forked subagent context." (Frontmatter reference)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: 부작용이 있는 절차(배포, 커밋)는 `disable-model-invocation: true`로 사람이 부를 때만 돌게 한다. `allowed-tools`는 허용이지 제한이 아니므로 제한은 `disallowed-tools`나 deny 규칙에서 한다. 책임: 지침, 실행 제어.
- 주의: `allowed-tools`는 작업 폴더 신뢰 여부와 상관없이 적용된다(같은 절). 남이 만든 저장소의 Skill을 열기 전에 이 필드를 읽어야 한다.

## I13 사용자 정의 슬래시 명령과 Skill은 한 장치다

- 공식 문서: https://code.claude.com/docs/en/skills.md, https://code.claude.com/docs/en/claude-directory.md (한국어: https://code.claude.com/docs/ko/skills.md, https://code.claude.com/docs/ko/claude-directory.md)
- `병합` — `원문 확인` — "Custom commands have been merged into skills." (Extend Claude with skills)
- `같은 이름, 같은 동작` — `원문 확인` — "A file at .claude/commands/deploy.md and a skill at .claude/skills/deploy/SKILL.md both create /deploy and work the same way." (Extend Claude with skills)
- `기존 파일은 계속 동작` — `원문 확인` — "Your existing .claude/commands/ files keep working." (Extend Claude with skills)
- `옛 형식` — `원문 확인` — "a Markdown file in .claude/commands/ is the older format and still works." (Choose where skills load)
- `새 작업은 Skill로` — `원문 확인` — "Prefer a skill for new work, since skills also support supporting files." (Choose where skills load)
- `디렉터리 문서의 표현` — `원문 확인` — "Single-file prompts; same mechanism as skills" (File reference)
- 2.1.318 확인: `claude --help`의 `--disable-slash-commands`가 "Disable all skills and commands"라고 적혀 있어 두 가지를 한 스위치로 끈다.
- 수업에 쓸 점: "명령"과 "Skill"을 별개 장치로 가르치면 안 된다. 같은 파일 규약의 두 모양이다. 책임: 지침.
- 주의: `commands/` 파일은 `name`과 `paths` 필드를 쓰지 못한다(claude-directory의 Frontmatter fields by file 표). 내장 명령(`/help`, `/compact`)은 Skill이 아니다(skills 문서 도입 NOTE).

## I14 Output style

- 공식 문서: https://code.claude.com/docs/en/output-styles.md (한국어: https://code.claude.com/docs/ko/output-styles.md)
- `정의` — `원문 확인` — "An output style is a set of instructions that sets Claude's role, tone, and response format for every response in a session." (Output styles)
- `내장 스타일 수` — `원문 확인` — "Claude Code includes four built-in styles besides its default, and you can write your own." (Output styles)
- `강제가 아니다` — `원문 확인` — "An output style gives Claude instructions to follow. It doesn't guarantee that something always happens or never happens." (Output styles)
- `Default의 의미` — `원문 확인` — "Default means no output style is selected." (Default)
- `대소문자` — `원문 확인` — "The value is case-sensitive, so write the built-in names as Proactive, Concise, Explanatory, and Learning." (Change your output style)
- `설정 명령` — `원문 확인` — "run /output-style <style> to switch, for example /output-style concise." (Change your output style)
- `저장 위치` — `원문 확인` — "The command and both menus save your choice to .claude/settings.local.json at the local project level." (Change your output style)
- `사용자 정의 위치` — `원문 확인` — "User: ~/.claude/output-styles" (Create a custom output style)
- `사용자 정의 스타일이 지우는 것` — `원문 확인` — "custom output styles leave out Claude Code's section of built-in software engineering instructions, such as how to scope changes, write comments, and verify work, unless keep-coding-instructions is set to true." (How output styles work)
- `매 요청에 실린다` — `원문 확인` — "Claude Code sends the active style's instructions with every request." (How output styles work)
- `서브에이전트` — `원문 확인` — "Other subagents run their own system prompt, so styles don't change how they respond." (How output styles work)
- `파일 편집은 재시작` — `원문 확인` — "In the terminal, Claude Code reads style files when it starts, so if you create or edit one during a running session, restart Claude Code to pick up the change." (Create a custom output style)
- 2.1.318 확인: 대화형 전용이라 미확인(`/output-style`은 실행하지 않았다).
- 수업에 쓸 점: Output style은 "어떻게 답하는가"를 바꾸는 지침이고, 프로젝트에 대한 사실은 CLAUDE.md에 둔다. 사용자 정의 스타일은 `keep-coding-instructions`를 안 켜면 "작업 검증" 같은 내장 코딩 지침도 함께 빠진다. 책임: 지침, 검증.
- 주의: 내장 스타일은 Proactive, Concise, Explanatory, Learning 네 가지이고 Concise는 v2.1.237 이상, `/output-style` 명령은 v2.1.269 이상이 필요하다(같은 문서). 이전 자료에서 "Default/Explanatory/Learning 세 가지"로 가르쳤다면 어긋난다. Proactive 스타일은 권한 모드를 바꾸지 않는다(같은 문서 Proactive 절).

## I15 확장 장치 비교: CLAUDE.md, Skill, subagent, hook, MCP, plugin

- 공식 문서: https://code.claude.com/docs/en/features-overview.md (한국어: https://code.claude.com/docs/ko/features-overview.md)
- `확장 층` — `원문 확인` — "This guide covers the extension layer: features you add to customize what Claude knows, connect it to external services, and automate workflows." (Extend Claude Code)
- `역할 분담 한 문장` — `원문 확인` — "Each extension solves a different problem: CLAUDE.md handles always-on context, skills handle on-demand knowledge and workflows, MCP handles external connections, subagents handle isolation, and hooks handle automation." (Combine features)
- `CLAUDE.md 칸: 하는 일` — `원문 확인` — "Persistent context loaded every conversation" (Match features to your goal)
- `Skill 칸: 하는 일` — `원문 확인` — "Instructions, knowledge, and workflows Claude can use" (Match features to your goal)
- `Skill 칸: 쓸 때` — `원문 확인` — "Reusable content, reference docs, repeatable tasks" (Match features to your goal)
- `subagent 칸: 하는 일` — `원문 확인` — "Isolated execution context that returns summarized results" (Match features to your goal)
- `subagent 칸: 쓸 때` — `원문 확인` — "Context isolation, parallel tasks, specialized workers" (Match features to your goal)
- `MCP 칸` — `원문 확인` — "Connect to external services" (Match features to your goal)
- `hook 칸: 쓸 때` — `원문 확인` — "Automation that must run on every matching event" (Match features to your goal)
- `plugin` — `원문 확인` — "A plugin bundles skills, hooks, subagents, and MCP servers into a single installable unit." (Match features to your goal)
- `plugin을 쓸 때` — `원문 확인` — "Use plugins when you want to reuse the same setup across multiple repositories or distribute to others via a marketplace." (Match features to your goal)
- `CLAUDE.md냐 Skill이냐: 선택 기준` — `원문 확인` — "Put it in a skill if it's reference material Claude needs sometimes (API docs, style guides) or a workflow you trigger with /<name> (deploy, review, release)." (CLAUDE.md vs Skill)
- `CLAUDE.md 크기 기준` — `원문 확인` — "Rule of thumb: Keep CLAUDE.md under 200 lines. If it's growing, move reference content to skills or split into .claude/rules/ files." (CLAUDE.md vs Skill)
- `rules` — `원문 확인` — "Use rules to keep CLAUDE.md focused." (CLAUDE.md vs Rules vs Skills)
- `CLAUDE.md냐 Output style이냐` — `원문 확인` — "Use an output style if it's about the response itself and you might want it off again: length, format, how much Claude explains, or a different role such as a writing assistant." (CLAUDE.md vs Output style)
- `둘 다 강제가 아니다` — `원문 확인` — "Claude follows both as instructions, so neither is enforced. For anything that has to happen every time, use a hook." (CLAUDE.md vs Output style)
- `Skill냐 subagent냐` — `원문 확인` — "Use a subagent when you need context isolation or when your context window is getting full." (Skill vs Subagent)
- `Skill과 subagent의 정의` — `원문 확인` — "Skills are reusable content you can load into any context" (Skill vs Subagent)
- `MCP냐 Skill이냐` — `원문 확인` — "MCP gives Claude purpose-built tools for an external system, with the connection and authentication handled by the server." (MCP vs Skill)
- `Skill이 MCP에 더하는 것` — `원문 확인` — "Skills give Claude knowledge about how to use those tools effectively, plus workflows you can trigger with /<name>." (MCP vs Skill)
- `hook냐 Skill이냐` — `원문 확인` — "Use a hook when the action must happen the same way every time and doesn't need Claude to think." (Hook vs Skill)
- `Skill을 쓸 때` — `원문 확인` — "Use a skill when Claude should decide how to apply the steps, or when the content is knowledge rather than a script." (Hook vs Skill)
- `보장은 hook` — `원문 확인` — "If a rule must hold every time, make it a hook rather than a prompt instruction." (Hook vs Skill)
- `요청과 강제의 차이` — `원문 확인` — "in CLAUDE.md or a skill is a request, not a guarantee. A PreToolUse hook that blocks the edit is enforcement." (Hook vs Skill)
- `언제 무엇을 더하나` — `원문 확인` — "A repeated mistake or a recurring review comment is a CLAUDE.md edit, not a one-off correction in chat." (Build your setup over time)
- `층 쌓임: CLAUDE.md` — `원문 확인` — "CLAUDE.md files are additive: all levels contribute content to Claude's context simultaneously." (Understand how features layer)
- `층 쌓임: 충돌` — `원문 확인` — "When instructions conflict, Claude uses judgment to reconcile them." (Understand how features layer)
- `층 쌓임: Skill과 subagent` — `원문 확인` — "Skills and subagents override by name: when the same name exists at multiple levels, one definition wins based on priority (managed > user > project for skills; managed > CLI flag > project > user > plugin for subagents)." (Understand how features layer)
- `층 쌓임: hook` — `원문 확인` — "Hooks merge: all registered hooks fire for their matching events regardless of source." (Understand how features layer)
- 2.1.318 확인: 해당 없음(문서 서술). `claude plugin --help`에 `details` 하위 명령("Show a plugin's component inventory and projected token cost")이 있음을 확인했다.
- 수업에 쓸 점: 장치 선택 단계의 기준표다. 실패를 보고 "더 쓸 문장이 부족한가(CLAUDE.md), 가끔 필요한 절차인가(Skill), 격리가 필요한가(subagent), 예외 없이 막아야 하나(hook), 밖의 데이터인가(MCP)"를 순서대로 묻게 한다. 책임: 지침, 도구, 실행 제어.
- 주의: Skill과 subagent는 이름으로 덮어쓰고 CLAUDE.md는 이어 붙으며 hook은 합쳐진다(층 쌓임 절). 같은 "여러 층"이라도 규칙이 다르다. 비교 탭의 일부는 표 형태라 이 대장에서는 칸 단위로 인용했다.

## I16 장치별 맥락 비용

- 공식 문서: https://code.claude.com/docs/en/features-overview.md (한국어: https://code.claude.com/docs/ko/features-overview.md)
- `비용 일반론` — `원문 확인` — "Every feature you add consumes some of Claude's context." (Understand context costs)
- `너무 많으면` — `원문 확인` — "Too much can fill up your context window, but it can also add noise that makes Claude less effective; skills may not trigger correctly, or Claude may lose track of your conventions." (Understand context costs)
- `CLAUDE.md 적재량` — `원문 확인` — "Full content of each file that loads at session start" (Context cost by feature)
- `Output style 적재량` — `원문 확인` — "The active style's full instructions; nothing for the Default style" (Context cost by feature)
- `Skill 적재량` — `원문 확인` — "Descriptions at start, full content when used" (Context cost by feature)
- `MCP 적재량` — `원문 확인` — "Tool names; full schemas on demand" (Context cost by feature)
- `hook 적재량` — `원문 확인` — "Zero, unless hook returns additional context" (Context cost by feature)
- `Skill의 설명을 맥락에서 빼기` — `원문 확인` — "Set disable-model-invocation: true in a skill's frontmatter to keep its description out of Claude's context." (Context cost by feature)
- `부작용 있는 Skill` — `원문 확인` — "Use disable-model-invocation: true for skills with side effects. This saves context and ensures they run only when you name them." (Understand how features load)
- `subagent의 시작 맥락` — `원문 확인` — "The built-in Explore and Plan agents start with neither" (Understand how features load)
- 2.1.318 확인: 해당 없음(문서 서술). 도구별 토큰 수는 대화형 `/context all`이라 미확인.
- 수업에 쓸 점: "많이 넣을수록 안전하다"가 틀린 이유를 보여 준다. 항상 적재되는 지침(CLAUDE.md, Output style)과 필요할 때 적재되는 지침(Skill, 경로 한정 규칙)을 가르는 근거다. 책임: 지침.
- 주의: 비용 열은 "맥락 비용"이며 돈이 아니다. 표 아래 별표 설명은 `disable-model-invocation`이 설명도 맥락에서 뺀다고 한다. 이 점은 I12의 표와 같은 말이다.

## I17 검증 기준을 지침으로 주기 (best-practices)

- 공식 문서: https://code.claude.com/docs/en/best-practices.md (한국어: https://code.claude.com/docs/ko/best-practices.md)
- `끝났다고 했는데 아닌 이유` — `원문 확인` — "Claude said it was done and it wasn't quite, usually because it had no way to check its own work." (Best practices for Claude Code)
- `끝의 기준` — `원문 확인` — "Claude stops when the work looks done." (Give Claude a check to run)
- `통과/실패 확인을 줘라` — `원문 확인` — "Give Claude something it can run that comes back pass or fail. Once it has that, it can keep going on its own and you don't have to watch." (Give Claude a check to run)
- `CLAUDE.md의 가장 쓸모 있는 한 줄` — `원문 확인` — "If your repo already has one of these, the single most useful line in your CLAUDE.md is the command that runs it." (Give Claude a check to run)
- `근거를 요구하라` — `원문 확인` — "Whichever option you use, ask Claude for evidence: the command it ran and its output, or the screenshot." (Give Claude a check to run)
- `못 본 세션` — `원문 확인` — "For a session you weren't watching, it's also the only evidence you have." (Give Claude a check to run)
- `새 눈의 검토` — `원문 확인` — "reviews the diff in a fresh subagent that never saw your conversation." (Give Claude a check to run)
- `Stop 훅은 강제` — `원문 확인` — "This one is enforced by Claude Code (the harness), so the turn doesn't end until the typecheck passes or the block limit is reached." (Give Claude a check to run)
- `Stop 훅 상한` — `원문 확인` — "If the hook blocks eight stops in a row with no tool call between them, Claude Code overrides the next block and ends the turn." (Enforce the check with a Stop hook)
- `검토 지시문의 함정` — `원문 확인` — "A reviewer that's asked to find problems will always find something." (Review against your spec)
- 2.1.318 확인: 대화형 전용이라 미확인(`/goal`, `/code-review`, `/verify`는 실행하지 않았다).
- 수업에 쓸 점: 검증 기준(통과/실패로 돌아오는 검사)을 지침에 넣는 방법이다. 자기 확인, `/goal`, `Stop` 훅, 남이 한 검토가 강도가 다른 네 단계라는 점을 보여 준다. 책임: 지침, 검증.
- 주의: `/goal`은 별도 모델이 매 턴 조건을 확인하고 `/code-review`는 하위 에이전트를 쓰므로 모델 호출이 늘어난다(같은 문서). 실행 전에 규모를 고지한다.

## I18 설계, 조기 교정 (best-practices)

- 공식 문서: https://code.claude.com/docs/en/best-practices.md (한국어: https://code.claude.com/docs/ko/best-practices.md)
- `구체적 프롬프트` — `원문 확인` — "A specific prompt helps for the same reason, because it gives Claude information it doesn't already have." (Write a specific prompt)
- `먼저 인터뷰` — `원문 확인` — "Interview me until you could write the spec, then write it to SPEC.md." (Brainstorm with Claude first)
- `새 세션에서 짓는다` — `원문 확인` — "Once SPEC.md exists, start a fresh session to build from it, so the build begins with a clean context and a written definition of done." (Brainstorm with Claude first)
- `첫 1분을 본다` — `원문 확인` — "Watch the first minute, press Esc the moment Claude drifts, and after two failed corrections run /clear and write a better prompt instead of a third." (Steer the session)
- `Esc` — `원문 확인` — "Esc stops Claude mid-action and keeps everything up to that point, so you can redirect without losing work." (Steer the session)
- `세 번째 교정 대신` — `원문 확인` — "/clear plus one new prompt that folds in what you learned works better almost every time." (Steer the session)
- `되돌리기의 한계` — `원문 확인` — "Checkpoints cover the files Claude edited with its own file tools in your main conversation, so a file that only a Bash command touched isn't restored." (Steer the session)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: 목표·범위·끝 기준을 SPEC.md 같은 파일로 먼저 쓰고 새 세션에서 짓는 흐름의 공식 근거다. 두 번 교정해도 틀리면 대화를 비우고 다시 쓴다. 책임: 지침, 상태.
- 주의: 이 판의 `best-practices`에는 "탐색, 계획, 코딩" 순서를 가르치는 절이나 plan mode 설명이 없다. 위 인터뷰 후 SPEC.md 흐름과 `Shift+Tab`으로 권한 모드를 바꾼다는 한 줄(Change the permission mode 절)만 있다. plan mode는 `permission-modes` 문서(다른 대장)에서 확인한다.

## I19 `.claude` 디렉터리 파일 지도

- 공식 문서: https://code.claude.com/docs/en/claude-directory.md (한국어: https://code.claude.com/docs/ko/claude-directory.md)
- `대부분 두 파일` — `원문 확인` — "Most users only edit CLAUDE.md and settings.json." (Explore the .claude directory)
- `나머지는 선택` — `원문 확인` — "The rest of the directory is optional: add skills, rules, or subagents as you need them." (Explore the .claude directory)
- `공유 범위` — `원문 확인` — "Commit project files to git to share them with your team; files in ~/.claude are personal configuration that applies across all your projects." (Explore the .claude directory)
- `CLAUDE.md 행` — `원문 확인` — "Instructions loaded every session" (File reference)
- `rules 행` — `원문 확인` — "Topic-scoped instructions, optionally path-gated" (File reference)
- `skills 행` — `원문 확인` — "Reusable prompts invoked with /name or auto-invoked" (File reference)
- `권한과 훅은 settings` — `원문 확인` — "Allow or block specific tool calls" (Choose the right file)
- `output style 행` — `원문 확인` — "Change how Claude formats responses" (Choose the right file)
- `Skill frontmatter 필드 목록` — `원문 확인` — "name, description, when_to_use, argument-hint, arguments, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, model, effort, context, agent, background, hooks, paths, shell, metadata, license, compatibility" (Frontmatter fields by file)
- `output style frontmatter 필드 목록` — `원문 확인` — "name, description, keep-coding-instructions, force-for-plugin" (Frontmatter fields by file)
- 2.1.318 확인: 대화형 전용이라 미확인. 이 저장소의 `.claude/` 실제 내용은 이 대장에서 조사하지 않았다.
- 수업에 쓸 점: "무엇을 바꾸려면 어느 파일인가"를 한 장으로 보여 주므로 지침 층과 실행 제어 층(settings)이 서로 다른 파일임을 구분하게 한다. 책임: 지침, 실행 제어.
- 주의: Skill 필드 목록은 skills 문서의 frontmatter 표와 같은 이름들이다. 두 문서가 어긋나면 skills 문서와 코드를 따르고 차이를 알려야 한다.

## 수업에 쓸 때 주의

- 이 대장은 지침 책임 담당 페이지 여섯 개만 다룬다. 권한·훅·plan mode(실행 제어), 세션 저장(상태), 기록은 다른 대장의 몫이다. I8과 I15의 hook 인용도 "지침과 강제의 구분"을 위한 것이다.
- 대화형으로만 확인되는 동작(`/init`, `/memory`, `/context all`, `/doctor prompt-audit`, `/output-style`, `/config`)은 이 대장에서 실행하지 않았다. 수업에서 시연하려면 먼저 수강생 환경에서 한 번 확인해야 한다.
- 버전에 민감한 사실이 많다: AGENTS.md 직접 읽기 v2.1.277, `/doctor prompt-audit` v2.1.283, `/output-style` v2.1.269, Concise 스타일 v2.1.237, 온디맨드 파일 크기 상한 v2.1.309. 이 컴퓨터는 2.1.318이라 모두 충족하지만 수강생 버전은 `claude --version`으로 확인한다.
- 문서는 자주 바뀐다. 공식 문서와 수업 자료가 다르면 이 저장소 원칙대로 직접 확인한 쪽을 따르고, 차이를 수강생에게 알린다.
- `/doctor prompt-audit`, `/goal`, `/code-review`처럼 모델을 부르는 명령을 수업 활동에 넣을 때는 실행 직전에 규모를 한 줄로 고지한다.
Quotes verified: 163/163
