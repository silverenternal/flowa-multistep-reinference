---
status: superseded
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 7. Theorem-aligned FID + per-round harness pattern — slug-collision pointer

> **Pointer file.** The canonical content for this decision lives at
> **[ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md)**. This
> file exists at the slug slot `0007` only because the Workflow K task
> brief referenced this decision as "ADR-0007"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation `0015`
> because the slot `0007` was already taken by
> [ADR-0007](0007-prev-anchored-bounded-merge.md)
> ("Prev-anchored bounded merge"). Two ADRs sharing the numeric
> prefix `0007` would violate the convention pinned by
> [ADR-0001](0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" — i.e.
> unique per ADR). Do not write new content here; update the canonical
> ADR-0015 instead and add a cross-reference back from there.

## Context and Problem Statement

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
([`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
§5). The audit asked: how does the per-round scheduler's BL-distance
trajectory reconcile with Theorem 1's quantitative O(eps) bound? The
honest answer was "we cannot tell" — the canonical FID surface
wasn't designed to.

The Workflow K task brief on 2026-09-01 asked for this ADR under
the slug slot `0007`. The audit identified a slug collision with the
existing [ADR-0007](0007-prev-anchored-bounded-merge.md) and
recommended the safer monotonic-prefix allocation `0015`. The canonical
content was written at
[ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md) with an
explicit `## Numbering note` at the bottom, pointing back to this
pointer file.

This file is the explicit pointer for the `0007` slot so a reviewer
who follows the brief's "ADR-0007" label lands on a file that
explains the situation rather than a 404 or a silent duplicate of
the canonical content.

## Decision Drivers

* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique. Two ADRs sharing the prefix
  `0007` would silently break the doc scanner's
  (`tools/check_docs_against_code.py`) numeric-prefix indexing.
* **No silent duplication.** Writing the full ADR text at `0007-`
  while the canonical text lives at `0015-` would force future
  authors to remember to update two locations; this file's role is
  to be a pointer, not a second source of truth.
* **Audit trail clarity.** The brief's slug labels and the audit's
  recommended allocations both deserve a documented home. The three
  brief-slot pointers (`0006-`, `0007-`, `0008-`) plus the three
  canonical allocations (`0014-`, `0015-`, `0016-`) form a
  **derive-then-diagnose-then-enforce** chain
  (DERIV-001 → TheoremAlignedFID → RegimeAwareEpsSelector) whose
  cross-references are pinned by ADR-0014/0015/0016 directly.
* **Paper-quantity consumption is the audit-trail anchor.** ADR-0013
  introduces the four paper quantities `(A_g, B_g, C_g, e_rho)`
  (ADR-0014 routes them through DERIV-001 derivation rules).
  TheoremAlignedFID must consume them too — the audit reader asking
  "does this run's per-round trajectory match the O(eps) prediction?"
  needs them on every per-round result.
* **Per-round emission is the framework's primary audit object.**
  The canonical per-round FID trajectory is the load-bearing claim
  for the paper's empirical-verification narrative.
* **Byte-for-byte back-compat is non-negotiable.** The legacy
  `InceptionV3FIDEvaluator.compute_from_features` /
  `compute_from_precomputed` API must keep returning bit-identical
  `FIDResult` objects. TheoremAlignedFID is a *sibling* module that
  delegates the Fréchet arithmetic to the legacy module; legacy
  callers see no change.

## Considered Options

1. **Pointer file at the brief's slug slot, forwarding every
   cross-reference to the canonical allocation** (this file). The
   canonical content lives at
   [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md).
2. **Write the full ADR text at `0007-` while the canonical text also
   lives at `0015-`.** Rejected: two source-of-truth files drift on
   every correction, and the doc scanner cannot distinguish which is
   the authoritative surface.
3. **Allocate the ADR at a free monotonic prefix (`0015`) and
   silently drop the brief's `0007` slot.** Rejected: a reviewer
   who follows the brief's "ADR-0007" label lands on a 404; the
   pointer file is the explicit fix.
4. **Allocate the ADR at the brief's `0007` slot and renumber the
   existing `0007-prev-anchored-bounded-merge.md` ADR.** Rejected:
   breaks the doc scanner's references to ADR-0007 throughout the
   codebase (ARCHITECTURE.md, todo.json, ADR cross-references). The
   audit recommended the cheaper fix: leave the existing 0007 in
   place and forward `0007` to `0015`.

## Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* This file's `status: superseded` (not `accepted`) makes the
  pointer relationship machine-readable.
* The canonical text — TheoremAlignedFID + PerRoundFIDTracker +
  NuGReferenceRegistry + TheoremAlignedFIDReport, the `O(eps)`
  convergence assertion (`fid(r) <= C_paper * eps_r` with
  `C_paper = (C_g * B_g + 1 / e_rho) / A_g`), the Lemma 4 regime
  diagnosis (`regime_check_ok` / `regime_violations`), the
  byte-stable `NuGReferenceRegistry` cache, the `as_fid_result`
  back-compat projection — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md).
* The four artefacts (`PaperQuantitiesSnapshot`,
  `TheoremAlignedFIDResult`, `FIDPerRoundResult`,
  `ConvergenceDiagnostic`, `TheoremAlignedFIDReport`,
  `NuGReferenceRegistry`, `InceptionV3TheoremAlignedFIDEvaluator`,
  `PerRoundFIDTracker`) and the `REGIME_VIOLATION_AUDIT_CODE`
  constant live in
  [`adaptive_reflow/eval/fid_theorem_aligned.py`](../adaptive_reflow/eval/fid_theorem_aligned.py).

## Consequences

Positive:

* A reviewer who follows the brief's "ADR-0007" label arrives at a
  file that immediately explains the slug collision and points to
  the canonical content. No 404, no silent duplicate.
* The convention pinned by ADR-0001 is preserved — no two ADRs
  share the numeric prefix `0007`.
* The audit's recommendation ("Recommend no further ADR authoring
  in this workflow; the gaps to close are at the implementation
  layer, not the documentation layer") is honoured: the canonical
  ADR-0015 is the only authoritative source of truth.
* The pointer file documents the three closed gaps
  (no per-round emission / no paper-quantity consumption / no
  `O(eps)` convergence assertion) and the canonical artefacts that
  close them, so a reviewer skimming only the pointer still gets
  the architectural gist.

Negative:

* This file is a fourth-level navigation hop. A reviewer who only
  reads this pointer file without following the link to ADR-0015
  will see no per-round emission contract, no regime-check detail,
  no `as_fid_result` back-compat projection, and no
  TheoremAlignedFIDReport example. The pointer is explicit about
  that, but the cost is real for any reviewer who skims.
* The cross-reference chain now spans four files for what was
  originally one brief slot (brief → pointer → canonical ADR →
  cross-referenced docs). This is the documented trade-off for
  preserving the ADR-0001 numeric-prefix convention.
* The pointer file cannot carry `status: accepted` because the
  slug-collision slot cannot be the authoritative home; a reader
  who grep-searches `status: accepted` for `ADR-0007` will not
  find this pointer.

## Confirmation

The decision is enforced by:

* The existence of
  [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md)
  with the full canonical content (Status: accepted, date
  2026-09-01) and an explicit `## Numbering note` section
  pointing back to this pointer file.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  (Theorem-aligned FID + per-round harness pattern bullet)
  cross-references **ADR-0015** (not `ADR-0007`) as the canonical
  home, so the authoritative surface is single-sourced.
* The `docs/ARCHITECTURE.md` §10 FAQ row for "Why does FID
  consume `(A_g, B_g, C_g, e_rho)` per round, not just `value`?"
  names **ADR-0015** as the entry point.
* `tools/check_docs_against_code.py` does not flag a duplicate
  prefix because the new file's `status: superseded` frontmatter
  marks it as a non-authoritative pointer; the canonical prefix
  indexing reads `status: accepted` ADRs only.

## More Information

* [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID + per-round harness pattern
  ADR. This is where the eight artefacts
  (`PaperQuantitiesSnapshot`, `TheoremAlignedFIDResult`,
  `FIDPerRoundResult`, `ConvergenceDiagnostic`,
  `TheoremAlignedFIDReport`, `NuGReferenceRegistry`,
  `InceptionV3TheoremAlignedFIDEvaluator`, `PerRoundFIDTracker`),
  the `O(eps)` convergence assertion, the Lemma 4 regime
  diagnosis, the per-round harness wiring
  (`tools/run_image_eval.py --per-round`,
  `tools/run_sota_lumina_image_2_0_experiment.py::_make_per_round_callback`,
  `tools/run_sota_hidream_i1_experiment.py`), and the byte-stable
  `as_fid_result` back-compat projection live.
* [ADR-0016](0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR (brief slot `0008`); consumes the
  same `e_rho` paper quantity and provides the scheduler-side
  Lemma 4 *enforcement* that complements ADR-0015's FID-side
  *diagnosis*.
* [ADR-0014](0014-hyperparameter-free-framework-principle.md) —
  the Hyperparameter-Free Framework Principle (DERIV-001; brief
  slot `0006`); its `paper_quantities` evaluators feed
  `TheoremAlignedFIDResult`'s `(A_g, B_g, C_g, e_rho)` fields.
* [ADR-0013](0013-posterior-selection-drives-algorithm.md) —
  the paper-quantity naming `(A_g, B_g, C_g, e_rho)` and the
  theorem-driven scheduler justification that ADR-0015 consumes
  as audit-trail anchors.
* [ADR-0007](0007-prev-anchored-bounded-merge.md) — the
  pre-existing ADR that owns the `0007` slug slot; the slug
  collision that motivated this pointer file.
* [ADR-0001](0001-record-architecture-decisions.md) — the
  numeric-prefix convention this pointer file exists to
  preserve.
* [`docs/lean/THEOREM_1_MAPPING.md`](../lean/THEOREM_1_MAPPING.md)
  §B.3 (Exterior exponential bound, paper Lemma 4, line 110-113) —
  the formal verification of Lemma 4 and the `e_rho` quantity
  ADR-0015's regime check consumes.
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §5 — the FID-JMAA workflow + Phase 4 verdict (the
  TheoremAlignedFID surface, the per-round harness wiring status,
  the regime-enforcement diagnostic-only status).
* [`docs/r17-survey/fm-lcm-interface-gap-audit.md`](../r17-survey/fm-lcm-interface-gap-audit.md)
  §8 rows 156-157 — the per-round harness wiring status
  (`per-round-wired-partial`) and the Phase-4 scheduler `e_rho`
  regime enforcement status (diagnostic-only).
* `NoiseSelectedRectification_EN.md` Proposition 3 (line 115-118) —
  the paper's BL → KL monotonicity result that ADR-0015's
  `ConvergenceDiagnostic.monotone` checks per round.
* `NoiseSelectedRectification_EN.md` Lemma 4 (line 110-113) — the
  paper's exterior exponential bound whose `o(eps)` step is the
  Lemma 4 regime `eps^2 < e_rho / log 2` ADR-0015's regime check
  surfaces and ADR-0016's regime selector enforces.
* `adaptive_reflow/eval/fid_theorem_aligned.py` — the canonical
  TheoremAlignedFID module + the eight artefacts plus the
  `REGIME_VIOLATION_AUDIT_CODE` constant.
* `tests/test_eval/test_fid_theorem_aligned.py` — the 15-test
  regression surface (snapshot byte-stability, per-round emission,
  `O(eps)` convergence assertion, regime check, registry cache
  stability, legacy back-compat via `as_fid_result`).
* Audit Phase 1 (2026-09-01) input to Workflow K — the
  recommendation that this pointer file implements.