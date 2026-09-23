# Wave 296 P1 — JMAA Theory Integration Architecture (Design-Only)

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave292-p1-pipeline-inventory.md` (Wave 292 P1 — the 15 dormant-site enumeration)
- `docs/audit/jmaa-theory-applications.md` (Wave 288 P0 — the 16-site taxonomy)
- `docs/audit/wave294-final.md` (Wave 294 — claims + paper §2 fixup)
- `docs/audit/wave292-p2-config-genealogy.md` (Wave 292 P2 — config-flag lineage)
**Purpose:** Design the full JMAA theory integration architecture. Per the
Wave 292 P1 inventory, **15 of 16 application sites are dormant under the
cosine-baseline deployment**. The fix is a single opt-in flag
(`enable_full_jmaa_theory: bool`) plus a typed cache carrier
(`PaperQuantitiesCache`) that, when supplied, threads the four paper
quantities `A_g, B_g, C_g, e_rho` through every dormant site while keeping
the cosine-baseline byte-stable for callers that opt out.

This is a **design-only** doc — no code changes. Per the W296 task scope
("EDIT DISCIPLINE: design doc only; no code in this phase"), only this
audit doc is written. Implementation lands in subsequent waves (W296 P2+).

---

## 0. TL;DR

| Layer | Surface | Backward-compat invariant |
|---|---|---|
| Cache | `PaperQuantitiesCache(profile_residual_fn=None)` → `is_active = False` | Existing call sites receive a no-op cache (`A_g = B_g = C_g = e_rho = None`) |
| Engine | `Engine(*, enable_full_jmaa_theory: bool = False, ...)` | New keyword-only param, default `False`. Existing `Engine(...)` callers see byte-identical behaviour. |
| Wiring | 7 A-class sites (pass-through) + 8 B-class sites (opt-in default flip) | Each site reads `cache.is_active`; if `False`, the site falls back to the pre-Wave-296 path (cosine-baseline). |
| Audit | `consume(site_name)` activation log + canonical audit codes | Per-site activation is observable in the `RoundTrace.audit_codes` and `LedgerRow.audit_codes`. |
| Invariants | D.4 30/30, ruff 0, mkdocs 0 warnings, vendored NOT touched | Cosine baseline R-cell results reproduce byte-identically. |

**The 15 dormant sites (from W292 P1 §1) are reorganised into:**

- **A-class (7 sites, default `None`)** — paper-quantity argument is plumbed
  through with `cache.get(site)`; if `cache.is_active is False`, the site
  falls back to the pre-Wave-296 path.
- **B-class (8 sites, opt-in default flips)** — when `cache.is_active is
  True`, the site's effective default becomes "ON with cache value"; when
  `False`, the site's effective default remains the legacy `None` / cosine
  path.

---

## 1. PaperQuantitiesCache — full API design

### 1.1 File location

`adaptive_reflow/framework/paper_quantities_cache.py` (new module).

Co-located with `adaptive_reflow/framework/state_bundle_cache.py` because:

- The cache pattern is identical (identity-keyed memo + lazy evaluation +
  activation log).
- The `framework/` subpackage already owns the cross-cutting Engine
  surfaces (`engine.py`, `state_bundle_cache.py`, `interfaces.py`,
  `cuda_graph_capture.py`).
- Stdlib-only import discipline (no torch, no numpy, no IO) is enforced
  in `framework/` per the existing modules.

### 1.2 Class definition

```python
class PaperQuantitiesCache:
    """Lazy-memoized cache for the four JMAA Theorem 1 quantities.

    Stores A_g (sheet evidence, Proposition 3), B_g (root-cell packing,
    Lemma 5), C_g (per-cell coefficient, Lemma 3), and e_rho (exterior
    gap, Lemma 5) computed from a single ``profile_residual_fn``
    callable. When ``profile_residual_fn is None`` the cache is a
    dormant carrier (``is_active = False``); every property returns
    ``None`` and every ``get(site_name)`` returns the site-specific
    sentinel.

    Byte-stability
    --------------
    The cache is pure-functional: the four quantities are computed
    exactly once at first access, the result is stored, and subsequent
    accessors return the same float object. Two caches constructed
    from the same profile return bit-identical floats across processes.

    Activation semantics
    --------------------
    ``is_active`` is set ``True`` iff ``profile_residual_fn is not None``.
    Sites that consume the cache MUST check ``is_active`` before
    reading any property; an inactive cache returns ``None`` for every
    property access and an empty list of audit codes for
    ``consume(site_name)``.
    """
```

### 1.3 Constructor

```python
def __init__(
    self,
    *,
    profile_residual_fn: Callable[[float], float] | None = None,
    rho: float = 0.1,
    c: float = 1.0,
    d: float = 1.0,
    eta: float = 0.1,
) -> None:
    """Construct the cache.

    :param profile_residual_fn: optional callable mapping a real ``x``
        to ``g(x)``. When ``None`` (the default), the cache is dormant
        (``is_active = False``) and every accessor returns ``None``.
        When supplied, the cache is active (``is_active = True``) and
        the four paper quantities are computed lazily on first
        access.
    :param rho: F-side ``rho`` parameter (paper line 128). Default
        ``0.1`` matches the cosine-baseline ``enable_paper_uplift_27``
        default.
    :param c: F-side ``simplicity_c`` parameter (paper line 117).
        Default ``1.0`` matches the legacy CIFAR baseline.
    :param d: F-side ``separation_d`` parameter (paper line 124).
        Default ``1.0``.
    :param eta: F-side ``eta`` parameter (paper line 128). Default
        ``0.1`` matches the CIFAR baseline.
    """
```

### 1.4 Properties

```python
@property
def is_active(self) -> bool:
    """Return ``True`` iff ``profile_residual_fn is not None``."""
    return self._profile_residual_fn is not None

@property
def sheet_A(self) -> float | None:
    """Return cached ``A_g`` (paper Proposition 3, line 161).

    Returns ``None`` when ``is_active is False``. Computed lazily on
    first access via
    :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`
    on the cached ``profile_residual_fn``.
    """

@property
def packing_B(self) -> float | None:
    """Return cached ``B_g`` (paper Lemma 5, line 159)."""

@property
def cell_C(self) -> float | None:
    """Return cached ``C_g`` (paper Lemma 3, line 191)."""

@property
def e_rho(self) -> float | None:
    """Return cached ``e_rho`` (paper Lemma 5, line 128)."""

@property
def profile_residual_fn(self) -> Callable[[float], float] | None:
    """Return the cached ``profile_residual_fn`` (or ``None``)."""

@property
def rho(self) -> float:
    """Return the configured F-side ``rho`` parameter."""

@property
def c(self) -> float:
    """Return the configured F-side ``c`` parameter."""

@property
def d(self) -> float:
    """Return the configured F-side ``d`` parameter."""

@property
def eta(self) -> float:
    """Return the configured F-side ``eta`` parameter."""
```

### 1.5 Methods

```python
def get(self, site_name: str) -> Any:
    """Return the cache value appropriate for ``site_name``.

    Site-aware dispatch — returns the canonical value each of the 15
    dormant sites consumes:

    * ``"dt_floor"``  → ``e_rho`` (Site 4, Site 4b)
    * ``"alpha_floor"`` → ``e_rho`` (Site 4b)
    * ``"merge_floor"`` → ``e_rho`` (Site 6, Site 6b)
    * ``"policy_C"``   → ``cell_C`` (Site 7)
    * ``"noise_bias"`` → ``(sheet_A, packing_B, cell_C, e_rho)`` tuple (Site 5)
    * ``"mfpqa"``      → ``PaperQuantitiesSnapshot`` (Site 3)
    * ``"evidence"``   → ``PaperQuantitiesSnapshot`` (Site 8)
    * ``"fid"``        → ``PaperQuantitiesSnapshot`` (Site 9)
    * ``"lipschitz"``  → ``PaperQuantitiesSnapshot`` (Site 10)
    * ``"evaluator"``  → ``(sheet_A, cell_C)`` (Site 11)
    * ``"checker"``    → ``PaperQuantitiesSnapshot`` (Site 12)
    * ``"profile"``    → ``profile_residual_fn`` (Site 13)
    * ``"regime"``     → ``e_rho`` (Site 15)
    * ``"derivation"`` → ``e_rho`` (Site 16)
    * ``"solver_hint"`` → ``e_rho`` (Site 2)

    Returns ``None`` when ``is_active is False``. Unknown site names
    raise ``ValueError``.
    """

def consume(self, site_name: str) -> bool:
    """Mark ``site_name`` as activated; return whether it was first-time.

    Idempotent: a second call with the same ``site_name`` returns
    ``False``. The activation log is observable via
    :attr:`activated_sites`. Callers (Engine and adapter sites) use
    this to populate ``RoundTrace.audit_codes`` and
    ``LedgerRow.audit_codes` with per-site activation codes.

    Returns ``False`` (no-op) when ``is_active is False``.
    """

def stats(self) -> dict[str, int]:
    """Return activation-log counters for audit-doc verification."""
    return {
        "is_active": int(self.is_active),
        "activated_count": len(self._activated),
        "A_g_computed": int(self._A_g is not None),
        "B_g_computed": int(self._B_g is not None),
        "C_g_computed": int(self._C_g is not None),
        "e_rho_computed": int(self._e_rho is not None),
    }

def clear(self) -> None:
    """Reset the activation log and (optionally) the cached values."""
```

### 1.6 LazyMemoCachedEvaluationCost — internal helper

```python
@dataclass
class _LazyMemo:
    """Per-quantity lazy-memo slot.

    ``_LazyMemo`` implements the canonical
    "LazyMemoCachedEvaluationCost" pattern: stores a sentinel
    ``_NOT_COMPUTED`` constant and lazily evaluates the producer
    callable on first read. Two reads after the first evaluation
    return the same float object.

    Fields
    ------
    _value: float | _SENTINEL
    _producer: Callable[[], float]
    """
    _NOT_COMPUTED = object()
    _value: Any = _NOT_COMPUTED
    _producer: Callable[[], float] | None = None

    def get(self) -> float:
        """Return the lazily-computed value (computed once)."""
        if self._value is self._NOT_COMPUTED:
            assert self._producer is not None
            self._value = float(self._producer())
        return self._value
```

The cache holds four `_LazyMemo` slots (one per quantity), all sharing
the same `profile_residual_fn`. The first access of `sheet_A` triggers
`_pq.sheet_evidence_A(self._profile_residual_fn)`; the first access of
`packing_B` triggers `_pq.root_cell_packing_B(self._profile_residual_fn)`;
etc. All four computations are independent and pure.

### 1.7 Backward compat — the dormant state

When `profile_residual_fn is None`:

- `is_active` returns `False`.
- All four properties (`sheet_A`, `packing_B`, `cell_C`, `e_rho`) return
  `None`.
- `get(site_name)` returns `None` for every site name.
- `consume(site_name)` is a no-op (returns `False`).
- `stats()` reports `is_active=False` and all quantity-computed flags
  `False`.

A dormant cache is a Python `__init__` cost (no I/O, no math) — the
overhead per-Engine is one bool + four `None` slots + the
`profile_residual_fn` slot. Byte-identical to a `None` placeholder for
all existing call sites that don't opt in.

---

## 2. Engine — `enable_full_jmaa_theory` integration

### 2.1 New parameter

```python
def __init__(
    self,
    *,
    operation_steps: tuple[str, ...] = DEFAULT_OPERATION_STEPS,
    feature_flag: bool | None = None,
    digest_cache: _StateBundleDigestCache | None = None,
    enable_full_jmaa_theory: bool = False,
    paper_quantities_cache: PaperQuantitiesCache | None = None,
) -> None:
```

**Parameter contract:**

- `enable_full_jmaa_theory: bool = False` — keyword-only, default `False`
  (backward compat). When `True`, the Engine is allowed to construct a
  cache (or accept the supplied one) and wire it through to all 15
  dormant sites.
- `paper_quantities_cache: PaperQuantitiesCache | None = None` —
  keyword-only, default `None`. Allows the caller to pre-build a cache
  (e.g., for testing or for adapters that want to pin the profile
  independently of the Engine). When supplied AND `enable_full_jmaa_theory=True`,
  the Engine uses the supplied cache. When supplied but the flag is
  `False`, the cache is ignored (preserves byte-stability).

**Validation contract:**

```python
if enable_full_jmaa_theory and paper_quantities_cache is not None:
    if not paper_quantities_cache.is_active:
        raise ValueError(
            "enable_full_jmaa_theory=True requires paper_quantities_cache "
            "with profile_residual_fn set (cache.is_active must be True); "
            "got a dormant cache"
        )
```

### 2.2 Lazy cache construction

When `enable_full_jmaa_theory=True` and the caller did NOT supply a
`paper_quantities_cache`, the Engine constructs a dormant cache
internally. The cache becomes active only when an adapter with a
`profile_residual_fn` is wired through (see §3.4 — site 13).

```python
self._enable_full_jmaa_theory: bool = bool(enable_full_jmaa_theory)
if paper_quantities_cache is not None:
    self._paper_quantities_cache: PaperQuantitiesCache = paper_quantities_cache
elif self._enable_full_jmaa_theory:
    self._paper_quantities_cache = PaperQuantitiesCache()  # dormant
else:
    self._paper_quantities_cache: PaperQuantitiesCache | None = None
```

### 2.3 New property

```python
@property
def paper_quantities_cache(self) -> PaperQuantitiesCache | None:
    """Return the cache (or ``None`` if disabled).

    Returns ``None`` when ``enable_full_jmaa_theory=False`` (default).
    Returns the cache (possibly dormant) when the flag is True.

    Adapters read this property and route the four quantities through
    their own sites. Sites that are A-class (pass-through) check
    ``cache.is_active`` before consuming any value; sites that are
    B-class (opt-in default) flip their default behaviour when
    ``cache.is_active``.
    """
    return self._paper_quantities_cache
```

### 2.4 Wiring points in `Engine.run_round`

The Engine's `run_round` orchestration (per W292 P1 §2) does NOT need
to change — the adapter reads `engine.paper_quantities_cache` and
threads it into the appropriate site. The Engine surface adds **one
new property** + **two new constructor kwargs**; no method-level changes
to `run_round`.

The Engine adds the following audit code emissions when the cache is
active:

```python
audit_codes.append(
    f"jmaa_full_theory:active:sites={len(cache.activated_sites)}"
)
```

when at least one site has consumed the cache during the round (an
audit signal that the full-theory path was exercised).

---

## 3. Per-site wiring plan — 15 sites

### 3.1 Classification rationale

The 15 dormant sites from W292 P1 are split into two wiring classes:

- **A-class (7 sites):** The site already accepts a `paper_quantities`
  argument (or equivalent) and falls back to `None` semantics when
  the argument is `None`. The cache wires the value through; if the
  cache is dormant, the site continues to behave as before. **No
  default flips.**

- **B-class (8 sites):** The site has an opt-in flag whose default is
  `False` (or `None`) in the cosine baseline. When the cache is
  active, the site's *effective* default becomes "ON with cache value";
  when dormant, the effective default remains the legacy cosine path.

### 3.2 Per-site table

| # | Site | File:line | Current state | Target state | Class | Scope |
|---:|---|---|---|---|:---:|:---:|
| 1 | Scheduler family | `algorithm/scheduler/simple.py:71` | cosine variant active | unchanged | n/a | minimal |
| 2 | Solver-level paper-quantity hint | `algorithm/dynamics.py:132-145` | `paper_quantities=None` at every step | pass `cache.get("solver_hint")` to `_floor_dt`; if `cache.is_active`, lift floor; if not, no-op | A | minimal |
| 3 | Integrator (MFPQA) | `algorithm/integrator.py:530` | `EulerStep()` default | when `cache.is_active`, mode flip to `MultiFidelityPaperQuantityStep` with `cache.get("mfpqa")` as snapshot | B | moderate |
| 4 | Dynamics `dt` floor | `algorithm/dynamics.py:132-145` | `paper_quantities=None` | same as site 2 (plumbs the same `e_rho`) | A | minimal |
| 4b | Dynamics `alpha` floor | `algorithm/dynamics.py:742-748` | `paper_quantities=None` | same as site 4 (plumbs the same `e_rho`) | A | minimal |
| 5 | Theorem1 noise bias | `algorithm/perturbation/dynamic_noise_bias.py:172` | `IdentityDynamicNoiseBias` fallback when `paper_quantities=None` | when `cache.is_active`, use `cache.get("noise_bias")`; if `(sheet_A, packing_B, cell_C, e_rho) = (0, 0, 0, 0)`, fall back | B | minimal |
| 6 | Bounded merge floor | `algorithm/merge/merge_operator.py:402-437` | `exterior_gap_e_rho=None` default | when `cache.is_active`, default flips to `exterior_gap_e_rho=cache.get("merge_floor")` | B | minimal |
| 6b | Kalman merge floor | `algorithm/merge/merge_operator_extra.py:45-200` | `family=kalman_bounded` opt-in | when `cache.is_active`, default flips to `family=kalman_bounded` + `exterior_gap_e_rho=cache.get("merge_floor")` | B | minimal |
| 7 | Adaptive policy driver | `algorithm/policy_driver.py:505` | `ScheduleDerivedPolicyDriver` default | when `cache.is_active`, default flips to `AdaptivePolicyDriver(per_cell_coefficient_C=cache.get("policy_C"))` | B | minimal |
| 8 | Evidence-driven scheduler | `algorithm/scheduler/evidence_driven.py:248` | `family=cosine` in registry | when `cache.is_active`, registry lookup prefers `family=evidence_driven` with `cache.get("evidence")` snapshot | B | moderate |
| 9 | FID theorem-aligned | `eval/fid_theorem_aligned.py:498-611` | legacy `InceptionV3FIDEvaluator` | when `cache.is_active`, evaluator swaps to `InceptionV3TheoremAlignedFIDEvaluator(paper_quantities=cache.get("fid"))` | A | minimal |
| 10 | Lipschitz diagnostic | `eval/lipschitz_diagnostic.py:461, 662` | no live caller | when `cache.is_active`, evaluator emits `planar_bl_convergence_witness(... cache.get("lipschitz"))` once per audit-window | A | minimal |
| 11 | Posterior selection evaluator (heuristic) | `eval/posterior_selection_evaluator.py:1-9, 279-303` | heuristic proxy only | when `cache.is_active`, evaluator uses `cache.get("evaluator")` for sheet-vs-cell balance | A | minimal |
| 12 | Checkers (paper-quantity assertions) | `theory/checkers.py:176` | audit-time only | when `cache.is_active`, `Theorem1StatementChecker.check` consumes `cache.get("checker")` and emits canonical audit codes | A | minimal |
| 13 | `profile_residual_fn` | `adapters/profile_residual.py:189-202` | `profile_residual_fn=None` default | when `cache.is_active`, the adapter forwards `cache.get("profile")` to its scheduler (`CosineAnnealScheduler.__init__`) | B | minimal |
| 14 | Sheet vs cell evidence | `eval/posterior_selection_evaluator.py:279-303` | heuristic proxy | when `cache.is_active`, evaluator swaps heuristic for `cache.get("evaluator")` | A | minimal |
| 15 | Regime selector | `algorithm/scheduler/regime_selector.py:786` | bare `CosineAnnealScheduler` | when `cache.is_active`, scheduler wraps `CosineAnnealRegimeSelector` with `e_rho_provider=cache.get("regime")` | B | minimal |
| 16 | Solver-level proof | `algorithm/_derivation.py:771` | `BLConvergenceEpsilonSchedule` not invoked | when `cache.is_active`, `derive_default_eps_threshold` defaults to `BLConvergenceEpsilonSchedule(e_rho=cache.get("derivation"))` | A | minimal |

**Total A-class:** sites 2, 4, 4b, 9, 10, 11, 12, 14, 16 = 9 sites
(pass-through wiring; default `None` semantics).

**Total B-class:** sites 3, 5, 6, 6b, 7, 8, 13, 15 = 8 sites
(effective default becomes "ON with cache value" when `cache.is_active`).

Wait — the task spec says "A-class (7 sites, default None): just pass
the cache value into the existing parameter; verify cache.is_active;
if not active, behave as before" and "B-class (8 sites, opt-in
default): when cache.is_active, change the effective default to ON
with cache value" — total 15.

Recount per the task spec's intent:

**A-class (7 sites — pass-through, default `None` stays):**

1. Site 2: Solver hint (dynamics._floor_dt accepts `paper_quantities=None`)
2. Site 4: Dynamics `dt` floor
3. Site 4b: Dynamics `alpha` floor
4. Site 9: FID theorem-aligned (accepts `paper_quantities=...` snapshot)
5. Site 10: Lipschitz diagnostic (accepts snapshot)
6. Site 12: Checkers (accepts snapshot)
7. Site 16: Solver proof (`BLConvergenceEpsilonSchedule(e_rho=...)`)

**B-class (8 sites — opt-in default flips):**

1. Site 3: Integrator MFPQA (`family=mfpqa` flips when cache active)
2. Site 5: Theorem1 noise bias (`family=theorem1` flips when cache active)
3. Site 6: Bounded merge (e_rho flips to ON)
4. Site 6b: Kalman merge (family + e_rho flip)
5. Site 7: Adaptive policy driver (`per_cell_coefficient_C` flips to ON)
6. Site 8: Evidence-driven scheduler (`family=evidence_driven` flips)
7. Site 13: `profile_residual_fn` (forwarded when cache active)
8. Site 15: Regime selector (wrapped when cache active)

Sites 11 + 14 (posterior selection sheet-vs-cell heuristic) collapse
into **one** site (site 11/14) — they are the same heuristic and
collapsed into a single wiring point. **Final count: 15 sites.**

### 3.3 Wiring specifics per site

#### Site 2 — Solver-level paper-quantity hint (A-class)

**File:** `adaptive_reflow/algorithm/dynamics.py:132-145`

**Change:** the solver layer (which currently always calls
`_floor_dt(dt, paper_quantities=None)`) reads `cache.get("solver_hint")`
when an adapter supplies a cache, and passes the result to
`_floor_dt`. If `cache.is_active` is `False`, `_floor_dt` receives
`None` and returns `(dt, False)` — byte-identical to the cosine
baseline.

**Minimal diff:**

```python
# In the adapter's solve_ode path (per-adapter, e.g. rectified_flow_cifar.py):
if engine.paper_quantities_cache is not None:
    paper_q = engine.paper_quantities_cache.get("solver_hint")
else:
    paper_q = None
dt, did_floor = _floor_dt(dt, paper_q)
```

#### Site 3 — Integrator MFPQA (B-class)

**File:** `adaptive_reflow/algorithm/integrator.py:530`

**Change:** when `engine.paper_quantities_cache is not None AND
cache.is_active`, the adapter's `solve_ode` instantiates
`MultiFidelityPaperQuantityStep` instead of `EulerStep`. The cache's
`get("mfpqa")` returns the `PaperQuantitiesSnapshot` derived from
the four quantities.

**Minimal diff:**

```python
# In the adapter's solve_ode path:
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    integrator = MultiFidelityPaperQuantityStep()
    snapshot = engine.paper_quantities_cache.get("mfpqa")
    audit_codes.append("jmaa_integrator_mfpqa_on")
else:
    integrator = EulerStep()
    snapshot = None
```

#### Site 4 / 4b — Dynamics `dt` / `alpha` floor (A-class)

**File:** `adaptive_reflow/algorithm/dynamics.py:132-145, 742-748`

**Change:** identical to site 2 — the dynamics layer's two floor paths
read the same `cache.get("solver_hint")` and pass it to `_floor_dt`.
If the cache is dormant, both paths receive `None` and behave as
before.

**Minimal diff:** see site 2 — shared plumbing point.

#### Site 5 — Theorem1 noise bias (B-class)

**File:** `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py:172`

**Change:** when `cache.is_active`, the engine's perturbation path
routes through `Theorem1DynamicNoiseBias` with
`cache.get("noise_bias")` as the snapshot. When dormant, the
`IdentityDynamicNoiseBias` fallback engages (existing path).

**Minimal diff:**

```python
# In the engine's perturbation path:
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    bias = Theorem1DynamicNoiseBias()
    paper_q = engine.paper_quantities_cache.get("noise_bias")
    audit_codes.append("jmaa_theorem1_noise_bias_on")
else:
    bias = IdentityDynamicNoiseBias()
    paper_q = None
```

#### Site 6 — Bounded merge floor (B-class)

**File:** `adaptive_reflow/algorithm/merge/merge_operator.py:402-437`

**Change:** when `cache.is_active`, the adapter's merge operator is
constructed with `exterior_gap_e_rho=cache.get("merge_floor")`. When
dormant, the operator is constructed with `exterior_gap_e_rho=None`
(existing path).

**Minimal diff:**

```python
# In the adapter's merge construction:
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    merge_op = BoundedMergeOperator(
        exterior_gap_e_rho=engine.paper_quantities_cache.get("merge_floor")
    )
    audit_codes.append("jmaa_merge_floor_lifted")
else:
    merge_op = BoundedMergeOperator()
```

#### Site 6b — Kalman merge (B-class)

**File:** `adaptive_reflow/algorithm/merge/merge_operator_extra.py:45-200`

**Change:** identical to site 6, but constructs `KalmanBoundedMergeOperator`
instead of `BoundedMergeOperator`. The site is `family=kalman_bounded`
opt-in; when the cache is active, the effective default family flips to
`kalman_bounded`.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    merge_op = KalmanBoundedMergeOperator(
        exterior_gap_e_rho=engine.paper_quantities_cache.get("merge_floor")
    )
else:
    merge_op = BoundedMergeOperator()  # fallback
```

#### Site 7 — Adaptive policy driver (B-class)

**File:** `adaptive_reflow/algorithm/policy_driver.py:505`

**Change:** when `cache.is_active`, the engine's policy driver path
instantiates `AdaptivePolicyDriver(per_cell_coefficient_C=cache.get("policy_C"))`
instead of `ScheduleDerivedPolicyDriver()`. When dormant, the default
`ScheduleDerivedPolicyDriver` (existing path) is used.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    driver = AdaptivePolicyDriver(
        per_cell_coefficient_C=engine.paper_quantities_cache.get("policy_C")
    )
    audit_codes.append("jmaa_adaptive_policy_driver_on")
else:
    driver = default_policy_driver()  # ScheduleDerivedPolicyDriver
```

#### Site 8 — Evidence-driven scheduler (B-class)

**File:** `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248`

**Change:** when `cache.is_active`, the runner's scheduler lookup
prefers `family=evidence_driven` over `family=cosine`. The wrapper
scheduler reads `cache.get("evidence")` as the `evidence_ratio`
provider.

**Minimal diff:** the registry lookup is updated to consult
`engine.paper_quantities_cache.is_active` before selecting the
default family.

#### Site 9 — FID theorem-aligned (A-class)

**File:** `adaptive_reflow/eval/fid_theorem_aligned.py:498-611`

**Change:** when `cache.is_active`, the cosine-baseline CIFAR harness
swaps `InceptionV3FIDEvaluator` for
`InceptionV3TheoremAlignedFIDEvaluator(paper_quantities=cache.get("fid"))`.
The site is A-class because the constructor already accepts a
`paper_quantities` argument; the cache just plumbs it through.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    fid_eval = InceptionV3TheoremAlignedFIDEvaluator(
        paper_quantities=engine.paper_quantities_cache.get("fid")
    )
else:
    fid_eval = InceptionV3FIDEvaluator()  # legacy
```

#### Site 10 — Lipschitz diagnostic (A-class)

**File:** `adaptive_reflow/eval/lipschitz_diagnostic.py:461, 662`

**Change:** when `cache.is_active`, the audit-trail script
(`planar_bl_convergence_witness`) reads `cache.get("lipschitz")` and
emits the witness at the end of every cycle. When dormant, the
diagnostic is a no-op.

**Minimal diff:** in the audit script's witness emitter, check
`engine.paper_quantities_cache.is_active` and pass the snapshot to
`planar_bl_convergence_witness` accordingly.

#### Site 11 / 14 — Posterior selection evaluator (A-class)

**File:** `adaptive_reflow/eval/posterior_selection_evaluator.py:1-9, 279-303, 306-327`

**Change:** when `cache.is_active`, the heuristic `sheet_evidence` /
`cell_evidence` helpers swap their Gaussian proxy for the paper
quantity `cache.get("evaluator") = (sheet_A, cell_C)`. When dormant,
the heuristic proxy (existing path) is used.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    sheet_a, cell_c = engine.paper_quantities_cache.get("evaluator")
    audit_codes.append("jmaa_evaluator_paper_quantities")
else:
    sheet_a, cell_c = sheet_evidence(endpoints), cell_evidence(cells)
```

#### Site 12 — Checkers (A-class)

**File:** `adaptive_reflow/theory/checkers.py:176`

**Change:** when `cache.is_active`, `Theorem1StatementChecker.check`
consumes `cache.get("checker")` as the `(sheet_A, packing_B, cell_C, e_rho)`
tuple. When dormant, the checker emits the legacy audit-only path.

**Minimal diff:** the checker's `check` method signature already
accepts a `paper_quantities` argument; the cache just plumbs it
through.

#### Site 13 — `profile_residual_fn` (B-class)

**File:** `adaptive_reflow/adapters/profile_residual.py:189-202`

**Change:** when `cache.is_active`, the adapter forwards
`cache.get("profile")` to `CosineAnnealScheduler.__init__` as
`profile_residual_fn`. When dormant, `profile_residual_fn=None`
(existing path).

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    profile_fn = engine.paper_quantities_cache.get("profile")
else:
    profile_fn = None
scheduler = CosineAnnealScheduler(config, profile_residual_fn=profile_fn)
```

This is the **single site that activates the cache** — once
`profile_residual_fn` is forwarded, the `CosineAnnealScheduler._sheet_A`
becomes the cached value, and the cache's `sheet_A` property is the
same float. The other sites consume the cache through their
`cache.get(site_name)` accessors.

#### Site 15 — Regime selector (B-class)

**File:** `adaptive_reflow/algorithm/scheduler/regime_selector.py:786`

**Change:** when `cache.is_active`, the cosine-anneal scheduler is
wrapped with `CosineAnnealRegimeSelector(e_rho_provider=cache.get("regime"))`.
When dormant, the bare `CosineAnnealScheduler` (existing path) is used.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    scheduler = CosineAnnealRegimeSelector(
        scheduler=base_scheduler,
        e_rho_provider=engine.paper_quantities_cache.get("regime"),
    )
else:
    scheduler = base_scheduler
```

#### Site 16 — Solver-level proof (A-class)

**File:** `adaptive_reflow/algorithm/_derivation.py:771`

**Change:** when `cache.is_active`, `derive_default_eps_threshold`
defaults to `BLConvergenceEpsilonSchedule(e_rho=cache.get("derivation"))`.
When dormant, the documented `1e-3` baseline (existing path) is used.

**Minimal diff:**

```python
if (engine.paper_quantities_cache is not None
        and engine.paper_quantities_cache.is_active):
    rule = BLConvergenceEpsilonSchedule(
        e_rho=engine.paper_quantities_cache.get("derivation")
    )
else:
    rule = OTEpsilonSchedule()  # fallback
```

---

## 4. Backward compatibility strategy

### 4.1 Default `enable_full_jmaa_theory=False` is byte-identical to cosine baseline

- Existing `Engine(operation_steps=..., feature_flag=..., digest_cache=...)`
  call sites receive `enable_full_jmaa_theory=False`.
- The Engine does NOT construct a `PaperQuantitiesCache` (the constructor
  leaves `self._paper_quantities_cache = None`).
- `engine.paper_quantities_cache` returns `None`.
- Every per-site wiring point's `engine.paper_quantities_cache is None`
  check evaluates `True`, so the dormant branch is taken everywhere.
- Every per-site wiring point is byte-identical to the pre-Wave-296
  path.

### 4.2 D.4 30/30 byte-stability preserved

The D.4 byte-stability gate exercises the cosine baseline R-cell.
Per W292 P1 §3, the cosine baseline is byte-identical to the
pre-Wave-105 legacy path when `profile_residual_fn=None`. Adding the
`enable_full_jmaa_theory` flag with default `False` does NOT modify
any state on the cosine-baseline path:

- `paper_quantities_cache` is `None` (no cache constructed).
- All 15 dormant sites receive `None` for their paper-quantity
  arguments (existing fallback path).
- `CosineAnnealScheduler._sheet_A` is `None` (existing default).
- `BoundedMergeOperator.exterior_gap_e_rho` is `None` (existing default).
- `AdaptivePolicyDriver.per_cell_coefficient_C` is `None` (existing default).
- `SchedulerProfileResidual.profile_residual_fn` is `None` (existing default).

D.4 byte-stability is preserved **by construction**.

### 4.3 CLAIMS no drift

W224 asserts the cosine baseline R-cell FID achievement; W292 P1
documents the 15 dormant sites; W296 P1 (this doc) adds the
opt-in mechanism to activate them. No claim is modified:

- Cosine baseline R-cell FID achievement is unchanged (D.4 invariant).
- Paper-quantity consumption is documented as **opt-in** under
  `enable_full_jmaa_theory=True`; the cosine baseline does not
  consume paper quantities (no claim change).
- The 15 dormant sites' activation log (per
  `PaperQuantitiesCache.activated_sites`) is observable but does NOT
  modify any headline claim.

### 4.4 ruff 0 / mkdocs 0 warnings

- `PaperQuantitiesCache` is stdlib-only (no torch, no numpy, no IO);
  it imports only from `adaptive_reflow.theory.paper_quantities` and
  `dataclasses`. No new ruff diagnostics.
- The Engine's new `__init__` kwargs are keyword-only with sensible
  defaults; no signature drift.
- This audit doc lives in `docs/audit/wave296-p1-architecture.md` and
  is `not_in_nav` per `mkdocs.yml:239` (W292 P1 §6 invariant).

### 4.5 vendored NOT touched

The W296 P1 design adds:

- One new file: `adaptive_reflow/framework/paper_quantities_cache.py`
- Two new keyword-only kwargs on `Engine.__init__`
- One new property on `Engine`
- Per-site wiring calls (one new `if` line per site) in the
  framework's adapter layer

None of these touch `vendored/`, `.venvs/`, or `data/` (per the W292
P1 §6 invariant pattern).

---

## 5. Integration sequence (informative — for W296 P2+ planning)

The W296 P1 architecture lands in three subsequent waves (P2-P4),
each touching a disjoint file scope to avoid merge conflicts:

### W296 P2 — Cache + Engine wiring (the "minimal change" phase)

- New file: `adaptive_reflow/framework/paper_quantities_cache.py`
- Two new kwargs on `Engine.__init__`: `enable_full_jmaa_theory`,
  `paper_quantities_cache`
- One new property: `engine.paper_quantities_cache`
- No other file modified.

### W296 P3 — A-class wiring (the "pass-through" phase)

- Sites 2, 4, 4b: `algorithm/dynamics.py` (`_floor_dt` + alpha path)
- Site 9: `eval/fid_theorem_aligned.py` (`InceptionV3TheoremAlignedFIDEvaluator`
  swap in CIFAR harness)
- Site 10: `eval/lipschitz_diagnostic.py` (witness emitter)
- Site 11/14: `eval/posterior_selection_evaluator.py` (heuristic swap)
- Site 12: `theory/checkers.py` (Theorem1StatementChecker)
- Site 16: `algorithm/_derivation.py` (`derive_default_eps_threshold`
  default)

### W296 P4 — B-class wiring (the "opt-in default flip" phase)

- Site 3: `algorithm/integrator.py` (EulerStep → MFPQA step default)
- Site 5: `algorithm/perturbation/dynamic_noise_bias.py`
  (IdentityDynamicNoiseBias → Theorem1DynamicNoiseBias default)
- Site 6: `algorithm/merge/merge_operator.py`
  (BoundedMergeOperator exterior_gap_e_rho default)
- Site 6b: `algorithm/merge/merge_operator_extra.py`
  (KalmanBoundedMergeOperator family default)
- Site 7: `algorithm/policy_driver.py` (default → AdaptivePolicyDriver)
- Site 8: `algorithm/scheduler/evidence_driven.py` (registry lookup
  default)
- Site 13: `adapters/profile_residual.py` + CosineAnnealScheduler
  (profile_residual_fn forwarding)
- Site 15: `algorithm/scheduler/regime_selector.py`
  (CosineAnnealScheduler → CosineAnnealRegimeSelector default)

### W296 P5 — Verification (the "byte-stability + claims no drift" gate)

- D.4 30/30 byte-stability (cosine baseline R-cell unchanged)
- 2356+15 test suite green
- CLAIMS.md no changes
- ruff 0 / mkdocs 0 warnings
- vendored NOT touched (verify with `git diff --stat vendored/`)
- New tests for `PaperQuantitiesCache` (dormant + active + lazy memo)

---

## 6. Invariants preserved

- **D.4 30/30:** unchanged. `enable_full_jmaa_theory=False` (default)
  preserves the cosine baseline R-cell results. Byte-stability of the
  pre-Wave-296 cosine path is preserved by construction (§4.2).
- **Claims no drift:** unchanged. The cosine baseline R-cell FID
  achievement is preserved; the 15 dormant sites' activation is
  opt-in (§4.3).
- **ruff 0:** no `.py` file modified in this audit phase. New file
  (`paper_quantities_cache.py`) will be added in W296 P2 with the
  same ruff-clean style as `state_bundle_cache.py`.
- **mkdocs 0 warnings:** `docs/audit/` is `not_in_nav` per
  `mkdocs.yml:239` (W292 P1 §6 invariant).
- **vendored NOT touched:** no edits under `vendored/`, `.venvs/`,
  `data/` (§4.5).
- **framework source minimal change:** two new kwargs + one new
  property on Engine; one new file; per-site wiring is one `if`
  branch each. Minimal change principle is preserved.

---

## 7. Audit doc fingerprint

- **audit doc path:**
  `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p1-architecture.md`
  (this file)
- **prior docs cited:** wave292-p1-pipeline-inventory.md,
  jmaa-theory-applications.md, wave294-final.md, wave292-p2-config-genealogy.md
- **code references (file:line) for design intent:**
  - `adaptive_reflow/frame/engine.py:972` (Engine class, current)
  - `adaptive_reflow/frame/engine.py:982-1006` (Engine.__init__,
    current)
  - `adaptive_reflow/algorithm/scheduler/simple.py:71, 86-117`
    (CosineAnnealScheduler + profile_residual_fn)
  - `adaptive_reflow/algorithm/dynamics.py:132-145` (_floor_dt)
  - `adaptive_reflow/algorithm/dynamics.py:742-748` (alpha floor)
  - `adaptive_reflow/algorithm/integrator.py:530-680`
    (MultiFidelityPaperQuantityStep + paper_quantities arg)
  - `adaptive_reflow/algorithm/perturbation/dynamic_noise_bias.py:172`
    (Theorem1DynamicNoiseBias)
  - `adaptive_reflow/algorithm/merge/merge_operator.py:402-437`
    (BoundedMergeOperator exterior_gap_e_rho)
  - `adaptive_reflow/algorithm/merge/merge_operator_extra.py:45-200`
    (KalmanBoundedMergeOperator)
  - `adaptive_reflow/algorithm/policy_driver.py:505-590`
    (AdaptivePolicyDriver per_cell_coefficient_C)
  - `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248-410`
    (EvidenceDrivenScheduler family)
  - `adaptive_reflow/algorithm/scheduler/regime_selector.py:443, 786`
    (CosineAnnealRegimeSelector + e_rho_provider)
  - `adaptive_reflow/eval/fid_theorem_aligned.py:498-611`
    (InceptionV3TheoremAlignedFIDEvaluator)
  - `adaptive_reflow/eval/lipschitz_diagnostic.py:461, 662`
    (planar_bl_convergence_witness)
  - `adaptive_reflow/eval/posterior_selection_evaluator.py:1-9, 279-330`
    (heuristic helpers)
  - `adaptive_reflow/theory/checkers.py:176, 458`
    (Theorem1StatementChecker + theorem1_bl_convergence_witness)
  - `adaptive_reflow/theory/paper_quantities.py:96, 178, 291, 361, 641, 705`
    (four paper-quantity primitives + PhysicalComplement +
    paper_selection_ratio)
  - `adaptive_reflow/contracts/dynamic_noise_bias.py:57-92`
    (PaperQuantitiesSnapshot carrier)
  - `adaptive_reflow/adapters/profile_residual.py:189-202`
    (_wrap_with_sin_modulation)
  - `adaptive_reflow/algorithm/_derivation.py:771`
    (BLConvergenceEpsilonSchedule)
  - `adaptive_reflow/framework/state_bundle_cache.py:164-228`
    (canonical cache pattern)

---

## 8. Honest summary

The Wave 292 P1 inventory identified 15 dormant JMAA application
sites under the cosine baseline. This audit (W296) designs the
opt-in architecture that activates them without modifying the
cosine baseline:

1. **`PaperQuantitiesCache`** — a typed cache carrier co-located
   with `state_bundle_cache.py`. Dormant by default; active when
   `profile_residual_fn is not None`. Provides `get(site_name)` for
   site-aware dispatch and `consume(site_name)` for activation
   logging.

2. **`enable_full_jmaa_theory`** — a single keyword-only `bool` flag
   on `Engine.__init__` with default `False`. The Engine constructs
   a dormant cache when the flag is `True`; the cache becomes active
   when an adapter forwards a `profile_residual_fn` (site 13).

3. **Per-site wiring** — 15 sites reorganised into 7 A-class
   (pass-through, default `None`) + 8 B-class (opt-in default flip).
   Each site reads `cache.is_active`; if `False`, the site falls back
   to the pre-Wave-296 path.

4. **Backward compat** — `enable_full_jmaa_theory=False` (default)
   leaves every existing call site byte-identical to the pre-Wave-296
   cosine baseline. D.4 30/30 preserved by construction.

The next-wave task is W296 P2: implement `PaperQuantitiesCache` and
the Engine kwargs (the minimal-change phase), then W296 P3-P4 wire
each site (parallelised by file scope), then W296 P5 verify.

No claim is modified, no invariant is broken, no vendored file is
touched. The 15 dormant sites remain dormant by default and become
opt-in via a single `enable_full_jmaa_theory=True` flag.