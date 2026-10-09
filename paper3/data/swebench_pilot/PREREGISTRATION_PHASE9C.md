# Pre-registration: Phase 9C — clean-protocol Opus 5 vs Fable 5.1 replication

Committed BEFORE the first run of the new set. This commit contains **no result
artefacts**. The clean-git protocol and its throwaway validation run were
committed separately at `a451e66`; that run is labelled `model=throwaway,
repeat=0` and is **excluded from every analysis below** — it validated the
harness, it is not data.

Supersedes the ten runs of `data/live_runs/phase_c_sub/`, which are **relegated
to a labelled pilot** and are **not pooled** with the new set at any point.

---

## 0. Why the pilot is being redone, and what I confirmed before acting

**Statistics.** The pilot's headline `p = 2.1e-05` was a Mann–Whitney over 65 vs
72 *intervals*, treating intervals within a run as independent. They share a
repo, a task, a session and a tool-use policy. The run is the correct unit.
Confirmed by recomputation:

| spec | Opus median | Fable median | delta (O−F) |
|---|---|---|---|
| runA | 7.123 | 3.438 | **+3.685** |
| runB | 4.163 | 4.642 | **−0.479** |
| runC | 7.790 | 4.766 | **+3.024** |
| runD | 7.035 | 3.040 | **+3.995** |
| runE | 3.949 | 1.095 | **+2.854** |

4/5 favour Fable being faster. Exact Wilcoxon signed-rank: W⁺ = 14, W⁻ = 1,
**two-sided p = 4/32 = 0.1250**. And the **floor at n = 5 is
2/2⁵ = 0.0625** — perfect separation cannot reach α = 0.05, so the pilot's
claim was unreachable at any effect size. Both figures confirmed independently.

**Protocol.** Bug injection wrote *uncommitted* edits over a pinned commit, so
`git diff` handed over the answer key.

### 0.1 One correction to the brief's reading of the git leak

The brief states the leak "sits directly upstream of the Read-call counts that
carry the tool-use-strategy mechanism." **The pilot data does not support
that**, and it should not be asserted:

| run | git recon calls | Read calls |
|---|---|---|
| runE **Fable** | 3 | **25** |
| runE **Opus** | 3 | **4** |

Both runE arms had *identical* git availability and both used it. The 25-vs-4
Read difference therefore varies **within** constant git availability, so it is
not an artefact of the leak. Across the pilot, git use tracked task complexity
(only runC and runE, the two multi-target tasks) and was associated with *more*
actions, not fewer (mean 20.2 vs 9.3).

The leak is still a genuine defect and is fixed — it changes what is findable
(the throwaway agent could not recover the test-invisible `first` bug that pilot
agents read straight out of `git diff`), which changes task difficulty and makes
action counts non-comparable to Paper 2. But the mechanism variable is **not**
downstream of it, and the rerun's purpose is replication under a clean protocol,
not decontamination of a poisoned measurement.

---

## 1. THE BINDING CONSTRAINT: distinct specs, not pairs

**This changes the design and must be settled before any run.**

`heart_instrument/agent_runner.py::RUNS` contains **5 specs across 3 repos**,
and `runA`/`runB` share both repo *and* pytest target — they differ only in
which bugs are injected. So there are **4 distinct (repo, target) combinations**.

15 matched pairs drawn from 5 specs is **3 repeats per spec**, and repeats within
a spec share repo, task, target and injected bugs. They are not independent
units. **Wilcoxon would still be n = 5, floor 0.0625.** Repeats reduce
within-spec measurement noise; they add no independent units.

Floors, for the record:

| independent specs | best possible two-sided Wilcoxon p |
|---|---|
| 5 | 6.25e-02 |
| 8 | 7.81e-03 |
| 10 | 1.95e-03 |
| 15 | 6.10e-05 |
| 20 | 1.91e-06 |

**Committed design.** The confirmatory unit is the **spec**. H16 and H17a are
scored on a Wilcoxon signed-rank over **per-spec** values, where a spec's value
is the median across its repeats. `n` in every test below is the **number of
distinct specs**, never the number of runs.

**Therefore the rerun requires expanding the spec set**, and the analysis is
pre-registered against whatever the final count is:

- **n ≥ 12 distinct specs** → H16/H17a scored confirmatorily at α = 0.05.
- **8 ≤ n < 12** → scored, with the floor and achieved power stated inline.
- **n < 8** → H16/H17a are reported as **descriptive only**, explicitly
  unscoreable, exactly as the pilot should have been.

New specs must be distinct `(repo, pytest target)` pairs, not new bug-sets on an
existing target. Target modules available without new repos: sortedcontainers
(`sortedlist`, `sorteddict`, `sortedset`, `sortedkeylist`), toolz (`itertoolz`,
`dicttoolz`, `functoolz`, `recipes`), more-itertools (`more`, `recipes`) — about
10, so reaching 12–15 needs 2–5 additional repositories. Every new injection
must satisfy the existing exactly-once replacement rule and its applied/skipped
status is logged per run as now.

**Repeats.** 2 per spec per arm, giving 4 runs per spec. Repeat count is fixed
now and does not depend on interim results.

---

## 2. Hypotheses

Effort is fixed and recorded per run; extended-thinking status per action **if
the hook exposes it** (it did not in the pilot — `thought` is always `""`), in
which case its absence is recorded rather than silently omitted.

### H16 (replication of the cadence direction)

**Fable 5.1's median inter-action interval is BELOW Opus 5's on matched specs.**
Direction stated now: Fable faster. This is the direction the pilot showed
(4/5 specs), and it is the counter-intuitive one — the heavier-reasoning model
acting faster at the median.

- **Test:** Wilcoxon signed-rank on per-spec median dt (Opus − Fable),
  two-sided, α = 0.05, exact null distribution, `n` = distinct specs.
- **Supported** if p < 0.05 and the median difference is positive.
- **Falsified** if p < 0.05 with a negative median difference (Fable slower).
- **Inconclusive** if p ≥ 0.05, reported as inconclusive with the floor stated —
  not as a null and not as support.

### H17 (the Read-burst mechanism) — the one that matters

In the pilot this entire claim rests on **one run**: runE Fable, 25 Reads vs 4,
the only clamp in ten runs, 28 A6 fires vs 0. If Read-bursting does not
replicate, **the mechanism claim comes out of the paper.**

**H17a — Fable issues more Read calls per run than Opus on matched specs.**
- **Test:** Wilcoxon signed-rank on per-spec Read count (Fable − Opus),
  two-sided, α = 0.05, `n` = distinct specs. Supported if p < 0.05 with a
  positive median difference.

**H17b — Read-call count predicts peak modelled frustration.**
- **Test, and the pre-committed discipline:** the **raw** correlation between
  Read count and peak frustration will **NOT** be quoted as evidence. More Reads
  means more actions, and more actions means more accumulation opportunities and
  a shorter median dt, so a raw correlation is near-tautological in exactly the
  way §5 of the data pack documents for two other correlations.
  The reported statistic is the **Spearman partial correlation of Read count
  with peak frustration, controlling for action count**, over all runs of both
  arms, with a permutation null (20,000 shuffles, seed 20260908).
  Every correlation in the eventual report gets the **THE TEST / NOT a test**
  treatment: raw, marginal-with-control, and partial printed side by side.
- **Supported** if the partial is positive with permutation p < 0.05.
- **Falsified** if the partial is not distinguishable from zero (p ≥ 0.05) —
  in which case Read-bursting is a correlate of doing more work, not a
  mechanism, and the claim is withdrawn.
- If Read count and action count are collinear beyond r_s > 0.9, the partial is
  uninterpretable; that is **stated as an outcome**, not worked around.

### H18 (clamp rate)

**Clamps remain rare in both arms under the clean protocol.**
- **"Rare" fixed now: ≤ 20% of runs per arm reach the 1.0 clamp.**
- **Supported** if both arms are ≤ 20%.
- **Falsified** if either arm exceeds 20% — clamping would then be a common
  outcome rather than the rare one the pilot suggested (1/5 Fable, 0/5 Opus),
  and the "trap is reachable but unreliable" framing would need replacing with
  "the trap closes routinely".
- **Third outcome, pre-stated:** if **zero** runs clamp in either arm, the
  pilot's single runE clamp is **unreplicated**, and the clamp-specific
  mechanism claim is withdrawn. The cadence and regime-placement results do not
  depend on it and stand either way.

---

## 3. Action counts under the clean protocol — direction stated in advance

**Prediction: action counts INCREASE relative to the pilot**, because the
`git diff` shortcut to bug localisation is gone and the agent must localise by
reading and testing.

Pilot baselines for the same specs (Opus / Fable): runA 8/7, runB 13/7,
runC 15/16, runD 14/7, runE 15/35.

- **Supported** if the median per-spec action count in the new set exceeds the
  pilot median on matched specs (Opus 14, Fable 7).
- **Falsified** if it is lower.
- Counter-evidence already in hand, stated so it cannot be presented later as a
  surprise: the single throwaway run gave runD 15 actions against pilot
  runD Opus 14 and Fable 7 — one data point, consistent with "no change or a
  small increase", not with a large one.

This comparison is **pilot-vs-new across a protocol change**, so it is
confounded with the protocol by construction. It is registered as
**descriptive**, to make the protocol's effect legible, not as a test of
anything about the models.

---

## 4. H11 — retired, with a conditional revival

H11 (within-run dt bimodality, Hartigan's dip test, per run, n ≥ 30 intervals)
is **RETIRED as a confirmatory hypothesis**, and the reason is **structural, not
an n problem**:

- The dip test's power floor is **per run**. Additional spec pairs add *runs*,
  not intervals *within* a run.
- Only **1 of 10** pilot runs reached n ≥ 30 (Fable runE, 34). Action counts are
  7–16 on four of five specs.
- Pooling intervals across runs to reach n ≥ 30 would commit exactly the
  unit-of-analysis error that §0 is correcting, so it is not an available fix.

Reaching a scoreable H11 would require deliberately selecting long-running
tasks, which changes the task set and hence the estimand. That is a different
experiment, not this one.

**Conditional revival, committed now:** if ≥ 8 runs in the new set reach
n ≥ 30 intervals, the dip test will be run and reported — labelled
**EXPLORATORY**, because H11 is retired at the time of this commit and a revived
retired hypothesis is not confirmatory.

---

## 5. Discipline

- No frozen component modified. `phase_c_subagent.py` is left byte-identical;
  the new protocol lives in `phase_c2_subagent.py`.
- 358 tests green before and after.
- Anything specified after seeing results is labelled **EXPLORATORY** at the
  point it appears.
- Every correlation reported anywhere gets the **THE TEST / NOT a test**
  treatment, including H17b's.
- Attribution remains by time window; agents run one at a time in the
  foreground; operator records are dropped by `tool_input`; any window with an
  unattributable record is **discarded, not repaired**.
- Per-run clean-git assertions (six) are logged; a run whose assertions fail is
  **aborted, not repaired**.
- Repos are restored to their pinned SHAs after every run and the restore is
  verified and logged.

## 6. What this round still cannot settle

- **H10** is retired (see the scorecard), not deferred.
- **H12** is not re-registered: the pilot's Opus PARTIAL (1/5) rested on a
  band-crossing definition applied to a single run, and with the pilot
  relegated there is no confirmatory claim to carry forward. It will be
  recomputed on the new set and reported **descriptively**.
- **Absolute cadence remains cross-harness** against Paper 2. Nothing in this
  round makes C2 comparable to the scriptable-loop numbers; only the deferred
  C-main arm would.

---

# AMENDMENT 1 — spec set and repeat count (pre-data)

Committed **before the first 9C run**. No 9C result artefact exists at this
commit. Both changes are resource/statistics decisions taken without reference
to any 9C outcome.

## A1.1 Spec set: 8 verified specs, built and mechanically checked

`scripts/build_phase9c_specs.py` proposed 10 candidate specs and **verified 8**.
Each verified spec is a **distinct (repo, source module, test target) triple**:

| id | repo | module | target | bugs |
|---|---|---|---|---|
| S02 | sortedcontainers | `sorteddict.py` | `test_coverage_sorteddict.py` | 3 |
| S03 | sortedcontainers | `sortedset.py` | `test_coverage_sortedset.py` | 3 |
| S05 | toolz | `itertoolz.py` | `test_itertoolz.py` | 3 |
| S06 | toolz | `dicttoolz.py` | `test_dicttoolz.py` | 1 |
| S07 | toolz | `functoolz.py` | `test_functoolz.py` | 2 |
| S08 | toolz | `recipes.py` | `test_recipes.py` | 2 |
| S09 | more-itertools | `more_itertools/recipes.py` | `test_recipes.py` | 2 |
| S10 | more-itertools | `more_itertools/more.py` | `test_more.py` | 1 |

Each was admitted only on passing four mechanical checks: target tests **pass**
on the clean pinned tree; every bug's `old` string occurs **exactly once**;
target tests **fail** after injection (so the task is not degenerate); and the
tree **restores** to the pinned SHA.

S01 and S04 were **dropped**, not patched — their candidate `old` strings did
not occur exactly once. Both targeted `sortedlist.py`, which S02/S03 already
cover at the repo level, so admitting them would have added two specs sharing a
module with each other while the eight kept specs share none. Eight distinct
modules is preferred to ten with a duplicated module.

**n = 8** falls in the pre-registered `8 ≤ n < 12` band, so H16 and H17a are
**scored with the floor and achieved power stated inline**. Exact two-sided
Wilcoxon floor at n = 8 is **2/2⁸ = 7.81e-03**, comfortably below α = 0.05, so
unlike the pilot the test is reachable.

## A1.2 Repeats: 1 per spec per arm, not 2

§1 fixed repeats at 2 (32 runs at 8 specs). Amended to **1 repeat per spec per
arm — 16 runs total** — for a stated, result-independent reason:

For a Wilcoxon signed-rank on per-spec values, **independent specs supply
power; repeats only reduce within-spec measurement noise.** Under a fixed run
budget, spending runs on distinct specs strictly dominates spending them on
repeats. The 16 runs therefore go to 8 specs × 2 arms rather than 4 specs × 2
arms × 2 repeats.

**The cost, stated rather than hidden:** each spec's value is a single run's
median, so per-spec estimates carry run-to-run agent stochasticity that
averaging would have damped. This inflates within-pair noise and *reduces*
power against a real effect — it cannot manufacture one.

**Contingency, fixed now so it is not a forking path:** if H16 or H17a returns
**inconclusive** (p ≥ 0.05), the committed next step is to **add the second
repeat to all 8 specs** and re-score on the 2-repeat means. It is *not* to
reinterpret, re-threshold, or subset the existing runs. If either returns
significant, no further runs are added.

## A1.3 Everything else unchanged

Direction of H16 (Fable faster) stated in §2 stands. H17b's partial-correlation
discipline stands. H18's ≤20% "rare" threshold stands. The action-count
direction prediction (increase, descriptive) stands. H11 remains retired with
its conditional revival. The pilot remains relegated and unpooled.
