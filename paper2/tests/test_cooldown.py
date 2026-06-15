"""Unit tests for CooldownGuidelines per-trigger refractory behavior.

Uses a stub GuidelinesEngine-like object whose evaluate_transition returns a
controlled set of interventions, so the cooldown logic is tested in
isolation from the trigger logic.
"""
from __future__ import annotations

from heart_guidelines.cooldown import CooldownGuidelines, REFRACTORY_ACTIONS
from heart_guidelines.base import Intervention, InterventionKind


def _iv(trigger, severity=0.8):
    return Intervention(
        kind=InterventionKind.PAUSE_VERDICT, severity=severity,
        message="m", rationale="r", triggered_by=trigger, metadata={},
    )


class _StubEngine:
    """evaluate_transition returns whatever was queued for each call."""
    def __init__(self, per_call):
        self._per_call = per_call
        self._i = 0

    def evaluate_transition(self, state, context=None):
        res = self._per_call[self._i] if self._i < len(self._per_call) else []
        self._i += 1
        return res


def test_refractory_constant_is_5():
    assert REFRACTORY_ACTIONS == 5


def test_fires_then_suppresses_for_5_then_allows():
    # Same trigger fires every action for 8 actions.
    stub = _StubEngine([[_iv("velocity_spike")] for _ in range(8)])
    cg = CooldownGuidelines(stub)
    verdicts = []
    for idx in range(8):
        out = cg.evaluate({}, {}, action_index=idx)
        verdicts.append(out[0]["suppressed"])
    # action 0: net fire (False). actions 1-5: suppressed (within 5).
    # action 6: (6-0)=6 > 5 => allowed again (False), then 7 suppressed.
    assert verdicts == [False, True, True, True, True, True, False, True]


def test_suppressed_firings_are_recorded_not_dropped():
    stub = _StubEngine([[_iv("velocity_spike")] for _ in range(3)])
    cg = CooldownGuidelines(stub)
    a0 = cg.evaluate({}, {}, action_index=0)
    a1 = cg.evaluate({}, {}, action_index=1)
    # both actions return a firing record; a1's is flagged suppressed
    assert len(a0) == 1 and a0[0]["suppressed"] is False
    assert len(a1) == 1 and a1[0]["suppressed"] is True
    assert a1[0]["trigger"] == "velocity_spike"


def test_independent_per_trigger_cooldowns():
    # T1 fires at action 0; T2 fires at action 1 -- different triggers, so
    # T2 is NOT suppressed by T1's cooldown.
    stub = _StubEngine([
        [_iv("velocity_spike")],
        [_iv("acceleration_onset")],
    ])
    cg = CooldownGuidelines(stub)
    a0 = cg.evaluate({}, {}, action_index=0)
    a1 = cg.evaluate({}, {}, action_index=1)
    assert a0[0]["suppressed"] is False
    assert a1[0]["suppressed"] is False  # different trigger, own cooldown


def test_cooldown_measured_from_last_NET_fire_not_gross():
    # Fire at 0 (net). Suppressed at 1..5. At 6 it nets again. The window for
    # the NEXT suppression is measured from 6, not from the suppressed 1..5.
    stub = _StubEngine([[_iv("velocity_spike")] for _ in range(9)])
    cg = CooldownGuidelines(stub)
    nets = []
    for idx in range(9):
        out = cg.evaluate({}, {}, action_index=idx)
        nets.append(not out[0]["suppressed"])
    # net fires at 0 and 6 only
    assert [i for i, n in enumerate(nets) if n] == [0, 6]


def test_reset_clears_state():
    stub = _StubEngine([[_iv("velocity_spike")], [_iv("velocity_spike")]])
    cg = CooldownGuidelines(stub)
    cg.evaluate({}, {}, action_index=0)       # net fire
    cg.reset()
    out = cg.evaluate({}, {}, action_index=1)  # after reset -> net fire again
    assert out[0]["suppressed"] is False


def test_no_firings_returns_empty():
    stub = _StubEngine([[]])
    cg = CooldownGuidelines(stub)
    assert cg.evaluate({}, {}, action_index=0) == []
