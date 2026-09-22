# Wave 32 Agent A — `todo/` audit + gap analysis

**Author**: Wave 32 Agent A
**Date**: 2026-09-05
**Scope**: per-task audit of `todo/*.md` (38 files), gap cross-reference
against HARD gates (`framework-freeze-checklist.md` MUST-1),
group-G capability metrics (`verification_outputs/capability_audit_q3_2026.json`),
adapter-level audit findings (`docs/audit/adapter-conformance-deep-dive.md`),
operating-regime findings (`docs/audit/ROOT_CAUSE_ANALYSIS.md`),
algorithm-level audit findings (`docs/audit/theory-implementation-gap.md`),
and mkdocs-strict surface (`mkdocs.yml`).

## 1. Per-task audit (38 files)

### 1.1 Already marked `done` (24 files)

| File | Commit evidence | One-line summary |
|---|---|---|
| `algo-improvement-conformance-battery.md` | `4d30f41` | D.5 LIVE: 90 passed, 8 checks × 14 adapters |
| `algo-improvement-convergence-order.md` | `d7cd65b` + `53e5d52` | C.6 + DPK45 bug fix; 5/5 integrators pass |
| `algo-improvement-env-hash.md` | `43b862d` | F.5 LIVE: env_hash + requirements-lock + capture script |
| `algo-improvement-f2-reproduction.md` | `e397528` | F.2 4/8 → 7/8 REPRODUCED |
| `algo-improvement-failure-modes.md` | `441f54f` (Wave 17 P2) | Algo D: noise_sigma on twodim_fm + Pareto plots |
| `algo-improvement-mutation-testing.md` | `6ec3385` (Wave 18 F.6) | Q4 2026: aggregate 0.833, theory 0.533 |
| `algo-improvement-operating-regime.md` | (Wave 17 P3) | CRITICAL gap closed; `docs/theory/operating-regime.md` |
| `algo-improvement-planar-bl-repoint.md` | `6d12744` (Wave 14 A) | Theorem1StatementChecker consumes true R² BL |
| `algo-improvement-property-based-testing.md` | (Wave 17 P1) | B.7: 9+ Hypothesis tests in `tests/test_property_based/` |
| `algo-improvement-rate-bound.md` | `f9d34e1` (Wave 15 B) | `rate_bound.py` + `√(2/π)` explicit bound |
| `algo-improvement-sbc.md` | `c0e2fe2` (Wave 18 C.7) | C.7 SBC: 6/6 algorithms pass chi-squared |
| `algo-improvement-traceability-hardening.md` | `3ead25f` (Wave 15 A) | A.4 0.171 → 0.938; A.7 75% → 87.5%; B.4 +5 doctests |
| `algo-improvement-uplift-isolation.md` | `a1f8650` (Wave 14/15) | 36-uplift isolation suite in `tests/test_algo_uplifts/` |
| `paper-writeup.md` | `2f436f1` (Wave 19 P2) | `docs/paper-draft.md` 990 lines, 6 sections |
| `PHASE-1-framework-and-theory.md` | (Wave 11 + 12) | `G-MASTER-PHASE-1` passed |
| `PHASE-2-model-complexity-analysis.md` | `a6e574d` (Wave 19 P1A1) | 3 models + `todo/models/RANKING.md` |
| `push-unpushed-commits.md` | (Wave 12) | `e0238ab` pushed; origin/main matches |
| `rerun-wave10-with-refactored-framework.md` | `a37476b` (Wave 19 P1A2) | verdict=not_supported; metric saturated |
| `wave10-result-validation.md` | (Wave 10) | LineageFlow shipped; BLOCKED on `core` documented |
| `wave11-result-validation.md` | (Wave 11) | 10 Protocol surfaces + 52 conformance tests |
| `wave12-result-validation.md` | (Wave 12) | 7 A1 fixes pushed |
| `wave13-metrics-research-result.md` | (Wave 13) | rev 2 + 5 critical + 4 major issues fixed |
| `wave14-result-validation.md` | (Wave 14) | 9 baseline audits populated |

### 1.2 Files whose status needs updating in-place (3 files)

| File | Current status | Recommended update | Justification |
|---|---|---|---|
| `framework-capability-metrics.md` | `pending` | **done** | capability audit tool shipped (Wave 23 Agent B); gate integrated (Wave 23 Agent D); capability_audit_q3_2026.json shows all 5 G HARD metrics PASS (post Wave 28 + 30 fixes) |
| `framework-internal-metrics-rev3-plan.md` | `pending` | **done** | Wave 22 P3 (#489); integrated into rev 3 plan with capability-metrics (task #487); rev 3 plan file authored at `todo/framework-internal-metrics-rev3-plan.md` (verified) |
| `framework-freeze-checklist.md` | `pending` | **partial** (see §2 MUST-1 update) | 5/5 G HARD now PASS but freeze-checklist summary table still lists G.1/G.3/G.6 as FAIL — stale; E.4 also went live (Wave 27 A) but checklist says NOT-MET; F.6 went live (Wave 18 + Wave 25) but is NOT in the summary table at all |

### 1.3 Files that remain `pending` by design (2 files)

| File | Status | Why pending is correct |
|---|---|---|
| `PHASE-3-glue-layer-improvement.md` | **partial** (4 glue modules + 84 tests shipped, but 0/4 RANKING adapters consume `adaptive_reflow.core.*`; per MUST-3) | Per-adapter refactor deferred per MUST-3 contract (gated on ≥2 of 4 RANKING adapters existing); MM-FM BLOCKED, LineageFlow BLOCKED on `core` |
| `PHASE-4-model-integration-iteration.md` | **blocked** | Gated on MUST-1..3 + MUST-5 of freeze-checklist; also blocked by the G-MER-PHASE-4 saturation-tie block rule (Wave 19 P1A2 verdict=not_supported) |

### 1.4 Process / governance / decision-log files (5 files — no status field needed)

| File | Why no status |
|---|---|
| `decisions.md` | append-only decision log |
| `EXECUTION-PLAN.md` | decomposed atomic subtasks (most completed) |
| `GATES.md` | master gate definitions (binding per user directive) |
| `lessons-learned.md` | append-only lesson log |
| `LOOP.md` | per-model lifecycle doc |
| `RISK-REGISTER.md` | forward-looking risks |
| `STATUS.md` | single source of truth (this wave updates it) |
| `TIMELINE.md` | phase duration budget |
| `README.md` | directory map |

## 2. Gap table (per-gap status + plan-pointer + recommended action)

### 2.1 HARD gates NOT MET (per `framework-internal-metrics.md` rev 2 §3)

| Gap | Status | Plan-pointer | Recommended action |
|---|---|---|---|
| **D.4** pinned adapter regression vectors | **NOT MET** | **NONE** (no `todo/algo-improvement-*.md` for D.4; only mentioned in `framework-freeze-checklist.md` line 66 + `framework-internal-metrics.md` line 80 + `EXECUTION-PLAN.md` line 74 sub-step) | Author `todo/algo-improvement-D4-regression-vectors.md` to plan the 18/18 `(seed, input, NFE)` regression-vector pinning; per-adapter discipline requires the adapter author to commit a vector before PHASE-4 integration; pattern: `regression-vectors/<adapter>.json` with fixed seed + NFE + initial-state-tensor hash |
| **E.1** CLM claim test-coupled floor | **PARTIAL** (11/41 active = 26.8%; target ≥ 70% by Wave 16) | **NONE** (only mentioned in `framework-freeze-checklist.md` line 68 + `framework-internal-metrics.md` line 87) | Author `todo/algo-improvement-E1-claim-test-coupling.md` to plan the remaining 18-20 claims (categories b/c/d) that Wave 26 Agent C deferred; targeted scope: high-impact claims not yet wired; est. 4-6 hours to close to ≥ 70% |
| **E.4** doc-builder diff job | **MET** (Wave 27 Agent A, 2026-09-05 — `tools/check_doc_paper_refs_diff.py` + `.github/workflows/doc-citation-diff.yml`; 458 functions checked) | n/a | Update `framework-freeze-checklist.md` MUST-1 summary table to mark E.4 PASS (stale entry says NOT MET); the diff-job lives, the dry-run reports `PASS  E.4 diff -- 0 regressions across 458 functions` |

### 2.2 Group G capability metrics (per `verification_outputs/capability_audit_q3_2026.json`)

| Gap | Status | Plan-pointer | Recommended action |
|---|---|---|---|
| **G.1** mean value score | **PASS** (0.0884 ≥ +0.05; median of sign-normalized deltas) | n/a | Update `framework-freeze-checklist.md` MUST-1 summary to mark G.1 PASS (stale entry says FAIL) |
| **G.2** cost-benefit ratio | **PASS** (0.962 ≤ 5.0) | n/a | Already SOFT; not blocking |
| **G.3** worst-case bound | **PASS** (-0.0251 ≥ -0.03; post Wave 28 Agent A extractor-family-variance fix) | n/a | Update `framework-freeze-checklist.md` MUST-1 summary to mark G.3 PASS (stale entry says FAIL) |
| **G.4** generalization breadth | **PASS** (3 ≥ 3) | n/a | Update `framework-freeze-checklist.md` MUST-1 summary to mark G.4 PASS (already in summary but listed as PASS — confirm) |
| **G.5** saturation point | **FAIL** (275 NFE median, SOFT) | `todo/framework-capability-metrics.md` §G.5; `docs/CONSOLIDATED_RESULTS.md` | Paper-time aspiration only; not blocking; close via Wave 32 Agent B web-research recommendations (target ≤ 50 NFE median; would require multi-NFE rows for all integrated models) |
| **G.6** honest negative surface | **PASS** (0.25 ≤ 0.30; post Wave 30 Agent A equal-family-weight stratification) | n/a | Update `framework-freeze-checklist.md` MUST-1 summary to mark G.6 PASS (stale entry says FAIL) |
| **G.7** reproducibility-of-capability | **PASS** (7/7 ≥ 6/7) | n/a | Already in summary; confirm |

### 2.3 Adapter-level issues (per `docs/audit/adapter-conformance-deep-dive.md`)

| Gap | Status | Plan-pointer | Recommended action |
|---|---|---|---|
| **StochasticFMAdapter enum bug** (`reference_frame="stochastic_fm"`, `normalization="per_channel_std"` — non-canonical) | **NOT MET** (documented as `NONCONFORMANCE_BUG #5` in audit doc; adapter is **orphan** — not in `ADAPTER_REGISTRY`, not referenced by production adapters) | **NONE** (no `todo/algo-improvement-stochastic-fm-*.md` plan; only mentioned in `docs/audit/adapter-conformance-deep-dive.md` lines 112-160) | Pick one of: (a) change strings to canonical `world` + `per_atom_std`; (b) extend canonical enums; (c) **delete** `StochasticFMAdapter` (audit-doc recommendation, lowest-risk path since adapter is unused). Recommend (c) as a 1-line fix-wave |
| **FlowMol3V2Adapter restart shape crash** (`apply_restart_distribution` crashes on shape mismatch) | **NOT MET** (documented as `NONCONFORMANCE_BUG #1`) | **NONE** (only mentioned in audit doc) | Author `todo/algo-improvement-FlowMol3V2-restart-fix.md`; 5-10 LOC fix + regression test |
| **model_card.md missing from mkdocs nav** (5 `docs/models/*.model_card.md` files: `flowmol3`, `lineageflow`, `rectified_flow_cifar`, `self_flow`, `twodim_fm`) | **NOT MET** (mkdocs strict FAILS at 2026-09-05; 8 unnavmed files including model cards, `capability_g1_analysis.md`, `theory/DEVIATIONS.md`) | **NONE** (no `todo/algo-improvement-*.md` plan; only mentioned in `docs/baseline-audit-report.md` line 962-978) | Add nav entry to `mkdocs.yml`: `- Models:` section under Architecture with 5 model-card entries. Or add `models/*.model_card.md` to `not_in_nav` allowlist (silent; trade-off: cards not linkable from site) |
| **Reference_flowa orphan class** | **NOT MET** (documented as `NONCONFORMANCE_DESIGN #2 (orphan)`) | n/a | Same fix pattern as `stochastic_fm`: either register or delete |
| **FreqFlow / Kanzi skeleton** | **NOT MET** (documented as `NONCONFORMANCE_DESIGN #3/#4` — skeletons not yet registered) | `todo/PHASE-3-glue-layer-improvement.md` | Registration is part of MUST-2 / PHASE-3 acceptance; deferred |

### 2.4 Algorithm-level (`D.1` shrink adapters) — per Wave 11 follow-up

| Gap | Status | Plan-pointer | Recommended action |
|---|---|---|---|
| **D.1** adapter line count median ≤ 350 (rev 3) / ≤ 500 (rev 2); currently ~1500 median | **NOT MET** (deferred per Wave 11 Phase 3 note in `PHASE-1-framework-and-theory.md` §1.2 + Wave 24 Agent B follow-up gate in `framework-freeze-checklist.md` MUST-3) | **NONE** (no dedicated `todo/algo-improvement-D1-shrink.md`; only mentioned in `framework-internal-metrics.md` line 77 + `framework-freeze-checklist.md` line 290 SHOULD-4) | Author `todo/algo-improvement-D1-shrink-adapters.md` to plan the per-adapter refactor that consumes `adaptive_reflow.core.*` (MUST-3 framework-core glue); per the freeze-checklist §MUST-3 "Follow-up gate", this is gated on ≥2 of 4 RANKING adapters existing (MM-FM + LineageFlow both BLOCKED → Kanzi + FreqFlow are the 2 needed); est. 4-8 hours per adapter once unblocked |

### 2.5 Operating regime (F-* audit findings) — per Wave 29 + 31 follow-ups

| Finding | Status | Plan-pointer | Recommended action |
|---|---|---|---|
| **F-1** `checkers.py:sheet_tube_evidence` wrong residual | **DONE** (Wave 30 commit `8944a09` per git log) | n/a | Confirmed fixed |
| **F-2** `sample_planar_residual_posterior` simplified residual | **OPEN** (Agent A F-2 priority medium per ROOT_CAUSE_ANALYSIS) | **NONE** (no dedicated plan; deferred per ROOT_CAUSE_ANALYSIS §5 action #5 "docstring-only") | Accept limitation + docstring; paper-faithful 2D-vector sampler is a new module (defer to dedicated paper-faithfulness wave) |
| **F-3** `paper_selection_ratio` algebraic form vs paper | **OPEN** (cosmetic; not on algorithm path) | n/a | Doc-only; deferred |
| **F-4** `selection_ratio` heuristic cell-evidence-constant | **DONE** (Wave 30 commit `8944a09`: renamed to `sheet_vs_cells_proxy`) | n/a | Confirmed fixed |
| **F-5** `CodimensionSheetScheduler.n_cap` cosine-driven | **DONE** (Wave 31 commit `64429c9`: `PaperRatioAdaptiveScheduler` + ratio-driven n_cap) | n/a | Confirmed fixed — limitation removed |
| **F-6** `LinearBlender` is convex combine not paper restart | **OPEN** (per ROOT_CAUSE_ANALYSIS §5 action #3 "no paper §4 restart operator exists" — accept limitation) | n/a | Accept limitation (no paper §4 restart operator exists); documentation only |

## 3. Plan coverage matrix

| Gap | Has plan file? | Plan path |
|---|---|---|
| D.4 regression vectors | NO | n/a — gap |
| E.1 test-coupled 70% | NO | n/a — gap |
| E.4 doc-builder diff | YES (implicit via Wave 27 Agent A) | `.github/workflows/doc-citation-diff.yml` |
| G.5 saturation point | YES | `framework-capability-metrics.md` §G.5 |
| StochasticFMAdapter enum | NO | n/a — gap |
| FlowMol3V2 restart shape | NO | n/a — gap |
| model_card.md in nav | NO | n/a — gap |
| D.1 shrink adapters | NO (Wave 11 deferred) | n/a — gap (gated on MUST-3 refactor) |
| F-2 paper-faithful sampler | NO | n/a — gap (docstring-only) |
| F-3 paper_selection_ratio cosmetic | NO | n/a — gap (doc-only) |
| F-6 LinearBlender restart operator | NO | n/a — accepted limitation |

**Total gaps without plan**: 7 actionable (D.4, E.1, StochasticFMAdapter, FlowMol3V2 restart, model_card nav, D.1 shrink, plus F-2/F-3 docstring updates if pursued).

**Total gaps accepted-as-limitation**: 2 (F-6 LinearBlender, F-3 paper_selection_ratio cosmetic).

## 4. mkdocs strict surface (as of 2026-09-05)

`mkdocs build --strict` aborts with 1 warning per this run. Unnavmed files:

- `capability_g1_analysis.md` (Wave 28 Agent B output)
- `models/flowmol3.model_card.md` (F.4)
- `models/lineageflow.model_card.md` (F.4)
- `models/rectified_flow_cifar.model_card.md` (F.4)
- `models/self_flow.model_card.md` (F.4)
- `models/twodim_fm.model_card.md` (F.4)
- `theory/DEVIATIONS.md`

**Action**: add to `mkdocs.yml` either (a) a `Models` section under `Architecture` linking the 5 `*.model_card.md` files plus `capability_g1_analysis.md` and `theory/DEVIATIONS.md`; or (b) add `models/*.md` + `capability_g1_analysis.md` + `theory/DEVIATIONS.md` to the `not_in_nav` allowlist. Option (a) is preferred (cards become discoverable). This breaks the B.3 `mkdocs --strict` HARD gate that was previously claimed as PASS.

## 5. Summary

- **24 of 38** `todo/*.md` files already marked `done` (verified via git log)
- **3 files** need in-place status updates: `framework-capability-metrics.md`, `framework-internal-metrics-rev3-plan.md`, `framework-freeze-checklist.md`
- **2 files** correctly stay `pending` (PHASE-3 partial, PHASE-4 blocked)
- **8 HARD gates** flipped from FAIL to PASS since the freeze-checklist was last updated (E.4, F.6, G.1, G.3, G.6, plus internal theory findings F-1, F-4, F-5); checklist is stale
- **7 actionable gaps** have no plan file (D.4 regression vectors, E.1 test-coupled floor, StochasticFMAdapter enum, FlowMol3V2 restart shape, model_card.md nav, D.1 shrink adapters, F-2/F-3 docstring updates)
- **mkdocs --strict** is currently FAILING (8 unnavmed files) — B.3 HARD gate is at risk