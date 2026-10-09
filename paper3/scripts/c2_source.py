"""Which Phase-9C dataset the analyses read -- one switch, so no script can
read a mix of the two.

  canonical (default)  data/live_runs/phase_c2_canonical/ -- built by
                       scripts/build_9c_canonical.py from the subagent
                       transcripts: every call the agent made, in order, with
                       the hook's failed-call blind spot repaired.
  hook                 data/live_runs/phase_c2/ -- the published hook-only
                       data, kept unchanged so every pre-registered score can
                       be reproduced exactly as originally scored.

Set HEART_9C_SOURCE=hook to reproduce the original scoring. The two audit
scripts (hook_coverage_audit.py, transcript_timestamp_check.py) read the hook
directory directly, by design: auditing the hook is their job.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_DIR = ROOT / "data" / "live_runs" / "phase_c2"
CANON_DIR = ROOT / "data" / "live_runs" / "phase_c2_canonical"
SOURCE = os.environ.get("HEART_9C_SOURCE", "canonical")
if SOURCE not in ("canonical", "hook"):
    raise SystemExit(f"HEART_9C_SOURCE must be 'canonical' or 'hook', not {SOURCE!r}")
C2 = CANON_DIR if SOURCE == "canonical" else HOOK_DIR
# Reports are written here, so a hook-mode run can never overwrite the
# canonical reports -- otherwise whichever source ran last would decide what
# the published report says.
PILOT = ROOT / "data" / "swebench_pilot"
REPORT_DIR = PILOT if SOURCE == "canonical" else PILOT / "as_originally_scored"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_LINE = ("**Data source: canonical** -- Phase-9C sessions recounted from the "
               "subagent transcripts, with the failed tool calls the logging hook "
               "never saw restored (`RECONCILIATION_9C.md`)."
               if SOURCE == "canonical" else
               "**Data source: hook, as originally scored** -- the published "
               "scoring, which could not see failed tool calls.")
