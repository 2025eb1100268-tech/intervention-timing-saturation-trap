"""Phase 9C analysis: H16, H17a, H17b, H18 — scored exactly as pre-registered.

Unit of analysis is the SPEC (PREREGISTRATION_PHASE9C.md §1). Exact Wilcoxon
signed-rank null distributions, computed from scratch. Every correlation gets
the THE TEST / NOT a test treatment required by §5 of the data pack.

Run from repo root:  python scripts/phase_c2_analyze.py
"""
from __future__ import annotations

import itertools
import json
import math
import random
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heart_instrument.convert import convert                            # noqa: E402
from phase_c_analyze import replay                                      # noqa: E402

from c2_source import C2, SOURCE, REPORT_DIR                            # noqa: E402
PILOT_DIR = ROOT / "data" / "swebench_pilot"
SEED, BOOT = 20260908, 20000
ALPHA = 0.05
CLAMP_RATE_RARE = 0.20
COLLINEAR = 0.90

# Pilot per-spec action counts, for the §3 descriptive comparison.
PILOT_ACTIONS = {"opus": [8, 13, 15, 14, 15], "fable": [7, 7, 16, 7, 35]}


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def ranks(v: List[float]) -> List[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(xs: List[float], ys: List[float]) -> float:
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def wilcoxon_exact(d: List[float]) -> Dict[str, Any]:
    """Two-sided exact signed-rank. Zero differences dropped (Wilcoxon's own
    convention); the drop count is reported."""
    nz = [x for x in d if x != 0]
    dropped = len(d) - len(nz)
    n = len(nz)
    if n == 0:
        return {"n": 0, "dropped_zeros": dropped, "W": None, "p": float("nan"),
                "floor": float("nan"), "median_diff": 0.0}
    rk = ranks([abs(x) for x in nz])
    Wp = sum(rk[i] for i, x in enumerate(nz) if x > 0)
    Wm = sum(rk[i] for i, x in enumerate(nz) if x < 0)
    W = min(Wp, Wm)
    cnt = 0
    for signs in itertools.product([1, -1], repeat=n):
        wp = sum(rk[i] for i in range(n) if signs[i] > 0)
        wm = sum(rk[i] for i in range(n) if signs[i] < 0)
        if min(wp, wm) <= W:
            cnt += 1
    return {"n": n, "dropped_zeros": dropped, "W_plus": Wp, "W_minus": Wm,
            "W": W, "p": cnt / 2 ** n, "floor": 2 / 2 ** n,
            "median_diff": statistics.median(nz)}


def partial_spearman(x, y, z) -> float:
    rxy, rxz, ryz = spearman(x, y), spearman(x, z), spearman(y, z)
    den = math.sqrt(max((1 - rxz ** 2) * (1 - ryz ** 2), 1e-12))
    return (rxy - rxz * ryz) / den


def main() -> int:
    runs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for p in sorted(C2.glob("S*_*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["model"] not in ("opus", "fable"):
            continue                                  # throwaway / probe
        runs[(r["spec"], r["model"])] = r
    specs = sorted({s for s, _ in runs} if runs else [])
    specs = [s for s in specs if (s, "opus") in runs and (s, "fable") in runs]
    if not specs:
        sys.exit("no matched 9C pairs found")

    # ---- replay each run through the frozen engine for peak frustration ----
    for (s, m), r in runs.items():
        d = C2 / s
        jl = d / f"session_{m}_r{r['repeat']}.jsonl"
        wd = d / f"replay_{m}_r{r['repeat']}"
        wd.mkdir(parents=True, exist_ok=True)
        convert(jl, wd)
        r["_replay"] = replay(wd / "trajectory.json", r["dt_seconds"])

    O: List[str] = []
    w = O.append
    w("# Phase 9C — clean-protocol replication: Opus 5 vs Fable 5.1")
    w("")
    w(f"Tree commit `{sha()}`. Pre-registered: `PREREGISTRATION_PHASE9C.md` "
      f"+ Amendment 1, both committed before the first run. "
      f"**n = {len(specs)} distinct specs**, 1 run per arm per spec, 16 runs. "
      f"The pilot (`phase_c_sub/`) is **not pooled** with anything here.")
    w("")
    w("Unit of analysis is the **spec**. Clean-git protocol: bug committed into "
      "a single orphan root commit with all other refs deleted, six assertions "
      "logged per run.")
    w("")
    if SOURCE == "canonical":
        w("**Data source: canonical (transcript-derived).** The published scoring "
          "read a PostToolUse hook that never saw a failed tool call. Every "
          "number below is recomputed from the subagent transcripts with those "
          "calls restored (`scripts/build_9c_canonical.py`; "
          "`HOOK_COVERAGE_AUDIT.md`). The scores as originally pre-registered "
          "and scored are preserved beside the corrected ones in "
          "`RECONCILIATION_9C.md`; set `HEART_9C_SOURCE=hook` to reproduce them.")
    else:
        w("**Data source: hook (as originally scored).** This is the published "
          "scoring, which could not see failed tool calls. The canonical, "
          "transcript-derived version is the default.")
    w("")

    # ---- protocol integrity ----
    w("## 0. Protocol integrity")
    w("")
    allpass = all(all(r["assertions"].values()) for r in runs.values())
    grecon = {m: [runs[(s, m)]["git_recon_calls"] for s in specs] for m in ("opus", "fable")}
    green = sum(1 for r in runs.values() if r["final_tests_green"])
    w(f"- clean-git assertions: **{'6/6 PASS on all 16 runs' if allpass else 'FAILURE'}**")
    w(f"- target tests green: **{green}/{len(runs)}** runs")
    w(f"- git recon attempts (found nothing by construction): Opus "
      f"{grecon['opus']}, Fable {grecon['fable']}")
    w("")

    # ---- per-spec table ----
    w("## 1. Per-spec results")
    w("")
    w("| spec | module | actions O / F | median dt O / F | Read O / F | peak frust O / F | clamp O / F |")
    w("|---|---|---|---|---|---|---|")
    for s in specs:
        o, f = runs[(s, "opus")], runs[(s, "fable")]
        ro, rf = o["_replay"], f["_replay"]
        yn = lambda x: "Y" if x else "n"
        w(f"| {s} | `{Path(o['repo']).name}` | {o['n_actions']} / {f['n_actions']} | "
          f"{o['dt_stats']['median']} / {f['dt_stats']['median']} | "
          f"{o['tools_used'].get('Read',0)} / {f['tools_used'].get('Read',0)} | "
          f"{ro['max_frust']:.3f} / {rf['max_frust']:.3f} | "
          f"{yn(ro['clamped'])} / {yn(rf['clamped'])} |")
    w("")

    # ---- H16 ----
    w("## 2. H16 — cadence direction")
    w("")
    w("Pre-registered: Fable's median dt **below** Opus's; Wilcoxon signed-rank "
      "on per-spec median dt (Opus − Fable), two-sided, exact, α = 0.05.")
    w("")
    d16 = [runs[(s, "opus")]["dt_stats"]["median"] -
           runs[(s, "fable")]["dt_stats"]["median"] for s in specs]
    r16 = wilcoxon_exact(d16)
    w("| spec | Opus | Fable | Opus − Fable |")
    w("|---|---|---|---|")
    for s, dd in zip(specs, d16):
        w(f"| {s} | {runs[(s,'opus')]['dt_stats']['median']} | "
          f"{runs[(s,'fable')]['dt_stats']['median']} | **{dd:+.3f}** |")
    w("")
    pos = sum(1 for x in d16 if x > 0)
    h16 = ("SUPPORTED" if r16["p"] < ALPHA and r16["median_diff"] > 0 else
           "FALSIFIED" if r16["p"] < ALPHA else "INCONCLUSIVE")
    w(f"Specs favouring Fable faster: **{pos}/{len(d16)}**. "
      f"W⁺ = {r16['W_plus']:.0f}, W⁻ = {r16['W_minus']:.0f}, "
      f"**exact two-sided p = {r16['p']:.4f}** "
      f"(floor at n = {r16['n']} is {r16['floor']:.2e}), median difference "
      f"{r16['median_diff']:+.3f} s.")
    w("")
    w(f"**H16: {h16}**"
      + ("" if h16 != "INCONCLUSIVE" else
         " — reported as inconclusive, not as a null and not as support. "
         "Per Amendment 1 §A1.2 the committed next step is to add the second "
         "repeat to all 8 specs and re-score on 2-repeat means, not to "
         "reinterpret these runs."))
    w("")

    # ---- H17a ----
    w("## 3. H17a — Read-burst, per-spec counts")
    w("")
    d17 = [runs[(s, "fable")]["tools_used"].get("Read", 0) -
           runs[(s, "opus")]["tools_used"].get("Read", 0) for s in specs]
    r17 = wilcoxon_exact([float(x) for x in d17])
    w("| spec | Opus Read | Fable Read | Fable − Opus |")
    w("|---|---|---|---|")
    for s, dd in zip(specs, d17):
        w(f"| {s} | {runs[(s,'opus')]['tools_used'].get('Read',0)} | "
          f"{runs[(s,'fable')]['tools_used'].get('Read',0)} | **{dd:+d}** |")
    w("")
    h17a = ("SUPPORTED" if r17["n"] and r17["p"] < ALPHA and r17["median_diff"] > 0
            else "FALSIFIED" if r17["n"] and r17["p"] < ALPHA else "INCONCLUSIVE")
    if r17["n"]:
        w(f"W⁺ = {r17['W_plus']:.0f}, W⁻ = {r17['W_minus']:.0f}, **exact "
          f"two-sided p = {r17['p']:.4f}** (n = {r17['n']} after dropping "
          f"{r17['dropped_zeros']} tied pair(s); floor {r17['floor']:.2e}), "
          f"median difference {r17['median_diff']:+.1f} Reads.")
    w("")
    w(f"**H17a: {h17a}**")
    w("")

    # ---- H17b ----
    w("## 4. H17b — does Read count *predict* peak frustration?")
    w("")
    w("Pre-registered discipline: the **raw** correlation is NOT the test, "
      "because more Reads means more actions means more accumulation. The test "
      "is the **partial controlling for action count**.")
    w("")
    rd = [runs[(s, m)]["tools_used"].get("Read", 0) for s in specs for m in ("opus", "fable")]
    pk = [runs[(s, m)]["_replay"]["max_frust"] for s in specs for m in ("opus", "fable")]
    ac = [runs[(s, m)]["n_actions"] for s in specs for m in ("opus", "fable")]
    raw = spearman(rd, pk)
    r_ra = spearman(rd, ac)
    r_pa = spearman(pk, ac)
    part = partial_spearman(rd, pk, ac)
    rng = random.Random(SEED)
    null = []
    for _ in range(BOOT):
        sh = pk[:]
        rng.shuffle(sh)
        null.append(partial_spearman(rd, sh, ac))
    pv = sum(1 for x in null if abs(x) >= abs(part)) / len(null)
    w("**NOT a test:**")
    w("")
    w("| | Spearman |")
    w("|---|---|")
    w(f"| raw: Read count vs peak frustration | {raw:.3f} |")
    w(f"| Read count vs action count (collinearity check) | {r_ra:.3f} |")
    w(f"| peak frustration vs action count | {r_pa:.3f} |")
    w("")
    w("**THE TEST:**")
    w("")
    w(f"| | value |")
    w(f"|---|---|")
    w(f"| **partial ρ(Read, peak frust \\| action count)** | **{part:.4f}** |")
    w(f"| permutation p ({BOOT:,} shuffles, seed {SEED}) | **{pv:.4f}** |")
    w(f"| n (runs, both arms) | {len(rd)} |")
    w("")
    if abs(r_ra) > COLLINEAR:
        h17b = "UNINTERPRETABLE"
        w(f"**H17b: UNINTERPRETABLE.** Read count and action count are "
          f"collinear at ρ = {r_ra:.3f} > {COLLINEAR}, which the "
          f"pre-registration declared as an outcome rather than something to "
          f"work around: the partial cannot separate them.")
    else:
        h17b = "SUPPORTED" if part > 0 and pv < ALPHA else "FALSIFIED"
        if h17b == "SUPPORTED":
            w("**H17b: SUPPORTED**")
        else:
            # Canonical wording: scripts/withdrawals.py, W1.
            w("**H17b: FALSIFIED under its pre-registered clause — canonical "
              "label: did not replicate (W1).** The partial is not "
              "distinguishable from zero at n = 16. The clause equated "
              "non-significance with falsification; this is absence of "
              "evidence for a read-burst mechanism, not evidence that reading "
              "plays no role. Per the pre-registration the mechanism claim is "
              "**withdrawn from the paper** either way.")
    w("")

    # ---- H18 ----
    w("## 5. H18 — clamp rate")
    w("")
    cl = {m: sum(1 for s in specs if runs[(s, m)]["_replay"]["clamped"]) for m in ("opus", "fable")}
    rc = {m: cl[m] / len(specs) for m in cl}
    reach = {m: sum(1 for s in specs if runs[(s, m)]["_replay"]["reached"]) for m in ("opus", "fable")}
    mx = {m: max(runs[(s, m)]["_replay"]["max_frust"] for s in specs) for m in ("opus", "fable")}
    w("| arm | reached 0.7 | reached clamp | clamp rate | max frustration observed |")
    w("|---|---|---|---|---|")
    for m in ("opus", "fable"):
        w(f"| {m} | {reach[m]}/{len(specs)} | {cl[m]}/{len(specs)} | "
          f"{rc[m]*100:.0f}% | {mx[m]:.3f} |")
    w("")
    if cl["opus"] == 0 and cl["fable"] == 0:
        h18 = "SUPPORTED (zero-clamp branch)"
        w(f"**H18: SUPPORTED**, and via the pre-stated **third outcome**: "
          f"**zero runs clamped in either arm**. Therefore the pilot's single "
          f"runE clamp is **unreplicated**, and the clamp-specific mechanism "
          f"claim is **withdrawn**. The cadence and regime-placement results "
          f"do not depend on it and stand.")
    elif max(rc.values()) <= CLAMP_RATE_RARE:
        h18 = "SUPPORTED"
        w(f"**H18: SUPPORTED** — both arms at or below the pre-registered "
          f"{CLAMP_RATE_RARE*100:.0f}% 'rare' threshold.")
    else:
        h18 = "FALSIFIED"
        w(f"**H18: FALSIFIED** — an arm exceeds {CLAMP_RATE_RARE*100:.0f}%. "
          f"Clamping is a common outcome, not a rare one, and the 'reachable "
          f"but unreliable' framing must be replaced with 'the trap closes "
          f"routinely'.")
    w("")

    # ---- action counts ----
    w("## 6. Action counts under the clean protocol (descriptive)")
    w("")
    w("Pre-registered direction: **increase** relative to the pilot, since the "
      "`git diff` shortcut to localisation is gone.")
    w("")
    w("| arm | 9C per-spec actions | 9C median | pilot median | direction |")
    w("|---|---|---|---|---|")
    for m in ("opus", "fable"):
        a = [runs[(s, m)]["n_actions"] for s in specs]
        pm = statistics.median(PILOT_ACTIONS[m])
        am = statistics.median(a)
        w(f"| {m} | {a} | **{am:.1f}** | {pm:.1f} | "
          f"{'increase' if am > pm else 'decrease' if am < pm else 'unchanged'} |")
    w("")
    w("**The pre-registered direction was wrong, and the comparison is worse "
      "confounded than the pre-registration admitted.** I registered this as "
      "confounded with the protocol change; it is *also* confounded with the "
      "**spec set**, because 9C uses eight different specs from the pilot's "
      "five. The pilot included `runE` = the entire more-itertools suite "
      "(32-35 actions); every 9C spec targets a single test file. So a "
      "decrease was likely from the task set alone, independently of the git "
      "protocol, and this comparison cannot separate the two. It is reported "
      "as a failed prediction and as uninformative about the protocol — not "
      "reinterpreted.")
    w("")
    w("The consequence matters downstream: shorter runs mean fewer "
      "accumulating observations, which is why peak frustration is lower here "
      f"than in the pilot (max {max(runs[(s, 'opus')]['_replay']['max_frust'] for s in specs):.3f} / "
      f"{max(runs[(s, 'fable')]['_replay']['max_frust'] for s in specs):.3f} against 0.807 / 1.000) and why "
      "nothing clamped. That is Phase B's evidence-starvation mechanism "
      "operating on the trace length, and it is the one thing in this arm "
      "consistent with the pilot.")
    w("")

    # ---- H11 conditional revival ----
    nlong = sum(1 for r in runs.values() if r["n_dt"] >= 30)
    w("## 7. H11 conditional revival check")
    w("")
    w(f"Runs reaching n ≥ 30 dt intervals: **{nlong}/{len(runs)}**. Revival "
      f"required ≥ 8. **{'Revived' if nlong >= 8 else 'Not revived'}** — H11 "
      f"remains retired.")
    w("")

    # ---- pooled cadence, descriptive and cross-harness ----
    w("## 8. Pooled cadence (descriptive, cross-harness)")
    w("")
    pa = sorted(d for s_ in specs for d in runs[(s_, "opus")]["dt_seconds"])
    pb = sorted(d for s_ in specs for d in runs[(s_, "fable")]["dt_seconds"])
    def q(v, f):
        k = (len(v) - 1) * f
        lo, hi = int(math.floor(k)), int(math.ceil(k))
        return v[lo] if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)
    w("| | Opus 5 | Fable 5.1 | Paper 2 (scriptable loop) |")
    w("|---|---|---|---|")
    w(f"| n dt | {len(pa)} | {len(pb)} | 65 |")
    w(f"| median | **{q(pa,.5):.2f}** | **{q(pb,.5):.2f}** | 1.53 |")
    w(f"| p90 | {q(pa,.9):.2f} | {q(pb,.9):.2f} | 2.33 |")
    w(f"| max | {max(pa):.2f} | {max(pb):.2f} | 15.87 |")
    w("")
    w("Both arms sit several times Paper 2's cadence and inside the (1, 30] s "
      "critical band. **That is a harness-level observation, not a model one** "
      "— H16 shows the two models are indistinguishable here — and it is "
      "cross-harness against Paper 2, so it supports no confirmatory claim. "
      "It is reported for what it is: a real agent harness runs an order of "
      "magnitude slower than a scriptable one-tool-call loop, which is exactly "
      "the kind of infrastructure fact the paper argues determines a "
      "wall-clock monitor's regime.")
    w("")

    # ---- what this does to the paper ----
    w("## 9. What this does to the paper")
    w("")
    w("**Withdrawn.** The Phase-C model-contrast claims do not survive a clean "
      "protocol with the correct unit of analysis:")
    w("")
    w(f"- the cadence *direction* (Fable faster) does not replicate — "
      f"{sum(1 for s in specs if runs[(s, 'opus')]['dt_stats']['median'] > runs[(s, 'fable')]['dt_stats']['median'])}/8 "
      f"specs, p = {r16['p']:.2f}, median difference {r16['median_diff']:+.2f} s. The pilot's 4/5 was noise "
      "at n = 5 with a floor of 0.0625.")
    w("- the **Read-burst mechanism is withdrawn** — H17a inconclusive "
      "(p = 1.00; Read counts are 0–4 in *both* arms, never the pilot's 25) "
      "and H17b's partial not distinguishable from zero.")
    w("- the **clamp is withdrawn** — 0/16 runs clamped. The pilot's single "
      "runE clamp (28 A6 fires) is unreplicated and was one run.")
    w("")
    w("**Unaffected.** Everything computed on frozen streams with exact "
      "arithmetic, which is where the paper's weight was already placed: "
      "Phase B's budget×cadence identity (0 mismatches / 19,360 cells) and the "
      "evidence-starvation floor; Phase A0's sign-constraint proof; Phase E's "
      "design rule (13/20 containment) and the shipped tests; and the "
      "monitor-class census.")
    w("")
    w("**Net reading.** Paper 3's claims should rest on the frozen-data results "
      "and the deliverable, not on live-agent model comparisons. This arm is "
      "the honest demonstration of why: an n = 5 pilot with the wrong unit and "
      "a protocol leak produced three findings, and all three evaporated when "
      "the unit, the protocol and the spec count were fixed.")
    w("")

    # ---- scorecard ----
    w("## 10. Scorecard")
    w("")
    w("| hypothesis | result |")
    w("|---|---|")
    w(f"| H16 cadence direction | **{h16}** (p = {r16['p']:.4f}, {pos}/{len(d16)} specs) |")
    w(f"| H17a Read-burst counts | **{h17a}**" + (f" (p = {r17['p']:.4f})" if r17['n'] else "") + " |")
    w(f"| H17b Read → frustration mechanism | **{h17b}** under its clause"
      + ("" if h17b == "SUPPORTED" else " · canonical: **did not replicate** (W1)")
      + f" (partial {part:.3f}, p = {pv:.4f}) |")
    w(f"| H18 clamp rate | **{h18}** |")
    w(f"| H11 revival | not revived ({nlong}/{len(runs)} runs at n ≥ 30) |")
    w("")

    rep = "\n".join(O)
    dest = REPORT_DIR / "PHASE_C2_REPORT.md"
    dest.write_text(rep, encoding="utf-8")
    (C2 / "_analysis.json").write_text(json.dumps({
        "specs": specs, "h16": r16, "h17a": r17,
        "h17b": {"raw": raw, "read_vs_actions": r_ra, "partial": part, "p": pv},
        "clamps": cl, "n_long": nlong,
        "runs": {f"{s}|{m}": {k: v for k, v in runs[(s, m)].items()
                              if not k.startswith("_")}
                 for s in specs for m in ("opus", "fable")}},
        indent=1, default=str), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(rep)
    print(f"\nsaved: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
