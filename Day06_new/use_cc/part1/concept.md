# Part 1. Coding Agent와 AI SDLC — 개념 정리

> **핵심 질문: AI가 코드를 쓰는 지금, 개발의 각 단계는 무엇을 남겨야 다음 단계가 이어 갈 수 있는가?**

이 문서는 강의(개념 10분)의 내용을 글로 옮긴 것이다. 영어 인용은 원문 그대로 두고, 근거는 `Day06_new/docs/SOURCES.md`의 대장 위치를 함께 적었다.

---

## 1. 코딩 에이전트는 "모델 + 하네스"다

같은 모델을 써도 결과가 다른 이유를 설명하는 가장 짧은 식이 있다.

> "Agent = Model + Harness" — Birgitta Böckeler, *Harness engineering for coding agent users* (martinfowler.com, 2026-04-02)

모델은 다음 행동을 고른다. 그 바깥의 모든 것, 즉 무엇을 읽게 할지, 어떤 도구를 줄지, 무엇을 막을지, 무엇을 기억시킬지,
끝났다는 말을 무엇으로 확인할지가 하네스(harness)다. 학습용 하네스를 단계별로 만드는 저장소 하나는 이렇게 나눈다.

> "The loop belongs to the agent. The mechanisms belong to the harness." — shareAI-lab/learn-claude-code `README.md:162`

여러분이 매일 쓰는 Claude Code도 하네스다. 모델은 Anthropic이 고르지만, 그 하네스의 상당 부분(CLAUDE.md, Skill, 권한, Hook, 기록)은 **여러분이 설정한다.**
오늘 하루는 "모델을 바꾸지 않고, 내가 바꿀 수 있는 쪽"을 다룬다.

## 2. AI SDLC: 단계마다 다음 단계가 읽을 산출물을 남긴다

Anthropic Applied AI 팀의 Louis Claxton이 쓴 *The AI-native SDLC playbook*(2026-08-21)은 소프트웨어 개발 수명 주기를 여섯 단계로 본다.

> "six non-linear stages (Plan, Design, Build, Test, Deploy, Maintain)"

그리고 이 플레이북 전체를 한 문장으로 줄이면 이것이다.

> "Every stage commits an artifact the next stage can read."

원문이 드는 산출물 사슬은 다음과 같다(`docs/sources/web.md` 1절 항목 3·5).

| 단계 | 끝날 때 버전 관리에 남기는 것 | 다음 단계가 그것을 읽어 하는 일 |
|---|---|---|
| Plan | `intent.md` — 요청한 사람의 말로 쓴 문제·결과·대상·제약 | 받아들여진 intent가 요구사항·설계를 시작시킨다 |
| Design | `spec.md` — 동작·구조·수용 기준 | 승인된 spec이 plan mode를 시작시킨다 |
| Build | `plan.md` — 바꿀 파일, 순서, 위험, 증명(테스트) | 계획대로 구현하고 diff와 테스트를 남긴다 |
| Test | diff와 그 테스트 | 검토 결과가 달린 PR이 된다 |
| Deploy | 검토 결과가 달린 PR | 병합이 배포 파이프라인을 시작시킨다 |
| Maintain | 사고 기록 | 운영 지표가 기준을 벗어나면 새 `intent.md`를 쓴다(루프가 닫힌다) |

> "An accepted intent.md triggers the requirements and design pass, an approved spec.md triggers plan mode, a merged PR triggers the pipeline, and a breached control band in production writes the next intent.md"

주의할 점 두 가지.

- `REVIEW.md`는 이 사슬의 산출물이 아니다. 기술 리드가 저장소 루트에 두는 **검토 정책 파일**이다.
- 이 플레이북은 **조직** 단위의 글이다. 제품 담당자, 플랫폼 엔지니어, 기술 리드가 나눠 맡는 일을 전제로 한다. 오늘 실습은 이것을 **나 한 사람**의 루프로 옮긴다(5절).
- 한국어판(`claude.com/ko/...`)은 부분 번역이다. 측정 지표 부분은 한국어판에도 영어로 남아 있다.

## 3. 왜 "산출물"이어야 하는가: 에이전트는 못 보는 것을 모른다

OpenAI에서 3명의 엔지니어가 5개월 동안 손으로 코드를 쓰지 않고 Codex로 제품을 만든 보고서(Ryan Lopopolo, 2026-02-11)는 이렇게 쓴다.

> "From the agent’s point of view, anything it can’t access in-context while running effectively doesn’t exist."

채팅창에서 정한 범위, 머릿속의 완료 기준, 어제 대화에서 합의한 예외는 **다음 세션의 에이전트에게 존재하지 않는다.**
그래서 같은 보고서는 계획을 저장소에 커밋되는 "일급 산출물"로 다룬다.

> "Plans are treated as first-class artifacts."

채팅형으로 AI를 쓰면 대개 이렇게 된다.

| 단계 | 채팅형 사용에서 흔한 모습 | 끊기는 것 |
|---|---|---|
| Plan·Design | "이런 기능 만들어 줘" 한 문장 | 완료 기준이 대화에만 있다 |
| Build | 대화에서 바로 코드가 나온다 | 무엇을 바꾸기로 했는지(계획)가 남지 않는다 |
| Test | "잘 되네요"로 끝난다 | 무엇을 실행해 확인했는지(증거)가 남지 않는다 |
| Deploy·Maintain | 사람이 복사해 붙인다 | 다음에 같은 실수를 막을 장치가 남지 않는다 |

## 4. 하네스는 그 사슬을 "강제"하는 쪽이다

산출물을 남기라고 **부탁**하는 것과 **강제**하는 것은 다르다. 플레이북은 둘을 이렇게 구분한다.

> "A skill is an advisory control while a hook is the deterministic layer behind it."
>
> "The skill makes violations rare and the hook makes them close to impossible."

그리고 빌드 단계의 원칙을 한 줄로 적는다.

> "Nothing is implemented without an accepted plan."

오늘 Part 2~5는 이 "강제하는 쪽", 즉 하네스를 여섯 책임(지침·도구·실행 제어·상태·검증·기록)으로 나눠 읽는다.

## 5. 조직의 플레이북을 내 루프로: 한 사람의 AI SDLC 예

`jh941213/ADLC-harness`는 한 개발자가 위 플레이북과 비슷한 루프를 Claude Code·Codex·Copilot CLI용 plugin으로 만든 것이다(라이선스 표기가 없어 이 저장소에 복사하지 않았다. 링크로만 본다).

- 루프: "의도 → 설계 → 계획 → 구현 → 검증 → 리뷰 → 출시 → 학습" (`README.md:5`)
- 사람이 멈춰 승인하는 곳은 네 곳뿐: "사람은 의도·설계·계획·출시 게이트에서만 승인하고, 단계마다 문서와 승인 기록이 커밋으로 남는다." (`README.md:7`)
- 완료 주장의 규칙: "완료는 이번에 실행한 검증 출력으로만 말한다." (`README.md:8`)
- 멈춤 규칙: "같은 원인으로 세 번 실패하면 멈추고 보고한다." (`README.md:79`)

조직에서는 승인자와 구현자가 다른 사람이다. 혼자 일할 때는 **내가 의도를 쓰고, 내가 승인하고, 내가 AI에게 구현시키고, 내가 확인한다.**
그래서 게이트가 쉽게 생략된다. 한 사람의 AI SDLC에서 하네스가 더 중요한 이유다.

## 6. 오늘 하루의 지도

오늘 손에 남는 것은 `notes/MY_AI_SDLC.md` 하나다. Part마다 한 칸씩 채우고, 실습에서 완성한다.

| 칸 | 채우는 곳 | 질문 |
|---|---|---|
| §1 지금 내 흐름 | Part 1 | 최근 작업 하나는 어느 단계에서 무엇을 남겼나 |
| §2 내 하네스 지도 | Part 2 | 내 폴더에서 Claude Code에 무엇이 실리고, 어느 책임이 비어 있나 |
| §3 Plan·Checkpoint·Evidence | Part 3 | 내 작업은 무엇으로 이어 가고, 무엇으로 완료를 인정하나 |
| §4 가져올 설계 | Part 4 | 남의 하네스에서 근거를 확인하고 가져올 것 하나 |
| §5 내 계획 양식 | Part 5 | 내 작업의 계획에 꼭 들어갈 칸과 실행 구조 |
| §6~§9 진단·분류·장치·지표 | 실습 | 반복되는 문제, 실패한 책임, 고칠 장치, 확인할 지표 |

## 원문

- Claude, *The AI-native SDLC playbook* — https://claude.com/resources/articles/the-ai-native-sdlc-playbook (한국어판 `https://claude.com/ko/resources/articles/the-ai-native-sdlc-playbook`)
- Birgitta Böckeler, *Harness engineering for coding agent users* — https://martinfowler.com/articles/harness-engineering.html
- OpenAI, *Harness engineering: leveraging Codex in an agent-first world* — https://openai.com/index/harness-engineering/ (봇 접근이 막혀 있다. 보관본: `docs/sources/web.md` 4절)
- shareAI-lab/learn-claude-code — https://github.com/shareAI-lab/learn-claude-code
- jh941213/ADLC-harness — https://github.com/jh941213/ADLC-harness
