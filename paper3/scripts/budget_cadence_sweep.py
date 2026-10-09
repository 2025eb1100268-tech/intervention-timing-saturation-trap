"""Phase B: monitoring budget x cadence sweep.

Pre-registered in data/swebench_pilot/PREREGISTRATION_PHASE9.md §2 (committed
before this script was run). No new agent runs: this operates entirely on the
20 existing frozen error streams (`has_error` from fullstate_dt0_<id>.json).

The question. Cost-constrained runtime monitoring samples a fraction of actions
to save money. If a monitor is wall-clock calibrated, sampling 1-in-r actions
multiplies the elapsed time between observations by r -- so the budget knob and
the calibration knob are the same knob, and a purely economic decision silently
moves the monitor across a regime boundary. At Paper 2's measured 1.53 s
cadence, r=10 puts effective dt near 15 s, inside the observed (1, 30] s
critical band.

INSTRUMENT DEFINITIONS ARE IMPORTED, NOT RETYPED. I1, I2 and every constant
come from scripts/generality_sweep.py (Phase 8, frozen). A6 and T3 come from
heart_guidelines, driven through the canonical replay loop of
scripts/nonuniform_replay.py. Nothing is tuned in this file.

Conditions (all three pre-registered; B1 primary):
  B1  sampled observation  -- monitor ingests every r-th action; elapsed
                              between observations = r*dt. Evidence AND decay
                              both change. (The Hua-et-al. cost model.)
  B2  sampled evaluation   -- monitor ingests every action at dt; triggers
                              evaluated only on every r-th. Decomposes B1 into
                              evidence-loss vs decay-stretch.
  B3  sampled observation, -- as B1 but decay per observation is exp(-lam*dt),
      sample-time calibrated  not exp(-lam*r*dt). The constructive control:
                              re-basing onto the observation clock.

A6 and T3 are run under B1 only (pre-registered).

Outputs:
  data/swebench_pilot/BUDGET_CADENCE_REPORT.md
  data/swebench_pilot/budget_cadence_metrics.json
  data/swebench_pilot/fig_data/budget_cadence.csv

Run from repo root:  python scripts/budget_cadence_sweep.py
"""
from __future__ import annotations
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

# --- frozen Phase-8 instrument definitions, imported verbatim ---------------
from generality_sweep import (           # noqa: E402
    ORIG5, all_ids, error_stream,
    i1_series, i1_level_metrics, i1_edge_fires, i2_fires,
    LAMBDA, STEP, LEVEL, REARM, CUSUM_K, CUSUM_H,
    PERSIST_DROP, DT_GRID as FROZEN_DT_GRID,
)

# --- frozen engine-side machinery ------------------------------------------
from heart_core.engine import EmotionEngine                              # noqa: E402
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter         # noqa: E402
from heart_adapters.claude_code.trajectory import parse_trajectory_file  # noqa: E402
from heart_guidelines.guidelines_engine import GuidelinesEngine          # noqa: E402
from heart_guidelines.state_history import StateHistory, HistoryEntry    # noqa: E402
from heart_guidelines.cooldown import CooldownGuidelines                 # noqa: E402
from heart_guidelines.triggers import trigger_sustained_frustration      # noqa: E402

PILOT_DIR = Path("data/swebench_pilot")
FIG_DIR = PILOT_DIR / "fig_data"

# Pre-registered sweep axes.
R_GRID = [1, 2, 5, 10, 20, 50]
MEASURED_DT = [1.53, 2.33]                      # Paper 2 pooled median, p90
DT_ALL = sorted(set([float(d) for d in FROZEN_DT_GRID] + MEASURED_DT))
CADENCE = 1.53                                  # the measured-cadence point
ENGINE_MAX_OFFSETS = 5                          # pre-registered offset cap for A6/T3
T3_BOUND = 3                                    # carried from H6/H9
H14D_MIN_FLIPS = 11                             # >= 11/20, pre-registered


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(not a git repo)"


def short(t: str) -> str:
    return t.replace("astropy__astropy-", "astropy-").replace("django__django-", "django-")


def traj_path(tid: str) -> Path:
    p = PILOT_DIR / f"{tid}.json"
    return p if p.exists() else PILOT_DIR / "batch2" / f"{tid}.json"


def subsample(seq: List, r: int, offset: int) -> List:
    return seq[offset::r]


def persistence(series: List[float]) -> Tuple[Optional[int], float, bool]:
    """(first_crossing_index, post-crossing persistence %, crossed?) over the
    monitor's OWN observation sequence -- the frozen Phase-5/8 definition."""
    first = next((i for i, s in enumerate(series) if s >= LEVEL), None)
    if first is None:
        return None, 0.0, False
    post = series[first:]
    return first, 100.0 * sum(1 for s in post if s >= LEVEL) / len(post), True


# ---------------------------------------------------------------------------
# I1 / I2 under the three budget conditions. All series come from the frozen
# Phase-8 functions; only the stream and the elapsed-time argument differ.
# ---------------------------------------------------------------------------
def i1_under(condition: str, errors: List[int], r: int, offset: int,
             dt: float) -> Tuple[List[float], List[int]]:
    """Returns (series the monitor sees, indices at which it may fire)."""
    if condition == "B1":
        sub = subsample(errors, r, offset)
        return i1_series(sub, r * dt), list(range(len(sub)))
    if condition == "B3":
        sub = subsample(errors, r, offset)
        return i1_series(sub, dt), list(range(len(sub)))
    if condition == "B2":
        full = i1_series(errors, dt)
        return full, list(range(offset, len(full), r))
    raise ValueError(condition)


def i1_metrics(condition: str, errors: List[int], r: int, offset: int,
               dt: float) -> Dict[str, Any]:
    series, eval_idx = i1_under(condition, errors, r, offset, dt)
    seen = [series[i] for i in eval_idx]
    first, persist, crossed = persistence(seen)
    edge = i1_edge_fires(seen)
    return {
        "n_obs": len(seen),
        "fire_count": sum(1 for s in seen if s >= LEVEL),
        "first_cross": first,
        "persist": persist,
        "crossed": crossed,
        "edge_fires": len(edge),
        "max_s": max(seen) if seen else 0.0,
        "degenerate": len(seen) < 2,
    }


def i2_metrics(condition: str, errors: List[int], r: int, offset: int,
               dt: float) -> Dict[str, Any]:
    if condition in ("B1", "B3"):
        sub = subsample(errors, r, offset)
        fires = i2_fires(sub, dt)
        n_obs = len(sub)
    elif condition == "B2":
        allowed = set(range(offset, len(errors), r))
        fires = [i for i in i2_fires(errors, dt) if i in allowed]
        n_obs = len(allowed)
    else:
        raise ValueError(condition)
    return {"n_obs": n_obs, "fire_count": len(fires), "fires": tuple(fires),
            "degenerate": n_obs < 2}


def critical_interval(cells: Dict[float, float]) -> Tuple[float, float]:
    """Smallest FROZEN-GRID dt whose persistence < 50%; interval = (prev, dt].
    Restricted to the frozen grid so it stays comparable to Phases 5 and 8."""
    for i, dt in enumerate(FROZEN_DT_GRID):
        if cells.get(float(dt), 0.0) < PERSIST_DROP:
            return (float(FROZEN_DT_GRID[i - 1]) if i > 0 else 0.0, float(dt))
    return (600.0, math.inf)


def label_interval(iv: Tuple[float, float]) -> str:
    return "never" if iv[1] == math.inf else f"({iv[0]:.0f}, {iv[1]:.0f}]"


# ---------------------------------------------------------------------------
# A6 / T3 under B1: canonical replay loop (identical order to
# scripts/nonuniform_replay.py), with only the observed actions ingested.
# ---------------------------------------------------------------------------
_EVENT_CACHE: Dict[str, list] = {}


def get_events(tid: str):
    if tid not in _EVENT_CACHE:
        _EVENT_CACHE[tid] = parse_trajectory_file(traj_path(tid))
    return _EVENT_CACHE[tid]


def replay_budget_b1(tid: str, r: int, offset: int, dt: float) -> Dict[str, Any]:
    events = subsample(get_events(tid), r, offset)
    engine = EmotionEngine()
    adapter = ClaudeCodeAdapter(engine)
    cooldown = CooldownGuidelines(GuidelinesEngine())
    history = StateHistory(max_size=10)

    gap = r * dt          # elapsed wall-clock between successive observations
    frust: List[float] = []
    a6 = t3 = 0

    for idx, event in enumerate(events):
        if idx >= 1 and gap > 0:
            engine._tick_decay(gap)

        adapter.observe(event)
        vector = {k: float(v) for k, v in engine.get_emotion_vector().items()}
        reflective = bool(engine.get_state().get("reflective", False))

        history.append(HistoryEntry(
            action_index=idx, tool_name=event.tool_name,
            tool_args=event.tool_args or {}, state=vector,
            reflective_flag=reflective, has_error=event.has_error(),
            rules_fired=0, reasoning_text=event.reasoning_text or "",
        ))
        context = {"reflective_flag": reflective, "history": history}

        if trigger_sustained_frustration(vector, context):
            a6 += 1
        for f in cooldown.evaluate(vector, context, action_index=idx):
            if f["trigger"] == "saturation_entry" and not f["suppressed"]:
                t3 += 1
        frust.append(vector["frustration"])

    first, persist, crossed = persistence(frust)
    crossings = sum(1 for i in range(1, len(frust))
                    if frust[i - 1] < LEVEL <= frust[i])
    if frust and frust[0] >= LEVEL:
        crossings += 1
    return {"n_obs": len(frust), "a6": a6, "t3": t3, "crossed": crossed,
            "persist": persist, "crossings": crossings,
            "degenerate": len(frust) < 2}


def med_mm(vals: List[float]) -> str:
    if not vals:
        return "-"
    m, lo, hi = statistics.median(vals), min(vals), max(vals)
    return f"{m:.0f}" if lo == hi else f"{m:.0f} [{lo:.0f}-{hi:.0f}]"


# ---------------------------------------------------------------------------
def main() -> None:
    if not PILOT_DIR.exists():
        sys.stderr.write("run from repo root\n")
        sys.exit(2)
    FIG_DIR.mkdir(exist_ok=True)

    ids = all_ids()
    streams = {t: error_stream(t) for t in ids}

    out: List[str] = []
    w = out.append
    w("# Monitoring budget x cadence (Phase B)")
    w("")
    w(f"Tree commit: `{git_sha()}`. Pre-registered: "
      f"`PREREGISTRATION_PHASE9.md` §2, committed before this script ran. "
      f"No new agent runs; 20 frozen error streams. Instrument definitions "
      f"imported verbatim from `scripts/generality_sweep.py` (Phase 8): "
      f"I1 lambda=ln2/150, step {STEP}, level {LEVEL}, re-arm {REARM}; "
      f"I2 k={CUSUM_K}, h={CUSUM_H}. Nothing tuned.")
    w("")
    w(f"Sweep: r in {R_GRID} x dt in {[f'{d:g}' for d in DT_ALL]} s "
      f"(frozen grid plus the two pre-registered measured-cadence points "
      f"{MEASURED_DT}). Offsets: all r for I1/I2, "
      f"min(r,{ENGINE_MAX_OFFSETS}) for A6/T3.")
    w("")

    # --- assumption re-check ------------------------------------------------
    w("## Assumption re-check: `has_error` is dt-invariant")
    w("")
    ok_inv = True
    for t in ("astropy__astropy-13398", "astropy__astropy-13033"):
        ref = streams[t]
        for dtv in FROZEN_DT_GRID:
            p = PILOT_DIR / f"fullstate_dt{int(dtv)}_{t}.json"
            got = [1 if e["has_error"] else 0
                   for e in json.loads(p.read_text(encoding="utf-8"))["timeline"]]
            ok_inv = ok_inv and (got == ref)
    w(f"Checked across all {len(FROZEN_DT_GRID)} dt-variant fullstate files for "
      f"astropy-13398 and astropy-13033: **{'PASS' if ok_inv else 'FAIL'}** "
      f"(dt does not change which actions error). Same check as Phase 8.")
    w("")

    metrics: Dict[str, Any] = {"tree_commit": git_sha(), "r_grid": R_GRID,
                               "dt_all": DT_ALL, "cells": {}}

    # ================= H14c: the cliff is a change of variable ==============
    w("## H14c — is the cliff exactly a change of variable?")
    w("")
    w("For every (trajectory, r, dt, offset), I1 under B1 must be **bitwise "
      "identical** to the frozen Phase-8 `i1_series` evaluated at "
      "`dt' = r*dt` on the offset-subsampled stream. This is an identity, not "
      "an empirical claim; a failure is a bug.")
    w("")
    h14c_fail = []
    for t in ids:
        for r in R_GRID:
            for off in range(r):
                for dt in DT_ALL:
                    sub = subsample(streams[t], r, off)
                    a, _ = i1_under("B1", streams[t], r, off, dt)
                    b = i1_series(sub, r * dt)
                    if a != b:
                        h14c_fail.append((short(t), r, off, dt))
    w(f"Cells checked: {len(ids)} trajectories x {sum(R_GRID)} (r, offset) pairs "
      f"x {len(DT_ALL)} dt. **Mismatches: {len(h14c_fail)}**"
      + ("" if not h14c_fail else f" -- {h14c_fail[:10]}"))
    w("")
    if not h14c_fail:
        w("**H14c holds exactly.** Budget r and cadence dt enter I1 only through "
          "the product `r*dt`. A monitoring-budget decision and a cadence change "
          "are, for this instrument, *the same intervention*: the effective "
          "time constant a wall-clock monitor experiences is set jointly by how "
          "fast the agent acts and how much of its behaviour anyone can afford "
          "to look at.")
    w("")

    # ================= I1 level under B1 ====================================
    w("## Table 1 — I1 level trigger under B1 (sampled observation)")
    w("")
    w("Median across offsets; `x` marks cells where the subsampled stream has "
      "fewer than 2 observations (degenerate, reported not fixed).")
    w("")
    header = "| r | " + " | ".join(f"dt={d:g}" for d in DT_ALL) + " |"
    w(header)
    w("|" + "---|" * (len(DT_ALL) + 1))
    i1_persist: Dict[Tuple[str, int, str], Dict[float, float]] = {}
    for r in R_GRID:
        cells = []
        for dt in DT_ALL:
            per_traj = []
            for t in ids:
                vals = [i1_metrics("B1", streams[t], r, o, dt) for o in range(r)]
                nd = [v for v in vals if not v["degenerate"]]
                use = nd or vals
                p = statistics.median([v["persist"] for v in use])
                per_traj.append(p)
                i1_persist.setdefault((t, r, "B1"), {})[dt] = p
            allde = all(i1_metrics("B1", streams[t], r, 0, dt)["degenerate"] for t in ids)
            cells.append("x" if allde else f"{statistics.median(per_traj):.0f}")
        w(f"| {r} | " + " | ".join(cells) + " |")
    w("")
    w("Cell = median across trajectories of median-across-offsets "
      "post-first-crossing persistence (%). The frozen regime rule is "
      f"persistence < {PERSIST_DROP:.0f}% ⇒ the monitor has left the alarm "
      f"regime.")
    w("")

    # ================= critical intervals shift as 1/r ======================
    w("## Table 2 — I1 critical interval vs budget (B1)")
    w("")
    w("| Trajectory | " + " | ".join(f"r={r}" for r in R_GRID) + " |")
    w("|" + "---|" * (len(R_GRID) + 1))
    crit: Dict[Tuple[str, int], Tuple[float, float]] = {}
    for t in ids:
        row = []
        for r in R_GRID:
            crit[(t, r)] = critical_interval(i1_persist[(t, r, "B1")])
            row.append(label_interval(crit[(t, r)]))
        w(f"| {short(t)} | " + " | ".join(row) + " |")
    w("")
    w("Pre-registered expectation (H14c corollary): the interval at budget r is "
      "the r=1 interval divided by r, to grid resolution.")
    w("")

    # ================= H14d: regime flip at measured cadence ================
    w("## Table 3 — H14d: regime flip at the measured cadence "
      f"(dt = {CADENCE} s)")
    w("")
    w("| Trajectory | " + " | ".join(f"r={r}" for r in R_GRID)
      + " | flips by r=10? |")
    w("|" + "---|" * (len(R_GRID) + 2))
    alarm_at_r1 = []
    flipped = []
    for t in ids:
        row, states = [], {}
        for r in R_GRID:
            vals = [i1_metrics("B1", streams[t], r, o, CADENCE) for o in range(r)]
            nd = [v for v in vals if not v["degenerate"]] or vals
            p = statistics.median([v["persist"] for v in nd])
            c = statistics.median([1.0 if v["crossed"] else 0.0 for v in nd]) >= 0.5
            states[r] = (p, c)
            row.append(f"{p:.0f}" + ("" if c else "*"))
        in_alarm_1 = states[1][1] and states[1][0] >= PERSIST_DROP
        left_10 = not (states[10][1] and states[10][0] >= PERSIST_DROP)
        if in_alarm_1:
            alarm_at_r1.append(t)
            if left_10:
                flipped.append(t)
        verdict = "-" if not in_alarm_1 else ("YES" if left_10 else "no")
        w(f"| {short(t)} | " + " | ".join(row) + f" | {verdict} |")
    w("")
    w("Persistence %; `*` = never crossed 0.7 at all.")
    w("")
    h14d = len(flipped) >= H14D_MIN_FLIPS
    w(f"In the alarm regime at r=1: **{len(alarm_at_r1)}/20**. "
      f"Left it by r=10: **{len(flipped)}/20** "
      f"(pre-registered bar: >= {H14D_MIN_FLIPS}/20).")
    w("")

    # ================= H14a / H14b: I2 ======================================
    w("## Table 4 — H14a / H14b: sample-time CUSUM under budget")
    w("")
    w("| Trajectory | dt-invariant at every r? | fire count by r "
      f"({', '.join(str(r) for r in R_GRID)}) | non-increasing in r? |")
    w("|---|---|---|---|")
    h14a = True
    h14b_viol = []
    for t in ids:
        inv = True
        for r in R_GRID:
            for off in range(r):
                ref = i2_metrics("B1", streams[t], r, off, DT_ALL[0])["fires"]
                for dt in DT_ALL:
                    if i2_metrics("B1", streams[t], r, off, dt)["fires"] != ref:
                        inv = False
        h14a = h14a and inv
        counts = []
        for r in R_GRID:
            vals = [i2_metrics("B1", streams[t], r, o, CADENCE)["fire_count"]
                    for o in range(r)]
            counts.append(statistics.median(vals))
        mono = all(counts[i + 1] <= counts[i] + 1e-9 for i in range(len(counts) - 1))
        if not mono:
            h14b_viol.append((short(t), counts))
        w(f"| {short(t)} | {'PASS' if inv else 'FAIL'} | "
          f"{', '.join(f'{c:.0f}' for c in counts)} | "
          f"{'yes' if mono else 'NO'} |")
    w("")
    w("Left column is H14a (exact dt-invariance, preserved at every budget). "
      "Right column is H14b (budget degrades I2 along a sensitivity axis, "
      "never across a regime boundary). I2 has no critical interval at any r "
      "because it never reads a clock.")
    w("")

    # ================= H14e: A6 / T3 ========================================
    w("## Table 5 — H14e: A6 and T3 under B1 (engine replay)")
    w("")
    w("| r | A6 fires (med [min-max]) | T3 net (max) | trajectories in alarm | "
      "critical interval, median |")
    w("|---|---|---|---|---|")
    a6t3: Dict[Tuple[str, int, float], Dict] = {}
    t3_max_overall = 0
    for r in R_GRID:
        offs = list(range(min(r, ENGINE_MAX_OFFSETS)))
        a6v, t3v, alarm = [], [], 0
        per_traj_crit = []
        for t in ids:
            cells = {}
            for dt in DT_ALL:
                res = [replay_budget_b1(t, r, o, dt) for o in offs]
                nd = [x for x in res if not x["degenerate"]] or res
                cells[dt] = statistics.median([x["persist"] for x in nd])
                for x in nd:
                    a6t3[(t, r, dt)] = x
                if abs(dt - CADENCE) < 1e-9:
                    a6v.append(statistics.median([x["a6"] for x in nd]))
                    t3v.append(max(x["t3"] for x in nd))
                    if statistics.median([1.0 if x["crossed"] else 0.0
                                          for x in nd]) >= 0.5:
                        alarm += 1
            per_traj_crit.append(critical_interval(cells)[1])
        t3_max_overall = max(t3_max_overall, max(t3v) if t3v else 0)
        finite = [c for c in per_traj_crit if c != math.inf]
        medc = f"{statistics.median(finite):.0f}" if finite else "never"
        w(f"| {r} | {med_mm(a6v)} | {max(t3v) if t3v else 0} | {alarm}/20 | "
          f"{medc} |")
    w("")
    w(f"A6 and alarm counts evaluated at the measured cadence dt = {CADENCE} s; "
      f"critical interval computed over the frozen grid. T3 bound carried from "
      f"H6/H9 is <= {T3_BOUND}.")
    w("")

    # ================= B1 vs B2 vs B3 decomposition =========================
    w("## Table 6 — decomposing the budget effect (I1, dt = "
      f"{CADENCE} s)")
    w("")
    w("| r | B1 sampled observation | B2 sampled evaluation | "
      "B3 sample-time calibrated |")
    w("|---|---|---|---|")
    for r in R_GRID:
        row = []
        for cond in ("B1", "B2", "B3"):
            vals = []
            for t in ids:
                per_off = [i1_metrics(cond, streams[t], r, o, CADENCE)
                           for o in range(r)]
                nd = [v for v in per_off if not v["degenerate"]] or per_off
                vals.append(statistics.median([v["persist"] for v in nd]))
            row.append(f"{statistics.median(vals):.0f}")
        w(f"| {r} | " + " | ".join(row) + " |")
    w("")
    w("Median-across-trajectories persistence (%). B1 changes evidence **and** "
      "decay; B2 changes neither (only how often the trigger is checked); B3 "
      "changes evidence only, because its decay is re-based onto the "
      "observation clock. The B1-vs-B3 gap is the part of the budget effect "
      "attributable purely to **wall-clock calibration** -- and it is the part "
      "a monitor author can remove without touching a threshold.")
    w("")

    # ================= scorecard ============================================
    w("## H14 scorecard")
    w("")
    h14b = not h14b_viol
    rows = [
        ("H14a  I2 dt-invariant at every r", h14a,
         "exact invariance preserved under budget"
         if h14a else "FAILURE IS A BUG -- sample-time CUSUM cannot read a clock"),
        ("H14b  I2 fire count non-increasing in r", h14b,
         "budget degrades I2 quantitatively" if h14b else f"violations: {h14b_viol}"),
        ("H14c  I1 under B1 == i1_series(sub, r*dt)", not h14c_fail,
         "budget and cadence are the same knob" if not h14c_fail
         else f"{len(h14c_fail)} mismatches -- BUG"),
        (f"H14d  >= {H14D_MIN_FLIPS}/20 leave alarm regime by r=10 at {CADENCE}s",
         h14d, f"{len(flipped)}/20 flipped (of {len(alarm_at_r1)}/20 in alarm at r=1)"),
        (f"H14e  T3 net <= {T3_BOUND} everywhere", t3_max_overall <= T3_BOUND,
         f"max T3 net observed = {t3_max_overall}"),
    ]
    for name, ok, note in rows:
        w(f"- **{name}** -> {'SUPPORTED' if ok else 'NOT SUPPORTED'} ({note})")
    w("")

    # ================= figure data ==========================================
    lines = ["condition,r,dt,effective_dt,median_persist,median_fire_count"]
    for cond in ("B1", "B2", "B3"):
        for r in R_GRID:
            for dt in DT_ALL:
                ps, fs = [], []
                for t in ids:
                    per_off = [i1_metrics(cond, streams[t], r, o, dt)
                               for o in range(r)]
                    nd = [v for v in per_off if not v["degenerate"]] or per_off
                    ps.append(statistics.median([v["persist"] for v in nd]))
                    fs.append(statistics.median([v["fire_count"] for v in nd]))
                eff = r * dt if cond in ("B1",) else dt
                lines.append(f"{cond},{r},{dt:g},{eff:g},"
                             f"{statistics.median(ps):.2f},"
                             f"{statistics.median(fs):.2f}")
    (FIG_DIR / "budget_cadence.csv").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8")

    metrics["cells"] = {
        f"{t}|{r}|{dt:g}": {
            "i1_b1": i1_metrics("B1", streams[t], r, 0, dt),
            "i2_b1": {k: v for k, v in i2_metrics("B1", streams[t], r, 0, dt).items()
                      if k != "fires"},
        }
        for t in ids for r in R_GRID for dt in DT_ALL
    }
    metrics["h14"] = {"a": h14a, "b": h14b, "c": not h14c_fail, "d": h14d,
                      "e": t3_max_overall <= T3_BOUND,
                      "flipped": [short(t) for t in flipped],
                      "alarm_at_r1": [short(t) for t in alarm_at_r1],
                      "t3_max": t3_max_overall}
    (PILOT_DIR / "budget_cadence_metrics.json").write_text(
        json.dumps(metrics, indent=1), encoding="utf-8")

    report = "\n".join(out)
    (PILOT_DIR / "BUDGET_CADENCE_REPORT.md").write_text(report, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)
    print(f"\nsaved: {PILOT_DIR / 'BUDGET_CADENCE_REPORT.md'}")
    print(f"saved: {PILOT_DIR / 'budget_cadence_metrics.json'}")
    print(f"saved: {FIG_DIR / 'budget_cadence.csv'}")


if __name__ == "__main__":
    main()
