"""Deep Agents 기본 하위 에이전트(general-purpose) 설정과 `task` 도구 점검.

Deep Agents는 설계한 담당자 말고 `general-purpose` 하위 에이전트를 하나 더 붙인다. 이 에이전트는 부모의
도구를 받지만 부모의 사용자 정의 middleware는 받지 않아, 이 과정의 허용 목록과 공유 예산 밖에서 돈다
(02 3절). 공개 이름은 셋이다.
"""
import re
from contextlib import contextmanager

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from deepagents._models import get_model_identifier, get_model_provider

# `task` 도구 설명에서 담당자 목록이 들어가는 구간의 앞뒤 경계다 (deepagents TASK_TOOL_DESCRIPTION).
# 같은 설명의 사용 안내 bullet도 "- "로 시작하므로 이 구간만 잘라서 읽는다.
_LISTING_START = "Available agent types and the tools they have access to:\n"
_LISTING_END = "\n\nSpecify subagent_type"
_LISTING_LINE = re.compile(r"^- ([^:\n]+): ", re.MULTILINE)


def _set_general_purpose(key: str, *, enabled: bool) -> None:
    """프로필 key에 general-purpose 사용 여부를 등록한다 (다시 등록하면 새 값이 덮어쓴다)."""
    register_harness_profile(key, HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=enabled)))


def use_designed_subagents_only(provider: str = "anthropic") -> None:
    """provider 전체에 general-purpose를 끈다. 이후 만드는 Deep Agent에는 설계한 담당자만 남는다."""
    _set_general_purpose(provider, enabled=False)


@contextmanager
def framework_default_subagent(model):
    """블록 안에서만 model의 프레임워크 기본(general-purpose 포함) 에이전트를 만들 수 있게 한다.

    비교용으로 만들어 보는 데만 쓴다. `provider:identifier` 키는 provider 설정보다 우선하므로, 들어갈 때
    enabled=True를 등록하고 나올 때(예외가 나도) 같은 키에 enabled=False를 되돌려 등록한다.
    """
    provider, identifier = get_model_provider(model), get_model_identifier(model)
    key = f"{provider}:{identifier}" if identifier else provider
    _set_general_purpose(key, enabled=True)
    try:
        yield
    finally:
        _set_general_purpose(key, enabled=False)


def task_targets(app) -> list[str] | None:
    """컴파일된 에이전트의 `task` 도구가 내놓는 하위 에이전트 이름. `task` 도구가 없으면 None.

    읽는 곳: `task` 도구의 description 중 담당자 목록 구간의 `- {이름}: {설명}` 줄이다.
    인자 스키마의 `subagent_type`은 enum 없는 문자열이라 이름을 담고 있지 않다.
    """
    task = app.nodes["tools"].bound.tools_by_name.get("task")
    if task is None:
        return None
    start = task.description.index(_LISTING_START) + len(_LISTING_START)
    listing = task.description[start:task.description.index(_LISTING_END, start)]
    return _LISTING_LINE.findall(listing)
