"""Day07_new 수업용 보조 모듈. 하위 모듈은 import하지 않는다(각 모듈을 따로 쓴다)."""
from __future__ import annotations

import pathlib

VLLM_VERSION = "0.32.0"
VLLM_COMMIT = "5df63a7203cdb9328d824a27b682e77c7b9928be"
DEFAULT_BLOCK_SIZE = 16
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
