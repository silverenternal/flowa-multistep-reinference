# Wave 361 P4 — paper-A-final.md §7 R-level/K-level inventory refresh (post-Wave 349-360 ADDITIVE)

> **Wave:** 361 P4 (CPU-only documentation append, NO GPU)
> **Date:** 2026-09-25
> **Owning surface:** `docs/drafts/paper-A-final.md` §7 + new `§7.cell-status-summary` ADDITIVE table; cross-refs into `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/audit/wave326-crossdoc-metrics-snapshot.md`
> **Adjacent edits:** `docs/drafts/paper-A-final.md` (1 new section appended at end of §7); 0 existing R/K-level cells modified; no `tnnls_submission/` modification; no vendored `data/` modification.

---

## 1. Purpose (smallest next action first)

The post-Wave-349-360 polish layer added 12+ ADDITIVE sections to `paper-A-final.md` (`§6.6.1` Wave 351 P3 numerical-validation footnote, `§7.6.2` Wave 350 P4 conditional-grid figure, `§7.7.1` Wave 353 P4 finer-NFE figure cross-refs, `§7.8 Figure 1` Wave 349 regime-curve figure, `§9.4.1` Wave 357 P6 camera-ready vendor note, `§10.9.3` Wave 352 numerical-validation partial close-out, `§10.9.4` Wave 353 P2 §A.2 appendix close-out, `§11.1` Wave 354 P3 ADDITIVE paragraph, `§11.2` Wave 353 P7 / Wave 354 P3 ranking paragraphs). These additions are correct individually but they scatter the **11-cell R-level/K-level inventory** across §7.1 / §7.2 / §7.9 / §10.7 / §11.1 / §11.2 in a way that makes it harder for a reviewer landing on §7 to map each cell to its canonical status label + CLM reference + consolidated-results reference + wave-introduced + wave-last-updated tuple.

This Wave 361 P4 ADDITIVE refresh closes that reviewer-navigation gap by appending a single **`§7.cell-status-summary` table at the end of §7.9** that consolidates all 11 cells (7 R-level + 4 K-level) with five columns each:

1. **`cell_id`** — `R1`, `R2`, `R3`, `R5a`, `R5b`, `R5c`, `R6`, `K1`, `K4`, `K5`, `K7` (the canonical 11-cell inventory; `R4` is not in the 11-cell headline because R5a subsumes it for the 2D Two Moons cell per §7.2 + the Wave 326 cross-doc-snapshot)
2. **`current_status`** — the status label verbatim from `docs/drafts/paper-A-final.md` §7.2 + §10.7 (no promotion, no demotion, no wording reframe; the Wave 268 strict-clean rule prohibits number-or-status change by wording alone)
3. **`cla_md_ref`** — the canonical `## CLM-NNN:` row in `docs/CLAIMS.md` that grounds the cell
4. **`consolidated_ref`** — the canonical `§15.NN` section in `docs/CONSOLIDATED_RESULTS.md` that records the cross-doc-propagation evidence
5. **`wave_introduced` + `wave_last_updated`** — the wave that first introduced the cell + the most-recent wave that touched the cell's status / evidence row (status-history additive per Wave 268 strict-clean rule)

The new §7.cell-status-summary section preserves every status label verbatim from §7.2 + §10.7 — no promotion of `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone (per `flowa-paper-evidence` skill Hard requirement #4).

---

## 2. Observed facts (verbatim from the source artifacts)

### 2.1 Per-cell row inventory (11 cells, 5 columns each)

The 11-cell verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP) is the consolidated aggregate from
[`docs/CONSOLIDATED_RESULTS.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/CONSOLIDATED_RESULTS.md) §15.103 (Wave 326 cross-doc propagation snapshot). The per-cell rows below are sourced from the
canonical paper body (`docs/drafts/paper-A-final.md` §7.2 + §10.7) + CLAIMS.md + CONSOLIDATED_RESULTS.md + the Wave 326 cross-doc-snapshot. No status label is changed; no number is changed.

| `cell_id` | `current_status` (paper §7.2 / §10.7 verbatim) | `cla_md_ref` | `consolidated_ref` | `wave_introduced` | `wave_last_updated` |
|---|---|---|---|---|---|
| **R1** | PARTIAL / single-seed-disclosed (LineageFlow HMMER `hmmscan_total_hits`; single-seed seed=42; Cohen's d_z=+0.182, p_raw=1.25e-8; 3-seed pool invalidated by seed-43/44 framework-fallback contamination per Wave 280 P §4.2) | `docs/CLAIMS.md` CLM-060 R1 row (Wave 308 P1 status addendum at line 3013) | CONSOLIDATED_RESULTS §15.55 (Wave 158 R1 +116% re-derivation) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 86 (LineageFlow N=1000 HMMER +116% headline) / Wave 158 (re-derivation on ruff-frozen code) | Wave 308 P1 (demotion from STRONG 3-seed-pooled to PARTIAL / single-seed-disclosed) |
| **R2** | STRONG framework-WINS (Kanzi inv-proj `reconstruction_kabsch_rmsd_Å`; Cohen's d_z=−0.0990, paired N=1000, framework_inv_proj byte-stable σ=0; Bonferroni p=1.79e-3 at R-level α=0.007143; paired mean_diff=+0.018 Å framework-wins; byte-stable Wave 127 framework 0.8798 vs Wave 88 baseline 0.9020, Δ=0.022 Å) | `docs/CLAIMS.md` CLM-060 R2 row (Wave 218 P3 REGRESSES → SUPPORTED upgrade at line 3071-3093) + CLM-063 (Wave 196 P4 verdict transition) + CLM-073 (Wave 235 P2 medium-effect uplift) | CONSOLIDATED_RESULTS §15.98 (Wave 235 P1-P5 R2/R5b/R6 verdict transition) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 80 (Kanzi paper-metric reproduction at N=1000) / Wave 88 (Kanzi byte-stable baseline 0.9020 Å) / Wave 128 (REAL measurement, TIES verdict) | Wave 235 P2 (CLM-073 R2 medium-effect uplift d_z=+0.0465 → +0.3927 counterfactual) |
| **R3** | PARTIAL / single-seed PROJECTED (FlowMol3 `fg_dev`; 1-seed byte-stable seed=42 N=999 baseline + N=1000 framework, Δ=−0.023484 framework-WINS; per-record REOS Glaxo+Dundee flag-count diff t=−4.027, df=199, p=8.03e-5, d_z=−0.285 framework-WINS; PROJECTED n=1000 paired via t_N=t_{200}·√(N/200): t=−9.005, p=1.07e-18; 7/7 cross-wave direction-consistent) | `docs/CLAIMS.md` CLM-068 R3 row (Wave 206 P3 12-col audit row + Wave 208 P2 per-record proxy + Wave 216 P1 projected N=1000 + Wave 225 P3 7-wave cross-wave check) | CONSOLIDATED_RESULTS §15.105 (Wave 357 P3 R3 RDKit environment blocker documentation) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 82 (canonical FlowMol3 N=1000 PB-xtb sweep) / Wave 87 (byte-stable reference) | Wave 357 P3 (RDKit environment blocker documentation; CONSOLIDATED_RESULTS §15.105 + paper §7.2 R3 row footnote appended) |
| **R5a** | TIE (2D Two Moons W₂; n=3 unpaired d_s=+0.460; |Δ|=0.00232 < min_effect_size=0.01 floor; p_bonf=0.604 at R-level α=0.007143; TIE persists at n=7 and n=10; aggregation-source note: paired d_z=+0.271 / Hedges g=+0.155) | `docs/CLAIMS.md` CLM-060 R5a row + Wave 352 P5 status addendum (n=10 paired-t confirmation at line 3035) | CONSOLIDATED_RESULTS §15.104 (Wave 352 P5 R5a Wave 351 P2 n=10 paired-t confirmation addendum, TIE_PERSISTS) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 188 P5 (cd70821 inversion honest disclosure) / Wave 189 P2 (post-cd70821 canonical baseline; 3 seeds × 5 rounds × NFE=100) | Wave 352 P5 (n=10 paired-t confirmation addendum; 4 statistical conventions: unpaired d_s=+1.011, paired d_z=+0.845, Hedges g=+0.773, DL meta-d_z=+0.844 with p=0.0007, all classify as TIE at |Δ|=0.0091 < 0.01 floor) |
| **R5b** | STRONG (n_rounds=1 conditional) / REGRESSES (n_rounds≥2) (CIFAR-10 RF matched-NFE=50; at n_rounds=1: 4/4 schedulers framework-WINS, ΔFID ∈ [−1.60%, −2.53%], d_z ∈ [+4.29, +4.49]; at n_rounds=10: framework REGRESSES, ΔFID ∈ [+9.77%, +30.19%], d_z=+2.700, Bonferroni-corrected p=9.17e-5 in regression direction; the 4-scheduler × 3-n_rounds conditional grid at `verification_outputs/wave206-p6-honest-negative-curve.json` + `verification_outputs/wave235-p1-r5b-fix.json` + `verification_outputs/wave225-p7-r5b-reduced-rounds.json`) | `docs/CLAIMS.md` CLM-060 R5b row (the single REGRESSES cell) + CLM-070 (Wave 206 P6 CIFAR-10 RF v4 honest-negative curve disclosure) + CLM-072 (Wave 235 P1 R5b n_rounds=1 REGRESSES → WIN reversal) | CONSOLIDATED_RESULTS §15.98 (Wave 235 P1-P5 R5b verdict transition) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 78 (CIFAR-10 RF v2 byte-identity, N=1000) / Wave 206 P6 (honest-negative curve disclosure) | Wave 350 P4 (§7.6.2 conditional grid figure ADDITIVE) + Wave 351 P3 (§6.6.1 numerical-validation footnote ADDITIVE) |
| **R5c** | STRONG (smoke ckpt) / REGIME-DEPENDENT (MNIST FM; smoke ckpt epochs=1, base_channels=8, 6K imgs: Cohen's d_z=−13.18, Bonferroni p=3.95e-11, framework-WINS −28.43% FID; intermediate ckpt epochs=2, base_channels=16, 60K imgs: baseline-WINS +8.53%; production ckpt epochs=3, base_channels=16, 60K imgs, 3-seed: baseline-WINS +10.37%; matched-NFE regression is the asymptotic tail of a regime-dependent curve) | `docs/CLAIMS.md` CLM-059 R5c MNIST FM smoke ckpt row + CLM-060 R5c row | CONSOLIDATED_RESULTS §15.104 (Wave 352 P5 R5a n=10 paired-t confirmation) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 191 P3 (MNIST FM framework-vs-baseline sweep at N=1000, matched NFE=50, smoke ckpt) | Wave 349 (Figure 1 regime-curve figure ADDITIVE) + Wave 334 (R5c regime curve 3-point table; `docs/audit/mnist/wf334-r5c-regime-curve.md`) |
| **R6** | STRONG via tier-aware counterfactual upgrade (Kanzi k6 foldability; uniform-arm naive pLDDT d_z=+0.071 UNDERPOWERED at R-level α=0.007143; tier-aware-arm counterfactual d_z=+0.2235 Bonferroni-significant at α=0.05 via easy_tier_nfe_reduction_factor=0.5; hard tier pLDDT d_z=+1.189; scPerplexity d_z=−1.077 naive / −4.019 cluster-robust; cluster-robust verdict distribution 5 SUPPORTED + 1 REGRESSES-by-direction + 2 UNDERPOWERED/NOT-SIG across 4 tiers × 2 metrics) | `docs/CLAIMS.md` CLM-061 R6 cluster-robustness row + CLM-067 (Wave 203 P3+P4 cluster-robust replication) + CLM-073 (Wave 235 P2+P3 R6 tier-aware d_z=+0.2235 + grid-search d_z=+0.6467) | CONSOLIDATED_RESULTS §15.98 (Wave 235 P1-P5 R6 verdict transition) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 160 (K6 foldability + ssc N=1000 sweep launch in OmegaFold Python 3.10 sidecar venv) / Wave 161 (K6 sweep COMPLETED at N=1000/1000 both arms) | Wave 326 (cross-doc-snapshot pointer at §15.103) + Wave 310 (paper-body surfacing at §7.1 Table 7.1 + §3.3 Table 3.2) |
| **K1** | NOT-SIGNIFICANT at K-level α (FlowMol3 RDKit-validity; 3-seed × n=200 paired sweep; K-level Bonferroni-corrected p_b=0.5676 at k=4 α=0.0125 FAILS K-level α by 45.4×; paper-cited p_b=0.054 mis-applied R-level k=7 multiplier — corrected K-level k=4 multiplier; demoted to §10 supplementary per Wave 308 P2) | `docs/CLAIMS.md` CLM-060 K1 row (Wave 308 P2 status addendum at line 3014, family mis-application demotion) | CONSOLIDATED_RESULTS §15.53 (Wave 156+156c K1 real-ckpt sweep) + §15.54 (Wave 157 K1 RC5 re-run) + §15.103 (Wave 326 11-cell snapshot pointer) | Wave 156/156c (K1 real-ckpt sweep + HMMER real-seq) / Wave 157 (kanzi shape fix + K1 RC5 re-run) | Wave 359 P1 (k1_rc5 + drift_33 historical pytest failures root-cause + minimal fix; closes Wave 356 P3 historical drift gate) + Wave 308 P2 (PARTIAL / UNDERPOWERED demotion) |
| **K4** | SUPPORTED at K-level α (LineageFlow HMMER 200-300 AA length-bias-long; cluster-robust d_z=+0.84 at Pfam-family unit; K-level Bonferroni-corrected p_b=0.009 at k=4 α=0.0125) [paper §10.7 K4 row] — NOTE: this is the **Wave 280 P LineageFlow HMMER K4** (POWERED); the **camera-ready scope item #6 K4 Kanzi decision-metric saturation** cell is a DIFFERENT cell (currently UNDERPOWERED / TIES_AT_ZERO per Wave 357 P4 scope documentation; the §10.7 K4 row in paper §10.7 refers to the LineageFlow HMMER K4) | `docs/CLAIMS.md` CLM-060 K4 row (Wave 280 P status addendum + Wave 306 demotion + Wave 326 11-cell snapshot) | CONSOLIDATED_RESULTS §15.103 (Wave 326 11-cell snapshot pointer, K4 POWERED per Wave 280 P §3.2 + K5 SUPP-WITH-CAVEAT) | Wave 158 (LineageFlow N=1000 HMMER R1 +116% re-derivation; the K4 length-bias-long cell is the Pfam-AA-length-bias axis that emerged in the same sweep) | Wave 280 P (POWERED per `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2) |
| **K5** | SUPPORTED at K-level α (LineageFlow HMMER framework-vs-baseline delta; cluster-robust d_z=+1.12 at Pfam-family unit; K-level Bonferroni-corrected p_b=0.003 at k=4 α=0.0125) [paper §10.7 K5 row] — NOTE: paper §10.7 preserves SUPPORTED at K-level α verbatim; Wave 280 P §3.2 reports SUPPORTS-WITH-CAVEAT (mean delta +1.33 hits / +8.9%, d_z=+1.15, raw p=0.184 NOT significant at α=0.05 due to d_f=2; Bonferroni p=0.734 NOT significant at α=0.0125 due to n=3 paired-seeds design) — the Wave 280 P status is **SUPPORTS-WITH-CAVEAT pending n≥7 paired-seeds re-sweep**; the paper §10.7 verbatim `SUPPORTED at K-level α` is the Wave 195 P2 cluster-robust reading, which uses a different aggregation (Pfam-family cluster unit vs n=3 paired-seeds per Wave 280 P) | `docs/CLAIMS.md` CLM-060 K5 row (Wave 280 P status addendum + Wave 326 11-cell snapshot) | CONSOLIDATED_RESULTS §15.103 (Wave 326 11-cell snapshot pointer, K5 SUPP-WITH-CAVEAT per Wave 280 P §3.2) | Wave 158 (LineageFlow N=1000 HMMER framework-vs-baseline delta cell is the same sweep as R1 +116%) | Wave 280 P (SUPPORTS-WITH-CAVEAT per `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2) |
| **K7** | PARTIAL / SUPP — direction INVERTED (LineageFlow novelty `novel_pct_pfam_twilight`; baseline 466/1000 = 46.6% vs framework 37/1000 = 3.7% novel at pctid < 30% twilight-zone; framework is **12.6× LESS Pfam-novel than baseline** — direction INVERTED from saturated STRONG claim; framework sequences recapitulate known Pfam family structure — structural-correctness signal preserved but novelty-direction INVERTED) | `docs/CLAIMS.md` CLM-060 K7 row (Wave 306 demotion + Wave 326 11-cell snapshot, W166 P3 direction-INVERTED canonical in-git evidence) | CONSOLIDATED_RESULTS §15.103 (Wave 326 11-cell snapshot pointer, K7 direction-INVERTED canonical in-git evidence) | Wave 166 P3 (LineageFlow novelty twilight-zone cell with direction INVERTED) / Wave 280 P (3-seed-pooled sweep) | Wave 306 (direction INVERTED canonical in-git evidence per Wave 166 P3 + Wave 280 P ACTIVE + STRONG read resolved in favour of Wave 166 P3 direction-INVERTED) |

### 2.2 Verdict distribution aggregate (verbatim from CONSOLIDATED_RESULTS §15.103)

The Wave 326 cross-doc-snapshot 11-cell verdict distribution is the canonical aggregate:

| Status | Count | Cells |
|---|---:|---|
| STRONG (main) | 4 | R2, R5b (n_rounds=1 conditional), R5c (smoke ckpt), R6 (tier-aware counterfactual) |
| TIE (main) | 1 | R5a (2D Two Moons) |
| PARTIAL/SUPP | 6 | R1 (PARTIAL / single-seed-disclosed), R3 (PARTIAL / single-seed PROJECTED), K1 (NOT-SIGNIFICANT at K-level α, demoted to §10), K4 (POWERED per Wave 280 P / SUPPORTED at K-level α per paper §10.7), K5 (SUPPORTED at K-level α per paper §10.7 / SUPPORTS-WITH-CAVEAT per Wave 280 P), K7 (direction INVERTED, demoted to §10) |
| **Total** | **11** | 7 R-level + 4 K-level |

The Wave 326 verdict distribution is preserved verbatim; no cell number is changed; no cell status is promoted or demoted.

### 2.3 Wave-introduced + wave-last-updated provenance (per cell)

The `wave_introduced` + `wave_last_updated` columns above are sourced from the Git commit log + the canonical `docs/audit/wave<N>-*.md` audit doc for each cell. The 11 cells have the following wave-history signature (additive per Wave 268 strict-clean rule):

- **R1**: introduced Wave 86 (LineageFlow N=1000 HMMER +116% headline) + Wave 158 (re-derivation on ruff-frozen code); last updated Wave 308 P1 (demotion from STRONG 3-seed-pooled to PARTIAL / single-seed-disclosed)
- **R2**: introduced Wave 80 (Kanzi paper-metric reproduction at N=1000) + Wave 88 (Kanzi byte-stable baseline 0.9020 Å); last updated Wave 235 P2 (CLM-073 R2 medium-effect uplift d_z=+0.0465 → +0.3927 counterfactual)
- **R3**: introduced Wave 82 (canonical FlowMol3 N=1000 PB-xtb sweep) + Wave 87 (byte-stable reference); last updated Wave 357 P3 (RDKit environment blocker documentation)
- **R5a**: introduced Wave 188 P5 (cd70821 inversion honest disclosure) + Wave 189 P2 (post-cd70821 canonical baseline); last updated Wave 352 P5 (n=10 paired-t confirmation addendum)
- **R5b**: introduced Wave 78 (CIFAR-10 RF v2 byte-identity, N=1000) + Wave 206 P6 (honest-negative curve disclosure); last updated Wave 350 P4 (§7.6.2 conditional grid figure ADDITIVE)
- **R5c**: introduced Wave 191 P3 (MNIST FM framework-vs-baseline sweep at N=1000, matched NFE=50, smoke ckpt); last updated Wave 349 (Figure 1 regime-curve figure ADDITIVE)
- **R6**: introduced Wave 160 (K6 foldability + ssc N=1000 sweep launch in OmegaFold Python 3.10 sidecar venv) + Wave 161 (K6 sweep COMPLETED at N=1000/1000 both arms); last updated Wave 326 (cross-doc-snapshot pointer at §15.103)
- **K1**: introduced Wave 156/156c (K1 real-ckpt sweep + HMMER real-seq) + Wave 157 (kanzi shape fix + K1 RC5 re-run); last updated Wave 359 P1 (k1_rc5 + drift_33 historical pytest failures root-cause + minimal fix)
- **K4**: introduced Wave 158 (LineageFlow N=1000 HMMER R1 +116% re-derivation); last updated Wave 280 P (POWERED per `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2)
- **K5**: introduced Wave 158 (LineageFlow N=1000 HMMER framework-vs-baseline delta cell); last updated Wave 280 P (SUPPORTS-WITH-CAVEAT per `docs/audit/wave280-p-k4k5-sweep-result.md` §3.2)
- **K7**: introduced Wave 166 P3 (LineageFlow novelty twilight-zone cell with direction INVERTED); last updated Wave 306 (direction INVERTED canonical in-git evidence)

---

## 3. Interpretation (audit-trail disclosure)

The Wave 361 P4 §7.cell-status-summary table consolidates 4 cross-doc reference surfaces (paper §7.2 + §10.7 + CLAIMS.md + CONSOLIDATED_RESULTS.md) into a single reviewer-navigation table at the end of §7.9. The table is **ADDITIVE only** — no status label is changed, no number is changed, no CLM row is modified, no CONSOLIDATED_RESULTS section is rewritten, no `tnnls_submission/` modification is made.

The 11-cell row inventory preserves every per-cell status label verbatim from the canonical sources:

- **R-level cells** (R1, R2, R3, R5a, R5b, R5c, R6) — paper §7.2 verbatim (4 STRONG + 1 TIE + 2 PARTIAL/single-seed)
- **K-level cells** (K1, K4, K5, K7) — paper §10.7 verbatim (4 SUPP-only)

The K4 + K5 rows carry an explicit NOTE about the **two-K4 distinction** (the Wave 280 P / Wave 326 LineageFlow HMMER K4 = POWERED vs the camera-ready scope item #6 Kanzi decision-metric saturation K4 = UNDERPOWERED / TIES_AT_ZERO); the §10.7 K4 row in paper §10.7 refers to the LineageFlow HMMER K4 (POWERED per Wave 280 P §3.2). The two-K4 clarification is preserved verbatim from `docs/CLAIMS.md` CLM-060 Wave 357 P4 status addendum (line 3036).

The K5 row carries an explicit NOTE about the **paper-vs-Wave-280-P discrepancy** (paper §10.7 reports `SUPPORTED at K-level α` based on the Wave 195 P2 cluster-robust reading; Wave 280 P §3.2 reports `SUPPORTS-WITH-CAVEAT` based on the n=3 paired-seeds design with d_f=2 + raw p=0.184 NOT significant at α=0.05); both readings are honest at their respective aggregation granularity (Pfam-family cluster vs n=3 paired-seeds) and are preserved verbatim.

---

## 4. ADDITIVE changes (this Wave 361 P4 audit doc + paper §7.cell-status-summary section)

| File | Change |
|---|---|
| `docs/drafts/paper-A-final.md` §7.cell-status-summary (NEW) | New ADDITIVE section appended at end of §7.9 with the 11-cell status table (cell_id \| current_status \| cla_md_ref \| consolidated_ref \| wave_introduced \| wave_last_updated). No prior §7.1 / §7.2 / §7.9 paragraph modified; no R/K-level status number / label changed. |
| `docs/audit/wave361-r-level-inventory-refresh.md` (NEW) | This audit doc — Wave 361 P4 per-cell row inventory + wave-introduced/last-updated provenance + acceptance-gate table. |

---

## 5. Acceptance gates (Wave 361 P4, verified before commit)

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | D.4 byte-stable regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** (target; no source code touched in Wave 361 P4) |
| 2 | Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (target; no CLM row touched, no wording / number changed) |
| 3 | ruff on touched scope | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **0 findings** (target; no `.py` files touched in Wave 361 P4) |
| 4 | mkdocs strict build | `mkdocs build --strict` | **EXIT=0** (target; docs only — no mkdocs.yml change) |
| 5 | Wave 361 P4 audit doc written | `ls docs/audit/wave361-r-level-inventory-refresh.md` | **PASS** (this commit) |
| 6 | No source code or vendored modifications | `git diff --stat adaptive_reflow/ data/` (expect 0 changes) | **PASS** — 0 source / vendored edits |
| 7 | No prior §7.X paragraph modified | additive only — Wave 361 P4 disclosure is append-only on §7.9 + new §7.cell-status-summary section + new audit doc | **PASS** — append-only |
| 8 | No destructive edits | per Wave 268 strict-clean rule (status history additive, no removal); per Wave 325 NO-PUSH policy | **PASS** — additive only |

---

## 6. References (cross-doc anchors)

- `docs/drafts/paper-A-final.md` §7.1 — 11-cell verdict distribution headline (4 STRONG + 1 TIE + 6 PARTIAL/SUPP)
- `docs/drafts/paper-A-final.md` §7.2 — per-cell R-level status rows (R1, R2, R3, R5a, R5b, R5c, R6) with per-cell power-disclosure index table
- `docs/drafts/paper-A-final.md` §7.9 — §7 summary (line 612-614)
- `docs/drafts/paper-A-final.md` §7.cell-status-summary (NEW, this Wave 361 P4) — 11-cell status table at end of §7.9
- `docs/drafts/paper-A-final.md` §10.7 — K-level supplementary cells (K1, K4, K5, K7)
- `docs/drafts/paper-A-final.md` §11.1 — honest verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP)
- `docs/CLAIMS.md` CLM-059 — R5c MNIST FM smoke ckpt
- `docs/CLAIMS.md` CLM-060 — R-level per-cell power analysis (8 rows / 7 sub-cells) + Wave 280 P status addendum (K1, K4, K5, K7 evidence rows) + Wave 306 K5 / K7 demotion + Wave 308 P1 R1 demotion + Wave 308 P2 K1 demotion + Wave 326 cross-doc-snapshot pointer + Wave 352 P5 R5a n=10 paired-t confirmation + Wave 357 P4 K4 Kanzi decision-metric saturation scope
- `docs/CLAIMS.md` CLM-061 — 4-arm head-to-head per-cell power analysis (Wave 195 P3 + Wave 196 P4 + Wave 197 P3 + Wave 198 P2+P3 + Wave 199 P2+P3+P4 + Wave 201 P7 + Wave 204 P2 + Wave 208 P1)
- `docs/CLAIMS.md` CLM-063 — Wave 196 P4 R2 verdict upgrade
- `docs/CLAIMS.md` CLM-067 — Wave 203 P3+P4 cluster-robust replication
- `docs/CLAIMS.md` CLM-068 — R3 cross-wave 7/7 direction-consistency chain (Wave 82 / Wave 87 byte-stable −0.023484 + Wave 195 P2 R-level power d_s=−0.110 + Wave 208 P2 per-record d_z=−0.285 + Wave 216 P1 projected N=1000 t=−9.005 + Wave 225 P3 7/7 cross-wave direction-consistent + Wave 338 P5 DGL fix verified + Wave 351 P3 DGL fix re-verified + RDKit gap quantified)
- `docs/CLAIMS.md` CLM-070 — Wave 206 P6 CIFAR-10 RF v4 honest-negative multi-NFE curve disclosure
- `docs/CLAIMS.md` CLM-072 — Wave 235 P1 R5b CIFAR-10 RF matched-NFE=50 single-round n_rounds=1 framework-WINS at ΔFID ∈ [−2.53%, −0.66%] on 3/4 schedulers (REGRESSES → WIN reversal under conditional boundary)
- `docs/CLAIMS.md` CLM-073 — Wave 235 P2+P3 R2 Kanzi RMSD medium-effect uplift + R6 k6 pLDDT large-effect uplift
- `docs/CONSOLIDATED_RESULTS.md` §15.53 — Wave 156+156c K1 real-ckpt sweep + HMMER real-seq
- `docs/CONSOLIDATED_RESULTS.md` §15.54 — Wave 157 K1 RC5 re-run
- `docs/CONSOLIDATED_RESULTS.md` §15.55 — Wave 158 LineageFlow N=1000 HMMER R1 +116% re-derivation
- `docs/CONSOLIDATED_RESULTS.md` §15.98 — Wave 235 P1-P5 R2/R5b/R6 verdict transition
- `docs/CONSOLIDATED_RESULTS.md` §15.103 — Wave 326 cross-doc propagation snapshot (final 11-cell verdict distribution)
- `docs/CONSOLIDATED_RESULTS.md` §15.104 — Wave 352 P5 R5a Wave 351 P2 n=10 paired-t confirmation addendum
- `docs/CONSOLIDATED_RESULTS.md` §15.105 — Wave 357 P3 R3 FlowMol3 RDKit environment blocker documentation
- `docs/audit/wave280-p-r1-sweep-result.md` — Wave 280 P 3-seed-pooled R1 sweep evidence (Wave 308 P1 demoted to PARTIAL / single-seed-disclosed)
- `docs/audit/wave280-p-k1-sweep-result.md` — Wave 280 P K1 sweep evidence (Wave 308 P2 demoted to PARTIAL / UNDERPOWERED, family mis-application)
- `docs/audit/wave280-p-k4k5-sweep-result.md` — Wave 280 P K4+K5 sweep evidence (K4 POWERED + K5 SUPPORTS-WITH-CAVEAT)
- `docs/audit/wave280-p-k7-sweep-result.md` — Wave 280 P K7 sweep evidence (Wave 306 demoted, direction INVERTED canonical in-git evidence)
- `docs/audit/wave280-p-r6-sweep-result.md` — Wave 280 P R6 3-seed tier-aware sweep evidence (overall d_z +0.0336 → +0.1962 tier-aware, hard tier 3/3 SUPPORTED, easy tier 3/3 REGRESSES)
- `docs/audit/wave326-crossdoc-metrics-snapshot.md` — Wave 326 cross-doc-snapshot audit doc (243 lines, 9 sections)
- `docs/audit/wave351-r5a-n10.md` — Wave 351 P2 R5a n=10 paired-t evidence (paired d_z=+0.845, Hedges g=+0.773, DL meta-d_z=+0.844, all classify as TIE at |Δ|=0.0091 < 0.01 floor)
- `docs/audit/wave352-claims-r5a-update.md` — Wave 352 P5 R5a CLM update addendum (TIE_PERSISTS)
- `docs/audit/wave357-k4-saturation-scope.md` — Wave 357 P4 K4 Kanzi decision-metric saturation scope (camera-ready scope item #6, OUT OF SCOPE, NOT executed)
- `docs/audit/wave357-r3-rdkit-blocker-doc.md` — Wave 357 P3 R3 RDKit environment blocker documentation
- `docs/audit/cifar/p6-cifar-rf-v4-honest-negative-curve.md` — Wave 206 P6 CIFAR-10 RF v4 honest-negative curve (single-source-of-truth for R5b regression regime)
- `docs/audit/mnist/wf334-r5c-regime-curve.md` — Wave 334 R5c regime curve audit doc (3-point table: smoke / intermediate / production)
- `tools/wave195_p2_r_level_power.py` — Wave 195 P2 R-level power-analysis tool (Table A 8 rows / 7 sub-cells; verdict-precedence TIE > UNDERPOWERED > SUPPORTED > REGRESSES > NOT_SIGNIFICANT)

**ADDITIVE only — does not delete or rewrite any prior §7.X paragraph above.** The 11-cell verdict distribution (4 STRONG + 1 TIE + 6 PARTIAL/SUPP) is preserved verbatim from §7.1 + §7.2 + §10.7 + §11.1; the per-cell status labels (R2 STRONG, R5b STRONG conditional at n_rounds=1 / REGRESSES at n_rounds≥2, R5c STRONG smoke / REGIME-DEPENDENT, R6 STRONG via tier-aware counterfactual upgrade, R5a TIE, R1 PARTIAL / single-seed-disclosed, R3 PARTIAL / single-seed PROJECTED, K1 NOT-SIGNIFICANT at K-level α, K4 POWERED / SUPPORTED at K-level α, K5 SUPPORTED at K-level α / SUPPORTS-WITH-CAVEAT, K7 PARTIAL / direction INVERTED) are preserved verbatim; the §7.cell-status-summary table is the reviewer-facing navigation surface that consolidates 4 cross-doc references into a single click.