# 웹 원문 근거 대장 (확인일 2026-11-05)

## 0. 확인 방법과 수준 표기

- 방법: 원문 HTML을 `curl -sL`(일반 브라우저 User-Agent)로 내려받고, `python3 -I` + `html.parser`로 텍스트를 뽑은 뒤 공백만 정규화해서 인용문을 부분 문자열로 대조했다. `<code>` 표시와 OpenAI 페이지의 링크 표지 "(opens in a new window)"는 대조 전에 지웠다. Claude Code 문서는 `llms.txt`가 가리키는 `.md` 판(`https://code.claude.com/docs/en/<page>.md`)으로 대조했고, 같은 이름의 HTML 페이지가 200으로 열리는 것도 확인했다. 문서 쪽 인용은 마크다운 링크 표기를 지운 본문 텍스트다.
- 이 대장에 큰따옴표로 실은 영어·한국어 인용문은 모두 위 방식으로 원문 텍스트와 일치를 확인했다. WebFetch(요약 모델)는 쓰지 않았다.
- 수준 표기
  - `원문 확인`: 원 페이지를 내려받아 인용문을 grep으로 대조했다.
  - `원문 확인(Wayback 사본)`: 원 URL은 curl에 403이었고, web.archive.org에 보관된 원 페이지 사본으로 grep 대조했다(4번에만 해당).
  - `원문 열람(대조 안 됨)`, `2차 출처만`, `미확인`: 해당 항목에 따로 적었다.
- 인용 뒤 괄호는 원문 위치(절 제목)다. `›`는 하위 절을 뜻한다.

---

## 1. Claude, "The AI-native SDLC playbook"

- URL: 입력한 `https://claude.com/blog/the-ai-native-sdlc-playbook`은 `https://claude.com/resources/articles/the-ai-native-sdlc-playbook`으로 리다이렉트된다(canonical 태그도 이 주소).
- 한국어판: `https://claude.com/ko/resources/articles/the-ai-native-sdlc-playbook` (제목 "AI-native SDLC 플레이북")
- 저자: Louis Claxton — `원문 확인` — "AuthorLouis Claxton" (머리 메타 영역, 한국어판도 같은 표기). 감사 명단: "Thanks to Jim Blackhurst, Will Steuk, and Jamal Arif" (Resources and acknowledgments)
- 날짜: 2026-08-21 — `원문 확인` — "DateAugust 21, 2026" / 한국어판 "날짜2026년 8월 21일". 읽기 시간은 영문 "Reading time40 min", 한국어판 "읽기 소요 시간44분".
- 분류: Category Best practices, Product Claude Enterprise, Claude Code, Claude Tag
- 수준: `원문 확인` (영문판, 한국어판 모두)

### 항목

1. `여섯 단계는 Plan·Design·Build·Test·Deploy·Maintain이고 원문은 이를 비선형이라 부른다` — `원문 확인` — "six non-linear stages (Plan, Design, Build, Test, Deploy, Maintain)" (Plays). 한국어판: "6가지 비선형 단계(계획, 디자인, 빌드, 테스트, 배포, 유지보수)" (플레이). 목차 표기는 "Stage 1 — Plan"부터 "Stage 6 — Maintain"까지다.
2. `모든 단계는 다음 단계가 읽을 산출물을 커밋한다` — `원문 확인` — "Every stage commits an artifact the next stage can read." (What is an AI-native SDLC? 끝의 강조문). 한국어판에서도 이 문장은 번역 없이 영어로 나온다.
3. `산출물 사슬의 원문 목록` — `원문 확인` — "Each stage ends by writing one to version control (including intent.md, spec.md, plan.md, the diff and its tests, the PR with its review findings, and the incident record) and the next stage begins by reading it." (What is an AI-native SDLC?). 한국어판: "각 단계는 버전 관리 기록(intent.md, spec.md, plan.md, 변경 사항 및 테스트, 검토 결과가 포함된 PR, 인시던트 기록 포함)을 작성하는 것으로 끝나며, 다음 단계는 이를 읽는 것으로 시작됩니다."
4. `커밋이 다음 단계를 촉발하는 순서` — `원문 확인` — "An accepted intent.md triggers the requirements and design pass, an approved spec.md triggers plan mode, a merged PR triggers the pipeline, and a breached control band in production writes the next intent.md" (Plays)
5. `단계별 산출물` — `원문 확인`
   - Plan → `intent.md`: "the product owner reviews and corrects the agent-written intent.md before it is committed." (01 Plan › Capture as intent.md)
   - Design → `spec.md`: "Commit spec.md alongside intent.md." (02 Design › Requirements and design › How to execute it). 자동화 단계에서는 "commit spec.md as a pull request".
   - Build → `plan.md`: "the approved version is committed as plan.md for later stages to check against." (03 Build › Claude Code plan mode as the default starting point). 실행 단계 문장: "Commit the approved plan as plan.md."
   - Build 이후 → diff와 테스트, 검토 결과가 달린 PR (3번 문장)
   - Maintain → 새 `intent.md`: "The agent writes its diagnosis as intent.md in the Stage 1: Plan format" (06 Maintain › Closing the loop)
   - `REVIEW.md`는 단계 산출물이 아니다: "The tech lead writes the review policy as REVIEW.md at the repo root" (05 Deploy › AI in the PR review loop › How to execute it). 3번의 산출물 목록에 `REVIEW.md`는 없다.
6. `승인된 계획 없이는 구현하지 않는다` — `원문 확인` — "Nothing is implemented without an accepted plan." (03 Build 도입문). 한국어판도 영어 그대로다.
7. `플랜 모드가 계획 승인 전 편집을 막는다` — `원문 확인` — "Plan mode enforces this itself, since Claude cannot edit files until the engineer accepts the plan." (03 Build › plan mode › Governance considerations). 한국어판: "엔지니어가 계획을 수락하기 전까지는 Claude가 파일을 편집할 수 없기 때문에, 계획 모드에서는 이를 자체적으로 시행합니다." 공식 문서에는 예외가 있다(6(b) 참고).
8. `스킬은 권고 통제, 훅은 결정론적 통제` — `원문 확인`
   - "The skill makes violations rare and the hook makes them close to impossible." (03 Build › Skills as institutional knowledge › Governance considerations). 한국어판: "이 스킬은 위반 사례를 낮추고, 후크는 사실상 위반이 거의 불가능하게 만듭니다."
   - "A skill is an advisory control while a hook is the deterministic layer behind it." (03 Build › Hooks as build-time guardrails). 한국어판: "스킬은 권고형 통제이고, 후크는 그 뒤에 작동하는 결정론적 계층입니다."
9. `CLAUDE.md 운영 규칙` — `원문 확인` — "When Claude makes a mistake twice, the correction goes into CLAUDE.md." / "Keep it under a page, because Claude reads all of it at the start of a session" (03 Build › The CLAUDE.md › How to execute it)
10. `평가는 최근 실제 작업 20~50개로 만든다` — `원문 확인` — "The platform engineer collects 20 to 50 real tasks from recent work with its expected/accepted outcome." (04 Test › Continuous evals in CI › How to execute it). 한국어판: "플랫폼 엔지니어가 최근 작업에서 20~50개의 실제 작업과 각각의 예상/승인된 결과를 수집합니다."
    - 평가 항목의 모양: "Write each task as an eval, meaning the prompt plus the checks that define acceptable (tests pass, lint clean, behavior unchanged, policy followed)."
    - 실행 시점: "The suite runs non-interactively in CI on a schedule and on any change to CLAUDE.md, skills or hooks"
    - 사고에서 평가로: "Each production incident gets an eval, written by the team that owned the incident, and stays in the suite as a regression test."
11. `버그 수정은 실패하는 테스트부터` — `원문 확인` — "For bug fixes, write the failing test first." 이어서 "Only then ask Claude to make it pass without editing the test, with the test-file hook from the final step enforcing the restriction." (04 Test › Give Claude a feedback loop › How to execute it). 한국어판 앞 문장: "버그를 수정할 때는 먼저 실패하는 테스트를 작성합니다." 뒤 문장의 한국어판은 오역이다(아래 주의).
12. `테스트 편집을 막는 훅` — `원문 확인` — "an agent fixing code must not be able to weaken the check on that code." / "A hook that blocks edits to test files during a fix task does this." (같은 절의 마지막 단계). 한국어판: "수정 작업 중에 테스트 파일에 대한 편집을 차단하는 후크가 이를 수행합니다." 원문에는 이 훅의 스크립트 예시가 없다. 원문에 실린 훅 스크립트는 배포 게이트(`.claude/hooks/production-gate.sh`)뿐이고, 그 주석이 "exit 2 # exit 2 blocks the action; the message goes to Claude"다.
13. `훅 게이트의 결과는 허용·확인·차단` — `원문 확인` — "The platform engineer expresses each gate as a hook, a script that runs before Claude acts that can allow, ask, or block." (05 Deploy › Hooks as approval gates › How to execute it)

### 플레이별 측정 지표 (원문 "How to measure it")

한국어판에는 대응하는 한국어 문장이 없다. 한국어판의 측정 블록 13개가 모두 영어 원문 그대로 나온다(예: 한국어판에도 "First-pass CI success rate for agent-written changes, which the CI system already supports."가 영어로 있다). 아래는 모두 `원문 확인`이다.

| 플레이 (원문 위치) | 선행 지표 (Leading indicator) | 후행 지표 (Lagging indicator) |
|---|---|---|
| 01 Plan › Capture as intent.md | "Time from first conversation to a committed intent.md, read from git history on the intent home, which records author and time stamp." | "The survival rate, or the share of intent.md files that the product owner accepts into Stage 2: Design rather than closes." |
| 02 Design › Requirements and design (참고) | "Elapsed time between the intent.md commit and the spec.md commit for the same change" | "Requirements rework after build starts." |
| 03 Build › plan mode | "Share of changes that merge from the first implementation pass, and time from plan approval to merged PR" | "Rework cycles per change, again from the PR metadata, and how often the merged diff still matches the committed plan.md." |
| 03 Build › The CLAUDE.md | "How often Claude repeats a mistake CLAUDE.md should have caught." | "Time to first merged PR for a new member of the team from PR history." |
| 03 Build › Skills as institutional knowledge | "Time from the policy owner approving a policy change to the updated skill merging, taken from the PR on the skill folder." | "PR reviews findings that cite the policy, which should fall towards zero once the skill is applying the policy while the code is written." |
| 04 Test › Give Claude a feedback loop | "First-pass CI success rate for agent-written changes, which the CI system already supports." | "Review time per PR (from the PR metadata), which should fall once the tests catch what reviewers used to catch, and the change failure rate from an incident tracker." |
| 04 Test › Continuous evals in CI | "The eval pass rate over time, reported by the suite on every run, and how long a production incident takes to become a permanent eval." | "Regressions caught in CI compared with regressions found in production derived from the incident tracker." |
| 05 Deploy › AI in the PR review loop | "Time to first review, which should fall to minutes, and the share of review comments resolved without a human touching the branch" | "Defects and vulnerabilities caught before merge set against those escaping to production, from the PR history and the incident tracker." |
| 05 Deploy › Hooks as approval gates (참고) | "Time spent waiting on each approval gate." | "Gate violations reaching production before and after hooks from the incident tracker." |

- "PR reviews findings"는 원문 표기 그대로다.
- "Hooks as build-time guardrails" 플레이에는 측정 블록이 없다.

### 수업에 쓸 때 주의

- 블로그 URL은 `/resources/articles/`로 옮겨졌다. 인용할 때는 canonical 주소를 쓴다.
- `REVIEW.md`를 Deploy 단계의 산출물로 가르치면 원문과 어긋난다. 원문의 산출물 사슬(항목 3)은 intent.md → spec.md → plan.md → diff와 테스트 → 검토 결과가 달린 PR → 사고 기록이고, Maintain이 다시 intent.md를 쓴다. `REVIEW.md`는 기술 리드가 저장소 루트에 두는 검토 정책 파일이다.
- 한국어판은 부분 번역이다. 6단계 비교표, 각 단계 도입문(예: "Nothing is implemented without an accepted plan."), Traditional/AI-native 대비 문단, 측정 지표 13블록, 일부 Getting started와 Governance 블록이 영어로 남아 있다. 측정 지표를 한국어로 쓰면 저자 번역이라고 밝힌다.
- 한국어판 오역 두 곳:
  - "마지막 단계부터 테스트 파일 후크로 제한을 적용합니다." — 원문 "with the test-file hook from the final step"은 '같은 목록의 마지막 단계에서 설명하는 테스트 파일 훅으로'라는 뜻이다.
  - "기술 리드는 리포지토리 부분에 REVIEW.md로 검토 정책을 작성하고" — 원문은 "at the repo root"(저장소 루트)다.
  - 한국어판은 hook을 "후크"로 쓴다.
- 항목 7(플랜 모드는 승인 전 편집 불가)은 공식 문서상 bypass 권한이 있는 대화형 터미널 세션에서는 성립하지 않는다(6(b)).
- 항목 13은 훅 결과를 allow/ask/block으로 부른다. 공식 문서의 PreToolUse 값은 allow/deny/ask/defer이고 "block"은 폐기된 값으로 "deny"에 대응한다(6(c)).
- "20 to 50 real tasks"는 수집 규모 권고일 뿐이고 원문에 그 수치의 근거(실험, 통계)는 없다.
- PDF 판("Prefer a PDF?")은 내려받지 않았다.

---

## 2. Anthropic, "Effective harnesses for long-running agents"

- URL: 입력한 `https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents`는 `https://www.anthropic.com/research/effective-harnesses-for-long-running-agents`로 리다이렉트된다(canonical도 이 주소). 페이지 분류는 Team "Engineering".
- 저자: Justin Young — `원문 확인` — "Written by Justin Young." (Authors & acknowledgements)
- 날짜: 2025-11-26 — `원문 확인` — "Nov 26, 2025" (Published)
- 수준: `원문 확인`

### 항목

1. `해법은 초기화 에이전트와 코딩 에이전트 두 단계` — `원문 확인` — "an initializer agent that sets up the environment on the first run, and a coding agent that is tasked with making incremental progress in every session, while leaving clear artifacts for the next session." (도입부)
2. `두 에이전트는 첫 사용자 프롬프트만 다르다` — `원문 확인` — "We refer to these as separate agents in this context only because they have different initial user prompts." (Footnotes 01). 같은 각주는 시스템 프롬프트, 도구, 하네스가 같다고 말한다.
3. `초기화 에이전트가 만드는 것` — `원문 확인` — "an init.sh script, a claude-progress.txt file that keeps a log of what agents have done, and an initial git commit that shows what files were added." (The long-running agent problem)
4. `코딩 에이전트의 역할` — `원문 확인` — "Every subsequent session asks the model to make incremental progress, then leave structured updates." (같은 절)
5. `기능 목록은 JSON이고 passes 필드만 바꾼다` — `원문 확인` (Environment management › Feature list)
   - 규모와 초기값: "In the claude.ai clone example, this meant over 200 features" / "These features were all initially marked as “failing”"
   - 수정 범위: "We prompt coding agents to edit this file only by changing the status of a passes field". 예시 JSON의 마지막 필드는 "passes": false.
   - JSON을 고른 이유: "the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files."
   - 강한 지시문: "“It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality.”"
6. `기능 목록 파일 이름` — `원문 확인` — 본문은 "feature list file", "features list file"이라고만 부른다. 파일 이름은 예시 세션 기록에만 나온다: "<read - feature_list.json>" (Getting up to speed 예시). 같은 예시 끝에는 "Now let me review the tests.json file more comprehensively"도 있다. 원문 안에서 이름이 하나로 고정되어 있지 않다. 동반 quickstart README는 `feature_list.json`을 쓴다(항목 12).
7. `한 번에 기능 하나` — `원문 확인` — "the next iteration of the coding agent was then asked to work on only one feature at a time." (Incremental progress)
8. `git 커밋과 진행 파일` — `원문 확인` — "ask the model to commit its progress to git with descriptive commit messages and to write summaries of its progress in a progress file." (Incremental progress)
9. `init.sh와 시작 전 기본 E2E 점검` — `원문 확인` — "It also helps to ask the initializer agent to write an init.sh script that can run the development server, and then run through a basic end-to-end test before implementing a new feature." (Getting up to speed). 세션 시작 순서: "Read the features list file and choose the highest-priority feature that’s not yet done to work on."
10. `E2E 테스트와 브라우저 자동화` — `원문 확인` (Testing)
    - "Claude mostly did well at verifying features end-to-end once explicitly prompted to use browser automation tools and do all testing as a human user would."
    - 사용 도구는 Puppeteer MCP. 한계: "Claude can’t see browser-native alert modals through the Puppeteer MCP"
11. `실패 양상` — `원문 확인`
    - 본문 첫 두 가지: "Claude’s failures manifested in two patterns." → "First, the agent tended to try to do too much at once—essentially to attempt to one-shot the app." / "a later agent instance would look around, see that progress had been made, and declare the job done." (The long-running agent problem)
    - 본문 추가 한 가지: "One final major failure mode that we observed was Claude’s tendency to mark a feature as complete without proper testing." 같은 절에 "but would fail recognize that the feature didn’t work end-to-end." [sic]도 있다. (Testing)
    - 표(Agent failure modes and solutions)의 네 문제: "Claude declares victory on the entire project too early." / "Claude leaves the environment in a state with bugs or undocumented progress." / "Claude marks features as done prematurely." / "Claude has to spend time figuring out how to run the app." 표 캡션: "Summarizing four common failure modes and solutions in long-running AI agents."
    - 배경: "However, compaction isn’t sufficient." / "even a frontier coding model like Opus 4.5 running on the Claude Agent SDK in a loop across multiple context windows will fall short of building a production-quality web app" (The long-running agent problem)
12. `claude-quickstarts autonomous-coding` — `원문 확인` — 본문 "You can find code examples in the accompanying quickstart." 이 링크의 href는 `https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding`이다(HTML에서 확인). `gh api`로 디렉터리가 있는 것을 확인했다(agent.py, prompts/initializer_prompt.md, prompts/coding_prompt.md, prompts/app_spec.txt 등, 해당 경로 마지막 커밋 2026-10-23). README의 해당 문장: "creates `feature_list.json` with 200 test cases" (README 파일 grep). 코드와 프롬프트 내용은 읽지 않았다.

### 수업에 쓸 때 주의

- `/engineering/` 주소는 `/research/`로 옮겨졌다.
- 대상은 Claude Agent SDK로 만든 하네스(Opus 4.5)다. Claude Code의 기능 설명이 아니다.
- 실패 양상의 개수는 본문이 2개 + 1개, 표가 4개다. 네 가지라고 가르치면 표 기준이라고 밝힌다. 표의 첫 행 문구는 "declares victory on the entire project too early"이고 본문 문구는 "declare the job done"이다.
- "fail recognize"는 원문 오탈자다. 인용할 때 [sic]을 붙인다.
- 감사 명단의 "Prithvi Rajasakeran"은 3번 글의 저자 표기 "Prithvi Rajasekaran"과 철자가 다르다(원문 그대로).
- 기능 목록 파일 이름은 항목 6을 따른다. 이 글이 파일 이름을 feature_list.json으로 정했다고 하면 과장이다. 이름은 quickstart README와 예시 세션 기록에서 나온다.

---

## 3. Anthropic, "Harness design for long-running application development"

- URL: 입력한 `https://www.anthropic.com/engineering/harness-design-long-running-apps`는 `https://www.anthropic.com/research/harness-design-long-running-apps`로 리다이렉트된다.
- 저자: Prithvi Rajasekaran — `원문 확인` — "Written by Prithvi Rajasekaran, a member of our Labs team."
- 날짜: 2026-03-24 — `원문 확인` — "Mar 24, 2026" (Published)
- 수준: `원문 확인`

### 항목

1. `planner, generator, evaluator 세 역할` — `원문 확인` — "The final result was a three-agent architecture—planner, generator, and evaluator—that produced rich full-stack applications over multi-hour autonomous coding sessions." (도입부)
   - Planner: "took a simple 1-4 sentence prompt and expanded it into a full product spec" (Scaling to full-stack coding › The architecture)
   - Generator: "instructing the generator to work in sprints, picking up one feature at a time from the spec."
   - Evaluator: "the evaluator used the Playwright MCP to click through the running application the way a user would"
   - 발상: "Taking inspiration from Generative Adversarial Networks (GANs), I designed a multi-agent structure with a generator and evaluator agent." (도입부)
2. `별도 평가자를 회의적으로 조정하는 편이 자기 비평보다 다루기 쉽다` — `원문 확인` — "But tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work" (Why naive implementations fall short). 배경 문장: "agents tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre."
3. `레트로 게임 메이커 실험의 시간과 비용` — `원문 확인` (Running the harness)
   - 모델: "For the first version of this harness, I used Claude Opus 4.5"
   - 표 값: Solo 20 min, $9 / Full harness 6 hr, $200
   - "The harness was over 20x more expensive, but the difference in output quality was immediately apparent."
   - 계획 규모: "the planner step expanded that prompt into a 16-feature spec spread across ten sprints."
4. `스프린트 계약` — `원문 확인` — "Before each sprint, the generator and evaluator negotiated a sprint contract: agreeing on what "done" looked like for that chunk of work before any code was written." (The architecture). 세부: "Sprint 3 alone had 27 criteria covering the level editor" (Running the harness). 소통 방식: "Communication was handled via files"
5. `평가자도 조정이 필요하다` — `원문 확인` — "Out of the box, Claude is a poor QA agent." (Running the harness)
6. `Opus 4.6에서 하네스를 줄였다` — `원문 확인` (Iterating on the harness, Removing the sprint construct, Results from the updated harness)
   - "I started by removing the sprint construct entirely."
   - "With the sprint construct removed, I moved the evaluator to a single pass at the end of the run rather than grading per sprint."
   - DAW 실험: "The run was still lengthy and expensive, at about 4 hours and $124 in token costs." 표 합계는 Total V2 Harness 3 hr 50 min, $124.70.
   - "The practical implication is that the evaluator is not a fixed yes-or-no decision."
7. `하네스의 각 부품은 모델 한계에 대한 가정이다` — `원문 확인` — "every component in a harness encodes an assumption about what the model can't do on its own" (Iterating on the harness)
8. `컨텍스트 리셋을 뺀 이유` — `원문 확인` — "Opus 4.5 largely removed that behavior on its own, so I was able to drop context resets from this harness entirely." (The architecture). 이전 하네스(Sonnet 4.5)는 context anxiety 때문에 리셋을 썼다.

### 수업에 쓸 때 주의

- $9 대 $200 비교는 V1(Opus 4.5, 레트로 게임 메이커 프롬프트)이다. $124.70은 V2(Opus 4.6, 스프린트 제거, DAW 프롬프트)다. 프롬프트와 모델이 다르므로 한 표에 섞어 비교하지 않는다.
- 스프린트 계약은 V1에만 있다. V2는 스프린트 구조를 뺐다.
- "20x"는 비용 비교다. 품질 차이는 저자의 정성 평가이고 수치 지표는 없다.

---

## 4. OpenAI, "Harness engineering: leveraging Codex in an agent-first world"

- URL: `https://openai.com/index/harness-engineering/` — curl 요청에 403(봇 차단 페이지)이 돌아왔다.
- 대조본: `https://web.archive.org/web/20260628021114id_/https://openai.com/index/harness-engineering/` (2026-06-28 스냅숏)과 `https://web.archive.org/web/20261026152238id_/https://openai.com/index/harness-engineering/` (2026-10-26 스냅숏). 두 스냅숏의 본문 텍스트는 줄 단위로 같다. 앞 주소는 아래 보조 저장소의 `sources/sources.json`이 이 글의 archived_url로 지정한 주소다.
- 저자: Ryan Lopopolo — `원문 확인(Wayback 사본)` — "By Ryan Lopopolo, Member of the Technical Staff"
- 날짜: 2026-02-11 — `원문 확인(Wayback 사본)` — "February 11, 2026"
- 수준: `원문 확인(Wayback 사본)`. openai.com 원 URL을 직접 열람하지는 못했다.
- 보조 저장소: `https://github.com/lopopolo/harness-engineering` (CC-BY-4.0, 2026-07-18 생성, 저자 본인의 선집). README에 "fetch helper for agents blocked by the canonical page" 안내가 있고, 그 도우미(`sources/scripts/fetch_openai.py`)는 canonical URL이 실패하면 sources.json의 archived_url을 쓴다. 도우미는 실행하지 않았고, `gh api`로 소스와 sources.json을 텍스트로만 읽어 주소를 얻었다. 저장소의 해설 문서는 이 대장의 근거로 쓰지 않았다.

### 항목

1. `실험 조건: 5개월, 손으로 쓴 코드 0줄` — `원문 확인(Wayback 사본)` — "Over the past five months, our team has been running an experiment: building and shipping an internal beta of a software product with 0 lines of manually-written code." (도입부). 표어: "Humans steer. Agents execute."
2. `시작 시점` — `원문 확인(Wayback 사본)` — "The first commit to an empty repository landed in late August 2025." (We started with an empty git repository)
3. `규모 수치` — `원문 확인(Wayback 사본)` (We started with an empty git repository, 도입부)
   - "Five months later, the repository contains on the order of a million lines of code"
   - "roughly 1,500 pull requests have been opened and merged with a small team of just three engineers driving Codex."
   - "This translates to an average throughput of 3.5 PRs per engineer per day"
   - "the team has grown to now seven engineers."
   - "We estimate that we built this in about 1/10th the time it would have taken to write the code by hand."
4. `AGENTS.md는 백과사전이 아니라 목차` — `원문 확인(Wayback 사본)` (We made repository knowledge the system of record)
   - "give Codex a map, not a 1,000-page instruction manual."
   - "So instead of treating AGENTS.md as the encyclopedia, we treat it as the table of contents."
   - "A short AGENTS.md (roughly 100 lines) is injected into context and serves primarily as a map, with pointers to deeper sources of truth elsewhere."
5. `계획을 저장소에 커밋한다` — `원문 확인(Wayback 사본)` — "Plans are treated as first-class artifacts." / "complex work is captured in execution plans with progress and decision logs that are checked into the repository." (같은 절. 배치도에 `docs/exec-plans/active/`, `completed/`, `tech-debt-tracker.md`가 있다.)
6. `린트 오류 메시지에 수정 지시를 넣는다` — `원문 확인(Wayback 사본)` — "Because the lints are custom, we write the error messages to inject remediation instructions into agent context." (Enforcing architecture and taste)
7. `doc-gardening 에이전트` — `원문 확인(Wayback 사본)` — "A recurring “doc-gardening” agent scans for stale or obsolete documentation that does not reflect the real code behavior and opens fix-up pull requests." (We made repository knowledge the system of record)
8. `에이전트가 못 보는 지식은 없는 것` — `원문 확인(Wayback 사본)` — "From the agent’s point of view, anything it can’t access in-context while running effectively doesn’t exist." (Agent legibility is the goal)
9. `엔트로피 정리` — `원문 확인(Wayback 사본)` — "Our team used to spend every Friday (20% of the week) cleaning up “AI slop.”" (Entropy and garbage collection). 이후 "golden principles"와 주기적 정리 작업으로 바꿨다.
10. `사람 리뷰는 필수가 아니다` — `원문 확인(Wayback 사본)` — "Humans may review pull requests, but aren’t required to." (Redefining the role of the engineer)
11. `장시간 단일 실행` — `원문 확인(Wayback 사본)` — "We regularly see single Codex runs work on a single task for upwards of six hours" (Increasing application legibility)
12. `결론` — `원문 확인(Wayback 사본)` — "Our most difficult challenges now center on designing environments, feedback loops, and control systems" (What we’re still learning). 이 문장은 5번 Fowler 글에도 인용되어 있다.

### 수업에 쓸 때 주의

- 엔지니어 수는 3명으로 시작해 지금 7명이다. 1,500 PR은 3명과 같은 문장에 있다. 7명이 1,500 PR을 냈다고 쓰면 틀린다.
- 100만 줄은 원문이 "on the order of"(대략)라고 한 추정치다. "5개월"은 2025년 8월 말 첫 커밋 기준이다.
- 내부 베타 제품 하나의 사례 보고이고 통제 실험이 아니다. 원문도 일반화를 유보한다: "should not be assumed to generalize without similar investment" (Increasing levels of autonomy)
- 원 URL이 봇을 막으므로 수강생이 curl이나 WebFetch로 다시 확인하면 실패할 수 있다. 대조본 주소를 함께 준다.

---

## 5. Birgitta Böckeler, "Harness engineering for coding agent users" (martinfowler.com)

- URL: `https://martinfowler.com/articles/harness-engineering.html` (200, 리다이렉트 없음)
- 제목: 페이지 제목은 "Harness engineering for coding agent users"다. "Harness engineering"만으로 부르면 제목과 다르다.
- 저자: Birgitta Böckeler (Thoughtworks Distinguished Engineer)
- 날짜: 2026-04-02 — `원문 확인` — "02 April 2026". 첫 메모: "17 February 2026: published my initial memo on Harness Engineering" (Significant Revisions). 원문: "This article supersedes that memo, so we have redirected the original memo URL to this page"
- 수준: `원문 확인`

### 항목

1. `에이전트 = 모델 + 하네스` — `원문 확인` — "Agent = Model + Harness" (도입부). 글의 범위는 코딩 에이전트 사용자가 만드는 바깥 하네스(outer harness)다.
2. `Guides(피드포워드)` — `원문 확인` — "Guides (feedforward controls) - anticipate the agent's behaviour and aim to steer it before it acts." (Feedforward and Feedback)
3. `Sensors(피드백)` — `원문 확인` — "Sensors (feedback controls) - observe after the agent acts and help it self-correct." 예: "custom linter messages that include instructions for the self-correction - a positive kind of prompt injection." (같은 절)
4. `한쪽만 쓰면 생기는 일` — `원문 확인` — "an agent that keeps repeating the same mistakes (feedback-only) or an agent that encodes rules but never finds out whether they worked (feed-forward-only)."
5. `Computational` — `원문 확인` — "Computational - deterministic and fast, run by the CPU." (Computational vs Inferential)
6. `Inferential` — `원문 확인` — "Inferential - Semantic analysis, AI code review, “LLM as judge”." (같은 절)
7. `Harnessability` — `원문 확인` — 한 문장짜리 정의는 없다. 절 첫 문장: "Not every codebase is equally amenable to harnessing." (Harnessability). 관련 용어 ambient affordances(Ned Letcher): "structural properties of the environment itself that make it legible, navigable, and tractable to agents operating within it." (Ambient affordances)
8. `조향 루프` — `원문 확인` — "Whenever an issue happens multiple times, the feedforward and feedback controls should be improved" (The steering loop)
9. `규제 범주 세 가지` — `원문 확인` — 절 제목 "Maintainability harness", "Architecture fitness harness", "Behaviour harness" (Regulation categories)
10. `사람의 역할` — `원문 확인` — "A good harness should not necessarily aim to fully eliminate human input, but to direct it to where our input is most important." (The role of the human)

### 수업에 쓸 때 주의

- harnessability의 정의 문장을 지어내지 않는다. 절 첫 문장과 원문의 예(강타입 언어의 타입 검사, 분명한 모듈 경계, Spring 같은 프레임워크)로 설명한다.
- 원문 예시 표에서 AGENTS.md와 Skills는 feedforward, Inferential로 분류되어 있다.
- 글 말미에 "GenAI (Claude and Claude Code) was used for research, pulling in relevant ideas from existing notes, and polishing the language."라고 밝힌다.
- 철자는 영국식(behaviour)이다.

---

## 6. Claude Code 공식 문서 (code.claude.com)

- 색인: `https://code.claude.com/docs/llms.txt` (200)
- 수준: `원문 확인` (각 페이지의 `.md` 판을 grep 대조, HTML 페이지 200 확인). 문서는 계속 바뀌므로 확인일 2026-11-05 기준이다.

### (a) `/insights`

- URL: `https://code.claude.com/docs/en/commands`, `https://code.claude.com/docs/en/costs#analyze-your-usage-patterns`, `https://code.claude.com/docs/en/claude-directory`
- `공식 내장 명령이다` — `원문 확인` — "Generate an HTML report analyzing your recent sessions on this machine" (Commands 표의 `/insights` 행). 같은 행: "Not available in cloud sessions"
- `무엇을 분석하나` — `원문 확인` — "It analyzes your recent sessions on this machine and writes an HTML report covering what you work on, friction points such as misunderstood requests or buggy code, and suggestions for using Claude Code more effectively." / "A single run analyzes up to 200 sessions it hasn't seen before and skips very short ones." (Analyze your usage patterns)
- `보고서 위치` — `원문 확인` — "Claude Code writes the latest report to ~/.claude/usage-data/report.html and saves a timestamped copy of each run in the same directory" (같은 절). `.claude` 디렉터리 문서의 표: "Past /insights reports and the cached analysis data used to build them" (`~/.claude/usage-data/` 행)
- `모델을 쓰는가` — `원문 확인` — "The analysis runs through the same provider and account as your regular sessions, and the tokens count against your plan or API usage." 토큰을 쓰므로 모델을 호출한다는 것은 이 문장에서 나온 추론이다. 어떤 모델과 프롬프트를 쓰는지는 문서에 없다.
- 범위: "Sessions from other devices and claude.ai aren't included."

### (b) Plan mode

- URL: `https://code.claude.com/docs/en/permission-modes#analyze-before-you-edit-with-plan-mode`
- `정의` — `원문 확인` — "Plan mode tells Claude to research and propose changes without making them." / "Claude reads files, runs shell commands to explore, and writes a plan, but does not edit your source."
- `편집 차단과 예외` — `원문 확인` — "Except in interactive terminal sessions with bypass permissions available, edits stay blocked until you approve the plan."
- `진입` — `원문 확인` — "Enter plan mode by pressing Shift+Tab or prefixing a single prompt with /plan." CLI: `claude --permission-mode plan`
- `계획 파일 위치` — `원문 확인` — "The current session's own plan files in ~/.claude/plans/, or in the plansDirectory" (permission-modes). `.claude` 디렉터리 표: "Plan files written during plan mode" (`plans/` 행)

### (c) Hooks — PreToolUse 결정 값

- URL: `https://code.claude.com/docs/en/hooks#pretooluse-decision-control`, `https://code.claude.com/docs/en/hooks-guide`
- `네 가지 결과` — `원문 확인` — "This gives it richer control: four outcomes (allow, deny, ask, or defer) plus the ability to modify tool input before execution."
- `defer 조건` — `원문 확인` — "ends the turn so the tool can be resumed later, and requires non-interactive mode with the -p flag."
- `폐기된 값` — `원문 확인` — "The deprecated values "approve" and "block" map to "allow" and "deny" respectively."
- `exit 2` — `원문 확인` — "Exit with code 2 to block the action." (Exit code 2)
- `결정론적 통제` — `원문 확인` — "which gives you deterministic control: certain actions always happen rather than relying on the LLM to choose to run them." (hooks-guide 도입)

### (d) Memory — CLAUDE.md 로드와 auto memory

- URL: `https://code.claude.com/docs/en/memory` (#how-claude-md-files-load, #agents-md, #auto-memory)
- `상위 디렉터리` — `원문 확인` — "Claude Code loads CLAUDE.md and CLAUDE.local.md from your current working directory and every directory above it." / "All discovered files are concatenated into context rather than overriding each other."
- `하위 디렉터리` — `원문 확인` — "Files in subdirectories load on demand." / "Instead of loading them at launch, Claude Code loads each one once Claude reads, writes, or edits another file in that subdirectory."
- `AGENTS.md` — `원문 확인` — "By default, Claude reads AGENTS.md only when you have no CLAUDE.md in your working directory or above it." (문서는 AGENTS.md 직접 읽기에 v2.1.277 이상이 필요하다고 적는다.)
- `auto memory 위치` — `원문 확인` — "Each project gets its own memory directory at ~/.claude/projects/<project>/memory/." / "The <project> path is derived from the git repository, so all worktrees and subdirectories within the same repo share one auto memory directory."
- `로드량` — `원문 확인` — "The first 200 lines of MEMORY.md, or the first 25KB, whichever comes first, are loaded at the start of every conversation."
- `기본값` — `원문 확인` — "Auto memory is on by default in local sessions."

### (e) 세션 transcript 저장 위치

- URL: `https://code.claude.com/docs/en/sessions#where-transcripts-are-stored`, `https://code.claude.com/docs/en/claude-directory`
- `위치` — `원문 확인` — "By default, Claude Code stores transcripts as JSONL at ~/.claude/projects/<project>/<session-id>.jsonl, where <project> is your working directory path with non-alphanumeric characters replaced by -."
- `형식은 내부용` — `원문 확인` — "The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release."
- `내용` — `원문 확인` — "Conversation transcript: messages, tool calls, and tool results" (`.claude` 디렉터리 표의 `projects/<project>/<session>.jsonl` 행)
- `보존 기간` — `원문 확인` — cleanupPeriodDays에 대해 "The default is 30 days and the minimum is 1" (claude-directory)

### 수업에 쓸 때 주의

- transcript 폴더의 `<project>`는 작업 디렉터리 경로에서, auto memory의 `<project>`는 git 저장소에서 정해진다. 같은 저장소의 하위 폴더에서 실행하면 transcript 폴더는 달라지고 auto memory는 공유된다(두 문장을 대조한 해석).
- 문서가 JSONL 형식을 내부용이라고 명시하므로, transcript를 직접 파싱하는 실습은 버전마다 깨질 수 있다고 함께 알려야 한다.
- `/insights`는 사용자의 요금제나 API 토큰을 쓴다. 저장소 AGENTS.md의 비용 고지 규칙에 맞춰 실행 전에 고지한다.
- 1번 플레이북의 "Claude cannot edit files until the engineer accepts the plan"과 "allow, ask, or block"은 (b), (c)의 공식 문서 표현과 다르다.
- 문서에 적힌 버전 번호(v2.1.xxx)는 확인일 기준이다.

---

## 7. Sebastian Raschka, "Components of A Coding Agent"

- URL: `https://magazine.sebastianraschka.com/p/components-of-a-coding-agent`
- 저자: Sebastian Raschka, PhD
- 날짜: 2026-04-04 — `원문 확인` — "Apr 04, 2026"
- 부제: "How Coding Agents Use Tools, Memory, and Repo Context to Make LLMs Work Better in Practice"
- 수준: `원문 확인`

### 항목

1. `여섯 구성요소` — `원문 확인` — "In this article, I lay out six of the main building blocks of a coding agent." 절 제목과 예제 코드 주석의 이름이 다르다.

| # | 절 제목 (원문) | 예제 코드 주석 (원문) |
|---|---|---|
| 1 | "1. Live Repo Context" | "# 1) Live Repo Context -> WorkspaceContext" |
| 2 | "2. Prompt Shape And Cache Reuse" | "# 2) Prompt Shape And Cache Reuse -> build_prefix, memory_text, prompt" |
| 3 | "3. Tool Access and Use" | "# 3) Structured Tools, Validation, And Permissions" |
| 4 | "4. Minimizing Context Bloat" | "# 4) Context Reduction And Output Management -> clip, history_text" |
| 5 | "5. Structured Session Memory" | "# 5) Transcripts, Memory, And Resumption" |
| 6 | "6. Delegation With (Bounded) Subagents" | "# 6) Delegation And Bounded Subagents -> tool_delegate" |

2. `하네스 정의` — `원문 확인` — "Agent harness: the software scaffold around an agent that manages context, tool use, prompts, state, and control flow"
3. `모델 품질처럼 보이는 것의 상당 부분은 맥락 품질` — `원문 확인` — "A lot of apparent “model quality” is really context quality." (4. Minimizing Context Bloat)
4. `예제 저장소` — 본문이 `https://github.com/rasbt/mini-coding-agent`를 가리킨다. `gh api`로 저장소가 있는 것만 확인했다(2026-04-02 생성). 코드는 읽지 않았다.

### 수업에 쓸 때 주의

- 3~6번은 절 제목과 코드 주석 이름이 다르다. 슬라이드에는 한쪽을 골라 쓰고 어느 쪽인지 밝힌다.
- 저자가 직접 "I use the terms “coding agent” and “coding harness” somewhat interchangeably for simplicity."라고 밝힌다.
- 페이지 아래 댓글은 근거로 쓰지 않는다.

---

## 확인 못 한 것

- `https://openai.com/index/harness-engineering/` 원 URL 직접 열람: curl에 403. Wayback 사본 두 개(2026-06-28, 2026-10-26)로만 대조했다.
- SDLC 플레이북 PDF 판의 내용.
- SDLC 플레이북 한국어판의 측정 지표 한국어 문장: 한국어판에 존재하지 않는다(영어 그대로). 한국어 대응문이 필요하면 저자 번역으로 표시해야 한다.
- `/insights`가 쓰는 모델, 프롬프트, 분석 방식의 세부: 공식 문서에 없다.
- claude-quickstarts `autonomous-coding`의 코드와 프롬프트 내용(디렉터리 존재와 README의 파일 이름만 확인), rasbt/mini-coding-agent의 코드.
- Fowler의 후속 글("More on sensors")과 2026-02-17 초기 메모(원문에 따르면 현재는 본문 URL로 리다이렉트된다).
- Anthropic 두 글의 그림과 영상 안의 텍스트.
- lopopolo/harness-engineering 저장소의 해설 문서 내용(archived_url 확인 용도로만 썼다).
