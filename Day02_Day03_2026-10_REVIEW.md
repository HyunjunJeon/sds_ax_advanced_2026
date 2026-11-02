# Day02·Day03 개선 결과 — 2026-10-02

## 적용 결과

실습 코드·의존성·공식 원문 코퍼스·평가·안내 문서에 반영했다. 기존 업무 코퍼스가 기본값이며,
공식 원문은 선택 확장이다. 실제 모델 품질 비교와 평가 초안의 사람 검수는 아직 완료하지 못했다.

| 항목 | 변경 전 | 적용 후 | 근거 |
|---|---|---|---|
| DeepAgents | 0.7.13 | 0.7.21 | `Day02/pyproject.toml:12`, `Day03/pyproject.toml:6` |
| OpenViking | 0.4.16 | 0.4.22 | `Day02/runtime/openviking/pyproject.toml:5` |
| Day03 LangChain / Core | 기존 lock | 1.4.3 / 1.6.6 | `Day03/pyproject.toml:7` |
| 공식 원문 | 없음 | 2개 원문·9개 발췌·12개 사례 | `Day02/data/official-2026-10/README.md:3` |
| Day02 답변 사후 평가 | 검색 recall 중심 | 인용 구조·인용 문서 recall·독립 Judge·평가 누락 | `Day02/src/day02/evaluation.py:23` |
| Day03 평가 | 기존 구조 비교 | 마지막 턴 평가·초안 표시·Judge 범위·usage 누락 | `Day03/common/evaluation.py:91` |

각 프로젝트와 OpenViking 런타임의 lock을 갱신하고 의존성 해석 기준일을 고정했다.
코퍼스 로더는 원문·발췌·catalog 해시 및 연속 행 좌표를 검증한다. Day03에는 같은 파일을 동봉했고
두 사본의 바이트 일치를 확인했다. 근거: `Day02/src/day02/corpus.py:67`.

Day02는 02 적재, 03 검색, 04 답변, 09 비교, 13 기존 결과 분석에 코퍼스 선택을 연결했다.
Day03은 `LabConfig.corpus`와 별도 workspace를 사용하고 다른 코퍼스가 섞인 작업 영역은 거절한다.
실행 안내: [Day02 확장 실습](Day02/docs/OCTOBER_2026.md), [Day03 확장 실습](Day03/docs/OCTOBER_2026.md).
학생 TODO·예산 한도·공개 과제 테스트는 변경하지 않았다.

## 검증 기록

2026-10-02, 각 Day의 환경에서 실행했다. 유료 실행의 실패 행도 그대로 보존했다.

| 검사 | 결과 | 범위·한계 |
|---|---|---|
| 변경 전 제공 코드 회귀검사 | Day02 40 / Day03 30 통과 | 기존 기준선 |
| 변경 후 `uv run --locked pytest -q` | Day02 **56 통과** / Day03 **36 통과** | Day02 PyMuPDF SWIG 관련 deprecation 경고 7건 |
| 변경 Python 파일 Ruff | 통과 | Day03은 설치된 Day02 Ruff 실행 파일로 검사 |
| 공식 코퍼스 오프라인 검색 | 24행, 오류 0 | 12사례 × bounded/fixed, BM25, 각 1회 |
| 공식 코퍼스 잠정 recall@6 | 두 청킹 모두 0.9 | AI 작성 정답 초안 기준, 답변 품질 점수가 아님 |
| 기본 business 오프라인 검색 | 완료 | 기본 실행 경로 회귀 확인 |
| Day03 local 적재·재사용·기준일 필터 | 통과 | 회귀 테스트에 포함 |
| OpenViking 실제 0.4.22 + 로컬 모의 모델 | 인증·적재·조회·재사용·find·grep 통과 | 합성 임베딩/요약, 품질 비교 아님 |
| Day03 실제 모델 기준선 2사례 | **둘 다 인증 오류** | Judge 미실행. 성공·0비용·보류로 처리하지 않음 |

OpenViking 계약 검증은 `Day02/`에서 `uv run --locked python scripts/verify_openviking_contract.py`로
재실행할 수 있다. 임시 저장소와 로컬 모의 모델만 사용한다. 구현: `Day02/scripts/verify_openviking_contract.py:55`.
기존 0.4.16 운영 데이터의 마이그레이션, 다른 OS, 실제 임베딩 검색 품질까지 검증한 것은 아니다.

로컬 실행 식별자(생성 결과는 Git 제외):

- 공식 검색: `Day02/outputs/rag-comparison/20261002T102731255967Z/`
- 기본 업무 검색: `Day02/outputs/rag-comparison/20261002T103433382912Z/`
- 실제 모델 인증 실패: `Day03/outputs/rag-comparison/20261002T102906329651Z/`

## 남은 검증

1. 수강생 또는 강사가 `Day03/.env.example`을 참고해 인증 정보를 직접 확인한다. 키 값은 공유하지 않는다.
2. 강사가 공식 원문과 기대 사실을 대조해 `gold.jsonl`의 초안을 검수한다. 현재 `draft` 상태를 유지했다.
3. 인증 해결 후 소규모 기준선 실행, 이어 같은 사례·예산·코퍼스의 반복 비교를 한다.
   05·07 구현을 마친 뒤 전체 7구조를 비교한다. 실패 행과 평가 누락을 보존한다.

현재 결과로 “답변 정확도가 올랐다”거나 “멀티에이전트가 더 좋다”고 결론 내릴 수 없다.

## 공식 변경 근거

- [DeepAgents 0.7.21 변경 이력, 고정 commit](https://github.com/langchain-ai/deepagents/blob/4394bcd00b8eb46e7c423939643a0dfcfb5d8773/libs/deepagents/CHANGELOG.md): blob·파일 읽기·Context·하위 Agent 상태 변경을 원문으로 동봉했다.
- [OpenViking 0.4.22 릴리스](https://github.com/volcengine/OpenViking/releases/tag/v0.4.22): sessions used API 제거, cosine 점수 범위, ACL, 메모리 추출 실패 상태 변경을 확인했다. 현재 클라이언트는 제거된 API를 사용하지 않는다.
- [LangChain 멀티에이전트 안내](https://docs.langchain.com/oss/python/langchain/multi-agent): 정보 전달과 호출·토큰 비용을 비교 설계에 반영했다.

공개일과 수집일을 분리하고 commit/tag·원문 바이트·SHA-256·발췌 행 좌표를 기록했다.
영어 공식 원문에 한국어 질문을 붙였다. `gold.jsonl`은 Agent 입력에 주지 않는 사후 평가 초안이며,
사람 검수 전 지표는 잠정치다. 역사적 사례는 고정 changelog에 적힌 날짜로 필터링한 것으로,
당시 웹페이지 전체의 바이트를 복원한 자료는 아니다. 라이선스 고지는 코퍼스 `licenses/`에 있다.


## 추가 완료 — 모델 호출 없는 수업 준비

2026-10-02 추가 요청에 따라 다음을 완료했다. 이번 작업에서는 실제 모델·임베딩·Judge API를 호출하지 않았다.

1. **12개 사례 원문 재대조:** [강사용 검수표](Day02/docs/OCTOBER_REVIEW.md:13)에 발췌/원문 행 좌표,
   적용 조건, 질문·기대 사실 보완 제안을 기록했다. ACL 생성 조건, commit의 변경 없음 확인 주체,
   미래 릴리스 질문의 가정 표현을 보완 후보로 남겼다. gold는 draft를 유지했고 자료를 임의 승인하지 않았다.
2. **검색 누락 분석:** [검색 진단](Day02/docs/OCTOBER_RETRIEVAL_AUDIT.md:31)에서 `tech-isolated`의 누락을
   단일 문서 색인의 음수 BM25 점수와 양수 점수 필터로 좁혔다. 24행 검색 순위는 기존 결과와 모두 같았다.
   재실행 가능한 진단 스크립트와 해시·점수를 포함한 JSON을 동봉했다. 검색 정책 변경은 후속 통제 실험이다.
3. **WORKSHEET 연결:** [Day02](Day02/WORKSHEET.md:147), [Day03](Day03/WORKSHEET.md:163)에
   예측 → 실행 → 근거 확인 → 설명 및 빈 기록표를 추가했다. 기존 채점 기준과 학생 구현 지점은 유지했다.
4. **모의 응답 검증 및 보완:** `Day02/tests/test_answer_evaluation_runner.py`에 6개 검사를 추가했다.
   인증 실패, Judge 생성/호출/파싱 오류, 후속 턴·반복별 세션 격리, 사용량 일부 누락을 검증한다.
   Judge 생성 실패도 행에 보존하도록 수정했고, Agent 토큰 사용량이 누락되면 합계를 null로 남긴다.

최종 검증: 각 Day에서 `uv run --locked pytest -q` 실행 → **Day02 56 / Day03 36 통과**.
추가·변경 Python 파일 Ruff 및 `git diff --check` 통과. 두 Day의 공식 코퍼스 사본도 바이트 일치 확인.
Day02에는 기존 PyMuPDF SWIG deprecation 경고 7건이 남아 있다.

강사의 사람 검수와 실제 모델 품질 비교는 위 오프라인 작업으로 대체되지 않는다.
