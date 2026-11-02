"""Claude, Jev, Langfuse 실연결과 MCP stdio 트레이스 전파를 한 번 확인하는 스크립트. pytest가 수집하지 않는다.

실행: 저장소 루트에서 .venv/bin/python Day04_new/tests/live_smoke.py
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def check_claude(env: dict) -> str:
    from langchain_anthropic import ChatAnthropic

    model = ChatAnthropic(model=env["DAY04_MODEL"], api_key=env["ANTHROPIC_API_KEY"],
                          reasoning_effort=env["DAY04_EFFORT"], timeout=120.0, max_retries=0)
    reply = model.invoke("한 단어로만 답하세요: 하늘 색은?")
    text = reply.text if isinstance(reply.text, str) else str(reply.text)
    return "ok" if text.strip() else "fail: empty"


def check_jev(env: dict) -> str:
    body = {"model": "jev-latest", "state": "CSV 합계와 보고서 합계가 일치한다.",
            "questions": {"judgeable": {"type": "noul",
                                        "instructions": "이 인수 기준을 실행 결과만으로 참/거짓 판정할 수 있는가?",
                                        "criteria": {"true": "실행 결과로 참/거짓을 판정할 수 있다.",
                                                     "false": "실행 결과만으로는 판정할 수 없다."}}}}
    response = httpx.post("https://api.typesafe.ai/v1/systemone", json=body, timeout=15.0,
                          headers={"Authorization": "Bearer " + env["TYPESAFE_API_KEY"]})
    if response.status_code >= 400:
        return f"fail: HTTP {response.status_code}"
    answer = (response.json().get("answers") or {}).get("judgeable") or {}
    probability = float(answer["noul"])
    return "ok" if 0.0 <= probability <= 1.0 else "fail: out of range"


def check_langfuse(env: dict):
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_TRACING_ENVIRONMENT"):
        os.environ[key] = env[key]
    from langfuse import get_client

    client = get_client()
    try:
        authed = client.auth_check() is True
    except Exception as error:
        return client, f"fail: {type(error).__name__}"  # 스팬 생성은 인증과 무관하므로 클라이언트는 돌려준다.
    if not authed:
        return client, "fail: auth_check"
    with client.start_as_current_observation(name="day04_new-smoke", as_type="span"):
        pass
    client.flush()
    return client, "ok"


async def probe_traceparent(client) -> tuple[str, str, str]:
    from fastmcp.client.transports import PythonStdioTransport
    from langchain.mcp import MCPAdapter

    with client.start_as_current_observation(name="day04_new-smoke-mcp", as_type="span") as span:
        async with MCPAdapter(PythonStdioTransport(str(HERE / "smoke_server.py"))) as adapter:
            tools = {t.name: t for t in await adapter.list_tools()}
            result = await tools["echo_trace"].ainvoke({})
        trace_id = span.trace_id
        protocol = "unknown"
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    for part in (result if isinstance(result, list) else [result]):
        if isinstance(part, dict) and part.get("text"):
            text = part["text"]
    parts = text.strip().split("-")
    received = len(parts) == 4 and len(parts[1]) == 32
    matches = received and parts[1] == trace_id
    return str(received).lower(), str(matches).lower(), protocol


def main() -> None:
    print("이 실행은 Claude 1회, Jev 1회 호출과 Langfuse trace 1~2건입니다.")
    env = dotenv_values(ROOT / ".env")
    out = {}
    for name, fn in (("claude", check_claude), ("jev", check_jev)):
        try:
            out[name] = fn(env)
        except Exception as error:
            out[name] = f"fail: {type(error).__name__}"
    client, out["langfuse_auth"] = check_langfuse(env)
    out["traceparent_received"] = out["traceparent_matches_langfuse"] = "unknown: not run"
    out["mcp_protocol_version"] = "unknown"
    if client is not None:
        try:
            out["traceparent_received"], out["traceparent_matches_langfuse"], out["mcp_protocol_version"] = asyncio.run(probe_traceparent(client))
            client.flush()
        except Exception as error:
            reason = f"unknown: {type(error).__name__}"
            out["traceparent_received"] = out["traceparent_matches_langfuse"] = reason
    out["model"] = env["DAY04_MODEL"]
    out["ran_at"] = datetime.now(timezone.utc).isoformat()
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "smoke.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
