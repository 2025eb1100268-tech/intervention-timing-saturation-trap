"""Extended A10 LLM-as-judge sweep: 2 conditions x N models x 3 interventions.

Additive to scripts/llm_calibration.py. Does NOT modify the original A10 data,
rubric, or trigger code. Writes to data/swebench_pilot/llm_eval_extended/.

Reuses VERBATIM the RUBRIC and SYSTEM_PROMPT from scripts/llm_calibration.py.
Two context conditions:

  windowed  -- last 3 thoughts only (matches original A10 exactly).
  macro     -- the full running trajectory so far: every prior thought,
               tool call, and observation up to the current action,
               each item truncated to keep prompts tractable.

Usage:
    python scripts/llm_calibration_sweep.py --model gpt-5.4-mini --condition windowed --intervention pause
    python scripts/llm_calibration_sweep.py --model gpt-5.4 --condition macro --intervention reflect

Or run all combos for a model:
    python scripts/llm_calibration_sweep.py --model gpt-5.4-mini --all
"""

from __future__ import annotations
import argparse
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
OUT_DIR = PILOT_DIR / "llm_eval_extended"
TRAJ_ID = "astropy__astropy-13398"

# Per-item truncation in MACRO context. Chosen to keep last-action prompt
# under ~25k input tokens for the longest trajectory we are evaluating.
MACRO_THOUGHT_CHARS = 600
MACRO_ACTION_CHARS = 200
MACRO_OBS_CHARS = 400
WINDOWED_CONTEXT_N = 3
WINDOWED_THOUGHT_CHARS = 600


# VERBATIM COPY from scripts/llm_calibration.py -- do not modify.
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

# VERBATIM COPY from scripts/llm_calibration.py -- do not modify.
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


def _action_text(event) -> str:
    args = event.tool_args or {}
    if "command" in args:
        return f"command: {str(args['command'])}"
    elif "path" in args:
        return f"editing path: {args['path']}"
    return f"args: {json.dumps(args, default=str)}"


def build_windowed_prompt(intervention: str, idx: int, total: int,
                          events: List, current_event) -> str:
    """3 prior thoughts only -- matches original A10 verbatim."""
    rubric_text = RUBRIC[intervention]
    start = max(0, idx - WINDOWED_CONTEXT_N)
    context_thoughts = [
        events[i].reasoning_text or ""
        for i in range(start, idx)
        if events[i].reasoning_text
    ]

    context_block = ""
    if context_thoughts:
        for i, t in enumerate(context_thoughts):
            offset = len(context_thoughts) - i
            context_block += f"\n[{offset} action(s) ago]: {t[:WINDOWED_THOUGHT_CHARS]}\n"
    else:
        context_block = "\n(no prior context -- this is action 0)\n"

    action_desc = _action_text(current_event)[:500]

    return f"""Rubric for this question:
{rubric_text}

You are reviewing action {idx} of {total} in this session.

--- RECENT CONTEXT ---{context_block}

--- CURRENT ACTION (action {idx}) ---

THOUGHT: {(current_event.reasoning_text or "(empty)")[:1500]}

ACTION: {action_desc}

OBSERVATION: {(current_event.result_text or "(empty)")[:600]}

---

Apply the rubric. Should the agent be told to {intervention.upper()}
before this action?

Respond with JSON ONLY in this exact shape:
{{"fire": true|false, "confidence": <float 0.0-1.0>, "reason": "<one sentence>"}}
"""


def build_macro_prompt(intervention: str, idx: int, total: int,
                       events: List, current_event) -> str:
    """Full running trajectory so far. Per-item truncation applied."""
    rubric_text = RUBRIC[intervention]

    if idx == 0:
        context_block = "\n(no prior context -- this is action 0)\n"
    else:
        parts = []
        for i in range(idx):
            ev = events[i]
            thought = (ev.reasoning_text or "(empty)")[:MACRO_THOUGHT_CHARS]
            act = _action_text(ev)[:MACRO_ACTION_CHARS]
            obs = (ev.result_text or "(empty)")[:MACRO_OBS_CHARS]
            parts.append(
                f"\n[Action {i}]\n"
                f"  THOUGHT: {thought}\n"
                f"  ACTION: {act}\n"
                f"  OBSERVATION: {obs}\n"
            )
        context_block = "".join(parts)

    action_desc = _action_text(current_event)[:500]

    return f"""Rubric for this question:
{rubric_text}

You are reviewing action {idx} of {total} in this session. The agent's
FULL trajectory up to this point is provided below. Use it.

--- FULL TRAJECTORY SO FAR ---{context_block}

--- CURRENT ACTION (action {idx}) ---

THOUGHT: {(current_event.reasoning_text or "(empty)")[:1500]}

ACTION: {action_desc}

OBSERVATION: {(current_event.result_text or "(empty)")[:600]}

---

Apply the rubric. Should the agent be told to {intervention.upper()}
before this action?

Respond with JSON ONLY in this exact shape:
{{"fire": true|false, "confidence": <float 0.0-1.0>, "reason": "<one sentence>"}}
"""


def build_prompt(condition: str, intervention: str, idx: int, total: int,
                 events: List, current_event) -> str:
    if condition == "windowed":
        return build_windowed_prompt(intervention, idx, total, events, current_event)
    elif condition == "macro":
        return build_macro_prompt(intervention, idx, total, events, current_event)
    raise ValueError(f"unknown condition: {condition}")


def estimate_cost(model: str, total_tokens: int) -> float:
    """Rough cost estimate. 80/20 input/output split, matching
    scripts/llm_calibration.py heuristic.
    """
    rates = {
        # (input $/Mtok, output $/Mtok). Mini matches the existing script.
        "gpt-5.4-mini": (0.75, 3.0),
        "gpt-5.4": (10.0, 30.0),  # rough flagship estimate
    }
    in_rate, out_rate = rates.get(model, (5.0, 15.0))
    est_input = total_tokens * 0.8
    est_output = total_tokens * 0.2
    return (est_input / 1_000_000) * in_rate + (est_output / 1_000_000) * out_rate


def safe_model_name(model: str) -> str:
    return model.replace(".", "p").replace("/", "_")


def run_eval(model: str, condition: str, intervention: str) -> Dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)

    traj_path = PILOT_DIR / f"{TRAJ_ID}.json"
    events = parse_trajectory_file(traj_path)
    total = len(events)

    print(f"\n=== {model} | {condition} | {intervention} | {total} actions ===")

    results = []
    total_tokens = 0

    for idx, event in enumerate(events):
        prompt = build_prompt(condition, intervention, idx, total, events, event)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            tu = response.usage.total_tokens if response.usage else None
            results.append({
                "action_index": idx,
                "fire": bool(parsed.get("fire", False)),
                "confidence": float(parsed.get("confidence", 0.0)),
                "reason": str(parsed.get("reason", ""))[:300],
                "tokens_used": tu,
                "error": None,
            })
            if tu:
                total_tokens += tu
        except Exception as e:
            results.append({
                "action_index": idx,
                "fire": False,
                "confidence": 0.0,
                "reason": "",
                "tokens_used": None,
                "error": repr(e)[:400],
            })
        marker = "FIRE" if results[-1]["fire"] else "    "
        err = f" ERROR" if results[-1]["error"] else ""
        if idx % 10 == 0 or results[-1]["fire"] or results[-1]["error"]:
            print(f"  [{idx:3d}/{total}] {marker} tok_tot={total_tokens}{err}")
        time.sleep(0.05)

    n_fired = sum(1 for r in results if r["fire"])
    n_errors = sum(1 for r in results if r["error"])
    cost = estimate_cost(model, total_tokens)

    output = {
        "trajectory_id": TRAJ_ID,
        "model": model,
        "condition": condition,
        "intervention": intervention,
        "total_actions": total,
        "total_tokens": total_tokens,
        "n_fired": n_fired,
        "n_errors": n_errors,
        "estimated_cost_usd": round(cost, 4),
        "results": results,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{safe_model_name(model)}_{condition}_{intervention}.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))

    print(f"  saved: {out_path}")
    print(f"  fired: {n_fired}/{total}  errors: {n_errors}  tokens: {total_tokens}  ~${cost:.3f}")
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--condition", choices=["windowed", "macro"])
    p.add_argument("--intervention", choices=["pause", "reflect", "clarify"])
    p.add_argument("--all", action="store_true",
                   help="Run all 6 combos (windowed+macro x pause+reflect+clarify) for this model")
    args = p.parse_args()

    if args.all:
        combos = [(c, i) for c in ("windowed", "macro")
                  for i in ("pause", "reflect", "clarify")]
        grand_total_tokens = 0
        grand_total_cost = 0.0
        for cond, intv in combos:
            out = run_eval(args.model, cond, intv)
            grand_total_tokens += out["total_tokens"]
            grand_total_cost += out["estimated_cost_usd"]
        print(f"\n=== Total {args.model}: tokens={grand_total_tokens}  ~${grand_total_cost:.3f} ===")
    else:
        if not args.condition or not args.intervention:
            print("ERROR: must specify --condition and --intervention unless --all", file=sys.stderr)
            sys.exit(1)
        run_eval(args.model, args.condition, args.intervention)


if __name__ == "__main__":
    main()
