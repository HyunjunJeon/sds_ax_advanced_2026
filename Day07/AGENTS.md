# AGENTS.md — Day07: vLLM 기초와 추론 속도 최적화

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day07 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** RunPod에 띄운 vLLM(GLM-5.3-Flash)을 호출해 보고, 자유 실습 두 가지를 진행한다.
**채점 과제가 없고 힌트 정책 대상 파일도 없다.** `task.md`와 `dcode_task.md`는 자유 실습(채점 없음)이므로
루트 AGENTS.md 4장의 단계적 힌트(L0~L3)를 적용하지 않는다. 구현을 끝까지 돕는 것도 허용한다.
다만 5장(절대 하지 말 것)과 7장(키와 보안)은 그대로 적용한다.

## 0. 가장 먼저 — CLI 플래그가 없다

`runpod_model_call.py`와 `runpod_openai_reasoning.py`에는 `argparse`가 없다. 플래그를 지어내 안내하지 않는다.

## 1. 실행

- Day07은 독립 프로젝트다. 항상 `cd Day07 && uv run python <파일>`로 실행한다. 루트에서 `uv run`을 하지 않는다.
- `RUNPOD_BASE_URL`은 필수다. `Day07/.env`에서 읽으며, 없으면 두 스크립트는 안내를 출력하고 종료 코드 1로 끝난다.
  값은 강사가 공지한다. 코드나 문서에 Pod 주소를 하드코딩하지 않는다.
- `.env`의 내용을 출력하지 않는다. "설정됨/미설정"만 확인한다. 키가 없으면 `.env.example`을 보고 수강생이 직접 채우게 안내한다.

## 2. 도울 때 지킬 것

- `dcode_task.md`는 OpenAI·Anthropic·Google 3사 모델 호출을 불허한다. 테스트 모델은 GLM-5.3-Flash,
  DeepSeek-V4.1-Flash, Qwen3.8이다. 이 제한을 벗어나는 코드나 모델 설정을 제안하지 않는다.
- EXA(task.md의 Tool)나 OpenRouter(dcode_task.md)를 호출하는 실행은 막지 않되, 실행 직전에 규모를 한 줄로 고지한다.
- RunPod Pod는 시간당 과금되며 비용은 강사가 낸다. 불필요하게 긴 호출을 반복하지 않는다.
- RunPod 프록시는 100초에서 연결을 끊는다. 두 스크립트의 `timeout=95`는 이 때문이며, 긴 응답은 스트리밍으로 받는다.
- 사고 과정 필드 이름은 vLLM 버전에 따라 `reasoning` 또는 `reasoning_content`다 (`runpod_openai_reasoning.py`의 `reasoning_of`).
- 이 폴더의 문서에 없는 플래그·옵션·파일은 지어내지 않는다. 확인이 안 되면 [README.md](README.md)와 강의 PDF를 보라고 안내한다.

## 3. 파일 상태표

| 파일 | 내용 |
|---|---|
| `runpod_model_call.py` | langchain-openai로 호출 (자유 실습 참고용) |
| `runpod_openai_reasoning.py` | openai SDK로 reasoning/content 분리 확인 |
| `task.md`, `dcode_task.md` | 자유 실습 안내 (채점 없음) |
| `.env.example` | `RUNPOD_BASE_URL`(필수), `EXA_API_KEY`, `OPENROUTER_API_KEY` |
| `README.md` | 준비·실행·활동·강사용 Pod 기동 메모 |
