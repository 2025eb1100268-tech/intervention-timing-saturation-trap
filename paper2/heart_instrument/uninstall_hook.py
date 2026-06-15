"""Remove the heart_instrument PostToolUse logger hook from
~/.claude/settings.json. Backs up before writing. Idempotent.

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


def _is_ours(h: dict) -> bool:
    cmd = str(h.get("command", "")).replace("\\", "/")
    return HOOK_TAG in cmd


def main():
    if not SETTINGS.exists():
        print("no settings.json; nothing to do")
        return
    settings = json.loads(SETTINGS.read_text(encoding="utf-8-sig") or "{}")
    ptu = settings.get("hooks", {}).get("PostToolUse", [])
    if not ptu:
        print("no PostToolUse hooks configured; nothing to do")
        return

    n = 1
    while (bak := SETTINGS.with_name(f"settings.json.heart_backup_{n}")).exists():
        n += 1
    bak.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"backup: {bak}")

    removed = 0
    new_ptu = []
    for entry in ptu:
        kept = [h for h in entry.get("hooks", []) if not _is_ours(h)]
        removed += len(entry.get("hooks", [])) - len(kept)
        if kept:
            entry["hooks"] = kept
            new_ptu.append(entry)
    if new_ptu:
        settings["hooks"]["PostToolUse"] = new_ptu
    else:
        settings.get("hooks", {}).pop("PostToolUse", None)
        if not settings.get("hooks"):
            settings.pop("hooks", None)

    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"removed {removed} heart_instrument hook entr{'y' if removed==1 else 'ies'} from {SETTINGS}")


if __name__ == "__main__":
    main()
