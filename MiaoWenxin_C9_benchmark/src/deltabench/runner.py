"""Protocol orchestration for DeltaE-Bench.

Six blocks, run per solver:

  B0  capability probe      -> the agent's raw outcome ledger (self-observation)
  B1  cold self-prediction  -> DeltaE_0 with no self-history at all
  B2  self-model authoring  -> score the *artifact* on held-out cells
  B3  warm self-prediction  -> DeltaE_1 once the self-model exists
  B4  surface-disguise probe-> does the self-model survive inverted cues?
  B5  budgeted control      -> does the self-model improve actual decisions?
  B6  unseen-skill probe    -> does the self-model generalise to a new family?

Everything is seeded; two runs with the same config produce byte-identical
output.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, asdict, field

from .items import FAMILIES, LEVELS, make_grid, make_stratified
from .solvers import PROFILES, SimulatedSolver
from .metacog import (
    RunContext, MetaPredictor, NullPredictor, BaseRatePredictor,
    CueOnlyPredictor, PopulationDifficultyPredictor, SelfOraclePredictor,
    NoisySelfPredictor, SelfModelPredictor, BehavioralChannel, BiasCorrected,
    author_self_model,
)
from . import metrics as M

PROBE_FAMILIES: tuple[str, ...] = FAMILIES[:-1]          # 5 families observed
HELD_FAMILY: str = FAMILIES[-1]                          # 1 family never observed
PROBE_LEVELS: tuple[int, ...] = (1, 3, 5)
INTERP_LEVELS: tuple[int, ...] = (2, 4)
PROBE_CELLS = [(f, lv) for f in PROBE_FAMILIES for lv in PROBE_LEVELS]
ALL_CELLS = [(f, lv) for f in FAMILIES for lv in LEVELS]


@dataclass
class Config:
    seed: int = 20261231
    per_cell_probe: int = 8      # observations the agent gets of itself
    per_cell_eval: int = 6       # items per prediction block
    per_cell_truth: int = 40     # large held-out sample -> low-noise competence estimate
    budget_frac: float = 0.25
    sm_qualities: tuple[float, ...] = (1.0, 0.5, 0.0)  # 1.0=self-observed, 0.0=prior-only
    # Intrinsic self-signal.  Tuned so that the *cold* predictor lands in the
    # AUROC 0.70-0.80 band that black-box confidence elicitation actually
    # achieves on frontier models, rather than the ~1.0 an oracle would give.
    inner_gain: float = 0.45
    inner_bias: float = 0.90        # over-confidence, as consistently reported
    inner_sigma: float = 0.90
    blend_weights: tuple[float, ...] = (0.25, 0.5, 0.75)


def competence_estimate(truth_out, alternating: bool = False):
    """Per-cell accuracy from a large held-out run of the solver.

    Returns ``(cells, noise_floor)``.  ``noise_floor`` is the mean absolute
    difference between two *disjoint halves* of the same sample -- i.e. the MAE
    any perfect estimator would still incur because per-cell accuracy can only
    ever be measured through a finite number of trials.  Without this number an
    SMA figure is uninterpretable: a five-point gap may be entirely sampling
    noise.
    """
    buckets: dict = {}
    for item, _ans, ok in truth_out:
        buckets.setdefault((item.family, item.level), []).append(int(ok))

    cells = {k: sum(v) / len(v) for k, v in buckets.items()}
    half_a, half_b = {}, {}
    for k, v in buckets.items():
        a, b = v[0::2], v[1::2]
        if a and b:
            half_a[k] = sum(a) / len(a)
            half_b[k] = sum(b) / len(b)
    floor = M.sma(half_a, half_b) if half_a else float("nan")
    return cells, floor


def _sma_over(model: dict, truth: dict, cells) -> float:
    sub_model = {k: model[k] for k in cells if k in model}
    sub_truth = {k: truth[k] for k in cells if k in truth}
    return M.sma(sub_model, sub_truth)


def _fit_debias(probs, labels, target_rate, lo: float = -6.0, hi: float = 6.0,
                iters: int = 60) -> float:
    """Find a logit shift ``b`` so that sigmoid(logit(p) + b) has mean
    ``target_rate``.  Estimated on the probe block only, then frozen."""
    logits = [M.logit(p) for p in probs]

    def rate(b):
        return M.mean([M.sigmoid(z + b) for z in logits])

    if rate(lo) > target_rate:
        return lo
    if rate(hi) < target_rate:
        return hi
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if rate(mid) < target_rate:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass
class BlockResult:
    name: str
    n_items: int
    predictors: dict = field(default_factory=dict)


def _score_block(name, items, outcomes, probs_by_predictor, w_cue) -> BlockResult:
    labels = [int(c) for _, _, c in outcomes]
    out = {}
    for pname, probs in probs_by_predictor.items():
        br = M.brier(probs, labels)
        mur = M.murphy(probs, labels)
        out[pname] = {
            "delta_e": M.delta_e(probs, labels),
            "abs_delta_e": abs(M.delta_e(probs, labels)),
            "ece": M.ece(probs, labels),
            "brier": br,
            "auroc": M.auroc(probs, labels),
            "cue_residual_auroc": (
                M.cue_residual_auroc(w_cue, items, labels, probs)
                if w_cue is not None else float("nan")
            ),
            "murphy_reliability": mur["reliability"],
            "murphy_resolution": mur["resolution"],
            "accuracy": M.mean(labels),
            "mean_confidence": M.mean(probs),
        }
    return BlockResult(name=name, n_items=len(items), predictors=out)


def _budget_utility(items, outcomes, probs, budget_frac, seed):
    """Select a budget-limited subset; return accuracy under three strategies."""
    labels = [int(c) for _, _, c in outcomes]
    n = len(labels)
    k = max(1, int(round(budget_frac * n)))
    order_model = sorted(range(n), key=lambda i: -probs[i])[:k]
    order_oracle = sorted(range(n), key=lambda i: (-labels[i], -probs[i]))[:k]
    rng = random.Random(seed)
    order_rand = rng.sample(range(n), k)

    def acc(idx):
        return sum(labels[i] for i in idx) / len(idx)

    a_model, a_oracle, a_rand = acc(order_model), acc(order_oracle), acc(order_rand)
    denom = a_oracle - a_rand
    cu = (a_model - a_rand) / denom if abs(denom) > 1e-9 else float("nan")
    return {
        "budget": k,
        "pool": n,
        "acc_model": a_model,
        "acc_oracle": a_oracle,
        "acc_random": a_rand,
        "control_utility": cu,
    }


def run_one(solver_key: str, cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    srand = cfg.seed + sum(ord(c) for c in solver_key)

    rng = random.Random(cfg.seed)
    probe_items = make_stratified(rng, cfg.per_cell_probe, PROBE_CELLS, prefix="B0-")
    cold_items = make_stratified(rng, cfg.per_cell_eval, PROBE_CELLS, prefix="B1-")
    warm_items = make_stratified(rng, cfg.per_cell_eval, PROBE_CELLS, prefix="B3-")
    stroop_items = make_stratified(rng, cfg.per_cell_eval, PROBE_CELLS,
                                   mode="stroop", prefix="B4-")
    ctrl_items = make_stratified(rng, cfg.per_cell_eval, PROBE_CELLS, prefix="B5-")
    extrap_items = make_stratified(rng, cfg.per_cell_eval,
                                   [(HELD_FAMILY, lv) for lv in LEVELS], prefix="B6-")
    truth_items = make_grid(rng, cfg.per_cell_truth, prefix="T-")

    solver = SimulatedSolver(PROFILES[solver_key], seed=srand)
    probe_out = solver.run(probe_items)
    ledger = [(it, ok) for it, _, ok in probe_out]

    truth_out = solver.run(truth_items)
    truth_cells, sma_noise_floor = competence_estimate(truth_out)

    base_rate = M.mean([int(ok) for _, _, ok in probe_out])
    w_cue = M.fit_cue_model([it for it, _ in ledger], [int(ok) for _, ok in ledger])
    ctx = RunContext(base_rate=base_rate, ledger=ledger, rng=random.Random(srand + 1))

    # ---- self-models (two authoring policies) -----------------------------
    self_models = {
        f"quality={q:.1f}": author_self_model(ledger, ALL_CELLS, quality=q)
        for q in cfg.sm_qualities
    }
    sm_scores = {}
    interp_cells = [(f, lv) for f in PROBE_FAMILIES for lv in INTERP_LEVELS]
    extrap_cells = [(HELD_FAMILY, lv) for lv in LEVELS]
    for label, model in self_models.items():
        extrap_common = [k for k in extrap_cells if k in model and k in truth_cells]
        sm_scores[label] = {
            "sma_holdout": _sma_over(model, truth_cells, PROBE_CELLS),
            "sma_interp": _sma_over(model, truth_cells, interp_cells),
            "sma_extrap": _sma_over(model, truth_cells, extrap_cells),
            "sma_noise_floor": sma_noise_floor,
            # rank agreement on the *unseen* family's own difficulty ladder
            "spearman_extrap_ladder": M.spearman(
                [model[k] for k in extrap_common],
                [truth_cells[k] for k in extrap_common],
            ),
        }
    main_sm = self_models[f"quality={cfg.sm_qualities[0]:.1f}"]

    # ---- predictors -------------------------------------------------------
    inner = NoisySelfPredictor(cfg.inner_gain, cfg.inner_bias, cfg.inner_sigma,
                               seed=srand + 2, name="P4 InnerSignal(cold)")
    # A second, independent instance estimates the agent's own bias on the probe
    # block; the shift is frozen so it cannot be fitted on the evaluation data.
    inner_probe = NoisySelfPredictor(cfg.inner_gain, cfg.inner_bias, cfg.inner_sigma,
                                     seed=srand + 11)
    probe_labels = [int(ok) for _, _, ok in probe_out]
    inner_probe_p = inner_probe.run(probe_items, ctx, probe_labels)
    shift = M.mean(inner_probe_p) - base_rate
    bias_corrected = BiasCorrected(inner, shift)

    model_only = SelfModelPredictor(main_sm, cue_weights=w_cue)
    model_only.name = "P7 SelfModelOnly"
    blends = {
        f"P5 KSTAR-blend(w={w:.2f})": _Blend(inner, model_only, w, cue_weights=w_cue)
        for w in cfg.blend_weights
    }
    warm_weight = cfg.blend_weights[len(cfg.blend_weights) // 2]
    warm_agent = blends[f"P5 KSTAR-blend(w={warm_weight:.2f})"]

    generic = {
        "P0 Null (always 0.5)": NullPredictor(),
        "P1 BaseRate (marginal)": BaseRatePredictor(),
        "P2 CueOnly (stereotype)": CueOnlyPredictor(weights=w_cue),
        "P3 PopDifficulty (no self)": PopulationDifficultyPredictor(),
        "P6 BiasCorrected(inner)": bias_corrected,
        "P9 SelfOracle (ceiling)": SelfOraclePredictor(),
    }

    def eval_set(items, with_self_model: bool):
        """Cold blocks must not contain a predictor that needs the self-model."""
        outs = solver.run(items)
        labels = [int(ok) for _, _, ok in outs]
        preds = dict(generic)
        preds["P4 InnerSignal(cold)"] = inner
        if with_self_model:
            preds.update(blends)
            preds["P7 SelfModelOnly"] = model_only
        probs = {nm: p.run(items, ctx, labels) for nm, p in preds.items()}
        return outs, probs

    cold_out, cold_probs = eval_set(cold_items, with_self_model=False)
    warm_out, warm_probs = eval_set(warm_items, with_self_model=True)
    stroop_out, stroop_probs = eval_set(stroop_items, with_self_model=True)
    extrap_out, extrap_probs = eval_set(extrap_items, with_self_model=True)

    blocks = [
        _score_block("B1_cold", cold_items, cold_out, cold_probs, w_cue),
        _score_block("B3_warm", warm_items, warm_out, warm_probs, w_cue),
        _score_block("B4_stroop", stroop_items, stroop_out, stroop_probs, w_cue),
        _score_block("B6_unseen_skill", extrap_items, extrap_out, extrap_probs, w_cue),
    ]

    # ---- behavioural channel (MEG) ---------------------------------------
    # The wagering channel is the verbal channel with a single de-bias term
    # estimated on the agent's own probe block and then frozen.  Nothing else
    # differs, so the residual gap measures how far the *stated* confidence is
    # displaced from the signal the agent can act on -- i.e. "knows more than it
    # says".  A real run measures both channels directly instead of modelling
    # this step; the assumption is stated in the task spec.
    beh_bias = _fit_debias(inner_probe_p, probe_labels, base_rate)
    beh = BehavioralChannel(inner, gain=1.0, bias=beh_bias)
    beh_probs = beh.run(warm_items, ctx, [int(ok) for _, _, ok in warm_out])
    warm_labels = [int(ok) for _, _, ok in warm_out]
    verbal_probs = warm_probs["P4 InnerSignal(cold)"]
    meg = {
        "debias_fitted": beh_bias,
        "brier_verbal": M.brier(verbal_probs, warm_labels),
        "brier_behavioral": M.brier(beh_probs, warm_labels),
        "delta_e_verbal": M.delta_e(verbal_probs, warm_labels),
        "delta_e_behavioral": M.delta_e(beh_probs, warm_labels),
        "auroc_verbal": M.auroc(verbal_probs, warm_labels),
        "auroc_behavioral": M.auroc(beh_probs, warm_labels),
    }
    meg["expression_gap_brier"] = meg["brier_verbal"] - meg["brier_behavioral"]

    # ---- budgeted control -------------------------------------------------
    ctrl_out = solver.run(ctrl_items)
    ctrl_labels = [int(ok) for _, _, ok in ctrl_out]
    control = {}
    for label, pred in (("cold_inner", inner), ("warm_blend", warm_agent),
                        ("self_model_only", model_only)):
        probs = pred.run(ctrl_items, ctx, ctrl_labels)
        control[label] = _budget_utility(ctrl_items, ctrl_out, probs,
                                         cfg.budget_frac, srand + 5)
    # ceiling for calibration of the CU scale
    oracle_probs = [float(l) for l in ctrl_labels]
    control["oracle_ceiling"] = _budget_utility(ctrl_items, ctrl_out, oracle_probs,
                                                cfg.budget_frac, srand + 5)

    # ---- ability profile --------------------------------------------------
    ability = {
        "overall_accuracy": base_rate,
        "per_family": {
            f: M.mean([int(ok) for it, _, ok in probe_out if it.family == f])
            for f in PROBE_FAMILIES
        },
        "per_family_held_out": M.mean([int(ok) for it, _, ok in truth_out
                                       if it.family == HELD_FAMILY]),
    }

    # ---- surface-disguise degradation ------------------------------------
    warm_p = blocks[1].predictors
    stroop_p = blocks[2].predictors
    degradation = {}
    for nm in warm_p:
        if nm in stroop_p:
            degradation[nm] = {
                "delta_e_normal": warm_p[nm]["delta_e"],
                "delta_e_stroop": stroop_p[nm]["delta_e"],
                "delta_abs_ece": stroop_p[nm]["ece"] - warm_p[nm]["ece"],
                "delta_brier": stroop_p[nm]["brier"] - warm_p[nm]["brier"],
                "delta_auroc": stroop_p[nm]["auroc"] - warm_p[nm]["auroc"],
            }

    return {
        "solver": PROFILES[solver_key].name,
        "config": {k: (list(v) if isinstance(v, tuple) else v)
                   for k, v in asdict(cfg).items()},
        "ability": ability,
        "self_model_quality_sweep": sm_scores,
        "sma_noise_floor": sma_noise_floor,
        "self_model_cells": {f"{f}|L{lv}": p for (f, lv), p in sorted(main_sm.items())},
        "blocks": {b.name: {"n_items": b.n_items, "predictors": b.predictors}
                   for b in blocks},
        "surface_disguise": degradation,
        "memory_expression_gap": meg,
        "control": control,
        "n_ledger": len(ledger),
        "raw": {
            "warm": _raw_dump(warm_items, warm_out, warm_probs),
            "stroop": _raw_dump(stroop_items, stroop_out, stroop_probs),
        },
    }


def _raw_dump(items, outcomes, probs_by_predictor):
    """Minimal per-item record so figures can be regenerated from results.json."""
    return {
        "items": [
            {"iid": it.iid, "family": it.family, "level": it.level,
             "cue_salience": round(it.cue_salience, 4),
             "population_difficulty": round(it.population_difficulty, 4)}
            for it in items
        ],
        "labels": [int(ok) for _, _, ok in outcomes],
        "probs": {nm: [round(p, 6) for p in ps] for nm, ps in probs_by_predictor.items()},
    }


class _Blend(MetaPredictor):
    """Weighted logit-space blend of an intrinsic signal and the self-model.

    ``w = 0``  -> the agent's intrinsic read-out only (cold condition)
    ``w = 0.5``-> intrinsic signal plus the authored self-model (warm condition)
    ``w = 1``  -> the authored self-model only
    """

    def __init__(self, inner, model_pred, weight, cue_weights=None):
        self.inner = inner
        self.model_pred = model_pred
        self.weight = weight
        self.cue_weights = cue_weights
        self.name = f"blend(w={weight:.1f})"

    def predict(self, item, ctx, y=None):
        a = self.inner.predict(item, ctx, y)
        b = self.model_pred.predict(item, ctx, y)
        z = self.weight * M.logit(b) + (1.0 - self.weight) * M.logit(a)
        return M.clip(M.sigmoid(z))

    def run(self, items, ctx, outcomes=None):
        if outcomes is None:
            outcomes = [None] * len(items)
        return [self.predict(it, ctx, y) for it, y in zip(items, outcomes)]


def run_all(cfg: Config | None = None, solver_keys=None) -> dict:
    cfg = cfg or Config()
    keys = list(solver_keys or PROFILES.keys())
    return {
        "config": {k: (list(v) if isinstance(v, tuple) else v)
                   for k, v in asdict(cfg).items()},
        "models": {k: run_one(k, cfg) for k in keys},
    }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run the DeltaE-Bench reference protocol.")
    ap.add_argument("--out", default="results", help="output directory")
    ap.add_argument("--seed", type=int, default=Config.seed)
    ap.add_argument("--models", default="", help="comma-separated solver keys")
    args = ap.parse_args(argv)

    cfg = Config(seed=args.seed)
    keys = [k for k in args.models.split(",") if k] or None
    res = run_all(cfg, keys)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, default=str)
    print(f"wrote {os.path.join(args.out, 'results.json')}")
    print(f"{len(res['models'])} models x {len(res['models'][list(res['models'])[0]]['blocks'])} blocks")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
