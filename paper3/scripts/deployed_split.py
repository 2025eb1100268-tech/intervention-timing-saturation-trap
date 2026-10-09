"""The split: of the agent-facing clock-indexed monitors found, how many
DETECT misuse and how many merely LIMIT rate or spend?

The hunt ran five independent search angles, so the same system was found more
than once and the raw survivor count double-counts. This deduplicates to
distinct systems and classifies each by what it is FOR, because the paper's
claim is only as strong as the detection count: "clock-indexed windows are the
production norm for agent monitoring" means something different if every
instance is a billing control.

Three buckets, and the middle one is not a hedge:
  misuse   -- fires on suspected abuse, attack or policy violation. A security
              control. Evasion by pacing is a security property.
  ops      -- fires on errors, latency or quality regressions. Operational
              alerting. Evasion is not the threat model, but the same
              arithmetic governs whether it can fire at all.
  rate     -- caps requests, tokens or spend. Resource control. Being evadable
              by slowing down is arguably the design, not a defect -- which is
              exactly why these must not be counted as safety monitors.

Classification is a judgement call, so it is written out per system here rather
than asserted in prose, and the rule is stated: a system counts as `misuse`
only if its own documentation frames the accumulated condition as abuse,
attack, threat or policy violation.

Run from repo root:  python scripts/deployed_split.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
HUNT = ROOT / "data" / "swebench_pilot" / "external_monitors" / "deployed_hunt.json"
OUT = ROOT / "data" / "swebench_pilot" / "DEPLOYED_SPLIT.md"

# canonical system -> (bucket, agent_facing, quote_confirmed_somewhere, note)
# One row per distinct SYSTEM. Names as found across angles are mapped below.
CLASSIFY = {
    "Elastic Bedrock denied-topic rule": ("misuse", True, True,
        "counts guardrail BLOCKED/topic_policy events per user.id; 'attempts to probe the model's denied topics'"),
    "Elastic Azure OpenAI DoS rule": ("misuse", True, True,
        "'Potential Denial of Azure OpenAI ML Service'; >=10 ChatCompletions in a 60s bucket"),
    "Agent Threat Rules ATR-2026-00553": ("misuse", True, False,
        "'Runaway tool-call loop within a single session'; actions rate_limit_source, escalate"),
    "Microsoft Purview IRM cumulative exfiltration": ("misuse", True, False,
        "30-day exfiltration accumulation; the agent-policy link was a three-page stitch and is NOT printable"),
    "Fastly Next-Gen WAF attack thresholds": ("misuse", False, False,
        "50 signals/1 min, 350/10 min, 1800/1 hr per IP; not agent-specific"),
    "Datadog Cloud SIEM detection rules": ("misuse", False, True,
        "keepAlive enum in seconds; general SIEM, not agent-specific"),

    "Datadog LLM Observability monitor": ("ops", True, True,
        "error spans, last('15m') > 25, evaluation_delay 300s"),
    "LangSmith alerts": ("ops", True, True,
        "aggregation window settable only to 5 or 15 minutes"),
    "Dynatrace Davis static thresholds": ("ops", False, True,
        "3 of 5 minutes sliding violation default"),
    "AWS CloudWatch metric alarms": ("ops", False, True,
        "M-of-N breaching datapoints, Period in seconds"),

    "Microsoft AGT MCPSlidingRateLimiter": ("rate", True, True,
        "prunes tool-call timestamps older than window_size=300.0s, denies above max_calls_per_window=100"),
    "Microsoft AGT AgentRateLimiter (token bucket)": ("rate", True, False,
        "refill_rate 5.0 tokens/sec; quote unconfirmed"),
    "FastMCP rate limiting middleware": ("rate", True, True,
        "token bucket 10.0 req/s, burst 20; also a sliding-window variant"),
    "LangChain Core InMemoryRateLimiter": ("rate", True, True,
        "state is elapsed * requests_per_second, bucket size 1"),
    "CrewAI RPMController": ("rate", True, True,
        "max_rpm with a hardcoded 60s reset"),
    "LiteLLM proxy limits and budgets": ("rate", True, True,
        "window_size default 60s; budget_duration erases accumulated spend"),
    "Helicone rate-limit policy": ("rate", True, True,
        "w = time window in seconds, minimum 60; u=cents accrues spend"),
    "Kong ai-rate-limiting-advanced": ("rate", True, True,
        "window_size 'defined in seconds', sliding by default, over total_tokens"),
    "Cloudflare AI Gateway rate limiting": ("rate", True, True,
        "rate_limiting_interval / _limit / _technique; fixed vs sliding worked example"),
    "Anthropic Claude API rate limits": ("rate", True, True,
        "token bucket, 'continuously replenished', RPM/ITPM/OTPM"),
}

# Names as they appeared in the hunt -> canonical system, so the dedup is auditable.
ALIASES = {
    "microsoft agent-governance-toolkit — mcp security gateway 1.0 spec (mcpslidingratelimiter)": "Microsoft AGT MCPSlidingRateLimiter",
    "microsoft agent governance toolkit (agt) — agentratelimiter / ratelimiter and rate_limit policy action": "Microsoft AGT AgentRateLimiter (token bucket)",
    "fastmcp — ratelimitingmiddleware / slidingwindowratelimitingmiddleware": "FastMCP rate limiting middleware",
    "langsmith — alerts (aggregation window)": "LangSmith alerts",
    "helicone — custom llm rate limits (helicone-ratelimit-policy)": "Helicone rate-limit policy",
    "helicone — custom llm rate limits (helicone-ratelimit-policy) ": "Helicone rate-limit policy",
    "agent threat rules (atr) — atr-2026-00553 \"runaway tool-call loop within a single session\"": "Agent Threat Rules ATR-2026-00553",
    "anthropic claude api rate limits (token bucket)": "Anthropic Claude API rate limits",
    "anthropic claude api — rate limits (token bucket)": "Anthropic Claude API rate limits",
    "kong ai-rate-limiting-advanced plugin": "Kong ai-rate-limiting-advanced",
    "kong ai gateway — ai-rate-limiting-advanced plugin": "Kong ai-rate-limiting-advanced",
    "cloudflare ai gateway — rate limiting": "Cloudflare AI Gateway rate limiting",
    "cloudflare ai gateway — rate limiting (fixed vs sliding window)": "Cloudflare AI Gateway rate limiting",
    "elastic security prebuilt detection rules for aws bedrock (elastic/detection-rules, rules/integrations/aws_bedrock/)": "Elastic Bedrock denied-topic rule",
    "elastic security prebuilt detection rules for azure openai (elastic/detection-rules, rules/integrations/azure_openai/)": "Elastic Azure OpenAI DoS rule",
    "datadog llm observability monitor (`llm-observability alert` monitor type)": "Datadog LLM Observability monitor",
    "litellm proxy — per-agent and per-session rate limits": "LiteLLM proxy limits and budgets",
    "litellm proxy (open source) — virtual-key budgets and tpm/rpm limits": "LiteLLM proxy limits and budgets",
    "langchain core — inmemoryratelimiter": "LangChain Core InMemoryRateLimiter",
    "crewai — rpmcontroller (max_rpm)": "CrewAI RPMController",
    "microsoft purview insider risk management — \"risky agents (preview)\" policy + policy timeframes + cumulative exfiltration detection": "Microsoft Purview IRM cumulative exfiltration",
    "datadog cloud siem / security monitoring detection rules": "Datadog Cloud SIEM detection rules",
    "aws cloudwatch metric alarms (period / evaluation periods / datapoints to alarm)": "AWS CloudWatch metric alarms",
    "dynatrace davis ai — static thresholds for anomaly detection": "Dynatrace Davis static thresholds",
    "fastly next-gen waf (signal sciences) — attack thresholds": "Fastly Next-Gen WAF attack thresholds",
}


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def main() -> int:
    hunt = json.loads(HUNT.read_text(encoding="utf-8"))
    raw_survivors, unmapped = [], []
    seen_by_system: Dict[str, List[str]] = {}
    for angle in hunt["angles"]:
        for v in angle.get("verdicts", []) or []:
            if not v.get("survives"):
                continue
            raw = v.get("name", "")
            raw_survivors.append(raw)
            canon = ALIASES.get(raw.strip().lower())
            if canon is None:
                unmapped.append(raw)
                continue
            seen_by_system.setdefault(canon, []).append(angle["angle"])

    systems = sorted(seen_by_system)
    buckets = {"misuse": [], "ops": [], "rate": []}
    for s in systems:
        b, agent, conf, note = CLASSIFY[s]
        buckets[b].append((s, agent, conf, note, seen_by_system[s]))

    agent_facing = [s for s in systems if CLASSIFY[s][1]]
    ag_mis = [s for s in agent_facing if CLASSIFY[s][0] == "misuse"]
    ag_ops = [s for s in agent_facing if CLASSIFY[s][0] == "ops"]
    ag_rate = [s for s in agent_facing if CLASSIFY[s][0] == "rate"]
    printable = [s for s in ag_mis if CLASSIFY[s][2]]

    O: List[str] = []
    w = O.append
    w("# The split: misuse detection vs rate control")
    w("")
    w(f"Generated by `scripts/deployed_split.py` at `{sha()}`. Deduplicates "
      f"[`external_monitors/deployed_hunt.json`](external_monitors/deployed_hunt.json) "
      f"to distinct systems and classifies each by what it is for.")
    w("")
    w("## Headline")
    w("")
    w(f"- **{len(raw_survivors)} raw survivor rows** across five search angles, "
      f"which is what an earlier summary reported. Those angles overlapped: the "
      f"rows collapse to **{len(systems)} distinct systems**. Any count above "
      f"that number double-counts.")
    w(f"- **{len(agent_facing)} of {len(systems)}** are agent-facing (they watch "
      f"LLM or agent traffic rather than general infrastructure).")
    w(f"- Of those {len(agent_facing)}: **{len(ag_mis)} misuse detection**, "
      f"**{len(ag_ops)} operational alerting**, **{len(ag_rate)} rate or spend "
      f"control**.")
    w(f"- Misuse detectors whose quote a verification pass confirmed, and which "
      f"are therefore printable: **{len(printable)}** "
      f"({', '.join(printable)}).")
    w("")
    w("**So the honest form of the claim is:** clock-indexed accumulation is the "
      f"production norm for agent **rate control** ({len(ag_rate)} of "
      f"{len(agent_facing)} agent-facing systems), and it also appears in "
      f"{len(ag_mis)} agent-facing **misuse detectors**, of which "
      f"{len(printable)} can be cited with a confirmed configuration. The "
      "stronger sentence — that it is the norm for agent *monitoring* — is not "
      "supported by these counts and should not be written.")
    w("")
    w("## By bucket")
    w("")
    for b, label in (("misuse", "Misuse / attack detection — evasion by pacing is a security property"),
                     ("ops", "Operational alerting — errors, latency, quality"),
                     ("rate", "Rate, token or spend control — evadability by slowing down is arguably the design")):
        w(f"### {label}")
        w("")
        w("| system | agent-facing | quote confirmed | what accumulates | found by |")
        w("|---|---|---|---|---|")
        for s, agent, conf, note, angles in buckets[b]:
            w(f"| {s} | {'yes' if agent else 'no'} | {'yes' if conf else '**no**'} | "
              f"{note} | {', '.join(sorted(set(angles)))} |")
        w("")
    w("## The selection problem, stated")
    w("")
    w("This search looked for clock-indexed configurations and found "
      "clock-indexed configurations. It did **not** search for count-indexed "
      "accumulators with comparable effort, so it cannot support a claim that "
      "the sample-time middle is rare in deployed tooling. What it does support "
      "is narrower and still useful: among the systems we examined, the "
      "accumulating ones forget on the clock, and the three leading LLM "
      "guardrail toolkits we checked (NeMo Guardrails, Guardrails AI, Lakera) "
      "accumulate nothing at all — their schemas contain no window, decay or "
      "cooldown, only request timeouts. Any sentence about what is *absent* "
      "must be scoped to what was searched.")
    w("")

    OUT.write_text("\n".join(O), encoding="utf-8")
    # Machine-readable copy for the paper's appendix (no new numbers).
    (HUNT.parent / "deployed_split.json").write_text(json.dumps({
        "raw_survivor_rows": len(raw_survivors),
        "systems": [{"system": s, "purpose": CLASSIFY[s][0], "agent_facing": CLASSIFY[s][1],
                     "confirmed": CLASSIFY[s][2], "configuration": CLASSIFY[s][3],
                     "angles": sorted(set(seen_by_system[s]))} for s in systems],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if unmapped:
        print("UNMAPPED survivor names (add to ALIASES):")
        for u in unmapped:
            print("   ", u[:100])
    print(f"raw survivor rows {len(raw_survivors)} -> distinct systems {len(systems)}")
    print(f"agent-facing {len(agent_facing)}: misuse {len(ag_mis)}, ops {len(ag_ops)}, rate {len(ag_rate)}")
    print(f"printable misuse detectors: {len(printable)} -> {printable}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 1 if unmapped else 0


if __name__ == "__main__":
    sys.exit(main())
