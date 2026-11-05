"""키 상태와 연결을 확인한다. 키 값은 출력하지 않는다(설정됨/미설정만).

사용법 (실습 폴더에서):
    ./lab tools/keys.py            키 상태, 공급자와 모델, Langfuse 인증과 프로젝트 주소. 유료 호출 없음
    ./lab tools/keys.py --smoke    위에 더해: scripted Episode 1개를 Langfuse(cc_m0)에 남기고, 에이전트 모델을 1회 부른다(유료 1회)
"""

from __future__ import annotations

import argparse
import sys

from eval_lab.settings import key_status, load_settings, make_agent_model, provider_of


def main() -> int:
    parser = argparse.ArgumentParser(description="키 상태와 연결 확인(값은 출력하지 않는다)")
    parser.add_argument("--smoke", action="store_true", help="scripted Episode 1개 기록 + 에이전트 모델 1회 호출(유료 1회)")
    arguments = parser.parse_args()

    # 1단계: 키는 설정됨/미설정만. 공급자와 모델 이름은 비밀이 아니라 그대로 보인다.
    settings = load_settings()
    provider = provider_of(settings)
    print("키 상태(값은 출력하지 않습니다):")
    for name, state in key_status(settings).items():
        print(f"  {name:22s} {state}")
    print(f"모델 공급자: {provider.name} ({provider.api_url}) / 에이전트 모델: {settings.model}, effort {settings.effort}")
    print(f"Judge: {settings.judge_model}, effort {settings.judge_effort} / 개선기 effort {settings.improver_effort}")

    # 2단계: Langfuse 인증과 프로젝트 주소. 키가 없으면 로컬 경로로 진행한다는 안내만 낸다.
    from eval_lab.notebook import langfuse_or_none

    langfuse = langfuse_or_none(settings)
    if langfuse is None:
        print("Langfuse: 키가 없습니다. 이 실습은 Langfuse가 주 화면이므로 .env의 LANGFUSE_* 를 직접 채우세요.")
        return 1
    # 인증 실패는 False가 아니라 예외(UnauthorizedError)로 오기도 한다. 어느 쪽이든 같은 안내를 낸다(키 값은 출력하지 않는다).
    try:
        authenticated = langfuse.auth_check()
    except Exception as error:  # noqa: BLE001 - 원인 이름만 보여 주고 같은 안내로 받는다
        print(f"Langfuse: 인증 실패({type(error).__name__}).", end=" ")
        authenticated = False
    if not authenticated:
        print("키가 틀렸거나, 주소(LANGFUSE_HOST 또는 LANGFUSE_BASE_URL)가 키를 만든 프로젝트의 지역과 다릅니다. "
              f"지금 주소: {settings.langfuse_host or '(비어 있음: 기본 https://cloud.langfuse.com)'}")
        return 1
    project = langfuse.api.projects.get().data[0]
    host = (settings.langfuse_host or "https://cloud.langfuse.com").rstrip("/")
    print(f"Langfuse: 인증됨 / 프로젝트 {project.name} / {host}/project/{project.id}/traces")

    if not arguments.smoke:
        return 0

    # 3단계(--smoke): scripted Episode 1개를 Langfuse에 남긴다. 모델 호출은 없다.
    from eval_lab.agent import PROMPTS
    from eval_lab.dataset import load_dataset, load_fixtures
    from eval_lab.episodes import execute_episode
    from eval_lab.notebook import announce

    card = next(c for c in load_dataset(split="dev") if c.metadata.scenario_id == "normal")
    artifact = execute_episode(card.input, load_fixtures()[card.fixture_id], followups=card.followups,
                               max_turns=card.max_turns, scenario_id="smoke-normal", release="baseline", trial=1,
                               mode="scripted", prompt=PROMPTS["baseline"], langfuse=langfuse,
                               environment_tag="cc_m0", tags=["smoke"], version="smoke")
    langfuse.flush()
    print("scripted Episode:", artifact.response.kind, "/ Langfuse:",
          langfuse.get_trace_url(trace_id=artifact.turns[0].trace_id))

    # 4단계(--smoke): 에이전트 모델 1회. 짧은 질문 하나로 키와 주소가 맞는지만 본다.
    announce("m0 연결 확인", model_calls=1)
    reply = make_agent_model(settings).invoke("주문 취소 요청을 받으면 가장 먼저 무엇을 확인해야 하는지 한 문장으로 답하세요.")
    text = reply.content if isinstance(reply.content, str) else " ".join(
        block.get("text", "") for block in reply.content if isinstance(block, dict))
    print("에이전트 모델 응답(1회 관찰):", text.strip()[:200])
    print("토큰:", reply.usage_metadata)
    return 0


if __name__ == "__main__":
    sys.exit(main())
