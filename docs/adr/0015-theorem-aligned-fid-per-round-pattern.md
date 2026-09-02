---
status: accepted
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 15. Theorem-aligned FID and per-round harness pattern

## Context and Problem Statement

The framework's image-side evaluation surface — `adaptive_reflow.eval.fid`
and `adaptive_reflow.eval.clip_score` — was a **canonical FID** as of
Phase 3 of the FID-JMAA workflow. The canonical FID is the Fréchet
distance between two Gaussians fit to the inception-pool3 features of
the two image sets; for Gaussians it is mathematically equivalent to
the **2-Wasserstein (W₂)** distance and, on Euclidean state spaces,
to the **Bounded-Lipschitz (BL)** distance that is the metric of paper
Theorem 1 (Li 2026, `NoiseSelectedRectification_EN.md`, Proposition 3,
`:115-118`). The canonical FID is therefore the right metric *in
principle*.

The canonical FID surface, however, did three things wrong from the
Theorem-1 standpoint:

1. **No per-round emission.** The legacy
   `InceptionV3FIDEvaluator.compute_from_features` /
   `compute_from_precomputed` API returns a single
   `FIDResult(value, is_finite, feature_dim, n_samples)`. The
   framework's per-round scheduler / blender / merge / materializer
   pipeline produces *one sample distribution per round*; the
   canonical evaluator cannot tell the framework which round's
   trajectory satisfied the Theorem-1 prediction and which did not.
   The per-round trajectory (the load-bearing audit object for the
   "BL-distance is monotone non-increasing across rounds" claim) is
   unobservable.
2. **No paper-quantity consumption.** The canonical FID surface
   knows about `(mu, sigma)`, not about `(A_g, B_g, C_g, e_rho)`.
   The four paper quantities are the **audit-trail anchor** for
   Theorem 1 (ADR-0013 §"Paper-quantity naming"); without them on the
   FID result, the empirical trajectory cannot be reconciled with
   the paper Lemma 2 / 3 / 4 / Proposition 3 estimates. The O(eps)
   rate Theorem 1 implies — `fid(r) <= C_paper * eps_r` with
   `C_paper = (C_g * B_g + 1 / e_rho) / A_g` — is not checkable
   because the trajectory carries no `eps_r` and no
   `(A_g, B_g, C_g, e_rho)`.
3. **No `O(eps)` convergence assertion.** The canonical surface is a
   distance calculator, not a *diagnostic*. The "framework's per-round
   FID satisfies the Theorem-1 quantitative bound" claim is a
   first-class deliverable of the FID-JMAA workflow, but the legacy
   surface has no place where that assertion lives.

These three gaps are *load-bearing* for the paper's Section 4
("Empirical Verification") narrative
([`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
§5). The audit asked: how does the per-round scheduler's BL-distance
trajectory reconcile with Theorem 1's quantitative O(eps) bound? The
honest answer today was "we cannot tell" — the canonical FID surface
wasn't designed to.

The decision answers four questions:

1. **What** is the canonical FID surface for the paper?
2. **How** is the `O(eps)` convergence assertion encoded?
4. **What** is the audit-trail emission contract?
4. **How** is byte-for-byte back-compat preserved?

## Decision Drivers

* **Paper-quantity consumption is the audit-trail anchor.** ADR-0013
  introduces the four paper quantities `(A_g, B_g, C_g, e_rho)`
  ([`docs/adr/0013-posterior-selection-drives-algorithm.md`](0013-posterior-selection-drives-algorithm.md)).
  ADR-0014
  ([`docs/adr/0014-hyperparameter-free-framework-principle.md`](0014-hyperparameter-free-framework-principle.md))
  routes them through DERIV-001 derivation rules. TheoremAlignedFID
  must consume them too — the audit reader asking "does this run's
  per-round trajectory match the O(eps) prediction?" needs them on
  every per-round result.
* **Per-round emission is the framework's primary audit object.**
  ADR-0013 names `selection_ratio`, `sheet_evidence`, `cell_evidence`
  as the canonical per-round metric names. TheoremAlignedFID is the
  image-side analogue: the canonical per-round FID trajectory is the
  load-bearing claim for the paper's empirical-verification
  narrative.
* **The Lemma 4 regime check belongs on the FID result, not only on
  the scheduler.** Paper Lemma 4 (line 110-113,
  `NoiseSelectedRectification_EN.md` Lemma 4) bounds the
  physical-complement mass by `exp(-e_rho / (2 eps^2)) = o(eps)`, but
  the `o(eps)` step is only valid while
  `eps^2 < e_rho / log(2)` (the *Lemma 4 regime*). A per-round FID
  result whose `eps_r` violated the regime would be reporting a
  quantity that is no longer grounded in the theorem, and the
  diagnostic should say so explicitly. The Lemma 4 regime check
  surfaces on `TheoremAlignedFIDResult.regime_check_ok` and
  `ConvergenceDiagnostic.regime_violations`.
* **Byte-for-byte back-compat is non-negotiable.** The legacy
  `InceptionV3FIDEvaluator.compute_from_features` /
  `compute_from_precomputed` API must keep returning bit-identical
  `FIDResult` objects. TheoremAlignedFID is a *sibling* module
  (`adaptive_reflow.eval.fid_theorem_aligned`) that delegates the
  Fréchet arithmetic to the legacy module's
  `_compute_frechet_distance_inner`; legacy callers see no change.
* **Stable `nu_g` reference cache.** A profile-specific `nu_g` is the
  paper's reference distribution; two runs with identical `g` must
  produce bit-identical `(ref_mu, ref_sigma)` so the per-round FID
  trajectory is reproducible from a config hash. The cache key is
  SHA-256 of `g` sampled on the canonical paper grid `(-K, K)` with
  default `h=0.01`, matching the `PaperQuantitiesSnapshot` cache
  key so two callers using the same `g` (and the same Monte-Carlo
  seed) hit the same cache entry.

## Considered Options

1. **`TheoremAlignedFID` module + `PerRoundFIDTracker` orchestrator +
   `NuGReferenceRegistry` cache + `TheoremAlignedFIDReport`
   top-level report, sitting alongside the legacy FID surface and
   delegating Fréchet arithmetic to the legacy module.** The legacy
   `FIDProtocol` / `InceptionV3FIDEvaluator` is untouched.
2. **Replace the canonical FID surface with a theorem-aligned
   surface.** Rejected: breaks every legacy caller, every Lumina /
   HiDream smoke test, every `tools/run_image_eval.py` flag, and
   loses the back-compat with the pre-FID-JMAA MJHQ-30K reference
   statistics. The paper-quantity and per-round concerns are
   *additive* concerns, not replacements.
3. **Thread `(A_g, B_g, C_g, e_rho)` through the legacy
   `FIDResult` directly.** Rejected: changes the public surface of
   `FIDResult` (a frozen dataclass with five fields), breaks every
   `as_fid_result` projection, and conflates the legacy and the
   paper-quantity worlds. A separate `TheoremAlignedFIDResult`
   preserves the type discipline.
4. **Compute `O(eps)` convergence as an external utility over an
   array of per-round FIDs.** Rejected: the `O(eps)` check is part
   of the paper-quantity emission contract — without it on the
   per-round result, a downstream caller cannot tell which round's
   `fid(r)` is paper-bound and which is not. The check belongs on
   the report, not in a side utility.

## Decision Outcome

Chosen option: **option 1 — `TheoremAlignedFID` module +
`PerRoundFIDTracker` orchestrator + `NuGReferenceRegistry` cache +
`TheoremAlignedFIDReport` top-level report, sitting alongside the
legacy FID surface and delegating Fréchet arithmetic to the legacy
module.**

### The four artefacts

| Artefact | Path | Concern |
|---|---|---|
| `PaperQuantitiesSnapshot` | `adaptive_reflow.eval.fid_theorem_aligned` | Frozen bundle of `(A_g, B_g, C_g, e_rho)` for one profile `g`; byte-stable. |
| `TheoremAlignedFIDResult` | same | FID result extended with `epsilon`, the four paper constants, `regime_check_ok`, `paper_implied_constant`; projects back to legacy `FIDResult` via `as_fid_result` (byte-stable). |
| `InceptionV3TheoremAlignedFIDEvaluator` | same | Sibling of `InceptionV3FIDEvaluator`. `compute_per_round` emits one `FIDPerRoundResult` per round; `assert_convergence_rate` checks monotonicity and the quantitative `O(eps)` paper-bound. |
| `PerRoundFIDTracker` | same | Orchestrates the round loop, consumes the framework's `eps_schedule` (read-only — does NOT mutate scheduler state), pulls `nu_g` references from `NuGReferenceRegistry`, returns a `TheoremAlignedFIDReport`. |
| `NuGReferenceRegistry` | same | Stable cache of `g -> (ref_mu, ref_sigma)` Gaussian fits; SHA-256 cache key matches `PaperQuantitiesSnapshot` so two callers using the same `g` hit the same entry. |
| `ConvergenceDiagnostic` | same | Surfaces `monotone`, `O_eps_holds`, `regime_violations`, `paper_implied_constant`, `observed_constant`, plus the per-round deltas. |
| `TheoremAlignedFIDReport` | same | Top-level report: rounds + convergence + snapshot + `(ref_mu, ref_sigma)`. |
| `REGIME_VIOLATION_AUDIT_CODE` | same | The canonical audit code `"theorem1_regime_violation"`; surfaces on `ConvergenceDiagnostic.regime_violations`. |

### Per-round emission contract

`InceptionV3TheoremAlignedFIDEvaluator.compute_per_round` emits one
`FIDPerRoundResult` per round, carrying:

* `round_index` (0-based) and `epsilon_r` (the scheduler's `eps` for
  round `r`).
* `result: TheoremAlignedFIDResult` — `value`, `is_finite`,
  `feature_dim`, `n_samples`, plus the four paper quantities
  `(A_g, B_g, C_g, e_rho)` and `regime_check_ok` (Lemma 4 regime
  flag).
* `paper_bound_O_eps = C_paper * epsilon_r` — the implied
  upper-bound per Theorem 1 quantitative `O(eps)` rate, with
  `C_paper = (C_g * B_g + 1 / e_rho) / A_g`.

The `O(eps)` check on the full trajectory is `fid(r) <= C_paper *
eps_r + tolerance` for all `r` where both quantities are finite and
positive; `ConvergenceDiagnostic.O_eps_holds` records whether the
bound holds.

### Lemma 4 regime check

`ConvergenceDiagnostic.regime_violations` is the list of round indices
where `eps_r^2 >= e_rho / log(2)` — i.e. where the scheduler's
`eps` trajectory left the Lemma 4 asymptotic regime. The check is
**diagnostic-only** at this ADR: the diagnostic *records* the
violation, but does not yet *prevent* it. The enforcement path lives
in
[`docs/adr/0016-regime-aware-eps-selector.md`](0016-regime-aware-eps-selector.md),
which makes the regime check *opt-in* on the scheduler side.

### Per-round harness wiring

The per-round FID trajectory reaches the harness through three
additive wires:

* `tools/run_image_eval.py --per-round` — emits per-round metrics for
  the canonical `--reference-stats` path.
* `tools/run_sota_lumina_image_2_0_experiment.py::_make_per_round_callback`
  (line 341) — Lumina-side per-round PNG dump + per-round callback.
* `tools/run_sota_hidream_i1_experiment.py` (analogous) — HiDream-side
  per-round callback.

All three are code-on-disk and unit-verified
(`tests/test_tools/test_run_image_eval.py::test_per_round_emits_per_round_metrics`
+ `test_per_round_falls_back_when_no_round_dirs`); the empirical
per-round PNG dump + HiDream supervisor is **blocked on torch install**
with status `per-round-wired-partial` per
[`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
§8 row 156.

### Module contract

* **stdlib + numpy only** on the public surface (ADR-0001). The
  Fréchet arithmetic is delegated to
  `InceptionV3FIDEvaluator._compute_frechet_distance_inner`; no
  numerical regression can be introduced through this module.
* **Frozen dataclasses** for every result / report type
  (`PaperQuantitiesSnapshot`, `TheoremAlignedFIDResult`,
  `FIDPerRoundResult`, `ConvergenceDiagnostic`,
  `TheoremAlignedFIDReport`).
* **Byte-stable cache** — `NuGReferenceRegistry` uses SHA-256 of `g`
  sampled on the canonical paper grid, so two callers with the same
  `g` (and the same Monte-Carlo seed) hit the same cache entry.
* **Pure** w.r.t. arguments — `compute_per_round` /
  `assert_convergence_rate` are deterministic functions of the
  supplied `sample_features_per_round`, `eps_schedule`, and
  `paper_quantities_snapshot`.
* **Back-compat via `as_fid_result`** —
  `TheoremAlignedFIDResult.as_fid_result()` projects to a byte-stable
  `FIDResult` (drops the paper-quantity fields), so the legacy
  single-shot FID consumer
  (`tools.run_image_eval.compute_fid_from_features`) keeps working
  unchanged.

### Consequences

Positive:

* The framework's image-side FID surface now consumes the four
  paper quantities `(A_g, B_g, C_g, e_rho)` per round. A reviewer
  asking "does this run's per-round trajectory match Theorem 1's
  O(eps) prediction?" gets a `ConvergenceDiagnostic` answer rather
  than a hand-wave.
* Per-round tracking is enabled. The audit reader can see
  `fid(0), fid(1), ..., fid(R-1)` and check monotonicity against
  Theorem 1's BL → KL-monotone prediction (paper Proposition 3 →
  ADR-0013).
* The Lemma 4 regime check surfaces as
  `TheoremAlignedFIDResult.regime_check_ok` (per-round) and
  `ConvergenceDiagnostic.regime_violations` (trajectory-wide). The
  regime *enforcement* is opt-in on the scheduler side
  ([ADR-0016](0016-regime-aware-eps-selector.md)); the regime
  *diagnosis* is on by default.
* The legacy `FIDProtocol` / `InceptionV3FIDEvaluator` surface is
  byte-stable — `as_fid_result()` projects to a `FIDResult` that
  equals the legacy output bit-for-bit. The existing Lumina /
  HiDream / FlowMol3 smoke tests keep working unchanged.
* The `NuGReferenceRegistry` cache key matches the `PaperQuantitiesSnapshot`
  cache key, so the FID reference and the paper-quantity reference
  for the same `g` come from the same source — no risk of the two
  caches drifting on a `g` change.

Negative:

* The package grows by ~700 lines across
  `adaptive_reflow/eval/fid_theorem_aligned.py` (and a similar
  number across the test file). The abstraction is only worth that
  cost while the per-round trajectory is actually emitted into the
  audit trail — the empirical per-round PNG dump is currently
  blocked on torch install (`per-round-wired-partial` status).
* The `O(eps)` convergence assertion is *quantitative*, not
  statistical: `C_paper = (C_g * B_g + 1 / e_rho) / A_g` is a
  conservative upper-bound constant, and the observed
  `fid(r) / eps_r` ratio can sit well below it on benign inputs.
  A reader who expects a single-line "yes / no" answer gets a
  `ConvergenceDiagnostic` that names the per-round deltas, the
  regime violations, and the gap between `paper_implied_constant`
  and `observed_constant`.
* The Lemma 4 regime check is *diagnostic-only* on the FID side —
  it records violations but does not block the run. The opt-in
  scheduler-side enforcement is in
  [ADR-0016](0016-regime-aware-eps-selector.md); a caller that
  wants fail-closed semantics must opt into `regime_aware=True`.
* The per-round harness wiring is on disk and unit-verified but
  the empirical per-round PNG dump + HiDream supervisor are
  blocked on torch install. Status `per-round-wired-partial`
  per [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 row 156.

### Relationship to ADR-0013 (paper-quantity naming)

ADR-0013 introduces the four paper quantities
`(A_g, B_g, C_g, e_rho)` and the theorem-driven scheduler
justification. This ADR **consumes** those quantities as inputs to
`TheoremAlignedFIDResult` and `ConvergenceDiagnostic` but does not
redefine them. ADR-0013's paper-quantity naming is canonical; this
ADR adds the FID-side paper-quantity consumption layer.

### Relationship to ADR-0014 (DERIV-001)

ADR-0014 introduces the Hyperparameter-Free Framework Principle. The
`C_paper = (C_g * B_g + 1 / e_rho) / A_g` constant in this ADR is a
direct consumer of two of the five DERIV-001 derivation outputs — the
`paper_quantities` evaluators
(`adaptive_reflow.contracts.paper_quantities.{sheet_evidence_A,
root_cell_packing_B, per_cell_coefficient_C, exterior_gap_e_rho}`).
The TheoremAlignedFID surface is the **empirical** verification
path for the four quantities that ADR-0014 consumes *theoretically*
through its derivation rules.

### Relationship to ADR-0016 (regime enforcement)

ADR-0016 introduces the opt-in scheduler-side `RegimeAwareEpsSelector`
that *enforces* the Lemma 4 regime on the scheduler's `eps` trajectory
(`eps^2 < e_rho / log 2`). This ADR's
`ConvergenceDiagnostic.regime_violations` is the FID-side
*diagnosis* of the same condition. Together they form a
**diagnose-then-enforce** workflow: TheoremAlignedFID records the
violations on every run; a caller who wants fail-closed semantics
opts into `RegimeAwareEpsSelector` to *prevent* them on subsequent
runs.

### Confirmation

The decision is enforced by:

* `adaptive_reflow/eval/fid_theorem_aligned.py` — `PaperQuantitiesSnapshot`,
  `TheoremAlignedFIDResult`, `FIDPerRoundResult`, `ConvergenceDiagnostic`,
  `TheoremAlignedFIDReport`, `NuGReferenceRegistry`,
  `InceptionV3TheoremAlignedFIDEvaluator`, `PerRoundFIDTracker`,
  `REGIME_VIOLATION_AUDIT_CODE`.
* `adaptive_reflow/eval/fid.py::InceptionV3FIDEvaluator` —
  unchanged; the Fréchet arithmetic is delegated from
  TheoremAlignedFID into `_compute_frechet_distance_inner`.
* `tests/test_eval/test_fid_theorem_aligned.py` — 15 tests:
  snapshot byte-stability, per-round emission,
  `assert_convergence_rate` monotonicity + `O(eps)` bound, registry
  cache stability, legacy back-compat via `as_fid_result`.
* `tools/run_image_eval.py --per-round`,
  `tools/run_sota_lumina_image_2_0_experiment.py::_make_per_round_callback`
  (line 341), `tools/run_sota_hidream_i1_experiment.py` (analogous) —
  per-round harness wiring.
* `tests/test_tools/test_run_image_eval.py::test_per_round_emits_per_round_metrics`
  + `test_per_round_falls_back_when_no_round_dirs` — unit-verified
  per-round emission + graceful no-round-dirs fallback.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5 — the FID-JMAA workflow + Phase 4 verdict: 15 PASS tests across
  the theorem-aligned FID module; per-round harness wiring on disk;
  empirical blocked on torch install.

## More Information

* [docs/adr/0013](0013-posterior-selection-drives-algorithm.md) —
  the paper-quantity naming `(A_g, B_g, C_g, e_rho)` and the
  theorem-driven scheduler justification that this ADR consumes as
  audit-trail anchors.
* [docs/adr/0014](0014-hyperparameter-free-framework-principle.md) —
  the DERIV-001 derivation rules whose `paper_quantities`
  evaluators feed `TheoremAlignedFIDResult`'s
  `(A_g, B_g, C_g, e_rho)` fields.
* [docs/adr/0016](0016-regime-aware-eps-selector.md) — the
  scheduler-side Lemma 4 regime *enforcement* (opt-in via
  `regime_aware=True`); this ADR's
  `ConvergenceDiagnostic.regime_violations` is the FID-side
  *diagnosis*.
* [`docs/lean/THEOREM_1_MAPPING.md`](../lean/THEOREM_1_MAPPING.md)
  §B.3 (Exterior exponential bound, paper Lemma 4, line 110-113) —
  the formal verification of Lemma 4 and the `e_rho` quantity this
  ADR's regime check consumes.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5 — the FID-JMAA workflow + Phase 4 verdict (the
  TheoremAlignedFID surface, the per-round harness wiring status,
  the regime-enforcement diagnostic-only status).
* [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 rows 156-157 — the per-round harness wiring status
  (`per-round-wired-partial`) and the Phase-4 scheduler `e_rho`
  regime enforcement status (diagnostic-only).
* `NoiseSelectedRectification_EN.md` Lemma 4 (line 110-113) — the
  paper's exterior exponential bound
  `∫_{T^c \ ⋃_z I_z} p_ε ≤ e^{-e_ρ/(2ε²)} = o(ε)` whose
  `o(ε)` step is the Lemma 4 regime `eps^2 < e_rho / log 2`.
* `adaptive_reflow/eval/fid_theorem_aligned.py` — the TheoremAlignedFID
  module + the eight artefacts (`PaperQuantitiesSnapshot`,
  `TheoremAlignedFIDResult`, `FIDPerRoundResult`,
  `ConvergenceDiagnostic`, `TheoremAlignedFIDReport`,
  `NuGReferenceRegistry`,
  `InceptionV3TheoremAlignedFIDEvaluator`, `PerRoundFIDTracker`)
  plus the `REGIME_VIOLATION_AUDIT_CODE` constant.
* `tests/test_eval/test_fid_theorem_aligned.py` — the 15-test
  regression surface (snapshot byte-stability, per-round emission,
  `O(eps)` convergence assertion, regime check, registry cache
  stability, legacy back-compat via `as_fid_result`).

## Numbering note

This ADR was originally described in the Workflow K task brief as
"ADR-0007" (to group it numerically with the FID-JMAA workflow's
Phase-4 deliverables). The audit identified a slug collision with the
existing
[ADR-0007](0007-prev-anchored-bounded-merge.md)
("Prev-anchored bounded merge") — two ADRs sharing the number `7`
would be a documentation-reader trap. The audit recommended the
safer allocation `0015` (next free monotonic prefix after the
existing ADR-0014). This file therefore lives at
`docs/adr/0015-theorem-aligned-fid-per-round-pattern.md` and is
referenced from this ADR and from
[`ARCHITECTURE.md`](../ARCHITECTURE.md) as ADR-0015.