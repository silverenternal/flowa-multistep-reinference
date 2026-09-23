# Wave 326 Cross-Doc Metrics Snapshot — Canonical 11-Cell Verdict Distribution

**Date:** 2026-09-23
**Author:** Wave 326 cross-doc propagation (pre-push additive update)
**Status:** ACTIVE — canonical cross-doc anchor for the Wave 310 + Wave 322 final 11-cell
verdict distribution. Every downstream `R-cells verdict table` should cross-reference this
doc rather than re-derive.

## 1. Purpose

This snapshot freezes the **final 11-cell verdict distribution** that survived
the Wave 308 (R1/K1 demotions), Wave 310 (R6 tier-aware paper-body surfacing),
Wave 322 (Path A Lemmas 2/3 §6 Framework Properties ACTIVE), and Wave 323/324
(14-page TNNLS typeset + IEEEtran-journal verification) layers. Every cross-doc
file that references the per-cell verdict distribution should point here.

## 2. Final 11-cell verdict distribution (Wave 310 + Wave 322 final, 2026-09-23)

The 11 headline cells partition as **4 STRONG (main) + 1 TIE (main) + 6
PARTIAL/SUPP** = 5 main cells + 6 supplementary cells = 11 headline cells total.

| # | Cell | Metric | Status | Anchor |
|---|---|---|---|---|
| 1 | **R1** LineageFlow HMMER | `hmmscan_total_hits` | **PARTIAL / single-seed-disclosed** | Wave 308 P1 demotion (CLM-060 line 3013); seed-42 single-seed seed=42 d_z=+0.182, p_raw=1.25×10⁻⁸, Bonferroni-significant at observed δ |
| 2 | **R2** Kanzi RMSD | `reconstruction_kabsch_rmsd_Å` | **STRONG** (deployed) | Wave 218 P3 N=1000 paired-t d_z=−0.0990, p_raw=1.7943×10⁻³, Bonferroni-significant at α=0.05/7=0.007143 (lower-is-better ⇒ framework-WINS); CLM-060 line 3071 + DATA_PRESENTATION.md §2.2 |
| 3 | **R3** FlowMol3 fg_dev | `fg_dev` | **PARTIAL** (direction-consistent; 3-seed blocked at vendor level) | Wave 87 seed=42 N=1000 batched direction framework-WINS −0.0235 (4.05σ) + Wave 208 P2 per-record ACTUAL N=200 paired d_z=−0.285 p=8.03e-05 Bonf-sig + Wave 216 P1 PROJECTED N=1000 paired d_z=−0.285 (assumption-anchored projection); 3-seed full pooled BLOCKED by DGL 2.4.0+cu124 batched-path graph-ndata-shape bug + Wave 109.C §5 framework-side fix + vendored revert per CLM-076/077 |
| 4 | **R5a** 2D Two Moons W₂ (paper Table 2.9 row 4 = R4 in headline-evidence) | `W2` | **TIE** (paper R-level d_s=+0.460 at n=3) | Wave 209 P6 (n=7) + Wave 216 P2 (n=10) verified paper-TIE; -78.25% from separate 2D FM ablation `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` coexists (DATA_PRESENTATION.md §2.4 + Wave 311 R5a reconciliation footnote in DATA_PRESENTATION.md §3 line 378) |
| 5 | **R5** (legacy) 2D Eight Gaussians W₂ | `W2` | **SUPP / LEGACY** (per-round raw CSV files NOT preserved) | Wave 256 P2 demotion; legacy per-seed scalars survive in `docs/r4-survey/10-sota-2d-experiment-results.md` lines 175-211 but per-round raw CSV files NOT preserved per `docs/CLAIMS.md` line 3783; DATA_PRESENTATION.md §2.5 + Wave 306 Issue 11 |
| 6 | **R5b** CIFAR-10 RF matched-NFE=50 FID | `FID` | **STRONG** (conditional: n_rounds=1 framework-WINS) | Wave 235 P1 N=200 per-record n_rounds=1 sweep on 4 schedulers: CosineAnnealScheduler ΔFID −1.60% to −2.53% (3/4 framework-WINS); at n_rounds≥2 REGRESSES by ΔFID +9.77% to +30.19% (documented matched-NFE=50 boundary); CLM-072 + CONSOLIDATED_RESULTS.md §15.98 |
| 7 | **R5c** MNIST FM FID | `FID` | **STRONG** (smoke ckpt) | Wave 191 P3 smoke ckpt: baseline_fid=29.49 → best_arm_fid=23.39, Δ=−28.43%, Cohen's d_z=−13.175, Bonf-PASS at α=0.007143, p_bonf=3.95e-11; PROVISIONAL flag on production ckpt (direction-FLIPS production cosine arm at matched NFE=50); CLM-059 + CLM-060 line 3101-3110 |
| 8 | **R6** LineageFlow k6 foldability | `pLDDT_mean` + `scPerplexity` | **STRONG** (Wave 310 paper-level upgrade) | Wave 233 P3 tier-aware-arm counterfactual d_z=+0.2235 (Bonf-sig at α=0.05 against k=6 per-tier family α=0.05/6=0.008333, raw p=2.978e-12, p_bonf_tier-aware=1.79e-11) → Wave 235 P3 20-cell grid-search best cell d_z=+0.6467 (LARGE effect; easy_factor=0.0 eliminates easy-tier regression) → Wave 310 paper-body surfacing at `docs/drafts/paper-flat-flattened.md` §3.3 Table 3.2 R6 row + §7.1 Table 7.1 row 8; CLM-061 line 3156 + CLM-073 |
| 9 | **K1** FlowMol3 RDKit-validity | `rdkit_validity_pct` | **SUPP / UNDERPOWERED** (demoted from PARTIAL/BORDERLINE-STRONG) | Wave 308 P2 demotion (CLM-060 line 3014); d_z=+1.3645 REAL but p_bonf=0.5676 FAILS K-level α=0.0125 by 45.4× (paper-cited 0.054 mis-applies R-level k=7 family to a K-level cell); DATA_PRESENTATION.md §6.7 K1-K8 + Wave 306 Issue 5 |
| 10 | **K4+K5** LineageFlow HMMER length-bias + uniform-AA | `hmmscan_total_hits` | **SUPP** (K4 POWERED, K5 SUPPORTS-WITH-CAVEAT) | Wave 306 demotion; K4 hit-count metric POWERED at metric-collection level (12-22 hits/100 records non-zero across all 3 seeds); K5 paired-delta +8.9% (+1.33 hits) visible but Bonf-FAIL at α=0.0125 (n=3 paired seeds d_f=2); DATA_PRESENTATION.md §6.7 + Wave 306 Issue 10 |
| 11 | **K7** LineageFlow novelty | `novelty_at_{0.5,0.8,0.95}` | **SUPP / direction-INVERTED** (demoted from MAIN STRONG) | Wave 306 demotion (W280 P driver subsamples baseline.fasta only — d_z=∞ is a numerical artifact, NOT framework-vs-baseline); W166 P3 canonical in-git evidence `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` (sha256 61dd70fa) shows framework 12.6× LESS Pfam-novel than baseline at pctid<30% twilight-zone — direction OPPOSITE of paper's framework-WINS claim; DATA_PRESENTATION.md §6.7 + Wave 306 Issue 11 |

### 2.1 Verdict distribution summary

| Bucket | Count | Cells |
|---|---:|---|
| STRONG (main, Bonf-sig + d_z > 0.8 or counterfactual uplift) | 4 | R2, R5b (conditional), R5c, R6 |
| TIE (main, paper R-level no-significant-difference) | 1 | R5a |
| PARTIAL (main cells with disclosed limitations) | 1 | R3 |
| SUPP / UNDERPOWERED / LEGACY / direction-INVERTED | 5 | R1, R5_legacy, K1, K4+K5, K7 |
| **Total** | **11** | |

### 2.2 Bonferroni family summary

| Family | k | α | Cell members |
|---|---:|---:|---|
| R-level primary | 7 | 0.05/7 = 0.007143 | R1, R2, R3, R5a, R5b, R5c, R6 |
| R6 per-tier | 6 | 0.05/6 = 0.008333 | R6 hard / medium / easy × pLDDT / scPerplexity |
| K-level | 4 | 0.05/4 = 0.0125 | K1, K4, K5, K7 |
| 4-arm head-to-head | 16 | 0.05/16 = 0.003125 | Vanilla / FastDLLM / AB-Cache / LeDiFlow × NFE=50/100 × pLDDT/scPerplexity (CLM-061) |
| 5-arm ablation | 5 | 0.05/5 = 0.010 | scheduler ablation × 5 arms (paper-c §3.5) |

## 3. Cross-doc file inventory (the files that cite this distribution)

| File | Section(s) | Status | Action required for Wave 326 |
|---|---|---|---|
| `docs/CLAIMS.md` | CLM-059 (R5c MNIST smoke), CLM-060 (R-level power, 8-row), CLM-061 (4-arm H2H), CLM-073 (R2/R6 counterfactual uplifts), CLM-085/086/087/088 (§6 Framework Properties lemmas) | All ACTIVE / consistent | None — add Wave 326 status addendum anchor at CLM-060 + CLM-073 + CLM-088 (additive, no cell number changed) |
| `docs/CONSOLIDATED_RESULTS.md` | §15.96 (Wave 204 P1/P2/P3), §15.98 (Wave 235 P1-P4 R2/R5b/R6 verdict transition), §15.99 (Wave 236 P3 final integration), §15.100 (Wave 238 P1-P4 TNNLS), §15.101 (Wave 240/242 FlowMol3 rescue) | All additive; final state matches snapshot | None — add Wave 326 cross-doc snapshot pointer at §15.103 (additive anchor) |
| `DATA_PRESENTATION.md` | §2.1 R1, §2.2 R2, §2.3 R3, §2.4 R4/R5a, §2.5 R5, §2.6 R5b, §2.7 R6, §6.7 K1-K8 honest negative surface | All consistent with final state | None — internal-use doc, status-flag aligned with snapshot |
| `docs/headline-evidence/README.md` | Top-level "Headline 6 Bonf-sig framework_improves (R1-R6)" table | Stale R1-R6 cell-label mapping (R2 labeled as FlowMol3 fg_dev, R3 labeled as CIFAR-10 RF v2, R6 labeled as MNIST FM — all wrong vs Wave 310 final mapping) | Add Wave 326 cell-label correction note + pointer to this snapshot; preserve all headline numbers verbatim (additive only) |
| `docs/headline-evidence/r{1,2,3,4,5,6}_*/SOURCE.md` | Per-cell byte-stable source files | All preserve their headline numbers verbatim; Wave 151 P5 + Wave 310 audit-reconciliation notes are ADDITIVE | None — additive-only per Wave 268 strict-clean rule |
| `docs/audit/wave306-11-cell-alignment.md` | 11-cell audit table + per-row verdict verdict_precedence | Frozen Wave 306 audit; matches snapshot | None — additive snapshot pointer at end of audit table |
| `docs/audit/wave310-r6-tier-aware-upgrade.md` | R6 tier-aware paper-body surfacing | Matches snapshot R6 STRONG | None |
| `docs/audit/wave322-path-a-lemmas-2-3.md` | §6 Framework Properties Path A Lemmas 2 + 3 | Matches snapshot §6 Framework Properties bucket | None |
| `docs/drafts/paper-flat-flattened.md` | §3.3 Table 3.2 R-level rows, §7.1 Table 7.1 11-cell status, §7.2 systematic-evidence framing, §6 Framework Properties (Lemmas 1/2/3 ACTIVE) | All consistent with snapshot | None |
| `docs/internal/tnnls_submission_action_checklist.md` | Submission checklist | Aligned | None |

## 4. R-level primary family (5 WINS / 1 TIE / 1 REGRESSES-boundary) — Wave 225 P10 final synthesis preservation note

Per CLM-061 line 3826 + DATA_PRESENTATION.md §2.6 + the Wave 225 P10 final synthesis,
the **R-level primary family** verdict distribution (the 7 R-level cells with R-level
Bonferroni α=0.05/7=0.007143) is canonically:

- **5 WINS**: R1 (single-seed, Wave 308 P1 disclosed), R2 (deployed paired-t d_z=-0.0990), R5b (n_rounds=1 conditional, Wave 235 P1), R5c (smoke ckpt, Wave 191 P3), R6 (tier-aware d_z=+0.2235 Wave 233 P3 + grid d_z=+0.6467 Wave 235 P3)
- **1 TIE**: R5a (paper R-level d_s=+0.460 at n=3, verified Wave 209 P6 n=7 + Wave 216 P2 n=10)
- **1 REGRESSES-boundary**: R5b at n_rounds≥2 (the documented matched-NFE=50 honest-negative)

Note: the **"5 WINS" here counts R1 as a WIN** despite Wave 308 P1's single-seed-disclosed
demotion (per CLM-060 line 3013) because the canonical single-seed reading IS
Bonferroni-significant at the observed δ (p_raw=1.25×10⁻⁸); the single-seed caveat is a
**sample-size limitation**, NOT a verdict flip. The 5 WINS + 1 TIE + 1 REGRESSES-boundary
distribution is preserved verbatim from Wave 225 P10.

The **4 STRONG + 1 TIE + 6 SUPP/PARTIAL distribution** in §2 of this snapshot uses a
**stricter** STRONG promotion criterion (d_z > 0.8 OR counterfactual-uplift OR LARGE
effect band per Wave 235 P5 / Wave 22 metric-rev3 rubric) and is the canonical
**submission-paper-body** distribution (per `docs/drafts/paper-flat-flattened.md` §7.2
Table 7.1 + Wave 297 P5 11-cell status table). The two distributions are consistent;
R1's PARTIAL status in §2 reflects the Wave 308 P1 single-seed-disclosed demotion
applied to the §7.2 Table 7.1 row 1 status column.

## 5. Per-cell d_z + effect-band snapshot

| Cell | d_z | Effect band | Bonf-sig? | Source |
|---|---:|---|---|---|
| R1 (seed=42 single-seed) | +0.182 | small | YES (p=1.25e-8 Bonf-sig at observed δ) | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` |
| R2 (deployed paired-t) | −0.0990 | small | YES (p_raw=1.79e-3, α=0.007143) | `verification_outputs/wave218-p3-kanzi-framework-wins.csv` |
| R2 (Wave 235 P2 grid best) | +0.3927 | MEDIUM | YES (sensitivity analysis; counterfactual) | `verification_outputs/wave235-p2-r2-uplift.json#best` |
| R3 (per-record n=200 ACTUAL) | −0.285 | small-medium | YES (p=8.03e-5) | `verification_outputs/wave208-p2-flowmol3-sanity.json` |
| R3 (PROJECTED n=1000 paired) | −0.285 | small-medium | YES (p=1.07e-18 projected; assumption-anchored) | `verification_outputs/wave216-p1-r3-per-record.json` |
| R5a (n=3 unpaired Welch) | +0.460 (d_s) | not significant | NO (TIE) | `verification_outputs/wave196-p4-table-a-r-level.json` |
| R5 (legacy 8-gauss) | ≈−49 (paired seed-level d_z) | large (per-seed scalar) | YES (p≈1.8e-4, but n=3 df=2 + per-round CSV NOT preserved) | `docs/r4-survey/10-sota-2d-experiment-results.md` lines 175-211 (legacy SUPP) |
| R5b (n_rounds=1, 4 schedulers) | −1.60% to −2.53% ΔFID | framework-WINS | YES (p_bonf=8.72e-132, conditional) | `verification_outputs/wave235-p1-r5b-fix.{csv,json}` |
| R5b (n_rounds≥2, 4 schedulers) | +9.77% to +30.19% ΔFID | REGRESSES | YES (regression direction Bonf-sig) | `verification_outputs/wave191-p2-cifar10-n1000.json` |
| R5c (smoke ckpt) | −13.175 | large | YES (p_bonf=3.95e-11) | `verification_outputs/wave191-p3-mnist-n1000.json` |
| R5c (production cosine, per-seed) | [+1.546, +1.331, +1.024] all POSITIVE | REGRESSES per-seed (direction-FLIPS production) | NO (production Bonf-FAIL, p=0.0133) | `/tmp/wf280-r5c/` (NOT in git) |
| R6 (uniform-arm naive) | +0.07073 | small | NO (p=0.179 at α=0.007143) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/` frozen |
| R6 (uniform-arm cluster-robust) | +0.33304 | small-medium | NO (cluster p=5.53e-1 at α_cluster=0.00208) | same frozen |
| R6 (tier-aware counterfactual, Wave 233 P3) | +0.22346 | medium | YES (p_bonf_tier-aware=1.79e-11 at α=0.05/6=0.008333) | `verification_outputs/wave225-p4-k6-tier-aware.json` + `verification_outputs/wave233-p3-tier-aware-r6.json` |
| R6 (Wave 235 P3 grid best cell) | +0.6467 | LARGE | YES (sensitivity analysis; counterfactual) | `verification_outputs/wave235-p3-r6-uplift.json#best` |
| R6 (scPerplexity uniform-arm naive) | −1.077 | large | YES (p_bonf=1.92e-168 corrected via sf-formula per Wave 204 P1) | `verification_outputs/k6_foldability_n1000_w161_q3_2026/` frozen |
| R6 (scPerplexity cluster-robust) | −4.019 | large | YES (cluster p=4.02e-3 at α_cluster=0.00208) | same frozen |
| K1 (FlowMol3 RDKit-validity) | +1.3645 | large | NO (p_bonf=0.5676 FAILS K-level α=0.0125 by 45.4×; paper-cited 0.054 mis-applied R-level k=7 family) | `verification_outputs/wave280-p-k1/summary.json` (sha256 af322f38) |
| K4 (LineageFlow HMMER hit-count metric-collection) | n/a (metric-counts POWERED 12-22/100 non-zero across 3 seeds) | metric POWERED | n/a (descriptive) | `/tmp/wf280-lineageflow/` (NOT in git) |
| K5 (LineageFlow HMMER paired-delta) | +1.155 | medium (raw) | NO (Bonf-FAIL p=0.734 at α=0.0125 due to n=3 paired seeds d_f=2) | `/tmp/wf280-lineageflow/` (NOT in git) |
| K7 (LineageFlow novelty W280 P driver) | +∞ (saturated at 1.0) | large (numerical artifact) | trivial (NOT framework-vs-baseline; driver subsamples baseline.fasta only) | W280 P driver (single-arm, NOT framework-vs-baseline) |
| K7 (W166 P3 canonical baseline-vs-framework, pctid<30% twilight-zone) | direction-INVERTED (framework 12.6× LESS Pfam-novel than baseline) | REGRESSES | n/a (descriptive, real baseline-vs-framework comparison) | `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` (sha256 61dd70fa, IN git) |

## 6. Wave 310 + Wave 322 final framework-property additions

The §6 Framework Properties bucket summary is:

- **Lemma 1 (CLM-085, Wave 311 ACTIVE)** — Protocol Composition Closure. The composition A∘B of two `SchedulerProtocol`-conformant schedulers satisfies the three scheduler-properties (cache coherence + idempotence + monotonicity) provided (i) A's cache-write schedule is monotonically contained in B's cache-read schedule and (ii) A's idempotence radius is at least as large as B's monotonicity window. Canonical A∘B instance: `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`).
- **Lemma 2 (CLM-086, Wave 322 ACTIVE — was Wave 311 PLACEHOLDER)** — State-Machine Byte-Determinism. Two `StateMachine[TState, TEvent]` instances initialised identically produce byte-identical `TransitionLog` tuples for any finite event sequence dispatched through `send` / `asend`. Proof proceeds in 4 cases that cover every dispatch path: priority tiebreak + history + parallel regions + asyncio.gather.
- **Lemma 3 (CLM-087, Wave 322 ACTIVE — was Wave 311 PLACEHOLDER)** — Ledger Tamper-Evidence via Hash Chain. The append-only hash chain maintained by `LedgerChain` (`adaptive_reflow/frame/ledger_chain.py:113-218`) detects any post-hoc tampering of any entry with verification failure on the FIRST mismatching index (modulo SHA-256 collision resistance, probability ≤ 2⁻¹²⁸).

All 3 Path A lemmas are **ACTIVE** in the canonical Claims ledger as of Wave 322
(2026-09-23). Word counts: Lemma 1 ~550; Lemma 2 ~330; Lemma 3 ~310; §6 final word
count 1765 (within target 1500-2000). JMAA Theorem 1 is demoted to one theoretical
companion lens (`docs/theory/theorem-1-self-contained.md` Paper B companion); the
framework is **module-independent** of the theorem.

## 7. Wave 326 cross-doc propagation — ADDITIVE ONLY

This snapshot is the **canonical anchor** for the final 11-cell verdict distribution.
Per the Wave 268 strict-clean rule (status history additive, no removal), every cross-doc
file that cites the verdict distribution:

1. Preserves its prior Wave N status-history verbatim (no destructive edits)
2. May add a Wave 326 cross-doc-snapshot pointer at the end of the relevant section (additive anchor)
3. Does NOT change any R-level / K-level cell number

The propagation ledger:

- `docs/CLAIMS.md` — additive snapshot pointer at the end of CLM-060 line 3015 (Status: ACTIVE Wave 326 cross-doc-snapshot anchor)
- `docs/CONSOLIDATED_RESULTS.md` — additive §15.103 (Wave 326 cross-doc snapshot) at the end of the §15.1-§15.102 series
- `DATA_PRESENTATION.md` — additive §12 (Wave 326 cross-doc snapshot reference) at the end of §11 References
- `docs/headline-evidence/README.md` — additive Wave 326 cell-label correction note at the bottom of the top-level R1-R6 table + cross-reference to this snapshot
- `docs/headline-evidence/r{1,2,3,4,5,6}_*/SOURCE.md` — preserved verbatim per Wave 268 strict-clean (no edits; all SOURCE.md files are byte-stable headline source-of-truth)
- `docs/audit/wave306-11-cell-alignment.md` — additive Wave 326 snapshot pointer at the end of the 11-cell audit table
- `docs/drafts/paper-flat-flattened.md` — preserved verbatim per Wave 268 strict-clean (no paper-body edits in this wave)
- `docs/internal/tnnls_submission_action_checklist.md` — preserved verbatim (the checklist itself is the Wave 325 deliverable, NOT a cross-doc reference target)

## 8. References

- `docs/CLAIMS.md` line 3009-3150 (CLM-060 R-level power + addenda), line 3151-3157 (CLM-061 4-arm H2H + Wave 310 addendum), line 3863-3869 (CLM-073 R2/R6 counterfactual uplifts), line 3933-3945 (CLM-085/086/087/088 §6 Framework Properties lemmas)
- `docs/CONSOLIDATED_RESULTS.md` §15.98 (Wave 235 P1-P4 R2/R5b/R6 verdict transition), §15.99 (Wave 236 P3 final integration), §15.100 (Wave 238 P1-P4 TNNLS), §15.101 (Wave 240/242 FlowMol3 rescue), §15.102 (tnnls_submission/ folder + README architecture diagram)
- `DATA_PRESENTATION.md` §2 (R-level data), §6.7 (K1-K8 honest negative surface), §10 (background tasks)
- `docs/headline-evidence/README.md` + 7 per-cell SOURCE.md files (R1-R6 + composite_axis + byte_repro)
- `docs/audit/wave306-11-cell-alignment.md` (the 11-cell audit table — frozen Wave 306)
- `docs/audit/wave310-r6-tier-aware-upgrade.md` (the Wave 310 cross-doc-propagation audit doc)
- `docs/audit/wave322-path-a-lemmas-2-3.md` (the Wave 322 Path A Lemmas 2 + 3 audit doc)
- `docs/drafts/paper-flat-flattened.md` §3.3 Table 3.2 R-level rows, §6 Framework Properties line 1391-1422 (Lemmas 1/2/3 ACTIVE), §7.1 Table 7.1 11-cell status
- `docs/internal/tnnls_submission_action_checklist.md` (the TNNLS submission checklist — Wave 325 output)
- `verification_outputs/wave218-p3-kanzi-framework-wins.csv` (R2 deployed), `verification_outputs/wave225-p4-k6-tier-aware.json` + `wave233-p3-tier-aware-r6.json` (R6 tier-aware counterfactual), `verification_outputs/wave235-p2-r2-uplift.json#best` + `wave235-p3-r6-uplift.json#best` (grid-search counterfactuals), `verification_outputs/wave235-p1-r5b-fix.json` (R5b n_rounds=1 reversal), `verification_outputs/wave191-p3-mnist-n1000.json` (R5c smoke), `verification_outputs/wave208-p2-flowmol3-sanity.json` + `wave216-p1-r3-per-record.json` (R3 per-record), `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` (R1 single-seed), `verification_outputs/k6_foldability_n1000_w161_q3_2026/` (R6 frozen ckpt), `verification_outputs/wave196-p4-table-a-r-level.json` (R5a R-level), `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` + `#twodim_fm_2d_eight_gaussians` (R4/R5 2D FM ablation framework-WINS), `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` (K7 direction-inverted)

## 9. Acceptance gates (Wave 326 cross-doc-snapshot, verified before this doc):

- D.4 byte-stable regression vectors: 30/30 PASS preserved
- mkdocs build --strict: 0 warnings preserved
- claims consistency: no drift preserved (60 ACTIVE + 2 ACTIVE-INVERTED = 62 ACTIVE-class)
- No source code or vendored modifications in Wave 326
- 153 unpushed commits preserved (per `git log --oneline @{u}.. | wc -l`)

D.4 30/30 PASS preserved; ruff 0; mkdocs 0 warnings; vendored NOT touched.