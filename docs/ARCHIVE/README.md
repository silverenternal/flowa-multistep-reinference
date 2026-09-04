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
| `UNIVERSAL_CONTRACT_NOTES.md` | superseded | `docs/ARCHITECTURE.md` |
| `UNIVERSAL_MOLECULAR_MAPPING.md` | superseded | `docs/ARCHITECTURE.md` |
| `NoiseSelectedRectification_EN.md` | English extract of a noise-selection derivation; not part of current scope | (no current home) |
| `_benchmark_ablation.md`, `_test_ablation_quick.md` (consolidated into `_ablation_scratch.md`) | ad-hoc ablation scratch (5-round smoke + 20-round canonical runs) | `docs/ABLATION.md` |
| `candidate_registry_init.md` | initial design notes | `adaptive_reflow/writer/registry.py` |
| `paper-plan.md` | pre-`docs/paper-draft.md` planning | `docs/paper-draft.md` |

## `docs/adr/` duplicates

Three ADR numbers had merge collisions producing competing files; the
newer `0014/0015/0016` supersede the older `0006/0007/0008`:

| Archived (old) | Current (new) |
|---|---|
| `0006-engine-wraps-adapter-pattern.md` | `0014-hyperparameter-free-framework-principle.md` |
| `0007-prev-anchored-bounded-merge.md` | `0015-theorem-aligned-fid-per-round-pattern.md` |
| `0008-claim-gate-deferral-placeholder.md` | `0016-regime-aware-eps-selector.md` |

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
