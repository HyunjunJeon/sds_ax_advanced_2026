"""회의실 예약 서비스 (Day06_new 실습용 작은 예제).

예약은 data_dir 아래 JSON 파일에 저장한다. 시각은 같은 날의 "HH:MM" 문자열이다.
요구사항 R1~R7은 feature_list.json에 있고, 각 요구사항의 검사는 test_reservation.py에 있다.
"""

import json
from pathlib import Path


class ReservationError(Exception):
    """예약을 저장하지 않은 이유를 담는다."""


class ReservationService:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # 사용자마다 파일 하나에 저장한다.
    def _path(self, user):
        return self.data_dir / f"{user}.json"

    def _load(self, user):
        path = self._path(user)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, user, items):
        text = json.dumps(items, ensure_ascii=False, indent=2)
        self._path(user).write_text(text, encoding="utf-8")

    def reserve(self, user, room, start, end):
        item = {"user": user, "room": room, "start": start, "end": end}
        items = self._load(user)
        items.append(item)
        self._save(user, items)
        return item

    def list(self, user, include_others=False):
        # R3: 다른 사용자의 예약도 함께 보여 준다.
        items = self._load(user)
        if include_others:
            items = []
            for path in sorted(self.data_dir.glob("*.json")):
                items.extend(json.loads(path.read_text(encoding="utf-8")))
        return sorted(items, key=lambda item: (item["room"], item["start"]))
