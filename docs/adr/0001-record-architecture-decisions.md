---
status: accepted
date: 2026-08-27
deciders: flowa-maintainer
consulted: N/A
informed: N/A
---

# 1. Record architecture decisions

## Context and Problem Statement

`flowa-multistep-reinference` is a typed-contracts framework whose
correctness *is* the contract layer. As the surface grows beyond ~30
public modules and 800+ verified doc claims, the boundary decisions
that hold the package together (the contracts / universal split, the
universal / molecular split, the engine operation order, the audit-code
policy) need a permanent, dated, reviewable home that is not a chat log
and not the README.

We need a place to record:

* Why each load-bearing boundary was drawn where it was.
* What alternatives were considered and rejected.
* What the consequences (positive and negative) of each decision are.

## Decision Drivers

* The project is a single-maintainer research project. The ADR author
  and reviewer are the same person, but the decisions themselves still
  need to survive memory and to be greppable from the codebase.
* The decisions are **load-bearing**: they are enforced by the test
  suite (AST guards, mutation score targets, hostile-case fixtures)
  and a future maintainer must be able to recover the reasoning.
* The format must be lightweight enough that an ADR is cheaper to write
  than to skip, and structured enough that an automated tool could
  index them.

## Considered Options

1. **Markdown Architecture Decision Records (MADR) 4.0** — lightweight,
   frontmatter-driven, single-file-per-decision, no central index
   file required.
2. **nygard format** (`# Title`, `## Status`, `## Context`, …) — even
   lighter, but the frontmatter convention makes automated indexing
   easier.
3. **Free-form `docs/decisions/*.md` with no template** — least
   friction, but no consistency means future ADRs will drift.

## Decision Outcome

Chosen option: **MADR 4.0**, because the frontmatter gives us a
greppable machine-readable summary and the in-body sections are short
enough to write under 50 lines per decision. This file is itself an
example of the format; every subsequent ADR follows the same template.

The ADRs live under `docs/adr/`, one file per decision, with a numeric
prefix `NNNN-kebab-case-slug.md`. The numeric prefix is monotonic but
otherwise meaningless; the slug is the searchable identifier. There is
no central index file — the `docs/adr/` directory listing is the index.

### Consequences

Positive:

* Every load-bearing boundary has a single-file, greppable history.
* The doc scanner (`tools/check_docs_against_code.py`) can index ADR
  filenames as part of the catalogue.
* A new ADR is ~50 lines; writing one is cheaper than skipping one.

Negative:

* Two formats may coexist in the wild (MADR 4.0 + nygard-style ADRs in
  the literature). We mitigate by *using* MADR 4.0 for every ADR we
  author ourselves.
* The single-maintainer role means an ADR is not externally reviewed.
  We mitigate by writing the **Consequences** section honestly, including
  the negatives.

### Confirmation

The decision is confirmed by the existence of `docs/adr/0001` and
`docs/adr/0002` through `docs/adr/0005`. Each future load-bearing
decision follows the same template; if a future ADR diverges, that
divergence itself requires a meta-ADR.

## Pros and Cons of the Options

### MADR 4.0

* Good, because the frontmatter is greppable.
* Good, because the body is short.
* Bad, because the frontmatter is a small additional cost.

### nygard format

* Good, because every developer already knows it.
* Bad, because the format drifts quickly without frontmatter anchors.

### Free-form

* Good, because the cost-per-ADR is lowest.
* Bad, because consistency degrades with time.

## More Information

* [docs/adr/0002](0002-typed-contracts-core-boundary.md) — the first
  substantive decision after this meta-ADR.
* [docs/TESTING_STRATEGY.md](../TESTING_STRATEGY.md) §2.7 — the
  doc-drift scanner that consumes the ADR filenames.
* MADR 4.0 template reference: <https://adr.github.io/madr/>