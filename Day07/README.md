# Day07: vLLM 기초와 추론 속도 최적화

RunPod에 띄운 vLLM 서버(GLM-5.3-Flash)를 호출해 보고, 자유 실습 두 가지(DeepAgents 만들기, dcode 설정)를 진행한다.
강의 자료는 [Day7_vLLM_기초와_추론_속도_최적화.pdf](Day7_vLLM_기초와_추론_속도_최적화.pdf)다.
채점 과제는 없다.

## 파일

| 파일 | 내용 |
|---|---|
| `runpod_model_call.py` | langchain-openai `ChatOpenAI`로 RunPod vLLM을 호출한다 |
| `runpod_openai_reasoning.py` | openai SDK로 호출해 사고 과정(reasoning)과 답변(content)을 나눠 본다 |
| [task.md](task.md) | 활동 1: DeepAgents 하나 만들기 |
| [dcode_task.md](dcode_task.md) | 활동 2: dcode 설정 과제 4개 |
| `.env.example` | 환경변수 양식 (`RUNPOD_BASE_URL`, `EXA_API_KEY`, `OPENROUTER_API_KEY`) |
| `Day07_01.png` ~ `Day07_03.png` | 강의 이미지 |

## 준비

```bash
cd Day07
# 설치는 저장소 루트의 `uv sync` 한 번으로 끝난다. 여기서 `uv sync`를 실행하지 않는다.
cp .env.example .env
```

`.env`의 `RUNPOD_BASE_URL`은 필수이며 강사가 수업 때 공지한다. 형태는 `https://<POD_ID>-8000.proxy.runpod.net/v1`이다.
값이 없으면 두 스크립트는 안내 메시지를 출력하고 종료한다. `EXA_API_KEY`는 task.md의 EXA Tool,
`OPENROUTER_API_KEY`는 dcode_task.md에서 쓴다.

## 실행

```bash
cd Day07
uv run python runpod_model_call.py
uv run python runpod_openai_reasoning.py
```

두 스크립트에는 CLI 플래그가 없다.

- `runpod_model_call.py`: `ChatOpenAI`로 "한 줄로 자기소개 해줘."를 호출하고 답변을 출력한다.
  `chat_template_kwargs`로 `reasoning_effort: low`를 전달한다.
- `runpod_openai_reasoning.py`: 같은 질문을 비스트리밍과 스트리밍으로 호출하고 Reasoning과 Answer를 나눠 출력한다.
  `reasoning_effort: max`를 전달한다.

## 활동 (자유 실습, 채점 없음)

### 활동 1 — [task.md](task.md)

- DeepAgents 하나를 만든다.
- 모델은 GLM-5.3-flash(RunPod)를 쓴다.
- EXA API를 활용하는 Tool을 하나 둔다.
- 입력: `GLM-5.3-Flash 라는 모델의 분석 보고서를 작성할 것.`

### 활동 2 — [dcode_task.md](dcode_task.md)

- OpenRouter 기반 API를 쓴다. OpenAI·Anthropic·Google 3사 모델 호출은 불허한다.
- 테스트 모델: GLM-5.3-Flash, DeepSeek-V4.1-Flash, Qwen3.8.
- WSL 환경에서만 진행한다.
- 문서: https://docs.langchain.com/oss/deepagents/code/quickstart
- 설치: `curl -LsSf https://langch.in/dcode | bash`
- 과제 4개: Prompt Caching을 고려한 구성, 모델별 Harness Profile, 메모리 구성 확인·테스트, Middleware로 Self-Improving.
- 목-금 PJT용 dcode 소스는 Day08에서 제공한다.

## 주의

- RunPod 프록시는 100초에서 연결을 끊는다. 그래서 두 스크립트의 `timeout`이 95초다. 긴 응답은 스트리밍으로 받는다.
- vLLM 버전에 따라 사고 과정 필드 이름이 `reasoning` 또는 `reasoning_content`다 (`runpod_openai_reasoning.py`의 `reasoning_of`).
- langchain-openai의 `ChatOpenAI`는 비표준 필드(reasoning)를 버리므로 사고 과정은 openai SDK로 확인한다.

## 강사용: Pod 기동

(2026-09-15 강사 검증 메모)

- RunPod Secure Cloud, H200 SXM x4 (시간당 약 $18.36).
- 이미지 `vllm/vllm-openai:glm53-flash` (vLLM v0.28.1rc1 dev 빌드, ENTRYPOINT `vllm serve`).
- 모델 `zai-org/GLM-5.3-Flash`, TP4 + MTP(5), 이름 `GLM-5.3-Flash`로 8000 포트에 서빙한다.
  접속 주소는 `https://<POD_ID>-8000.proxy.runpod.net/v1`이다.
- **처음부터 환경변수 `NCCL_NVLS_ENABLE=0`을 준다.** 없으면 약 78초마다 `ncclCommInitRank`에서
  `Failed to bind NVLink SHARP (NVLS) Multicast memory ... CUDA error 401`로 크래시 루프에 빠진다.
- 기동에 약 15~20분이 걸린다. 가중치 약 306 GiB 다운로드 약 300초, 로드 약 56초, CUDA graph 약 215초, 이후 autotune warm-up.
- 진행 확인은 `runpodctl pod logs --tail N`으로 한다. GraphQL `memoryUtilPercent`는 계속 0이고 `--since`는 0줄을 돌려주는 경우가 많다.
- 수업이 끝나면 Pod를 내린다. 시간당 과금은 강사에게 청구된다.
