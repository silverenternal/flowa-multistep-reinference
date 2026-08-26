---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 2. Typed contracts as the core boundary

## Context and Problem Statement

The `adaptive_reflow/` package was reorganized (DTB-UMC, completed
2026-08-25) into twelve peer subpackages, each owning one concern. One
of those subpackages, `contracts/`, holds every frozen dataclass,
`NewType`, hash helper, and validator that the rest of the package
depends on. The split into **eleven files** under `contracts/` mirrors
the eight DTB sections (DTB-R0/R1/R2/R4/R5/NC1/NC2/NA1/L1/L2/S1).

The question this ADR answers: **where is the canonical contract
surface, and what is the import direction?**

Today the layout is:

```
adaptive_reflow/contracts/        # 11 files: archive, authority, bundle,
                                  # decision, envelope, hashes, operations,
                                  # phase, schedule, types, validators
adaptive_reflow/universal/        # imports from contracts
adaptive_reflow/molecular/        # imports from contracts
adaptive_reflow/frame/            # imports from contracts
adaptive_reflow/{policy,schedule,envelope,diagnostics,writer,adapters,eval}
                                  # all import from contracts
```

`contracts/` is the leaf of the package DAG.

## Decision Drivers

* Stdlib-only is a project invariant: `contracts/` cannot import
  `torch`, `numpy`, or any third-party module, and cannot perform
  I/O. Splitting contracts into per-concern files preserves that
  invariant and makes the surface audit-friendly.
* The other subpackages need *one* canonical surface to import from,
  not eleven. The `contracts/__init__.py` curated re-export layer
  serves as that single surface.
* The reverse direction — `contracts/` importing from `molecular/` or
  `universal/` — would create a cycle and would force the leaf to
  carry molecule-shaped or universal-shaped knowledge.

## Considered Options

1. **Keep `contracts/` as the canonical surface; molecular and universal
   may import from it; reverse direction forbidden.**
2. **Promote `universal/` to the leaf.** Both molecular and contracts
   import from universal. Rejected because `universal/` carries
   Protocols and carriers, not the pure-data contracts; it is a
   *higher* abstraction, not a *lower* one.
3. **No leaf at all; allow mutual imports.** Rejected because it
   breaks the DAG and complicates `mypy --strict` validation.

## Decision Outcome

Chosen option: **`adaptive_reflow/contracts/` is the canonical typed
contract surface. `molecular/`, `universal/`, `frame/`, `policy/`,
`schedule/`, `envelope/`, `diagnostics/`, `writer/`, `adapters/`, and
`eval/` may import from `contracts/`. The reverse direction is
forbidden.**

The `contracts/` package is stdlib-only: no `torch`, no I/O, no other
`adaptive_reflow.*` imports. It is the only subpackage where
`mypy --strict` is run as a release gate.

### Consequences

Positive:

* A single, well-defined leaf makes the package DAG easy to draw and
  easy to enforce (see `ARCHITECTURE.md` §3).
* Every cross-subpackage dataclass crossing has exactly one canonical
  path: through `contracts/`.
* The eleven-file split under `contracts/` mirrors the eight DTB
  sections so a researcher looking for the carrier type that backs
  DTB-R1 (`RoundResultBundle`) goes to `contracts/bundle.py`.

Negative:

* A new contract must be added in two places: the per-DTB file
  (`contracts/<section>.py`) and the curated re-export layer
  (`contracts/__init__.py`). The doc scanner enforces the second
  step; CI fails on drift.
* Some contracts need to import sibling contracts for typing (e.g.
  `RoundResultBundle` referencing `PhaseState`). The per-file
  `from __future__ import annotations` + lazy `__getattr__` shim
  pattern keeps this working without breaking the leaf invariant;
  the cost is four documented `mypy --strict` errors in
  `molecular/__init__.py` (see `FINAL_STATUS.md` §4).

### Confirmation

The decision is enforced by:

* The package's own import graph (the `mypy --strict` gate on
  `contracts/` and `universal/`).
* The doc scanner (`tools/check_docs_against_code.py`) — every
  re-export in `contracts/__init__.py` must resolve to a real symbol.
* The unit tests under `tests/test_contracts/`.

## More Information

* [ARCHITECTURE.md §3](../../ARCHITECTURE.md) — the full dependency
  direction rules.
* [ARCHITECTURE.md §4.1](../../ARCHITECTURE.md) — the canonical
  re-export surface of `contracts/`.
* [docs/adr/0003](0003-universal-vs-molecular-split.md) — the next
  decision down the DAG.
* [FINAL_STATUS.md §4](../../FINAL_STATUS.md) — the documented
  `mypy --strict` noise in the molecular re-export shim.