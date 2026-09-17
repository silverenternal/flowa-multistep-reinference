# `todo/INDEX.md` — Master entry point

**Date:** 2026-09-14 (Wave 134 Phase 4 — `v1.0-paper-final` snapshot
refresh; ruff 0 / D.4 33/33 / 8 N=1000 sweep JSONs in repo)
**Purpose:** curated entry point to the `todo/` working folder. New
readers should start with the [Reading order](#reading-order-for-new-readers)
section. Each section below groups files by purpose, links the most
important ones, and links to related artifacts outside `todo/`.

> **Folder layout (2026-09-14 Wave 134 Phase 4):** the
> `todo/` root holds 26 files — 8 active root plans (3 algo
> SHIPPED, 1 algo READ-ONLY, 2 adapter SHIPPED/READ-ONLY, 2 EXECUTED
> meta-plans), 11 governance docs (STATUS, PUSH-READY, GATES, LOOP,
> TIMELINE, RISK-REGISTER, EXECUTION-PLAN, README, decisions,
> lessons-learned, push-unpushed-commits), 3 framework synthesis docs
> (framework-freeze-checklist, framework-internal-metrics,
> framework-capability-metrics), 1 entry point (INDEX), and 3 PHASE
> docs (PHASE-1/2/3). The historical `todo/completed/` (47 archived
> plans), `todo/inprogress/`, `todo/planned/` (8 plans + 1 README),
> and `todo/models/` (5 files) subdirectories were deleted in Wave 127
> Phase 5; their content lives in git history (`14e8bc5^` and earlier).
> This file plus `todo/STATUS.md` are the cross-cutting entry points
> that stay at the `todo/` root.

---

## Current execution (2026-09-17, post-Wave 177 — Q1 submission path)

Start with [STATUS.md](STATUS.md). **New plan: `paper-finish-line-tier1-shortboard-closure.md`** — 10 waves (Wave 178-187) over 5-9 weeks closing all P0 + P1 short boards for **JMLR** Q1 submission. The previous v1.0-paper-final snapshot (Wave 131-144) is preserved at the bottom of STATUS.md for traceability.

**Active waves / next actions (post-Wave 177 push `cec3328`):**

* **Wave 178 — Kanzi real ckpt architecture redesign** (P0-2 + P1-3): trajectory in `(L, 3)` coord space throughout; eliminates bridge CPU cost; enables end-to-end kanzi real primary metric eval; fixes kanzi pLDDT trade-off at the mechanism level. READY to launch.
* **Wave 179 — Multi-seed R6 + Wave 174 ladder** (P0-3): seeds {42, 43, 44}; 36 cells × N=30 = 1080 records; error bars + significance tests. QUEUED.
* **Wave 180-182 — Head-to-head with related work** (P0-1): Fast-DLLM, AB-Cache, LeDiFlow / FlowCast / PFDiff. Three sequential competitor comparisons. QUEUED.
* **Wave 183 — Finer NFE curve** (P1-1): 9 NFE points × 2 models × 2 arms × N=30 = 108 cells. QUEUED.
* **Wave 184 — n_rounds ablation** (P1-2): isolate restart-blend from multi-round averaging. QUEUED.
* **Wave 185 — Theory bound tightness** (P1-4): empirical BL distance vs Theorem 1 bound. QUEUED.
* **Wave 186 — Sensitivity analysis** (P1-5): β base, restart_min_nfe, NFE_REF, seed. QUEUED.
* **Wave 187 — Camera-ready + JMLR submission** (final): §10.24-10.30 + §15.75-15.81 + §R.66-72 + CLM updates + JMLR submit + tag `v1.1-paper-final-camera-ready`. QUEUED.

**Critical short boards (must close before JMLR submission):**

| # | Short board | Severity | Closes via |
|---|---|---|---|
| P0-1 | No head-to-head with Fast-DLLM / FlowCast / AB-Cache / PFDiff / LeDiFlow | CRITICAL | Wave 180-182 |
| P0-2 | Kanzi pLDDT regression at NFE=50-200 (Wave 175 fix didn't work) | CRITICAL | Wave 178 |
| P0-3 | Single seed (seed=42) | CRITICAL | Wave 179 |
| P1-1 | NFE curve too sparse (3 points) | HIGH | Wave 183 |
| P1-2 | No n_rounds ablation | HIGH | Wave 184 |
| P1-3 | Kanzi real ckpt end-to-end eval NOT done | HIGH | Wave 178 |
| P1-4 | Theory ↔ empirical gap (BL bound tightness) | HIGH | Wave 185 |
| P1-5 | Sensitivity analysis | MEDIUM | Wave 186 |

**Open questions (must resolve before Wave 178 launches):** see §9 of the new plan.

---

## Historical execution (2026-09-14, v1.0-paper-final)

Start with [STATUS.md](STATUS.md). Wave 134 final pass: 3 unpushed
commits ahead of `origin/main` (the Wave 11-127 backlog was pushed
during Wave 128-133; only Wave 134 doc-migration Phases 1-3 are now
unpushed; this Phase 4 STATUS + INDEX refresh becomes the 4th);
`push_risk = LOW` (user-gated). D.4 = 33/33 adapters PASS;
pytest = 5155/196 green; ruff = 0; claims_consistency = PASS
("No drift detected."); mkdocs build --strict = PASS;
ckpt SHA-256 = 4/4 PASS. Tag `v1.0-paper-final` (Wave 131 Phase 3
freeze marker, `39a65a7`); post-Wave 134 will add `v1.0.1-paper-final`
as the doc-only `/tmp/` → `verification_outputs/` migration tag
(additive; no source-code change). 8 N=1000 sweep JSONs in
`verification_outputs/` (formal reproducibility set). Mypy 988 errors
are out of scope for the 7-day finish-line (CLM-024 wording
acknowledges, Wave 127 Phase 3).

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
9. Ruff 207 non-auto-fixable findings → **CLOSED in Wave 131** (0 findings)
10. Wave 86 LineageFlow N=1000 HMMER raw JSON (still NOT in `/tmp/`
    either; would need fresh re-run from raw HMMER output, ~30 min on
    LineageFlow venv) — camera-ready deferred

Wave 127 fix landing traces are documented in
`docs/audit/wave127-finish-line.md` (Wave 127 Phase 6); the per-wave
audit catalogue in [`docs/audit/INDEX.md`](../docs/audit/INDEX.md)
covers Wave 1 → Wave 134 (63+ of 101+ waves have audit docs).

## Sections

### 1. Active plan files — 8 root `*-improvement-*.md` files (post-Wave-134 refresh)

| # | File | Status |
|---|---|---|
| 1 | [algo-improvement-paper-quantity-beta-calibration.md](algo-improvement-paper-quantity-beta-calibration.md) | **SHIPPED** (Wave 125 — code landed `4fbf135` + `da090c2`); camera-ready only — CIFAR/twodim acceptance deferred |
| 2 | [algo-improvement-restart-policy-collapse-fix.md](algo-improvement-restart-policy-collapse-fix.md) | **SHIPPED** (Wave 125 — code landed `4fbf135`); camera-ready only — twodim/CIFAR acceptance deferred |
| 3 | [algo-improvement-brai-perturbation-magnitude.md](algo-improvement-brai-perturbation-magnitude.md) | **SHIPPED** (Wave 125 — code landed `ae33583`); camera-ready only — ESM-2 N=100 + N=1000 acceptance deferred |
| 4 | [algo-improvement-framework-vs-model-metrics-gap.md](algo-improvement-framework-vs-model-metrics-gap.md) | **READ-ONLY synthesis** (Wave 123 Agent 6); no further code in 7-day scope |
| 5 | [adapter-improvement-inv-proj-bridge-lossy-replacement.md](adapter-improvement-inv-proj-bridge-lossy-replacement.md) | **SHIPPED** (Wave 122 P2 + Wave 127/128 N=1000 byte-reproducible); Kanzi framework_inv_proj N=1000 framework 0.8798 vs baseline 0.9020 (TIES, byte-reproducible on ruff-frozen code, Wave 131 Phase 3) |
| 6 | [adapter-improvement-8-adapter-shim-audit.md](adapter-improvement-8-adapter-shim-audit.md) | **READ-ONLY audit** (Wave 123 Agent 6); per-adapter fixes deferred to camera-ready |
| 7 | [paper-finish-line-radical-tier1.md](paper-finish-line-radical-tier1.md) | **EXECUTED** (Wave 129 — radical Tier-1 SCI plan replaces Wave 127 conservative framing; cover letter + §1/§7 + supplementary + checklist all landed Wave 132-133) |
| 8 | [code-tasks-before-freeze.md](code-tasks-before-freeze.md) | **EXECUTED** (Wave 130 — pre-freeze engineering audit + plan; ruff 207→0 Wave 131 Phase 1 + D.4 33/33 + pytest 5155 + claims PASS all green) |
| 9 | [2026-09-14-tier1-numerical-polish-plan.md](2026-09-14-tier1-numerical-polish-plan.md) | **PLANNED - 6 polish items** (Wave 145 Phase 3 — algorithm ablation + hyperparameter sweep + CIFAR v4 audit + PDF + LineageFlow N=1000 + LineageFlow foldability; awaits user OK before launch) |

> **Historical plans (CLOSED):** the 26 `algo-improvement-*.md` files
> that previously lived under `todo/completed/` (47 archived plans) were
> removed in Wave 127 Phase 5. Their content is preserved in git history
> (`14e8bc5^` and earlier). All 26 are CLOSED (commits landed; status
> in `STATUS.md`). For the historical traceability index, see
> `git log --all -- 'todo/completed/algo-improvement-*'`.

### 2. Executed Wave plans (NEW — Wave 134 Phase 4)

These plans were active in earlier waves, have been EXECUTED + verified
green, and are preserved at the `todo/` root for traceability. The
audit docs live under `docs/audit/` (not `todo/audit/` — that subdir
was never created; `todo/` audit-style plans were never a thing).

| # | Plan | Status | Audit doc |
|---|---|---|---|
| 1 | [paper-finish-line-radical-tier1.md](paper-finish-line-radical-tier1.md) | **EXECUTED** (Wave 129) — radical Tier-1 SCI plan replaces conservative Wave 127 framing; cover letter + §1/§7 + supplementary + checklist landed Wave 132-133 | [`docs/audit/wave132-tier1-polish.md`](../docs/audit/wave132-tier1-polish.md) |
| 2 | [code-tasks-before-freeze.md](code-tasks-before-freeze.md) | **EXECUTED** (Wave 130) — pre-freeze engineering audit + plan; ruff 207→0 Wave 131 Phase 1 + D.4 33/33 + pytest 5155 + claims PASS all green | [`docs/audit/wave131-pre-freeze-hygiene.md`](../docs/audit/wave131-pre-freeze-hygiene.md) |
| 3 | (Wave 131 plan) ruff 207→0 + byte-reproducibility verification | **DONE** (Wave 131 Phase 1 + Phase 3) — ruff `ruff check adaptive_reflow/ tests/` returns `All checks passed!` (0 findings); Kanzi N=1000 framework_inv_proj byte-reproducible on ruff-frozen code | [`docs/audit/wave131-pre-freeze-hygiene.md`](../docs/audit/wave131-pre-freeze-hygiene.md) |
| 4 | (Wave 132 plan) NeurIPS template + cover letter + camera-ready sections | **DONE** (Wave 132 Phases B/C/D/E) — paper re-templated to NeurIPS 2026; cover letter R1-R6 explicit; discussion + limitations + broader impact + conclusion sections landed | [`docs/audit/wave132-tier1-polish.md`](../docs/audit/wave132-tier1-polish.md) |
| 5 | (Wave 133 plan) number consistency + final polish | **DONE** (Wave 133 Phases 1-4) — R1-R6 numbers cross-checked across docs; supplementary.md additively filled; `check_docs_against_code.py` regressions fixed; README.md Tier-1 SCI submission pointer; final paper-draft.md read-through | [`docs/audit/wave133-number-consistency.md`](../docs/audit/wave133-number-consistency.md) |
| 6 | (Wave 134 plan) `/tmp/` → `verification_outputs/` doc migration | **DONE** (Wave 134 Phases 1-4) — 3 doc surfaces (`paper-draft.md`, `baseline-audit-report.md`, `CONSOLIDATED_RESULTS.md`) updated to repo-resident paths; formal N=1000 reproducibility set established (8 headline JSONs); tag `v1.0.1-paper-final` pending; STATUS + INDEX refresh (this commit) | (no separate audit doc; rolled into CONSOLIDATED §15.32) |

### 3. Phase plans — `PHASE-1..3`

| File | Status | Wave / Commit |
|---|---|---|
| [PHASE-1-framework-and-theory.md](PHASE-1-framework-and-theory.md) | done | Wave 11 + Wave 12 (commit `ebc0550` + `e0238ab`) |
| [PHASE-2-model-complexity-analysis.md](PHASE-2-model-complexity-analysis.md) | done | Wave 19 P1A1 (`a6e574d`; 3 per-model analysis files + RANKING.md) |
| [PHASE-3-glue-layer-improvement.md](PHASE-3-glue-layer-improvement.md) | done | Wave 24 + Wave 38 + Wave 39 (4 core glue modules + Protocol enforcement) |

> **PHASE-4** (model integration iteration) — removed in Wave 127 Phase 5;
> the per-model info now lives in `docs/CONSOLIDATED_RESULTS.md` §15 and
> the per-wave audit catalogue at [`docs/audit/INDEX.md`](../docs/audit/INDEX.md).

### 4. Wave result validations + master synthesis

The wave result validation files and master synthesis docs
(`wave10-result-validation.md`, `wave11-result-validation.md`, `wave12-result-validation.md`,
`wave13-metrics-research-result.md`, `wave14-result-validation.md`,
`wave43-problems-review.md`, `wave45-adapter-fix-master-plan.md`,
`wave46-master-synthesis.md`) previously lived under `todo/completed/`
and were removed in Wave 127 Phase 5.

For new readers of the recent Tier 3 work, the canonical entry points
are:

- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit
  catalogue (Wave 1 → Wave 134).
- [`docs/CONSOLIDATED_RESULTS.md`](../docs/CONSOLIDATED_RESULTS.md) §15.32 —
  Tier 3 verdict table (Wave 131 final close).
- [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md) —
  5-arm ablation matrix for Kanzi composite.

The wave46 master synthesis historically lived at
`todo/completed/wave46-master-synthesis.md`; its content is preserved
in git history (`14e8bc5^` and earlier). For equivalent current
material, see [`docs/audit/wave99b-n1000-verdict.md`](../docs/audit/wave99b-n1000-verdict.md)
+ [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md).

### 5. Model-specific — formerly `models/`

The `models/` subdirectory (README + RANKING.md + 4 model cards:
kanzi, lineageflow, freqflow, mm-fm) was removed in Wave 127 Phase 5.

The Tier 3 model roster is now summarized in:

- `STATUS.md` §"Active plans" + §"Camera-ready deferred"
- `docs/CONSOLIDATED_RESULTS.md` §15 (Tier 3 verdict table)
- `docs/audit/wave52-kanzi-composite-ablation-synthesis.md`

### 6. Operational & governance

| File | Purpose |
|---|---|
| [STATUS.md](STATUS.md) | **single source of truth** — current state + last completed wave + next actions (refreshed 2026-09-14 Wave 134 Phase 4 for v1.0-paper-final state) |
| [framework-freeze-checklist.md](framework-freeze-checklist.md) | MUST-1..5 freeze criteria with current PASS/FAIL status |
| [GATES.md](GATES.md) | master gate definitions (binding rule: every todo/ task must have an acceptance gate) |
| [PUSH-READY.md](PUSH-READY.md) | push-readiness summary (refreshed 2026-09-14: VERDICT READY, 3 unpushed, user-gated) |
| [push-unpushed-commits.md](push-unpushed-commits.md) | push-protocol + Wave 12 push log (now superseded by 3-commit Wave 134 backlog) |
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
5. **[docs/audit/wave131-pre-freeze-hygiene.md](../docs/audit/wave131-pre-freeze-hygiene.md)** +
   **[docs/audit/wave132-tier1-polish.md](../docs/audit/wave132-tier1-polish.md)** +
   **[docs/audit/wave133-number-consistency.md](../docs/audit/wave133-number-consistency.md)** —
   the v1.0-paper-final pre-freeze + Tier-1 polish + number-consistency
   audit trail (committed `v1.0-paper-final` tag points to `39a65a7`).

After those five, branch by interest:
- **Algorithm / theory depth:** [PHASE-1-framework-and-theory.md](PHASE-1-framework-and-theory.md) → [framework-internal-metrics.md](framework-internal-metrics.md) → [`docs/audit/wave52-kanzi-composite-ablation-synthesis.md`](../docs/audit/wave52-kanzi-composite-ablation-synthesis.md) (composite formula)
- **Per-model glue:** [PHASE-3-glue-layer-improvement.md](PHASE-3-glue-layer-improvement.md) + [docs/CONSOLIDATED_RESULTS.md §15](../docs/CONSOLIDATED_RESULTS.md)
- **Push protocol:** [PUSH-READY.md](PUSH-READY.md) → [push-unpushed-commits.md](push-unpushed-commits.md) → [RISK-REGISTER.md](RISK-REGISTER.md)
- **Decision history:** [decisions.md](decisions.md) → [lessons-learned.md](lessons-learned.md) → [RISK-REGISTER.md](RISK-REGISTER.md)

---

## Cross-references

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — 3 unpushed commits (Wave 134 Phases 1-3)
- `git tag v1.0-paper-final` — freeze marker (points to `39a65a7`); post-Wave 134 will add `v1.0.1-paper-final`
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 39 ACTIVE + 2 DEPRECATED claims (41 CLM entries; `tools/check_claims_consistency.py` PASS)
- `docs/baseline-audit-report.md` — 9 metrics + Wave 30+ re-audit (R.23 at Wave 131 final close)
- `verification_outputs/capability_audit_q4_2026_post_w38.json` — current capability gate values (G.1..G.7)
- `verification_outputs/ckpt_sha256.json` — 4/4 PASS (FlowMol3, Kanzi cleaned_model, Kanzi encoder, LineageFlow)
- 8 N=1000 sweep JSONs at `verification_outputs/` top level (formal reproducibility set)
- `docs/audit/INDEX.md` — per-wave audit catalogue (Wave 1 → Wave 134)
- `docs/theory/theorem1_rate_bound.md` — NEW (Wave 15 B)
- `env_hash.txt` — NEW (Wave 15 Phase 1)
- `requirements-lock.txt` — NEW (Wave 15 Phase 1)
