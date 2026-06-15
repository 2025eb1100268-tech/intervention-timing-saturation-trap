# Non-uniform dt replay (Phase 7)

Pre-registered design: `PREREGISTRATION_PHASE7.md` (committed before running, including the analytic expectation). Engine/adapter/triggers/thresholds frozen; ~420 metric-only replays.

Phase-6 pooled empirical dt: median **1.53 s**, p90 **2.33 s** (n=65). C2 lognormal: mu=0.4251, sigma=0.3298 (median/p90-matched). C3 = the 5 real Phase-6 sequences, order preserved. C4 (EXPLORATORY) = same sequences scaled per trajectory to the geometric midpoint of its critical interval.

## C1 constant median dt (pre-registered)

Per trajectory: median over seeds/sequences (min-max in brackets).

| Trajectory | crossings | elevated frac | A6 fires | T3 net | flicker |
|---|---|---|---|---|---|
| astropy-12907 | 1 | 0.39 | 11 | 1 | 0 |
| astropy-13033 | 1 | 0.80 | 47 | 1 | 0 |
| astropy-13236 | 1 | 0.50 | 22 | 1 | 0 |
| astropy-13398 | 1 | 0.73 | 41 | 1 | 0 |
| astropy-13453 | 1 | 0.58 | 18 | 1 | 0 |
| astropy-14096 | 1 | 0.37 | 10 | 1 | 0 |
| astropy-14182 | 1 | 0.74 | 26 | 1 | 0 |
| astropy-14309 | 0 | 0.00 | 0 | 0 | 0 |
| astropy-14369 | 1 | 0.73 | 40 | 1 | 0 |
| astropy-14508 | 1 | 0.36 | 9 | 1 | 0 |
| astropy-7336 | 1 | 0.68 | 19 | 1 | 0 |
| astropy-7671 | 1 | 0.30 | 8 | 1 | 0 |
| astropy-8707 | 1 | 0.72 | 29 | 1 | 0 |
| astropy-8872 | 1 | 0.33 | 11 | 1 | 0 |
| django-10097 | 1 | 0.65 | 22 | 1 | 0 |
| django-10554 | 1 | 0.69 | 22 | 1 | 0 |
| django-10914 | 1 | 0.55 | 18 | 1 | 0 |
| django-10973 | 1 | 0.35 | 11 | 1 | 0 |
| django-11087 | 1 | 0.61 | 23 | 1 | 0 |
| django-11095 | 1 | 0.37 | 11 | 1 | 0 |
| **aggregate** | med 1, max 1 | - | - | max 1 | med 0, max 0 |

## C2 i.i.d. lognormal, 10 seeds (pre-registered)

Per trajectory: median over seeds/sequences (min-max in brackets).

| Trajectory | crossings | elevated frac | A6 fires | T3 net | flicker |
|---|---|---|---|---|---|
| astropy-12907 | 1 | 0.39 | 11 | 1 | 0 |
| astropy-13033 | 1 | 0.80 | 47 | 1 | 0 |
| astropy-13236 | 1 [1-2] | 0.48 [0.45-0.50] | 21 [20-22] | 1 | 0 [0-1] |
| astropy-13398 | 1 | 0.73 | 41 | 1 | 0 |
| astropy-13453 | 1 | 0.58 | 18 | 1 | 0 |
| astropy-14096 | 1 | 0.37 | 10 | 1 | 0 |
| astropy-14182 | 1 | 0.74 | 26 | 1 | 0 |
| astropy-14309 | 0 [0-1] | 0.00 [0.00-0.04] | 0 [0-1] | 0 [0-1] | 0 [0-1] |
| astropy-14369 | 1 | 0.73 | 40 | 1 | 0 |
| astropy-14508 | 1 | 0.36 | 9 | 1 | 0 |
| astropy-7336 | 1 | 0.68 | 19 | 1 | 0 |
| astropy-7671 | 1 | 0.30 | 8 | 1 | 0 |
| astropy-8707 | 1 | 0.72 | 29 | 1 | 0 |
| astropy-8872 | 1 | 0.33 | 11 | 1 | 0 |
| django-10097 | 1 | 0.65 | 22 | 1 | 0 |
| django-10554 | 1 | 0.69 | 22 | 1 | 0 |
| django-10914 | 1 | 0.55 | 18 | 1 | 0 |
| django-10973 | 1 | 0.35 | 11 | 1 | 0 |
| django-11087 | 1 | 0.61 | 23 | 1 | 0 |
| django-11095 | 1 | 0.37 | 11 | 1 | 0 |
| **aggregate** | med 1, max 1 | - | - | max 1 | med 0, max 0 |

## C3 empirical sequences, 5 per trajectory (pre-registered)

Per trajectory: median over seeds/sequences (min-max in brackets).

| Trajectory | crossings | elevated frac | A6 fires | T3 net | flicker |
|---|---|---|---|---|---|
| astropy-12907 | 1 | 0.39 | 11 | 1 | 0 |
| astropy-13033 | 1 | 0.80 | 47 | 1 | 0 |
| astropy-13236 | 2 [1-2] | 0.48 [0.45-0.50] | 21 [20-22] | 1 | 1 [0-1] |
| astropy-13398 | 1 | 0.73 | 41 | 1 | 0 |
| astropy-13453 | 1 | 0.58 | 18 | 1 | 0 |
| astropy-14096 | 1 | 0.37 | 10 | 1 | 0 |
| astropy-14182 | 1 | 0.74 | 26 | 1 | 0 |
| astropy-14309 | 0 | 0.00 | 0 | 0 | 0 |
| astropy-14369 | 1 | 0.73 | 40 | 1 | 0 |
| astropy-14508 | 1 | 0.36 | 9 | 1 | 0 |
| astropy-7336 | 1 | 0.68 | 19 | 1 | 0 |
| astropy-7671 | 1 | 0.30 | 8 | 1 | 0 |
| astropy-8707 | 1 | 0.72 | 29 | 1 | 0 |
| astropy-8872 | 1 | 0.33 | 11 | 1 | 0 |
| django-10097 | 1 | 0.65 | 22 | 1 | 0 |
| django-10554 | 1 | 0.69 | 22 | 1 | 0 |
| django-10914 | 1 | 0.55 | 18 | 1 | 0 |
| django-10973 | 1 | 0.35 | 11 | 1 | 0 |
| django-11087 | 1 | 0.61 | 23 | 1 | 0 |
| django-11095 | 1 | 0.37 | 11 | 1 | 0 |
| **aggregate** | med 1, max 2 | - | - | max 1 | med 0, max 1 |

## C4 scaled empirical sequences (EXPLORATORY)

Per trajectory: median over seeds/sequences (min-max in brackets).

| Trajectory | crossings | elevated frac | A6 fires | T3 net | flicker |
|---|---|---|---|---|---|
| astropy-12907 | 1 | 0.21 [0.18-0.25] | 6 [5-7] | 1 | 0 |
| astropy-13033 | 1 [0-2] | 0.02 [0.00-0.08] | 1 [0-5] | 1 [0-2] | 1 [0-2] |
| astropy-13236 | 0 | 0.00 | 0 | 0 | 0 |
| astropy-13398 | 1 [1-2] | 0.73 [0.66-0.73] | 41 [37-41] | 1 [1-2] | 0 |
| astropy-13453 | 1 | 0.26 [0.23-0.29] | 8 [7-9] | 1 | 0 |
| astropy-14096 | 1 | 0.30 [0.19-0.30] | 8 [5-8] | 1 | 0 |
| astropy-14182 | 2 [1-4] | 0.43 [0.40-0.60] | 15 [14-21] | 2 [1-2] | 1 [0-3] |
| astropy-14309 | 0 | 0.00 | 0 | 0 | 0 |
| astropy-14369 | 1 [1-3] | 0.73 [0.31-0.73] | 40 [17-40] | 1 [1-2] | 0 [0-1] |
| astropy-14508 | 1 | 0.28 [0.28-0.32] | 7 [7-8] | 1 | 0 |
| astropy-7336 | 1 [1-2] | 0.43 [0.39-0.43] | 12 [11-12] | 1 | 0 |
| astropy-7671 | 1 [1-2] | 0.26 [0.22-0.26] | 7 [6-7] | 1 | 0 [0-2] |
| astropy-8707 | 3 [1-4] | 0.35 [0.30-0.50] | 14 [12-20] | 2 [1-3] | 1 [0-2] |
| astropy-8872 | 1 [0-1] | 0.06 [0.00-0.09] | 2 [0-3] | 1 [0-1] | 1 [0-1] |
| django-10097 | 1 [1-2] | 0.56 [0.32-0.62] | 19 [11-21] | 1 [1-2] | 0 [0-1] |
| django-10554 | 2 [1-3] | 0.41 [0.38-0.53] | 13 [12-17] | 1 [1-2] | 0 [0-2] |
| django-10914 | 2 [0-3] | 0.12 [0.00-0.18] | 4 [0-6] | 1 [0-1] | 2 [0-3] |
| django-10973 | 1 [1-2] | 0.03 [0.03-0.06] | 1 [1-2] | 1 | 1 [1-2] |
| django-11087 | 3 [1-4] | 0.47 [0.21-0.58] | 18 [8-22] | 1 [1-2] | 0 [0-2] |
| django-11095 | 0 | 0.00 | 0 | 0 | 0 |
| **aggregate** | med 1, max 3 | - | - | max 3 | med 0, max 2 |

## H5 / H6 scorecard (pre-registered; scored on C1-C3 only)

**H5 eligibility:** trajectories whose critical interval brackets the dt median (1.53 s): astropy-13398, astropy-14309, astropy-7671 (3/20).

| Trajectory | condition | median crossings | flicker (>2)? |
|---|---|---|---|
| astropy-13398 | C2 | 1 | no |
| astropy-13398 | C3 | 1 | no |
| astropy-14309 | C2 | 0 | no |
| astropy-14309 | C3 | 0 | no |
| astropy-7671 | C2 | 1 | no |
| astropy-7671 | C3 | 1 | no |

**H5: NOT SUPPORTED** -- no bracketed trajectory shows median crossings > 2 under C2/C3.

**H6: SUPPORTED** -- T3 net fire count <= 3 in every (trajectory x condition x seed) cell of C1-C3.

## Falsification clause outcome

Per-trajectory under C3 (real bursts): **19/20 trajectories are clean single-crossing accumulators** (median crossings <= 1 and median flicker 0 over the 5 real sequences).

Exceptions:
- astropy-13236: median crossings 2, median flicker 1 (per-sequence crossings [2, 1, 1, 2, 2], flicker [1, 0, 0, 1, 1]). This is a boundary double-crossing -- the trajectory hovers near 0.7 when a ~16 s gap (the runE heavy step) lands, dips under, and re-crosses. It does not meet H5's flicker bar (> 2 crossings).

**Verdict on the committed clause:** at measured cadence A6 is, to within one marginal boundary case, a single-crossing accumulator -- so the knife-edge/bistability framing in the paper's §4-5 **is softened to 'regime-dependent'**: the accumulator regime governs at measured cadence (C1-C3), and multi-crossing/flicker appears only when the latency distribution overlaps the critical band (exploratory C4 below shows exactly that, on 9/20 trajectories). The single C3 exception is the direct, if marginal, demonstration that the firing pattern is latency-sequence-dependent at the regime boundary.

## C4 exploratory reading (not confirmatory)

With the same burst shapes shifted into each trajectory's critical band, **9/20 trajectories show multi-crossing or flicker** (median crossings across trajectories 1.0, max per-sequence crossings 4; median flicker 0.0, max 3). Max T3 net = 3 -- T3's <= 3 bound holds even here, beyond its pre-registered scope. Reading: the knife-edge is REAL once cadence overlaps the critical band, but it is bounded re-crossing (<= 4), not wild oscillation; combined with C3 this cleanly separates 'mechanism exists' (C4) from 'regime not reached at measured cadence' (C1-C3).

Figure data: `fig_data/flicker_traces.csv` (frustration + dt traces for astropy-13398 and astropy-13033 under C3 and C4, runE-derived sequence).