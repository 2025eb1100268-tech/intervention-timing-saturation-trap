# Building the Paper 2 LaTeX project

## Status from the rendering pass

- **Structure validated** (no compiler was available in the authoring
  environment): all `\input` targets, all 5 `\includegraphics` figures, and
  all 11 `\cite` keys resolve; braces balance in every file; no undefined
  `\ref`. Verified by an automated lint during the rendering pass.
- **Not compiled to PDF here:** the environment has no `pdflatex`, `xelatex`,
  `lualatex`, or `tectonic`, and none was installable. Compile locally with the
  commands below.

## Compile

```bash
cd paper2
pdflatex main
bibtex   main
pdflatex main
pdflatex main
```
or simply `latexmk -pdf main.tex`.

## Before submission (2 required swaps)

1. **NeurIPS style file.** `neurips_2024.sty` here is a self-contained minimal
   stand-in (the official file is not redistributable). Replace it with the
   official `neurips_2024.sty` from the call-for-papers. The body uses only
   standard macros, so no body edits are needed; you may need to set the
   correct option (`[preprint]` vs `[final]`).
2. **`\cite{P1}-v2`.** The erratum is cited as `\cite{P1}` plus the literal
   text "-v2". Once the P1 v2 (erratum) arXiv version exists, either keep this
   or add a dedicated `@misc` entry for the v2.

## Estimated length

No compiled page count is available (no local TeX). Content estimate:
abstract 433 w + body 3755 w + related work 356 w + appendix 387 w
≈ 4930 words, 5 figures, 2 tables. At NeurIPS two-column density this is
approximately **8–9 pages** for the full version (≈6–7 pp main + figures/refs;
≈1.5 pp appendix). The 4-page workshop distillation noted in the draft would
keep Secs. 3–7 + Fig. 1–2 and move the rest to supplementary.

## Open author-verification items (do not submit without checking)

- `references.bib`: `plank2022` page numbers/DOI are flagged `[VERIFY]`
  (carried from P1, not re-verified this pass). All other entries were
  verified against arXiv / the publisher / Project Euclid during the
  rendering pass.
- The draft's `[CONFIRM]` marker (Sec. 6 design-timing disclosure) is resolved
  in the appendix provenance paragraph, **with a caveat**: the repo was never
  under git, so "git-timestamped" in Sec. 2 overstates the provenance. Soften
  to "timestamped" or place the repo under version control and cite the prereg
  commit hashes. See `RELEASE_CHECKLIST.md` and the rendering-pass report.
