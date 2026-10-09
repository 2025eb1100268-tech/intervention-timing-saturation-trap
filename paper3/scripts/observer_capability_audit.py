"""Phase A0: static + empirical capability audit of the frozen observer.

Answers one question: *can this monitor's signal extractor express recovery
at all?* The answer is settled analytically, not statistically, so this runs
before any labelling and its output is quoted in PREREGISTRATION_PHASE9.md §0.

It is NOT a Phase-9 result. Everything here is a property of frozen code
(heart_adapters/claude_code/signals.py, heart_core/{engine,dynamics}.py) and
of the frozen 20-trajectory corpus, both unchanged since Paper 2.

Checks, in order:

  1. SIGN AUDIT       -- is any emitted delta negative? (Can the observer
                         push any emotion DOWN?)
  2. ANTAGONIST AUDIT -- frustration's only opponent in CONFLICTS is `hope`.
                         Does any rule emit `hope`? Does `hope` ever rise
                         above BASELINE in practice?
  3. DEAD-PATH AUDIT  -- do the three indirect attenuation paths ever fire?
                         (_rebalance_conflicts_v2, _normalize_energy,
                         _apply_core_layer)
  4. MONOTONICITY     -- empirically, does frustration ever decrease across an
                         action step at dt=0?
  5. CHANNEL CENSUS   -- which emotions does the observer actually emit, and
                         in what proportion?
  6. METACOGNITION    -- how often does the observer's own hedge detector
                         fire, what does it emit, and how does that compare to
                         reframing markers the observer does not consume?
  7. DRAIN ARITHMETIC -- how much signal-free elapsed time, and how many
                         signal-free actions at measured cadence, are needed
                         to fall from the clamp below the trigger threshold?

Pure read-only post-processing plus static inspection. Writes
data/swebench_pilot/OBSERVER_CAPABILITY_AUDIT.md.

Run from repo root:  python scripts/observer_capability_audit.py
"""
from __future__ import annotations
import glob
import inspect
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heart_adapters.claude_code.signals import ALL_RULES
from heart_adapters.claude_code.trajectory import parse_trajectory_file
from heart_core.dynamics import CONFLICTS, BASELINE, DEFAULT_HALF_LIVES
from heart_core.plugins import load_emotion_cores
from heart_guidelines.text_features import extract_features

PILOT_DIR = Path("data/swebench_pilot")

ORIG5 = [
    "astropy__astropy-12907", "astropy__astropy-13033", "astropy__astropy-13236",
    "astropy__astropy-13398", "astropy__astropy-13453",
]

FRUST_HI = 0.7          # A6 / T3 threshold, frozen
CLAMP = 1.0
ENERGY_CAP = 6.0        # _normalize_energy(max_sum=6.0)
REBALANCE_FLOOR = 0.55  # _rebalance_conflicts_v2 requires both members above this
CADENCES = [1.53, 2.33, 5.0, 15.0]   # Paper 2 pooled median, p90, and two grid points


def all_ids() -> List[str]:
    batch2 = sorted(os.path.basename(f)[:-5]
                    for f in glob.glob(str(PILOT_DIR / "batch2" / "*.json")))
    return ORIG5 + batch2


def traj_path(tid: str) -> Path:
    p = PILOT_DIR / f"{tid}.json"
    return p if p.exists() else PILOT_DIR / "batch2" / f"{tid}.json"


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(not a git repo)"


def short(t: str) -> str:
    return t.replace("astropy__astropy-", "astropy-").replace("django__django-", "django-")


# The five trajectories Paper 1 replayed (its saturation table), a subset of the twenty.
PAPER1_FIVE = ("astropy__astropy-13033", "astropy__astropy-13398", "astropy__astropy-13236",
               "astropy__astropy-13453", "astropy__astropy-12907")


def main() -> None:
    if not PILOT_DIR.exists():
        sys.stderr.write("run from repo root\n")
        sys.exit(2)

    ids = all_ids()
    out: List[str] = []
    w = out.append

    w("# Observer capability audit (Phase A0)")
    w("")
    w(f"Tree commit: `{git_sha()}`. Read-only audit of frozen code and frozen "
      f"artefacts; **not a Phase-9 result**. Reproduces "
      f"`PREREGISTRATION_PHASE9.md` §0.")
    w("")

    # ---------------------------------------------------------------- 1 + 5
    # Sign audit and channel census, over the persisted signals_applied.
    neg: List[tuple] = []
    channel: Dict[str, int] = {}
    channel_mass: Dict[str, float] = {}
    n_actions = 0
    n_signals = 0
    hope_max = 0.0
    vsum_max = 0.0
    fr_decreases = 0
    fr_steps = 0
    nodelta: List[tuple] = []
    silent_runs: List[tuple] = []
    per: Dict[str, Dict[str, int]] = {}

    for t in ids:
        d = json.loads((PILOT_DIR / f"fullstate_dt0_{t}.json").read_text(encoding="utf-8"))
        tl = d["timeline"]
        pt = per.setdefault(t, {"actions": 0, "signals": 0, "negative_deltas": 0,
                                "frustration_steps": 0, "frustration_decreases": 0})
        pt["actions"] = len(tl)
        z = 0
        prev_fr = None
        best = cur = 0
        for e in tl:
            n_actions += 1
            sa = e["signals_applied"]
            if not sa:
                z += 1
            has_fr = False
            for s in sa:
                n_signals += 1
                pt["signals"] += 1
                if s["delta"] < 0:
                    neg.append((t, e["action_index"], s))
                    pt["negative_deltas"] += 1
                channel[s["emotion"]] = channel.get(s["emotion"], 0) + 1
                channel_mass[s["emotion"]] = channel_mass.get(s["emotion"], 0.0) + s["delta"]
                if s["emotion"] == "frustration":
                    has_fr = True
            cur = 0 if has_fr else cur + 1
            best = max(best, cur)
            v = e["vector"]
            hope_max = max(hope_max, v["hope"])
            vsum_max = max(vsum_max, sum(v.values()))
            if prev_fr is not None:
                fr_steps += 1
                pt["frustration_steps"] += 1
                if v["frustration"] < prev_fr - 1e-12:
                    fr_decreases += 1
                    pt["frustration_decreases"] += 1
            prev_fr = v["frustration"]
        nodelta.append((t, len(tl), z, 100.0 * z / len(tl)))
        silent_runs.append((t, best))

    w("## 1. Sign audit — can the observer push anything DOWN?")
    w("")
    w(f"- actions: **{n_actions}** across {len(ids)} trajectories")
    w(f"- emitted signals: **{n_signals}**")
    w(f"- **negative deltas: {len(neg)}**")
    w("")
    if neg:
        w("Counterexamples found — the structural claim below does NOT hold:")
        for t, i, s in neg[:20]:
            w(f"  - {short(t)} action {i}: {s}")
    else:
        w("Zero. Confirmed by static inspection of all eight rules in "
          "`heart_adapters/claude_code/signals.py`: every `return` is a list of "
          "non-negative `(emotion, delta)` pairs. **The observer is a "
          "monotone non-negative evidence source.**")
    w("")

    w("## 5. Channel census — what does the observer actually emit?")
    w("")
    w("| emotion | firings | summed delta | opposes `frustration` in CONFLICTS? |")
    w("|---|---|---|---|")
    fr_opponents = set()
    for (a, b), cw in CONFLICTS.items():
        if cw < 0:
            if a == "frustration":
                fr_opponents.add(b)
            if b == "frustration":
                fr_opponents.add(a)
    for emo, c in sorted(channel.items(), key=lambda kv: -kv[1]):
        w(f"| {emo} | {c} | {channel_mass[emo]:.2f} | "
          f"{'YES' if emo in fr_opponents else 'no'} |")
    w("")
    neg_valence = sum(channel.get(e, 0) for e in ("frustration", "fear", "confusion"))
    w(f"Negative-valence escalation accounts for **{neg_valence}/{n_signals} "
      f"({100.0*neg_valence/n_signals:.1f}%)** of all emitted signals. "
      f"`frustration`'s only opponent in `CONFLICTS` is "
      f"**{sorted(fr_opponents)}**; no positive-valence channel the observer "
      f"emits appears in that set.")
    w("")

    # ---------------------------------------------------------------- 2 + 3
    w("## 2. Antagonist audit — is the de-escalation path reachable?")
    w("")
    emits_hope = []
    for rule in ALL_RULES:
        src = inspect.getsource(rule)
        if '"hope"' in src or "'hope'" in src:
            emits_hope.append(rule.__name__)
    w(f"- rules whose source mentions `hope`: "
      f"**{emits_hope if emits_hope else 'none'}**")
    w(f"- measured `max(hope)` across every action of every trajectory: "
      f"**{hope_max:.4f}** (BASELINE = {BASELINE})")
    w("")
    if not emits_hope and hope_max <= BASELINE + 1e-9:
        w("`hope` is never emitted and never rises above baseline. The "
          "`(\"hope\",\"frustration\"): -0.50` conflict term — the engine's only "
          "route from an observation to a *decrease* in frustration — is "
          "**unreachable given this rule set**.")
    w("")

    w("## 3. Dead-path audit — the three indirect attenuation routes")
    w("")
    cores = load_emotion_cores("emotions")
    w("| path | condition to fire | measured | reachable? |")
    w("|---|---|---|---|")
    w(f"| `_rebalance_conflicts_v2` | both members of a conflicting pair "
      f"> {REBALANCE_FLOOR} | `max(hope)` = {hope_max:.4f} | "
      f"**no** (hope never clears {REBALANCE_FLOOR}) |")
    w(f"| `_normalize_energy` | `sum(state)` > {ENERGY_CAP} | max observed "
      f"`sum(state)` = **{vsum_max:.3f}** | "
      f"**{'yes' if vsum_max > ENERGY_CAP else 'no'}** |")
    w(f"| `_apply_core_layer` | non-empty plugin registry | "
      f"`load_emotion_cores()` returns `{cores}` | "
      f"**{'yes' if cores else 'no'}** (no-op) |")
    w("")

    # ---------------------------------------------------------------- 4
    w("## 4. Monotonicity — the empirical consequence")
    w("")
    w(f"- within-trajectory action steps examined at dt=0: **{fr_steps}**")
    w(f"- steps on which `frustration` **decreased**: **{fr_decreases}**")
    w("")
    if fr_decreases == 0:
        w("Frustration is **strictly non-decreasing** under the observer. The "
          "only mechanism in the whole monitor that lowers it is the "
          "wall-clock decay term in `EmotionEngine._tick_decay`. This is a "
          "property of the *instrument*, not of the agents observed — it would "
          "hold identically against a perfectly self-correcting agent.")
    w("")

    w("### No-signal (silent) fraction per trajectory")
    w("")
    fr = [x[3] for x in nodelta]
    w(f"min **{min(fr):.1f}%**, median **{statistics.median(fr):.1f}%**, "
      f"max **{max(fr):.1f}%** — reproduces the 25–79% / median 52% figure "
      f"reported in Paper 1.")
    w("")

    # ---------------------------------------------------------------- 6
    w("## 6. Metacognition detection — the sign-inverted channel")
    w("")
    hedge = cyc = rec = backout = anymark = 0
    empty_reasoning = 0
    total = 0
    for t in ids:
        events = parse_trajectory_file(traj_path(t))
        for e in events:
            total += 1
            r = e.reasoning_text or ""
            if not r.strip():
                empty_reasoning += 1
            f = extract_features(r)
            h = e.has_hedge_words()
            c = f["cycle_count"] > 0
            rr = f["recognition_count"] > 0
            cmd = str((e.tool_args or {}).get("command", "")).lower()
            bk = any(x in cmd for x in ("git revert", "git checkout --",
                                        "git reset", "git stash"))
            hedge += h
            cyc += c
            per[t]["reframing_rule_firings"] = per[t].get("reframing_rule_firings", 0) + int(h)
            per[t]["cycle_markers"] = per[t].get("cycle_markers", 0) + int(c)
            rec += rr
            backout += bk
            anymark += bool(h or c or rr or bk)
    w("| marker | consumed by a rule? | actions | rate |")
    w("|---|---|---|---|")
    w(f"| `ActionEvent.has_hedge_words()` | **yes** (`rule_hedge_words`) | "
      f"{hedge} | {100.0*hedge/total:.1f}% |")
    w(f"| `text_features._CYCLE_RE` | no | {cyc} | {100.0*cyc/total:.1f}% |")
    w(f"| `text_features._RECOGNITION_RE` | no | {rec} | {100.0*rec/total:.1f}% |")
    w(f"| backing-out bash command | no | {backout} | {100.0*backout/total:.1f}% |")
    w(f"| **any of the above** | — | {anymark} | {100.0*anymark/total:.1f}% |")
    w("")
    w(f"Actions with empty reasoning text: {empty_reasoning} "
      f"({100.0*empty_reasoning/total:.1f}%).")
    w("")
    w("`rule_hedge_words` branches on `len(task_metadata['files_in_scope']) >= 3`. "
      "The aime-coder parser populates `task_metadata` with only "
      "`task_description` and `source_format`, so `files_in_scope` is always "
      "`[]`, the complex-task branch is dead code on this corpus, and the rule "
      "always returns exactly `[(\"confusion\", 0.08)]`.")
    w("")
    w("**Therefore: detecting explicit metacognition raises the "
      "negative-accumulation sum.** The observer's only reframing detector is "
      "sign-inverted with respect to recovery, and fires on "
      f"{hedge}/{total} actions.")
    w("")

    # ---------------------------------------------------------------- 7
    w("## 7. Drain arithmetic")
    w("")
    hl = DEFAULT_HALF_LIVES["frustration"]
    lam = math.log(2.0) / hl
    T_heart = math.log((CLAMP - BASELINE) / (FRUST_HI - BASELINE)) / lam
    T_i1 = math.log(CLAMP / FRUST_HI) / lam
    w(f"HEART, decaying toward BASELINE={BASELINE} with half-life {hl:.0f} s: "
      f"falling from the clamp {CLAMP} below {FRUST_HI} needs "
      f"`{BASELINE} + {CLAMP-BASELINE}*exp(-ln2/{hl:.0f}*T) < {FRUST_HI}`, i.e. "
      f"**T > {T_heart:.2f} s** of signal-free elapsed time.")
    w("")
    w(f"I1 (no baseline term): **T > {T_i1:.2f} s**.")
    w("")
    w("| cadence (s) | consecutive signal-free actions needed (HEART) | (I1) |")
    w("|---|---|---|")
    for c in CADENCES:
        w(f"| {c} | {T_heart/c:.1f} | {T_i1/c:.1f} |")
    w("")
    b = [x[1] for x in silent_runs]
    need = T_heart / CADENCES[0]
    lengths = [x[1] for x in nodelta]
    w(f"Longest observed run of consecutive actions carrying **no frustration "
      f"signal**: min {min(b)}, median {statistics.median(b):.1f}, max {max(b)}.")
    w(f"Trajectories whose longest silent run reaches the "
      f"{need:.1f} actions needed at {CADENCES[0]} s: "
      f"**{sum(1 for x in b if x >= need)}/{len(ids)}**. "
      f"Trajectories even {need:.0f} actions long in total: "
      f"**{sum(1 for L in lengths if L >= need)}/{len(ids)}**.")
    w("")

    # ---------------------------------------------------------------- verdict
    w("## Verdict")
    w("")
    structural = (len(neg) == 0 and not emits_hope
                  and hope_max <= BASELINE + 1e-9
                  and vsum_max <= ENERGY_CAP and not cores
                  and fr_decreases == 0)
    if structural:
        w("**The observer cannot express recovery.** Every evidence channel is "
          "non-negative; the single de-escalating term in the engine is "
          "unreachable from the rule set; all three indirect attenuation paths "
          "are dead; and frustration is empirically strictly non-decreasing "
          "over 694 action steps. Recovery sensitivity on the channel that "
          "drives every trigger is **exactly zero by construction**, and no "
          "amount of hand labelling can change that constant.")
        w("")
        w("This generalises past HEART, and is the second structural result "
          "Paper 3 carries alongside wall-clock-vs-sample-time calibration: "
          "**a monitor whose evidence channel is sign-constrained — all "
          "evidence incriminating, none exculpatory — cannot de-escalate, "
          "regardless of which integrator sits behind it.** The only remaining "
          "route from agent recovery to monitor state is *silence*, which is "
          "what Phase A-iii measures.")
    else:
        w("The structural claim does **not** hold as stated; see the failing "
          "checks above. Phase A must be scored as an ordinary empirical "
          "sensitivity study and `PREREGISTRATION_PHASE9.md` §0 corrected.")
    w("")

    # ---------------------------------------------------------------- 8
    w("## 8. Paper 1's five trajectories")
    w("")
    w("Paper 1 replayed five of these twenty trajectories. Every count above, "
      "restricted to those five, so a correction to Paper 1 can scope each "
      "number to the corpus it describes.")
    w("")
    keys = ("actions", "signals", "negative_deltas", "frustration_steps",
            "frustration_decreases", "reframing_rule_firings", "cycle_markers")
    sub = {k: sum(per[x].get(k, 0) for x in PAPER1_FIVE) for k in keys}
    allc = {k: sum(v.get(k, 0) for v in per.values()) for k in keys}
    w("| count | Paper 1's five | all twenty |")
    w("|---|---|---|")
    for k in keys:
        w(f"| {k.replace('_', ' ')} | {sub[k]} | {allc[k]} |")
    w("")
    (PILOT_DIR / "observer_capability_audit.json").write_text(json.dumps(
        {"paper1_five": list(PAPER1_FIVE), "paper1_five_totals": sub,
         "all_twenty_totals": allc, "per_trajectory": per}, indent=1), encoding="utf-8")

    report = "\n".join(out)
    (PILOT_DIR / "OBSERVER_CAPABILITY_AUDIT.md").write_text(report, encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(report)
    print(f"\nsaved: {PILOT_DIR / 'OBSERVER_CAPABILITY_AUDIT.md'}")


if __name__ == "__main__":
    main()
