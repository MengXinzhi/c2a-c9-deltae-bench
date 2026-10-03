"""Metric-level unit tests.

Every one of these asserts a property that *theory* predicts, so a green run is
evidence that the scorer is measuring what the design says it is measuring.
Run with:  python -m pytest tests -q      (or: python tests/test_metrics.py)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deltabench import metrics as M  # noqa: E402


def test_auroc_perfect_reversed_and_constant():
    labels = [1, 1, 0, 0]
    assert abs(M.auroc([0.9, 0.8, 0.2, 0.1], labels) - 1.0) < 1e-9
    assert abs(M.auroc([0.1, 0.2, 0.8, 0.9], labels) - 0.0) < 1e-9
    assert abs(M.auroc([0.5, 0.5, 0.5, 0.5], labels) - 0.5) < 1e-9


def test_auroc_ties_use_average_ranks():
    # everything tied -> chance level
    assert abs(M.auroc([0.3, 0.3, 0.3, 0.3], [1, 1, 0, 0]) - 0.5) < 1e-9
    # positive 0.5 vs negatives {0.5, 0.1}: one tie (0.5) + one win (1.0) -> 0.75
    assert abs(M.auroc([0.5, 0.5, 0.1], [1, 0, 0]) - 0.75) < 1e-9


def test_delta_e_sign():
    labels = [1, 0, 1, 0]
    assert abs(M.delta_e([0.8] * 4, labels) - 0.3) < 1e-9     # over-confident
    assert abs(M.delta_e([0.2] * 4, labels) + 0.3) < 1e-9     # under-confident


def test_constant_predictor_aces_ece_but_fails_brier():
    """The single most important guard in the whole metric suite: a predictor
    that says 0.5 to everything must not look good."""
    labels = [1, 0] * 50
    p = [0.5] * 100
    assert M.ece(p, labels) < 1e-9
    assert abs(M.brier(p, labels) - 0.25) < 1e-9

    # an informative, correctly calibrated predictor must beat it on Brier
    labels2, p2 = [], []
    for i in range(100):
        if i % 4 == 0:
            labels2.append(1); p2.append(0.8)
        elif i % 4 == 1:
            labels2.append(0); p2.append(0.2)
        elif i % 4 == 2:
            labels2.append(1); p2.append(0.4)
        else:
            labels2.append(0); p2.append(0.4)
    assert M.brier(p2, labels2) < 0.25


def test_perfectly_calibrated_has_zero_ece():
    labels, probs = [], []
    for _ in range(100):
        labels += [1, 0, 0, 0, 0]
        probs += [0.2] * 5
    assert M.ece(probs, labels, bins=15) < 0.03


def test_murphy_decomposition_reconstructs_brier():
    labels = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1] * 20
    probs = [0.9, 0.2, 0.7, 0.6, 0.3, 0.4, 0.8, 0.1, 0.55, 0.75] * 20
    mur = M.murphy(probs, labels)
    assert abs(mur["brier_reconstructed"] - M.brier(probs, labels)) < 1e-9


def test_spearman_monotone_and_reversed():
    assert abs(M.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1.0) < 1e-9
    assert abs(M.spearman([1, 2, 3, 4], [40, 30, 20, 10]) + 1.0) < 1e-9


def test_logistic_fit_recovers_a_separable_boundary():
    rng_x = [[1.0, -2.0], [1.0, -1.0], [1.0, 1.0], [1.0, 2.0]] * 10
    y = [0, 0, 1, 1] * 10
    w = M.logistic_fit(rng_x, y, l2=0.0, iters=2000, lr=1.0)
    assert w[1] > 0
    lo = M.logistic_predict(w, [1.0, -2.0])
    hi = M.logistic_predict(w, [1.0, 2.0])
    assert hi - lo > 0.5


def test_cue_residual_auroc_collapses_when_confidence_is_pure_cue():
    """If a predictor's confidence is a monotone function of the cue model, the
    residual carries no ranking information and the metric must say ~0.5."""
    from deltabench.items import Item

    items = [
        Item(iid=f"i{i}", family="arith_mod", level=1 + i % 5,
             prompt="x" * (10 + 4 * (i % 7)) + " " + "1" * (i % 11),
             answer="0", cue_salience=(i % 10) / 10.0,
             population_difficulty=0.5)
        for i in range(60)
    ]
    labels = [1 if (i % 3 == 0) else 0 for i in range(60)]
    w = M.fit_cue_model(items, labels)
    probs = M.cue_only_probability(w, items)
    assert abs(M.cue_residual_auroc(w, items, labels, probs) - 0.5) < 0.02


def test_paired_bootstrap_detects_a_real_shift():
    a = [0.9] * 40
    b = [0.5] * 40
    assert M.paired_bootstrap_p(a, b) < 0.05
    assert M.paired_bootstrap_p(a, list(a)) > 0.5


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} metric tests passed")
