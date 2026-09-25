# Project Audit Index

> **Topic-cluster map of all `docs/audit/*.md` files.** Regenerated from on-disk layout (2026-09-25, Wave 347 governance refresh). Reviewers can answer *"what does the project claim about X?"* by reading the cluster summary for X.

Audit files are organized into topic-cluster subdirectories (`docs/audit/<cluster>/waveNNN-*.md`). Wave filenames are preserved (so `git log --follow` continues to work and the per-wave audit trail is intact). Flat files at the top level are classified into clusters by filename + first-30-line keyword scan (see `cluster_order` in `/tmp/regen_index.py`).

**Active surface** = one of the docs that are loaded by an external reviewer (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`, `docs/METRIC_LEDGER.md`, `docs/INSIGHTS.md`, `docs/ARCHITECTURE.md`, `docs/README.md`, `docs/paper-draft.md`, `docs/cover-letter-tnnls.md`, `docs/push-ready-summary.md`, plus 13 other Tier-1 reviewer-facing docs and the 8 `tnnls_submission/*.md` package files). **Active** = a cluster file is cited from at least one active surface; **Historical** = not cited (preserved for the per-wave audit trail).

---

## How to use this index

1. **Pick the cluster that matches your question** (CIFAR-10, Kanzi, LineageFlow, Algorithm / Theorem 1, Statistical methodology, …). 2. **Read the cluster summary** (one paragraph each, written without wave numbers — describes what the project actually claims and where the evidence lives). 3. **Open the active files first** (these are cited by reviewer-facing docs and are the canonical references). 4. **Historical files** preserve the per-wave audit trail and are useful for tracing the evolution of a result; skip them on a first read.

---

## Cluster map

| Cluster | Topic | Files | Active | Historical |
|---------|-------|------:|------:|-----------:|
| `cifar` | CIFAR-10 RF (Rectified Flow on CIFAR-10) | 7 | 5 | 2 |
| `kanzi` | Kanzi (protein flow autoencoder) | 9 | 9 | 0 |
| `flowmol3` | FlowMol3 (molecular 3D flow matching) | 5 | 3 | 2 |
| `lineageflow` | LineageFlow (protein flow matching, HMMER + foldability + novelty) | 19 | 16 | 3 |
| `freqflow` | FreqFlow + MM-FM (frequency / multimodal flow) | 3 | 3 | 0 |
| `mnist` | MNIST FM (MNIST flow matching) | 4 | 2 | 2 |
| `brai` | BRAI perturbation (Bounded-Range Adaptive Integration) | 0 | 0 | 0 |
| `2d_toy` | 2D toy FM (two-dim flow matching, 8gaussian) | 2 | 1 | 1 |
| `self_flow` | Self-Flow ICML 2026 (image FM) | 0 | 0 | 0 |
| `hidream` | HiDream-I1 (image diffusion) | 0 | 0 | 0 |
| `graphbfn` | GraphBFN (graph Bayesian flow network) | 0 | 0 | 0 |
| `lumina` | Lumina-Image-2.0 (image generation) | 0 | 0 | 0 |
| `protbfn_abbfn` | ProtBFN-AbBFN (antibody / protein BFN) | 0 | 0 | 0 |
| `wan2_2` | Wan2.2 video (video diffusion) | 0 | 0 | 0 |
| `web_research` | Web research 2026 (FM literature surveys) | 0 | 0 | 0 |
| `engineering` | Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree) | 84 | 53 | 31 |
| `reproducibility` | Reproducibility (reproducibility-record, preregistration, reproduce-script) | 8 | 4 | 4 |
| `data_packaging` | Data packaging + manifest (sha256, csv, metric-ledger) | 18 | 7 | 11 |
| `push_state` | Push state (push-ready, freeze, release, submission) | 4 | 3 | 1 |
| `algorithm_4arm` | Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency) | 32 | 19 | 13 |
| `sweep_eval` | Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability) | 90 | 77 | 13 |
| `stats_method` | Statistical methodology (R5/R6, p-value, bonferroni, TOST) | 18 | 8 | 10 |
| `paper_claims` | Paper + claims (paper packaging, claim audit, paper-update) | 20 | 8 | 12 |
| `final_verify` | Final-verify (per-wave close-out, pre-push hygiene) | 36 | 21 | 15 |
| `governance` | Governance (scope, audit, gap, condition, placeholder, cross-cutting) | 35 | 19 | 16 |
| **TOTAL** | — | **394** | **258** | **136** |

---

## Cluster details

### Cluster: `cifar` — CIFAR-10 RF (Rectified Flow on CIFAR-10)

**Files: 7** (active: 5, historical: 2)

CIFAR-10 RF (Rectified Flow on CIFAR-10). This cluster is part of the project's audit surface for cifar.

**Active (cited by ≥1 reviewer-facing surface):**

- [`cifar-reference-availability.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/cifar-reference-availability.md) (372B, 2026-09-22)
- [`cifar-v4-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/cifar-v4-audit.md) (7.2KB, 2026-09-22)
- [`p6-cifar-rf-v4-honest-negative-curve.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/p6-cifar-rf-v4-honest-negative-curve.md) (11.3KB, 2026-09-22)
- [`wave280-p-cifar-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/wave280-p-cifar-sweep-result.md) (15.6KB, 2026-09-22)
- [`wave286-p-cifar-resweep-aggregated.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/wave286-p-cifar-resweep-aggregated.md) (17.5KB, 2026-09-22)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- [`p-cifar10-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/p-cifar10-impl.md) (11.2KB, 2026-09-22)
- [`wave275-p4-cifar10-proposal.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/cifar/wave275-p4-cifar10-proposal.md) (32.6KB, 2026-09-22)

---

### Cluster: `kanzi` — Kanzi (protein flow autoencoder)

**Files: 9** (active: 9, historical: 0)

Kanzi (protein flow autoencoder). This cluster is part of the project's audit surface for kanzi.

**Active (cited by ≥1 reviewer-facing surface):**

- [`kanzi-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/kanzi-fix.md) (3.8KB, 2026-09-22)
- [`kanzi-gpu-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/kanzi-gpu-sweep.md) (30.0KB, 2026-09-22)
- [`kanzi-load-torch-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/kanzi-load-torch-fix.md) (5.0KB, 2026-09-22)
- [`kanzi-nfe-bug.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/kanzi-nfe-bug.md) (7.7KB, 2026-09-22)
- [`p1-kanzi-byte-stability-regression.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/p1-kanzi-byte-stability-regression.md) (17.2KB, 2026-09-22)
- [`p2-kanzi-n30-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/p2-kanzi-n30-sweep.md) (7.7KB, 2026-09-22)
- [`p2-kanzi-rerun.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/p2-kanzi-rerun.md) (7.1KB, 2026-09-22)
- [`p3-kanzi-n1000-framework-inv-proj.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/p3-kanzi-n1000-framework-inv-proj.md) (10.5KB, 2026-09-22)
- [`p4-kanzi-full.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/kanzi/p4-kanzi-full.md) (16.8KB, 2026-09-22)

---

### Cluster: `flowmol3` — FlowMol3 (molecular 3D flow matching)

**Files: 5** (active: 3, historical: 2)

FlowMol3 (molecular 3D flow matching). This cluster is part of the project's audit surface for flowmol3.

**Active (cited by ≥1 reviewer-facing surface):**

- [`c-flowmol3-n1000.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/flowmol3/c-flowmol3-n1000.md) (15.0KB, 2026-09-22)
- [`p2-flowmol3-dgl-fix-or-sanity.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/flowmol3/p2-flowmol3-dgl-fix-or-sanity.md) (11.1KB, 2026-09-22)
- [`p3-flowmol3-n1000.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/flowmol3/p3-flowmol3-n1000.md) (7.9KB, 2026-09-22)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- [`p-flowmol3-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/flowmol3/p-flowmol3-impl.md) (9.3KB, 2026-09-22)
- [`wave275-p4-flowmol3-proposal.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/flowmol3/wave275-p4-flowmol3-proposal.md) (33.6KB, 2026-09-22)

---

### Cluster: `lineageflow` — LineageFlow (protein flow matching, HMMER + foldability + novelty)

**Files: 19** (active: 16, historical: 3)

LineageFlow (protein flow matching, HMMER + foldability + novelty). This cluster is part of the project's audit surface for lineageflow.

**Active (cited by ≥1 reviewer-facing surface):**

- [`b-lineageflow-n1000-gpu.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/b-lineageflow-n1000-gpu.md) (10.2KB, 2026-09-22)
- [`lineageflow-hmmer-poc.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/lineageflow-hmmer-poc.md) (4.7KB, 2026-09-22)
- [`lineageflow-nfe-scan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/lineageflow-nfe-scan.md) (2.2KB, 2026-09-22)
- [`p3-lineageflow-n30-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/p3-lineageflow-n30-sweep.md) (10.2KB, 2026-09-22)
- [`p5-lineageflow-regression.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/p5-lineageflow-regression.md) (10.4KB, 2026-09-22)
- [`data_packaging/hmmer-launch.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/data_packaging/hmmer-launch.md) (5.2KB, 2026-09-22)
- [`engineering/hmmer-collect.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/engineering/hmmer-collect.md) (7.8KB, 2026-09-22)
- [`engineering/hmmer-rederivation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/engineering/hmmer-rederivation.md) (10.5KB, 2026-09-22)
- [`sweep_eval/hmmer-launch.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/hmmer-launch.md) (6.3KB, 2026-09-22)
- [`sweep_eval/novelty-diagnosis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/novelty-diagnosis.md) (18.8KB, 2026-09-22)
- [`sweep_eval/novelty-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/novelty-fix.md) (15.6KB, 2026-09-22)
- [`sweep_eval/novelty-sweep-fixed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/novelty-sweep-fixed.md) (14.0KB, 2026-09-22)
- [`sweep_eval/novelty-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/novelty-sweep.md) (13.5KB, 2026-09-22)
- [`sweep_eval/p1-pLDDT-inversion.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/p1-pLDDT-inversion.md) (18.5KB, 2026-09-22)
- [`sweep_eval/p2-foldability-sc-workers-per-gpu.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/p2-foldability-sc-workers-per-gpu.md) (3.9KB, 2026-09-22)
- [`sweep_eval/p3-run-foldability-propagate-workers-per-gpu.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/sweep_eval/p3-run-foldability-propagate-workers-per-gpu.md) (5.9KB, 2026-09-22)

**Historical (3 files, not cited by reviewer-facing surfaces):**

- [`p-k7-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/p-k7-impl.md) (6.1KB, 2026-09-22)
- [`p-lineageflow-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/p-lineageflow-impl.md) (10.1KB, 2026-09-22)
- [`wave275-p4-lineageflow-proposal.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/lineageflow/wave275-p4-lineageflow-proposal.md) (24.1KB, 2026-09-22)

---

### Cluster: `freqflow` — FreqFlow + MM-FM (frequency / multimodal flow)

**Files: 3** (active: 3, historical: 0)

FreqFlow + MM-FM (frequency / multimodal flow). This cluster is part of the project's audit surface for freqflow.

**Active (cited by ≥1 reviewer-facing surface):**

- [`p3-freqflow-honest-disclosure.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/freqflow/p3-freqflow-honest-disclosure.md) (12.6KB, 2026-09-22)
- [`p5-freqflow-n1000.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/freqflow/p5-freqflow-n1000.md) (8.4KB, 2026-09-22)
- [`mm-fm-unblock-investigation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/freqflow/mm-fm-unblock-investigation.md) (10.0KB, 2026-09-21)

---

### Cluster: `mnist` — MNIST FM (MNIST flow matching)

**Files: 4** (active: 2, historical: 2)

MNIST FM (MNIST flow matching). This cluster is part of the project's audit surface for mnist.

**Active (cited by ≥1 reviewer-facing surface):**

- [`wave280-p-r5c-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/mnist/wave280-p-r5c-sweep-result.md) (17.4KB, 2026-09-22)
- [`wf334-r5c-regime-curve.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/mnist/wf334-r5c-regime-curve.md) (12.2KB, 2026-09-23)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- [`p-mnist-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/mnist/p-mnist-impl.md) (10.6KB, 2026-09-22)
- [`wave275-p4-mnist-proposal.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/mnist/wave275-p4-mnist-proposal.md) (39.9KB, 2026-09-23)

---

### Cluster: `2d_toy` — 2D toy FM (two-dim flow matching, 8gaussian)

**Files: 2** (active: 1, historical: 1)

2D toy FM (two-dim flow matching, 8gaussian). This cluster is part of the project's audit surface for 2d_toy.

**Active (cited by ≥1 reviewer-facing surface):**

- [`wave286-p-paper-quantity-ablation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/2d_toy/wave286-p-paper-quantity-ablation.md) (18.9KB, 2026-09-22)

**Historical (1 files, not cited by reviewer-facing surfaces):**

- [`wave282-p-cosine-vs-paper-controllers.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/2d_toy/wave282-p-cosine-vs-paper-controllers.md) (20.7KB, 2026-09-22)

---

### Cluster: `engineering` — Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree)

**Files: 84** (active: 53, historical: 31)

Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree). This cluster is part of the project's audit surface for engineering.

**Active (cited by ≥1 reviewer-facing surface):**

- [`bridge-bug-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/bridge-bug-design.md) (27.0KB, 2026-09-22)
- [`cli-pr-prep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/cli-pr-prep.md) (33.9KB, 2026-09-22)
- [`cli-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/cli-verify.md) (11.8KB, 2026-09-22)
- [`doc-cleanup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/doc-cleanup.md) (12.8KB, 2026-09-22)
- [`docstring-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/docstring-audit.md) (9.0KB, 2026-09-22)
- [`eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/eval.md) (11.4KB, 2026-09-22)
- [`followup-w148.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/followup-w148.md) (8.8KB, 2026-09-22)
- [`followup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/followup.md) (8.4KB, 2026-09-22)
- [`headline-evidence.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/headline-evidence.md) (9.7KB, 2026-09-22)
- [`impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/impl.md) (11.5KB, 2026-09-22)
- [`inv-proj-final-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/inv-proj-final-fix.md) (19.4KB, 2026-09-22)
- [`mypy-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/mypy-fix.md) (8.4KB, 2026-09-22)
- [`number-consistency.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/number-consistency.md) (9.5KB, 2026-09-22)
- [`p1-setup-w184.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p1-setup-w184.md) (8.7KB, 2026-09-22)
- [`p1-setup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p1-setup.md) (15.1KB, 2026-09-22)
- [`p2-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p2-verify.md) (5.0KB, 2026-09-22)
- [`p3-integration.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p3-integration.md) (13.1KB, 2026-09-22)
- [`p3-journal-decision.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p3-journal-decision.md) (12.0KB, 2026-09-22)
- [`p3-tier-aware.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p3-tier-aware.md) (11.5KB, 2026-09-22)
- [`p4-plot.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p4-plot.md) (9.4KB, 2026-09-22)
- [`p4-table-aggregate.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p4-table-aggregate.md) (12.3KB, 2026-09-22)
- [`p5-gates.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p5-gates.md) (8.0KB, 2026-09-22)
- [`p5-results.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p5-results.md) (10.5KB, 2026-09-22)
- [`pdf-warning-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/pdf-warning-fixes.md) (2.6KB, 2026-09-22)
- [`polish-execute.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/polish-execute.md) (10.1KB, 2026-09-22)
- [`pr1-application.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/pr1-application.md) (3.2KB, 2026-09-22)
- [`primitive-cli-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/primitive-cli-design.md) (9.4KB, 2026-09-22)
- [`push-and-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/push-and-fix.md) (9.7KB, 2026-09-22)
- [`push-w156c.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/push-w156c.md) (6.7KB, 2026-09-22)
- [`push-w158.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/push-w158.md) (5.1KB, 2026-09-22)
- [`push.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/push.md) (5.1KB, 2026-09-22)
- [`ruff-cleanup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/ruff-cleanup.md) (9.2KB, 2026-09-22)
- [`scripts-ruff-cleanup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/scripts-ruff-cleanup.md) (7.8KB, 2026-09-22)
- [`tier1-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/tier1-polish.md) (9.4KB, 2026-09-22)
- [`tmp-migration.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/tmp-migration.md) (8.5KB, 2026-09-22)
- [`todo-refactor.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/todo-refactor.md) (9.8KB, 2026-09-22)
- [`data_packaging/pdf-warning-zero.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/data_packaging/pdf-warning-zero.md) (3.7KB, 2026-09-22)
- [`engineering-audit-2026-09-13.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/engineering-audit-2026-09-13.md) (4.9KB, 2026-09-21)
- [`governance/pdf-warning-reduction.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/governance/pdf-warning-reduction.md) (5.3KB, 2026-09-22)
- [`paper_claims/pdf-warning-reduction.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/paper_claims/pdf-warning-reduction.md) (3.2KB, 2026-09-22)
- [`wave290-p4-benchmark-fixed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave290-p4-benchmark-fixed.md) (19.8KB, 2026-09-23)
- [`wave291-p1-hypothesis-redesign.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave291-p1-hypothesis-redesign.md) (26.8KB, 2026-09-23)
- [`wave296-p1-architecture.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave296-p1-architecture.md) (40.0KB, 2026-09-23)
- [`wave296-p2-cache.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave296-p2-cache.md) (23.3KB, 2026-09-23)
- [`wave297-p3-intro-rewritten.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave297-p3-intro-rewritten.md) (15.0KB, 2026-09-23)
- [`wave297-p4-framework-rewritten.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave297-p4-framework-rewritten.md) (21.4KB, 2026-09-23)
- [`wave297-p5-empirical-rewritten.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave297-p5-empirical-rewritten.md) (39.0KB, 2026-09-23)
- [`wave297-p7-readme-updated.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave297-p7-readme-updated.md) (11.5KB, 2026-09-23)
- [`wave306-11-cell-alignment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave306-11-cell-alignment.md) (27.4KB, 2026-09-23)
- [`wave307-data-archaeology.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave307-data-archaeology.md) (49.9KB, 2026-09-23)
- [`wave310-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave310-restoration-execution.md) (24.8KB, 2026-09-25)
- [`wave311-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave311-restoration-execution.md) (18.5KB, 2026-09-23)
- [`wave322-restoration-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave322-restoration-execution.md) (17.8KB, 2026-09-23)

**Historical (31 files, not cited by reviewer-facing surfaces):**

- [`c3-fix-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/c3-fix-summary.md) (14.4KB, 2026-09-22)
- [`p3-number-verification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p3-number-verification.md) (36.8KB, 2026-09-22)
- [`p5-ground-truth-corrections.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/p5-ground-truth-corrections.md) (9.1KB, 2026-09-22)
- [`review-layer4-docs-config.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/review-layer4-docs-config.md) (11.3KB, 2026-09-22)
- [`scheduler-per-cell-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/scheduler-per-cell-summary.md) (32.4KB, 2026-09-22)
- [`wave275-p4-overview.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave275-p4-overview.md) (22.7KB, 2026-09-22)
- [`wave279-plan-complete.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave279-plan-complete.md) (12.8KB, 2026-09-22)
- [`wave279-user-decisions.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave279-user-decisions.md) (5.6KB, 2026-09-22)
- [`wave287-p-ci-hardening.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave287-p-ci-hardening.md) (9.9KB, 2026-09-22)
- [`wave287-p-test-coverage.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave287-p-test-coverage.md) (8.9KB, 2026-09-22)
- [`wave290-p2-driver-microfix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave290-p2-driver-microfix.md) (17.4KB, 2026-09-23)
- [`wave290-p5-workflow-paused-status.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave290-p5-workflow-paused-status.md) (16.4KB, 2026-09-23)
- [`wave292-p2-config-genealogy.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave292-p2-config-genealogy.md) (37.1KB, 2026-09-23)
- [`wave293-p3-fix-applied.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave293-p3-fix-applied.md) (13.9KB, 2026-09-23)
- [`wave296-p5-activation-log.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave296-p5-activation-log.md) (12.5KB, 2026-09-23)
- [`wave296-p6-backward-compat.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave296-p6-backward-compat.md) (12.7KB, 2026-09-23)
- [`wave296-p7-fid-comparison.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave296-p7-fid-comparison.md) (10.8KB, 2026-09-23)
- [`wave299-final-verification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave299-final-verification.md) (34.6KB, 2026-09-23)
- [`wave301-day0-prompt.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave301-day0-prompt.md) (18.1KB, 2026-09-23)
- [`wave301-day2-execution-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave301-day2-execution-plan.md) (46.5KB, 2026-09-23)
- [`wave301-day3-execution-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave301-day3-execution-plan.md) (45.7KB, 2026-09-23)
- [`wave302-p2-exp-b1-smoke.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave302-p2-exp-b1-smoke.md) (19.4KB, 2026-09-23)
- [`wave306-fix-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave306-fix-plan.md) (62.8KB, 2026-09-23)
- [`wave308-d3-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave308-d3-review.md) (25.7KB, 2026-09-23)
- [`wave326-ci-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave326-ci-design.md) (17.0KB, 2026-09-23)
- [`wave326-ci-redesign-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave326-ci-redesign-execution.md) (19.1KB, 2026-09-23)
- [`wave326-data-integrity-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave326-data-integrity-design.md) (13.0KB, 2026-09-23)
- [`wave326-readme-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave326-readme-update.md) (8.0KB, 2026-09-23)
- [`wave334-reviewer-prediction.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave334-reviewer-prediction.md) (19.8KB, 2026-09-25)
- [`wave338-phase2-mechanism.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave338-phase2-mechanism.md) (11.9KB, 2026-09-23)
- [`wave340-readme-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/engineering/wave340-readme-update.md) (13.0KB, 2026-09-23)

---

### Cluster: `reproducibility` — Reproducibility (reproducibility-record, preregistration, reproduce-script)

**Files: 8** (active: 4, historical: 4)

Reproducibility (reproducibility-record, preregistration, reproduce-script). This cluster is part of the project's audit surface for reproducibility.

**Active (cited by ≥1 reviewer-facing surface):**

- [`item4-tex-rewrite.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/item4-tex-rewrite.md) (6.7KB, 2026-09-22)
- [`p3-comparison.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/p3-comparison.md) (5.5KB, 2026-09-22)
- [`wave298-p3-reproducibility-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/wave298-p3-reproducibility-innovations.md) (39.5KB, 2026-09-23)
- [`wave324-d5-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/wave324-d5-review.md) (8.0KB, 2026-09-23)

**Historical (4 files, not cited by reviewer-facing surfaces):**

- [`p5-experiment-setup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/p5-experiment-setup.md) (19.4KB, 2026-09-22)
- [`p8-experiment-setup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/p8-experiment-setup.md) (15.7KB, 2026-09-22)
- [`wave303-day0-prompt.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/wave303-day0-prompt.md) (24.0KB, 2026-09-23)
- [`wave325-push-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/reproducibility/wave325-push-execution.md) (11.7KB, 2026-09-23)

---

### Cluster: `data_packaging` — Data packaging + manifest (sha256, csv, metric-ledger)

**Files: 18** (active: 7, historical: 11)

Data packaging + manifest (sha256, csv, metric-ledger). This cluster is part of the project's audit surface for data_packaging.

**Active (cited by ≥1 reviewer-facing surface):**

- [`fasta-generation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/fasta-generation.md) (9.5KB, 2026-09-22)
- [`fix-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/fix-design.md) (16.5KB, 2026-09-22)
- [`tier1-metric-alignment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/tier1-metric-alignment.md) (9.3KB, 2026-09-22)
- [`wave297-p6-limitations-rewritten.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave297-p6-limitations-rewritten.md) (39.1KB, 2026-09-23)
- [`wave326-final-metrics-table.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave326-final-metrics-table.md) (11.5KB, 2026-09-23)
- [`wave331-data-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave331-data-fix.md) (4.1KB, 2026-09-23)
- [`wave344-supplementary-bundle.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave344-supplementary-bundle.md) (14.3KB, 2026-09-25)

**Historical (11 files, not cited by reviewer-facing surfaces):**

- [`data-linkage-closure.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/data-linkage-closure.md) (16.2KB, 2026-09-22)
- [`data-linkage-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/data-linkage-plan.md) (28.5KB, 2026-09-22)
- [`framework-inv-proj-re-run.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/framework-inv-proj-re-run.md) (5.7KB, 2026-09-22)
- [`implementation-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/implementation-plan.md) (49.2KB, 2026-09-22)
- [`p1-data-gathering.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/p1-data-gathering.md) (59.8KB, 2026-09-22)
- [`p5-metrics-patch.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/p5-metrics-patch.md) (6.4KB, 2026-09-22)
- [`wave275-p1-state-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave275-p1-state-inventory.md) (20.4KB, 2026-09-22)
- [`wave275-p2-metric-ledger.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave275-p2-metric-ledger.md) (5.9KB, 2026-09-22)
- [`wave327-revised-q1-assessment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave327-revised-q1-assessment.md) (29.8KB, 2026-09-23)
- [`wave328-freeze-survey.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave328-freeze-survey.md) (18.8KB, 2026-09-23)
- [`wave342-readme-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/data_packaging/wave342-readme-update.md) (12.8KB, 2026-09-25)

---

### Cluster: `push_state` — Push state (push-ready, freeze, release, submission)

**Files: 4** (active: 3, historical: 1)

Push state (push-ready, freeze, release, submission). This cluster is part of the project's audit surface for push_state.

**Active (cited by ≥1 reviewer-facing surface):**

- [`submission-polish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/push_state/submission-polish.md) (9.7KB, 2026-09-22)
- [`submission-prep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/push_state/submission-prep.md) (18.4KB, 2026-09-22)
- [`verify-submission-readiness.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/push_state/verify-submission-readiness.md) (10.4KB, 2026-09-22)

**Historical (1 files, not cited by reviewer-facing surfaces):**

- [`wave324-submission-prep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/push_state/wave324-submission-prep.md) (11.5KB, 2026-09-23)

---

### Cluster: `algorithm_4arm` — Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency)

**Files: 32** (active: 19, historical: 13)

Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency). This cluster is part of the project's audit surface for algorithm_4arm.

**Active (cited by ≥1 reviewer-facing surface):**

- [`p-r6-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p-r6-impl.md) (16.1KB, 2026-09-22)
- [`p1-4arm-power-analysis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p1-4arm-power-analysis.md) (8.3KB, 2026-09-22)
- [`p1-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p1-design.md) (17.7KB, 2026-09-22)
- [`p2-eval-w182.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p2-eval-w182.md) (18.2KB, 2026-09-22)
- [`p2-eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p2-eval.md) (17.5KB, 2026-09-22)
- [`p2-impl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p2-impl.md) (6.7KB, 2026-09-22)
- [`p2-progress.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p2-progress.md) (6.8KB, 2026-09-22)
- [`p2-wallclock-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p2-wallclock-fix.md) (12.2KB, 2026-09-22)
- [`p3-4arm-power.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p3-4arm-power.md) (14.6KB, 2026-09-22)
- [`p3-comparison.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p3-comparison.md) (3.2KB, 2026-09-22)
- [`p3-rerun.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p3-rerun.md) (8.8KB, 2026-09-22)
- [`p4-aggregate.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p4-aggregate.md) (9.7KB, 2026-09-22)
- [`p4-theorem1-power.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p4-theorem1-power.md) (19.6KB, 2026-09-22)
- [`p6-boundary-framing.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p6-boundary-framing.md) (12.9KB, 2026-09-22)
- [`push.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/push.md) (4.1KB, 2026-09-22)
- [`theory-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/theory-audit.md) (22.8KB, 2026-09-22)
- [`algorithm-gap-investigation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/algorithm-gap-investigation.md) (25.3KB, 2026-09-21)
- [`wave311-path-a-lemma-1.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave311-path-a-lemma-1.md) (18.6KB, 2026-09-23)
- [`wave322-path-a-lemmas-2-3.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave322-path-a-lemmas-2-3.md) (24.8KB, 2026-09-23)

**Historical (13 files, not cited by reviewer-facing surfaces):**

- [`p3-f-side-actual-values.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p3-f-side-actual-values.md) (15.3KB, 2026-09-22)
- [`p3-post-hoc-sensitivity.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p3-post-hoc-sensitivity.md) (9.7KB, 2026-09-22)
- [`p6-repo-naming.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/p6-repo-naming.md) (6.7KB, 2026-09-22)
- [`wave292-p3-crosscheck.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave292-p3-crosscheck.md) (30.7KB, 2026-09-23)
- [`wave293-p1-locate-sign.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave293-p1-locate-sign.md) (19.2KB, 2026-09-23)
- [`wave294-p2-medium-fixed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave294-p2-medium-fixed.md) (11.9KB, 2026-09-23)
- [`wave296-p3-a-class-wired.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave296-p3-a-class-wired.md) (20.5KB, 2026-09-23)
- [`wave296-p4-b-class-wired.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave296-p4-b-class-wired.md) (22.5KB, 2026-09-23)
- [`wave300-p3-resolution-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave300-p3-resolution-plan.md) (27.5KB, 2026-09-23)
- [`wave302-p5-codim-deep-dive.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave302-p5-codim-deep-dive.md) (15.1KB, 2026-09-23)
- [`wave303-day0-14-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave303-day0-14-plan.md) (69.0KB, 2026-09-23)
- [`wave305-day0-risk-package.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave305-day0-risk-package.md) (37.8KB, 2026-09-23)
- [`wave336-r5b-mechanism.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/algorithm_4arm/wave336-r5b-mechanism.md) (20.6KB, 2026-09-23)

---

### Cluster: `sweep_eval` — Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability)

**Files: 90** (active: 77, historical: 13)

Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability). This cluster is part of the project's audit surface for sweep_eval.

**Active (cited by ≥1 reviewer-facing surface):**

- [`cross-model-nfe-curve.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/cross-model-nfe-curve.md) (9.1KB, 2026-09-22)
- [`cuda-fix-sweep-recovery.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/cuda-fix-sweep-recovery.md) (25.4KB, 2026-09-22)
- [`dispatch-verification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/dispatch-verification.md) (12.2KB, 2026-09-22)
- [`eval-w174.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/eval-w174.md) (13.3KB, 2026-09-22)
- [`eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/eval.md) (11.3KB, 2026-09-22)
- [`fair-fasta-generation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/fair-fasta-generation.md) (10.6KB, 2026-09-22)
- [`fasta-generation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/fasta-generation.md) (7.4KB, 2026-09-22)
- [`finish.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/finish.md) (5.5KB, 2026-09-22)
- [`gpu-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/gpu-verify.md) (9.7KB, 2026-09-22)
- [`headline-evidence-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/headline-evidence-audit.md) (13.1KB, 2026-09-22)
- [`item1-ablation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/item1-ablation.md) (8.9KB, 2026-09-22)
- [`item2-hp-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/item2-hp-sweep.md) (7.7KB, 2026-09-22)
- [`k1-rc5-launch-w156.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k1-rc5-launch-w156.md) (13.9KB, 2026-09-22)
- [`k1-rc5-launch.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k1-rc5-launch.md) (8.2KB, 2026-09-22)
- [`k1-rc5-preflight.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k1-rc5-preflight.md) (6.7KB, 2026-09-22)
- [`k1-rerun.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k1-rerun.md) (11.0KB, 2026-09-22)
- [`k6-sweep-launch.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k6-sweep-launch.md) (11.6KB, 2026-09-22)
- [`k6-verification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k6-verification.md) (8.8KB, 2026-09-22)
- [`n-rounds-flag.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/n-rounds-flag.md) (6.5KB, 2026-09-22)
- [`nfe-curve.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/nfe-curve.md) (14.4KB, 2026-09-22)
- [`nfe-flag.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/nfe-flag.md) (7.9KB, 2026-09-22)
- [`nfe-real.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/nfe-real.md) (10.3KB, 2026-09-22)
- [`omegafold-provisioning.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/omegafold-provisioning.md) (14.3KB, 2026-09-22)
- [`p1-design-w178.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-design-w178.md) (21.9KB, 2026-09-22)
- [`p1-design-w179.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-design-w179.md) (11.3KB, 2026-09-22)
- [`p1-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-design.md) (10.7KB, 2026-09-22)
- [`p1-investigation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-investigation.md) (12.2KB, 2026-09-22)
- [`p1-revert-all.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-revert-all.md) (5.7KB, 2026-09-22)
- [`p1-setup-w181.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-setup-w181.md) (13.2KB, 2026-09-22)
- [`p1-setup-w182.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-setup-w182.md) (14.8KB, 2026-09-22)
- [`p1-setup-w186.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-setup-w186.md) (5.1KB, 2026-09-22)
- [`p1-setup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-setup.md) (10.2KB, 2026-09-22)
- [`p2-empirical-bl.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-empirical-bl.md) (11.9KB, 2026-09-22)
- [`p2-eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-eval.md) (13.8KB, 2026-09-22)
- [`p2-fasta-generation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-fasta-generation.md) (8.9KB, 2026-09-22)
- [`p2-generate-w183.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-generate-w183.md) (20.0KB, 2026-09-22)
- [`p2-generate-w184.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-generate-w184.md) (10.7KB, 2026-09-22)
- [`p2-generate.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-generate.md) (10.3KB, 2026-09-22)
- [`p2-post-cd70821-2d-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p2-post-cd70821-2d-sweep.md) (7.9KB, 2026-09-22)
- [`p3-comparison.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-comparison.md) (8.5KB, 2026-09-22)
- [`p3-eval-w183.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-eval-w183.md) (18.3KB, 2026-09-22)
- [`p3-eval-w184.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-eval-w184.md) (9.0KB, 2026-09-22)
- [`p3-eval-w186.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-eval-w186.md) (11.9KB, 2026-09-22)
- [`p3-eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-eval.md) (10.8KB, 2026-09-22)
- [`p3-fasta-ladder.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-fasta-ladder.md) (6.2KB, 2026-09-22)
- [`p3-sanity.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-sanity.md) (9.5KB, 2026-09-22)
- [`p3-tightness.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p3-tightness.md) (15.2KB, 2026-09-22)
- [`p4-aggregate-w183.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-aggregate-w183.md) (7.0KB, 2026-09-22)
- [`p4-aggregate.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-aggregate.md) (16.4KB, 2026-09-22)
- [`p4-aggregation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-aggregation.md) (13.6KB, 2026-09-22)
- [`p4-cross-adapter-ablation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-cross-adapter-ablation.md) (11.9KB, 2026-09-22)
- [`p4-nfe-curve-w168.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-nfe-curve-w168.md) (12.8KB, 2026-09-22)
- [`p4-nfe-curve.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p4-nfe-curve.md) (12.0KB, 2026-09-22)
- [`p5-plot.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p5-plot.md) (7.7KB, 2026-09-22)
- [`p6-e2e-eval.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p6-e2e-eval.md) (7.8KB, 2026-09-22)
- [`p6-paper.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p6-paper.md) (5.5KB, 2026-09-22)
- [`rc4-ablation-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/rc4-ablation-fix.md) (5.6KB, 2026-09-22)
- [`restart-blend-analysis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/restart-blend-analysis.md) (12.9KB, 2026-09-22)
- [`restart-over-application.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/restart-over-application.md) (11.9KB, 2026-09-22)
- [`shape-fix-resweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/shape-fix-resweep.md) (22.1KB, 2026-09-22)
- [`sweeps-collect.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/sweeps-collect.md) (6.2KB, 2026-09-22)
- [`validation-experiment.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/validation-experiment.md) (17.3KB, 2026-09-22)
- [`w2-n1000-reruns.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/w2-n1000-reruns.md) (21.6KB, 2026-09-22)
- [`wave280-p-k1-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-k1-sweep-result.md) (18.6KB, 2026-09-22)
- [`wave280-p-k4k5-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-k4k5-sweep-result.md) (11.2KB, 2026-09-22)
- [`wave280-p-k7-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-k7-sweep-result.md) (7.6KB, 2026-09-22)
- [`wave280-p-r1-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-r1-sweep-result.md) (11.1KB, 2026-09-22)
- [`wave280-p-r3-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-r3-sweep-result.md) (6.7KB, 2026-09-22)
- [`wave280-p-r6-sweep-result.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave280-p-r6-sweep-result.md) (12.5KB, 2026-09-22)
- [`wave286-p-fid-gpu-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave286-p-fid-gpu-fix.md) (8.1KB, 2026-09-22)
- [`wave286-p-fid-gpu-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave286-p-fid-gpu-verify.md) (11.8KB, 2026-09-22)
- [`wave290-p1-bottleneck-confirmed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave290-p1-bottleneck-confirmed.md) (18.1KB, 2026-09-23)
- [`wave290-p3-batched-harness.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave290-p3-batched-harness.md) (13.0KB, 2026-09-23)
- [`wave291-p3-1seed-results.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave291-p3-1seed-results.md) (6.2KB, 2026-09-23)
- [`wave291-p5-3seed-results.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave291-p5-3seed-results.md) (9.7KB, 2026-09-23)
- [`wave307-archaeology-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave307-archaeology-summary.md) (19.7KB, 2026-09-23)
- [`wave311-d1-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave311-d1-review.md) (21.9KB, 2026-09-23)

**Historical (13 files, not cited by reviewer-facing surfaces):**

- [`b-config-scattering-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/b-config-scattering-audit.md) (19.3KB, 2026-09-22)
- [`framework-synth-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/framework-synth-sweep.md) (10.5KB, 2026-09-22)
- [`k1-rc5-3arm-preflight.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/k1-rc5-3arm-preflight.md) (8.4KB, 2026-09-22)
- [`p1-restore-r4-r5.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p1-restore-r4-r5.md) (9.2KB, 2026-09-22)
- [`p5-doc-consolidation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/p5-doc-consolidation.md) (20.2KB, 2026-09-22)
- [`wave287-p-adversarial-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave287-p-adversarial-sweep.md) (8.5KB, 2026-09-22)
- [`wave291-p2-sweep-driver.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave291-p2-sweep-driver.md) (12.8KB, 2026-09-23)
- [`wave291-p4-regime-analysis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave291-p4-regime-analysis.md) (16.6KB, 2026-09-23)
- [`wave293-p4-related-docs.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave293-p4-related-docs.md) (12.6KB, 2026-09-23)
- [`wave301-day1-execution-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave301-day1-execution-plan.md) (38.7KB, 2026-09-23)
- [`wave302-p1-regime-sweep-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave302-p1-regime-sweep-design.md) (30.4KB, 2026-09-23)
- [`wave330-zh-review-version.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave330-zh-review-version.md) (4.0KB, 2026-09-23)
- [`wave338-p5-r3-dgl-fix-and-sweep.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/sweep_eval/wave338-p5-r3-dgl-fix-and-sweep.md) (11.5KB, 2026-09-23)

---

### Cluster: `stats_method` — Statistical methodology (R5/R6, p-value, bonferroni, TOST)

**Files: 18** (active: 8, historical: 10)

Statistical methodology (R5/R6, p-value, bonferroni, TOST). This cluster is part of the project's audit surface for stats_method.

**Active (cited by ≥1 reviewer-facing surface):**

- [`p1-power-spec.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p1-power-spec.md) (30.2KB, 2026-09-22)
- [`p1-r3-uplift.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p1-r3-uplift.md) (12.1KB, 2026-09-22)
- [`p1-r5c-underflow-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p1-r5c-underflow-fix.md) (5.4KB, 2026-09-22)
- [`p2-r-level-power.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p2-r-level-power.md) (19.0KB, 2026-09-22)
- [`p3-r3-cross-seed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p3-r3-cross-seed.md) (5.7KB, 2026-09-22)
- [`p4-r-level-refresh.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p4-r-level-refresh.md) (7.6KB, 2026-09-22)
- [`pr2-application.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/pr2-application.md) (17.7KB, 2026-09-22)
- [`wave310-r6-tier-aware-upgrade.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/wave310-r6-tier-aware-upgrade.md) (14.1KB, 2026-09-23)

**Historical (10 files, not cited by reviewer-facing surfaces):**

- [`p1-fix-r2-numbers.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p1-fix-r2-numbers.md) (9.4KB, 2026-09-22)
- [`p1-r5b-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p1-r5b-fix.md) (11.5KB, 2026-09-22)
- [`p2-r2-re-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p2-r2-re-audit.md) (14.1KB, 2026-09-22)
- [`p3-r3-re-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p3-r3-re-audit.md) (19.0KB, 2026-09-22)
- [`p3-r6-uplift.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p3-r6-uplift.md) (8.5KB, 2026-09-22)
- [`p4-r6-re-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p4-r6-re-audit.md) (22.5KB, 2026-09-22)
- [`p6-non-inferiority.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/p6-non-inferiority.md) (3.7KB, 2026-09-22)
- [`wave275-p4-r6-proposal.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/wave275-p4-r6-proposal.md) (25.8KB, 2026-09-22)
- [`wave302-p4-r6-replication.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/wave302-p4-r6-replication.md) (11.4KB, 2026-09-23)
- [`wave347-r5a-ds-aggregation-clarification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/stats_method/wave347-r5a-ds-aggregation-clarification.md) (15.7KB, 2026-09-25)

---

### Cluster: `paper_claims` — Paper + claims (paper packaging, claim audit, paper-update)

**Files: 20** (active: 8, historical: 12)

Paper + claims (paper packaging, claim audit, paper-update). This cluster is part of the project's audit surface for paper_claims.

**Active (cited by ≥1 reviewer-facing surface):**

- [`agent3-pdf-generation.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/agent3-pdf-generation.md) (6.8KB, 2026-09-22)
- [`d-paper-package-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/d-paper-package-update.md) (10.8KB, 2026-09-22)
- [`p3-clm057-update.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/p3-clm057-update.md) (13.3KB, 2026-09-22)
- [`wave297-p2-paper-design.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave297-p2-paper-design.md) (33.2KB, 2026-09-23)
- [`wave309-paper-a-restoration-plan.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave309-paper-a-restoration-plan.md) (31.7KB, 2026-09-25)
- [`wave323-typeset-execution.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave323-typeset-execution.md) (14.5KB, 2026-09-23)
- [`wave343-paper-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave343-paper-fixes.md) (18.0KB, 2026-09-25)
- [`wave345-cross-doc-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave345-cross-doc-fixes.md) (51.0KB, 2026-09-25)

**Historical (12 files, not cited by reviewer-facing surfaces):**

- [`p4-paper-updates.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/p4-paper-updates.md) (20.2KB, 2026-09-22)
- [`p6-paper-polish-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/p6-paper-polish-audit.md) (6.9KB, 2026-09-22)
- [`wave293-p2-verify-direction.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave293-p2-verify-direction.md) (10.9KB, 2026-09-23)
- [`wave294-p3-low-paper-fixed.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave294-p3-low-paper-fixed.md) (9.6KB, 2026-09-23)
- [`wave297-p1-paper-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave297-p1-paper-inventory.md) (19.5KB, 2026-09-23)
- [`wave298-p7-paper-append.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave298-p7-paper-append.md) (20.5KB, 2026-09-23)
- [`wave298-p8-claims-updated.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave298-p8-claims-updated.md) (15.8KB, 2026-09-23)
- [`wave299-paper-a-outline.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave299-paper-a-outline.md) (25.1KB, 2026-09-23)
- [`wave299-paper-b-deferred.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave299-paper-b-deferred.md) (17.2KB, 2026-09-23)
- [`wave323-d3-review.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave323-d3-review.md) (12.3KB, 2026-09-23)
- [`wave328-freeze-manifest.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave328-freeze-manifest.md) (12.0KB, 2026-09-23)
- [`wave342-claims-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/paper_claims/wave342-claims-fixes.md) (18.7KB, 2026-09-25)

---

### Cluster: `final_verify` — Final-verify (per-wave close-out, pre-push hygiene)

**Files: 36** (active: 21, historical: 15)

Final-verify (per-wave close-out, pre-push hygiene). This cluster is part of the project's audit surface for final_verify.

**Active (cited by ≥1 reviewer-facing surface):**

- [`close-remaining-debt.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-remaining-debt.md) (26.9KB, 2026-09-22)
- [`close-w150.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w150.md) (7.3KB, 2026-09-22)
- [`close-w151.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w151.md) (9.9KB, 2026-09-22)
- [`close-w152.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w152.md) (12.4KB, 2026-09-22)
- [`close-w153.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w153.md) (14.2KB, 2026-09-22)
- [`close-w154b.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w154b.md) (20.3KB, 2026-09-22)
- [`close-w155.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w155.md) (11.2KB, 2026-09-22)
- [`close-w156c.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w156c.md) (19.4KB, 2026-09-22)
- [`close-w157.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w157.md) (11.0KB, 2026-09-22)
- [`close-w158.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w158.md) (19.7KB, 2026-09-22)
- [`close-w159.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w159.md) (15.8KB, 2026-09-22)
- [`close-w160.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close-w160.md) (18.8KB, 2026-09-22)
- [`close.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/close.md) (12.8KB, 2026-09-22)
- [`final-synthesis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/final-synthesis.md) (15.7KB, 2026-09-22)
- [`finish-line.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/finish-line.md) (18.9KB, 2026-09-22)
- [`p10-final-synthesis.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/p10-final-synthesis.md) (16.1KB, 2026-09-22)
- [`pre-freeze-hygiene.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/pre-freeze-hygiene.md) (15.3KB, 2026-09-22)
- [`status-reconciliation-2026-09-13.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/status-reconciliation-2026-09-13.md) (467B, 2026-09-22)
- [`todo-status-reconciliation-2026-09-13.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/todo-status-reconciliation-2026-09-13.md) (432B, 2026-09-21)
- [`wave297-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave297-final.md) (13.2KB, 2026-09-23)
- [`wave298-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave298-final.md) (19.8KB, 2026-09-23)

**Historical (15 files, not cited by reviewer-facing surfaces):**

- [`p5-final-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/p5-final-verify.md) (4.7KB, 2026-09-22)
- [`w276-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/w276-final.md) (17.4KB, 2026-09-22)
- [`wave277-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave277-final.md) (10.3KB, 2026-09-22)
- [`wave278-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave278-final.md) (9.2KB, 2026-09-22)
- [`wave280-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave280-final.md) (23.2KB, 2026-09-22)
- [`wave286-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave286-final.md) (28.7KB, 2026-09-22)
- [`wave287-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave287-final.md) (5.9KB, 2026-09-22)
- [`wave291-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave291-final.md) (22.0KB, 2026-09-23)
- [`wave292-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave292-final.md) (9.7KB, 2026-09-23)
- [`wave293-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave293-final.md) (10.5KB, 2026-09-23)
- [`wave294-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave294-final.md) (18.1KB, 2026-09-23)
- [`wave300-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave300-final.md) (27.0KB, 2026-09-23)
- [`wave301-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave301-final.md) (15.8KB, 2026-09-23)
- [`wave302-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave302-final.md) (24.9KB, 2026-09-23)
- [`wave303-final.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/final_verify/wave303-final.md) (68.3KB, 2026-09-23)

---

### Cluster: `governance` — Governance (scope, audit, gap, condition, placeholder, cross-cutting)

**Files: 35** (active: 19, historical: 16)

Governance (scope, audit, gap, condition, placeholder, cross-cutting). This cluster is part of the project's audit surface for governance.

**Active (cited by ≥1 reviewer-facing surface):**

- [`evidence-freetraj-blocker.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/evidence-freetraj-blocker.md) (665B, 2026-09-22)
- [`layer1-adapters-status.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/layer1-adapters-status.md) (690B, 2026-09-22)
- [`p2-real-state-shape.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/p2-real-state-shape.md) (6.6KB, 2026-09-22)
- [`p3-build-initial-state.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/p3-build-initial-state.md) (12.3KB, 2026-09-22)
- [`p3-root-cause.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/p3-root-cause.md) (12.1KB, 2026-09-22)
- [`p4-velocity-field-noop.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/p4-velocity-field-noop.md) (12.4KB, 2026-09-22)
- [`EPSILON_DIRECTION.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/EPSILON_DIRECTION.md) (17.6KB, 2026-09-21)
- [`PHASE4_DOCSTRING_AUDIT.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/PHASE4_DOCSTRING_AUDIT.md) (12.6KB, 2026-09-21)
- [`empirical-conditions.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/empirical-conditions.md) (16.0KB, 2026-09-21)
- [`framework-model-gap-cpu-2026-09-13.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/framework-model-gap-cpu-2026-09-13.md) (713B, 2026-09-21)
- [`jmaa-theory-applications.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/jmaa-theory-applications.md) (6.0KB, 2026-09-22)
- [`todo-six-plan-status-2026-09-13.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/todo-six-plan-status-2026-09-13.md) (785B, 2026-09-21)
- [`wave287-p-scheduler-codepath-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave287-p-scheduler-codepath-audit.md) (28.7KB, 2026-09-22)
- [`wave289-p1-honest-reframe.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave289-p1-honest-reframe.md) (18.2KB, 2026-09-23)
- [`wave292-p1-pipeline-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave292-p1-pipeline-inventory.md) (40.0KB, 2026-09-23)
- [`wave298-p1-code-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave298-p1-code-innovations.md) (29.7KB, 2026-09-23)
- [`wave298-p2-methodology-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave298-p2-methodology-innovations.md) (30.9KB, 2026-09-23)
- [`wave298-p6-deep-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave298-p6-deep-innovations.md) (40.4KB, 2026-09-23)
- [`wave326-crossdoc-metrics-snapshot.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave326-crossdoc-metrics-snapshot.md) (20.6KB, 2026-09-23)

**Historical (16 files, not cited by reviewer-facing surfaces):**

- [`wave275-p3-flatten.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave275-p3-flatten.md) (5.6KB, 2026-09-22)
- [`wave281/p-partial-evidence.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave281/p-partial-evidence.md) (1.5KB, 2026-09-22)
- [`wave288-p1-honest-progress-summary.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave288-p1-honest-progress-summary.md) (51.1KB, 2026-09-23)
- [`wave294-p1-re-inventory.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave294-p1-re-inventory.md) (18.3KB, 2026-09-23)
- [`wave294-p4-cross-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave294-p4-cross-verify.md) (24.0KB, 2026-09-23)
- [`wave297-p8-cross-verify.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave297-p8-cross-verify.md) (45.2KB, 2026-09-23)
- [`wave298-p4-engineering-innovations.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave298-p4-engineering-innovations.md) (35.0KB, 2026-09-23)
- [`wave298-p5-literature-compare.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave298-p5-literature-compare.md) (34.3KB, 2026-09-23)
- [`wave335-self-check-verification.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave335-self-check-verification.md) (17.1KB, 2026-09-23)
- [`wave337-final-self-check-report.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave337-final-self-check-report.md) (14.5KB, 2026-09-23)
- [`wave338-h7-cleanup.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave338-h7-cleanup.md) (10.0KB, 2026-09-23)
- [`wave339-b6-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave339-b6-fixes.md) (9.6KB, 2026-09-23)
- [`wave339-h8-fixes.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave339-h8-fixes.md) (6.3KB, 2026-09-23)
- [`wave341-deep-audit.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave341-deep-audit.md) (52.5KB, 2026-09-25)
- [`wave341-readme-cosine-vs-codim.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave341-readme-cosine-vs-codim.md) (23.0KB, 2026-09-25)
- [`wave346-byte-page-fix.md`](https://github.com/silverenternal/flowa-multistep-reinference/blob/main/docs/audit/governance/wave346-byte-page-fix.md) (8.7KB, 2026-09-25)

---

## Maintenance

- **New audit file?** Place it under `docs/audit/<cluster>/waveNNN-*.md`; the cluster is determined by filename keyword scan (see `cluster_order` in `/tmp/regen_index.py`). Files at the top level are classified by filename + first-30-line content scan.
- **Active vs Historical flag?** Re-run citation-grep against the active surfaces list (see `ACTIVE_SURFACES` + `TNNLS_SURFACES` in `/tmp/regen_index.py`).
- **Cluster boundaries are heuristic.** If a file lands in the wrong cluster because its filename is generic, the filename keyword was the primary signal — content keywords were the fallback. Inspect the first 30 lines of the file to confirm.

_This file complements the per-wave `INDEX.md` table. The per-wave table is authoritative for *"what did Wave N do?"*; this topic-cluster index is authoritative for *"what does the project claim about X?"._
