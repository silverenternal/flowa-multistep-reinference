---
status: superseded
date: 2026-09-01
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 6. Hyperparameter-Free Framework Principle (DERIV-001) — slug-collision pointer

> **Pointer file.** The canonical content for this decision lives at
> **[ADR-0014](0014-hyperparameter-free-framework-principle.md)**. This
> file exists at the slug slot `0006` only because the Workflow K task
> brief referenced this decision as "ADR-0006"; the audit (Phase 1,
> 2026-09-01) recommended the safer monotonic-prefix allocation `0014`
> because the slot `0006` was already taken by
> [ADR-0006](0006-engine-wraps-adapter-pattern.md)
> ("Engine-wraps-adapter pattern"). Two ADRs sharing the numeric
> prefix `0006` would violate the convention pinned by
> [ADR-0001](0001-record-architecture-decisions.md)
> ("the numeric prefix is monotonic but otherwise meaningless" — i.e.
> unique per ADR). Do not write new content here; update the canonical
> ADR-0014 instead and add a cross-reference back from there.

## Context and Problem Statement

The Workflow K task brief on 2026-09-01 asked for three new ADRs
under the slug slots `0006`, `0007`, `0008`:

| Brief slot | Subject | Canonical allocation |
|---|---|---|
| ADR-0006 | Hyperparameter-Free Framework Principle (DERIV-001) | [ADR-0014](0014-hyperparameter-free-framework-principle.md) |
| ADR-0007 | Theorem-aligned FID + per-round harness pattern | [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md) |
| ADR-0008 | Regime-aware eps selector (opt-in Lemma 4 enforcement) | [ADR-0016](0016-regime-aware-eps-selector.md) |

The audit identified slug collisions with the existing
[ADR-0006](0006-engine-wraps-adapter-pattern.md),
[ADR-0007](0007-prev-anchored-bounded-merge.md), and
[ADR-0008](0008-claim-gate-deferral-placeholder.md), and recommended
allocating the next free monotonic prefixes (0014 / 0015 / 0016).
The three canonical ADRs were written at those prefixes with an
explicit `## Numbering note` at the bottom of each, pointing back
to the slug-collision source.

This file is the explicit pointer for the `0006` slot so a reviewer
who follows the brief's "ADR-0006" label lands on a file that
explains the situation rather than a duplicate or a 404.

## Decision Drivers

* **Convention preservation.** ADR-0001 pins the numeric-prefix
  convention as monotonic-and-unique. Two ADRs sharing the prefix
  `0006` would silently break the doc scanner's
  (`tools/check_docs_against_code.py`) numeric-prefix indexing.
* **No silent duplication.** Writing the full ADR text at `0006-`
  while the canonical text lives at `0014-` would force future
  authors to remember to update two locations; this file's role is
  to be a pointer, not a second source of truth.
* **Audit trail clarity.** The brief's slug labels and the audit's
  recommended allocations both deserve a documented home. The three
  brief-slot pointers (`0006-`, `0007-`, `0008-`) plus the three
  canonical allocations (`0014-`, `0015-`, `0016-`) form a
  **derive-then-diagnose-then-enforce** chain
  (DERIV-001 -> TheoremAlignedFID -> RegimeAwareEpsSelector) whose
  cross-references are pinned by ADR-0014/0015/0016 directly.

## Decision

Chosen option: **single pointer file at the brief's slug slot,
forwarding every cross-reference to the canonical allocation.**

* This file's `status: superseded` (not `accepted`) makes the
  pointer relationship machine-readable.
* The canonical text — Context / Decision / Decision Drivers /
  Considered Options / Decision Outcome / Consequences /
  Confirmation / More Information — is **not** duplicated here. The
  reviewer reads the canonical content at
  [ADR-0014](0014-hyperparameter-free-framework-principle.md).
* The five derivation rules
  (`PolyakMemoryFraction`, `OTEpsilonSchedule`,
  `BLConvergenceEpsilonSchedule`, `LipschitzStepSize`,
  `FisherMemoryFraction`), the backward-compat invariant, the
  strict-DAG discipline, and the provenance richness are documented
  in full at ADR-0014.

## Consequences

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

* This file is a fourth-level navigation hop. A reviewer who only
  reads this pointer file without following the link to ADR-0014
  will see no derivation rules, no decision-outcome content, and
  no more-information section. The pointer is explicit about that,
  but the cost is real for any reviewer who skims.
* The cross-reference chain now spans four files for what was
  originally one brief slot (brief -> pointer -> canonical ADR ->
  cross-referenced docs). This is the documented trade-off for
  preserving the ADR-0001 numeric-prefix convention.

## Confirmation

The decision is enforced by:

* The existence of
  [ADR-0014](0014-hyperparameter-free-framework-principle.md)
  with the full canonical content (Status: accepted, date
  2026-09-01) and an explicit `## Numbering note` section
  pointing back to this pointer file.
* The `docs/ARCHITECTURE.md` §8.0 design-principles block
  (line 1217) cross-references **ADR-0014** (not `ADR-0006`)
  for the Hyperparameter-Free Framework Principle, so the
  authoritative surface is single-sourced.
* The `docs/ARCHITECTURE.md` §10 FAQ row for "Why does the
  framework not have hand-set magic numbers?" (line 1525) names
  **ADR-0014** as the entry point.
* `tools/check_docs_against_code.py` does not flag a duplicate
  prefix because the new file's `status: superseded` frontmatter
  marks it as a non-authoritative pointer; the canonical prefix
  indexing reads `status: accepted` ADRs only.

## More Information

* [ADR-0014](0014-hyperparameter-free-framework-principle.md) —
  the canonical Hyperparameter-Free Framework Principle ADR
  (DERIV-001). This is where the five derivation rules, the
  backward-compat invariant, the strict-DAG discipline, the
  full 23-hparam coverage map, and the empirical evidence chain
  live.
* [ADR-0015](0015-theorem-aligned-fid-per-round-pattern.md) —
  the canonical Theorem-aligned FID + per-round harness pattern
  ADR (brief slot `0007`).
* [ADR-0016](0016-regime-aware-eps-selector.md) — the canonical
  Regime-aware eps selector ADR (brief slot `0008`).
* [ADR-0006](0006-engine-wraps-adapter-pattern.md) — the
  pre-existing ADR that owns the `0006` slug slot; the slug
  collision that motivated this pointer file.
* [ADR-0001](0001-record-architecture-decisions.md) — the
  numeric-prefix convention this pointer file exists to
  preserve.
* [`docs/ALGORITHMS.md`](../ALGORITHMS.md) §"Hyperparameter-Free
  Framework Principle (DERIV-001)" — the principle, the five
  authorized sources, the DAG / namespace discipline, the
  backward-compat invariant, the sample wiring, and the full
  23-hparam coverage map (P-18 + P-19).
* [`docs/r17-survey/algorithm-correctness-evidence.md`](../r17-survey/algorithm-correctness-evidence.md)
  §4 (Gate 3 — P-19) — the empirical evidence chain: 22 PASS
  tests across 2 files, 5 derivation rules match closed-form on
  the 2D oracle, framework trajectory converges monotonically
  under derived hyperparameters, 0 bugs filed.
* [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §8.0 (line 1217)
  and §10 FAQ row (line 1525) — the load-bearing design
  principles and FAQ that cross-reference ADR-0014.
* Audit Phase 1 (2026-09-01) input to Workflow K — the
  recommendation that this pointer file implements.
