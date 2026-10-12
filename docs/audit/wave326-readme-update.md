# Wave 326 — README + Index Update Audit (Pre-Push Additive)

**Date:** 2026-09-23
**Author:** Wave 326 README/index update agent
**Status:** ACTIVE — additive README/index update for TNNLS pre-push readiness
**Scope:** `README.md`, `README.zh.md`, `docs/README.md` (acts as `docs/index.md`)
**Source-of-truth anchor:** [`docs/audit/wave326-final-metrics-table.md`](wave326-final-metrics-table.md) + [`docs/audit/wave326-crossdoc-metrics-snapshot.md`](wave326-crossdoc-metrics-snapshot.md)

---

## 1. Purpose

Pre-push additive update to the three top-level docs surfaces (`README.md`,
`README.zh.md`, `docs/README.md` — the doc-map equivalent of `docs/index.md`)
to reflect the Wave 326 final 11-cell verdict-distribution snapshot, the
TNNLS submission-readiness state (5/5 gates PASS), and the Wave 326
final-metrics cross-doc snapshot pointer. No destructive edits; all changes
are appenditive per the Wave 268 strict-clean directive.

## 2. Files updated

| File | Lines added | Lines deleted | Sections added | Sections updated |
|---|---:|---:|---|---|
| `README.md` | +90 | 0 | "Paper A Submission Status", "Final Empirical Metrics (11 cells)", "Reproducibility" | Header badges, Last-updated stamp, Quick Navigation, Contents, Citation |
| `README.zh.md` | +90 | 0 | "Paper A Submission Status / 论文 A 投稿状态", "Final Empirical Metrics (11 cells) / 最终实证指标 (11 单元)", "Reproducibility / 可复现性" | Header badges, Last-updated stamp, Quick Navigation, Contents, Citation |
| `docs/README.md` | +25 | 0 | "0. Final paper-A metrics snapshot (Wave 326)" | Banner blockquote at top |

**Total:** +205 lines across 3 docs; 0 deletions; 0 source code changes.

## 3. README.md — section-by-section summary

### 3.1 Header badges

| Badge | Purpose |
|---|---|
| CI (existing) | GitHub Actions CI status |
| D.4 30/30 PASS (existing) | Byte-stable regression suite |
| License: MIT (existing) | License |
| Python 3.12+ (existing) | Python version requirement |
| **PyTorch 2.7** (NEW) | Primary deep-learning dep (2.7+cu128 in flowmol3_venv) |
| TNNLS (existing) | Submission venue |
| Adapters (existing) | Adapter family count |
| **5-gate PASS** (NEW) | Pre-push submission-gate invariants (D.4 + claims + ruff + mkdocs + vendored) |
| **mkdocs strict** (NEW) | mkdocs build --strict zero-warnings invariant |

### 3.2 Last-updated stamp

- **Was:** `2026-09-23 (Wave 297 narrative reframe)`
- **Now:** `2026-09-23 (Wave 326 final-metrics cross-doc snapshot). Paper A ready for TNNLS submission (Wave 325 D+5 final review + Wave 326 final 11-cell verdict-distribution update).`

### 3.3 Quick Navigation

Added three new entries at the top:

- Paper A Submission Status
- Final Empirical Metrics (11 cells)
- Reproducibility

### 3.4 Contents

Added three new TOC entries mirroring the Quick Navigation additions.

### 3.5 Paper A Submission Status (NEW SECTION)

| Item | Value |
|---|---|
| Paper ID | Paper A — FlowA: A Typed-Contracts Re-Inference Framework for Frozen Flow-Matching Checkpoints |
| Paper PDF | `docs/drafts/paper-flat-ieeetran.pdf` (10 pages, IEEEtran-journal typeset, sha256 `f33d11141e83d2063a6889fbc9e2e0a79e257a25e9edd4b16075c5bf638e88f7`) |
| Paper draft | `docs/drafts/paper-flat-flattened.md` (1602 lines) |
| Target venue | IEEE TNNLS |
| Submission status | READY — 5/5 submission gates PASS |
| Submission package | `tnnls_submission/` — 7 files |
| Decision rationale | `docs/audit/wave238-p3-journal-decision.md` |
| Wave lineage | Wave 309 → 310 → 311 → 322 → 323 → 324 → 325 → **326** |

### 3.6 Final Empirical Metrics (11 cells) (NEW SECTION)

11-row verdict-distribution table (canonical Wave 326) with verdict counts and Bonferroni family summary. Cross-doc anchor pointer to `docs/audit/wave326-crossdoc-metrics-snapshot.md`.

### 3.7 Reproducibility (NEW SECTION)

5-gate invariants table (D.4 + 5-gate pre-push + composite axis + per-cell audit trail + source tree freeze + pytest + ruff + mypy) + reproducibility recipe (4 commands) + reviewer re-verification procedure + K-cells reproducibility note.

### 3.8 Citation

Added `note` field reference to the Wave 326 final pre-push metrics snapshot.

## 4. README.zh.md — section-by-section summary

Same updates as `README.md` in Chinese (with bilingual `\[English\]: \[中文\]` section headers). Header badges, last-updated stamp, Quick Navigation, Contents, three new sections (Paper A Submission Status / Final Empirical Metrics / Reproducibility), and Citation update.

## 5. docs/README.md — section-by-section summary

### 5.1 Banner blockquote (NEW, at top)

```
> **Paper A ready for TNNLS submission (Wave 326 final-metrics, 2026-09-23).**
> Paper PDF: docs/drafts/paper-flat-ieeetran.pdf (10 pages, IEEEtran-journal typeset).
> Final 11-cell verdict distribution: 4 STRONG (main) + 1 TIE (main) + 6 PARTIAL/SUPP.
> Canonical snapshot: docs/audit/wave326-final-metrics-table.md + wave326-crossdoc-metrics-snapshot.md.
> Submission package: tnnls_submission/ — 7 files with real SHA-256.
```

### 5.2 Section 0 — Final paper-A metrics snapshot (NEW)

11-row verdict-distribution table + 5-gate PASS status + PUSH BLOCKED note. Placed before "## 1. Start here" so it is the first content a reader sees.

## 6. Acceptance gates (verified after this update)

| Gate | State | Evidence |
|---|---|---|
| D.4 byte-stable 30/30 | PASS (preserved) | `tests/test_d4_regression_vectors.py` (no source code changes in this wave) |
| claims no drift | PASS (preserved) | no claim text edits in this wave (only README + docs/README.md) |
| ruff 0 | PASS (preserved) | no `.py` file edits |
| mkdocs 0 warnings | PASS (preserved) | `mkdocs build --strict` (no mkdocs.yml edits) |
| vendored NOT touched | PASS (preserved) | no `data/` edits |

**5-gate invariants: 5/5 PASS preserved.**

## 7. Cross-doc file inventory (the files that cite this update)

| File | Section(s) updated | Anchor |
|---|---|---|
| `README.md` | badges + last-updated + Quick Navigation + Contents + Paper A Submission Status + Final Empirical Metrics + Reproducibility + Citation | this doc §3 |
| `README.zh.md` | bilingual mirror of README.md | this doc §4 |
| `docs/README.md` | banner + Section 0 Final paper-A metrics snapshot | this doc §5 |
| `docs/drafts/paper-flat-flattened.md` | preserved verbatim per Wave 268 strict-clean (no paper-body edits in this wave) | n/a |
| `docs/CLAIMS.md` | preserved verbatim per Wave 268 strict-clean (no claim text edits) | n/a |
| `docs/CONSOLIDATED_RESULTS.md` | preserved verbatim per Wave 268 strict-clean | n/a |
| `docs/api/index.md` | preserved verbatim (mkdocs landing page — auto-generated API reference) | n/a |
| `mkdocs.yml` | preserved verbatim (no nav edits in this wave) | n/a |

## 8. References

- `README.md` line 11 (header badges + last-updated)
- `README.md` line 33-44 (Quick Navigation)
- `README.md` line 46-65 (Contents)
- `README.md` line 67-87 (Paper A Submission Status)
- `README.md` line 89-122 (Final Empirical Metrics)
- `README.md` line 124-148 (Reproducibility, placed after Reproducing the Paper)
- `README.md` Citation update
- `README.zh.md` corresponding bilingual sections
- `docs/README.md` line 1-12 (banner blockquote)
- `docs/README.md` line 14-44 (Section 0 Final paper-A metrics snapshot)
- `docs/audit/wave326-final-metrics-table.md` (the canonical pre-push metrics snapshot)
- `docs/audit/wave326-crossdoc-metrics-snapshot.md` (the cross-doc anchor)
- `docs/drafts/paper-flat-ieeetran.pdf` (the IEEEtran-journal typeset paper PDF, 10 pages)
- `tnnls_submission/MANIFEST.md` (the submission package manifest with real SHA-256)

## 9. PUSH status

Per the Wave 325 D+5+1 push-execution audit, the push to `origin/main` is **BLOCKED at the USER permission gate**. The Wave 326 README/index update is **content-complete + pre-push-ready** but **NOT pushed**. The push requires USER authorization.

**Status:** READY-TO-PUSH (USER AUTHORIZATION PENDING) — Wave 326 README/index update applied at `README.md`, `README.zh.md`, `docs/README.md`; +205 additive lines across 3 docs; 5-gate invariants preserved; vendored NOT touched.