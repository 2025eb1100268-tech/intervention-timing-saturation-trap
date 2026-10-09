"""Lint the v2 erratum notices of Papers 1 and 2 against their canonical text.

Each correction a v2 carries must appear in its LaTeX word for word, as written
in its single source, `scripts/withdrawals.py` (E0, E1, E2a-c). E0 is itself a
quotation of Paper 2 v1's published text, and is checked against that source.
A notice that paraphrases, or a canonical text edited after the notice was
written, fails here.

Targets are read from the v2 branches with `git show`, so the lint checks what
is committed, not a working copy. `--worktree DIR` reads files from a checkout
instead (to lint before committing).

Run from repo root:  python scripts/lint_errata_notices.py
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = {
    "paper1": {"branch": "paper1-arxiv-v2",
               "files": ["paper1/intervention_timing_paper.tex"],
               "require": ["E0", "E1"]},
    "paper2": {"branch": "paper2-arxiv-v2",
               "files": ["paper2/main.tex", "paper2/sections/body.tex",
                         "paper2/sections/appendix.tex"],
               "require": ["E2a", "E2b", "E2c"]},
}


def canonical() -> dict:
    spec = importlib.util.spec_from_file_location("withdrawals", ROOT / "scripts" / "withdrawals.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    out = {}
    for e in wd.ERRATA:
        if "correction" in e:
            out[e["id"]] = e["correction"]
        for it in e.get("items", []):
            out[it["id"]] = it["correction"]
    return out


# The sources arXiv actually published, as tagged in this repository
# (paper1-v1-posted: arXiv e-print 2606.04296v1; paper2-v1-posted: 2606.19386v1).
POSTED = {
    "paper1": ("paper1-v1-posted", ["paper1/intervention_timing_paper.tex"]),
    "paper2": ("paper2-v1-posted", ["paper2/main.tex", "paper2/sections/body.tex",
                                    "paper2/sections/appendix.tex"]),
}
PUBLISHED_IN = {"E0": "paper1", "E1": "paper1", "E2a": "paper2", "E2b": "paper2", "E2c": "paper2"}


def posted_plain(paper: str) -> str:
    """A posted source as plain text, with the forms the record quotes in:
    citations of Paper 1 as [P1], and inline math as its Unicode."""
    tag, files = POSTED[paper]
    src = "\n".join(subprocess.run(["git", "show", f"{tag}:{f}"], cwd=ROOT, capture_output=True,
                                   text=True, encoding="utf-8", check=True).stdout for f in files)
    src = src.replace("~\\cite{P1}", " [P1]").replace("\\cite{P1}", "[P1]")
    src = src.replace("\\rho", "ρ").replace("\\Delta ", "Δ").replace("\\Delta", "Δ").replace("$", "")
    return norm_tex(src)


def published_checks() -> list:
    """Every 'published text' the record quotes, and E0's correction (itself a
    quotation of Paper 2), must appear in the posted source. Returns failures."""
    spec = importlib.util.spec_from_file_location("withdrawals", ROOT / "scripts" / "withdrawals.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    entries = []
    for e in wd.ERRATA:
        entries += [e] if "published_text" in e else []
        entries += e.get("items", [])
    texts = {p: posted_plain(p) for p in POSTED}
    bad = []
    for e in entries:
        for q in e["published_text"]:
            if norm_md(q["text"]) not in texts[PUBLISHED_IN[e["id"]]]:
                bad.append(f"{e['id']} published text ({q['where']}) not found in {POSTED[PUBLISHED_IN[e['id']]][0]}")
    e0 = next(e for e in entries if e["id"] == "E0")
    if norm_md(e0["correction"]) not in texts["paper2"]:
        bad.append("E0's correction is not Paper 2's posted text (paper2-v1-posted)")
    return bad


def norm_md(s: str) -> str:
    s = s.replace("**", "").replace("`", "")
    return " ".join(s.split())


def norm_tex(s: str) -> str:
    s = re.sub(r"(?<!\\)%[^\n]*", "", s)                       # comments
    for _ in range(4):                                         # unwrap markup
        s = re.sub(r"\\(texttt|emph|textbf|textit|mbox)\{([^{}]*)\}", r"\2", s)
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", '"').replace("''", '"').replace("`", "'")   # TeX quotes
    s = s.replace("\\,", " ").replace("~", " ")
    for a, b in (("\\%", "%"), ("\\_", "_"), ("\\&", "&"), ("\\#", "#")):
        s = s.replace(a, b)
    return " ".join(s.split())


def read_target(t: dict, worktree: Path | None) -> str:
    parts = []
    for f in t["files"]:
        if worktree:
            parts.append((worktree / f).read_text(encoding="utf-8"))
        else:
            r = subprocess.run(["git", "show", f"{t['branch']}:{f}"], cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                raise SystemExit(f"cannot read {t['branch']}:{f}: {r.stderr.strip()}")
            parts.append(r.stdout)
    return norm_tex("\n".join(parts))


def longest_prefix(needle: str, hay: str) -> int:
    lo, hi = 0, len(needle)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if needle[:mid] in hay:
            lo = mid
        else:
            hi = mid - 1
    return lo


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(TARGETS))
    ap.add_argument("--worktree", type=Path, help="read files from this checkout instead of the branch")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    canon = canonical()
    bad = 0
    failures = published_checks()
    for f in failures:
        print("FAIL  " + f)
    bad += len(failures)
    if not failures:
        print("ok    every quoted published text, and E0's correction, appears in the posted sources "
              "(paper1-v1-posted, paper2-v1-posted)")
    for name, t in TARGETS.items():
        if args.only and name != args.only:
            continue
        text = read_target(t, args.worktree)
        src = str(args.worktree) if args.worktree else t["branch"]
        for key in t["require"]:
            needle = norm_md(canon[key])
            if needle in text:
                print(f"ok    {name} ({src}): {key} quoted verbatim")
            else:
                bad += 1
                k = longest_prefix(needle, text)
                print(f"FAIL  {name} ({src}): {key} not verbatim; matches up to char {k} "
                      f"of {len(needle)}, diverges at: ...{needle[max(0, k - 30):k + 50]}...")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
