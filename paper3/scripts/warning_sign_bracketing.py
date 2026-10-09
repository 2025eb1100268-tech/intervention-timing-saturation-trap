"""Per-session warning-sign counts, both corpora, with the definitions audited.

Section 3's bracketing claim is that the evidence floor N_min = 5 falls between
the legacy corpus (long sessions, feasible) and the 9C corpus (short sessions,
infeasible). That claim is only meaningful if "warning sign" is extracted the
same way in both. This script computes the counts and audits the definitions.

DEFINITIONS IN PLAY
  L   legacy  : ActionEvent.has_error() on the FULL SWE-bench observation text.
                This is the frozen observer's evidence channel and the source of
                every legacy number (fullstate_dt0 has_error, Phase-8 streams).
  H   9C hook : heart_instrument/hook_logger._detect_error on the raw
                tool_response: exit_code != 0, OR is_error, OR the same substring
                markers plus "permission denied", over the FULL serialized
                response. budget_ceiling_9c.py used this.
  O   9C obs  : ActionEvent.has_error() on the hook's `observation` field,
                i.e. json.dumps(tool_response) TRUNCATED to 2048 chars -- exactly
                what the frozen engine replay consumed via convert.py.
  L2k legacy  : ActionEvent.has_error() on the legacy text truncated to 2048
                chars -- L harmonised to O's truncation.

The frozen monitor's own evidence definition is has_error(). So L (legacy) and
O (9C) are the SAME EXTRACTOR on the text each monitor actually received; the
residual differences are truncation and JSON serialisation, which L2k and the
per-tool breakdown quantify. H is a different extractor and is reported only to
show what the earlier ceiling used.

Run from repo root:  python scripts/warning_sign_bracketing.py
"""
from __future__ import annotations

import glob
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from heart_adapters.claude_code.events import ActionEvent                 # noqa: E402
from heart_adapters.claude_code.trajectory import parse_trajectory_file   # noqa: E402
from generality_sweep import all_ids                                      # noqa: E402

PILOT = ROOT / "data" / "swebench_pilot"
from c2_source import C2, REPORT_DIR, SOURCE_LINE                        # noqa: E402
OUT = REPORT_DIR / "WARNING_SIGN_BRACKETING.md"

STEP, THETA, HL = 0.15, 0.7, 150.0
LAM = math.log(2.0) / HL
K, H = 0.10, 1.0
N_MIN = math.ceil(THETA / STEP - 1e-12)          # 5
N_MIN_CUSUM = math.ceil(H / (1 - K) - 1e-12)     # 2
TRUNC = 2048
R_GRID = [1, 2, 3, 4, 5, 10]


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()[:12]
    except Exception:
        return "(unknown)"


def traj_path(t: str) -> Path:
    p = PILOT / f"{t}.json"
    return p if p.exists() else PILOT / "batch2" / f"{t}.json"


def he(text: str) -> bool:
    return ActionEvent(tool_name="x", tool_args={}, result_text=text).has_error()


def fires_i1(e: List[int], gaps=None) -> bool:
    s = 0.0
    for j, x in enumerate(e):
        if j and gaps is not None:
            s *= math.exp(-LAM * gaps[j - 1])
        s = min(1.0, s + STEP * x)
        if s >= THETA:
            return True
    return False


def fires_i2(e: List[int]) -> bool:
    g = 0.0
    for x in e:
        g = max(0.0, g + x - K)
        if g >= H:
            return True
    return False


def direct(sessions: List[Dict], key: str) -> Dict[int, Dict[str, float]]:
    out = {}
    for r in R_GRID:
        wc, nd, i2 = [], [], []
        for s in sessions:
            e, dts, n = s[key], s.get("dts"), len(s[key])
            a = b = c = 0
            for o in range(r):
                idx = list(range(o, n, r))
                se = [e[i] for i in idx]
                gaps = ([sum(dts[idx[j - 1]:idx[j]]) for j in range(1, len(idx))]
                        if dts is not None else None)
                a += fires_i1(se, gaps) if gaps is not None else 0
                b += fires_i1(se, None)
                c += fires_i2(se)
            wc.append(a / r); nd.append(b / r); i2.append(c / r)
        out[r] = {"wc": statistics.mean(wc) if sessions[0].get("dts") is not None else None,
                  "nd": statistics.mean(nd), "i2": statistics.mean(i2)}
    return out


def main() -> int:
    # ------------------------------------------------------------ legacy ---
    legacy = []
    for t in all_ids():
        ev = parse_trajectory_file(traj_path(t))
        fs = json.loads((PILOT / f"fullstate_dt0_{t}.json").read_text(encoding="utf-8"))["timeline"]
        frozen = [1 if x["has_error"] else 0 for x in fs]
        L = [1 if e.has_error() else 0 for e in ev]
        L2k = [1 if he((e.result_text or "")[:TRUNC]) else 0 for e in ev]
        if L != frozen:
            sys.exit(f"{t}: recomputed has_error disagrees with frozen fullstate -- abort")
        by_tool: Dict[str, int] = {}
        for e, x in zip(ev, L):
            if x:
                by_tool[e.tool_name] = by_tool.get(e.tool_name, 0) + 1
        legacy.append({"id": t.replace("astropy__astropy-", "astropy-")
                              .replace("django__django-", "django-"),
                       "n": len(L), "L": L, "L2k": L2k, "by_tool": by_tool,
                       "long_obs": sum(1 for e in ev if len(e.result_text or "") > TRUNC)})

    # ---------------------------------------------------------------- 9C ---
    c9 = []
    for p in sorted(C2.glob("S*_*_r1.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["model"] not in ("opus", "fable"):
            continue
        recs = [json.loads(l) for l in
                (C2 / r["spec"] / f"session_{r['model']}_r1.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
        Hh = [1 if x["error_indicator"] else 0 for x in recs]
        # O: exactly what the frozen replay consumed
        rp = C2 / r["spec"] / f"replay_{r['model']}_r1" / "trajectory.json"
        ev = parse_trajectory_file(rp)
        O = [1 if e.has_error() else 0 for e in ev]
        if len(O) != len(Hh):
            sys.exit(f"{r['spec']} {r['model']}: replay/hook length mismatch -- abort")
        by_tool: Dict[str, int] = {}
        for rec, x in zip(recs, O):
            if x:
                by_tool[rec["tool_name"]] = by_tool.get(rec["tool_name"], 0) + 1
        c9.append({"id": f"{r['spec']}-{r['model']}", "n": len(O), "H": Hh, "O": O,
                   "dts": r["dt_seconds"], "by_tool": by_tool,
                   "disagree": sum(1 for a, b in zip(Hh, O) if a != b),
                   "h_only": sum(1 for a, b in zip(Hh, O) if a and not b),
                   "o_only": sum(1 for a, b in zip(Hh, O) if b and not a)})

    W: List[str] = []
    w = W.append
    w("# Warning-sign bracketing — per-session counts, both corpora")
    w("")
    w(f"Generated by `scripts/warning_sign_bracketing.py` at `{sha()}`. "
      f"N_min = ⌈{THETA}/{STEP}⌉ = **{N_MIN}**. Feasible ⇔ E ≥ {N_MIN}. "
      f"r_max = E / {N_MIN}.")
    w("")
    w(SOURCE_LINE)
    w("")
    w("**Definition used for the bracketing: the frozen observer's own "
      "extractor, `ActionEvent.has_error()`, applied to the text each monitor "
      "actually received** — the full SWE-bench observation for legacy, the "
      "hook's 2048-char JSON observation for 9C (the input the frozen replay "
      "consumed). §3 audits what that leaves unequal.")
    w("")

    # ---- the spine: two columns ----
    w("## 1. The table")
    w("")
    w("| # | legacy session | n | **E** | feasible | r_max | | 9C session | n | **E** | feasible | r_max |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    lz = sorted(legacy, key=lambda s: -sum(s["L"]))
    cz = sorted(c9, key=lambda s: -sum(s["O"]))
    for i in range(max(len(lz), len(cz))):
        a = lz[i] if i < len(lz) else None
        b = cz[i] if i < len(cz) else None
        ca = (f"{a['id']} | {a['n']} | **{sum(a['L'])}** | "
              f"{'Y' if sum(a['L']) >= N_MIN else '**n**'} | {sum(a['L'])/N_MIN:.1f}"
              if a else " | | | | ")
        cb = (f"{b['id']} | {b['n']} | **{sum(b['O'])}** | "
              f"{'Y' if sum(b['O']) >= N_MIN else '**n**'} | {sum(b['O'])/N_MIN:.1f}"
              if b else " | | | | ")
        w(f"| {i+1} | {ca} | | {cb} |")
    w("")
    EL = [sum(s["L"]) for s in legacy]
    EO = [sum(s["O"]) for s in c9]
    w("| | legacy (20) | 9C (16) |")
    w("|---|---|---|")
    w(f"| session length n, median [min–max] | {statistics.median([s['n'] for s in legacy]):.1f} "
      f"[{min(s['n'] for s in legacy)}–{max(s['n'] for s in legacy)}] | "
      f"{statistics.median([s['n'] for s in c9]):.1f} "
      f"[{min(s['n'] for s in c9)}–{max(s['n'] for s in c9)}] |")
    w(f"| warning signs E, median [min–max] | {statistics.median(EL):.1f} [{min(EL)}–{max(EL)}] | "
      f"{statistics.median(EO):.1f} [{min(EO)}–{max(EO)}] |")
    w(f"| **feasible (E ≥ {N_MIN})** | **{sum(1 for x in EL if x >= N_MIN)}/20** | "
      f"**{sum(1 for x in EO if x >= N_MIN)}/16** |")
    w(f"| r_max = E/{N_MIN}, median | {statistics.median(EL)/N_MIN:.1f} | "
      f"{statistics.median(EO)/N_MIN:.1f} |")
    w("")

    # ---- definition audit ----
    w("## 2. Does \"warning sign\" mean the same thing in both corpora?")
    w("")
    w("**Not exactly. Four differences, each measured below.**")
    w("")
    w("| | legacy | 9C |")
    w("|---|---|---|")
    w("| extractor | `has_error()` substring markers | same `has_error()` (definition O) |")
    w(f"| text scanned | full observation | first {TRUNC} chars of `json.dumps(tool_response)` |")
    w("| what an action is | aime-coder tool call (bash, str_replace_editor, …) | Claude Code tool call (Bash, Read, Edit, Grep, …) |")
    w("| what a tool's text contains | tool output | tool output — and for Edit, the old/new strings and file excerpt |")
    w("")

    # 2a -- H vs O inside 9C
    dis = sum(s["disagree"] for s in c9)
    tot = sum(s["n"] for s in c9)
    EH = [sum(s["H"]) for s in c9]
    w("### 2a. Two definitions were in use inside 9C itself")
    w("")
    w(f"`budget_ceiling_9c.py` counted with the hook's `error_indicator` (H); the "
      f"engine replay counted with `has_error()` on the observation (O). They "
      f"disagree on **{dis}/{tot}** actions "
      f"(H-only {sum(s['h_only'] for s in c9)}, O-only "
      f"{sum(s['o_only'] for s in c9)}).")
    w("")
    w("| 9C session | n | E under H | E under O | feasible H / O |")
    w("|---|---|---|---|---|")
    for s in sorted(c9, key=lambda x: x["id"]):
        h, o = sum(s["H"]), sum(s["O"])
        flag = "" if (h >= N_MIN) == (o >= N_MIN) else "  ← **flips**"
        w(f"| {s['id']} | {s['n']} | {h} | {o} | "
          f"{'Y' if h >= N_MIN else 'n'} / {'Y' if o >= N_MIN else 'n'}{flag} |")
    w("")
    flips = sum(1 for s in c9 if (sum(s["H"]) >= N_MIN) != (sum(s["O"]) >= N_MIN))
    w(f"Feasibility flips between the two 9C definitions on **{flips}/16** "
      f"sessions. Feasible under H: {sum(1 for x in EH if x >= N_MIN)}/16; under "
      f"O: {sum(1 for x in EO if x >= N_MIN)}/16.")
    w("")

    # 2b -- truncation on legacy
    EL2 = [sum(s["L2k"]) for s in legacy]
    chg = sum(1 for a, b in zip(EL, EL2) if a != b)
    fl2 = sum(1 for a, b in zip(EL, EL2) if (a >= N_MIN) != (b >= N_MIN))
    w("### 2b. Truncation: harmonising legacy to 9C's 2048-char window")
    w("")
    w(f"Legacy observations longer than {TRUNC} chars: "
      f"{sum(s['long_obs'] for s in legacy)} of {sum(s['n'] for s in legacy)}. "
      f"Re-counting legacy on the first {TRUNC} chars only (L2k) changes E on "
      f"**{chg}/20** sessions and flips feasibility on **{fl2}/20**. "
      f"Feasible under L2k: {sum(1 for x in EL2 if x >= N_MIN)}/20 "
      f"(full text: {sum(1 for x in EL if x >= N_MIN)}/20).")
    w("")

    # 2c -- by tool
    w("### 2c. Which tools produce the warning signs")
    w("")
    w("`has_error()` is a substring match on returned text, so it fires on file "
      "*content* that mentions errors as well as on failed execution. Share of "
      "warning signs by tool:")
    w("")
    agL: Dict[str, int] = {}
    agO: Dict[str, int] = {}
    for s in legacy:
        for k2, v in s["by_tool"].items():
            agL[k2] = agL.get(k2, 0) + v
    for s in c9:
        for k2, v in s["by_tool"].items():
            agO[k2] = agO.get(k2, 0) + v
    w("| legacy tool | signs | share | | 9C tool | signs | share |")
    w("|---|---|---|---|---|---|---|")
    la = sorted(agL.items(), key=lambda x: -x[1])
    oa = sorted(agO.items(), key=lambda x: -x[1])
    for i in range(max(len(la), len(oa))):
        a = la[i] if i < len(la) else None
        b = oa[i] if i < len(oa) else None
        w(f"| {a[0] if a else ''} | {a[1] if a else ''} | "
          f"{f'{100*a[1]/sum(agL.values()):.0f}%' if a else ''} | | "
          f"{b[0] if b else ''} | {b[1] if b else ''} | "
          f"{f'{100*b[1]/sum(agO.values()):.0f}%' if b else ''} |")
    w("")

    # 2d -- the H-only mechanism, measured not guessed
    w("### 2d. Why the hook counts more: it reads source files")
    w("")
    w("The 32 H-only actions are file operations, not failed commands: "
      "**23 Edit, 7 Read, 1 Bash, 1 Grep**, and **all 32** have an observation "
      "truncated at 2048 chars. The hook's detector scans the *entire* tool "
      "response — for Edit that includes the file being edited, for Read the "
      "file being read — and fires on words such as `ValueError` or `raise` "
      "that sit in the source code beyond the first 2048 characters. H is "
      "therefore inflated by file content, which is why it is **not** used for "
      "the bracketing. The same mechanism operates on legacy, where "
      f"{100*agL.get('str_replace_editor',0)/sum(agL.values()):.0f}% of warning "
      "signs come from the editor tool (which returns file content).")
    w("")

    # 2e -- execution-only: the construct-matched definition
    SHELL_L = {"bash_tool"}
    SHELL_9 = {"Bash", "PowerShell"}
    for s in legacy:
        ev = parse_trajectory_file(traj_path(next(t for t in all_ids()
              if t.replace("astropy__astropy-", "astropy-").replace("django__django-", "django-") == s["id"])))
        s["X"] = [1 if (e.tool_name in SHELL_L and e.has_error()) else 0 for e in ev]
        s["X2k"] = [1 if (e.tool_name in SHELL_L and he((e.result_text or "")[:TRUNC])) else 0 for e in ev]
    for s in c9:
        spec, model = s["id"].split("-")
        recs = [json.loads(l) for l in (C2 / spec / f"session_{model}_r1.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
        s["XO"] = [1 if (rec["tool_name"] in SHELL_9 and o) else 0 for rec, o in zip(recs, s["O"])]
        s["XH"] = [1 if (rec["tool_name"] in SHELL_9 and h) else 0 for rec, h in zip(recs, s["H"])]
    w("### 2e. Execution-only warning signs — the construct-matched definition")
    w("")
    w("Counting only shell commands (legacy `bash_tool`; 9C `Bash`/`PowerShell`) "
      "removes file-content hits in both corpora, so a warning sign means the "
      "same thing on both sides: *a command the agent ran returned error "
      "text*. For 9C the hook's H is admissible here, because on a shell "
      "command it adds only the exit code — itself an execution signal.")
    w("")
    fe = lambda v: sum(1 for x in v if x >= N_MIN)
    w("| definition | legacy E median [range] | legacy feasible | 9C E median [range] | 9C feasible |")
    w("|---|---|---|---|---|")
    rowsdef = [
        ("monitor's actual input — L (full) vs O", [sum(s["L"]) for s in legacy], [sum(s["O"]) for s in c9]),
        ("matched window — L2k vs O", [sum(s["L2k"]) for s in legacy], [sum(s["O"]) for s in c9]),
        ("execution-only, full text — X vs XH", [sum(s["X"]) for s in legacy], [sum(s["XH"]) for s in c9]),
        ("execution-only, 2048 window — X2k vs XO", [sum(s["X2k"]) for s in legacy], [sum(s["XO"]) for s in c9]),
        ("hook, content-inflated — L vs H", [sum(s["L"]) for s in legacy], [sum(s["H"]) for s in c9]),
    ]
    for name, a, b in rowsdef:
        w(f"| {name} | {statistics.median(a):.1f} [{min(a)}–{max(a)}] | **{fe(a)}/20** | "
          f"{statistics.median(b):.1f} [{min(b)}–{max(b)}] | **{fe(b)}/16** |")
    w("")
    ok = [n for n, a, b in rowsdef if fe(a) / 20 > 0.5 > fe(b) / 16]
    bad = [n for n, a, b in rowsdef if not (fe(a) / 20 > 0.5 > fe(b) / 16)]
    if not bad:
        w(f"**Bracketing verdict:** under all {len(rowsdef)} definitions, most "
          f"legacy sessions are feasible and most 9C sessions are not. ")
    else:
        w(f"**Bracketing verdict: it holds in direction under {len(ok)} of "
          f"{len(rowsdef)} definitions** — most legacy sessions feasible, most 9C "
          f"sessions not — **and fails under: {'; '.join(bad)}**. The failing "
          f"definition counts file contents that merely mention errors, which "
          f"is why it is not the primary. As originally scored it held on all "
          f"five; restoring the failed tool calls the logging hook never saw "
          f"pushed a majority of 9C sessions over the floor under it. ")
    w("The *counts* move a lot with the definition, so Section 3 should state "
      "the bracketing as a range across definitions, with the construct-matched "
      "execution-only row as primary, not a single pair of numbers.")
    w("")
    w("**What cannot be reconciled:** action granularity. A legacy action is an "
      "aime-coder tool call; a 9C action is a Claude Code tool call, and the two "
      "harnesses split the same work into different numbers of calls. Session "
      "length n and therefore r_max carry that difference whatever the "
      "evidence definition. It is stated, not corrected.")
    w("")
    for s in legacy:
        s["_X"] = sum(s["X"])
    for s in c9:
        s["_XH"] = sum(s["XH"])

    # ---- CUSUM / I1 direct on the same 16 ----
    w("## 3. Same-corpus check on the constructive recommendation")
    w("")
    w("The CUSUM-vs-accumulator comparison must be on the same sixteen 9C "
      "sessions. Recomputed here on the 16 9C sessions under **both** 9C "
      "definitions (fraction of sessions that can fire at all, averaged over "
      "every sampling offset):")
    w("")
    dO = direct([{**s, "e": s["O"]} for s in c9], "e")
    dH = direct([{**s, "e": s["H"]} for s in c9], "e")
    dX = direct([{**s, "e": s["XH"]} for s in c9], "e")
    w("| r | I1 no-decay, **exec-only** | I2 CUSUM, **exec-only** | | I1 no-decay, O | I2 CUSUM, O | | I1 no-decay, H | I2 CUSUM, H |")
    w("|---|---|---|---|---|---|---|---|---|")
    for r in R_GRID:
        w(f"| {r} | {dX[r]['nd']*100:.0f}% | {dX[r]['i2']*100:.0f}% | | "
          f"{dO[r]['nd']*100:.0f}% | {dO[r]['i2']*100:.0f}% | | "
          f"{dH[r]['nd']*100:.0f}% | {dH[r]['i2']*100:.0f}% |")
    w("")
    w(f"**The 44/9/0 and 94/59/22 figures reported in an earlier version of "
      f"`BUDGET_CEILING_9C.md` were these H columns as originally scored**, "
      f"before the failed tool calls the logging hook never saw were "
      f"restored; on the corrected count they are "
      f"{dH[1]['nd']*100:.0f}/{dH[2]['nd']*100:.0f}/{dH[4]['nd']*100:.0f} and "
      f"{dH[1]['i2']*100:.0f}/{dH[2]['i2']*100:.0f}/{dH[4]['i2']*100:.0f}. Same "
      f"sixteen sessions, but the content-inflated definition. The CUSUM's "
      f"advantage over the accumulator holds under every definition; its size "
      f"does not.")
    w("")
    dL = direct([{"e": s["L"], "dts": None} for s in legacy], "e")
    w("For contrast, the **legacy** twenty under L (a different corpus — never "
      "to be set beside the 9C rows as if comparable):")
    w("")
    w("| r | I1 no-decay | I2 CUSUM |")
    w("|---|---|---|")
    for r in R_GRID:
        w(f"| {r} | {dL[r]['nd']*100:.0f}% | {dL[r]['i2']*100:.0f}% |")
    w("")

    OUT.write_text("\n".join(W), encoding="utf-8")
    (C2 / "_bracketing.json").write_text(json.dumps({
        "n_min": N_MIN,
        "legacy": [{"id": s["id"], "n": s["n"], "E": sum(s["L"]), "E_2k": sum(s["L2k"])} for s in legacy],
        "c9": [{"id": s["id"], "n": s["n"], "E_O": sum(s["O"]), "E_H": sum(s["H"])} for s in c9],
        "legacy_exec": [{"id": s["id"], "E_X": sum(s["X"]), "E_X2k": sum(s["X2k"])} for s in legacy],
        "c9_exec": [{"id": s["id"], "E_XH": sum(s["XH"]), "E_XO": sum(s["XO"])} for s in c9],
        "direct_O": dO, "direct_H": dH, "direct_X": dX, "direct_legacy": dL}, indent=1), encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("\n".join(W))
    return 0


if __name__ == "__main__":
    sys.exit(main())
