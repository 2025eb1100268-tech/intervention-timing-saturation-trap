# Transition Trigger Report (Phase 2)

Transition triggers T1-T4 evaluated through the cooldown wrapper (REFRACTORY_ACTIONS=5), persisted in `fullstate_<id>.json` (schema 1.2). Gross = pre-cooldown firings; net = post-cooldown (non-suppressed) firings. A6 fire counts shown alongside for comparison. Numbers only.

Triggers: T1 velocity_spike (pause), T2 acceleration_onset (reflect), T3 saturation_entry (pause, rising-edge+hysteresis), T4 plateau_no_recovery (reflect).

## Per-trajectory fire counts

| Trajectory | actions | T1 g/n | T2 g/n | T3 g/n | T4 g/n | A6 sf | A6 sva | A6 hc |
|---|---|---|---|---|---|---|---|---|
| astropy-12907 | 28 | 4/1 | 0/0 | 1/1 | 7/2 | 11 | 12 | 11 |
| astropy-13033 | 59 | 4/1 | 0/0 | 1/1 | 30/5 | 47 | 49 | 48 |
| astropy-13236 | 44 | 3/2 | 0/0 | 1/1 | 8/4 | 23 | 30 | 17 |
| astropy-13398 | 56 | 4/1 | 0/0 | 1/1 | 36/7 | 41 | 42 | 42 |
| astropy-13453 | 31 | 2/1 | 0/0 | 1/1 | 13/3 | 18 | 18 | 18 |

## Degenerate-behavior flags (pre-registered invariant 4)

Reported, not fixed. 'Zero fires' = 0 gross firings across all trajectories; '>50% fire rate' = gross fires on >50% of a trajectory's actions.

- **acceleration_onset**: 0 gross firings across all 5 trajectories (ZERO-FIRE degenerate).
- **plateau_no_recovery** on astropy__astropy-13033: 30/59 = 50.8% gross fire rate (>50% degenerate).
- **plateau_no_recovery** on astropy__astropy-13398: 36/56 = 64.3% gross fire rate (>50% degenerate).

## 13398: transition firings vs. annotator labels

*(Redacted from the public release: the human-annotation results are not finalized for this round. The annotator-overlap analysis will appear in a later release.)*

## Post-saturation firing rate

For each trajectory, the fraction of POST-saturation actions (those at or after the action where frustration first reaches 0.7) on which each trigger fires (gross). A6 sustained_frustration shown for contrast.

| Trajectory | sat. onset | post-sat actions | T1 | T2 | T3 | T4 | A6 sustained_frust |
|---|---|---|---|---|---|---|---|
| astropy-12907 | 17 | 11 | 27% | 0% | 9% | 64% | 100% |
| astropy-13033 | 12 | 47 | 2% | 0% | 2% | 64% | 100% |
| astropy-13236 | 21 | 23 | 4% | 0% | 4% | 26% | 100% |
| astropy-13398 | 15 | 41 | 5% | 0% | 2% | 88% | 100% |
| astropy-13453 | 13 | 18 | 11% | 0% | 6% | 72% | 100% |