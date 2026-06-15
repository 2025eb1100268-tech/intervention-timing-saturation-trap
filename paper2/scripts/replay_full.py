"""Canonical full-state replay artifact generator.

Replays one or more SWE-bench trajectories through the UNMODIFIED
EmotionEngine + ClaudeCodeAdapter + GuidelinesEngine and persists a
complete per-action state record to data/swebench_pilot/fullstate_<id>.json.

This is the canonical state artifact for the follow-up paper (transition-
aware triggers need the full 18-vector + trend + volatility per action,
which none of the existing artifacts persist). It changes NO scientific
behavior: the engine, adapter, signal rules, and triggers are all imported
and run exactly as scripts/replay_with_guidelines.py runs them, in the same
order, with the same StateHistory construction.

TIMING / WHEN STATE IS CAPTURED
-------------------------------
For each action we call `adapter.observe(event)` first (which applies that
action's signals to the engine), THEN read engine.get_emotion_vector() and
engine.get_state(). So the persisted `vector`, `trend`, `volatility`,
`neg_sum_*`, and `reflective_flag` are the POST-ACTION state -- the exact
state the GuidelinesEngine sees when it evaluates triggers for this action.
This matches replay_with_guidelines.py and saturation_replay.py.

`get_emotion_vector()` / `get_state()` call `_tick_decay(0.0)` internally,
which is a no-op (the engine's `if dt == 0: return` guard), so reading state
does not mutate it. Order of reads therefore does not matter.

Usage:
    python scripts/replay_full.py astropy__astropy-13398
    python scripts/replay_full.py astropy__astropy-13398 astropy__astropy-13033
    python scripts/replay_full.py --all
    python scripts/replay_full.py --all --force      # re-replay even if exists

Run from the repository root (relative data/ paths require it).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

from heart_core.engine import EmotionEngine
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter
from heart_adapters.claude_code.trajectory import parse_trajectory_file
from heart_guidelines.guidelines_engine import GuidelinesEngine
from heart_guidelines.state_history import StateHistory, HistoryEntry
from heart_guidelines.cooldown import CooldownGuidelines

# Try to read an engine version symbol without modifying heart_core.
try:
    import heart_core as _heart_core
    ENGINE_VERSION = getattr(_heart_core, "__version__", None) or "unversioned"
except Exception:
    ENGINE_VERSION = "unversioned"

SCHEMA_VERSION = "1.2"  # 1.1 adds vector_post_decay; 1.2 adds transition_firings

PILOT_DIR = Path("data/swebench_pilot")

# The five A6 negative-set emotions and the A8 four-set (vengeance dropped).
NEG_5 = ("frustration", "anger", "fear", "confusion", "vengeance")
NEG_4 = ("frustration", "anger", "fear", "confusion")


def _check_cwd() -> None:
    if not PILOT_DIR.exists():
        sys.stderr.write(
            f"ERROR: {PILOT_DIR} not found. Run from the repository root "
            f"(current cwd: {Path.cwd()}).\n"
        )
        sys.exit(2)


def discover_all_trajectories() -> List[str]:
    """Glob real trajectory files only.

    Real files are named 'astropy__astropy-<n>.json'. The saturation_*,
    fullstate_*, guidelines_replay, pilot_run_log, and *_report files are
    explicitly excluded by prefix/substring so the glob can never pick them
    up even if naming changes.
    """
    out = []
    for p in sorted(PILOT_DIR.glob("astropy__astropy-*.json")):
        name = p.name
        if any(tok in name for tok in ("saturation_", "fullstate_", "replay", "report")):
            continue
        out.append(p.stem)
    return out


def replay_one(traj_id: str, dt_seconds: float = 0.0) -> Dict[str, Any]:
    """Replay a single trajectory, returning the full-state artifact dict.

    Mirrors scripts/replay_with_guidelines.py:replay_trajectory exactly --
    same engine/adapter/guidelines/history construction and evaluation order.

    dt_seconds (Phase 3): synthetic, uniform inter-action time fed to the
    engine's decay. Before each action after the first, the caller calls
    engine._tick_decay(dt_seconds) explicitly. This is the ONLY injection
    point; heart_core is not modified.

    Composition (verified against heart_core/engine.py):
      - _tick_decay(dt) with dt>0 applies exponential decay toward BASELINE
        with momentum modulation (trend>0.04 -> x0.85, trend<-0.04 -> x1.15),
        then rebalance/normalize/snapshot, and sets last_ts.
      - adapter.observe() -> _apply_event() -> _tick_decay(0.0) returns
        immediately (the `if dt == 0: return` guard), so the internal tick
        stays a no-op and ALL decay is carried by the explicit pre-tick.
      - For dt_seconds == 0 we skip the explicit pre-tick entirely, so this
        path is byte-identical to Phase 2 (schema 1.2) modulo the dt field.
    """
    traj_path = PILOT_DIR / f"{traj_id}.json"
    if not traj_path.exists():
        # Phase 5: batch2 raw trajectories live in a subdirectory.
        alt = PILOT_DIR / "batch2" / f"{traj_id}.json"
        if alt.exists():
            traj_path = alt
        else:
            raise FileNotFoundError(f"trajectory not found: {traj_path}")

    events = parse_trajectory_file(traj_path)

    engine = EmotionEngine()
    adapter = ClaudeCodeAdapter(engine)
    guidelines = GuidelinesEngine()
    # Phase 2: transition triggers evaluated through the cooldown wrapper.
    # Separate from `guidelines` so the A6/A8/A9 firing set is untouched.
    cooldown = CooldownGuidelines(guidelines)
    history = StateHistory(max_size=10)

    timeline: List[Dict[str, Any]] = []
    for idx, event in enumerate(events):
        # 0a) Phase 3 decay injection. Advance the engine by dt_seconds of
        #     inter-action time BEFORE this action's event. Skipped for the
        #     first action (no predecessor) and when dt==0 (keeps the dt=0
        #     path byte-identical to Phase 2). The internal _tick_decay(0.0)
        #     inside observe() remains a no-op, so this pre-tick carries all
        #     decay. Momentum modulation inside _tick_decay is intentionally
        #     left active -- it is part of the model under test.
        if dt_seconds > 0 and idx >= 1:
            engine._tick_decay(float(dt_seconds))

        # 0) snapshot the engine vector BEFORE applying this action's event.
        #    Semantics of "vector_post_decay": the state after inter-action
        #    decay but before this action's event. The engine applies decay
        #    inside _apply_event via _tick_decay(0.0); per the Task 1a dt
        #    audit, dt is always 0 on the replay path, so decay is a no-op and
        #    the pre-observe() state is bit-identical to the engine's internal
        #    "after decay, before event" state. get_emotion_vector() also calls
        #    _tick_decay(0.0) (no-op), so this read does not mutate state.
        vector_post_decay = {
            emo: float(v) for emo, v in engine.get_emotion_vector().items()
        }

        # 1) apply this action's signals to the engine
        adapter_result = adapter.observe(event)

        # 2) read POST-ACTION state (non-mutating; see module docstring)
        vector = {emo: float(v) for emo, v in engine.get_emotion_vector().items()}
        engine_state = engine.get_state()
        reflective = bool(engine_state.get("reflective", False))
        has_error = event.has_error()

        # 3) append to history BEFORE evaluating guidelines (reference order)
        history.append(HistoryEntry(
            action_index=idx,
            tool_name=event.tool_name,
            tool_args=event.tool_args or {},
            state=vector,
            reflective_flag=reflective,
            has_error=has_error,
            rules_fired=adapter_result.get("rules_fired", 0),
            reasoning_text=event.reasoning_text or "",
        ))

        # 4) evaluate guidelines with the same context the reference builds
        context = {"reflective_flag": reflective, "history": history}
        interventions = guidelines.evaluate(vector, context=context)

        firings = [
            {
                "trigger": iv.triggered_by,
                "kind": iv.kind.value,
                "severity": iv.severity,
            }
            for iv in interventions
        ]

        # 4b) Phase-2 transition triggers via the cooldown wrapper. Same
        # context, same post-event vector, same action_index. Records gross
        # firings each with a `suppressed` flag (net = not suppressed).
        transition_firings = cooldown.evaluate(
            vector, context=context, action_index=idx
        )

        signals_applied = [
            {"emotion": s["emotion"], "delta": s["delta"]}
            for s in adapter_result.get("applied", [])
        ]

        neg_sum_5 = sum(vector.get(e, 0.0) for e in NEG_5)
        neg_sum_4 = sum(vector.get(e, 0.0) for e in NEG_4)

        timeline.append({
            "action_index": idx,
            "tool_name": event.tool_name,
            "has_error": has_error,
            "signals_applied": signals_applied,
            "vector": vector,
            "vector_post_decay": vector_post_decay,
            "neg_sum_5": neg_sum_5,
            "neg_sum_4": neg_sum_4,
            "reflective_flag": reflective,
            "trend": {e: float(v) for e, v in engine_state.get("trend", {}).items()},
            "volatility": {e: float(v) for e, v in engine_state.get("volatility", {}).items()},
            "guidelines_firings": firings,
            "transition_firings": transition_firings,
        })

    # Canonical (dt=0) artifacts keep schema 1.2 and omit dt_seconds, so the
    # existing fullstate_<id>.json files are unchanged. The Phase-3 dt sweep
    # (dt_seconds passed explicitly, including an explicit 0 via the sweep)
    # stamps schema 1.3 and records dt_seconds.
    out: Dict[str, Any] = {
        "trajectory_id": traj_id,
        "total_actions": len(events),
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "timeline": timeline,
    }
    return out


def write_artifact(traj_id: str, force: bool = False) -> Path:
    out_path = PILOT_DIR / f"fullstate_{traj_id}.json"
    if out_path.exists() and not force:
        print(f"  skip (exists): {out_path.name}  -- use --force to regenerate")
        return out_path
    artifact = replay_one(traj_id)
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    # quick A6 summary for operator confidence
    tl = artifact["timeline"]
    n = len(tl)
    def rate(trig):
        c = sum(1 for e in tl if any(f["trigger"] == trig for f in e["guidelines_firings"]))
        return c, (100 * c / n if n else 0.0)
    sf = rate("sustained_frustration")
    sva = rate("same_valence_accumulation")
    hc = rate("high_confusion_no_reflection")
    print(f"  wrote {out_path.name}: {n} actions | A6 sf={sf[0]} ({sf[1]:.1f}%) "
          f"sva={sva[0]} ({sva[1]:.1f}%) hc={hc[0]} ({hc[1]:.1f}%)")
    return out_path


# --- Phase 3: dt sweep ------------------------------------------------------
SWEEP_SCHEMA_VERSION = "1.3"  # adds top-level dt_seconds


def _fmt_dt(dt) -> str:
    """Filename token for a dt value: integers render without a decimal."""
    f = float(dt)
    return str(int(f)) if f == int(f) else str(f)


def write_sweep_artifact(traj_id: str, dt_seconds: float, force: bool = False) -> Path:
    """Write a dt-sweep artifact fullstate_dt<dt>_<id>.json (schema 1.3).
    Never overwrites the canonical fullstate_<id>.json."""
    out_path = PILOT_DIR / f"fullstate_dt{_fmt_dt(dt_seconds)}_{traj_id}.json"
    if out_path.exists() and not force:
        print(f"  skip (exists): {out_path.name}  -- use --force to regenerate")
        return out_path
    artifact = replay_one(traj_id, dt_seconds=float(dt_seconds))
    artifact["schema_version"] = SWEEP_SCHEMA_VERSION
    artifact["dt_seconds"] = float(dt_seconds)
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    tl = artifact["timeline"]
    n = len(tl)
    sf = sum(1 for e in tl if any(f["trigger"] == "sustained_frustration"
                                  for f in e["guidelines_firings"]))
    max_fr = max((e["vector"]["frustration"] for e in tl), default=0.0)
    print(f"  wrote {out_path.name}: {n} actions | dt={_fmt_dt(dt_seconds)}s | "
          f"max_frust={max_fr:.3f} | A6 sf={sf}")
    return out_path


def main():
    _check_cwd()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    force = "--force" in flags

    # --dt <seconds> : write a sweep artifact instead of the canonical one.
    dt_value = None
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--dt" and i + 1 < len(argv):
            dt_value = float(argv[i + 1])
        elif a.startswith("--dt="):
            dt_value = float(a.split("=", 1)[1])
    # the dt numeric value is a positional-looking arg; strip it from traj args
    if dt_value is not None:
        args = [a for a in args if a != _fmt_dt(dt_value) and a != str(dt_value)]

    if "--all" in flags:
        traj_ids = discover_all_trajectories()
        if not traj_ids:
            sys.stderr.write("No trajectory files found to replay.\n")
            sys.exit(1)
    elif args:
        traj_ids = args
    else:
        print("usage: python scripts/replay_full.py <traj_id> [<traj_id> ...] | --all [--force]")
        sys.exit(1)

    if dt_value is not None:
        print(f"replay_full DT-SWEEP: {len(traj_ids)} trajectory(ies) at "
              f"dt={_fmt_dt(dt_value)}s, engine_version={ENGINE_VERSION}")
        for tid in traj_ids:
            write_sweep_artifact(tid, dt_value, force=force)
    else:
        print(f"replay_full: {len(traj_ids)} trajectory(ies), engine_version={ENGINE_VERSION}")
        for tid in traj_ids:
            write_artifact(tid, force=force)


if __name__ == "__main__":
    main()
