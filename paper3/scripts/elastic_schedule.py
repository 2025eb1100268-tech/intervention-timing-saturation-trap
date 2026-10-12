"""Detection odds for a paced prober against the Elastic denied-topic rule's schedule.

DEPLOYED_MONITOR_CENSUS.md's boundary analysis of "Unusual High Denied Topic
Blocks Detected" (detection-rules c5678aa) reads these figures from the JSON
this writes; no figure there is typed by hand. The rule, as shipped:

    interval = "10m", from = "now-60m"   a run every 600 s, each looking back 3600 s
    Kibana buildTimeRangeFilter          the range is closed: [t - 3600, t]
    where ... count > 5                  it fires on six events

The attacker probes every s seconds from time 0; the schedule's phase u, unknown
to the attacker, is uniform on [0, 600). Runs fall at u + 600j.

EXACT. A run at t sees probes m-5..m (probe i at i*s) iff m*s <= t <= (m-5)*s + 3600.
The phases that catch a prober by time H are the union over m of those intervals
(cut at H), reduced mod 600; the share caught is its measure over 600, computed in
exact rational arithmetic. A burst of six probes is the case m = 5 alone.

MONTE CARLO CHECK, by a different route: draw phases, step through the runs,
count the probes inside each run's closed range, and fire on six. The script
fails if any Monte Carlo share is more than four standard errors from the exact
one, or differs from it at all where the exact share is 0 or 1.

    python scripts/elastic_schedule.py
    # writes data/swebench_pilot/external_monitors/elastic_schedule.json
"""
from __future__ import annotations

import json
import math
import random
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "swebench_pilot" / "external_monitors" / "elastic_schedule.json"

RULE_COMMIT = "c5678aa55127177cd11a23aab25a8715854bdae7"
RUN, LOOKBACK, N_FIRE = 600, 3600, 6          # interval, closed look-back, events to fire
WEEK = 7 * 86400
BURST_SPACINGS = ["600", "650", "700", "719.9"]
SUSTAINED_SPACINGS = ["700", "710", "719", "719.5", "719.9", "720.1"]
SWEEP = (600, 700, F(1, 10))                    # every spacing on this grid is checked exactly
SEED, N_BURST, N_SUSTAINED = 20261012, 100_000, 4_000


def exact_share(s: F, horizon=None, burst: bool = False) -> F:
    """Share of schedule phases with a run that sees six probes by `horizon`."""
    pieces = []
    m = N_FIRE - 1
    while True:
        lo, hi = m * s, (m - N_FIRE + 1) * s + LOOKBACK
        if horizon is not None:
            if lo > horizon:
                break
            hi = min(hi, F(horizon))
        if hi >= lo:
            a = lo % RUN
            b = a + (hi - lo)
            pieces.append((a, min(b, F(RUN))))
            if b > RUN:
                pieces.append((F(0), b - RUN))
        if burst:
            break
        m += 1
    pieces.sort()
    total, cur = F(0), None
    for a, b in pieces:
        if cur is None or a > cur[1]:
            if cur is not None:
                total += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur is not None:
        total += cur[1] - cur[0]
    return min(total / RUN, F(1))


def mc_share(s: float, n: int, rng: random.Random, horizon=None, burst: bool = False) -> float:
    """Monte Carlo over schedule phases: step through the runs and count probes in range."""
    end = horizon if horizon is not None else (N_FIRE - 1) * s + LOOKBACK
    last_probe = (N_FIRE - 1) if burst else None
    caught = 0
    for _ in range(n):
        t = rng.uniform(0, RUN)
        while t <= end:
            k_hi = math.floor(t / s)
            if last_probe is not None:
                k_hi = min(k_hi, last_probe)
            k_lo = max(0, math.ceil((t - LOOKBACK) / s))
            if k_hi - k_lo + 1 >= N_FIRE:
                caught += 1
                break
            t += RUN
    return caught / n


def agree(exact: float, mc: float, n: int) -> tuple:
    if exact in (0.0, 1.0):
        return mc == exact, 0.0
    se = math.sqrt(exact * (1 - exact) / n)
    return abs(mc - exact) <= 4 * se, abs(mc - exact) / se


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rng = random.Random(SEED)
    failures = []
    burst = []
    for s in BURST_SPACINGS:
        sf = F(s)
        ex = exact_share(sf, burst=True)
        formula = min(F(1), max(F(0), (LOOKBACK - (N_FIRE - 1) * sf) / RUN))
        if ex != formula:
            failures.append(f"burst at {s} s: exact {float(ex)} != (3600 - 5s)/600 = {float(formula)}")
        mc = mc_share(float(sf), N_BURST, rng, burst=True)
        ok, z = agree(float(ex), mc, N_BURST)
        if not ok:
            failures.append(f"burst at {s} s: Monte Carlo {mc} vs exact {float(ex)}")
        burst.append({"spacing_s": float(sf), "exact_share": float(ex), "formula_share": float(formula),
                      "monte_carlo_share": mc, "monte_carlo_z": round(z, 2)})
    sustained = []
    for s in SUSTAINED_SPACINGS:
        sf = F(s)
        ex = exact_share(sf, WEEK)
        mc = mc_share(float(sf), N_SUSTAINED, rng, WEEK)
        ok, z = agree(float(ex), mc, N_SUSTAINED)
        if not ok:
            failures.append(f"sustained at {s} s: Monte Carlo {mc} vs exact {float(ex)}")
        sustained.append({"spacing_s": float(sf), "exact_share": float(ex), "monte_carlo_share": mc,
                          "monte_carlo_z": round(z, 2)})
    lo, hi, step = SWEEP
    grid = [lo + k * step for k in range(int((hi - lo) / step) + 1)]
    below = [g for g in grid if exact_share(F(g), WEEK) < 1]
    if below:
        failures.append(f"sweep: caught within a week for every phase fails at {[float(g) for g in below[:5]]}")
    out = {
        "generator": "scripts/elastic_schedule.py",
        "rule": {"file": "rules/integrations/aws_bedrock/aws_bedrock_multiple_topic_policy_blocks_detected.toml",
                 "commit": RULE_COMMIT, "interval_s": RUN, "lookback_s": LOOKBACK, "range": "closed",
                 "fires_on_events": N_FIRE},
        "horizon_s": WEEK,
        "evading_spacing_above_s": LOOKBACK / (N_FIRE - 1),
        "burst": burst,
        "sustained_within_week": sustained,
        "sweep_all_caught_within_week": {"from_s": float(lo), "to_s": float(hi), "step_s": float(step),
                                         "spacings_checked": len(grid), "all_caught": not below},
        "monte_carlo": {"seed": SEED, "phases_burst": N_BURST, "phases_sustained": N_SUSTAINED,
                        "tolerance": "4 standard errors; exact agreement where the exact share is 0 or 1"},
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    for r in burst:
        print(f"burst      s = {r['spacing_s']:6g} s  exact {r['exact_share']:.4f}  MC {r['monte_carlo_share']:.4f}")
    for r in sustained:
        print(f"sustained  s = {r['spacing_s']:6g} s  exact {r['exact_share']:.4f}  MC {r['monte_carlo_share']:.4f}")
    print(f"sweep {float(lo):g}-{float(hi):g} s step {float(step):g}: "
          f"{'every phase caught within a week' if not below else 'NOT all caught'}")
    if failures:
        print("FAILED:\n  " + "\n  ".join(failures))
        return 1
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
