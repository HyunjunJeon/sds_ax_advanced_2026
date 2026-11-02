#!/usr/bin/env python3
"""Check the `file:line` citations in a Day03_new document against the files they cite.

usage: check_citations.py <doc> [--strict] [--allow <file>] [--root <Day03_new dir>] [--quiet]
       check_citations.py --self-test

What is a citation: `<path>.<ext>:<N>` or `<path>.<ext>:<N>-<M>`, backticked or plain. <path> is relative to Day03_new
(mas_lab, rag_lab, tests, data, docs, ...) or to the document's folder; a leading `Day03_new/` or `../` is fine, a bare
basename (`hybrid.py:90`) is accepted when exactly one file of that name exists under Day03_new. URLs and clock times
(`09:28`) are not citations because they have no `<name>.<ext>` before the colon.

Table form: in a markdown table row that names files in backticks (`mas_lab/desk.py`) and lists symbols as `Name:N` or
`Name:N-M`, each `Name:N` is checked against the files of that row (this is the form of AGENTS.md chapter 4).

Hard failures (exit 1, also without --strict): the file does not exist (or the bare basename is ambiguous), or N is past
the last line of the file, or M < N.
--strict: for every citation, take the backticked identifiers of the same sentence (a table cell is one sentence). If
there is at least one, one of them must appear in lines N-1 .. M+1 of the cited file; otherwise it is a MISMATCH (exit 1).
A citation whose sentence has no backticked identifier is counted as `no_identifier` and is NOT verified by --strict.

--allow <file>: one entry per line, tab separated. `PREFIX<TAB>REASON` exempts every finding on the document line that
starts with PREFIX (exact text); `PREFIX<TAB>CITATION<TAB>REASON` exempts only that citation text. Lines starting with #
are comments. An allowed finding is still printed (as ALLOWED) and counted. Unused entries are printed as UNUSED-ALLOW.

No bytecode is written; nothing outside the document and the temporary self-test folder is touched.
"""
from __future__ import annotations

import argparse
import keyword
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

DAY03_NEW = Path(__file__).resolve().parents[3]  # tools -> audit -> docs -> Day03_new
EXTENSIONS = "py|md|json|jsonl|ipynb|toml|txt|yaml|yml|cfg|ini|csv|sh|lock|example"
CITE = re.compile(
    r"(?<![\w/.\-])((?:\.\./)*(?:[\w.\-]+/)*(?:[\w\-]+\.(?:" + EXTENSIONS + r")|\.gitignore)):(\d+)(?:[-–](\d+))?(?![\w])"
)
SYMBOL_CITE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(\d+)(?:-(\d+))?$")
BARE_RANGE = re.compile(r"^:(\d+)(?:-(\d+))?$")
PATH_TOKEN = re.compile(r"^(?:\.\./)*(?:[\w.\-]+/)*(?:[\w\-]+\.(?:" + EXTENSIONS + r")|\.gitignore)$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*(?:\(\))?$")
SEARCH_DIRS = ("mas_lab", "rag_lab", "tests", "docs", "data", "data/business", "data/support", "skills", "")
PROTECTED = {"gold.jsonl"}  # the evaluation answer key: existence is checked, the content is never opened
NOT_IDENTIFIERS = {"True", "False", "None"}


@dataclass
class Finding:
    kind: str  # missing | ambiguous | past_end | bad_range | mismatch
    doc_line: int
    citation: str
    detail: str
    allowed: str | None = None


@dataclass
class Report:
    citations: int = 0
    verified_files: int = 0
    no_identifier: int = 0
    strict_checked: int = 0
    strict_pass: int = 0
    table_symbols: int = 0
    protected: int = 0
    findings: list[Finding] = field(default_factory=list)
    unused_allow: list[str] = field(default_factory=list)

    def active(self, kinds: set[str]) -> list[Finding]:
        return [f for f in self.findings if f.kind in kinds and not f.allowed]


class Resolver:
    def __init__(self, day03: Path, doc_dir: Path):
        self.day03, self.doc_dir, self.repo = day03, doc_dir, day03.parent
        self._lines: dict[Path, list[str]] = {}

    def lines(self, path: Path) -> list[str]:
        if path.name in PROTECTED:
            raise PermissionError(f"{path.name} is the evaluation answer key and is never opened by this checker")
        if path not in self._lines:
            self._lines[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self._lines[path]

    def resolve(self, raw: str) -> tuple[Path | None, str]:
        """Return (path, note). path None means missing or ambiguous (note says which)."""
        raw = raw.removeprefix("./")
        candidates = [self.doc_dir / raw, self.day03 / raw, self.repo / raw]
        if raw.startswith("Day03_new/"):
            candidates.insert(0, self.day03 / raw.removeprefix("Day03_new/"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve(), ""
        if "/" not in raw:
            found = {p.resolve() for d in (self.doc_dir, *(self.day03 / s for s in SEARCH_DIRS)) if (p := d / raw).is_file()}
            if len(found) == 1:
                return found.pop(), "bare"
            if len(found) > 1:
                return None, "ambiguous: " + ", ".join(sorted(str(p.relative_to(self.repo)) for p in found))
        return None, "file not found"


def mask_backticks(line: str) -> tuple[str, list[str]]:
    spans: list[str] = []

    def keep(match: re.Match) -> str:
        spans.append(match.group(1))
        return f"\x00{len(spans) - 1}\x00"

    return re.sub(r"`([^`]*)`", keep, line), spans


def sentence_of(masked: str, position: int) -> str:
    """The sentence of the masked text around `position`; boundaries are '. ', '.' at end, '? ', '! ' and '|' (table cells)."""
    bounds = [0] + [m.end() for m in re.finditer(r"(?<=[.!?])\s+|\|", masked)] + [len(masked)]
    start = max(b for b in bounds if b <= position)
    end = min((b for b in bounds if b > position), default=len(masked))
    return masked[start:end]


def identifiers_in(sentence: str, spans: list[str]) -> list[str]:
    found: list[str] = []
    for index in {int(n) for n in re.findall(r"\x00(\d+)\x00", sentence)}:
        token = spans[index].strip()
        if CITE.search(token) or SYMBOL_CITE.match(token) or PATH_TOKEN.match(token) or token in NOT_IDENTIFIERS:
            continue
        lead = re.match(r"^([A-Za-z_][A-Za-z0-9_]+)\s*(?:=|\()", token)
        if lead and not IDENT.match(token):
            token = lead.group(1)  # `max_retries=0` and `Budget(...)` name `max_retries` and `Budget`
        if not IDENT.match(token) or keyword.iskeyword(token):
            continue
        for part in token.removesuffix("()").split("."):
            if part not in NOT_IDENTIFIERS and part not in found:
                found.append(part)
    return found


def where_is(ident: str, lines: list[str]) -> str:
    word = re.compile(rf"\b{re.escape(ident)}\b")
    exact = [n for n, text in enumerate(lines, 1) if re.match(rf"^\s*(?:async\s+def|def|class)\s+{re.escape(ident)}\b", text)
             or re.match(rf"^{re.escape(ident)}\s*[:=]", text)]
    anywhere = [n for n, text in enumerate(lines, 1) if word.search(text)]
    if exact:
        return f"`{ident}` is defined at line {', '.join(map(str, exact[:3]))}"
    if anywhere:
        return f"`{ident}` appears at line {', '.join(map(str, anywhere[:4]))}"
    return f"`{ident}` does not appear in the file"


def range_has(lines: list[str], idents: list[str], low: int, high: int) -> list[str]:
    window = lines[max(low - 1, 0):high]
    text = "\n".join(window)
    return [i for i in idents if re.search(rf"(?<![A-Za-z0-9_]){re.escape(i)}(?![A-Za-z0-9_])", text)]


def load_allow(path: Path | None) -> list[list[str]]:
    entries: list[list[str]] = []
    if path:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip() and not raw.lstrip().startswith("#"):
                entries.append(raw.split("\t"))
    return entries


def check(doc: Path, *, strict: bool, allow: Path | None = None, day03: Path = DAY03_NEW) -> Report:
    report = Report()
    resolver = Resolver(day03, doc.parent)
    allow_entries = load_allow(allow)
    used: set[int] = set()
    in_fence = False

    def add(kind: str, number: int, citation: str, detail: str, line_text: str) -> None:
        finding = Finding(kind, number, citation, detail)
        for index, entry in enumerate(allow_entries):
            prefix = entry[0]
            if line_text.startswith(prefix) and (len(entry) < 3 or entry[1] == citation):
                finding.allowed = entry[-1] if len(entry) > 1 else "(no reason given)"
                used.add(index)
                break
        report.findings.append(finding)

    def check_range(number: int, citation: str, path: Path, start: int, end: int | None, idents: list[str], line_text: str) -> None:
        if path.name in PROTECTED:
            report.protected += 1  # exists, so it is not 'missing'; the line is not checked because the file is not opened
            return
        total = len(resolver.lines(path))
        last = end if end is not None else start
        if last < start or start < 1:
            add("bad_range", number, citation, f"range {start}-{last} is not valid", line_text)
            return
        if last > total:
            add("past_end", number, citation, f"line {last} is past the end ({path.relative_to(day03.parent)} has {total} lines)", line_text)
            return
        report.verified_files += 1
        if not strict:
            return
        if not idents:
            report.no_identifier += 1
            return
        report.strict_checked += 1
        lines = resolver.lines(path)
        hit = range_has(lines, idents, start - 1, last + 1)
        if hit:
            report.strict_pass += 1
            return
        add("mismatch", number, citation,
            f"none of {', '.join('`' + i + '`' for i in idents)} in lines {max(start - 1, 1)}-{min(last + 1, total)}; "
            + "; ".join(where_is(i, lines) for i in idents[:3]), line_text)

    for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        masked, spans = mask_backticks(line)
        # Plain-text citations may sit inside or outside backticks: scan the raw line, locate the sentence by position in the masked line.
        row_files = [resolver.resolve(s.strip()) for s in spans if PATH_TOKEN.match(s.strip())] if line.lstrip().startswith("|") else []
        row_paths = [p for p, _ in row_files if p and p.name not in PROTECTED]
        for match in CITE.finditer(line):
            raw, first, last = match.group(1), int(match.group(2)), match.group(3)
            citation = match.group(0)
            report.citations += 1
            path, note = resolver.resolve(raw)
            if path is None:
                kind = "ambiguous" if note.startswith("ambiguous") else "missing"
                add(kind, number, citation, note if kind == "ambiguous" else f"{raw}: {note}", line)
                continue
            plain_position = len(mask_backticks(line[:match.start()])[0])
            sentence = sentence_of(masked, min(plain_position, max(len(masked) - 1, 0)))
            check_range(number, citation, path, first, int(last) if last else None, identifiers_in(sentence, spans), line)
        if row_paths:
            for index, span in enumerate(spans):
                symbol = SYMBOL_CITE.match(span.strip())
                bare = BARE_RANGE.match(span.strip())
                if not (symbol or bare):
                    continue
                report.citations += 1
                report.table_symbols += 1
                first = int((symbol or bare).group(2 if symbol else 1))
                tail = (symbol or bare).group(3 if symbol else 2)
                last = int(tail) if tail else first
                citation = span.strip()
                longest = max(len(resolver.lines(p)) for p in row_paths)
                if last < first or first < 1 or last > longest:
                    add("past_end" if last > longest else "bad_range", number, citation,
                        f"line {last} is past the end of every file of this row ({', '.join(str(p.relative_to(day03.parent)) for p in row_paths)}; longest {longest} lines)"
                        if last > longest else f"range {first}-{last} is not valid", line)
                    continue
                report.verified_files += 1
                if not strict or not symbol:
                    continue
                report.strict_checked += 1
                name = symbol.group(1)
                homes = [p for p in row_paths if range_has(resolver.lines(p), [name], first - 1, last + 1)]
                if homes:
                    report.strict_pass += 1
                    continue
                elsewhere = [f"{p.relative_to(day03.parent)}: {where_is(name, resolver.lines(p))}" for p in row_paths]
                add("mismatch", number, citation,
                    f"`{name}` is not in lines {max(first - 1, 1)}-{last + 1} of any file of this row; " + "; ".join(elsewhere), line)
    report.unused_allow = ["\t".join(entry) for index, entry in enumerate(allow_entries) if index not in used]
    return report


def render(report: Report, doc: Path, *, strict: bool, quiet: bool) -> int:
    hard = {"missing", "ambiguous", "past_end", "bad_range"}
    for finding in report.findings:
        tag = "ALLOWED" if finding.allowed else ("MISMATCH" if finding.kind == "mismatch" else "FAIL")
        if quiet and finding.allowed:
            continue
        suffix = f"  [allowed: {finding.allowed}]" if finding.allowed else ""
        print(f"{tag:8} {doc.name}:{finding.doc_line}  `{finding.citation}`  {finding.kind}: {finding.detail}{suffix}")
    for entry in report.unused_allow:
        print(f"UNUSED-ALLOW  {entry}")
    failing_hard, failing_mismatch = report.active(hard), report.active({"mismatch"})
    allowed = sum(1 for f in report.findings if f.allowed)
    print(
        f"citations={report.citations} resolved_in_range={report.verified_files} hard_failures={len(failing_hard)} "
        f"(missing/ambiguous={sum(f.kind in {'missing', 'ambiguous'} for f in failing_hard)} "
        f"past_end={sum(f.kind == 'past_end' for f in failing_hard)} bad_range={sum(f.kind == 'bad_range' for f in failing_hard)}) "
        f"table_symbol_citations={report.table_symbols} "
        + (f"strict_checked={report.strict_checked} strict_pass={report.strict_pass} mismatches={len(failing_mismatch)} "
           f"no_identifier(not verified)={report.no_identifier} " if strict else "strict=off ")
        + f"allowed={allowed} protected_not_opened={report.protected}"
    )
    return 1 if failing_hard or failing_mismatch else 0


def self_test() -> None:
    with tempfile.TemporaryDirectory() as scratch:
        base = Path(scratch).resolve()  # the resolver returns resolved paths; /var is a link to /private/var on macOS
        day03 = base / "Day03_new"
        (day03 / "mas_lab").mkdir(parents=True)
        (day03 / "docs").mkdir()
        (day03 / "mas_lab" / "a.py").write_text("import os\n\n\ndef good_func():\n    return 1\n\n\nclass Thing:\n    pass\n", encoding="utf-8")
        (day03 / "mas_lab" / "b.py").write_text("X = 1\nY = 2\n", encoding="utf-8")
        (day03 / ".gitignore").write_text(".env\noutputs/\n", encoding="utf-8")
        doc = day03 / "AGENTS.md"

        def run(text: str, *, strict: bool, allow_text: str | None = None) -> tuple[int, Report]:
            doc.write_text(text, encoding="utf-8")
            allow = None
            if allow_text is not None:
                allow = base / "allow.tsv"
                allow.write_text(allow_text, encoding="utf-8")
            report = check(doc, strict=strict, allow=allow, day03=day03)
            import io
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):
                code = render(report, doc, strict=strict, quiet=False)
            return code, report

        good = "`good_func`는 4번째 줄에 있습니다 (`mas_lab/a.py:4`).\n"
        past_end = "범위 밖입니다 (`mas_lab/a.py:99`).\n"
        wrong_id = "`other_func`는 여기 있습니다 (`mas_lab/a.py:4`).\n"

        code, report = run(good, strict=True)
        assert code == 0 and report.citations == 1 and report.strict_pass == 1, (code, report)
        code, report = run(past_end, strict=False)
        assert code == 1 and report.findings[0].kind == "past_end", (code, report)
        code, report = run(wrong_id, strict=False)
        assert code == 0, "wrong identifier is only a --strict finding"
        code, report = run(wrong_id, strict=True)
        assert code == 1 and report.findings[0].kind == "mismatch" and "does not appear" in report.findings[0].detail, report
        code, report = run(good + past_end + wrong_id, strict=True)
        assert code == 1 and sorted(f.kind for f in report.findings) == ["mismatch", "past_end"], report.findings

        # one-line tolerance: the identifier may sit on the line before or after the cited line
        code, _ = run("`good_func`(`mas_lab/a.py:3`) und `Thing`(`mas_lab/a.py:7-9`).\n", strict=True)
        assert code == 0
        # range end counts
        code, report = run("`Thing`(`mas_lab/a.py:8-30`).\n", strict=False)
        assert code == 1 and report.findings[0].kind == "past_end"
        # missing file, Day03_new prefix, bare basename, plain (not backticked) citation, .gitignore
        code, report = run("`x`(`mas_lab/nope.py:1`)\n", strict=False)
        assert code == 1 and report.findings[0].kind == "missing"
        code, _ = run("`good_func` Day03_new/mas_lab/a.py:4 und `Y` b.py:2\n", strict=True)
        assert code == 0
        code, report = run(".gitignore:2 und .gitignore:3\n", strict=False)
        assert code == 1 and [f.kind for f in report.findings] == ["past_end"] and report.citations == 2, report
        # URLs and clock times are not citations; fenced code is skipped
        code, report = run("see https://example.com/a.py:3 at 09:28 and\n```\nmas_lab/a.py:99\n```\n", strict=True)
        assert code == 0 and report.citations == 0, report
        # no identifier -> counted, not verified
        code, report = run("(`mas_lab/a.py:4`) 설명만 있습니다.\n", strict=True)
        assert code == 0 and report.no_identifier == 1
        # table form: Name:N next to a file in the same row
        table = "| 주제 | 파일 | 심볼 |\n|---|---|---|\n| x | `mas_lab/a.py`, `mas_lab/b.py` | `good_func:4`, `Thing:8`, `Y:2` |\n"
        code, report = run(table, strict=True)
        assert code == 0 and report.table_symbols == 3 and report.strict_pass == 3, report
        stale = table.replace("good_func:4", "good_func:40").replace("Thing:8", "Thing:2")
        code, report = run(stale, strict=True)
        assert code == 1 and sorted(f.kind for f in report.findings) == ["mismatch", "past_end"], report.findings
        # allow file: prefix+reason and prefix+citation+reason; unused entries are reported
        text = good + wrong_id
        code, report = run(text, strict=True, allow_text="`other_func`는\t이 줄은 일부러 다른 파일의 이름을 쓴다\n")
        assert code == 0 and report.findings[0].allowed, report.findings
        code, report = run(text, strict=True, allow_text="`other_func`는\tmas_lab/a.py:5\t다른 인용\n")
        assert code == 1 and report.unused_allow, report
        code, report = run(past_end, strict=False, allow_text="범위 밖입니다\t일부러\n")
        assert code == 0 and report.findings[0].allowed == "일부러"
        # leading identifier of `name=value` tokens
        (day03 / "mas_lab" / "c.py").write_text("def make():\n    return dict(\n        max_retries=0,\n    )\n", encoding="utf-8")
        code, report = run("`max_retries=0`는 세 번째 줄입니다 (`mas_lab/c.py:3`).\n", strict=True)
        assert code == 0 and report.strict_pass == 1, report
        code, report = run("`other_retries=0`는 세 번째 줄입니다 (`mas_lab/c.py:3`).\n", strict=True)
        assert code == 1 and report.findings[0].kind == "mismatch", report
        # bare basename found under data/business
        (day03 / "data" / "business").mkdir(parents=True)
        (day03 / "data" / "business" / "sla.md").write_text("a\nb\nc\n", encoding="utf-8")
        code, report = run("원문은 `sla.md:2`입니다.\n", strict=True)
        assert code == 0 and report.citations == 1 and report.no_identifier == 1, report
        # the answer key is never opened: an unreadable gold.jsonl must not raise or be counted past-end
        gold = day03 / "data" / "gold.jsonl"
        gold.write_text("SENTINEL\n", encoding="utf-8")
        gold.chmod(0)
        try:
            code, report = run("`x`(`data/gold.jsonl:3`) und `data/gold.jsonl:999`\n", strict=True)
        finally:
            gold.chmod(0o600)
        assert code == 0 and report.protected == 2 and not report.findings, report
        # positive control for the real-document shape: a cited line past the end of a short file is a hard failure
        code, report = run("`gate_answer`(`mas_lab/b.py:154`), `x`(`mas_lab/b.py:161`)\n", strict=False)
        assert code == 1 and [f.kind for f in report.findings] == ["past_end", "past_end"]
    print("self-test ok")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("doc", nargs="?")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--allow")
    parser.add_argument("--root", help="the Day03_new directory (default: the Day03_new that holds this script)")
    parser.add_argument("--quiet", action="store_true", help="do not print ALLOWED findings")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.doc:
        parser.error("a document is required")
    root = Path(args.root) if args.root else DAY03_NEW
    doc = Path(args.doc).resolve()
    report = check(doc, strict=args.strict, allow=Path(args.allow) if args.allow else None, day03=root.resolve())
    return render(report, doc, strict=args.strict, quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
