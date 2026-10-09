# Observer capability audit (Phase A0)

Tree commit: `b8e72b1452ee`. Read-only audit of frozen code and frozen artefacts; **not a Phase-9 result**. Reproduces `PREREGISTRATION_PHASE9.md` §0.

## 1. Sign audit — can the observer push anything DOWN?

- actions: **714** across 20 trajectories
- emitted signals: **765**
- **negative deltas: 0**

Zero. Confirmed by static inspection of all eight rules in `heart_adapters/claude_code/signals.py`: every `return` is a list of non-negative `(emotion, delta)` pairs. **The observer is a monotone non-negative evidence source.**

## 5. Channel census — what does the observer actually emit?

| emotion | firings | summed delta | opposes `frustration` in CONFLICTS? |
|---|---|---|---|
| frustration | 359 | 27.80 | no |
| fear | 202 | 10.10 | no |
| confusion | 166 | 22.41 | no |
| happiness | 22 | 1.64 | no |
| pride | 14 | 2.10 | no |
| curiosity | 2 | 0.10 | no |

Negative-valence escalation accounts for **727/765 (95.0%)** of all emitted signals. `frustration`'s only opponent in `CONFLICTS` is **['hope']**; no positive-valence channel the observer emits appears in that set.

## 2. Antagonist audit — is the de-escalation path reachable?

- rules whose source mentions `hope`: **none**
- measured `max(hope)` across every action of every trajectory: **0.1000** (BASELINE = 0.1)

`hope` is never emitted and never rises above baseline. The `("hope","frustration"): -0.50` conflict term — the engine's only route from an observation to a *decrease* in frustration — is **unreachable given this rule set**.

## 3. Dead-path audit — the three indirect attenuation routes

| path | condition to fire | measured | reachable? |
|---|---|---|---|
| `_rebalance_conflicts_v2` | both members of a conflicting pair > 0.55 | `max(hope)` = 0.1000 | **no** (hope never clears 0.55) |
| `_normalize_energy` | `sum(state)` > 6.0 | max observed `sum(state)` = **4.827** | **no** |
| `_apply_core_layer` | non-empty plugin registry | `load_emotion_cores()` returns `{}` | **no** (no-op) |

## 4. Monotonicity — the empirical consequence

- within-trajectory action steps examined at dt=0: **694**
- steps on which `frustration` **decreased**: **0**

Frustration is **strictly non-decreasing** under the observer. The only mechanism in the whole monitor that lowers it is the wall-clock decay term in `EmotionEngine._tick_decay`. This is a property of the *instrument*, not of the agents observed — it would hold identically against a perfectly self-correcting agent.

### No-signal (silent) fraction per trajectory

min **25.4%**, median **51.6%**, max **78.6%** — reproduces the 25–79% / median 52% figure reported in Paper 1.

## 6. Metacognition detection — the sign-inverted channel

| marker | consumed by a rule? | actions | rate |
|---|---|---|---|
| `ActionEvent.has_hedge_words()` | **yes** (`rule_hedge_words`) | 2 | 0.3% |
| `text_features._CYCLE_RE` | no | 43 | 6.0% |
| `text_features._RECOGNITION_RE` | no | 8 | 1.1% |
| backing-out bash command | no | 0 | 0.0% |
| **any of the above** | — | 49 | 6.9% |

Actions with empty reasoning text: 0 (0.0%).

`rule_hedge_words` branches on `len(task_metadata['files_in_scope']) >= 3`. The aime-coder parser populates `task_metadata` with only `task_description` and `source_format`, so `files_in_scope` is always `[]`, the complex-task branch is dead code on this corpus, and the rule always returns exactly `[("confusion", 0.08)]`.

**Therefore: detecting explicit metacognition raises the negative-accumulation sum.** The observer's only reframing detector is sign-inverted with respect to recovery, and fires on 2/714 actions.

## 7. Drain arithmetic

HEART, decaying toward BASELINE=0.1 with half-life 150 s: falling from the clamp 1.0 below 0.7 needs `0.1 + 0.9*exp(-ln2/150*T) < 0.7`, i.e. **T > 87.74 s** of signal-free elapsed time.

I1 (no baseline term): **T > 77.19 s**.

| cadence (s) | consecutive signal-free actions needed (HEART) | (I1) |
|---|---|---|
| 1.53 | 57.3 | 50.4 |
| 2.33 | 37.7 | 33.1 |
| 5.0 | 17.5 | 15.4 |
| 15.0 | 5.8 | 5.1 |

Longest observed run of consecutive actions carrying **no frustration signal**: min 2, median 4.5, max 10.
Trajectories whose longest silent run reaches the 57.3 actions needed at 1.53 s: **0/20**. Trajectories even 57 actions long in total: **1/20**.

## Verdict

**The observer cannot express recovery.** Every evidence channel is non-negative; the single de-escalating term in the engine is unreachable from the rule set; all three indirect attenuation paths are dead; and frustration is empirically strictly non-decreasing over 694 action steps. Recovery sensitivity on the channel that drives every trigger is **exactly zero by construction**, and no amount of hand labelling can change that constant.

This generalises past HEART, and is the second structural result Paper 3 carries alongside wall-clock-vs-sample-time calibration: **a monitor whose evidence channel is sign-constrained — all evidence incriminating, none exculpatory — cannot de-escalate, regardless of which integrator sits behind it.** The only remaining route from agent recovery to monitor state is *silence*, which is what Phase A-iii measures.

## 8. Paper 1's five trajectories

Paper 1 replayed five of these twenty trajectories. Every count above, restricted to those five, so a correction to Paper 1 can scope each number to the corpus it describes.

| count | Paper 1's five | all twenty |
|---|---|---|
| actions | 218 | 714 |
| signals | 221 | 765 |
| negative deltas | 0 | 0 |
| frustration steps | 213 | 694 |
| frustration decreases | 0 | 0 |
| reframing rule firings | 2 | 2 |
| cycle markers | 21 | 43 |
