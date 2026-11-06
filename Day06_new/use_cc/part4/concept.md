# Part 4. 오픈소스 Agent Harness 구조 분석 (개념 8분 + 시연 5분)

## 핵심 질문

> **Claude Code 위에 얹는 하네스(plugin)는 어느 확장점에 붙는가? Claude Code를 대체하는 하네스와는 무엇이 다른가?**

이 문서의 Claude Code 사실은 모두 `Day06_new/docs/sources/claude_code/`의 근거 대장에 항목이 있는 것만 적는다. 문장 뒤의 `T14` 같은 표시는 그 항목 번호이고, 누르면 대장 파일로 간다. 대장에 없거나 확인하지 못한 것은 "확인 필요"라고 적는다. 이 Part는 읽기만 한다. 남의 plugin은 설치하지도 실행하지도 않는다.

---

## 1. plugin은 확장점을 한 묶음으로 싣는다

- plugin은 Skill, agent, hook, MCP 서버 같은 구성요소를 담은 폴더이고, Claude Code가 이것을 한 단위로 설치하고 싣는다. ([T14](../../docs/sources/claude_code/02_tools.md))
- 켠 plugin은 그것을 쓰는 세션만이 아니라 모든 세션의 일부가 된다. ([T14](../../docs/sources/claude_code/02_tools.md))
- 확장 장치 비교표에서 plugin은 CLAUDE.md, Skill, 하위 에이전트, hook, MCP를 묶어 배포하는 단위다. ([I15](../../docs/sources/claude_code/01_instructions.md))
- 그래서 남의 하네스를 읽는 첫 질문은 "어느 확장점을 몇 개 쓰는가"다. 이 질문의 답을 그린 그림이 확장점 지도다.

### 폴더 구조

- 매니페스트는 plugin 루트의 `.claude-plugin/plugin.json`이고 선택 사항이다. 다른 파일은 모두 plugin 루트에 둔다. `.claude-plugin/` 안에 넣지 않는다. ([T15](../../docs/sources/claude_code/02_tools.md))
- plugin 루트의 CLAUDE.md는 지침으로 실리지 않는다. 지침을 싣고 싶으면 Skill로 쓴다. ([T15](../../docs/sources/claude_code/02_tools.md), [T16](../../docs/sources/claude_code/02_tools.md))
- 사용자 정의 명령과 Skill은 한 장치다. 그래서 `commands/`의 파일도 같은 방식으로 읽는다. ([I13](../../docs/sources/claude_code/01_instructions.md))
- plugin Skill의 이름은 `/<plugin>:<directory>`이다. 예를 들어 `my-plugin`의 `skills/review/SKILL.md`는 `/my-plugin:review`다. ([T16](../../docs/sources/claude_code/02_tools.md))

| 확장점 | plugin 안의 위치 | 근거 |
|---|---|---|
| 매니페스트 | `.claude-plugin/plugin.json` | [T15](../../docs/sources/claude_code/02_tools.md) |
| 명령과 Skill | `commands/`, `skills/<이름>/SKILL.md` | [I13](../../docs/sources/claude_code/01_instructions.md), [T16](../../docs/sources/claude_code/02_tools.md) |
| hook | `hooks/hooks.json` | [T17](../../docs/sources/claude_code/02_tools.md) |
| MCP 서버 | `.mcp.json` | [T18](../../docs/sources/claude_code/02_tools.md) |
| 실행 파일 | `bin/` | [T20](../../docs/sources/claude_code/02_tools.md) |

## 2. hook과 MCP는 켜는 순간 돈다

- plugin hook은 `hooks/hooks.json`에 두고, 세션이 plugin을 실으면 등록된다. plugin의 Skill이나 명령을 쓰는지와 관계없이 각 이벤트마다 돈다. ([T17](../../docs/sources/claude_code/02_tools.md), [C13](../../docs/sources/claude_code/03_control.md))
- plugin MCP 서버는 plugin 루트의 `.mcp.json`에 선언한다. 도구 이름은 `mcp__plugin_<plugin>_<server>__<tool>`이다. 서버 이름만 쓴 hook matcher(`mcp__database-tools__.*` 형태)는 plugin이 싣는 서버에 걸리지 않는다. ([T18](../../docs/sources/claude_code/02_tools.md))
- 그래서 plugin MCP 도구에 규칙이나 matcher를 걸 때는 전체 이름을 쓴다.

### 신뢰 경계

- plugin은 사용자 권한으로 내 컴퓨터에서 코드를 돌리는 내용과, 지침으로 맥락에 들어오는 내용을 함께 실을 수 있다. ([T19](../../docs/sources/claude_code/02_tools.md))
- 권한 규칙과 샌드박스는 Claude가 하는 도구 호출을 덮는다. plugin이 스스로 돌리는 코드는 덮지 않는다. hook과 MCP 서버는 샌드박스 밖에서 돈다. 권한 규칙을 걸어 두었으니 plugin의 hook도 막힌다고 믿으면 안 된다. ([T19](../../docs/sources/claude_code/02_tools.md))
- 켠 plugin의 `bin/`은 Bash 도구의 PATH에 들어가 Claude의 Bash 명령이 그 실행 파일을 쓸 수 있다. ([T20](../../docs/sources/claude_code/02_tools.md))
- 마켓플레이스의 자동 업데이트가 켜져 있으면 plugin이 배경에서 바뀐다. 내가 읽은 파일이 나중에 달라질 수 있다. ([T20](../../docs/sources/claude_code/02_tools.md))
- 설치 전 경고 창은 hook이 있다는 사실만 보여 주고 무엇을 돌리는지는 보여 주지 않는다. 그래서 plugin 폴더의 파일을 직접 읽는다. ([T19](../../docs/sources/claude_code/02_tools.md))
- 설치 범위는 세 가지다. user는 이 컴퓨터의 모든 프로젝트, project는 커밋된 `.claude/settings.json`을 통해 저장소 사람 모두, local은 이 저장소에서 나만 켠다. ([T21](../../docs/sources/claude_code/02_tools.md))

### allowed-tools는 제한이 아니다

command나 Skill의 `allowed-tools`는 도구를 미리 승인하는 필드다. 쓸 수 있는 도구를 그것으로 좁힌다는 뜻이 아니다. 공식 문서가 적은 frontmatter 필드는 호출 제어와 도구 필드이고, 모르는 필드는 오류 없이 무시된다. ([I12](../../docs/sources/claude_code/01_instructions.md))

## 3. 주 사례: vendor/ralph-loop

`Day06_new/vendor/ralph-loop/`은 anthropics/claude-plugins-official 저장소의 `plugins/ralph-loop`을 커밋 `1aa4a4b`에서 그대로 복사한 것이다. 라이선스는 Apache-2.0(`vendor/ralph-loop/LICENSE`)이다.

- Stop hook이 `block`하면 Claude는 멈추지 못하고 계속한다. 공식 문서는 같은 hook이 연속 8번 계속시키면 다음 block을 무시하고 턴을 끝낸다고 적고, `stop_hook_active`를 보라고 한다. ([C16](../../docs/sources/claude_code/03_control.md)) 이 복사본의 `stop-hook.sh`는 `stop_hook_active`를 읽지 않는다. 확인 필요: 연속 상한에 닿은 뒤 이 루프가 어떻게 이어지는지는 실행해 보지 않았다.
- **ralph-loop은 수업에서 설치하지도 실행하지도 않는다.** 반복 루프는 한 번 시작하면 모델 호출이 계속되어 비용이 커질 수 있다. ([C16](../../docs/sources/claude_code/03_control.md)) 이 Part는 파일을 읽는 것으로 끝낸다.

### 다른 후보 둘은 이름과 확장점 수만

| 후보 | 고정 | plugin인가 | 확장점 수 |
|---|---|---|---|
| woowabros/ramo-harness (P1) | `3485937` | 아니오. `install.sh`로 `.claude/`에 복사하는 설치형 | 5종: Skill 12, agent 19, 명령 9, hook 4종, statusLine 1 |
| obra/superpowers (P2) | `22f0b46` | 예 | 2종: Skill 15, hook 1 (SessionStart) |

수치의 출처는 `Day06_new/docs/sources/claude_code/08_plugin_candidates.md`의 P1·P2 표다. 이 수업은 두 후보를 열어 읽지 않는다.

## 4. 대조: Claude Code를 대체하는 하네스

ralph-loop은 Claude Code의 hook 이벤트에 기대어 자기 루프를 만든다. 아래 셋은 반대로 Claude Code 없이 자기 루프를 가진다. `Day06/`의 스냅샷이고, 읽기 전용이며 실행하지 않는다(`Day06_new/AGENTS.md` 2장).

| 폴더 | 한 줄로 | 루프 본체 |
|---|---|---|
| `Day06/pi` | 코어는 작게, 나머지는 확장으로 | `Day06/pi/packages/agent/src/agent-loop.ts:156` `runLoop` |
| `Day06/deepseek-harness` | 루프까지 모든 것이 plugin | `Day06/deepseek-harness/packages/core/agent-loop/src/agent.ts:72` `ReactLoopAgent` |
| `Day06/ouroboros` | 기존 에이전트를 런타임으로 부르는 바깥 계층 | `Day06/ouroboros/src/ouroboros/orchestrator/runner.py:8454` `execute_seed` |

pi의 README는 넣지 않은 것을 먼저 적는다(`Day06/pi/packages/coding-agent/README.md:499-507`): MCP, 하위 에이전트, 권한 팝업, plan mode, 내장 to-do가 없다. Claude Code는 권한 규칙과 plan 모드를 갖고 있다([C1](../../docs/sources/claude_code/03_control.md), [C7](../../docs/sources/claude_code/03_control.md)). 같은 책임을 Claude Code에서는 설정으로, pi에서는 확장 코드로 맡는 셈이다.

"pi 코어에는 하위 에이전트가 없다"와 "pi로는 하위 에이전트를 쓸 수 없다"는 다른 말이다. 기능을 물으면 코어, 기본 번들, 예제, 확장을 나눠 답한다.

## 5. 실패 → 책임 → 장치 → 확인

| 실패 | 책임 | Claude Code 장치 | 동작 확인 |
|---|---|---|---|
| plugin을 켰더니 모르는 hook이 모든 세션에서 돈다 | 실행 제어 | 설치 전에 `hooks/hooks.json`과 `bin/`을 읽는다 ([T17](../../docs/sources/claude_code/02_tools.md), [T19](../../docs/sources/claude_code/02_tools.md), [T20](../../docs/sources/claude_code/02_tools.md)) | 확장점 지도에 hook 이벤트를 적는다 |
| 권한 규칙이 plugin hook·MCP도 막는다고 믿었다 | 실행 제어 | 신뢰 경계 ([T19](../../docs/sources/claude_code/02_tools.md)) | 확인 질문 |
| plugin 루트 CLAUDE.md를 지침으로 읽었다 | 지침 | 지침은 Skill로 ([T15](../../docs/sources/claude_code/02_tools.md), [T16](../../docs/sources/claude_code/02_tools.md)) | `harness_inventory.py <plugin 폴더>`의 "경고: 루트 CLAUDE.md" 행 (M4-2) |
| command의 `allowed-tools`를 도구 제한으로 읽었다 | 도구·실행 제어 | 사전 승인일 뿐 ([I12](../../docs/sources/claude_code/01_instructions.md)) | `vendor/ralph-loop/commands/ralph-loop.md:4` |
| 완료 판정이 글자 일치뿐이다 | 검증 | `<promise>` 비교 (`stop-hook.sh:133, 137`) 대 검사 실행 ([I17](../../docs/sources/claude_code/01_instructions.md)) | 토론 |
| plugin MCP에 서버 이름만으로 규칙·matcher를 걸었다 | 도구 | `mcp__plugin_<plugin>_<server>__<tool>` ([T18](../../docs/sources/claude_code/02_tools.md)) | (설명) |

표를 읽는 순서는 실패 → 책임이다. 어느 책임의 문제인지 먼저 정하면 볼 장치가 정해진다.

## 6. 시연 (5분): vendor/ralph-loop 폴더를 걷는다

강사가 `Day06_new/vendor/ralph-loop/`을 열고 아래 순서로 파일만 읽는다. 아무것도 실행하지 않는다.

1. (1분) `ls`로 폴더를 본다. 어느 폴더가 어떤 확장점인지는 M4-1에서 예측한다.
2. (1분) `.claude-plugin/plugin.json`: 매니페스트가 이름과 버전뿐이다. 구성요소 목록이 없고 폴더 위치로 정해진다. ([T15](../../docs/sources/claude_code/02_tools.md))
3. (1분) `hooks/hooks.json`: 4행의 `Stop`. 이 한 줄이 plugin을 켜는 순간 모든 세션의 응답 끝에 걸린다. ([T17](../../docs/sources/claude_code/02_tools.md))
4. (1분) `hooks/stop-hook.sh`를 위에서 훑는다. 상태를 읽고, 마지막 응답을 보고, 끝낼지 이어갈지 정하는 곳이다. 줄 번호는 미션에서 찾는다.
5. (1분) 확장점 지도는 칠판에 틀만 그린다. 칸은 미션에서 채운다.

## 7. 잘 다루기 습관

1. plugin을 켜기 전에 `hooks/hooks.json`, `.mcp.json`, `bin/`을 읽는다([T19](../../docs/sources/claude_code/02_tools.md), [T20](../../docs/sources/claude_code/02_tools.md)).
2. plugin의 hook과 MCP 서버는 권한 규칙 밖에서 돈다는 것을 기억한다([T19](../../docs/sources/claude_code/02_tools.md)).
3. 남의 하네스는 확장점별(명령·Skill, agent, hook, MCP)로 지도를 그린다([T14](../../docs/sources/claude_code/02_tools.md), [T15](../../docs/sources/claude_code/02_tools.md)).
4. "켜 두면 모든 세션"이다. 필요할 때만 켠다([T14](../../docs/sources/claude_code/02_tools.md), [T21](../../docs/sources/claude_code/02_tools.md)).

## 해설 뒤에 읽는다

M4-3까지 마친 뒤에 읽는다. 예측과 표를 직접 채운 다음에 맞춰 본다.

`Day06_new/vendor/ralph-loop/`의 9개 파일, 980줄이고 구성요소는 **명령 3개와 Stop hook 1개**다. Skill, agent, MCP는 없다.

| 파일 | 줄 | 무엇이 보이나 | 확장점 |
|---|---|---|---|
| `.claude-plugin/plugin.json` | 2-3 | 이름 `ralph-loop`, 버전 `1.0.1` | 매니페스트 ([T15](../../docs/sources/claude_code/02_tools.md)) |
| `commands/ralph-loop.md` | 4 | `allowed-tools`가 `setup-ralph-loop.sh` 호출만 미리 승인한다 | 명령 ([I12](../../docs/sources/claude_code/01_instructions.md), [I13](../../docs/sources/claude_code/01_instructions.md)) |
| `commands/ralph-loop.md` | 16, 18 | 같은 프롬프트를 되먹이고, 완료 약속은 참일 때만 출력하라고 쓴 지침 | 명령 |
| `commands/cancel-ralph.md` | 3 | 취소 명령은 상태 파일 확인·삭제·읽기만 승인한다 | 명령 |
| `hooks/hooks.json` | 4 | `Stop` 이벤트에 `stop-hook.sh`를 건다 | hook ([T17](../../docs/sources/claude_code/02_tools.md), [C13](../../docs/sources/claude_code/03_control.md)) |
| `hooks/stop-hook.sh` | 13 | 상태 파일은 `.claude/ralph-loop.local.md` | 상태 |
| `hooks/stop-hook.sh` | 61-63 | 반복 횟수가 `MAX_ITERATIONS`에 닿으면 상태 파일을 지우고 끝낸다 | 실행 제어 |
| `hooks/stop-hook.sh` | 133, 137 | 마지막 응답의 `<promise>` 글자가 완료 약속과 같으면 끝낸다 | 검증 |
| `hooks/stop-hook.sh` | 185 | 아니면 `"decision": "block"`으로 같은 프롬프트를 되먹인다 | 실행 제어 ([C16](../../docs/sources/claude_code/03_control.md)) |
| `scripts/setup-ralph-loop.sh` | 140-148 | 반복 횟수와 약속을 상태 파일에 쓴다 | 상태 |
| `scripts/setup-ralph-loop.sh` | 27 | `--max-iterations`의 기본값은 무제한이다 | 실행 제어 |

여섯 책임으로 옮기면 지침(명령 본문), 도구(`allowed-tools`), 실행 제어(Stop hook), 상태(상태 파일), 검증(글자 일치)이 있고 **기록은 비어 있다**. 로그도 보고서도 없고 상태 파일이 덮어써질 뿐이다.

- 검증 칸을 보자. 완료는 실행해 본 결과가 아니라 `<promise>` 글자가 같은지로 정한다(`stop-hook.sh:133, 137`). Claude Code의 권장은 통과·실패가 나오는 검사를 주는 것이다. ([I17](../../docs/sources/claude_code/01_instructions.md))

## 근거

본문과 표에서 인용한 대장 항목이다. 링크는 이 저장소의 대장 파일이고, 오른쪽이 그 항목이 적은 공식 문서다.

- [T14](../../docs/sources/claude_code/02_tools.md) plugin이란 무엇이고 어떤 구성요소를 담는가 — https://code.claude.com/docs/en/plugins/overview
- [T15](../../docs/sources/claude_code/02_tools.md) 매니페스트 위치와 표준 디렉터리 구조 — https://code.claude.com/docs/en/plugins/manifest-reference
- [T16](../../docs/sources/claude_code/02_tools.md) plugin Skill의 이름 붙이기 — https://code.claude.com/docs/en/plugins/components
- [T17](../../docs/sources/claude_code/02_tools.md) plugin hook은 언제 로드되고 언제 도는가 — https://code.claude.com/docs/en/plugins/components
- [T18](../../docs/sources/claude_code/02_tools.md) plugin MCP 서버의 로드와 이름 — https://code.claude.com/docs/en/plugins/components
- [T19](../../docs/sources/claude_code/02_tools.md) plugin의 신뢰 경계와 보안 경고 — https://code.claude.com/docs/en/plugins/security
- [T20](../../docs/sources/claude_code/02_tools.md) plugin의 bin/와 자동 업데이트 — https://code.claude.com/docs/en/plugins/security
- [T21](../../docs/sources/claude_code/02_tools.md) plugin 설치 범위 — https://code.claude.com/docs/en/plugins/overview
- [I12](../../docs/sources/claude_code/01_instructions.md) Skills의 호출 제어와 도구 frontmatter — https://code.claude.com/docs/en/skills.md
- [I13](../../docs/sources/claude_code/01_instructions.md) 사용자 정의 슬래시 명령과 Skill은 한 장치다 — https://code.claude.com/docs/en/skills.md
- [I15](../../docs/sources/claude_code/01_instructions.md) 확장 장치 비교 — https://code.claude.com/docs/en/features-overview.md
- [I17](../../docs/sources/claude_code/01_instructions.md) 검증 기준을 지침으로 주기 — https://code.claude.com/docs/en/best-practices.md
- [C13](../../docs/sources/claude_code/03_control.md) hook 이벤트 목록 — https://code.claude.com/docs/en/hooks.md
- [C16](../../docs/sources/claude_code/03_control.md) Stop hook은 완료 관문이 될 수 있다 — https://code.claude.com/docs/en/hooks.md

plugin 후보의 파일·줄 근거는 `Day06_new/docs/sources/claude_code/08_plugin_candidates.md`(P1·P2·P3)이고, 이 문서의 `vendor/ralph-loop` 줄 번호는 복사본에서 다시 확인했다.
