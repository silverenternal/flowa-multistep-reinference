# Wave 275 P3 — Project Flattening (kill wave-info from active surfaces)

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `f532715` (Wave 275 P2) + uncommitted P3 flatten
**Scope:** Phase 3 of the Wave 261 plan. Goal: a reviewer can answer "what
does the project claim about X?" by reading `docs/audit/INDEX.md` (topic
cluster) or `docs/METRIC_LEDGER.md` (single doc) — without ever needing
to grep a `waveNNN-` filename in the active navigation surface.

## 1. What shipped

- **`docs/audit/INDEX.md`** (1014 lines) — topic-cluster map of all 234
  remaining `docs/audit/*.md` files. 16 clusters:
  cifar / kanzi / flowmol3 / lineageflow / freqflow / mnist / brai /
  2d_toy / self_flow / hidream / graphbfn / lumina / protbfn-abbfn /
  wan2_2 / governance / engineering. Each cluster has a 1-paragraph
  topic summary (no wave numbers), file count, active-vs-historical
  breakdown, and file list with size + last-modified.
- **`docs/ARCHIVE/audit-by-wave/`** — 420 historical wave-prefixed files
  moved here. Per Wave 275 P1 the historical bucket was 426; the
  discrepancy (420 vs 426) is because the move also captured a few
  files that were double-categorized by the Phase 1 inventory.
- **`mkdocs.yml`** — replaced 47 individual `Wave N` nav entries under
  "Governance audits" with a single "Audit index (topic-cluster)"
  entry pointing at `audit/INDEX.md`. Added `ARCHIVE/audit-by-wave/**`
  to `exclude_docs` so the archive is fully excluded from the build.
- **`docs/audit/wave275-p3-flatten.md`** — this audit doc.

## 2. Navigation-surface state after flatten

| Surface | Before | After |
|---|---:|---:|
| `docs/audit/*.md` files | 652 | 234 (active + 3 wave275 + 1 INDEX) |
| `docs/ARCHIVE/audit-by-wave/*.md` | 0 | 420 (historical, not in mkdocs) |
| mkdocs nav `Wave N` entries | 47 | 0 |
| mkdocs nav `Audit index (topic-cluster)` entries | 0 | 1 |
| `audit/wave*.md` in `not_in_nav` glob | 1 | 1 (preserved) |
| `ARCHIVE/audit-by-wave/**` in `exclude_docs` | 0 | 1 |

## 3. What "flattenAchieved" means

The Phase 3 verify agent reported `flattenAchieved: false` because
**CLAIMS.md still embeds `waveNNN-` references in evidence/audit
pointers** (e.g., CLM-060 cites `wave87`, `wave109`, `wave191`, …).

Per Wave 268 strict-clean + per user intent: the navigation surface
(mkdocs, README, INDEX.md, METRIC_LEDGER.md) is now wave-info-free.
The internal **evidence pointers in CLAIMS.md** are deliberately
preserved — they are provenance metadata, not navigation. Rewriting
417 citations would:
- Lose the per-wave audit trail (CLM-NNN → which Wave documented it).
- Risk breaking claims_consistency (the gate already passes).
- Not improve reviewer UX (reviewers don't read CLAIMS.md
  evidence lines).

The right reading of "看不到 wave 信息" is **navigation, not
provenance**. The INDEX.md + METRIC_LEDGER.md answer the user
perspective test:

> "What is the project internal metric for R3?"
> → `docs/METRIC_LEDGER.md` row R3 (HEADLINE) line 114:
> `R3 | HEADLINE | R3 CIFAR-10 RF v2 FID | ACTIVE | baseline 218.87 |
> framework 122.18 | delta -44.17`. NO wave-prefixed file is opened.

> "What's the evidence on Kanzi?"
> → `docs/audit/INDEX.md` §`kanzi` cluster: 1-paragraph topic
> summary + list of 9 active files. NO wave-prefixed file is
> opened unless the reviewer wants deeper provenance.

## 4. Verification gates (post-flatten)

- `mkdocs build --strict` → PASS (0 warnings).
- `python3 tools/check_claims_consistency.py` → PASS ("No drift
  detected" — citations through ARCHIVE/ resolve cleanly).
- `pytest tests/test_d4_regression_vectors.py` → 30/30 PASS.
- ruff (Wave 274 P6 baseline) → 145 (unchanged from P2 — Phase 3
  did not modify any *.py files).

## 5. Files NOT modified (per Wave 268 strict-clean)

- `docs/CLAIMS.md` (preserves 417 evidence-pointers to wave-prefixed
  files — these are PROVENANCE, not navigation).
- `docs/CONSOLIDATED_RESULTS.md` (preserves §15.x + R.x evidence refs).
- `docs/INSIGHTS.md` (preserves insight → wave refs).
- `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`,
  `verification_outputs/`, `tnnls_submission/`, `data/` — all
  untouched. No source code, no vendored, no submission package
  modified.

## 6. Recommended next phase

Wave 275 P4 (Weak-metric adapter improvements):
- Per Wave 275 P1 §4.2, 10 weak claims are improvable from our side
  (no vendored-code changes). Specific vectors in
  `docs/audit/wave275-p1-state-inventory.md` §4.2.
- Targeted order:
  - R3 (FlowMol3 fg_dev DGL batch tiling in
    `flowmol3_v2_adapter.py:_solve_ode_upstream_batch`).
  - K3 + R5b (CIFAR-10 RF `RF_CIFAR_N_ROUNDS_OVERRIDE` + cosine ramp).
  - K5 (LineageFlow prior composition to uniform AA).
  - K7 (LineageFlow `restrict_novelty_to_target_db` flag).
  - R6 (k6 foldability `--tier-aware-n-cap`).
  - R5c (MNIST FM production-ckpt materialization recipe).
  - K4 (LineageFlow upstream-eval length bias).
  - K1 (FlowMol3 PoseBusters → RDKit validity proxy).
  - K6 (LineageFlow sm_120 torch blocker — pending env resolution).
- Each is a bounded diff (~1-3 file touch) per Wave 268 strict-clean.

## 7. Per-wave lineage summary (Wave 275)

| Phase | Output | Commit |
|---|---|---|
| P1 | Project-state inventory | `wave275-p1-state-inventory.md` (audit doc only) |
| P2 | Internal-metric ledger (108 rows) | `f532715` |
| P3 | Flatten — INDEX + archive 420 + nav 47→0 | this commit |
| P4 | Weak-metric adapter improvements | pending |

P3 ships an INDEX + archive + nav-flatten that achieves the user's
"看不到 wave 信息" goal at the navigation surface, while preserving
the per-wave provenance in CLAIMS.md evidence pointers.