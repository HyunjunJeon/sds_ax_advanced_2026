# 공식 원문 스냅샷 — 2026-10-02

- `sources/`: 고정 commit/tag의 공식 변경 이력과 릴리스 원문.
- `documents/`: 원문의 연속 행을 그대로 발췌한 검색 대상 9개.
- `manifest.json`: 출처 URL, 버전, 공개일, 수집일, 원문·발췌 SHA-256, 행 범위.
- `catalog.json`: 검색용 고객·기준일·문서 메타데이터.
- `cases.jsonl`: 한국어 질문 12개. 후속 질문은 같은 세션에서 실행한다.
- `gold.jsonl`: 사후 평가 전용 AI 작성 초안. Agent 입력에 포함하지 않는다.
- `licenses/`: DeepAgents MIT 및 OpenViking Apache-2.0 고지. 원문 저작권은 각 권리자에게 있다.

원문 2개의 출처와 추출 좌표는 `manifest.json`을 기준으로 한다. 원문의 영어를 번역해 대체하지 않았다.
Day02의 `scripts/build_official_snapshot.py`가 수집·발췌하며 기존 디렉터리는 덮어쓰지 않는다.
Day03은 이 폴더를 `vendor/day02/data/`에 복사해 별도 프로젝트로 사용한다.

평가 초안의 `review_status=draft`는 사람의 검수가 아니다. 강사는 기대 문서·기대 사실을
원문과 대조한 뒤 검수 상태와 실제 담당자·근거를 기록한다. 검수 전 수치는 잠정 지표다.
검색용 `status=approved`는 공식 발표 자료라는 분류이며 평가 초안의 검수 완료를 뜻하지 않는다.

기준일 이전 문서는 고정 변경 이력의 릴리스 날짜로 필터링한다. 과거 웹페이지 전체를
그 시점의 바이트로 복원했다는 뜻은 아니다. 해시 일치는 사실성·완전성을 보증하지 않는다.

수업 실행 안내: Day02 `docs/OCTOBER_2026.md`, Day03 `docs/OCTOBER_2026.md`.
