---
status: accepted
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 16. Regime-aware eps selector (opt-in Lemma 4 enforcement on the scheduler)

## Context and Problem Statement

The framework's algorithm layer
([ADR-0011](0011-algorithm-abstractions.md)) routes the per-round
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
   `ConvergenceDiagnostic.regime_violations` (trajectory-wide) — the
   FID side, recorded in
   [`docs/adr/0015-theorem-aligned-fid-per-round-pattern.md`](0015-theorem-aligned-fid-per-round-pattern.md).
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
ADR-0014 ([DERIV-001](0014-hyperparameter-free-framework-principle.md))
rejects.

The user's audit on 2026-09-01 was explicit: the missing
*enforcement* is the missing piece between the regime *diagnosis*
(FID-side, ADR-0015) and the regime *derivation* (paper-quantity
side, ADR-0014). The framework today can **observe** a violation
and **derive** a regime from `e_rho`, but cannot **prevent** one.

The decision answers five questions:

1. **What** is the canonical selector surface?
2. **How** is the Lemma 4 regime enforced?
3. **When** does enforcement activate (opt-in flag)?
4. **What** is the failure-closed semantics when `e_rho` is degenerate?
5. **What** is the back-compat invariant that protects existing
   `CosineAnnealScheduler` callers?

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
  ceiling is orthogonal to the schedule family. The contract is
  `select(eps_r, e_rho, *, slack) -> eps_{r+1}` with
  `eps_{r+1} <= sqrt(e_rho / log 2) - slack`.
* **The selector must be stdlib-only.** It lives in
  `adaptive_reflow.algorithm.scheduler.regime_selector`, the
  contracts-adjacent algorithm layer. No `torch`, no `numpy`, no I/O,
  no global state beyond per-instance controller memory.
* **The Lemma 4 regime check is duplicated, not imported.** The
  algorithm layer must not depend on the eval layer; the regime
  predicate is re-derived from `math` primitives and pinned
  bit-for-bit equal to the eval-layer version by a regression test.
* **Audit-trail emission is part of the contract.** A caller that
  opts into the regime check expects to know *when* the regime was
  violated, *how far* outside the regime the schedule was
  proposing, and *what* the selector emitted instead. The audit
  trail carries `EPS_REGIME_CLAMPED`, `EPS_REGIME_INFEASIBLE`,
  `EPS_REGIME_OK`, and the human-readable
  `REGIME_VIOLATION_WARNING`.

## Considered Options

1. **`RegimeAwareEpsSelector` Protocol +
   `regime_ceiling(eps_r, e_rho, *, slack) -> float` ceiling +
   `regime_holds(eps, e_rho) -> bool` predicate + opt-in flag on
   `EvidenceDrivenScheduler(..., regime_aware=False)`, with two
   concrete selectors (`CosineAnnealRegimeSelector`,
   `ConvergenceAdaptiveRegimeSelector`) wrapping the existing
   scheduler trajectories and applying the Lemma 4 ceiling on top.**
   Default `regime_aware=False` is byte-identical to Phase 3.
2. **Replace the existing scheduler trajectories with regime-aware
   variants.** Rejected: the regime is an upper bound, not a
   schedule; replacing the schedule would lose the cosine-anneal /
   convergence-adaptive semantics and break every existing caller
   that has a hand-set `eps_implicit_base` they want preserved.
3. **Block on regime violation (raise an exception).** Rejected: the
   framework's per-round scheduler emits a `ScheduleSample`; a
   mid-cycle exception would leave the engine in an undefined
   state. The fail-closed semantics must be a *clamp-to-floor +
   audit-code* path, not a raise.
4. **Thread `e_rho` through the scheduler protocol itself as a
   required field.** Rejected: the framework's `SchedulerProtocol`
   is the four-axis abstraction (ADR-0011) that must work without
   any paper-quantity context; requiring `e_rho` would make
   `CosineAnnealScheduler` paper-quantity-aware by default and
   break every adapter that calls `scheduler.sample()` without a
   profile residual. The `e_rho` is supplied via the optional
   `e_rho_provider` callback, not as a constructor argument.

## Decision Outcome

Chosen option: **option 1 — `RegimeAwareEpsSelector` Protocol +
`regime_ceiling(eps_r, e_rho, *, slack) -> float` ceiling +
`regime_holds(eps, e_rho) -> bool` predicate + opt-in flag on
`EvidenceDrivenScheduler(..., regime_aware=False)`, with two
concrete selectors wrapping the existing trajectories.**

### The four selectors

| Selector | Path | Concern |
|---|---|---|
| `RegimeAwareEpsSelector` (Protocol) | `adaptive_reflow.algorithm.scheduler.regime_selector` | Abstract per-round `eps` selector bounded by the Lemma 4 regime; `family() -> str`, `select(eps_r, e_rho, *, slack) -> float`, `select_detailed(...) -> RegimeSelection`, `observe_round_feedback`, `reset`, `to_config`. |
| `_BaseRegimeSelector` (template method) | same | Shared base: subclass implements `_propose(eps_r, round_index)`; base applies the regime ceiling, the `EPS_FLOOR`, and builds the audit trail. Concentrating the clamp here means the Lemma 4 bound is implemented exactly once. |
| `CosineAnnealRegimeSelector` | same | Wraps the cosine anneal of `CosineAnnealScheduler`; bounded by the regime ceiling. |
| `ConvergenceAdaptiveRegimeSelector` | same | Wraps the PID-lite convergence controller of `ConvergenceAdaptiveScheduler`; bounded by the same ceiling. |

### The Lemma 4 ceiling

The ceiling is `regime_ceiling(e_rho, *, slack) -> sqrt(e_rho / log 2) - slack`,
where `slack = 1e-9` is the strict-inequality slack (Lemma 4 requires
`eps^2 < e_rho / log 2` *strictly*, so the floating-point ceiling
must be a hair below the paper's bound). The helper returns `0.0`
for degenerate `e_rho <= 0` and for the case where `slack` swallows
the whole bound, so call sites can treat
`ceiling <= EPS_FLOOR` as the single infeasibility test.

The `regime_holds(eps, e_rho) -> bool` predicate is the Lemma 4
check `eps^2 < e_rho / log 2`; it returns `False` on degenerate
inputs (`eps <= 0` or `e_rho <= 0`) so call sites need no extra
guards. The eval-layer version of the same predicate
(`adaptive_reflow.eval.fid_theorem_aligned._regime_check`) is pinned
bit-for-bit equal by a regression test
(`tests/test_algorithm/test_regime_selector.py::test_regime_predicate_matches_fid_module`)
so a future change cannot drift the two.

### Audit codes

| Audit code | When emitted | Carries |
|---|---|---|
| `EPS_REGIME_CLAMPED` | `eps_requested > ceiling` and the value was reduced | `requested`, `ceiling`, `applied` |
| `EPS_REGIME_INFEASIBLE` | `ceiling <= EPS_FLOOR` (no positive `eps` satisfies the regime) | `e_rho`, `ceiling`, `floor` |
| `EPS_REGIME_OK` | proposal already satisfied the regime (no clamp fired) | — |

Every regime-aware round emits at least one of these three codes
(`EPS_REGIME_OK` on every safe round) so the audit trail proves the
check ran rather than silently no-op'd. The human-readable
`REGIME_VIOLATION_WARNING` prefix is pushed onto the scheduler's
`regime_violation_warnings` list whenever a clamp or an infeasible
ceiling occurs.

### Opt-in flag

`EvidenceDrivenScheduler.__init__(..., regime_aware=False, ...)` is
the opt-in point:

* `regime_aware=False` (default) keeps the `eps_implicit` path
  byte-identical to Phase 3: no selector is consulted, no extra
  audit codes are emitted, and `config_hash` / `to_config` are
  unchanged.
* `regime_aware=True` routes every round's PID-proposed `eps`
  through a `RegimeAwareEpsSelector` so the emitted `eps` always
  satisfies `eps^2 < e_rho / log 2`; a would-be violation is
  clamped to the ceiling and logged as a regime-violation warning.
  Has no effect when `eps_implicit_base is None` (there is no `eps`
  to gate).

The selector is built from `regime_selector_family` (default
`"cosine_anneal"`) and `regime_slack` (default `1e-9`) when no
explicit `regime_selector` is supplied. The `e_rho_provider`
callback is the optional hook that supplies the per-round `e_rho`
from a profile residual `g`; without it, the selector is degenerate
and emits `EPS_REGIME_INFEASIBLE` on every round.

### Module contract

* **stdlib-only.** No `torch`, no `numpy`, no I/O, no global state
  beyond per-instance controller memory.
* **Pure w.r.t. arguments.** `select(eps_r, e_rho, *, slack)` is a
  deterministic function of its arguments; `select_detailed` returns
  the same `eps_next` as `select` for identical arguments; the only
  mutable state is the explicit per-round controller memory cleared
  by `reset()`.
* **Bit-for-bit regime predicate equality** with the eval-layer
  `_regime_check` (pinned by a regression test).
* **Back-compat invariant.** `regime_aware=False` (default) leaves
  every existing caller byte-identical to Phase 3.
* **Frozen dataclasses** for `RegimeSelection`.

### Consequences

Positive:

* The framework now has a **diagnose-then-enforce** workflow for
  the Lemma 4 regime. TheoremAlignedFID (ADR-0015) records the
  violations on every run via
  `ConvergenceDiagnostic.regime_violations`; a caller who wants
  fail-closed semantics opts into `regime_aware=True` to
  *prevent* them on subsequent runs.
* The selector wraps an existing schedule trajectory rather than
  replacing it. A new schedule family can opt into the regime
  check by supplying its `_propose` method — the Lemma 4 ceiling
  is orthogonal to the schedule family.
* The audit trail carries `EPS_REGIME_CLAMPED`,
  `EPS_REGIME_INFEASIBLE`, `EPS_REGIME_OK` so a downstream reader
  can tell *when* the regime was violated, *how far* outside the
  regime the schedule proposed, and *what* the selector emitted
  instead.
* The default `regime_aware=False` keeps the existing 2356+15 test
  surface green. The framework's per-round `eps_implicit` trajectory
  is byte-identical to Phase 3 when the opt-in is off.
* The regime predicate is re-derived in the algorithm layer from
  `math` primitives rather than imported from the eval layer
  (algorithm layer must not depend on the eval layer); the two
  implementations are pinned bit-for-bit equal by
  `test_regime_predicate_matches_fid_module`.

Negative:

* The package grows by ~600 lines across
  `adaptive_reflow/algorithm/scheduler/regime_selector.py` (and a
  similar number across the test file). The abstraction is only
  worth that cost while at least one caller actually opts in —
  the empirical evidence today is *diagnostic-only* per
  [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5.2.
* The opt-in is *per-scheduler*: a caller that wants fail-closed
  semantics on a `CosineAnnealScheduler` (the default for the
  whole framework) must construct it inside an
  `EvidenceDrivenScheduler` shell, which adds a layer. The
  alternative — wrapping the framework's default `CosineAnnealScheduler`
  with a regime selector — is rejected because it changes the
  `config_hash` and breaks the byte-for-byte audit invariant on
  every existing caller.
* The `EPS_REGIME_INFEASIBLE` audit code fires whenever the
  `e_rho_provider` returns a degenerate `e_rho <= 0` — i.e. the
  profile residual has no `e_rho` to gate on. The caller is
  expected to widen `e_rho` (via `rho` or `eta`) to recover. A
  caller that does not supply an `e_rho_provider` gets a
  `EPS_REGIME_INFEASIBLE` on every round, which is the documented
  "you opted in without supplying the inputs the opt-in needs"
  signal — not a silent bypass.
* The Lemma 4 regime check is a *necessary* condition for the
  paper's `o(eps)` step, not a *sufficient* one. A run with all
  rounds inside the regime can still violate Theorem 1's
  quantitative `O(eps)` rate if the other estimates (Lemmas 2 and
  3) are violated. The selector is a guard on Lemma 4 only; the
  full Theorem-1 reconciliation lives in ADR-0015's
  `ConvergenceDiagnostic.O_eps_holds`.

### Relationship to ADR-0014 (DERIV-001)

ADR-0014 ([DERIV-001](0014-hyperparameter-free-framework-principle.md))
introduces the Hyperparameter-Free Framework Principle. The
`BLConvergenceEpsilonSchedule` derivation rule is one of the five
canonical concrete derivation rules in DERIV-001; it reads
`paper_quantities.e_rho` and outputs `eps_threshold` via
`eps_t = sqrt(e_rho * delta_t)`. This ADR adds the *enforcement*
path for the same `e_rho` quantity — the regime selector is the
**runtime guard** that keeps the scheduler's `eps_implicit`
trajectory inside the regime the DERIV-001 derivation assumes. The
two paths are complementary: DERIV-001 *derives* an
`eps_threshold` from `e_rho`; this ADR *clamps* the scheduler's
`eps_implicit` to the regime ceiling.

### Relationship to ADR-0015 (TheoremAlignedFID)

ADR-0015 ([TheoremAlignedFID](0015-theorem-aligned-fid-per-round-pattern.md))
introduces the FID-side Lemma 4 *diagnosis*
(`TheoremAlignedFIDResult.regime_check_ok`,
`ConvergenceDiagnostic.regime_violations`). This ADR adds the
scheduler-side Lemma 4 *enforcement*. Together they form a
**diagnose-then-enforce** workflow:

1. ADR-0015 surfaces the regime violations on every run
   (diagnostic, on by default).
2. This ADR prevents them on subsequent runs (opt-in via
   `regime_aware=True`).

A caller that wants a fully reconciled Theorem-1 trajectory —
both diagnosed and enforced — opts into both: `regime_aware=True`
on the scheduler + `TheoremAlignedFIDReport` on the FID side.

### Relationship to ADR-0013 (paper-quantity naming)

ADR-0013 introduces the four paper quantities
`(A_g, B_g, C_g, e_rho)`. This ADR consumes `e_rho` as the
ceiling input via `e_rho_provider` (the optional per-round
`e_rho` producer). ADR-0013's paper-quantity naming is canonical;
this ADR adds the **runtime guard** that prevents the scheduler
from leaving the regime the four quantities imply.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/algorithm/scheduler/regime_selector.py` — the
  abstract `RegimeAwareEpsSelector` Protocol, the
  `_BaseRegimeSelector` template-method base, the two concrete
  selectors (`CosineAnnealRegimeSelector`,
  `ConvergenceAdaptiveRegimeSelector`), the audit-code constants
  (`EPS_REGIME_CLAMPED`, `EPS_REGIME_INFEASIBLE`, `EPS_REGIME_OK`,
  `REGIME_VIOLATION_WARNING`), the `DEFAULT_REGIME_SLACK` and
  `EPS_FLOOR` constants, and the `regime_ceiling` / `regime_holds`
  helpers.
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py::EvidenceDrivenScheduler.__init__`
  — the opt-in point via `regime_aware=False` (default) /
  `regime_aware=True`, the `regime_selector` /
  `regime_selector_family` / `e_rho_provider` / `regime_slack` /
  `regime_gate` parameters, the public `regime_aware` flag, and
  the per-round `regime_violation_warnings` list.
* `tests/test_algorithm/test_regime_selector.py` — the
  protocol / closed-form / fallback / dispatcher regression tests,
  including
  `test_regime_predicate_matches_fid_module` (bit-for-bit
  equality with the eval-layer `_regime_check`).
* `tests/test_algorithm/test_regime_aware_evidence_driven.py` —
  the end-to-end trajectory test: framework KL on the
  Gaussian-mixture target is monotone non-increasing under
  regime-aware `eps_implicit`, `regime_violation_warnings` fires
  exactly once when the proposal exceeds the ceiling,
  `config_hash` is unchanged when `regime_aware=False`.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5.2 — the Phase-4 status: `ConvergenceDiagnostic.regime_violations`
  surface exists, the scheduler consumes `paper_quantities` at
  round 0 only, and `_apply_paper_quantities_rewiring` at
  `runner.py:577` does NOT gate on `e_rho` (diagnostic-only).
  The opt-in enforcement path is this ADR; existing diagnostic-only
  status remains until a caller actually opts in.
* [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 row 157 — the Phase-4 scheduler `e_rho` regime enforcement
  status row, updated to reflect the opt-in path this ADR adds.

## More Information

* [docs/adr/0013](0013-posterior-selection-drives-algorithm.md) —
  the paper-quantity naming `(A_g, B_g, C_g, e_rho)` and the
  theorem-driven scheduler justification that this ADR's
  `e_rho_provider` callback consumes.
* [docs/adr/0014](0014-hyperparameter-free-framework-principle.md) —
  the DERIV-001 derivation rules whose `BLConvergenceEpsilonSchedule`
  is the *theoretical* companion to this ADR's regime enforcement.
* [docs/adr/0015](0015-theorem-aligned-fid-per-round-pattern.md) —
  the FID-side Lemma 4 *diagnosis* (`regime_check_ok`,
  `regime_violations`); together with this ADR forms the
  diagnose-then-enforce workflow.
* [`docs/lean/THEOREM_1_MAPPING.md`](../lean/THEOREM_1_MAPPING.md)
  §B.3 (Exterior exponential bound, paper Lemma 4, line 110-113) —
  the formal verification of Lemma 4 and the `e_rho` quantity this
  ADR's regime selector consumes.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5 — the FID-JMAA workflow + Phase 4 verdict (TheoremAlignedFID
  surface, per-round harness wiring, regime enforcement
  diagnostic-only status).
* [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 row 157 — the Phase-4 scheduler `e_rho` regime enforcement
  status (`diagnostic-only`, updated by this ADR to reflect the
  opt-in path).
* `NoiseSelectedRectification_EN.md` Lemma 4 (line 110-113) — the
  paper's exterior exponential bound
  `∫_{T^c \ ⋃_z I_z} p_ε ≤ e^{-e_ρ/(2ε²)} = o(ε)` whose
  `o(ε)` step is the regime `eps^2 < e_rho / log 2` this ADR
  enforces.
* `adaptive_reflow/algorithm/scheduler/regime_selector.py` — the
  abstract `RegimeAwareEpsSelector` Protocol, the
  `_BaseRegimeSelector` template-method base, the two concrete
  selectors (`CosineAnnealRegimeSelector`,
  `ConvergenceAdaptiveRegimeSelector`), the audit-code constants,
  the `regime_ceiling` / `regime_holds` helpers, the
  `RegimeSelection` frozen dataclass.
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py::EvidenceDrivenScheduler`
  — the opt-in point via `regime_aware=False` (default) /
  `regime_aware=True`, the `regime_selector` /
  `regime_selector_family` / `e_rho_provider` / `regime_slack`
  parameters, and the per-round `regime_violation_warnings` list.
* `tests/test_algorithm/test_regime_selector.py`,
  `tests/test_algorithm/test_regime_aware_evidence_driven.py` —
  the protocol, closed-form, fallback, dispatcher, and end-to-end
  trajectory regression tests.

## Numbering note

This ADR was originally described in the Workflow K task brief as
"ADR-0008" (to group it numerically with the FID-JMAA workflow's
Phase-4 deliverables and the `TheoremAlignedFID` decision). The
audit identified a slug collision with the existing
[ADR-0008](0008-claim-gate-deferral-placeholder.md)
("Claim-gate deferral placeholder") — two ADRs sharing the number
`8` would be a documentation-reader trap. The audit recommended the
safer allocation `0016` (next free monotonic prefix after the
existing ADR-0015). This file therefore lives at
`docs/adr/0016-regime-aware-eps-selector.md` and is referenced from
this ADR and from
[`ARCHITECTURE.md`](../ARCHITECTURE.md) as ADR-0016.