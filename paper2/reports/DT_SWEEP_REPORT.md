# dt Sweep Report (Phase 3)

Counterfactual: the published saturation result used a replay pipeline that passes `dt=0` to the engine, so exponential decay never ran (`DT_AUDIT.md`). Here we inject a synthetic, uniform inter-action time `dt` before each action via an explicit `engine._tick_decay(dt)` from the replay caller (heart_core unmodified), then re-evaluate the same unchanged A6 and T1-T4 triggers.

Pre-registered dt grid (seconds): [0, 1, 5, 15, 30, 60, 150, 300, 600]. 150 s = the frustration half-life; 600 s = 4 half-lives. **Decay-at-dt includes the engine's momentum modulation** (trend > 0.04 slows decay x0.85; trend < -0.04 accelerates x1.15); it is left active as part of the model under test.

Saturation persistence = of the actions at/after frustration first reaches 0.7, the % still >= 0.7. T3 (saturation_entry) uses rising-edge + hysteresis, so it can fire more than once if decay pulls frustration below 0.5 and it re-crosses 0.7; the gross and net-of-cooldown counts are both shown.

## astropy-12907

| dt (s) | max frust | crosses 0.7 | first cross | persistence % | A6 sustained_frust | T3 gross | T3 net |
|---|---|---|---|---|---|---|---|
| 0 | 1.000 | yes | 17 | 100.0 | 11 | 1 | 1 |
| 1 | 0.962 | yes | 17 | 100.0 | 11 | 1 | 1 |
| 5 | 0.844 | yes | 18 | 100.0 | 10 | 1 | 1 |
| 15 | 0.695 | no | - | - | 0 | 0 | 0 |
| 30 | 0.565 | no | - | - | 0 | 0 | 0 |
| 60 | 0.425 | no | - | - | 0 | 0 | 0 |
| 150 | 0.294 | no | - | - | 0 | 0 | 0 |
| 300 | 0.251 | no | - | - | 0 | 0 | 0 |
| 600 | 0.250 | no | - | - | 0 | 0 | 0 |

## astropy-13033

| dt (s) | max frust | crosses 0.7 | first cross | persistence % | A6 sustained_frust | T3 gross | T3 net |
|---|---|---|---|---|---|---|---|
| 0 | 1.000 | yes | 12 | 100.0 | 47 | 1 | 1 |
| 1 | 1.000 | yes | 12 | 100.0 | 47 | 1 | 1 |
| 5 | 1.000 | yes | 12 | 100.0 | 47 | 1 | 1 |
| 15 | 0.877 | yes | 18 | 63.4 | 26 | 2 | 2 |
| 30 | 0.593 | no | - | - | 0 | 0 | 0 |
| 60 | 0.428 | no | - | - | 0 | 0 | 0 |
| 150 | 0.305 | no | - | - | 0 | 0 | 0 |
| 300 | 0.267 | no | - | - | 0 | 0 | 0 |
| 600 | 0.253 | no | - | - | 0 | 0 | 0 |

## astropy-13236

| dt (s) | max frust | crosses 0.7 | first cross | persistence % | A6 sustained_frust | T3 gross | T3 net |
|---|---|---|---|---|---|---|---|
| 0 | 1.000 | yes | 21 | 100.0 | 23 | 1 | 1 |
| 1 | 1.000 | yes | 22 | 100.0 | 22 | 1 | 1 |
| 5 | 1.000 | yes | 28 | 100.0 | 16 | 1 | 1 |
| 15 | 0.759 | yes | 39 | 60.0 | 3 | 1 | 1 |
| 30 | 0.530 | no | - | - | 0 | 0 | 0 |
| 60 | 0.386 | no | - | - | 0 | 0 | 0 |
| 150 | 0.291 | no | - | - | 0 | 0 | 0 |
| 300 | 0.263 | no | - | - | 0 | 0 | 0 |
| 600 | 0.253 | no | - | - | 0 | 0 | 0 |

## astropy-13398

| dt (s) | max frust | crosses 0.7 | first cross | persistence % | A6 sustained_frust | T3 gross | T3 net |
|---|---|---|---|---|---|---|---|
| 0 | 1.000 | yes | 15 | 100.0 | 41 | 1 | 1 |
| 1 | 1.000 | yes | 15 | 100.0 | 41 | 1 | 1 |
| 5 | 0.789 | yes | 15 | 36.6 | 15 | 2 | 2 |
| 15 | 0.691 | no | - | - | 0 | 0 | 0 |
| 30 | 0.578 | no | - | - | 0 | 0 | 0 |
| 60 | 0.438 | no | - | - | 0 | 0 | 0 |
| 150 | 0.295 | no | - | - | 0 | 0 | 0 |
| 300 | 0.263 | no | - | - | 0 | 0 | 0 |
| 600 | 0.253 | no | - | - | 0 | 0 | 0 |

## astropy-13453

| dt (s) | max frust | crosses 0.7 | first cross | persistence % | A6 sustained_frust | T3 gross | T3 net |
|---|---|---|---|---|---|---|---|
| 0 | 1.000 | yes | 13 | 100.0 | 18 | 1 | 1 |
| 1 | 1.000 | yes | 13 | 100.0 | 18 | 1 | 1 |
| 5 | 1.000 | yes | 13 | 100.0 | 18 | 1 | 1 |
| 15 | 0.949 | yes | 14 | 70.6 | 12 | 1 | 1 |
| 30 | 0.788 | yes | 14 | 17.6 | 3 | 1 | 1 |
| 60 | 0.678 | no | - | - | 0 | 0 | 0 |
| 150 | 0.538 | no | - | - | 0 | 0 | 0 |
| 300 | 0.439 | no | - | - | 0 | 0 | 0 |
| 600 | 0.375 | no | - | - | 0 | 0 | 0 |

## Summary: trap persistence by dt

For each dt: mean persistence over the trajectories that cross 0.7 (trajectories that never cross are excluded from the mean and counted separately), and the number of trajectories (of 5) where the trap fully holds (persistence >= 90%).

| dt (s) | trajectories crossing 0.7 | mean persistence % (of crossers) | # trap fully holds (>=90%) |
|---|---|---|---|
| 0 | 5/5 | 100.0 | 5 |
| 1 | 5/5 | 100.0 | 5 |
| 5 | 5/5 | 87.3 | 4 |
| 15 | 3/5 | 64.7 | 0 |
| 30 | 1/5 | 17.6 | 0 |
| 60 | 0/5 | - | 0 |
| 150 | 0/5 | - | 0 |
| 300 | 0/5 | - | 0 |
| 600 | 0/5 | - | 0 |

## Summary: critical dt per trajectory

Smallest grid dt at which persistence drops below 50% (including dt where frustration never crosses 0.7, treated as persistence 0). 'never' = persistence stayed >= 50% through dt=600.

| Trajectory | critical dt (s) |
|---|---|
| astropy-12907 | 15 |
| astropy-13033 | 30 |
| astropy-13236 | 30 |
| astropy-13398 | 5 |
| astropy-13453 | 30 |

## What this does and does not show

1. The `dt` values here are synthetic and uniform; the real inter-action wall-clock times for these SWE-bench traces are unknown and not recorded in the trace files. 2. The sweep tests the State Saturation Trap's sensitivity to the engine's decay term, not to real agent timing. 3. At `dt=0` the result reproduces the published pure-accumulator behavior exactly (byte-equivalent artifacts); as `dt` grows, decay competes with event-driven accumulation. 4. Any statement about a 'realistic cadence' requires an explicit assumption about agent action latency. 5. As a stated assumption, not a measurement: typical tool-call round-trips are on the order of seconds to tens of seconds, which is far below the 150 s frustration half-life. 6. Under that assumption the relevant grid region is roughly `dt` in [1, 30] s, and the numbers for that region are in the tables above; we do not collapse them into a single headline. 7. The decay includes momentum modulation, so the mapping from `dt` to persistence is not a plain exponential and is trajectory-dependent. 8. Persistence is measured only from the first crossing onward; a trajectory that never crosses contributes no persistence value (and is excluded from the mean-of-crossers). 9. No threshold was changed and no `dt` value outside the pre-registered grid was evaluated. 10. These artifacts support a sensitivity figure; they are not evidence about what any real agent's timing was.
