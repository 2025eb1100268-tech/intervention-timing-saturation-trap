"""Unit tests for the Phase-8 HEART-free instruments (I1 leaky accumulator,
I1 edge trigger, I2 sample-time CUSUM) on synthetic error sequences.
Deterministic; no trajectory data; no heart_* imports.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.generality_sweep import (
    i1_series, i1_level_metrics, i1_edge_fires, i2_fires,
    LAMBDA, STEP, LEVEL, REARM, DT_GRID,
)


# --- I1 on all-error ---------------------------------------------------------
def test_i1_all_error_dt0_crosses_at_fifth_error():
    # dt=0: pure accumulator, s after i-th error = 0.15*(i+1) (clamped).
    # 0.15*5 = 0.75 >= 0.7 -> first crossing at index 4.
    s = i1_series([1] * 12, 0)
    m = i1_level_metrics(s)
    assert abs(s[4] - 0.75) < 1e-12
    assert m["first_cross"] == 4
    assert m["persist"] == 100.0      # no decay -> stays up
    assert m["max_s"] == 1.0          # clamps at 1.0 eventually


def test_i1_all_error_large_dt_asymptote():
    # At dt=600 the decay factor is 2^-4 = 0.0625; the geometric asymptote is
    # 0.15/(1-0.0625) = 0.16 < 0.7 -> never crosses.
    s = i1_series([1] * 50, 600)
    m = i1_level_metrics(s)
    assert m["crosses"] is False
    assert m["max_s"] < 0.2


# --- I1 on no-error ----------------------------------------------------------
def test_i1_no_error_never_moves():
    for dt in (0, 60, 600):
        s = i1_series([0] * 30, dt)
        assert max(s) == 0.0
        assert i1_level_metrics(s)["crosses"] is False
        assert i1_edge_fires(s) == []


# --- I1 on alternating -------------------------------------------------------
def test_i1_alternating_dt0_crosses_at_fifth_error():
    # errors at even indices; at dt=0 nothing decays, so the 5th error
    # (index 8) brings s to 0.75.
    e = [1, 0] * 10
    s = i1_series(e, 0)
    assert i1_level_metrics(s)["first_cross"] == 8


def test_i1_alternating_large_dt_never_crosses():
    e = [1, 0] * 25
    m = i1_level_metrics(i1_series(e, 600))
    assert m["crosses"] is False


# --- I1 on single burst ------------------------------------------------------
def test_i1_single_burst_dt0_persists_after_burst():
    # 5-error burst then clean: at dt=0 there is no decay, so s stays at 0.75
    # for the rest of the trajectory (accumulator regime).
    e = [1] * 5 + [0] * 20
    s = i1_series(e, 0)
    m = i1_level_metrics(s)
    assert m["first_cross"] == 4
    assert m["persist"] == 100.0
    assert i1_edge_fires(s) == [4]    # single rising edge


def test_i1_single_burst_dt60_dies():
    # dt=60: per-step decay exp(-ln2/150*60) ~ 0.7579; burst sum
    # 0.15*(1+r+r^2+r^3+r^4) ~ 0.527 < 0.7 -> never crosses.
    e = [1] * 5 + [0] * 20
    m = i1_level_metrics(i1_series(e, 60))
    assert m["crosses"] is False


# --- I1 edge: hysteresis and re-arm ------------------------------------------
def test_i1_edge_rearms_only_below_0_5():
    # dt=15 (decay ~0.933/step): a 6-error burst reaches ~0.76 (crosses);
    # 12 clean steps decay to ~0.33 (< 0.5 -> re-arm); a second 6-error
    # burst re-crosses -> exactly two edge fires.
    e = [1] * 6 + [0] * 12 + [1] * 6
    s = i1_series(e, 15)
    # confirm the structure the test assumes: crossed, decayed below re-arm
    assert max(s[:6]) >= LEVEL
    assert min(s[6:18]) < REARM
    assert max(s[18:]) >= LEVEL
    fires = i1_edge_fires(s)
    assert len(fires) == 2


def test_i1_edge_no_refire_without_rearm():
    # dt=0: after crossing, s never decays below 0.5, so a second burst does
    # NOT produce a second edge fire.
    e = [1] * 5 + [0] * 10 + [1] * 5
    s = i1_series(e, 0)
    assert i1_edge_fires(s) == [4]


# --- I2 CUSUM -----------------------------------------------------------------
def test_i2_all_error_fires_from_second_error():
    # g: 0.9, 1.8, ... -> first fire at index 1.
    assert i2_fires([1] * 6, 0)[0] == 1


def test_i2_no_error_never_fires():
    assert i2_fires([0] * 40, 0) == []


def test_i2_two_errors_with_short_gap_fire():
    # 0.9 then 8 clean (-0.8 -> 0.1) then error -> 1.0 -> fires.
    e = [1] + [0] * 8 + [1]
    assert i2_fires(e, 0) == [9]


def test_i2_two_errors_with_long_gap_do_not_fire():
    # 0.9 then 10 clean (floors near 0) then error -> 0.9 < 1.0.
    e = [1] + [0] * 10 + [1]
    assert i2_fires(e, 0) == []


def test_i2_dt_invariance_exact():
    # The defining property: identical fire indices at every grid dt.
    e = [1, 1, 0, 1, 0, 0, 1, 1, 1, 0] * 3
    ref = i2_fires(e, 0)
    for dt in DT_GRID:
        assert i2_fires(e, dt) == ref
