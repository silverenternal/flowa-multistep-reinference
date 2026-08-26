---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 3. Universal vs molecular split

## Context and Problem Statement

The package carries a `universal/` subpackage that *claims* to be
model-family-agnostic: the `FlowMatchingODEAdapter`,
`RestartMixer`, `EnvelopeCriterion`, and `Evaluator` Protocols are
declared there together with stdlib-only carriers and validators.
Today, however, only the **molecular** implementation
(`adaptive_reflow.molecular`) has been driven end-to-end. There is no
non-molecular adapter in the tree, so the universal/molecular split
is, today, a *promise* rather than a *proven* invariant.

The risk is that the boundary erodes: a molecule-shaped carrier drifts
into `universal/` "just for convenience", and the next non-molecule
adapter author inherits a dependency they did not ask for.

## Decision Drivers

* The `universal/` claim is load-bearing for every future model family
  (latent image FM, discrete CTMC FM, audio FM). The boundary must be
  enforceable, not aspirational.
* The boundary is enforced by a single AST-level guard test
  (`tests/test_universal/test_no_molecular_import.py`). The guard is
  necessary but not sufficient: it would pass even if the universal
  Protocols accidentally required a molecule-shaped carrier.
* The only proof that the universal Protocols are *satisfiable* by a
  non-molecule adapter is a non-molecule adapter that actually exists.

## Considered Options

1. **Keep the universal/molecular split; require a non-molecular
   adapter (ToyGaussianAdapter) as the proof artifact.**
2. **Collapse the split.** Reject `universal/` and put everything in
   `molecular/`. Loses the model-family-agnostic goal.
3. **Keep the split, drop the proof requirement.** Leaves the boundary
   unenforceable in practice; the AST guard alone is too weak.

## Decision Outcome

Chosen option: **Keep the universal/molecular split. The proof
artifact is `ToyGaussianAdapter` (a 1-D Gaussian-parameter adapter
implementing the eight-method `FlowMatchingODEAdapter` Protocol with
zero molecule vocabulary), which lands under
`adaptive_reflow.adapters.toy_gaussian` by 2026-09-22
(see [ROADMAP.md](../../ROADMAP.md) — Now bucket).**

The boundary is enforced by **two** guards, not one:

1. **AST-level import-isolation guard.**
   `tests/test_universal/test_no_molecular_import.py` walks every
   `.py` file under `adaptive_reflow/universal/` and asserts no
   `ast.Import` / `ast.ImportFrom` node targets the
   `adaptive_reflow.molecular` namespace.
2. **Adapter-satisfiability guard.**
   `tests/test_universal/test_adapter_universality.py` constructs a
   synthetic non-molecular adapter in-tree and asserts it satisfies
   the `FlowMatchingODEAdapter` Protocol without importing
   `adaptive_reflow.molecular`.

The first guard prevents accidental leakage; the second guard proves
that the Protocols are satisfiable without molecule vocabulary.

### Consequences

Positive:

* The two-guard combination makes the split provable, not aspirational.
* `ToyGaussianAdapter` doubles as a worked example for new adapter
  authors (mirrors the role `ToyLinearAdapter` already plays).
* Future non-molecule adapters have an existence proof to point to
  when arguing the universal surface is real.

Negative:

* Two guards cost more maintenance than one. The AST guard is a
  `ast` walk; the satisfiability guard is a `Protocol`-conformance
  test. Both are stdlib-only.
* Adding a new universal Protocol now requires a corresponding
  satisfiability test under `tests/test_universal/`. The cost is
  small (~30 lines per Protocol) and is part of the merge bar.

### Confirmation

The decision is confirmed when:

* `ToyGaussianAdapter` is merged under `adaptive_reflow/adapters/`.
* `tests/test_universal/test_adapter_universality.py` (or its
  sibling) covers the Gaussian case explicitly.
* The `ROADMAP.md` Now bucket closes the entry.

## More Information

* [ARCHITECTURE.md §0](../../ARCHITECTURE.md) — the canonical
  universal/molecular narrative.
* [ARCHITECTURE.md §3](../../ARCHITECTURE.md) — the dependency
  direction rules.
* [docs/TESTING_STRATEGY.md §2.1](../TESTING_STRATEGY.md) — the
  universal-test-layer summary.
* [ROADMAP.md](../../ROADMAP.md) — the dated entry for the
  ToyGaussianAdapter closure.