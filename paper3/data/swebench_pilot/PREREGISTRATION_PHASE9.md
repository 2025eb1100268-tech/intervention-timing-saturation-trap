# Pre-registration: Phase 9 — Paper 3 (monitor calibration as a control property)

Committed BEFORE any Phase-9 result file exists. Written to the
`phase9-preregistration` branch; the commit that adds this file contains **no
result artefacts**, so the commit graph — not filesystem mtimes — establishes
that H10–H14 preceded every number they are scored against.

Framing: Paper 3 is addressed to the AI-control literature. HEART is one
methods sentence. The load-bearing instrument is **I1**, the wall-clock leaky
accumulator defined in `PREREGISTRATION_PHASE8.md` — no engine, no emotions,
no rules, five lines of arithmetic. The reviewer objection being answered is
*"you dissected a monitor class whose only demonstrated member is your own."*
Every phase below exists to answer that objection, and the confirmatory claims
are scored on I1 and I2 first, with the HEART triggers (A6, T3) reported as a
second, concrete member of the class rather than as the subject.

Engine, adapter, observer rules, triggers, thresholds and all instrument
constants are **frozen** at the Phase 1–8 values. No constant is tuned in
Phase 9. Anything specified after a result is seen is labelled EXPLORATORY at
the point it appears, per Phases 7–8.

---

## 0. Facts established BEFORE this commitment (and used to set thresholds)

These are stated up front so that no threshold below can be read as blind. All
were computed from the frozen Phase-1–8 artefacts on 2026-09-08, before this
file was written, and are reproducible by
`python scripts/observer_capability_audit.py`. They are properties of the
existing corpus and of the frozen code — none of them is a Phase-9 result.

**0.1 The observer cannot emit a de-escalating signal.** Across all 20
trajectories, 714 actions and 765 emitted signals, there are **0 negative
deltas**. All eight rules in `heart_adapters/claude_code/signals.py` return
non-negative deltas by construction.

**0.2 Every indirect attenuation path is dead on this corpus.** Frustration's
only antagonist in `CONFLICTS` is `("hope","frustration"): -0.50`. No rule
emits `hope`; measured `max(hope) = 0.100` = `BASELINE`, over every action of
every trajectory. `_rebalance_conflicts_v2` requires both members of a
conflicting pair above 0.55 and therefore never damps frustration.
`_normalize_energy(max_sum=6.0)` never activates: measured max vector sum
**4.827 < 6.0**. `load_emotion_cores` returns `{}`, so `_apply_core_layer` is
a no-op. The realized channel census is
`frustration 359, fear 202, confusion 166, happiness 22, pride 14, curiosity 2,
empathy 0`; none of the three positive-valence channels opposes frustration in
`CONFLICTS`.

**0.3 Consequence, verified empirically.** Frustration is **strictly
non-decreasing** across an action step at dt=0: **0 decreases in 694
within-trajectory steps**. The sole mechanism that lowers frustration in this
monitor is the wall-clock decay term. This is a structural property of the
monitor, not a property of the agents observed.

**0.4 The observer's metacognition detector is sign-inverted and nearly
silent.** `ActionEvent.has_hedge_words()` is the only rule input that targets
reframing ("let me reconsider", "on second thought", "actually wait"). It
fires on **2 of 714 actions (0.3%)**. Because `task_metadata` from the
aime-coder parser never carries `files_in_scope`, `rule_hedge_words` always
takes its `len(files_in_scope) < 3` branch and returns exactly
`[("confusion", 0.08)]`. Detecting explicit metacognition therefore
**increases** the negative-accumulation sum. Surface reframing markers that
the observer does *not* consume (`text_features._CYCLE_RE`) are present on
**43 of 714 actions (6.0%)**; any recovery-adjacent surface marker on **49
(6.9%)**.

**0.5 Drain arithmetic (restated from PHASE7 §Analytic expectation, and
extended).** From the frustration clamp, `0.1 + 0.9·exp(-ln2/150·T) < 0.7`
gives **T > 87.74 s** of signal-free elapsed time. At Paper 2's pooled median
cadence 1.53 s that is **57.3 consecutive signal-free actions**; at p90 2.33 s,
37.7; at 5 s, 17.5; at 15 s, 5.8. For I1 (no baseline term) the equivalent is
**77.19 s**, i.e. 50.4 actions at 1.53 s. On the existing corpus the longest
run of consecutive actions carrying no frustration signal is **max 10, median
4.5**, and only **1 of 20** trajectories is even 57 actions long in total.

**0.6 Paper 2's cadence baseline is not an Anthropic baseline.** Per
`data/live_runs/TIMING_REPORT.md` and `heart_instrument/agent_runner.py`, the
1.53 s / 2.33 s figures come from a **scriptable single-tool-call loop driven
by `gpt-5.4-mini`**, used because the Claude Code CLI was not invocable in
that environment. They are not Claude Code numbers and not Anthropic-model
numbers. This governs the Phase C design in §4 and is a declared limitation of
H10.

---

## 1. Phase A — observer sensitivity calibration (BLOCKING)

Nothing downstream is interpretable without it, and it **gates Phase C and
Phase D**. Full protocol, strata and sampling frame:
`PHASE_A_LABELING_PROTOCOL.md`, committed in the same commit as this file.

§0.1–0.4 already establish analytically that the observer's sensitivity to
recovery **on the frustration channel is exactly zero, by construction**.
Phase A is therefore not a search for that number. It measures the three
things the analysis cannot settle:

- **A-i** Do human labellers agree that recovery events occur in these traces
  at all, and at what base rate? (If the base rate is ~0, Phase D has no
  signal to find and that is the finding.)
- **A-ii** Does the observer emit *any* distinguishable response at
  human-labelled recovery events — of any sign, on any channel? Scored as
  sensitivity and precision of "observer emits a non-empty `signals_applied`"
  and of "observer emits its hedge-marker" against the human labels.
- **A-iii** Is observer **silence** informative? I.e. is `signals_applied == []`
  enriched at recovery events relative to base rate? Silence is the only
  channel through which the frozen monitor can drain, so this is the only
  route by which recovery could ever reach the state variable.

**Pre-registered Phase A gate.** Phase D proceeds as a confirmatory analysis
only if (a) the human recovery base rate is ≥ 3% of labelled actions, **and**
(b) two independent labellers reach Cohen's κ ≥ 0.40 on the binary recovery
label. If (a) fails, Phase D is dropped and reported as "no recovery events to
detect." If (b) fails, Phase D is reported as EXPLORATORY only, and the κ
becomes a Paper-3 result in its own right, continuous with Paper 1's
inter-rater finding. κ ≥ 0.40 is chosen as the same "moderate agreement"
Landis–Koch boundary Paper 1 used; it is not a new threshold.

**Falsification / finding clause.** If A-ii returns sensitivity below 0.20 at
the observer's own hedge-marker, the honest class-level statement in Paper 3
is that *this monitor's recovery sensitivity is not merely low but structurally
zero on the channel that matters, and near-zero on every channel*, and every
Phase-D comparison is framed as a bound, not a measurement. Given §0.4 this is
the expected outcome; it is registered as the expectation so that it cannot
later be presented as a discovery.

---

## 2. Phase B — monitoring budget × cadence

No new agent runs. Runs entirely on the 20 existing frozen error streams
(`has_error` from `fullstate_dt0_<id>.json`). Script:
`scripts/budget_cadence_sweep.py`, committed with this file and unrun at
commit time.

**Sweep.** `r ∈ {1, 2, 5, 10, 20, 50}` crossed with the frozen dt grid
`{0, 1, 5, 15, 30, 60, 150, 300, 600}` s, plus two additional
**measured-cadence points** `dt ∈ {1.53, 2.33}` s (Paper 2's pooled median and
p90). The two extra points are declared here, before running, and are
therefore confirmatory, not exploratory; they exist because the r=10 → ~15 s
claim cannot be evaluated on a grid that omits the measured cadence.

**Sampling phase.** Sampling 1-in-r has r offsets. For the cheap instruments
(I1, I2) **all r offsets** are evaluated. For the engine instruments (A6, T3)
offsets are `o ∈ {0 … min(r,5)-1}`. Results are reported as median across
offsets with min–max, never as a single offset.

**Conditions** (all three specified now; B1 primary, B2 and B3 secondary and
confirmatory, none exploratory):

- **B1 sampled observation** (primary; the Hua-et-al. cost model). The monitor
  ingests only every r-th action. Elapsed time between successive observations
  is `r·dt`. Both evidence and decay change.
- **B2 sampled evaluation** (secondary). The monitor ingests every action with
  per-action `dt`, but triggers are evaluated only on every r-th action.
  Evidence and decay are unchanged; only the checking frequency changes.
  B2 exists to decompose B1 into *evidence loss* vs *decay stretch*.
- **B3 sampled observation, sample-time calibrated** (secondary; the
  constructive control). As B1, but the decay applied per observation is
  `exp(-λ·dt)` rather than `exp(-λ·r·dt)` — i.e. the monitor is recalibrated to
  its own observation clock. This changes the calibration *basis*, which is the
  paper's thesis; it tunes no constant. B3 is the remedy Phase E packages.

**Instruments.** A6 `sustained_frustration`, I1 level, I1 edge, I2 CUSUM, T3
`saturation_entry` net (through `CooldownGuidelines`, refractory 5). All
constants exactly as Phase 7/8. A6 and T3 run under B1 only.

**Regime metric.** Frozen from Phase 5/8: post-first-crossing persistence
< 50% defines the critical grid point; critical interval = (previous grid
point, that dt].

### Hypotheses

- **H14a (dt-invariance survives budget).** For every r and every trajectory,
  I2's fire pattern (set of firing observation indices) is identical across
  all 9 grid dt values. *Falsified by any counterexample — and a counterexample
  is an implementation bug, not a discovery, since sample-time CUSUM cannot
  read a clock. Debug the code, not the hypothesis.*
- **H14b (budget degrades I2 quantitatively, not qualitatively).** I2's fire
  count is **non-increasing in r** for every trajectory, and I2 exhibits no
  critical interval at any r. *Falsified if I2's fire count increases with r on
  any trajectory, or if I2 shows a persistence collapse at any (r, dt).*
- **H14c (the cliff is exactly a change of variable).** For every
  (trajectory, r, dt, offset), I1 under B1 is **bitwise identical** to I1 at
  `dt' = r·dt` evaluated on the offset-subsampled stream. *This is an identity,
  not an empirical claim; failure is a bug.* Consequently the I1 critical
  interval under budget r is the r=1 interval divided by r, to within grid
  resolution.
- **H14d (regime flip at realistic budget).** At `dt = 1.53 s`, the majority
  (≥ 11/20) of trajectories that sit in the alarm regime at r=1 leave it by
  r=10, where "leave" means post-first-crossing persistence drops below 50% or
  the trajectory ceases to cross 0.7 at all. *Falsified if fewer than 11/20
  change regime between r=1 and r=10 at dt=1.53 s.*
- **H14e (A6 and T3 track I1 and stay bounded).** A6 reproduces the I1 cliff
  under B1 (its critical interval shifts by the same 1/r factor, to grid
  resolution), and T3 net fire count remains ≤ 3 in every
  (trajectory × r × dt × offset) cell. *T3 exceeding 3 anywhere falsifies the
  "edge triggers are cadence-robust" claim carried from Phases 7–8 and must be
  reported as such.*

**Note on the ambiguity in the originally-drafted H14.** The scoping brief
worded this as "I2 CUSUM stays exactly invariant across all r." That wording is
ambiguous between *invariant across dt at each r* (true by construction, and
registered here as H14a) and *invariant across r* (necessarily **false** — a
monitor that only sees every r-th action sees fewer errors, so its CUSUM must
fire later or not at all, which is exactly H14b). The ambiguity is resolved
here, before any Phase-B result exists, in favour of the decomposition above.
Recording the resolution now is the point: the paper-relevant contrast is that
**budget moves I1 across a regime boundary while it moves I2 only along a
sensitivity axis**, and that contrast would be destroyed by quietly reading
H14 the charitable way after seeing the output.

**Degeneracy.** Trajectory lengths are 25–59 actions (median 32.5). At r=20
and r=50 most trajectories yield ≤ 2 and ≤ 1 observations respectively. Per
Phase-8 discipline, degenerate cells are **reported, not fixed**, and no
second parameterization is run. That budget r=50 leaves a 30-action trajectory
effectively unmonitored is itself a reportable property of cost-constrained
monitoring at agentic trace lengths.

---

## 3. Phase D — recovery comparison

Gated on Phase A (§1). Replays new Phase-C traces through the frozen engine,
observer and triggers, and asks whether current models produce recovery signal
the older traces did not, and whether it suffices to drain the state at
measured cadence.

- **H13.** Recovery signal is present in frontier traces but insufficient to
  drain the state at measured cadence. Draining from the clamp below 0.7
  requires 87.74 s of signal-free elapsed time (§0.5) and the observed gaps
  will not reach it. The trap holds numerically even if the mechanism has
  softened.
  - **Operationalisation.** A run *drains* if, in the frozen replay under its
    own real ordered dt sequence, frustration reaches ≥ 0.7 and subsequently
    falls below 0.7. Equivalently: some contiguous window carries > 87.74 s of
    summed dt with no frustration-increasing observer signal inside it.
  - **Falsified if ≥ 20% of frontier runs that reach the clamp subsequently
    drain below 0.7.** Supported if < 20% do and at least one human- or
    marker-identified recovery event occurs in a non-draining run (i.e.
    recovery happened and the monitor did not register it).
  - If **no** frontier run reaches the clamp at all, H13 is scored
    **inapplicable, not supported** — and that outcome is a substantive
    Paper-1-ages-out result, reported as such rather than reframed.

---

## 4. Phase C — frontier cadence census (design commitments only; not run yet)

Registered now because the arms and the logging point must be fixed before any
run, but **no Phase-C execution is authorized by this document**.

**The harness confound, and how it is controlled.** Per §0.6, Paper 2's
cadence numbers are `gpt-5.4-mini` inside `heart_instrument/agent_runner.py`.
Running Opus 5 through the Claude Code CLI hook and comparing to 1.53 s would
change model, vendor, harness, tool schema and turn structure simultaneously,
and H10 would be uninterpretable. Phase C therefore commits to:

- **C-main (bridge arm, required).** Opus 5 inside the *same*
  `agent_runner.py` loop: same three repositories at the SHAs pinned in
  `data/live_runs/REPO_PROVENANCE.md`, same injection specs, same
  `MAX_ACTIONS`, same `OBS_TRUNCATE`, same one-tool-call-per-turn structure,
  and the timestamp taken at the **same point in the cycle** — after the
  observation is produced (PostToolUse semantics). This is the only arm that
  is comparable to Paper 2, and H10 is scored on it alone.
- **C-effort (required).** Opus 5 in the same loop at two reasoning-effort
  settings, effort fixed and recorded per run. Effort is expected to move
  latency more than model identity does, and is currently treated as
  safety-irrelevant by everyone.
- **C-tail (small n, exploratory).** Fable 5.1, framed explicitly as the
  heavier-reasoning end of the same vendor's line. Small n; reported with
  its n; not scored confirmatorily.
- **C-eco (secondary, registered).** Opus 5 through the real Claude Code
  `PostToolUse` hook (`heart_instrument/hook_logger.py`). Ecologically valid
  but not comparable to Paper 2; its purpose is to *measure the harness delta*
  between the scriptable loop and the real CLI, which is itself a number the
  control literature does not have.

No OpenAI arm. Considered and dropped as underpowered and confounded.

**Logging requirements, per action:** effort level, extended-thinking status,
tool name, error indicator, and the post-observation wall-clock timestamp with
microseconds. Within-run distributions are reported in full — median, p90, IQR,
max, and the full ordered sequence — never the median alone.

**Power requirement (declared now because H11 fails silently without it).**
Hartigan's dip test is underpowered below ~30 observations. Paper 2's runs
carried n = 6…31 intervals. Phase C therefore targets **≥ 8 runs of ≥ 40
actions each**, and only runs with **n ≥ 30 dt intervals** are scored for H11.
Runs shorter than that are reported but excluded from the H11 denominator, and
the exclusion count is reported.

### Hypotheses

- **H10 (cadence).** Opus 5's pooled median inter-action dt is **below**
  Paper 2's 1.53 s, while its p90 is **materially above** 2.33 s — "materially"
  fixed here as **p90 ≥ 3.50 s** (≥ 1.5× Paper 2's p90).
  - Scored on C-main only. Median claim tested by Mann–Whitney U against the
    n=65 Paper-2 pool (α = 0.05, two-sided); p90 ratio reported with a
    bootstrap 95% CI (10,000 resamples, seed 20260908).
  - **Falsified if the distribution is tighter than Paper 2's**, fixed as
    dispersion ratio `p90/median ≤ 1.523` (Paper 2's own 2.33/1.53).
  - Declared limitation: even C-main changes vendor and model family together.
    H10 is a statement about *this harness with this model*, not about
    Anthropic models in general, and the paper will say so.
- **H11 (bimodality).** Within-run dt is bimodal — sub-second tool calls
  interleaved with reasoning pauses of tens of seconds.
  - **Primary test, declared in advance: Hartigan's dip test on log₁₀(dt),
    per run, α = 0.05.** Implementation: the `diptest` package if importable;
    otherwise the pre-registered fallback is a **BIC comparison of a 1- vs
    2-component Gaussian mixture on log₁₀(dt)**, with 2 components preferred
    only at `BIC(2) − BIC(1) < −10` (Kass–Raftery "very strong"). Whichever
    test is used is recorded in the result file; the fallback is not selected
    after seeing an unfavourable dip result.
  - **Supported if ≥ 50% of scored runs (n ≥ 30) reject unimodality.
    Falsified if < 25% do.** Between 25% and 50% is scored inconclusive and
    reported as inconclusive.
- **H12 (within-run stability).** Paper 2's "regimes are stable within a run"
  partially breaks on frontier traces: a non-trivial fraction of runs show band
  crossings under **real ordered latency**, not only under the exploratory
  time-scaled C4 condition.
  - **Operationalisation.** A run shows a *band crossing* if the frozen replay
    under its real ordered dt sequence yields crossings ≥ 2 or flicker ≥ 1,
    while the same trajectory replayed at that run's own constant median dt
    yields crossings ≤ 1 and flicker 0. (Phase-7 metrics, unchanged; flicker =
    excursions above 0.7 shorter than 5 actions.)
  - **Threshold, fixed in advance: H12 supported if ≥ 25% of runs show a band
    crossing; falsified if < 10%.** Paper 2's C3 result was 1/20 = 5%, so
    < 10% is "indistinguishable from Paper 2" and ≥ 25% is a real change.
    10–25% is scored partial and reported as partial.

---

## 5. Phase E — deliverable artefact

A reusable **cadence-invariance test**: sweep dt over a supplied grid, report
whether fire behaviour changes. Invariant ⇒ the monitor is sample-time
calibrated. Cliff ⇒ it is wall-clock calibrated. Packaged with the Section-8
design rule (input rate × half-life vs threshold elevation) so that any monitor
author can run it against their own monitor. Phase B's B3 condition is the
constructive half: it demonstrates that re-basing the decay onto the
observation clock removes the cliff.

No hypothesis is scored on Phase E; it is an artefact, and its correctness is
established by H14a/H14c holding on instruments whose calibration we already
know.

---

## 6. What we would be pleased to see falsified

Stated here so the framing cannot be retrofitted after the results are in.

**We would be pleased to see H13 and H12 falsified.** If Paper 1's mechanism
ages out with model generation — frontier agents recover, gaps lengthen, the
state drains, the trap stops closing — while Paper 2's structural result
survives (wall-clock calibration is still a regime boundary, budget still moves
monitors across it, sample-time integrators are still invariant), that is a
**stronger paper than a third confirmation**, and it is the outcome we would
prefer. It would say the affective-saturation finding was a property of a model
generation, and the calibration finding is a property of the instrument class —
which is exactly the division of labour Paper 3 is arguing for.

Concretely, we commit now to the following readings:

| Outcome | Reading, committed in advance |
|---|---|
| H13 falsified, H14 supported | Best case. Paper 1's mechanism is generational; Paper 2's is structural. Paper 3 leads with the instrument-class result and reports the trap as historical. |
| H13 supported, H14 supported | Third confirmation. Honest but weaker; the paper says so and does not inflate it. |
| H13 supported, H14 falsified | The budget corollary fails; Paper 3 loses its control-literature hook and is rescoped to a replication note. |
| H12 falsified (< 10%) | Paper 2's within-run stability claim is *confirmed*, not broken. Reported as a confirmation of prior work, and the C4 exploratory framing in Paper 2 §7 stands unchanged. |
| Phase A gate fails on κ | Reported as a Paper-1-continuous inter-rater result; Phase D demoted to exploratory in the same commit that reveals it. |

We are not entitled to any of these outcomes and will report whichever occurs.

---

## 7. Implementation conventions (declared with the commitment)

- **Indexing.** Unchanged from Phases 3/5/7/8: the first action receives no
  decay. `s_0 = clamp01(0.15·e_0)`; for i ≥ 1,
  `s_i = clamp01(s_{i-1}·exp(-λ·Δ) + 0.15·e_i)` where Δ is the elapsed time
  since the previous **observation** (`r·dt` under B1, `dt` under B3).
- **Subsampling.** Under budget r with offset o, the observed index set is
  `{o, o+r, o+2r, …}`. Skipped actions are invisible to the monitor under B1
  and B3; under B2 they are ingested but not evaluated.
- **Error stream source.** `has_error` from `fullstate_dt0_<id>.json`, all 20
  trajectories. The Phase-8 assumption that `has_error` is identical across
  dt-variant fullstate files was verified there and is re-verified by the
  Phase-B script on the same two trajectories before the sweep runs.
- **Statistics.** Spearman correlations computed from scratch (average ranks
  for ties, Pearson on ranks), as in Phase 8. Bootstrap seed 20260908. No
  library-version-dependent statistic is used without recording the version.
- **Provenance.** Every Phase-9 result file records the git commit SHA of the
  tree that produced it. This document's commit contains no result files.
- **No post-hoc tuning.** No threshold, half-life, step size, refractory
  window, or trigger definition is modified in Phase 9. Any quantity first
  specified after a result is seen is labelled EXPLORATORY inline, at the point
  it appears.
