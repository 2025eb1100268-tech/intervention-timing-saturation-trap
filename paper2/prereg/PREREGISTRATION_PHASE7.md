# Pre-registration: Phase 7 — non-uniform dt replay

Committed BEFORE any Phase-7 replay was executed. Engine, adapter, triggers,
thresholds all frozen (the Phase 1-6 invariants). dt injected per action via
the established explicit `engine._tick_decay(dt)` pre-tick; everything else
identical to the Phase 3/5 replay loop.

## Conditions (per trajectory; the 20-trajectory Phase-5 set)

- **C1** constant dt = the pooled median inter-action dt from Phase 6's live
  runs (computed from `data/live_runs/run*/timing.json` at run time, not
  hand-entered). One replay per trajectory.
- **C2** i.i.d. lognormal dt. Parameters fit to the Phase 6 pooled
  distribution by matching median and p90 exactly:
  `mu = ln(median)`, `sigma = (ln(p90) - ln(median)) / z_0.90`,
  `z_0.90 = 1.2815515655`. **10 seeds per trajectory** (seed = 1000*traj_index
  + s, s in 0..9, stdlib `random.Random`).
- **C3** empirical sequences: the real dt sequences from the five Phase 6
  live runs, tiled/truncated to trajectory length, order preserved (burst
  structure intact). **5 sequences per trajectory** (one per live run).

## Metrics, per (trajectory x condition x seed)

- upward threshold-crossing count of frustration at 0.7
- fraction of actions in elevated state (frustration >= 0.7)
- A6 `sustained_frustration` fire count; T3 `saturation_entry` NET fire count
  (through the standard CooldownGuidelines, refractory 5)
- **flicker index**: number of distinct excursions above 0.7 lasting
  < 5 actions

## Hypotheses (committed now)

- **H5**: under C2/C3, A6 exhibits flicker (median crossing count > 2) on
  trajectories whose uniform-dt critical interval (Phase 5) brackets the dt
  median.
- **H6**: T3 net fire count remains <= 3 under all conditions
  (cadence-robust).

## Falsification clause (committed now)

If A6 behaves as a clean single-crossing accumulator under C3 (real bursts),
the knife-edge/bistability framing must be softened to "regime-dependent"
and the paper's §4-5 revised accordingly. Whichever happens is reported.

## Analytic expectation (stated before running; part of this commitment)

From the frozen dynamics we can already derive where this experiment's power
lies, and we state it so the result cannot be over-read:

1. Decay from the frustration clamp (1.0) to below 0.7 requires
   `0.1 + 0.9*exp(-ln2/150 * dt) < 0.7`, i.e. **dt > ~88 s of inter-action
   silence**. Phase 6's maximum observed gap is 15.9 s. Therefore once a
   trajectory clamps, NO gap in C1-C3 can pull it back below threshold.
2. The pooled median (~1.5 s) lies below the critical interval of 17 of the
   20 trajectories; only the three with interval (1, 5] are bracketed, so H5
   has at most 3 eligible trajectories.
3. Consequently the expected C1-C3 outcome is single-crossing accumulator
   behavior nearly everywhere. If that occurs, the honest reading is
   "measured cadence sits below the critical band," NOT "the mechanism
   cannot flicker." Distinguishing those is the purpose of C4 below.

## Exploratory condition (declared now, NOT pre-registered as confirmatory)

- **C4 (EXPLORATORY)** scaled empirical sequences: each Phase-6 dt sequence
  multiplied by a per-trajectory factor `s = target / empirical_median`,
  where `target` = geometric midpoint `sqrt(lo*hi)` of that trajectory's
  Phase-5 critical interval (intervals recomputed from the existing
  fullstate_dt artifacts, not hand-entered). Burst SHAPE preserved, location
  shifted into the knife-edge band. 5 sequences per trajectory. Same metrics.
  C4 answers "does flicker exist anywhere in the dynamics?" and is reported
  in a separate, clearly-labeled exploratory section. H5/H6 are scored on
  C1-C3 only.

## Procedure notes

- Replays are metric-only (no fullstate persistence; ~420 replays).
- Per-trajectory events parsed once and reused (ActionEvents are immutable;
  the adapter does not mutate them).
- Figure data: frustration traces under C3 and C4 for two illustrative
  trajectories (13398: interval (1,5]; 13033: interval (15,30]).
- No threshold, trigger, or engine change of any kind.
