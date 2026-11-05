# 회의실 예약 서비스 — 작업 규칙

이 폴더는 여러 세션에 걸쳐 작업하는 작은 예약 서비스다. 세션은 이전 대화를 기억하지 못한다.
이어 가는 데 필요한 사실은 모두 이 폴더의 파일과 git 기록에 있다.

## 파일

| 파일 | 무엇인가 |
|---|---|
| `feature_list.json` | 요구사항 R1~R7과 각 요구사항의 통과 여부(`passes`), 그 통과를 확인한 코드 커밋(`verified_at`) |
| `progress.md` | 세션마다 남긴 진행 기록 |
| `reservation.py` | 서비스 코드 |
| `test_reservation.py` | 요구사항 검사. `test_<ID>_...` 이름이 `feature_list.json`의 `test` 칸과 같다 |

## 시작할 때 (세션마다)

1. `progress.md`와 `feature_list.json`을 읽는다.
2. `git log --oneline -5`로 최근 변경을 본다.
3. `python3 -m unittest -v`로 지금 코드의 실제 상태를 확인한다.

## 작업할 때

- 한 번에 요구사항 하나만 작업한다.
- `test_reservation.py`는 고치지 않는다. 검사가 틀렸다고 생각하면 고치지 말고 사람에게 묻는다.
- `feature_list.json`에서는 `passes`와 `verified_at`만 바꾼다. 항목을 지우거나 설명을 고치지 않는다.
- `passes`를 `true`로 바꾸기 전에 그 요구사항의 검사를 실행해 통과를 확인한다.
  `verified_at`에는 그때의 코드 커밋을 적는다: 코드를 커밋한 뒤 `git log -1 --format=%h -- reservation.py`.

## 끝낼 때

1. 바꾼 코드를 커밋한다.
2. `progress.md`에 이번 세션의 기록을 덧붙인다: 한 일, 실행한 검사와 결과, 확인하지 못한 것, 다음 할 일.
3. `feature_list.json`과 `progress.md`를 커밋한다.
