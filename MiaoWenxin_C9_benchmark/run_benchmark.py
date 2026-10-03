#!/usr/bin/env python3
"""DeltaE-Bench -- single entry point.

    python run_benchmark.py                       # full reference run
    python run_benchmark.py --seed 7 --out out2   # different seed, new output dir
    python run_benchmark.py --models SolverA      # one solver only

Produces, in the output directory:
    results.json      every metric, every predictor, every block
    results.md        the same thing as Markdown tables
    report.html       one self-contained page with embedded SVG figures
    figures/*.svg     the figures on their own

Pure standard library.  Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from deltabench.runner import Config, run_all          # noqa: E402
from deltabench.report import build_report             # noqa: E402
from deltabench.solvers import PROFILES                # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the DeltaE-Bench reference protocol.")
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--seed", type=int, default=Config.seed)
    ap.add_argument("--models", default="",
                    help=f"comma-separated subset of {list(PROFILES)}")
    ap.add_argument("--per-cell-probe", type=int, default=Config.per_cell_probe)
    ap.add_argument("--per-cell-eval", type=int, default=Config.per_cell_eval)
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args(argv)

    cfg = Config(
        seed=args.seed,
        per_cell_probe=args.per_cell_probe,
        per_cell_eval=args.per_cell_eval,
    )
    keys = [k.strip() for k in args.models.split(",") if k.strip()] or None
    if keys:
        unknown = [k for k in keys if k not in PROFILES]
        if unknown:
            ap.error(f"unknown solver(s) {unknown}; available: {list(PROFILES)}")

    t0 = time.time()
    res = run_all(cfg, keys)
    elapsed = time.time() - t0

    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "results.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, default=str)

    print(f"[ok] {len(res['models'])} solvers in {elapsed:.1f}s -> {json_path}")
    for k, r in res["models"].items():
        warm = r["blocks"]["B3_warm"]["predictors"]
        inner = warm["P4 InnerSignal(cold)"]
        pop = warm["P3 PopDifficulty (no self)"]
        ctrl = r["control"]
        sweep = r["self_model_quality_sweep"]["quality=1.0"]
        print(f"     {r['solver']:<26} acc={inner['accuracy']:.3f} "
              f"| dE(in)= {inner['delta_e']:+.3f} ECE={inner['ece']:.3f} "
              f"AUROC={inner['auroc']:.3f} "
              f"| AUROC(popdiff)={pop['auroc']:.3f} "
              f"| CU {ctrl['cold_inner']['control_utility']:.2f}"
              f"->{ctrl['warm_blend']['control_utility']:.2f} "
              f"| SMA={sweep['sma_holdout']:.3f} (floor {r['sma_noise_floor']:.3f})")

    if not args.no_report:
        paths = build_report(res, args.out)
        print(f"[ok] report -> {paths['markdown']}")
        print(f"[ok] report -> {paths['html']}  (+{len(paths['figures'])} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
