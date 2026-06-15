"""Phase 5 Tasks 2-4: scale analysis over ~20 trajectories.

Pure post-processing of the fullstate/saturation artifacts (no replays here).
Produces data/swebench_pilot/SCALE_REPORT.md and fig_data/*_n20.csv, the
exploratory pre-saturation r correction, and the consistency assertions.

Run from repo root.
"""
from __future__ import annotations
import glob
import json
import math
import os
import sys
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PILOT_DIR = Path("data/swebench_pilot")
FIG_DIR = PILOT_DIR / "fig_data"

ORIG5 = [
    "astropy__astropy-12907", "astropy__astropy-13033", "astropy__astropy-13236",
    "astropy__astropy-13398", "astropy__astropy-13453",
]
DT_GRID = [0, 1, 5, 15, 30, 60, 150, 300, 600]
FRUST_HI = 0.7
B = 0.10
T_HALF = 150.0
LAMBDA = math.log(2.0) / T_HALF
ELEVATION = FRUST_HI - B  # 0.6
NEG_5 = ("frustration", "anger", "fear", "confusion", "vengeance")
PERSIST_HOLD = 90.0
PERSIST_DROP = 50.0

# Phase 1-4 recorded values for the original 5 (Task 4a hard assertions).
PHASE14_SATURATION = {
    # traj: (n, first_cross_dt0, sf_count, sva_count, hc_count)
    "astropy__astropy-12907": (28, 17, 11, 12, 11),
    "astropy__astropy-13033": (59, 12, 47, 49, 48),
    "astropy__astropy-13236": (44, 21, 23, 30, 17),
    "astropy__astropy-13398": (56, 15, 41, 42, 42),
    "astropy__astropy-13453": (31, 13, 18, 18, 18),
}
PHASE14_CRIT = {  # observed critical-dt point (DT_SWEEP_REPORT.md)
    "astropy__astropy-12907": 15, "astropy__astropy-13033": 30,
    "astropy__astropy-13236": 30, "astropy__astropy-13398": 5,
    "astropy__astropy-13453": 30,
}


def _check_cwd():
    if not PILOT_DIR.exists():
        sys.stderr.write("run from repo root\n"); sys.exit(2)


def all_ids() -> List[str]:
    batch2 = sorted(os.path.basename(f)[:-5]
                    for f in glob.glob(str(PILOT_DIR / "batch2" / "*.json")))
    return ORIG5 + batch2


def short(t):
    return t.replace("astropy__astropy-", "astropy-").replace("django__django-", "django-")


def load_fullstate(traj, dt):
    p = PILOT_DIR / f"fullstate_dt{int(dt)}_{traj}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_saturation(traj):
    p = PILOT_DIR / f"saturation_{traj}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---- saturation metrics (Paper-1 style) from saturation_<traj>.json ----
def saturation_row(traj) -> Dict[str, Any]:
    d = load_saturation(traj)
    tl = d["timeline"]; n = len(tl)
    fc = next((e["action_index"] for e in tl if e["frustration"] >= FRUST_HI), None)
    if fc is None:
        persist = None
    else:
        post = [e for e in tl if e["action_index"] >= fc]
        persist = 100.0 * sum(1 for e in post if e["frustration"] >= FRUST_HI) / len(post)
    sf = sum(1 for e in tl if e["fires"]["sustained_frustration"])
    sva = sum(1 for e in tl if e["fires"]["same_valence_accumulation"])
    hc = sum(1 for e in tl if e["fires"]["high_confusion_no_reflection"])
    return {"traj": traj, "n": n, "first_cross": fc, "persist": persist,
            "sf": sf, "sva": sva, "hc": hc, "max_fr": max(e["frustration"] for e in tl)}


# ---- dt-sweep metrics from fullstate_dt<dt>_<traj>.json ----
def sweep_cell(traj, dt) -> Dict[str, Any]:
    art = load_fullstate(traj, dt)
    tl = art["timeline"]; n = len(tl)
    frust = [e["vector"]["frustration"] for e in tl]
    fc = next((i for i, f in enumerate(frust) if f >= FRUST_HI), None)
    persist = None
    if fc is not None:
        post = frust[fc:]
        persist = 100.0 * sum(1 for f in post if f >= FRUST_HI) / len(post)
    a6 = sum(1 for e in tl if any(f["trigger"] == "sustained_frustration"
                                  for f in e.get("guidelines_firings", [])))
    t3 = sum(1 for e in tl for f in e.get("transition_firings", [])
             if f["trigger"] == "saturation_entry" and not f["suppressed"])
    return {"n": n, "crosses": fc is not None, "persist": persist, "a6": a6, "t3": t3,
            "max_fr": max(frust)}


def critical_dt(traj) -> Tuple[str, Optional[int]]:
    """Smallest grid dt with persistence<50% (no-cross treated as 0). Returns
    (interval_label, crit_point)."""
    for dt in DT_GRID:
        c = sweep_cell(traj, dt)
        p = c["persist"] if (c["crosses"] and c["persist"] is not None) else 0.0
        if p < PERSIST_DROP:
            idx = DT_GRID.index(dt)
            low = DT_GRID[idx - 1] if idx > 0 else 0
            return f"({low}, {dt}]", dt
    return "never", None


# ---- zero-signal coverage from dt0 fullstate ----
def zero_signal(traj) -> Dict[str, Any]:
    art = load_fullstate(traj, 0)
    tl = art["timeline"]; n = len(tl)
    zeros = [len(e.get("signals_applied", [])) == 0 for e in tl]
    longest = cur = 0
    for z in zeros:
        cur = cur + 1 if z else 0
        longest = max(longest, cur)
    nz = sum(zeros)
    return {"n": n, "zero_pct": 100.0 * nz / n, "longest": longest}


# ---- r (original clamp-censored) and r_presat (exploratory) ----
def realized_frust_deltas(traj) -> List[float]:
    art = load_fullstate(traj, 0)
    return [e["vector"]["frustration"] - e["vector_post_decay"]["frustration"]
            for e in art["timeline"]]


def raw_requested_frust(traj) -> List[float]:
    """Raw rule-requested frustration deltas (signals_applied), per action."""
    art = load_fullstate(traj, 0)
    out = []
    for e in art["timeline"]:
        out.append(sum(s["delta"] for s in e.get("signals_applied", [])
                       if s["emotion"] == "frustration"))
    return out


def predict_dtcrit(r: float) -> Optional[float]:
    if r >= ELEVATION:
        return None
    return -(1.0 / LAMBDA) * math.log(1.0 - r / ELEVATION)


def r_original(traj) -> float:
    deltas = realized_frust_deltas(traj)
    pos = sum(d for d in deltas if d > 0)
    return pos / len(deltas)


def r_presaturation(traj) -> Tuple[float, int, bool]:
    """Mean realized positive frustration input over PRE-saturation region:
    actions before frustration first reaches 1.0 (the clamp). If it never
    reaches 1.0 at dt=0, use the whole trajectory. Returns (r, region_len,
    used_whole)."""
    art = load_fullstate(traj, 0)
    tl = art["timeline"]
    fr = [e["vector"]["frustration"] for e in tl]
    deltas = realized_frust_deltas(traj)
    first_clamp = next((i for i, f in enumerate(fr) if f >= 1.0), None)
    if first_clamp is None:
        region = deltas
        used_whole = True
    else:
        region = deltas[:first_clamp]  # actions strictly before clamp
        used_whole = False
    if not region:
        return 0.0, 0, used_whole
    pos = sum(d for d in region if d > 0)
    return pos / len(region), len(region), used_whole


def censoring_severity(traj) -> float:
    """Fraction of total RAW rule-requested frustration input that was lost to
    the clamp: 1 - (realized positive / raw-requested positive)."""
    raw = raw_requested_frust(traj)
    real = realized_frust_deltas(traj)
    raw_pos = sum(d for d in raw if d > 0)
    real_pos = sum(d for d in real if d > 0)
    if raw_pos <= 0:
        return 0.0
    return max(0.0, 1.0 - real_pos / raw_pos)


def event_rate(traj) -> float:
    art = load_fullstate(traj, 0)
    tl = art["timeline"]
    ev = sum(1 for e in tl if e.get("signals_applied"))
    return 100.0 * ev / len(tl)


def band(vals):
    s = sorted(v for v in vals if v is not None)
    if not s:
        return (None, None, None)
    return (min(s), statistics.median(s), max(s))


def main():
    _check_cwd()
    FIG_DIR.mkdir(exist_ok=True)
    ids = all_ids()

    # ---------- Task 4a: assert original 5 unchanged ----------
    assertions = []
    all_pass = True
    for t in ORIG5:
        sr = saturation_row(t)
        exp = PHASE14_SATURATION[t]
        got = (sr["n"], sr["first_cross"], sr["sf"], sr["sva"], sr["hc"])
        ok = (got == exp)
        all_pass = all_pass and ok
        assertions.append((t, exp, got, ok))
        # also critical-dt point
        _, crit = critical_dt(t)
        ok2 = (crit == PHASE14_CRIT[t])
        all_pass = all_pass and ok2
        assertions.append((t + " crit_dt", PHASE14_CRIT[t], crit, ok2))

    # ---------- gather per-trajectory ----------
    sat = {t: saturation_row(t) for t in ids}
    zs = {t: zero_signal(t) for t in ids}
    crit = {t: critical_dt(t) for t in ids}

    out = []
    w = out.append
    w("# Scale Report: ~20 trajectories (Phase 5)")
    w("")
    w(f"Expanded set: {len(ids)} trajectories (original 5 + 15 batch2 from the "
      "same public 20250514_aime_coder submission, selected a priori: first 15 "
      "alphabetical with 25-70 actions that parse cleanly; see "
      "`batch2/SKIP_LOG.md`). Engine, adapter, triggers, thresholds, and dt grid "
      "all unchanged. Pure re-run of the existing pipeline.")
    w("")

    # ---- Task 4a result up top ----
    w("## Consistency check (Task 4a): original 5 unchanged")
    w("")
    w("| item | expected | got | match |")
    w("|---|---|---|---|")
    for name, exp, got, ok in assertions:
        w(f"| {short(name)} | {exp} | {got} | {'PASS' if ok else 'FAIL'} |")
    w("")
    w(f"**{'All original-5 assertions PASS.' if all_pass else 'CONSISTENCY FAILURE.'}**")
    w("")

    # ---- saturation table ----
    w("## Saturation table (dt=0, all trajectories)")
    w("")
    w("| Trajectory | actions | first cross 0.7 | persistence % | A6 sf % | A6 sva % | A6 hc % | max frust |")
    w("|---|---|---|---|---|---|---|---|")
    for t in ids:
        s = sat[t]; n = s["n"]
        fc = "never" if s["first_cross"] is None else str(s["first_cross"])
        pr = f"{s['persist']:.0f}" if s["persist"] is not None else "-"
        w(f"| {short(t)} | {n} | {fc} | {pr} | {100*s['sf']/n:.0f} | "
          f"{100*s['sva']/n:.0f} | {100*s['hc']/n:.0f} | {s['max_fr']:.2f} |")
    w("")
    crossers = [t for t in ids if sat[t]["first_cross"] is not None]
    full_hold = [t for t in crossers if sat[t]["persist"] is not None and sat[t]["persist"] >= PERSIST_HOLD]
    w(f"Cross 0.7 at dt=0: **{len(crossers)}/{len(ids)}**. "
      f"Persistence >= {PERSIST_HOLD:.0f}% (trap fully holds at dt=0): "
      f"**{len(full_hold)}/{len(ids)}**.")
    w("")

    # ---- dt-sweep persistence summary ----
    w("## dt-sweep persistence summary (all trajectories)")
    w("")
    w("| dt (s) | trajectories crossing 0.7 | mean persistence % (crossers) | # trap holds (>=90%) |")
    w("|---|---|---|---|")
    for dt in DT_GRID:
        cells = [sweep_cell(t, dt) for t in ids]
        cr = [c for c in cells if c["crosses"] and c["persist"] is not None]
        mp = f"{statistics.mean([c['persist'] for c in cr]):.1f}" if cr else "-"
        holds = sum(1 for c in cr if c["persist"] >= PERSIST_HOLD)
        w(f"| {dt} | {len(cr)}/{len(ids)} | {mp} | {holds} |")
    w("")

    # ---- per-trajectory critical-dt intervals ----
    w("## Per-trajectory critical-dt interval")
    w("")
    w("| Trajectory | critical dt interval (s) |")
    w("|---|---|")
    for t in ids:
        w(f"| {short(t)} | {crit[t][0]} |")
    w("")

    # ---- A6 / T3 vs dt aggregates with bands ----
    w("## A6 and T3 fire counts vs dt (aggregate bands over all trajectories)")
    w("")
    w("min / median / max fire count across the trajectories at each dt.")
    w("")
    w("| dt (s) | A6 sf min/med/max | T3 net min/med/max |")
    w("|---|---|---|")
    for dt in DT_GRID:
        cells = [sweep_cell(t, dt) for t in ids]
        a6b = band([c["a6"] for c in cells])
        t3b = band([c["t3"] for c in cells])
        w(f"| {dt} | {a6b[0]}/{a6b[1]:.0f}/{a6b[2]} | {t3b[0]}/{t3b[1]:.0f}/{t3b[2]} |")
    w("")

    # ---- zero-signal coverage ----
    w("## Zero-signal coverage (dt=0)")
    w("")
    w("| Trajectory | actions | zero-signal % | longest zero run |")
    w("|---|---|---|---|")
    for t in ids:
        z = zs[t]
        w(f"| {short(t)} | {z['n']} | {z['zero_pct']:.1f} | {z['longest']} |")
    w("")

    # ---------- Task 3: exploratory correction ----------
    w("## EXPLORATORY: pre-saturation r correction (Task 3)")
    w("")
    w("**This correction was specified AFTER observing the original model's "
      "residuals (Phase 4a).** It is exploratory, not pre-registered. The "
      "original `r` averages realized frustration input over ALL actions, but "
      "once frustration hits the 1.0 clamp the realized input is censored to 0, "
      "deflating `r`. The corrected `r_presat` averages realized positive input "
      "over the PRE-saturation region only (actions before frustration first "
      "reaches 1.0; whole trajectory if it never clamps). dt_crit uses the same "
      "fixed formula `-(1/lambda) ln(1 - r/0.6)`.")
    w("")
    w("| Trajectory | r (orig) | dt_crit orig | r_presat | dt_crit corr | obs interval | orig inside? | corr inside? | clamp-censored input % |")
    w("|---|---|---|---|---|---|---|---|---|")
    corr_rows = []
    for t in ids:
        ro = r_original(t)
        rp, reglen, whole = r_presaturation(t)
        do = predict_dtcrit(ro)
        dc = predict_dtcrit(rp)
        interval, _ = crit[t]
        # interval inside test
        def inside(pred):
            if interval == "never":
                return pred is None
            if pred is None:
                return False
            lo, hi = interval.strip("(]").split(", ")
            return float(lo) < pred <= float(hi)
        cens = censoring_severity(t)
        corr_rows.append((t, ro, do, rp, dc, interval, inside(do), inside(dc), cens, whole))
        do_s = "inf" if do is None else f"{do:.1f}"
        dc_s = "inf" if dc is None else f"{dc:.1f}"
        w(f"| {short(t)} | {ro:.4f} | {do_s} | {rp:.4f} | {dc_s} | {interval} | "
          f"{'yes' if inside(do) else 'no'} | {'yes' if inside(dc) else 'no'} | "
          f"{100*cens:.0f}%{'*' if whole else ''} |")
    w("")
    n_orig_in = sum(1 for r_ in corr_rows if r_[6])
    n_corr_in = sum(1 for r_ in corr_rows if r_[7])
    w(f"Predictions inside the observed interval: original **{n_orig_in}/{len(ids)}**, "
      f"corrected **{n_corr_in}/{len(ids)}**. `*` = no clamp reached, whole "
      f"trajectory used for r_presat.")
    w("")

    # ---------- Task 4b: distribution check ----------
    w("## Distribution check (Task 4b): batch2 vs original 5")
    w("")
    batch2 = [t for t in ids if t not in ORIG5]
    def dist_block(group, label):
        ns = [sat[t]["n"] for t in group]
        zps = [zs[t]["zero_pct"] for t in group]
        ers = [event_rate(t) for t in group]
        nb = band(ns); zb = band(zps); eb = band(ers)
        return (f"| {label} | {len(group)} | {nb[0]}/{nb[1]:.0f}/{nb[2]} | "
                f"{zb[0]:.0f}/{zb[1]:.0f}/{zb[2]:.0f} | {eb[0]:.0f}/{eb[1]:.0f}/{eb[2]:.0f} |")
    w("min/median/max per group. event-rate = % of actions with >=1 signal.")
    w("")
    w("| group | n | action-count | zero-signal % | event-rate % |")
    w("|---|---|---|---|---|")
    w(dist_block(ORIG5, "original 5"))
    w(dist_block(batch2, "batch2 (15)"))
    w(dist_block(ids, "all 20"))
    w("")
    w("No reweighting applied; distributions reported as-is to show whether the "
      "pilot 5 were representative of the broader set.")
    w("")

    report = "\n".join(out)
    (PILOT_DIR / "SCALE_REPORT.md").write_text(report, encoding="utf-8")

    # ---------- fig_data _n20 CSVs (new files; never overwrite n5) ----------
    # (a) frustration curves at dt {0,5,15,60}
    lines = ["trajectory,dt,action_index,frustration"]
    for t in ids:
        for dt in [0, 5, 15, 60]:
            art = load_fullstate(t, dt)
            if art is None:
                continue
            for e in art["timeline"]:
                lines.append(f"{short(t)},{dt},{e['action_index']},{e['vector']['frustration']:.6f}")
    (FIG_DIR / "frustration_curves_n20.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # (b) A6 and T3 net vs dt per trajectory
    lines = ["trajectory,dt,a6_sustained_frustration,t3_saturation_entry_net"]
    for t in ids:
        for dt in DT_GRID:
            c = sweep_cell(t, dt)
            lines.append(f"{short(t)},{dt},{c['a6']},{c['t3']}")
    (FIG_DIR / "fire_counts_vs_dt_n20.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # (c) aggregate bands vs dt
    lines = ["dt,a6_min,a6_med,a6_max,t3_min,t3_med,t3_max,n_crossers,mean_persist"]
    for dt in DT_GRID:
        cells = [sweep_cell(t, dt) for t in ids]
        a6b = band([c["a6"] for c in cells]); t3b = band([c["t3"] for c in cells])
        cr = [c for c in cells if c["crosses"] and c["persist"] is not None]
        mp = statistics.mean([c["persist"] for c in cr]) if cr else 0.0
        lines.append(f"{dt},{a6b[0]},{a6b[1]:.1f},{a6b[2]},{t3b[0]},{t3b[1]:.1f},{t3b[2]},{len(cr)},{mp:.2f}")
    (FIG_DIR / "dt_bands_n20.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print(f"\nsaved: {PILOT_DIR / 'SCALE_REPORT.md'}")
    print("fig_data: frustration_curves_n20.csv, fire_counts_vs_dt_n20.csv, dt_bands_n20.csv")
    print(f"\nTASK 4a ASSERTION: {'ALL PASS' if all_pass else 'FAILED'}")
    if not all_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
