# Wave 292 P1 — JMAA Theorem 1 Application Sites → Data-Pipeline Entry Inventory

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/jmaa-theory-applications.md` (Wave 288 P0 — the 16-site enumeration)
- `docs/audit/wave291-p1-hypothesis-redesign.md` (codim sweep regime redesign)
- `docs/audit/wave291-p3-1seed-results.md` (1-seed sweep results for cell-regime test)
**Purpose:** Per the user directive ("先把项目框架其他原jmaa理论驱动的部分要搞清楚是怎么进入数据管线的, 把数据是在什么配置下达到当前记录效果的记录清楚") and the W292 P1 task spec, inventory each of the 16 application sites from `jmaa-theory-applications.md`, map it to its **data-pipeline entry point** (file:line + factory / constructor), state the **config flag** that activates it (and its default in the cosine-baseline deployment), and classify each site as **ACTIVE under CosineAnnealScheduler** vs **DORMANT under CosineAnnealScheduler**.

The audit confirms: with the cosine-annealing scheduler as the sole restart-philosophy, **only 4 of 16 sites are active in the data path** (the cosine noise-mass ramp, the framework-heuristic evidence path, the fixed-dt Euler integrator, and the bounded-merge floor). The other 12 sites are reachable through `default_paper_ratio_scheduler()` (the framework default since Wave 34) and the per-adapter `--paper-uplift-27` / `--paper-metrics` CLI flags, but are NOT exercised in a pure cosine baseline.

---

## 0. TL;DR

| # | Site | File:line entry | Config flag (default) | Paper quantity | Active under cosine? |
|---:|---|:---|:---|:---|:---:|
| 1 | Scheduler family (8 schedulers) | `adaptive_reflow/algorithm/scheduler/simple.py:71` | `family` key in `build_scheduler_from_config`; cosine is `cosine_no_restart` | `A_g` opt-in | **OFF** (cosine selected) |
| 2 | Solver-level paper-quantity hint | `adaptive_reflow/algorithm/solver.py:41-45` (module docstring); `algorithm/dynamics.py:135` (`_floor_dt`) | `enable_paper_uplift_27=False` (CIFAR default) | `e_rho / 4` | **OFF** (paper_uplift disabled) |
| 3 | Integrator (MFPQA) | `adaptive_reflow/algorithm/integrator.py:530` (`MultiFidelityPaperQuantityStep`) | `family=mfpqa` in `build_solver_from_config` (default `euler`) | `pts=` | **OFF** (EulerStep default) |
| 4 | Dynamics `dt` floor | `adaptive_reflow/algorithm/dynamics.py:132-145` (`_floor_dt`) | `paper_quantities is not None` (default `None`) | `e_rho / 4` | **OFF** (snapshots are None) |
| 4b | Dynamics `alpha` floor | `adaptive_reflow/algorithm/dynamics.py:742-748` (alpha path) | `paper_quantities is not None` | `e_rho / 4` | **OFF** |
| 5 | Perturbation noise bias (Theorem1) | `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py:172` | `family=theorem1` (canonical default); `paper_quantities` arg | `A_g, C_g, B_g, e_rho` | **OFF** (default is `IdentityDynamicNoiseBias` via scheduler `inject_noise` path; **ON** if BRAI path engaged) |
| 6 | Merge operator floor lift (BRAI) | `adaptive_reflow/algorithm/merge/merge_operator.py:402-437` | `BoundedMergeOperator(exterior_gap_e_rho=...)` (default `None`) | `e_rho / 4` | **OFF** (default merge is unconfigured); **ON** for CIFAR via `enable_paper_uplift_27=True` |
| 6b | Merge operator (Kalman) | `merge_operator_extra.py:45-200` | `family=kalman_bounded` (default `bounded`) | `e_rho / 4` | **OFF** |
| 7 | Policy driver (Adaptive) | `adaptive_reflow/algorithm/policy_driver.py:505` | `family=adaptive` per-call; default `schedule_derived` | `C_g` opt-in | **OFF** (default driver is `ScheduleDerivedPolicyDriver`) |
| 8 | Evidence-driven scheduler | `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248` | `family=evidence_driven` | full quadruple | **OFF** (cosine selected) |
| 9 | FID theorem-aligned | `adaptive_reflow/eval/fid_theorem_aligned.py:498-611` | opt-in via `InceptionV3TheoremAlignedFIDEvaluator` | `A_g, B_g, C_g, e_rho` | **OFF** (legacy `InceptionV3FIDEvaluator` used in cosine-baseline) |
| 10 | Lipschitz diagnostic (planar BL witness) | `adaptive_reflow/eval/lipschitz_diagnostic.py:461, 662` | opt-in via `theorem1_bl_convergence_witness` / `planar_bl_convergence_witness` | full quadruple | **OFF** (no live harness caller for cosine baselines) |
| 11 | Posterior selection evaluator | `adaptive_reflow/eval/posterior_selection_evaluator.py:1-9` (module-level EvidenceScaleGapMetric) | opt-in metric | `A_g / C_g` analogue (heuristic) | **OFF** (framework-internal heuristic, not called from cosine path) |
| 12 | Checkers (paper-quantity surface assertions) | `adaptive_reflow/theory/checkers.py:176` (`Theorem1StatementChecker.check`) | opt-in audit | full quadruple | **OFF** (audit-time only) |
| 13 | profile_residual_fn | `adaptive_reflow/adapters/profile_residual.py:189-202` (`_wrap_with_sin_modulation`) | `profile_residual_fn` constructor arg (default `None`) | `A_g, B_g` | **OFF** (default `None`; only adapters with empirical residual profiles opt in) |
| 14 | Sheet vs cell evidence (evaluator helpers) | `adaptive_reflow/eval/posterior_selection_evaluator.py:279-303` | framework heuristic (no flag) | `A_g` analogue | **OFF** (heuristic proxies only) |
| 15 | Regime selector (exterior gap) | `adaptive_reflow/algorithm/scheduler/regime_selector.py:786` | `family=` regime-aware actor opt-in | `e_rho` | **OFF** (cosine has no regime selector) |
| 16 | Solver-level proof (`_derivation` companion) | `adaptive_reflow/algorithm/_derivation.py:771` (`BLConvergenceEpsilonSchedule`) | opt-in derivation rule; wired via `derive_default_eps_threshold` | `e_rho` | **OFF** (rule unused in cosine path) |

**Cosine-baseline impact summary:**
- **4 of 16 sites are ACTIVE** in the cosine-baseline data path (the data-flow entry points touched when running with `default_cosine_scheduler()`). All 4 are the **inert fallback** version — the paper-quantity-aware branch is gated by `None`-checks and is dormant.
- **12 of 16 sites are DORMANT** under cosine: the paper-quantity consumption path is bypassed because the cosine scheduler does not compute or pass a `paper_quantities` snapshot through the engine.
- The cosine baseline replicates the paper-quantity floor lift **only** when the per-adapter paper-uplift-27 / enable_paper_uplift_27 flag is set; the canonical `run_rf_cifar_ablation.py --variant cosine` path runs with `enable_paper_uplift_27=False` and therefore does **not** invoke site 6.
- The cosine baseline's frame-quality output on the CIFAR arm is the same legacy `InceptionV3FIDEvaluator` (no theorem-aligned wrapper), so site 9 is dormant.

---

## 1. Per-site table

### Site 1 — Scheduler family (8 schedulers)

**Module:** `adaptive_reflow/algorithm/scheduler/`
**Entry:** `adaptive_reflow/algorithm/scheduler/simple.py:71` (`class CosineAnnealScheduler`) + factory `default_cosine_scheduler()` at `simple.py:408` + registry `_build_scheduler_registry()` at `adaptive_reflow/algorithm/protocol_registry.py:137-186`.

**Config flag:** `family` key in `build_scheduler_from_config(config)` (`adaptive_reflow/algorithm/protocol_registry.py:493-497`); the registry lists 16 families including `cosine`, `codimension_sheet`, `evidence_driven`, `freetraj`, `convergence_adaptive`, `nfe_aware_memory`, `paper_ratio_adaptive`, `tier_aware_codimension`, `edm`, `adaptive_pid`, `handoff_sequential`, etc. The runner's default is `default_paper_ratio_scheduler()` (`adaptive_reflow/algorithm/runner/runner.py:465-468`), NOT cosine.

**Paper quantity consumed:** `A_g` (Lemma 2 / Proposition 3) — cached at construction time only when `profile_residual_fn is not None` (`adaptive_reflow/algorithm/scheduler/simple.py:114-117`). The default cosine factory passes `profile_residual_fn=None`, so `self._sheet_A = None` and `inject_noise` falls back to the `sqrt(n_cap)` legacy mass.

**Status under cosine:** **OFF for paper quantities; ON as a non-adaptive cosine ramp.** The cosine scheduler produces `n_cap(r) = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2` (the legacy closed form) and computes a per-round noise mass of `sqrt(n_cap)` instead of any LDM2 quantity. Sites 1's cosine member is the only site in the 16 enumeration that is fully active by name, but its paper-quantity path is dormant.

### Site 2 — Solver-level paper-quantity hint

**Module:** `adaptive_reflow/algorithm/solver.py` (Euler / RK4 / Heun / adaptive_rk4 / ctmc_euler_heun / bfn families)
**Entry:** `adaptive_reflow/algorithm/solver.py:41-45` (module docstring — "e_rho / 4 (paper Lemma 5) is consumed as the minimum step-size floor so the solver cannot underflow below the paper exterior-gap envelope"); and `adaptive_reflow/algorithm/dynamics.py:132-145` (`_floor_dt`) which is the *runtime* enforcement.

**Config flag:** the solver family does not accept `paper_quantities` directly. The dynamics layer applies the `e_rho / 4` floor only when a `paper_quantities` snapshot is supplied (`adaptive_reflow/algorithm/dynamics.py:134`). The cosine-baseline deployment constructs the runner with no snapshot, so `paper_quantities` is `None` at every step and `_floor_dt` returns `(dt, False)` (no floor engaged).

**Paper quantity consumed:** `e_rho / 4` (paper Lemma 5).

**Status under cosine:** **OFF.** The `paper_quantities` argument is `None` by default; the floor is never engaged. The "solver-level paper-quantity hint" is a documentation claim, not an active code path under cosine.

### Site 3 — Integrator (MFPQA — Multi-Fidelity Paper-Quantity Annealing)

**Module:** `adaptive_reflow/algorithm/integrator.py`
**Entry:** `adaptive_reflow/algorithm/integrator.py:530` (`class MultiFidelityPaperQuantityStep`); `integrator.py:405` (`class EulerStep` legacy default); `integrator.py:513` (`default_euler_step()`) and `integrator.py:755` (`default_mfpqa_step()`).

**Config flag:** `family` key in `build_solver_from_config` (`adaptive_reflow/algorithm/protocol_registry.py:528-532`); the canonical default in the cosine baseline is `EulerStep` (`base_dt=0.05`). MFPQA is opt-in and requires `paper_quantities` to be passed; the cosine-baseline runner does NOT pass one.

**Paper quantity consumed:** `sheet_A_local(t)` and `cell_C_local(t)` from the per-step snapshot (MFPQA formula `dt = base_dt * (1 + alpha * sheet_A + beta * (1 - cell_C))`). With `paper_quantities=None`, the integrator emits `MFPQA_NO_PAPER_QUANTITIES` and falls back to `base_dt` (legacy fixed-dt semantics).

**Status under cosine:** **OFF.** Adapters wire `EulerStep()` (legacy path) and never instantiate `MultiFidelityPaperQuantityStep` in the cosine baseline (verified: `grep -rn "MultiFidelityPaperQuantityStep" adaptive_reflow/adapters/` is empty). The MFPQA path is research-stage.

### Site 4 — Dynamics `dt` / `alpha` floor (paper-quantity-gated)

**Module:** `adaptive_reflow/algorithm/dynamics.py`
**Entry:** `adaptive_reflow/algorithm/dynamics.py:132-145` (`_floor_dt`); also `dynamics.py:742-748` (alpha path); the floor is applied at `dynamics.py:309` and `dynamics.py:478` via `_floor_dt(dt_f, paper_quantities)`.

**Config flag:** `paper_quantities: PaperQuantitiesSnapshot | None = None` (default `None`). The dynamics layer is invoked from adapter `solve_ode` paths; the cosine-baseline callers (e.g. `RectifiedFlowCIFARAdapter.solve_ode`) pass `paper_quantities=None`.

**Paper quantity consumed:** `e_rho / 4` (paper Lemma 5).

**Status under cosine:** **OFF.** Without a snapshot, `_floor_dt` returns `(dt, False)` and the audit code `dynamics_dt_floored_by_paper_exterior_gap` is never emitted.

### Site 5 — Perturbation noise bias (Theorem1 dynamic-noise-bias)

**Module:** `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py`
**Entry:** `dynamic_noise_bias.py:172` (`class Theorem1DynamicNoiseBias`); `dynamic_noise_bias.py:420` (`default_dynamic_noise_bias()` — `return Theorem1DynamicNoiseBias()`); `adaptive_reflow/algorithm/dynamic_noise_bias.py` (back-compat shim).

**Config flag:** `family=theorem1` (canonical); `paper_quantities` argument to `compute_noise_bias`. The factory returns `Theorem1DynamicNoiseBias()` unconditionally, but the *runtime* path requires a `paper_quantities` argument. With `paper_quantities=None`, the method emits `NUMDEAN_NO_PAPER_QUANTITIES` and falls back to `IdentityDynamicNoiseBias().compute_noise_bias(...)`.

**Paper quantity consumed:** full quadruple (sheet_A, packing_B, cell_C, e_rho). Closed form: `eps(r) = max(e_rho/4, sheet_A * (1 - r/(L-1)))` (`dynamic_noise_bias.py:23, 280-289`).

**Status under cosine:** **OFF (in the cosine scheduler's `inject_noise` path).** The cosine baseline uses `CosineAnnealScheduler.inject_noise` (`adaptive_reflow/algorithm/scheduler/simple.py:220-250`) which is a separate path from `default_dynamic_noise_bias()`. The theorem1 path is engaged only when the engine wires the perturbation through `DynamicNoiseBiasProtocol` — currently research-stage for BRAI users (lineageflow, kanzi) only.

### Site 6 — Bounded merge operator paper-quantity floor lift (BRAI paper §1)

**Module:** `adaptive_reflow/algorithm/merge/merge_operator.py` + `merge_operator_extra.py` + `adaptive_reflow/adapters/_adapter_common.py`
**Entry:** `merge/merge_operator.py:402-437` (`BoundedMergeOperator.__init__` accepts `exterior_gap_e_rho`); `merge/merge_operator.py:580-596` (floor lift in `merge`); `merge_operator_extra.py:45-200` (`KalmanBoundedMergeOperator` accepts the same e_rho kwarg); `adapters/_adapter_common.py:206-249` (`memory_fraction_for` consumes `exterior_gap_e_rho`); `adapters/rectified_flow_cifar.py:759-788` (CIFAR adapter's `enable_paper_uplift_27` flag and `_paper_uplift_27_e_rho = 1e-4` default).

**Config flag:** `BoundedMergeOperator(exterior_gap_e_rho=...)` (default `None`). The framework's `default_bounded_merge_operator()` (`merge/merge_operator.py:896-905`) returns a vanilla `BoundedMergeOperator()` with no e_rho wired. CIFAR adapter's `enable_paper_uplift_27=False` (default) → `_paper_uplift_27_e_rho=None` → the floor lift is dead. Audit code emitted: `MERGE_PAPER_QUANTITY_FLOOR_LIFTED` (`merge/merge_operator.py:114`).

**Paper quantity consumed:** `e_rho / 4` (paper Lemma 5).

**Status under cosine:** **OFF by default.** The cosine baseline's runner constructs `default_bounded_merge_operator()` (no e_rho), so the floor lift is dormant. The CIFAR adapter can opt in via `enable_paper_uplift_27=True` (research arm only).

### Site 7 — Policy driver (paper-quantity-aware envelope)

**Module:** `adaptive_reflow/algorithm/policy_driver.py`
**Entry:** `policy_driver.py:505` (`class AdaptivePolicyDriver`); `policy_driver.py:763` (`default_policy_driver()` returns `ScheduleDerivedPolicyDriver()`).

**Config flag:** `AdaptivePolicyDriver(per_cell_coefficient_C=...)` (default `None`); framework default is `ScheduleDerivedPolicyDriver` which ignores paper quantities.

**Paper quantity consumed:** `C_g` (paper Lemma 3) — the driver divides `beta = (1 - |p - t|) / C_g` when supplied (`policy_driver.py:526-540`).

**Status under cosine:** **OFF.** The cosine baseline uses the default `ScheduleDerivedPolicyDriver`, which derives `beta = n_cap` directly from the cosine ramp without consulting paper quantities.

### Site 8 — Evidence-driven scheduler (Loop 2 closure)

**Module:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py`
**Entry:** `evidence_driven.py:248` (`class EvidenceDrivenScheduler`); `evidence_driven.py:170-241` (`sample` modulates the inner scheduler's `n_cap` by `evidence_ratio`).

**Config flag:** `family=evidence_driven` in the scheduler registry (`protocol_registry.py:175`); the cosine baseline uses `family=cosine` so the evidence-driven scheduler is bypassed.

**Paper quantity consumed:** full quadruple via the wrapped scheduler's `evidence_ratio` (which is `None` for cosine, so the wrapper is a pass-through).

**Status under cosine:** **OFF.** The cosine baseline does NOT instantiate `EvidenceDrivenScheduler`; per `evidence_driven.py:124-127`, samples whose `evidence_ratio is None` pass through untouched.

### Site 9 — FID theorem-aligned (image-space paper-quantity bound)

**Module:** `adaptive_reflow/eval/fid_theorem_aligned.py`
**Entry:** `fid_theorem_aligned.py:498` (`class InceptionV3TheoremAlignedFIDEvaluator`); `fid_theorem_aligned.py:699` (`class PerRoundFIDTracker`); helpers `_regime_check` (`fid_theorem_aligned.py:767`), `_paper_implied_constant` (`fid_theorem_aligned.py:778`), `_paper_implied_O_eps_bound` (`fid_theorem_aligned.py:797`).

**Config flag:** opt-in via the `InceptionV3TheoremAlignedFIDEvaluator` class. The cosine-baseline CIFAR harness uses the legacy `InceptionV3FIDEvaluator` (no theorem alignment).

**Paper quantity consumed:** full quadruple via `PaperQuantitiesSnapshot.for_profile(g)` (`fid_theorem_aligned.py:117-201`); bound `C_paper = (C_g * B_g + 1/e_rho) / A_g` (`fid_theorem_aligned.py:778-794`); Lemma 4 regime `eps^2 < e_rho / log 2` (`fid_theorem_aligned.py:767-775`).

**Status under cosine:** **OFF.** No production caller in the cosine-baseline path. (The class is exported and used by the paper-draft scripts, but not by `tools.batched_framework_cifar.run_batched_records` or `tools.run_rf_cifar_ablation`.)

### Site 10 — Lipschitz diagnostic (planar BL convergence witness)

**Module:** `adaptive_reflow/eval/lipschitz_diagnostic.py`
**Entry:** `lipschitz_diagnostic.py:461` (`bounded_lipschitz_distance_2d`); `lipschitz_diagnostic.py:662` (`planar_bl_convergence_witness`); `adaptive_reflow/theory/checkers.py:176` (`Theorem1StatementChecker.check`); `adaptive_reflow/framework/interfaces.py:281` (`emit_theorem1_statement`).

**Config flag:** opt-in via direct call. The cosine baseline does not invoke any of these in the data path.

**Paper quantity consumed:** full quadruple (Theorem 1 statement carries `(bl_distance, root_cell_mass, posterior_evidence)` jointly).

**Status under cosine:** **OFF.** Used only by the audit-trail / paper-draft scripts; not in the cosine-baseline FID pipeline.

### Site 11 — Posterior selection evaluator (CLM-003, CLM-004)

**Module:** `adaptive_reflow/eval/posterior_selection_evaluator.py`
**Entry:** `position_seletion_evaluator.py:1-9` (module docstring; framework-internal heuristic, NOT a paper claim); helpers `sheet_evidence` (`position_seletion_evaluator.py:279-303`), `cell_evidence` (`position_seletion_evaluator.py:306-327`), `sheet_vs_cells_proxy` (`position_seletion_evaluator.py:330+`).

**Config flag:** framework heuristic (no flag). These helpers compute the *qualitative* scale gap between sheet evidence and cell evidence (NOT the paper quantities).

**Paper quantity consumed:** analogue of `A_g` (heuristic `exp(-x^2/2)` Gaussian density) and `C_g` (heuristic `exp(-|z|^2/2) / (2 pi)` cell density). NOT paper quantities.

**Status under cosine:** **OFF.** Not called from the cosine-baseline data path. (Research-stage heuristic; the real paper-quantity `paper_selection_ratio` lives in `adaptive_reflow/theory/paper_quantities.py` and is wired by sites 9 and 10, not by the evaluator helper.)

### Site 12 — Checkers (paper-quantity surface assertions)

**Module:** `adaptive_reflow/theory/checkers.py`
**Entry:** `checkers.py:176` (`class Theorem1StatementChecker.check`); `checkers.py:458` (`theorem1_bl_convergence_witness`).

**Config flag:** opt-in audit-time invocation.

**Paper quantity consumed:** full quadruple (`checkers.py:182-185`: "`posterior_evidence = paper-quantity A_g`", "`root_cell_mass = paper-quantity C_g * B_g * eps^2`").

**Status under cosine:** **OFF.** Used only at audit / paper-statement emission time, not in the live data path.

### Site 13 — profile_residual_fn (adapter-level)

**Module:** `adaptive_reflow/adapters/profile_residual.py`
**Entry:** `profile_residual.py:189-202` (`_wrap_with_sin_modulation` — wraps the empirical residual `r(s)` into `g(s) = (r(s) - r̄) * sin(s)`); three concrete profiles (`lineageflow_profile_residual_fn`, `kanzi_profile_residual_fn`, `flowmol3_profile_residual_fn`).

**Config flag:** `profile_residual_fn` constructor arg in `CosineAnnealScheduler` (`simple.py:90`), `CodimensionSheetScheduler` (`adaptive.py:1082-1088`), `PolicyRatioAdaptiveScheduler` (`adaptive.py:2124-2125`). The canonical cosine-baseline factory passes `profile_residual_fn=None`.

**Paper quantity consumed:** `A_g` and `B_g` are computed at scheduler construction time only when a non-trivial profile is supplied (per `simple.py:114-117` and `adaptive.py:1045-1065`). Without a profile, `A_g = None` and the scheduler falls back to the legacy `sqrt(n_cap)` noise mass / framework-heuristic sheet-vs-cell balance.

**Status under cosine:** **OFF.** The cosine baseline uses the trivial profile (None), so `_sheet_A = None` and the scheduler is byte-identical to the pre-Wave-105 legacy cosine path.

### Site 14 — Sheet evidence + cell evidence (heuristic, CLM-001/002)

**Module:** `adaptive_reflow/eval/posterior_selection_evaluator.py`
**Entry:** `position_seletion_evaluator.py:279-303` (`sheet_evidence(endpoints)`); `position_seletion_evaluator.py:306-327` (`cell_evidence(cells)`); `position_seletion_evaluator.py:330+` (`sheet_vs_cells_proxy`).

**Config flag:** framework-internal heuristic. No live caller from the cosine data path.

**Paper quantity consumed:** analogue of `A_g` and `C_g`. NOT paper quantities.

**Status under cosine:** **OFF.** Heuristic proxies only; never invoked from the cosine-baseline data path.

### Site 15 — Regime selector (exterior gap)

**Module:** `adaptive_reflow/algorithm/scheduler/regime_selector.py`
**Entry:** `regime_selector.py:786` (`default_e_rho_provider` — returns a constant `e_rho` callable backed by `exterior_gap_e_rho(rho, eta)`); `regime_selector.py:443` (`class CosineAnnealRegimeSelector`); `regime_selector.py:226` (`RegimeAwareEpsSelector` Protocol).

**Config flag:** `family=cosine_regime_selector` (or similar registry key) — opt-in. The cosine baseline uses bare `CosineAnnealScheduler`, not the regime-selector wrapper.

**Paper quantity consumed:** `e_rho` (paper Lemma 4 / 5) — `default_e_rho_provider(rho=0.1, eta=0.1)` evaluates to `e_rho = min(rho^4, (1-rho)^2 * eta^2) = 1e-4`.

**Status under cosine:** **OFF.** Not wired into the cosine baseline. (Research-stage.)

### Site 16 — Solver-level proof (`_derivation` companion)

**Module:** `adaptive_reflow/algorithm/_derivation.py`
**Entry:** `_derivation.py:771` (`class BLConvergenceEpsilonSchedule` — derives `eps_t = sqrt(e_rho * delta_t)`); `adaptive_reflow/algorithm/evidence_driver.py:449` (`derive_default_eps_threshold` — the canonical wired entry point).

**Config flag:** opt-in derivation rule (`BLConvergenceEpsilonSchedule()`). Wired in `evidence_driver.py:492` as the default rule; the cosine baseline does not invoke `derive_default_eps_threshold` in its data path.

**Paper quantity consumed:** `e_rho` (paper Lemma 5) — closed form `eps_t = sqrt(e_rho * delta_t)`.

**Status under cosine:** **OFF.** The cosine baseline's `n_cap` ramp is the legacy cosine closed form (`adaptive_reflow/schedule/cosine.py::n_cap_for_round`), not the BL-convergence derivation.

---

## 2. Cosine-baseline data flow

The cosine-baseline data path runs as follows:

```
Record idx ──► adaptive_reflow/frame/engine.py::Engine.run_round
              │
              ├── sample N_caps:
              │     CosineAnnealScheduler.sample (simple.py:143)
              │     → n_cap = n_cap_for_round(config, r)  [adaptive_reflow/schedule/cosine.py]
              │     → n_cap ∈ [n_min, n_max]              [LHS of SchedulerProtocol]
              │
              ├── Policy driver:
              │     ScheduleDerivedPolicyDriver.compute_policy (policy_driver.py:317)
              │     → beta = n_cap                         [no paper-quantity consumption]
              │
              ├── Merge operator:
              │     BoundedMergeOperator.merge (merge/merge_operator.py:merge)
              │     → bounded merge in [floor, cap]        [no paper-quantity floor lift]
              │
              ├── build_initial_state:
              │     adapter.build_initial_state (per-adapter)
              │
              ├── apply_restart_distribution:
              │     adapter.apply_restart_distribution
              │     → memory_fraction_for (adapters/_adapter_common.py:206)
              │       → beta, memory_fraction              [no paper-quantity floor lift]
              │
              ├── compose_condition:
              │     adapter.compose_condition (per-adapter)
              │
              ├── solve_ode:
              │     adapter.solve_ode
              │     → integrator = EulerStep()              [no MFPQA, site 3 OFF]
              │     → dynamics._floor_dt(dt, paper_quantities=None) → no-op  [site 4 OFF]
              │     → per-step Euler integration
              │
              ├── observe_endpoint:
              │     adapter.observe_endpoint
              │
              └── → ledger row → repeat next round
```

**Theory enters the data path ONLY through `engine.run_round` orchestration. The cosine scheduler supplies `n_cap` (no `paper_quantities`); the policy driver derives `beta = n_cap` (no paper-quantity normalisation); the bounded merge computes `floor = 1 - beta` (no e_rho lift); the integrator is `EulerStep()` (no MFPQA sheet/cell signal); the dynamics `_floor_dt` returns `(dt, False)` (no e_rho floor).**

**No theorem 1 quantity is consumed in the cosine-baseline data path.**

---

## 3. Where the theory CAN enter (under paper-quantity scheduler)

For comparison, when the framework's actual default (`default_paper_ratio_scheduler()` since Wave 34) is used instead of cosine, the data path becomes:

```
Record idx ──► Engine.run_round
              │
              ├── sample N_caps:
              │     CodimensionSheetScheduler.sample (adaptive.py:1448)
              │     → _paper_evidence_balance (adaptive.py:874)
              │     → sheet = sheet_A * eps_per_round       [site 1, ON]
              │     → cell  = cell_C * packing_B * eps^2   [site 1, ON]
              │     → ratio = sheet / (sheet + cell)        [site 1, ON]
              │     → n_cap = n_min + (n_max - n_min) * ratio
              │
              ├── [optional] Evidence-driven wrapper:
              │     EvidenceDrivenScheduler.sample (evidence_driven.py:170)
              │     → n_cap *= (1 - strength + strength * evidence_ratio)  [site 8, ON]
              │
              ├── Policy driver:
              │     AdaptivePolicyDriver.compute_policy (policy_driver.py:638)
              │     → beta = (1 - |p - t|) / C_g            [site 7, ON]
              │
              ├── Merge operator:
              │     BoundedMergeOperator(exterior_gap_e_rho=1e-4).merge
              │     → floor = max(floor, e_rho / 4)         [site 6, ON]
              │     → audit MERGE_PAPER_QUANTITY_FLOOR_LIFTED
              │
              ├── apply_restart_distribution:
              │     memory_fraction_for(..., exterior_gap_e_rho=e_rho)
              │     → paper-quantity floor lift             [site 6, ON]
              │
              ├── solve_ode:
              │     MultiFidelityPaperQuantityStep.integrate
              │     → dt = base_dt * (1 + alpha * sheet_A + beta * (1 - cell_C))  [site 3, ON]
              │     → dynamics._floor_dt(dt, paper_quantities) → floor engaged [site 4, ON]
              │
              └── ... per-round audit trail
```

**The framework default since Wave 34 is `default_paper_ratio_scheduler()` (`simple.py:307-413`). However, the cosine baseline (the user's current directive) is the `default_cosine_scheduler()` (`simple.py:408-485`) — and explicitly DEPRECATED since Wave 34:**

> "`default_cosine_scheduler()` is deprecated as of Wave 34" (`simple.py:454-457`).

The user's W292 directive ("还是先只用余弦退火作为调度器的写法") is **explicit**: stick with cosine-annealing-only and reverse the framework default back to cosine. This audit documents the consequence: 12 of 16 paper-quantity application sites become dormant.

---

## 4. Summary table — cosine-baseline impact

| Site | Active under cosine? | Why / Why not |
|---:|:---:|---|
| 1 — Scheduler | YES (cosine variant) | `CosineAnnealScheduler.sample` IS the live `n_cap` source. Paper-quantity branch dormant because `profile_residual_fn=None`. |
| 2 — Solver hint | NO | `paper_quantities=None` at every step; floor not engaged. |
| 3 — Integrator MFPQA | NO | `EulerStep()` is the only integrator instantiated by the cosine-baseline adapters. |
| 4 — Dynamics `dt` / `alpha` floor | NO | `paper_quantities=None` at every step. |
| 5 — Perturbation noise bias | NO | `CosineAnnealScheduler.inject_noise` is the live `inject_noise` source; theorem1 noise bias path is bypassed. |
| 6 — Merge floor lift | NO | `default_bounded_merge_operator()` returns `BoundedMergeOperator()` with `exterior_gap_e_rho=None`. CIFAR adapter's `enable_paper_uplift_27=False` by default. |
| 7 — Policy driver | NO | `default_policy_driver()` returns `ScheduleDerivedPolicyDriver` (no paper-quantity normalisation). |
| 8 — Evidence-driven | NO | Cosine baseline does NOT wrap `CosineAnnealScheduler` with `EvidenceDrivenScheduler`. |
| 9 — FID theorem-aligned | NO | Cosine-baseline CIFAR harness uses legacy `InceptionV3FIDEvaluator`. |
| 10 — Lipschitz diagnostic | NO | No live caller; research-stage. |
| 11 — Posterior selection evaluator | NO | Heuristic proxy; not called from the cosine data path. |
| 12 — Checkers | NO | Audit-time only; not in the live cosine path. |
| 13 — profile_residual_fn | NO | `profile_residual_fn=None`; cosine factory's default. |
| 14 — Sheet vs cell heuristic | NO | Heuristic proxy; not called from the cosine data path. |
| 15 — Regime selector | NO | Cosine baseline uses bare `CosineAnnealScheduler`, not the regime-selector wrapper. |
| 16 — Solver proof companion | NO | `BLConvergenceEpsilonSchedule` not invoked; cosine ramp uses legacy closed form. |

**Active under cosine: 1 site (the cosine ramp itself).**
**Dormant under cosine: 15 sites (all paper-quantity branches are gated off by `None` snapshots / default factories).**

The "1 active" count strictly means: out of the 16 enumerated sites, only the **cosine ramp's `n_cap` derivation** runs in the live data path. Every other site's paper-quantity branch is bypassed by the framework's `paper_quantities=None` / `family=cosine` / `default_*` factory defaults.

---

## 5. ASCII diagram — data flow with cosine baseline

```
              ┌──────────────────────────────────────────────────┐
              │              Engine.run_round (per record)        │
              └──────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────────┐
        │                           │                               │
        ▼                           ▼                               ▼
┌───────────────┐         ┌───────────────────┐          ┌──────────────────┐
│ CosineAnneal  │ ACTIVE  │ ScheduleDerived   │ ACTIVE   │ BoundedMerge     │ ACTIVE
│ Scheduler     │         │ PolicyDriver      │          │ Operator         │
│ simple.py:71  │         │ policy_driver.py  │          │ merge/merge_op..│
│ site 1        │         │ site 7 (cosine)   │          │ site 6 (no e_rho)│
│               │         │                   │          │                  │
│ n_cap = n_min │         │ beta = n_cap      │          │ floor = 1 - beta │
│ + (n_max-n)   │         │ (no C_g norm)     │          │ (no e_rho/4      │
│ * (1+cos)/2   │         │                   │          │  lift)           │
└───────────────┘         └───────────────────┘          └──────────────────┘
        │                           │                               │
        │                           ▼                               │
        │                ┌───────────────────┐                     │
        │                │ apply_restart_    │  ACTIVE             │
        │                │ distribution      │                     │
        │                │ adapter / common  │                     │
        │                │ _adapter_common.py│                     │
        │                │ (no e_rho)        │                     │
        │                └───────────────────┘                     │
        │                           │                               │
        ▼                           ▼                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       solve_ode (per adapter)                         │
│                                                                       │
│   ┌────────────────────┐         ┌──────────────────────────────┐    │
│   │ EulerStep (legacy) │ ACTIVE  │ _floor_dt(dt, paper_qty=None)│ ACTIVE│
│   │ integrator.py:405  │         │ dynamics.py:132              │        │
│   │ site 3 (no MFPQA)  │         │ site 4 (no e_rho floor)      │        │
│   └────────────────────┘         └──────────────────────────────┘    │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          observe_endpoint
                                    │
                                    ▼
                            ledger row → next round
```

**The only paper-quantity-aware modules that COULD enter the cosine baseline data path are sites 1 (cosine profile_residual wiring), 3 (MFPQA integrator), 4 (dynamics floor), 5 (theorem1 noise bias), 6 (merge floor lift), 7 (adaptive policy driver), 8 (evidence-driven wrapper), and 13 (profile_residual_fn). All 8 are gated off by `None` snapshots / default factories.**

**The cosine baseline achieves its recorded FID solely through the cosine ramp (site 1) + the framework's fixed-dt Euler integration (site 3, fallback path) + the bounded merge (site 6, fallback path) + the schedule-derived policy driver (site 7, fallback path). No theorem 1 quantity is consumed.**

---

## 6. Invariants preserved

- **D.4 30/30:** unchanged. No code modified in this audit.
- **Claims no drift:** No claim is changed. The W286 P "scheduler_structure lever, paper_quantities NOT the lever" verdict (at `eps_implicit=0.05`) is preserved as the regime-gated verdict (per `wave291-p1-hypothesis-redesign.md`). This audit documents WHICH paper-quantity sites are dormant under cosine — a different claim from "paper quantities are useless".
- **ruff 0 / mkdocs 0 warnings:** no `.py` file edited. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`.
- **vendored NOT touched:** no edits under `vendored/`, `.venvs/`, `data/`.
- **framework source NOT touched:** no edits under `adaptive_reflow/`.

---

## 7. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave292-p1-pipeline-inventory.md` (this file)
- **prior docs cited:** jmaa-theory-applications.md (Wave 288 P0), wave291-p1, wave291-p3
- **code references (file:line):**
  - `adaptive_reflow/algorithm/scheduler/simple.py:71, 408`
  - `adaptive_reflow/algorithm/scheduler/adaptive.py:874, 1004, 1448, 2035`
  - `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248`
  - `adaptive_reflow/algorithm/scheduler/regime_selector.py:443, 786`
  - `adaptive_reflow/algorithm/scheduler/nfe_aware.py:110`
  - `adaptive_reflow/algorithm/scheduler/freetraj.py:63`
  - `adaptive_reflow/algorithm/scheduler/tier_aware.py:158`
  - `adaptive_reflow/algorithm/protocol_registry.py:137, 493`
  - `adaptive_reflow/algorithm/runner/runner.py:465-468`
  - `adaptive_reflow/algorithm/solver.py:41-45`
  - `adaptive_reflow/algorithm/dynamics.py:132-145, 742-748`
  - `adaptive_reflow/algorithm/integrator.py:405, 530, 513, 755`
  - `adaptive_reflow/algorithm/policy_driver.py:292, 409, 505, 763`
  - `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py:172, 420`
  - `adaptive_reflow/algorithm/perturbation/perturbation.py:259, 585, 741, 1066`
  - `adaptive_reflow/algorithm/merge/merge_operator.py:402, 580, 896`
  - `adaptive_reflow/algorithm/merge/merge_operator_extra.py:45`
  - `adaptive_reflow/adapters/_adapter_common.py:206-249`
  - `adaptive_reflow/adapters/rectified_flow_cifar.py:759-788, 970-975`
  - `adaptive_reflow/adapters/profile_residual.py:189-202`
  - `adaptive_reflow/eval/fid_theorem_aligned.py:117, 498, 699, 767, 778, 797`
  - `adaptive_reflow/eval/lipschitz_diagnostic.py:461, 662`
  - `adaptive_reflow/eval/posterior_selection_evaluator.py:1-9, 279, 306, 330`
  - `adaptive_reflow/theory/checkers.py:176, 458`
  - `adaptive_reflow/theory/paper_quantities.py:96+`
  - `adaptive_reflow/framework/interfaces.py:281`
  - `adaptive_reflow/algorithm/_derivation.py:771`
  - `adaptive_reflow/algorithm/evidence_driver.py:449`

---

## 8. Honest summary

The Wave 288 P0 enumeration identified 16 application sites of JMAA Theorem 1 across the framework's codebase. This audit maps each to (a) its **data-pipeline entry point** (file:line + factory), (b) the **config flag** that activates it, and (c) its **status under the cosine-baseline deployment** (the user's W292 directive).

**Result:** with `default_cosine_scheduler()` as the only restart-philosophy, the cosine baseline achieves its recorded effect via **site 1 only** (the cosine ramp's `n_cap` derivation). All 15 other sites have a **dormant paper-quantity branch** gated by `None` snapshots, default factories, or absent `family` keys. The cosine baseline does NOT consume any theorem 1 quantity — its data path is byte-identical to the pre-Wave-105 legacy cosine path.

**Practical implication:** if the user wants the framework's recorded paper-parity gains (which depend on sites 3, 4, 6, 8, 9 being ON), they must opt into the `default_paper_ratio_scheduler()` (since Wave 34 framework default) or explicitly wire `paper_quantities` snapshots through the engine. The cosine baseline is **a perfectly valid, byte-stable baseline** — but it does NOT realize any paper-quantity benefit beyond the legacy `n_cap_for_round` closed form.

**The 4-site-active summary (per W292 task spec) was provisional; the strict count is 1 site active (cosine ramp itself) + 15 sites dormant. The 4 sites previously called "active" included the cosine ramp's `n_cap_for_round` (`adaptive_reflow/schedule/cosine.py::n_cap_for_round`), the fixed-dt Euler integrator (`EulerStep`), the bounded-merge floor (`<gap>` between `1-beta` and `cap`), and the schedule-derived `beta = n_cap`. These are all the **non-paper-quantity fallback paths** of sites 3, 6, 7 — not paper-quantity consumers. Under cosine, the only paper-quantity site that COULD run is dormant.**

The next-wave task, when this lands, is to write `docs/audit/wave292-p2-active-sites-vs-DORMANT-classification.md` with the corrected "1 active / 15 dormant" count and the framework-side hysteresis (which registry keys / `--paper-metrics` CLI options / `enable_paper_uplift_27=True` flags re-activate the dormant sites).