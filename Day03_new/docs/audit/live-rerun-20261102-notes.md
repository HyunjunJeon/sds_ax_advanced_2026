# 2026-11-02 실행 기록 전체 재실행 노트

모델 호출과 EXA 호출이 있는 유료 실행 기록이다. `.env`는 열거나 출력하지 않았다(키 상태는 `key_status()`로 `설정됨`만 확인). 모든 수치는 1회 관찰이다.

## 1. 왜 다시 돌렸나

- 2026-11-02 저자가 Supervisor 용어를 라이브러리 관례에 맞추기로 정했다(`docs/DESIGN.md` 1절 저자 결정). 그래서 02의 코드 셀 11개에서 변수·라벨·표 이름을 바꿨다.
- 라벨은 `Trace`에만 들어가 모델 입력에 닿지 않는다(`mas_lab/runner.py:41`). 그래도 `tests/audit_live.py`의 `stale_cells`는 저장본 코드와 기본 실행본 코드가 같기를 요구한다(`tests/audit_live.py:47-51`). 바꾼 직후 감사는 `FAIL 02-Agent-Architecture: 저장본의 코드가 실행본과 다릅니다.`로 1건 실패했다. 바꾸기 전 저장본(백업)으로는 통과했다.
- 저자 승인으로 02 기본 실행을 먼저 다시 돌렸다. 그 뒤 저자가 "다시 안 돌린 작업들은 모두 다시 돌려 보는 게 좋다"고 정해, 나머지 12개 기록도 다시 돌렸다. 그 12개는 2026-11-01에 만든 기록이었다. `mas_lab`의 `gate.py`·`workers.py`·`exa.py` 수정 앞뒤로 갈려 있었고, 모두 `rag_lab` 동기화(2026-11-02 09:13)보다 앞섰다.

## 2. 무엇을 어떻게 돌렸나

명령(저장소 루트): `uv run --no-sync python Day03_new/tests/run_live.py Day03_new/<노트북> [--exercises]`. 429를 줄이려고 하나씩 차례로 돌렸다.

| 순서 | 기록 | 시작~끝 (KST) | 결과 |
|---|---|---|---|
| 1 | 02 기본 | 21:40:44~21:43:09 | `LIVE RUN OK errors=0` |
| 2 | 00 | 21:56:33~21:56:47 | `LIVE RUN OK errors=0` |
| 3~4 | 01 기본, 켠 실행 | 21:56:47~22:01:38 | 둘 다 `errors=0` |
| 5 | 02 켠 실행 | 22:01:38~22:04:38 | `errors=0` |
| 6~7 | 03 기본, 켠 실행 | 22:04:38~22:09:00 | 둘 다 `errors=0` |
| 8~9 | 04 기본, 켠 실행 | 22:09:00~22:12:43 | 둘 다 `errors=0` |
| 10~11 | 05 기본, 켠 실행 | 22:12:43~22:40:53 | 둘 다 `errors=0` |
| 12~13 | 06 기본, 켠 실행 | 22:40:53~22:51:21 | 둘 다 `errors=0` |

02 기본의 시각은 실행본 셀 메타데이터에서 읽었고, 나머지는 실행 스크립트 로그에서 읽었다. 버린 실행은 없다. 같은 기록을 두 번 돌리지 않았다.

**실행 당시 코드.** 코드와 노트북의 마지막 수정은 21:32:00(`02-Agent-Architecture.ipynb`)이다. `mas_lab/contracts.py`와 `04-Graph-Engineering.ipynb`는 21:27:27이다. 모두 첫 실행 21:40:44보다 앞선다. 아래는 그때의 sha256 앞 12자리다. 이 파일들이 바뀌면 그 노트북의 기록은 다시 판정해야 한다.

```text
e3b0c44298fc mas_lab/__init__.py
3810d4c69e85 mas_lab/contracts.py
65b0de9f5663 mas_lab/desk.py
231ea7dcf35f mas_lab/evaluation.py
c8f238a968aa mas_lab/exa.py
16c50d6ee3ec mas_lab/gate.py
c5a5f4d9d0ad mas_lab/hybrid.py
940756399a78 mas_lab/ledger.py
f897e5feac36 mas_lab/research.py
ecbdd088db96 mas_lab/runner.py
041311a76495 mas_lab/structures.py
7cd0f6949e61 mas_lab/trace.py
91b45ed62807 mas_lab/view.py
2fde59e593fb mas_lab/workers.py
e3b0c44298fc rag_lab/__init__.py
1deabc44e1b5 rag_lab/corpus.py
e3704857dcfc rag_lab/evidence.py
dcab73f251c2 rag_lab/pipeline.py
8ab9f86eeec3 rag_lab/retrieval.py
d72fe2f6775b rag_lab/settings.py
4adca3d69adf 00-Setup.ipynb
24ee361dfa42 01-Workflow-vs-Agent.ipynb
dd25b39907a8 02-Agent-Architecture.ipynb
0b4b995429c2 03-Four-Flows.ipynb
afe934173a80 04-Graph-Engineering.ipynb
c792c01ae757 05-Choosing-Multi-Agent.ipynb
c434d2328eb4 06-Lab-Research-Agents.ipynb
```

## 3. 결과

- 13개 기록 모두 `finished: true`, 오류 0건이다. `.usage.jsonl` 줄 수가 각 `.json`의 `model_calls`와 같다.
- `uv run python tests/audit_live.py` → `AUDIT OK`. 모델을 부른 셀은 98개이고, 고지를 넘은 셀은 0개, 고지와 실측이 같은 셀은 15개다.
- 13개 실행본 모두 저장본과 코드도 markdown도 같다(켠 실행본은 `RUN_EXERCISE`·`RUN_OPTIONAL` 줄만 다르다). `nbformat`으로 셀을 하나씩 비교했다.
- 새 02 실행본 출력에는 Supervisor만 있고 Manager는 없다(셀 7 구조 표, 15, 44 비교표, 45 사건 순서, 55 설계 기록).

| 기록 | 2026-11-01 기록: 모델 / 초 / USD | 2026-11-02 재실행: 모델 / 초 / USD |
|---|---|---|
| 00-Setup | 3 / 10.0 / 0.0045 | 3 / 12.1 / 0.0137 |
| 01-Workflow-vs-Agent | 45 / 142.5 / 0.2472 | 41 / 133.7 / 0.2170 |
| 01-Workflow-vs-Agent.exercises | 52 / 172.6 / 0.2792 | 46 / 155.2 / 0.2354 |
| 02-Agent-Architecture | 33 / 106.8 / 0.2466 | 35 / 146.2 / 0.2509 |
| 02-Agent-Architecture.exercises | 51 / 164.3 / 0.3236 | 53 / 179.0 / 0.3384 |
| 03-Four-Flows | 37 / 110.6 / 0.2307 | 37 / 128.2 / 0.2365 |
| 03-Four-Flows.exercises | 44 / 135.8 / 0.2805 | 41 / 131.6 / 0.2446 |
| 04-Graph-Engineering | 33 / 100.4 / 0.2380 | 35 / 106.1 / 0.2144 |
| 04-Graph-Engineering.exercises | 36 / 109.0 / 0.2197 | 36 / 114.3 / 0.2146 |
| 05-Choosing-Multi-Agent | 135 / 394.6 / 0.9216 | 135 / 450.2 / 0.8670 |
| 05-Choosing-Multi-Agent.exercises | 435 / 1272.2 / 2.6047 | 441 / 1237.9 / 2.5742 |
| 06-Lab-Research-Agents | 26 / 199.2 / 0.4890 | 29 / 212.2 / 0.4772 |
| 06-Lab-Research-Agents.exercises | 59 / 388.1 / 1.0937 | 64 / 413.0 / 1.0596 |

| 합계 | 2026-11-01 기록 | 2026-11-02 재실행 |
|---|---|---|
| 기본 실행 7개 | 312회, 1064.1초, USD 2.3776 | 315회, 1188.6초, USD 2.2767 |
| 켠 실행 6개 | 677회, 2241.9초, USD 4.8013 | 681회, 2231.0초, USD 4.6667 |
| 13개 합(겹치는 두 실행의 합, 지출 아님) | 989회, 3306.0초, USD 7.1789 | 996회, 3419.6초, USD 6.9435 |

비용은 `tests/cost_report.py` 값이다. `.usage.jsonl`을 `cost_report.py` 없이 따로 더해(입력 2, 출력 10, 캐시 읽기 0.2 USD/100만 토큰) 대조했고 호출 수, 토큰, 비용이 같았다. 캐시 쓰기 단가는 모델링하지 않아 하한이다.

**두 기록의 차이를 원인별로 나눌 수 없다.** 코드(`mas_lab` 세 파일, `rag_lab` 동기화, 02 이름)도 바뀌었고 모델 응답도 실행마다 달라진다. 이 표는 "이번에 이렇게 나왔다"만 말한다.

**EXA.** 00 1회, 06 기본 21회(셀 7·12·17·19·25에 1+2+6+6+6), 06 켠 실행 47회(21 + 셀 34 둘째 행 6 + 셀 45 6 + 셀 47 병렬 2·연쇄 6 + 셀 49 둘째 행 6)다. 횟수는 재실행 전과 같다. 검색당 0.007 USD로 합쳐 69회, 약 USD 0.48이다.

## 4. 이번 실행의 지출

| 구간 | 모델 호출 | 초 | 모델 비용 하한 | EXA |
|---|---:|---:|---:|---:|
| 02 기본 실행 | 35 | 146.2 | USD 0.2509 | 0 |
| 나머지 12개 | 961 | 3273.4 | USD 6.6926 | 69회, 약 USD 0.48 |
| 합계 | 996 | 3419.6 | USD 6.9435 | 69회, 약 USD 0.48 |

실행 전 고지는 02가 약 33회·약 USD 0.25, 12개가 모델 약 950회(셀 고지 상한 합 약 1,390회)·약 USD 7·EXA 약 69회·약 USD 0.5였다. 문서 갱신, 감사, 시험은 모델도 EXA도 부르지 않았다. 이 작업을 진행한 에이전트 자신의 토큰은 세지 않았다.

## 5. 남긴 것과 바뀐 것

- 이전 기록: `outputs/live/superseded-20261102/`(02 기본 실행의 json·usage·실행본), `outputs/live/superseded-20261102-before-full-rerun/`(나머지 12개 기록 36개 파일, `design_log.json`, `baseline/`). `cost_report.py`와 `audit_live.py`는 `outputs/live/` 바로 아래만 읽어 이 폴더를 세지 않는다(`tests/cost_report.py:39`, `tests/audit_live.py:55`).
- 실행이 덮어쓴 파일: `outputs/design_log.json`은 22:40:53(05 켠 실행 끝)에, `outputs/baseline/01.json`은 22:01:00(01 켠 실행)에 마지막으로 쓰였다.
- `outputs/runs`: 1,893파일에서 2,008파일이 됐다(재실행이 115행을 썼다). 이 폴더는 git에 올리지 않는다.
- 문서: README의 비용·켠 칸 표와 기록 시점, AGENTS 6장(비용 표, 기록 시점, 켠 칸 표)과 7장의 관찰 문장, DESIGN 9.2·9.1 표·같은 셀 변동·10.4의 6·11번·11절 지출·12절 행을 새 기록으로 고쳤다. 앞의 값은 "재실행 전", "앞 판"으로 남겼다.
- AGENTS 6장에 있던 "다시 돌리지 않은 이유"(기록 묶음별 코드 비교)는 지웠다. 그 판단의 근거는 `docs/audit/stale-records-notes.md`와 `docs/audit/sync-equivalence-notes.md`에, 요약은 DESIGN 12절 `마지막 수정 앞에 돌린 기록` 행의 이력에 그대로 있다.

## 6. 한계

- 1회 관찰이다. 같은 코드로 다시 돌려도 호출 수, 토큰, 답이 달라진다(DESIGN 9.2 "같은 셀의 변동").
- 단가표 자체는 검증하지 않았다. 캐시 쓰기 비용은 빠져 있다.
- 노트북 코드를 다시 고치면 감사가 기본 실행만 잡는다. 켠 실행본은 감사 없이 어긋나므로 함께 다시 돌려야 한다.

## 7. 재실행에서 새로 관찰한 것

- **`supervisor`의 `general-purpose` 위임.** 05 켠 실행 셀 41에서 `supervisor` 3행(`outputs/runs`의 `b0f3a3af…`, `74b1bcea…`, `51a7ca00…`)이 `task`로 `general-purpose`에 `no-op`·`dummy`를 위임했다. 세 행 모두 `budget.model`이 `model_calls`보다 1 적다(7/8, 5/6, 10/11). `build_supervisor`가 Deep Agents의 기본 하위 에이전트를 끄지 않아 생긴 길이고(`mas_lab/structures.py:56`), 고칠지는 저자 결정으로 남겼다(`docs/DESIGN.md` 12절).
- **문서가 가리키던 관찰 일곱 개가 뒤집혔다.**
  - 04 켠 실행 셀 53이 날짜 표기로 실패한다.
  - 재실행 행의 `recovered`는 모두 0이다.
  - 평균 B에서 남은 사례가 하나가 되는 모양이 Single이 아니라 hybrid에서 나온다.
  - 06 셀 12의 기본·켠 실행 호출 수(3과 2)가 재실행 전과 서로 바뀌었다.
  - 06 셀 7의 `published`는 3건 중 1건이다.
  - 01 셀 38 켠 실행의 호출 수가 6과 4로 갈렸다.
  - 위의 `general-purpose` 위임이 나왔다.
  
  AGENTS 7장과 DESIGN 9.2절을 새 값으로 고쳤다.
- **확인하지 못한 것.**
  - 05 기본 실행의 supervisor 행(셀 14)과 05 켠 실행의 `persona` 행(셀 17)은 `누락 사실 [9월20일]`이지만, 실행본에서 답 본문이 잘려 표기 차이인지 알 수 없다.
  - 재실행 행의 `filled` 세 건(14, 16, 14)이 `facts` 번호 가지를 탔는지 알 수 없다. 행에 Worker의 `facts`가 남지 않기 때문이다.
