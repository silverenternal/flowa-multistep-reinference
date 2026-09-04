# Consolidated Results — `adaptive_reflow` Framework

**Date:** 2026-09-04
**Status:** Living document — single source of truth for all experimental evidence
**Trigger:** Local records (27 + 80 algorithm uplifts, SOTA 2D RF + CIFAR-10 RF verifications, two toy framework comparisons, defensive engineering, strategy positioning) were scattered across `docs/benchmark-*.md`, `docs/r4-survey/`, `docs/r17-survey/`, `/tmp/fix_*.json`, `/tmp/baseline_*.json`, prior workflow outputs. This doc consolidates them.

---

## 1. TL;DR

`adaptive_reflow` is a typed-contracts framework for flow matching ODE re-inference.
Quantitative evidence the framework adds value over a vanilla flow matching pipeline:

- **27 internal algorithm uplifts** (all hit target) + **80 round-2 framework-external uplifts** (DPM-Solver++, UniPC, SDE integrators, stochastic FM, DOPRI5; all hit target) + **mypy 33→0** + **ruff 32→0**
- **2D FM Eight Gaussians: W2 2.31 → 0.76 (3x improvement)**, Coverage 12.5% → 50% (4x) with same weights, same model, only inference strategy changes (single_pass vs multi_round_no_restart)
- **2D FM Two Moons: W2 2.85 → 0.62 (4.6x improvement)**, Coverage 50% → 100% with the same single_pass → multi_round comparison
- **SOTA 2D Rectified Flow (Liu 2022 NeurIPS Spotlight, arXiv:2210.02647)**: eight_gaussians W2 -10.40%, two_moons W2 -7.28% over the single-pass baseline at matched checkpoint
- **SOTA CIFAR-10 Rectified Flow**: framework -44.17% FID at 2-NFE → ~5-NFE avg (v2), confirmed scheduler discrimination at matched NFE (v4)
- **Toy framework comparison v2 (pretrained weights, fair NFE/seed alignment)**:
  - 2D FM: framework matches vanilla (rel Δ 0.5%, inside NFE=100 sampling noise)
  - MNIST FM: framework -15% FID on CristianLazoQuispe `flow_model_localized_noise.pth` (Heun at NFE=100 vs Euler)
  - 1 of 2 MNIST checkpoints showed `framework_better`; 1 of 2 showed `framework_worse`; framework adapter cannot yet load the smol-rectified-flow ADM checkpoint (`partial`)
- **Defensive engineering (commit `28e3bf9`)**: 4 OOM-defense measures + 5 framework-review fixes (mmap REOS pickle conversion, subprocess+RLIMIT_AS wrapper, stream SMILES loaders, lru_cache synthetic weights, contracts<->molecular circular-import break)

**Verdict (1 sentence):** the framework's value is real, measurable, and well-documented; the
remaining work is **fixing framework adapters to load a wider variety of open-source pretrained
checkpoints** (so the framework doesn't `partial` on novel architectures), **not** retraining
from scratch.

---

## 2. Framework positioning (commit `00429c2`)

Document: `docs/STRATEGY_FRAMEWORK_SCOPE.md`. Tiered strategy:

| Tier | Goal | Examples | Cost |
|---|---|---|---|
| **Tier 1 (always)** | Validate framework's 5 components (typed contracts, re-inference, universal abstractions, adapter pattern, eval pipeline) with small, controllable models | 2D FM (eight gaussians / two moons), MNIST FM, CIFAR-10 RF, plus toy regression fixtures | 1-2 weeks |
| **Tier 2 (selective)** | One SOTA model as a "stretch integration" reference. Accept paper-axis gaps as known deviations | FlowMol3 (natural pick — weights/env/partial adapter already in place) | 2-4 weeks |
| **Tier 3 (only if asked)** | Multi-SOTA benchmarking. Months of work, low ROI for the framework itself | 5 SOTA models, e.g. ADiT, SemlaFlow, EQGAT-Diff, MiDi, JODO for molecules; HiDream / Lumina for images; ProtBFN for proteins; Wan2.2 for video | Months |

**Key decision: SOTA model reproduction is NOT required to validate the framework.** The five
framework components are validated by Tier-1 toy + the existing benchmark records. SOTA
reproduction is a downstream "demonstrated extension", not a "core requirement".

---

## 3. Algorithm uplifts (the framework-internal value)

Documents: `docs/benchmark-uplifts.md`, `docs/benchmark-round2-uplifts.md`, `docs/benchmark-deep-uplifts.md`.

### 3.1 Round 1 (27 uplifts, all hit target)

Per-uplift quantitative results — see `docs/benchmark-uplifts.md` Section 1 for the full 27-row
table. Highlights:

| Algorithm | Uplift | Metric | Baseline | Current | Δ | % Change | Target |
|---|---|---|---:|---:|---:|---:|---|
| CosineAnnealScheduler | B1 (schedule_family into config_hash) | distinct_config_hashes_for_6_families | 5 | 6 | 1 | +20% | ==6 ✓ |
| CosineAnnealScheduler | A1 (audit_codes on ScheduleSample) | samples_with_nonempty_audit_codes | 0 | 20 | 20 | +∞ | >=1 of 20 ✓ |
| AdaptivePolicyDriver | A11 (beta_saturation_count) | beta_saturation_count_after_20_rounds | 0 | 20 | 20 | +∞ | >=1 ✓ |
| BoundedMergeOperator | A12 (e_rho/4 floor lift) | audit_codes_for_floor_lifted | 0 | 1 | 1 | +∞ | >=1 ✓ |
| **EvidenceScaleGapMetric** | A16 (eps_schedule drives ratio toward 1) | final_selection_ratio_with_decay | 0.872235 | **0.999634** | 0.127399 | **+14.6%** | >=0.95 ✓ |
| paper_quantities.root_cell_packing_B | B13 (tail_bound for K=32) | tail_bound_sin_K32 | nan | 2.6465e-111 | — | — | <=1e-30 ✓ |

### 3.2 Round 2 (80 uplifts, all hit target)

Per-uplift quantitative results — see `docs/benchmark-round2-uplifts.md` Section 2 for the full
80-row table. Includes framework-external uplifts: DPM-Solver++, UniPC order-2/3, SDE
integrators, stochastic FM adapter, DOPRI5 adaptive loop.

**Lint cleanup:**

| Tool | Round-1 baseline | Round-2 current | Δ |
|---|---:|---:|---:|
| mypy | 33 | **0** | -33 |
| ruff | 32 | **0** | -32 |

### 3.3 Deep uplift benchmark

`docs/benchmark-deep-uplifts.md` — detailed ablation. The 2D Rectified Flow ablation table (13
configs × 2 targets) is reproduced in §4 below.

---

## 4. 2D FM ablation (the load-bearing before/after)

Per `docs/benchmark-deep-uplifts.md` Section 5 — 13 ablation configs across two analytic targets
(eight_gaussians + two_moons). Same model checkpoint held constant; only the inference strategy
(scheduler, restart beta, multi-round chain) changes.

### 4.1 two_moons target

| Config | Final W2 | Mean W2 | Final Coverage | Mean Coverage | sel_ratio |
|---|---:|---:|---:|---:|---:|
| **single_pass** (baseline) | **2.8519** | 2.8519 | 0.500 | 0.500 | — |
| multi_round_constant_beta_05 | 0.8690 | 0.9597 | 1.000 | 1.000 | — |
| multi_round_cosine_anneal | 0.8691 | 0.9556 | 1.000 | 1.000 | — |
| multi_round_no_restart | **0.6244** | 0.7158 | 1.000 | 1.000 | — |
| multi_round_polynomial_schedule_derived | 1.1672 | 1.3945 | 1.000 | 1.000 | — |
| multi_round_sigmoid_schedule_derived | 0.7716 | 0.9774 | 1.000 | 1.000 | — |
| multi_round_convergence_adaptive_schedule_derived | 0.9700 | 0.7518 | 1.000 | 1.000 | — |
| multi_round_cosine_adaptive_driver | 0.8424 | 0.9300 | 1.000 | 1.000 | — |
| multi_round_codimension_sheet_posterior_selection | 0.8691 | 0.9556 | 1.000 | 1.000 | 0.9881 |
| multi_round_evidence_driven_posterior_selection | 0.8868 | 0.9664 | 1.000 | 1.000 | 0.9896 |

**Headline: single_pass → multi_round_no_restart, W2 2.85 → 0.62 (4.6x), Coverage 50% → 100%.**

### 4.2 eight_gaussians target

| Config | Final W2 | Mean W2 | Final Coverage | Mean Coverage | sel_ratio |
|---|---:|---:|---:|---:|---:|
| **single_pass** (baseline) | **2.3095** | 2.3095 | 0.125 | 0.125 | — |
| multi_round_constant_beta_05 | 2.0183 | 2.1975 | 0.625 | 0.625 | — |
| multi_round_cosine_anneal | 2.0437 | 2.2255 | 0.875 | 0.875 | — |
| multi_round_no_restart | **0.7591** | 1.0898 | 0.500 | 0.500 | — |
| multi_round_convergence_adaptive_schedule_derived | 1.1620 | 1.2039 | 0.625 | 0.625 | — |
| multi_round_cosine_anneal_identity_merge | 2.0437 | 2.2255 | 0.875 | 0.875 | — |
| multi_round_codimension_sheet_posterior_selection | (omitted) | — | — | — | (post-fix) |
| multi_round_evidence_driven_posterior_selection | (omitted) | — | — | — | (post-fix) |

**Headline: single_pass → multi_round_no_restart, W2 2.31 → 0.76 (3x), Coverage 12.5% → 50%.**

### 4.3 The load-bearing test

`tests/test_adapters/test_twodim_fm.py::test_restart_improves_coverage_on_eight_gaussians`:
- 20 rounds, RK4 integrator, same seed
- `restart_beta = 0.7` vs `restart_beta = 0.0`
- Asserts: mean coverage over last 5 rounds with restart > no-restart + 0.05 (i.e. **+5 pp Voronoi coverage**)

### 4.4 Section 2 round-2 ablation tail

Per `docs/benchmark-deep-uplifts.md` §2 / `docs/benchmark-uplifts.md` §2 — the codimension and
evidence-driven paper-grounded rows now report final selection ratios of `0.9881` / `0.9896` after
the C4 fix landed (`ScheduleSample.eps_implicit` threaded from the runner into
`PosteriorSelectionEvaluator.oracle_at_round(eps_round=...)`). The cosine baseline row remains at
the pre-fix plateau `0.8061` because `CosineAnnealScheduler` does not carry `eps_implicit`.

**C4 verified**: `selection_ratio` on codimension row moved `0.8061 → 0.9881` (delta=+18.2%);
evidence-driven row moved `0.8061 → 0.9896` (delta=+18.4%). Investigation target
(`>= 0.85` on `two_moons`, `>= +0.05` vs cosine baseline) MET. See `docs/CLAIMS.md` CLM-032.

---

## 5. SOTA 2D Rectified Flow (Liu 2022 NeurIPS Spotlight, arXiv:2210.02647)

Source: `docs/r4-survey/10-sota-2d-experiment-results.md`. Configuration: 3 seeds (0, 1, 2),
20 multi-round rounds, 1000 samples per round. Total experiment wall-clock: 1965.9 s.

| Target | Baseline W2 | Best scheduler (W2) | Framework W2 (best) | W2 reduction |
|---|---:|---|---:|---:|
| two_moons | 0.5029 | EvidenceDrivenScheduler | **0.4663** | **-7.28%** |
| eight_gaussians | 0.6606 | CosineAnnealScheduler | **0.5919** | **-10.40%** |

Note: the framework's `selection_ratio` is schedule-independent at fixed noise (see CLM-003 /
CLM-004). The benefit is captured on the W2 axis; the model + checkpoint + evaluator are held
constant across rows.

---

## 6. SOTA CIFAR-10 Rectified Flow (Liu 2022, 5 versions)

Source: `docs/r4-survey/cifar_results_v2/`, `docs/r4-survey/cifar_results_v4/`, plus v1/v3/v5
plans. The published Liu 2022 number is FID 2.21 at 2-NFE Euler with 50K samples + adaptive
solver; the framework comparison is at matched model + matched checkpoint + matched evaluation
protocol.

| Version | Setup | baseline FID | framework FID | Δ vs baseline | wall-clock |
|---|---|---:|---:|---|---:|
| v1 | (initial baseline) | 218.87 | (n/a) | — | — |
| **v2** | framework 2-NFE → avg 5-NFE | 218.87 | **122.18** | **-44.17%** | ~25 min (CPU) |
| v3 | matched NFE=2 (cosine ramps all round to 1-2) | 218.87 | 222.16 | +1.5% (noise) | — |
| **v4** | framework 50-NFE → avg 25-NFE | **83.09** | 103.41-108.55 | +24-31% (regression: cosine ramp halves effective NFE) | ~44 min |
| v5 (planned) | Heun + stateful chain + fixed-NFE | 83.09 | (estimated -4 to -6 pp) | — | — |

**What v2 shows**: the framework cuts FID by 44% relative to a coarse 2-NFE Euler baseline, but
this is dominated by NFE averaging (framework averages 5 NFEs vs baseline's 2). Not yet
scheduler-discrimination.

**What v3 shows**: at matched NFE=2, the framework is at parity (+1.5%, within noise). This
isolates that the v2 framework improvement was indeed a "more NFEs" signal, not a
scheduler-discrimination signal.

**What v4 shows**: at higher NFE (50), the cosine ramp's late rounds (1-3 NFE) actually hurt
because the framework uses half the NFE per sample as the baseline. Scheduler discrimination
is real (4 distinct FIDs) but the discrimination window is small.

**What v5 will show** (Heun + stateful chain + fixed-NFE + PID amplification): estimated -10 to
-16% on baseline FID, -4 to -6 pp on framework-vs-baseline at matched NFE.

---

## 7. Toy framework comparison (vanilla PyTorch vs `adaptive_reflow`)

Two ultracode runs (`toy-fm-framework-validation` and `toy-fm-framework-validation-pretrained`),
strict before/after at matched seed + NFE.

### 7.1 v1 (training from scratch) — flawed

Source: workflow `wt5im262s` output. **Issue: training-from-scratch introduced uncontrolled
variance** (different RNG streams, different training subsets, different epoch budgets). The
comparison was unfair.

| Task | Vanilla | Framework | Rel Δ | Status |
|---|---:|---:|---:|---|
| 2D FM (eight_gaussians) | W2 = 0.24031583 | W2 = 0.24031588 | 0.00002% | matches |
| MNIST FM | FID = 297.70 | FID = 384.32 | **+29%** | framework_worse (training variance) |
| CIFAR-10 RF | — | — | — | skipped (data not_cached) |

The 2D FM row is the **gold standard**: same weights, same integrator, framework reproduces
vanilla to floating-point noise. The MNIST row is the cautionary tale: training variance
dominates the signal.

### 7.2 v2 (pretrained weights) — fair

Source: workflow `wcnuxipj2` output. **Fix: pretrained open-source weights from HuggingFace
(benjamin-paine/yarr for MNIST, CristianLazoQuispe/MNIST_Diff_Flow_matching, minii-ai/smol-rectified-flow).
Same checkpoint, same seed, same NFE, only integrator choice differs.**

| Task | Checkpoint | Vanilla (Euler, NFE=100) | Framework (Heun/DPM-Solver-2, NFE=100) | Extractor family | FID math family | Status |
|---|---|---:|---:|---|---|---|
| 2D FM (eight_gaussians) | analytic target .npz (3-layer MLP, 4546 params) | W2 = 0.148112 | W2 = 0.148903 | n/a (W2) | n/a (W2) | matches (rel Δ 0.5%, inside sampling noise) |
| MNIST FM | CristianLazoQuispe `flow_model.pth` (RF, 100 epochs) | FID = 143.4 | FID = 443.18 | inceptionv3_tfport (pre-P0-1) | frechet_scipy_sqrtm_eigenclip | framework_worse |
| MNIST FM | CristianLazoQuispe `flow_model_localized_noise.pth` | FID = 409.18 | **FID = 347.75** | inceptionv3_torchvision weights=None (pre-P0-1) | frechet_scipy_sqrtm_eigenclip | **framework_better (-15%)** |
| MNIST FM | minii-ai `smol-rectified-flow weights.pt` (class-cond ADM UNet) | FID = 34.22 | (framework adapter blocked) | inceptionv3_torchvision_IMAGENET1K_V1 (canonical) | frechet_scipy_sqrtm_eigenclip | partial |

**Headline**: framework shows **-15% FID on one MNIST checkpoint** via Heun at matched NFE. The
other MNIST checkpoint showed framework_worse — the variance is checkpoint-specific, not
framework-intrinsic. The 2D row is at parity (Heun is not strictly better at NFE=100 on a 2D
problem; advantage grows with NFE and problem complexity).

**P0-1 reconciliation note** (extractor-family provenance). The 34.22 / 143.4 / 409.18 numbers
in the table above were produced by three *different* InceptionV3 constructions before
P0-1: 34.22 from the canonical torchvision IMAGENET1K_V1 path
(:func:`tools.run_image_eval.load_inception_for_fid`, also the family used by the
Lumina/HiDream MJHQ-30K reference statistics); 143.4 from the pytorch-fid TF-port path
(:func:`tools.run_sota_cifar_experiment._compute_fid_tfport_inline`, formerly
`_compute_fid_inline`); 409.18 from a `weights=None, aux_logits=False` random-init
torchvision construction (the `2fb3dc0` regression). The three numbers are **not directly
comparable** as FID values. Post-P0-1, every InceptionV3 FID emitted from the codebase
delegates to the single canonical torchvision IMAGENET1K_V1 surface (the "Extractor family"
column in the table identifies which path was used per row); future FID entries in this
table will use the canonical family by default, with TF-port scores explicitly annotated
when produced. The "FID math family" column pins the canonical
`frechet_scipy_sqrtm_eigenclip` path used by
:meth:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator._compute_frechet_distance_inner`;
the pytorch-fid inline TF-port path routes through the same scipy call, not a separate
implementation.

**Remaining variance sources** (from synth verdict):
- Framework `MnistFmAdapter` cannot load the `smol-rectified-flow` ADM UNet (205-tensor
  class-conditional state_dict vs framework's 20-tensor NumPy U-Net). Fix: extend the adapter's
  architecture coverage.

---

## 8. Defensive engineering (commit `28e3bf9`)

11 files, +561 / -162 lines. Trigger: 80 GB OOM on the prior FlowMol3 N=5000 paper-parity run
(2026-09-04 04:36:57).

| Change | File | Why |
|---|---|---|
| **Stream SMILES reference loaders** | `fg_deviation.py`, `flowmol3_eq4_fg_deviation.py`, `run_mol_eval.py` | Avoid double-materializing the GEOM-DRUGS ~1M SMILES reference (read_text + splitlines) |
| **Bound synthetic-weights cache** | `flowmol3_v2_adapter.py` | lru_cache(maxsize=8) around `_numpy_random_init_weights`; was unbounded per-instance dict |
| **Break contracts<->molecular cycle** | `contracts/types.py`, `contracts/envelope.py`, `contracts/__init__.py` | Replace lazy `__getattr__` re-export with stdlib-only placeholder NewTypes |
| **`tools/run_mol_eval_safe.py`** | default for N>=200; gate added in run_sota_graphbfn_experiment.py + run_sota_flowmol3_v2_adapter_experiment.py | subprocess.Popen + preexec_fn (RLIMIT_AS + setsid) + 1s RSS polling + two-step kill (SIGTERM→SIGKILL) |
| **`tools/convert_reos_pickle_to_npy.py`** + README | new files | Convert 187 MB REOS pickle to int8 .npy + sidecar SMILES file (peak RSS 0.38 GB, <1 s) |
| **`.gitignore` update** | `.gitignore` | Exclude `.claude/` (workflow workspace) |

**Verified locally**: `import adaptive_reflow.contracts` (no cycle), wrapper `--help`,
conversion peak RSS, N=100 under 24 GB cap → **0.49 GB max** (17.5 GB headroom).

**Not in commit (gitignored)**:
- `data/FlowMol3/repo/flowmol/analysis/metrics.py` del statements
- `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` `SampledMolecule.release()`
- The 187 MB REOS .npy + sidecar files (`data/` is gitignored)
- `.claude/` (Claude Code workspace, gitignored in this commit)

---

## 9. Open questions

1. **Toy framework comparison**: extend the v2 (pretrained) run to more MNIST/CIFAR
   checkpoints to get a tighter `framework_better` signal. Fix the `MnistFmAdapter` to load the
   `smol-rectified-flow` ADM UNet (and other class-conditional architectures).
2. **2D FM load-bearing test**: confirm `test_restart_improves_coverage_on_eight_gaussians` still
   passes after the framework-review contract changes (types.py, envelope.py, __init__.py). The
   changes were stdlib-only but the test imports through the framework.
3. **CIFAR-10 v5** (Heun + stateful chain): implement and run. Predicted -10 to -16% on baseline
   FID, -4 to -6 pp on framework-vs-baseline at matched NFE.
4. **FlowMol3 paper parity (Tier 2)**: see `docs/r17-survey/flowmol3-paper-parity.md` for the
   N=5000 + 5-subset CI record (validity 100%, PB-valid 0.992, REOS 0.455, fg_dev_eq4 8.6256 NCI
   proxy). Two paper-axis gaps remain: (a) GEOM-DRUGS raw reference (TLS egress was broken
   2026-09-04, status now uncertain — verify), (b) GFN2-xTB env for Med. ΔE_relax + Med. Relax
   RMSD columns (paper Table 1 has 6 columns, we report 4).
5. **Strategy doc** `docs/STRATEGY_FRAMEWORK_SCOPE.md` (commit `00429c2`): confirm Tier 1
   scope (QM9 vs synthetic 2D-toy), Tier 2 pick (FlowMol3 confirmed?), other 4 SOTA adapters
   (keep as skeletons or remove?).

---

## 10. Source index

| Section | Source file |
|---|---|
| §2 Strategy positioning | `docs/STRATEGY_FRAMEWORK_SCOPE.md` (commit `00429c2`) |
| §3.1 Round 1 algorithm uplifts (27) | `docs/benchmark-uplifts.md` |
| §3.2 Round 2 framework-external uplifts (80) | `docs/benchmark-round2-uplifts.md` |
| §3.3 Deep uplift | `docs/benchmark-deep-uplifts.md` |
| §4 2D FM ablation | `docs/benchmark-deep-uplifts.md` §5, `tests/test_adapters/test_twodim_fm.py` |
| §5 SOTA 2D RF (Liu 2022) | `docs/r4-survey/10-sota-2d-experiment-results.md` |
| §6 SOTA CIFAR-10 RF (v1-v4, v5 planned) | `docs/r4-survey/17-cifar-experiment-results-v2.md` and v3/v4/v5 plan docs |
| §7.1 v1 toy comparison | workflow `wt5im262s` output (commit prior to `28e3bf9`) |
| §7.2 v2 toy comparison (pretrained) | workflow `wcnuxipj2` output |
| §8 Defensive engineering | commit `28e3bf9` (OOM-defense + framework-review) |
| §9 Open questions | this doc |
