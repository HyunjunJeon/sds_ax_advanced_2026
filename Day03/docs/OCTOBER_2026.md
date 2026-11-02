# 2026-10 공통 원문으로 구조 비교하기

Day02의 RAG 실습을 마친 뒤 기존 00→13 순서로 진행한다. 이 확장은 같은 근거가
구조 사이에서 어떻게 전달·유실되는지 관찰하는 데 사용한다.

## 코퍼스 선택

`vendor/day02/data/official-2026-10/`은 Day02와 같은 원문·발췌·사례·평가 초안의 스냅샷이다.
원문 2개, 발췌 9개, 사례 12개이며 기준일은 2026-10-02다. 원문과 발췌가 변조되면 실행 전에 거절한다.
`gold.jsonl`은 AI 작성 초안(`draft`)이다. 강사의 원문 대조 전 결과는 잠정 지표로 읽는다.

00 및 각 번호 파일의 `LabConfig`에 아래 조건을 적용한다. CLI 플래그는 없다.

```python
실험 = LabConfig(
    backend="local",
    corpus="official-2026-10",
    workspace="work/rag/october-lab01",
    entity="공통",
    as_of="2026-10-02",
    question="DeepAgents 0.7.21의 FilesystemMiddleware blob 지원은 어떻게 바뀌었나요?",
)
```

번호별로 workspace를 다르게 지정한다. business 작업 영역을 공식 코퍼스로 바꾸면 거절된다.
local은 어휘 검색이며 00 준비는 무료지만, 01 이후의 Agent는 실제 모델을 호출한다.
OpenViking은 `backend="viking"`, 별도 서버 설정, 첫 실행의 `ingest=True`가 필요하다.
서버 실패를 local로 자동 우회하지 않는다.

## 단계별 관찰

| 단계 | 질문·대조 | 확인할 근거 |
|---|---|---|
| 01 기준선 | `tech-blob` | 직접 검색으로 해결한 호출 수와 인용 |
| 02 적응형 | `tech-context` | 재검색 전후 누락 근거 |
| 03 순차 | 변경 이력 두 버전의 비교 | 조사·작성·검토에 전달한 정보 |
| 04 라우터 | 기술 문서 질문의 담당자 | 배정 이유와 실제 검색 오류를 구분 |
| 05 병렬 | `tech-parallel` | 같은 plan_file의 순차/동시 실행 시간·합산 토큰 |
| 06 Supervisor | `tech-context`, evidence/summary 대조 | parent_context·원문 복원·실패 보존 |
| 07 Handoff | `tech-followup` | 담당자 유지·후속 질문 해석 |
| 08 웹 보강 | 고정 원문과 새 수집 비교 | 공개일·수집일·원문 해시 |
| 09·13 비교 | 아래 사례를 동일 조건으로 실행 | 품질·실패·Judge 누락·비용 |

05·07의 TODO는 수강생 구현 지점이다. 완성 뒤 전체 7구조를 비교한다.
독립적인 기능을 조사하는 병렬 구조와, 사용자 응답 담당자를 이전하는 Handoff의 목적을 구분한다.
[공식 멀티에이전트 안내](https://docs.langchain.com/oss/python/langchain/multi-agent)도
각 Agent가 받는 정보와 호출·토큰 비용을 패턴 선택의 기준으로 설명한다.

## 비교 조건

09에서 `실험.corpus`와 새 workspace를 정하고 `CASES`를 선택한 코퍼스의 ID로 바꾼다.
첫 실행 확인은 01의 기준선 1개와 사례 1개로 하고, 선수 구현을 마친 뒤 반복 비교를 한다.

```python
CASES = ["tech-blob", "tech-context", "tech-parallel", "tech-followup", "tech-unannounced"]
REPEATS = 3
```

`tech-followup`은 2턴이다. 비용은 두 턴 모두 포함하고 평가는 마지막 턴에만 적용한다.
실행 전 출력하는 규모에서 후속 턴과 별도 Judge를 확인한다. 13의 짝 비교는 같은 원문·사례·lock을 요구한다.

## 보고서 읽기

- `required_document_recall`: 반환된 근거에 필요한 문서가 있는가.
- `cited_document_recall`: 답변이 실제로 인용한 문서가 필요한 문서를 덮는가.
- `claim_citation_coverage`: 주장에 등록된 인용 ID가 붙었는가. 의미 지지와 다르다.
- `semantic_quality`: 별도 Judge의 판단. 미실행·오류는 정답으로 채우지 않는다.
- `final_turns`, `judge_coverage`: 마지막 턴 중 평가가 실제로 반환된 범위.
- `usage_observed_runs`: 토큰 사용량이 확인된 실행 수. 누락은 0토큰이 아니다.
- `draft_evaluations`: 사람 검수 전 평가 초안으로 계산한 최종 턴 수.

“더 많은 Agent가 더 좋다”를 결론으로 미리 정하지 않는다. 어떤 사례의 누락이 줄었고
어떤 추가 비용·실패가 생겼는지 원문과 trace를 함께 설명한다.

모델 없이 수행하는 예측·원문 대조·평가 범위 확인 활동은 [WORKSHEET 선택 확장](../WORKSHEET.md)을 따른다.
