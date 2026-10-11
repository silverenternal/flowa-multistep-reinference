# `todo/INDEX.md` — Master entry point (2026-10-11, post-push governance refresh)

> **Start here → [`WAVES.md`](WAVES.md).** It is the consolidated, increment-free
> management surface: current state, phase history, evidence ledger, gates,
> decisions, lessons, risks, and open items in one place. The files below are
> retained for provenance; `WAVES.md` supersedes them as the primary read.

**Date:** 2026-10-11 (post-push governance refresh — venue is TNNLS; project at HEAD `0209002`)
**Purpose:** curated entry point to the `todo/` working folder. New readers should start with the [Reading order](#reading-order-for-new-readers) section.

> **Historical note.** This file previously described a "TPAMI 6-week path (post-Wave 205)". The venue was switched to **TNNLS** at Wave 238 P3. The TPAMI framing below was superseded; the plan file `TPAMI-6-WEEK-PLAN.md` is retained only as history.

---

## Current execution — TNNLS (post-push governance refresh)

**Venue:** IEEE TNNLS (Transactions on Neural Networks and Learning Systems, CAS 1区 TOP) — switched from TPAMI at Wave 238 P3 (`docs/audit/engineering/wave238-p3-journal-decision.md`). Backups: TIP → PR → Neural Networks → EAAI.

**State:** HEAD `0209002`; **pushed to `origin/main`** (0 ahead; the 192-commit backlog landed 2026-10-11). All acceptance gates PASS (pytest subset green / mypy 0 / ruff 0 / claims no-drift / mkdocs strict exit 0). Manuscript = `docs/drafts/paper-A-final.pdf` (11 pages, SHA `33d3a771…`), title *"FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints"*.

**Entry points:**
- **[STATUS.md](STATUS.md)** — current state + R-level claims + recent waves + venue decision
- **[RISK-REGISTER.md](RISK-REGISTER.md)** — forward-looking risks + mitigations (R-001..R-022)
- **[PUSH-READY.md](PUSH-READY.md)** — push-readiness summary (user-gated)
- **[`docs/audit/wave384-project-audit.md`](../docs/audit/wave384-project-audit.md)** — latest project audit + documentation-drift trail
- **[`tnnls_submission/SUBMISSION_READINESS.md`](../tnnls_submission/SUBMISSION_READINESS.md)** — single-source submission-readiness consolidation (Wave 365)

**Remaining user-gated actions (agent cannot perform):**
1. Fill the **17 `[USER TO FILL]` placeholders** in `tnnls_submission/cover_letter.md` (see `tnnls_submission/FILL_GUIDE.md`).
2. ~~**`git push`** to `origin/main`~~ — **DONE 2026-10-11** (`origin/main` = `0209002`). The remaining push item is the submission tag (see `tnnls_submission/README.md` §3).

---

## Folder layout (2026-10-11 post-push)

The `todo/` root holds 11 files:

- **10 governance docs:** STATUS, INDEX, README, decisions, lessons-learned, GATES, LOOP, TIMELINE, RISK-REGISTER, PUSH-READY
- **1 historical plan file:** TPAMI-6-WEEK-PLAN.md (superseded by the TNNLS path)

---

## Sections

### 1. Active plan

| File | Purpose |
|---|---|
| [STATUS.md](STATUS.md) | **single source of truth** — current state + R-level claims + recent waves + venue decision |

### 2. Operational & governance

| File | Purpose |
|---|---|
| [README.md](README.md) | directory structure + when to add new files + current focus |
| [GATES.md](GATES.md) | master gate definitions (binding rule: every todo/ task must have an acceptance gate) |
| [PUSH-READY.md](PUSH-READY.md) | push-readiness summary (user-gated; reflects current HEAD) |
| [decisions.md](decisions.md) | architecture decision log D-001.. (append-only) |
| [lessons-learned.md](lessons-learned.md) | cross-cutting patterns LL-001.. (append-only) |
| [RISK-REGISTER.md](RISK-REGISTER.md) | forward-looking risks + mitigations (different from `lessons-learned.md`) |
| [LOOP.md](LOOP.md) | per-model lifecycle + iteration mechanism + stop conditions |
| [TIMELINE.md](TIMELINE.md) | phase durations + "project done" definition |

### 3. Archived

15 obsolete task files + 5 stale synthesis docs were moved to `/tmp/todo-archive-2026-09-21/` (preserved for traceability). Pre-Wave-205 task files tied to superseded venues (EAAI/JMLR) are not referenced by the current TNNLS path.

---

## Reading order (for new readers)

1. **[README.md](README.md)** — directory structure + when to add new files + current focus
2. **[STATUS.md](STATUS.md)** — current state + R-level claims + recent waves + venue decision
3. **[`docs/audit/wave384-project-audit.md`](../docs/audit/wave384-project-audit.md)** — latest audit + documentation-drift trail
4. **[`tnnls_submission/SUBMISSION_READINESS.md`](../tnnls_submission/SUBMISSION_READINESS.md)** — submission-readiness consolidation
5. **[`docs/drafts/paper-A-final.md`](../docs/drafts/paper-A-final.md)** — canonical paper source (title + abstract inline)
6. **[`docs/CLAIMS.md`](../docs/CLAIMS.md)** — 61 active claims ledger with provenance
7. **[`docs/audit/INDEX.md`](../docs/audit/INDEX.md)** — per-wave audit catalogue (topic clusters)

After those seven, branch by interest:
- **Statistics rigor:** [`docs/tables/wave203-p4-standardized-stats.md`](../docs/tables/wave203-p4-standardized-stats.md)
- **Mechanism validation:** paper §6 (Lemmas 1–3 + Theorems 4–5)
- **Efficiency / Pareto:** paper §7.7 + `verification_outputs/`
- **Reproducibility:** `reproduce/` + `paper-data/<cell>/REPRODUCIBILITY_RECIPE.md`
- **Decision history:** [decisions.md](decisions.md) → [lessons-learned.md](lessons-learned.md) → [RISK-REGISTER.md](RISK-REGISTER.md)

---

## Cross-references

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — unpushed commits (user-gated)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 61 active claims (CLM-001..CLM-069)
- `docs/audit/INDEX.md` — per-wave audit catalogue (topic clusters)
- `verification_outputs/` — byte-addressable verification artifacts
- `data/` — vendored model checkpoints (FlowMol3 + Kanzi + LineageFlow + CIFAR-10 RF + MNIST FM + FreqFlow)
