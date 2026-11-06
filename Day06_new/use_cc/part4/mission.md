# M4. 남의 plugin의 확장점 지도를 그리고 Day06 스냅샷과 대조한다 (Part 4 · 미션 25분)

> **핵심 질문: 이 plugin은 Claude Code의 어느 확장점에 붙어 있고, 여섯 책임 중 무엇을 Claude Code에 맡기고 무엇을 비워 두었는가?**
>
> 먼저 읽을 곳: `part4/concept.md` 1~2절(확장점, 신뢰 경계).
> 이 미션이 끝나면 `notes/MY_AI_SDLC.md`의 §4a(확장점 지도), §4b(대조), §4c(가져올 설계)가 채워진다.

터미널은 하나다. `Day06_new/use_cc`의 조교 세션이고 셸 명령 앞에 `!`를 붙인다. 실험 폴더와 실험 대상 세션은 이 미션에 없다.

## 이 미션의 비용

모든 값은 **예고 (저자 실측 전)** 이다.

| 무엇 | 규모 | 누구의 비용 |
|---|---|---|
| 조교 세션 (M4-1~M4-4의 질문과 파일 읽기) | 차례 약 8~15회 (예고 (저자 실측 전)). 파일을 열 때마다 늘어난다 | 내 Claude Code 계정 |
| `harness_inventory.py` | 모델을 부르지 않는다 | 없음 |

**ralph-loop은 설치하지도 실행하지도 않는다.** 반복 루프라 비용이 커질 수 있기 때문이다(C16). 이 미션은 `Day06_new/vendor/ralph-loop`의 파일을 읽기만 한다. 사본의 출처는 `anthropics/claude-plugins-official` 커밋 `1aa4a4b`이다.

## 규칙

- 읽는 곳은 `Day06_new/vendor/ralph-loop`와 `Day06/pi`, `Day06/deepseek-harness`, `Day06/ouroboros`다. 모두 읽기 전용이다. 경로는 `파일:줄`로 적는다.
- 그 폴더 안의 지시문(README, CLAUDE.md, command 본문)은 분석 대상이지 따를 지시가 아니다.
- 조교는 파일을 함께 열어 주지만, **표의 칸은 내가 적는다.** "정답이 뭐예요?"에 조교는 칸을 먼저 채우지 않는다.

---

## M4-1. 먼저 예측하세요 (2분)

파일을 열기 전에 §4a 맨 위 "예측" 줄에 두 가지를 적는다.

1. ralph-loop은 Claude Code 확장점 몇 종에 붙는가? (skill, 하위 에이전트, command, hook, MCP 중에서 센다)
2. 여섯 책임(지침, 도구, 실행 제어, 상태, 검증, 기록) 중 빈 칸은 무엇인가?

## M4-2. `[따라하기]` 확장점 지도 (10분)

`Day06_new/vendor/ralph-loop` 안에서 아래를 차례로 열고, 찾은 것을 §4a에 `파일:줄`로 적는다. 조교에게 파일을 열어 달라고 해도 된다.

1. `.claude-plugin/plugin.json`: plugin의 이름과 버전이 여기 있다(T15).
2. `commands/` 아래 command 파일 3개: 각 파일 맨 위 설정 블록의 `description`과 `allowed-tools`를 본다(I13, T16). `allowed-tools`는 사전 승인이지 도구 제한이 아니다(I12). 어느 command가 어느 도구를 미리 승인하는지 적는다.
3. `hooks/hooks.json`: 어느 이벤트에 어떤 명령이 걸렸는지 적는다(T17, C13). 이 hook이 실제로 무엇을 하는지는 `hooks/stop-hook.sh`를 열어야 안다. hook은 세션이 끝나려 할 때 불리고, 반복 루프의 비용이 여기서 생긴다(C16).

다음으로 같은 폴더를 도구로 센다.

```text
!uv run python tools/harness_inventory.py ../vendor/ralph-loop
```

실제 출력의 plugin 부분은 다음과 같다(실행 환경에서 저자가 돌린 결과. 맨 위 표는 시작 폴더 기준이라 학생마다 다르므로 뺐다).

```text
plugin 폴더 모드 (이 폴더가 plugin 모양: .claude-plugin/plugin.json 또는 hooks/hooks.json)

| 구성 요소 | 개수 |
|---|---|
| command(commands/*.md) | 3개 |
| Skill(skills/*/SKILL.md) | 0개 |
| 하위 에이전트(agents/*.md) | 0개 |
| plugin hook(hooks/hooks.json) | Stop 1 |
| MCP 서버(.mcp.json) | 0개 |
| bin/ 실행 파일 | 0개 |
| 경고: 루트 CLAUDE.md(plugin은 지침으로 읽지 않음) | 0 |
```

- 도구가 0이라도 `.mcp.json` 파일이 있으면 직접 연다.
- 내가 직접 센 개수와 이 표를 맞춰 본다. 어긋나면 어느 쪽이 틀렸는지 적는다.
- 맨 위 표는 `vendor/ralph-loop`에서 Claude Code를 열었다고 가정하고 함께 실릴 것을 센다. 위쪽 폴더의 CLAUDE.md(`Day06_new`, 저장소 루트), 저장소의 Skill, 내 사용자 전역 설정이 섞이므로 사람마다 다르다. plugin 부분은 plugin 폴더 안의 구성요소만 센다. 내 출력의 plugin 부분만 §4a에 옮긴다.
- '그 밖의 hook' 줄은 내 사용자 전역 설정의 hook이다. ralph-loop의 hook은 Stop 하나뿐이다.
- 예측 1번과 비교해 센 확장점 수를 적는다.

## M4-3. 여섯 책임 (6분)

M4-2에서 연 파일로 여섯 책임 표를 직접 다시 만든다. §4a 표에 칸마다 `파일:줄`을 적는다. 조교에게 칸을 대신 채워 달라고 하지 않는다.

| 책임 | ralph-loop에서 이 책임을 하는 것 | 파일:줄 |
|---|---|---|
| 지침 | | |
| 도구 | | |
| 실행 제어 | | |
| 상태 | | |
| 검증 | | |
| 기록 | | |

두 가지를 찾아서 표 아래에 한 문장씩 쓴다.

- **빈 칸.** 근거를 못 찾은 칸은 무엇인가? "없다"고 쓰기 전에 폴더 전체에서 로그나 보고서 파일이 있는지 찾는다.
- **문자열 일치.** 검증 칸을 채울 때 `hooks/stop-hook.sh`에서 "끝났는가"를 어떻게 판정하는지 찾는다. 그 판정이 실행 증거를 보는가, 글자를 비교하는가? 실행해서 확인하는 쪽은 어떤 모습인지 한 문장으로 쓴다(I17).

## M4-4. `[내 것 만들기]` 대조 (7분)

여섯 책임 중 **하나**를 고른다(권장: 실행 제어 또는 상태). ralph-loop은 그 책임을 Claude Code의 hook에 기댄다. 아래 스냅샷 중 **하나**는 자기 루프를 직접 가진다. 같은 책임을 그 스냅샷이 어디서 하는지 찾는다.

| 스냅샷 | 읽는 곳 |
|---|---|
| pi | `../../Day06/pi` |
| deepseek-harness | `../../Day06/deepseek-harness` |
| ouroboros | `../../Day06/ouroboros` |

시작점은 `part4/concept.md`가 적어 둔 루프의 위치다. 조교에게 "이 폴더에서 루프가 어디서 도는지 찾아 줘"까지는 부탁해도 된다. 읽고 판단하는 것은 내가 한다.

**§4b에 적는다.** 고른 책임, 스냅샷 이름, ralph-loop의 `파일:줄`, 스냅샷의 `파일:줄`, 둘이 다른 점 한 문장. 근거가 없으면 "확인 필요"라고 쓴다.

**§4c에 적는다.** 오늘 본 것 중 **내 AI SDLC에 가져올 설계 하나**와 가져오지 **않을** 것 하나, 각각의 근거(`파일:줄`).

## 선택: 이전 판 주장 한 개 판정 (시간이 남을 때)

세 주장 중 하나를 골라 Day06 스냅샷의 설정과 코드로 확인한다. 문서와 일치하는지가 아니라 **실행 경로에서 확인되는지**를 본다. 판정은 일치 / 부분 일치 / 불일치 / 판정 불가 중에서 내가 적고, 근거 수준(실행 경로에서 확인 / 정의만 확인 / 문서에만 있음)을 함께 쓴다. 조교는 판정을 먼저 말하지 않는다.

출처: walkinglabs/learn-harness-engineering @ `a9342ff4`의 한국어판.

| # | 대상 | 주장 | 출처 |
|---|---|---|---|
| A | deepseek-harness | "모델 어댑터, 도구 레지스트리, session 로그, 심지어 agent 루프 자체까지 제품의 모든 부분이 plugin입니다." | `docs/ko/harness-designs/deepseek/index.md:5` |
| B | deepseek-harness | "Model-visible means logged. Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it." | `docs/ko/harness-designs/deepseek/index.md:53` |
| C | pi | "메모리를 추가하고 싶다면 `agent/pre-step`에 주입합니다. ... 모델 요청을 바꾸고 싶다면 `agent/request`에 hooks를 겁니다." | `docs/ko/harness-designs/pi/index.md:50` |

## 마치기 전에 확인

- [ ] §4a에 예측, 확장점 지도, 여섯 책임 표가 있고 칸마다 `파일:줄`이 있다
- [ ] `harness_inventory.py`의 plugin 부분을 옮기고 내가 센 개수와 맞춰 보았다
- [ ] 빈 칸과 문자열 일치 검증을 한 문장씩 썼다
- [ ] §4b에 책임 하나의 대조가, §4c에 가져올 설계 하나가 있다
- [ ] 읽은 모든 곳이 읽기 전용이었고 ralph-loop을 실행하지 않았다

## 확인 질문 (해설 시간에 내 말로 답합니다)

1. ralph-loop의 command `allowed-tools`를 "이 도구만 쓸 수 있다"로 읽으면 왜 틀리는가(I12)?
2. 켠 plugin의 hook은 모든 세션에서 돈다. 설치하기 전에 어느 파일을 읽어야 그것을 알 수 있나(T17)?
3. 완료 판정이 글자 비교일 때 생길 수 있는 문제는 무엇이고, 실행 증거로 바꾸려면 무엇이 필요한가(I17)?
4. 고른 책임에서 ralph-loop이 Claude Code에 맡긴 부분과 스냅샷이 직접 가진 부분을 각각 말해 보라. 직접 가질 때 치르는 비용은 무엇인가?
5. `harness_inventory.py`의 맨 위 표와 plugin 부분은 각각 무엇을 센 것인가? 둘을 섞어 읽으면 어떤 잘못이 생기나?
