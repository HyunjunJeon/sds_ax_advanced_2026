# Clean clone notes 2 (node clean-clone-2, run dag_mvy51tor_2og7v6)

P = <P>
이 실행은 앞선 P/clean-clone-notes.md (run dag_mvxjjtgg_181ytn)를 오늘 작업 트리에서 되풀이한 것이다. 같은 절차, 같은 24개 Day06 경로 처리.
새 폴더: P/clone2-src, P/clone2-dst, P/clone2-uv-cache(끝에 삭제). 도구는 P/clone-tools/make_candidate.py, key_scan.py를 읽기만 하고 재사용했다. 새로 쓴 스크립트: P/clone2-keyscan.py, P/clone2-gitgrep.py.
로그: P/clone2-sync.log, P/clone2-pytest.log, P/clone2-pytest-v.log, P/clone2-check-notebook.log, P/clone2-selftest.log, P/clone2-step4.{out,err}, P/clone2-keyscan.txt, P/clone2-sizes-before-delete.txt.
이 노드의 유료 호출은 0이다. 모델 호출 0, EXA 호출 0, 키를 복제본에 복사하지 않았다.

## 1. 후보와 복제본

- 실제 저장소에서 `git ls-files -co --exclude-standard -z`는 22290 경로를 냈다 (앞 실행은 22166). 22284개가 존재해 P/clone2-src로 복사했다: 파일 22248, 심볼릭 링크 36(링크로 재생성). 존재하지 않는 6개는 작업 트리에서 지워진 파일이다: Day02/uv.lock, Day03/uv.lock, Day04/requirements.txt, Day05/uv.lock, Day07/uv.lock, Day08/uv.lock.
- `git init -q`, `git add -A`가 22260개를 넣었고, 이 저장소에서는 추적되지만 새 이력에서는 ignore 규칙에 걸리는 24개 Day06 경로를 건너뛰었다(앞 실행과 같은 24개): Day06/ouroboros/.ouroboros/{mechanical.toml, seeds/seed_73827177a2a3.yaml, seeds/seed_78c8e6e41813.yaml}, Day06/ouroboros/.python-version, ouroboros canonical evidence의 `.ouroboros/traces` 18개(pair-1..3 x 6개), pi doom.js와 doom.wasm. 목록은 P/clone2-missing.txt. 이 24개만 `git add -f --pathspec-from-file`로 넣고 `git -c user.name=audit -c user.email=audit@example.invalid commit -q -m candidate` 했다. 결과: 추적 파일 22284, 상태 깨끗함.
- `git clone -q P/clone2-src P/clone2-dst`: 추적 파일 22284. 실행 전 복제본: `.env` 0개, `.venv` 0개, `outputs` 폴더 0개 (`.env.example`만 10개).
- Day03_new/docs/audit 있음: 파일 52개, tools/ 12개(check_citations.py, check_costs.py, rows.py, row_tables.py, falsify6.py, mkcopy.py, report.py, dryrun.py, build_notes6.py, hashtree.sh, design-allow.txt, README.md), rows/ 7개.
- 한계: 후보는 작업 트리 그대로다. 다른 세션의 커밋 안 된 수정(Day02_new, Day02/Day03 수정, 추적되지 않았지만 ignore되지 않은 파일)이 후보 안에 들어 있다. 증명하는 것은 "이 작업 트리를 새로 clone하면 설치되고 통과한다"이지 "origin/main이 통과한다"가 아니다. 복제본에는 원격 이력도 Lecture_Note(git 제외)도 없다.

## 2. uv sync --locked, 빈 캐시

명령 (P/clone2-dst에서): `env -u VIRTUAL_ENV UV_CACHE_DIR=P/clone2-uv-cache PYTHONDONTWRITEBYTECODE=1 uv sync --locked`. 캐시 폴더는 방금 만든 빈 폴더(항목 0개)였다. nohup으로 돌렸고 시작 후 30초 안에 끝났다.
uv 0.13.6 (Homebrew). 로그: `Using CPython 3.13.14`, `Resolved 363 packages in 10ms`, `Prepared 345 packages in 8.66s`, `Installed 345 packages in 788ms`, exit=0.
- 패키지 수: 설치 345 (`importlib.metadata`의 배포판 수도 345), 해석 363 (uv.lock 기준).
- Python 3.13.14
- deepagents 0.7.32
- langgraph 1.2.19
- langchain-anthropic 1.7.7
(P/versions-before.txt와 같고, 앞 실행과 같다.) 삭제 직전 크기: 캐시 2292912128 바이트(2.1G), .venv 1973862400 바이트(1.8G).

## 3. 오프라인 검사 (P/clone2-dst/Day03_new, 복제본 .venv/bin/python, ANTHROPIC_API_KEY와 EXA_API_KEY는 env -u로 제거)

- `python -m pytest -p no:cacheprovider`: **608 passed, 2 failed** (610개), 7.4~12.2초. 실패 id 정확히 2개:
  - `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]`
  - `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[evidence.py]`
  이 둘은 저자 결정으로 빨간 채로 두는 셀이다. `[corpus.py]`는 통과한다. skip 0, xfail 0, error 0. 다른 실패 없음. 앞 실행은 503 passed/0 failed였고 그 뒤 테스트가 107개 늘고 Day02_new 수정으로 이 두 셀이 빨개졌다 — 허용 범위와 같은 집합이다(다른 셀이 빨갛게 바뀌지 않았다).
  (`-q -rf`는 이 저장소 conftest 때문에 "short test summary"가 안 나와서 `-v`로 한 번 더 돌려 FAILED 줄 2개를 확인했다.)
- `check_notebook.py` 7개 모두 OK, rc=0: 00-Setup --minutes 10, 01~06 --minutes 60.
- `docs/audit/tools/check_citations.py --self-test`: `self-test ok`, rc=0.
- `docs/audit/tools/check_costs.py --self-test`: **복제본에서는 rc=1** (`CalledProcessError`). 원인은 `reference()`가 `tests/cost_report.py`를 부르는데, 그 스크립트가 `Day03_new/outputs/live에 *.usage.jsonl이 없습니다.`를 내고 rc=1로 끝나기 때문이다(outputs는 git 제외라 복제본에 없다). 과제 지시가 이 도구는 outputs가 필요하다고 정해 둔 바로 그 경우여서 FAIL로 세지 않는다. 원인이 outputs뿐임을 확인했다: 실제 저장소의 `outputs/live/*.usage.jsonl`(13개)과 `*.json`을 복제본에 잠시 복사해 같은 명령을 돌리면 `self-test ok`. (usage 파일만 복사하면 seconds 칸이 비어 "cost_report output and read_rows disagree"로 실패한다; `.json`까지 필요하다.) 복사한 파일은 지우고 복제본의 outputs/live를 원래 상태(00-Setup.executed.ipynb, 00-Setup.json)로 되돌렸다. 이 복사는 키 스캔 뒤에 했다.
  발견: `check_costs.py --self-test`는 Day03_new/outputs가 있어야 하고, outputs 없는 새 clone에서는 추적을 남기지 않고 traceback으로 끝난다. docs/audit/tools/README.md는 이 도구를 "저자용, 수강생 실습에는 필요 없다"고 적었으므로 수강생 경로는 아니다.

## 4. 00-Setup, tests/run_live.py, .env 없음, 키 제거

명령 (P/clone2-dst에서): `env -u VIRTUAL_ENV -u ANTHROPIC_API_KEY -u EXA_API_KEY PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python Day03_new/tests/run_live.py Day03_new/00-Setup.ipynb`. 복제본에 `.env` 0개.
- 종료 코드 1, 출력 `LIVE RUN FAILED 00-Setup errors=1` (예상한 멈춤).
- 멈춘 셀: 노트북 셀 인덱스 **5** (code 셀, 실행 번호 In[3]), 5번째 줄 `settings = require_key()`. 첫 키 확인에서 멈췄고 6번째 줄 `require_exa_key()`와 `make_model`에는 닿지 않았다.
- 오류: RuntimeError, 메시지 원문: "ANTHROPIC_API_KEY가 미설정입니다. Day03_new/.env.example을 .env로 복사한 뒤 ANTHROPIC_API_KEY에 본인의 키를 직접 채우세요."  (.env.example 이름이 한국어 문장 안에 있다.)
- 앞서 실행된 셀: 인덱스 2와 3, 둘 다 ok, 모델 호출 0.
- **모델 호출 0**: 결과 JSON에서 model_calls=0, input_tokens=0, output_tokens=0이고 `.usage.jsonl`이 만들어지지 않았다 (outputs/live에는 00-Setup.executed.ipynb와 00-Setup.json만 생겼다). 실제 키로 도는 앞 실행의 5절은 이번에 하지 않았다.

## 5. 키 스캔 (P/clone2-keyscan.py, P/clone2-gitgrep.py)

실제 Day03_new/.env를 값 출력 없이 읽었다: 항목 7개, 비밀 이름 중 값이 12자 이상인 것은 ANTHROPIC_API_KEY와 EXA_API_KEY 두 개 → 바늘 4개(전체값, 끝 12자 각각). OPENROUTER_API_KEY는 값이 비어 제외, 나머지 일반 항목(모델 이름, URL)은 코드에 정상적으로 나오므로 제외.
- 바이트 스캔 (.venv 제외, 심볼릭 링크 따라가지 않음): 파일 47157개 (작업 트리 22250 + .git 24907, 풀리지 않은 loose 객체; 작업 트리 22250 = 추적 22248 비링크 + outputs/live 2개). **총 히트 0** (ANTHROPIC 전체 0, 끝12자 0, EXA 전체 0, 끝12자 0).
- 양성 대조: 복제본 안 임시 파일(Day03_new/keyscan-control.tmp)에 ANTHROPIC 전체값과 EXA 끝 12자를 써 넣고 다시 스캔 → 히트 3 (ANTHROPIC 전체 1, ANTHROPIC 끝12자 1, EXA 끝12자 1). 파일 제거 후 재스캔 → 0, 파일 없음.
- 추가: `git grep -l -F -a -f <needles>` HEAD blob 매칭 파일 0 (rc=1 = 없음), `git grep --no-index`(작업 트리, .venv 제외) 매칭 파일 0. 바늘 파일은 mode 0600으로 만들어 쓰고 바로 지웠다(존재하지 않음 확인).
- 키 값이나 .env 내용은 어디에도 출력하거나 기록하지 않았다.

## 6. 실제 저장소 불변 확인, 정리

- 실제 루트 pyproject.toml sha256 59dfcfc2d720158f33a30b845506ff60fbbf7b58da428f8bd16079d44ff5830c, 전후 같음.
- 실제 루트 uv.lock sha256 e39fee03edbc931007298a611bafdc3543b003add9139295c288543b3a863ac4, 전후 같음. (전/후 파일은 P/clone2-hash-before.txt, clone2-hash-after.txt; 경로 접두사만 다르다.)
- 실제 루트 .venv: 깊이 2까지 시작 표식(P/clone2-hash-before.txt)보다 새로운 항목 0. .git/index도 새롭지 않고 index.lock 없음. Day03_new/.env도 새롭지 않음. 실제 Day03_new/outputs/runs 파일 수 1893, 전후 같음 (P/clone2-runs-before.txt).
- 실제 저장소에서 실행한 git 명령은 읽기 전용 `git ls-files` 하나뿐이다. 실제 저장소에 쓴 것은 없다. 복제본의 `git status --short`는 깨끗하고 `__pycache__` 0개다.
- 삭제: P/clone2-uv-cache (2292912128 바이트)와 P/clone2-dst/.venv (1973862400 바이트)를 크기 기록(P/clone2-sizes-before-delete.txt) 후 삭제했고 없음을 확인했다. 남긴 것: P/clone2-src (약 669 MB), P/clone2-dst (약 748 MB, .venv 제외).

## 증명하지 않은 것

- 01~06 노트북 실행은 하지 않았다(유료). 이 노드는 모델 호출 0, EXA 호출 0.
- 실제 키를 넣은 00-Setup 경로(앞 실행 5절)는 지시대로 이번에 하지 않았다.
- origin/main의 clone은 시험하지 않았다(위 한계). macOS aarch64만 시험했고 Windows/Linux는 아니다.
- Python 3.13.14는 이 기계에 이미 설치돼 있었다(로그에 CPython 다운로드 없음). Python이 없는 학생의 다운로드 경로는 시험하지 않았다.
- check_costs.py의 문서 대조 실행은 요구되지 않았고 하지 않았다(outputs 없음).

Clean clone: PASS
