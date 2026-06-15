"""Phase 6 Task 3: real agentic debugging runs with native wall-clock logging.

The Claude Code CLI is not invocable in this environment (not on PATH in any
shell; only the VSCode extension's embedded instance exists), so per the
task's sanctioned fallback this uses a scriptable tool-use agent loop
(OpenAI gpt-5.4-mini, single tool call per turn) operating on REAL cloned
open-source repos with deterministically injected bugs. Nothing is simulated:
real API calls, real disk edits, real pytest runs, real wall-clock.

Each run writes data/live_runs/<run_id>/session.jsonl in the SAME record
schema hook_logger.py produces (so heart_instrument/convert.py serves both
sources). Unlike hook logs, these records carry the assistant's text in
"thought" (the loop sees it; Claude Code hooks don't expose it).

Timestamps follow PostToolUse semantics: a record's ts is taken AFTER the
tool's observation is produced, so inter-record dt = one full
thought->tool->observation cycle, comparable to hook-captured sessions.

Bug injection: every spec is an exact old->new text replacement, applied only
if the old text occurs EXACTLY ONCE in the file; otherwise the bug is skipped
and logged in run_meta.json (no fuzzy patching).

Usage:
    python heart_instrument/agent_runner.py            # all 5 runs
    python heart_instrument/agent_runner.py runC       # one run
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MODEL = "gpt-5.4-mini"
MAX_ACTIONS = 50
OBS_TRUNCATE = 2048
REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "data" / "live_runs"
REPOS_DIR = RUNS_DIR / "repos"

# ---------------------------------------------------------------------------
# Run specs: repo, env, default pytest target, goal, bugs (exact old->new).
# ---------------------------------------------------------------------------
RUNS = {
    "runA": {
        "repo": "sortedcontainers",
        "env": {"PYTHONPATH": "src"},
        "pytest_default": "tests/test_coverage_sortedlist.py -q -p no:cacheprovider --override-ini addopts=",
        "goal": ("The test file tests/test_coverage_sortedlist.py has multiple "
                 "failing tests caused by bugs in src/sortedcontainers/"
                 "sortedlist.py. Find and fix every bug in the source until the "
                 "test file passes completely. Never edit test files."),
        "bugs": [
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "                pos -= 1\n                _lists[pos].append(value)",
             "new": "                pos -= 1\n                _lists[pos].insert(0, value)"},
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "        idx = bisect_left(_lists[pos], value)\n\n        return _lists[pos][idx] == value",
             "new": "        idx = bisect_left(_lists[pos], value)\n\n        return _lists[pos][idx] is value"},
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "        pos = bisect_left(_maxes, value)\n\n        if pos == len(_maxes):\n            return\n",
             "new": "        pos = bisect_right(_maxes, value)\n\n        if pos == len(_maxes):\n            return\n"},
        ],
    },
    "runB": {
        "repo": "sortedcontainers",
        "env": {"PYTHONPATH": "src"},
        "pytest_default": "tests/test_coverage_sortedlist.py -q -p no:cacheprovider --override-ini addopts=",
        "goal": ("The test file tests/test_coverage_sortedlist.py has multiple "
                 "failing tests caused by bugs in src/sortedcontainers/"
                 "sortedlist.py. Find and fix every bug in the source until the "
                 "test file passes completely. Never edit test files."),
        "bugs": [
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "        del _lists_pos[idx]\n        self._len -= 1",
             "new": "        del _lists_pos[idx]\n        self._len -= 2"},
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "        pos = bisect_left(_maxes, value)\n\n        if pos == len(_maxes):\n            return False",
             "new": "        pos = bisect_right(_maxes, value)\n\n        if pos == len(_maxes):\n            return False"},
            {"file": "src/sortedcontainers/sortedlist.py",
             "old": "        else:\n            _lists.append([value])\n            _maxes.append(value)\n\n        self._len += 1",
             "new": "        else:\n            _lists.append([value])\n            _maxes.append(value)\n\n        self._len += 2"},
        ],
    },
    "runC": {
        "repo": "toolz",
        "env": {},
        "pytest_default": "toolz/tests/test_itertoolz.py toolz/tests/test_dicttoolz.py -q",
        "goal": ("Several tests in toolz/tests/test_itertoolz.py and "
                 "toolz/tests/test_dicttoolz.py fail because of bugs in "
                 "toolz/itertoolz.py and toolz/dicttoolz.py. Find and fix every "
                 "bug until those two test files pass. Never edit test files. "
                 "(Note: toolz/tests/test_package.py::test_has_version fails for "
                 "environmental reasons in this checkout; it is OUT OF SCOPE -- "
                 "ignore it.)"),
        "bugs": [
            {"file": "toolz/itertoolz.py",
             "old": "    return itertools.islice(seq, n)\n",
             "new": "    return itertools.islice(seq, n + 1)\n"},
            {"file": "toolz/itertoolz.py",
             "old": "    try:\n        return seq[-n:]\n",
             "new": "    try:\n        return seq[-n:][::-1]\n"},
            {"file": "toolz/dicttoolz.py",
             "old": "    rv = factory()\n    for d in dicts:\n        rv.update(d)\n    return rv",
             "new": "    rv = factory()\n    for d in reversed(list(dicts)):\n        rv.update(d)\n    return rv"},
        ],
    },
    "runD": {
        "repo": "toolz",
        "env": {},
        "pytest_default": "toolz/tests/test_itertoolz.py -q",
        "goal": ("Several tests in toolz/tests/test_itertoolz.py fail because of "
                 "bugs in toolz/itertoolz.py. Find and fix every bug until that "
                 "test file passes. Never edit test files. (Note: toolz/tests/"
                 "test_package.py::test_has_version fails for environmental "
                 "reasons; it is OUT OF SCOPE.)"),
        "bugs": [
            {"file": "toolz/itertoolz.py",
             "old": "    return itertools.islice(seq, n, None)\n",
             "new": "    return itertools.islice(seq, n + 1, None)\n"},
            {"file": "toolz/itertoolz.py",
             "old": "    return itertools.islice(seq, 0, None, n)\n",
             "new": "    return itertools.islice(seq, 1, None, n)\n"},
            {"file": "toolz/itertoolz.py",
             "old": "    return next(iter(seq))\n",
             "new": "    return next(iter(seq), None)\n"},
        ],
    },
    "runE": {
        "repo": "more-itertools",
        "env": {},
        "pytest_default": "tests/ -q",   # FULL suite: the slow-test-suite run
        "goal": ("Tests under tests/ fail because of bugs in "
                 "more_itertools/recipes.py and more_itertools/more.py. Find and "
                 "fix every bug until the full tests/ suite passes. Run the FULL "
                 "tests/ suite to verify (it is large; that is expected). Never "
                 "edit test files."),
        "bugs": [
            {"file": "more_itertools/recipes.py",
             "old": "    return list(islice(iterable, n))\n",
             "new": "    return list(islice(iterable, max(0, n - 1)))\n"},
            {"file": "more_itertools/more.py",
             "old": "                if len(chunk) != n:\n                    raise ValueError('iterable is not divisible by n.')",
             "new": "                if len(chunk) > n:\n                    raise ValueError('iterable is not divisible by n.')"},
        ],
    },
}

# ---------------------------------------------------------------------------
# Tools (real disk / subprocess execution inside the run's repo)
# ---------------------------------------------------------------------------
TOOL_SCHEMA = [
    {"type": "function", "function": {
        "name": "list_dir", "description": "List files in a directory of the repo.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file region with line numbers (max 120 lines per call).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "start_line": {"type": "integer"},
            "end_line": {"type": "integer"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "grep_search",
        "description": "Regex search across repo .py files; returns file:line matches.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Exact-match replace in a file. old must occur exactly once.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old": {"type": "string"},
            "new": {"type": "string"}}, "required": ["path", "old", "new"]}}},
    {"type": "function", "function": {
        "name": "run_pytest",
        "description": "Run pytest (default: the task's test target). Optional custom path/args.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": []}}},
]


def t_list_dir(wd: Path, args, env):
    p = wd / (args.get("path") or ".")
    if not p.exists():
        return f"ERROR: {args.get('path')} not found"
    items = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir()
                   if x.name not in (".git", "__pycache__"))
    return "\n".join(items[:200])


def t_read_file(wd: Path, args, env):
    p = wd / args.get("path", "")
    if not p.exists():
        return f"ERROR: {args.get('path')} not found"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    s = max(1, int(args.get("start_line") or 1))
    e = min(len(lines), int(args.get("end_line") or s + 119), s + 119)
    return "\n".join(f"{i}: {lines[i-1]}" for i in range(s, e + 1))


def t_grep_search(wd: Path, args, env):
    pat = args.get("pattern", "")
    try:
        rx = re.compile(pat)
    except re.error as ex:
        return f"ERROR: bad regex: {ex}"
    out = []
    for p in wd.rglob("*.py"):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    out.append(f"{p.relative_to(wd)}:{i}: {line.strip()[:140]}")
                    if len(out) >= 60:
                        return "\n".join(out) + "\n(truncated at 60 matches)"
        except Exception:
            continue
    return "\n".join(out) if out else "(no matches)"


def t_edit_file(wd: Path, args, env):
    p = wd / args.get("path", "")
    if not p.exists():
        return f"ERROR: {args.get('path')} not found"
    text = p.read_text(encoding="utf-8")
    old = args.get("old", "")
    n = text.count(old)
    if n == 0:
        return "ERROR: old text not found (must match exactly, including whitespace)"
    if n > 1:
        return f"ERROR: old text occurs {n} times; provide a longer unique snippet"
    p.write_text(text.replace(old, args.get("new", ""), 1), encoding="utf-8")
    return f"edited {args.get('path')} (1 replacement)"


def t_run_pytest(wd: Path, args, env, default_target: str):
    target = args.get("path") or default_target
    cmd = [sys.executable, "-m", "pytest"] + target.split()
    e = dict(os.environ); e.update(env)
    try:
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True,
                           timeout=300, env=e)
        return (r.stdout + r.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return "ERROR: pytest timed out after 300s"


# ---------------------------------------------------------------------------
def inject_bugs(repo_dir: Path, bugs) -> list:
    """Apply bug specs; return injection log. Resets files via git first."""
    subprocess.run(["git", "checkout", "--", "."], cwd=repo_dir,
                   capture_output=True, text=True)
    log = []
    for i, b in enumerate(bugs):
        p = repo_dir / b["file"]
        text = p.read_text(encoding="utf-8")
        n = text.count(b["old"])
        if n != 1:
            log.append({"bug": i, "file": b["file"], "applied": False,
                        "reason": f"old text occurs {n} times (need exactly 1)"})
            continue
        p.write_text(text.replace(b["old"], b["new"], 1), encoding="utf-8")
        log.append({"bug": i, "file": b["file"], "applied": True})
    return log


_ERROR_MARKERS = ("error:", "exception:", "failed", "traceback", "syntaxerror",
                  "typeerror", "valueerror", "command failed", "non-zero exit",
                  "exit code 1", "exit code 2")


def run_one(run_id: str, client) -> dict:
    spec = RUNS[run_id]
    repo_dir = REPOS_DIR / spec["repo"]
    out_dir = RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "session.jsonl"
    jsonl_path.write_text("", encoding="utf-8")  # fresh log

    injection = inject_bugs(repo_dir, spec["bugs"])
    n_applied = sum(1 for b in injection if b["applied"])

    system = ("You are a software engineer debugging a real open-source Python "
              "repository. Work step by step: run the tests to see failures, "
              "locate the buggy source with grep/read, fix with exact edits, "
              "and re-run tests. One tool call at a time. Before EVERY tool "
              "call, write one or two sentences of reasoning explaining what "
              "you are about to do and why (this mirrors the rationale format "
              "of the reference traces). Stop when the target tests pass.")
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": spec["goal"]}]

    dispatch = {
        "list_dir": lambda a: t_list_dir(repo_dir, a, spec["env"]),
        "read_file": lambda a: t_read_file(repo_dir, a, spec["env"]),
        "grep_search": lambda a: t_grep_search(repo_dir, a, spec["env"]),
        "edit_file": lambda a: t_edit_file(repo_dir, a, spec["env"]),
        "run_pytest": lambda a: t_run_pytest(repo_dir, a, spec["env"],
                                             spec["pytest_default"]),
    }

    n_actions = 0
    finished = False
    for _ in range(MAX_ACTIONS):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMA,
            parallel_tool_calls=False,
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            finished = True
            break
        tc = msg.tool_calls[0]
        try:
            args = json.loads(tc.function.arguments or "{}")
        except Exception:
            args = {}
        fn = dispatch.get(tc.function.name)
        obs = fn(args) if fn else f"ERROR: unknown tool {tc.function.name}"
        messages.append({"role": "tool", "tool_call_id": tc.id,
                         "content": obs[:3500]})

        # PostToolUse-style record: ts AFTER observation
        err = any(m in obs.lower() for m in _ERROR_MARKERS)
        record = {
            "ts": datetime.now().astimezone().isoformat(timespec="microseconds"),
            "event": "PostToolUse",
            "session_id": run_id,
            "tool_name": tc.function.name,
            "tool_input": json.dumps(args, default=str)[:OBS_TRUNCATE],
            "status": "error" if err else "ok",
            "error_indicator": err,
            "observation": obs[:OBS_TRUNCATE],
            "thought": (msg.content or "")[:OBS_TRUNCATE],
        }
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        n_actions += 1

    # verdict: do the target tests pass now?
    final = t_run_pytest(repo_dir, {}, spec["env"], spec["pytest_default"])
    solved = (" passed" in final and " failed" not in final and "error" not in final.lower())

    meta = {
        "run_id": run_id, "repo": spec["repo"], "model": MODEL,
        "bugs_specified": len(spec["bugs"]), "bugs_applied": n_applied,
        "injection_log": injection, "n_actions": n_actions,
        "agent_stopped_itself": finished, "final_tests_green": solved,
        "final_pytest_tail": final[-400:],
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # restore the repo for the next run
    subprocess.run(["git", "checkout", "--", "."], cwd=repo_dir,
                   capture_output=True, text=True)
    return meta


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.stderr.write("OPENAI_API_KEY unset; no scriptable harness -> stopping "
                         "(no simulated timings).\n")
        sys.exit(3)
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    targets = sys.argv[1:] or list(RUNS.keys())
    for rid in targets:
        print(f"=== {rid} ({RUNS[rid]['repo']}) ===", flush=True)
        meta = run_one(rid, client)
        print(f"  actions={meta['n_actions']} bugs_applied={meta['bugs_applied']}"
              f"/{meta['bugs_specified']} green={meta['final_tests_green']} "
              f"self_stop={meta['agent_stopped_itself']}", flush=True)


if __name__ == "__main__":
    main()
