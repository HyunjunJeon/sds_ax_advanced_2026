# Part 1. Coding Agent와 AI SDLC(Software Development Life Cycle) (개념 12분 + 시연 5분)

## 핵심 질문

> **채팅으로 묻는 것과 에이전트에게 맡기는 것은 무엇이 다르고, 맡긴 일의 각 행동은 SDLC의 어느 단계인가?**

이 문서의 Claude Code 사실은 모두 `Day06_new/docs/sources/claude_code/`의 근거 대장에 항목이 있는 것만 적는다. 문장 뒤의 `S1` 같은 표시는 그 항목 번호이고, 누르면 대장 파일로 간다. 대장에 없는 것은 쓰지 않았다. 이 Part의 미션은 실험 폴더 하나에서 요청 하나를 맡기고 첫 1분을 관찰하는 것이다. 단계는 `mission.md`에 있다.

---

## 1. 채팅과 에이전트: 도구가 있어야 에이전트다

Claude Code는 모델 둘레에서 도구를 주고 모델이 보는 맥락을 관리하는 층이다. 공식 문서는 이 층을 agentic harness라고 부른다 ([S2](../../docs/sources/claude_code/04_state.md)). 루프는 두 구성요소로 돈다. 추론하는 모델과 행동하는 도구다 ([S2](../../docs/sources/claude_code/04_state.md)). 도구가 없으면 Claude는 글로만 답한다 ([S2](../../docs/sources/claude_code/04_state.md)). 채팅으로 묻는 것은 이 글 답이고, 에이전트에게 맡기는 것은 도구로 파일을 읽고 고치고 명령을 돌리는 일이다.

에이전트 루프는 세 단계다. 맥락 모으기, 행동, 결과 확인이다. 사용자는 어느 지점에서든 끼어들 수 있다 ([S1](../../docs/sources/claude_code/04_state.md)). 문서는 세 단계가 서로 섞인다고도 적는다. 순서가 고정된 파이프라인으로 외우지 않는다 ([S1](../../docs/sources/claude_code/04_state.md)).

내장 도구 가운데 Read는 승인이 필요 없고 Edit·Write·Bash는 필요하다 ([T1](../../docs/sources/claude_code/02_tools.md)). 관찰은 자유롭고 변경은 승인을 거친다. 도구 표는 모델과 플랫폼에 따라 달라지므로 도구가 몇 개라고 숫자로 외우지 않는다 ([T1](../../docs/sources/claude_code/02_tools.md)).

## 2. 시작 권한 모드: 무엇이 묻지 않고 실행되는가

Claude Code v2.1.283 이상에서 대화형 터미널 세션의 시작 권한 모드는 기본이 auto다 ([C10](../../docs/sources/claude_code/03_control.md)). 모드는 `--permission-mode` 플래그로 시작할 때 지정한다 ([C10](../../docs/sources/claude_code/03_control.md), [K2](../../docs/sources/claude_code/07_commands_cli.md)). 화면의 Manual과 설정값 `default`는 같은 모드이고, CLI는 `manual`을 별칭으로 받는다 ([C6](../../docs/sources/claude_code/03_control.md), [C10](../../docs/sources/claude_code/03_control.md)).

auto는 승인이 없는 모드가 아니다. 별도의 분류기 모델이 행동을 실행 전에 검토하고, 분류기 호출은 토큰 비용에 들어간다 ([C8](../../docs/sources/claude_code/03_control.md)). auto가 안전을 보장하지도 않는다 ([C8](../../docs/sources/claude_code/03_control.md)).

그래서 이 수업은 실험 세션을 아래 명령으로 연다.

```
claude --permission-mode acceptEdits
```

acceptEdits는 파일 편집과 `mkdir, touch, rm, rmdir, mv, cp, sed`를 묻지 않고 실행하고, 그 밖의 Bash 명령은 읽기 전용 내장 집합을 빼고 묻는다 ([C6](../../docs/sources/claude_code/03_control.md)). 이 수업이 acceptEdits를 고르는 이유는 두 가지다. 어떤 행동이 묻지 않고 실행되는지가 표로 정해져 있어서 관찰이 쉽고, 분류기 호출이라는 변수가 실험에 끼지 않기 때문이다 ([C6](../../docs/sources/claude_code/03_control.md), [C8](../../docs/sources/claude_code/03_control.md)). 세션을 연 뒤에는 상태 줄에서 모드를 먼저 확인한다 ([C10](../../docs/sources/claude_code/03_control.md)).

## 3. 일찍 바로잡기와 끝 확인

- **Esc**: 현재 응답이나 도구 호출을 중간에 멈추고 방향을 바꾼다. 거기까지 한 일은 남는다 ([K3](../../docs/sources/claude_code/07_commands_cli.md), [I18](../../docs/sources/claude_code/01_instructions.md)).
- **`/clear`**: 두 번 고쳐도 틀리면 세 번째 교정 대신 `/clear`로 대화를 비우고 배운 것을 넣어 새로 쓴다 ([I18](../../docs/sources/claude_code/01_instructions.md), [K1](../../docs/sources/claude_code/07_commands_cli.md)).
- **통과/실패 검사를 같이 준다**: Claude는 일이 끝나 보이면 멈춘다. "끝났다고 했는데 아니었다"는 대개 스스로 확인할 방법이 없었기 때문이다. 통과나 실패로 돌아오는 검사를 주고, 명령과 그 출력이라는 근거(Evidence)를 요구한다 ([I17](../../docs/sources/claude_code/01_instructions.md)). 보지 않은 세션에서는 이것이 유일한 근거다 ([I17](../../docs/sources/claude_code/01_instructions.md)).

## 4. 기록: 한 일을 어디서 보는가

- 대화 기록은 `~/.claude/projects/<project>/<session-id>.jsonl`에 쌓인다. 형식은 내부용이고 버전마다 바뀌므로 직접 파싱하는 스크립트는 깨질 수 있다 ([S12](../../docs/sources/claude_code/04_state.md)).
- **Ctrl+O**로 트랜스크립트 보기를 열면 도구 사용의 상세가 보인다 ([K3](../../docs/sources/claude_code/07_commands_cli.md)).
- **`/usage`**는 세션 비용을 보여 준다 ([K1](../../docs/sources/claude_code/07_commands_cli.md), [V10](../../docs/sources/claude_code/06_verification_records.md)). 구독자에게는 달러 값이 청구와 무관하다 ([V10](../../docs/sources/claude_code/06_verification_records.md)). `/clear`로 새 세션을 열면 합계가 초기화된다 ([V10](../../docs/sources/claude_code/06_verification_records.md)).

## 5. AI SDLC 여섯 단계

Anthropic의 *The AI-native SDLC playbook*은 소프트웨어 개발 수명 주기를 여섯 비선형 단계로 본다. Plan, Design, Build, Test, Deploy, Maintain이다 (`docs/sources/web.md:26`, 이 항목은 Claude Code 대장이 아니라 웹 원문 대장이다). 이 Part에서는 맡긴 일의 도구 호출 하나하나를 이 여섯 단계 중 어디에 놓을지 말하는 것까지 한다. 단계마다 남기는 산출물은 Part 3에서 다룬다.

## 6. 실패 → 책임 → 장치 → 확인

| 실패 | 책임 | Claude Code 장치 | 동작 확인 |
|---|---|---|---|
| 채팅 답을 손으로 옮기다 틀린다 | 도구 | 파일을 읽고 고치고 명령을 돌리는 내장 도구 ([T1](../../docs/sources/claude_code/02_tools.md), [S2](../../docs/sources/claude_code/04_state.md)) | `show_session.py` 표의 도구 호출 줄 |
| "끝났다"고 했는데 검사를 안 돌렸다 | 검증 | 검사 명령을 지침에 두고 근거를 요구 ([I17](../../docs/sources/claude_code/01_instructions.md)) | 표에서 구현 뒤에 `python3 -m unittest`가 있는가 |
| 엉뚱한 방향으로 오래 간다 | 실행 제어 | Esc, 두 번 틀리면 `/clear` ([I18](../../docs/sources/claude_code/01_instructions.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)) | 첫 1분 관찰 메모 |
| 어떤 행동이 묻지 않고 실행되는지 모른다 | 실행 제어 | 시작 모드를 명시하고 상태 줄로 확인 ([C10](../../docs/sources/claude_code/03_control.md), [C6](../../docs/sources/claude_code/03_control.md)) | 승인 화면이 뜬 호출 목록. `git commit`은 acceptEdits에서도 묻는다 ([C6](../../docs/sources/claude_code/03_control.md)) |

## 7. 시연 (5분)

같은 질문을 두 곳에 던진다. 예: "이 폴더의 테스트가 통과하는지 알려 줘."

1. 채팅(도구가 없는 곳)에 묻는다. 답은 글이다. 실제로 돌려 봤는지 확인할 수 없다 ([S2](../../docs/sources/claude_code/04_state.md)).
2. 실험 대상 세션을 `claude --permission-mode acceptEdits`로 열고 같은 질문을 던진다. 어떤 도구 호출에서 승인 화면이 뜨는지 본다 ([T1](../../docs/sources/claude_code/02_tools.md), [C6](../../docs/sources/claude_code/03_control.md)).
3. 답이 끝나면 Ctrl+O로 도구 호출을 연다. 호출 순서를 루프 세 단계 (모으기, 행동, 확인) 에 놓는다 ([K3](../../docs/sources/claude_code/07_commands_cli.md), [S1](../../docs/sources/claude_code/04_state.md)).

강사는 둘의 차이를 한 문장으로 말하게 한다. 한쪽은 말만 했고 다른 쪽은 실행한 명령과 출력이 남았다.

## 8. 잘 다루기 습관

1. 맡길 때 "끝을 무엇으로 확인할지" 명령 한 줄을 같이 준다 ([I17](../../docs/sources/claude_code/01_instructions.md)).
2. 첫 1분을 보고, 어긋나면 Esc. 두 번 고쳐도 틀리면 `/clear` 뒤 새로 쓴다 ([I18](../../docs/sources/claude_code/01_instructions.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)).
3. 세션을 열면 권한 모드부터 본다. 기본은 버전마다 다르다 ([C10](../../docs/sources/claude_code/03_control.md)).
4. 결과는 최종 답이 아니라 도구 호출 기록으로 읽는다 ([S12](../../docs/sources/claude_code/04_state.md), [K3](../../docs/sources/claude_code/07_commands_cli.md)).

## 근거

본문과 표에서 인용한 대장 항목이다. 링크는 이 저장소의 대장 파일이고, 오른쪽이 그 항목이 적은 공식 문서다.

- [C6](../../docs/sources/claude_code/03_control.md) 권한 모드 표: default, acceptEdits — https://code.claude.com/docs/en/permission-modes.md
- [C8](../../docs/sources/claude_code/03_control.md) auto 모드: 누가 결정하는가와 비용 — https://code.claude.com/docs/en/permission-modes.md
- [C10](../../docs/sources/claude_code/03_control.md) 모드 전환과 시작 모드 — https://code.claude.com/docs/en/permission-modes.md
- [I17](../../docs/sources/claude_code/01_instructions.md) 검증 기준을 지침으로 주기 (best-practices) — https://code.claude.com/docs/en/best-practices.md
- [I18](../../docs/sources/claude_code/01_instructions.md) 설계, 조기 교정 (best-practices) — https://code.claude.com/docs/en/best-practices.md
- [K1](../../docs/sources/claude_code/07_commands_cli.md) 내장 명령 — https://code.claude.com/docs/en/commands.md
- [K2](../../docs/sources/claude_code/07_commands_cli.md) CLI 플래그 — https://code.claude.com/docs/en/cli-reference.md
- [K3](../../docs/sources/claude_code/07_commands_cli.md) 키 조작 — https://code.claude.com/docs/en/interactive-mode.md
- [S1](../../docs/sources/claude_code/04_state.md) 에이전트 루프(세 단계) — https://code.claude.com/docs/en/how-claude-code-works.md
- [S2](../../docs/sources/claude_code/04_state.md) Claude Code는 무엇인가(모델과 도구, 하네스 표현) — https://code.claude.com/docs/en/how-claude-code-works.md
- [S12](../../docs/sources/claude_code/04_state.md) transcript 위치와 형식 경고 — https://code.claude.com/docs/en/sessions.md#where-transcripts-are-stored
- [T1](../../docs/sources/claude_code/02_tools.md) 내장 도구 목록과 권한 필요 여부 — https://code.claude.com/docs/en/tools-reference
- [V10](../../docs/sources/claude_code/06_verification_records.md) 비용 추적 명령 (/usage) — https://code.claude.com/docs/en/costs
- 웹 원문 대장 `docs/sources/web.md:26` — Claude, *The AI-native SDLC playbook* — https://claude.com/resources/articles/the-ai-native-sdlc-playbook
