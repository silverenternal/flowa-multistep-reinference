---
status: superseded
date: 2026-09-05
deciders: flowa-maintainer
consulted: N/A
informed: N/A
supersedes:
  - docs/adr/0006-hyperparameter-free-framework-principle.md
  - docs/adr/0007-theorem-aligned-fid-per-round-pattern.md
  - docs/adr/0008-regime-aware-eps-selector.md
---

# Superseded slug-collision pointers — consolidated archive

> **Consolidated pointer file.** Wave 16 Phase 3 (2026-09-05) merged
> three separate slug-collision pointer files into this single document
> to reduce live-nav surface area. The three pointer files
> (`docs/adr/0006-hyperparameter-free-framework-principle.md`,
> `docs/adr/0007-theorem-aligned-fid-per-round-pattern.md`,
> `docs/adr/0008-regime-aware-eps-selector.md`) have been **deleted**
> (see `git rm` history). Each pointer's narrative is preserved below
> in its own subsection so a reviewer who follows the brief's
> "ADR-0006" / "ADR-0007" / "ADR-0008" label still lands on the full
> explanation. The canonical content lives at the three new monotonic
> allocations (0014 / 0015 / 0016), unchanged.

## Background — the slug collision

The Workflow K task brief on 2026-09-01 asked for three new ADRs under
the slug slots `0006`, `0007`, `0008`:

| Brief slot | Subject | Canonical allocation |
|---|---|---|
| ADR-0006 | Hyperparameter-Free Framework Principle (DERIV-001) | [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md) |
| ADR-0007 | Theorem-aligned FID + per-round harness pattern | [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md) |
| ADR-0008 | Regime-aware eps selector (opt-in Lemma 4 enforcement) | [ADR-0016](../adr/0016-regime-aware-eps-selector.md) |

The audit identified slug collisions with the existing
[ADR-0006](0006-engine-wraps-adapter-pattern.md),
[ADR-0007](0007-prev-anchored-bounded-merge.md), and
[ADR-0008](0008-claim-gate-deferral-placeholder.md) (which live in
this archive subdirectory because they were themselves superseded —
note: those archived ADRs cover different topics; see per-slot
subsections below), and recommended allocating the next free monotonic
prefixes (0014 / 0015 / 0016). The three canonical ADRs were written
at those prefixes with an explicit `## Numbering note` at the bottom
of each, pointing back to the slug-collision source.

Three brief-slot pointer files were created at the live `0006/0007/0008`
slots to forward every cross-reference to the canonical allocations.
Wave 16 Phase 3 (2026-09-05) consolidated those three pointers into
this single archive file so the live `docs/adr/` directory contains
exactly one source of truth per numeric prefix (the canonical ADR
plus the pre-existing archived ADRs). A reviewer who follows the
brief's "ADR-0006" / "ADR-0007" / "ADR-0008" label finds the full
narrative in the per-slot subsections below; the canonical content
lives at the three new monotonic allocations (0014 / 0015 / 0016).

The pre-existing archived ADRs at this subdirectory's slot `0006` /
`0007` / `0008` (engine-wraps-adapter / prev-anchored-bounded-merge /
claim-gate-deferral-placeholder) cover **different topics** and were
the slug-collision source — they are NOT consolidated into this file
and remain individually addressable at their original paths.

---

## 0006 (Hyperparameter-Free Framework Principle)

> **Pointer to canonical:** the canonical content for this decision
> lives at
> **[ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md)**.
> This pointer slot existed only because the Workflow K task brief
> referenced this decision as "ADR-0006"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation
> `0014` because the slot `0006` was already taken by the
> pre-existing ADR [0006-engine-wraps-adapter-pattern.md](0006-engine-wraps-adapter-pattern.md)
> ("Engine-wraps-adapter pattern"). Two ADRs sharing the numeric
> prefix `0006` would violate the convention pinned by
> [ADR-0001](../adr/0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" —
> i.e. unique per ADR). Do not write new content here; update the
> canonical ADR-0014 instead and add a cross-reference back from
> there.

### Context and Problem Statement

The Workflow K task brief on 2026-09-01 asked for three new ADRs
under the slug slots `0006`, `0007`, `0008`. The audit identified
slug collisions and recommended allocating the next free monotonic
prefixes (0014 / 0015 / 0016). The three canonical ADRs were written
at those prefixes with an explicit `## Numbering note` at the bottom
of each, pointing back to the slug-collision source.

This pointer file was the explicit pointer for the `0006` slot so a
reviewer who follows the brief's "ADR-0006" label lands on a file
that explains the situation rather than a duplicate or a 404.

### Decision Drivers

* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique. Two ADRs sharing the prefix
  `0006` would silently break the doc scanner's
  (`tools/check_docs_against_code.py`) numeric-prefix indexing.
* **No silent duplication.** Writing the full ADR text at `0006-`
  while the canonical text lives at `0014-` would force future
  authors to remember to update two locations; this pointer's role
  was to be a pointer, not a second source of truth.
* **Audit trail clarity.** The brief's slug labels and the audit's
  recommended allocations both deserve a documented home. The three
  brief-slot pointers (`0006-`, `0007-`, `0008-`) plus the three
  canonical allocations (`0014-`, `0015-`, `0016-`) form a
  **derive-then-diagnose-then-enforce** chain
  (DERIV-001 -> TheoremAlignedFID -> RegimeAwareEpsSelector) whose
  cross-references are pinned by ADR-0014/0015/0016 directly.

### Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* The canonical text — Context / Decision / Decision Drivers /
  Considered Options / Decision Outcome / Consequences /
  Confirmation / More Information — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md).
* The five derivation rules
  (`PolyakMemoryFraction`, `OTEpsilonSchedule`,
  `BLConvergenceEpsilonSchedule`, `LipschitzStepSize`,
  `FisherMemoryFraction`), the backward-compat invariant, the
  strict-DAG discipline, and the provenance richness are documented
  in full at ADR-0014.

### Consequences

Positive:

* A reviewer who follows the brief's "ADR-0006" label arrives at a
  file that immediately explains the slug collision and points to
  the canonical content. No 404, no silent duplicate.
* The convention pinned by ADR-0001 is preserved — no two ADRs
  share the numeric prefix `0006`.
* The audit's recommendation ("Recommend no further ADR authoring
  in this workflow; the gaps to close are at the implementation
  layer, not the documentation layer") is honoured: the canonical
  ADR-0014 is the only authoritative source of truth.

Negative:

* The pointer was a fourth-level navigation hop. A reviewer who
  only read the pointer file without following the link to ADR-0014
  would see no derivation rules, no decision-outcome content, and
  no more-information section.
* The cross-reference chain spans four files for what was originally
  one brief slot (brief -> pointer -> canonical ADR ->
  cross-referenced docs).

### Confirmation

The decision is enforced by:

* The existence of
  [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md)
  with the full canonical content (Status: accepted, date
  2026-09-01) and an explicit `## Numbering note` section
  pointing back to the slug-collision source.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  (line 1217) cross-references **ADR-0014** (not `ADR-0006`)
  for the Hyperparameter-Free Framework Principle.
* `tools/check_docs_against_code.py` does not flag a duplicate
  prefix because the pointer file's `status: superseded`
  frontmatter marked it as a non-authoritative pointer; the
  canonical prefix indexing reads `status: accepted` ADRs only.

### More Information

* [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md) —
  the canonical Hyperparameter-Free Framework Principle ADR
  (DERIV-001).
* [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID + per-round harness pattern
  ADR (brief slot `0007`).
* [ADR-0016](../adr/0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR (brief slot `0008`).
* [0006-engine-wraps-adapter-pattern.md](0006-engine-wraps-adapter-pattern.md) —
  the pre-existing ADR that owns the `0006` slug slot; the slug
  collision that motivated the pointer file.

---

## 0007 (Theorem-Aligned FID + Per-Round Pattern)

> **Pointer to canonical:** the canonical content for this decision
> lives at
> **[ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md)**.
> This pointer slot existed only because the Workflow K task brief
> referenced this decision as "ADR-0007"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation
> `0015` because the slot `0007` was already taken by the
> pre-existing ADR
> [0007-prev-anchored-bounded-merge.md](0007-prev-anchored-bounded-merge.md)
> ("Prev-anchored bounded merge"). Two ADRs sharing the numeric
> prefix `0007` would violate the convention pinned by
> [ADR-0001](../adr/0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" —
> i.e. unique per ADR).

### Context and Problem Statement

The canonical FID surface (Fréchet distance between two Gaussians fit
to inception-pool3 features) is mathematically equivalent to the
**2-Wasserstein (W₂)** distance on Gaussians, and on Euclidean state
states to the **Bounded-Lipschitz (BL)** distance that is the metric
of paper Theorem 1 (`NoiseSelectedRectification_EN.md`, Proposition
3, lines 115-118). The canonical FID is therefore the right metric
*in principle* — but it did three things wrong from the Theorem-1
standpoint:

1. **No per-round emission.** The legacy
   `InceptionV3FIDEvaluator.compute_from_features` /
   `compute_from_precomputed` API returns a single
   `FIDResult(value, is_finite, feature_dim, n_samples)`. The
   framework's per-round scheduler / blender / merge / materializer
   pipeline produces *one sample distribution per round*; the
   canonical evaluator cannot tell the framework which round's
   trajectory satisfied the Theorem-1 prediction and which did not.
2. **No paper-quantity consumption.** The canonical FID surface
   knows about `(mu, sigma)`, not about `(A_g, B_g, C_g, e_rho)`.
   The four paper quantities are the **audit-trail anchor** for
   Theorem 1 (ADR-0013 §"Paper-quantity naming"); without them on
   the FID result, the empirical trajectory cannot be reconciled
   with the paper Lemma 2 / 3 / 4 / Proposition 3 estimates. The
   `O(eps)` rate Theorem 1 implies — `fid(r) <= C_paper * eps_r`
   with `C_paper = (C_g * B_g + 1 / e_rho) / A_g` — is not checkable
   because the trajectory carries no `eps_r` and no
   `(A_g, B_g, C_g, e_rho)`.
3. **No `O(eps)` convergence assertion.** The canonical surface is a
   distance calculator, not a *diagnostic*. The "framework's per-round
   FID satisfies the Theorem-1 quantitative bound" claim is a
   first-class deliverable of the FID-JMAA workflow, but the legacy
   surface has no place where that assertion lives.

These three gaps are *load-bearing* for the paper's Section 4
("Empirical Verification") narrative
([`docs/r17-survey/algorithm-correctness-evidence.md`](../../r17-survey/algorithm-correctness-evidence.md)
§5). The audit asked: how does the per-round scheduler's BL-distance
trajectory reconcile with Theorem 1's quantitative O(eps) bound? The
honest answer was "we cannot tell" — the canonical FID surface
wasn't designed to.

### Decision Drivers

* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique.
* **No silent duplication.** Writing the full ADR text at `0007-`
  while the canonical text lives at `0015-` would force future
  authors to remember to update two locations; this pointer's role
  was to be a pointer, not a second source of truth.
* **Audit trail clarity.** The three brief-slot pointers plus the
  three canonical allocations form a
  **derive-then-diagnose-then-enforce** chain.
* **Paper-quantity consumption is the audit-trail anchor.**
* **Per-round emission is the framework's primary audit object.**
* **Byte-for-byte back-compat is non-negotiable.** The legacy
  `InceptionV3FIDEvaluator.compute_from_features` /
  `compute_from_precomputed` API must keep returning bit-identical
  `FIDResult` objects.

### Considered Options

1. **Pointer file at the brief's slug slot, forwarding every
   cross-reference to the canonical allocation** (this pointer).
   The canonical content lives at
   [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md).
2. **Write the full ADR text at `0007-` while the canonical text also
   lives at `0015-`.** Rejected: two source-of-truth files drift on
   every correction.
3. **Allocate the ADR at a free monotonic prefix (`0015`) and
   silently drop the brief's `0007` slot.** Rejected: a reviewer
   who follows the brief's "ADR-0007" label lands on a 404; the
   pointer file is the explicit fix.
4. **Allocate the ADR at the brief's `0007` slot and renumber the
   existing `0007-prev-anchored-bounded-merge.md` ADR.** Rejected:
   breaks the doc scanner's references to ADR-0007 throughout the
   codebase.

### Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* The canonical text — TheoremAlignedFID + PerRoundFIDTracker +
  NuGReferenceRegistry + TheoremAlignedFIDReport, the `O(eps)`
  convergence assertion, the Lemma 4 regime diagnosis, the
  byte-stable `NuGReferenceRegistry` cache, the `as_fid_result`
  back-compat projection — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md).

### Consequences

Positive:

* A reviewer who follows the brief's "ADR-0007" label arrives at a
  file that immediately explains the slug collision and points to
  the canonical content.
* The convention pinned by ADR-0001 is preserved.
* The audit's recommendation is honoured.
* The pointer documents the three closed gaps
  (no per-round emission / no paper-quantity consumption / no
  `O(eps)` convergence assertion).

Negative:

* The pointer was a fourth-level navigation hop.
* The cross-reference chain spans four files.
* The pointer file cannot carry `status: accepted` because the
  slug-collision slot cannot be the authoritative home.

### Confirmation

The decision is enforced by:

* The existence of
  [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md)
  with the full canonical content and an explicit `## Numbering
  note` section pointing back to the slug-collision source.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  cross-references **ADR-0015** as the canonical home.

### More Information

* [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID + per-round harness pattern
  ADR.
* [ADR-0016](../adr/0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR (brief slot `0008`).
* [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md) —
  the Hyperparameter-Free Framework Principle (DERIV-001; brief
  slot `0006`); its `paper_quantities` evaluators feed
  `TheoremAlignedFIDResult`'s `(A_g, B_g, C_g, e_rho)` fields.
* [0007-prev-anchored-bounded-merge.md](0007-prev-anchored-bounded-merge.md) —
  the pre-existing ADR that owns the `0007` slug slot.

---

## 0008 (Regime-Aware eps Selector)

> **Pointer to canonical:** the canonical content for this decision
> lives at
> **[ADR-0016](../adr/0016-regime-aware-eps-selector.md)**. This
> pointer slot existed only because the Workflow K task brief
> referenced this decision as "ADR-0008"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation
> `0016` because the slot `0008` was already taken by the
> pre-existing ADR
> [0008-claim-gate-deferral-placeholder.md](0008-claim-gate-deferral-placeholder.md)
> ("Claim-gate deferral placeholder"). Two ADRs sharing the numeric
> prefix `0008` would violate the convention pinned by
> [ADR-0001](../adr/0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" —
> i.e. unique per ADR).

### Context and Problem Statement

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

### Decision Drivers

* **Fail-closed is the load-bearing semantics.** A violation that
  silently flows into the per-round FID trajectory is worse than a
  hard error.
* **Opt-in is non-negotiable.** The 2356+15 test surface runs the
  default `CosineAnnealScheduler` with hand-set `eps_implicit`.
* **The selector wraps an existing trajectory; it does not replace
  it.** The Lemma 4 bound is an *upper-bound* on `eps`, not a
  schedule in its own right.
* **The selector must be stdlib-only.**
* **The Lemma 4 regime check is duplicated, not imported.**
* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique.

### Considered Options

1. **Pointer file at the brief's slug slot, forwarding every
   cross-reference to the canonical allocation** (this pointer).
   The canonical content lives at
   [ADR-0016](../adr/0016-regime-aware-eps-selector.md).
2. **Write the full ADR text at `0008-` while the canonical text
   also lives at `0016-`.** Rejected.
3. **Allocate the ADR at a free monotonic prefix (`0016`) and
   silently drop the brief's `0008` slot.** Rejected.
4. **Allocate the ADR at the brief's `0008` slot and renumber the
   existing `0008-claim-gate-deferral-placeholder.md` ADR.**
   Rejected.

### Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* The canonical text — `RegimeAwareEpsSelector` Protocol +
  `regime_ceiling(eps_r, e_rho, *, slack)` ceiling +
  `regime_holds(eps, e_rho)` predicate + the opt-in flag on
  `EvidenceDrivenScheduler(..., regime_aware=False)`, with two
  concrete selectors (`CosineAnnealRegimeSelector`,
  `ConvergenceAdaptiveRegimeSelector`) wrapping the existing
  scheduler trajectories — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0016](../adr/0016-regime-aware-eps-selector.md).
* The Lemma 4 ceiling
  `regime_ceiling(e_rho, *, slack) -> sqrt(e_rho / log 2) - slack`
  (with `slack = 1e-9` as the strict-inequality slack), the
  `EPS_REGIME_CLAMPED` / `EPS_REGIME_INFEASIBLE` / `EPS_REGIME_OK`
  audit codes, the `e_rho_provider` callback, and the
  `regime_selector_family` / `regime_slack` knobs live in
  `adaptive_reflow/algorithm/scheduler/regime_selector.py`.

### Consequences

Positive:

* A reviewer who follows the brief's "ADR-0008" label arrives at a
  file that immediately explains the slug collision and points to
  the canonical content.
* The convention pinned by ADR-0001 is preserved.
* The audit's recommendation is honoured.
* The pointer documents the five-question decision.

Negative:

* The pointer was a fourth-level navigation hop.
* The cross-reference chain spans four files.
* The pointer file cannot carry `status: accepted` because the
  slug-collision slot cannot be the authoritative home.

### Confirmation

The decision is enforced by:

* The existence of
  [ADR-0016](../adr/0016-regime-aware-eps-selector.md) with the full
  canonical content and an explicit `## Numbering note` section
  pointing back to the slug-collision source.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  cross-references **ADR-0016** as the canonical home.

### More Information

* [ADR-0016](../adr/0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR.
* [ADR-0015](../adr/0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID ADR (brief slot `0007`); its
  `ConvergenceDiagnostic.regime_violations` is the FID-side
  Lemma 4 *diagnosis*.
* [ADR-0014](../adr/0014-hyperparameter-free-framework-principle.md) —
  the Hyperparameter-Free Framework Principle (DERIV-001; brief
  slot `0006`); its `BLConvergenceEpsilonSchedule` derivation
  rule reads `paper_quantities.e_rho` and outputs `eps_threshold`.
* [0008-claim-gate-deferral-placeholder.md](0008-claim-gate-deferral-placeholder.md) —
  the pre-existing ADR that owns the `0008` slug slot.

---

## See also

* [`docs/ARCHIVE/adr/README.md`](README.md) — the ADR archive index
  (lists the pre-existing archived ADRs at slots 0006/0007/0008 which
  cover different topics — engine-wraps-adapter, prev-anchored-bounded-merge,
  claim-gate-deferral-placeholder).
* [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) §10 FAQ — the
  load-bearing FAQ that cross-references the canonical ADRs (0014 /
  0015 / 0016) and previously listed the brief-slot pointers at
  (0006 / 0007 / 0008) as forwarding shims.