"""Does the budget-cadence identity hold for a TIME-WINDOW monitor?

Proposition 1 in the paper is stated for the exponential leaky integrator, but
its proof never uses the exponential. It uses only this: the monitor's
forgetting is a function of the ELAPSED TIME between the observations it
receives. That covers the far more common production shape --

    fire if at least N qualifying events fall in the last T seconds

-- which is fail2ban's (maxretry, findtime), Wazuh's (frequency, timeframe),
Sigma's correlation timespan, and every SIEM analytic window.

This checks the generalised proposition against an independent implementation,
and then asks the question that actually matters for deployment: at agent
cadence, does the CLOCK term in such a monitor do anything at all, or does the
evidence floor bind first?

Everything here is arithmetic on the frozen legacy corpus. The identity is a
regression check on the implementation, not evidence for the claim.

Run from repo root:  python scripts/window_identity.py
"""
from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heart_adapters.claude_code.trajectory import parse_trajectory_file  # noqa: E402
from generality_sweep import all_ids                                    # noqa: E402
from warning_sign_bracketing import traj_path                           # noqa: E402

OUT = ROOT / "data" / "swebench_pilot" / "WINDOW_IDENTITY.md"
SHELL_LEGACY = {"bash_tool"}
DT_GRID = (0.0, 1.0, 1.53, 5.0, 15.0, 30.0, 60.0, 150.0, 600.0)
R_GRID = (1, 2, 3, 5, 10, 20)
# Production defaults, quoted with their units, plus an agent-scaled setting.
SETTINGS = [
    ("fail2ban default (maxretry=5, findtime=600 s)", 5, 600.0),
    ("fail2ban sshd-style (maxretry=3, findtime=600 s)", 3, 600.0),
    ("short window (N=3, T=60 s)", 3, 60.0),
    ("tight window (N=3, T=10 s)", 3, 10.0),
]


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def window_budget(stream: Sequence[int], dt: float, r: int, offset: int,
                  n: int, T: float) -> List[bool]:
    """How a deployed monitor sees it: the agent acts every dt seconds and the
    monitor observes every r-th action, judging the window on REAL wall-clock
    timestamps, including the time it spent not looking."""
    obs = [i for i in range(offset, len(stream), r)]
    out = []
    for i in obs:
        t_i = i * dt
        cnt = sum(1 for j in obs
                  if j <= i and stream[j] and (t_i - j * dt) < T)
        out.append(cnt >= n)
    return out


def window_cadence(stream: Sequence[int], dt: float, r: int, offset: int,
                   n: int, T: float) -> List[bool]:
    """The same monitor at FULL budget on the subsampled stream, with the
    inter-observation interval stretched to r*dt."""
    sub = stream[offset::r]
    step = r * dt
    out = []
    for k in range(len(sub)):
        t_k = k * step
        cnt = sum(1 for m in range(k + 1)
                  if sub[m] and (t_k - m * step) < T)
        out.append(cnt >= n)
    return out


def main() -> int:
    streams = []
    for t in all_ids():
        ev = parse_trajectory_file(traj_path(t))
        streams.append([1 if (e.tool_name in SHELL_LEGACY and e.has_error()) else 0
                        for e in ev])

    # ---- the identity ----
    cells = mismatch = 0
    for s in streams:
        for dt in DT_GRID:
            for r in R_GRID:
                for off in range(r):
                    for _, n, T in SETTINGS:
                        a = window_budget(s, dt, r, off, n, T)
                        b = window_cadence(s, dt, r, off, n, T)
                        cells += 1
                        if a != b:
                            mismatch += 1

    # ---- does the clock term do anything at agent cadence? ----
    # The window holds at most floor(T / (r*dt)) + 1 observed actions. If that
    # is >= the session length the window never drops anything and the monitor
    # is a pure counter with floor n.
    rows = []
    for label, n, T in SETTINGS:
        for dt, cad in ((1.53, "Paper 2 loop"), (5.5, "9C harness")):
            for r in (1, 2, 5, 10, 20):
                cap = math.floor(T / (r * dt)) + 1          # observed actions in view
                med_obs = statistics.median(
                    [len(range(0, len(s), r)) for s in streams])
                fires = statistics.mean(
                    [sum(any(window_budget(s, dt, r, o, n, T)) for o in range(r)) / r
                     for s in streams])
                rows.append({"setting": label, "n": n, "T": T, "dt": dt,
                             "cadence": cad, "r": r, "window_actions": cap,
                             "median_observed": med_obs, "fire_rate": fires,
                             "clock_inert": cap >= med_obs})

    O: List[str] = []
    w = O.append
    w("# The budget-cadence identity for time-window monitors")
    w("")
    w(f"Generated by `scripts/window_identity.py` at `{sha()}`. Legacy corpus, "
      f"execution-only evidence, 20 trajectories.")
    w("")
    w("## 1. The proposition generalises")
    w("")
    w("Proposition 1 is stated for the exponential leaky integrator, but its "
      "proof uses only that forgetting is a function of the elapsed time "
      "between observations. The same argument covers **any** monitor with "
      "that property, including the rectangular form that dominates production "
      "alerting:")
    w("")
    w("> fire if at least *N* qualifying events fall within the last *T* seconds")
    w("")
    w("which is fail2ban's `maxretry`/`findtime`, Wazuh's rule `frequency`/"
      "`timeframe`, Sigma's correlation `timespan`, and the window of a SIEM "
      "analytic rule. Under a 1-in-r budget the monitor sees every r-th action "
      "while the clock keeps running, so the interval between the observations "
      "it receives is r·Δt — exactly the interval it would see at full budget "
      "from an agent acting r times more slowly.")
    w("")
    w(f"Checked against an independent implementation over {len(streams)} "
      f"trajectories × {len(DT_GRID)} intervals × {len(R_GRID)} budgets × every "
      f"sampling offset × {len(SETTINGS)} window settings: "
      f"**{mismatch} mismatches in {cells:,} cells**. Like Proposition 1's "
      f"19,360, this is a regression check on the implementation. The claim is "
      f"arithmetic: elapsed time between consecutive observations is r·Δt in "
      f"both constructions, and the evidence consumed is the same subsequence.")
    w("")
    w("**Why this matters for the paper's weakest point.** The wall-clock class "
      "is not defined by exponential decay. It is every monitor whose "
      "forgetting is indexed in seconds, and the rectangular window is the "
      "form production monitoring actually ships.")
    w("")
    w("## 2. At agent cadence, does the clock term do anything?")
    w("")
    w("A window of T seconds holds ⌊T/(r·Δt)⌋+1 observed actions. When that "
      "exceeds the session length the window never drops anything: the monitor "
      "is a **pure counter with floor N**, and the evidence floor binds rather "
      "than the clock. Fire rate averages every sampling offset.")
    w("")
    w("| setting | cadence | r | actions in window | median observed | clock inert? | fire rate |")
    w("|---|---|---|---|---|---|---|")
    for x in rows:
        w(f"| {x['setting']} | {x['cadence']} ({x['dt']} s) | {x['r']} | "
          f"{x['window_actions']} | {x['median_observed']:.0f} | "
          f"{'**yes**' if x['clock_inert'] else 'no'} | {x['fire_rate']:.0%} |")
    w("")
    inert = sum(1 for x in rows if x["clock_inert"])
    w(f"**{inert} of {len(rows)} configurations have an inert clock**: at agent "
      f"cadence a 600-second window spans more actions than an entire session, "
      f"so a production monitor tuned for human-timescale attacks degenerates "
      f"into the counter of Section 3 and is governed by its floor. The clock "
      f"term only becomes live at large r or at long cadence — which is "
      f"precisely the budget-cadence identity doing its work.")
    w("")
    w("This is the honest version of the paper's claim about clock-calibrated "
      "monitors: on agent streams the two constraints are ordered, and for "
      "production window defaults the floor is the one that binds first.")
    w("")
    w("**The reduction is the finding; the agreement is not evidence.** When the "
      "window spans the whole episode, \"N events in the last T seconds\" and "
      "\"N events so far\" are the same function on that input, so the window "
      "monitor's fire rate MUST equal the pure count floor's (N=5 → 60% = "
      "12/20; N=3 → 85% = 17/20). That equality is an identity and a regression "
      "check, not a cross-validation of two independent results — the same "
      "error this study has now made three times, after the tautological "
      "Spearman and the 16-of-16 replay agreement.")
    w("")

    OUT.write_text("\n".join(O), encoding="utf-8")
    (ROOT / "data" / "swebench_pilot" / "_window_identity.json").write_text(
        json.dumps({"mismatches": mismatch, "cells": cells, "rows": rows},
                   indent=1), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"identity: {mismatch} mismatches in {cells:,} cells")
    print(f"clock inert in {inert}/{len(rows)} configurations")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 1 if mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
