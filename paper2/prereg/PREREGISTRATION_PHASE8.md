# Pre-registration: Phase 8 — generality of cadence bistability

Committed BEFORE any Phase-8 computation. Pure post-processing of the
per-action `has_error` boolean already persisted in the fullstate timelines;
no engine replay, no heart_core imports in the new script. All constants
below are pre-registered; degenerate behavior is reported, not fixed; no
second parameterization is run.

---
Instruments, all over the per-action binary error stream e_i in {0,1}, evaluated on
the same 20 trajectories and the same dt grid {0, 1, 5, 15, 30, 60, 150, 300, 600} s:

I1 WALL-CLOCK LEAKY ACCUMULATOR (the HEART-free analog):
   s_0 = 0;  s_i = clamp01( s_{i-1} * exp(-lambda * dt) + 0.15 * e_i )
   lambda = ln(2)/150 (same half-life as HEART frustration, by design, to isolate
   the calibration choice). Level trigger: fire iff s_i >= 0.7.
   Edge trigger: fire on upward crossing of 0.7; re-arm when s falls below 0.5.
   Rationale for 0.15: the engine's repeated-error frustration delta; declared a
   priori, not tuned.

I2 SAMPLE-TIME CUSUM (the classical control, defined per-observation):
   g_0 = 0;  g_i = max(0, g_{i-1} + e_i - 0.10);  fire iff g_i >= 1.0
   k = 0.10, h = 1.0, declared a priori. By construction g has NO dt dependence.

Hypotheses:
H7: I1 reproduces the two-regime structure: at dt <= 1 s, the level trigger on I1 is
    a near-constant alarm post-first-crossing (persistence >= 90%) on the majority of
    trajectories that cross; at dt >= 60 s, s never reaches 0.7 on >= 18/20
    trajectories. Critical intervals fall in the same (1, 30] s band as HEART's.
H8: I2's fire pattern (set of firing action indices) is IDENTICAL at every dt for
    every trajectory (exact invariance).
H9: I1's edge trigger fires <= 3 times per trajectory at every dt.

Falsification: if I1 does not show the two-regime structure (e.g., never crosses 0.7
anywhere, or shows no dead regime), the paper's class-level claim is NOT supported
and Paper 2 remains scoped to HEART; this is reported as the primary Phase 8 finding.
If H8 fails, there is a bug — sample-time CUSUM cannot depend on dt; debug the
implementation, not the hypothesis.
---

## Implementation conventions (declared with the commitment)

- Indexing: the first action receives no decay (no preceding gap), matching
  every prior phase's replay convention: s_0 = clamp01(0.15 * e_0); for
  i >= 1, s_i = clamp01(s_{i-1} * exp(-lambda*dt) + 0.15 * e_i). I2
  analogously processes every action including the first: g_0 =
  max(0, 0 + e_0 - 0.10).
- Error stream source: `has_error` from `fullstate_dt0_<id>.json` (all 20).
  Assumption to verify before running: has_error is identical across the
  dt-variant fullstate files (dt does not change which actions error) —
  checked on 2 trajectories across all 9 dt values and reported.
- Critical interval for I1: same definition as Phase 5 (smallest grid dt
  with post-first-crossing persistence < 50%, never-crossing counted as
  persistence 0; interval = (previous grid point, that dt]).
- Spearman correlation (I1 vs HEART critical dt): computed from scratch
  (average ranks for ties; Pearson on ranks); interval represented by its
  upper grid endpoint, 'never' ranked above 600.
