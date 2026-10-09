"""The map: fourteen published agent/control monitors on five columns.

Four were audited earlier, with reimplementation (EXTERNAL_MONITOR_CHECKS.md).
Ten more were classified by reading alone, each by one agent and then
re-derived by an adversarial verifier that re-fetched every quoted passage
(external_monitors/census_fanout.json; all ten survived, all quotes
confirmed). Nine further candidates were discovered but not classified,
because the fan-out was capped at ten; they are named below, not hidden.

Columns: forgetting basis, can-the-statistic-fall, evidence floor (N_min) at
the stated episode length, harm model, evidence source. The last two exist
because which logging blind spot matters depends on WHERE a monitor's evidence
comes from, not on what harm it targets.

Run from repo root:  python scripts/control_monitor_census.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "swebench_pilot" / "external_monitors"
OUT = ROOT / "data" / "swebench_pilot" / "CONTROL_MONITOR_CENSUS.md"

# The four audited earlier, with values established in EXTERNAL_MONITOR_CHECKS.md.
AUDITED = [
    {"name": "Ctrl-Z three strikes", "paper": "Bhatt et al. 2025, arXiv:2504.10374",
     "forgetting_basis": "count", "can_fall": "never",
     "can_fall_note": "basic rule never; the Time Travel variant revises past evidence by resampling",
     "n_min": "3 (stated, tuned)", "episode_length": "≤ 15 steps, reset per task",
     "harm_model": "agent_sabotage", "evidence_source": "action_content", "how": "audited"},
    {"name": "Hills et al. k-strikes arm", "paper": "Hills et al. 2026, arXiv:2607.02514 (App. J)",
     "forgetting_basis": "count", "can_fall": "never", "can_fall_note": "",
     "n_min": "3 (k stated)", "episode_length": "5 PRs (task sequences; not restated for App. J)",
     "harm_model": "agent_sabotage", "evidence_source": "action_content", "how": "audited"},
    {"name": "Hills et al. link-tracker", "paper": "Hills et al. 2026, arXiv:2607.02514",
     "forgetting_basis": "count", "can_fall": "never",
     "can_fall_note": "the run maximum never falls; its text notes can drop concerns",
     "n_min": "1 (max over PRs > 6)", "episode_length": "5 PRs",
     "harm_model": "agent_sabotage", "evidence_source": "action_content", "how": "audited"},
    {"name": "Brown et al. cluster gate", "paper": "Brown et al. 2026, arXiv:2605.31593",
     "forgetting_basis": "count", "can_fall": "never",
     "can_fall_note": "no expiry published; latches once met",
     "n_min": "max(⌊Θ⌋+1, m+1) — no integer (Θ, m unpublished)",
     "episode_length": "not stated; buffers pooled across users",
     "harm_model": "external_misuse", "evidence_source": "action_content", "how": "audited"},
]

# Compact cells for the paper's Table 2, audited rows. Read rows take theirs from
# the verifier's `table_row` in census_fanout.json.
AUDITED_CELLS = {
    "Ctrl-Z three strikes": ("count (reset per task)", "never (Time Travel resampling can revise a step)",
                             "3 (stated, tuned)", "≤ 15 steps"),
    "Hills et al. k-strikes arm": ("count (reset per run)", "never", "3 (k stated)",
                                  "5 PRs (task sequences)"),
    "Hills et al. link-tracker": ("count (reset per run)", "never (run maximum)", "1 (max over PRs > 6)",
                                 "5 PRs"),
    "Brown et al. cluster gate": ("count (no expiry; buffers pooled across users)", "never (latches)",
                                 "max(⌊Θ⌋+1, m+1); Θ, m unpublished", "not stated"),
}

# Can the monitor alarm on ONE qualifying observation by some stated path?
# Audited rows: EXTERNAL_MONITOR_CHECKS.md, "N=1 escape path". Read rows: our
# classification of the verifier's `single_step_escape` text, quoted in full in
# census_fanout.json. "rule" = the stateful rule itself fires on one;
# "beside" = a separate single-step path; "none" = no N=1 path is stated.
N1_PATH = {
    "Ctrl-Z three strikes": "beside (single-step threshold)",
    "Hills et al. k-strikes arm": "beside (current-PR arm)",
    "Hills et al. link-tracker": "rule",
    "Brown et al. cluster gate": "beside (per-request threshold)",
    "Adaptive macro-protocol": "beside (per-task harm estimate on s_t)",
    "Sequential, hierarchical": "rule (one chunk)",
    "SHADE-Arena turn-by-turn": "rule",
    "Asynchronous episode monitor": "rule (one episode)",
    "BashArena per-action": "rule",
    "LinuxArena live per-action": "rule",
    "AI-Control Game memoryless": "rule",
    "Human decision sabotage": "none stated (floor 1 or 2)",
    "Lightweight sequential monitor": "none",
    "THRD Decision Module": "beside (R_i > 3.5 at any turn)",
}


def n1_path(name: str) -> str:
    hits = [v for k, v in N1_PATH.items() if name.startswith(k)]
    if len(hits) != 1:
        raise SystemExit(f"N1_PATH: {len(hits)} entries match {name!r}")
    return hits[0]


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def short(s: str, n: int = 70) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    fan = json.loads((EXT / "census_fanout.json").read_text(encoding="utf-8"))
    read = []
    for v in fan["rows"]:
        if not v.get("survives"):
            continue
        cells = [c.strip() for c in v["table_row"].split(" | ")]
        if len(cells) == 6 and ": " in cells[0]:      # "name: forgetting" in one cell
            cells = cells[0].split(": ", 1) + cells[1:]
        elif len(cells) == 6:                         # episode cell omitted
            cells.insert(4, short(v["episode_length"], 60))
        if len(cells) != 7:
            raise SystemExit(f"table_row for {v['name']!r} has {len(cells)} cells, expected 7")
        read.append({"name": v["name"], "paper": v.get("paper") or v.get("url", ""),
                     "forgetting_basis": v["forgetting_basis"], "can_fall": v["can_fall"],
                     "can_fall_note": "", "n_min": v["n_min"],
                     "episode_length": v["episode_length"], "harm_model": v["harm_model"],
                     "evidence_source": v["evidence_source"], "how": "read",
                     "quotes_confirmed": v.get("quotes_confirmed"),
                     "cells": (cells[0], cells[1], cells[2], cells[3], cells[4])})
    for m in AUDITED:
        m["cells"] = (m["name"],) + AUDITED_CELLS[m["name"]]
    allm = AUDITED + read
    n = len(allm)
    for m in allm:
        m["n1"] = n1_path(m["name"])

    def floor_kind(s: str) -> str:
        s = s.strip().lower()
        if s.startswith("1"):
            return "1"
        if s[:1].isdigit():
            return "count ≥ 2"
        return "undefined / symbolic"

    fb = Counter(m["forgetting_basis"] for m in allm)
    cf = Counter(m["can_fall"] for m in allm)
    fl = Counter(floor_kind(m["n_min"]) for m in allm)
    hm = Counter(m["harm_model"] for m in allm)
    ev = Counter(m["evidence_source"] for m in allm)

    O: List[str] = []
    w = O.append
    w("# The map — fourteen published agent and control monitors")
    w("")
    w(f"Generated by `scripts/control_monitor_census.py` at `{sha()}`. Four "
      f"monitors were audited with reimplementation (`EXTERNAL_MONITOR_CHECKS.md`); "
      f"{len(read)} were classified by reading alone, each re-derived by an "
      f"adversarial verifier that re-fetched every quoted passage "
      f"(`external_monitors/census_fanout.json`; {sum(1 for r in read if r['quotes_confirmed'])}"
      f"/{len(read)} quotes confirmed). Values only from published text, code or "
      f"configuration; what a paper does not state is recorded as not stated.")
    w("")
    w("## What the map shows")
    w("")
    w(f"- **Forgetting basis: none of the {n} forgets on the clock.** "
      f"{fb.get('count', 0)} forget per observation or reset per episode; "
      f"{fb.get('none', 0)} carry no accumulated suspicion at all. Set beside "
      f"`DEPLOYED_MONITOR_CENSUS.md` — where clock-indexed windows are the norm "
      f"for agent rate control and appear in shipped misuse detectors — this is a "
      f"**research-to-production gap on the first axis**: the published protocols "
      f"count, the deployed infrastructure times.")
    w(f"- **Can the statistic fall: the field splits.** {cf.get('evidence', 0)} have an "
      f"evidence channel that lowers it (Bayesian updates, significance tests on a "
      f"running mean, re-scoring of cumulative behaviour); "
      f"{cf.get('decay_or_reset_only', 0)} fall only by reset at the episode boundary; "
      f"{cf.get('never', 0)} never fall within their scope; {cf.get('n/a', 0)} have no "
      f"statistic to fall. The inability to exonerate is a design choice that most "
      f"research protocols do not make.")
    w(f"- **Evidence floor: the dominant design has none.** {fl.get('1', 0)} of {n} "
      f"fire on a single observation — mostly a maximum over per-step scores. "
      f"{fl.get('count ≥ 2', 0)} have an integer count floor of two or more, and "
      f"{fl.get('undefined / symbolic', 0)} define their decision so that no integer "
      f"follows from the published parameters. **The floor is a property of a "
      f"minority design**: count-based aggregation. Where it exists it binds — "
      f"Hills et al. report it binding in their own results.")
    multi = [m for m in allm if floor_kind(m["n_min"]) == "count ≥ 2"]
    multi_beside = [m for m in multi if m["n1"].startswith("beside")]
    strict = [m for m in multi if m["n1"] == "none"]
    w(f"- **A floor on the stateful path is not a floor on the monitor.** Of the "
      f"{len(multi)} with an integer floor of two or more, {len(multi_beside)} "
      f"({', '.join(m['name'] for m in multi_beside)}) sit beside a single-step path "
      f"that alarms on one observation; the floor binds only the multi-step path. "
      f"{len(strict)} ({', '.join(m['name'] for m in strict)}) "
      f"{'states' if len(strict) == 1 else 'state'} no single-step "
      f"path at all. Do not write that these monitors \"require more than one "
      f"observation to alarm\": by that test only the last is shown to.")
    w(f"- **Harm model: {hm.get('agent_sabotage', 0)} target agent sabotage, "
      f"{hm.get('external_misuse', 0)} external misuse, "
      f"{hm.get('agent_malfunction', 0)} agent malfunction.** No published monitor in "
      f"this set targets a struggling or stuck agent. Our own distress-based "
      f"instrument is alone in that column.")
    w(f"- **Evidence source: {ev.get('action_content', 0)} of {n} judge what an action "
      f"says or does; {ev.get('mixed', 0)} mix in other signals; "
      f"{ev.get('outcome_failure', 0)} draw their evidence from failures.** This is "
      f"the precise form of the logging asymmetry. A feed that sees only successful "
      f"actions blinds evidence drawn from failures, whatever the harm model. In the "
      f"research literature no monitor draws on failures, so none is blinded. In "
      f"production, the Elastic misuse rule counts guardrail `BLOCKED` events — "
      f"failure evidence — so a success-only feed would blind a *misuse* detector. "
      f"The blind spot follows the evidence source, not the harm model.")
    w("")
    w("## The table")
    w("")
    w("| monitor | paper | forgets on | can fall | N_min | episode | harm model | evidence | how |")
    w("|---|---|---|---|---|---|---|---|---|")
    for m in allm:
        fall = m["can_fall"] + (f" ({m['can_fall_note']})" if m.get("can_fall_note") else "")
        w(f"| {short(m['name'], 60)} | {short(m['paper'], 48)} | {m['forgetting_basis']} | "
          f"{short(fall, 60)} | {short(m['n_min'], 46)} | {short(m['episode_length'], 40)} | "
          f"{m['harm_model']} | {m['evidence_source']} | {m['how']} |")
    w("")
    w("## Table 2 — paper form")
    w("")
    w("Untruncated compact cells: the verifier's `table_row` for the ten read rows, "
      "`AUDITED_CELLS` for the four audited. *N = 1 path* says whether some stated "
      "path alarms on a single qualifying observation (`rule`: the stateful rule "
      "itself; `beside`: a separate single-step path; `none`: no such path stated). "
      "Full text, quotations and sources: `external_monitors/census_fanout.json` "
      "and `EXTERNAL_MONITOR_CHECKS.md`.")
    w("")
    w("| monitor | forgets on | can fall | N_min (stateful path) | N = 1 path | "
      "episode length | harm | how |")
    w("|---|---|---|---|---|---|---|---|")
    for m in allm:
        name, forget, fall, nmin, ep = m["cells"]
        w(f"| {name} | {forget} | {fall} | {nmin} | {m['n1']} | {ep} | "
          f"{m['harm_model'].replace('_', ' ')} | {m['how']} |")
    w("")
    w("## Not classified — the fan-out was capped at ten")
    w("")
    w("Discovered, deduplicated, and left out only because of the cap. Some would "
      "change the map's corners — a streaming classifier that takes a cumulative "
      "maximum over tokens, an e-process sequential test with an evidence channel "
      "— and they are the obvious next rows.")
    w("")
    for name in fan.get("dropped", []):
        w(f"- {name}")
    w("")
    w("## Limits")
    w("")
    w("- **Reading, not running.** The ten read-only rows classify each paper's "
      "stated rule. None was reimplemented or executed.")
    w("- **Selection.** Discovery searched for monitors that carry state, and "
      "ranked stateful ones with a published aggregation rule first, so the map "
      "over-represents stateful designs relative to the literature as a whole.")
    w("- **Columns are coarse by design.** `count` covers a per-step drift, a "
      "per-episode reset and a per-task Bayesian update alike; the `n_min` column "
      "carries the detail.")
    w("")
    OUT.write_text("\n".join(O), encoding="utf-8")
    # Machine-readable copy for the paper's Table 2 and Appendix B. Verifier text
    # is carried whole: the supporting quotations sit inside it.
    raw = {v["name"]: v for v in fan["rows"]}

    def arxiv_id(s: str):
        m = re.search(r"\d{4}\.\d{4,5}", s or "")
        return m.group(0) if m else None
    by_id = {arxiv_id(d.get("arxiv_or_url")): d for d in fan.get("discovered", [])}
    discovered = {name: by_id.get(arxiv_id(v.get("url"))) for name, v in raw.items()}
    (EXT / "table2.json").write_text(json.dumps({"rows": [{
        "name": m["name"], "paper": m["paper"], "how": m["how"],
        "cells": dict(zip(("monitor", "forgets_on", "can_fall", "n_min", "episode"), m["cells"])),
        "n1_path": m["n1"], "harm_model": m["harm_model"],
        "evidence_source": m["evidence_source"], "floor_kind": floor_kind(m["n_min"]),
        "verifier": ({k: raw[m["name"]].get(k) for k in
                      ("n_min", "episode_length", "single_step_escape", "corrections", "url")}
                     if m["how"] == "read" else None),
        "discovery_note": (discovered.get(m["name"]) or {}).get("why"),
    } for m in allm]}, indent=1, ensure_ascii=False), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"{n} monitors | forgetting {dict(fb)} | can fall {dict(cf)}")
    print(f"floor {dict(fl)} | harm {dict(hm)} | evidence {dict(ev)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
