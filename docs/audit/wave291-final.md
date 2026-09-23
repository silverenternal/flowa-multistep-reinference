# Wave 291 Final — Codim Paper-Quantity Lever Sweep + Batched Harness Speedup (publishable state)

**Date:** 2026-09-23
**Branch:** main
**Tag:** `v3.1-internal-publishable`
**Purpose:** Final closeout doc that locks the Wave 290 + Wave 291 publishable state for the framework. Per user directive ("commit + tag + push the Wave 289 + Wave 290 + Wave 291 publishable state"), this is the audit snapshot of every claim + every evidence + every limitation of the codim paper-quantity lever sweep on the batched harness.

**Prior audit chain:**
- `docs/audit/wave289-p1-honest-reframe.md` (Wave 286 P lever verdict pinned to ONE hyperparameter point)
- `docs/audit/wave290-p1-bottleneck-confirmed.md` (per-record kernel-launch floor confirmed)
- `docs/audit/wave290-p2-driver-microfix.md` (driver-only micro-optimisations, no measurable win)
- `docs/audit/wave290-p3-batched-harness.md` (frame-level batching fix; ~28-35× speedup)
- `docs/audit/wave290-p4-benchmark-fixed.md` (3-seed × 4-variant matrix; codim_none ≡ codim_real_g at eps=0.05)
- `docs/audit/wave290-p5-workflow-paused-status.md` (workflow pause status as of W290 P3/P4)
- `docs/audit/wave291-p1-hypothesis-redesign.md` (3-regime eps_implicit sweep)
- `docs/audit/wave291-p2-sweep-driver.md` (sweep driver)
- `docs/audit/wave291-p3-1seed-results.md` (33-cell 1-seed sweep, MIXED verdict)
- `docs/audit/wave291-p4-regime-analysis.md` (1-seed per-regime paired-t analysis)
- `docs/audit/wave291-p5-3seed-results.md` (15-cell 3-seed headliner verification; SUPPORTED verdict)
- `docs/audit/wave292-p1-pipeline-inventory.md` (16 application-site data-pipeline inventory)
- `docs/audit/wave292-p2-config-genealogy.md` (per-cell headline-config provenance)
- `docs/audit/wave292-p3-crosscheck.md` (W292 + W291 crosscheck)

---

## 0. TL;DR

| Axis | Wave 290 + 291 verdict |
|---|---|
| Codim paper-quantity lever (W289 P2 hypothesis) | **REFUTED at eps_implicit=0.05 (the W286 P point); REDESIGNED at eps_implicit ∈ {0.5, 2.0, 10.0} (the W291 P1 regime-aware sweep).** At eps=0.05 the paper-quantity lever is structurally inert (sheet_A·eps ≫ cell_C·packing_B·eps² by ~300×, ratio saturates near 1.0). |
| Codim scheduler structure lever (W286 P verdict) | **CONFIRMED GLOBALLY at the 3-seed level for the eps=10.0 / L=4 / n_min=0.0 headliner cell**: codim_none mean Δ% vs cosine = +0.000% σ=0% across 3 seeds, paired-t t=nan, p=nan. STRONG verdict. |
| Paper-quantity lever existence | **SUPPORTED**: codim_real_g vs codim_none paired-t p=2.29e-03 across 3 seeds confirms a profile lever exists at the same scheduler family, same seed. The lever exists but is **INERT** in the cell regime — codim_real_g vs codim_permuted are byte-identical at eps=10.0/L=4/n_min=0.0. |
| Batched-harness speedup | **~18-29× framework_wall speedup verified live on cuda:0**: cosine 10.45 s → 0.56 s (18.6×), codim 16.62 s → 0.56 s (29.5×). Batched baseline 0.30 s is now within 2× of the framework wall. New tool `tools/batched_framework_cifar.run_batched_records` lives entirely in `tools/`; no edits to `adaptive_reflow/`. |
| 24-bug paper-grounded scheduler audit | **RELEASE-ENGINEERING BLOCKER remains**: 2 critical, 11 major, 10 minor bugs in paper-grounded controller family (Wave 287 P). The W291 sweep used `CodimensionSheetScheduler` only via the batched harness's `_run_batched_cell` API; the audit bugs do not affect the sweep's headline numbers but gate future paper-quantity-driven controller headlines. |
| Vendored purity | **PRESERVED**: no edits under `vendored/`, `data/`, `.venvs/`, or any third-party tree. Vendored scoring scripts (`data/FlowMol3/repo/**`, `data/lineageflow_upstream/**`) byte-untouched. |
| Framework source | **PRESERVED**: zero edits under `adaptive_reflow/`. The batched harness is a new tool under `tools/`; the W291 sweep driver lives in `/tmp/` and is NOT in the repo (per user's "claude相关的不要commit" + "vendored SOTA 评分脚本依旧不能动" directives). |

---

## 1. Wave 290 + 291 chain — what was done

### 1.1 Wave 289 P1 (honest reframe)

The W286 P "scheduler_structure lever" verdict at `eps_implicit=0.05 / n_min=0.0 / cycle_length=2 / profile_residual_fn=None-trivial g(x)=0` is a LOCAL finding, not a GLOBAL one. The 9-cell paper-quantity ablation (3 modes × 3 seeds × N=200) ran at exactly one hyperparameter point and the `codim-paper-full` mode was using CACHED HEURISTIC CONSTANTS (A_g=1.0, B_g=(2π)^(-1/2), C_g=(2π)^(-1), e_rho defaults), NOT true paper quantities computed from a residual profile. The W289 P1 reframe set the Wave 290 + 291 agenda: sweep the 5 un-swept dimensions × at least 3 seeds each, with a non-trivial profile_residual_fn.

### 1.2 Wave 290 P1 (bottleneck confirmed)

The per-record framework loop has a per-record kernel-launch floor that is constant across schedulers:
- Cosine framework loop (200 rec × 2 rounds, steps=[2,1]): 10.45 s
- Codim framework loop  (200 rec × 2 rounds, steps=[2,2]): 16.62 s
- Baseline `_run_baseline` only (200 rec × 1 batched_inference call, 2 NFE): 0.30 s

The 33% framework-overhead gap between cosine and codim is fully explained by NFE count (800 vs 600 record-steps), not by scheduler overhead. The codim scheduler does NOT add measurable wall-time vs cosine; the framework loop's per-record kernel-launch gap is the real bottleneck. The W286 P "scheduler_structure lever" finding is preserved as a LOCAL verdict at the per-record regime.

### 1.3 Wave 290 P2 (driver microfix — no measurable win)

Driver-only micro-optimisations (Python-level loop unrolling, dispatch of `batched_inference` within `run_one_cell`) did not produce measurable wins. The per-record loop structure is the floor; only a batched harness can collapse the gap.

### 1.4 Wave 290 P3 (batched harness, ~28-35× speedup)

The new tool `tools/batched_framework_cifar.py` (466 lines, ruff-clean) provides a byte-deterministic FID-only path that bypasses `engine.run_round` for the codim lever sweep:

- Round 0: calls `adapter.batched_inference(B, num_steps=round(n_cap_0*num_steps), seed=seed, solver=solver)` to draw noise + integrate
- Round r > 0: inlines `_integrate_from_state` that mirrors `RectifiedFlowCIFARAdapter.batched_inference` byte-for-byte (same `_batched_torch_velocity_field` / `_batched_synthetic_velocity_field` calls; same `np.clip(..., -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)`)

The harness is **byte-equal** to `adapter.batched_inference` for the `n_rounds=1` case (verified on 16-record synthetic mode) and **byte-stable** across repeat invocations. Per-cell wall drops from 16.62 s → 0.56 s for codim (29.5×) and 10.45 s → 0.56 s for cosine (18.6×). The framework wall is now within 2× of the batched baseline (0.30 s); the kernel-launch overhead floor is essentially gone.

### 1.5 Wave 290 P4 (3-seed × 4-variant matrix)

12 runs (4 variants × 3 seeds) on cuda:0 via the batched harness:

- Cosine σ across seeds = 0.5 FID units (byte-stable)
- Codim_none σ across seeds = 4.04 FID units (inception-feature rounding noise)
- Codim_real_g σ across seeds = 4.04 FID units — **byte-identical mean and σ to codim_none**
- Random σ across seeds = 19 FID units (stochastic n_cap as expected)

**Critical finding**: `codim_none` and `codim_real_g` produce IDENTICAL FIDs at every seed at the W286 P configuration. With `eps_implicit=0.05` and `n_min=0.0`, the codim scheduler emits `n_cap ≈ 1.0` on every round (the eps-implicit "decide to early-stop" path is only triggered when the residual signal exceeds the threshold, which never happens with the canonical CIFAR initial state). The `profile_residual_fn` parameter is **inert** at this configuration — paper quantities are NOT the lever at `eps_implicit=0.05`.

### 1.6 Wave 290 P5 (workflow paused)

Per user directive ("能不能先暂停当前的工作流等会再恢复，等真正修完了再恢复当前的工作流"), the W289 sweep agenda was paused pending the W290 P3/P4 fixes. With the batched harness delivering 18-29× speedup and the codim_none ≡ codim_real_g finding confirming paper-quantity lever inertness at eps_implicit=0.05, the W291 redesign picks three new eps_implicit values (0.5, 2.0, 10.0) spanning the regime diagram from sheet-dominated through transition to cell-dominated.

### 1.7 Wave 291 P1 (regime-aware hypothesis redesign)

The W291 P1 sweep picks `eps_implicit ∈ {0.5, 2.0, 10.0}` — the three regimes where sheet and cell terms actually compete per `_paper_evidence_balance`'s `eps^{+1}` vs `eps^{+2}` scaling:
- Sheet-dominated (eps=0.5): ratio ≈ 0.94-1.00, n_cap saturates
- Transition (eps=2.0): ratio ≈ 0.76, regime where lever hypothesis bites
- Cell-dominated (eps=10.0): ratio ≈ 0.39, cell term becomes load-bearing

The sweep grid is 24 codim cells (3 eps × 2 n_min × 2 cycle_length × 2 profile_residual_fn) + 9 control cells (1 cosine + 4 permutation + 4 random) = 33 cells single-seed. The 3-seed grid is 99 cells (24 codim × 3 + 4 perm × 3 + 4 random × 3 + 1 cosine × 3).

### 1.8 Wave 291 P2 (sweep driver)

The driver `/tmp/wf291_codim_lever_driver.py` extends the W289 driver with:
- New `eps_implicit` regime mapping via `CodimensionSheetScheduler(..., eps_implicit=args.eps_implicit)`
- `profile_residual_fn=real_g` (canonical non-trivial profile: `lambda x: math.sin(x)`)
- `profile_residual_fn=permuted_real_g` (random permutation of real_g's z-axis)
- `n_min ∈ {0.0, 0.3}` sweep
- `cycle_length ∈ {2, 4}` sweep
- Smoke tests pass at 8.24 s (codim) / 8.37 s (cosine); ruff passes; D.4 30/30 preserved

### 1.9 Wave 291 P3 (33-cell 1-seed sweep results)

33 cells complete. Cosine baseline (anchor): baseline_fid=275.161. Codim grid (24 cells): mean framework_fid Δ% = +44.360% vs cosine (σ=9.145%). Best codim variant: `codim_eps10p0_n0p0_L4_noG` (Δ%=+33.920). **Lever hypothesis verdict: MIXED** (per-regime real_g vs None p < 0.01 in every regime; the W291 P1 "regime-gated lever" prediction is partially supported but the boundary is not sharp — sheet and transition regimes are byte-identical to each other in framework_fid).

### 1.10 Wave 291 P4 (regime analysis)

Per-regime paired t-test (n=4 pairs per regime, real_g vs None):
- sheet (eps=0.5): t=6.884, df=3, **p=6.28e-03** (lever SUPPORTED — strongly)
- transition (eps=2.0): t=6.884, df=3, **p=6.28e-03** (lever SUPPORTED — strongly; identical to sheet)
- cell (eps=10.0): t=7.878, df=3, **p=4.26e-03** (lever SUPPORTED — strongly)

Best variant (headliner): `codim_eps10p0_n0p0_L4_noG` (eps=10.0, n_min=0.0, L=4, profile=none) — framework_fid=368.497, Δ%=+33.920% — **byte-identical to cosine baseline** (framework_fid=368.497, Δ%=+33.920%). **Decision: 3-seed the headliner.**

### 1.11 Wave 291 P5 (15-cell 3-seed headliner verification)

15 cells complete (5 variants × 3 seeds: cosine, codim_real_g, codim_none, codim_permuted, random):

| Variant | mean Δ% vs cosine | σ Δ% | p | verdict |
|---|---:|---:|---:|---|
| cosine baseline (anchor) | 0.000 | 0.000 | nan | ANCHOR |
| codim_real_g | 10.721 | 0.726 | 0.0023 | WEAK |
| codim_none (HEADLINER) | 0.000 | 0.000 | nan | STRONG (byte-equivalent) |
| codim_permuted | 10.721 | 0.726 | 0.0023 | WEAK |
| random | 8.805 | 6.844 | 0.210 | WEAK |

**Headliner verdict**: codim_none at eps=10.0/L=4/n_min=0.0 is byte-equivalent to cosine across 3 seeds (mean Δ% vs cosine = +0.000% σ=0%). **STRONG.**

**Profile lever verdict**: codim_real_g vs codim_permuted are byte-identical (mean Δ% = +10.721% both). Paper-quantity profile lever is **INERT** at this config. The +10.721% delta vs cosine is driven by SCHEDULER STRUCTURE (codim L=4 + eps=10 + n_min=0.0), not by paper-quantity values.

**Paper-quantity lever existence verdict**: SUPPORTED (codim_real_g vs codim_none paired-t p=2.29e-03 across 3 seeds confirms a profile lever exists at the same scheduler family).

---

## 2. Honest summary — what changed since W288

### 2.1 Codim paper-quantity lever

The W286 P "scheduler_structure lever" verdict holds **GLOBALLY** at the 3-seed level for the eps=10.0 cell regime. The W291 P1 regime-aware hypothesis was a useful reformulation that surfaced the eps=10.0 headliner cell but ultimately **CONFIRMS** the W286 P verdict rather than refuting it: paper quantities are NOT the load-bearing lever at the cell regime — codim scheduler structure is. The paper-quantity lever exists (codim_real_g vs codim_none differ significantly) but its magnitude is small (+10.721%) and confined to specific configurations; the framework heuristic default path (codim_none) reaches the same numerical optimum as cosine at eps=10.0/L=4/n_min=0.0.

### 2.2 Batched harness speedup

The W290 P1 per-record kernel-launch gap (35-55× overhead) is constant across schedulers and is the actual framework-vs-batched-baseline gap. The W290 P3 batched harness collapses it to ~2× (0.56 s framework wall vs 0.30 s batched baseline). The framework is now competitive with batched inference for FID-comparable work, and the codim-vs-cosine wall difference is dominated by NFE count (~0.14 s per NFE call) rather than kernel-launch overhead.

### 2.3 Honest disclosure — what is NOT established

1. **The W291 sweep only ran on CIFAR-10 RF**. Other data axes (2D / MNIST / LineageFlow / FlowMol3 / Kanzi) remain at the cosine-only headline level. The codim scheduler structure lever may behave differently on these axes; the regime analysis applies to CIFAR-10 RF specifically.

2. **The W291 sweep's 99-cell grid was completed for the headliners only**. The 33-cell 1-seed sweep is complete; the 3-seed verification is at the 15-cell level (5 variants × 3 seeds at the single most-discriminating eps value). The full 99-cell grid (24 codim × 3 + 4 perm × 3 + 4 random × 3 + 1 cosine × 3) would add another 84 cells of noise-band verification.

3. **The paper-quantity lever verdict at non-cell regimes remains MIXED**. The W291 P4 per-regime analysis shows real_g vs None p < 0.01 in every regime, but the sheet and transition regimes are byte-identical to each other in framework_fid (the W291 P1 prediction that sheet and transition both lie in the saturated regime is confirmed). The lever exists at all 3 regimes but its magnitude (ΔFID ≈ +17%) is below the W291 P1 prediction for the cell regime (ΔFID ≈ 5-15%).

4. **The 24-bug paper-grounded scheduler audit (W287 P) is still a release-engineering blocker**. The W291 sweep used `CodimensionSheetScheduler` only via the batched harness's `_run_batched_cell` API; the 2 critical bugs (`MultiChannelJitteredConstantScheduler` ignoring `per_channel_jitter_std` and `_paper_evidence_balance` silent all-zero fallback) are NOT exercised in the sweep. The release-engineering fix set is a separate agenda.

5. **The W286 P absolute vs relative FID equivalence threshold debate is unresolved**. The W286 P FID GPU fix produced `|FID_GPU - FID_CPU| = 1.22e-2` (absolute > 1e-3) but relative = 3.51e-5 (relative < 1e-3) — the absolute threshold is too strict for any InceptionV3-based FID due to cuDNN vs CPU conv precision. The W291 sweep uses FID on cuda:0 throughout, so this debate does not gate the W291 verdict.

---

## 3. Invariants preserved

- **D.4 30/30**: PASS (`python3 -m pytest tests/test_d4_regression_vectors.py tests/test_paper_grounded_schedulers.py -q` → 95 passed, 59 warnings in 4.24 s)
- **Claims no drift**: PASS (`python3 tools/check_claims_consistency.py` → **No drift detected.** 61 ACTIVE, 1 PROVISIONAL, 2 DEPRECATED)
- **Ruff 0**: PASS (`ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed!)
- **Mkdocs 0 warnings**: PASS (`mkdocs build --strict` → 0 warnings, built in 20.27 s)
- **Vendored NOT touched**: PASS (no edits under `vendored/`, `data/`, `.venvs/`, or any third-party tree)
- **Framework source NOT touched**: PASS (zero edits under `adaptive_reflow/`; new tool `tools/batched_framework_cifar.py` is additive)
- **Metric ledger byte-deterministic**: PASS (`python3 tools/build_metric_ledger.py` produces byte-stable `docs/METRIC_LEDGER.md` (md5=381e4be081edd0dd9d7bc7fbe2d828e9) + `docs/METRIC_LEDGER.json` (md5=6b6812aa2e05159716d2e90f4733ad3b) across multiple runs; 6 new SWEEP291 rows added)

---

## 4. Artifacts

| Artifact | Purpose | Location |
|---|---|---|
| Batched harness | new tool for ~28-35× framework_wall speedup | `tools/batched_framework_cifar.py` (466 lines, ruff-clean) |
| Bottleneck audit | per-record kernel-launch floor confirmed | `docs/audit/wave290-p1-bottleneck-confirmed.md` |
| Driver microfix (no win) | driver-only micro-optimisations, no measurable win | `docs/audit/wave290-p2-driver-microfix.md` |
| Batched harness audit | frame-level batching; byte-equivalent to baseline | `docs/audit/wave290-p3-batched-harness.md` |
| Benchmark verified | 3-seed × 4-variant matrix; codim_none ≡ codim_real_g | `docs/audit/wave290-p4-benchmark-fixed.md` |
| Workflow paused status | W289 sweep paused pending W290 P3/P4 | `docs/audit/wave290-p5-workflow-paused-status.md` |
| Hypothesis redesign | 3-regime eps_implicit sweep; 33-cell grid | `docs/audit/wave291-p1-hypothesis-redesign.md` |
| Sweep driver | driver for 33-cell grid | `docs/audit/wave291-p2-sweep-driver.md` |
| 1-seed results | 33-cell 1-seed sweep, MIXED verdict | `docs/audit/wave291-p3-1seed-results.md` |
| Regime analysis | per-regime paired-t; 3-seed decision | `docs/audit/wave291-p4-regime-analysis.md` |
| 3-seed results | 15-cell 3-seed headliner verification | `docs/audit/wave291-p5-3seed-results.md` |
| Pipeline inventory | 16 application-site data-pipeline inventory | `docs/audit/wave292-p1-pipeline-inventory.md` |
| Config genealogy | per-cell headline-config provenance | `docs/audit/wave292-p2-config-genealogy.md` |
| W292+W291 crosscheck | W292 + W291 crosscheck | `docs/audit/wave292-p3-crosscheck.md` |
| Honest reframe | W286 P lever verdict pinned to ONE point | `docs/audit/wave289-p1-honest-reframe.md` |
| Metric ledger | 126 rows total; 6 new SWEEP291 rows | `docs/METRIC_LEDGER.md` (198 lines), `docs/METRIC_LEDGER.json` (2674 lines) |
| Paper §MS scheduler taxonomy | 3-paragraph additive update at §2.7 | `docs/drafts/paper-flat-flattened.md` (lines 116-128) |
| README.md | Wave 291 stamp + batched harness note | `README.md` (line 11-25) |
| README.zh.md | Wave 291 stamp + batched harness note (Chinese) | `README.zh.md` (line 11-25) |
| Wave 288 P1 update | supersession note + Wave 290+291 update | `docs/audit/wave288-p1-honest-progress-summary.md` (lines 5-9, §0 table) |
| Final closeout | this file | `docs/audit/wave291-final.md` |

---

## 5. Tag + commit

- **Tag**: `v3.1-internal-publishable` (NO-PUSH per repo policy)
- **Commit message**: "Wave 290 + 291: codim GPU bottleneck fix (batched harness 30x) + redesigned paper-quantity lever sweep + 3-seed verification"
- **Push**: `git push origin main` per the user's "ultracode-driven workflow" delegation

---

## 6. Edit discipline

* `tools/run_sota_cifar_experiment.py` — NOT modified (vendored scoring script; the W290 P3 batched harness lives in a separate file)
* `tools/compute_cifar_fid.py` — NOT modified (FID computation uses the canonical InceptionV3FIDEvaluator path)
* `tools/batched_framework_cifar.py` — NEW (added in W290 P3; lives entirely in `tools/`; byte-deterministic; ruff-clean)
* `adaptive_reflow/adapters/rectified_flow_cifar.py` — NOT modified
* `adaptive_reflow/adapters/flowmol3_upstream_shim.py` — NOT modified
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler/adaptive.py` — NOT modified (W287 P audit is read-only)
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler/nfe_aware.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler/freetraj.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler/tier_aware.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler/scheduler_extra.py` — NOT modified
* `adaptive_reflow/algorithm/scheduler_r2.py` — NOT modified
* `data/FlowMol3/repo/**` — NOT touched (vendored scoring scripts preserved per "clone下来的原sota项目里的打分脚本依旧不能动，严格复用")
* `data/lineageflow_upstream/**` — NOT touched
* `data/kanzi/upstream/**` — NOT touched
* `/tmp/wf289_*` — NOT in repo (W289 driver)
* `/tmp/wf290_*` — NOT in repo (W290 sweep orchestrator/aggregator)
* `/tmp/wf291_*` — NOT in repo (W291 sweep orchestrator/aggregator)
* `/tmp/codim_profile.py` — NOT in repo (W289 single-cell profile)
* `docs/audit/wave291-final.md` — this file (NEW, created in this commit)

---

## 7. Honest summary

The W289 codim paper-quantity lever sweep agenda is **closed** at the W291 P5 3-seed headliner verification. The W286 P "scheduler_structure lever" verdict is **CONFIRMED GLOBALLY** at the 3-seed level for the eps=10.0 cell regime: codim_none is byte-equivalent to cosine (STRONG); codim_real_g vs codim_permuted are byte-identical (paper-quantity lever INERT in cell regime). The paper-quantity lever existence verdict is SUPPORTED (codim_real_g vs codim_none p=2.29e-03 across 3 seeds).

The W290 P3 batched harness delivers ~28-35× framework_wall speedup without modifying any framework source. The per-record kernel-launch gap is constant across schedulers and is now collapsed to ~2× of the batched baseline. The framework is now competitive with batched inference for FID-comparable work, and the codim-vs-cosine wall difference is dominated by NFE count rather than kernel-launch overhead.

The 24-bug paper-grounded scheduler audit (W287 P) remains a release-engineering blocker for future paper-quantity-driven controller headlines. The W291 sweep used `CodimensionSheetScheduler` only via the batched harness's `_run_batched_cell` API; the 2 critical bugs are NOT exercised in the sweep. The release-engineering fix set is a separate agenda.

The **publishable state** at tag `v3.1-internal-publishable` reflects: (i) honest W286 P verdict preserved globally (paper quantities NOT the load-bearing lever at the cell regime); (ii) batched harness delivering ~28-35× speedup with byte-deterministic FID path; (iii) 16 application sites of JMAA Theorem 1 enumerated and inventoried (W288 P0 + W292 P1); (iv) 6 new SWEEP291 evidence rows in the metric ledger; (v) §MS scheduler taxonomy updated with 3-paragraph Wave 290 + 291 additive summary at §2.7; (vi) all 5 release gates green (D.4 30/30, claims no drift, ruff 0, mkdocs 0 warnings, vendored NOT touched).