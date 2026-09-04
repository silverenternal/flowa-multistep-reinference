# Documentation Archive

This directory contains historical documents that have been superseded
by current docs at the repo root and under `docs/`. Files here are
**preserved for context and** **not actively maintained**. They are
excluded from the mkdocs site build.

## Top-level governance planning notes

Historical planning / migration documents from before the post-refactor
layout landed. The current governance is at:

- `ARCHITECTURE.md` (repo root, deleted) was the planned location;
  the canonical doc now lives at `docs/ARCHITECTURE.md`.
- The Phase-4 status update that was in the deleted `ARCHITECTURE.md`
  has been merged into `docs/ARCHITECTURE.md` (search for
  "Phase-4 status update").
- `STATUS.md` (deleted) was a stale snapshot; `CHANGELOG.md` is the
  authoritative status record.

| File | Status before archive | Where to find the current state |
|---|---|---|
| `ARCHITECTURE_PLAN.md` | superseded | `docs/ARCHITECTURE.md` |
| `FILE_MAPPING.md` | superseded | `docs/ARCHITECTURE.md` §2 |
| `REFACTOR_PLAN_V2.md` | superseded | `docs/ARCHITECTURE.md` |
| `SPLIT_NOTES.md` | superseded | `docs/ARCHITECTURE.md` |
| `FINAL_STATUS.md` | stale snapshot | `CHANGELOG.md` |
| `UNIVERSAL_CONTRACT_NOTES.md` (now `REFACTOR_PLAN_V2.md` Appendix A) | superseded | `docs/ARCHITECTURE.md` |
| `UNIVERSAL_MOLECULAR_MAPPING.md` (now `REFACTOR_PLAN_V2.md` Appendix B) | superseded | `docs/ARCHITECTURE.md` |
| `NoiseSelectedRectification_EN.md` | This file IS the paper (Li 2026). It is the only copy in the repo — the LaTeX source tree `docs/formal_architecture_lean4/.../main.tex` does not exist. Cited by line number from 4 production modules (`adaptive_reflow/theory/paper_quantities.py`, `algorithm/categorical_blender.py`, `algorithm/merge_operator.py:569`, `algorithm/scheduler/_core.py:2177`) and from 15+ live docs (`paper-draft.md`, `CLAIMS.md`, `INSIGHTS.md`, `docs/lean/*`, `docs/adr/0015/0016`, `docs/audit/EPSILON_DIRECTION.md`, `DESIGN_BOUNDARY.md`). Lines 87-92 contain Theorem 1 exactly as cited. Note: line 34 embeds `<img src=figures/fibre_selection.svg>`; no `.svg` exists — broken image. Full file move deferred (Wave 16 `do_not_execute` D1). | cited by line number from production code and 15+ live docs |
| `_benchmark_ablation.md`, `_test_ablation_quick.md` (consolidated into `_ablation_scratch.md`) | ad-hoc ablation scratch (5-round smoke + 20-round canonical runs) | `docs/ABLATION.md` |
| `candidate_registry_init.md` | initial design notes | `adaptive_reflow/writer/registry.py` |
| `paper-plan.md` | pre-`docs/paper-draft.md` planning | `docs/paper-draft.md` |

## `docs/adr/` duplicates and slug collisions

Two distinct things live at the `0006/0007/0008` numbers in `docs/adr/`-
adjacent paths. They are **different topics** and were consolidated in
Wave 16 B1:

1. **Original archived ADRs** (different topics, different decisions,
   unchanged):

   | Archived (original) | Topic |
   |---|---|
   | `0006-engine-wraps-adapter-pattern.md` | Engine-wraps-Adapter pattern (2026-08-27, accepted) |
   | `0007-prev-anchored-bounded-merge.md` | prev-anchored bounded_merge (2026-08-27, superseded) |
   | `0008-claim-gate-deferral-placeholder.md` | claim-gate deferral placeholder (2026-08-27, superseded) |

2. **Slug-collision shims** that briefly lived at
   `docs/adr/0006/0007/0008` before being moved to higher numbers —
   consolidated into one archived entry in Wave 16 B1:

   | Archived (consolidated entry) | Current (canonical) |
   |---|---|
   | `0006-superseded-slug-collision-pointers.md` (## 0006 subsection) | `0014-hyperparameter-free-framework-principle.md` |
   | `0006-superseded-slug-collision-pointers.md` (## 0007 subsection) | `0015-theorem-aligned-fid-per-round-pattern.md` |
   | `0006-superseded-slug-collision-pointers.md` (## 0008 subsection) | `0016-regime-aware-eps-selector.md` |

The slug collision arose because Workflow K brief asked for ADRs at
slots `0006/0007/0008` but those numbers were already taken by the
original three ADRs above. The shims were a temporary mitigation; B1
collected all three into a single archive entry and the canonical
`0014/0015/0016` remain the live entry points.

## `docs/r3-survey/` (the r3 survey)

The r3 frontier decoupling survey was superseded by r4-survey and
r17-survey; the r4/r5/r17 surveys are the current ones.

| File | Status before archive | Current home |
|---|---|---|
| `01-architecture.md` through `09-c4-investigation.md` | superseded | `docs/r4-survey/`, `docs/r5-survey/`, `docs/r17-survey/` |

## Algorithm uplift planning notes

| File | Status before archive | Current home |
|---|---|---|
| `algorithm-uplift-plan.md`, `algorithm-deep-uplift-plan.md`, `algorithm-round2-uplift-plan.md` (consolidated into `algorithm-uplift-plans.md`) | pre-implementation planning for the 3 algorithm rounds | `ROADMAP.md`, `CHANGELOG.md`, `docs/r17-survey/` |

## `tools/mutate/WINDOWS_LIMITATION.md`

Windows-specific mutation test limitation, superseded by the
`tools/mutate/ast_mutator.py` AST-based mutation harness (cross-platform).
The mutation score thresholds documented there have been migrated into
`ARCHITECTURE.md` §11 mutation gate.
