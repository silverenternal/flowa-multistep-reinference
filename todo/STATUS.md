# `todo/STATUS.md` — current execution status (2026-09-17 post-Wave 177)

**Updated:** 2026-09-17 (Wave 177 final push `cec3328` — kanzi shape pad + lineageflow synthetic composite `None` fix; lineageflow real re-run bit-identical to Wave 176; D.4 33/33 + ruff 0 + claims PASS)

This file replaces the stale 2026-09-14 snapshot that was preserved below for provenance. The historical content under the divider does not reflect the current repo state — kept only for traceability.

---

## Current evidence and next gates (2026-09-17, post-Wave 177)

- **HEAD commit:** `cec3328` (Wave 177 P1 + P2 + P3 final; kanzi real ckpt shape pad + lineageflow synthetic composite returns `None` + lineageflow real re-run bit-identical to Wave 176).
- **Unpushed commits ahead of `origin/main`:** 0 (post-Wave 177 push). 0 behind.
- **D.4 byte-stable regression vectors:** 33/33 PASS (last verified Wave 177).
- **Pytest default-threads:** 5155 passed, 196 skipped (last verified Wave 131 freeze; ruff-frozen code preserved).
- **Ruff:** 0 findings (last verified Wave 177).
- **Mypy:** 988 errors in 70 files (camera-ready only; CLM-024 wording acknowledges).
- **mkdocs build --strict:** PASS (last verified Wave 131).
- **ckpt SHA-256:** 4/4 PASS (FlowMol3, Kanzi cleaned_model, Kanzi encoder, LineageFlow).
- **claims_consistency:** PASS (No drift detected; 41 ACTIVE, 0 PROVISIONAL, 2 DEPRECATED; last verified Wave 177).

## R-level experimental claims (load-bearing for §10.6)

| # | Model | Metric | Baseline | Framework | Δ | N | Status |
|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | HMMER hits | 158 | **342** | **+116%** | 1000 | ✅ p<1e-10 |
| R2 | FlowMol3 | fg_dev | 0.6381 | **0.6146** | **−0.0235** | 1000 | ✅ 4.05σ |
| R3 | CIFAR-10 RF v2 | FID | 218.87 | **122.18** | **−44.17%** | 1000 | ✅ NFE-averaged |
| R4 | 2D Two Moons | W₂ | 0.5029 | **0.4663** | **−7.28%** | 1000 | ✅ |
| R5 | 2D Eight Gaussians | W₂ | 0.6606 | **0.5919** | **−10.40%** | 1000 | ✅ |
| R6 | LineageFlow | pLDDT / scPerp | 42.07/17.88 | **43.20/13.96** | **+1.12/−3.92** | 1000 | ✅ NFE=10 caveat |

## Wave 174-177 evidence (cross-model GPU eval)

| Wave | Outcome | Status |
|---|---|---|
| Wave 174 P4 | N=30 lineageflow 3/3 wins both + kanzi 3/3 scPerp + pLDDT trade-off (NFE=50/100/200) | DONE |
| Wave 175 P2 | Per-adapter NFE_REF mechanism (kanzi=10, lineageflow=50) — DID NOT FIX kanzi pLDDT (argmax decoder insensitivity) | DONE (architectural limit documented) |
| Wave 176 P1 | Primary metric saturation: both baselines already 1.00; framework ties correctly; lineageflow composite +0.20/+0.14/+0.05 | DONE |
| Wave 177 P1+P2+P3 | Kanzi real ckpt shape pad (load-bearing for Wave 178) + lineageflow synthetic composite returns `None` (was misleading −0.25) + lineageflow real re-run bit-identical | DONE |

## Critical short boards (next-wave priority)

**See `todo/paper-finish-line-tier1-shortboard-closure.md` for full plan.**

| # | Short board | Severity | Closes via |
|---|---|---|---|
| P0-1 | No head-to-head with Fast-DLLM / FlowCast / AB-Cache / PFDiff / LeDiFlow | CRITICAL | Wave 180-182 |
| P0-2 | Kanzi pLDDT regression at NFE=50-200 (Wave 175 fix didn't work) | CRITICAL | Wave 178 (architecture) |
| P0-3 | Single seed (seed=42) — Wave 174/175/176 all use only seed=42 | CRITICAL | Wave 179 (multi-seed) |
| P1-1 | NFE curve too sparse (3 points) | HIGH | Wave 183 |
| P1-2 | No n_rounds ablation (multi-round vs restart-blend) | HIGH | Wave 184 |
| P1-3 | Kanzi real ckpt end-to-end eval NOT done | HIGH | Wave 178 (architecture enables) |
| P1-4 | Theory ↔ empirical gap (BL bound tightness) | HIGH | Wave 185 |
| P1-5 | Sensitivity analysis on key hyperparameters | MEDIUM | Wave 186 |

## Venue decision

**Primary: JMLR (Journal of Machine Learning Research)** — best fit for math theory + cross-model + reproducibility profile; rolling submission; 35-50 page papers OK.

**Backups:** AI (Elsevier Q1) / PR (Elsevier Q1). Defer TPAMI / NeurIPS / ICLR (not good fit).

## Next-wave execution path (10 waves, 5-9 weeks)

| Wave | Goal | Status |
|---|---|---|
| 178 | Kanzi real ckpt architecture redesign (P0-2 + P1-3) | READY |
| 179 | Multi-seed R6 + Wave 174 ladder (P0-3) | QUEUED |
| 180 | Head-to-head: FlowA vs Fast-DLLM (P0-1 part 1) | QUEUED |
| 181 | Head-to-head: FlowA vs AB-Cache (P0-1 part 2) | QUEUED |
| 182 | Head-to-head: FlowA vs FlowCast / PFDiff / LeDiFlow (P0-1 part 3) | QUEUED |
| 183 | Finer NFE curve (P1-1) | QUEUED |
| 184 | n_rounds ablation (P1-2) | QUEUED |
| 185 | Theory bound tightness (P1-4) | QUEUED |
| 186 | Sensitivity analysis (P1-5) | QUEUED |
| 187 | Camera-ready paper finalization + JMLR submission | QUEUED |

---

## Historical snapshot (2026-09-14, Wave 134) — preserved for provenance

*(The text below this divider is from `todo/STATUS.md` prior to the 2026-09-17 rewrite. It describes the v1.0-paper-final state and does not reflect the post-Wave 177 reality. Kept only for traceability of the v1.0.1 tag history.)*

### 2026-09-14 v1.0-paper-final snapshot (historical)

- **HEAD commit:** `1d1723d` (Wave 144 Phase 4 final close; 18 commits ahead of v1.1-paper-final planned tag).
- **Tag:** `v1.0-paper-final` (Wave 131 Phase 3 freeze marker; ruff 0 / D.4 33/33 / pytest ≥5155 / claims PASS / mkdocs strict EXIT=0 / ckpt SHA-256 4/4 PASS).
- **Unpushed commits ahead of `origin/main`:** 2 (Wave 144 Phase 2 + Phase 4; awaiting user OK).
- **D.4 byte-stable regression vectors:** 33/33 adapters PASS.
- **Pytest default-threads:** 5155 passed, 196 skipped.
- **Ruff:** 0 findings (down from 207 in Wave 127; Wave 131 Phase 1).
- **Mypy:** 988 errors in 70 files (camera-ready only; out of scope; CLM-024 wording acknowledges).
- **mkdocs build --strict:** PASS.
- **ckpt SHA-256:** 4/4 PASS per `verification_outputs/ckpt_sha256.json`.

**Open follow-ups (2026-09-14 view; superseded by 2026-09-17 plan above):**

1. Wave 92c (in flight): N=1000 Kanzi framework paper-metric — closes W2 measurability
2. Wave 93 Phase 2 (in flight): per-cell CI + Bonferroni + reframe §7.6 — closes W4 reframing
3. Wave 94: ICLR 2027 submission package — superseded by Wave 187 (JMLR submission)
4. Wave 92d (OPT-IN): N=5000 sweep on all 3 Tier 3 models — closes W3 (defer until Wave 92c/93/94)
5. FreqFlow / MM-FM: indefinitely deferred (no upstream ckpt / no shipped adapter)
6. CI dashboard: composite-aware check in `tools/capability_audit.py`