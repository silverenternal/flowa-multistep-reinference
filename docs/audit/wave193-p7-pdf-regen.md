# Wave 193 P7 — EAAI PDF regeneration audit

**Date**: 2026-09-18
**Source markdown**: `docs/paper-draft.md` (3441 lines, post-P5 cut)
**Converter**: `docs/build_pdf/md_to_tex_eaai.py` (Wave 192 P3, unchanged)
**Target**: elsarticle preprint, 3p, twocolumn, A4
**PDF binary**: `docs/build_pdf/paper-eaai.pdf` + mirrored to `docs/paper-eaai.pdf` and `eaai_submission/manuscript.pdf`

## Result

| Item | Value | Target | Status |
|------|-------|--------|--------|
| Page count | **56** | 35-40 | OUT OF RANGE |
| PDF size | 877,426 bytes | n/a | OK |
| Title on page 1 | yes | yes | PASS |
| Abstract on page 1 | yes | yes | PASS |
| Tables embedded (count) | 54 in `.tex` / 12 load-bearing + aux | all 12 | PASS |
| ASCII figures ≤45 chars | N/A (Figs 1-4 are PNG) | ≤45 | PASS (separate file `wave192-ascii-figures.md` already refitted in P6 to 45 chars max) |

## Page count vs target

PDF is **56 pages**, target is **35-40** (gap: 16-21 pages to cut). Per task
instruction, NO cuts were applied without P5/P6 approval — this audit only
identifies the offenders.

## Section page distribution (from `pdftotext` layout analysis)

| Section | Pages | Lines in tex | Notes |
|---------|-------|--------------|-------|
| Title + Abstract | 1 | — | Required |
| §1. Introduction | 3 | 40 | Within target |
| §2. Framework | 5 | 302 | Largest theoretical section; table-heavy |
| §3. Algorithm | 3 | 180 | Within target |
| §4. Experiments | 6 | 303 | Includes Tables 6-12 (load-bearing) |
| §Ablations | (in 18-24) | 126 | Per-component matrix |
| §5. Discussion | (in 18-24) | 289 | Surveys closest neighbours |
| §6. Conclusion | (in 25) | 39 | Within target |
| **§7. Tier 3 real-ckpt results** | **12** | **665** | **#1 offender** |
| §8. SOTA baseline comparison | 5 | 205 | Within target |
| §9. Discussion (camera-ready) | 2 | 66 | Within target |
| **§10.x Limitations (camera-ready)** | **12** | **304** | **#2 offender** |
| §11. Broader Impact | (in 43-56) | 8 | Within target |
| §12. Conclusion (camera-ready) | (in 43-56) | 20 | Within target |
| References | 2-3 | 110 | Required |

## Proposed cuts (NEEDS P5/P6 APPROVAL — not applied)

To reach 35-40 pages, ~16-21 pages must be removed. The §7 + §10.x combination
alone accounts for 24 pages (43% of total). Proposed ordering:

### Tier-1 cuts (highest impact, lowest risk)

1. **Move §10.4-§10.6 to supplementary** (4 pages saved)
   - §10.4 Known negative surface (95 lines, 57 in tex)
   - §10.5 Known limitations status (100 lines, 83 in tex)
   - §10.6 R1-R6 Metric Inventory (33 lines, 24 in tex)
   - These are administrative/inventory sections; the abstract already
     summarises the R-level status. Keep §10.7 (Limitations and Future Work)
     as the in-paper limitations section.

2. **Condense §7. Tier 3 real-ckpt results** (5-7 pages saved)
   - §7 is 665 lines / 12 pages — the single biggest section
   - Sub-claim Tables 13 + 14 + 15 are reference tables that could move to
     supplementary §S7 with a 1-paragraph summary in main text
   - Cut to 5-7 pages: keep headline composite-axis verdict, move per-model
     detail (Kanzi codebook trajectory, LineageFlow HMMER scan, FlowMol3
     chem-axis) to supplementary

### Tier-2 cuts (additional 4-6 pages saved)

3. **Move Table 14a/14b (external baselines comparison protocol) to supplementary**
   - These are tier-3 baseline comparisons with explicit
     `PARTIALLY POPULATED` flags per the §10.x tables inventory
   - The "where baselines win" / "headline positioning" prose can stay

4. **Condense §5. Discussion** (2-3 pages saved)
   - §5 is 289 lines / 7 pages; the survey-of-neighbours portion
     (5.1-5.4) is comprehensive and could be tightened
   - Per P6 (w6), §5.7 was already consolidated to 5 most load-bearing items;
     §5.1-5.4 are the remaining fat

### Tier-3 cuts (additional 3-4 pages saved, more controversial)

5. **Move Tier 3 supplementary sub-claims (7.5-7.7) to supplementary**
   - 7.5 FlowMol3 chemistry axis placeholder discussion
   - 7.6 Saturation problem documentation
   - 7.7 Composite-axis reframing notes
   - Keep only the §7.2 composite-axis verdict in main text

6. **Condense §2. Framework** (2-3 pages saved)
   - §2.8 BGV12 + V03 concrete form subsection (3 pages alone) could be
     condensed; the abstract already cites the theorems
   - §2.6-2.7 hyperparameter-free + FM-LCM interface redesign sections
     could be table-form

## Tables load-bearing check

All 12 numbered load-bearing tables embedded:
- Table 1 (8 adapters), Table 2 (8 ports), Table 3 (landscape),
  Table 4 (algorithm/input/output), Table 5 (5 paper-uplifts),
  Table 6 (two_moons), Table 7 (eight_gaussians),
  Table 8 (3 protocol generations), Table 9 (CIFAR-10 v4),
  Table 10 (R2 LineageFlow), Table 11 (R2 refactored),
  Table 12 (20-round two_moons)

Plus auxiliary tables: 13 (per-model verdict), 14 (external baseline
comparison), 15 (Tier 3 baseline comparison).

## Verification commands

```bash
# Re-run converter + compile (P7 deliverable)
python docs/build_pdf/md_to_tex_eaai.py
cd docs/build_pdf && pdflatex -interaction=nonstopmode paper-eaai.tex

# Verify page count
pdfinfo docs/build_pdf/paper-eaai.pdf | grep Pages
# -> 56 pages (target 35-40: OUT OF RANGE)

# Verify title + abstract on page 1
pdftotext -f 1 -l 1 docs/build_pdf/paper-eaai.pdf - | head -10
# -> "FlowA: A Typed-Contracts Framework for Flow-Matching Re-Inference"
#    "Abstract" followed by 13-line abstract block

# Verify Tables 1-12 embedded
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  grep -c "Table $i " docs/build_pdf/paper-eaai.tex
done
# -> all >= 1 occurrence
```

## Status: AWAITING P5/P6 APPROVAL for cuts

PDF saved (overwrite) to:
- `docs/paper-eaai.pdf`
- `eaai_submission/manuscript.pdf`

Per task constraint: do NOT make cuts without P5/P6 approval. The proposed
Tier-1 cuts (items 1-2 above) are the minimum-effort path to ≤40 pages
without losing load-bearing content. Recommend P5/P6 review of:
1. Whether moving §10.4-§10.6 to supplementary is acceptable (the R-level
   inventory is referenced from §1 abstract, but full table is in supp.)
2. Whether §7 sub-claim tables 13-15 can move to supplementary §S7
3. Whether §2.8 BGV12 concrete form can be condensed (vs supplementary
   backup derivation)
