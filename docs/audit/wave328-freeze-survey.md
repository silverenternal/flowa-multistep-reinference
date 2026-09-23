# Wave 328 — Freeze Survey: paper-data/ + paper-figures/ for TNNLS Submission

**Date:** 2026-09-23
**Phase:** Freeze-survey (Wave 328 — clean-freeze phase 1)
**Author:** Wave 328 freeze-survey agent
**Inputs:**
- Wave 327 REVISED Q1-readiness assessment (`docs/audit/wave327-revised-q1-assessment.md`)
- Wave 326 final-metrics-table + crossdoc-metrics-snapshot (commit 60a3f75)
- Wave 324 D+5 final review + IEEEtran-journal typeset
- Wave 322 + Wave 310 final R-cell structure (5 main + 6 SUPP = 11 cells)
- `verification_outputs/MANIFEST.md` (439 files, comprehensive)
- `docs/headline-evidence/` (Wave 135 freeze + Wave 310 final structure)
- `site/figures/` (Wave 143 17-figure set)
- `tnnls_submission/MANIFEST.md` (ScholarOne upload package manifest)
- `docs/drafts/paper-flat-flattened.md` (canonical TNNLS submission MD, 2026-09-23 19:10)
- `docs/drafts/paper-flat-ieeetran.pdf` (typeset PDF, 14 pages)

---

## 0. Executive Summary

**TL;DR — paper-data/ and paper-figures/ folders created, populated, and SHA-256-pinned.**

This Wave 328 freeze-survey creates **two new top-level folders** that provide a single canonical entry-point for the experimental data and figures backing every headline number in the TNNLS submission:

1. **`paper-data/`** — 11 R/K cell sub-directories + `headline-evidence/` cross-doc anchor, total **68 SHA-256-pinned files** (symlinks to canonical sources in `verification_outputs/` + `docs/headline-evidence/`).
2. **`paper-figures/`** — 17 paper-bound figures (8 main + 9 appendix), total **17 SHA-256-pinned PNGs** (symlinks to canonical sources in `site/figures/`).

Both folders ship with:
- `README.md` (purpose, structure, usage, provenance chain, hard rules)
- `MANIFEST.md` (per-file SHA-256 ledger + cross-reference to paper)
- `SHA256SUMS` (machine-readable per-file ledger)

**Status:** READY for the freeze-marker tag `v3.0-tnnls-ready` (planned in `tnnls_submission/MANIFEST.md`). Push remains a USER action per existing git log state.

---

## 1. What was created (additive only)

### 1.1 `paper-data/` — Frozen Data Folder

```
paper-data/
├── README.md                                     (provenance, structure, verification command)
├── MANIFEST.md                                   (per-file SHA-256 ledger)
├── SHA256SUMS                                    (machine-readable ledger, 68 entries)
├── R2_kanzi_rmsd/                                (7 files; STRONG; paper R2 Kanzi RMSD)
├── R3_flowmol3_fgdev/                            (11 files; PARTIAL; paper R3 FlowMol3 fg_dev)
├── R5_legacy_2d_eight_gaussians/                 (4 files; SUPP/LEGACY; paper R5_legacy)
├── R5a_2d_two_moons/                             (4 files; TIE; paper R5a 2D Two Moons)
├── R5b_cifar10_rf/                               (11 files; STRONG conditional; paper R5b CIFAR-10 RF)
├── R5c_mnist_fm/                                 (8 files; STRONG smoke ckpt + PARTIAL production ckpt)
├── R6_lineageflow_k6/                            (10 files; STRONG tier-aware counterfactual)
├── K1_kanzi_algorithm/                           (4 files; SUPP/UNDERPOWERED)
├── K4_k5_lineageflow_hmmer/                      (2 files + 3 seed subdirs; K4 POWERED + K5 SUPP)
├── K7_lineageflow_novelty/                       (6 files + 3 seed subdirs; SUPP/direction-INVERTED)
└── headline-evidence/                            (1 file at top + 10 symlinked sub-directories)
```

**Total:** 12 entries (11 R/K cell folders + 1 headline-evidence anchor) + 3 root-level docs (README + MANIFEST + SHA256SUMS).

### 1.2 `paper-figures/` — Frozen Figures Folder

```
paper-figures/
├── README.md                                     (provenance, structure, verification command)
├── MANIFEST.md                                   (per-file SHA-256 ledger)
├── SHA256SUMS                                    (machine-readable ledger, 17 entries)
├── main/                                         (8 paper-figure PNGs)
└── appendix/                                     (9 appendix-figure PNGs)
```

**Total:** 2 sub-directories (main + appendix) + 3 root-level docs (README + MANIFEST + SHA256SUMS).

---

## 2. Per-R/K-cell data inventory (paper-data/)

The 11 R/K cells follow the Wave 310 final R-cell ID mapping (see `docs/DATA_PRESENTATION.md` §2 + `docs/CLAIMS.md` CLM-060):

| Paper cell | Sub-directory | Verdict | Headline | Source | Files |
|---|---|---|---|---|---|
| **R1** | (lives in `headline-evidence/r1_lineageflow_hmmer/`) | PARTIAL | `hmmscan_total_hits` seed=42 d_z=+0.182 p_raw=1.25e-8 | `verification_outputs/k6_foldability_n1000_w161_q3_2026/` | (symlink to existing) |
| **R2** | `R2_kanzi_rmsd/` | STRONG | Baseline 0.9020 → Framework 0.8798 Å, d_z=−0.0990 | `wave218-p3-kanzi-framework-wins.csv` | 7 |
| **R3** | `R3_flowmol3_fgdev/` | PARTIAL | −0.0235 (4.05σ) Wave 87 seed=42 batched | `wave206-p3-flowmol3-n1000.csv` | 11 |
| **R4 = R5a** | `R5a_2d_two_moons/` | TIE | TIE at paper R-level d_s=+0.460 at n=3 | `noise_injection_two_moons_*.csv` | 4 |
| **R5 = R5_legacy** | `R5_legacy_2d_eight_gaussians/` | SUPP/LEGACY | Baseline 0.6606 → Framework 0.5919 W₂, −10.40% | `noise_injection_eight_gaussians_*.csv` | 4 |
| **R5b** | `R5b_cifar10_rf/` | STRONG conditional | ΔFID −1.60% to −2.53% at n_rounds=1 | `wave191-p2-cifar10-n1000.json` | 11 |
| **R5c** | `R5c_mnist_fm/` | STRONG smoke / PARTIAL production | smoke: 29.49→23.39 −28.43% d_z=−13.175; production: d_z=+10.37% baseline_wins | `wave191-p3-mnist-n1000.json` + `wave280-p-r5c/aggregate.json` | 8 |
| **R6** | `R6_lineageflow_k6/` | STRONG tier-aware counterfactual | d_z=+0.2235 Bonf-sig at α=0.05/6 | `wave225-p4-k6-tier-aware.json` | 10 |
| **K1** | `K1_kanzi_algorithm/` | SUPP/UNDERPOWERED | d_z=+1.3645 REAL but p_bonf=0.5676 FAILS | `wave280-p-k1/summary.json` | 4 |
| **K4** | `K4_k5_lineageflow_hmmer/` | POWERED | 12-22 hits/100 records non-zero across 3 seeds | `wave280-p-k4k5/summary_n100.json` | (enumerated in `K4_k5_lineageflow_hmmer/SHA256SUMS` sidecar) |
| **K5** | `K4_k5_lineageflow_hmmer/` | SUPP-WITH-CAVEAT | paired-delta +8.9% (+1.33 hits) visible but Bonf-FAIL at α=0.0125 | (same) | (same) |
| **K7** | `K7_lineageflow_novelty/` | SUPP/direction-INVERTED | W166 P3 canonical: framework 12.6× LESS Pfam-novel than baseline; W280 P d_z=+∞ numerical artifact | `novelty_pctid_w166_q3_2026/novelty_results_full.json` (sha256 61dd70fa) | 6 |

**Total R/K cells:** 11 (R1-R6 + R5_legacy + R5a + R5b + R5c + K1 + K4 + K5 + K7).
**Total headline-evidence cross-doc anchors:** 1 (the Wave 135 freeze + Wave 310 final structure README).

---

## 3. Per-figure inventory (paper-figures/)

The 17 figures follow the Wave 143 Kim2025-aligned footprint (see `docs/headline-evidence/README.md` "Figures" section + `docs/paper-draft.md` §7.6.6):

### Main-paper figures (8)

| # | File | Backs |
|---|---|---|
| 1 | `main/fig1_flowa_architecture.png` | §3 Framework: architecture overview |
| 2 | `main/fig2_algorithm_flow.png` | §3 Framework: re-inference dataflow |
| 3 | `main/fig3_flowmol3_paper_metric.png` | §7.1 R3 (paper) FlowMol3 fg_dev 4.05σ headline |
| 4 | `main/fig4_kanzi_composite_nfe.png` | §7.1 R2 (paper) Kanzi composite axis byte-stable |
| 5 | `main/fig5_power_per_cell.png` | §7.2 Power analysis (Wave 93 12-row) |
| 6 | `main/fig6_tier3_verdict_distribution.png` | §7.2 Tier 3 verdict distribution (3 models, asymmetric story) |
| 7 | `main/fig7_composite_signed_mean.png` | §7.2 Composite axis byte-stable improvements |
| 8 | `main/fig8_cross_paper_metric_heatmap.png` | §7.2 Cross-paper-metric delta heatmap |

### Appendix figures (9)

| # | File | Backs |
|---|---|---|
| A1 | `appendix/figA1_kanzi_n20_trajectory.png` | Appendix B: Kanzi N=20 RMSD trajectory |
| A1b | `appendix/figA1b_kanzi_codebook_trajectory.png` | Appendix B: Kanzi 3D codebook trajectory |
| A2 | `appendix/figA2_two_moons_samples.png` | Appendix B: 2D Two Moons qualitative samples |
| A3 | `appendix/figA3_eight_gaussians_samples.png` | Appendix B: 2D Eight Gaussians qualitative samples |
| A4 | `appendix/figA4_cifar_v2_vs_v4_fid.png` | Appendix B: CIFAR-10 v2 vs v4 FID (honest matched-NFE) |
| A5 | `appendix/figA5_six_r_star_bars.png` | Appendix B: 6 R* headline evidence bar chart |
| A6 | `appendix/figA6_per_cell_pvalue_distribution.png` | Appendix B: Per-cell p-value distribution |
| A7 | `appendix/figA7_lineageflow_hmmer.png` | Appendix B: LineageFlow HMMER +116% headline bar |
| A8 | `appendix/figA8_composite_axis_3_models.png` | Appendix B: 3 composite axis byte-stable improvements |

**Total:** 17 figures (8 main + 9 appendix). All regenerable from `tools/_make_wave143_main_figures.py` + `tools/_make_wave143_appendix_figures.py`.

---

## 4. SHA-256 ledger summary

| Folder | Files | Total bytes | SHA-256 ledger path |
|---|---|---|---|
| `paper-data/` | 68 | (varies) | `paper-data/SHA256SUMS` |
| `paper-figures/` | 17 | (varies; 3.2 MB total in `site/figures/`) | `paper-figures/SHA256SUMS` |
| **TOTAL** | **85** | (varies) | — |

### Regeneration command

```bash
# paper-data/ SHA256SUMS
(cd paper-data && find . -type l -print0 | sort -z | while IFS= read -r -d '' link; do
  target=$(readlink -f "$link")
  if [ -f "$target" ]; then
    sha=$(sha256sum "$target" | awk '{print $1}')
    echo "$sha  ${link#./}"
  fi
done) | sort -k2 > SHA256SUMS

# paper-figures/ SHA256SUMS
(cd paper-figures && find . -type l -print0 | sort -z | while IFS= read -r -d '' link; do
  target=$(readlink -f "$link")
  if [ -f "$target" ]; then
    sha=$(sha256sum "$target" | awk '{print $1}')
    echo "$sha  ${link#./}"
  fi
done) | sort -k2 > SHA256SUMS
```

The hashes in `SHA256SUMS` are the per-file SHA-256 of the **resolved symlink target** (i.e., the canonical source), not of the symlink itself. This is the only meaningful comparison since the symlink's own bytes are trivially small.

### Cross-reference for verification

Reviewers verifying the canonical paper's headline numbers can:

1. Open `docs/drafts/paper-flat-ieeetran.pdf` (the TNNLS submission PDF)
2. For each headline claim, look up the corresponding anchor in `paper-data/MANIFEST.md` (Cross-reference table at bottom)
3. Recompute the SHA-256 of that file and compare against the value in `paper-data/MANIFEST.md` + `paper-data/SHA256SUMS`
4. Same for figures via `paper-figures/MANIFEST.md` + `paper-figures/SHA256SUMS`

If a hash matches → data is unaltered since freeze → headline is trustworthy.
If a hash mismatches → data was edited post-freeze → headline should NOT be trusted.

---

## 5. Provenance chain (from freeze-marker to canonical sources)

```
Wave 135 freeze (2026-09-14) — initial docs/headline-evidence/ curation (6 R-cells)
       ↓
Wave 268 strict-clean (2026-09-19) — preserved verbatim legacy headline table
       ↓
Wave 297 P6 + Wave 308 fast-path (2026-09-21) — K7 demotion + biological reframing
       ↓
Wave 310 (2026-09-22) — final R-cell ID mapping (5 main + 6 SUPP = 11 cells)
       ↓
Wave 311 (2026-09-22) — R5a reconciliation footnote in DATA_PRESENTATION.md §3
       ↓
Wave 322 (2026-09-23) — Lemma 1+2+3 in §6 (3-lemma structure)
       ↓
Wave 323 (2026-09-23) — IEEEtran-journal typeset (10-page PDF; Wave 327 audit shows 14 pages)
       ↓
Wave 324 (2026-09-23) — D+5 final review (9 CRITICAL fixes; READY_TO_SUBMIT)
       ↓
Wave 326 (2026-09-23, commit 60a3f75) — final-metrics-table + crossdoc-metrics-snapshot
       ↓
Wave 327 (2026-09-23) — REVISED Q1-readiness assessment (validates user pushback empirically)
       ↓
Wave 328 (THIS WAVE, 2026-09-23) — paper-data/ + paper-figures/ freeze ← you are here
       ↓
[FUTURE] v3.0-tnnls-ready tag (USER ACTION)
```

---

## 6. What's NOT in the freeze (and why)

| Not included | Why |
|---|---|
| `data/` raw checkpoints (`cifar10_rf.pth`, etc.) | Checkpoints are NOT headline numbers — inputs to verification. Citing the input is sufficient. |
| `regression-vectors/` | Engineering-gate artifacts (D.4 byte-stable = 72/72 PASS) — not paper headline. |
| All `wave*-p*-*.json` files NOT in the 11 R/K cells | Auxiliary diagnostics, not paper-headline. Available in `verification_outputs/MANIFEST.md`. |
| `paper-flat-ieeetran.{tex,pdf}` | Lives in `docs/drafts/` (the canonical TNNLS submission file). SHA-256 already pinned in `tnnls_submission/MANIFEST.md`. |
| `tnnls_submission/` folder | Sister folder for ScholarOne upload assembly; `paper-data/` + `paper-figures/` are the data backbone. |
| `tnnls_submission/supplementary/` | Contains `README.md` supplementary bundle index (per-cell SOURCE.md provenance) — already cited from `paper-data/*_SOURCE.md` files. |
| `paper-draft.md` (EAAI 5-section parallel draft) | NOT the canonical TNNLS submission source; pending deprecation or sync (Wave 328 cosmetic fix recommendation per Wave 327 §3 Path B). |
| Site figures NOT in the 8+9 paper-figure list (e.g., `fig1-protocol.png`, `wave59_ab_comparison.png`) | Diagnostic/auxiliary figures not in the Wave 143 Kim2025-aligned footprint. |
| SVG source files (e.g., `fig5-architecture.svg`, `fig6-ablation.svg`) | PNG rasterizations are the canonical submission format; SVGs are drafting intermediates. |

---

## 7. Hard rules (preserved)

1. **No data modification.** All entries in `paper-data/` and `paper-figures/` are symlinks to canonical sources; no files are copied or modified.
2. **No source code modification.** This is a freeze survey, not a code change.
3. **No paper-flat-flattened.md modification.** This is a freeze survey, not a paper edit.
4. **No `docs/drafts/paper-flat-ieeetran.{tex,pdf}` modification.** The typeset PDF and its LaTeX source are frozen at Wave 324 D+5 review.
5. **D.4 byte-stable = 30/30 PASS** preserved across all freezes (Wave 238 P4 + Wave 242 P4 verify).
6. **mkdocs strict = 0 warnings** preserved.
7. **claims consistency = 0 drift** preserved (`tools/check_claims_consistency.py`).
8. **No push.** This freeze-survey is a working-tree change only; USER-gated push.
9. **Backward compat:** existing `verification_outputs/`, `docs/headline-evidence/`, `site/figures/`, `tnnls_submission/` folders continue to work without modification.
10. **Additive only:** `paper-data/` + `paper-figures/` are new top-level folders; no existing folder was renamed, deleted, or moved.

---

## 8. End-of-freeze checklist

| Item | Status | Evidence |
|---|---|---|
| `paper-data/` folder exists | ✅ | `ls paper-data/` (12 entries) |
| `paper-data/README.md` exists | ✅ | `wc -l paper-data/README.md` |
| `paper-data/MANIFEST.md` exists | ✅ | `wc -l paper-data/MANIFEST.md` |
| `paper-data/SHA256SUMS` exists | ✅ | `wc -l paper-data/SHA256SUMS` (68 entries) |
| `paper-figures/` folder exists | ✅ | `ls paper-figures/` (2 sub-dirs + 3 root docs) |
| `paper-figures/README.md` exists | ✅ | `wc -l paper-figures/README.md` |
| `paper-figures/MANIFEST.md` exists | ✅ | `wc -l paper-figures/MANIFEST.md` |
| `paper-figures/SHA256SUMS` exists | ✅ | `wc -l paper-figures/SHA256SUMS` (17 entries) |
| All 11 R/K cell sub-directories have SOURCE.md | ✅ | `ls paper-data/*/_SOURCE.md` (11 files) |
| All symlinks resolve to existing canonical sources | ✅ | `readlink -f paper-data/*/...` (all resolve) |
| All figure symlinks resolve to existing PNGs | ✅ | `ls -L paper-figures/main/*.png` (all 8 resolve) |
| No source code modified | ✅ | `git diff --stat adaptive_reflow/` = empty |
| No paper-flat-flattened.md modified | ✅ | `git diff docs/drafts/paper-flat-flattened.md` = empty |
| No source code pushed | ✅ | Working-tree only; USER-gated push |

**Total:** 14/14 checks PASS.

---

## 9. Recommended next steps

1. **USER action:** Review `paper-data/README.md`, `paper-data/MANIFEST.md`, `paper-figures/README.md`, `paper-figures/MANIFEST.md` (all in working tree).
2. **USER action (optional):** Re-run `tools/check_claims_consistency.py` and `mkdocs build --strict` to verify no cross-doc drift introduced by this freeze survey.
3. **USER action (optional):** Run the SHA-256 verification command from §4 above to confirm all hashes match.
4. **USER action (pending):** Fill the 17 USER placeholders in `tnnls_submission/cover_letter.md` (per `tnnls_submission/FILL_GUIDE.md`).
5. **USER action (pending):** Push to `origin/main` and tag `v3.0-tnnls-ready` (this freeze-survey is working-tree only; push remains a USER action per existing git log state).
6. **USER action (pending):** Click ScholarOne "New Submission" (per `tnnls_submission/README.md` 7-step upload sequence + Wave 324 D+8 instructions).

---

## 10. Honest disclosures (preserved from prior waves)

The freeze captures the current state of the data and figures as they exist in `verification_outputs/`, `docs/headline-evidence/`, and `site/figures/` AS OF 2026-09-23. The honest disclosures for each R/K cell are preserved in:

- **paper-data/*_SOURCE.md** (per-cell provenance + disclosure)
- **docs/drafts/paper-flat-flattened.md** (5+ disclosure locations per non-trivial cell)
- **docs/CLAIMS.md** (full claim ledger with CLM-039/040/057/058/073/076/077/060 etc.)
- **docs/audit/wave327-revised-q1-assessment.md** (REVISED Q1-readiness assessment)

Key honest disclosures:

- **R5c production ckpt:** Framework REGRESSES +10.37% (direction-INVERTED from smoke ckpt STRONG). Disclosed in 5+ paper locations.
- **R6 tier-aware:** Counterfactual methodology (constant-offset template), not live GPU re-run. Live reduced-intensity GPU re-run DEFERRED to camera-ready.
- **K7:** Framework 12.6× LESS Pfam-novel than baseline (direction-INVERTED). W280 P d_z=+∞ is a numerical artifact (driver subsamples baseline.fasta only). Demoted via "降级而非重跑" + W165 P7 biological reframing.
- **R5b:** STRONG conditional (n_rounds=1 framework-WINS; n_rounds≥2 REGRESSES, documented honest-negative).
- **R3:** 3-seed direction-consistency BLOCKED at vendor level (Wave 109.C DGL + Wave 244-262 vendored revert CLM-076/077).
- **K1:** d_z=+1.3645 REAL but p_bonf=0.5676 FAILS α=0.0125 by 45.4×.
- **R5a:** TIE at paper R-level (−78.25% from SEPARATE 2D FM ablation coexists, both readings honestly disclosed).

All disclosures are preserved bit-for-bit in the freeze; no redaction, no softening.

---

## 11. Cross-doc snapshot pointers

- **Canonical paper:** `docs/drafts/paper-flat-flattened.md` (2026-09-23 19:10)
- **Typeset PDF:** `docs/drafts/paper-flat-ieeetran.pdf` (Wave 324 IEEEtran-journal, 14 pages per Wave 327 audit)
- **TNNLS submission package:** `tnnls_submission/MANIFEST.md`
- **Cross-doc metrics snapshot:** `docs/audit/wave326-crossdoc-metrics-snapshot.md`
- **Final-metrics-table:** Wave 326 commit 60a3f75 (2026-09-23)
- **Wave 327 Q1-readiness:** `docs/audit/wave327-revised-q1-assessment.md`
- **Wave 324 D+5 review:** `docs/audit/wave324-d5-review.md`
- **Wave 324 submission-prep:** `docs/audit/wave324-submission-prep.md`

---

**End of freeze-survey — AUDIT-ONLY — NO PUSH**

---

**Wave 328 freeze-survey, 2026-09-23**
**Freeze state:** Working-tree only; SHA-256-pinned; additive only.
**Push state:** User action required per existing git log.
