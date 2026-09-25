# TNNLS Submission — Supplementary Bundle Index

**Venue:** IEEE Transactions on Neural Networks and Learning Systems (TNNLS)
**Manuscript:** FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints
**Submitted:** pending (cover-letter USER ACTION placeholders to be filled)
**Freeze-marker commit:** Wave 343 + Wave 344 HEAD (`paper-A-final.{md,tex,pdf}` 14 pp., 2026-09-25; Wave 343 paper bibliography fix added BGV12 + Villani 2003 + RMSPreserving disposition)
**Final tag (to push):** `v3.0-tnnls-ready`

This README indexes every artifact that the manuscript sources a
headline number from. Reviewers re-verify each row by reading the
listed file with `cat`, `head`, or `python3 -c "import json; print(json.load(open(path)))"`
and check the SHA-256 listed in [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md).

The bundle is organised by **provenance role**: every entry states
which paper section, audit doc, or wave the file backs, what file
format it is, and the byte-addressable location. Reviewers
prioritise the **headline-evidence** and **verification-outputs** rows;
the **cross-doc** rows are the audit trail that justifies each
headline number.

---

## A. Headline evidence (per-cell SOURCE.md provenance)

Per-cell `SOURCE.md` files document the byte-stable chain from each
headline number back to the originating sweep run. Every cell listed
in [`docs/drafts/paper-A-final.tex`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.tex) Table II (R1–R6) has a
matching entry under [`docs/headline-evidence/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/headline-evidence).

| Cell | Domain | Path |
|---|---|---|
| R1 | LineageFlow HMMER (protein FM) | [`docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md) |
| R2 | Kanzi / FlowMol3 fg_dev (molecular FM) | [`docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md) |
| R3 | CIFAR-10 RF v2 (image RF, FID −44.17%) | [`docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md) |
| R4 | 2D Two Moons W₂ (−7.28%) | [`docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md) |
| R5 | 2D Eight Gaussians W₂ (−10.40%) | [`docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md) |
| R5c | MNIST FM FID (−15.01%) | [`docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md) |
| R6 | K6 foldability per-tier + scPerplexity | [`docs/headline-evidence/byte_reproducibility_evidence/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/byte_reproducibility_evidence/SOURCE.md) |
| (composite) | Composite axis byte-stable | [`docs/headline-evidence/composite_axis_byte_stable/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/composite_axis_byte_stable/SOURCE.md) |
| (NFE) | 2.5–10× NFE compression | [`docs/headline-evidence/nfe_speedup_2p5_to_10x/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/nfe_speedup_2p5_to_10x/SOURCE.md) |
| (Kanzi N=1000) | Kanzi N=1000 byte-reproducible | [`docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md) |
| (hub) | headline-evidence hub | [`docs/headline-evidence/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/headline-evidence/README.md) |

## B. Cross-doc audit trail (data provenance + restoration)

These audit docs establish the chain of custody for every headline
number; reviewers can trace each Table II/III cell back to its
originating wave.

| Wave | Doc | Role |
|---|---|---|
| 297 | [`docs/audit/wave297-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave297-final.md) + [`wave297-p1..p8`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) | Restored paper body (intro, framework, empirical) |
| 298 | [`docs/audit/wave298-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave298-final.md) + [`wave298-p1..p8`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/audit) | 7 genuinely-novel innovations catalogue |
| 306 | [`docs/audit/wave306-11-cell-alignment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave306-11-cell-alignment.md) + [`wave306-fix-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave306-fix-plan.md) | 11-cell alignment (R1–R6 + K1/K4/K5/K7) |
| 307 | [`docs/audit/wave307-data-archaeology.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave307-data-archaeology.md) + [`wave307-archaeology-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave307-archaeology-summary.md) | Data archaeology for all 11 cells |
| 309 | [`docs/audit/wave309-paper-a-restoration-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave309-paper-a-restoration-plan.md) | Restoration plan for paper-A cells |
| 310 | [`docs/audit/wave310-r6-tier-aware-upgrade.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave310-r6-tier-aware-upgrade.md) + [`wave310-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave310-restoration-execution.md) | R6 STRONG tier-aware upgrade + D2 restoration (R6 d_z +0.2235) |
| 311 | [`docs/audit/wave311-d1-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-d1-review.md) + [`wave311-path-a-lemma-1.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-path-a-lemma-1.md) + [`wave311-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave311-restoration-execution.md) | D+1 review + Path A Lemma 1 (protocol composition closure) |
| 322 | [`docs/audit/wave322-path-a-lemmas-2-3.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave322-path-a-lemmas-2-3.md) + [`wave322-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave322-restoration-execution.md) | Path A Lemma 2 (state-machine byte-determinism) + Lemma 3 (ledger tamper-evidence) — complete 3-lemma structure in §6 Framework Properties |
| 323 | [`docs/audit/wave323-d3-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave323-d3-review.md) + [`wave323-typeset-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave323-typeset-execution.md) | D+3 self-review + IEEEtran-journal typeset to TNNLS |
| 324 | [`docs/audit/wave324-d5-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/wave324-d5-review.md) | Final D+5 review (this Wave) — 9 CRITICAL fixes, ready-to-submit verdict |

## C. Verification outputs — headline numbers

These JSON / CSV files are the byte-addressable artifacts behind
every headline number in the paper. Reviewers re-verify by
inspecting the bytes:

### C.1 R-canonical

| Cell | File | Format |
|---|---|---|
| R2 Kanzi framework-wins | [`verification_outputs/wave218-p3-kanzi-framework-wins.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave218-p3-kanzi-framework-wins.json) | JSON (paired 4-arm) |
| R6 tier-aware (d_z +0.2235 anchor) | [`verification_outputs/wave233-p3-tier-aware-r6.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave233-p3-tier-aware-r6.json) | JSON (per-tier paired) |
| R6 tier-aware per-cell | [`verification_outputs/wave233-p3-tier-aware-r6.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave233-p3-tier-aware-r6.csv) | CSV |
| R6 tier-aware R2 + R6 alternate | [`verification_outputs/wave233-p3-tier-aware-r2.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave233-p3-tier-aware-r2.json) / [`.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave233-p3-tier-aware-r2.csv) | JSON/CSV |
| R5c MNIST FM N=1000 (smoke) | [`verification_outputs/wave191-p3-mnist-n1000.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave191-p3-mnist-n1000.json) | JSON |
| R5b n_rounds=1 framework-WINS | [`verification_outputs/wave247-p3-r5b-n1000-n1.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave247-p3-r5b-n1000-n1.json) / [`.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave247-p3-r5b-n1000-n1.csv) | JSON/CSV |

### C.2 Wave 280 P-sweep outputs (power + per-cell effect)

| P | Cell / axis | File |
|---|---|---|
| R1 (LineageFlow) | HMMER hit-rate | [`verification_outputs/wave280-p-r1/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-r1) |
| R3 (FlowMol3) | fg_dev direction | [`verification_outputs/wave280-p-r3/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-r3) |
| R5c (MNIST) | FID bootstrap | [`verification_outputs/wave280-p-r5c/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-r5c) |
| K1 | algorithm-primitive ablation | [`verification_outputs/wave280-p-k1/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-k1) |
| K4/K5 | tier/saturation tier | [`verification_outputs/wave280-p-k4k5/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-k4k5) |
| K7 (novelty pctid) | direction | [`verification_outputs/wave280-p-k7/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-k7) |
| CIFAR sweep | NFE50 head-to-head | [`verification_outputs/wave280-p-cifar/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/wave280-p-cifar) (cross-check) |

### C.3 Statistical methods (Wave 234 P2-P6 + Wave 295 follow-ups)

| Method | Path |
|---|---|
| TOST equivalence (16 cells) | [`verification_outputs/wave234-p2-tost.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p2-tost.csv) |
| Jonckheere-Terpstra ordered test | [`verification_outputs/wave234-p3-jonckheere.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p3-jonckheere.csv) |
| BF01 (Bayes factor for H0) | [`verification_outputs/wave234-p4-bf01.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p4-bf01.csv) |
| DerSimonian-Laird meta-analysis | [`verification_outputs/wave234-p5-meta-summary.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p5-meta-summary.json) (+ [`wave234-p5-meta-analysis.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p5-meta-analysis.csv)) |
| Non-inferiority test (R5b) | [`verification_outputs/wave234-p6-ni-test.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave234-p6-ni-test.csv) |
| Real 4-arm per-record (Wave 230 P2) | [`verification_outputs/wave230-p2-real-4arm-per-record.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave230-p2-real-4arm-per-record.csv) |

### C.4 Wave 235 top-4 high-leverage improvements

| P | Cell | File |
|---|---|---|
| P1 (R5b n_rounds=1) | CIFAR-10 RF structural elimination | [`verification_outputs/wave235-p1-r5b-fix.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.csv) / [`.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p1-r5b-fix.json) |
| P2 (R2 medium-effect) | Kanzi RMSD uplift | [`verification_outputs/wave235-p2-r2-uplift.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p2-r2-uplift.csv) / [`.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p2-r2-uplift.json) |
| P3 (R6 LARGE overall) | K6 foldability overall uplift | [`verification_outputs/wave235-p3-r6-uplift.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p3-r6-uplift.csv) / [`.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave235-p3-r6-uplift.json) |
| P4 (FlowMol3 3-seed) | direction diagnostic | [`verification_outputs/wave235-p4-flowmol3-seed{42,43,44}*.json`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs) (partial) |

### C.5 Wall-clock CUDA-graph capture (Wave 236 P2 / 238 P2)

| File | Description |
|---|---|
| [`verification_outputs/wave236-p2-cuda-graph-wall-clock.csv`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave236-p2-cuda-graph-wall-clock.csv) | 5-arm R5b wall-clock harness (matched-NFE=50, BATCH=64) |
| [`verification_outputs/wave236-p2-cuda-graph-wall-clock.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/wave236-p2-cuda-graph-wall-clock.json) | JSON mirror with overhead breakdown |

### C.6 R1 hits.tbl files (data provenance)

Per-seed HMMER `.tbl` files underlying the R1 LineageFlow headline.
Both files are byte-stable across the Wave 158 baseline + Wave 158
framework arm and the Wave 310 P1 tier-aware upgrade.

- [`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl)
- [`verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl)

### C.7 K7 (novelty pctid) direction files

Direction-consistency verification under the Wave 297 novelty
fraction axis. Reviewers can rerun the analysis script and confirm
direction:

- [`verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json)
- [`verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json)
- [`verification_outputs/novelty_pctid_w166_q3_2026/baseline/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/novelty_pctid_w166_q3_2026/baseline) (raw HMMER pctid output)
- [`verification_outputs/novelty_pctid_w166_q3_2026/framework/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/verification_outputs/novelty_pctid_w166_q3_2026/framework) (raw HMMER pctid output)

## D. Source code anchors

All framework code is in this repository (`flowa-multistep-reinference`),
SHA-pinned at the current HEAD (see `MANIFEST.md` for the exact
commit):

| Path | Role |
|---|---|
| [`adaptive_reflow/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/adaptive_reflow) | Framework core (theory, schedulers, adapters, framework glue) |
| [`adaptive_reflow/theory/paper_quantities.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/theory/paper_quantities.py) | Typed evaluators for $(A_g, B_g, C_g, e_\rho)$ (Theorem 1) |
| [`adaptive_reflow/framework/cuda_graph_capture.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/framework/cuda_graph_capture.py) | CUDA-graph velocity-field cache (Wall-clock fix Wave 236 P2) |
| [`adaptive_reflow/framework/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/adaptive_reflow/framework) | Schedulers (`CosineAnnealScheduler`, `CodimensionSheetScheduler`, `BoundedMergeOperator`, `EvidenceDrivenScheduler`) |
| [`adaptive_reflow/contracts.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/contracts.py) | Adapter Capability + Adapter Protocol contract surface (typed) |
| [`adaptive_reflow/profile_residual.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/profile_residual.py) | `AdapterCapabilities.profile_residual_fn` extension point |
| [`adaptive_reflow/stats/equivalence.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/adaptive_reflow/stats/equivalence.py) | TOST + JT + BF01 + meta + NI typed statistical functions |
| [`adaptive_reflow/adapters/`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/adaptive_reflow/adapters) | 12 vendored adapters (LineageFlow, Kanzi, FlowMol3, CFRF, MNIST FM, TwoDimFM, …) |
| [`tests/test_d4_regression_vectors.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tests/test_d4_regression_vectors.py) | D.4 30/30 byte-stable regression suite |
| [`tools/paper_metrics.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/paper_metrics.py) + [`paper_metrics_kanzi.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/paper_metrics_kanzi.py) + [`upstream_eval.py`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tools/upstream_eval.py) | Metric wrappers (PB 0.6.5 + Kanzi DAE + LineageFlow eval) |

## E. Lemmas (paper §6 Framework Properties)

Three self-contained proofs are inserted into §6 of the manuscript:

- **Lemma 1** (Path A, Wave 311) — Protocol composition closure: any
  pair of paper-quantity-driven schedulers composed via
  `BoundedMergeOperator` yields a closed protocol. Source:
  [`docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md)
  (`lem-1` block).
- **Lemma 2** (Path A, Wave 322) — State-machine byte-determinism:
  every `StateBundle` is byte-stable under `SolverStep` ∘
  `SchedulerStep` for any of the four FlowA schedulers. Source: same
  file (`lem-2` block).
- **Lemma 3** (Path A, Wave 322) — Ledger tamper-evidence: the hash-
  chained transition log detects any post-hoc edit outside the
  redaction envelope. Source: same file (`lem-3` block).

All three lemmas are proved in the manuscript §6 with explicit
proof sketches; the source markdown (above) carries the full proofs.

## F. Theorem 1 theory package (mathematical foundation)

- [`docs/theory/theorem-1-self-contained.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/theorem-1-self-contained.md) — main derivation
- [`docs/theory/theorem1_rate_bound.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/theorem1_rate_bound.md) — rate-bound corollary
- [`docs/theory/operating-regime.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/operating-regime.md) — operating-regime analysis
- [`docs/theory/DEVIATIONS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/theory/DEVIATIONS.md) — theorem-vs-implementation deviations

## Cross-references

- [`tnnls_submission/MANIFEST.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/MANIFEST.md) — package manifest with SHA-256 + size
- [`tnnls_submission/README.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/README.md) — ScholarOne upload instructions
- [`tnnls_submission/cover_letter.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/cover_letter.md) — cover letter (17 USER placeholders — see `FILL_GUIDE.md`)
- [`tnnls_submission/FILL_GUIDE.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/FILL_GUIDE.md) — fill-guide for cover-letter placeholders
- [`docs/drafts/paper-A-final.{tex,pdf}`](https://github.com/silverenternal/flowa-multistep-reinference/tree/main/docs/drafts) — 10-page IEEEtran-typeset manuscript (TNNLS-ready)
- [`docs/drafts/paper-A-final.aux`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.aux) / [`.log`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/drafts/paper-A-final.log) — typeset diagnostic logs (compile-clean)

## G. Review-reproducibility bundle (Wave 344 — single-archive package)

To make reviewer reproducibility a single-file transfer, this Wave
packaged the per-cell headline artifacts, the headline-evidence
SOURCE.md provenance, and the most consequential Wave 339 + Wave 343
audit docs into one archive:

**Archive:** [`tnnls_submission/supplementary_bundle.zip`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary_bundle.zip)
- **Size:** 148 MB (compressed)
- **SHA-256:** `d1b5ba24a55a9336e7b65cee7bea652482943932181ddfdd6a8d6a9e5c758f3e`
- **Self-extracting tarball not used**: zip preserves directory structure
  on Windows / macOS / Linux without PATH requirements

**Bundle contents** (40 files, 159 MB uncompressed):

| Subdirectory | Count | Contents |
|---|---|---|
| `headline_artifacts/` | 11 entries (8 files + 3 subdirs) | 6 headline artifacts copied verbatim from `verification_outputs/`: R2 `wave218-p3-kanzi-framework-wins.{json,csv}`, R5c `wave191-p3-mnist-n1000.json`, R6 `wave233-p3-tier-aware-r6.{json,csv}`, R5b `wave247-p3-r5b-n1000-n1/` (with `inception_feats_cache/`), R1 `lineageflow_hmmer_real_n1000_w158_q3_2026/` (`baseline_hits.tbl` + `framework_hits.tbl`), K7 `novelty_pctid_w166_q3_2026/` (`novelty_results.json` + `novelty_results_full.json` + baseline/framework `.m8` files) |
| `headline_evidence/` | 11 files | 10 per-cell `SOURCE.md` provenance files (R1, R2, R3, R4, R5, R5c, R6, Kanzi N=1000, composite axis, NFE 2.5–10×) + hub `README.md`, all dereferenced from the symlinks under `paper-data/headline-evidence/` so reviewers do not need to resolve any path outside the archive |
| `audit_docs/` | 3 files | `wave306-11-cell-alignment.md` (the 11-cell alignment audit), `wave339-b6-fixes.md` (Wave 339 final-polish upstream fix), `wave343-paper-fixes.md` (Wave 343 paper bibliography fix for BGV12 + Villani 2003) |
| `SHA256SUMS` | 1 file | sidecar with sorted SHA-256 (40 entries, excludes self) |

**Sidecar integrity file:** [`tnnls_submission/supplementary_bundle/SHA256SUMS`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/tnnls_submission/supplementary_bundle/SHA256SUMS) (40 lines, lowercase sorted, two-space separator, relative paths from archive root; format matches `paper-data/SHA256SUMS`). Reviewers re-verify with:

```bash
cd supplementary_bundle && sha256sum -c SHA256SUMS
```

The archive is rebuilt only at Wave boundaries; the ZIP SHA above is
the current freeze-state hash. Future edits to any in-bundle file
require regenerating the archive + sidecar + updating the SHA above
(per Wave 344 traceability convention).

**Why the bundle is additive** (per AGENTS.md §3 hard-guardrail #2 "no
destructive edits"): every file in the ZIP is a byte-copy of an
existing repo file; no source file is moved, renamed, or deleted. The
manifest above is the only new artifact.
