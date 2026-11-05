"""회의실 예약 서비스의 요구사항 검사. 이 파일은 고치지 않는다(CLAUDE.md).

검사 이름은 test_<요구사항 ID>_... 형식이다. feature_list.json의 "test" 칸과 같은 이름이다.
python3 -m unittest -v 로 실행한다.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reservation import ReservationError, ReservationService

HERE = Path(__file__).resolve().parent


def shown(items):
    # 화면에 보이는 칸만 비교한다.
    return [(item["room"], item["start"], item["end"]) for item in items]


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_R1_reserved_item_is_listed(self):
        # R1: 회의실과 시간을 선택해 예약하면 목록에 정확한 시간과 회의실이 표시된다.
        service = ReservationService(self.data_dir)
        service.reserve("A", "회의실1", "10:00", "11:00")
        self.assertEqual(shown(service.list("A")), [("회의실1", "10:00", "11:00")])

    def test_R2_reservation_kept_after_reload(self):
        # R2: 예약 뒤 새로고침(새 서비스 객체)해도 등록한 예약이 유지된다.
        ReservationService(self.data_dir).reserve("A", "회의실1", "10:00", "11:00")
        reloaded = ReservationService(self.data_dir)
        self.assertEqual(shown(reloaded.list("A")), [("회의실1", "10:00", "11:00")])

    def test_R3_other_user_sees_reservation(self):
        # R3: 독립된 사용자 B가 조회하면 A가 등록한 같은 예약이 표시된다.
        service = ReservationService(self.data_dir)
        service.reserve("A", "회의실1", "10:00", "11:00")
        self.assertEqual(shown(service.list("B")), [("회의실1", "10:00", "11:00")])

    def test_R4_overlap_rejected(self):
        # R4: 기존 10:00-11:00, 신규 10:30-11:30(같은 회의실)은 겹치므로 거절하고 중복 데이터도 없다.
        service = ReservationService(self.data_dir)
        service.reserve("A", "회의실1", "10:00", "11:00")
        with self.assertRaises(ReservationError):
            service.reserve("B", "회의실1", "10:30", "11:30")
        all_items = shown(service.list("A")) + shown(service.list("B"))
        self.assertEqual(sorted(set(all_items)), [("회의실1", "10:00", "11:00")])

    def test_R5_back_to_back_allowed(self):
        # R5: 기존 10:00-11:00, 신규 11:00-12:00처럼 바로 이어지는 예약은 허용한다.
        service = ReservationService(self.data_dir)
        service.reserve("A", "회의실1", "10:00", "11:00")
        service.reserve("A", "회의실1", "11:00", "12:00")
        self.assertEqual(
            shown(service.list("A")),
            [("회의실1", "10:00", "11:00"), ("회의실1", "11:00", "12:00")],
        )

    def test_R6_invalid_time_rejected(self):
        # R6: 종료 시각이 시작 시각과 같거나 앞서면 저장하지 않고 이유를 알린다.
        service = ReservationService(self.data_dir)
        with self.assertRaises(ReservationError) as caught:
            service.reserve("A", "회의실1", "11:00", "10:00")
        self.assertIn("종료", str(caught.exception))
        self.assertEqual(service.list("A"), [])

    def test_R7_kept_after_restart(self):
        # R7: 서버를 다시 시작한 뒤(새 프로세스)에도 저장된 예약을 다시 조회할 수 있다.
        ReservationService(self.data_dir).reserve("A", "회의실1", "10:00", "11:00")
        code = (
            "import json, sys\n"
            "from reservation import ReservationService\n"
            "items = ReservationService(sys.argv[1]).list('A')\n"
            "print(json.dumps([[i['room'], i['start'], i['end']] for i in items]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, self.data_dir],
            cwd=str(HERE),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [["회의실1", "10:00", "11:00"]])


if __name__ == "__main__":
    unittest.main()
