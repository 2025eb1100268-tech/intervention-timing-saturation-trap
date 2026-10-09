# Pre-registration addendum: Phase C as run (subagent harness)

Committed BEFORE any Phase-C data is collected. Amends
`PREREGISTRATION_PHASE9.md` §4 and `PHASE_C_PLAN.md`. The instrumentation probe
that established the mechanics below (four `echo` commands) is not data and is
excluded from every analysis.

---

## 1. Why the pre-registered C-main arm is not the arm being run

`PREREGISTRATION_PHASE9.md` §4 committed to a **bridge arm**: Opus 5 inside the
frozen `agent_runner.py` scriptable loop, which is the only configuration
comparable to Paper 2's `gpt-5.4-mini` numbers. That arm requires an Anthropic
API key.

**There is no API credential in this environment** — `ANTHROPIC_API_KEY` and
`ANTHROPIC_AUTH_TOKEN` are unset, the `ant` CLI is not installed, and the
installed SDK is `anthropic` 0.75.0, which predates `output_config`/`effort` and
adaptive thinking. The `claude` CLI is also not on PATH, exactly as it was for
Paper 2.

So C-main **cannot be run**, and is deferred, not silently substituted.

## 2. What is being run instead: C-sub (new arm)

**C-sub** — Claude Code **subagents** as the coding agents, instrumented by the
already-installed `PostToolUse` hook (`heart_instrument/hook_logger.py`).

Established empirically by the probe, and recorded here as the harness's
measurement properties:

- Subagent tool calls **do** fire `PostToolUse`.
- They are written to the **parent session's** log with the **parent's**
  `session_id`, interleaved with the operator's own calls. There is no field
  distinguishing them.
- Attribution is therefore **by time window**: wall-clock is recorded
  immediately before launching an agent and immediately after it returns, and
  only records strictly inside that window are attributed to it. The terminal
  `tool_name == "Agent"` record is excluded.
- This is only sound if **no other tool call occurs while an agent runs**.
  Agents are therefore run **one at a time, in the foreground**, and the
  operator issues no tool calls in between. Any window containing an
  unattributable record is **discarded, not repaired**.

### What C-sub preserves from the pre-registered design

- **The timestamp point is identical to Paper 2's**: `ts` is taken by the
  `PostToolUse` hook after the tool's observation is produced, so inter-record
  dt is one full reason → tool → observation cycle. This is the single most
  important comparability property and it survives.
- Same three repositories at the SHAs pinned in
  `data/live_runs/REPO_PROVENANCE.md`, same injected bugs (the exact
  old→new replacements in the frozen `agent_runner.py::RUNS`), same task goals.

### What C-sub changes, and therefore what it cannot support

| | Paper 2 / C-main | C-sub |
|---|---|---|
| harness | scriptable one-tool-call loop | Claude Code subagent |
| tool surface | 5 bespoke tools | full Claude Code toolset (Read/Edit/Bash/Grep/Glob/…) |
| parallel tool calls | disabled | **not controllable** |
| reasoning effort | settable, recordable | **not settable** |
| extended-thinking status | readable from `usage` | **not exposed to hooks** (`thought` is always `""`) |
| token usage | per action | not exposed to hooks |

Consequences, committed now:

- **H10 is NOT scored on C-sub.** Its pre-registered comparison is against
  Paper 2's pooled dt within a matched harness, and C-sub is not that harness.
  C-sub's absolute cadence numbers are reported as descriptive, and any
  comparison to 1.53 s / 2.33 s is explicitly labelled cross-harness.
- **C-effort is dropped** for this round — effort is not settable on subagents.
  Recorded as not-run, not as a null result.
- **H11 and H12 are scored on C-sub**, because both are *within-run* tests and
  do not depend on cross-harness comparability. The n ≥ 30 power requirement and
  the exclusion-count reporting from §4 carry over unchanged.
- **H13 is scored on C-sub**, since it is a statement about whether observed
  gaps reach the 87.74 s drain threshold, which is harness-relative by nature.

### The model contrast is the point, and it is internally controlled

Opus 5 and Fable 5.1 arms run in the **same session, same machine, same repos,
same bugs, same harness, same attribution method**, differing only in the model
driving the agent. That contrast is clean even though neither arm is comparable
to Paper 2. It is the comparison the paper actually needs: *does model choice
move the inter-action interval enough to move a monitor's regime?*

## 3. H15 — new hypothesis, derived from Phase B, registered before any run

Phase B's exploratory finding was that **evidence starvation**, not calibration,
dominates at realistic monitoring budgets: reaching the I1 threshold needs five
accumulating error observations, and a 1-in-r budget on an n-action trace leaves
about n/r observations. The starvation floor therefore scales with **trace
length**.

This yields a prediction that runs against the optimistic reading of frontier
progress:

> **H15.** Opus 5 completes the same injected-bug tasks in **fewer actions**
> than Paper 2's `gpt-5.4-mini` (which took 7, 14, 9, 8 and 32 actions;
> median 9). A more capable agent that solves the task in fewer steps gives any
> stateful monitor **fewer observations to accumulate over**, pushing the
> evidence-starvation floor to a *smaller* budget r. Monitoring gets harder, not
> easier, as agents improve.

- **Scored on** the per-run action count of the C-sub Opus 5 arm against the
  Paper-2 counts for the same five run specs, paired by spec.
- **Supported if** the paired median action count is below the Paper-2 median
  for the same specs.
- **Falsified if** the paired median is greater than or equal to it.
- Because C-sub's tool surface is richer than Paper 2's five-tool schema, a
  reduction in action count is **partly a harness effect and partly a model
  effect, and the two cannot be separated in this arm.** This confound is stated
  now, before the result, and will be stated wherever H15 is reported. H15 is
  therefore registered as **suggestive, not confirmatory**, and the clean test
  of it requires the deferred C-main arm.

### Derived quantities reported per run (definitions fixed now)

- `r_starv = n_actions / 5` — the budget at which fewer than five observations
  remain, below which an accumulator with step 0.15 and threshold 0.7 cannot
  reach threshold at all.
- `r_cliff = delta_star / median_dt`, with `delta_star` from the Phase E design
  rule `-(H/ln2)·ln(1 - a·p/theta)` using that run's own measured error rate p.
- The binding constraint is `min(r_starv, r_cliff)`, and which of the two binds
  is reported per run.

## 4. Analysis conventions (fixed now)

- dt is the difference between consecutive `ts` values inside an attributed
  window. The first action of a window has no preceding gap and contributes no
  dt, matching every prior phase.
- Runs are reported individually with full within-run distributions — median,
  p90, IQR, max, and the ordered sequence — never the median alone.
- H11's dip test and the BIC fallback, H12's band-crossing definition, and
  H13's drain threshold are all exactly as specified in
  `PREREGISTRATION_PHASE9.md` §4. Nothing is redefined here.
- Repos are restored with `git checkout -- .` after every run; the injection log
  from each run records which bug specs applied.
