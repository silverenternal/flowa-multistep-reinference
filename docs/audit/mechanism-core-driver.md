# Mechanism — what the core driver actually does, and why it raises the ceiling

**Date:** 2026-10-23
**Status:** reading note. No code changed, no experiment run. It corrects the
mechanism statement I had been carrying (and used to plan GAP-78).
**Scope:** `adaptive_reflow/algorithm/runner/runner.py`,
`adaptive_reflow/frame/engine.py`,
`adaptive_reflow/algorithm/scheduler/protocols.py`,
`adaptive_reflow/algorithm/nfe_allocation.py`,
`adaptive_reflow/adapters/{mnist_fm,lineageflow}.py`.

---

## 0. The one-sentence version

The driver does **not** integrate better. It spends the same NFE on a
*different distribution*: it re-noises the endpoint back to the path time
`t = m`, re-integrates only `[m, 1]`, and does that `R` times, so the composite
map is a contraction applied `R` times instead of one pass over `[0, 1]`.

That is why "run the baseline with more steps" is not a threat: the single-pass
sampler is already converged (3 steps on MNIST, §2), so its plateau is a
property of the distribution it produces, not of the step count.

## 1. The chain, in code

1. **Capacity → memory.** The scheduler emits `n_cap`; the engine sets
   `beta = n_cap`, and `memory_fraction()` returns `1 − n_cap`
   (`algorithm/scheduler/protocols.py:105-115`; the `beta = n_cap` override is
   `frame/engine.py:1794-1830`).
2. **Restart state is the path state at `t = m`.**
   `apply_restart_distribution` builds
   `x_m = m · x_prior + (1 − m) · ε`, `ε ~ N(0, I)`
   (`adapters/mnist_fm.py:705-710`). Under `x_t = (1−t)x_0 + t x_1` this is
   *exactly* the path state at `t = m` — the comment at
   `adapters/mnist_fm.py:815-820` says so, and that is what GAP-56 fixed.
3. **The round integrates `[m, 1]`, not `[0, 1]`.**
   `solve_ode` reads `t0` from the condition (`adapters/mnist_fm.py:821-830`);
   under `--restart-t0-mode memory` the driver sets `t0_r = 1 − beta_r = m`
   (`scripts/wave191_p3_mnist_sweep.py:181-185`).
4. **NFE is reallocated, not increased.** `nfe_steps_for_evidence` splits a
   *fixed* total NFE across rounds ∝ `1/eps` with an 8× cap
   (`algorithm/nfe_allocation.py:64-140`), so the low-eps terminal refinement
   rounds get the steps and the high-noise early round gets few. Total NFE is
   preserved exactly.
5. **Rounds compose.** `observe_endpoint` feeds the endpoint to the next
   round's `apply_restart_distribution` (`frame/engine.py:1876-1906` calls
   restart, compose, `solve_ode`, observe).

## 2. Why it is faster

At a fixed total NFE the budget is concentrated where the endpoint is decided:

* the `[0, m]` segment is traversed **once** (round 0), not `R` times;
* the terminal region `[m, 1]` is traversed `R` times, and the `1/eps` skew
  gives those passes most of the steps;
* each pass starts from a state that is already a mixture of a real endpoint
  and noise, so the model never re-walks the noise-dominated early region.

The result is the same quality at fewer NFE, or better quality at the same NFE.
It is a **compute-reallocation** claim, not a "we integrate more accurately"
claim.

## 3. Why the ceiling rises — and why more steps cannot

GAP-64 measured the decisive fact: on `production` the single-pass FID is flat
from NFE=3 to NFE=100 (**11.1035 → 11.0675, 0.33 %**), and on `w16e1_5k`
**26.9258 → 26.7300 (0.73 %)**. The RK4 sampler is converged at three steps.
There is **no truncation error left to remove**, so the baseline's plateau is
the error of the distribution the single pass produces. Adding steps moves
nothing; only changing the distribution moves it.

The restart changes the distribution. Measured on R5c, it is a
variance-shrinkage plus (pre-GAP-76) a mean shift; GAP-76 removed the mean
component (mean ΔFID +7.75 % → −3.34 %), leaving the dispersion term. GAP-64's
sign rule, 4/4 correct:

| checkpoint | base `rho` | framework shrinks to | ΔFID (cosine) |
|---|---:|---:|---:|
| `production` | 0.782 | 0.745 | +8.91 % |
| `w16e1_10k` | 0.752 | 0.508 | +2.47 % |
| `w16e1_60k` | 0.704 | 0.611 | +15.42 % |
| `w16e1_5k` | **1.006** | 0.550 | **−9.65 %** |

Shrinkage helps **iff the base is at or above the data's dispersion**. The one
cell the framework wins is the only over-dispersed base. So the ceiling claim
is precise: the operator can land *below* the single-pass floor, but only where
the base's error has the sign the operator corrects.

## 4. The same statement holds on protein, with a different mechanism

On LineageFlow the gain is not dispersion at all: D-004b measured that the
**init-only** arm reproduces the full framework, so the win comes from the
fresh restart state changing *where the trajectory starts*, i.e. which
sequence basin it lands in. Same theme — the framework changes the distribution
the sampler visits, not the accuracy of a single pass — but a different channel
(initial-condition exploration rather than dispersion).

## 5. What this changes in the plan

1. **GAP-78 was mis-specified.** "Restore the conditional variance
   directionally" is not the lever: GAP-67 already corrected the *input* second
   moment and the output dispersion did not follow (its R4: the map is not a
   scalar dispersion operator). What the table above says is that the operator's
   **sign is fixed by construction** (it always shrinks) while the base's
   dispersion **differs by checkpoint**. A constant `m` therefore cannot win on
   both an over-dispersed and an under-dispersed base. The fix is an
   **inference-time gate**: estimate the base's dispersion from the samples
   themselves and choose `m` (or the round count) so the shrink fires only where
   it helps. GAP-78 is rewritten accordingly.
2. **GAP-84's frontier is the right instrument, with the right reading.** The
   baseline curve is flat because it is converged; dominance therefore shows up
   as a *level* difference, not as a slope difference. The frontier must report
   the plateau and the NFE-to-baseline-plateau number, and must state that the
   baseline's flatness is convergence (GAP-64 §0 fact 2), not a compute limit.
3. **A cell cannot be won by a mechanism tuned on another cell.** The three
   channels are distinct: dispersion (image), initial-condition exploration
   (protein), and per-position identifiability (K7/GAP-70). Each gap must name
   its channel and its inference-time observable.
