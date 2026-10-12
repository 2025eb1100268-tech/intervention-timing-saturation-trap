# Paper 3 — data and generators

Release for *Clocks, Counts, and Evidence Floors in Stateful Runtime
Monitoring of AI Agents* (Modgil, 2026). The four checks the paper contributes
are a separate, standalone package:
[monitor_invariance](https://github.com/2025eb1100268-tech/monitor_invariance)
(v0.1.0).

The layout mirrors the working repository, so every path a script or report
names resolves here: reports and pre-registrations in `data/swebench_pilot/`,
session data in `data/live_runs/`, generators in `scripts/`. `MANIFEST.md`
lists every file with its sha256.

## Where each part of the paper comes from

| paper | files |
|---|---|
| §2.1 Proposition 1, verified on 19,360 and 29,520 cells | `BUDGET_CADENCE_REPORT.md`, `WINDOW_IDENTITY.md` |
| §2.3 recalibration (29% → 50%) | `BUDGET_CADENCE_REPORT.md` (Table 6) |
| §2.4 window reduction | `WINDOW_IDENTITY.md` |
| §3.3 Hills et al. and Ctrl-Z floors; §4.2, §4.5, §4.6 | `EXTERNAL_MONITOR_CHECKS.md`, `external_monitors/extraction.json`, `_checks.json` |
| §3.4 the floor on both corpora; Appendix A | `WARNING_SIGN_BRACKETING.md`, `data/live_runs/phase_c2_canonical/_bracketing.json` |
| §3.4 the logging hook, restored calls | `HOOK_COVERAGE_AUDIT.md`, `TRANSCRIPT_TIMESTAMP_CHECK.md`, `RECONCILIATION_9C.md` |
| §3.4 hold-out (Opus 5.5) | `PHASE_9D_REPORT.md` |
| §3.6, §5.2 CUSUM vs accumulator | `BUDGET_CEILING_9C.md` |
| §4, Table 2, Appendix B — the fourteen control monitors | `CONTROL_MONITOR_CENSUS.md`, `external_monitors/census_fanout.json`, `table2.json` |
| §4.2–4.4, Appendix D — deployed systems, the probing rule | `DEPLOYED_MONITOR_CENSUS.md`, `DEPLOYED_SPLIT.md`, `external_monitors/deployed_hunt.json`, `deployed_split.json` |
| §6.1 the observer audit; recovery proxy | `OBSERVER_CAPABILITY_AUDIT.md` (§8: Paper 1's five trajectories), `LEXICAL_RECOVERY_PROXY.md` |
| §6, Appendix F — withdrawals and errata | `WITHDRAWALS_AND_ERRATA.md`, `withdrawals.json` |
| §7 pilot and replication | `PHASE_C_SUB_COMPARISON.md`, `PHASE_C_SUB_REPORT_*.md`, `PHASE_C2_REPORT.md` |
| Appendix E — pre-registered hypotheses | `HYPOTHESIS_SCORECARD.md`, the four `PREREGISTRATION_PHASE9*.md` |
| figures quoted as originally scored | `data/swebench_pilot/as_originally_scored/` |

## Session data

- `data/live_runs/phase_c_sub/` — the pilot: ten sessions, five task specifications.
- `data/live_runs/phase_c2/` — the clean-protocol replication (sixteen sessions,
  eight specifications) and the Opus 5.5 hold-out, **as logged by the hook**: the
  basis of every "as originally scored" figure.
- `data/live_runs/phase_c2_canonical/` — the same sessions **rebuilt from the
  session transcripts**, with the failed tool calls the hook never saw restored
  (`source` field on each record). Every corrected figure in the paper comes from
  here.
- `data/live_runs/REPO_PROVENANCE.md` — the upstream repositories and commits the
  tasks were planted in.

## What is not here, and why

- **The HEART engine.** As for Paper 2, the scripts are published to document the
  exact method; those that replay the engine cannot run without it. Their outputs
  are included.
- **Raw SWE-bench-Verified trajectories.** They belong to their sources and are not
  redistributed; the per-session counts the paper uses are in `_bracketing.json`.
- **Raw session transcripts.** They are the full working conversations, including
  material unrelated to the study; the records derived from them, which carry
  every tool call and timestamp the analysis uses, are included.
- **Internal working notes and drafts.** The generated reports supersede them, and
  some notes carry figures that were later corrected.

Local paths are scrubbed (`<repo>`, `<home>`, `<project>`, `<user>`); nothing
else is altered. Released under the repository's MIT license.
