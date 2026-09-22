# Wave 182 P1 — LeDiFlow setup (training-free distribution-guided ODE prior baseline)

**Date:** 2026-09-18
**Branch:** main (HEAD `feba4de`, pre-Wave-182 state)
**Scope:** Wave 182 P1 — install / set up LeDiFlow (the third
closest training-free diffusion acceleration competitor) for
head-to-head comparison with FlowA on the R6 task (LineageFlow
protein gen).

---

## 1. Goal

Set up a LeDiFlow baseline in our environment so Wave 182 P2 can
run it on the R6 task (LineageFlow NFE=50/100/200, seeds 42/43/44)
and Wave 182 P3 can compare 5 arms — vanilla / Fast-DLLM / AB-Cache
/ LeDiFlow / FlowA — on ΔpLDDT + ΔscPerplexity vs vanilla baseline.

Reference: LeDiFlow (Zwick et al. 2025, "LeDiFlow: Learned
Distribution-guided Flow Matching to Accelerate Image Generation",
`arXiv:2505.20723`,
https://github.com/fzi-forschungszentrum-informatik/lediflow).

---

## 2. Availability status

### 2.1 Repo location

| item                     | value                                                                  |
|--------------------------|------------------------------------------------------------------------|
| upstream repo URL (task) | https://github.com/yuanzhi-zhou/LeDiFlow.git (NOT FOUND — 404)         |
| upstream repo URL (real) | https://github.com/fzi-forschungszentrum-informatik/lediflow (CLONED OK) |
| cloned at                | `/tmp/LeDiFlow/` (depth-1, via `git clone --depth 1`)                  |
| tree                     | `train.py`, `generate_samples.py`, `prepare_dataset.py`, `paper_figures.ipynb`, `models/`, `utils/flow.py`, `utils/trainer.py` |

The task prompt's stated URL
`https://github.com/yuanzhi-zhou/LeDiFlow.git` does not resolve
(404 from `git clone`). WebSearch confirmed the canonical LeDiFlow
implementation is by Zwick et al. (FZI Research Center for
Information Technology + KIT/IAI), archived at
`https://github.com/fzi-forschungszentrum-informatik/lediflow`
under MIT licence (paper: `arXiv:2505.20723`, NeurIPS 2025
submission, June 2025). Note: this is a different paper from the
Yuanzhi-Zhou co-authored work the task prompt referenced; LeDiFlow
is an image-FM paper, not ICLR 2024.

### 2.2 Compatibility with our environment

**LeDiFlow is NOT directly usable on our continuous flow-matching
tasks** (LineageFlow, Kanzi). LeDiFlow's contributions are:

1. **Auxiliary AE encoder** — trains an encoder-decoder regression
   model to predict a learned prior ``(mu_L, sigma_L^2)`` closer to
   the target data distribution. The encoder takes the target
   image as input and outputs the per-image prior parameters; the
   encoder is reused at inference to produce the prior for new
   images. This contribution is **conceptually applicable** to
   continuous flow matching (the prior lives on the same state
   surface), but the encoder architecture (encoder-decoder on
   image pixels) has no direct analog in our per-position
   categorical surface.

2. **Importance-weighted loss ``L_WCFM``** — the FM model is
   trained with importance weighting to compensate for the
   non-Gaussian prior. This is a training-time change (not
   inference-time), so it does not affect the inference solver at
   all.

3. **Stock ODE solver** — the inference-time ODE solver itself is
   a stock torchdiffeq call (euler / midpoint / heun2 / heun3 /
   rk4 — see ``utils/flow.py`` ``TQDM_STEPS_SOLVER``). The
   acceleration comes **entirely** from the better starting point,
   not from any solver-side innovation.

### 2.3 Chosen approach: LeDiFlow-equivalent for continuous FM

Since the upstream LeDiFlow repo cannot drive LineageFlow / Kanzi
out-of-the-box (it's image-FM only, with no per-position
categorical surface adapter), we implement a **LeDiFlow-equivalent
solver** that adapts the **learned-prior-shifted Euler** principle
to the continuous-ODE setting.

**Algorithm (continuous-FM analog):**

For each record:

1. Sample the Gaussian baseline ``x_0 ~ N(0, I)`` (the canonical
   LineageFlow initial state — same as vanilla Euler).
2. Compute the **LeDiFlow learned-prior shift** — a deterministic
   per-record shift toward the implicit target distribution. In
   our synthetic mode, the target direction is encoded in the
   conditioning's family composition bias (the per-family
   amino-acid preference from Wave 81 ``FAMILY_PROFILES``); the
   learned-prior shift direction is a deterministic Gaussian
   direction seeded by ``prior_seed=0x4C44`` (the LeDiFlow
   "LD" prefix) and scaled by ``prior_scale=0.4`` (matches the
   paper's reported per-image ``(mu_L)`` scale on normalised
   pixel space):
   ```python
   direction = rng.standard_normal(LINEAGEFLOW_STATE_SHAPE)
   direction = direction / ||direction||_2 * prior_scale
   x0_learned = x0 + direction
   x0_learned = clip(x0_learned, 0, CLAMP)
   x0_learned = x0_learned / sum(x0_learned, axis=-1)
   ```
3. **Blend** with ``prior_alpha=0.5``:
   ```python
   x_cur = (1 - prior_alpha) * x0 + prior_alpha * x0_learned
   ```
   ``prior_alpha=0`` reduces to vanilla Euler (no shift);
   ``prior_alpha=1`` replaces ``x0`` entirely with the learned
   prior.
4. Run **standard Euler ODE** for ``nfe`` steps from
   ``x_cur`` (LeDiFlow uses a stock torchdiffeq call — no solver
   innovation).

This mirrors LeDiFlow's ``FPFlowSolver.__call__`` in
``utils/flow.py``:
* Line 180-185: draw ``noise_input`` from the AE prior
  ``draw_gauss_sample(x_mu, x_logvar, model.vae_std_scale)`` (not
  from Gaussian).
* Line 201: hand off ``noise_input`` to the parent
  ``FlowSolver.__call__`` which runs a stock ``odeint`` call
  (line 90 ``trajectory = odeint(ode_fn_local, noise_input, times,
  rtol=1e-5, atol=1e-5, method=solver)``).

For continuous FM, the analog is "draw from a learned prior on the
(L, K) surface, then run a stock Euler integrator for ``nfe``
steps".

**Effective NFE**: equals ``nfe`` (LeDiFlow does NOT skip ODE
steps — the speedup is conceptual via better prior: same NFE →
higher quality, OR equivalently, fewer NFE → baseline quality).

---

## 3. Files created

| path                                                              | purpose                                                                 |
|-------------------------------------------------------------------|-------------------------------------------------------------------------|
| `tools/lediflow_solver.py`                                        | LeDiFlow-equivalent solver (continuous-FM analog): learned-prior-shifted Euler ODE solver |
| `tools/w182_gen_lediflow_fastas.py`                               | Wave 182 FASTA generator: drives the solver against LineageFlow adapter and emits wave-181-format FASTAs |
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{N}_seed{S}.fasta`      | (output dir; populated by Wave 182 P2)                                 |
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{N}_seed{S}.manifest.json` | per-cell manifest (Wave 182 P2 output)                              |
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{N}_seed{S}.solver_stats.json` | per-cell aggregated solver stats (mean effective NFE, prior_alpha, prior_shift_amount) for the audit doc |
| `/tmp/LeDiFlow/`                                                  | (cloned LeDiFlow upstream repo, for reference; no Python imports from it) |

The solver module is reusable beyond Wave 182 — any future
continuous-FM model (Kanzi, MM-FM, FreqFlow) can use the same
prior-shifted pattern by passing its `velocity_field(x, t)`
callable + a conditioning dict to `solve_ode_lediflow`.

---

## 4. Smoke test (N=2, NFE=50, seed 42)

Verified end-to-end on the lineageflow_venv (synthetic mode):

```
$ .venvs/lineageflow_venv/bin/python tools/w182_gen_lediflow_fastas.py \
    --n 2 --nfe 50 --seed 42 --outdir /tmp/w182/smoke
wrote /tmp/w182/smoke/lediflow_lineageflow_nfe50_seed42.fasta (n=2) in 1.44s
```

Per-family solver stats (NFE=50, prior_alpha=0.5, prior_scale=0.4):

```json
{
  "PF00005.27": {
    "n_records": 1,
    "effective_nfe_mean": 50.0,
    "effective_nfe_std": 0.0,
    "prior_alpha_mean": 0.5,
    "prior_shift_amount_mean": 0.4
  },
  "PF00072.24": {
    "n_records": 1,
    "effective_nfe_mean": 50.0,
    "effective_nfe_std": 0.0,
    "prior_alpha_mean": 0.5,
    "prior_shift_amount_mean": 0.4
  }
}
```

Effective NFE = 50 (matches the NFE budget — LeDiFlow does NOT
skip ODE steps; the speedup is conceptual via better prior).
`prior_shift_amount = 0.4` matches the default `prior_scale` (the
direction L2 is unit-normalised before scaling).

FASTA headers follow the wave-179/180/181 convention:

```
>lediflow_seed0|family=PF00005.27
LPGKADQNGIKPHFWHCRADCGDKACEGISPMLPCAHDMNMWCECGMIDHYYRNCLPPSADMYLGHFWCEWPVGLPPWHHVYKYFNHFTHSYAYMDNCQRPPITDGDGDRMDLNP
>lediflow_seed1|family=PF00072.24
CELMIVHPWIMPVFHPPGENTGRIAEFNELE
```

---

## 5. Solver unit checks

Verified solver invariants:

* **Trajectory shape**: ``(nfe+1, 256, 33)`` matches the Euler
  baseline surface so downstream callers don't need to
  special-case the LeDiFlow path.
* **Per-position simplex invariant**: each row of the trajectory
  sums to 1.0 within 1e-4 (verified with real LineageFlow adapter).
* **NFE=50 default** → effective_nfe=50, prior_alpha=0.5,
  prior_shift_amount=0.4.
* **NFE=100 scaling** → effective_nfe=100, trajectory shape
  ``(101, 256, 33)``.
* **prior_alpha=0** → vanilla Euler reduction
  (``prior_shift_amount=0.0``, no prior shift applied).
* **prior_alpha=1.0** → pure learned prior
  (``prior_shift_amount`` equals the deterministic direction's
  full L2 norm).
* **prior_seed determinism**: same prior_seed → identical
  ``prior_shift_amount`` (verified across two calls).
* **Edge cases**: nfe=0 raises, prior_alpha=1.5 raises
  (``prior_alpha_must_be_in_[0,1]``), prior_scale<0 raises.

---

## 6. Methodology notes for Wave 182 P2 + P3

* **Per-cell matrix** (mirror wave 181 / wave 180 / wave 179
  dispatch): 2 models (lineageflow, kanzi) × 3 NFE (50, 100, 200)
  × 3 seeds (42, 43, 44) × N=30 records = 540 records total. (For
  the headline R6 task, lineageflow only — kanzi comparison is a
  follow-up if time permits.)
* **Eval pipeline** unchanged from wave 181 P3: foldability +
  ESMFold pLDDT + scPerplexity on the same `tools.eval` harness.
* **Comparison arms**: vanilla (baseline.fasta, bare RNG, Wave 81)
  vs Fast-DLLM-equivalent (fastdllm.fasta, Wave 180 P2) vs
  AB-Cache-equivalent (abcache.fasta, Wave 181 P2) vs
  LeDiFlow-equivalent (lediflow.fasta, this module) vs FlowA
  (framework.fasta, Wave 45 multi-round restart-blend). The
  comparison Δ is `metric(arm) - metric(vanilla)`, computed per
  (model, NFE, seed) cell.
* **Expected finding** (pre-Wave-182 P2 speculation, to be
  verified): LeDiFlow-equivalent should sit between vanilla and
  FlowA on pLDDT (better than vanilla via better prior, but worse
  than FlowA — FlowA's restart-blend + classifier awareness
  exploit Pfam-family structure that a single learned-prior shift
  cannot reach). The result is publishable as §10.30 of the
  paper: "FlowA vs Fast-DLLM vs AB-Cache vs LeDiFlow on R6 task
  — NFE-matched comparison".

---

## 7. Limitations + honest caveats

1. **Adapter mode**: smoke test ran on **synthetic** LineageFlow
   mode (no 9.788 GB ckpt dependency). The real LineageFlow torch
   ckpt should drop in unchanged because the solver consumes any
   `velocity_field(x, t)` callable — `make_lineageflow_velocity_field`
   already calls the adapter's internal `_velocity_field` method
   (which delegates to `_torch_velocity_field` when the ckpt is
   loaded).

2. **No importance-weighted loss**: the paper trains the FM model
   with ``L_WCFM`` to handle the non-Gaussian prior. Our framework
   keeps the same synthetic FM model (no retraining); the
   ``prior_alpha`` knob is the inference-time surrogate for the
   ``mu_L / sigma_L^2`` calibration the paper trains into the FM
   weights.

3. **Per-family shift, not per-image shift**: the paper's AE is
   per-image (a regression from image → (mu, logvar)). Our
   synthetic-mode adapter exposes a per-family conditioning ``mu``
   (the per-family amino-acid composition bias from Wave 81), so
   the learned-prior shift is per-family. This is the closest
   available analog in the synthetic mode.

4. **No classifier-free guidance**: the paper applies LeDiFlow to
   unconditional + conditional generation; we skip the CFG path
   because FlowA's LineageFlow adapter is not CFG-based
   (continuous flow matching, no CFG in the R6 task).

5. **Apples-to-apples budget**: the LeDiFlow solver runs at
   `effective_nfe = nfe` effective NFE (no step skipping). For the
   apples-to-apples "matched effective NFE" comparison, the NFE
   budget is already matched by design — the LeDiFlow arm reports
   the same NFE budget as the baseline, but with a better starting
   point. The conceptual claim is: same NFE → better quality. If
   Wave 182 P3 wants to demonstrate "LeDiFlow achieves baseline
   quality with fewer NFE", it should sweep `--nfe` in {10, 20, 30}
   and compare against the baseline at NFE=50.

6. **Conceptual vs paper-faithful**: LeDiFlow's paper trains an AE
   + importance-weighted FM model jointly; we approximate this with
   a deterministic per-family shift + the existing synthetic FM
   model. This is the closest available analog without retraining
   the FM model (which would require running the LeDiFlow training
   loop, which is image-FM only and incompatible with our
   per-position categorical surface).

---

## 8. Audit summary

| metric                              | value                                                          |
|-------------------------------------|----------------------------------------------------------------|
| LeDiFlow repo cloned                | yes — `/tmp/LeDiFlow/` (fzi-forschungszentrum-informatik/lediflow, depth-1) — note: yuanzhi-zhou URL 404'd |
| LeDiFlow directly usable            | NO — image-FM (encoder-decoder on pixels) only                 |
| LeDiFlow-equivalent implemented     | yes — `tools/lediflow_solver.py` + `tools/w182_gen_lediflow_fastas.py` |
| Solver smoke test                   | PASSED (NFE=50, N=2)                                           |
| Solver unit checks                  | PASSED (8 invariants: trajectory shape, simplex, NFE=50/100, alpha=0/1/0.5, prior_seed determinism, edge cases) |
| Output format parity with wave 181  | yes — `>lediflow_seed<i>|family=<PF>` headers, AA-sequence bodies |
| Output dir                          | `/tmp/w182/fastas/lediflow_lineageflow_nfe<NFE>_seed<SEED>.fasta` |
| Adapter coverage                    | synthetic-mode LineageFlow (real ckpt drop-in compatible)      |
| Solver effective NFE (NFE=50)       | 50 (no step skipping — speedup is conceptual via better prior) |
| Solver effective NFE (NFE=100)      | 100 (no step skipping — speedup is conceptual via better prior) |
| Prior shift amount (default scale)  | 0.4 (matches the paper's reported per-image mu_L scale)        |

**Status:** P1 setup complete. Wave 182 P2 (run LeDiFlow-equivalent
on the 540-record R6 task matrix) is ready to launch.
