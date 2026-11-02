"""dryrun.py --collected FILE: apply every row's edits in memory to the real file of this repository's Day03_new (no write) and report (a) rows whose `old` text does not occur exactly once,
(b) rows whose edit is a no-op, (c) pre-registered test names (expect) that match no collected test id of the clean copy.
FILE lists those test ids, one per line (the output of `pytest --collect-only -q tests` run in a clean copy, without the summary lines); it is not kept in this folder."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from rows import ROWS, matches
ROOT = Path(__file__).resolve().parents[3]  # tools -> audit -> docs -> Day03_new
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--collected", required=True, type=Path)
collected = parser.parse_args().collected.read_text(encoding="utf-8").splitlines()
bad, noop, noexpect = [], [], []
for rid, row in ROWS.items():
    if row["kind"] == "notebook":
        continue
    if row["edits"]:
        text = (ROOT / row["file"]).read_text(encoding="utf-8")
        for old, new in row["edits"]:
            n = text.count(old)
            if n != 1:
                bad.append((rid, n, old[:90])); break
            if old == new:
                noop.append(rid)
            text = text.replace(old, new)
    if row["nb_edits"]:
        nb = json.loads((ROOT / row["file"]).read_text(encoding="utf-8"))
        for cid, old, new in row["nb_edits"]:
            cells = [c for c in nb["cells"] if c.get("id") == cid]
            if len(cells) != 1:
                bad.append((rid, f"cell {cid} x{len(cells)}", "")); break
            src = cells[0]["source"] if isinstance(cells[0]["source"], str) else "".join(cells[0]["source"])
            if src.count(old) != 1:
                bad.append((rid, src.count(old), old[:90])); break
    for e in row["expect"]:
        if not any(matches(e, c) for c in collected):
            noexpect.append((rid, e))
print("rows", len(ROWS), "bad", len(bad), "noop", noop, "expect-without-collected-test", len(noexpect))
for b in bad: print("BAD", b)
for b in noexpect: print("NOEXPECT", b)
