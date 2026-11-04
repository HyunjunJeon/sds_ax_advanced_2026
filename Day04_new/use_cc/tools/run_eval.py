"""내 plugin을 `claude plugin eval`로 실제로 돌려 본다. **유료 실행**이다.

`claude plugin eval`(Claude Code 2.1.318)을 이 과정에 맞는 기본값으로 감싼다. 직접 쳐도 되지만 빠뜨리기 쉬운 것이 있다.

- `--no-publish`: 빼면 HTML 보고서(프롬프트, 판정 결과)가 claude.ai에 게시된다. 이 도구는 언제나 붙인다.
- `--mocks off`: 빼면 MCP 서버가 가짜 응답(mock)으로 바뀌어 내 서버가 뜨지 않는다. 내 서버를 시험하려는 것이므로 끈다.
- `--allow-tools`: 내 서버의 도구(mcp__plugin_<plugin>_<server>__*)와 Skill을 허용한다. 이름은 plugin.json과 .mcp.json에서 만든다.
- `--max-cost-usd`: 비용 상한. 실행 직전에 몇 번 돌지 알린다.
- `--trust-plugin`: 처음 돌릴 때 묻는 신뢰 확인을 건너뛴다. **내가 만든 plugin에만** 쓴다.
- 결과는 challenge/runs/<plugin>-<시각>/ 에 남는다(git에 올라가지 않는다). 실패한 결과도 지우지 않는다.

사용법 (Day04_new/use_cc 폴더에서):

    uv run python tools/run_eval.py challenge/work/<내 plugin> --runs 1
    uv run python tools/run_eval.py challenge/work/<내 plugin> --case permission-denied --keep-temp

--keep-temp를 주면 실행 기록(trace.jsonl)을 남긴다. `uv run python tools/show_session.py <trace 경로>`로 표를 본다.
남긴 임시 폴더에는 권한이 잠긴 하위 폴더(sealed)가 있다. 다 본 뒤에는 출력에 나온 명령으로 지운다.
기본으로 plugin이 없는 기준선(baseline)도 함께 돌려 차이(Δ)를 보여 준다. 기준선을 빼려면 --ablation none.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

USE_CC_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = USE_CC_DIR / "challenge" / "runs"
DEFAULT_MODEL = "claude-sonnet-5-5"  # Day04_new의 기본 모델과 같다(cap_lab/settings.py:13)
DEFAULT_MAX_COST = 2.0
# 사례 하나를 한 번 돌릴 때의 Claude 호출 수. 저자 실측(예시 plugin)은 2~5회였다.
CALLS_PER_RUN = (2, 6)


def plugin_names(plugin: Path) -> tuple[str, str]:
    """(plugin 이름, MCP 서버 이름)."""
    manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    servers = json.loads((plugin / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    return manifest["name"], next(iter(servers))


def tool_pattern(plugin_name: str, server_name: str) -> str:
    """내 서버의 도구 전체를 허용하는 패턴. 영숫자, _, - 밖의 글자는 _로 바뀐다(https://code.claude.com/docs/en/mcp.md)."""

    def clean(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]", "_", text)

    return f"mcp__plugin_{clean(plugin_name)}_{clean(server_name)}__*"


def selected_cases(plugin: Path, case_glob: str | None) -> list[str]:
    names = sorted(path.parent.name for path in (plugin / "evals").glob("*/prompt.md"))
    return [name for name in names if case_glob is None or fnmatch(name, case_glob)]


def build_command(plugin: Path, arguments: argparse.Namespace, output_dir: Path) -> list[str]:
    plugin_name, server_name = plugin_names(plugin)
    command = [
        shutil.which("claude") or "claude", "plugin", "eval", str(plugin),
        "--mocks", "off",
        "--allow-tools", tool_pattern(plugin_name, server_name), "Skill",
        "--runs", str(arguments.runs),
        "--model", arguments.model,
        "--ablation", arguments.ablation,
        "--max-cost-usd", str(arguments.max_cost_usd),
        "--no-publish",
        "--trust-plugin",
        "--json", str(output_dir / "result.json"),
        "--output-dir", str(output_dir),
        "--report", str(output_dir / "report.html"),
    ]
    if arguments.case:
        command += ["--case", arguments.case]
    if arguments.keep_temp:
        command.append("--keep-temp")
    return command


def notice(case_count: int, arguments: argparse.Namespace) -> str:
    arms = 2 if arguments.ablation == "with-without" else 1
    runs = case_count * arguments.runs * arms
    low, high = CALLS_PER_RUN
    return (f"[고지] 사례 {case_count}개 × {arguments.runs}회 × {arms}조건(plugin 있음{'/없음' if arms == 2 else ''}) = "
            f"Claude 실행 {runs}회, 호출 약 {runs * low}~{runs * high}회. 비용 상한 ${arguments.max_cost_usd}. "
            "내 Claude Code 계정으로 실행됩니다. 진행합니다.")


def summarize(result: dict) -> str:
    """사례마다 plugin 있음/없음의 점수와 판정기 결과를 표로 보여 준다."""
    lines = ["| 사례 | 조건 | 점수 | 판정기 |", "|---|---|---|---|"]
    for case in result.get("cases", []):
        for arm, runs in (case.get("arms") or {}).items():
            label = {"with": "plugin 있음", "without": "plugin 없음"}.get(arm, arm)
            for run in runs:
                graders = ", ".join(
                    f"{grader.get('name')}={'통과' if grader.get('passed') else '실패'}"
                    + ("(지표)" if grader.get("scored") is False else "")
                    for grader in run.get("graders", [])
                )
                error = f" 오류: {run['error']}" if run.get("error") else ""
                lines.append(f"| {case.get('name')} | {label} | {run.get('score')} | {graders}{error} |")
    aggregates = result.get("aggregates", {})
    lines.append("")
    lines.append(f"통과한 사례 {aggregates.get('casesPassed')}/{aggregates.get('casesTotal')}, "
                 f"평균 차이(Δ, plugin 있음 - 없음) {aggregates.get('meanDelta')}, 비용 ${result.get('costUsd')}")
    lines.append("판정기 뒤의 (지표)는 점수에 들어가지 않는 표시다. 예: 기준선과 비교할 때 `tool_used: Skill`")
    return "\n".join(lines)


def trace_paths(result: dict) -> list[str]:
    return [f"{case.get('name')} [{arm}]: {run.get('tracePath')}"
            for case in result.get("cases", []) for arm, runs in (case.get("arms") or {}).items() for run in runs]


def main() -> None:
    parser = argparse.ArgumentParser(description="내 plugin을 claude plugin eval로 실제로 돌린다 (유료)")
    parser.add_argument("plugin", type=Path, help="plugin 폴더")
    parser.add_argument("--runs", type=int, default=1, help="사례마다 돌릴 횟수 (기본 1. 흔들림을 보려면 늘린다)")
    parser.add_argument("--case", help="이 이름 패턴에 맞는 사례만 돌린다 (예: permission-*)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"모델 (기본 {DEFAULT_MODEL})")
    parser.add_argument("--ablation", choices=("with-without", "none"), default="with-without",
                        help="with-without(기본): plugin 없는 기준선도 돌려 차이를 본다. none: plugin 있는 쪽만")
    parser.add_argument("--max-cost-usd", type=float, default=DEFAULT_MAX_COST, help=f"비용 상한 (기본 {DEFAULT_MAX_COST})")
    parser.add_argument("--keep-temp", action="store_true", help="실행 기록(trace.jsonl)을 남긴다")
    arguments = parser.parse_args()

    plugin = arguments.plugin.expanduser().resolve()
    cases = selected_cases(plugin, arguments.case)
    if not cases:
        raise SystemExit(f"[멈춤] {plugin}/evals 에 돌릴 사례가 없습니다.")
    output_dir = RUNS_DIR / f"{plugin.name}-{datetime.now(UTC).astimezone():%Y%m%d-%H%M%S}"
    output_dir.mkdir(parents=True)

    print(notice(len(cases), arguments))
    command = build_command(plugin, arguments, output_dir)
    completed = subprocess.run(command, cwd=plugin, capture_output=True, text=True, check=False)
    (output_dir / "eval.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "eval.stderr.txt").write_text(completed.stderr, encoding="utf-8")

    result_path = output_dir / "result.json"
    if not result_path.is_file():
        print(completed.stdout[-2000:], completed.stderr[-2000:], sep="\n")
        raise SystemExit(f"[멈춤] 결과 파일이 없습니다(종료 코드 {completed.returncode}). 기록: {output_dir}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    print(summarize(result))
    if arguments.keep_temp:
        print("\n실행 기록 (show_session.py로 읽는다):")
        print("\n".join(trace_paths(result)))
        folders = sorted({str(Path(path).parents[1]) for path in
                          (run.get("tracePath") for case in result.get("cases", [])
                           for runs in (case.get("arms") or {}).values() for run in runs) if path})
        if folders:
            print("\n다 본 뒤 임시 폴더를 지운다:")
            print("  " + " && ".join(f"chmod -R u+rwx {folder} && rm -rf {folder}" for folder in folders))
    print(f"\n결과: {output_dir}")
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
