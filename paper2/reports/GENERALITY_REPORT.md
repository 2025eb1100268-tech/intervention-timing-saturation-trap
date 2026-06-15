# Generality sweep (Phase 8): HEART-free instruments on the error stream

Pre-registered: `PREREGISTRATION_PHASE8.md` (committed before running). Pure post-processing of per-action `has_error`; no heart_* imports. I1: wall-clock leaky accumulator (lambda=ln2/150, step 0.15, level 0.7, edge re-arm 0.5). I2: sample-time CUSUM (k=0.1, h=1.0).

`has_error` invariance check (assumption): verified identical across all 9 dt-variant fullstate files for astropy-13398 and astropy-13033 before running — PASS (dt does not change which actions error).

## Error-stream statistics (the instruments' input)

| Trajectory | actions | errors | error rate | longest error-free run |
|---|---|---|---|---|
| astropy-12907 | 28 | 6 | 0.21 | 13 |
| astropy-13033 | 59 | 38 | 0.64 | 7 |
| astropy-13236 | 44 | 18 | 0.41 | 9 |
| astropy-13398 | 56 | 5 | 0.09 | 17 |
| astropy-13453 | 31 | 8 | 0.26 | 8 |
| astropy-14096 | 27 | 9 | 0.33 | 6 |
| astropy-14182 | 35 | 9 | 0.26 | 14 |
| astropy-14309 | 28 | 9 | 0.32 | 7 |
| astropy-14369 | 55 | 23 | 0.42 | 6 |
| astropy-14508 | 25 | 5 | 0.20 | 11 |
| astropy-7336 | 28 | 10 | 0.36 | 8 |
| astropy-7671 | 27 | 8 | 0.30 | 5 |
| astropy-8707 | 40 | 16 | 0.40 | 11 |
| astropy-8872 | 33 | 12 | 0.36 | 7 |
| django-10097 | 34 | 10 | 0.29 | 10 |
| django-10554 | 32 | 12 | 0.38 | 8 |
| django-10914 | 33 | 10 | 0.30 | 8 |
| django-10973 | 31 | 7 | 0.23 | 8 |
| django-11087 | 38 | 13 | 0.34 | 12 |
| django-11095 | 30 | 14 | 0.47 | 7 |

## Table A: I1 level trigger vs dt

| dt (s) | trajectories crossing 0.7 | mean persistence % (crossers) | # trap holds (>=90%) | fire count med (min-max) |
|---|---|---|---|---|
| 0 | 20/20 | 100.0 | 20 | 18 (7-45) |
| 1 | 19/20 | 99.4 | 18 | 18 (0-45) |
| 5 | 17/20 | 95.3 | 15 | 14 (0-44) |
| 15 | 15/20 | 70.0 | 8 | 6 (0-43) |
| 30 | 7/20 | 41.7 | 0 | 0 (0-31) |
| 60 | 0/20 | - | 0 | 0 (0-0) |
| 150 | 0/20 | - | 0 | 0 (0-0) |
| 300 | 0/20 | - | 0 | 0 (0-0) |
| 600 | 0/20 | - | 0 | 0 (0-0) |

## Table B: critical-dt interval — I1 vs HEART

| Trajectory | I1 interval (s) | HEART interval (s) |
|---|---|---|
| astropy-12907 | (1, 5] | (5, 15] |
| astropy-13033 | (30, 60] | (15, 30] |
| astropy-13236 | (30, 60] | (15, 30] |
| astropy-13398 | (0, 1] | (1, 5] |
| astropy-13453 | (5, 15] | (15, 30] |
| astropy-14096 | (15, 30] | (5, 15] |
| astropy-14182 | (5, 15] | (5, 15] |
| astropy-14309 | (15, 30] | (1, 5] |
| astropy-14369 | (15, 30] | (5, 15] |
| astropy-14508 | (1, 5] | (5, 15] |
| astropy-7336 | (5, 15] | (15, 30] |
| astropy-7671 | (5, 15] | (1, 5] |
| astropy-8707 | (15, 30] | (15, 30] |
| astropy-8872 | (15, 30] | (15, 30] |
| django-10097 | (5, 15] | (5, 15] |
| django-10554 | (15, 30] | (15, 30] |
| django-10914 | (15, 30] | (15, 30] |
| django-10973 | (5, 15] | (5, 15] |
| django-11087 | (15, 30] | (5, 15] |
| django-11095 | (30, 60] | (15, 30] |

Spearman correlation (upper endpoints; 'never' ranked above 600): **rho = 0.530**. Both instruments are driven by event sparsity, so positive correlation is expected; reported either way per the preregistration.

## Table C: I2 sample-time CUSUM — dt-invariance check

| Trajectory | identical fire pattern across all 9 dt? | fires at dt=0 |
|---|---|---|
| astropy-12907 | PASS | 24 |
| astropy-13033 | PASS | 56 |
| astropy-13236 | PASS | 30 |
| astropy-13398 | PASS | 28 |
| astropy-13453 | PASS | 27 |
| astropy-14096 | PASS | 23 |
| astropy-14182 | PASS | 32 |
| astropy-14309 | PASS | 25 |
| astropy-14369 | PASS | 48 |
| astropy-14508 | PASS | 9 |
| astropy-7336 | PASS | 25 |
| astropy-7671 | PASS | 23 |
| astropy-8707 | PASS | 36 |
| astropy-8872 | PASS | 21 |
| django-10097 | PASS | 32 |
| django-10554 | PASS | 28 |
| django-10914 | PASS | 21 |
| django-10973 | PASS | 19 |
| django-11087 | PASS | 34 |
| django-11095 | PASS | 19 |

## Table D: I1 edge trigger fires vs dt

| dt (s) | min | median | max |
|---|---|---|---|
| 0 | 1 | 1 | 1 |
| 1 | 0 | 1 | 1 |
| 5 | 0 | 1 | 1 |
| 15 | 0 | 1 | 2 |
| 30 | 0 | 0 | 2 |
| 60 | 0 | 0 | 0 |
| 150 | 0 | 0 | 0 |
| 300 | 0 | 0 | 0 |
| 600 | 0 | 0 | 0 |

## H7 / H8 / H9 scorecard

- dt=0: 20/20 crossers hold >=90% -> PASS
- dt=1: 18/19 crossers hold >=90% -> PASS
- dt=60: 20/20 never reach 0.7 (need >=18) -> PASS
- dt=150: 20/20 never reach 0.7 (need >=18) -> PASS
- dt=300: 20/20 never reach 0.7 (need >=18) -> PASS
- dt=600: 20/20 never reach 0.7 (need >=18) -> PASS
- critical intervals in (1,30]: 16/20 (outside: [('astropy-13033', (30, 60)), ('astropy-13236', (30, 60)), ('astropy-13398', (0, 1)), ('django-11095', (30, 60))]) -> FAIL

**H7 (two-regime structure in I1): NOT FULLY SUPPORTED**

**H8 (I2 exact dt-invariance): SUPPORTED**

**H9 (I1 edge <= 3 fires everywhere): SUPPORTED**

## Falsification clause outcome

The committed falsification trigger did **NOT** occur: I1 shows both regimes unambiguously (alarm regime: 20/20 cross at dt=0 with 100% mean persistence; dead regime: 20/20 never reach 0.7 at every dt >= 60). The **two-regime structure replicates in the HEART-free instrument**, and I2's exact dt-invariance (H8) confirms the effect enters purely through the wall-clock decay term.

**Scope caveat carried from H7:** H7 as committed was a three-part conjunction, and its third sub-criterion (every critical interval inside (1, 30]) failed on 4/20 trajectories -- all in bins ADJACENT to the band (three at (30, 60], one at (0, 1]). The accurate class-level statement is therefore: cadence bistability is a property of wall-clock-calibrated leaky integrators sampled at agent cadence, with the critical band's exact placement depending on the input stream and step size -- I1's band ((0, 60]) is the same order of magnitude as HEART's ((1, 30]) but not bin-identical (Spearman rho between per-trajectory critical dts reported in Table B). H7 is scored NOT FULLY SUPPORTED on its strict band clause; the falsification clause is not triggered.
