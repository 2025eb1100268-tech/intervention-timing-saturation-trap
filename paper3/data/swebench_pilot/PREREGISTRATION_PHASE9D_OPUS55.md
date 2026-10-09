# Pre-registration: Phase 9D — held-out Opus 5.5 arm

Committed BEFORE the first run. This commit contains **no result artefacts**.

One throwaway calibration call preceded it and is **excluded from every analysis
below**: a single subagent launched with the Agent tool's `opus` alias, no tools,
no open measurement window, asked only to state its model. It answered
`Opus 5.5 / claude-opus-5-5`, and its transcript
(`subagents/agent-a15d32bba5d88cde9.jsonl`) records `claude-opus-5-5` on every
assistant message. It validated alias resolution; it is not data.

---

## 0. What this is, and what it is not

**It is a held-out test of the paper's one remaining empirical measurement.**
Section 3.4 reports that the evidence floor binds on current agent sessions:
under the execution-only definition, 15 of 16 Phase-9C sessions carry fewer than
the 5 qualifying observations the reference accumulator needs. Opus 5.5 did not
exist when that analysis was frozen. Its sessions are therefore a prospective
test of a prediction derived from the frozen arithmetic, not a re-measurement
tuned to it.

**It is not a model comparison.** Phase 9C's H16 could not distinguish Opus 5
from Fable 5.1 at n = 8 specs (exact Wilcoxon p = 0.84), and every model claim
from the pilot was withdrawn. Adding a third model at the same n does not create
the power H16 lacked. **No cadence, action-count or behavioural comparison
between Opus 5.5 and either earlier model will be claimed**, whichever way the
numbers fall. They are reported descriptively.

**It is not pooled.** The 16 Phase-9C runs remain the paper's primary
measurement and are frozen. Opus 5.5 is reported as a separate held-out arm.
Every frozen 9C analysis filters on `model in ("opus", "fable")`, so the new
label cannot enter them; regeneration of the frozen reports after these runs
must produce no diff, and that is checked.

## 1. Design

| | |
|---|---|
| specs | the 8 frozen Phase-9C specs: S02, S03, S05, S06, S07, S08, S09, S10 (`phase9c_specs.json`) |
| runs | 8 — one per spec, `repeat = 1`, as in 9C |
| protocol | `clean-git-orphan-root-v2`, `scripts/phase_c2_subagent.py`, **unchanged** |
| goal | pasted verbatim from `prepare` |
| launch | exactly one subagent per window; no other tool call between `prepare` and `harvest` |
| model | Opus 5.5 (`claude-opus-5-5`), via the Agent tool's `opus` alias |
| label | **`opus55`** — NOT `opus`, which would overwrite the frozen 9C Opus 5 files |
| order | spec order S02 → S10 |

**Model identity is verified per run from the record, not from self-report:**
after each `harvest`, the subagent's transcript is read and every assistant
message must record `claude-opus-5-5`. A run that fails this is discarded,
logged, and re-run.

## 2. Declared deviations from Phase 9C

Stated now so that none can be discovered after the fact and used to explain a
result away.

1. **Model** — the point of the exercise.
2. **Effort.** 9C subagents inherited effort from an Opus 5 session
   (`effort: override-from-opus5-session` in every 9C run file). These inherit
   from an Opus 5.5 session at a different setting. Recorded as
   `override-from-opus55-session`. **Not matched, magnitude unknown.** It can
   plausibly move cadence and session length; this is one more reason no
   comparison is claimed.
3. **Agent type.** The Agent tool's default (`general-purpose`). 9C's run files
   do not record the agent type, so equality with 9C is assumed, not verified.
4. **Date.** Runs on 2026-10-05, roughly three and a half weeks after 9C.

## 3. Definitions (frozen; the analysis script implements these mechanically)

- **Qualifying observation, primary (`E_X`, execution-only):** a hook record
  whose `tool_name` is `Bash` or `PowerShell` and whose `error_indicator` is
  true — identical to `scripts/budget_ceiling_9c.py` (`SHELL`, `DEF = "X"`).
- Also reported: `E_O` (the frozen observer's `has_error()` on the replay
  trajectory) and `E_H` (hook `error_indicator` on every tool), as in 9C.
- **Reference accumulator** I1: step 0.15, threshold 0.7, `N_min = 5`.
- **CUSUM** I2: `g = max(0, g + e − 0.1)`, fire at `g ≥ 1.0`, `N_min = 2`.
- **Feasible** ⇔ `E_X ≥ 5`.
- Direct subsampling at r ∈ {1, 2, 3, 4, 5, 10}, averaged over every offset, for
  I1 wall-clock, I1 no-decay and I2 — the `budget_ceiling_9c.py` procedure.

## 4. Hypotheses

### H19 (primary, confirmatory) — the floor binds on a held-out frontier model

> At most 2 of the 8 Opus 5.5 sessions carry `E_X ≥ 5`, so the 5-event
> reference accumulator cannot fire on at least 6 of 8 even at full budget.

- **SUPPORTED** if ≤ 2 of 8 sessions have `E_X ≥ 5`.
- **FALSIFIED** if ≥ 3 of 8 do.

**Why the line is at three.** At Phase 9C's pooled feasible rate (1/16),
P(≥ 3 of 8) = **0.011**. At the 9C Opus 5 arm's own rate (1/8) it is **0.067**.
So a falsification would be strong evidence against the pooled rate but only
suggestive against the Opus-5-arm rate, and will be reported with both figures.

**What H19 cannot show.** Support at n = 8 is not evidence that Opus 5.5 behaves
like the earlier models. It is evidence that the floor result was not an
artefact of two models from one generation.

### H20 (secondary, confirmatory) — the paper's design advice recovers coverage

Section 3.6 recommends a statistic with a smaller floor. On 9C a CUSUM at
`N_min = 2` fired on 6 sessions against 1 for the 5-event accumulator.

> At full budget (r = 1), I2 fires on strictly more Opus 5.5 sessions than I1
> with no decay (the best case for any leaky integrator).

- **SUPPORTED** if count(I2 fires) > count(I1 no-decay fires).
- **FALSIFIED** if count(I2 fires) ≤ count(I1 no-decay fires).

This can genuinely fail: if Opus 5.5 sessions carry almost no failures, both
monitors are silent and lowering the floor recovers nothing — which would mean
the design advice does not transfer to this model, and the paper must say so.

### Descriptive only — declared now, no confirmatory claim

Per session: `n`, `E_X`, `E_O`, `E_H`, median Δt, tools used, git recon calls,
final tests green. Fire rates at every r for all three monitors. Median session
length and `E_X` across the arm.

## 5. Run rules

- A run whose clean-git assertions fail is aborted by the harness and re-run;
  the abort is logged.
- **A run whose target tests are red at harvest is kept.** No run is repeated
  to obtain a different outcome.
- A run whose transcript records any model other than `claude-opus-5-5` is
  discarded and re-run, logged.
- If a subagent hits a usage or rate limit mid-run, that run is discarded as
  incomplete and re-run from `prepare`, logged; a partial session is not data.

## Amendment 1 — committed before any data

**An aborted window.** The first S02 window was opened at
2026-10-05T02:03:05+05:30 and closed by `harvest` **before any subagent was
launched**: 0 actions captured, repo restored to its pinned commit, and the
empty output files deleted. Nothing was measured.

**Why.** `prepare` prints only the task goal, which names files by relative
path. A subagent starts in the project root, not the repository. Whether 9C
pasted the goal alone or wrapped it decides whether agents must spend actions
discovering the repo, which moves `n` and the chance of a failed command — both
of which bear on H19 — so it could not be guessed. It could not be checked
inside the open window either, because any operator tool call there is logged as
an agent action.

**What the record shows.** The PostToolUse hook logs operator `Agent` calls
with their full input. Every one of the 16 Phase-9C windows contains exactly one
such call, so all 16 launch prompts are recoverable unambiguously. They show
that 9C used a **wrapper**, not the bare goal: the repository path, the
`PYTHONPATH` setting, the exact pytest command, the goal, and a closing
instruction to work step by step. The Opus 5 and Fable 5.1 arms received
**identical** text for every spec. All 16 used `subagent_type:
"general-purpose"` and `run_in_background: false`. The eight prompts are saved
verbatim as `data/live_runs/phase_c2/_9c_launch_prompts.json`.

**Procedure from here.** Each 9D run launches with the recovered 9C prompt for
its spec, **verbatim**, with the same `description` and `subagent_type`, in the
foreground, with `model: "opus"` (verified to resolve to `claude-opus-5-5`).

**Effect on §2.** Deviation 3 (agent type) is **resolved**: verified equal to
9C, not assumed. Deviations 1, 2 and 4 stand.

## Amendment 2 — after run 1 of 8, before runs 2–8

**What was found.** Reconciling run 1 (S02) against its subagent transcript:
the transcript records 10 tool calls, the hook captured 9, and the one missing
was the **only call with `is_error = True`** — the first pytest run, exit
code 1. Claude Code fires `PostToolUse` only after a tool call succeeds.

**It applies to the frozen 9C data.** All 16 Phase-9C transcripts survive and
map one-to-one onto their windows (`_9c_transcript_map.json`). Across them the
hook missed 6 calls, **every one of them a failed call**. The gap is
model-dependent: Opus 5 lost none (it piped pytest output, so its pipelines
exited 0); Fable 5.1 lost all six (it did not). `HOOK_COVERAGE_AUDIT.md`
recomputes every session with the hook's own detector applied to every call.

**Consequence for H19 and H20.** The paper's execution-only definition counts
shell commands that returned an error — exactly the class the hook cannot see.
Opus 5.5 on S02 let its failing command exit non-zero, so the hook-based count
is biased **toward supporting H19**. Scoring is therefore amended:

- **H19 and H20 are each scored twice** — on the hook count, exactly as
  pre-registered, and on the **transcript count**: the same execution-only
  definition, the same detector (`hook_logger._detect_error`), the same
  thresholds, applied to every call the agent made.
- **The transcript score governs interpretation**, because the hook is now
  known to be blind to the construct. If the two disagree, both are reported,
  and the disagreement is itself reported as a finding about the instrument.
- **Thresholds are unchanged.**

**Disclosure.** S02's values were seen before this amendment: `E_X` = 0 by
hook, 1 by transcript. Both are far below the threshold of 5.

**The hook is not modified during 9D**, so the instrument stays identical to
9C's; the transcript supplies the corrected count. Registering the logger for
`PostToolUseFailure` as well is recommended for any future collection, outside
this arm.

## 6. Frozen before running

The analysis is mechanical over the definitions in §3. The script that computes
it is written after the runs, because it must read their files, but it may only
call the frozen functions and constants named above. Any departure from §3 is
reported as a deviation, not adopted silently.
