"""합성 7일 배경 운영 기록: 계획(plan) -> 시뮬레이션(simulate) -> 옷 입히기(dress) -> 로컬 기록 -> OTLP 내보내기.

m3a·m4·m5 미션이 함께 쓰는 배경 운영 기록을 만든다. 수강생은 실습 폴더의 적재 도구로
자기 Langfuse 프로젝트에 한 번 적재한다. 이 모듈은 모델을 한 번도 부르지 않는다.

무엇이 진짜이고 무엇이 합성인가:
- 진짜(시뮬레이터 결과): Episode의 서비스 Event, 업무 상태, 응답. dev 시나리오의 입력과 fixture를
  주문 서비스 시뮬레이터(OrderEnvironment)에서 실수를 섞는 scripted 드라이버(traffic.MistakeDriver)로 실제로 실행한다.
- 합성: 시각, 지연, 토큰, 비용, 모델 호출(generation) observation. 분포는 저자의 실제 DeepSeek 실행
  1회 관찰(outputs/synth-probe/calibrate-all-notes.md: live Episode 56개, holdout 제외)에 맞췄다. 서비스 호출 지연은 그 관찰조차 없는 가정이다
  (시뮬레이터는 프로세스 안에서 0~3ms에 끝난다).
- scripted 드라이버의 결과와 합성 수치는 LLM 성능이 아니다. 모델 이름 synthetic/deepseek-v4.1-flash-ultrafast는
  실제 모델 호출이 아니라는 표시다. 모든 observation에 synthetic 표시가 붙는다.

이 기록을 쓰지 않는 곳: 06의 replay pool, holdout, PREREG P3 측정, 03b meta-evaluation.
holdout 가족(incident-hv-*)과 holdout fixture는 만들지 않는다.

관측 트리(live와 비교): live는 episode > turn-N > LangGraph·model·tools CHAIN > ChatAnthropic > anthropic.messages.create
모양이다. 합성 트리는 CHAIN 래퍼와 안쪽 SDK generation을 빼고 모델 호출 1회에 바깥 GENERATION 하나만 둔다.
이 단순화는 근거 노트 6절 D3의 잠정 설계 선택이다(live와의 집계 차이는 미확인).

    episode(agent) > turn-N(agent) > model-call(generation) / <도구>(tool) > service.<도구>(span)

같은 (seed, anchor, environment)는 같은 계획, id, 시각, 요약을 만든다. 날짜만 anchor를 따르고
Episode 내용과 수치는 seed만 따르므로, 언제 적재해도 같은 이야기가 된다.
"""

import base64
import hashlib
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from threading import Lock
from typing import Protocol

from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Tracer, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)
from opentelemetry.util.types import AttributeValue

from eval_lab.agent import MAX_MODEL_CALLS, PROMPTS
from eval_lab.contracts import Artifact, Event, Scenario, TurnRecord
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.episodes import episode_summary, execute_episode
from eval_lab.online import count_observations, root_filter
from eval_lab.settings import Settings, require
from eval_lab.traffic import (
    DAY_MIX,
    STYLE_CODES,
    STYLE_WEIGHTS,
    MistakeDriver,
    TrafficItem,
    _build_item,
    record_from_artifact,
)

# ---------------------------------------------------------------- 이야기 상수

STORY_ID = "day05-ops-week-v1"
STORY_DAYS = 7
EPISODES_PER_DAY = 40
DEFAULT_SEED = 7

# 수강생 프로젝트에 적재할 기본 Langfuse environment. 다른 실습 기록과 섞이지 않게 전용 이름을 쓴다.
DEFAULT_ENVIRONMENT = "synth_ops"

# 합성 generation의 모델 이름. 실제 모델(deepseek/deepseek-v4.1-flash-ultrafast) 호출이 아니라는 표시다.
SYNTHETIC_MODEL = "synthetic/deepseek-v4.1-flash-ultrafast"
GENERATOR = "eval_lab.synth"

# 실습 폴더의 '이어서 처리' 운영 사례(use_cc/sandbox/ops.py의 RESUME_FAMILY와 같은 이름).
RESUME_FAMILY = "incident-ops-resume"
# holdout 가족의 접두사. 이 접두사의 가족은 합성 기록에 절대 넣지 않는다.
HOLDOUT_FAMILY_PREFIX = "incident-hv-"

# 한국 표준시. 일광 절약 시간이 없어 고정 오프셋으로 충분하다.
KST = timezone(timedelta(hours=9), "KST")

AGENT_V1 = "agent-v1"
AGENT_V2 = "agent-v2"

# scripted 드라이버가 따르는 Prompt 버전. 버전 라벨(agent-v1/v2)은 실수 확률만 바꾼다.
SCRIPTED_RELEASE = "baseline"

# KST 시각별 요청 가중치. 00~07시는 요청이 없고, 10~12시와 14~17시가 붐빈다(12시는 점심 시간이라 줄어든다).
# 23시에도 요청을 두지 않아 가장 늦은 Episode도 그날 안에 끝난다.
HOURLY_WEIGHTS = {8: 3, 9: 6, 10: 10, 11: 10, 12: 6, 13: 7, 14: 10, 15: 10, 16: 10,
                  17: 7, 18: 5, 19: 4, 20: 3, 21: 2, 22: 1}

# 버전별 실수 확률(traffic.MISTAKES의 이름). agent-v2는 최종 확인 생략이 잦다(6일차 canary가 드러낼 것).
MISTAKE_RATES = {
    AGENT_V1: {"blind_retry": 0.10, "skip_final_check": 0.05, "write_before_approval": 0.02,
               "claim_without_record": 0.02, "write_out_of_scope": 0.01},
    AGENT_V2: {"blind_retry": 0.10, "skip_final_check": 0.40, "write_before_approval": 0.02,
               "claim_without_record": 0.02, "write_out_of_scope": 0.01},
}


# ---------------------------------------------------------------- 이야기 구성

@dataclass(frozen=True)
class StoryDay:
    """이야기의 하루. 시각은 모두 KST 시(hour)다.

    - version: 그날의 기본 버전.
    - resume_share: incident-ops-resume 요청의 비율. 개수는 round(하루 Episode 수 x 비율)로 정확히 맞춘다.
    - incident_hours: [시작 시, 끝 시) 결제 장애 창. 창 안의 요청은 incident_mix를 따르고 결제 도구가 느리다.
    - canary_version, canary_share, canary_full_hour: canary_full_hour 전에는 canary_share 비율만,
      그 시각부터는 전부 canary_version으로 처리한다.
    """

    story_day: int
    description: str
    version: str = AGENT_V1
    resume_share: float = 0.0
    incident_hours: tuple[int, int] | None = None
    canary_version: str | None = None
    canary_share: float = 0.0
    canary_full_hour: int | None = None


@dataclass(frozen=True)
class Story:
    """7일 이야기 전체. normal_mix·incident_mix는 dev 가족(또는 incident-ops-resume)의 가중치다."""

    story_id: str
    episodes_per_day: int
    days: tuple[StoryDay, ...]
    normal_mix: dict[str, int]
    incident_mix: dict[str, int]
    mistake_rates: dict[str, dict[str, float]]
    hourly_weights: dict[int, int]


DEFAULT_STORY = Story(
    story_id=STORY_ID,
    episodes_per_day=EPISODES_PER_DAY,
    days=(
        StoryDay(1, "평소 운영", resume_share=0.05),
        StoryDay(2, "평소 운영", resume_share=0.05),
        StoryDay(3, "평소 운영", resume_share=0.05),
        StoryDay(4, "평소 운영", resume_share=0.05),
        StoryDay(5, "결제 장애 14:00-16:00 KST", resume_share=0.05, incident_hours=(14, 16)),
        StoryDay(6, "agent-v2 canary: 13시 전 20%, 13시부터 100%", resume_share=0.05,
                 canary_version=AGENT_V2, canary_share=0.20, canary_full_hour=13),
        StoryDay(7, "이어서 처리 요청 급증(6일차 canary 뒤 agent-v1로 되돌림)", resume_share=0.40),
    ),
    normal_mix=DAY_MIX[1],
    incident_mix=DAY_MIX[2],
    mistake_rates=MISTAKE_RATES,
    hourly_weights=HOURLY_WEIGHTS,
)


class ResumeFactory(Protocol):
    """incident-ops-resume 항목을 만드는 함수. 실습 폴더는 ops.resume_item을 넘긴다."""

    def __call__(self, item_id: str, *, day: int, style: str) -> TrafficItem: ...


@dataclass(frozen=True)
class EpisodePlan:
    """Episode 하나의 계획. 실행 전에 정해지는 것만 담는다(모의 트래픽 - LLM 성능이 아니다).

    index는 이야기 전체의 시간순 번호(0부터), date는 KST 날짜, start_time은 UTC(ms 정밀도)다.
    incident는 결제 장애 창 안의 요청인가다. 이 표시는 Langfuse에 보내지 않는다(장애는 수강생이 찾을 몫이다).
    """

    story_id: str
    seed: int
    index: int
    story_day: int
    date: str
    start_time: datetime
    version: str
    item: TrafficItem
    mistake_rates: dict[str, float]
    incident: bool


# ---------------------------------------------------------------- 1. 계획

MS_PER_HOUR = 3_600_000


def plan_episodes(story: Story, *, seed: int, anchor: datetime,
                  resume_factory: ResumeFactory | None = None) -> list[EpisodePlan]:
    """이야기를 Episode 계획 목록으로 펼친다. 같은 (story, seed, anchor)는 같은 계획이다.

    - 날짜: anchor(적재 시각)의 KST 날짜를 기준으로 1일차 = 기준일 - 7일 ... 7일차 = 기준일 - 1일이다.
      모든 시작 시각이 기준일 0시(KST) 전이라 미래 시각이 없다.
    - 가족·문형·버전·시각의 추첨은 (seed, story_id, 날짜 번호)로만 정한다. anchor는 날짜만 옮긴다.
    - dev 가족은 load_dataset(split='dev') 카드로, incident-ops-resume은 resume_factory로 만든다.
    - ValueError: anchor에 시간대가 없을 때, 가족이 dev 가족도 incident-ops-resume도 아닐 때
      (holdout 가족 incident-hv-*는 이름을 대고 거절한다), 이어서 처리 요청이 필요한데 resume_factory가 없을 때.
    """
    # 1단계: 기준 시각과 이야기 구성을 먼저 검사한다. 실행 전에 실패해야 한다.
    if anchor.tzinfo is None or anchor.utcoffset() is None:
        raise ValueError("anchor는 시간대가 있는 datetime이어야 합니다(예: datetime.now(timezone.utc)).")
    cards_by_family = {card.metadata.family_id: card for card in load_dataset(split="dev")}
    _check_story(story, dev_families=set(cards_by_family))
    if _needs_resume(story) and resume_factory is None:
        raise ValueError(f"이 이야기에는 {RESUME_FAMILY} 요청이 필요합니다. resume_factory(실습 폴더의 ops.resume_item)를 넘기세요.")

    # 2단계: 날마다 계획을 만든다. 번호는 이야기 전체에서 시간순으로 이어진다.
    anchor_date = anchor.astimezone(KST).date()
    plans: list[EpisodePlan] = []
    for day in story.days:
        day_date = anchor_date - timedelta(days=len(story.days) + 1 - day.story_day)
        plans.extend(_plan_day(story, day, day_date, seed=seed, first_index=len(plans),
                               cards_by_family=cards_by_family, resume_factory=resume_factory))
    return plans


def _check_story(story: Story, *, dev_families: set[str]) -> None:
    """날짜 번호, 가족 이름, 버전별 실수 확률이 맞는지 검사한다. 틀리면 ValueError."""
    # 1단계: 날짜 번호는 1부터 빠짐없이 이어져야 날짜 계산(기준일 - 7 ... - 1)이 맞다.
    numbers = [day.story_day for day in story.days]
    if numbers != list(range(1, len(story.days) + 1)):
        raise ValueError(f"story_day는 1부터 차례로 이어져야 합니다: {numbers}")

    # 2단계: 가족은 dev 가족이거나 incident-ops-resume이어야 한다. holdout 가족은 이름을 대고 거절한다.
    for family in sorted({*story.normal_mix, *story.incident_mix}):
        if family.startswith(HOLDOUT_FAMILY_PREFIX):
            raise ValueError(f"holdout 가족은 합성 기록에 쓰지 않습니다: {family}")
        if family != RESUME_FAMILY and family not in dev_families:
            raise ValueError(f"dev 가족도 {RESUME_FAMILY}도 아닌 가족입니다: {family}")

    # 3단계: 그날 쓰는 버전마다 실수 확률이 있어야 한다.
    for day in story.days:
        for version in filter(None, (day.version, day.canary_version)):
            if version not in story.mistake_rates:
                raise ValueError(f"{day.story_day}일차 버전 {version}의 실수 확률이 없습니다.")
        if not 0.0 <= day.resume_share <= 1.0:
            raise ValueError(f"{day.story_day}일차 resume_share는 0 이상 1 이하여야 합니다: {day.resume_share}")


def _needs_resume(story: Story) -> bool:
    """이야기 어딘가에 incident-ops-resume 요청이 들어가는가."""
    in_mix = RESUME_FAMILY in story.normal_mix or RESUME_FAMILY in story.incident_mix
    return in_mix or any(day.resume_share > 0 for day in story.days)


def _shuffled_quota(rng: random.Random, weights: dict[str, int], count: int) -> list[str]:
    """count개의 자리를 가중치 비율대로 정확히 나눈 이름 목록을 섞어 돌려준다(최대 나머지 방식).

    날마다 무작위로 추첨하면 Episode 40건의 표본 잡음만으로 입력 분포 경보(전체 변동 거리 > 0.3)가
    평범한 날에도 울린다(seed 7 무작위 추첨 1회 관찰: 2일차 0.32, 3일차 0.38). 그래서 개수는 비율로 고정하고 자리만 섞는다.
    """
    total = sum(weights.values())
    shares = {name: count * weight / total for name, weight in weights.items()}
    counts = {name: math.floor(share) for name, share in shares.items()}
    # 남은 자리는 나머지가 큰 이름부터 하나씩 준다. 나머지가 같으면 dict 순서를 따른다.
    by_remainder = sorted(weights, key=lambda name: counts[name] - shares[name])
    for name in by_remainder[:count - sum(counts.values())]:
        counts[name] += 1
    names = [name for name, how_many in counts.items() for _ in range(how_many)]
    rng.shuffle(names)
    return names


def _pick_version(day: StoryDay, hour: int, rng: random.Random) -> str:
    """요청 시각의 버전을 정한다. 추첨은 언제나 한 번 해서 다른 추첨 순서가 날마다 밀리지 않게 한다."""
    draw = rng.random()
    if day.canary_version is None:
        return day.version
    if day.canary_full_hour is not None and hour >= day.canary_full_hour:
        return day.canary_version
    return day.canary_version if draw < day.canary_share else day.version


def _plan_day(story: Story, day: StoryDay, day_date: date, *, seed: int, first_index: int,
              cards_by_family: dict[str, Scenario],
              resume_factory: ResumeFactory | None) -> list[EpisodePlan]:
    """하루치 계획. 시작 시각을 시간대 곡선에서 뽑아 시간순으로 놓고 자리마다 요청을 정한다."""
    rng = random.Random(f"synth-plan:{seed}:{story.story_id}:{day.story_day}")
    count = story.episodes_per_day

    # 1단계: 시작 시각(그날 0시부터의 ms)을 시간대 가중치로 뽑아 정렬한다.
    hours = list(story.hourly_weights)
    hour_weights = [story.hourly_weights[hour] for hour in hours]
    offsets_ms = sorted(rng.choices(hours, weights=hour_weights)[0] * MS_PER_HOUR + rng.randrange(MS_PER_HOUR)
                        for _ in range(count))

    # 2단계: 자리를 셋으로 나눈다. 이어서 처리 요청(정확한 개수), 장애 창 안, 그 밖.
    hours_of = [offset_ms // MS_PER_HOUR for offset_ms in offsets_ms]
    resume_slots = set(rng.sample(range(count), round(count * day.resume_share)))
    incident_slots = [position for position in range(count) if position not in resume_slots
                      and day.incident_hours is not None
                      and day.incident_hours[0] <= hours_of[position] < day.incident_hours[1]]
    normal_slots = [position for position in range(count)
                    if position not in resume_slots and position not in incident_slots]

    # 3단계: 가족과 문형을 비율대로 정확히 나눠 자리에 섞어 놓는다. 장애 창 안은 incident_mix를 따른다.
    families = dict.fromkeys(resume_slots, RESUME_FAMILY)
    families.update(zip(incident_slots, _shuffled_quota(rng, story.incident_mix, len(incident_slots))))
    families.update(zip(normal_slots, _shuffled_quota(rng, story.normal_mix, len(normal_slots))))
    styles = _shuffled_quota(rng, STYLE_WEIGHTS, count)

    # 4단계: 자리마다 버전을 정하고 항목을 만든다.
    midnight_kst = datetime.combine(day_date, time(0), tzinfo=KST)
    plans = []
    for position, offset_ms in enumerate(offsets_ms):
        hour = hours_of[position]
        incident = position in incident_slots
        family, style = families[position], styles[position]
        version = _pick_version(day, hour, rng)

        item_id = f"s{day.story_day}-{position:02d}-{STYLE_CODES[style]}-{family.removeprefix('incident-')}"
        item = _make_item(family, item_id=item_id, day=day.story_day, style=style,
                          cards_by_family=cards_by_family, resume_factory=resume_factory)
        start_utc = (midnight_kst + timedelta(milliseconds=offset_ms)).astimezone(UTC)
        plans.append(EpisodePlan(story_id=story.story_id, seed=seed, index=first_index + position,
                                 story_day=day.story_day, date=day_date.isoformat(), start_time=start_utc,
                                 version=version, item=item, mistake_rates=dict(story.mistake_rates[version]),
                                 incident=incident))
    return plans


def _make_item(family: str, *, item_id: str, day: int, style: str, cards_by_family: dict[str, Scenario],
               resume_factory: ResumeFactory | None) -> TrafficItem:
    """가족 하나의 항목. dev 가족은 traffic의 항목 생성기로, 이어서 처리는 resume_factory로 만든다."""
    if family != RESUME_FAMILY:
        return _build_item(cards_by_family[family], item_id=item_id, day=day, style=style)
    # plan_episodes가 resume_factory 유무를 먼저 검사했으므로 여기서는 항상 있다.
    item = resume_factory(item_id, day=day, style=style)
    if item.family_id != RESUME_FAMILY:
        raise ValueError(f"resume_factory가 {RESUME_FAMILY}가 아닌 항목을 만들었습니다: {item.family_id}")
    return item


# ---------------------------------------------------------------- 2. 시뮬레이션 (모델 호출 0회)

@dataclass(frozen=True)
class SimulatedEpisode:
    """시뮬레이터로 실제 실행한 Episode. artifact의 id·시각은 아직 실행 순간의 값(uuid, perf_counter)이다."""

    plan: EpisodePlan
    artifact: Artifact
    actor_id: str
    injected_mistakes: list[str]


def simulate(plans: list[EpisodePlan], *, fixtures: dict | None = None) -> list[SimulatedEpisode]:
    """계획마다 Episode를 주문 서비스 시뮬레이터에서 실행한다. 모델 호출 0회다(모의 트래픽 - LLM 성능이 아니다).

    - execute_episode(mode='scripted', langfuse=None)와 버전별 실수 확률의 MistakeDriver를 쓴다.
      Event, 업무 상태, 응답은 시뮬레이터가 실제로 낸 결과이고, 드라이버가 시도한 실수 이름도 남긴다.
    - fixtures가 없으면 dataset.load_fixtures()를 쓴다. 실습 폴더의 data/fixtures.json에는 fx-ops-resume이 들어 있고,
      저장소의 data/fixtures.json에는 없다. 계획에 필요한 fixture가 없으면 ValueError다.
    """
    fixtures = load_fixtures() if fixtures is None else fixtures
    episodes = []
    for plan in plans:
        # 1단계: fixture를 찾는다. 없는 fixture를 조용히 건너뛰지 않는다.
        item = plan.item
        if item.fixture_id not in fixtures:
            raise ValueError(f"fixture {item.fixture_id}가 없습니다. 이어서 처리 요청에는 use_cc/ops_fixtures.json을 "
                             "더한 fixture(실습 폴더의 data/fixtures.json)가 필요합니다.")
        fixture = fixtures[item.fixture_id]

        # 2단계: 버전별 실수 확률의 드라이버로 Episode를 실행한다. 실수 선택은 (seed, 요청 ID)로 정해진다.
        driver = MistakeDriver(plan.mistake_rates, seed=plan.seed)
        artifact = execute_episode(
            item.request, fixture, followups=item.followups, max_turns=item.max_turns,
            scenario_id=item.item_id, release=SCRIPTED_RELEASE, trial=1, mode="scripted",
            prompt=PROMPTS[SCRIPTED_RELEASE], langfuse=None, scripted_driver=driver)
        injected = list(driver.injected.get(item.request.request_id, []))
        episodes.append(SimulatedEpisode(plan=plan, artifact=artifact, actor_id=fixture["actor_id"],
                                         injected_mistakes=injected))
    return episodes


# ---------------------------------------------------------------- 3. 옷 입히기: 합성 시각·지연·토큰·비용과 observation 트리

# 표준정규분포의 90% 분위수. 중앙값과 p90으로 로그정규 분포의 sigma를 정한다.
_Z90 = NormalDist().inv_cdf(0.9)


@dataclass(frozen=True)
class LogNormal:
    """중앙값과 p90에 맞춘 로그정규 분포. 뽑은 값은 [low, high]로 자른다."""

    median: float
    p90: float
    low: float
    high: float

    def draw(self, rng: random.Random) -> float:
        sigma = math.log(self.p90 / self.median) / _Z90
        value = rng.lognormvariate(math.log(self.median), sigma)
        return min(max(value, self.low), self.high)


# 보정 분포: outputs/synth-probe/calibrate-all-notes.md(live Episode 56개, holdout 제외, generation 318개; 1회 관찰).
# 중앙값, p90, 관측 최솟값, 최댓값. 토큰은 Langfuse generation usage 값이다.
GENERATION_LATENCY_MS = LogNormal(median=276, p90=567, low=159, high=1315)
INPUT_TOKENS = LogNormal(median=268, p90=358, low=130, high=1567)
OUTPUT_TOKENS = LogNormal(median=60, p90=197, low=41, high=476)
# cache_read는 턴의 첫 호출에서 0이다(캐시가 아직 없다). 나머지 호출에서 이 분포를 쓴다.
CACHE_READ_TOKENS = LogNormal(median=1536, p90=2048, low=0, high=2304)

# 서비스 호출 지연은 합성 가정이다. 시뮬레이터는 프로세스 안에서 0~3ms에 끝나 실제 서비스 지연의 근거가 없다.
# 평소 호출은 중앙값 40ms·p90 120ms, 결제 TIMEOUT은 결제 서비스의 제한 시간 약 5초(4.5~5.5초)로 둔다.
# TIMEOUT 폭을 3~8초로 넓게 두면 평범한 날끼리도 p95 비가 1.5배를 넘는 일이 생겨(seed 5 1회 관찰) 좁혔다.
SERVICE_LATENCY_MS = LogNormal(median=40, p90=120, low=2, high=500)
TIMEOUT_LATENCY_MS = (4500.0, 5500.0)
# 5일차 장애 창 안에서 결제 도구 호출은 이 배수만큼 느리다(합성 가정).
PAYMENT_TOOLS = frozenset({"get_payment", "refund_payment"})
INCIDENT_PAYMENT_SLOWDOWN = 4.0

# observation 사이 틈(ms). 프레임워크 오버헤드 자리다. 1 이상이라 형제의 시작 ms가 겹치지 않는다.
GAP_MS = (1, 4)

# 모델 호출 한 번이 요청하는 도구 호출 수(1~3)의 가중치. Episode당 모델 호출 수가 보정 관찰
# (calibrate-all-notes.md: 56 Episode, 중앙값 5, p90 10, 최대 11; 1회 관찰)에 가깝도록 정한 합성 입력이다.
# 기본 이야기(seed 7)에서 중앙값 5, p90 8, 최대 10이 나온다. p90을 10까지 올리면 중앙값이 6 이상으로 같이 올라
# 중앙값 5를 우선했다. 도구 호출 수는 시뮬레이터가 정하므로 이 가중치로 더 맞출 수 없다.
TOOLS_PER_CALL_WEIGHTS = {1: 62, 2: 30, 3: 8}

# 합성 비용 계산에만 쓰는 가격(USD / 100만 토큰). 저자가 2026-11-05에 적어 둔 OpenGateway 할인 표시가다.
PRICE_INPUT_PER_MTOK = 0.15
PRICE_OUTPUT_PER_MTOK = 0.60

NS_PER_MS = 1_000_000


@dataclass(frozen=True)
class SyntheticSpan:
    """보낼 observation 하나. 시각은 epoch ms, attributes는 OTLP 속성 그대로다(trace 전체 속성 포함)."""

    span_id: str
    parent_id: str | None
    name: str
    start_ms: int
    end_ms: int
    attributes: dict[str, AttributeValue]


@dataclass(frozen=True)
class DressedEpisode:
    """합성 시각·id·사용량을 입힌 Episode. spans[0]이 root(episode)이고 나머지는 시작 시각 순서다.

    artifact는 원래 Artifact에서 id(artifact_id, episode_id, event_id)를 결정적 값으로, Event 시각을
    service span 시각으로, 사용량을 generation 합계로, elapsed_seconds를 root 길이로 바꾼 것이다.
    """

    plan: EpisodePlan
    environment: str
    trace_id: str
    artifact: Artifact
    injected_mistakes: list[str]
    spans: list[SyntheticSpan]


def validate_environment(name: str) -> str:
    """Langfuse environment 이름 규칙을 검사하고 이름을 돌려준다.

    소문자·숫자·'-'·'_'만, 1~40자, 'langfuse'로 시작하지 않는다. 어기면 ValueError다
    (규칙을 어긴 이름은 SDK가 버리므로 적재 전에 막는다).
    """
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", name) or name.startswith("langfuse"):
        raise ValueError(f"environment 이름은 소문자·숫자·-·_ 1~40자이고 langfuse로 시작하지 않아야 합니다: {name!r}")
    return name


def dress(simulated: list[SimulatedEpisode], *, environment: str = DEFAULT_ENVIRONMENT) -> list[DressedEpisode]:
    """시뮬레이션 결과에 합성 시각·지연·토큰·비용과 observation 트리를 입힌다.

    - id: sha256(seed, environment, Episode 번호, 경로)에서 trace id 32자리, span id 16자리를 뗀다.
      environment가 다르면 id가 달라지고 시각·수치는 같다.
    - 트리: episode(agent) > turn-N(agent) > model-call(generation) 다음에 그 호출이 요청한 도구 1~3개,
      각 도구는 <도구>(tool) > service.<도구>(span)다. 턴마다 마지막 model-call이 응답을 낸다.
      Episode당 model-call은 agent.MAX_MODEL_CALLS를 넘지 않는다.
    - 시각: root는 계획의 시작 시각에서 시작하고, 자식은 부모 안에, 형제는 Event step 순서로 겹치지 않게 놓는다.
    - 수치: generation 지연·토큰·cache_read는 보정 분포에서, 서비스 지연은 합성 가정(SERVICE_LATENCY_MS,
      TIMEOUT_LATENCY_MS, 5일차 장애 창의 INCIDENT_PAYMENT_SLOWDOWN)에서 뽑는다. 합성 값이며 LLM 성능이 아니다.
    """
    validate_environment(environment)
    return [_EpisodeDresser(episode, environment).dress() for episode in simulated]


def _json(value) -> str:
    """OTLP 속성에 넣을 JSON 문자열. 한국어를 그대로 둔다."""
    return json.dumps(value, ensure_ascii=False)


def _level_attributes(result: dict) -> dict[str, AttributeValue]:
    """서비스 결과의 status로 observation level을 정한다. error는 ERROR, denied는 WARNING, 메시지는 결과 code다."""
    level = {"error": "ERROR", "denied": "WARNING"}.get(result.get("status"))
    if level is None:
        return {}
    return {"langfuse.observation.level": level, "langfuse.observation.status_message": str(result.get("code"))}


def _service_latency_ms(rng: random.Random, event: Event, *, incident: bool) -> int:
    """서비스 호출 하나의 합성 지연(ms). 근거 있는 관찰이 아니라 가정이다(SERVICE_LATENCY_MS 주석)."""
    if event.result.get("code") == "TIMEOUT":
        latency = rng.uniform(*TIMEOUT_LATENCY_MS)
    else:
        latency = SERVICE_LATENCY_MS.draw(rng)
    if incident and event.tool in PAYMENT_TOOLS:
        latency *= INCIDENT_PAYMENT_SLOWDOWN
    return max(1, round(latency))


def _group_tool_calls(events: list[Event], rng: random.Random) -> list[list[Event]]:
    """턴 하나의 도구 호출을 차례대로 1~3개씩 묶는다. 묶음 하나가 model-call 한 번이 요청한 호출이다."""
    sizes = list(TOOLS_PER_CALL_WEIGHTS)
    weights = [TOOLS_PER_CALL_WEIGHTS[size] for size in sizes]
    groups, position = [], 0
    while position < len(events):
        size = rng.choices(sizes, weights=weights)[0]
        groups.append(events[position:position + size])
        position += size
    return groups


def _pack_tool_calls(events: list[Event]) -> list[list[Event]]:
    """도구 호출을 3개씩 묶는다. 무작위 묶음이 모델 호출 예산(MAX_MODEL_CALLS)을 넘을 때 쓴다."""
    return [events[position:position + 3] for position in range(0, len(events), 3)]


class _EpisodeDresser:
    """Episode 하나에 옷을 입힌다. 시각은 ms 정수 커서 하나를 앞으로만 움직여 정한다."""

    def __init__(self, episode: SimulatedEpisode, environment: str):
        plan = episode.plan
        self.episode = episode
        self.plan = plan
        self.environment = environment
        # 수치(시각·토큰)는 environment와 무관하게 (seed, story, 번호)로만 정한다.
        self.rng = random.Random(f"synth-dress:{plan.seed}:{plan.story_id}:{plan.index}")
        self.trace_id = self._hex("trace", 32)
        self.episode_id = self._hex("episode-id", 32)
        self.common = self._trace_attributes()
        self.spans: list[SyntheticSpan] = []
        self.dressed_events: dict[str, Event] = {}
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_usd = 0.0

    # ------------------------------------------------ 도우미

    def _hex(self, path: str, length: int) -> str:
        """결정적 16진수 id. sha256(seed, environment, 번호, 경로)의 앞 length자리다."""
        key = f"{self.plan.seed}|{self.environment}|{self.plan.index}|{path}"
        return hashlib.sha256(key.encode()).hexdigest()[:length]

    def _gap(self) -> int:
        return self.rng.randint(*GAP_MS)

    def _trace_attributes(self) -> dict[str, AttributeValue]:
        """모든 span에 복사하는 trace 전체 속성. Langfuse는 이 값을 root에서 자식으로 물려주지 않는다."""
        plan, item = self.plan, self.plan.item
        tags = ["synthetic", "day05-ops-week", f"day-{plan.story_day}", item.family_id,
                f"style-{STYLE_CODES[item.style]}"]
        trace_metadata = {"synthetic": "true", "generator": GENERATOR, "story": plan.story_id,
                          "seed": str(plan.seed), "scenario_id": item.item_id, "trial": "1", "mode": "synthetic"}
        attributes: dict[str, AttributeValue] = {
            "langfuse.environment": self.environment,
            "langfuse.version": plan.version,
            "session.id": self.episode_id,
            "user.id": self.episode.actor_id,
            "langfuse.trace.tags": tags,
            "langfuse.observation.metadata.synthetic": "true",
            "langfuse.observation.metadata.generator": GENERATOR,
        }
        attributes.update({f"langfuse.trace.metadata.{key}": value for key, value in trace_metadata.items()})
        return attributes

    def _add(self, path: str, parent_id: str | None, name: str, start_ms: int, end_ms: int,
             attributes: dict[str, AttributeValue]) -> str:
        """span 하나를 남기고 그 id를 돌려준다."""
        span_id = self._hex(path, 16)
        self.spans.append(SyntheticSpan(span_id=span_id, parent_id=parent_id, name=name, start_ms=start_ms,
                                        end_ms=end_ms, attributes={**self.common, **attributes}))
        return span_id

    # ------------------------------------------------ 조각

    def _model_call(self, path: str, parent_id: str, start_ms: int, *, turn_index: int, call_index: int,
                    model_input: dict, model_output: dict) -> int:
        """model-call generation 하나를 남기고 끝 시각을 돌려준다. 토큰·비용·지연은 합성 값이다."""
        # 1단계: 보정 분포에서 지연·토큰을 뽑는다. 턴의 첫 호출은 캐시가 없어 cache_read가 0이다.
        latency_ms = round(GENERATION_LATENCY_MS.draw(self.rng))
        input_tokens = round(INPUT_TOKENS.draw(self.rng))
        output_tokens = round(OUTPUT_TOKENS.draw(self.rng))
        cache_read = 0 if call_index == 1 else round(CACHE_READ_TOKENS.draw(self.rng))

        # 2단계: 가격 상수로 비용을 계산한다(합성 비용).
        input_cost = input_tokens * PRICE_INPUT_PER_MTOK / 1_000_000
        output_cost = output_tokens * PRICE_OUTPUT_PER_MTOK / 1_000_000
        self.model_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += input_cost + output_cost

        # 3단계: generation span을 남긴다. cache_read는 usage가 아니라 metadata에만 둔다.
        end_ms = start_ms + latency_ms
        self._add(path, parent_id, "model-call", start_ms, end_ms, {
            "langfuse.observation.type": "generation",
            "langfuse.observation.model.name": SYNTHETIC_MODEL,
            "langfuse.observation.input": _json(model_input),
            "langfuse.observation.output": _json(model_output),
            "langfuse.observation.usage_details": _json({"input": input_tokens, "output": output_tokens}),
            "langfuse.observation.cost_details": _json({"input": input_cost, "output": output_cost}),
            "langfuse.observation.metadata.cache_read_tokens": str(cache_read),
            "langfuse.observation.metadata.turn_index": str(turn_index),
            "langfuse.observation.metadata.call_index": str(call_index),
        })
        return end_ms

    def _tool_call(self, path: str, parent_id: str, start_ms: int, event: Event) -> int:
        """<도구>(tool) > service.<도구>(span) 한 쌍을 남기고, 결정적 id와 시각을 단 Event를 기록한다."""
        # 1단계: 시각을 정한다. service span은 tool span 안에 틈을 두고 놓는다.
        service_start = start_ms + self._gap()
        service_end = service_start + _service_latency_ms(self.rng, event, incident=self.plan.incident)
        tool_end = service_end + self._gap()

        # 2단계: 두 span을 남긴다. 결과 status가 error·denied면 level과 상태 메시지(code)를 단다.
        level = _level_attributes(event.result)
        tool_id = self._add(path, parent_id, event.tool, start_ms, tool_end, {
            "langfuse.observation.type": "tool",
            "langfuse.observation.input": _json(event.args),
            "langfuse.observation.output": _json(event.result),
            **level,
        })
        service_id = self._add(f"{path}/service", tool_id, f"service.{event.tool}", service_start, service_end, {
            "langfuse.observation.type": "span",
            "langfuse.observation.input": _json(event.args),
            "langfuse.observation.output": _json(event.result),
            "langfuse.observation.metadata.event_id": self._hex(f"event-{event.step}", 32),
            "langfuse.observation.metadata.step": str(event.step),
            **level,
        })

        # 3단계: Event에 결정적 id와 service span 시각을 단다. 인자·결과·step은 시뮬레이터 값 그대로다.
        self.dressed_events[event.event_id] = event.model_copy(update={
            "event_id": self._hex(f"event-{event.step}", 32),
            "start_ns": service_start * NS_PER_MS,
            "end_ns": service_end * NS_PER_MS,
            "observation_id": service_id,
            "parent_observation_id": tool_id,
        })
        return tool_end

    def _turn(self, turn: TurnRecord, groups: list[list[Event]], start_ms: int) -> int:
        """turn-N span과 그 안의 model-call·도구 호출을 남기고 turn의 끝 시각을 돌려준다."""
        path = f"turn-{turn.turn_index}"
        turn_id = self._hex(path, 16)
        cursor = start_ms + self._gap()
        model_input: dict = {"request": turn.request.model_dump(mode="json")}

        # 1단계: 묶음마다 model-call 한 번과 그 호출이 요청한 도구들. 마지막 빈 묶음은 응답을 내는 model-call이다.
        for call_index, group in enumerate([*groups, []], start=1):
            if group:
                model_output = {"tool_calls": [{"tool": event.tool, "args": event.args} for event in group]}
            else:
                model_output = {"response": turn.response.model_dump(mode="json") if turn.response else None}
            last_end = self._model_call(f"{path}/model-call-{call_index}", turn_id, cursor,
                                        turn_index=turn.turn_index, call_index=call_index,
                                        model_input=model_input, model_output=model_output)
            for event in group:
                last_end = self._tool_call(f"{path}/tool-{event.step}", turn_id, last_end + self._gap(), event)
            cursor = last_end + self._gap()
            model_input = {"tool_results": [{"tool": event.tool, "result": event.result} for event in group]}

        # 2단계: turn span은 마지막 자식이 끝난 뒤 틈을 두고 닫는다.
        end_ms = cursor
        response = turn.response.model_dump(mode="json") if turn.response else {"response_missing": True}
        self._add(path, self._hex("episode", 16), path, start_ms, end_ms, {
            "langfuse.observation.type": "agent",
            "langfuse.observation.input": _json(turn.request.model_dump(mode="json")),
            "langfuse.observation.output": _json(response),
            "langfuse.observation.metadata.episode_id": self.episode_id,
            "langfuse.observation.metadata.turn_index": str(turn.turn_index),
        })
        return end_ms

    def _tool_groups(self, events_by_turn: list[list[Event]]) -> list[list[list[Event]]]:
        """턴별 도구 묶음. model-call 합계(묶음 수 + 턴 수)가 MAX_MODEL_CALLS를 넘으면 3개씩 다시 묶는다."""
        groups = [_group_tool_calls(events, self.rng) for events in events_by_turn]
        calls = sum(len(turn_groups) + 1 for turn_groups in groups)
        if calls > MAX_MODEL_CALLS:
            groups = [_pack_tool_calls(events) for events in events_by_turn]
        return groups

    # ------------------------------------------------ 전체

    def dress(self) -> DressedEpisode:
        """Episode 전체를 입힌다: 턴 -> root -> 결정적 id의 Artifact -> root output 요약."""
        simulated = self.episode.artifact
        events_by_id = {event.event_id: event for event in simulated.events}
        events_by_turn = [[events_by_id[event_id] for event_id in turn.event_ids] for turn in simulated.turns]

        # 1단계: root 시작은 계획의 시작 시각(ms)이다. 턴을 차례로 놓는다.
        root_start = int(self.plan.start_time.timestamp() * 1000)
        cursor = root_start + self._gap()
        for turn, groups in zip(simulated.turns, self._tool_groups(events_by_turn)):
            cursor = self._turn(turn, groups, cursor) + self._gap()
        root_end = cursor

        # 2단계: 결정적 id·합성 시각·사용량으로 Artifact를 다시 만든다. 업무 내용은 시뮬레이터 값 그대로다.
        turns = [turn.model_copy(update={
            "event_ids": [self.dressed_events[event_id].event_id for event_id in turn.event_ids],
            "trace_id": self.trace_id,
        }) for turn in simulated.turns]
        artifact = simulated.model_copy(update={
            "artifact_id": self._hex("artifact-id", 32),
            "episode_id": self.episode_id,
            "events": [self.dressed_events[event.event_id] for event in simulated.events],
            "turns": turns,
            "elapsed_seconds": (root_end - root_start) / 1000,
            "model_calls": self.model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
        })

        # 3단계: root span. 입력은 첫 요청, 출력은 온라인 평가기가 읽는 Episode 요약이다.
        first_request = artifact.initial_request or artifact.request
        self._add("episode", None, "episode", root_start, root_end, {
            "langfuse.observation.type": "agent",
            "langfuse.observation.input": _json(first_request.model_dump(mode="json")),
            "langfuse.observation.output": _json(episode_summary(artifact)),
        })
        spans = sorted(self.spans, key=lambda span: span.start_ms)
        return DressedEpisode(plan=self.plan, environment=self.environment, trace_id=self.trace_id,
                              artifact=artifact, injected_mistakes=list(self.episode.injected_mistakes),
                              spans=spans)


# ---------------------------------------------------------------- 4. 로컬 기록 (모니터링·trace 선정 입력)

def local_records(dressed: list[DressedEpisode]) -> list[dict]:
    """옷 입힌 Episode를 traffic 기록 dict로 바꾼다. monitoring.local_metrics와 online.select_traces가 그대로 받는다.

    traffic.record_from_artifact의 키에 start_time(ISO UTC, ms), date(KST YYYY-MM-DD), story_day, version을 더한다.
    latency_ms는 root span의 길이(ms)다. 합성 값이며 LLM 성능이 아니다.
    """
    records = []
    for episode in dressed:
        plan, root = episode.plan, episode.spans[0]
        record = record_from_artifact(plan.item, episode.artifact, injected_mistakes=episode.injected_mistakes)
        record.update(
            latency_ms=float(root.end_ms - root.start_ms),
            start_time=plan.start_time.isoformat(timespec="milliseconds"),
            date=plan.date,
            story_day=plan.story_day,
            version=plan.version,
        )
        records.append(record)
    return records


def write_local_records(path: Path | str, records: list[dict]) -> Path:
    """기록을 JSONL로 쓴다(한 줄에 기록 하나, Artifact는 model_dump(mode='json')). 쓴 경로를 돌려준다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({**record, "artifact": record["artifact"].model_dump(mode="json")}, ensure_ascii=False)
             for record in records]
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def read_local_records(path: Path | str) -> list[dict]:
    """write_local_records가 쓴 JSONL을 읽어 Artifact 객체를 되살린다. 빈 줄은 건너뛴다."""
    records = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["artifact"] = Artifact.model_validate(row["artifact"])
        records.append(row)
    return records


# ---------------------------------------------------------------- 5. OTLP 내보내기와 적재 전 확인

# Langfuse Cloud 기본 주소. LANGFUSE_HOST(또는 LANGFUSE_BASE_URL)가 비었을 때만 쓴다.
DEFAULT_LANGFUSE_HOST = "https://cloud.langfuse.com"
OTLP_TRACES_PATH = "/api/public/otel/v1/traces"
# 이 header가 있어야 v4 실시간 수집 경로를 탄다(근거 노트 R6). 탐침은 이 header를 보내 지연 없이 읽혔다(Q7).
INGESTION_VERSION_HEADER = {"x-langfuse-ingestion-version": "4"}
OTLP_SERVICE_NAME = "day05-synth"
EXPORT_BATCH_SIZE = 512
FLUSH_TIMEOUT_MS = 120_000


def otlp_target(settings: Settings) -> tuple[str, dict[str, str]]:
    """Langfuse OTLP 수집 주소와 header를 만든다. 키가 비면 키 이름만 대고 RuntimeError다.

    header에는 HTTP Basic 인증(공개키:비밀키의 base64)이 들어 있다. 돌려받은 header를 출력하거나 기록하지 않는다.
    """
    require(settings, "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    host = (settings.langfuse_host or DEFAULT_LANGFUSE_HOST).rstrip("/")
    credentials = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
    headers = {"Authorization": "Basic " + base64.b64encode(credentials).decode(), **INGESTION_VERSION_HEADER}
    return host + OTLP_TRACES_PATH, headers


class _PresetIds(IdGenerator):
    """다음 span의 trace id와 span id를 미리 정해 둔다. 결정적 id 그대로 보내기 위해서다."""

    def __init__(self) -> None:
        self.trace_id = 0
        self.span_id = 0

    def preset(self, trace_hex: str, span_hex: str) -> None:
        self.trace_id = int(trace_hex, 16)
        self.span_id = int(span_hex, 16)

    def generate_trace_id(self) -> int:
        return self.trace_id

    def generate_span_id(self) -> int:
        return self.span_id


class _CountingExporter(SpanExporter):
    """감싼 exporter의 결과를 센다. BatchSpanProcessor는 실패를 삼키므로 성공·실패 수를 따로 세야 알 수 있다."""

    def __init__(self, inner: SpanExporter) -> None:
        self.inner = inner
        self.exported = 0
        self.failed = 0
        self._lock = Lock()

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        result = self.inner.export(spans)
        with self._lock:
            if result is SpanExportResult.SUCCESS:
                self.exported += len(spans)
            else:
                self.failed += len(spans)
        return result

    def shutdown(self) -> None:
        self.inner.shutdown()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self.inner.force_flush(timeout_millis)


def _emit(tracer: Tracer, ids: _PresetIds, trace_id: str, span: SyntheticSpan) -> None:
    """SyntheticSpan 하나를 정한 id·부모·시각 그대로 연다. root는 빈 Context로 열어 바깥 span에 붙지 않게 한다."""
    ids.preset(trace_id, span.span_id)
    if span.parent_id is None:
        context = Context()
    else:
        parent = SpanContext(int(trace_id, 16), int(span.parent_id, 16), is_remote=False,
                             trace_flags=TraceFlags(TraceFlags.SAMPLED))
        context = set_span_in_context(NonRecordingSpan(parent))
    otel_span = tracer.start_span(span.name, context=context, start_time=span.start_ms * NS_PER_MS,
                                  attributes=span.attributes)
    otel_span.end(end_time=span.end_ms * NS_PER_MS)


def export_otlp(dressed: list[DressedEpisode], *, settings: Settings, environment: str,
                exporter: SpanExporter | None = None) -> dict[str, int]:
    """옷 입힌 Episode를 OTLP로 보낸다. 모델 호출 0회. {traces, observations, exported, failed}를 돌려준다.

    - exporter가 없으면 settings의 Langfuse 키로 OTLP HTTP exporter를 만든다(otlp_target). 키는 출력하지 않는다.
      시험은 exporter 자리에 메모리 exporter를 넣는다.
    - 이 함수 전용 TracerProvider를 만들고 전역 provider는 건드리지 않는다. BatchSpanProcessor로 묶어 보내고
      force_flush 뒤 shutdown한다. 대기열이 넘쳐 span이 버려지지 않게 대기열 크기를 보낼 span 수 이상으로 둔다.
    - environment와 다른 environment로 입힌 기록이 섞여 있으면 ValueError다(id가 environment에서 나온다).
    - 같은 id를 다시 보내면 Langfuse에 일시적으로 중복이 보일 수 있다(근거 노트 Q2, R4). 이 함수는 확인하지 않으므로
      적재 도구가 먼저 existing_root_count로 빈 environment인지 확인한다.
    """
    # 1단계: environment 이름과 기록이 맞는지 확인한다.
    validate_environment(environment)
    others = sorted({episode.environment for episode in dressed} - {environment})
    if others:
        raise ValueError(f"environment {environment}로 보낼 기록에 다른 environment로 입힌 Episode가 있습니다: {others}")

    # 2단계: exporter와 전용 TracerProvider를 준비한다.
    target = exporter
    if target is None:
        endpoint, headers = otlp_target(settings)
        target = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    counter = _CountingExporter(target)
    total = sum(len(episode.spans) for episode in dressed)
    ids = _PresetIds()
    provider = TracerProvider(sampler=ALWAYS_ON, resource=Resource.create({"service.name": OTLP_SERVICE_NAME}),
                              id_generator=ids, shutdown_on_exit=False)
    provider.add_span_processor(BatchSpanProcessor(counter, max_queue_size=max(total, EXPORT_BATCH_SIZE),
                                                   max_export_batch_size=EXPORT_BATCH_SIZE))
    tracer = provider.get_tracer(GENERATOR)

    # 3단계: Episode마다 span을 정한 id·시각으로 열고 닫는다. 끝난 span은 processor가 묶어 보낸다.
    for episode in dressed:
        for span in episode.spans:
            _emit(tracer, ids, episode.trace_id, span)

    # 4단계: 남은 묶음을 보내고 provider를 닫는다. 보낸 수와 거절된 수를 그대로 돌려준다.
    provider.force_flush(FLUSH_TIMEOUT_MS)
    provider.shutdown()
    return {"traces": len(dressed), "observations": total, "exported": counter.exported, "failed": counter.failed}


def existing_root_count(client, environment: str, *, cap: int = STORY_DAYS * EPISODES_PER_DAY) -> int:
    """environment에 이미 있는 root observation(episode) 수. 0이 아니면 적재 도구는 다시 보내지 않는다.

    client는 Langfuse 클라이언트다(시험은 가짜를 넘긴다). cap에서 세기를 멈춘다. 집계가 비동기라 방금 보낸 것은
    아직 안 세일 수 있다(online.count_observations).
    """
    return count_observations(client, root_filter(validate_environment(environment)), cap=cap)


def estimate_observations(dressed: list[DressedEpisode]) -> dict:
    """보낼 trace·observation 수와 유형별 개수. Hobby 요금제는 trace와 observation을 각각 1 unit으로 센다.

    {traces, observations, units(traces + observations), by_type{agent, generation, tool, span}}를 돌려준다.
    점수·Judge 평가가 만드는 unit은 들어 있지 않다.
    """
    by_type = Counter(span.attributes["langfuse.observation.type"] for episode in dressed for span in episode.spans)
    observations = sum(by_type.values())
    return {"traces": len(dressed), "observations": observations, "units": len(dressed) + observations,
            "by_type": dict(by_type)}
