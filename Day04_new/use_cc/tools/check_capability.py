"""Capability Challenge 검사기. 수강생의 plugin(Skill 하나 + MCP 서버 하나)이 기준표의 자동 항목을 지키는지 본다.

모델을 부르지 않는다. 서버는 임시 폴더를 상태 폴더로 주고 직접 띄워 MCP로 말을 건다.
`claude plugin validate`가 있으면 그것도 한 번 부른다(모델 호출 없음). 없거나 --skip-validate면 건너뛴다.

사용법 (Day04_new/use_cc 폴더에서):

    uv run python tools/check_capability.py challenge/work/<내 plugin>
    uv run python tools/check_capability.py challenge/examples/example-tasks

검사 항목과 뜻은 `challenge/challenge.md`의 기준표에 있다. 결과가 "실패"인 항목이 하나라도 있으면 종료 코드 1이다.
"주의"는 고치기를 권하지만 실패로 세지 않는다.

이 검사기가 보는 것은 **모양**이다. 도구 설명이 좋은지, Claude가 도구를 제대로 고르는지는 보지 않는다.
그것은 `tools/run_eval.py`(실제 실행)와 강사 리뷰가 본다.
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from mcp import Client
from mcp.client.stdio import StdioServerParameters

PASS, WARN, FAIL, SKIP = "통과", "주의", "실패", "건너뜀"
# Claude Code의 Skill description 한도. 05 노트북 1절이 다룬 deepagents 한도와 같은 값이다.
DESCRIPTION_LIMIT = 1024
TOOL_COUNT_RANGE = (3, 5)
FAULT_ENV = "CAPABILITY_FAULT"
# 예시 서버의 장애 주입 관례가 돌려주는 오류 코드. Skill이 이 둘에 대한 행동을 적어야 한다.
FAULT_ERROR_CODES = ("permission_denied", "temporarily_unavailable")
CAPABILITY_SECTIONS = ("1", "2", "3", "4", "5", "6", "7")
PLACEHOLDER = "(여기에"
# 쓰지 않는 조건을 적었는지 보는 표현. 05 노트북 1절: description은 쓰는 조건과 쓰지 않는 조건을 모두 담아야 한다.
NEGATIVE_MARKERS = ("않", "말 것", "제외")
# eval 사례에 필요한 태그. challenge.md 기준표의 "사례" 줄과 같다.
REQUIRED_EVAL_TAGS = ("trigger", "should-not-trigger", "selection", "fault")
BUILTIN_TOOLS = {"Skill", "ToolSearch", "Read", "Glob", "Grep", "Bash", "Write", "Edit", "WebFetch", "WebSearch", "Task"}
CALL_TIMEOUT_SECONDS = 30
# 요청을 보내기 전에 stdout을 지켜보는 시간. 올바른 MCP 서버는 요청을 받기 전에 stdout에 아무것도 쓰지 않는다.
STDOUT_WATCH_SECONDS = 2.0


@dataclass
class Finding:
    check: str
    status: str
    detail: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, ok: bool, detail: str, *, warn_only: bool = False) -> bool:
        status = PASS if ok else (WARN if warn_only else FAIL)
        self.findings.append(Finding(check, status, detail))
        return ok

    def skip(self, check: str, detail: str) -> None:
        self.findings.append(Finding(check, SKIP, detail))

    @property
    def failed(self) -> bool:
        return any(finding.status == FAIL for finding in self.findings)


# ---------------------------------------------------------------- 작은 도우미


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """--- 로 둘러싼 YAML 머리말과 본문을 나눈다. 머리말이 없으면 빈 사전."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def get_path(value: Any, path: str) -> Any:
    """'task.task_id'처럼 점으로 이은 경로의 값을 꺼낸다. 없으면 KeyError."""
    for part in path.split("."):
        if isinstance(value, list):
            value = value[int(part)]
        else:
            value = value[part]
    return value


def claude_tool_name(plugin_name: str, server_name: str, tool_name: str) -> str:
    """plugin MCP 도구의 Claude Code 이름. 영숫자, _, - 밖의 글자는 _로 바뀐다(https://code.claude.com/docs/en/mcp.md)."""

    def clean(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9_-]", "_", text)

    return f"mcp__plugin_{clean(plugin_name)}_{clean(server_name)}__{tool_name}"


# ---------------------------------------------------------------- plugin 구조


def check_manifest(plugin: Path, report: Report) -> str | None:
    manifest = plugin / ".claude-plugin" / "plugin.json"
    if not report.add("plugin.json", manifest.is_file(), f"{manifest.relative_to(plugin)} 가 있어야 한다"):
        return None
    try:
        name = json.loads(manifest.read_text(encoding="utf-8")).get("name", "")
    except json.JSONDecodeError as error:
        report.add("plugin.json", False, f"JSON이 아니다: {error}")
        return None
    report.add("plugin.json 이름", bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)),
               f"name이 소문자와 -로 된 이름이어야 한다 (지금: {name!r})")
    return name


def check_validate(plugin: Path, report: Report, skip: bool) -> None:
    claude = shutil.which("claude")
    if skip or claude is None:
        report.skip("claude plugin validate", "건너뜀 (--skip-validate 이거나 claude가 없다)")
        return
    completed = subprocess.run([claude, "plugin", "validate", str(plugin)], capture_output=True, text=True,
                               check=False, timeout=120)
    report.add("claude plugin validate", completed.returncode == 0,
               "통과" if completed.returncode == 0 else completed.stdout[-400:] + completed.stderr[-400:])


def check_skill(plugin: Path, report: Report) -> tuple[str, str] | None:
    """Skill이 하나 있고 머리말이 맞는지 본다. (skill 이름, 본문)을 돌려준다."""
    skill_files = sorted((plugin / "skills").glob("*/SKILL.md"))
    if not report.add("Skill 하나", len(skill_files) == 1,
                      f"skills/<이름>/SKILL.md 가 정확히 하나여야 한다 (지금 {len(skill_files)}개)"):
        return None
    skill_file = skill_files[0]
    try:
        frontmatter, body = read_frontmatter(skill_file)
    except yaml.YAMLError as error:
        report.add("Skill 머리말", False, f"YAML을 읽을 수 없다: {error}")
        return None
    folder = skill_file.parent.name
    name = frontmatter.get("name", "")
    description = str(frontmatter.get("description", "")).strip()
    report.add("Skill 머리말", name == folder, f"name({name!r})이 폴더 이름({folder!r})과 같아야 한다")
    report.add("Skill description", 0 < len(description) <= DESCRIPTION_LIMIT,
               f"비어 있지 않고 {DESCRIPTION_LIMIT}자 이하여야 한다 (지금 {len(description)}자)")
    report.add("Skill 쓰지 않는 조건", any(marker in description for marker in NEGATIVE_MARKERS),
               "description에 쓰지 않는 조건(예: '…에는 사용하지 않는다')이 있으면 좋다", warn_only=True)
    return name, body


# ---------------------------------------------------------------- MCP 서버


@dataclass
class ServerConfig:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]


def load_server(plugin: Path, report: Report) -> ServerConfig | None:
    config_path = plugin / ".mcp.json"
    if not report.add(".mcp.json", config_path.is_file(), "plugin 맨 위에 .mcp.json이 있어야 한다"):
        return None
    servers = json.loads(config_path.read_text(encoding="utf-8")).get("mcpServers", {})
    if not report.add(".mcp.json 서버 하나", len(servers) == 1, f"MCP 서버가 정확히 하나여야 한다 (지금 {len(servers)}개)"):
        return None
    name, entry = next(iter(servers.items()))
    if not report.add(".mcp.json stdio", "command" in entry, "stdio 서버(command, args)여야 한다"):
        return None
    return ServerConfig(name, entry["command"], list(entry.get("args", [])), dict(entry.get("env", {})))


def expand(text: str, plugin: Path, project: Path) -> str:
    """Claude Code가 하는 것처럼 ${CLAUDE_PLUGIN_ROOT} 등을 실제 경로로 바꾼다."""
    return (text.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin))
                .replace("${CLAUDE_PROJECT_DIR}", str(project))
                .replace("${CLAUDE_PLUGIN_DATA}", str(project / ".plugin-data")))


class ServerSession:
    """임시 상태 폴더로 서버를 띄워 연결한다. 끝나면 임시 폴더를 지운다."""

    def __init__(self, plugin: Path, config: ServerConfig, extra_env: dict[str, str] | None = None) -> None:
        self.plugin, self.config, self.extra_env = plugin, config, extra_env or {}

    async def __aenter__(self) -> Client:
        self.project = Path(tempfile.mkdtemp(prefix="capability-check-"))
        env = {key: expand(value, self.plugin, self.project) for key, value in self.config.env.items()}
        params = StdioServerParameters(
            command=expand(self.config.command, self.plugin, self.project),
            args=[expand(argument, self.plugin, self.project) for argument in self.config.args],
            env={**env, **self.extra_env, "CLAUDE_PLUGIN_ROOT": str(self.plugin), "CLAUDE_PROJECT_DIR": str(self.project)},
            cwd=str(self.project),
        )
        self.client_context = Client(params)
        return await asyncio.wait_for(self.client_context.__aenter__(), CALL_TIMEOUT_SECONDS)

    async def __aexit__(self, *exc_info) -> None:
        try:
            await self.client_context.__aexit__(*exc_info)
        finally:
            shutil.rmtree(self.project, ignore_errors=True)


def check_quiet_stdout(plugin: Path, config: ServerConfig, report: Report) -> None:
    """서버를 직접 띄워 요청을 보내지 않고 stdout을 지켜본다. 무언가 나오면 stdout 오염이다.

    mcp SDK 클라이언트는 JSON이 아닌 줄을 건너뛰기도 해서 tools/list만으로는 이 결함이 드러나지 않는다(이 검사기의 반증 시험에서 확인).
    도구를 부르는 도중의 print는 이 검사가 보지 못한다. 그런 print는 Claude Code의 /mcp나 도구 결과에서 드러난다.
    """
    project = Path(tempfile.mkdtemp(prefix="capability-stdout-"))
    command = [expand(config.command, plugin, project)] + [expand(argument, plugin, project) for argument in config.args]
    env = {**os.environ, **{key: expand(value, plugin, project) for key, value in config.env.items()},
           "CLAUDE_PLUGIN_ROOT": str(plugin), "CLAUDE_PROJECT_DIR": str(project)}
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   cwd=project, env=env)
        try:
            output, _ = process.communicate(timeout=STDOUT_WATCH_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
    finally:
        shutil.rmtree(project, ignore_errors=True)
    shown = output.decode("utf-8", "replace").strip()[:120]
    report.add("stdout 오염(시작할 때)", not output,
               f"요청을 보내기 전에 stdout에 출력이 있다: {shown!r}. 진단은 stderr에 쓴다(print(..., file=sys.stderr))")


def normalize_result(result) -> dict[str, Any]:
    """tools/call 결과를 {is_error, payload}로. payload는 structuredContent나 본문 JSON."""
    payload = result.structured_content
    if payload is None:
        text = "".join(getattr(item, "text", "") for item in result.content)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"_text": text}
    return {"is_error": bool(result.is_error), "payload": payload}


async def fetch_tools(plugin: Path, config: ServerConfig):
    async with ServerSession(plugin, config) as client:
        return (await asyncio.wait_for(client.list_tools(), CALL_TIMEOUT_SECONDS)).tools


def check_tools(tools, report: Report) -> None:
    low, high = TOOL_COUNT_RANGE
    report.add("도구 수", low <= len(tools) <= high, f"도구가 {low}~{high}개여야 한다 (지금 {len(tools)}개)")
    for tool in tools:
        report.add(f"{tool.name}: 설명", bool((tool.description or "").strip()), "도구 설명이 비어 있으면 안 된다")
        properties = (tool.input_schema or {}).get("properties", {})
        missing_type = [key for key, spec in properties.items() if not ({"type", "enum", "anyOf", "$ref"} & set(spec))]
        missing_description = [key for key, spec in properties.items() if not spec.get("description")]
        report.add(f"{tool.name}: 인자 타입", not missing_type, f"타입이 없는 인자: {missing_type}")
        report.add(f"{tool.name}: 인자 설명", not missing_description,
                   f"설명이 없는 인자: {missing_description} (Annotated[..., Field(description=...)])")
        annotations = tool.annotations
        hints = ("read_only_hint", "destructive_hint", "idempotent_hint", "open_world_hint")
        unset = [hint for hint in hints if annotations is None or getattr(annotations, hint) is None]
        report.add(f"{tool.name}: annotations", not unset, f"적지 않은 힌트: {unset}. 기본값이 destructive·openWorld=true다")
        report.add(f"{tool.name}: 출력 형식", tool.output_schema is not None,
                   "outputSchema가 없다. 반환 타입을 dict[str, Any]처럼 적으면 생긴다", warn_only=True)


# ---------------------------------------------------------------- 계약 사례


def load_contract(plugin: Path, report: Report) -> list[dict[str, Any]]:
    path = plugin / "checks" / "contract.jsonl"
    if not report.add("계약 사례 파일", path.is_file(), "checks/contract.jsonl 이 있어야 한다"):
        return []
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expects = [call.get("expect", {}) for case in cases for call in case.get("calls", [])]
    report.add("계약 사례: 업무 오류", any("error" in expect for expect in expects),
               "업무 오류(success:false, error 코드)를 기대하는 호출이 하나 이상 있어야 한다")
    report.add("계약 사례: 중복 실행", any("same_as" in expect or "len" in expect for expect in expects),
               "같은 호출을 두 번 보내 결과를 비교하는 사례(same_as 또는 len)가 하나 이상 있어야 한다")
    return cases


def resolve_args(arguments: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """{"from_call": 0, "path": "task.task_id"} 를 앞 호출 결과의 값으로 바꾼다."""
    resolved = {}
    for key, value in arguments.items():
        if isinstance(value, dict) and "from_call" in value:
            value = get_path(results[value["from_call"]]["payload"], value["path"])
        resolved[key] = value
    return resolved


def judge(expect: dict[str, Any], result: dict[str, Any], results: list[dict[str, Any]]) -> list[str]:
    """기대와 다른 점을 문장으로 돌려준다. 빈 목록이면 기대대로다."""
    problems = []
    payload = result["payload"]
    if result["is_error"] != expect.get("is_error", False):
        problems.append(f"is_error={result['is_error']} (업무 오류는 예외가 아니라 success:false로 돌려준다)")
        return problems
    business_error = isinstance(payload, dict) and payload.get("success") is False
    if "error" in expect and not (business_error and payload.get("error") == expect["error"]):
        problems.append(f"success:false, error={expect['error']!r} 를 기대했는데 {payload}")
    if "success" in expect and not (isinstance(payload, dict) and payload.get("success") is expect["success"]):
        problems.append(f"success={expect['success']} 를 기대했는데 {payload}")
    for path, value in expect.get("equals", {}).items():
        try:
            actual = get_path(payload, path)
        except (KeyError, IndexError, TypeError, ValueError):
            actual = "(없음)"
        if actual != value:
            problems.append(f"{path}={value!r} 를 기대했는데 {actual!r}")
    for path, length in expect.get("len", {}).items():
        try:
            actual_length = len(get_path(payload, path))
        except (KeyError, IndexError, TypeError, ValueError):
            actual_length = "(없음)"
        if actual_length != length:
            problems.append(f"len({path})={length} 를 기대했는데 {actual_length}")
    if "same_as" in expect:
        rule = expect["same_as"]
        try:
            earlier = get_path(results[rule["call"]]["payload"], rule["path"])
            now = get_path(payload, rule["path"])
        except (KeyError, IndexError, TypeError, ValueError):
            earlier, now = "(없음)", "(없음2)"
        if earlier != now:
            problems.append(f"{rule['path']}가 {rule['call']}번째 호출과 같아야 하는데 {earlier!r} != {now!r}")
    return problems


async def run_contract_case(plugin: Path, config: ServerConfig, case: dict[str, Any]) -> list[str]:
    results: list[dict[str, Any]] = []
    problems: list[str] = []
    async with ServerSession(plugin, config) as client:
        for index, call in enumerate(case.get("calls", [])):
            try:
                arguments = resolve_args(call.get("args", {}), results)
            except (KeyError, IndexError, TypeError, ValueError) as error:
                problems.append(f"{index}번째 호출의 인자를 앞 결과에서 꺼낼 수 없다: {error}")
                break
            raw = await asyncio.wait_for(client.call_tool(call["tool"], arguments), CALL_TIMEOUT_SECONDS)
            result = normalize_result(raw)
            results.append(result)
            problems += [f"{index}번째 호출 {call['tool']}: {problem}" for problem in judge(call.get("expect", {}), result, results)]
    return problems


def check_contract(plugin: Path, config: ServerConfig, cases: list[dict[str, Any]], report: Report) -> None:
    for case in cases:
        try:
            problems = asyncio.run(run_contract_case(plugin, config, case))
        except Exception as error:  # noqa: BLE001 - 서버가 죽거나 시간 안에 답하지 않은 것도 결과로 보고한다
            problems = [f"서버와 주고받다 멈췄다: {type(error).__name__}: {error}"]
        report.add(f"계약: {case.get('id', '?')}", not problems, "; ".join(problems) or "기대대로")


# ---------------------------------------------------------------- 장애 주입


async def call_with_fault(plugin: Path, config: ServerConfig, fault: dict[str, Any], tool: str,
                          arguments: dict[str, Any], times: int) -> list[dict[str, Any]]:
    async with ServerSession(plugin, config, {FAULT_ENV: json.dumps(fault)}) as client:
        return [normalize_result(await asyncio.wait_for(client.call_tool(tool, arguments), CALL_TIMEOUT_SECONDS))
                for _ in range(times)]


def check_faults(plugin: Path, config: ServerConfig, tools, cases: list[dict[str, Any]], report: Report) -> None:
    """부작용이 있는 도구 하나로 장애 주입 관례(CAPABILITY_FAULT)가 동작하는지 본다."""
    writable = {tool.name for tool in tools if tool.annotations is not None and tool.annotations.read_only_hint is False}
    sample = next(((call["tool"], call.get("args", {})) for case in cases for call in case.get("calls", [])
                   if call["tool"] in writable
                   and not any(isinstance(value, dict) for value in call.get("args", {}).values())), None)
    if not report.add("장애 주입: 시험할 호출", sample is not None,
                      "계약 사례에 부작용이 있는 도구(readOnlyHint=false)를 고정 인자로 부르는 호출이 있어야 한다"):
        return
    tool, arguments = sample
    try:
        denied = asyncio.run(call_with_fault(plugin, config, {"permission_denied": [tool]}, tool, arguments, 1))[0]
        transient = asyncio.run(call_with_fault(plugin, config, {"transient": {tool: 1}}, tool, arguments, 2))
    except Exception as error:  # noqa: BLE001 - 어떤 실패든 결과로 보고한다
        report.add("장애 주입", False, f"서버와 주고받다 멈췄다: {type(error).__name__}: {error}")
        return
    report.add("장애 주입: 권한 거부", not denied["is_error"] and denied["payload"].get("error") == "permission_denied",
               f"{FAULT_ENV}={{\"permission_denied\": [\"{tool}\"]}}일 때 error=permission_denied 를 기대했는데 {denied}")
    first, second = transient
    report.add("장애 주입: 일시 장애", first["payload"].get("error") == "temporarily_unavailable"
               and second["payload"].get("error") != "temporarily_unavailable",
               f"첫 호출은 temporarily_unavailable, 둘째는 정상을 기대했는데 {first['payload']} / {second['payload']}")


# ---------------------------------------------------------------- Skill과 서버의 연결


def check_skill_mentions(body: str, tools, cases: list[dict[str, Any]], report: Report) -> None:
    unmentioned = [tool.name for tool in tools if tool.name not in body]
    report.add("Skill이 도구를 안내", not unmentioned, f"SKILL.md 본문에 나오지 않는 도구: {unmentioned}")
    codes = {call["expect"]["error"] for case in cases for call in case.get("calls", []) if "error" in call.get("expect", {})}
    codes |= set(FAULT_ERROR_CODES)
    missing = sorted(code for code in codes if code not in body)
    report.add("Skill이 오류 코드를 안내", not missing, f"SKILL.md 본문에 행동이 적히지 않은 오류 코드: {missing}")


# ---------------------------------------------------------------- eval 사례


def check_evals(plugin: Path, plugin_name: str, config: ServerConfig, tools, report: Report) -> None:
    case_dirs = sorted(path.parent for path in (plugin / "evals").glob("*/prompt.md"))
    if not report.add("eval 사례", bool(case_dirs), "evals/<사례>/prompt.md 가 하나 이상 있어야 한다"):
        return
    real_tools = {claude_tool_name(plugin_name, config.name, tool.name) for tool in tools}
    prefix = claude_tool_name(plugin_name, config.name, "")
    tags_seen: set[str] = set()
    for case_dir in case_dirs:
        frontmatter, _ = read_frontmatter(case_dir / "prompt.md")
        tags = set(frontmatter.get("tags") or [])
        graders = [read_frontmatter(path)[0] for path in sorted((case_dir / "graders").glob("*.md"))]
        report.add(f"eval {case_dir.name}: 판정기", bool(graders), "graders/*.md 가 하나 이상 있어야 한다")
        for grader in graders:
            name = str(grader.get("tool", ""))
            if grader.get("type") == "tool_used" and name and name not in BUILTIN_TOOLS:
                known = name in real_tools or (name.endswith("*") and name[:-1].startswith(prefix))
                report.add(f"eval {case_dir.name}: 도구 이름", known,
                           f"{name} 는 이 plugin에 없는 도구다. 이름 형식은 {prefix}<도구>")
        if "trigger" in tags and any(g.get("type") == "tool_used" and g.get("tool") == "Skill" for g in graders):
            tags_seen.add("trigger")
        if "should-not-trigger" in tags:
            tags_seen.add("should-not-trigger")
        if "selection" in tags and any(g.get("type") == "tool_used" and g.get("input_match") for g in graders):
            tags_seen.add("selection")
        if "fault" in tags and "EVAL_" + FAULT_ENV in (frontmatter.get("env") or {}):
            tags_seen.add("fault")
    for tag in REQUIRED_EVAL_TAGS:
        hint = {
            "trigger": "태그 trigger + `tool_used: Skill` 판정기",
            "should-not-trigger": "태그 should-not-trigger (불리면 안 되는 말)",
            "selection": "태그 selection + input_match가 있는 tool_used 판정기",
            "fault": f"태그 fault + env의 EVAL_{FAULT_ENV}",
        }[tag]
        report.add(f"eval 범위: {tag}", tag in tags_seen, f"이런 사례가 하나 이상 있어야 한다: {hint}")


# ---------------------------------------------------------------- CAPABILITY.md


def check_capability_doc(plugin: Path, report: Report) -> None:
    path = plugin / "CAPABILITY.md"
    if not report.add("CAPABILITY.md", path.is_file(), "plugin 맨 위에 CAPABILITY.md가 있어야 한다"):
        return
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    by_number = {section.split(".", 1)[0].strip(): section for section in sections}
    for number in CAPABILITY_SECTIONS:
        section = by_number.get(number, "")
        body_lines = [line for line in section.splitlines()[1:] if line.strip()]
        report.add(f"CAPABILITY.md {number}절", bool(body_lines), f"'## {number}.' 절이 있고 내용이 있어야 한다")
    report.add("CAPABILITY.md 안내 문장", PLACEHOLDER not in text, f"'{PLACEHOLDER} …)' 안내 문장을 지우고 내 말로 써야 한다")


# ---------------------------------------------------------------- 실행


def run_checks(plugin: Path, skip_validate: bool) -> Report:
    report = Report()
    plugin_name = check_manifest(plugin, report)
    check_validate(plugin, report, skip_validate)
    skill = check_skill(plugin, report)
    config = load_server(plugin, report)
    tools = []
    if config is not None:
        check_quiet_stdout(plugin, config, report)
        try:
            tools = asyncio.run(fetch_tools(plugin, config))
            report.add("서버 기동과 tools/list", True, f"도구 {len(tools)}개를 받았다")
        except Exception as error:  # noqa: BLE001 - 어떤 실패든 결과로 보고한다
            report.add("서버 기동과 tools/list", False,
                       f"{type(error).__name__}: {error}. stdout에 print를 했거나 .mcp.json의 경로가 틀렸을 수 있다")
    cases = load_contract(plugin, report)
    if tools:
        check_tools(tools, report)
        check_contract(plugin, config, cases, report)
        check_faults(plugin, config, tools, cases, report)
        if skill is not None:
            check_skill_mentions(skill[1], tools, cases, report)
        if plugin_name:
            check_evals(plugin, plugin_name, config, tools, report)
    check_capability_doc(plugin, report)
    return report


def render(report: Report) -> str:
    width = max(len(finding.check) for finding in report.findings)
    lines = []
    for finding in report.findings:
        detail = "" if finding.status == PASS else f"  {finding.detail}"
        lines.append(f"[{finding.status}] {finding.check.ljust(width)}{detail}")
    counts = {status: sum(f.status == status for f in report.findings) for status in (PASS, WARN, FAIL, SKIP)}
    lines.append("")
    lines.append(" / ".join(f"{status} {count}" for status, count in counts.items()))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capability Challenge plugin 검사기 (모델 호출 없음)")
    parser.add_argument("plugin", type=Path, help="plugin 폴더 (.claude-plugin/plugin.json이 있는 곳)")
    parser.add_argument("--skip-validate", action="store_true", help="claude plugin validate를 부르지 않는다")
    arguments = parser.parse_args()
    plugin = arguments.plugin.expanduser().resolve()
    report = run_checks(plugin, arguments.skip_validate)
    print(f"검사한 plugin: {plugin}")
    print(render(report))
    sys.exit(1 if report.failed else 0)


if __name__ == "__main__":
    main()
