# TPAMI 6-Week Data-Preparation Plan (FlowA)

**Created:** 2026-09-21 (Wave 205)
**Anchor commit:** `72ba46e`
**Target venue:** IEEE TPAMI (double-column, 14 pp main text + unlimited refs + supplementary)
**Companion doc:** `docs/tpami_submission_checklist.md` (full 6-section checklist)

---

## Strategy

FlowA is a **training-free** re-inference framework for Flow Matching checkpoints. Three honest framings drive the TPAMI submission:

1. **Cross-budget NFE compression** (2.5-10× speedup, FID at NFE=50 ≈ baseline FID at NFE=500) is the primary headline
2. **Selection_ratio axis** is where paper quantities are load-bearing (0.8143 → 0.9896 via A2 + A4)
3. **Matched-NFE honest negative** on CIFAR-10 RF v4 (+24-31% framework regression) is actively disclosed as scope articulation

The 6-week plan executes the data prep in priority order: statistical rigor (W1 ✅) → N=1000 scale (W2) → mechanism validation (W3) → efficiency (W4) → statistical depth (W5) → reproducibility + submission (W6).

---

## Week 1 — Data audit + statistics standardization ✅ DONE

**Goal:** Fix statistical rigor issues identified by DeepSeek audit before any new data is collected.

### W1.1 — Fix 2 p-value reporting bugs ✅ DONE
- Wave 196 vanilla_scPerplexity: p=5.73e-16 → 1.14e-19 (3× tighter, sf not 1-cdf)
- Wave 195 R5c MNIST: p=1.3e-11 → 3.4e-318 (t=-419 underflow)
- Wave 204 P1 defensive sf() vs 1-cdf() in _paired_result (CLM-040 + CLM-061 updated)

### W1.2 — Cluster-robust analysis ✅ DONE
- Wave 203 P3: k6 cluster-robust verdict holds (monotonic hard > medium > easy)
- ICC estimated + N_eff derived
- Bonferroni alpha recomputed against N_clusters

### W1.3 — Standardized stats table ✅ DONE
- Wave 203 P4: 12-col audit-grade row format
- `docs/tables/wave203-p4-standardized-stats.md` covers all head claims

### W1.4 — TPAMI checklist ✅ DONE
- Wave 205: 6-section checklist + 6-week schedule + 3 reviewer Q
- `docs/tpami_submission_checklist.md`

**Deliverables:** CLM-066 (stats audit), CLM-067 (cluster-robust), v2.7-paper-stats-audit-fix tag pending

---

## Week 2 — N=1000 paired-record re-runs (Wave 206)

**Goal:** Every R-level cell has N=1000 paired records on the omegafold_py310 conda env (torch 2.14.0+cu130, sm_120 supported).

### W2.1 — LineageFlow N=1000 sweep on omegafold_py310 [CRITICAL]
- **Cells:** R1 HMMER + R6 foldability (4 Pfam families × 250 records)
- **Duration:** ~6-8h on 2× RTX PRO 6000 Blackwell
- **Output:** `verification_outputs/lineageflow_n1000_*_q4_2026.json`, per-record JSONL
- **Statistic:** 12-col audit row per cell

### W2.2 — Kanzi framework_inv_proj N=1000 re-run [CRITICAL]
- **Cell:** R2 Kanzi framework_inv_proj
- **Duration:** ~3-4h CPU (already-tuned CLI from Wave 127)
- **Output:** `/tmp/w206/kanzi_n1000_framework_paper_metrics.json`
- **Acceptance:** N=1000 zero-skipped

### W2.3 — FlowMol3 N=1000 re-run
- **Cell:** R3 FlowMol3 fg_dev
- **Duration:** ~3h GPU
- **Statistic:** paired-t + d_z, byte-stable σ=0

### W2.4 — 2D RF two_moons + eight_gaussians N=1000
- **Cells:** R4 + R5 (already have these; verify N=1000 byte-stable)

### W2.5 — CIFAR-10 RF + MNIST FM N=1000
- **Cells:** R3 CIFAR-10 + R5c MNIST FM (already N=1000; refresh per Wave 195 p-fix)

### W2.6 — FreqFlow MNIST N=1000 [MEDIUM]
- **Cell:** FreqFlow synthetic + real at N=1000
- **Statistic:** Bonferroni-significant in FreqFlow synthetic+real family

### W2.7 — Matched-NFE=50 CIFAR-10 RF v4 honest-negative curve [HIGH]
- **Cells:** framework + baseline at NFE ∈ {10,20,30,50,100,200,500} on CIFAR-10 RF v4
- **Purpose:** document +24-31% regression as first-class honest negative
- **Statistic:** Bonferroni-significant in *wrong direction* at α=0.007143

**Deliverable:** all R-level cells refreshed, N=1000 paired, byte-stable, 12-col stats table refreshed

---

## Week 3 — Ablation + control experiments (Wave 207)

**Goal:** Prove paper quantities are necessary for the improvement.

### W3.1 — 5-arm per-component ablation (A0 → A4) [HIGH]
- **Setup:** A0 baseline → A1 +BatchedTrajectoryRunner +CosineAnnealScheduler → A2 +CodimensionSheetScheduler → A3 +BoundedMergeOperator → A4 +EvidenceDrivenScheduler
- **Data:** 2D RF two_moons (3 seeds, 20 rounds, RK4); CIFAR-10 RF FID (NFE=50, 500 samples)
- **Metric:** W_2, selection_ratio, FID
- **Statistic:** ablation family k=4 α=0.0125; Cohen's d on (A4 − A0) selection_ratio axis

### W3.2 — Fixed-threshold scheduler control [HIGH]
- Replace CodimensionSheetScheduler with fixed n_cap=5 (no paper quantities)
- **Data:** R1 LineageFlow HMMER N=1000
- **Expected:** fixed-threshold should underperform adaptive → proves paper quantities necessary

### W3.3 — Random/uniform schedule control [HIGH]
- Replace scheduler with random schedule / uniform schedule
- **Data:** 2D RF + LineageFlow

### W3.4 — Single-scheduler module-level ablation [MEDIUM]
- Each scheduler enabled alone (only CosineAnneal / only CodimensionSheet / only EvidenceDriven / only BoundedMerge)
- Identify which scheduler is the selection_ratio driver

### W3.5 — Cosine-ramp halving ablation [MEDIUM]
- Document the cosine-ramp halving effect on effective NFE (per-scheduler NFE curve)
- **Data:** cross_model_nfe_curve_w171_q3_2026/

**Deliverable:** §5.3 mechanism validation + Figure S4 (ablation waterfall)

---

## Week 4 — Efficiency + Pareto frontier (Wave 208)

**Goal:** Report compute overhead, draw Pareto frontier plots.

### W4.1 — Wall-clock time per cell [HIGH]
- Measure framework vs baseline wall-clock at matched NFE=50
- **Metric:** seconds/sample, seconds/iteration

### W4.2 — Memory overhead [HIGH]
- Peak GPU memory, CPU memory, intermediate tensor size

### W4.3 — NFE accounting [HIGH]
- Per-component NFE consumption, total NFE ≤ baseline NFE (matched compute proof)

### W4.4 — Pareto frontier plots [HIGH]
- NFE ∈ {10, 20, 30, 50, 100, 200, 500, 1000} both arms
- **Output:** Figure 4 — FID vs NFE dual-arm + Pareto frontier
- **Statistic:** 95% CI on cross-budget ratio (bootstrap ≥1000 resamples)

### W4.5 — 2.5-10× speedup CI [HIGH]
- Re-derive "framework FID at NFE=50 ≈ baseline FID at NFE=500" with full NFE grid
- Range must be a CI, not point estimate

**Deliverable:** Figure 4 + supplementary Figure S2 + §5.5 efficiency section

---

## Week 5 — Statistical depth (Wave 209)

**Goal:** Bring every R-level cell to TPAMI-grade statistical depth.

### W5.1 — 12-col stats table for all head claims [HIGH]
- Refresh `docs/tables/wave203-p4-standardized-stats.md` with W2-W4 data
- Every cell: (n_paired, mean_diff, sd_diff, t, df, p, CI95_low, CI95_high, d_z, test_type, family, α_bonferroni, bonf_sig)

### W5.2 — Pre-defined Bonferroni families [HIGH]
- R-level: 6 cells → α=0.05/6=0.0083
- 4-arm head-to-head: 16 cells → α=0.05/16=0.003125
- Ablation: 5 arms → α=0.05/5=0.01
- Selection_ratio axis: 4 cells → α=0.05/4=0.0125
- FreqFlow: 2 cells → α=0.05/2=0.025

### W5.3 — Cluster-robust replication for all protein cells [HIGH]
- k6 + LineageFlow + Kanzi: cluster by Pfam family
- ICC + N_eff for each cell

### W5.4 — FDR-BH sensitivity analysis [MEDIUM]
- Benjamini-Hochberg FDR as exploratory sensitivity analysis on all R-level cells
- Compare Bonferroni vs FDR verdicts

### W5.5 — Cross-budget bootstrap CIs [HIGH]
- 95% CI on 2.5-10× speedup ratio (bootstrap ≥1000 resamples)
- 95% CI on cross-budget FID delta

### W5.6 — Power analysis refresh [MEDIUM]
- Wave 195 power analysis refresh with W2-W4 data
- Power curve per cell, N_eff for 80% power at d_z=0.5

**Deliverable:** §10.42 statistical rigor section expanded, 12-col stats table refreshed

---

## Week 6 — Reproducibility + submission prep (Wave 210)

**Goal:** Submission-ready package.

### W6.1 — GitHub repo public release [HIGH]
- MIT/Apache 2.0 license
- Public release of adaptive_reflow/ + tests/ + scripts/ + tools/

### W6.2 — Zenodo data deposit [HIGH]
- Per-record JSONL for k6 foldability + sc
- Per-cell CSVs (R1-R6 + ablation + Pareto)
- Theorem load-bearing JSON
- DOIs for each dataset

### W6.3 — Model weights public release [HIGH]
- FlowMol3 + CIFAR-10 RF + MNIST FM + LineageFlow + Kanzi + FreqFlow ckpts
- SHA-256 pin per ckpt

### W6.4 — Docker image [MEDIUM]
- omegafold_py310 conda env (torch 2.14.0+cu130 + sm_120)
- One-click reproduce all R-level cells

### W6.5 — Documentation refresh [HIGH]
- README.md: install + use + reproduce
- docs/paper-draft.md: final 14pp version
- CLAIMS.md: 55+ active claims, provenance per claim

### W6.6 — Honest negatives framing [HIGH]
- §5.7 Limitations: 5 reviewer-risk items actively pre-empted
- Matched-NFE=50 CIFAR-10 RF v4 honest-negative curve prominent in main text

### W6.7 — Final gates [HIGH]
- D.4: 33/33 PASS
- ruff: 0 findings (or 207 documented out-of-scope)
- pytest: 5155 passed / 196 skipped
- mkdocs build --strict: EXIT=0
- ckpt SHA-256: 4/4 PASS
- claims_consistency: No drift detected

### W6.8 — Tag v3.0-tpami-submission + push [HIGH]
- git tag -a v3.0-tpami-submission
- git push origin v3.0-tpami-submission (user-gated)
- Submit to TPAMI Editorial Manager

**Deliverable:** submission package ready for TPAMI upload

---

## Critical risks (per `RISK-REGISTER.md`)

| Risk | Severity | Mitigation |
|---|---|---|
| LineageFlow N=1000 sweep still slow on omegafold_py310 | HIGH | --workers-per-gpu N + LPT length-balanced sharding (Wave 201) |
| Matched-NFE honest negative undermines paper | LOW | TPAMI accepts honest negatives; frame as scope articulation |
| Cluster-robust kills k6 verdict | LOW | Wave 203 P3 already verified cluster-robust holds |
| 14/16 UNDERPOWERED cells in 4-arm head-to-head | MEDIUM | Explicit power analysis + honest disclosure |
| Mypy 988 errors | LOW | Camera-ready only; CLM-024 wording acknowledges |
| Push to origin blocked | LOW | User-gated; tag works regardless |

---

## Coordination with existing docs

- `docs/tpami_submission_checklist.md` — the 6-section companion checklist
- `docs/paper-draft.md` — main paper draft (Wave 194 MrFlow 5-section template)
- `docs/CLAIMS.md` — 55+ active claims ledger with provenance
- `docs/CONSOLIDATED_RESULTS.md` — 12-cell per-paper-claim FINAL status
- `docs/baseline-audit-report.md` — Wave-by-wave audit row ledger
- `verification_outputs/` — 264+ verification artifacts

---

## Execution kickoff

W1 ✅ done. **W2 starts next**: Wave 206 LineageFlow + Kanzi + FlowMol3 N=1000 re-runs on omegafold_py310 conda env.

Each wave runs as one ultracode workflow; agents emit JSON to `/tmp/w20N/agentN_result.json` for the next wave to read.