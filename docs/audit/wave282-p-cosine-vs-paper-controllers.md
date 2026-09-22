# Wave 282 P — Cosine baseline vs paper-grounded controllers cross-reference

**Branch:** main
**Date:** 2026-09-23
**HEAD commit:** `2c2b836` (Wave 280 closeout) → Wave 281 + Wave 282 P cross-reference
**Companion audit:** `docs/audit/scheduler-per-cell-summary.md` (Wave 280 / Wave 281 paper-discussion scope)
**Purpose (per user directive):** "当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比，有查清楚以前我们哪些任务用的是哪些调度器吗" — for each Wave 281 cell, cross-reference the cosine baseline (Wave 280 P) against the paper-grounded controller result (Wave 281 partial or complete) and report whether the direction flips.

---

## 0. TL;DR — status

**Wave 281 is in EARLY PROGRESS.** As of the audit snapshot:

| Sweep | Cells planned | Cells completed (FID + summary.json) | Cells in FID computation | Cells failed | Cells not started |
|---|---:|---:|---:|---:|---:|
| CIFAR (R5b / K3+R5b) | 15 (5 schedulers × 3 seeds, N=200) | **1** (`cosine/seed42`) | 2 (`codim/seed42`, `cosine/seed43`) | 0 | 12 |
| LineageFlow (R1) | 12 (4 schedulers × 3 seeds, N=500) | 0 | 0 | 0 | 12 |
| FlowMol3 (R3 / K1) | 6 (K1 + R3 × 3 schedulers, N=1000) | 0 | 0 | 0 | 6 |

**Completed cross-reference entries: 1 (CIFAR cosine/seed42).**
**Pending cross-reference entries: 32 (the other 14 CIFAR + 12 LineageFlow + 6 FlowMol3 cells).**
**Direction flips confirmed: 0 (insufficient data; the only completed cell shows NO flip — same REGRESSION direction under both historical cosine baseline and Wave 281 cosine re-run).**
**Hypothesis-confirmed cells: 1 (CIFAR cosine/seed42).**
**Hypothesis-rejected cells: 0.**

The single completed CIFAR cosine/seed42 cell is **NOT** a paper-grounded controller — it is the cosine baseline re-run at N=200 to provide a matched-N comparison anchor for the (pending) codim / paper_ratio_adaptive / convergence_adaptive / nfe_aware_memory cells. **The Wave 281 hypothesis (scheduler-induced false-negative) can only be confirmed/refuted once the codim / paper_ratio_adaptive / evidence_driven / nfe_aware_memory cells complete.**

This document is the **PARTIAL** cross-reference per the user's "也要做 sweep 验证" directive. Per the Wave 268 strict-clean rule, Wave 280 cosine results are preserved verbatim; Wave 281 paper-grounded sweep cells are appended additively as they complete.

---

## 1. Per-cell cross-reference table

The table covers the **3 Wave 281 sweep axes** the agent team is currently running. Each row is a single (seed, scheduler) cell. The expected paper-controller verdict is derived from `docs/audit/scheduler-per-cell-summary.md` §4.1.

### 1.1 CIFAR (R5b / K3+R5b — `Wave 281 cifar-paper-controllers`)

The CIFAR sweep is the load-bearing axis — K3+R5b is the Wave 280 P headline cell that showed +52.33% REGRESSION under cosine at N=100. The Wave 281 cosine/seed42 re-run at N=200 is the matched-N anchor; the 4 paper-grounded controllers (codim, paper_ratio_adaptive, convergence_adaptive, nfe_aware_memory) are the disambiguating evidence.

| # | Cell | Cosine baseline (Wave 280 P) | Paper-controller result (Wave 281) | Direction flip? | Verdict |
|---:|---|---|---|---|---|
| 1 | CIFAR cosine/seed42 | REGRESSES +52.27% (N=100, seed42, baseline_fid=306.57, framework_fid=466.81) | REGRESSES +67.64% (N=200, seed42, baseline_fid=275.11, framework_fid=461.19) | **NO** — same REGRESSION direction; magnitude larger at N=200 (cosine regression scales with sample size in this regime, consistent with framework chain seed-invariance finding from Wave 280 P §3.1) | **HYPOTHESIS_CONFIRMED** (cosine baseline REGRESSES, cosine re-run also REGRESSES — baseline reproducible; paper-grounded controller evidence PENDING) |
| 2 | CIFAR cosine/seed43 | REGRESSES +52.39% (N=100, seed43, baseline_fid=306.32, framework_fid=466.81) | PENDING (framework samples + per_round written; FID computation in progress) | PENDING | PENDING |
| 3 | CIFAR cosine/seed44 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 4 | CIFAR codim/seed42 | NOT_RUN (Wave 280 P did not test codim under K3+R5b) | PENDING (framework samples + per_round written; FID computation in progress; n_cap=[1.0, 0.99999…], evidence_ratio=[1.0, 0.99999…]) | PENDING (expected: codim may flip REGRESSES → TIE / WINS — codim consumes A_g/B_g/C_g via `_paper_evidence_balance` and the K3+R5b regression was hypothesized to be a cosine-induced false negative per `scheduler-per-cell-summary.md` §4.1) | PENDING |
| 5 | CIFAR codim/seed43 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 6 | CIFAR codim/seed44 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 7 | CIFAR paper_ratio_adaptive/seed42 | NOT_RUN | NOT_RUN | PENDING (expected: paper_ratio_adaptive is the most aggressive paper-quantity consumer — `PaperRatioAdaptiveScheduler(base=CodimSheet)` per `adaptive_reflow/algorithm/scheduler/adaptive.py:2035`; expected to flip REGRESSES → WINS if cosine is the cause) | PENDING |
| 8 | CIFAR paper_ratio_adaptive/seed43 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 9 | CIFAR paper_ratio_adaptive/seed44 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 10 | CIFAR convergence_adaptive/seed42 | NOT_RUN | NOT_RUN | PENDING (expected: convergence_adaptive uses `ConvergenceAdaptiveScheduler(base=cosine)` with PID-lite on `_smoothed_w2` per CLM-026; partial paper-quantity consumer — may flip direction if the convergence signal overrides cosine regression) | PENDING |
| 11 | CIFAR convergence_adaptive/seed43 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 12 | CIFAR convergence_adaptive/seed44 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 13 | CIFAR nfe_aware_memory/seed42 | NOT_RUN | NOT_RUN (smoke test at N=50 only: REGRESSES +3.11%, baseline_fid=333.08, framework_fid=343.44, framework_total_nfe=4 — much smaller magnitude than cosine) | PENDING (smoke result suggests `NFEAwareMemoryScheduler` may not regress as severely as cosine; needs full N=200 3-seed sweep to confirm) | PENDING |
| 14 | CIFAR nfe_aware_memory/seed43 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 15 | CIFAR nfe_aware_memory/seed44 | NOT_RUN | NOT_RUN | PENDING | PENDING |

**CIFAR cells compared: 15. Cells with Wave 281 result data: 1 (cosine/seed42 complete + 2 in FID computation). Direction flips: 0. Hypothesis-confirmed cells: 1 (cosine re-run reproduces REGRESSION). Hypothesis-rejected cells: 0.**

### 1.2 LineageFlow (R1 — `Wave 281 lineageflow-paper-controllers`, NOT STARTED)

The LineageFlow sweep is protein-axis (Wave 158 P2 byte-stable reference + Wave 225 P4 tier-aware counterfactual). All 12 cells pending driver invocation.

| # | Cell | Cosine baseline (Wave 280 P / Wave 158 P2) | Paper-controller result (Wave 281) | Direction flip? | Verdict |
|---:|---|---|---|---|---|
| 16 | LineageFlow cosine/seed42 | `hmmscan_total_hits` baseline from Wave 158 P2 (NOT_RUN in Wave 280 P R1 sweep; the Wave 280 P R1 sweep used `LineageFlowAdapter + default_cosine_scheduler(cycle_length=N_ROUNDS)` per `tools/experiments/run_lineageflow_comparison.py:278`) | NOT_RUN | PENDING | PENDING |
| 17 | LineageFlow cosine/seed43 | same | NOT_RUN | PENDING | PENDING |
| 18 | LineageFlow cosine/seed44 | same | NOT_RUN | PENDING | PENDING |
| 19 | LineageFlow codim/seed42 | NOT_RUN (codim was not used in R1 sweep) | NOT_RUN | PENDING (expected: codim is paper-quantity-driven but `LineageFlowAdapter.profile_residual_fn` may not be wired; if not wired, codim falls back to `default_cosine_scheduler` behavior — needs deferred check per `scheduler-per-cell-summary.md` §4.1) | PENDING |
| 20 | LineageFlow codim/seed43 | same | NOT_RUN | PENDING | PENDING |
| 21 | LineageFlow codim/seed44 | same | NOT_RUN | PENDING | PENDING |
| 22 | LineageFlow paper_ratio_adaptive/seed42 | NOT_RUN | NOT_RUN | PENDING (needs `LineageFlowAdapter.profile_residual_fn` wiring; deferred if not exposed) | PENDING |
| 23 | LineageFlow paper_ratio_adaptive/seed43 | same | NOT_RUN | PENDING | PENDING |
| 24 | LineageFlow paper_ratio_adaptive/seed44 | same | NOT_RUN | PENDING | PENDING |
| 25 | LineageFlow convergence_adaptive/seed42 | NOT_RUN | NOT_RUN | PENDING (convergence-adaptive may not need adapter-level wiring since it tracks `_smoothed_w2` from the per-round trajectory) | PENDING |
| 26 | LineageFlow convergence_adaptive/seed43 | same | NOT_RUN | PENDING | PENDING |
| 27 | LineageFlow convergence_adaptive/seed44 | same | NOT_RUN | PENDING | PENDING |

**LineageFlow cells compared: 12. Cells with Wave 281 result data: 0. Direction flips: 0. Hypothesis-confirmed cells: 0. Hypothesis-rejected cells: 0.**

### 1.3 FlowMol3 (R3 / K1 — `Wave 281 flowmol3-paper-controllers`, NOT STARTED)

The FlowMol3 sweep is chemistry-axis (Wave 87 N=1000 byte-stable reference + Wave 275 P4 weak-metric remediation). K1 + R3 paper-controllers planned.

| # | Cell | Cosine baseline (Wave 280 P / Wave 87) | Paper-controller result (Wave 281) | Direction flip? | Verdict |
|---:|---|---|---|---|---|
| 28 | FlowMol3 K1 cosine/seed42 | `rdkit_validity_pct` baseline from Wave 87 byte-stable seed=42 (NOT_RUN in Wave 280 P K1 sweep — K1 is metric-only, not scheduler fix) | NOT_RUN | PENDING | PENDING |
| 29 | FlowMol3 K1 codim/seed42 | NOT_RUN | NOT_RUN | PENDING (needs `FlowMol3Adapter.profile_residual_fn` wiring per `scheduler-per-cell-summary.md` §4.1) | PENDING |
| 30 | FlowMol3 K1 evidence_driven/seed42 | NOT_RUN | NOT_RUN | PENDING | PENDING |
| 31 | FlowMol3 R3 cosine/seed42 | `fg_dev` baseline from Wave 87 / Wave 82 (NOT_RUN in Wave 280 P R3 sweep on the cosine row, but R3 is the canonical paper metric per `scheduler-per-cell-summary.md` row 3) | NOT_RUN | PENDING | PENDING |
| 32 | FlowMol3 R3 codim/seed42 | NOT_RUN | NOT_RUN | PENDING (fg_dev IS the empirical handle on paper Proposition 3 `C_g`; codim should consume this — expected to be the most likely flip cell) | PENDING |
| 33 | FlowMol3 R3 evidence_driven/seed42 | NOT_RUN | NOT_RUN | PENDING (evidence_driven consumes e_rho + evidence_ratio; should also consume fg_dev signal) | PENDING |

**FlowMol3 cells compared: 6. Cells with Wave 281 result data: 0. Direction flips: 0. Hypothesis-confirmed cells: 0. Hypothesis-rejected cells: 0.**

---

## 2. Aggregate cross-reference statistics (PARTIAL)

| Axis | Cells planned | Cells with Wave 281 data | Direction flips confirmed | HYPOTHESIS_CONFIRMED | HYPOTHESIS_REJECTED |
|---|---:|---:|---:|---:|---:|
| CIFAR (R5b / K3+R5b) | 15 | 1 | 0 | 1 (cosine/seed42 re-run reproduces REGRESSION) | 0 |
| LineageFlow (R1) | 12 | 0 | 0 | 0 | 0 |
| FlowMol3 (R3 / K1) | 6 | 0 | 0 | 0 | 0 |
| **TOTAL** | **33** | **1** | **0** | **1** | **0** |

---

## 3. What the single completed CIFAR cosine/seed42 cell tells us

### 3.1 Cosine baseline is reproducible

The Wave 281 cosine/seed42 cell at N=200 reproduces the Wave 280 P cosine/seed42 cosine direction (REGRESSION) and produces a similar framework FID (461.19 vs 466.81, -1.21% difference). The baseline FID shifts (275.11 vs 306.57) due to:
- Sample size (N=200 vs N=100) — InceptionV3 feature extraction variance drops with sample size
- Possibly different RNG (Wave 281 uses a different seed offset scheme in the driver)

The **framework FID is the load-bearing number** and it is consistent across Wave 280 P and Wave 281 (466.81 → 461.19). This corroborates the Wave 280 P §3.1 finding that **the framework chain is byte-stable across seeds** (framework samples are deterministic given the same scheduler config), and the cosine regression is therefore a **fundamental property of the CosineAnnealScheduler + cosine_ramp_strength=0.5 + K3+R5b config**, not a sample-size artefact.

### 3.2 Cosine regression scales with sample size

The ΔFID% went from +52.27% (N=100) to +67.64% (N=200). The framework FID is essentially constant (466.81 vs 461.19), but the baseline FID dropped from 306.57 to 275.11 (a real improvement in baseline FID under larger sample — Inception feature distribution converges). This **inflates** the ΔFID% ratio because the baseline denominator shrinks while the framework numerator stays constant.

This is a methodologically important observation: **the ΔFID% is not stable across sample sizes when the framework term is constant**. Future Wave 282+ sweeps should report absolute ΔFID (framework_fid - baseline_fid) alongside ΔFID% to disambiguate ratio scaling from genuine regression magnitude.

### 3.3 What we still don't know

The Wave 281 cosine/seed42 cell does NOT tell us whether **paper-grounded controllers would flip the direction**. We need:
1. codim/seed42 (FID computation in progress)
2. cosine/seed43 (FID computation in progress)
3. All 12 remaining cells (not started)

Per `scheduler-per-cell-summary.md` §4.1 the **most likely flip cells** are:
- CIFAR codim/seed{42,43,44} — codim consumes A_g/B_g/C_g via `_paper_evidence_balance`; K3+R5b's REGRESSION is hypothesized to be a cosine-induced false negative
- CIFAR paper_ratio_adaptive/seed{42,43,44} — most aggressive paper-quantity consumer; expected to flip if cosine is the cause
- FlowMol3 R3 codim/seed42 — fg_dev IS the empirical handle on C_g; codim should consume this; expected to be the most likely flip cell

The **least likely flip cells** are:
- CIFAR convergence_adaptive/seed{42,43,44} — uses `default_cosine_scheduler` as base + PID on `_smoothed_w2`; partial paper-quantity consumer; may not flip if the cosine floor dominates
- CIFAR nfe_aware_memory/seed{42,43,44} — only consumes NFE budget + `e_rho` indirectly via memory_fraction scaling; not a direct paper-quantity consumer

---

## 4. Verification status (PARTIAL)

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
30 passed in 1.06s   # unchanged from Wave 280 P

$ python3 tools/check_claims_consistency.py
**No drift detected.**

$ ruff check tools/run_sota_cifar_experiment.py tools/compute_cifar_fid.py
All checks passed!
```

* D.4 30/30 regression vectors: **PASS** (the sweep did not touch any framework internals).
* Claims consistency: **No drift detected**.
* ruff on the sweep tool + FID script: **0 findings**.

---

## 5. Honest disclosure — partial completion

Per the Wave 268 strict-clean rule and the user's "做了算法上的改进就该想办法去做实验上的验证" directive, the audit proceeds with the **partial** 1/15 CIFAR completed cell + 2/15 in FID computation + 0/12 LineageFlow + 0/6 FlowMol3. The audit reports:
1. **What was completed** (CIFAR cosine/seed42 — full FID + summary.json).
2. **What is in FID computation** (CIFAR codim/seed42, cosine/seed43 — samples + per_round_metrics.csv present, no summary.json).
3. **What is pending** (12 CIFAR + 12 LineageFlow + 6 FlowMol3 cells).

**This cross-reference doc is to be UPDATED ADDITIVELY** as each Wave 281 cell completes. The table in §1 is the canonical template; each new cell's row gets filled in as the sweep progresses. The aggregate statistics in §2 are recomputed at each update.

The remaining work is substantial:
- 14 CIFAR cells × ~3 min wall each = ~42 min wall (RTX PRO 6000 Blackwell, no contention)
- 12 LineageFlow cells × ~10 min wall each = ~120 min wall (Wave 158 P2 baseline)
- 6 FlowMol3 cells × ~30 min wall each = ~180 min wall (Wave 87 N=1000 reference)
- **Total remaining wall time: ~5.7 hours** under no contention

This exceeds any single subagent invocation budget. The sweep is expected to run in **incremental batches** over Wave 281 phases, with each batch updating this cross-reference doc additively.

---

## 6. What the Wave 282 P cross-reference does NOT establish

1. **Direction-flip evidence for any cell.** Only 1/33 cells has a Wave 281 result, and that cell is the cosine baseline re-run (not a paper-grounded controller). **No direction flip can be confirmed until the codim/paper_ratio_adaptive/evidence_driven/convergence_adaptive/nfe_aware_memory cells complete.**
2. **Statistical significance of any flip.** Even when the codim/paper_ratio_adaptive cells complete, the Wave 280 P §3.1 finding that **framework samples are byte-identical across seeds** means d_z will be dominated by baseline noise variance. The framework FID will be constant across seeds within a given (N, scheduler) config, so the paired t-test statistic will be (mean_ΔFID%) / std(baseline_noise). This will produce a high d_z for any non-zero ΔFID%, which inflates the apparent statistical strength.
3. **The hypothesis that cosine is the cause of the Wave 280 P REGRESSES results.** Without the codim/paper_ratio_adaptive cells, we cannot falsify or confirm this hypothesis.
4. **The framework chain seed-propagation fix** (Wave 280 P §3.1 + Wave 280 P §9.4). The framework chain does not currently thread `seed` into `build_initial_state`, so framework samples are byte-identical across seeds. This is a **load-bearing bug for future multi-seed sweeps** but does not affect the Wave 281 cosine/seed42 cell (which is the same as Wave 280 P cosine/seed42 in this respect).

---

## 7. Edit discipline

* `tools/run_sota_cifar_experiment.py` — **NOT modified** (vendored scoring script; Wave 281 driver imports `_make_adapter` + `_run_baseline` + `_compute_fid` + `FID_EXTRACTOR_FAMILY` from it but does not modify the file).
* `tools/compute_cifar_fid.py` — **NOT modified** (FID computation uses the canonical InceptionV3FIDEvaluator path).
* `adaptive_reflow/adapters/rectified_flow_cifar.py` — **NOT modified** (the Wave 275 K3+R5b constant flip is the canonical state; the Wave 281 driver reads it but does not change it).
* `/tmp/wf281_paper_controllers_driver.py` — sweep driver (NOT committed per "claude相关的确实不要commit"; lives in `/tmp/`).
* `/tmp/wf281-cifar/{cosine,codim,paper_ratio_adaptive,convergence_adaptive,nfe_aware_memory}/seed{42,43,44}/` — sweep artifacts (per-cell `baseline_samples.npz`, `<scheduler>_samples.npz`, `per_round_metrics.csv`, `summary.json`).
* `/tmp/wf281-lineageflow/` — NOT YET CREATED.
* `/tmp/wf281-flowmol3/` — NOT YET CREATED.

---

## 8. Next steps (Wave 282+ follow-up)

1. **Complete the remaining 14 CIFAR cells.** Two cells (`codim/seed42`, `cosine/seed43`) are in FID computation; the other 12 are not started. Expected ~42 min wall.
2. **Start the LineageFlow paper-controller sweep.** 12 cells (4 schedulers × 3 seeds, N=500). Expected ~120 min wall. Requires `LineageFlowAdapter.profile_residual_fn` wiring check per `scheduler-per-cell-summary.md` §4.1.
3. **Start the FlowMol3 paper-controller sweep.** 6 cells (K1 + R3 × 3 schedulers, N=1000). Expected ~180 min wall. Requires `FlowMol3Adapter.profile_residual_fn` wiring check per `scheduler-per-cell-summary.md` §4.1.
4. **Fix the framework chain seed-propagation bug** (Wave 280 P §9.4). Thread `seed` into `build_initial_state` so framework samples vary across seeds.
5. **Report absolute ΔFID alongside ΔFID%** in all Wave 282+ sweep cells (per §3.2 observation).
6. **UPDATE THIS DOC ADDITIVELY** as each Wave 281 cell completes.

---

## 9. User directives honored

- **"当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比"** — honored via the Wave 281 cosine re-run; the cosine baseline is preserved verbatim per Wave 268 strict-clean rule, and the paper-grounded sweep cells are appended additively.
- **"有查清楚以前我们哪些任务用的是哪些调度器吗"** — honored via the companion audit `docs/audit/scheduler-per-cell-summary.md`; all 13 R-cell + weak-claim headline sweeps used `CosineAnnealScheduler`, the only non-paper-quantity consumer among the 5 paper-grounded controllers.
- **"做了算法上的改进就该想办法去做实验上的验证"** — partially honored (Wave 281 in progress, 1/15 CIFAR cells completed).
- **"claude相关的确实不要commit"** — honored (driver lives in `/tmp/`).
- **"也要做 sweep 验证"** — honored at the per-cell level (WAVE247_SEED-controlled; scheduler family threaded through).

---

## 10. Honest summary

* **Goal achieved:** partial. 1 of 33 cells has a full Wave 281 result (cosine baseline re-run); 2 cells are in FID computation.
* **Direction of result (cosine/seed42):** REGRESSION (+67.64% ΔFID, N=200), reproducing the Wave 280 P cosine/seed42 REGRESSION at N=100. The cosine baseline is reproducible; the framework FID is constant across Wave 280 P and Wave 281 cosine cells.
* **Direction flips confirmed:** 0 (insufficient data).
* **Hypothesis-confirmed cells:** 1 (CIFAR cosine/seed42 — cosine baseline REGRESSION is reproducible).
* **Hypothesis-rejected cells:** 0.
* **Sub-finding (load-bearing):** ΔFID% scales with sample size when framework FID is constant. The cosine/seed42 ΔFID% went from +52.27% (N=100) to +67.64% (N=200) because the baseline FID dropped with sample size (better Inception feature distribution), not because the framework got worse.
* **Sub-finding (load-bearing, inherited from Wave 280 P §3.1):** framework samples are byte-identical across seeds in the Engine + adapter chain path. The framework FID is constant across seeds for a given (N, scheduler) config.
* **Statistical strength:** not yet computable (only 1 cell completed).
* **Frame-vs-baseline claim promotion:** none yet (insufficient data).
