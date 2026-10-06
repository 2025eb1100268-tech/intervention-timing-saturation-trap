"""Remove the heart_instrument logger hook from ~/.claude/settings.json, from
both tool-call events (PostToolUse and PostToolUseFailure). Backs up before
writing. Idempotent.

Usage:
    python heart_instrument/uninstall_hook.py
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

SETTINGS = Path(os.path.expanduser("~")) / ".claude" / "settings.json"
HOOK_TAG = "heart_instrument/hook_logger.py"
EVENTS = ("PostToolUse", "PostToolUseFailure")


def _is_ours(h: dict) -> bool:
    cmd = str(h.get("command", "")).replace("\\", "/")
    return HOOK_TAG in cmd


def uninstall(settings: dict) -> int:
    """Strip the logger from every event it is registered for. Returns the
    number of hook entries removed."""
    hooks = settings.get("hooks", {})
    removed = 0
    for event in EVENTS:
        entries = hooks.get(event, [])
        new_entries = []
        for entry in entries:
            kept = [h for h in entry.get("hooks", []) if not _is_ours(h)]
            removed += len(entry.get("hooks", [])) - len(kept)
            if kept:
                entry["hooks"] = kept
                new_entries.append(entry)
        if new_entries:
            hooks[event] = new_entries
        else:
            hooks.pop(event, None)
    if "hooks" in settings and not settings["hooks"]:
        settings.pop("hooks")
    return removed


def main():
    if not SETTINGS.exists():
        print("no settings.json; nothing to do")
        return
    settings = json.loads(SETTINGS.read_text(encoding="utf-8-sig") or "{}")
    if not any(settings.get("hooks", {}).get(e) for e in EVENTS):
        print("no PostToolUse or PostToolUseFailure hooks configured; nothing to do")
        return

    n = 1
    while (bak := SETTINGS.with_name(f"settings.json.heart_backup_{n}")).exists():
        n += 1
    bak.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"backup: {bak}")

    removed = uninstall(settings)
    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"removed {removed} heart_instrument hook entr{'y' if removed==1 else 'ies'} from {SETTINGS}")


if __name__ == "__main__":
    main()
