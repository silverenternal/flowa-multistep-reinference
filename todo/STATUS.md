# `todo/STATUS.md` — current execution status (2026-10-12, post-push governance refresh)

**Updated:** 2026-10-12 (post-push governance refresh — `origin/main` advanced from `0209002` to `fea137d`; the three manuscript-consistency sweeps `165df71` / `60c2441` / `fea137d` were pushed after user authorization, following the earlier `dc10cdb` manuscript-fix pass). **Prior 2026-10-11 update:** post-push governance refresh — `origin/main` advanced from `6036207` to `0209002`; the 192-commit backlog was pushed after the 147.1 MB `supplementary_bundle.zip` was purged from history + gitignored (GitHub 100 MB blob limit); CI gates re-verified green — pytest subset `5055 passed / 171 skipped / 50 deselected / 12 xfailed / 0 failed`, mypy 0 errors in 230 files, ruff 0, claims no-drift, mkdocs `--strict` exit 0; see [`docs/audit/governance-refresh-post-push.md`](../docs/audit/governance-refresh-post-push.md). Prior Wave 385 figure-addendum — §III architecture TikZ figure + §VII evidence-comparison figure added to `paper-A-final.{tex,md}`, PDF re-typeset to 11 pages; see [`docs/audit/wave385-figures.md`](../docs/audit/wave385-figures.md). Wave 384 project audit re-pointed the governance docs at HEAD `061682c` ≈ Wave 383; see [`docs/audit/wave384-project-audit.md`](../docs/audit/wave384-project-audit.md))

---

## Current state (2026-10-12)

- **HEAD commit:** `fea137d` ("docs(manuscript): fourth consistency sweep — capability groups, field name, §4.5 cell list"). **Pushed to `origin/main`** (user-authorized 2026-10-12; this push landed the three manuscript-consistency sweeps `165df71` / `60c2441` / `fea137d`, following the earlier `dc10cdb` manuscript-fix pass). Prior governance refresh was at `061682c` (≈ Wave 383); Waves 384–385 intervened (project audit + figure-addendum).
- **Tag:** `v3.1-tnnls-with-figure` / `v3.0-tnnls-ready` (local; the tag push remains user-gated per `tnnls_submission/README.md` §3)
- **Unpushed commits ahead of `origin/main`:** **0** (all commits through `fea137d` are on `origin/main`; the 192-commit backlog landed 2026-10-11 after the 147.1 MB supplementary-bundle blob was purged from local history, and the three manuscript-consistency sweeps landed 2026-10-12 — `origin/main` had never contained the backlog, so no force-push was needed)
- **D.4 byte-stable regression vectors:** **30/30 PASS** (verified via `pytest tests/test_d4_regression_vectors.py -q` at Wave 384 audit: `30 passed, 3 warnings in 7.56s`)
- **Pytest:** CI subset (`-m "not slow and not benchmark"`) = **5055 passed / 171 skipped / 50 deselected / 12 xfailed / 0 failed** (measured 2026-10-11, 8m39s; the earlier Wave 384 "25 failed / 5166 passed" figure reflected env/ordering-dependent failures that are now resolved). The README "5155 passed / 196 skipped" figure is the Wave 131 freeze baseline.
- **Ruff:** 0 findings in scope (`ruff check adaptive_reflow/ tests/ scripts/ tools/` → All checks passed!, Wave 384)
- **Mypy:** **0 errors in 230 files** (`mypy --strict adaptive_reflow`, measured 2026-10-11; the prior 988-error deferral was closed by the mypy batch — torch `nn.Module` override + stale `type: ignore` removal + ~24 real fixes)
- **mkdocs build --strict:** PASS (exit 0, ~29s at Wave 384)
- **ckpt SHA-256:** 4/4 PASS
- **claims_consistency:** PASS (61 active claims, 2 deprecated, 0 provisional; CLM-040 forced to PROVISIONAL by `Disputed by` citation; verified at Wave 384 audit)
- **9-gate:** ALL PASS (verified at Wave 339; re-verified at Wave 342–346; **re-verified at Wave 384**)
- **Venue:** TNNLS (IEEE Trans on Neural Networks and Learning Systems, CAS 1区 TOP) — switched from TPAMI at Wave 238 P3; `tnnls_submission/` package contains 8 files + supplementary bundle (`supplementary_bundle/`)
- **Paper:** `docs/drafts/paper-A-final.pdf` (**11 pages, 446895 bytes, SHA-256 `68b28acd...`**); title **"FlowA: Geometry-Aware State-Intervention Reformulation for Frozen Flow-Matching Checkpoints"** (renamed during Waves 366–383; two figures added in Wave 385; manuscript-review defect fixes 2026-10-11 + 2026-10-12 consistency pass); `.md` sha256 `9613cb01...`; `.tex` sha256 `99638eb0...`; evidence-comparison figure `docs/figures/fig9_cell_evidence_comparison.png` sha256 `4f3224bd...`

## R-level experimental claims (load-bearing for paper §7.3 / §10.6)

| # | Model | Metric | Baseline | Framework | Δ | N | Status |
|---|---|---|---:|---:|---:|---:|---|
| R1 | LineageFlow | HMMER hits | 158 | **342** | **+116%** | 1000 (single-seed seed=42) | ✅ PARTIAL / single-seed-disclosed (Wave 308 P1) |
| R2 | Kanzi | RMSD medium-tier | 0.6146 | **0.5919** | **−0.0227** | 1000 | ✅ SUPPORTED framework_WINS (Wave 218 P3) |
| R3 | CIFAR-10 RF v2 | FID | 218.87 | **122.18** | **−44.17%** | 1000 | ✅ NFE-averaged (Wave 109.C; smoke ckpt byte-stable per Wave 191; 3-seed BLOCKED at vendor level per CLM-068) |
| R4 | 2D Two Moons | W₂ | 0.5029 | **0.4663** | **−7.28%** | 1000 | ✅ matched (Wave 209 P6; R5a TIE_PERSISTS per Wave 337, n=3 paired-t below strict Bonferroni at `min_effect_size=0.01`) |
| R5 | 2D Eight Gaussians | W₂ | 0.6606 | **0.5919** | **−10.40%** | 1000 | ✅ matched (Wave 209 P6) |
| R5b | CIFAR-10 RF | FID matched-NFE=50 | 218.87 (v2 avg) / 454.39 (rounds1) | 122.18 (v2 avg) / rounds1-conditional WIN | n_rounds=1 ΔFID −1.60% to −2.53%; n_rounds≥2 REGRESSES | 200/1000 | ✅ SUPPORTED conditional on `n_rounds=1`; REGRESSES at `n_rounds≥2` (Wave 235 P1 R5b reversal; 2/4 schedulers WIN at N=1000 per Wave 247, NOT 4/4 as README N=200 headline implies) |
| R5c | MNIST FM | FID matched-NFE=50 | (smoke ckpt) / production ckpt 1.0× | framework WINS −28.43% smoke / +10.37% production | smoke-ckpt d_z=−13.175 (WINS); production-ckpt d_z per seed [+1.55, +1.33, +1.02] (baseline_WINS) | 1000 smoke / 200 per-seed × 3 seeds production | ✅ SUPPORTED smoke-ckpt / baseline-WINS production-ckpt (Wave 280 P direction-flip; both paths documented per Wave 341 §3.6) |
| R6 | LineageFlow | pLDDT / scPerp | 42.07/17.88 | **43.20/13.96** | **+1.12/−3.92** | 1000 | ✅ PARTIAL_SUPPORTED (Wave 233 P3 tier-aware d_z=+0.2235 + Wave 235 P3 grid-search d_z=+0.6467); ONLY headline cell using paper-quantity-driven `TierAwareCodimensionSheetScheduler` wrapping `CodimensionSheetScheduler`; 12/13 R-cells use `CosineAnnealScheduler`; hard tier d_z=+1.1895 SUPPORTED 3/3 seeds; easy tier REGRESSES 3/3 seeds (Wave 280 P R6 sweep) |

**Recent R-level updates (Wave 235 / 280 / 308 / 326 / 336 / 341 / 343):**
- Wave 196 vanilla_scPerplexity p-value: 5.73e-16 → **1.14e-19** (3× tighter; sf not 1-cdf)
- Wave 195 R5c MNIST p-value: 1.3e-11 → **3.4e-318** (t=-419 underflow; Wave 204 P1 defensive sf() fix)
- Wave 235 P1 **R5b reversal**: REGRESSES at all-n_rounds → conditional WIN at `n_rounds=1`, REGRESSES at `n_rounds≥2`
- Wave 280 P **R5c production-ckpt direction-flip**: smoke ckpt framework WINS −28.43% → production ckpt baseline WINS +10.37% per seed [+1.55, +1.33, +1.02]
- Wave 308 P1 **R1 demotion**: 3-seed-pooled STRONG d_z=+9.2 → PARTIAL / single-seed-disclosed (seeds 43/44 framework-fallback contamination invalidated the 3-seed pool; single-seed seed=42 d_z=+0.182 preserved)
- Wave 336 Tier 1+2 TNNLS execution: R6 live GPU N=1000 + R5c sweep + R5b mechanism + R1 3-seed + R3 N=1000
- Wave 341 deep audit: R5b 4/4 schedulers WIN → 2/4 schedulers WIN at N=1000 (README N=200 headline inconsistency surfaced; README fixed at Wave 342)
- Wave 343 BGV12/Villani bibliography + RMSPreserving disposition (paper §6.2 + §6.5)

**R-level verdict distribution (Wave 326 cross-doc-snapshot, 11 cells):**
- STRONG (main, 4): R2, R5b (n_rounds=1 conditional), R5c (smoke ckpt), R6 (tier-aware)
- TIE (main, 1): R5a (2D Two Moons paper R-level d_s=+0.460 at n=3, verified Wave 209 P6 n=7 + Wave 216 P2 n=10)
- PARTIAL/SUPP (6): R1 (single-seed-disclosed), R3 (3-seed BLOCKED), K1 (Wave 308 P2 §10 supplementary), K4+K5 (Wave 306), K7 (Wave 306)

## Recent waves (Wave 339-384)

| Wave | Outcome | Status |
|---|---|---|
| 339 | H8 5 abbreviations define + B6 3 cross-doc numbers align + 9-gate re-run + final PDF | DONE |
| 340 | README + docs/README + zh mirror update for Wave 339 final polish | DONE |
| 341 | Deep audit: data holes + doc organization + paper↔project alignment (READ-ONLY; 3 governance files identified as stale; 6 ORPHAN_SHA drifts flagged; 1 CRITICAL BGV12/Villani citation error + 4 unresolved discrepancies) | DONE |
| 342 | README Scheduler column + R5b 4/4 source-consistent fix + CLAIMS.md Status fields (16 mechanical additions) + 4 audit docs (cosine claim confirmed for paper 1, BGV12/Villani/RMSPreserving deferred to Wave 343) | DONE |
| 343 | Paper bibliography fix (BGV12 + Villani 2003) + RMSPreserving disposition + pdflatex rebuild (14 pages / 305270 bytes / SHA-256 `426cb5d3...`) + 5-gate | DONE |
| 344 | Package supplementary bundle (6 headline artifacts + headline-evidence + audit docs) + update MANIFEST SHA-256 ledger (paper v3.1 Wave 343) + 9-gate | DONE |
| 345 | Cross-doc stale references fixed (paper-flat-ieeetran.pdf → paper-A-final.pdf; paper-flattened-draft.md → paper-A-final.md) in 4 tnnls_submission/*.md + 9-gate + re-tag | DONE |
| 346 | README.md byte/page numbers updated (10 pages / 381510 bytes → 14 pages / 305270 bytes for paper-A-final.pdf) + 9-gate + re-tag v3.0-tnnls-ready | DONE |
| 347 | Governance refresh: `todo/STATUS.md` + `todo/RISK-REGISTER.md` (R-016..R-022) + `docs/audit/INDEX.md` (regenerated from 394-file on-disk layout) | DONE |
| 348–365 | TNNLS submission-package hardening: cross-doc GitHub-URL fixes (Wave 348, 282 paths), supplementary-bundle SHA refresh, per-cell reproducibility recipes (Waves 362–363), paper-polish gap closures (Wave 364), submission-readiness consolidation (Wave 365) | DONE |
| 366–371 | Manuscript polish: abstract compression (Wave 370, 1017 → 250 words, USER-EXPLICIT DESTRUCTIVE), theory de-wave (Wave 367 P5), mechanism synthesis (Wave 371) | DONE |
| 372–375 | **Manuscript restructure**: claim audit (Wave 372, removes unestablished residual-error rate + first-round FID sign bound), inference-dynamics positioning (Wave 373), typeset check (Wave 374), image-feedback path (Wave 375) | DONE |
| 379–383 | **Mechanism restructure + retitle**: mechanism synthesis (379), mechanism restructure (380), style polish (381), abstract/introduction polish (382), reformulation positioning + title → *"Geometry-Aware State-Intervention Reformulation"* + mechanism figure relocation (383); PDF re-typeset 14 → **10 pages** | DONE |
| **384** | **Project audit + documentation refresh** (this wave): gates re-verified ALL PASS at HEAD `061682c`; cross-doc drift D1–D8 documented; README/README.zh/docs/README + STATUS/INDEX/README refreshed to current title + 10-page build; paper internal cross-reference defects P1–P5 flagged; audit doc `docs/audit/wave384-project-audit.md` | DONE |
| **385** | **Figure-addendum**: added the §III architecture TikZ figure (three-domain split + four-port surface + five adapters + kernel band) and the §VII evidence-comparison figure (matplotlib PNG + committed renderer `tools/render_cell_evidence_figure.py`, ruff-clean, byte-stable); `.md` source synced (§3.2 ASCII architecture + §7.2 PNG reference); PDF re-typeset 10 → 11 pages (zero fatal errors, zero overfull hboxes); MANIFEST + governance page-count/SHA rows refreshed; audit doc `docs/audit/wave385-figures.md` | DONE |

**See `docs/audit/wave341-deep-audit.md` for the Wave 341 deep-audit finding trail and `docs/audit/wave384-project-audit.md` for the Wave 384 audit + documentation-drift trail.**

## Venue decision (revised 2026-10-11)

**Primary: TNNLS (IEEE Trans on Neural Networks and Learning Systems, CAS 1区 TOP)** — switched from TPAMI at Wave 238 P3 (`docs/audit/engineering/wave238-p3-journal-decision.md`); tags `v3.0-tnnls-ready` + `v3.1-tnnls-with-figure` (NOT pushed).

**Backups:** TIP (IEEE Trans on Image Processing) → PR (Pattern Recognition) → Neural Networks → EAAI.

## 6-week TNNLS execution path (revised 2026-09-25)

| Week | Focus | Deliverables | Wave |
|---:|---|---|---|
| **W1** | 数据审计 + bug 修复 (DONE) | Wave 203 + 204 + 205 + 341 (stats audit, p-fix, TPAMI checklist, deep audit) | ✅ 203-205, 341 |
| **W2** | N=1000 重跑 + TNNLS 切换 | LineageFlow + Kanzi + FlowMol3 + 2D + CIFAR + MNIST N=1000 on omegafold_py310; Wave 238 P3 TNNLS decision | ✅ 206-238 |
| **W3** | Ablation + 控制实验 + Tier-aware | 5-arm per-component ablation + Fixed-threshold control + Random/uniform + 单 scheduler + Wave 233 P3 TierAwareCodimensionSheetScheduler | ✅ 207-233 |
| **W4** | 效率 + Pareto + CUDA-graph | Wall-clock + memory + NFE accounting + Pareto frontier NFE {10...1000} + Wave 236 P2 CUDA-graph capture | ✅ 208-236 |
| **W5** | 统计强化 + 标准化报告 + Deep audit | 12-col stats table 全面化 + Bonferroni families + Cluster-robust 全面化 + FDR-BH + Wave 341 deep audit + Wave 235 R5b reversal + Wave 280 R5c flip + Wave 308 R1+K1 demotions | ✅ 209-308 |
| **W6** | 复现包 + 限制披露 + 投前 final gates + Submission freeze | GitHub repo + Zenodo data + Docker image + Honest negatives + tag v3.0-tnnls-ready (Wave 328, 338, 343, 346) + paper-A-final.pdf 14 pages + 9-gate + Wave 344 supplementary bundle + Wave 345 cross-doc fix | ✅ 326-346 |

## Out of scope (deferred)

- ~~Mypy 988-error repair (camera-ready)~~ — **CLOSED** (mypy --strict now 0 errors in 230 files)
- Ruff 207 non-auto-fixable findings (camera-ready)
- FreqFlow + MM-FM integration (no upstream ckpt / no shipped adapter)
- ~~Push to origin/main (user-gated; see `todo/PUSH-READY.md` and `wave325-push-execution.md`)~~ — **DONE 2026-10-11** (`origin/main` = `0209002`; 192-commit backlog pushed); **re-pushed 2026-10-12** (`origin/main` = `fea137d`; three manuscript-consistency sweeps)
- Wave 341 §6.5 RMSPreserving class reintroduction (deprecated back-compat alias; canonical name `EqualRmsCoordinateMixer` per ADR-0009)
- 3-seed R3 N=1000 paired sweep (BLOCKED at vendor level per CLM-068; smoke ckpt Wave 191 byte-stable is the load-bearing evidence)
- 3-seed R1 N=1000 (Wave 308 P1 invalidated by framework-fallback contamination on seeds 43/44)
- Live GPU R6 N=1000 (DEFERRED; counterfactual grid-search d_z=+0.6467 is the load-bearing evidence, not live GPU)
- R2 n=30 / n=100 paired-t replication (deferred; n=1000 single-seed SUPPORTED is load-bearing)
- R5a TIE_PERSISTS resolution (Wave 337: no n=30/n=100 confirmation; `|Δ|=0.00232` < `min_effect_size=0.01` floor)
- R5b 4/4 schedulers WIN at N=1000 (Wave 247 P3: 2/4 schedulers WIN, NOT 4/4; per-Wave 268 strict-clean rule, README fixed at Wave 342 not re-run)
