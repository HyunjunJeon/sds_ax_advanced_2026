# 할 일 보관함 (Capability Challenge 예시)

> 강사 쪽에서 채운 **예시**입니다. 수강생의 `CAPABILITY.md`는 `blank/CAPABILITY.md`에서 시작하고, 자기 말로 씁니다.
> 6절의 숫자는 저자가 2026-11-04에 Claude Code 2.1.318, `claude-sonnet-5-5`로 `claude plugin eval`을 한 번 돌린 결과입니다. 1회 관찰입니다.

## 1. 이 능력이 하는 일

혼자 일하는 사람이 Claude Code에게 "이거 할 일에 넣어 줘", "남은 거 보여 줘", "그거 끝났어"라고 말하면, 할 일이 시험 폴더의
`.capability-data/tasks.json`에 쌓이고 바뀝니다. 데이터는 지어낸 할 일뿐이고, 바깥 시스템과 통신하지 않습니다.

## 2. 능력의 네 요소

| 요소 | 이 능력에서 무엇인가 | 빠지면 어떻게 되는가 |
|---|---|---|
| 지침 | `skills/task-keeper/SKILL.md`. 언제 쓰고 언제 쓰지 않는지(description), 제목을 다듬지 말 것, 오류 코드별 행동 | 도구는 그대로 남는다. Part 1의 관찰대로라면 Claude가 도구를 쓰지 않고 글로만 답할 수 있다(이 plugin에서는 확인하지 않았다) |
| 도구 | MCP 서버 `tasks`의 `add_task`, `list_tasks`, `complete_task` | 할 일을 저장할 수 없다. 서버가 뜨지 않으면 `/mcp`에 실패로 보인다 |
| 실행 제어 | 서버의 업무 규칙(제목 길이, 없는 ID 거절), 장애 주입(`CAPABILITY_FAULT`), Claude Code의 도구 승인 | 규칙이 없으면 한 글자 제목 같은 쓸모없는 할 일이 쌓인다 |
| 상태 | `${CLAUDE_PROJECT_DIR}/.capability-data/tasks.json` | 세션을 닫으면 할 일이 사라진다. 시험 폴더마다 따로 생기므로 실험끼리 섞이지 않는다 |

## 3. 도구 설계

| 도구 | 하는 일 | 부작용 | annotations를 그렇게 적은 이유 |
|---|---|---|---|
| `add_task` | 할 일 추가 | 할 일이 하나 생긴다 | 같은 제목의 열린 할 일이 있으면 새로 만들지 않으므로 `idempotentHint=true`. 지우지 않으므로 `destructiveHint=false`. `checks/contract.jsonl`의 `add-twice-is-idempotent`가 이것이 사실인지 본다 |
| `list_tasks` | 목록 보기 | 없음 | 아무것도 바꾸지 않으므로 `readOnlyHint=true` |
| `complete_task` | 끝냄 표시 | 상태가 done으로 바뀐다 | 이미 끝낸 것을 다시 끝내도 결과가 같으므로 `idempotentHint=true`. `complete-twice-is-idempotent`가 본다 |

`priority`와 `status`는 정해진 값만 받으므로 enum으로 받는다. 모델이 "높음"처럼 다른 말을 넣지 못하게 하려는 것이다.

## 4. 판단은 어디에 두었나

| 무엇을 정하나 | 어디에 두었나 | 이유 |
|---|---|---|
| 제목이 쓸 만한가 | 코드 규칙(두 글자 이상) | 입력이 길이라는 닫힌 조건으로 줄어든다. "실제 행동인가"까지 보려면 판단 모델이 필요하지만, 라벨을 구할 방법이 아직 없어 두지 않았다 |
| 어느 할 일을 끝낼까 | 사용자에게 묻기(Skill 3번) | 제목이 겹치면 짐작하면 안 된다. 틀리면 엉뚱한 일이 끝난 것으로 남는다 |
| 우선순위 | 사용자가 말한 대로, 말하지 않으면 기본값 | 모델이 우선순위를 지어내면 사용자의 판단이 바뀐다 |

## 5. 견고성

- **권한 거부:** `permission_denied`가 오면 Skill이 같은 호출을 되풀이하지 말라고 한다. eval 사례 `permission-denied`가 이것을 본다.
- **일시 장애:** `temporarily_unavailable`(retryable)이 오면 같은 인자로 한 번만 다시 보낸다. 아직 eval 사례로 확인하지 않았다(7절).
- **중복 실행:** `add_task`와 `complete_task`는 두 번 와도 결과가 한 번과 같다. 검사기의 계약 사례가 확인한다.
- **판단할 수 없을 때:** 제목이 겹치면 끝내지 않고 묻는다.

## 6. 확인 결과

`uv run python tools/run_eval.py challenge/examples/example-tasks --runs 1`과 같은 조건으로 한 번 돌렸다(저자, 2026-11-04).

| 사례 | plugin 있음 | plugin 없음(기준선) | 읽은 것 |
|---|---|---|---|
| `add-with-priority` | 통과 (Skill 불림, `add_task`를 priority=high로 1회) | 실패 (도구가 없다) | 이 능력이 없으면 할 일을 저장할 수 없다 |
| `concept-question` | 통과 (추가하지 않음) | 통과 | 불리면 안 되는 질문에 쓸데없이 불리지 않았다. 기준선과 차이는 없다 |
| `permission-denied` | 통과 (거부 뒤 되풀이하지 않고 권한 문제를 알림) | 절반 (되풀이는 없지만 권한 이야기를 하지 않음) | 기준선은 도구가 없어 거부를 겪지도 않는다 |

평균 차이(Δ)는 0.5였다. 실행 기록(`--keep-temp`로 남긴 trace)에서 `permission-denied`의 순서는 `Skill`(example-tasks:task-keeper) → `ToolSearch` → `add_task` → `success=false error=permission_denied`였다.
실패한 사례가 없어 고친 것은 없다. 반복하지 않은 1회 관찰이다.

## 7. 남은 한계

- 일시 장애(`temporarily_unavailable`)를 eval 사례로 확인하지 않았다.
- 제목이 겹칠 때 묻는지(Skill 3번)를 eval 사례로 확인하지 않았다. 할 일을 미리 넣어 두는 준비가 필요하다.
- 각 사례를 1회만 돌렸다. "잘 동작한다"고 말하려면 `--runs`를 늘려 흔들림을 봐야 한다.
- 이 plugin의 `.mcp.json`은 이 저장소의 `.venv`를 쓴다. 다른 기계로 옮기려면 서버를 띄우는 방법을 바꿔야 한다.
