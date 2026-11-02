"""eval_lab을 import하면 DeepEval 텔레메트리가 꺼지는지 새 프로세스에서 확인한다."""

import os
import subprocess
import sys
from pathlib import Path

DAY05_NEW = Path(__file__).resolve().parent.parent
VARIABLE = "DEEPEVAL_TELEMETRY_OPT_OUT"


def _run(code: str, preset: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != VARIABLE}
    if preset is not None:
        env[VARIABLE] = preset
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=DAY05_NEW,
        env=env,
        capture_output=True,
        text=True,
        timeout=100,
        check=True,
    )
    return done.stdout.strip().splitlines()[-1]


def test_importing_judges_turns_deepeval_telemetry_off():
    code = (
        "import eval_lab.judges\n"
        "from deepeval.telemetry import telemetry_opt_out\n"
        "print(telemetry_opt_out())"
    )
    assert _run(code, preset=None) == "True"


def test_value_already_set_by_user_is_kept():
    code = "import os, eval_lab\nprint(os.environ['DEEPEVAL_TELEMETRY_OPT_OUT'])"
    assert _run(code, preset="YES") == "YES"
