# `todo/` — Next-phase task tracker (per-task markdown)

**Date:** 2026-09-05
**Purpose:** Per-task markdown tracker for the next phase of framework work. Lives
alongside `todo.json` (which is the machine-readable index of completed/in-progress
tasks) — this folder is for human-readable planning and tracking.

## Structure

```
todo/
├── README.md                                 (this file)
├── STATUS.md                                 (single source of truth, auto-updated per wave)
├── GATES.md                                  (master gate definitions, includes G-FRAMEWORK-HEALTH)
├── framework-internal-metrics.md            (6 metric groups A-F + entry gates per phase)
├── LOOP.md                                   (per-model lifecycle + iteration + stop conditions)
├── TIMELINE.md                               (phase durations + project-done definition)
├── RISK-REGISTER.md                          (forward-looking risks + mitigations)
├── decisions.md                              (architecture decisions D-001..)
├── lessons-learned.md                        (lessons LL-001..)
│
├── PHASE-1-framework-and-theory.md           (Wave 11 + 12 done)
├── PHASE-2-model-complexity-analysis.md      (next phase — UNBLOCKED)
├── PHASE-3-glue-layer-improvement.md         (pending)
├── PHASE-4-model-integration-iteration.md    (pending)
│
├── wave10-result-validation.md               (done)
├── wave11-result-validation.md               (done)
├── wave12-result-validation.md               (done — 7 A1 fixes + pushed)
├── wave13-metrics-research-result.md         (done — framework-internal-metrics rev 2)
├── wave14-result-validation.md               (done — A + 9 baseline audits; C in progress)
│
├── algo-improvement-planar-bl-repoint.md     (done — Wave 14 A; commit 6d12744)
├── algo-improvement-rate-bound.md            (done — Wave 15 B; commit f9d34e1; 8 tests)
├── algo-improvement-uplift-isolation.md      (done — Wave 15 rescue; commit a1f8650; 37 tests)
├── algo-improvement-failure-modes.md         (pending — 1.2.d, D, GPU)
├── algo-improvement-env-hash.md              (done — Wave 15 Phase 1; commit 43b862d)
├── algo-improvement-traceability-hardening.md (done — Wave 15 A; commit 3ead25f; A.4→0.938)
├── algo-improvement-conformance-battery.md   (done — Wave 15 C; commit 4d30f41; D.5 LIVE)
├── algo-improvement-f2-reproduction.md       (done — Wave 15 F; commit e397528; F.2→7/8)
├── algo-improvement-property-based-testing.md (NEW — B.7, framework depth gap)
├── algo-improvement-convergence-order.md      (NEW — C.6, framework depth gap)
├── algo-improvement-sbc.md                    (NEW — C.7, framework depth gap)
├── algo-improvement-mutation-testing.md      (NEW — F.6, framework depth gap, quarterly)
├── algo-improvement-operating-regime.md      (NEW — CRITICAL framework depth gap)
│
├── rerun-wave10-with-refactored-framework.md (pending — depends on D-004)
├── push-unpushed-commits.md                  (done — Wave 6 → Wave 12 pushed 2026-09-05)
├── paper-writeup.md                          (pending — per user "投稿的计划已经有了")
└── add-more-2026-sota-models.md             (FOLDED into PHASE-2)

todo/models/
├── README.md                                 (per-model analysis template)
└── lineageflow.md                            (Wave 10 BLOCKED lesson)
```

## Convention

- **One .md file per next-phase task** — not for in-flight work (that's in
  todo.json under `tasks[]`).
- Each file starts with: **status** (`pending` / `in_progress` / `blocked` /
  `done`), **dependencies** (which previous tasks must complete first), and
  **next action** (one sentence describing the first thing to do when the task
  starts).

## When to add files

Add a new file here when:
- A wave finishes and uncovers a follow-up task.
- The user gives a new directive that doesn't fit an existing wave.
- The framework acquires a new SOTA model and the next-paper idea branches.

## Current focus (per user directive 2026-09-05)

> "先把算法完善的工作做完" — finish the algorithm improvement work first.

**Wave 15 status (as of 2026-09-05):** All 4 framework-hardening tasks
landed. Phase 3 verify in progress. 11 framework gaps closed.

**Next priority (framework depth gaps, per user "framework depth not
enough" 2026-09-05 directive):**

1. **B.7 property-based testing** — `algo-improvement-property-based-testing.md`
   — 0% → ≥40% by Wave 16. CPU only. ~2-4 hours.
2. **C.6 convergence-order verification** — `algo-improvement-convergence-order.md`
   — 0% → SciML test_convergence pattern. GPU. ~4-6 hours.
3. **C.7 Simulation-Based Calibration** — `algo-improvement-sbc.md`
   — 0% → SBC for stochastic re-inference. GPU. ~6-12 hours.
4. **F.6 ML-aware mutation testing** — `algo-improvement-mutation-testing.md`
   — 0% → quarterly audit. ~8-24 hours compute.
5. **Operating-regime theoretical analysis** — `algo-improvement-operating-regime.md`
   — **CRITICAL** (the framework's core claim). 1-2 weeks math + 1-3 days GPU + 2-4 hours docs.

**Algo layer:**
6. **D** `algo-improvement-failure-modes.md` — pending, GPU

Each task has its own gate definition listed in each detail file.

## Detailed atomic subtasks

For all 12 pending files broken into ~110 atomic subtasks (15-60 min each),
see `todo/EXECUTION-PLAN.md`. Use this when scheduling work — each subtask
has time estimate + dependencies + acceptance criteria.