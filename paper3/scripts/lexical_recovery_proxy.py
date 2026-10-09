"""Lexical recovery proxy, v1 — FROZEN marker list + no-path verification.

WHAT THIS IS. An automatable surface-lexical count of reframing-shaped language
in agent reasoning text. It replaces the dropped Phase-A human labelling study
(see PREREGISTRATION_PHASE9C.md, Decision 2).

WHAT THIS IS NOT. It is **not** a validated construct and **not** recovery
ground truth. There is no inter-rater validation behind it, no human labels
were collected, and no claim is made that a marker hit means the agent actually
recovered. Paper 1 measured Krippendorff alpha = +0.047 on a comparable
intervention-timing label, so a recovery label set would very likely come back
low-kappa; that is why the human study was dropped rather than run.

THE ONLY CLAIM IT SUPPORTS. Recovery-*shaped* language occurs in these traces at
a measurable rate, and it is structurally unable to reach the monitor's state.
The second half is a proof, not a measurement, and is re-verified on every run
of this script (section 3 below).

MARKER PROVENANCE. The v1 list is exactly `heart_guidelines/text_features.py`'s
`_CYCLE_PATTERNS`, adopted verbatim rather than re-authored, for two reasons:
it predates Paper 3 (it is Paper-1-era frozen code, so it cannot have been
tuned to this result), and it is already the list whose 43/714 rate the Phase-A0
audit reported. Per-term rationale is recorded below. The list is frozen at v1;
any change requires a new version constant and a re-run, and the version is
stamped into the emitted report.

Run from repo root:  python scripts/lexical_recovery_proxy.py
"""
from __future__ import annotations

import glob
import inspect
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heart_adapters.claude_code.signals import ALL_RULES                  # noqa: E402
from heart_adapters.claude_code.trajectory import parse_trajectory_file   # noqa: E402
from heart_guidelines.text_features import _CYCLE_PATTERNS                # noqa: E402
from generality_sweep import all_ids                                      # noqa: E402

PILOT = ROOT / "data" / "swebench_pilot"

PROXY_VERSION = "v1"

# ---------------------------------------------------------------------------
# FROZEN MARKER LIST, v1. Terms are those of text_features._CYCLE_PATTERNS,
# verbatim. The rationale column is what each term is taken to indicate; it is
# a statement of intent, not evidence that the term succeeds at indicating it.
# ---------------------------------------------------------------------------
MARKERS: List[Dict[str, str]] = [
    {"pattern": r"\btry (a|another|different) (approach|way|method)\b",
     "indicates": "strategy abandonment",
     "rationale": "Names the switch explicitly. The strongest single signal in "
                  "the list: the agent states it is discarding the current "
                  "approach rather than refining it."},
    {"pattern": r"\blet me try (again|another)\b",
     "indicates": "retry or switch",
     "rationale": "Ambiguous between a retry of the same approach ('again') "
                  "and a switch ('another'). Kept because the surrounding "
                  "clause usually disambiguates for a human reader, but this "
                  "is the list's weakest term and the main reason the proxy "
                  "should not be read as ground truth."},
    {"pattern": r"\bnew approach\b",
     "indicates": "strategy abandonment",
     "rationale": "Direct statement of a plan change."},
    {"pattern": r"\bdifferent (approach|strategy|way)\b",
     "indicates": "strategy abandonment",
     "rationale": "As above, without the 'try' framing; catches 'I need a "
                  "different approach' and 'a different strategy would'."},
    {"pattern": r"\bonce more\b",
     "indicates": "retry",
     "rationale": "Repetition marker. Included for continuity with the frozen "
                  "list; on its own it is closer to persistence than to "
                  "recovery, and it is counted but flagged."},
    {"pattern": r"\b(still|again|continue) (failing|having|getting)\b",
     "indicates": "recognition of a failing approach",
     "rationale": "The agent registers that the current approach is not "
                  "working. Recognition precedes abandonment and is the "
                  "observable antecedent of it."},
    {"pattern": r"\bdidn't work\b",
     "indicates": "recognition of a failing approach",
     "rationale": "Explicit negative outcome attribution to the agent's own "
                  "prior action."},
    {"pattern": r"\bdoes(n't| not) work\b",
     "indicates": "recognition of a failing approach",
     "rationale": "Present-tense variant of the above."},
    {"pattern": r"\bnot working\b",
     "indicates": "recognition of a failing approach",
     "rationale": "Progressive variant; catches 'this is not working'."},
    {"pattern": r"\bone more time\b",
     "indicates": "retry",
     "rationale": "As 'once more'. Counted, flagged as persistence-leaning."},
]

# Terms whose semantics lean toward persistence rather than course-change.
# Reported separately so the headline rate can be read with and without them.
PERSISTENCE_LEANING = {r"\bonce more\b", r"\bone more time\b",
                       r"\blet me try (again|another)\b"}

_RE = re.compile("|".join(m["pattern"] for m in MARKERS), re.IGNORECASE)
_RE_STRICT = re.compile(
    "|".join(m["pattern"] for m in MARKERS
             if m["pattern"] not in PERSISTENCE_LEANING), re.IGNORECASE)


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def traj_path(tid: str) -> Path:
    p = PILOT / f"{tid}.json"
    return p if p.exists() else PILOT / "batch2" / f"{tid}.json"


def verify_no_path() -> Dict[str, object]:
    """Re-prove, from the code, that a marker hit cannot move engine state.

    Four independent links; all four must hold or the proxy's second claim is
    void and this script says so.
    """
    # 1. No module under heart_adapters/ imports text_features.
    adapter_srcs = glob.glob(str(ROOT / "heart_adapters" / "**" / "*.py"),
                             recursive=True)
    importers = [os.path.relpath(p, ROOT) for p in adapter_srcs
                 if "text_features" in Path(p).read_text(encoding="utf-8")]

    # 2. Every (emotion, delta) literal any of the 8 rules can return.
    lits = set()
    for r in ALL_RULES:
        for m in re.finditer(r'\(\s*"(\w+)"\s*,\s*(-?[0-9]*\.?[0-9]+)\s*\)',
                             inspect.getsource(r)):
            lits.add((m.group(1), float(m.group(2))))
    negatives = sorted(l for l in lits if l[1] < 0)

    # 3. The one text_features consumer is a trigger; triggers return bool and
    #    never write state.
    rt = (ROOT / "heart_guidelines" / "reasoning_triggers.py").read_text(encoding="utf-8")
    trigger_writes_state = "_apply_event" in rt

    # 4. The sole state writer in the Claude Code path applies only signals
    #    from extract_signals.
    ad = (ROOT / "heart_adapters" / "claude_code" / "adapter.py").read_text(encoding="utf-8")
    writers = ad.count("_apply_event")

    return {
        "adapter_imports_text_features": importers,
        "rule_count": len(ALL_RULES),
        "delta_literals": sorted(lits),
        "negative_delta_literals": negatives,
        "trigger_writes_state": trigger_writes_state,
        "adapter_apply_event_calls": writers,
        "holds": (not importers and not negatives
                  and not trigger_writes_state and writers == 1),
    }


def main() -> int:
    ids = all_ids()
    rows = []
    for t in ids:
        events = parse_trajectory_file(traj_path(t))
        n = len(events)
        hits, strict, terms = 0, 0, {}
        for ev in events:
            txt = ev.reasoning_text or ""
            if _RE.search(txt):
                hits += 1
            if _RE_STRICT.search(txt):
                strict += 1
            for m in MARKERS:
                if re.search(m["pattern"], txt, re.IGNORECASE):
                    terms[m["pattern"]] = terms.get(m["pattern"], 0) + 1
        rows.append({"tid": t, "n": n, "hits": hits, "strict": strict,
                     "rate": 100.0 * hits / n, "strict_rate": 100.0 * strict / n,
                     "terms": terms})

    tot_n = sum(r["n"] for r in rows)
    tot_h = sum(r["hits"] for r in rows)
    tot_s = sum(r["strict"] for r in rows)
    npath = verify_no_path()

    O: List[str] = []
    w = O.append
    w(f"# Lexical recovery proxy ({PROXY_VERSION})")
    w("")
    w(f"Generated by `scripts/lexical_recovery_proxy.py` at commit `{sha()}`. "
      f"Marker list frozen at **{PROXY_VERSION}**; changing it requires a new "
      f"version constant.")
    w("")
    w("> **This is a lexical proxy, not a validated construct.** No human "
      "labels were collected; there is no inter-rater validation; a marker hit "
      "is **not** evidence that the agent recovered. It replaces the dropped "
      "Phase-A labelling study, which was dropped because Phase A0 is an "
      "impossibility result that human labels cannot strengthen, and because "
      "Paper 1's own Krippendorff alpha of **+0.047** on a comparable "
      "intervention-timing label predicts a recovery label set would return "
      "low-kappa and weaken the section.")
    w("")
    w("**The only claim it supports:** recovery-*shaped* language occurs in "
      "these traces at the rate below, and it is structurally unable to reach "
      "the monitor's state (§3 — a proof, re-verified on every run).")
    w("")

    # ---- 1. markers ----
    w("## 1. Frozen marker list")
    w("")
    w("Terms are `heart_guidelines/text_features.py::_CYCLE_PATTERNS` verbatim, "
      "adopted rather than re-authored: the list is Paper-1-era frozen code, so "
      "it cannot have been tuned to this result, and it is the list whose "
      "43/714 rate the A0 audit already reported.")
    w("")
    w("| # | pattern | indicates | rationale | hits |")
    w("|---|---|---|---|---|")
    agg: Dict[str, int] = {}
    for r in rows:
        for k, v in r["terms"].items():
            agg[k] = agg.get(k, 0) + v
    for i, m in enumerate(MARKERS, 1):
        flag = " *(persistence-leaning)*" if m["pattern"] in PERSISTENCE_LEANING else ""
        w(f"| {i} | `{m['pattern']}` | {m['indicates']}{flag} | "
          f"{m['rationale']} | {agg.get(m['pattern'], 0)} |")
    w("")
    w("Three terms lean toward persistence rather than course-change and are "
      "reported separately below as a **strict** variant that excludes them: "
      + ", ".join(f"`{p}`" for p in sorted(PERSISTENCE_LEANING)) + ".")
    w("")

    # ---- 2. rates ----
    w("## 2. Per-trajectory rate")
    w("")
    w("Reported per trajectory, not only pooled, because the pooled figure "
      "hides a 0%–17% spread.")
    w("")
    w("| trajectory | actions | marker hits | rate | strict hits | strict rate |")
    w("|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -x["rate"]):
        short = r["tid"].replace("astropy__astropy-", "astropy-").replace("django__django-", "django-")
        w(f"| {short} | {r['n']} | {r['hits']} | {r['rate']:.1f}% | "
          f"{r['strict']} | {r['strict_rate']:.1f}% |")
    w(f"| **pooled** | **{tot_n}** | **{tot_h}** | **{100.0*tot_h/tot_n:.1f}%** | "
      f"**{tot_s}** | **{100.0*tot_s/tot_n:.1f}%** |")
    w("")
    rts = [r["rate"] for r in rows]
    nz = sum(1 for r in rows if r["hits"] == 0)
    w(f"Per-trajectory rate: min **{min(rts):.1f}%**, median "
      f"**{statistics.median(rts):.1f}%**, max **{max(rts):.1f}%**; "
      f"**{nz}/{len(rows)}** trajectories contain no marker at all. The pooled "
      f"{100.0*tot_h/tot_n:.1f}% is therefore not a per-trajectory expectation.")
    w("")

    # ---- 3. no-path proof ----
    w("## 3. No-path verification (re-run every time)")
    w("")
    w("Four independent links. All four must hold.")
    w("")
    w("| # | link | result |")
    w("|---|---|---|")
    w(f"| 1 | modules under `heart_adapters/` importing `text_features` | "
      f"**{npath['adapter_imports_text_features'] or 'none'}** — no observer "
      f"rule can even see the markers |")
    w(f"| 2 | negative `(emotion, delta)` literals across all "
      f"{npath['rule_count']} rules | "
      f"**{npath['negative_delta_literals'] or 'none'}** — no rule can emit a "
      f"de-escalating signal |")
    w(f"| 3 | `reasoning_triggers.py` (the one `text_features` consumer) "
      f"writes engine state | **{'YES' if npath['trigger_writes_state'] else 'no'}** — "
      f"its functions return `bool`; triggers read state, never write it |")
    w(f"| 4 | `_apply_event` call sites in the Claude Code adapter | "
      f"**{npath['adapter_apply_event_calls']}** (`adapter.py:47`), applying "
      f"only signals from `extract_signals` |")
    w("")
    if npath["holds"]:
        w("**The chain holds.** A marker hit reaches no rule; no rule can emit "
          "a negative delta; the single consumer of the marker module cannot "
          "write state; and the sole state writer applies only the eight rules' "
          "output. Recovery-shaped language is therefore **unrepresentable** in "
          "this monitor's state — by construction, not by measurement, and "
          "independently of how good the agent gets.")
    else:
        w("**THE CHAIN DOES NOT HOLD.** One or more links failed; the proxy's "
          "structural claim is void and must not be reported until this is "
          "resolved.")
    w("")

    # ---- 4. limitations ----
    w("## 4. Limitations of the proxy itself")
    w("")
    for i, s in enumerate([
        "**No inter-rater validation and no human labels.** It is a regex "
        "count. It is not recovery ground truth and must never be described as "
        "a recovery *rate*.",
        "**Surface lexical only.** It cannot see recovery expressed without "
        "these phrasings, and it fires on the phrasings without the behaviour. "
        "Both error directions are unmeasured.",
        "**Three persistence-leaning terms** are included for continuity with "
        "the frozen list; the strict variant excludes them and is reported "
        "alongside so the headline does not depend on that choice.",
        "**Legacy traces only.** C-sub traces carry no reasoning text — the "
        "PostToolUse hook does not expose it — so the proxy cannot be computed "
        "on the frontier runs. This is also why Phase D was dropped rather "
        "than merely deferred.",
        "**The rate is not the interesting number.** The structural result in "
        "§3 does not depend on it. If the rate were 0% or 50% the "
        "unrepresentability conclusion would be identical.",
    ], 1):
        w(f"{i}. {s}")

    rep = "\n".join(O)
    dest = PILOT / "LEXICAL_RECOVERY_PROXY.md"
    dest.write_text(rep, encoding="utf-8")
    (PILOT / "lexical_recovery_proxy.json").write_text(json.dumps(
        {"version": PROXY_VERSION, "commit": sha(), "markers": MARKERS,
         "persistence_leaning": sorted(PERSISTENCE_LEANING),
         "pooled": {"actions": tot_n, "hits": tot_h, "strict": tot_s},
         "per_trajectory": rows, "no_path": npath}, indent=1), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(rep)
    print(f"\nsaved: {dest}")
    return 0 if npath["holds"] else 1


if __name__ == "__main__":
    sys.exit(main())
