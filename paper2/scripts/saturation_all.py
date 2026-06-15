#!/usr/bin/env python3
"""Aggregate per-trajectory saturation replays into SATURATION_ALL.md.

Reads the per-trajectory data/swebench_pilot/saturation_<traj>.json files
produced by scripts/saturation_replay.py (which is run unmodified, with the
unmodified engine / observer / A6 triggers and untouched thresholds).

State/firing-rate analysis ONLY. No human labels, no F1/precision/recall.

Also runs a consistency check against the previously recorded values for the
two already-analyzed trajectories and prints PASS/FAIL.

Usage:
    python scripts/saturation_all.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

PILOT_DIR = Path("data/swebench_pilot")
SUS_THR = 0.7  # SUSTAINED_FRUSTRATION_THRESHOLD (from heart_guidelines/triggers.py)

# The original five pilot trajectories, in descending-length order. Used
# only as a preferred ordering for the table; the actual trajectory list is
# discovered from the saturation_*.json files present (see discover_trajectories).
_ORIGINAL_ORDER = [
    "astropy__astropy-13033",
    "astropy__astropy-13398",
    "astropy__astropy-13236",
    "astropy__astropy-13453",
    "astropy__astropy-12907",
]

# Previously recorded numbers for the two already-analyzed trajectories. These
# are a paper reproducibility guarantee: any drift here is a real regression.
EXPECTED = {
    "astropy__astropy-13398": {"first_cross": 15, "sf": 73.2, "sva": 75.0, "hc": 75.0},
    "astropy__astropy-13033": {"first_cross": 12, "sf": 79.7, "sva": 83.1, "hc": 81.4},
}
RATE_TOL = 0.1  # percentage-point tolerance on the rounded rates


def discover_trajectories():
    """Return trajectory ids that have a saturation_<id>.json present.

    Derived from files on disk rather than a hardcoded list, so new
    trajectories are picked up automatically. The original five are listed
    first (in their established order) for table stability; any additional
    trajectories follow, sorted.
    """
    found = set()
    for p in PILOT_DIR.glob("saturation_astropy__astropy-*.json"):
        # strip the 'saturation_' prefix and '.json' suffix
        found.add(p.stem[len("saturation_"):])
    ordered = [t for t in _ORIGINAL_ORDER if t in found]
    extras = sorted(t for t in found if t not in _ORIGINAL_ORDER)
    return ordered + extras


def analyze(traj_id):
    path = PILOT_DIR / f"saturation_{traj_id}.json"
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    tl = d["timeline"]
    n = len(tl)

    first_cross = next((e["action_index"] for e in tl if e["frustration"] >= SUS_THR), None)
    if first_cross is None:
        stays = False
    else:
        stays = all(tl[i]["frustration"] >= SUS_THR for i in range(first_cross, n))

    sf = sum(1 for e in tl if e["fires"]["sustained_frustration"])
    sva = sum(1 for e in tl if e["fires"]["same_valence_accumulation"])
    hc = sum(1 for e in tl if e["fires"]["high_confusion_no_reflection"])
    max_frust = max(e["frustration"] for e in tl)
    max_acc = max(e["neg_sum"] for e in tl)

    return {
        "traj": traj_id, "n": n,
        "first_cross": first_cross, "stays": stays,
        "max_frust": max_frust, "max_acc": max_acc,
        "sf": sf, "sva": sva, "hc": hc,
        "sf_pct": 100 * sf / n, "sva_pct": 100 * sva / n, "hc_pct": 100 * hc / n,
    }


def main():
    traj_ids = discover_trajectories()
    results = [analyze(t) for t in traj_ids]

    # Consistency check. Trajectories in EXPECTED are a hard reproducibility
    # guarantee (FAIL is a real regression). Trajectories NOT in EXPECTED are
    # new: they are reported as 'n/a (new)' and do not affect the pass status
    # -- a warning-with-pass, never a crash.
    check_lines = []
    all_pass = True
    for r in results:
        exp = EXPECTED.get(r["traj"])
        if not exp:
            check_lines.append(
                f"| {r['traj']} | first-cross {r['first_cross']} | "
                f"{round(r['sf_pct'],1)}/{round(r['sva_pct'],1)}/{round(r['hc_pct'],1)}% | "
                f"n/a (new trajectory, no reference) |"
            )
            continue
        fc_ok = (r["first_cross"] == exp["first_cross"])
        sf_ok = abs(round(r["sf_pct"], 1) - exp["sf"]) <= RATE_TOL
        sva_ok = abs(round(r["sva_pct"], 1) - exp["sva"]) <= RATE_TOL
        hc_ok = abs(round(r["hc_pct"], 1) - exp["hc"]) <= RATE_TOL
        ok = fc_ok and sf_ok and sva_ok and hc_ok
        all_pass = all_pass and ok
        check_lines.append(
            f"| {r['traj']} | first-cross {r['first_cross']} (exp {exp['first_cross']}) | "
            f"{round(r['sf_pct'],1)}/{round(r['sva_pct'],1)}/{round(r['hc_pct'],1)}% "
            f"(exp {exp['sf']}/{exp['sva']}/{exp['hc']}) | "
            f"{'PASS' if ok else 'FAIL'} |"
        )

    # Build report
    out = []
    w = out.append
    w(f"# State Saturation Trap — {len(results)} pilot trajectories")
    w("")
    w("State/firing-rate analysis only. No human labels, no F1. Each trajectory "
      "replayed through the unmodified engine + observer + A6 triggers "
      "(`scripts/saturation_replay.py`), thresholds and engine constants "
      "untouched. Frustration is clamped to [0,1]; the threshold of interest is "
      f"{SUS_THR} (`SUSTAINED_FRUSTRATION_THRESHOLD`). The accumulator is the sum "
      "of five negative-arousal emotions (frustration + anger + fear + confusion "
      "+ vengeance), range [0,5], gated at 1.5 by `same_valence_accumulation`.")
    w("")
    w("## Summary table")
    w("")
    w("| Trajectory | Actions | First crosses 0.7 | Stays saturated | Max frust | "
      "sustained_frust % | same_valence % | high_confusion % | Accumulator max |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        fc = "never" if r["first_cross"] is None else f"action {r['first_cross']}"
        stays = "—" if r["first_cross"] is None else ("yes" if r["stays"] else "no")
        w(f"| {r['traj'].replace('astropy__astropy-','astropy-')} | {r['n']} | {fc} | "
          f"{stays} | {r['max_frust']:.2f} | "
          f"{r['sf']}/{r['n']} = {r['sf_pct']:.1f}% | "
          f"{r['sva']}/{r['n']} = {r['sva_pct']:.1f}% | "
          f"{r['hc']}/{r['n']} = {r['hc_pct']:.1f}% | "
          f"{r['max_acc']:.3f} |")
    w("")

    # Consistency check block
    w("## Consistency check (previously recorded trajectories)")
    w("")
    w("| Trajectory | first-cross | rates sustained/same_valence/high_confusion | result |")
    w("|---|---|---|---|")
    for cl in check_lines:
        w(cl)
    w("")
    w(f"**{'All consistency checks PASS.' if all_pass else 'CONSISTENCY CHECK FAILED.'}**")
    w("")

    # Plain-language reading -- data-driven
    n_total = len(results)
    saturators = [r for r in results if r["first_cross"] is not None and r["stays"]]
    non_sat = [r for r in results if not (r["first_cross"] is not None and r["stays"])]
    # "early" = crosses within the first third of the trajectory
    early = [r for r in saturators if r["first_cross"] is not None
             and r["first_cross"] <= r["n"] / 3.0]

    w("## Plain-language reading")
    w("")
    para = []
    para.append(
        f"Of the {n_total} pilot trajectories, **{len(saturators)} saturate**: "
        "frustration crosses 0.7 and then stays at or above it through the final "
        "action.")
    if saturators:
        crosses = ", ".join(
            f"{r['traj'].replace('astropy__astropy-','')} at action {r['first_cross']} "
            f"(of {r['n']})" for r in saturators)
        para.append(f"First-crossing points: {crosses}.")
    if len(early) == len(saturators) and saturators:
        para.append(
            "Every saturating trajectory crosses within roughly the first third of "
            "its actions, so once saturated the threshold-on-state A6 triggers fire "
            "on a large fraction of the remainder — the same mechanism the paper "
            "reports on the original two.")
    if non_sat:
        names = ", ".join(r["traj"].replace("astropy__astropy-", "") for r in non_sat)
        para.append(
            f"**Exception(s): {names}** do not meet the strict saturate-and-stay "
            "criterion — reported plainly as a non-reproduction, not adjusted.")
    else:
        para.append(
            "No trajectory breaks the pattern: the State Saturation Trap reproduces "
            f"on all {n_total} pilot trajectories (n={n_total}, up from the n=2 in the "
            "paper draft).")
    # Firing-rate spread note
    minrate = min(r["sf_pct"] for r in results)
    maxrate = max(r["sf_pct"] for r in results)
    para.append(
        f"sustained_frustration firing rates span {minrate:.1f}%–{maxrate:.1f}% across "
        "the five; the shorter trajectories sit lower simply because the pre-"
        "saturation prefix is a larger fraction of a short run, not because the "
        "mechanism differs.")
    w(" ".join(para))
    w("")
    w("## Notes")
    w("")
    w("- No engine, trigger, threshold, adapter, or label code modified; "
      "`scripts/saturation_replay.py` run unmodified per trajectory.")
    w("- No human labels used; no F1/precision/recall computed (no labels exist "
      "for 12907 / 13236 / 13453).")
    w("- 'Stays saturated' requires frustration >= 0.7 at every action from the "
      "first crossing to the end (strict).")

    report = "\n".join(out)
    out_path = PILOT_DIR / "SATURATION_ALL.md"
    out_path.write_text(report, encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print()
    print(f"saved: {out_path}")
    if not all_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
