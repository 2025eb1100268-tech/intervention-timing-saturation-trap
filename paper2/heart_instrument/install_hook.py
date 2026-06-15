"""Install the heart_instrument PostToolUse logger hook into the user's
Claude Code settings (~/.claude/settings.json).

Schema verified against the official hooks reference
(code.claude.com/docs/en/hooks):

    "hooks": {
      "PostToolUse": [
        {"matcher": "*",
         "hooks": [{"type": "command", "command": "...", "timeout": 10}]}
      ]
    }

Behavior:
  - backs up settings.json to settings.json.heart_backup_<n> before writing
  - idempotent: detects an already-installed entry (by the HOOK_TAG token in
    the command string) and does nothing
  - uses the absolute path of the current Python interpreter + hook script,
    quoted for the Windows shell form
  - timeout 10 s and exit-0-always hook script => log-only, never blocks

Takes effect from the NEXT Claude Code session (hooks load at session start).

Usage:
    python heart_instrument/install_hook.py
    python heart_instrument/uninstall_hook.py
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"
HOOK_SCRIPT = (Path(__file__).resolve().parent / "hook_logger.py")
HOOK_TAG = "heart_instrument/hook_logger.py"  # identity token for (un)install


def build_command() -> str:
    py = sys.executable
    return f'"{py}" "{HOOK_SCRIPT}"'


def main():
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

    hooks = settings.setdefault("hooks", {})
    ptu = hooks.setdefault("PostToolUse", [])

    # idempotency: already installed?
    for entry in ptu:
        for h in entry.get("hooks", []):
            if HOOK_TAG.replace("/", os.sep) in str(h.get("command", "")) or \
               HOOK_TAG in str(h.get("command", "")).replace("\\", "/"):
                print("already installed; nothing to do")
                return

    ptu.append({
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": build_command(),
            "timeout": 10,
        }],
    })

    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"installed PostToolUse logger hook into {SETTINGS}")
    print(f"hook script: {HOOK_SCRIPT}")
    print("logs will appear under ~/.claude/heart_instrument_logs/<session_id>.jsonl")
    print("NOTE: takes effect from the NEXT Claude Code session.")


if __name__ == "__main__":
    main()
