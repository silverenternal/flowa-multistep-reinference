# `todo/INDEX.md` — Master entry point

**Date:** 2026-09-14 (Wave 127 Phase 5 flat refactor)
**Purpose:** curated entry point to the `todo/` working folder. New
readers should start with the [Reading order](#reading-order-for-new-readers)
section. Each section below groups files by purpose, links the most
important ones, and links to related artifacts outside `todo/`.

> **Folder layout (2026-09-14 Wave 127 Phase 5 flat refactor):** the
> `todo/` root holds 25 files only — 6 active root plans, 11 governance
> docs (STATUS, INDEX, GATES, LOOP, TIMELINE, RISK-REGISTER, EXECUTION-PLAN,
> README, decisions, lessons-learned, PUSH-READY), push-unpushed-commits
> log, and 3 framework synthesis docs (framework-freeze-checklist,
> framework-internal-metrics, framework-capability-metrics), and 3 PHASE
> docs (PHASE-1/2/3). The historical `todo/completed/` (47 archived
> plans), `todo/inprogress/`, `todo/planned/` (8 plans + 1 README), and
> `todo/models/` (5 files) subdirectories were deleted in Wave 127 Phase 5;
> their content lives in git history (`14e8bc5^` and earlier). This file
> plus `todo/STATUS.md` are the cross-cutting entry points that stay at
> the `todo/` root.

---

## Current execution (2026-09-14)

Start with [STATUS.md](STATUS.md). Wave 127 finish-line: 167 unpushed
commits; `push_risk = LOW` (user-gated). D.4 = 18/18 adapters PASS; pytest =
5155/196 green; ruff --fix applied (720 auto-fixed, 207 non-auto-fixable
remaining are CI-static-gate scope). Mypy 988 errors are out of scope for
the 7-day finish-line (CLM-024 wording acknowledges, Wave 127 Phase 3).

## Historical state summary (2026-09-10)

> **As of 2026-09-10 (Wave 93 Phase 1 landed): 4 一区 reviewer weaknesses
> closed (W1 ✅ Wave 90 / W2 ✅ Wave 91+92a+b / W3 defer / W4 🔄 reframing).
> Wave 92a (Kanzi adapter constants fix `73c6978`) + Wave 92b (upstream
> N-samples patch `60dcbb7`) + Wave 93 Phase 1 (`tools/statistical_power_analysis.py`
> + 4 unit tests `e69ffd8`) all landed. Wave 92c (N=1000 Kanzi
> framework paper-metric sweep) in flight.**

| Bucket | Status (2026-09-10) |
|---|---|
| **G-MASTER gate** | 5/5 HARD PASS (unchanged since Wave 56) |
| **CLM claims** | 41 ACTIVE + 2 DEPRECATED |
| **D.4 regression vectors** | 18/18 adapters PASS (post-Wave 127) |
| **D.5 conformance battery** | 90/90 passed |
| **Algorithm uplifts** | 107 hit target |
| **B.7 / C.7** | ≥40% property-based + 6/6 SBC pass |
| **Tier 3 composite** | Kanzi + LineageFlow + FlowMol3 all `framework_improves` (Wave 52 byte-stable) |
| **Tier 3 paper-metric N=1000** | FlowMol3 1/4 + LineageFlow 1/4 framework_improves; **Kanzi framework_inv_proj** Wave 126 partial (additive annotation `f42de22`) |
| **W1 (PB-xtb)** | ✅ CLOSED (Wave 90) |
| **W2 (Kanzi framework)** | ⚠️ PARTIALLY CLOSED (Wave 91-99; magnitude deferred to Wave 100+ N=1000 framework arm) |
| **W3 (N=1000 small)** | ⚠️ DEFER (Wave 92d N=5000, OPT-IN) |
| **W4 (2/12 mixed)** | 🔄 REFRAMING (Wave 93 statistical power + Bonferroni + Wave 127 Phase 3 §7.6 reframe) |
| **Push state** | 167 unpushed commits (post-Wave 127 Phase 4); `push_risk = LOW` |
| **MUST-1..5** | MUST-1/2/3/4 = PASS; MUST-5 = user-gated push |

**Tier 3 model roster (active):** Kanzi (ICLR 2026, protein) · LineageFlow (ICML 2026, protein) · FlowMol3 (molecule).
**Tier 3 model roster (deferred):** FreqFlow · MM-FM (no upstream ckpt / no shipped adapter — indefinitely deferred per Wave 36).

**Open follow-ups (camera-ready, NOT 7-day finish-line):**
1. Kanzi `framework_synth` N=1000 re-run (~33-50 h CPU)
2. LineageFlow NFE scan 8/9 cells (~8-16 h CPU)
3. CIFAR multi-arm Table 4 re-run (~5 h GPU)
4. ESM-2 NLL N=100 + N=1000 (~3 GPU-h)
5. Wan2.2 N=1000 sweep
6. FreqFlow / MM-FM: indefinitely deferred
7. CI dashboard: composite-aware check in `tools/capability_audit.py`
8. Mypy 988-error repair (CI-static-gate)
9. Ruff 207 non-auto-fixable findings (CI-static-gate)

Wave 127 fix landing traces are documented in
`docs/audit/wave127-finish-line.md` (Wave 127 Phase 6) and the per-wave
audit catalogue in [`docs/audit/INDEX.md`](../docs/audit/INDEX.md).

## Sections

### 1. Active plan files — 6 root `*-improvement-*.md` files

| # | File | Status |
|---|---|---|
| 1 | [algo-improvement-paper-quantity-beta-calibration.md](algo-improvement-paper-quantity-beta-calibration.md) | Wave 125 partial — code landed; CIFAR/twodim acceptance deferred |
| 2 | [algo-improvement-restart-policy-collapse-fix.md](algo-improvement-restart-policy-collapse-fix.md) | Wave 125 partial — code landed; twodim/CIFAR acceptance deferred |
| 3 | [algo-improvement-brai-perturbation-magnitude.md](algo-improvement-brai-perturbation-magnitude.md) | Wave 125 partial — code landed; ESM-2 N=100 + N=1000 acceptance deferred |
| 4 | [algo-improvement-framework-vs-model-metrics-gap.md](algo-improvement-framework-vs-model-metrics-gap.md) | READ-ONLY synthesis (Wave 123 Agent 6); no further code in 7-day scope |
| 5 | [adapter-improvement-inv-proj-bridge-lossy-replacement.md](adapter-improvement-inv-proj-bridge-lossy-replacement.md) | Wave 126 partial — N=20 sweep done (Wave 126 Phase 1 additive annotation); N=1000 done in Wave 127 Phase 1 OR deferred |
| 6 | [adapter-improvement-8-adapter-shim-audit.md](adapter-improvement-8-adapter-shim-audit.md) | READ-ONLY audit complete (Wave 123 Agent 6); per-adapter fixes deferred |

> **Historical plans (CLOSED):** the 26 `algo-improvement-*.md` files
> that previously lived under `todo/completed/` (47 archived plans) were
> removed in Wave 127 Phase 5. Their content is preserved in git history
> (`14e8bc5^` and earlier). All 26 are CLOSED (commits landed; status
> in `STATUS.md`). For the historical traceability index, see
> `git log --all -- 'todo/completed/algo-improvement-*'`.

### 2. Phase plans — `PHASE-1..3`

| File | Status | Wave / Commit |
|---|---|---|
| [PHASE-1-framework-and-theory.md](PHASE-1-framework-and-theory.md) | done | Wave 11 + Wave 12 (commit `ebc0550` + `e0238ab`) |
| [PHASE-2-model-complexity-analysis.md](PHASE-2-model-complexity-analysis.md) | done | Wave 19 P1A1 (`a6e574d`; 3 per-model analysis files + RANKING.md) |
| [PHASE-3-glue-layer-improvement.md](PHASE-3-glue-layer-improvement.md) | done | Wave 24 + Wave 38 + Wave 39 (4 core glue modules + Protocol enforcement) |

> **PHASE-4** (model integration iteration) — removed in Wave 127 Phase 5;
> the per-model info now lives in `docs/CONSOLIDATED_RESULTS.md` §15 and
> the per-wave audit catalogue at [`docs/audit/INDEX.md`](../docs/audit/INDEX.md).

### 3. Wave result validations + master synthesis

The wave result validation files and master synthesis docs
(`wave10-result-validation.md`, `wave11-result-validation.md`, `wave12-result-validation.md`,
`wave13-metrics-research-result.md`, `wave14-result-validation.md`,
`wave43-problems-review.md`, `wave45-adapter-fix-master-plan.md`,
`wave46-master-synthesis.md`) previously lived under `todo/completed/`
and were removed in Wave 127 Phase 5.

For new readers of the recent Tier 3 work, the canonical entry points
are:

- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit
  catalogue (Wave 1 → Wave 133).
- [`docs/CONSOLIDATED_RESULTS.md`](../docs/CONSOLIDATED_RESULTS.md) §15.15 —
  Tier 3 verdict table.
- [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md) —
  5-arm ablation matrix for Kanzi composite.

The wave46 master synthesis historically lived at
`todo/completed/wave46-master-synthesis.md`; its content is preserved
in git history (`14e8bc5^` and earlier). For equivalent current
material, see [`docs/audit/wave99b-n1000-verdict.md`](../docs/audit/wave99b-n1000-verdict.md)
+ [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md).

### 4. Model-specific — formerly `models/`

The `models/` subdirectory (README + RANKING.md + 4 model cards:
kanzi, lineageflow, freqflow, mm-fm) was removed in Wave 127 Phase 5.

The Tier 3 model roster is now summarized in:

- `STATUS.md` §"Active plans" + §"Camera-ready deferred"
- `docs/CONSOLIDATED_RESULTS.md` §15 (Tier 3 verdict table)
- `docs/audit/wave52-kanzi-composite-ablation-synthesis.md`

### 5. Operational & governance

| File | Purpose |
|---|---|
| [STATUS.md](STATUS.md) | **single source of truth** — current state + last completed wave + next actions |
| [framework-freeze-checklist.md](framework-freeze-checklist.md) | MUST-1..5 freeze criteria with current PASS/FAIL status |
| [GATES.md](GATES.md) | master gate definitions (binding rule: every todo/ task must have an acceptance gate) |
| [PUSH-READY.md](PUSH-READY.md) | push-readiness summary (refreshed 2026-09-14: VERDICT READY, 167 unpushed, user-gated) |
| [push-unpushed-commits.md](push-unpushed-commits.md) | push-protocol + Wave 12 push log (now superseded by 167 unpushed commits) |
| [decisions.md](decisions.md) | architecture decision log D-001.. (append-only) |
| [lessons-learned.md](lessons-learned.md) | cross-cutting patterns LL-001.. (append-only) |
| [RISK-REGISTER.md](RISK-REGISTER.md) | forward-looking risks + mitigations (different from `lessons-learned.md`) |
| [EXECUTION-PLAN.md](EXECUTION-PLAN.md) | pending tasks broken into ~110 atomic subtasks (15-60 min each) |
| [TIMELINE.md](TIMELINE.md) | phase durations + "project done" definition |
| [README.md](README.md) | directory structure + when to add new files + current focus |
| [LOOP.md](LOOP.md) | per-model lifecycle + iteration mechanism + stop conditions |
| [framework-internal-metrics.md](framework-internal-metrics.md) | rev 2 ship-ready; A-F metric groups + entry gates per phase |
| [framework-capability-metrics.md](framework-capability-metrics.md) | group G capability metrics |

> **Removed in Wave 127 Phase 5:** `framework-internal-metrics-rev3-plan.md`,
> `paper-writeup.md`, `rerun-wave10-with-refactored-framework.md`,
> `gap-plan-wave32.md` (all under `todo/completed/` previously) — preserved
> in git history.

---

## Reading order (for new readers)

1. **[README.md](README.md)** — directory structure + when to add new files + current focus
2. **[STATUS.md](STATUS.md)** — current state + last completed wave + next actions
3. **[framework-freeze-checklist.md](framework-freeze-checklist.md)** — MUST-1..5 freeze criteria (what "done" means)
4. **[docs/audit/wave99b-n1000-verdict.md](../docs/audit/wave99b-n1000-verdict.md)** +
   **[docs/audit/wave52-kanzi-composite-ablation-synthesis.md](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md)** —
   current Tier 3 / composite-benchmark / push-ready story
   (the load-bearing narrative). The historical `wave46-master-synthesis.md`
   lives in git history under `todo/completed/`.

After those four, branch by interest:
- **Algorithm / theory depth:** [PHASE-1-framework-and-theory.md](PHASE-1-framework-and-theory.md) → [framework-internal-metrics.md](framework-internal-metrics.md) → [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md) (composite formula)
- **Per-model glue:** [PHASE-3-glue-layer-improvement.md](PHASE-3-glue-layer-improvement.md) + [docs/CONSOLIDATED_RESULTS.md §15](../docs/CONSOLIDATED_RESULTS.md)
- **Push protocol:** [PUSH-READY.md](PUSH-READY.md) → [push-unpushed-commits.md](push-unpushed-commits.md) → [RISK-REGISTER.md](RISK-REGISTER.md)
- **Decision history:** [decisions.md](decisions.md) → [lessons-learned.md](lessons-learned.md) → [RISK-REGISTER.md](RISK-REGISTER.md)

---

## Cross-references

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — 167 unpushed commits (Wave 11 → Wave 127 Phase 4)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 41 ACTIVE + 2 DEPRECATED claims (43 CLM entries)
- `docs/baseline-audit-report.md` — 9 metrics + Wave 30+ re-audit
- `verification_outputs/capability_audit_q4_2026_post_w38.json` — current capability gate values (G.1..G.7)
- `docs/audit/INDEX.md` — per-wave audit catalogue
- `docs/theory/theorem1_rate_bound.md` — NEW (Wave 15 B)
- `env_hash.txt` — NEW (Wave 15 Phase 1)
- `requirements-lock.txt` — NEW (Wave 15 Phase 1)
