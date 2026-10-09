"""Regenerate the erratum blocks of Paper 1 v2 and Paper 2 v2 from the canonical record.

The corrections each v2 quotes live in scripts/withdrawals.py. This script
rewrites, idempotently, the block between BEGIN/END markers in each paper's
LaTeX (and, on first run, the hand-placed block it replaces), so a wording
change in the record is one command away from both papers.
scripts/lint_errata_notices.py then checks the result word for word.

    python scripts/v2_errata.py --paper1 .wf/wt-p1v2 --paper2 .wf/wt-p2v2

Each path is a checkout of the corresponding v2 branch (paper1-arxiv-v2,
paper2-arxiv-v2). Commit there afterwards.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BS = "\\"
UNICODE = {"Δ": BS + "ensuremath{" + BS + "Delta}", "—": BS + "textemdash", "–": BS + "textendash",
           "×": BS + "ensuremath{" + BS + "times}", "−": BS + "ensuremath{-}", "≥": BS + "ensuremath{" + BS + "geq}"}


def canonical() -> dict:
    spec = importlib.util.spec_from_file_location("wd", ROOT / "scripts" / "withdrawals.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    out = {}
    for e in wd.ERRATA:
        if "correction" in e:
            out[e["id"]] = e["correction"]
        for it in e.get("items", []):
            out[it["id"]] = it["correction"]
    return out


def tex(s: str) -> str:
    for a in ("%", "&", "_", "#", "$"):
        s = s.replace(a, BS + a)
    return re.sub(r"(^|[\s(])'", r"\1`", s)          # opening single quotes


def quote(s: str) -> str:
    return BS + "begin{quote}\n" + tex(s) + "\n" + BS + "end{quote}\n"


def replace_block(text: str, begin: str, end: str, block: str, legacy: tuple) -> str:
    """Replace between markers; on first run, replace the legacy hand-placed span."""
    marked = begin + "\n" + block + end + "\n"
    if begin in text:
        a = text.index(begin)
        b = text.index(end, a) + len(end) + 1
        return text[:a] + marked + text[b:]
    a = text.index(legacy[0])
    b = text.index(legacy[1], a) + (len(legacy[1]) if legacy[2] else 0)
    return text[:a] + marked + text[b:]


def ensure_unicode(text: str, quoted: str, anchor: str) -> str:
    need = sorted({c for c in quoted if ord(c) > 127})
    missing = [c for c in need if "newunicodechar{" + c + "}" not in text]
    unknown = [c for c in missing if c not in UNICODE]
    if unknown:
        raise SystemExit(f"no LaTeX mapping for {unknown}")
    if not missing:
        return text
    lines = ""
    if BS + "usepackage{newunicodechar}" not in text:
        lines += BS + "usepackage{newunicodechar}\n"
    lines += "".join(BS + "newunicodechar{" + c + "}{" + UNICODE[c] + "}\n" for c in missing)
    return text.replace(anchor, anchor + "% v2: characters the quoted corrections use.\n" + lines, 1)


def paper1(root: Path, c: dict) -> None:
    f = root / "paper1" / "intervention_timing_paper.tex"
    t = f.read_text(encoding="utf-8")
    block = (
        "% Items (a) and (b) quote scripts/withdrawals.py (E0, E1) verbatim. Do not edit\n"
        "% here: edit the record and re-run scripts/v2_errata.py (heart-observer).\n"
        + BS + "noindent" + BS + "fbox{" + BS + "begin{minipage}{" + BS + "dimexpr" + BS + "linewidth-2"
        + BS + "fboxsep-2" + BS + "fboxrule" + BS + "relax}\n" + BS + "small\n"
        + BS + "textbf{Erratum notice (version 2).} Version~1 of this paper contains two\n"
        "errors, both in the mechanism it gives for the State Saturation Trap. Each is\n"
        "stated below in the words of its canonical source. The rest of the text is\n"
        "unchanged from version~1; the three passages that rest on these errors are\n"
        "footnoted.\n\n" + BS + "smallskip\n"
        + BS + "noindent" + BS + "textbf{(a) Decay never executed in the replays.} From the erratum\n"
        "published in~" + BS + "cite{modgil2026bistable} (Section~3), which refers to this paper as\n[P1]:\n"
        + quote(c["E0"]) +
        "The code-path audit behind it is released with that paper\n(" + BS + "texttt{paper2/prereg/DT"
        + BS + "_AUDIT.md}).\n\n"
        + BS + "noindent" + BS + "textbf{(b) The observer could not register recovery.} From the\n"
        "errata record of~" + BS + "cite{modgil2026sok}, which refers to this paper as Paper~1:\n"
        + quote(c["E1"]) + "\n"
        + BS + "noindent" + BS + "textbf{What stands.} The saturation firing rates and the replay\n"
        "consistency reported in Section~" + BS + "ref{sec:saturation} are deterministic\n"
        "functions of the pipeline and are unchanged. The inter-rater results of\n"
        "Section~" + BS + "ref{sec:irr} involve no instrument and are unchanged. What changes is\n"
        "the attribution of the saturation to the agents. The full audit is\n"
        "in~" + BS + "cite{modgil2026sok}.\n"
        + BS + "end{minipage}}\n" + BS + "medskip\n")
    t = replace_block(t, "% BEGIN v2 erratum notice", "% END v2 erratum notice", block,
                      ("% ---- v2 erratum notice.", BS + "medskip\n", True))
    t = ensure_unicode(t, c["E0"] + c["E1"], BS + "newcommand{" + BS + "alphacoef}{" + BS + "ensuremath{" + BS + "alpha}}\n")
    f.write_text(t, encoding="utf-8", newline="\n")
    print(f"paper1: notice regenerated in {f}")


def paper2(root: Path, c: dict) -> None:
    f = root / "paper2" / "sections" / "body.tex"
    t = f.read_text(encoding="utf-8")
    block = (
        BS + "paragraph{Erratum to this paper (v2).} Version~1 of this paper contains three\n"
        "errors, corrected in this version. Each correction is quoted below from the\n"
        "errata record of~" + BS + "cite{P3}, which refers to this paper as Paper~2.\n\n"
        + BS + "emph{(1) How the cadence was measured.} Version~1 described the timing runs of\n"
        "Section~" + BS + "ref{sec:cadence} as hook-instrumented (abstract;\n"
        "Sections~" + BS + "ref{sec:intro} and~" + BS + "ref{sec:cadence}).\n"
        + quote(c["E2b"]) +
        "This version names the model. The correction bears only on how far the\n"
        "measured cadence generalises, which Section~" + BS + "ref{sec:limitations} already\n"
        "bounded (``a lower bound for frontier loops---the deployments most likely to\n"
        "enter the transition band are exactly the ones not measured''). The abstract,\n"
        "Sections~" + BS + "ref{sec:intro}, " + BS + "ref{sec:cadence} and~" + BS + "ref{sec:limitations}, and the\n"
        "Instrumentation appendix are corrected in this version.\n\n"
        + BS + "emph{(2) The cross-instrument correlation.} Version~1 reports that\n"
        "per-trajectory critical intervals correlate between the two instruments at\n"
        "Spearman $" + BS + "rho = 0.530$ (abstract; Section~" + BS + "ref{sec:class}).\n"
        + quote(c["E2a"]) +
        "Both passages are footnoted in this version.\n\n"
        + BS + "emph{(3) The scope of the abstract's cadence claim.} Version~1's abstract said\n"
        "that real autonomous coding cadence sits firmly inside the trap regime.\n"
        + quote(c["E2c"]) +
        "This version's abstract narrows the claim to the measured cadence.\n\n")
    t = replace_block(t, "% BEGIN v2 erratum (generated by heart-observer scripts/v2_errata.py; edit the record, not this)",
                      "% END v2 erratum", block,
                      (BS + "paragraph{Erratum to this paper (v2).}", BS + "section{The Uniform-Cadence Sweep}", False))
    f.write_text(t, encoding="utf-8", newline="\n")
    main_tex = root / "paper2" / "main.tex"
    m = main_tex.read_text(encoding="utf-8")
    missing = sorted({ch for ch in c["E2a"] + c["E2b"] + c["E2c"] if ord(ch) > 127
                      and "newunicodechar{" + ch + "}" not in m})
    if missing:
        raise SystemExit(f"paper2/main.tex lacks newunicodechar mappings for {missing}")
    print(f"paper2: erratum regenerated in {f}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper1", type=Path)
    ap.add_argument("--paper2", type=Path)
    a = ap.parse_args(argv)
    c = canonical()
    if a.paper1:
        paper1(a.paper1, c)
    if a.paper2:
        paper2(a.paper2, c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
