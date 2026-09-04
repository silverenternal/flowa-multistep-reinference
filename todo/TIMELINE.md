# `todo/TIMELINE.md` — phase durations + "project done" definition

**Date:** 2026-09-05
**Purpose:** time-budget the 4-phase plan per user "对机子负担最小" directive.
Also define "project done" precisely so the loop has a clear exit.

---

## 1. Per-phase time budget

Estimates are based on Wave 1-11 history (most recent wave: 32 min for
download+adapter+test on LineageFlow, ~30 min for Wave 11 JMAA refactor,
~1-3 hours per wave for parallel-agent waves).

### STAGE 1 (framework + theory + algorithm) — **1-2 hours**

- Wave 11 (done; commit `ebc0550`): ~30 min
- Wave 12 A1 fixes (done; commit `e0238ab`): ~30 min
- Conformance tests + docs: ~15 min
- **Budget: 1 hour active work** (rest is verification + reading)

### STAGE 2 (per-model analysis) — **30 min per model**

- Read paper / repo / HF model card: 15 min
- Fill the 7 sections of `todo/models/M.md`: 10 min
- Update `RANKING.md`: 5 min
- **Budget: 30 min per model, 1 model at a time**
- For 5 candidate models: ~2.5 hours total

### STAGE 3 (per-model glue) — **1-2 hours per model**

- Adapter file (~1500 lines like Self-Flow): 30-45 min
- Test file (22 tests, all passing): 30 min
- Registration + docs: 10 min
- Verification (pytest + mkdocs): 5 min
- **Budget: 1.5 hours per model**
- For 5 candidate models: ~7.5 hours total

### STAGE 4 (per-model comparison) — **30-60 min per model**

- Verify acceptance metric table filled
- Run baseline 1-pass
- Run framework multi-round
- Capture metrics, write comparison.md
- Record verdict in `todo/models/M.md` §F
- **Budget: 45 min per model**
- For 5 candidate models: ~4 hours total

### Project total (3 supported models required to exit)

| Stage | Time |
|---|---|
| STAGE 1 | 1 hour |
| STAGE 2 (3 models analyzed) | 1.5 hours |
| STAGE 3 (3 models glued) | 4.5 hours |
| STAGE 4 (3 models integrated) | 2.25 hours |
| paper draft | 4 hours |
| push + cleanup | 30 min |
| **TOTAL** | **~14 hours** |

---

## 2. Per-wave budget (user "对机子负担最小")

| Wave type | CPU | GPU | Wall-clock |
|---|---|---|---|
| Per-model analysis (STAGE 2) | light (5-10 min CPU) | none | <10 min |
| Per-model adapter write (STAGE 3) | moderate (LLM token use) | none | <5 min LLM + ~30 min for code |
| Per-model comparison (STAGE 4) | moderate | 1 GPU only (5090 or PRO 6000, **not both in parallel**) | 30-60 min |
| Phase 1 refactor (theory lift) | moderate | none | <30 min |
| mkdocs build verification | trivial | none | <10 sec |

**Total machine burden across the whole project**: ~10 hours CPU + ~4 hours GPU
(single card at a time).

---

## 3. "Project done" definition

The project is done when **ALL** of:

- [ ] **G-MASTER-PHASE-1 passed** (framework + theory + algorithm solid)
- [ ] **>= 3 RANKING.md models verdict = supported** (or partially_supported
      with caveat in CLM-001..CLM-047)
- [ ] **Workshop paper draft** exists with all required content (per
      `paper-writeup.md` checklist + G-MASTER-PAPER gate)
- [ ] **All unpushed commits pushed to origin/main** (G-OPS-PUSH)
- [ ] **User explicit "project done"** confirmation

Until then: loop continues (per `LOOP.md`).

---

## 4. Stretch goals (NOT required for project done)

- **>= 5 models supported** (not just 3) — strengthens the "any FM improves" claim
- **Main-conference submission** (workshop first, main-conference would need
  2-3 more months of polish — out of scope per `paper-writeup.md`)
- **Online docs deployment** to GitHub Pages (per `Wave 8 FIX-2` follow-up)
- **Throughput benchmark** vs diffusers / torchcfm (not yet measured)

---

## 5. Why this matters

The user has been very clear: "对机子负担最小" + "服务器爆不能接受". This file makes
time + machine cost explicit per phase, so:

- We don't accidentally launch waves that run for hours without user check-in
- We know in advance how long the whole project will take (~14 hours total)
- We can decide whether to do all 5 candidate models or stop at 3 (the minimum)

---

## 6. Update frequency

This file is updated when:
- A new stage's actual time diverges significantly from estimate (e.g., 50%
  off for 2 consecutive waves)
- User gives a new time constraint
- A stage is skipped or merged with another
- Project done criteria changes (e.g., user decides 5 models required not 3)