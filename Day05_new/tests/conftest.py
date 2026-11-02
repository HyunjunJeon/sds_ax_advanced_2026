"""오프라인 시험 환경. .env를 읽지 않고, 키 환경 변수를 지우고, IP 네트워크 연결을 막는다."""
import socket
import sys
from pathlib import Path

import pytest

DAY05_ROOT = Path(__file__).resolve().parents[1]
if str(DAY05_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY05_ROOT))

from eval_lab.settings import (
    ALL_ENV_NAMES,
)

_IP_FAMILIES = (socket.AF_INET, socket.AF_INET6)


def _refuse_ip_connect(connect):
    """AF_INET/AF_INET6 연결만 막고 Unix 소켓과 subprocess 파이프는 그대로 둔다."""
    def guarded(self, address):
        if self.family in _IP_FAMILIES:
            raise RuntimeError("tests must not use the network")
        return connect(self, address)
    return guarded


@pytest.fixture(autouse=True)
def offline_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DAY05_ENV_FILE", str(tmp_path / "no-such.env"))
    for name in ALL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _refuse_ip_connect(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse_ip_connect(socket.socket.connect_ex))
