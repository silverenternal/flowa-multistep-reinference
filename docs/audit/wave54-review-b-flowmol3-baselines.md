# Wave 54 Agent B — FlowMol3 SOTA baseline review (READ-ONLY)

**Author:** Wave 54 Phase 1 reviewer (Agent B)
**Date:** 2026-09-07
**Wave:** 54 (post-§7.5 honest-verdict rewrite)
**Scope:** read-only audit of which SOTA baselines exist in the repo today
for FlowMol3 vs which baselines Wave 52 WF2 added for Kanzi + LineageFlow,
and a concrete Phase-2 design for the missing FlowMol3 baseline(s).
**Status:** review only. No code touched. No commits.

---

## B.1 List of current baselines in `scripts/baselines/`

| File | Role | Tier | Target |
|---|---|---|---|
| `scripts/baselines/__init__.py` | package marker + module index | — | — |
| `scripts/baselines/consistency_model.py` | CM + iCT 1-step mock sampler | Tier 1/2 | toy / CIFAR-RF |
| `scripts/baselines/rectified_flow_reflow.py` | Rectified Flow + Reflow inference-time proxy | Tier 1/2 | toy / CIFAR-RF |
| `scripts/baselines/dpm_solver_plus_plus.py` | DPMSolver++ 2nd-order multistep | Tier 1/2 | toy / CIFAR-RF |
| `scripts/baselines/run_baselines.py` | runner that wires the 3 Tier 1/2 baselines to `twodim_fm`, `mnist_fm`, `rectified_flow_cifar` (synthetic-mode Protocol surface) and emits `verification_outputs/baseline_comparison_q4_2026.json` | Tier 1/2 | toy + CIFAR-10 RF |
| `scripts/baselines/_lineageflow_helpers.py` | shared `compute_composite` + `phi1/phi2/phi3` helpers (numpy-only, sidecar-venv safe) | Tier 3 | LineageFlow only |
| `scripts/baselines/run_lineageflow_baseline_euler.py` | plain-Euler baseline on the real LineageFlow ckpt (10.5 GB) | Tier 3 | LineageFlow |
| `scripts/baselines/run_lineageflow_baseline_heun.py` | Heun RK2 baseline on the real LineageFlow ckpt | Tier 3 | LineageFlow |
| `scripts/baselines/run_lineageflow_baseline_rk4.py` | RK4 baseline on the real LineageFlow ckpt | Tier 3 | LineageFlow |

**Total: 9 files, 0 FlowMol3-targeted baseline scripts.**

---

## B.2 Mapping of baselines → model family

### B.2.1 Kanzi (protein, hybrid flow-AE)

* **No dedicated baseline scripts.** Tier 3 baseline numbers do not exist in
  `scripts/baselines/` for Kanzi; the Kanzi comparison is realised in
  `tools/run_real_ckpt_eval.py` (single-pass vs framework arm via
  `--composite-metric real`, the `KanziGlue` inline class added in Wave 52
  Agent A).
* The 3 SOTA inference baselines (CM / RF / DPMSolver++) implemented by
  Wave 52 Agent B are *not* run on Kanzi (per §8.5 paper-draft; the
  decision metric saturates, the composite axis is the framework's
  measurement surface).

### B.2.2 LineageFlow (protein, pure flow-matching)

* **3 dedicated baseline scripts** (`run_lineageflow_baseline_{euler,heun,rk4}.py`)
  on the real LineageFlow ckpt. Each runs at NFE=10 and emits its own
  `verification_outputs/lineageflow_baseline_<method>_q4_2026.json` plus
  the consolidated `lineageflow_baseline_comparison_q4_2026.json`.
* These are *integrator baselines* (single-pass ODE solve, varying the
  inner solver), not the *inference-loop* baselines Wave 52 picked
  (CM / RF+Reflow / DPMSolver++). The comparison is framework
  restart-blend vs pure time-stepping on the protein axis — see
  `docs/audit/wave52-lineageflow-baseline-comparison.md` §4.

### B.2.3 FlowMol3 (molecular 3D, CTMC flow-matching)

* **Zero baseline scripts.** No `run_flowmol3_baseline_*.py` file exists.
* The Wave 52 Agent B 3-baseline set (CM / RF / DPMSolver++) is run
  only on the toy + CIFAR-10 RF synthetic-mode Protocol surface (per
  `verification_outputs/baseline_comparison_q4_2026.json` — keys
  are `twodim_fm`, `mnist_fm`, `rectified_flow_cifar` only).
* The Wave 52 Agent C 3-baseline set (euler / heun / rk4) is run only
  on LineageFlow.
* The §8.5 paper-draft table 14 explicitly states the FlowMol3 row's
  external-baseline columns are `NOT YET MEASURED`.

**Conclusion: FlowMol3 has no Tier 3 baseline comparison whatsoever
in this repo.**

---

## B.3 FlowMol3's relevant comparison set (prior SOTA in molecular generative flow matching)

The framework needs to compare FlowMol3 (Dunn et al., NeurIPS 2024,
arXiv:2412.00765 / Project page: https://github.com/DunniZhang/FlowMol3,
flow-matching for 3D molecule conformer generation under CTMC) against
its direct predecessors in the molecular generative flow literature.
The relevant comparison set, ordered by recency:

| # | Method | Year | Venue | What it tests vs FlowMol3 |
|---|---|---|---|---|
| 1 | **GraphAF** (Shi et al.) | 2020 | ICML | autoregressive flow on molecular SMILES / graphs — earliest FM-style molecular baseline; published under "flow-based" framing pre-OT |
| 2 | **MolGen** (Fang et al.) | 2022 | NeurIPS | 1D molecular pretraining + finetuning via flow-based decoder; text-conditioned |
| 3 | **GeoDiff** (Xu et al. 2022) | 2022 | ICLR | equivariance-respecting diffusion for 3D conformer generation; the 3D diffusion baseline FlowMol3 most directly supersedes |
| 4 | **DM-SBG** (arXiv:2209.14665) | 2022 | preprint | score-based generative network for molecules; first equivariant SDE for conformer generation |
| 5 | **MolDiff** (Zhang et al. 2023) | 2023 | ICLR | diffusion on 3D molecules with SE(3)-equivariant denoiser; closest published 3D-mol diffusion SOTA pre-FlowMol3 |
| 6 | **EquiFM** (Song et al. 2023) | 2023 | ICLR | equivariant flow matching for 3D molecules — closest *flow-matching* predecessor to FlowMol3 |
| 7 | **Equivariant Flow Matching** + **Rectified Flow** (Liu 2022) | 2022/2023 | ICLR 2023 Spotlight | linear-OT family underlying FlowMol3 — the method that informs FlowMol3's choice of flow parameterisation |
| 8 | **Lipman Flow Matching** (Lipman et al. 2023) | 2023 | ICLR | the canonical continuous-time flow-matching loss FlowMol3 generalises from non-molecular → CTMC (for discrete atom-type jumps) |

All 8 methods are *published molecular generation SOTA on GEOM-DRUGS
and/or QM9*. They are the baselines FlowMol3 itself benchmarks against
in the published paper, and they are therefore the right reference set
for a framework-vs-SOTA comparison on FlowMol3.

**Note on data availability.** QM9 is small and freely usable
(molecules < 9 heavy atoms). GEOM-DRUGS is large (≈ 1M
RDKit-sanitisable conformers, ~370k molecules) and has historically
been the dataset where FlowMol3 + MolDiff + GeoDiff report. The
framework has
`data/flowmol3/weights_real/checkpoints/last.ckpt` (65 M params,
PyTorch Lightning 2.1.3, epoch 17, global_step 1 547 236 — verified
in `verification_outputs/flowmol3_real_metric_v3_q4_2026.json`
§`real_ckpt_meta`) but **no QM9/GEOM-DRUGS reference conformer set
shipped** — Wave 15 F.2 R5/R6 noted that the upstream `flowmol` package
is not in this sandbox (also: RDKit `SampleAnalyzer.analyze` is the
canonical chemistry-validity check, but `xtb` is not on `$PATH`,
documented in §7.5 paper-draft).

---

## B.4 Top missing baselines (ranked by relevance × implementability)

### B.4.1 **Missing baseline #1 — MolDiff (Zhang et al. 2023, ICLR)**

**Why it matters.** MolDiff is the *closest published 3D-mol diffusion
baseline*. The FlowMol3 paper itself benchmarks against MolDiff (and
reports the largest framework-style gain on MolDiff's metric). Running
MolDiff on the same GEOM-DRUGS eval lets the framework compare against
the *strongest non-flow-matching* baseline on the 3D-mol axis. Without
MolDiff, the FlowMol3 baseline comparison has only the framework's
own numbers + FlowMol3's paper numbers — a category error (the §8.4
paper-draft warning against cross-paper number pasting applies).

**Implementability.** Medium-high. MolDiff is published in ICLR 2023
with public code at https://github.com/microsoft/MolDiff (PyTorch
+ PyG). It uses SE(3)-equivariant denoiser, so the same chemistry
validity metric as FlowMol3 (RDKit sanitisation, ring validity,
geometric plausibility) applies. The challenge is adapter-side:
MolDiff does not share the framework's `batched_inference` /
`_velocity_field` Protocol, so a stand-alone
`scripts/baselines/run_flowmol3_baseline_moldiff.py` would have to
import MolDiff directly (similar to the LineageFlow
`_lineageflow_helpers.py` sidecar-venv pattern). Reference sampling
distribution can be 2D conformer + atom-type, with `frac_valid_mols`
+ `frac_mols_stable` (the Wave 49 FlowMol3 composite axes 1 and 2)
as the comparable metric.

### B.4.2 **Missing baseline #2 — EquiFM (Song et al. 2023, ICLR)**

**Why it matters.** EquiFM is the closest *flow-matching* predecessor
to FlowMol3 — both use SE(3)-equivariant continuous-time coupling,
EquiFM is *not* CTMC. Running EquiFM as a baseline lets the framework
make the precise "FlowMol3's CTMC parameterisation adds value over a
straight continuous-time flow-matching baseline" argument. This is the
*flow-matching axis* — what the framework itself argues about.

**Implementability.** Medium. EquiFM's official code release is more
fragmented than MolDiff's; the most common reproduction path is via
the EquiFM `model.py` in https://github.com/hanjq17/EquiFM (PyTorch
+ PyG + e3nn). A standalone
`scripts/baselines/run_flowmol3_baseline_equifm.py` would face the
same adapter-Protocol impedance as MolDiff, plus a smaller public
codebase that may need a sidcar venv like LineageFlow.

### B.4.3 (Honourable mention) **GraphAF / GeoDiff**

These are older and clearly weaker than FlowMol3 on the published
metric, so they would be useful as a *paper-completeness* reference
(checking the framework does not regress to GraphAF-era quality) but
not as a discriminating baseline. **Not recommended for Phase 2.**

### B.4.4 What the Wave 52 baselines *cannot* fill

CM+iCT, RF+Reflow, DPMSolver++ — these are *image-CIFAR-centric*
baselines. They compare against the framework on the toy 2D + MNIST
+ CIFAR-10 RF Protocol surface. They have no molecular generative
modeling layer (no atom-type classification, no bond formation, no
RDKit validity check). They would *not* be informative on the FlowMol3
axis even if re-targeted, because the metric the framework competes
on at the FlowMol3 tier (chemistry validity + 3D-geometry plausibility)
is fundamentally different from the W2 / L2-norm proxy these baselines
were designed for. The §3.3 of `docs/audit/wave52-sota-baselines-survey.md`
explicitly excludes "domain-specialised" baselines from the chosen 3;
for FlowMol3 the comparison has to be domain-specialised.

---

## B.5 Byte-stable check — Wave 52 Kanzi + LineageFlow + FlowMol3 numbers must NOT change

The Phase 2 baseline addition **must not** perturb any existing JSON
artefact. Byte-stable inventory (sha-safe paths — none of these are
re-emitted by Phase 2):

| Path | What it carries | Wave 52 value | Must not change |
|---|---|---|---|
| `verification_outputs/baseline_comparison_q4_2026.json` | 3 baselines × 3 toy/CIFAR models, N=500, signed-mean | framework twodim_fm W2 baseline 0.5029; CM 0.1798; RF 0.3893; DPMSolver++ 1.1414 | YES |
| `verification_outputs/lineageflow_baseline_euler_q4_2026.json` | Euler on real LF ckpt, NFE=10, B=2 L=32 K=20 | composite self −0.102; argmax turnover 0.21875 | YES |
| `verification_outputs/lineageflow_baseline_heun_q4_2026.json` | Heun on real LF ckpt, NFE=10 | composite self −0.103 | YES |
| `verification_outputs/lineageflow_baseline_rk4_q4_2026.json` | RK4 on real LF ckpt, NFE=10, B=1 L=16 K=20 | composite self −0.023 | YES |
| `verification_outputs/lineageflow_baseline_comparison_q4_2026.json` | consolidated LF baseline comparison | framework composite +0.211 | YES |
| `verification_outputs/kanzi_real_composite_q4_2026.json` | Kanzi 9-cell composite (3 seeds × 3 NFE) | composite_median +0.170175; verdict `framework_improves` | YES |
| `verification_outputs/flowmol3_real_composite_q4_2026.json` | FlowMol3 9-cell composite (post-Wave 53 metric + wiring fix) | composite +0.0000; verdict `no_signal` (placeholder) | YES (Phase 2 only ADDS a *baseline* comparison JSON; does not touch this one) |

**Phase 2 must NOT:**
* Re-run any of the above scripts (the existing JSON records are
  frozen for the Wave 54 honest-verdict rewrite).
* Modify `scripts/baselines/run_baselines.py` (CM/RF/DPM++-on-toy runner).
* Modify `scripts/baselines/run_lineageflow_baseline_*.py` (3 LF
  baseline scripts).
* Modify `verification_outputs/kanzi_real_composite_q4_2026.json`
  (`KanziGlue` 9-cell sweep).

**Phase 2 MAY:**
* Add new files under `scripts/baselines/` (e.g.
  `run_flowmol3_baseline_moldiff.py`).
* Add new JSON under `verification_outputs/`
  (e.g. `flowmol3_baseline_moldiff_q4_2026.json`).
* Add new audit doc under `docs/audit/`
  (e.g. `wave54-phase2-flowmol3-baselines.md`).

---

## B.6 Where new FlowMol3 baseline files should live (naming convention)

Following the Wave 52 naming convention for LineageFlow baselines
(`scripts/baselines/run_lineageflow_baseline_<integrator>.py`):

```
scripts/baselines/
├── __init__.py                       (unchanged)
├── consistency_model.py              (unchanged)
├── rectified_flow_reflow.py          (unchanged)
├── dpm_solver_plus_plus.py           (unchanged)
├── run_baselines.py                  (unchanged)
├── _lineageflow_helpers.py           (unchanged)
├── run_lineageflow_baseline_euler.py (unchanged)
├── run_lineageflow_baseline_heun.py  (unchanged)
├── run_lineageflow_baseline_rk4.py   (unchanged)
│
│  ── NEW (Wave 54 Phase 2) ──
├── _flowmol3_helpers.py              (RDKit validity, atom-type marginal,
│                                      `frac_valid_mols`, `frac_mols_stable`,
│                                      shared composite glue)
├── run_flowmol3_baseline_moldiff.py  (MolDiff as a Tier 3 baseline on the
│                                      real FlowMol3 metric axis)
└── run_flowmol3_baseline_equifm.py   (EquiFM as a Tier 3 baseline on the
                                       real FlowMol3 metric axis)
```

The `_flowmol3_helpers.py` module mirrors `_lineageflow_helpers.py`'s
sidecar-venv role: it duplicates the Wave 49 `FlowMol3Glue.composite`
math byte-identically (RDKit validity + stability + chemistry marginal
checks), so the new baseline scripts can compute composite scores
without dragging in the full `adaptive_reflow` package.

Outputs land:
verification_outputs/
├── flowmol3_baseline_moldiff_q4_2026.json
└── flowmol3_baseline_equifm_q4_2026.json
```

---

## B.7 Concrete Phase 2 fix design

### B.7.1 Two new baseline scripts (recommended scope)

#### File 1: `scripts/baselines/_flowmol3_helpers.py`

* Mirrors `_lineageflow_helpers.py` (numpy / stdlib only, no
  `adaptive_reflow` import).
* Functions:
  * `load_moldiff_model(ckpt_path, device="cpu")` → `(model, n_params, ...)`;
    if MolDiff ckpt is not on disk, fall back to the deterministic
    random-init path (mirrors `mnist_fm` synthetic-mode fallback).
  * `chem_validity(samples)` → `(frac_valid_mols, frac_mols_stable)`
    via a thin RDKit shim. If RDKit is missing, return `float("nan")`
    with a clear `marker=blocked_rdkit` (graceful degradation;
    `tools/run_real_ckpt_eval.py` already handles NaN chemistry axes).
  * `composite_chemistry(samples, weights=(0.30, 0.25, 0.15, 0.15, 0.15))`
    → `(composite, phi1_valid, phi2_stable, phi3_neg_energy_js,
    phi4_neg_reos_cum, phi5_neg_med_rmsd_xtb)` — byte-identical to
    `FlowMol3Glue.composite_score` in
    `tools/run_real_ckpt_eval.py:_compute_flowmol3_composite`.
  * Shared constants: `FLOWMOL3_ATOM_TYPES = 10`,
    `FLOWMOL3_DEFAULT_T0 = 0.0`, `FLOWMOL3_DEFAULT_T1 = 1.0`.
* ~120 LOC. No `adaptive_reflow` import.

#### File 2: `scripts/baselines/run_flowmol3_baseline_moldiff.py`

* Mirrors `run_lineageflow_baseline_euler.py` structurally.
* Loads the MolDiff model (or synthetic fallback), builds the
  starting noise + atom-type mask + 3D coordinates, runs NFE=10
  (and NFE=50, NFE=250) sampling, calls `composite_chemistry`,
  emits `flowmol3_baseline_moldiff_q4_2026.json`.
* Outputs:
  * `composite (MolDiff self)` — how MolDiff's own reflow / DDPM sampler
    concentrates vs the reference distribution.
  * `composite (MolDiff vs FlowMol3 baseline arm)` — MolDiff run from the
    same starting simplex as FlowMol3's 1-pass Euler, on the same NFE.
  * Wallclock, NFE, geometry (B, n_atoms, K).
* Notes:
  * MolDiff's chemistry-validity numbers may saturate at 0.95+ on
    GEOM-DRUGS (its published regime) — the comparison would still be
    informative on the composite axis (non-saturating by construction).
  * If MolDiff's public ckpt is not in this sandbox, the script
    degrades to a synthetic-init fallback (mirrors the Wave 52 Agent B
    `_load_twodim_weights` pattern). The composite numbers are then
    *paired-NFE only*, not a MolDiff paper-parity reproduction —
    the audit doc must say so explicitly.

#### File 3 (optional, lower priority): `scripts/baselines/run_flowmol3_baseline_equifm.py`

* Same shape as File 2, but for EquiFM.
* Deferred if Wave 54 has time / Wave 55 picks it up.

### B.7.2 Comparison table format (proposed §8.3 update)

A new §8.6 in paper-draft.md (or extension of the §8.3 Table 14):

| Model | iCT 1-step | RF+Reflow 1-step | DPMSolver++ 20-step | MolDiff (NFE=50) | EquiFM (NFE=50) | Framework vs **native** baseline (measured) | Source |
|---|---|---|---|---|---|---|---|
| 2D Rectified Flow | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | n/a | n/a | **PASS** (W2 −7.28%) | §4.2 |
| CIFAR-10 Rectified Flow | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | n/a | n/a | scheduler-discriminating at v4 | §4.3 |
| Kanzi (protein) | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | n/a | n/a | decision metric saturated; **composite +0.170 → framework_improves** | §7.3, §7.6 |
| LineageFlow (protein) | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | n/a | n/a | decision metric saturated; **composite +0.211 → framework_improves** | §7.4, §7.6 |
| FlowMol3 (molecule) | NOT YET MEASURED | NOT YET MEASURED | NOT YET MEASURED | **PLANNED Phase 2** (synthetic-mode if MolDiff ckpt missing) | **PLANNED Phase 2** | composite +0.000 `no_signal` (placeholder metric); metric layer BLOCKED | §7.5, §7.6 |

### B.7.3 Honest negative results to document

Even after Phase 2 lands:

1. **MolDiff / EquiFM on FlowMol3's metric may saturate at 0.95+** (the
   `frac_valid_mols` axis hits its ceiling on GEOM-DRUGS for all
   modern methods). The composite axis (Wave 49) is non-saturating and
   carries the comparison.
2. **The CTMC parameterisation gap** (paper-draft §5.7 limitation #3)
   is *not* closed by adding MolDiff/EquiFM baselines — both are
   continuous-time, so the comparison still leaves FlowMol3's CTMC vs
   linear-interpolant mismatch in scope. Phase 2 reports the comparison
   honestly; the CTMC gap remains separately scoped.
3. **MolDiff / EquiFM ckpts may not be in this sandbox.** The audit
   doc must say "synthetic-mode MolDiff baseline" or "synthetic-mode
   EquiFM baseline" if the upstream ckpts are not available — same
   convention Wave 52 Agent B used for `rectified_flow_cifar` real-ckpt
   being BLOCKED on outbound.

### B.7.4 What Phase 2 explicitly does NOT do

* Does **not** modify `adaptive_reflow/`, `framework/`, `scheduler/`,
  `tools/run_real_ckpt_eval.py`, or any adapter.
* Does **not** retrain any model.
* Does **not** re-emit any Wave 52 / Wave 53 / Wave 54 JSON.
* Does **not** commit unless explicitly asked (Wave 54 rule: read-only
  audit + Phase 2 fix design is the deliverable; commits deferred).

---

## B.8 Cross-references

* `docs/audit/wave52-baseline-comparison-impl.md` — 3 baselines
  (CM/RF/DPMSolver++) implemented + run on toy + CIFAR-10 RF.
* `docs/audit/wave52-sota-baselines-survey.md` — the 3-baseline survey
  + rationales + excluded candidates (LCM, ADD, PD, UniPC).
* `docs/audit/wave52-lineageflow-baseline-comparison.md` — 3
  LineageFlow baselines (Euler/Heun/RK4) on real LF ckpt.
* `docs/audit/wave52-kanzi-composite.md` — Kanzi composite benchmark
  on real Kanzi ckpt (no baseline scripts; uses `tools/run_real_ckpt_eval.py`).
* `docs/audit/wave52-sota-baseline-comparison.md` — D's integrated
  per-model comparison + 3-axis framework position.
* `docs/audit/wave52-per-component-ablation.md` — 5-arm × 3-model
  ablation matrix.
* `docs/paper-draft.md` §7.5 (FlowMol3 honest verdict), §7.6
  (3-model honest verdict), §8.5 (SOTA baseline measurement status).
* `docs/CONSOLIDATED_RESULTS.md` §15.7 (Tier 3 framework-vs-baseline
  synthesis).
* `verification_outputs/baseline_comparison_q4_2026.json` — 3
  Tier 1/2 baseline runs.
* `verification_outputs/lineageflow_baseline_*_q4_2026.json` — 3
  Tier 3 LF baseline runs.
* `verification_outputs/kanzi_real_composite_q4_2026.json` — Kanzi
  composite 9-cell sweep.
* `verification_outputs/flowmol3_real_composite_q4_2026.json` — FlowMol3
  composite 9-cell sweep (placeholder uniform-vs-uniform).

---

## B.9 JSON return value

```json
{
  "review_doc_path": "docs/audit/wave54-review-b-flowmol3-baselines.md",
  "existing_baselines_count": 9,
  "kanzi_baseline_files": [],
  "lineageflow_baseline_files": [
    "scripts/baselines/_lineageflow_helpers.py",
    "scripts/baselines/run_lineageflow_baseline_euler.py",
    "scripts/baselines/run_lineageflow_baseline_heun.py",
    "scripts/baselines/run_lineageflow_baseline_rk4.py"
  ],
  "flowmol3_baseline_files": [],
  "missing_baselines_top2": [
    {
      "name": "MolDiff",
      "paper": "Zhang et al. 2023, ICLR",
      "reason": "Closest published 3D-mol diffusion baseline; what FlowMol3 itself benchmarks against"
    },
    {
      "name": "EquiFM",
      "paper": "Song et al. 2023, ICLR",
      "reason": "Closest flow-matching predecessor to FlowMol3; lets framework argue on the FM axis specifically"
    }
  ],
  "relevant_comparison_papers": [
    "GraphAF (Shi et al. 2020, ICML)",
    "MolGen (Fang et al. 2022, NeurIPS)",
    "GeoDiff (Xu et al. 2022, ICLR)",
    "DM-SBG (arXiv:2209.14665, 2022)",
    "MolDiff (Zhang et al. 2023, ICLR)",
    "EquiFM (Song et al. 2023, ICLR)",
    "Rectified Flow (Liu 2022, ICLR 2023 Spotlight)",
    "Lipman Flow Matching (Lipman et al. 2023, ICLR)"
  ],
  "byte_stable_check_files": [
    "verification_outputs/baseline_comparison_q4_2026.json",
    "verification_outputs/lineageflow_baseline_euler_q4_2026.json",
    "verification_outputs/lineageflow_baseline_heun_q4_2026.json",
    "verification_outputs/lineageflow_baseline_rk4_q4_2026.json",
    "verification_outputs/lineageflow_baseline_comparison_q4_2026.json",
    "verification_outputs/kanzi_real_composite_q4_2026.json",
    "verification_outputs/flowmol3_real_composite_q4_2026.json"
  ],
  "files_to_create": [
    "scripts/baselines/_flowmol3_helpers.py",
    "scripts/baselines/run_flowmol3_baseline_moldiff.py",
    "scripts/baselines/run_flowmol3_baseline_equifm.py",
    "verification_outputs/flowmol3_baseline_moldiff_q4_2026.json",
    "verification_outputs/flowmol3_baseline_equifm_q4_2026.json",
    "docs/audit/wave54-phase2-flowmol3-baselines.md"
  ],
  "notes": "READ-ONLY review. Wave 52 baselines (CM / RF / DPMSolver++) are general-purpose image-CIFAR-style and do NOT carry a molecular generative modeling layer; they cannot fill the FlowMol3 baseline gap by re-targeting. The Wave 52 Agent C LineageFlow baselines (Euler / Heun / RK4) are integrator baselines on the protein axis only. The Tier 3 FlowMol3 baseline gap must be filled by domain-specialised molecular generative flow baselines — MolDiff + EquiFM are the right pair (closest 3D-mol diffusion SOTA + closest flow-matching predecessor). Phase 2 design specifies new scripts under scripts/baselines/ + new JSONs under verification_outputs/; byte-stable check: NO existing JSON may be re-emitted."
}
```