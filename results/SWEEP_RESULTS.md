# Extended A10 LLM-as-judge Sweep

Trajectory: `astropy__astropy-13398` (56 actions)
Labels: `data/swebench_pilot/human_labels.json` (4 pause / 5 reflect / 2 clarify)
Rubric: verbatim from `scripts/llm_calibration.py`

Two context conditions:
- **WINDOWED**: 3 prior thoughts only (matches original A10).
- **MACRO**: full running trajectory so far (prior thought + action + observation per item, truncated for prompt budget).

Three judge models. `claude` here is Claude Opus 4.7 acting as the judge directly through this CLI session, not via the Anthropic API. See section at bottom for what that means for comparability.

## Sweep table

Columns: firing rate (% of 56) and F1 vs human labels, per intervention.

| Model | Condition | Pause fire% | Pause F1 | Reflect fire% | Reflect F1 | Clarify fire% | Clarify F1 | Tokens | Est. cost |
|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4-mini | WINDOWED | 0.0 | N/A | 0.0 | N/A | 0.0 | N/A | 113540 | $0.136 |
| gpt-5.4-mini | MACRO | 0.0 | N/A | 0.0 | N/A | 0.0 | N/A | 875104 | $1.050 |
| gpt-5.4 | WINDOWED | 0.0 | N/A | 3.6 | N/A | 3.6 | N/A | 114340 | $1.601 |
| gpt-5.4 | MACRO | 14.3 | 0.167 | 32.1 | 0.087 | 23.2 | N/A | 876106 | $12.265 |
| claude | WINDOWED | 5.4 | N/A | 17.9 | 0.400 | 0.0 | N/A | - | - |
| claude | MACRO | 23.2 | 0.235 | 23.2 | 0.333 | 1.8 | 0.667 | - | - |

## WINDOWED -> MACRO firing-rate change (per model x intervention)

| Model | Pause | Reflect | Clarify |
|---|---|---|---|
| gpt-5.4-mini | FLAT (0.0) | FLAT (0.0) | FLAT (0.0) |
| gpt-5.4 | ROSE (0.0 -> 14.3) | ROSE (3.6 -> 32.1) | ROSE (3.6 -> 23.2) |
| claude | ROSE (5.4 -> 23.2) | ROSE (17.9 -> 23.2) | ROSE (0.0 -> 1.8) |

## Cost per model (across both conditions)

| Model | Tokens | Est. cost |
|---|---|---|
| gpt-5.4-mini | 988644 | $1.186 |
| gpt-5.4 | 990446 | $13.866 |
| claude | - | - |

## Reference: original A10 (gpt-5.4-mini WINDOWED only)

From `calibration_report_v4.md`:
- llm_pause: 0/56 fires (0.0%), F1 N/A (0 TP)
- llm_reflect: 0/56 fires (0.0%), F1 N/A (0 TP)
- llm_clarify: 0/56 fires (0.0%), F1 N/A (0 TP)
- Total tokens: 112324, cost: ~$0.135

## Notes on the `claude` row

The `claude` judge is Claude Opus 4.7 producing verdicts 
directly in this session, applying the same verbatim rubric 
to the same 56-action trajectory under the same two 
conditions. Differences from the OpenAI rows:

- Each verdict is one read+judge by the same judge instance, 
  not an independent API call.
- The judge sees the entire trajectory file when rendering 
  verdicts; the WINDOWED constraint is enforced by 
  evaluating each action against only its 3 most recent 
  prior thoughts at judgment time, but the judge cannot 
  truly unsee what it has read. This biases WINDOWED toward 
  whatever MACRO produces. Read this as an upper bound on 
  whether full-trajectory access changes judge behavior, 
  not as a clean condition contrast.
- Cost is $0 to the user (subscription-priced, not metered).

## Methodology guarantees

- No engine code, trigger code, threshold values, or human_labels.json were modified.
- The rubric strings and SYSTEM_PROMPT are byte-for-byte copies of `scripts/llm_calibration.py`.
- Metric computation is byte-for-byte equivalent to `scripts/calibration_analysis.py:compute_metrics`.
- Outputs are write-only under `data/swebench_pilot/llm_eval_extended/`.
