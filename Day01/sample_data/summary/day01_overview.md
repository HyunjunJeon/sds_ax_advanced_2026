# Day01 자료 개요: LangGraph V1 튜토리얼

## 1. 이 자료가 가르치는 것
- **한 줄 요약**: LangGraph V1과 LangChain 1.x로 AI 에이전트를 만드는 방법을 단계별로 배우는 한국어 Jupyter Notebook 모음입니다. 대상은 초보자부터 중급 개발자까지입니다.
- **출처**: `braincrew-lab/langgraph-v1-tutorial` 저장소의 스냅샷입니다. 커밋은 `aca51ad2db7e4ff91f25bfea14d3eeb4e13798c7`입니다. 설치를 저장소 루트로 합치기 위해 `pyproject.toml`, `README.md`를 고쳤고 `uv.lock`, `.python-version`은 삭제했습니다. (UPSTREAM.md 기준)
- **학습 목표**
  - StateGraph의 State, 노드, 엣지, 조건부 분기와 `Command`/`Send`로 그래프를 만듭니다.
  - `create_agent`, 도구, 미들웨어, Runtime, 구조화된 출력, Human-in-the-Loop로 에이전트를 만듭니다.
  - 단기/장기 메모리, 가드레일, 컨텍스트 엔지니어링, MCP로 에이전트를 확장합니다.
  - Supervisor, 협업 네트워크, 계층적 팀 같은 멀티에이전트 패턴을 구현합니다.
  - 상태 수동 업데이트, ToolNode, 병렬 분기, 서브그래프, 스트리밍으로 LangGraph 핵심 기능을 익힙니다.
  - RAG 응용(Agentic/Corrective/Self/Adaptive RAG), 실전 유스케이스, GraphRAG를 다룹니다.
- **다루는 라이브러리**(README의 버전 표 기준)
  - `langchain` >= 1.4.0
  - `langchain-core` >= 1.6
  - `langgraph` >= 1.2.11
  - `langgraph-checkpoint-postgres` / `-redis`
  - `langchain-anthropic` / `langchain-openai`
  - `fastmcp` / `mcp`
  - `deepagents`
  - `langchain-teddynote`
  - Appendix에서는 Neo4j(`langchain-neo4j`)와 Tavily 웹 검색도 사용합니다.
- **실행 환경**
  - Python 3.13, 패키지 관리자는 uv(저장소 루트에서 `uv sync --locked`)입니다.
  - 기본 모델은 OpenAI `gpt-5.4`(`init_chat_model("gpt-5.4")`)입니다.
  - 필요한 API 키는 OpenAI, Tavily, LangSmith(선택), Anthropic(선택)입니다.
  - 사전 지식은 Python 기초, async/await, LLM·프롬프트 기초입니다.

## 2. PART별 핵심 내용과 대표 노트북

### PART 01. LangGraph 기초
Ch01에서 그래프 생성의 기본 개념을 배웁니다.
- 대표: `/PART01-LangGraph-기초/Ch01-그래프-생성하기/03-LangGraph-Building-Graphs.ipynb` (StateGraph, 노드/엣지, 조건부 분기, `Command`/`Send`)
- 이 챕터의 다른 노트북은 다음과 같습니다.
  - `01-LangGraph-Introduction.ipynb`
  - `01-LangGraph-Models.ipynb`
  - `01-QuickStart-LangGraph-Tutorial.ipynb`
  - `02-LangGraph-Messages.ipynb`
  - `02-QuickStart-LangGraph-Graph-API.ipynb`

### PART 02. 에이전트
- Ch02 에이전트
  - 대표: `/PART02-에이전트/Ch02-에이전트/01-LangGraph-Agents.ipynb` (`create_agent`, 도구, 미들웨어, 재시도/폴백)
  - 그 밖에 `02-LangGraph-ChatBot.ipynb`, `02-LangGraph-Tools.ipynb`(`@tool`, `ToolRuntime`), `03-QuickStart-LangGraph-Ollama.ipynb`(로컬 모델)가 있습니다.
- Ch03 Runtime: `/PART02-에이전트/Ch03-Runtime/04-LangGraph-Runtime.ipynb` (`Runtime`, `context_schema`, Store, Stream writer)
- Ch04 구조화된 출력: `/PART02-에이전트/Ch04-구조화된-출력/05-LangGraph-Structured-Output.ipynb` (`response_format`, `ToolStrategy`, `ProviderStrategy`)
- Ch05 Human-in-the-Loop: `/PART02-에이전트/Ch05-Human-in-the-Loop/06-LangGraph-Human-In-the-Loop.ipynb`
  - `interrupt`, `HumanInTheLoopMiddleware`, `Command(resume=...)`를 다룹니다.
  - 같은 폴더에 `02-LangGraph-Human-In-The-Loop.ipynb`도 있습니다.

### PART 03. 에이전트 확장
- Ch06 미들웨어: `/PART03-에이전트-확장/Ch06-미들웨어/01-LangGraph-Middleware.ipynb` (`before_model`, `after_model`, `wrap_model_call`, `dynamic_prompt`)
- Ch07 컨텍스트 엔지니어링: `/PART03-에이전트-확장/Ch07-컨텍스트-엔지니어링/03-LangGraph-Context-Engineering.ipynb`
- Ch08 가드레일: `/PART03-에이전트-확장/Ch08-가드레일/04-LangGraph-Guardrail.ipynb` (`PIIMiddleware`)
- Ch09 메모리: `/PART03-에이전트-확장/Ch09-메모리-추가하기/01-LangGraph-Add-Memory.ipynb`
  - `InMemorySaver`와 `thread_id`로 단기 메모리를 다룹니다.
  - 같은 폴더에 `02-LangGraph-Memory-Postgres`(Postgres 영속 메모리), `04-LangGraph-Agent-With-Memory`(장기 메모리), `09-LangGraph-DeleteMessages`, `12-LangGraph-Add-Conversation-Summary`(대화 요약)가 있습니다.
- Ch10 MCP: `/PART03-에이전트-확장/Ch10-LangGraph-MCP-실습/01-LangGraph-MCP-Tutorial.ipynb` (`langchain.mcp` `MCPAdapter`, FastMCP 서버, stdio / Streamable HTTP)

### PART 04. 멀티에이전트
- Ch11 Supervisor: `/PART04-멀티에이전트/Ch11-멀티에이전트-Supervisor/01-LangGraph-Supervisor.ipynb` (`03-LangGraph-Multi-Agent-Supervisor.ipynb`도 있음)
- Ch12 협업 네트워크: `/PART04-멀티에이전트/Ch12-멀티-에이전트-협업-네트워크/02-LangGraph-Multi-Agent-Collaboration.ipynb` (에이전트 간 핸드오프)
- Ch13 계층적 팀: `/PART04-멀티에이전트/Ch13-계층적-에이전트-팀/04-LangGraph-Hierarchial-Agent-Team.ipynb`

### PART 05. 핵심 기능 구현하기
`/PART05-핵심-기능-구현하기/` 아래 Ch14~Ch22가 있습니다.
- Ch14: `Ch14-LangGraph-활용-Agent-구축/03-LangGraph-Agent.ipynb` (에이전트 루프를 직접 구현)
- Ch15: `Ch15-중간-단계의-상태-수동-업데이트/07-LangGraph-Manual-State-Update.ipynb` (`update_state`)
- Ch16: `Ch16-상태-커스터마이징/08-LangGraph-State-Customization.ipynb`
- Ch17: `Ch17-ToolNode/10-LangGraph-ToolNode.ipynb` (`ToolNode`, `tools_condition`)
- Ch18: `Ch18-병렬-노드-실행을-위한-분기-생성/11-LangGraph-Branching.ipynb` (팬아웃/팬인)
- Ch19: `Ch19-서브그래프-추가-및-사용/13-LangGraph-Subgraph.ipynb`
- Ch20: `Ch20-서브그래프-입출력-변환/14-LangGraph-Subgraph-Transform-State.ipynb`
- Ch21: `Ch21-LangGraph-스트리밍-모드/` 아래 `03-LangGraph-Streaming`, `05-LangGraph-Streaming-Outputs`, `15-LangGraph-Streaming-Steps` (`stream_mode`, 토큰 스트리밍, 이벤트 스트리밍)
- Ch22: `Ch22-Agent-Chat-UI-OSS/Agent-Chat-UI-OSS.ipynb` (`langgraph dev`와 Agent Chat UI)

### Appendix (노트북 앞부분을 직접 확인함)
- **A-RAG응용** (노트북 10개)
  - 순서: Naive RAG → Groundedness Check → Web Search → Query Rewrite → Agentic RAG → CRAG → Self-RAG → Adaptive RAG.
  - Naive RAG는 PDF 문서로 Retriever와 Chain을 만들고, State/Node/Edge로 RAG 워크플로우를 구성하고, 스트리밍 출력까지 다룹니다.
  - 대표: `/Appendix/A-RAG응용/02-LangGraph-Naive-RAG.ipynb`
  - **README에 없는 노트북 2개**
    - `01-LangGraph-Building-Graphs.ipynb`: State → 노드 → 그래프 → 컴파일 → 시각화 순서의 기본 그래프 생성과 조건부 엣지를 복습합니다.
    - `10-LangGraph-Retrieval.ipynb`: 벡터 저장소 기반 지식 베이스를 만들고 2-Step RAG, Agentic RAG, Hybrid RAG 세 구조를 비교합니다. `create_agent`로 Agentic RAG를 만들고, 쿼리 전처리·검색 검증·생성 후 검사를 넣은 Hybrid RAG와 메타데이터 필터링을 다룹니다.
- **B-Use-Cases** (노트북 5개)
  - `01-LangGraph-Agent-Simulation`, `02-LangGraph-Prompt-Generation`, `03-LangGraph-Plan-and-Execute`, `04-LangGraph-SQL-Agent`, `05-LangGraph-Research-Assistant`
  - 대표: `/Appendix/B-Use-Cases/03-LangGraph-Plan-and-Execute.ipynb`. 장기 계획을 먼저 세우고 단계별로 실행하며 필요하면 재계획합니다. 계획에는 큰 모델, 실행에는 작은 모델을 쓰는 방식이며, ReAct와 대비됩니다.
- **C-GraphRAG** (노트북 1개)
  - `/Appendix/C-GraphRAG/01-LangGraph-Text2Cypher-Neo4j.ipynb`
  - 자연어 질문을 Cypher로 변환하고 검증·실행한 뒤 자연어로 답합니다. 오류가 나면 쿼리를 다시 만드는 재시도 로직이 있습니다. Neo4j(AuraDB 또는 Docker)와 Movies 샘플 데이터를 씁니다.

## 3. README와 실제 파일 대조
- 실제 `.ipynb`는 총 51개입니다. PART01~05의 노트북 목록은 README와 일치합니다.
- README는 챕터 폴더를 줄여서 적었습니다(예: `PART02/Ch02/...`). 실제 폴더명은 `PART02-에이전트/Ch02-에이전트/`처럼 한글 이름이 붙어 있어 위 경로를 따릅니다.
- Appendix A의 `01-LangGraph-Building-Graphs.ipynb`와 `10-LangGraph-Retrieval.ipynb`는 README 설명에 없고 실제 파일만 있습니다.
- README 표에는 B의 5개 주제와 C의 Text2Cypher가 모두 적혀 있고 실제 파일과 일치합니다.

## 4. 권장 학습 순서
1. 환경 준비: uv 설치, 루트에서 `uv sync --locked`, `.env`에 API 키 설정.
2. PART01(그래프 기초) → PART02(에이전트) → PART03(확장: 미들웨어, 메모리, MCP) → PART04(멀티에이전트) → PART05(핵심 기능 심화) → Appendix 순으로 진행합니다. 이 순서는 README가 권장하는 순서입니다.
3. PART01은 `01-LangGraph-Introduction`과 `01-QuickStart-LangGraph-Tutorial`로 시작해 `03-LangGraph-Building-Graphs`로 마무리합니다.
4. Appendix는 A(RAG, `01-Building-Graphs`로 복습한 뒤 `02`~`10`) → B(유스케이스) → C(GraphRAG, Neo4j 필요) 순으로 보면 됩니다. 이 Appendix 내부 순서는 파일 번호를 따른 제 제안입니다.

## 5. 근거로 읽은 파일
- `/README.md` (전체)
- `/UPSTREAM.md`
- glob `**/*.ipynb` 결과(실제 노트북 목록)
- 노트북 앞부분(limit=40)
  - `/Appendix/A-RAG응용/01-LangGraph-Building-Graphs.ipynb`
  - `/Appendix/A-RAG응용/02-LangGraph-Naive-RAG.ipynb`
  - `/Appendix/A-RAG응용/10-LangGraph-Retrieval.ipynb`
  - `/Appendix/B-Use-Cases/03-LangGraph-Plan-and-Execute.ipynb`
  - `/Appendix/C-GraphRAG/01-LangGraph-Text2Cypher-Neo4j.ipynb`
- PART01~05 노트북은 열지 않았고, 내용은 README 설명을 따랐습니다.
