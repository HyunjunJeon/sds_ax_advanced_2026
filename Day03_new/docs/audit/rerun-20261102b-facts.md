# Day03_new 재실행(rerun-20261102b) 기록 기반 수치

생성: 13개 기록(`Day03_new/outputs/live/*.json`, `.usage.jsonl`, `.executed.ipynb`) 직접 집계. 모델·EXA 호출 없음. 셀 번호는 0부터이고 마크다운 셀을 포함한다. 이전 기록은 `outputs/live/superseded-20261102-before-subagent-off/`다. 02는 이전 기록의 25번 이상 셀이 +4, 05는 이전 2~35가 +3, 36~57이 +6 이동했다(새 02 셀 25~28, 05 셀 2~4와 39~41이 새 셀).

## Totals

Cost: 입력 2, 출력 10, 캐시 읽기 0.2 USD / 1M 토큰, 기록된 입력은 캐시 읽기를 포함(비캐시 = 입력 - 캐시 읽기). 직접 재합산(`.usage.jsonl`)과 `tests/cost_report.py` 출력을 비교했다.

### 이번 재실행(현재 기록, outputs/live)

| 기록 | 호출 | 초 | 입력 | 출력 | 캐시 읽기 | 비용(USD) |
|---|---:|---:|---:|---:|---:|---:|
| 00-Setup | 3 | 12.6 | 7582 | 388 | 3489 | 0.0128 |
| 01-Workflow-vs-Agent | 45 | 131.2 | 186251 | 12153 | 152345 | 0.2198 |
| 01-Workflow-vs-Agent.exercises | 51 | 153.2 | 208926 | 14008 | 171658 | 0.2489 |
| 02-Agent-Architecture | 33 | 114.2 | 113267 | 13640 | 73192 | 0.2312 |
| 02-Agent-Architecture.exercises | 53 | 165.4 | 166118 | 20325 | 118884 | 0.3215 |
| 03-Four-Flows | 38 | 131.7 | 86025 | 16247 | 44580 | 0.2543 |
| 03-Four-Flows.exercises | 44 | 138.4 | 110580 | 18015 | 81957 | 0.2538 |
| 04-Graph-Engineering | 35 | 107.8 | 94303 | 15855 | 63187 | 0.2334 |
| 04-Graph-Engineering.exercises | 36 | 115.0 | 90778 | 16866 | 61568 | 0.2394 |
| 05-Choosing-Multi-Agent | 142 | 402.8 | 549206 | 53185 | 393366 | 0.9222 |
| 05-Choosing-Multi-Agent.exercises | 451 | 1237.5 | 1713172 | 145338 | 1256429 | 2.6182 |
| 06-Lab-Research-Agents | 28 | 214.0 | 147993 | 32660 | 74422 | 0.4886 |
| 06-Lab-Research-Agents.exercises | 63 | 433.4 | 295148 | 73650 | 132337 | 1.0886 |
| **base(7)** | 324 | 1114.3 | 1184627 | 144128 | 804581 | 2.3623 |
| **exercises(6)** | 698 | 2242.8 | 2584722 | 288202 | 1822833 | 4.7704 |
| **all(13)** | 1022 | 3357.1 | 3769349 | 432330 | 2627414 | 7.1327 |

비반올림 합계와 행별 반올림 값의 합:

| 묶음 | 초(비반올림) | 초(행 1자리 합) | 비용(비반올림) | 비용(행 4자리 합) |
|---|---:|---:|---:|---:|
| base(7) | 1114.308 | 1114.3 | 2.362288 | 2.3623 |
| exercises(6) | 2242.829 | 2242.9 | 4.770365 | 4.7704 |
| all(13) | 3357.137 | 3357.2 | 7.132653 | 7.1327 |

### 이전 기록(superseded-20261102-before-subagent-off)

| 기록 | 호출 | 초 | 입력 | 출력 | 캐시 읽기 | 비용(USD) |
|---|---:|---:|---:|---:|---:|---:|
| 00-Setup | 3 | 12.1 | 8758 | 353 | 4077 | 0.0137 |
| 01-Workflow-vs-Agent | 41 | 133.7 | 161078 | 11773 | 123824 | 0.2170 |
| 01-Workflow-vs-Agent.exercises | 46 | 155.2 | 180172 | 13816 | 146182 | 0.2354 |
| 02-Agent-Architecture | 35 | 146.2 | 125672 | 13949 | 77760 | 0.2509 |
| 02-Agent-Architecture.exercises | 53 | 179.0 | 168682 | 19751 | 109160 | 0.3384 |
| 03-Four-Flows | 37 | 128.2 | 78292 | 15842 | 43613 | 0.2365 |
| 03-Four-Flows.exercises | 41 | 131.6 | 89848 | 17768 | 62660 | 0.2446 |
| 04-Graph-Engineering | 35 | 106.1 | 88649 | 15051 | 63002 | 0.2144 |
| 04-Graph-Engineering.exercises | 36 | 114.3 | 90080 | 15485 | 66909 | 0.2146 |
| 05-Choosing-Multi-Agent | 135 | 450.2 | 496246 | 49999 | 347468 | 0.8670 |
| 05-Choosing-Multi-Agent.exercises | 441 | 1237.9 | 1614963 | 144522 | 1167197 | 2.5742 |
| 06-Lab-Research-Agents | 29 | 212.2 | 156937 | 32201 | 88161 | 0.4772 |
| 06-Lab-Research-Agents.exercises | 64 | 413.0 | 305459 | 71722 | 149173 | 1.0596 |
| **base(7)** | 315 | 1188.6 | 1115632 | 139168 | 747905 | 2.2767 |
| **exercises(6)** | 681 | 2231.0 | 2449204 | 283064 | 1701281 | 4.6667 |
| **all(13)** | 996 | 3419.6 | 3564836 | 422232 | 2449186 | 6.9435 |

비반올림 합계와 행별 반올림 값의 합:

| 묶음 | 초(비반올림) | 초(행 1자리 합) | 비용(비반올림) | 비용(행 4자리 합) |
|---|---:|---:|---:|---:|
| base(7) | 1188.641 | 1188.7 | 2.276715 | 2.2767 |
| exercises(6) | 2230.962 | 2231.0 | 4.666742 | 4.6668 |
| all(13) | 3419.603 | 3419.7 | 6.943457 | 6.9435 |

- cost_report(현재) 합계 비용 7.132653, 호출 1022; 직접 재합산 7.132653, 호출 1022; 일치: True
  - 행별 비용도 일치: True
- cost_report(이전) 합계 비용 6.943457, 호출 996; 직접 재합산 6.943457, 호출 996; 일치: True
  - 행별 비용도 일치: True
- 이번 합계 행(`cost_report`): `| **합계** | | 1022 | 3357.1 | 3769349 | 432330 | **7.1327** |` (위 all(13)과 같다).

## Times

| 기록 | json mtime(KST) |
|---|---|
| 00-Setup | 2026-11-03 00:05:43 |
| 01-Workflow-vs-Agent | 2026-11-03 00:08:09 |
| 01-Workflow-vs-Agent.exercises | 2026-11-03 00:10:51 |
| 02-Agent-Architecture | 2026-11-03 00:12:59 |
| 02-Agent-Architecture.exercises | 2026-11-03 00:15:51 |
| 03-Four-Flows | 2026-11-03 00:18:20 |
| 03-Four-Flows.exercises | 2026-11-03 00:20:43 |
| 04-Graph-Engineering | 2026-11-03 00:22:46 |
| 04-Graph-Engineering.exercises | 2026-11-03 00:24:47 |
| 05-Choosing-Multi-Agent | 2026-11-03 00:31:43 |
| 05-Choosing-Multi-Agent.exercises | 2026-11-03 00:52:28 |
| 06-Lab-Research-Agents | 2026-11-03 00:56:17 |
| 06-Lab-Research-Agents.exercises | 2026-11-03 01:03:38 |

- 시작 표지(code-hashes.txt mtime): 2026-11-03 00:05:29 KST
- 마지막 기록 종료: 2026-11-03 01:03:38 KST; 창 00:05:29 ~ 01:03:38 (run-finalize 보고: 00:05:29 ~ 01:03:38)
- 벽시계 3489초, 노트북 실행 초 합 3357.1

## Audit

- model_calls > 0 셀: 98개 (13개 기록 합계)
- 고지한 model_calls= 합과 같은 셀: 15개; 다른 셀: 83개 (실측 < 고지 83, 실측 > 고지 0, 고지 숫자 없음 0)

고지와 다른 셀(기록, 셀, 실측, 고지 합):
- 00-Setup 셀 16: 실측 2, 고지 3
- 01-Workflow-vs-Agent 셀 11: 실측 2, 고지 4
- 01-Workflow-vs-Agent 셀 17: 실측 8, 고지 12
- 01-Workflow-vs-Agent 셀 23: 실측 4, 고지 6
- 01-Workflow-vs-Agent 셀 27: 실측 3, 고지 4
- 01-Workflow-vs-Agent 셀 32: 실측 3, 고지 4
- 01-Workflow-vs-Agent 셀 36: 실측 20, 고지 30
- 01-Workflow-vs-Agent.exercises 셀 11: 실측 2, 고지 4
- 01-Workflow-vs-Agent.exercises 셀 17: 실측 11, 고지 12
- 01-Workflow-vs-Agent.exercises 셀 23: 실측 4, 고지 6
- 01-Workflow-vs-Agent.exercises 셀 27: 실측 3, 고지 4
- 01-Workflow-vs-Agent.exercises 셀 32: 실측 3, 고지 4
- 01-Workflow-vs-Agent.exercises 셀 36: 실측 17, 고지 30
- 01-Workflow-vs-Agent.exercises 셀 44: 실측 3, 고지 4
- 01-Workflow-vs-Agent.exercises 셀 48: 실측 3, 고지 4
- 02-Agent-Architecture 셀 9: 실측 5, 고지 12
- 02-Agent-Architecture 셀 15: 실측 9, 고지 14
- 02-Agent-Architecture 셀 20: 실측 9, 고지 14
- 02-Agent-Architecture 셀 36: 실측 7, 고지 12
- 02-Agent-Architecture 셀 38: 실측 3, 고지 8
- 02-Agent-Architecture.exercises 셀 9: 실측 6, 고지 12
- 02-Agent-Architecture.exercises 셀 15: 실측 10, 고지 14
- 02-Agent-Architecture.exercises 셀 20: 실측 9, 고지 14
- 02-Agent-Architecture.exercises 셀 36: 실측 7, 고지 12
- 02-Agent-Architecture.exercises 셀 38: 실측 3, 고지 8
- 02-Agent-Architecture.exercises 셀 52: 실측 10, 고지 14
- 02-Agent-Architecture.exercises 셀 54: 실측 8, 고지 12
- 03-Four-Flows 셀 28: 실측 7, 고지 12
- 03-Four-Flows 셀 29: 실측 6, 고지 12
- 03-Four-Flows 셀 43: 실측 5, 고지 6
- 03-Four-Flows 셀 54: 실측 9, 고지 15
- 03-Four-Flows.exercises 셀 28: 실측 6, 고지 12
- 03-Four-Flows.exercises 셀 29: 실측 7, 고지 12
- 03-Four-Flows.exercises 셀 43: 실측 5, 고지 6
- 03-Four-Flows.exercises 셀 54: 실측 9, 고지 15
- 03-Four-Flows.exercises 셀 61: 실측 6, 고지 8
- 04-Graph-Engineering 셀 5: 실측 2, 고지 4
- 04-Graph-Engineering 셀 6: 실측 2, 고지 4
- 04-Graph-Engineering 셀 13: 실측 6, 고지 12
- 04-Graph-Engineering 셀 31: 실측 8, 고지 12
- 04-Graph-Engineering 셀 44: 실측 2, 고지 5
- 04-Graph-Engineering 셀 52: 실측 10, 고지 16
- 04-Graph-Engineering.exercises 셀 5: 실측 2, 고지 4
- 04-Graph-Engineering.exercises 셀 6: 실측 2, 고지 4
- 04-Graph-Engineering.exercises 셀 13: 실측 7, 고지 12
- 04-Graph-Engineering.exercises 셀 31: 실측 7, 고지 12
- 04-Graph-Engineering.exercises 셀 44: 실측 2, 고지 5
- 04-Graph-Engineering.exercises 셀 52: 실측 9, 고지 16
- 04-Graph-Engineering.exercises 셀 56: 실측 2, 고지 4
- 05-Choosing-Multi-Agent 셀 6: 실측 10, 고지 20
- 05-Choosing-Multi-Agent 셀 12: 실측 3, 고지 8
- 05-Choosing-Multi-Agent 셀 16: 실측 10, 고지 20
- 05-Choosing-Multi-Agent 셀 20: 실측 9, 고지 20
- 05-Choosing-Multi-Agent 셀 26: 실측 6, 고지 12
- 05-Choosing-Multi-Agent 셀 34: 실측 16, 고지 30
- 05-Choosing-Multi-Agent 셀 35: 실측 16, 고지 24
- 05-Choosing-Multi-Agent 셀 43: 실측 70, 고지 100
- 05-Choosing-Multi-Agent 셀 48: 실측 2, 고지 3
- 05-Choosing-Multi-Agent.exercises 셀 6: 실측 9, 고지 20
- 05-Choosing-Multi-Agent.exercises 셀 12: 실측 3, 고지 8
- 05-Choosing-Multi-Agent.exercises 셀 16: 실측 9, 고지 20
- 05-Choosing-Multi-Agent.exercises 셀 20: 실측 9, 고지 20
- 05-Choosing-Multi-Agent.exercises 셀 26: 실측 5, 고지 12
- 05-Choosing-Multi-Agent.exercises 셀 34: 실측 14, 고지 30
- 05-Choosing-Multi-Agent.exercises 셀 35: 실측 16, 고지 24
- 05-Choosing-Multi-Agent.exercises 셀 43: 실측 68, 고지 100
- 05-Choosing-Multi-Agent.exercises 셀 47: 실측 265, 고지 330
- 05-Choosing-Multi-Agent.exercises 셀 48: 실측 2, 고지 3
- 05-Choosing-Multi-Agent.exercises 셀 54: 실측 29, 고지 48
- 05-Choosing-Multi-Agent.exercises 셀 56: 실측 17, 고지 24
- 05-Choosing-Multi-Agent.exercises 셀 58: 실측 5, 고지 15
- 06-Lab-Research-Agents 셀 12: 실측 3, 고지 13
- 06-Lab-Research-Agents 셀 17: 실측 8, 고지 16
- 06-Lab-Research-Agents 셀 19: 실측 8, 고지 16
- 06-Lab-Research-Agents 셀 25: 실측 9, 고지 16
- 06-Lab-Research-Agents.exercises 셀 12: 실측 3, 고지 13
- 06-Lab-Research-Agents.exercises 셀 17: 실측 8, 고지 16
- 06-Lab-Research-Agents.exercises 셀 19: 실측 8, 고지 16
- 06-Lab-Research-Agents.exercises 셀 25: 실측 9, 고지 16
- 06-Lab-Research-Agents.exercises 셀 34: 실측 7, 고지 16
- 06-Lab-Research-Agents.exercises 셀 45: 실측 7, 고지 16
- 06-Lab-Research-Agents.exercises 셀 47: 실측 12, 고지 32
- 06-Lab-Research-Agents.exercises 셀 49: 실측 9, 고지 16

## Switch cells

기록 base에서 모델 호출 0, exercises에서 > 0인 셀 (셀 번호는 0부터, 마크다운 포함, 새 번호).

| 노트북 | 셀 | 호출 | 초 | 스위치 | 고지 |
|---|---:|---:|---:|---|---:|
| 01 | 44 | 3 | 4.382 | RUN_EXERCISE | 4 |
| 01 | 48 | 3 | 16.249 | RUN_EXERCISE | 4 |
| 01 합 | 2셀 | 6 | 20.631 | | 8 |
| 02 | 52 | 10 | 30.574 | RUN_EXERCISE | 14 |
| 02 | 54 | 8 | 21.859 | RUN_EXERCISE | 12 |
| 02 합 | 2셀 | 18 | 52.433 | | 26 |
| 03 | 61 | 6 | 12.455 | RUN_EXERCISE | 8 |
| 03 합 | 1셀 | 6 | 12.455 | | 8 |
| 04 | 56 | 2 | 4.463 | RUN_EXERCISE | 4 |
| 04 합 | 1셀 | 2 | 4.463 | | 4 |
| 05 | 47 | 265 | 694.713 | RUN_OPTIONAL | 330 |
| 05 | 54 | 29 | 84.874 | RUN_EXERCISE | 48 |
| 05 | 56 | 17 | 46.783 | RUN_EXERCISE | 24 |
| 05 | 58 | 5 | 12.609 | RUN_EXERCISE | 15 |
| 05 합 | 4셀 | 316 | 838.979 | | 417 |
| 06 | 34 | 7 | 43.479 | RUN_OPTIONAL | 16 |
| 06 | 45 | 7 | 30.682 | RUN_EXERCISE | 16 |
| 06 | 47 | 12 | 96.553 | RUN_EXERCISE | 32 |
| 06 | 49 | 9 | 39.198 | RUN_EXERCISE | 16 |
| 06 합 | 4셀 | 35 | 209.912 | | 80 |
| 전체 합 | | 383 | 1138.873 | | |

base에서만 유료인 셀(exercises에서 0): 없음

## Same cells

base와 exercises 둘 다 호출 > 0인 셀. 쌍은 (base / exercises) 호출, 초.

### 01

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 5 | 1 | 1 | 7.329 | 6.037 |
| 9 | 2 | 2 | 2.996 | 3.110 |
| 11 | 2 | 2 | 7.035 | 6.894 |
| 17 | 8 | 11 | 27.511 | 35.030 |
| 23 | 4 | 4 | 17.141 | 18.816 |
| 27 | 3 | 3 | 7.488 | 9.725 |
| 32 | 3 | 3 | 5.290 | 5.092 |
| 36 | 20 | 17 | 47.453 | 38.850 |
| 39 | 2 | 2 | 6.313 | 6.282 |
| 합(9셀) | 45 | 45 | 128.556 | 129.836 |

- base 전체 호출 45 (공통 셀 45, 나머지 0); exercises 전체 51 (공통 45, 스위치 셀 6, 합 51, 차 0)

### 02

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 9 | 5 | 6 | 19.229 | 20.458 |
| 15 | 9 | 10 | 26.316 | 26.839 |
| 20 | 9 | 9 | 25.597 | 25.549 |
| 36 | 7 | 7 | 30.638 | 26.302 |
| 38 | 3 | 3 | 10.228 | 11.804 |
| 합(5셀) | 33 | 35 | 112.008 | 110.952 |

- base 전체 호출 33 (공통 셀 33, 나머지 0); exercises 전체 53 (공통 35, 스위치 셀 18, 합 53, 차 0)

### 03

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 11 | 5 | 5 | 32.604 | 26.243 |
| 28 | 7 | 6 | 14.446 | 9.999 |
| 29 | 6 | 7 | 24.836 | 32.296 |
| 34 | 6 | 6 | 9.883 | 9.596 |
| 43 | 5 | 5 | 13.446 | 12.910 |
| 54 | 9 | 9 | 26.307 | 24.760 |
| 합(6셀) | 38 | 38 | 121.522 | 115.804 |

- base 전체 호출 38 (공통 셀 38, 나머지 0); exercises 전체 44 (공통 38, 스위치 셀 6, 합 44, 차 0)

### 04

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 5 | 2 | 2 | 7.838 | 7.324 |
| 6 | 2 | 2 | 4.032 | 4.136 |
| 13 | 6 | 7 | 9.215 | 13.055 |
| 15 | 3 | 3 | 24.798 | 27.751 |
| 22 | 2 | 2 | 8.742 | 8.492 |
| 31 | 8 | 7 | 19.688 | 16.031 |
| 44 | 2 | 2 | 4.431 | 5.592 |
| 52 | 10 | 9 | 26.848 | 25.853 |
| 합(8셀) | 35 | 34 | 105.592 | 108.234 |

- base 전체 호출 35 (공통 셀 35, 나머지 0); exercises 전체 36 (공통 34, 스위치 셀 2, 합 36, 차 0)

### 05

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 6 | 10 | 9 | 34.200 | 30.153 |
| 12 | 3 | 3 | 12.556 | 14.590 |
| 16 | 10 | 9 | 26.950 | 29.419 |
| 20 | 9 | 9 | 25.110 | 24.372 |
| 26 | 6 | 5 | 21.716 | 20.155 |
| 34 | 16 | 14 | 37.815 | 39.645 |
| 35 | 16 | 16 | 36.021 | 35.942 |
| 43 | 70 | 68 | 200.159 | 195.319 |
| 48 | 2 | 2 | 5.349 | 6.065 |
| 합(9셀) | 142 | 135 | 399.876 | 395.660 |

- base 전체 호출 142 (공통 셀 142, 나머지 0); exercises 전체 451 (공통 135, 스위치 셀 316, 합 451, 차 0)

### 06

| 셀 | 호출 base | 호출 ex | 초 base | 초 ex |
|---:|---:|---:|---:|---:|
| 12 | 3 | 3 | 18.834 | 19.901 |
| 17 | 8 | 8 | 44.813 | 39.992 |
| 19 | 8 | 8 | 71.319 | 77.427 |
| 25 | 9 | 9 | 75.917 | 83.877 |
| 합(4셀) | 28 | 28 | 210.883 | 221.197 |

- base 전체 호출 28 (공통 셀 28, 나머지 0); exercises 전체 63 (공통 28, 스위치 셀 35, 합 63, 차 0)

## Estimate vs actual

extra = exercises - base. 스위치 셀 합은 스위치 셀의 호출 합이다. 고지 = 해당 셀 소스의 model_calls= 합(상한).

| 노트북 | base 실측 | base 고지 합(유료 셀) | extra(ex-base) | 스위치 셀 호출 합 | 스위치 셀 고지 합 |
|---|---:|---:|---:|---:|---:|
| 01 | 45 | 65 | 6 | 6 | 8 |
| 02 | 33 | 60 | 20 | 18 | 26 |
| 03 | 38 | 56 | 6 | 6 | 8 |
| 04 | 35 | 58 | 1 | 2 | 4 |
| 05 | 142 | 237 | 309 | 316 | 417 |
| 06 | 28 | 61 | 35 | 35 | 80 |
| 00 | 3 | | | | |
| 합 | 324 | 537 | 377 | 383 | 543 |

## Named cells

역할은 실행본 셀 소스로 확인했다(새 셀 번호). 쌍은 base / exercises 호출, 초.

| 노트북 | 셀 | 역할(소스 근거) | 호출 base / ex | 초 base / ex |
|---|---:|---|---|---|
| 01 | 36 | `BASELINE_IDS` 세 사례의 Single 기준선, `run_grid(["single"], ...)`, 고지 30 | 20 / 17 | 47.453 / 38.850 |
| 02 | 9 | "Single이 T-1001 처리", `build_single`, 고지 12 | 5 / 6 | 19.229 / 20.458 |
| 02 | 36 | "Handoff 턴 1: T-1001", `build_handoff`, 고지 12 | 7 / 7 | 30.638 / 26.302 |
| 02 | 38 | "Handoff 턴 2: 같은 thread의 후속 질문", 고지 8 | 3 / 3 | 10.228 / 11.804 |
| 05 | 34 | "hybrid 단순 사례와 복합 사례"(simple-deadline, complex-double-pay), 고지 30 | 16 / 14 | 37.815 / 39.645 |
| 05 | 35 | "Fast Path 강제 2사례"(`force_path="fast"`), 고지 24 | 16 / 16 | 36.021 / 35.942 |
| 05 | 43 | "같은 조건 비교표", `run_grid(CONFIG["STRUCTURES"], ..., repeats=CONFIG["REPEATS"])`, 고지 100 | 70 / 68 | 200.159 / 195.319 |
| 05 | 47 | "전체 비교 4유형 x 5구조 x 1회", `if not RUN_OPTIONAL`, 고지 330. 스위치 셀이라 base는 0호출 | 0 / 265 | - / 694.713 |
| 06 | 12 | "Worker 1개로 소주제 하나 조사"(`research-one`), 고지 model 5 + EXA 2 | 3 / 3 | 18.834 / 19.901 |
| 06 | 17 | "병렬 리서치" `run_research("parallel", ...)`, 고지 16 | 8 / 8 | 44.813 / 39.992 |
| 06 | 19 | "같은 그래프를 max_concurrency=1로 실행"(serial), 고지 16 | 8 / 8 | 71.319 / 77.427 |
| 06 | 25 | "앞 결과를 뒤 Worker에 넘기는 연쇄"(chained), 고지 16 | 9 / 9 | 75.917 / 83.877 |

05 셀 47의 base 기록은 `RUN_OPTIONAL = False`라 안내 문구만 출력한다(위 Switch cells 표에 포함). 05 셀 43의 호출은 base 70, ex 68이다.

## EXA

검색 횟수와 USD(검색 1회 0.007)는 셀 출력의 `EXA 호출`, `검색 횟수`, 표의 `EXA 호출`/`EXA 비용(USD)` 열에서 읽었다. 고지 `exa_calls=`도 셀 소스와 같이 적는다.

| 기록 | 셀 | 내용 | 검색 | USD | 고지 exa_calls |
|---|---:|---|---:|---:|---:|
| 00 | 17 | EXA 검색 확인(`검색 1회`, 비용(달러) 0.007) | 1 | 0.007 | 1 |
| 06 base | 7 | 자료 형태 확인(`검색 횟수: 1`, 0.007) | 1 | 0.007 | 1 |
| 06 base | 12 | Worker 1개(`EXA 호출: 2`, 0.014) | 2 | 0.014 | 2 |
| 06 base | 17 | 병렬 | 6 | 0.042 | 6 |
| 06 base | 19 | serial | 6 | 0.042 | 6 |
| 06 base | 25 | 연쇄 | 6 | 0.042 | 6 |
| 06 base 합 | | | 21 | 0.147 | 21 |
| 06 ex | 7, 12, 17, 19, 25 | base와 같은 다섯 셀(출력 값 같음: 1, 2, 6, 6, 6) | 21 | 0.147 | 21 |
| 06 ex | 34 | 병렬 한 번 더(표 두 번째 행, 첫 행은 셀 17의 앞 실행; `EXA 호출` 6, 0.042) | 6 | 0.042 | 6 |
| 06 ex | 45 | 해보기 1 병렬(6, 0.042) | 6 | 0.042 | 6 |
| 06 ex | 47 | 해보기 2: parallel 2(0.014) + chained 6(0.042) | 8 | 0.056 | 12 |
| 06 ex | 49 | 해보기 3 병렬(표 두 번째 행; 첫 행은 셀 34의 앞 실행; 6, 0.042) | 6 | 0.042 | 6 |
| 06 ex 합 | | | 47 | 0.329 | 51 |

- 06 전체(base + ex): 21 + 47 = 68회, 0.476 USD. 00을 더하면 69회, 0.483 USD.
- 06 base와 ex의 셀 7~25 EXA 값이 같다. 셀 47의 parallel 행은 2회(plan_hash 99b79eb0c58f), chained 행은 6회였다. 고지 12회보다 4회 적다.


## general-purpose

기준: `Day03_new/outputs/runs/*.json` 중 mtime이 시작 표지(`docs/audit/rerun-20261102b-code-hashes.txt` mtime, 2026-11-03 00:05:29 KST)보다 늦은 파일. JSON 전체 텍스트에 `general-purpose`가 들어 있는지와, `structure == "supervisor"` 행의 `budget.model`(예산이 센 모델 호출)이 `model_calls`(실제)와 다른지를 셌다. 이전 기록 쪽은 같은 구조로, 2026-11-02 21:40:44 KST(이전 재실행의 첫 실행) 이후 시작 표지 이전의 행이다(`docs/audit/live-rerun-20261102-notes.md` 2절의 실행 시각 21:40:44~22:51:21과 같은 창. 06은 `outputs/runs`를 쓰지 않는다).

### 이번 재실행(mtime > 시작 표지)
- 행 115개; 구조별 {'handoff': 10, 'hybrid': 32, 'single': 42, 'single_skills': 12, 'supervisor': 19}
- new rows delegating to general-purpose: 0
- supervisor 행 19개 중 budget.model != model_calls: 0개

### 이전 기록(2026-11-02 21:40:44 KST ~ 시작 표지)
- 행 115개; 구조별 {'handoff': 10, 'hybrid': 32, 'single': 42, 'single_skills': 12, 'supervisor': 19}
- previous rows delegating to general-purpose (JSON text contains `general-purpose`): 3
- supervisor 행 19개 중 budget.model != model_calls: 3개
- general-purpose 파일: b0f3a3afdf604ecea45d038a68a1b441.json, 74b1bcea770c478ea506972ae66f6a7a.json, 51a7ca00fb6943c59bc7d25794590416.json
  - b0f3a3afdf604ecea45d038a68a1b441.json: budget.model 7, model_calls 8
  - 74b1bcea770c478ea506972ae66f6a7a.json: budget.model 5, model_calls 6
  - 51a7ca00fb6943c59bc7d25794590416.json: budget.model 10, model_calls 11

## Saved vs executed

저장본 `Day03_new/<노트북>.ipynb`와 실행본을 셀 단위로 비교(`RUN_EXERCISE`/`RUN_OPTIONAL =` 줄은 양쪽에서 지운 뒤 비교). 셀 수 = 같은 번호의 셀 종류와 개수.

| 실행본 | 셀 수 같음 | 코드 셀 같음 | 마크다운 셀 같음 | 다른 셀 |
|---|---|---|---|---|
| 00-Setup | True | True | True | - |
| 01-Workflow-vs-Agent | True | True | True | - |
| 01-Workflow-vs-Agent.exercises | True | True | True | - |
| 02-Agent-Architecture | True | True | True | - |
| 02-Agent-Architecture.exercises | True | True | True | - |
| 03-Four-Flows | True | True | True | - |
| 03-Four-Flows.exercises | True | True | True | - |
| 04-Graph-Engineering | True | True | True | - |
| 04-Graph-Engineering.exercises | True | True | True | - |
| 05-Choosing-Multi-Agent | True | True | True | - |
| 05-Choosing-Multi-Agent.exercises | True | True | True | - |
| 06-Lab-Research-Agents | True | True | True | - |
| 06-Lab-Research-Agents.exercises | True | True | True | - |

- 13개 모두 같음: True

## Notebook sizes

| 노트북 | 셀 | 코드 셀 | 마크다운 셀 | 마크다운 글자 수 |
|---|---:|---:|---:|---:|
| 00-Setup | 25 | 12 | 13 | 8265 |
| 01-Workflow-vs-Agent | 51 | 32 | 19 | 15867 |
| 02-Agent-Architecture | 62 | 36 | 26 | 15865 |
| 03-Four-Flows | 67 | 41 | 26 | 15591 |
| 04-Graph-Engineering | 66 | 42 | 24 | 16763 |
| 05-Choosing-Multi-Agent | 64 | 37 | 27 | 19801 |
| 06-Lab-Research-Agents | 55 | 30 | 25 | 15684 |
| **합계** | 390 | 230 | 160 | 107836 |

## Spend

- 이번 재실행: 모델 호출 1022회(base 324, exercises 698), 노트북 실행 초 합 3357.1초(비반올림 3357.137, 시작 표지~마지막 기록 벽시계 3489초, 00:05:29~01:03:38 KST), 입력 3,769,349 / 출력 432,330 / 캐시 읽기 2,627,414 토큰, 비용 7.1327 USD(모델), EXA 검색 69회(00 1 + 06 base 21 + 06 ex 47) = 0.483 USD(검색당 0.007).
- 합계 약 7.62 USD(모델 7.1327 + EXA 0.483 = 7.6157).
- 이전 기록(superseded-20261102-before-subagent-off) 모델 996회, 3419.6초, 6.9435 USD. 호출 +26, 비용 +0.1892 USD, 초 -62.5.
