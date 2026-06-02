"""Calibration analysis: guidelines firings vs human labels.

Reads:
  - data/swebench_pilot/guidelines_replay.json (from Component 1)
  - data/swebench_pilot/human_labels.json (from manual labeling)

Writes:
  - data/swebench_pilot/calibration_report.md
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple


PILOT_DIR = Path("data/swebench_pilot")
TRAJ_ID = "astropy__astropy-13398"


# Mapping: trigger_name -> human label field
TRIGGER_TO_LABEL = {
    # Phase A6 (deprecated, kept for comparison)
    "sustained_frustration": "pause",
    "same_valence_accumulation": "reflect",
    "high_confusion_no_reflection": "clarify",
    # Phase A8 composite triggers
    "rapid_negative_escalation": "pause",
    "failure_repetition": "reflect",
    "stalled_progress_with_uncertainty": "clarify",
    # Phase A9 reasoning-pattern triggers
    "cycle_with_resistance": "reflect",
    "tone_degradation": "pause",
}


def load_replay() -> Dict:
    return json.loads((PILOT_DIR / "guidelines_replay.json").read_text())


def load_labels() -> Dict[int, Dict[str, bool]]:
    """Returns {action_index: {pause: bool, reflect: bool, clarify: bool}}.

    Action indices not present default to all-false.
    """
    raw = json.loads((PILOT_DIR / "human_labels.json").read_text())
    traj_data = raw.get(TRAJ_ID, {})
    out = {}
    for entry in traj_data.get("labels", []):
        out[entry["action_index"]] = {
            "pause": bool(entry.get("pause", False)),
            "reflect": bool(entry.get("reflect", False)),
            "clarify": bool(entry.get("clarify", False)),
        }
    return out


def trigger_fired_at(timeline_entry: Dict, trigger_name: str) -> bool:
    """Did the given trigger fire on this action?"""
    return any(
        f["trigger"] == trigger_name
        for f in timeline_entry.get("guidelines_firings", [])
    )


def load_llm_eval(intervention: str):
    """Load LLM eval results if present. Returns dict {action_index: bool}
    or None if file not found."""
    path = PILOT_DIR / f"llm_eval_{intervention}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {r["action_index"]: bool(r["fire"]) for r in data["results"]}


def compute_llm_metrics(replay: Dict, labels: Dict, intervention: str):
    """Same as compute_metrics but reads LLM fire decisions instead of
    trigger firings from the replay."""
    llm_fires = load_llm_eval(intervention)
    if llm_fires is None:
        return None

    label_field = intervention  # pause -> pause, etc.
    tp = fp = fn = tn = 0
    fp_indices, fn_indices, tp_indices = [], [], []

    for entry in replay["timeline"]:
        idx = entry["action_index"]
        fired = llm_fires.get(idx, False)
        labeled = labels.get(idx, {}).get(label_field, False)

        if fired and labeled:
            tp += 1
            tp_indices.append(idx)
        elif fired and not labeled:
            fp += 1
            fp_indices.append(idx)
        elif not fired and labeled:
            fn += 1
            fn_indices.append(idx)
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
        "trigger": f"llm_{intervention}",
        "label_field": label_field,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "tp_indices": tp_indices, "fp_indices": fp_indices, "fn_indices": fn_indices,
    }


def human_labeled(labels: Dict[int, Dict], action_idx: int, field: str) -> bool:
    """Did the human label this field as True for this action?"""
    return labels.get(action_idx, {}).get(field, False)


def compute_metrics(replay: Dict, labels: Dict, trigger_name: str, label_field: str) -> Dict:
    """Compute TP/FP/FN/TN and precision/recall/F1 for one trigger."""
    tp = fp = fn = tn = 0
    fp_indices = []
    fn_indices = []
    tp_indices = []

    for entry in replay["timeline"]:
        idx = entry["action_index"]
        fired = trigger_fired_at(entry, trigger_name)
        labeled = human_labeled(labels, idx, label_field)

        if fired and labeled:
            tp += 1
            tp_indices.append(idx)
        elif fired and not labeled:
            fp += 1
            fp_indices.append(idx)
        elif not fired and labeled:
            fn += 1
            fn_indices.append(idx)
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
        "trigger": trigger_name,
        "label_field": label_field,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp_indices": tp_indices,
        "fp_indices": fp_indices,
        "fn_indices": fn_indices,
    }


def fmt(x):
    """Format a metric or 'N/A' if None."""
    if x is None:
        return "N/A"
    return f"{x:.3f}"


def render_report(replay: Dict, labels: Dict, all_metrics: List[Dict]) -> str:
    n_actions = replay["total_actions"]
    n_labeled = sum(
        1 for m in labels.values()
        if any(m.values())
    )

    lines = []
    lines.append(f"# Calibration Report: {TRAJ_ID}")
    lines.append("")
    lines.append(f"Total actions in trajectory: **{n_actions}**")
    lines.append(f"Actions with at least one human label: **{n_labeled}**")
    lines.append("")
    lines.append("**Small-sample caveat:** with only 8 positive labels across 56 actions, ")
    lines.append("these metrics are statistically noisy. They are directional, not stable.")
    lines.append("")

    lines.append("## Phase A10 -- LLM-based evaluation")
    lines.append("")
    lines.append("This report extends v3 with three LLM-based trigger ")
    lines.append("evaluations using GPT-5.4-mini against the same labels. ")
    lines.append("LLM rows appear only if the corresponding eval file exists ")
    lines.append("(scripts/llm_calibration.py {pause|reflect|clarify}).")
    lines.append("")

    lines.append("## Per-intervention calibration")
    lines.append("")
    lines.append("| Trigger | Label | TP | FP | FN | TN | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for m in all_metrics:
        lines.append(
            f"| {m['trigger']} | {m['label_field']} | "
            f"{m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | "
            f"{fmt(m['precision'])} | {fmt(m['recall'])} | {fmt(m['f1'])} |"
        )
    lines.append("")

    lines.append("## Per-intervention diagnostic detail")
    lines.append("")
    for m in all_metrics:
        lines.append(f"### {m['trigger']} -> {m['label_field']}")
        lines.append("")
        lines.append(f"- **TP indices** (system fired AND human labeled): {m['tp_indices']}")
        lines.append(f"- **FP indices** (system fired, human did NOT label): {m['fp_indices']}")
        lines.append(f"- **FN indices** (system did NOT fire, human labeled): {m['fn_indices']}")
        lines.append("")

    lines.append("## Aggregate firing summary")
    lines.append("")
    by_trigger = {}
    for entry in replay["timeline"]:
        for f in entry.get("guidelines_firings", []):
            by_trigger[f["trigger"]] = by_trigger.get(f["trigger"], 0) + 1
    for trigger, count in sorted(by_trigger.items(), key=lambda x: -x[1]):
        lines.append(f"- {trigger}: fired on {count} of {n_actions} actions ({100*count/n_actions:.1f}%)")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("This report was generated automatically. Interpretation is the ")
    lines.append("operator's responsibility and goes in DESIGN_LOG.md, not here. ")
    lines.append("No threshold tuning has been applied based on this report.")

    return "\n".join(lines)


def main():
    replay = load_replay()
    labels = load_labels()

    all_metrics = []
    for trigger_name, label_field in TRIGGER_TO_LABEL.items():
        metrics = compute_metrics(replay, labels, trigger_name, label_field)
        all_metrics.append(metrics)

    # LLM eval rows (only included if eval files exist)
    for intervention in ("pause", "reflect", "clarify"):
        llm_metrics = compute_llm_metrics(replay, labels, intervention)
        if llm_metrics is not None:
            all_metrics.append(llm_metrics)

    report = render_report(replay, labels, all_metrics)
    output_path = PILOT_DIR / "calibration_report_v4.md"
    output_path.write_text(report)

    print(f"saved: {output_path}")
    print()
    print("=" * 70)
    print(report)


if __name__ == "__main__":
    main()
