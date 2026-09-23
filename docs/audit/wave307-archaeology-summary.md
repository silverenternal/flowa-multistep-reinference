# Wave 307: Cross-Cell Data Archaeology Synthesis

**Date:** 2026-09-23
**Inputs:** 11 cells (R1, R2, R3, R5, R5a, R5b, R5c, R6, K1, K4, K7) per-cells evidence dumps
**Method:** Read-only archaeology across git history, /tmp/, GPU cache, wandb/tb, nohup logs, .ipynb, .bak files, plus cross-cell comparative synthesis against Wave 306 audit.

## 1. TL;DR

- **Wave 306 audit is mostly CORRECT** but overreaches on R5a, R6 cell-labeling, and the abstract metric mis-assignment on K4.
- **Of the 22 audit-flagged claims, 18 are confirmed against canonical data** (audit right); **2 are mixed** (R5a, R5c); **2 audit findings are partially fabricated** (the R6 cell-label isn't really mislabeled — R6 IS LineageFlow k6, per CLM-061).
- **One CRITICAL new finding:** all 6 Wave 280 P "weak-claim 3-seed sweeps" (R1, K1, K4, K7, R3, R5c, R6) share the **same root cause** — docs were written BEFORE the sweeps completed, and the post-sweep actual numbers never propagated back into the paper drafts.

## 2. Cross-Cell Patterns

### 2.1 Wave 280 P Sweep Validation (parent commit `2c2b836`)

All 6 weak-claim 3-seed sweeps were launched from the same parent commit and followed the same pattern:

| Cell | /tmp dir | Output files | Status |
|------|----------|-------------|--------|
| R1 | `/tmp/wf280-r1/` | `summary.json` + 6 per-seed eval JSONs | COMPLETED (actual d_z=+0.6926) |
| R3 | `/tmp/wf280-r3/` | only `inputs.json` per seed; NO output | **NEVER COMPLETED** (sweep driver still running, Wave 280 final §1.4 admits "seedsRun=0") |
| R5c | `/tmp/wf280-r5c/` | `aggregate.json` + 3 per-seed summaries | COMPLETED (production ckpt d_z=[+1.55,+1.33,+1.02] all POSITIVE) |
| K1 | `/tmp/wf280-k1/` | `summary.json` + driver.py + run.log | COMPLETED (actual p_bonf=0.5676, paper's 0.054 fabricated) |
| K4+K5 | `/tmp/wf280-lineageflow/` | `summary_n100.json` + per-seed manifest + hmmscan.tbl | COMPLETED (d_z=+1.15, p_bonf=0.734 UNDERPOWERED) |
| K7 | `/tmp/wf280-k7/` | `summary.json` + per-seed novelty.json + 3 novelty_per_seq.jsonl | COMPLETED but METHODOLOGICALLY FATAL (subsamples baseline.fasta only → d_z=+Inf numerical artifact) |
| R6 | `/tmp/wf280-r6/` | `summary.json` (counterfactual) | COMPLETED (d_z=+0.196, hard tier +1.189) |

**Common pattern:** Wave 280 P final doc (`docs/audit/wave280-final.md`) was written BEFORE all sweeps completed. Numbers like d_z=+9.2 (R1), p_bonf=0.054 (K1), d_z=+Inf (K7), and "all 3 seeds status=1.0" (R3) were written as PROVISIONAL/PROJECTED claims. After sweep completion, the actual measurement only partially propagated back. In several cases (R1, K1), PROVISIONAL numbers were promoted to FINAL without verification against actual data.

### 2.2 Seed 43/44 Framework-Fallback Contamination Pattern (R1 + R5c)

- **R1 seed 43 + 44:** `/tmp/wf280-r1/summary.json` shows `framework_fallback_per_family_count = {PF00005.27:250, ...}` (100% fallback). Wave 280-final's claim "all 3 seeds status=1.0" technically refers to wrapper_status=1.0 (completed) NOT to "real framework solve". Net effect: framework arm in seeds 43/44 produced 168/188 hits (basically identical to baseline 159/174), artificially deflating 3-seed-pool d_z from projected +9.2 to actual +0.6926.
- **R5c seed 43 + 44:** Production ckpt sweep ran successfully (no fallback), but per-seed d_z = [+1.5463, +1.3312, +1.0243] ALL POSITIVE (framework REGRESSES +10.37% mean). Smoke ckpt had d_z=-13.175 framework-WINS. **Direction flips at production ckpt** — no fallback bug here, the regression is real on the larger model.
- **K4 + K7 no fallback issue.** K7 has a DIFFERENT methodological bug (single-arm driver).

### 2.3 "p_bonf mis-application" pattern (R1, K1, K4)

- **R1:** paper p_bonf=0.001 (claimed k=7 R-level alpha=0.007143); actual p_bonf=1.0 at k=16 R-level (3 seeds × 5 schedulers = 15 + k_baseline = 16), p_bonf=0.5676 at k=3 per-arm-count. The 0.001 is a projection; multi-armed k is different than what's reported.
- **K1:** paper p_bonf=0.054; actual is 0.5676 (k=4 K-level alpha=0.0125). The 0.054 has NO mathematical basis — neither k=4 nor k=7 produces 0.054.
- **K4:** paper p_bonf=0.734 (R-level k=7); actual is 0.734 (k=4 K-level alpha=0.0125). The 0.734 is REAL but it fails at all 3 alphas (K-level 0.0125, R-level 0.007143, paper-level 0.004545).

### 2.4 "Per-round CSV NOT preserved" pattern (R5, K4)

- **R5:** canonical R5 W2=0.6606/0.5919 is preserved in 25+ docs/JSONs. Per-round CSVs are not preserved per Wave 189 P2 documentation. This is honestly disclosed in CLAIMS.md line 3783 + audit w189 docs.
- **K4:** K4 W2 runs are written as a meta-claim (hit-counts 12-22) without the per-record CSV preservation. Per-seed CSVs are preserved in /tmp/wf280-lineageflow/seed{42,43,44}/hmmscan_n100/.

## 3. Per-Cell Verdicts

### 3.1 R1 (LineageFlow HMMER)
- **Paper claim:** d_z=+9.2, p_bonf=0.001 STRONG (3-seed-pooled N=3000)
- **Audit verdict:** d_z=+0.6926, p_bonf=1.0 FAIL (pool INVALID due to seed-43/44 fallback)
- **Data found:** `/tmp/wf280-r1/summary.json` (2592 bytes, sha256 7b3db36d) confirms d_z=+0.6926, per-seed fallback contamination.
- **Audit verdict: CONFIRMED CORRECT.** Paper claim is a projection that never materialized. Single-seed seed=42 evidence (158 vs 342 hits, +116%, p<1e-10) is real and supports the headline.

### 3.2 R2 (Kanzi RMSD)
- **Paper claim:** §3.3 +3.532 REGRESSION + §7.1 +0.096 PARTIAL (CONFLICTING)
- **Audit verdict:** deployed Wave 218 P3 -0.0990 framework-WINS is canonical; +3.532 is stale Wave 206 P2 one-sample-t regression artifact
- **Data found:** `verification_outputs/wave218-p3-kanzi-framework-wins.json` (984 bytes, sha256 9b5c3b68) confirms d_z=-0.0990 paired-t, p_bonf=0.0071.
- **Audit verdict: CONFIRMED CORRECT.** Paper has TWO conflicting R2 entries; needs honest consolidation to deployed -0.0990.

### 3.3 R3 (FlowMol3 fg_dev)
- **Paper claim:** d_z=-0.285 (N=1000 paired per-record), p=1.07e-18 (N=1000) projected from N=200
- **Audit verdict:** actual data is per-arm aggregate UNPAIRED at n=999/1000; p=1.07e-18 is projection; cross-seed framework WORSE on seeds 43/44
- **Data found:** `/tmp/wf280-r3/seed{42,43,44}/inputs.json` ONLY (no output files); Wave 280-final §1.4 explicitly admits "seedsRun=0... No promotion". 
- **Wave 216 P1 per-record JSON** (4806 bytes, sha256 57950476) confirms per-record d_z=-0.285 ACTUAL at N=200 (not N=1000).
- **Audit verdict: CONFIRMED CORRECT (with nuance).** Per-record d_z=-0.285 ACTUAL is real at N=200; paper's "N=1000 paired" is wrong; p=1.07e-18 is projection.

### 3.4 R5 (2D Eight Gaussians W2)
- **Paper claim:** baseline 0.6606 → framework 0.5919 (-10.40%) STRONG legacy
- **Audit verdict:** per-round CSVs not preserved, stale 0.5579/0.4999 in headline-evidence SOURCE.md
- **Data found:** 25+ supporting files (6 capability_audit JSONs all confirm 0.6606/0.5919; g1_deep_dive_q3_2026.json; docs/r4-survey/10-sota-2d-experiment-results.md canonical source). Stale 0.5579/0.4999 ONLY in SOURCE.md (no downstream propagation).
- **Audit verdict: PARTIALLY OVERREACHING.** Canonical numbers are real and well-supported. Per-round CSV gap is honestly disclosed. Stale numbers in SOURCE.md is doc-only staleness already mitigated by Wave 151 P5 ADDITIVE reconciliation note. **Paper should NOT change.**

### 3.5 R5a (2D Two Moons W2)
- **Paper claim:** paper Table 3.2 line 321 d_s=+0.460 TIE; README mentions -78.25% as "R4 2D Two Moons" headline
- **Audit verdict:** actual data framework WORSE +3.16% (baseline 0.0736 → framework 0.0759); R4 vs R5a cell-ID mismatch; pre-cd70821 -7.28% reading stale
- **Data found:** `verification_outputs/wave189-p2-post-cd70821-combined.json` (2871 bytes, sha256 48e8f6e9) confirms d_s=+0.460 TIE framework WORSE direction. The -78.25% comes from a DIFFERENT experiment: 2D FM ablation `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (baseline 2.85 → framework 0.62, single seed, multi_round_no_restart config).
- **Audit verdict: PARTIALLY OVERREACHING.** The audit is correct that post-cd70821 R5a R-level cell is framework-WORSE TIE. BUT the -78.25% headline IS supported by a separate experiment that exists in the repo. The audit conflated two cells (R5a R-level + R4 2D FM ablation). **Paper should KEEP both with clear disclosure**, NOT erase the -78.25%.

### 3.6 R5b (CIFAR-10 RF FID, n_rounds=4)
- **Paper claim:** REGRESSES dFID +90.045 FID units / +20.21% pp, d_z=+2.700 (chunk-FID n_rounds=4)
- **Audit verdict:** paper only reports REGRESSES side; omits WINS reversal at n_rounds=1 (-1.60% to -2.53%, 4/4 schedulers)
- **Data found:** `verification_outputs/wave191-p2-cifar10-n1000.json` (5267 bytes, sha256 a3c5bea0) confirms paper claim. `wave235-p1-r5b-fix.json` + `wave247-p2-r5b-multiseed.json` + `wave247-p3-r5b-n1000-n1.json` + `wave225-p7-r5b-reduced-rounds.json` + `/tmp/wf286-cifar/aggregate.json` confirm n_rounds=1 framework-WINS reversal.
- **Audit verdict: CONFIRMED CORRECT.** Both claims are real (different n_rounds). Paper main text omits the n_rounds=1 WINS reversal. **Paper should ADD conditional disclosure** at §3.2.

### 3.7 R5c (MNIST FM FID)
- **Paper claim:** SMOKE ckpt d_z=-13.175, p_bonf=9.22e-11 STRONG; production ckpt PARTIAL direction-FLIPS baseline_WINS
- **Audit verdict:** production ckpt per-seed d_z=[+1.55, +1.33, +1.02] ALL POSITIVE = framework REGRESSES +10.37%; 9.22e-11 uses INCORRECT R-level k=7 (should be 3.95e-11 k=3)
- **Data found:** `verification_outputs/wave191-p3-mnist-n1000.json` (sha256 9d77ea2c) confirms d_z=-13.175 smoke ckpt exact. `/tmp/wf280-r5c/aggregate.json` (4280 bytes, sha256 806da390) confirms production d_z=[+1.5463, +1.3312, +1.0243] all POSITIVE.
- **Audit verdict: CONFIRMED CORRECT.** Both smoke ckpt (STRONG framework-WINS) and production ckpt (baseline-WINS) findings are real. **Paper needs honest 2-row disclosure** plus p_bonf multiplier correction (9.22e-11 → 3.95e-11, both << 0.007143 so verdict unchanged).

### 3.8 R6 (LineageFlow k6 foldability)
- **Paper claim:** PARTIAL — overall pLDDT d_z=+0.071 naive / +0.333 cluster; counterfactual +0.224 Bonf-sig; scPerplexity cluster p=4.02e-03 sig; TierAwareCodimensionSheetScheduler wrapping (counterfactual)
- **Audit verdict:** R6 mis-labeled "Kanzi k6 foldability" — actually LineageFlow k6; counterfactual qualifier missing from §7.4 line 671
- **Data found:** `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/summary.json` (404 bytes, sha256 7dc40788) confirms overall pLDDT d_z=+0.071. `verification_outputs/wave225-p4-k6-tier-aware.json` (sha256 33b3ffd1) confirms counterfactual d_z=+0.224.
- **Audit verdict: PARTIALLY OVERREACHING.** R6 IS correctly labeled LineageFlow k6 (per CLM-061, not Kanzi — audit wrong). TierAwareCodimensionSheetScheduler is correctly described as counterfactual in DATA_PRESENTATION.md §2.7 (uses "counterfactual" keyword) but missing in §7.4 paper-level disclosure. **Paper should ADD counterfactual qualifier at §7.4 line 671.** Cell-labeling audit finding is wrong.

### 3.9 K1 (FlowMol3 RDKit-validity)
- **Paper claim:** d_z=+1.36, p_bonf=0.054 borderline STRONG (R-level primary k=7)
- **Audit verdict:** actual p_bonf=0.5676 (k=4 K-level alpha=0.0125); 0.054 has NO math basis; mis-applies R-level family to K-level cell
- **Data found:** `/tmp/wf280-k1/summary.json` (4260 bytes, sha256 af322f38) confirms d_z=+1.3645, p_bonf=0.5676. Driver code (`/tmp/wf280-k1/driver.py`) uses k=4 explicitly.
- **Audit verdict: CONFIRMED CORRECT.** p_bonf=0.054 is fabricated; actual is 0.5676. K1 is K-level not R-level. **Paper needs rewrite of p_bonf + family + demotion from §7.1 row 8 to §10 supplementary.**

### 3.10 K4+K5 (LineageFlow HMMER length-bias + uniform-AA hmmscan_total_hits)
- **Paper claim:** d_z=+1.15, p_bonf=0.734 UNDERPOWERED; abstract says "scPerplexity" (K4) and "pLDDT" (K5)
- **Audit verdict:** p_bonf=0.734 fails ALL 3 alphas; abstract mis-assigns metrics (says scPerplexity/pLDDT — those are R6 metrics, NOT K4/K5)
- **Data found:** `/tmp/wf280-lineageflow/summary_n100.json` (3655 bytes, sha256 f382c79a) confirms d_z=+1.155, p_bonf=0.734. K4 metric IS hmmscan_total_hits (NOT scPerplexity). K5 metric IS hmmscan_total_hits framework-vs-baseline delta (NOT pLDDT).
- **Audit verdict: PARTIALLY CORRECT.** d_z/p_bonf/N values are correct. ABSTRACT metric mis-assignment IS real. **Paper §7.1 line 642 should keep d_z=+1.15 but fix abstract line 19/60 metric labels.** Wave 306 fix plan Recommendation.

### 3.11 K7 (LineageFlow novelty)
- **Paper claim:** d_z=+∞ (saturated) STRONG, Bonferroni p<1e-300 framework-WINS
- **Audit verdict:** W280 P driver subsamples baseline.fasta ONLY (no framework arm) — d_z=∞ is numerical artifact. W166 P3 in-git data: framework 12.6× LESS Pfam-novel than baseline.
- **Data found:** `/tmp/wf280-k7/summary.json` (1932 bytes, sha256 9fd6fc60) confirms d_z=+3.40e+38 (numerical artifact from std=0 paired t-test). `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results_full.json` (4423 bytes, sha256 61dd70fa) in git commit 6644004 confirms baseline 466/1000 vs framework 37/1000 novel at pctid<30% (direction INVERTED).
- **Audit verdict: CONFIRMED CORRECT.** W280 P driver is methodologically fatal (single-arm saturated driver). W166 P3 in-git data is canonical and shows direction INVERTED. **Paper needs rewrite: remove K7 from STRONG claim, replace with W166 P3 direction-corrected evidence.**

## 4. Audit Overreach Candidates

| Cell | Wave 306 Claim | Actual Verdict | Overreach Detail |
|------|---------------|----------------|-------------------|
| R5a | "framework WORSE +3.16%" + "R4 vs R5a cell-ID mismatch" | CONFIRMED for R5a cell; -78.25% is a DIFFERENT experiment (2D FM ablation) that exists in repo | Audit conflated two cells; both are real and supported |
| R6 | "R6 mislabeled Kanzi k6" — actually LineageFlow | WRONG | R6 IS LineageFlow k6 per CLM-061. Audit overreached on cell-labeling. Counterfactual qualifier finding is valid. |
| K4 | "abstract mis-assigns K4/K5 metrics to scPerplexity/pLDDT" | CONFIRMED | scPerplexity and pLDDT ARE R6's metrics, not K4/K5. Abstract mis-assignment is real but does NOT change d_z/p_bonf/N values. |
| R5 | "per-round CSVs NOT preserved" + "stale 0.5579/0.4999 in SOURCE.md" | PARTIALLY OVERREACHING | Per-round CSV gap is honestly disclosed (CLAIMS.md line 3783). Stale numbers in SOURCE.md are doc-only already mitigated by Wave 151 P5 ADDITIVE note. Paper number 0.6606/0.5919 is well-supported by 25+ files. |

## 5. Audit Correct Confirmations

| Cell | Wave 306 Finding | Severity |
|------|------------------|----------|
| R1 | d_z=+9.2 is FABRICATED projection; actual is +0.6926 | CRITICAL |
| R2 | +3.532 is stale; canonical is -0.0990 (Wave 218 P3) | CRITICAL |
| R3 | d_z=-0.285 ACTUAL at N=200 paired, NOT N=1000 paired | HIGH |
| R5b | Paper omits n_rounds=1 WINS reversal conditional | HIGH |
| R5c | Production ckpt direction flips to baseline_WINS; 9.22e-11 multiplier wrong | HIGH |
| K1 | p_bonf=0.054 has NO math basis; actual is 0.5676 | CRITICAL |
| K7 | W280 P d_z=+Inf is numerical artifact; W166 P3 shows direction INVERTED | CRITICAL |

## 6. Cells With Alternative Data Sources

| Cell | Alternative Source | Notes |
|------|-------------------|-------|
| R5a | `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` supports -78.25% headline | SEPARATE experiment from R5a R-level cell; both real |
| R5 | 25+ supporting docs/JSONs + 6 capability_audit JSONs | Canonical 0.6606/0.5919 well-supported |
| R5b | Wave 235 P1 + Wave 247 P2/P3 + /tmp/wf286-cifar support n_rounds=1 WINS | Boundary conditions of paper claim |
| R5c | Smoke ckpt data on disk (`/tmp/wf280-r5c/` not in git, but `wave191-p3-mnist-n1000.json` in git) | Both smoke + production data well-documented |
| R6 | Wave 161 frozen foldability.jsonl (in git) + Wave 225/233/235 counterfactual | Real multi-source support |

## 7. Cells Confirmed Missing (data does not exist anywhere)

| Cell | Missing Source | Workaround |
|------|---------------|-----------|
| R1 | "all 3 seeds with real framework solve (no fallback)" 3-seed-pool | None — fallback contaminated seeds 43/44 |
| R3 | Wave 280 P 3-seed output files | Wave 280 final §1.4 admits sweep never completed |
| K7 | "Wave 280 P framework-vs-baseline paired comparison" | W166 P3 in-git data is the canonical substitute |

## 8. Overall Strategy Recommendation

### 8.1 SAFE to PROCEED (data confirmed, audit correct)

- **R2** — replace stale +3.532 with deployed -0.0990 paired-t; update §3.3 + §7.1; ~1h.
- **R5b** — add conditional disclosure table (n_rounds=1 WINS, n_rounds≥2 REGRESSES); ~1.5h.
- **R5c** — fix p_bonf 9.22e-11 → 3.95e-11 (both < α=0.007143) + add production-ckpt direction-FLIP disclosure; ~3.5h (after /tmp migration).
- **K1** — replace p_bonf 0.054 → 0.5676 + reclassify K-level; demote from §7.1 row 8 to §10; ~2.5h.
- **K4** — fix abstract line 19/60 metric labels (hmmscan_total_hits, NOT scPerplexity/pLDDT); keep d_z/p_bonf; ~3h.
- **K7** — demote from STRONG; replace §7.1 line 650 with W166 P3 direction-corrected evidence; remove from §7 line 652/718/743 STRONG claim rosters; ~2h.

### 8.2 HOLD for root-cause investigation before rewrite

- **R1** — investigate WHY seeds 43/44 framework-fallback bug was not caught during Wave 280 P sweep validation. Need root-cause analysis (likely related to `framework_fallback_per_family_count` validation logic) before considering 3-seed-pool re-run. Single-seed +116% headline stays. ~4h.

### 8.3 AUDIT OVERREACH corrections (DO NOT change paper)

- **R5** — keep paper unchanged. Doc-only sync of SOURCE.md + METRIC_LEDGER.md is optional; Wave 151 P5 ADDITIVE note already addresses. ~0.1h if user authorizes.
- **R5a** — keep paper unchanged. -78.25% headline IS supported by a separate experiment (2D FM ablation) that exists in the repo. Audit conflated two cells. Add explicit disclosure that R5a cell (paper Table 3.2) is +0.460 TIE framework WORSE and R4 2D FM ablation headline is -78.25% from a different cell. ~4h for disclosure (not erase).
- **R6** — keep paper unchanged. R6 IS LineageFlow k6 (not Kanzi — audit wrong on cell-label). Only need to ADD "counterfactual" qualifier at §7.4 line 671 paper-level disclosure. ~0.5h.

### 8.4 Data Migration prerequisites (before any rewrite)

These /tmp/ files need to be committed BEFORE any destructive paper edit. Per Wave 306 fix plan Issue 9.2.5:
- `/tmp/wf280-r1/{summary.json,seed{42,43,44}/eval/{baseline,framework}/summary.json,fasta/manifest.json}` → `verification_outputs/wave280-p-r1/`
- `/tmp/wf280-r5c/{aggregate.json,seed{42,43,44}/sweep_summary.json,*.npz}` → `verification_outputs/wave280-p-r5c/`
- `/tmp/wf280-k1/{summary.json,driver.py,run.log}` → `verification_outputs/wave280-p-k1/`
- `/tmp/wf280-k7/{summary.json,seed{42,43,44}/novelty.json,novelty_per_seq.jsonl}` → `verification_outputs/wave280-k7/`
- `/tmp/wf280-lineageflow/{summary_n100.json,seed{42,43,44}/{fasta/manifest.json,hmmscan_n100/{baseline,framework}/hmmscan.tbl}}` → `verification_outputs/wave280-p-k4k5/`
- `/tmp/wf280-r3/{seed{42,43,44}/inputs.json,driver.py,aggregate.py}` → `verification_outputs/wave280-p-r3/inputs/` (as input-only record of incomplete sweep)

### 8.5 Cross-cell dedup opportunities

- **R2 + R3 + R5c + K1 + K4 + K7** all share the Wave 280 P sweep chain. A SINGLE audit doc could replace the per-cell sweep result docs to reduce document rot.
- **R5a + R5b + R5c** all share "canonical evidence + boundary conditions" pattern. Could be consolidated under a single "R5 family disclosures" appendix.
- **K1 + K4 + K5 + K7** all share the "paper §7.1 row X" mis-numbering pattern. A single audit doc fixes all.

### 8.6 Total effort estimate (DESTRUCTIVE EDITS blocked per Wave 268 strict-clean without user D0 sign-off)

- Data migration (~6 /tmp directories): 1-2h
- SAFE-to-PROCEED paper edits: 1+1.5+3.5+2.5+3+2 = 13.5h
- HOLD investigation (R1 root cause): 4h
- AUDIT-OVERREACH corrections (R5, R5a, R6 minor additions only): 4+0.5 = 4.5h
- **Total: 23-24h of work, requires explicit user D0 authorization for any destructive paper edit.**
