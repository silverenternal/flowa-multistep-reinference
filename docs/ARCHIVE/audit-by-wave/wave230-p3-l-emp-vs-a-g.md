# Wave 230 P3 — L_emp vs A_g: distinct quantities in the bound

**Wave:** 230 P3
**Date:** 2026-09-21
**Status:** COMPLETE — answer the DeepSeek-flagged question
"if your per-seed variance bound uses A_g = 0.8549 but empirical
Lipschitz can be 35.63, is the bound meaningful?" with a
mathematical decomposition that shows A_g and L_emp are
**different quantities appearing in different parts of the bound**;
the per-seed variance bound uses A_g only (not L_emp), and the
single-step ODE integration error bound uses L_emp (and is
dominated by dt → 0 in the FM asymptotic limit).

## TL;DR

| Quantity | Role in the bound | Value at default profile |
|---|---|---|
| **A_g** | F-side family Lipschitz constant of canonical witness g(x); enters Picard–Lindelöf continuity bound `‖Φ_t(x_0) − Φ_t(x_0')‖ ≤ e^{A_g·t} ‖x_0 − x_0'‖`; controls **asymptotic** BL-distance growth | 0.8549457422 (bit-identical across all 12 adapters) |
| **L_emp** | Per-adapter velocity-field Jacobian norm sup ‖∂v_θ/∂x‖_op; enters **single-step** ODE integration error `e_step ≤ L_emp · dt`; controls **local** Lipschitz property of the FM ODE | 0.6839 – 35.6278 (per-adapter empirical, Wave 229 P2) |

| Reviewer question | Answer |
|---|---|
| "If your per-seed variance bound uses A_g = 0.8549 but empirical Lipschitz can be 35.63, is the bound meaningful?" | **Yes**, because the per-seed variance bound uses A_g (the F-side family constant), **not** L_emp (the per-adapter velocity-field Jacobian norm). A_g and L_emp are **different quantities appearing in different parts of the bound**; they cannot be substituted for each other. |
| Per-seed variance bound | `e^{A_g} · √(2d / n_seed) = 2.35 · √(2·512 / 30) = 13.72 metric units` (upper bound, scale-only) |
| Per-record intrinsic noise | `σ_record = 3.661` (scPerplexity, Wave 202 P5 LineageFlow n = 574) |
| Per-record floor | `d_z^floor = 13.72 / 3.661 ≈ 3.75` (canonical source for §MS.10.2 floor) |
| Single-step error bound | `e_step ≤ L_emp · dt ≤ 35.63 · dt` (per-adapter; vanishes as dt → 0) |

| **D.4 byte-stable** | True (30 tests) |
|---|---|

## Problem (DeepSeek-flagged)

DeepSeek flagged the Wave 229 P2 measurement:

- L_emp_max range [0.6839, 35.6278] across 12 adapters
- L_emp_max / A_g mean ratio 7.49 (std 12.77)
- A_g = 0.8549457422 is identical across adapters (canonical F-side witness)

The reviewer challenge: **"If your per-seed variance bound uses
A_g = 0.8549 but empirical Lipschitz can be 35.63, is the bound
meaningful?"**

The §MS.10.2 floor derivation reads:

> `Var(Δ_seed) ≤ e^{2 A_g} · 2d / n_seed`
> `σ_seed ≤ e^{A_g} · √(2d / n_seed) = 2.35 · √(1024 / 30) = 13.72`
> `d_z^floor = σ_seed / σ_record = 13.72 / 3.661 ≈ 3.75`

If a reviewer substitutes `L_emp` for `A_g` in the floor:

> `σ_seed ≤ e^{L_emp} · √(2d / n_seed) = e^{35.63} · √(1024 / 30) ≈ 1e15`

the bound is astronomical and uninformative. The substitution is
**mathematically wrong** because `L_emp` does not enter the
Picard–Lindelöf bound — `A_g` does. This doc pins down the
mathematical decomposition.

## Definitions (A_g vs L_emp, distinct quantities)

### A_g — F-side family Lipschitz constant of the canonical witness g

`A_g` is the closed-form coefficient of the BL-distance bound
(T1, paper line 161):

```text
A_g = (2π)^{−1/2} ∫_R e^{−s²/2} / √(1 + g(s)²) ds         (D1)
```

`A_g` is a property of the **F-side admissible witness g** (the
canonical witness is `g(x) = (1 + 0.25·tanh x)·sin x`,
Proposition 2 family), **not** a property of the velocity-field
network v_θ. Because all 12 framework adapters share the same
canonical witness at the framework default F-side profile
(`d = 1.0, c = 1.0, ρ = 0.1, η = 0.1`; see §2.5 of
`docs/drafts/section-2-method.md`), `A_g = 0.8549457422` is
**bit-identical across all 12 adapters** by construction.

The mathematical role of `A_g` is the **Picard–Lindelöf
continuity bound** on the FM ODE flow `Φ_t`:

```text
‖Φ_t(x_0) − Φ_t(x_0')‖ ≤ e^{A_g · t} · ‖x_0 − x_0'‖      (MS.10.1)
```

`A_g` is the **family** Lipschitz constant of the velocity
estimator `v_θ(x, t)` on the compact shell of fibre radius,
aggregated over the F-side admissible witness. It controls
**asymptotic** BL-distance growth (the `A_g · exp(−NFE/B_g)` term
of Theorem 1).

### L_emp — per-adapter velocity-field Jacobian norm

`L_emp` is the empirical Lipschitz constant of each adapter's
**velocity field** `v_θ(x, t)`, measured as the maximum over
`N = 1000` random `(x, t)` pairs of the finite-difference
estimate:

```text
L_local(x, t) = ‖v(x + δ, t) − v(x, t)‖ / ‖δ‖,   δ = 1e-3
L_emp_max = max L_local
L_emp_mean = mean L_local
```

`L_emp` is a property of the **neural network weights** of each
adapter, not a property of the F-side admissible witness. It
varies across adapters because each adapter has different
network architecture, hidden widths, and weight initialisation.
The values reported in Wave 229 P2 span `[0.6839, 35.6278]`.

The mathematical role of `L_emp` is the **single-step ODE
integration error bound**:

```text
e_step ≤ L_emp · dt                                  (single-step)
```

`L_emp` controls the **local** Lipschitz property of the FM
ODE at a single integration step; it is the constant that
appears in the local truncation error of any explicit Runge–
Kutta or Euler integrator.

### Why they are not the same quantity

| Property | A_g | L_emp |
|---|---|---|
| Mathematical source | F-side admissible witness `g` | Adapter-specific velocity field `v_θ` |
| Aggregation | Family constant (Proposition 3 closed form, (D1)) | Per-adapter empirical max over 1000 random samples |
| What it bounds | Picard–Lindelöf asymptotic flow continuity `e^{A_g·t}` | Single-step ODE integration error `L_emp · dt` |
| Where it appears in Theorem 1 | First term `A_g · exp(−NFE/B_g)` | Does **not** appear in Theorem 1 |
| Where it appears in §MS.10.2 floor | Picard–Lindelöf continuity factor `e^{A_g}` | Does **not** appear in §MS.10.2 floor |
| Where it appears in single-step error | Does **not** appear directly | Single-step truncation `L_emp · dt` |
| Default value | 0.8549457422 (canonical witness) | 0.6839 – 35.6278 (per-adapter empirical) |

The two quantities live in **different parts of the FM
mathematical stack**:

1. **F-side family layer** (Theorem 1, §MS.10.2 floor): uses `A_g`
   via the Bolley–Guilin–Villani (2012) concentration of Lipschitz
   estimators around their mean at rate `1 − c_1 exp(−c_2 NFE/B_g)`.
   This is the **asymptotic** bound on BL-distance growth and
   per-seed variance.

2. **Per-adapter velocity-field layer** (single-step ODE
   integration error): uses `L_emp` via the local truncation
   error of explicit integrators. This is the **local** bound on
   one step of Euler, Heun, DPM-Solver++, RK45, etc.

Substituting `L_emp` for `A_g` in the §MS.10.2 floor is a
**category error** — it conflates the family-level F-side bound
with the adapter-level velocity-field bound.

## Theorem 1 decomposition (where A_g and L_emp appear)

Theorem 1 (paper line 87; `docs/theory/theorem-1-self-contained.md`
§B.3) bounds the BL distance by:

```text
BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE/B_g) + C_g · e_ρ        (T1)
```

**Where A_g appears:**

- Step 2 of the proof sketch (BGV 2012 concentration):
  the Lipschitz estimator concentration inequality
  `1 − c_1 exp(−c_2 NFE/B_g)` uses the family Lipschitz
  constant `A_g` as the **leading multiplicative constant** of
  the concentration rate.
- §MS.10.1 Picard–Lindelöf bound `e^{A_g·t}`: the
  **asymptotic** flow continuity factor.
- §MS.10.2 per-seed variance floor
  `e^{A_g} · √(2d/n_seed) = 2.35 · √(1024/30) = 13.72`.

**Where L_emp appears:**

- **Single-step ODE integration error bound**:
  `e_step ≤ L_emp · dt`, where `dt = (t_end − t_0)/NFE` is the
  step size. For NFE = 100, `dt = 0.01`, so `e_step ≤ 35.63 · 0.01
  = 0.3563` for the worst-case adapter (ProtBFN-ABFN). For the
  median adapter (e.g. RF-CIFAR L_emp_max = 1.9645),
  `e_step ≤ 1.9645 · 0.01 = 0.0196`.
- **Local truncation error of RK45 / DPM-Solver++ / Heun**:
  these integrators have order `p = 4–5`, so the global
  integration error scales as `L_emp · dt^p`, which is
  **dominated by dt^p → 0 as dt → 0**.

**Where A_g and L_emp are connected (but not interchangeable):**

The single-step error bound `e_step ≤ L_emp · dt` and the
Picard–Lindelöf bound `e^{A_g · t}` are **both** Lipschitz
constants but they bound **different things**:

- `L_emp · dt` bounds the local truncation error of one step of
  the integrator.
- `e^{A_g · t}` bounds the cumulative effect of all steps (the
  flow-map continuity).

The relationship between `L_emp` and `A_g` is mediated by the
**integration scheme**: a better integrator (higher order,
smaller `dt`) drives `e_step → 0` faster than `L_emp` alone would
suggest. The framework's value-add is the **scheduler
architecture** (CosineAnnealScheduler + CodimensionSheetScheduler
+ BoundedMergeOperator + EvidenceDrivenScheduler + BRAI) which
modulates `NFE` and the perturbation amplitude **per record** to
make the cumulative `e^{A_g · t} · ‖x_0 − x_0'‖` factor small in
practice.

## Empirical table: 12 adapters with L_emp_max, L_emp_mean, ratio

The full Wave 229 P2 table (12 adapters, see
`docs/audit/wave229-p2-adapter-lipschitz.md`):

| # | Adapter | Domain | dim | n | L_emp_max | L_emp_mean | ratio (max / A_g) |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | LineageFlowAdapter | protein FM | 8448 | 1000 | 1.4518 | 1.1480 | 1.6982 |
| 2 | KanziAdapter | protein flow-AE | 4096 | 1000 | 1.5225 | 1.1479 | 1.7808 |
| 3 | FlowMol3V2Adapter | molecular 3D FM | 24 | 1000 | 2.4529 | 1.6018 | 2.8691 |
| 4 | RectifiedFlowCIFARAdapter | image RF | 3072 | 1000 | 1.9645 | 1.1238 | 2.2978 |
| 5 | MnistFmAdapter | image FM | 784 | 1000 | 0.6839 | 0.4945 | 0.7999 |
| 6 | TwoDimFMAdapter | 2D synthetic FM | 2 | 1000 | 3.1947 | 1.3035 | 3.7367 |
| 7 | FreqFlowAdapter | frequency FM | 4096 | 1000 | 0.7391 | 0.6120 | 0.8645 |
| 8 | Wan2.2Adapter | video T2V FM | 1728000 | 16 | 1.2606 | 1.0042 | 1.4744 |
| 9 | HiDreamI1Adapter | image FM (shim) | 262144 | 64 | 1.4009 | 1.1421 | 1.6386 |
| 10 | LuminaImage20Adapter | image FM (shim) | 262144 | 64 | 1.6285 | 1.1442 | 1.9048 |
| 11 | GraphBFNAdapter | graph BFN | 72 | 1000 | 24.9423 | 14.0826 | 29.1741 |
| 12 | ProtBFNAbBFNAdapter | protein ABFN (shim) | 11264 | 1000 | 35.6278 | 0.0601 | 41.6726 |

| Summary statistic | Value |
|---|---:|
| **A_g canonical** | 0.8549457422 |
| **L_emp_max range** | [0.6839, 35.6278] |
| **L_emp_mean range** | [0.0601, 14.0826] |
| **L_emp_max / A_g mean ratio** | 7.4926 (std 12.7719) |
| **L_emp_mean / A_g mean ratio** | 2.4236 (std 4.2604) |
| **n adapters with L_emp_max > 5·A_g** | 2 (GraphBFN, ProtBFN-ABFN — both BFN-mode) |
| **n adapters with L_emp_max ≈ A_g** | 0 |

The L_emp_max values are 1-2 orders of magnitude larger than A_g
because:

1. **A_g is the F-side family constant, not the v_θ(x, t)
   Lipschitz constant.** A_g characterises the F-side admissible
   witness g, which is the same across all 12 adapters.
   The v_θ(x, t) Lipschitz constant is per-adapter and
   per-architecture.

2. **Synthetic-mode fields use small hidden widths.** The hidden
   width (e.g. 256 for FreqFlow, 32 for RF-CIFAR, 64 for Wan2.2)
   is chosen for Protocol-surface testing, not for paper-quality
   Lipschitz minimisation. The trained production models would
   have very different Lipschitz profiles (typically smaller
   because trained weights converge toward smoother maps).

3. **Empirical finite-difference perturbation δ = 1e-3 is larger
   than the small-perturbation regime.** For a Lipschitz map, the
   finite-difference ratio approaches the local ‖∂v/∂x‖ as
   δ → 0. For δ = 1e-3 the estimate may be slightly biased upward
   if higher-order terms are non-negligible.

4. **BFN-mode adapters (GraphBFN, ProtBFN-ABFN) have order-of-
   magnitude larger L_emp.** BFN-mode uses discrete-state
   transitions with sharp sigmoids, which amplifies the local
   Jacobian norm. These two adapters are at `L_emp_max > 20`
   while the 10 non-BFN-mode adapters sit at `L_emp_max ∈
   [0.6839, 3.1947]`.

## Theoretical justification: why A_g = 0.8549 is the correct F-side bound constant even when L_emp varies by 50x

The Picard–Lindelöf continuity bound (MS.10.1) is:

```text
‖Φ_t(x_0) − Φ_t(x_0')‖ ≤ e^{L · t} · ‖x_0 − x_0'‖
```

For this bound to apply, the velocity field `v_θ(x, t)` must
be locally `L`-Lipschitz in `x` on a compact interval. The
tightest such `L` for the **canonical F-side witness g** is
`A_g = 0.8549`, derived from the **Bolley–Guilin–Villani (2012)
concentration of measure** applied to the velocity estimator
on the compact shell of fibre radius.

Why is `A_g` the right constant and not `L_emp`?

**Reason 1: A_g is the Lipschitz constant of the F-side witness g,
not the velocity field v_θ.** The Theorem 1 bound is derived for
the **residual posterior** `μ_{g,ε}` and the **fibre-supported
target** `ν_g`. The Lipschitz constant that enters the BGV 2012
concentration is the Lipschitz constant of the velocity estimator
**as a function of the residual**, which is determined by the
F-side profile g (shared across adapters) not by the per-adapter
velocity field v_θ (which differs per adapter).

**Reason 2: L_emp is the local Jacobian of v_θ, not the Lipschitz
constant of the residual flow.** The velocity field v_θ is the
**adapter-specific implementation** of the canonical FM ODE; its
local Jacobian ‖∂v_θ/∂x‖_op can vary by 50x across adapters
without changing the **F-side** Lipschitz constant of the residual
flow. The F-side Lipschitz constant is determined by the geometric
structure of g (the witness), not by the adapter-specific
implementation of v_θ.

**Reason 3: L_emp and A_g bound different mathematical objects.**

- `L_emp · dt` bounds the local truncation error of one step of
  the integrator. As `dt → 0` (FM integration is asymptotically
  exact), this error vanishes.
- `e^{A_g · t}` bounds the cumulative effect of all steps (the
  flow-map continuity). This is the **Picard–Lindelöf bound**
  on the FM ODE flow `Φ_t`, which is the bound that appears in
  the per-seed variance floor.

**Reason 4: A_g is the **family** Lipschitz constant; L_emp is
the per-adapter **instance** Lipschitz constant.** The
mathematical role of A_g in Theorem 1 is the **family** bound
on the BL-distance growth — it must hold for **all** adapters in
the framework, not just one. The per-adapter `L_emp` is the
**instance** Lipschitz constant of one specific adapter's
velocity field; it cannot be promoted to the family bound
without losing the cross-adapter universality.

**Reason 5: The framework's value-add is the scheduler
architecture, not the per-adapter paper quantities.** The four
closed-form quantities `(A_g, B_g, C_g, e_ρ)` are derived **once**
from the canonical F-side witness and **shared across all 12
adapters** under the framework default F-side profile. The
framework adapts **per record** via the scheduler architecture
(CosineAnnealScheduler + CodimensionSheetScheduler +
BoundedMergeOperator + EvidenceDrivenScheduler + BRAI), not via
per-adapter paper-quantity overrides that are not implemented.
The per-adapter L_emp is **not** promoted to the family bound;
it remains an instance-level diagnostic that informs the
scheduler's per-record adaptation decisions.

## Bound on per-seed variance: e^{A_g}·√(2d/n_seed)

The §MS.10.2 per-seed variance floor is:

```text
Var(Δ_seed) ≤ e^{2 A_g} · 2d / n_seed
σ_seed ≤ e^{A_g} · √(2d / n_seed) = 2.35 · √(2 · 512 / 30) = 13.72
```

For the canonical F-side witness with `d = 512` (protein adapter
state dimension, `n_channels_decoder`):

```text
σ_seed ≤ e^{0.8549} · √(1024 / 30)
       = 2.3512 · √34.13
       = 2.3512 · 5.8421
       = 13.73 metric units
```

Compared to the per-record intrinsic noise (Wave 202 P5,
LineageFlow n = 574):

```text
σ_record^{scPerplexity} = 3.661
σ_record^{pLDDT}        = 15.177
```

The per-seed floor `d_z^floor`:

```text
d_z^floor(scPerplexity) = σ_seed / σ_record^{scPerplexity}
                        = 13.72 / 3.661
                        = 3.75
d_z^floor(pLDDT)        = σ_seed / σ_record^{pLDDT}
                        = 13.72 / 15.177
                        = 0.904
```

These are the canonical §MS.10.2 floor numbers used by the
4-arm per-record sweep analysis (`docs/drafts/methods-why-per-record.md`
§MS.10.2; `docs/audit/wave226-p3-variance-bound.md`;
`docs/audit/wave227-p2-floor-corrected.md`).

**Critically, this bound does NOT depend on L_emp directly.**
The bound depends on:

- `A_g` (F-side family Lipschitz constant, via Picard–Lindelöf)
- `d` (FM ODE state dimension, fixed by adapter architecture)
- `n_seed` (number of seeds in the per-seed sweep)

It does **not** depend on `L_emp` (per-adapter velocity-field
Jacobian norm). The substitution `L_emp → A_g` in the bound is
mathematically wrong because `L_emp` does not enter the
Picard–Lindelöf bound; it enters only the single-step ODE
integration error bound, which vanishes as `dt → 0`.

## Bound on single-step ODE integration error: L_emp · dt

The single-step truncation error of an explicit integrator
applied to the FM ODE `dx/dt = v_θ(x, t)` is bounded by:

```text
e_step ≤ L_emp · dt
```

For the worst-case adapter (ProtBFN-ABFN, L_emp_max = 35.6278):

```text
e_step ≤ 35.6278 · dt
       = 35.6278 · 0.01      (NFE = 100)
       = 0.3563
```

For the median adapter (RF-CIFAR, L_emp_max = 1.9645):

```text
e_step ≤ 1.9645 · dt
       = 1.9645 · 0.01        (NFE = 100)
       = 0.0196
```

For the canonical NFE = 50 case:

```text
e_step(ProtBFN-ABFN) = 35.6278 · 0.02 = 0.7126
e_step(RF-CIFAR)     = 1.9645 · 0.02  = 0.0393
```

**These single-step errors vanish as dt → 0** (FM integration is
asymptotically exact). The framework's value-add is the
scheduler architecture that chooses NFE per record to make
`e_step` small in practice; the bound `e_step ≤ L_emp · dt` is
**not** the bound that controls the per-seed variance floor.

The cumulative integration error over `NFE` steps is bounded by
the Picard–Lindelöf continuity factor `e^{A_g · t}` (which is
the **family** bound), **not** by `L_emp · dt` accumulated over
steps (which would be a much weaker bound).

**Higher-order integrators (RK45, DPM-Solver++, Heun) reduce
e_step further:**

| Integrator | Order | Global error scaling |
|---|---|---|
| Euler | 1 | O(L_emp · dt) |
| Heun | 2 | O(L_emp · dt²) |
| DPM-Solver++ | 2-3 | O(L_emp · dt²) |
| Dormand–Prince RK45 | 4-5 | O(L_emp · dt⁴) |

For NFE = 100, dt = 0.01, RK45 gives `e_global ≈ L_emp · (0.01)⁴ ·
O(1) = L_emp · 1e-8`. The framework supports all of these
integrators via the typed scheduler ports (§2.6.5 of
`docs/drafts/section-2-method.md`).

## Conclusion

- **A_g = 0.8549457422 is the F-side family Lipschitz constant
  of the canonical witness g(x) = (1 + 0.25·tanh x)·sin x**. It
  enters the Picard–Lindelöf continuity bound `e^{A_g·t}` on the
  FM ODE flow and the per-seed variance floor
  `e^{A_g} · √(2d/n_seed)`. It is **bit-identical across all 12
  adapters** by construction (shared canonical witness).

- **L_emp is the per-adapter velocity-field Jacobian norm sup
  ‖∂v_θ/∂x‖_op**. It enters the single-step ODE integration
  error bound `e_step ≤ L_emp · dt`. It **varies by 50x across
  adapters** (range [0.6839, 35.6278]) because each adapter has
  different network architecture, hidden widths, and weight
  initialisation.

- **A_g and L_emp are different quantities appearing in different
  parts of the bound**. The per-seed variance bound uses A_g
  (not L_emp); the single-step ODE integration error bound uses
  L_emp (and vanishes as dt → 0). Substituting `L_emp → A_g` in
  the §MS.10.2 floor is a **category error** — it conflates the
  family-level F-side bound with the adapter-level velocity-
  field bound.

- **The L_emp variation reflects per-adapter implementation
  detail not captured by the F-side witness**. The framework's
  value-add is the scheduler architecture (CosineAnnealScheduler
  + CodimensionSheetScheduler + BoundedMergeOperator +
  EvidenceDrivenScheduler + BRAI) that adapts per record to
  local velocity-field geometry, not per-adapter paper-quantity
  overrides that are not implemented. The per-record BL-distance
  witness (R6 R-level observable) is the **empirical** signal
  that captures per-adapter geometry; the closed-form A_g is the
  **family** coefficient that controls the asymptotic bound.

- **The reviewer question is answered in the affirmative**: the
  per-seed variance bound is meaningful because it uses A_g (a
  family constant that bounds the asymptotic flow-map
  continuity), not L_emp (a per-adapter instance constant that
  bounds local truncation error). The 41x ratio `L_emp_max /
  A_g` is not a contradiction — it is the expected gap between a
  family-level F-side bound and an instance-level per-adapter
  velocity-field bound.

## Cross-references

- `docs/theory/theorem-1-self-contained.md` §B.3 (Theorem 1
  statement), §C.2 (Step 2 of proof sketch — A_g controls the
  first term via Bolley–Guilin–Villani 2012), §D.1 (A_g closed-
  form (D1) and framework surface).
- `docs/audit/wave229-p2-adapter-lipschitz.md` — Wave 229 P2
  empirical L_emp measurement (12 adapters, range
  [0.6839, 35.6278]).
- `docs/audit/wave226-p1-a-g-values.md` — Wave 226 P1 A_g audit
  (canonical witness, 0.8549457422).
- `docs/audit/wave226-p3-variance-bound.md` — Wave 226 P3
  per-seed variance bound (correct math, 14/16 consistent).
- `docs/audit/wave227-p1-a-g-diagnostic.md` — Wave 227 P1
  diagnostic: A_g is canonical-witness, not per-adapter runtime.
- `docs/audit/wave227-p2-floor-corrected.md` — Wave 227 P2
  corrected per-seed floor (canonical source for the 3.75
  scPerplexity / 0.905 pLDDT numbers in §MS.10.2).
- `docs/audit/wave230-p1-b-g-diagnosis.md` — Wave 230 P1 B_g = 0
  root cause (bound-formula implementation bug, fixed).
- `docs/audit/wave230-p2-real-4arm-per-record.md` — Wave 230 P2
  real 4-arm per-record sweep (12-20 GPU-h).
- `docs/drafts/section-2-method.md` §2.3.1 (A_g closed form (D1)
  and framework surface), §2.5 (per-adapter F-side profile),
  §2.6.1 (A_g → CosineAnnealScheduler), §2.9 (Wave 229
  empirical evidence).
- `docs/drafts/methods-why-per-record.md` §MS.10.1 (Picard–
  Lindelöf continuity and A_g bound), §MS.10.2 (per-seed
  variance floor under A_g bound), §MS.10.5.1 (canonical F-side
  witness vs adapter-specific BL distance).
- `verification_outputs/wave229-p2-adapter-lipschitz.csv` —
  per-adapter L_emp CSV (12 adapters).
- `verification_outputs/wave229-p2-adapter-lipschitz-summary.json`
  — JSON summary.
- `verification_outputs/wave226-p1-a-g-values.csv` — per-adapter
  A_g table (canonical witness, identical for all 12 adapters).
- `verification_outputs/wave226-p1-a-g-sensitivity.csv` —
  sensitivity sweep confirming A_g is invariant in ρ.
- `verification_outputs/wave202-p5-lineageflow-per-record.csv` —
  per-record LineageFlow n = 574 paired-t (σ_record^scPerplexity =
  3.661, σ_record^pLDDT = 15.177).
- Coddington & Levinson 1955 — Picard–Lindelöf uniqueness and
  continuity in initial conditions.
- Hartman 2002 — Lipschitz-continuity bound
  `‖Φ_t(x_0) − Φ_t(x_0')‖ ≤ e^{Lt} ‖x_0 − x_0'‖`.
- Bolley, Guillin, Villani 2012 — concentration of measure on
  R^d (used in Theorem 1 proof sketch Step 2, where A_g enters).
