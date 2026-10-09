"""Phase C2 — clean-git run harness. Supersedes phase_c_subagent.py (now pilot).

THE DEFECT THIS FIXES. In the pilot, bug injection wrote *uncommitted* edits on
top of a pinned commit, so `git diff` handed the agent the answer key. Agents
used it (3 calls in runC and runE of both arms).

THE FIX, and why this shape. Committing the bug makes `git diff` clean but
leaves `git show HEAD` revealing it, so that is not enough. Instead the repo is
rebuilt as a **single orphan root commit** containing the upstream tree with the
bug already in it:

  * `git status --porcelain` is empty
  * `git diff HEAD` is empty
  * `git log --oneline` has exactly ONE entry
  * `git show HEAD` shows the whole tree as an initial add -- no bug-specific
    diff exists anywhere in the history to recover
  * no other local branch or ref remains to diff against

Five assertions, checked and LOGGED per run before the agent starts. A run whose
assertions fail is aborted, not repaired.

Git stays present (unlike Paper 2's five-tool harness, which had none), so the
condition is realistic: the agent has version control, it just has no injected
diff to read.

RESTORE. The pinned SHA is recorded before rebuilding and the original ref is
recreated afterwards; the upstream objects survive in the object store, and
`data/live_runs/REPO_PROVENANCE.md` remains the authority.

Two-step around the agent launch, as in the pilot -- attribution is by time
window because subagent tool calls land in the parent session log:

    python scripts/phase_c2_subagent.py prepare <spec> --model <m> --effort <e>
    ... operator launches EXACTLY ONE subagent, no other tool call ...
    python scripts/phase_c2_subagent.py harvest
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from heart_instrument.agent_runner import REPOS_DIR  # noqa: E402

# Phase 9C spec set: frozen and mechanically verified by
# scripts/build_phase9c_specs.py (baseline passes, each bug's `old` occurs
# exactly once, target tests fail after injection). Falls back to the pilot's
# RUNS only if the 9C set is absent.
_SPEC_FILE = ROOT / "data" / "swebench_pilot" / "phase9c_specs.json"
if _SPEC_FILE.exists():
    _d = json.loads(_SPEC_FILE.read_text(encoding="utf-8"))
    RUNS = {r["id"]: {"repo": r["repo"], "env": r["env"],
                      "pytest_default": r["pytest_default"],
                      "goal": r["goal"], "bugs": r["verified_bugs"],
                      "module": r["module"]}
            for r in _d["specs"]}
else:                                                    # pragma: no cover
    from heart_instrument.agent_runner import RUNS       # noqa: F401


def inject_bugs(repo_dir, bugs):
    """Exactly-once replacement, same contract as the frozen injector."""
    log = []
    for b in bugs:
        f = repo_dir / b["file"] if "file" in b else None
        if f is None:
            f = repo_dir / b["module"] if "module" in b else None
        rec = {**b, "applied": False}
        if f is None or not f.exists():
            rec["reason"] = f"file not found: {f}"
            log.append(rec); continue
        txt = f.read_text(encoding="utf-8")
        n = txt.count(b["old"])
        if n != 1:
            rec["reason"] = f"old occurs {n} times, need exactly 1"
            log.append(rec); continue
        f.write_text(txt.replace(b["old"], b["new"], 1), encoding="utf-8")
        rec["applied"] = True
        log.append(rec)
    return log

OUT = ROOT / "data" / "live_runs" / "phase_c2"
STATE = OUT / "_window.json"
LOG_DIR = Path(os.path.expanduser("~")) / ".claude" / "heart_instrument_logs"

STEP, THRESHOLD, HALF_LIFE = 0.15, 0.7, 150.0
MIN_OBS = math.ceil(THRESHOLD / STEP)          # 5
GIT_ID = ["-c", "user.name=upstream", "-c", "user.email=upstream@example.invalid"]


def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}:\n{r.stderr}")
    return r.stdout.strip()


def now() -> datetime:
    return datetime.now().astimezone()


def session_log() -> Path:
    logs = sorted(LOG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not logs:
        sys.exit("no hook logs found; is the PostToolUse hook installed?")
    return logs[-1]


def pct(s: List[float], p: float) -> float:
    if not s:
        return float("nan")
    k = (len(s) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


# ---------------------------------------------------------------------------
def rebuild_clean(repo: Path, bugs) -> Dict[str, Any]:
    """Inject bugs, then rebuild history as one orphan root commit."""
    pinned = git(repo, "rev-parse", "HEAD")
    orig_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False) or "detached"

    git(repo, "checkout", "-f", pinned)
    git(repo, "clean", "-fd", check=False)
    injection = inject_bugs(repo, bugs)

    # Orphan root commit: no parent, so no diff in history reveals the bug.
    git(repo, "checkout", "--orphan", "_c2_clean")
    git(repo, "add", "-A")
    git(repo, *GIT_ID, "commit", "-q", "-m", "Initial commit")
    # Drop every other ref so nothing remains to diff against.
    for ref in git(repo, "for-each-ref", "--format=%(refname)").splitlines():
        if ref.strip() and not ref.endswith("_c2_clean"):
            git(repo, "update-ref", "-d", ref.strip(), check=False)
    git(repo, "reflog", "expire", "--expire=now", "--all", check=False)

    head = git(repo, "rev-parse", "HEAD")

    # Assertion 5 must be formulated as "no diff ISOLATES the bug", not "the
    # bug text is absent from git show". On an orphan root commit every path is
    # an addition, so `git show HEAD` necessarily contains the full file
    # contents -- including the bug -- while containing no modification hunk
    # that distinguishes the bug from upstream code. The satisfiable check is
    # therefore that every path in the sole commit is status A, never M.
    name_status = git(repo, "show", "HEAD", "--name-status", "--format=")
    statuses = {ln.split("\t")[0].strip() for ln in name_status.splitlines()
                if ln.strip()}

    # And separately: confirm the bug really is in the working tree, so a
    # passing assertion set cannot mean "no bug was injected".
    injected_present = True
    for b in bugs:
        if not b.get("new"):
            continue
        f = repo / b["file"]
        if f.exists() and b["new"] not in f.read_text(encoding="utf-8", errors="replace"):
            injected_present = False

    checks = {
        "status_porcelain_empty": git(repo, "status", "--porcelain") == "",
        "diff_head_empty": git(repo, "diff", "HEAD") == "",
        "single_commit": git(repo, "rev-list", "--count", "HEAD") == "1",
        "no_other_branch": len([b for b in git(repo, "branch", "-a").splitlines()
                                if b.strip()]) == 1,
        "no_modification_hunk_in_history": statuses.issubset({"A"}) and bool(statuses),
        "injected_bug_present_in_worktree": injected_present,
    }
    return {"pinned_sha": pinned, "original_branch": orig_branch,
            "clean_head": head, "injection_log": injection,
            "bugs_applied": sum(1 for b in injection if b["applied"]),
            "assertions": checks, "all_passed": all(checks.values())}


def restore(repo: Path, pinned: str, orig_branch: str) -> bool:
    try:
        git(repo, "checkout", "-f", pinned)
        if orig_branch and orig_branch != "detached":
            git(repo, "branch", "-f", orig_branch, pinned, check=False)
            git(repo, "checkout", "-f", orig_branch, check=False)
        git(repo, "branch", "-D", "_c2_clean", check=False)
        git(repo, "clean", "-fd", check=False)
        return git(repo, "rev-parse", "HEAD") == pinned
    except Exception:
        return False


def _resolve_model(session_id: str, lo: datetime, hi: datetime):
    """(model_id, transcript path) for the single subagent transcript whose
    first line falls inside the window, or (None, None) if not exactly one."""
    hits = []
    for f in Path.home().glob(f".claude/projects/*/{session_id}/subagents/agent-*.jsonl"):
        first, models = None, set()
        for line in f.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if first is None and r.get("timestamp"):
                first = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            m = (r.get("message") or {}).get("model")
            if m:
                models.add(m)
        if first is not None and lo < first <= hi:
            hits.append((f, models))
    if len(hits) != 1 or len(hits[0][1]) != 1:
        return None, None
    return next(iter(hits[0][1])), str(hits[0][0])


# ---------------------------------------------------------------------------
def cmd_prepare(a) -> int:
    if a.spec not in RUNS:
        sys.exit(f"unknown spec {a.spec}; have {sorted(RUNS)}")
    spec = RUNS[a.spec]
    repo = REPOS_DIR / spec["repo"]
    OUT.mkdir(parents=True, exist_ok=True)

    bugs = [{**b, "file": spec["module"]} for b in spec["bugs"]]
    built = rebuild_clean(repo, bugs)
    log = session_log()
    st = {
        "spec": a.spec, "model": a.model, "effort": a.effort,
        "repeat": a.repeat, "repo": spec["repo"], "repo_dir": str(repo),
        "protocol": "clean-git-orphan-root-v2",
        "log": str(log), "window_open": now().isoformat(),
        "pytest_default": spec["pytest_default"], "env": spec["env"],
        "bugs_specified": len(spec["bugs"]), **built,
    }
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")

    print(f"spec     : {a.spec} ({spec['repo']})  repeat {a.repeat}")
    print(f"model    : {a.model}   effort: {a.effort}")
    print(f"bugs     : {built['bugs_applied']}/{len(spec['bugs'])} applied")
    for b in built["injection_log"]:
        if not b["applied"]:
            print(f"  SKIPPED: {b.get('file')} -- {b.get('reason','n/a')}")
    print(f"pinned   : {built['pinned_sha'][:12]} -> clean head "
          f"{built['clean_head'][:12]}")
    print("clean-git assertions:")
    for k, v in built["assertions"].items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    if not built["all_passed"]:
        print("\nASSERTIONS FAILED -- aborting. Restoring repo.")
        restore(repo, built["pinned_sha"], built["original_branch"])
        STATE.unlink(missing_ok=True)
        return 2
    print(f"\nwindow open: {st['window_open']}")
    print("\nGOAL (paste verbatim into the subagent):")
    print("-" * 68)
    print(spec["goal"])
    print("-" * 68)
    print("\nLaunch EXACTLY ONE subagent. No other tool call until it returns, "
          "then: harvest")
    return 0


def cmd_harvest(a) -> int:
    if not STATE.exists():
        sys.exit("no open window; run `prepare` first")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    close = now()
    lo = datetime.fromisoformat(st["window_open"])

    recs = []
    with open(st["log"], encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                t = datetime.fromisoformat(r["ts"])
            except Exception:
                continue
            operator = (r.get("tool_name") == "Agent"
                        or "phase_c2_subagent" in (r.get("tool_input") or "")
                        or "phase_c_subagent" in (r.get("tool_input") or ""))
            if lo < t <= close and not operator:
                r["_t"] = t
                recs.append(r)
    recs.sort(key=lambda r: r["_t"])

    ts = [r["_t"] for r in recs]
    dts = [(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))]
    n = len(recs)
    errs = sum(bool(r["error_indicator"]) for r in recs)
    p = errs / n if n else 0.0
    tools = {t: sum(1 for r in recs if r["tool_name"] == t)
             for t in sorted({r["tool_name"] for r in recs})}
    gitn = sum(any(k in (r.get("tool_input") or "")
                   for k in ("git diff", "git status", "git show", "git log",
                             "git stash", "git reflog"))
               for r in recs)

    repo = Path(st["repo_dir"])
    fin = subprocess.run(["python", "-m", "pytest", *st["pytest_default"].split()],
                         cwd=repo, capture_output=True, text=True,
                         env={**os.environ, **{k: str(v) for k, v in st["env"].items()}})
    tail = (fin.stdout + fin.stderr)[-600:]
    green = " passed" in tail and " failed" not in tail and "error" not in tail.lower()

    s = sorted(dts)
    med = statistics.median(dts) if dts else float("nan")
    x = STEP * p / THRESHOLD
    dstar = (-(HALF_LIFE / math.log(2.0)) * math.log(1.0 - x)) if x < 1.0 else None
    out = {
        **{k: st[k] for k in ("spec", "model", "effort", "repeat", "repo",
                              "protocol", "pinned_sha", "clean_head",
                              "bugs_specified", "bugs_applied", "injection_log",
                              "assertions", "window_open")},
        "window_close": close.isoformat(),
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
        "final_tests_green": green, "final_pytest_tail": tail[-400:],
    }
    # Model identity from the record, not the alias. The Agent tool's alias
    # `opus` meant Opus 5 for Phase 9C and Opus 5.5 for 9D; naming files by the
    # label would have let 9D overwrite frozen 9C data. Find the one subagent
    # transcript that began inside this window and take the model it recorded.
    model_id, transcript = _resolve_model(Path(st["log"]).stem, lo, close)
    out["model_id"] = model_id
    out["transcript"] = transcript
    name = model_id or st["model"]
    if model_id is None:
        print("  WARNING: no unique subagent transcript in the window; "
              "filename falls back to the label, which aliases can make ambiguous")
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{st['spec']}_{name}_r{st['repeat']}.json"
    if dest.exists():
        sys.exit(f"refusing to overwrite {dest.name}")
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    (OUT / st["spec"]).mkdir(exist_ok=True)
    (OUT / st["spec"] / f"session_{name}_r{st['repeat']}.jsonl").write_text(
        "\n".join(json.dumps({k: v for k, v in r.items() if k != "_t"})
                  for r in recs) + "\n", encoding="utf-8")

    ok = restore(repo, st["pinned_sha"], st["original_branch"])
    STATE.unlink()

    d = out["dt_stats"]
    print(f"{st['spec']} {st['model']} r{st['repeat']}: actions={n} dts={len(dts)}")
    print(f"  tools: {tools}")
    print(f"  git recon calls: {gitn}  (clean protocol -> should find nothing)")
    print(f"  dt: min {d['min']} med {d['median']} p90 {d['p90']} max {d['max']}")
    print(f"  err {p:.2f} | delta* {out['derived']['delta_star_s']}s | "
          f"r_starv {out['derived']['r_starv']} | r_cliff {out['derived']['r_cliff']}")
    print(f"  tests green: {green} | repo restored to pinned: {ok}")
    print(f"  saved: {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("spec")
    p.add_argument("--model", default="opus")
    p.add_argument("--effort", default="inherited-session-default")
    p.add_argument("--repeat", type=int, default=1)
    p.set_defaults(fn=cmd_prepare)
    h = sub.add_parser("harvest")
    h.set_defaults(fn=cmd_harvest)
    r = sub.add_parser("restore-check")
    r.add_argument("repo")
    r.set_defaults(fn=lambda a: (print(git(REPOS_DIR / a.repo, "status", "--porcelain")
                                       or "clean"), 0)[1])
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
