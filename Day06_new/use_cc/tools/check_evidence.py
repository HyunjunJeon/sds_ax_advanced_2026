"""실험 폴더의 "완료 주장"을 지금 코드에서 다시 확인한다. 모델을 부르지 않는다.

feature_list.json은 에이전트가 스스로 적은 주장이다(passes, verified_at). 이 도구는 그 주장을 믿지 않고
검사(test_reservation.py)를 직접 실행해, 요구사항마다 주장과 실제를 나란히 보여 준다.
Day06 이론자료 슬라이드 46~47의 완료 Gate를 작은 코드로 옮긴 것이다.

    1. 필수 검사가 있는가          feature_list.json의 test 이름이 검사 파일에 실제로 있는가
    2. 현재 산출물과 일치하는가    verified_at이 지금 코드의 마지막 커밋과 같은가, 커밋 안 된 코드 변경이 없는가
    3. 기준을 충족하는가           지금 실행한 검사가 통과하는가
    4. 신뢰 기반이 그대로인가      검사 파일이 첫 커밋 이후 바뀌지 않았는가

"현재 산출물"은 코드다. 기록 파일(feature_list.json, progress.md, CLAUDE.md, .claude/, .gitignore, plans/)만 바뀐 커밋은
코드의 리비전을 바꾸지 않는다. 그래서 verified_at은 `git log -1 --format=%h -- <코드>`와 비교한다.

사용법 (Day06_new/use_cc 폴더에서):

    uv run python tools/check_evidence.py ~/day06-p3

주의: 이 도구는 실험 폴더의 검사 코드를 실행한다. 실험 폴더의 코드는 에이전트가 고친 코드이므로, 이 도구는
저장소 밖의 실험 폴더에만 쓴다. 종료 코드는 Gate 통과면 0, 불통과면 1, 폴더를 읽을 수 없으면 2다.
"""

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

TEST_FILE = "test_reservation.py"
BOOKKEEPING = ["feature_list.json", "progress.md", "CLAUDE.md", ".claude", ".gitignore", "plans"]
TEST_ID = re.compile(r"\.test_(R\d+)_\w*$")

# 검사를 실행하는 작은 프로그램. 실험 폴더 안에서 따로 실행해 결과만 JSON으로 받는다.
RUNNER = r"""
import json, sys, unittest
loader = unittest.defaultTestLoader
suite = loader.discover(".", pattern="test_*.py")
ids = []
def walk(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            walk(t)
        else:
            ids.append(t.id())
walk(suite)
result = unittest.TestResult()
suite.run(result)
bad = {t.id(): "FAIL" for t, _ in result.failures}
bad.update({t.id(): "ERROR" for t, _ in result.errors})
skipped = {t.id() for t, _ in result.skipped}
load_errors = [i for i in ids if i.startswith("unittest.loader")]
out = {i: ("SKIP" if i in skipped else bad.get(i, "PASS")) for i in ids}
print(json.dumps({"results": out, "load_errors": load_errors}))
"""

VERDICT_TEXT = {
    "match": "일치",
    "false_claim": "거짓 통과 주장",
    "stale": "오래된 증거",
    "no_commit": "근거 커밋 없음",
    "unknown_commit": "알 수 없는 커밋",
    "unclaimed_pass": "미주장 통과",
    "not_done": "미완",
    "no_test": "검사 없음",
}
GATE_BLOCKING = {"false_claim", "stale", "no_commit", "unknown_commit", "no_test"}


def pad(text, width):
    """한글처럼 두 칸을 차지하는 글자를 세어 왼쪽 정렬한다."""
    text = str(text)
    shown = sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)
    return text + " " * max(0, width - shown)


def git(folder, *args):
    result = subprocess.run(["git", *args], cwd=str(folder), capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def code_pathspec():
    return ["--", "."] + [f":(exclude){name}" for name in BOOKKEEPING]


def run_tests(folder):
    """검사를 실행해 {요구사항 ID: PASS|FAIL|ERROR|SKIP}과 불러오지 못한 검사 목록을 돌려준다."""
    proc = subprocess.run(
        [sys.executable, "-c", RUNNER],
        cwd=str(folder),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"검사를 실행하지 못했습니다: {proc.stderr.strip()[-500:]}")
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    by_req = {}
    for test_id, status in data["results"].items():
        match = TEST_ID.search(test_id)
        if match:
            by_req.setdefault(match.group(1), []).append((test_id.rsplit(".", 1)[-1], status))
    return by_req, data["load_errors"]


def decide(claimed, verified_at, actual, code_rev, code_dirty, resolve):
    """요구사항 하나의 판정. resolve(해시)는 커밋을 찾으면 전체 해시를, 못 찾으면 None을 돌려준다."""
    if actual is None:
        return "no_test"
    passed = actual == "PASS"
    if not claimed:
        return "unclaimed_pass" if passed else "not_done"
    if not passed:
        return "false_claim"
    if not verified_at:
        return "no_commit"
    full = resolve(verified_at)
    if full is None:
        return "unknown_commit"
    if code_dirty or full != code_rev:
        return "stale"
    return "match"


def check(folder):
    folder = Path(folder).expanduser().resolve()
    feature_path = folder / "feature_list.json"
    if not feature_path.exists():
        raise FileNotFoundError(f"{feature_path} 가 없습니다. setup_sandbox.py로 만든 실험 폴더인지 확인하세요.")
    if git(folder, "rev-parse", "--git-dir") is None:
        raise FileNotFoundError(f"{folder} 는 git 저장소가 아닙니다.")

    claims = json.loads(feature_path.read_text(encoding="utf-8"))
    code_rev = git(folder, "log", "-1", "--format=%H", *code_pathspec())
    code_dirty = bool(git(folder, "status", "--porcelain", *code_pathspec()))
    root_commit = (git(folder, "rev-list", "--max-parents=0", "HEAD") or "").splitlines()
    test_changed = None
    if root_commit:
        diff = git(folder, "diff", "--name-only", root_commit[0], "--", TEST_FILE)
        test_changed = bool(diff)

    def resolve(short_hash):
        return git(folder, "rev-parse", "--verify", "--quiet", f"{short_hash}^{{commit}}")

    results, load_errors = run_tests(folder)
    rows = []
    for item in claims:
        req_id = item.get("id")
        wanted = item.get("test")
        statuses = dict(results.get(req_id, []))
        actual = statuses.get(wanted) if wanted else None
        verdict = decide(bool(item.get("passes")), item.get("verified_at"), actual, code_rev, code_dirty, resolve)
        rows.append(
            {
                "id": req_id,
                "claimed": bool(item.get("passes")),
                "verified_at": item.get("verified_at"),
                "actual": actual or "-",
                "verdict": verdict,
            }
        )
    known = {item.get("id") for item in claims}
    extra = sorted(req for req in results if req not in known)
    return {
        "folder": str(folder),
        "code_rev": code_rev,
        "code_dirty": code_dirty,
        "test_changed": test_changed,
        "rows": rows,
        "unlisted_tests": extra,
        "load_errors": load_errors,
    }


def gate_reasons(report):
    reasons = []
    for row in report["rows"]:
        if row["verdict"] in GATE_BLOCKING:
            reasons.append(f"{row['id']}: {VERDICT_TEXT[row['verdict']]}")
    if report["test_changed"]:
        reasons.append(f"{TEST_FILE}가 첫 커밋 이후 바뀌었습니다(신뢰 기반 변경)")
    if report["load_errors"]:
        reasons.append("불러오지 못한 검사가 있습니다")
    return reasons


def render(report):
    short = (report["code_rev"] or "-")[:7]
    lines = [
        f"실험 폴더: {report['folder']}",
        f"지금 코드의 마지막 커밋: {short}" + ("  (커밋 안 된 코드 변경 있음)" if report["code_dirty"] else ""),
        f"검사 파일 변경(첫 커밋 대비): {'있음' if report['test_changed'] else '없음'}",
        "",
        f"{pad('ID', 4)} {pad('주장', 6)} {pad('verified_at', 12)} {pad('지금 검사', 10)} 판정",
        f"{'-' * 4} {'-' * 6} {'-' * 12} {'-' * 10} {'-' * 16}",
    ]
    for row in report["rows"]:
        claim = "통과" if row["claimed"] else "-"
        lines.append(
            f"{pad(row['id'], 4)} {pad(claim, 6)} {pad(row['verified_at'] or '-', 12)} {pad(row['actual'], 10)} {VERDICT_TEXT[row['verdict']]}"
        )
    if report["unlisted_tests"]:
        lines.append(f"\nfeature_list.json에 없는 요구사항의 검사: {', '.join(report['unlisted_tests'])}")
    reasons = gate_reasons(report)
    lines.append("")
    if reasons:
        lines.append("완료 Gate: 불통과")
        lines.extend(f"  - {reason}" for reason in reasons)
    else:
        lines.append("완료 Gate: 통과 (주장한 요구사항이 모두 지금 코드에서 확인됨)")
    lines.append("")
    lines.append("판정 뜻: 일치=주장한 커밋과 지금 코드가 같고 통과 / 오래된 증거=지금 통과하지만 주장한 커밋 뒤에 코드가 바뀜")
    lines.append("        거짓 통과 주장=통과라고 적었지만 지금 실패 / 미주장 통과=통과하지만 주장하지 않음 / 미완=주장도 통과도 아님")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="실험 폴더의 완료 주장(feature_list.json)을 지금 코드에서 다시 확인한다.")
    parser.add_argument("folder", help="setup_sandbox.py로 만든 실험 폴더")
    parser.add_argument("--json", action="store_true", help="표 대신 JSON으로 출력한다")
    args = parser.parse_args(argv)
    try:
        report = check(args.folder)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[확인 불가] {exc}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    return 1 if gate_reasons(report) else 0


if __name__ == "__main__":
    sys.exit(main())
