# 2026-10 공식 원문으로 RAG 확장하기

기준일: 2026-10-02. 00→06의 기본 실습과 07·08의 구현 과제를 기존 번호 순서로 진행한다.
아래 코퍼스는 같은 검색·인용 경로에 연결하는 확장이다. 가상 업무 규정의 날짜·정답을 바꾸지 않는다.

## 무엇을 배우는가

- 공개일과 수집일은 다르다. 기준일 이전에 공개된 발췌만 검색 대상이 된다.
- 최신 원문도 URL만 저장하면 나중에 바뀔 수 있다. commit/tag, 원문 바이트, 발췌 행 좌표와 해시를 함께 기록한다.
- 검색에 필요한 문서가 나왔는지와 답변이 그 문서를 정확하게 인용했는지는 따로 평가한다.

## 자료

`data/official-2026-10/`의 `manifest.json`은 공식 원문 2개와 연속 행 발췌 9개를 기록한다.
`catalog.json`은 검색용 메타데이터, `cases.jsonl`은 질문 12개, `gold.jsonl`은 사후 평가 초안이다.
원문은 영어 변경 이력과 영문 릴리스 절이며 질문은 한국어다. 원문 안의 코드 예제는 실행 지시가 아니다.

`gold.jsonl`의 `review_status=draft`는 AI가 발췌에 대조해 작성했다는 뜻이며 사람의 검수가 아니다.
강사는 `source_documents`와 기대 사실을 대조하고 검수 이유·담당자를 실제 확인 뒤 기록한다.
보고서는 초안 기준의 결과를 잠정 지표로 표시한다. 공식 배포된 문서를 뜻하는 catalog의
`status=approved`와 평가 초안의 검수 상태를 혼동하지 않는다.

역사적 사례는 고정 changelog에 적힌 릴리스 날짜로 문서를 필터링한다.
당시 웹페이지 전체의 바이트를 복원한 자료라는 뜻은 아니다. 근거 없는 미래 기능 질문은 보류한다.

## 순서대로 실행하기

모든 명령은 `Day02/`에서 실행한다. 00은 원문 해시·좌표도 검사하며 모델을 호출하지 않는다.

```bash
# 설치는 저장소 루트의 `uv sync` 한 번으로 끝난다. 여기서 `uv sync`를 실행하지 않는다.
uv run python 00_prepare.py
uv run pytest -q
```

01에서 원문·청크·표 좌표를 확인한 뒤, 준비된 OpenViking 서버에 02로 적재한다.
첫 적재는 9개 발췌의 요약·임베딩 API를 호출한다. 재실행은 검증된 원문을 재사용한다.

```bash
uv run python 02_ingest.py --corpus official-2026-10
uv run python 02_ingest.py --corpus official-2026-10 --expect-reused
uv run python 03_search.py --namespace official-2026-10 --entity 공통 --as-of 2026-10-02 --question "OpenViking 0.4.22 cosine score_threshold" --extra-query "cosine ranking thresholds"
uv run python 04_rag_with_skills.py --namespace official-2026-10 --entity 공통 --as-of 2026-10-02 --format auto --question "OpenViking 0.4.22의 cosine 점수와 임계값은 어떻게 바뀌었나요?"
```

03은 검색 API, 04는 모델 API를 사용한다. 04의 답변은 현재 턴 근거·인용 구조·의미 지지 검사를 거친다.
05의 후속 질문은 `day02 ask`의 같은 `--session`과 `--namespace official-2026-10`을 사용해 확인할 수 있다.
06의 멀티모달 자료는 기존 샘플을 사용하고, 원문 좌표와 시각 관찰의 차이를 계속 확인한다.

09는 파일 안 `CORPUS = "official-2026-10"`으로 바꾼 뒤 실행한다.
기본 BM25 비교는 모델·서버를 호출하지 않는다. `SERVER=True`는 별도로 02 적재가 필요하다.
13은 선택한 코퍼스의 평가 자료와 원문 해시를 대조한다. 다른 원문으로 실행한 결과를 구조/검색 변경의 효과로 비교하지 않는다.

```bash
uv run python 09_compare.py
```

04까지 완료한 뒤 답변 사후 평가를 하려면 다음을 실행한다. 기본은 긍정 질문·미공개 미래 질문 각 1건이다.
이 스크립트는 09의 청킹·검색 변형을 적용하는 실행기가 아니다. 현재 `ask()` 경로를 평가한다.

```bash
uv run python scripts/evaluate_answers.py
```

`CORPUS`, `CASE_IDS`, `REPEATS`, `JUDGE`는 스크립트 상단 상수다.
여러 턴은 같은 세션에 이어가고 마지막 질문만 기대 사실로 평가한다. 실패·Judge 오류도 행에 남긴다.
API 호출 한도와 별도 Judge 규모를 실행 전에 출력한다.

## 결과를 설명하는 질문

1. 기준일을 2026-09-02로 바꾸면 0.7.21 문서가 왜 제외되는가?
2. `required_document_recall=1`인데 `cited_document_recall=0`일 수 있는가?
3. 인용 ID가 유효해도 cosine 임계값이 자동 보정된다고 답하면 왜 오답인가?
4. `judge_coverage=0`과 정답률 0은 어떻게 다른가?
5. 모델 호출 실패를 답변 보류나 0비용으로 집계하면 무엇이 왜곡되는가?

## 버전 변경 근거

- [DeepAgents 0.7.21 기준 changelog](https://github.com/langchain-ai/deepagents/blob/4394bcd00b8eb46e7c423939643a0dfcfb5d8773/libs/deepagents/CHANGELOG.md): 도구 결과·파일 읽기·하위 Agent 상태 전달 관련 변경을 실습 원문으로 사용한다.
- [OpenViking 0.4.22](https://github.com/volcengine/OpenViking/releases/tag/v0.4.22): 세션 used API 제거, cosine 점수 범위, ACL 변경을 확인한다. 과거 성공 응답·임계값을 새 버전에 그대로 적용하지 않는다.

새 자료 수집은 강사용 `scripts/build_official_snapshot.py`에서 새 `CORPUS` 이름으로 수행한다.
기존 스냅샷은 덮어쓰지 않는다. 원문 재배포 고지는 `licenses/`에 동봉했다.

## 모델 없이 확인할 자료

- [강사용 사례 검수표](OCTOBER_REVIEW.md): 12개 사례의 원문 행 좌표·적용 조건·보완 제안. 사람 검수는 미완료다.
- [오프라인 검색 진단](OCTOBER_RETRIEVAL_AUDIT.md): 단일 문서 색인의 음수 BM25 점수와 누락 원인.
- [WORKSHEET 선택 확장](../WORKSHEET.md): 예측 → 실행 → 근거 확인 → 설명 기록 양식.
- `uv run --locked pytest -q tests/test_answer_evaluation_runner.py`: 모의 응답으로 실패 보존·후속 턴·usage 누락 검사.

답변 평가 summary의 `agent_input_tokens`·`agent_output_tokens`는 모든 Agent 호출의 usage가 확인될 때만
합산한다. 한 실행이라도 누락되면 null이며 `usage_observed_runs`·`usage_missing_runs`를 함께 읽는다.
Judge 사용량은 행별 `evaluation.judge_usage`로 별도 기록한다. Agent 토큰 합계가 전체 비용은 아니다.
