"""Decay-vs-event decomposition of the affective dynamics (Phase 2, Task 1c/1d).

Reads the fullstate_<id>.json artifacts (schema >= 1.1, which carry
`vector_post_decay`) and decomposes per-action change into a decay component
and an event component, then quantifies how much the engine transforms raw
rule outputs.

DEFINITIONS (per action n, n>=1; action 0 has no predecessor so is excluded
from decay accounting):
  post_decay[n] = vector_post_decay at action n  (state after inter-action
                  decay, before this action's event)
  post_event[n] = vector at action n             (state after this action's event)

  decay_delta(X)[n]  = X(post_decay[n]) - X(post_event[n-1])
  event_delta(X)[n]  = X(post_event[n]) - X(post_decay[n])

where X is a scalar functional of the vector (neg_sum_5 or frustration).

NOTE (see DT_AUDIT.md): on this replay pipeline the engine receives dt=0 on
every tick, so decay is a structural no-op. The decay component below is
therefore ~0 BY CONSTRUCTION, not as an empirical property of the affect
model. This is stated in the output report.

Usage:
    python scripts/decompose_dynamics.py            # all fullstate_* present
    python scripts/decompose_dynamics.py <traj_id> ...
Run from repository root.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

PILOT_DIR = Path("data/swebench_pilot")
NEG_5 = ("frustration", "anger", "fear", "confusion", "vengeance")
FROZEN_EPS = 0.01  # "decay moved neg_sum_5 by < this" => effectively frozen


def _check_cwd():
    if not PILOT_DIR.exists():
        sys.stderr.write(f"ERROR: run from repo root; {PILOT_DIR} not found "
                         f"(cwd {Path.cwd()}).\n")
        sys.exit(2)


def neg5(vec: Dict[str, float]) -> float:
    return sum(vec.get(e, 0.0) for e in NEG_5)


def discover() -> List[str]:
    return sorted(p.stem[len("fullstate_"):]
                  for p in PILOT_DIR.glob("fullstate_astropy__astropy-*.json"))


def analyze(traj_id: str) -> Dict[str, Any]:
    art = json.loads((PILOT_DIR / f"fullstate_{traj_id}.json").read_text(encoding="utf-8"))
    if "vector_post_decay" not in art["timeline"][0]:
        raise RuntimeError(f"{traj_id}: fullstate schema lacks vector_post_decay; "
                           f"regenerate with replay_full.py --force (schema >=1.1)")
    tl = art["timeline"]
    n = len(tl)

    # --- 1c: decay vs event split, neg_sum_5 and frustration ---
    decay_abs_n5 = event_abs_n5 = 0.0
    decay_abs_fr = event_abs_fr = 0.0
    frozen_actions = 0
    decomposed_actions = 0  # actions n>=1 we can attribute decay for

    for i in range(n):
        post_event = tl[i]["vector"]
        post_decay = tl[i]["vector_post_decay"]
        # event component exists for every action (event applied this step)
        event_abs_n5 += abs(neg5(post_event) - neg5(post_decay))
        event_abs_fr += abs(post_event["frustration"] - post_decay["frustration"])
        if i >= 1:
            prev_event = tl[i - 1]["vector"]
            d_n5 = neg5(post_decay) - neg5(prev_event)
            d_fr = post_decay["frustration"] - prev_event["frustration"]
            decay_abs_n5 += abs(d_n5)
            decay_abs_fr += abs(d_fr)
            decomposed_actions += 1
            if abs(d_n5) < FROZEN_EPS:
                frozen_actions += 1

    total_n5 = decay_abs_n5 + event_abs_n5
    total_fr = decay_abs_fr + event_abs_fr

    # --- 1d: engine transformation of rule outputs ---
    # For event-bearing actions: raw = sum of signal deltas requested by the
    # rules; realized = summed signed change across all 18 dims net of decay
    # (post_event - post_decay). Discrepancy = |raw - realized|, capturing
    # momentum bias + conflict softening + energy normalization.
    discrepancies = []
    for i in range(n):
        sig = tl[i]["signals_applied"]
        if not sig:
            continue
        raw = sum(s["delta"] for s in sig)
        post_event = tl[i]["vector"]
        post_decay = tl[i]["vector_post_decay"]
        realized = sum(post_event[k] - post_decay[k] for k in post_event)
        discrepancies.append(abs(raw - realized))
    mean_disc = (sum(discrepancies) / len(discrepancies)) if discrepancies else 0.0

    return {
        "traj": traj_id, "n": n,
        "decay_abs_n5": decay_abs_n5, "event_abs_n5": event_abs_n5,
        "decay_frac_n5": (decay_abs_n5 / total_n5) if total_n5 else 0.0,
        "event_frac_n5": (event_abs_n5 / total_n5) if total_n5 else 0.0,
        "decay_abs_fr": decay_abs_fr, "event_abs_fr": event_abs_fr,
        "decay_frac_fr": (decay_abs_fr / total_fr) if total_fr else 0.0,
        "event_frac_fr": (event_abs_fr / total_fr) if total_fr else 0.0,
        "frozen_actions": frozen_actions, "decomposed_actions": decomposed_actions,
        "frozen_frac": (frozen_actions / decomposed_actions) if decomposed_actions else 0.0,
        "n_event_actions": len(discrepancies),
        "mean_abs_discrepancy": mean_disc,
    }


def main():
    _check_cwd()
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or discover()
    rows = [analyze(t) for t in ids]

    out = []
    w = out.append
    w("# Dynamics Decomposition: decay vs. event")
    w("")
    w("Per-action change in affective state, split into a **decay** component "
      "(inter-action relaxation) and an **event** component (this action's "
      "applied signals, as transformed by the engine). Computed from "
      "`fullstate_<id>.json` (schema 1.1) using `vector` (post-event) and "
      "`vector_post_decay` (post-decay, pre-event).")
    w("")
    w("> **Structural caveat (see `DT_AUDIT.md`):** on this replay pipeline the "
      "engine receives `dt = 0` on every tick, so decay is a no-op. The decay "
      "component below is therefore ~0 **by construction of the pipeline**, not "
      "as a measured property of the affect model. Read the event column as "
      "\"all observed dynamics,\" and the decay column as a confirmation that "
      "no inter-action relaxation occurs in replay.")
    w("")

    w("## neg_sum_5: total variation attributable to decay vs. events")
    w("")
    w("Total variation = sum of |per-action deltas|. Decay deltas are over "
      "actions 1..n-1 (action 0 has no predecessor).")
    w("")
    w("| Trajectory | actions | sum |decay Δ| | sum |event Δ| | decay share | event share |")
    w("|---|---|---|---|---|---|")
    for r in rows:
        w(f"| {r['traj'].replace('astropy__astropy-','astropy-')} | {r['n']} | "
          f"{r['decay_abs_n5']:.4f} | {r['event_abs_n5']:.4f} | "
          f"{100*r['decay_frac_n5']:.1f}% | {100*r['event_frac_n5']:.1f}% |")
    w("")

    w("## frustration only: decay vs. events")
    w("")
    w("| Trajectory | sum |decay Δ| | sum |event Δ| | decay share | event share |")
    w("|---|---|---|---|---|")
    for r in rows:
        w(f"| {r['traj'].replace('astropy__astropy-','astropy-')} | "
          f"{r['decay_abs_fr']:.4f} | {r['event_abs_fr']:.4f} | "
          f"{100*r['decay_frac_fr']:.1f}% | {100*r['event_frac_fr']:.1f}% |")
    w("")

    w("## Frozen-by-decay actions")
    w("")
    w(f"Fraction of actions (n>=1) where decay moved neg_sum_5 by < {FROZEN_EPS}.")
    w("")
    w("| Trajectory | frozen / decomposed | fraction |")
    w("|---|---|---|")
    for r in rows:
        w(f"| {r['traj'].replace('astropy__astropy-','astropy-')} | "
          f"{r['frozen_actions']}/{r['decomposed_actions']} | {100*r['frozen_frac']:.1f}% |")
    w("")

    w("## Engine transformation of rule outputs (Task 1d)")
    w("")
    w("For event-bearing actions only: **raw** = sum of the per-emotion deltas "
      "the rules requested (`signals_applied`); **realized** = summed signed "
      "change across all 18 dimensions net of decay (`vector - vector_post_decay`). "
      "The discrepancy `|raw - realized|` captures the engine's momentum bias, "
      "conflict softening (opposed emotions reduced), and energy normalization.")
    w("")
    w("| Trajectory | event-bearing actions | mean |raw - realized| |")
    w("|---|---|---|")
    for r in rows:
        w(f"| {r['traj'].replace('astropy__astropy-','astropy-')} | "
          f"{r['n_event_actions']} | {r['mean_abs_discrepancy']:.4f} |")
    w("")

    # 3-sentence summary, data-driven
    mean_event_share = sum(r["event_frac_n5"] for r in rows) / len(rows)
    mean_frozen = sum(r["frozen_frac"] for r in rows) / len(rows)
    mean_disc = sum(r["mean_abs_discrepancy"] for r in rows) / len(rows)
    w("## Summary")
    w("")
    w(f"Across the {len(rows)} trajectories, events account for "
      f"{100*mean_event_share:.1f}% of neg_sum_5 total variation on average and "
      f"decay for the remainder, consistent with the dt=0 audit. On average "
      f"{100*mean_frozen:.1f}% of actions are frozen-by-decay (neg_sum_5 decay "
      f"move < {FROZEN_EPS}). The engine transforms raw rule outputs by a mean "
      f"absolute amount of {mean_disc:.4f} in summed-intensity terms on "
      f"event-bearing actions, i.e. the realized state change is not a "
      f"pass-through of the requested deltas.")

    report = "\n".join(out)
    out_path = PILOT_DIR / "DYNAMICS_DECOMPOSITION.md"
    out_path.write_text(report, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print(f"\nsaved: {out_path}")


if __name__ == "__main__":
    main()
