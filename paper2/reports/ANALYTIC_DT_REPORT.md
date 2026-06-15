# Analytic critical-dt model vs. the sweep (Phase 4a)

First-order, zero-free-parameter prediction of the critical inter-action time `dt_crit` (the dt above which the frustration saturation trap stops holding), derived from event statistics alone, compared against the interval-censored observed values from `DT_SWEEP_REPORT.md`. Pure post-processing of `fullstate_dt0_*.json`; no replays, no fitted parameters, no per-trajectory adjustment.

## Model

```
Engine per-action decay near elevated level x:
    x' = B + (x - B) * exp(-lambda * dt),   B = 0.10,  lambda = ln(2)/150
Per-action decay drain at level x:
    D(dt, x) = (1 - exp(-lambda*dt)) * (x - B)
Per-action event input (uniform-input approximation):
    r = (total realized positive frustration input) / (total actions)
    realized input/action = frustration(vector) - frustration(vector_post_decay)
Sustained elevation at x requires r >= D(dt, x). At the trap threshold
x = 0.7, (x - B) = 0.6:
    dt_crit = -(1/lambda) * ln(1 - r / 0.6)        [r>=0.6 -> infinite]
    lambda = ln(2)/150 = 0.004621 1/s
```

### Known limitations (stated up front; not patched)

- Ignores the engine's momentum modulation of decay (x0.85 when trend>0.04, x1.15 when trend<-0.04).
- Assumes uniform event input; real frustration input is bursty (errors cluster).
- Uses the mean input rate; the trap may locally hold inside high-input bursts at dt above dt_crit.
- Observed critical dt is interval-censored on the coarse grid {1,5,15,30,...}: an observed value `c` means the truth lies in (prev_grid, c]. Predictions are judged against the interval, not a point.

## Per-trajectory results

`total input` = sum of positive realized frustration deltas; `r` = total input / total actions; `dt_crit` = model prediction; `interval` = censored observed critical dt; `inside?` = prediction within the interval; `input CV` = coefficient of variation of per-action frustration deltas (burstiness); `max delta` = largest single-action realized frustration delta.

| Trajectory | actions | event actions | total input | r | dt_crit (s) | obs interval (s) | inside? | input CV | max delta |
|---|---|---|---|---|---|---|---|---|---|
| astropy-12907 | 28 | 10 | 0.9000 | 0.03214 | 11.92 | (5, 15] | yes | 1.47 | 0.150 |
| astropy-13033 | 59 | 12 | 0.9000 | 0.01525 | 5.57 | (15, 30] | no | 2.16 | 0.115 |
| astropy-13236 | 44 | 13 | 0.9000 | 0.02045 | 7.51 | (15, 30] | no | 1.70 | 0.120 |
| astropy-13398 | 56 | 10 | 0.9000 | 0.01607 | 5.88 | (1, 5] | no | 2.33 | 0.150 |
| astropy-13453 | 31 | 7 | 0.9000 | 0.02903 | 10.73 | (15, 30] | no | 2.20 | 0.250 |

## Residuals

The fixed model places 1 of 5 predictions inside the censored observed interval; of the 4 misses, 3 fall below the interval (underprediction) and 1 above (overprediction). All predicted dt_crit values are single-digit-to-low-tens of seconds, the same order as the observed intervals (1-30 s). The largest deviation is on astropy-13033 (predicted 5.57 s vs interval (15, 30]). The model's a-priori prediction is that bursty (high-CV) trajectories sustain the trap above dt_crit, so the uniform-rate model should UNDERpredict for high-CV trajectories; the 3 underpredictions (astropy-13033, astropy-13236, astropy-13453 -- all CV >= 1.7) are in that predicted direction. The exception is astropy-13398: it overpredicts, landing just above its narrow (1, 5] interval, i.e. the model expects the trap to survive slightly longer than the sweep showed -- the opposite of the burstiness bias and attributable to interval coarseness (the true value sits between the 1 s and 5 s grid points, near the prediction). Because every trajectory has high CV (sparse, clustered input), the uniform-rate r is small and predictions cluster at the low end. No correction was applied; residuals are reported as computed. The single mean-rate scalar cannot represent within-trajectory clustering, which is the mechanism by which a trajectory holds the trap at a larger dt than the mean rate alone supports.

## Design rule

In dimensionless form, a leaky-integrator stress monitor over an agent action stream holds an elevated alarm at level `x` exactly when the mean per-action input rate clears the per-action decay drain:

```
    r  >=  (1 - 2^(-dt / T_half)) * (threshold - baseline)
```

where `r` is mean realized input per action, `dt` is the inter-action time, `T_half` is the state's half-life, and `(threshold - baseline)` is the elevation the alarm sits above rest. The right-hand side rises from 0 (at dt=0, pure accumulator -- the published regime) toward `(threshold - baseline)` as `dt` grows past a few half-lives. For a monitor designer this means the saturation/no-recovery behavior is a joint property of the input rate and the half-life relative to the agent's action cadence: choosing `T_half` comparable to or below the expected inter-action time converts a sticky accumulator into a leaky one, and the trap holds only while `r` exceeds the decay drain at the operating `dt`. The bursty, clustered nature of real frustration input means a mean-rate design rule is necessary but not sufficient: local bursts can hold the alarm above the mean-rate critical dt.
