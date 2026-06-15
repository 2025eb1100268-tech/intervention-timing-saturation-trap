"""Generate all five Paper-2 figures from fig_data/ and the runE monitor log.

Run from repo root:  python paper2/figures/make_figures.py
Outputs PDF + PNG (300dpi) for fig1..fig5 in paper2/figures/.
"""
from __future__ import annotations
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from figstyle import apply_style, save, CB, SINGLE_COL, DOUBLE_COL
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parents[2]
FIGD = ROOT / "data" / "swebench_pilot" / "fig_data"
PILOT = ROOT / "data" / "swebench_pilot"
LIVE = ROOT / "data" / "live_runs"

# A symmetric-log-ish x: dt grid includes 0, which log can't show. We plot on
# a linear index axis and label with the real dt values; this keeps the cliff
# legible and honestly represents the discrete grid.
DT_GRID = [0, 1, 5, 15, 30, 60, 150, 300, 600]
XIDX = list(range(len(DT_GRID)))
XLAB = [str(d) for d in DT_GRID]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _xaxis(ax):
    ax.set_xticks(XIDX)
    ax.set_xticklabels(XLAB)
    ax.set_xlabel(r"inter-action $\Delta t$ (s)")
    ax.margins(x=0.02)


# ---------------------------------------------------------------------------
# Fig 1 — centerpiece: two panels, shared x, three monitor archetypes
# ---------------------------------------------------------------------------
def fig1():
    bands = read_csv(FIGD / "dt_bands_n20.csv")
    gen = read_csv(FIGD / "generality_n20.csv")
    bd = {int(r["dt"]): r for r in bands}
    gd = {int(r["dt"]): r for r in gen}

    a6_med = [float(bd[d]["a6_med"]) for d in DT_GRID]
    a6_min = [float(bd[d]["a6_min"]) for d in DT_GRID]
    a6_max = [float(bd[d]["a6_max"]) for d in DT_GRID]
    t3_med = [float(bd[d]["t3_med"]) for d in DT_GRID]

    i1_med = [float(gd[d]["i1_level_median"]) for d in DT_GRID]
    i1_min = [float(gd[d]["i1_level_min"]) for d in DT_GRID]
    i1_max = [float(gd[d]["i1_level_max"]) for d in DT_GRID]
    i1_edge = [float(gd[d]["i1_edge_median"]) for d in DT_GRID]
    i2 = [float(gd[d]["i2_median"]) for d in DT_GRID]

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(DOUBLE_COL, 2.5), sharex=True)

    # (a) HEART
    axa.fill_between(XIDX, a6_min, a6_max, color=CB["blue"], alpha=0.18, lw=0)
    axa.plot(XIDX, a6_med, color=CB["blue"], marker="o", ms=3)
    axa.plot(XIDX, t3_med, color=CB["vermil"], marker="s", ms=3)
    axa.annotate("A6 level\n(median + min–max band)", xy=(2, a6_med[2]),
                 xytext=(2.3, 30), fontsize=7, color=CB["blue"], va="center")
    axa.annotate("T3 edge", xy=(6, t3_med[6]), xytext=(5.0, 6.0),
                 fontsize=7, color=CB["vermil"], va="center")
    axa.set_ylabel("firings per trajectory")
    axa.set_title("(a) HEART affect engine", loc="left", fontweight="bold")
    axa.set_ylim(-1.5, 49)
    _xaxis(axa)

    # (b) HEART-free instruments
    axb.fill_between(XIDX, i1_min, i1_max, color=CB["green"], alpha=0.16, lw=0)
    axb.plot(XIDX, i1_med, color=CB["green"], marker="o", ms=3)
    axb.plot(XIDX, i1_edge, color=CB["vermil"], marker="s", ms=3)
    axb.plot(XIDX, i2, color=CB["black"], marker="^", ms=3, ls="--")
    axb.annotate("I1 accumulator\n(level)", xy=(1, i1_med[1]),
                 xytext=(0.3, 9.5), fontsize=7, color=CB["green"], va="center")
    axb.annotate("I1 edge", xy=(6, i1_edge[6]), xytext=(5.0, 6.0),
                 fontsize=7, color=CB["vermil"], va="center")
    axb.annotate("I2 sample-time CUSUM (dt-invariant)", xy=(4, 26),
                 xytext=(0.3, 40), fontsize=7, color=CB["black"], va="center")
    axb.set_title("(b) HEART-free instruments", loc="left", fontweight="bold")
    axb.set_ylim(-1.5, 49)
    _xaxis(axb)

    fig.tight_layout(w_pad=1.2)
    save(fig, "fig1")


# ---------------------------------------------------------------------------
# Fig 2 — persistence vs dt, 20 thin lines + mean, shaded band, cadence markers
# ---------------------------------------------------------------------------
def fig2():
    # per-trajectory persistence vs dt computed from fullstate_dt files
    import glob, os
    ids = [os.path.basename(f)[:-5] for f in
           glob.glob(str(PILOT / "fullstate_dt0_*.json"))]
    ids = sorted(set(i.replace("fullstate_dt0_", "") for i in ids))

    def persistence(tid, dt):
        art = json.loads((PILOT / f"fullstate_dt{dt}_{tid}.json").read_text(encoding="utf-8"))
        fr = [e["vector"]["frustration"] for e in art["timeline"]]
        fc = next((i for i, f in enumerate(fr) if f >= 0.7), None)
        if fc is None:
            return 0.0
        post = fr[fc:]
        return 100.0 * sum(1 for f in post if f >= 0.7) / len(post)

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.4))

    # shaded critical band (1, 30] in index space: dt=1 -> idx1, dt=30 -> idx4
    ax.axvspan(XIDX[1], XIDX[4], color=CB["yellow"], alpha=0.22, lw=0, zorder=0)

    allp = []
    for tid in ids:
        ps = [persistence(tid, d) for d in DT_GRID]
        allp.append(ps)
        ax.plot(XIDX, ps, color=CB["grey"], lw=0.5, alpha=0.55, zorder=1)
    mean_p = np.mean(allp, axis=0)
    ax.plot(XIDX, mean_p, color=CB["blue"], lw=1.8, zorder=3, label="mean")

    # measured cadence markers in index space (interpolated position on the
    # linear-index axis between dt grid points)
    def idx_of(dt_val):
        for i in range(len(DT_GRID) - 1):
            lo, hi = DT_GRID[i], DT_GRID[i + 1]
            if lo <= dt_val <= hi:
                frac = (dt_val - lo) / (hi - lo) if hi > lo else 0
                return i + frac
        return len(DT_GRID) - 1
    # the two markers are very close in index space; draw both lines, label
    # once with a small bracket to avoid overprinting.
    x_med = idx_of(1.53)
    x_p90 = idx_of(2.33)
    for x in (x_med, x_p90):
        ax.axvline(x, color=CB["vermil"], lw=0.9, ls=":", zorder=2)
    ax.annotate("measured cadence\nmedian 1.53 s, p90 2.33 s",
                xy=(x_med, 50), xytext=(x_p90 + 0.55, 52),
                fontsize=6.3, color=CB["vermil"], va="center",
                arrowprops=dict(arrowstyle="-", color=CB["vermil"], lw=0.6))

    ax.text(XIDX[3], 95, "critical band\n(1, 30] s", fontsize=6.5,
            color="#8a7400", ha="center", va="top")
    ax.set_ylabel("post-crossing persistence (%)")
    ax.set_ylim(-3, 105)
    _xaxis(ax)
    fig.tight_layout()
    save(fig, "fig2")


# ---------------------------------------------------------------------------
# Fig 3 — frustration vs action for one trajectory at 4 dt values
# ---------------------------------------------------------------------------
def fig3():
    rows = read_csv(FIGD / "frustration_curves_n20.csv")
    tid = "astropy-13398"
    series = defaultdict(list)
    for r in rows:
        if r["trajectory"] == tid:
            series[int(r["dt"])].append((int(r["action_index"]), float(r["frustration"])))
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.3))
    colors = {0: CB["blue"], 5: CB["green"], 15: CB["orange"], 60: CB["vermil"]}
    for dt in [0, 5, 15, 60]:
        pts = sorted(series[dt])
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=colors[dt], label=f"$\\Delta t$={dt}s")
    ax.axhline(0.7, color=CB["grey"], lw=0.7, ls="--")
    ax.text(1, 0.72, "threshold 0.7", fontsize=6.3, color=CB["grey"])
    ax.set_xlabel("action index")
    ax.set_ylabel("modeled frustration")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, loc="center right", handlelength=1.3)
    ax.set_title(f"{tid}: one agent, four monitor realities", loc="left", fontsize=7.5)
    fig.tight_layout()
    save(fig, "fig3")


# ---------------------------------------------------------------------------
# Fig 4 — predicted vs observed critical-dt intervals (both estimators)
# ---------------------------------------------------------------------------
def fig4():
    # Parse the ANALYTIC report tables for predicted dt_crit + observed interval.
    txt = (PILOT / "ANALYTIC_DT_REPORT.md").read_text(encoding="utf-8")
    # original predictions (table after "## Per-trajectory results")
    orig = {}
    for line in txt.splitlines():
        if line.startswith("| astropy-") and "(" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            # cols: traj actions evt total r dtcrit interval inside cv maxd
            try:
                traj = cells[0]; dtcrit = float(cells[5])
                iv = cells[6]  # e.g. (5, 15]
                lo, hi = iv.strip("(]").split(",")
                orig[traj] = (dtcrit, float(lo), float(hi))
            except Exception:
                pass
    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.6))
    ys = list(range(len(orig)))
    trajs = list(orig.keys())
    for y, t in zip(ys, trajs):
        dtcrit, lo, hi = orig[t]
        ax.plot([lo, hi], [y, y], color=CB["skyblue"], lw=3, alpha=0.7,
                solid_capstyle="butt",
                label="observed interval" if y == 0 else None)
        ax.plot(dtcrit, y, "o", color=CB["vermil"], ms=4,
                label="predicted (zero-param)" if y == 0 else None)
    ax.set_yticks(ys)
    ax.set_yticklabels([t.replace("astropy-", "ast-") for t in trajs], fontsize=6)
    ax.set_xlabel(r"critical $\Delta t$ (s)")
    ax.set_xlim(0, 32)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("predicted vs observed critical $\\Delta t$ (5 pilot traj.)",
                 loc="left", fontsize=7.3)
    fig.tight_layout()
    save(fig, "fig4")


# ---------------------------------------------------------------------------
# Fig 5 — the live runE monitor log
# ---------------------------------------------------------------------------
def fig5():
    rows = [json.loads(l) for l in
            (LIVE / "runE" / "monitor_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    idx = [r["action_index"] for r in rows]
    fr = [r["frustration"] for r in rows]
    a6 = [r["a6"]["sustained_frustration"] for r in rows]
    t3 = [r["t3_net_fired"] for r in rows]
    dt = [r["dt"] for r in rows]

    fig, ax = plt.subplots(figsize=(DOUBLE_COL * 0.62, 2.4))
    ax.plot(idx, fr, color=CB["blue"], marker=".", ms=3, label="frustration")
    ax.axhline(0.7, color=CB["grey"], lw=0.7, ls="--")
    ax.text(0.3, 0.72, "0.7", fontsize=6.3, color=CB["grey"])

    # A6 plateau: shade where A6 true
    for x, on in zip(idx, a6):
        if on:
            ax.axvspan(x - 0.5, x + 0.5, color=CB["orange"], alpha=0.10, lw=0, zorder=0)
    # T3 fire marker
    for x, on, y in zip(idx, t3, fr):
        if on:
            ax.plot(x, y, "*", color=CB["vermil"], ms=11, zorder=5)
            ax.annotate("T3 edge-fire\n(0.603→0.750)", xy=(x, y), xytext=(x + 1.5, 0.55),
                        fontsize=6.5, color=CB["vermil"],
                        arrowprops=dict(arrowstyle="->", color=CB["vermil"], lw=0.7))
    ax.text(20, 0.12, "orange shade: A6 true (25/32 actions)",
            fontsize=6.3, color="#9a6a00")
    ax.set_xlabel("action index (real wall-clock run)")
    ax.set_ylabel("modeled frustration")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"live run: median $\\Delta t$={np.median([d for d in dt if d>0]):.2f}s",
                 loc="left", fontsize=7.3)
    fig.tight_layout()
    save(fig, "fig5")


if __name__ == "__main__":
    apply_style()
    print("rendering figures...")
    fig1(); fig2(); fig3(); fig4(); fig5()
    print("done.")
