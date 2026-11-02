"""mkcopy.py <row> --work DIR --snapshot DIR: fresh copy under <work>/<row>/ (this repository's Day03_new + the ONE snapshot of Day02_new/rag_lab), excluding exactly .env outputs __pycache__ .ipynb_checkpoints .ruff_cache.

Both folders are arguments and have no default: <work> is where the copies and results are written (never inside this repository), <snapshot> is a copy of Day02_new/rag_lab taken once at the start of a run.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]  # tools -> audit -> docs -> Day03_new -> repository
EX = ["--exclude", ".env", "--exclude", "outputs", "--exclude", "__pycache__", "--exclude", ".ipynb_checkpoints", "--exclude", ".ruff_cache"]


def make(row: str, work: Path, snapshot: Path) -> Path:
    if REPO / "Day03_new" in (work, *work.parents):
        raise SystemExit(f"--work {work} lies inside Day03_new: the copy would contain itself")
    dest = work / row
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "Day03_new").mkdir(parents=True)
    (dest / "Day02_new").mkdir(parents=True)
    subprocess.run(["rsync", "-a", *EX, f"{REPO}/Day03_new/", f"{dest}/Day03_new/"], check=True)
    subprocess.run(["rsync", "-a", *EX, f"{snapshot}/", f"{dest}/Day02_new/rag_lab/"], check=True)
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("row")
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    print(make(args.row, args.work.resolve(), args.snapshot.resolve()))
