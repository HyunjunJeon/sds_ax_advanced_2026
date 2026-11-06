# Part 2. What is Agent Harness (개념 17분 + 시연 6분)

## 핵심 질문

> **"하지 마"를 어디에 적어야 실제로 막히는가? Claude Code의 각 장치는 여섯 책임 중 무엇을 맡는가?**

이 문서의 Claude Code 사실은 모두 `Day06_new/docs/sources/claude_code/`의 근거 대장에 항목이 있는 것만 적는다. 문장 뒤의 `C2` 같은 표시는 그 항목 번호이고, 누르면 대장 파일로 간다. 대장에 없는 것은 쓰지 않았다. 이 Part의 미션은 폴더 네 개를 만들어 같은 요청을 보내고 결과를 비교한다. 단계는 `mission.md`에 있다.

---

## 1. 하네스 = 모델 밖의 모든 것: 여섯 책임

하네스는 모델이 아닌 모든 것이다. 이 수업은 하네스를 여섯 책임 하나의 틀로 말한다.

| 책임 | 답할 질문 |
|---|---|
| 지침 | 목표·범위·완료 조건은 무엇인가? |
| 도구 | 관측과 변경을 어떻게 실행하는가? |
| 실행 제어 | 무엇을 허용·승인·중단하는가? |
| 상태 | 다음 세션이 무엇을 이어받는가? |
| 검증 | 어떤 근거로 완료를 인정하는가? |
| 기록 | 실패 원인과 변경을 설명할 수 있는가? |

폴더 이름이나 기능 이름과 책임을 1:1로 짝짓지 않는다. 한 장치가 여러 책임에 걸치기도 한다. 오늘은 이 한 틀로 일관되게 말한다.

## 2. Claude Code에서 각 책임을 맡는 장치

아래 표가 이 Part의 지도다. 오른쪽 끝 칸이 근거 항목이다.

| 책임 | Claude Code 기능 | 근거 |
|---|---|---|
| 지침 | CLAUDE.md는 관리·사용자·프로젝트·로컬 범위가 있다. 위 폴더의 파일은 시작 때 이어 붙여 싣고, 하위 폴더의 파일은 필요할 때 싣는다. | [I1](../../docs/sources/claude_code/01_instructions.md), [I2](../../docs/sources/claude_code/01_instructions.md) |
| 지침 | AGENTS.md는 작업 폴더와 그 위에 CLAUDE.md가 없을 때만 읽는다. `@` 가져오기는 깊이 4까지다. `.claude/rules/`는 `paths`로 범위를 한정한다. | [I3](../../docs/sources/claude_code/01_instructions.md), [I4](../../docs/sources/claude_code/01_instructions.md), [I5](../../docs/sources/claude_code/01_instructions.md) |
| 지침 | CLAUDE.md는 200줄 이하가 목표이고, 코드에서 알 수 없는 것만 적는다. 지침은 강제가 아니다. | [I6](../../docs/sources/claude_code/01_instructions.md), [I8](../../docs/sources/claude_code/01_instructions.md) |
| 지침 | Skill은 위치가 적재를 정한다. 설명은 항상 싣고 본문은 쓸 때 싣는다. 호출 제어 필드가 있다. 사용자 정의 명령과 Skill은 한 장치다. Output style도 지침이다. | [I10](../../docs/sources/claude_code/01_instructions.md), [I11](../../docs/sources/claude_code/01_instructions.md), [I12](../../docs/sources/claude_code/01_instructions.md), [I13](../../docs/sources/claude_code/01_instructions.md), [I14](../../docs/sources/claude_code/01_instructions.md) |
| 지침 | 확장 장치 비교표와 장치별 맥락 비용. | [I15](../../docs/sources/claude_code/01_instructions.md), [I16](../../docs/sources/claude_code/01_instructions.md) |
| 도구 | 도구 이름이 곧 권한 규칙의 키다. macOS에서 Glob·Grep은 기본 도구가 아니고 검색은 Bash를 거친다. Bash는 명령마다 별도 프로세스이고 시간·출력 한도가 있다. | [T2](../../docs/sources/claude_code/02_tools.md), [T3](../../docs/sources/claude_code/02_tools.md), [T4](../../docs/sources/claude_code/02_tools.md), [T5](../../docs/sources/claude_code/02_tools.md) |
| 도구 | MCP는 local·project·user 범위가 있고, 프로젝트 `.mcp.json` 서버는 승인을 묻는다. 도구 이름 형태가 있고, 도구 검색은 시작 때 이름만 싣는다. | [T8](../../docs/sources/claude_code/02_tools.md), [T10](../../docs/sources/claude_code/02_tools.md), [T11](../../docs/sources/claude_code/02_tools.md), [T12](../../docs/sources/claude_code/02_tools.md) |
| 실행 제어 | 권한 규칙 문법, deny→ask→allow 순서(집행은 모델이 아니라 Claude Code), Bash 복합 명령과 규칙의 한계. | [C1](../../docs/sources/claude_code/03_control.md), [C2](../../docs/sources/claude_code/03_control.md), [C3](../../docs/sources/claude_code/03_control.md) |
| 실행 제어 | 설정 우선순위와 목록 병합, 폴더 신뢰(allow는 신뢰 뒤, deny·ask는 무관). | [C4](../../docs/sources/claude_code/03_control.md), [C5](../../docs/sources/claude_code/03_control.md) |
| 실행 제어 | 권한 모드: default(Manual)·acceptEdits·plan·auto(분류기)·dontAsk·bypassPermissions. | [C6](../../docs/sources/claude_code/03_control.md), [C7](../../docs/sources/claude_code/03_control.md), [C8](../../docs/sources/claude_code/03_control.md), [C9](../../docs/sources/claude_code/03_control.md), [C10](../../docs/sources/claude_code/03_control.md) |
| 실행 제어 | 샌드박스(Bash만, 기본 꺼짐)와 권한 규칙의 관계. | [C11](../../docs/sources/claude_code/03_control.md), [C12](../../docs/sources/claude_code/03_control.md) |
| 실행 제어 | hook 이벤트, matcher, exit 2, PreToolUse 결정 값, hook 위치와 `/hooks`. | [C13](../../docs/sources/claude_code/03_control.md), [C14](../../docs/sources/claude_code/03_control.md), [C15](../../docs/sources/claude_code/03_control.md), [C17](../../docs/sources/claude_code/03_control.md), [C18](../../docs/sources/claude_code/03_control.md) |
| 상태 | 맥락 창에 실리는 것과 `/context`, auto memory. 자세한 것은 Part 3에서 본다. | [S3](../../docs/sources/claude_code/04_state.md), [S17](../../docs/sources/claude_code/04_state.md) |
| 검증 | Stop hook 완료 관문, 대화를 못 본 하위 에이전트의 검토. 자세한 것은 Part 3·5에서 본다. | [C16](../../docs/sources/claude_code/03_control.md), [I17](../../docs/sources/claude_code/01_instructions.md) |
| 기록 | transcript, `/insights`, OpenTelemetry, 무엇이 실렸는지 보는 명령. 자세한 것은 실습에서 본다. | [S12](../../docs/sources/claude_code/04_state.md), [V11](../../docs/sources/claude_code/06_verification_records.md), [V6](../../docs/sources/claude_code/06_verification_records.md), [V12](../../docs/sources/claude_code/06_verification_records.md) |

한 가지 장치가 한 책임만 맡는 것은 아니다. 예를 들어 CLAUDE.md는 지침이지만 ([S3](../../docs/sources/claude_code/04_state.md))에서 보듯 맥락 창을 차지하므로 상태의 비용이기도 하다.

## 3. 지침과 실행 제어는 다르다

네 가지 방법으로 같은 말을 해 본다. "이미 만든 커밋은 고치지 마(`git commit --amend` 금지)."

| 방법 | 어디에 적나 | 누가 지키게 하나 |
|---|---|---|
| CLAUDE.md의 한 줄 | `CLAUDE.md` | 모델. 지침은 사용자 메시지로 전달되고 모델이 읽는다. 어길 수 있다. |
| deny 규칙 | `.claude/settings.json`의 권한 규칙 | Claude Code. 도구를 실행하기 전에 규칙을 평가한다. |
| PreToolUse hook | hook 설정과 스크립트 | Claude Code가 hook을 부르고, 스크립트가 exit 2로 끝나면 막는다. |
| Skill | `.claude/skills/<이름>/SKILL.md` | 모델. 그것도 Skill을 부른 뒤에만 본문이 실린다. 설명은 항상 맥락에 있고 본문은 쓸 때 실린다. ([I11](../../docs/sources/claude_code/01_instructions.md)) |

- CLAUDE.md는 맥락이지 강제가 아니다. 공식 문서는 행동을 무조건 막으려면 PreToolUse hook을 쓰라고 적는다. 지침은 모델이 읽는 비결정적 지침이다. ([I8](../../docs/sources/claude_code/01_instructions.md))
- 규칙은 deny, ask, allow 순서로 평가한다. 처음 맞는 규칙이 결과를 정하고, allow는 deny의 예외가 될 수 없다. 이 평가를 집행하는 것은 모델이 아니라 Claude Code다. ([C2](../../docs/sources/claude_code/03_control.md))
- hook은 exit 2로 끝나면 동작을 막고, 사유는 stderr로 Claude에게 간다. 그 밖의 종료는 막지 않는다. ([C15](../../docs/sources/claude_code/03_control.md))
- "반드시"는 지침에 두지 않는다. 확장 장치 비교표도 CLAUDE.md는 항상 싣는 맥락, hook은 자동화라고 역할을 나눈다. ([I15](../../docs/sources/claude_code/01_instructions.md))

### 규칙은 명령 글자를 맞춘다

- Bash 규칙은 명령 전체 글자와 맞춘다. `*`는 아무 글자나 뜻한다. ([C1](../../docs/sources/claude_code/03_control.md))
- 복합 명령은 하위 명령마다 본다. allow는 하위 명령이 전부 허용돼야 하고, deny·ask는 하나만 걸려도 적용된다. ([C3](../../docs/sources/claude_code/03_control.md))
- 그래서 같은 일을 하는 다른 글자의 명령은 규칙 밖일 수 있다. 명령 글자와 무관하게 막으려면 샌드박스를 본다.

### 샌드박스는 다른 방식으로 막는다

- 샌드박스는 운영체제가 Bash 프로세스 둘레에 치는 경계다. 모델이 무엇을 골랐든, 허용된 명령이 이름보다 많은 일을 해도 경계는 유지된다. ([C12](../../docs/sources/claude_code/03_control.md))
- 범위는 Bash 명령만이다. 파일 도구, MCP 서버, hook은 샌드박스 밖에서 돈다. 기본은 꺼짐이다. ([C11](../../docs/sources/claude_code/03_control.md))
- `/sandbox`는 권한 모드가 아니다. ([C12](../../docs/sources/claude_code/03_control.md))

### 지침 장치 셋: CLAUDE.md · rules · Skill

세 장치는 모두 지침이다. 다른 점은 언제 맥락에 실리느냐다.

| 장치 | 언제 실리나 | 맥락 비용 |
|---|---|---|
| CLAUDE.md | 세션을 열 때 항상 ([I1](../../docs/sources/claude_code/01_instructions.md), [I2](../../docs/sources/claude_code/01_instructions.md)) | 파일 전체가 실린다 |
| `.claude/rules/` | `paths`를 적은 규칙은 맞는 파일을 다룰 때만 ([I5](../../docs/sources/claude_code/01_instructions.md)) | 맞을 때만 든다 |
| Skill | 설명은 항상, 본문은 쓸 때 ([I11](../../docs/sources/claude_code/01_instructions.md)) | 설명만 항상 든다 |

- 장치별 맥락 비용은 CLAUDE.md는 시작 때 파일 전체, Skill은 시작 때 설명과 쓸 때 본문이다. 많이 넣을수록 안전하지 않다. ([I16](../../docs/sources/claude_code/01_instructions.md))
- 호출 제어: Skill에 `disable-model-invocation: true`를 쓰면 모델은 그 Skill을 스스로 부를 수 없고 사용자만 부른다. 이때 설명도 맥락에 없고, 부를 때 본문이 실린다. ([I12](../../docs/sources/claude_code/01_instructions.md))
- 이 수업의 결정을 예로 본다. 조교 폴더(`use_cc`)에는 한때 `disable-model-invocation`을 건 미션 Skill이 있었다. 그러면 수강생이 명령을 직접 쳐야 하고, 그 전에는 진행 규칙이 맥락에 없다. 그래서 Skill을 없애고 진행 규칙을 `MISSION_GUIDE.md`에 두어 `use_cc/CLAUDE.md`가 `@`로 가져오게 했다. 진행 규칙은 이제 세션마다 실린다. ([I4](../../docs/sources/claude_code/01_instructions.md), [I12](../../docs/sources/claude_code/01_instructions.md))

### 세션을 열 때 실리는 것

- CLAUDE.md는 관리·사용자·프로젝트·로컬 위치가 있다. 작업 폴더 위쪽의 파일은 시작 때 싣고 하위 폴더의 파일은 그 폴더의 파일을 다룰 때 싣는다. ([I1](../../docs/sources/claude_code/01_instructions.md), [I2](../../docs/sources/claude_code/01_instructions.md))
- CLAUDE.md 안의 `@경로`는 그 파일을 함께 싣는다. 깊이는 4까지이고, import는 크기를 줄여 주지 않는다. ([I4](../../docs/sources/claude_code/01_instructions.md))
- auto memory는 `MEMORY.md`의 앞 200줄 또는 25KB를 모든 대화의 시작에 싣는다. 주제 파일은 시작 때 싣지 않는다. ([S17](../../docs/sources/claude_code/04_state.md))
- auto memory 폴더는 git 저장소에서 정해진다. 같은 저장소의 하위 폴더는 모두 한 폴더를 공유한다. ([S17](../../docs/sources/claude_code/04_state.md))
- 그래서 `Day06_new/use_cc`에서 연 조교 세션은 이 수업 저장소의 다른 곳에서 한 세션과 auto memory를 공유한다. 실험 폴더는 각자 git 저장소이므로 자기 auto memory를 따로 가진다.
- 무엇이 실렸는지는 `/context all`과 `/memory`로 본다. ([I7](../../docs/sources/claude_code/01_instructions.md), [V12](../../docs/sources/claude_code/06_verification_records.md))

### hook 이벤트와 여섯 책임

hook 이벤트는 30개가 넘고 버전마다 는다. 이 수업은 그중 일곱 개만 여섯 책임으로 이 표에 묶는다. ([C13](../../docs/sources/claude_code/03_control.md), [C16](../../docs/sources/claude_code/03_control.md), [C20](../../docs/sources/claude_code/03_control.md), [C21](../../docs/sources/claude_code/03_control.md))

| 책임 | 이벤트 |
|---|---|
| 지침·상태 (시작·요청 때 맥락 주입) | `SessionStart`, `UserPromptSubmit` |
| 실행 제어 (실행 전에 막기) | `PreToolUse` |
| 검증 (도구가 끝난 뒤 검사, 완료 관문) | `PostToolUse`, `Stop`, `TaskCompleted` |
| 기록 | `SessionEnd` |

Part 3은 `Stop`을 쓰고, 실습은 `PostToolUse`나 `SessionStart`를 쓸 수 있다.

## 4. 실패 → 책임 → 장치 → 확인

| 실패 | 책임 | Claude Code 장치 | 동작 확인 |
|---|---|---|---|
| CLAUDE.md에 "절대 하지 마"라고 썼는데 했다 | 지침과 실행 제어를 혼동 | deny 규칙 ([C1](../../docs/sources/claude_code/03_control.md), [C2](../../docs/sources/claude_code/03_control.md)) 또는 PreToolUse hook exit 2 ([C15](../../docs/sources/claude_code/03_control.md)). "반드시"는 hook에 ([I8](../../docs/sources/claude_code/01_instructions.md), [I15](../../docs/sources/claude_code/01_instructions.md)) | 실험 2a·2b·2c·2d의 같은 요청 |
| 규칙을 썼는데 안 먹는다 | 지침(적재) | `/context all`의 Memory files, `/memory` ([I7](../../docs/sources/claude_code/01_instructions.md), [S3](../../docs/sources/claude_code/04_state.md), [V12](../../docs/sources/claude_code/06_verification_records.md)) | M2-1 |
| deny 규칙이 다른 형태의 명령에 뚫렸다 | 실행 제어 | 규칙은 명령 글자를 맞춘다 ([C1](../../docs/sources/claude_code/03_control.md), [C3](../../docs/sources/claude_code/03_control.md)). 글자와 무관하게 막으려면 샌드박스 ([C11](../../docs/sources/claude_code/03_control.md), [C12](../../docs/sources/claude_code/03_control.md)) | 실험 2b의 옵션 순서 예측 |
| hook이 오류로 끝났는데 막힌 줄 알았다 | 실행 제어 | 막는 것은 exit 2뿐, 그 밖의 종료는 비차단 ([C15](../../docs/sources/claude_code/03_control.md)) | hook stderr 문장이 Claude에게 갔는가 |
| Skill이 안 뜨거나 엉뚱하게 뜬다 | 지침 | 설명(description)이 언제 쓰는지의 지침 ([I11](../../docs/sources/claude_code/01_instructions.md)), `/skills` ([V12](../../docs/sources/claude_code/06_verification_records.md)) | 실험 2d |
| 받은 저장소의 설정이 내 컴퓨터에서 돌았다 | 실행 제어 | allow는 신뢰 뒤에만, hook·Skill의 allowed-tools는 다른 규칙 ([C5](../../docs/sources/claude_code/03_control.md), [I12](../../docs/sources/claude_code/01_instructions.md)), `.mcp.json` 승인 ([T10](../../docs/sources/claude_code/02_tools.md)) | (설명) |

표를 읽는 순서는 실패 → 책임이다. 어느 책임의 문제인지 먼저 정하면 고칠 장치가 정해진다.

## 5. 대조: mini-coding-agent (강사 시연 6분)

같은 책임을 읽을 수 있는 소스로 한 번 본다. 대상은 `vendor/mini-coding-agent/mini_coding_agent.py`, 파일 하나 1,019줄이다. 실행하지 않고 아래 다섯 곳만 읽는다.

| 보는 곳 | 줄 | 무엇이 보이나 | 짝이 되는 Claude Code 장치 |
|---|---|---|---|
| 요청 처리 | `mini_coding_agent.py:445` | `MiniAgent.ask`. 요청 하나를 이 함수가 처리한다. | 세션 한 번의 대화 |
| 루프 | `mini_coding_agent.py:455-491` | 모델 호출 → 도구 호출이면 실행하고 기록 → 최종 답이면 끝. 한도(`max_steps`)에 걸리면 "멈췄다"는 문장을 돌려준다. | 에이전트 루프는 Claude Code가 맡는다 |
| 도구 관문 | `mini_coding_agent.py:496-515` | `run_tool`. 없는 도구 → 인자 검증 → 같은 호출 반복 거절 → 위험 도구 승인 → 실행·출력 자르기. | 규칙 평가 순서 ([C2](../../docs/sources/claude_code/03_control.md)) |
| 승인 정책 | `mini_coding_agent.py:602-613` | `approve`. 읽기 전용이면 거절, `auto`면 승인, `never`면 거절, 그 외에는 사람에게 y/N을 묻는다. | 권한 모드 ([C6](../../docs/sources/claude_code/03_control.md), [C7](../../docs/sources/claude_code/03_control.md), [C8](../../docs/sources/claude_code/03_control.md), [C9](../../docs/sources/claude_code/03_control.md)) |
| 검증 없음 | `mini_coding_agent.py:481-484` | 모델이 최종 답을 내면 기록하고 그대로 반환한다. 작업 결과를 확인하는 단계가 없다. | Stop hook 완료 관문 ([C16](../../docs/sources/claude_code/03_control.md)) |

**이 시연의 메시지는 하나다.** 같은 책임을 한 파일의 코드로 맡기느냐, Claude Code의 설정으로 맡기느냐. 앞쪽은 코드를 고치고, 뒤쪽은 설정을 고친다. mini-coding-agent는 대조군이고, 이 Part에서 실험하는 것은 Claude Code다.

## 6. 잘 다루기 습관

1. "반드시"는 CLAUDE.md나 Skill이 아니라 deny 규칙이나 hook에 둔다([I8](../../docs/sources/claude_code/01_instructions.md), [C2](../../docs/sources/claude_code/03_control.md), [I15](../../docs/sources/claude_code/01_instructions.md), [I11](../../docs/sources/claude_code/01_instructions.md)).
2. 지침이 안 먹으면 먼저 `/context all`과 `/memory`로 실렸는지 본다([I7](../../docs/sources/claude_code/01_instructions.md), [V12](../../docs/sources/claude_code/06_verification_records.md)).
3. CLAUDE.md는 200줄 이하, 코드를 읽어도 모르는 것만([I6](../../docs/sources/claude_code/01_instructions.md)).
4. 막는 hook은 exit 2로 끝내고, matcher는 도구 이름을 거른다는 것을 기억한다([C14](../../docs/sources/claude_code/03_control.md), [C15](../../docs/sources/claude_code/03_control.md)).
5. 남이 준 폴더는 `.claude/settings.json`, `.mcp.json`, Skill의 `allowed-tools`를 열기 전에 읽는다([C5](../../docs/sources/claude_code/03_control.md), [T10](../../docs/sources/claude_code/02_tools.md), [I12](../../docs/sources/claude_code/01_instructions.md)).

## 근거

본문과 표에서 인용한 대장 항목이다. 링크는 이 저장소의 대장 파일이고, 오른쪽이 그 항목이 적은 공식 문서다.

- [C1](../../docs/sources/claude_code/03_control.md) 권한 규칙 문법 (Tool, Tool(specifier), mcp__) — https://code.claude.com/docs/en/permissions.md
- [C2](../../docs/sources/claude_code/03_control.md) 평가 순서: deny, ask, allow, 그리고 모델이 아닌 Claude Code가 집행한다 — https://code.claude.com/docs/en/permissions.md
- [C3](../../docs/sources/claude_code/03_control.md) Bash 규칙과 복합 명령 — https://code.claude.com/docs/en/permissions.md
- [C4](../../docs/sources/claude_code/03_control.md) 설정 위치와 우선순위 (managed, command line, local, project, user) — https://code.claude.com/docs/en/settings.md
- [C5](../../docs/sources/claude_code/03_control.md) 폴더 신뢰(workspace trust) 대화상자가 바꾸는 것 — https://code.claude.com/docs/en/permissions.md
- [C6](../../docs/sources/claude_code/03_control.md) 권한 모드 표: default, acceptEdits — https://code.claude.com/docs/en/permission-modes.md
- [C7](../../docs/sources/claude_code/03_control.md) plan 모드 — https://code.claude.com/docs/en/permission-modes.md
- [C8](../../docs/sources/claude_code/03_control.md) auto 모드: 누가 결정하는가와 비용 — https://code.claude.com/docs/en/permission-modes.md
- [C9](../../docs/sources/claude_code/03_control.md) dontAsk와 bypassPermissions — https://code.claude.com/docs/en/permission-modes.md
- [C10](../../docs/sources/claude_code/03_control.md) 모드 전환과 시작 모드 — https://code.claude.com/docs/en/permission-modes.md
- [C11](../../docs/sources/claude_code/03_control.md) 샌드박스가 격리하는 것 (파일 시스템, 네트워크) — https://code.claude.com/docs/en/sandboxing.md
- [C12](../../docs/sources/claude_code/03_control.md) 샌드박스와 권한 규칙의 관계 — https://code.claude.com/docs/en/sandboxing.md
- [C13](../../docs/sources/claude_code/03_control.md) hook 이벤트 목록 (수업에서 쓸 이벤트) — https://code.claude.com/docs/en/hooks.md
- [C14](../../docs/sources/claude_code/03_control.md) matcher는 무엇을 거르는가 — https://code.claude.com/docs/en/hooks.md
- [C15](../../docs/sources/claude_code/03_control.md) 종료 코드 2의 의미 — https://code.claude.com/docs/en/hooks.md
- [C16](../../docs/sources/claude_code/03_control.md) Stop hook은 완료 관문이 될 수 있다 — https://code.claude.com/docs/en/hooks.md
- [C17](../../docs/sources/claude_code/03_control.md) PreToolUse 결정 값과 권한 규칙의 우선순위 — https://code.claude.com/docs/en/hooks.md
- [C18](../../docs/sources/claude_code/03_control.md) hook을 설정하는 위치와 /hooks 명령 — https://code.claude.com/docs/en/hooks.md
- [C20](../../docs/sources/claude_code/03_control.md) SessionStart hook: 시작 원인 matcher와 맥락 주입 — https://code.claude.com/docs/en/hooks.md
- [C21](../../docs/sources/claude_code/03_control.md) PostToolUse hook: 실행 뒤 피드백 — https://code.claude.com/docs/en/hooks.md
- [I1](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md 파일 위치와 범위 — https://code.claude.com/docs/en/memory.md
- [I2](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md 적재 순서: 상위 폴더는 시작 때, 하위 폴더는 필요할 때 — https://code.claude.com/docs/en/memory.md
- [I3](../../docs/sources/claude_code/01_instructions.md) AGENTS.md 대체 읽기 — https://code.claude.com/docs/en/memory.md
- [I4](../../docs/sources/claude_code/01_instructions.md) `@` import — https://code.claude.com/docs/en/memory.md
- [I5](../../docs/sources/claude_code/01_instructions.md) `.claude/rules/`와 경로 한정 규칙 — https://code.claude.com/docs/en/memory.md
- [I6](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md 크기와 내용에 대한 공식 조언 — https://code.claude.com/docs/en/memory.md
- [I7](../../docs/sources/claude_code/01_instructions.md) `/init`, `/memory`, `/context all`, `/doctor` — https://code.claude.com/docs/en/memory.md
- [I8](../../docs/sources/claude_code/01_instructions.md) CLAUDE.md는 맥락이지 강제가 아니다 — https://code.claude.com/docs/en/memory.md
- [I10](../../docs/sources/claude_code/01_instructions.md) Skills의 위치 — https://code.claude.com/docs/en/skills.md
- [I11](../../docs/sources/claude_code/01_instructions.md) Skills의 적재 시점: 시작 때는 설명, 쓸 때 본문 — https://code.claude.com/docs/en/skills.md
- [I12](../../docs/sources/claude_code/01_instructions.md) Skills의 호출 제어와 도구 frontmatter — https://code.claude.com/docs/en/skills.md
- [I13](../../docs/sources/claude_code/01_instructions.md) 사용자 정의 슬래시 명령과 Skill은 한 장치다 — https://code.claude.com/docs/en/skills.md
- [I14](../../docs/sources/claude_code/01_instructions.md) Output style — https://code.claude.com/docs/en/output-styles.md
- [I15](../../docs/sources/claude_code/01_instructions.md) 확장 장치 비교: CLAUDE.md, Skill, subagent, hook, MCP, plugin — https://code.claude.com/docs/en/features-overview.md
- [I16](../../docs/sources/claude_code/01_instructions.md) 장치별 맥락 비용 — https://code.claude.com/docs/en/features-overview.md
- [I17](../../docs/sources/claude_code/01_instructions.md) 검증 기준을 지침으로 주기 (best-practices) — https://code.claude.com/docs/en/best-practices.md
- [S3](../../docs/sources/claude_code/04_state.md) 컨텍스트 윈도우에 채워지는 것과 `/context` — https://code.claude.com/docs/en/context-window.md
- [S12](../../docs/sources/claude_code/04_state.md) transcript 위치와 형식 경고 — https://code.claude.com/docs/en/sessions.md
- [S17](../../docs/sources/claude_code/04_state.md) auto memory — https://code.claude.com/docs/en/memory.md
- [T2](../../docs/sources/claude_code/02_tools.md) 도구 이름은 권한 규칙의 키다 — https://code.claude.com/docs/en/tools-reference
- [T3](../../docs/sources/claude_code/02_tools.md) Glob·Grep은 macOS·Linux에서 기본 도구가 아니다 — https://code.claude.com/docs/en/tools-reference
- [T4](../../docs/sources/claude_code/02_tools.md) Bash 도구: 작업 디렉터리와 환경 변수는 어디까지 이어지나 — https://code.claude.com/docs/en/tools-reference
- [T5](../../docs/sources/claude_code/02_tools.md) Bash 도구: 시간 제한과 출력 한도 — https://code.claude.com/docs/en/tools-reference
- [T8](../../docs/sources/claude_code/02_tools.md) MCP 설치 범위 세 가지와 저장 위치 — https://code.claude.com/docs/en/mcp
- [T10](../../docs/sources/claude_code/02_tools.md) 프로젝트 `.mcp.json` 서버의 승인 — https://code.claude.com/docs/en/mcp
- [T11](../../docs/sources/claude_code/02_tools.md) MCP 도구 이름과 128자 한도 — https://code.claude.com/docs/en/mcp
- [T12](../../docs/sources/claude_code/02_tools.md) MCP 도구 검색(지연 로딩) — https://code.claude.com/docs/en/mcp
- [V6](../../docs/sources/claude_code/06_verification_records.md) OpenTelemetry 모니터링 — 켜는 방법 — https://code.claude.com/docs/en/monitoring-usage
- [V11](../../docs/sources/claude_code/06_verification_records.md) /insights (web.md 6(a) 재확인) — https://code.claude.com/docs/en/costs
- [V12](../../docs/sources/claude_code/06_verification_records.md) 구성 디버깅 — 무엇이 로드됐는지 보는 명령 — https://code.claude.com/docs/en/debug-your-config
