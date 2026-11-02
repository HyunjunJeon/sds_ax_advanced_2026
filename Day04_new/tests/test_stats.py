import pytest

from cap_lab.stats import decide, noise_band, paired_bootstrap_diff, wilson_ci


def res(diff, lo, hi):
    return {"diff": diff, "lo": lo, "hi": hi, "n_cases": 5}


def test_wilson_ci_known_value():
    lo, hi = wilson_ci(8, 10)
    assert lo == pytest.approx(0.490, abs=0.001)
    assert hi == pytest.approx(0.943, abs=0.001)


def test_wilson_ci_no_data_is_none():
    assert wilson_ci(0, 0) is None


def test_bootstrap_same_seed_same_result():
    a = {"c1": [0, 0, 1], "c2": [0, 0, 0], "c3": [1, 0, 0]}
    b = {"c1": [1, 1, 1], "c2": [1, 0, 1], "c3": [1, 1, 0]}
    assert paired_bootstrap_diff(a, b, iters=500, seed=3) == paired_bootstrap_diff(a, b, iters=500, seed=3)


def test_bootstrap_diff_value_and_bools():
    a = {"c1": [False, False], "c2": [True, False]}
    b = {"c1": [True, True], "c2": [True, True]}
    out = paired_bootstrap_diff(a, b, iters=200)
    assert out["diff"] == pytest.approx(0.75)
    assert out["n_cases"] == 2
    assert out["lo"] <= out["diff"] <= out["hi"]


def test_bootstrap_uses_only_shared_cases():
    a = {"c1": [0.0], "only_a": [1.0]}
    b = {"c1": [1.0], "only_b": [0.0]}
    out = paired_bootstrap_diff(a, b, iters=100)
    assert out["n_cases"] == 1
    assert out["diff"] == 1.0


def test_bootstrap_no_shared_case_is_none():
    assert paired_bootstrap_diff({"x": [1]}, {"y": [1]}, iters=10) is None


def test_identical_aa_gives_zero_diff_and_noise():
    a = {"c1": [1, 0], "c2": [0, 0], "c3": [1, 1]}
    assert paired_bootstrap_diff(a, a, iters=200)["diff"] == 0
    assert noise_band(a, a, iters=200) == 0


def test_noise_band_none_without_shared_cases():
    assert noise_band({"x": [1]}, {"y": [1]}, iters=10) is None


def test_decide_improved():
    out = decide(res(0.3, 0.1, 0.5), {"g": res(-0.01, -0.05, 0.03)}, {"g": 0.05})
    assert out["verdict"] == "개선"
    assert out["reasons"] and all(isinstance(r, str) for r in out["reasons"])


def test_decide_tradeoff_when_guard_drops_beyond_noise():
    out = decide(res(0.3, 0.1, 0.5), {"g": res(-0.2, -0.3, -0.1)}, {"g": 0.05})
    assert out["verdict"] == "교환"


def test_decide_lower_is_better_guard_increase_is_worse():
    guards = {"cost": res(0.2, 0.1, 0.3)}
    target = res(0.3, 0.1, 0.5)
    assert decide(target, guards, {"cost": 0.05}, lower_is_better=frozenset({"cost"}))["verdict"] == "교환"
    assert decide(target, guards, {"cost": 0.05})["verdict"] == "개선"


def test_decide_lower_is_better_decrease_is_fine():
    out = decide(
        res(0.3, 0.1, 0.5), {"cost": res(-0.2, -0.3, -0.1)}, {"cost": 0.05},
        lower_is_better=frozenset({"cost"}),
    )
    assert out["verdict"] == "개선"


def test_decide_regression():
    assert decide(res(-0.3, -0.5, -0.1), {}, {})["verdict"] == "회귀"


def test_decide_unconfirmed_when_interval_spans_zero():
    assert decide(res(0.1, -0.1, 0.3), {}, {})["verdict"] == "개선 확인 불가"


def test_decide_no_data_target_none():
    assert decide(None, {}, {})["verdict"] == "판정 불가: 데이터 부족"


def test_decide_no_data_when_noise_band_missing():
    out = decide(res(0.3, 0.1, 0.5), {"g": res(0, -0.1, 0.1)}, {"g": None})
    assert out["verdict"] == "판정 불가: 데이터 부족"
