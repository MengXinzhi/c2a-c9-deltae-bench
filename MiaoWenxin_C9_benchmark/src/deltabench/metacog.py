"""Metacognitive predictors.

A predictor answers one question: *before* attempting the item, what is the
probability that I will get it right?

Predictors are deliberately orthogonal to ability solvers.  The same solved
outcome can be paired with a predictor that knows nothing about it (``Null``), a
predictor that only reads surface cues (``CueOnly``), a predictor that knows the
normative difficulty of the item but not its own idiosyncratic profile
(``PopulationDifficulty``), or a predictor with genuine access to its own
internal correctness signal (``NoisySelf``).  The benchmark's whole point is to
separate those cases empirically.

``SelfOracle`` and ``NoisySelf`` are the only predictors that may see ``y``.
They exist to fix the ceiling and to model a realistic partial signal; they are
never used to score a real submission.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .items import Item, FAMILIES, LEVELS, _population_difficulty
from . import metrics as M


@dataclass
class RunContext:
    """Everything a predictor is allowed to condition on."""

    base_rate: float = 0.5
    ledger: list = field(default_factory=list)          # list[(Item, bool)]
    self_model: dict = field(default_factory=dict)      # (family, level) -> p
    cue_weights: list | None = None                     # frozen Block-1 cue model
    rng: random.Random = field(default_factory=lambda: random.Random(0))


class MetaPredictor:
    name = "base"
    channel = "verbal"

    def predict(self, item: Item, ctx: RunContext, y: bool | None = None) -> float:
        raise NotImplementedError

    def run(self, items, ctx, outcomes=None) -> list[float]:
        if outcomes is None:
            outcomes = [None] * len(items)
        return [self.predict(it, ctx, y) for it, y in zip(items, outcomes)]


class NullPredictor(MetaPredictor):
    """Untouched prior: always 50%.  Scores a *perfect* ECE -- which is exactly
    why ECE alone must never be the headline metric."""

    name = "P0 Null (always 0.5)"

    def predict(self, item, ctx, y=None):
        return 0.5


class BaseRatePredictor(MetaPredictor):
    """Knows the marginal accuracy of its own run, nothing else.  Zero
    resolution: the canonical 'beats ECE, fails Brier' degenerate strategy."""

    name = "P1 BaseRate (marginal)"

    def __init__(self, base_rate: float | None = None):
        self.fixed = base_rate

    def predict(self, item, ctx, y=None):
        return M.clip(self.fixed if self.fixed is not None else ctx.base_rate)


class CueOnlyPredictor(MetaPredictor):
    """Difficulty stereotyping: a logistic model over surface text features only.

    Fit on the capability probe, then *frozen*.  Its weakness map is derived from
    how things look, not from how the model itself performs.
    """

    name = "P2 CueOnly (stereotype)"

    def __init__(self, weights: list | None = None):
        self.weights = weights

    def predict(self, item, ctx, y=None):
        w = self.weights if self.weights is not None else ctx.cue_weights
        if w is None:
            return 0.5
        return M.clip(M.logistic_predict(w, M.cue_features(item)))


class PopulationDifficultyPredictor(MetaPredictor):
    """Knows the normative difficulty of the item -- and only that.

    This is the critical control.  It has excellent information about how hard
    the item is *in general*, and none about whether *this* system fails on it.
    Any benchmark that lets this predictor win is measuring difficulty
    perception, not metacognition.
    """

    name = "P3 PopDifficulty (no self)"

    def predict(self, item, ctx, y=None):
        return M.clip(1.0 - item.population_difficulty)


class SelfOraclePredictor(MetaPredictor):
    """Ceiling: perfect access to its own correctness.  Not a submission."""

    name = "P9 SelfOracle (ceiling)"

    def predict(self, item, ctx, y=None):
        if y is None:
            return 0.5
        return 0.97 if y else 0.03


class NoisySelfPredictor(MetaPredictor):
    """Realistic partial signal: an internal 'this feels right' reading, plus
    over-confidence bias, plus noise.

    ``gain`` controls resolution (how sharply the signal separates correct from
    incorrect), ``bias`` shifts the whole distribution toward over-confidence,
    ``sigma`` adds trial-level noise.
    """

    def __init__(self, gain: float, bias: float, sigma: float, seed: int = 7,
                 name: str | None = None):
        self.gain = gain
        self.bias = bias
        self.sigma = sigma
        self.rng = random.Random(seed)
        self.name = name or f"NoisySelf(g={gain},b={bias},s={sigma})"

    def predict(self, item, ctx, y=None):
        if y is None:
            return 0.5
        z = self.gain * (1.0 if y else -1.0) + self.bias + self.rng.gauss(0.0, self.sigma)
        return M.clip(M.sigmoid(z))


class BiasCorrected(MetaPredictor):
    """A calibration fix that leaves resolution untouched -- the 'negative
    control' for the metric suite.

    The shift is estimated on the agent's own probe block (a legitimate
    self-calibration step for a real deployment) and then frozen.  It drives
    DeltaE and ECE toward zero, which is exactly the failure mode a benchmark
    must be able to *see through*: AUROC, cue-residual AUROC, Brier and the
    control utility must all be unchanged.  Any suite in which ECE alone decides
    the ranking would be fooled by this predictor.
    """

    def __init__(self, inner: MetaPredictor, shift: float,
                 name: str = "P6 BiasCorrected(inner)"):
        self.inner = inner
        self.shift = shift
        self.name = name

    def predict(self, item, ctx, y=None):
        return M.clip(self.inner.predict(item, ctx, y) - self.shift)


class SelfModelPredictor(MetaPredictor):
    """Predicts from an *authored* per-cell self-model, falling back to the
    surface-cue prior for cells the self-model does not cover."""

    name = "P8 SelfModel (authored)"

    def __init__(self, self_model: dict, cue_weights: list | None = None):
        self.self_model = self_model
        self.cue_weights = cue_weights

    def predict(self, item, ctx, y=None):
        key = (item.family, item.level)
        if key in self.self_model:
            return M.clip(self.self_model[key])
        w = self.cue_weights if self.cue_weights is not None else ctx.cue_weights
        if w is not None:
            return M.clip(M.logistic_predict(w, M.cue_features(item)))
        return M.clip(ctx.base_rate)


class BehavioralChannel(MetaPredictor):
    """The 'place a bet' channel, modelled as a de-biased, compressed read-out of
    the verbal channel.

    Modelling assumption (documented, not hidden): verbalised confidence is
    systematically over-stated and over-dispersed relative to what a wagering
    decision implies.  ``gain`` < 1 compresses, ``bias`` < 0 de-biases.  When a
    real model is plugged in, both channels are *measured* directly and this
    class is not used.
    """

    def __init__(self, inner: MetaPredictor, gain: float = 0.85, bias: float = -0.90):
        self.inner = inner
        self.gain = gain
        self.bias = bias
        self.name = f"behavioral[{inner.name}]"

    def predict(self, item, ctx, y=None):
        p = self.inner.predict(item, ctx, y)
        return M.clip(M.sigmoid(self.gain * M.logit(p) + self.bias))


# ------------------------------------------------------------ self-model authoring

def author_self_model(
    ledger: list,
    cells: list[tuple[str, int]],
    quality: float,
    min_n: int = 2,
) -> dict:
    """Turn a raw outcome ledger into an explicit per-cell self-model.

    ``ledger`` is the un-aggregated list of (Item, correct).  Nothing else is
    used: this is the model's *own* observation history and nothing more.
    ``quality`` blends pure self-observation (1.0) with the objective difficulty
    prior (0.0); the two settings are reported separately because leaning on
    world priors when predicting your own behaviour is a real failure mode.

    Held-out scoring means the caller must pass a *disjoint* cell set for
    evaluation, so the returned numbers cannot be memorised.
    """
    quality = max(0.0, min(1.0, quality))

    per_cell: dict[tuple[str, int], list[int]] = {}
    per_family: dict[str, list[int]] = {}
    all_outcomes: list[int] = []
    for item, correct in ledger:
        key = (item.family, item.level)
        per_cell.setdefault(key, []).append(int(correct))
        per_family.setdefault(item.family, []).append(int(correct))
        all_outcomes.append(int(correct))

    def smoothed(vals, prior, k=1.5):
        return (sum(vals) + k * prior) / (len(vals) + k)

    global_mean = (sum(all_outcomes) + 1.0) / (len(all_outcomes) + 2.0) if all_outcomes else 0.5

    model: dict[tuple[str, int], float] = {}
    for family, level in cells:
        prior = 1.0 - _population_difficulty(family, level)

        fam_vals = per_family.get(family, [])
        fam_est = smoothed(fam_vals, global_mean) if fam_vals else global_mean

        cell_vals = per_cell.get((family, level), [])
        if len(cell_vals) >= min_n:
            obs = smoothed(cell_vals, fam_est)
        else:
            # not enough direct evidence for this cell -> interpolate within the
            # family, which is the honest thing a self-observer can do.
            obs = fam_est

        model[(family, level)] = quality * obs + (1.0 - quality) * prior
    return model


def cells_holdout(ledger, rng, frac: float = 0.5, per_cell: int = 2) -> list[tuple[str, int]]:
    """Cells for which the ledger holds evidence -- scored on *new* items."""
    seen = sorted({(it.family, it.level) for it, _ in ledger})
    rng.shuffle(seen)
    k = max(1, int(len(seen) * frac))
    return seen[:k]


def cells_interp(ledger) -> list[tuple[str, int]]:
    """Levels *not* observed in the ledger, inside families that *were*."""
    seen_families = {it.family for it, _ in ledger}
    seen = {(it.family, it.level) for it, _ in ledger}
    out = []
    for f in sorted(seen_families):
        for lv in LEVELS:
            if (f, lv) not in seen:
                out.append((f, lv))
    return out


def cells_extrap(ledger) -> list[tuple[str, int]]:
    """Families never observed at all."""
    seen_families = {it.family for it, _ in ledger}
    return [(f, lv) for f in FAMILIES if f not in seen_families for lv in LEVELS]
