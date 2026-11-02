"""측정 통계와 사전 등록된 판정 규칙. 표준 라이브러리만 쓰고 모든 함수는 결정적이다."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence

VERDICT_IMPROVED = "개선"
VERDICT_TRADEOFF = "교환"
VERDICT_REGRESSED = "회귀"
VERDICT_UNCONFIRMED = "개선 확인 불가"
VERDICT_NO_DATA = "판정 불가: 데이터 부족"

Values = Mapping[str, Sequence[float]]
BootstrapResult = dict[str, float | int]


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson 점수 구간. n이 0이면 숫자처럼 보이지 않도록 None을 돌려준다."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def paired_bootstrap_diff(
    a: Values, b: Values, *, iters: int = 10000, seed: int = 0
) -> BootstrapResult | None:
    """사례 단위 쌍체 부트스트랩. 통계량은 사례별 (b 평균 - a 평균)의 평균이다.

    a, b는 사례 id -> 반복별 값(bool은 0/1). 양쪽에 값이 있는 사례만 쓴다.
    반환: {diff, lo, hi, n_cases} (lo/hi는 95% 백분위 구간). 공유 사례가 없으면 None.
    """
    deltas = [
        sum(b[case]) / len(b[case]) - sum(a[case]) / len(a[case])
        for case in sorted(a.keys() & b.keys())
        if len(a[case]) > 0 and len(b[case]) > 0
    ]
    if not deltas:
        return None
    rng = random.Random(seed)
    n = len(deltas)
    stats = sorted(sum(rng.choices(deltas, k=n)) / n for _ in range(iters))
    lo_index = int(0.025 * (iters - 1))
    hi_index = int(math.ceil(0.975 * (iters - 1)))
    return {
        "diff": sum(deltas) / n,
        "lo": stats[lo_index],
        "hi": stats[hi_index],
        "n_cases": n,
    }


def noise_band(a1: Values, a2: Values, *, iters: int = 10000, seed: int = 0) -> float | None:
    """같은 구성을 두 번 돌린 A/A 쌍에서 우연만으로 생기는 차이의 폭."""
    result = paired_bootstrap_diff(a1, a2, iters=iters, seed=seed)
    if result is None:
        return None
    return max(abs(result["lo"]), abs(result["hi"]))


def _guard_is_worse(diff: float, band: float, lower_is_better: bool) -> bool:
    return diff > band if lower_is_better else diff < -band


def decide(
    target: BootstrapResult | None,
    guards: Mapping[str, BootstrapResult | None],
    guard_noise: Mapping[str, float | None],
    *,
    lower_is_better: frozenset[str] = frozenset(),
) -> dict[str, object]:
    """사전 등록된 판정 규칙. 반환: {"verdict": str, "reasons": list[str]}."""
    if target is None:
        return {"verdict": VERDICT_NO_DATA, "reasons": ["목표 지표의 비교 결과가 없습니다."]}
    if target["hi"] < 0:
        return {
            "verdict": VERDICT_REGRESSED,
            "reasons": [f"목표 지표 구간 상한 {target['hi']:.3f}이 0보다 작습니다."],
        }
    if target["lo"] <= 0:
        return {
            "verdict": VERDICT_UNCONFIRMED,
            "reasons": [f"목표 지표 구간 하한 {target['lo']:.3f}이 0 이하라 개선을 확인할 수 없습니다."],
        }

    missing = [
        name for name in guards if guards[name] is None or guard_noise.get(name) is None
    ]
    if missing:
        return {
            "verdict": VERDICT_NO_DATA,
            "reasons": [f"가드 지표 {name}의 비교 결과 또는 잡음 폭이 없습니다." for name in missing],
        }

    worse = []
    for name, result in guards.items():
        band = guard_noise[name]
        if _guard_is_worse(result["diff"], band, name in lower_is_better):
            worse.append(
                f"가드 지표 {name}이 나빠졌습니다: 차이 {result['diff']:+.3f}, 잡음 폭 {band:.3f}."
            )
    if worse:
        return {"verdict": VERDICT_TRADEOFF, "reasons": worse}
    return {
        "verdict": VERDICT_IMPROVED,
        "reasons": [f"목표 지표 구간 하한 {target['lo']:.3f}이 0보다 크고 가드 지표는 잡음 폭 안입니다."],
    }
