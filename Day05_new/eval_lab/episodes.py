"""요청·후속 입력·업무 상태의 수명을 관리한다. 이 모듈은 평가 정답을 받지 않는다.

`Day05/business_lab/episodes.py`를 이식했다. 더한 것은 세 가지다.

1. 하네스 게이트(gate)와 바꿔 끼울 수 있는 scripted 드라이버(scripted_driver).
2. Episode 하나 = Langfuse root observation 하나(DESIGN 5절 기록 요구 사항).
   langfuse를 넘기면 scripted든 실제 모델이든 Episode 전체가 `episode` observation 안에서 돌고,
   그 안에서 propagate_attributes로 session_id(=episode_id), version(=정책·Prompt 버전, 기본 release),
   environment, tags, metadata(scenario_id, trial, mode)를 건다.
   턴(turn-N)과 service.* observation은 그 아래에 달린다.
   Episode가 끝나면 root observation의 output에 JSON 요약(episode_summary)을 넣는다.
   Langfuse v4부터 trace 입출력은 root observation에서 오므로, trace 입출력 설정 API는 쓰지 않는다.
   온라인 평가기는 root observation output만으로 Artifact를 다시 만들 수 있다(artifact_from_summary).
3. Artifact.awaiting_user: 고객의 답을 기다리며 멈춘 Episode인지 적는다. 궤적 판정은 이 값과
   실행 상태로 "끝나지 않은 Episode(PROVISIONAL)"를 가린다. 추가 질문이 마지막 답인 것만으로는 가리지 않는다.
"""

from collections.abc import Callable
from contextlib import nullcontext
from functools import partial
from time import perf_counter
from uuid import uuid4

from langfuse import propagate_attributes

from eval_lab.agent import Gate, make_live_session, run_scripted
from eval_lab.contracts import Artifact, Followup, Request, Response, TurnRecord
from eval_lab.environment import OBSERVATION_GATE, OrderEnvironment

# scripted 드라이버의 모양: driver(request, env, release) -> (Response, usage dict)
ScriptedDriver = Callable[[Request, OrderEnvironment, str], tuple[Response, dict]]

# root observation output 요약의 형식 이름. 형식을 바꾸면 이 값도 바꾼다.
# 기본값이 있는 키를 더하는 것(awaiting_user)은 바꾼 것으로 보지 않는다. 옛 요약도 그대로 읽혀야 하고,
# 값을 바꾸면 online이 이미 적재된 v1 요약을 모두 거부하기 때문이다.
SUMMARY_SCHEMA = "day05-episode-summary-v1"


def execute_episode(request: Request, fixture: dict, *, followups: list[Followup], max_turns: int,
                    scenario_id: str, release: str, trial: int, mode: str, prompt: str,
                    model=None, langfuse=None, gate: Gate | None = None,
                    scripted_driver: ScriptedDriver | None = None,
                    environment_tag: str | None = None, tags: list[str] | None = None,
                    version: str | None = None) -> Artifact:
    """같은 Episode에서 환경·대화·예산을 유지한다. 오류가 나도 부분 상태·각 턴을 보존한다.

    계약:
    - mode="live"는 실제 모델 호출이다(model 필수). mode="scripted"는 정답을 읽지 않는 서비스 계약 검증이다.
    - 후속 입력은 직전 응답이 사전 조건에 맞을 때만 공급한다. 무조건 다음 정답 입력을 주지 않는다.
    - gate가 있으면 모든 도구 호출이 게이트를 먼저 거친다. 결정 기록은 Artifact.gate_events에 복사된다.
    - scripted_driver가 없으면 agent.run_scripted(gate 포함)를 쓴다. 직접 만든 드라이버에는
      게이트를 넘길 자리가 없으므로, gate와 scripted_driver를 함께 주면 ValueError를 낸다.
      직접 만든 드라이버는 agent.call_tool(env, tool, args, gate=...)로 게이트를 스스로 거친다.
    - langfuse가 있으면 Episode 전체가 root observation 하나 안에서 실행되고 output에 요약이 남는다.
      environment_tag는 Langfuse 환경 형식(소문자·숫자·-·_, 40자 이하)이어야 하며, 아니면 SDK가 버린다.
    - version은 Langfuse version으로 다는 정책·Prompt 버전 이름이다(DESIGN 5절 기록 요구 사항).
      주지 않으면 release를 쓴다. Artifact.release와 실행 Prompt는 바꾸지 않고 기록의 라벨만 바꾼다.
    - Artifact.awaiting_user는 최대 턴에서 멈췄는데 마지막 응답에 맞는 후속 입력이 남았을 때만 True다.
      후속 입력 수 + 1 <= 최대 턴을 먼저 확인하므로 이 실행기에서는 False다. 추가 질문이 마지막 답이어도 같다.
    - 실행 오류는 Artifact.execution_status(execution_error / infra_error)로 돌려준다. 예외로 던지지 않는다.
    """
    # 0단계: 함께 쓸 수 없는 인자 조합을 먼저 막는다. 게이트가 조용히 무시되는 일을 막기 위해서다.
    if scripted_driver is not None and gate is not None:
        raise ValueError("직접 만든 scripted_driver에는 게이트를 넘길 수 없습니다. "
                         "드라이버 안에서 agent.call_tool(..., gate=gate)를 쓰고 gate 인자는 비워 두세요.")

    episode_id = uuid4().hex
    run_turns = partial(_run_turns, request, fixture, followups=followups, max_turns=max_turns,
                        scenario_id=scenario_id, release=release, trial=trial, mode=mode, prompt=prompt,
                        model=model, langfuse=langfuse, gate=gate, scripted_driver=scripted_driver,
                        episode_id=episode_id)

    # 1단계: Langfuse가 없으면 기록 없이 실행만 한다.
    if langfuse is None:
        return run_turns()

    # 2단계: Episode 전체를 root observation 하나로 감싼다. 입력은 첫 요청이다.
    # Langfuse는 시작 시각을 밀리초로 정렬하므로 앞 observation과 같은 밀리초에 열지 않는다(OBSERVATION_GATE).
    OBSERVATION_GATE.wait()
    root_scope = langfuse.start_as_current_observation(name="episode", as_type="agent",
                                                       input=request.model_dump(mode="json"))
    with root_scope as root:
        OBSERVATION_GATE.mark()
        # 3단계: root 안에서 Episode 단위 속성을 건다. root와 그 아래 모든 observation에 붙는다.
        attribute_scope = propagate_attributes(
            session_id=episode_id,
            version=version or release,
            environment=environment_tag,
            tags=tags,
            metadata={"scenario_id": scenario_id, "trial": str(trial), "mode": mode},
        )
        with attribute_scope:
            artifact = run_turns()
        # 4단계: Episode가 끝난 뒤 root output에 요약을 넣는다. 온라인 평가기는 이 값만 읽는다.
        root.update(output=episode_summary(artifact))
    return artifact


def _run_turns(request: Request, fixture: dict, *, followups: list[Followup], max_turns: int,
               scenario_id: str, release: str, trial: int, mode: str, prompt: str,
               model, langfuse, gate: Gate | None, scripted_driver: ScriptedDriver | None,
               episode_id: str) -> Artifact:
    """Episode의 턴을 실행하고 Artifact를 만든다. 기록 범위(root observation)는 호출한 쪽이 연다."""
    started = perf_counter()
    env, initial, final, response = None, {}, None, None
    current, turns = request, []
    status, error, awaiting_user = "completed", None, False
    usage = {"model_calls": 0, "input_tokens": None, "output_tokens": None, "cost_usd": None}
    try:
        # 1단계: 예산을 확인하고 격리된 업무 환경을 만든다.
        if max_turns < 1 or len(followups) + 1 > max_turns:
            raise ValueError("InvalidEpisodeBudget")
        env = OrderEnvironment(fixture, langfuse=langfuse)
        initial = env.snapshot()

        # 2단계: 실행기를 고른다. live는 실제 모델, scripted는 모델 없는 드라이버다.
        if mode == "live":
            invoke = make_live_session(env, release, model, usage=usage, prompt=prompt, gate=gate)
        elif mode == "scripted":
            # 모델 호출이 없으므로 토큰과 비용은 확실한 0이다(모르는 값이 아니다).
            usage.update(input_tokens=0, output_tokens=0, cost_usd=0.0)
            driver = scripted_driver or partial(run_scripted, gate=gate)

            def invoke(req):
                return driver(req, env, release)[0]
        else:
            raise ValueError("UnknownMode")

        # 3단계: 턴을 돈다. 후속 입력은 직전 응답 유형이 조건과 맞을 때만 넣는다.
        # break는 후속 입력을 더 넣을 수 없을 때다(남은 입력이 없거나 직전 응답이 조건과 다르다).
        for index in range(max_turns):
            if index:
                if index > len(followups) or response is None:
                    break
                next_input = followups[index - 1]
                if response.kind != next_input.when_response:
                    break
                current = next_input.request
            env.turn_index = index + 1
            before = env.snapshot()
            event_offset = len(env.events)
            response = None
            if langfuse:
                OBSERVATION_GATE.wait()
            scope = (langfuse.start_as_current_observation(name=f"turn-{index + 1}", as_type="agent",
                       input=current.model_dump(), metadata={"episode_id": episode_id, "turn_index": index + 1})
                     if langfuse else nullcontext())
            with scope as span:
                if langfuse:
                    OBSERVATION_GATE.mark()
                try:
                    response = invoke(current)
                finally:
                    turns.append(TurnRecord(turn_index=index + 1, request=current, response=response,
                        event_ids=[e.event_id for e in env.events[event_offset:]], initial_state=before,
                        final_state=env.snapshot(), trace_id=langfuse.get_current_trace_id() if langfuse else None))
                    if span:
                        span.update(output=response.model_dump() if response else {"response_missing": True})

        # 4단계: 최대 턴을 다 썼는데 마지막 응답에 맞는 후속 입력이 아직 남았으면 고객의 답을 기다리는 중이다.
        # N턴 뒤 다음 후속 입력은 followups[N - 1]이다. 1단계의 예산 검사(후속 입력 수 + 1 <= 최대 턴)가
        # 있는 한 이 실행기에서는 그런 입력이 남지 않아 False다. 검사를 바꿔도 값이 맞도록 직접 계산한다.
        used_all_turns = len(turns) == max_turns
        pending = followups[max_turns - 1] if used_all_turns and max_turns <= len(followups) else None
        awaiting_user = pending is not None and response is not None and response.kind == pending.when_response
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 부분 상태와 함께 Artifact로 남긴다.
        status = "execution_error" if env else "infra_error"
        error = type(exc).__name__
    finally:
        if env:
            final = env.snapshot()
            env.close()

    # 5단계: 근거를 Artifact로 묶는다. 게이트 결정 기록도 함께 복사한다.
    return Artifact(artifact_id=uuid4().hex, scenario_id=scenario_id, release=release, trial=trial,
                    request=current, initial_request=request, episode_id=episode_id, turns=turns,
                    execution_status=status, initial_state=initial, final_state=final,
                    events=env.events if env else [], gate_events=list(env.gate_events) if env else [],
                    response=response, error_type=error, awaiting_user=awaiting_user,
                    elapsed_seconds=perf_counter() - started, **usage)


# ---------------------------------------------------------------- root observation 요약

def episode_summary(artifact: Artifact) -> dict:
    """root observation output에 넣을 JSON 요약을 만든다. 모든 값은 JSON으로 바로 직렬화된다.

    계약:
    - artifact_from_summary(episode_summary(a))는 model_events를 뺀 a와 같다.
    - model_events(모델 응답 원문)는 넣지 않는다. 같은 내용이 모델 호출 observation에 이미 있고,
      root output을 작게 유지하기 위해서다.
    - request는 Episode의 첫 요청, last_request는 마지막 턴의 요청이다.
    """
    dumped = artifact.model_dump(mode="json")
    first_request = dumped["initial_request"] or dumped["request"]
    summary = {
        "schema": SUMMARY_SCHEMA,
        "episode_id": dumped["episode_id"],
        "artifact_id": dumped["artifact_id"],
        "scenario_id": dumped["scenario_id"],
        "release": dumped["release"],
        "trial": dumped["trial"],
        "status": dumped["execution_status"],
        "error_type": dumped["error_type"],
        "awaiting_user": dumped["awaiting_user"],
        "request": first_request,
        "last_request": dumped["request"],
        "turns": dumped["turns"],
        "events": dumped["events"],
        "gate_events": dumped["gate_events"],
        "initial_state": dumped["initial_state"],
        "final_state": dumped["final_state"],
        "response": dumped["response"],
        "usage": {
            "model_calls": dumped["model_calls"],
            "input_tokens": dumped["input_tokens"],
            "output_tokens": dumped["output_tokens"],
            "cost_usd": dumped["cost_usd"],
        },
        "elapsed_seconds": dumped["elapsed_seconds"],
    }
    return summary


def artifact_from_summary(summary: dict) -> Artifact:
    """root observation output(episode_summary의 결과)에서 Artifact를 다시 만든다.

    모르는 형식이면 ValueError를 낸다. model_events는 요약에 없으므로 빈 목록이 된다.
    awaiting_user가 없는 요약(이 키가 생기기 전에 적재한 것)은 끝난 Episode(False)로 읽는다.
    """
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise ValueError(f"알 수 없는 Episode 요약 형식입니다: {summary.get('schema')!r}")
    usage = summary["usage"]
    # 서버를 거친 JSON은 0.0이 0으로 바뀌는 식으로 숫자 타입이 달라질 수 있어 느슨한 검증(strict=False)을 쓴다.
    return Artifact.model_validate({
        "artifact_id": summary["artifact_id"],
        "scenario_id": summary["scenario_id"],
        "release": summary["release"],
        "trial": summary["trial"],
        "request": summary["last_request"],
        "initial_request": summary["request"],
        "execution_status": summary["status"],
        "error_type": summary["error_type"],
        "awaiting_user": summary.get("awaiting_user", False),
        "initial_state": summary["initial_state"],
        "final_state": summary["final_state"],
        "events": summary["events"],
        "gate_events": summary["gate_events"],
        "response": summary["response"],
        "turns": summary["turns"],
        "episode_id": summary["episode_id"],
        "elapsed_seconds": summary["elapsed_seconds"],
        "model_calls": usage["model_calls"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cost_usd": usage["cost_usd"],
    }, strict=False)
