# `todo/` — Task tracker (per-task markdown)

> **Consolidated surface → [`WAVES.md`](WAVES.md).** One increment-free document
> covering current state, phase history, evidence, gates, decisions, lessons,
> risks, and open items. The per-task files below are retained for provenance.

**Date:** 2026-10-12 (repo-docs maintenance refresh)
**Purpose:** Per-task markdown tracker for the **TNNLS** submission work. Lives alongside `todo.json` (machine-readable index) — this folder is for human-readable planning.

## Structure

```
todo/
├── README.md                       (this file)
├── STATUS.md                       (single source of truth — current state + R-level claims + venue decision)
├── INDEX.md                        (master entry point — reading order + cross-references)
├── TPAMI-6-WEEK-PLAN.md            (HISTORICAL — superseded by the TNNLS path)
│
├── GATES.md                        (master gate definitions)
├── LOOP.md                         (per-model lifecycle + iteration + stop conditions)
├── TIMELINE.md                     (phase durations + project-done definition)
├── RISK-REGISTER.md                (forward-looking risks + mitigations R-001..R-022)
├── PUSH-READY.md                   (push-readiness summary, user-gated)
├── decisions.md                    (architecture decisions D-001.., append-only)
└── lessons-learned.md              (lessons LL-001.., append-only)
```

## Current focus (2026-10-12)

**Venue:** IEEE TNNLS (switched from TPAMI). Project at HEAD `8756f19`; **5 commits ahead of `origin/main`** (`fea137d`; the later manuscript-consistency sweeps and governance / repo-docs refreshes are local-only — push is user-gated). Acceptance gates PASS (D.4 30/30 / ruff 0 / claims no-drift / mkdocs strict exit 0). The readiness verifier (`tools/verify_submission_readiness.py`) now passes **all** gates (`READY_WITH_SKIPS: mypy_0`, exit 0 — `mypy_0` SKIPs when mypy is absent from PATH): `k1_rc5` was repointed at the live manuscript and `drift_33`'s allowlist extended on explicit user decision; see `todo/WAVES.md` §1.2.

**Remaining user-gated actions:**
1. Fill the 17 `[USER TO FILL]` placeholders in `tnnls_submission/cover_letter.md` (see `tnnls_submission/FILL_GUIDE.md`).
2. `git push` the 5 local-only commits to `origin/main` (last pushed: `fea137d`, 2026-10-12).

**Latest audit:** [`docs/audit/repo-docs-maintenance.md`](../docs/audit/repo-docs-maintenance.md) — repo-docs maintenance refresh (HEAD `8756f19`; new-management-surface wave-ref cleanup + gate-honesty reconciliation + legacy-artifact inventory). Prior: [`docs/audit/governance-refresh-post-push.md`](../docs/audit/governance-refresh-post-push.md) — post-push governance refresh (HEAD `0209002`).

## Convention

- **One .md file per next-phase task** — not for in-flight work (that's in `todo.json` under `tasks[]`).
- Each file starts with: **status** (`pending` / `in_progress` / `blocked` / `done`), **dependencies**, and **next action**.

## When to add files

Add a new file here when:
- A work phase finishes and uncovers a follow-up task.
- The user gives a new directive that doesn't fit an existing phase.
- The TNNLS submission path branches (e.g., new reviewer concern requires new ablation).

## Archived (preserved for traceability)

15 obsolete task files + 5 stale synthesis docs moved to `/tmp/todo-archive-2026-09-21/`. List available via `ls /tmp/todo-archive-2026-09-21/`.

## See also

- [`docs/CLAIMS.md`](../docs/CLAIMS.md) — 61 active claims ledger
- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit catalogue (topic clusters)
- [`tnnls_submission/SUBMISSION_READINESS.md`](../tnnls_submission/SUBMISSION_READINESS.md) — submission-readiness consolidation
- [`docs/drafts/paper-A-final.md`](../docs/drafts/paper-A-final.md) — canonical paper source
