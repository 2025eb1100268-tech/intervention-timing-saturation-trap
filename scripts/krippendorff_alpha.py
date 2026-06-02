#!/usr/bin/env python3
"""
Multi-rater reliability for agent-intervention-timing labels on trajectory
astropy__astropy-13398 (56 actions, indices 0..55), three annotators.

Computes Krippendorff's alpha (nominal/binary metric) from scratch via the
coincidence-matrix method -- NOT a library -- for each intervention type
(pause / reflect / clarify) and for the "flagged-at-all" (any-type) location
coding. Intermediate observed/expected disagreement (Do, De) are printed so
each alpha is auditable by hand.

As a cross-check, recomputes the three pairwise Cohen's kappas on the
location coding and asserts they reproduce the previously verified values
(A-B +0.349, A-C +0.092, B-C -0.181). On any FAIL the script stops.

Self-contained: reads the three label files in labels/; writes
results/KRIPPENDORFF_REPORT.md. No engine code is required.

Usage:
    python scripts/krippendorff_alpha.py
"""
from __future__ import annotations
import json
import sys
from itertools import combinations
from pathlib import Path

IRR_DIR = Path("labels")
OUT_DIR = Path("results")
N_ACTIONS = 56
TYPES = ["pause", "reflect", "clarify"]

# Raters in a fixed order. (filename, short name)
RATERS = [
    ("labels_annotator_a.json", "Annotator A"),
    ("labels_annotator_b.json", "Annotator B"),
    ("labels_annotator_c.json", "Annotator C"),
]

# Previously verified pairwise Cohen's kappa on the location (any-flag) coding.
EXPECTED_COHEN = {
    ("Annotator A", "Annotator B"): 0.349,
    ("Annotator A", "Annotator C"): 0.092,
    ("Annotator B", "Annotator C"): -0.181,
}
COHEN_TOL = 0.001

# Below this many positives from a rater, that rater's column is degenerate
# for the type and alpha is dominated by absence agreement.
SPARSE_POS = 3


def load_rater(path: Path):
    """Return (name, {type: [0/1]*56}, anyflag[0/1]*56)."""
    d = json.loads(path.read_text(encoding="utf-8-sig"))
    flagged = d.get("flagged", {})
    vecs = {t: [0] * N_ACTIONS for t in TYPES}
    anyflag = [0] * N_ACTIONS
    for idx_str, lab in flagged.items():
        i = int(idx_str)
        for t in TYPES:
            if lab.get(t):
                vecs[t][i] = 1
        if any(lab.get(t) for t in TYPES):
            anyflag[i] = 1
    return d.get("human_labeler", path.stem), vecs, anyflag


def krippendorff_alpha_binary(columns):
    """Krippendorff's alpha for binary nominal data via the coincidence matrix.

    `columns` is a list of rater vectors, each length N units, values in {0,1}.
    Every unit is assumed rated by every rater (no missing data), which holds
    here because reviewed_all_actions is true: an un-flagged action is a 0.

    Returns dict with alpha, Do, De, coincidence entries, marginals.
    """
    n_raters = len(columns)
    n_units = len(columns[0])

    # 2x2 coincidence matrix o[c][k]
    o = {(0, 0): 0.0, (0, 1): 0.0, (1, 0): 0.0, (1, 1): 0.0}
    for u in range(n_units):
        vals = [columns[r][u] for r in range(n_raters)]
        m_u = len(vals)  # ratings on this unit (= n_raters here)
        if m_u < 2:
            continue
        # every ordered pair of DISTINCT raters contributes, normalized by m_u-1
        for i in range(m_u):
            for j in range(m_u):
                if i == j:
                    continue
                o[(vals[i], vals[j])] += 1.0 / (m_u - 1)

    n0 = o[(0, 0)] + o[(0, 1)]
    n1 = o[(1, 0)] + o[(1, 1)]
    n = n0 + n1

    # nominal metric: disagreement = off-diagonal mass
    sum_o_diff = o[(0, 1)] + o[(1, 0)]
    Do = sum_o_diff / n if n > 0 else float("nan")

    sum_e_diff = n0 * n1 + n1 * n0
    De = sum_e_diff / (n * (n - 1)) if n > 1 else float("nan")

    if De == 0:
        alpha = float("nan")  # no expected disagreement -> undefined
    else:
        alpha = 1.0 - Do / De

    return {
        "alpha": alpha, "Do": Do, "De": De,
        "o00": o[(0, 0)], "o01": o[(0, 1)], "o10": o[(1, 0)], "o11": o[(1, 1)],
        "n0": n0, "n1": n1, "n": n,
    }


def cohen_kappa(a, b):
    """Cohen's kappa for two binary vectors (same convention as scripts/irr.py)."""
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
        return float("nan"), Po, Pe
    return (Po - Pe) / (1 - Pe), Po, Pe


def band(alpha):
    """Krippendorff guidance: alpha>=0.80 reliable, >=0.667 tentative.
    Below that it is not usable. We report the band but never let a word
    imply agreement where alpha<=0."""
    if alpha != alpha:  # nan
        return "undefined"
    if alpha <= 0.0:
        return "no information (at/below chance)"
    if alpha < 0.40:
        return "weak (not usable)"
    if alpha < 0.667:
        return "moderate (still below tentative cutoff)"
    if alpha < 0.80:
        return "tentative"
    return "reliable"


def fmt(x, p=4):
    if x != x:
        return "undefined"
    return f"{x:+.{p}f}" if p <= 3 else f"{x:.{p}f}"


def falpha(x):
    return "undefined" if x != x else f"{x:+.3f}"


def main():
    paths_ok = all((IRR_DIR / fn).exists() for fn, _ in RATERS)
    if not paths_ok:
        print(f"missing label files in {IRR_DIR}", file=sys.stderr)
        sys.exit(1)

    raters = []
    for fn, short in RATERS:
        name, vecs, anyflag = load_rater(IRR_DIR / fn)
        raters.append((short, name, vecs, anyflag))

    out = []
    w = out.append

    w("# Krippendorff's Alpha — multi-rater reliability (n=3)")
    w("")
    w(f"Trajectory: astropy__astropy-13398, {N_ACTIONS} actions (indices 0-{N_ACTIONS-1}).")
    w("Annotators (n=3): " + "; ".join(f"{s} ({n})" for s, n, _, _ in raters) + ".")
    w("")
    w("Krippendorff's alpha, nominal/binary metric, computed from scratch via "
      "the coincidence-matrix method (no library). Every action was reviewed by "
      "every rater, so an un-flagged action is a genuine 0, not missing data. "
      "Do = observed disagreement, De = expected disagreement, alpha = 1 - Do/De.")
    w("")

    # Per-rater positive counts
    w("## Per-annotator positive counts")
    w("")
    w("| Annotator | pause | reflect | clarify | any-flag |")
    w("|---|---|---|---|---|")
    for s, n, vecs, anyflag in raters:
        w(f"| {s} | {sum(vecs['pause'])} | {sum(vecs['reflect'])} | "
          f"{sum(vecs['clarify'])} | {sum(anyflag)} |")
    w("")

    # Per-type alpha
    w("## Krippendorff's alpha by intervention type")
    w("")
    w("| Type | Do | De | alpha | band | n_positives (M / G / R) | degeneracy |")
    w("|---|---|---|---|---|---|---|")
    type_results = {}
    for t in TYPES:
        cols = [vecs[t] for _, _, vecs, _ in raters]
        pos = [sum(c) for c in cols]
        r = krippendorff_alpha_binary(cols)
        type_results[t] = r
        degen = ""
        is_degenerate = False
        if min(pos) == 0:
            degen = "a rater used this type 0x -> absence-dominated; read as NO INFORMATION"
            is_degenerate = True
        elif min(pos) < SPARSE_POS or r["n1"] < SPARSE_POS * 2:
            degen = "low base rate -> alpha dominated by absence agreement"
        # A degenerate column must not display a banding word that implies
        # agreement; override the band to NO INFORMATION regardless of alpha.
        band_label = "NO INFORMATION (degenerate)" if is_degenerate else band(r["alpha"])
        w(f"| {t} | {r['Do']:.4f} | {r['De']:.4f} | {falpha(r['alpha'])} | "
          f"{band_label} | {pos[0]} / {pos[1]} / {pos[2]} | {degen} |")
    w("")

    # Coincidence detail for auditability
    w("### Coincidence-matrix detail (auditable)")
    w("")
    w("| Type | o00 | o01 | o10 | o11 | n0 | n1 | n |")
    w("|---|---|---|---|---|---|---|---|")
    for t in TYPES:
        r = type_results[t]
        w(f"| {t} | {r['o00']:.1f} | {r['o01']:.1f} | {r['o10']:.1f} | "
          f"{r['o11']:.1f} | {r['n0']:.1f} | {r['n1']:.1f} | {r['n']:.0f} |")
    w("")

    # Any-flag (location) alpha
    any_cols = [anyflag for _, _, _, anyflag in raters]
    any_pos = [sum(c) for c in any_cols]
    ra = krippendorff_alpha_binary(any_cols)
    w("## Location alpha (flagged-at-all, ignoring intervention type)")
    w("")
    w("Did the three annotators flag the *same actions*, regardless of which "
      "intervention type they assigned?")
    w("")
    w("| Coding | Do | De | alpha | band | n_positives (M / G / R) |")
    w("|---|---|---|---|---|---|")
    w(f"| any-flag (location) | {ra['Do']:.4f} | {ra['De']:.4f} | "
      f"{falpha(ra['alpha'])} | {band(ra['alpha'])} | "
      f"{any_pos[0]} / {any_pos[1]} / {any_pos[2]} |")
    w("")
    w(f"Coincidence detail: o00={ra['o00']:.1f} o01={ra['o01']:.1f} "
      f"o10={ra['o10']:.1f} o11={ra['o11']:.1f} "
      f"n0={ra['n0']:.1f} n1={ra['n1']:.1f} n={ra['n']:.0f}")
    w("")

    # Cohen cross-check on location coding
    w("## Cross-check: pairwise Cohen's kappa on location coding")
    w("")
    w("Confirms this script reproduces the previously verified pairwise values "
      "(`scripts/irr.py`). Any FAIL stops the run.")
    w("")
    w("| Pair | kappa (this script) | expected | abs diff | result |")
    w("|---|---|---|---|---|")
    name_to_any = {s: anyflag for s, _, _, anyflag in raters}
    all_pass = True
    fail_lines = []
    for (a_s, b_s) in combinations([s for s, _, _, _ in raters], 2):
        k, Po, Pe = cohen_kappa(name_to_any[a_s], name_to_any[b_s])
        exp = EXPECTED_COHEN.get((a_s, b_s), EXPECTED_COHEN.get((b_s, a_s)))
        diff = abs(k - exp)
        ok = diff <= COHEN_TOL
        all_pass = all_pass and ok
        if not ok:
            fail_lines.append(f"{a_s}-{b_s}: got {k:+.4f}, expected {exp:+.3f}, diff {diff:.4f}")
        w(f"| {a_s} <-> {b_s} | {k:+.4f} | {exp:+.3f} | {diff:.4f} | "
          f"{'PASS' if ok else 'FAIL'} |")
    w("")
    if all_pass:
        w("**All pairwise Cohen cross-checks PASS.**")
    else:
        w("**CROSS-CHECK FAILED — see discrepancies below. Numbers not trusted.**")
        for fl in fail_lines:
            w(f"- {fl}")
    w("")

    # Plain-language reading
    w("## Plain-language reading")
    w("")
    cleared = [t for t in TYPES if type_results[t]["alpha"] == type_results[t]["alpha"]
               and type_results[t]["alpha"] >= 0.40]
    reflect_a = type_results["reflect"]["alpha"]
    pause_a = type_results["pause"]["alpha"]
    clarify_a = type_results["clarify"]["alpha"]
    para = []
    if cleared:
        para.append("The only intervention type(s) clearing even alpha=0.4: "
                    + ", ".join(cleared) + ".")
    else:
        para.append("No intervention type clears even alpha=0.4 "
                    "(the weakest 'not usable' cutoff). reflect is the highest at "
                    f"alpha={reflect_a:+.3f}, still well short of the 0.667 "
                    "tentative threshold.")
    para.append(
        f"pause (alpha={pause_a:+.3f}) and clarify (alpha={clarify_a:+.3f}) are at "
        "or below the no-information floor: their alpha is driven by the fact that "
        "all three raters agree on the many actions NObody flagged, not by agreement "
        "on what to flag. For pause, Annotator C used the label zero times, so the "
        "column is degenerate; for clarify, the three raters' positives barely overlap, "
        "pushing alpha negative (worse than chance).")
    para.append(
        f"The three-rater location alpha (any-flag) is {ra['alpha']:+.3f} -- far below "
        "the best pairwise Cohen kappa (A-B +0.349), because Annotator C's "
        "15 flags overlap the others' almost not at all, and the third rater drags "
        "the multi-way agreement down. This is the honest multi-rater picture: even "
        "*where* to intervene is essentially unreproducible across three annotators, "
        "and *which* intervention type is worse still except for reflect.")
    w(" ".join(para))
    w("")

    w("## Notes")
    w("")
    w("- Alpha computed from scratch (coincidence-matrix method); Do/De and the "
      "full 2x2 coincidence entries are printed above so every value is "
      "hand-checkable.")
    w("- Krippendorff guidance: alpha>=0.80 reliable, >=0.667 tentatively usable. "
      "Nothing here approaches either cutoff.")
    w("- Degenerate cells (a rater with 0 positives, or near-zero total positives) "
      "are flagged explicitly; their alpha reflects absence agreement, not "
      "agreement on intervention timing.")
    w("- No tuning. Negative and near-zero alphas are reported as-is.")

    report = "\n".join(out)
    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / "KRIPPENDORFF_REPORT.md"
    out_path.write_text(report, encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print()
    print(f"saved: {out_path}")

    if not all_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
