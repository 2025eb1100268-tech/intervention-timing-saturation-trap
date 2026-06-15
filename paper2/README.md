# Bistable by Construction — Paper 2 release bundle

Everything needed to compile, edit, and release the paper. Self-contained;
no API keys, no local paths, no unfinalized human-annotation data (see
"Excluded" below). Leak-gate verified.

## Layout

```
paper/            LaTeX project — compile this
  main.tex          entry point
  sections/         body.tex, sec10_related_work.tex, appendix.tex
  references.bib    11 verified citations (one [VERIFY] flag inside)
  neurips_2024.sty  minimal stand-in — REPLACE with official NeurIPS .sty
  figures/          fig1..5 (PDF + PNG @300dpi) + the matplotlib source
  BUILD.md          compile commands, page estimate, pre-submission swaps
  paper2_draft.md   the original content-final markdown draft (reference)

prereg/           pre-registration documents + the dt audit (verbatim)
reports/          all empirical reports (TRANSITION_REPORT is redacted, below)
fig_data/         CSVs behind every figure
heart_instrument/ the hook logger, converter, agent runner, live monitor
scripts/          analysis scripts (transparency; the engine is NOT shipped)
tests/            self-contained unit tests (generality, transition, cooldown)
live_demo/        the runE live T3 demo (session + monitor log + meta, scrubbed)
```

## Compile the paper

```bash
cd paper
latexmk -pdf main.tex      # or: pdflatex main; bibtex main; pdflatex main; pdflatex main
```

No LaTeX was available where this bundle was produced, so it was **not compiled
here** — but it is structurally validated (all inputs, 5 figures, 11 citations
resolve; braces balanced; no undefined refs). See `paper/BUILD.md`.

## Two things to do before submission (from BUILD.md)

1. Replace `paper/neurips_2024.sty` with the official NeurIPS style file from
   the call-for-papers (the body uses only standard macros, so no edits needed).
2. `references.bib`: `plank2022` page numbers/DOI are flagged `[VERIFY]`.

## Engine code fixes (the engine itself is proprietary and not shipped)

The paper references two cosmetic fixes to `heart_core/engine.py`. They are
value-preserving and listed here for the record (apply them in your engine
copy, not in this bundle, which contains no engine source):

- `engine.py:153` and `engine.py:727`: change the stale `12-dim` docstrings to
  `18-dim` (the vector is 18-dimensional).
- `engine.py:279,313,336`: replace the hardcoded energy-cap literal `6.0` with
  a named `ENERGY_CAP = 6.0` constant referenced at all three sites.

## Redaction / exclusions (human-annotation data not finalized)

Per the author's instruction this round:
- `reports/TRANSITION_REPORT.md` has its annotator-overlap section **redacted**
  (a placeholder notes it returns in a later release).
- **Not included:** the three annotator label files, `human_labels.json`, and
  any IRR / kappa / consensus report. The paper's §9 timing-alignment result is
  text-only (cites P1's published numbers) and does not need the raw labels.
- **Not included:** the cloned third-party repos used by the live runs
  (sortedcontainers/toolz/more-itertools — not ours to redistribute). The
  bug-injection specs live in `heart_instrument/agent_runner.py`, so a reader
  can reproduce against fresh clones.

`RELEASE_CHECKLIST.md` (next to this README) has the full manifest and the
verification commands.
