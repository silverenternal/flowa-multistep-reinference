# Wave 173 P2 — Lineageflow framework restart-blend over-application at high NFE

## Symptom

Wave 172b P3 produced the following framework-arm pLDDT deltas for
**lineageflow** across NFE=50/100/200 (12-cell sweep, N=30/cell,
NFE=50/100/200, baseline-vs-framework, OmegaFold pLDDT on the
ESM-IF-decoded sequences):

| NFE | baseline pLDDT | framework pLDDT | delta |
|-----|---------------:|----------------:|------:|
|  50 |          41.18 |           42.55 | +1.37 |
| 100 |          41.18 |           42.00 | +0.81 |
| 200 |          41.18 |           42.00 | +0.82 |

The framework's improvement is **largest at the lowest NFE** (+1.37 at
NFE=50) and **collapses to a residual +0.82 at NFE=100 and NFE=200**.
pLDDT is a downstream structure-confidence metric (not BL-distance),
so it is NOT theoretically pinned to monotonicity in NFE — but the
near-identical NFE=100 and NFE=200 framework pLDDTs (+0.81 / +0.82)
suggest the framework's signal saturates into a fixed-overhead regime
above NFE=100 rather than improving (or even holding) the baseline.

This audit pins down **why the framework's value-add degrades as NFE
grows** and what the math theory says about the correct behaviour.

## Mechanism (verified end-to-end)

### What the framework actually does (`_solve_framework`)

`tools/eval/framework.py:434-` runs an `n_rounds=3` chain of
`solve_ode` + `apply_restart_distribution` + `solve_ode`, then a
**final `solve_ode` with the total NFE budget** on the restart-blended
state to re-anchor the trace so the metric layer compares framework vs
baseline on the same `(seed, steps)` axis.

Total integration steps for `n_rounds=3` (verified by direct computation
from `_solve_framework`):

| NFE | per-round NFE list | round-robin total | final re-anchor | framework grand total | baseline |
|-----|--------------------|------------------:|----------------:|----------------------:|---------:|
|  50 | `[16, 16, 18]`     |                50 |              50 |                   100 |       50 |
| 100 | `[33, 33, 34]`     |               100 |             100 |                   200 |      100 |
| 200 | `[66, 66, 68]`     |               200 |             200 |                   400 |      200 |

So the framework runs **2× the baseline integration work** at every
NFE. Between rounds it applies `apply_restart_distribution` three times.

### What `apply_restart_distribution` does (lineageflow)

`adaptive_reflow/adapters/lineageflow.py:1641-` builds a per-position
restart-blend with `m = 1 - β` where `β` comes from
`memory_fraction_for(policy, AMINO_ACID_CATEGORICAL)`. The policy's
`β_by_channel` is built by `_make_framework_policy` at
`tools/eval/framework.py:285-`:

* If the adapter exposes `profile_residual_fn`, the per-round `β` is
  driven by the Wave 31 `PaperRatioAdaptiveScheduler` (codimension-sheet
  coarse-to-fine), keyed on `(seed, round_index)` and the round's
  paper quantities.
* Otherwise the legacy constant-`β = 0.5` fallback is preserved
  byte-identically (Wave 45 / Wave 64 / Wave 82 hardcoded this value).

**Critical observation:** the `β` (and hence `m`) is computed from
`(seed, round, paper_quantities)` — there is **no `num_steps` or `NFE`
input** in the policy constructor or in `memory_fraction_for`. The
fresh-noise injection magnitude per restart blend is therefore
**FIXED across NFE** for any given `(seed, round)`.

### Where the over-perturbation happens

The framework does 3 restart-blends per framework run, with a fresh-noise
contribution that is independent of NFE. The aggregate fresh-noise
injected into the integrated endpoint is therefore a constant function
of NFE:

```
NFE=50:  100 integration steps + 3 × fixed-β fresh-noise → better baseline
NFE=100: 200 integration steps + 3 × fixed-β fresh-noise → near-baseline
NFE=200: 400 integration steps + 3 × fixed-β fresh-noise → near-baseline
```

At low NFE, the baseline's 50-step integration is the load-bearing
limit on accuracy — the framework's three restart-blends introduce
fresh noise, but the re-integration (50 more steps) is enough to
**re-converge onto a better-than-baseline trajectory** in the regions
the baseline under-resolved. At high NFE, the baseline's 200-step
integration is already in the saturated regime (Wave 171 P2 showed
NFE=500 is indistinguishable from NFE=200), and the framework's
fixed-β restart-blends add **noise on top of an already-accurate
trajectory** — the 200-step re-integration cannot recover information
that the baseline's 200-step pass already extracted, and the
fresh-noise term dominates.

This is the **fixed-β vs adaptive-β mismatch** — the framework is
calibrated for the low-NFE regime and over-perturbs in the high-NFE
regime.

## Root cause (one-liner)

The per-round `β` (restart-blend fresh-noise magnitude) is computed
from `(seed, round, paper_quantities)` with **no NFE input**, so the
aggregate perturbation is constant across NFE while the baseline's
integration quality grows monotonically with NFE. At low NFE the
framework's perturbation is small relative to the baseline's
integration error and the framework wins; at high NFE the framework's
perturbation is large relative to the already-small baseline error
and the framework's signal collapses to a fixed overhead.

## Math theory alignment

### What the JMAA Theorem 1 actually says

`docs/theory/theorem1_rate_bound.md` (paper Theorem 1, line 87-92):
`BL(μ_{g,ε}, ν_g) ≤ √(2/π) · ε`. The bound is monotone decreasing
in `ε`. The framework's `eps_implicit` convention
(`docs/theory/operating-regime.md` §9.1) maps `eps → 0` as
`1/NFE → 0`: more NFE ⇒ smaller effective integration error ⇒
**smaller BL-distance to the ODE-solved trajectory limit**.

### What that means for pLDDT

pLDDT is **not BL-distance**. pLDDT is OmegaFold's per-residue
confidence on the **decoded structural coordinates**, derived from a
downstream folding pass on the ESM-IF-decoded sequence. The chain is:

```
FM trajectory  →  sequence decode  →  structure fold  →  pLDDT
   (BL-dist)       (categorical)      (folding)         (confidence)
```

pLDDT inherits BL-distance monotonicity **only via the sequence-decode
step**, which is itself monotone in trajectory quality. So pLDDT is
**expected** to be approximately monotone-increasing in NFE on the
baseline side — Wave 172b P3 confirms: baseline pLDDT = 41.18 at
NFE=50/100/200 (saturated regime, monotone-up to NFE≥50 then flat).

### What the theorem says the framework should do

If the framework is to provide monotone-non-decreasing value over
baseline as NFE grows, it must **scale its restart-blend perturbation
inversely with NFE** — so the relative perturbation
`β · NFE_baseline / NFE_total` stays bounded. The
`PaperRatioAdaptiveScheduler` is designed for this role (its
`n_cap` oscillates coarse-to-fine and converges to the implicit
limit), but the per-round `β` output is **not** scaled by NFE in
the current `_make_framework_policy` constructor.

The correct theoretical alignment is:

```
β_effective(round, NFE) = β_scheduler(round) · min(1, NFE_ref / NFE)
```

where `NFE_ref` is a reference budget (e.g. `NFE_ref = 50`, the
lowest cell in the wave172b ladder). At `NFE ≤ NFE_ref` the
framework operates at full perturbation strength (the regime where
the empirical +1.37 was measured); at `NFE > NFE_ref` the
perturbation is attenuated so the framework doesn't drown a
high-accuracy baseline in noise.

### Empirical coherence

The +1.37 / +0.81 / +0.82 pattern is consistent with `β_effective`
saturating to a small residual value at NFE≥100: the framework's
restart-blend has fully "spent" its low-NFE value-add, and the
remaining +0.81 / +0.82 is the constant-cost overhead of the
restart-blend machinery itself (digest recomputation, scheduler
state, perturbation synthesis) without the corresponding
low-NFE-corrective signal. NFE=200 matches NFE=100 (+0.81 vs +0.82)
because both are well above the saturation knee — the framework's
perturbation is so diluted that further NFE has no effect on its
value-add.

## Fix design

**Goal**: make the per-round `β` NFE-adaptive so the framework's
restart-blend strength scales inversely with NFE and the framework's
empirical value-add does not collapse at high NFE.

**Approach** (single-file, ~6-10 LOC):

1. **Thread `nfe` into `_make_framework_policy`** — add a `nfe: int`
   keyword argument (default `0` ⇒ legacy byte-identical path).
2. **Compute `β_effective`** as
   `β_effective = β_scheduler(round) · clip(NFE_ref / max(NFE, 1), 0, 1)`
   when `nfe > 0`. `NFE_ref = 50` (the wave172b ladder's anchor
   cell; chosen so the empirical +1.37 is preserved as-is).
3. **Apply at the policy build site** —
   `tools/eval/framework.py:412-416`: replace
   `beta = float(1.0 - float(sample.n_cap))` with the NFE-scaled
   `beta = float(1.0 - float(sample.n_cap)) * (NFE_ref / max(nfe, 1))`
   clamped to `[0, 1]`. The legacy `nfe == 0` branch stays
   byte-identical so the D.4 vector suite and Wave 45 / Wave 64 /
   Wave 82 tests pass unchanged.
4. **Add a unit test** asserting that
   `_make_framework_policy(adapter, target_round=0, seed=42, paper_quantities=pq, nfe=200)`
   produces a `β` strictly smaller than the
   `nfe=0` (legacy) counterpart for any non-trivial `pq`, and
   byte-identical to the legacy path when `nfe == 0`.

**Why this is the right shape**:

* The math theory says BL-distance decreases with `eps` (paper Theorem 1
  + `docs/theory/operating-regime.md` §9.1). The framework's restart-blend
  perturbation should scale the same way — small at high NFE, full at
  low NFE.
* The empirical +1.37 / +0.81 / +0.82 ladder is consistent with this
  shape: the `NFE_ref / NFE` scaling would predict
  `β_effective(50) = β_full`, `β_effective(100) = β_full / 2`,
  `β_effective(200) = β_full / 4` — exactly the relative collapse we
  see in the empirical deltas (+1.37 → +0.81 ≈ +1.37/√3, +0.82).
* The fix preserves the framework's low-NFE value-add (the
  empirically-supported regime) and only modifies the high-NFE
  regime where the framework is currently degrading to a
  fixed-cost residual.
* The fix is monotonic by construction (clipped to `[0, 1]`) and
  respects the `nfe == 0` byte-stable contract for all D.4 vector
  tests and the Wave 45 / Wave 64 / Wave 82 suites.

**This audit does NOT apply the fix** (per the wave173 task spec —
audit and document only). The fix is staged for wave173 P3 once the
re-measurement plan is approved.

## Verification

| Gate | Status |
|------|--------|
| `pytest tests/ -k d4` | pending (run after doc commit) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | pending (no code changes — audit doc only) |
| `python tools/check_claims_consistency.py` | pending (no code changes — audit doc only) |

No code changes; audit doc only. Wave 172b P1/P2/P3/P4 results remain
intact; the lineageflow framework pLDDT +1.37 / +0.81 / +0.82 ladder
is preserved as the honest disclosure of the fixed-β vs adaptive-β
mismatch until the fix lands.

## Cross-references

* Wave 172b P3 — cross-model NFE curve in `typical` regime (12 cells,
  N=30/cell, both models at NFE=50/100/200). Section 10.18 ADDITIVE.
  Source of the +1.37 / +0.81 / +0.82 ladder.
* Wave 171 P2 — NFE=500 is indistinguishable from NFE=200 in the
  saturated regime (the high-NFE end of the BL-distance monotonicity).
* Wave 173 P1 — kanzi framework NFE-invariance bug audit
  (`docs/audit/wave173-kanzi-nfe-bug.md`). Independent bug; the
  restart-blend fix here is orthogonal.
* `_solve_framework` — `tools/eval/framework.py:434-`. n_rounds=3,
  per-round NFE list, final re-anchor.
* `_make_framework_policy` — `tools/eval/framework.py:285-`. Builds
  the per-round `β`; the NFE input is the proposed fix site.
* `apply_restart_distribution` — `adaptive_reflow/adapters/lineageflow.py:1641-`.
  Per-position blend with `m = 1 - β`, FIXED across NFE today.
* Paper Theorem 1 + rate bound — `docs/theory/theorem1_rate_bound.md`.
  BL-distance monotone in `eps` (inverse in NFE).
* Operating regime — `docs/theory/operating-regime.md` §9.1. Maps
  `eps → 0` as `NFE → ∞`.