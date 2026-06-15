# Live-run timing report (Phase 6, Task 4)

Real wall-clock inter-action times from instrumented agentic debugging runs on real cloned open-source repos (sortedcontainers, toolz, more-itertools) with deterministically injected bugs. Harness: scriptable tool-use loop (gpt-5.4-mini, one tool call per action), native PostToolUse-style logging -- the Claude Code CLI is not invocable in this environment, so the task's sanctioned fallback harness was used; the hook (heart_instrument/hook_logger.py) is installed and produces the identical log format for the user's own Claude Code sessions. dt = gap between consecutive post-observation timestamps = one full thought->tool->observation cycle.

## Per-run distributions (seconds)

| run | n dts | min | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|---|
| runA (sortedcontainers) | 6 | 1.37 | 1.50 | 1.78 | 1.85 | 1.90 | 1.94 |
| runB (sortedcontainers) | 13 | 1.07 | 1.22 | 1.46 | 1.81 | 2.14 | 2.59 |
| runC (toolz) | 8 | 1.16 | 1.32 | 1.48 | 1.62 | 1.75 | 1.99 |
| runD (toolz) | 7 | 1.11 | 1.25 | 1.65 | 1.96 | 2.38 | 2.76 |
| runE (more-itertools) | 31 | 0.97 | 1.23 | 1.53 | 1.93 | 3.57 | 15.87 |
| **pooled** | 65 | 0.97 | 1.25 | 1.53 | 1.86 | 2.33 | 15.87 |

### Run outcomes

| run | repo | actions | bugs applied | tests green | self-stopped |
|---|---|---|---|---|---|
| runA | sortedcontainers | 7 | 2/3 | True | True |
| runB | sortedcontainers | 14 | 3/3 | True | True |
| runC | toolz | 9 | 3/3 | True | True |
| runD | toolz | 8 | 3/3 | True | True |
| runE | more-itertools | 32 | 2/2 | True | True |

## Threshold fractions (pooled)

| dt > 5 s | dt > 15 s | dt > 30 s |
|---|---|---|
| 3.1% | 3.1% | 0.0% |

## Heavy-step clustering: lag-1 autocorrelation of dt

| run | lag-1 autocorr |
|---|---|
| runA | 0.342 |
| runB | -0.005 |
| runC | -0.051 |
| runD | -0.222 |
| runE | 0.101 |
| mean of per-run values | 0.033 |

Positive values = heavy (slow) steps cluster together; ~0 = no clustering. Per-run values avoid the spurious correlation that pooling across runs would introduce.

## dt by tool type (pooled)

| tool | n | min | median | p90 | max |
|---|---|---|---|---|---|
| run_pytest | 6 | 1.84 | 2.14 | 15.46 | 15.87 |
| edit_file | 22 | 1.06 | 1.75 | 2.56 | 3.61 |
| grep_search | 5 | 1.36 | 1.53 | 1.85 | 1.99 |
| read_file | 32 | 0.97 | 1.34 | 1.79 | 3.57 |

## Comparison with the Phase 4b toy probe

| source | n | median | p90 | max |
|---|---|---|---|---|
| Phase 4b toy probe (gpt-5.4-mini, 3-file toy packages) | 20 | 1.10 | 2.32 | 2.56 |
| Phase 6 real repos (this report) | 65 | 1.53 | 2.33 | 15.87 |

Real-repo medians are 1.4x the toy probe's; maxima are 6.2x. The gap is the cost of real repos: bigger files to read, larger growing contexts (longer prefill), and genuine test suites (more-itertools's full run is the heavy tail). This confirms the Phase 4b caveat that toy times were a lower bound.

## Notes

- Thought text IS present in these traces (the loop captures assistant rationale before each call). Hook-captured Claude Code sessions have empty thoughts (hooks do not expose reasoning text), so A9/text features apply to runner traces but will NOT apply to hook traces -- documented in convert.py.
- dt distributions reflect this harness (mini model, US endpoint, local execution); absolute values shift with model/network, but the shape (heavy-tailed, tool-dependent) is the transferable observation.