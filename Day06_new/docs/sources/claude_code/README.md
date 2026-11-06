# Claude Code 근거 대장 색인 (확인일 2026-11-06, Claude Code 2.1.318)

Claude Code 공식 문서(code.claude.com)를 쪽별로 내려받아 인용문을 문자열로 대조한 근거 대장이다. 파일마다 마지막 줄에 `Quotes verified: n/n`이 있다. 수업 자료의 Claude Code 사실은 아래 항목 ID로 인용한다.

| 파일 | 책임 | ID 범위 | 항목 수 | 인용 수 |
|---|---|---|---|---|
| [01_instructions.md](01_instructions.md) | 지침 | I1~I19 | 19 | 163 |
| [02_tools.md](02_tools.md) | 도구 | T1~T21 | 21 | 78 |
| [03_control.md](03_control.md) | 실행 제어 | C1~C21 | 21 | 151 |
| [04_state.md](04_state.md) | 상태 | S1~S17 | 17 | 64 |
| [05_execution.md](05_execution.md) | 계획과 실행 구조 | X1~X16 | 16 | 87 |
| [06_verification_records.md](06_verification_records.md) | 검증·기록 | V1~V13 | 13 | 76 |
| [07_commands_cli.md](07_commands_cli.md) | 명령·CLI·키 조작 | K1~K3 | 3 (표 행 다수) | 79 |
| [08_plugin_candidates.md](08_plugin_candidates.md) | Part 4 plugin 후보 | P1~P3 | 3 | 해당 없음 |

08은 `Quotes verified` 줄이 없다. 후보 저장소를 SHA로 고정해 `path:line`으로 인용하는 방식이라 github.md와 같은 쪽이다. 마지막 줄은 추천(`anthropics/claude-plugins-official@1aa4a4b`)이다.

## 이전 대장과의 관계

[../web.md](../web.md) 6절(확인일 2026-11-05)은 이 대장의 앞선 부분집합이다. 6(a)~6(e)의 인용문을 오늘 쪽과 다시 대조했다.

- 6(a) 비용·`/insights`: 8개 모두 통과, 변경 없음. 다만 `commands` 쪽 `/insights` 행의 뒷부분이 길어졌고(앞 문장은 그대로), V11에 두 가지가 더해졌다(자동 모드가 처리했을 권한 프롬프트 추정, 보고서를 `cleanupPeriodDays`(기본 30일) 뒤에 삭제).
- 6(b) plan 모드, 6(c) 훅: 11개 모두 통과, 변경 없음. `defer` 문장은 `-p`가 코드 표시로 바뀌어 백틱을 지운 뒤에만 일치한다(서식 차이일 뿐 낱말은 같다).
- 6(d) CLAUDE.md·auto memory: 변경 없음.
- 6(e) transcript 등: 대조 가능한 것은 변경 없음. 아래 2개는 `claude-directory` 쪽을 내려받지 않아 이번에 대조하지 못했다(변경 여부 미확인): "Conversation transcript: messages, tool calls, and tool results", "The default is 30 days and the minimum is 1". 30일 보존 값은 `sessions`와 `checkpointing`에서 다시 확인했다.
- 변경된 인용문 목록: 변경 없음(깨진 인용문 0개).
- 방식 차이: web.md는 코드 표시를 지우고 대조했고, 이 대장은 파일마다 0절에 정규화 방식을 적었다(06은 백틱을 그대로 두고 대조).

## 대화형 전용·미확인 항목

`grep -n -E '미확인|대화형 전용'`으로 8개 파일을 훑어 항목 ID별로 모았다. 항목 단위로 64개이고, 이 밖에 항목에 속하지 않는 파일 공통 문구(0절 방법, 맺음 주의)가 07 외 모든 파일에 있다. 대화형 명령은 모델을 부르거나 세션 안에서만 동작해 실행하지 않았다. 수업 전에 저자가 한 번 손으로 확인해야 한다.

| 파일 | 항목 수 | ID |
|---|---|---|
| 01_instructions.md | 16 | I1, I2, I3, I4, I5, I6, I7, I9, I10, I11, I12, I14, I16, I17, I18, I19 |
| 02_tools.md | 13 | T1, T3, T4, T5, T7, T9, T10, T11, T12, T16, T17, T18, T21 |
| 03_control.md | 9 | C2, C5, C7, C8, C10, C11, C12, C13, C18 |
| 04_state.md | 11 | S3, S4, S5, S6, S9, S10, S11, S13, S14, S15, S17 |
| 05_execution.md | 9 | X3, X4, X6, X7, X8, X9, X10, X14, X15 |
| 06_verification_records.md | 5 | V1, V2, V10, V11, V12 |
| 07_commands_cli.md | 1 | K1 (명령 행 전부 "문서 확인, 대화형 미확인") |
| 08_plugin_candidates.md | 0 | 해당 없음 |

특별히 짚을 것:

- X14: "explore, plan, implement, commit" 네 단계 패턴은 common-workflows에서 찾지 못해 미확인이다.
- T3: `--tools` 동작은 미확인이다.
- C14의 "Edit만 거는 훅은 Bash로 쓴 파일을 못 본다"는 추론이며 실제 세션 반례가 필요하다.
- 05의 `--teammate-mode`는 문서도 `--help`에 없다고 적는다.
