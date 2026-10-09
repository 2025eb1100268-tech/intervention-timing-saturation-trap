# Monitoring budget x cadence (Phase B)

Tree commit: `f2c0ea7c575c`. Pre-registered: `PREREGISTRATION_PHASE9.md` §2, committed before this script ran. No new agent runs; 20 frozen error streams. Instrument definitions imported verbatim from `scripts/generality_sweep.py` (Phase 8): I1 lambda=ln2/150, step 0.15, level 0.7, re-arm 0.5; I2 k=0.1, h=1.0. Nothing tuned.

Sweep: r in [1, 2, 5, 10, 20, 50] x dt in ['0', '1', '1.53', '2.33', '5', '15', '30', '60', '150', '300', '600'] s (frozen grid plus the two pre-registered measured-cadence points [1.53, 2.33]). Offsets: all r for I1/I2, min(r,5) for A6/T3.

## Assumption re-check: `has_error` is dt-invariant

Checked across all 9 dt-variant fullstate files for astropy-13398 and astropy-13033: **PASS** (dt does not change which actions error). Same check as Phase 8.

## H14c — is the cliff exactly a change of variable?

For every (trajectory, r, dt, offset), I1 under B1 must be **bitwise identical** to the frozen Phase-8 `i1_series` evaluated at `dt' = r*dt` on the offset-subsampled stream. This is an identity, not an empirical claim; a failure is a bug.

Cells checked: 20 trajectories x 88 (r, offset) pairs x 11 dt. **Mismatches: 0**

**H14c holds exactly.** Budget r and cadence dt enter I1 only through the product `r*dt`. A monitoring-budget decision and a cadence change are, for this instrument, *the same intervention*: the effective time constant a wall-clock monitor experiences is set jointly by how fast the agent acts and how much of its behaviour anyone can afford to look at.

## Table 1 — I1 level trigger under B1 (sampled observation)

Median across offsets; `x` marks cells where the subsampled stream has fewer than 2 observations (degenerate, reported not fixed).

| r | dt=0 | dt=1 | dt=1.53 | dt=2.33 | dt=5 | dt=15 | dt=30 | dt=60 | dt=150 | dt=300 | dt=600 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | 100 | 100 | 100 | 100 | 58 | 0 | 0 | 0 | 0 | 0 |
| 2 | 50 | 50 | 29 | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 50 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Cell = median across trajectories of median-across-offsets post-first-crossing persistence (%). The frozen regime rule is persistence < 50% ⇒ the monitor has left the alarm regime.

## Table 2 — I1 critical interval vs budget (B1)

| Trajectory | r=1 | r=2 | r=5 | r=10 | r=20 | r=50 |
|---|---|---|---|---|---|---|
| astropy-12907 | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-13033 | (30, 60] | (15, 30] | (5, 15] | (0, 0] | (0, 0] | (0, 0] |
| astropy-13236 | (30, 60] | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-13398 | (0, 1] | (0, 0] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-13453 | (5, 15] | (0, 1] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-14096 | (15, 30] | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-14182 | (5, 15] | (0, 1] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-14309 | (15, 30] | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-14369 | (15, 30] | (5, 15] | (0, 1] | (0, 0] | (0, 0] | (0, 0] |
| astropy-14508 | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-7336 | (5, 15] | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-7671 | (5, 15] | (0, 1] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-8707 | (15, 30] | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| astropy-8872 | (15, 30] | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-10097 | (5, 15] | (0, 1] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-10554 | (15, 30] | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-10914 | (15, 30] | (1, 5] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-10973 | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-11087 | (15, 30] | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |
| django-11095 | (30, 60] | (5, 15] | (0, 0] | (0, 0] | (0, 0] | (0, 0] |

Pre-registered expectation (H14c corollary): the interval at budget r is the r=1 interval divided by r, to grid resolution.

## Table 3 — H14d: regime flip at the measured cadence (dt = 1.53 s)

| Trajectory | r=1 | r=2 | r=5 | r=10 | r=20 | r=50 | flips by r=10? |
|---|---|---|---|---|---|---|---|
| astropy-12907 | 63 | 0* | 0* | 0* | 0* | 0* | YES |
| astropy-13033 | 100 | 100 | 100 | 0* | 0* | 0* | YES |
| astropy-13236 | 100 | 100 | 0* | 0* | 0* | 0* | YES |
| astropy-13398 | 0* | 0* | 0* | 0* | 0* | 0* | - |
| astropy-13453 | 100 | 0* | 0* | 0* | 0* | 0* | YES |
| astropy-14096 | 100 | 38 | 0* | 0* | 0* | 0* | YES |
| astropy-14182 | 100 | 0* | 0* | 0* | 0* | 0* | YES |
| astropy-14309 | 85 | 17 | 0* | 0* | 0* | 0* | YES |
| astropy-14369 | 100 | 97 | 0* | 0* | 0* | 0* | YES |
| astropy-14508 | 86 | 0* | 0* | 0* | 0* | 0* | YES |
| astropy-7336 | 100 | 21 | 0* | 0* | 0* | 0* | YES |
| astropy-7671 | 100 | 14 | 0* | 0* | 0* | 0* | YES |
| astropy-8707 | 100 | 100 | 0* | 0* | 0* | 0* | YES |
| astropy-8872 | 100 | 92 | 0* | 0* | 0* | 0* | YES |
| django-10097 | 93 | 12 | 0* | 0* | 0* | 0* | YES |
| django-10554 | 100 | 50 | 0* | 0* | 0* | 0* | YES |
| django-10914 | 91 | 50 | 0* | 0* | 0* | 0* | YES |
| django-10973 | 78 | 0* | 0* | 0* | 0* | 0* | YES |
| django-11087 | 100 | 50 | 0* | 0* | 0* | 0* | YES |
| django-11095 | 100 | 100 | 0* | 0* | 0* | 0* | YES |

Persistence %; `*` = never crossed 0.7 at all.

In the alarm regime at r=1: **19/20**. Left it by r=10: **19/20** (pre-registered bar: >= 11/20).

## Table 4 — H14a / H14b: sample-time CUSUM under budget

| Trajectory | dt-invariant at every r? | fire count by r (1, 2, 5, 10, 20, 50) | non-increasing in r? |
|---|---|---|---|
| astropy-12907 | PASS | 24, 9, 0, 0, 0, 0 | yes |
| astropy-13033 | PASS | 56, 25, 9, 4, 1, 0 | yes |
| astropy-13236 | PASS | 30, 14, 4, 2, 0, 0 | yes |
| astropy-13398 | PASS | 28, 8, 0, 0, 0, 0 | yes |
| astropy-13453 | PASS | 27, 12, 0, 0, 0, 0 | yes |
| astropy-14096 | PASS | 23, 8, 0, 0, 0, 0 | yes |
| astropy-14182 | PASS | 32, 16, 2, 0, 0, 0 | yes |
| astropy-14309 | PASS | 25, 8, 1, 0, 0, 0 | yes |
| astropy-14369 | PASS | 48, 22, 8, 3, 0, 0 | yes |
| astropy-14508 | PASS | 9, 3, 0, 0, 0, 0 | yes |
| astropy-7336 | PASS | 25, 11, 4, 0, 0, 0 | yes |
| astropy-7671 | PASS | 23, 8, 0, 0, 0, 0 | yes |
| astropy-8707 | PASS | 36, 16, 5, 1, 0, 0 | yes |
| astropy-8872 | PASS | 21, 10, 2, 0, 0, 0 | yes |
| django-10097 | PASS | 32, 15, 1, 0, 0, 0 | yes |
| django-10554 | PASS | 28, 12, 4, 0, 0, 0 | yes |
| django-10914 | PASS | 21, 8, 2, 0, 0, 0 | yes |
| django-10973 | PASS | 19, 8, 1, 0, 0, 0 | yes |
| django-11087 | PASS | 34, 13, 2, 0, 0, 0 | yes |
| django-11095 | PASS | 19, 8, 2, 0, 0, 0 | yes |

Left column is H14a (exact dt-invariance, preserved at every budget). Right column is H14b (budget degrades I2 along a sensitivity axis, never across a regime boundary). I2 has no critical interval at any r because it never reads a clock.

## Table 5 — H14e: A6 and T3 under B1 (engine replay)

| r | A6 fires (med [min-max]) | T3 net (max) | trajectories in alarm | critical interval, median |
|---|---|---|---|---|
| 1 | 18 [0-47] | 1 | 19/20 | 15 |
| 2 | 0 [0-18] | 1 | 10/20 | 3 |
| 5 | 0 | 1 | 0/20 | 0 |
| 10 | 0 | 0 | 0/20 | 0 |
| 20 | 0 | 0 | 0/20 | 0 |
| 50 | 0 | 0 | 0/20 | 0 |

A6 and alarm counts evaluated at the measured cadence dt = 1.53 s; critical interval computed over the frozen grid. T3 bound carried from H6/H9 is <= 3.

## Table 6 — decomposing the budget effect (I1, dt = 1.53 s)

| r | B1 sampled observation | B2 sampled evaluation | B3 sample-time calibrated |
|---|---|---|---|
| 1 | 100 | 100 | 100 |
| 2 | 29 | 100 | 50 |
| 5 | 0 | 100 | 0 |
| 10 | 0 | 100 | 0 |
| 20 | 0 | 100 | 0 |
| 50 | 0 | 0 | 0 |

Median-across-trajectories persistence (%). B1 changes evidence **and** decay; B2 changes neither (only how often the trigger is checked); B3 changes evidence only, because its decay is re-based onto the observation clock. The B1-vs-B3 gap is the part of the budget effect attributable purely to **wall-clock calibration** -- and it is the part a monitor author can remove without touching a threshold.

## H14 scorecard

- **H14a  I2 dt-invariant at every r** -> SUPPORTED (exact invariance preserved under budget)
- **H14b  I2 fire count non-increasing in r** -> SUPPORTED (budget degrades I2 quantitatively)
- **H14c  I1 under B1 == i1_series(sub, r*dt)** -> SUPPORTED (budget and cadence are the same knob)
- **H14d  >= 11/20 leave alarm regime by r=10 at 1.53s** -> SUPPORTED (19/20 flipped (of 19/20 in alarm at r=1))
- **H14e  T3 net <= 3 everywhere** -> SUPPORTED (max T3 net observed = 1)
