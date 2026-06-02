"""Replay trajectory 13398 through the guidelines layer.

For each action: update engine via adapter, then evaluate guidelines and
log firings. Output is consumed by calibration_analysis.py.

This script does NOT modify any engine, adapter, or guidelines code. It
is read-only over those modules.

NOTE (deviation from A7 spec): the spec's emotion_state_dict() reads
state["intensities"], which does not exist on EmotionEngine.get_state().
The actual key for the 18-emotion vector is "vector" (or it's
exposed directly via engine.get_emotion_vector()). Using the public
get_emotion_vector() API to avoid the typo.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

# requires the proprietary HEART engine (not included; see README)
from heart_core.engine import EmotionEngine
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter
from heart_adapters.claude_code.trajectory import parse_trajectory_file
from heart_guidelines.guidelines_engine import GuidelinesEngine
from heart_guidelines.state_history import StateHistory, HistoryEntry


PILOT_DIR = Path("data/swebench_pilot")
TRAJ_ID = "astropy__astropy-13398"


def emotion_state_dict(engine: EmotionEngine) -> Dict[str, float]:
    """Extract the full 18-emotion vector as a dict."""
    return {emo: float(val) for emo, val in engine.get_emotion_vector().items()}


def replay_trajectory(traj_path: Path) -> Dict[str, Any]:
    """Walk the trajectory and log per-action guidelines evaluations."""
    events = parse_trajectory_file(traj_path)

    engine = EmotionEngine()
    adapter = ClaudeCodeAdapter(engine)
    guidelines = GuidelinesEngine()
    history = StateHistory(max_size=10)

    timeline = []
    for idx, event in enumerate(events):
        # Update engine via adapter
        adapter_result = adapter.observe(event)

        # Evaluate guidelines AFTER engine update
        state = emotion_state_dict(engine)
        engine_state = engine.get_state()
        reflective = bool(engine_state.get("reflective", False))
        has_error = event.has_error()

        # Append to history BEFORE evaluating guidelines, so triggers see
        # this action's state in their window
        history.append(HistoryEntry(
            action_index=idx,
            tool_name=event.tool_name,
            tool_args=event.tool_args or {},
            state=state,
            reflective_flag=reflective,
            has_error=has_error,
            rules_fired=adapter_result.get("rules_fired", 0),
            reasoning_text=event.reasoning_text or "",
        ))

        context = {"reflective_flag": reflective, "history": history}
        interventions = guidelines.evaluate(state, context=context)

        # Log entry
        firings = [
            {
                "trigger": iv.triggered_by,
                "kind": iv.kind.value,
                "severity": iv.severity,
                "rationale": iv.rationale,
            }
            for iv in interventions
        ]

        timeline.append({
            "action_index": idx,
            "tool_name": event.tool_name,
            "agent_dominant": engine_state.get("emotion"),
            "agent_intensity": float(engine_state.get("intensity", 0.0)),
            "reflective_flag": reflective,
            "frustration": state.get("frustration", 0.0),
            "confusion": state.get("confusion", 0.0),
            "fear": state.get("fear", 0.0),
            "rules_fired": adapter_result.get("rules_fired", 0),
            "user_activated": adapter_result.get("user_state", {}).get("is_activated", False),
            "guidelines_firings": firings,
            "has_error": has_error,
        })

    return {
        "trajectory_id": traj_path.stem,
        "total_actions": len(events),
        "timeline": timeline,
    }


def main():
    traj_path = PILOT_DIR / f"{TRAJ_ID}.json"
    if not traj_path.exists():
        traj_path = PILOT_DIR / f"{TRAJ_ID}.traj"
    if not traj_path.exists():
        raise FileNotFoundError(f"trajectory not found: {TRAJ_ID}")

    print(f"replaying {traj_path.name}...")
    result = replay_trajectory(traj_path)

    output_path = PILOT_DIR / "guidelines_replay.json"
    output_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"saved: {output_path}")

    # Quick summary to stdout
    n_actions = result["total_actions"]
    n_with_firings = sum(1 for t in result["timeline"] if t["guidelines_firings"])
    by_trigger = {}
    for t in result["timeline"]:
        for f in t["guidelines_firings"]:
            by_trigger[f["trigger"]] = by_trigger.get(f["trigger"], 0) + 1

    print(f"\nactions: {n_actions}")
    print(f"actions with at least one intervention firing: {n_with_firings}")
    print(f"firings by trigger:")
    for trigger, count in sorted(by_trigger.items(), key=lambda x: -x[1]):
        print(f"  {trigger}: {count}")


if __name__ == "__main__":
    main()
