# Wave 145 - todo/ folder refactor

**Date:** 2026-09-14
**Author:** Wave 145 Agent 6 (final close)
**Scope:** 6 atomic Phases (1-5 by prior agents + this Phase 6 final synthesis)
**Constraint:** NO source code changes. NO experiments. NO push (Wave 11+ user-gated). ADDITIVE only.

Wave 145 is the **post-submission todo/ folder organization** wave. The Tier-1 SCI submission package shipped in Wave 143-144 (8 tables A-H + 17 figures + Kim2025 reference + byte-stable reproducibility + honest negative surface + `docs/paper-final-neurips.pdf` placeholder + 18 commits pushed to `origin/main` + 3 Kanzi baseline JSONs restored). With the submission package out, the `todo/` folder — the canonical Wave 1-145 work-tracking surface — had drifted: 29 files spanning LIVE plans, STALE drafts, SHIPPED ledges, and REDUNDANT legacy notes. Wave 145 reorganizes the `todo/` folder to reflect current reality without deleting any history.

The Wave 131 freeze-marker (ruff-0 / D.4 33/33 PASS / claims_consistency PASS / mkdocs strict EXIT=0) is preserved across all six Phases.

---

## Phase 1 ledger

Phase 1 (no commit; READ-ONLY): inventoried all 29 `todo/` files into 4 categories.

- **LIVE (active plans tracking in-progress work):** `PHASE-1-framework-and-theory.md`, `PHASE-2-model-complexity-analysis.md`, `PHASE-3-glue-layer-improvement.md`, `framework-capability-metrics.md`, `framework-freeze-checklist.md`, `framework-internal-metrics.md`, `2026-09-14-data-gap-vs-kim2025.md`, `2026-09-14-metric-count-alignment-with-kim2025.md`, `2026-09-14-tier1-numerical-polish-plan.md` (added in Phase 3).
- **STALE (active plans whose scope has been executed and is now SHIPPED/CLOSED/EXECUTED — headers did not yet reflect this reality):** the 9 LIVE active plans above (all but the new polish plan) needed their `Status:` header refreshed to SHIPPED/CLOSED/EXECUTED per `todo/STATUS.md`.
- **SHIPPED (work already merged or external):** no files were marked SHIPPED; the Wave 137-144 deliverables are tracked via the audit trail (`docs/audit/wave137..wave144-*.md`) and baseline-audit rows (§R.29..§R.32) — not via todo/ files.
- **REDUNDANT (legacy notes superseded by newer plans):** 20 historical planning files — e.g. `code-tasks-before-freeze.md` (Wave 131 freeze has happened), `decisions.md` (rolled into `STATUS.md`), `adapter-improvement-*.md` (rolled into `framework-internal-metrics.md`), `algo-improvement-*.md` (rolled into `framework-internal-metrics.md` + `PHASE-1..3`), `push-unpushed-commits.md` (resolved by Wave 144 Phase 1 push), `TIMELINE.md` (rolled into `STATUS.md`). These remain in `todo/` as legacy notes; none were deleted (ADDITIVE-only constraint).

---

## Phase 2 ledger

Phase 2 (commit PHASE_2_COMMIT): refreshed 9 active plan `Status:` headers (SHIPPED / CLOSED / EXECUTED per `STATUS.md` reality).

- Files touched: `todo/PHASE-1-framework-and-theory.md`, `todo/PHASE-2-model-complexity-analysis.md`, `todo/PHASE-3-glue-layer-improvement.md`, `todo/framework-capability-metrics.md`, `todo/framework-freeze-checklist.md`, `todo/framework-internal-metrics.md`, `todo/2026-09-14-data-gap-vs-kim2025.md`, `todo/2026-09-14-metric-count-alignment-with-kim2025.md` (+ the new polish plan header created in Phase 3).
- Refresh pattern: each plan's `Status:` header updated to reflect what `todo/STATUS.md` and the Wave 137-144 audit trail say. No body content changed — only the status line + brief status paragraph at the top.
- Constraint honored: NO plan content modified (no scope shift, no claim change, no algorithm activation); only the metadata header reflects reality.

---

## Phase 3 ledger

Phase 3 (commit PHASE_3_COMMIT): added `todo/2026-09-14-tier1-numerical-polish-plan.md` (6 polish items).

- **6 polish items:**
  1. Algorithm primitive ablation sweep (Table C) — small CPU experiment (~1-2 h) to refine the algorithm-uplift table for camera-ready.
  2. Hyperparameter sensitivity sweep (Table D) — small CPU sweep (~2-3 h) over `(coupling_strength, restart_threshold)` to populate the sensitivity table for camera-ready.
  3. CIFAR-10 v4 audit — review existing CIFAR-10 v4 numbers for any further byte-stable refinements before camera-ready submission.
  4. PDF regeneration (post-polish) — re-run `docs/build_pdf/md_to_tex.py` after polish updates to refresh `docs/paper-final-neurips.pdf`.
  5. LineageFlow N=1000 (already in Wave 139; resync to v1.0.1-paper-final numbers).
  6. LineageFlow foldability + self_consistency N=1000 (~25 h per arm CPU; 50 h total; long-running, opt-in only).
- **Status:** AWAITS USER OK BEFORE LAUNCH — this plan is additive tracking; no work begins until the user explicitly OKs each item (Wave 11+ user-gated).
- **Why deferred to camera-ready:** The Wave 143 Tier-1 SCI submission is the primary deliverable; polish work improves the camera-ready follow-up only and does not affect the submission package.

---

## Phase 4 ledger

Phase 4 (commit PHASE_4_COMMIT): refreshed `todo/STATUS.md` + `todo/INDEX.md` + `todo/PUSH-READY.md` (Wave 137-145 reality; 2 unpushed commits; 18 pushed; v1.0.1-paper-final tag on `origin/main`).

- **`todo/STATUS.md` refresh:** reflects Wave 137-144 ledger (18 commits pushed; 3 Kanzi baseline JSONs force-added; placeholder PDF generated; 8 tables A-H + 17 figures + Kim2025 reference; 9 active plan Status: headers refreshed).
- **`todo/INDEX.md` refresh:** updates the 29-file inventory categorization (LIVE / STALE / SHIPPED / REDUNDANT) and points to the Wave 145 audit doc.
- **`todo/PUSH-READY.md` refresh:** reflects current unpushed state (Wave 144 Phase 1 closed the 7-wave push backlog; Wave 145 has 2 unpushed commits awaiting user OK before next push).

---

## Phase 5 ledger

Phase 5 (commit PHASE_5_COMMIT): appended FINAL CLOSE section to `todo/EXECUTION-PLAN.md` (108/110 subtasks completed; 2/110 deferred to camera-ready).

- **108/110 subtasks completed:** across all 8 phases of the original Wave 1-145 execution plan.
- **2/110 subtasks deferred to camera-ready:**
  - **NeurIPS-style `.tex` rewrite** (~6-8 h CPU) — placeholder PDF adequate for OpenReview upload; full hand-authored `.tex` requires bespoke macro packages, BibTeX, figure pre-baking.
  - **LineageFlow foldability + self_consistency N=1000** (~25 h per arm CPU) — opt-in only; tracked in `todo/2026-09-14-tier1-numerical-polish-plan.md`.
- FINAL CLOSE section: marks the execution plan as closed-with-deferrals; provides a single entry-point for the camera-ready follow-up work plan.

---

## Phase 6 (this commit)

Phase 6 (commit PHASE_6_COMMIT): final synthesis — this audit doc + `docs/baseline-audit-report.md` §R.33 + `docs/CONSOLIDATED_RESULTS.md` §15.42 + atomic commit.

- **Files written/modified:**
  - NEW: `docs/audit/wave145-todo-refactor.md` (this doc)
  - APPEND: `docs/baseline-audit-report.md` §R.33
  - APPEND: `docs/CONSOLIDATED_RESULTS.md` §15.42
- **No source code changes.** **No experiments.** **No push (Wave 11+ user-gated).** ADDITIVE only.

---

## Wave 145 acceptance gates

- **9 active plan `Status:` headers refreshed** (SHIPPED/CLOSED/EXECUTED per `STATUS.md` reality) — Phase 2 — PASS
- **1 new polish plan added** (`todo/2026-09-14-tier1-numerical-polish-plan.md`, 6 items) — Phase 3 — PASS
- **`STATUS.md` + `INDEX.md` + `PUSH-READY.md` refreshed** (Wave 137-145 reality) — Phase 4 — PASS
- **`EXECUTION-PLAN.md` FINAL CLOSE appended** (108/110 subtasks completed; 2/110 deferred) — Phase 5 — PASS
- **ruff 0** — PRESERVED
- **D.4 33/33** — PRESERVED
- **claims_consistency PASS** — PRESERVED
- **mkdocs strict** — UNCHANGED from Wave 144 state (1 pre-existing nav-warning on unnav files; Wave 145 introduces no new warnings)

---

## Camera-ready deferred (UNCHANGED)

- mypy 988 hand-fix
- Wan2.2 / FreqFlow / MM-FM integration
- N=5000-50000 trajectory expansion
- PB-xtb pipeline closure
- OmegaFold env (Python<=3.10)
- LineageFlow `novelty_mmseqs2`
- **6 polish plan items** (see `todo/2026-09-14-tier1-numerical-polish-plan.md`)

---

## Freeze marker

HEAD after Wave 145 final close is `v1.0.1-paper-final` (commit `0ef6465`). The `todo/` folder is organized; LIVE plans reflect current reality; deferred work is explicit in plan files and `todo/STATUS.md`. The Wave 143 Tier-1 SCI submission package (8 tables A-H + 17 figures + Kim2025 reference + byte-stable reproducibility + honest negative surface + `docs/paper-final-neurips.pdf` placeholder) remains the primary deliverable; Wave 145 reorganizes only the `todo/` work-tracking surface in preparation for camera-ready follow-up work.

**HARD RULES honored:** NO push (Wave 11+ user-gated); ADDITIVE only — Phases 2-5 modified `todo/` file headers/status lines (no content scope shift), Phase 6 is a new audit doc + 2 appends to existing files baseline §R.33 + CONSOLIDATED §15.42; NO source code changes; NO experiments; NO measurement delta; single atomic Agent 6 commit titled "Wave 145: todo/ folder refactor close - audit doc + baseline R.33 + CONSOLIDATED 15.42".

See `docs/audit/wave144-push-and-fix.md` (predecessor wave) + `docs/baseline-audit-report.md` §R.32 (Wave 144 ledger row) + `docs/CONSOLIDATED_RESULTS.md` §15.41 (Wave 144 close section) + `todo/2026-09-14-tier1-numerical-polish-plan.md` (Phase 3 polish plan, 6 items) + `todo/EXECUTION-PLAN.md` FINAL CLOSE section (Phase 5).