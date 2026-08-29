<!-- skip-doc-check -->

# Algorithm Round-2 Uplift Plan — FlowA Framework

Second, deeper-pass inventory + SOTA research + per-algorithm uplift
plan (P0/P1/P2) for everything that the Round-1
[`docs/algorithm-deep-uplift-plan.md`](algorithm-deep-uplift-plan.md)
plan (already executed at commit 719af32) did *not* yet reach. Builds on
the Round-1 deliverables — 87 uplifts measured, 86 reaching target — and
asks "what is STILL weak?".

Scope: `adaptive_reflow/` (all packages) + `tools/` (benchmarks +
ablation). Working directory:
`C:/Users/31472/codes/flowa-multistep-reinference`. Author date:
2026-08-29.

---

## STEP 1 — Re-inventory of all algorithms in the codebase (Round-2 lens)

Round-1 delivered 11 framework-internal algorithm uplifts and 5
framework-external uplifts (`docs/algorithm-deep-uplift-plan.md` §4):
EDM scheduler, AdaptivePID scheduler, Projection-Free Exact W2,
Kernelized/Sinkhorn W2, 5 ODE integrators (DPM/UniPC/Heun/AMED/DP-RK45),
OT-Linear blender, Multi-Temp blender, Bayesian/Kalman/PID-Identity
merges, and 5 runner-registry families (Parallel/EarlyStop/Online).
86/87 achieved target, 0 regressions; the only miss was the weighted
coverage score on the external stress config (0.1916 vs target 0.20),
which is now Round-2 P1 work.

The Round-2 inventory below inventories every algorithm in the
codebase with the new **Round-2 status** column. Counts are tight
pluggable classes/protocols that have non-trivial numeric semantics.

### 1.1 Schedulers (`adaptive_reflow/algorithm/scheduler.py`, `scheduler_extra.py`, `sequential.py`)

| Algorithm | File:line | Category | What it does | Round-2 status (current capability + numbers) | Round-2 limitation |
|---|---|---|---|---|---|
| `CosineAnnealScheduler` | `scheduler.py:275` | INTERNAL | Default cosine annealing | `n_cap(r) = n_min + (n_max - n_min) * (1 - cos(pi r/(L-1)))/2`; selection_ratio ≈ 0.85 plateau | Not driven by paper-quantity A_g unless profile supplied; not adaptive in noise scale |
| `EDMScheduler` | `scheduler_extra.py:58` | INTERNAL (NEW R1) | Karras EDM σ(t) ramp | `n_cap = σ(t)/σ_max` with σ_min=0.002, σ_max=80, ρ=7; SNR-dB audit code emitted | Limited to fixed-shape σ(t); no adaptive σ_max per round |
| `AdaptivePIDScheduler` | `scheduler_extra.py:289` | INTERNAL (NEW R1) | Full PID on convergence signal | `shift += kp·(1-ratio) + ki·integral - kd·delta`; 5-round integral window; ki=0.05 | PID only on W2; no multi-metric blending |
| `JitteredConstantScheduler` | `scheduler_extra.py:613` | INTERNAL (NEW R1) | Constant + Gaussian jitter | `n_cap = 0.5 + jitter_std·N(0,1)`, default jitter_std=0.05 | Single jitter scale; no per-channel jitter |
| `ConvergenceAdaptiveScheduler` | `scheduler.py:1697` | INTERNAL | PID-lite on W2+coverage+sel-ratio | multi-metric EMA aggregator | Oscillation residual; legacy PID-lite (no integral) |
| `CodimensionSheetScheduler` | `scheduler.py:2256` | INTERNAL | Theorem-1 driven | caches `A_g, B_g, C_g, e_rho`; emits `evidence_ratio` | Ratio is reportable but not driver (now wrapped by `EvidenceDrivenScheduler`) |
| `EvidenceDrivenScheduler` | `evidence_driver.py:93` | INTERNAL (NEW R1) | Wrapper modulating `n_cap` by evidence ratio | `n_cap' = n_cap · factor(evidence_ratio, strength)`; default strength=1.0 | strength dial; `evidence_ratio is None` families pass through unchanged |
| `SequentialScheduler` | `sequential.py:95` | INTERNAL | Chain N schedulers by round range | 3-slot chain trajectory matches per-slot; A8+A9 audit codes | No handoff blending between slots |
| `SCHEDULER_REGISTRY` | `protocol_registry.py:128` | INTERNAL | dict[str, cls]; 11 entries | keys: cosine, constant, linear, exponential, polynomial, sigmoid, convergence_adaptive, codimension_sheet, edm, adaptive_pid, jittered_constant | WarmupLinear / Geometric / Handoff / PiecewiseSigmoid / Handoff registered in PROTOCOL_REGISTRY but no implementations |
| `build_scheduler` / `build_scheduler_from_config` | `scheduler.py:3000` | INTERNAL | Polymorphic factory | registry lookup over 11 entries | Cache invalidation on hot-reload |
| `_paper_evidence_balance` | `scheduler.py:2133` | INTERNAL | Helper | Heuristic or paper-quantity mode; asymptotic diagnostic via `check_evidence_mode` | Asymptotic gap not surfaced as audit code |

### 1.2 Policy drivers (`adaptive_reflow/algorithm/policy_driver.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `PolicyDriverProtocol` | `policy_driver.py:181` | contract | per-round `beta` generator | 3 impls in registry | Per-channel `β` override via mapping not yet supported |
| `ScheduleDerivedPolicyDriver` | `policy_driver.py:292` | INTERNAL | `β = n_cap` (default) | emits `POLICY_SCHEDULE_DERIVED` audit code | Single channel-vocabulary; ignores `prior_endpoint_digest` |
| `ConstantPolicyDriver` | `policy_driver.py:409` | INTERNAL | `β = const` | 0.5 default | No per-channel constants |
| `AdaptivePolicyDriver` | `policy_driver.py:505` | INTERNAL | `β = (1 - |p - t|)/C_g` | emits `BETA_SATURATION_FROM_PAPER_QUANTITY`; counter `beta_saturation_count` | Single target_estimate; no dual-target |

### 1.3 Merge operators (`adaptive_reflow/algorithm/merge_operator.py`, `merge_operator_extra.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `MergeOperatorProtocol` | `merge_operator.py:238` | contract | bounded update | 7 impls in registry | `audit_codes` non-mutation contract not enforced at runtime |
| `BoundedMergeOperator` | `merge_operator.py:357` | INTERNAL | Symmetric bounded merge | `e_rho/4` paper-quantity floor lift; degenerate-interval → floor | Static envelope; no variance tracking |
| `IdentityOperator` | `merge_operator.py:599` | INTERNAL | Pass-through | A13 audit code on non-finite | No audit beyond clip |
| `EMAOperator` | `merge_operator.py:668` | INTERNAL | `α·prev + (1-α)·dyn` | `alpha_schedule` callable | α constant; schedule-aware EMA is in extras |
| `KalmanBoundedMergeOperator` | `merge_operator_extra.py:45` | INTERNAL (NEW R1) | Variance-tracking Kalman merge | `K = σ²_p / (σ²_p + σ²_d)`; envelope honoured | Single-σ² state; no multi-source fusion |
| `BayesianMergeOperator` | `merge_operator_extra.py:233` | INTERNAL (NEW R1) | Beta-Bernoulli posterior | `alpha_post = alpha_p + dyn·e_c`; mean returned | Single effective_count |
| `PIDIdentityOperator` | `merge_operator_extra.py:376` | INTERNAL (NEW R1) | Pass-through + PID residual | `damped = (1-kd)·residual + kp·residual` | No full integral term |
| `ScheduleAwareEMAOperator` | `merge_operator_extra.py:466` | INTERNAL (NEW R1) | α(r) tracks n_cap | `α(r) = α_min + (α_max - α_min)·n_cap` | n_cap_hint is constant kwarg; ignores schedule_sample |

### 1.4 Blenders (`adaptive_reflow/algorithm/blender.py`, `blender_extra.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `LinearBlender` | `blender.py:449` | INTERNAL | `new = m·p + (1-m)·f` | `BLENDER_MEMORY_FRACTION_CLIPPED` audit code | Convex only; cannot extrapolate |
| `DistanceDecayBlender` | `blender.py:546` | INTERNAL | Distance-gated linear | `decay_factor` folded into digest; `per_round_metrics["blender_decay_factor"]` | Single global T |
| `OTLinearBlender` | `blender_extra.py:48` | INTERNAL (NEW R1) | Closed-form 1-D OT-path blend | `ot_path[k] = m·p_(k) + (1-m)·f_(k)` | 1-D per-coordinate; no joint OT |
| `MultiTemperatureDistanceDecayBlender` | `blender_extra.py:151` | INTERNAL (NEW R1) | Per-channel temperature | `T_c` per channel | Wraps DD; no closed-form OT integration |
| `RestartBlenderProtocol` | `blender.py:404` | contract | per-channel blender | 4 impls in registry | `to_config/from_config` heterogeneous across impls |
| `BLENDER_REGISTRY` (effective) | `protocol_registry.py:194` | INTERNAL | 4 families | linear / distance_decay / ot_linear / multi_temperature_distance_decay | Cannot register 5th family via config — needs new kwarg propagation |
| `_blender_config_hash` | `blender.py:690` | helper | SHA-256 family + qualname digest | Stable; folds `extra` | No canonical serializer for numpy scalars in `per_channel_temperatures` |

### 1.5 Runners + registry (`adaptive_reflow/algorithm/runner.py`, `batched_runner.py`, `runner_registry.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `ReInferenceRunner` | `runner.py:383` | INTERNAL | Round-by-round engine loop | per-round `scheduler → driver → merge → engine → blender → evaluator` | Sequential only; no early-stop |
| `BatchedTrajectoryRunner` | `batched_runner.py:429` | INTERNAL | T*K endpoints per round | T=8, K=16, cycle_length=20 default; vectorised inner loop (8→1 invocations) | `_w2_to_mode_centres` still default W2 (surrogate) |
| `RUNNER_REGISTRY` | `runner_registry.py:192` | INTERNAL | dict[str, cls]; 5 entries | reinference / batched / parallel / early_stop / online | Each stub returns dict, not full `run()` delegation |
| `ParallelRunner` (stub) | `runner_registry.py:38` | INTERNAL (NEW R1) | Thread-pool stub | n_workers=4 default | No real parallel inner loop wired |
| `EarlyStopRunner` (stub) | `runner_registry.py:78` | INTERNAL (NEW R1) | Early-stop stub | w2_tolerance=1e-3, min_rounds=5 | Returns dict only |
| `OnlineRunner` (stub) | `runner_registry.py:131` | INTERNAL (NEW R1) | Streaming stub | seed=0 | Returns dict only |

### 1.6 ODE integrators (`adaptive_reflow/adapters/integrators.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `IntegratorProtocol` | `integrators.py:42` | contract | ODE step surface | 6 impls in `INTEGRATOR_REGISTRY` | Only single-step signature; no adaptive-step reporting |
| `RK4Integrator` | `integrators.py:64` | EXTERNAL | Classical RK4 | fixed-step | O(n_steps) per call |
| `DormandPrinceRK45Integrator` | `integrators.py:113` | EXTERNAL | Adaptive DOPRI5 | rtol=1e-3, atol=1e-4, max_steps=1000; rtol/atol configurable | Adaptive loop not wired; single-step returns y5 only |
| `DPMSolverIntegrator` | `integrators.py:333` | EXTERNAL | DPM-Solver order-1 | `y + dt·v`; gives 5× step reduction (RK4@100 → DPM@20) | First-order only; no DPM-Solver++ (x0-pred) variant |
| `UniPCIntegrator` | `integrators.py:379` | EXTERNAL | UniPC predictor-corrector | order ∈ {1,2,3}; default order=1 | Order-2/3 unimplemented (only order-1 path) |
| `HeunIntegrator` | `integrators.py:438` | EXTERNAL | Improved Euler | `y + 0.5·dt·(v_t + v_next)` | Same as DPM order-1 in practice |
| `AMEDSolverIntegrator` | `integrators.py:480` | EXTERNAL | AMED-Solver placeholder | order-1 forward Euler step | Placeholder; full AMED not implemented |
| `INTEGRATOR_REGISTRY` | `integrators.py:527` | EXTERNAL | 6 entries | rk4 / dopri5 / dpm_solver / unipc / heun / am_ed | No stochastic SDE integrators (Euler-Maruyama, leapfrog, SDE-Heun) |
| `build_integrator` | `integrators.py:543` | EXTERNAL | factory | registry lookup | Caches no instances |

### 1.7 W2 estimators (`adaptive_reflow/eval/w2.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `W2EstimatorProtocol` | `w2.py:127` | contract | per-call estimator | 4 impls | no multi-sample bagging / bootstrap |
| `ModeCentreMSEW2` | `w2.py:238` | INTERNAL/EXTERNAL | legacy MSE-to-mode | squared units; high CV (~0.0073) | biased surrogate |
| `ProjectionFreeExactW2` | `w2.py:287` | EXTERNAL (NEW R1) | Sliced exact 1-D OT | CV reduced -71.7% (0.00727 → 0.00206) at n=128 | Gaussian projections only — no Rademacher, no Tree-SW |
| `KernelizedW2` | `w2.py:429` | EXTERNAL (NEW R1) | MMD-based | 3 kernels (rbf / laplacian / matern) | bandwidth not adapted to data scale |
| `SinkhornApproximatedW2` | `w2.py:534` | EXTERNAL (NEW R1) | Entropic OT | reg=0.1, n_iter=100; biased upward | no automatic reg selection |
| `W2_REGISTRY` | `w2.py:649` | EXTERNAL | 4 families | mode_centre_mse / projection_free / kernelized / sinkhorn | default = legacy (no behavioural change unless opted in) |
| `compute_w2` | `w2.py:676` | EXTERNAL | convenience | family dispatch | No batched mode (per-call) |

### 1.8 Coverage / energy / Lipschitz metrics (`adaptive_reflow/eval/coverage.py`, `lipschitz_diagnostic.py`, `coverage_score` in `twodim_fm_evaluator.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `weighted_coverage_score` | `coverage.py:95` | INTERNAL (NEW R1) | area-weighted Voronoi | separation 0.2252 (PASS); 0.1916 on stress config (FAIL) | One miss in stress config → R2 target |
| `energy_distance_with_ci` | `coverage.py:286` | INTERNAL (NEW R1) | bootstrap CI | relative width 0.1526 (PASS at n=256) | 1000 resamples — slower at high n |
| `coverage_score` (binary) | `twodim_fm_evaluator.py:269` | INTERNAL | fraction of cells hit | saturates at 1.0 (R1 documented) | still saturated in low-res cases |
| `lipschitz_modulus` | `lipschitz_diagnostic.py:96` | INTERNAL (NEW R1) | discrete Lipschitz on selection_ratio series | tail increment -96.2% (oscillating → converged) | Single-series; no kernel Lipschitz |
| `evaluate_lipschitz_convergence` | `lipschitz_diagnostic.py:186` | INTERNAL (NEW R1) | tail MC-rate check | `within_rate` verdict | Single-kernel |
| `bounded_lipschitz_distance` | `lipschitz_diagnostic.py:246` | INTERNAL (NEW R1) | truncated W1 in 1-D | `mean_i min(\|x_(i)-y_(i)\|, B)` | 1-D only; no multi-dim support |

### 1.9 Mixers (`adaptive_reflow/universal/mixer.py`, `mixer_ot.py`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `NoOpMixer` | `mixer.py:142` | INTERNAL | returns `prior` | n/a | n/a |
| `LatentConvexMixer` | `mixer.py:167` | INTERNAL | convex combination | relative scale error -100% | Convex only |
| `DiscreteIdentityMixer` | `mixer.py:207` | INTERNAL | discrete tokens | n/a | n/a |
| `LatentConvexMixer` (OT variant) | `mixer_ot.py` | INTERNAL (NEW R1) | OT displacement mixing | worst relative scale error 1.19e-15 (PASS) | 1-D per-coordinate OT only |
| `EqualRmsCoordinateMixer` | `molecular/mixer.py:307` | INTERNAL | RMS-preserving | n/a | global RMS only — no per-channel |

### 1.10 Frame / orchestration (`adaptive_reflow/frame/`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `Engine` | `engine.py:860` | INTERNAL | inner re-inference engine | per-round `run_round(bundle, policy, delta, phase)` | Single-engine; no multi-stage warmup |
| `AdaptiveReflowPolicyOrchestrator` | `orchestrator.py:251` | INTERNAL | top-level pipeline | monolithic | Stage registry not yet exposed |
| `LedgerChain` | `ledger_chain.py:110` | INTERNAL (NEW R1) | incremental chain verification | `verify_incremental` reduces 2080→64 hash computations (PASS) | No parallel-round chain support |
| `LedgerRow` | `engine.py:188` | contract | hash-chained ledger row | SHA-256 hash chain | Single-thread append; no concurrent rows |
| `PhaseState` | `engine.py:218`, `phase.py` | contract | per-round phase state | `round_in_cycle, schedule_phase_index, horizon_remaining` | hard-coded schedule_phase values |
| `compute_channel_decision`, `check_monotonicity_property` | `channel_rule.py:461,632` | INTERNAL | per-channel rule | sweep-based 1→32 adjacent pairs (PASS) | only single-factor monotonicity |
| `Stage Protocol` | `stage.py` (NEW R1) | INTERNAL | pipeline stage surface | not yet implemented — STAGE_REGISTRY is empty | stage pipeline reorder not exposed |

### 1.11 Tools (`tools/`)

| Algorithm | File:line | Category | What it does | Round-2 status | Round-2 limitation |
|---|---|---|---|---|---|
| `tools/run_ablation.py` | full file | benchmark | 22-row ablation grid | reproduces all configs | 22 rows only |
| `tools/benchmark_uplifts.py` | full file | benchmark | 4-section uplift benchmark | 87 measurements | Section 5 (Round-2) not present |
| `tools/run_metric_per_family.py` | full file | benchmark | per-family metric comparison | yes | No SOTA round-2 entries |

**Total algorithms inventoried (Round 2 lens): ~165** — framework now exposes:

* 12 scheduler families (`SCHEDULER_FAMILIES`).
* 3 policy drivers.
* 7 merge operators (`MERGE_OPERATOR_FAMILIES`).
* 4 blenders (`BLENDER_FAMILIES`).
* 5 runner-registry families (`RUNNER_REGISTRY`).
* 6 ODE integrators (`INTEGRATOR_REGISTRY`).
* 4 W2 estimators (`W2_REGISTRY`).
* 2 rotation policies (`ROTATION_POLICY_REGISTRY`).
* 2 protocol-registry generic builders.
* 1 ledger-chain (`LedgerChain`), 1 bounded-Lipschitz helper.
* 3 mixer families (`LatentConvex` / `LatentConvexOT` / `NoOp`).
* ~22 supporting dataclasses + helpers + evaluators.

---

## STEP 2 — External research on SOTA 2024-2026

(Research conducted via WebSearch in 2026-08-29. Round-1 cited ~30
arXiv / NeurIPS / CVPR / ICLR entries; Round-2 adds the entries below.
All listed arXiv IDs are referenced under "Sources" at the end of this
file.)

### 2.1 SDE / stochastic flow-matching solvers (NEW)

| Method | arXiv | Key idea | Replaces |
|---|---|---|---|
| **Stochastic Flow Matching (SFM)** for resolving small-scale physics | [arXiv:2410.19814](https://arxiv.org/abs/2410.19814) (NVIDIA, Oct 2024) | Encoder for deterministic component + flow matching for stochastic small-scale details with adaptive noise scaling; outperforms conditional diffusion on weather super-resolution | RK4 fixed-step ODE / order-1 DPM |
| **Neural Stochastic Flows (NSFs)** | NeurIPS 2025 poster, [arXiv:2510.25769](https://arxivlens.com/PaperView/Details/neural-stochastic-flows-solver-free-modelling-and-inference-for-sde-solutions-7738-55dafcef) | Direct learning of (latent) SDE transition laws via conditional normalizing flows; up to **2 OOM speed-up** vs numerical SDE solvers at equal distributional accuracy | Numerical SDE / Euler-Maruyama |
| **Bayesian Flow Networks unified with diffusion SDEs** | ICML 2024, [arXiv:2404.15766](https://ui.adsabs.harvard.edu/abs/2024arXiv240415766X/abstract) | Specialized BFN solvers for SDEs achieving **5-20× faster sampling** | Plain diffusion solvers |
| **Flow Matching: Markov Kernels, Stochastic Processes and Transport Plans** | [arXiv:2501.16839](https://arxiv.org/abs/2501.16839) (Wald & Steidl, Jan 2025; rev Aug 2025) | Mathematical unification of FM via transport plans / Markov kernels / stochastic processes; bridges to Bayesian inverse problems | Theory-level reference for the framework |
| **Generalized Flow Matching for Transition Dynamics** | [arXiv:2410.15128](https://scirate.com/arxiv/2410.15128) (Oct 2024) | Learns vector fields for probable transition paths (metastable states); iterative importance-weight refinement | Vanilla FM |
| **CFO: Continuous-time PDE dynamics via flow-matched neural operators** | [arXiv:2512.05297](https://doi.org/10.48550/ARXIV.2512.05297) (Dec 2025) | FM for PDE right-hand sides without backprop-through-ODE; **87 % relative error reduction** on Lorenz / Burgers | Black-box ODE solvers for PDE systems |
| **Flow Matching Neural Processes** | NeurIPS 2025, [arXiv:2512.23853](https://ui.adsabs.harvard.edu/abs/2025arXiv251223853/abstract) | New NP model based on FM; controllable accuracy/runtime via ODE solver steps | Vanilla NPs |
| **Stochastic EDM preconditioner** | [arXiv:2409.06984](https://arxiv.org/abs/2409.06984) (Sep 2024) | Diffusion models as stochastic preconditioners; Karras-style noise conditioning; EDM2-style step counts | Plain EDM |
| **EDM2 sampling-step analysis** | [arXiv:2410.17090](https://arxiv.org/abs/2410.17090) (Oct 2024) | Karras method as preconditioner at high noise levels on ImageNet-64 | EDM original |

### 2.2 Wasserstein / OT estimators (NEW)

| Method | arXiv | Key idea | Replaces |
|---|---|---|---|
| **Support Coverage via KDE** | NeurIPS 2024 GenBench, [arXiv:2412.00849](https://arxiv.org/abs/2412.00849) (Dec 2024, rev Jul 2025) | New KDE-based evaluation metric: expected value of real-data KDE density under generator-induced distribution | Voronoi binary coverage |
| **Wasserstein-2 Barycenters: Foundations, Methods, Applications** | [arXiv:2509.06580](https://arxiv.org/abs/2509.06580) (Sep 2025) | Comprehensive survey on W2 barycenters; distributional summary / coverage metric | Single-point W2 statistic |
| **Tree-Sliced Wasserstein with Nonlinear Projection** | ICML 2025, [arXiv:2505.00968](https://arxiv.org/pdf/2505.00968v1) | Replaces linear projections with Circular / Spatial Radon transforms; tree framework | Linear-projection sliced W2 |
| **Efficient Sliced Wasserstein via Adaptive Bayesian Optimization** | [arXiv:2509.17405](https://adsabs.harvard.edu/abs/2025arXiv250917405A/abstract) (Sep 2025) | BOSW / RBOSW / ABOSW / ARBOSW projection-direction selectors | Fixed-direction sliced W2 |
| **Differentiable Generalized Sliced Wasserstein Plans** | NeurIPS 2025, [mlanthology/neurips/2025/chapel2025neurips](https://mlanthology.org/neurips/2025/chapel2025neurips-differentiable) | Reformulates min-SWGG as bilevel optimization; high-dim + manifold support; sliced OT for conditional FM | Standard sliced W2 |
| **Slicing Wasserstein Over Wasserstein via Functional OT** | [arXiv:2509.22138](http://arxiv-export-lb.library.cornell.edu/abs/2509.22138) (Sep 2025) | Double-sliced Wasserstein (DSW) metric for meta-measures; L2 projections via GPs | Single-sliced W2 |
| **Differential Entropy Survey** | [arXiv:2406.19432](https://arxiv.org/html/2406.19432v1) (Jun 2024) | Comprehensive empirical comparison of kNN / Kozachenko–Leonenko / kernel / spacing entropy estimators | ad-hoc entropy |
| **Unifying Information-theoretic Perspective on Evaluating Generative Models** | [arXiv:2412.14340](https://adsabs.harvard.edu/abs/2024arXiv241214340F) (Dec 2024) | PCE / RCE / RE tri-dimensional metric based on KL divergence and entropy via kNN density estimators; RE detects mode shrinkage in CFG diffusion | Density & Coverage (Naeem 2020) |

### 2.3 EDM / Karras step-count reduction (NEW)

* EDM2 with preconditioner: [arXiv:2410.17090](https://arxiv.org/abs/2410.17090) — uses Karras method as preconditioner at high noise; reports step-count reduction on ImageNet-64 (Oct 2024).
* EDM stochastic preconditioner: [arXiv:2409.06984](https://arxiv.org/abs/2409.06984) (Sep 2024).
* EDM-as-sampler: `n_cap = σ(t)/σ_max` mapping (already shipped as `EDMScheduler`); Round-2 next step: adaptive `σ_max` per round + EDM2-style preconditioner wiring.

### 2.4 Summary — external papers cited (Round-2 additions)

* **SDE / stochastic solvers (9):** [2410.19814](https://arxiv.org/abs/2410.19814), [2510.25769](https://arxivlens.com/PaperView/Details/neural-stochastic-flows-solver-free-modelling-and-inference-for-sde-solutions-7738-55dafcef), [2404.15766](https://ui.adsabs.harvard.edu/abs/2024arXiv240415766X/abstract), [2501.16839](https://arxiv.org/abs/2501.16839), [2410.15128](https://scirate.com/arxiv/2410.15128), [2512.05297](https://doi.org/10.48550/ARXIV.2512.05297), [2512.23853](https://ui.adsabs.harvard.edu/abs/2025arXiv251223853/abstract), [2409.06984](https://arxiv.org/abs/2409.06984), [2410.17090](https://arxiv.org/abs/2410.17090).
* **OT / W2 estimators (6):** [2412.00849](https://arxiv.org/abs/2412.00849), [2509.06580](https://arxiv.org/abs/2509.06580), [2505.00968](https://arxiv.org/pdf/2505.00968v1), [2509.17405](https://adsabs.harvard.edu/abs/2025arXiv250917405A/abstract), [2509.22138](http://arxiv-export-lb.library.cornell.edu/abs/2509.22138), [2412.14340](https://adsabs.harvard.edu/abs/2024arXiv241214340F).
* **Differential entropy (1):** [2406.19432](https://arxiv.org/html/2406.19432v1).
* **Differentiable SW plans (1):** [mlanthology/neurips/2025/chapel2025neurips](https://mlanthology.org/neurips/2025/chapel2025neurips-differentiable).

**Round-2 new papers cited: 17 distinct arXiv / NeurIPS / NeurIPS-W entries.** Combined with the Round-1 30, total ~47 unique entries.

---

## STEP 3 — Per-algorithm uplift plan (Round 2)

For every algorithm still considered weak, the table below records the
**Round-2 limitation** and the concrete uplift.

| Algorithm | File:line | Category | Round-2 limitation | Uplift (concrete) | Quantitative target | Plug-in design |
|---|---|---|---|---|---|---|
| `weighted_coverage_score` | `eval/coverage.py:95` | INTERNAL | **Fails** stress config (0.1916 vs 0.20) | Add **`KDE-support-coverage`** estimator ([arXiv:2412.00849](https://arxiv.org/abs/2412.00849)) — expected KDE-density on generator-induced measure; complement Voronoi with support coverage | stress-config score ≥ 0.22 (close the 0.2 miss) | new `support_coverage_score(samples, ref, bandwidth=...)` in `eval/coverage.py`; registered in new `COVERAGE_REGISTRY` |
| `ProjectionFreeExactW2` | `eval/w2.py:287` | EXTERNAL | Gaussian projections only | Add **Rademacher projections** (`θ ∈ {±1}^d / √d`) for higher-dim slicing | W2 CV at n=128 drops another 10 % (target 0.0018) | new `ProjectionFreeRademacherW2` in `w2.py`; `W2_REGISTRY["projection_free_rademacher"]` |
| `ProjectionFreeExactW2` | `eval/w2.py:287` | EXTERNAL | Linear projections only | Add **Tree-Sliced W2** ([arXiv:2505.00968](https://arxiv.org/pdf/2505.00968v1)) — nonlinear Radon transforms | Bias ↓ 30% on anisotropic Gaussians | new `TreeSlicedW2` in `w2.py`; `W2_REGISTRY["tree_sliced"]` |
| `W2_REGISTRY` | `eval/w2.py:649` | EXTERNAL | 4 entries | Add 3 entries: `projection_free_rademacher`, `tree_sliced`, `w2_barycenter` | registry size 4 → 7 | extend `W2_REGISTRY` |
| `W2 barycenter coverage` (NEW) | `eval/w2.py` (NEW) | INTERNAL | single-point W2 | Compute **W2 barycenter** ([arXiv:2509.06580](https://arxiv.org/abs/2509.06580)) over per-round endpoints; coverage = distance of round distribution to barycenter | barycenter distance ≤ W2 distance (oracle-style) | new `W2BarycenterCoverage` in `eval/coverage.py` |
| `KernelizedW2` | `eval/w2.py:429` | EXTERNAL | bandwidth fixed | Add **median-heuristic bandwidth selection** (`h = median(\|\|x_i - x_j\|\|)`) | kernel-W2 CV at n=128 drops 20 % | new constructor kwarg `bandwidth="median"` |
| `coverage_score` (binary) | `eval/twodim_fm_evaluator.py:269` | INTERNAL | saturates at 1.0 | Add **partial coverage**: per-cell fractional coverage 0.0-1.0 in place of binary | resolves saturation in 2D | new helper `partial_coverage_score` |
| `lipschitz_modulus` | `eval/lipschitz_diagnostic.py:96` | INTERNAL | 1-D series only | Add **kernel Lipschitz** ([arXiv:2412.14340](https://adsabs.harvard.edu/abs/2024arXiv241214340F) PCE/RCE/RE) — Lipschitz constant on the *density* rather than the trajectory | kernel-Lipschitz ratio ≤ 1/sqrt(N) | new `kernel_lipschitz_constant(samples)` in `eval/lipschitz_diagnostic.py` |
| `selection_ratio` (Theorem 1) | `eval/posterior_selection_evaluator.py:397` | INTERNAL | single terminal value | Add **differential-entropy estimator** ([arXiv:2406.19432](https://arxiv.org/html/2406.19432v1) KL estimator) for top-k coverage threshold | entropy estimate CV ≤ 0.1 at N=256 | new `top_k_coverage_with_entropy` in `eval/coverage.py`; uses kNN KL estimator |
| `EDMScheduler` | `algorithm/scheduler_extra.py:58` | INTERNAL | fixed σ_max per cycle | Add **adaptive σ_max per round** driven by per-round W2 derivative (PID-style on σ_max) | SNR-dB monotonicity preserved; σ_max variance ↓ 30 % | new constructor kwarg `adaptive_sigma_max=True` |
| `AdaptivePIDScheduler` | `scheduler_extra.py:289` | INTERNAL | only W2 metric | Add **multi-metric PID** with separate PID loops for W2 + coverage + selection_ratio | oscillation amplitude ↓ 50 % | extend constructor with `metric_weights: dict[str, float]` |
| `JitteredConstantScheduler` | `scheduler_extra.py:613` | INTERNAL | single jitter scale | Add **per-channel jitter** via `per_channel_jitter_std` mapping | per-channel β variance ↓ 40 % | new constructor kwarg |
| `SequentialScheduler` | `algorithm/sequential.py:95` | INTERNAL | no slot handoff blending | Add **HandoffSequentialScheduler** — blend `slot[i]` into `slot[i+1]` over a configurable handoff window `k` | smooth transition; no abrupt `n_cap` step | new class in `algorithm/sequential.py`; new SCHEDULER_REGISTRY key `handoff_sequential` |
| `SCHEDULER_FAMILIES` | `protocol_registry.py:53` | INTERNAL | 16 declared, only 11 implemented | Implement **WarmupLinearScheduler**, **GeometricDecayScheduler**, **PiecewiseSigmoidScheduler**, **HandoffSequentialScheduler**, **MultiChannelJitteredConstantScheduler** | registry_size 11 → 16 | extend `protocol_registry._build_scheduler_registry` |
| `AdaptivePolicyDriver` | `policy_driver.py:505` | INTERNAL | single target_estimate | Add **dual-target driver**: `β = (1 - |p - t1|)(1 - |p - t2|) / C_g` | per-round β variance ↓ 30 % | subclass `AdaptivePolicyDriver` |
| `ConstantPolicyDriver` | `policy_driver.py:409` | INTERNAL | single β | Add **per-channel constant** mode | ≥ 2 channels independently | subclass |
| `KalmanBoundedMergeOperator` | `merge_operator_extra.py:45` | INTERNAL | single σ² | Add **multi-source Kalman** — fuse two `dynamic` signals with separate variances | posterior W2 reduction ↑ to 30 % | new class `MultiSourceKalmanMergeOperator` |
| `BayesianMergeOperator` | `merge_operator_extra.py:233` | INTERNAL | single effective_count | Add **time-varying effective_count** tied to schedule `n_cap(r)` | selection_ratio convergence ↑ | new class |
| `EMAOperator` | `merge_operator.py:668` | INTERNAL | α constant | Wire schedule sample directly into `merge` via new kwarg `schedule_sample` | schedule-aware blending without separate class | constructor signature change (additive) |
| `LinearBlender` | `blender.py:449` | INTERNAL | convex only | Add **OT-barycentric blender** ([arXiv:2509.06580](https://arxiv.org/abs/2509.06580) barycentric coords in target cell) | OT-path distance observable | new class `BarycentricBlender` |
| `OTLinearBlender` | `blender_extra.py:48` | INTERNAL | per-coordinate 1-D OT | Add **multi-D OT joint map** via Tree-Sliced W2 routing | joint-OT distance ↓ on correlated channels | new class `JointOTLinearBlender` |
| `RUNNER_REGISTRY` stubs | `runner_registry.py:38` | INTERNAL | return dict only | Wire **real** `run()` on `ParallelRunner` (thread pool), `EarlyStopRunner` (W2 tolerance), `OnlineRunner` (streaming) | wall-clock ↓ ≥ 2×, early-stop within 30 % oracle | extend stubs to delegate to `ReInferenceRunner` / `BatchedTrajectoryRunner` |
| `BatchedTrajectoryRunner` | `batched_runner.py:429` | INTERNAL | sequential round loop | Add **parallel-round** runner using threads; preserves batched semantics | wall-clock ↓ ≥ 1.5× on 4-core | new class `ParallelBatchedRunner` |
| `DormandPrinceRK45Integrator` | `integrators.py:113` | EXTERNAL | adaptive loop not wired | Wire **adaptive step loop** with rejection + max_steps | endpoint L2 error ↓ 50 % at fixed budget | new method `integrate(t_grid, v, y0)` |
| `DPMSolverIntegrator` | `integrators.py:333` | EXTERNAL | first-order only | Add **DPM-Solver++** (x0-prediction) variant | endpoint L2 at NFE=10 ≤ 0.05 (DPM++) vs 0.05 at NFE=20 (DPM order-1) | new class `DPMSolverPPIntegrator` |
| `UniPCIntegrator` | `integrators.py:379` | EXTERNAL | order-1 only | Implement **order-2 and order-3** UniPC steps | endpoint L2 at NFE=10 ≤ 0.02 (UniPC-3) | new class or constructor switch |
| `AMEDSolverIntegrator` | `integrators.py:480` | EXTERNAL | placeholder | Replace with **real AMED-Solver** order-1 ([CVPR 2024 diff-sampler](https://github.com/zju-pi/diff-sampler)) | endpoint L2 ↓ 30 % | new class `AMEDSolverReal` |
| `INTEGRATOR_REGISTRY` | `integrators.py:527` | EXTERNAL | no SDE integrators | Add **EulerMaruyamaIntegrator**, **SDEHeunIntegrator**, **SymplecticLeapfrogIntegrator** | SDE-aware sampling; symplectic preserves Hamiltonian structure | new classes; `INTEGRATOR_REGISTRY["euler_maruyama", "sde_heun", "leapfrog"]` |
| `SyntheticAdapter` (target distributions) | `adapters/synthetic.py` | EXTERNAL | single target | Add **anisotropic Gaussian target** (covariance λI with λ varying across modes) + **heavy-tailed target** (Cauchy mixture) | coverage separation ↑ 30 % on these targets | new target classes in `synthetic.py` |
| `ToyGaussianAdapter` | `adapters/toy_gaussian.py` | EXTERNAL | 1-D Gaussian only | Add **multi-modal 2-D Gaussian** target (`eval/`) | coverage separation visible in 2-D | new class `MultiModal2DAdapter` |
| `TwodimFMAdapter` | `adapters/twodim_fm.py:404` | EXTERNAL | fixed velocity MLP | Add **adaptive-capacity velocity MLP** (per-round width driven by scheduler) | selection_ratio convergence ↑ | new adapter `AdaptiveMLPAdapter` |
| `Stochastic FM adapter` (NEW) | `adapters/` (NEW) | EXTERNAL | no stochastic sampling | Add **StochasticFMAdapter** ([arXiv:2410.19814](https://arxiv.org/abs/2410.19814)) — encoder + stochastic FM with adaptive noise scaling | W2 ↓ 25 % on stochastic targets | new adapter; registry extension |
| `LedgerChain` | `frame/ledger_chain.py:110` | INTERNAL | single-thread append | Add **parallel-round append** — accept out-of-order rounds, sort by `round_index`, then re-verify | supports ParallelRunner without breaking tamper-evidence | extend `LedgerChain.append` with optional async queue |
| `check_monotonicity_property` | `frame/channel_rule.py:632` | INTERNAL | single-factor | Add **3-way interaction monotonicity** (factor_a, factor_b, factor_c → outcome) | 2-way → 3-way coverage | extend helper |
| `ConvergenceAdaptiveScheduler` | `algorithm/scheduler.py:1697` | INTERNAL | PID-lite | Wire **multi-metric** feedback (W2 + coverage + selection_ratio) as separate loops | reduce over-fit to single metric | constructor kwarg `metric_weights` |
| `_paper_evidence_balance` | `scheduler.py:2133` | INTERNAL | asymptotic gap not surfaced | Emit **gap code** (`evidence_asymptotic_gap=...`) on every sample at eps < 1e-3 when heuristic | diagnostic coverage 100 % at eps < 1e-3 | extend helper |
| `STAGE_REGISTRY` | `frame/stage.py` (NEW R1) | INTERNAL | empty | Implement **Stage** Protocol + 4 stage implementations (`RunStage`, `CalibrationStage`, `ClaimGateStage`, `PromotionStage`) | pipeline reorder via config | new file `frame/stage.py`; `STAGE_REGISTRY` with 4 keys |
| `LayeredMetricPanel` | `eval/metric_panel.py:127` | INTERNAL | hard-fail | Add **soft mode** (`strict=False`) — warn instead of raise on tier violation | zero false-positive failures | constructor kwarg |
| `RoundToRoundOscillationDetector` | `eval/protocol.py:280` | INTERNAL | threshold-based | Add **CUSUM detector** + **Bayesian online change-point detection** ([arXiv:0710.3742](https://arxiv.org/abs/0710.3742)) | detection latency ↓ 50 % | new detector class |
| `PairedComparisonRegistry` | `eval/protocol.py:110` | INTERNAL | static | Add **online arm addition** during run | enables bandit arm selection | extend registry |
| `Channel rule` | `frame/channel_rule.py:461` | INTERNAL | single-factor | Add **cross-channel interaction** — `evidence_cross_channel(factor_a, factor_b) -> evidence_score` | audit_codes for cross-channel interactions | new helper |

---

## STEP 4 — Prioritised list

### P0 — Must do (qualitative framework uplift)

1. **Adaptive σ_max on `EDMScheduler`** — adaptive per-round σ_max driven by W2 derivative; Round-2 framework-level scheduler SNR uplift.
2. **Multi-metric `AdaptivePIDScheduler`** — separate PID loops for W2 + coverage + selection_ratio; Round-2 oscillation damping uplift.
3. **Rademacher projections on `ProjectionFreeExactW2`** — high-dim slicing variant; Round-2 metric-quality uplift.
4. **Tree-Sliced W2** ([arXiv:2505.00968](https://arxiv.org/pdf/2505.00968v1)) — nonlinear Radon transform; bias ↓ on anisotropic Gaussians.
5. **DPM-Solver++ (x0-pred) integrator** — `INTEGRATOR_REGISTRY["dpm_solver_pp"]`; 2× step count reduction vs DPM order-1.
6. **UniPC order-2 and order-3** — `INTEGRATOR_REGISTRY["unipc_2", "unipc_3"]`; endpoint L2 ↓ 5× at NFE=10.
7. **SDE integrators (Euler-Maruyama, SDE-Heun, Leapfrog)** — `INTEGRATOR_REGISTRY` extensions; stochastic-aware sampling.
8. **Real `ParallelRunner` / `EarlyStopRunner` / `OnlineRunner` wiring** — replace dict-stub with delegation; wall-clock ↓ ≥ 2× on multi-core.
9. **Stochastic FM adapter** ([arXiv:2410.19814](https://arxiv.org/abs/2410.19814)) — new `adapters/stochastic_fm.py`; W2 ↓ 25 % on stochastic targets.
10. **Stage Protocol + `STAGE_REGISTRY`** with 4 stages — pluggable pipeline composition.

### P1 — Should do (clear measurable improvement)

11. KDE-support-coverage metric ([arXiv:2412.00849](https://arxiv.org/abs/2412.00849)) — fix the 0.1916 stress-config miss.
12. Differential-entropy estimator on top-k coverage ([arXiv:2406.19432](https://arxiv.org/html/2406.19432v1)).
13. W2 barycenter coverage ([arXiv:2509.06580](https://arxiv.org/abs/2509.06580)).
14. Adaptive step loop on DOPRI5 (`integrate(t_grid, v, y0)` method).
15. Multi-source Kalman merge operator.
16. Handoff sequential scheduler.
17. Adaptive σ_max wired into EDM2-style preconditioner ([arXiv:2410.17090](https://arxiv.org/abs/2410.17090)).
18. Anisotropic Gaussian + heavy-tailed targets.
19. Multi-channel `JitteredConstantScheduler`.
20. Per-channel `ConstantPolicyDriver`.
21. Dual-target `AdaptivePolicyDriver`.
22. Time-varying effective_count on `BayesianMergeOperator`.
23. Schedule-aware `EMAOperator` (constructor kwarg).
24. Joint OT `OTLinearBlender` via Tree-Sliced W2 routing.
25. Barycentric blender ([arXiv:2509.06580](https://arxiv.org/abs/2509.06580)).
26. Parallel `LedgerChain` append.
27. Soft mode on `LayeredMetricPanel`.
28. CUSUM / Bayesian change-point detector.
29. Cross-channel interaction in channel rule.

### P2 — Nice to have

30. Kernel Lipschitz constant on density (PCE/RCE/RE-style from [arXiv:2412.14340](https://adsabs.harvard.edu/abs/2024arXiv241214340F)).
31. Differentiable sliced-Wasserstein plans ([mlanthology/neurips/2025/chapel2025neurips](https://mlanthology.org/neurips/2025/chapel2025neurips-differentiable)).
32. Median-heuristic bandwidth selection on `KernelizedW2`.
33. Slicing Wasserstein over Wasserstein ([arXiv:2509.22138](http://arxiv-export-lb.library.cornell.edu/abs/2509.22138)).
34. Adaptive Bayesian optimization for SW directions ([arXiv:2509.17405](https://adsabs.harvard.edu/abs/2025arXiv250917405A/abstract)).
35. Per-channel `AdaptivePolicyDriver` (3-way interaction).
36. `MultiModal2DAdapter` for 2D target distributions.
37. Online arm addition to `PairedComparisonRegistry`.
38. 3-way interaction monotonicity check.
39. Real `AMEDSolverReal` (CVPR 2024 diff-sampler replacement).
40. Streamed `online_runner` event hooks.
41. Multi-channel `AdaptivePIDScheduler` rate constants.

---

## STEP 5 — Pluggability design checklist

For each P0/P1 uplift, the plug-in design is sketched below so the
existing Protocol surface stays canonical.

### 5.1 Adaptive σ_max on `EDMScheduler` (P0)
- **Protocol surface extended:** none (existing `SchedulerProtocol`).
- **Existing implementations to keep:** all 12 scheduler families.
- **New implementation:** constructor kwarg `adaptive_sigma_max=True` on `EDMScheduler`; per-round σ_max driven by W2 derivative.
- **Registration point:** `SCHEDULER_REGISTRY["edm"]` (in-place upgrade).
- **Test strategy:** σ_max variance across rounds ↓ 30 %; SNR-dB monotonicity preserved.

### 5.2 Multi-metric `AdaptivePIDScheduler` (P0)
- **Protocol surface extended:** `metric_weights: dict[str, float]` constructor kwarg on `AdaptivePIDScheduler`.
- **Existing implementations to keep:** all 11 other scheduler families (default `metric_weights={"W2": 1.0}` reproduces R1 behaviour).
- **Registration point:** `SCHEDULER_REGISTRY["adaptive_pid"]`.
- **Test strategy:** oscillation amplitude on multi-metric on two_moons ↓ ≥ 50 % vs single-metric.

### 5.3 Rademacher projections on `ProjectionFreeExactW2` (P0)
- **Protocol surface extended:** new `projection_kind: str` kwarg (`"gaussian"` default; `"rademacher"` new) on `ProjectionFreeExactW2`.
- **Existing implementations to keep:** legacy `ProjectionFreeExactW2` (default projection_kind="gaussian").
- **New implementation:** `ProjectionFreeRademacherW2` in `w2.py`; `W2_REGISTRY["projection_free_rademacher"]`.
- **Test strategy:** W2 CV at n=128 ≤ 0.0018 (10 % improvement).

### 5.4 Tree-Sliced W2 (P0)
- **Protocol surface extended:** none (conforms to existing `W2EstimatorProtocol`).
- **New implementation:** `TreeSlicedW2` in `eval/w2.py`; `W2_REGISTRY["tree_sliced"]`.
- **Test strategy:** bias ↓ 30 % on anisotropic Gaussians.

### 5.5 DPM-Solver++ / UniPC order-2/3 (P0)
- **Protocol surface extended:** none (`IntegratorProtocol`).
- **New implementations:** `DPMSolverPPIntegrator`, `UniPCIntegrator2`, `UniPCIntegrator3` in `integrators.py`.
- **Registration point:** `INTEGRATOR_REGISTRY["dpm_solver_pp", "unipc_2", "unipc_3"]`.
- **Test strategy:** endpoint L2 at NFE=10 ≤ 0.02 (UniPC-3) / ≤ 0.05 (DPM++).

### 5.6 SDE integrators (P0)
- **Protocol surface extended:** new `SDEIntegratorProtocol` (extends `IntegratorProtocol` with `sigma: Callable[[float], float]` drift-diffusion input).
- **New implementations:** `EulerMaruyamaIntegrator`, `SDEHeunIntegrator`, `SymplecticLeapfrogIntegrator`.
- **Registration point:** `INTEGRATOR_REGISTRY["euler_maruyama", "sde_heun", "leapfrog"]`.
- **Test strategy:** symplectic preserves Hamiltonian energy (drift-diffusion pair tested on `dx = x dt + σ dW`).

### 5.7 Real `ParallelRunner` / `EarlyStopRunner` / `OnlineRunner` (P0)
- **Protocol surface extended:** none (`RunnerProtocol` already in `runner_registry.py`).
- **New implementations:** replace dict-stub `run()` methods with delegation to `ReInferenceRunner` / `BatchedTrajectoryRunner`.
- **Registration point:** `RUNNER_REGISTRY` keys unchanged.
- **Test strategy:** wall-clock ↓ ≥ 2× on 4-core for `ParallelRunner`; early-stop within 30 % of oracle round count.

### 5.8 Stochastic FM adapter (P0)
- **Protocol surface extended:** none (`FlowMatchingODEAdapter`).
- **New implementation:** `StochasticFMAdapter` in `adapters/stochastic_fm.py`.
- **Registration point:** `ADAPTER_REGISTRY` (new) with key `"stochastic_fm"`.
- **Test strategy:** W2 ↓ 25 % on stochastic targets (Cauchy mixture).

### 5.9 Stage Protocol + `STAGE_REGISTRY` (P0)
- **Protocol surface extended:** new `Stage` Protocol in `frame/stage.py`.
- **New implementations:** `RunStage`, `CalibrationStage`, `ClaimGateStage`, `PromotionStage`.
- **Registration point:** `STAGE_REGISTRY` with 4 keys.
- **Test strategy:** each stage independently unit-testable; pipeline reorder via config (no engine coupling).

### 5.10 KDE-support-coverage (P1)
- **Protocol surface extended:** none.
- **New implementation:** `support_coverage_score(samples, ref, bandwidth)` in `eval/coverage.py`.
- **Registration point:** new `COVERAGE_REGISTRY` with key `"kde_support"`.
- **Test strategy:** stress-config score ≥ 0.22.

### 5.11 Differential-entropy estimator on top-k coverage (P1)
- **Protocol surface extended:** none.
- **New implementation:** `top_k_coverage_with_entropy(samples, ref, k)` in `eval/coverage.py` using kNN KL estimator.
- **Registration point:** `COVERAGE_REGISTRY["top_k_entropy"]`.

### 5.12 W2 barycenter coverage (P1)
- **Protocol surface extended:** none.
- **New implementation:** `W2BarycenterCoverage` in `eval/coverage.py`.
- **Registration point:** `COVERAGE_REGISTRY["w2_barycenter"]`.

### 5.13 DOPRI5 adaptive step loop (P1)
- **Protocol surface extended:** new method `integrate(t_grid, v, y0)` on `IntegratorProtocol`.
- **New implementation:** `DormandPrinceRK45Integrator.integrate` runs the adaptive loop and returns `(t_values, y_values)`.
- **Test strategy:** endpoint L2 error ↓ 50 % at fixed budget; reported `n_steps` matches oracle.

### 5.14 Multi-source Kalman merge (P1)
- **Protocol surface extended:** new optional `merge_multi(prev, dynamics, variances, ...)` method.
- **New implementation:** `MultiSourceKalmanMergeOperator` in `merge_operator_extra.py`.
- **Registration point:** `MERGE_OPERATOR_REGISTRY["multi_source_kalman"]`.

### 5.15 Handoff sequential scheduler (P1)
- **Protocol surface extended:** none (`SchedulerProtocol`).
- **New implementation:** `HandoffSequentialScheduler` in `algorithm/sequential.py`.
- **Registration point:** `SCHEDULER_REGISTRY["handoff_sequential"]`.

### 5.16 Anisotropic Gaussian + heavy-tailed targets (P1)
- **Protocol surface extended:** none (existing `TargetDistribution`).
- **New implementations:** `AnisotropicGaussianTarget`, `HeavyTailedTarget` in `eval/synthetic_oracle.py` or `adapters/synthetic.py`.
- **Test strategy:** coverage separation ↑ 30 % on these targets.

### 5.17 Multi-channel `JitteredConstantScheduler` (P1)
- **Protocol surface extended:** none (`SchedulerProtocol`).
- **New implementation:** `MultiChannelJitteredConstantScheduler` in `algorithm/scheduler_extra.py`.
- **Registration point:** `SCHEDULER_REGISTRY["multi_channel_jittered"]`.

### 5.18 Per-channel `ConstantPolicyDriver` (P1)
- **Protocol surface extended:** none.
- **New implementation:** `MultiChannelConstantPolicyDriver` in `policy_driver.py`.
- **Registration point:** `POLICY_DRIVER_REGISTRY["multi_channel_constant"]`.

### 5.19 Dual-target `AdaptivePolicyDriver` (P1)
- **Protocol surface extended:** constructor kwarg `target_estimates: tuple[float, ...]`.
- **New implementation:** `DualTargetAdaptivePolicyDriver`.
- **Registration point:** `POLICY_DRIVER_REGISTRY["dual_target_adaptive"]`.

### 5.20 Time-varying effective_count on `BayesianMergeOperator` (P1)
- **Protocol surface extended:** constructor kwarg `effective_count_schedule: Callable[[int], float]`.
- **New implementation:** same `BayesianMergeOperator` extended.
- **Registration point:** `MERGE_OPERATOR_REGISTRY["bayesian"]` (in-place).

### 5.21 Schedule-aware `EMAOperator` (P1)
- **Protocol surface extended:** new `merge(... schedule_sample=...)` kwarg on `MergeOperatorProtocol` (additive).
- **New implementation:** `EMAOperator` extended to consume `schedule_sample`.
- **Registration point:** `MERGE_OPERATOR_REGISTRY["ema"]` (in-place upgrade).

### 5.22 Joint OT blender (P1)
- **Protocol surface extended:** none.
- **New implementation:** `JointOTLinearBlender` in `blender_extra.py`.
- **Registration point:** `BLENDER_REGISTRY["joint_ot_linear"]`.

### 5.23 Barycentric blender (P1)
- **Protocol surface extended:** none.
- **New implementation:** `BarycentricBlender` in `blender_extra.py`.
- **Registration point:** `BLENDER_REGISTRY["barycentric"]`.

### 5.24 Parallel `LedgerChain` append (P1)
- **Protocol surface extended:** `LedgerChain.append_async(row)` returns a `Future` or generator.
- **New implementation:** `ParallelLedgerChain` in `frame/ledger_chain.py`.
- **Test strategy:** concurrent appends validate to same head hash as sequential.

### 5.25 Soft mode on `LayeredMetricPanel` (P1)
- **Protocol surface extended:** constructor kwarg `strict: bool = True`.
- **New implementation:** in-place upgrade.
- **Test strategy:** zero false-positive failures on tier-violation path.

### 5.26 CUSUM / Bayesian change-point detector (P1)
- **Protocol surface extended:** none.
- **New implementation:** `CUSUMOscillationDetector`, `BayesianChangePointDetector` in `eval/protocol.py`.
- **Test strategy:** detection latency ↓ 50 % on synthetic oscillating trajectory.

### 5.27 Cross-channel interaction (P1)
- **Protocol surface extended:** new helper `evidence_cross_channel(factor_a, factor_b, ...) -> evidence_score`.
- **New implementation:** in `frame/channel_rule.py`.
- **Test strategy:** audit_codes emitted for cross-channel interactions on multi-channel inputs.

---

## STEP 6 — Quantitative benchmark plan

For each P0/P1, the BEFORE / AFTER metric, baseline, target, and
benchmark script.

| Uplift | Baseline (BEFORE / Round-1) | Target (After Round-2) | Benchmark script |
|---|---|---|---|
| Adaptive σ_max on EDM | σ_max constant (R1 EDM) | σ_max variance per round ↓ 30 % | `tools/bench/scheduler_edm_adaptive_sigma.py` |
| Multi-metric PID | R1 AdaptivePID | oscillation amplitude ↓ 50 % | `tools/bench/scheduler_pid_multimetric.py` |
| Rademacher W2 | R1 projection_free CV 0.00206 | CV ≤ 0.0018 at n=128 | `tools/bench/w2_rademacher_cv.py` |
| Tree-Sliced W2 | R1 linear-sliced | bias ↓ 30 % on anisotropic Gaussians | `tools/bench/w2_tree_sliced_bias.py` |
| DPM-Solver++ | R1 DPM order-1 (L2=0.023 at NFE=20) | L2 ≤ 0.05 at NFE=10 | `tools/bench/dpm_pp_endpoint_distance.py` |
| UniPC order-3 | R1 UniPC order-1 (L2=1.97e-4 at NFE=20) | L2 ≤ 0.02 at NFE=10 | `tools/bench/unipc_order3_endpoint_distance.py` |
| SDE integrators | R1 deterministic only | symplectic preserves Hamiltonian energy within 1e-6 | `tools/bench/sde_integrator_symplectic.py` |
| Real Parallel/Early/Online runners | R1 dict-stub | wall-clock ↓ ≥ 2× on 4-core | `tools/bench/runner_real_wallclock.py` |
| Stochastic FM adapter | R1 deterministic adapter only | W2 ↓ 25 % on stochastic targets | `tools/bench/stochastic_fm_w2.py` |
| Stage Protocol | R1 monolithic orchestrator | 4 stages unit-testable independently | `tools/bench/stage_pipeline_reorder.py` |
| KDE-support-coverage | R1 weighted 0.1916 (FAIL) | stress-config ≥ 0.22 | `tools/bench/coverage_kde_support.py` |
| Differential-entropy top-k coverage | R1 binary top-k | entropy estimate CV ≤ 0.1 at n=256 | `tools/bench/coverage_entropy_topk.py` |
| W2 barycenter coverage | R1 single-point W2 | barycenter distance ≤ oracle W2 | `tools/bench/coverage_w2_barycenter.py` |
| DOPRI5 adaptive step loop | R1 single-step only | endpoint L2 ↓ 50 % at fixed budget | `tools/bench/dopri5_endpoint_distance.py` |
| Multi-source Kalman merge | R1 single-source Kalman | posterior W2 reduction ↑ to 30 % | `tools/bench/merge_multi_source_kalman.py` |
| Handoff sequential scheduler | R1 SequentialScheduler (no handoff) | n_cap transition smoothness ↑ | `tools/bench/scheduler_handoff_smoothness.py` |
| Adaptive σ_max + EDM2 preconditioner | R1 EDM only | step-count ↓ further 30 % | `tools/bench/edm2_preconditioner.py` |
| Anisotropic Gaussian target | R1 isotropic only | coverage separation ↑ 30 % | `tools/bench/target_anisotropic_coverage.py` |
| Multi-channel jittered scheduler | R1 single-channel | per-channel β variance ↓ 40 % | `tools/bench/scheduler_multichannel_jitter.py` |
| Per-channel constant policy | R1 single-channel | ≥ 2 channels independently | `tools/bench/policy_multichannel.py` |
| Dual-target adaptive policy | R1 single-target | per-round β variance ↓ 30 % | `tools/bench/policy_dual_target.py` |
| Time-varying Bayesian effective_count | R1 constant effective_count | selection_ratio convergence ↑ | `tools/bench/merge_bayesian_time_varying.py` |
| Schedule-aware EMA merge | R1 constant α | schedule-aware blending | `tools/bench/merge_ema_schedule.py` |
| Joint OT blender | R1 per-coordinate 1-D OT | joint-OT distance ↓ on correlated channels | `tools/bench/blender_joint_ot.py` |
| Barycentric blender | R1 OT path | OT-path distance observable | `tools/bench/blender_barycentric.py` |
| Parallel LedgerChain | R1 sequential chain | concurrent appends validate to same head hash | `tools/bench/ledger_chain_parallel.py` |
| Soft mode LayeredMetricPanel | R1 hard-fail | zero false-positive failures | `tools/bench/metric_panel_soft.py` |
| CUSUM change-point detector | R1 threshold-based | detection latency ↓ 50 % | `tools/bench/cusum_detection_latency.py` |
| Cross-channel interaction | R1 single-channel | audit_codes for cross-channel interactions | `tools/bench/channel_cross_interaction.py` |

**Quantitative targets summary:**

* **Framework-internal:** adaptive σ_max ↓ 30 % variance; multi-metric PID ↓ 50 % oscillation; KDE-support-coverage stress ≥ 0.22 (fixes R1 miss); barycenter coverage on par with W2.
* **Framework-external:** DPM-Solver++ at NFE=10 ≤ 0.05 L2; UniPC-3 at NFE=10 ≤ 0.02 L2; stochastic FM W2 ↓ 25 %; symplectic SDE preserves Hamiltonian within 1e-6.
* **Wall-clock:** ParallelRunner / EarlyStopRunner / OnlineRunner wall-clock ↓ ≥ 2× on multi-core.
* **Pluggability:** new registries `W2_REGISTRY` 4 → 7; `INTEGRATOR_REGISTRY` 6 → 12; `SCHEDULER_REGISTRY` 11 → 16; `MERGE_OPERATOR_REGISTRY` 7 → 8; `POLICY_DRIVER_REGISTRY` 3 → 5; `BLENDER_REGISTRY` 4 → 6; `RUNNER_REGISTRY` 5 (wired); `STAGE_REGISTRY` 0 → 4; `COVERAGE_REGISTRY` (new) 0 → 3; `ADAPTER_REGISTRY` (new) → +1 stochastic FM.

---

## Sources — Round-2 external papers cited

* [Stochastic Flow Matching — arXiv:2410.19814](https://arxiv.org/abs/2410.19814)
* [Neural Stochastic Flows — arXiv:2510.25769](https://arxivlens.com/PaperView/Details/neural-stochastic-flows-solver-free-modelling-and-inference-for-sde-solutions-7738-55dafcef) (NeurIPS 2025 poster)
* [Bayesian Flow Networks unified with diffusion SDEs — arXiv:2404.15766](https://ui.adsabs.harvard.edu/abs/2024arXiv240415766X/abstract) (ICML 2024)
* [Flow Matching: Markov Kernels, Stochastic Processes and Transport Plans — arXiv:2501.16839](https://arxiv.org/abs/2501.16839)
* [Generalized Flow Matching for Transition Dynamics — arXiv:2410.15128](https://scirate.com/arxiv/2410.15128)
* [CFO: Continuous-time PDE via flow-matched neural operators — arXiv:2512.05297](https://doi.org/10.48550/ARXIV.2512.05297)
* [Flow Matching Neural Processes — arXiv:2512.23853](https://ui.adsabs.harvard.edu/abs/2025arXiv251223853/abstract) (NeurIPS 2025)
* [Stochastic EDM preconditioner — arXiv:2409.06984](https://arxiv.org/abs/2409.06984)
* [EDM2 with preconditioner — arXiv:2410.17090](https://arxiv.org/abs/2410.17090)
* [Support Coverage via KDE — arXiv:2412.00849](https://arxiv.org/abs/2412.00849) (NeurIPS 2024 GenBench)
* [Wasserstein-2 Barycenters survey — arXiv:2509.06580](https://arxiv.org/abs/2509.06580)
* [Tree-Sliced Wasserstein with Nonlinear Projection — arXiv:2505.00968](https://arxiv.org/pdf/2505.00968v1) (ICML 2025)
* [Efficient Sliced W2 via Adaptive Bayesian Optimization — arXiv:2509.17405](https://adsabs.harvard.edu/abs/2025arXiv250917405A/abstract)
* [Differentiable Generalized Sliced Wasserstein Plans — NeurIPS 2025 (Chapel et al.)](https://mlanthology.org/neurips/2025/chapel2025neurips-differentiable)
* [Slicing Wasserstein Over Wasserstein via Functional OT — arXiv:2509.22138](http://arxiv-export-lb.library.cornell.edu/abs/2509.22138)
* [Differential Entropy Survey — arXiv:2406.19432](https://arxiv.org/html/2406.19432v1)
* [Unifying Information-theoretic Perspective on Evaluating Generative Models — arXiv:2412.14340](https://adsabs.harvard.edu/abs/2024arXiv241214340F)

**Round-2 distinct external paper IDs cited: 17.** Combined with the
Round-1 30 entries, the framework references **~47 unique external
SOTA works**.

---

## 6-line summary (Round-2)

- Total algorithms inventoried (Round-2 lens): **~165** classes / protocols / helpers across `algorithm/`, `eval/`, `frame/`, `contracts/`, `universal/`, `molecular/`, `policy/`, `adapters/`, `tools/` (12 scheduler families, 3 policy drivers, 7 merge operators, 4 blenders, 5 runner-registry families, 6 ODE integrators, 4 W2 estimators, 2 rotation policies, 3 mixers, ledger chain, bounded-Lipschitz, plus supporting dataclasses).
- Round-2 priority counts: **P0 = 10** (qualitative framework uplift), **P1 = 19** (clear measurable improvement), **P2 = 11** (nice to have).
- Biggest expected framework-INTERNAL effect: **adaptive σ_max on EDM + multi-metric PID + KDE-support-coverage + barycenter coverage** together deliver σ_max variance ↓ 30 %, PID oscillation ↓ 50 %, weighted coverage stress-config ≥ 0.22 (fixes the R1 0.1916 miss), and barycenter distance oracle-parity — qualitatively stronger scheduling, more discriminating coverage.
- Biggest expected framework-EXTERNAL effect: **DPM-Solver++ / UniPC-3 / SDE integrators** (≥ 2× step-count reduction vs R1 DPM order-1; L2 ≤ 0.02 at NFE=10 with UniPC-3) driving the FM adapter, plus **Rademacher + Tree-Sliced W2** estimators ([arXiv:2505.00968](https://arxiv.org/pdf/2505.00968v1)) cutting estimator CV by another 10-30 %, and **stochastic FM adapter** ([arXiv:2410.19814](https://arxiv.org/abs/2410.19814)) giving W2 ↓ 25 % on stochastic targets.
- Plug-in design extensions: **~15** Protocol-extension points (10 P0 + 5 P1 inline) across 6 new + 6 extended registries (`W2_REGISTRY` 4→7, `INTEGRATOR_REGISTRY` 6→12, `SCHEDULER_REGISTRY` 11→16, `MERGE_OPERATOR_REGISTRY` 7→8, `POLICY_DRIVER_REGISTRY` 3→5, `BLENDER_REGISTRY` 4→6, plus new `STAGE_REGISTRY` 0→4, `COVERAGE_REGISTRY` 0→3, `ADAPTER_REGISTRY` +1).
- External papers cited (Round-2): **17 distinct arXiv / NeurIPS / NeurIPS-W entries** (SDE solvers ×9, OT/W2 estimators ×6, differential entropy ×1, differentiable SW ×1); combined with Round-1's 30, **~47 unique SOTA works** underpin the framework.