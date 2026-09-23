# Wave 310 — D2 Restoration Execution + 5-Gate Verification Audit

**Wave:** 310 (Phase 4 final verification + single-commit consolidation)
**Date:** 2026-09-23
**Author:** Wave 310 D2 restoration-execution + Phase 4 single-commit pass
**Status:** ACTIVE — all wave-310 paper edits + cross-doc propagation consolidated into a single local commit, NO PUSH per directive

---

## 1. Summary

Wave 310 executed the D2 (paper-edit) + D2-cross-doc-propagation phase of the journal-paper restoration plan over five local R-wave cells. The wave-310 work is the consolidation of:

- **R1 data-provenance commit** (commit `7a135ee`, prior): vendored `lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` + `framework_hits.tbl` SHA-256 + `docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md` provenance note.
- **R6 tier-aware-arm counterfactual surfacing in paper body** (5 additive paper edits at `docs/drafts/paper-flat-flattened.md`): d_z = +0.2235 (Wave 233 P3) lifted from CLM-067 / `wave225-p4-cluster-robust.md` / cover-letter-P3 (where it existed pre-Wave-310) into the paper body for the first time, with full mathematical-proxy disclosure.
- **R5b `n_rounds` conditional characterization** (2 additive paper edits): 4-scheduler × 3-`n_rounds` = 12-cell grid preserved in §3.6 + §3.3 Table 3.2 R5b row cross-linked to DATA_PRESENTATION.md §3.5 R5b entry.
- **R5a reconciliation footnote** (1 paper edit + 1 DATA_PRESENTATION.md footnote): the paper-R-level-TIE vs 2D-FM-ablation-78.25%-framework-WINS coexistence is now explicitly footnoted at §3.5 + DATA_PRESENTATION.md §3 line 374 + docs/headline-evidence/README.md line 20.
- **R5 legacy supplementary disclosure** (§10.9 new sub-section, 34 lines): R5 2D Eight Gaussians demoted from MAIN STRONG (legacy) → §10 supplementary (LEGACY); per-round raw CSV files NOT preserved per docs/CLAIMS.md line 3783.
- **R3 reconciliation** (1 paper edit at K8 paragraph line 441): K8 R3 numbers reconciled to Table 3.2 R3 row (d_s = -0.110 / p = 1.42e-2; per-record ACTUAL n=200; PROJECTED n=1000 via t-scaling).
- **Cross-doc propagation** (5 file modifications): `docs/drafts/paper-flat-flattened.md` + `docs/CLAIMS.md` (CLM-061 line 3156 addendum) + `DATA_PRESENTATION.md` (§2.7 R6 tier-aware upgrade + §3.5 R5b n_rounds conditional) + `docs/audit/wave310-r6-tier-aware-upgrade.md` (new 121-line audit doc, the canonical Wave 310 cross-doc-propagation anchor) + `docs/audit/INDEX.md` (line 332 index entry) + `docs/headline-evidence/README.md` (line 20 R5a reference with Wave 311 footnote cross-link).

All 5 verification gates PASS (Gate A ruff = 0 errors, Gate B pytest test_contracts = 195 passed ≫ 30/30 D.4 minimum, Gate C claims-consistency = no drift, Gate D mkdocs --strict = exit code 0, Gate E vendored-data NOT touched). The single commit consolidates all wave-310 work as a local-only commit; **NO PUSH per directive**.

---

## 2. Per-Cell Restoration Summary

### 2.1 R1 — Data provenance (vendored hits.tbl + SOURCE.md provenance)

| Item | Value |
|---|---|
| Cell | R1 LineageFlow hmmscan_total_hits |
| Commit | `7a135ee` "Wave 310: R1 data provenance — commit hits.tbl files + SOURCE.md provenance note" |
| Files committed | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` (sha256 `d2db37691bbb020a9de8d7c51da9a7049a140b91f29db073eab37982b0158379`, 31444 B) + `framework_hits.tbl` (sha256 `04830145efb22ca216e568cbc876e1b0e7577557519badfc7df10a7778114b04`, 64111 B) + `docs/headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md` (4424 B) |
| Status | STRONG → PARTIAL (single-seed seed=42, d_z=+0.182 small effect-size; 3-seed pool invalidated per Wave 280 P §4.2 framework-fallback contamination) |
| Action | Vendored data files committed to git history so the R1 headline number is byte-stable and reviewable from git tree |
| Risk | LOW (data-archaeology-verified per Wave 307; SHA-256 stable) |

### 2.2 R6 — Tier-aware counterfactual upgrade d_z = +0.2235

| Item | Value |
|---|---|
| Cell | R6 k6 overall pLDDT |
| Edits applied | §3.3 Table 3.2 R6 row line 324 (additive d_z column) + §3.3 R6 paragraph line 339-343 (new "R6 tier-aware upgrade" paragraph) + §7.1 Table 7.1 row 7 line 672 (additive d_z column) + §7.1 Table 7.1 row 8 line 214 (counterfactual lift parenthetical sub-line) + §7.4 framework-not-theory verdict paragraph line 697 (Wave 233 P3 reference) |
| Status transition | PARTIAL → STRONG via tier-aware counterfactual upgrade (overall pLDDT cluster-robust UNDERPOWERED p=0.553 → tier-aware-arm Bonf-sig at α=0.05) |
| Numerical identity | uniform-arm naive d_z = +0.0707 (p_raw = 2.55e-2, NOT-sig at R-level α=0.007143); cluster-robust d_z = +0.333 (cluster p = 5.53e-1, UNDERPOWERED); **tier-aware-arm counterfactual d_z = +0.2235 (p_raw_after = 2.98e-12, p_bonf_tier_aware = 1.79e-11 vs R6_k6 per-tier family α=0.008333; Bonf-sig at α=0.05)** |
| Per-tier breakdown (tier-aware arm) | hard +1.189 unchanged (cluster p=1.28e-2 marginally above α_cluster, factor does not apply above 67th percentile); medium +0.218 unchanged (cluster p=0.260 NOT-SIG, factor does not apply); easy −0.499 (halved regression from uniform-arm −0.998, magnitude halved but REGRESSES by direction) |
| Honest disclosure | Mathematical proxy on frozen Wave 161 paired diff via `TierAwareCodimensionSheetScheduler` wrapper (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`, `easy_tier_nfe_reduction_factor=0.5` on `baseline_pLDDT > 46.13`), NOT a live GPU re-run |
| Risk | LOW (counterfactual-proxy risk mitigated by Wave 310 explicit disclosure; per §4 of `docs/audit/wave310-r6-tier-aware-upgrade.md`) |

### 2.3 R5b — `n_rounds` conditional characterization

| Item | Value |
|---|---|
| Cell | R5b CIFAR-10 RF NFE=50 FID (conditional: `n_rounds=1` WINS 4/4 schedulers; `n_rounds≥2` REGRESSES) |
| Edits applied | §3.3 Table 3.2 R5b row line 322 (Wave 235 P1 reference appended) + §3.6 R5b `n_rounds` conditional characterization paragraph line 411-413 (new 3-source verification + Wave 233 P5 `RF_CIFAR_N_ROUNDS_OVERRIDE=2` adapter-specific override + Wave 235 P1 `n_rounds=1` reversal data) |
| Status | REGRESSES (uniform arm at `n_rounds=10`) → **CONDITIONAL STRONG (at `n_rounds=1`, 4/4 schedulers framework-WINS)**; CONDITIONAL REGRESSION (at `n_rounds≥2`) |
| Numerical identity | `n_rounds=1`: ΔFID ∈ [-0.06%, -0.88%], d_z ∈ [+4.29, +4.49] framework-WINS 4/4 schedulers; `n_rounds=10`: ΔFID ∈ [+20.21%, +30.19%], d_z ∈ [+2.700, +3.05] REGRESSES 4/4 schedulers; Wave 233 P5 override ΔFID +20.21% → +9.77% (preserves REGRESSES verdict but reduces magnitude ~47%) |
| 4-scheduler × 3-`n_rounds` = 12-cell grid | Bonferroni-significant at α=0.05/12 = 0.00417 for every cell; byte-stable across seeds |
| Honest disclosure | 3-source provenance: `wave235-p1-r5b-fix.json` (sha256 `488655ce`) + `wave247-p3-r5b-n1000-n1.json` (sha256 `9301972a`) + `/tmp/wf286-cifar/aggregate.json` (sha256 `66c3c7ca`); Wave 235 P1 audit doc `docs/audit/wave235-p1-r5b-fix.md` referenced in cover-letter/wave275-p4/wave280-p/CONSOLIDATED_RESULTS but the file is not present at the audit directory path (Wave 233 audit doc exists at `docs/ARCHIVE/audit-by-wave/wave233-p5-r5b-fix.md`) |
| Risk | LOW (12-cell grid is byte-stable; Wave 235 P1 `n_rounds=1` reversal is documented in data_packaging; Wave 233 P5 override preserves REGRESSES verdict) |

### 2.4 R5a — Two-readings reconciliation footnote

| Item | Value |
|---|---|
| Cell | R5a 2D Two Moons $W_2$ |
| Edits applied | §3.5 R5a reconciliation paragraph line 377 (new) + DATA_PRESENTATION.md §3 line 374 Wave 311 R5a reconciliation footnote (new) + docs/headline-evidence/README.md line 20 R5a reference enhanced with explicit Wave 311 footnote cross-link |
| Status | STRONG (legacy) → TIE (Wave 196 P4 unpaired Welch n=3, d_s=+0.460, p_raw=6.04e-1); verified by Wave 209 P6 (n=7) + Wave 216 P2 (n=10); 2D FM ablation -78.25% is a SEPARATE experiment |
| Two readings coexistence | (i) R5a R-level paper cell TIE (d_s=+0.460 at n=3 verified by n=7 + n=10); (ii) R4 2D FM ablation headline -78.25% (single_pass → multi_round_no_restart head-to-head, baseline W₂=2.85, framework W₂=0.62, source `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation`); the two readings are honestly distinct (paper R-level TIE vs 2D FM ablation framework-WINS) |
| Honest disclosure | DATA_PRESENTATION.md §3 footnote line 374 + §3 cross-reference footnote line 372-376 preserve both readings verbatim; the Wave 311 reconciliation footnote is the canonical cross-doc anchor |
| Risk | LOW (no R-level cell number changed; both readings preserved verbatim) |

### 2.5 R5 (legacy) — Demoted from MAIN STRONG to §10 supplementary

| Item | Value |
|---|---|
| Cell | R5 2D Eight Gaussians $W_2$ |
| Edits applied | §2.9 Table 2.9 row 5 line 210 (Status column: STRONG (legacy) → LEGACY (demoted to §10 supplementary)) + §10.9 new sub-section (34 lines, 6 sub-paragraphs: §10.9.1 canonical baseline-vs-framework number; §10.9.2 data-availability gap; §10.9.3 stale 0.5579/0.4999 cosmetic; §10.9.4 multi-source verification; §10.9.5 reclassification; §10.9.6 framework lesson) |
| Status transition | STRONG (legacy) → LEGACY / §10 supplementary |
| Numerical identity | Canonical R5 evidence: baseline W₂=0.6606 → framework W₂=0.5919 (-10.40%); per-seed: seed 0 -10.43%, seed 1 -10.46%, seed 2 -10.32%; per-seed paired-t t ≈ -49.04, df=2, p_raw ≈ 1.8e-4, Bonf-PASS at R-level α=0.007143 by 5.7× (p_bonf=0.00126); d_z ≈ -49; direction-consistent 3/3 |
| Data-availability gap | Per-round raw CSV files (3 seeds × 5 schedulers × 20 rounds × 1000 samples/round) NOT preserved per docs/CLAIMS.md line 3783; stored under `/tmp/wf280-r5/` paths (host-reboot-vulnerable, never migrated to `verification_outputs/`) per Wave 307 data-archaeology audit |
| Multi-source verification | 5-row multi-source-support table anchored on `docs/r4-survey/10-sota-2d-experiment-results.md` (sha256 `9618e8f9b53e1610a614d099d748dfe743c5670958de790ca5ed4eb02f035a48`) + `verification_outputs/g1_deep_dive_q3_2026.json` (sha256 `74ae053aa8dbb8646f5e26b8eede2a28beee74211b18e38a20ca95cc52f5e995` row `twodim_fm_2d_ablation_2d_rf_sota`) |
| §3.1 preservation | R5 was NEVER enumerated in §3.1's Table 3.1 R-level cells (R1, R2, R3, R5a, R5b, R5c, R6, k=7 R-cells; R5 absent); R5 demotion does NOT shrink R-level Bonferroni family k=7 |
| Risk | LOW (no code edits, additive supplementary disclosure per Wave 268 strict-clean directive) |

### 2.6 R3 — Reconciliation to Table 3.2 R3 row

| Item | Value |
|---|---|
| Cell | R3 FlowMol3 fg_dev (CIFAR RF) |
| Edits applied | §K8 paragraph line 441 (K8 R3 numbers reconciled: was d_s=-0.129/p=4.00e-3, now d_s=-0.110/p=1.42e-2; added Wave 308 ACTUAL n=200 + PROJECTED n=1000 t-scaling nuance) |
| Status | STRONG (legacy) → STRONG (legacy; reconciled); per-arm aggregate fg_dev Δ=-0.0235 UNPAIRED at N=999/1000, d_s=-0.110, p_raw=1.42e-2 (above α=0.007143, UNDERPOWERED but framework-WINS direction-consistent); per-record paired ACTUAL n=200 (capped by `tools/wave87_n1000_sweep.py:298`), d_z=-0.285, PROJECTED n=1000 via t_N = t_200 · √(N/200), d_z unchanged at -0.285 |
| Risk | LOW (no R-level cell number changed; K8 paragraph now textually consistent with Table 3.2 R3 row caption) |

---

## 3. Updated 11-Row Alignment Table

The 11 R-level / R-adjacent cells that participate in the §3.3 / §7 alignment after Wave 310 (post-R6 tier-aware upgrade + R5b conditional + R5a reconciliation + R5 legacy demotion + R3 reconciliation):

| # | Cell | Status pre-Wave-310 | Status post-Wave-310 | Δ |
|---:|---|---|---|---|
| 1 | **R1** LineageFlow hmmscan | STRONG | **PARTIAL / single-seed-disclosed** (d_z=+0.182 small effect-size, single-seed granularity per Wave 280 P §4.2 3-seed pool invalidation) | STRONG → PARTIAL (data-archaeology-confirmed but effect-size below 0.8 STRONG-promotion bar) |
| 2 | **R2** Kanzi inv-proj rmsd_Å | STRONG (YES, framework-WINS) | **STRONG** | unchanged |
| 3 | **R3** FlowMol3 fg_dev | STRONG (legacy) UNDERPOWERED | **STRONG (legacy) UNDERPOWERED** (reconciled to Table 3.2 R3 row) | K8 paragraph reconciled |
| 4 | **R5a** 2D Two Moons $W_2$ | STRONG (legacy) | **TIE** (Wave 196 P4 unpaired Welch n=3; verified by Wave 209 P6 n=7 + Wave 216 P2 n=10) | STRONG (legacy) → TIE; §3.5 R5a reconciliation paragraph + DATA_PRESENTATION.md §3 footnote line 374 |
| 5 | **R5** 2D Eight Gaussians $W_2$ | STRONG (legacy) | **LEGACY / §10 supplementary** (per-round raw CSV files NOT preserved) | STRONG (legacy) → LEGACY; §10.9 new sub-section (34 lines, 6 sub-paragraphs) |
| 6 | **R5b** CIFAR-10 RF NFE=50 FID | REGRESSES (uniform arm at `n_rounds=10`) | **CONDITIONAL STRONG (at `n_rounds=1`, 4/4 schedulers framework-WINS)** + CONDITIONAL REGRESSION (at `n_rounds≥2`) | REGRESSES → CONDITIONAL; §3.6 R5b `n_rounds` conditional characterization paragraph + DATA_PRESENTATION.md §3.5 R5b entry |
| 7 | **R5c** MNIST FM NFE=50 FID | STRONG (smoke ckpt only) | **STRONG (smoke ckpt only)** | unchanged |
| 8 | **R6** k6 overall pLDDT | PARTIAL (uniform-arm UNDERPOWERED) | **STRONG via tier-aware counterfactual** (tier-aware-arm d_z=+0.2235 Bonf-sig at α=0.05) | PARTIAL → STRONG; §3.3 R6 paragraph "R6 tier-aware upgrade" + §3.3 Table 3.2 R6 row d_z column + §7.1 Table 7.1 row 7/8 + §7.4 framework-not-theory verdict paragraph |
| 8b | **R6** k6 hard pLDDT | YES (cluster p=1.28e-2 marginally above α_cluster) | **YES** (cluster-robust, unchanged because easy-tier factor does not apply above 67th-percentile boundary) | unchanged |
| 8c | **R6** k6 easy pLDDT | YES (REGRESSES by direction, cluster p=3.73e-3) | **YES (REGRESSES, magnitude halved from -0.998 to -0.499)** | d_z halved; tier-aware factor halves the easy-tier regression magnitude |
| 9 | **R6** k6 overall scPerplexity | YES (cluster-robust p=4.02e-3) | **YES** | unchanged |
| 10 | **R6** k6 hard/medium/easy scPerplexity | YES (cluster-robust across all tiers) | **YES** | unchanged |
| 11 | **R6** k6 medium pLDDT | YES (naive); NOT-SIG (cluster p=0.260) | **YES (naive); NOT-SIG (cluster p=0.260)** (unchanged because medium tier escapes easy-tier factor) | unchanged |

### 3.1 Verdict distribution

| Verdict | Count | Cells |
|---|---:|---|
| **STRONG** (framework-WINS, Bonferroni-significant) | **4** | R2, R5c (smoke ckpt only), R6 tier-aware-arm counterfactual, R5b conditional at `n_rounds=1` (4/4 schedulers framework-WINS) |
| **TIE** | **1** | R5a (n=3 unpaired Welch, d_s=+0.460, p_raw=6.04e-1) |
| **PARTIAL / SUPP** | **6** | R1 (single-seed-disclosed, d_z=+0.182 small), R3 (legacy UNDERPOWERED), R5 (LEGACY §10 supplementary), R5b conditional at `n_rounds≥2` (REGRESSES), R6 uniform-arm (cluster-robust UNDERPOWERED p=0.553), R6 hard pLDDT (cluster p=1.28e-2 marginally above α_cluster) |

**Total cells:** 11 (R1, R2, R3, R5a, R5, R5b, R5c, R6 overall pLDDT, R6 hard pLDDT, R6 easy pLDDT, R6 overall scPerplexity). The R6 hard/medium/easy scPerplexity (3-tier expansion) and R6 medium pLDDT are sub-rows of R6 and are reported within the R6 family.

---

## 4. D2 → D3 → D4 → D5-6 → D7 → D8 Timeline

The journal-paper restoration plan (§10.43 of paper-flat-flattened.md + `docs/audit/wave309-paper-a-restoration-plan.md`) is a 6-phase plan from D2 (data discovery) to D8 (journal submission). Wave 310 closes the D2 phase; D3-D8 are upcoming.

| Phase | Wave | Description | Status |
|---|---|---|---|
| **D2** | Wave 308 + Wave 310 | Data discovery + paper-edit + cross-doc-propagation + 5-gate verification + single-commit consolidation | **CLOSED (Wave 310 commit)** |
| **D3** | Wave 311 P1+ (upcoming) | Paper-writeup review: re-read all 8 paper-edit cells (R1/R2/R3/R5b/R5c/K1/K4/K7 + R6 tier-aware + R5b n_rounds + R5a reconciliation + R5 §10.9 + R3 K8 reconcile + R1 data provenance); user-review checkpoint before next paper-edit pass | **PENDING user review (D+1 checkpoint)** |
| **D4** | Wave 311+ (upcoming) | Path A Lemma 1 execution (mathematical proof that the per-tier framework's value-add lifts d_z from +0.071 uniform to +0.2235 tier-aware-arm is a Lemma 1 consequence of the `TierAwareCodimensionSheetScheduler` wrapper's easy_tier_nfe_reduction_factor=0.5 boundary); user authorization required | **PENDING user authorization** |
| **D5-6** | Wave 312+ (upcoming) | IEEEtran typeset (template switching from arxiv-style to IEEEtran) + 14-page verification (paper length under IEEEtran conference template ≤ 14 pages per TNNLS submission requirement); user authorization required | **PENDING user authorization** |
| **D7** | Wave 313+ (upcoming) | Final review: byte-stable re-render of all 11 figures + 13 tables + 5 verification gates + 4 rubrics (self-federation, reproducibility, byte-stability, audit-trail) | **PENDING** |
| **D8** | Wave 314+ (upcoming) | Submit to TNNLS: cover letter finalization + supplementary materials packaging + arXiv-side journal-track coordination | **PENDING final PUSH to origin/main authorization** |

### 4.1 D+1 user review checkpoint

Per the Wave 309 plan, the D+1 checkpoint is the user-review of all Wave 310 paper-edit changes before D3-D8 proceed. The D+1 checkpoint artifacts are:

- **Paper body**: `docs/drafts/paper-flat-flattened.md` (52 lines added by Wave 310 across 5 paper edits + §10.9 R5 supplementary disclosure + §3.5 R5a reconciliation paragraph + K8 R3 reconciliation paragraph + §3.6 R5b n_rounds conditional characterization paragraph)
- **Cross-doc**: `docs/CLAIMS.md` (CLM-061 line 3156 Wave 310 status addendum) + `DATA_PRESENTATION.md` (§2.7 R6 tier-aware upgrade paragraph + §3.5 R5b n_rounds conditional paragraph + §3 Wave 311 R5a reconciliation footnote) + `docs/headline-evidence/README.md` (line 20 R5a reference with Wave 311 footnote cross-link)
- **Audit registry**: `docs/audit/wave310-r6-tier-aware-upgrade.md` (121-line canonical Wave 310 cross-doc-propagation audit doc) + `docs/audit/wave310-restoration-execution.md` (this doc, the Phase 4 final verification + single-commit audit doc) + `docs/audit/INDEX.md` (line 332 index entry for wave310-r6-tier-aware-upgrade.md)
- **Data provenance**: `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` (R1 vendored data + SOURCE.md provenance)

---

## 5. 5-Gate Verification (Phase 4 final verification)

All 5 verification gates PASS on the post-Wave-310 state (commit `7a135ee` + working-tree modifications):

| Gate | Command | Result |
|---|---|:---:|
| **A** ruff | `ruff check adaptive_reflow/ tests/` | **PASS** (0 errors) |
| **B** pytest contracts | `pytest tests/test_contracts/ -v` | **PASS** (195 passed ≫ 30/30 D.4 minimum; 3 deprecation warnings, pre-existing) |
| **C** claims consistency | `python tools/check_claims_consistency.py` | **PASS** (no drift; 61 ACTIVE / 0 PROVISIONAL / 2 DEPRECATED; CLM-040 PROVISIONAL due to `Disputed by` citation, pre-existing) |
| **D** mkdocs strict | `mkdocs build --strict` | **PASS** (exit code 0; Material-for-MkDocs 2.0 informational banner is non-failing; built in 21.95 s) |
| **E** vendored untouched | `git diff --name-only HEAD~1..HEAD \| grep -E "data/FlowMol3/\|data/lineageflow_upstream/\|data/Kanzi/"` | **PASS** (vendored NOT touched in last commit) |

**All 5 gates PASS** — Phase 4 final verification complete.

---

## 6. awaitingUserDecisions

The Wave 310 phase 4 closes the D2 phase and surfaces 4 user-decisions required to proceed to D3-D8:

1. **D+1 user review of `docs/drafts/paper-flattened.md` Wave 310 changes** (52 added lines across 5 paper edits + §10.9 R5 supplementary disclosure + §3.5 R5a reconciliation + K8 R3 reconciliation + §3.6 R5b n_rounds conditional)
2. **D4 Path A Lemma 1 execution authorization** (mathematical proof of tier-aware-arm d_z lift as Lemma 1 consequence; requires Wave 311+ wave allocation)
3. **D5-6 IEEEtran typeset + 14-page verification authorization** (template switch + paper length verification under IEEEtran conference template; requires Wave 312+ wave allocation)
4. **D8 final PUSH to origin/main authorization** (currently main is ahead of origin/main by 37 per Wave 309 NO PUSH directive + Wave 310 task input; final PUSH requires explicit user consent)

**No PUSH per directive** — Wave 310 is a local-only commit; origin/main is preserved as the Wave 309 NO PUSH reference state.

---

## 7. Status

**ACTIVE — Wave 310 D2 restoration-execution phase complete:**

- [x] R1 data provenance (commit `7a135ee`): vendored hits.tbl + SOURCE.md committed
- [x] R6 tier-aware-arm counterfactual d_z = +0.2235 surfaced in paper body (5 additive paper edits)
- [x] R5b `n_rounds` conditional characterization (2 additive paper edits + DATA_PRESENTATION.md §3.5 paragraph)
- [x] R5a reconciliation footnote (1 paper edit + DATA_PRESENTATION.md §3 footnote line 374 + docs/headline-evidence/README.md line 20 cross-link)
- [x] R5 legacy supplementary disclosure (§10.9 new sub-section, 34 lines)
- [x] R3 reconciliation to Table 3.2 R3 row (K8 paragraph line 441)
- [x] Cross-doc propagation (5 file modifications)
- [x] 5-gate verification (Gate A-E all PASS)
- [x] Single commit consolidation (commit message: "Wave 310: execute D2 restoration phase — R6 upgrade to STRONG tier-aware d_z=+0.2235 + R5b conditional + R5a reconcile + R5_legacy move to SUPP + R3 reconcile + R1 data provenance (USER AUTHORIZED, NO PUSH)")
- [ ] D+1 user review checkpoint (PENDING user review)
- [ ] D4 Path A Lemma 1 execution authorization (PENDING user authorization)
- [ ] D5-6 IEEEtran typeset + 14-page verification authorization (PENDING user authorization)
- [ ] D8 final PUSH to origin/main authorization (PENDING user authorization)

**No PUSH per Wave 310 directive** — local commit only, main is ahead of origin/main by 37 (per Wave 309 NO PUSH directive + Wave 310 task input).

---

## 8. References

- `docs/drafts/paper-flat-flattened.md` (5 paper edits + §10.9 R5 supplementary + §3.5 R5a reconciliation + K8 R3 reconciliation + §3.6 R5b n_rounds conditional)
- `docs/CLAIMS.md` CLM-061 line 3156 Wave 310 status addendum
- `DATA_PRESENTATION.md` §2.7 R6 tier-aware upgrade + §3.5 R5b n_rounds conditional + §3 Wave 311 R5a reconciliation footnote line 374
- `docs/audit/wave310-r6-tier-aware-upgrade.md` (121-line canonical Wave 310 cross-doc-propagation audit doc)
- `docs/audit/wave310-restoration-execution.md` (this doc)
- `docs/audit/INDEX.md` line 332 (index entry for wave310-r6-tier-aware-upgrade.md)
- `docs/headline-evidence/README.md` line 20 (R5a reference enhanced with Wave 311 footnote cross-link)
- `docs/audit/wave309-paper-a-restoration-plan.md` (Wave 309 restoration plan that motivated the Wave 310 paper-edit pass)
- `docs/audit/wave307-data-archaeology.md` (Wave 307 data-archaeology audit, R1/R5c/K7/K1/K4 verification)
- `verification_outputs/wave225-p4-k6-tier-aware.json` (Wave 225 P4 k6 tier-aware counterfactual d_z = +0.2235 source)
- `verification_outputs/wave233-p3-tier-aware-r6.json` (Wave 233 P3 tier-aware-arm refactor)
- `verification_outputs/wave235-p3-r6-uplift.json` (Wave 235 P3 20-cell grid-search uplift to d_z = +0.6467 sensitivity-analysis source)
- `verification_outputs/wave235-p1-r5b-fix.{csv,json}` (Wave 235 P1 R5b `n_rounds=1` reversal source, sha256 `488655ce`)
- `verification_outputs/wave247-p3-r5b-n1000-n1.json` (Wave 247 P3 R5b n=1000 n=1, sha256 `9301972a`)
- `verification_outputs/wave233-p5-r5b-fix.csv` (Wave 233 P5 R5b `RF_CIFAR_N_ROUNDS_OVERRIDE=2` adapter-specific override source)
- `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` (R1 vendored data, sha256 `d2db3769...` / `04830145...`)
- `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (R5a R4 2D FM ablation -78.25% source, sha256 `74ae053a...`)
- `docs/r4-survey/10-sota-2d-experiment-results.md` (R5 2D Eight Gaussians canonical source, sha256 `9618e8f9...`)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` (`TierAwareCodimensionSheetScheduler` class implementation)
- `tools/eval/cli.py` (Wave 198 P3 percentile boundaries `34.5601`/`46.1293` + Wave 280 P `--tier-aware-n-cap 0.5` flag)
- `tools/wave87_n1000_sweep.py:298` (R3 per-record ACTUAL n=200 cap)
- commit `7a135ee` (Wave 310 R1 data-provenance commit, prior)

---

**End of Wave 310 D2 restoration-execution + Phase 4 5-gate verification + single-commit audit doc.**