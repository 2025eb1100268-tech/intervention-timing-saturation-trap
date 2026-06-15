"""Phase 6 Task 4: TIMING_REPORT.md from the live-run session logs.

Reads data/live_runs/run*/session.jsonl (+ run_meta.json), computes per-run
and pooled inter-action dt distributions, threshold fractions, lag-1
autocorrelation, and a per-tool breakdown. Compares explicitly against the
Phase 4b toy-probe numbers (timing_probe/timing_raw.json).

Run from repo root:  python heart_instrument/timing_report.py
"""
from __future__ import annotations
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

RUNS_DIR = Path("data/live_runs")
PROBE_RAW = Path("timing_probe/timing_raw.json")


def load_run(run_dir: Path):
    recs = [json.loads(l) for l in
            (run_dir / "session.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    ts = [datetime.fromisoformat(r["ts"]) for r in recs]
    dts = [(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))]
    meta = {}
    mp = run_dir / "run_meta.json"
    if mp.exists():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    return recs, dts, meta


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    lo = int(math.floor(k)); hi = int(math.ceil(k))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def dist(vals):
    s = sorted(vals)
    if not s:
        return None
    return {"n": len(s), "min": s[0], "p25": pct(s, 0.25),
            "median": pct(s, 0.50), "p75": pct(s, 0.75),
            "p90": pct(s, 0.90), "max": s[-1]}


def lag1_autocorr(vals):
    n = len(vals)
    if n < 3:
        return None
    mu = statistics.mean(vals)
    var = sum((v - mu) ** 2 for v in vals)
    if var == 0:
        return None
    cov = sum((vals[i] - mu) * (vals[i + 1] - mu) for i in range(n - 1))
    return cov / var


def frow(label, d):
    return (f"| {label} | {d['n']} | {d['min']:.2f} | {d['p25']:.2f} | "
            f"{d['median']:.2f} | {d['p75']:.2f} | {d['p90']:.2f} | {d['max']:.2f} |")


def main():
    run_dirs = sorted(p for p in RUNS_DIR.glob("run*") if (p / "session.jsonl").exists())
    if not run_dirs:
        sys.stderr.write("no run*/session.jsonl found\n"); sys.exit(1)

    out = []
    w = out.append
    w("# Live-run timing report (Phase 6, Task 4)")
    w("")
    w("Real wall-clock inter-action times from instrumented agentic debugging "
      "runs on real cloned open-source repos (sortedcontainers, toolz, "
      "more-itertools) with deterministically injected bugs. Harness: "
      "scriptable tool-use loop (gpt-5.4-mini, one tool call per action), "
      "native PostToolUse-style logging -- the Claude Code CLI is not "
      "invocable in this environment, so the task's sanctioned fallback "
      "harness was used; the hook (heart_instrument/hook_logger.py) is "
      "installed and produces the identical log format for the user's own "
      "Claude Code sessions. dt = gap between consecutive post-observation "
      "timestamps = one full thought->tool->observation cycle.")
    w("")

    all_dts = []
    all_recs = []
    w("## Per-run distributions (seconds)")
    w("")
    w("| run | n dts | min | p25 | median | p75 | p90 | max |")
    w("|---|---|---|---|---|---|---|---|")
    metas = {}
    per_run = {}
    for rd in run_dirs:
        recs, dts, meta = load_run(rd)
        metas[rd.name] = meta
        per_run[rd.name] = (recs, dts)
        all_dts.extend(dts)
        all_recs.extend(recs)
        d = dist(dts)
        if d:
            w(frow(f"{rd.name} ({meta.get('repo','?')})", d))
    pooled = dist(all_dts)
    w(frow("**pooled**", pooled))
    w("")

    w("### Run outcomes")
    w("")
    w("| run | repo | actions | bugs applied | tests green | self-stopped |")
    w("|---|---|---|---|---|---|")
    for name, meta in metas.items():
        w(f"| {name} | {meta.get('repo','?')} | {meta.get('n_actions','?')} | "
          f"{meta.get('bugs_applied','?')}/{meta.get('bugs_specified','?')} | "
          f"{meta.get('final_tests_green','?')} | {meta.get('agent_stopped_itself','?')} |")
    w("")

    # threshold fractions
    n = len(all_dts)
    f5 = sum(1 for d in all_dts if d > 5) / n
    f15 = sum(1 for d in all_dts if d > 15) / n
    f30 = sum(1 for d in all_dts if d > 30) / n
    w("## Threshold fractions (pooled)")
    w("")
    w(f"| dt > 5 s | dt > 15 s | dt > 30 s |")
    w(f"|---|---|---|")
    w(f"| {100*f5:.1f}% | {100*f15:.1f}% | {100*f30:.1f}% |")
    w("")

    # lag-1 autocorrelation
    w("## Heavy-step clustering: lag-1 autocorrelation of dt")
    w("")
    w("| run | lag-1 autocorr |")
    w("|---|---|")
    pooled_within = []
    for name, (recs, dts) in per_run.items():
        ac = lag1_autocorr(dts)
        w(f"| {name} | {ac:.3f} |" if ac is not None else f"| {name} | n/a |")
        if ac is not None:
            pooled_within.append(ac)
    if pooled_within:
        w(f"| mean of per-run values | {statistics.mean(pooled_within):.3f} |")
    w("")
    w("Positive values = heavy (slow) steps cluster together; ~0 = no "
      "clustering. Per-run values avoid the spurious correlation that pooling "
      "across runs would introduce.")
    w("")

    # per-tool breakdown
    w("## dt by tool type (pooled)")
    w("")
    by_tool = {}
    for name, (recs, dts) in per_run.items():
        # dt[i] belongs to the action at index i+1 (the cycle that produced it)
        for i, dt in enumerate(dts):
            tool = recs[i + 1]["tool_name"]
            by_tool.setdefault(tool, []).append(dt)
    w("| tool | n | min | median | p90 | max |")
    w("|---|---|---|---|---|---|")
    for tool in sorted(by_tool, key=lambda t: -statistics.median(by_tool[t])):
        s = sorted(by_tool[tool])
        w(f"| {tool} | {len(s)} | {s[0]:.2f} | {pct(s,0.5):.2f} | "
          f"{pct(s,0.9):.2f} | {s[-1]:.2f} |")
    w("")

    # comparison with the Phase 4b toy probe
    w("## Comparison with the Phase 4b toy probe")
    w("")
    if PROBE_RAW.exists():
        probe = json.loads(PROBE_RAW.read_text(encoding="utf-8"))
        pdts = sorted(x for t in probe["tasks"] for x in t["action_dts"])
        w("| source | n | median | p90 | max |")
        w("|---|---|---|---|---|")
        w(f"| Phase 4b toy probe ({probe['model']}, 3-file toy packages) | "
          f"{len(pdts)} | {pct(pdts,0.5):.2f} | {pct(pdts,0.9):.2f} | {pdts[-1]:.2f} |")
        w(f"| Phase 6 real repos (this report) | {pooled['n']} | "
          f"{pooled['median']:.2f} | {pooled['p90']:.2f} | {pooled['max']:.2f} |")
        w("")
        ratio_med = pooled["median"] / pct(pdts, 0.5)
        ratio_max = pooled["max"] / pdts[-1]
        w(f"Real-repo medians are {ratio_med:.1f}x the toy probe's; maxima are "
          f"{ratio_max:.1f}x. The gap is the cost of real repos: bigger files "
          f"to read, larger growing contexts (longer prefill), and genuine test "
          f"suites (more-itertools's full run is the heavy tail). This "
          f"confirms the Phase 4b caveat that toy times were a lower bound.")
    else:
        w("(toy probe raw data not found)")
    w("")

    w("## Notes")
    w("")
    w("- Thought text IS present in these traces (the loop captures assistant "
      "rationale before each call). Hook-captured Claude Code sessions have "
      "empty thoughts (hooks do not expose reasoning text), so A9/text "
      "features apply to runner traces but will NOT apply to hook traces -- "
      "documented in convert.py.")
    w("- dt distributions reflect this harness (mini model, US endpoint, "
      "local execution); absolute values shift with model/network, but the "
      "shape (heavy-tailed, tool-dependent) is the transferable observation.")

    report = "\n".join(out)
    (RUNS_DIR / "TIMING_REPORT.md").write_text(report, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)
    print(f"\nsaved: {RUNS_DIR / 'TIMING_REPORT.md'}")


if __name__ == "__main__":
    main()
