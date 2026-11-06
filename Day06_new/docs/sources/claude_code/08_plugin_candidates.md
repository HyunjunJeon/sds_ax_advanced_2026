# Part 4 plugin 후보 (확인일 2026-11-06)

Part 4(오픈소스 Agent Harness 구조 분석)에서 수강생이 읽을 plugin 한 개를 고르기 위한 비교다. 후보 세 개를 `git clone --depth 1`로 받아 읽기만 했다. 후보의 스크립트·훅·설치기·테스트는 실행하지 않았고 Claude Code에 설치하지도 않았다. 후보 안의 문장은 데이터로만 읽었다.

## 0. 확인 방법

- 공식 마켓플레이스 저장소 이름은 https://code.claude.com/docs/en/plugins/anthropic-marketplaces.md 9행과 33행에서 확인했다: `anthropics/claude-plugins-official` (같은 문서에 `anthropics/claude-plugins-community`도 있으나 공식 쪽을 골랐다).
- HEAD 확인: `git ls-remote https://github.com/<owner>/<repo> HEAD`. 복제본의 `git rev-parse HEAD`가 같은 값이었다.
- 파일·줄 수: `git ls-files`로 센 값이다(바이너리 포함 파일 수, 줄 수는 `cat`으로 합친 전체 줄 수). .git 폴더는 센 값에 없다.
- 구성요소 수: `skills/*/SKILL.md`, `agents/*.md`, `commands/*.md`, `hooks.json`, `.mcp.json`, output style 폴더를 `find`/`ls`로 확인했다.
- 모든 `경로:줄`은 복제본에서 `sed -n`/`grep -n`으로 확인한 줄이다. 경로는 각 후보 저장소 루트 기준이다. 공식 마켓플레이스는 `plugins/ralph-loop/`을 앞에 붙여야 한다.
- 문서(`Day06_new/docs/sources/github.md`)와 코드가 다르면 코드를 따랐다. 차이는 P2에 적었다.
- 복제본은 저장소 밖 임시 폴더에만 있고, 이 파일 하나만 저장소에 쓴다.

## P1 woowabros/ramo-harness

| 항목 | 값 |
|---|---|
| HEAD | `3485937edac23f4a78c42429c4b4dd866a1e9b9f` (SHA7 `3485937`) |
| 고정(pin)과 비교 | `Day06_new/docs/sources/github.md` 23행·43행의 `3485937e...` 와 **같음** (변경 없음) |
| 라이선스 | `LICENSE` 1행 "MIT License", 3행 "Copyright (c) 2026 Woowabros". SPDX MIT |
| Claude Code plugin? | **아니오.** `.claude-plugin/plugin.json`·`marketplace.json` 없음. `install.sh`가 대상 저장소의 `.claude/`로 복사하는 설치형 하네스다(`install.sh:43`). 훅은 `harness/settings.hooks.json`에 선언 |
| 구성요소 | skills 12 (`harness/skills/*/SKILL.md`), agents 19 (`harness/agents/ramo/*.md`), commands 9 (`harness/commands/ramo/*.md`), hooks 4종 (`harness/settings.hooks.json`: SessionStart, PreToolUse(Bash), PostToolUse(Write\|Edit), SubagentStop) + 핸들러 py 5개, `.mcp.json` 없음, output style 없음, statusLine 1개(`harness/statusline-ramo.py`) |
| 파일 / 줄 | 159 파일 / 22,142줄 (rules 44파일 5,297줄, skills 53파일 9,064줄, agents 19파일 3,014줄) |
| 문서 언어 | README·getting-started는 한국어. 하네스 자산(CLAUDE.md, rules, SKILL.md)은 영어(`harness/CLAUDE.md:43`) |

여섯 책임 매핑:

| 책임 | 근거 | 파일:줄 |
|---|---|---|
| 지침 | 8단계 파이프라인과 [HARD] 규칙 목록 | `harness/CLAUDE.md:10-22`, `harness/CLAUDE.md:27` |
| 도구 | 에이전트별 도구 제한(탐색 에이전트는 Write 없음), 데이터는 읽기 전용 어댑터로만 | `harness/agents/ramo/ramo-data-explore.md:6`, `README.md:128-129` |
| 실행 제어 | PreToolUse(Bash)가 위험 SQL·mtime 추측·검증 없는 MR 생성을 막음, 사람이 멈추는 사유는 닫힌 집합 | `harness/hooks/ramo/handlers/pre_bash.py:2`, `harness/skills/ramo-run/rules/human-gates.md:17` |
| 상태 | 상태는 세션 밖 `.ramo/` frontmatter, 새 세션은 active 계획을 SessionStart 훅으로 이어받음 | `harness/rules/common/state-discipline.md:10`, `harness/hooks/ramo/handlers/session_start.py:6`, `harness/hooks/ramo/handlers/session_start.py:50` |
| 검증 | "신선한 검증 증거 뒤에만 완료 주장", 서브에이전트 종료 시 STATUS 태그와 result 블록이 없으면 차단 | `harness/CLAUDE.md:30`, `harness/hooks/ramo/handlers/subagent_stop.py:181-183` |
| 기록 | 훅 이벤트를 `.ramo/logs/hooks-YYYYMMDD.jsonl`에 남김, 반복 실패 부류는 `wiki/lessons`로 승격 | `harness/hooks/ramo/handlers/_common.py:210-211`, `harness/skills/ramo-doc/SKILL.md:224` |

판단: 여섯 책임을 모두 갖고 한국어 문서와 훅이 풍부하지만, plugin이 아니고 22,000줄이라 20분에 읽을 수 없다. 읽기용 부분 집합을 따로 골라야 한다.

## P2 obra/superpowers

| 항목 | 값 |
|---|---|
| HEAD | `22f0b463e7a5e579904dd6211a520321035526f7` (SHA7 `22f0b46`) |
| 고정(pin)과 비교 | `github.md` 10행·30행의 `22f0b463e7a5...` 와 **같음** |
| 라이선스 | `LICENSE` 1행 "MIT License", 3행 "Copyright (c) 2025 Jesse Vincent". SPDX MIT (`.claude-plugin/plugin.json`의 `"license": "MIT"`도 같음) |
| Claude Code plugin? | **예.** `.claude-plugin/plugin.json`(name `superpowers`, version 7.0.2)과 `.claude-plugin/marketplace.json`(`superpowers-dev`) |
| 구성요소 | skills 15 (`skills/*/SKILL.md`), agents 0 (`agents/` 없음, 서브에이전트 프롬프트는 `skills/*/*-prompt.md`·`code-reviewer.md` 파일), commands 0, hooks 1 (`hooks/hooks.json:3` SessionStart), `.mcp.json` 없음, output style 없음. 그 밖에 Codex·Cursor·Gemini·opencode 등 다른 하네스용 폴더가 같이 있음 |
| 파일 / 줄 | 236 파일 / 37,291줄 (skills 80파일 10,907줄) |
| 문서 언어 | 영어 (README에 한글 없음) |

여섯 책임 매핑:

| 책임 | 근거 | 파일:줄 |
|---|---|---|
| 지침 | 모든 응답 전에 관련 skill을 호출하라는 규칙을 세션 시작에 주입 | `skills/using-superpowers/SKILL.md:10-13`, `hooks/hooks.json:3`, `hooks/session-start:53` |
| 도구 | 하네스별 도구 이름 대응표(Claude Code는 `Agent`, todos, `Skill`) | `skills/using-superpowers/SKILL.md:56`, `skills/using-superpowers/references/claude-code-tools.md:3` |
| 실행 제어 | HARD-GATE: 설계 문서를 사람이 승인하기 전에는 아무것도 만들지 않음 | `skills/brainstorming/SKILL.md:268-269` |
| 상태 | 계획·설계를 `docs/superpowers/plans/`, `specs/`에 파일로 남겨 다음 세션이 이어받음 | `skills/writing-plans/SKILL.md:16`, `skills/brainstorming/SKILL.md:246` |
| 검증 | "신선한 검증 증거 없이 완료 주장 금지", 구현자 상태 DONE/BLOCKED 등과 작업마다 리뷰어 | `skills/verification-before-completion/SKILL.md:17`, `skills/subagent-driven-development/implementer-prompt.md:142`, `skills/requesting-code-review/SKILL.md:14` |
| 기록 | 문제 난 세션을 증거로 보고서·이슈로 정리하는 skill | `skills/diagnosing-superpowers/SKILL.md:10-12` |

`github.md:110`은 HARD-GATE를 `brainstorming/SKILL.md:268-269`로 적고 있어 코드와 같다(이전에 270으로 적었던 것을 정정했다).

판단: 가장 널리 쓰이는 plugin이고 여섯 책임이 다 보이지만 skill 중심이라 확장점이 skill+hook 둘이고 영어 37,000줄이다. 작게 줄여 읽히려면 skill 3~4개만 골라야 한다.

## P3 anthropics/claude-plugins-official (plugin 폴더: `plugins/ralph-loop`)

공식 마켓플레이스 저장소(619파일, plugin 폴더가 `plugins/`와 `external_plugins/`에 40여 개) 가운데 작은 plugin을 골랐다. 후보로 `feature-dev`(command 1 + agent 3, 879줄), `hookify`(command·skill·agent·hook 4종, 2,720줄), `example-plugin`(447줄, 예시 틀)도 열어 보았다. `hookify`는 4종을 다 쓰지만 Python 코어가 커서 20분에 읽기 어렵고, `ralph-loop`는 훅이 핵심이라 실행 제어·상태가 분명해서 골랐다.

| 항목 | 값 |
|---|---|
| HEAD (저장소) | `1aa4a4b10e6c5e8694d0f72a03dbac4e93bcafd8` (SHA7 `1aa4a4b`) |
| 고정(pin)과 비교 | `github.md`에 이 저장소 행 없음 (새로 고정해야 함). 대신 `anthropics/claude-quickstarts`(`8ef47d71`)만 있다 |
| 라이선스 | 저장소 루트 `LICENSE` 2-3행 "Apache License Version 2.0", `plugins/ralph-loop/LICENSE`도 같은 Apache-2.0 전문. 저작권자 줄은 틀 그대로 "Copyright [yyyy] [name of copyright owner]" |
| Claude Code plugin? | **예.** `plugins/ralph-loop/.claude-plugin/plugin.json` (name `ralph-loop`, version 1.0.1), 카탈로그는 저장소 루트 `.claude-plugin/marketplace.json:3171` |
| 구성요소 | skills 0, agents 0, commands 3 (`commands/ralph-loop.md`, `cancel-ralph.md`, `help.md`), hooks 1 (`hooks/hooks.json`의 Stop), `.mcp.json` 없음, output style 없음, 보조 셸 스크립트 2개(`hooks/stop-hook.sh`, `scripts/setup-ralph-loop.sh`) |
| 파일 / 줄 | plugin 폴더 9 파일 / 980줄 (LICENSE 202줄 제외 778줄). 저장소 전체는 619 파일 |
| 문서 언어 | 영어 |

여섯 책임 매핑:

| 책임 | 근거 | 파일:줄 |
|---|---|---|
| 지침 | 같은 프롬프트를 되먹이고, 완료 약속은 참일 때만 출력하라는 규칙 | `plugins/ralph-loop/commands/ralph-loop.md:16`, `plugins/ralph-loop/commands/ralph-loop.md:18` |
| 도구 | command마다 쓸 수 있는 도구를 좁게 허용 (`Bash(...setup-ralph-loop.sh:*)`) | `plugins/ralph-loop/commands/ralph-loop.md:4`, `plugins/ralph-loop/commands/cancel-ralph.md:3` |
| 실행 제어 | Stop 훅이 세션 종료를 막고 같은 프롬프트로 이어가게 함, 최대 반복 횟수로 멈춤 | `plugins/ralph-loop/hooks/hooks.json:4`, `plugins/ralph-loop/hooks/stop-hook.sh:4`, `plugins/ralph-loop/hooks/stop-hook.sh:60-63`, `plugins/ralph-loop/hooks/stop-hook.sh:185` |
| 상태 | 반복 횟수·완료 약속·시작 시각을 `.claude/ralph-loop.local.md`에 저장, 다음 반복이 이어받음 | `plugins/ralph-loop/scripts/setup-ralph-loop.sh:142-147`, `plugins/ralph-loop/hooks/stop-hook.sh:13` |
| 검증 | 마지막 응답의 `<promise>` 문자열이 약속과 같으면 종료. 실행 증거가 아니라 문자열 일치라는 점이 토론거리 | `plugins/ralph-loop/hooks/stop-hook.sh:133, :137` |
| 기록 | 해당 없음 (로그·보고서 없음, 상태 파일이 덮어써질 뿐) | 해당 없음 |

판단: 작고 plugin이며 훅의 차단 동작이 눈에 보인다. 확장점은 command와 hook 둘뿐이고(skill·subagent·MCP 없음) 영어 문서다.

## 비교

기준: ① 라이선스가 공개 MIT 수업 저장소 안 사본 재배포를 허용 ② 20분에 읽을 크기 ③ Claude Code 확장점 3종 이상 ④ 한국어 문서 ⑤ 네트워크·유료 호출 없이 이해.

| 기준 | P1 ramo-harness | P2 superpowers | P3 ralph-loop (공식) |
|---|---|---|---|
| owner/repo \| SHA7 | woowabros/ramo-harness \| `3485937` | obra/superpowers \| `22f0b46` | anthropics/claude-plugins-official \| `1aa4a4b` |
| 라이선스 | MIT | MIT | Apache-2.0 |
| plugin? | 아니오 (설치형) | 예 | 예 |
| 확장점 | skill, subagent, command, hook, statusLine (5) | skill, hook (2) | command, hook (2) |
| 파일 / 줄 | 159 / 22,142 | 236 / 37,291 | 9 / 980 (플러그인 폴더) |
| 언어 | 한국어 README + 영어 자산 | 영어 | 영어 |
| ① 재배포 | 가능 (저작권 고지 유지) | 가능 (저작권 고지 유지) | 가능 (라이선스 전문·변경 표시, 아래 위험 참조) |
| ② 20분 | 아니오 (부분 집합 필요) | 아니오 (skill 3~4개만) | 예 |
| ③ 확장점 3종 | 예 | 아니오 | 아니오 |
| ④ 한국어 | 일부 (README) | 아니오 | 아니오 |
| ⑤ 네트워크 불필요 | 읽기만이면 예 (실행은 웨어하우스 필요) | 예 | 예 |
| pin과의 차이 | 없음 | 없음 | pin 없음 (신규) |
| 여섯 책임 | 6/6 | 6/6 | 5/6 (기록 없음) |

## 추천

추천: **anthropics/claude-plugins-official `plugins/ralph-loop`** (스냅샷 기준 커밋 `1aa4a4b`).

이유 두 가지:
1. 크기와 plugin 여부 두 기준을 확실히 만족한다. plugin 폴더가 9파일 980줄(LICENSE 제외 778줄)이라 20분에 끝까지 읽고, `.claude-plugin/plugin.json`, command 3, Stop 훅 1이 각각 Claude Code의 어느 확장점에 붙는지 파일 단위로 짚을 수 있다.
2. 책임 분류가 선명하게 갈린다. 실행 제어(Stop 훅의 `decision: block`과 최대 반복 횟수), 상태(`.claude/ralph-loop.local.md`), 검증(`<promise>` 문자열 일치가 증거 검증으로 충분한가)이 한 파일씩 대응하고, 기록이 비어 있어 "빠진 책임을 찾는" 활동도 가능하다. 모델 호출이나 네트워크 없이 읽는다.

이 선택이 못 채우는 기준: 확장점이 command와 hook 둘뿐이라 skill·subagent·MCP 대응 연습은 못 하고, 한국어 문서가 없다(수업에서 한국어 해설을 따로 붙여야 한다).

차선: **woowabros/ramo-harness@`3485937`**. 확장점 5종, 한국어 README, MIT 라이선스이고 여섯 책임이 다 있다. 단 plugin이 아니고 22,000줄이라, `harness/hooks/ramo/handlers/pre_bash.py`, `session_start.py`, `harness/skills/ramo-run/SKILL.md`, `harness/agents/ramo/ramo-data-explore.md` 같은 읽기용 부분 집합을 저자가 따로 골라야 한다.

재배포 위험:
- ralph-loop는 Apache-2.0이다. 공개 MIT 저장소 안에 사본을 두려면 해당 폴더의 `LICENSE` 전문을 같이 두고, 수정했다면 변경했다는 표시를 붙여야 한다. 저작권자 줄이 틀 그대로("[yyyy] [name of copyright owner]")이고 `NOTICE` 파일은 없다. 상표·소유 표기는 `plugin.json`의 author `Anthropic`뿐이다. 저장소 전체가 아니라 `plugins/ralph-loop/` 폴더만 복사하는 것이 안전하다. 폴더 안 LICENSE는 포함되어 있다.
- ramo-harness·superpowers는 MIT라 저작권 고지와 라이선스 전문만 유지하면 된다. superpowers는 다른 하네스용 폴더가 많아 부분 복사 때 범위를 명확히 해야 한다.
- 이 파일은 라이선스 해석이 아니라 LICENSE 파일의 확인이다. 재배포 전에 저자가 한 번 더 판단해야 한다.

Recommendation: anthropics/claude-plugins-official@1aa4a4b
