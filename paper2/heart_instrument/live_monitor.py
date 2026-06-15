"""Phase 6 Task 5: live HEART monitor over a session JSONL.

Tails a heart_instrument session JSONL (hook or agent_runner format) while a
run is in progress, and for each new action:

  1. computes REAL elapsed dt from the previous record's timestamp,
  2. advances the frozen engine with an explicit `engine._tick_decay(dt)`
     pre-tick (the exact Phase-3 injection pattern -- heart_core unmodified;
     the internal _tick_decay(0.0) inside observe() stays a no-op),
  3. feeds the action through the unmodified ClaudeCodeAdapter,
  4. evaluates T3 (saturation_entry) through CooldownGuidelines and the A6
     triggers directly (A6 logged for contrast, never surfaced),
  5. prints a one-line alert if T3 net-fires.

LOG-ONLY: the monitor never writes to the session, never signals the agent,
never injects anything. It appends its own observations to
<out>/monitor_log.jsonl.

Usage (alongside a running session):
    python heart_instrument/live_monitor.py data/live_runs/runE/session.jsonl \
        --follow 600        # tail for up to 600 s
    python heart_instrument/live_monitor.py <session.jsonl>   # one pass, no tail
"""
from __future__ import annotations
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running as `python heart_instrument/live_monitor.py` from repo root:
# put the repo root (parent of this package) on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heart_core.engine import EmotionEngine
from heart_adapters.claude_code.adapter import ClaudeCodeAdapter
from heart_adapters.claude_code.events import ActionEvent
from heart_guidelines.guidelines_engine import GuidelinesEngine
from heart_guidelines.state_history import StateHistory, HistoryEntry
from heart_guidelines.cooldown import CooldownGuidelines
from heart_guidelines.triggers import (
    trigger_sustained_frustration,
    trigger_same_valence_accumulation,
    trigger_high_confusion_no_reflection,
)
from heart_instrument.convert import map_tool, parse_args_field


class LiveMonitor:
    def __init__(self, out_path: Path):
        self.engine = EmotionEngine()
        self.adapter = ClaudeCodeAdapter(self.engine)
        self.cooldown = CooldownGuidelines(GuidelinesEngine())
        self.history = StateHistory(max_size=10)
        self.out_path = out_path
        self.prev_ts = None
        self.idx = 0

    def process(self, record: dict):
        ts = datetime.fromisoformat(record["ts"])
        dt = 0.0 if self.prev_ts is None else max(0.0, (ts - self.prev_ts).total_seconds())
        self.prev_ts = ts

        # Phase-3 pattern: explicit real-dt pre-tick; internal tick stays no-op
        if dt > 0:
            self.engine._tick_decay(float(dt))

        raw_args = parse_args_field(record.get("tool_input", "{}"))
        tool, args = map_tool(record.get("tool_name", "unknown"), raw_args)
        event = ActionEvent(
            tool_name=tool, tool_args=args,
            reasoning_text=record.get("thought", "") or "",
            result_text=record.get("observation", "") or "",
            user_text=None, timestamp=float(self.idx), task_metadata={},
        )
        adapter_result = self.adapter.observe(event)

        vector = {k: float(v) for k, v in self.engine.get_emotion_vector().items()}
        engine_state = self.engine.get_state()
        reflective = bool(engine_state.get("reflective", False))

        self.history.append(HistoryEntry(
            action_index=self.idx, tool_name=event.tool_name,
            tool_args=event.tool_args or {}, state=vector,
            reflective_flag=reflective, has_error=event.has_error(),
            rules_fired=adapter_result.get("rules_fired", 0),
            reasoning_text=event.reasoning_text or "",
        ))
        context = {"reflective_flag": reflective, "history": self.history}

        transition = self.cooldown.evaluate(vector, context, action_index=self.idx)
        t3_net = [f for f in transition
                  if f["trigger"] == "saturation_entry" and not f["suppressed"]]

        a6 = {
            "sustained_frustration": bool(trigger_sustained_frustration(vector, context)),
            "same_valence_accumulation": bool(trigger_same_valence_accumulation(vector, context)),
            "high_confusion_no_reflection": bool(trigger_high_confusion_no_reflection(vector, context)),
        }

        entry = {
            "action_index": self.idx, "ts": record["ts"], "dt": round(dt, 3),
            "tool": tool, "frustration": round(vector["frustration"], 4),
            "neg_sum_5": round(sum(vector[e] for e in
                                   ("frustration", "anger", "fear", "confusion",
                                    "vengeance")), 4),
            "t3_net_fired": bool(t3_net),
            "transition_firings": transition,
            "a6": a6,  # logged for contrast, never surfaced as an alert
        }
        with open(self.out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if t3_net:
            print(f"[T3 ALERT] action {self.idx}: frustration crossed 0.7 "
                  f"(rising edge) -- frustration={vector['frustration']:.3f}, "
                  f"dt={dt:.1f}s", flush=True)
        self.idx += 1


def main():
    if len(sys.argv) < 2:
        print("usage: python heart_instrument/live_monitor.py <session.jsonl> "
              "[--follow <seconds>]")
        sys.exit(1)
    src = Path(sys.argv[1])
    follow = 0.0
    if "--follow" in sys.argv:
        follow = float(sys.argv[sys.argv.index("--follow") + 1])

    out = src.parent / "monitor_log.jsonl"
    out.write_text("", encoding="utf-8")
    mon = LiveMonitor(out)
    print(f"monitoring {src} -> {out} (follow={follow:.0f}s)", flush=True)

    pos = 0
    deadline = time.time() + follow
    while True:
        if src.exists():
            with open(src, "r", encoding="utf-8") as f:
                f.seek(pos)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            mon.process(json.loads(line))
                        except Exception as e:
                            print(f"[monitor] skip bad line: {e!r}", flush=True)
                pos = f.tell()
        if time.time() >= deadline:
            break
        time.sleep(1.0)

    print(f"monitor done: {mon.idx} actions processed; log: {out}", flush=True)


if __name__ == "__main__":
    main()
