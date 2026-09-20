# `todo/INDEX.md` — Master entry point (2026-09-21 post-Wave 205)

**Date:** 2026-09-21 (post-Wave 205 — TPAMI checklist; todo/ refactored from 30 files → 11 files)
**Purpose:** curated entry point to the `todo/` working folder. New readers should start with the [Reading order](#reading-order-for-new-readers) section.

---

## Current execution — TPAMI 6-week path (post-Wave 205)

**Strategy:** Switch from EAAI/JMLR to **TPAMI (IEEE Trans on Pattern Analysis and Machine Intelligence)** after DeepSeek audit + Wave 203/204 statistics standardization (12-col stats table, cluster-robust, 2 p-value bug fixes).

**Entry points:**
- **[STATUS.md](STATUS.md)** — current state + last completed wave + next actions
- **[TPAMI-6-WEEK-PLAN.md](TPAMI-6-WEEK-PLAN.md)** — full 6-week data-prep schedule (W1-W6)
- **[`docs/tpami_submission_checklist.md`](../docs/tpami_submission_checklist.md)** — 6-section TPAMI checklist (core perf + mechanism + efficiency + stats + reproducibility + limitations)

**Waves 198-205 status:**

| Wave | Outcome | Status |
|---|---|---|
| 198 | Per-record + strata analysis found cancellation root cause (NOT effect-size bound) | ✅ DONE |
| 199-200 | LineageFlow N=1000 sweep BLOCKED-ON-DATA (CPU >40h/arm, torch 1.13.1 vs Blackwell sm_120) | ⛔ BLOCKED |
| 201 | Eval pipeline 2-3× speedup via --workers-per-gpu + LPT + auto-detect | ✅ DONE |
| 202 | Found omegafold_py310 conda env (torch 2.14.0+cu130 + sm_120 supported) | ✅ DONE |
| 203 | Statistics audit fix: 2 p-value bugs + cluster-robust + 12-col stats table + CLM-066/067 | ✅ DONE |
| 204 | Wave 196 vanilla scPerplexity defensive sf() fix; commit `72ba46e` | ✅ DONE |
| 205 | TPAMI submission data-preparation checklist | ✅ DONE |

**Waves 206-210 (TPAMI 6-week plan):**

| Wave | Goal | Status |
|---|---|---|
| **206** | W2 — N=1000 paired-record re-runs on omegafold_py310 (LineageFlow, Kanzi, FlowMol3, 2D, CIFAR, MNIST, FreqFlow, CIFAR honest-negative curve) | 🟢 NEXT |
| 207 | W3 — Ablation + control experiments (5-arm A0-A4, fixed-threshold, random/uniform, single-scheduler, cosine-ramp) | QUEUED |
| 208 | W4 — Efficiency + Pareto frontier (wall-clock, memory, NFE accounting, Pareto NFE {10...1000}, 2.5-10× speedup CI) | QUEUED |
| 209 | W5 — Statistical depth (12-col stats refresh, Bonferroni families, cluster-robust replication, FDR-BH, bootstrap CI) | QUEUED |
| 210 | W6 — Reproducibility + submission (GitHub, Zenodo, Docker, docs refresh, honest negatives, tag v3.0-tpami-submission + push) | QUEUED |

**W1 ✅ DONE** — see `STATUS.md` §"Recent waves" + `docs/tpami_submission_checklist.md` §1 for completion evidence.

---

## Folder layout (2026-09-21 post-Wave 205)

The `todo/` root holds 11 files:

- **10 governance docs** (kept from pre-Wave-205 layout): STATUS, INDEX, README, decisions, lessons-learned, GATES, LOOP, TIMELINE, RISK-REGISTER, PUSH-READY
- **1 new plan file:** TPAMI-6-WEEK-PLAN.md

**15 obsolete task files** (2026-09-14-tier1-*, adapter-improvement-*, algo-improvement-*, paper-finish-line-*, code-tasks-before-freeze, PHASE-1/2/3) and **3 stale synthesis files** (EXECUTION-PLAN, framework-freeze-checklist, framework-internal-metrics, framework-capability-metrics, push-unpushed-commits) moved to `/tmp/todo-archive-2026-09-21/` for traceability.

> **TODO refactor rationale:** Every pre-Wave-205 task file was tied to a now-superseded venue (EAAI / JMLR) or completion state. They are preserved in `/tmp/todo-archive-2026-09-21/` if needed; if not referenced by 2026-10-21, they will be deleted.

---

## Sections

### 1. Active plan

| File | Purpose |
|---|---|
| [TPAMI-6-WEEK-PLAN.md](TPAMI-6-WEEK-PLAN.md) | **NEW** — 6-week TPAMI data-prep schedule with W1-W6 deliverables + per-wave scope + critical risks |

### 2. Operational & governance (preserved from pre-Wave-205)

| File | Purpose |
|---|---|
| [STATUS.md](STATUS.md) | **single source of truth** — current state + R-level claims + recent waves + venue decision |
| [README.md](README.md) | directory structure + when to add new files + current focus |
| [GATES.md](GATES.md) | master gate definitions (binding rule: every todo/ task must have an acceptance gate) |
| [PUSH-READY.md](PUSH-READY.md) | push-readiness summary (user-gated; reflects current HEAD) |
| [decisions.md](decisions.md) | architecture decision log D-001.. (append-only) |
| [lessons-learned.md](lessons-learned.md) | cross-cutting patterns LL-001.. (append-only) |
| [RISK-REGISTER.md](RISK-REGISTER.md) | forward-looking risks + mitigations (different from `lessons-learned.md`) |
| [LOOP.md](LOOP.md) | per-model lifecycle + iteration mechanism + stop conditions |
| [TIMELINE.md](TIMELINE.md) | phase durations + "project done" definition |

### 3. Archived (moved to `/tmp/todo-archive-2026-09-21/`)

15 obsolete task files + 5 stale synthesis docs. Preserved for traceability until 2026-10-21.

---

## Reading order (for new readers)

1. **[README.md](README.md)** — directory structure + when to add new files + current focus
2. **[STATUS.md](STATUS.md)** — current state + R-level claims + recent waves + venue decision
3. **[TPAMI-6-WEEK-PLAN.md](TPAMI-6-WEEK-PLAN.md)** — full 6-week schedule
4. **[`docs/tpami_submission_checklist.md`](../docs/tpami_submission_checklist.md)** — 6-section TPAMI checklist
5. **[`docs/paper-draft.md`](../docs/paper-draft.md)** — main paper draft
6. **[`docs/CLAIMS.md`](../docs/CLAIMS.md)** — 55+ active claims ledger with provenance
7. **[`docs/audit/INDEX.md`](../docs/audit/INDEX.md)** — per-wave audit catalogue (Wave 1 → Wave 205)

After those seven, branch by interest:
- **Statistics rigor:** [`docs/tables/wave203-p4-standardized-stats.md`](../docs/tables/wave203-p4-standardized-stats.md) + [`verification_outputs/wave203-p3-k6-cluster-robust.json`](../verification_outputs/wave203-p3-k6-cluster-robust.json)
- **Mechanism validation:** see TPAMI-6-WEEK-PLAN.md §"W3 Ablation"
- **Efficiency / Pareto:** see TPAMI-6-WEEK-PLAN.md §"W4 Efficiency"
- **Reproducibility:** see TPAMI-6-WEEK-PLAN.md §"W6 Reproducibility"
- **Decision history:** [decisions.md](decisions.md) → [lessons-learned.md](lessons-learned.md) → [RISK-REGISTER.md](RISK-REGISTER.md)

---

## Cross-references

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — unpushed commits (user-gated)
- `git tag v2.7-paper-stats-audit-fix` — pending tag (Wave 203 P5)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 55+ active claims (CLM-040, CLM-061, CLM-066, CLM-067 updated Wave 203/204)
- `docs/baseline-audit-report.md` — Wave-by-wave audit row ledger
- `verification_outputs/` — 264+ verification artifacts (N=1000 sweep JSONs + per-record JSONL + standardized stats tables + cluster-robust CSVs)
- `data/` — model checkpoints (FlowMol3 + Kanzi + LineageFlow + CIFAR-10 RF + MNIST FM + FreqFlow)