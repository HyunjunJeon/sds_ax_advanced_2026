# M1. 내 사례의 능력을 설계한다 (Part 1 · 미션 20분)

> **핵심 질문: 능력은 무엇으로 이루어지고, 판단은 어디에 두는가?**
>
> 강사가 강사 사례(요구사항 인터뷰 서버)로 보여 준 것을 이제 **내 사례**에 적용합니다.
> 이 미션이 끝나면 손에 두 가지가 남습니다. (1) 강사 사례 서버가 나를 인터뷰해 고정한 명세(seed), (2) 내 능력 설계서.
> 둘 다 Part 2부터 계속 씁니다.

## 이 미션의 비용

| 무엇 | 규모 | 누구의 비용 |
|---|---|---|
| 터미널 2의 인터뷰 | Claude Code 호출 약 10~15회. 저자 확인에서 11~13회였다(녹화본 11회, 대화형 Opus 13회, 대화형 Sonnet 12회) | 내 Claude Code 계정 |
| 서버의 완료 기준 판정 | Jev 1~3회. 완료 기준을 답할 때마다 한 번 | `Day04_new/.env`의 Decision API 키 |
| 터미널 1의 조교 세션 | Claude Code 호출 약 5~10회. 저자 확인에서 6회였다. `!` 명령을 칠 때마다 조교가 한 번 답한다 | 내 Claude Code 계정 |
| 선택 깨뜨리기 | Claude Code 호출 약 1~6회 | 내 Claude Code 계정 |

판정 모델(Jev)에는 내가 말한 완료 기준 문장이 그대로 전송됩니다. 실제 업무 자료를 넣지 마세요(`case_criteria.md`의 C6).

## 표지 읽는 법

노트북과 같은 표지를 씁니다. 조교 세션(터미널 1)도 이 표지에 맞춰 돕습니다.

| 표지 | 뜻 |
|---|---|
| `[따라하기]` | 강사가 시연에서 보여 준 것을 그대로 해 본다 |
| `[내 것 만들기]` | 입력을 내가 정한다. 조교가 대신 정해 주지 않는다 |
| `[깨뜨리기]` | 일부러 규칙을 어긴다. 고칠 대상이 아니라 관찰 대상이다 |
| **먼저 예측하세요.** | 실행 전에 예측을 적는다. 조교는 예측을 듣기 전에 결과를 말하지 않는다 |
| **관찰할 것.** | 어느 칸을 읽을지만 알려 준다. 정답은 적혀 있지 않다 |

## 터미널에서 명령을 치는 법

이 미션에서는 터미널 두 개가 모두 Claude Code 화면이 됩니다. 그 화면에서 셸 명령을 치려면 **앞에 `!`를 붙입니다.**

- 예: `!ls notes`. 명령이 실행되고, 그 출력이 대화에 들어가며, Claude가 한 번 답합니다.
- `!` 명령은 **터미널 1(조교 세션)에서만** 칩니다. 터미널 2(실험 대상 세션)에 치면 그 출력이 실험 대상의 대화에 섞입니다.
- `!` 대신 조교에게 "표를 보여 주세요"처럼 부탁해도 됩니다.

---

## 준비 (강사 시연을 따라 하며)

강사가 시연 2.1~2.2를 보여 줄 때 같이 합니다. 미션 20분에는 들어가지 않습니다.
**터미널 1은 조교 세션, 터미널 2는 실험 대상 세션**입니다. 실험 대상 세션은 강사 사례의 MCP 서버와 Skill만 가지고 시작해야 하므로 **저장소 밖**에 따로 만듭니다.

`[따라하기]` 터미널 1에서 (아직 Claude Code를 열기 전의 셸):

```bash
cd Day04_new/use_cc
uv run python setup_sandbox.py ~/day04-sandbox
claude
```

- 저장소 안의 경로를 주면 스크립트가 거절합니다. Claude Code는 시작한 폴더 위의 CLAUDE.md와 저장소 루트까지의 `.claude/skills`를 함께 읽기 때문입니다. 그러면 실험 대상 세션에 이 과정의 조교 규칙이 섞입니다.
- `Decision API 판정기를 만들 수 없습니다`가 나오면 `Day04_new/.env`의 Decision API 키를 직접 채우고 다시 실행합니다. 키 없이 진행하려면 `--gate off`를 붙입니다. 그러면 M1-2에서 서버가 완료 기준을 되묻지 않습니다.
- `claude`를 처음 열면 **"External imports"를 허용할지** 묻습니다. 위 폴더의 CLAUDE.md가 `@AGENTS.md`로 이 폴더 밖의 규칙 파일을 불러오기 때문입니다. 기본 선택은 "No"입니다. **화살표로 "Yes, allow external imports"를 고른 뒤** Enter를 누릅니다. "No"를 고르면 조교 세션에 과정의 공통 규칙이 실리지 않습니다.
- 조교 세션에서 `/mission part1`을 입력하면 조교가 이 카드를 같이 봅니다.

`[따라하기]` 터미널 2에서:

```bash
cd ~/day04-sandbox
claude
```

처음 열면 확인 화면이 두 번 나옵니다. **두 번 모두 기본 선택이 원하는 것이 아니므로 Enter만 누르지 마세요.**

| 화면 | 기본 선택 | 골라야 할 것 |
|---|---|---|
| 폴더를 신뢰하는가 (Quick safety check) | No, exit | ↓로 **Yes, I trust this folder** |
| 새 MCP 서버를 쓸 것인가 (New MCP server found in this project: requirements) | Continue without using this MCP server | ↑로 **Use this MCP server** |

- 서버 없이 시작해 버렸다면 `/exit`로 나와 `claude mcp reset-project-choices`를 실행한 뒤 다시 `claude`를 엽니다.
- `/mcp`를 입력해 `requirements`가 `✔`로 연결되어 있는지 봅니다. 내 계정에 붙은 다른 커넥터(claude.ai 커넥터 등)도 함께 보일 수 있습니다. 그것도 이 세션에 실린 도구입니다.

---

## M1-0. `[내 것 만들기]` 사례를 고른다 (2분)

`case_criteria.md`의 조건 여섯 가지(C1~C6)를 읽고 내 사례를 하나 고릅니다. 정하지 못했으면 같은 파일의 예시 다섯 개 중 하나를 고르거나 바꿔서 씁니다.
한 줄로 적어 둡니다. 예: "장애 티켓의 심각도를 정하고 담당 팀에 배정하는 도구"

## M1-1. 먼저 예측하세요 (2분)

`use_cc/notes/part1.md`를 만들고 아래 세 가지에 대한 예측을 한 줄씩 적습니다. 터미널 1에서 `!mkdir -p notes`로 폴더를 먼저 만듭니다.
강사 사례가 아니라 **내 사례**에 대한 예측입니다. 시연과 다르게 나올 수 있습니다. 적은 뒤 조교 세션에 "예측을 적었다"고 말합니다.

1. 내 사례의 첫 말을 하면 Claude Code는 강사 사례의 Skill(`requirements-interview`)을 부를까요? 그 Skill의 description(실험 폴더의 `.claude/skills/requirements-interview/SKILL.md` 3~6행)과 내 첫 말을 비교해서 이유를 적으세요.
2. Claude가 `start_interview`의 `goal` 인자에 내 말을 **그대로** 넣을까요, **바꿔서** 넣을까요?
3. M1-2에서 서버가 완료 기준을 되물으면, 대화 상자에 적은 내 답은 서버의 판정을 **다시 받을까요**, 받지 않고 그대로 기록될까요?

## M1-2. `[내 것 만들기]` 강사 사례 서버가 내 사례를 인터뷰한다 (10분)

터미널 2에서 내 사례로 인터뷰를 부탁합니다. 첫 말은 이렇게 시작해도 됩니다.

> "(내 사례 한 줄)을 만들고 싶어요. 어떤 걸 정해야 하는지 질문으로 정리해 주세요."

그다음 Claude가 묻는 대로 답합니다.

1. **제약**을 답합니다. 없으면 "없음"이라고 답합니다.
2. **완료 기준은 처음에 일부러 모호하게** 답해 봅니다. 예: "팀원들이 쓰기 편하면 완료예요."
3. 서버가 완료 기준을 되물으면 Claude Code 화면에 **대화 상자**가 뜹니다. 서버가 Claude를 거치지 않고 나에게 직접 묻는 것입니다(MRTR).
   대화 상자 위에는 `MCP server "requirements" requests your input`이 보이고, 진행 줄에는 `Fulfilling input required by 'tools/call'`이 보입니다.
   `* 완료 기준` 칸에 **실행 결과로 참/거짓을 확인할 수 있는** 완료 기준을 직접 적고, ↓로 `Accept`를 고른 뒤 Enter를 누릅니다. 예: "티켓 30건을 넣으면 P1으로 분류한 티켓이 모두 당직 팀에 배정된다"
4. Claude가 명세를 확정해도 되는지 물으면 확인해 주고, `status=frozen`이 될 때까지 진행합니다.

진행하면서 만날 수 있는 화면:

- 권한 모드가 기본(manual)이면 MCP 도구를 **도구마다 처음 부를 때** `Do you want to proceed?`를 묻습니다(`start_interview`, `record_answer`, `freeze_seed`, … 각각). 화면에 도구 이름, 인자, 도구 설명이 보입니다. 읽어 보고 `1. Yes`를 고릅니다. auto mode면 묻지 않습니다.
- 여기서 `3. No`를 고르면 그 턴이 멈추고 `Interrupted · What should Claude do instead?`가 뜹니다. 서버에는 아무것도 기록되지 않습니다. 다시 하려면 "다시 시작해 주세요"라고 말하고 이번에는 승인합니다.
- 화면에는 도구 호출이 `Called requirements 2 times`처럼 접혀 보입니다. 어떤 도구를 어떤 순서로 불렀는지는 아래 표로 봅니다.

**관찰할 것.**

- 터미널 1에서 기록을 표로 봅니다(또는 조교에게 부탁합니다).

  ```text
  !uv run python tools/show_session.py --latest ~/day04-sandbox
  ```

  표의 `도구` 열에서 `Skill`과 `(지침)` 줄이 있는지, 첫 `mcp__requirements__…` 줄 앞에 무엇이 있는지, `start_interview`의 `goal` 인자를 읽습니다. 예측 1, 2와 비교합니다.
- 대화 상자가 떴다면, 그 문장은 누가 만든 것인지 서버 코드에서 찾아보세요(`cap_lab/server/server.py:242-246`). 대화 상자에 답한 뒤 Claude가 한 말에서, Claude가 그 답을 알고 있었는지도 봅니다.
- 실험 폴더의 `evidence/<서버 세션 ID>/event-*.json` 중 `answer_recorded`이고 `field`가 `acceptance_criteria`인 파일의 `gate` 칸. `score`, `threshold`, `source`를 읽습니다. `source`가 `elicited`이면 `original` 칸도 있습니다. `score`는 어느 문장의 점수인지 확인하고 예측 3과 비교합니다(`cap_lab/server/server.py:283-290`).

**결과는 1회 관찰입니다.** 같은 말을 해도 실행마다 도구 순서나 호출 수가 다를 수 있습니다. 옆 사람과 다르게 나왔다면 틀린 것이 아니라 비교할 거리입니다.

## M1-3. `[내 것 만들기]` 내 능력 설계서를 쓴다 (6분)

양식을 복사하고 0~4절을 채웁니다. 터미널 1에서:

```text
!mkdir -p notes && cp part1/design_sheet.md notes/design_sheet.md
```

- 1절(seed)은 M1-2의 결과를 옮겨 적습니다. seed 파일은 실험 폴더의 `evidence/<서버 세션 ID>/seed-<ID>.json`에 있습니다.
- 3절은 **내 사례**의 네 요소입니다. 강사 사례의 네 요소를 다시 적는 것이 아닙니다.
- 4절은 내 사례에서 무언가를 정하는 곳을 세 군데 이상 찾아 코드 규칙, 판단 모델(Jev), 생성(LLM)으로 나눕니다.
- 막히면 `design_sheet_example.md`(강사 사례로 채운 예시)의 **0~4절만** 봅니다. 칸을 얼마나 자세히 적는지만 참고하고, 내용은 내 사례로 씁니다. 5~6절에는 예측과 확인 질문의 예시 답이 있으니, 내 답을 먼저 쓴 뒤에 봅니다.
- 조교 세션은 빈칸을 가리키고 질문할 수 있지만 칸을 대신 채우지 않습니다.

## 마치기 전에 확인

| 확인할 것 | 확인하는 법 (터미널 1) |
|---|---|
| 명세가 확정되었다 | `!ls ~/day04-sandbox/evidence/*/seed-*.json`에 파일이 하나 이상 있다. seed 파일은 `freeze_seed`가 성공했을 때만 생긴다 |
| 예측과 설계서가 있다 | `!ls notes`에 `part1.md`(예측 세 줄)와 `design_sheet.md`(0~4절)가 있다 |

## 선택. `[깨뜨리기]` 지침을 빼면 (유료, 시간이 남을 때만)

노트북의 Deep Agent에서는 Skill 폴더를 비우면 MCP 도구가 하나도 보이지 않았습니다(`01-Agent-Capability.ipynb` 3.4절). Claude Code에서도 같을까요?

**먼저 예측하세요.** Skill을 빼고 같은 첫 말을 하면 Claude Code는 `start_interview`를 부를까요? 부르지 않는다면 무엇을 할까요?

터미널 2에서 `/exit`로 나온 뒤, 셸에서:

```bash
mv .claude/skills/requirements-interview .claude/skills-off-requirements-interview
claude
```

M1-2와 같은 첫 말을 한 번만 하고, 터미널 1에서 `!uv run python tools/show_session.py --latest ~/day04-sandbox`로 표를 봅니다(이번에는 방금 연 세션이 표에 나옵니다).
끝나면 터미널 2에서 다시 `/exit`로 나와 **반드시 되돌립니다.**

```bash
mv .claude/skills-off-requirements-interview .claude/skills/requirements-interview
```

**관찰할 것.** 표에 `Skill`과 `(지침)` 줄이 있는가, MCP 도구 줄이 있는가, 실험 폴더의 `evidence/`에 새 세션 폴더가 생겼는가. 오류가 났는지가 아니라, 오류 없이 무엇이 달라졌는지를 봅니다.

---

## 확인 질문 (해설 시간에 내 말로 답합니다)

설계서 6절에도 같은 다섯 질문이 있습니다. 그곳에 답을 적어 둡니다.

1. 내 사례의 네 요소를 하나씩 대 보세요. 그중 하나를 뺐을 때 **오류 없이** 쓸모없어지는 것은 무엇인가요?
2. 터미널 2에서 MCP 도구의 **정의(인자 형식)** 는 처음부터 Claude에게 있었나요? 표의 어느 줄이 그 근거인가요? 노트북의 Deep Agent와는 무엇이 다른가요?
3. 완료 기준을 되물은 것은 Claude인가요, 서버인가요? 그 판단을 판단 모델(Jev)에 둔 이유를 입력의 성질로 설명해 보세요.
4. 내 설계서 4절에서 코드 규칙으로 둔 판단 하나를 고르세요. 그 입력이 정말 닫힌 집합인가요?
5. 내 인터뷰 결과는 1회 관찰입니다. "이 능력은 잘 동작한다"고 말하려면 무엇이 더 있어야 하나요?
