# Claude Code 근거 대장 — 상태 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: `https://code.claude.com/docs/en/<page>.md`를 `curl -sL`로 내려받아 `python3 -I` 스크립트로 대조했다. 마크다운 링크 `[text](url)`는 text만 남기고, 백틱과 굵은 글씨 표시(`**`)를 지우고, 공백을 하나로 모은 뒤 인용문이 부분 문자열인지 확인했다. WebFetch(요약 모델)는 쓰지 않았다.
- 사용한 페이지: `how-claude-code-works`, `context-window`, `sessions`, `checkpointing`, `memory`(auto memory 부분만), `costs`(`/compact`, `/clear`, auto-compaction, 컨텍스트 줄이기 부분만). 모두 `https://code.claude.com/docs/en/<page>.md` 판이다.
- 한국어 URL은 `https://code.claude.com/docs/_llms/ko.txt` 목록에 있는 것만 적었다. 한국어 문장은 인용하지 않았다.
- 로컬 확인: `claude --version`은 `2.1.318 (Claude Code)`였다. `claude --help`의 도움말 출력만 봤고 모델을 부르는 실행(`claude -p`, 대화형 실행)은 하지 않았다. 표의 `|` 칸은 원문에서 그대로 두었다.
- 수준 표기: `원문 확인`은 위 대조를 통과한 인용문이다. 인용 뒤 괄호는 원문 절 제목이다.

## S1 에이전트 루프(세 단계)

- 공식 문서: https://code.claude.com/docs/en/how-claude-code-works.md (한국어: https://code.claude.com/docs/ko/how-claude-code-works.md)
- `세 단계` — `원문 확인` — "it works through three phases: gather context, take action, and verify results." (The agentic loop)
- `사용자도 루프의 일부` — `원문 확인` — "You can interrupt at any point to steer Claude in a different direction, provide additional context, or ask it to try a different approach." (The agentic loop)
- 2.1.318 확인: 해당 없음(설명 문서).
- 수업에 쓸 점: 지침 없이 "알아서 해 줘"라고 맡기면 어느 단계에서 틀렸는지 못 찾는다. 세 단계 이름으로 실패 지점을 말하게 한다. 검증이 루프의 한 단계라는 근거다. 책임: 검증, 실행 제어.
- 주의: 문서는 이 단계들이 "blend together"한다고도 적는다. 순서가 고정된 파이프라인이 아니다.

## S2 Claude Code는 무엇인가(모델과 도구, 하네스 표현)

- 공식 문서: https://code.claude.com/docs/en/how-claude-code-works.md (한국어: https://code.claude.com/docs/ko/how-claude-code-works.md)
- `두 구성요소` — `원문 확인` — "The agentic loop is powered by two components: models that reason and tools that act." (The agentic loop)
- `하네스 정의` — `원문 확인` — "Claude Code is the layer around the model that provides the tools and manages the context the model sees. This surrounding layer is what the term agentic harness refers to." (The agentic loop)
- `도구가 있어야 에이전트` — `원문 확인` — "Without tools, Claude can only respond with text." (Tools)
- 2.1.318 확인: 해당 없음.
- 수업에 쓸 점: 공식 문서가 직접 "agentic harness"라는 말을 쓰므로, 수업의 하네스 정의를 외부 블로그가 아니라 Claude Code 문서로 세울 수 있다. 책임: 전체(여섯 책임의 출발점).
- 주의: 문서는 하네스를 "모델 둘레의 층"으로만 정의한다. 여섯 책임은 문서에 없고 수업의 분석 틀이다.

## S3 컨텍스트 윈도우에 채워지는 것과 `/context`

- 공식 문서: https://code.claude.com/docs/en/context-window.md , https://code.claude.com/docs/en/how-claude-code-works.md (한국어: https://code.claude.com/docs/ko/context-window.md / https://code.claude.com/docs/ko/how-claude-code-works.md)
- `구성` — `원문 확인` — "Claude's context window holds your conversation history, file contents, command outputs, CLAUDE.md, auto memory, loaded skills, and system instructions." (The context window)
- `시작 시 로드` — `원문 확인` — "Before you type anything: CLAUDE.md, auto memory, MCP tool names, and skill descriptions all load into context." (What the timeline shows)
- `/context` — `원문 확인` — "run /context for a live breakdown by category with optimization suggestions, including which CLAUDE.md and auto memory files loaded." (Check your own session)
- 2.1.318 확인: 대화형 전용이라 미확인(`/context`는 세션 안 슬래시 명령).
- 수업에 쓸 점: "분명히 말했는데 모른다"는 실패의 원인을 컨텍스트에 실제로 올라와 있는지 `/context`로 확인하게 한다. 책임: 상태, 지침.
- 주의: 문서의 타임라인 숫자는 "representative" 대표값이다. 실측값으로 인용하지 않는다.

## S4 compaction 뒤에 남는 것과 다시 읽히는 것

- 공식 문서: https://code.claude.com/docs/en/context-window.md#what-survives-compaction , https://code.claude.com/docs/en/memory.md (한국어: https://code.claude.com/docs/ko/context-window.md / https://code.claude.com/docs/ko/memory.md)
- `루트 CLAUDE.md` — `원문 확인` — "Project-root CLAUDE.md survives compaction: after /compact, Claude re-reads it from disk and re-injects it into the session." (Instructions seem lost after /compact)
- `하위 CLAUDE.md와 paths 규칙` — `원문 확인` — "Path-scoped rules and nested CLAUDE.md files load into message history when Claude reads, writes, or edits their trigger file, so compaction summarizes them away with everything else." (What survives compaction)
- `읽은 파일` — `원문 확인` — "Right after compaction, Claude Code re-reads up to five of the files Claude has read or edited in the session, choosing the ones modified most recently." (What survives compaction)
- `skill 본문` — `원문 확인` — "Skill bodies are re-injected after compaction, but large skills are truncated to fit the per-skill cap, and the oldest invoked skills are dropped once the total budget is exceeded." (What survives compaction)
- `skill 한도(표 행)` — `원문 확인` — "Re-injected, capped at 5,000 tokens per skill and 25,000 tokens total; oldest dropped first" (What survives compaction, 표의 Invoked skill bodies 행)
- 2.1.318 확인: 대화형 전용이라 미확인(compaction은 모델 호출이 필요하다).
- 수업에 쓸 점: 대화로만 준 지시는 compaction에서 사라지고 파일에 쓴 지시는 다시 읽힌다. 다음 세션과 compaction 뒤에 무엇이 상속되는지 가르는 기준이다. 책임: 상태, 지침.
- 주의: skill 설명 재주입은 표에서 v2.1.304 이상을 요구한다. 한도 5,000/25,000 토큰은 문서 표기이며 2.1.318에서 직접 측정하지 않았다.

## S5 auto-compaction

- 공식 문서: https://code.claude.com/docs/en/how-claude-code-works.md#when-context-fills-up , https://code.claude.com/docs/en/context-window.md (한국어: https://code.claude.com/docs/ko/how-claude-code-works.md / https://code.claude.com/docs/ko/context-window.md)
- `자동 요약` — `원문 확인` — "Claude Code manages context automatically as you approach the limit. It compacts the conversation into a summary." (When context fills up)
- `손실` — `원문 확인` — "The summary keeps your requests and key code snippets, but detailed instructions from early in the conversation may be lost." (When context fills up)
- `반복 중단` — `원문 확인` — "Claude Code stops auto-compacting after a few attempts and shows an error instead of looping." (When context fills up)
- `창이 꽉 차도 세션은 안 끝남` — `원문 확인` — "Claude Code compacts automatically as you approach the limit, so a full context window doesn't end your session." (When your context fills up)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: 긴 작업 중간에 초기 지시가 흐려지는 실패를 설명한다. 지시를 CLAUDE.md나 계획 파일로 옮겨 두는 이유다. 책임: 상태.
- 주의: 자동 compaction이 걸리는 지점은 모델과 설정에 따라 다르다(문서가 model-config 페이지로 넘긴다). 이 대장은 임계값 숫자를 적지 않는다.

## S6 `/compact` 지시문, `/clear`

- 공식 문서: https://code.claude.com/docs/en/how-claude-code-works.md#when-context-fills-up , https://code.claude.com/docs/en/costs.md#manage-context-proactively (한국어: https://code.claude.com/docs/ko/how-claude-code-works.md / https://code.claude.com/docs/ko/costs.md)
- `포커스를 줘서 compact` — `원문 확인` — "or run /compact with a focus (like /compact focus on the API changes)." (When context fills up)
- `수동 compact 효과` — `원문 확인` — "The summary keeps what you choose instead of what the automatic pass guesses is important." (When your context fills up)
- `/clear` — `원문 확인` — "Clear between tasks: Use /clear to start fresh when switching to unrelated work." (Manage context proactively)
- `clear 전 이름 붙이기` — `원문 확인` — "Use /rename before clearing so you can find the session later, then /resume to return to it." (Manage context proactively)
- 2.1.318 확인: 대화형 전용이라 미확인.
- 수업에 쓸 점: 무엇을 남길지 사람이 정하면 요약이 중요한 것을 놓치는 실패를 줄인다. `/clear`는 이어받을 것이 없는 새 시작이고, 이름을 붙이면 되돌아올 수 있다. 책임: 상태.
- 주의: 문서는 CLAUDE.md에 "Compact instructions" 절을 두는 방법도 적는다. 이 절이 2.1.318에서 어떻게 동작하는지는 직접 확인하지 않았다.

## S7 컨텍스트와 비용(costs)

- 공식 문서: https://code.claude.com/docs/en/costs.md (한국어: https://code.claude.com/docs/ko/costs.md)
- `컨텍스트가 비용` — `원문 확인` — "Token costs scale with context size: the more context Claude processes, the more tokens you use." (Reduce token usage)
- `compact도 비용` — `원문 확인` — "/compact reads the conversation it summarizes, so compacting a large context is itself a large request." (비용이 늘어나는 요인 목록의 Compaction 항목)
- `clear는 무료` — `원문 확인` — "When you want a fresh start instead of continuity, /clear costs nothing" (같은 목록)
- 2.1.318 확인: 해당 없음.
- 수업에 쓸 점: 컨텍스트를 줄이는 행동에 비용이 든다는 점을 미리 고지하게 한다. 책임: 상태, 실행 제어.
- 주의: 이 절 두 번째, 세 번째 인용은 절 제목이 아니라 목록 항목이라 괄호에 위치를 풀어 적었다. 비용 수치는 이 대장에 적지 않는다.

## S8 `--continue`, `--resume`

- 공식 문서: https://code.claude.com/docs/en/sessions.md#resume-a-session (한국어: https://code.claude.com/docs/ko/sessions.md)
- `같은 session ID로 이어감` — `원문 확인` — "Resuming a session with claude --continue or claude --resume reopens it under the same session ID and appends new messages to the existing conversation." (Resume or fork sessions)
- `--continue` — `원문 확인` — "Reopens the most recent session in the current directory" (Resume a session 표)
- `이름으로 재개` — `원문 확인` — "Resumes the named session directly" (Resume a session 표)
- 2.1.318 확인: `claude --help`에 `-c, --continue`, `--resume`, `--from-pr [value]`, `--fork-session`, `-n, --name <name>`이 나온다.
- 수업에 쓸 점: "어제 하던 일"을 이어받는 두 길(같은 세션 이어가기, 새 세션 시작)을 구분해야 한다. 이어받기가 곧 상태의 상속이다. 책임: 상태.
- 주의: `claude -p`·Agent SDK·`/loop`로 만든 세션은 picker와 `--continue`에서 빠진다(Where the session picker looks). 실습에서 `-p`로 만든 세션을 `--continue`로 찾으려 하지 않는다.

## S9 재개된 세션이 되살리는 것과 못 되살리는 것

- 공식 문서: https://code.claude.com/docs/en/sessions.md#what-a-resumed-session-restores , https://code.claude.com/docs/en/how-claude-code-works.md (한국어: https://code.claude.com/docs/ko/sessions.md)
- `세션은 서로 독립` — `원문 확인` — "Sessions are independent. Each new session starts with a fresh context window, without the conversation history from previous sessions." (Work with sessions)
- `되살리는 범위` — `원문 확인` — "When Claude Code loads a conversation from its transcript, the resumed session restores the conversation along with the state saved in it:" (What a resumed session restores)
- `플래그는 일부만` — `원문 확인` — "Not every configuration flag from the original launch is restored." (What a resumed session restores)
- 2.1.318 확인: 대화형 전용이라 미확인(재개 동작).
- 수업에 쓸 점: 새 세션은 빈 컨텍스트로 시작한다는 사실이 "다음 세션이 상속하는 것"의 출발점이다. `--mcp-config`, `--add-dir` 등은 재개 때 다시 주어야 한다. 책임: 상태, 도구.
- 주의: 이 절의 인용 중 세 번째 이후 항목(permission mode 복원 규칙 등)은 조건이 많아 이 대장에서 풀어 쓰지 않았다. 수업에서 쓰려면 원 페이지를 다시 읽는다.

## S10 세션 이름 붙이기

- 공식 문서: https://code.claude.com/docs/en/sessions.md#name-your-sessions (한국어: https://code.claude.com/docs/ko/sessions.md)
- `목적` — `원문 확인` — "Give sessions descriptive names so they're findable in the session picker and resumable by name." (Name your sessions)
- `기본 이름은 재개 손잡이가 아님` — `원문 확인` — "The default isn't a resume handle." (Name your sessions)
- 2.1.318 확인: `claude --help`에 `-n, --name <name>`이 "Set a display name for this session"으로 나온다. `/rename`은 대화형 전용이라 미확인.
- 수업에 쓸 점: 나중에 같은 작업을 찾아 이어받으려면 이름이 필요하다. 이름 없는 세션은 기본 이름으로 `--resume` 못 한다. 책임: 상태, 기록.
- 주의: 이름 없는 세션의 생성 제목은 작은 모델이 첫 프롬프트로 만든다(문서 설명). 즉 제목 생성에도 모델 호출이 있다.

## S11 세션 분기(fork)

- 공식 문서: https://code.claude.com/docs/en/sessions.md#branch-a-session (한국어: https://code.claude.com/docs/ko/sessions.md)
- `분기 정의` — `원문 확인` — "Branching creates a copy of the conversation so far and switches you into it, leaving the original intact." (Branch a session)
- `명령줄에서` — `원문 확인` — "From the command line, combine --continue or --resume with --fork-session:" (Branch a session)
- `새 ID` — `원문 확인` — "Forking with --fork-session or /branch copies the history into a new session ID, leaving the original unchanged." (Resume or fork sessions)
- 2.1.318 확인: `claude --help`에 `--fork-session`이 "When resuming, create a new session ID"로 나온다. `/branch`는 대화형 전용이라 미확인.
- 수업에 쓸 점: 다른 접근을 시험하다 원래 세션을 망가뜨리는 실패를 막는다. 코드는 복구 대상이 아니고 대화만 분기된다는 점은 S14와 함께 가르친다. 책임: 상태.
- 주의: 분기는 대화를 복사할 뿐 작업 폴더의 파일은 복사하지 않는다(이 문장은 인용 두 문장을 합친 해석이다. 파일은 worktree 문서를 따로 봐야 한다).

## S12 transcript 위치와 형식 경고

- 공식 문서: https://code.claude.com/docs/en/sessions.md#where-transcripts-are-stored , https://code.claude.com/docs/en/how-claude-code-works.md (한국어: https://code.claude.com/docs/ko/sessions.md)
- `위치` — `원문 확인` — "By default, Claude Code stores transcripts as JSONL at ~/.claude/projects/<project>/<session-id>.jsonl, where <project> is your working directory path with non-alphanumeric characters replaced by -." (Where transcripts are stored)
- `형식은 내부용` — `원문 확인` — "The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release." (Where transcripts are stored)
- `대안` — `원문 확인` — "To build on session data, use /export or the script interfaces instead." (Where transcripts are stored)
- `쓰는 내용` — `원문 확인` — "Each message, tool use, and result is written to a plaintext JSONL file under ~/.claude/projects/" (Work with sessions)
- 2.1.318 확인: 해당 없음(파일 위치는 설명 문서 기준). `claude --help`에서 `/export`는 확인하지 않았다.
- 수업에 쓸 점: 실패 원인을 사후에 설명하려면 기록이 필요하고, 그 기록은 JSONL이지만 형식을 보장하지 않는다. 파싱 스크립트가 버전마다 깨질 수 있다고 알려야 한다. 책임: 기록, 상태.
- 주의: 수강생의 transcript에는 대화 전체와 도구 결과가 들어 있다. 내용이 나오는 옵션은 Claude Code 밖에서만 쓰라는 저장소 규칙과 같이 간다.

## S13 checkpoint가 추적하는 것

- 공식 문서: https://code.claude.com/docs/en/checkpointing.md (한국어: https://code.claude.com/docs/ko/checkpointing.md)
- `자동 추적` — `원문 확인` — "Claude Code automatically tracks Claude's file edits as you work, allowing you to quickly undo changes and rewind to previous states if anything gets off track." (Checkpointing 도입부)
- `생성 시점` — `원문 확인` — "Every prompt you send that starts a turn creates a new checkpoint" (Automatic tracking)
- `대화와 함께 저장` — `원문 확인` — "Claude Code saves checkpoints with the conversation, so you can still run /rewind after you resume a session" (Automatic tracking)
- `원격 작업은 대상 아님` — `원문 확인` — "Actions that affect remote systems (databases, APIs, deployments) can't be checkpointed." (Undo changes with checkpoints)
- 2.1.318 확인: 대화형 전용이라 미확인(checkpoint는 세션 안에서만 만들어지고 `claude --help`에 대응 플래그가 없다).
- 수업에 쓸 점: 사용자 프롬프트 한 번이 되돌림 지점 하나가 된다. 어떤 변경은 추적 밖이라는 한계(S15)와 짝으로 가르쳐야 "되돌릴 수 있다"는 과신이 안 생긴다. 책임: 상태, 실행 제어.
- 주의: 추적 대상은 Claude의 파일 편집 도구가 바꾼 파일이다. 데이터베이스·API·배포는 포함되지 않는다.

## S14 되감기: `/rewind`, `Esc Esc`와 복원 대상

- 공식 문서: https://code.claude.com/docs/en/checkpointing.md#rewind-and-summarize (한국어: https://code.claude.com/docs/ko/checkpointing.md)
- `여는 방법` — `원문 확인` — "Run /rewind, or press Esc twice when the prompt input is empty, to open the rewind menu." (Rewind and summarize)
- `코드와 대화 모두` — `원문 확인` — "Restore code and conversation: revert both code and conversation to that point" (Rewind and summarize)
- `대화만` — `원문 확인` — "Restore conversation: rewind to that message while keeping current code" (Rewind and summarize)
- `코드만` — `원문 확인` — "Restore code: revert file changes while keeping the conversation" (Rewind and summarize)
- `요약` — `원문 확인` — "Summarize from here: compress the conversation from this point forward into a summary, freeing context window space" (Rewind and summarize)
- `입력창에 글이 있을 때` — `원문 확인` — "If the prompt input contains text, double Esc clears it instead of opening the menu." (Rewind and summarize)
- 2.1.318 확인: 대화형 전용이라 미확인(`/rewind`와 `Esc Esc`는 세션 안 동작).
- 수업에 쓸 점: 복원 대상(코드, 대화, 둘 다)을 고르는 기준이 실패 유형이다. 코드만 틀렸으면 코드만 되감아 대화의 맥락을 지키고, 대화가 틀어졌으면 대화를 되감는다. 책임: 상태, 검증.
- 주의: Restore code 두 선택지는 선택한 지점 뒤에 추적된 파일 변경이 있을 때만 나온다. Summarize는 파일을 바꾸지 않고 요약만 한다.

## S15 checkpoint의 문서화된 한계

- 공식 문서: https://code.claude.com/docs/en/checkpointing.md#limitations (한국어: https://code.claude.com/docs/ko/checkpointing.md)
- `Bash만 바꾼 파일` — `원문 확인` — "A file that only Bash commands changed isn't tracked and stays as it is. To revert it, use version control, such as Git." (Bash command changes not tracked)
- `외부 변경` — `원문 확인` — "Manual changes you make to files outside of Claude Code and edits from other concurrent sessions are normally not captured, unless they happen to modify the same files as the current session." (External changes not tracked)
- `하위 에이전트` — `원문 확인` — "Any other subagent: rewinding restores only the files Claude had already edited in your conversation." (Subagent edits not restored)
- `symlink` — `원문 확인` — "Checkpointing doesn't rewind symlinked or hard-linked files." (Symlinked and hard-linked paths not restored)
- `버전 관리 대체 아님` — `원문 확인` — "Checkpoints are designed for quick, session-level recovery." (Not a replacement for version control)
- `git을 써야 하는 이유` — `원문 확인` — "For permanent version history and collaboration, continue using version control, such as Git, for commits, branches, and long-term history." (Not a replacement for version control)
- 2.1.318 확인: 대화형 전용이라 미확인. 한계는 문서 기준이다.
- 수업에 쓸 점: 같은 `sed -i`라도 Claude가 먼저 편집 도구로 고친 파일은 되감기에 포함되고, Bash만 건드린 파일은 빠진다. 이 경계 때문에 큰 변경 전에는 git 커밋이 상태의 진짜 안전판이다. 책임: 상태, 실행 제어, 검증.
- 주의: Bash 조항은 문장이 미묘하다. 문서는 "Claude가 이미 편집 도구로 고친 파일이면, 그 뒤 Bash가 바꾼 내용도 되감긴다"고 적는다. 위 인용은 그 반대편(Bash만 건드린 파일)이다. 수업에서 "Bash 변경은 전부 안 된다"로 단순화하면 틀린다.

## S16 checkpoint 보존 기간

- 공식 문서: https://code.claude.com/docs/en/checkpointing.md#automatic-tracking (한국어: https://code.claude.com/docs/ko/checkpointing.md)
- `개수 한도` — `원문 확인` — "Claude Code keeps file snapshots for the 100 most recent checkpoints in a session." (Automatic tracking)
- `보존 기간` — `원문 확인` — "Claude Code deletes a session's file snapshots in the retention sweep, by default about 30 days after the session last saved one." (Automatic tracking)
- `더 오래 보관` — `원문 확인` — "To keep snapshots longer, set cleanupPeriodDays." (Automatic tracking)
- 2.1.318 확인: 해당 없음(저장 정책은 설명 문서 기준).
- 수업에 쓸 점: 오래된 세션을 재개해 되감으면 실패할 수 있다. "일주일 뒤에 돌아와 되감기"를 상태 계약에 쓰려면 기간을 확인해야 한다. 책임: 상태.
- 주의: 같은 30일이 transcript 보존에도 쓰이지만(sessions의 `cleanupPeriodDays` 표) 이 대장에서는 checkpoint snapshot 문장만 인용했다.

## S17 auto memory

- 공식 문서: https://code.claude.com/docs/en/memory.md#auto-memory (한국어: https://code.claude.com/docs/ko/memory.md)
- `기본값` — `원문 확인` — "Auto memory is on by default in local sessions." (Enable or disable auto memory)
- `위치와 worktree 공유` — `원문 확인` — "Each project gets its own memory directory at ~/.claude/projects/<project>/memory/. The <project> path is derived from the git repository, so all worktrees and subdirectories within the same repo share one auto memory directory." (Storage location)
- `시작 시 로드량` — `원문 확인` — "The first 200 lines of MEMORY.md, or the first 25KB, whichever comes first, are loaded at the start of every conversation." (How it works)
- `주제 파일은 안 올림` — `원문 확인` — "Claude Code doesn't load topic files such as user_role.md or feedback_testing.md at startup." (How it works)
- `기계 로컬` — `원문 확인` — "Auto memory is machine-local." (Storage location)
- `transcript 정리에서 제외` — `원문 확인` — "MEMORY.md and topic files stay until you or Claude edits or deletes them." (Storage location)
- 2.1.318 확인: 대화형 전용이라 미확인(`/memory` 토글). 환경 변수 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`은 문서 기준이다.
- 수업에 쓸 점: 다음 세션이 저절로 상속하는 내용이 MEMORY.md의 앞부분뿐임을 알려 준다. 중요한 계약은 CLAUDE.md나 저장소 파일에 둬야 하고, 기억에 맡기면 다른 기계에서 사라진다. 책임: 상태.
- 주의: 이 저장소 수강생의 실습 폴더는 저장소 밖에 만든다. auto memory의 `<project>`는 git 저장소에서 정해지고 transcript의 `<project>`는 작업 디렉터리 경로에서 정해져 서로 다를 수 있다(web.md 6장 주의와 같은 해석). 저장소 밖 폴더가 git 저장소가 아니면 프로젝트 루트를 쓴다는 문장이 문서에 있다.

## 수업에 쓸 때 주의

- 대화형 전용 기능(`/context`, `/compact`, `/rewind`, `Esc Esc`, `/branch`, `/memory`)은 `claude --help`로 확인할 수 없고 이 대장은 문서 원문까지만 확인했다. 수업 전에 저자가 한 번 손으로 확인해야 한다.
- S15의 Bash 조항은 단순화하면 틀린다. "Claude가 편집 도구로 고친 파일이면 이후 Bash 변경도 되감긴다. Bash만 건드린 파일은 추적되지 않는다"로 정확히 말한다.
- compaction 임계값과 skill 한도 숫자(5,000/25,000 토큰, 파일 다섯 개)는 문서 표기다. 2.1.318에서 직접 측정한 값이 아니다.
- transcript JSONL 형식은 내부용이라고 문서가 경고한다. 파싱 실습은 버전 의존으로 표시한다.
- `/compact`는 모델 호출을 쓰고, 제목 생성이나 `/insights`도 토큰을 쓴다. `/clear`는 비용이 없다. 실습 전 규모를 고지한다.
- 세션과 checkpoint는 로컬 파일이다. 같은 이름의 문서 서술이 클라우드·데스크톱·VS Code에서 다를 수 있다. 이 대장은 CLI만 다룬다.

Quotes verified: 64/64
