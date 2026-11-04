# Capability Challenge: 내 능력 하나 완성하기

> **원하는 일 하나를 Claude Code가 잘 하게 만듭니다.**
> 언제·어떻게 할지는 **Skill**이, 무엇으로 할지는 **MCP 서버**가 맡습니다. 둘을 **plugin** 하나로 묶어 Claude Code에서 실제로 쓰고,
> `claude plugin eval`로 정말 되는지 확인합니다.
>
> 코드는 Claude가 써도 됩니다. **무엇을 만들지, 어떻게 나눌지, 무엇을 기대할지, 왜 그렇게 정했는지는 내가 정합니다.**

## 1. 무엇을 만드나

```
challenge/work/<내 plugin>/        (new_capability.py가 만든다. git에 올라가지 않는다)
  .claude-plugin/plugin.json       plugin 이름
  skills/<이름>/SKILL.md           언제 쓰고 언제 쓰지 않는가, 어떤 순서로, 오류가 나면 무엇을 하는가
  .mcp.json, server/server.py      MCP 서버. 도구 3~5개
  checks/contract.jsonl            계약 사례: 모델 없이 도구를 직접 불러 확인할 것 (검사기가 돌린다)
  evals/<사례>/prompt.md, graders/ eval 사례: Claude에게 말을 걸어 확인할 것 (claude plugin eval이 돌린다)
  CAPABILITY.md                    내 결정과 확인 결과를 내 말로 쓴 설명
```

**무엇이든 됩니다.** 내 업무에서 Claude Code가 대신 해 주면 좋겠는 일을 고르세요. Part 1에서 정한 사례를 이어 써도 됩니다.
조건은 하나만 꼭 지킵니다. **가상 데이터와 로컬 저장소만 씁니다**(`part1/case_criteria.md`의 C6). 실제 사내 시스템, 실제 고객 정보, 실제 계정에 연결하지 않습니다.
나머지 조건(C1~C5: 여러 단계의 상태, 부작용이 있는 도구, 거부될 만한 동작, 판단 지점, 도구 3~5개)은 있으면 아래 단계에서 실험할 거리가 많아집니다. 없으면 `CAPABILITY.md`에 왜 없는지 적습니다.

## 2. 두 곳에서 일합니다

| 어디 | 여는 법 | 하는 일 |
|---|---|---|
| **만드는 세션** (터미널 1) | `cd Day04_new/use_cc && claude` → `/challenge` | Claude와 함께 서버, Skill, 사례를 만든다. 검사기와 eval을 돌린다. 이 세션의 규칙은 `use_cc/CLAUDE.md`에 있다 |
| **써 보는 세션** (터미널 2) | 저장소 **밖**의 빈 폴더에서 `claude --plugin-dir <내 plugin 절대 경로>` | 만든 능력을 실제 사용자처럼 써 본다 |

써 보는 세션을 저장소 밖에서 여는 이유는 Part 1과 같습니다. 저장소 안이면 이 과정의 CLAUDE.md와 다른 Skill이 함께 실려, 무엇이 결과를 만들었는지 가를 수 없습니다.
`--plugin-dir`로 열면 plugin의 MCP 서버가 승인 화면 없이 바로 붙고, 서버의 상태는 그 폴더의 `.capability-data/`에 생깁니다(저자 확인은 `claude -p`로 했다, 2.1.318. 문서도 "plugin을 켜면 그 MCP 서버를 자동으로 시작한다"고 적는다: https://code.claude.com/docs/en/mcp.md).
Claude Code 화면 안에서 셸 명령을 치려면 앞에 `!`를 붙입니다.

## 3. 단계

### 0단계. 시작하기

```bash
cd Day04_new/use_cc
uv run python challenge/new_capability.py <내 plugin 이름>     # 예: incident-triage
```

예시 plugin(`challenge/examples/example-tasks`, 할 일 보관함)이 복사됩니다. **예시 자체를 먼저 읽으세요.** 서버의 관례 다섯 가지가 `server/server.py` 맨 위에 적혀 있습니다.

### 1단계. 무엇을 만들지 정한다 (내가 정한다)

- 누가, 어떤 상황에서, 무엇을 시키면, 무엇이 남는가를 한 문단으로 씁니다(`CAPABILITY.md` 1절).
- 막히면 Part 1처럼 강사 사례 서버에게 인터뷰를 받아도 됩니다(`part1/mission.md`의 M1-2).

### 2단계. MCP 서버를 만든다 (Claude가 쓰고, 내가 정한다)

내가 정하는 것: 도구를 어떻게 나눌지와 이름, 각 도구가 받는 인자와 정해진 값(enum), 어떤 업무 오류 코드를 돌려줄지, 상태가 바뀌는 순서를 어디서 막을지, 같은 호출이 두 번 오면 어떻게 할지.
Claude가 하는 것: `server/server.py`를 내 영역으로 바꾸고, `checks/contract.jsonl`에 계약 사례를 쓴다.

예시 서버의 관례를 지킵니다.

1. 업무 오류는 값으로: `{"success": false, "error": "<코드>", "message": "..."}`
2. 도구마다 annotations 네 개를 모두 적는다(실제 동작과 맞게)
3. 인자마다 타입과 설명, 정해진 값은 enum
4. 장애 주입: 환경 변수 `CAPABILITY_FAULT`(또는 `EVAL_CAPABILITY_FAULT`)로 권한 거부와 일시 장애
5. stdout에 print 하지 않는다

### 3단계. Skill을 쓴다

내가 정하는 것: 언제 쓰고 **언제 쓰지 않는가**(description), 어떤 순서로 도구를 쓰는가, 오류 코드마다 무엇을 하는가, 사용자에게 무엇을 물어야 하고 무엇을 지어내면 안 되는가.
description은 처음부터 Claude에게 보이고 본문은 Skill이 불릴 때 들어온다는 것(Part 1)을 기억하세요. 쓰지 않는 조건도 description에 둡니다.

### 4단계. 검사한다 (모델 호출 없음, 몇 번이든)

```bash
uv run python tools/check_capability.py challenge/work/<내 plugin>
```

"실패"가 하나도 없을 때까지 고칩니다. 검사기는 **모양**만 봅니다. 도구 설명이 좋은지, Claude가 제대로 고르는지는 보지 않습니다.

### 5단계. 써 본다

다른 터미널에서:

```bash
mkdir -p ~/cap-trial-<내 plugin> && cd ~/cap-trial-<내 plugin>
claude --plugin-dir <내 plugin의 절대 경로>
```

실제 사용자처럼 말을 겁니다. 만드는 세션에서 `!uv run python tools/show_session.py --latest ~/cap-trial-<내 plugin>`로 어떤 도구를 어떤 순서로 불렀는지 봅니다.
장애를 넣어 보려면 `CAPABILITY_FAULT='{"permission_denied": ["<도구>"]}' claude --plugin-dir …`로 엽니다.

### 6단계. 정말 되는지 확인한다 (유료)

eval 사례를 `evals/`에 씁니다. 사례마다 폴더 하나, 그 안에 `prompt.md`(말 한 번)와 `graders/*.md`(판정기)입니다. 예시의 세 사례를 보고 내 것으로 바꿉니다.
**네 종류가 하나씩은 있어야 합니다**(검사기가 봅니다).

| 태그 | 무엇을 보나 | 판정기 예 |
|---|---|---|
| `trigger` | 불려야 할 말에 Skill이 불리는가 | `type: tool_used`, `tool: Skill` |
| `should-not-trigger` | 불리면 안 되는 말에 도구를 쓰지 않는가 | `type: tool_used`, `tool: <도구>`, `min: 0`, `max: 0` |
| `selection` | 맞는 도구를 맞는 인자로 부르는가 | `type: tool_used`, `tool: <도구>`, `input_match: '<인자 정규식>'` |
| `fault` | 권한 거부나 일시 장애 뒤에 맞게 행동하는가 | `prompt.md`의 `env: {EVAL_CAPABILITY_FAULT: '…'}` + `tool_used`의 `max`, `type: regex` |

도구 이름은 `mcp__plugin_<plugin 이름>_<서버 이름>__<도구>` 꼴입니다. 판정기는 이 밖에 `tool_order`, `regex`, `file_exists`, `llm`(판정 모델이 채점, 비용이 더 든다)이 있습니다.

```bash
uv run python tools/run_eval.py challenge/work/<내 plugin> --runs 1
```

- 실행 직전에 규모를 알립니다. 저자의 예시 plugin(사례 3개, 1회, 기준선 포함)은 0.17달러, 1분이었습니다.
- 기본으로 **plugin이 없는 기준선**도 함께 돌려 차이(Δ)를 보여 줍니다. Δ가 0이면 내 plugin이 없어도 같은 결과라는 뜻입니다.
- 실행 기록을 보려면 `--keep-temp`를 붙이고 출력된 `trace.jsonl` 경로를 `tools/show_session.py`로 읽습니다.
- 결과는 `challenge/runs/`에 남습니다. 실패한 결과도 지우지 않습니다.

### 7단계. 고치고 다시 확인한다

- 처음 실패한 사례 하나를 고릅니다. 원인이 어디인지(description? Skill 본문? 도구 설명이나 인자 형식? 서버 규칙?) 기록을 보고 정한 뒤 **한 곳만** 고치고 다시 돌립니다.
- 실패가 하나도 없으면 더 어려운 사례를 하나 더 만듭니다. 실패하는 사례를 찾을 때까지가 확인입니다.
- 1회 관찰로 "고쳐졌다"고 말하지 않습니다. 가능하면 `--runs 3`으로 다시 봅니다.

### 8단계. `CAPABILITY.md`를 쓴다 (내가 쓴다)

`blank/CAPABILITY.md`의 일곱 절입니다. 무엇을 정했는지와 함께 **왜 그렇게 정했는지**를 씁니다. 확인 결과(6절)에는 실패한 것도 적습니다.

## 4. 기준표

| 대상 | 기준 | 누가 보나 |
|---|---|---|
| plugin | `plugin.json`의 이름, `claude plugin validate` 통과 | 검사기 |
| MCP | 도구 3~5개, 각 도구의 설명, 인자마다 타입과 설명 | 검사기 |
| MCP | annotations 네 개를 모두 적었다 | 검사기 |
| MCP | 업무 오류가 예외가 아니라 `success:false` + 오류 코드다 | 검사기(계약 사례) |
| MCP | 같은 호출을 두 번 보내도 annotations가 말한 대로다 | 검사기(계약 사례) |
| MCP | 장애 주입 관례(`CAPABILITY_FAULT`)가 동작한다 | 검사기 |
| MCP | 시작할 때 stdout에 아무것도 쓰지 않는다 | 검사기 |
| MCP | 판단할 수 없을 때 통과시키지 않는다 | 실제 실행 + 리뷰 |
| Skill | 머리말이 맞고 description이 1024자 이하, 쓰지 않는 조건이 있다 | 검사기 |
| Skill | 본문이 모든 도구와 모든 오류 코드(장애 주입의 두 코드 포함)에 대해 말한다 | 검사기 |
| Skill | 불려야 할 때 불리고, 불리면 안 될 때 불리지 않는다 | eval(`trigger`, `should-not-trigger`) |
| 사용 | 맞는 도구를 맞는 인자로 부른다 | eval(`selection`) |
| 사용 | 거부나 장애 뒤에 같은 호출을 되풀이하지 않는다 | eval(`fault`) |
| 사용 | plugin이 있을 때와 없을 때 차이가 있다 | eval(기준선 Δ) |
| 설명 | `CAPABILITY.md` 일곱 절이 있고 안내 문장이 남아 있지 않다 | 검사기 |
| 설명 | 네 요소, 판단 위치, 결정의 이유, 실패를 포함한 확인 결과, 남은 한계가 내 말로 적혀 있다 | 강사 리뷰 |

## 5. 끝났다고 말할 수 있을 때

- [ ] 검사기에 "실패"가 없다
- [ ] eval 사례 네 종류가 있고 `run_eval.py`로 한 번 이상 돌렸다
- [ ] 처음 실패한 사례 하나를 고치고 다시 돌렸다(실패가 없었다면 실패하는 사례를 더 만들었다)
- [ ] `CAPABILITY.md`를 내 말로 썼다
- [ ] 써 보는 세션에서 내 능력을 실제로 한 번 끝까지 썼다

**더 해 보고 싶다면** (선택)

- `--runs 3`으로 반복해 흔들림을 본다. 바꾸기 전에 무엇이 좋아질지 먼저 적고(노트북 07의 사전 등록), 바꾼 뒤 비교한다.
- 판단 지점을 판단 모델(Jev)로 만든다. `cap_lab/server/gate.py`(판정과 문턱값, fail-closed)와 `cap_lab/decisions.py`(질문 모양 `Noul`, `Choice`, `Score`)가 예시다. Decision API 키가 필요하다.
- 서버가 사용자에게 직접 묻게(elicitation) 만든다. `cap_lab/server/server.py:235-246`이 예시다. 대화형 Claude Code는 대화 상자를 띄운다(Part 1에서 확인). `claude plugin eval`에서 어떻게 되는지는 확인하지 않았다.

**참고 자료:** 실제로 배포되는 큰 MCP 서버(Ouroboros, 도구 36개)를 뜯어본 `reference/ouroboros-mcp-architecture.md`가 있습니다. 14절이 "작은 서버에 가져올 것과 가져오지 않을 것"입니다.

## 6. 막혔을 때

| 증상 | 먼저 볼 것 |
|---|---|
| 검사기의 "서버 기동과 tools/list"가 실패 | `.mcp.json`의 경로. plugin을 `challenge/work/` 밖으로 옮기면 `${CLAUDE_PLUGIN_ROOT}/../../../../../.venv/bin/python`이 이 저장소의 파이썬을 가리키지 못한다 |
| "stdout 오염" | 서버 코드의 print. 진단은 `print(..., file=sys.stderr)` |
| eval의 "도구 이름" 실패 | 판정기의 `tool:`이 `mcp__plugin_<plugin>_<서버>__<도구>` 꼴인지. plugin 이름을 바꿨다면 판정기도 바꾼다 |
| eval에서 내 서버가 안 쓰인다 | `run_eval.py`로 돌렸는지. `claude plugin eval`을 직접 치면 기본이 가짜 서버(`--mocks record`)다 |
| 써 보는 세션에서 Skill이 안 불린다 | description이 내 말과 맞는가. `/context`나 `show_session.py` 표에서 Skill 줄을 본다 |
| 써 보는 세션에서 도구가 안 보인다 | `/mcp`에 `plugin:<plugin>:<서버>`가 `connected`인지 |
