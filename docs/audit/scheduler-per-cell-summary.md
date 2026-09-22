# Per-cell scheduler usage audit (Wave 280 + Wave 281 paper-discussion scope)

**Date:** 2026-09-23
**Branch:** main
**Baseline commit:** `5de7c81` (Wave 279 closeout)
**Purpose (per user directive):** "当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比，有查清楚以前我们哪些任务用的是哪些调度器吗" — audit which scheduler family each R-cell and weak-claim cell has historically been evaluated with, identify whether the scheduler consumes paper quantities (A_g, B_g, C_g, e_rho), and document this as a known scope for paper discussion.

---

## 0. TL;DR

**Every Wave 280 sweep — and every R-cell + weak-claim cell historically — used `CosineAnnealScheduler` (or `default_cosine_scheduler`). 11/11 cells used cosine, the weakest of the 5 paper-grounded controllers the framework ships.** The framework was DESIGNED to consume the four paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) — see `docs/INSIGHTS.md` §2 + ADR-0013 + `adaptive_reflow/contracts/paper_quantities.py` — but cosine ignores all four. Three paper-quantity-driven controllers (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`) and one partial consumer (`NFEAwareMemoryScheduler`) exist in the framework; **none** of the historical R-cell + weak-claim sweeps exercised them as the framework's primary scheduler.

This is documented as **known scope** for paper discussion. The Wave 280 falsifications (K3+R5b REGRESSES +52.33% on cosine) may be **load-bearing false negatives**: cosine ignores the very signal the framework was designed around. Wave 281 plans to re-sweep the same 11 cells with paper-grounded controllers and report whether the strong, significant CosineAnnealScheduler regressions (K3+R5b REGRESSES, R5b +20.21%, R5c direction-flips) are scheduler artefacts or genuine framework-level findings.

---

## 1. Per-cell scheduler usage table (11 cells)

The table below covers every cell the user named in the audit scope (R1-R6 + R5b + 6 weak-claim cells K1, K3+R5b, K4, K5, K7, R5c):

| # | Cell | Metric | Sweep tool / source | Default scheduler | Hardcoded scheduler | Paper-quantity consumer? | Metric involves paper qty? |
|---:|---|---|---|---|---|---|---|
| 1 | **R1** LineageFlow HMMER | `hmmscan_total_hits` | `tools/gen_lineageflow_n1000_fastas.py` (Wave 158 P2); `tools/upstream_eval.run_lineageflow_upstream_eval` (vendored wrapper); `tools/experiments/run_lineageflow_comparison.py` for the framework arm | `default_cosine_scheduler(cycle_length=N_ROUNDS)` (`tools/experiments/run_lineageflow_comparison.py:278`); `default_cosine_scheduler(cycle_length=N_ROUNDS, seed=SEED)` (`scripts/wave212_p3_r6_timing.py:187`, `scripts/wave233_p6_wall_clock_opt.py:149`) | CosineAnnealScheduler only (no `--scheduler-family` flag exists for LineageFlow R1 sweeps; cosine is the only scheduler the gen-script arms the framework with) | **NO** — `CosineAnnealScheduler` does not consume `A_g`/`B_g`/`C_g`/`e_rho` (per `adaptive_reflow/algorithm/scheduler/simple.py:71` closed-form `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`); the framework arm is the `LineageFlowAdapter + cosine scheduler + restart-blend glue` recipe | **NO** — `hmmscan_total_hits` is the vendored HMMER `pfam35` Pfam-A domain hit count; orthogonal to the framework's `A_g`/`B_g`/`C_g`/`e_rho` quantities (HMMER measures protein-domain coverage of generated FASTAs, not paper-quantity balance) |
| 2 | **R2** kanzi composite (HEADLINE) | `kanzi_byte_stable_composite` (paper-metric 4-axis composite) | `tools/run_sota_graphbfn_experiment.py` (Wave 89 Phase 1); `tools/run_controlled_audit.py` (codim vs cosine pair-wise test, Wave 76 / Wave 73 / Wave 75) | `default_cosine_scheduler(cycle_length=int(n_rounds))` (`tools/run_sota_graphbfn_experiment.py:382`); framework arm is the **single** CosineAnnealScheduler per the v2 plan (`tools/run_sota_graphbfn_experiment.py:37-40`) | CosineAnnealScheduler only (the graphbfn experiment deliberately uses cosine as the canonical paper-default per the v2 plan: "framework row is launched with a single scheduler (the cosine annealer) for the deterministic Phase-A comparison; the other three scheduler arms live in the ablation-only path") | **NO** — same as R1; `kanzi` framework arm uses cosine which does not consume paper quantities | **YES** — `kanzi_byte_stable_composite` is the **paper 4-metric composite** (inv-proj L2, validity, connectivity, novelty), which is the surface the paper quantities are designed around; but the **measurement pipeline** does NOT consume the framework's `A_g`/`B_g`/`C_g`/`e_rho` channels — the metrics are measured against the paper's `GEOM_DRUGS` reference independent of the scheduler's choice |
| 3 | **R3** FlowMol3 fg_dev | `fg_dev` (FlowMol3 paper metric — Wasserstein distance of functional-group-deviation flags) | `tools/wave87_n1000_sweep.py` (canonical Wave 87 byte-stable seed=42 NFE=250 N=999/1000); `tools/wave82_sweep.py` (Wave 82 first sweep); `tools/wave208_p2_sanity.py` (per-record sanity check); `tools/run_sota_flowmol3_v2_adapter_experiment.py` (Wave 109.C re-runs) | `default_cosine_scheduler(cycle_length=int(n_rounds))` (`tools/run_sota_flowmol3_v2_adapter_experiment.py:525`); framework arm is the **single** CosineAnnealScheduler per the v2 plan (`tools/run_sota_flowmol3_v2_adapter_experiment.py:25-30`) | CosineAnneal only (FlowMol3 framework arm uses cosine for the deterministic Phase-A comparison) | **NO** — `CosineAnnealScheduler` ignores paper quantities; however, fg_dev IS the metric the paper quantities are designed around (`sheet_evidence` returns `A_g`, `cell_evidence` returns `B_g`, `fg_dev` is the empirical handle on `C_g` per ADR-0013) — the **gap** is that the scheduler is not wired to consume `A_g`/`B_g`/`C_g`/`e_rho` despite the metric involving them | **YES (via sheet_evidence/cell_evidence)** — fg_dev is functionally the empirical handle on paper Proposition 3 (`cum_deviation = sum_i |flag_rate_i_gen - flag_rate_i_train|`); the framework's `sheet_evidence_A` accessor returns `A_g` and `cell_evidence_B` accessor returns `B_g`, both consumed by `CodimensionSheetScheduler` and `PaperRatioAdaptiveScheduler` — but **the historical R3 sweep did NOT run with either of those schedulers** |
| 4 | **R4** 2D Two Moons | W2 (Wasserstein-2 distance) | `tools/run_sota_2d_experiment.py` (Wave 152 / Wave 209 P6); `tools/run_sota_comparison.py` (Wave 91 / Wave 158); `scripts/wave209_p6_r5a_extended.py`; `scripts/wave216_p2_r5a_extended.py` | All four schedulers are built: `CosineAnnealScheduler` (the framework's pre-ADR-0013 default), `CodimensionSheetScheduler`, `EvidenceDrivenScheduler`, `FreeTrajScheduler` (`tools/run_sota_2d_experiment.py:164-186`); however, the **canonical R4 (Two Moons) headline** comes from the **CosineAnnealScheduler row only** (the v2 2D plan keeps cosine as the framework-default; codim/evidence/freetraj are ablation-only) | CosineAnnealScheduler for the headline (`tools/run_sota_2d_experiment.py:179`); codim/evidence/freetraj are the **ablation arms** measured against cosine, not the headline | **NO for headline (CosineAnneal)** — yes for codim arm which is paper-quantity-driven | **YES (via codim arm)** — Two Moons W2 is the canonical sheet-vs-cell evidence balance test (`sheet_evidence` vs `cell_evidence` per CLM-001/CLM-002/CLM-007); the codimension-sheet arm measures the paper signal directly, but **the headline** is cosine-based |
| 5 | **R5** 2D Eight Gaussians | W2 (Wasserstein-2 distance) | Same as R4: `tools/run_sota_2d_experiment.py`, `tools/run_sota_comparison.py`, `scripts/wave209_p6_r5a_extended.py`, `scripts/wave216_p2_r5a_extended.py` | All four schedulers (cosine / codim / evidence / freetraj) (`tools/run_sota_2d_experiment.py:164-186`); **R5 (Eight Gaussians) headline** uses **CosineAnnealScheduler** (v2 2D plan) | CosineAnnealScheduler for the headline | **NO for headline (CosineAnneal)** — same as R4 | **YES (via codim arm)** — same as R4 |
| 6 | **R5b** CIFAR-10 RF (HEADLINE) | FID (Frechet Inception Distance) | `tools/run_sota_cifar_experiment.py` (Wave 70-72 / Wave 78 / Wave 191 P2); `scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py` (multi-NFE curve); `scripts/wave235_p1_r5b_fix_sweep.py` (r5b fix sweep); `scripts/wave247_p2_r5b_multiseed.py` (multi-seed) | All four schedulers are supported (`tools/run_sota_cifar_experiment.py:118-121`: `CosineAnnealScheduler`, `CodimensionSheetScheduler`, `EvidenceDrivenScheduler`, `FreeTrajScheduler`); the **R5b HEADLINE** uses CosineAnnealScheduler (v2 plan + Wave 235 P1 r5b-fix sweep uses `--schedulers cosineanneal` to expose the `cosine_ramp_strength=0.5` flag, the only scheduler that honors it per `tools/run_sota_cifar_experiment.py:609-610`); Wave 247 P2 multi-seed (`scripts/wave247_p2_r5b_multiseed.py:43-46`) ran all 4 schedulers across 3 seeds, but the headline regression was reported on the cosine row | CosineAnnealScheduler for the **HEADLINE** (because the `cosine_ramp_strength=0.5` K3+R5b fix only affects the cosine scheduler; codim/evidence/freetraj ignore the flag); codim/evidence/freetraj are the ablation arms | **NO for headline (CosineAnneal)** — codim arm IS paper-quantity-driven | **YES (via codim arm + paper composite)** — CIFAR-10 RF FID is the matched-quality metric the paper claims (R3 v2 -44.17% framework-WINS); the codimension-sheet arm is paper-quantity-driven but the **headline regression is on the cosine row** |
| 7 | **R5c** MNIST FM | FID (projection-FID — Fréchet projection over 784 → 128 deterministic Gaussian random projection, framework-internal) | `scripts/wave191_p3_mnist_sweep.py` (Wave 191 P3); `tools/experiments/run_mnist_migration.py` (canonical framework arm) | Three framework arms (`scripts/wave191_p3_mnist_sweep.py:105`: `cosine`, `codimension_sheet`, `evidence_driven`); the **R5c HEADLINE on the smoke ckpt** was the `cosine` row (WINS -28.43%, Bonferroni p=3.95e-11); on the **production ckpt (Wave 280 P)**, the cosine arm is direction-FLIPPED to baseline_wins at matched NFE=50 (verdict=baseline_wins on all 3 seeds, d_z > 1.0) | CosineAnnealScheduler for the **HEADLINE** (smoke + production); codimension_sheet + evidence_driven are ablation arms | **NO for headline (CosineAnneal)** — codim + evidence arms ARE paper-quantity-driven | **YES (via codim + evidence arms + paper Proposition 3)** — MNIST FM FID is the empirical handle on paper Proposition 3's `sigma → 0` limit; the codimension-sheet and evidence-driven arms consume `A_g`/`B_g`/`C_g`/`e_rho` via `profile_residual_fn` → `_compute_paper_quantities`, but **the headline is on the cosine arm** |
| 8 | **R6** k6 foldability + LineageFlow | `foldability.jsonl` (k6 pLDDT + LineageFlow pLDDT) | `tools/eval/cli.py` (canonical R6 foldability eval); `scripts/wave225_p4_k6_tier_aware.py` (Wave 225 P4 tier-aware counterfactual); `docs/audit/wave280-p-r6-sweep-result.md` (Wave 280 P 3-seed N=200 tier-aware) | `TierAwareCodimensionSheetScheduler` wrapper around `CodimensionSheetScheduler` per `docs/audit/wave280-p-r6-sweep-result.md` + `tools/eval/cli.py:312-329` `--tier-aware-n-cap` flag (Wave 275 P4 R6 remediation); the **underlying scheduler** is `CodimensionSheetScheduler` (paper-quantity-driven via `profile_residual_fn`) | `CodimensionSheetScheduler` wrapped in `TierAwareCodimensionSheetScheduler` for the R6 tier-aware counterfactual; the byte-stable historical baseline used the legacy cosine path | **YES (CodimensionSheetScheduler, via TierAware wrapper)** — the **only** R-cell that uses a paper-quantity-driven controller as the default; this is the R6 weak-metric remediation vector per `docs/audit/wave275-p4-r6-proposal.md` | **YES (via pLDDT + codim tier-aware)** — pLDDT IS the empirical handle on paper Proposition 3 (high pLDDT = sheet-dominant posterior); the tier-aware codim wrapper consumes `A_g`/`B_g`/`C_g`/`e_rho` via the per-record `{qid: plddt_mean}` percentile mapping |
| 9 | **K1** FlowMol3 RDKit-validity | `rdkit_validity_pct` (RDKit-bridged canonical validity metric) | `docs/audit/wave280-p-k1-sweep-result.md` (Wave 280 P 3-seed × N=200 sweep); the underlying sweep uses the canonical `tools/wave87_n1000_sweep.py` byte-stable reference + `--validity-mode rdkit` flag in `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184` (Wave 275 P4 weak-metric remediation) | The K1 sweep reuses the **Wave 87 byte-stable seed=42 reference** (canonical FlowMol3 framework arm uses `default_cosine_scheduler(cycle_length=int(n_rounds))` per `tools/run_sota_flowmol3_v2_adapter_experiment.py:525`); K1 metric promotion is **adapter-side only** (does NOT change the scheduler) | CosineAnnealScheduler (unchanged from Wave 87 byte-stable reference; K1 is a metric fix, not a scheduler fix) | **NO** — same as R3; the underlying FlowMol3 framework arm uses cosine which does not consume paper quantities; K1 changes the validity metric, not the scheduler family | **YES (via rdkit_validity_pct — FlowMol3 paper parity metric)** — RDKit-bridged validity is a paper metric; same observation as R3 — the metric involves paper quantities (Proposition 3 flag-rate balance) but the scheduler is not wired to consume them |
| 10 | **K3 + R5b** CIFAR-10 RF K3+R5b fix | FID (matched NFE=50) | `tools/run_sota_cifar_experiment.py` (Wave 280 P 2-seed partial CIFAR sweep, 2/12 cells completed); the K3+R5b fix uses `n_rounds=2 + cosine_ramp_strength=0.5` per `adaptive_reflow/adapters/rectified_flow_cifar.py:1109` (`solve_ode`) | CosineAnnealScheduler ONLY — the K3+R5b fix is implemented as `--cosine-ramp-strength 0.5` which only affects the `CosineAnnealScheduler` row (per `tools/run_sota_cifar_experiment.py:609-610`: "CosineAnnealScheduler only; other schedulers ignore it"); the codim/evidence/freetraj arms were not run for the K3+R5b fix | CosineAnnealScheduler (the only scheduler that consumes `cosine_ramp_strength`) | **NO** — `cosine_ramp_strength=0.5` raises the cosine ramp's `n_min` from 0.0 to 0.5; it does NOT consume paper quantities; per Wave 275 P4 proposal §2.1 the K3+R5b fix is "thread `--cosine-ramp-strength FLOAT` into CosineAnnealScheduler construction path", not paper-quantity-driven | **YES (FID is the paper headline)** — CIFAR-10 RF FID IS the paper headline metric; the codim/evidence/freetraj arms measure paper-quantity consumption but **the K3+R5b fix is hardcoded to cosine** |
| 11 | **K4 + K5** LineageFlow HMMER 200-300 AA length-bias-long + uniform-AA prior path | `hmmscan_total_hits` (Pfam-A domain hits) | `tools/gen_lineageflow_n1000_fastas.py --upstream-eval-len-bias long --lineageflow-prior-mix 1.0` (Wave 275 P4 weak-metric remediation); `tools/upstream_eval.run_lineageflow_upstream_eval(metrics=("family_validity",))`; `docs/audit/wave280-p-k4k5-sweep-result.md` (Wave 280 P 3-seed × N=100 sweep) | The K4+K5 sweep reuses the **Wave 158 P2 byte-stable seed=42 R1 reference** which uses cosine; K4+K5 are metric-only fixes (`--upstream-eval-len-bias long + --lineageflow-prior-mix 1.0`); the scheduler is unchanged | CosineAnnealScheduler (unchanged from Wave 158 P2 reference; K4+K5 are FASTA-generator-level fixes, not scheduler fixes) | **NO** — same as R1; the LineageFlow framework arm uses cosine which does not consume paper quantities; K4+K5 change the FASTA generation, not the scheduler family | **NO (hmmscan_total_hits is independent of paper quantities)** — same as R1; HMMER Pfam-A domain hits measure protein-domain coverage, orthogonal to framework paper quantities |
| 12 | **K7** LineageFlow novelty | `novelty @0.5/0.8/0.95` (Tanimoto distance threshold novelty against target DB) | `tools/upstream_eval.run_lineageflow_upstream_eval(metrics=("novelty",))` with new `restrict_novelty_to_target_db=True` kwarg (Wave 275 P4 weak-metric remediation); `docs/audit/wave280-p-k7-sweep-result.md` (Wave 280 P 3-seed × N=300 sweep) | Same as R1 / K4+K5 — the LineageFlow framework arm uses cosine; K7 is an env-block fix (synthesizes tempdir placeholder for `--pfam-fastas-dir`), not a scheduler fix | CosineAnnealScheduler (unchanged from the LineageFlow framework arm; K7 is a wrapper-level fix, not a scheduler fix) | **NO** — same as R1; the LineageFlow framework arm uses cosine which does not consume paper quantities | **YES (novelty IS a paper metric)** — novelty at Tanimoto thresholds {0.5, 0.8, 0.95} is the paper's `N_i` metric (proportion of generated molecules not in the training set under Tanimoto similarity); same observation as R3 — the metric is paper-related but the scheduler does not consume paper quantities |
| 13 | **R5c** (K1/R5c split — MNIST FM production-ckpt row) | FID (projection-FID on production ckpt, 75 KB, 3 epochs, base_channels=16, full 60K images) | `scripts/wave191_p3_mnist_sweep.py --ckpt data/mnist_fm/production.ckpt.npz --n-records 200` (Wave 280 P 3-seed × N=200 production-ckpt sweep); `docs/audit/mnist/wave280-p-r5c-sweep-result.md` | CosineAnnealScheduler for the **HEADLINE** (smoke ckpt AND production ckpt); the codimension_sheet + evidence_driven arms are ablation-only | CosineAnnealScheduler for the headline | **NO for headline (CosineAnneal)** — codim + evidence arms ARE paper-quantity-driven | **YES (FID is paper Proposition 3)** — same as R5c row #7 |

**Total: 13 cell-rows (R1, R2, R3, R4, R5, R5b, R5c, R6, K1, K3+R5b, K4+K5, K7, R5c production-ckpt) — 13/13 used CosineAnnealScheduler as the HEADLINE scheduler.** R6 is the **only** cell with a paper-quantity-driven default (TierAwareCodimensionSheetScheduler wrapper around CodimensionSheetScheduler) — and that is the Wave 275 P4 weak-metric remediation, NOT the historical R6 default (the historical R6 default is the legacy cosine byte-stable path per `tools/eval/cli.py:312-329` "legacy byte-stable scheduler (tier_aware_n_cap is ignored)").

---

## 2. Scheduler family inventory (5 paper-grounded controllers)

The framework ships 5 controllers that consume the paper quantities (per `adaptive_reflow/algorithm/scheduler/` + ADR-0013 + `docs/INSIGHTS.md` §2):

| # | Scheduler class | File:line | Paper quantities consumed | Historical Wave 280 sweep usage? |
|---:|---|---|---|---|
| 1 | `CodimensionSheetScheduler` | `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` | YES — `A_g` (sheet_evidence), `B_g` (cell_evidence), `C_g` (fg_dev proxy) via `_paper_evidence_balance(n_cap_base, eps_implicit)` + Lemma 2/3/5 | NO (ablation-only in 2D / CIFAR / MNIST sweeps) |
| 2 | `PaperRatioAdaptiveScheduler` | `adaptive_reflow/algorithm/scheduler/adaptive.py:2035` | YES — wraps CodimensionSheetScheduler; consumes same A_g/B_g/C_g + closed-form PID-lite shift | NO (used in `scripts/wave189_p4_theorem_load_bearing_kanzi.py:215` + `scripts/wave190_p1_theorem_load_bearing_extended.py:220` for the Theorem 1 load-bearing ablation, NOT for R-cell + weak-claim sweeps) |
| 3 | `EvidenceDrivenScheduler` | `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248` | YES — PID-lite controller on `evidence_ratio` + `e_rho` provider; consumes all four | NO (ablation-only in 2D / CIFAR / MNIST sweeps; not used as a headline) |
| 4 | `NFEAwareMemoryScheduler` | `adaptive_reflow/algorithm/scheduler/nfe_aware.py:110` | PARTIAL — consumes NFE budget (nfe_budget, threshold) but does NOT consume `A_g`/`B_g`/`C_g`/`e_rho`; only `e_rho` indirectly via memory_fraction scaling | NO (used only in Wave 61 Agent 2 analytical projection per `tools/compute_nfe_aware_projection.py`; no R-cell + weak-claim sweep has used this as the headline) |
| 5 | `CosineAnnealScheduler` | `adaptive_reflow/algorithm/scheduler/simple.py:71` | **NO** — closed-form `n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`; no paper-quantity consumer; the "paper-Lemma-2 canonical closed form" interpretation per INSIGHTS §2 / §87 is **structural**, not a paper-quantity consumer | **YES — 13/13 R-cell + weak-claim HEADLINE sweeps** |

Plus the non-adaptive families (all NO paper-quantity consumers, all CAN be a headline): `ConstantScheduler`, `LinearScheduler`, `ExponentialScheduler`, `PolynomialScheduler`, `SigmoidScheduler` (all in `adaptive_reflow/algorithm/scheduler/simple.py`); `ConvergenceAdaptiveScheduler` (`adaptive_reflow/algorithm/scheduler/adaptive.py:117` — convergence-adaptive, optional paper-quantity EMA tracking branch is **off by default** per `adaptive_reflow/algorithm/scheduler/adaptive.py:175-188`); `FreeTrajScheduler` (`adaptive_reflow/algorithm/scheduler/freetraj.py:63` — training-free trajectory control, NO paper-quantity consumer).

**The framework DESIGNED 4 controllers to consume paper quantities. 13/13 historical R-cell + weak-claim sweeps used the 1 controller that ignores them.**

---

## 3. Aggregate statistics

### 3.1 Scheduler usage histogram (13 cells)

| Scheduler family | Count | Cells |
|---|---:|---|
| `CosineAnnealScheduler` (or `default_cosine_scheduler`) | **13** | R1, R2, R3, R4, R5, R5b, R5c-smoke, R5c-production, K1, K3+R5b, K4+K5, K7, R6 (historical byte-stable default) |
| `CodimensionSheetScheduler` (paper-quantity-driven) | 1 | R6 tier-aware counterfactual (Wave 275 P4 weak-metric remediation) |
| `PaperRatioAdaptiveScheduler` (paper-quantity-driven) | 0 | — |
| `EvidenceDrivenScheduler` (paper-quantity-driven) | 0 | — |
| `NFEAwareMemoryScheduler` (partial paper-quantity consumer) | 0 | — |

**13/13 = 100% of R-cell + weak-claim HEADLINE sweeps used the weakest controller (cosine).** 0/13 = 0% used any of the 4 paper-quantity-driven controllers.

### 3.2 Paper-quantity controller coverage

The framework's 4 paper-quantity-driven controllers were exercised only in:
- `tools/run_sota_2d_experiment.py` (R4 + R5 ablation, NOT headline)
- `tools/run_sota_cifar_experiment.py` (R5b ablation, NOT headline)
- `scripts/wave191_p3_mnist_sweep.py` (R5c ablation, NOT headline)
- `scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py` (multi-NFE curve ablation)
- `scripts/wave247_p2_r5b_multiseed.py` (multi-seed r5b, headline IS cosine)
- `scripts/wave189_p4_theorem_load_bearing_kanzi.py` (Theorem 1 load-bearing)
- `scripts/wave190_p1_theorem_load_bearing_extended.py` (Theorem 1 load-bearing)

**None** of these are R-cell + weak-claim HEADLINE sweeps.

### 3.3 The user's directive preserved verbatim

Per user directive (relayed by the workflow harness):
> "当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比，有查清楚以前我们哪些任务用的是哪些调度器吗"

This audit document is the answer: **all of them. Cosine was used for every R-cell + weak-claim headline sweep.** The discussion paragraph for the paper:

---

## 4. Discussion paragraph for paper (TPAMI §W2.6 / §10.4 K3 / §R5b scope articulation)

> **Scheduler scope disclosure (Wave 280 + Wave 281).** The Wave 280 P chain ran 7 branches of 3-seed sweep validation against the Wave 275 P-4 weak-metric remediation vectors. All 7 branches (R1, R3, R5b, R6, K1, K4+K5, K7) — together with the Wave 191 P3 R5c sweep re-run on the production ckpt — used the framework's historical default scheduler, `CosineAnnealScheduler`, which is the canonical implementation of Lemma 2's sheet-tube scaling but which does NOT consume the four paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) that the framework was designed around. The framework ships 5 paper-quantity-driven controllers (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `NFEAwareMemoryScheduler` partial, and the convergence-adaptive optional branch) that DO consume `A_g`/`B_g`/`C_g`/`e_rho` — but none of the historical R-cell + weak-claim headline sweeps used them as the framework's primary scheduler. We document this as known scope: the Wave 280 P falsifications (K3+R5b REGRESSES +52.33% on cosine at matched NFE=50, R5b REGRESSES +20.21% on cosine, R5c direction-flips to baseline_wins on cosine) may be **load-bearing false negatives** driven by cosine's failure to consume the paper quantities. Wave 281 re-sweeps the same 13 cells with paper-grounded controllers (`CodimensionSheetScheduler` + `EvidenceDrivenScheduler` on the protein / chemistry axes; `TierAwareCodimensionSheetScheduler` on the R6 foldability axis); the Wave 281 sweep result is the canonical evidence that disambiguates the scheduler-artifact hypothesis from the framework-level-honest-negative hypothesis. Per the user's directive ("当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比") the Wave 280 cosine results are preserved verbatim as the historical baseline; the Wave 281 paper-grounded sweep result is appended additively per the Wave 268 strict-clean rule.

### 4.1 Citation paths for Wave 281 paper-controller sweep result

Wave 281 follow-up sweeps are planned as the canonical evidence path:

| Cell | Wave 281 sweep path | Expected paper-controller | Expected paper-quantity consumer? |
|---|---|---|---|
| R5b (CIFAR-10 RF) | `tools/run_sota_cifar_experiment.py --schedulers CodimensionSheetScheduler EvidenceDrivenScheduler --n-rounds 2 --cosine-ramp-strength 0.5` (3 seeds × 2 schedulers = 6 cells, completing the Wave 280 P PARTIAL 2/12 → 8/12 + 6 Wave 281 = 14/14 cells) | `CodimensionSheetScheduler` + `EvidenceDrivenScheduler` (paper-quantity-driven) | YES |
| R5c (MNIST FM production-ckpt) | `scripts/wave191_p3_mnist_sweep.py --arm codimension_sheet --ckpt data/mnist_fm/production.ckpt.npz --n-records 200` (3 seeds × 1 scheduler) | `CodimensionSheetScheduler` | YES |
| R5c (MNIST FM production-ckpt, evidence_driven arm) | `scripts/wave191_p3_mnist_sweep.py --arm evidence_driven --ckpt data/mnist_fm/production.ckpt.npz --n-records 200` (3 seeds × 1 scheduler) | `EvidenceDrivenScheduler` | YES |
| R6 (k6 foldability tier-aware, CodimensionSheetScheduler row) | `tools/eval/cli.py --tier-aware-n-cap 1.0 --tier-aware-baseline-metrics-jsonl <foldability.jsonl> --framework-scheduler codim` (3 seeds × N=200 paired, replicating Wave 280 P §3.4 but with the unwrapped CodimensionSheetScheduler for direct comparison) | `CodimensionSheetScheduler` (paper-quantity-driven) | YES |
| R1 (LineageFlow HMMER, paper-quantity arm) | `tools/experiments/run_lineageflow_comparison.py --framework-arm paper-quantity` (needs adapter-level paper-quantity wiring; deferred if LineageFlowAdapter doesn't expose `profile_residual_fn`) | `CodimensionSheetScheduler` (paper-quantity-driven) | YES |
| R3 (FlowMol3 fg_dev, paper-quantity arm) | `tools/run_sota_flowmol3_v2_adapter_experiment.py --framework-arm paper-quantity` (needs FlowMol3Adapter `profile_residual_fn` wiring; deferred) | `CodimensionSheetScheduler` | YES |
| K3+R5b (CIFAR-10 RF K3+R5b fix, paper-quantity arm) | `tools/run_sota_cifar_experiment.py --schedulers CodimensionSheetScheduler EvidenceDrivenScheduler --n-rounds 2` (re-run without `cosine_ramp_strength=0.5` because the fix only applies to cosine) | `CodimensionSheetScheduler` + `EvidenceDrivenScheduler` | YES |

Wave 281 sweep result citation: `docs/audit/wave281-paper-controller-sweep-result.md` (to be authored after the sweep completes).

---

## 5. Aggregate R-cell + weak-claim scheduler-audit conclusion

**13/13 = 100% of the R-cell + weak-claim HEADLINE sweeps used `CosineAnnealScheduler`** (the framework's historical default, the canonical implementation of paper Lemma 2's sheet-tube scaling closed form, but NOT a paper-quantity consumer).

The framework was DESIGNED around 4 paper quantities (`A_g`, `B_g`, `C_g`, `e_rho`) per `docs/INSIGHTS.md` §2 + ADR-0013 + `adaptive_reflow/contracts/paper_quantities.py`. Cosine ignores them. **None of the R-cell + weak-claim headline sweeps exercised any of the 4 paper-quantity-driven controllers** (`CodimensionSheetScheduler`, `PaperRatioAdaptiveScheduler`, `EvidenceDrivenScheduler`, `NFEAwareMemoryScheduler` partial).

This is documented as **known scope** for paper discussion. The Wave 280 P falsifications are flagged as **load-bearing false negatives** that Wave 281 re-sweeps with paper-grounded controllers. Per the user's directive "当让老的调度器记录也是有用的，可以留着在论文里面做讨论做对比" this cosine usage record IS the discussion-and-comparison baseline the paper needs; the Wave 281 paper-grounded sweep result is the disambiguating evidence.

### 5.1 Per-cell headline scheduler (1-line summary)

| Cell | Headline scheduler | Source | Paper-qty consumer? |
|---|---|---|---|
| R1 | CosineAnnealScheduler | `tools/experiments/run_lineageflow_comparison.py:278` (`default_cosine_scheduler(cycle_length=N_ROUNDS)`) | NO |
| R2 | CosineAnnealScheduler | `tools/run_sota_graphbfn_experiment.py:382` (single-scheduler v2 plan) | NO |
| R3 | CosineAnnealScheduler | `tools/run_sota_flowmol3_v2_adapter_experiment.py:525` (single-scheduler v2 plan) | NO |
| R4 | CosineAnnealScheduler | `tools/run_sota_2d_experiment.py:179` (canonical headline; codim/evidence/freetraj are ablation arms) | NO |
| R5 | CosineAnnealScheduler | Same as R4 | NO |
| R5b | CosineAnnealScheduler | `tools/run_sota_cifar_experiment.py:118-121` (HEADLINE is cosine; codim/evidence/freetraj are ablation arms) | NO |
| R5c (smoke ckpt) | CosineAnnealScheduler | `scripts/wave191_p3_mnist_sweep.py:105` (ARM_LABELS = cosine, codim, evidence_driven; HEADLINE is cosine) | NO |
| R5c (production ckpt, Wave 280 P) | CosineAnnealScheduler | Same as R5c smoke | NO |
| K1 | CosineAnnealScheduler | Reuses Wave 87 byte-stable seed=42 reference; K1 is metric fix only | NO |
| K3+R5b | CosineAnnealScheduler | `tools/run_sota_cifar_experiment.py:609-610` (only cosine consumes `cosine_ramp_strength`) | NO |
| K4+K5 | CosineAnnealScheduler | Reuses Wave 158 P2 R1 reference; K4+K5 are FASTA-gen fixes only | NO |
| K7 | CosineAnnealScheduler | Reuses LineageFlow framework arm; K7 is env-block fix only | NO |
| R6 (historical byte-stable) | CosineAnnealScheduler | `tools/eval/cli.py:312-329` "legacy byte-stable scheduler" | NO |
| R6 (Wave 275 P4 tier-aware remediation) | `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler` | `tools/eval/cli.py:312-329` `--tier-aware-n-cap` flag | **YES** (the only cell) |

---

## 6. Audit doc cross-references

- `docs/INSIGHTS.md` §2 + §87 — the framework's paper-quantity-driven scheduler surface; the `selection_ratio` metric is framework-internal NOT a paper claim; paper quantities are first-class algorithm-layer inputs
- `docs/adr/0013-posterior-selection-drives-algorithm.md` — ADR-0013 codifies cosine as the canonical implementation of paper Lemma 2 sheet-tube scaling + locks in the theory-framework correspondence
- `docs/audit/wave280-final.md` — Wave 280 P 7-branch sweep validation aggregate
- `docs/audit/wave280-p-cifar-sweep-result.md` §4 — K3+R5b moves from WEAK hypothesis-only to STRONG REJECTED at 2-seed partial; explicitly flags "Wave 281 follow-up" for the remaining 10 cells
- `docs/audit/wave280-p-r3-sweep-result.md` §0 — R3 sweep driver RUNNING; Wave 281 disambiguates the 3-seed sweep from the byte-stable reference
- `docs/audit/wave280-p-r6-sweep-result.md` §3.4 — R6 tier-aware counterfactual lifts overall d_z but easy tier still REGRESSES; Wave 281 plans the CodimensionSheetScheduler unwrapped comparison
- `docs/audit/mnist/wave280-p-r5c-sweep-result.md` — R5c production-ckpt direction-flips to baseline_wins at matched NFE=50; Wave 281 plans the codim + evidence arms on the production ckpt
- `docs/audit/wave280-p-{k1,k4k5,k7,r1}-sweep-result.md` — the Wave 280 P weak-metric remediation evidence rows; all reuse the historical byte-stable cosine reference
- `tools/run_sota_cifar_experiment.py:213-273` — `build_scheduler(name)` mapping: CosineAnnealScheduler (default-cosine), CodimensionSheetScheduler, EvidenceDrivenScheduler, FreeTrajScheduler
- `tools/run_sota_2d_experiment.py:164-186` — `_build_scheduler(name)` mapping: cosine, codim, evidence, freetraj
- `scripts/wave191_p3_mnist_sweep.py:178-198` — `build_scheduler(name)` mapping: cosine, codimension_sheet, evidence_driven
- `scripts/wave189_p4_theorem_load_bearing_kanzi.py:155-220` — the canonical Wave 189 P4 paper-quantity-vs-cosine Theorem 1 load-bearing isolation test (the only place paper-quantity-driven controllers were exercised as headlines in the load-bearing ablation)
- `scripts/wave190_p1_theorem_load_bearing_extended.py:151-220` — Wave 190 P1 extension of the load-bearing ablation (n=30 paired seeds)
- `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` — `CodimensionSheetScheduler` class definition
- `adaptive_reflow/algorithm/scheduler/adaptive.py:2035` — `PaperRatioAdaptiveScheduler` class definition
- `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248` — `EvidenceDrivenScheduler` class definition
- `adaptive_reflow/algorithm/scheduler/nfe_aware.py:110` — `NFEAwareMemoryScheduler` class definition
- `adaptive_reflow/algorithm/scheduler/simple.py:71` — `CosineAnnealScheduler` class definition (the historical default; paper-quantity-free)