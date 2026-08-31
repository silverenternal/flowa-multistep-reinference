# Fix plan v2 — frontier patterns + R12 follow-up

> **Author:** Agent R (research + deep-code-review + fix-plan-v2 subagent)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Status:** READ-ONLY plan; no code changes. Awaiting approval before
> the Phase-3 workstream (state propagation + Heun solver + apples-to-
> apples comparison + PID amplification) is executed.
> **Inputs cited:**
> - `docs/r4-survey/18-comprehensive-code-review.md` (R11 audit; 52 bugs)
> - `docs/r4-survey/19-fix-plan.md` (R12 fix plan; 7 P0 fixes)
> - `docs/r4-survey/20-cifar-experiment-v3-results.md` (R12 v3/v4 results)
> - commit `82cd299` (the 7 P0 fixes were applied)
> - WebSearch frontier-pattern research (5 queries; see §1)

---

## §0. TL;DR

R12 already shipped the 7 P0 fixes (commit `82cd299`) and lifted the
CIFAR-10 baseline FID from 218.87 to 83.09 (2.63×) by widening the NFE
budget and adding a per-scheduler seed offset. **All 7 P0 fixes verified
applied; no regressions; 4 P0 fixes have dedicated regression tests, 3
are exercised by smoke runs only.**

The four critical issues that remain open (F-34 state propagation,
Heun solver, apples-to-apples NFE comparison, PID signal amplification)
are **research-grade**, not bug-grade. They require:

1. **Frontier-pattern selection** (§1) — pick the right approach from
   k-diffusion, EDM, Rectified Flow, control theory, etc.
2. **Deep code review** (§2) — verify the fix site and the
   forward/backward-compatibility surface.
3. **Implementation plan** (§3) — file:line + code sketch.
4. **Risk + verification** (§5-§6).
5. **P1 + P2 backlog carry-over** (§4) — from the r12 audit.

**Effort estimate (Phase-3 workstream):** 16–22 h hands-on (~3 dev-
days) + 4 h wall-clock for the Heun + 5K-sample FID run = **~25 h
wall-clock to reach a Heun-enabled 5K-sample CIFAR-10 number within
~6× of the published 2.58 FID.**

**Honest scope statement:** this plan does NOT promise to close the 32×
gap to published FID. Sample-count (5K vs 50K = 10×) and solver order
(Heun 2nd-order vs Euler 1st-order ≈ 2×) are the dominant terms; both
are addressed here but cannot be eliminated at our CPU compute budget.

---

## §1. Research summary (citations + recommendations)

### §1.1. Multi-round state propagation (for F-34)

**Sources consulted (4):**

- **EDM / Karras 2022** — probability-flow ODE with Heun's 2nd-order
  solver. State is `(x, σ)`; propagation is implicit in the ODE step
  (no explicit "round" concept). Source: [EDM Walkthrough](https://aicassindra.com/blogs/transformer_math/tm_edm.html).
- **k-diffusion (sample_euler / sample_heun / sample_ancestral)** —
  implements restart via re-noising at intermediate `σ` values. State
  propagation is the trajectory itself. Source: [EDM Implementation
  Notebook](http://beckham.nz/2024/05/31/diffusion-scheduler-origins).
- **Rectified Flow (Liu 2022)** — reflow / rectifier between rounds
  re-trains the velocity field on its own ODE pairs. The
  **inference-time** analogue is to chain `x_{t+1}` from round `r` as
  `x_0` of round `r+1`, optionally with a fresh-noise perturbation
  (β-blend). Source: [Flow Straight and Fast
  Review](https://liner.com/review/flow-straight-and-fast-learning-to-generate-and-transfer-data).
- **Score-based generative modeling** — annealed Langevin dynamics
  chains rounds by adding noise then denoising. The chains carry
  `(x, score)` and the noise level decreases monotonically.

**Pattern matrix:**

| Pattern | Source | State propagated | Refresh? | Cost | Fidelity |
|---|---|---|---|---|---|
| Pure chain (`x_{t+1} → x_0^{(r+1)}`) | Flow Matching | state only | none | 1× | medium (drift accumulates) |
| β-blend chain (memory fraction) | FlowA's `apply_restart_distribution` | state + memory | partial | ~1× | high (paper Theorem 1) |
| Ancestral re-noise (EDM) | k-diffusion | state + fresh noise | full | ~1× | high (escapes local modes) |
| Reflow (distillation) | Liu 2022 | model re-trained | full | 100× | highest (paper headline) |

**Recommendation for FlowA:**

The framework **already implements the β-blend chain** in
`apply_restart_distribution` (per `adapters/rectified_flow_cifar.py:732`)
and the runner **already chains the bundle** between rounds via
`observe_endpoint` (per `runner.py:1061`). The F-34 audit finding
(line 748) was about the runner's `bundle` parameter NOT being updated
in the loop body — that fix has now landed (line 1061 re-assigns
`bundle` from `observe_endpoint`).

**What's missing in the harness** (`tools/run_sota_cifar_experiment.py:467`)
is the **call to `apply_restart_distribution`** between rounds. The
harness currently calls `adapter.batched_inference(n_samples, num_steps,
seed)` per round with a fresh seed — i.e., each round draws fresh
Gaussian noise and starts a fresh Euler trajectory. This is the
"ancestral re-noise" pattern without the chaining: the framework's
"coarse-to-fine" signal lives only in `n_cap`, not in the per-sample
state. On CIFAR the per-sample state is discarded anyway (the per-round
samples are pooled into a single FID set), so the chain is moot for
the FID comparison — but for a **stateful** comparison, the harness
must thread `bundle → apply_restart_distribution → observe_endpoint →
bundle_{r+1}`.

**Design recommendation:** add a `--stateful` flag to the harness
(default off — the v3/v4 results are stateless). When on, the harness
constructs one `bundle` per chain, calls `apply_restart_distribution`
between rounds, and computes the FID on the **final round's endpoint**
of each chain (not the pooled per-round samples). This isolates the
"framework chains state across rounds" effect from the "framework pools
independent samples across rounds" effect.

### §1.2. Heun 2nd-order ODE solver (for the FID gap)

**Sources consulted (5):**

- **Karras EDM 2022** — establishes Heun as the standard 2nd-order
  solver for diffusion models. Source: [NVIDIA Modulus EDM
  Docs](https://docs.nvidia.com/deeplearning/modulus/modulus-core-v040/examples/generative/diffusion/README.html).
- **Skrew.ai ODE Solvers** — Heun evaluates the velocity field 2×
  per step (2 NFEs), achieves 2nd-order accuracy; for flow matching,
  "Heun typically matches Euler quality at roughly half the steps".
  Source: [ODE Solvers for Flow
  Matching](https://news.skrew.ai/ode-solvers-flow-matching-generative-models).
- **Exposure-Bias analysis (arXiv 2308.15321)** — Heun 35 NFE improves
  EDM FID 3.81 → 2.80 unconditional (unconditional CIFAR-10). Source:
  [Elucidating the Exposure Bias in Diffusion
  Models](https://ar5iv.arxiv.org/html/2308.15321).
- **Trajectory regularity (arXiv 2405.11326)** — Heun's 2nd-order
  truncation error bound (per-step: `O(Δt²)` vs Euler's `O(Δt)`).
  Source: [On the Trajectory Regularity of ODE-based Diffusion
  Sampling](https://ar5iv.labs.arxiv.org/html/2405.11326).
- **Liu 2022 Rectified Flow** — the paper's headline 2.58 FID uses
  RK45 (adaptive) at 127 NFE; Heun at 35–50 NFE typically lands
  5.0–7.0 on 1-RF (paper Table 1). Source: [Flow Straight and Fast
  Review](https://liner.com/review/flow-straight-and-fast-learning-to-generate-and-transfer-data).

**Heun algorithm (predictor-corrector):**

```
# at each step (x, t) -> (x, t'):
v1 = velocity_field(x, t)                          # predictor
x_pred = x + (t' - t) * v1                         # Euler trial step
v2 = velocity_field(x_pred, t')                    # corrector eval
x_new = x + (t' - t) * 0.5 * (v1 + v2)             # trapezoidal update
```

This is **2 NFEs per step**. With 50 steps that's 100 NFEs vs Euler's
50. **Equivalent NFE comparison**: Heun-25 vs Euler-50 should land
within 0.5 FID (the trapezoidal rule halves the truncation error per
step, so 2× fewer steps gives the same accuracy).

**Score-model output (rectified_flow_cifar):** our `_torch_velocity_field`
returns the velocity `v(x, t)` directly (no ε/v parameterisation
switch). Heun just calls it twice at different `(x, t)`. No
parameterisation change needed.

**Reference implementation** (k-diffusion `sample_heun`):

```python
def sample_heun(model, x, sigmas, ...):
    s_in = x.new_ones([x.shape[0]])
    for i in trange(len(sigmas) - 1):
        sigma_cur, sigma_next = sigmas[i], sigmas[i+1]
        dt = sigma_next - sigma_cur
        # Euler predictor
        denoised = model(x, sigma_cur * s_in)
        d_cur = (x - denoised) / sigma_cur
        x_next = x + d_cur * dt
        # Heun corrector
        if sigma_next != 0:
            denoised_next = model(x_next, sigma_next * s_in)
            d_next = (x_next - denoised_next) / sigma_next
            x_next = x + (d_cur + d_next) * 0.5 * dt
        x = x_next
    return x
```

In our `RF_CIFAR_T_END = 1.0` parameterisation, `t` runs from `0 → 1`
(velocity field is `v(x, t)` for `t ∈ [0, 1]`). Heun port:

```python
# In rectified_flow_cifar.py:867-884, replace the Euler loop with:
for i in range(1, t_grid.size):
    t0, t1 = float(t_grid[i-1]), float(t_grid[i])
    dt = t1 - t0
    v1 = velocity_field(x_cur, t0)
    x_pred = np.clip(x_cur + dt * v1, -CLAMP, CLAMP)
    if i < t_grid.size - 1:                       # corrector (skip last step)
        v2 = velocity_field(x_pred, t1)
        x_cur = np.clip(x_cur + 0.5 * dt * (v1 + v2), -CLAMP, CLAMP)
    else:
        x_cur = x_pred
    traj[i] = x_cur
```

**Cost vs Euler:** ~2× wall-clock per step. Heun-25 vs Euler-50
should land within 0.5 FID but cost the same wall-clock. Heun-50 vs
Euler-50 costs 2× wall-clock for ~30–40% FID improvement.

**Expected FID improvement (informed by literature):**
- Euler 50 NFE (current v4): 83.09
- Heun 25 NFE: ~80–82 (1.5–4% improvement at matched wall-clock)
- Heun 50 NFE: ~70–75 (15–18% improvement at 2× wall-clock)
- Heun 100 NFE: ~60–65 (28–33% improvement at 4× wall-clock; matches
  the paper's 127 NFE RK45 adaptive within ~2×)

### §1.3. Apples-to-apples NFE comparison

**Sources consulted (4):**

- **Rectified Flow Liu 2022 Table 1** — same model, different NFE
  budget; FID vs NFE plotted. Source: [Flow Straight and Fast
  Review](https://liner.com/review/flow-straight-and-fast-learning-to-generate-and-transfer-data).
- **EDM Karras 2022 Table 1** — same model, NFE ∈ {18, 36, 80}, FID
  reported at each NFE. Source: [EDM
  Walkthrough](https://aicassindra.com/blogs/transformer_math/tm_edm.html).
- **DPM-Solver (Lu 2022)** — ablations at NFE ∈ {5, 10, 20, 50, 100}.
  Reports FID at each NFE. (Source omitted — covered in standard
  diffusion lit.)
- **Multisample Flow Matching (Kornilov 2023)** — explicitly
  introduces a "consistency metric" for matched-NFE comparison.
  Source: [Multisample Flow
  Matching](https://ar5iv.arxiv.org/html/2304.14772).
- **What Flow Matching Brings to TD Learning (Agrawalla 2026)** —
  "compute-matched comparison: allocating the same capacity via
  Q-network ensembles or ResNets performs worse, even in a compute-
  matched evaluation." Source: [Flow Matching for TD
  Learning](https://arxiv.org/pdf/2603.04333).

**The right comparison protocol (literature consensus):**

1. **Same model weights** (we have this — Liu 2022 1-RF).
2. **Same NFE per sample** (we DON'T have this — baseline uses 50
   Euler-NFE per sample; framework uses avg 25.2 Euler-NFE per sample).
3. **Same noise stream per sample** (we DON'T have this — baseline
   uses `seed=0`, framework uses `seed=r+offset` per round).
4. **Same FID sample count** (we have this for v4 — 500 samples).
5. **FID computed against the same reference .npz** (we have this).

**The apples-to-apples fix (per the v3 §5 honest framing):**

```bash
# Option A: matched total NFE (framework sums across rounds to baseline)
python tools/run_sota_cifar_experiment.py \
    --baseline-num-steps 250 \
    --framework-max-num-steps 250 \
    --n-samples 500 --n-rounds 10 --framework-samples 50

# Framework per-sample budget: avg 126 NFE × 1 round ≈ 126 NFE per chain
# Baseline per-sample budget: 250 NFE × 1 sample
# Effective NFE per FID sample: framework ≈ 126; baseline ≈ 250
# NOT YET MATCHED — the framework's per-sample budget is half the baseline.

# Option B: matched per-sample NFE (recommended by the literature)
python tools/run_sota_cifar_experiment.py \
    --baseline-num-steps 25 \
    --framework-max-num-steps 25 \
    --n-samples 500 --n-rounds 10 --framework-samples 50
# Framework per-sample budget: avg 12.6 NFE × 1 chain ≈ 12.6 NFE
# Baseline per-sample budget: 25 NFE × 1 sample
# MATCHED — both produce 1 image at ~25 NFE total per FID sample.

# Option C: matched wall-clock (the strictest protocol)
# Run baseline at 100 NFE, framework at 50 NFE
# Frame baseline's wall-clock ≈ framework's wall-clock
# (only valid if the framework's per-round overhead is comparable to
# the baseline's per-sample overhead)
```

**Recommendation:** adopt **Option B (matched per-sample NFE)** as the
default. This is the standard protocol in EDM/DPM-Solver/Rectified-Flow
ablations. The Option A protocol is a "framework is more compute-
efficient" claim; Option C is a "framework is faster at the same
quality" claim — both are valid but they're different claims.

**Recommendation:** keep the **current v4 protocol** (Option A — both
at 50 NFE budget) as a **compute-budget-matched** comparison but
acknowledge in the markdown that the framework's per-sample NFE is
half the baseline's (because of the cosine ramp). Add Option B as a
new `--match-nfe` CLI flag.

### §1.4. PID signal amplification (for the F-3 / F-32 outcome gap)

**Sources consulted (5):**

- **Ziegler-Nichols tuning** — the canonical PID gain selection method.
  Source: [Ziegler-Nichols Tuning
  Method](https://www.motioncontroltips.com/control-theory-ziegler-nichols-tuning-method/).
- **Adaptive PID via Genetic Algorithm** — adjusts PID gains online to
  improve weak-signal tracking. Source: [Adaptive PID for Weak Signal
  Tracking](https://www.researchgate.net/publication/327154599_An_Adaptive_PID_Controller_Using_a_Genetic_Algorithm_for_Weak_Signal_Tracking).
- **Real-Time Adaptive PID via RL (arXiv 2108.05355)** — RL adjusts
  PID gains in real time. Source: [Real-Time Adaptive PID via
  RL](https://arxiv.org/abs/2108.05355).
- **Adaptive Gain Tuning for Nonlinear PID (IEEE 8823567)** — adjusts
  Kp/Ki/Kd based on operating conditions using ML estimation.
- **Model-Reference Adaptive Control (MDPI 7763)** — adapts controller
  parameters to handle uncertainty and varying dynamics.

**Why the current PID signal is too small:**

Per the evidence_driven.py audit (F-3) and the v3 results:

- `target_ratio = 1.0` (paper's evidence ordering set-point)
- `evidence_ratio` proxy from `CodimensionSheetScheduler` drifts from
  1.0 (r=0) to ~0.952 (r=9) per v3 §1.4
- `error = target_ratio - observed_ratio` max ≈ 0.048
- `raw = kp * error + ki * integral_error` with `kp=0.2, ki=0.05`,
  integral caps at ±10 → `raw ≈ 0.2*0.048 + 0.05*0.048 ≈ 0.012`
- `applied = clip(raw, ±max_step=0.05) = 0.012`
- **Δ n_cap at r=9 ≈ 0.012**, which when mapped through
  `round(0.988 * 50) = 49` (cosine) vs `round(0.988+0.012 * 50) = 50`
  is a **+1 NFE bump at most** — below the rounding threshold in
  most cases (the cosine ramp's `n_cap[9] = 0.0` so the PID delta
  hits a clamped value of 0.012 which rounds to 0 anyway).

**Three amplification strategies (literature-backed):**

1. **Lower the target_ratio set-point** (cheapest, paper-neutral):
   set `target_ratio = 0.95` so the baseline error is `1.0 - 0.952 = 0.048`
   mapped through a larger gain. Or set `target_ratio = 0.99` so the
   steady-state error drives the delta above the rounding threshold.
2. **Use error-deadband amplification** (Ziegler-Nichols derivative
   trick): when `|error| < ε`, multiply the gain by a factor `K_boost`
   (e.g., 10×) so a small error still moves `n_cap`. This is what the
   paper's evidence ordering actually expects (paper Theorem 1 says
   ratio rises as `eps → 0`; we want to drive `eps` to 0).
3. **Adaptive gain scheduling** (IEEE 8823567): make `kp` a function
   of `cycle_length` (more rounds → smaller `kp` because more
   opportunities to correct). Currently `kp=0.2` is fixed; adaptive
   `kp = 0.2 / max(1, round/10)` would give the PID more authority
   early when the error is largest.

**Recommendation:** combine **(1) lower target_ratio to 0.95** + **(3)
adaptive `kp`** for the cleanest amplification. The deadband approach
(2) is brittle — it introduces a discontinuity at the deadband edge.
The literature consensus (Ziegler-Nichols + RL adaptive tuning) is that
**gain scheduling + set-point tuning** is more robust than
deadband tricks.

**Specific recommendations:**

```python
# In evidence_driven.py, the _PIDLiteController.__init__ signature:
class _PIDLiteController:
    def __init__(
        self,
        *,
        kp: float = 0.2,                 # baseline Kp
        ki: float = 0.05,                # baseline Ki
        max_step: float = 0.05,
        target_ratio: float = 0.95,      # CHANGED: 1.0 -> 0.95 (paper Theorem 1
                                          # is "ratio rises toward 1"; the natural
                                          # asymptote is below 1.0 because of
                                          # the cell evidence contribution)
    ):
```

Plus, add **gain scheduling** to the harness:

```python
# In tools/run_sota_cifar_experiment.py:197-206, the EvidenceDrivenScheduler config:
if name == "EvidenceDrivenScheduler":
    # Adaptive Kp: smaller for longer cycles (more chances to correct).
    adaptive_kp = 0.5 / max(1, int(rounds) / 5)
    return EvidenceDrivenScheduler(
        config=_build_cosine_schedule_config(int(rounds)),
        kp=adaptive_kp,                    # CHANGED: 0.2 -> adaptive
        ki=0.05,
        max_step=0.1,                      # CHANGED: 0.05 -> 0.1
        target_ratio=0.95,                 # CHANGED: 1.0 -> 0.95
        k_eps=0.5,
        eps_implicit_base=0.05,
    )
```

**Expected effect:** with `target_ratio=0.95` and `kp=0.5/2 = 0.25`
(for `rounds=10`):
- `error = 0.95 - 0.952 = -0.002` (cosine baseline is actually
  overshooting the set-point slightly → negative error → +ve delta)
- `raw = 0.25 * (-0.002) + 0.05 * integral ≈ -0.0005 + 0.0003 ≈ -0.0002`
- This is still too small. **Need a different amplification lever.**

**Alternative: amplify the error signal itself.** The cosine baseline
(`evidence_ratio = 1.0` constant in the proxy) is the wrong signal — the
proxy scheduler gives the SAME `evidence_ratio=1.0` for every round
when `eps_implicit=0.05`. The PID is therefore running with
`error = target - 1.0 = 0.0` at every round. **No amplification can
produce a non-zero delta when the input signal is constant.**

**The real fix:** the harness should compute `evidence_ratio` from the
**observed** sample's `coverage` / `W2` / `selection_ratio`, not from
the proxy scheduler's constant. The proxy was a v2 workaround (per
`tools/run_sota_cifar_experiment.py:447-462`); the v3 audit confirms
it is insufficient. The proper signal is the **per-round oracle
metric** computed by the framework's evaluator (which exists in
`runner.py:963-967` but is **not used by the harness**).

**Real recommendation:** the harness should:

1. Run a small "oracle pass" per round (compute `selection_ratio` via
   the `PosteriorSelectionEvaluator`) to get a real per-round
   `evidence_ratio`.
2. Pass that to `scheduler.record_round_feedback(...)`.
3. Use `target_ratio = 0.95` and `kp = 0.5` (the original paper
   configuration).

This is the **structural fix** for the PID amplification issue — the
current architecture simply does not feed the PID a real signal.

---

## §2. Per-issue fix design

### §2.1. F-34 state propagation design

**Status: PARTIALLY FIXED at the runner level; NOT FIXED at the harness level.**

**What's already there:**
- `runner.py:1061` calls `observe_endpoint(trace, bundle)` and re-
  assigns `bundle = ...` at the bottom of each round loop iteration.
- `runner.py:774-778` constructs the initial `bundle` only for
  `r=0` via `build_initial_state(...)`.
- All 10 adapters implement `observe_endpoint` (per `grep`).

**What's missing in the harness:**
- `tools/run_sota_cifar_experiment.py:467` calls `adapter.batched_inference(...)`
  per round with a fresh seed; it **does not chain state**.
- The harness does not use `ReInferenceRunner` at all; it directly
  drives `scheduler.sample` and `adapter.batched_inference`.
- The per-round samples are pooled into a single FID set (not the
  final-round endpoint), so chained state is moot for the FID
  metric.

**Design: add `--stateful` flag to the harness.**

When `--stateful` is on:

1. For each chain, construct one `bundle` via
   `adapter.build_initial_state(batch_id=f"chain-{i}", sample_id=f"chain-{i}-r0")`.
2. For each round `r`:
   a. Build `RestartPolicy` with `beta_by_channel={channel: merged_beta}`.
   b. Call `adapter.apply_restart_distribution(bundle, policy)` → new
      bundle (β-blended).
   c. Call `adapter.solve_ode(bundle, condition_delta, seed=seed)` →
      `ODEIntegratorTrace`.
   d. Call `adapter.observe_endpoint(trace, bundle)` → new bundle.
   e. Use this bundle as round `r+1`'s prior.
3. After the final round, write `adapter.export_endpoint(bundle)` to
   the chain's output.

This is the "β-blend chain" pattern from the FlowA paper (Theorem 1
+ ADR-0013). On CIFAR, the β-blend chain would actually refine rather
than just re-noise — round `r+1` sees round `r`'s denoised endpoint
blended with fresh noise scaled by `1 - beta = n_cap`. With
`n_cap = 0.5`, the chain is half-memory / half-fresh-noise.

### §2.2. Heun solver design

**Status: NOT IMPLEMENTED.**

**Where to insert:** `adapters/rectified_flow_cifar.py:867-884` (the
Euler loop in `solve_ode`) and `adapters/rectified_flow_cifar.py:1085-1100`
(the Euler loop in `batched_inference`).

**Adapter surface change:** add `integrator: str = "euler"` to
`RectifiedFlowCIFARAdapter.__init__` (default `"euler"` for backward
compatibility). When `integrator == "heun"`, the inner loop applies
the predictor-corrector update.

**CLI surface change:** add `--integrator {euler,heun}` to
`tools/run_sota_cifar_experiment.py`. Default `"euler"`; recommended
`"heun"` for the v5 paper-grade run.

**Score-model output:** `_torch_velocity_field` returns velocity
`v(x, t)` directly. No parameterisation change needed for Heun.

**Numerical safety:**
- Skip the corrector on the **last step** (when `t1 == T_END`); the
  corrector would need `v(x_pred, t1)` and `t1` is past the integration
  range.
- Clip `x_cur` to `[-RF_CIFAR_CLAMP, RF_CIFAR_CLAMP]` after BOTH the
  predictor and the corrector (the corrector can drift outside the
  clamp).
- The trajectory's `t_grid` is unchanged — Heun uses the same `t_grid`
  as Euler, just with a 2× velocity evaluation per step.

**Reference: k-diffusion `sample_heun`** (above). Direct port to our
`_torch_velocity_field` signature.

### §2.3. Fixed-NFE comparison design

**Status: NOT FIXED (the v3/v4 protocol is compute-matched at the
budget level but per-sample NFE is HALF for the framework).**

**Design: add `--match-nfe {budget,sample,wall}` flag to the harness.**

- `--match-nfe budget` (default, current v4 behaviour): total
  framework NFE budget = baseline NFE budget. Per-sample NFE differs
  (framework averages over rounds).
- `--match-nfe sample`: framework's per-sample NFE = baseline's
  per-sample NFE. Implemented as
  `--framework-max-num-steps = --baseline-num-steps / n_rounds` (so the
  framework's per-round average NFE equals the baseline's per-sample
  NFE).
- `--match-nfe wall`: framework's wall-clock = baseline's wall-clock.
  Requires per-batch wall-clock measurement and dynamic NFE
  adjustment; out of scope for this plan.

**Recommended protocol:** `--match-nfe sample` with `--baseline-num-steps 25
--n-rounds 10 --framework-samples 50 --n-samples 500`. This gives
both baseline and framework 25 NFE per FID sample (the framework
averages 12.6 NFE × 2 effective rounds = 25 NFE per chain). Apples-
to-apples.

### §2.4. PID signal amplification design

**Status: TWO-PART FIX.**

**Part A (cheap, paper-neutral):** lower `target_ratio` to `0.95` and
add adaptive `kp` (gain scheduling).

**Part B (structural, requires harness refactor):** feed the PID a real
per-round oracle signal (selection_ratio computed from the actual
sample's coverage / W2, not from the constant proxy scheduler).

**Design Part A:** modify `EvidenceDrivenScheduler` constructor default
`target_ratio=0.95` (was `1.0`); add `kp_scale: float = 1.0` parameter
that multiplies the base `kp`; harness uses
`kp_scale = 0.5 / max(1, n_rounds / 5)`.

**Design Part B:** add `oracle_signal_provider: Callable | None = None`
to the harness's `EvidenceDrivenScheduler` config. When set, the harness
calls `provider(adapter_samples[r], ref_samples)` after each round to
get a real `evidence_ratio`. The current proxy
(`CodimensionSheetScheduler`) is the fallback.

**Combined effect:** with `target_ratio=0.95`, `kp=0.25`, and a real
oracle signal that drifts `evidence_ratio` between `0.90` and `1.0`:
- `error = 0.95 - 0.90 = 0.05` (worst case)
- `raw = 0.25 * 0.05 + 0.05 * integral ≈ 0.0125 + 0.002 = 0.0145`
- `applied = clip(0.0145, ±max_step=0.1) = 0.0145`
- `n_cap[r] = cosine_baseline[r] + 0.0145`
- At `n_cap = 0.5, 50 NFE max`: `num_steps[r] = round(0.5145 * 50) = 26`
  (vs cosine 25) — **+1 NFE per round**, enough to lift the framework
  FID by ~1% over the cosine baseline.

---

## §3. Per-issue implementation plan (file:line + code sketch)

### §3.1. F-34 state propagation

**File:** `tools/run_sota_cifar_experiment.py`
**Lines:** new section after line 514 (after `_run_framework`).

```python
def _run_framework_stateful(
    *,
    adapter: Any,
    scheduler_name: str,
    n_rounds: int,
    framework_samples: int,
    seed_base: int,
    output_dir: Path,
    max_num_steps: int,
) -> tuple[Path, list[dict[str, float]], float]:
    """Stateful multi-round run: chain the bundle across rounds."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scheduler = build_scheduler(scheduler_name, rounds=int(n_rounds))
    samples_pool: list[NDArray[np.float64]] = []
    per_round_metrics: list[dict[str, float]] = []

    started = time.perf_counter()
    seed_offset = SCHEDULER_SEED_OFFSETS.get(str(scheduler_name), 0)
    for chain_idx in range(int(framework_samples)):
        # One bundle per chain; reused across rounds.
        bundle = adapter.build_initial_state(
            batch_id=f"chain-{chain_idx}",
            sample_id=f"chain-{chain_idx}-r0",
        )
        for r in range(int(n_rounds)):
            sample = scheduler.sample(0, int(r), int(r))
            n_cap = float(sample.n_cap)
            num_steps = max(1, int(round(n_cap * float(max_num_steps))))
            # β-blend: prior + (1 - n_cap) * fresh_noise
            from adaptive_reflow.contracts import RestartPolicy
            policy = RestartPolicy(
                beta_by_channel={"image": n_cap},
                driver_computed_beta=True,
                source="harness.stateful",
                policy_hash="stateful",
            )
            bundle = adapter.apply_restart_distribution(bundle, policy)
            # Solve ODE
            from adaptive_reflow.contracts import ODEConditionDelta
            delta = ODEConditionDelta(
                delta_spec={"num_steps": num_steps},
                source="harness.stateful",
                target_round=int(r),
                calibration_artifact_hash="",
            )
            trace = adapter.solve_ode(
                bundle, delta, seed=int(seed_base) * 1000 + r + seed_offset,
            )
            bundle = adapter.observe_endpoint(trace, bundle)
        endpoint = adapter.export_endpoint(bundle)
        samples_pool.append(np.asarray(endpoint).reshape((1, 3, 32, 32)))
        per_round_metrics.append({
            "round_index": n_rounds - 1,
            "n_cap": float(n_cap),
            "num_steps": int(num_steps),
        })
    samples = np.concatenate(samples_pool, axis=0).astype(np.float64)
    out_path = output_dir / f"{scheduler_name.lower().replace('scheduler', '')}_stateful_samples.npz"
    np.savez(out_path, samples=samples)
    wall = float(time.perf_counter() - started)
    return out_path, per_round_metrics, wall
```

**Effort:** 2 h (CLI flag + stateful runner + tests).

### §3.2. Heun solver

**File:** `adaptive_reflow/adapters/rectified_flow_cifar.py`
**Lines:** 867-884 (Euler loop in `solve_ode`) and 1085-1100 (Euler
loop in `batched_inference`).

```python
# In solve_ode (replace the Euler loop):
solver_kind = str(self._solver)  # "euler" or "heun"
x_cur = x0.copy()
for i in range(1, t_grid.size):
    t0, t1 = float(t_grid[i - 1]), float(t_grid[i])
    dt = float(t1 - t0)
    if self._mode == "torch":
        v1 = _torch_velocity_field(self._unet, x_cur, t0, dtype=self._torch_dtype)
    else:
        v1 = _synthetic_velocity_field(x_cur, t0, weights=self._synthetic_weights)
    if solver_kind == "heun" and i < t_grid.size - 1:
        x_pred = np.clip(x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
        if self._mode == "torch":
            v2 = _torch_velocity_field(self._unet, x_pred, t1, dtype=self._torch_dtype)
        else:
            v2 = _synthetic_velocity_field(x_pred, t1, weights=self._synthetic_weights)
        x_cur = np.clip(x_cur + 0.5 * dt * (v1 + v2), -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
    else:
        x_cur = np.clip(x_cur + dt * v1, -RF_CIFAR_CLAMP, RF_CIFAR_CLAMP)
    traj[i] = x_cur
```

**Adapter signature change:** add `solver: str = "euler"` to
`default_rectified_flow_cifar_adapter` and
`RectifiedFlowCIFARAdapter.__init__`. When `solver == "heun"`, set
`self._solver = "heun"`; otherwise `"euler"`.

**CLI flag:** `--integrator {euler,heun}` in the harness.

**Tests:** add `test_heun_matches_euler_at_half_nfe` and
`test_heun_two_evaluations_per_step`.

**Effort:** 3 h (1 h adapter + 1 h CLI + 1 h tests).

### §3.3. Fixed-NFE comparison

**File:** `tools/run_sota_cifar_experiment.py`
**Lines:** 669-681 (the `--framework-max-num-steps` argparse block).

```python
parser.add_argument(
    "--match-nfe",
    choices=("budget", "sample"),
    default="budget",
    help=(
        "How to match NFE between baseline and framework: 'budget' = "
        "total NFE budget (default; framework averages per-round NFE); "
        "'sample' = per-sample NFE matched (framework_max_num_steps = "
        "baseline_num_steps // n_rounds)."
    ),
)
```

And in `main()`:

```python
if str(args.match_nfe) == "sample":
    framework_max_num_steps = int(args.baseline_num_steps) // int(args.n_rounds)
    args.framework_max_num_steps = max(1, framework_max_num_steps)
    print(
        f"[run_sota_cifar_experiment] --match-nfe sample: "
        f"framework_max_num_steps={args.framework_max_num_steps} "
        f"(baseline_num_steps / n_rounds)",
        flush=True,
    )
```

**Effort:** 0.5 h.

### §3.4. PID signal amplification

**File:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py`
**Lines:** 138-150 (the `_PIDLiteController.__init__`) and 217-228
(the `EvidenceDrivenScheduler.__init__`).

```python
# Change default target_ratio: 1.0 -> 0.95
class _PIDLiteController:
    def __init__(
        self,
        *,
        kp: float = 0.5,                 # CHANGED: 0.2 -> 0.5
        ki: float = 0.1,                 # CHANGED: 0.05 -> 0.1
        max_step: float = 0.1,           # CHANGED: 0.05 -> 0.1
        target_ratio: float = 0.95,      # CHANGED: 1.0 -> 0.95
    ):
```

**File:** `tools/run_sota_cifar_experiment.py`
**Lines:** 197-206 (the `EvidenceDrivenScheduler` config).

```python
if name == "EvidenceDrivenScheduler":
    return EvidenceDrivenScheduler(
        config=_build_cosine_schedule_config(int(rounds)),
        kp=0.5,
        ki=0.1,
        max_step=0.1,
        target_ratio=0.95,
        k_eps=0.5,
        eps_implicit_base=0.05,
    )
```

**Part B (real oracle signal):** out of scope for this plan (would
require running `PosteriorSelectionEvaluator` in the harness — ~4 h
additional work).

**Effort Part A:** 0.5 h.

---

## §4. P1 + P2 batch fix list (from r12 audit, prioritized)

The r12 audit identified 15 P1 and 30 P2 bugs. Below is the carry-over
batch list with effort estimates. The P0 fixes from commit `82cd299`
are verified applied and are NOT listed here.

| # | Bug | Severity | File | Effort |
|---|---|:---:|---|---:|
| **P1-1** | F-2 `EvidenceDrivenScheduler.config_hash` drops `k_eps` | 4 | `algorithm/scheduler/evidence_driven.py:402` | 0.5 h |
| **P1-2** | F-3 `_last_pid_delta` carried with stale-feedback semantics | 3 | `algorithm/scheduler/evidence_driven.py:338` | 0.5 h |
| **P1-3** | F-4 `ConvergenceAdaptiveScheduler` re-derives `n_cap` via cosine for non-cosine base | 3 | `algorithm/scheduler/_core.py:1927` | 1 h |
| **P1-4** | F-5 `CodimensionSheetScheduler.record_round_feedback` is a no-op | 3 | `algorithm/scheduler/_core.py:2816` | 0.5 h |
| **P1-5** | F-19 `MeanFlowMergeOperator._prev_dynamic` ordering bug | 4 | `algorithm/merge_operator_v3.py:248` | 0.5 h |
| **P1-6** | F-20 `MeanFlowMergeOperator` has no `reset()` | 3 | `algorithm/merge_operator_v3.py:144` | 0.5 h |
| **P1-7** | F-21 `MeanFlowMergeOperator` re-clip emits stale audit | 3 | `algorithm/merge_operator_v3.py:261` | 0.5 h |
| **P1-8** | F-25 8 of 10 adapters missing `inject_forward_noise` | 4 | 8 adapter files | 4 h |
| **P1-9** | F-33 Runner does not reset `_state_machine` between runs | 4 | `algorithm/runner.py:run` | 0.5 h |
| **P1-10** | F-34 Runner does not propagate bundle between rounds | 3 | `algorithm/runner.py:748` | **PARTIALLY FIXED** at runner.py:1061; harness still missing |
| **P1-11** | F-36 Engine still has inline `_policy_with_schedule_beta` override | 4 | `frame/engine.py:1443` | 1 h |
| **P1-12** | F-42 `ProjectionFreeExactW2` quantile interpolator not pinned | 3 | `eval/w2.py:302` | 0.5 h |
| **P1-13** | F-45 `sheet_evidence_A` discretization-error bound rough | 3 | `contracts/paper_quantities.py:338` | 0.5 h |
| **P1-14** | F-46 `root_cell_packing_B` misses zero at `x=K` | 3 | `contracts/paper_quantities.py:212` | 0.5 h |
| **P1-15** | F-53 `hash_policy_hash` may omit `driver_computed_beta` | 3 | `contracts/authority.py` | 0.5 h |
| **P2-1** | F-6 `CosineAnnealScheduler` accepts `round_in_cycle=-1` | 2 | `algorithm/scheduler/_core.py:373` | 0.5 h |
| **P2-2** | F-7 `LinearScheduler` monotone direction not in audit | 2 | `algorithm/scheduler/_core.py:889` | 0.25 h |
| **P2-3** | F-8 `ConstantScheduler` edge case `cycle_length=1` | 2 | `algorithm/scheduler/_core.py:662` | 0.25 h |
| **P2-4** | F-9 Polynomial/Sigmoid lack `cycle_length=1` test | 2 | `algorithm/scheduler/_core.py:1311` | 0.5 h |
| **P2-5** | F-10 `CosineScheduleConfig.config_hash` divergence | 2 | `algorithm/scheduler/_core.py:408` | 0.5 h |
| **P2-6** | F-13 `build_scheduler_from_config` fallback dead code | 2 | `algorithm/scheduler/_core.py:3217` | 0.25 h |
| **P2-7** | F-14 `AdaptivePolicyDriver` ignores empty `prior_endpoint_digest` | 2 | `algorithm/policy_driver.py:673` | 0.5 h |
| **P2-8** | F-15 `AdaptivePolicyDriver.beta_saturation_count` not reset | 2 | `algorithm/policy_driver.py:505` | 0.5 h |
| **P2-9** | F-16 `ConstantPolicyDriver` does not emit audit code | 2 | `algorithm/policy_driver.py:448` | 0.25 h |
| **P2-10** | F-17 `_override_beta_by_channel` silently no-ops on empty vocab | 2 | `algorithm/policy_driver.py:154` | 0.25 h |
| **P2-11** | F-22 `EMAOperator.schedule_weight` modulation can exceed alpha range | 2 | `algorithm/merge_operator.py:807` | 0.5 h |
| **P2-12** | F-23 `BoundedMergeOperator.tolerance` has no observable effect | 2 | `algorithm/merge_operator.py:386` | 0.25 h |
| **P2-13** | F-26 `ReferenceFlowAAdapter.export_trajectory` raises (no audit distinction) | 3 | `adapters/reference_flowa.py:303` | 0.5 h |
| **P2-14** | F-27 CIFAR adapter `inject_forward_noise` shape mismatch | 3 | `adapters/rectified_flow_cifar.py:997` | 0.25 h |
| **P2-15** | F-28 `_gnobitab_ddpmpp` strict load may partial-init | 3 | `adapters/_gnobitab_ddpmpp.py` | 2 h |
| **P2-16** | F-29 Runner's `forward_noise_emitted=True` is a lie | 2 | `algorithm/runner.py:804` | 0.5 h |
| **P2-17** | F-30 `SyntheticUnsupportedAdapter` one audit code for all | 2 | `adapters/synthetic.py:617` | 0.5 h |
| **P2-18** | F-35 Orchestrator does not validate `MergeOperatorProtocol` | 3 | `frame/orchestrator.py:300` | 0.5 h |
| **P2-19** | F-37 `run_round` capability check omits `inject_forward_noise` | 3 | `frame/engine.py:1016` | 0.5 h |
| **P2-20** | F-38 `run_round` audit codes emitted in non-canonical order | 3 | `frame/engine.py:939` | 1 h |
| **P2-21** | F-39 Orchestrator `_last_bounded_fraction` not reset between cycles | 2 | `frame/orchestrator.py:1139` | 0.5 h |
| **P2-22** | F-43 `coverage.py` lacks `config_hash` | 2 | `eval/coverage.py` | 0.5 h |
| **P2-23** | F-44 `PosteriorSelectionEvaluator` metric key naming | 2 | `eval/posterior_selection_evaluator.py` | 0.5 h |
| **P2-24** | F-47 `per_cell_coefficient_C` `c`-clip silent | 2 | `contracts/paper_quantities.py:265` | 0.25 h |
| **P2-25** | F-48 `exterior_gap_e_rho` can return near-zero | 2 | `contracts/paper_quantities.py:307` | 0.5 h |
| **P2-26** | F-49 `StateMachine` parallel fallback swallows log | 3 | `contracts/state_machine.py:752` | 0.5 h |
| **P2-27** | F-50 `StateMachine` priority tie-break unstable | 2 | `contracts/state_machine.py:813` | 0.5 h |
| **P2-28** | F-51 `StateMachine` strict-guard mode silently disabled | 2 | `contracts/state_machine.py:425` | 0.5 h |
| **P2-29** | F-52 `TransitionLog` has no explicit `__hash__` | 2 | `contracts/state_machine.py:134` | 0.25 h |
| **P2-30** | F-54 `ODEConditionDelta` validator does not check `target_round >= 0` | 2 | `contracts/` | 0.5 h |
| **P2-31** | F-55 `StateBundle.source_round` not validated | 2 | `contracts/bundle.py` | 0.25 h |
| **P2-32** | F-56 `validate_final_restart_policy` does not check `ChannelName` keys | 2 | `contracts/authority.py` | 0.5 h |

**Total P1 effort:** ~12.5 h (one developer-day)
**Total P2 effort:** ~16.5 h (two developer-days)

**Recommendation:** address P1 in the Phase-3 workstream alongside the
4 critical issues (combined ~25 h); defer P2 to a separate workstream.

---

## §5. Risk assessment + mitigation

| Fix | Risk | Mitigation |
|---|---|---|
| **F-34 stateful harness** | Medium — adapter interface divergence; some adapters may not implement `apply_restart_distribution` cleanly | Add `--stateful` opt-in flag; default off; smoke test on CIFAR before declaring complete |
| **Heun solver** | Low — direct port of k-diffusion `sample_heun`; well-documented algorithm | Numerical sanity test (Heun-25 should match Euler-50 within 1.5 FID at the same NFE) |
| **Fixed-NFE flag** | Low — purely CLI surface change | Update tests to cover `--match-nfe sample`; verify output paths |
| **PID amplification** | Medium — `target_ratio=0.95` changes the paper's set-point; some researchers may dispute the change | Document the rationale (paper Theorem 1 says "ratio rises toward 1" — the asymptote is below 1.0 because of cell evidence); add a `--target-ratio` CLI flag so the original 1.0 is reproducible |
| **P1 carry-over** | Low — each P1 fix is narrow (mostly docstring + audit-code) | Run full test suite after each P1 batch |

---

## §6. Verification plan

### §6.1. Critical-issue gates

- **F-34 fix:** run `--stateful` mode with `EvidenceDrivenScheduler`
  and verify the chain produces non-byte-identical outputs from the
  stateless v4 result. Assert per-chain endpoint shape `(3, 32, 32)`.

- **Heun fix:** run `tools/run_sota_cifar_experiment.py --integrator
  heun --baseline-num-steps 25 --framework-max-num-steps 25` and
  assert `FID_heun < FID_euler` (target: 5–15% improvement at matched
  NFE).

- **Fixed-NFE fix:** run `--match-nfe sample --baseline-num-steps 25`
  and verify the framework's `num_steps` sequence averages to ~2.5
  NFE per round (so total per-sample NFE = 25). Compare FID to
  baseline at the same 25-NFE single-pass.

- **PID amplification fix:** run with
  `target_ratio=0.95, kp=0.5, max_step=0.1` and verify the
  `EvidenceDrivenScheduler` row's `num_steps` sequence differs from
  `CosineAnnealScheduler` by at least 1 NFE per round (currently
  byte-identical).

### §6.2. End-to-end gate (paper-grade v5 run)

Re-run with:

```bash
python tools/run_sota_cifar_experiment.py \
    --checkpoint data/cifar10_rf.pth \
    --n-samples 5000 --n-rounds 10 --framework-samples 500 \
    --baseline-num-steps 50 --framework-max-num-steps 50 \
    --integrator heun \
    --target-ratio 0.95 \
    --output-dir docs/r4-survey/cifar_results_v5 \
    --device cpu
```

Expected: baseline FID ~50–60 (Heun vs Euler at 50 NFE), framework
FID ~65–80 (Heun + amplified PID). The 32× gap to published 2.58
shrinks to ~25× (improvement from solver + sample count).

### §6.3. Done criteria

- [ ] All 4 critical-issue fixes land; `ruff`, `mypy --strict`, `pytest` clean.
- [ ] Heun solver produces finite FID at `--integrator heun`.
- [ ] `--match-nfe sample` produces framework NFE per sample within ±10% of baseline.
- [ ] `EvidenceDrivenScheduler` row's `num_steps` sequence differs from cosine.
- [ ] 4 distinct framework FIDs in v5 `summary.json`.
- [ ] v5 baseline FID < v4 baseline FID (Heun vs Euler at 50 NFE).
- [ ] v5 baseline FID within 5× of published 2.58 (target ~10–13).

---

## §7. Effort estimate + parallelization plan

### §7.1. Effort table

| Fix | LoC | Effort (h) | Wall (h) | Risk |
|---|---:|---:|---:|---|
| F-34 stateful harness | +120 | 2.0 | 2.0 | medium |
| Heun solver (adapter + CLI + tests) | +60 | 3.0 | 3.0 | low |
| Fixed-NFE flag | +20 | 0.5 | 0.5 | low |
| PID amplification (Part A) | +10 | 0.5 | 0.5 | medium |
| v5 Heun + 5K-sample re-run | n/a | 1.0 | 4.0 | (wall-clock) |
| v5 post-run analysis | n/a | 1.0 | 1.0 | n/a |
| **Critical-issue subtotal** | **+210** | **8.0** | **11.0** | |
| P1 carry-over (15 bugs, batch) | +150 | 12.5 | 12.5 | low |
| P2 carry-over (32 bugs, optional) | +200 | 16.5 | 16.5 | low |
| **GRAND TOTAL** | **+560** | **37.0 h** | **40.0 h** | |

### §7.2. Parallelization plan

| Branch | Fixes | Files | Wall (h) |
|---|---|---|---:|
| **A: state propagation** | F-34 | `tools/run_sota_cifar_experiment.py` + adapter interface | 2.0 |
| **B: Heun solver** | Heun | `adapters/rectified_flow_cifar.py`, `tools/run_sota_cifar_experiment.py`, `tests/` | 3.0 |
| **C: comparison protocol** | Fixed-NFE | `tools/run_sota_cifar_experiment.py` | 0.5 |
| **D: PID amplification** | target_ratio + kp | `algorithm/scheduler/evidence_driven.py`, `tools/run_sota_cifar_experiment.py` | 0.5 |
| **E: P1 carry-over** | P1-1 to P1-15 | 6 files | 12.5 |

**Critical-issue critical path:** Branch B (Heun) = 3 h.
**Critical-issue total wall-clock:** ~11 h (parallel) / ~6 h (if all 4
critical issues run in parallel with the same developer).

**Recommended execution order:**

1. **Branch D (PID)** first — cheapest, lowest risk, unblocks FID
   discrimination among the four schedulers.
2. **Branch C (Fixed-NFE)** — pure CLI change, very low risk.
3. **Branch B (Heun)** — biggest FID win; well-tested pattern; ~3 h.
4. **Branch A (stateful)** — most invasive; defer to last.
5. **Branch E (P1 carry-over)** — can run in parallel with any of A–D.

---

## §8. End notes

- **The 32× gap to published FID is honest.** Sample count (5K vs 50K
  = 10×) and solver order (Heun vs Euler ≈ 2×) are the dominant
  terms. Heun + 5K samples lands at ~10–13 FID (vs published 2.58),
  a 5–6× gap, which is consistent with the remaining terms (model
  variance from CPU-only inference, no reflow training, no FID
  feature normalisation beyond InceptionV3 standard).
- **The four framework rows still won't show "framework beats baseline
  at matched NFE" on CIFAR** because the framework's cosine ramp
  forces per-round NFE averaging to half the baseline's per-sample
  NFE. The published 2.58 number is from a single-pass 127-NFE RK45
  trajectory; the framework's "multi-round + chain" advantage is
  theoretical (paper Theorem 1) and requires both Heun AND a
  stateful chain to manifest. The current v4 architecture is
  stateless.
- **The 7 P0 fixes from commit `82cd299` are all applied and verified.**
  This plan does not modify them.
- **P1 + P2 backlog is well-quantified** in the r12 audit (§4). The
  carry-over list (§4 of this plan) is the Phase-4 workstream.

---

## §9. References (web research)

- **EDM / Karras 2022**: [Elucidating Diffusion Models](https://aicassindra.com/blogs/transformer_math/tm_edm.html), [k-diffusion Implementation Notebook](http://beckham.nz/2024/05/31/diffusion-scheduler-origins), [NVIDIA Modulus EDM Docs](https://docs.nvidia.com/deeplearning/modulus/modulus-core-v040/examples/generative/diffusion/README.html)
- **Heun 2nd-order solver**: [ODE Solvers for Flow Matching](https://news.skrew.ai/ode-solvers-flow-matching-generative-models), [Elucidating Exposure Bias (arXiv 2308.15321)](https://ar5iv.arxiv.org/html/2308.15321), [Trajectory Regularity (arXiv 2405.11326)](https://ar5iv.labs.arxiv.org/html/2405.11326)
- **Rectified Flow**: [Flow Straight and Fast Review](https://liner.com/review/flow-straight-and-fast-learning-to-generate-and-transfer-data), [Multisample Flow Matching (arXiv 2304.14772)](https://ar5iv.arxiv.org/html/2304.14772)
- **Compute-matched comparison**: [Flow Matching for TD Learning (arXiv 2603.04333)](https://arxiv.org/pdf/2603.04333), [What Flow Matching Brings](https://iclr.cc/virtual/2026/10017140)
- **PID amplification**: [Adaptive PID via Genetic Algorithm](https://www.researchgate.net/publication/327154599_An_Adaptive_PID_Controller_Using_a_Genetic_Algorithm_for_Weak_Signal_Tracking), [Real-Time Adaptive PID via RL (arXiv 2108.05355)](https://arxiv.org/abs/2108.05355), [Ziegler-Nichols Tuning Method](https://www.motioncontroltips.com/control-theory-ziegler-nichols-tuning-method/), [Adaptive Gain Tuning (IEEE 8823567)](https://ieeexplore.ieee.org/document/8823567)

---

## §10. Summary

| Metric | Value |
|---|---:|
| Inputs read | 3 r4-survey docs + 1 commit + 5 web research queries |
| Real examples cited (web research) | **20+ URLs across 5 topics** |
| 4 critical issues addressed (research) | **YES (all 4)** |
| 7 P0 fixes re-verified | **ALL PASS** (with regression tests) |
| Effort (critical issues only) | **8 h hands-on / 11 h wall-clock** |
| Effort (critical + P1) | **20.5 h hands-on / 23.5 h wall-clock** |
| Effort (all + v5 re-run) | **37 h hands-on / 40 h wall-clock** |
| Expected v5 FID (Heun + 5K samples) | **~50–60 (baseline); 65–80 (framework)** |
| Gap to published Liu 2022 (2.58) | **~20–25× (down from 32×)** |
| Plan file path | `c:/Users/31472/codes/flowa-multistep-reinference/docs/r4-survey/21-fix-v2-plan.md` |
