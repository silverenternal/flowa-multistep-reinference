---
status: superseded
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 8. Regime-aware eps selector (opt-in Lemma 4 enforcement) — slug-collision pointer

> **Pointer file.** The canonical content for this decision lives at
> **[ADR-0016](0016-regime-aware-eps-selector.md)**. This file exists
> at the slug slot `0008` only because the Workflow K task brief
> referenced this decision as "ADR-0008"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation
> `0016` because the slot `0008` was already taken by
> [ADR-0008](0008-claim-gate-deferral-placeholder.md)
> ("Claim-gate deferral placeholder"). Two ADRs sharing the numeric
> prefix `0008` would violate the convention pinned by
> [ADR-0001](0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" — i.e.
> unique per ADR). Do not write new content here; update the canonical
> [ADR-0016](0016-regime-aware-eps-selector.md) instead and add a
> cross-reference back from there.

## Context and Problem Statement

The framework's algorithm layer (ADR-0011) routes the per-round
`eps_implicit` through one of three paths: `CosineAnnealScheduler`
(per-round cosine-decay production), `CodimensionSheetScheduler`
(paper-quantity-aware cosine; ADR-0013), and
`ConvergenceAdaptiveScheduler` / `EvidenceDrivenScheduler` (a
PID-lite controller on `evidence_ratio` that emits an `eps_implicit`
delta). All three paths share the same paper-quantity contract
`(A_g, B_g, C_g, e_rho)` (ADR-0013) — but **none** of them enforce
the Lemma 4 regime `eps^2 < e_rho / log(2)` that the paper requires
for the exterior exponential bound
`∫_{T^c \ ⋃_z I_z} p_ε ≤ e^{-e_ρ/(2ε²)} = o(ε)` to apply.

The regime check exists in two places today, both **diagnostic**:

1. `adaptive_reflow.eval.fid_theorem_aligned._regime_check` and
   `TheoremAlignedFIDResult.regime_check_ok` (per-round) and
   `ConvergenceDiagnostic.regime_violations` (trajectory-wide) —
   the FID side (ADR-0015).
2. `adaptive_reflow.algorithm.evidence_driver.EvidenceDrivenScheduler.regime_violation_warnings`
   (an *appended* warning list, never gating).

Neither path *prevents* the violation; both paths record it. A
scheduler with a large `eps_implicit_base` and a strong PID step
(`max_step = 0.1`) can leave the regime on round 0, and the
resulting per-round FID trajectory is no longer grounded in Theorem
1's quantitative `O(eps)` rate (paper Proposition 3, ADR-0015). A
caller that wants fail-closed semantics has no opt-in path: today
the only way to enforce the regime is to hand-tune
`eps_implicit_base` and `max_step` until the trajectory happens to
stay inside the regime, which is exactly the hand-set pattern that
ADR-0014 (DERIV-001) rejects.

The decision answers five questions:

1. **What** is the canonical selector surface?
2. **How** is the Lemma 4 regime enforced?
3. **When** does enforcement activate (opt-in flag)?
4. **What** is the failure-closed semantics when `e_rho` is degenerate?
5. **What** is the back-compat invariant that protects existing
   `CosineAnnealScheduler` callers?

The Workflow K task brief on 2026-09-01 asked for this ADR under
the slug slot `0008`. The audit identified a slug collision with the
existing [ADR-0008](0008-claim-gate-deferral-placeholder.md) and
recommended the safer monotonic-prefix allocation `0016`. The
canonical content was written at
[ADR-0016](0016-regime-aware-eps-selector.md) with an explicit
`## Numbering note` at the bottom, pointing back to this pointer
file.

This file is the explicit pointer for the `0008` slot so a reviewer
who follows the brief's "ADR-0008" label lands on a file that
explains the situation rather than a 404 or a silent duplicate of
the canonical content.

## Decision Drivers

* **Fail-closed is the load-bearing semantics.** A violation that
  silently flows into the per-round FID trajectory is worse than a
  hard error: the framework *appears* to be working (the FID values
  are finite, the metrics are emitted), but the values are no longer
  grounded in the paper. A caller that opts into the regime check
  gets a *hard* answer: the selector either returns a value inside
  the regime or emits the floor and a `regime_infeasible` audit
  code. There is no silent bypass.
* **Opt-in is non-negotiable.** The 2356+15 test surface runs the
  default `CosineAnnealScheduler` with hand-set `eps_implicit`. The
  regime selector must default to **off**, and the scheduler's
  byte-identical `eps_implicit` trajectory must be preserved when
  the opt-in flag is `False`. Existing callers cannot have their
  audit trail rewritten.
* **The selector wraps an existing trajectory; it does not replace
  it.** The Lemma 4 bound is an *upper-bound* on `eps`, not a
  schedule in its own right. A new schedule family should be able to
  opt into the regime check by supplying its proposal; the regime
  ceiling is orthogonal to the schedule family.
* **The selector must be stdlib-only.** It lives in
  `adaptive_reflow.algorithm.scheduler.regime_selector`, the
  contracts-adjacent algorithm layer. No `torch`, no `numpy`, no I/O,
  no global state beyond per-instance controller memory.
* **The Lemma 4 regime check is duplicated, not imported.** The
  algorithm layer must not depend on the eval layer; the regime
  predicate is re-derived from `math` primitives and pinned
  bit-for-bit equal to the eval-layer version by a regression test.
* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique. Two ADRs sharing the prefix
  `0008` would silently break the doc scanner's numeric-prefix
  indexing.

## Considered Options

1. **Pointer file at the brief's slug slot, forwarding every
   cross-reference to the canonical allocation** (this file). The
   canonical content lives at
   [ADR-0016](0016-regime-aware-eps-selector.md).
2. **Write the full ADR text at `0008-` while the canonical text
   also lives at `0016-`.** Rejected: two source-of-truth files
   drift on every correction, and the doc scanner cannot
   distinguish which is the authoritative surface.
3. **Allocate the ADR at a free monotonic prefix (`0016`) and
   silently drop the brief's `0008` slot.** Rejected: a reviewer
   who follows the brief's "ADR-0008" label lands on a 404; the
   pointer file is the explicit fix.
4. **Allocate the ADR at the brief's `0008` slot and renumber the
   existing `0008-claim-gate-deferral-placeholder.md` ADR.**
   Rejected: breaks the doc scanner's references to ADR-0008
   throughout the codebase. The audit recommended the cheaper
   fix: leave the existing 0008 in place and forward `0008` to
   `0016`.

## Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* This file's `status: superseded` (not `accepted`) makes the
  pointer relationship machine-readable.
* The canonical text — `RegimeAwareEpsSelector` Protocol +
  `regime_ceiling(eps_r, e_rho, *, slack)` ceiling +
  `regime_holds(eps, e_rho)` predicate + the opt-in flag on
  `EvidenceDrivenScheduler(..., regime_aware=False)`, with two
  concrete selectors (`CosineAnnealRegimeSelector`,
  `ConvergenceAdaptiveRegimeSelector`) wrapping the existing
  scheduler trajectories — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0016](0016-regime-aware-eps-selector.md).
* The Lemma 4 ceiling
  `regime_ceiling(e_rho, *, slack) -> sqrt(e_rho / log 2) - slack`
  (with `slack = 1e-9` as the strict-inequality slack), the
  `EPS_REGIME_CLAMPED` / `EPS_REGIME_INFEASIBLE` / `EPS_REGIME_OK`
  audit codes, the `e_rho_provider` callback, and the
  `regime_selector_family` / `regime_slack` knobs live in
  [`adaptive_reflow/algorithm/scheduler/regime_selector.py`](../adaptive_reflow/algorithm/scheduler/regime_selector.py).

## Consequences

Positive:

* A reviewer who follows the brief's "ADR-0008" label arrives at a
  file that immediately explains the slug collision and points to
  the canonical content. No 404, no silent duplicate.
* The convention pinned by ADR-0001 is preserved — no two ADRs
  share the numeric prefix `0008`.
* The audit's recommendation ("Recommend no further ADR authoring
  in this workflow; the gaps to close are at the implementation
  layer, not the documentation layer") is honoured: the canonical
  ADR-0016 is the only authoritative source of truth.
* The pointer file documents the five-question decision (selector
  surface / regime enforcement / opt-in flag / fail-closed
  semantics / back-compat invariant) and the canonical artefacts
  that close them, so a reviewer skimming only the pointer still
  gets the architectural gist.

Negative:

* This file is a fourth-level navigation hop. A reviewer who only
  reads this pointer file without following the link to ADR-0016
  will see no Lemma 4 ceiling derivation, no audit-code table, no
  `e_rho_provider` callback signature, and no end-to-end trajectory
  test. The pointer is explicit about that, but the cost is real
  for any reviewer who skims.
* The cross-reference chain now spans four files for what was
  originally one brief slot (brief → pointer → canonical ADR →
  cross-referenced docs). This is the documented trade-off for
  preserving the ADR-0001 numeric-prefix convention.
* The pointer file cannot carry `status: accepted` because the
  slug-collision slot cannot be the authoritative home; a reader
  who grep-searches `status: accepted` for `ADR-0008` will not
  find this pointer.

## Confirmation

The decision is enforced by:

* The existence of
  [ADR-0016](0016-regime-aware-eps-selector.md) with the full
  canonical content (Status: accepted, date 2026-09-01) and an
  explicit `## Numbering note` section pointing back to this
  pointer file.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  (Regime-aware eps selector bullet) cross-references
  **ADR-0016** (not `ADR-0008`) as the canonical home, so the
  authoritative surface is single-sourced.
* The `docs/ARCHITECTURE.md` §10 FAQ row for "How does the
  framework prevent the scheduler's `eps` from leaving the Lemma
  4 regime?" names **ADR-0016** as the entry point.
* `tools/check_docs_against_code.py` does not flag a duplicate
  prefix because the new file's `status: superseded` frontmatter
  marks it as a non-authoritative pointer; the canonical prefix
  indexing reads `status: accepted` ADRs only.

## More Information

* [ADR-0016](0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR. This is where the four selectors
  (`RegimeAwareEpsSelector` Protocol, `_BaseRegimeSelector`
  template-method base, `CosineAnnealRegimeSelector`,
  `ConvergenceAdaptiveRegimeSelector`), the Lemma 4 ceiling
  `regime_ceiling(e_rho, *, slack)`, the `regime_holds` predicate,
  the audit-code table (`EPS_REGIME_CLAMPED`,
  `EPS_REGIME_INFEASIBLE`, `EPS_REGIME_OK`,
  `REGIME_VIOLATION_WARNING`), the opt-in flag on
  `EvidenceDrivenScheduler`, and the bit-for-bit regime-predicate
  equality with the eval layer live.
* [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID ADR (brief slot `0007`); its
  `ConvergenceDiagnostic.regime_violations` is the FID-side
  Lemma 4 *diagnosis* that this ADR's selector is the
  scheduler-side *enforcement* for.
* [ADR-0014](0014-hyperparameter-free-framework-principle.md) —
  the Hyperparameter-Free Framework Principle (DERIV-001; brief
  slot `0006`); its `BLConvergenceEpsilonSchedule` derivation
  rule reads `paper_quantities.e_rho` and outputs `eps_threshold`
  — the *theoretical* companion to this ADR's regime enforcement.
* [ADR-0013](0013-posterior-selection-drives-algorithm.md) —
  the paper-quantity naming `(A_g, B_g, C_g, e_rho)` and the
  theorem-driven scheduler justification that this ADR's
  `e_rho_provider` callback consumes as a ceiling input.
* [ADR-0008](0008-claim-gate-deferral-placeholder.md) — the
  pre-existing ADR that owns the `0008` slug slot; the slug
  collision that motivated this pointer file.
* [ADR-0001](0001-record-architecture-decisions.md) — the
  numeric-prefix convention this pointer file exists to
  preserve.
* [`docs/lean/THEOREM_1_MAPPING.md`](../lean/THEOREM_1_MAPPING.md)
  §B.3 (Exterior exponential bound, paper Lemma 4, line 110-113) —
  the formal verification of Lemma 4 and the `e_rho` quantity
  this ADR's regime selector consumes.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5 — the FID-JMAA workflow + Phase 4 verdict (TheoremAlignedFID
  surface, per-round harness wiring, regime enforcement
  diagnostic-only status).
* [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 row 157 — the Phase-4 scheduler `e_rho` regime enforcement
  status (`diagnostic-only`, updated by ADR-0016 to reflect the
  opt-in path).
* `NoiseSelectedRectification_EN.md` Lemma 4 (line 110-113) — the
  paper's exterior exponential bound
  `∫_{T^c \ ⋃_z I_z} p_ε ≤ e^{-e_ρ/(2ε²)} = o(ε)` whose
  `o(ε)` step is the regime `eps^2 < e_rho / log 2` this ADR
  enforces.
* `adaptive_reflow/algorithm/scheduler/regime_selector.py` — the
  canonical RegimeAwareEpsSelector Protocol, the
  `_BaseRegimeSelector` template-method base, the two concrete
  selectors, the audit-code constants, the `regime_ceiling` /
  `regime_holds` helpers.
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py::EvidenceDrivenScheduler`
  — the opt-in point via `regime_aware=False` (default) /
  `regime_aware=True`, the `regime_selector` /
  `regime_selector_family` / `e_rho_provider` / `regime_slack`
  parameters, and the per-round `regime_violation_warnings`
  list.
* `tests/test_algorithm/test_regime_selector.py`,
  `tests/test_algorithm/test_regime_aware_evidence_driven.py` —
  the protocol, closed-form, fallback, dispatcher, and end-to-end
  trajectory regression tests
  (including `test_regime_predicate_matches_fid_module`).
* Audit Phase 1 (2026-09-01) input to Workflow K — the
  recommendation that this pointer file implements.