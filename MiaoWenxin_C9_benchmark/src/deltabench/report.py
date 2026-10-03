"""Report generation: Markdown tables, hand-rolled SVG figures, one HTML page.

No plotting dependency is used -- the SVG is emitted directly so that the
figures are reproducible byte-for-byte from ``results.json``.
"""

from __future__ import annotations

import json
import os

# --- light-theme palette -----------------------------------------------------
INK = "#1f2937"
MUTED = "#6b7280"
GRID = "#e5e7eb"
BG = "#ffffff"
PANEL = "#f8fafc"

SERIES = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed",
          "#0891b2", "#be185d", "#4d7c0f", "#475569"]


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _fmt(v, nd=3):
    if isinstance(v, float):
        return "n/a" if v != v else f"{v:.{nd}f}"
    return str(v)


# ------------------------------------------------------------------ SVG helpers

def svg_reliability(probs, labels, title="Reliability, B3 warm block",
                    bins=10, w=520, h=360) -> str:
    pad_l, pad_r, pad_t, pad_b = 52, 16, 40, 44
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b

    buckets = [[] for _ in range(bins)]
    for p, y in zip(probs, labels):
        buckets[min(bins - 1, int(p * bins))].append((p, y))

    pts = []
    for i, b in enumerate(buckets):
        if not b:
            continue
        conf = sum(p for p, _ in b) / len(b)
        acc = sum(y for _, y in b) / len(b)
        pts.append((conf, acc, len(b)))

    def X(v):
        return pad_l + v * pw

    def Y(v):
        return pad_t + (1 - v) * ph

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
         f'width="{w}" height="{h}" role="img">',
         f'<rect width="{w}" height="{h}" fill="{BG}"/>',
         f'<text x="{pad_l}" y="22" font-family="system-ui,-apple-system,Segoe UI,sans-serif" '
         f'font-size="14" font-weight="600" fill="{INK}">{_esc(title)}</text>']

    for k in range(6):
        v = k / 5
        s.append(f'<line x1="{X(v):.1f}" y1="{pad_t}" x2="{X(v):.1f}" y2="{pad_t+ph}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<line x1="{pad_l}" y1="{Y(v):.1f}" x2="{pad_l+pw}" y2="{Y(v):.1f}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{X(v):.1f}" y="{pad_t+ph+18}" font-size="10" fill="{MUTED}" '
                 f'text-anchor="middle" font-family="system-ui,sans-serif">{v:.1f}</text>')
        s.append(f'<text x="{pad_l-8}" y="{Y(v)+3:.1f}" font-size="10" fill="{MUTED}" '
                 f'text-anchor="end" font-family="system-ui,sans-serif">{v:.1f}</text>')

    s.append(f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t}" '
             f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="4 3"/>')

    poly = " ".join(f"{X(c):.1f},{Y(a):.1f}" for c, a, _ in pts)
    s.append(f'<polyline points="{poly}" fill="none" stroke="{SERIES[0]}" stroke-width="2"/>')
    for c, a, n in pts:
        s.append(f'<circle cx="{X(c):.1f}" cy="{Y(a):.1f}" r="4" fill="{SERIES[0]}"/>')

    s.append(f'<text x="{pad_l+pw/2}" y="{h-6}" font-size="11" fill="{MUTED}" '
             f'text-anchor="middle" font-family="system-ui,sans-serif">stated confidence</text>')
    s.append(f'<text transform="translate(14,{pad_t+ph/2}) rotate(-90)" font-size="11" '
             f'fill="{MUTED}" text-anchor="middle" font-family="system-ui,sans-serif">observed accuracy</text>')
    s.append("</svg>")
    return "".join(s)


def svg_bars(rows, title, xlabel, w=560, row_h=26, pad_l=220, ref=None) -> str:
    """rows: list of (label, value).  Values in [0,1] unless ref is given."""
    n = len(rows)
    h = 52 + n * row_h + 30
    pw = w - pad_l - 60
    vmax = max([abs(v) for _, v in rows if v == v] + [0.1])
    if ref is not None:
        vmax = max(vmax, abs(ref))

    def X(v):
        return pad_l + (v / vmax) * pw

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
         f'width="{w}" height="{h}" role="img">',
         f'<rect width="{w}" height="{h}" fill="{BG}"/>',
         f'<text x="16" y="22" font-size="14" font-weight="600" fill="{INK}" '
         f'font-family="system-ui,sans-serif">{_esc(title)}</text>']

    if ref is not None:
        s.append(f'<line x1="{X(ref):.1f}" y1="34" x2="{X(ref):.1f}" y2="{34+n*row_h}" '
                 f'stroke="{SERIES[1]}" stroke-width="1.5" stroke-dasharray="5 3"/>')
        s.append(f'<text x="{X(ref)+5:.1f}" y="{34+n*row_h+14}" font-size="10" '
                 f'fill="{SERIES[1]}" font-family="system-ui,sans-serif">'
                 f'{_esc("chance") if abs(ref-0.5)<1e-9 else _esc(f"ref={ref:.2f}")}</text>')

    for i, (label, v) in enumerate(rows):
        y = 40 + i * row_h
        col = SERIES[i % len(SERIES)]
        s.append(f'<text x="{pad_l-10}" y="{y+13}" font-size="11" fill="{INK}" '
                 f'text-anchor="end" font-family="system-ui,sans-serif">{_esc(label)}</text>')
        if v == v:
            s.append(f'<rect x="{pad_l}" y="{y+3}" width="{max(1,(v/vmax)*pw):.1f}" '
                     f'height="{row_h-9}" rx="2" fill="{col}" opacity="0.85"/>')
            s.append(f'<text x="{X(v)+6:.1f}" y="{y+14}" font-size="10" fill="{MUTED}" '
                     f'font-family="system-ui,sans-serif">{v:.3f}</text>')

    s.append(f'<text x="{pad_l}" y="{h-8}" font-size="11" fill="{MUTED}" '
             f'font-family="system-ui,sans-serif">{_esc(xlabel)}</text>')
    s.append("</svg>")
    return "".join(s)


# ------------------------------------------------------------------- md tables

def _md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_esc(c) for c in r) + " |")
    return "\n".join(out)


PRED_ORDER = [
    "P0 Null (always 0.5)",
    "P1 BaseRate (marginal)",
    "P2 CueOnly (stereotype)",
    "P3 PopDifficulty (no self)",
    "P4 InnerSignal(cold)",
    "P5 KSTAR-blend(w=0.25)",
    "P5 KSTAR-blend(w=0.50)",
    "P5 KSTAR-blend(w=0.75)",
    "P6 BiasCorrected(inner)",
    "P7 SelfModelOnly",
    "P9 SelfOracle (ceiling)",
]


def _pred_table(block):
    rows = []
    for name in PRED_ORDER:
        m = block["predictors"].get(name)
        if not m:
            continue
        rows.append([name, _fmt(m["delta_e"]), _fmt(m["ece"]), _fmt(m["brier"]),
                     _fmt(m["auroc"]), _fmt(m["cue_residual_auroc"])])
    return _md_table(
        ["Predictor", "DeltaE", "ECE", "Brier", "AUROC", "cue-residual AUROC"], rows)


def _headline(res):
    """Derive the report's headline claims from the data, not from prose."""
    out = {}
    for key, r in res["models"].items():
        warm = r["blocks"]["B3_warm"]["predictors"]
        cold = r["blocks"]["B1_cold"]["predictors"]
        disc = r["surface_disguise"]
        out[key] = {
            "accuracy": warm["P9 SelfOracle (ceiling)"]["accuracy"],
            "delta_e_cold": cold["P4 InnerSignal(cold)"]["delta_e"],
            "delta_e_warm": warm["P4 InnerSignal(cold)"]["delta_e"],
            "delta_e_warm_blend": warm["P5 KSTAR-blend(w=0.50)"]["delta_e"],
            "auroc_inner": warm["P4 InnerSignal(cold)"]["auroc"],
            "auroc_popdiff": warm["P3 PopDifficulty (no self)"]["auroc"],
            "cue_resid_inner": warm["P4 InnerSignal(cold)"]["cue_residual_auroc"],
            "cue_resid_cue": warm["P2 CueOnly (stereotype)"]["cue_residual_auroc"],
            "stroop_d_auroc_cue": disc["P2 CueOnly (stereotype)"]["delta_auroc"],
            "stroop_d_auroc_selfmodel": disc["P7 SelfModelOnly"]["delta_auroc"],
            "control_warm": r["control"]["warm_blend"]["control_utility"],
            "control_cold": r["control"]["cold_inner"]["control_utility"],
            "sma_holdout": r["self_model_quality_sweep"]["quality=1.0"]["sma_holdout"],
            "sma_extrap": r["self_model_quality_sweep"]["quality=1.0"]["sma_extrap"],
            "sma_floor": r["sma_noise_floor"],
            "spearman_extrap": r["self_model_quality_sweep"]["quality=1.0"]["spearman_extrap_ladder"],
            "meg": r["memory_expression_gap"]["expression_gap_brier"],
            # calibration-fix contrast: what changes and what does not
            "inner_ece": warm["P4 InnerSignal(cold)"]["ece"],
            "inner_delta_e": warm["P4 InnerSignal(cold)"]["delta_e"],
            "inner_brier": warm["P4 InnerSignal(cold)"]["brier"],
            "inner_auroc": warm["P4 InnerSignal(cold)"]["auroc"],
            "inner_cue_resid": warm["P4 InnerSignal(cold)"]["cue_residual_auroc"],
            "bc_ece": warm["P6 BiasCorrected(inner)"]["ece"],
            "bc_delta_e": warm["P6 BiasCorrected(inner)"]["delta_e"],
            "bc_brier": warm["P6 BiasCorrected(inner)"]["brier"],
            "bc_auroc": warm["P6 BiasCorrected(inner)"]["auroc"],
            "bc_cue_resid": warm["P6 BiasCorrected(inner)"]["cue_residual_auroc"],
        }
    return out


def build_report(res, out_dir) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    cfg = res["config"]
    lines = []
    lines.append("# DeltaE-Bench reference run\n")
    lines.append(
        f"Seed `{cfg['seed']}` | probe {cfg['per_cell_probe']} items/cell | "
        f"eval {cfg['per_cell_eval']} items/cell | truth sample "
        f"{cfg['per_cell_truth']} items/cell\n")
    lines.append(
        "> **Scope.** These numbers come from six *simulated* solvers, not from a "
        "frontier model. They validate the instrument (that it discriminates, and "
        "that the control predictors behave as the design predicts). Plug a real "
        "model in via `deltabench.adapters` to obtain real results.\n")

    head = _headline(res)

    # --- ability ------------------------------------------------------------
    rows = []
    for k, r in res["models"].items():
        a = r["ability"]
        fam = ", ".join(f"{f.split('_')[0]}={a['per_family'][f]:.2f}"
                        for f in sorted(a["per_family"]))
        rows.append([r["solver"], f"{a['overall_accuracy']:.3f}",
                     f"{a['per_family_held_out']:.3f}", fam])
    lines.append("## 1. Ability profiles (the 'objective self')\n")
    lines.append(_md_table(["Solver", "probe acc", "unseen-family acc", "per-family probe acc"], rows))
    lines.append("")

    # --- headline ----------------------------------------------------------
    lines.append("## 2. Headline metrics\n")
    rows = []
    for k, h in head.items():
        rows.append([res["models"][k]["solver"], f"{h['accuracy']:.3f}",
                     f"{h['delta_e_cold']:+.3f}", f"{h['delta_e_warm_blend']:+.3f}",
                     f"{h['auroc_inner']:.3f}", f"{h['auroc_popdiff']:.3f}",
                     f"{h['control_cold']:.3f}", f"{h['control_warm']:.3f}"])
    lines.append(_md_table(
        ["Solver", "acc", "DeltaE cold", "DeltaE warm", "AUROC inner",
         "AUROC popdiff", "CU cold", "CU warm"], rows))
    lines.append("\n*CU = budgeted control utility: 0 = the self-model is worthless "
                 "for choosing what to attempt, 1 = it selects as well as an oracle.*\n")

    # --- calibration-fix contrast -----------------------------------------
    lines.append("## 2b. What a calibration fix does -- and does not -- change\n")
    rows = []
    for k, h in head.items():
        rows.append([res["models"][k]["solver"],
                     f"{h['inner_ece']:.3f} -> {h['bc_ece']:.3f}",
                     f"{h['inner_delta_e']:+.3f} -> {h['bc_delta_e']:+.3f}",
                     f"{h['inner_brier']:.3f} -> {h['bc_brier']:.3f}",
                     f"{h['inner_auroc']:.3f} -> {h['bc_auroc']:.3f}",
                     f"{h['inner_cue_resid']:.3f} -> {h['bc_cue_resid']:.3f}"])
    lines.append(_md_table(
        ["Solver", "ECE", "DeltaE", "Brier", "AUROC", "cue-residual AUROC"], rows))
    lines.append("\n`P6` subtracts, from every prediction, a constant estimated on the "
                 "agent's own probe block. That is an ordinary self-calibration step. "
                 "It collapses ECE and DeltaE -- the two metrics most often quoted -- "
                 "while resolution metrics barely move. **A benchmark that ranks on "
                 "ECE or DeltaE alone can be defeated by this predictor without any "
                 "improvement in metacognition.**\n")

    # --- block tables -------------------------------------------------------
    names = {"B1_cold": "3. Block B1 -- cold self-prediction (no self-history)",
             "B3_warm": "4. Block B3 -- warm self-prediction (authored self-model available)",
             "B4_stroop": "5. Block B4 -- surface disguise (cue/difficulty inverted)",
             "B6_unseen_skill": "6. Block B6 -- unseen skill family"}
    lines.append("For reference, the predictors are: `P0` constant 0.5; `P1` the run's "
                 "marginal accuracy; `P2` a logistic model over surface text features; "
                 "`P3` the normative item difficulty with no self-access; `P4` the "
                 "agent's intrinsic pre-answer signal; `P5` a logit-space blend of that "
                 "signal with the authored self-model; `P6` `P4` after a self-calibration "
                 "shift; `P7` the authored self-model alone; `P9` an oracle ceiling. "
                 "Block B1 contains only predictors that need no self-history.\n")
    for bkey, title in names.items():
        lines.append(f"## {title}\n")
        for k, r in res["models"].items():
            lines.append(f"**{r['solver']}**\n")
            lines.append(_pred_table(r["blocks"][bkey]))
            lines.append("")

    # --- self-model sweep --------------------------------------------------
    lines.append("## 7. Self-model accuracy (SMA) -- is the authored artifact any good?\n")
    rows = []
    for k, r in res["models"].items():
        for q, s in r["self_model_quality_sweep"].items():
            rows.append([r["solver"], q, _fmt(s["sma_holdout"]), _fmt(s["sma_interp"]),
                         _fmt(s["sma_extrap"]), _fmt(s["sma_noise_floor"]),
                         _fmt(s["spearman_extrap_ladder"])])
    lines.append(_md_table(
        ["Solver", "authoring policy", "SMA seen cells", "SMA interpolated",
         "SMA unseen family", "noise floor", "Spearman (unseen ladder)"], rows))
    lines.append("\n`quality=1.0` uses only the agent's own outcome history; "
                 "`quality=0.0` ignores that history and falls back on the normative "
                 "difficulty prior. **The noise floor is the MAE that even a perfect "
                 "estimator incurs** because per-cell accuracy is only observable "
                 "through finitely many trials -- read SMA against it, not against 0. "
                 "A blank Spearman entry means the authored self-model returned a "
                 "single constant for that family, so no ordering exists to correlate.\n")

    # --- surface disguise --------------------------------------------------
    lines.append("## 8. Surface disguise: does confidence survive inverted cues?\n")
    rows = []
    for k, r in res["models"].items():
        d = r["surface_disguise"]
        for nm in ("P2 CueOnly (stereotype)", "P3 PopDifficulty (no self)",
                   "P4 InnerSignal(cold)", "P7 SelfModelOnly",
                   "P9 SelfOracle (ceiling)"):
            if nm not in d:
                continue
            rows.append([r["solver"], nm, f"{d[nm]['delta_e_normal']:+.3f}",
                         f"{d[nm]['delta_e_stroop']:+.3f}",
                         f"{d[nm]['delta_auroc']:+.3f}",
                         f"{d[nm]['delta_brier']:+.3f}"])
    lines.append(_md_table(
        ["Solver", "Predictor", "DeltaE normal", "DeltaE disguised",
         "dAUROC", "dBrier"], rows))
    lines.append("\nA predictor that reads the rendered text loses discrimination "
                 "when the surface stops predicting difficulty. A predictor keyed on "
                 "task identity does not. That contrast is the construct validity "
                 "test for 'self-knowledge' vs 'difficulty stereotyping'.\n")

    # --- control -----------------------------------------------------------
    lines.append("## 9. Budgeted control -- does self-knowledge change behaviour?\n")
    rows = []
    for k, r in res["models"].items():
        c = r["control"]
        rows.append([r["solver"], f"{c['cold_inner']['control_utility']:.3f}",
                     f"{c['warm_blend']['control_utility']:.3f}",
                     f"{c['self_model_only']['control_utility']:.3f}",
                     f"{c['oracle_ceiling']['acc_oracle']:.3f}",
                     f"{c['oracle_ceiling']['acc_random']:.3f}"])
    lines.append(_md_table(
        ["Solver", "CU cold", "CU warm", "CU self-model only",
         "oracle acc", "random acc"], rows))
    lines.append("")

    # --- MEG ---------------------------------------------------------------
    lines.append("## 10. Metacognitive expression gap (verbal vs behavioural channel)\n")
    rows = []
    for k, r in res["models"].items():
        m = r["memory_expression_gap"]
        rows.append([r["solver"], f"{m['brier_verbal']:.3f}",
                     f"{m['brier_behavioral']:.3f}",
                     f"{m['expression_gap_brier']:+.3f}",
                     f"{m['delta_e_verbal']:+.3f}", f"{m['delta_e_behavioral']:+.3f}"])
    lines.append(_md_table(
        ["Solver", "Brier verbal", "Brier bet channel", "gap",
         "DeltaE verbal", "DeltaE bet"], rows))
    lines.append("\nA positive gap means the stated confidence is displaced further "
                 "from reality than the signal the agent can act on: it behaves more "
                 "competently than it can say, i.e. it *knows* more than it can "
                 "*express*. `debias_fitted` is the single logit shift the agent "
                 "learned from its own probe block. With a real model both channels "
                 "are measured directly rather than modelled.\n")

    md = "\n".join(lines)
    md_path = os.path.join(out_dir, "results.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)

    # --- figures -----------------------------------------------------------
    produced = []
    first_key = list(res["models"])[0]
    warm_raw = res["models"][first_key]["raw"]["warm"]
    for nm, fname, title in (
        ("P5 KSTAR-blend(w=0.50)", "reliability_blend.svg", "Reliability -- warm self-model"),
        ("P4 InnerSignal(cold)", "reliability_inner.svg", "Reliability -- intrinsic signal only"),
    ):
        svg = svg_reliability(warm_raw["probs"][nm], warm_raw["labels"], title)
        p = os.path.join(fig_dir, fname)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(svg)
        produced.append(p)

    rows = [(n.replace("P", "").strip(), res["models"][first_key]["blocks"]["B3_warm"]["predictors"][n]["auroc"])
            for n in PRED_ORDER if n in res["models"][first_key]["blocks"]["B3_warm"]["predictors"]]
    svg = svg_bars(rows, "AUROC of pre-answer confidence (B3 warm)", "AUROC (0.5 = chance)", ref=0.5)
    p = os.path.join(fig_dir, "auroc_warm.svg")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(svg)
    produced.append(p)

    rows = []
    for nm in PRED_ORDER:
        if nm in res["models"][first_key]["surface_disguise"]:
            rows.append((nm.split(" ")[1] if " " in nm else nm,
                         res["models"][first_key]["surface_disguise"][nm]["delta_auroc"]))
    svg = svg_bars(rows, "Loss of AUROC under surface disguise", "dAUROC (negative = worse)",
                   ref=0.0, pad_l=200)
    p = os.path.join(fig_dir, "surface_disguise.svg")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(svg)
    produced.append(p)

    # --- html --------------------------------------------------------------
    def _embed(svg_path):
        with open(svg_path, encoding="utf-8") as fh:
            return fh.read()

    html = ["""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>DeltaE-Bench reference run</title>
<style>
:root{--ink:#1f2937;--muted:#6b7280;--line:#e5e7eb;}
*{box-sizing:border-box}
body{margin:0;padding:32px;background:#fff;color:var(--ink);
 font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.65}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.scope{background:#fff7ed;border-left:3px solid #d97706;padding:10px 14px;border-radius:0 6px 6px 0;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th{text-align:left;background:#f3f4f6;font-weight:600;padding:7px 9px;border-bottom:1px solid var(--line)}
td{padding:6px 9px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
tr:hover td{background:#fafafa}
code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12.5px}
.figs{display:flex;flex-wrap:wrap;gap:18px;margin-top:12px}
.figs figure{margin:0;background:#f8fafc;border:1px solid var(--line);border-radius:8px;padding:10px}
.note{color:var(--muted);font-size:13px}
</style></head><body><div class="wrap">"""]
    html.append("<h1>DeltaE-Bench &mdash; reference run</h1>")
    html.append(f'<p class="note">seed <code>{cfg["seed"]}</code> &middot; '
                f'{len(res["models"])} simulated solvers &middot; '
                f'probe {cfg["per_cell_probe"]}/cell &middot; eval {cfg["per_cell_eval"]}/cell</p>')
    html.append('<p class="scope"><b>Scope.</b> All numbers below come from <b>simulated '
                'solvers</b>, not from a frontier model. They demonstrate that the '
                'instrument discriminates and that the control predictors behave as the '
                'design predicts. Real results require plugging in a model via '
                '<code>deltabench.adapters</code>.</p>')

    html.append("<h2>Headline</h2><table><tr>"
                "<th>Solver</th><th>acc</th><th>&Delta;E cold</th><th>&Delta;E warm</th>"
                "<th>AUROC inner</th><th>AUROC popdiff</th><th>CU cold</th><th>CU warm</th></tr>")
    for k, h in head.items():
        html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                    [res["models"][k]["solver"], f"{h['accuracy']:.3f}",
                     f"{h['delta_e_cold']:+.3f}", f"{h['delta_e_warm_blend']:+.3f}",
                     f"{h['auroc_inner']:.3f}", f"{h['auroc_popdiff']:.3f}",
                     f"{h['control_cold']:.3f}", f"{h['control_warm']:.3f}"]) + "</tr>")
    html.append("</table>")

    html.append('<h2>What a calibration fix changes &mdash; and what it does not</h2>'
                '<table><tr><th>Solver</th><th>ECE</th><th>&Delta;E</th><th>Brier</th>'
                '<th>AUROC</th><th>cue-residual AUROC</th></tr>')
    for k, h in head.items():
        html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                    [res["models"][k]["solver"],
                     f"{h['inner_ece']:.3f} &rarr; {h['bc_ece']:.3f}",
                     f"{h['inner_delta_e']:+.3f} &rarr; {h['bc_delta_e']:+.3f}",
                     f"{h['inner_brier']:.3f} &rarr; {h['bc_brier']:.3f}",
                     f"{h['inner_auroc']:.3f} &rarr; {h['bc_auroc']:.3f}",
                     f"{h['inner_cue_resid']:.3f} &rarr; {h['bc_cue_resid']:.3f}"]) + "</tr>")
    html.append("</table>")

    html.append('<h2>Figures</h2><div class="figs">')
    for p in produced:
        html.append(f"<figure>{_embed(p)}</figure>")
    html.append("</div>")

    html.append("<h2>Surface disguise &mdash; construct validity</h2><table>"
                "<tr><th>Solver</th><th>Predictor</th><th>&Delta;E normal</th>"
                "<th>&Delta;E disguised</th><th>dAUROC</th><th>dBrier</th></tr>")
    for k, r in res["models"].items():
        d = r["surface_disguise"]
        for nm in ("P2 CueOnly (stereotype)", "P3 PopDifficulty (no self)",
                   "P4 InnerSignal(cold)", "P7 SelfModelOnly", "P9 SelfOracle (ceiling)"):
            if nm not in d:
                continue
            html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                        [r["solver"], nm, f"{d[nm]['delta_e_normal']:+.3f}",
                         f"{d[nm]['delta_e_stroop']:+.3f}",
                         f"{d[nm]['delta_auroc']:+.3f}", f"{d[nm]['delta_brier']:+.3f}"]) + "</tr>")
    html.append("</table>")

    html.append("<h2>Self-model accuracy</h2><table><tr><th>Solver</th>"
                "<th>policy</th><th>SMA seen</th><th>SMA interp</th>"
                "<th>SMA unseen family</th><th>noise floor</th><th>Spearman</th></tr>")
    for k, r in res["models"].items():
        for q, s in r["self_model_quality_sweep"].items():
            html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                        [r["solver"], q, _fmt(s["sma_holdout"]), _fmt(s["sma_interp"]),
                         _fmt(s["sma_extrap"]), _fmt(s["sma_noise_floor"]),
                         _fmt(s["spearman_extrap_ladder"])]) + "</tr>")
    html.append("</table>")

    html.append("<h2>Budgeted control</h2><table><tr><th>Solver</th><th>CU cold</th>"
                "<th>CU warm</th><th>CU self-model only</th><th>oracle acc</th>"
                "<th>random acc</th></tr>")
    for k, r in res["models"].items():
        c = r["control"]
        html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                    [r["solver"], f"{c['cold_inner']['control_utility']:.3f}",
                     f"{c['warm_blend']['control_utility']:.3f}",
                     f"{c['self_model_only']['control_utility']:.3f}",
                     f"{c['oracle_ceiling']['acc_oracle']:.3f}",
                     f"{c['oracle_ceiling']['acc_random']:.3f}"]) + "</tr>")
    html.append("</table>")

    html.append("<h2>Metacognitive expression gap</h2><table><tr><th>Solver</th>"
                "<th>Brier verbal</th><th>Brier bet</th><th>gap</th>"
                "<th>&Delta;E verbal</th><th>&Delta;E bet</th></tr>")
    for k, r in res["models"].items():
        m = r["memory_expression_gap"]
        html.append("<tr>" + "".join(f"<td>{v}</td>" for v in
                    [r["solver"], f"{m['brier_verbal']:.3f}", f"{m['brier_behavioral']:.3f}",
                     f"{m['expression_gap_brier']:+.3f}", f"{m['delta_e_verbal']:+.3f}",
                     f"{m['delta_e_behavioral']:+.3f}"]) + "</tr>")
    html.append("</table>")

    html.append("</div></body></html>")
    html_path = os.path.join(out_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write("".join(html))

    return {"markdown": md_path, "html": html_path, "figures": produced}


if __name__ == "__main__":  # pragma: no cover
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "results/results.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "results"
    with open(src, encoding="utf-8") as fh:
        data = json.load(fh)
    print(build_report(data, dst))
