"""Analyze the extended LLM-as-judge sweep and emit SWEEP_RESULTS.md.

Reads every data/swebench_pilot/llm_eval_extended/<model>_<condition>_<intervention>.json
and compares fire/no-fire against data/swebench_pilot/human_labels.json.

Writes:
  - data/swebench_pilot/llm_eval_extended/SWEEP_RESULTS.md

Metric computation matches scripts/calibration_analysis.py verbatim.
No threshold tuning, no rubric tuning. Read-only over labels.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


PILOT_DIR = Path("data/swebench_pilot")
EXT_DIR = PILOT_DIR / "llm_eval_extended"
TRAJ_ID = "astropy__astropy-13398"


def load_labels() -> Dict[int, Dict[str, bool]]:
    raw = json.loads((PILOT_DIR / "human_labels.json").read_text())
    traj = raw.get(TRAJ_ID, {})
    out = {}
    for entry in traj.get("labels", []):
        out[entry["action_index"]] = {
            "pause": bool(entry.get("pause", False)),
            "reflect": bool(entry.get("reflect", False)),
            "clarify": bool(entry.get("clarify", False)),
        }
    return out


def total_actions() -> int:
    raw = json.loads((PILOT_DIR / "human_labels.json").read_text())
    return raw[TRAJ_ID]["trajectory_total_actions"]


def compute_metrics(fires: Dict[int, bool], labels: Dict[int, Dict[str, bool]],
                    intervention: str, n_actions: int) -> Dict:
    tp = fp = fn = tn = 0
    for idx in range(n_actions):
        fired = fires.get(idx, False)
        labeled = labels.get(idx, {}).get(intervention, False)
        if fired and labeled:
            tp += 1
        elif fired and not labeled:
            fp += 1
        elif not fired and labeled:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
    }


def load_eval(path: Path) -> Tuple[Optional[Dict[int, bool]], Optional[Dict]]:
    if not path.exists():
        return None, None
    data = json.loads(path.read_text())
    fires = {r["action_index"]: bool(r["fire"]) for r in data["results"]}
    return fires, data


def fmt(v, prec=3) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{prec}f}"


def safe_model_name(model: str) -> str:
    return model.replace(".", "p").replace("/", "_")


def main():
    labels = load_labels()
    n = total_actions()

    models = ["gpt-5.4-mini", "gpt-5.4", "claude"]
    conditions = ["windowed", "macro"]
    interventions = ["pause", "reflect", "clarify"]

    # cell[(model, cond)] -> {intervention: {fire_rate, metrics, cost, tokens, present}}
    cells = {}
    cost_by_model = {m: 0.0 for m in models}
    tokens_by_model = {m: 0 for m in models}

    for m in models:
        for c in conditions:
            cell = {}
            for i in interventions:
                path = EXT_DIR / f"{safe_model_name(m)}_{c}_{i}.json"
                fires, data = load_eval(path)
                if fires is None:
                    cell[i] = None
                    continue
                metrics = compute_metrics(fires, labels, i, n)
                n_fired = sum(1 for v in fires.values() if v)
                cost = data.get("estimated_cost_usd", 0.0) or 0.0
                tokens = data.get("total_tokens", 0) or 0
                cost_by_model[m] = cost_by_model.get(m, 0.0) + cost
                tokens_by_model[m] = tokens_by_model.get(m, 0) + tokens
                cell[i] = {
                    "fire_rate": n_fired / n,
                    "n_fired": n_fired,
                    "metrics": metrics,
                    "cost": cost,
                    "tokens": tokens,
                }
            cells[(m, c)] = cell

    # Render
    lines = []
    lines.append("# Extended A10 LLM-as-judge Sweep")
    lines.append("")
    lines.append(f"Trajectory: `{TRAJ_ID}` ({n} actions)")
    lines.append(f"Labels: `data/swebench_pilot/human_labels.json` "
                 f"(4 pause / 5 reflect / 2 clarify)")
    lines.append("Rubric: verbatim from `scripts/llm_calibration.py`")
    lines.append("")
    lines.append("Two context conditions:")
    lines.append("- **WINDOWED**: 3 prior thoughts only (matches original A10).")
    lines.append("- **MACRO**: full running trajectory so far "
                 "(prior thought + action + observation per item, "
                 "truncated for prompt budget).")
    lines.append("")
    lines.append("Three judge models. `claude` here is Claude Opus 4.7 acting "
                 "as the judge directly through this CLI session, not via the "
                 "Anthropic API. See section at bottom for what that means for "
                 "comparability.")
    lines.append("")

    lines.append("## Sweep table")
    lines.append("")
    lines.append("Columns: firing rate (% of 56) and F1 vs human labels, "
                 "per intervention.")
    lines.append("")
    lines.append("| Model | Condition | Pause fire% | Pause F1 | "
                 "Reflect fire% | Reflect F1 | Clarify fire% | Clarify F1 | "
                 "Tokens | Est. cost |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for m in models:
        for c in conditions:
            cell = cells[(m, c)]
            row = [m, c.upper()]
            tokens_row = 0
            cost_row = 0.0
            for i in interventions:
                v = cell.get(i)
                if v is None:
                    row.extend(["-", "-"])
                else:
                    row.append(f"{100*v['fire_rate']:.1f}")
                    row.append(fmt(v["metrics"]["f1"]))
                    tokens_row += v["tokens"]
                    cost_row += v["cost"]
            row.append(str(tokens_row) if tokens_row else "-")
            row.append(f"${cost_row:.3f}" if tokens_row else "-")
            lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Direction of change WINDOWED -> MACRO per cell
    lines.append("## WINDOWED -> MACRO firing-rate change (per model x intervention)")
    lines.append("")
    lines.append("| Model | Pause | Reflect | Clarify |")
    lines.append("|---|---|---|---|")
    for m in models:
        cw = cells.get((m, "windowed"), {})
        cm = cells.get((m, "macro"), {})
        row = [m]
        for i in interventions:
            w = cw.get(i)
            mm = cm.get(i)
            if w is None or mm is None:
                row.append("n/a")
                continue
            dw = w["fire_rate"]
            dm = mm["fire_rate"]
            if dm > dw + 1e-9:
                row.append(f"ROSE ({100*dw:.1f} -> {100*dm:.1f})")
            elif dm < dw - 1e-9:
                row.append(f"FELL ({100*dw:.1f} -> {100*dm:.1f})")
            else:
                row.append(f"FLAT ({100*dw:.1f})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Cost per model
    lines.append("## Cost per model (across both conditions)")
    lines.append("")
    lines.append("| Model | Tokens | Est. cost |")
    lines.append("|---|---|---|")
    for m in models:
        t = tokens_by_model.get(m, 0)
        c = cost_by_model.get(m, 0.0)
        if t == 0 and c == 0:
            lines.append(f"| {m} | - | - |")
        else:
            lines.append(f"| {m} | {t} | ${c:.3f} |")
    lines.append("")

    # Original A10 reference
    lines.append("## Reference: original A10 (gpt-5.4-mini WINDOWED only)")
    lines.append("")
    lines.append("From `calibration_report_v4.md`:")
    lines.append("- llm_pause: 0/56 fires (0.0%), F1 N/A (0 TP)")
    lines.append("- llm_reflect: 0/56 fires (0.0%), F1 N/A (0 TP)")
    lines.append("- llm_clarify: 0/56 fires (0.0%), F1 N/A (0 TP)")
    lines.append("- Total tokens: 112324, cost: ~$0.135")
    lines.append("")

    # Notes
    lines.append("## Notes on the `claude` row")
    lines.append("")
    lines.append("The `claude` judge is Claude Opus 4.7 producing verdicts ")
    lines.append("directly in this session, applying the same verbatim rubric ")
    lines.append("to the same 56-action trajectory under the same two ")
    lines.append("conditions. Differences from the OpenAI rows:")
    lines.append("")
    lines.append("- Each verdict is one read+judge by the same judge instance, ")
    lines.append("  not an independent API call.")
    lines.append("- The judge sees the entire trajectory file when rendering ")
    lines.append("  verdicts; the WINDOWED constraint is enforced by ")
    lines.append("  evaluating each action against only its 3 most recent ")
    lines.append("  prior thoughts at judgment time, but the judge cannot ")
    lines.append("  truly unsee what it has read. This biases WINDOWED toward ")
    lines.append("  whatever MACRO produces. Read this as an upper bound on ")
    lines.append("  whether full-trajectory access changes judge behavior, ")
    lines.append("  not as a clean condition contrast.")
    lines.append("- Cost is $0 to the user (subscription-priced, not metered).")
    lines.append("")

    lines.append("## Methodology guarantees")
    lines.append("")
    lines.append("- No engine code, trigger code, threshold values, or "
                 "human_labels.json were modified.")
    lines.append("- The rubric strings and SYSTEM_PROMPT are byte-for-byte "
                 "copies of `scripts/llm_calibration.py`.")
    lines.append("- Metric computation is byte-for-byte equivalent to "
                 "`scripts/calibration_analysis.py:compute_metrics`.")
    lines.append("- Outputs are write-only under `data/swebench_pilot/llm_eval_extended/`.")
    lines.append("")

    out = "\n".join(lines)
    out_path = EXT_DIR / "SWEEP_RESULTS.md"
    out_path.write_text(out)
    print(f"saved: {out_path}\n")
    print("=" * 70)
    print(out)


if __name__ == "__main__":
    main()
