# Phase 9C — clean-protocol replication: Opus 5 vs Fable 5.1

Tree commit `653d346496bc`. Pre-registered: `PREREGISTRATION_PHASE9C.md` + Amendment 1, both committed before the first run. **n = 8 distinct specs**, 1 run per arm per spec, 16 runs. The pilot (`phase_c_sub/`) is **not pooled** with anything here.

Unit of analysis is the **spec**. Clean-git protocol: bug committed into a single orphan root commit with all other refs deleted, six assertions logged per run.

**Data source: hook (as originally scored).** This is the published scoring, which could not see failed tool calls. The canonical, transcript-derived version is the default.

## 0. Protocol integrity

- clean-git assertions: **6/6 PASS on all 16 runs**
- target tests green: **16/16** runs
- git recon attempts (found nothing by construction): Opus [0, 0, 0, 0, 0, 2, 1, 0], Fable [0, 0, 0, 0, 0, 1, 2, 0]

## 1. Per-spec results

| spec | module | actions O / F | median dt O / F | Read O / F | peak frust O / F | clamp O / F |
|---|---|---|---|---|---|---|
| S02 | `sortedcontainers` | 7 / 6 | 5.461 / 1.675 | 1 / 1 | 0.342 / 0.299 | n / n |
| S03 | `sortedcontainers` | 10 / 7 | 6.36 / 5.419 | 1 / 2 | 0.150 / 0.398 | n / n |
| S05 | `toolz` | 14 / 5 | 5.234 / 4.798 | 4 / 1 | 0.515 / 0.299 | n / n |
| S06 | `toolz` | 6 / 5 | 4.002 / 4.924 | 0 / 1 | 0.241 / 0.150 | n / n |
| S07 | `toolz` | 9 / 8 | 3.982 / 4.439 | 3 / 2 | 0.608 / 0.392 | n / n |
| S08 | `toolz` | 12 / 6 | 5.58 / 7.028 | 1 / 2 | 0.274 / 0.300 | n / n |
| S09 | `more-itertools` | 20 / 17 | 5.205 / 7.322 | 3 / 3 | 0.679 / 0.191 | n / n |
| S10 | `more-itertools` | 5 / 4 | 8.683 / 5.224 | 0 / 0 | 0.347 / 0.347 | n / n |

## 2. H16 — cadence direction

Pre-registered: Fable's median dt **below** Opus's; Wilcoxon signed-rank on per-spec median dt (Opus − Fable), two-sided, exact, α = 0.05.

| spec | Opus | Fable | Opus − Fable |
|---|---|---|---|
| S02 | 5.461 | 1.675 | **+3.786** |
| S03 | 6.36 | 5.419 | **+0.941** |
| S05 | 5.234 | 4.798 | **+0.436** |
| S06 | 4.002 | 4.924 | **-0.922** |
| S07 | 3.982 | 4.439 | **-0.457** |
| S08 | 5.58 | 7.028 | **-1.448** |
| S09 | 5.205 | 7.322 | **-2.117** |
| S10 | 8.683 | 5.224 | **+3.459** |

Specs favouring Fable faster: **4/8**. W⁺ = 20, W⁻ = 16, **exact two-sided p = 0.8438** (floor at n = 8 is 7.81e-03), median difference -0.010 s.

**H16: INCONCLUSIVE** — reported as inconclusive, not as a null and not as support. Per Amendment 1 §A1.2 the committed next step is to add the second repeat to all 8 specs and re-score on 2-repeat means, not to reinterpret these runs.

## 3. H17a — Read-burst, per-spec counts

| spec | Opus Read | Fable Read | Fable − Opus |
|---|---|---|---|
| S02 | 1 | 1 | **+0** |
| S03 | 1 | 2 | **+1** |
| S05 | 4 | 1 | **-3** |
| S06 | 0 | 1 | **+1** |
| S07 | 3 | 2 | **-1** |
| S08 | 1 | 2 | **+1** |
| S09 | 3 | 3 | **+0** |
| S10 | 0 | 0 | **+0** |

W⁺ = 8, W⁻ = 8, **exact two-sided p = 1.0000** (n = 5 after dropping 3 tied pair(s); floor 6.25e-02), median difference +1.0 Reads.

**H17a: INCONCLUSIVE**

## 4. H17b — does Read count *predict* peak frustration?

Pre-registered discipline: the **raw** correlation is NOT the test, because more Reads means more actions means more accumulation. The test is the **partial controlling for action count**.

**NOT a test:**

| | Spearman |
|---|---|
| raw: Read count vs peak frustration | 0.464 |
| Read count vs action count (collinearity check) | 0.740 |
| peak frustration vs action count | 0.209 |

**THE TEST:**

| | value |
|---|---|
| **partial ρ(Read, peak frust \| action count)** | **0.4701** |
| permutation p (20,000 shuffles, seed 20260908) | **0.0795** |
| n (runs, both arms) | 16 |

**H17b: FALSIFIED under its pre-registered clause — canonical label: did not replicate (W1).** The partial is not distinguishable from zero at n = 16. The clause equated non-significance with falsification; this is absence of evidence for a read-burst mechanism, not evidence that reading plays no role. Per the pre-registration the mechanism claim is **withdrawn from the paper** either way.

## 5. H18 — clamp rate

| arm | reached 0.7 | reached clamp | clamp rate | max frustration observed |
|---|---|---|---|---|
| opus | 0/8 | 0/8 | 0% | 0.679 |
| fable | 0/8 | 0/8 | 0% | 0.398 |

**H18: SUPPORTED**, and via the pre-stated **third outcome**: **zero runs clamped in either arm**. Therefore the pilot's single runE clamp is **unreplicated**, and the clamp-specific mechanism claim is **withdrawn**. The cadence and regime-placement results do not depend on it and stand.

## 6. Action counts under the clean protocol (descriptive)

Pre-registered direction: **increase** relative to the pilot, since the `git diff` shortcut to localisation is gone.

| arm | 9C per-spec actions | 9C median | pilot median | direction |
|---|---|---|---|---|
| opus | [7, 10, 14, 6, 9, 12, 20, 5] | **9.5** | 14.0 | decrease |
| fable | [6, 7, 5, 5, 8, 6, 17, 4] | **6.0** | 7.0 | decrease |

**The pre-registered direction was wrong, and the comparison is worse confounded than the pre-registration admitted.** I registered this as confounded with the protocol change; it is *also* confounded with the **spec set**, because 9C uses eight different specs from the pilot's five. The pilot included `runE` = the entire more-itertools suite (32-35 actions); every 9C spec targets a single test file. So a decrease was likely from the task set alone, independently of the git protocol, and this comparison cannot separate the two. It is reported as a failed prediction and as uninformative about the protocol — not reinterpreted.

The consequence matters downstream: shorter runs mean fewer accumulating observations, which is why peak frustration is lower here than in the pilot (max 0.679 / 0.398 against 0.807 / 1.000) and why nothing clamped. That is Phase B's evidence-starvation mechanism operating on the trace length, and it is the one thing in this arm consistent with the pilot.

## 7. H11 conditional revival check

Runs reaching n ≥ 30 dt intervals: **0/16**. Revival required ≥ 8. **Not revived** — H11 remains retired.

## 8. Pooled cadence (descriptive, cross-harness)

| | Opus 5 | Fable 5.1 | Paper 2 (scriptable loop) |
|---|---|---|---|
| n dt | 75 | 50 | 65 |
| median | **5.58** | **5.12** | 1.53 |
| p90 | 15.90 | 17.89 | 2.33 |
| max | 108.57 | 49.93 | 15.87 |

Both arms sit several times Paper 2's cadence and inside the (1, 30] s critical band. **That is a harness-level observation, not a model one** — H16 shows the two models are indistinguishable here — and it is cross-harness against Paper 2, so it supports no confirmatory claim. It is reported for what it is: a real agent harness runs an order of magnitude slower than a scriptable one-tool-call loop, which is exactly the kind of infrastructure fact the paper argues determines a wall-clock monitor's regime.

## 9. What this does to the paper

**Withdrawn.** The Phase-C model-contrast claims do not survive a clean protocol with the correct unit of analysis:

- the cadence *direction* (Fable faster) does not replicate — 4/8 specs, p = 0.84, median difference -0.01 s. The pilot's 4/5 was noise at n = 5 with a floor of 0.0625.
- the **Read-burst mechanism is withdrawn** — H17a inconclusive (p = 1.00; Read counts are 0–4 in *both* arms, never the pilot's 25) and H17b's partial not distinguishable from zero.
- the **clamp is withdrawn** — 0/16 runs clamped. The pilot's single runE clamp (28 A6 fires) is unreplicated and was one run.

**Unaffected.** Everything computed on frozen streams with exact arithmetic, which is where the paper's weight was already placed: Phase B's budget×cadence identity (0 mismatches / 19,360 cells) and the evidence-starvation floor; Phase A0's sign-constraint proof; Phase E's design rule (13/20 containment) and the shipped tests; and the monitor-class census.

**Net reading.** Paper 3's claims should rest on the frozen-data results and the deliverable, not on live-agent model comparisons. This arm is the honest demonstration of why: an n = 5 pilot with the wrong unit and a protocol leak produced three findings, and all three evaporated when the unit, the protocol and the spec count were fixed.

## 10. Scorecard

| hypothesis | result |
|---|---|
| H16 cadence direction | **INCONCLUSIVE** (p = 0.8438, 4/8 specs) |
| H17a Read-burst counts | **INCONCLUSIVE** (p = 1.0000) |
| H17b Read → frustration mechanism | **FALSIFIED** under its clause · canonical: **did not replicate** (W1) (partial 0.470, p = 0.0795) |
| H18 clamp rate | **SUPPORTED (zero-clamp branch)** |
| H11 revival | not revived (0/16 runs at n ≥ 30) |
