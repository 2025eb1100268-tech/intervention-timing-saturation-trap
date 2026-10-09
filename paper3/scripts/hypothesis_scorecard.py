"""Paper 3's hypothesis scorecard: every pre-registered prediction, as originally
scored and as corrected, with retired and descriptive ones kept distinct.

Scores are not retyped from memory. Each entry names the generated artefact
that scored it and a pattern that must match there; if an artefact changes and
the scorecard does not, this script fails. Pre-registration commits come from
git (the commit that added the file, then every later commit to it).

Paper 2's hypotheses (H1-H9, Phases 7-8) are scored in Paper 2 and not
repeated here.

Run from repo root:  python scripts/hypothesis_scorecard.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "data" / "swebench_pilot"
OUT_MD = PILOT / "HYPOTHESIS_SCORECARD.md"
OUT_JSON = PILOT / "hypothesis_scorecard.json"

PREREGS = {
    "Phase 9": "PREREGISTRATION_PHASE9.md",
    "Phase 9 addendum C": "PREREGISTRATION_PHASE9_ADDENDUM_C.md",
    "Phase 9C": "PREREGISTRATION_PHASE9C.md",
    "Phase 9D": "PREREGISTRATION_PHASE9D_OPUS55.md",
}

# kind: confirmatory | retired | descriptive (pre-registered direction, scored descriptively)
H = [
    {"id": "H10", "prereg": "Phase 9", "kind": "retired",
     "claim": "Frontier agents act faster than Paper 2's gpt-5.4-mini loop.",
     "original": "Retired 2026-09-10 before any cadence result; unscored.", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"\*\*H10\*\* cadence[^|]*\| \*\*2026-09-10\*\*")]},
    {"id": "H11", "prereg": "Phase 9", "kind": "retired",
     "claim": "Within-run inter-action intervals are bimodal.",
     "original": "Retired 2026-09-10: unscoreable per run at these session lengths; unscored.", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"\*\*H11\*\* bimodality[^|]*\| \*\*2026-09-10\*\*")]},
    {"id": "H12", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "At least 25% of runs cross the critical band within a run (pilot).",
     "original": "Opus FALSIFIED, then PARTIAL 1/5 once the operator's own record was removed from the window (b5fa412); Fable FALSIFIED 0/5. Pilot only; descriptive in 9C.",
     "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H12 within-run stability \| ≥25% band crossings \| Opus \*\*PARTIAL\*\* 1/5; Fable \*\*FALSIFIED\*\* 0/5"),
                  ("WITHDRAWALS_AND_ERRATA.md", r"H12 FALSIFIED → PARTIAL")]},
    {"id": "H13", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "Fewer than 20% of clamped runs drain below threshold (pilot).",
     "original": "FALSIFIED in both arms, though not by its mechanism: Opus never clamped.", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H13 recovery/drain \| <20% of clamped runs drain \| \*\*FALSIFIED\*\* both arms")]},
    {"id": "H14a", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "The sample-time CUSUM is dt-invariant at every budget.",
     "original": "SUPPORTED (20/20).", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H14a I2 dt-invariant at every r \| SUPPORTED \(20/20\)")]},
    {"id": "H14b", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "The CUSUM's fire count is non-increasing in the budget divisor r.",
     "original": "SUPPORTED (20/20 monotone).", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H14b I2 fire count non-increasing in r \| SUPPORTED \(20/20 monotone\)")]},
    {"id": "H14c", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "The wall-clock accumulator under a 1-in-r budget equals itself at r·dt.",
     "original": "SUPPORTED: 0 mismatches in 19,360 cells.", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H14c I1 under budget ≡ I1 at r·dt \| SUPPORTED — \*\*0 mismatches / 19,360 cells\*\*")]},
    {"id": "H14d", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "At least 11 of 20 trajectories leave the alarm regime by r = 10.",
     "original": "SUPPORTED (19/20).", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H14d ≥11/20 leave alarm regime by r=10 \| SUPPORTED — \*\*19/20\*\*")]},
    {"id": "H14e", "prereg": "Phase 9", "kind": "confirmatory",
     "claim": "The edge trigger's net fires stay at or below 3 everywhere.",
     "original": "SUPPORTED (maximum 1).", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H14e T3 net ≤ 3 everywhere \| SUPPORTED — max \*\*1\*\*")]},
    {"id": "H15", "prereg": "Phase 9 addendum C", "kind": "confirmatory",
     "claim": "Frontier agents take fewer actions than the gpt-5.4-mini loop (pilot).",
     "original": "FALSIFIED (Opus median 14 vs 9).", "corrected": None,
     "evidence": [("PAPER3_DATAPACK.md", r"H15 action count \| fewer actions than gpt-5\.4-mini \| \*\*FALSIFIED\*\* \(Opus median 14 vs 9\)")]},
    {"id": "9C-§3", "prereg": "Phase 9C", "kind": "descriptive",
     "claim": "Action counts increase under the clean protocol relative to the pilot (direction stated in advance).",
     "original": "Failed: Opus median 14.0 → 9.5 (decrease), Fable 7.0 → 7.0 (unchanged). Uninformative: the replication also changed the task specifications.",
     "corrected": None,
     "evidence": [("PHASE_C2_REPORT.md", r"\| opus \| [^|]+\| \*\*9\.5\*\* \| 14\.0 \| decrease \|"),
                  ("PHASE_C2_REPORT.md", r"\| fable \| [^|]+\| \*\*7\.0\*\* \| 7\.0 \| unchanged \|"),
                  ("PHASE_C2_REPORT.md", r"reported as a failed prediction and as uninformative")]},
    {"id": "H16", "prereg": "Phase 9C", "kind": "confirmatory",
     "claim": "Fable 5.1's median inter-action interval is below Opus 5's, per task specification.",
     "original": "INCONCLUSIVE: 4/8 in direction, exact Wilcoxon p = 0.8438, median difference −0.010 s.",
     "corrected": "INCONCLUSIVE: 5/8, p = 0.3828, median difference +0.802 s.",
     "evidence": [("RECONCILIATION_9C.md", r"\*\*H16\*\*[^\n]*4/8 in direction, p = 0\.8438, median diff -0\.010 s \| \*\*5/8, p = 0\.3828, median diff \+0\.802 s\*\* \| INCONCLUSIVE → INCONCLUSIVE")]},
    {"id": "H17a", "prereg": "Phase 9C", "kind": "confirmatory",
     "claim": "Fable 5.1 issues more Read calls per run than Opus 5.",
     "original": "INCONCLUSIVE: exact p = 1.0000.", "corrected": "INCONCLUSIVE: p = 1.0000 (unchanged).",
     "evidence": [("RECONCILIATION_9C.md", r"\*\*H17a\*\*[^\n]*p = 1\.0000 \| p = 1\.0000 \| INCONCLUSIVE → INCONCLUSIVE")]},
    {"id": "H17b", "prereg": "Phase 9C", "kind": "confirmatory",
     "claim": "Read-call count predicts peak modelled frustration, controlling for action count.",
     "original": "FALSIFIED under its clause: partial ρ = 0.470, p = 0.0795. Canonical label: did not replicate (W1).",
     "corrected": "Unchanged: partial ρ = 0.471, p = 0.0812.",
     "evidence": [("RECONCILIATION_9C.md", r"\*\*H17b\*\*[^\n]*partial 0\.470, p = 0\.0795 \| partial 0\.471, p = 0\.0812 \| FALSIFIED under clause")]},
    {"id": "H18", "prereg": "Phase 9C", "kind": "confirmatory",
     "claim": "No more than 20% of runs per arm reach the clamp.",
     "original": "SUPPORTED via the zero-clamp branch (0/8, 0/8); the clamp claim is withdrawn (W2).",
     "corrected": "Unchanged (0/8, 0/8).",
     "evidence": [("RECONCILIATION_9C.md", r"\*\*H18\*\*[^\n]*Opus 0/8, Fable 0/8 \| Opus 0/8, Fable 0/8 \| SUPPORTED \(zero-clamp branch\)")]},
    {"id": "H19", "prereg": "Phase 9D", "kind": "confirmatory",
     "claim": "Held-out model (Opus 5.5): at most 2 of 8 sessions carry 5 or more qualifying observations.",
     "original": "SUPPORTED, 0/8 (hook count).", "corrected": "SUPPORTED, 0/8 (transcript count, which governs).",
     "evidence": [("PHASE_9D_REPORT.md", r"\*\*H19\*\*[^\n]*0/8 → SUPPORTED \| \*\*0/8 → SUPPORTED\*\*")]},
    {"id": "H20", "prereg": "Phase 9D", "kind": "confirmatory",
     "claim": "Held-out model: the CUSUM fires on more sessions than the no-decay accumulator at full budget.",
     "original": "SUPPORTED, 1 vs 0 (hook count).",
     "corrected": "SUPPORTED, 1 vs 0 (transcript count). Carries no information: the narrowest margin the clause allows. Not cited.",
     "evidence": [("PHASE_9D_REPORT.md", r"\*\*H20\*\*[^\n]*I2 1 vs I1 0 → SUPPORTED \| \*\*I2 1 vs I1 0 → SUPPORTED\*\*"),
                  ("PHASE_9D_REPORT.md", r"carries no information")]},
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def prereg_commits(fname: str) -> dict:
    log = git("log", "--format=%h|%ad|%s", "--date=short", "--follow", "--",
              f"data/swebench_pilot/{fname}").splitlines()
    rows = [dict(zip(("commit", "date", "subject"), l.split("|", 2))) for l in reversed(log)]
    return {"file": fname, "registered": rows[0], "later": rows[1:]}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    texts = {}
    missing = []
    for h in H:
        for f, rx in h["evidence"]:
            t = texts.setdefault(f, (PILOT / f).read_text(encoding="utf-8"))
            if not re.search(rx, t):
                missing.append(f"{h['id']}: no match in {f} for /{rx}/")
    if missing:
        print("scorecard disagrees with its sources:\n  " + "\n  ".join(missing))
        return 1
    regs = {k: prereg_commits(v) for k, v in PREREGS.items()}
    sha = git("rev-parse", "HEAD")[:12]

    O = [f"# Hypothesis scorecard — Paper 3",
         "",
         f"Generated by `scripts/hypothesis_scorecard.py` at `{sha}`. Every score is "
         f"checked against the artefact that produced it; the script fails if one has "
         f"moved. Paper 2's hypotheses (H1–H9) are scored in Paper 2.",
         "",
         "**Kinds.** *Confirmatory*: scored by its pre-registered clause. *Retired*: "
         "withdrawn before any data could score it; unscored, and retiring it is not a "
         "claim about its answer. *Descriptive*: a direction stated in advance and "
         "reported, not tested.",
         "",
         "## Pre-registrations",
         "",
         "| pre-registration | file | registered | later commits |",
         "|---|---|---|---|"]
    for k, r in regs.items():
        later = "; ".join(f"`{x['commit']}` {x['date']} {x['subject']}" for x in r["later"]) or "—"
        O.append(f"| {k} | `{r['file']}` | `{r['registered']['commit']}` {r['registered']['date']} | {later} |")
    O += ["", "## Scorecard", "",
          "| id | pre-registration | kind | prediction | as originally scored | corrected | source |",
          "|---|---|---|---|---|---|---|"]
    for h in H:
        src = ", ".join(sorted({f for f, _ in h["evidence"]}))
        O.append(f"| {h['id']} | {h['prereg']} (`{regs[h['prereg']]['registered']['commit']}`) | "
                 f"{h['kind']} | {h['claim']} | {h['original']} | {h['corrected'] or 'no correction'} | {src} |")
    O.append("")
    OUT_MD.write_text("\n".join(O), encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"preregistrations": regs, "hypotheses": [
        {k: v for k, v in h.items() if k != "evidence"} | {"sources": sorted({f for f, _ in h["evidence"]})}
        for h in H]}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(H)} entries checked against their sources; wrote {OUT_MD.name} and {OUT_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
