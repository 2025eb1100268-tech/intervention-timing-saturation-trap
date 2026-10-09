"""Canonical wording for Paper 3's withdrawals and errata -- single source.

The paper's credibility rests on its audit trail, so the artefact tree and the
manuscript must not disagree by a word about what was withdrawn. This file is
the one place that wording lives. It emits:

  data/swebench_pilot/WITHDRAWALS_AND_ERRATA.md   (human-readable, quotable)
  data/swebench_pilot/withdrawals.json            (read by make_draft_datapack)

and then LINTS the rest of the artefact tree for drift: any artefact that
labels a withdrawn claim differently from its canonical label is reported, and
the script exits non-zero. Draft prose should quote `statement` verbatim.

Run from repo root:  python scripts/withdrawals.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "data" / "swebench_pilot"

LABEL = "DID NOT REPLICATE"

WITHDRAWALS = [
    {
        "id": "W1",
        "name": "Read-burst mechanism",
        "label": LABEL,
        "claim_withdrawn": (
            "Fable 5.1 issues bursts of file reads that drive a stateful "
            "monitor to its alarm clamp, making tool-use strategy the "
            "mechanism by which model choice moves a monitor's regime."),
        "statement": (
            "The Read-burst mechanism did not replicate. Under the clean "
            "protocol, sessions in both arms made 0–4 file reads (H17a, exact "
            "Wilcoxon p = 1.00), and read count did not predict peak modelled "
            "frustration once session length was controlled (partial "
            "ρ = 0.47, permutation p = 0.081, n = 16; p = 0.080 as originally "
            "scored, before the failed tool calls the logging hook never saw "
            "were restored). The pilot's evidence was a single session."),
        "preregistered_score": (
            "H17a INCONCLUSIVE; H17b FALSIFIED under its clause as written "
            "(\"falsified if the partial is not distinguishable from zero\")."),
        "why_label_differs": (
            "The H17b clause equated non-significance with falsification. A "
            "partial of 0.47 at p = 0.081 (0.080 as originally scored) with "
            "n = 16 is absence of evidence, "
            "not evidence of absence, so the accurate label is did-not-"
            "replicate. The pre-registered consequence -- withdrawal from the "
            "paper -- is the same under either label. Both are recorded; the "
            "pre-registered score is not rewritten."),
        "not_a_claim_that": (
            "file-reading bursts cannot charge an accumulator. They can; one "
            "did, once. We have no replicated instance and no evidence that "
            "either model does it systematically."),
        "pilot_evidence": "runE, Fable 5.1: 25 reads vs 4 for Opus 5; the only clamp in ten pilot runs; A6 fired 28 times vs 0.",
        "commits": {"pilot": "b5fa412", "preregistration": "616b09b", "result": "c64089e"},
    },
    {
        "id": "W2",
        "name": "Saturation trap at frontier cadence (the clamp)",
        "label": LABEL,
        "claim_withdrawn": (
            "Paper 1's saturation trap still closes at frontier-model cadence: "
            "a Fable 5.1 session drove the frozen monitor to the 1.0 clamp."),
        "statement": (
            "The frontier-cadence clamp did not replicate. Under the clean "
            "protocol no session in either arm reached the 1.0 clamp (0 of 8 "
            "and 0 of 8; maximum modelled frustration 0.679 and 0.486, or 0.679 "
            "and 0.398 as originally scored -- the logging hook never saw "
            "failed tool calls, so the replay was missing early errors in the "
            "Fable 5.1 arm). The pilot's evidence was a single session."),
        "preregistered_score": (
            "H18 SUPPORTED via its pre-stated zero-clamp branch, which the "
            "pre-registration defined as withdrawing the clamp claim."),
        "why_label_differs": (
            "H18 predicted clamps would be rare and was supported; what is "
            "withdrawn is the pilot's positive claim that the trap closes at "
            "frontier cadence, which has no replicated instance."),
        "not_a_claim_that": (
            "the trap cannot close. It closes on the legacy corpus at 1.53 s "
            "(Paper 2; Phase B). The clean-protocol sessions were short enough "
            "that the monitor was starved of evidence before it could "
            "saturate."),
        "pilot_evidence": "Opus 5 0/5 clamps, Fable 5.1 1/5 (runE).",
        "commits": {"pilot": "b5fa412", "preregistration": "616b09b", "result": "c64089e"},
    },
    {
        "id": "W3",
        "name": "Cadence difference between models",
        "label": LABEL,
        "claim_withdrawn": (
            "Fable 5.1 acts faster than Opus 5 (pooled median 1.20 s vs "
            "5.11 s, Mann–Whitney p = 2.1×10⁻⁵), moving the monitor between "
            "regimes (9/20 vs 17/20 trajectories in the alarm regime)."),
        "statement": (
            "The model difference in cadence did not replicate. The pilot's "
            "p = 2.1×10⁻⁵ treated time gaps within a session as independent; "
            "at the correct unit, the session, it was p = 0.125 at n = 5, "
            "where the smallest achievable p is 0.0625. The clean-protocol "
            "replication found 5 of 8 tasks in the predicted direction, exact "
            "Wilcoxon p = 0.38, median difference +0.80 s (as originally "
            "scored: 4 of 8, p = 0.84, −0.01 s, from a logging hook that never "
            "saw failed tool calls and so dropped the Fable 5.1 arm's opening "
            "actions). The corrected values lean toward the pilot's direction "
            "and remain indistinguishable from no difference at this n."),
        "preregistered_score": "H16 INCONCLUSIVE.",
        "why_label_differs": "Label and score agree: the prediction was neither supported nor contradicted.",
        "not_a_claim_that": "the two models run at the same cadence. We cannot distinguish them at this n.",
        "pilot_evidence": "Pooled over intervals: 65 vs 72 gaps, treated as independent.",
        "commits": {"pilot": "b5fa412", "correction": "616b09b", "result": "c64089e"},
    },
]

ERRATA = [
    {
        "id": "E0",
        "name": "Paper 1 — decay never executed in the replays (Δt = 0)",
        "paper": "Paper 1, arXiv 2606.04296",
        "published_text": [
            {"where": "§3 The Diagnostic Probe and the Three-Layer Architecture",
             "text": ("A continuous 18-dimensional affect vector, each dimension in "
                      "[0,1], with per-emotion exponential decay toward a baseline "
                      "of 0.10")},
        ],
        # Paper 2 v1, §3, published text, verbatim; [P1] renders its \cite{P1}.
        # lint_errata_notices.py checks this against paper2/sections/body.tex at 4ad51fd.
        "correction": (
            "Consequences: every [P1] firing rate and replay-consistency number is "
            "unaffected (they are deterministic functions of the Δt = 0 pipeline), "
            "but the mechanistic account—agents accumulate negative affect faster "
            "than it decays—was wrong. There was no race between accumulation and "
            "decay; there was only accumulation."),
        "correction_source": "Paper 2 (arXiv:2606.19386v1), §3 'The Δt = 0 Audit and Erratum', quoted verbatim",
        "what_stands": (
            "Every Paper 1 firing rate and replay-consistency number; only the "
            "mechanism changes."),
        "disposition": (
            "Published in Paper 2 v1 §3. Carried verbatim in Paper 1 v2 as item (a) "
            "of its erratum notice (branch paper1-arxiv-v2), in place of DT_AUDIT.md's "
            "internal one-line finding."),
        "sources": ["DT_AUDIT.md (code-path trace)", "paper2/sections/body.tex at 4ad51fd"],
    },
    {
        "id": "E1",
        "name": "Paper 1 — attribution of saturation to agent non-recovery",
        "paper": "Paper 1, arXiv 2606.04296",
        "published_text": [
            {"where": "§5 The State Saturation Trap",
             "text": ("A human developer crossing this threshold would typically "
                      "engage in a recovery action, such as stepping away, "
                      "reframing, or seeking help, allowing the state to decay. "
                      "The agents show no such recovery signal, so the state "
                      "remains saturated.")},
            {"where": "§8 Why the Detectors Fail: A Joint Reading",
             "text": ("This failure is independent of label subjectivity; it is "
                      "inherent to the trigger and the agent's lack of recovery, "
                      "and it reproduces across all five trajectories.")},
        ],
        # Every count is scoped to its corpus: Paper 1's five trajectories first,
        # then the twenty-trajectory corpus that contains them
        # (OBSERVER_CAPABILITY_AUDIT.md §8; LEXICAL_RECOVERY_PROXY.md).
        "correction": (
            "The observer used in Paper 1 has no channel through which a "
            "recovery signal could register. None of its eight rules emits a "
            "negative change: 0 of the 221 signals it emitted on Paper 1's five "
            "trajectories, and 0 of 765 across the twenty-trajectory corpus that "
            "contains them. The only emotion that opposes frustration, hope, is "
            "emitted by no rule, and the rule that detects reframing language "
            "adds confusion rather than removing frustration. The absence of a "
            "recovery signal was therefore guaranteed by the instrument and is "
            "not evidence about the agents. Recovery-shaped language does occur: "
            "by a frozen lexical proxy, on 21 of 218 steps in Paper 1's five "
            "trajectories and on 43 of 714 across the twenty. It has no path to "
            "the monitor's state."),
        "what_stands": (
            "The saturation itself and the inter-rater result. Only the "
            "attribution to the agents changes. This is the second correction "
            "to Paper 1; Paper 2 corrected its decay mechanism (Δt = 0)."),
        "verification": (
            "Both quotations were confirmed character-for-character by the "
            "author against the PDF of arXiv 2606.04296v1, the only version "
            "posted (checked 2026-10-05). The abstract's annotator sentence, "
            "retrieved verbatim from the arXiv API rather than through a "
            "summarising fetch, reads: 'three trained annotators using one "
            "rubric on a 56-action trajectory agree on where to intervene "
            "only slightly above chance'. Note 'one rubric', not 'the same "
            "rubric'. The PDF itself (LaTeX source, arXiv e-print retrieved "
            "2026-10-07) reads 'the same rubric' in its abstract, so the "
            "discrepancy is between the listing and the PDF; the v2 listing "
            "abstract is aligned to the PDF."),
        "still_open": (
            "(1) Prepared, not posted. Paper 2's published text says 'We "
            "issue an erratum in [P1]-v2'. Paper 1 v2 (branch paper1-arxiv-v2, "
            "78bd2b3 and later) carries both corrections in a notice before the "
            "abstract, each quoted verbatim -- Paper 2's published Delta-t = 0 "
            "consequence paragraph (E0) and this one -- and footnotes the "
            "abstract clause and the two quoted "
            "sentences; scripts/lint_errata_notices.py checks the quotations. "
            "Posting it makes Paper 2's sentence true. (2) Does not apply: "
            "Paper 1 does not describe the observer's hedge-word rule; its "
            "only mention of hedging is the A9 regex trigger's dictionary."),
        "sources": ["OBSERVER_CAPABILITY_AUDIT.md (47e177d; five-trajectory counts §8, b8e72b1)",
                    "LEXICAL_RECOVERY_PROXY.md (a451e66)"],
    },
    {
        "id": "E2",
        "name": "Paper 2 — repositioning",
        "paper": "Paper 2, arXiv 2606.19386",
        "items": [
            {
                "id": "E2a",
                "published_text": [
                    {"where": "Abstract", "text": "critical band of the same order of magnitude, Spearman ρ = 0.530 with the engine's"},
                    {"where": "§8 (body.tex l.337 of the posted source)", "text": "Per-trajectory critical Δts correlate between instruments at Spearman ρ = 0.530."},
                ],
                "correction": (
                    "This correlation carries no information beyond the two "
                    "instruments' shared dependence on error rate. It equals "
                    "the product of each instrument's correlation with error "
                    "rate to three decimals (0.899 × 0.593 = 0.533), and the "
                    "partial correlation controlling for error rate is −0.007 "
                    "(permutation p = 0.97). Paper 2's class-level conclusion "
                    "is unaffected: it rests on both instruments showing the "
                    "same two regimes on identical streams (20/20 in the alarm "
                    "regime at Δt = 0; none crossing threshold at "
                    "Δt ≥ 150 s), not on this correlation."),
                "disposition": (
                    "Corrected in Paper 2 itself: arXiv v2 quotes this "
                    "correction verbatim in its §3 erratum and footnotes both "
                    "passages (branch paper2-arxiv-v2, a5f291b). Also stated "
                    "in Paper 3."),
                "source": "PAPER3_DATAPACK.md §5.2 (77d2dab)",
            },
            {
                "id": "E2b",
                "published_text": [
                    {"where": "Abstract", "text": "Hook-instrumented real agent runs measure inter-action latency at median 1.53 s (p90 2.33 s)"},
                    {"where": "§5 Measured Real Cadence (body.tex l.215 of the posted source)", "text": "We therefore instrumented a real agent loop directly: a tool-call hook logs an ISO wall-clock timestamp, tool name, and result status for every action"},
                ],
                "correction": (
                    "The five runs were not logged by the Claude Code hook. "
                    "They were driven by a scriptable loop issuing one tool "
                    "call per turn to gpt-5.4-mini, which wrote the same "
                    "PostToolUse-schema record natively after each "
                    "observation. The hook, which produces the identical "
                    "format, was installed but was not the source of these "
                    "timestamps. Paper 2 does not name the model. No number "
                    "changes: the timestamp is taken at the same point in "
                    "each cycle, after the tool's observation."),
                "disposition": (
                    "Corrected in Paper 2 itself, not here: arXiv v2 of Paper 2 "
                    "adds a paragraph 'Erratum to this paper (v2)' to its §3, "
                    "alongside the Δt = 0 erratum, and corrects the abstract, "
                    "§1, §5, §9 and the Instrumentation appendix (branch "
                    "paper2-arxiv-v2, c20c244; this correction quoted verbatim "
                    "since a5f291b). Paper 3 cites the v2 erratum and does not "
                    "restate it in its related work."),
                "source": "data/live_runs/TIMING_REPORT.md; heart_instrument/agent_runner.py (MODEL = \"gpt-5.4-mini\", parallel_tool_calls=False)",
            },
            {
                "id": "E2c",
                "published_text": [
                    {"where": "Abstract", "text": "real autonomous coding cadence sits firmly inside the trap regime, vindicating [P1]'s empirical finding under a corrected mechanism"},
                ],
                "correction": (
                    "This holds for the harness, model and session lengths "
                    "measured, and Paper 2's own limitations section said so: "
                    "the cadence came from 'a small-model loop on small repos "
                    "(a lower bound for frontier loops—the deployments most "
                    "likely to enter the transition band are exactly the ones "
                    "not measured)'. The abstract claimed more than that "
                    "limitation allowed. A companion paper finds that a "
                    "production agent harness driving frontier models acts "
                    "more slowly than Paper 2's loop, in a comparison that also "
                    "changes model vendor and task set, and that on its shorter "
                    "sessions the monitor was starved of evidence rather than "
                    "trapped: no session reached the clamp. Whether the trap closes "
                    "depends on cadence and session length; it is not a "
                    "general property of autonomous coding."),
                "disposition": (
                    "Corrected in Paper 2 itself: arXiv v2 quotes this "
                    "correction verbatim in its §3 erratum and narrows the "
                    "abstract's phrase to 'the measured cadence' (branch "
                    "paper2-arxiv-v2). Self-contained: it carries no Paper 3 "
                    "figure. The cadences and the starvation result are "
                    "Paper 3's (§6.2)."),
                "source": "PHASE_C2_REPORT.md (c64089e); WARNING_SIGN_BRACKETING.md (00cd2bf)",
            },
        ],
        "what_stands": (
            "Paper 2's central result — wall-clock-calibrated leaky "
            "integrators have two regimes and a sample-time CUSUM is exactly "
            "invariant to Δt — and its dt = 0 erratum to Paper 1."),
    },
]

INTERNAL_CORRECTIONS = [
    ("Design rule validated by Spearman ρ = 0.899", "The ρ is identical to raw error rate's; the rule is supported by absolute containment (13/20, worst miss one bin).", "aa7bc54"),
    ("Pilot model contrast at p = 2.1×10⁻⁵", "Wrong unit of analysis; see W3.", "616b09b"),
    ("Operator's own record attributed to the agent", "Removed from every window; pooled Opus median 5.60 → 5.11 s; H12 FALSIFIED → PARTIAL.", "b5fa412"),
    ("Budget ceiling from the pilot (1-in-2.8 / 1-in-1.4)", "Replaced by the 9C ceiling.", "d819642"),
    ("\"The literature routinely contemplates 1-in-10\"", "Never sourced; withdrawn. Verified figures are audit budgets (1–2%).", "d819642"),
    ("design_report reported the cliff bound as max safe budget", "Overstated headroom ~5×; now reports min(cliff, starvation).", "d819642"),
    ("9C warning signs counted with the hook's error_indicator", "Inflated by file contents; execution-only is primary.", "00cd2bf"),
    ("Formula-vs-replay agreement (16/16) presented as validation", "An identity; relabelled as a regression check.", "00cd2bf"),
    ("Brown et al. is the sharpest starvation case (≥ m prior contexts)", "Brown et al. publish none of k, Θ, m, h; the published floors at stated lengths are Ctrl-Z (3, ≤ 15 steps) and Hills et al.'s k-strikes arm (3, 5 PRs).", "ceac2d2"),
    ("Evidence starvation applies to every published monitor", "Count-based rules only; the link-tracker is a max rule with N_min = 1.", "ceac2d2"),
    ("Evidence starvation presented without prior observation", "Hills et al. (App. J) report it for their k-strikes arm; the Ctrl-Z authors' post names the pressure. Paper 3 adds the budget closed form and the benign-session measurement.", "ceac2d2"),
    ("Phase B decomposition quoted at 29.5% (§4, transcribed from a hand-written reading doc)", "The generated BUDGET_CADENCE_REPORT.md Table 6 says 29; the decimal is not reproducible from budget_cadence_metrics.json. Now parsed from Table 6, so the removable split reads 30/70 not 29/71.", "95a19ed"),
    ("Phase 9C computed from a PostToolUse hook, treated as complete", "Claude Code fires PostToolUse only after a call succeeds; the 6 failed calls it never saw are restored from the subagent transcripts. Every label stands. Moved: W2 Fable peak 0.398 -> 0.486; W3 4/8, p 0.84, -0.01 s -> 5/8, p 0.38, +0.80 s; CUSUM full-budget coverage 38% -> 50%; E2c 5.1-5.6 -> 5.0-5.6 s (RECONCILIATION_9C.md).", "8aeb027"),
    ("\"Every label stands\" after the 9C regeneration", "Wrong: the bracketing direction claim flipped under the content-inflated definition (9C feasible 7/16 -> 10/16), and four hardcoded passages still asserted it held under every definition. Caught by an independent adversarial review. The reconciliation now checks qualitative labels per definition.", "0754de4"),
    ("CUSUM advantage held \"because every pair of failures fell within eight actions\"", "False under either count: S05 Opus has consecutive failures 11 clean actions apart. Accurate: in every firing session at least one consecutive pair fell within 8.", "8aeb027"),
    ("E1 quoted twenty-trajectory counts as Paper 1's ('in the same traces')", "Each count scoped to its corpus: 221 signals and 21 of 218 proxy steps on Paper 1's five trajectories; 765 and 43 of 714 across the twenty.", "b8e72b1"),
    ("\"The formula says the cliff is at 24.5 s\" (§5.1, hardcoded)", "δ* at p = 0.50 — a 9C run figure under the hook definition, quoted inside a legacy-corpus result. Legacy medians are 15.7 s contaminated, 7.4 s execution-only; now computed at generation time (CLIFF_RECOMPUTE.md).", "7fcc5f5"),
]

# Lint: patterns that would contradict the canonical labels.
LINT_FILES = ["PAPER3_CONCLUSIONS.md", "PAPER3_DATAPACK.md", "PHASE_C2_REPORT.md",
              "BUDGET_CEILING_9C.md", "WARNING_SIGN_BRACKETING.md",
              "EXTERNAL_MONITOR_CHECKS.md"]
LINT_RULES = [
    (re.compile(r"read.?burst[^\n]{0,120}\bfalsified\b(?![^\n]{0,200}did not replicate)", re.I),
     "Read-burst labelled FALSIFIED without the canonical 'did not replicate'"),
    (re.compile(r"\bH17b\b[^\n]{0,80}FALSIFIED(?![^\n]{0,240}did not replicate)", re.I),
     "H17b shown as FALSIFIED without the canonical label alongside"),
    (re.compile(r"\bnot a mechanism\b", re.I),
     "asserts read-bursting is NOT a mechanism -- absence of evidence stated as evidence of absence"),
    (re.compile(r"routinely contemplates(?![^\n]{0,160}(never sourced|withdrawn))", re.I),
     "unsourced '1-in-10' comparison without its withdrawal"),
    (re.compile(r"(Fable|heavier-reasoning)[^\n]{0,60}\b(is|are) the faster", re.I),
     "cadence difference asserted as a finding (see W3)"),
    (re.compile(r"(hook-instrumented|rather than the hook)(?![\s\S]{0,400}\bv2\b)", re.I),
     "Paper 2's hook misdescription restated without pointing to Paper 2 v2 (E2b)"),
    (re.compile(r"(?<!claim that )Brown et al\.? (is|as) the sharpest", re.I),
     "Brown et al. as the sharpest starvation case -- their parameters are unpublished (EXTERNAL_MONITOR_CHECKS.md)"),
    (re.compile(r"published ones?,?\s+which\s+are\s+all\s+built\s+this\s+way", re.I),
     "every published monitor claimed to have a count floor -- the link-tracker has N_min = 1"),
    (re.compile(r"(holds in direction under every definition|direction never changes)(?! that excludes)", re.I),
     "bracketing direction claimed for every definition -- after the logging correction it fails under the content-inflated one; scope it"),
    (re.compile(r"every pair of (execution )?failures", re.I),
     "CUSUM condition misstated -- one firing session has consecutive failures 11 apart; say 'at least one consecutive pair'"),
    (re.compile(r"(cliff is at 24\.5|critical interval[^\n]{0,40}\*\*24\.5)", re.I),
     "24.5 s cliff quoted without naming the rate it is delta* of (p = 0.50, 9C hook definition)",
     lambda text, m: re.search(r"p\s*[=≈]\s*0\.50?\b",
                               text[max(0, m.start() - 300):m.end() + 300]) is not None),
]


# ---- numeric drift: the CUSUM-vs-accumulator fire rates ----
# These appear as "a% → b% → c%" in several artefacts and nothing regenerates
# them together. Rather than pin one blessed triple, we recompute every triple
# the committed data can justify (either series, any ordered choice of three
# budgets) and reject prose triples that are not among them. A stale figure
# survives only if it happens to match some other legitimate combination, so
# this narrows drift rather than eliminating it.
ARROW_TRIPLE = re.compile(r"(\d+)% → (\d+)% → (\d+)%")
NUMERIC_LINT_FILES = ["data/swebench_pilot/PAPER3_CONCLUSIONS.md",
                      "data/swebench_pilot/PAPER3_DATAPACK.md",
                      "data/swebench_pilot/BUDGET_CEILING_9C.md",
                      "data/swebench_pilot/WARNING_SIGN_BRACKETING.md",
                      "data/swebench_pilot/EXTERNAL_MONITOR_CHECKS.md",
                      "monitor_invariance/README.md"]


def valid_fire_triples():
    sys.path.insert(0, str(ROOT / "scripts"))
    from c2_source import C2
    p = C2 / "_budget_ceiling.json"
    if not p.exists():
        return None
    direct = json.loads(p.read_text(encoding="utf-8"))["direct"]
    out = set()
    for series in ("i2", "nd", "wc"):
        pts = {int(r): v[series] for r, v in direct.items() if v.get(series) is not None}
        for a in pts:
            for b in pts:
                for c in pts:
                    out.add((round(pts[a] * 100), round(pts[b] * 100), round(pts[c] * 100)))
    return out


def numeric_drift():
    valid = valid_fire_triples()
    if valid is None:
        return []
    bad = []
    for rel in NUMERIC_LINT_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for m in ARROW_TRIPLE.finditer(text):
            trip = tuple(int(g) for g in m.groups())
            if trip not in valid:
                line = text.count("\n", 0, m.start()) + 1
                bad.append((rel, line,
                            "fire-rate triple matches no budget combination in "
                            "_budget_ceiling.json (numeric drift)", m.group(0)))
    return bad


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def main() -> int:
    O = []
    w = O.append
    w("# Withdrawals and errata — canonical wording")
    w("")
    w(f"Generated by `scripts/withdrawals.py` at `{sha()}`. **This is the single "
      "source for how Paper 3 describes what it withdrew and what it corrects in "
      "Papers 1 and 2. Manuscript prose must quote each `statement` and "
      "`correction` verbatim.** The script lints the artefact tree for drift "
      "from these labels and fails if it finds any.")
    w("")
    w(f"All three withdrawals carry the same label: **{LABEL}.** None is "
      f"labelled *falsified* in prose: in each case the clean replication "
      f"failed to reproduce the pilot, which is absence of evidence. Where a "
      f"pre-registered clause scored one as falsified, that score is recorded "
      f"unchanged beside the label.")
    w("")
    w("## Withdrawals")
    w("")
    for x in WITHDRAWALS:
        w(f"### {x['id']} — {x['name']}: **{x['label']}**")
        w("")
        w(f"**Claim withdrawn.** {x['claim_withdrawn']}")
        w("")
        w(f"> **Canonical statement.** {x['statement']}")
        w("")
        w(f"- **Pre-registered score (unchanged):** {x['preregistered_score']}")
        w(f"- **Why the label is what it is:** {x['why_label_differs']}")
        w(f"- **This is not a claim that** {x['not_a_claim_that']}")
        w(f"- **Pilot evidence:** {x['pilot_evidence']}")
        w(f"- **Commits:** " + ", ".join(f"{k} `{v}`" for k, v in x["commits"].items()))
        w("")
    w("## Errata to earlier papers")
    w("")
    for e in ERRATA:
        w(f"### {e['id']} — {e['name']}")
        w("")
        if "items" in e:
            for it in e["items"]:
                w(f"**{it['id']}. {e['paper']} — published text:**")
                w("")
                for q in it["published_text"]:
                    w(f"> {q['text']}  \n> — *{q['where']}*")
                    w("")
                w(f"> **Canonical correction.** {it['correction']}")
                w("")
                w(f"- **Where it is corrected:** {it['disposition']}")
                w(f"- **Source:** {it['source']}")
                w("")
            w(f"**What stands in Paper 2:** {e['what_stands']}")
            w("")
            continue
        w(f"**{e['paper']} — published text:**")
        w("")
        for q in e["published_text"]:
            w(f"> {q['text']}  \n> — *{q['where']}*")
            w("")
        w(f"> **Canonical correction.** {e['correction']}")
        w("")
        if e.get("correction_source"):
            w(f"- **The correction's own source:** {e['correction_source']}")
        w(f"- **What stands:** {e['what_stands']}")
        if e.get("disposition"):
            w(f"- **Where it is corrected:** {e['disposition']}")
        if e.get("verification"):
            w(f"- ✓ **Verified:** {e['verification']}")
        if e.get("still_open"):
            w(f"- **Open items, status:** {e['still_open']}")
        w(f"- **Sources:** " + "; ".join(e["sources"]))
        w("")
    w("## Corrections made during this study")
    w("")
    w("Recorded in place in the artefacts named; listed here so the audit-trail "
      "section can cite one location.")
    w("")
    w("| what was said | what replaced it | commit |")
    w("|---|---|---|")
    for a, b, c in INTERNAL_CORRECTIONS:
        w(f"| {a} | {b} | `{c}` |")
    w("")

    # ---- lint ----
    problems = []
    for fname in LINT_FILES:
        p = PILOT / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for rule in LINT_RULES:
            rx, why = rule[0], rule[1]
            # Optional third element: exempt(text, match) -> True means the
            # surrounding context already says what the rule demands. Needed
            # where the qualifier may appear BEFORE the match, which a regex
            # lookahead cannot see and Python cannot express as a lookbehind.
            exempt = rule[2] if len(rule) > 2 else None
            for m in rx.finditer(text):
                if exempt and exempt(text, m):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                problems.append((fname, line, why, m.group(0)[:90]))
    problems.extend(numeric_drift())
    w("## Lint")
    w("")
    if problems:
        w(f"**{len(problems)} drift(s) from the canonical wording:**")
        w("")
        for f, l, why, snip in problems:
            w(f"- `{f}:{l}` — {why}: “{snip}”")
    else:
        w(f"**Clean.** No artefact in {', '.join(f'`{f}`' for f in LINT_FILES)} "
          f"contradicts the canonical labels.")
    w("")

    (PILOT / "WITHDRAWALS_AND_ERRATA.md").write_text("\n".join(O), encoding="utf-8")
    (PILOT / "withdrawals.json").write_text(json.dumps(
        {"label": LABEL, "withdrawals": WITHDRAWALS, "errata": ERRATA}, indent=1,
        ensure_ascii=False), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if problems:
        for f, l, why, snip in problems:
            print(f"DRIFT {f}:{l}  {why}\n      {snip}")
        return 1
    print("lint clean; wrote WITHDRAWALS_AND_ERRATA.md and withdrawals.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
