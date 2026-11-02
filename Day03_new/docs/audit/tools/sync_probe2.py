"""Wider old-versus-new probe of one Day03_new tree. No model, no EXA, no .env, no gold.

usage: sync_probe2.py <day03_tree> <out.jsonl> [--break-rank]
Part 1: every chunk's text pieces as queries, one fresh context each, in every case scope.
Part 2: many searches on ONE context with the real default byte limit, as an Agent does, in order.
Part 3: the same with a small byte limit, which forces the overflow path.
"""
import json
import random
import sys
from datetime import date
from pathlib import Path

tree, out_path = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(tree))

from rag_lab.corpus import Scope, load_cases, load_corpus  # noqa: E402
from rag_lab.evidence import Budget, RetrievalContext  # noqa: E402
from rag_lab.retrieval import Retriever  # noqa: E402

retriever = Retriever(load_corpus())
assert retriever.mode == "bm25"
if "--break-rank" in sys.argv:  # negative control: a changed ranking must change the output
    original = Retriever.rank
    Retriever.rank = lambda self, query, scope=None, limit=6: list(reversed(original(self, query, scope, limit)))

cases = load_cases()
scopes = sorted({(c["entity"], c["as_of"]) for c in cases})
pieces = sorted({text for chunk in retriever.chunks.values() for text in (chunk.text[:40], chunk.text[:120])})
questions = sorted({c["question"] for c in cases if isinstance(c.get("question"), str)})
big = {"max_tool_calls": 10**9, "max_searches": 10**9, "max_reads": 10**9, "max_seconds": 10**9}


def timeless(events):
    return [{k: v for k, v in event.items() if k != "seconds"} for event in events]


def dump(out, **row):
    if "events" in row:  # the clock differs between any two runs, so it is not part of the comparison
        row["events"] = timeless(row["events"])
    out.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


counts = {"part1": 0, "part2": 0, "part3": 0, "excluded2": 0, "excluded3": 0}
with out_path.open("w", encoding="utf-8") as out:
    for entity, as_of in scopes:
        scope = Scope(entity, date.fromisoformat(as_of))
        for query in [*questions, *pieces]:
            for limit in (3, 6, 10):
                context = RetrievalContext(retriever, scope, Budget(**big))
                dump(out, part=1, scope=[entity, as_of], query=query, limit=limit, result=context.search(query, limit),
                     context_bytes=context._context_bytes(), events=context.budget.events)
                counts["part1"] += 1
        for part, limit_bytes in ((2, 24000), (3, 3000)):
            for seed in range(20):
                order = random.Random(seed).sample([*questions, *pieces], 12)
                context = RetrievalContext(retriever, scope, Budget(max_context_bytes=limit_bytes, **big))
                for query in order:
                    dump(out, part=part, scope=[entity, as_of], seed=seed, query=query, result=context.search(query, 6),
                         context_bytes=context._context_bytes())
                    counts[f"part{part}"] += 1
                excluded = [e for e in context.budget.events if e.get("event") == "context_excluded"]
                counts[f"excluded{part}"] += len(excluded)
                dump(out, part=part, seed=seed, events=context.budget.events)
print(tree.name, counts)
