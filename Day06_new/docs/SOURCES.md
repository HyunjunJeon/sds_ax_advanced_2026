# Day06_new 근거 대장 (저자용, 확인일 2026-11-05)

수업 자료에 나오는 외부 사실은 모두 아래 대장 중 하나에서 원문 대조 수준과 함께 확인한 것이다. 대장에 없는 사실은 수업 자료에 쓰지 않는다.

| 대장 | 범위 | 확인 방법 |
|---|---|---|
| [sources/web.md](sources/web.md) | 웹 글 7종: Claude AI-native SDLC 플레이북(영문·한국어), Anthropic 장기 실행 하네스 글 2편, OpenAI Harness engineering, Böckeler(martinfowler.com), Claude Code 공식 문서, Raschka | 원문을 내려받아 인용문을 문자열로 대조. OpenAI 글만 Wayback 사본으로 대조 |
| [sources/github.md](sources/github.md) | 저장소 15개(superpowers, spec-kit, HumanLayer ACE, better-harness, AHE, learn-harness-engineering, mini-coding-agent, learn-claude-code, agentic-coding-design-patterns, ADLC-harness, anti-samcheonpo, harness-map, ramo-harness, revfactory/harness, claude-quickstarts) | 기본 브랜치 HEAD를 SHA로 고정하고 `path:line` 인용 |
| `sources/part4_claims.md` (git 제외, 강사용) | Part 4 연습 정답지: learn-harness-engineering의 Pi·DeepSeek 분석 주장 12개를 `Day06/` 스냅샷으로 판정 | 진입점에서 호출을 따라간 소스 읽기. 하네스는 실행하지 않음 |
| 이 파일 아래 "직접 읽은 코드" | `vendor/` 두 스냅샷의 줄 인용 | 저자가 스냅샷 파일을 직접 읽음 |

## 대장에서 나온 주의 (수업 자료에 반영함)

- 플레이북의 산출물 사슬은 intent.md → spec.md → plan.md → diff와 테스트 → 검토 결과가 달린 PR → 사고 기록이고, Maintain이 다시 intent.md를 쓴다. `REVIEW.md`는 사슬의 산출물이 아니라 Deploy 단계의 검토 정책 파일이다(web.md 1절 항목 3·5).
- 플레이북 한국어판은 부분 번역이다. 측정 지표 블록은 한국어판에도 영어 그대로다. 수업 자료의 지표 한국어 문장은 저자 번역이라고 밝힌다(web.md 1절 주의).
- 플레이북은 plan mode에서 계획 승인 전 편집이 안 된다고 쓰지만, 공식 문서는 bypass 권한이 있는 대화형 터미널 세션을 예외로 둔다(web.md 6(b)). Hook 결과를 플레이북은 allow/ask/block으로, 공식 문서는 allow/deny/ask/defer로 쓴다(web.md 6(c)).
- superpowers의 "2–5분 태스크"는 README(`README.md:314`)에만 남아 있고 현재 `skills/writing-plans/SKILL.md`에는 시간 기준이 없다. 태스크 크기 기준은 "자기 테스트 주기를 가진 가장 작은 단위"다(github.md 1절).
- spec-kit의 tasks 템플릿은 테스트를 선택으로 둔다(`templates/tasks-template.md:12`, github.md 2절).
- HumanLayer 글이 링크한 프롬프트 세 개는 2026-10-22에 삭제되었다. 원문은 삭제 전 커밋으로만 읽을 수 있다(github.md 3절).
- learn-claude-code는 장 번호를 바꿨다(옛 s03 TodoWrite → 새 s05 등, github.md 8절). 수업 자료는 새 번호를 쓴다.
- learn-harness-engineering은 "다섯 하위 시스템"을 두 가지로 쓴다: 강의 L02는 instructions·state·verification·scope·lifecycle, 하네스 분해 문서는 instructions·tools·environment·state·feedback(github.md 6절).
- `/insights`는 공식 내장 명령이고 토큰을 쓴다. 보고서는 `~/.claude/usage-data/report.html`(web.md 6(a)).
- transcript 폴더 이름은 작업 디렉터리 경로에서, auto memory 폴더 이름은 git 저장소에서 정해진다(web.md 6(d)(e)).
- Claude Code는 시작 폴더와 그 위에 CLAUDE.md가 없을 때만 AGENTS.md를 읽는다(web.md 6(d)).
- OpenAI 글의 1,500 PR은 "엔지니어 3명"과 같은 문장에 있다. 7명은 현재 인원이다(web.md 4절 주의).
- Anthropic 글의 $9 대 $200은 V1(Opus 4.5) 실험이고 $124.70은 V2(Opus 4.6) 실험이다. 한 표에 섞지 않는다(web.md 3절 주의).

## 직접 읽은 코드 (vendor/, 2026-11-05)

### vendor/autonomous-coding (claude-quickstarts `8ef47d71`)

| 사실 | 근거 | 수준 |
|---|---|---|
| 바깥 루프는 반복마다 새 클라이언트(새 문맥)를 만든다 | `agent.py:146`, `agent.py:158-159` | 실행 경로에서 확인(진입 `autonomous_agent_demo.py` → `run_autonomous_agent`) |
| 첫 반복만 초기화 프롬프트, 이후는 코딩 프롬프트. 첫 반복 여부는 `feature_list.json`이 있는지로 정한다 | `agent.py:124-126`, `agent.py:161-166` | 실행 경로에서 확인 |
| 루프는 `max_iterations`에서만 멈춘다. 모든 기능이 통과해도 하네스 코드는 멈추지 않는다 | `agent.py:149-153` (통과 수는 출력만 한다: `agent.py:174-175`, `progress.py:12-36`) | 실행 경로에서 확인 |
| `passes` 집계는 `feature_list.json`에 적힌 값을 그대로 센다(다시 검사하지 않는다) | `progress.py:22-34` | 실행 경로에서 확인 |
| "passes만 바꿔라", "기능을 지우거나 고치지 마라"는 프롬프트 지시다 | `prompts/initializer_prompt.md:53-57`, `prompts/coding_prompt.md:106-126` | 코드에 정의만 확인(프롬프트 파일) |
| 그 지시를 코드로 강제하는 장치는 없다. 등록된 hook은 Bash 명령 허용 목록 하나다 | `client.py:113-117`, `security.py:297` | 실행 경로에서 확인(hook 등록) / `feature_list.json` 편집을 막는 장치는 찾지 못함 |
| 새 작업 전에 이미 통과한 기능 1~2개를 다시 검사하라는 지시 | `prompts/coding_prompt.md:46-59` | 코드에 정의만 확인(프롬프트) |
| 진행 기록 파일 `claude-progress.txt`를 세션 끝에 쓰라는 지시 | `prompts/initializer_prompt.md:93-101`, `prompts/coding_prompt.md:142-158` | 코드에 정의만 확인(프롬프트) |
| README의 허용 명령 목록(`ls`…`pkill`)에는 `cp`, `mkdir`, `chmod`, `pwd`, `init.sh`가 없지만 코드의 `ALLOWED_COMMANDS`에는 있다 | `README.md:73-76`, `security.py:15-41` | 문서와 코드가 다름(코드를 따른다) |
| 권한 설정은 sandbox 사용, 편집 자동 승인, 프로젝트 폴더 안 파일 도구 허용, `Bash(*)` 허용 후 hook으로 거른다 | `client.py:67-85` | 코드에 정의만 확인 |
| README의 License 절은 "Internal Anthropic use."다(저장소는 MIT) | `README.md:161-163` | 문서 |

### vendor/mini-coding-agent (`717cae4f`)

| 사실 | 근거 | 수준 |
|---|---|---|
| 요청 하나의 루프: `max_steps`(기본 6)와 형식 오류 재시도 한도 안에서 모델 호출 → 도구 실행 → 기록을 반복하고, 모델이 최종 답을 내면 끝난다 | `mini_coding_agent.py:445-491`, 기본값 `:233`, `:962` | 실행 경로에서 확인 |
| 완료는 모델의 최종 답(`<final>`)뿐이다. 하네스가 결과를 검사하는 단계는 없다 | `mini_coding_agent.py:481-484` | 실행 경로에서 확인 |
| 한도에 걸리면 "멈췄다"는 문장을 답으로 돌려준다(미해결 종료) | `mini_coding_agent.py:486-491` | 실행 경로에서 확인 |
| 도구 실행 관문 순서: 없는 도구 → 인자 검증 → 같은 호출 반복 거절 → 위험 도구 승인 → 실행과 출력 자르기 | `mini_coding_agent.py:496-515` | 실행 경로에서 확인 |
| 같은 도구·같은 인자가 직전 두 번 연속이면 거절한다 | `mini_coding_agent.py:517-522` | 실행 경로에서 확인 |
| 위험 도구는 `run_shell`, `write_file`, `patch_file`이다 | `mini_coding_agent.py:302-319` | 코드에 정의만 확인 |
| 승인 정책 ask/auto/never. auto는 임의 명령 실행과 파일 쓰기를 허용한다고 도움말이 적는다 | `mini_coding_agent.py:602-613`, `:956-961` | 실행 경로에서 확인 |
| 파일 도구는 작업 폴더 밖 경로를 거절한다. `run_shell`은 `shell=True`로 실행되고 경로 검사가 없다 | `mini_coding_agent.py:734-740`, `:796-810` | 실행 경로에서 확인 |
| 하위 에이전트는 읽기 전용, 승인 never, 깊이 1, 단계 3이 기본이다 | `mini_coding_agent.py:847-866` | 실행 경로에서 확인 |
| 작업 폴더 정보(git 상태, 최근 커밋, AGENTS.md·README.md 등 앞부분)를 미리 모은다 | `mini_coding_agent.py:75-140`, `DOC_NAMES` `:14` | 실행 경로에서 확인 |
| 프롬프트 = 고정 앞부분(규칙·도구·예시·작업 폴더) + 메모리 + 대화 기록 + 현재 요청 | `mini_coding_agent.py:333-374`, `:422-428` | 실행 경로에서 확인 |
| 오래된 기록은 짧게 자르고 같은 파일 읽기는 한 번만 남긴다 | `mini_coding_agent.py:390-417` | 실행 경로에서 확인 |
| 세션은 `.mini-coding-agent/sessions/<id>.json`에 기록마다 저장되고 `--resume`으로 이어 간다 | `mini_coding_agent.py:146-164`, `:433-435`, `:912-934`, `:955` | 실행 경로에서 확인 |
