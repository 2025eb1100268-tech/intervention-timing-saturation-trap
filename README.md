# The Saturation Trap and the Subjectivity of Intervention Timing

Reproducibility release for the paper *"The Saturation Trap and the
Subjectivity of Intervention Timing: Why Affect-Based Triggers and LLM Judges
Fail to Time Interventions on Autonomous Agents"* (Manvendra Modgil, Modint
Intelligence).

**arXiv:** arXiv:2606.04296
Paper: https://arxiv.org/abs/2606.04296

This repository releases the human annotation data, the analysis scripts, and
the computed result artifacts behind the paper's empirical claims. It is
released for transparency of method and to allow independent recomputation of
the inter-rater reliability statistics.

---

## Contents

### `labels/`
The three annotators' intervention-timing labels for trajectory
`astropy__astropy-13398` (56 actions). Each file has the schema
`{"human_labeler": ..., "trajectory_total_actions": 56, "flagged": {"<action_index>": {"pause": bool, "reflect": bool, "clarify": bool}, ...}}`.
Annotator identities are anonymized to **A**, **B**, **C** to match the paper.

- `labels_annotator_a.json`
- `labels_annotator_b.json`
- `labels_annotator_c.json`

### `scripts/`
- `irr.py` — pairwise Cohen's κ and the action-overlap map. **Self-contained**;
  runs on the label files alone.
- `krippendorff_alpha.py` — three-rater Krippendorff's α (nominal/binary,
  implemented from scratch via the coincidence-matrix method) with a Cohen's κ
  cross-check. **Self-contained**; runs on the label files alone.
- `saturation_replay.py`, `saturation_all.py` — the State Saturation Trap
  replay and the five-trajectory aggregator.
- `llm_calibration.py`, `llm_calibration_sweep.py`, `sweep_analyze.py` — the
  zero-shot LLM-as-judge calibration and the cross-model sweep.
- `replay_with_guidelines.py`, `calibration_analysis.py` — the per-action
  trigger replay and calibration scoring.

Every script except `irr.py` and `krippendorff_alpha.py` imports the
proprietary HEART engine and therefore **cannot be run from this repository**;
each such import is marked with the comment
`# requires the proprietary HEART engine (not included; see README)`. These
scripts are released for transparency of method, not as runnable artifacts.

### `results/`
- `IRR_REPORT.md` — pairwise Cohen's κ report (regenerated from the anonymized
  labels).
- `KRIPPENDORFF_REPORT.md` — three-rater Krippendorff's α report.
- `SATURATION_ALL.md` — State Saturation Trap summary across all five pilot
  trajectories.
- `SWEEP_RESULTS.md` — cross-model LLM-as-judge sweep
  (gpt-5.4-mini / gpt-5.4 / Claude × windowed / macro).
- `CLAUDE_CLEAN_V2_RESULTS.md` — the methodologically clean (fully isolated)
  Claude judge re-run that is primary in the paper.
- `saturation_astropy__astropy-{12907,13033,13236,13398,13453}.json` — the
  per-action engine-state replays for the five trajectories.

---

## Reproducing the inter-rater reliability

Both self-contained scripts run on the label files with no dependencies beyond
the Python standard library:

```bash
# Pairwise Cohen's kappa + action-overlap map
python scripts/irr.py \
  labels/labels_annotator_a.json \
  labels/labels_annotator_b.json \
  labels/labels_annotator_c.json

# Three-rater Krippendorff's alpha (+ Cohen cross-check)
python scripts/krippendorff_alpha.py
```

Expected (paper §7):

| Statistic | Value |
|---|---|
| Cohen's κ, A↔B (location) | +0.349 |
| Cohen's κ, A↔C (location) | +0.092 |
| Cohen's κ, B↔C (location) | −0.181 |
| Krippendorff's α, location (any-type) | +0.047 |
| Krippendorff's α, reflect | +0.226 |
| Krippendorff's α, pause | −0.025 (degenerate; C never used pause) |
| Krippendorff's α, clarify | −0.106 (below chance) |

`krippendorff_alpha.py` re-derives the three pairwise Cohen's κ values and
prints `PASS`/`FAIL` against the above as a self-check.

---

## Not included: the HEART engine

The diagnostic probe used in the paper — the HEART continuous 18-dimensional
affective-dynamics engine, its observer/adapter, and its guideline-trigger
layer — is **proprietary and is not part of this release**. It is the subject
of **Indian Patent Application No. 202521098101**. In the paper it is used only
as a fixed, unmodified diagnostic probe; no engine parameter or trigger
threshold was tuned in any experiment.

Consequently, the engine-dependent scripts in `scripts/` (everything except
`irr.py` and `krippendorff_alpha.py`) are published to document the exact
method, but cannot be executed without the engine. The `results/` artifacts
they produced are included so their outputs are inspectable.

The raw SWE-bench-Verified trajectory traces are the property of their
respective sources and are not redistributed here; only the per-action
engine-state replays (`results/saturation_*.json`) and the human labels are
released.

---

## Citation

```bibtex
@misc{modgil2026saturationtrap,
  title  = {The Saturation Trap and the Subjectivity of Intervention Timing:
            Why Affect-Based Triggers and LLM Judges Fail to Time Interventions
            on Autonomous Agents},
  author = {Modgil, Manvendra},
  year   = {2026},
  eprint = {XXXX.XXXXX},
  archivePrefix = {arXiv}
}
```

## License

MIT — see [LICENSE](LICENSE). The MIT license covers the contents of this
repository only; it does **not** grant any rights to the HEART engine, which is
proprietary (see above).
