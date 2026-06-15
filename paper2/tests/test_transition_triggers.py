"""Unit tests for Phase-2 transition triggers T1-T4 on synthetic
StateHistory sequences. Deterministic; no trajectory data required.

Each test constructs a StateHistory by hand and asserts the trigger's
verdict on the final action. neg_sum_5 is driven through `frustration`
alone (the other four negative emotions held at 0) so the synthetic
neg_sum_5 equals the frustration value, which keeps the sequences readable
while exercising the exact pre-registered thresholds.
"""
from __future__ import annotations
import pytest

from heart_guidelines.state_history import StateHistory, HistoryEntry
from heart_guidelines.transition_triggers import (
    trigger_velocity_spike,
    trigger_acceleration_onset,
    trigger_saturation_entry,
    trigger_plateau_no_recovery,
    T1_VELOCITY_THRESHOLD,
    T2_ACCEL_THRESHOLD,
)


def _vec(frustration=0.0, **extra):
    """An 18-ish emotion dict; only the keys triggers read need to be real.
    neg_sum_5 = frustration + anger + fear + confusion + vengeance; we drive
    via frustration and leave the rest 0 unless overridden."""
    base = {
        "frustration": frustration, "anger": 0.0, "fear": 0.0,
        "confusion": 0.0, "vengeance": 0.0,
        "happiness": 0.0, "pride": 0.0, "hope": 0.0, "curiosity": 0.0,
    }
    base.update(extra)
    return base


def _history(frustrations, **kw):
    """Build a StateHistory whose entries carry the given frustration series.
    Returns (history, last_state) where last_state is the final vector (the
    'current action' state passed to the trigger)."""
    h = StateHistory(max_size=50)
    states = [_vec(frustration=f, **kw) for f in frustrations]
    for i, s in enumerate(states):
        h.append(HistoryEntry(
            action_index=i, tool_name="t", tool_args={}, state=s,
            reflective_flag=False, has_error=False, rules_fired=0,
        ))
    return h, states[-1]


def _ctx(history):
    return {"history": history, "reflective_flag": False}


# --- T1 velocity_spike: ramp / step -----------------------------------------

def test_t1_step_above_threshold_fires():
    # neg_sum_5 jumps 0.0 -> 0.6 over a 3-window (first diff 0.6 >= 0.5)
    h, last = _history([0.0, 0.0, 0.6])
    assert trigger_velocity_spike(last, _ctx(h)) is True


def test_t1_gentle_ramp_below_threshold_does_not_fire():
    # rises 0.1 per action; over 3-window the first diff is 0.2 < 0.5
    h, last = _history([0.1, 0.2, 0.3, 0.4])
    assert trigger_velocity_spike(last, _ctx(h)) is False


def test_t1_exactly_at_threshold_fires():
    h, last = _history([0.1, 0.1, 0.6])  # diff = 0.5 == threshold (>=)
    assert abs((0.6 - 0.1) - T1_VELOCITY_THRESHOLD) < 1e-12
    assert trigger_velocity_spike(last, _ctx(h)) is True


def test_t1_insufficient_history_returns_false():
    h, last = _history([0.0, 0.9])  # only 2 < T1_WINDOW(3)
    assert trigger_velocity_spike(last, _ctx(h)) is False


# --- T2 acceleration_onset: accelerating vs linear --------------------------

def test_t2_accelerating_fires():
    # neg_sum_5: ...,0.0,0.1,0.5 -> d1=0.1, d2=0.4, accel=0.3 >= 0.3
    h, last = _history([0.0, 0.0, 0.0, 0.1, 0.5])
    assert trigger_acceleration_onset(last, _ctx(h)) is True


def test_t2_linear_ramp_zero_acceleration_does_not_fire():
    # constant slope 0.1 -> accel 0
    h, last = _history([0.0, 0.1, 0.2, 0.3, 0.4])
    assert trigger_acceleration_onset(last, _ctx(h)) is False


def test_t2_requires_5_history():
    # accelerating but only 4 history entries -> below T2_MIN_HISTORY
    h, last = _history([0.0, 0.0, 0.1, 0.5])
    assert trigger_acceleration_onset(last, _ctx(h)) is False


def test_t2_exactly_at_threshold_fires():
    # d1=0.0, d2=0.3 -> accel 0.3 == threshold
    h, last = _history([0.0, 0.2, 0.2, 0.2, 0.5])
    a, b, c = 0.2, 0.2, 0.5
    assert abs(((c - b) - (b - a)) - T2_ACCEL_THRESHOLD) < 1e-12
    assert trigger_acceleration_onset(last, _ctx(h)) is True


# --- T3 saturation_entry: rising edge + hysteresis (oscillation) ------------

def test_t3_rising_edge_fires_on_crossing():
    # 0.6 -> 0.75 crosses 0.7 upward
    h, last = _history([0.6, 0.75])
    assert trigger_saturation_entry(last, _ctx(h)) is True


def test_t3_does_not_refire_while_staying_high():
    # crosses at idx1, stays high; final step is high->high, not a crossing
    h, last = _history([0.6, 0.75, 0.8, 0.9])
    assert trigger_saturation_entry(last, _ctx(h)) is False


def test_t3_rearms_only_after_dropping_below_0_5():
    # cross (fire) -> stay high -> drop to 0.4 (re-arm) -> cross again (fire)
    h, last = _history([0.6, 0.75, 0.8, 0.4, 0.75])
    assert trigger_saturation_entry(last, _ctx(h)) is True


def test_t3_no_rearm_if_only_drops_to_0_6():
    # drops to 0.6 (above rearm 0.5) then back up -> still disarmed -> no fire
    h, last = _history([0.6, 0.75, 0.6, 0.75])
    assert trigger_saturation_entry(last, _ctx(h)) is False


def test_t3_oscillation_below_threshold_never_fires():
    h, last = _history([0.2, 0.5, 0.3, 0.6, 0.4, 0.69])
    assert trigger_saturation_entry(last, _ctx(h)) is False


# --- T4 plateau_no_recovery: plateau vs moving --------------------------------

def test_t4_high_flat_no_positive_fires():
    # neg_sum_5 ~1.6 flat over last 3, no positive > 0.3
    h, last = _history([1.6, 1.6, 1.6])
    assert trigger_plateau_no_recovery(last, _ctx(h)) is True


def test_t4_below_floor_does_not_fire():
    # flat but neg_sum_5 = 1.4 < 1.5
    h, last = _history([1.4, 1.4, 1.4])
    assert trigger_plateau_no_recovery(last, _ctx(h)) is False


def test_t4_high_but_moving_does_not_fire():
    # neg_sum_5 high but changing by 0.2 over the window (> 0.05 flatness)
    h, last = _history([1.5, 1.6, 1.8])
    assert trigger_plateau_no_recovery(last, _ctx(h)) is False


def test_t4_positive_emotion_present_does_not_fire():
    # high + flat but curiosity 0.5 > 0.3 -> recovery signal present
    h, last = _history([1.6, 1.6, 1.6], curiosity=0.5)
    assert trigger_plateau_no_recovery(last, _ctx(h)) is False


# --- guards: no context / empty history -------------------------------------

@pytest.mark.parametrize("trig", [
    trigger_velocity_spike, trigger_acceleration_onset,
    trigger_saturation_entry, trigger_plateau_no_recovery,
])
def test_no_context_returns_false(trig):
    assert trig(_vec(0.9), None) is False
