# Scale Report: ~20 trajectories (Phase 5)

Expanded set: 20 trajectories (original 5 + 15 batch2 from the same public 20250514_aime_coder submission, selected a priori: first 15 alphabetical with 25-70 actions that parse cleanly; see `batch2/SKIP_LOG.md`). Engine, adapter, triggers, thresholds, and dt grid all unchanged. Pure re-run of the existing pipeline.

## Consistency check (Task 4a): original 5 unchanged

| item | expected | got | match |
|---|---|---|---|
| astropy-12907 | (28, 17, 11, 12, 11) | (28, 17, 11, 12, 11) | PASS |
| astropy-12907 crit_dt | 15 | 15 | PASS |
| astropy-13033 | (59, 12, 47, 49, 48) | (59, 12, 47, 49, 48) | PASS |
| astropy-13033 crit_dt | 30 | 30 | PASS |
| astropy-13236 | (44, 21, 23, 30, 17) | (44, 21, 23, 30, 17) | PASS |
| astropy-13236 crit_dt | 30 | 30 | PASS |
| astropy-13398 | (56, 15, 41, 42, 42) | (56, 15, 41, 42, 42) | PASS |
| astropy-13398 crit_dt | 5 | 5 | PASS |
| astropy-13453 | (31, 13, 18, 18, 18) | (31, 13, 18, 18, 18) | PASS |
| astropy-13453 crit_dt | 30 | 30 | PASS |

**All original-5 assertions PASS.**

## Saturation table (dt=0, all trajectories)

| Trajectory | actions | first cross 0.7 | persistence % | A6 sf % | A6 sva % | A6 hc % | max frust |
|---|---|---|---|---|---|---|---|
| astropy-12907 | 28 | 17 | 100 | 39 | 43 | 39 | 1.00 |
| astropy-13033 | 59 | 12 | 100 | 80 | 83 | 81 | 1.00 |
| astropy-13236 | 44 | 21 | 100 | 52 | 68 | 39 | 1.00 |
| astropy-13398 | 56 | 15 | 100 | 73 | 75 | 75 | 1.00 |
| astropy-13453 | 31 | 13 | 100 | 58 | 58 | 58 | 1.00 |
| astropy-14096 | 27 | 16 | 100 | 41 | 59 | 56 | 1.00 |
| astropy-14182 | 35 | 7 | 100 | 80 | 83 | 74 | 1.00 |
| astropy-14309 | 28 | 23 | 100 | 18 | 29 | 0 | 0.76 |
| astropy-14369 | 55 | 15 | 100 | 73 | 75 | 69 | 1.00 |
| astropy-14508 | 25 | 14 | 100 | 44 | 60 | 60 | 1.00 |
| astropy-7336 | 28 | 9 | 100 | 68 | 71 | 68 | 1.00 |
| astropy-7671 | 27 | 15 | 100 | 44 | 48 | 26 | 0.91 |
| astropy-8707 | 40 | 11 | 100 | 72 | 82 | 82 | 1.00 |
| astropy-8872 | 33 | 22 | 100 | 33 | 48 | 33 | 1.00 |
| django-10097 | 34 | 12 | 100 | 65 | 68 | 65 | 1.00 |
| django-10554 | 32 | 10 | 100 | 69 | 72 | 66 | 1.00 |
| django-10914 | 33 | 15 | 100 | 55 | 73 | 73 | 1.00 |
| django-10973 | 31 | 14 | 100 | 55 | 58 | 55 | 1.00 |
| django-11087 | 38 | 7 | 100 | 82 | 82 | 82 | 1.00 |
| django-11095 | 30 | 17 | 100 | 43 | 57 | 23 | 1.00 |

Cross 0.7 at dt=0: **20/20**. Persistence >= 90% (trap fully holds at dt=0): **20/20**.

## dt-sweep persistence summary (all trajectories)

| dt (s) | trajectories crossing 0.7 | mean persistence % (crossers) | # trap holds (>=90%) |
|---|---|---|---|
| 0 | 20/20 | 100.0 | 20 |
| 1 | 20/20 | 100.0 | 20 |
| 5 | 19/20 | 93.4 | 17 |
| 15 | 14/20 | 63.4 | 2 |
| 30 | 5/20 | 15.6 | 0 |
| 60 | 1/20 | 2.6 | 0 |
| 150 | 0/20 | - | 0 |
| 300 | 0/20 | - | 0 |
| 600 | 0/20 | - | 0 |

## Per-trajectory critical-dt interval

| Trajectory | critical dt interval (s) |
|---|---|
| astropy-12907 | (5, 15] |
| astropy-13033 | (15, 30] |
| astropy-13236 | (15, 30] |
| astropy-13398 | (1, 5] |
| astropy-13453 | (15, 30] |
| astropy-14096 | (5, 15] |
| astropy-14182 | (5, 15] |
| astropy-14309 | (1, 5] |
| astropy-14369 | (5, 15] |
| astropy-14508 | (5, 15] |
| astropy-7336 | (15, 30] |
| astropy-7671 | (1, 5] |
| astropy-8707 | (15, 30] |
| astropy-8872 | (15, 30] |
| django-10097 | (5, 15] |
| django-10554 | (15, 30] |
| django-10914 | (15, 30] |
| django-10973 | (5, 15] |
| django-11087 | (5, 15] |
| django-11095 | (15, 30] |

## A6 and T3 fire counts vs dt (aggregate bands over all trajectories)

min / median / max fire count across the trajectories at each dt.

| dt (s) | A6 sf min/med/max | T3 net min/med/max |
|---|---|---|
| 0 | 5/18/47 | 1/1/1 |
| 1 | 3/18/47 | 1/1/1 |
| 5 | 0/16/47 | 0/1/2 |
| 15 | 0/4/28 | 0/1/2 |
| 30 | 0/0/5 | 0/0/1 |
| 60 | 0/0/1 | 0/0/1 |
| 150 | 0/0/0 | 0/0/0 |
| 300 | 0/0/0 | 0/0/0 |
| 600 | 0/0/0 | 0/0/0 |

## Zero-signal coverage (dt=0)

| Trajectory | actions | zero-signal % | longest zero run |
|---|---|---|---|
| astropy-12907 | 28 | 57.1 | 5 |
| astropy-13033 | 59 | 25.4 | 5 |
| astropy-13236 | 44 | 50.0 | 3 |
| astropy-13398 | 56 | 78.6 | 10 |
| astropy-13453 | 31 | 58.1 | 5 |
| astropy-14096 | 27 | 48.1 | 3 |
| astropy-14182 | 35 | 51.4 | 6 |
| astropy-14309 | 28 | 60.7 | 4 |
| astropy-14369 | 55 | 43.6 | 6 |
| astropy-14508 | 25 | 52.0 | 5 |
| astropy-7336 | 28 | 35.7 | 3 |
| astropy-7671 | 27 | 51.9 | 3 |
| astropy-8707 | 40 | 37.5 | 4 |
| astropy-8872 | 33 | 54.5 | 4 |
| django-10097 | 34 | 55.9 | 10 |
| django-10554 | 32 | 43.8 | 3 |
| django-10914 | 33 | 45.5 | 3 |
| django-10973 | 31 | 61.3 | 5 |
| django-11087 | 38 | 57.9 | 7 |
| django-11095 | 30 | 43.3 | 2 |

## EXPLORATORY: pre-saturation r correction (Task 3)

**This correction was specified AFTER observing the original model's residuals (Phase 4a).** It is exploratory, not pre-registered. The original `r` averages realized frustration input over ALL actions, but once frustration hits the 1.0 clamp the realized input is censored to 0, deflating `r`. The corrected `r_presat` averages realized positive input over the PRE-saturation region only (actions before frustration first reaches 1.0; whole trajectory if it never clamps). dt_crit uses the same fixed formula `-(1/lambda) ln(1 - r/0.6)`.

| Trajectory | r (orig) | dt_crit orig | r_presat | dt_crit corr | obs interval | orig inside? | corr inside? | clamp-censored input % |
|---|---|---|---|---|---|---|---|---|
| astropy-12907 | 0.0321 | 11.9 | 0.0418 | 15.6 | (5, 15] | yes | no | 0% |
| astropy-13033 | 0.0153 | 5.6 | 0.0537 | 20.3 | (15, 30] | no | yes | 67% |
| astropy-13236 | 0.0205 | 7.5 | 0.0279 | 10.3 | (15, 30] | no | no | 40% |
| astropy-13398 | 0.0161 | 5.9 | 0.0294 | 10.9 | (1, 5] | no | no | 14% |
| astropy-13453 | 0.0290 | 10.7 | 0.0505 | 19.0 | (15, 30] | no | yes | 31% |
| astropy-14096 | 0.0333 | 12.4 | 0.0430 | 16.1 | (5, 15] | yes | no | 14% |
| astropy-14182 | 0.0257 | 9.5 | 0.0654 | 25.0 | (5, 15] | yes | no | 28% |
| astropy-14309 | 0.0235 | 8.6 | 0.0235 | 8.6 | (1, 5] | no | no | 0%* |
| astropy-14369 | 0.0164 | 6.0 | 0.0542 | 20.5 | (5, 15] | yes | no | 56% |
| astropy-14508 | 0.0360 | 13.4 | 0.0474 | 17.8 | (5, 15] | yes | no | 5% |
| astropy-7336 | 0.0321 | 11.9 | 0.0780 | 30.1 | (15, 30] | no | no | 44% |
| astropy-7671 | 0.0299 | 11.1 | 0.0299 | 11.1 | (1, 5] | no | no | 0%* |
| astropy-8707 | 0.0225 | 8.3 | 0.0688 | 26.4 | (15, 30] | no | yes | 61% |
| astropy-8872 | 0.0273 | 10.1 | 0.0330 | 12.2 | (15, 30] | no | no | 25% |
| django-10097 | 0.0265 | 9.8 | 0.0568 | 21.5 | (5, 15] | yes | no | 31% |
| django-10554 | 0.0281 | 10.4 | 0.0735 | 28.3 | (15, 30] | no | yes | 53% |
| django-10914 | 0.0273 | 10.1 | 0.0445 | 16.7 | (15, 30] | no | yes | 47% |
| django-10973 | 0.0290 | 10.7 | 0.0355 | 13.2 | (5, 15] | yes | yes | 5% |
| django-11087 | 0.0237 | 8.7 | 0.0501 | 18.9 | (5, 15] | yes | no | 38% |
| django-11095 | 0.0300 | 11.1 | 0.0361 | 13.4 | (15, 30] | no | no | 25% |

Predictions inside the observed interval: original **8/20**, corrected **6/20**. `*` = no clamp reached, whole trajectory used for r_presat.

## Distribution check (Task 4b): batch2 vs original 5

min/median/max per group. event-rate = % of actions with >=1 signal.

| group | n | action-count | zero-signal % | event-rate % |
|---|---|---|---|---|
| original 5 | 5 | 28/44/59 | 25/57/79 | 21/43/75 |
| batch2 (15) | 15 | 25/32/55 | 36/51/61 | 39/49/64 |
| all 20 | 20 | 25/32/59 | 25/52/79 | 21/48/75 |

No reweighting applied; distributions reported as-is to show whether the pilot 5 were representative of the broader set.
