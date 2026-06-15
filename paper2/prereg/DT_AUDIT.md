# Task 1a — dt audit: what time-delta the engine receives during replay

Reported **before** any Phase-2 coding, because the finding materially affects
how every Phase-2 transition result must be interpreted.

## Finding (one line)

**During replay the engine's decay is never invoked. `dt` is effectively
always 0.** Inter-action time decay does not happen; the affective state only
changes on actions that carry a signal, and is otherwise frozen bit-for-bit.

## The trace path (code)

1. **Parser → ActionEvent.** The aime-coder parser sets `ActionEvent.timestamp`
   to a synthetic ordinal, not a real clock value:
   - `_build_event_from_assistant`: `timestamp=float(idx)` ([trajectory.py:224](../../heart_adapters/claude_code/trajectory.py#L224))
   - spec-format turns: `timestamp=float(turn_index)` ([trajectory.py:257](../../heart_adapters/claude_code/trajectory.py#L257))
   - final conclude turn: `timestamp=float(len(prompt))` ([trajectory.py:171](../../heart_adapters/claude_code/trajectory.py#L171))
   The trace files carry **no real timestamps**; the field is a position index.

2. **ActionEvent.timestamp is never read on the replay path.** `adapter.observe()`
   ([adapter.py:26-67](../../heart_adapters/claude_code/adapter.py#L26-L67)) does not
   reference `event.timestamp` at all. It calls
   `engine._apply_event(emo, delta)` ([adapter.py:47](../../heart_adapters/claude_code/adapter.py#L47))
   once per signal.

3. **`_apply_event` ticks decay with a hardcoded 0.** [engine.py:287](../../heart_core/engine.py#L287):
   `self._tick_decay(0.0)`. And `_tick_decay` returns immediately when `dt==0`
   ([engine.py:260-261](../../heart_core/engine.py#L260-L261)): `if dt == 0: return`.

4. **The wall-clock decay path (`_tick_decay(None)`, which would compute
   `dt = now - last_ts`) is never called during replay.** Its only call site is
   `decay_emotions()` ([engine.py:515](../../heart_core/engine.py#L515)), which the
   adapter/replay never invokes. Every other `_tick_decay` call in the engine
   passes `0.0` (the getters at lines 668-733) or `1.0` (the `simulate_*`
   preview at line 409, also unused in replay).

Net: on the replay path the engine receives `dt = 0` on every tick, so the
exponential-decay term `exp(-λ·dt) = exp(0) = 1` — **no decay is ever applied.**

## Distribution of inter-action dt

There are two distinct quantities; both are reported.

### (a) The `dt` the engine actually decays on
Constant **0.0** for every action of every trajectory (synthetic/fixed).
Source: hardcoded `_tick_decay(0.0)` in `_apply_event`
([engine.py:287](../../heart_core/engine.py#L287)). min = median = max = **0.0**.

### (b) The `ActionEvent.timestamp` field (computed but unused for decay)
Synthetic ordinal `2·index` (the parser doubles because it pairs
assistant+user messages). Per trajectory, the inter-action difference of this
field:

| Trajectory | actions | timestamp-diff min / median / max |
|---|---|---|
| astropy-12907 | 28 | 2.0 / 2.0 / 2.0 |
| astropy-13033 | 59 | 2.0 / 2.0 / 2.0 |
| astropy-13236 | 44 | 2.0 / 2.0 / 2.0 |
| astropy-13398 | 56 | 2.0 / 2.0 / 4.0 |
| astropy-13453 | 31 | 2.0 / 2.0 / 2.0 |

(The one 4.0 gap in 13398 is a turn where an assistant message had no paired
user observation, so the ordinal skipped. It is **not** used by the engine.)

## Empirical confirmation

Reading `fullstate_astropy__astropy-13398.json`: of the 43 zero-signal actions
(no rule fired), **43/43 leave the full 18-vector unchanged to machine
precision** (max |Δ| across all dims = 0 exactly). Zero actions showed any
decay-driven drift. This is the direct observable consequence of `dt = 0`.

## Consequence for Phase 2 interpretation

- **"neg_sum_5 decay" is structurally zero on this pipeline.** Any
  decay-vs-event decomposition (Task 1c) will attribute ~100% of total
  variation to events and ~0% to decay, and the "fraction of actions where
  decay moved neg_sum_5 by <0.01" will be ~100% — **by construction, not as an
  empirical property of the affect model.** This must be stated in
  DYNAMICS_DECOMPOSITION.md so it is not misread as "decay is negligible on
  these traces."
- **The Saturation Trap mechanism is reinforced, not contradicted:** with no
  decay, once frustration is driven up it cannot relax between actions even in
  principle, so saturation is absolute. The follow-up paper's transition
  triggers operate on a state series that only moves on event-bearing actions.
- **Velocity/acceleration of neg_sum_5 are therefore event-driven step
  changes**, not smooth trajectories. T1/T2 first/second differences are
  differences of a piecewise-constant series. This is a property of the data
  pipeline the triggers must be read against.

No code was changed to produce this audit.
