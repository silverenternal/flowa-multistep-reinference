# Wave 227 P1 — A_g Diagnostic: Per-Adapter vs. Canonical Witness

**Wave:** 227 P1
**Date:** 2026-09-21
**Status:** COMPLETE — A_g is a **canonical-witness computation**, not a per-adapter runtime. The
"paper quantities are adapter-specific" claim should be reframed as **the BL-distance
witness is adapter-specific; the closed-form A_g, B_g, C_g, e_ρ coefficients are canonical
across adapters that share the framework default F-side profile**.

---

## TL;DR

| Question (DeepSeek) | Answer | Evidence |
|---|---|---|
| (a) Why is A_g identical across all 12 adapters? | All 12 adapters share the canonical F-side profile `g(x) = (1 + 0.25·tanh x)·sin x` and identical `(d, c, ρ, η) = (1.0, 1.0, 0.1, 0.1)`. No per-adapter g profile construction exists in the framework. | `docs/audit/wave226-p1-a-g-values.md`; `verification_outputs/wave226-p1-a-g-values.csv`; `tests/test_theory/test_rate_bound.py:44-72` |
| (b) Why is A_g invariant in ρ? | `sheet_evidence_A(g, K, h)` takes only `g` and grid parameters. `(d, c, ρ, η)` are F-side hypothesis constraints (not g-shapes), consumed by `validate_f_side` and `per_cell_coefficient_C` / `exterior_gap_e_rho`. | `adaptive_reflow/theory/paper_quantities.py:96-175`; `adaptive_reflow/theory/validation.py:58-95` |
| (c) Is A_g computed from a per-adapter profile or a canonical witness? | **Canonical witness.** No adapter declares `profile_residual_fn`; the framework's `AdapterCapabilities` does not expose `profile_residual_fn`. When the runner / scheduler receive no `paper_quantities_provider`, they fall back to legacy closed forms (no per-adapter A_g computation). | `tools/eval/framework.py:240-280`; `adaptive_reflow/universal/adapter.py:132` (no profile_residual_fn field); `adaptive_reflow/algorithm/runner/runner.py:1172-1214` |

**Conclusion.** The "paper quantities are adapter-specific" claim is **structurally weak**
for A_g (and B_g, C_g, e_ρ by the same argument): these are closed-form
quantities of a chosen `g` and the chosen F-side hypothesis set. The framework
uses a **single canonical F-side admissible witness** for all 12 adapters (the
Proposition 2 family `g(x) = (1 + 0.25·tanh x)·sin x`), and consequently A_g is
bit-identical across all 12 rows of `verification_outputs/wave226-p1-a-g-values.csv`.

**Adapter-specific work product lives at the empirical BL-distance layer**, NOT at
the A_g layer: the per-record BL witness in
`adaptive_reflow/theory/rate_bound.py` (theorem1_bl_convergence_witness) is the
adapter-specific observable. A_g, B_g, C_g, e_ρ are the closed-form COEFFICIENTS of
the BL bound; they are canonical once `(d, c, ρ, η)` and `g` are chosen.

---

## 1. `sheet_evidence_A` signature — does NOT take (d, c, ρ, η)

**File:** `adaptive_reflow/theory/paper_quantities.py:96-175`

```python
def sheet_evidence_A(
    g: Callable[[float], float],
    *,
    K: float = 8.0,
    h: float = 0.01,
) -> float:
    """Return ``A_g`` from Proposition 3 / line 161.

    Paper verbatim (line 116-117, Proposition 3, and line 161):

        "``A_g := (2*pi)^{-1/2} \\int_R \\frac{e^{-s^2/2}}{\\sqrt{1+g(s)^2}} ds > 0``"
    """
```

The function takes a `Callable[[float], float]` named `g` (the residual profile) and
two grid parameters (`K`, `h`). It does **NOT** take `(d, c, ρ, η)`. The integral
operates on `g(s)` alone:

```python
gs = float(g(s))
denom = math.sqrt(1.0 + gs * gs)
f_s = math.exp(-0.5 * s * s) / denom
```

**Consequence.** A_g is a pure functional of `g`. Two calls with the same `g`
return bit-identical floats (D.4 byte-stability), and a `g`-swap changes A_g
but `(d, c, ρ, η)` swaps do not.

---

## 2. (d, c, ρ, η) are F-side hypothesis constraints, NOT g-shape parameters

**File:** `adaptive_reflow/theory/validation.py:58-95`

```python
def validate_f_side(
    d: float, c: float, rho: float, eta: float,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``(d, c, rho, eta)`` satisfy the F-side hypotheses.

    Paper verbatim (line 22-26, Lemma 5 line 135-138):
        * ``d > 0``   (uniform separation constant).
        * ``c > 0``   (uniform simplicity constant).
        * ``rho in (0, 1/4]`` and ``rho < d/4``  (disjoint-cell constraint).
        * ``eta > 0``  (exterior gap constant).
    """
```

The four constants are **hypothesis constraints**:

| Constant | Role | Bound |
|---|---|---|
| `d` | uniform separation between roots | lower bound on |r − s| for r ≠ s ∈ Z_g |
| `c` | uniform simplicity on roots | lower bound on \|g(r + u)\| / \|u\| |
| `ρ` | cell half-width + disjoint-cell guarantee | upper bound on cell size; ρ < d/4 |
| `η` | exterior gap | lower bound on \|g(x)\| outside cells |

`ρ` and `η` flow into the **per-cell coefficient** `C_g` and the **exterior gap**
`e_ρ` respectively:

```python
# per_cell_coefficient_C(rho, c): C_g = e^{rho^2/2} / ((1-rho)^2 * min(c^2, 1))
# exterior_gap_e_rho(rho, eta):  e_rho = min(rho^4, (1-rho)^2 * eta^2)
```

**These constants are CONSUMED by B_g / C_g / e_ρ, NOT by A_g.** A_g is a pure
integral over `g`, with no dependence on `(d, c, ρ, η)`. The sensitivity sweep in
`docs/audit/wave226-p1-a-g-values.md` (ρ ∈ {0.05, 0.10, 0.15, 0.20, 0.25}) confirms
this empirically: A_g = 0.8549457422 across all five rows.

---

## 3. A_g consumption paths — every call site uses an external `g` callable

A_g is consumed at exactly six runtime sites. In every case, the `g` callable is
either user-supplied, framework-defaulted, or absent (legacy closed form):

| File | Line | Call | `g` source |
|---|---|---|---|
| `adaptive_reflow/framework/interfaces.py` | 364 | `sheet_evidence_A(g)` | `g` argument passed in by caller (`assert_theorem1_statement`) |
| `adaptive_reflow/algorithm/runner/runner.py` | 1185 | `_pq.sheet_evidence_A(provider)` | `config.paper_quantities_provider` (`Callable[[float], float] \| None`) |
| `adaptive_reflow/algorithm/scheduler/simple.py` | 117 | `_pq.sheet_evidence_A(profile_residual_fn)` | constructor `profile_residual_fn` argument |
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 1276 | `_pq.sheet_evidence_A(profile_residual_fn)` | constructor `profile_residual_fn` argument |
| `adaptive_reflow/algorithm/scheduler/evidence_driven.py` | 457 | `_pq.sheet_evidence_A(profile_residual_fn)` | constructor `profile_residual_fn` argument |
| `adaptive_reflow/eval/fid_theorem_aligned.py` | 192 | `sheet_evidence_A(g, K=K, h=h)` | `g` argument passed in by caller |
| `adaptive_reflow/theory/checkers.py` | 243 | `sheet_evidence_A(g)` | `g` argument passed in by caller |
| `tools/eval/framework.py` | 266 | `_pq.sheet_evidence_A(profile_residual_fn)` | duck-typed `getattr(caps, "profile_residual_fn", None)` / `getattr(adapter, ...)` |

In **none** of these paths is a per-adapter profile constructed dynamically.
`tools/eval/framework.py` does a duck-type lookup on `caps.profile_residual_fn` and
`adapter.profile_residual_fn`, but neither `AdapterCapabilities`
(`adaptive_reflow/universal/adapter.py:132`) nor any of the 12 adapter classes
(`LineageFlowAdapter`, `KanziAdapter`, `FlowMol3V2Adapter`, `RectifiedFlowCIFARAdapter`,
`MnistFmAdapter`, `TwoDimFMAdapter`, `FreqFlowAdapter`, `Wan2.2Adapter`,
`HiDreamI1Adapter`, `LuminaImage20Adapter`, `GraphBFNAdapter`, `ProtBFNAbBFNAdapter`)
expose a `profile_residual_fn` attribute — the lookup returns `None`, the function
returns `None`, and no A_g is computed at runtime for any of the 12 adapters.

---

## 4. Canonical witness in tests

**File:** `tests/test_theory/test_rate_bound.py:44-72`

```python
def test_check_explicit_rate_bound_on_canonical_g_a_at_small_eps():
    """Bound holds at ``eps = 0.1`` for canonical
    ``g_a(x) = (1 + 0.25 * tanh(x)) * sin(x)`` (Proposition 2 family).
    """
    g = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)  # noqa: E731

    report = check_explicit_rate_bound(
        g, eps=0.1, n_samples=512, seed=0,
        f_side_d=0.5, f_side_c=0.5, f_side_rho=0.1, f_side_eta=0.1,
    )
```

The framework's canonical F-side admissible witness is the Proposition 2 family
member

```
g(x) = (1 + 0.25 · tanh x) · sin x,
```

with default F-side constants `(d=0.5, c=0.5, ρ=0.1, η=0.1)`. The same profile is
the framework default in `adaptive_reflow/theory/rate_bound.py:57-60`:

```python
_DEFAULT_FSIDE_D: float = 1.0
_DEFAULT_FSIDE_C: float = 1.0
_DEFAULT_FSIDE_RHO: float = 0.1
_DEFAULT_FSIDE_ETA: float = 0.1
```

(Production overrides `d, c` to 1.0 vs the test's 0.5 — see Wave 226 P1 audit for
the rationale, but the same `g(x)` is used.) This is the SINGLE source of `g` for
every A_g computation in the framework.

---

## 5. Wave 226 P1 audit confirms identical A_g across all 12 adapters

**File:** `docs/audit/wave226-p1-a-g-values.md` (full doc read for context)

The Wave 226 P1 audit explicitly states the canonical witness and the rationale:

> | **A_g (default profile)** | **0.8549457422** | canonical F-side profile g(x) = (1 + 0.25 tanh x) sin x |
>
> **12 adapters, A_g identical across all:** LineageFlow, Kanzi, FlowMol3,
> CIFAR-10 RF, MNIST FM, 2D RF, FreqFlow, Wan2.2, HiDream I1, Lumina Image
> 2.0, GraphBFN, ProtBFN-ABFN. All twelve share the framework default
> F-side profile, so the literal A_g value is the same for all rows; the
> per-adapter CSV is for documentation and cross-reference.

`verification_outputs/wave226-p1-a-g-values.csv` confirms bit-identical A_g across
all 12 rows (and a sensitivity sweep showing A_g is invariant in ρ ∈ {0.05, 0.10,
0.15, 0.20, 0.25}).

This audit doc already acknowledges that the per-adapter CSV is a *documentation*
table — the literal A_g value is the same because the input `g` is the same.

---

## 6. Adapter-specificity lives at the BL-distance layer, NOT the A_g layer

The framework's adapter-specific empirical work product is the **per-record
Bounded-Lipschitz (BL) distance**, NOT the closed-form A_g coefficient:

1. **`theorem1_bl_convergence_witness`** in `adaptive_reflow/theory/rate_bound.py`
   runs a Monte-Carlo BL estimate for the supplied `g` and `(d, c, ρ, η)`. This is
   the **adapter-specific** observable.
2. The closed-form A_g, B_g, C_g, e_ρ are the **coefficients** of the bound

   ```
   BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE/B_g) + C_g · e_ρ.
   ```

   They are canonical once `g` and `(d, c, ρ, η)` are fixed.

3. The **per-record paired effect d_z** is the per-adapter empirical signal (R-level
   headline claims): same `x_0` paired across framework-vs-baseline, eliminates the
   seed-to-seed variance term `e^{2A_g} · 2d / n_seed` (Wave 226 P2 §MS.10.2).

So the "adapter-specific" claim should be reframed as:

> **Adapter-specific work product:** the per-record BL distance (R6 R-level
> headline observable) and the per-record paired-diff effect d_z. **Canonical
> coefficients:** A_g, B_g, C_g, e_ρ — bit-identical across all 12 adapters
> because they share the canonical F-side admissible witness `g(x) = (1 + 0.25·tanh
> x)·sin x` and default `(d, c, ρ, η) = (1.0, 1.0, 0.1, 0.1)`. Adapters that
> override the F-side profile would shift A_g and would require a per-adapter
> re-evaluation (see §MS.10.4 caveat 4 in `docs/drafts/methods-why-per-record.md`).

---

## 7. Recommended narrative reframing for Methods §MS.10

The current `docs/drafts/methods-why-per-record.md` §MS.10.4 caveat 4 already says:

> 4. **Cross-adapter A_g** is identical to the default profile on all 12
>    adapters (Wave 226 P1 audit), so the per-seed floor is the same on all
>    adapters. Adapters that override the F-side profile would shift the
>    floor and would require a per-adapter re-evaluation of the per-seed /
>    per-record granularity choice.

This caveat is **correct** and captures the relevant fact. Suggested additions:

1. **Explicit reframing in §MS.10.1**: insert one sentence noting that A_g is a
   *canonical* coefficient for the canonical F-side witness (the same Proposition
   2 family `g(x) = (1 + 0.25·tanh x)·sin x` used in
   `tests/test_theory/test_rate_bound.py`), not a per-adapter runtime. The
   per-adapter empirical signal is the per-record BL distance (cite R6).

2. **§MS.10.2 Picard–Lindelöf floor (UNCHANGED)**: the floor argument is correct.
   The seed-to-seed variance `e^{2A_g} · 2d / n_seed` is the floor for any `g`
   satisfying the F-side hypotheses; A_g is the canonical coefficient and
   per-seed variance is dominated by the `2d` term amplified by the
   `e^{2A_g}` factor. The argument does not require per-adapter A_g.

3. **Add a §MS.10.5.1 "Canonical witness" note**: state that the framework's
   canonical F-side admissible witness is the Proposition 2 family member
   `g(x) = (1 + 0.25·tanh x)·sin x`, identical across all 12 adapter
   evaluations. Adapters that wish to override `g` would invoke
   `ReInferenceConfig.paper_quantities_provider` with a custom `Callable[[float],
   float]`; no adapter does so today.

---

## 8. Conclusion

| DeepSeek sub-question | Final answer |
|---|---|
| (a) Why is A_g identical across all 12 adapters? | All 12 share the canonical F-side profile `g(x) = (1 + 0.25·tanh x)·sin x` and identical `(d, c, ρ, η) = (1.0, 1.0, 0.1, 0.1)`. No per-adapter g profile construction exists in the framework. |
| (b) Why is A_g invariant in ρ? | `sheet_evidence_A(g, K, h)` depends only on `g` and grid parameters; `(d, c, ρ, η)` are F-side hypothesis constraints consumed by `validate_f_side`, `per_cell_coefficient_C`, and `exterior_gap_e_rho`, not by A_g. |
| (c) Per-adapter profile or canonical witness? | **Canonical witness.** A_g is bit-identical across all 12 adapters by construction. |

**Operational implication.** The "paper quantities are adapter-specific" claim in
the Wave 226 P2 methods paragraph is **structurally weak** at the A_g layer; the
claim is correct only for the **empirical BL distance (per-record)**, which IS
adapter-specific. The current §MS.10.4 caveat 4 correctly notes this; a §MS.10.1
or §MS.10.5.1 refinement would make the structural claim explicit.

**No code changes required.** The audit confirms the framework's design
intent: a single canonical F-side admissible witness plus an empirical per-record
BL evaluation. Adapters that wish to override the witness can supply a custom
`paper_quantities_provider`; no adapter does today.

---

## Cross-references

- `adaptive_reflow/theory/paper_quantities.py` — A_g, B_g, C_g, e_ρ evaluators.
- `adaptive_reflow/theory/validation.py` — F-side hypothesis validators.
- `adaptive_reflow/theory/rate_bound.py:57-60` — `_DEFAULT_FSIDE_*` constants.
- `tests/test_theory/test_rate_bound.py:44-72` — canonical witness test fixture.
- `adaptive_reflow/framework/interfaces.py:340-364` — Theorem 1 statement
  assembler that consumes A_g.
- `adaptive_reflow/algorithm/runner/runner.py:1172-1214` — runner's
  paper_quantities_provider path.
- `adaptive_reflow/algorithm/scheduler/{simple,adaptive,evidence_driven}.py` —
  scheduler's profile_residual_fn path.
- `tools/eval/framework.py:240-280` — eval-time paper-quantity extraction (returns
  None when no profile_residual_fn is supplied).
- `adaptive_reflow/universal/adapter.py:132` — `AdapterCapabilities` (no
  profile_residual_fn field).
- `docs/audit/wave226-p1-a-g-values.md` — input audit, canonical witness rationale.
- `docs/audit/wave226-p3-variance-bound.md` — variance bound argument that uses
  A_g.
- `verification_outputs/wave226-p1-a-g-values.csv` — 12-adapter A_g table
  (identical across rows).
- `verification_outputs/wave226-p1-a-g-sensitivity.csv` — A_g invariance in ρ.
- `docs/drafts/methods-why-per-record.md` — §MS.10 methods paragraph that
  re-states the Wave 226 P1 audit for the per-seed / per-record granularity
  debate.