"""Install the heart_instrument logger hook into the user's Claude Code
settings (~/.claude/settings.json), for BOTH tool-call events.

Claude Code fires `PostToolUse` only after a tool call succeeds and
`PostToolUseFailure` after one fails (code.claude.com/docs/en/hooks). An
earlier version of this installer registered PostToolUse alone, so the logger
never saw a failed call -- including every shell command that exits non-zero.
It now registers the logger for both events by default.

Schema verified against the official hooks reference:

    "hooks": {
      "PostToolUse":        [{"matcher": "*", "hooks": [{"type": "command", "command": "...", "timeout": 10}]}],
      "PostToolUseFailure": [{"matcher": "*", "hooks": [{"type": "command", "command": "...", "timeout": 10}]}]
    }

Behavior:
  - backs up settings.json to settings.json.heart_backup_<n> before writing
  - idempotent per event: an event that already carries the logger (found by
    the HOOK_TAG token in the command string) is left alone
  - uses the absolute path of the current Python interpreter + hook script,
    quoted for the Windows shell form
  - timeout 10 s and exit-0-always hook script => log-only, never blocks

Register each event in exactly ONE settings scope: hooks from user and project
settings both run, so the same event registered in both logs every call twice.
If a project's .claude/settings.json already registers PostToolUseFailure,
install only the other event:

    python heart_instrument/install_hook.py --events PostToolUse

Takes effect from the NEXT Claude Code session (hooks load at session start).

Usage:
    python heart_instrument/install_hook.py
    python heart_instrument/uninstall_hook.py
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"
HOOK_SCRIPT = (Path(__file__).resolve().parent / "hook_logger.py")
HOOK_TAG = "heart_instrument/hook_logger.py"  # identity token for (un)install
EVENTS = ("PostToolUse", "PostToolUseFailure")


def build_command() -> str:
    py = sys.executable
    return f'"{py}" "{HOOK_SCRIPT}"'


def _is_ours(h: dict) -> bool:
    return HOOK_TAG in str(h.get("command", "")).replace("\\", "/")


def install(settings: dict, events=EVENTS) -> list:
    """Add the logger to each event that lacks it. Returns the events added."""
    hooks = settings.setdefault("hooks", {})
    added = []
    for event in events:
        entries = hooks.setdefault(event, [])
        if any(_is_ours(h) for e in entries for h in e.get("hooks", [])):
            continue
        entries.append({
            "matcher": "*",
            "hooks": [{
                "type": "command",
                "command": build_command(),
                "timeout": 10,
            }],
        })
        added.append(event)
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--events", nargs="+", choices=EVENTS, default=list(EVENTS),
                    help="events to register (default: both)")
    args = ap.parse_args(argv)

    if not SETTINGS.parent.exists():
        sys.stderr.write(f"{SETTINGS.parent} not found -- is Claude Code installed?\n")
        sys.exit(1)

    settings = {}
    if SETTINGS.exists():
        settings = json.loads(SETTINGS.read_text(encoding="utf-8-sig") or "{}")
        # backup
        n = 1
        while (bak := SETTINGS.with_name(f"settings.json.heart_backup_{n}")).exists():
            n += 1
        bak.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print(f"backup: {bak}")

    added = install(settings, args.events)
    if not added:
        print("already installed for " + ", ".join(args.events) + "; nothing to do")
        return

    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"installed logger hook for {', '.join(added)} into {SETTINGS}")
    print(f"hook script: {HOOK_SCRIPT}")
    print("logs will appear under ~/.claude/heart_instrument_logs/<session_id>.jsonl")
    print("NOTE: takes effect from the NEXT Claude Code session.")


if __name__ == "__main__":
    main()
