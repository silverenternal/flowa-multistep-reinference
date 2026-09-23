# paper-data/ — Frozen Data for TNNLS Submission

**Date:** 2026-09-23 (Wave 328 freeze)
**Purpose:** Provide a single canonical entry-point for the experimental data backing every headline number in `docs/drafts/paper-flat-flattened.md` (the canonical TNNLS submission file).
**Submission target:** IEEE TNNLS (per `docs/cover-letter-tnnls.md` + Wave 324 submission-prep doc)
**Canonical paper file:** `docs/drafts/paper-flat-flattened.md` + `docs/drafts/paper-flat-ieeetran.pdf`
**Source:** This folder is a curated, SHA-256-pinned subset of `verification_outputs/` + `docs/headline-evidence/` for the 11 R/K cells in the Wave 310 final verdict distribution.

---

## What this folder contains

**11 R/K cell sub-directories + `headline-evidence/` (cross-doc anchor)** — all symlinks to canonical sources. No files are copied; the SHA-256 ledger is in `MANIFEST.md` and per-subdirectory `*_SOURCE.md` files.

| Sub-directory | Paper cell | Verdict | Anchor |
|---|---|---|---|
| `R2_kanzi_rmsd/` | R2 Kanzi RMSD uplift | **STRONG** (deployed paired-t Bonf-sig at α=0.007143) | `wave218-p3-kanzi-framework-wins.csv` |
| `R5c_mnist_fm/` | R5c MNIST FM FID | **STRONG** (smoke ckpt) / **PARTIAL** (production ckpt direction-FLIPS +10.37%) | `wave280-p-r5c/aggregate.json` + `wave191-p3-mnist-n1000/` |
| `R6_lineageflow_k6/` | R6 LineageFlow k6 foldability | **STRONG** (tier-aware counterfactual d_z=+0.2235) | `k6_foldability_n1000_w161_q3_2026/` + `wave225-p4-k6-tier-aware.json` |
| `R5b_cifar10_rf/` | R5b CIFAR-10 RF v2 FID | **STRONG conditional** (n_rounds=1) / **REGRESSES** (n_rounds≥2) | `wave191-p2-cifar10-n1000/` + `wave235-p1-r5b-fix.{csv,json}` |
| `R5a_2d_two_moons/` | R5a 2D Two Moons W₂ | **TIE** at paper R-level (d_s=+0.460 at n=3); −78.25% from SEPARATE 2D FM ablation | `noise_injection_two_moons_*.{csv,png}` |
| `R3_flowmol3_fgdev/` | R3 FlowMol3 fg_dev | **PARTIAL** (single-seed 4.05σ; 3-seed BLOCKED at vendor level) | `wave206-p3-flowmol3-n1000.*` + `wave235-p4-flowmol3-3seed.*` |
| `R5_legacy_2d_eight_gaussians/` | R5_legacy 2D Eight Gaussians W₂ | **SUPP / LEGACY** (per-round raw CSVs NOT preserved) | `noise_injection_eight_gaussians_*.{csv,png}` |
| `K1_kanzi_algorithm/` | K1 Kanzi algorithm-primitive 5-arm | **SUPP / UNDERPOWERED** (p_bonf=0.5676 FAILS α=0.0125 by 45.4×) | `wave280-p-k1/` |
| `K4_k5_lineageflow_hmmer/` | K4 (length-bias) + K5 (uniform-AA) | **K4 POWERED + K5 SUPP-WITH-CAVEAT** | `wave280-p-k4k5/` |
| `K7_lineageflow_novelty/` | K7 LineageFlow novelty | **SUPP / direction-INVERTED** (W166 P3 canonical; W280 P numerical artifact) | `wave280-k7/` + `novelty_pctid_w166_q3_2026/` |
| `headline-evidence/` | Cross-doc anchor (Wave 135 freeze + Wave 310 final structure) | n/a (anchor only) | `docs/headline-evidence/` |

**Total sub-directories:** 11 R/K cell folders + 1 headline-evidence cross-doc anchor = **12 entries**.

---

## How to use this folder for reviewer verification

Every headline number in the canonical paper has at least one anchor in `paper-data/`. Reviewers can re-verify with:

```bash
# 1. Re-hash every file under paper-data/ + headline-evidence/ + verification_outputs/MANIFEST.md
(cd paper-data && find . -type f -not -name 'SHA256SUMS*' -print0 | sort -z | xargs -0 sha256sum) > /tmp/paper_data_recomputed.sha256

# 2. Compare against paper-data/MANIFEST.md tables
diff <(awk '/^## / {section=1; next} /^\| `verification_outputs/ {print $2, $4}' paper-data/MANIFEST.md | sort) \
     /tmp/paper_data_recomputed.sha256
```

The hashes must match. Any mismatch = artifact edited since this freeze = NOT trustworthy.

---

## What's NOT in this folder (and why)

| Not included | Why |
|---|---|
| `data/` (raw checkpoints: cifar10_rf.pth, etc.) | Checkpoints are NOT headline numbers — they're inputs to verification. Citing the input is sufficient. |
| `regression-vectors/` | Engineering-gate artifacts (D.4 byte-stable = 72/72 PASS) — not paper headline numbers. |
| All `wave*-p*-*.json` files not in the 11 R/K cells above | Auxiliary diagnostics, not paper-headline. Available in `verification_outputs/MANIFEST.md`. |
| `paper-flat-ieeetran.{tex,pdf}` | Lives in `docs/drafts/` (the canonical TNNLS submission file). |
| `tnnls_submission/` | Sister folder for ScholarOne upload assembly; this folder is the data backbone. |

---

## Provenance chain

1. **Wave 135 freeze** (2026-09-14) — initial `docs/headline-evidence/` curation with 6 R-cells (Wave 135 R-cell ID mapping, NOT paper R-cell IDs)
2. **Wave 310 final structure** — 5 main + 6 SUPP = 11 cells (Wave 310 final R-cell ID mapping); see `docs/DATA_PRESENTATION.md` §2 + `docs/CLAIMS.md` CLM-060
3. **Wave 322** — Lemma 1+2+3 in §6 (3-lemma structure)
4. **Wave 326** — final metrics table + crossdoc-metrics-snapshot
5. **Wave 327** — REVISED Q1-readiness assessment (this audit doc validates user pushback empirically)
6. **Wave 328** (this wave) — paper-data/ + paper-figures/ freeze

---

## Hard rules (preserved)

1. **No data modification.** All entries are symlinks to canonical sources; no files are copied or modified.
2. **No source code modification.** This is a freeze survey, not a code change.
3. **No paper-flat-flattened.md modification.** This is a data-freeze survey, not a paper-edit.
4. **D.4 byte-stable = 30/30 PASS** preserved across all freezes (Wave 238 P4 + Wave 242 P4 verify).
5. **mkdocs strict = 0 warnings** preserved.
6. **claims consistency = 0 drift** preserved.

---

## End-of-freeze-marker

After Wave 328 freeze is complete, the next-step git tag is `v3.0-tnnls-ready` (planned in `tnnls_submission/MANIFEST.md`). The freeze-marker commit is Wave 326 HEAD (60a3f75, 2026-09-23). Push remains a USER action per existing git log state.

---

**End of README**
