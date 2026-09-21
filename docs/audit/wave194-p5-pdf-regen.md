# Wave 194 P5 — EAAI PDF regeneration audit

**Date**: 2026-09-19
**Source markdown**: `docs/paper-draft.md` (post-Wave-194 P3, 1268 lines, 5-section MrFlow/EAAI template)
**Converter**: `docs/build_pdf/md_to_tex_eaai.py` (Wave 192 P3, unchanged)
**Target**: elsarticle preprint, 3p, twocolumn, A4
**PDF binary**: `docs/build_pdf/paper-eaai.pdf` + mirrored to `docs/paper-eaai.pdf` and `eaai_submission/manuscript.pdf`

## Result

| Item | Value | Target | Status |
|------|-------|--------|--------|
| Page count | **17** | ≤40 | **PASS** |
| Page range | 17 | 35-40 (ideal) | BELOW ideal (smaller post-Wave-194 P3 restructure) |
| PDF size | 505,017 bytes | n/a | OK |
| Title on page 1 | yes | yes | PASS |
| Abstract on page 1 | yes | yes | PASS |
| Tables embedded (count) | **13** in `.tex` | ≥12 | **PASS** |
| Figures rendered | **4** | 4-6 | **PASS** (added FIG 3 + FIG 4 to markdown) |
| Verbatim (ASCII) blocks | 3 | n/a | OK |

## Change vs prior build (Wave 193 P7)

Prior (pre-Wave-194) PDF: **56 pages / 877,426 bytes** (`docs/audit/wave193-p7-pdf-regen.md`).

Wave 194 P3 collapsed the paper-draft.md from 7,591 lines → 1,268 lines
to the MrFlow (Zheng et al. 2026, arXiv:2607.01642) 5-section template:
- **Removed §7 Tier 3 real-ckpt results (12 pp, 665 lines in tex)**
- **Removed §11 Broader Impact (2 pp)**
- **Removed §12 Conclusion-camera-ready (1 pp)**
- **Collapsed §5 Discussion (5 pp) → §5 Conclusion (1.6 pp)**
- **Trimmed §10.x Limitations (12 pp → 5 pp)**
- Net: -39 pages from 56 → 17.

The post-restructure paper is materially shorter; this is intentional
per Wave 194 P1-P3 alignment to the MrFlow / EAAI 5-section template.

## Page-count vs ideal (35-40 pages)

Current 17 pages is well below the 35-40 ideal range but well within
the ≤40 hard constraint. The Wave 193 P7 cuts (moving §7 detail to
supplementary, condensing §10.x) brought the page count into compliance
with the ≤40 target; reaching the 35-40 ideal would require either:
1. Re-inflating §4 with per-model Tier 3 detail (deferred to supplementary)
2. Adding a Broader Impact / Discussion section beyond MrFlow template

Neither is recommended — the MrFlow 5-section structure is the EAAI
template alignment per Wave 194 P2/P3.

## Tables load-bearing check

13 tables embedded in `.tex` (target ≥12): PASS.

The 13 embedded tables correspond to the load-bearing Tables 1-10 in
`docs/paper-draft.md` (4 typed Protocols, 8 named ports, 4 scheduler
families, 4 paper quantities, 5 adapters × 3 domains, R1-R6 headline
evidence, per-component ablation, n_rounds + NFE curve, hyperparameter
sensitivity, pLDDT + scPerplexity deltas) plus 3 auxiliary tables
within the experimental matrix.

## Figures embedded check

4 figures rendered (target 4-6): PASS.

- FIG 1: `docs/figures/fig1_flowa_architecture.png` — §1 Introduction (architecture of 4 Protocols)
- FIG 2: `docs/figures/fig2_algorithm_flow.png` — §3 Method (multi-round restart-blend pipeline)
- FIG 3: `docs/figures/fig3-selection-ratio.png` — §3.6 Theoretical grounding (selection_ratio BGV12/V03 witness)
- FIG 4: `docs/figures/fig4-cifar-fid.png` — §4.2 Main results (CIFAR-10 RF FID across NFE)

FIG 3 + FIG 4 were added to `docs/paper-draft.md` in this wave (P5)
to bring figure count from 2 → 4. Markdown insertions:

- After line 510 in §3.6 (selection_ratio derivation), added:
  ```
  <!-- FIG 3: docs/figures/fig3-selection-ratio.png -->
  **Figure 3**: empirical `selection_ratio` trajectory across NFE
  budgets on the 2D Two Moons and Eight Gaussians targets...
  ```
- After line 596 in §4.2 (R5 CIFAR-10 RF v2 row), added:
  ```
  <!-- FIG 4: docs/figures/fig4-cifar-fid.png -->
  **Figure 4**: CIFAR-10 RF FID across NFE budgets, baseline
  (single-pass Euler, matched NFE) vs FlowA re-inference loop...
  ```

## Verification commands

```bash
# Re-run converter
python3 docs/build_pdf/md_to_tex_eaai.py
# -> Wrote <repo_root>/docs/build_pdf/paper-eaai.tex (88591 chars)

# Compile
cd docs/build_pdf && pdflatex -interaction=nonstopmode paper-eaai.tex
cd docs/build_pdf && pdflatex -interaction=nonstopmode paper-eaai.tex
# -> Output written on paper-eaai.pdf (17 pages, 505017 bytes)

# Verify page count
pdfinfo docs/build_pdf/paper-eaai.pdf | grep Pages
# -> Pages: 17

# Verify tables/figures
grep -c '\\begin{table}' docs/build_pdf/paper-eaai.tex   # -> 13
grep -c '\\begin{figure}' docs/build_pdf/paper-eaai.tex  # -> 4
grep -E 'MISSING|SKIPPED' docs/build_pdf/paper-eaai.tex  # -> (empty)
```

## Outputs

PDF saved (overwrite) to:
- `docs/build_pdf/paper-eaai.pdf` (build artefact)
- `docs/paper-eaai.pdf` (main text)
- `eaai_submission/manuscript.pdf` (EAAI submission copy)

Auxiliary: `docs/build_pdf/paper-eaai.tex` (88,591 chars / 1,032 lines).