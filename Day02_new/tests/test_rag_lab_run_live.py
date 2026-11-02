"""run_live.py를 임시 복사본에서 CLI로 실행한다. 모델을 부르지 않는 셀만 쓴다."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

DAY02_NEW = Path(__file__).resolve().parents[1]
FAKE_KEY = "sk-test-not-a-real-key-1234567890"
USAGE_CELL = ("import json, os\n"
              "with open(os.environ['DAY02_USAGE_LOG'], 'a') as log:\n"
              "    log.write(json.dumps({'model': 'm', 'input_tokens': 10, 'output_tokens': 3, 'cache_read_tokens': 0}) + '\\n')\n")


def make_copy(tmp_path: Path) -> Path:
    root = tmp_path / "복사본 폴더" / "Day02_new"
    shutil.copytree(DAY02_NEW / "rag_lab", root / "rag_lab", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "tests").mkdir()
    shutil.copy(DAY02_NEW / "tests" / "run_live.py", root / "tests")
    (root / ".env").write_text(f"ANTHROPIC_API_KEY={FAKE_KEY}\n", encoding="utf-8")
    return root


def run_notebook(root: Path, *cells: str) -> tuple[subprocess.CompletedProcess, Path]:
    path = root / "07-시험 노트북.ipynb"
    nbformat.write(new_notebook(cells=[new_markdown_cell("# 제목"), *map(new_code_cell, cells)]), path)
    done = subprocess.run([sys.executable, str(root / "tests" / "run_live.py"), str(path)], capture_output=True,
                          text=True, timeout=180, cwd=root.parent)
    return done, root / "outputs" / "live"


def report_of(live: Path) -> dict:
    return json.loads((live / "07-시험 노트북.json").read_text(encoding="utf-8"))


def test_success_reports_cells_tokens_and_finished(tmp_path):
    root = make_copy(tmp_path)
    done, live = run_notebook(root, "import pathlib\nassert pathlib.Path.cwd().name == 'Day02_new'", USAGE_CELL, USAGE_CELL)
    assert done.returncode == 0, done.stderr
    assert "LIVE RUN OK 07-시험 노트북 errors=0" in done.stdout
    report = report_of(live)
    assert '"finished": true' in (live / "07-시험 노트북.json").read_text(encoding="utf-8")
    assert [(c["index"], c["status"]) for c in report["cells"]] == [(1, "ok"), (2, "ok"), (3, "ok")]
    assert all(c["seconds"] >= 0 for c in report["cells"]) and report["errors"] == []
    assert (report["model_calls"], report["input_tokens"], report["output_tokens"]) == (2, 20, 6)
    assert report["notebook"] == "07-시험 노트북.ipynb" and report["total_seconds"] > 0
    assert (live / "07-시험 노트북.usage.jsonl").is_file()
    assert nbformat.read(live / "07-시험 노트북.executed.ipynb", as_version=4).cells[1].execution_count == 1


def test_first_error_stops_run_redacts_key_and_exits_one(tmp_path):
    root = make_copy(tmp_path)
    marker = root / "뒤의 셀이 실행됨"
    done, live = run_notebook(root, f"raise ValueError('거부된 키 {FAKE_KEY}')", f"open({str(marker)!r}, 'w')")
    assert done.returncode == 1
    assert "LIVE RUN OK" not in done.stdout and not marker.exists()
    report = report_of(live)
    assert report["finished"] is False
    assert report["errors"] == [{"index": 1, "type": "ValueError", "message": "거부된 키 ***"}]
    assert [c["status"] for c in report["cells"]] == ["error"]
    assert FAKE_KEY not in (live / "07-시험 노트북.executed.ipynb").read_text(encoding="utf-8")


def test_key_printed_by_a_cell_does_not_reach_the_saved_copy(tmp_path):
    root = make_copy(tmp_path)
    done, live = run_notebook(root, f"print('{FAKE_KEY}')")
    assert done.returncode == 0, done.stderr
    assert FAKE_KEY not in (live / "07-시험 노트북.executed.ipynb").read_text(encoding="utf-8")


def test_second_run_starts_a_fresh_usage_log(tmp_path):
    root = make_copy(tmp_path)
    run_notebook(root, USAGE_CELL)
    _, live = run_notebook(root, USAGE_CELL)
    assert report_of(live)["model_calls"] == 1


def test_kernel_does_not_receive_shell_secrets(tmp_path):
    root = make_copy(tmp_path)
    path = root / "07-시험 노트북.ipynb"
    cell = "import os\nassert 'ANTHROPIC_API_KEY' not in os.environ and 'GH_TOKEN' not in os.environ"
    nbformat.write(new_notebook(cells=[new_code_cell(cell)]), path)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "ANTHROPIC_API_KEY": "셸에-남은-값", "GH_TOKEN": "x"}
    done = subprocess.run([sys.executable, str(root / "tests" / "run_live.py"), str(path)], capture_output=True, text=True,
                          timeout=180, env=env)
    assert done.returncode == 0, done.stderr


def test_missing_notebook_and_bad_arguments_exit_two(tmp_path):
    root = make_copy(tmp_path)
    script = str(root / "tests" / "run_live.py")
    missing = subprocess.run([sys.executable, script, str(root / "없음.ipynb")], capture_output=True, text=True, timeout=60)
    assert missing.returncode == 2 and "읽을 수 없습니다" in missing.stderr
    assert subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=60).returncode == 2


def test_rerun_copies_the_previous_records_to_history_before_replacing_them(tmp_path):
    root = make_copy(tmp_path)
    _, live = run_notebook(root, USAGE_CELL, USAGE_CELL)
    first_usage = (live / "07-시험 노트북.usage.jsonl").read_text(encoding="utf-8")
    assert not (live / "history").exists()
    run_notebook(root, USAGE_CELL)
    (kept,) = (live / "history").iterdir()
    assert (kept / "07-시험 노트북.usage.jsonl").read_text(encoding="utf-8") == first_usage
    assert json.loads((kept / "07-시험 노트북.json").read_text(encoding="utf-8"))["model_calls"] == 2
    assert (kept / "07-시험 노트북.executed.ipynb").is_file()
    assert report_of(live)["model_calls"] == 1


def test_each_cell_records_the_usage_line_range_it_produced(tmp_path):
    root = make_copy(tmp_path)
    done, live = run_notebook(root, USAGE_CELL, "x = 1", USAGE_CELL + USAGE_CELL)
    assert done.returncode == 0, done.stderr
    assert {c["index"]: c["usage_lines"] for c in report_of(live)["cells"]} == {1: [0, 1], 2: [1, 1], 3: [1, 3]}
