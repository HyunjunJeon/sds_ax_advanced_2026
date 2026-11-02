# Clean clone notes 3 (node clean-clone-3, run dag_mvyi94ja_vi2zuw)

P = <P>
이 실행은 P/clean-clone-2-notes.md (run dag_mvy51tor_2og7v6)의 절차를 rag_lab 동기화(sync-copy, 09:13) 뒤의 작업 트리에서 그대로 되풀이한 것이다. 같은 절차, 같은 24개 Day06 경로 처리.
새 폴더: P/clone3-src, P/clone3-dst, P/clone3-uv-cache (빈 캐시로 시작). 시작 전에 P/clone2-src (648928 KiB)와 P/clone2-dst (730272 KiB)를 지웠다 (P/clone3-freed-clone2.txt, 두 경로 모두 realpath가 P 바로 아래임을 확인한 뒤 삭제).
도구는 P/clone-tools/make_candidate.py, key_scan.py를 읽기만 하고 재사용했다. 새로 만든 스크립트: P/clone3-keyscan.py (clone2-keyscan.py 복사), P/clone3-gitgrep.py (clone2-gitgrep.py에서 이름만 바꿈).
로그: P/clone3-sync.log, clone3-pytest.log, clone3-pytest-v.log, clone3-check-notebook.log, clone3-selftest.log, clone3-step4.{out,err,rc}, clone3-keyscan.txt, clone3-sizes-before-delete.txt, clone3-versions.txt, clone3-make-candidate.txt, clone3-missing.txt.
이 노드의 유료 호출은 0이다. 모델 호출 0, EXA 호출 0, 키를 복제본에 복사하지 않았다. 키 값은 어디에도 출력하거나 기록하지 않았다.

## 1. 후보와 복제본

- 실제 저장소에서 `GIT_OPTIONAL_LOCKS=0 git ls-files -co --exclude-standard -z`가 22299 경로를 냈다 (clone2는 22290). make_candidate.py 결과: `paths=22299 files=22257 symlinks=36 dirs=0 skipped_missing=6`. 존재하지 않는 6개는 clone2와 같다: Day02/uv.lock, Day03/uv.lock, Day04/requirements.txt, Day05/uv.lock, Day07/uv.lock, Day08/uv.lock.
- `git init -q`, `git add -A`가 22269개를 넣었고, 추적되지만 새 이력에서는 ignore에 걸리는 경로 24개를 건너뛰었다. 이 24개는 clone2-missing.txt와 한 줄도 다르지 않다 (`diff` 같음): Day06/ouroboros/.ouroboros/{mechanical.toml, seeds/*.yaml 2개}, Day06/ouroboros/.python-version, ouroboros canonical evidence `.ouroboros/traces` 18개, pi doom.js와 doom.wasm. 이 24개만 `git add -f --pathspec-from-file`로 넣고 `git -c user.name=audit -c user.email=audit@example.invalid -c commit.gpgsign=false commit -q -m candidate` 했다. 결과: 추적 파일 22293, 상태 깨끗함.
- `git clone -q P/clone3-src P/clone3-dst`: 추적 파일 22293. 실행 전 복제본: `.env` 0개, `.venv` 0개, `outputs` 폴더 0개 (`.env.example`은 11개).
- 동기화된 rag_lab이 복제본에 들어 있다: 복제본 `Day03_new/rag_lab/`의 sha256이 `Day02_new/rag_lab/`와 네 파일 모두 같다 (corpus.py `1deabc44...`, retrieval.py `8ab9f86e...`, evidence.py `e3704857...`, pipeline.py `dcab73f2...`).
- 복제본 루트 pyproject.toml `59dfcfc2...`, uv.lock `e39fee03...` (실제 저장소와 같음).
- Day03_new/docs/audit 있음: 파일 53개.
- 한계: 후보는 작업 트리 그대로다(약 09:16~09:17 시점). 다른 세션/노드의 커밋 안 된 수정이 후보 안에 들어 있다. 증명하는 것은 "이 작업 트리를 새로 clone하면 설치되고 통과한다"이지 "origin/main이 통과한다"가 아니다. 복제본에는 원격 이력도 Lecture_Note(git 제외)도 없다.

## 2. uv sync --locked, 빈 캐시

명령 (P/clone3-dst에서): `env -u VIRTUAL_ENV UV_CACHE_DIR=P/clone3-uv-cache PYTHONDONTWRITEBYTECODE=1 uv sync --locked`. 캐시 폴더는 방금 만든 빈 폴더(항목 0개)였다. 09:18:42에 시작해 09:18:53에 끝났다.
uv 0.13.6 (Homebrew 2026-10-26 aarch64-apple-darwin). 로그: `Using CPython 3.13.14`, `Resolved 363 packages in 2ms`, `Prepared 345 packages in 10.24s`, `Installed 345 packages in 773ms`, exit=0.
- 패키지 수: 설치 345 (로그의 ` + ` 줄 345개, `importlib.metadata` 배포판 수 345), 해석 363 (uv.lock 기준).
- Python 3.13.14
- deepagents 0.7.32
- langgraph 1.2.19
- langchain-anthropic 1.7.7
(P/versions-before.txt, clone2와 같다.) 삭제 직전 크기(du 기준 KiB x 1024): 캐시 2306252800 바이트(2.1G), .venv 1988235264 바이트(1.9G), clone3-src 665047040 바이트, clone3-dst(.venv 포함) 2736300032 바이트. (P/clone3-sizes-before-delete.txt)

## 3. 오프라인 검사 (P/clone3-dst/Day03_new, 복제본 .venv/bin/python, ANTHROPIC_API_KEY와 EXA_API_KEY는 env -u로 제거)

- `python -m pytest -p no:cacheprovider`: **611 passed, 0 failed**, rc=0, 11.83초. `-v` 재실행도 611 passed, rc=0, 7.98초 (PASSED 줄 611개, FAILED/ERROR/SKIPPED/XFAIL/XPASS 줄 0개).
  - 네 셀이 모두 통과한다: `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[corpus.py]`, `[retrieval.py]`, `[evidence.py]`, `[pipeline.py]`. clone2에서는 retrieval.py와 evidence.py 두 셀이 빨갰고 pipeline.py 셀은 없었다(610개 = 608 passed + 2 failed). 지금은 셀이 하나 늘어 611개다.
- `check_notebook.py` 7개 모두 OK, rc=0: 00-Setup --minutes 10, 01~06 --minutes 60.
- `docs/audit/tools/check_citations.py --self-test`: `self-test ok`, rc=0.
- `docs/audit/tools/check_costs.py --self-test`: **복제본에서는 rc=1**, 기대한 실패다. `CalledProcessError`는 `reference()`(check_costs.py:69)가 `tests/cost_report.py`를 부르는데, 그 스크립트가 `.../clone3-dst/Day03_new/outputs/live에 *.usage.jsonl이 없습니다.`를 내고 rc=1로 끝나기 때문이다(`tests/cost_report.py`를 직접 실행해 같은 메시지와 rc=1을 확인했다; outputs는 git 제외라 복제본에 없다). 지시가 이 한 가지 self-test의 실패를 예상된 것으로 정해 두었다. 다른 self-test는 모두 통과했다. clone2와 같은 원인이고 이번에는 outputs를 복사해 되돌리는 확인은 하지 않았다(필요 없음).

## 4. 00-Setup, tests/run_live.py, .env 없음, 키 제거

명령 (P/clone3-dst에서): `env -u VIRTUAL_ENV -u ANTHROPIC_API_KEY -u EXA_API_KEY PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python Day03_new/tests/run_live.py Day03_new/00-Setup.ipynb`. 복제본에 `.env` 0개. (에이전트 셸 환경에는 두 키 이름 중 하나가 있었으나 이름 개수만 확인했고 값은 보지 않았다. 모든 복제본 명령은 `env -u`로 두 이름을 지우고 실행했다.)
- 종료 코드 1 (P/clone3-step4.rc), 출력 `LIVE RUN FAILED 00-Setup errors=1` (예상한 멈춤).
- 멈춘 셀: 노트북 셀 인덱스 **5** (code 셀, 실행 번호 In[3]), 5번째 줄 `settings = require_key()`. 첫 키 확인에서 멈췄고 6번째 줄 `require_exa_key()`와 `make_model`에는 닿지 않았다. 실행 번호 In[3]이 마지막이며 인덱스 6 이후 code 셀은 모두 실행 번호가 없다.
- 오류: RuntimeError, 메시지 원문: "ANTHROPIC_API_KEY가 미설정입니다. Day03_new/.env.example을 .env로 복사한 뒤 ANTHROPIC_API_KEY에 본인의 키를 직접 채우세요."  (.env.example 이름이 한국어 문장 안에 있다.)
- 앞서 실행된 셀: 인덱스 2와 3, 둘 다 ok, 모델 호출 0.
- **모델 호출 0**: 결과 JSON(00-Setup.json)에서 model_calls=0, input_tokens=0, output_tokens=0이고 `.usage.jsonl`이 만들어지지 않았다 (복제본 outputs/live에는 00-Setup.executed.ipynb와 00-Setup.json만 생겼다). 실제 키 단계는 하지 않았다.

## 5. 키 스캔 (P/clone3-keyscan.py, P/clone3-gitgrep.py)

실제 Day03_new/.env를 값 출력 없이 읽었다: 항목 7개, 비밀 이름 중 값이 12자 이상인 것은 ANTHROPIC_API_KEY와 EXA_API_KEY 두 개 → 바늘 4개(전체값, 끝 12자 각각).
- 바이트 스캔 (.venv 제외, 심볼릭 링크 따라가지 않음, `.git` 포함): 파일 47173개. **총 히트 0** (ANTHROPIC 전체 0, 끝12자 0, EXA 전체 0, 끝12자 0). 스캔은 4절 실행 뒤에 했으므로 복제본 outputs/live의 파일 2개도 포함한다.
- 양성 대조: 복제본 안 임시 파일(Day03_new/keyscan-control.tmp)에 ANTHROPIC 전체값과 EXA 끝 12자를 써 넣고 다시 스캔 → 파일 47174개, 히트 3 (ANTHROPIC 전체 1, ANTHROPIC 끝12자 1, EXA 끝12자 1). 파일 제거 후 재스캔 → 47173개, 히트 0, 파일 없음.
- 추가: `git grep -l -F -a -f <needles>` HEAD blob 매칭 파일 0 (rc=1 = 없음), `git grep --no-index`(작업 트리, .venv 제외) 매칭 파일 0. 바늘 파일은 mode 0600으로 만들어 쓰고 바로 지웠다(존재하지 않음 확인).
- 키 값이나 .env 내용은 어디에도 출력하거나 기록하지 않았다.

## 6. 실제 저장소 불변 확인, 정리

- 실제 루트 pyproject.toml sha256 59dfcfc2d720158f33a30b845506ff60fbbf7b58da428f8bd16079d44ff5830c, 전후 같음.
- 실제 루트 uv.lock sha256 e39fee03edbc931007298a611bafdc3543b003add9139295c288543b3a863ac4, 전후 같음 (P/clone3-hash-before.txt, clone3-hash-after.txt, `diff` 같음).
- 실제 루트 .venv: 시작 표식(P/clone3-start-marker)보다 새로운 항목(깊이 2까지) 0. `.git/index` 수정 시각과 크기 전후 같음 (1793429557, 3158654), index.lock 없음, `.git/config` sha256 전후 같음, stash 0개 전후 같음. Day03_new/.env 수정 시각 전후 같음. 실제 Day03_new/outputs 아래 표식보다 새 파일 0, `outputs/runs` 파일 수 1893, 전후 같음.
- 실제 저장소에서 실행한 git 명령은 읽기 전용 `git ls-files`(GIT_OPTIONAL_LOCKS=0)와 `git stash list`뿐이다. 실제 저장소에 쓴 것은 없다. 복제본의 `git status --short`는 깨끗하고 `__pycache__` 0개다.
- 삭제: P/clone3-uv-cache, P/clone3-dst/.venv, P/clone3-src를 크기 기록 후 삭제했고(realpath가 P 아래임을 확인) 없음을 확인했다. 남긴 것: P/clone3-dst (.venv 제외, 748437504 바이트, 추적 파일 22293, 상태 깨끗함).

## 증명하지 않은 것

- 01~06 노트북 실행은 하지 않았다(유료). 이 노드는 모델 호출 0, EXA 호출 0.
- 실제 키를 넣은 00-Setup 경로는 지시대로 하지 않았다.
- origin/main의 clone은 시험하지 않았다(위 한계). macOS aarch64만 시험했고 Windows/Linux는 아니다.
- Python 3.13.14는 이 기계에 이미 설치돼 있었다(로그에 CPython 다운로드 없음). Python이 없는 학생의 다운로드 경로는 시험하지 않았다.
- check_costs.py의 문서 대조 실행은 요구되지 않았고 하지 않았다(outputs 없음).
- 동기화 뒤 part 3(검색 행) 차이의 원인은 이 노드의 범위가 아니며 조사하지 않았다.

Clean clone: PASS
