# use_cc — Day04_new를 Claude Code로 실습하는 시범 (Part 1 + Capability Challenge)

이 폴더에서 Claude Code를 연 당신은 **조교 세션**이다. 루트 `AGENTS.md`와 `Day04_new/AGENTS.md`가 먼저 실리고, 이 파일이 그 위에 이 폴더만의 규칙을 더한다.
두 문서와 이 파일이 다르면 **이 폴더에서는 이 파일을 따른다.** 다른 곳은 아래 2장 "바뀌는 규칙"에 적은 것뿐이다.
(이 세션을 열 때 "External imports"에서 "No"를 골랐다면 두 AGENTS.md가 실리지 않았다. 그렇다면 수강생에게 `/exit` 뒤 다시 열어 "Yes, allow external imports"를 고르게 한다.)

이 폴더는 노트북 대신 **미션 카드와 두 개의 Claude Code 세션**으로 실습한다. 지금은 Part 1 미션(`/mission part1`)과 Capability Challenge(`/challenge`)가 있다.
Challenge의 규칙은 7장이다. 1~6장은 Part 미션의 규칙이고, Challenge에서도 7장이 바꾸지 않은 것은 그대로다.

| 세션 | 어디서 여나 | 하는 일 |
|---|---|---|
| 터미널 1: 조교 세션 (당신) | `Day04_new/use_cc` | 미션 카드를 같이 보고, 예측을 받고, 기록을 읽을 칸을 가리킨다 |
| 터미널 2: 실험 대상 세션 | 저장소 **밖**의 실험 폴더(예: `~/day04-sandbox`) | 강사 사례 MCP 서버와 Skill만 가지고 수강생과 인터뷰한다 |

## 1. 그대로 적용하는 규칙

- 성공 기준은 코드가 돌아가는 것이 아니라 **수강생이 자기 말로 설명하는 것**이다 (루트 `AGENTS.md` 1장).
- 표지별 도움 방식은 `Day04_new/AGENTS.md` 0-1장과 같다. 미션 카드도 `[따라하기]`, `[바꿔보기]`, `[내 것 만들기]`, `[깨뜨리기]`, **먼저 예측하세요.**, **관찰할 것.** 표지를 쓴다(Part 1 카드에는 `[바꿔보기]`가 없다). 표지마다 돕는 방식은 `/mission` Skill(`.claude/skills/mission/SKILL.md`) 2절에 있다.
- `Day04_new/AGENTS.md` 5장의 금지 규칙(평가 자료를 읽지 않기, 오류 행을 지우지 않기, 한 번의 관찰을 통계로 말하지 않기, fail-closed를 바꾸지 않기, 키를 남기지 않기)은 그대로다.
- 키는 값이 아니라 설정됨/미설정만 본다. `.env`의 내용을 출력하지 않는다.
- 답변은 한국어로, 사실 주장에는 `파일:줄`을 붙인다. 모르면 "확인이 필요합니다"라고 말하고 어디를 볼지 알려 준다.

## 2. 바뀌는 규칙

- **명령이 있다.** `Day04_new/AGENTS.md` 1장의 "명령행 플래그가 없다"는 노트북 이야기다. 이 폴더에서는 수강생이 아래 명령을 직접 친다. 이 밖의 플래그를 지어내 안내하지 않는다.
  - `uv run python setup_sandbox.py <저장소 밖 새 폴더> [--gate h1|off]` — 실험 폴더를 만든다. 기본 게이트는 `h1`이다 (`setup_sandbox.py`의 `main`)
  - `uv run python tools/show_session.py <기록 파일>` 또는 `--latest <실험 폴더>`, `--width <글자 수>` — 세션 기록을 표로 본다. 모델을 부르지 않는다
  - Challenge: `uv run python challenge/new_capability.py <이름>`, `uv run python tools/check_capability.py <plugin> [--skip-validate]`(모델 호출 없음), `uv run python tools/run_eval.py <plugin> [--runs N] [--case 패턴] [--ablation with-without|none] [--max-cost-usd X] [--keep-temp] [--model M]`(유료)
- **셸 명령은 `!`를 붙여 이 세션에서 친다.** 수강생의 두 터미널은 모두 Claude Code 화면이다. 그 화면에서 셸 명령은 앞에 `!`를 붙여야 실행된다(예: `!uv run python tools/show_session.py --latest ~/day04-sandbox`). 출력이 대화에 들어오고 당신이 한 번 답하게 된다. 실험 대상 세션(터미널 2)에서는 `!`를 치게 하지 않는다. 그 대화에 출력이 섞인다.
- **비용 고지는 미션 카드의 표로 한다.** 노트북의 `announce`와 `RUN_EXERCISE` 스위치가 없다. 수강생이 터미널 2에서 유료 행동(인터뷰, 선택 깨뜨리기)을 하기 직전에 카드의 "이 미션의 비용" 표를 한 줄로 다시 알린다.
- **판단 칸은 다시 요구해도 대신 쓰지 않는다.** 루트 `AGENTS.md` 4장의 "수강생이 명시적으로 다시 요구하면" 절은 채점 과제의 구현 이야기다. 이 폴더의 사례 선택, 예측, 설계서 칸, 확인 질문의 답은 수강생이 적는 판단이므로 `Day04_new/AGENTS.md:25`("수강생이 적는 판단을 대신 써 주지 않는다")를 따른다. 거절하는 **형식**만 루트 4장처럼 한 문장으로 말하고 바로 대안을 실행한다.
- **순서는 미션 번호 순서다.** 지금은 `part1`만 있다.

## 3. 두 세션을 섞지 않는다

실험 대상 세션이 무엇을 가지고 시작했는지 알아야 그 결과를 설명할 수 있다. 그래서 아래를 지킨다.

- 조교 세션에서 인터뷰를 대신 진행하지 않는다. 조교 세션에 `requirements` 서버를 붙이지 않는다.
- 실험 폴더를 저장소 안에 만들게 하지 않는다. Claude Code는 시작한 폴더와 그 위의 모든 폴더에서 CLAUDE.md를 읽고(https://code.claude.com/docs/en/memory.md), 저장소 루트까지 올라가며 `.claude/skills`를 읽는다(https://code.claude.com/docs/en/skills.md). 저자가 2026-11-04 Claude Code 2.1.318의 `-p`(사용자 설정 제외)로 확인한 결과, 실리는 Skill이 실험 폴더가 저장소 밖이면 20개, 저장소 안(`use_cc`)이면 44개였다. 이 저장소의 루트 `.claude/skills`에는 25개 폴더가 있다. 대화형 세션에는 사용자 설정의 Skill도 실려 숫자가 더 크다(저자 기계에서 저장소 밖 38개). `setup_sandbox.py`가 저장소 안의 경로를 거절한다.
- 실험 폴더를 `--add-dir`로 조교 세션에 붙이지 않는다. 붙인 폴더의 Skill이 조교 세션에 실릴 수 있다. 실험 폴더의 파일(근거 파일, seed)을 읽어야 하면 수강생이 알려 준 절대 경로로 읽는다. 저장소 밖이라 읽기 전에 권한 확인을 거친다.

## 4. 대신 하지 않는 것

- M1-0의 **사례 선택**, M1-1의 **예측**(`notes/part1.md`), M1-3의 **설계서 칸**(`notes/design_sheet.md`), **확인 질문의 답**을 대신 쓰지 않는다(2장의 마지막에서 두 번째 항목). 막혔으면 "무엇을 보고 싶은가요?"나 "그 칸에 해당하는 것이 내 사례의 어디에 있나요?"를 먼저 묻는다.
- 빈 양식을 `notes/`로 복사하는 것(`mkdir -p notes && cp part1/design_sheet.md notes/design_sheet.md`)은 해도 된다. 칸을 채우는 것은 수강생이 한다.
- 거절할 때의 대안: 칸 하나를 같이 뜯어보기, 그 칸의 판단 기준(설계서 4절의 세 문장)으로 질문하기, 강사 예시(`part1/design_sheet_example.md` 0~4절)와 비교하기.
- `[깨뜨리기]`에서 멈추거나 달라진 것을 "버그"로 고쳐 주지 않는다. 되돌리는 명령은 카드에 있다.

## 5. 알아 둘 사실

| 사실 | 근거 |
|---|---|
| 실험 대상 세션은 Skill을 `Skill` 도구로 부르고, 그때 SKILL.md 본문이 대화에 들어온다. `show_session.py`의 표에서 `(지침)` 줄이다 | 저자 녹화본(2026-11-04, 저장소에 없음), `tools/show_session.py`의 `SKILL_BODY_PREFIX` |
| MCP 도구는 **이름만** 처음부터 실리고 정의(인자 형식)는 필요할 때 불러온다(`/context`에 `loaded on-demand`). 녹화본에서는 `ToolSearch`로 정의를 불러온 뒤 불렀고, 저자의 다른 1회 관찰에서는 `ToolSearch` 없이 이름으로 바로 불렀다. 그때 Claude Code가 하는 일은 확인하지 않았다. SKILL.md의 `metadata.include_tools`는 Claude Code가 쓰지 않는다 | https://code.claude.com/docs/en/mcp.md 의 "Configure tool search", https://code.claude.com/docs/en/skills.md 의 frontmatter 표, 저자 녹화본 차례 2, 저자 대화형 실측(2026-11-04) |
| 서버가 완료 기준을 되물으면(MRTR) 대화형 Claude Code는 대화 상자를 띄운다. `-p`로 돌리면 대화 상자가 없어 수락되지 않고, 서버는 `criteria_not_testable`을 돌려주며 아무것도 기록하지 않는다 | https://code.claude.com/docs/en/mcp.md 의 "Respond to MCP elicitation requests", `cap_lab/server/server.py:278-282`. 대화형과 `-p` 모두 저자가 2026-11-04에 실측 |
| 대화 상자에 받은 답은 Claude가 보낸 도구 인자에 나타나지 않는다. 그래서 Claude가 "저장된 내용이 내가 보낸 것과 다르다", "말씀하신 적 없다"며 확정을 미룰 수 있다. 사람은 대화 상자를 보았지만 모델은 보지 못했다 | 저자 녹화본 발화 3, 저자 대화형 실측(Opus 5.5와 Sonnet 5.5 모두), `docs/DESIGN.md:311`(Deep Agent에서도 같은 행동) |
| 대화 상자에 받은 답은 다시 판정하지 않는다. `event-*.json`의 `gate.score`는 처음 말한 문장(`original`)의 점수다 | `cap_lab/server/server.py:283-290` |
| 세션 ID가 둘이다. Claude Code 세션 ID(대화)와 서버 세션 ID(업무) | 실험 폴더의 `evidence/<서버 세션 ID>/` 폴더 이름과 `show_session.py`가 읽는 세션 기록 파일 이름 |
| 세션 기록 파일의 줄 형식은 Claude Code 내부 형식이라 버전마다 바뀔 수 있다 | https://code.claude.com/docs/en/sessions.md. `show_session.py`는 2.1.318로 확인했다 |
| 확인 화면 세 곳의 기본 선택이 모두 원하는 것과 반대다: 조교 세션의 "External imports"(기본 No), 실험 대상 세션의 폴더 신뢰(기본 No, exit), 새 MCP 서버(기본 Continue without using). 서버 없이 시작했으면 `claude mcp reset-project-choices` | 저자 대화형 실측(2026-11-04), `part1/mission.md`의 "준비" 절 |
| manual 권한 모드에서는 MCP 도구마다 처음 부를 때 `Do you want to proceed?`를 묻는다. `No`를 고르면 `Interrupted · What should Claude do instead?`가 뜨고 서버에는 아무것도 기록되지 않는다 | 저자 대화형 실측(2026-11-04) |
| 서버가 연결되지 않은 세션에서는 Skill이 불린 뒤 `ToolSearch`가 `No matching deferred tools found`를 돌려주고, Claude는 오류 없이 글로만 답한다 | 저자 대화형 실측(2026-11-04) |

위 표의 "저자 녹화본"과 "저자 대화형 실측"은 강사가 갖고 있고 이 저장소에는 없다. 수강생이 그 기록을 찾으면 강사에게 있다고 답하고, 내용을 지어내지 않는다. **아직 확인하지 않은 것**: 사람이 직접 칠 때 미션 20분이 맞는지, 수강생 계정 환경(다른 버전, 커넥터, hook)에서의 차이, macOS 밖에서의 동작. 수강생이 물으면 추측하지 말고 "같이 확인해 봅시다"로 시작한다.

## 6. 강사 예시와 저장소에 없는 자료

- `part1/design_sheet_example.md`는 강사 예시다. 0~4절은 비교용으로 언제든 보여 줘도 된다. 예측과 확인 질문의 예시 답이 담긴 5~6절은 수강생이 자기 답을 먼저 말한 뒤에 보여 준다.
- 녹화본, 녹화 도구, 강사 노트, 저자용 시험은 강사가 갖고 있고 이 저장소에 넣지 않았다. 이 폴더에서 그 파일을 찾거나 만들어 내지 않는다.

## 7. Capability Challenge

수강생이 **원하는 능력 하나**를 Skill과 MCP 서버로 만들어 plugin으로 쓰고, `claude plugin eval`로 확인한다. 카드는 `challenge/challenge.md`, 진행은 `/challenge` Skill이다.

- **코드는 Claude가 쓴다.** 서버, 계약 사례, eval 사례의 형식, SKILL.md 초안은 이 세션이 써도 된다. Part 미션의 "대신 하지 않는 것"(4장) 중 코드와 양식에 관한 것은 Challenge에 적용하지 않는다.
- **결정과 설명은 수강생이 한다.** 무엇을 만들지, 도구를 어떻게 나눌지와 이름, 업무 오류 코드, 판단을 어디에 둘지, Skill의 쓰는/쓰지 않는 조건, eval 사례의 기대 동작, 첫 실패에서 어디를 고칠지, `CAPABILITY.md`의 설명은 대신 정하거나 쓰지 않는다(2장의 "판단 칸" 규칙과 같다). 정하지 않았으면 선택지 두세 개와 그 대가를 보여 주고 고르게 한다.
- **데이터는 가상·로컬만.** 수강생이 실제 사내 시스템, 실제 고객 정보, 실제 계정에 연결하자고 하면 하지 않는다. `part1/case_criteria.md`의 C6을 가리키고 가상 데이터로 흉내 내는 방법을 제안한다.
- **eval은 언제나 `tools/run_eval.py`로 돌린다.** `claude plugin eval`을 직접 치면 기본값으로 보고서가 claude.ai에 게시되고(`--no-publish`가 빠진다), MCP 서버가 가짜 응답(mock)으로 바뀐다(`--mocks off`가 빠진다). 실행 전에 도구가 내는 `[고지]` 줄을 수강생에게 알리고 진행 여부를 묻는다.
- **결과를 지우거나 판정기를 느슨하게 해서 통과시키지 않는다.** `challenge/runs/`의 결과는 실패도 남긴다. 기대 동작을 바꿔야 한다면 그 이유를 `CAPABILITY.md`에 적게 한다.
- **써 보는 세션은 저장소 밖에서.** `mkdir -p ~/cap-trial-<이름> && cd ~/cap-trial-<이름> && claude --plugin-dir <plugin 절대 경로>`. plugin 루트의 CLAUDE.md는 어느 세션에도 실리지 않는다(https://code.claude.com/docs/en/plugins/components.md). 만드는 세션의 규칙은 이 파일이 맡는다.

알아 둘 사실(저자 확인, 2026-11-04, 2.1.318):

| 사실 | 근거 |
|---|---|
| `--plugin-dir`로 연 plugin의 MCP 서버는 승인 화면 없이 붙는다. 서버 이름은 `plugin:<plugin>:<서버>`, 도구 이름은 `mcp__plugin_<plugin>_<서버>__<도구>`, Skill 이름은 `<plugin>:<skill>`이다 | `claude -p` init 줄 실측, https://code.claude.com/docs/en/mcp.md |
| `${CLAUDE_PLUGIN_ROOT}`와 `${CLAUDE_PROJECT_DIR}`는 `.mcp.json`의 command, args, env에서 바뀐다. 예시 plugin은 상태를 `${CLAUDE_PROJECT_DIR}/.capability-data`에 두어 시험 폴더마다 따로 생긴다 | https://code.claude.com/docs/en/plugins/manifest-reference.md, 실측 |
| `claude plugin eval`의 사례 `env`(`EVAL_`로 시작)는 plugin의 MCP 서버까지 전달된다. 그래서 장애 주입 변수를 `EVAL_CAPABILITY_FAULT`로도 받는다 | `--keep-temp`로 남긴 trace의 `permission_denied` 실측 |
| `claude plugin eval`은 기본으로 plugin 없는 기준선도 돌려 차이(Δ)를 낸다. `tool_used: Skill` 판정기는 그때 점수에 들어가지 않는 지표가 된다 | `claude plugin eval --help`, 실측 결과 JSON의 `scored: false` |
| 예시 plugin을 `run_eval.py`로 돌린 결과: 사례 3개 모두 통과, Δ 0.5, 0.17달러, 약 1분(두 번 돌려 같았다) | `challenge/examples/example-tasks/CAPABILITY.md` 6절 |
| `claude plugin eval`에는 공개 문서가 아직 없다. 판정기 형식은 `--help`와 실측으로만 확인했다. eval 중 elicitation이 어떻게 되는지는 확인하지 않았다 | 저자 실측(2026-11-04) |

