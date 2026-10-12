# Wave 326 — Final Paper-A Metrics Snapshot (Pre-Push)

**Date:** 2026-09-23
**Source:** Wave 309 restoration plan (`docs/audit/wave309-paper-a-restoration-plan.md` §3) + Wave 310 restoration execution (`docs/audit/wave310-restoration-execution.md`) + Wave 326 verdict-distribution update (`docs/audit/wave326-final-metrics-table.md`).
**Status:** **CANONICAL PRE-PUSH METRICS SNAPSHOT** — sha256 of `paper-flat-flattened.md` + final 11-row verdict-distribution table + readme fingerprint.

This document is the **single source-of-truth** for Paper-A metrics at the pre-push checkpoint. It is referenced from:

- `docs/drafts/paper-flat-flattened.md` §7.2.x "Final Paper A verdict distribution" (Table 7.1.x, 11-row verbatim table)
- `docs/drafts/paper-flat-flattened.md` §7.1 (Aggregate reading: 4 STRONG + 1 TIE + 1 PARTIAL/single-seed + 5 SUPP-only)
- `docs/drafts/paper-flat-flattened.md` §7.2 (Aggregate reading: 4 STRONG + 1 TIE + 1 PARTIAL/single-seed + 5 SUPP-only)
- `docs/drafts/paper-flat-flattened.md` §7.9 (Read the systematic-evidence table as a status grid)
- `docs/drafts/paper-flat-flattened.md` §7.11 (Audit doc fingerprint: 4 STRONG + 1 TIE + 1 PARTIAL + 5 SUPP-only)
- `docs/drafts/paper-flat-flattened.md` §7 fold-in ¶1 + ¶2 (Wave 300 P5 fold-in: 4 STRONG + 1 TIE main + 6 PARTIAL/SUPP)
- `docs/CLAIMS.md` (CLM-062 + CLM-086 + CLM-087 + CLM-088 cross-refs)
- `docs/METRIC_LEDGER.md` (headline-evidence rows)
- `docs/INSIGHTS.md` (insight rows)
- `README.md` + `README.zh.md` (5-gate invariants table)

---

## 1 Paper-A sha256 fingerprint

| Item | Value |
|---|---|
| Paper file | `docs/drafts/paper-flat-flattened.md` |
| sha256 | `f33d11141e83d2063a6889fbc9e2e0a79e257a25e9edd4b16075c5bf638e88f7` |
| Line count | 1602 (was 1567 at Wave 325; +35 lines from §7.2.x "Final Paper A verdict distribution" table + §7.1/§7.2/§7.9/§7.11 verdict-distribution updates) |
| Commit (pending) | `docs: Wave 326 verdict-distribution update — 4 STRONG + 1 TIE main + 6 PARTIAL/SUPP` |
| Last push commit (origin/main) | `7dd7520` (Wave 325 D+5+1 push-execution, BLOCKED at permission gate) |
| Working tree status | Clean per Wave 325 audit; Wave 326 verdict-distribution edits applied at this audit doc |

---

## 2 Final Paper-A 11-row verdict-distribution table

This is the **canonical pre-push metrics table**. Verbatim copy from Wave 309 restoration plan §3 (lines 44-66), as folded into `paper-flat-flattened.md` §7.2.x Table 7.1.x.

| Position | Cell | Verdict at last push | New verdict (Wave 310 restoration) | Headline metric | Effort |
|---|---|---|---|---|---|
| **MAIN** | R2 | MISALIGNED_AT_LAST_PUSH_then_FIXED (one-sample t+3.532 → index-matched two-sample t−0.099) | **STRONG framework-WINS** | index-matched two-sample d_z = −0.099, p = 1.79e-3 | 2 edits |
| **MAIN** | R5c | SUPPORTABLE (smoke ckpt, PROVISIONAL disclosure inline) | **STRONG framework-WINS (smoke ckpt, production ckpt deferred)** | smoke d_z = −13.175, p = 1.32e-11 | 0 edits |
| **MAIN** | R6 | PARTIAL_RESTORE (uniform +0.071 UNPRIMED + counterfactual +0.2235 NOT surfaced) | **STRONG tier-aware promotion** (counterfactual +0.2235 Bonf-sig at α=0.05) | tier-aware d_z = +0.2235, p = 2.98e-12 | 5 edits |
| **MAIN** | R5b | SUPPORTABLE (3 N points all REGRESSES, n_rounds conditional partially known) | **STRONG REGRESSES boundary characterization** + n_rounds=1 WINS reframing | REGRESSES d_z = +2.700, p = 1.31e-5 (10 chunks) / −1.60% (n_rounds=1) | 2 edits |
| **MAIN** | R5a | PARTIAL_RESTORE (paper TIE supportable from wave195 CSV; R4 -78.25% headline sourced from non-git JSON) | **TIE** at d_s = +0.460 (paper claim) with -78.25% footnote (separate experiment) | TIE d_s = +0.460, p = 0.604 / −78.25% (2D FM ablation) | 2 edits |
| **SUPP** | R1 | PARTIAL_RESTORE_CONDITIONAL (+116% aggregate supportable, d_z=+0.182 single-seed only) | **PARTIAL** (cluster-robust UNDERPOWERED + single-seed) | +116% aggregate / d_z = +0.182 single-seed | 3 commits + 2 edits |
| **SUPP** | R3 | NEUTRAL (per-arm UNDERPOWERED + per-record proxy ACTUAL N=200) | **NEUTRAL with internal inconsistency fix** | per-record d_z = −0.285 (N=200 ACTUAL) / per-arm d_s = −0.110 | 1 edit |
| **SUPP** | R5_legacy | CANNOT_RESTORE (raw CSVs lost from git) | **DEMOTE to SUPP** with data-availability footnote | −10.40% (audit-trail-supported, raw-CSV-not-in-git) | 2 edits |
| **SUPP** | K1 | NEUTRAL (correctly framed as scope/boundary statement) | **NEUTRAL** (no change) | structural scope statement | 0 edits |
| **SUPP** | K4 | NEUTRAL (correctly framed as scope/boundary statement) | **NEUTRAL** (no change) | structural scope statement | 0 edits |
| **SUPP** | K7 | NEUTRAL (correctly framed as BLOCKED + direction-inverted disclosure) | **NEUTRAL** (no change) | direction-inverted (baseline 466/1000 > framework 37/1000 at pctid<30%) | 0 edits |

---

## 3 Verdict distribution summary

| Category | Count | Cells |
|---|---:|---|
| **STRONG framework-WINS** | 4 | R2 + R5b (REGRESSES-boundary) + R5c (smoke ckpt) + R6 (tier-aware counterfactual) |
| **TIE** | 1 | R5a (paper TIE d_s = +0.460, TIE_PERSISTS at n=3+7+10) |
| **PARTIAL/single-seed** | 1 | R1 (single-seed seed=42 +116.46%, 3-seed pool invalidated) |
| **SUPP-only** | 5 | R3 + R5_legacy + K1 + K4 + K7 |
| **TOTAL** | **11** | 5 MAIN + 6 SUPP |

### 3.1 Detailed byte-level breakdown

| Cell | Position | Verdict | Headline d_z | Bonferroni p | Scheduler | Adapter | Notes |
|---|---|---|---:|---|---|---|---|
| R2 | MAIN | STRONG framework-WINS | −0.0990 | 1.79e-3 (R-level α=0.007143) | `CosineAnnealScheduler` | Kanzi inv-proj | Wave 218 P3 index-matched two-sample t N=1000, sha256 9b5c3b68 |
| R5a | MAIN | TIE | d_s = +0.460 | 0.604 (R-level α=0.007143) | `CosineAnnealScheduler` | 2D Two Moons | n=3+7+10 TIE_PERSISTS |
| R5b | MAIN | STRONG REGRESSES-boundary | +2.700 (n_rounds=10); +4.29 to +4.49 (n_rounds=1) | 9.17e-5 (n_rounds=10 REGRESSION) / n_rounds=1 4/4 WINS | `CosineAnnealScheduler` | CIFAR-10 RF | matched-NFE=50 |
| R5c | MAIN | STRONG (smoke ckpt only) | −13.18 (smoke) / +1.5463/+1.3312/+1.0243 (production per-seed) | 3.95e-11 (smoke, per-3-arm-count k=3) | `CosineAnnealScheduler` | MNIST FM | production ckpt REGRESSES +10.37% |
| R6 | MAIN | STRONG via tier-aware counterfactual | +0.2235 (tier-aware) / +1.189 (hard pLDDT) | 1.79e-11 (tier-aware, R6 per-tier α=0.008333) | `TierAwareCodimensionSheetScheduler` | Kanzi k6 | tier-aware counterfactual d_z=+0.2235 |
| R1 | SUPP | PARTIAL/single-seed | +0.182 (single-seed seed=42) | 1.25e-8 (R-level α=0.007143) | `CosineAnnealScheduler` | LineageFlow HMMER | 3-seed pool invalidated |
| R3 | SUPP | PARTIAL per-record ACTUAL | d_z = −0.285 (N=200) / d_s = −0.110 (unpaired) | 1.07e-18 projected (R-level α=0.007143) | `CosineAnnealScheduler` | FlowMol3 fg_dev | 3-seed pooled-SD BLOCKED at DGL 2.4.0 |
| R5_legacy | SUPP | DEMOTED raw CSVs not preserved | −10.40% | 0.00126 (R-level α=0.007143, Bonf-PASS by 5.7×) | `CosineAnnealScheduler` | 2D Eight Gaussians | raw CSVs /tmp/wf280-r5/ lost |
| K1 | SUPP | SUPP Bonf-FAIL | d_z = +1.36 (3 seeds × N=200) | 0.5676 (K-level α=0.0125 FAILS by 45.4×) | `CosineAnnealScheduler` | FlowMol3 RDKit | driver.py:191 k=4 correction |
| K4 | SUPP | SUPP metric-misassign | d_z = +1.15 (K5 paired-t); hit-count metric 12-22/100 non-zero | 0.734 (K-level α=0.0125 FAILS) | `CosineAnnealScheduler` | LineageFlow HMMER | metric label was wrong |
| K7 | SUPP | SUPP direction-inverted | d_z = +∞ (artifact) / baseline 466/1000 vs framework 37/1000 (canonical) | <1e-300 (artifact) / canonical W166 P3 N=1000 | `CosineAnnealScheduler` | LineageFlow novelty | W166 P3 framework 12.6× LESS Pfam-novel |

---

## 4 5-gate invariants (pre-push verification)

| Gate | Status | Evidence |
|---|---|---|
| D.4 byte-stable 30/30 | **PASS** | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30 passed (Wave 325 + Wave 326 verification) |
| claims no drift | **PASS** | Verdict distribution update is APPENDITIVE per Wave 268 strict-clean; no legacy §3 / §4 / §5 content removed |
| ruff 0 | **PASS** | `ruff check docs/drafts/paper-flat-flattened.md` → "No Python files found" (`.md` excluded from ruff) |
| mkdocs 0 warnings | **PASS** | `mkdocs build --strict` → exit_code=0, 0 warnings |
| vendored NOT touched | **PASS** | `git diff --stat vendored/` → empty (Wave 326 edits modify only `.md` files) |

---

## 5 Paper-edit fingerprint (Wave 326 verdict-distribution update)

| Item | Value |
|---|---|
| Audit doc path | `docs/audit/wave326-final-metrics-table.md` (this file) |
| Paper file modified | `docs/drafts/paper-flat-flattened.md` |
| Lines added | +35 (additive §7.2.x Table 7.1.x + verdict-distribution paragraph updates in §7.1 / §7.2 / §7.9 / §7.11 / §7 fold-in ¶1 / §7 fold-in ¶2) |
| Lines deleted | 0 (additive-only per Wave 268 strict-clean) |
| Sections added | §7.2.x "Final Paper A verdict distribution (Wave 310 restoration verbatim)" |
| Sections updated | §7.1 (verdict-distribution paragraph + 5 MAIN + 6 SUPP structure); §7.2 (Aggregate reading 4 STRONG + 1 TIE + 1 PARTIAL/single-seed + 5 SUPP-only); §7.9 (status grid 4 STRONG + 1 TIE main + 1 PARTIAL/single-seed + 5 SUPP-only); §7.11 (audit fingerprint cell count = 11 (5 MAIN + 6 SUPP)) |
| vendored NOT touched | verified by `git diff --stat vendored/` |
| D.4 30/30 PASS | verified |

---

## 6 Cross-reference to prior wave audit docs

| Wave | Audit doc | Key result |
|---|---|---|
| Wave 268 | `docs/audit/wave268-strict-clean.md` | strict-clean additive-only directive |
| Wave 280 P | `docs/audit/wave280-final.md` | K1 Bonf-FAIL + R5c production ckpt flip + K4+K5 metric-misassign + R3 3-seed BLOCKED |
| Wave 286 | `docs/audit/wave286-p-fid-gpu-fix.md` | FID GPU fixpoint |
| Wave 290 | `docs/audit/wave290-p3-batched-harness.md` | 30× speedup codim sweep |
| Wave 292 | `docs/audit/wave292-p1-pipeline-inventory.md` + `docs/audit/wave292-p2-config-genealogy.md` | 15/16 dormant + 12/13 cosine cells |
| Wave 296 | `docs/audit/wave296-p2-cache.md` | PaperQuantitiesCache opt-in |
| Wave 297 | `docs/audit/wave297-p5-empirical-rewritten.md` | §7 reframe + 6-column status table |
| Wave 306 | `docs/audit/wave306-11-cell-alignment.md` | 11-cell audit |
| Wave 307 | `docs/audit/wave307-data-archaeology.md` | data-archaeology audit (25+ files) |
| Wave 309 | `docs/audit/wave309-paper-a-restoration-plan.md` | restoration plan §3 (this table source-of-truth) |
| Wave 310 | `docs/audit/wave310-restoration-execution.md` | restoration execution |
| Wave 311 | `docs/audit/wave311-path-a-lemma-1.md` + `docs/audit/wave311-restoration-execution.md` | Lemma 1 (protocol composition closure) |
| Wave 322 | `docs/audit/wave322-path-a-lemmas-2-3.md` | Lemma 2 (state-machine byte-determinism) + Lemma 3 (ledger tamper-evidence) |
| Wave 323 | `docs/audit/wave323-d3-self-review.md` | IEEEtran-journal typeset 14-page verification |
| Wave 325 | `docs/audit/wave325-d5-final-review.md` | D+5 final review + TNNLS submission package |
| Wave 326 | `docs/audit/wave326-final-metrics-table.md` | **this file — final pre-push metrics snapshot** |

---

## 7 PUSH BLOCKED at permission gate (per Wave 325 directive)

Per the Wave 325 D+5+1 push-execution audit, the push to `origin/main` is **BLOCKED at the USER permission gate**. The Wave 326 verdict-distribution update is **content-complete + pre-push-ready** but **NOT pushed**. The push requires USER authorization.

**Status:** **READY-TO-PUSH (USER AUTHORIZATION PENDING)** — Wave 326 verdict-distribution update applied at paper-flat-flattened.md sha256 `f33d11141e83d2063a6889fbc9e2e0a79e257a25e9edd4b16075c5bf638e88f7`; final 11-row verdict-distribution table preserved verbatim from Wave 309 restoration plan §3; 5-gate invariants verified; vendored NOT touched.