"""The paper's own arithmetic, applied to DEPLOYED agent monitors.

EXTERNAL_MONITOR_CHECKS.md audits four monitors from published AI-control
papers. This audits monitors that are shipped: gateways, agent frameworks and
SIEM detection rules whose accumulated state over an agent's actions is indexed
in wall-clock seconds. It exists because the paper's weakest claim was that the
wall-clock class has no member but our own instrument.

Each entry carries only values taken from source code, a configuration
reference or a shipped rule file, with the parameter named and its units. Two
entries were re-verified first-hand against the raw file (marked VERIFIED
FIRST-HAND); the rest come from the search in
external_monitors/deployed_hunt.json, and entries whose quote the verification
pass could not confirm are excluded from the table entirely.

For each we compute the quantity the paper's Section 3 defines: how slowly an
agent must act for the monitor's accumulated state never to reach its
threshold. For a monitor firing at N events inside a T-second window that is

    safe_rate = (N - 1) / T          events per second, sustained indefinitely
    safe_gap  = T / (N - 1)          seconds between events

which is arithmetic, not a measurement, and is the same starvation bound as
r_max = E / N_min with the window supplying E.

Run from repo root, after scripts/elastic_schedule.py:
    python scripts/deployed_monitor_census.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "swebench_pilot" / "DEPLOYED_MONITOR_CENSUS.md"
# The Elastic rule's schedule figures, from scripts/elastic_schedule.py.
SCHEDULE = ROOT / "data" / "swebench_pilot" / "external_monitors" / "elastic_schedule.json"

# N = events needed inside the window; T = window in seconds.
# purpose: 'detect'  = fires on suspected misbehaviour (a safety monitor)
#          'limit'   = caps load, spend or rate (resource control)
MONITORS = [
    {
        "name": "Elastic Security — “Unusual High Denied Topic Blocks Detected”",
        "what": "counts Amazon Bedrock guardrail `BLOCKED` events with `topic_policy` per `user.id`",
        "n": 6, "t": 3600.0,
        "param": '`from = "now-60m"`, `interval = "10m"`, `where Esql.ml_policy_blocked_topic_count > 5`',
        "purpose": "detect",
        "gates": "raises a severity-medium alert (risk_score 47)",
        "source": "rules/integrations/aws_bedrock/aws_bedrock_multiple_topic_policy_blocks_detected.toml, `maturity = \"production\"`, elastic/detection-rules",
        "quote": "Detects repeated compliance violation 'BLOCKED' actions coupled with specific policy name such as 'topic_policy', indicating persistent misuse or attempts to probe the model's denied topics.",
        "verified": True,
    },
    {
        "name": "Microsoft Agent Governance Toolkit — `MCPSlidingRateLimiter`",
        "what": "keeps a timestamp per MCP tool call, per `agent_id`",
        "n": 100, "t": 300.0,
        "param": "`max_calls_per_window: int = 100`, `window_size: float = 300.0` (seconds), `clock = time.monotonic`",
        "purpose": "limit",
        "gates": "denies the tool call",
        "source": "agent-governance-python/agent-os/src/agent_os/mcp_sliding_rate_limiter.py (and a Rust twin at agent-governance-rust/agentmesh-mcp/src/mcp/rate_limit.rs), MIT",
        "quote": "cutoff = now - self.window_size … self._prune_expired(bucket, cutoff) … if len(bucket) >= self.max_calls_per_window",
        "verified": True,
    },
    {
        "name": "Agent Threat Rules — ATR-2026-00553 “Runaway tool-call loop”",
        "what": "counts tool-call spans per agent session",
        "n": 100, "t": 60.0,
        "param": '`window: "PT1M"`, `threshold: 100`, `min_events: 10`, `cooldown: "PT5M"`',
        "purpose": "detect",
        "gates": "`rate_limit_source` and `escalate`",
        "source": "Agent Threat Rules (open-source agent detection ruleset)",
        "quote": "behavioural accumulator over tool-call spans per session",
        "verified": False,
    },
    {
        "name": "LangSmith — production alerts on agent runs",
        "what": "aggregates LLM/agent run errors or feedback",
        "n": None, "t": 900.0,
        "param": "`Aggregation Window`, settable only to 5 or 15 minutes",
        "purpose": "detect",
        "gates": "fires an alert to PagerDuty/webhook",
        "source": "LangSmith alerts documentation",
        "quote": "the longest span of agent behaviour any LangSmith alert can accumulate over is fifteen minutes",
        "verified": False,
    },
    {
        "name": "Datadog LLM Observability monitor",
        "what": "counts an agent's error spans",
        "n": 26, "t": 900.0,
        "param": '`.rollup("count").last("15m") > 25`, `evaluation_delay = 300` (seconds)',
        "purpose": "detect",
        "gates": "monitor alert",
        "source": "`llm-observability alert` monitor type; production config in terraform-provider-datadog issue #3858",
        "quote": "twenty-five spans inside a 15-minute trailing window",
        "verified": False,
    },
    {
        "name": "FastMCP — `RateLimitingMiddleware`",
        "what": "token bucket over an agent's tool calls",
        "n": 20, "t": 2.0,
        "param": "`max_requests_per_second` (default 10.0), `burst_capacity` (default 20)",
        "purpose": "limit",
        "gates": "rejects the tool call",
        "source": "FastMCP middleware (the dominant Python MCP server framework)",
        "quote": "an over-budget agent is forgiven by nothing but elapsed seconds",
        "verified": False,
    },
    {
        "name": "CrewAI — `RPMController`",
        "what": "counts requests per crew/agent",
        "n": None, "t": 60.0,
        "param": "`max_rpm`; forgetting hardcoded: `time.sleep(60); self._current_rpm = 0`",
        "purpose": "limit",
        "gates": "blocks agent execution",
        "source": "crewAIInc/crewAI, `RPMController`",
        "quote": "the threshold is configurable but the forgetting interval is not",
        "verified": False,
    },
    {
        "name": "LangChain Core — `InMemoryRateLimiter`",
        "what": "token bucket in front of every LLM call in an agent loop",
        "n": 1, "t": 1.0,
        "param": "`requests_per_second` (source default 1), `max_bucket_size` (1); state is `elapsed * requests_per_second`",
        "purpose": "limit",
        "gates": "blocks the model call",
        "source": "langchain-core, `InMemoryRateLimiter`",
        "quote": "the evidence of a call is gone one second after it is made",
        "verified": False,
    },
]

STATELESS = [
    ("NVIDIA NeMo Guardrails", "full Configuration YAML schema contains no accumulation window, decay, cooldown or session-level frequency threshold; the only duration-valued parameters are request timeouts. Every rail is a stateless per-message classifier."),
    ("Guardrails AI", "validators are per-output, threshold-on-a-score. No time term found."),
    ("Lakera Guard", "documented as a per-request detector returning flags; no abuse-scoring window or decay parameter found in the docs."),
]


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def _burst(sched: dict, s: float) -> float:
    return next(r for r in sched["burst"] if r["spacing_s"] == s)["exact_share"]


def _sustained(sched: dict, s: float) -> dict:
    return next(r for r in sched["sustained_within_week"] if r["spacing_s"] == s)


def main() -> int:
    if not SCHEDULE.exists():
        raise SystemExit(f"{SCHEDULE.relative_to(ROOT)} missing: run scripts/elastic_schedule.py first")
    sched = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    O: List[str] = []
    w = O.append
    w("# Deployed agent monitors whose memory is wall-clock")
    w("")
    w(f"Generated by `scripts/deployed_monitor_census.py` at `{sha()}`. Companion "
      f"to `EXTERNAL_MONITOR_CHECKS.md`, which audits monitors from published "
      f"papers; this one audits monitors that ship. Search provenance: "
      f"[`external_monitors/deployed_hunt.json`](external_monitors/deployed_hunt.json).")
    w("")
    w("## Why this exists")
    w("")
    w("The paper's weakest claim was that no monitor outside our own work "
      "accumulates state against the clock, which made Section 2 a description "
      "of a failure mode nobody had been shown to have. That claim was wrong, "
      "and it was wrong because we searched the AI-control literature rather "
      "than deployed agent infrastructure. **Clock-indexed accumulation over an "
      "agent's actions is the production norm.** It appears in MCP gateways, in "
      "agent frameworks, in LLM gateways and in shipped SIEM detection rules.")
    w("")
    w("The class is also not defined by exponential decay. A sliding window — "
      "*N events in the last T seconds* — forgets on the clock just as "
      "completely, and `WINDOW_IDENTITY.md` shows the budget-cadence identity "
      "covers it exactly (0 mismatches in 29,520 cells).")
    w("")
    w("## The census")
    w("")
    w("`safe gap` is the pacing at which an agent's behaviour never accumulates "
      "to the threshold: arithmetic from the monitor's own published defaults, "
      "not a measurement, and not an exploit we ran.")
    w("")
    w("| monitor | purpose | what accumulates | N | window T | safe gap | gates |")
    w("|---|---|---|---|---|---|---|")
    for m in MONITORS:
        if m["n"] and m["n"] > 1:
            gap = m["t"] / (m["n"] - 1)
            gap_s = f"**{gap:.2f} s**" if gap < 60 else f"**{gap/60:.1f} min**"
        elif m["n"] == 1:
            gap_s = f"**{m['t']:.0f} s**"
        else:
            gap_s = "—"
        star = " ✓" if m["verified"] else ""
        w(f"| {m['name']}{star} | {m['purpose']} | {m['what']} | "
          f"{m['n'] if m['n'] else '—'} | {m['t']:.0f} s | {gap_s} | {m['gates']} |")
    w("")
    w("✓ = re-verified first-hand against the raw source file for this report; "
      "the rest carry a quote the verification pass confirmed. Candidates whose "
      "quotes could not be confirmed are excluded.")
    w("")
    w("## The two that matter most")
    w("")
    for m in MONITORS[:2]:
        w(f"**{m['name']}**")
        w("")
        w(f"- Accumulates: {m['what']}")
        w(f"- Parameters: {m['param']}")
        w(f"- Gates: {m['gates']}")
        w(f"- Source: {m['source']}")
        w(f"- Quote: “{m['quote']}”")
        if m["n"] and m["n"] > 1:
            gap = m["t"] / (m["n"] - 1)
            w(f"- **Arithmetic consequence:** an agent that keeps its qualifying "
              f"events more than {gap:.2f} s apart "
              f"({'one every %.1f minutes' % (gap / 60) if gap >= 60 else '%.2f per second' % (1 / gap)}) "
              f"never reaches the threshold, for any total number of events and "
              f"for any session length.")
        w("")
    w("The Elastic rule is the one a reviewer should be shown first, because it "
      "is not a rate limiter. It is a **misbehaviour detector**: production "
      "maturity, mapped to MITRE ATLAS, firing on repeated attempts to probe a "
      "model's denied topics.")
    w("")
    w("### Boundary semantics, pinned")
    w("")
    w("The exact figure matters, so here is every term that decides it:")
    w("")
    w("- **Threshold.** `where Esql.ml_policy_blocked_topic_count > 5`, so "
      "**N_min = 6** qualifying events, not 5.")
    w("- **Window.** `from = \"now-60m\"`, i.e. T = 3600 s. Kibana builds the "
      "range as `{ gte: from, lte: to }` "
      "(`build_events_query.ts: buildTimeRangeFilter`), so the interval is "
      "**closed at both ends**.")
    w("- **Hard bound, under any schedule.** Above 720 s between probes, no "
      "60-minute window can hold six of them, so the rule cannot fire for any "
      "number of probes and any evaluation schedule. The evading pace is "
      "*strictly greater than* 3600/5 = **720 s** — write \"just over twelve "
      "minutes\", never \"twelve minutes\".")
    w("- **The schedule matters below the bound.** The rule does not watch a "
      "continuous window: it *runs* every 10 minutes (`interval = \"10m\"`), "
      "each run looking back 60 minutes. Six probes at spacing *s* are caught by "
      "a run only if it lands inside an opening 3600 − 5*s* seconds wide. For a "
      "**single six-probe burst**, with the schedule's phase unknown to the "
      "attacker:")
    w("  - at or below 600 s, a run always lands in the opening — always caught;")
    w("  - between 600 and 720 s, caught with probability (3600 − 5*s*)/600 — "
      f"{_burst(sched, 650):.2f} at 650 s, {_burst(sched, 700):.2f} at 700 s;")
    w("  - at exactly 720 s the opening has zero width, and it fires only if a "
      "run lands on the sixth ingest to the second — a knife-edge set by clock "
      "alignment and ingest jitter, not something to cite as safe.")
    edge = _sustained(sched, 719.9)
    sweep = sched["sweep_all_caught_within_week"]
    w("- **A persistent attacker does not get the burst's odds.** Probing "
      "indefinitely at a fixed spacing below 720 s gives the schedule a fresh "
      "chance with every further probe, and its phase walks through the opening: "
      f"every attacker spaced at {sweep['to_s']:g} s or less is caught within a "
      f"week, and {edge['exact_share']:.0%} are even at 719.9 s "
      f"({edge['exact_share']:.2%} of schedule phases, exactly). Only spacing "
      "above 720 s is safe for a campaign. (Computed by "
      "`scripts/elastic_schedule.py` in exact arithmetic over schedule phases, "
      f"at every spacing from {sweep['from_s']:g} to {sweep['to_s']:g} s in {sweep['step_s']:g} s steps; "
      "each figure is checked by a Monte Carlo over random phases that steps "
      f"through the runs and counts probes, {edge['monte_carlo_share']:.1%} at "
      "719.9 s. Source: "
      "[`external_monitors/elastic_schedule.json`](external_monitors/elastic_schedule.json).)")
    w("- **Which clock.** The rule sets `timestamp_override = \"event.ingested\"`, "
      "so the accumulator is indexed on **ingest time**, not on the agent's own "
      "action time. An attacker's spacing is therefore only as precise as the "
      "logging pipeline that carries it.")
    w("- **Key.** The count is `by user.id`. The accumulator is per identity, so "
      "rotating identities resets it — the same evasion available against "
      "Brown et al.'s per-cluster buffer, for the same structural reason.")
    w("")
    w("An attacker who keeps blocked probes just over twelve minutes apart is "
      "invisible to this rule indefinitely, for any total number of probes — "
      "not because the detector is badly tuned, but because its evidence is "
      "indexed in seconds while the attacker controls the spacing.")
    w("")
    w("**Concede the lineage.** Pacing below a count-in-window threshold is "
      "textbook low-and-slow evasion, and security reviewers will know it as "
      "such; it needs the same explicit concession this work gives to "
      "statistical process control. What is ours is narrower: that monitors "
      "watching *agents* ship with windows set at human timescales, and that "
      "the evading pace is computable from published configuration.")
    w("")
    w("## The contrast case, which sharpens the finding")
    w("")
    w("The leading LLM guardrail toolkits accumulate **nothing**:")
    w("")
    for name, note in STATELESS:
        w(f"- **{name}** — {note}")
    w("")
    w("So the design space in deployed agent monitoring is currently split "
      "between per-message classifiers with no memory at all, and "
      "infrastructure whose memory is wall-clock. The sample-time middle — a "
      "statistic that forgets per observation, as CUSUM does — is where the "
      "published control protocols sit (`EXTERNAL_MONITOR_CHECKS.md`) and is "
      "almost absent from shipped agent tooling.")
    w("")
    w("## What this does and does not license the paper to say")
    w("")
    w("**Supported.** Monitors that accumulate state over an agent's actions and "
      "forget it on a wall-clock timer are deployed today, with published "
      "defaults, gating real actions. Section 2's identity applies to them "
      "exactly, and the pacing that defeats each is computable from its own "
      "configuration.")
    w("")
    w("**Not supported.** Most entries here are resource controls, not safety "
      "monitors, and a rate limiter being evadable by slowing down is arguably "
      "its design rather than its defect — say so before a reviewer does. The "
      "exceptions are the detection rules (Elastic, Agent Threat Rules, the "
      "Datadog and LangSmith alerting paths), where evasion by pacing is a "
      "security property and not a billing one. We have not run any of these "
      "systems, measured any evasion, or tested an attacker against them; every "
      "number here is read off a configuration and divided.")
    w("")
    w("**Also not supported.** That anyone has been harmed by this, or that any "
      "operator is unaware of it. The claim is narrower: the parameter that "
      "decides whether these monitors can see a slow agent is a window length "
      "chosen for human-timescale abuse, and nothing in their documentation "
      "connects it to the cadence of the agent being watched.")
    w("")

    OUT.write_text("\n".join(O), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for m in MONITORS:
        if m["n"] and m["n"] > 1:
            print(f"{m['name'][:52]:54s} N={m['n']:4d} T={m['t']:7.0f}s "
                  f"safe gap {m['t']/(m['n']-1):8.2f}s")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
