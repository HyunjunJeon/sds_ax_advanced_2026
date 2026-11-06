# Claude Code 하네스 습관 지도

이 한 장은 Day06_new의 지도다. 아래 표에서 책임별로 Claude Code 장치와 대장 항목(ID)을 찾고, 표 아래 절에서 Part마다 배운 "잘 다루기 습관"을 다시 읽는다. 습관 줄은 각 카드의 문구를 그대로 옮겼다. 내 장치가 어느 칸에 있는지 찾는 데 쓴다. 근거가 필요하면 ID 링크로 대장을 연다.

## 여섯 책임 × Claude Code 장치

| 책임 | 장치 (Claude Code 기능) | 대장 ID | 어느 Part에서 |
|---|---|---|---|
| 지침 | CLAUDE.md 범위와 `@` 가져오기, `.claude/rules/`, Skill과 사용자 정의 명령, Output style. 지침은 강제가 아니다. | [I1](../../docs/sources/claude_code/01_instructions.md), [I3](../../docs/sources/claude_code/01_instructions.md), [I4](../../docs/sources/claude_code/01_instructions.md), [I5](../../docs/sources/claude_code/01_instructions.md), [I6](../../docs/sources/claude_code/01_instructions.md), [I8](../../docs/sources/claude_code/01_instructions.md), [I10](../../docs/sources/claude_code/01_instructions.md), [I11](../../docs/sources/claude_code/01_instructions.md), [I12](../../docs/sources/claude_code/01_instructions.md), [I15](../../docs/sources/claude_code/01_instructions.md) | Part 2 |
| 도구 | 내장 도구 이름이 권한 규칙의 키, Bash 한도, MCP 범위와 승인, 도구 검색. | [T2](../../docs/sources/claude_code/02_tools.md), [T3](../../docs/sources/claude_code/02_tools.md), [T4](../../docs/sources/claude_code/02_tools.md), [T5](../../docs/sources/claude_code/02_tools.md), [T8](../../docs/sources/claude_code/02_tools.md), [T10](../../docs/sources/claude_code/02_tools.md), [T11](../../docs/sources/claude_code/02_tools.md), [T12](../../docs/sources/claude_code/02_tools.md) | Part 2 |
| 도구 | plugin 묶음(명령·Skill, agent, hook, MCP)과 켜는 순간 도는 hook·MCP. | [T14](../../docs/sources/claude_code/02_tools.md), [T15](../../docs/sources/claude_code/02_tools.md), [T19](../../docs/sources/claude_code/02_tools.md), [T20](../../docs/sources/claude_code/02_tools.md), [T21](../../docs/sources/claude_code/02_tools.md) | Part 4 |
| 실행 제어 | 권한 규칙 deny→ask→allow, 설정 우선순위, 폴더 신뢰, 권한 모드, 샌드박스. | [C1](../../docs/sources/claude_code/03_control.md), [C2](../../docs/sources/claude_code/03_control.md), [C3](../../docs/sources/claude_code/03_control.md), [C4](../../docs/sources/claude_code/03_control.md), [C5](../../docs/sources/claude_code/03_control.md), [C6](../../docs/sources/claude_code/03_control.md), [C7](../../docs/sources/claude_code/03_control.md), [C10](../../docs/sources/claude_code/03_control.md) | Part 2, Part 5 |
| 실행 제어 | hook 이벤트, matcher, exit 2, `/hooks`. | [C13](../../docs/sources/claude_code/03_control.md), [C14](../../docs/sources/claude_code/03_control.md), [C15](../../docs/sources/claude_code/03_control.md), [C18](../../docs/sources/claude_code/03_control.md) | Part 2 |
| 실행 제어 | plan mode, 하위 에이전트와 tools 좁히기, worktree, 병렬의 토큰 비용, 헤드리스 `-p`. | [C7](../../docs/sources/claude_code/03_control.md), [X2](../../docs/sources/claude_code/05_execution.md), [X3](../../docs/sources/claude_code/05_execution.md), [X4](../../docs/sources/claude_code/05_execution.md), [X5](../../docs/sources/claude_code/05_execution.md), [X6](../../docs/sources/claude_code/05_execution.md), [X7](../../docs/sources/claude_code/05_execution.md), [X13](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md) | Part 5 |
| 상태 | 맥락 창과 `/context`, auto memory, 세션 이름과 `/clear`, `/rewind`(버전 관리가 아니다), 압축 뒤 남는 것. | [S3](../../docs/sources/claude_code/04_state.md), [S4](../../docs/sources/claude_code/04_state.md), [S6](../../docs/sources/claude_code/04_state.md), [S10](../../docs/sources/claude_code/04_state.md), [S15](../../docs/sources/claude_code/04_state.md), [S17](../../docs/sources/claude_code/04_state.md), [I9](../../docs/sources/claude_code/01_instructions.md) | Part 2, Part 3 |
| 검증 | Stop hook 완료 관문(`stop_hook_active`), 대화를 못 본 하위 에이전트의 검토, 끝을 확인할 명령 한 줄. | [C16](../../docs/sources/claude_code/03_control.md), [I17](../../docs/sources/claude_code/01_instructions.md), [I18](../../docs/sources/claude_code/01_instructions.md), [X14](../../docs/sources/claude_code/05_execution.md) | Part 1, Part 3, Part 5 |
| 기록 | transcript와 도구 호출 기록, `/insights`, OpenTelemetry 지표, `/context`·`/memory`로 실렸는지 확인. | [S12](../../docs/sources/claude_code/04_state.md), [V7](../../docs/sources/claude_code/06_verification_records.md), [V9](../../docs/sources/claude_code/06_verification_records.md), [V11](../../docs/sources/claude_code/06_verification_records.md), [V12](../../docs/sources/claude_code/06_verification_records.md), [K3](../../docs/sources/claude_code/07_commands_cli.md) | Part 1, 실습 |

## Part 1

카드: [part1](../part1/concept.md)

1. 맡길 때 "끝을 무엇으로 확인할지" 명령 한 줄을 같이 준다 ([I17](../../docs/sources/claude_code/01_instructions.md)).
2. 첫 1분을 보고, 어긋나면 Esc. 두 번 고쳐도 틀리면 `/clear` 뒤 새로 쓴다 ([I18](../../docs/sources/claude_code/01_instructions.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)).
3. 세션을 열면 권한 모드부터 본다. 기본은 버전마다 다르다 ([C10](../../docs/sources/claude_code/03_control.md)).
4. 결과는 최종 답이 아니라 도구 호출 기록으로 읽는다 ([S12](../../docs/sources/claude_code/04_state.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)).

## Part 2

카드: [part2](../part2/concept.md)

1. "반드시"는 CLAUDE.md나 Skill이 아니라 deny 규칙이나 hook에 둔다([I8](../../docs/sources/claude_code/01_instructions.md), [C2](../../docs/sources/claude_code/03_control.md), [I15](../../docs/sources/claude_code/01_instructions.md), [I11](../../docs/sources/claude_code/01_instructions.md)).
2. 지침이 안 먹으면 먼저 `/context all`과 `/memory`로 실렸는지 본다([I7](../../docs/sources/claude_code/01_instructions.md), [V12](../../docs/sources/claude_code/06_verification_records.md)).
3. CLAUDE.md는 200줄 이하, 코드를 읽어도 모르는 것만([I6](../../docs/sources/claude_code/01_instructions.md)).
4. 막는 hook은 exit 2로 끝내고, matcher는 도구 이름을 거른다는 것을 기억한다([C14](../../docs/sources/claude_code/03_control.md), [C15](../../docs/sources/claude_code/03_control.md)).
5. 남이 준 폴더는 `.claude/settings.json`, `.mcp.json`, Skill의 `allowed-tools`를 열기 전에 읽는다([C5](../../docs/sources/claude_code/03_control.md), [T10](../../docs/sources/claude_code/02_tools.md), [I12](../../docs/sources/claude_code/01_instructions.md)).

## Part 3

카드: [part3](../part3/concept.md)

1. 큰 변경 전에는 git 커밋. `/rewind`는 버전 관리가 아니다 ([S15](../../docs/sources/claude_code/04_state.md)).
2. 대화로만 한 약속은 파일(CLAUDE.md, `progress.md`)로 옮긴다 ([I9](../../docs/sources/claude_code/01_instructions.md), [S4](../../docs/sources/claude_code/04_state.md)).
3. 관련 없는 일 사이에는 `/clear`, 돌아올 세션에는 이름을 붙인다 ([S6](../../docs/sources/claude_code/04_state.md), [S10](../../docs/sources/claude_code/04_state.md)).
4. 완료는 말이 아니라 다시 돌린 검사로 인정한다. 강제하려면 Stop hook이고, 막는 조건이 영원히 참이 되지 않게 `stop_hook_active`를 본다 ([C16](../../docs/sources/claude_code/03_control.md), [I17](../../docs/sources/claude_code/01_instructions.md)).

## Part 4

카드: [part4](../part4/concept.md)

1. plugin을 켜기 전에 `hooks/hooks.json`, `.mcp.json`, `bin/`을 읽는다([T19](../../docs/sources/claude_code/02_tools.md), [T20](../../docs/sources/claude_code/02_tools.md)).
2. plugin의 hook과 MCP 서버는 권한 규칙 밖에서 돈다는 것을 기억한다([T19](../../docs/sources/claude_code/02_tools.md)).
3. 남의 하네스는 확장점별(명령·Skill, agent, hook, MCP)로 지도를 그린다([T14](../../docs/sources/claude_code/02_tools.md), [T15](../../docs/sources/claude_code/02_tools.md)).
4. "켜 두면 모든 세션"이다. 필요할 때만 켠다([T14](../../docs/sources/claude_code/02_tools.md), [T21](../../docs/sources/claude_code/02_tools.md)).

## Part 5

카드: [part5](../part5/concept.md)

1. 디스크에 닿기 전에 봐야 할 변경은 plan mode로 시작하고, 승인한 계획은 저장소 파일로 옮긴다([C7](../../docs/sources/claude_code/03_control.md), [X14](../../docs/sources/claude_code/05_execution.md)).
2. 검토는 대화를 못 본 하위 에이전트에게 맡기고 도구를 좁힌다([X3](../../docs/sources/claude_code/05_execution.md), [X2](../../docs/sources/claude_code/05_execution.md), [T7](../../docs/sources/claude_code/02_tools.md), [I17](../../docs/sources/claude_code/01_instructions.md)).
3. 병렬은 독립성과 비용을 같이 본다. 일꾼을 늘리면 토큰이 곱해진다([X5](../../docs/sources/claude_code/05_execution.md), [X4](../../docs/sources/claude_code/05_execution.md)).
4. `-p`에는 신뢰 대화상자가 없다. 낯선 폴더에서는 먼저 설정을 읽는다([X13](../../docs/sources/claude_code/05_execution.md)).

## 실습

카드: [lab](../lab/mission.md)

1. 같은 실수를 두 번 고쳤으면 대화가 아니라 장치로 옮긴다(I15, I6).
2. 장치를 만들면 "실렸나"(`/context`, `/hooks`, `/permissions`)와 "쓰였나"(세션 기록)를 따로 확인한다(V12).
3. 지표는 Claude Code가 내보내는 숫자로 모으고, 본문을 담는 스위치는 끈 채로 둔다(V7, V9).
