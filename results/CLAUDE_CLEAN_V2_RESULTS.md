# Clean Claude Judge Run v2 — uniform fresh-sub-agent method

**v2 SUPERSEDES v1 (`CLAUDE_CLEAN_RESULTS.md`).**

In v1, only 2 of the 6 slices ran as fresh isolated sub-agents; the other 4 were produced inline in a busy parent session. That mixed the measurement method across cells and biased the inline `clarify` cells downward — the same deference effect the paper studies, leaking into the measurement instrument itself.

**In v2, ALL SIX cells are fresh, isolated sub-agents.** Each was a separate Claude Opus instance with no other task context, given only its 56-prompt slice file and the verbatim embedded rubric, judging one action at a time. Method is now uniform across every cell, so cross-cell and cross-condition comparisons are valid.

Trajectory: `astropy__astropy-13398` (56 actions)
Labels: `data/swebench_pilot/human_labels.json` (4 pause / 5 reflect / 2 clarify)
Rubric: verbatim from `scripts/llm_calibration.py`
Metric computation: byte-for-byte equivalent to `scripts/calibration_analysis.py:compute_metrics`

## v2 results — F1 vs human labels (uniform method)

| Condition | Intervention | Fires/56 | Fire% | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|---|---|
| windowed | pause | 7/56 | 12.5 | 0 | 7 | 4 | 45 | 0.000 | 0.000 | N/A |
| windowed | reflect | 13/56 | 23.2 | 2 | 11 | 3 | 40 | 0.154 | 0.400 | 0.222 |
| windowed | clarify | 12/56 | 21.4 | 1 | 11 | 1 | 43 | 0.083 | 0.500 | 0.143 |
| macro | pause | 4/56 | 7.1 | 0 | 4 | 4 | 48 | 0.000 | 0.000 | N/A |
| macro | reflect | 18/56 | 32.1 | 2 | 16 | 3 | 35 | 0.111 | 0.400 | 0.174 |
| macro | clarify | 8/56 | 14.3 | 1 | 7 | 1 | 47 | 0.125 | 0.500 | 0.200 |

## WINDOWED → MACRO firing-rate change (v2)

| Intervention | Windowed | Macro | Direction |
|---|---|---|---|
| pause | 12.5% | 7.1% | FELL (12.5% → 7.1%) |
| reflect | 23.2% | 32.1% | ROSE (23.2% → 32.1%) |
| clarify | 21.4% | 14.3% | FELL (21.4% → 14.3%) |

## v1 → v2 delta per cell (inline bias made visible)

v1 method: `SA` = fresh sub-agent, `IN` = inline parent session. v2 method: all `SA`. The delta column shows how much the firing count moved when the inline cells were re-run as proper sub-agents.

| Condition | Intervention | v1 method | v1 fires | v2 fires | Δ fires | v1 F1 | v2 F1 | Δ F1 |
|---|---|---|---|---|---|---|---|---|
| windowed | pause | IN | 5 | 7 | +2 | 0.222 | N/A | n/a |
| windowed | reflect | SA | 6 | 13 | +7 | 0.545 | 0.222 | -0.323 |
| windowed | clarify | SA | 8 | 12 | +4 | 0.200 | 0.143 | -0.057 |
| macro | pause | IN | 9 | 4 | -5 | 0.154 | N/A | n/a |
| macro | reflect | IN | 13 | 18 | +5 | 0.222 | 0.174 | -0.048 |
| macro | clarify | IN | 12 | 8 | -4 | 0.143 | 0.200 | +0.057 |

Cells whose v1 method was `IN` (inline) are the ones where v1 measurement was contaminated by the parent session. Watch those rows' Δ — large movement there confirms the inline bias; small movement in the `SA` rows confirms the fresh-sub-agent method is stable.

## v2 per-cell diagnostic indices

### claude_clean_v2_windowed_pause
- TP (system fired AND human labeled): `[]`
- FP (system fired, human did NOT): `[35, 36, 40, 41, 43, 45, 46]`
- FN (system did NOT fire, human labeled): `[9, 18, 33, 42]`

### claude_clean_v2_windowed_reflect
- TP (system fired AND human labeled): `[29, 42]`
- FP (system fired, human did NOT): `[30, 31, 32, 35, 36, 40, 41, 43, 44, 45, 46]`
- FN (system did NOT fire, human labeled): `[2, 9, 33]`

### claude_clean_v2_windowed_clarify
- TP (system fired AND human labeled): `[44]`
- FP (system fired, human did NOT): `[29, 31, 33, 35, 37, 38, 40, 42, 45, 47, 48]`
- FN (system did NOT fire, human labeled): `[0]`

### claude_clean_v2_macro_pause
- TP (system fired AND human labeled): `[]`
- FP (system fired, human did NOT): `[45, 46, 52, 55]`
- FN (system did NOT fire, human labeled): `[9, 18, 33, 42]`

### claude_clean_v2_macro_reflect
- TP (system fired AND human labeled): `[29, 42]`
- FP (system fired, human did NOT): `[30, 31, 32, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48]`
- FN (system did NOT fire, human labeled): `[2, 9, 33]`

### claude_clean_v2_macro_clarify
- TP (system fired AND human labeled): `[44]`
- FP (system fired, human did NOT): `[37, 38, 40, 41, 42, 46, 47]`
- FN (system did NOT fire, human labeled): `[0]`

## Methodology guarantees

- No engine code, trigger code, threshold values, or `human_labels.json` were modified.
- The rubric strings and SYSTEM_PROMPT are byte-for-byte copies of `scripts/llm_calibration.py`.
- Metric computation is byte-for-byte equivalent to `scripts/calibration_analysis.py:compute_metrics`.
- ALL SIX cells: fresh isolated Claude Opus sub-agent, one per (condition × intervention), no shared task context, judging one action at a time against the embedded rubric.
- Each sub-agent received the identical prompt structure as the OpenAI per-action loop (windowed = 3 prior thoughts; macro = full prior trajectory truncated per item).
- No tuning of any kind. Zeros reported as zeros.

### Per-cell I/O mechanism (judgment method uniform; file-read mechanism varied)

The 3 MACRO sub-agents ran in sandboxes where Bash and PowerShell were permission-denied, so they read their slice files via the Read/Grep tools instead of the suggested Python helper. Because each macro prompt embeds the cumulative full trajectory, a sub-agent could recover the complete trajectory from a small number of reads. All three still judged every one of the 56 actions independently and produced complete, schema-valid output (verified: action indices 0–55 present, n_fired consistent). The 3 WINDOWED sub-agents used the Read tool directly on their smaller slice files. In every cell the fire/no-fire decision was the sub-agent's own judgment, not scripted — the JUDGMENT method is uniform across all six cells; only the file-I/O mechanism differed (Read/Grep vs. Python helper), which does not affect verdicts.

### Run-to-run judge variance

Note `windowed/reflect`: v1 (a fresh sub-agent) fired 6/56 at F1 0.545; v2 (also a fresh sub-agent) fired 13/56 at F1 0.222. Same method, different run — so part of the v1→v2 delta even in `SA` cells is intrinsic LLM-judge stochasticity, not just the inline-vs-isolated method change. With only 8 positive labels on one trajectory, single-cell F1 values are high-variance point estimates; the stable finding is the qualitative one (Claude-as-judge fires in the grinding-loop region 29–48 and concentrates TPs at human-labeled 29/42/44), not any specific F1 number.

Cost: $0 to user (subscription-priced).