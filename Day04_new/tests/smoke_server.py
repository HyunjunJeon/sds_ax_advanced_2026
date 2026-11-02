"""트레이스 전파 확인용 최소 MCP stdio 서버. 요청 _meta로 받은 traceparent를 그대로 돌려준다."""
from mcp.server.mcpserver import Context, MCPServer

server = MCPServer("smoke")


@server.tool()
def echo_trace(ctx: Context) -> str:
    """요청 _meta에 담긴 W3C traceparent를 반환한다. 없으면 빈 문자열."""
    meta = ctx.request_context.meta
    if meta is None:
        return ""
    value = meta.get("traceparent") if hasattr(meta, "get") else getattr(meta, "traceparent", None)
    return value or ""


if __name__ == "__main__":
    server.run("stdio")
