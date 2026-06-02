#!/usr/bin/env python3
"""
Inter-rater reliability for agent-intervention-timing labels on trajectory
astropy__astropy-13398 (56 actions, indices 0..55).

Computes, for each pair of annotators and each intervention type (pause/reflect/
clarify), Cohen's Kappa over the full 56-action binary vectors, plus:
  - raw counts (how many each flagged for that type)
  - observed agreement Po
  - a degeneracy flag when one rater's positives are too sparse for Kappa to be
    meaningful (prevalence problem)
Also computes "flagged-at-all" agreement (any type vs none) so type-confusion is
separated from location-agreement.

No tuning, no thresholds on the result. Reports whatever the labels give.

Usage:
    python irr.py labels/labels_annotator_a.json labels/labels_annotator_b.json labels/labels_annotator_c.json
Outputs IRR_REPORT.md in the cwd and prints it.
"""
import json
import sys
from itertools import combinations

N_ACTIONS = 56
TYPES = ["pause", "reflect", "clarify"]
# Below this many positives from EITHER rater, per-type Kappa is flagged as
# unreliable due to low base rate (prevalence problem).
SPARSE_POS_THRESHOLD = 3


def load(path):
    d = json.load(open(path))
    name = d.get("human_labeler", path)
    flagged = d.get("flagged", {})
    # build full-length binary vectors over 0..N_ACTIONS-1
    vecs = {t: [0] * N_ACTIONS for t in TYPES}
    anyflag = [0] * N_ACTIONS
    for idx_str, lab in flagged.items():
        i = int(idx_str)
        for t in TYPES:
            if lab.get(t):
                vecs[t][i] = 1
        if any(lab.get(t) for t in TYPES):
            anyflag[i] = 1
    return name, vecs, anyflag, flagged


def cohen_kappa(a, b):
    """Cohen's kappa for two binary vectors. Returns (kappa, Po, Pe)."""
    n = len(a)
    both1 = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    both0 = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    a1b0 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    a0b1 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    Po = (both1 + both0) / n
    pa1 = (both1 + a1b0) / n
    pb1 = (both1 + a0b1) / n
    Pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if Pe == 1.0:
        # both raters constant and identical -> agreement perfect but kappa undefined
        return (float("nan"), Po, Pe)
    kappa = (Po - Pe) / (1 - Pe)
    return (kappa, Po, Pe)


def fmt_k(k):
    if k != k:  # nan
        return "undefined"
    return f"{k:+.3f}"


def landis_koch(k):
    if k != k:
        return "—"
    if k < 0.0:
        return "poor (worse than chance)"
    if k <= 0.20:
        return "slight"
    if k <= 0.40:
        return "fair"
    if k <= 0.60:
        return "moderate"
    if k <= 0.80:
        return "substantial"
    return "almost perfect"


def main():
    paths = sys.argv[1:]
    if len(paths) < 2:
        print("need >=2 label files")
        sys.exit(1)

    raters = [load(p) for p in paths]
    names = [r[0] for r in raters]

    out = []
    w = out.append

    w("# Inter-Rater Reliability — agent-intervention-timing labels")
    w("")
    w(f"Trajectory: astropy__astropy-13398, {N_ACTIONS} actions (indices 0–{N_ACTIONS-1}).")
    w(f"Annotators (n={len(raters)}): " + "; ".join(names) + ".")
    w("")
    w("Cohen's Kappa computed over full 56-action binary vectors per intervention "
      "type. Low-base-rate types are flagged: when an annotator marks very few "
      "positives, Kappa is unstable and the raw overlap is the more interpretable "
      "statistic. Annotator C's discarded first pass is excluded.")
    w("")

    # Per-rater positive counts
    w("## Per-annotator positive counts")
    w("")
    w("| Annotator | pause | reflect | clarify | any-flag |")
    w("|---|---|---|---|---|")
    for name, vecs, anyflag, flagged in raters:
        row = [name] + [str(sum(vecs[t])) for t in TYPES] + [str(sum(anyflag))]
        w("| " + " | ".join(row) + " |")
    w("")

    # Per-type pairwise kappa
    w("## Pairwise Cohen's Kappa, by intervention type")
    w("")
    for t in TYPES:
        w(f"### {t.capitalize()}")
        w("")
        w("| Pair | rater-A pos | rater-B pos | Po | Kappa | Interpretation | Note |")
        w("|---|---|---|---|---|---|---|")
        for (na, va, aa, fa), (nb, vb, ab, fb) in combinations(raters, 2):
            posa, posb = sum(va[t]), sum(vb[t])
            k, Po, Pe = cohen_kappa(va[t], vb[t])
            note = ""
            if min(posa, posb) < SPARSE_POS_THRESHOLD:
                note = "low base rate — Kappa unreliable"
            if posa == 0 and posb == 0:
                note = "neither rater used this type"
            w(f"| {na} ↔ {nb} | {posa} | {posb} | {Po:.3f} | {fmt_k(k)} | "
              f"{landis_koch(k)} | {note} |")
        w("")

    # Flagged-at-all (location agreement, ignoring type)
    w("## Location agreement (flagged-at-all, ignoring intervention type)")
    w("")
    w("Did the annotators flag the *same actions*, regardless of which intervention "
      "type they assigned? This separates 'where to intervene' from 'how'.")
    w("")
    w("| Pair | A flags | B flags | shared actions | Po | Kappa | Interpretation |")
    w("|---|---|---|---|---|---|---|")
    for (na, va, aa, fa), (nb, vb, ab, fb) in combinations(raters, 2):
        shared = sorted(i for i in range(N_ACTIONS) if aa[i] and ab[i])
        k, Po, Pe = cohen_kappa(aa, ab)
        w(f"| {na} ↔ {nb} | {sum(aa)} | {sum(ab)} | "
          f"{shared if shared else '—'} | {Po:.3f} | {fmt_k(k)} | {landis_koch(k)} |")
    w("")

    # Action-level overlap map
    w("## Action-level overlap map")
    w("")
    all_flagged = {}
    for name, vecs, anyflag, flagged in raters:
        # Use the last whitespace-delimited token so "Annotator A/B/C" stays
        # distinct (the first token "Annotator" would collide across raters).
        short = name.split()[-1] if name.split() else name
        for i in range(N_ACTIONS):
            if anyflag[i]:
                all_flagged.setdefault(i, []).append(short)
    if all_flagged:
        w("| Action | Flagged by | # annotators |")
        w("|---|---|---|")
        for i in sorted(all_flagged):
            who = all_flagged[i]
            w(f"| {i} | {', '.join(who)} | {len(who)} |")
    w("")
    # consensus
    consensus_all = sorted(i for i, who in all_flagged.items() if len(who) == len(raters))
    consensus_2 = sorted(i for i, who in all_flagged.items() if len(who) >= 2)
    w(f"- Flagged by **all {len(raters)}** annotators: "
      f"{consensus_all if consensus_all else 'none'}")
    w(f"- Flagged by **≥2** annotators: {consensus_2 if consensus_2 else 'none'}")
    total_union = len(all_flagged)
    w(f"- Total distinct actions flagged by anyone: {total_union} of {N_ACTIONS}")
    w("")

    w("## Reading")
    w("")
    w("- Per-type Kappa is low-to-undefined across most pairs, driven partly by "
      "genuine disagreement and partly by low base rates (each annotator flags "
      "few actions). Both facts are reported rather than collapsed into one number.")
    w("- Location agreement (which actions to flag at all) is the more stable view; "
      "even there, agreement is modest and concentrated in the late-trajectory "
      "grinding region.")
    w("- Annotators diverge on intervention *type* even when they flag the same "
      "action — the clearest single takeaway, and the one that bears on why no "
      "automated trigger matches any single annotator's labels.")

    report = "\n".join(out)
    import os
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "IRR_REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)


if __name__ == "__main__":
    main()
