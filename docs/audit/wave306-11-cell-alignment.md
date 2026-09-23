# Wave 306 — 11-Cell Alignment Table

**Date:** 2026-09-23
**Source:** Wave 304 DeepSeek audit + Wave 305 day-0 risk package + Wave 306 fix plan
**Status:** READ-ONLY synthesis (no paper edits applied; all 24 destructive edits + 9 tmp migrations awaiting user authorization)

This document consolidates the 11 empirical cells (5 main + 6 supplementary) claimed in Paper A against the actual deployed data. It is the single source-of-truth for the paper-vs-data alignment state before any paper edits are applied.

---

## Alignment Table

| # | Cell | Metric | Scheduler | Position | N (paper) | N (actual) | d_z (paper) | d_z (actual) | p (paper) | p (actual) | p_bonf (paper) | p_bonf (actual) | α | Bonf Pass | Status | DS # | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **R1** | LineageFlow HMMER `hmmscan_total_hits` (LineageFlow protein FM, NFE=10 short-bias 30-150 AA) | CosineAnnealScheduler | MAIN (§7.1 row 1) | 1000 (per-record) | 3000 (3-seed) | **+9.2** (FABRICATED) | **+0.6926** (3-seed aggregate) / **+0.182** (seed=42 single-seed, Wave 158 P2) | 1.25e-08 (seed=42) | 0.3531 (3-seed) / 1.25e-08 (seed=42) | **0.001** (Wave 280 P "Fabricated") | **1.0** (3-seed k=7) | 0.007143 | **FAIL** | **PARTIAL/UNDERPOWERED** — 3-seed pool INVALID due to seed-43/44 framework-fallback rate=100% (per `/tmp/wf280-r1/seed{43,44}/fasta/manifest.json` framework_fallback_per_family_count=={PF00005.27: 250, PF00072.24: 250, PF00183.19: 250, PF02517.18: 250}); only seed=42 invoked real framework. Honest verdict: seed=42 single-seed Bonf-PASS but 3-seed pool fails. | **#1** | **CRITICAL** |
| 2 | **R2** | Kanzi `reconstruction_kabsch_rmsd_Å` (lower_is_better) | CosineAnnealScheduler | MAIN (§3.3 row + §7.1 row 2) | 1000 | 1000 (paired, Wave 218 P3 deployed) | **+3.532** (§3.3 — REGRESSION, one-sample t) / +0.096 (§7.1 — PARTIAL) | **−0.0990** (paired-t deployed; framework-WINS) | 0.0 (§3.3) / 0.018 (§7.1) | **1.79e-3** | 0.0 (§3.3) / 0.018 (§7.1) | **1.79e-3** | 0.007143 | **PASS (deployed)** / FAIL (Wave 206 P2 source) | **STRONG framework-WINS (deployed)** — paper carries TWO conflicting R2 entries: §3.3 line 319 says REGRESSION d_z=+3.532 (Wave 206 P2, one-sample-t, framework_source=W196_byte_stable_fallback); §7.1 line 641 says PARTIAL d_z=+0.096 (Wave 196 P3 paired). Deployed Wave 218 P3 paired-t has framework-WINS d_z=−0.0990 (sign convention: NEGATIVE=framework-WINS on lower_is_better). | **#1** | **CRITICAL** |
| 3 | **R3** | FlowMol3 `fg_dev` (cumulative REOS Glaxo+Dundee flag-rate L1 dev from QM9 training) | CosineAnnealScheduler | MAIN (§3.3 row + §7.1 row 3) | 1000 (paired, projected) | 999 baseline + 1000 framework unpaired + 200 paired ACTUAL | −0.285 | −0.285 (N=200 ACTUAL) | 0.014 (unpaired) / **1.07e-18 (PROJECTED, misleading)** | 8.03e-05 (N=200 ACTUAL) / 1.42e-2 (unpaired) | 0.028 | 0.0997 (k=7 naïve) | 0.007143 | PASS ACTUAL / FAIL UNPAIRED / **BLOCKED 3-seed** | **PARTIAL** — per-record ACTUAL N=200 paired is Bonf-PASS d_z=−0.285 p=8.03e-05; per-record PROJECTED N=1000 paired is projection from N=200 (NOT real measurement — needs caveat); unpaired 1-seed aggregate UNDERPOWERED p=0.014; 3-seed pooled-SD upgrade BLOCKED at vendor level (Wave 109.C DGL 2.4.0 incompat). 7/7 cross-wave direction-consistent at 1 seed. | **#2** | **HIGH** |
| 4 | **R5a** (paper) / **R4** (headline-evidence) | 2D Two Moons W2 | CosineAnnealScheduler (paper Table 2.9 row 4) / **PaperRatioAdaptiveScheduler** (actual Wave 189 P2 / CLM-055) | MAIN (§3.3 row + §2.9 row 4) | 1000 | 3 unpaired seeds | **−7.28%** (pre-cd70821 artifact) / +0.460 (current paper d_s) | **+0.271** (paired d_z actual) / +3.16% framework-WORSE | 0.604 | 0.685 (paired-t) | 0.604 | 0.685 | 0.007143 | **FAIL (TIE)** | **TIE (framework-WORSE +3.16%)** — paper correctly reports TIE; actual data shows framework WORSE on post-cd70821 reading (Wave 189 P2 baseline=0.0736 → framework=0.0759). Pre-cd70821 -7.28% headline was artifact of np.tanh vs ReLU activation mismatch bug (fixed by commit cd70821 2026-08-31). Cell-ID inconsistent: R4 in headline-evidence vs R5a in paper. | **#7** | **CRITICAL** |
| 5 | **R5** (legacy) | 2D Eight Gaussians W2 | CosineAnnealScheduler | MAIN §2.9 row 5 (NOT in §3.1 / §7.1) | 1000 (Wave 16 SOTA) | 3 unpaired seeds (canonical from `docs/r4-survey/10-sota-2d-experiment-results.md`) / **0 in git** (raw per-round CSVs lost per CLM-055 line 3783) | **−3.13** (legacy REMOVED in Wave 256 P2) | **−49.04** (paired seed-level d_z) | 0.0038 (legacy) | 1.8e-04 (paired seed-level) | 0.007143 | 0.007143 | 0.007143 | PASS | **STRONG (legacy, demote to SUPP)** — actual seed-level paired-t yields d_z≈−49 (mean_diff=−0.06873, sd_paired=0.001401, t=−84.88, df=2, p≈1.8e-04); paper no longer carries d_z but still cites −10.40% headline. Per-round raw CSV files NOT preserved; canonical data is per-seed scalars in `docs/r4-survey/10-sota-2d-experiment-results.md` lines 175-211. | **#8** | **MEDIUM** |
| 6 | **R5b** | CIFAR-10 RF matched-NFE=50 FID | CosineAnnealScheduler (n_rounds=1 primary; n_rounds=2,4 supplementary) | MAIN (§3.2 row + §7.1 row 5) | 1000 chunked (paper) | 200 paired per-record (Wave 235 P1) + 10 paired chunks (Wave 191 P2) | +2.700 (paper chunk-FID n_rounds=4) | **+4.368** (n_rounds=1, framework-WINS) / **+5.444** (n_rounds=2, REGRESSES) / **−4.368** framework-WINS at n_rounds=1 (signed) | 1.31e-5 (chunk-FID n_rounds=4) | 8.72e-132 (n_rounds=1) / <1e-149 (n_rounds=2) | 9.17e-5 (chunk-FID n_rounds=4) | 8.72e-132 (n_rounds=1) | 0.007143 | PASS n_rounds=1 / FAIL n_rounds≥2 | **CONDITIONAL** — n_rounds=1 framework-WINS by ΔFID −1.60% to −2.53% on 3/4 schedulers (Cosine/Codim/Evidence/FreeTraj); n_rounds≥2 framework-REGRESSES by ΔFID +9.77% to +30.19%; `--no-final-restart` falsifier at n_rounds=10 grows regression to +30.19% (falsifies DeepSeek no-final-restart hypothesis). Paper §3.1 reports ONLY regression side; n_rounds=1 WIN reversal needs disclosure. | **#6** | **CRITICAL** |
| 7 | **R5c** | MNIST FM NFE=50 FID | CosineAnnealScheduler | MAIN (§3.2 row + §7.1 row 6) | 1000 smoke / 1000 production | 1000 smoke (Wave 191 P3) / 600 production (3-seed × N=200) | **−13.175** (smoke) / direction-FLIPS production | **−13.175** (smoke) / per-seed production [+1.546, +1.331, +1.024] all POSITIVE = baseline_WINS | **1.32e-11** (smoke) | 1.32e-11 (smoke) / +10.37% production (framework REGRESSES) | **9.22e-11** (paper, INCORRECT — uses R-level k=7 multiplier) / 3.95e-11 (correct per-3-arm-count Bonf from JSON) | 3.95e-11 smoke / 0.0133 production FAIL | 0.007143 | PASS smoke / FAIL production (direction FLIPS) | **STRONG smoke-ckpt + PARTIAL production (direction-FLIPS)** — smoke ckpt evidence_driven arm: baseline_fid=29.49 → best_arm_fid=23.39, Δ=−28.43%, Cohen's d_z=−13.175, Bonf-PASS at α=0.007143; production ckpt cosine arm at matched NFE=50: per-seed d_z=[+1.546, +1.331, +1.024] all POSITIVE = framework REGRESSES +10.37%, per-seed best_arm_fid=13.67 > baseline_fid=11.99. 9.22e-11 figure uses R-level k=7 multiplier (INCORRECT; should be 3.95e-11 per-3-arm-count). Aggregate.py d_z vs smoke-ckpt=Infinity (script bug because all 3 production seeds produce identical best_arm_fid=13.666766). Production ckpt data NOT in git (`/tmp/wf280-r5c/` only). | **#1** | **CRITICAL** |
| 8 | **R6** | LineageFlow k6 foldability `pLDDT_mean` + `scPerplexity` | **TierAwareCodimensionSheetScheduler** wrapping CodimensionSheetScheduler (only paper-quantity-driven headline; **COUNTERFACTUAL** per Wave 225 P4 / Wave 233 P3) | MAIN (§7.1 row 7) | 1000 | 1000 (Wave 161 foldability.jsonl frozen) | +0.071 naive / +0.333 cluster / **+0.224 counterfactual** | +0.07073 naive / +0.33304 cluster / +0.22346 counterfactual | 2.55e-2 naive / 5.53e-1 cluster | 2.5536e-2 naive / 5.53e-1 cluster / 2.978e-12 counterfactual | 0.0255 (paper, INCORRECT — should be 0.179) / 2.08e-11 counterfactual | 0.179 R-level k=7 / 0.281 paper-level k=11 / 2.08e-11 counterfactual | 0.007143 R / 0.00208 cluster / 0.004545 paper | FAIL overall / PASS counterfactual | **PARTIAL** — counterfactual +0.224 lifts overall pLDDT to Bonf-sig; naive +0.071 d_z cluster p=0.553 UNDERPOWERED; hard-tier pLDDT d_z=+1.189 (cluster p=1.28e-2 marginally above strict α_cluster=0.00208); easy-tier pLDDT d_z=−0.998 REGRESSES; scPerplexity d_z=−1.077 naive / −4.019 cluster (cluster p=4.02e-3 sig at α_cluster=0.00208). Paper §7.4 line 671 says "10 of 11 cosine + 1 paper-quantity-driven (R6)" disclosure is accurate but does NOT add "counterfactual" qualifier. Paper Table 7.1 row 7 mis-labels as "Kanzi k6 foldability" — k6 foldability uses LineageFlowAdapter (Pfam k6 subset via OmegaFold+ESM-IF), NOT Kanzi. | **#0** | **HIGH** |
| 9 | **K1** | FlowMol3 RDKit-validity `rdkit_validity_pct` | CosineAnnealScheduler | MAIN (§7.1 row 8) → **SUPP** | 200 (3 seeds × N=200) | 200 | +1.36 | +1.3645 (paired, seed-level n=3 d_f=2) | 0.054 (paper, **WRONG**) / 0.1419 raw | **0.1419 raw / 0.5676 actual** | **0.054** (paper, NO math basis) | **0.5676** (k=4 K-level α=0.0125) | 0.0125 K / 0.007143 R (both FAIL) | **FAIL** | **PARTIAL/UNDERPOWERED** — p_bonf=0.5676 FAILS Bonferroni by 45.4× at K-level α=0.0125; per-seed CV=5.3% reproducibility STRONG; 3/3 direction-consistent K1>PB; d_z>0.8 PASS but p_bonf FAIL → SUPP per Wave 305 §6 line 150 D3 trim path. Paper mis-applies "R-level primary k=7 α=0.007143" family to a K-level cell. Data NOT in git (`/tmp/wf280-k1/` only). | **#3** | **CRITICAL** |
| 10 | **K4+K5** | LineageFlow HMMER length-bias + uniform-AA `hmmscan_total_hits` | CosineAnnealScheduler | MAIN (§7.1 row 9) → **SUPP** | 300 (3 seeds × N=100) | 3 paired seeds (n=3 d_f=2; 300 records useful at metric-collection only) | +1.15 | +1.155 (paired, seed-level d_z) | 0.734 | 0.734 (raw) | 0.734 | 0.734 | 0.0125 K / 0.007143 R / 0.004545 paper (all FAIL) | **FAIL** | **UNDERPOWERED** — K4 hit-count metric POWERED (12-22 hits/100 non-zero across all 3 seeds at metric-collection level); K5 paired-delta +8.9% (+1.33 hits) visible but Bonferroni-FAIL at all 3 pre-registered α thresholds; structural gap from n=3 paired seeds d_f=2. Wave 280 P §2.1 sample-size downgrade (N=500→N=100) undocumented in paper. Data NOT in git (`/tmp/wf280-lineageflow/` only). Abstract line 19/60 mis-labels metric as "K4 scPerplexity, K5 pLDDT" (those are R6's metrics on LineageFlow). | **#4** | **CRITICAL** |
| 11 | **K7** | LineageFlow novelty (per-record vs Pfam-A target DB at pctid twilight-zone 30%) | CosineAnnealScheduler | MAIN (§7.1 row 11) → **SUPP** | 1000 (paper §7 ¶1 line 630) | 900 (3 seeds × N=300 W280 P saturated) / **1000** (W166 P3 canonical baseline-vs-framework, IN git) | **+∞** (saturated at 1.0; W280 P driver subsamples baseline.fasta only, NO framework arm) | **+∞** (W280 P saturated) / W166 P3 baseline 466/1000=46.6% novel vs framework 37/1000=3.7% novel at pctid<30% (direction INVERTED) | **<1e-300** (W280 P, paired one-sample t vs 0.0) | **<1e-300** (W280 P, trivial) / **direction-INVERTED on W166 P3** (framework 12.6× LESS Pfam-novel than baseline at corrected Rost 1999 twilight-zone 30% threshold; framework produces +425 recognizable Pfam homologs, 963 vs 538) | <1e-300 (paper saturated) | N/A descriptive (W166 P3 is pctid metric, not paired-t) | 0.007143 R / 0.0125 K | PASS saturated (trivial, NOT framework-vs-baseline) | **PARTIAL/SUPP — direction-INVERTED** — W280 P d_z=∞ is a numerical artifact of single-arm driver (subsamples baseline.fasta only, paired one-sample t-test vs baseline=0.0, not framework-vs-baseline delta); only W166 P3 (`verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json`, sha256 `61dd70fa…`) has a real baseline-vs-framework comparison and it shows framework is **12.6× LESS** Pfam-novel than baseline (direction OPPOSITE of paper's STRONG claim). The `novelty_at_{0.5,0.8,0.95}` saturation = 1.0 across all 3 seeds × 300 records because target DB is small (200 sequences) and synthetic baseline fragments (~90 aa) cannot produce statistically significant alignments at strict e-value against full-length Pfam-A seeds (~178 aa) — methodological artifact per W165 P7. | **#2** | **CRITICAL** |

---

## Top 5 Critical Fixes (DATA INTEGRITY)

These must be resolved before camera-ready submission. Each represents an empirically-falsifiable claim that a careful reviewer or reproduction could overturn.

### Fix #1 — R2: Replace §3.3 line 319 with deployed Wave 218 P3 paired-t

**Priority:** CRITICAL (DeepSeek #1 — data integrity)
**Effort:** 15 min paper edits (3 sites: §3.3 line 319, §3.3 line 333, §7.1 line 641)

Paper §3.3 line 319 cites Wave 206 P2 (one-sample t-test, framework mean=1.5585 Å, REGRESSION, p=0.0, d_z=+3.532). The deployed Wave 218 P3 paired-t shows R2 framework-WINS at d_z=−0.0990, p=1.79e-3 (framework_source=W214-P2 byte-stable framework_inv_proj, sha256=971aa2d1…; baseline_source=W218-P3 paired, sha256=35343d1c…).

**Action:** Replace `+3.532 (one-sample t, REGRESSION)` → `−0.0990 (paired t, framework-WINS)` at §3.3 line 319 + line 333 + §7.1 line 641. Update status from PARTIAL → STRONG at §7.1 row 2.

### Fix #2 — R3: Add 'PROJECTED from N=200 ACTUAL' caveat at §7.1 row 3 line 642

**Priority:** HIGH (DeepSeek #2)
**Effort:** 10 min paper edits (1 site)

Paper §7.1 line 642 cell description says "N=1000 paired per-record" but actual data is 1-seed UNPAIRED per-arm aggregate (n=999 baseline + n=1000 framework) at the fg_dev granularity; per-record paired is only N=200 ACTUAL (Wave 208 P2, data-capped at 200 by tools/wave87_n1000_sweep.py:298) and PROJECTED N=1000 (NOT a real measurement — projection via t_N=t_actual*sqrt(N/n_actual) scaling).

**Action:** Add explicit "(PROJECTED from N=200 ACTUAL — not a real N=1000 paired sweep)" caveat to the p=1.07e-18 cell in Table 7.1. Clarify that fg_dev is per-arm aggregate UNPAIRED at 1 seed, NOT "N=1000 paired".

### Fix #3 — K1: Correct p_bonf from 0.054 → 0.5676 + demote to SUPP

**Priority:** CRITICAL (DeepSeek #3, #8, #9)
**Effort:** 2.5 hours (1h data migration + 30 min paper edits + 1h SUPP relocation)

Paper §7.1 line 647 + §7.4 line 717 + §7 line 748 cite p_bonf=0.054; actual computed value in `/tmp/wf280-k1/summary.json` (sha256=af322f38…, 4260 bytes) is p_bonf=0.5676. The 0.054 figure has no mathematical basis in either K-level k=4 (0.5676) or R-level k=7 (≈0.994) computation. Paper also mis-applies "R-level primary k=7 α=0.007143" family to a K-level cell (K-level k=4 α=0.0125 per Wave 22 metric-rev3).

**Action:**
1. Migrate `/tmp/wf280-k1/{summary.json, driver.py, run.log}` → `verification_outputs/wave280-p-k1/` + commit (DeepSeek #9).
2. Replace p_bonf=0.054 → 0.5676 at paper line 647 + line 717 + line 215 Table 2.9 + line 748 + docs/CLAIMS.md line 3012 + wave280-p-k1-sweep-result.md §0/§3.3/§3.4/§4/§6.
3. Demote K1 from §7.1 Table 7.1 row 8 → §10 supplementary (D3 trim path per Wave 305 §6 line 150; frees ~530 words).

### Fix #4 — K4+K5: Migrate data + fix abstract + demote to SUPP

**Priority:** CRITICAL (DeepSeek #4, #8, #9)
**Effort:** 3 hours (1h data migration + 1h paper edits + 1h SUPP narrative)

Paper Table 7.1 row 9 + abstract line 19/60 cite p_bonf=0.734 at "R-level primary k=7"; K4+K5 are K-level cells (K-level k=4 α=0.0125). Both interpretations yield FAIL since p_bonf=0.734>>α. Abstract line 19/60 also mis-assigns metrics: "K4 LineageFlow scPerplexity, K5 LineageFlow pLDDT" — actual data has K4 metric = `hmmscan_total_hits` (NOT scPerplexity), K5 metric = `hmmscan_total_hits` framework-vs-baseline delta (NOT pLDDT). scPerplexity and pLDDT are R6's metrics on LineageFlow, NOT K4/K5's metrics.

**Action:**
1. Migrate `/tmp/wf280-lineageflow/{summary_n100.json, seed{42,43,44}/{fasta,hmmscan_n100}/*}` → `verification_outputs/wave280-p-k4k5/` + SHA-256 sidecars + commit.
2. Fix abstract line 19 + line 60: "K4 LineageFlow HMMER length-bias (hmmscan_total_hits), K5 LineageFlow HMMER framework-vs-baseline delta".
3. Demote K4+K5 from MAIN §7.1 row 9 → SUPP (replace with one paragraph disclosing n=3 paired seeds d_f=2 structural gap; K4 hit-counts powered; K5 paired-delta +8.9% visible but Bonf-FAIL).
4. Disambiguate cell-ID: rename lumped "K4+K5" → "K4 (hit-count powered) + K5 (paired-delta FAIL)".

### Fix #5 — K7: Demote from MAIN STRONG → SUPP with W166 P3 direction-inverted evidence

**Priority:** CRITICAL (DeepSeek #2 — strongest direction-inversion in the inconsistency list)
**Effort:** 1.5 hours (1h paper edits + 30 min audit doc revision)

Paper §7.1 line 650 + §7 line 718 + §7.2 line 743 + §7 line 652 list K7 as one of 3 STRONG cells with "d_z=+∞ saturated at 1.0, Bonferroni p<1e-300 on CosineAnnealScheduler". This is a numerical artifact: W280 P driver subsamples ONLY `data/lineageflow_n1000/baseline.fasta` (no framework arm) and runs paired one-sample t-test against baseline=0.0 (NOT framework-vs-baseline delta). The only real baseline-vs-framework novelty comparison is W166 P3 (`verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json`, sha256=61dd70fa…, IN git) which shows baseline 466/1000=46.6% novel vs framework 37/1000=3.7% novel at pctid<30% twilight-zone — direction **OPPOSITE** of paper's framework-WINS claim (framework is 12.6× LESS Pfam-novel than baseline, because framework sequences recapitulate Pfam family structure at >=30% identity per W165 P7 zinc-finger/DNA-binding discovery).

**Action:**
1. Replace paper §7.1 line 650 cell description with W166 P3 direction-corrected evidence: "baseline 466/1000=46.6% novel vs framework 37/1000=3.7% novel; +42.9 pp delta favoring baseline; framework LESS Pfam-novel by 12.6× (W165 P7 zinc-finger/DNA-binding finding)".
2. Remove "K7" from §7 line 652 "5 STRONG cells" roster + §7 line 743 "STRONG cells: 3 (R1, R5c, K7)" → "STRONG cells: 2 (R5c smoke ckpt only; K7 demoted per Wave 306 Issue 5 direction-inversion)".
3. Remove §7 line 718 "K7 STRONG — novelty saturated at 1.0" bullet.
4. Move K7 from MAIN §7.1 → SUPP behind aggregate-counterfactual framing.

---

## Counts

**Cross-cell new issues identified (NEW-1 through NEW-16 in Wave 306 fix plan §newIssuesFound):**

| Severity | Count | Issues |
|----------|-------|--------|
| **CRITICAL** | **4** | NEW-1 (R2 §3.3 REGRESSION vs deployed), NEW-2 (R1 d_z=+9.2 fabricated), NEW-3 (R5c production-ckpt direction FLIPS), NEW-4 (R3 "N=1000 paired" misleading) |
| **HIGH** | **5** | NEW-5 (R6 TierAware "counterfactual" qualifier), NEW-6 (R6 cluster p=0.553 UNDERPOWERED), NEW-7 ("5 STRONG cells" overcounts by 2), NEW-8 (K1 internal 0.054 inconsistency), NEW-9 (R5c aggregate.py d_z=Infinity script bug) |
| **MEDIUM** | **5** | NEW-10 (K4 "3-seed × N=100" framing misleading), NEW-11 (K4 N=500→N=100 downgrade undocumented), NEW-12 (R6 "Kanzi k6 foldability" mislabeled), NEW-13 (K7 driver subsamples baseline.fasta only), NEW-14 (R5b chunk-FID vs per-record-L2 design not comparable) |
| **LOW** | **2** | NEW-15 (paper-profile.md α=0.0083 typo), NEW-16 (K-cell R-level vs K-level family ambiguity) |
| **TOTAL** | **16** | |

**Per-cell prioritization (by cellId / priority from fixPlan.cellAudits):**

| Severity | Cells | Count |
|----------|-------|-------|
| **CRITICAL** | R1, R2, R5a, R5b, R5c, K1, K4+K5, K7 | **8** |
| **HIGH** | R3, R6 | **2** |
| **MEDIUM** | R5 (legacy) | **1** |
| **LOW** | — | **0** |
| **TOTAL** | | **11** |

**Total per-cell fixes proposed (from fixPlan.fixes): 24 entries** (22 destructive requiring user auth + 2 neutral cross-doc naming).

**Total /tmp/ data migrations proposed (from fixPlan.tmpMoves): 9 entries** (all requiring user auth):
- `wf280-k1` → `verification_outputs/wave280-p-k1/` (K1 summary.json+driver.py+run.log; 19 KB)
- `wf280-lineageflow` → `verification_outputs/wave280-p-k4k5/` (K4+K5 + per-seed fastas/hmmscan_n100; ~30 KB + per-seed fasta/hmmscan artefacts)
- `wf280-k7` → `verification_outputs/wave280-p-k7/` (K7 summary+per-seed novelty.json+novelty_per_seq.jsonl; ~125 KB)
- `wf280-r1` → `verification_outputs/wave280-p-r1/` (R1 summary.json + seed{42,43,44}/{eval,fasta}/{framework,baseline}/*; ~3 MB)
- `wf280-r5c` → `verification_outputs/wave280-p-r5c/` (R5c production-ckpt aggregate.json+seed{42,43,44}/{sweep_summary.json,*_samples.npz}; ~3 MB)
- `wf280-r6` → `verification_outputs/wave280-p-r6/` (R6 sweep_summary.json+seed{42,43,44}/sweep_summary.json; ~17 KB)
- `wf286-cifar` → `verification_outputs/wave286-r5b-boundary/` (R5b 5-scheduler × 3-seed + aggregate.json+all_cells.csv; ~200 MB)
- `wf296-p7-fid-compare` → `verification_outputs/wave296-p7-r5b-byte-stable/` (R5b byte-stable FID compare; ~2 KB)
- `wf302-p5-ablation` → `verification_outputs/wave302-p5-ablation/` (5-arm ablation supplementary; ~5 MB)

**Total /tmp/ data volume to migrate:** ~210 MB across 9 directories.

---

## /tmp/ Data Inventory Summary (from Wave 304 audit)

| Category | Count | Total Size |
|----------|-------|-----------|
| CRITICAL (data lost or in /tmp/ only, blocks reproducibility) | 4 | K1 (19 KB) + R3 stubs (1.4 KB, not real data) |
| HIGH (in /tmp/ only, supplementary paper cells) | 12 | K7 + R5b + R5c + R6 (~210 MB) |
| LOW (smoke/test/superseded/exploratory, IGNORE) | ~50 | wf289-smoke, wf290, wf290_p2, wf291-p5-3seed, wf291-codim-lever, wf289-codim-lever.stale-bottleneck, wf280-test, wf281-smoke, wf302-test, wf274-paper, etc. |
| **MOVE total** | **~50 files / ~30 GB** (most are R5b npz samples at ~12 MB each) | |

**Overall reproducibility verdict:** PARTIAL — K4 raw data exists in `/tmp/wf280-lineageflow/` and CAN be migrated; K1 raw data exists in `/tmp/wf280-k1/` and CAN be migrated; R5b raw data is large but exists in `/tmp/wf286-cifar/` and CAN be migrated. The audit's "K4 DATA LOST" reading was over-stated — the data IS in `/tmp/` and migration is non-destructive.

---

## Awaiting User Decisions

1. **Authorize 22 destructive paper edits** (R2 §3.3 line 319, R2 §3.3 line 333, R2 §7.1 line 641, R3 §7.1 row 3, K1 §7.1 row 8 + §7.4 line 717 + Table 2.9 line 215 + §7 line 748, K1 wave280-p-k1-sweep-result.md §0 + §3.3 + §3.4 + §4 + §6, K4+K5 §7.1 row 9 + abstract line 19 + line 60 + CLAIMS.md line 3012, K7 §7.1 row 11 + §7.9 line 718 + §7.2 line 743 + §7.2 line 652 + CLAIMS.md line 3012, R5b §3.2 row + §7.1 row 5 + §3.6 + §3.3, R6 §7.1 row 7 + CLAIMS.md line 3040) + **2 neutral naming fixes** (headline-evidence/README.md line 20 + headline-evidence/R4→R5a rename).

2. **Authorize 9 /tmp/ data migrations** to `verification_outputs/` + commits. Total ~210 MB / ~50 files.

3. **R5a cell-ID unification:** Keep "R5a" in paper Table 3.2 line 321 + Table 2.9 line 209 + update `docs/headline-evidence/README.md` line 20 + `docs/headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md` to use "R5a" (or vice-versa).

4. **R5a scheduler correction:** Table 2.9 row 4 line 209 lists "CosineAnnealScheduler"; actual Wave 189 P2 / CLM-055 data uses PaperRatioAdaptiveScheduler. Update Table 2.9 to "PaperRatioAdaptiveScheduler" OR re-run R5a with CosineAnnealScheduler to validate.

5. **R6 §7.4 line 671 disclosure:** Add "(Wave 225 P4 counterfactual construction; Wave 161 frozen foldability.jsonl + Wave 225 P4 / Wave 233 P3 REDUCED_INTENSITY_FACTOR=0.5 per-record diff shift per Wave 209 P1 A3 methodology — NOT a live GPU run)" qualifier to "TierAwareCodimensionSheetScheduler wrapping CodimensionSheetScheduler".

6. **R6 §7.1 row 7 label:** Replace "Kanzi k6 foldability" → "LineageFlow k6 foldability (Pfam k6 subset via OmegaFold+ESM-IF per Wave 161 frozen foldability.jsonl)".

7. **R5b §3.2 conditional disclosure:** Replace single-cell REGRESSES row with conditional table (n_rounds=1 WINS 3/4 schedulers ΔFID −1.60% to −2.53%; n_rounds≥2 REGRESSES ΔFID +9.77% to +30.19%; --no-final-restart falsifier n_rounds=10 +30.19%).

8. **K-cell Bonferroni family:** Re-classify K1/K4/K5/K7 from "R-level primary k=7 α=0.007143" (paper current) → "K-level k=4 α=0.0125" (Wave 22 metric-rev3). Both interpretations yield FAIL verdict for K1/K4+K5/K7, but family labeling affects future cells.

10. **R5c p_bonf figure correction:** Replace 9.22e-11 (paper-draft.md:1444+2956, baseline-audit-report.md:7154, CLAIMS.md:3009+3086, wave275-p4-mnist-proposal.md:508 — uses INCORRECT R-level k=7 multiplier) → 3.95e-11 (JSON p_value_bonferroni per-3-arm-count). Both <<α=0.007143, verdict unchanged.

11. **Wave 307 sequencing:** Order of operations: (1) /tmp/ data migrations FIRST (commit per-cell), (2) per-cell paper edits SECOND (after data is in git), (3) cross-doc propagation THIRD (CLAIMS.md + headline-evidence + CONSOLIDATED_RESULTS.md), (4) RESOLUTION pass FOURTH (Wave 307+). Confirm or re-order.

12. **K7 /tmp data handling:** If `/tmp/wf280-k7/` is at risk of host reboot, migrate IMMEDIATELY before the R5b/CIFAR larger migrations. K7 data is ~125 KB (smallest migration after K1+K4+K5).

13. **R5b /tmp data volume:** `wf286-cifar/` contains ~50 .npz files at ~12 MB each = ~600 MB. Confirm /home partition has room (verify `df -h /home`).

14. **R1 d_z=+9.2 issue:** Investigate root cause of seed-43/44 framework-fallback rate=100% BEFORE regenerating R1 numbers. Current data is preserved at `/tmp/wf280-r1/` — do not discard.

15. **R5 production-ckpt statistical design:** Per-seed d_z=[+1.546, +1.331, +1.024] all POSITIVE is directionally consistent (baseline_WINS), but the aggregate d_z vs smoke-ckpt = Infinity (script bug). Re-compute aggregate d_z as paired diff across the 3 production seeds vs the 3-seed mean of smoke-ckpt OR report per-seed d_z only.

16. **R5c aggregate.py script fix:** `verification_outputs/wf280-r5c/aggregate.py` reports `paired_vs_smoke_ckpt_baseline.t_stat = Infinity` and `p_value_raw = 0.0` (meaningless). Fix by using `scipy.stats.t.sf` which handles infinity → 0 correctly, OR skip the Infinity d_z case and report undefined.

17. **R6 d_z headline choice:** Choose between naive +0.071 / cluster +0.333 / counterfactual +0.224 as the §7.1 R6 row headline. Recommendation: counterfactual +0.224 (since R6 IS the paper-quantity-driven wrapper cell; the naive +0.071 should appear in §3.3 as the uniform-cosine baseline reading for context).

19. **Naming agreement:** Per "R6 LineageFlow k6 foldability" vs "R6 Kanzi k6 foldability" — pick one and propagate to all 5 sites (paper §7.1 row 7 + abstract line 19/60 + Table 2.9 row 8 + docs/CLAIMS.md + headline-evidence).

---

**END WAVE 306 ALIGNMENT TABLE**

Next step: wait for user authorization on the 17 decisions above before applying any paper edits or /tmp/ migrations.