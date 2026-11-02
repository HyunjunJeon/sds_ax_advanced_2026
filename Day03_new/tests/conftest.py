"""저장소 루트에서 pytest를 실행해도 노트북과 똑같이 import가 되게 한다."""
import sys
from datetime import date
from pathlib import Path

import pytest

DAY03_NEW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY03_NEW))
sys.path.insert(0, str(DAY03_NEW / "tests"))


@pytest.fixture
def scope_alpha():
    from rag_lab.corpus import Scope
    return Scope("알파", date(2026, 9, 8))


@pytest.fixture
def desk(scope_alpha):
    from mas_lab.desk import Desk
    from mas_lab.runner import build_retriever
    return Desk(scope_alpha, build_retriever())


@pytest.fixture(autouse=True)
def runs_in_tmp(tmp_path, monkeypatch):
    """run_case는 실행 행을 runner의 ROOT/outputs/runs에 쓴다. 가짜 모델 행이 저자의 실제 실행 행에 섞이지 않게 runner의 ROOT만 옮긴다.

    rag_lab.settings.ROOT는 그대로다. Desk와 말뭉치가 data/를 그 경로로 읽는다.
    """
    monkeypatch.setattr("mas_lab.runner.ROOT", tmp_path)
