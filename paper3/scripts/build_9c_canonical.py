"""Build the canonical Phase-9C (and 9D) dataset from the subagent transcripts.

WHY. Claude Code fires PostToolUse only after a tool call succeeds, so the hook
that produced the published 9C data never saw a failed call
(HOOK_COVERAGE_AUDIT.md). The transcripts recorded every call. Every quantity
derived from the hook log -- evidence counts, action counts, inter-action
gaps, and the frozen-engine replay that consumes both -- inherits the gap.

WHAT THIS BUILDS. One record per call the agent made, in transcript order:

  * a call the hook ALSO logged keeps the hook's record VERBATIM -- timestamp,
    serialised input, observation payload, error flag. So every number that
    changes is attributable solely to the restored calls, never to a change of
    instrument on calls that were already measured.
  * a call the hook MISSED is restored from the transcript: same schema, the
    hook's own detector (`hook_logger._detect_error`) applied to the result,
    and the transcript's result-line timestamp shifted by that tool's measured
    offset.

TIMESTAMPS. TRANSCRIPT_TIMESTAMP_CHECK.md matched all 202 calls both
instruments logged. The transcript's RESULT line sits at the hook's cycle point
-- after the observation, as in Paper 2 -- for every tool except Edit, which is
stamped ~0.91 s later by post-edit processing. Every restored call is a shell
call, whose offset is ~10 ms, so restored timestamps carry no Edit artefact.

Nothing here changes the hook data in data/live_runs/phase_c2/, which remains
the record of what was originally scored. Output goes to
data/live_runs/phase_c2_canonical/ in the same layout and schema, so every
downstream analysis runs unchanged against it (see scripts/c2_source.py).

Run from repo root:  python scripts/build_9c_canonical.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heart_instrument.hook_logger import _detect_error            # noqa: E402
from transcript_timestamp_check import match, parse_ts, SUB       # noqa: E402
from c2_source import HOOK_DIR, CANON_DIR                         # noqa: E402

TRUNC = 2048
STEP, THRESHOLD, HALF_LIFE = 0.15, 0.7, 150.0
MIN_OBS = math.ceil(THRESHOLD / STEP)
GIT_RECON = ("git diff", "git status", "git show", "git log", "git stash", "git reflog")


def transcript_calls(path: Path) -> List[Dict]:
    """Every call with its input, result text, error flag, result timestamp
    and the model that issued it."""
    issued, results = [], {}
    for line in path.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("timestamp")
        msg = r.get("message") or {}
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                issued.append({"id": c["id"], "name": c["name"],
                               "input": json.dumps(c.get("input"), default=str)[:TRUNC],
                               "model": msg.get("model")})
            elif c.get("type") == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = " ".join(b.get("text", "") for b in body if isinstance(b, dict))
                results[c["tool_use_id"]] = {"t_result": parse_ts(ts) if ts else None,
                                             "is_error": bool(c.get("is_error")),
                                             "text": str(body or "")}
    for c in issued:
        c.update(results.get(c["id"], {"t_result": None, "is_error": None, "text": ""}))
    return issued


def pct(s: List[float], p: float) -> float:
    k = (len(s) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> int:
    maps: Dict[str, str] = {}
    for f in ("_9c_transcript_map.json", "_9d_transcript_map.json"):
        maps.update(json.loads((HOOK_DIR / f).read_text()))

    # Per-tool offset (hook ts minus transcript result ts), from every call
    # both instruments logged.
    loaded, offsets = {}, defaultdict(list)
    for key, tname in maps.items():
        spec, model = key.split("_", 1)
        hook = [json.loads(l) for l in (HOOK_DIR / spec / f"session_{model}_r1.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
        calls = transcript_calls(SUB / tname)
        pairs = match(calls, hook)
        if pairs is None:
            sys.exit(f"{key}: a hook record has no transcript counterpart -- abort")
        loaded[key] = (spec, model, tname, hook, calls, pairs)
        for c, h in pairs:
            offsets[c["name"]].append(
                (datetime.fromisoformat(h["ts"]) - c["t_result"]).total_seconds())
    off = {t: statistics.median(v) for t, v in offsets.items()}
    # Matching is on identifying fields cut to 120 chars, so two calls sharing
    # a prefix could be paired wrongly. A wrong pairing shows up as a timestamp
    # residual far from that tool's offset; abort on any.
    for key, (_, _, _, _, _, pairs) in loaded.items():
        for c, h in pairs:
            resid = (datetime.fromisoformat(h["ts"]) - c["t_result"]).total_seconds() - off[c["name"]]
            if abs(resid) > 0.5:
                sys.exit(f"{key}: {c['name']} pairing residual {resid:+.3f} s -- likely a mismatched call; abort")

    CANON_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for key, (spec, model, tname, hook, calls, pairs) in sorted(loaded.items()):
        run = json.loads((HOOK_DIR / f"{spec}_{model}_r1.json").read_text(encoding="utf-8"))
        tz = datetime.fromisoformat(hook[0]["ts"]).tzinfo if hook else None
        by_id = {c["id"]: h for c, h in pairs}
        lo = datetime.fromisoformat(run["window_open"])
        hi = datetime.fromisoformat(run["window_close"])
        sid = hook[0].get("session_id") if hook else None

        recs, restored = [], []
        for pos, c in enumerate(calls, 1):
            if c["id"] in by_id:
                rec = dict(by_id[c["id"]])
                rec["source"] = "hook"
            else:
                if not c["is_error"]:
                    sys.exit(f"{key}: transcript call {pos} missing from the hook is NOT "
                             f"an error -- the established mechanism does not explain it")
                if c["name"] not in off:
                    sys.exit(f"{key}: no measured offset for tool {c['name']}")
                payload = {"is_error": True, "content": c["text"]}
                t = (c["t_result"] + timedelta(seconds=off[c["name"]])).astimezone(tz)
                if not (lo < t <= hi):
                    sys.exit(f"{key}: restored call {pos} falls outside the window")
                rec = {"ts": t.isoformat(timespec="microseconds"),
                       "event": "PostToolUseFailure (restored from transcript)",
                       "session_id": sid, "tool_name": c["name"],
                       "tool_input": c["input"],
                       "status": "error", "error_indicator": _detect_error(payload),
                       "observation": json.dumps(payload, default=str)[:TRUNC],
                       "thought": "", "source": "transcript"}
                restored.append(pos)
            recs.append(rec)

        models = {c["model"] for c in calls if c["model"]}
        ts = [datetime.fromisoformat(r["ts"]) for r in recs]
        if any(b < a for a, b in zip(ts, ts[1:])):
            sys.exit(f"{key}: canonical timestamps are not monotone -- abort")
        dts = [(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))]
        n = len(recs)
        errs = sum(bool(r["error_indicator"]) for r in recs)
        p = errs / n if n else 0.0
        tools = {t: sum(1 for r in recs if r["tool_name"] == t)
                 for t in sorted({r["tool_name"] for r in recs})}
        gitn = sum(any(k in (r.get("tool_input") or "") for k in GIT_RECON) for r in recs)
        s = sorted(dts)
        med = statistics.median(dts) if dts else float("nan")
        x = STEP * p / THRESHOLD
        dstar = (-(HALF_LIFE / math.log(2.0)) * math.log(1.0 - x)) if x < 1.0 else None

        out = dict(run)
        out.update({
            "n_actions": n, "n_dt": len(dts), "tools_used": tools,
            "git_recon_calls": gitn, "error_rate": round(p, 4),
            "dt_seconds": [round(d, 6) for d in dts],
            "dt_stats": {k: (round(v, 3) if v is not None else None) for k, v in {
                "min": min(s) if s else None, "p25": pct(s, .25) if s else None,
                "median": med if s else None, "p75": pct(s, .75) if s else None,
                "p90": pct(s, .90) if s else None, "max": max(s) if s else None,
            }.items()},
            "derived": {
                "delta_star_s": round(dstar, 2) if dstar else None,
                "r_starv": round(n / MIN_OBS, 2) if n else 0.0,
                "r_cliff": round(dstar / med, 2) if (dstar and med and med > 0) else None,
            },
            "canonical": {
                "source": "subagent transcript; hook records kept verbatim where present",
                "transcript": tname,
                "model_id": sorted(models),
                "n_hook": len(hook), "n_restored": len(restored),
                "restored_positions": restored,
                "as_originally_scored": {
                    "n_actions": run["n_actions"], "error_rate": run["error_rate"],
                    "dt_median": run["dt_stats"]["median"],
                    "git_recon_calls": run["git_recon_calls"],
                },
            },
        })
        (CANON_DIR / f"{spec}_{model}_r1.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        (CANON_DIR / spec).mkdir(exist_ok=True)
        (CANON_DIR / spec / f"session_{model}_r1.jsonl").write_text(
            "\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        summary.append((key, sorted(models), len(hook), n, restored,
                        run["dt_stats"]["median"], out["dt_stats"]["median"]))

    (CANON_DIR / "_offsets.json").write_text(json.dumps(
        {t: {"median_s": off[t], "n": len(offsets[t])} for t in sorted(off)}, indent=1),
        encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("per-tool offset (hook - transcript result):",
          {t: round(v, 3) for t, v in sorted(off.items())})
    for key, models, nh, nc, restored, m0, m1 in summary:
        flag = f" restored {restored}" if restored else ""
        print(f"{key:12s} {','.join(models):18s} n {nh:2d} -> {nc:2d}  "
              f"median dt {m0} -> {m1}{flag}")
    print(f"wrote {len(summary)} canonical runs to {CANON_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
