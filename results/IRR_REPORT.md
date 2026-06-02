# Inter-Rater Reliability — agent-intervention-timing labels

Trajectory: astropy__astropy-13398, 56 actions (indices 0–55).
Annotators (n=3): Annotator A; Annotator B; Annotator C.

Cohen's Kappa computed over full 56-action binary vectors per intervention type. Low-base-rate types are flagged: when an annotator marks very few positives, Kappa is unstable and the raw overlap is the more interpretable statistic. Annotator C's discarded first pass is excluded.

## Per-annotator positive counts

| Annotator | pause | reflect | clarify | any-flag |
|---|---|---|---|---|
| Annotator A | 4 | 5 | 2 | 8 |
| Annotator B | 1 | 4 | 2 | 6 |
| Annotator C | 0 | 2 | 13 | 15 |

## Pairwise Cohen's Kappa, by intervention type

### Pause

| Pair | rater-A pos | rater-B pos | Po | Kappa | Interpretation | Note |
|---|---|---|---|---|---|---|
| Annotator A ↔ Annotator B | 4 | 1 | 0.911 | -0.029 | poor (worse than chance) | low base rate — Kappa unreliable |
| Annotator A ↔ Annotator C | 4 | 0 | 0.929 | +0.000 | slight | low base rate — Kappa unreliable |
| Annotator B ↔ Annotator C | 1 | 0 | 0.982 | +0.000 | slight | low base rate — Kappa unreliable |

### Reflect

| Pair | rater-A pos | rater-B pos | Po | Kappa | Interpretation | Note |
|---|---|---|---|---|---|---|
| Annotator A ↔ Annotator B | 5 | 4 | 0.911 | +0.397 | fair |  |
| Annotator A ↔ Annotator C | 5 | 2 | 0.911 | +0.247 | fair | low base rate — Kappa unreliable |
| Annotator B ↔ Annotator C | 4 | 2 | 0.893 | -0.050 | poor (worse than chance) | low base rate — Kappa unreliable |

### Clarify

| Pair | rater-A pos | rater-B pos | Po | Kappa | Interpretation | Note |
|---|---|---|---|---|---|---|
| Annotator A ↔ Annotator B | 2 | 2 | 0.929 | -0.037 | poor (worse than chance) | low base rate — Kappa unreliable |
| Annotator A ↔ Annotator C | 2 | 13 | 0.732 | -0.066 | poor (worse than chance) | low base rate — Kappa unreliable |
| Annotator B ↔ Annotator C | 2 | 13 | 0.732 | -0.066 | poor (worse than chance) | low base rate — Kappa unreliable |

## Location agreement (flagged-at-all, ignoring intervention type)

Did the annotators flag the *same actions*, regardless of which intervention type they assigned? This separates 'where to intervene' from 'how'.

| Pair | A flags | B flags | shared actions | Po | Kappa | Interpretation |
|---|---|---|---|---|---|---|
| Annotator A ↔ Annotator B | 8 | 6 | [33, 42, 44] | 0.857 | +0.349 | fair |
| Annotator A ↔ Annotator C | 8 | 15 | [0, 2, 18] | 0.696 | +0.092 | slight |
| Annotator B ↔ Annotator C | 6 | 15 | — | 0.625 | -0.181 | poor (worse than chance) |

## Action-level overlap map

| Action | Flagged by | # annotators |
|---|---|---|
| 0 | A, C | 2 |
| 2 | A, C | 2 |
| 3 | C | 1 |
| 4 | C | 1 |
| 5 | C | 1 |
| 9 | A | 1 |
| 18 | A, C | 2 |
| 22 | C | 1 |
| 25 | B | 1 |
| 28 | C | 1 |
| 29 | A | 1 |
| 30 | C | 1 |
| 33 | A, B | 2 |
| 37 | B | 1 |
| 38 | B | 1 |
| 40 | C | 1 |
| 42 | A, B | 2 |
| 43 | C | 1 |
| 44 | A, B | 2 |
| 45 | C | 1 |
| 46 | C | 1 |
| 48 | C | 1 |
| 55 | C | 1 |

- Flagged by **all 3** annotators: none
- Flagged by **≥2** annotators: [0, 2, 18, 33, 42, 44]
- Total distinct actions flagged by anyone: 23 of 56

## Reading

- Per-type Kappa is low-to-undefined across most pairs, driven partly by genuine disagreement and partly by low base rates (each annotator flags few actions). Both facts are reported rather than collapsed into one number.
- Location agreement (which actions to flag at all) is the more stable view; even there, agreement is modest and concentrated in the late-trajectory grinding region.
- Annotators diverge on intervention *type* even when they flag the same action — the clearest single takeaway, and the one that bears on why no automated trigger matches any single annotator's labels.