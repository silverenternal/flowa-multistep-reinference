# Project Audit Index

> **Topic-cluster map of all `docs/audit/*.md` files.** Generated as a Wave-275+ follow-up so reviewers can answer *"what does the project claim about X?"* by reading the cluster summary for X — without ever needing to grep `waveNNN-` filenames.

Audit files are organized into topic-cluster subdirectories (`docs/audit/<cluster>/waveNNN-*.md`). Wave filenames are preserved (so `git log --follow` continues to work and the per-wave audit trail is intact); only the directory has changed. The 9 `docs/audit/wave275-*.md` files are kept at the top level as Wave-275 active docs.

**Active surface** = one of the docs that are loaded by an external reviewer (`README.md`, `CLAIMS.md`, `CONSOLIDATED_RESULTS.md`, `baseline-audit-report.md`, `paper-final-neurips.md`, `paper-draft-anonymous.md`, `push-ready-summary.md`, `METRIC_LEDGER.md`, `INSIGHTS.md`, `ARCHITECTURE.md`, `cover-letter-tnnls.md`, `paper-draft.md`, `configs.md`, plus 9 other Tier-1 reviewer-facing docs). **Active** = a cluster file is cited from at least one active surface; **Historical** = not cited (preserved for the per-wave audit trail).

---

## How to use this index

1. **Pick the cluster that matches your question** (CIFAR-10, Kanzi, LineageFlow, Algorithm / Theorem 1, Statistical methodology, …). 2. **Read the cluster summary** (one paragraph each, written without wave numbers — describes what the project actually claims and where the evidence lives). 3. **Open the active files first** (these are cited by reviewer-facing docs and are the canonical references). 4. **Historical files** preserve the per-wave audit trail and are useful for tracing the evolution of a result; skip them on a first read.

---

## Cluster map

| Cluster | Topic | Files | Active | Historical |
|---------|-------|------:|------:|-----------:|
| `cifar` | CIFAR-10 RF (Rectified Flow on CIFAR-10) | 18 | 3 | 15 |
| `kanzi` | Kanzi (protein flow autoencoder) | 15 | 9 | 6 |
| `flowmol3` | FlowMol3 (molecular 3D flow matching) | 10 | 6 | 4 |
| `lineageflow` | LineageFlow (protein flow matching, HMMER + foldability + novelty) | 10 | 6 | 4 |
| `freqflow` | FreqFlow + MM-FM (frequency / multimodal flow) | 3 | 3 | 0 |
| `mnist` | MNIST FM (MNIST flow matching) | 1 | 0 | 1 |
| `brai` | BRAI perturbation (Bounded-Range Adaptive Integration) | 1 | 0 | 1 |
| `2d_toy` | 2D toy FM (two-dim flow matching, 8gaussian) | 3 | 0 | 3 |
| `self_flow` | Self-Flow ICML 2026 (image FM) | 0 | 0 | 0 |
| `hidream` | HiDream-I1 (image diffusion) | 0 | 0 | 0 |
| `graphbfn` | GraphBFN (graph Bayesian flow network) | 0 | 0 | 0 |
| `lumina` | Lumina-Image-2.0 (image generation) | 0 | 0 | 0 |
| `protbfn_abbfn` | ProtBFN-AbBFN (antibody / protein BFN) | 0 | 0 | 0 |
| `wan2_2` | Wan2.2 video (video diffusion) | 0 | 0 | 0 |
| `web_research` | Web research 2026 (FM literature surveys) | 5 | 2 | 3 |
| `engineering` | Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree) | 114 | 44 | 70 |
| `reproducibility` | Reproducibility (reproducibility-record, preregistration, reproduce-script) | 15 | 3 | 12 |
| `data_packaging` | Data packaging + manifest (sha256, csv, metric-ledger) | 29 | 10 | 19 |
| `push_state` | Push state (push-ready, freeze, release, submission) | 9 | 3 | 6 |
| `algorithm_4arm` | Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency) | 79 | 22 | 57 |
| `sweep_eval` | Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability) | 121 | 81 | 40 |
| `stats_method` | Statistical methodology (R5/R6, p-value, bonferroni, TOST) | 65 | 17 | 48 |
| `paper_claims` | Paper + claims (paper packaging, claim audit, paper-update) | 36 | 4 | 32 |
| `final_verify` | Final-verify (per-wave close-out, pre-push hygiene) | 74 | 21 | 53 |
| `governance` | Governance (scope, audit, gap, condition, placeholder, cross-cutting) | 45 | 17 | 28 |
| **TOTAL** | — | **653** | **251** | **402** |

---

## Cluster details

### Cluster: `cifar` — CIFAR-10 RF (Rectified Flow on CIFAR-10)

**Files: 18** (active: 3, historical: 15)

Rectified Flow on CIFAR-10: FID measurements, NFE-vs-FID ablation curves, matched-NFE GPU sweeps, RF-CIFAR checkpoint loader, ARM-filter and reference build, CPU smoke baselines. The cluster documents the project's image-axis validation at N=100/1000 and the framework's RF-CIFAR adapter reproducibility.

**Active (cited by ≥1 reviewer-facing surface):**

- `cifar/wave129-cifar-reference-availability.md` (372B, 2026-09-21)
- `cifar/wave146-cifar-v4-audit.md` (7.2KB, 2026-09-21)
- `cifar/wave206-p6-cifar-rf-v4-honest-negative-curve.md` (11.3KB, 2026-09-21)

**Historical (15 files, not cited by reviewer-facing surfaces):**

- `cifar-evaluation-corrections.md` (3.0KB, 2026-09-21)
- `cifar-fid-performance-audit.md` (887B, 2026-09-21)
- `rf-cifar-ablation-resume-2026-09-13.md` (988B, 2026-09-21)
- `rf-cifar-reference-gate-2026-09-13.md` (503B, 2026-09-21)
- `wave128-cifar-checkpoint-loader.md` (464B, 2026-09-21)
- `wave128-cifar-gpu-audit.md` (845B, 2026-09-21)
- `wave128-cifar-gpu-retry.md` (839B, 2026-09-21)
- `wave128-cifar-loader-retry2.md` (502B, 2026-09-21)
- `wave128-cifar-retry3-smoke.md` (419B, 2026-09-21)
- `wave129-cifar-small-sweep.md` (485B, 2026-09-21)
- `wave131-cifar-arm-filter.md` (548B, 2026-09-21)
- `wave131-cifar-reference-build.md` (320B, 2026-09-21)
- `wave131-cifar-small-sweep.md` (482B, 2026-09-21)
- `wave132-cifar-arm-fid-smoke.md` (517B, 2026-09-21)
- `wave191-p2-cifar10-n1000.md` (6.7KB, 2026-09-21)

---

### Cluster: `kanzi` — Kanzi (protein flow autoencoder)

**Files: 15** (active: 9, historical: 6)

KanziAdapter (protein flow autoencoder): RMSD-based decision metric, `project_out` / `project_out_inv` bridge, inverse-projection bug fixes, Kanzi N=30/1000 sweeps, framework-vs-baseline comparison, byte-stability regression, NFE-aware evaluation, and the Wave-91 latent→coord bridge that made the framework arm measurably different from baseline.

**Active (cited by ≥1 reviewer-facing surface):**

- `kanzi/wave100-kanzi-load-torch-fix.md` (5.0KB, 2026-09-21)
- `kanzi/wave120-kanzi-gpu-sweep.md` (30.0KB, 2026-09-21)
- `kanzi/wave157-kanzi-fix.md` (3.8KB, 2026-09-21)
- `kanzi/wave173-kanzi-nfe-bug.md` (7.7KB, 2026-09-21)
- `kanzi/wave175-p4-kanzi-full.md` (16.8KB, 2026-09-21)
- `kanzi/wave190-p2-kanzi-n30-sweep.md` (7.7KB, 2026-09-21)
- `kanzi/wave196-p3-kanzi-n1000-framework-inv-proj.md` (10.5KB, 2026-09-21)
- `kanzi/wave214-p1-kanzi-byte-stability-regression.md` (17.2KB, 2026-09-21)
- `kanzi/wave214-p2-kanzi-rerun.md` (7.1KB, 2026-09-21)

**Historical (6 files, not cited by reviewer-facing surfaces):**

- `kanzi-inv-proj-bridge-followup-2026-09-13.md` (4.0KB, 2026-09-21)
- `wave101-p0-kanzi-tools.md` (845B, 2026-09-21)
- `wave101-p1a-kanzi-runner.md` (675B, 2026-09-21)
- `wave109-a-kanzi-n1000.md` (14.0KB, 2026-09-21)
- `wave206-p2-kanzi-framework-n1000.md` (8.3KB, 2026-09-21)
- `wave225-p5-kanzi-tier-aware.md` (5.1KB, 2026-09-21)

---

### Cluster: `flowmol3` — FlowMol3 (molecular 3D flow matching)

**Files: 10** (active: 6, historical: 4)

FlowMol3 (molecular 3D flow matching): fg_dev metric, PoseBusters / xtb validation, FlowMol3 factory fix (force_mode=real), N=1000 sweeps, 1-mol drop investigation, DGL dependency fix, 3-seed re-runs, and the Wave-238/240/242 FlowMol3 direction decision sequence.

**Active (cited by ≥1 reviewer-facing surface):**

- `closure-flowmol3-sweep.md` (18.0KB, 2026-09-21)
- `flowmol3/wave109-c-flowmol3-n1000.md` (15.0KB, 2026-09-21)
- `flowmol3/wave206-p3-flowmol3-n1000.md` (7.9KB, 2026-09-21)
- `flowmol3/wave208-p2-flowmol3-dgl-fix-or-sanity.md` (11.1KB, 2026-09-21)
- `wave235-p4-flowmol3-3seed.md` (10.9KB, 2026-09-21)
- `wave242-p2-flowmol3-direction.md` (8.8KB, 2026-09-21)

**Historical (4 files, not cited by reviewer-facing surfaces):**

- `wave107-a2-flowmol3-drop.md` (16.7KB, 2026-09-21)
- `wave209-p5-cross-domain-flowmol3.md` (9.3KB, 2026-09-21)
- `wave238-p1-flowmol3-direction.md` (8.3KB, 2026-09-21)
- `wave240-p2-flowmol3-direction.md` (6.2KB, 2026-09-21)

---

### Cluster: `lineageflow` — LineageFlow (protein flow matching, HMMER + foldability + novelty)

**Files: 10** (active: 6, historical: 4)

LineageFlow (protein flow matching): HMMER foldability + novelty metrics, OmegaFold pLDDT + ESM-IF inverse folding, MMseqs2 + Pfam database provisioning, novelty sweep, cross-model NFE curves, N=30/1000 baselines, per-record CSV / strata reporting, restart-blend analysis, and the Wave-150 HMMER POC that established the audit infrastructure for the LineageFlow arm.

**Active (cited by ≥1 reviewer-facing surface):**

- `lineageflow-upstream-investigation.md` (13.5KB, 2026-09-21)
- `lineageflow/wave109-b-lineageflow-n1000-gpu.md` (10.2KB, 2026-09-21)
- `lineageflow/wave139-lineageflow-nfe-scan.md` (2.2KB, 2026-09-21)
- `lineageflow/wave150-lineageflow-hmmer-poc.md` (4.7KB, 2026-09-21)
- `lineageflow/wave175-p5-lineageflow-regression.md` (10.4KB, 2026-09-21)
- `lineageflow/wave190-p3-lineageflow-n30-sweep.md` (10.2KB, 2026-09-21)

**Historical (4 files, not cited by reviewer-facing surfaces):**

- `wave107-a3-lineageflow-n1000-gpu.md` (32.3KB, 2026-09-21)
- `wave200-p2-lineageflow-n1000-baseline-gpu-blocked.md` (9.3KB, 2026-09-21)
- `wave202-p5-lineageflow-per-record-and-strata.md` (7.7KB, 2026-09-21)
- `wave206-p1-lineageflow-n1000.md` (3.3KB, 2026-09-21)

---

### Cluster: `freqflow` — FreqFlow + MM-FM (frequency / multimodal flow)

**Files: 3** (active: 3, historical: 0)

FreqFlow + MM-FM (frequency / multimodal flow matching): honest-disclosure audit, N=1000 sweep, and MM-FM unblock investigation. The cluster is small because FreqFlow is a low-priority 2026 SOTA candidate.

**Active (cited by ≥1 reviewer-facing surface):**

- `mm-fm-unblock-investigation.md` (10.0KB, 2026-09-21)
- `freqflow/wave189-p3-freqflow-honest-disclosure.md` (12.6KB, 2026-09-21)
- `freqflow/wave206-p5-freqflow-n1000.md` (8.4KB, 2026-09-21)

---

### Cluster: `mnist` — MNIST FM (MNIST flow matching)

**Files: 1** (active: 0, historical: 1)

MNIST flow matching: a single Wave-191 N=1000 audit (with a Wave-250 provisional addendum). MNIST serves as a Tier-1 toy reproduction target alongside 2D toy FM.

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `wave191-p3-mnist-n1000.md` (9.4KB, 2026-09-21)

---

### Cluster: `brai` — BRAI perturbation (Bounded-Range Adaptive Integration)

**Files: 1** (active: 0, historical: 1)

BRAI perturbation: a single 2026-09-13 audit measuring perturbation magnitude for BRAI (Bounded-Range Adaptive Integration). BRAI is referenced as a framework scheduler-perturbation driver.

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `brai-perturbation-magnitude-2026-09-13.md` (676B, 2026-09-21)

---

### Cluster: `2d_toy` — 2D toy FM (two-dim flow matching, 8gaussian)

**Files: 3** (active: 0, historical: 3)

2D toy flow matching: two 2026-09-13 smoke audits (paper-beta-twodim + twodim-restart-sigma05) plus Wave-128 twodim CPU smoke. The cluster documents the canonical 2D FM toy target used for framework ablation.

**Historical (3 files, not cited by reviewer-facing surfaces):**

- `paper-beta-twodim-smoke-2026-09-13.md` (1.8KB, 2026-09-21)
- `twodim-restart-sigma05-smoke-2026-09-13.md` (1.7KB, 2026-09-21)
- `wave128-twodim-cpu-smoke.md` (962B, 2026-09-21)

---

### Cluster: `self_flow` — Self-Flow ICML 2026 (image FM)

**Files: 0** (active: 0, historical: 0)

Self-Flow (ICML 2026): no dedicated audit files in `docs/audit/`. Self-Flow is referenced as a 2026 image-FM SOTA candidate, but the project has no per-model audit for it.

---

### Cluster: `hidream` — HiDream-I1 (image diffusion)

**Files: 0** (active: 0, historical: 0)

HiDream-I1: no dedicated audit files. Referenced as a candidate SOTA image model but never integrated.

---

### Cluster: `graphbfn` — GraphBFN (graph Bayesian flow network)

**Files: 0** (active: 0, historical: 0)

GraphBFN: no dedicated audit files. Referenced as a candidate graph BFN but never integrated.

---

### Cluster: `lumina` — Lumina-Image-2.0 (image generation)

**Files: 0** (active: 0, historical: 0)

Lumina-Image-2.0: no dedicated audit files. Referenced as a candidate SOTA image model but never integrated.

---

### Cluster: `protbfn_abbfn` — ProtBFN-AbBFN (antibody / protein BFN)

**Files: 0** (active: 0, historical: 0)

ProtBFN-AbBFN: no dedicated audit files. Referenced as a candidate protein BFN but never integrated.

---

### Cluster: `wan2_2` — Wan2.2 video (video diffusion)

**Files: 0** (active: 0, historical: 0)

Wan2.2 video: no dedicated audit files. Referenced as a candidate video diffusion model but never integrated.

---

### Cluster: `web_research` — Web research 2026 (FM literature surveys)

**Files: 5** (active: 2, historical: 3)

Web research 2026 (FM literature surveys): four cross-cutting surveys of 2026 flow-matching literature — FM restart-blend, robust aggregators, saturation efficiency, and a general metrics + similar-projects survey. Used to ground the framework's design choices in published 2026 work.

**Active (cited by ≥1 reviewer-facing surface):**

- `web-research-2026.md` (42.4KB, 2026-09-21)
- `web-research-robust-aggregators-2026.md` (29.2KB, 2026-09-21)

**Historical (3 files, not cited by reviewer-facing surfaces):**

- `wave266-p2-grep-audit.md` (15.0KB, 2026-09-22)
- `web-research-fm-restart-2026.md` (30.5KB, 2026-09-21)
- `web-research-saturation-2026.md` (24.4KB, 2026-09-21)

---

### Cluster: `engineering` — Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree)

**Files: 114** (active: 44, historical: 70)

Engineering hygiene (CI, ruff, mkdocs, pytest, byte-stability): the Wave-101 four-layer review and follow-up fix waves covering layer-1 adapter stubs, layer-2 algorithm + tools, layer-3 pytest organization, layer-4 docs-config, ruff auto-fixes, mkdocs nav, pytest hygiene, working-tree cleanup, docstring audit, mypy fixes, security scan, and byte-stability regression. The cluster is the audit record of the project's engineering-quality push leading up to submission.

**Active (cited by ≥1 reviewer-facing surface):**

- `engineering-audit-2026-09-13.md` (4.9KB, 2026-09-21)
- `wave114-pytest-hygiene.md` (13.8KB, 2026-09-21)
- `wave117-working-tree-cleanup.md` (12.9KB, 2026-09-21)
- `engineering/wave124-inv-proj-final-fix.md` (19.4KB, 2026-09-21)
- `engineering/wave132-tier1-polish.md` (9.4KB, 2026-09-21)
- `engineering/wave133-number-consistency.md` (9.5KB, 2026-09-21)
- `engineering/wave134-tmp-migration.md` (8.5KB, 2026-09-21)
- `engineering/wave135-headline-evidence.md` (9.7KB, 2026-09-21)
- `engineering/wave137-doc-cleanup.md` (12.8KB, 2026-09-21)
- `engineering/wave140-docstring-audit.md` (9.0KB, 2026-09-21)
- `engineering/wave144-push-and-fix.md` (9.7KB, 2026-09-21)
- `engineering/wave145-todo-refactor.md` (9.8KB, 2026-09-21)
- `engineering/wave146-polish-execute.md` (10.1KB, 2026-09-21)
- `engineering/wave147-bridge-bug-design.md` (27.0KB, 2026-09-21)
- `engineering/wave147-followup.md` (8.4KB, 2026-09-21)
- `engineering/wave147-pdf-warning-fixes.md` (2.6KB, 2026-09-21)
- `engineering/wave147-primitive-cli-design.md` (9.4KB, 2026-09-21)
- `engineering/wave148-cli-pr-prep.md` (33.9KB, 2026-09-21)
- `engineering/wave148-followup.md` (8.8KB, 2026-09-21)
- `engineering/wave149-mypy-fix.md` (8.4KB, 2026-09-21)
- `engineering/wave149-pr1-application.md` (3.2KB, 2026-09-21)
- `engineering/wave154b-push.md` (5.1KB, 2026-09-21)
- `engineering/wave156-ruff-cleanup.md` (9.2KB, 2026-09-21)
- `engineering/wave156c-hmmer-collect.md` (7.8KB, 2026-09-21)
- `engineering/wave156c-push.md` (6.7KB, 2026-09-21)
- `engineering/wave158-hmmer-rederivation.md` (10.5KB, 2026-09-21)
- `engineering/wave158-push.md` (5.1KB, 2026-09-21)
- `engineering/wave158-scripts-ruff-cleanup.md` (7.8KB, 2026-09-21)
- `engineering/wave166b-eval.md` (11.4KB, 2026-09-21)
- `engineering/wave167-cli-verify.md` (11.8KB, 2026-09-21)
- `engineering/wave173-impl.md` (11.5KB, 2026-09-21)
- `engineering/wave173-p5-results.md` (10.5KB, 2026-09-21)
- `engineering/wave178-p5-gates.md` (8.0KB, 2026-09-21)
- `engineering/wave183-p1-setup.md` (15.1KB, 2026-09-21)
- `engineering/wave184-p1-setup.md` (8.7KB, 2026-09-21)
- `engineering/wave185-p4-plot.md` (9.4KB, 2026-09-21)
- `engineering/wave196-p4-table-aggregate.md` (12.3KB, 2026-09-21)
- `wave218-p1-fix-applied.md` (5.8KB, 2026-09-21)
- `engineering/wave233-p3-tier-aware.md` (11.5KB, 2026-09-21)
- `engineering/wave236-p3-integration.md` (13.1KB, 2026-09-21)
- `wave238-p2-cuda-graph-verify.md` (10.1KB, 2026-09-21)
- `engineering/wave238-p3-journal-decision.md` (12.0KB, 2026-09-21)
- `wave260-p1-gates-verify.md` (3.4KB, 2026-09-22)
- `engineering/wave262-p2-verify.md` (5.0KB, 2026-09-22)
- `wave310-r6-tier-aware-upgrade.md` (14.5KB, 2026-09-23)
- `wave311-d1-review.md` (20.4KB, 2026-09-23)
- `wave311-path-a-lemma-1.md` (19.1KB, 2026-09-23)
- `wave322-path-a-lemmas-2-3.md` (Wave 322 combined Lemma 2 + Lemma 3 audit doc, ACTIVE — closes Wave 311 PARTIAL-APPLY placeholders for CLM-086 + CLM-087)

**Historical (70 files, not cited by reviewer-facing surfaces):**

- `mkdocs-nav-current-audits-2026-09-13.md` (640B, 2026-09-21)
- `pytest-failure-analysis.md` (20.6KB, 2026-09-21)
- `engineering/wave101-review-layer4-docs-config.md` (11.3KB, 2026-09-21)
- `wave102-layer4-fix.md` (6.9KB, 2026-09-21)
- `wave103-layer1-fix.md` (8.1KB, 2026-09-21)
- `wave104-layer3-fix.md` (10.6KB, 2026-09-21)
- `wave105-layer2-fix.md` (6.8KB, 2026-09-21)
- `wave106-a-1-adapter-stubs.md` (28.9KB, 2026-09-21)
- `wave106-a3-honesty-gaps.md` (22.8KB, 2026-09-21)
- `wave106-a4-path-consistency.md` (19.7KB, 2026-09-21)
- `engineering/wave106-c3-fix-summary.md` (14.4KB, 2026-09-21)
- `wave107-a1-seeded-decoder.md` (15.4KB, 2026-09-21)
- `wave148-blocked-unified-narrative.md` (35.3KB, 2026-09-21)
- `wave148-bridge-pr-prep.md` (37.9KB, 2026-09-21)
- `wave155-push.md` (2.4KB, 2026-09-21)
- `wave157-push.md` (4.0KB, 2026-09-21)
- `wave157-tools-ruff-cleanup.md` (6.1KB, 2026-09-21)
- `wave161-push.md` (4.7KB, 2026-09-21)
- `wave162-push.md` (4.2KB, 2026-09-21)
- `wave163-mmseqs-install.md` (14.2KB, 2026-09-21)
- `wave163-push.md` (4.6KB, 2026-09-21)
- `wave164b-push.md` (3.8KB, 2026-09-21)
- `wave165-push.md` (2.6KB, 2026-09-21)
- `wave165b-push.md` (1.9KB, 2026-09-21)
- `wave166-push.md` (5.6KB, 2026-09-21)
- `wave166b-push.md` (7.5KB, 2026-09-21)
- `wave169-push.md` (3.4KB, 2026-09-21)
- `wave171-eval-refactor.md` (9.0KB, 2026-09-21)
- `wave171-push.md` (7.5KB, 2026-09-21)
- `wave175-finish.md` (9.6KB, 2026-09-21)
- `engineering/wave188-p5-ground-truth-corrections.md` (9.1KB, 2026-09-21)
- `wave193-p6-harmonisation.md` (10.9KB, 2026-09-21)
- `wave194-p4-five-fixes.md` (3.9KB, 2026-09-21)
- `wave209-p5-narrative-focus.md` (9.4KB, 2026-09-21)
- `wave210-p4-recommendations.md` (17.8KB, 2026-09-21)
- `wave213-p7-abstract-consistency.md` (10.9KB, 2026-09-21)
- `wave213-p8-signature-ordering.md` (8.8KB, 2026-09-21)
- `wave214-p0-stop-wave213.md` (11.1KB, 2026-09-21)
- `wave214-p5-downstream-update.md` (20.0KB, 2026-09-21)
- `wave215-p1-ruff-cleanup.md` (8.9KB, 2026-09-21)
- `wave215-p2-mkdocs-fix.md` (2.5KB, 2026-09-21)
- `wave215-p3-final-verification.md` (5.3KB, 2026-09-21)
- `wave217-p1-security-scan.md` (14.7KB, 2026-09-21)
- `wave218-p2-smoke.md` (5.9KB, 2026-09-21)
- `wave225-p8-pq-weight-tune.md` (7.3KB, 2026-09-21)
- `wave226-p4-consistency-check.md` (6.4KB, 2026-09-21)
- `wave227-p4-verify.md` (3.9KB, 2026-09-21)
- `wave228-p3-path-decision.md` (22.5KB, 2026-09-21)
- `wave232-p1-mkdocs-nav-fix.md` (4.0KB, 2026-09-21)
- `wave233-p2-verify.md` (3.8KB, 2026-09-21)
- `wave233-p7-integrate.md` (15.1KB, 2026-09-21)
- `wave234-p1-install.md` (6.5KB, 2026-09-21)
- `wave235-p5-integrate.md` (10.2KB, 2026-09-21)
- `wave237-p2-reverify.md` (1.9KB, 2026-09-21)
- `wave246-p1-metrics-py-commit.md` (6.1KB, 2026-09-22)
- `wave250-p5-wave191-provisional.md` (5.6KB, 2026-09-22)
- `wave252-p2-clean-readme.md` (2.9KB, 2026-09-22)
- `engineering/wave253-p3-number-verification.md` (36.8KB, 2026-09-22)
- `wave260-p2-update-claims.md` (8.0KB, 2026-09-22)
- `wave261-p1-inventory.md` (15.9KB, 2026-09-22)
- `wave264-p1-tldr-cleanup.md` (2.4KB, 2026-09-22)
- `wave266-p1-inventory.md` (22.1KB, 2026-09-22)
- `wave266-p3-moves.md` (10.5KB, 2026-09-22)
- `wave267-p2-readme-restructure.md` (6.7KB, 2026-09-22)
- `wave270-p1-ruff-code-fixes.md` (5.9KB, 2026-09-22)
- `wave270-p2-yml-fixes.md` (9.3KB, 2026-09-22)
- `wave270-p4-ruff-auto-fix.md` (3.3KB, 2026-09-22)
- `wave272-p2-ci-verify.md` (7.5KB, 2026-09-22)
- `wave273-p2-ci-verify.md` (6.8KB, 2026-09-22)
- `wave273-p3-optimize.md` (9.0KB, 2026-09-22)

---

### Cluster: `reproducibility` — Reproducibility (reproducibility-record, preregistration, reproduce-script)

**Files: 15** (active: 3, historical: 12)

Reproducibility: reproducibility-record audits, preregistration audit, reproduce-script / reproduce-directory / data-access investigations, experiment-setup design, cover-letter completion, and bilingual README. The cluster documents the project's submission-grade reproducibility infrastructure.

**Active (cited by ≥1 reviewer-facing surface):**

- `reproducibility/wave146-item4-tex-rewrite.md` (6.7KB, 2026-09-21)
- `wave152-reproduce-script.md` (9.4KB, 2026-09-21)
- `reproducibility/wave180-p3-comparison.md` (5.5KB, 2026-09-21)

**Historical (12 files, not cited by reviewer-facing surfaces):**

- `reproducibility/wave209-p8-experiment-setup.md` (15.7KB, 2026-09-21)
- `wave209-p8-reproducibility-checklist.md` (10.0KB, 2026-09-21)
- `reproducibility/wave211-p5-experiment-setup.md` (19.4KB, 2026-09-21)
- `wave211-p6-final-checklist.md` (16.9KB, 2026-09-21)
- `wave212-p1-profile-setup.md` (8.4KB, 2026-09-21)
- `wave213-p9-cover-letter-completion.md` (9.6KB, 2026-09-21)
- `wave224-p3-reproduce-verified.md` (5.9KB, 2026-09-21)
- `wave245-p3-wallclock-confirmation.md` (11.2KB, 2026-09-22)
- `wave245-p5-preregistration-audit.md` (9.7KB, 2026-09-22)
- `wave267-p1-reproduce-directory.md` (10.3KB, 2026-09-22)
- `wave267-p3-data-access.md` (8.2KB, 2026-09-22)
- `wave272-p1-bilingual-readme.md` (4.4KB, 2026-09-22)

---

### Cluster: `data_packaging` — Data packaging + manifest (sha256, csv, metric-ledger)

**Files: 29** (active: 10, historical: 19)

Data packaging + manifest: SHA-256 manifest audit, missing-CSVs investigation, metric-ledger, metrics-patch + validation, tier-aware independence, verification manifest, data-linkage plan, and metric-methodology. The cluster is the audit record of the data + manifest integrity pipeline.

**Active (cited by ≥1 reviewer-facing surface):**

- `ROOT_CAUSE_ANALYSIS.md` (16.1KB, 2026-09-21)
- `metric-methodology.md` (32.2KB, 2026-09-21)
- `data_packaging/wave108-implementation-plan.md` (49.2KB, 2026-09-21)
- `data_packaging/wave111-data-linkage-closure.md` (16.2KB, 2026-09-21)
- `data_packaging/wave111-data-linkage-plan.md` (28.5KB, 2026-09-21)
- `data_packaging/wave143-tier1-metric-alignment.md` (9.3KB, 2026-09-21)
- `data_packaging/wave151-pdf-warning-zero.md` (3.7KB, 2026-09-21)
- `data_packaging/wave156-hmmer-launch.md` (5.2KB, 2026-09-21)
- `data_packaging/wave166b-fasta-generation.md` (9.5KB, 2026-09-21)
- `data_packaging/wave173-fix-design.md` (16.5KB, 2026-09-21)

**Historical (19 files, not cited by reviewer-facing surfaces):**

- `wave106-c1-fix-summary.md` (14.8KB, 2026-09-21)
- `wave106-c4-fix-summary.md` (18.6KB, 2026-09-21)
- `data_packaging/wave149-framework-inv-proj-re-run.md` (5.7KB, 2026-09-21)
- `wave155-real-ckpt-validation.md` (6.9KB, 2026-09-21)
- `wave165-bl-distance.md` (7.5KB, 2026-09-21)
- `wave165-failure-modes.md` (8.5KB, 2026-09-21)
- `wave176-primary-metric.md` (8.2KB, 2026-09-21)
- `wave244-p1-manifest-sha256.md` (4.3KB, 2026-09-21)
- `wave244-p2-missing-csvs.md` (7.5KB, 2026-09-21)
- `data_packaging/wave244-p5-metrics-patch.md` (6.4KB, 2026-09-22)
- `wave245-p1-metrics-patch-validation.md` (9.7KB, 2026-09-22)
- `wave245-p2-tier-aware-independence.md` (12.2KB, 2026-09-22)
- `wave246-p2-tier-aware-independence-r1.md` (10.8KB, 2026-09-22)
- `wave252-p4-verification-manifest.md` (5.4KB, 2026-09-22)
- `data_packaging/wave253-p1-data-gathering.md` (59.8KB, 2026-09-22)
- `wave258-p1-complete-metrics-patch.md` (4.2KB, 2026-09-22)
- `wave259-p1-additional-metrics-patches.md` (4.1KB, 2026-09-22)
- `wave274-p7-manifest-sha.md` (1.5KB, 2026-09-22)
- `wave275-p2-metric-ledger.md` (5.9KB, 2026-09-22)

---

### Cluster: `push_state` — Push state (push-ready, freeze, release, submission)

**Files: 9** (active: 3, historical: 6)

Push state (push-ready, freeze, release, submission): release notes, Zenodo non-interactive deposit, submission polish / prep / package, changelog contact, code-release checklist, and submission-readiness verifications. The cluster tracks the actual push state of the project.

**Active (cited by ≥1 reviewer-facing surface):**

- `push_state/wave136-submission-polish.md` (9.7KB, 2026-09-21)
- `push_state/wave138-submission-prep.md` (18.4KB, 2026-09-21)
- `push_state/wave153-verify-submission-readiness.md` (10.4KB, 2026-09-21)

**Historical (6 files, not cited by reviewer-facing surfaces):**

- `todo-task-inventory-2026-09-13.md` (2.8KB, 2026-09-21)
- `wave106-a-2-audit.md` (34.2KB, 2026-09-21)
- `wave231-p5-submission-package.md` (8.4KB, 2026-09-21)
- `wave252-p1-release-notes.md` (3.9KB, 2026-09-22)
- `wave263-p3-changelog-contact.md` (10.2KB, 2026-09-22)
- `wave269-p2-zenodo-ni.md` (5.2KB, 2026-09-22)

---

### Cluster: `algorithm_4arm` — Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency)

**Files: 79** (active: 22, historical: 57)

Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency): the 4-arm ablation design, paper-quantity-driven β scheduler, A_g / B_g / C_g / e_ρ measurements and cross-adapter distributions, Theorem 1 power + self-contained statement, BL-bound tightness, unified-boundary framing, efficiency Pareto, wall-clock profiling, process profile, GPU-offload assessment, source-hotpaths analysis, and the speedup-semantics audit. This cluster is the core algorithmic-contribution audit trail.

**Active (cited by ≥1 reviewer-facing surface):**

- `algorithm-gap-investigation.md` (25.3KB, 2026-09-21)
- `wave125-algorithm-fixes.md` (25.4KB, 2026-09-21)
- `algorithm_4arm/wave159-push.md` (4.1KB, 2026-09-21)
- `algorithm_4arm/wave169-theory-audit.md` (22.8KB, 2026-09-21)
- `algorithm_4arm/wave175-p2-impl.md` (6.7KB, 2026-09-21)
- `algorithm_4arm/wave181-p2-eval.md` (17.5KB, 2026-09-21)
- `algorithm_4arm/wave181-p3-comparison.md` (3.2KB, 2026-09-21)
- `algorithm_4arm/wave182-p2-eval.md` (18.2KB, 2026-09-21)
- `algorithm_4arm/wave184-p4-aggregate.md` (9.7KB, 2026-09-21)
- `algorithm_4arm/wave185-p1-design.md` (17.7KB, 2026-09-21)
- `algorithm_4arm/wave195-p3-4arm-power.md` (14.6KB, 2026-09-21)
- `algorithm_4arm/wave195-p4-theorem1-power.md` (19.6KB, 2026-09-21)
- `wave196-p2-4arm-n30.md` (8.3KB, 2026-09-21)
- `algorithm_4arm/wave197-p2-progress.md` (6.8KB, 2026-09-21)
- `algorithm_4arm/wave208-p1-4arm-power-analysis.md` (8.3KB, 2026-09-21)
- `algorithm_4arm/wave208-p6-boundary-framing.md` (12.9KB, 2026-09-21)
- `algorithm_4arm/wave213-p6-repo-naming.md` (6.7KB, 2026-09-21)
- `wave229-p3-core-adapter-paper-quantities.md` (6.0KB, 2026-09-21)
- `wave230-p2-real-4arm-per-record.md` (10.3KB, 2026-09-21)
- `wave233-p6-wall-clock-opt.md` (10.9KB, 2026-09-21)
- `algorithm_4arm/wave236-p2-wallclock-fix.md` (12.2KB, 2026-09-21)
- `algorithm_4arm/wave262-p3-rerun.md` (8.8KB, 2026-09-22)

**Historical (57 files, not cited by reviewer-facing surfaces):**

- `algorithm-saturation-review.md` (40.0KB, 2026-09-21)
- `paper-quantity-beta-calibration-cpu-audit.md` (1.1KB, 2026-09-21)
- `wave101-review-layer1-adapters.md` (27.3KB, 2026-09-21)
- `wave101-review-layer2-algorithm-tools.md` (14.9KB, 2026-09-21)
- `wave123-8-adapter-shim-audit.md` (3.8KB, 2026-09-21)
- `wave170-fix-design.md` (22.5KB, 2026-09-21)
- `wave172b-push.md` (12.0KB, 2026-09-21)
- `wave187-p1-final-review.md` (16.7KB, 2026-09-21)
- `wave189-p4-theorem-load-bearing.md` (7.9KB, 2026-09-21)
- `wave194-p3-section-rewrite.md` (10.1KB, 2026-09-21)
- `wave208-p3-theorem-1-self-contained.md` (9.4KB, 2026-09-21)
- `wave208-p5-efficiency-pareto.md` (13.8KB, 2026-09-21)
- `wave208-p7-results-draft.md` (17.9KB, 2026-09-21)
- `wave209-p4-matched-compute-definition.md` (4.5KB, 2026-09-21)
- `wave209-p6-boundary-characterization.md` (11.0KB, 2026-09-21)
- `wave209-p6-easy-tier-mirror.md` (12.9KB, 2026-09-21)
- `wave209-p6-unified-boundary-format.md` (15.6KB, 2026-09-21)
- `wave209-p7-4arm-reframing.md` (7.6KB, 2026-09-21)
- `wave209-p7-signature-ordering.md` (6.6KB, 2026-09-21)
- `wave209-p8-f-side-actual-values.md` (12.5KB, 2026-09-21)
- `wave209-p8-final-checklist.md` (15.0KB, 2026-09-21)
- `wave210-p1-process-profile.md` (10.0KB, 2026-09-21)
- `wave210-p2-source-hotpaths.md` (17.8KB, 2026-09-21)
- `wave210-p3-gpu-offload-assessment.md` (19.7KB, 2026-09-21)
- `wave211-p1-efficiency-narrative.md` (19.9KB, 2026-09-21)
- `algorithm_4arm/wave211-p3-f-side-actual-values.md` (15.3KB, 2026-09-21)
- `wave211-p4-results-final.md` (21.7KB, 2026-09-21)
- `wave213-p1-speedup-semantics.md` (12.0KB, 2026-09-21)
- `wave213-p3-hmmer-mechanism.md` (9.5KB, 2026-09-21)
- `wave216-p3-4arm-uplift.md` (15.0KB, 2026-09-21)
- `wave217-p3-24x-fix.md` (10.8KB, 2026-09-21)
- `wave217-p4-companion-note.md` (8.5KB, 2026-09-21)
- `wave217-p5-reviewer-template.md` (10.1KB, 2026-09-21)
- `wave226-p1-a-g-values.md` (10.4KB, 2026-09-21)
- `wave226-p2-methods-paragraph.md` (6.1KB, 2026-09-21)
- `wave226-p3-variance-bound.md` (11.1KB, 2026-09-21)
- `wave227-p1-a-g-diagnostic.md` (15.4KB, 2026-09-21)
- `wave227-p2-floor-corrected.md` (13.9KB, 2026-09-21)
- `wave227-p3-methods-update.md` (9.6KB, 2026-09-21)
- `wave228-p1-4arm-per-record.md` (12.4KB, 2026-09-21)
- `wave228-p2-paper-quantities-distribution.md` (11.5KB, 2026-09-21)
- `wave228-p4-narrative-reframe.md` (13.6KB, 2026-09-21)
- `wave229-p1-4arm-per-record.md` (12.2KB, 2026-09-21)
- `wave229-p4-integration.md` (11.0KB, 2026-09-21)
- `wave229-p4-wall-clock-matched.md` (13.7KB, 2026-09-21)
- `wave230-p1-b-g-diagnosis.md` (10.5KB, 2026-09-21)
- `wave230-p3-l-emp-vs-a-g.md` (23.3KB, 2026-09-21)
- `wave231-p1-b-g-paper-fix.md` (8.5KB, 2026-09-21)
- `wave231-p2-real-4arm-paper-fix.md` (13.9KB, 2026-09-21)
- `wave231-p4-l-emp-cite.md` (5.6KB, 2026-09-21)
- `algorithm_4arm/wave246-p3-post-hoc-sensitivity.md` (9.7KB, 2026-09-22)
- `wave247-p3-r5b-n1000.md` (3.9KB, 2026-09-22)
- `wave247-p4-r5b-tier-aware.md` (12.6KB, 2026-09-22)
- `wave247-p5-r5b-nfe-sweep.md` (2.3KB, 2026-09-22)
- `wave250-p1-fix-pre-existing-bugs.md` (12.8KB, 2026-09-22)
- `wave251-p2-status-check.md` (10.1KB, 2026-09-22)
- `wave256-p4-split-docs.md` (6.9KB, 2026-09-22)

---

### Cluster: `sweep_eval` — Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability)

**Files: 121** (active: 81, historical: 40)

Sweep / eval / ablation: N=30/64/1000 sweeps, NFE curves, novelty + foldability sweeps, fair-comparison framework-vs-baseline, restart-blend analysis, K1-RC5 / K6-cluster sweeps, foldability propagation with workers-per-GPU, OmegaFold + ESM-IF smoke, mode-collapse analysis, module-ablation, and per-record CSV aggregation. The cluster is the audit record of the project's experimental infrastructure.

**Active (cited by ≥1 reviewer-facing surface):**

- `wave111-a-sweep-driver-audit.md` (34.9KB, 2026-09-21)
- `sweep_eval/wave111-b-config-scattering-audit.md` (19.3KB, 2026-09-21)
- `wave111-c-gpu-utilization-audit.md` (18.4KB, 2026-09-21)
- `wave113a6-base-class-refactor.md` (11.7KB, 2026-09-21)
- `wave115-bucket-d-regressions.md` (10.1KB, 2026-09-21)
- `sweep_eval/wave115-cuda-fix-sweep-recovery.md` (25.4KB, 2026-09-21)
- `wave116-cuda-fix-real-sweep.md` (21.2KB, 2026-09-21)
- `wave118-bucket-d-fixes.md` (11.1KB, 2026-09-21)
- `sweep_eval/wave121-shape-fix-resweep.md` (22.1KB, 2026-09-21)
- `sweep_eval/wave146-item1-ablation.md` (8.9KB, 2026-09-21)
- `sweep_eval/wave146-item2-hp-sweep.md` (7.7KB, 2026-09-21)
- `sweep_eval/wave150-rc4-ablation-fix.md` (5.6KB, 2026-09-21)
- `sweep_eval/wave151-headline-evidence-audit.md` (13.1KB, 2026-09-21)
- `sweep_eval/wave151-k1-rc5-preflight.md` (6.7KB, 2026-09-21)
- `sweep_eval/wave152-framework-synth-sweep.md` (10.5KB, 2026-09-21)
- `sweep_eval/wave152-k1-rc5-3arm-preflight.md` (8.4KB, 2026-09-21)
- `sweep_eval/wave154-hmmer-launch.md` (6.3KB, 2026-09-21)
- `sweep_eval/wave154-k1-rc5-launch.md` (8.2KB, 2026-09-21)
- `sweep_eval/wave154b-sweeps-collect.md` (6.2KB, 2026-09-21)
- `sweep_eval/wave156-k1-rc5-launch.md` (13.9KB, 2026-09-21)
- `sweep_eval/wave157-k1-rerun.md` (11.0KB, 2026-09-21)
- `sweep_eval/wave159-omegafold-provisioning.md` (14.3KB, 2026-09-21)
- `sweep_eval/wave160-k6-sweep-launch.md` (11.6KB, 2026-09-21)
- `sweep_eval/wave161-k6-verification.md` (8.8KB, 2026-09-21)
- `sweep_eval/wave163-novelty-sweep.md` (13.5KB, 2026-09-21)
- `sweep_eval/wave166-nfe-real.md` (10.3KB, 2026-09-21)
- `sweep_eval/wave166-novelty-diagnosis.md` (18.8KB, 2026-09-21)
- `sweep_eval/wave166-novelty-fix.md` (15.6KB, 2026-09-21)
- `sweep_eval/wave166-novelty-sweep-fixed.md` (14.0KB, 2026-09-21)
- `sweep_eval/wave166b-nfe-curve.md` (14.4KB, 2026-09-21)
- `sweep_eval/wave167-p2-fasta-generation.md` (8.9KB, 2026-09-21)
- `sweep_eval/wave167-p3-eval.md` (10.8KB, 2026-09-21)
- `sweep_eval/wave167-p4-nfe-curve.md` (12.0KB, 2026-09-21)
- `sweep_eval/wave168-eval.md` (11.3KB, 2026-09-21)
- `sweep_eval/wave168-fasta-generation.md` (7.4KB, 2026-09-21)
- `sweep_eval/wave168-nfe-flag.md` (7.9KB, 2026-09-21)
- `sweep_eval/wave168-p4-nfe-curve.md` (12.8KB, 2026-09-21)
- `sweep_eval/wave169-p1-pLDDT-inversion.md` (18.5KB, 2026-09-21)
- `sweep_eval/wave169-restart-blend-analysis.md` (12.9KB, 2026-09-21)
- `sweep_eval/wave169-validation-experiment.md` (17.3KB, 2026-09-21)
- `sweep_eval/wave170-fair-fasta-generation.md` (10.6KB, 2026-09-21)
- `sweep_eval/wave170-n-rounds-flag.md` (6.5KB, 2026-09-21)
- `sweep_eval/wave173-p6-paper.md` (5.5KB, 2026-09-21)
- `sweep_eval/wave173-restart-over-application.md` (11.9KB, 2026-09-21)
- `sweep_eval/wave174-cross-model-nfe-curve.md` (9.1KB, 2026-09-21)
- `sweep_eval/wave174-dispatch-verification.md` (12.2KB, 2026-09-21)
- `sweep_eval/wave174-eval.md` (13.3KB, 2026-09-21)
- `sweep_eval/wave174-gpu-verify.md` (9.7KB, 2026-09-21)
- `sweep_eval/wave174-p3-fasta-ladder.md` (6.2KB, 2026-09-21)
- `sweep_eval/wave175-p1-design.md` (10.7KB, 2026-09-21)
- `sweep_eval/wave175-p3-sanity.md` (9.5KB, 2026-09-21)
- `sweep_eval/wave178-finish.md` (5.5KB, 2026-09-21)
- `sweep_eval/wave178-p1-design.md` (21.9KB, 2026-09-21)
- `sweep_eval/wave178-p6-e2e-eval.md` (7.8KB, 2026-09-21)
- `sweep_eval/wave179-p1-design.md` (11.3KB, 2026-09-21)
- `sweep_eval/wave179-p2-generate.md` (10.3KB, 2026-09-21)
- `sweep_eval/wave179-p4-aggregate.md` (16.4KB, 2026-09-21)
- `sweep_eval/wave179-p5-plot.md` (7.7KB, 2026-09-21)
- `sweep_eval/wave180-p1-setup.md` (10.2KB, 2026-09-21)
- `sweep_eval/wave180-p2-eval.md` (13.8KB, 2026-09-21)
- `sweep_eval/wave181-p1-setup.md` (13.2KB, 2026-09-21)
- `sweep_eval/wave182-p1-setup.md` (14.8KB, 2026-09-21)
- `sweep_eval/wave182-p3-comparison.md` (8.5KB, 2026-09-21)
- `sweep_eval/wave183-p2-generate.md` (20.0KB, 2026-09-21)
- `sweep_eval/wave183-p3-eval.md` (18.3KB, 2026-09-21)
- `sweep_eval/wave183-p4-aggregate.md` (7.0KB, 2026-09-21)
- `sweep_eval/wave184-p2-generate.md` (10.7KB, 2026-09-21)
- `sweep_eval/wave184-p3-eval.md` (9.0KB, 2026-09-21)
- `sweep_eval/wave185-p2-empirical-bl.md` (11.9KB, 2026-09-21)
- `sweep_eval/wave185-p3-tightness.md` (15.2KB, 2026-09-21)
- `sweep_eval/wave186-p1-setup.md` (5.1KB, 2026-09-21)
- `sweep_eval/wave186-p3-eval.md` (11.9KB, 2026-09-21)
- `sweep_eval/wave186-p4-aggregation.md` (13.6KB, 2026-09-21)
- `sweep_eval/wave189-p2-post-cd70821-2d-sweep.md` (7.9KB, 2026-09-21)
- `sweep_eval/wave197-p1-investigation.md` (12.2KB, 2026-09-21)
- `sweep_eval/wave201-p2-foldability-sc-workers-per-gpu.md` (3.9KB, 2026-09-21)
- `sweep_eval/wave201-p3-run-foldability-propagate-workers-per-gpu.md` (5.9KB, 2026-09-21)
- `wave203-p3-k6-cluster-robust.md` (7.8KB, 2026-09-21)
- `sweep_eval/wave206-w2-n1000-reruns.md` (21.6KB, 2026-09-21)
- `sweep_eval/wave208-p4-cross-adapter-ablation.md` (11.9KB, 2026-09-21)
- `sweep_eval/wave262-p1-revert-all.md` (5.7KB, 2026-09-22)

**Historical (40 files, not cited by reviewer-facing surfaces):**

- `wave106-c2-fix-summary.md` (13.6KB, 2026-09-21)
- `wave110-c-sweep-results.md` (7.2KB, 2026-09-21)
- `wave110-plan.md` (9.5KB, 2026-09-21)
- `wave155-make-adapter-fix.md` (5.6KB, 2026-09-21)
- `wave163-novelty-investigation.md` (14.6KB, 2026-09-21)
- `wave165-novelty-canonical.md` (16.6KB, 2026-09-21)
- `wave165b-ablation.md` (6.3KB, 2026-09-21)
- `wave165b-nfe-curve.md` (11.2KB, 2026-09-21)
- `wave165b-novelty-canonical.md` (16.0KB, 2026-09-21)
- `wave170-fair-comparison.md` (8.5KB, 2026-09-21)
- `wave170-mechanism-analysis.md` (26.8KB, 2026-09-21)
- `wave171-cross-model-nfe-curve.md` (17.9KB, 2026-09-21)
- `wave171-mode-collapse-analysis.md` (8.4KB, 2026-09-21)
- `wave172b-cross-model-nfe-curve.md` (16.2KB, 2026-09-21)
- `wave172b-eval.md` (13.4KB, 2026-09-21)
- `wave172b-fasta-generation.md` (9.3KB, 2026-09-21)
- `wave177-shape-composite-fixes.md` (7.9KB, 2026-09-21)
- `wave186-p2-generate.md` (13.2KB, 2026-09-21)
- `wave190-p1-sweep-driver-extension.md` (6.9KB, 2026-09-21)
- `wave193-p7-pdf-regen.md` (6.2KB, 2026-09-21)
- `wave202-p2-omegafold-esmif-smoke-test.md` (8.5KB, 2026-09-21)
- `wave204-p4-per-record-csv-commit.md` (8.1KB, 2026-09-21)
- `wave209-p1-module-ablation.md` (11.3KB, 2026-09-21)
- `wave209-p2-ci-emphasis.md` (10.6KB, 2026-09-21)
- `wave209-p3-sf-path-confirmation.md` (3.6KB, 2026-09-21)
- `wave212-p5-memory-trace.md` (15.9KB, 2026-09-21)
- `wave213-p5-memory-structure.md` (17.9KB, 2026-09-21)
- `wave218-p3-n1000-verified.md` (7.3KB, 2026-09-21)
- `wave219-p1-sweep-launched.md` (4.4KB, 2026-09-21)
- `wave224-p1-killed-orphans.md` (5.1KB, 2026-09-21)
- `wave225-p0-baseline.md` (2.3KB, 2026-09-21)
- `wave225-p4-k6-tier-aware.md` (5.5KB, 2026-09-21)
- `wave229-p5-molecule-image-per-record.md` (7.1KB, 2026-09-21)
- `wave231-p3-wording-fix.md` (6.5KB, 2026-09-21)
- `wave252-p3-reproduce.md` (2.4KB, 2026-09-22)
- `wave254-p3-fix-r4-r5.md` (7.9KB, 2026-09-22)
- `sweep_eval/wave255-p1-restore-r4-r5.md` (9.2KB, 2026-09-22)
- `sweep_eval/wave255-p5-doc-consolidation.md` (20.2KB, 2026-09-22)
- `wave256-p3-validation-language.md` (6.5KB, 2026-09-22)
- `wave264-p2-table-fix.md` (9.4KB, 2026-09-22)

---

### Cluster: `stats_method` — Statistical methodology (R5/R6, p-value, bonferroni, TOST)

**Files: 65** (active: 17, historical: 48)

Statistical methodology (R5/R6, p-value, bonferroni, TOST, Jonckheere-Terpstra, BF01, meta-analysis, non-inferiority, power-spec): the R2/R3/R5a/R5b/R6 uplift series, bootstrap + cross-seed + tier-aware stats, R5b Heun upgrade + multi-seed + NFE-sweep + reduced-rounds, R6 control + reframe + re-audit + mean-diff fix, Bonferroni families, statistical-power analysis, post-hoc sensitivity, TOST sensitivity, JT-hypothesis justification, meta-analysis, and BF01 sensitivity. This cluster is the audit record of the project's statistical rigor.

**Active (cited by ≥1 reviewer-facing surface):**

- `stats_method/wave149-pr2-application.md` (17.7KB, 2026-09-21)
- `wave162-audit.md` (22.7KB, 2026-09-21)
- `stats_method/wave195-p1-power-spec.md` (30.2KB, 2026-09-21)
- `stats_method/wave195-p2-r-level-power.md` (19.0KB, 2026-09-21)
- `stats_method/wave204-p1-r5c-underflow-fix.md` (5.4KB, 2026-09-21)
- `stats_method/wave206-p4-r-level-refresh.md` (7.6KB, 2026-09-21)
- `stats_method/wave216-p1-r3-uplift.md` (12.1KB, 2026-09-21)
- `stats_method/wave225-p3-r3-cross-seed.md` (5.7KB, 2026-09-21)
- `wave233-p5-r5b-fix.md` (10.2KB, 2026-09-21)
- `wave234-p2-tost.md` (7.9KB, 2026-09-21)
- `wave234-p3-jonckheere.md` (6.8KB, 2026-09-21)
- `wave234-p4-bf01.md` (6.4KB, 2026-09-21)
- `wave234-p5-meta-analysis.md` (9.6KB, 2026-09-21)
- `stats_method/wave234-p6-non-inferiority.md` (3.7KB, 2026-09-22)
- `stats_method/wave235-p1-r5b-fix.md` (11.5KB, 2026-09-21)
- `wave235-p2-r2-uplift.md` (7.6KB, 2026-09-21)
- `stats_method/wave235-p3-r6-uplift.md` (8.5KB, 2026-09-21)

**Historical (48 files, not cited by reviewer-facing surfaces):**

- `wave101-layer2-p1c-sota-argparse.md` (1.5KB, 2026-09-21)
- `wave101-layer3-p0-test-organization.md` (1.1KB, 2026-09-21)
- `wave101-layer3-p1a-protocol-tests.md` (1.2KB, 2026-09-21)
- `wave101-layer3-p1b-large-adapter-tests.md` (1003B, 2026-09-21)
- `wave101-layer3-p2a-real-ckpt-eval.md` (720B, 2026-09-21)
- `wave101-review-layer3-tests.md` (11.3KB, 2026-09-21)
- `wave105-p2b-extra-r2-merge.md` (3.6KB, 2026-09-21)
- `wave204-p3-standardized-stats-superset.md` (11.0KB, 2026-09-21)
- `wave209-p2-bonferroni-families.md` (11.5KB, 2026-09-21)
- `wave209-p2-stats-comprehensive.md` (11.2KB, 2026-09-21)
- `wave209-p3-power-analysis-table.md` (4.1KB, 2026-09-21)
- `wave209-p6-r5a-extension.md` (8.7KB, 2026-09-21)
- `wave209-p6-r5b-deep-analysis.md` (14.0KB, 2026-09-21)
- `wave212-p2-r5b-timing.md` (10.5KB, 2026-09-21)
- `wave212-p3-r6-control.md` (12.2KB, 2026-09-21)
- `wave212-p4-cprofile-analysis.md` (6.0KB, 2026-09-21)
- `wave216-p2-r5a-uplift.md` (9.2KB, 2026-09-21)
- `wave216-p4-r6-uplift.md` (7.4KB, 2026-09-21)
- `wave219-p4-stats-clm.md` (7.3KB, 2026-09-21)
- `wave219-p6-path-sanitize.md` (5.6KB, 2026-09-21)
- `wave225-p1-r5a-integrity.md` (10.1KB, 2026-09-21)
- `wave225-p2-r3-bootstrap.md` (2.9KB, 2026-09-21)
- `wave225-p6-r6-reframing.md` (7.8KB, 2026-09-21)
- `wave225-p7-r5b-reduced-rounds.md` (10.4KB, 2026-09-21)
- `wave225-p9-r5b-matched-eff-nfe.md` (11.9KB, 2026-09-21)
- `wave233-p4-r5a-expanded.md` (9.2KB, 2026-09-21)
- `wave234-p7-integrate.md` (7.3KB, 2026-09-21)
- `wave246-p3-bf01-sensitivity.md` (4.7KB, 2026-09-22)
- `wave246-p3-jt-hypothesis-justification.md` (7.5KB, 2026-09-22)
- `wave246-p3-tost-sensitivity.md` (3.9KB, 2026-09-22)
- `wave247-p1-r5b-history.md` (26.4KB, 2026-09-22)
- `wave247-p2-r5b-multiseed.md` (6.3KB, 2026-09-22)
- `wave248-p1-r5b-heun-upgrade.md` (7.4KB, 2026-09-22)
- `stats_method/wave254-p1-fix-r2-numbers.md` (9.4KB, 2026-09-22)
- `wave254-p2-fix-r3-per-arm.md` (8.0KB, 2026-09-22)
- `wave254-p4-fix-r6-mean-diff.md` (4.3KB, 2026-09-22)
- `stats_method/wave255-p2-r2-re-audit.md` (14.1KB, 2026-09-22)
- `stats_method/wave255-p3-r3-re-audit.md` (19.0KB, 2026-09-22)
- `stats_method/wave255-p4-r6-re-audit.md` (22.5KB, 2026-09-22)
- `wave256-p1-r2-paper-number-fix.md` (7.3KB, 2026-09-22)
- `wave263-p1-r4-r5-numerical-stability.md` (7.3KB, 2026-09-22)
- `wave263-p2-r2-r3-eaai.md` (8.5KB, 2026-09-22)
- `wave265-p1-r1-p-value.md` (2.7KB, 2026-09-22)
- `wave265-p2-quick-start-r3-row.md` (4.6KB, 2026-09-22)
- `wave265-p3-r2-format.md` (7.7KB, 2026-09-22)
- `wave268-p1-r4-r5-w2.md` (7.1KB, 2026-09-22)
- `wave269-p1-r6-metric.md` (9.8KB, 2026-09-22)
- `wave273-p1-readme-state.md` (11.8KB, 2026-09-22)

---

### Cluster: `paper_claims` — Paper + claims (paper packaging, claim audit, paper-update)

**Files: 36** (active: 4, historical: 32)

Paper + claims (paper packaging, claim audit, paper-update): paper draft + rewrite + presentation + walkthrough + polish + PDF + experimental-clarity + figure-metric audits, six-main-claims audits, claim-close, claim-correction, CLM-053/054/057/058/062 audits, cross-claim consistency, paper-number fix, paper-full audit, validation language, and paper-update finalization. The cluster tracks the paper's content audit history.

**Active (cited by ≥1 reviewer-facing surface):**

- `paper_claims/wave109-d-paper-package-update.md` (10.8KB, 2026-09-21)
- `paper_claims/wave144-agent3-pdf-generation.md` (6.8KB, 2026-09-21)
- `paper_claims/wave150-pdf-warning-reduction.md` (3.2KB, 2026-09-21)
- `paper_claims/wave214-p3-clm057-update.md` (13.3KB, 2026-09-21)

**Historical (32 files, not cited by reviewer-facing surfaces):**

- `paper-p6-wave-history-supplementary.md` (19.7KB, 2026-09-21)
- `wave107-a4-paper-presentation.md` (33.8KB, 2026-09-21)
- `wave164b-paper-review.md` (12.9KB, 2026-09-21)
- `paper_claims/wave188-p6-paper-polish-audit.md` (6.9KB, 2026-09-21)
- `wave192-p3-pdf-conversion.md` (7.3KB, 2026-09-21)
- `wave193-p5-paper-cut.md` (6.3KB, 2026-09-21)
- `wave194-p5-pdf-regen.md` (4.7KB, 2026-09-21)
- `wave197-p4-paper-clm-update.md` (13.6KB, 2026-09-21)
- `wave209-p7-six-main-claims.md` (8.4KB, 2026-09-21)
- `wave211-p2-six-main-claims.md` (16.9KB, 2026-09-21)
- `wave213-p2-claim2-correction.md` (9.3KB, 2026-09-21)
- `wave213-p4-six-claims-audit.md` (21.1KB, 2026-09-21)
- `wave214-p4-paper-propagation-deferred.md` (18.8KB, 2026-09-21)
- `wave218-p5-paper-updated.md` (8.9KB, 2026-09-21)
- `wave219-p5-paper-updated.md` (7.4KB, 2026-09-21)
- `wave242-p3-paper-update.md` (12.4KB, 2026-09-21)
- `wave244-p3-abstract-trim.md` (9.0KB, 2026-09-21)
- `wave244-p4-paper-pdf.md` (10.7KB, 2026-09-21)
- `wave245-p4-paper-experimental-clarity.md` (9.4KB, 2026-09-22)
- `paper_claims/wave246-p4-paper-updates.md` (20.2KB, 2026-09-22)
- `wave249-p1-clm053-audit.md` (20.8KB, 2026-09-22)
- `wave249-p2-clm057-058-audit.md` (23.3KB, 2026-09-22)
- `wave249-p3-clm054-audit.md` (20.5KB, 2026-09-22)
- `wave249-p4-clm062-wave191-audit.md` (22.3KB, 2026-09-22)
- `wave249-p5-cross-clm-consistency.md` (35.2KB, 2026-09-22)
- `wave250-p2-clm054-add.md` (7.0KB, 2026-09-22)
- `wave250-p3-clm057-058-add.md` (14.4KB, 2026-09-22)
- `wave250-p4-clm062-add.md` (11.6KB, 2026-09-22)
- `wave251-p1-clm053-not-ok-decision.md` (12.2KB, 2026-09-22)
- `wave256-p2-full-paper-audit.md` (13.4KB, 2026-09-22)
- `wave262-p4-paper-update.md` (10.1KB, 2026-09-22)
- `wave274-p4-paper-pdf-blocked.md` (2.2KB, 2026-09-22)

---

### Cluster: `final_verify` — Final-verify (per-wave close-out, pre-push hygiene)

**Files: 74** (active: 21, historical: 53)

Final-verify (per-wave close-out, pre-push hygiene): per-wave final synthesis, final-decision, final-commit, final-audit, final-state, final-gate-verification, final-pre-push, final-paper-update, pre-freeze + pre-push hygiene, status-reconciliation, status-reality checks, finish-line + finish-engineering + close-remaining waves, and the Wave-101..Wave-275 `*-final-verify.md` files. The cluster is the project's per-wave acceptance gate record.

**Active (cited by ≥1 reviewer-facing surface):**

- `todo-status-reconciliation-2026-09-13.md` (432B, 2026-09-21)
- `final_verify/wave101-status-reconciliation-2026-09-13.md` (467B, 2026-09-21)
- `final_verify/wave108-final-synthesis.md` (15.7KB, 2026-09-21)
- `wave113-final-synthesis.md` (13.7KB, 2026-09-21)
- `wave119-finish-engineering-debt.md` (25.5KB, 2026-09-21)
- `final_verify/wave122-close-remaining-debt.md` (26.9KB, 2026-09-21)
- `final_verify/wave127-finish-line.md` (18.9KB, 2026-09-21)
- `final_verify/wave131-pre-freeze-hygiene.md` (15.3KB, 2026-09-21)
- `final_verify/wave149-close.md` (12.8KB, 2026-09-21)
- `final_verify/wave150-close.md` (7.3KB, 2026-09-21)
- `final_verify/wave151-close.md` (9.9KB, 2026-09-21)
- `final_verify/wave152-close.md` (12.4KB, 2026-09-21)
- `final_verify/wave153-close.md` (14.2KB, 2026-09-21)
- `final_verify/wave154b-close.md` (20.3KB, 2026-09-21)
- `final_verify/wave155-close.md` (11.2KB, 2026-09-21)
- `final_verify/wave156c-close.md` (19.4KB, 2026-09-21)
- `final_verify/wave157-close.md` (11.0KB, 2026-09-21)
- `final_verify/wave158-close.md` (19.7KB, 2026-09-21)
- `final_verify/wave159-close.md` (15.8KB, 2026-09-21)
- `final_verify/wave160-close.md` (18.8KB, 2026-09-21)
- `final_verify/wave225-p10-final-synthesis.md` (16.1KB, 2026-09-21)

**Historical (53 files, not cited by reviewer-facing surfaces):**

- `todo-status-correction-2026-09-13.md` (679B, 2026-09-21)
- `wave101-final-synthesis.md` (4.6KB, 2026-09-21)
- `wave106-final-synthesis.md` (24.5KB, 2026-09-21)
- `wave110-final-synthesis.md` (11.5KB, 2026-09-21)
- `wave161-close.md` (18.2KB, 2026-09-21)
- `wave187-p4-final-gate-verification.md` (4.5KB, 2026-09-21)
- `wave189-p6-final-gate-verification.md` (7.4KB, 2026-09-21)
- `wave190-p5-final-gate-verification.md` (7.3KB, 2026-09-21)
- `wave191-p5-final-gate-verification.md` (8.5KB, 2026-09-21)
- `wave192-p5-final-gate-verification.md` (8.5KB, 2026-09-21)
- `wave194-p6-final-gate-verification.md` (4.2KB, 2026-09-21)
- `wave195-p6-final-gate-verification.md` (5.5KB, 2026-09-21)
- `wave196-p6-final-gate-verification.md` (8.5KB, 2026-09-21)
- `wave197-p5-final-gate-verification.md` (7.7KB, 2026-09-21)
- `wave199-p5-final-gate-verification.md` (10.1KB, 2026-09-21)
- `wave204-p5-final-gate-verification.md` (10.2KB, 2026-09-21)
- `wave216-p5-final-synthesis.md` (14.0KB, 2026-09-21)
- `wave219-p7-pre-push.md` (4.8KB, 2026-09-21)
- `wave224-p2-final-verify.md` (6.5KB, 2026-09-21)
- `wave229-p5-final-verify.md` (2.2KB, 2026-09-21)
- `wave230-p4-final-verify.md` (7.4KB, 2026-09-21)
- `wave231-p6-final-verify.md` (3.9KB, 2026-09-21)
- `wave232-p3-final-verify.md` (2.6KB, 2026-09-21)
- `wave236-p4-final-verify.md` (3.4KB, 2026-09-21)
- `wave238-p4-final-verify.md` (6.8KB, 2026-09-21)
- `wave242-p4-final-verify.md` (4.7KB, 2026-09-21)
- `wave244-p5-final-verify.md` (7.8KB, 2026-09-21)
- `wave245-p6-final-verify.md` (3.2KB, 2026-09-22)
- `wave246-p5-final-verify.md` (1.7KB, 2026-09-22)
- `wave249-final-decision.md` (14.0KB, 2026-09-22)
- `wave250-p6-final-verify.md` (16.0KB, 2026-09-22)
- `wave251-p3-final-pre-push.md` (4.5KB, 2026-09-22)
- `wave252-p5-final-verify.md` (2.7KB, 2026-09-22)
- `wave254-p6-final-verify.md` (11.0KB, 2026-09-22)
- `wave255-p6-final-verify.md` (7.8KB, 2026-09-22)
- `wave256-p5-final-verify.md` (5.6KB, 2026-09-22)
- `wave258-p3-final-verify.md` (972B, 2026-09-22)
- `wave260-p4-final-commit.md` (2.2KB, 2026-09-22)
- `wave261-p5-final-audit.md` (14.7KB, 2026-09-22)
- `final_verify/wave262-p5-final-verify.md` (4.7KB, 2026-09-22)
- `wave263-p4-final-verify.md` (1.0KB, 2026-09-22)
- `wave264-p3-final-verify.md` (1.5KB, 2026-09-22)
- `wave265-p4-final-verify.md` (6.9KB, 2026-09-22)
- `wave266-p4-final-verify.md` (7.1KB, 2026-09-22)
- `wave267-p4-final-verify.md` (1.9KB, 2026-09-22)
- `wave268-p4-final-verify.md` (9.7KB, 2026-09-22)
- `wave269-p3-final-verify.md` (7.6KB, 2026-09-22)
- `wave270-p3-final-verify.md` (10.9KB, 2026-09-22)
- `wave270-p4-final-verify.md` (3.1KB, 2026-09-22)
- `wave272-p4-final-verify.md` (4.8KB, 2026-09-22)
- `wave273-p4-final-verify.md` (2.4KB, 2026-09-22)
- `wave274-p5-final-verify.md` (15.2KB, 2026-09-22)
- `wave275-p1-state-inventory.md` (20.4KB, 2026-09-22)

---

### Cluster: `governance` — Governance (scope, audit, gap, condition, placeholder, cross-cutting)

**Files: 45** (active: 17, historical: 28)

Governance (scope, audit, gap, condition, placeholder, cross-cutting): scope + gap-audit + empirical-conditions + open-requirements, placeholder-audit + registry-placeholder-audit, metric-methodology, docs-evidence audit, phase-4 blocker + eval, theory-implementation-gap, framework-code-review, framework-model-gap, g1-spec-literal review, upstream-modifications, epsilon-direction, phase4 docstring audit, algorithm-gap + algorithm-saturation + saturation-improvement-plan, per-adapter-value-verification, restart-policy-collapse, cifar-evaluation-corrections, cifar-fid-performance, closure (flowmol3-sweep, s7.4-s7.5, s7.7, state-none-fix, t3-final), and other cross-cutting investigations. The cluster is the project's governance + meta-audit trail.

**Active (cited by ≥1 reviewer-facing surface):**

- `EPSILON_DIRECTION.md` (17.6KB, 2026-09-21)
- `PHASE4_DOCSTRING_AUDIT.md` (12.6KB, 2026-09-21)
- `empirical-conditions.md` (16.0KB, 2026-09-21)
- `framework-model-gap-cpu-2026-09-13.md` (713B, 2026-09-21)
- `g1-spec-literal-review.md` (24.5KB, 2026-09-21)
- `gap-audit.md` (15.2KB, 2026-09-21)
- `phase-4-blocker-investigation.md` (14.9KB, 2026-09-21)
- `phase-4-eval-pipeline.md` (16.4KB, 2026-09-21)
- `theory-implementation-gap.md` (28.2KB, 2026-09-21)
- `todo-six-plan-status-2026-09-13.md` (785B, 2026-09-21)
- `governance/wave101-layer1-adapters-status.md` (690B, 2026-09-21)
- `governance/wave129-evidence-freetraj-blocker.md` (665B, 2026-09-21)
- `governance/wave149-pdf-warning-reduction.md` (5.3KB, 2026-09-21)
- `governance/wave178-p2-real-state-shape.md` (6.6KB, 2026-09-21)
- `governance/wave178-p3-build-initial-state.md` (12.3KB, 2026-09-21)
- `governance/wave178-p4-velocity-field-noop.md` (12.4KB, 2026-09-21)
- `governance/wave197-p3-root-cause.md` (12.1KB, 2026-09-21)

**Historical (28 files, not cited by reviewer-facing surfaces):**

- `adapter-conformance-deep-dive.md` (24.7KB, 2026-09-21)
- `closure-s7.4-s7.5.md` (17.8KB, 2026-09-21)
- `closure-s7.7.md` (9.5KB, 2026-09-21)
- `closure-state-none-fix.md` (10.8KB, 2026-09-21)
- `closure-t3-final.md` (21.9KB, 2026-09-21)
- `docs-evidence-audit-2026-09-13.md` (1.2KB, 2026-09-21)
- `framework-code-review.md` (40.7KB, 2026-09-21)
- `open-requirements.md` (1.7KB, 2026-09-21)
- `per-adapter-value-verification.md` (11.6KB, 2026-09-21)
- `registry-placeholder-audit-2026-09-13.md` (821B, 2026-09-21)
- `restart-policy-collapse-fix-2026-09-13.md` (737B, 2026-09-21)
- `saturation-improvement-plan.md` (7.7KB, 2026-09-21)
- `todo-experiment-smoke-2026-09-13.md` (788B, 2026-09-21)
- `upstream-modifications.md` (23.5KB, 2026-09-22)
- `wave101-layer4-p0b-archive-note.md` (502B, 2026-09-21)
- `wave101-p1-figures-metrics.md` (761B, 2026-09-21)
- `wave101-p2-feasibility.md` (866B, 2026-09-21)
- `wave106-c2-f03-json-persistence-note.md` (1.1KB, 2026-09-21)
- `wave131-rf1step-smoke.md` (400B, 2026-09-21)
- `wave148-tabular-reflow.md` (5.8KB, 2026-09-21)
- `wave167-push.md` (1.1KB, 2026-09-21)
- `wave212-p6-root-cause.md` (19.0KB, 2026-09-21)
- `wave217-p2-public-audit.md` (9.2KB, 2026-09-21)
- `wave229-p2-adapter-lipschitz.md` (6.3KB, 2026-09-21)
- `wave232-p2-abstract-trim.md` (7.7KB, 2026-09-21)
- `wave233-p1-abstract-trim.md` (4.4KB, 2026-09-21)
- `wave254-p5-fix-metadata.md` (8.5KB, 2026-09-22)
- `wave272-p3-readme-optimization.md` (7.2KB, 2026-09-22)

---

## Maintenance

- **New audit file?** Place it under `docs/audit/`; the cluster it lands in is determined by filename + first-30-line keyword scan (see `cluster_order` in `/tmp/build_index.py`). Update the relevant cluster summary in this file.
- **Active vs Historical flag?** Re-run the citation-grep against the active surfaces list (see `ACTIVE_SURFACES` in `/tmp/build_index.py`).
- **Cluster boundaries are heuristic.** If a file lands in the wrong cluster because its filename is generic (e.g. `waveXXX-p1-design.md`), the filename keyword was the primary signal — content keywords were the fallback. Inspect the first 30 lines of the file to confirm.

---

_This file complements the per-wave `INDEX.md` table. The per-wave table is authoritative for *"what did Wave N do?"*; this topic-cluster index is authoritative for *"what does the project claim about X?"*._