# Day03_new 감사 증거 (`docs/audit/`)

## 이 폴더는 무엇인가

`Day03_new/README.md`, `Day03_new/AGENTS.md`, `Day03_new/docs/DESIGN.md`가 적은 숫자와 판단(비용, 실행 기록, 실제 모델 행, 반증 표)의 근거가 되는 **감사 작업 기록**을 저장소에 보존한 폴더입니다. 작업하는 동안 이 기록들은 세션 스크래치패드에만 있었고, 세션이 끝나면 사라집니다. 문서의 주장을 나중에도 확인할 수 있게 익명화해서 옮겨 두었습니다.

- 수업 자료가 아닙니다. 수강생이 읽을 필요는 없습니다.
- 모델 호출과 EXA 호출은 이 폴더를 만들 때 하지 않았습니다. 여기 있는 기록은 이미 끝난 실행의 결과물입니다.

`tools/`에는 문서 인용·비용 검사기(`check_citations.py`, `check_costs.py`)와 결함 주입 도구(`rows.py`, `falsify6.py`, `mkcopy.py` 등)가 있고 안내는 `tools/README.md`입니다. 이 파일들은 세션 원본에서 기기 고유의 절대 경로를 스크립트 위치에서 계산한 경로와 명령행 인자로 바꿨고, 그 밖에는 결함 표 여섯 개를 `row_tables.py`로 옮기고, 정답표(`gold.jsonl`)를 `falsify6.py`의 `diff`와 `hashtree.sh`의 마지막 해시 줄에서 빼고, `mkcopy.py`가 `Day03_new` 안의 작업 폴더를 거부하게 하고, 검사기가 현재 폴더의 `./Day03_new`를 기본값으로 찾던 것을 없애고 `check_citations.py` 자체 시험의 임시 폴더를 도구 폴더 안에서 운영체제 임시 폴더로 옮기고, 쓰이지 않던 이름(`rows.py`의 `section`, `NOTE_A`, `DIFFERS`, `build_notes6.py`의 `same_tree`, `report.py`의 `cnt`)을 지운 것이 다릅니다. 사용법과 검사기가 보지 못하는 것은 `tools/README.md`에 있습니다. 2026-11-02에 더한 `tools/sync_probe2.py`(동기화 전후의 검색 결과를 모델 없이 비교)는 스크래치패드 원본과 바이트까지 같고, 원본에 기기 경로가 없어 고친 곳이 없습니다.

## 읽는 법

- 노트(`*-notes.md`)는 감사 단계가 **영어로 쓴 작업 기록**입니다. 쓸 당시의 첫 판단을 그대로 둡니다. 나중에 틀린 것으로 밝혀진 문장도 고치지 않았고, 고칠 것은 아래 `## 정오표`에 적었습니다.
- 노트 안의 `P/…`는 작업 당시 스크래치패드 폴더를 줄여 쓴 말입니다. 이 폴더에 같은 이름의 파일이 있으면 그것이 복사본입니다. `P/c2-code-hashes.txt`, `P/exa_id_forms/record_check.txt`, `P/live-before-c2/`처럼 이 폴더에 없는 `P/` 파일은 보존하지 않았으므로, 그 인용은 이 폴더만으로는 확인할 수 없습니다.
- 노트의 `file:line` 인용은 **노트를 쓴 시점의 코드** 기준입니다. 현재 코드와 다를 수 있습니다. 코드와 노트가 다르면 코드가 정답입니다.
- "B1"은 실행 `dag_mvxjjtgg_181ytn`(01~05 재실행), "C2"는 실행 `dag_mvxqwuxv_oit10v`(04·05 재실행)입니다. 각 노트의 첫 줄에 같은 이름이 있습니다.
- 2026-11-02에 더한 노트 넷(`sync-copy-notes.md`, `sync-equivalence-notes.md`, `falsify-7-notes.md`, `clean-clone-3-notes.md`)은 `rag_lab` 동기화(실행 `dag_mvyi94ja_vi2zuw`)의 기록입니다. 이 중 `sync-equivalence-notes.md`와 `clean-clone-3-notes.md`는 한국어이고(위 "영어로 쓴"에 들지 않습니다), 나머지 둘은 영어입니다. 이 넷의 `P/…` 가운데 이 폴더에 없는 것은 보존하지 않았습니다: `P/s2-*.jsonl`(각 약 6.8 MB), `P/sync_probe.py`, `P/sync_queries.py`, `P/sync-old.jsonl`, `P/sync-new.jsonl`, `P/sync-queries.json`, `P/sync-code-hashes.txt`, `P/sync-before/`, `P/sync-try/`, `P/falsify-7-*`(작업 폴더, 스냅샷, 로그, 사전 등록), `P/clone3-*`(로그, 해시, 검사 스크립트). 그 인용은 이 폴더만으로는 확인할 수 없습니다.

## 파일별로 무엇을 증명하는가

### 실행 기록 (노트북 01~05, 호출 수·시간·토큰)

| 파일 | 증명하는 것 |
|---|---|
| `live-01-notes.md` ~ `live-05-notes.md` | B1 재실행에서 노트북 01~05(base와 exercises)의 모델 호출 수, 초, 토큰, `switched`, 그리고 그때 고친 마크다운 문장과 이유 |
| `live-04-c2-notes.md`, `live-05-c2-notes.md` | C2 재실행에서 04·05의 새 실행 기록, 저장된 관찰 문장이 새 기록에 아직 참인지의 확인, 05 셀 34 문장의 근거 |
| `preflight-c2-notes.md` | C2 재실행 직전의 코드 해시(`gate.py`, `exa.py`, `workers.py` 등)와 루트 `pyproject.toml`, `uv.lock` 해시. 이후 판단의 기준선 |
| `cost-report-b1.txt` | B1 재실행 직후 노트북별 비용 표 (`tests/cost_report.py` 출력) |
| `cost-report-c2.txt` | C2 재실행 직후 노트북별 비용 표. 이 폴더를 만들 때 현재 `tests/cost_report.py` 출력과 한 글자도 다르지 않음을 확인. 2026-11-02 전체 재실행 뒤에는 현재 출력과 다르다(지금 출력은 아래 `cost-report-rerun-20261102.txt`) |
| `live-rerun-20261102-notes.md` | 2026-11-02 Supervisor 용어 수정 뒤 13개 기록을 모두 다시 돌린 기록. 다시 돌린 이유, 순서와 시각, 실행 당시 코드 해시 27개, 기록별 전후 호출 수·초·비용, 감사 결과, 지출, 이전 기록을 남긴 곳 |
| `cost-report-rerun-20261102.txt` | 전체 재실행 직후 노트북별 비용 표 (`tests/cost_report.py` 출력). 합계 996회, 3419.6초, 6.9435 USD 2026-11-03 재실행 뒤에는 **현재 출력이 아니다**(지금 출력은 `cost-report-rerun-20261102b.txt`). |
| `live-rerun-20261102b-notes.md` | 2026-11-03 자동 `general-purpose`를 끈 뒤 13개 기록을 모두 다시 돌린 기록. 다시 돌린 이유, 명령과 순서와 창(00:05:29~01:03:38 KST), 이전 기록 보존 위치, 코드 해시 재확인, 기록별 전후 호출 수·초·비용, 감사, 새 행의 `general-purpose` 0개, 지출, 한계 |
| `rerun-20261102b-facts.md` | 위 재실행의 기록 직접 집계: 합계, 시각, 감사 셀, 켜는 칸, 같은 셀 변동, EXA, `general-purpose` 행 대조, 저장본·실행본 비교, 노트북 크기 |
| `rerun-20261102b-code-hashes.txt` | 위 재실행 시작 때 코드 28개 파일(`mas_lab`, `rag_lab`, 노트북)의 sha256 앞 12자리 |
| `cost-report-rerun-20261102b.txt` | 위 재실행 직후 노트북별 비용 표(`tests/cost_report.py` 출력). 합계 1022회, 3357.1초, 7.1327 USD. 현재 출력 |
| `stale-records-notes.md` | 00~03과 06의 저장된 실행 기록이 `gate.py`, `workers.py`, `exa.py` 수정 앞의 기록이어도 기록이 달라지지 않는 이유 |

### 실제 모델 행과 반복 관찰

| 파일 | 증명하는 것 |
|---|---|
| `id-spelling-rows-notes.md` | `p7001`, `P7001`, `p-7001` 세 철자를 현재 `gate.py`로 실제 모델에 넣은 행 세 개의 기대, 결과, 판정. 세 행 모두 `denied`, 모델 호출 합계 25회 |
| `id-spelling-rows-notes.pre-results.md` | 위 노트의 결과를 붙이기 **전** 복사본. 기대와 판정 규칙을 결과를 보기 전에 고정했다는 증거 |
| `rows/` | 위 세 행의 실제 행 파일과 실행 상태 (아래 따로 설명) |
| `new-question-3-notes.md` | 새 질문 감사 3차: 현재 `gate.py`에서 `hybrid`로 13행(R1~R8, N1~N5). N5(`p7001`)가 철자 구멍으로 이어진 근거 |
| `ops-log-notes.md`, `ops_log_runs.json` | `complex-ops-log`를 `hybrid`로 아홉 번 반복한 첫 묶음(`checked_worker` 도입 직후)과 그 행 id·호출 수·초 |
| `ops-log-2-notes.md`, `ops_log2_runs.json`, `ops_log2_raw.jsonl` | 같은 반복의 두 번째 묶음, 앞 묶음과의 비교, Worker가 실제로 돌려준 원본 결과(raw) 14건 |

### 코드 수정의 근거와 반증

| 파일 | 증명하는 것 |
|---|---|
| `gate-id-forms-notes.md` | 환불 쓰기 관문이 `p7001`, `P7001`, `p-7001`을 `P-7001`로 읽도록 고친 앞뒤와 테스트 |
| `exa-id-forms-notes.md` | EXA 질의 경계(`INTERNAL_PATTERN`)가 같은 철자와 조사가 붙은 번호를 막되 전에 막던 것도 계속 막도록 고친 과정. 1차 시도가 왜 부족했는지 포함 |
| `worker-refs-precision-notes.md` | `checked_worker`가 라벨이 붙은 근거 id를 되살리고 빈 근거를 이 Worker 자신의 도구 결과로 채우는 동작과 그 테스트 |
| `replay-4-notes.md` | 저장된 실제 행 422개를 현재 관문에 다시 통과시켜도 뒤집힌 행이 0이라는 재생 결과 |
| `edge-legend-notes.md` | 04 노트북에 넣은 점선·실선 설명 문장 두 개와 그 근거(`draw_mermaid()`의 `-.->`와 `-->`) |
| `graph-render-notes.md`, `graph-render.png` | 실제 `build_hybrid` 그래프가 04의 그림대로 그려진다는 확인(노드 13개, 간선 19개)과 그 그림 |
| `falsify-5-notes.md` | 최종 트리에서 결함 주입 표를 돌린 결과 (테스트 495개 시점) |
| `falsify-6-notes.md` | 당시 트리(`rag_lab` 동기화 앞)에서 결함 주입 표 전체를 다시 돌린 결과: 173행(결함 172 + 정상 1), 172개 모두 잡힘, 생존 0. 정상 복사본 610개 중 608개 통과와 기준선 두 개 빨강 |

### 검증과 정리

| 파일 | 증명하는 것 |
|---|---|
| `verify-b1-notes.md` | B1 재실행 기록이 실제이고 완결이라는 확인(호출 1,120회, 약 USD 6.85). 판정은 FAIL이며 이유 둘 중 하나가 아래 "알려진 빨간 테스트"입니다 |
| `verify-c2-notes.md` | C2 재실행 뒤 코드 해시 37개 중 37개 일치, 어떤 노트북 셀이 어떤 기록보다 늦게 바뀌었는지의 시각 대조, 키 검사 |
| `clean-clone-notes.md` | 저자의 작업 트리를 새 `git` 저장소로 만들어 복제한 사본에 빈 uv 캐시로 설치해 통과한 기록 (`Clean clone: PASS`). 대상은 원격에 올라간 커밋이 아니라 그때의 작업 트리입니다 |
| `clean-clone-2-notes.md` | 같은 절차를 2026-11-02의 작업 트리에서 되풀이한 기록 (`Clean clone: PASS`, 실행 `dag_mvy51tor_2og7v6`). 새 `git` 저장소로 만든 사본에 빈 uv 캐시로 `uv sync --locked`가 345개 패키지를 설치했고, pytest는 610개 중 608개 통과와 2개 실패(`[retrieval.py]`, `[evidence.py]`, 아래 "알려진 빨간 테스트"), 노트북 검사기 7개 통과, 모델 호출 0회, EXA 호출 0회입니다. 복제본에는 `outputs`가 없어 `check_costs.py --self-test`가 종료 코드 1로 끝난 것과 그 원인 확인도 적혀 있습니다. 실제 키를 넣은 00-Setup 단계는 되풀이하지 않았습니다. 이 노트는 한국어로 쓰였고(위 "읽는 법"의 "영어로 쓴"에 들지 않습니다), 로그(`P/clone2-*.log`)는 보존하지 않았습니다 |
| `scratch-env-cleanup-notes.md` | 스크래치패드에 남아 있던 `.env` 복사본 하나를 지우고 전체를 다시 검사해 키가 0건임을 확인한 기록 |

### `rag_lab` 동기화 (2026-11-02)

`Day03_new/rag_lab`의 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 네 파일을 `Day02_new/rag_lab`과 같은 바이트로 맞춘 일의 기록입니다. 이 기록들은 동기화 **뒤**에 만들었고, 실행 기록(`outputs/live`, `outputs/runs`, 가장 늦은 것이 2026-11-01 21:26)은 동기화(2026-11-02 09:13) **앞**의 코드로 만들어졌습니다. 저자 결정(2026-11-02)으로 유료 재실행은 하지 않았습니다. 모델 호출과 EXA 호출은 0회입니다.

| 파일 | 증명하는 것 |
|---|---|
| `sync-copy-notes.md` | 네 파일의 복사와 `tests/test_layout.py:13`의 복사본 시험이 네 칸(`corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py`)이 된 것. 시험 611개 중 611개 통과와 0 실패(동기화 앞은 610개 중 608개 통과와 2 실패), 노트북 검사기 7개 통과, 감사 `AUDIT OK`, 코드 해시가 바뀐 파일이 정확히 네 개, 옮겨 간 줄 번호. 마지막 줄 `Sync copy: PASS` |
| `sync-equivalence-notes.md` | 동기화가 모델이 받는 검색 결과를 바꾸는지의 확인(`tools/sync_probe2.py`). 새 컨텍스트 검색 720개와 기본 한도 24,000바이트에서 쌓이는 검색 720개가 같고(차이 0), 3,000바이트로 넘침을 일부러 탄 780줄 중 73줄이 다르며 원인은 `_admit`. 저장된 행 1,893개에 넘침이 0건. 한계(저장된 모델 질의 없음, `read_more` 한 번씩, 모델 답 미확보)와 첫 탐침·둘째 탐침의 실수 |
| `falsify-7-notes.md` | 동기화 뒤 트리에서 결함 주입 표 전체를 다시 돌린 결과: 175행(결함 174 + 정상 1), 174개 모두 잡힘, 생존 0. 정상 복사본 세 번 모두 611개 통과, 0 실패. 새 행 `sy01`, `sy02`는 `[pipeline.py]`, `[evidence.py]` 칸을 잡고, `[retrieval.py]` 칸에는 따로 행이 없습니다. 마지막 줄 `Falsify 7: PASS` |
| `clean-clone-3-notes.md` | `clean-clone-2-notes.md`의 절차를 동기화 뒤의 작업 트리에서 되풀이한 기록. 새 `git` 저장소로 만든 사본에 빈 uv 캐시로 `uv sync --locked`가 345개 패키지를 설치했고, pytest 611개 중 611개 통과(네 복사본 칸 모두 통과), 노트북 검사기 7개 통과, 모델·EXA 호출 0회, 키 검색 0건. 키 없는 00-Setup은 `require_key()`에서 멈추고, `check_costs.py --self-test`는 사본에 `outputs`가 없어 종료 코드 1입니다(예상). 마지막 줄 `Clean clone: PASS` |
| `tools/sync_probe2.py` | 위 `sync-equivalence-notes.md`가 쓴 도구. 사용법은 `tools/README.md` |

### `rows/` (정확히 7개)

실제 모델이 `p7001`, `P7001`, `p-7001` 철자를 읽은 **유일한 증거**이고 다른 곳에는 없습니다. `Day03_new/outputs/runs/`는 커밋되지 않는 폴더라서 일부러 여기에 둡니다.

| 파일 | 내용 |
|---|---|
| `idspell_S1_idspell-lower-nohyphen.json` | S1 `p7001`: 행 전체와 `audit_name`, `question` |
| `idspell_S2_idspell-upper-nohyphen.json` | S2 `P7001` |
| `idspell_S3_idspell-lower-hyphen.json` | S3 `p-7001` |
| `idspell_total.json` | 세 행의 호출 수 합계(25)와 `status`, `outcome` |
| `0e114942fdd74647bbcab44007fe906f.json`, `930b14f9453046f5aef1f8ac9e4043e6.json`, `ca2787e30d2c42fe92fba7411c0aac74.json` | 위 세 행이 `outputs/runs`에 저장했던 행 파일 그대로(S2, S1, S3 순서) |

## 알려진 빨간 테스트 (2026-11-02 09:13에 해소)

`tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]`와 `[evidence.py]` 두 개는 **저자 결정**으로 `Day02_new` 세션이 끝날 때까지 빨간 채로 두었습니다. 다른 세션이 `Day02_new/rag_lab`을 고치고 있어서, 세션이 끝난 뒤에 복사본을 동기화하기로 했기 때문입니다. 이것은 결함이 아니었습니다. `verify-b1-notes.md`의 FAIL 판정 이유 1번, `falsify-6-notes.md`의 "기준선 두 개 빨강", `clean-clone-2-notes.md`의 610개 중 608개 통과와 2개 실패가 이 두 개입니다.

2026-11-02 09:13에 동기화(`sync-copy-notes.md`)로 두 칸이 초록이 되었고 `[pipeline.py]` 칸이 하나 늘어, 지금은 시험 611개가 모두 통과합니다. 위 세 노트와 이 날짜 앞의 다른 노트는 **동기화 앞의 상태**를 적은 기록이라 빨간 두 칸이 나오는 것이 맞고, 고치지 않았습니다.

## 익명화 규칙

복사본은 원본과 **아래 치환만** 다릅니다. 판단, 숫자, 문장은 하나도 바꾸지 않았습니다. 치환은 문자열 단위이고, `.json`과 `.jsonl`은 쓴 뒤에 전부 다시 파싱했습니다. `graph-render.png`는 바이트 그대로 복사했습니다.

| 원래 | 바뀐 토큰 | 치환 횟수 |
|---|---|---:|
| 스크래치패드의 작업 폴더(`phase3`) 절대 경로 | `<P>` | 12 |
| 그 상위 스크래치패드 절대 경로 | `<scratchpad>` (지시된 토큰 목록에 없어서 이 문서에서 정한 이름) | 2 |
| 저장소 절대 경로 | `<repo>` | 12 |
| 그 밖의 홈 폴더 아래 경로 | `<home>` | 0 |
| 세션 id | `<session>` | 0 (아래 설명) |
| Claude 프로젝트 폴더 이름 | `<claude-project>` | 0 (아래 설명) |
| 서브에이전트 transcript 파일 이름(`agent-` 다음에 16진수가 붙은 `.jsonl`) | `<transcript>` | 2 |
| 운영체제 임시 폴더의 절대 경로(`falsify-5-notes.md`, `falsify-6-notes.md`의 `pytest-of-` 앞까지) | `<tmp>` | 2 |
| 위 pytest 임시 폴더 이름에 든 로컬 사용자 이름 | `<user>` | 2 |

세션 id와 프로젝트 폴더 이름은 모두 스크래치패드 절대 경로 **안에** 있었고, 그 경로가 통째로 `<P>`와 `<scratchpad>`로 바뀌었기 때문에 따로 바뀐 횟수는 0입니다.

2026-11-02에 더한 `clean-clone-2-notes.md`도 같은 규칙으로 옮겼습니다. 치환은 3행의 `P = …` 한 곳(`<P>` 1회)뿐이고, 위 표의 횟수에는 들어 있지 않습니다. 세션 id와 임시 폴더의 사용자 번호는 그 경로 안에 있었고 경로가 통째로 `<P>`로 바뀌었습니다.

2026-11-02에 더한 `sync-copy-notes.md`, `falsify-7-notes.md`, `clean-clone-3-notes.md`도 같은 규칙으로 옮겼고 이 표의 횟수에는 들어 있지 않습니다. `sync-copy-notes.md`와 `clean-clone-3-notes.md`는 3행의 `P = …` 한 곳씩(`<P>` 각 1회), `falsify-7-notes.md`는 160행(행 b11)의 pytest 임시 폴더 한 곳(`<tmp>` 1회와 `<user>` 1회)이 바뀌었습니다. 세 파일 모두 바뀐 줄 수는 그 외에 없고, 마지막 줄(`Sync copy: PASS`, `Falsify 7: PASS`, `Clean clone: PASS`)은 원본과 같습니다. `sync-equivalence-notes.md`는 이 폴더에서 처음 쓴 노트라 치환이 없고, `tools/sync_probe2.py`도 원본에 경로가 없어 치환이 없습니다(바이트까지 같음).

일부러 그대로 둔 것:

- 실행 id(`dag_…`). 세션 id가 아닙니다.
- `알파`, `P-7001` 같은 수업 데이터의 고객 이름과 번호.

## 검사 기록 (이 폴더를 만들 때)

2026-11-01. 숫자만 적습니다. 비밀 값과 정답표 값은 적지 않았습니다.

- **키 검사.** `Day03_new/.env`와 `Day02_new/.env`에서 이름에 KEY·TOKEN·SECRET·PASSWORD가 든 항목의 값(12자 이상)을 프로세스 안에서만 읽어, 전체 값 3개와 끝 12자 3개를 이 폴더의 40개 파일(PNG 포함, `tools/`는 세지 않음, 바이트 단위)에 대 보았습니다. 전체 값 0건, 끝 12자 0건, 키 모양(접두어 뒤에 자격 증명 글자가 이어지는 꼴) 0건입니다. 접두어 낱말만 세면 4건이 나오는데 모두 `verify-c2-notes.md:130`의 한 줄이 "어떤 모양을 검사했는지"를 적은 말이고 뒤에 이어지는 글자가 없습니다. 같은 검사기가 양성 대조 파일(필요한 값과 키 모양을 모두 넣은 파일)에서는 전체 값 3건, 끝 12자 6건, 키 모양 5건을 찾았고 그 파일은 지웠습니다. 40개는 이 검사를 한 2026-11-01의 파일 수입니다. 2026-11-02에 더한 `clean-clone-2-notes.md`는 이 검사에 들어 있지 않습니다. 그 파일에는 키 모양과 32자 넘는 글자열 검색만 했고(긴 글자열은 시험 이름 하나와 `pyproject.toml`, `uv.lock`의 해시 둘뿐, 키 모양 0건), `.env` 값과의 대조는 하지 않았습니다. 그 노트 5절의 키 검사는 복제본 안(파일 47157개)을 본 기록입니다.
- **정답표 검사.** `Day03_new/data/gold.jsonl` 12행에 대해 (1) 한 행 전체 또는 `required_any` 목록을 그대로 옮긴 문자열이 있는지 봤고 0건입니다. (2) 같은 줄에 사례 id와 필수·금지 표현이 함께 나오는 줄이 18줄 있습니다. 그 줄들을 읽어 보니 모두 자동 검사가 출력한 `누락 사실` 목록이나 모델 답을 옮긴 문장이고 정답표를 옮긴 것이 아닙니다. 다만 몇 줄은 한 사례(`complex-double-pay`)에서 자동 검사가 "빠졌다"고 출력한 필수 표현을 적고 있어서, 그 사례의 필수 묶음 일부(한 줄에서 6개 중 최대 4개)가 이 폴더에서 읽힙니다. 이것이 부담스러우면 저자가 해당 줄을 가리면 됩니다.

2026-11-02 (동기화 기록을 더할 때). 숫자만 적습니다. 새 파일 다섯 개(`sync-copy-notes.md`, `sync-equivalence-notes.md`, `falsify-7-notes.md`, `clean-clone-3-notes.md`, `tools/sync_probe2.py`)와 `tools/README.md`를 봤고, 이 폴더는 이제 파일 58개(최상위 38, `rows/` 7, `tools/` 13)입니다.

- **경로 검색.** 기기 고유의 절대 경로(홈 폴더, 스크래치패드, 운영체제 임시 폴더), 세션 id, 저장소 폴더 이름, pytest 임시 폴더에 든 사용자 이름을 찾는 검색을 폴더 전체(58개)에 했고 걸린 파일이 0개입니다. 검색 패턴은 이 문서에 적지 않았습니다(적으면 이 문서가 걸립니다).
- **키 모양 검색.** 새 파일 다섯 개에서 `sk-` 접두어, `API_KEY`·`TOKEN`·`SECRET`·`PASSWORD`가 `=` 뒤에 값과 함께 나오는 꼴을 찾았고 0건입니다. 33자 넘는 글자열은 시험 이름, 식별자 둘(`approved-carried-through-a-handoff`, `trailing-letter-after-five-digits`), 경로 조각 둘(`clean-clone-3-notes.md`의 `.../clone3-dst/...`와 `sync-equivalence-notes.md`의 도구 경로), 해시(`sha256=` 6개와 `clean-clone-3-notes.md`의 루트 `pyproject.toml`, `uv.lock` 해시 2개)뿐이었습니다. `.env` 값과의 대조는 하지 않았습니다(이 단계는 `.env`를 읽지 않습니다). `clean-clone-3-notes.md` 5절의 키 검사는 복제본 안(파일 47173개)을 본 기록입니다.
- **정답표 검사.** `data/gold.jsonl`을 열어 대조하지는 않았습니다. 새 다섯 개 파일에 `누락 사실`, `필수 사실`, `required_any`, `금지 표현`이 든 줄이 0줄입니다. 이것은 정답표 값이 없다는 증명이 아니고, 자동 검사 출력이 옮겨 온 흔적이 없다는 확인입니다.
- **다시 센 숫자.** `sync-equivalence-notes.md`의 숫자는 `P/s2-*.jsonl` 다섯 개를 줄 단위로 다시 읽어 센 값입니다. 작업 지시의 숫자 하나(순위를 뒤집은 대조 780줄 중 723줄)는 다시 세지 못했고 그 노트 9절에 적었습니다.

## 정오표

2026-11-01. 아래는 노트 본문을 **고치지 않고** 따로 적는 정정입니다. 각 항목은 이 폴더의 파일과 현재 코드에서 다시 확인한 뒤 적었습니다.

### (a) `id-spelling-rows-notes.md` 판정 5번의 `INTERNAL_PATTERN`

- 어디: `id-spelling-rows-notes.md:154`의 판정 5번("EXA: none called")이 `exa.py:18`의 `INTERNAL_PATTERN`을 `\bP-\d+\b`로 인용합니다.
- 무엇이 틀렸나: 그것은 **옛 패턴**입니다. 현재 `Day03_new/mas_lab/exa.py:18`의 `INTERNAL_PATTERN`은 앞뒤에 영문자·숫자가 붙지 않은 `P-<숫자>`, `P<숫자 4자리 이상>`, `INV-…`, `INC-<숫자>`, `T-<숫자>`를 대소문자 구분 없이 읽는 다른 패턴입니다. 그 노트의 원본은 21:20:44에 저장되었고 `exa.py`는 그보다 앞서 바뀌었습니다(1차 수정은 19:37 이후, 마지막 수정은 20:04:21). 그래서 쓸 당시에도 현재 패턴이 아니었습니다. 또 옛 패턴 자체도 `\bP-\d+\b`가 아니라 `\b(?:P-\d+|INV-[\w-]+|INC-\d+|T-\d+)\b`였고(`exa-id-forms-notes.md:11-14`에 옛 패턴이 그대로 적혀 있습니다), 노트의 인용은 그 중 P 부분만 떼어 옮긴 꼴입니다.
- 확인: `exa.py`의 현재 해시 앞 8자리는 `c8f238a9`이고 C2 코드 해시표와 같습니다. `verify-c2-notes.md:11`과 `:25`가 그 표 37개 중 37개 일치를 기록합니다. 해시표 파일 자체(`P/c2-code-hashes.txt`)는 보존하지 않았지만, 이 폴더를 만들 때 현재 트리에 같은 표를 다시 대 보니 37개 모두 일치했습니다.
- 결론은 그대로 유지: 이 세 행에서 EXA를 부르지 않았다는 판정은 패턴과 상관없이 섭니다. 근거는 셋입니다. `mas_lab/workers.py:25-30`의 `ROLE_TOOLS`에 웹 도구가 없습니다. `mas_lab/exa.py`를 가져오는 곳은 `mas_lab/research.py:16` 하나입니다. `rows/`의 세 행 파일의 `tools_called`에는 `lookup_payments`, `search_knowledge`, `read_evidence`뿐입니다. 세 가지 모두 현재 파일에서 다시 확인했습니다.
- 같은 인용이 `gate-id-forms-notes.md:103`에도 있습니다. 그 노트는 19:36:36에 저장되었고, 옛 `exa.py`의 복사본(`exa.before.py`)은 그 뒤 19:37:04에 만들어졌으며 1차 수정의 산출물은 19:38 이후에 나옵니다. 따라서 그 노트가 쓰일 때 `exa.py`는 아직 옛 패턴이었고 "`p7001`은 막지 못한다"는 요점은 맞았습니다. 다만 인용한 `\bP-\d+\b`는 옛 패턴의 P 부분만이라는 점은 같습니다. 이 시각들은 스크래치패드 파일의 수정 시각이고, 그 파일들(`exa.before.py` 등)은 이 폴더에 보존하지 않았습니다. 옛 패턴 문자열은 `exa-id-forms-notes.md:11-14`로 확인됩니다.

### (b) `인용 문서` 실패 행 수: 3개와 4개

- 어디: `ops-log-notes.md`는 아홉 행 중 `인용 문서`가 실패한 행을 5·6·7번 **세 개**만 이름 붙여 말합니다(`:59`). 같은 파일의 표는 2번 행의 실패 칸에도 `인용 문서`를 적습니다(`:18`). 합계 줄은 자동 검사 통과를 "9행 중 5행"이라 적어(`:27`) 실패는 4행입니다. `ops-log-2-notes.md`는 같은 아홉 행을 **네 개**로 셉니다(`:96`, `:120`).
- 정오: 두 노트는 모순이 아니라 세는 대상이 다릅니다. 실패 칸에 `인용 문서`가 있는 행은 4개(2, 5, 6, 7번)이고, 그중 2번은 `budget_exceeded`로 끝나 답이 없는 행입니다. 답이 있는 행으로는 3개(5, 6, 7번)입니다. `ops-log-notes.md`의 "3"은 답이 있는 행만 센 값이므로 4행 전체의 값으로 읽으면 틀립니다.

### (c) 루트 `pyproject.toml`과 `uv.lock`이 "바뀌지 않았다"는 앞선 검토 노트

- 어디: 앞선 검토 노트는 이 폴더에 없습니다. DAG 실행 `dag_mvwjfg3r_ks78yp`의 `review-spec` 보고서 31행이 "루트 `pyproject.toml`과 `uv.lock`은 10-31 16:10 이후 바뀌지 않았다"고 적습니다.
- 무엇이 틀렸나: 시각이 틀렸습니다. 두 파일의 수정 시각은 `pyproject.toml` 2026-10-31 16:10:30, `uv.lock` 2026-10-31 16:11:57입니다. `uv.lock`은 "16:10" 뒤에도 쓰였습니다.
- 내용이 안 바뀌었다는 근거는 해시입니다. `preflight-c2-notes.md:13-14`, `verify-b1-notes.md:59`, `clean-clone-notes.md:57-58`이 같은 값(`59dfcfc2…`, `e39fee03…`)을 적고, 이 폴더를 만들 때 현재 파일에서 다시 계산한 앞 12자리도 같았습니다. 즉 **내용은 그대로, 시각은 정정**입니다.
- 확인하지 못한 것: 누가(앞선 실행인지 사람인지) 그 두 파일을 그 시각에 썼는지는 알 수 없습니다. 수정 시각은 이 감사 기록들보다 하루 앞선 2026-10-31입니다.

### (d) 시점이 지난 서술 (오류는 아님)

- `verify-b1-notes.md:118`은 스크래치패드의 `.env` 복사본을 그대로 두었다고 적습니다. 그 뒤 `scratch-env-cleanup-notes.md`가 그 파일을 지우고 전체를 다시 검사해 키가 0건임을 확인했습니다. `verify-b1-notes.md`의 FAIL 이유 2번(키가 든 파일 1개)은 그래서 해소되었습니다.

### (e) 그 밖에 틀린 것

찾지 못했습니다. 다시 대 본 것: 위 (a)~(c)의 근거 줄, `ops_log_runs.json`과 `ops_log2_runs.json`의 호출 수·초 합계(56회 155.2초, 55회 142.1초)와 두 노트의 합계, `verify-c2-notes.md:54`와 `stale-records-notes.md`가 가리키는 `edge-legend-notes.md:17`, `live-05-notes.md:27`·`:30`·`:39`, `replay-4-notes.md:93`·`:97`의 내용, `cost-report-c2.txt`와 현재 출력. 노트 전체를 한 줄씩 다시 확인한 것은 아닙니다.
