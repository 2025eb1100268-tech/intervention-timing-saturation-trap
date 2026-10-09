"""Before the transcripts become the canonical 9C source: are their timestamps
at the same point in the action cycle as the hook's?

The hook's `ts` is taken when the PostToolUse script runs -- after the tool has
produced its observation, which is the cycle point Paper 2's loop used. A
subagent transcript writes one line when the model emits a tool call and
another when the tool result is appended. If the RESULT line tracks the hook
closely on every call both instruments logged, the transcript can stand in for
the hook on the calls it missed, at the same cycle point. If it does not, the
transcript cannot be the timing source and this script says so.

Matching is by order and exact tool input: the hook's records are a
subsequence of the transcript's calls (the missing ones are the failures).

Run from repo root:  python scripts/transcript_timestamp_check.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
C2 = ROOT / "data" / "live_runs" / "phase_c2"
SUB = Path.home() / ".claude" / "projects" / "<project>" / \
    "77c15df0-2f1d-47c6-9f77-ef81b52d8c8b" / "subagents"
OUT = ROOT / "data" / "swebench_pilot" / "TRANSCRIPT_TIMESTAMP_CHECK.md"
TRUNC = 2048


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def transcript_calls(path: Path) -> List[Dict]:
    """Each tool call: name, input (hook-serialised), and the timestamps of the
    line that issued it and the line that carried its result."""
    issued, results = [], {}
    for line in path.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("timestamp")
        for c in (r.get("message") or {}).get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                issued.append({"id": c["id"], "name": c["name"],
                               "input": json.dumps(c.get("input"), default=str)[:TRUNC],
                               "t_issue": parse_ts(ts) if ts else None})
            elif c.get("type") == "tool_result":
                results[c["tool_use_id"]] = {"t_result": parse_ts(ts) if ts else None,
                                             "is_error": bool(c.get("is_error"))}
    for c in issued:
        c.update(results.get(c["id"], {"t_result": None, "is_error": None}))
    return issued


# The two instruments serialise inputs differently (the transcript carries
# defaults such as Edit's replace_all that the hook payload omits, and the hook
# truncates at 2048 chars), so match on each tool's identifying fields, read
# order-independently and tolerant of truncation.
KEYS = {"Bash": ["command"], "PowerShell": ["command"],
        "Read": ["file_path", "offset", "limit"], "Write": ["file_path"],
        "Edit": ["file_path", "old_string"], "Grep": ["pattern", "path", "glob"],
        "Glob": ["pattern", "path"], "TaskStop": ["task_id", "shell_id"],
        "ToolSearch": ["query"], "TaskOutput": ["task_id"]}


def field(s: str, k: str):
    m = re.search(r'"%s": (?:"((?:[^"\\]|\\.){0,120})|(-?\d+|true|false|null))' % re.escape(k), s)
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def sig(name: str, s: str):
    ks = KEYS.get(name)
    if ks is None:
        return (name, s[:120])
    return (name,) + tuple(field(s, k) for k in ks)


def match(calls: List[Dict], hook: List[Dict]):
    """In-order match of hook records onto transcript calls by identifying
    fields. Returns the pairs, or None if a hook record has no counterpart."""
    pairs, j = [], 0
    for h in hook:
        target = sig(h["tool_name"], h["tool_input"])
        while j < len(calls) and sig(calls[j]["name"], calls[j]["input"]) != target:
            j += 1
        if j == len(calls):
            return None
        pairs.append((calls[j], h))
        j += 1
    return pairs


def main() -> int:
    maps = {}
    for f in ("_9c_transcript_map.json", "_9d_transcript_map.json"):
        p = C2 / f
        if p.exists():
            maps.update(json.loads(p.read_text()))
    rows, d_result, d_issue = [], [], []
    for key, tname in sorted(maps.items()):
        spec, model = key.split("_", 1)
        sess = C2 / spec / f"session_{model}_r1.jsonl"
        hook = [json.loads(l) for l in sess.read_text(encoding="utf-8").splitlines() if l.strip()]
        calls = transcript_calls(SUB / tname)
        pairs = match(calls, hook)
        if pairs is None:
            rows.append((key, len(calls), len(hook), None, None, None, "UNMATCHED"))
            continue
        dr = [(datetime.fromisoformat(h["ts"]) - c["t_result"]).total_seconds()
              for c, h in pairs if c["t_result"]]
        di = [(datetime.fromisoformat(h["ts"]) - c["t_issue"]).total_seconds()
              for c, h in pairs if c["t_issue"]]
        d_result += dr
        d_issue += di
        unmatched_ok = all(c["is_error"] for c in calls
                           if c["id"] not in {pc["id"] for pc, _ in pairs})
        rows.append((key, len(calls), len(pairs), statistics.median(dr),
                     max(abs(x) for x in dr), statistics.median(di),
                     "ok" if unmatched_ok else "UNMATCHED CALL NOT AN ERROR"))

    O: List[str] = []
    w = O.append
    w("# Transcript timestamps against hook timestamps")
    w("")
    w(f"{len(d_result)} calls logged by both instruments, across {len(rows)} runs "
      f"(16 Phase-9C, 8 Phase-9D).")
    w("")
    w("| offset (hook ts minus transcript ts) | median | min | max | max abs |")
    w("|---|---|---|---|---|")
    for label, d in (("vs the line carrying the RESULT", d_result),
                     ("vs the line ISSUING the call", d_issue)):
        w(f"| {label} | {statistics.median(d):+.3f} s | {min(d):+.3f} s | "
          f"{max(d):+.3f} s | {max(abs(x) for x in d):.3f} s |")
    w("")
    w("| run | transcript calls | matched | median offset (result) | max abs offset (result) | median offset (issue) | unmatched calls |")
    w("|---|---|---|---|---|---|---|")
    for key, n, m, med, mx, medi, note in rows:
        if med is None:
            w(f"| {key} | {n} | — | — | — | — | **{note}** |")
        else:
            w(f"| {key} | {n} | {m} | {med:+.3f} s | {mx:.3f} s | {medi:+.3f} s | {note} |")
    w("")
    OUT.write_text("\n".join(O), encoding="utf-8")
    json.dump({"offset_result": d_result, "offset_issue": d_issue},
              open(C2 / "_ts_check.json", "w"), indent=1)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(f"matched calls: {len(d_result)}")
    print(f"hook - transcript RESULT line: median {statistics.median(d_result):+.3f}s "
          f"min {min(d_result):+.3f} max {max(d_result):+.3f}")
    print(f"hook - transcript ISSUE  line: median {statistics.median(d_issue):+.3f}s "
          f"min {min(d_issue):+.3f} max {max(d_issue):+.3f}")
    bad = [r for r in rows if r[-1] != "ok"]
    print(f"runs with problems: {len(bad)} {[r[0] for r in bad]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
