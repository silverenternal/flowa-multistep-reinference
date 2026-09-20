# `todo/STATUS.md` — current execution status (2026-09-21, post-Wave 205)

**Updated:** 2026-09-21 (Wave 205 TPAMI checklist completed; todo/ refactored from 30 files → 10 governance + 6-week plan)

---

## Current state (2026-09-21)

- **HEAD commit:** `72ba46e` (Wave 204 P1 — defensive sf() vs 1-cdf() in _paired_result, R6 scPerplexity underflow fix)
- **Tag:** none yet (Wave 203 P5 v2.7-paper-stats-audit-fix tag pending final gates; not pushed)
- **Unpushed commits ahead of `origin/main`:** see `git rev-list --count origin/main..HEAD` (user-gated)
- **D.4 byte-stable regression vectors:** 33/33 PASS
- **Pytest default-threads:** 5155 passed, 196 skipped (preserved from Wave 131 freeze; ruff-frozen code)
- **Ruff:** post-Wave 127 Phase 4 auto-fix count: ~207 remaining (out-of-scope-for-7-day; CLM-024 wording acknowledges)
- **Mypy:** 988 errors in 70 files (camera-ready only; CLM-024 wording acknowledges)
- **mkdocs build --strict:** PASS
- **ckpt SHA-256:** 4/4 PASS
- **claims_consistency:** PASS (CLM-040 + CLM-061 updated Wave 204; CLM-066 + CLM-067 added Wave 203)

## R-level experimental claims (load-bearing for paper §7.3 / §10.6)

| # | Model | Metric | Baseline | Framework | Δ | N | Status |
|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | HMMER hits | 158 | **342** | **+116%** | 1000 | ✅ p<1e-10 |
| R2 | FlowMol3 | fg_dev | 0.6381 | **0.6146** | **−0.0235** | 1000 | ✅ 4.05σ |
| R3 | CIFAR-10 RF v2 | FID | 218.87 | **122.18** | **−44.17%** | 1000 | ✅ NFE-averaged |
| R4 | 2D Two Moons | W₂ | 0.5029 | **0.4663** | **−7.28%** | 1000 | ✅ matched |
| R5 | 2D Eight Gaussians | W₂ | 0.6606 | **0.5919** | **−10.40%** | 1000 | ✅ matched |
| R6 | LineageFlow | pLDDT / scPerp | 42.07/17.88 | **43.20/13.96** | **+1.12/−3.92** | 1000 | ✅ NFE=10 caveat |

**Wave 203/204 fixes applied to R-level stats:**
- Wave 196 vanilla_scPerplexity p-value: 5.73e-16 → **1.14e-19** (3× tighter; sf not 1-cdf)
- Wave 195 R5c MNIST p-value: 1.3e-11 → **3.4e-318** (t=-419 underflow)
- Wave 203 P3 cluster-robust: k6 monotonic hard > medium > easy holds under cluster-robust SE

## Recent waves (Wave 198-205)

| Wave | Outcome | Status |
|---|---|---|
| 198 | Per-record + strata analysis found cancellation root cause (NOT effect-size bound) | DONE |
| 199-200 | LineageFlow N=1000 sweep BLOCKED-ON-DATA (CPU >40h/arm, torch 1.13.1 vs Blackwell sm_120) | BLOCKED |
| 201 | Eval pipeline 2-3× speedup via --workers-per-gpu + LPT + auto-detect | DONE |
| 202 | Found omegafold_py310 conda env (torch 2.14.0+cu130 + sm_120 supported); unblock sweep | DONE |
| 203 | Statistics audit fix: 2 p-value bugs + cluster-robust + 12-col standardized stats table + CLM-066/067 | DONE |
| 204 | Wave 196 vanilla scPerplexity defensive sf() fix in _paired_result; commit `72ba46e` | DONE |
| 205 | TPAMI submission data-preparation checklist (6 sections + 6-week schedule + 3 reviewer Q) | DONE |

**See `docs/tpami_submission_checklist.md` for full TPAMI prep plan.**

## Venue decision (revised 2026-09-21)

**Primary: TPAMI (IEEE Trans on Pattern Analysis and Machine Intelligence, CAS 1区 TOP)** — switched from EAAI after DeepSeek audit + standardization (12-col stats table, cluster-robust, Bonferroni). TPAMI accepts honest negatives as scope articulation; 6-week prep plan.

**Backups:** EAAI (Engineering Applications of AI) → PR (Pattern Recognition) → Neural Networks → TIP.

## 6-week TPAMI execution path

| Week | Focus | Deliverables | Wave |
|---:|---|---|---|
| **W1** | 数据审计 + bug 修复 (DONE) | Wave 203 + 204 + 205 (stats audit, p-fix, TPAMI checklist) | ✅ 203-205 |
| **W2** | N=1000 重跑 | LineageFlow + Kanzi + FlowMol3 + 2D + CIFAR + MNIST N=1000 on omegafold_py310 | 206 |
| **W3** | Ablation + 控制实验 | 5-arm per-component ablation + Fixed-threshold control + Random/uniform + 单 scheduler | 207 |
| **W4** | 效率 + Pareto | Wall-clock + memory + NFE accounting + Pareto frontier NFE {10...1000} | 208 |
| **W5** | 统计强化 + 标准化报告 | 12-col stats table 全面化 + Bonferroni families + Cluster-robust 全面化 + FDR-BH | 209 |
| **W6** | 复现包 + 限制披露 + 投前 final gates | GitHub repo + Zenodo data + Docker image + Honest negatives + tag v3.0 | 210 |

**Detailed schedule:** `todo/TPAMI-6-WEEK-PLAN.md`

## Out of scope (deferred)

- Mypy 988-error repair (camera-ready)
- Ruff 207 non-auto-fixable findings (camera-ready)
- FreqFlow + MM-FM integration (no upstream ckpt / no shipped adapter)
- Push to origin/main (user-gated; see `PUSH-READY.md`)