# `todo/` — Task tracker (per-task markdown)

**Date:** 2026-09-21 (post-Wave 205 refactor)
**Purpose:** Per-task markdown tracker for the TPAMI submission data-preparation work. Lives alongside `todo.json` (machine-readable index) — this folder is for human-readable planning.

## Structure (post-Wave 205)

```
todo/
├── README.md                       (this file)
├── STATUS.md                       (single source of truth — current state + R-level claims + venue decision)
├── INDEX.md                        (master entry point — reading order + cross-references)
├── TPAMI-6-WEEK-PLAN.md            (NEW — 6-week TPAMI data-prep schedule W1-W6)
│
├── GATES.md                        (master gate definitions)
├── LOOP.md                         (per-model lifecycle + iteration + stop conditions)
├── TIMELINE.md                     (phase durations + project-done definition)
├── RISK-REGISTER.md                (forward-looking risks + mitigations)
├── PUSH-READY.md                   (push-readiness summary, user-gated)
├── decisions.md                    (architecture decisions D-001.., append-only)
└── lessons-learned.md              (lessons LL-001.., append-only)
```

## Current focus (per user directive 2026-09-21)

> "基于刚才的总结，之前 todo 目录里的所有任务都可以删除，直接写新的任务安排计划"

Switched from EAAI/JMLR to **TPAMI**. The 6-week data-prep plan is in [TPAMI-6-WEEK-PLAN.md](TPAMI-6-WEEK-PLAN.md).

**W1 ✅ DONE** (Wave 203-205: stats audit + 2 p-value bug fixes + TPAMI checklist)
**W2 starts next** (Wave 206: N=1000 paired-record re-runs on omegafold_py310)

## Convention

- **One .md file per next-phase task** — not for in-flight work (that's in `todo.json` under `tasks[]`).
- Each file starts with: **status** (`pending` / `in_progress` / `blocked` / `done`), **dependencies**, and **next action**.
- TPAMI plan file uses W1-W6 phases per Wave 206-210.

## When to add files

Add a new file here when:
- A wave finishes and uncovers a follow-up task.
- The user gives a new directive that doesn't fit an existing wave.
- The TPAMI submission path branches (e.g., new reviewer concern requires new ablation).

## Archived (preserved for traceability until 2026-10-21)

15 obsolete task files + 5 stale synthesis docs moved to `/tmp/todo-archive-2026-09-21/`. List available via `ls /tmp/todo-archive-2026-09-21/`.

## Detailed atomic subtasks

For all W2-W6 work broken into atomic subtasks (~30 min each), see [TPAMI-6-WEEK-PLAN.md](TPAMI-6-WEEK-PLAN.md) §W2-W6. Use this when scheduling work — each subtask has time estimate + dependencies + acceptance criteria.

## See also

- [`docs/tpami_submission_checklist.md`](../docs/tpami_submission_checklist.md) — 6-section TPAMI checklist
- [`docs/paper-draft.md`](../docs/paper-draft.md) — main paper draft
- [`docs/CLAIMS.md`](../docs/CLAIMS.md) — 55+ active claims ledger
- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit catalogue