# `todo/` — Task tracker (per-task markdown)

> **Consolidated surface → [`WAVES.md`](WAVES.md).** One increment-free document
> covering current state, phase history, evidence, gates, decisions, lessons,
> risks, and open items. The per-task files below are retained for provenance.

**Date:** 2026-10-11 (post-Wave 384 documentation refresh)
**Purpose:** Per-task markdown tracker for the **TNNLS** submission work. Lives alongside `todo.json` (machine-readable index) — this folder is for human-readable planning.

## Structure (post-Wave 384)

```
todo/
├── README.md                       (this file)
├── STATUS.md                       (single source of truth — current state + R-level claims + venue decision)
├── INDEX.md                        (master entry point — reading order + cross-references)
├── TPAMI-6-WEEK-PLAN.md            (HISTORICAL — superseded by the TNNLS path at Wave 238 P3)
│
├── GATES.md                        (master gate definitions)
├── LOOP.md                         (per-model lifecycle + iteration + stop conditions)
├── TIMELINE.md                     (phase durations + project-done definition)
├── RISK-REGISTER.md                (forward-looking risks + mitigations R-001..R-022)
├── PUSH-READY.md                   (push-readiness summary, user-gated)
├── decisions.md                    (architecture decisions D-001.., append-only)
└── lessons-learned.md              (lessons LL-001.., append-only)
```

## Current focus (2026-10-11)

**Venue:** IEEE TNNLS (switched from TPAMI at Wave 238 P3). Project at HEAD `061682c` (≈ Wave 383); 188 commits ahead of `origin/main` (user-gated NO-PUSH). All acceptance gates PASS.

**Remaining user-gated actions:**
1. Fill the 17 `[USER TO FILL]` placeholders in `tnnls_submission/cover_letter.md` (see `tnnls_submission/FILL_GUIDE.md`).
2. `git push` to `origin/main`.

**Latest audit:** [`docs/audit/wave384-project-audit.md`](../docs/audit/wave384-project-audit.md) — gates GREEN; documentation-drift D1–D8 documented and refreshed; paper internal cross-reference defects P1–P5 flagged.

## Convention

- **One .md file per next-phase task** — not for in-flight work (that's in `todo.json` under `tasks[]`).
- Each file starts with: **status** (`pending` / `in_progress` / `blocked` / `done`), **dependencies**, and **next action**.

## When to add files

Add a new file here when:
- A wave finishes and uncovers a follow-up task.
- The user gives a new directive that doesn't fit an existing wave.
- The TNNLS submission path branches (e.g., new reviewer concern requires new ablation).

## Archived (preserved for traceability)

15 obsolete task files + 5 stale synthesis docs moved to `/tmp/todo-archive-2026-09-21/`. List available via `ls /tmp/todo-archive-2026-09-21/`.

## See also

- [`docs/CLAIMS.md`](../docs/CLAIMS.md) — 61 active claims ledger
- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit catalogue (topic clusters)
- [`tnnls_submission/SUBMISSION_READINESS.md`](../tnnls_submission/SUBMISSION_READINESS.md) — submission-readiness consolidation
- [`docs/drafts/paper-A-final.md`](../docs/drafts/paper-A-final.md) — canonical paper source
