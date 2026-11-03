# 2026, 삼성SDS - AX Advanced 과정 

## 설치

저장소를 받은 뒤 **루트에서 한 번만** 설치합니다. Day01~Day08이 이 환경 하나를 함께 씁니다.

```bash
uv sync --locked
```

- Python 3.13, `deepagents` 0.7.32 기준이며 `.venv`는 약 1.8GB입니다.
- 실습은 각 Day 폴더에서 `uv run ...`으로 실행합니다. 루트 `.venv`가 자동으로 잡힙니다.
- `.env`는 Day마다 따로 있습니다. 각 폴더의 `.env.example`을 복사해 직접 채웁니다.
- **Day 폴더 안에서 `uv sync`를 실행하지 않습니다.** 다른 Day의 패키지가 지워집니다. 실수했다면 루트에서 `uv sync --locked`로 복구합니다.
- OpenViking 서버만 `mcp<2`를 요구해 `Day02/runtime/openviking/`의 별도 환경으로 실행됩니다. 수강생 명령은 같습니다.

## Install Skills

```bash
# Langchain Skills
# https://github.com/langchain-ai/langchain-skills
npx skills add langchain-ai/langchain-skills --skill '*' --yes
```

## Day02_new

`Day02_new/`는 `Day02/`와 나란히 놓인 새 버전으로, Day01처럼 노트북(`00-Setup`부터 `06-Lab-DeepAgents-RAG`까지)을 위에서 아래로 실행하며 배웁니다. `Day02/`를 대체하지 않습니다. 루트 환경을 쓰고 `pyproject.toml`은 없으며, 이 폴더의 `.env`에 `ANTHROPIC_API_KEY`가 필요합니다. 자세한 내용은 [Day02_new/README.md](Day02_new/README.md)를 봅니다.

## Day03_new

`Day03_new/`는 `Day03/`와 나란히 놓인 새 버전으로, Day01처럼 노트북(`00-Setup`부터 `06-Lab-Research-Agents`까지, 03·04·05는 a/b로 나뉨)을 위에서 아래로 실행하며 Workflow와 Agent의 경계부터 Multi-Agent 선택 기준까지 배웁니다. `Day03/`를 대체하지 않습니다. 루트 환경을 쓰고 `pyproject.toml`은 없으며, 이 폴더의 `.env`에 `ANTHROPIC_API_KEY`와 `EXA_API_KEY`가 필요합니다. 00의 키 확인 셀이 두 키를 모두 확인하고 EXA는 06의 필수 실습에서 씁니다. 자세한 내용은 [Day03_new/README.md](Day03_new/README.md)를 봅니다.
