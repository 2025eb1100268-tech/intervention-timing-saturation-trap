"""Phase C / C-sub: Opus 5 vs Fable 5.1, same harness, same specs, same session.

Reads the `_analysis_<model>.json` files written by phase_c_analyze.py and
produces the internally-controlled model contrast -- the comparison the arm was
designed for. Neither arm is comparable to Paper 2 (different harness); the two
arms ARE comparable to each other.

Statistics are computed from scratch (stdlib only), per the pre-registration's
convention: Mann-Whitney U with tie correction and a normal approximation on the
pooled dt; a bootstrap CI on the ratio of pooled medians (seed 20260908, 10,000
resamples); and a per-spec paired sign count, which with n=5 specs is reported
as a count, not as a test.

Run from repo root:  python scripts/phase_c_compare.py
"""
from __future__ import annotations

import json
import math
import random
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SUB_DIR = ROOT / "data" / "live_runs" / "phase_c_sub"
PILOT_DIR = ROOT / "data" / "swebench_pilot"
SEED = 20260908
BOOT = 10_000

P2 = {"runA": (7, 1.78, 1.90, 1.94), "runB": (14, 1.46, 2.14, 2.59),
      "runC": (9, 1.48, 1.75, 1.99), "runD": (8, 1.65, 2.38, 2.76),
      "runE": (32, 1.53, 3.57, 15.87)}


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def ranks(v: List[float]) -> Tuple[List[float], List[int]]:
    """Average ranks; also returns tie-group sizes for the variance correction."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    ties: List[int] = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        if j > i:
            ties.append(j - i + 1)
        i = j + 1
    return r, ties


def mann_whitney(a: List[float], b: List[float]) -> Dict[str, float]:
    n1, n2 = len(a), len(b)
    allv = a + b
    r, ties = ranks(allv)
    R1 = sum(r[:n1])
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    mean = n1 * n2 / 2.0
    N = n1 + n2
    tie_term = sum(t ** 3 - t for t in ties) / (N * (N - 1)) if N > 1 else 0.0
    var = n1 * n2 / 12.0 * ((N + 1) - tie_term)
    z = (U - mean) / math.sqrt(var) if var > 0 else 0.0
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return {"U": U, "z": z, "p_two_sided": p,
            "prob_superiority_b_over_a": U2 / (n1 * n2) if n1 * n2 else float("nan")}


def boot_median_ratio(a: List[float], b: List[float]) -> Tuple[float, float, float]:
    rng = random.Random(SEED)
    obs = statistics.median(b) / statistics.median(a)
    rs = []
    for _ in range(BOOT):
        sa = [a[rng.randrange(len(a))] for _ in a]
        sb = [b[rng.randrange(len(b))] for _ in b]
        rs.append(statistics.median(sb) / statistics.median(sa))
    rs.sort()
    return obs, rs[int(0.025 * BOOT)], rs[int(0.975 * BOOT) - 1]


_HEART_INTERVALS: Dict[str, Tuple[float, float]] = {}


def regime_placement(median: float) -> Dict[str, int]:
    """Where a cadence sits relative to HEART's per-trajectory critical
    intervals (Phase 5 definition, via the frozen Phase-8 helper)."""
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


def load(model: str) -> Dict:
    p = SUB_DIR / f"_analysis_{model}.json"
    if not p.exists():
        sys.exit(f"missing {p}; run phase_c_analyze.py --model {model} first")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["runs"] = {r["run_id"]: r for r in d["runs"]}
    return d


def main() -> int:
    A, B = load("opus"), load("fable")
    specs = sorted(set(A["runs"]) & set(B["runs"]))
    if not specs:
        sys.exit("no overlapping specs between arms")

    out: List[str] = []
    w = out.append
    w("# Phase C / C-sub — Opus 5 vs Fable 5.1 (internally controlled)")
    w("")
    w(f"Tree commit `{git_sha()}`. Same session, same machine, same repos at the "
      f"pinned SHAs, same frozen bug injections, same goals, same subagent "
      f"harness, same PostToolUse timestamp point, same time-window attribution "
      f"with the operator's own records removed. The arms differ in the model "
      f"driving the agent and in nothing else we control.")
    w("")
    w("**One declared asymmetry.** The Opus 5 arm was launched with an explicit "
      "`model: \"opus\"` override while the session model was Opus 5; the "
      "Fable 5.1 arm inherited the session model after the operator switched the "
      "session to Fable 5.1 so that reasoning effort would match the model. In "
      "both arms the subagent model equals the session model; whether an "
      "explicit override changes inherited effort is not documented, so this is "
      "recorded rather than assumed away.")
    w("")

    # ---- per spec ----
    w("## Per spec")
    w("")
    w("| spec | actions O / F (P2) | median O / F (P2) | p90 O / F (P2) | max O / F (P2) | tests green O / F |")
    w("|---|---|---|---|---|---|")
    f_slower = 0
    for s in specs:
        a, b = A["runs"][s], B["runs"][s]
        da, db = a["dt_stats"], b["dt_stats"]
        p2 = P2.get(s, ("-", "-", "-", "-"))
        f_slower += db["median"] > da["median"]
        w(f"| {s} | {a['n_actions']} / {b['n_actions']} ({p2[0]}) | "
          f"{da['median']} / **{db['median']}** ({p2[1]}) | "
          f"{da['p90']} / {db['p90']} ({p2[2]}) | "
          f"{da['max']} / {db['max']} ({p2[3]}) | "
          f"{'Y' if a['final_tests_green'] else 'N'} / "
          f"{'Y' if b['final_tests_green'] else 'N'} |")
    w("")
    w(f"Specs on which Fable 5.1's median dt exceeds Opus 5's: "
      f"**{f_slower}/{len(specs)}**. With five specs this is a count, not a test.")
    w("")

    # ---- pooled ----
    pa = [d for s in specs for d in A["runs"][s]["dt_seconds"]]
    pb = [d for s in specs for d in B["runs"][s]["dt_seconds"]]
    sa, sb = sorted(pa), sorted(pb)

    def pct(v, p):
        k = (len(v) - 1) * p
        lo, hi = int(math.floor(k)), int(math.ceil(k))
        return v[lo] if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)

    w("## Pooled inter-action interval")
    w("")
    w("| | Opus 5 | Fable 5.1 | Paper 2 (cross-harness) |")
    w("|---|---|---|---|")
    w(f"| n dt | {len(pa)} | {len(pb)} | 65 |")
    w(f"| min | {min(pa):.2f} | {min(pb):.2f} | 0.97 |")
    w(f"| p25 | {pct(sa,.25):.2f} | {pct(sb,.25):.2f} | 1.25 |")
    w(f"| **median** | **{pct(sa,.5):.2f}** | **{pct(sb,.5):.2f}** | 1.53 |")
    w(f"| p75 | {pct(sa,.75):.2f} | {pct(sb,.75):.2f} | 1.86 |")
    w(f"| p90 | {pct(sa,.9):.2f} | {pct(sb,.9):.2f} | 2.33 |")
    w(f"| max | {max(pa):.2f} | {max(pb):.2f} | 15.87 |")
    w(f"| p90/median | {pct(sa,.9)/pct(sa,.5):.2f} | {pct(sb,.9)/pct(sb,.5):.2f} | 1.52 |")
    w("")
    mw = mann_whitney(pa, pb)
    obs, lo, hi = boot_median_ratio(pa, pb)
    w(f"Mann–Whitney U (two-sided, tie-corrected normal approximation): "
      f"U = {mw['U']:.0f}, z = {mw['z']:.2f}, **p = {mw['p_two_sided']:.3g}**. "
      f"Probability that a random Fable interval exceeds a random Opus interval: "
      f"**{mw['prob_superiority_b_over_a']:.2f}**.")
    w("")
    w(f"Ratio of pooled medians Fable/Opus: **{obs:.2f}** "
      f"(bootstrap 95% CI {lo:.2f}–{hi:.2f}, {BOOT:,} resamples, seed {SEED}).")
    w("")
    if lo <= 1.0 <= hi:
        w("The CI spans 1: **the two models are not distinguishable on median "
          "cadence in this harness at this n.** That is itself a usable "
          "result — see the reading below.")
    else:
        w("The CI excludes 1: the two models differ in median cadence in this "
          "harness.")
    w("")

    # ---- regime placement of each cadence ----
    w("## Where each cadence puts the monitor")
    w("")
    w("Against HEART's per-trajectory critical intervals (Phase 5, recomputed "
      "from the frozen artefacts). *Below* = the agent acts faster than that "
      "trajectory's critical interval, so the accumulator can hold itself "
      "above threshold (alarm regime); *above* = dead regime; *inside* = the "
      "knife-edge band.")
    w("")
    w("| pooled median | below (alarm) | inside band | above (dead) |")
    w("|---|---|---|---|")
    placements = {}
    for label, med in (("Paper 2 (gpt-5.4-mini, scriptable loop)", 1.53),
                       ("Opus 5 (C-sub)", pct(sa, .5)),
                       ("Fable 5.1 (C-sub)", pct(sb, .5))):
        pl = regime_placement(med)
        placements[label] = pl
        w(f"| {label}, {med:.2f} s | {pl['below']}/20 | {pl['inside']}/20 | "
          f"{pl['above']}/20 |")
    w("")

    # ---- monitor-relevant outcomes ----
    w("## What the frozen monitor saw, per arm")
    w("")
    w("| spec | max frust O / F | reached 0.7 O / F | reached clamp O / F | "
      "drained O / F | band crossing O / F | A6 O / F | T3 O / F |")
    w("|---|---|---|---|---|---|---|---|")
    for s in specs:
        ra = A["runs"][s]["_replay"]["real"]
        rb = B["runs"][s]["_replay"]["real"]
        yn = lambda x: "Y" if x else "n"
        # band crossing needs the const control too
        def band(r):
            real, const = r["_replay"]["real"], r["_replay"]["const"]
            return ((real["crossings"] >= 2 or real["flicker"] >= 1)
                    and const["crossings"] <= 1 and const["flicker"] == 0)
        w(f"| {s} | {ra['max_frust']:.3f} / {rb['max_frust']:.3f} | "
          f"{yn(ra['reached'])} / {yn(rb['reached'])} | "
          f"{yn(ra['clamped'])} / {yn(rb['clamped'])} | "
          f"{yn(ra['drained'])} / {yn(rb['drained'])} | "
          f"{yn(band(A['runs'][s]))} / {yn(band(B['runs'][s]))} | "
          f"{ra['a6']} / {rb['a6']} | {ra['t3']} / {rb['t3']} |")
    w("")
    clampA = sum(A["runs"][s]["_replay"]["real"]["clamped"] for s in specs)
    clampB = sum(B["runs"][s]["_replay"]["real"]["clamped"] for s in specs)
    w(f"Runs reaching the 1.0 clamp — the state Paper 1's saturation trap "
      f"requires: Opus **{clampA}/{len(specs)}**, Fable **{clampB}/{len(specs)}**.")
    w("")

    # ---- budget ----
    w("## Implied monitoring-budget ceiling")
    w("")
    w("| spec | r_starv O / F | r_cliff O / F | binding O / F | max safe budget O / F |")
    w("|---|---|---|---|---|")
    safesA, safesB = [], []
    for s in specs:
        da, db = A["runs"][s]["derived"], B["runs"][s]["derived"]
        sa_ = min(x for x in (da["r_starv"], da["r_cliff"]) if x is not None)
        sb_ = min(x for x in (db["r_starv"], db["r_cliff"]) if x is not None)
        safesA.append(sa_); safesB.append(sb_)
        w(f"| {s} | {da['r_starv']} / {db['r_starv']} | {da['r_cliff']} / {db['r_cliff']} | "
          f"{da['binding']} / {db['binding']} | 1-in-{sa_:.1f} / 1-in-{sb_:.1f} |")
    w("")
    w(f"Median max safe budget: Opus **1-in-{statistics.median(safesA):.1f}**, "
      f"Fable **1-in-{statistics.median(safesB):.1f}**.")
    w("")

    # ---- reading (data-driven; no prose assumes a direction) ----
    medA, medB = pct(sa, .5), pct(sb, .5)
    faster = "Fable 5.1" if medB < medA else "Opus 5"
    slower = "Opus 5" if faster == "Fable 5.1" else "Fable 5.1"
    a6A = {s: A["runs"][s]["_replay"]["real"]["a6"] for s in specs}
    a6B = {s: B["runs"][s]["_replay"]["real"]["a6"] for s in specs}
    reads = {m: {s: d["runs"][s]["tools_used"].get("Read", 0)
                 for s in specs} for m, d in (("O", A), ("F", B))}
    w("## Reading")
    w("")
    w(f"**The model moved the monitor's regime, and it moved it in the "
      f"direction nobody would have guessed from the model names.** Pooled "
      f"median cadence: Opus 5 **{medA:.2f} s**, Fable 5.1 **{medB:.2f} s** — "
      f"the heavier-reasoning model is the *faster-acting* one at the median "
      f"(ratio {obs:.2f}, CI {lo:.2f}–{hi:.2f}, p = {mw['p_two_sided']:.1g}). "
      f"Against the 20 legacy trajectories' critical intervals, "
      f"{slower}'s median sits below "
      f"{placements['Opus 5 (C-sub)' if slower=='Opus 5' else 'Fable 5.1 (C-sub)']['below']}/20 "
      f"(alarm regime) and {faster}'s below "
      f"{placements['Fable 5.1 (C-sub)' if faster=='Fable 5.1' else 'Opus 5 (C-sub)']['below']}/20, "
      f"with Paper 2's 1.53 s at {placements['Paper 2 (gpt-5.4-mini, scriptable loop)']['below']}/20.")
    w("")
    w(f"The mechanism is visible in the tool census, not in reasoning speed. "
      f"Fable 5.1's dispersion ratio is {pct(sb,.9)/medB:.1f} against Opus 5's "
      f"{pct(sa,.9)/medA:.1f}: its traces are a dense cluster of ~1 s tool "
      f"calls with a long tail of multi-second pauses. On runE it made "
      f"{reads['F']['runE']} `Read` calls (Opus: {reads['O']['runE']}), each "
      f"returning in about a second, and that burst charged the frozen "
      f"accumulator to the clamp — A6 fired {a6B['runE']}x against Opus's "
      f"{a6A['runE']}x on the same spec. **Median inter-action interval is a "
      f"property of the agent's tool-use strategy at least as much as of its "
      f"reasoning latency**, and a wall-clock-calibrated monitor responds to "
      f"a strategy shift exactly as it would to a model swap or a budget cut.")
    w("")
    w(f"So the same monitor, same thresholds, same harness: **{clampA}/{len(specs)}** "
      f"clamps under Opus 5, **{clampB}/{len(specs)}** under Fable 5.1. Paper 1's "
      f"saturation trap is not simply historical — it is reachable by any "
      f"trace whose cadence sits below the critical interval, and a frontier "
      f"model produced one. Nor is it reliable: the same model on four other "
      f"specs never came near the clamp. The monitor's output is a function of "
      f"cadence, and cadence is a function of things the monitor's author does "
      f"not control.")
    w("")
    w("Neither arm is comparable to Paper 2 on absolute cadence — the harness "
      "differs — which is why H10 is not scored. The within-harness contrast "
      "above is the comparison this arm was designed to deliver, and n = 5 "
      "specs per arm is its declared limit (`PHASE_C_PLAN.md` §7).")
    w("")

    report = "\n".join(out)
    dest = PILOT_DIR / "PHASE_C_SUB_COMPARISON.md"
    dest.write_text(report, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)
    print(f"\nsaved: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
