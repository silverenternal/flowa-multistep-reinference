# TODO task inventory (2026-09-13)

This inventory was produced with the `flowa-research-audit` workflow. It is a
read-only audit of every Markdown task surface under `todo/`; no GPU sweep was
rerun and no task was marked complete without implementation evidence.

## Observed state

* `todo/completed/` contains 47 archived plans. Their headers are historical,
  so wording such as `PLANNED` in an archived file does not represent current
  work.
* Active root plans (`adapter-improvement-*`, `algo-improvement-*`) are all
  `PLANNED` and explicitly require user approval in their headers.
* Planned Wave 91 bridge is marked DONE. Wave 92b and Wave 93 Phase 1 are
  recorded as landed in `todo/STATUS.md`; Wave 92c and Wave 93 Phase 2 remain
  in flight. Wave 92d/N=5000 and Wave 94 are gated on those results.
* `todo/inprogress/` contains stale Wave 75–78 cascade documents. The current
  `STATUS.md` says those waves already landed, but moving them is a repository
  mutation and should be done as a separate, reviewable docs commit.
* `todo/push-unpushed-commits.md` says the push is complete, while
  `todo/STATUS.md` reports 327 unpushed commits and a user-gated push. This is a
  documentation contradiction requiring maintainer resolution before push.

## Dependency graph

```text
Wave 92c Kanzi N=1000 ──┬──> Wave 93 Phase 2 power/reframe ──> Wave 94 package
                        └──> Wave 92d N=5000 (optional, user-gated)
```

The four Wave 101 hygiene plans are independent of the long GPU work. Their
lowest-risk order is Layer 4 docs/config P0, Layer 3 test organization P0,
Layer 2/1 source refactors, with D.4 and capability checks after each change.
The six root algorithm/adapter plans depend on design decisions and explicit
approval; they must not be silently activated by an inventory pass.

## Executable checklist

1. Resolve the push-state contradiction and archive stale `todo/inprogress`
   plans (docs-only, maintainer decision required).
2. Execute Wave 101 Layer-4 P0 docs additions; verify `mkdocs build --strict`.
3. Execute Wave 101 Layer-3 P0 test hygiene; compare pytest collection count
   and run D.4 vectors.
4. Complete Wave 92c and Wave 93 Phase 2 using their existing sidecar outputs;
   do not duplicate recorded long-running sweeps.
5. Decide whether to opt into Wave 92d N=5000, then prepare Wave 94 package.
6. Revisit each root `PLANNED (waiting for user approval)` algorithm/adapter
   file only after the corresponding design decision is recorded.

## Evidence

* Files inspected: `todo/STATUS.md`, `todo/INDEX.md`, every non-completed
  `todo/**/*.md`, and repository status.
* Command: `python` header scan over `Path('todo').rglob('*.md')` on
  2026-09-13, from commit `f42de22`.
* GPU work was intentionally not rerun; current recorded gate evidence remains
  the Wave 99.D entries in `todo/STATUS.md`.

