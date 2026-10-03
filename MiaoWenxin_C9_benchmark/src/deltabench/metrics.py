"""Scoring metrics for DeltaE-Bench.

Pure standard library -- no NumPy/SciPy -- so the benchmark reproduces on any
Python 3.10+ interpreter.

Metric set and why each is here
-------------------------------
``delta_e``        mean signed (predicted self-success - actual success).
                   The KSTAR DeltaE endpoint: 0 means the self-model is
                   unbiased, <0 means under-confident, >0 over-confident.
``ece``            binned |confidence - accuracy|.  Reported because it is
                   conventional, *not* because it is sufficient: a constant
                   predictor scores a perfect ECE while carrying no information.
``brier``          proper scoring rule.  Cant be gamed by a constant predictor.
``murphy``         Brier = reliability - resolution + uncertainty.  Separates
                   "are the numbers right" from "do the numbers separate".
``auroc``          does confidence rank own-correct above own-incorrect.
``cue_residual_auroc``  AUROC of confidence *after* removing what a
                   surface-cue-only model already explains.  This is the
                   headline discriminator between self-knowledge and difficulty
                   stereotyping.
``sma``            self-model accuracy: mean absolute error of an authored
                   per-cell self-model against held-out empirical accuracy.
``spearman``       rank agreement, used for domain-ordering ("know my own
                   relative strengths") questions.
"""

from __future__ import annotations

import math
import random

_EPS = 1e-6


def clip(p: float, lo: float = _EPS, hi: float = 1.0 - _EPS) -> float:
    return max(lo, min(hi, p))


def logit(p: float) -> float:
    p = clip(p)
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


# ---------------------------------------------------------------- calibration

def delta_e(probs, labels) -> float:
    """Mean signed calibration gap (KSTAR DeltaE).  >0 = over-confident."""
    probs, labels = list(probs), list(labels)
    if not probs:
        return float("nan")
    return sum(p - y for p, y in zip(probs, labels)) / len(probs)


def ece(probs, labels, bins: int = 15) -> float:
    probs, labels = list(probs), list(labels)
    if not probs:
        return float("nan")
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for p, y in zip(probs, labels):
        idx = min(bins - 1, int(clip(p, 0.0, 0.999999) * bins))
        buckets[idx].append((p, y))
    total = len(probs)
    err = 0.0
    for b in buckets:
        if not b:
            continue
        conf = sum(p for p, _ in b) / len(b)
        acc = sum(y for _, y in b) / len(b)
        err += (len(b) / total) * abs(conf - acc)
    return err


def brier(probs, labels) -> float:
    probs, labels = list(probs), list(labels)
    if not probs:
        return float("nan")
    return sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def murphy(probs, labels, bins: int = 15) -> dict:
    """Murphy decomposition: Brier = reliability - resolution + uncertainty."""
    probs, labels = list(probs), list(labels)
    n = len(probs)
    if n == 0:
        return {"reliability": float("nan"), "resolution": float("nan"),
                "uncertainty": float("nan"), "brier_reconstructed": float("nan")}
    base = sum(labels) / n
    uncertainty = base * (1.0 - base)

    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for p, y in zip(probs, labels):
        idx = min(bins - 1, int(clip(p, 0.0, 0.999999) * bins))
        buckets[idx].append((p, y))

    reliability = 0.0
    resolution = 0.0
    for b in buckets:
        if not b:
            continue
        w = len(b) / n
        conf = sum(p for p, _ in b) / len(b)
        acc = sum(y for _, y in b) / len(b)
        reliability += w * (conf - acc) ** 2
        resolution += w * (acc - base) ** 2
    return {
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "brier_reconstructed": reliability - resolution + uncertainty,
    }


# ------------------------------------------------------------------ ranking

def auroc(scores, labels) -> float:
    """Rank-based AUROC with average ranks for ties."""
    pairs = list(zip(scores, labels))
    n_pos = sum(1 for _, y in pairs if y == 1)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = sorted(range(len(pairs)), key=lambda i: pairs[i][0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and pairs[order[j + 1]][0] == pairs[order[i]][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    rank_sum_pos = sum(ranks[i] for i in range(len(pairs)) if pairs[i][1] == 1)
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _rank(values) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(xs, ys) -> float:
    xs, ys = list(xs), list(ys)
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def spearman(xs, ys) -> float:
    return pearson(_rank(list(xs)), _rank(list(ys)))


# ------------------------------------------------------------ cue residualising

def logistic_fit(X: list[list[float]], y: list[int], l2: float = 1.0,
                 iters: int = 600, lr: float = 0.35) -> list[float]:
    """Plain gradient descent.  ``X`` must already include the intercept column."""
    n = len(X)
    if n == 0:
        return [0.0] * (len(X[0]) if X else 0)
    d = len(X[0])
    w = [0.0] * d
    for _ in range(iters):
        grad = [0.0] * d
        for xi, yi in zip(X, y):
            z = sum(w[k] * xi[k] for k in range(d))
            err = sigmoid(z) - yi
            for k in range(d):
                grad[k] += err * xi[k]
        for k in range(d):
            w[k] -= lr * (grad[k] / n + l2 * w[k] / n)
    return w


def logistic_predict(w: list[float], x: list[float]) -> float:
    return sigmoid(sum(wk * xk for wk, xk in zip(w, x)))


def cue_features(item) -> list[float]:
    """Surface features a reader gets from the rendered text.  No access to the
    hidden difficulty level, and no access to the reference answer."""
    return [
        1.0,
        math.log1p(item.len_chars) / 6.0,
        item.digit_count / 20.0,
        item.cue_salience,
    ]


def fit_cue_model(items, labels) -> list[float]:
    return logistic_fit([cue_features(it) for it in items], list(labels))


def cue_only_probability(w: list[float], items) -> list[float]:
    return [logistic_predict(w, cue_features(it)) for it in items]


def cue_residual_auroc(w_cue, items, labels, probs) -> float:
    """AUROC of confidence once the surface-cue model's explanation is removed.

    Residual = logit(confidence) - logit(cue-only prediction).  If the model's
    confidence is *only* difficulty stereotyping, the residual carries no
    ranking information and this value collapses to ~0.5.
    """
    if len(items) != len(probs):
        raise ValueError("items/probs length mismatch")
    resid = [
        logit(p) - logit(c)
        for p, c in zip(probs, cue_only_probability(w_cue, items))
    ]
    return auroc(resid, labels)


# ------------------------------------------------------------------ self-model

def sma(cell_pred: dict, cell_true: dict) -> float:
    """Mean absolute error of a self-model over the cells present in both."""
    common = [k for k in cell_pred if k in cell_true]
    if not common:
        return float("nan")
    return sum(abs(cell_pred[k] - cell_true[k]) for k in common) / len(common)


def cell_accuracy(records) -> dict:
    """records: iterable of (family, level, correct) -> {(family, level): acc}."""
    acc: dict[tuple[str, int], list[int]] = {}
    for family, level, correct in records:
        acc.setdefault((family, level), []).append(int(correct))
    return {k: sum(v) / len(v) for k, v in acc.items()}


# ---------------------------------------------------------------- uncertainty

def bootstrap_ci(values, stat_fn=mean, n_boot: int = 2000, alpha: float = 0.05,
                 seed: int = 12345) -> tuple[float, float]:
    vals = list(values)
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    stats = []
    n = len(vals)
    for _ in range(n_boot):
        stats.append(stat_fn([vals[rng.randrange(n)] for _ in range(n)]))
    stats.sort()
    lo = stats[int((alpha / 2) * n_boot)]
    hi = stats[int((1 - alpha / 2) * n_boot) - 1]
    return lo, hi


def paired_bootstrap_p(a, b, n_boot: int = 2000, seed: int = 999) -> float:
    """Two-sided bootstrap p for mean(a) != mean(b) on paired samples."""
    a, b = list(a), list(b)
    if len(a) != len(b) or not a:
        return float("nan")
    diffs = [x - y for x, y in zip(a, b)]
    obs = mean(diffs)
    rng = random.Random(seed)
    n = len(diffs)
    centred = [d - obs for d in diffs]
    count = 0
    for _ in range(n_boot):
        s = sum(centred[rng.randrange(n)] for _ in range(n)) / n
        if abs(s) >= abs(obs):
            count += 1
    return (count + 1) / (n_boot + 1)
