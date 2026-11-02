# docs/audit/tools — 문서 검사기와 결함 주입 도구

저자용 도구다. 수강생 실습에는 필요 없다. 이 폴더의 도구는 모델도 EXA도 부르지 않는다 (`build_notes6.py`만 `.env`를 읽는다, 아래 4절).
저장소 루트나 Day03_new 경로는 코드에 적혀 있지 않다. 각 스크립트가 자기 위치(`Path(__file__)`)에서 Day03_new와 저장소 루트를 계산한다.
임시 작업 폴더(복사본, 결과, 스냅샷)는 항상 명령행 인자이고 기본값이 없다.

모든 명령은 **저장소 루트**에서, 루트 환경의 Python으로, `-B`를 붙여 실행한다 (`__pycache__`가 이 폴더에 생기지 않게 하려는 것이다).
`sys.dont_write_bytecode`는 스크립트 안에도 있지만 `rows.py`를 import하는 스크립트가 여럿이라 `-B`를 빼면 남는다.

| 파일 | 하는 일 |
|---|---|
| `check_citations.py` | 문서의 `파일:줄` 인용이 실제 파일의 그 줄을 가리키는지 검사 |
| `check_costs.py` | 문서의 비용 표가 `tests/cost_report.py` 출력과 같은지 검사 |
| `design-allow.txt` | `check_citations.py --strict`가 `docs/DESIGN.md`에서 허용하는 옛 기록 4줄 |
| `rows.py`, `row_tables.py` | 결함 주입 표: 행 175개 = `clean` 1 + 결함 174 |
| `falsify6.py`, `mkcopy.py` | 행마다 복사본을 만들어 결함 하나를 넣고 전체 시험을 돌린다 |
| `report.py`, `dryrun.py`, `build_notes6.py` | 결과 요약, 사전 점검, 기록 문서 생성 |
| `hashtree.sh` | 실행 전후에 실제 트리가 같은지 보는 해시 |
| `sync_probe2.py` | `rag_lab/`과 `data/business/`, `data/cases.jsonl`이 든 폴더 하나를 받아 검색 결과를 JSON 줄(2,280줄)로 쓴다. 명령은 `.venv/bin/python -B Day03_new/docs/audit/tools/sync_probe2.py <폴더> <출력.jsonl> [--break-rank]`이고, 두 폴더의 출력을 줄 단위로 비교한다. `--break-rank`는 일부러 순위를 뒤집어 비교가 차이를 잡는지 보는 대조 실행이다(코드 주석은 negative control이라 부른다). 모델·EXA를 부르지 않고 `.env`와 `data/gold.jsonl`을 읽지 않는다. 쓰임과 결과는 `sync-equivalence-notes.md` |

## 1. check_citations.py

문서 안의 `파일:줄`, `파일:시작-끝`, 표의 `심볼:줄`을 읽어 파일이 있는지, 줄이 파일 끝을 넘지 않는지 확인한다.
`--strict`이면 같은 문장의 백틱 식별자 하나가 인용한 줄의 앞뒤 한 줄 안에 있는지도 본다 (없으면 `MISMATCH`).

```bash
.venv/bin/python -B Day03_new/docs/audit/tools/check_citations.py --self-test
.venv/bin/python -B Day03_new/docs/audit/tools/check_citations.py Day03_new/AGENTS.md --strict
.venv/bin/python -B Day03_new/docs/audit/tools/check_citations.py Day03_new/docs/DESIGN.md --strict --allow Day03_new/docs/audit/tools/design-allow.txt
```

끝 줄이 요약이다. 통과는 `hard_failures=0`과 `mismatches=0`이다 (`DESIGN.md`는 여기에 `allowed=4`가 더 보인다). 종료 코드 0이 통과다.

**보지 못하는 것.**
- 문장에 백틱 식별자가 없는 인용(`no_identifier`)은 줄이 파일 안에 있는지만 보고 내용은 확인하지 않는다. 요약의 `no_identifier(not verified)` 개수만큼은 사람이 읽는다.
- 경로의 해석 순서는 문서 폴더, Day03_new, 저장소 루트다. `rag_lab/evidence.py:22`처럼 접두사가 없으면 문장이 `Day02_new`의 같은 이름 파일을 뜻해도 Day03_new의 복사본을 읽는다. 다른 폴더의 파일은 `Day02_new/rag_lab/evidence.py:22`처럼 저장소 루트 기준으로 적은 것만 확인되고, 저장소 밖 파일(외부 소스)은 확인되지 않는다. 그런 인용은 손으로 읽는다.
- 문장의 주장(줄이 말하는 내용, 숫자, 동작 설명)은 검사하지 않는다. 식별자가 그 줄 근처에 있다는 것만 본다.
- 확장자가 `.py .md .json .jsonl .ipynb .toml .txt .yaml .yml .cfg .ini .csv .sh .lock .example`가 아닌 파일, 코드 블록 안의 인용은 읽지 않는다.
- `data/gold.jsonl` 인용은 파일이 있는지만 보고 열지 않는다 (요약의 `protected_not_opened`). 자체 시험은 임시 폴더의 가짜 파일로 이를 확인한다.

## 2. design-allow.txt

`--allow`로 넘기면 그 줄에서 나온 `--strict` 결과가 `ALLOWED`로 세어지고 통과를 막지 않는다. 형식은 탭으로 나눈 `줄의 앞부분<TAB>인용<TAB>이유`다.
**여기에는 라벨이 붙은 옛 기록만 넣는다.** 지금도 참이라고 말하는 문장이 `--strict`에서 걸렸으면 문서를 고친다. 이 파일에 올려 통과시키지 않는다.
쓰이지 않은 항목은 `UNUSED-ALLOW`로 나오니, 문서가 바뀌어 항목이 남았으면 지운다.

## 3. check_costs.py

`Day03_new/tests/cost_report.py`를 돌려(모델 호출 없음, `outputs/live`만 읽는다) 기록 13개의 호출 수·초·입력·출력·USD를 얻고,
문서의 표에서 첫 칸이 기록 이름(`01-Workflow-vs-Agent`, `...exercises`)인 행이 같은지, `합계` 행이 반올림 전 값의 합과 같은지 본다.

```bash
.venv/bin/python -B Day03_new/docs/audit/tools/check_costs.py --self-test
.venv/bin/python -B Day03_new/docs/audit/tools/check_costs.py Day03_new/AGENTS.md
.venv/bin/python -B Day03_new/docs/audit/tools/check_costs.py Day03_new/README.md
.venv/bin/python -B Day03_new/docs/audit/tools/check_costs.py Day03_new/docs/DESIGN.md --require none
```

`--require`는 문서에 꼭 있어야 하는 기록(`all`, `base`, `exercises`, `none`)이다. 비용 표가 없어도 되는 문서는 `none`으로 본다.

**보지 못하는 것.** 표 밖의 문장에 적힌 숫자("모델 호출 312회" 같은 서술)는 읽지 않는다. 호출 수 헤더가 없는 표의 기록 행은 `SKIPPED`로 보일 뿐 비교하지 않는다.
`cost_report.py`가 계산하지 않는 값(캐시 쓰기 단가)은 표에 있어도 맞는지 알 수 없다.

## 4. 결함 주입 표 (falsify 7의 기록)

`rows.py`의 표는 **falsify-7 실행의 기록이다.** falsify 6의 행 172개는 `Day03_new/rag_lab`을 `Day02_new/rag_lab`과 동기화한 뒤에도 글자 그대로 한 번씩 나와서 하나도 고치지 않았고, 동기화가 만든 행 `sy01`, `sy02`만 더했다. 그 실행이 쓴 Day02_new 스냅샷(`Day02_new/rag_lab`을 시작 때 한 번 복사한 것)과 결과(`results.jsonl`, 행별 `out.txt`)는 여기에 없다.
다음 사용자는 자기 스냅샷과 자기 작업 폴더를 넘긴다. 작업 폴더는 저장소 밖이어야 한다 (`mkcopy.py`는 Day03_new 안의 폴더를 거부한다).
행 하나의 정의는 복사본 하나에 결함 하나(한 파일의 한 번 나오는 문자열 교체)와 그 결함이 깨뜨려야 하는 시험 이름이다.
`row_tables.py`는 행 `g`, `w`, `b`, `gi`, `ex`, `wp`의 교체 문자열을 담는다. 원래는 임시 폴더의 여섯 스크립트에 있던 표를 글자 그대로 옮긴 것이고, 그 스크립트들은 보존되지 않았다. 행 라벨 끝의 `[phase3/...]`는 그 옛 임시 폴더 이름이 남은 것이다 (라벨은 기록이라 고치지 않았다).

행 수는 이렇게 센다 (결함 174행이 나와야 한다).

```bash
.venv/bin/python -B -c "import sys; sys.path.insert(0, 'Day03_new/docs/audit/tools'); import rows; print(len(rows.ROWS) - 1)"
```

```bash
WORK=<복사본과 결과를 쓸 빈 폴더>     # 저장소 밖
SNAP=<Day02_new/rag_lab을 복사해 둔 폴더>
.venv/bin/python -B Day03_new/docs/audit/tools/falsify6.py --work $WORK --snapshot $SNAP clean 1     # 행 id를 적는다. 생략하면 전부, `a:b`는 순서 조각
.venv/bin/python -B Day03_new/docs/audit/tools/report.py --work $WORK     # `SURVIVORS []`이면 돌린 행이 모두 잡힌 것
```

- 모델도 EXA도 부르지 않는다. 행마다 API 키 환경변수와 `*_proxy`를 지우고, 복사본에는 `.env`가 없고, `exa.py`에 넣는 행은 닿지 않는 프록시(`127.0.0.1:9`) 뒤에서 돈다.
- 행 하나는 복사 + 전체 `tests` 시험으로 약 8~10초이고 175행 전체는 약 30분이다. 실제 트리에는 쓰지 않는다. 복사본에서만 고친다.
- **`clean` 행이 기준이다.** 결함 없는 복사본에서 시험이 하나도 실패하지 않아야 `ok`다 (2026-11-02 동기화 뒤 611개 통과, 0 실패). `falsify6.py`의 `BASELINE`은 "저자가 일부러 빨갛게 둔 시험 id"의 목록인데 동기화로 두 칸
  (`test_rag_lab_copies_are_byte_identical[retrieval.py]`, `[evidence.py]`)이 초록이 되어 지금은 비어 있다. 다시 빨간 칸을 두기로 하면 그 id를 `BASELINE`에 적는다. 적어 두지 않은 빨간 칸이 있으면 `clean`이 `NOT-CAUGHT`다.
- **`sy01`, `sy02`.** 복사본 시험(`tests/test_layout.py:13`)은 `corpus.py`, `retrieval.py`, `evidence.py`, `pipeline.py` 네 칸이다. 행 13은 `[corpus.py]` 칸을, `sy01`은 `rag_lab/pipeline.py`의 주석에서, `sy02`는 `rag_lab/evidence.py`의 주석에서 1바이트를 바꿔
  `[pipeline.py]`, `[evidence.py]` 칸이 실패해야 한다. 주석만 바꾸므로 다른 시험은 움직이지 않는다. `[retrieval.py]` 칸에는 행이 없다.
- 행의 `old` 문자열이 코드에서 정확히 한 번 나오지 않으면 `INJECT FAILED`이고 행은 잡히지 않은 것으로 센다. 코드가 움직이면 행이 낡는다. `dryrun.py`로 먼저 본다.
- 이 표는 결함을 "넣을 수 있는 곳"의 목록이다. 시험이 어떤 결함을 잡는다는 보증이 아니다. 잡히지 않는 행(`NOT-CAUGHT`)이 곧 시험의 빈틈이고, 지우거나 가리지 않는다.

```bash
# 행의 old 문자열이 지금 코드에 한 번씩 나오는지, 예고한 시험 이름이 수집되는지 (쓰기 없음)
.venv/bin/python -B Day03_new/docs/audit/tools/dryrun.py --collected <시험 id 목록 파일>
# 목록 파일: 깨끗한 복사본의 Day03_new 에서  uv run --no-sync --project <저장소 루트> pytest -p no:cacheprovider --collect-only -q tests | grep '::'
# 정상 출력: `rows 175 bad 0 noop []`, 그리고 n10~n13의 NOEXPECT 4줄 (그 시험 칸은 주입이 노트북을 고친 뒤에야 생긴다)
```

`build_notes6.py`는 falsify-7의 기록 문서를 `results.jsonl`과 실행 전후 해시에서 만든다.

```bash
.venv/bin/python -B Day03_new/docs/audit/tools/build_notes6.py --work $WORK --snapshot $SNAP --record <실행 기록 폴더> --prefix <기록 파일 이름의 앞부분> --prev-rows <이전 판 rows.py> --out <쓸 파일>
```

필요한 기록 파일 이름은 `--help`가 알려 준다. 이전 판(falsify 6)의 `rows.py`는 어느 행이 새로 생기거나 고쳐졌는지 비교하려고 읽는데 여기에 보존되지 않았다. 기록 파일은 `--prefix`로 시작하는 이름(`<prefix>-realtree-before.txt` 등)이고, 시작 표지(`<prefix>-start-marker`)는 도구를 마지막으로 고친 뒤에 만든다. 이 스크립트는 판정에 쓸 비밀 값 검사를 하려고
이 저장소의 `.env` 파일과 키 이름이 든 환경변수를 **프로세스 안에서** 읽는다 (값은 출력하지 않고 파일에 쓰지 않는다). 읽으면 안 되는 자리에서는 돌리지 않는다.
판정(`PASS`/`FAIL`)은 돌리는 시점의 트리 상태를 반영한다. 그 뒤 문서가 바뀌었으면 `FAIL`로 나올 수 있다.

## 5. 정답표를 읽지 않는다

이 도구들은 `data/gold.jsonl`을 파싱하거나 출력하지 않는다. `check_citations.py`는 존재만 확인하고, `falsify6.py`의 `diff`와 `hashtree.sh`의 전체 해시, `build_notes6.py`의 비밀 값 검사는 그 파일을 비교·해시 대상에서 뺀다.
단 `mkcopy.py`의 `rsync`는 복사본의 시험이 그 파일을 읽으므로 파일을 그대로 복사한다.

## 6. hashtree.sh

`Day03_new/mas_lab`, `tests`, `rag_lab`, 노트북 7개, `Day02_new/rag_lab`의 내용 해시와 `outputs/runs` 파일 수를 줄마다 한 줄로 낸다.

```bash
Day03_new/docs/audit/tools/hashtree.sh > <실행 전 파일>
Day03_new/docs/audit/tools/hashtree.sh > <실행 후 파일>   # 둘을 diff 한다
```

**보지 못하는 것.** 해시가 같다는 것은 그 폴더들의 파일 내용이 같다는 뜻뿐이다. 마지막의 "all non-excluded files" 줄(참고용)은 `data/gold.jsonl`을 뺀 값이라 이 줄이 없던 시절의 기록과 비교되지 않는다.
