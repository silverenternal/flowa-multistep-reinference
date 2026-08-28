# Schedule theory — cosine annealing and its analog to EDM / Nichol-Dhariwal

This page is the one-page reference for the cosine schedule family used by
`adaptive_reflow`'s outer-cycle scheduler. It explains how the closed-form
`n_cap_for_round` mirrors the Nichol-Dhariwal cosine schedule and Karras's
EDM polynomial noise scale, then states the closed form the framework
consumes.

## 1. The closed form

For an outer cycle of length `L` with `n_min`, `n_max`, and round index `r ∈ {0, 1, …, L-1}`,
the canonical cosine schedule's fresh-noise capacity is

```
n_cap(r) = n_min + (n_max − n_min) · (1 − cos(π · r / (L − 1))) / 2
```

with the single-round degenerate edge case (`L == 1`) returning `n_max`
deterministically. The companion memory fraction is the complement

```
memory_fraction(r) = 1 − n_cap(r).
```

This is the closed form
[`adaptive_reflow.schedule.cosine.n_cap_for_round`](../../adaptive_reflow/schedule/cosine.py)
and the constant-time closed form consumed by every
`SchedulerProtocol` implementation in
[`adaptive_reflow.algorithm.scheduler`](../../adaptive_reflow/algorithm/scheduler.py).

## 2. Analogy to Nichol-Dhariwal (arXiv:2102.09672)

Nichol & Dhariwal's "Improved Denoising Diffusion Probabilistic Models"
introduced the cosine noise schedule for diffusion models (Section 3.2,
eq. 8):

```
ᾱ(t) = cos²( (t/T + s) / (1 + s) · π / 2 )
```

with a small offset `s` to prevent `ᾱ` from vanishing too quickly at `t = 0`.
The signal-rate `ᾱ(t)` is monotone-decreasing in `t`; the noise-rate
`β_diff(t)` (their instantaneous noise coefficient, **not** the framework's
`beta_by_channel` restart coefficient) is

```
β_diff(t) = 1 − ᾱ(t) / ᾱ(t−1).
```

The framework's `n_cap(r)` is the same monotone-decreasing curve evaluated
at the round index `r / (L − 1)` and rescaled into the canonical `[n_min,
n_max]` envelope. **The functional form is identical**: a half-cosine
scaled into `[0, 1]`. The frame's `n_cap` plays the role of the
"fresh-noise capacity" the way Nichol-Dhariwal's `1 − ᾱ(t)` plays the
role of the cumulative-noise fraction.

> Nichol, A., Dhariwal, P. (2021). *Improved Denoising Diffusion
> Probabilistic Models.* arXiv:2102.09672.

## 3. Analogy to Karras EDM (arXiv:2206.00364)

Karras et al.'s "Elucidating the Design Space of Diffusion-Based
Generative Models" (EDM) parameterises the forward noise injection as

```
x_t = x_0 + σ(t) · ε,        ε ~ N(0, I),
```

with a polynomial noise scale

```
σ(t) = t
```

(or, in the more elaborate sampling pipeline, a geometric progression
over `t ∈ [σ_min, σ_max]`). EDM's `σ` is the "noise level" used to scale
the standard normal; the framework's `n_cap` plays exactly the same role
when fed to the symmetric forward step

```
state' = state + sqrt(n_cap) · generator.standard_normal(shape).
```

The framework's `SchedulerProtocol.inject_noise` is therefore the EDM
"forward noise injection" closed form, with `n_cap` standing in for
`σ²`. At round `0` with `n_cap = n_max` the framework is at EDM's
`σ_max` (high noise / exploration); at round `L-1` with `n_cap = n_min`
the framework is at EDM's `σ_min` (low noise / refinement). The
coarse-to-fine anneal is the analog of EDM's noise schedule collapse
toward zero.

> Karras, T., Aittala, M., Aila, T., Laine, S. (2022). *Elucidating the
> Design Space of Diffusion-Based Generative Models.* arXiv:2206.00364.

## 4. Why cosine (and not EDM's polynomial)?

Three reasons:

1. **Smooth envelope.** The cosine is C¹ and monotone-decreasing on the
   whole cycle; EDM's geometric progression is only monotone-decreasing
   on `[σ_min, σ_max]` and introduces staircase artefacts at the
   endpoints when the cycle is small.
2. **Single tunable knob.** `n_min` and `n_max` are the only envelope
   knobs; the inner cosine profile is determined by the closed form.
   EDM requires per-call rescaling to a chosen noise range, which adds a
   second source of truth.
3. **Natural round-at-midpoint.** `r = (L-1)/2` lands exactly at the
   midpoint `n_cap = (n_min + n_max) / 2`, mirroring EDM's
   "balanced" round.

The framework nevertheless exposes `PolynomialScheduler`,
`ExponentialScheduler`, and `SigmoidScheduler` so callers who want a
closer EDM-style ramp can swap them in without changing the protocol
surface.

## 5. Capacity ↔ memory

The framework's canonical transform is

```
memory_fraction = 1 − n_cap
```

so a high-capacity round (large `n_cap`) carries a low memory
fraction (lots of fresh noise, exploratory); a low-capacity round
(small `n_cap`) carries a high memory fraction (preserve the prior,
refine). This is the engine-side override
[`_policy_with_schedule_beta`](../../adaptive_reflow/frame/engine.py)
and the driver-side override
[`ScheduleDerivedPolicyDriver.compute_policy`](../../adaptive_reflow/algorithm/policy_driver.py).

The closed form is byte-identical across both paths; ADR-0010 documents
the canonical chain (`scheduler → driver → runner → engine → adapter`)
and Contract 1.2 documents the dedup invariant
(`driver_computed_beta=True` suppresses the engine's inline override).

## 6. Forward noise injection as the EDM-side symmetric step

`SchedulerProtocol.inject_noise` is the EDM / score-SDE symmetric
forward step. For every round `r`, the runner advances a deterministic
`np.random.Generator` by exactly one `standard_normal` draw so the
per-round injection is reproducible across replays; the runner emits
`FORWARD_NOISE_INJECTED` in the audit trail whenever the call is
made. The reverse step is the engine-side
`apply_restart_distribution` (the convex blend
`memory_fraction · prior + (1 − memory_fraction) · fresh`). Together
they form the round model's symmetric pair — the analog of EDM's
forward / reverse (denoising) steps under the cosine capacity profile.

## 7. References

* Nichol, A., Dhariwal, P. (2021). *Improved Denoising Diffusion
  Probabilistic Models.* arXiv:2102.09672. Section 3.2, eq. 8.
* Karras, T., Aittala, M., Aila, T., Laine, S. (2022). *Elucidating the
  Design Space of Diffusion-Based Generative Models.* arXiv:2206.00364.
  Section 5.2 (forward noise injection) and Section 5.3 (sampling).
* [`docs/adr/0010-cosine-driven-memory-fraction.md`](adr/0010-cosine-driven-memory-fraction.md)
  — the framework's canonical schedule wiring.
* [`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py) —
  the `SchedulerProtocol` definition and all concrete schedulers.
* [`adaptive_reflow/schedule/cosine.py`](../adaptive_reflow/schedule/cosine.py) —
  the closed-form `n_cap_for_round` helper.

## 8. Closed-form expressions — all eight schedulers

The framework ships nine registered `SchedulerProtocol` implementations
(`SCHEDULER_REGISTRY` in
[`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py)
plus [`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py));
the table below lists the **closed form for `n_cap(r)`** of every
implementation that has one. `SequentialScheduler` is excluded
because its `n_cap(r)` is the dispatch of its sub-scheduler's
`n_cap(r - cumulative_offset)` (see
[`docs/sequential-protocol.md`](sequential-protocol.md)).

| Family | Class | Closed form `n_cap(r)` | Monotone? | `n_min`/`n_max`? | Reference |
| --- | --- | --- | :---: | --- | --- |
| `cosine` | `CosineAnnealScheduler` | `n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` | yes | yes | [§1](#1-the-closed-form), [CLM-005] |
| `constant` | `ConstantScheduler` | `n_cap` (constant across `r`) | n/a | n/a (config) | [`scheduler.py:478`](../adaptive_reflow/algorithm/scheduler.py) |
| `linear` | `LinearScheduler` | `n_min + (n_max - n_min) * r / (L - 1)` | yes (slope ≥ 0) | yes | [`scheduler.py:672`](../adaptive_reflow/algorithm/scheduler.py) |
| `exponential` | `ExponentialScheduler` | `n_max * exp(-alpha * r)` | yes | `n_min = 0` implicit | [`scheduler.py:882`](../adaptive_reflow/algorithm/scheduler.py) |
| `polynomial` | `PolynomialScheduler` | `n_min + (n_max - n_min) * (1 - u_r ** power)` where `u_r = r / max(L - 1, 1)` | yes if `n_max > n_min` | yes | [`scheduler.py:1103`](../adaptive_reflow/algorithm/scheduler.py) |
| `sigmoid` | `SigmoidScheduler` | `n_min + (n_max - n_min) * sigmoid(steepness * (u_r - midpoint))` | yes (when `steepness > 0`) | yes | [`scheduler.py:1340`](../adaptive_reflow/algorithm/scheduler.py) |
| `convergence_adaptive` | `ConvergenceAdaptiveScheduler` | `base.sample(r) + shift(r)` where `shift(r)` is the PID-lite output | inherited from `base` | inherited from `base` | [`scheduler.py:1593`](../adaptive_reflow/algorithm/scheduler.py), ADR-0012 |
| `codimension_sheet` | `CodimensionSheetScheduler` | `n_min + (n_max - n_min) * ratio(r)` where `ratio(r) = sheet(r) / (sheet(r) + cell(r))` with `sheet = 1 / max(n_cap_base, eps_implicit)` and `cell = (1 - n_cap_base)^2 / eps_implicit^2` [CLM-006] | inherited from base | inherited | [`scheduler.py:2053`](../adaptive_reflow/algorithm/scheduler.py), ADR-0013 |

All eight closed forms are **pure** with respect to their arguments:
two calls with identical inputs return equal `ScheduleSample` objects.
The single-round degenerate edge case (`cycle_length == 1`) is
handled deterministically by every implementation (returns
`n_max` for the four envelope-anchor families; returns `n_max * exp(0)`
for the exponential family; returns `0.5` for the constant family).

## 9. Comparison to field standards

The schedule-theory literature offers three published closed forms
that map onto the framework's `n_cap(r)` envelope. The table below
aligns the framework's `cosine` (canonical) and `exponential`
(implemented) families with each one; the framework does NOT ship a
direct port of EDM's `sigma(t) = t` polynomial ramp — it ships the cosine
because the cosine is `C^1` and monotone-decreasing on the whole
cycle (no staircase artefacts at the endpoints), which EDM's
geometric progression lacks on small cycles (see [§4](#4-why-cosine-and-not-edms-polynomial)).

| Field standard | Closed form (their notation) | Framework analog | Identical? | Reference |
| --- | --- | --- | :---: | --- |
| **Nichol-Dhariwal cosine** (arXiv:2102.09672, eq. 8) | `alpha_bar(t) = cos^2((t/T + s) / (1 + s) * pi/2)`; `beta_diff(t) = 1 - alpha_bar(t)/alpha_bar(t-1)` | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` | **Yes** (functional form: half-cosine scaled into `[0, 1]`; offset `s = 0`) | [§2](#2-analogy-to-nichol-dhariwal-arxiv210209672) |
| **Karras EDM rho-spacing** (arXiv:2206.00364, §5.2) | `sigma(t) = t` (polynomial); geometric progression `sigma_i = (sigma_max^(1/rho) + i/(N-1) * (sigma_min^(1/rho) - sigma_max^(1/rho)))^rho` | `n_cap(r) = n_min + 0.5 * (n_max - n_min) * (1 - cos(pi * r / (L - 1)))` | **No** (different functional form); cosine is the framework's chosen replacement, not a port | [§3](#3-analogy-to-karras-edm-arxiv220600364), [§4](#4-why-cosine-and-not-edms-polynomial) |
| **SD3 exponential shift** (Esser et al. 2024, §"Shifted schedules") | `sigma(t) = sigma_max * t` shifted so `log(sigma(t)/sigma_max) = -gamma * log(t)` (rectified flow-style log-shift) | `n_cap(r) = n_max * exp(-alpha * r)` | **No** (different parameterisation); the exponential family is a framework analogue, not a port | [`scheduler.py:882`](../adaptive_reflow/algorithm/scheduler.py) |

The "Identical?" column reflects whether the framework's closed form
is **byte-equivalent** to the field standard. The cosine is identical
to Nichol-Dhariwal at the functional level (same half-cosine, same
scaling); the framework's exponential is *not* a port of SD3's
log-shift (it is a raw `exp(-alpha * r)`) but is the closest
single-parameter closed form that respects monotonicity.

> **What this section does NOT claim.** The framework does NOT claim
> to reproduce any of the three field standards' empirical
> performance. The closed forms are aligned at the *direction* level
> (monotone-decreasing `n_cap` over rounds, mapping onto the paper's
> `eps -> 0` direction) but not at the *magnitude* level
> ([CLM-015]). The 18-row ablation in `tools/run_ablation.py` records
> the framework's own empirical behaviour; comparing those numbers to
> a Nichol-Dhariwal or EDM run on the same target is out of scope.

## 10. How to choose a schedule

The decision tree below maps `cycle_length` (the round budget of one
outer cycle) onto a recommended `SchedulerProtocol` family. The
recommendations are derived from the ablation grid in
`tools/run_ablation.py` (see `docs/ABLATION.md` §"New findings:
schedule families (ADR-0012)") and the framework's paper-grounding
ADR (ADR-0013).

```
                       +---------------------------------+
                       |  What is your cycle_length?     |
                       +----------------+----------------+
                                        |
            +---------------------------+---------------------------+
            |                           |                           |
            v                           v                           v
       cycle_length              5 <= cycle_length              cycle_length
       < 5                       <= 10                          > 10
            |                           |                           |
            v                           v                           v
   PolynomialScheduler        CosineAnnealScheduler       +----------------+
   (power=1.0, linear)         (default, n_min=0.0,        | Is there an   |
                                n_max=1.0)                  | external       |
                                - ties or wins              | convergence    |
                                on the canonical            | signal?        |
                                2D-FM target                +----+-----------+
                                [CLM-018]                         |
                                                           +-----+------+
                                                           v            v
                                                       Yes (oracle)   No
                                                           |            |
                                                           v            v
                                                  ConvergenceAdaptive    +---------+
                                                  Scheduler              | L > 20? |
                                                  (base=Cosine,          |         |
                                                   shift_max=0.2)        v         v
                                                  ADR-0012             Yes        No
                                                                       |          |
                                                                       v          v
                                                            CodimensionSheet   CosineAnneal
                                                            Scheduler          Scheduler
                                                            (eps_implicit=     (default)
                                                             0.05, paper-
                                                             aligned)
                                                            [CLM-006]
```

The decision rules:

* **`cycle_length < 5`** — use `PolynomialScheduler(power=1.0)`.
  Cosine with fewer than 5 rounds has no time to anneal (the cosine
  ramp's first quarter is the steepest descent, but on a 4-round
  cycle there is no room for the smooth half-cosine profile to
  distinguish itself from a linear ramp); the linear is the cheapest
  closed form that respects monotonicity.
* **`5 <= cycle_length <= 10`** — use `CosineAnnealScheduler` with
  the default `n_min=0.0, n_max=1.0` envelope. Cosine wins or ties on
  the canonical 2D-FM target in this range [CLM-018].
* **`cycle_length > 10` and convergence signal is available** —
  use `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler(...))`.
  The convergence signal (a per-round oracle metric) lets the
  scheduler shift away from the cosine ramp when the per-round
  evidence is monotone-improving (shift negative, refine earlier) or
  monotone-stalling (shift positive, re-explore). The shift is
  bounded by `[-shift_max, +shift_max]` so the envelope invariant is
  preserved.
* **`cycle_length > 20` and no convergence signal** — use
  `CodimensionSheetScheduler(eps_implicit=0.05)`. This is the
  paper-grounded closed form for paper Theorem 1 magnitude level
  [CLM-006]; the longer cycle gives the Lemma 2 + Lemma 3 closed form
  room to settle.
* **All other cases** — use `CosineAnnealScheduler` with the default
  envelope. The cosine is the recommended default because (a) it is
  the canonical implementation of paper Lemma 2's sheet-tube scaling
  at the direction level [CLM-005]; (b) it ties or wins on the
  canonical 2D-FM target [CLM-018]; (c) it has a single tunable knob
  (the `n_min` / `n_max` envelope anchors).

### 10.1 Defaults matrix cross-reference

The scenario column of [`docs/defaults-matrix.md`](defaults-matrix.md)
mirrors this decision tree:

| Decision-tree branch | Defaults-matrix row |
| --- | --- |
| `cycle_length < 5` (linear) | "Short run" row uses `CosineAnnealScheduler(cycle_length=4)` (the `4`-round cosine is equivalent to a linear on a 4-round cycle because the half-cosine collapses to a line at `L=4`). |
| `cycle_length > 20` paper-aligned | "Long run" row uses `CodimensionSheetScheduler(eps_implicit=0.05)`. |
| Convergence signal available | "Adaptive" row uses `ConvergenceAdaptiveScheduler(base=CosineAnnealScheduler)`. |
| Multi-phase piecewise | "Sequential" row uses `SequentialScheduler([(Cosine, 8), (Expo, 4), (Const, 8)])`. |

The matrix and the decision tree are two views of the same
recommendation set; the matrix is the reader-facing recipe, the
decision tree is the algorithmically-derived branching.

## 11. References (extended)

* Nichol, A., Dhariwal, P. (2021). *Improved Denoising Diffusion
  Probabilistic Models.* arXiv:2102.09672. Section 3.2, eq. 8.
* Karras, T., Aittala, M., Aila, T., Laine, S. (2022). *Elucidating the
  Design Space of Diffusion-Based Generative Models.* arXiv:2206.00364.
  Section 5.2 (forward noise injection) and Section 5.3 (sampling).
* Esser, P., Kulal, S., Blattmann, A., et al. (2024). *Scaling Rectified
  Flow Transformers for High-Resolution Image Synthesis (SD3).*
  arXiv:2403.06306. Section on shifted schedules (the log-shift
  parameterisation).
* [`docs/adr/0010-cosine-driven-memory-fraction.md`](adr/0010-cosine-driven-memory-fraction.md)
  — the framework's canonical schedule wiring.
* [`docs/adr/0012-noise-schedule-survey.md`](adr/0012-noise-schedule-survey.md)
  — the noise-schedule survey ADR (accepts
  `ConvergenceAdaptiveScheduler`; rejects Karras EDM `sigma(t) = t`).
* [`docs/adr/0013-posterior-selection-drives-algorithm.md`](adr/0013-posterior-selection-drives-algorithm.md)
  — the paper-grounded algorithm-layer ADR (introduces
  `CodimensionSheetScheduler`).
* [`docs/defaults-matrix.md`](defaults-matrix.md) — the reader-facing
  defaults matrix (heuristic guide, not a hard guarantee).
* [`docs/sequential-protocol.md`](sequential-protocol.md) — the
  `SequentialScheduler` reference.
* [`adaptive_reflow/algorithm/scheduler.py`](../adaptive_reflow/algorithm/scheduler.py) —
  the `SchedulerProtocol` definition and all concrete schedulers.
* [`adaptive_reflow/algorithm/sequential.py`](../adaptive_reflow/algorithm/sequential.py) —
  the `SequentialScheduler` implementation (P1-2).
* [`adaptive_reflow/schedule/cosine.py`](../adaptive_reflow/schedule/cosine.py) —
  the closed-form `n_cap_for_round` helper.