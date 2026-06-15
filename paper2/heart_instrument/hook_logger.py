"""Claude Code PostToolUse hook: log-only wall-clock action logger.

Registered in ~/.claude/settings.json as a PostToolUse hook (matcher "*").
Claude Code invokes this script after every tool call and pipes a JSON
payload on stdin (verified against the official hooks reference,
code.claude.com/docs/en/hooks):

    {
      "session_id": "...", "transcript_path": "...", "cwd": "...",
      "hook_event_name": "PostToolUse",
      "tool_name": "Bash" | "Edit" | "Read" | ...,
      "tool_input": {...},
      "tool_response": {...}
    }

This script appends ONE JSONL line per tool call to a session log:

    ~/.claude/heart_instrument_logs/<session_id>.jsonl

Record schema (the "hook-compatible JSONL" the converter consumes):
    {
      "ts": ISO-8601 wall-clock with microseconds,
      "event": "PostToolUse",
      "session_id": str,
      "tool_name": str            # raw Claude Code tool name
      "tool_input": str,          # JSON-serialized, truncated to 2048 chars
      "status": "ok" | "error",
      "error_indicator": bool,
      "observation": str,         # tool_response excerpt, truncated to 2048
      "thought": ""               # NOT available from hooks; always empty here
    }

ZERO INTERFERENCE GUARANTEES:
  - always exits 0, on every path including internal exceptions
  - prints nothing to stdout/stderr (no JSON output -> no behavior change;
    PostToolUse exit 0 with empty stdout is a no-op for the session)
  - never blocks: pure local file append, no network, no subprocess
  - registered with a short timeout (10 s) by the installer as belt+braces

Hooks load at session start: installing the hook takes effect from the NEXT
Claude Code session (interactive or `claude -p` headless -- the docs confirm
PostToolUse fires in print mode).
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from pathlib import Path

TRUNCATE = 2048
LOG_DIR = Path(os.path.expanduser("~")) / ".claude" / "heart_instrument_logs"

# Substrings that mark an errored tool result (mirrors the heuristic family
# used by ActionEvent.has_error -- duplicated here because the hook must be
# stdlib-only and must NOT import heart_* code).
_ERROR_MARKERS = (
    "error:", "exception:", "failed", "traceback", "syntaxerror",
    "typeerror", "valueerror", "command failed", "non-zero exit",
    "exit code 1", "exit code 2", "permission denied",
)


def _detect_error(tool_response) -> bool:
    try:
        if isinstance(tool_response, dict):
            ec = tool_response.get("exit_code")
            if isinstance(ec, int) and ec != 0:
                return True
            if tool_response.get("is_error") is True:
                return True
            text = json.dumps(tool_response, default=str)
        else:
            text = str(tool_response)
        low = text.lower()
        return any(m in low for m in _ERROR_MARKERS)
    except Exception:
        return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # malformed stdin: do nothing, never interfere

    try:
        session_id = str(payload.get("session_id") or "unknown_session")
        tool_name = str(payload.get("tool_name") or "unknown_tool")
        tool_input = payload.get("tool_input")
        tool_response = payload.get("tool_response")

        err = _detect_error(tool_response)
        record = {
            "ts": datetime.now().astimezone().isoformat(timespec="microseconds"),
            "event": "PostToolUse",
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": json.dumps(tool_input, default=str)[:TRUNCATE],
            "status": "error" if err else "ok",
            "error_indicator": err,
            "observation": json.dumps(tool_response, default=str)[:TRUNCATE],
            "thought": "",  # hooks do not expose assistant reasoning text
        }

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # sanitize session id for a filename
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in session_id)
        with open(LOG_DIR / f"{safe}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # any failure is swallowed: log-only, never block
    return 0


if __name__ == "__main__":
    sys.exit(main())
