# Day06_new 설계 기록 (저자용)

수강생용 문서가 아니다. 설계 결정, 제작 계획, 검증 기록, 남은 일을 적는다. 코드와 어긋나면 코드를 따른다.

## 1. 저자 결정 (2026-11-05)

| 결정 | 내용 |
|---|---|
| 주제 | AI SDLC & Agent Harness. Part 1 Coding Agent와 AI SDLC, Part 2 What is Agent Harness, Part 3 Evidence·Checkpoint·Plan, Part 4 오픈소스 Agent Harness 구조 분석, Part 5 계획 구체화와 실행 구조, 실습 개인 AI SDLC 설계 |
| 형식 | `Day06_new/` + `use_cc` 미션 카드(Day04_new·Day05_new의 use_cc 형식). `Day06/`은 그대로 둔다 |
| 외부 스냅샷 | `mini-coding-agent`, `autonomous-coding` 두 개만. 나머지는 링크와 근거 대장의 고정 커밋 인용 |
| 세션 기록 | 수강생 자기 업무 세션까지 허용 |
| 시간 | 4시간(휴식 제외) |

승인된 제작 전제: Part 4는 `Day06/` 스냅샷을 경로로 참조, 실행 사례는 Day06 이론 강의의 회의실 예약 R1~R7, 개념은 Part별 `concept.md` + git 제외 강사 노트(슬라이드 없음), 외부 plugin은 필수 설치에서 뺌, 업무 세션 진단은 모델을 부르지 않는 로컬 도구(기본 출력에 내용·이름 없음).

## 2. 제작 계획 (승인본, 대화에서 옮김)

```
 [A sources] [B vendor] [C toy+sandbox] [D diag tools]
      |           |            |              |
      |           +------+-----+------+-------+
      |                  v            v
      |            [E day-docs]   [F tutor]
      |                  |            |
      +--------+---------+-----+------+----------------+
      v        v         v     v      v                v
    [G1]     [G2]      [G3]  [G4]   [G5]            [H lab]
      +--------+---------+--+--+------+----------------+
                            v
                      [I root AGENTS]
                            v
                       [J audit]  (static, no model)
                            v
                       [K live]   (paid, separate approval)
                            v
                       [L final]  (update cost tables + re-audit)
```

| 노드 | 상태 | 산출물 |
|---|---|---|
| A 근거 대장 | 완료 | `docs/sources/web.md`, `github.md`, `part4_claims.md`(git 제외), `docs/SOURCES.md` |
| B 스냅샷 | 완료(저자 결정: 그대로 유지, 4절) | `vendor/`, `vendor/SNAPSHOTS.md` |
| C 예제와 실험 폴더 | 완료 | `use_cc/sandbox_template/`, `use_cc/setup_sandbox.py`, `use_cc/tools/check_evidence.py` |
| D 진단 도구 | 완료 | `use_cc/tools/diagnose_sessions.py`, `harness_inventory.py`, `show_session.py` |
| E Day 문서 | 완료 | `AGENTS.md`, `CLAUDE.md`, `README.md`, 이 파일 |
| F 조교 | 완료 | `use_cc/CLAUDE.md`, `use_cc/.claude/skills/mission/SKILL.md` |
| G1~G5, H | 완료. 실험 대상 세션 비용은 실측, 조교 세션 비용은 예고 | `use_cc/part1~5/`, `use_cc/lab/` |
| I 루트 AGENTS.md | 이 브랜치에서 반영 | 3장 실행 규칙, 6장 비용, 8장 표 |
| J 정적 감사 | 5절 | |
| K 유료 실측 | 완료(2026-11-05, 1회씩) | 5절. 기록은 `use_cc/part3/recordings/`, `use_cc/part5/recordings/`(git 제외) |
| L 마무리 | 완료 | 실측 반영, 진단 도구 수정, 감사 재실행 |

## 3. 설계의 핵심

- **하루를 꿰는 산출물 하나**: `notes/MY_AI_SDLC.md` §1~§9. Part마다 한 칸, 실습에서 완성. 4시간 안에 실습을 끝내려고 Part 미션을 실습의 재료로 만들었다.
- **틀은 여섯 책임 하나**: 다른 자료의 틀은 Part 2 대응표로만 연결(`use_cc/part2/concept.md` 2절). 대응은 이 수업의 해석이라고 밝혔다.
- **Part 3 실험 폴더의 결함 설계**: "이전 세션"이 R3를 거짓으로 완료 표시하고(`verified_at`은 있지만 검사 실패), R1·R2·R7은 다른 코드 커밋에서 확인한 오래된 증거, R5는 미주장 통과. R4 검사는 사용자 A·B를 함께 쓴다. 겹침을 "내 예약"에서만 찾으면 실패하고, 모든 사용자의 예약에서 찾으면 R3(공용 조회)를 고치지 않아도 통과한다(저자가 2026-11-05 직접 구현해 확인. 처음 설계 문서에 "R3 없이 통과할 수 없다"고 쓴 것은 틀렸다). 커밋 작성자·시각을 고정해 해시가 모든 기계에서 같다.
- **완료 Gate의 "현재 산출물" = 코드 리비전**: 기록 파일(`feature_list.json`, `progress.md`, `CLAUDE.md`, `.claude/`, `.gitignore`, `plans/`)만 바뀐 커밋이나 그 파일들의 미커밋 변경은 증거를 낡게 하지 않는다. 그래야 "코드를 커밋 → `verified_at` 기록 → 기록 커밋" 순서가 성립한다.
- **업무 세션 보안**: 진단 도구 두 개는 기본 출력에 건수·번호만. 내용·이름 옵션은 `CLAUDECODE` 환경 변수가 있으면 거절(Claude Code 안의 `!` 실행 출력은 모델로 전송되므로). MCP 도구 이름도 기본으로 가린다. `harness_inventory.py`는 설정 값과 환경 변수 이름을 어떤 옵션으로도 출력하지 않는다(텔레메트리 변수 이름 네 개만 예외).
- **진단 신호 정의의 판단**(2.1.318 실제 기록으로 조정):
  - 도구 거절은 "[Request interrupted by user for tool use]"를 함께 남기므로 그 표식은 "중단"으로 세지 않는다.
  - 문서(.md 등) 수정은 "수정 뒤 검사 없음"에서 뺀다(잡음이 컸다).
  - "검사 파일 수정"은 Edit/MultiEdit만 센다. Write는 새 파일 생성과 구별할 수 없다.

## 4. 결정 대기 (저자)

1. ~~`vendor/autonomous-coding`의 공개 여부~~ → **2026-11-05 저자 결정: 그대로 유지**(저장소 MIT 기준, `vendor/SNAPSHOTS.md`에 차이 기록). 아래는 당시 선택지 기록이다. 폴더 README의 License 절이 "Internal Anthropic use."(`vendor/autonomous-coding/README.md:161-163`)이고 저장소 라이선스는 MIT다. 선택지: (a) 저장소 MIT 기준으로 유지하고 `vendor/SNAPSHOTS.md`에 차이를 적어 둔다(지금 상태) (b) 사본을 지우고 고정 커밋 링크로만 읽게 한다. (b)면 Part 3 카드·개념·`docs/SOURCES.md`의 `vendor/autonomous-coding/` 경로를 `https://github.com/anthropics/claude-quickstarts/blob/8ef47d71.../autonomous-coding/...` 형식으로 바꾼다. 줄 번호는 그대로다.
2. ~~유료 실측(K)~~ → 2026-11-05 진행, 5절.

## 5. 검증 기록

### 정적 (모델 호출 없음)

- 시험: `use_cc/tests/`(git 제외) — 결과는 감사 노드에서 기록.
- 실제 2.1.318 기록으로 두 진단 도구 실행: 강사 기계 최근 14일 세션 24개, 대화 내용 출력 없음 확인.
- 실험 폴더를 두 번 만들어 해시가 같은 것 확인. 처음 `check_evidence.py` 판정이 설계와 같은 것 확인.
- Part 4 정답지의 핵심 인용(`cordis.patch.yml:472-475`, base 패치 invariant 0건, sdk-minimal invariant 행, README `:32`, `AgentLoop extends Service`, pi에서 두 이벤트 이름 0건)을 저자가 스냅샷에서 다시 확인.

### 유료 실측 K (2026-11-05)

조건: Claude Code 2.1.318, `claude -p`, `--model claude-sonnet-5-5`, `--setting-sources project,local`(사용자 설정 제외), `--permission-mode acceptEdits`, Bash는 git·python3·읽기 명령만 `--allowedTools`로 허용, 깨끗한 환경 변수(`env -i`). 실험 폴더는 scratchpad(저장소 밖). 각 1회.

| 실행 | 모델 호출 | 시간 | 비용 | 관찰 |
|---|---|---|---|---|
| 연결 확인 | 1 | 1.5초 | $0.02 | — |
| Part 3 "이어서 작업해 줘" | 8 | 31초 | $0.13 | 시작 순서 준수, R3 거짓 주장 발견·수정, `verified_at` = 코드 커밋, R1·R2·R7 오래된 증거 미갱신 → Gate 불통과 유지. 권한 거절 2건(`$(...)`가 든 명령, `sed -i`) |
| Part 3 깨뜨리기(`--continue`, `--settings`로 hook 적용) | 3 | 20초 | $0.18 | hook이 Edit를 막음. 같은 차례의 Bash가 실행되어 사실이 아닌 기록 커밋 → 스스로 revert |
| Part 5 계획 A(`--permission-mode plan`) | 3 | 29초 | $0.11 | 검사 실행, R3 범위 밖 보고. 계획 파일 `~/.claude/plans/<이름>.md` 생성 확인 |
| Part 5 계획 B | 3 | 50초 | $0.16 | 요청한 칸 모두 채움. 106줄(계획 A 34줄) |
| 합계 | 18 | 약 2분 | 약 $0.60 | 처음 예고(30~75회)보다 훨씬 적었다 |

실측으로 드러나 고친 것:
- `diagnose_sessions.py`가 hook에 막힌 Edit를 "검사 파일 수정"으로 셌다 → 오류로 끝난 수정은 제외. "hook이 막음" 신호를 새로 추가(결함별 반증 시험 2개).
- "R4는 R3 없이 통과할 수 없다"는 설계 문장이 틀렸다 → 직접 구현해 확인하고 DESIGN·강사 노트·카드 문구를 고쳤다.
- 비대화형에서는 신뢰하지 않은 폴더의 프로젝트 허용 규칙이 무시된다(경고). 깨뜨리기는 `--settings`로 프로젝트 설정을 넣어 hook을 적용했다.
- 카드 명령 `show_session.py --latest`, `diagnose_sessions.py --project`를 실제 기록으로 확인했다.

### 아직 확인하지 않은 것

- 대화형 화면: plan mode 승인 화면의 선택지 이름, 폴더 신뢰 뒤 hook과 허용 규칙의 동작(비대화형 + `--settings`로만 확인).
- 조교 세션의 호출 수(카드에 "예고").
- `/insights`의 비용 규모, `/context`·`/memory`가 모델을 부르는지.
- WSL에서의 동작(macOS에서만 확인). 실험 폴더의 검사는 Python 3.9에서 돌아가는 것을 확인했다.

## 6. 저자가 직접 할 Day 간 정리 (이 브랜치에서 하지 않음)

- `Day06/HARNESSES.md`와 `Day06/AGENTS.md`는 오늘 삭제된 `gajae-code`를 아직 설명한다(`77faa440`).
- 루트 `AGENTS.md`의 Day06 설명("하네스 4종")도 같은 이유로 맞지 않는다.
