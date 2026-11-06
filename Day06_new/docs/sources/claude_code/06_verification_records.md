# Claude Code 근거 대장 — 검증·기록 (확인일 2026-11-06, Claude Code 2.1.318)

## 0. 확인 방법

- 방법: 각 페이지의 `.md` 판(`https://code.claude.com/docs/en/<page>.md`)을 `curl -sL`로 내려받고, 마크다운 링크 `[text](url)`를 text로 바꾸고 공백을 하나로 합친 뒤 인용문이 부분 문자열인지 `python3 -I` 스크립트로 대조했다. 큰따옴표 인용문은 모두 대조를 통과한 것만 실었고 WebFetch(요약 모델)는 쓰지 않았다. 인용 뒤 괄호는 원문의 절 제목이다.
- 사용한 페이지: `code-review-local`, `plugin-evals`, `monitoring-usage`, `costs`, `debug-your-config`, `analytics`, 그리고 `/insights` 재확인용 `commands`, `claude-directory` (모두 `https://code.claude.com/docs/en/<page>`).
- 한국어 URL은 `https://code.claude.com/docs/_llms/ko.txt` 목록에 있는 것만 적었고 한국어 문장은 인용하지 않았다. 목록에 없는 페이지는 `목록에 없음`으로 적었다.
- 로컬 확인: `claude --version`(2.1.318), `claude --help`, `claude plugin eval --help`, `claude doctor --help`만 실행했다. 모델을 부르는 명령(`claude -p`, 대화형 `claude`, `/insights`, `/code-review`, `claude plugin eval` 실행 자체)은 쓰지 않았다.
- 수준 표기: `원문 확인`은 인용문이 위 방식으로 통과한 경우만 쓴다. 문서에 없는 해석은 `주의`에 해석이라고 밝혔다.

## V1 /code-review (로컬 코드 리뷰)

- 공식 문서: https://code.claude.com/docs/en/code-review-local (한국어: https://code.claude.com/docs/ko/code-review-local.md)
- `무엇을 보는가` — `원문 확인` — "Claude reviews the changes on your branch, looks for correctness bugs, and reports what it found in your conversation." (Review locally with /code-review)
- `대상 기본값` — `원문 확인` — "With no target, `/code-review` reviews your branch's commits ahead of its upstream branch plus your uncommitted changes." (Choose what to review)
- `단계(effort)` — `원문 확인` — "At `low`, the review reports the findings it's most confident in, so you see fewer false positives." (Tune effort and arguments)
- `비용` — `원문 확인` — "The review runs in your own session, so it counts toward your plan's usage or API billing the same way the rest of the session does." (Review locally with /code-review)
- `수정 여부` — `원문 확인` — "without `--fix`, the review's instructions ask Claude for a report only." (What the review reads and edits)
- `지침 출처` — `원문 확인` — "the review follows your `CLAUDE.md`, including in a non-interactive `-p` run. It doesn't read `REVIEW.md`." (What the review reads and edits)
- 2.1.318 확인: 대화형 슬래시 명령이라 `claude --help`에 나오지 않는다. 미확인(실행하지 않음).
- 수업에 쓸 점: 완료를 모델 자기 보고가 아니라 별도 컨텍스트의 리뷰로 한 번 더 걸러 "고쳤다고 말만 한" 실패를 막는다. 책임은 검증이다.
- 주의: 단계 이름(`low`~`max`, `ultra`)과 단계별 모델 호출 수는 이 페이지에 없다. `--max-findings`는 v2.1.288 이상, `/review`는 v2.1.223부터 `/code-review`의 별칭이다. 터미널 세션에서는 백그라운드 서브에이전트로 돌아 `--fix` 편집이 체크포인트 밖에 있다.

## V2 /code-review ultra (클라우드 리뷰)와 --fix

- 공식 문서: https://code.claude.com/docs/en/code-review-local (한국어: https://code.claude.com/docs/ko/code-review-local.md)
- `ultra 동작` — `원문 확인` — "`/code-review ultra --fix` runs the deeper ultrareview in the cloud, then asks Claude to apply its findings to your working tree when they arrive back in your session." (Escalate to ultrareview)
- `인증 제한` — `원문 확인` — "Ultrareview requires authentication with a claude.ai account." (Escalate to ultrareview)
- `되돌리기 제한` — `원문 확인` — "After one, `/rewind` restores only the files Claude had already edited in your conversation." (What the review reads and edits)
- 2.1.318 확인: 대화형 전용이라 미확인. `claude ultrareview` 하위 명령은 이 페이지가 언급하지만 로컬 `--help`로 확인하지 않았다.
- 수업에 쓸 점: 리뷰가 고친 파일이 `/rewind`로 안 돌아올 수 있음을 알아야 기록(git)으로 되돌릴 수 있다. 책임은 기록과 실행 제어다.
- 주의: ultra의 비용은 이 페이지에 숫자로 없다(다른 페이지 ultrareview에 있을 수 있으나 이번에 열지 않았다). 수업에서 쓰기 전에 고지가 필요하다.

## V3 claude plugin eval — 무엇을 재는가

- 공식 문서: https://code.claude.com/docs/en/plugin-evals (한국어: https://code.claude.com/docs/ko/plugin-evals.md)
- `측정 대상` — `원문 확인` — "Measure how reliably your plugin leads Claude to produce the right outcome" (Test plugins with evals)
- `반복 횟수` — `원문 확인` — "each case runs three times by default." (How a case is scored)
- `기준선과의 차이` — `원문 확인` — "Their difference, `Δ`, is what the plugin contributed." (The no-plugin baseline)
- `채점기 종류 예` — `원문 확인` — "A grader is a pass/fail check on what Claude produced, such as a regex over the reply, whether a particular tool was called, or a rubric that a second model judges the reply against." (Test plugins with evals)
- 2.1.318 확인: `claude plugin eval --help`에서 `--ablation`(기본 with-without), `--runs`(기본 case.runs ?? 3), `--threshold`, `--max-cost-usd`, `--json`을 확인했다. 요구 버전 v2.1.269 이상을 2.1.318이 만족한다.
- 수업에 쓸 점: "플러그인이 있어서 통과했는지, 없어도 통과했는지"를 구분하는 Δ가 개인 지표 설계의 모범이다. 책임은 검증이다.
- 주의: 대상은 플러그인(skills, hooks, agents)이지 일반 프로젝트가 아니다. 한 번 실행은 비결정적이라 점수는 평균이다.

## V4 claude plugin eval — 목, 격리, 신뢰

- 공식 문서: https://code.claude.com/docs/en/plugin-evals (한국어: https://code.claude.com/docs/ko/plugin-evals.md)
- `MCP 목` — `원문 확인` — "A run never starts your plugin's real MCP servers unless you ask." (Mock MCP servers)
- `목 입력 검사` — `원문 확인` — "the `expect:` block guards the input. If a call violates it, the run aborts with score 0 and records why" (Mock MCP servers)
- `격리` — `원문 확인` — "Nothing personal or project-level loads" (How runs are isolated)
- `신뢰` — `원문 확인` — "Pointing it at a plugin is the same trust decision as `claude --plugin-dir`, so only evaluate plugins you trust." (What a run can access)
- 2.1.318 확인: `--mocks <mode>`, `--allow-real-servers`, `--trust-plugin`이 `claude plugin eval --help`에 있다.
- 수업에 쓸 점: 실제 외부 서비스 없이 도구 호출을 재현하고 호출 입력까지 검사할 수 있어, 실패를 재현 가능한 기록으로 남기는 방법의 예가 된다. 책임은 검증과 기록이다.
- 주의: 개인 설정, `CLAUDE.md`, 메모리가 격리되므로 수강생 자신의 환경 효과는 이 도구로 재지 못한다.

## V5 claude plugin eval — 보고서 게시 기본값과 비용

- 공식 문서: https://code.claude.com/docs/en/plugin-evals (한국어: https://code.claude.com/docs/ko/plugin-evals.md)
- `모델 호출` — `원문 확인` — "Every eval run and every judge grader is a real model call on your account, counted against your plan's usage or your API bill" (Test plugins with evals)
- `호출 규모` — `원문 확인` — "a suite makes roughly cases × runs agent runs with the plugin and the same number again for the no-plugin baseline, plus three short judge calls per `llm` or `baseline` grader per run." (How a case is scored)
- `비용 표시` — `원문 확인` — "When the command reports a cost, the figure is a list-price estimate of those calls." (Requirements)
- `비용 상한` — `원문 확인` — "A ceiling on the run's list-price cost estimate, not on plan usage." (Command options)
- `게시 기본값` — `원문 확인` — "Claude Code also publishes the report as a private artifact and prints `Published: <url>`. Pass `--no-publish` to keep it local." (HTML report)
- `세션이 시작한 실행` — `원문 확인` — "A run that a Claude Code session started, such as when you ask Claude to run the suite for you, also stays local" (HTML report)
- 2.1.318 확인: `--no-publish`("Keep the HTML report local only"), `--publish-report`, `--max-cost-usd`가 `--help`에 있다. 결과 폴더와 JSON 필드는 이 페이지 설명을 믿었고 실행으로 확인하지 않았다.
- 수업에 쓸 점: 실행 전 `cases × runs × 2`로 호출 수를 계산해 고지하고 `--max-cost-usd`를 쓴다. 책임은 실행 제어와 기록이다.
- 주의: claude.ai 구독으로 로그인했고 artifacts가 가능하면 보고서가 기본으로 비공개 아티팩트로 게시된다. 수업에서 `--no-publish`를 안내할지는 저자가 정한다. 초기 접근 제한 오류 문구가 troubleshooting에 있어 계정에 따라 쓰지 못할 수 있다.

## V6 OpenTelemetry 모니터링 — 켜는 방법

- 공식 문서: https://code.claude.com/docs/en/monitoring-usage (한국어: https://code.claude.com/docs/ko/monitoring-usage.md)
- `내보내는 것` — `원문 확인` — "Claude Code exports metrics as time series data via the standard metrics protocol, events via the logs/events protocol, and optionally distributed traces via OpenTelemetry." (Monitoring)
- `켜는 스위치` — `원문 확인` — "export CLAUDE_CODE_ENABLE_TELEMETRY=1" (Quick start)
- `환경 변수 표` — `원문 확인` — "Enables telemetry collection (required)" (Common configuration variables)
- `프로토콜` — `원문 확인` — "Claude Code has no default protocol, so set this or the signal-specific protocol variable for each `otlp` exporter you enable" (Common configuration variables)
- `확인 방법` — `원문 확인` — "check your backend for the `claude_code.session.count` metric, which Claude Code emits when a session starts." (Quick start)
- `콘솔 출력` — `원문 확인` — "Metrics exporter types, comma-separated. Use `none` to disable" (Common configuration variables)
- 2.1.318 확인: 환경 변수 방식이라 `--help`에 없다. `claude --help`의 `--debug-file <path>`가 문서의 문제 해결 안내와 일치함만 확인했다. 실제 내보내기는 실행하지 않았다.
- 수업에 쓸 점: 개인 지표를 모델 자기 보고가 아니라 Claude Code가 직접 내보내는 숫자로 모은다. 책임은 기록이다.
- 주의: 문서는 조직 운영 관점이다. 개인 PC에서 `console` 내보내기만 쓰면 수집 서버 없이도 확인할 수 있다는 점은 표의 `console` 값에서 나온 해석이며 실행해 보지 않았다. 관리 설정이 있는 기기에서는 OTLP 목적지가 잠길 수 있다.

## V7 OpenTelemetry — 메트릭 목록

- 공식 문서: https://code.claude.com/docs/en/monitoring-usage (한국어: https://code.claude.com/docs/ko/monitoring-usage.md)
- `세션` — `원문 확인` — "Count of CLI sessions started" (Metrics)
- `코드 줄` — `원문 확인` — "Count of lines of code modified" (Metrics)
- `풀 리퀘스트` — `원문 확인` — "Number of pull requests created" (Metrics)
- `커밋` — `원문 확인` — "Number of git commits created" (Metrics)
- `비용` — `원문 확인` — "Cost of the Claude Code session" (Metrics)
- `토큰` — `원문 확인` — "Number of tokens used" (Metrics)
- `편집 도구 결정` — `원문 확인` — "Count of code editing tool permission decisions" (Metrics)
- `활동 시간` — `원문 확인` — "Total active time" (Metrics)
- `비용은 근사` — `원문 확인` — "Cost metrics are approximations." (Cost monitoring)
- 2.1.318 확인: 해당 없음(내보내기를 실행하지 않았다). 지표 이름은 `claude_code.session.count`, `claude_code.lines_of_code.count`, `claude_code.pull_request.count`, `claude_code.commit.count`, `claude_code.cost.usage`, `claude_code.token.usage`, `claude_code.code_edit_tool.decision`, `claude_code.active_time.total`이다.
- 수업에 쓸 점: 세션 수, 토큰, 비용, 편집 승인/거부(`accept`, `reject`)를 개인 지표 후보로 바로 쓸 수 있다. 책임은 기록이다.
- 주의: 토큰 유형은 `input`, `output`, `cacheRead`, `cacheCreation`이다. 비용은 목록 가격 기반 근사값이라 청구액과 다를 수 있다.

## V8 OpenTelemetry — 이벤트와 도구 결정

- 공식 문서: https://code.claude.com/docs/en/monitoring-usage (한국어: https://code.claude.com/docs/ko/monitoring-usage.md)
- `도구 결정 이벤트` — `원문 확인` — "Logged when a tool permission decision is made (accept/reject)." (Tool decision event)
- `도구 결과 이벤트` — `원문 확인` — "Logged when a tool completes execution. Not emitted if the tool call was rejected" (Tool result event)
- `결정 출처` — `원문 확인` — "Where the permission decision came from." (Tool result event)
- `프롬프트 이벤트` — `원문 확인` — "Logged when a prompt is submitted, including on turns Claude Code starts on its own." (User prompt event)
- `상관 키` — `원문 확인` — "The `prompt.id` attribute lets you tie all of those events back to the single prompt that triggered them." (Event correlation attributes)
- 2.1.318 확인: 해당 없음(내보내기를 실행하지 않았다).
- 수업에 쓸 점: 어떤 도구 호출이 설정, 훅, 사용자 중 누구의 결정으로 허용됐는지 기록할 수 있어 실행 제어의 효과를 사후에 설명한다. 책임은 실행 제어와 기록이다.
- 주의: 이 항목의 `결정 출처` 인용은 도구 결과 이벤트의 설명이고, 도구 결정 이벤트는 거부 출처(`user_abort`, `user_reject`)도 가진다(해당 절의 표). `tool_result`의 `request_id`는 v2.1.310 이상, `prompt_text`는 v2.1.287 이상이 필요하다고 적혀 있어 2.1.318에서는 해당된다.

## V9 OpenTelemetry — 기본 제외 항목과 포함 스위치

- 공식 문서: https://code.claude.com/docs/en/monitoring-usage (한국어: https://code.claude.com/docs/ko/monitoring-usage.md)
- `프롬프트 본문` — `원문 확인` — "Prompt content. Redacted by default. Set `OTEL_LOG_USER_PROMPTS=1` to include it" (User prompt event)
- `프롬프트 스위치` — `원문 확인` — "Enable logging of user prompt content (default: disabled)" (Common configuration variables)
- `도구 세부` — `원문 확인` — "Enable logging of tool parameters and input arguments in tool events and trace span attributes" (Common configuration variables)
- `도구 출력` — `원문 확인` — "Enable logging of tool content in the `tool.output` span event (default: disabled)." (Common configuration variables)
- `원시 API 본문` — `원문 확인` — "Bodies include the entire conversation history." (Common configuration variables)
- `연쇄 동의` — `원문 확인` — "Enabling this implies consent to everything `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, and `OTEL_LOG_TOOL_CONTENT` would reveal" (Common configuration variables)
- 2.1.318 확인: 해당 없음(환경 변수).
- 수업에 쓸 점: 기본값은 본문과 도구 세부를 빼므로 개인 지표는 안전하게 모을 수 있고, 켜는 스위치(`OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_RAW_API_BODIES`)는 비밀이 새는 경로임을 먼저 알린다. 책임은 기록이다.
- 주의: `OTEL_LOG_ASSISTANT_RESPONSES`는 설정하지 않으면 `OTEL_LOG_USER_PROMPTS` 값을 따라간다(표의 설명). 한 스위치가 다른 것을 함께 켤 수 있다.

## V10 비용 추적 명령 (/usage)

- 공식 문서: https://code.claude.com/docs/en/costs (한국어: https://code.claude.com/docs/ko/costs.md)
- `세션 블록` — `원문 확인` — "The Session block at the top of `/usage` shows detailed token usage statistics for your current session." (Using the `/usage` command)
- `구독자 주의` — `원문 확인` — "The Session block in `/usage` shows API token usage and is intended for API users." (Using the `/usage` command)
- `계산 방식` — `원문 확인` — "Claude Code computes the dollar figure locally from token counts at list price" (Using the `/usage` command)
- `초기화` — `원문 확인` — "These totals reset when `/clear` starts a new session" (Using the `/usage` command)
- `스피너 옆 토큰` — `원문 확인` — "It is a live, approximate count of the output the current turn has produced so far." (Read the token count beside the spinner)
- 2.1.318 확인: `claude --help`에 `--max-budget-usd <amount>`가 있다. `/usage` 자체는 대화형 전용이라 미확인.
- 수업에 쓸 점: 작업 전후 `/usage`의 Session 블록으로 비용과 줄 수 변화를 기록해 "얼마 들었나"를 말로 하지 않고 숫자로 남긴다. 책임은 기록이다.
- 주의: 이 페이지에는 `/cost` 명령이 없다(링크 문구 외에 사용 설명 없음). `/cost`를 가르치지 않고 `/usage`를 쓴다. 구독자는 달러 값이 청구와 무관하다.

## V11 /insights (web.md 6(a) 재확인)

- 공식 문서: https://code.claude.com/docs/en/costs (절: Analyze your usage patterns), https://code.claude.com/docs/en/commands, https://code.claude.com/docs/en/claude-directory (한국어: costs는 https://code.claude.com/docs/ko/costs.md, commands와 claude-directory는 목록에 없음)
- `내장 명령` — `원문 확인` — "Generate an HTML report analyzing your recent sessions on this machine" (commands, `/insights` 행)
- `클라우드 제외` — `원문 확인` — "Not available in cloud sessions" (commands, `/insights` 행)
- `분석 내용` — `원문 확인` — "It analyzes your recent sessions on this machine and writes an HTML report covering what you work on, friction points such as misunderstood requests or buggy code, and suggestions for using Claude Code more effectively." (Analyze your usage patterns)
- `상한` — `원문 확인` — "A single run analyzes up to 200 sessions it hasn't seen before and skips very short ones." (Analyze your usage patterns)
- `보고서 위치` — `원문 확인` — "Claude Code writes the latest report to `~/.claude/usage-data/report.html` and saves a timestamped copy of each run in the same directory" (Analyze your usage patterns)
- `토큰 사용` — `원문 확인` — "The analysis runs through the same provider and account as your regular sessions, and the tokens count against your plan or API usage." (Analyze your usage patterns)
- `범위` — `원문 확인` — "Sessions from other devices and claude.ai aren't included." (Analyze your usage patterns)
- `디렉터리 표` — `원문 확인` — "Past `/insights` reports and the cached analysis data used to build them" (claude-directory)
- 2.1.318 확인: 대화형 전용이라 미확인(실행하지 않음, 토큰을 쓴다).
- 수업에 쓸 점: 자기 세션의 마찰을 모델이 요약해 주지만 모델 호출이 든다. 책임은 기록이다.
- 주의: web.md 6(a)의 인용 6개는 오늘 페이지에서 모두 그대로 통과했다. 바뀐 것은 commands 표의 `/insights` 행이 길어진 점뿐이다(앞 문장은 같고 뒤에 "which projects you work in, how you use Claude Code, where things go wrong, and features to try."가 붙었다). 신규: 자동 모드 가능 시 권한 프롬프트 절감 추정이 보고서에 포함될 수 있고, 오래된 보고서는 `cleanupPeriodDays`(기본 30일)에 따라 시작 시 지워진다.

## V12 구성 디버깅 — 무엇이 로드됐는지 보는 명령

- 공식 문서: https://code.claude.com/docs/en/debug-your-config (한국어: https://code.claude.com/docs/ko/debug-your-config.md)
- `권장 명령 요약` — `원문 확인` — "Use /context, /doctor, /hooks, and /mcp to see what actually loaded." (Debug your configuration)
- `/context` — `원문 확인` — "The `/context` command shows everything occupying the context window for the current session." (See what loaded into context)
- `/hooks` — `원문 확인` — "Active hook configurations" (See what loaded into context)
- `/mcp` — `원문 확인` — "Connected MCP servers and their status" (See what loaded into context)
- `/permissions` — `원문 확인` — "Resolved allow and deny rules currently in effect" (See what loaded into context)
- `/status` — `원문 확인` — "Active settings sources, including whether managed settings are in effect" (See what loaded into context)
- `/skills` — `원문 확인` — "Available skills from project, user, and plugin sources" (See what loaded into context)
- `하위 폴더 CLAUDE.md` — `원문 확인` — "Subdirectory `CLAUDE.md` files load on demand rather than at session start, so they don't appear in that breakdown." (See what loaded into context)
- `터미널 진단` — `원문 확인` — "It prints read-only installation and settings diagnostics without starting a session." (Check resolved settings)
- `지침 대 강제` — `원문 확인` — "Use permissions or hooks for security boundaries and anything that must never happen, where you need a guarantee instead of guidance." (See what loaded into context)
- 2.1.318 확인: `claude doctor --help`가 "Check the health of your Claude Code installation. Reads settings files in the current directory without a trust prompt."라고 보여 준다. `claude --help`의 `--debug-file <path>`, `-d, --debug [filter]`도 있다. `/context`, `/memory`, `/hooks`, `/permissions`, `/mcp`는 대화형 전용이라 미확인.
- 수업에 쓸 점: 지침이 안 먹을 때 "모델이 무시했다"고 단정하지 않고 로드 여부부터 확인해 상태와 지침의 실패를 가른다. 책임은 지침, 상태, 기록이다.
- 주의: `/memory`는 표에서 설명만 확인했고 인용하지 않았다. 전체 화면 모드에서는 `/context all`이 필요하다고 문서에 적혀 있다.

## V13 분석 대시보드(analytics) — 개인 개발자 관점

- 공식 문서: https://code.claude.com/docs/en/analytics (한국어: https://code.claude.com/docs/ko/analytics.md)
- `열람 권한` — `원문 확인` — "Admins and Owners can view the dashboard." (Access analytics for Team and Enterprise)
- `토큰·비용은 OTel` — `원문 확인` — "For per-user token counts and cost estimates, configure OpenTelemetry export" (Access analytics for Team and Enterprise)
- `귀속 시간 창` — `원문 확인` — "Sessions from 21 days before to 2 days after the PR merge date are considered for attribution matching." (Time window)
- `재작성 코드` — `원문 확인` — "Code substantially rewritten by developers, with more than 20% difference, is not attributed to Claude Code" (Attribution notes)
- 2.1.318 확인: 해당 없음(웹 대시보드).
- 수업에 쓸 점: 이 대시보드는 팀 관리자용이라 수강생 개인 지표는 OTel(V6~V9)이나 `/usage`(V10)로 모아야 한다. 귀속 비율은 "AI가 쓴 코드 비율"의 정답이 아니라 규칙에 따른 추정이다. 책임은 기록이다.
- 주의: 기여도 지표는 GitHub 연동 설정이 필요하고, Team/Enterprise 요금제 기능이다.

## 수업에 쓸 때 주의

- 모델 호출이 드는 것: `/code-review`(세션 사용량), `claude plugin eval`(실행 수 `cases × runs × 2`와 judge 호출), `/insights`(분석 토큰). 실행 직전에 규모를 고지한다.
- 대화형 전용이라 이번에 실행 확인을 못 한 것: `/code-review`, `/insights`, `/usage`, `/context`, `/hooks`, `/mcp`, `/permissions`. 수업 전에 저자가 한 번 실행해 보여야 한다.
- OpenTelemetry는 기본값이 본문과 도구 세부를 뺀다. `OTEL_LOG_*` 스위치를 켜기 전에 무엇이 새는지 알려 준다. 수강생 자신의 세션 기록을 다루는 실습이라 본문 포함 옵션은 쓰지 않는다.
- 비용 숫자(`/usage`, `cost.usage`, `plugin eval`의 `costUsd`)는 목록 가격 추정이다. 청구액이 아니다.
- 문서의 버전 조건(`claude plugin eval` v2.1.269, `--max-findings` v2.1.288, `prompt_text` v2.1.287)은 2.1.318에서 충족되지만, 문서는 계속 바뀌므로 확인일 2026-11-06 기준이다.

Quotes verified: 76/76
