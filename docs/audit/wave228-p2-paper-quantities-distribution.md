# Wave 228 P2 — B_g, C_g, e_ρ Distribution Across 12 Adapters

**Wave:** 228 P2
**Date:** 2026-09-21
**Status:** COMPLETE — **All three quantities (B_g, C_g, e_ρ) are shared across all 12 adapters** under the canonical F-side profile, exactly like A_g (Wave 226 P1 / Wave 227 P1).
**Companion docs:**
- `docs/audit/wave226-p1-a-g-values.md` (A_g distribution across 12 adapters)
- `docs/audit/wave227-p1-a-g-diagnostic.md` (A_g canonical-witness reframing)
- `docs/audit/wave228-p1-4arm-per-record.md` (per-record coverage check, R6 reframe)

## TL;DR

| Quantity | Value (d=1.0, c=1.0, ρ=0.1, η=0.1) | Shared across 12 adapters? | Dependency |
|---|---:|:---:|---|
| **B_g** | **1.1697133855079125** | **YES** | `g` callable (canonical F-side admissible witness); grid params K, h; separation_d (documentation only) |
| **C_g** | **1.240756198591853** | **YES** | `(ρ, c)` only — both framework defaults |
| **e_ρ** | **0.00010000000000000002** | **YES** | `(ρ, η)` only — both framework defaults |

**Verdict:** All three quantities are **closed-form canonical coefficients**, NOT adapter-specific runtime diagnostics. They are bit-identical across all 12 framework adapters under the canonical F-side profile `g(x) = (1 + 0.25·tanh x)·sin x` and default `(d, c, ρ, η) = (1.0, 1.0, 0.1, 0.1)`.

## 1. `root_cell_packing_B` signature — `separation_d` is documentation only

**File:** `adaptive_reflow/theory/paper_quantities.py:178-288`

```python
def root_cell_packing_B(
    g: Callable[[float], float],
    *,
    separation_d: float = 1.0,
    K: float = 8.0,
    h: float = 0.01,
) -> float:
```

The docstring is explicit:

> The `separation_d` argument is the F-side uniform-separation constant; it
> is **not consumed by the sampler** (the literal quantity `B_g` is
> independent of `d`) but is accepted on the function signature so the
> call site can document which F-side parameters are in force.

The implementation (`paper_quantities.py:253-288`) iterates over the
uniform grid `x_k = -K + k*h`, collects `g(x_k)` values, and sums
`e^{-z^2/4}` for each detected sign change (linearly interpolated zero
location) and any exact zero on a grid node. The function NEVER reads
`separation_d` after the value check. `separation_d` is purely a
documentation affordance on the signature.

**Consequence.** `B_g` is a pure functional of `g` (and grid params K, h).
Two calls with the same `g`, `K`, `h` return bit-identical floats, and a
`g`-swap changes `B_g` but `(d, c, ρ, η)` swaps do not (separation_d is
read-only documentation on the signature).

## 2. `per_cell_coefficient_C` signature — `(ρ, c)` only

**File:** `adaptive_reflow/theory/paper_quantities.py:291-358`

```python
def per_cell_coefficient_C(
    *,
    rho: float = 0.1,
    c: float = 1.0,
) -> float:
```

Implementation:

```python
a = (1.0 - rho) ** 2 * min(c * c, 1.0)
return math.exp(0.5 * rho * rho) / a
```

`C_g` depends **only on `(ρ, c)`**. The function takes two arguments, both
of which are framework defaults `(ρ=0.1, c=1.0)`. No callable, no
adapter-specific input. Two calls with the same `(ρ, c)` return
bit-identical floats (D.4 byte-stability).

## 3. `exterior_gap_e_rho` signature — `(ρ, η)` only

**File:** `adaptive_reflow/theory/paper_quantities.py:361-418`

```python
def exterior_gap_e_rho(
    *,
    rho: float = 0.1,
    eta: float = 0.1,
) -> float:
```

Implementation:

```python
return min(rho ** 4, (1.0 - rho) ** 2 * eta ** 2)
```

`e_ρ` depends **only on `(ρ, η)`**. Both arguments are framework defaults
`(ρ=0.1, η=0.1)`. No callable, no adapter-specific input. Two calls with
the same `(ρ, η)` return bit-identical floats.

## 4. Empirical computation

```python
import math
from adaptive_reflow.theory.paper_quantities import (
    root_cell_packing_B,
    per_cell_coefficient_C,
    exterior_gap_e_rho,
)

# Canonical F-side admissible witness (Proposition 2 family member).
# See tests/test_theory/test_rate_bound.py:44-72 and
# docs/audit/wave226-p1-a-g-values.md §Method.
g = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)

# Framework defaults: d=1.0, c=1.0, rho=0.1, eta=0.1.
B_g = root_cell_packing_B(g, separation_d=1.0, K=8.0, h=0.01)
C_g = per_cell_coefficient_C(rho=0.1, c=1.0)
e_rho = exterior_gap_e_rho(rho=0.1, eta=0.1)

print(f"B_g = {B_g:.6f}")     # 1.169713
print(f"C_g = {C_g:.6f}")     # 1.240756
print(f"e_rho = {e_rho:.6f}") # 0.000100
```

Reproducible byte-stable computation:

| Quantity | Repr (full precision) | Rounded to 6 decimals |
|---|---:|---:|
| B_g | `1.1697133855079125` | 1.169713 |
| C_g | `1.240756198591853` | 1.240756 |
| e_ρ | `0.00010000000000000002` | 0.000100 |

## 5. Distribution across 12 adapters

The framework's canonical F-side admissible witness is

```
g(x) = (1 + 0.25 · tanh x) · sin x,
```

with default F-side constants `(d=1.0, c=1.0, ρ=0.1, η=0.1)`. The
canonical witness is shared by **all 12 framework adapters** (per
`docs/audit/wave226-p1-a-g-values.md`):

| # | Adapter | Domain | d | c | ρ | η | g |
|---|---|---|---:|---:|---:|---:|---|
| 1  | LineageFlowAdapter        | protein FM          | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 2  | KanziAdapter              | protein flow-AE     | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 3  | FlowMol3V2Adapter         | small-molecule FM   | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 4  | RectifiedFlowCIFARAdapter | CIFAR-10 RF         | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 5  | MnistFmAdapter            | MNIST FM            | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 6  | TwoDimFMAdapter           | 2D RF               | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 7  | FreqFlowAdapter           | time-series FM      | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 8  | Wan2.2Adapter             | video FM            | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 9  | HiDreamI1Adapter          | text-to-image FM    | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 10 | LuminaImage20Adapter      | text-to-image FM    | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 11 | GraphBFNAdapter           | graph BFN           | 1.0 | 1.0 | 0.1 | 0.1 | canonical |
| 12 | ProtBFNAbBFNAdapter       | protein ab-ligand BFN | 1.0 | 1.0 | 0.1 | 0.1 | canonical |

For each adapter, the literal `(B_g, C_g, e_ρ)` is:

| # | Adapter | B_g | C_g | e_ρ |
|---|---|---:|---:|---:|
| 1  | LineageFlowAdapter        | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 2  | KanziAdapter              | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 3  | FlowMol3V2Adapter         | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 4  | RectifiedFlowCIFARAdapter | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 5  | MnistFmAdapter            | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 6  | TwoDimFMAdapter           | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 7  | FreqFlowAdapter           | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 8  | Wan2.2Adapter             | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 9  | HiDreamI1Adapter          | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 10 | LuminaImage20Adapter      | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 11 | GraphBFNAdapter           | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |
| 12 | ProtBFNAbBFNAdapter       | 1.1697133855079125 | 1.240756198591853 | 0.00010000000000000002 |

All 12 rows are bit-identical for `(B_g, C_g, e_ρ)`.

## 6. Why all three are SHARED (formal argument)

**B_g:**
- Signature: `root_cell_packing_B(g, *, separation_d=1.0, K=8.0, h=0.01)`.
- The implementation only reads `g`, `K`, `h`. `separation_d` is checked
  for positivity then ignored (documentation affordance).
- All 12 adapters share the canonical `g(x) = (1 + 0.25·tanh x)·sin x`
  (no adapter overrides `paper_quantities_provider`; see Wave 226 P1
  §3 / Wave 227 P1).
- Default `K=8.0, h=0.01` is shared.
- ∴ `B_g` is bit-identical across all 12 adapters.

**C_g:**
- Signature: `per_cell_coefficient_C(*, rho=0.1, c=1.0)`.
- The implementation reads only `(ρ, c)`.
- All 12 adapters use framework defaults `(ρ=0.1, c=1.0)`.
- ∴ `C_g` is bit-identical across all 12 adapters.

**e_ρ:**
- Signature: `exterior_gap_e_rho(*, rho=0.1, eta=0.1)`.
- The implementation reads only `(ρ, η)`.
- All 12 adapters use framework defaults `(ρ=0.1, η=0.1)`.
- ∴ `e_ρ` is bit-identical across all 12 adapters.

## 7. Caveat — adapter overrides

The shared-ness argument above relies on the **canonical F-side profile**
and **framework defaults**. If an adapter were to override any of these,
the literal `(B_g, C_g, e_ρ)` would shift. The mechanism for such an
override:

- **B_g override** would require supplying a custom `Callable[[float],
  float]` via `ReInferenceConfig.paper_quantities_provider`. No adapter
  does so today (per `docs/audit/wave227-p1-a-g-diagnostic.md` §3,
  every consumer falls back to `None` when the lookup is missing).
- **C_g override** would require overriding `(ρ, c)` to non-default values
  at a call site. `per_cell_coefficient_C` is called with keyword
  arguments; the framework defaults `ρ=0.1, c=1.0` are not the
  framework's only admissible choice.
- **e_ρ override** similarly requires `(ρ, η)` overrides.

None of these overrides happens in the current framework or in any
adapter today. The current `(B_g, C_g, e_ρ)` values are bit-identical
across all 12 adapters.

## 8. Conclusion

| Quantity | Value | Across 12 adapters | Adapter-specific? |
|---|---:|:---:|:---:|
| A_g | 0.8549457422 (Wave 226 P1) | identical | **NO** — canonical |
| B_g | 1.1697133855079125 | identical | **NO** — canonical |
| C_g | 1.240756198591853 | identical | **NO** — canonical |
| e_ρ | 0.00010000000000000002 | identical | **NO** — canonical |

**All four paper-quantity coefficients are canonical across the 12
framework adapters.** The adapter-specific work product lives at the
**empirical per-record BL distance** layer (R6 R-level headline), not at
the A_g / B_g / C_g / e_ρ layer. The latter are the **closed-form
coefficients** of the BL bound; once `g` and `(d, c, ρ, η)` are chosen,
they are fixed.

**No code changes required.** The audit confirms the framework's
design intent: a single canonical F-side admissible witness plus an
empirical per-record BL evaluation. Adapters that wish to override the
witness can supply a custom `paper_quantities_provider`; no adapter
does today.

## Files

- `verification_outputs/wave228-p2-paper-quantities-distribution.csv` —
  per-quantity table (3 rows + header)
- `docs/audit/wave228-p2-paper-quantities-distribution.md` — this file

## Reproducibility

```bash
python -c "
import math
from adaptive_reflow.theory.paper_quantities import (
    root_cell_packing_B, per_cell_coefficient_C, exterior_gap_e_rho,
)
g = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)
print('B_g  =', root_cell_packing_B(g, separation_d=1.0, K=8.0, h=0.01))
print('C_g  =', per_cell_coefficient_C(rho=0.1, c=1.0))
print('e_rho=', exterior_gap_e_rho(rho=0.1, eta=0.1))
"
```

CPU-only, deterministic, byte-stable.

## References

- `adaptive_reflow/theory/paper_quantities.py` — `B_g`, `C_g`, `e_ρ` evaluators (canonical home).
- `adaptive_reflow/theory/rate_bound.py:57-60` — `_DEFAULT_FSIDE_*` constants.
- `tests/test_theory/test_rate_bound.py:44-72` — canonical F-side admissible witness test fixture.
- `docs/audit/wave226-p1-a-g-values.md` — A_g distribution across 12 adapters (identical across rows).
- `docs/audit/wave227-p1-a-g-diagnostic.md` — A_g canonical-witness reframing.
- `docs/audit/wave228-p1-4arm-per-record.md` — per-record coverage check (R6 reframe).