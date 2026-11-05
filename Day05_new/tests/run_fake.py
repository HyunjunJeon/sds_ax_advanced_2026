"""Day05_new 노트북을 키와 네트워크 없이 끝까지 돌린다. 모델·Jev·Judge·개선기·Langfuse는 tests/fakes.py의 가짜다.

사용법(저장소 루트에서):
    uv run --no-sync python Day05_new/tests/run_fake.py <path.ipynb>...
    uv run --no-sync python Day05_new/tests/run_fake.py --all

노트북마다 세 번 실행한다.
1. langfuse=fake switches=off: FakeLangfuse(메모리 기록)를 쓴다.
2. langfuse=none switches=off: Langfuse 키가 없어 실제 make_langfuse가 '미설정' RuntimeError를 낸다. 노트북은 로컬 경로로 가야 한다.
3. langfuse=fake switches=on: 임시 사본에서만 'RUN_EXERCISE = False'와 'RUN_OPTIONAL = False'를 True로 바꾼다.

저장된 노트북은 읽기만 한다. 실행하는 것은 메모리 사본이고, .env·산출물·DeepEval 캐시는 실행마다 새 임시 폴더에 둔다.
kernel의 작업 폴더는 Day05_new다. 사본 맨 앞에 주입 셀을 넣어 install_offline_kernel을 부른다.

출력: 실행마다 'OK <파일> langfuse=<fake|none> switches=<on|off> cells=<n> <초>s' 또는
'FAIL <파일> langfuse=<…> switches=<…> cell=<번호> <마지막 오류 줄>', 끝에 'run_fake: <OK 수>/<전체> OK'.
cells는 저장본의 코드 셀 수(주입 셀 제외), cell은 저장본 기준 셀 번호다. 주입 셀이 실패하면 -1, 파일을 읽지 못하면 '-'다.
모든 실행이 OK일 때만 종료 코드 0이다.
"""
from __future__ import annotations

import argparse
import functools
import os
import re
import socket
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError, DeadKernelError
from nbformat.reader import NotJSONError

DAY05_NEW = Path(__file__).resolve().parents[1]
TESTS_DIR = DAY05_NEW / "tests"

# --all이 실행하는 수업 노트북. 없는 파일은 FAIL이다.
NOTEBOOKS = (
    "00-Setup.ipynb",
    "01-Why-Evaluate.ipynb",
    "02-Offline-Golden-Dataset.ipynb",
    "03a-Online-Eval-Trace-Selection.ipynb",
    "03b-Trajectory-Eval.ipynb",
    "04-Agent-Monitoring.ipynb",
    "05-Continuous-Operation.ipynb",
    "06-Lab-Self-Improving-Agent.ipynb",
)
# (langfuse, switches) 순서대로 세 번 실행한다.
PASSES = (("fake", False), ("none", False), ("fake", True))
CELL_TIMEOUT_SECONDS = 300
# Day03_new/tests/run_live.py:27과 같은 생각이다. 셸에 남은 키가 kernel로 넘어가지 않게 이름으로 거른다.
SECRET_NAME_PARTS = ("API_KEY", "TOKEN", "SECRET", "LANGFUSE", "LANGSMITH", "ANTHROPIC", "OPENROUTER", "TYPESAFE")
# 키 자리에 넣는 비밀 아닌 값. 실제 make_* 함수의 '키 있음' 검사만 통과시킨다.
PLACEHOLDER = "offline-placeholder-not-a-key"
SWITCHES = re.compile(r"^(RUN_EXERCISE|RUN_OPTIONAL)\s*=\s*False", re.MULTILINE)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
NETWORK_BLOCKED = "run_fake: 네트워크 차단"


# ---------------------------------------------------------------- kernel 안에서 부르는 부분

def _outside(host: str | bytes | None) -> bool:
    """루프백이 아닌 호스트면 True. None은 바인드용 주소 조회라 바깥 연결이 아니다."""
    if isinstance(host, bytes):
        host = host.decode()
    return host is not None and host not in LOOPBACK_HOSTS


def _block_outbound_network() -> None:
    """socket의 연결·주소 조회를 감싸 루프백 밖으로 나가는 연결을 OSError로 막는다. AF_UNIX와 루프백은 그대로 둔다."""
    connect, connect_ex = socket.socket.connect, socket.socket.connect_ex
    create_connection, getaddrinfo = socket.create_connection, socket.getaddrinfo

    def guard(original):
        def guarded(self, address):
            if self.family in (socket.AF_INET, socket.AF_INET6) and _outside(address[0]):
                raise OSError(NETWORK_BLOCKED)
            return original(self, address)
        return guarded

    def guarded_create_connection(address, *args, **kwargs):
        if _outside(address[0]):
            raise OSError(NETWORK_BLOCKED)
        return create_connection(address, *args, **kwargs)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if _outside(host):
            raise OSError(NETWORK_BLOCKED)
        return getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guard(connect)
    socket.socket.connect_ex = guard(connect_ex)
    socket.create_connection = guarded_create_connection
    socket.getaddrinfo = guarded_getaddrinfo


def install_offline_kernel(*, langfuse: str) -> None:
    """주입 셀이 kernel 안에서 부른다. 바깥 네트워크를 막고 eval_lab의 모델·클라이언트 factory를 가짜로 바꾼다.

    노트북은 이 셀 뒤에 eval_lab.settings와 eval_lab.decisions에서 factory를 가져오므로 모듈 속성 교체가 적용된다.
    가짜 factory도 실제처럼 필요한 키가 비어 있으면 eval_lab.settings.require로 멈춘다.
    langfuse='fake'면 make_langfuse가 kernel마다 하나뿐인 FakeLangfuse를 돌려주고,
    'none'이면 실제 make_langfuse를 그대로 둔다(키가 없어 '미설정' RuntimeError).
    """
    _block_outbound_network()
    # 아래 import는 kernel 안에서만 필요하다. run_fake를 실행하는 쪽 프로세스는 eval_lab을 불러오지 않는다.
    import fakes
    from eval_lab import decisions, rsi, settings

    def make_agent_model(config: settings.Settings) -> fakes.NotebookAgentModel:
        """가짜 에이전트(NotebookAgentModel)."""
        settings.require(config, settings.provider_of(config).key_env)
        return fakes.NotebookAgentModel()

    def make_judge_model(config: settings.Settings) -> fakes.NotebookJudgeModel:
        """가짜 Judge(NotebookJudgeModel). DeepEvalAnthropic에 감싸도 된다."""
        settings.require(config, settings.provider_of(config).key_env)
        return fakes.NotebookJudgeModel()

    def make_improver_model(config: settings.Settings):
        """키 없는 scripted 개선기(rsi.scripted_improver('sensible'))."""
        settings.require(config, settings.provider_of(config).key_env)
        return rsi.scripted_improver("sensible")

    def make_decider(config: settings.Settings | None = None, *,
                     on_usage: decisions.UsageCallback | None = None) -> fakes.FakeDecider:
        """대본 NOTEBOOK_DECIDER_SCRIPT로 답하는 가짜 Jev."""
        settings.require(config or settings.load_settings(), "TYPESAFE_API_KEY")
        return fakes.FakeDecider(fakes.NOTEBOOK_DECIDER_SCRIPT, on_usage=on_usage)

    shared_langfuse = functools.cache(fakes.FakeLangfuse)

    def make_langfuse(config: settings.Settings | None = None) -> fakes.FakeLangfuse:
        """kernel마다 하나인 FakeLangfuse. 여러 셀이 같은 기록을 본다."""
        settings.require(config or settings.load_settings(), "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
        return shared_langfuse()

    settings.make_agent_model = make_agent_model
    settings.make_judge_model = make_judge_model
    settings.make_improver_model = make_improver_model
    decisions.make_decider = make_decider
    if langfuse == "fake":
        settings.make_langfuse = make_langfuse


def injected_source(langfuse: str) -> str:
    """임시 사본 맨 앞에 넣는 셀. Day05_new와 tests를 sys.path에 두고 install_offline_kernel을 부른다."""
    return (
        "# run_fake가 임시 사본에만 넣은 셀이다. 저장된 노트북에는 없다.\n"
        "import sys as _run_fake_sys\n"
        f"_run_fake_sys.path.insert(0, {str(DAY05_NEW)!r})\n"
        f"_run_fake_sys.path.append({str(TESTS_DIR)!r})\n"
        "import run_fake as _run_fake\n"
        f"_run_fake.install_offline_kernel(langfuse={langfuse!r})\n"
        "del _run_fake_sys, _run_fake\n"
    )


# ---------------------------------------------------------------- 실행하는 쪽

@dataclass(frozen=True)
class PassResult:
    """노트북 한 번 실행의 결과. executed는 실행을 마친 사본(주입 셀 포함, 출력 포함)이다."""

    notebook: str
    langfuse: str
    switches: bool
    ok: bool
    cells: int
    seconds: float
    failed_cell: int | str | None
    error: str
    executed: nbformat.NotebookNode | None

    def line(self) -> str:
        label = f"{self.notebook} langfuse={self.langfuse} switches={'on' if self.switches else 'off'}"
        if self.ok:
            return f"OK {label} cells={self.cells} {self.seconds:.1f}s"
        return f"FAIL {label} cell={self.failed_cell} {self.error}"


def kernel_environment(work: Path, langfuse: str) -> dict[str, str]:
    """kernel 환경 변수. 비밀 이름을 거르고, 자리값 .env·임시 산출물 폴더·DeepEval 설정을 넣는다.

    DEEPEVAL_DISABLE_DOTENV: deepeval은 import할 때 작업 폴더(Day05_new)의 .env를 os.environ에 올린다.
    끄지 않으면 저자의 실제 키가 kernel에 들어온다.
    """
    keys = ["OPENGATEWAY_API_KEY", "TYPESAFE_API_KEY"]
    if langfuse == "fake":
        keys += ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    env_file = work / "offline.env"
    env_file.write_text("".join(f"{name}={PLACEHOLDER}\n" for name in keys), encoding="utf-8")
    kept = {name: value for name, value in os.environ.items()
            if not any(part in name.upper() for part in SECRET_NAME_PARTS)}
    return {
        **kept,
        "DAY05_ENV_FILE": str(env_file),
        "DAY05_OUTPUT_ROOT": str(work / "outputs"),
        "DEEPEVAL_TELEMETRY_OPT_OUT": "1",
        "DEEPEVAL_CACHE_FOLDER": str(work / "deepeval"),
        "DEEPEVAL_DISABLE_DOTENV": "1",
    }


def prepare_copy(stored: nbformat.NotebookNode, *, langfuse: str, switches: bool) -> nbformat.NotebookNode:
    """저장본의 사본에 주입 셀을 넣고, switches면 RUN_EXERCISE·RUN_OPTIONAL을 켠다. 저장본은 바꾸지 않는다."""
    copy = nbformat.from_dict(stored)
    if switches:
        for cell in copy.cells:
            if cell.cell_type == "code":
                cell.source = SWITCHES.sub(lambda match: f"{match.group(1)} = True", cell.source)
    copy.cells.insert(0, nbformat.v4.new_code_cell(injected_source(langfuse)))
    return copy


def _error_line(error: Exception) -> str:
    """오류의 마지막 한 줄 요약. 셀 오류는 '이름: 값의 첫 줄'이다."""
    if isinstance(error, CellExecutionError):
        name, lines = error.ename, (error.evalue or "").strip().splitlines()[:1]
    else:
        name, lines = type(error).__name__, str(error).strip().splitlines()[-1:]
    return f"{name}: {''.join(lines)}".rstrip()


def run_pass(notebook: Path, *, langfuse: str, switches: bool) -> PassResult:
    """노트북 한 개를 한 번 실행한다. 실패하면 첫 실패 셀에서 멈춘다."""
    started = time.monotonic()

    def failed(cell: int | str, error: str, executed: nbformat.NotebookNode | None = None) -> PassResult:
        return PassResult(notebook.name, langfuse, switches, False, 0, time.monotonic() - started, cell, error, executed)

    try:
        stored = nbformat.read(notebook, as_version=4)
    except FileNotFoundError:
        return failed("-", "FileNotFoundError: 파일이 없습니다")
    except (OSError, NotJSONError) as error:
        return failed("-", f"{type(error).__name__}: 노트북을 읽을 수 없습니다")

    copy = prepare_copy(stored, langfuse=langfuse, switches=switches)
    with tempfile.TemporaryDirectory(prefix="run_fake-") as work:
        client = NotebookClient(copy, kernel_name="python3", timeout=CELL_TIMEOUT_SECONDS,
                                resources={"metadata": {"path": str(DAY05_NEW)}})
        with client.setup_kernel(env=kernel_environment(Path(work), langfuse)):
            for index, cell in enumerate(copy.cells):
                if cell.cell_type != "code":
                    continue
                try:
                    client.execute_cell(cell, index)
                except (CellExecutionError, CellTimeoutError, DeadKernelError) as error:
                    return failed(index - 1, _error_line(error), copy)
    code_cells = sum(1 for cell in stored.cells if cell.cell_type == "code")
    return PassResult(notebook.name, langfuse, switches, True, code_cells, time.monotonic() - started, None, "", copy)


def run_all_passes(notebook: Path) -> list[PassResult]:
    """PASSES 세 가지로 차례로 실행하고, 결과 줄을 바로 출력한다."""
    results = []
    for langfuse, switches in PASSES:
        result = run_pass(notebook, langfuse=langfuse, switches=switches)
        print(result.line(), flush=True)
        results.append(result)
    return results


def main(argv: list[str], *, day_dir: Path = DAY05_NEW) -> int:
    """CLI 진입점. day_dir은 --all이 노트북을 찾는 폴더다(시험이 빈 폴더를 넘길 수 있다)."""
    parser = argparse.ArgumentParser(description="Day05_new 노트북 오프라인(가짜 모델·가짜 Langfuse) 실행")
    parser.add_argument("notebooks", nargs="*", type=Path, help="실행할 .ipynb 경로")
    parser.add_argument("--all", action="store_true", help=f"{day_dir.name}의 수업 노트북 {len(NOTEBOOKS)}개")
    args = parser.parse_args(argv)
    if args.all == bool(args.notebooks):
        parser.error("노트북 경로들 또는 --all 중 하나만 주세요.")
    notebooks = [day_dir / name for name in NOTEBOOKS] if args.all else [path.resolve() for path in args.notebooks]
    results = [result for notebook in notebooks for result in run_all_passes(notebook)]
    passed = sum(result.ok for result in results)
    print(f"run_fake: {passed}/{len(results)} OK")
    return 0 if results and passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
