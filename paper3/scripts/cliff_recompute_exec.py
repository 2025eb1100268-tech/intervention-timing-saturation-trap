"""The design rule's cliff location, recomputed under BOTH evidence definitions.

The cliff quoted in PAPER3_DATAPACK.md §5.1 ("the formula says the cliff is at
24.5 s") is computed from the CONTAMINATED per-action error rate: the frozen
observer's has_error() over the whole text a tool returned, which fires on file
contents that merely mention errors (48% of legacy qualifying observations come
from the editor tool). This recomputes delta* and the measured critical interval
under the construct-matched EXECUTION-ONLY definition as well, and reports both
with the units each is quoted in.

Nothing is tuned. delta* = -(H/ln2)*ln(1 - a*p/theta) with the frozen constants;
only the stream feeding p and the replay changes.

Run from repo root:  python scripts/cliff_recompute_exec.py
"""
from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from monitor_invariance.design_rule import critical_interval          # noqa: E402
from heart_adapters.claude_code.trajectory import parse_trajectory_file  # noqa: E402
from generality_sweep import all_ids                                  # noqa: E402
from warning_sign_bracketing import traj_path                         # noqa: E402

STEP, THRESHOLD, HALF_LIFE = 0.15, 0.7, 150.0
LAM = math.log(2.0) / HALF_LIFE
GRID = (0.0, 1.0, 5.0, 15.0, 30.0, 60.0, 150.0, 300.0, 600.0)
SHELL_LEGACY = {"bash_tool"}
OUT = ROOT / "data" / "swebench_pilot" / "CLIFF_RECOMPUTE.md"


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def i1_fires(stream: List[int], dt: float) -> List[bool]:
    """The frozen I1 rule, one decision per observation."""
    s, out = 0.0, []
    for x in stream:
        s = min(1.0, s * math.exp(-LAM * dt) + STEP * x)
        out.append(s >= THRESHOLD)
    return out


def measured_interval(stream: List[int]):
    """First grid dt whose post-first-fire persistence drops below 50%,
    reported as (previous grid point, that dt]. Same rule as the paper.

    Returns None in TWO distinct cases, and the caller must not conflate them:
      - the monitor never leaves the alarm regime on the grid (no cliff), or
      - it never fires at all, even at dt = 0 (starved: E < N_min). The
        original implementation returned (0, 0] here, which reads as a cliff
        at zero rather than as the absence of any measurement.
    """
    if not any(i1_fires(stream, 0.0)):
        return None                      # starved: nothing to measure
    for i, dt in enumerate(GRID):
        fires = i1_fires(stream, dt)
        first = next((j for j, f in enumerate(fires) if f), None)
        persist = (100.0 * sum(fires[first:]) / len(fires[first:])
                   if first is not None else 0.0)
        if persist < 50.0:
            return (GRID[i - 1] if i else 0.0, dt)
    return None


def bin_of(x: float) -> int:
    for i, g in enumerate(GRID):
        if x <= g:
            return i
    return len(GRID)


def main() -> int:
    rows = []
    for t in all_ids():
        ev = parse_trajectory_file(traj_path(t))
        contaminated = [1 if e.has_error() else 0 for e in ev]
        execonly = [1 if (e.tool_name in SHELL_LEGACY and e.has_error()) else 0
                    for e in ev]
        n = len(ev)
        rows.append({
            "id": t.replace("astropy__astropy-", "astropy-").replace("django__django-", "django-"),
            "n": n,
            "p_cont": sum(contaminated) / n,
            "p_exec": sum(execonly) / n,
            "d_cont": critical_interval(STEP, sum(contaminated) / n, HALF_LIFE, THRESHOLD),
            "d_exec": critical_interval(STEP, sum(execonly) / n, HALF_LIFE, THRESHOLD),
            "m_cont": measured_interval(contaminated),
            "m_exec": measured_interval(execonly),
        })

    def contained(d: Optional[float], m) -> Optional[bool]:
        if d is None or m is None:
            return None
        return m[0] < d <= m[1]

    for r in rows:
        r["ok_cont"] = contained(r["d_cont"], r["m_cont"])
        r["ok_exec"] = contained(r["d_exec"], r["m_exec"])

    dc = [r["d_cont"] for r in rows if r["d_cont"] is not None]
    de = [r["d_exec"] for r in rows if r["d_exec"] is not None]
    # Where could the published 24.5 s have come from? Check the candidates.
    pooled_c = sum(r["p_cont"] * r["n"] for r in rows) / sum(r["n"] for r in rows)
    pooled_e = sum(r["p_exec"] * r["n"] for r in rows) / sum(r["n"] for r in rows)
    cand = {
        "delta* at median contaminated rate": critical_interval(STEP, statistics.median(r["p_cont"] for r in rows), HALF_LIFE, THRESHOLD),
        "delta* at pooled contaminated rate": critical_interval(STEP, pooled_c, HALF_LIFE, THRESHOLD),
        "delta* at mean contaminated rate": critical_interval(STEP, statistics.mean(r["p_cont"] for r in rows), HALF_LIFE, THRESHOLD),
        "mean of per-trajectory delta* (contaminated)": statistics.mean(dc),
        "median of per-trajectory delta* (contaminated)": statistics.median(dc),
        "delta* at max contaminated rate": critical_interval(STEP, max(r["p_cont"] for r in rows), HALF_LIFE, THRESHOLD),
        "delta* at pooled execution-only rate": critical_interval(STEP, pooled_e, HALF_LIFE, THRESHOLD),
        "delta* at p = 0.50 (the published 24.5 s)": critical_interval(STEP, 0.50, HALF_LIFE, THRESHOLD),
    }
    n_latch_c = sum(1 for r in rows if r["d_cont"] is None)
    n_latch_e = sum(1 for r in rows if r["d_exec"] is None)
    fired_c = sum(1 for r in rows if r["m_cont"] is not None)
    fired_e = sum(1 for r in rows if r["m_exec"] is not None)
    ok_c = sum(1 for r in rows if r["ok_cont"])
    ok_e = sum(1 for r in rows if r["ok_exec"])
    off_c = [bin_of(r["d_cont"]) - bin_of(r["m_cont"][1])
             for r in rows if r["d_cont"] is not None and r["m_cont"] is not None]
    off_e = [bin_of(r["d_exec"]) - bin_of(r["m_exec"][1])
             for r in rows if r["d_exec"] is not None and r["m_exec"] is not None]

    O: List[str] = []
    w = O.append
    w("# The design rule's cliff, recomputed under both evidence definitions")
    w("")
    w(f"Generated by `scripts/cliff_recompute_exec.py` at `{sha()}`. Frozen "
      f"constants throughout (step {STEP}, threshold {THRESHOLD}, half-life "
      f"{HALF_LIFE} s); only the evidence stream changes.")
    w("")
    w("**Why this exists.** `PAPER3_DATAPACK.md` §5.1 quotes the closed form's "
      "cliff at **24.5 s**, computed from the *contaminated* per-action error "
      "rate — the frozen observer's `has_error()` over whatever text a tool "
      "returned, which fires on source files that merely mention `ValueError`. "
      "§6.3 makes the execution-only definition primary. The two were never "
      "reconciled, so the cliff was quoted in units the rest of Section 3 had "
      "stopped using.")
    w("")
    w("| quantity | contaminated (as published) | execution-only (primary) |")
    w("|---|---|---|")
    w(f"| per-action rate p, median | {statistics.median(r['p_cont'] for r in rows):.3f} | "
      f"{statistics.median(r['p_exec'] for r in rows):.3f} |")
    w(f"| **closed-form cliff δ\\*, median** | **{statistics.median(dc):.1f} s** | "
      f"**{statistics.median(de):.1f} s** |")
    w(f"| δ\\* range | {min(dc):.1f}–{max(dc):.1f} s | {min(de):.1f}–{max(de):.1f} s |")
    w(f"| trajectories with no δ\\* (latch: step·p ≥ θ) | {n_latch_c}/20 | {n_latch_e}/20 |")
    w(f"| trajectories that fire at all (measured) | {fired_c}/20 | {fired_e}/20 |")
    w(f"| **closed form inside measured interval** | **{ok_c}/20** | **{ok_e}/{fired_e}** |")
    w(f"| worst miss, grid bins | {max((abs(o) for o in off_c), default=0)} | "
      f"{max((abs(o) for o in off_e), default=0)} |")
    w("")
    w(f"**The cliff moves from {statistics.median(dc):.1f} s to "
      f"{statistics.median(de):.1f} s** — the same direction and roughly the "
      f"same order, since δ\\* is monotone in p and the execution-only rate is "
      f"about half the contaminated one. Quote one number with its definition "
      f"attached; do not quote 24.5 s beside execution-only counts.")
    w("")
    w("**Containment is not comparable across the two columns.** Under "
      "execution-only most trajectories never reach threshold at any grid dt, "
      f"so there is no measured interval to contain the prediction: only "
      f"{fired_e}/20 fire at all, against {fired_c}/20 contaminated. The "
      "denominator changes with the definition, which is the same starvation "
      "result Section 3 reports, arriving here as missing measurements.")
    w("")
    w("## Where the published 24.5 s comes from — it is real, and it is the wrong corpus")
    w("")
    w("`PAPER3_DATAPACK.md` §5.1 states the cliff as 24.5 s. The figure is "
      "**correct arithmetic on a different corpus under a different evidence "
      "definition**: it is δ\\* at a per-action error rate of exactly 0.50, "
      "which is what several Phase-9C runs scored under the *hook* definition "
      "(`delta_star_s: 24.52` in the run JSONs; `PHASE_B_READING.md` uses "
      "\"p≈0.5\" as its worked example). §5.1 then quotes it inside the "
      "**legacy 20-trajectory** containment result, whose median contaminated "
      "rate is 0.327 and whose cliff is 15.7 s.")
    w("")
    w("| candidate | value |")
    w("|---|---|")
    for k, v in cand.items():
        w(f"| {k} | {'latch' if v is None else f'{v:.1f} s'} |")
    w("")
    w("Two separate defects, and they need different fixes:")
    w("")
    w("1. **Wrong corpus in §5.1.** The sentence draws a conclusion about the "
      "legacy corpus and then quotes a 9C number. For that sentence the figure "
      f"is **{statistics.median(dc):.1f} s** contaminated, "
      f"**{statistics.median(de):.1f} s** execution-only.")
    w("2. **It is a hardcoded literal** in `scripts/make_draft_datapack.py`, "
      "unlike every other number in the pack, so regeneration cannot correct it "
      "and the pack's \"cannot drift from the results\" guarantee does not "
      "cover it. Whatever figure replaces it should be computed at generation "
      "time.")
    w("")
    w("| trajectory | n | p cont | δ* cont | measured cont | p exec | δ* exec | measured exec |")
    w("|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -x["p_exec"]):
        mc = "—" if r["m_cont"] is None else f"({r['m_cont'][0]:g}, {r['m_cont'][1]:g}]"
        me = "—" if r["m_exec"] is None else f"({r['m_exec'][0]:g}, {r['m_exec'][1]:g}]"
        dcs = "latch" if r["d_cont"] is None else f"{r['d_cont']:.1f}"
        des = "latch" if r["d_exec"] is None else f"{r['d_exec']:.1f}"
        w(f"| {r['id']} | {r['n']} | {r['p_cont']:.3f} | {dcs} | {mc} | "
          f"{r['p_exec']:.3f} | {des} | {me} |")
    w("")

    OUT.write_text("\n".join(O), encoding="utf-8")
    (ROOT / "data" / "swebench_pilot" / "_cliff_recompute.json").write_text(
        json.dumps({"rows": rows,
                    "median_delta_contaminated": statistics.median(dc),
                    "median_delta_execonly": statistics.median(de),
                    "fired_contaminated": fired_c, "fired_execonly": fired_e,
                    "contained_contaminated": ok_c, "contained_execonly": ok_e},
                   indent=1, default=str), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"median delta*: contaminated {statistics.median(dc):.1f}s  "
          f"execution-only {statistics.median(de):.1f}s")
    print(f"fired at all: contaminated {fired_c}/20  execution-only {fired_e}/20")
    print(f"contained: contaminated {ok_c}/20  execution-only {ok_e}/{fired_e}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
