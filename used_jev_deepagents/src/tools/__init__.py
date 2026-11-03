"""에이전트 도구."""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "build_tools":
        from src.tools.documentation import build_tools

        return build_tools
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["build_tools"]
