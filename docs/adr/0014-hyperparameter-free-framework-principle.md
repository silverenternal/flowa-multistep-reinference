---
status: accepted
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 14. Hyperparameter-Free Framework Principle (DERIV-001)

## Context and Problem Statement

The framework's algorithm layer (the four-axis
`SchedulerProtocol` / `PolicyDriverProtocol` /
`MergeOperatorProtocol` / `RestartBlenderProtocol` product pinned
by [ADR-0011](0011-algorithm-abstractions.md), and the per-channel
materialization / condition-injection / state-channel surface
introduced later) exposes **23 algorithm-layer hyperparameters**
across the scheduler / merge / blender / evidence-driver surface
(plus the four paper-quantity contracts `A_g`, `B_g`, `C_g`,
`e_rho` from [ADR-0013](0013-posterior-selection-drives-algorithm.md)).
Before DERIV-001, every one of those 23 values was **hand-set** in a
module-level `DEFAULT_*` constant:

* `eps_implicit = 0.05` — hard-coded into
  `CodimensionSheetScheduler.__init__`.
* `DEFAULT_MEMORY_FRACTION_FALLBACK = 0.5` — the mid-cycle anchor.
* `DEFAULT_CONSTANT_BETA = 0.5`,
  `DEFAULT_ADAPTIVE_TARGET_ESTIMATE = 0.5`,
  `DEFAULT_DISTANCE_DECAY_TEMPERATURE = 1.0`,
  `DEFAULT_MIN_GUMBEL_TEMP = 1e-3`,
  `DEFAULT_FEEDBACK_METRIC_WEIGHTS = {"W2": 1.0, "coverage": 0.3, "selection_ratio": 0.5}`,
  `EPS_LOG = 1e-30`,
  `JitteredConstantScheduler.jitter_std = 0.05`,
  `MeanFlowMergeOperator.tolerance = 1e-9`,
  `MeanFlowMergeOperator.degenerate_eps = 1e-12`,
  `EMAOperator.alpha = 0.1`,
  `ConvergenceAdaptiveScheduler.{kp, kd, shift_max, ema} = {0.10, 0.05, 0.15, 0.3}`,
  `ExponentialScheduler.alpha = 0.1`,
  `PolynomialScheduler.power = 2.0`,
  `SigmoidScheduler.{midpoint, steepness} = {0.5, 10.0}`,
  `HandoffSequentialScheduler.handoff_window = 0`,
  `BoundedMergeOperator` floor divisor `4.0`,
  `LipschitzStepSize` step `1.0 / n_steps`,
  and so on.

These hand-set values were a **silent bug source**. A reviewer who
asked "why `0.05` for `eps_implicit` and not `0.01` or `0.1`?" got
no answer — the constant was placed there by a previous author,
empirically, and never linked to a paper quantity, a Lipschitz
estimate, or a theorem. Two constants in the same file could
silently conflict (e.g. `epsilon = 1e-9` in one branch and
`epsilon = 1e-12` in another) and the only way to know was to grep.
The risk is asymmetric: a poorly-justified hyperparameter cannot be
diagnosed after the fact because there is no derivation chain to
trace back to.

The user's insight on 2026-09-01 was: **the framework's 23
hyperparameters should not be arbitrary**. Every value should
trace to one of five authorized sources — a published paper
quantity, a local-curvature estimate, a closed-form algorithm
invariant, an information-geometry identity, or a generic
convergence theorem. The hand-set constants stay as **named
provenance** with documented empirical origin, but they are the
documented exception, not the rule.

The decision answers five questions:

1. **What** are the five authorized sources?
2. **How** is the principle operationalized?
3. **Which** concrete derivations instantiate the principle
   on which hyperparameters?
4. **What** is the backward-compat invariant that protects the
   existing 2356+15 test surface?
5. **What** is the DAG discipline that prevents derivation
   cycles?

## Decision Drivers

* **Provenance is the product.** A reader asking "where does
  `eps_implicit` come from?" should be able to grep the source
  and arrive at one (or more) of the five authorized categories
  with a closed-form formula and an academic citation. A
  hand-set constant must declare itself as such via a
  `DEFAULT_*_FALLBACK` named-provenance entry.
* **Backward compatibility is non-negotiable.** The 2356+15
  existing tests pass today because the hand-set constants are
  embedded in the module-level defaults. Every existing caller
  that does not opt into the parameter-free regime must keep
  getting the exact same values. The dispatcher MUST fall
  back to the documented hand-set constant when the supplied
  `DerivationContext` is missing the inputs the rule needs —
  the fallback is the byte-for-byte equivalent of the legacy
  wiring.
* **Strict DAG.** A derivation reads paper quantities,
  scheduler state, OT metrics, or local curvature — but
  **never** writes back into the quantities it derives from.
  The `NAMESPACE_ALGORITHM_POSTERIOR` constant isolates the
  Fisher-on-algorithm-posterior namespace from
  Fisher-on-model-parameters so a future
  `FisherMemoryFraction` derivation cannot accidentally share
  state with model-level optimizers. The
  `DerivationCycleError` exception enforces runtime checks for
  the small set of concrete derivations that participate in
  the cross-derivation DAG.
* **Five authorized sources, no sixth.** The principle does
  not permit "I picked `0.05` because it works on my
  benchmark". Hand-set engineering constants are admitted
  only as named provenance with documented empirical origin,
  and only when no derivation rule from the five categories
  applies. The doc verifier
  (`tools/check_docs_against_code.py`) cross-checks every
  concrete derivation's `derivation_source`,
  `derivation_formula`, and `academic_precedent` class-level
  attributes against the corresponding
  `docs/ALGORITHMS.md` row, flagging drift.
* **Fail-closed semantics.** A derivation that receives
  non-finite, non-numeric, or contract-violating inputs
  raises `ValueError` rather than silently coercing. The
  dispatcher catches the `ValueError` and converts it to the
  documented hand-set fallback — the engine never crashes
  because a Lipschitz estimator supplied a missing or
  non-positive value.

## Considered Options

1. **Abstract `DerivationRule` protocol plus 23 concrete
   subclasses, each pinned to one of the five authorized
   sources, with strict-DAG discipline and named-provenance
   fallback constants.** Every framework hyperparameter is
   routed through a `default_X(context, **kwargs)` dispatcher
   that picks the canonical derivation rule, attempts to
   derive from the supplied context, and falls back to the
   documented `DEFAULT_X_FALLBACK` constant if the derivation
   context is missing the required fields.
2. **Replace every `DEFAULT_*` constant with a hard-coded
   paper quantity at the call site.** Rejected: it makes the
   hand-set→derived transition compulsory and breaks every
   caller that does not have a `paper_quantities_provider`
   wired. The principle is opt-in, not mandatory.
3. **Per-hparam YAML config (`hyperparameters.yaml`) with
   either a derivation source name or a literal float.**
   Rejected: introduces a runtime config file that has to be
   loaded before the constants are reachable; bypasses the
   typed `DerivationContext` machinery; and makes the
   `config_hash` audit invariant (ADR-0010) depend on file
   IO instead of a deterministic in-memory protocol. The
   principle is a *code-level* commitment, not a *config-level*
   override.
4. **Single global registry of `(name, formula, fallback)`
   triples plus a free-form evaluator.** Rejected: the
   registry collapses the type diversity
   (`PolyakMemoryFraction` returns a `memory_fraction` in
   `[0, 1]`; `MetricWeightRule` returns a `dict[str, float]`;
   `SigmoidMidpointSteepnessRule` returns *two* values, one
   via `derive_midpoint` and one via `derive_steepness`).
   The abstract `DerivationRule` protocol with frozen
   dataclass subclasses preserves the type signature per
   rule and lets the doc verifier cross-check each one's
   `derivation_formula` against the implementation.

## Decision Outcome

Chosen option: **option 1 — abstract `DerivationRule` protocol
plus 23 concrete subclasses, strict-DAG discipline, and named
provenance fallback constants.**

### The five authorized sources

| Category | Alias | Closed-form anchor | Concrete example |
|---|---|---|---|
| Paper quantity | `paper_quantities` | JMAA Lemmas 2-5 (`A_g`, `B_g`, `C_g`, `e_rho`) | `OTEpsilonSchedule`: `eps_t = eps_0 * (1 + C_g * t)` |
| Local curvature | `lipschitz` | Lipschitz constant `L_e`, machine epsilon | `LipschitzStepSize`: `h_t = (tol / max(err, 1e-9))^{1/5} / L_e` |
| Mathematical invariant | `variance_preserving` / `ot` / `bl_convergence` / `other` | Closed-form algorithm-family invariant | `OTEpsilonSchedule` (OT path), `BLConvergenceEpsilonSchedule` (`sqrt(e_rho * delta_t)`), `PolynomialPowerRule` (`2 * L / (L + 1)`) |
| Information-geometry identity | `fisher` | Natural-gradient / Fisher on algorithm posterior | `FisherMemoryFraction`: `m_Fisher = 1 / (1 + F_trace / d)` |
| Generic convergence theorem | `polyak` | Polyak step size, Dormand-Prince adaptive `h_t`, Adam β1 | `EMAInverseVarianceRule`: `alpha = 1 / (1 + grad_var / grad_mean^2)` |

### The five concrete derivation rules (DERIV-001 proof on the algorithm layer)

| Rule | Source | Closed form | Hyperparameter derived | Fallback (back-compat) |
|---|---|---|---|---|
| `PolyakMemoryFraction` | `ot` | `m_t := W2_round_t / (W2_round_0 + W2_round_t)` | `memory_fraction` (blender_extra) | `1 - n_cap` (ADR-0010) |
| `OTEpsilonSchedule` | `paper_quantities` | `eps_t := eps_implicit * (1 + C_g * t)` | `eps_implicit` (codimension sheet scheduler) | `0.05` (CodimensionSheetScheduler default) |
| `BLConvergenceEpsilonSchedule` | `bl_convergence` | `eps_t := sqrt(e_rho * delta_t)` | `eps_threshold` (BL-convergence scale) | `1e-3` (evidence-heuristic threshold) |
| `LipschitzStepSize` | `lipschitz` | `h_t := (tol / max(err, 1e-9))^{1/5} / L_e` | ODE step (Dormand-Prince), `handoff_window` | `1.0 / n_steps` (uniform-step DP) |
| `FisherMemoryFraction` | `fisher` | `alpha_grad := exp(-e_rho); m_Fisher := 1 / (1 + F_trace / d)` | `alpha_grad` (MeanFlow EMA proxy) | `0.5` (mid-cycle anchor) |

These five rules are the **canonical proof** that the principle
holds on the algorithm layer's most-exercised surface
(`memory_fraction`, `eps_implicit`, `eps_threshold`, ODE step,
`alpha_grad`). They are the P-18 deliverables that close the
G3 (P-19) gate in
[`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
§4.

### The full 23-hparam coverage map (P-18 + P-19)

The framework's algorithm layer exposes 23 hyperparameters
across the scheduler / merge / blender / evidence-driver surface.
The full mapping lives in
[`docs/ALGORITHMS.md`](../ALGORITHMS.md) §"Hyperparameter-Free
Framework Principle (DERIV-001)" §"Full 23-hparam coverage map
(P-18 + P-19)" — the table enumerates every entry with its
`derivation_source`, the closed-form formula, the hand-set
back-compat fallback (preserved verbatim so legacy callers keep
getting the same value when the context is missing), and the
academic citation. The 22 active `default_*` entry points plus
one named-provenance divisor (`BoundedMergeFloorRule`, P-19 #4)
total **23 algorithm-layer hyperparameters** fully covered by
DERIV-001; entry #23 (`nfe/num_steps`, the adapter-layer ODE
step count) is the FM-LCM territory deferred per P-18 task
statement.

### Backward compatibility invariant

The dispatcher is **fail-closed**: every derivation has a
`fallback: ClassVar[float]` that returns the byte-for-byte
equivalent of the legacy hand-set constant when the supplied
`DerivationContext` is missing the inputs the rule needs.

* `PolyakMemoryFraction.fallback` → `1 - n_cap` (ADR-0010).
* `OTEpsilonSchedule.fallback` → `0.05` (CodimensionSheetScheduler default).
* `BLConvergenceEpsilonSchedule.fallback` → `1e-3` (evidence-heuristic threshold).
* `LipschitzStepSize.fallback` → `1.0 / n_steps` (uniform-step Dormand-Prince).
* `FisherMemoryFraction.fallback` → `0.5` (mid-cycle anchor).

Existing callers that do not pass a `DerivationContext` keep
getting the legacy value verbatim, so the existing 2356+15 test
suite remains green while the parameter-free regime is opt-in.
A buggy W2 estimator that supplies negative or non-finite values
raises `ValueError` from the rule's `derive` method; the
dispatcher catches and converts to the documented fallback
rather than crashing the engine.

### Constraint DAG

The principle's strict-DAG rule says a derivation reads paper
quantities, scheduler state, OT metrics, or local curvature —
**never** writes back into the quantities it derives from. The
five concrete derivation rules partition cleanly along the
dependency arrow:

* `PolyakMemoryFraction` reads `ot_metrics` + `scheduler_state`
  → outputs `memory_fraction` (consumed by the blender, NOT by
  the W2 measurement).
* `OTEpsilonSchedule` reads `paper_quantities` + `scheduler_state`
  → outputs `eps_implicit` (consumed by the codimension sheet
  scheduler, NOT by `C_g`).
* `BLConvergenceEpsilonSchedule` reads `paper_quantities` +
  `scheduler_state` → outputs `eps_threshold` (consumed by the
  evidence driver, NOT by `e_rho`).
* `LipschitzStepSize` reads `local_curvature` + `scheduler_state`
  → outputs ODE step (consumed by the integrator, NOT by the
  Lipschitz estimator).
* `FisherMemoryFraction` reads `paper_quantities` +
  `local_curvature` → outputs `alpha_grad` (consumed by the
  MeanFlow EMA proxy, NOT by the posterior Fisher).

The `Fisher-on-algorithm-posterior` namespace is isolated from
`Fisher-on-model-parameters` by `NAMESPACE_ALGORITHM_POSTERIOR`
so a future derivation that operates on model parameters cannot
accidentally share state with the algorithm-posterior Fisher.
The `DerivationCycleError` exception enforces runtime checks
for the small set of concrete derivations that participate in
the cross-derivation DAG (PolyakMemoryFraction ↔
FisherMemoryFraction, etc.) — a cycle attempt is forbidden by
construction.

### Module contract

* **stdlib-only on the public surface** (ADR-0001). The internal
  derivation math uses `math` only; no `numpy` or `scipy`
  import is required.
* **Frozen dataclasses** for every concrete subclass so the
  class-level provenance attributes
  (`derivation_source`, `derivation_formula`,
  `academic_precedent`) cannot be silently mutated.
* **Pure** w.r.t. arguments — `derive(context)` is a
  deterministic function of the context and the instance
  configuration.
* **Fail-closed** — `DerivationContext` fields are typed
  `Optional`; when a derivation requires a field that is
  `None`, the derivation returns the documented hand-set
  fallback rather than guessing.
* **Provenance-rich** — every concrete derivation exposes the
  authoritative source category, the closed-form formula, and
  the academic citation.

### Consequences

Positive:

* The framework's 23 algorithm-layer hyperparameters all trace
  to one (or more) of the five authorized sources. A reviewer
  who asks "where does `eps_implicit` come from?" gets a
  closed-form formula and an academic citation, not a hand-set
  constant with no provenance.
* The principle is **opt-in**. Existing callers that do not
  pass a `DerivationContext` keep getting the legacy values
  verbatim, so the 2356+15 test surface stays green while the
  parameter-free regime is exercised on the 2D oracle (P-19).
* The strict-DAG rule prevents the silent bug where a
  derived value feeds back into the quantity it was derived
  from. The `NAMESPACE_ALGORITHM_POSTERIOR` constant isolates
  the algorithm-posterior Fisher from the model-parameter
  Fisher, preventing cross-namespace cycles.
* The doc verifier
  (`tools/check_docs_against_code.py`) cross-checks every
  concrete derivation's `derivation_source`,
  `derivation_formula`, and `academic_precedent` against the
  corresponding `docs/ALGORITHMS.md` row, flagging drift.
* The 23-hparam coverage map (P-18 + P-19) lives in
  `docs/ALGORITHMS.md` as a single greppable table; the G3
  gate in
  `docs/r17-survey/algorithm-correctness-evidence.md` §4
  records the empirical verification (22 PASS tests across
  2 files; 5 derivation rules match closed-form on the 2D
  oracle; framework trajectory converges monotonically under
  derived hyperparameters).

Negative:

* The package grows by ~3,000 lines across the
  `_derivation.py` module. The abstraction is only worth that
  cost while more than one hyperparameter is actually
  derived rather than hand-set — hence the full 23-hparam
  coverage map (P-18 + P-19) was a precondition for the
  principle's adoption, not a follow-on.
* The `Fallback` constants (`DEFAULT_MEMORY_FRACTION_FALLBACK`
  etc.) are still hand-set, so a reviewer who asks "where does
  `0.05` come from?" gets "the legacy `CodimensionSheetScheduler`
  default" rather than a paper quantity. This is the named
  provenance carve-out: the carve-out is **explicit** in the
  table, and every fallback is documented as "preserved
  byte-for-byte for back-compat".
* The DAG discipline rejects cycles by raising
  `DerivationCycleError` — but a reviewer who wants to share
  state across two derivations (e.g. `PolyakMemoryFraction`
  and `FisherMemoryFraction` both reading the same W2
  history) cannot; they must re-derive the value or pass it
  explicitly via `DerivationContext`. This is the principled
  trade-off: cycles are how silent bugs propagate, and the
  constraint is load-bearing.
* Entry #23 (`nfe/num_steps`, the adapter-layer ODE step
  count) is **not** covered by the principle — it is the
  FM-LCM territory deferred per P-18 task statement. A
  reviewer who asks "why isn't `nfe/num_steps` derived?"
  gets "it is an adapter-layer concern, not an algorithm-layer
  concern, and the FM-LCM redesign workflow owns it". This is
  the documented scope boundary.

### Relationship to ADR-0011 (4-axis algorithm layer)

ADR-0011 lists the four-axis `(scheduler, policy_driver,
merge_operator, blender)` algorithm abstraction as the
**layer** abstraction. This ADR adds a fifth axis (`derivation`)
that is **orthogonal** to the four: every algorithm-layer object
in ADR-0011 can have its hyperparameter routed through a
`DerivationRule`, but the routing is optional and the layer
abstraction is unchanged. The cardinality of the algorithm
layer is therefore **5 axes after this ADR** (4 algorithm roles
+ 1 derivation role), not 4. The relationship is
"ADR-0011's 4 axes × this ADR's derivation axis = a
fully-derived framework configuration".

### Relationship to ADR-0013 (paper-quantity naming)

ADR-0013 introduces the four paper quantities
`(A_g, B_g, C_g, e_rho)` and the theorem-driven scheduler
justification. This ADR **consumes** those quantities as
inputs to derivation rules (e.g.
 `BLConvergenceEpsilonSchedule` reads `e_rho`; `OTEpsilonSchedule`
 reads `C_g`) but does not redefine them. ADR-0013's
 paper-quantity naming is canonical; this ADR adds the
 derivation-role layer above it.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/algorithm/_derivation.py` — the abstract
  `DerivationRule` Protocol, the `DerivationContext`
  dataclass, the `make_derivation_context` factory, and the
  five P-18 concrete subclasses
  (`PolyakMemoryFraction`, `OTEpsilonSchedule`,
  `BLConvergenceEpsilonSchedule`, `LipschitzStepSize`,
  `FisherMemoryFraction`) plus the 18 P-19 subclasses
  (`MeanFlowToleranceRule`, `MachineEpsilonRule`,
  `EMAInverseVarianceRule`, `LipschitzTemperatureRule`,
  `MinGumbelTempRule`, `EpsLogRule`, `ExponentialAlphaRule`,
  `PolynomialPowerRule`, `SigmoidMidpointSteepnessRule`,
  `ConvergenceAdaptivePolyRule`, `MetricWeightRule`,
  `VariancePreservingJitterRule`, `MidpointBetaRule`,
  `BoundaryConditionRule`, `MeanFlowFixedStrengthRule`,
  `BoundedMergeFloorRule`, `FisherMemoryFraction`,
  `ConvergenceAdaptivePolyRule`).
* `adaptive_reflow/algorithm/blender_extra.py::derive_default_memory_fraction`
  — the canonical `memory_fraction` dispatcher (Polyak → ADR-0010
  fallback).
* `adaptive_reflow/algorithm/scheduler/_core.py::derive_default_eps_implicit`
  — the canonical `eps_implicit` dispatcher (OT → BL → fallback).
* `adaptive_reflow/algorithm/evidence_driver.py::derive_default_eps_threshold`
  — the canonical `eps_threshold` dispatcher (BL → fallback).
* `adaptive_reflow/algorithm/merge_operator_v3.py::derive_default_alpha_grad`
  — the canonical `alpha_grad` dispatcher (Fisher → fallback).
* `adaptive_reflow/algorithm/handoff.py::derive_default_handoff_window`
  — the canonical handoff-window dispatcher (Lipschitz → fallback).
* `tests/test_algorithm/test_derivation.py` — the protocol,
  closed-form, fallback, and dispatcher regression tests.
* `tests/test_algorithm/test_hparam_derived_2d_oracle.py` —
  the P-19 G3 gate: 5 derivation rules match closed-form on
  the 2D oracle, degenerate-input fallbacks return the
  ADR-0010 back-compat value, framework trajectory matches
  P-13 convergence under the derived hyperparameters.
* `tests/test_algorithm/test_hparam_derived_end_to_end.py` —
  the P-19 end-to-end trajectory test: framework KL on the
  Gaussian-mixture target is monotone non-increasing under
  derived hyperparameters (no hand-set fallback).
* `tools/check_docs_against_code.py` — the doc scanner
  cross-checks every concrete derivation's
  `derivation_source`, `derivation_formula`, and
  `academic_precedent` against the corresponding
  `docs/ALGORITHMS.md` row.
* `docs/ALGORITHMS.md` §"Hyperparameter-Free Framework
  Principle (DERIV-001)" — the principle, the five
  authorized sources, the DAG / namespace discipline, the
  backward-compat invariant, and the full 23-hparam coverage
  map (P-18 + P-19).
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §4 — the G3 (P-19) gate evidence chain: 22 PASS tests
  across 2 files, 5 derivation rules match closed-form, 0
  bugs filed.

## More Information

* [docs/adr/0010](0010-cosine-driven-memory-fraction.md) —
  the schedule-driven memory fraction `1 - n_cap` preserved
  as the documented back-compat fallback for
  `PolyakMemoryFraction`.
* [docs/adr/0011](0011-algorithm-abstractions.md) — the
  four-role algorithm layer (`SchedulerProtocol` /
  `PolicyDriverProtocol` / `MergeOperatorProtocol` /
  `RestartBlenderProtocol`) that this ADR adds the
  `DerivationRule` derivation axis on top of.
* [docs/adr/0013](0013-posterior-selection-drives-algorithm.md)
  — the paper-quantity naming (`A_g`, `B_g`, `C_g`,
  `e_rho`) that this ADR consumes as inputs to derivation
  rules but does not redefine.
* [`docs/ALGORITHMS.md`](../ALGORITHMS.md) §"Hyperparameter-
  Free Framework Principle (DERIV-001)" — the principle, the
  five authorized sources, the DAG / namespace discipline,
  the backward-compat invariant, the sample wiring, and the
  full 23-hparam coverage map (P-18 + P-19).
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §4 (Gate 3 — P-19) — the empirical evidence chain: 22
  PASS tests across 2 files, 5 derivation rules match
  closed-form on the 2D oracle, framework trajectory
  converges monotonically under derived hyperparameters,
  0 bugs filed.
* `adaptive_reflow/algorithm/_derivation.py` — the abstract
  `DerivationRule` Protocol + the five P-18 concrete
  subclasses + the 18 P-19 subclasses + the dispatcher
  helpers (`default_memory_fraction`, `default_eps_implicit`,
  `default_lipschitz_step`, `default_alpha_grad`,
  `default_handoff_window`).
* `tests/test_algorithm/test_derivation.py`,
  `tests/test_algorithm/test_hparam_derived_2d_oracle.py`,
  `tests/test_algorithm/test_hparam_derived_end_to_end.py` —
  the protocol, closed-form, fallback, dispatcher, and
  G3-gate regression tests.

## Numbering note

This ADR was originally described in the Workflow K task brief as
"ADR-0006" (to group it numerically with ADR-0010 / ADR-0011 /
ADR-0013, the algorithm-layer decisions it builds on). The
audit identified a slug collision with the existing
[ADR-0006](0006-engine-wraps-adapter-pattern.md)
("Engine-wraps-adapter pattern") — two ADRs sharing the number
`6` would be a documentation-reader trap. The audit
recommended the safer allocation `0014` (next free monotonic
prefix after the existing ADR-0013). This file therefore lives
at `docs/adr/0014-hyperparameter-free-framework-principle.md`
and is referenced from this ADR and from
[`ARCHITECTURE.md`](../ARCHITECTURE.md) as ADR-0014.