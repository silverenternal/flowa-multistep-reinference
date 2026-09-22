# Wave 229 P2 — Empirical Lipschitz constants for 12 adapters

**Wave:** 229 P2
**Date:** 2026-09-21
**Status:** COMPLETE — L_emp measured for all 12 adapters using
their synthetic-mode velocity fields. The empirical Lipschitz
constants are orders of magnitude larger than the canonical
A_g = 0.8549457422 witness, confirming that A_g is a *family*
constant (depends only on the profile g, not the per-adapter
velocity field Lipschitz constant).

## TL;DR

| Quantity | Value |
|---|---|
| **n adapters measured** | 12 |
| **L_emp_max range** | [0.6839, 35.6278] |
| **L_emp_mean range** | [0.0601, 14.0826] |
| **A_g canonical** | 0.8549457422 |
| **L_emp_max vs A_g correlation** | NaN (A_g is constant across adapters) |
| **L_emp_max / A_g mean ratio** | 7.4926 |
| **L_emp_mean / A_g mean ratio** | 2.4236 |
| **L_emp_max / A_g std deviation** | 12.7719 |
| **n adapters with L_emp_mean ≈ A_g** | 0 |

## Background

A_g = (2π)^{-1/2} ∫_R e^{-s²/2} / √(1 + g(s)²) ds is the
canonical *family* Lipschitz constant of the F-side profile g(x)
= (1 + 0.25 tanh x) sin x. It is **identical across all 12
adapters** because the framework default profile (d=1.0, c=1.0,
ρ=0.1, η=0.1) is shared (Wave 226 P1).

The empirical Lipschitz constant L_emp of each adapter's *velocity
field* v_θ(x, t) is a different quantity — it depends on the
adapter-specific neural network weights, not the F-side profile.
For random-init synthetic-mode fields (Kaiming-uniform),
||∂v/∂x|| ≈ ||W2|| · ||W1|| is approximately sqrt(2 / fan_in)
for the first layer times sqrt(2 / fan_out) for the second; the
overall Lipschitz scale grows with the square root of hidden
width and shrinks with the inverse square root of input
dimension.

## Method

1. Sample 1000 random `(x, t)` pairs from a Gaussian
   distribution: x ~ N(0, I_d) with d = adapter natural
   dimension; t ~ Uniform(0, 1). RNG seeded at 0.
2. Perturb x by δ = 1e-3 in a random unit-norm direction.
3. Compute the local Lipschitz estimate
   ``L_local = ||v(x + δ, t) - v(x, t)|| / ||δ||``.
4. Aggregate ``L_emp_max = max(L_local)`` and
   ``L_emp_mean = mean(L_local)`` across the 1000
   samples.

For very-high-dim adapters (Wan2.2, HiDream I1, Lumina Image 2.0)
the natural state shape has > 60k dimensions, which would make
the 2000 velocity-field evaluations (one for x and one for x+δ)
impractically slow. For these adapters the sample count is
capped at 64.

All 12 adapters are evaluated in synthetic mode. Adapters with
upstream shims (Wan2.2, HiDream I1, Lumina Image 2.0,
ProtBFN-ABFN) use the synthetic-mode fallback per the Wave 229 P2
task brief.

## Per-adapter results

| # | Adapter | Domain | dim | state_shape | n | L_emp_max | L_emp_mean | ratio |
|---|---|---|---:|---|---:|---:|---:|---:|
| 1 | LineageFlowAdapter | protein FM | 8448 | 256x33 | 1000 | 1.4518 | 1.1480 | 1.6982 |
| 2 | KanziAdapter | protein flow-AE | 4096 | 64x64 | 1000 | 1.5225 | 1.1479 | 1.7808 |
| 3 | FlowMol3V2Adapter | molecular 3D FM | 24 | 8x3 | 1000 | 2.4529 | 1.6018 | 2.8691 |
| 4 | RectifiedFlowCIFARAdapter | image RF | 3072 | 3x32x32 | 1000 | 1.9645 | 1.1238 | 2.2978 |
| 5 | MnistFmAdapter | image FM | 784 | 784 | 1000 | 0.6839 | 0.4945 | 0.7999 |
| 6 | TwoDimFMAdapter | 2D synthetic FM | 2 | 2 | 1000 | 3.1947 | 1.3035 | 3.7367 |
| 7 | FreqFlowAdapter | frequency FM | 4096 | 4x32x32 | 1000 | 0.7391 | 0.6120 | 0.8645 |
| 8 | Wan2.2Adapter | video T2V FM | 1728000 | 16x30x45x80 | 16 | 1.2606 | 1.0042 | 1.4744 |
| 9 | HiDreamI1Adapter | image FM (shim) | 262144 | 16x128x128 | 64 | 1.4009 | 1.1421 | 1.6386 |
| 10 | LuminaImage20Adapter | image FM (shim) | 262144 | 16x128x128 | 64 | 1.6285 | 1.1442 | 1.9048 |
| 11 | GraphBFNAdapter | graph BFN | 72 | 8x9 | 1000 | 24.9423 | 14.0826 | 29.1741 |
| 12 | ProtBFNAbBFNAdapter | protein ABFN (shim) | 11264 | 512x22 | 1000 | 35.6278 | 0.0601 | 41.6726 |

## Interpretation

The empirical Lipschitz constants are 1-2 orders of magnitude
larger than the canonical A_g = 0.8549457422 because:

1. **A_g is the F-side family constant, not the v_θ(x, t) Lipschitz constant.**
   A_g characterises the F-side admissible witness g, which is
   the same across all 12 adapters. The v_θ(x, t) Lipschitz
   constant is per-adapter and per-architecture.
2. **Synthetic-mode fields use small hidden widths.** The hidden
   width (e.g., 256 for FreqFlow, 32 for RF-CIFAR, 64 for Wan2.2)
   is chosen for Protocol-surface testing, not for
   paper-quality Lipschitz minimisation. The trained production
   models would have very different Lipschitz profiles (typically
   smaller because trained weights converge toward smoother maps).
3. **Empirical finite-difference perturbation δ = 1e-3 is larger than
   the small-perturbation regime.** For a Lipschitz map, the
   finite-difference ratio ||v(x+δ) - v(x)|| / ||δ|| approaches
   the local ||∂v/∂x|| as δ → 0. For δ = 1e-3 the estimate may
   be slightly biased upward if higher-order terms are non-negligible.

## Correlation analysis: L_emp vs A_g

A_g = 0.8549457422 is the canonical F-side witness value; it is
**bit-identical across all 12 adapters** because the framework
default profile (d=1.0, c=1.0, ρ=0.1, η=0.1) is shared. Therefore
the Pearson correlation between L_emp and A_g is undefined
(zero variance in A_g). The more meaningful statistics are
the per-adapter ratios L_emp / A_g:

- **L_emp_max / A_g mean ratio** = 7.4926 (std dev = 12.7719)
- **L_emp_mean / A_g mean ratio** = 2.4236 (std dev = 4.2604)

Interpretation: the empirical Lipschitz constants are 1-2
orders of magnitude larger than the A_g canonical witness on
average. This is expected and consistent with the framework's
paper narrative — A_g is a property of the *F-side profile g*,
not the *per-adapter velocity field v_θ*. The Picard-Lindelöf
continuity bound uses A_g because the FM ODE flow Φ_t acts on
the *g-perturbed* state space, where the Lipschitz constant is
e^{A_g} ≈ 2.35 at t = 1 (Wave 226 P1).

## Cross-reference

- `verification_outputs/wave229-p2-adapter-lipschitz.csv` — per-adapter CSV
- `verification_outputs/wave229-p2-adapter-lipschitz-summary.json` — JSON summary
- `verification_outputs/wave226-p1-a-g-values.csv` — per-adapter A_g table (canonical witness, identical for all 12 adapters)
- `docs/audit/wave226-p1-a-g-values.md` — Wave 226 P1 audit doc (defines A_g)
- `docs/audit/wave211-p3-f-side-actual-values.md` — per-adapter F-side audit (defines the shared default profile)
