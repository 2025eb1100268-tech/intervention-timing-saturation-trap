"""The hook must log failed tool calls, and the installer must register it for them.

Claude Code fires PostToolUse only after a call succeeds and PostToolUseFailure
after one fails. The logger as first released was registered for PostToolUse
alone and never saw a failed call. Pure functions only: no test touches
~/.claude/settings.json.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from heart_instrument.hook_logger import build_record
from heart_instrument.install_hook import install
from heart_instrument.uninstall_hook import uninstall


def test_failure_event_is_an_error_and_keeps_its_detail():
    rec = build_record({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                        "tool_input": {"command": "pytest"}, "error": "Exit code 1",
                        "tool_use_id": "toolu_1", "session_id": "s"})
    assert rec["event"] == "PostToolUseFailure"
    assert rec["error_indicator"] is True and rec["status"] == "error"
    assert "Exit code 1" in rec["observation"]
    assert rec["tool_use_id"] == "toolu_1"


def test_failure_with_tool_response_uses_it():
    rec = build_record({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                        "tool_input": {}, "tool_response": {"stderr": "boom"}})
    assert rec["error_indicator"] is True
    assert json.loads(rec["observation"]) == {"stderr": "boom"}


def test_success_record_unchanged_in_meaning():
    ok = build_record({"hook_event_name": "PostToolUse", "tool_name": "Read",
                       "tool_input": {"file_path": "a.py"},
                       "tool_response": {"content": "x = 1"}})
    assert ok["event"] == "PostToolUse" and ok["error_indicator"] is False
    bad = build_record({"tool_name": "Bash", "tool_input": {},
                        "tool_response": {"stdout": "Traceback (most recent call last)"}})
    assert bad["event"] == "PostToolUse" and bad["error_indicator"] is True


def test_installer_registers_both_events_once_and_uninstaller_removes_both():
    other = {"type": "command", "command": "echo unrelated"}
    settings = {"hooks": {"PostToolUse": [{"matcher": "*", "hooks": [other]}]}}
    assert install(settings) == ["PostToolUse", "PostToolUseFailure"]
    for event in ("PostToolUse", "PostToolUseFailure"):
        cmds = [h["command"] for e in settings["hooks"][event] for h in e["hooks"]]
        assert sum("heart_instrument" in c.replace("\\", "/") for c in cmds) == 1
    assert install(settings) == []
    assert install({"hooks": {}}, ["PostToolUse"]) == ["PostToolUse"]
    assert uninstall(settings) == 2
    assert settings == {"hooks": {"PostToolUse": [{"matcher": "*", "hooks": [other]}]}}
