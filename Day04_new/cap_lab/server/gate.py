"""H1 완료 기준 판정 게이트. 완료 기준 하나에 Decision API의 Score 질문 testability 하나를 묻는다.

점수는 단계별 확률로 낸 기댓값이다. 척도는 Decision API가 정하므로 [0, 1]로 가정하지 않는다.
문턱값과 비교할 때는 < 또는 >=만 쓰고 ==는 쓰지 않는다. 기본 문턱값 0.5는 라벨로 재지 않은 자리값이다.

가짜 판정기: DAY04_ALLOW_FAKE_DECIDER=1이면 DAY04_FAKE_DECIDER의 값으로 HTTP 없이 답한다.
'{"testability": 0.9}'처럼 질문 이름별 점수 JSON이면 그 점수를, error이면 판정 실패를 흉내 낸다.
오프라인 시험과 키 없는 노트북 시연용이다. 측정 실행에서는 켜지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import TypeAdapter, ValidationError

from cap_lab.decisions import (
    DecisionBackend,
    DecisionError,
    Judgment,
    Question,
    Score,
    Verdict,
)

TESTABILITY = Score(
    name="testability",
    instructions=(
        "주어진 완료 기준을 실행 결과(테스트 통과 여부, 명령 출력, 생성된 파일의 내용 등)를 보고 "
        "참 또는 거짓으로 판정할 수 있는지 평가하라."
    ),
    levels=["판정할 수 없다(모호한 표현)", "일부만 판정할 수 있다", "실행 결과로 참/거짓을 판정할 수 있다"],
)

FAKE_SWITCH = "DAY04_ALLOW_FAKE_DECIDER"
FAKE_SCRIPT = "DAY04_FAKE_DECIDER"
_FAKE_SCORES = TypeAdapter(dict[str, float])


class GateUnavailable(RuntimeError):
    """판정기를 만들 수 없거나 판정이 실패했다. 게이트는 이때 아무것도 기록하지 않는다(fail-closed)."""


@dataclass(frozen=True)
class GateDecision:
    score: float
    threshold: float

    @property
    def passed(self) -> bool:
        # 기댓값은 소수가 흔하다. 같은 값인지가 아니라 문턱값 이상인지를 본다.
        return self.score >= self.threshold


class TestabilityGate:
    """완료 기준을 판정하고 문턱값과 비교한다. 판정기의 어떤 실패도 통과로 바꾸지 않는다."""

    def __init__(self, decider: DecisionBackend, threshold: float) -> None:
        self.decider = decider
        self.threshold = threshold
        # MRTR에서는 라운드마다 resolver가 다시 실행된다. 같은 문장을 다시 판정하면 비용이 늘고,
        # 두 번째 점수가 문턱값을 넘으면 사용자가 준 답이 버려진다. 성공한 판정만 저장한다.
        self._scores: dict[str, float] = {}

    def check(self, criterion: str) -> GateDecision:
        if criterion not in self._scores:
            self._scores[criterion] = self._judge(criterion)
        return GateDecision(self._scores[criterion], self.threshold)

    def _judge(self, criterion: str) -> float:
        try:
            verdict = self.decider.judge(criterion, [TESTABILITY]).verdicts[TESTABILITY.name]
        except DecisionError as error:
            # DecisionError 메시지는 공급자 이름과 HTTP 상태만 담는다(cap_lab/decisions.py). 키와 state는 없다.
            raise GateUnavailable(f"완료 기준을 판정하지 못했습니다({error}).") from error
        except Exception as error:
            # 그 밖의 어떤 실패도 통과로 바꾸지 않는다. 내용을 모르는 메시지라 예외 종류만 전한다.
            raise GateUnavailable(f"완료 기준을 판정하지 못했습니다({type(error).__name__}).") from error
        if verdict.score is None:
            raise GateUnavailable("판정기가 testability 점수를 주지 않았습니다(refused).")
        return verdict.score


@dataclass(frozen=True)
class FakeDecider:
    """가짜 판정기(DecisionBackend). scores에 있는 Score 질문은 그 점수로 답하고 없는 질문은 거절한다.

    error가 있으면 judge가 그 오류를 낸다.
    """

    scores: Mapping[str, float] = field(default_factory=dict)
    error: DecisionError | None = None
    name: ClassVar[str] = "fake"

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        if self.error is not None:
            raise self.error
        verdicts = {
            q.name: Verdict(q.name, q.kind, score=self.scores[q.name])
            if q.name in self.scores
            else Verdict(q.name, q.kind, refused=True)
            for q in questions
        }
        return Judgment(verdicts, self.name, "fake-decider")


def fake_decider_from_env(environ: Mapping[str, str]) -> FakeDecider | None:
    """DAY04_ALLOW_FAKE_DECIDER=1일 때만 가짜 판정기를 만든다. 스위치가 꺼져 있으면 None이다.

    DAY04_FAKE_DECIDER가 점수 JSON도 error도 아니면 ValueError를 낸다.
    """
    if environ.get(FAKE_SWITCH) != "1":
        return None
    script = environ.get(FAKE_SCRIPT, "")
    if script.strip() == "error":
        return FakeDecider(error=DecisionError("fake: 가짜 판정기가 판정 실패를 흉내 냈습니다."))
    try:
        return FakeDecider(_FAKE_SCORES.validate_json(script))
    except ValidationError as error:
        raise ValueError(
            f"{FAKE_SCRIPT}는 '{{\"testability\": 0.9}}' 같은 점수 JSON이거나 error여야 합니다."
        ) from error
