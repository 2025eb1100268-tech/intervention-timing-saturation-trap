# Krippendorff's Alpha — multi-rater reliability (n=3)

Trajectory: astropy__astropy-13398, 56 actions (indices 0-55).
Annotators (n=3): Annotator A (Annotator A); Annotator B (Annotator B); Annotator C (Annotator C).

Krippendorff's alpha, nominal/binary metric, computed from scratch via the coincidence-matrix method (no library). Every action was reviewed by every rater, so an un-flagged action is a genuine 0, not missing data. Do = observed disagreement, De = expected disagreement, alpha = 1 - Do/De.

## Per-annotator positive counts

| Annotator | pause | reflect | clarify | any-flag |
|---|---|---|---|---|
| Annotator A | 4 | 5 | 2 | 8 |
| Annotator B | 1 | 4 | 2 | 6 |
| Annotator C | 0 | 2 | 13 | 15 |

## Krippendorff's alpha by intervention type

| Type | Do | De | alpha | band | n_positives (M / G / R) | degeneracy |
|---|---|---|---|---|---|---|
| pause | 0.0595 | 0.0581 | -0.025 | NO INFORMATION (degenerate) | 4 / 1 / 0 | a rater used this type 0x -> absence-dominated; read as NO INFORMATION |
| reflect | 0.0952 | 0.1231 | +0.226 | weak (not usable) | 5 / 4 / 2 | low base rate -> alpha dominated by absence agreement |
| clarify | 0.2024 | 0.1830 | -0.106 | no information (at/below chance) | 2 / 2 / 13 | low base rate -> alpha dominated by absence agreement |

### Coincidence-matrix detail (auditable)

| Type | o00 | o01 | o10 | o11 | n0 | n1 | n |
|---|---|---|---|---|---|---|---|
| pause | 158.0 | 5.0 | 5.0 | 0.0 | 163.0 | 5.0 | 168 |
| reflect | 149.0 | 8.0 | 8.0 | 3.0 | 157.0 | 11.0 | 168 |
| clarify | 134.0 | 17.0 | 17.0 | 0.0 | 151.0 | 17.0 | 168 |

## Location alpha (flagged-at-all, ignoring intervention type)

Did the three annotators flag the *same actions*, regardless of which intervention type they assigned?

| Coding | Do | De | alpha | band | n_positives (M / G / R) |
|---|---|---|---|---|---|
| any-flag (location) | 0.2738 | 0.2874 | +0.047 | weak (not usable) | 8 / 6 / 15 |

Coincidence detail: o00=116.0 o01=23.0 o10=23.0 o11=6.0 n0=139.0 n1=29.0 n=168

## Cross-check: pairwise Cohen's kappa on location coding

Confirms this script reproduces the previously verified pairwise values (`scripts/irr.py`). Any FAIL stops the run.

| Pair | kappa (this script) | expected | abs diff | result |
|---|---|---|---|---|
| Annotator A <-> Annotator B | +0.3488 | +0.349 | 0.0002 | PASS |
| Annotator A <-> Annotator C | +0.0916 | +0.092 | 0.0004 | PASS |
| Annotator B <-> Annotator C | -0.1807 | -0.181 | 0.0003 | PASS |

**All pairwise Cohen cross-checks PASS.**

## Plain-language reading

No intervention type clears even alpha=0.4 (the weakest 'not usable' cutoff). reflect is the highest at alpha=+0.226, still well short of the 0.667 tentative threshold. pause (alpha=-0.025) and clarify (alpha=-0.106) are at or below the no-information floor: their alpha is driven by the fact that all three raters agree on the many actions NObody flagged, not by agreement on what to flag. For pause, Annotator C used the label zero times, so the column is degenerate; for clarify, the three raters' positives barely overlap, pushing alpha negative (worse than chance). The three-rater location alpha (any-flag) is +0.047 -- far below the best pairwise Cohen kappa (A-B +0.349), because Annotator C's 15 flags overlap the others' almost not at all, and the third rater drags the multi-way agreement down. This is the honest multi-rater picture: even *where* to intervene is essentially unreproducible across three annotators, and *which* intervention type is worse still except for reflect.

## Notes

- Alpha computed from scratch (coincidence-matrix method); Do/De and the full 2x2 coincidence entries are printed above so every value is hand-checkable.
- Krippendorff guidance: alpha>=0.80 reliable, >=0.667 tentatively usable. Nothing here approaches either cutoff.
- Degenerate cells (a rater with 0 positives, or near-zero total positives) are flagged explicitly; their alpha reflects absence agreement, not agreement on intervention timing.
- No tuning. Negative and near-zero alphas are reported as-is.