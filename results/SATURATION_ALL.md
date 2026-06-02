# State Saturation Trap — all five pilot trajectories

State/firing-rate analysis only. No human labels, no F1. Each trajectory replayed through the unmodified engine + observer + A6 triggers (`scripts/saturation_replay.py`), thresholds and engine constants untouched. Frustration is clamped to [0,1]; the threshold of interest is 0.7 (`SUSTAINED_FRUSTRATION_THRESHOLD`). The accumulator is the sum of five negative-arousal emotions (frustration + anger + fear + confusion + vengeance), range [0,5], gated at 1.5 by `same_valence_accumulation`.

## Summary table

| Trajectory | Actions | First crosses 0.7 | Stays saturated | Max frust | sustained_frust % | same_valence % | high_confusion % | Accumulator max |
|---|---|---|---|---|---|---|---|---|
| astropy-13033 | 59 | action 12 | yes | 1.00 | 47/59 = 79.7% | 49/59 = 83.1% | 48/59 = 81.4% | 3.200 |
| astropy-13398 | 56 | action 15 | yes | 1.00 | 41/56 = 73.2% | 42/56 = 75.0% | 42/56 = 75.0% | 2.500 |
| astropy-13236 | 44 | action 21 | yes | 1.00 | 23/44 = 52.3% | 30/44 = 68.2% | 17/44 = 38.6% | 3.085 |
| astropy-13453 | 31 | action 13 | yes | 1.00 | 18/31 = 58.1% | 18/31 = 58.1% | 18/31 = 58.1% | 2.550 |
| astropy-12907 | 28 | action 17 | yes | 1.00 | 11/28 = 39.3% | 12/28 = 42.9% | 11/28 = 39.3% | 2.550 |

## Consistency check (previously recorded trajectories)

| Trajectory | first-cross | rates sustained/same_valence/high_confusion | result |
|---|---|---|---|
| astropy__astropy-13033 | first-cross 12 (exp 12) | 79.7/83.1/81.4% (exp 79.7/83.1/81.4) | PASS |
| astropy__astropy-13398 | first-cross 15 (exp 15) | 73.2/75.0/75.0% (exp 73.2/75.0/75.0) | PASS |

**All consistency checks PASS.**

## Plain-language reading

Of the 5 pilot trajectories, **5 saturate**: frustration crosses 0.7 and then stays at or above it through the final action. First-crossing points: 13033 at action 12 (of 59), 13398 at action 15 (of 56), 13236 at action 21 (of 44), 13453 at action 13 (of 31), 12907 at action 17 (of 28). No trajectory breaks the pattern: the State Saturation Trap reproduces on all 5 pilot trajectories (n=5, up from the n=2 in the paper draft). sustained_frustration firing rates span 39.3%–79.7% across the five; the shorter trajectories sit lower simply because the pre-saturation prefix is a larger fraction of a short run, not because the mechanism differs.

## Notes

- No engine, trigger, threshold, adapter, or label code modified; `scripts/saturation_replay.py` run unmodified per trajectory.
- No human labels used; no F1/precision/recall computed (no labels exist for 12907 / 13236 / 13453).
- 'Stays saturated' requires frustration >= 0.7 at every action from the first crossing to the end (strict).