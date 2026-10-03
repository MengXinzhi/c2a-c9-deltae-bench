"""End-to-end protocol tests.

These check the *design claims*, not the plumbing: that the ceiling predictor
saturates, that the no-self-knowledge control does not, that surface disguise
damages a stereotype-driven reader, and that the whole thing is deterministic.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deltabench.runner import Config, run_one  # noqa: E402


def _cfg():
    return Config(seed=1234, per_cell_probe=8, per_cell_eval=6, per_cell_truth=40)


def test_full_protocol_runs_and_produces_finite_metrics():
    res = run_one("SolverA", _cfg())
    assert set(res["blocks"]) == {"B1_cold", "B3_warm", "B4_stroop", "B6_unseen_skill"}
    for block in res["blocks"].values():
        assert block["n_items"] > 0
        for name, m in block["predictors"].items():
            for key in ("delta_e", "ece", "brier", "auroc"):
                v = m[key]
                assert not math.isnan(v), f"{name}.{key} is NaN"
            assert 0.0 <= m["ece"] <= 1.0
            assert 0.0 <= m["brier"] <= 1.0
    assert not math.isnan(res["memory_expression_gap"]["expression_gap_brier"])
    assert res["n_ledger"] > 0


def test_determinism_same_seed_same_result():
    a = run_one("SolverB", _cfg())
    b = run_one("SolverB", _cfg())
    assert a["ability"] == b["ability"]
    assert a["blocks"]["B1_cold"]["predictors"] == b["blocks"]["B1_cold"]["predictors"]


def test_ceiling_predictor_saturates_and_control_does_not():
    res = run_one("SolverC", _cfg())
    warm = res["blocks"]["B3_warm"]["predictors"]
    ceiling = warm["P9 SelfOracle (ceiling)"]
    no_self = warm["P3 PopDifficulty (no self)"]
    assert ceiling["auroc"] > 0.99
    assert abs(ceiling["delta_e"]) < 0.1
    # knowing normative difficulty is not the same as knowing yourself
    assert no_self["auroc"] < 0.9


def test_null_and_baserate_are_calibrated_but_uninformative():
    res = run_one("SolverC", _cfg())
    warm = res["blocks"]["B3_warm"]["predictors"]
    null = warm["P0 Null (always 0.5)"]
    assert null["auroc"] == 0.5
    assert abs(null["brier"] - 0.25) < 0.06
    assert abs(null["delta_e"] - (0.5 - null["accuracy"])) < 1e-9


def test_surface_disguise_hurts_the_cue_reader_more_than_the_self_model():
    res = run_one("SolverA", _cfg())
    d = res["surface_disguise"]
    cue = d["P2 CueOnly (stereotype)"]
    model = d["P7 SelfModelOnly"]
    assert cue["delta_auroc"] < 0.0, "cue reader should lose discrimination"
    assert model["delta_auroc"] > cue["delta_auroc"]


def test_self_observation_beats_leaning_on_world_priors():
    """SMA is only interpretable against the sampling noise floor.

    With a finite self-observation budget, per-cell accuracy can never be
    measured exactly, so we assert two things: (a) an empirical self-model is
    within a small margin of the irreducible floor, and (b) it still beats a
    self-model that ignores its own history and falls back on the normative
    difficulty prior.
    """
    res = run_one("SolverB", _cfg())
    sweep = res["self_model_quality_sweep"]
    floor = res["sma_noise_floor"]
    self_observed = sweep["quality=1.0"]["sma_holdout"]
    prior_only = sweep["quality=0.0"]["sma_holdout"]
    assert self_observed <= floor + 0.08, (self_observed, floor)
    assert self_observed < prior_only, (self_observed, prior_only)


def test_control_utility_scale_is_anchored():
    res = run_one("SolverD", _cfg())
    ctrl = res["control"]
    assert abs(ctrl["oracle_ceiling"]["control_utility"] - 1.0) < 1e-6
    assert 0.0 <= ctrl["warm_blend"]["control_utility"] <= 1.5


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} protocol tests passed")
