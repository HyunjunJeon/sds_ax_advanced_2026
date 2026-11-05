"""저자 측정(PREREG P3) 실행 스크립트. pilot, 자기 개선 2라운드, holdout 재확인을 한 번에 돈다. pytest가 수집하지 않는다.

실행(저장소 루트에서):
    uv run --no-sync python Day05_new/tests/run_measurement.py             # 계획과 호출 규모만 출력(모델·키 없음)
    uv run --no-sync python Day05_new/tests/run_measurement.py --live      # 실제 측정(유료, 저자가 한 번)
    uv run --no-sync python Day05_new/tests/run_measurement.py --offline   # 같은 코드를 tests/fakes.py의 가짜로
선택: --no-langfuse(Langfuse 없이), --scenarios PATH(시나리오 파일), --out PATH(출력 루트, 기본 Day05_new/outputs).

순서(DESIGN 11절, PREREG P3):
0. 사전 점검. 유료 호출 전에 하나라도 걸리면 한국어 이유를 출력하고 종료 코드 3으로 멈춘다.
   PREREG 해시(tests/check_prereg.py를 그대로 실행), holdout 엄격 로드(검수 전 초안이 있으면 멈춤, 6사례),
   키(--live만: eval_lab factory가 비어 있는 키 이름을 대고 멈춘다), Langfuse 인증, 새 출력 폴더.
1. 규모 고지(eval_lab.notebook.announce).
2. pilot: 1라운드의 첫 9 Episode를 π0(빈 정책)로 실제 모델 실행 -> rsi.pilot_decision.
   치명 위반 Episode가 0이면 1·2라운드의 운영 단계를 scripted 트래픽(실수를 섞은 드라이버)으로 바꾼다.
3. 1라운드: 나머지 18 Episode만 새로 돌리고 pilot 9건은 pilot_records로 넘긴다(다시 돌리지 않는다).
   2라운드: 1라운드에서 고른 정책으로 27 Episode. 라운드의 판정은 Code 판정뿐이다(P1).
4. holdout: 6사례 x 3반복 x 정책 2개(π0, 최종 π*) = 36 Episode, 실제 모델. P5는 Code 판정만 쓰고,
   의미 판정(Jev -> Judge)은 넘김 비율(P6)과 기록용으로만 붙인다.
5. run_manifest.json을 새 파일로 남긴다. 중간에 멈춰도 그때까지의 상태로 남긴다.

산출물: <out>/measurement/<UTC 시각>-<6자리 16진수>/ 아래 round-1.json, round-2.json, holdout.json,
run_manifest.json, episodes.jsonl(Episode 요약과 holdout 의미 판정), pools/pool-round-<n>.json.
키 값은 어디에도 출력하거나 쓰지 않는다(설정됨/미설정만).
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import traceback
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

DAY05_NEW = Path(__file__).resolve().parents[1]
if str(DAY05_NEW) not in sys.path:
    sys.path.insert(0, str(DAY05_NEW))
# deepeval은 import할 때 작업 폴더의 .env를 os.environ에 올린다. 키는 eval_lab.settings가 Day05_new/.env에서만 읽으므로 끈다.
os.environ.setdefault("DEEPEVAL_DISABLE_DOTENV", "1")

# 아래 import는 sys.path와 DeepEval 설정을 맞춘 뒤에만 할 수 있다(E402).
from check_prereg import DOCS
from eval_lab.agent import MAX_MODEL_CALLS, PROMPTS
from eval_lab.contracts import Artifact, Expected, Scenario
from eval_lab.dataset import DATA, load_dataset, load_fixtures, pending_ids
from eval_lab.decisions import DecisionBackend, make_decider
from eval_lab.episodes import episode_summary, execute_episode
from eval_lab.evaluators import check_outcome
from eval_lab.judges import (
    JEV_QUESTIONS,
    T_HI,
    T_LO,
    JudgeUsage,
    SemanticVerdict,
    judge_semantics,
)
from eval_lab.notebook import announce
from eval_lab.policy import EMPTY_POLICY, PolicySpec, as_gate, validate_spec
from eval_lab.replay import load_pool
from eval_lab.rsi import (
    HOLDOUT_REPS,
    holdout_check,
    pilot_decision,
    run_round,
    scripted_improver,
)
from eval_lab.settings import (
    Settings,
    key_status,
    load_settings,
    make_agent_model,
    make_improver_model,
    make_judge_model,
    make_langfuse,
    provider_of,
)
from eval_lab.traffic import (
    MistakeDriver,
    TrafficItem,
    make_mistake_driver,
    pilot_items,
    round_items,
    run_traffic,
)
from eval_lab.trajectory_rules import TrajectoryVerdict, evaluate_trajectory
from langchain_core.language_models.chat_models import BaseChatModel
from langfuse import Langfuse

# ---------------------------------------------------------------- 사전 등록 수치와 고정값

# P3: 라운드 2회 x 27 Episode(dev fixture 9종 x 문형 3종).
TRAFFIC_EPISODES = 54
# P3: holdout 6사례 x 3반복 x 정책 2개(π0, 최종 π*).
HOLDOUT_CASES = 6
HOLDOUT_EPISODES = HOLDOUT_CASES * HOLDOUT_REPS * 2

# 호출 상한(고지용). Episode당 에이전트 호출 상한은 agent.MAX_MODEL_CALLS(12)다.
AGENT_CALLS_MAX = (TRAFFIC_EPISODES + HOLDOUT_EPISODES) * MAX_MODEL_CALLS
# judge_semantics는 Episode마다 Jev를 한 번 불러 질문 3개를 함께 묻고, 넘긴 질문마다 Judge를 한 번 부른다.
# 의미 판정은 holdout 36 Episode에만 붙인다(P1: P4·P5의 입력이 아니고, P6 넘김 비율 보고에만 쓴다).
JEV_CALLS_MAX = HOLDOUT_EPISODES
JUDGE_CALLS_MAX = HOLDOUT_EPISODES * len(JEV_QUESTIONS)
# DESIGN 13절의 개선기 상한. propose_candidates는 라운드마다 개선기를 한 번 부르므로 실제는 2회다.
IMPROVER_CALLS_MAX = 6

# 실행 Prompt. 저자 측정은 기본 Prompt 하나로 돈다(DESIGN 11.1: 에이전트 모델과 Prompt는 고정).
RELEASE = "baseline"
# Langfuse version 라벨. r<k>는 "k라운드를 마친 뒤의 정책"이다. 1라운드(pilot 포함)는 r0, 2라운드는 r1 정책으로 돈다.
# holdout은 각 정책 명세의 version을 그대로 라벨로 쓴다(π0 = EMPTY_POLICY.version = 'r0').
ROUND_VERSION_LABELS = {1: "r0", 2: "r1"}
# 저자 측정의 Langfuse environment. 수업 노트북의 trace와 섞이지 않게 따로 모은다(소문자·숫자·_ 40자 이하).
ENVIRONMENT_TAG = "day05_new_p3"

# DESIGN 11.2a 전환(pilot 치명 위반 0) 때 운영 단계에 쓰는 scripted 드라이버의 실수 확률과 seed.
# 11.2a가 "03a·04에서 쓰는 것"이라 했으므로 03a 노트북의 MISTAKE_RATES·SEED와 같은 값으로 고정한다.
FALLBACK_MISTAKE_RATES = {
    "write_before_approval": 0.05,
    "blind_retry": 0.50,
    "claim_without_record": 0.08,
    "write_out_of_scope": 0.04,
    "skip_final_check": 0.10,
}
FALLBACK_SEED = 7

DEFAULT_SCENARIOS = DATA / "scenarios.json"
DEFAULT_OUT = DAY05_NEW / "outputs"
CHECK_PREREG = Path(__file__).resolve().parent / "check_prereg.py"
PREREG_HASH_FILE = DOCS / "prereg.sha256"

EXIT_OK = 0
EXIT_RUN_FAILED = 1
# argparse의 인자 오류(2)와 구분한다.
EXIT_PREFLIGHT = 3


# --live는 실제 측정, --offline은 같은 코드를 가짜로 돌린 것이다. manifest의 mode에 그대로 남는다.
Mode = Literal["live", "offline"]


class PreflightError(RuntimeError):
    """사전 점검 실패. 메시지는 저자에게 보여 줄 한국어 이유다. 유료 호출 전에만 낸다."""


# ---------------------------------------------------------------- 계획 출력(호출 없음)

def print_plan(scenarios: Path) -> None:
    """프로토콜과 호출 상한을 출력한다. 모델·키·네트워크를 쓰지 않는다."""
    rates = ", ".join(f"{name} {rate}" for name, rate in FALLBACK_MISTAKE_RATES.items())
    lines = [
        "P3 저자 측정 계획(DESIGN 11절, PREREG P3). 계획만 출력합니다. 실행은 --live(유료) 또는 --offline(가짜)입니다.",
        (f"0. 사전 점검: PREREG 해시, holdout 엄격 로드({HOLDOUT_CASES}사례, 검수 전 초안이 있으면 멈춤), 키, "
         "Langfuse 인증, 새 출력 폴더 <out>/measurement/<UTC 시각>-<16진수>/"),
        ("1. pilot: 1라운드의 첫 9 Episode를 π0(빈 정책 r0)로 실제 모델 실행. 치명 위반 Episode가 0이면 "
         f"1·2라운드 운영 단계를 scripted 트래픽(실수 확률 {rates}; seed {FALLBACK_SEED})으로 바꿉니다. "
         "holdout은 실제 모델 그대로입니다."),
        ("2. 1라운드: 나머지 18 Episode + pilot 9 = 27, Code 판정으로 재생 풀 -> 개선기 후보 3개 -> "
         "꿈꾸기(V = recall - 2 x false_block)."),
        "3. 2라운드: 1라운드에서 고른 정책으로 27 Episode, 같은 순서.",
        (f"4. holdout: {HOLDOUT_CASES}사례 x {HOLDOUT_REPS}반복 x 정책 2개 = {HOLDOUT_EPISODES} Episode, 실제 모델. "
         "P5는 Code 판정만, 의미 판정(Jev -> Judge)은 넘김 비율과 기록용입니다."),
        f"5. run_manifest.json을 새 파일로 남깁니다. 문턱값 t_lo={T_LO}, t_hi={T_HI}(미조정).",
        (f"호출 상한: 에이전트 <= ({TRAFFIC_EPISODES} + {HOLDOUT_EPISODES}) x {MAX_MODEL_CALLS} = {AGENT_CALLS_MAX:,}회, "
         f"개선기 <= {IMPROVER_CALLS_MAX}회, Jev <= {JEV_CALLS_MAX}회, Judge(xhigh) <= {JUDGE_CALLS_MAX}회."),
    ]
    print("\n".join(lines))
    announce_totals("P3 저자 측정 --live")
    pending = pending_ids(scenarios, split="holdout")
    if pending:
        print(f"--live 전에 할 일: {scenarios.name}의 holdout 초안 {len(pending)}건({', '.join(pending)})을 "
              "저자가 검수해 approved로 바꾸고 reviewer를 채웁니다. 그 전에는 사전 점검이 멈춥니다.")
    else:
        print(f"{scenarios.name}의 holdout 초안: 없음.")


def announce_totals(purpose: str) -> None:
    """P3 호출 상한을 한 줄로 고지한다."""
    announce(purpose, model_calls=AGENT_CALLS_MAX, jev_calls=JEV_CALLS_MAX,
             judge_calls=JUDGE_CALLS_MAX, improver_calls=IMPROVER_CALLS_MAX)


# ---------------------------------------------------------------- 사전 점검

def check_prereg() -> str:
    """tests/check_prereg.py를 그대로 실행해 사전 등록 블록이 기록과 같은지 본다. 같으면 기록된 sha256을 돌려준다."""
    done = subprocess.run([sys.executable, str(CHECK_PREREG)], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise PreflightError(f"사전 등록 확인에 실패했습니다(종료 코드 {done.returncode}): {done.stdout.strip()}")
    return PREREG_HASH_FILE.read_text(encoding="utf-8").strip()


def load_holdout(scenarios: Path) -> list[Scenario]:
    """holdout을 엄격 모드로 읽는다. 검수 전 초안이 있으면 그 수를 대고 멈추고, 사례가 6개가 아니어도 멈춘다."""
    try:
        pending = pending_ids(scenarios, split="holdout")
        if pending:
            raise PreflightError(
                f"holdout에 검수 전 초안이 {len(pending)}건 있습니다({', '.join(pending)}). 저자가 검수해 "
                "approved로 바꾸고 reviewer를 채운 뒤 다시 실행하세요. 승인 전에는 holdout 측정을 시작하지 않습니다(DESIGN 12절 4).")
        cards = load_dataset(scenarios, split="holdout")
    except (OSError, ValueError) as error:
        raise PreflightError(f"holdout을 엄격 모드로 읽지 못했습니다({type(error).__name__}): {error}") from error
    if len(cards) != HOLDOUT_CASES:
        raise PreflightError(f"holdout 사례가 {len(cards)}개입니다. 사전 등록(P3)은 {HOLDOUT_CASES}개입니다.")
    return cards


def load_dev_expected(scenarios: Path, items: Sequence[TrafficItem]) -> dict[str, Expected]:
    """dev 카드의 기대 상태를 가족 ID로 묶는다. 운영 항목의 가족이 하나라도 빠지면 멈춘다.

    traffic.round_items는 기본 data/scenarios.json의 dev 분할로 항목을 만든다. --scenarios가 다른 파일이면
    두 파일의 dev 가족이 어긋날 수 있으므로, 업무 결과를 채점할 기대 상태가 모든 항목에 있는지 여기서 확인한다.
    """
    try:
        cards = load_dataset(scenarios, split="dev")
    except (OSError, ValueError) as error:
        raise PreflightError(f"dev 분할을 읽지 못했습니다({type(error).__name__}): {error}") from error
    expected = {card.metadata.family_id: card.expected_output for card in cards}
    missing = sorted({item.family_id for item in items} - set(expected))
    if missing:
        raise PreflightError(f"운영 항목의 가족 {missing}에 맞는 dev 카드가 {scenarios.name}에 없습니다.")
    return expected


@dataclass(frozen=True)
class Dependencies:
    """측정이 쓰는 모델·클라이언트 묶음. --live는 eval_lab factory가 만든 실제 객체, --offline은 tests/fakes.py의 가짜다."""

    config: Settings
    agent_model: BaseChatModel
    judge_model: BaseChatModel
    improver: BaseChatModel
    decider: DecisionBackend
    langfuse: Langfuse | None


def live_dependencies(config: Settings, *, use_langfuse: bool) -> Dependencies:
    """실제 모델·Jev·Langfuse를 만든다. 만들기만 하고 부르지 않는다.

    키 확인은 factory가 한다: 비어 있는 키가 있으면 이름만 대는 RuntimeError(Day05_new/.env.example 안내)를 낸다.
    Decision API 키는 make_decider의 선택 규칙(DAY05_DECISION_BACKEND, 아니면 TYPESAFE -> OPENROUTER -> OPENAI -> AZURE)을 따른다.
    """
    status = key_status(config)
    print("키 상태(값은 출력하지 않습니다): " + ", ".join(f"{name} {state}" for name, state in status.items()))
    try:
        return Dependencies(
            config=config,
            agent_model=make_agent_model(config),
            judge_model=make_judge_model(config),
            improver=make_improver_model(config),
            decider=make_decider(config),
            langfuse=make_langfuse(config) if use_langfuse else None,
        )
    except RuntimeError as error:
        raise PreflightError(str(error)) from error


def offline_dependencies(*, use_langfuse: bool, agent_model: BaseChatModel | None = None) -> Dependencies:
    """tests/fakes.py의 가짜로 같은 측정 코드를 키·네트워크 없이 돌린다. agent_model을 주면 그 가짜 에이전트를 쓴다.

    config는 .env를 읽지 않은 기본 Settings다. 모델 이름과 effort는 기록용 기본값이고 실제로 부르지 않는다.
    """
    import fakes  # 시험 전용 가짜는 --offline에서만 필요하다. --live 경로는 이 모듈을 불러오지 않는다.

    return Dependencies(
        config=Settings(),
        agent_model=agent_model if agent_model is not None else fakes.NotebookAgentModel(),
        judge_model=fakes.NotebookJudgeModel(),
        improver=scripted_improver("sensible"),
        decider=fakes.FakeDecider(fakes.NOTEBOOK_DECIDER_SCRIPT),
        langfuse=fakes.FakeLangfuse() if use_langfuse else None,
    )


def check_langfuse(langfuse: Langfuse | None) -> None:
    """Langfuse를 쓰면 유료 호출 전에 인증을 확인한다. 실패하면 멈춘다."""
    if langfuse is None:
        print("Langfuse: 쓰지 않습니다(--no-langfuse). 기록은 로컬 파일에만 남습니다.")
        return
    try:
        authorized = langfuse.auth_check()
    except Exception as error:  # SDK가 인증 실패를 일반 Exception으로도 낸다. 유료 호출 전에 이유를 대고 멈춘다.
        raise PreflightError(f"Langfuse 인증 확인에 실패했습니다({type(error).__name__}). 키와 LANGFUSE_HOST를 확인하세요.") from error
    if not authorized:
        raise PreflightError("Langfuse 인증 확인에 실패했습니다. 키와 LANGFUSE_HOST를 확인하세요.")
    print("Langfuse: 인증 확인됨.")


def new_measurement_dir(out_root: Path) -> Path:
    """<out_root>/measurement/<UTC 시각>-<6자리 16진수>/를 새로 만든다. 이미 있는 폴더는 다시 쓰지 않는다."""
    base = out_root / "measurement"
    base.mkdir(parents=True, exist_ok=True)
    while True:
        path = base / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path


# ---------------------------------------------------------------- 기록

def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_new_json(path: Path, payload: dict) -> None:
    """새 파일로만 쓴다("x" 모드). 이미 있으면 FileExistsError다."""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


class EpisodeLog:
    """Episode마다 한 줄을 episodes.jsonl에 바로 덧붙인다. 중간에 멈춰도 이미 돈 Episode의 기록은 남는다.

    한 줄: stage(pilot, round-1, round-2, holdout-pi0, holdout-pistar), policy_version(Langfuse version 라벨),
    injected_mistakes(scripted 운영 단계만), semantic(holdout만: 의미 판정 목록), summary(episodes.episode_summary).
    """

    def __init__(self, path: Path):
        path.open("x", encoding="utf-8").close()
        self.path = path

    def add(self, stage: str, policy_version: str, artifact: Artifact, *,
            injected_mistakes: Sequence[str] = (), semantic: Sequence[SemanticVerdict] | None = None) -> None:
        line = {
            "stage": stage,
            "policy_version": policy_version,
            "injected_mistakes": list(injected_mistakes),
            "semantic": [asdict(verdict) for verdict in semantic] if semantic is not None else None,
            "summary": episode_summary(artifact),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 측정

class Measurement:
    """P3 측정 한 번. 사전 점검을 통과한 입력만 받는다. run()이 pilot -> 1·2라운드 -> holdout -> manifest를 진행한다."""

    def __init__(self, deps: Dependencies, *, mode: Mode, holdout_cards: Sequence[Scenario],
                 dev_expected: dict[str, Expected], run_dir: Path, prereg_sha256: str, scenarios: Path):
        self.deps = deps
        self.mode = mode
        self.holdout_cards = list(holdout_cards)
        self.holdout_ids = [card.metadata.scenario_id for card in self.holdout_cards]
        self.holdout_expected = {card.metadata.scenario_id: card.expected_output for card in self.holdout_cards}
        self.dev_expected = dev_expected
        self.run_dir = run_dir
        self.prereg_sha256 = prereg_sha256
        self.scenarios = scenarios
        self.fixtures = load_fixtures()
        self.log = EpisodeLog(run_dir / "episodes.jsonl")
        self.semantic_usage = JudgeUsage()
        self.agent_calls = 0
        self.rounds_run = 0
        self.pilot_records: list[dict] = []
        self.driver: MistakeDriver | None = None
        # holdout Artifact마다 (stage, 정책 version). evaluate_holdout이 기록 줄을 쓸 때 읽는다.
        self.holdout_roles: dict[str, tuple[str, str]] = {}
        self.pi0_spec = EMPTY_POLICY

    # -------------------------------------------------- 운영 단계

    def _operate(self, items: Sequence[TrafficItem], spec: PolicySpec, *, stage: str, label: str) -> list[dict]:
        """운영 항목을 현재 정책을 게이트로 걸어 돌린다. 전환 뒤면 scripted 드라이버, 아니면 실제 모델이다."""
        if self.driver is None:
            records = run_traffic(list(items), mode="live", model=self.deps.agent_model, langfuse=self.deps.langfuse,
                                  gate=as_gate(spec), environment_tag=ENVIRONMENT_TAG, release=RELEASE, version=label)
        else:
            records = run_traffic(list(items), mode="scripted", driver=self.driver, langfuse=self.deps.langfuse,
                                  gate=as_gate(spec), environment_tag=ENVIRONMENT_TAG, release=RELEASE, version=label)
        for record in records:
            self.agent_calls += record["model_calls"]
            self.log.add(stage, label, record["artifact"], injected_mistakes=record["injected_mistakes"])
        return records

    def _traffic_for_round(self, round_no: int, spec: PolicySpec) -> list[dict]:
        """rsi.run_round의 run_traffic_fn. 1라운드는 pilot 뒤의 18건만 새로 돌린다(pilot은 pilot_records로 들어간다).

        Episode ID가 매번 새 uuid라 run_round의 중복 검사는 pilot을 다시 돌린 것을 잡지 못한다. 그래서 여기서 자른다.
        """
        items = round_items(round_no)
        if round_no == 1:
            items = items[len(self.pilot_records):]
        return self._operate(items, spec, stage=f"round-{round_no}", label=ROUND_VERSION_LABELS[round_no])

    def _evaluate_traffic(self, records: Sequence[dict]) -> list[tuple[TrajectoryVerdict, bool | None]]:
        """라운드의 evaluate_fn. Code 판정만 쓴다(P1): 궤적 판정과 업무 결과(check_outcome, 항목 가족의 dev 기대 상태)."""
        return [
            (evaluate_trajectory(record["artifact"]),
             check_outcome(record["artifact"], self.dev_expected[record["family_id"]]).passed)
            for record in records
        ]

    # -------------------------------------------------- holdout

    def _run_holdout(self, spec: PolicySpec, reps: int) -> list[Artifact]:
        """rsi.holdout_check의 run_holdout_fn. 사례마다 trial 1..reps를 실제 모델로 돌린다. scenario_id는 사례 ID다."""
        # π*는 round-2.json에서 다시 검증한 새 객체라, 내용이 빈 정책과 같아도 π0(EMPTY_POLICY)와 객체가 다르다.
        stage = "holdout-pi0" if spec is self.pi0_spec else "holdout-pistar"
        gate = as_gate(spec)
        artifacts = []
        for card in self.holdout_cards:
            for trial in range(1, reps + 1):
                artifact = execute_episode(
                    card.input, self.fixtures[card.fixture_id], followups=card.followups, max_turns=card.max_turns,
                    scenario_id=card.metadata.scenario_id, release=RELEASE, trial=trial, mode="live",
                    prompt=PROMPTS[RELEASE], model=self.deps.agent_model, langfuse=self.deps.langfuse, gate=gate,
                    environment_tag=ENVIRONMENT_TAG, tags=["p3-holdout", stage], version=spec.version)
                self.agent_calls += artifact.model_calls
                self.holdout_roles[artifact.artifact_id] = (stage, spec.version)
                artifacts.append(artifact)
        return artifacts

    def _evaluate_holdout(self, artifacts: Sequence[Artifact],
                          ) -> list[tuple[TrajectoryVerdict, bool | None, list[SemanticVerdict]]]:
        """holdout의 evaluate_fn. Code 판정(P5 입력)에 의미 판정 연쇄(Code -> Jev -> Judge, 보고용)를 붙인다.

        holdout은 Golden이 있는 오프라인 평가이므로 DESIGN 6.1대로 동결된 기대 답변(Expected)을 reference로 넣는다.
        """
        results = []
        for artifact in artifacts:
            expected = self.holdout_expected[artifact.scenario_id]
            semantic = judge_semantics(artifact, decider=self.deps.decider, judge_model=self.deps.judge_model,
                                       mode="cascade", reference=expected, usage=self.semantic_usage)
            stage, version = self.holdout_roles[artifact.artifact_id]
            self.log.add(stage, version, artifact, semantic=semantic)
            results.append((evaluate_trajectory(artifact), check_outcome(artifact, expected).passed, semantic))
        return results

    # -------------------------------------------------- 진행

    def run(self) -> dict:
        """pilot -> 1·2라운드 -> holdout을 진행하고 run_manifest.json을 남긴다. 실패해도 manifest는 남기고 예외를 다시 낸다."""
        manifest = self._manifest_header()
        status, error_text = "failed", None
        try:
            self._run_stages(manifest)
            status = "completed"
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}"
            raise
        finally:
            if self.deps.langfuse is not None:
                self.deps.langfuse.flush()
            manifest.update(status=status, error=error_text, ended_at=_utc_now(), calls=self._calls(),
                            files=sorted([*(path.name for path in self.run_dir.iterdir()), "run_manifest.json"]))
            _write_new_json(self.run_dir / "run_manifest.json", manifest)
        return manifest

    def _run_stages(self, manifest: dict) -> None:
        # 1단계: pilot. π0로 1라운드의 첫 9 Episode를 실제 모델로 돌리고 전환 여부를 정한다.
        self.pilot_records = self._operate(pilot_items(), self.pi0_spec, stage="pilot", label=ROUND_VERSION_LABELS[1])
        pilot = pilot_decision(self.pilot_records, [evaluate_trajectory(r["artifact"]) for r in self.pilot_records])
        print(f"[pilot] {pilot['reason']}")
        if pilot["switch_to_scripted"]:
            self.driver = make_mistake_driver(FALLBACK_MISTAKE_RATES, seed=FALLBACK_SEED)
        manifest["pilot"] = pilot
        manifest["fallback"]["switched"] = pilot["switch_to_scripted"]

        # 2단계: 1라운드와 2라운드. 2라운드는 1라운드에서 고른 정책에서 시작한다.
        pool_dir = self.run_dir / "pools"
        common = {"evaluate_fn": self._evaluate_traffic, "improver": self.deps.improver, "pool_dir": pool_dir,
                  "out_dir": self.run_dir, "holdout_ids": self.holdout_ids, "langfuse": self.deps.langfuse}
        current = self.pi0_spec
        pool_paths = []
        for round_no in (1, 2):
            pilot_records = self.pilot_records if round_no == 1 else ()
            payload = run_round(round_no, run_traffic_fn=self._traffic_for_round, current_spec=current,
                                pilot_records=pilot_records, **common)
            self.rounds_run += 1
            current = validate_spec(payload["chosen_spec"])
            pool_paths.append(Path(payload["pool_path"]))
            manifest["policies"][f"after_round_{round_no}"] = current.version
            print(f"[{round_no}라운드] Episode {payload['traffic']['episodes']}건, 치명 위반 "
                  f"{payload['evaluation']['fatal_episodes']}건, 고른 정책 {current.version}")

        # 3단계: holdout. 라운드에서 쓴 풀 전체로 오염 검사를 하고 π0와 최종 π*를 한 번씩 연다.
        pool = [episode for path in pool_paths for episode in load_pool(path)]
        manifest["version_labels"]["holdout-pistar"] = current.version
        holdout = holdout_check(pi0_spec=self.pi0_spec, pistar_spec=current, run_holdout_fn=self._run_holdout,
                                evaluate_fn=self._evaluate_holdout, pool=pool, holdout_ids=self.holdout_ids,
                                out_dir=self.run_dir, reps=HOLDOUT_REPS)
        manifest["decision"] = holdout["decision"]
        manifest["decision_reasons"] = holdout["reasons"]
        print(f"[holdout] P5 판정 {holdout['decision']}: {' / '.join(holdout['reasons'])}")

    def _manifest_header(self) -> dict:
        """시작 시점에 정해진 값. 진행하며 pilot, policies, decision, calls를 채운다."""
        config, deps = self.deps.config, self.deps
        return {
            "kind": "day05-new-p3-measurement",
            "mode": self.mode,
            "status": "running",
            "error": None,
            "started_at": _utc_now(),
            "ended_at": None,
            "prereg_sha256": self.prereg_sha256,
            "scenarios": str(self.scenarios),
            "holdout_ids": self.holdout_ids,
            "key_check": "eval_lab factory(설정됨/미설정)" if self.mode == "live" else "생략: --offline은 가짜 모델이라 키를 쓰지 않습니다",
            "models": {
                # 공급자와 주소. 2026-11-05부터 기본은 OpenGateway의 DeepSeek이다(eval_lab/settings.py PROVIDERS).
                "provider": {"name": config.provider, "api_url": provider_of(config).api_url},
                "agent": {"model": config.model, "effort": config.effort, "class": type(deps.agent_model).__name__},
                "judge": {"model": config.judge_model, "effort": config.judge_effort,
                          "class": type(deps.judge_model).__name__},
                "improver": {"model": config.model, "effort": config.improver_effort,
                             "class": type(deps.improver).__name__},
                "decider": {"backend": deps.decider.name},
            },
            "thresholds": {"t_lo": T_LO, "t_hi": T_HI, "status": "미조정"},
            "release": RELEASE,
            "environment_tag": ENVIRONMENT_TAG,
            "langfuse": deps.langfuse is not None,
            "version_labels": {"pilot": ROUND_VERSION_LABELS[1], "round-1": ROUND_VERSION_LABELS[1],
                               "round-2": ROUND_VERSION_LABELS[2], "holdout-pi0": self.pi0_spec.version,
                               "holdout-pistar": None},
            "policies": {"r0": self.pi0_spec.version, "after_round_1": None, "after_round_2": None},
            "pilot": None,
            "fallback": {"switched": None, "mistake_rates": FALLBACK_MISTAKE_RATES, "seed": FALLBACK_SEED,
                         "scope": "1·2라운드 운영 단계만. pilot과 holdout은 실제 모델이다."},
            "planned_calls_max": {"agent": AGENT_CALLS_MAX, "jev": JEV_CALLS_MAX, "judge": JUDGE_CALLS_MAX,
                                  "improver": IMPROVER_CALLS_MAX},
            "calls": None,
            "decision": None,
            "decision_reasons": None,
            "files": None,
        }

    def _calls(self) -> dict:
        """실제 호출 수. 에이전트는 Episode의 model_calls 합, Jev·Judge는 JudgeUsage, 개선기는 실행한 라운드 수다."""
        return {
            "agent": self.agent_calls,
            "jev": self.semantic_usage.jev_calls,
            "judge": self.semantic_usage.judge_calls,
            "improver": self.rounds_run,
            "escalation_rate": self.semantic_usage.escalation_rate,
        }


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PREREG P3 저자 측정. 플래그가 없으면 계획과 호출 규모만 출력합니다.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="실제 모델·Jev·Judge·Langfuse로 측정합니다(유료).")
    mode.add_argument("--offline", action="store_true",
                      help="같은 측정 코드를 tests/fakes.py의 가짜로 돌립니다(키·네트워크 없음).")
    parser.add_argument("--no-langfuse", action="store_true", help="Langfuse 없이 로컬 파일에만 기록합니다.")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS,
                        help=f"시나리오 파일. 기본 {DEFAULT_SCENARIOS.relative_to(DAY05_NEW)}.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"출력 루트. 기본 {DEFAULT_OUT.relative_to(DAY05_NEW)}. 그 아래 measurement/<UTC 시각>/에 씁니다.")
    return parser


def main(argv: Sequence[str] | None = None, *, offline_agent: BaseChatModel | None = None) -> int:
    """CLI 진입점. offline_agent는 --offline에서 기본 가짜 에이전트 대신 쓸 모델이다(시험이 넘긴다)."""
    args = build_parser().parse_args(argv)
    if not (args.live or args.offline):
        print_plan(args.scenarios)
        return EXIT_OK

    mode: Mode = "live" if args.live else "offline"
    use_langfuse = not args.no_langfuse
    # 0단계: 사전 점검. 여기까지는 유료 호출이 없다.
    try:
        prereg_sha256 = check_prereg()
        holdout_cards = load_holdout(args.scenarios)
        dev_expected = load_dev_expected(args.scenarios, [*round_items(1), *round_items(2)])
        if args.live:
            deps = live_dependencies(load_settings(), use_langfuse=use_langfuse)
        else:
            deps = offline_dependencies(use_langfuse=use_langfuse, agent_model=offline_agent)
        check_langfuse(deps.langfuse)
        run_dir = new_measurement_dir(args.out)
    except PreflightError as error:
        print(f"사전 점검에서 멈췄습니다. 호출은 하지 않았습니다. {error}")
        return EXIT_PREFLIGHT

    # 1단계: 규모 고지. --offline은 가짜라 실제 호출은 없지만 같은 상한을 알린다.
    announce_totals("P3 저자 측정" if args.live else "P3 저자 측정 --offline(가짜 모델, 실제 호출 없음)")
    print(f"출력 폴더: {run_dir}")
    measurement = Measurement(deps, mode=mode, holdout_cards=holdout_cards, dev_expected=dev_expected,
                              run_dir=run_dir, prereg_sha256=prereg_sha256, scenarios=args.scenarios)
    try:
        manifest = measurement.run()
    except Exception:  # noqa: BLE001 - 어떤 실패든 이유와 남은 기록 위치를 알리고 종료 코드로 돌려준다.
        traceback.print_exc()
        print(f"측정이 멈췄습니다. 이미 남긴 기록은 지우지 않습니다: {run_dir}")
        return EXIT_RUN_FAILED
    print(f"측정 완료: P5 판정 {manifest['decision']}, 호출 {manifest['calls']}. 산출물: {run_dir}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
