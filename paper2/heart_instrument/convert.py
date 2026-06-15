"""Convert a heart_instrument session JSONL log into (a) the spec trajectory
format the existing parser accepts and (b) a parallel real-timing file.

Input: a JSONL file where each line is one PostToolUse-style record
(written either by hook_logger.py during a Claude Code session, or natively
by agent_runner.py during a scripted run):

    {"ts": iso8601, "event": "PostToolUse", "session_id": str,
     "tool_name": str, "tool_input": str(JSON, truncated 2KB),
     "status": "ok"|"error", "error_indicator": bool,
     "observation": str(truncated 2KB), "thought": str}

Outputs:
  <out>/trajectory.json  -- {"trajectory": [{thought, action, observation}]}
      where action = {"tool": <canonical>, "args": {...}} (the dict form
      heart_adapters.claude_code.trajectory._extract_tool_and_args accepts).
  <out>/timing.json      -- {"session_id", "n_actions", "timestamps": [...],
                             "dt_seconds": [null, dt1, dt2, ...]}
      dt[i] = wall-clock seconds between action i-1 and action i. REAL and
      non-uniform, unlike the synthetic ordinal in the SWE-bench traces.

TOOL NAME MAPPING (every decision documented)
----------------------------------------------
The signal rules in heart_adapters/claude_code/signals.py key on the aime
canonical names. Mapping both vocabularies we produce:

  Claude Code hook names:
    Bash, PowerShell            -> bash_tool   (rules 1/6/7 key on bash_tool
                                                + tool_args["command"])
    Edit, Write, MultiEdit,
    NotebookEdit                -> str_replace_editor  (rules 3/5 key on
                                                editor names)
    Read                        -> str_replace_editor  (aime convention: file
                                                viewing was str_replace_editor
                                                with command=view; mapping Read
                                                the same way keeps repetition
                                                detection comparable)
    Grep, Glob                  -> codebase_search     (rule 8 long_search
                                                keys on codebase_search)
    WebSearch, WebFetch         -> web_search          (rule 8)
    TodoWrite, Task, Agent,
    ExitPlanMode, AskUserQuestion -> sequential_thinking (planning/meta tools;
                                                the aime traces' analogue.
                                                NO signal rule keys on it, so
                                                these are zero-signal actions,
                                                exactly like sequential_thinking
                                                in the SWE-bench traces)
  agent_runner.py names:
    run_pytest, run_python, bash, list_dir -> bash_tool (shell-executed)
    read_file, write_file       -> str_replace_editor
    grep_search                 -> codebase_search

  Anything unmapped passes through lowercased, generating no signals
  (documented limitation, same zero-signal behavior as sequential_thinking).

ARG mapping: tool_input is parsed back from its JSON string. bash-mapped
tools get {"command": ...}; editor-mapped get the original keys (path /
file_path / content / new_str pass through -- edit_size() reads new_str/
content). If the truncated JSON no longer parses, args = {"raw": <string>}.

THOUGHT AVAILABILITY: hook logs have thought == "" (Claude Code hooks do not
expose assistant reasoning text). Converted hook traces therefore CANNOT
exercise A9/text_features (hedge/cycle/tone) or rule_hedge_words /
rule_reasoning_action_ratio's reasoning-length gate -- documented here and
in TIMING_REPORT.md. agent_runner.py logs DO carry the assistant text as
thought, so runner traces exercise the full rule set.

Usage:
    python heart_instrument/convert.py <session.jsonl> <out_dir>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

CANONICAL = {
    # Claude Code hook vocabulary
    "bash": "bash_tool", "powershell": "bash_tool",
    "edit": "str_replace_editor", "write": "str_replace_editor",
    "multiedit": "str_replace_editor", "notebookedit": "str_replace_editor",
    "read": "str_replace_editor",
    "grep": "codebase_search", "glob": "codebase_search",
    "websearch": "web_search", "webfetch": "web_search",
    "todowrite": "sequential_thinking", "task": "sequential_thinking",
    "agent": "sequential_thinking", "exitplanmode": "sequential_thinking",
    "askuserquestion": "sequential_thinking",
    # agent_runner vocabulary
    "run_pytest": "bash_tool", "run_python": "bash_tool",
    "list_dir": "bash_tool",
    "read_file": "str_replace_editor", "write_file": "str_replace_editor",
    "edit_file": "str_replace_editor",
    "grep_search": "codebase_search",
}

# Runner tools whose args must be rewritten into a bash-style command so the
# bash-keyed rules (test detection, error context) see a realistic command.
_RUNNER_BASHIFY = {
    "run_pytest": lambda a: f"python -m pytest {a.get('path', '.')} -q",
    "run_python": lambda a: f"python {a.get('path', '')}",
    "list_dir":   lambda a: f"ls {a.get('path', '.')}",
    "bash":       lambda a: a.get("command", ""),
}


def map_tool(raw_name: str, args: dict) -> tuple[str, dict]:
    low = raw_name.lower()
    canon = CANONICAL.get(low, low)
    if low in _RUNNER_BASHIFY:
        return canon, {"command": _RUNNER_BASHIFY[low](args)}
    if canon == "bash_tool" and "command" not in args:
        # hook Bash records carry {"command": ...} already; this is a guard
        args = {"command": args.get("raw", json.dumps(args, default=str)[:400])}
    return canon, args


def parse_args_field(tool_input: str) -> dict:
    try:
        v = json.loads(tool_input)
        if isinstance(v, dict):
            return v
        return {"raw": str(v)}
    except Exception:
        return {"raw": tool_input}


def convert(jsonl_path: Path, out_dir: Path) -> dict:
    records = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))

    turns = []
    timestamps = []
    for r in records:
        raw_args = parse_args_field(r.get("tool_input", "{}"))
        tool, args = map_tool(r.get("tool_name", "unknown"), raw_args)
        turns.append({
            "thought": r.get("thought", "") or "",
            "action": {"tool": tool, "args": args},
            "observation": r.get("observation", "") or "",
        })
        timestamps.append(r["ts"])

    dts = [None]
    times = [datetime.fromisoformat(t) for t in timestamps]
    for i in range(1, len(times)):
        dts.append(round((times[i] - times[i - 1]).total_seconds(), 6))

    out_dir.mkdir(parents=True, exist_ok=True)
    traj = {"trajectory": turns}
    (out_dir / "trajectory.json").write_text(
        json.dumps(traj, indent=1, default=str), encoding="utf-8")
    timing = {
        "session_id": records[0].get("session_id", "unknown") if records else "empty",
        "n_actions": len(turns),
        "timestamps": timestamps,
        "dt_seconds": dts,
    }
    (out_dir / "timing.json").write_text(
        json.dumps(timing, indent=1), encoding="utf-8")
    return timing


def main():
    if len(sys.argv) != 3:
        print("usage: python heart_instrument/convert.py <session.jsonl> <out_dir>")
        sys.exit(1)
    timing = convert(Path(sys.argv[1]), Path(sys.argv[2]))
    real_dts = [d for d in timing["dt_seconds"] if d is not None]
    if real_dts:
        s = sorted(real_dts)
        print(f"converted {timing['n_actions']} actions; "
              f"dt min/med/max = {s[0]:.2f}/{s[len(s)//2]:.2f}/{s[-1]:.2f} s")
    else:
        print(f"converted {timing['n_actions']} actions (no dt — <2 actions)")


if __name__ == "__main__":
    main()
