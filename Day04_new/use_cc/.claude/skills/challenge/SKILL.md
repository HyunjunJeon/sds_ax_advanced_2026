---
name: challenge
description: Day04_new Capability Challenge를 진행한다. 수강생이 원하는 능력 하나를 Skill과 MCP 서버로 만들어 plugin으로 쓰고 eval로 확인하도록 돕는다. 수강생이 /challenge 로 직접 부를 때만 쓴다.
argument-hint: "<내 plugin 이름>"
disable-model-invocation: true
---

# Capability Challenge 진행 (만드는 세션)

카드는 `challenge/challenge.md`다. 먼저 읽고 그 단계 순서를 따른다. 이 세션의 규칙은 `CLAUDE.md`(이 폴더)의 7장이다.

## 1. 시작

1. 현재 작업 폴더가 `Day04_new/use_cc`인지 확인한다. 아니면 그 폴더에서 다시 열라고 안내하고 멈춘다.
2. 부를 때 받은 인자가 plugin 이름이면 `challenge/work/<이름>/`이 있는지 본다.
   - 없으면 수강생에게 이름을 확인받고 `uv run python challenge/new_capability.py <이름>`을 실행한다(모델 호출 없음).
   - 인자가 없으면 무엇을 만들고 싶은지부터 묻는다. 이름은 수강생이 정한다.
3. 예시 plugin(`challenge/examples/example-tasks`)의 `server/server.py` 맨 위 관례 다섯 가지와 `CAPABILITY.md`를 수강생과 같이 훑는다.

## 2. 누가 무엇을 하나

| 수강생이 정한다 (대신 정하지 않는다) | Claude가 한다 |
|---|---|
| 무엇을 만들지, 누가 쓰는지 | 예시를 내 영역으로 바꾸는 코드: `server/server.py`, 계약 사례, eval 사례의 형식 |
| 도구를 어떻게 나눌지, 도구 이름, 인자와 enum 값, 업무 오류 코드 | 정한 것을 코드로 옮기고, 관례 다섯 가지를 지키게 한다 |
| 판단을 어디에 둘지(코드 규칙, 판단 모델, 생성, 사용자에게 묻기) | 그 판단을 구현한다. 판단할 수 없을 때 통과시키지 않게 한다 |
| Skill의 description(언제 쓰고 언제 쓰지 않는가)과 오류 코드별 행동 | SKILL.md 초안을 쓰되, 수강생이 정한 조건과 행동을 그대로 옮긴다 |
| eval 사례의 **기대 동작**(이 말이면 무엇을 해야 하는가) | 그 기대를 판정기(`tool_used`, `regex` 등)로 옮긴다 |
| 첫 실패를 보고 **어디를** 고칠지 | 고친다. 한 번에 한 곳만 |
| `CAPABILITY.md`의 설명 | 쓰지 않는다. 빈칸을 가리키고, 근거가 될 기록(검사기 결과, eval 표, 실행 기록)을 찾아 준다 |

수강생이 정해야 할 것을 정하지 않은 채 "알아서 해 줘"라고 하면, 고를 수 있는 선택지 두세 개와 각각의 대가를 보여 주고 고르게 한다.

## 3. 돌려도 되는 것과 고지

- 검사기 `uv run python tools/check_capability.py challenge/work/<이름>`은 모델을 부르지 않는다. 고칠 때마다 돌린다.
- `uv run python tools/run_eval.py challenge/work/<이름> …`은 **유료**다. 실행 전에 도구가 내는 `[고지]` 줄의 규모를 수강생에게 먼저 말하고, 수강생이 진행하라고 할 때 돌린다.
- `claude plugin eval`을 직접 치지 않는다. 직접 치면 보고서가 claude.ai에 게시되고(`--no-publish`가 빠진다) MCP 서버가 가짜로 바뀐다(`--mocks off`가 빠진다). 언제나 `run_eval.py`를 쓴다.
- `--keep-temp`로 남긴 임시 폴더는 다 본 뒤 도구가 출력한 명령으로 지운다.
- 써 보는 세션(터미널 2)은 저장소 밖 폴더에서 `claude --plugin-dir <plugin 절대 경로>`로 연다. 이 세션에서 써 보는 대화를 대신 하지 않는다.

## 4. 결과를 다루는 법

- eval 결과의 실패를 지우거나, 통과하도록 판정기를 느슨하게 바꾸지 않는다. 판정기를 바꿔야 한다고 수강생이 판단하면, 기대 동작이 바뀐 이유를 `CAPABILITY.md`에 적게 한다.
- 실패가 하나도 없으면 더 어려운 사례를 하나 더 만들자고 제안한다. 무엇이 어려운지는 수강생이 정한다.
- 기준선(plugin 없음)과의 차이(Δ)가 0인 사례는 "내 plugin이 없어도 같다"는 뜻이다. 그 사례가 무엇을 확인하는지 수강생과 다시 본다.
- 한 번의 결과를 "잘 동작한다"고 말하지 않는다. "1회 관찰"이라고 부르고, `--runs`를 늘리는 선택지를 알려 준다.

## 5. 막히는 곳

카드(`challenge/challenge.md`)의 6절 표를 먼저 본다. 그 밖에:

| 증상 | 먼저 볼 것 |
|---|---|
| 검사기의 계약 사례가 실패 | 실패 문장에 나온 호출 번호와 기대. 서버가 업무 오류를 예외로 던지는지(`is_error=True`), 중복 방지가 빠졌는지 |
| "장애 주입: 시험할 호출" 실패 | 계약 사례에 부작용 도구(readOnlyHint=false)를 고정 인자로 부르는 호출이 있는지 |
| "Skill이 오류 코드를 안내" 실패 | SKILL.md 본문에 계약 사례의 오류 코드와 `permission_denied`, `temporarily_unavailable`에 대한 행동이 있는지 |
| eval의 `fault` 사례에서 거부가 일어나지 않는다 | `prompt.md`의 `env`에 `EVAL_CAPABILITY_FAULT`가 있는지, 값이 JSON 문자열인지 |
