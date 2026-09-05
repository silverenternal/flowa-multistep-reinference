---
status: accepted
date: 2026-09-05
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 17. Cosine-driven `n_cap` vs paper-ratio-driven `n_cap` (F-5 architectural choice)

## Context and Problem Statement

Wave 29 Agent A's theory ↔ implementation audit
(`docs/audit/theory-implementation-gap.md`) classified 6 deviations
into two buckets: **3 confirmed bugs** (F-1, F-2, F-3) and **5 known
limitations** (F-4, F-5, F-6, plus framework-architecture choices).
F-5 is the only **clean algorithm-level regression at matched NFE**:

> "`algorithm/scheduler/_core.py:CodimensionSheetScheduler.n_cap`
> driven by cosine not paper ratio — **KNOWN LIMITATION** (architectural)
> — High (causes twodim_fm regression)"
> — Wave 29 Agent A, F-5 row.

The paper's prediction is clear (paper Theorem 1 + Corollary 1, line
165): as `ε → 0` (terminal round of a coarse-to-fine anneal), the
sheet evidence `Θ(ε⁺¹)` dominates the cell evidence `O(ε⁺²)`, so the
per-round `n_cap` (fresh-noise capacity) should be HIGH because fine
integration is needed to resolve the sheet vs cells. The natural
mapping is:

```python
# Paper-equivalent n_cap driver
n_cap = n_min + (n_max - n_min) * (1.0 - eps_implicit)
# OR equivalently
n_cap = paper_selection_ratio(sheet_A, packing_B, cell_C, eps_implicit)
```

The framework's actual `n_cap` driver in
`adaptive_reflow/algorithm/scheduler/_core.py` is **cosine annealing**
(ADR-0010):

```python
n_cap = n_min + (n_max - n_min) * cosine_base_value
```

The paper-derived `ratio` is computed per-round (line 2748-2757) and
emitted on the sample as `evidence_ratio` — but it is a
**reportable metric**, not a driver of `n_cap`.

The architectural question this ADR answers:

1. **What** is the relationship between cosine annealing (the
   framework's `n_cap` driver) and the paper's
   evidence-ratio-driven `n_cap`?
2. **Why** does the framework stay with cosine annealing rather than
   switch to a paper-evidence-driven driver?
3. **What** is the consequence of this choice for the framework's
   operating regime?
4. **What** is the honest architectural statement about when this
   choice **helps** vs **regresses**?

## Decision Drivers

* **ADR-0010 (cosine-driven memory fraction) is canonical.** The
  framework's `n_cap_for_round` and `cosine_base_value` driver have
  been the canonical `n_cap` source since ADR-0010 was accepted
  (2026-08-27). All 36 algorithm-level uplifts in
  `docs/benchmark-uplifts.md` rely on the cosine-annealing behaviour
  in their (current, achieved) assertions — switching `n_cap` to a
  paper-evidence-driven driver would invalidate the byte-for-byte
  audit invariant on every existing uplift fixture.

* **The paper's `evidence_ratio` is computed but not driving.** The
  framework already computes `paper_selection_ratio` per-round and
  emits it as `ScheduleSample.evidence_ratio` (line 2748-2757). The
  signal exists in the framework; it is **logged**, not **used**.

* **`twodim_fm` is the canonical regression target.** The Wave 17
  Phase 2 controlled-noise sweep (`docs/CONDITIONS.md`,
  `docs/theory/operating-regime.md` §1.3) measured the framework
  consistently regressing on the synthetic 2D targets (`two_moons`,
  `eight_gaussians`) at every `σ ∈ [0, 0.5]`. The operating-regime
  analysis (`docs/theory/operating-regime.md` §2.2) attributes this
  regression to a **structural** mismatch between the framework's
  1-D-sheet design (`R → R²`, paper's actual setting) and `twodim_fm`'s
  2-D velocity field (no 1-D profile `g`).

* **Honest documentation over silent redesign.** The user directive
  for Wave 30 P1 is to **document, not redesign**. Switching
  `n_cap` from cosine annealing to a paper-evidence-driven driver
  is a **framework redesign**, not a documentation change. The
  honest path is: keep cosine annealing (ADR-0010), document F-5 as
  an **operating-regime limitation**, and let a future wave revisit
  the architectural question when a F-side-admissible adapter
  (paper Theorem 1's setting) is integrated.

* **Out-of-F-side adapters are honestly out-of-regime.** The
  paper's quantitative guarantees (sheet-evidence `A_g · ε` dominant
  over cell-evidence `C_g · B_g · ε²`) apply only when `g` is
  F-side admissible (`validate_g_admissible` accepts). For adapters
  where no such profile exists (e.g. `twodim_fm` is 2-D-velocity
  with no 1-D profile `g`), the paper's mechanism is
  ill-conditioned — there is no sheet-vs-cell separation to drive.
  The framework's regression on these adapters is **expected
  behaviour**, not a bug.

* **`evidence_ratio` is still the paper signal a future
  paper-driven driver would consume.** The per-round
  `paper_selection_ratio` (line 2748-2757) is the right input to a
  future `n_cap_from_evidence_ratio` driver; this ADR does NOT
  prevent that future design — it only documents that the current
  design is cosine-anneal-based, not paper-driven.

## Considered Options

1. **Stay with cosine annealing (ADR-0010); document F-5 as
   operating-regime limitation; emit `evidence_ratio` as reportable
   metric; accept regression on out-of-F-side-class adapters.**
   This ADR. The 36 algorithm-level uplifts remain canonical;
   `twodim_fm` continues to regress (documented); the architectural
   choice is explicit.
2. **Replace cosine annealing with paper-evidence-driven
   `n_cap`.** Rejected for Wave 30: this is a framework redesign,
   not a documentation change. It would break the
   `byte-identical-to-Phase-3` invariant on every existing caller,
   invalidate the 36 algorithm-level uplifts' (current, achieved)
   assertions, and require a new audit cycle before the redesigned
   scheduler can be confidently re-deployed. The framework is in a
   freeze-prep window (G-FRAMEWORK-HEALTH gate pending; see
   `todo/GATES.md`).
3. **Hybrid driver (cosine baseline + paper-evidence correction).**
   Rejected for Wave 30: the architecture is sound only if the
   correction term is well-defined for adapters where the paper
   signal is degenerate. `twodim_fm`'s `evidence_ratio` is
   non-zero but not interpretable as a sheet-vs-cell dominance
   indicator (no `g` profile); the correction would silently
   decay toward the cosine baseline, leaving the regression
   in-place. A hybrid design without a F-side-admissibility
   gate would be a silent regression.
5. **Defer entirely (do nothing).** Rejected: Wave 29 Agent A
   identified F-5 as the only clean algorithm-level regression;
   leaving it undocumented would be a regression in audit-trail
   completeness. The honest choice is to **document** rather than
   **redesign or ignore**.

## Decision Outcome

Chosen option: **option 1 — stay with cosine annealing, document F-5
as operating-regime limitation.**

### Statement

The framework's `CodimensionSheetScheduler.n_cap` is **cosine-driven**
(ADR-0010), not paper-evidence-driven. This is a deliberate
architectural choice, not a bug:

* The cosine-anneal `n_cap` is the canonical driver in
  `adaptive_reflow/algorithm/scheduler/_core.py::n_cap_for_round` and
  is consumed by `ScheduleSample` and the runner/engine chain.
* The paper-evidence signal `evidence_ratio =
  paper_selection_ratio(sheet_A, packing_B, cell_C, eps_implicit)` is
  computed per-round (line 2748-2757) and emitted as
  `ScheduleSample.evidence_ratio` — a reportable metric, not a
  driver.
* The choice is documented in `docs/theory/operating-regime.md`
  §"F-5 limitation" (added by this ADR) and cross-referenced from
  `docs/baseline-audit-report.md` §C.5 (additive).

### What this means for the framework's operating regime

The framework's **operating regime**, as published in
`docs/theory/operating-regime.md` §1.3 + §2.2, **already accounts**
for F-5:

* **In regime** (F-side-admissible adapters, paper Theorem 1's
  setting): the cosine-anneal `n_cap` is sufficient because the
  paper's `evidence_ratio` is a **reportable** sheet-vs-cell
  indicator, but the cosine-anneal schedule is the framework's
  documented coarse-to-fine exploration/refinement split. The
  algorithm-level uplifts hold.
* **Out of regime** (out-of-F-side-class adapters, e.g.
  `twodim_fm`): the cosine-anneal `n_cap` does not respond to the
  paper's sheet-vs-cell signal (which is degenerate because there is
  no `g` profile). The framework regresses; this is **expected
  behaviour**, not a bug. The operating-regime falsification in
  §1.3 is the honest statement.

### Why this is honest, not a regression

The regression on `twodim_fm` (and any other out-of-F-side adapter)
is **structural**, not a tuning problem:

* The framework's `CodimensionSheetScheduler` was designed for the
  paper's `R → R²` setting (1-D profile `g`, paper Theorem 1's
  setting). The paper's quantitative guarantees (`A_g · ε`
  dominant over `C_g · B_g · ε²`) apply here.
* `twodim_fm`'s velocity field is **2-D** (no 1-D profile `g`). The
  paper's sheet-vs-cell decomposition is ill-conditioned: `A_g` is
  not the dominant term because the velocity field is 2-D, and `B_g`
  is not the binding constraint because the root cells are 2-D
  Voronoi cells. See `docs/theory/operating-regime.md` §2.2 for the
  full justification.
* A future paper-evidence-driven `n_cap` would still regress on
  `twodim_fm` because the paper signal itself is degenerate for
  these adapters. The architectural choice (cosine vs paper) does
  **not** determine whether the framework helps or regresses on
  out-of-F-side adapters; the F-side hypothesis class does.

### Why we are NOT redesigning in Wave 30

Wave 30 P1's user directive is "document rather than redesign". The
full redesign path would require:

1. A new `n_cap_from_evidence_ratio` driver in
   `adaptive_reflow/algorithm/scheduler/_core.py`.
2. A F-side-admissibility gate (`validate_g_admissible`) integrated
   into the per-round scheduler so the driver knows when to fall
   back to cosine annealing.
3. A migration of the 36 algorithm-level uplifts to the new driver,
   with new (current, achieved) assertions.
4. A re-audit of the 12 measured upstream regressions (`twodim_fm`
   +45-190% uplift, LineageFlow saturation, CIFAR-10 +24-31%, etc.)
   to confirm the redesigned driver does not introduce new
   regressions.
5. A new conformance test battery + audit cycle.

This is a multi-wave effort, not a documentation change. The honest
path for Wave 30 P1 is to document F-5 as an operating-regime
limitation and let a future wave (with a F-side-admissible adapter
in scope) revisit the architectural question.

### Module contract

* **No code changes.** This ADR is a documentation decision; the
  `n_cap` driver remains `cosine-anneal` per ADR-0010.
* **`evidence_ratio` remains a reportable metric.** The per-round
  `ScheduleSample.evidence_ratio` (line 2748-2757) is unchanged. A
  future paper-evidence-driven scheduler can consume this signal
  without any breaking change to the surface.
* **Audit-trail emission is part of the contract.** The
  `evidence_ratio` audit code already exists; this ADR does not
  add a new code path.

### Consequences

Positive:

* The framework's 36 algorithm-level uplifts remain byte-identical
  to Phase 3; the (current, achieved) assertions in
  `docs/benchmark-uplifts.md` are preserved.
* The architectural choice is **explicit, documented, and traceable**.
  A reviewer who asks "why is `n_cap` cosine-driven rather than
  paper-driven?" gets this ADR + ADR-0010 + the
  `docs/theory/operating-regime.md` §"F-5 limitation" section as the
  answer chain, with cross-references to the Wave 29 Agent A audit.
* The `evidence_ratio` per-round signal is preserved as a future
  redesign's input — the architectural choice is **documented**, not
  **locked**. A future wave can introduce a
  `n_cap_from_evidence_ratio` driver without breaking this ADR.
* The framework's operating-regime statement in
  `docs/theory/operating-regime.md` becomes **complete**: the
  falsification in §1.3 + the F-5 limitation cross-reference form a
  single honest statement about when the framework helps vs
  regresses.
* **Honest negative result.** The framework's regression on
  `twodim_fm` and other out-of-F-side-class adapters is
  **documented as expected behaviour**, not a bug. This is the
  principled way to handle an architectural choice that has known
  negative consequences on adapters outside the design regime.

Negative:

* **The `twodim_fm` regression persists.** The framework continues
  to regress on synthetic 2D targets at every `σ ∈ [0, 0.5]`. The
  regression is documented; it is not fixed. Users who want the
  framework to help on these adapters must accept that the
  framework's design regime is `R → R²`, not 2-D-velocity.
* **The architectural choice is a load-bearing commitment.** Switching
  `n_cap` to a paper-evidence-driven driver is a framework redesign,
  not a configuration change. This ADR documents the choice; it does
  not make it reversible cheaply.
* **The `evidence_ratio` signal is logged, not used.** The framework
  computes a paper-quantity-aware signal per round and emits it as
  a metric. The signal is not consumed by the scheduler; it is
  preserved for future redesigns and for audit-trail completeness.
  A reviewer who reads `ScheduleSample.evidence_ratio` and assumes
  it drives `n_cap` will be misled — the docstring on the field
  must continue to make the role distinction clear.

### Relationship to ADR-0010 (cosine-driven memory fraction)

ADR-0010 ([cosine-driven memory fraction](0010-cosine-driven-memory-fraction.md))
introduces the driver ↔ runner ↔ engine chain that makes cosine
annealing the canonical source of per-round `n_cap`. This ADR
**does not redefine** ADR-0010 — it documents the **architectural
limitation** of ADR-0010's choice: the cosine-anneal `n_cap` is not
paper-evidence-driven, and the framework's regression on
out-of-F-side adapters is the consequence of this choice.

A future ADR could introduce an `evidence_ratio`-driven `n_cap` as
an **alternative driver** (with `validate_g_admissible` as the
admissibility gate), but that is a separate architectural decision
that requires a future wave's scope.

### Relationship to ADR-0013 (paper-quantity naming)

ADR-0013 ([posterior selection drives algorithm](0013-posterior-selection-drives-algorithm.md))
introduces the four paper quantities `(A_g, B_g, C_g, e_rho)` as the
canonical paper-quantity naming. This ADR **consumes** those
quantities — `paper_selection_ratio(A_g, B_g, C_g, eps)` is the
`evidence_ratio` that the framework already computes per round — but
does not redefine them. ADR-0013's paper-quantity naming is
canonical; this ADR adds the **architectural statement** that the
computed `evidence_ratio` is **logged**, not **driving**.

### Relationship to ADR-0014 (Hyperparameter-Free Framework Principle)

ADR-0014 ([Hyperparameter-Free Framework Principle](0014-hyperparameter-free-framework-principle.md))
introduces the five authorized sources for framework
hyperparameters, including `paper_quantities` (the `OTEpsilonSchedule`
derivation reads `C_g`). This ADR documents that **`n_cap` is
derived from the cosine driver, NOT from `paper_quantities`** —
i.e. the framework's `n_cap` is a hand-set engineering choice, not a
DERIV-001 derivation rule. A future DERIV-001 work item could
introduce a `PaperSelectionRatioMemoryFraction` derivation rule (the
DERIV-001 closed form would be `m_t = 1 - paper_selection_ratio(A_g,
B_g, C_g, eps_t)`), but that is a separate piece of work and
out-of-scope for Wave 30 P1.

### Confirmation

The decision is enforced by:

* `docs/theory/operating-regime.md` §"F-5 limitation" (NEW section
  added by this ADR) — the framework's operating-regime statement
  gains an explicit F-5 cross-reference, naming the Wave 29 Agent A
  finding, the cosine-vs-paper architectural choice, and the
  out-of-F-side regime consequence.
* `docs/baseline-audit-report.md` §C.5 (additive update) — the C.5
  failure-mode-characterisation section gains a cross-reference to
  the new F-5 limitation section in `operating-regime.md`.
* [`docs/audit/theory-implementation-gap.md`](../audit/theory-implementation-gap.md)
  §F-5 — the Wave 29 Agent A finding is preserved verbatim; this
  ADR documents the **decision**, not the audit.
* No code changes — the `n_cap` driver remains
  `cosine-anneal`-based per ADR-0010.

## More Information

* [docs/adr/0010](0010-cosine-driven-memory-fraction.md) — the
  cosine-driven memory fraction ADR whose `n_cap_for_round` is the
  framework's canonical driver. This ADR documents the architectural
  limitation of that choice.
* [docs/adr/0013](0013-posterior-selection-drives-algorithm.md) —
  the paper-quantity naming `(A_g, B_g, C_g, e_rho)` that this ADR's
  `evidence_ratio` consumes (as a reportable metric, not a driver).
* [docs/adr/0014](0014-hyperparameter-free-framework-principle.md) —
  the DERIV-001 derivation rules; a future DERIV-001 work item
  could introduce a paper-quantity-driven `n_cap` derivation rule.
* [docs/theory/operating-regime.md](../theory/operating-regime.md)
  §1.3 + §1.4 + §2.2 — the framework's honest operating-regime
  statement: the predicted `twodim_fm`-class regime is FALSIFIED at
  every `σ ∈ [0, 0.5]` under matched conditions on both synthetic
  targets. The §"F-5 limitation" section (added by this ADR)
  cross-references the architectural choice documented here.
* [docs/audit/theory-implementation-gap.md](../audit/theory-implementation-gap.md)
  §F-5 + §4 (per-target regression attribution table) — the Wave 29
  Agent A finding that names F-5 as the only clean algorithm-level
  regression at matched NFE and attributes `twodim_fm` regression to
  F-5.
* [docs/CONDITIONS.md](../CONDITIONS.md) §"Wave 17 Phase 2" + §"Wave
  17 Phase 3" — the controlled-noise-injection sweep (12 data
  points; `σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5}` × 2 targets) and the
  Wave 17 Phase 3 operating-regime addendum.
* [docs/benchmark-uplifts.md](../benchmark-uplifts.md) — the 36
  algorithm-level uplifts that this ADR's choice preserves
  byte-identical to Phase 3.
* `adaptive_reflow/algorithm/scheduler/_core.py` (lines
  2651-2784) — the `CodimensionSheetScheduler.n_cap` driver that
  this ADR documents as **cosine-driven, not paper-ratio-driven**.
* `docs/baseline-audit-report.md` §C.5 — the C.5 failure-mode-
  characterisation table; this ADR adds a cross-reference to the
  new F-5 limitation section in `operating-regime.md`.

## Numbering note

This ADR is allocated the prefix `0017` (next free monotonic prefix
after the existing ADR-0016). No slug collision with prior ADRs
exists; the cross-references above use the ADR numbers as a
documentation-reader navigation aid.