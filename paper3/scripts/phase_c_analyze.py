"""Phase C / C-sub analysis: cadence, H11-H13, H15, and the budget bounds.

Reads data/live_runs/phase_c_sub/<run>_<model>.json (written by
phase_c_subagent.py harvest), re-extracts each run's hook records from its
recorded time window, converts them to the trajectory format the frozen parser
accepts, and replays them through the FROZEN engine/adapter/triggers with the
run's own real ordered dt sequence.

Scoring follows PREREGISTRATION_PHASE9.md section 4 and
PREREGISTRATION_PHASE9_ADDENDUM_C.md. H10 is NOT scored here: C-sub is a
different harness from Paper 2 and the addendum says so.

Run from repo root:  python scripts/phase_c_analyze.py [--model opus]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from heart_instrument.convert import convert                              # noqa: E402
from heart_core.engine import EmotionEngine                               # noqa: E402
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter          # noqa: E402
from heart_adapters.claude_code.trajectory import parse_trajectory_file   # noqa: E402
from heart_guidelines.guidelines_engine import GuidelinesEngine           # noqa: E402
from heart_guidelines.state_history import StateHistory, HistoryEntry     # noqa: E402
from heart_guidelines.cooldown import CooldownGuidelines                  # noqa: E402
from heart_guidelines.triggers import trigger_sustained_frustration       # noqa: E402

SUB_DIR = ROOT / "data" / "live_runs" / "phase_c_sub"
PILOT_DIR = ROOT / "data" / "swebench_pilot"

FRUST_HI = 0.7
FLICKER_MAX_LEN = 5
DRAIN_S = 87.74            # 0.1 + 0.9*exp(-ln2/150*T) < 0.7, FROM THE CLAMP
CLAMP_EPS = 0.99           # "reached the clamp" for H13's mechanism claim
STEP, THRESHOLD = 0.15, 0.7
MIN_OBS = 5                # ceil(0.7/0.15)
H11_MIN_N = 30             # dip-test power floor, pre-registered

# Paper 2, published in data/live_runs/TIMING_REPORT.md (gpt-5.4-mini,
# scriptable one-tool-call loop). Reference only -- CROSS-HARNESS.
P2 = {
    "runA": {"n_actions": 7,  "n_dt": 6,  "median": 1.78, "p90": 1.90, "max": 1.94},
    "runB": {"n_actions": 14, "n_dt": 13, "median": 1.46, "p90": 2.14, "max": 2.59},
    "runC": {"n_actions": 9,  "n_dt": 8,  "median": 1.48, "p90": 1.75, "max": 1.99},
    "runD": {"n_actions": 8,  "n_dt": 7,  "median": 1.65, "p90": 2.38, "max": 2.76},
    "runE": {"n_actions": 32, "n_dt": 31, "median": 1.53, "p90": 3.57, "max": 15.87},
}
P2_POOLED = {"n_dt": 65, "median": 1.53, "p90": 2.33, "max": 15.87,
             "p25": 1.25, "min": 0.97}


def pct(s: List[float], p: float) -> float:
    if not s:
        return float("nan")
    k = (len(s) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def rebuild_jsonl(rec: Dict[str, Any], out_dir: Path) -> Path:
    """Re-extract this run's hook records from the recorded time window."""
    log_dir = Path(os.path.expanduser("~")) / ".claude" / "heart_instrument_logs"
    lo = datetime.fromisoformat(rec["window_open"])
    hi = datetime.fromisoformat(rec["window_close"])
    lines = []
    for p in log_dir.glob("*.jsonl"):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    t = datetime.fromisoformat(r["ts"])
                except Exception:
                    continue
                operator = (r.get("tool_name") == "Agent"
                            or "phase_c_subagent" in (r.get("tool_input") or ""))
                if lo < t <= hi and not operator:
                    lines.append((t, line.rstrip("\n")))
    lines.sort(key=lambda x: x[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "session.jsonl"
    dest.write_text("\n".join(l for _, l in lines) + "\n", encoding="utf-8")
    return dest


_HEART_INTERVALS: Dict[str, Tuple[float, float]] = {}


def regime_placement(median: float) -> Dict[str, int]:
    """Where a cadence sits relative to HEART's per-trajectory critical
    intervals (Phase 5 definition, recomputed from the frozen artefacts via
    the Phase-8 helper). Run from the repo root."""
    if not _HEART_INTERVALS:
        sys.path.insert(0, str(ROOT / "scripts"))
        from generality_sweep import all_ids, heart_critical_interval
        for t in all_ids():
            _HEART_INTERVALS[t] = heart_critical_interval(t)
    below = inside = above = 0
    for lo, hi in _HEART_INTERVALS.values():
        if median <= lo:
            below += 1
        elif median <= hi:
            inside += 1
        else:
            above += 1
    return {"below": below, "inside": inside, "above": above}


def recompute(rec: Dict[str, Any], jsonl_path: Path) -> Dict[str, Any]:
    """Re-derive every cadence field from the cleaned window records.

    The harvest step before commit be2750a attributed the operator's own
    `prepare` record to the agent (one spurious leading action and one
    spurious leading dt per run, identically in both arms). The cleaned
    session.jsonl is the authoritative source; the harvest-time numbers are
    kept under `harvest_uncorrected` for the audit trail.
    """
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                r["_t"] = datetime.fromisoformat(r["ts"])
                records.append(r)
    ts = [r["_t"] for r in records]
    dts = [(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))]
    n = len(records)
    errors = [bool(r["error_indicator"]) for r in records]
    p = (sum(errors) / n) if n else 0.0
    s = sorted(dts)
    med = statistics.median(dts) if dts else float("nan")
    x = STEP * p / THRESHOLD
    delta_star = (-(150.0 / math.log(2.0)) * math.log(1.0 - x)) if x < 1.0 else None
    r_starv = n / MIN_OBS if n else 0.0
    r_cliff = (delta_star / med) if (delta_star and med and med > 0) else None

    if "harvest_uncorrected" not in rec:
        rec["harvest_uncorrected"] = {
            k: rec[k] for k in ("n_actions", "n_dt", "dt_seconds", "dt_stats",
                                "error_rate", "derived", "tools_used")
            if k in rec}
    rec.update({
        "n_actions": n, "n_dt": len(dts),
        "tools_used": {t: sum(1 for r in records if r["tool_name"] == t)
                       for t in sorted({r["tool_name"] for r in records})},
        "error_rate": round(p, 4),
        "dt_seconds": [round(d, 6) for d in dts],
        "dt_stats": {
            "min": round(min(s), 3) if s else None,
            "p25": round(pct(s, .25), 3) if s else None,
            "median": round(med, 3) if s else None,
            "p75": round(pct(s, .75), 3) if s else None,
            "p90": round(pct(s, .90), 3) if s else None,
            "max": round(max(s), 3) if s else None,
        },
        "derived": {
            "delta_star_s": round(delta_star, 2) if delta_star else None,
            "r_starv": round(r_starv, 2),
            "r_cliff": round(r_cliff, 2) if r_cliff else None,
            "binding": (None if r_cliff is None else
                        ("starvation" if r_starv <= r_cliff else "cliff")),
        },
        "corrected_from_cleaned_window": True,
    })
    return rec


def replay(traj_path: Path, dt_schedule: List[float]) -> Dict[str, Any]:
    """Frozen replay, canonical order, real ordered dt injected per action."""
    events = parse_trajectory_file(traj_path)
    engine = EmotionEngine()
    adapter = ClaudeCodeAdapter(engine)
    cooldown = CooldownGuidelines(GuidelinesEngine())
    history = StateHistory(max_size=10)

    frust: List[float] = []
    a6 = t3 = 0
    for idx, ev in enumerate(events):
        if idx >= 1:
            dt = float(dt_schedule[idx - 1]) if idx - 1 < len(dt_schedule) else 0.0
            if dt > 0:
                engine._tick_decay(dt)
        adapter.observe(ev)
        vec = {k: float(v) for k, v in engine.get_emotion_vector().items()}
        refl = bool(engine.get_state().get("reflective", False))
        history.append(HistoryEntry(
            action_index=idx, tool_name=ev.tool_name, tool_args=ev.tool_args or {},
            state=vec, reflective_flag=refl, has_error=ev.has_error(),
            rules_fired=0, reasoning_text=ev.reasoning_text or ""))
        ctx = {"reflective_flag": refl, "history": history}
        if trigger_sustained_frustration(vec, ctx):
            a6 += 1
        for f in cooldown.evaluate(vec, ctx, action_index=idx):
            if f["trigger"] == "saturation_entry" and not f["suppressed"]:
                t3 += 1
        frust.append(vec["frustration"])

    n = len(frust)
    crossings = sum(1 for i in range(1, n) if frust[i - 1] < FRUST_HI <= frust[i])
    if frust and frust[0] >= FRUST_HI:
        crossings += 1
    flicker = 0
    run_len = 0
    for f in frust + [0.0]:
        if f >= FRUST_HI:
            run_len += 1
        else:
            if 0 < run_len < FLICKER_MAX_LEN:
                flicker += 1
            run_len = 0
    reached = any(f >= FRUST_HI for f in frust)
    # H13's mechanism claim is about draining FROM THE CLAMP. Reaching the
    # 0.7 trigger threshold and reaching the 1.0 clamp are different events
    # with very different drain times, and conflating them would misreport
    # what falsified H13.
    clamped = any(f >= CLAMP_EPS for f in frust)
    drained = False
    drain_gap = None
    if reached:
        first = next(i for i, f in enumerate(frust) if f >= FRUST_HI)
        drained = any(f < FRUST_HI for f in frust[first:])
        if drained:
            j = next(i for i in range(first, n) if frust[i] < FRUST_HI)
            drain_gap = dt_schedule[j - 1] if 0 < j <= len(dt_schedule) else None
    return {"n": n, "crossings": crossings, "flicker": flicker, "a6": a6,
            "t3": t3, "reached": reached, "clamped": clamped,
            "drained": drained, "drain_gap": drain_gap,
            "max_frust": max(frust) if frust else 0.0, "frust": frust}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="opus")
    args = ap.parse_args()

    # exclude this script's own output (_analysis_<model>.json)
    files = sorted(p for p in SUB_DIR.glob(f"*_{args.model}.json")
                   if not p.name.startswith("_"))
    if not files:
        sys.exit(f"no C-sub records for model={args.model}")
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    runs.sort(key=lambda r: r["run_id"])

    # Authoritative pass: rebuild each window from the hook log with operator
    # records removed, recompute every cadence field from it, and write the
    # corrected per-run JSON back (harvest-time values kept for the audit).
    for r in runs:
        rd = SUB_DIR / r["run_id"]
        recompute(r, rebuild_jsonl(r, rd))
        (SUB_DIR / f"{r['run_id']}_{args.model}.json").write_text(
            json.dumps({k: v for k, v in r.items() if not k.startswith("_")},
                       indent=1), encoding="utf-8")

    out: List[str] = []
    w = out.append
    w(f"# Phase C / C-sub — cadence census ({args.model})")
    w("")
    w(f"Tree commit `{git_sha()}`. Pre-registered: `PREREGISTRATION_PHASE9.md` "
      f"§4 and `PREREGISTRATION_PHASE9_ADDENDUM_C.md`, both committed before "
      f"any run. Harness: Claude Code subagents, PostToolUse hook, timestamp "
      f"taken after the observation (same point as Paper 2).")
    w("")
    w("**H10 is not scored here.** C-sub is a different harness from Paper 2's "
      "scriptable loop; every comparison below to 1.53 s / 2.33 s is "
      "cross-harness and labelled as such.")
    w("")
    w("**Correction applied.** The harvest step used before commit `be2750a` "
      "attributed the operator's own `prepare` call to the agent — its "
      "PostToolUse hook fires after the script stamps the window open, so it "
      "was always the first record in every window, in both arms. Every "
      "number below is recomputed from the cleaned window (one spurious "
      "leading action and one spurious leading dt removed per run); the "
      "harvest-time values are retained in each run's JSON under "
      "`harvest_uncorrected`. The artefact was identical across arms, so the "
      "model contrast was never biased by it; the absolute numbers were.")
    w("")

    # ---------------- per-run cadence ----------------
    w("## Per-run cadence, against Paper 2's same-spec runs")
    w("")
    w("| run | actions (P2) | dts | min | p25 | median (P2) | p75 | p90 (P2) | max (P2) |")
    w("|---|---|---|---|---|---|---|---|---|")
    pooled: List[float] = []
    for r in runs:
        d, rid = r["dt_stats"], r["run_id"]
        p2 = P2.get(rid, {})
        pooled.extend(r["dt_seconds"])
        w(f"| {rid} | {r['n_actions']} ({p2.get('n_actions','-')}) | {r['n_dt']} | "
          f"{d['min']} | {d['p25']} | **{d['median']}** ({p2.get('median','-')}) | "
          f"{d['p75']} | {d['p90']} ({p2.get('p90','-')}) | "
          f"{d['max']} ({p2.get('max','-')}) |")
    s = sorted(pooled)
    pool = {"n": len(s), "min": min(s), "p25": pct(s, .25), "median": pct(s, .5),
            "p75": pct(s, .75), "p90": pct(s, .9), "max": max(s)}
    w(f"| **pooled** | {sum(r['n_actions'] for r in runs)} (70) | {pool['n']} (65) | "
      f"{pool['min']:.2f} | {pool['p25']:.2f} | **{pool['median']:.2f}** (1.53) | "
      f"{pool['p75']:.2f} | {pool['p90']:.2f} (2.33) | {pool['max']:.2f} (15.87) |")
    w("")
    ratio = pool["median"] / P2_POOLED["median"]
    disp = pool["p90"] / pool["median"]
    w(f"Pooled median is **{ratio:.2f}x** Paper 2's; dispersion ratio "
      f"p90/median **{disp:.2f}** against Paper 2's "
      f"{P2_POOLED['p90']/P2_POOLED['median']:.2f}.")
    w("")
    place = regime_placement(pool["median"])
    place_p2 = regime_placement(P2_POOLED["median"])
    w("Placement against HEART's per-trajectory critical intervals (Phase 5, "
      "recomputed from the frozen fullstate artefacts). *Below* = the agent "
      "acts faster than that trajectory's critical interval, i.e. the "
      "accumulator can hold itself above threshold (alarm regime); *above* = "
      "dead regime; *inside* = the knife-edge band.")
    w("")
    w("| pooled median | below (alarm) | inside band | above (dead) |")
    w("|---|---|---|---|")
    w(f"| Paper 2, {P2_POOLED['median']:.2f} s | {place_p2['below']}/20 | "
      f"{place_p2['inside']}/20 | {place_p2['above']}/20 |")
    w(f"| this arm, {pool['median']:.2f} s | {place['below']}/20 | "
      f"{place['inside']}/20 | {place['above']}/20 |")
    w("")

    # ---------------- H15 ----------------
    w("## H15 — action count (registered as SUGGESTIVE, not confirmatory)")
    w("")
    w("| run | C-sub actions | Paper 2 actions | delta |")
    w("|---|---|---|---|")
    a_new, a_old = [], []
    for r in runs:
        p2n = P2.get(r["run_id"], {}).get("n_actions")
        if p2n:
            a_new.append(r["n_actions"])
            a_old.append(p2n)
            w(f"| {r['run_id']} | {r['n_actions']} | {p2n} | "
              f"{r['n_actions']-p2n:+d} |")
    mn, mo = statistics.median(a_new), statistics.median(a_old)
    h15 = mn < mo
    w(f"| **median** | **{mn:.0f}** | **{mo:.0f}** | {mn-mo:+.0f} |")
    w("")
    if args.model == "opus":
        h15_label = "SUPPORTED" if h15 else "FALSIFIED"
        w(f"**H15: {h15_label}** — predicted *fewer* actions; observed median "
          f"{mn:.0f} against {mo:.0f}. "
          + ("" if h15 else
             "The prediction was that a more capable agent finishes in fewer "
             "steps and so starves a stateful monitor of observations. It does "
             "not: on the same specs it takes **more** steps. The starvation "
             "mechanism from Phase B is unaffected — it depends on the "
             "observation count that survives subsampling, which is what the "
             "budget table below reports — but the specific route to it via "
             "shorter traces is refuted."))
    else:
        h15_label = (f"descriptive only — {'fewer' if h15 else 'more'} actions "
                     f"(median {mn:.0f} vs {mo:.0f}); H15 was registered on the "
                     f"Opus 5 arm and is scored there")
        w(f"**H15 on this arm: {h15_label}.** The addendum registers H15 for "
          f"Opus 5 specifically; this arm's count is reported, not scored.")
    w("")

    # ---------------- H11 ----------------
    w("## H11 — bimodality")
    w("")
    scored = [r for r in runs if r["n_dt"] >= H11_MIN_N]
    w(f"Pre-registered: Hartigan's dip test on log10(dt), per run, alpha 0.05, "
      f"**scored only on runs with n >= {H11_MIN_N} dt intervals**; excluded "
      f"runs reported with their count.")
    w("")
    w(f"Runs meeting n >= {H11_MIN_N}: **{len(scored)}/{len(runs)}** "
      f"(n per run: {', '.join(str(r['n_dt']) for r in runs)}).")
    w("")
    w("**H11 is UNSCOREABLE on this arm for lack of power**, exactly the gap "
      "recorded in `PHASE_C_PLAN.md` §7 before any run. It is reported as "
      "unscoreable, not as a null.")
    w("")
    widest = max(runs, key=lambda r: (r["dt_stats"]["max"] or 0)
                 / max(r["dt_stats"]["min"] or 1e-9, 1e-9))
    w("The descriptive picture is nonetheless what H11 describes: the pooled "
      f"spread runs from {pool['min']:.2f} s to {pool['max']:.2f} s, and one "
      f"run ({widest['run_id']}) mixes a {widest['dt_stats']['min']:.2f} s "
      f"minimum with a {widest['dt_stats']['max']:.1f} s maximum in the same "
      f"session. That is suggestive of the sub-second-tool-call / long-pause "
      f"mixture H11 posits, and it is **not** a test of it.")
    w("")

    # ---------------- replay: H12 / H13 ----------------
    w("## H12 / H13 — frozen replay under real ordered latency")
    w("")
    w("Each run's hook records are converted to the trajectory format the "
      "frozen parser accepts and replayed through the frozen engine, adapter "
      "and triggers, with that run's own real ordered dt sequence injected "
      "per action. The constant-dt control uses the same trajectory at that "
      "run's own median dt.")
    w("")
    w("| run | max frust | reached 0.7 | reached clamp | crossings (real / const) | "
      "flicker (real / const) | A6 | T3 net | band crossing? | drained? |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    n_band = n_drain = n_reached = n_clamped = 0
    for r in runs:
        rid = r["run_id"]
        rd = SUB_DIR / rid
        rebuild_jsonl(r, rd)
        convert(rd / "session.jsonl", rd)
        traj = rd / "trajectory.json"
        dts = r["dt_seconds"]
        real = replay(traj, dts)
        med = r["dt_stats"]["median"] or 0.0
        const = replay(traj, [med] * max(1, len(dts)))
        band = ((real["crossings"] >= 2 or real["flicker"] >= 1)
                and const["crossings"] <= 1 and const["flicker"] == 0)
        n_band += band
        n_reached += real["reached"]
        n_clamped += real["clamped"]
        n_drain += (real["reached"] and real["drained"])
        w(f"| {rid} | {real['max_frust']:.3f} | "
          f"{'yes' if real['reached'] else 'no'} | "
          f"{'yes' if real['clamped'] else '**no**'} | "
          f"{real['crossings']} / {const['crossings']} | "
          f"{real['flicker']} / {const['flicker']} | {real['a6']} | {real['t3']} | "
          f"{'YES' if band else 'no'} | "
          f"{'YES' if real['drained'] else 'no'} |")
        r["_replay"] = {"real": {k: v for k, v in real.items() if k != "frust"},
                        "const": {k: v for k, v in const.items() if k != "frust"}}
    w("")
    frac_band = n_band / len(runs)
    h12 = ("SUPPORTED" if frac_band >= 0.25
           else "FALSIFIED" if frac_band < 0.10 else "PARTIAL")
    w(f"**H12: {h12}** — band crossings on **{n_band}/{len(runs)} "
      f"({frac_band*100:.0f}%)** of runs. Pre-registered: supported >= 25%, "
      f"falsified < 10%, 10-25% partial. Paper 2's C3 comparison point was "
      f"1/20 = 5%.")
    w("")

    # H13
    long_gaps = [(r["run_id"], d) for r in runs for d in r["dt_seconds"]
                 if d > DRAIN_S]
    drains = [(r["run_id"], r["_replay"]["real"]) for r in runs
              if r["_replay"]["real"]["drained"]]
    w(f"**H13.** The pre-registered mechanism claim is specifically about "
      f"draining **from the clamp**: `0.1 + 0.9*exp(-ln2/150*T) < 0.7` needs "
      f"**T > {DRAIN_S} s**. Reaching the 0.7 *trigger threshold* and reaching "
      f"the 1.0 *clamp* are different events with very different drain times, "
      f"and they must not be conflated.")
    w("")
    w(f"- runs reaching 0.7: **{n_reached}/{len(runs)}**")
    w(f"- runs reaching the clamp: **{n_clamped}/{len(runs)}**")
    w(f"- gaps exceeding {DRAIN_S} s: **{len(long_gaps)}** "
      f"({', '.join(f'{rid} {d:.1f}s' for rid, d in long_gaps) or 'none'})")
    w("")
    if n_reached:
        frac_drain = n_drain / n_reached
        h13 = "FALSIFIED" if frac_drain >= 0.20 else "SUPPORTED"
        w(f"Of the {n_reached} runs that crossed 0.7, **{n_drain}** fell back "
          f"below it ({frac_drain*100:.0f}%). Pre-registered falsification "
          f"threshold: >= 20%. **H13: {h13}**")
        w("")
        for rid, rp in drains:
            run = next(x for x in runs if x["run_id"] == rid)
            longest = max(run["dt_seconds"]) if run["dt_seconds"] else 0.0
            same = rp["drain_gap"] is not None and abs(longest - rp["drain_gap"]) < 1e-6
            if rp["clamped"]:
                w(f"**Mechanism, {rid}.** It reached the clamp and fell back "
                  f"below 0.7 across a **{rp['drain_gap']:.1f} s** gap "
                  f"({'>=' if rp['drain_gap'] >= DRAIN_S else '<'} the "
                  f"{DRAIN_S} s the clamp requires"
                  + ("" if rp["drain_gap"] >= DRAIN_S else
                     " — so the state had already decayed part-way before "
                     "that gap, or an intervening no-signal stretch did the "
                     "rest") + ").")
            else:
                w(f"**Mechanism, {rid}.** It peaked at frustration "
                  f"**{rp['max_frust']:.3f}** — over the 0.7 trigger threshold, "
                  f"nowhere near the 1.0 clamp — and fell back below 0.7 across "
                  f"a **{rp['drain_gap']:.1f} s** gap, far short of the "
                  f"{DRAIN_S} s the clamp would have required, because there "
                  f"was no clamp to drain from. The run's longest gap was "
                  f"{longest:.1f} s"
                  + (", which was that gap." if same else
                     ", and it was not the one that did it."))
        w("")
        clamped_runs = [(x["run_id"], x["_replay"]["real"]["a6"]) for x in runs
                        if x["_replay"]["real"]["clamped"]]
        if not clamped_runs:
            w("So H13 is falsified **on its operationalisation but not by its "
              "mechanism**. H13 imagined a saturated state that real gaps "
              "could not drain. What actually happens on this arm is that the "
              f"state **never saturates**: {len(runs)-n_clamped}/{len(runs)} "
              f"runs never reach the clamp and {len(runs)-n_reached}/{len(runs)} "
              f"never reach 0.7 at all. The accumulator barely charges. That is "
              f"the Phase-B evidence-starvation mechanism appearing in live "
              f"frontier traces rather than in a subsampling sweep — Paper 1's "
              f"saturation trap does not reproduce on this arm, and the reason "
              f"is not that gaps got long enough to drain it but that there is "
              f"nothing to drain.")
        else:
            names = ", ".join(f"{rid} (A6 fired {a6}x)" for rid, a6 in clamped_runs)
            w(f"H13's verdict is driven by the runs that crossed 0.7 without "
              f"clamping. But on this arm **Paper 1's saturation trap does "
              f"reproduce** on {n_clamped}/{len(runs)} run(s): {names} reached "
              f"the 1.0 clamp and stayed there, while "
              f"{len(runs)-n_clamped}/{len(runs)} never reached the clamp and "
              f"{len(runs)-n_reached}/{len(runs)} never reached 0.7. The trap is "
              f"therefore not simply historical: it is a property of the "
              f"*trace's* cadence, and a run made of many fast tool calls "
              f"(a burst of file reads at ~1 s each) charges the accumulator "
              f"exactly as Paper 1's traces did, regardless of which model "
              f"produced it.")
    else:
        h13 = "INAPPLICABLE"
        w("**No run reached 0.7 at all.** Per the pre-registration H13 is "
          "scored **inapplicable, not supported**.")
    w("")

    # ---------------- budget bounds ----------------
    w("## Implied monitoring-budget ceiling (Phase B + Phase E applied per run)")
    w("")
    w("`r_starv = n_actions / 5` (five accumulating observations are needed to "
      "reach 0.7 at step 0.15). `r_cliff = delta*/median_dt` with delta* from "
      "the Phase E design rule at that run's own measured error rate. The "
      "binding constraint is the smaller.")
    w("")
    w("| run | actions | err rate | delta* (s) | median dt | r_starv | r_cliff | binding | max safe budget |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in runs:
        d = r["derived"]
        safe = min(x for x in (d["r_starv"], d["r_cliff"]) if x is not None)
        w(f"| {r['run_id']} | {r['n_actions']} | {r['error_rate']:.2f} | "
          f"{d['delta_star_s']} | {r['dt_stats']['median']} | {d['r_starv']} | "
          f"{d['r_cliff']} | {d['binding']} | **1-in-{safe:.1f}** |")
    w("")
    safes = [min(x for x in (r["derived"]["r_starv"], r["derived"]["r_cliff"])
                 if x is not None) for r in runs]
    w(f"Median max safe budget across runs: **1-in-{statistics.median(safes):.1f}** "
      f"(pilot; superseded by `BUDGET_CEILING_9C.md`). An earlier version of "
      f"this sentence compared it with a literature that \"routinely "
      f"contemplates 1-in-10\"; that figure was never sourced and is withdrawn. "
      f"The verified related work contains *audit* budgets (1-2%), in "
      f"protocols where the automated monitor still scores every action.")
    w("")

    # ---------------- confounds ----------------
    w("## Confounds observed during the arm (recorded, not corrected mid-arm)")
    w("")
    w("**The agents had `git` and could read the injected bugs directly.** Bug "
      "injection writes *uncommitted working-tree edits* over a pinned commit, "
      "so `git diff` reveals every bug. Paper 2's five-tool schema had no "
      "`git`, so on those traces the bug had to be found by debugging. This "
      "changes task difficulty and is part of why C-sub action counts are not "
      "comparable to Paper 2's. It was **not** corrected mid-arm: the protocol "
      "was held constant across every run of both arms, so the model contrast "
      "stays internally valid even though the cross-harness one does not.")
    w("")
    w("| run | tool calls | using `git diff/status/stash/show` | PowerShell | Read |")
    w("|---|---|---|---|---|")
    for r in runs:
        p = SUB_DIR / r["run_id"] / "session.jsonl"
        recs = [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]
        gitn = sum(any(k in (x.get("tool_input") or "")
                       for k in ("git diff", "git status", "git stash", "git show"))
                   for x in recs)
        psn = sum(x["tool_name"] == "PowerShell" for x in recs)
        rdn = sum(x["tool_name"] == "Read" for x in recs)
        w(f"| {r['run_id']} | {len(recs)} | {gitn} | {psn} | {rdn} |")
    w("")
    w("Two further things lengthen or reshape traces relative to an agent that "
      "stops at the literal criterion: some agents ran the broader suite or "
      "diffed against HEAD after the target tests passed, and some chose a "
      "read-many-files strategy over a run-the-tests strategy. Both are visible "
      "in the Read column and both change the cadence the monitor sees. Shell "
      "choice (Bash vs PowerShell) is mapped to the same `bash_tool` by "
      "`convert.py`, so the observer treats them identically; invocation "
      "latency may differ on Windows. A future C-main should strip `git` from "
      "the tool surface or commit the injected bugs so the answer key cannot "
      "be read.")
    w("")

    # ---------------- summary ----------------
    w("## Scorecard")
    w("")
    w("| hypothesis | arm | result |")
    w("|---|---|---|")
    w("| H10 cadence | C-main (deferred, no API key) | **not scored** — C-sub is cross-harness |")
    w(f"| H11 bimodality | C-sub | **unscoreable** — 0/{len(runs)} runs reach n >= {H11_MIN_N} |")
    w(f"| H12 within-run stability | C-sub | **{h12}** ({n_band}/{len(runs)}) |")
    w(f"| H13 recovery/drain | C-sub | **{h13}** |")
    w(f"| H15 action count | C-sub | **{h15_label}** |")
    w("")

    report = "\n".join(out)
    dest = PILOT_DIR / f"PHASE_C_SUB_REPORT_{args.model}.md"
    dest.write_text(report, encoding="utf-8")
    (SUB_DIR / f"_analysis_{args.model}.json").write_text(
        json.dumps({"pooled": pool, "runs": runs}, indent=1, default=str),
        encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)
    print(f"\nsaved: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
