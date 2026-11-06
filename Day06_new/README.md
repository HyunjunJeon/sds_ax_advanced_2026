# Day06_new — AI SDLC & Agent Harness

AI에게 코드를 맡기는 개발을 **AI SDLC**(Software Development Life Cycle)의 단계와 산출물로 다시 보고,
그 단계를 믿을 만하게 만드는 **Agent Harness**를 여섯 책임(지침·도구·실행 제어·상태·검증·기록)으로 읽습니다.
마지막에는 **나의 AI SDLC**를 진단하고 설계합니다. 노트북 없이 Claude Code 두 세션으로 실습합니다.

## 이 Day가 다루는 것

각 Part의 주된 사례는 **내가 쓰는 Claude Code의 기능**입니다. 권한 모드·hook·Skill·하위 에이전트·되감기·plan mode가 하네스의 어느 책임을 맡는지, 내 세션 기록에서 직접 확인합니다.

- `vendor/mini-coding-agent`는 Part 2에서 짧게 보는 **대조군**입니다. 같은 책임이 작은 코드에서는 어떻게 생겼는지 비교합니다.
- Part 4의 사례는 오픈소스 plugin **ralph-loop**(`vendor/ralph-loop`, Apache-2.0)입니다. 설치하거나 실행하지 않고 파일만 읽습니다.

## 오늘 손에 남는 것

`Day06_new/use_cc/notes/MY_AI_SDLC.md` 하나입니다. Part마다 한 칸씩 채우고, 마지막 실습에서 완성합니다.

## 시간표 (360분, 휴식 제외)

| 구간 | 분 | 개념 | 시연 | 미션 | 해설 | 카드 |
|---|---|---|---|---|---|---|
| 준비 | 10 | 0 | 5 | 5 | 0 | `use_cc/MISSION_GUIDE.md`, `use_cc/part1/mission.md`의 "준비" |
| Part 1. Coding Agent와 AI SDLC(Software Development Life Cycle) | 40 | 12 | 5 | 18 | 5 | `use_cc/part1/` |
| Part 2. What is Agent Harness | 70 | 17 | 6 | 39 | 8 | `use_cc/part2/` |
| Part 3. Evidence·Checkpoint·Plan | 70 | 15 | 10 | 37 | 8 | `use_cc/part3/` |
| Part 4. 오픈소스 Agent Harness 구조 분석 | 45 | 8 | 5 | 25 | 7 | `use_cc/part4/` |
| Part 5. 계획 구체화와 실행 구조 | 60 | 12 | 6 | 35 | 7 | `use_cc/part5/` |
| 실습: 개인 AI SDLC 설계 | 65 | 5 | 0 | 55 | 5 | `use_cc/lab/` |
| 합계 | 360 | 69 | 37 | 214 | 40 | |

Part마다 `concept.md`(개념 정리)와 `mission.md`(미션 카드)가 있습니다. 실습은 `lab/mission.md`입니다.

## 준비물

- Claude Code (계정 로그인), git, Python 3, uv (저장소 루트에서 `uv sync --locked`를 한 번 해 둡니다)
- 터미널 두 개. 실습 2단계에서는 Claude Code가 아닌 **일반 터미널** 하나가 더 필요합니다
- API 키 설정은 필요 없습니다. 이 Day의 도구는 모델을 부르지 않습니다

## 시작

조교 세션(터미널 1)을 엽니다.

```bash
cd Day06_new/use_cc
claude
```

1. 처음 열 때 "External imports"는 **"Yes, allow external imports"** 를 고릅니다. 위쪽 폴더의 `CLAUDE.md`가 `@AGENTS.md`로 저장소의 `AGENTS.md`를 가져오기 때문입니다(바깥 경로를 처음 만나면 승인 대화상자가 뜹니다, I4).
2. 양식을 복사합니다. 조교 세션에서 `!mkdir -p notes && cp lab/MY_AI_SDLC.md notes/MY_AI_SDLC.md`
3. 조교 세션에서 **"첫 번째 실습 시작"** 이라고 말합니다. 명령은 필요 없습니다. "파트 2", "마지막 실습"처럼 말해도 해당 카드가 열립니다.

실험 대상 세션(터미널 2)은 저장소 **밖**의 실험 폴더에서 엽니다. 카드가 폴더 이름을 알려 줍니다.

```bash
cd ~/day06-p1 && claude --permission-mode acceptEdits
```

시작 모드는 `--permission-mode`로 정하고(대장 C10), `acceptEdits`는 파일 편집과 몇 가지 파일 명령만 묻지 않습니다(C6). 모든 학생이 같은 모드에서 시작하므로 승인 화면이 뜨는 지점을 비교할 수 있습니다. 시작 모드만으로는 모델의 판단이 정해지지 않는다는 점은 auto 모드(C8)를 설명할 때 다시 나옵니다.

## 두 세션

| 터미널 | 여는 곳 | 하는 일 |
|---|---|---|
| 1. 조교 세션 | `Day06_new/use_cc` | 카드를 같이 보고, 도구를 실행하고, 읽을 곳을 가리킵니다. 셸 명령은 `!`를 붙여 칩니다 |
| 2. 실험 대상 세션 | 저장소 **밖**의 실험 폴더(`~/day06-p1`, `~/day06-p2a`~`p2d`, `~/day06-p3`, `~/day06-p5`, `~/day06-lab`) | 실험 폴더의 작업 규칙만 가지고 일합니다 |

실험 폴더는 `uv run python setup_sandbox.py <저장소 밖 경로>`로 만듭니다. 저장소 안 경로는 거절합니다.

## 비용

과금되는 것은 **내 Claude Code 계정**뿐입니다. 행동별 규모는 각 카드의 "이 미션의 비용" 표에 있습니다. 아래는 카드의 값을 옮긴 요약입니다. "예고"는 저자 실측 전이고, "저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형)"은 저자가 `-p` 헤드리스로 1회 돌린 값입니다. "저자 실측 (2026-11-05)"는 이전 판(240분 구성)에서 같은 방식으로 잰 값입니다. 대화형은 승인 화면 때문에 더 걸립니다.

| 구간 | 가장 큰 행동 | 규모 | 구분 |
|---|---|---|---|
| Part 1 | M1-2 실험 폴더 하나 (실험 1) | 모델 호출 6회, 0.111달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 1 | 안내 문서의 말 시작 3가지 | 각 2회, 세 가지 합 0.529달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 2 | M2-4 기준·a·b·c·d 다섯 폴더 | 3·1·3·3·10회, 합 0.31달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 3 | M3-3 "이어서 작업해 줘" (실험 3) | 7회, 0.111달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 3 | 실험 6 (Gate 막힘) | 12회, 0.163달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 3 | M3-6 깨뜨리기 | 3회, 약 0.18달러 | 저자 실측 (2026-11-05, 이전 판) |
| Part 3 | M3-5 되감기 탐침 | 3~6회, 약 0.05~0.15달러 | 예고 |
| Part 4 | 조교 세션의 질문과 파일 읽기 | 차례 약 8~15회. ralph-loop은 실행하지 않음 | 예고 |
| Part 5 | M5-7 계획 B 구현 + 검토자 (실험 8) | 13회 (구현 7회 0.1195달러, 검토 6회 0.2286달러), 합 0.348달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 5 | 실험 9 / 실험 10 | 2회, 0.042달러 / 7회, 0.1255달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |
| Part 5 | M5-3 계획 A / M5-4 계획 B | 3회, 약 0.11달러 / 3회, 약 0.16달러 | 저자 실측 (2026-11-05, 이전 판) |
| 실습 | 3단계 실험 11 (hook 예 / SessionStart) | 8회, 0.131달러 / 1회, 0.029달러 | 저자 실측 1회 (2026-11-06, Sonnet 5.5, 비대화형) |

조교 세션은 구간마다 차례 약 5~25회가 별도로 듭니다(예고). `/insights`는 선택이며 최근 세션을 모델이 읽어 토큰을 씁니다. `/context all`, `/usage` 같은 확인 명령이 모델을 부르는지는 저자가 확인하지 않았습니다. 진단·검사 도구 4종은 모델을 부르지 않습니다.

## 내 세션 기록을 다룰 때 (실습)

- 조교 세션에는 **건수와 번호만** 들어갑니다. 진단 도구의 기본 출력에는 대화 내용, 폴더 이름, 파일 경로가 없습니다.
- 내용을 보는 `--show`, `--reveal`은 **Claude Code 밖의 일반 터미널**에서만 칩니다. Claude Code 안에서는 도구가 거절합니다.
- 업무 코드·고객 정보·대화 원문을 조교에게 붙여 넣지 않습니다. 내 말로 요약합니다.
- **회사 정책이 이 수업의 규칙보다 우선합니다.** 세션 기록을 쓸 수 없으면 실험 폴더 세션으로 같은 실습을 합니다.

## 폴더 지도

| 경로 | 무엇 |
|---|---|
| `use_cc/` | 조교 규칙(`CLAUDE.md`), 미션 안내(`MISSION_GUIDE.md`), 실험 폴더 원본 |
| `use_cc/part1/` ~ `part5/` | Part별 `concept.md`와 `mission.md` |
| `use_cc/lab/` | 마지막 실습 카드, 양식 `MY_AI_SDLC.md`, hook 시작 템플릿 |
| `use_cc/concepts/` | 개념 문서(Claude Code 하네스 지도) |
| `use_cc/tools/` | `check_evidence.py`, `show_session.py`, `diagnose_sessions.py`, `harness_inventory.py` |
| `use_cc/setup_sandbox.py` | 저장소 밖 실험 폴더를 만듭니다 |
| `vendor/` | 읽기 자료: `mini-coding-agent`(Part 2 대조군), `autonomous-coding`(Part 3 대조군), `ralph-loop`(Part 4 사례, Apache-2.0). 실행하지 않습니다 |
| `docs/` | 근거 대장: 개념 문서의 Claude Code 사실과 외부 자료 인용을 원문과 대조해 둔 곳 |

Part 4는 `vendor/ralph-loop`와 `Day06/`의 하네스 스냅샷(`pi`, `deepseek-harness`, `ouroboros`)을 읽기만 합니다.
