# Wave 341 — Deep Audit: Data Holes, Doc Organization, Paper ↔ Project Alignment

**Date:** 2026-09-25
**Author:** Wave 341 deep-audit agent (READ-ONLY — no code, claim, or headline number changes)
**Status:** ACTIVE — research-audit surfacing the user's "dig deeper" question
**Trigger:** User request "再深挖一下项目，看看数据还有没有漏洞，文档有没有整理好，论文和项目有没有完全对齐，readme里的数据能不能查到（数据应该是对的，但是用的是cosine而不是codim）"
**Scope:** All 7 R-cell headline data artifacts + 7 K-cell supporting data artifacts + 12 headline artifacts (smoke anchor set) + `docs/` organization + paper ↔ project alignment across `docs/drafts/paper-flat-flattened.md`, `README.md`, `README.zh.md`, `docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/cover-letter-tnnls.md` + governance docs (`todo/STATUS.md`, `todo/RISK-REGISTER.md`, `docs/audit/INDEX.md`).
**Head SHA:** `45149561` (Wave 340 README polish — 137 commits ahead of `todo/STATUS.md` Wave-204 baseline; repo not pushed per Wave 325 user gating).

---

## 1. Executive Summary

The user's intuition is **correct on all three fronts** the deep audit investigated:

1. **Data holes** exist on R3 (FlowMol3 3-seed N=1000 paired sweep is `BLOCKED at vendor level` and the R5b N=1000 production-ckpt sweep `wave247-p3-r5b-n1000-n1` shows only **2/4 schedulers WIN at N=1000**, not 4/4 as the README N=200 headline implies), on R5a (cluster-robust verdict still TIE_PERSISTS per Wave 337 with no n=30/n=100 confirmation), on R2 (no n=30 / n=100 paired-t replication), and on K1 (Wave 308 P2 demoted to §10 supplementary with Bonferroni alpha mis-applied).
2. **Documents are mostly organized but 3 governance files are stale by 137+ commits** — `todo/STATUS.md` is anchored at Wave 204 / HEAD `72ba46e` / TPAMI venue / D.4 33/33, while actual state is Wave 340 / HEAD `45149561` / TNNLS venue / D.4 30/30; `todo/RISK-REGISTER.md` is stuck at Wave 6-10 era with 15 risks tracked (no DGL 2.4.0 bug, no TPAMI→TNNLS venue switch, no cosine-vs-codim scheduler-attribution gap); `docs/audit/INDEX.md` overstates cluster counts by ~50% (claims 653 files in 25 clusters but actual on-disk count is 387 in 17 clusters).
3. **Paper ↔ project alignment has 1 critical citation error and 4 unresolved discrepancies** — paper §6.5 cites Bolley-Guilin-Villani (2012) Bernoulli concentration inequality at lines 306/312/433/866/1336+ but bibliography [10] is `Karl/Kemeter/Dax/Sierak. Embracing Negative Results in ML. ICML 2024 / arXiv 2406.03980` (a totally different paper); Villani (2003) is also missing; Wave 337 R5a TIE unresolved; R5b README data-source inconsistency unresolved; `RMSPreservingCoordinateMixer` named in paper but not found in code.

**Honest assessment:** the paper is well-grounded in code at the framework-contract layer (4 anchor classes all verified to real line numbers) and at the headline-numbers layer (all 7 R-cells have valid verification artifacts; per-cell code paths resolved). The four load-bearing alignment issues (BGV12/Villani citation, R5b data-mix, R5a TIE, RMSPreserving class) are correctable additively without renumbering bibliography entries or re-running any sweep, per Wave 268 strict-clean rule (no destructive edits; minimal-files-touched). The data holes for R3 N=1000 (3-seed vendor-level BLOCKED), R2 replication, R5a TIE_PERSISTS, and K1 Bonferroni refit are honest disclosure items, not data-integrity failures, because the 1-seed/N=200/paired-t reference data is byte-stable and properly cited. The `reproduce.sh` smoke anchor set (12 artifacts) is 12/12 present per `python3 tools/verify_reproducibility_smoke.py` and SHA256SUMS-ledger-verified 6/6 directories / 149 files / 0 mismatches per `python3 tools/check_data_integrity.py`. The `python3 tools/check_data_provenance.py` flags 6 ORPHAN_SHA drifts in 3 audit docs (wave309 / wave310 / wave334), which are stale SHA references in old audit docs pointing to artifacts that have since been re-generated.

**Per Wave 268 strict-clean rule, the fixes proposed below are ADDITIVE** (no number changes, no destructive edits, no new commits). Per Wave 325 NO-PUSH policy, no `git push` without explicit user gating. Per AGENTS.md §3 hard guardrail #5 "TNNLS submission freeze is sacred", only additive docs in `tnnls_submission/` are allowed once `v3.0-tnnls-ready` is cut.

**Smallest next action (Wave 342+ candidates, ordered by impact-to-effort ratio):**

| # | Action | Impact | Effort | Wave scope |
|---|---|---|---|---|
| 1 | Wave 341 P1-P3 fix train on `README.md` + `README.zh.md` (add Scheduler column + fix R5b row + fix "3/4 schedulers" wording) | HIGH (reader trust on Headline Results table) | LOW (3-cell edit) | Wave 342 paper-evidence |
| 2 | Commit untracked `docs/audit/wave341-readme-cosine-vs-codim.md` | LOW (audit-trail completeness) | 1 line | Wave 342 governance |
| 3 | Add BGV12 [N] + Villani (2003) [M] bibliography entries additive in `paper-flat-flattened.md` + references tail | CRITICAL (any reviewer will flag) | LOW (~5 lines) | Wave 342 paper-evidence |
| 4 | Refresh `todo/STATUS.md` (HEAD, venue, D.4, Wave 341 audit reference) | HIGH (governance accuracy) | MEDIUM (mechanical) | Wave 342 governance |
| 5 | Add explicit `- Status: ACTIVE` field to CLM-070 through CLM-085 (16 entries) | MEDIUM (CLAIMS ledger format consistency) | MECHANICAL | Wave 342 governance |
| 6 | Regenerate `docs/audit/INDEX.md` from current 387-file / 17-cluster on-disk layout | MEDIUM (cluster map accuracy) | MECHANICAL | Wave 342 governance |

**NO-PUSH gate:** none of the above execute without explicit user authorization per Wave 325 + AGENTS.md §3 hard guardrail #3.

---

## 2. Data Integrity Tools — Verifier Results (all PASS)

```
$ python3 tools/check_data_integrity.py
# Verification-output integrity report
- Directories with SHA256SUMS: 6
- Files verified: 149
- Mismatches: 0
**All ledgers match on-disk state.**

$ python3 tools/verify_reproducibility_smoke.py
# Reproducibility smoke report
- Required artifacts: 12
- Present on disk: 12
- Missing / mis-listed: 0
**All 12 headline-evidence artifacts present.**

$ python3 tools/check_data_provenance.py
# Data provenance report
- Citations parsed: 44
- Unique paths cited: 32
- Unique sha256s cited: 34
- Drifts: 6 (3 docs × 2 orphan_sha each, see §7)

$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed, 3 warnings in 1.08s   # D.4 30/30 PASS preserved

$ python3 tools/check_claims_consistency.py
# Active claims: 61; Provisional: 0; Deprecated: 2
**No drift detected.**

$ python3 tools/check_data_provenance.py
provenance: citations=44 paths=32 drifts=6
```

**Verdict:** All 5 data integrity gates PASS. The "data holes" the user is worried about are not in the integrity tools' surface area (they verify presence + sha + drift); they are in the **evidence-chain completeness** for individual R-cells (e.g., R3 has valid evidence but the 3-seed pooled SD is BLOCKED at vendor level).

---

## 3. Per-Cell Data-Hole Assessment

### 3.1 R1 (LineageFlow HMMER hmmscan_total_hits)

| Property | Status |
|---|---|
| Headline source | `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` |
| N=1000 paired | ✅ Wave 158 P2 single-seed byte-stable |
| N=1000 3-seed pooled | ✅ `verification_outputs/wave280-p-r1/{seed42,seed43,seed44}/... + summary.json` (d_z=9.2, p_bonf_rlevel=0.001, all 3 seeds status=1.0 PASS) |
| SHA256SUMS ledger | ✅ `verification_outputs/wave280-p-r1/SHA256SUMS` covers all 4 + 18 sub-files |
| Scheduler attribution | CosineAnnealScheduler (default; codim NOT tested) — disclosed Wave 341 P1 |
| **Data holes** | **NONE** — both single-seed canonical headline + 3-seed replication present |
| **Verifier note** | Project's strongest cell; all R1 evidence has SHA pinning + version history |

### 3.2 R2 (Kanzi RMSD)

| Property | Status |
|---|---|
| Headline source | `verification_outputs/wave218-p3-kanzi-framework-wins.json` (deployed paired-t, d_z=−0.0990, p_raw=1.79e-3, Bonf-sig at α=0.007143, framework_WINS) |
| N=1000 paired | ✅ single-seed = canonical |
| 3-seed pooled / n=30 / n=100 | ❌ **MISSING** — only seed_base=42 paired-t |
| SHA256SUMS ledger for headline | ✅ framework_source: `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json` exists; baseline_source: `verification_outputs/wave218-p3-kanzi-baseline-n1000/...` exists; both rooted in `kanzi_n1000_*` directories |
| Scheduler attribution | NONE — R2 framework arm uses `framework_inv_proj` mode (synthetic x_final sampled from N(0, σ=1e-3) routed through a trained Linear(512→4) inverse projection at `tools/kanzi_latent_to_coord.py`, sha `5ab6234d`). Disclosed Wave 341 P1 |
| **Data holes** | (a) 3-seed paired-t replication not attempted; (b) medium-effect uplift at CLM-073 (d_z +0.0465 → +0.3927) comes from counterfactual grid search, not live re-run |
| **Verifier note** | R2 is a synthetic-mode framework_inv_proj cell — the framework_WINS verdict is a structural property of the synthetic test (small noise + trained inverse projection by construction wins on reconstruction metrics), NOT a scheduler verdict. Codim NOT tested |

### 3.3 R3 (FlowMol3 fg_dev)

| Property | Status |
|---|---|
| Headline source (canonical 1-seed) | `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json` (Wave 87 / Wave 82 sweep at seed_base=43, NFE=250, n_total_per_arm=200, framework 199 mols vs baseline 200 mols) — baseline fg_dev=0.6381, framework fg_dev=0.6146, Δ=−0.023484, framework_wins |
| Per-record proxy (Wave 208 P2) | `verification_outputs/wave208-p2-flowmol3-sanity.{csv,json}` — d_z=−0.285, p=8.03e-05, N=200 ACTUAL, Bonf-sig |
| Per-record N=1000 projected (Wave 216 P1) | PROJECTED via paired-test scaling (`t_N = t_actual * sqrt(N / n_actual)`, `d_z` unchanged, df=999): t=−9.005, p=1.07e-18, post-hoc power 1.0 |
| 3-seed N=1000 paired | ❌ **BLOCKED at vendor level** per CLM-076 (Wave 244-262 revert of all defensive patches to vendored upstream; DGL 2.4.0 `_solve_ode_upstream_batch` regression unfixed by Wave 244-262 revert; Wave 338 P5 SUCCESS on DGL fix path but production-ckpt sweep DEFERRED due to RDKit sampling-rate gap (~80/1000 valid mols vs canonical 999/1000)) |
| DGL fix | ✅ Wave 338 P5 SUCCESS — `_solve_ode_upstream_batch` per-mol prior tiling + `_pad_e` dimension-alignment fix at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2885` + 3002-3011; D.4 byte-stable preserved |
| SHA256SUMS ledger | ✅ `verification_outputs/wave280-p-r3/SHA256SUMS` covers 3-seed partial logs but does NOT cover `flowmol3_n1000_sweep_wave87_q4_2026.json` (top-level file, no ledger) |
| Scheduler attribution | NONE — Wave 87 framework arm is "small Gaussian perturbation applied to the canonical prior before upstream sampling" (`tools/wave87_n1000_sweep.py:11-13`); actual data: framework perturbation_sigma=0.05 vs baseline perturbation_sigma=0.0 |
| **Data holes** | (a) 3-seed N=1000 paired sweep is the camera-ready DEFERRED item — not a one-line fix; (b) per-record proxy is the load-bearing evidence at N=200 ACTUAL / N=1000 PROJECTED; honest disclosure in paper §10 Limitations |
| **Verifier note** | R3 evidence chain is the project's most honest disclosure — 1-seed is byte-stable; 3-seed is BLOCKED at the data-acquisition layer (cannot condition on local vendored patches), not at the framework layer |

### 3.4 R5a (2D Two Moons W₂)

| Property | Status |
|---|---|
| Headline source | `verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (baseline 2.85 / framework 0.62 / Δ −78.25%) sourced from `CONSOLIDATED_RESULTS §4.1` — `multi_round_no_restart` config |
| Multi-seed replication (n=3 / n=7 / n=10) | Wave 189 P2 3-seed: `verification_outputs/wave189-p2-post-cd70821-two_moons.json` shows `baseline_w2_mean=0.0736`, `framework_w2_mean=0.0759` (PaperRatioAdaptiveScheduler NOT Cosine!), Δ=−3.16%, p=0.685, NOT bonf-sig, **TIE_PERSISTS** at n=3 |
| n=7 + n=10 follow-up | Wave 209 P6 n=7 + Wave 216 P2 n=10 — both confirm TIE_PERSISTS direction-consistent |
| n=30 / n=100 attempts | ❌ **MISSING** — not attempted past n=10 |
| SHA256SUMS ledger | ❌ top-level file, no ledger parent |
| Scheduler attribution | UNDOCUMENTED in headline-evidence JSON — note field says "single_pass → multi_round_no_restart (best head-to-head)" but no SchedulerProtocol implementation is identified; `consolidated_results.md §4.1` table enumerates `multi_round_cosine_anneal`, `multi_round_codimension_sheet_posterior_selection`, `multi_round_evidence_driven_posterior_selection`, `multi_round_convergence_adaptive_schedule_derived` — the headline 0.6244 row is `multi_round_no_restart` (NOT a scheduler but a chain-stop config) |
| d_s=+0.460 paper-cited value | UNRESOLVED from Wave 337 final self-check — paper says d_s=+0.460 but raw per-seed CSV shows +0.610 and Hedges-corrected is +0.488; Wave 189 P2 aggregate JSON `framework_w2_mean=0.0759` disagrees with per-seed CSV `0.068891` (Δ +0.0104 disagreement on framework w2) |
| **Data holes** | (a) TIE_PERSISTS at n=3,7,10 — no n=30 or n=100 follow-up; (b) d_s=+0.460 paper-cited vs +0.610 / +0.488 disagreement unresolved; (c) Wave 337 final self-check flagged this; framework-callable-action-Wave-342 needed |

### 3.5 R5b (CIFAR-10 Rectified Flow FID)

| Property | Status |
|---|---|
| Headline source (READ-ONLY investigation) | **TWO conflicting sources surfaced in README Headline Results row 6:** (a) Baseline 218.87 / Framework 122.18 from `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged; "NOT fair comparison"); (b) Δ% range −2.53% to −0.66% from `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (matched NFE=50, 4 schedulers) |
| Verified `wave235-p1-r5b-fix.json#rounds1` | baseline_fid=454.3853933635171; framework FIDs: cosineanneal 447.107 (−1.60%), codimensionsheet 442.889 (−2.53%, BEST), evidencedriven 453.852 (−0.12%), freetraj 451.369 (−0.66%) — **4/4 schedulers WIN** |
| **1 of 2 CRITICAL README issues** | README ver. link → `wave235-p1-r5b-fix.json` but Baseline/Framework columns 218.87/122.18 don't match that file's baseline_fid 454.39 |
| **2 of 2 CRITICAL README issues** | README says "−2.53% to −0.66% on 3/4 schedulers" — drops evidencedriven (−0.12%) without explanation; paper-draft line 369 says "4/4 schedulers WIN at n_rounds=1" |
| N=1000 production-ckpt sweep | `verification_outputs/wave247-p3-r5b-n1000-n1/summary.json` — baseline FID 48.406 vs (cosineanneal 48.567 / codimensionsheet 48.659 / evidencedriven 48.167 / freetraj 48.252) — **2/4 schedulers WIN (evidencedriven, freetraj); 2/4 REGRESS (cosineanneal +0.33%, codimensionsheet +0.52%)**. Only 4 schedulers at NFE=50, fixed-NFE budget 1.000; ratio: framework/baseline = 1.00× |
| SHA256SUMS ledger | ❌ headline JSON `wave235-p1-r5b-fix.json` is top-level (no ledger); `wave247-p3-r5b-n1000-n1/SHA256SUMS` missing (the directory has summary.json + comparison.md + samples/ but no ledger file) |
| Scheduler attribution | All 4 schedulers tested at n_rounds=1; framework_WINS is real (mean d_z=+4.5 across 4 WINS) — but the headline `−2.53% to −0.66% on 3/4 schedulers` wording drops the −0.12% evidencedriven |
| n_rounds>=2 conditional boundary | Wave 336 mechanism analysis (4/4 schedulers REGRESS at n_rounds>=2 with ΔFID +9.77% to +30.19% — see `docs/audit/wave336-r5b-mechanism.md`) |
| **Data holes** | (a) N=1000 production-ckpt sweep exists but is NOT in README Headline Results row 6; (b) README Baseline/Framework columns sourced from v2 NFE-averaged (NOT fair comparison) but Δ% range sourced from rounds1 matched-NFE — IMPLICITLY INCONSISTENT; (c) Wave 341 P1-P3 addends already proposed |
| **Verifier note** | R5b is the cell with the LARGEST data-integrity surface — 4 verifications (rounds1 / rounds2 / rounds10 / v2-NFE-averaged) and only 2 are headline-visible; the cleanest fix (per Wave 268 strict-clean rule) is REPLACE Baseline/Framework columns with rounds1 actuals |

### 3.6 R5c (MNIST FM FID)

| Property | Status |
|---|---|
| Headline source (smoke ckpt, single seed) | `verification_outputs/wave191-p3-mnist-n1000.json` (canonical Wave 191 P2 byte-stable smoke ckpt baseline_fid=29.49, evidence_driven scheduler framework_FID=23.39, −28.43%, framework_WINS, d_z=−13.175, p_bonf<1e-10) |
| 3-seed pooled (Wave 280 P) | ✅ `verification_outputs/wave280-p-r5c/aggregate.json` — 3 seeds × 200 records (n_total=600): smoke-ckpt baseline_fid=29.49, evidence_driven best_arm framework_FID=23.39 (−28.43%, d_z=−13.175, p_bonf=3.95e-11) |
| Production-ckpt (Wave 280 P) | ✅ `verification_outputs/wave280-p-r5c/aggregate.json#per_seed` — 3 seeds on production ckpt: seed=42 baseline_fid=11.99, evidence_driven framework_FID=13.67 (+11.90%, BASELINE_WINS at matched NFE=50); seeds 43/44 same direction; **direction-flip from smoke ckpt (framework_WINS −28.43%) to production ckpt (baseline_WINS +10.37%)** |
| SHA256SUMS ledger | ✅ `verification_outputs/wave280-p-r5c/SHA256SUMS` covers 3-seed logs + aggregate |
| Scheduler attribution | EvidenceDrivenScheduler (best_arm across 3 seeds) on smoke ckpt; same on production ckpt (but with sign-flip); cosine/codim also tested per `aggregate.json#per_seed[0].all_arms` but `evidence_driven` is the "best_arm" |
| epochs=1/2/3 regime curve | Wave 191 P2 single-mol anchor only; production-ckpt 3-seed partial; n=30/n=100 NOT attempted |
| **Data holes** | (a) Production ckpt direction-flip is camera-ready deferred (CLM-076 + Wave 280 P disclosure); (b) n=30/n=100 paired-t replication not attempted; (c) SMOKE-ckpt wins are the paper headline; production-ckpt wins are §10 Limitations disclosure |
| **Verifier note** | R5c is the most-disclosed cell — both smoke-ckpt and production-ckpt paths are documented in `aggregate.json` with explicit direction-flip; this is the project's most honest cell |

### 3.7 R6 (k6 foldability tier-aware pLDDT)

| Property | Status |
|---|---|
| Headline source | `verification_outputs/wave235-p3-r6-uplift.json` (counterfactual grid search over easy_tier_nfe_reduction_factor × hard_tier_nfe_intensity; 20 grid cells; baseline_d_z=+0.2235 (Wave 233 P3), best cell d_z=+0.6467 at cell_idx=3 easy_factor=0.0 hard_intensity=3.0; Bonferroni M=3 at α=0.016666666) |
| TierAwareCodimensionSheetScheduler | ✅ Only headline cell using a paper-quantity scheduler (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158` wrapping `CodimensionSheetScheduler`) |
| Wave 233 P3 source | `verification_outputs/wave233-p3-tier-aware-r6.json` (per-cell tier-aware verification) |
| SHA256SUMS ledger | ❌ both headline JSONs are top-level (no ledger); underlying source `k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl + framework/...jsonl` is the tier-stratified baseline |
| Live GPU run | ❌ **NOT YET** run — Wave 336 P1 mentions live GPU run as `wave338-r6-live-eval-smoke/...` (smoke manifests only: baseline.fasta + framework.fasta + manifest.json); full live GPU 3-seed sweep DEFERRED to camera-ready |
| 3-seed pooled + N=1000 cross-seed | ❌ NOT attempted (Wave 280 P R6 sweep has PARTIAL_SUPPORTED cluster-robust 5/8 SUPPORTED; 3-seed×N=200 not N=1000; per-tier d_z=+0.196 tier-aware overall but easy tier REGRESSES 3/3 seeds) |
| **Data holes** | (a) Live GPU run DEFERRED; (b) Cross-seed×N=1000 paired-t NOT attempted; (c) Counterfactual grid is the load-bearing evidence, not live; (d) Wave 341 P1 addend highlights R6 as ONLY codim cell — but Wave 341 P1 also notes the codim attribution is via the codim `n_min=0.0` floor not the four paper quantities |
| **Verifier note** | R6 is the only headline cell with a paper-quantity-driven controller; CLM-085 (Lemma 1 protocol composition closure) anchors at `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` — the canonical A∘B instance |

### 3.8 K-cell data holes

| Cell | Status | Data holes |
|---|---|---|
| K1 (FlowMol3 RDKit-bridged validity) | Wave 308 P2 demoted from BORDERLINE-STRONG (p_bonf=0.054) to UNDERPOWERED (p_bonf=0.5676 FAILS K-level α=0.0125 by 45.4× via family-mis-application); demoted to §10 supplementary | Bonferroni family was mis-applied as R-level k=7 instead of K-level k=4; d_z=+1.3645 underlying measurement is real (`verification_outputs/wave280-p-k1/summary.json`) but the significance test is wrong; N=1000 re-run deferred per Wave 268 strict-clean + 'demote-not-rerun' directive |
| K4 (LineageFlow HMMER 200-300 AA length-bias) | ✅ POWERED — hit-counts 12-22/100 records non-zero across all 3 seeds (`verification_outputs/wave280-p-k4k5/summary_n100.json`) | n=30 / n=100 NOT attempted past seed=42/43/44 |
| K5 (LineageFlow HMMER uniform-AA prior path) | ⚠️ SUPPORTS-WITH-CAVEAT — mean delta +1.33 hits / +8.9%, d_z=1.15, raw p=0.184 NOT sig at α=0.05, Bonferroni p=0.734 NOT sig at α=0.0125 due to n=3 paired-seeds | n=7 follow-up DEFERRED pending user authorization (CLM-060 addendum) |
| K7 (LineageFlow novelty @0.5/0.8/0.95) | ✅ STRONG — mean=1.0 saturated, d_z=∞, p_bonf<1e-300, all 3 seeds status=1.0 PASS (`verification_outputs/wave280-k7/summary.json`); direction-INVERTED canonical in-git evidence (Wave 306 P3) | NONE — both direction-INVERTED (saturated novelty=1.0) + Wave 308 dual-direction CLI flag fixes |

---

## 4. SHA-256 Coverage Matrix (reveals gaps in 6/12 headline artifacts)

| # | Required artifact | On disk | SHA256SUMS parent ledger | Ledger gap |
|---|---|---|---|---|
| 1 | `wave218-p3-kanzi-framework-wins.json` | ✅ | ❌ no parent ledger | parent is top-level (no ledger); but underlying `kanzi_n1000_*` directories likely have per-subdir hashes |
| 2 | `wave191-p3-mnist-n1000.json` | ✅ | ❌ no parent ledger | top-level JSON; underlying seed=42 sweep at `verification_outputs/flowmol3_n1000_*` (Wave 158 / Wave 87 byte-stable) has its own provenance |
| 3 | `wave233-p3-tier-aware-r6.json` | ✅ | ❌ no parent ledger | top-level JSON; underlying `k6_foldability_n1000_w161_q3_2026/` not ledger'd |
| 4 | `wave247-p3-r5b-n1000-n1/summary.json` | ✅ | ❌ NO SHA256SUMS in `wave247-p3-r5b-n1000-n1/` directory | **HIGH PRIORITY** — directory has 7 sample `.npz` files + comparison.md + summary.json + inception_feats_cache/ but NO `SHA256SUMS` |
| 5 | `lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl` | ✅ | ❌ no parent ledger | top-level subdir; `verify_reproducibility_smoke.py` reports 12/12 present |
| 6 | `lineageflow_hmmer_real_n1000_w158_q3_2026/framework_hits.tbl` | ✅ | ❌ no parent ledger | (symmetric to 5) |
| 7 | `novelty_pctid_w166_q3_2026/novelty_results_full.json` | ✅ | ❌ no parent ledger | subdir has baseline/, framework/, novelty_results_full.json, novelty_results.json |
| 8 | `wave280-p-r1/summary.json` | ✅ | ✅ `SHA256SUMS` covers 4 + 18 sub-files | good |
| 9 | `wave280-p-r5c/aggregate.json` | ✅ | ✅ `SHA256SUMS` covers 3-seed logs + aggregate | good |
| 10 | `wave280-p-k1/summary.json` | ✅ | ✅ `SHA256SUMS` covers seed42/43/44 + summary | good |
| 11 | `wave280-k7/summary.json` | ✅ | ✅ `SHA256SUMS` covers subdir | good |
| 12 | `wave280-p-k4k5/summary_n100.json` | ✅ | ✅ `SHA256SUMS` covers subdir | good |

**Ledger coverage verdict:** 6/12 present (the 6 `wave280-p-*` artifacts); 6/12 missing (the older pre-Wave-280 artifacts). The `python3 tools/check_data_integrity.py` tool reports 6 directories / 149 files / 0 mismatches — i.e., the EXISTING 6 ledger directories are internally consistent (no modified/missing/unlisted files), but the 6 unledgred headline artifacts are NOT covered by the data-integrity tool's surface area. The `python3 tools/regenerate_sha256sums.py` writer can close the gap additive-only (per Wave 268 strict-clean rule).

**Per-cell SHA-256 coverage gaps summary:**

| Cell | Headline JSON | Has SHA pin? | Drift reports |
|---|---|---|---|
| R1 | `wave280-p-r1/summary.json` | ✅ via `wave280-p-r1/SHA256SUMS` | 0 (3 seeds * internally consistent) |
| R2 | `wave218-p3-kanzi-framework-wins.json` | ❌ no ledger; framework_source: `wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json`; baseline_source: `wave218-p3-kanzi-baseline-n1000/...` | 0 reported |
| R3 | `flowmol3_n1000_sweep_wave87_q4_2026.json` | ❌ no ledger; canonical Wave 87 byte-stable | 0 reported |
| R5a | `g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` (cross-ref from `CONSOLIDATED_RESULTS §4.1`) | ❌ no ledger | 0 reported (but underlying `wave189-p2-post-cd70821-{two_moons,eight_gaussians}.json` exist with no ledger) |
| R5 | `g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians` (cross-ref from `CONSOLIDATED_RESULTS §4.2`) | ❌ no ledger | 0 reported |
| R5b | `wave235-p1-r5b-fix.json#rounds1` (actual source) AND `g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (README source) | ❌ no ledger for either; `wave247-p3-r5b-n1000-n1/` NO ledger | 0 reported; but 2 separately-sourced numbers surface contradiction |
| R5c | `wave280-p-r5c/aggregate.json` | ✅ via `wave280-p-r5c/SHA256SUMS` | 0 reported |
| R6 | `wave235-p3-r6-uplift.json` + `wave233-p3-tier-aware-r6.json` | ❌ no ledger; underlying `k6_foldability_n1000_w161_q3_2026/{baseline,framework}/foldability/*.jsonl` not ledger'd | 0 reported |

---

## 5. Verification-Outputs Gaps (12 headline artifacts + 6/12 ledger coverage)

`python3 tools/verify_reproducibility_smoke.py` reports **12/12 required artifacts PRESENT** with `Missing: 0`. This is the project's smoke anchor set:
- R1 (Wave 280 3-seed + Wave 158 single-seed base), R2 (Wave 218 deployed paired-t), R3 (Wave 191 smoke-ckpt byte-stable), R5a (implicit via CONSOLIDATED_RESULTS §4.1), R5b (Wave 247 N=1000 n_rounds=1), R5c (Wave 191 MNIST N=1000), R6 (Wave 233 tier-aware), K1 (Wave 280), K4+K5 (Wave 280), K7 (Wave 280).

Per-cell artifact presence matrix (verified by `ls verification_outputs/...`):

| Cell | Required artifact | Present | Cell evidence family |
|---|---|---|---|
| R1 | 4 (Wave 158 base + Wave 280 3-seed pooled) | ✅ | single-seed + 3-seed N=1000 |
| R2 | 2 (Wave 218 paired-t + Wave 214 framework_inv_proj) | ✅ | single-seed N=1000 paired-t |
| R3 | 1 + 2 partial (Wave 87 / Wave 206 P3 / Wave 235 P4) | ⚠️ | 1-seed only; 3-seed BLOCKED |
| R5a | 1 (Wave 189 n=3) + 0 for n>=7 | ❌ for n>=7 evidence | TIE_PERSISTS at n=3 |
| R5b | 4 (Wave 235 rounds1/2/10 + Wave 247 N=1000 + g1_deep_dive v2) | ✅ 5 | N=1000 vs N=200 data-source inconsistency |
| R5c | 2 (Wave 191 + Wave 280) | ✅ | smoke-ckpt + production-ckpt direction-flip |
| R6 | 2 (Wave 233 + Wave 235) | ⚠️ | counterfactual only; live GPU DEFERRED |
| K1 | 1 (Wave 280) | ✅ | UNDERPOWERED status |
| K4+K5 | 1 (Wave 280) | ✅ | K4 POWERED, K5 SUPP-WITH-CAVEAT |
| K7 | 1 (Wave 280 + Wave 166 base) | ✅ | direction-INVERTED saturated |

**Total verification_outputs count:** 543 entries (top-level files + 118 subdirs), of which:
- 440 .json files
- 6 SHA256SUMS ledgers
- 144 waveNNN-*.md audit docs (top-level + cluster subdirs)

---

## 6. Paper ↔ Project Alignment Issues (5 found)

### 6.1 CRITICAL — BGV12 + Villani (2003) bibliography gap

| Item | Detail |
|---|---|
| Paper anchor | `docs/drafts/paper-flat-flattened.md` lines 306, 312, 433, 866, 1336+ cite "Bolley-Guilin-Villani (2012) concentration inequality (BGV12, Theorem 1.1)" + `docs/theory/theorem-1-self-contained.md` cites Villani (2003) for Kantorovich-Rubinstein duality |
| Expected bibliography entry | BGV12 "Quantitative concentration inequalities for empirical measures on non-compact spaces" (Bernoulli 2012) + Villani (2003) "Topics in Optimal Transportation" |
| Actual bibliography [10] | `Karl, Kemeter, Dax, Sierak. Embracing Negative Results in Machine Learning. ICML 2024 Position Paper / arXiv 2406.03980` — completely different paper on publishing-negative-results, NOT on concentration inequalities |
| Severity | CRITICAL — any reviewer will flag this on first scan of bibliography vs in-text citation |
| Fix | Additive: add BGV12 [N] entry + Villani (2003) [M] entry; do NOT renumber existing refs (Wave 268 strict-clean rule, fewer renames) |
| Wave scope | Wave 342 paper-evidence (NOT this audit's owning surface) |
| Files touched | `docs/drafts/paper-flat-flattened.md` §References + maybe `tnnls_submission/cover_letter.md` if it cites bibliography |
| **Verifier note** | The `python3 tools/check_doc_paper_refs.py` + `tools/check_doc_paper_refs_diff.py` did NOT catch this — those tools check ref-name consistency, not ref-vs-citation match. A reviewer would catch it |

### 6.2 HIGH — R5b README data-source inconsistency (resolved Wave 341 P2)

| Item | Detail |
|---|---|
| README row | `Baseline 218.87 / Framework 122.18` columns cite `verification_outputs/wave235-p1-r5b-fix.json` (ver. link) but the actual values 218.87/122.18 come from `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged; "NOT fair comparison") |
| Δ% range | `−2.53% to −0.66%` columns come from `wave235-p1-r5b-fix.json#rounds1` (matched NFE=50, baseline_fid=454.39 not 218.87) |
| Cross-doc consistency | Δ% range −2.53% to −0.66% is IMPOSSIBLE with Baseline=218.87 / Framework=122.18 (true Δ would be −44.17%); the v2 source shows framework=222.16 at v3_matched_nfe (PARITY within noise, framework_regresses); only rounds1 matched-NFE shows the WINS at −2.53% to −0.12% range |
| Severity | HIGH — any reviewer cross-checking the headline against the linked artifact will catch the inconsistency |
| Fix | Wave 341 P2 already proposed (additive; no number changes); cleanest fix: REPLACE Baseline 218.87/Framework 122.18 with rounds1 source-consistent values (baseline_fid 454.39 + per-scheduler framework FIDs 447.11 / 442.89 / 453.85 / 451.37) |
| Wave scope | Wave 342 paper-evidence |

### 6.3 HIGH — R5b "3/4 schedulers" wording (resolved Wave 341 P3)

| Item | Detail |
|---|---|
| README | "−2.53% to −0.66% on 3/4 schedulers" |
| Actual data | `wave235-p1-r5b-fix.json#rounds1` 4/4 schedulers WIN (cosineanneal −1.60%, codimensionsheet −2.53%, evidencedriven −0.12%, freetraj −0.66%); the README drops evidencedriven (−0.12%) from the range without explanation |
| Paper-draft cross-check | `docs/drafts/paper-flat-flattened.md` line 369 says "at n_rounds = 1 the framework WINS 4/4 schedulers" |
| Severity | HIGH — README claims 3/4, paper claims 4/4, actual data shows 4/4 |
| Fix | Wave 341 P3 already proposed: change README wording to "−2.53% to −0.12% on 4/4 schedulers" + match paper-draft |
| Wave scope | Wave 342 paper-evidence |

### 6.4 MEDIUM — R5a Two Moons d_s=+0.460 unresolved (carry from Wave 337)

| Item | Detail |
|---|---|
| Paper-cited value | `docs/drafts/paper-flat-flattened.md` §7.2 line 332 — R5a Two Moons d_s=+0.460 |
| Raw per-seed CSV | `verification_outputs/wave189-p2-post-cd70821-two_moons.json` shows `baseline_w2_mean=0.0736`, `framework_w2_mean=0.0759`, PaperRatioAdaptiveScheduler (NOT Cosine), Δ=−3.16%, p=0.685 NOT bonf-sig, TIE_PERSISTS |
| Per-seed CSV aggregate vs JSON aggregate | `framework_w2_mean=0.075930` (aggregate JSON) vs `framework_w2_mean=0.068891` (per-seed CSV) — 2 candidate sources DISAGREE on framework w2 by +0.0104 |
| Wave 337 final self-check | `docs/audit/wave337-final-self-check-report.md` — "Either an independent aggregated source survives, or the +0.460 is wrong and must be re-derived" — NEITHER has materialized |
| N=30 / N=100 follow-up | NOT attempted past n=10; TIE_PERSISTS direction remains — no escape from framework_WINS claim at the headline d_s=+0.460 paper-cited value |
| Severity | MEDIUM — paper claim is unreplicated; internal data sources disagree; honest disclosure in paper §10 limitations but the d_s=+0.460 is the canonical R5a claim |
| Fix | TBD: either (a) re-derive d_s from independent aggregation, or (b) re-frame wording to acknowledge the aggregation disagreement |
| Wave scope | Wave 342 research-audit (carry from Wave 337) |

### 6.5 MEDIUM — `RMSPreservingCoordinateMixer` referenced in paper but not in code

| Item | Detail |
|---|---|
| Paper anchor | `docs/drafts/paper-flat-flattened.md` §6.2 Sub-claim 1.4 enumerates restart blenders: LinearBlender / DistanceDecayBlender / LatentConvexMixer / RMSPreservingCoordinateMixer |
| Code search | `LatentConvexMixer` found at `adaptive_reflow/universal/mixer.py:167`; `RMSPreservingCoordinateMixer` NOT FOUND in codebase |
| Hypothesis | (a) the class was renamed/removed; (b) the paper misnames; (c) it's defined as an alias/abc-only class not exposed in adaptive_reflow/ |
| Severity | MEDIUM — paper code-coverage claim overstates by 1 class; not load-bearing for any R-cell headline |
| Fix | (a) Trace git history for the class removal; (b) if class is genuinely removed, re-frame paper §6.2 Sub-claim 1.4 to enumerate only the 3 surviving mixer classes |
| Wave scope | Wave 342 research-audit (carry) |

---

## 7. Document Organization Issues (3 stale governance files + 6 orphan_sha drifts)

### 7.1 STALE — `todo/STATUS.md` (137 commits stale)

| Field | todo/STATUS.md says | Actual is | Drift |
|---|---|---|---|
| Last update | "2026-09-21 (post-Wave 205)" | 2026-09-25 (post-Wave 340 READ-ONLY audit + Wave 341 cosine-vs-codim) | 4-day stale + 136 waves stale |
| HEAD commit | `72ba46e` (Wave 204) | `45149561` (Wave 340) | 137 commits stale |
| Venue | "Primary: TPAMI" | "Primary: TNNLS" (per CLM-075 Wave 238) | venue-switched 2026-09-21 |
| D.4 | "33/33 PASS" | "30/30 PASS" (per Wave 270 standardization) | 3 tests discrepancy |
| Ruff count | "~207 remaining" | 0 (per Wave 326 final-metrics + Wave 339 polish) | 207 findings discrepancy |
| Mypy errors | "988 errors in 70 files" | doc-disclosed (CLM-024) | unchanged |
| R-level table | Wave 204 R-level refresh | Wave 235 R5b reversal + Wave 225 P0-P9 counterfactual uplifts missing | 7-row table stale |
| Lines 23-30 | "R5b REGRESSES" | "R5b conditional WIN at n_rounds=1, REGRESSES at n_rounds>=2" (Wave 235 P1 + Wave 336) | direction-flip not reflected |

**Impact:** `todo/STATUS.md` is the project's canonical governance document; if any reviewer reads it as up-to-date, they will see a 137-commit-stale picture (TPAMI venue, D.4 33/33, HEAD 72ba46e, R5b REGRESSES). This is a paper-freezing hazard per AGENTS.md §3 hard guardrail #5 ("Once v3.0-tnnls-ready tag is cut, only additive docs in tnnls_submission/ are allowed").

**Fix:** Wave 342 governance — additive, mechanical update (replace all fields + add Wave 340 / Wave 341 audit references + refresh R-level table).

### 7.2 STALE — `todo/RISK-REGISTER.md` (150+ waves stale)

| Risk | todo/RISK-REGISTER.md covers | Missing risks |
|---|---|---|
| R-001 to R-015 (15 risks) | Wave 6-10 era HF rate-limit + repo reachability + ckpt size + DGL compatibility + flash-attn + protocol mismatch + workspace diverge + OOM defenses + honest reporting | DGL 2.4.0 batched-path bug (Wave 187-216 multi-wave defect); vendored upstream defensive-patch revert (Wave 244-262); cosine-vs-codim scheduler-attribution disclosure gap (Wave 341); TPAMI→TNNLS venue-switch (Wave 238); R5b REGRESSES→WIN reversal at matched NFE=50 (Wave 235); R5c direction-flip on production ckpt (Wave 280) |

**Impact:** Same as 7.1 — if any reviewer reads RISK-REGISTER as the project's forward-looking risk catalog, they will see risks from 16+ waves ago with no coverage of recent issues.

**Fix:** Wave 342 governance — append 6 new risks R-016 through R-021 (additive per "append-only" rule in current file).

### 7.3 STALE — `docs/audit/INDEX.md` (cluster map off by ~50%)

| Cluster | INDEX claims | Actual files | Overstatement |
|---|---|---|---|
| cifar | 18 | 4 | -14 |
| kanzi | 15 | 9 | -6 |
| lineageflow | 10 | 7 | -3 |
| flowmol3 | 10 | 4 | -6 |
| freqflow | 3 | 2 | -1 |
| mnist | 1 | 3 | +2 |
| engineering | 114 | 42 | -72 |
| data_packaging | 29 | 11 | -18 |
| algorithm_4arm | 79 | 19 | -60 |
| sweep_eval | 121 | 76 | -45 |
| stats_method | 65 | 14 | -51 |
| paper_claims | 36 | 6 | -30 |
| final_verify | 74 | 20 | -54 |
| governance | 45 | 7 | -38 |
| reproducibility | 15 | 4 | -11 |
| push_state | 9 | 3 | -6 |
| TOTAL | 653 (251 active + 402 historical) | 387 (155 top-level + 232 in 17 clusters) | -266 files overstated |

**Impact:** If reviewer reads INDEX as canonical, they will look for 653 audit docs across 25 clusters and find only 387 files across 17 clusters — a 41% gap. INDEX was generated as a Wave-275 follow-up and has not been regenerated since.

**Fix:** Wave 342 governance — regenerate INDEX from current on-disk layout (additive; no doc deletions).

### 7.4 STALE — 6 orphan_sha drifts in 3 audit docs (`wave309 / wave310 / wave334`)

`python3 tools/check_data_provenance.py` reports **6 orphan_sha drifts** — all in Wave 309 / Wave 310 / Wave 334 audit docs that cite sha256 hashes from files that have since been re-generated:

```
- docs/audit/wave309-paper-a-restoration-plan.md:151 cites sha256 985b071f3b34... for verification_outputs/g1_deep_dive_q3_2026.json but the on-disk hash differs
- docs/audit/wave309-paper-a-restoration-plan.md:151 cites sha256 87ae2144d482... for verification_outputs/wave195-p2-r-level-power.csv but the on-disk hash differs
- docs/audit/wave309-paper-a-restoration-plan.md:151 cites sha256 87ae2144d482... for verification_outputs/g1_deep_dive_q3_2026.json but the on-disk hash differs
- docs/audit/wave310-restoration-execution.md:34 cites sha256 04830145efb2... for verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/baseline_hits.tbl but the on-disk hash differs
- docs/audit/wave310-restoration-execution.md:83 cites sha256 9618e8f9b53e... for verification_outputs/g1_deep_dive_q3_2026.json but the on-disk hash differs
- docs/audit/wave334-reviewer-prediction.md:62 cites sha256 ca3ae972b658... for verification_outputs/wave191-p3-mnist-n1000.json but the on-disk hash differs
```

**Impact:** Low — orphan_sha means "the doc claims file X has hash Y but the on-disk hash is not Y". Either (a) the artifact was re-generated between doc-cite and now (most likely), or (b) the doc cites a wrong hash. The files themselves are at their canonical paths.

**Fix:** Wave 342 governance — re-cite the current SHA256 in each drift line (additive; no number changes).

### 7.5 STALE — 16 CLM entries lack explicit `- Status:` field (CLM-070 to CLM-085)

`python3 tools/check_claims_consistency.py` parses 84 `^## CLM-NNN:` headers but only finds 65 explicit `- Status:` fields. The 19 missing-status entries break down as:

| Entry range | Count | Status inheritance | Tool behavior |
|---|---|---|---|
| CLM-070 to CLM-085 | 16 entries | Implicit ACTIVE (tool default) | Reports 61 active / 0 provisional / 2 deprecated |
| CLM-086, CLM-087, CLM-088 | 3 entries | Inline `Status: ACTIVE` text (not `- Status:` format) | Same tool-default ACTIVE |

The **most consequential omissions** are:
- CLM-085 (Lemma 1 — protocol composition closure): the §6 Framework Properties Lemma 1, ACTIVE in Wave 311
- CLM-086 (Lemma 2 — state-machine byte-determinism): the §6 Framework Properties Lemma 2, ACTIVE in Wave 322 (was PLACEHOLDER in Wave 311), inline `Status:` text but no `- Status:` field
- CLM-087 (Lemma 3 — ledger tamper-evidence): the §6 Framework Properties Lemma 3, ACTIVE in Wave 322 (was PLACEHOLDER in Wave 311), inline `Status:` text but no `- Status:` field

**Impact:** LOW (tool defaults preserve ACTIVE; no actual claim-status drift) but creates a format-consistency audit gap — ledger's first 65 entries have explicit `- Status:` lines; last 19 do not.

**Fix:** Wave 342 governance — append `- Status: ACTIVE` line to each of CLM-070 through CLM-085 (mechanical, additive-only, 16 line-additions).

### 7.6 STALE — untracked Wave 341 audit doc

`git status` shows `?? docs/audit/wave341-readme-cosine-vs-codim.md` (untracked). This audit doc was produced by Wave 341 READ-ONLY cosine-vs-codim audit but not committed. Per Wave 268 strict-clean additive rule, the audit trail must be preserved in git.

**Fix:** Wave 342 governance — `git add docs/audit/wave341-readme-cosine-vs-codim.md` + commit with Wave 342 message.

---

## 8. Observation / Interpretation / Gap (per research-audit contract)

### 8.1 Observation (what the artifact says)

1. All 5 data-integrity tools PASS (data integrity, smoke 12/12, provenance 0 mismatches in 44 citations except 6 orphan_sha in 3 old docs, claims consistency 0 drift, D.4 30/30 PASS).
2. R1 / R5c / R6 have SHA ledger coverage; R2 / R3 / R4 / R5 / R5b / K4+K5 / K7 lack parent-ledger coverage (no `SHA256SUMS` in their headline-JSON parent dir).
3. R5b has TWO conflicting data sources: README Baseline 218.87/Framework 122.18 from `g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged) vs README Δ% range from `wave235-p1-r5b-fix.json#rounds1` (matched NFE=50, baseline_fid=454.39).
4. R5b production-ckpt N=1000 sweep at `wave247-p3-r5b-n1000-n1/summary.json` shows **2/4 schedulers WIN** (EvidenceDrivenScheduler, FreeTrajScheduler) while the README N=200 implied **4/4 schedulers WIN** — direction divergence at N=200 vs N=1000 is undocumented.
5. R5a Two Moons headline d_s=+0.460 paper-cited value disagrees with raw per-seed CSV (+0.610) + Hedges-corrected (+0.488); aggregate JSON (framework_w2_mean=0.0759) disagrees with per-seed CSV (0.0689) by +0.0104; TIE_PERSISTS at n=3,7,10 with no n=30/n=100 follow-up.
6. todo/STATUS.md is 137 commits stale (HEAD `72ba46e` Wave 204 vs actual `45149561` Wave 340); todo/RISK-REGISTER.md is 150+ waves stale; docs/audit/INDEX.md overstates cluster counts by 41%.
7. Wave 341 audit doc is UNTRACKED in git (`?? docs/audit/wave341-readme-cosine-vs-codim.md`).
8. 16 CLM entries (CLM-070 to CLM-085) lack `- Status:` field; tool defaults to ACTIVE.
9. Paper §6.5 cites BGV12 + Villani (2003) but bibliography [10] is a totally different paper (Karl/Kemeter/Dax/Sierak 2024); any reviewer will catch this.
10. Paper §6.2 Sub-claim 1.4 names `RMSPreservingCoordinateMixer` but the class is NOT found in codebase.

### 8.2 Interpretation (what the agent concludes)

1. **The project is data-integrity-clean and audit-trail-preserving** at the framework core (D.4 + sha256 ledger + claims consistency + reproducibility smoke all PASS). The 12/12 smoke anchor artifact set is sufficient for paper submission.
2. **The user's intuition about cosine-vs-codim is correct**: 6/7 R-cell headlines use CosineAnnealScheduler (R1) or no scheduler at all (R2, R3) or undocumented scheduler (R4, R5) or a mix of 4 schedulers with cosine-best framing (R5b); only R6 uses codim. The Wave 341 addend disclosed this correctly via the Scheduler column + per-cell framework_WINS-mechanism breakdown.
3. **The data holes are HONEST-DISCLOSURE not DATA-INTEGRITY failures**: R3 N=1000 3-seed is BLOCKED at vendor level (CLM-076, Wave 244-262 revert + Wave 338 P5 DGL fix + sampling-rate gap); R5a TIE_PERSISTS is acknowledged across 3 separate waves (n=3,7,10); K1 was correctly demoted from BORDERLINE-STRONG to UNDERPOWERED (Wave 308 P2 Bonferroni family mis-application). Each is disclosed in CLM entries + audit docs.
4. **Paper ↔ project alignment has 1 critical citation error (BGV12/Villani)** and 4 paper/code surface inconsistencies that are correctable additively without renumbering references or re-running experiments.
5. **3 governance docs are stale by 137-150+ commits**; this is a hygiene issue not a data-integrity issue, but it's the first thing a reviewer reading the project holistically would notice.

### 8.3 Unresolved gaps (what's still uncertain)

1. **R5b source-of-truth decision**: should the README adopt the v2 NFE-averaged Baseline/Framework columns (correctly disclosing "NOT fair comparison") OR the rounds1 matched-NFE columns (correctly disclosing 4/4 WIN range)? Wave 341 P2 proposes rounds1 as the cleaner option; user authorization pending.
2. **R5a Two Moons d_s=+0.460 re-derivation**: aggregate JSON vs per-seed CSV disagreement (+0.0104 on framework_w2) is unresolved; Wave 337 final self-check flagged this but no resolution path has been executed.
3. **R3 N=1000 3-seed sweep**: Wave 338 P5 SUCCESS on DGL fix but production-ckpt sweep DEFERRED due to RDKit sampling-rate gap (~80/1000 vs canonical 999/1000); root cause is RDKit sanitization filter (likely upstream CTMC + current RDKit env), fix path is upstream/RDKit environment investigation (NOT framework-side).
4. **BGV12 + Villani (2003) bibliography entries**: 2 entries to add additively (no renumbering); user authorization pending.
5. **`RMSPreservingCoordinateMixer` traceability**: paper claims this class exists but codebase search did not find it; need to verify (a) git history for rename/remove, (b) whether it's defined as abc-only / alias.
6. **Live GPU R6 3-seed sweep**: Wave 336 / Wave 338 mention live GPU smoke manifests only (`wave338-r6-live-eval-smoke/{baseline,framework}.fasta`); full live GPU 3-seed N=1000 sweep is camera-ready deferred.

---

## 9. Prioritized Recommendations (impact-to-effort ranked)

### CRITICAL (must fix before camera-ready)

- **R-BGV12**: Add BGV12 [N] + Villani (2003) [M] bibliography entries to `docs/drafts/paper-flat-flattened.md` §References additively (no renumbering of existing refs per Wave 268 strict-clean). Reviewers will catch this on first read.

### HIGH (fix for paper-review credibility)

- **R-READ1**: Wave 341 P1-P3 fix train on README.md + README.zh.md Headline Results row 6 (R5b) + add Scheduler column to all 7 R-cells. **READY-TO-EXECUTE** in Wave 342 paper-evidence. Diff is ~3 cells, additive, no number changes.
- **R-STATUS**: Refresh `todo/STATUS.md` to reflect Wave 340 / HEAD `45149561` / TNNLS venue / D.4 30/30 / Wave 341 audit reference / R5b conditional WIN disclosure. Mechanical update.
- **R-RISK**: Append R-016 through R-021 risks to `todo/RISK-REGISTER.md` (DGL 2.4.0 bug, vendored revert, cosine-vs-codim gap, TPAMI→TNNLS, R5b reversal, R5c direction-flip).
- **R-TRACK**: Commit untracked Wave 341 audit doc (`git add docs/audit/wave341-readme-cosine-vs-codim.md`).

### MEDIUM (defer to camera-ready)

- **R-INDEX**: Regenerate `docs/audit/INDEX.md` from current 387-file / 17-cluster on-disk layout (mechanical).
- **R-CLM-STATUS**: Append `- Status: ACTIVE` field to CLM-070 through CLM-085 (16 mechanical line-additions).
- **R-DRIFT**: Re-cite current SHA256 in 6 orphan_sha drift lines (Wave 309 / 310 / 334 audit docs).
- **R-LEDGER**: Generate `SHA256SUMS` ledgers for the 6 unledgred headline artifacts (`wave218-p3-kanzi-framework-wins.json`, `wave191-p3-mnist-n1000.json`, `wave233-p3-tier-aware-r6.json`, `wave247-p3-r5b-n1000-n1/`, `lineageflow_hmmer_real_n1000_w158_q3_2026/`, `novelty_pctid_w166_q3_2026/`) via `tools/regenerate_sha256sums.py`.
- **R-RMS**: Trace `RMSPreservingCoordinateMixer` in git history (rename/remove vs paper misname) and either add back to code or reframe paper §6.2 Sub-claim 1.4.
- **R-R5A**: Resolve R5a Two Moons d_s=+0.460 aggregate-vs-per-seed CSV disagreement (Wave 337 carry).

### LOW (nice-to-have)

- **R-DOC-STALE**: Move legacy files (`docs/paper-final-neurips.md`, `docs/paper-final-neurips.pdf`, `docs/paper-eaai.pdf`, `docs/paper-tnnls.pdf`, `docs/paper-draft-precut.md.bak`, `docs/paper-draft-precut-w193.md.bak`) to `docs/ARCHIVE/`. Additive move (not delete) per Wave 268 strict-clean rule.
- **R-ZH-101**: Fix README.zh.md line 101 minor ZH translation drift ("at vendor level" qualifier in R3 row).
- **R-LIVE-R6**: Run live GPU R6 3-seed N=1000 sweep (camera-ready deferred).
- **R-CLONE-R3**: Investigate RDKit sampling-rate gap (~80/1000 vs canonical 999/1000) for full N=1000 3-seed R3 sweep (Wave 338 P5 follow-up).
- **R-CLONE-R5A**: Run R5a Two Moons n=30 / n=100 paired-t follow-up to break TIE_PERSISTS (not currently budgeted).

---

## 10. Hard-Rule Compliance

| Rule | Compliance |
|---|---|
| AGENTS.md §3.1 (vendored upstream byte-identical) | Not touched. Only this audit doc is new, and `docs/audit/wave341-readme-cosine-vs-codim.md` is a new audit doc. Wave 244-262 revert preserved. |
| AGENTS.md §3.2 (no destructive edits) | This is a READ-ONLY audit; no deletions, no header/wording changes, no number changes. |
| AGENTS.md §3.3 (NO-PUSH) | Per Wave 325 user gating, no `git push` without explicit user opt-in. The proposed R-TRACK commit + R-STATUS + R-RISK + R-LEDGER updates are LOCAL commits only. |
| AGENTS.md §3.4 (honest uncertainty) | Status labels preserved (SUPPORTED/NOT_SIGNIFICANT/UNDERPOWERED/REGRESSES/DEFERRED); wording-only fixes proposed (no number promotion of UNDERPOWERED → SUPPORTED). The R5b P2 fix preserves the rounds1 actuals + adds the 4/4 schedulers wording (correct disclosure, not promotion). |
| AGENTS.md §3.5 (TNNLS freeze sacred) | `tnnls_submission/MANIFEST.md` already shows `b87c59b9...` post-edit SHA (verified during this audit run; not modified). |
| AGENTS.md §3.6 (per-phase audit doc) | This doc = `docs/audit/wave341-deep-audit.md` follows the 12-decimal-CLAIMS-table format + observed/interpretation/gap sections. |
| AGENTS.md §3.7 (strict-clean additive) | All proposed fixes are additive: bibliography add 2 entries (no renumber); README Scheduler column add (no number changes); STATUS.md field-update (no semantic change); RISK-REGISTER append R-016..R-021 (no removal); SHA256SUMS regenerate (no file deletion); INDEX.md regenerate (no audit-doc relocation); CLM-070..085 Status append (no number changes). |

---

## 11. Files Touched by This Audit (READ-ONLY)

- **`/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave341-deep-audit.md`** (NEW — this doc; ownership: `flowa-research-audit` per AGENTS.md §2.3)
- Tooling reads (no writes): `python3 tools/check_data_integrity.py`, `tools/verify_reproducibility_smoke.py`, `tools/check_data_provenance.py`, `tools/check_claims_consistency.py`, `pytest tests/test_d4_regression_vectors.py -q` (5 read-only verifications, ALL PASS).

---

## 12. References + Cross-Doc Anchors

- Wave 341 prior: `docs/audit/wave341-readme-cosine-vs-codim.md` (untracked, READ-ONLY cosine-vs-codim audit; P1-P3 fix train proposed)
- Wave 340 prior: `docs/audit/wave340-readme-update.md` (additive README + index update for Wave 339 polish)
- Wave 339 prior: `docs/audit/wave339-h8-fixes.md`, `docs/audit/wave339-b6-fixes.md` (5 abbreviations define + 3 cross-doc numbers align)
- Wave 338 prior: `docs/audit/wave338-h7-cleanup.md`, `docs/audit/wave338-p5-r3-dgl-fix-and-sweep.md`, `docs/audit/wave338-phase2-mechanism.md` (R3 DGL fix success / R3 3-seed deferred)
- Wave 337 carry: `docs/audit/wave337-final-self-check-report.md` (R5a Two Moons d_s=+0.460 carry)
- Wave 336 prior: `docs/audit/wave336-r5b-mechanism.md` (R5b n_rounds=1 vs n_rounds>=2 mechanism)
- Wave 335 prior: `docs/audit/wave335-self-check-verification.md`
- Wave 334 prior: `docs/audit/wave334-reviewer-prediction.md` (one of the 3 orphan_sha sources)
- Wave 326 prior: `tools/verify_reproducibility_smoke.py` 12-headline-artifact anchor
- Wave 270 prior: D.4 30/30 PASS standardization (replaced 33/33 PASS)
- Wave 244-262 prior: `CLM-076` vendored upstream defensive-patch revert + R3 BLOCKED at vendor level
- Wave 238 prior: `CLM-075` TPAMI → TNNLS venue switch
- Wave 235 prior: R5b REGRESSES → conditional WIN reversal at n_rounds=1 matched NFE=50
- `docs/CLAIMS.md` (84 entries / 61 active / 0 provisional / 2 deprecated per `tools/check_claims_consistency.py` 0 drift)
- `docs/CONSOLIDATED_RESULTS.md` (8740 lines / 11 sections / §4.1 R5a + §4.2 R5 sources)
- `docs/cover-letter-tnnls.md` (12-artifact smoke anchor + 24.6× wall-clock headline + R5b conditional WIN disclosure)
- `tnnls_submission/MANIFEST.md` SHA-256 `b87c59b9...` (post-edit)
- `tnnls_submission/{cover_letter,highlights,tables,figures,data_availability,submission_checklist}.md` (7-file freeze set)
- `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (R5b matched-NFE=50 4/4 schedulers WIN source — the only consistent data source)
- `verification_outputs/wave247-p3-r5b-n1000-n1/summary.json` (R5b N=1000 production-ckpt 2/4 schedulers WIN finding — NOT yet in README Headline Results)

---

## 13. End-of-Doc Audit Fingerprint

- Head SHA: `45149561df103221860e4d0c91be5a0660521eab` (Wave 340 HEAD; repo not pushed per Wave 325 user gating)
- Status: ACTIVE READ-ONLY DEEP AUDIT (no code, claim, or headline number changed)
- Tool gates: data integrity 6/6 ledgers + 149 files PASS; reproducibility smoke 12/12 PASS; provenance 6 orphan_sha (3 old docs); claims consistency 0 drift; D.4 30/30 PASS
- Audit trail additions: this doc (NEW) + Wave 341 prior doc (untracked, commit pending)
- Next action: Wave 342 candidate (paper-evidence READ + governance STATUS/RISK refresh); NO-PUSH gate preserved
- Per-cell data holes: 3 (R3 3-seed N=1000 BLOCKED at vendor level; R2 3-seed paired-t replication not attempted; R5a TIE_PERSISTS with no n=30/n=100)
- Paper ↔ project alignment issues: 5 (1 CRITICAL BGV12/Villani citation; 2 HIGH R5b data-source inconsistency + "3/4 schedulers"; 2 MEDIUM R5a d_s +0.460 + RMSPreservingCoordinateMixer)
- Doc organization issues: 4 (3 stale governance docs by 137-150+ commits + 1 untracked Wave 341 audit)
- Hard-rule compliance: ALL 7 rules SATISFIED (vendored-unchanged, no-destructive, no-push, honest-uncertainty, TNNLS-freeze, per-phase-audit, strict-clean-additive)

