# Day06_new — AI SDLC & Agent Harness

AI에게 코드를 맡기는 개발을 **AI SDLC**(Software Development Life Cycle)의 단계와 산출물로 다시 보고,
그 단계를 믿을 만하게 만드는 **Agent Harness**를 여섯 책임(지침·도구·실행 제어·상태·검증·기록)으로 읽습니다.
마지막에는 **나의 AI SDLC**를 진단하고 설계합니다. 노트북 없이 Claude Code 두 세션으로 실습합니다.

## 오늘 손에 남는 것

`Day06_new/use_cc/notes/MY_AI_SDLC.md` 하나입니다. Part마다 한 칸씩 채우고, 마지막 실습에서 완성합니다.

## 시간표 (4시간, 휴식 제외)

| 구간 | 분 | 구성 | 카드 |
|---|---|---|---|
| 준비 | 10 | 조교 세션 열기, 양식 복사 | `use_cc/part1/mission.md`의 "준비" |
| Part 1. Coding Agent와 AI SDLC | 35 | 개념 10 · 시연 5 · 미션 15 · 해설 5 | `use_cc/part1/` |
| Part 2. What is Agent Harness | 35 | 개념 8 · 시연 5 · 미션 17 · 해설 5 | `use_cc/part2/` |
| Part 3. Evidence·Checkpoint·Plan | 40 | 개념 8 · 시연 7 · 미션 20 · 해설 5 | `use_cc/part3/` |
| Part 4. 오픈소스 Agent Harness 구조 분석 | 30 | 개념 5 · 미션 20 · 해설 5 | `use_cc/part4/` |
| Part 5. 계획 구체화와 실행 구조 | 35 | 개념 8 · 미션 22 · 해설 5 | `use_cc/part5/` |
| 실습. 개인 AI SDLC 설계 | 55 | 진단 15 · 분류 10 · 설계 20 · 지표 10 | `use_cc/lab/` |

Part마다 `concept.md`(개념 정리)와 `mission.md`(미션 카드)가 있습니다.

## 준비물

- Claude Code (계정 로그인), git, Python 3, uv (저장소 루트에서 `uv sync --locked`를 한 번 해 둡니다)
- 터미널 두 개. 실습 2단계에서는 Claude Code가 아닌 **일반 터미널** 하나가 더 필요합니다
- API 키 설정은 필요 없습니다. 이 Day의 도구는 모델을 부르지 않습니다

## 시작

```bash
cd Day06_new/use_cc
claude
```

처음 열 때 "External imports"는 **"Yes, allow external imports"** 를 고릅니다. 그다음 조교 세션에서 `/mission part1`.

## 두 세션

| 터미널 | 여는 곳 | 하는 일 |
|---|---|---|
| 1. 조교 세션 | `Day06_new/use_cc` | 카드를 같이 보고, 도구를 실행하고, 읽을 곳을 가리킵니다. 셸 명령은 `!`를 붙여 칩니다 |
| 2. 실험 대상 세션 | 저장소 **밖**의 실험 폴더(`~/day06-p3`, `~/day06-p5`) | 실험 폴더의 작업 규칙만 가지고 일합니다 |

실험 폴더는 `uv run python setup_sandbox.py <저장소 밖 경로>`로 만듭니다. 저장소 안 경로는 거절합니다.

## 비용

과금되는 것은 **내 Claude Code 계정**뿐입니다. 행동별 규모는 각 카드의 "이 미션의 비용" 표에 있습니다. 표의 숫자가 "예고"이면 저자 실측 전입니다.

## 내 세션 기록을 다룰 때 (실습)

- 조교 세션에는 **건수와 번호만** 들어갑니다. 진단 도구의 기본 출력에는 대화 내용, 폴더 이름, 파일 경로가 없습니다.
- 내용을 보는 `--show`, `--reveal`은 **Claude Code 밖의 일반 터미널**에서만 칩니다. Claude Code 안에서는 도구가 거절합니다.
- 업무 코드·고객 정보·대화 원문을 조교에게 붙여 넣지 않습니다. 내 말로 요약합니다.
- **회사 정책이 이 수업의 규칙보다 우선합니다.** 세션 기록을 쓸 수 없으면 실험 폴더 세션으로 같은 실습을 합니다.

## 폴더 지도

| 경로 | 무엇 |
|---|---|
| `use_cc/` | 조교 규칙(`CLAUDE.md`), Part 카드, 도구, 실험 폴더 원본 |
| `use_cc/tools/` | `check_evidence.py`, `show_session.py`, `diagnose_sessions.py`, `harness_inventory.py` |
| `vendor/` | 읽기 자료: `mini-coding-agent`(Part 2), `autonomous-coding`(Part 3). 실행하지 않습니다 |
| `docs/` | 근거 대장(저자용) |

Part 4는 `Day06/`의 하네스 스냅샷(`pi`, `deepseek-harness`, `ouroboros`)을 읽기만 합니다.
