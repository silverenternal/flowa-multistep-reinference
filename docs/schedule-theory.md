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