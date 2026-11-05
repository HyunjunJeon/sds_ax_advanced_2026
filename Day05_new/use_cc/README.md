# Day05 use_cc — Agent 평가와 모니터링을 Claude Code로 실습하기

Day05_new의 노트북 과정(Part 1~5 + 실습)을 **Claude Code와 Langfuse 두 화면**으로 실습하는 구성입니다. 노트북(`Day05_new/00`~`06`)은 그대로 두고 강의 본문·참고본으로 씁니다.

- **Claude Code**(실습 폴더에서 연 세션)는 미션 카드의 부탁 문장대로 코드를 만들고 실행합니다.
- **Langfuse**(브라우저)는 주 검토 화면입니다. trace, 점수, Dataset, 사람 검수 큐, 대시보드를 여기서 읽습니다.
- 수강생은 **예측하고, 정하고(규칙 문장·검수·라벨·결정), 화면에서 확인하고, 자기 말로 설명합니다.** 그 칸은 Claude Code가 대신 채우지 않습니다.

## 수업 구성 (총 390분, 노트북 과정과 같은 시간)

| 카드 | Part | 분 | 핵심 질문 | 참고 노트북 |
|---|---|---|---|---|
| `missions/m0.md` | 준비 | 10 | 무엇이 어디에 기록되고 어느 화면에서 읽는가 | 00 |
| `missions/m1.md` | 1. 왜 Agent를 평가하는가 | 40 | 그럴듯한 답이 왜 성공의 증거가 못 되는가 | 01 |
| `missions/m2.md` | 2. 오프라인 평가와 Golden Dataset | 60 | 정답은 누가 어떻게 고정하는가 | 02 |
| `missions/m3a.md` | 3. 온라인 평가와 Trace 선정 | 45 | 정답 없는 운영 trace를 무엇으로, 어떤 것부터 채점하는가 | 03a |
| `missions/m3b.md` | 3. Trajectory 평가 | 55 | 틀린 것은 에이전트인가 평가기인가, 고친 평가기는 어떻게 믿는가 | 03b |
| `missions/m4.md` | 4. Agent Monitoring | 45 | 경보는 무엇을 말해 주고 무엇을 말해 주지 못하는가 | 04 |
| `missions/m5.md` | 5. 평가와 모니터링의 결합 | 45 | 사람 판정·평가기 변경·회귀 Golden·승인 게이트를 어떻게 잇는가 | 05 |
| `missions/m6.md` | 실습: Self-Improving Agent와 Observability | 90 | 무엇을 고정하고 무엇을 열며, "나아졌다"는 판정은 무엇으로 믿는가 | 06 |

교시 리듬은 개념(노트북 화면으로 강의) → 강사 시연 → 미션 → 해설입니다. m3b·m4·m5는 같은 모의 운영 기록(`cc_ops`)을 이어서 씁니다: 실제 모델이 '이어서 처리' 요청을 정책 문서와 Prompt대로 처리했는데 궤적 규칙이 치명으로 판정하는 사건을, 평가기 평가(m3b) → 경보(m4) → 사람 판정·backtest·승인 게이트(m5)로 따라갑니다.

## 준비

1. 저장소 루트에서 한 번 `uv sync --locked`.
2. **Langfuse 프로젝트는 각자 만듭니다.** Langfuse Cloud에 로그인(데이터 지역 선택) → New project → API 키 발급(Secret Key는 한 번만 보입니다). 순서는 `missions/m0.md`의 준비 1)에 있습니다. 수업 전에 해 오면 m0 시간이 넉넉해집니다.
3. `Day05_new/.env.example`을 `Day05_new/.env`로 복사해 **편집기로** 본인의 키를 채웁니다: `OPENGATEWAY_API_KEY`(에이전트·Judge·개선기가 모두 이 키로 `deepseek/deepseek-v4.1-flash-ultrafast`를 부릅니다), Decision API 키 하나(`TYPESAFE_API_KEY` 등), Langfuse 화면의 `.env` 예시 세 줄(`LANGFUSE_BASE_URL` 줄을 그대로 써도 됩니다). 키를 Claude Code 대화에 붙여 넣지 않습니다.
4. 실습 폴더를 **저장소 밖에** 만듭니다: `uv run --no-sync python Day05_new/use_cc/setup_sandbox.py ~/day05-lab`. 이때 `Day05_new/.env`가 실습 폴더로 복사되고, 그 뒤로는 실습 폴더의 `.env`가 쓰입니다.
5. `cd ~/day05-lab && claude` → 폴더 신뢰 화면에서 **Yes, I trust this folder**(기본값은 No) → `/mission m0`.

실습 폴더에는 dev 카드 9장과 dev fixture만 있고, holdout 카드는 ID만 있습니다. holdout은 m6에서 저장소 쪽 명령(`tools/holdout_check.py`)으로만 한 번 엽니다. Claude Code는 작업 폴더의 파일을 모두 읽을 수 있고, 권한 거부 규칙은 Python 스크립트가 직접 여는 파일에는 걸리지 않기 때문입니다(https://code.claude.com/docs/en/permissions.md).

## 비용

세 갈래입니다. 각 카드 맨 위의 "이 미션의 비용" 표가 그 미션의 규모입니다.

1. **Claude Code 세션**: 수강생 본인의 Claude Code 계정. 카드의 값은 리허설 전 추정입니다.
2. **에이전트 모델·Judge·개선기**: `OPENGATEWAY_API_KEY`. 2026-11-05 기준 가격은 100만 토큰당 입력 $0.15·출력 $0.60(할인가, 정가는 $0.30·$1.20)입니다. 가격은 바뀔 수 있습니다.
3. **Jev**: Decision API 키(m0, m2, m3a).

## 이 구성이 주장하지 않는 것

- 카드의 "저자 1회 관찰" 값은 2026-11-05 저자 리허설의 한 번 결과입니다. 수업에서는 다르게 나올 수 있습니다.
- Claude Code 세션의 호출 수와 미션 시간은 사람이 직접 진행해 재지 않았습니다(리허설 전 추정).
- OpenGateway가 effort를 DeepSeek의 어떤 설정으로 옮기는지, Langfuse Cloud의 2026-11-16 이후 동작은 확인하지 않았습니다. eval_lab은 그날 없어지는 Langfuse v1 API를 쓰지 않도록 바꿨습니다(`Day05_new/docs/DESIGN.md` 19절).
