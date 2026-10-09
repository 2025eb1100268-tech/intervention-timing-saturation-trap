"""Does the PostToolUse hook see every tool call? Audit against transcripts.

DISCOVERED during the Phase 9D Opus 5.5 run (S02): the subagent transcript
recorded three PowerShell calls; the hook captured two. The one missing was the
only one with `is_error = True` -- the first pytest run, exit code 1. Claude
Code fires PostToolUse after a tool call SUCCEEDS; a failed call does not
trigger it. `hook_logger.py`'s own docstring assumes the opposite ("invokes this
script after every tool call").

Why this matters more than an ordinary coverage gap: the paper's primary
evidence definition is execution-only -- *a shell command that returned an
error*. That is exactly the class of event a PostToolUse hook cannot see. The
hook can only count failures whose output contains error text while the tool
still reported success, which depends on incidental formatting habits (for
example piping pytest through `Select-Object` makes the pipeline succeed).

Every Phase-9C subagent transcript survives and maps one-to-one onto its
measurement window, so the true counts are recoverable. This recomputes them
with the hook's OWN detector (`_detect_error`), applied to every call in the
transcript instead of only the calls the hook was shown. Nothing else changes.

Run from repo root:  python scripts/hook_coverage_audit.py
"""
from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from heart_instrument.hook_logger import _detect_error  # noqa: E402

C2 = ROOT / "data" / "live_runs" / "phase_c2"
SUB = Path.home() / ".claude" / "projects" / "<project>" / \
    "77c15df0-2f1d-47c6-9f77-ef81b52d8c8b" / "subagents"
OUT = ROOT / "data" / "swebench_pilot" / "HOOK_COVERAGE_AUDIT.md"
SHELL = {"Bash", "PowerShell"}
N_MIN = 5
K, H = 0.10, 1.0
STEP, THRESH = 0.15, 0.7


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def transcript_calls(path: Path):
    """Every tool call in a subagent transcript, in order, with its result."""
    uses, results, models = [], {}, set()
    for line in path.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        msg = r.get("message") or {}
        if msg.get("role") == "assistant" and msg.get("model"):
            models.add(msg["model"])
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                uses.append((c["id"], c["name"], r.get("timestamp")))
            elif c.get("type") == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = " ".join(b.get("text", "") for b in body if isinstance(b, dict))
                results[c["tool_use_id"]] = (bool(c.get("is_error")), str(body or ""))
    calls = []
    for uid, name, ts in uses:
        is_err, text = results.get(uid, (False, ""))
        # The hook's own detector, fed what the transcript recorded.
        err = _detect_error({"is_error": is_err, "content": text})
        calls.append({"name": name, "is_error": is_err, "err": err, "ts": ts})
    return calls, models


def fires_i1_nodecay(e: List[int]) -> bool:
    s = 0.0
    for x in e:
        s = min(1.0, s + STEP * x)
        if s >= THRESH:
            return True
    return False


def fires_i2(e: List[int]) -> bool:
    g = 0.0
    for x in e:
        g = max(0.0, g + x - K)
        if g >= H:
            return True
    return False


def main() -> int:
    mapping: Dict[str, str] = json.loads((C2 / "_9c_transcript_map.json").read_text())
    extra = C2 / "_9d_transcript_map.json"
    if extra.exists():
        mapping.update(json.loads(extra.read_text()))

    rows = []
    for key, tname in sorted(mapping.items()):
        spec, model = key.split("_", 1)
        run_p = C2 / f"{spec}_{model}_r1.json"
        sess_p = C2 / spec / f"session_{model}_r1.jsonl"
        if not (run_p.exists() and sess_p.exists() and (SUB / tname).exists()):
            continue
        calls, models = transcript_calls(SUB / tname)
        hook = [json.loads(l) for l in sess_p.read_text(encoding="utf-8").splitlines() if l.strip()]
        hook_shell_err = sum(1 for r in hook if r["tool_name"] in SHELL and r["error_indicator"])
        t_shell = [c for c in calls if c["name"] in SHELL]
        e_t = [1 if (c["name"] in SHELL and c["err"]) else 0 for c in calls]
        rows.append({
            "run": key, "spec": spec, "model": model, "models": sorted(models),
            "n_transcript": len(calls), "n_hook": len(hook),
            "missing": len(calls) - len(hook),
            "missing_errored": sum(1 for c in calls if c["is_error"]),
            "shell_calls": len(t_shell),
            "shell_errored_flag": sum(1 for c in t_shell if c["is_error"]),
            "E_X_hook": hook_shell_err,
            "E_X_true": sum(e_t),
            "i1_true": fires_i1_nodecay(e_t),
            "i2_true": fires_i2(e_t),
        })

    c9 = [r for r in rows if r["model"] in ("opus", "fable")]
    d9 = [r for r in rows if r["model"] == "opus55"]

    O: List[str] = []
    w = O.append
    w("# Hook coverage audit — the instrument cannot see failed tool calls")
    w("")
    w(f"Generated by `scripts/hook_coverage_audit.py` at `{sha()}`.")
    w("")
    w("## The defect")
    w("")
    w("Claude Code fires `PostToolUse` after a tool call **succeeds**. A call "
      "that fails — including a shell command that exits non-zero — does not "
      "trigger it. The paper's primary evidence definition is execution-only: "
      "*a shell command that returned an error*. That is precisely the event a "
      "`PostToolUse` hook cannot observe. It can only count failures whose "
      "output contains error text while the tool still reported success, which "
      "depends on incidental formatting habits.")
    w("")
    w("Found by reconciling a Phase-9D run against its transcript: three "
      "PowerShell calls recorded, two captured, and the missing one was the "
      "only call with `is_error = True`.")
    w("")
    if c9:
        tot_missing = sum(r["missing"] for r in c9)
        tot_miss_err = sum(r["missing_errored"] for r in c9)
        w("## Phase 9C — the frozen 16 sessions, recounted")
        w("")
        w(f"- Tool calls in transcripts: **{sum(r['n_transcript'] for r in c9)}**; "
          f"captured by the hook: **{sum(r['n_hook'] for r in c9)}**; "
          f"missing: **{tot_missing}**, of which **{tot_miss_err}** were calls "
          f"the transcript marks `is_error = True`.")
        all_err = tot_missing == tot_miss_err
        w(f"- {'**Every missing call is a failed call.**' if all_err else 'Not every missing call is a failed call — see per-session rows.'}")
        fe_h = sum(1 for r in c9 if r["E_X_hook"] >= N_MIN)
        fe_t = sum(1 for r in c9 if r["E_X_true"] >= N_MIN)
        i2_h = None
        w(f"- **Feasible at N_min = 5 (E_X ≥ 5): {fe_h}/16 as published "
          f"(hook) → {fe_t}/16 recounted (transcript).**")
        w(f"- Median E_X: {statistics.median(r['E_X_hook'] for r in c9):.1f} "
          f"(hook) → {statistics.median(r['E_X_true'] for r in c9):.1f} "
          f"(transcript).")
        w(f"- CUSUM (N_min = 2) fires at full budget on "
          f"{sum(1 for r in c9 if r['i2_true'])}/16 recounted sessions; "
          f"5-event accumulator (no decay) on "
          f"{sum(1 for r in c9 if r['i1_true'])}/16.")
        w("")
        w("| run | model in transcript | calls (transcript / hook) | missing (all errored?) | E_X hook | **E_X true** |")
        w("|---|---|---|---|---|---|")
        for r in c9:
            w(f"| {r['run']} | {', '.join(r['models'])} | {r['n_transcript']} / {r['n_hook']} | "
              f"{r['missing']} ({'yes' if r['missing'] == r['missing_errored'] else 'NO'}) | "
              f"{r['E_X_hook']} | **{r['E_X_true']}** |")
        w("")
    if d9:
        w("## Phase 9D — Opus 5.5 runs completed so far")
        w("")
        w("| run | model in transcript | calls (transcript / hook) | missing (all errored?) | E_X hook | **E_X true** |")
        w("|---|---|---|---|---|---|")
        for r in d9:
            w(f"| {r['run']} | {', '.join(r['models'])} | {r['n_transcript']} / {r['n_hook']} | "
              f"{r['missing']} ({'yes' if r['missing'] == r['missing_errored'] else 'NO'}) | "
              f"{r['E_X_hook']} | **{r['E_X_true']}** |")
        w("")

    OUT.write_text("\n".join(O), encoding="utf-8")
    (C2 / "_hook_coverage.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for r in rows:
        print(f"{r['run']:12s} {','.join(r['models']):22s} calls {r['n_transcript']:3d}/{r['n_hook']:3d} "
              f"missing {r['missing']:2d} (errored {r['missing_errored']:2d})  "
              f"E_X hook {r['E_X_hook']} -> true {r['E_X_true']}")
    if c9:
        print(f"\n9C feasible (E_X>=5): hook {sum(1 for r in c9 if r['E_X_hook']>=5)}/16 "
              f"-> true {sum(1 for r in c9 if r['E_X_true']>=5)}/16")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
