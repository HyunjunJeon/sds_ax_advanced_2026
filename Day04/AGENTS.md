# AGENTS.md — Day04: Skills와 MCP로 만드는 두 Deep Agent

루트 [../AGENTS.md](../AGENTS.md)의 공통 규칙을 먼저 따르고, 여기에 Day04 고유 규칙을 더한다.

**이 폴더에서 배우는 것:** 코딩 에이전트와 질문 강화형 에이전트를 Deep Agents로 만들며, 업무 절차를 Skill로 분리하고
그 절차를 실제 MCP 도구·상태 저장·근거 파일과 연결한다 (`README.md:1-5`).
**채점 과제가 없다.** 제출물은 다섯 줄 기록뿐이다 (`README.md:111`).
루트 AGENTS.md 4장의 단계적 힌트 정책(L0–L3)은 아래 2장의 네 파일에만 적용하고, 나머지는 자유롭게 돕는다.

## 1. 실행 환경

Day04에는 `pyproject.toml`이 없다. 패키지는 저장소 루트 `pyproject.toml`에 있고 `uv run`이 루트 환경을 찾는다 (`README.md:26-32`).

```bash
cd Day04
# 설치는 저장소 루트의 `uv sync --locked` 한 번으로 끝난다.
# 여기서 `uv sync`를 실행하지 않는다.
cp -n .env.example .env
uv run python <파일>
```

- `.env`에는 `OPENROUTER_API_KEY`와 `OPENROUTER_MODEL`(기본값 `openai/gpt-5.6-luna`)이 있다 (`README.md:40-41`). **`.env` 내용을 출력하지 않는다.** "설정됨/미설정"만 확인하고, 키가 없으면 `.env.example`을 보고 수강생이 직접 채우게 한다.
- 코딩 에이전트의 `execute`는 현재 컴퓨터의 **로컬 셸**에서 실행된다. 파일 도구의 가상 경로는 OS 샌드박스가 아니다 (`README.md:46`).
- 스크립트의 CLI 옵션은 각 파일의 `argparse`에 있는 것만 안내한다.

| 스크립트 | 옵션 (argparse) |
|---|---|
| `coding_skills/prepare.py` | `--workspace` (`prepare.py:14`) |
| `coding_skills/agent.py` | `--prompt`(필수), `--workspace`, `--skills-dir`, `--run-dir` (`agent.py:147-153`) |
| `build_mcp/agent.py` | `--prompt`(필수), `--mode {mcp,scripts}`, `--skill-name`, `--server`, `--skills-dir`, `--db`, `--evidence-dir`, `--no-skills`, `--trace` (`agent.py:169-188`) |
| `build_mcp/verify.py` | `--server`, `--stage {1..5}` (`verify.py:462-463`) |
| `build_mcp/verify_agent.py` | `--server`, `--skills-dir`, `--output-dir` (`verify_agent.py:420-422`) |
| `coding_skills/verify_agent.py`, `build_mcp/verify_scripts.py` | 옵션 없음 (앞은 `-h`만 처리 `verify_agent.py:426`, 뒤는 `unittest.main`) |

## 2. 힌트 정책 대상 파일

수강생이 직접 쓰는 네 파일에만 루트 4장의 L0–L3을 적용한다 (`build_mcp/README.md:78-82`).

- `work/my-mcp/server.py`
- `work/my-mcp/workflow.py`
- `work/my-mcp/evidence.py`
- `work/my-mcp/skills/requirements-interview/SKILL.md`

| 단계 | 해도 되는 것 | 조건 |
|---|---|---|
| L0 | 개념 설명, 실패 상황 설명, 관련 원문·코드 안내 | 언제나 |
| L1 | 계약 해설, 반례 설계, 검사기 출력 읽기 | 언제나 |
| L2 | 의사코드, 함수 골격, 자료구조 제안 | 수강생이 자기 접근을 먼저 말한 뒤 |
| L3 | 최소 diff 수정 제안, 디버깅 | 수강생이 자기 코드와 실패 로그를 제시한 뒤 |

- `build_mcp/reference/`의 구현(`server.py`, `workflow.py`, `evidence.py`)을 `work/my-mcp/`에 **완성 답으로 옮겨 붙이지 않는다.** L0–L3을 우회하게 된다. 설명이 필요하면 정책이 허용하는 수준에서 인용·해설만 한다.
- 이 파일들은 채점 대상이 아니지만, 직접 쓰는 것이 학습 목표이므로 정책을 적용한다.
- 거부는 한 문장으로 짧게 하고 바로 대안(계약 해설, 반례 설계)을 실행한다.

## 3. 자유 실습 (정책 비적용)

아래 활동은 채점이 없는 **자유 실습**이다. AI 조교가 완성 구현까지 도울 수 있다.
단, 자유 실습이라는 표현이 2장의 네 파일로 확장되지는 않는다.

| 활동 | 내용 |
|---|---|
| `실습.md` | 연습 문제 6개 (`README.md:9`) |
| `coding_skills/task.md` | `diagram-design` Skill을 `agent.py`가 읽게 하고, 생성한 코드의 Flow를 HTML로 출력한다. Claude가 아니라 `agent.py`가 만들어야 한다. 순서: Skill 구조 파악 → `SKILL.md` 분할 설계 → 불필요한 reference·scripts·assets 선택 → 구현 → 실행 |
| `build_mcp/task.md` | 스킬을 새로 만들지 않고, MCP 서버 없이 `agent.py`가 원래 Tools를 코드 실행으로 쓰게 한다 |

`build_mcp/task.md`와 기존 구현의 관계: `build_mcp/agent.py`에 `--mode scripts`가 있고 `execute` 하나만 공개한다 (`agent.py:3`, `agent.py:170`). `build_mcp/script_runtime.py:1`은 "스킬을 발견하고 범용 execute만 제공하는 실행 환경"이다. `skills/requirements-interview-new/scripts/`에 `run.py`·`workflow.py`·`evidence.py`가 있고, `verify_scripts.py:1`은 이를 검사한다. 다만 이것이 `task.md`의 정답 구현인지, 수업에서 어떤 용도로 두었는지는 `task.md`에 쓰여 있지 않아 **확인이 필요하다.** 단정해 안내하지 않는다.

## 4. 파일 안내

| 경로 | 내용 |
|---|---|
| `coding_skills/` | 코딩 에이전트 실습. `agent.py`, `prepare.py`, `run_files.py`, `llm.py`, `skills/`(버그 수정·기능 추가·리뷰), `project/`(실패가 포함된 CSV 집계 프로그램), `README.md`, `task.md` |
| `build_mcp/` | 질문 강화형 에이전트·MCP 실습. [README.md](build_mcp/README.md), [MCP_GUIDE.md](build_mcp/MCP_GUIDE.md), [reference/](build_mcp/reference/)(기준 구현), `skills/`, 검사기 |
| [실습.md](실습.md) | 연습 문제 6개 |
| [SKILLS_GUIDE.md](SKILLS_GUIDE.md) | Skill의 기본 구조와 좋은 작성 기준 |
| [good_skill.md](good_skill.md), [skill_eval.md](skill_eval.md) | Skill 작성·평가 참고 자료 |
| [advanced_study/](advanced_study/) | 선택 논문 요약(`*_요약.md`)과 원문 PDF |
| `evidence/` | 실행 근거. `.gitignore`에 있어 커밋하지 않는다 |
| `work/` | 학생 작업 사본. `.gitignore`에 있어 커밋하지 않는다 |

## 5. 검사기와 비용

| 검사기 | 모델 호출 | 규모 |
|---|---|---|
| `build_mcp/verify.py` | 없음. MCP 서버 계약을 직접 검사한다 (`README.md:44`, `README.md:83`) | 즉시 |
| `build_mcp/verify_scripts.py` | 없음. 파일 첫 줄에 "모델/API 호출 없음"이 명시돼 있다 (`verify_scripts.py:1`) | 즉시 |
| `coding_skills/verify_agent.py` | 있음 | 모델 약 25–45회, 약 2–5분 (`coding_skills/README.md:154`) |
| `build_mcp/verify_agent.py` | 있음 | 모델 약 20–35회, 약 2–5분 (`build_mcp/README.md:262`) |

- 유료 실행(`agent.py`, `verify_agent.py`)은 막지 않는다. 실행 **직전에 규모를 한 줄로 고지**한다.
- 검사가 통과한 것과 Skill 절차를 따른 것은 별개다. 근거 파일(`evidence/`)과 최종 답변을 대조하게 한다.

## 6. 편집 경계

- `work/`, `evidence/`, `.env`는 커밋하지 않는다 (`.gitignore:1,6,7`). 루트 `.gitignore:15`에도 `.env`가 있다.
- `build_mcp/reference/work/`도 `work/` 규칙에 걸려 무시된다.
- `.env` 내용을 열거나 출력하지 않고, 키 값을 로그·결과에 남기지 않는다.
- 문서와 코드가 다르면 코드가 정답이다. 차이를 발견하면 수강생에게 알린다.
