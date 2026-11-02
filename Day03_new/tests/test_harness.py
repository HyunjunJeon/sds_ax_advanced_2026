"""Deep Agents 기본 general-purpose 하위 에이전트를 끈 상태를 task 도구의 모습으로 확인한다. 모델은 호출하지 않는다."""
import pytest
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

from mas_lab.harness import framework_default_subagent, task_targets
from mas_lab.runner import make_desk
from mas_lab.structures import build_single, build_supervisor
from rag_lab.corpus import load_cases

DESIGNED = ["billing", "policy", "outage"]


@pytest.fixture(scope="module")
def model():
    return ChatAnthropic(model="claude-sonnet-5-5", api_key="dummy-not-a-key", max_retries=0)


@pytest.fixture
def case():
    return next(c for c in load_cases() if c["id"] == "complex-double-pay")


def test_supervisor_offers_only_designed_workers(model, case):
    assert task_targets(build_supervisor(make_desk(case), model)) == DESIGNED


def test_single_agent_has_no_task_tool(model, case):
    assert task_targets(build_single(make_desk(case), model)) is None


def test_framework_default_brings_general_purpose_back_only_inside_block(model, case):
    with framework_default_subagent(model):
        assert "general-purpose" in task_targets(build_supervisor(make_desk(case), model))
    assert task_targets(build_supervisor(make_desk(case), model)) == DESIGNED
    assert task_targets(build_single(make_desk(case), model)) is None


def test_framework_default_restores_designed_only_when_block_raises(model, case):
    with pytest.raises(RuntimeError):
        with framework_default_subagent(model):
            raise RuntimeError("블록 안 실패")
    assert task_targets(build_supervisor(make_desk(case), model)) == DESIGNED


def test_plain_deep_agent_without_subagents_has_no_task_tool(model):
    assert task_targets(create_deep_agent(model=model)) is None
