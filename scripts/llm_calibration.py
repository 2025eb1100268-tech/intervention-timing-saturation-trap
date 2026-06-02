"""LLM-based trigger evaluation for one intervention type at a time.

Usage:
    python scripts/llm_calibration.py pause
    python scripts/llm_calibration.py reflect
    python scripts/llm_calibration.py clarify

For each action in the trajectory, sends a prompt to GPT-5.4-mini asking
whether the SPECIFIED intervention applies, using the annotators' exact
labeling rubric. Writes per-trigger JSON output for downstream calibration.

The LLM is given:
- The intervention type and rubric definition (verbatim from labeling task)
- The agent's thought, action, observation for the current step
- A short rolling context: previous 3 actions' thoughts only

The LLM returns:
- A boolean (should this intervention fire?)
- A confidence (0.0-1.0)
- A one-sentence reason

This script is calibration-only. It does NOT modify the live guidelines
layer.
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

from openai import OpenAI

# requires the proprietary HEART engine (not included; see README)
from heart_adapters.claude_code.trajectory import parse_trajectory_file


PILOT_DIR = Path("data/swebench_pilot")
TRAJ_ID = "astropy__astropy-13398"
MODEL = "gpt-5.4-mini"
CONTEXT_WINDOW = 3   # number of prior thoughts included as context


# Verbatim from the annotators' labeling rubric (see paper §4.2)
RUBRIC = {
    "pause": (
        "Should the LLM have been told to PAUSE before this action? "
        "A pause verdict means halt and reconsider, the current trajectory "
        "looks problematic. Examples: about to repeat a clearly-failing "
        "strategy, about to make a destructive move under accumulated "
        "frustration, about to commit while the previous attempts have all "
        "failed."
    ),
    "reflect": (
        "Should the LLM have been told to REFLECT before this action? "
        "A forced reflection means step back and consider alternatives, "
        "examine assumptions, look at the problem from a different angle. "
        "Less severe than pause. Appropriate when the agent is grinding "
        "without metacognition, running tests over and over without "
        "changing approach, making narrow edits when the problem is "
        "structural."
    ),
    "clarify": (
        "Should the LLM have been told to CLARIFY before this action? "
        "A clarify intervention means articulate what is unclear before "
        "proceeding. Appropriate when the agent is confused but plowing "
        "forward as if certain, searching aimlessly, making changes that "
        "don't address the actual error, hedging in reasoning but acting "
        "decisively anyway."
    ),
}


SYSTEM_PROMPT = (
    "You are a senior software engineer reviewing the in-progress session "
    "of an LLM coding agent in real time. You will be shown one action "
    "the agent is about to take, plus its recent reasoning history. You "
    "will be asked whether the agent should be told to perform a specific "
    "intervention before this action. Default to false. When uncertain, "
    "label false. Conservatism is correct. Apply the rubric exactly as "
    "stated; do not interpret it more liberally or strictly. Respond with "
    "JSON only."
)


def build_user_prompt(intervention: str, action_idx: int, total: int,
                       current_event, context_thoughts: List[str]) -> str:
    rubric_text = RUBRIC[intervention]

    context_block = ""
    if context_thoughts:
        for i, t in enumerate(context_thoughts):
            offset = len(context_thoughts) - i
            context_block += f"\n[{offset} action(s) ago]: {t[:600]}\n"
    else:
        context_block = "\n(no prior context -- this is action 0)\n"

    args = current_event.tool_args or {}
    if "command" in args:
        action_desc = f"command: {args['command'][:500]}"
    elif "path" in args:
        action_desc = f"editing path: {args['path']}"
    else:
        action_desc = f"args: {json.dumps(args, default=str)[:300]}"

    return f"""Rubric for this question:
{rubric_text}

You are reviewing action {action_idx} of {total} in this session.

--- RECENT CONTEXT ---{context_block}

--- CURRENT ACTION (action {action_idx}) ---

THOUGHT: {(current_event.reasoning_text or "(empty)")[:1500]}

ACTION: {action_desc}

OBSERVATION: {(current_event.result_text or "(empty)")[:600]}

---

Apply the rubric. Should the agent be told to {intervention.upper()}
before this action?

Respond with JSON ONLY in this exact shape:
{{"fire": true|false, "confidence": <float 0.0-1.0>, "reason": "<one sentence>"}}
"""


def evaluate_action(client: OpenAI, intervention: str, action_idx: int,
                     total: int, event, context_thoughts: List[str]) -> Dict[str, Any]:
    """Send one evaluation request. Returns parsed result dict or error."""
    user_prompt = build_user_prompt(intervention, action_idx, total,
                                      event, context_thoughts)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        return {
            "action_index": action_idx,
            "fire": bool(parsed.get("fire", False)),
            "confidence": float(parsed.get("confidence", 0.0)),
            "reason": str(parsed.get("reason", ""))[:300],
            "tokens_used": response.usage.total_tokens if response.usage else None,
            "error": None,
        }
    except Exception as e:
        return {
            "action_index": action_idx,
            "fire": False,
            "confidence": 0.0,
            "reason": "",
            "tokens_used": None,
            "error": repr(e),
        }


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in RUBRIC:
        print("usage: python scripts/llm_calibration.py {pause|reflect|clarify}")
        sys.exit(1)

    intervention = sys.argv[1]

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Load trajectory
    traj_path = PILOT_DIR / f"{TRAJ_ID}.json"
    if not traj_path.exists():
        traj_path = PILOT_DIR / f"{TRAJ_ID}.traj"
    events = parse_trajectory_file(traj_path)
    print(f"Loaded {len(events)} actions from {TRAJ_ID}")
    print(f"Evaluating intervention: {intervention}")
    print(f"Using model: {MODEL}")
    print()

    results = []
    total_tokens = 0

    for idx, event in enumerate(events):
        # Build rolling context: last CONTEXT_WINDOW thoughts
        start = max(0, idx - CONTEXT_WINDOW)
        context_thoughts = [
            events[i].reasoning_text or ""
            for i in range(start, idx)
            if events[i].reasoning_text
        ]

        result = evaluate_action(client, intervention, idx, len(events),
                                  event, context_thoughts)
        results.append(result)

        if result.get("tokens_used"):
            total_tokens += result["tokens_used"]

        marker = "FIRE" if result["fire"] else "    "
        err = f" ERROR: {result['error']}" if result["error"] else ""
        print(f"  [{idx:3d}/{len(events)}] {marker}  conf={result['confidence']:.2f}  {result['reason'][:80]}{err}")

        # Very mild rate limiting
        time.sleep(0.1)

    # Save
    output = {
        "trajectory_id": TRAJ_ID,
        "intervention": intervention,
        "model": MODEL,
        "context_window": CONTEXT_WINDOW,
        "total_actions": len(events),
        "total_tokens": total_tokens,
        "results": results,
    }

    output_path = PILOT_DIR / f"llm_eval_{intervention}.json"
    output_path.write_text(json.dumps(output, indent=2, default=str))

    n_fired = sum(1 for r in results if r["fire"])
    n_errors = sum(1 for r in results if r["error"])

    print()
    print("=" * 70)
    print(f"saved: {output_path}")
    print(f"fired: {n_fired} of {len(results)} actions")
    print(f"errors: {n_errors}")
    print(f"total tokens: {total_tokens}")

    # Rough cost estimate at GPT-5.4-mini rates
    # Approximate split: 80% input, 20% output (the prompt is much longer than the JSON)
    est_input = total_tokens * 0.8
    est_output = total_tokens * 0.2
    cost = (est_input / 1_000_000) * 0.75 + (est_output / 1_000_000) * 3.0
    print(f"estimated cost: ${cost:.3f}")


if __name__ == "__main__":
    main()
