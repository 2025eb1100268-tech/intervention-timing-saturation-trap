# Live-run target repositories — pinned provenance

The Phase-6 live runs (`runA`–`runE`) operated on real clones of three
open-source Python repositories with deterministically injected bugs (exact
old→new text replacements; see `heart_instrument/agent_runner.py`).

The clones themselves are **not** committed: they carry their own `.git`
directories (~25 MB total) and are upstream code we do not own. The exact
commits are pinned here instead, so any run is reproducible by re-cloning at
the recorded SHA.

Recorded 2026-09-08, read directly from the working clones that produced the
Phase-6 timing data (`git -C <dir> rev-parse HEAD`).

| Local path | Upstream | Commit SHA | `git describe` |
|---|---|---|---|
| `data/live_runs/repos/more-itertools` | https://github.com/more-itertools/more-itertools | `5692cd838d2b0b55ff46c5f9934b79a0b069027e` | `5692cd8` |
| `data/live_runs/repos/sortedcontainers` | https://github.com/grantjenks/python-sortedcontainers | `3ac358631f58c1347f1d6d2d92784117db0f38ed` | `3ac3586` |
| `data/live_runs/repos/toolz` | https://github.com/pytoolz/toolz | `568c2b8393973cd172a466546c9d95779c452438` | `1.1.0` |

To restore:

```bash
mkdir -p data/live_runs/repos && cd data/live_runs/repos
git clone https://github.com/more-itertools/more-itertools        && git -C more-itertools   checkout 5692cd838d2b0b55ff46c5f9934b79a0b069027e
git clone https://github.com/grantjenks/python-sortedcontainers sortedcontainers && git -C sortedcontainers checkout 3ac358631f58c1347f1d6d2d92784117db0f38ed
git clone https://github.com/pytoolz/toolz                        && git -C toolz            checkout 568c2b8393973cd172a466546c9d95779c452438
```

Bug-injection specs are literal `old`→`new` string replacements in
`heart_instrument/agent_runner.py::RUNS`, applied only when `old` occurs
**exactly once** in the target file; skipped injections are recorded in each
run's `run_meta.json`. Phase C (Paper 3) reuses these same three repositories,
the same SHAs, and the same injection specs unchanged.
