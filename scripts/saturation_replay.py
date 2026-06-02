"""Replay any trajectory through the engine + adapter + A6 triggers, and
log per-action emotion + trigger data. Sister script to
scripts/replay_with_guidelines.py; it does NOT modify that script.

Usage:
    python scripts/saturation_replay.py <trajectory_id>
e.g.
    python scripts/saturation_replay.py astropy__astropy-13033

Writes:
    data/swebench_pilot/saturation_<trajectory_id>.json
        - per-action: action_index, tool_name, frustration, anger, fear,
          confusion, vengeance, neg_sum (the same 5-emotion accumulator
          used by the A6 same_valence_accumulation trigger), reflective_flag,
          which A6 triggers fired (sustained_frustration,
          same_valence_accumulation, high_confusion_no_reflection)

This is a measurement script. It does NOT tune any thresholds or modify
engine, adapter, trigger, or label code.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Any

# requires the proprietary HEART engine (not included; see README)
from heart_core.engine import EmotionEngine
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter
from heart_adapters.claude_code.trajectory import parse_trajectory_file

# A6 triggers (verbatim from heart_guidelines/triggers.py — referenced, not modified)
# requires the proprietary HEART engine (not included; see README)
from heart_guidelines.triggers import (
    trigger_sustained_frustration,
    trigger_same_valence_accumulation,
    trigger_high_confusion_no_reflection,
    NEGATIVE_ACCUMULATION_THRESHOLD,
    SUSTAINED_FRUSTRATION_THRESHOLD,
    CONFUSION_DURATION_THRESHOLD,
)


PILOT_DIR = Path("data/swebench_pilot")
# The 5 emotions summed by same_valence_accumulation (verbatim from triggers.py:40)
NEGATIVES = ("frustration", "anger", "fear", "confusion", "vengeance")


def emotion_state_dict(engine: EmotionEngine) -> Dict[str, float]:
    return {emo: float(val) for emo, val in engine.get_emotion_vector().items()}


def replay(traj_id: str) -> Dict[str, Any]:
    traj_path = PILOT_DIR / f"{traj_id}.json"
    if not traj_path.exists():
        raise FileNotFoundError(traj_path)

    events = parse_trajectory_file(traj_path)
    engine = EmotionEngine()
    adapter = ClaudeCodeAdapter(engine)

    timeline = []
    for idx, event in enumerate(events):
        adapter.observe(event)
        state = emotion_state_dict(engine)
        engine_state = engine.get_state()
        reflective = bool(engine_state.get("reflective", False))
        ctx = {"reflective_flag": reflective}

        # A6 triggers (no tuning — uses the constants as defined in triggers.py)
        fires = {
            "sustained_frustration": bool(trigger_sustained_frustration(state, ctx)),
            "same_valence_accumulation": bool(trigger_same_valence_accumulation(state, ctx)),
            "high_confusion_no_reflection": bool(trigger_high_confusion_no_reflection(state, ctx)),
        }

        neg_sum = sum(state.get(e, 0.0) for e in NEGATIVES)

        timeline.append({
            "action_index": idx,
            "tool_name": event.tool_name,
            "reflective_flag": reflective,
            "frustration": state.get("frustration", 0.0),
            "anger": state.get("anger", 0.0),
            "fear": state.get("fear", 0.0),
            "confusion": state.get("confusion", 0.0),
            "vengeance": state.get("vengeance", 0.0),
            "neg_sum": neg_sum,
            "fires": fires,
        })

    return {
        "trajectory_id": traj_id,
        "total_actions": len(events),
        "thresholds": {
            "SUSTAINED_FRUSTRATION_THRESHOLD": SUSTAINED_FRUSTRATION_THRESHOLD,
            "NEGATIVE_ACCUMULATION_THRESHOLD": NEGATIVE_ACCUMULATION_THRESHOLD,
            "CONFUSION_DURATION_THRESHOLD": CONFUSION_DURATION_THRESHOLD,
        },
        "negatives": list(NEGATIVES),
        "timeline": timeline,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/saturation_replay.py <trajectory_id>", file=sys.stderr)
        sys.exit(1)
    traj_id = sys.argv[1]
    result = replay(traj_id)
    out_path = PILOT_DIR / f"saturation_{traj_id}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"saved: {out_path}")
    print(f"actions: {result['total_actions']}")
    by_trig = {k: 0 for k in ("sustained_frustration", "same_valence_accumulation", "high_confusion_no_reflection")}
    for t in result["timeline"]:
        for k, v in t["fires"].items():
            if v:
                by_trig[k] += 1
    n = result["total_actions"]
    for k, c in by_trig.items():
        print(f"  {k}: {c}/{n} ({100*c/n:.1f}%)")


if __name__ == "__main__":
    main()
