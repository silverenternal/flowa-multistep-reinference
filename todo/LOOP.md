# `todo/LOOP.md` — Per-model lifecycle + iteration mechanism + stop conditions

**Date:** 2026-09-05
**Purpose:** the `PHASE-1..4` files describe **a single model's journey**
through 4 stages. This file defines the **loop** that runs many models through
that journey, and the **stop conditions** that determine when the project
is done.

---

## 1. Per-model lifecycle (per the user's "一个一个来" directive)

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: framework 基础 (one-time, project-wide)                    │
│  Goal: theory + algorithm + glue patterns are solid                  │
│  Input: PHASE-1 todo file + JMAA paper                              │
│  Output: G-MASTER-PHASE-1 passed                                   │
│  Exit: ready for any model to enter STAGE 2                         │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: per-model analysis (loop per model)                        │
│  Goal: understand M's complexity, integration difficulty, risk      │
│  Input: PHASE-2 todo file + Wave 9 R1-R4 research                  │
│  Output: todo/models/M.md (7 sections)                              │
│  Exit: G-MASTER-PHASE-2 passed (>= 3 candidates analyzed)           │
│  Work: one model at a time per user directive                       │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: glue + adapter + tests (per model, ranking order)          │
│  Goal: make M runnable through framework's abstract interface       │
│  Input: todo/models/M.md (analysis) + PHASE-3 todo file            │
│  Output: adaptive_reflow/adapters/M.py + tests/test_adapters/test_M.py│
│  Exit: G-MASTER-PHASE-3 passed for M (per-model gate)               │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: baseline-vs-framework comparison (per model)                 │
│  Goal: empirically validate the "any FM improves" claim for M         │
│  Input: todo/models/M.md + todo/PHASE-4 acceptance metric table     │
│  Output: todo/PHASE-4-results/M/comparison.md + verdict recorded    │
│  Exit: G-MASTER-PHASE-4 per-model gate passed                       │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
        ┌───────────────────┴────────────────────┐
        ↓                                        ↓
   verdict = supported                  verdict ∈ {partial, not_supported}
        ↓                                        ↓
   next model in RANKING.md              back to STAGE 1 (re-fix theory)
                                            or STAGE 2 (re-analyze)
                                            or STAGE 3 (re-fix glue)
```

---

## 2. Iteration triggers (when to back up)

| Trigger | Action | New lesson entry? |
|---|---|---|
| 1 model verdict = not_supported | Back to STAGE 1; re-examine theory; append LL-N | yes |
| >= 2 consecutive models verdict = partial | Back to STAGE 2; check if ranking assumptions hold | yes |
| New SOTA model released (2026 Tier-1 venue) | Re-rank; potentially new STAGE 2 entry | no |
| Existing CLM claim disputed by new evidence | Update CLM + STAGE 1 | yes |
| Phase 1 refactor changes framework interfaces | Restart STAGE 3 for all ranked models | no |
| User explicit direction | Pause iteration; await next directive | no |

---

## 3. Stop conditions (when is the project done?)

The project is **done** when **ALL** of the following hold:

- [ ] **STAGE 1 done**: G-MASTER-PHASE-1 passed
- [ ] **>= 3 RANKING.md models verdict = supported** (or "partially_supported"
      for saturated metrics, with explicit caveat in CLM-001..CLM-047)
- [ ] **Workshop paper draft** exists (per `paper-writeup.md` + G-MASTER-PAPER)
- [ ] **All unpushed commits pushed to origin/main** (G-OPS-PUSH)
- [ ] **User explicit "project done"** confirmation

If any of the above is **false**, the loop continues.

---

## 4. Per-model lifecycle — concrete example (LineageFlow)

| Stage | Status | Result |
|---|---|---|
| STAGE 1 | done | Wave 11 shipped (commit `ebc0550`, pushed); G-MASTER-PHASE-1 done |
| STAGE 2 | done | `todo/models/lineageflow.md` (Wave 10 lessons) — 7 sections, 112 lines |
| STAGE 3 | done | `adaptive_reflow/adapters/lineageflow.py` + 22-test suite + registered |
| STAGE 4 | **BLOCKED** | real forward pass needs LineageFlow `core` source; verdict = partially_supported on synthetic shim |
| Loop action | pending user decision | (a) find upstream `core` source; (b) declare LineageFlow design-only and remove adapter; (c) re-classify as "framework's value not measurable on this model" |

---

## 5. Per-model lifecycle — next model (FreqFlow, by ranking)

| Stage | Status | Result |
|---|---|---|
| STAGE 2 | done (Wave 19 P1A1) | PHASE-2 analysis: `docs/PHASE-2-model-complexity-analysis.md` |
| STAGE 3 | done (Wave 21 Agent F) | `adaptive_reflow/adapters/freqflow.py` + 30-test suite (commit `5706eba`) |
| STAGE 4 | done (Wave 21) | comparison run; verdict documented in `docs/CONSOLIDATED_RESULTS.md` §7.5 |
| Gate | done | FreqFlow gate result recorded; `G-MASTER-PHASE-3` verdict = `partially_supported` |

---

## 6. Convergence rules (when does the loop terminate vs restart?)

```
IF verdict = supported:
  mark M done in `todo/models/M.md` §F
  record CLM in `docs/CLAIMS.md` (if not already)
  row in `docs/CONSOLIDATED_RESULTS.md` §7+
  NEXT model in RANKING order
  (no back-up)

ELIF verdict = partially_supported:
  mark M done with caveat in `todo/models/M.md` §F
  row in `docs/CONSOLIDATED_RESULTS.md` (with caveat)
  NO CLM claim added (claim is too soft)
  NEXT model in RANKING order (don't block on partial)
  append LL-N if metric saturation was the cause (LL-002 case)

ELIF verdict = not_supported:
  STOP the entire loop
  append LL-N to `todo/lessons-learned.md` with:
    - which model
    - what the regression was
    - which STAGE needs to be re-done
  re-enter STAGE 1 (theory lift) → STAGE 2 (re-analyze) → STAGE 3 (re-fix glue)
  re-run the failing model's STAGE 4 to confirm regression is gone
  THEN resume loop with the next model in ranking

ELIF verdict = blocked:
  mark M blocked with reason in `todo/models/M.md` §F
  attempt (a) unblock in current wave; (b) reclassify as design-only
  if neither works: SKIP M, NEXT model
```

---

## 7. Per-model lifecycle visualization (textual)

```
Model M enters loop at STAGE 2 (analysis)
    │
    ├─ STAGE 2 → analysis written
    │
    ├─ STAGE 3 → adapter + tests + registered
    │
    ├─ STAGE 4 → comparison + verdict
    │       │
    │       ├─ supported → loop ends for M, NEXT model
    │       ├─ partial → loop ends for M with caveat, NEXT model
    │       ├─ not_supported → back to STAGE 1, RE-RUN STAGE 4
    │       └─ blocked → SKIP M, NEXT model
    │
    └─ back to STAGE 1 (if regression) or NEXT model
```

---

## 8. When does the WHOLE PROJECT end?

When **ALL** of the stop conditions in §3 are met.

Until then, the loop runs forever (or until user terminates).

A model that gets blocked can stay blocked indefinitely (with `blocked` verdict
recorded honestly) — that does NOT terminate the project, just excludes M
from the claim's evidence base.

The PROJECT-LEVEL termination criterion is: **enough positive evidence (>= 3
models supported) to publish a paper**. Below that, keep iterating.
