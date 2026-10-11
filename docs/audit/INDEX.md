# Project Audit Index

> **Topic-cluster map of all `docs/audit/*.md` files.** Regenerated from on-disk layout (2026-10-11, Wave 384 documentation refresh). Reviewers can answer *"what does the project claim about X?"* by reading the cluster summary for X.

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
| `web_research` | Web research 2026 (FM literature surveys) | 1 | 0 | 1 |
| `engineering` | Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree) | 120 | 71 | 49 |
| `reproducibility` | Reproducibility (reproducibility-record, preregistration, reproduce-script) | 13 | 5 | 8 |
| `data_packaging` | Data packaging + manifest (sha256, csv, metric-ledger) | 23 | 10 | 13 |
| `push_state` | Push state (push-ready, freeze, release, submission) | 7 | 5 | 2 |
| `algorithm_4arm` | Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency) | 38 | 19 | 19 |
| `sweep_eval` | Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability) | 98 | 81 | 17 |
| `stats_method` | Statistical methodology (R5/R6, p-value, bonferroni, TOST) | 44 | 15 | 29 |
| `paper_claims` | Paper + claims (paper packaging, claim audit, paper-update) | 34 | 14 | 20 |
| `final_verify` | Final-verify (per-wave close-out, pre-push hygiene) | 37 | 22 | 15 |
| `governance` | Governance (scope, audit, gap, condition, placeholder, cross-cutting) | 45 | 25 | 20 |
| **TOTAL** | — | **509** | **306** | **203** |

---

## Cluster details

### Cluster: `cifar` — CIFAR-10 RF (Rectified Flow on CIFAR-10)

**Files: 7** (active: 5, historical: 2)

CIFAR-10 RF (Rectified Flow on CIFAR-10). This cluster is part of the project's audit surface for cifar.

**Active (cited by ≥1 reviewer-facing surface):**

- `cifar-reference-availability.md` (372B, 2026-09-22)
- `cifar-v4-audit.md` (7.2KB, 2026-09-22)
- `p6-cifar-rf-v4-honest-negative-curve.md` (11.3KB, 2026-09-22)
- `wave280-p-cifar-sweep-result.md` (15.6KB, 2026-09-22)
- `wave286-p-cifar-resweep-aggregated.md` (17.5KB, 2026-09-22)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- `p-cifar10-impl.md` (11.2KB, 2026-09-22)
- `wave275-p4-cifar10-proposal.md` (32.6KB, 2026-09-22)

---

### Cluster: `kanzi` — Kanzi (protein flow autoencoder)

**Files: 9** (active: 9, historical: 0)

Kanzi (protein flow autoencoder). This cluster is part of the project's audit surface for kanzi.

**Active (cited by ≥1 reviewer-facing surface):**

- `kanzi-fix.md` (3.8KB, 2026-09-22)
- `kanzi-gpu-sweep.md` (30.0KB, 2026-09-22)
- `kanzi-load-torch-fix.md` (5.0KB, 2026-09-22)
- `kanzi-nfe-bug.md` (7.7KB, 2026-09-22)
- `p1-kanzi-byte-stability-regression.md` (17.2KB, 2026-09-22)
- `p2-kanzi-n30-sweep.md` (7.7KB, 2026-09-22)
- `p2-kanzi-rerun.md` (7.1KB, 2026-09-22)
- `p3-kanzi-n1000-framework-inv-proj.md` (10.5KB, 2026-09-22)
- `p4-kanzi-full.md` (16.8KB, 2026-09-22)

---

### Cluster: `flowmol3` — FlowMol3 (molecular 3D flow matching)

**Files: 5** (active: 3, historical: 2)

FlowMol3 (molecular 3D flow matching). This cluster is part of the project's audit surface for flowmol3.

**Active (cited by ≥1 reviewer-facing surface):**

- `c-flowmol3-n1000.md` (15.0KB, 2026-09-22)
- `p2-flowmol3-dgl-fix-or-sanity.md` (11.1KB, 2026-09-22)
- `p3-flowmol3-n1000.md` (7.9KB, 2026-09-22)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- `p-flowmol3-impl.md` (9.3KB, 2026-09-22)
- `wave275-p4-flowmol3-proposal.md` (33.6KB, 2026-09-22)

---

### Cluster: `lineageflow` — LineageFlow (protein flow matching, HMMER + foldability + novelty)

**Files: 19** (active: 16, historical: 3)

LineageFlow (protein flow matching, HMMER + foldability + novelty). This cluster is part of the project's audit surface for lineageflow.

**Active (cited by ≥1 reviewer-facing surface):**

- `b-lineageflow-n1000-gpu.md` (10.2KB, 2026-09-22)
- `lineageflow-hmmer-poc.md` (4.7KB, 2026-09-22)
- `lineageflow-nfe-scan.md` (2.2KB, 2026-09-22)
- `p3-lineageflow-n30-sweep.md` (10.2KB, 2026-09-22)
- `p5-lineageflow-regression.md` (10.4KB, 2026-09-22)
- `data_packaging/hmmer-launch.md` (5.2KB, 2026-09-22)
- `engineering/hmmer-collect.md` (7.8KB, 2026-09-22)
- `engineering/hmmer-rederivation.md` (10.5KB, 2026-09-22)
- `sweep_eval/hmmer-launch.md` (6.3KB, 2026-09-22)
- `sweep_eval/novelty-diagnosis.md` (18.8KB, 2026-09-22)
- `sweep_eval/novelty-fix.md` (15.6KB, 2026-09-22)
- `sweep_eval/novelty-sweep-fixed.md` (14.0KB, 2026-09-22)
- `sweep_eval/novelty-sweep.md` (13.5KB, 2026-09-22)
- `sweep_eval/p1-pLDDT-inversion.md` (18.5KB, 2026-09-22)
- `sweep_eval/p2-foldability-sc-workers-per-gpu.md` (3.9KB, 2026-09-22)
- `sweep_eval/p3-run-foldability-propagate-workers-per-gpu.md` (5.9KB, 2026-09-22)

**Historical (3 files, not cited by reviewer-facing surfaces):**

- `p-k7-impl.md` (6.1KB, 2026-09-22)
- `p-lineageflow-impl.md` (10.1KB, 2026-09-22)
- `wave275-p4-lineageflow-proposal.md` (24.1KB, 2026-09-22)

---

### Cluster: `freqflow` — FreqFlow + MM-FM (frequency / multimodal flow)

**Files: 3** (active: 3, historical: 0)

FreqFlow + MM-FM (frequency / multimodal flow). This cluster is part of the project's audit surface for freqflow.

**Active (cited by ≥1 reviewer-facing surface):**

- `p3-freqflow-honest-disclosure.md` (12.6KB, 2026-09-22)
- `p5-freqflow-n1000.md` (8.4KB, 2026-09-22)
- `mm-fm-unblock-investigation.md` (10.0KB, 2026-09-21)

---

### Cluster: `mnist` — MNIST FM (MNIST flow matching)

**Files: 4** (active: 2, historical: 2)

MNIST FM (MNIST flow matching). This cluster is part of the project's audit surface for mnist.

**Active (cited by ≥1 reviewer-facing surface):**

- `wave280-p-r5c-sweep-result.md` (17.4KB, 2026-09-22)
- `wf334-r5c-regime-curve.md` (12.2KB, 2026-09-23)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- `p-mnist-impl.md` (10.6KB, 2026-09-22)
- `wave275-p4-mnist-proposal.md` (39.9KB, 2026-09-23)

---

### Cluster: `2d_toy` — 2D toy FM (two-dim flow matching, 8gaussian)

**Files: 2** (active: 1, historical: 1)

2D toy FM (two-dim flow matching, 8gaussian). This cluster is part of the project's audit surface for 2d_toy.

**Active (cited by ≥1 reviewer-facing surface):**

- `wave286-p-paper-quantity-ablation.md` (18.9KB, 2026-09-22)

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `wave282-p-cosine-vs-paper-controllers.md` (20.7KB, 2026-09-22)

---

### Cluster: `web_research` — Web research 2026 (FM literature surveys)

**Files: 1** (active: 0, historical: 1)

Web research 2026 (FM literature surveys). This cluster is part of the project's audit surface for web_research.

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `INDEX_MAINTENANCE.md` (11.3KB, 2026-09-25)

---

### Cluster: `engineering` — Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree)

**Files: 120** (active: 71, historical: 49)

Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree). This cluster is part of the project's audit surface for engineering.

**Active (cited by ≥1 reviewer-facing surface):**

- `bridge-bug-design.md` (27.0KB, 2026-09-22)
- `cli-pr-prep.md` (33.9KB, 2026-09-22)
- `cli-verify.md` (11.8KB, 2026-09-22)
- `doc-cleanup.md` (12.8KB, 2026-09-22)
- `docstring-audit.md` (9.0KB, 2026-09-22)
- `eval.md` (11.4KB, 2026-09-22)
- `followup-w148.md` (8.8KB, 2026-09-22)
- `followup.md` (8.4KB, 2026-09-22)
- `headline-evidence.md` (9.7KB, 2026-09-22)
- `impl.md` (11.5KB, 2026-09-22)
- `inv-proj-final-fix.md` (19.4KB, 2026-09-22)
- `mypy-fix.md` (8.4KB, 2026-09-22)
- `number-consistency.md` (9.5KB, 2026-09-22)
- `p1-setup-w184.md` (8.7KB, 2026-09-22)
- `p1-setup.md` (15.1KB, 2026-09-22)
- `p2-verify.md` (5.0KB, 2026-09-22)
- `p3-integration.md` (13.1KB, 2026-09-22)
- `p3-journal-decision.md` (12.0KB, 2026-09-22)
- `p3-tier-aware.md` (11.5KB, 2026-09-22)
- `p4-plot.md` (9.4KB, 2026-09-22)
- `p4-table-aggregate.md` (12.3KB, 2026-09-22)
- `p5-gates.md` (8.0KB, 2026-09-22)
- `p5-results.md` (10.5KB, 2026-09-22)
- `pdf-warning-fixes.md` (2.6KB, 2026-09-22)
- `polish-execute.md` (10.1KB, 2026-09-22)
- `pr1-application.md` (3.2KB, 2026-09-22)
- `primitive-cli-design.md` (9.4KB, 2026-09-22)
- `push-and-fix.md` (9.7KB, 2026-09-22)
- `push-w156c.md` (6.7KB, 2026-09-22)
- `push-w158.md` (5.1KB, 2026-09-22)
- `push.md` (5.1KB, 2026-09-22)
- `ruff-cleanup.md` (9.2KB, 2026-09-22)
- `scripts-ruff-cleanup.md` (7.8KB, 2026-09-22)
- `tier1-polish.md` (9.4KB, 2026-09-22)
- `tmp-migration.md` (8.5KB, 2026-09-22)
- `todo-refactor.md` (9.8KB, 2026-09-22)
- `data_packaging/pdf-warning-zero.md` (3.7KB, 2026-09-22)
- `engineering-audit-2026-09-13.md` (4.9KB, 2026-09-21)
- `governance/pdf-warning-reduction.md` (5.3KB, 2026-09-22)
- `paper_claims/pdf-warning-reduction.md` (3.2KB, 2026-09-22)
- `wave268-strict-clean.md` (10.4KB, 2026-09-26)
- `wave290-p4-benchmark-fixed.md` (19.8KB, 2026-09-23)
- `wave291-p1-hypothesis-redesign.md` (26.8KB, 2026-09-23)
- `wave296-p1-architecture.md` (40.0KB, 2026-09-23)
- `wave296-p2-cache.md` (23.3KB, 2026-09-23)
- `wave297-p3-intro-rewritten.md` (15.0KB, 2026-09-23)
- `wave297-p4-framework-rewritten.md` (21.4KB, 2026-09-23)
- `wave297-p5-empirical-rewritten.md` (39.0KB, 2026-09-23)
- `wave297-p7-readme-updated.md` (11.5KB, 2026-09-23)
- `wave306-11-cell-alignment.md` (27.4KB, 2026-09-23)
- `wave306-fix-plan.md` (62.8KB, 2026-09-23)
- `wave307-data-archaeology.md` (49.9KB, 2026-09-23)
- `wave310-restoration-execution.md` (24.8KB, 2026-09-25)
- `wave311-restoration-execution.md` (18.5KB, 2026-09-23)
- `wave322-restoration-execution.md` (17.8KB, 2026-09-23)
- `wave347-final-4-gap-fix.md` (18.1KB, 2026-09-25)
- `wave348-link-fix.md` (15.7KB, 2026-09-25)
- `wave349-gpu-acceleration.md` (10.3KB, 2026-09-25)
- `wave349-impl.md` (24.3KB, 2026-09-25)
- `wave350-r1-materialize-status.md` (16.9KB, 2026-09-25)
- `wave351-thm5-numerical.md` (22.3KB, 2026-09-25)
- `wave352-framework-code-anchors.md` (13.8KB, 2026-09-25)
- `wave352-l-local-appendix.md` (20.5KB, 2026-09-25)
- `wave355-capability-token-example.md` (9.6KB, 2026-09-25)
- `wave356-data-availability-polish.md` (23.6KB, 2026-09-25)
- `wave356-highlights-polish.md` (22.7KB, 2026-09-25)
- `wave357-ruff-w292-fix.md` (18.5KB, 2026-09-25)
- `wave358-figures-md-polish.md` (15.3KB, 2026-09-25)
- `wave361-figures-sha-crosscheck.md` (23.0KB, 2026-09-25)
- `wave364-g38.md` (14.3KB, 2026-09-26)
- `wave384-project-audit.md` (14.1KB, 2026-10-11)

**Historical (49 files, not cited by reviewer-facing surfaces):**

- `c3-fix-summary.md` (14.4KB, 2026-09-22)
- `p3-number-verification.md` (36.8KB, 2026-09-22)
- `p5-ground-truth-corrections.md` (9.1KB, 2026-09-22)
- `review-layer4-docs-config.md` (11.3KB, 2026-09-22)
- `scheduler-per-cell-summary.md` (32.4KB, 2026-09-22)
- `wave275-p4-overview.md` (22.7KB, 2026-09-22)
- `wave279-plan-complete.md` (12.8KB, 2026-09-22)
- `wave279-user-decisions.md` (5.6KB, 2026-09-22)
- `wave287-p-ci-hardening.md` (9.9KB, 2026-09-22)
- `wave287-p-test-coverage.md` (8.9KB, 2026-09-22)
- `wave290-p2-driver-microfix.md` (17.4KB, 2026-09-23)
- `wave290-p5-workflow-paused-status.md` (16.4KB, 2026-09-23)
- `wave292-p2-config-genealogy.md` (37.1KB, 2026-09-23)
- `wave293-p3-fix-applied.md` (13.9KB, 2026-09-23)
- `wave296-p5-activation-log.md` (12.5KB, 2026-09-23)
- `wave296-p6-backward-compat.md` (12.7KB, 2026-09-23)
- `wave296-p7-fid-comparison.md` (10.8KB, 2026-09-23)
- `wave299-final-verification.md` (34.6KB, 2026-09-23)
- `wave301-day0-prompt.md` (18.1KB, 2026-09-23)
- `wave301-day2-execution-plan.md` (46.5KB, 2026-09-23)
- `wave301-day3-execution-plan.md` (45.7KB, 2026-09-23)
- `wave302-p2-exp-b1-smoke.md` (19.4KB, 2026-09-23)
- `wave308-d3-review.md` (25.7KB, 2026-09-23)
- `wave326-ci-design.md` (17.0KB, 2026-09-23)
- `wave326-ci-redesign-execution.md` (19.1KB, 2026-09-23)
- `wave326-data-integrity-design.md` (13.0KB, 2026-09-23)
- `wave326-readme-update.md` (8.0KB, 2026-09-23)
- `wave334-reviewer-prediction.md` (19.8KB, 2026-09-25)
- `wave338-phase2-mechanism.md` (11.9KB, 2026-09-23)
- `wave340-readme-update.md` (13.0KB, 2026-09-23)
- `wave351-cover-letter-helper.md` (13.3KB, 2026-09-25)
- `wave352-cover-letter-interactive.md` (18.1KB, 2026-09-25)
- `wave353-a2-placeholder-fill.md` (18.7KB, 2026-09-25)
- `wave353-conclusion-takeaways.md` (10.3KB, 2026-09-25)
- `wave353-pseudocode-blocks.md` (12.3KB, 2026-09-25)
- `wave354-cover-letter-scaffold.md` (15.7KB, 2026-09-25)
- `wave355-supplementary-polish.md` (21.8KB, 2026-09-25)
- `wave358-insights-gap-check.md` (33.6KB, 2026-09-25)
- `wave359-final-consolidated.md` (39.6KB, 2026-09-25)
- `wave360-cover-letter-interactive-ux.md` (14.5KB, 2026-09-25)
- `wave360-verification-outputs-xref.md` (13.6KB, 2026-09-25)
- `wave363-all-cell-recipes.md` (29.3KB, 2026-09-26)
- `wave363-k4-recipe.md` (11.9KB, 2026-09-26)
- `wave363-k7-recipe.md` (9.8KB, 2026-09-26)
- `wave363-r1-recipe.md` (16.5KB, 2026-09-26)
- `wave364-g11.md` (15.6KB, 2026-09-26)
- `wave364-g3.md` (20.8KB, 2026-09-26)
- `wave364-g34.md` (14.9KB, 2026-09-26)
- `wave368-p2-section-7-6-deep.md` (15.1KB, 2026-09-26)

---

### Cluster: `reproducibility` — Reproducibility (reproducibility-record, preregistration, reproduce-script)

**Files: 13** (active: 5, historical: 8)

Reproducibility (reproducibility-record, preregistration, reproduce-script). This cluster is part of the project's audit surface for reproducibility.

**Active (cited by ≥1 reviewer-facing surface):**

- `item4-tex-rewrite.md` (6.7KB, 2026-09-22)
- `p3-comparison.md` (5.5KB, 2026-09-22)
- `wave298-p3-reproducibility-innovations.md` (39.5KB, 2026-09-23)
- `wave324-d5-review.md` (8.0KB, 2026-09-23)
- `wave358-tables-md-polish.md` (22.0KB, 2026-09-25)

**Historical (8 files, not cited by reviewer-facing surfaces):**

- `p5-experiment-setup.md` (19.4KB, 2026-09-22)
- `p8-experiment-setup.md` (15.7KB, 2026-09-22)
- `wave303-day0-prompt.md` (24.0KB, 2026-09-23)
- `wave325-push-execution.md` (11.7KB, 2026-09-23)
- `wave353-ledger-examples.md` (8.9KB, 2026-09-25)
- `wave361-reproduce-scripts-verify.md` (14.3KB, 2026-09-25)
- `wave363-p2-master-verifier.md` (23.4KB, 2026-09-26)
- `wave366-p2-reproducibility-manifest.md` (16.4KB, 2026-09-26)

---

### Cluster: `data_packaging` — Data packaging + manifest (sha256, csv, metric-ledger)

**Files: 23** (active: 10, historical: 13)

Data packaging + manifest (sha256, csv, metric-ledger). This cluster is part of the project's audit surface for data_packaging.

**Active (cited by ≥1 reviewer-facing surface):**

- `fasta-generation.md` (9.5KB, 2026-09-22)
- `fix-design.md` (16.5KB, 2026-09-22)
- `tier1-metric-alignment.md` (9.3KB, 2026-09-22)
- `wave297-p6-limitations-rewritten.md` (39.1KB, 2026-09-23)
- `wave326-final-metrics-table.md` (11.5KB, 2026-09-23)
- `wave328-freeze-survey.md` (18.8KB, 2026-09-23)
- `wave331-data-fix.md` (4.1KB, 2026-09-23)
- `wave344-supplementary-bundle.md` (14.3KB, 2026-09-25)
- `wave354-manifest-sha256-refresh.md` (15.0KB, 2026-09-25)
- `wave355-final-sha256-refresh.md` (15.0KB, 2026-09-25)

**Historical (13 files, not cited by reviewer-facing surfaces):**

- `data-linkage-closure.md` (16.2KB, 2026-09-22)
- `data-linkage-plan.md` (28.5KB, 2026-09-22)
- `framework-inv-proj-re-run.md` (5.7KB, 2026-09-22)
- `implementation-plan.md` (49.2KB, 2026-09-22)
- `p1-data-gathering.md` (59.8KB, 2026-09-22)
- `p5-metrics-patch.md` (6.4KB, 2026-09-22)
- `wave275-p1-state-inventory.md` (20.4KB, 2026-09-22)
- `wave275-p2-metric-ledger.md` (5.9KB, 2026-09-22)
- `wave327-revised-q1-assessment.md` (29.8KB, 2026-09-23)
- `wave342-readme-update.md` (12.8KB, 2026-09-25)
- `wave355-verification-outputs-readme.md` (15.8KB, 2026-09-25)
- `wave360-supplementary-bundle-verify.md` (6.3KB, 2026-09-25)
- `wave367-p3-related-work.md` (10.5KB, 2026-09-26)

---

### Cluster: `push_state` — Push state (push-ready, freeze, release, submission)

**Files: 7** (active: 5, historical: 2)

Push state (push-ready, freeze, release, submission). This cluster is part of the project's audit surface for push_state.

**Active (cited by ≥1 reviewer-facing surface):**

- `submission-polish.md` (9.7KB, 2026-09-22)
- `submission-prep.md` (18.4KB, 2026-09-22)
- `verify-submission-readiness.md` (10.4KB, 2026-09-22)
- `wave356-submission-checklist-review.md` (23.6KB, 2026-09-25)
- `wave358-submission-checklist-reaudit.md` (24.1KB, 2026-09-25)

**Historical (2 files, not cited by reviewer-facing surfaces):**

- `wave324-submission-prep.md` (11.5KB, 2026-09-23)
- `wave365-submission-readiness.md` (23.6KB, 2026-09-26)

---

### Cluster: `algorithm_4arm` — Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency)

**Files: 38** (active: 19, historical: 19)

Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency). This cluster is part of the project's audit surface for algorithm_4arm.

**Active (cited by ≥1 reviewer-facing surface):**

- `p-r6-impl.md` (16.1KB, 2026-09-22)
- `p1-4arm-power-analysis.md` (8.3KB, 2026-09-22)
- `p1-design.md` (17.7KB, 2026-09-22)
- `p2-eval-w182.md` (18.2KB, 2026-09-22)
- `p2-eval.md` (17.5KB, 2026-09-22)
- `p2-impl.md` (6.7KB, 2026-09-22)
- `p2-progress.md` (6.8KB, 2026-09-22)
- `p2-wallclock-fix.md` (12.2KB, 2026-09-22)
- `p3-4arm-power.md` (14.6KB, 2026-09-22)
- `p3-comparison.md` (3.2KB, 2026-09-22)
- `p3-rerun.md` (8.8KB, 2026-09-22)
- `p4-aggregate.md` (9.7KB, 2026-09-22)
- `p4-theorem1-power.md` (19.6KB, 2026-09-22)
- `p6-boundary-framing.md` (12.9KB, 2026-09-22)
- `push.md` (4.1KB, 2026-09-22)
- `theory-audit.md` (22.8KB, 2026-09-22)
- `algorithm-gap-investigation.md` (25.3KB, 2026-09-21)
- `wave311-path-a-lemma-1.md` (18.6KB, 2026-09-23)
- `wave322-path-a-lemmas-2-3.md` (24.8KB, 2026-09-23)

**Historical (19 files, not cited by reviewer-facing surfaces):**

- `p3-f-side-actual-values.md` (15.3KB, 2026-09-22)
- `p3-post-hoc-sensitivity.md` (9.7KB, 2026-09-22)
- `p6-repo-naming.md` (6.7KB, 2026-09-22)
- `wave292-p3-crosscheck.md` (30.7KB, 2026-09-23)
- `wave293-p1-locate-sign.md` (19.2KB, 2026-09-23)
- `wave294-p2-medium-fixed.md` (11.9KB, 2026-09-23)
- `wave296-p3-a-class-wired.md` (20.5KB, 2026-09-23)
- `wave296-p4-b-class-wired.md` (22.5KB, 2026-09-23)
- `wave300-p3-resolution-plan.md` (27.5KB, 2026-09-23)
- `wave302-p5-codim-deep-dive.md` (15.1KB, 2026-09-23)
- `wave303-day0-14-plan.md` (69.0KB, 2026-09-23)
- `wave305-day0-risk-package.md` (37.8KB, 2026-09-23)
- `wave336-r5b-mechanism.md` (20.6KB, 2026-09-23)
- `wave353-limitations-vendor-note.md` (14.6KB, 2026-09-25)
- `wave357-lean-sorry-discharge.md` (41.5KB, 2026-09-25)
- `wave364-g20.md` (15.5KB, 2026-09-26)
- `wave367-p5-theory-de-wave.md` (15.1KB, 2026-09-26)
- `wave368-p1-new-section-2-2.md` (9.6KB, 2026-09-26)
- `wave379-mechanism-synthesis.md` (6.2KB, 2026-09-27)

---

### Cluster: `sweep_eval` — Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability)

**Files: 98** (active: 81, historical: 17)

Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability). This cluster is part of the project's audit surface for sweep_eval.

**Active (cited by ≥1 reviewer-facing surface):**

- `cross-model-nfe-curve.md` (9.1KB, 2026-09-22)
- `cuda-fix-sweep-recovery.md` (25.4KB, 2026-09-22)
- `dispatch-verification.md` (12.2KB, 2026-09-22)
- `eval-w174.md` (13.3KB, 2026-09-22)
- `eval.md` (11.3KB, 2026-09-22)
- `fair-fasta-generation.md` (10.6KB, 2026-09-22)
- `fasta-generation.md` (7.4KB, 2026-09-22)
- `finish.md` (5.5KB, 2026-09-22)
- `gpu-verify.md` (9.7KB, 2026-09-22)
- `headline-evidence-audit.md` (13.1KB, 2026-09-22)
- `item1-ablation.md` (8.9KB, 2026-09-22)
- `item2-hp-sweep.md` (7.7KB, 2026-09-22)
- `k1-rc5-launch-w156.md` (13.9KB, 2026-09-22)
- `k1-rc5-launch.md` (8.2KB, 2026-09-22)
- `k1-rc5-preflight.md` (6.7KB, 2026-09-22)
- `k1-rerun.md` (11.0KB, 2026-09-22)
- `k6-sweep-launch.md` (11.6KB, 2026-09-22)
- `k6-verification.md` (8.8KB, 2026-09-22)
- `n-rounds-flag.md` (6.5KB, 2026-09-22)
- `nfe-curve.md` (14.4KB, 2026-09-22)
- `nfe-flag.md` (7.9KB, 2026-09-22)
- `nfe-real.md` (10.3KB, 2026-09-22)
- `omegafold-provisioning.md` (14.3KB, 2026-09-22)
- `p1-design-w178.md` (21.9KB, 2026-09-22)
- `p1-design-w179.md` (11.3KB, 2026-09-22)
- `p1-design.md` (10.7KB, 2026-09-22)
- `p1-investigation.md` (12.2KB, 2026-09-22)
- `p1-revert-all.md` (5.7KB, 2026-09-22)
- `p1-setup-w181.md` (13.2KB, 2026-09-22)
- `p1-setup-w182.md` (14.8KB, 2026-09-22)
- `p1-setup-w186.md` (5.1KB, 2026-09-22)
- `p1-setup.md` (10.2KB, 2026-09-22)
- `p2-empirical-bl.md` (11.9KB, 2026-09-22)
- `p2-eval.md` (13.8KB, 2026-09-22)
- `p2-fasta-generation.md` (8.9KB, 2026-09-22)
- `p2-generate-w183.md` (20.0KB, 2026-09-22)
- `p2-generate-w184.md` (10.7KB, 2026-09-22)
- `p2-generate.md` (10.3KB, 2026-09-22)
- `p2-post-cd70821-2d-sweep.md` (7.9KB, 2026-09-22)
- `p3-comparison.md` (8.5KB, 2026-09-22)
- `p3-eval-w183.md` (18.3KB, 2026-09-22)
- `p3-eval-w184.md` (9.0KB, 2026-09-22)
- `p3-eval-w186.md` (11.9KB, 2026-09-22)
- `p3-eval.md` (10.8KB, 2026-09-22)
- `p3-fasta-ladder.md` (6.2KB, 2026-09-22)
- `p3-sanity.md` (9.5KB, 2026-09-22)
- `p3-tightness.md` (15.2KB, 2026-09-22)
- `p4-aggregate-w183.md` (7.0KB, 2026-09-22)
- `p4-aggregate.md` (16.4KB, 2026-09-22)
- `p4-aggregation.md` (13.6KB, 2026-09-22)
- `p4-cross-adapter-ablation.md` (11.9KB, 2026-09-22)
- `p4-nfe-curve-w168.md` (12.8KB, 2026-09-22)
- `p4-nfe-curve.md` (12.0KB, 2026-09-22)
- `p5-plot.md` (7.7KB, 2026-09-22)
- `p6-e2e-eval.md` (7.8KB, 2026-09-22)
- `p6-paper.md` (5.5KB, 2026-09-22)
- `rc4-ablation-fix.md` (5.6KB, 2026-09-22)
- `restart-blend-analysis.md` (12.9KB, 2026-09-22)
- `restart-over-application.md` (11.9KB, 2026-09-22)
- `shape-fix-resweep.md` (22.1KB, 2026-09-22)
- `sweeps-collect.md` (6.2KB, 2026-09-22)
- `validation-experiment.md` (17.3KB, 2026-09-22)
- `w2-n1000-reruns.md` (21.6KB, 2026-09-22)
- `wave280-p-k1-sweep-result.md` (18.6KB, 2026-09-22)
- `wave280-p-k4k5-sweep-result.md` (11.2KB, 2026-09-22)
- `wave280-p-k7-sweep-result.md` (7.6KB, 2026-09-22)
- `wave280-p-r1-sweep-result.md` (11.1KB, 2026-09-22)
- `wave280-p-r3-sweep-result.md` (6.7KB, 2026-09-22)
- `wave280-p-r6-sweep-result.md` (12.5KB, 2026-09-22)
- `wave286-p-fid-gpu-fix.md` (8.1KB, 2026-09-22)
- `wave286-p-fid-gpu-verify.md` (11.8KB, 2026-09-22)
- `wave290-p1-bottleneck-confirmed.md` (18.1KB, 2026-09-23)
- `wave290-p3-batched-harness.md` (13.0KB, 2026-09-23)
- `wave291-p3-1seed-results.md` (6.2KB, 2026-09-23)
- `wave291-p5-3seed-results.md` (9.7KB, 2026-09-23)
- `wave307-archaeology-summary.md` (19.7KB, 2026-09-23)
- `wave311-d1-review.md` (21.9KB, 2026-09-23)
- `wave338-p5-r3-dgl-fix-and-sweep.md` (11.5KB, 2026-09-23)
- `wave350-thm5.md` (14.3KB, 2026-09-25)
- `wave353-h2h-ablation-refs.md` (13.4KB, 2026-09-25)
- `wave357-k5-k6-camera-ready.md` (22.8KB, 2026-09-25)

**Historical (17 files, not cited by reviewer-facing surfaces):**

- `b-config-scattering-audit.md` (19.3KB, 2026-09-22)
- `framework-synth-sweep.md` (10.5KB, 2026-09-22)
- `k1-rc5-3arm-preflight.md` (8.4KB, 2026-09-22)
- `p1-restore-r4-r5.md` (9.2KB, 2026-09-22)
- `p5-doc-consolidation.md` (20.2KB, 2026-09-22)
- `wave287-p-adversarial-sweep.md` (8.5KB, 2026-09-22)
- `wave291-p2-sweep-driver.md` (12.8KB, 2026-09-23)
- `wave291-p4-regime-analysis.md` (16.6KB, 2026-09-23)
- `wave293-p4-related-docs.md` (12.6KB, 2026-09-23)
- `wave301-day1-execution-plan.md` (38.7KB, 2026-09-23)
- `wave302-p1-regime-sweep-design.md` (30.4KB, 2026-09-23)
- `wave330-zh-review-version.md` (4.0KB, 2026-09-23)
- `wave356-archive-cleanup.md` (7.6KB, 2026-09-25)
- `wave359-k1-rc5-drift33-fix.md` (13.7KB, 2026-09-25)
- `wave359-lean-build-verify.md` (22.8KB, 2026-09-25)
- `wave363-k1-recipe.md` (16.4KB, 2026-09-26)
- `wave367-p2-intro-contributions.md` (14.0KB, 2026-09-26)

---

### Cluster: `stats_method` — Statistical methodology (R5/R6, p-value, bonferroni, TOST)

**Files: 44** (active: 15, historical: 29)

Statistical methodology (R5/R6, p-value, bonferroni, TOST). This cluster is part of the project's audit surface for stats_method.

**Active (cited by ≥1 reviewer-facing surface):**

- `p1-power-spec.md` (30.2KB, 2026-09-22)
- `p1-r3-uplift.md` (12.1KB, 2026-09-22)
- `p1-r5c-underflow-fix.md` (5.4KB, 2026-09-22)
- `p2-r-level-power.md` (19.0KB, 2026-09-22)
- `p3-r3-cross-seed.md` (5.7KB, 2026-09-22)
- `p4-r-level-refresh.md` (7.6KB, 2026-09-22)
- `pr2-application.md` (17.7KB, 2026-09-22)
- `wave310-r6-tier-aware-upgrade.md` (14.1KB, 2026-09-23)
- `wave350-r5b-figure.md` (15.9KB, 2026-09-25)
- `wave350-r6-live-attempt.md` (20.6KB, 2026-09-25)
- `wave351-r3-vendor-fix-status.md` (20.0KB, 2026-09-25)
- `wave351-r5a-n10.md` (11.2KB, 2026-09-25)
- `wave352-claims-r5a-update.md` (18.3KB, 2026-09-25)
- `wave357-r3-rdkit-blocker-doc.md` (28.5KB, 2026-09-25)
- `wave357-r6-gpu-scope.md` (40.7KB, 2026-09-25)

**Historical (29 files, not cited by reviewer-facing surfaces):**

- `p1-fix-r2-numbers.md` (9.4KB, 2026-09-22)
- `p1-r5b-fix.md` (11.5KB, 2026-09-22)
- `p2-r2-re-audit.md` (14.1KB, 2026-09-22)
- `p3-r3-re-audit.md` (19.0KB, 2026-09-22)
- `p3-r6-uplift.md` (8.5KB, 2026-09-22)
- `p4-r6-re-audit.md` (22.5KB, 2026-09-22)
- `p6-non-inferiority.md` (3.7KB, 2026-09-22)
- `wave275-p4-r6-proposal.md` (25.8KB, 2026-09-22)
- `wave302-p4-r6-replication.md` (11.4KB, 2026-09-23)
- `wave347-r5a-ds-aggregation-clarification.md` (15.7KB, 2026-09-25)
- `wave352-r6-status.md` (17.2KB, 2026-09-25)
- `wave354-r5b-figure-verify.md` (19.0KB, 2026-09-25)
- `wave359-r6-gpu-scope-cuda0.md` (35.7KB, 2026-09-25)
- `wave361-r-level-inventory-refresh.md` (26.1KB, 2026-09-25)
- `wave361-r6-forensic-evidence-chain.md` (13.7KB, 2026-09-26)
- `wave361-r6-launch-attempt.md` (8.2KB, 2026-09-25)
- `wave361-r6-launch-discrepancy.md` (8.8KB, 2026-09-25)
- `wave362-p1-r6-recipe.md` (16.0KB, 2026-09-26)
- `wave362-p2-verify-r6-recipe.md` (18.4KB, 2026-09-26)
- `wave362-r6-recipe.md` (31.8KB, 2026-09-26)
- `wave363-r2-recipe.md` (17.6KB, 2026-09-26)
- `wave363-r3-recipe.md` (27.0KB, 2026-09-26)
- `wave363-r5a-recipe.md` (18.3KB, 2026-09-26)
- `wave363-r5b-recipe.md` (14.3KB, 2026-09-26)
- `wave363-r5c-recipe.md` (17.6KB, 2026-09-26)
- `wave364-g15.md` (19.8KB, 2026-09-26)
- `wave364-p1-gap-selection-memo.md` (26.9KB, 2026-09-26)
- `wave366-p3-r6-recipe-citation.md` (16.9KB, 2026-09-26)
- `wave368-p3-section-7-8-deep.md` (10.8KB, 2026-09-26)

---

### Cluster: `paper_claims` — Paper + claims (paper packaging, claim audit, paper-update)

**Files: 34** (active: 14, historical: 20)

Paper + claims (paper packaging, claim audit, paper-update). This cluster is part of the project's audit surface for paper_claims.

**Active (cited by ≥1 reviewer-facing surface):**

- `agent3-pdf-generation.md` (6.8KB, 2026-09-22)
- `d-paper-package-update.md` (10.8KB, 2026-09-22)
- `p3-clm057-update.md` (13.3KB, 2026-09-22)
- `wave297-p2-paper-design.md` (33.2KB, 2026-09-23)
- `wave309-paper-a-restoration-plan.md` (31.7KB, 2026-09-25)
- `wave323-typeset-execution.md` (14.5KB, 2026-09-23)
- `wave343-paper-fixes.md` (18.0KB, 2026-09-25)
- `wave345-cross-doc-fixes.md` (51.0KB, 2026-09-25)
- `wave353-a1-theorem4-derivation.md` (17.1KB, 2026-09-25)
- `wave354-p5-lean-subclaim-stubs.md` (25.0KB, 2026-09-25)
- `wave355-claims-deep-audit.md` (20.2KB, 2026-09-25)
- `wave356-pdf-rebuild.md` (16.6KB, 2026-09-25)
- `wave360-claims-status-summary.md` (10.9KB, 2026-09-25)
- `wave372-manuscript-claim-audit.md` (6.0KB, 2026-09-27)

**Historical (20 files, not cited by reviewer-facing surfaces):**

- `p4-paper-updates.md` (20.2KB, 2026-09-22)
- `p6-paper-polish-audit.md` (6.9KB, 2026-09-22)
- `wave293-p2-verify-direction.md` (10.9KB, 2026-09-23)
- `wave294-p3-low-paper-fixed.md` (9.6KB, 2026-09-23)
- `wave297-p1-paper-inventory.md` (19.5KB, 2026-09-23)
- `wave298-p7-paper-append.md` (20.5KB, 2026-09-23)
- `wave298-p8-claims-updated.md` (15.8KB, 2026-09-23)
- `wave299-paper-a-outline.md` (25.1KB, 2026-09-23)
- `wave299-paper-b-deferred.md` (17.2KB, 2026-09-23)
- `wave323-d3-review.md` (12.3KB, 2026-09-23)
- `wave328-freeze-manifest.md` (12.0KB, 2026-09-23)
- `wave342-claims-fixes.md` (18.7KB, 2026-09-25)
- `wave353-claims-consolidation.md` (13.0KB, 2026-09-25)
- `wave354-paper-final-polish.md` (18.5KB, 2026-09-25)
- `wave364-g31.md` (12.8KB, 2026-09-26)
- `wave364-g32.md` (15.7KB, 2026-09-26)
- `wave364-paper-polish-gaps.md` (7.1KB, 2026-09-26)
- `wave366-p1-abstract-disclosure.md` (6.6KB, 2026-09-26)
- `wave371-paper-strengths.md` (3.8KB, 2026-09-27)
- `wave381-paper-style-polish.md` (832B, 2026-09-27)

---

### Cluster: `final_verify` — Final-verify (per-wave close-out, pre-push hygiene)

**Files: 37** (active: 22, historical: 15)

Final-verify (per-wave close-out, pre-push hygiene). This cluster is part of the project's audit surface for final_verify.

**Active (cited by ≥1 reviewer-facing surface):**

- `close-remaining-debt.md` (26.9KB, 2026-09-22)
- `close-w150.md` (7.3KB, 2026-09-22)
- `close-w151.md` (9.9KB, 2026-09-22)
- `close-w152.md` (12.4KB, 2026-09-22)
- `close-w153.md` (14.2KB, 2026-09-22)
- `close-w154b.md` (20.3KB, 2026-09-22)
- `close-w155.md` (11.2KB, 2026-09-22)
- `close-w156c.md` (19.4KB, 2026-09-22)
- `close-w157.md` (11.0KB, 2026-09-22)
- `close-w158.md` (19.7KB, 2026-09-22)
- `close-w159.md` (15.8KB, 2026-09-22)
- `close-w160.md` (18.8KB, 2026-09-22)
- `close.md` (12.8KB, 2026-09-22)
- `final-synthesis.md` (15.7KB, 2026-09-22)
- `finish-line.md` (18.9KB, 2026-09-22)
- `p10-final-synthesis.md` (16.1KB, 2026-09-22)
- `pre-freeze-hygiene.md` (15.3KB, 2026-09-22)
- `status-reconciliation-2026-09-13.md` (467B, 2026-09-22)
- `todo-status-reconciliation-2026-09-13.md` (432B, 2026-09-21)
- `wave297-final.md` (13.2KB, 2026-09-23)
- `wave298-final.md` (19.8KB, 2026-09-23)
- `wave352-sec10-9-close-out.md` (22.1KB, 2026-09-25)

**Historical (15 files, not cited by reviewer-facing surfaces):**

- `p5-final-verify.md` (4.7KB, 2026-09-22)
- `w276-final.md` (17.4KB, 2026-09-22)
- `wave277-final.md` (10.3KB, 2026-09-22)
- `wave278-final.md` (9.2KB, 2026-09-22)
- `wave280-final.md` (23.2KB, 2026-09-22)
- `wave286-final.md` (28.7KB, 2026-09-22)
- `wave287-final.md` (5.9KB, 2026-09-22)
- `wave291-final.md` (22.0KB, 2026-09-23)
- `wave292-final.md` (9.7KB, 2026-09-23)
- `wave293-final.md` (10.5KB, 2026-09-23)
- `wave294-final.md` (18.1KB, 2026-09-23)
- `wave300-final.md` (27.0KB, 2026-09-23)
- `wave301-final.md` (15.8KB, 2026-09-23)
- `wave302-final.md` (24.9KB, 2026-09-23)
- `wave303-final.md` (68.3KB, 2026-09-23)

---

### Cluster: `governance` — Governance (scope, audit, gap, condition, placeholder, cross-cutting)

**Files: 45** (active: 25, historical: 20)

Governance (scope, audit, gap, condition, placeholder, cross-cutting). This cluster is part of the project's audit surface for governance.

**Active (cited by ≥1 reviewer-facing surface):**

- `evidence-freetraj-blocker.md` (665B, 2026-09-22)
- `layer1-adapters-status.md` (690B, 2026-09-22)
- `p2-real-state-shape.md` (6.6KB, 2026-09-22)
- `p3-build-initial-state.md` (12.3KB, 2026-09-22)
- `p3-root-cause.md` (12.1KB, 2026-09-22)
- `p4-velocity-field-noop.md` (12.4KB, 2026-09-22)
- `EPSILON_DIRECTION.md` (17.6KB, 2026-09-21)
- `PHASE4_DOCSTRING_AUDIT.md` (12.6KB, 2026-09-21)
- `empirical-conditions.md` (16.0KB, 2026-09-21)
- `framework-model-gap-cpu-2026-09-13.md` (713B, 2026-09-21)
- `jmaa-theory-applications.md` (6.0KB, 2026-09-22)
- `todo-six-plan-status-2026-09-13.md` (785B, 2026-09-21)
- `wave287-p-scheduler-codepath-audit.md` (28.7KB, 2026-09-22)
- `wave289-p1-honest-reframe.md` (18.2KB, 2026-09-23)
- `wave292-p1-pipeline-inventory.md` (40.0KB, 2026-09-23)
- `wave298-p1-code-innovations.md` (29.7KB, 2026-09-23)
- `wave298-p2-methodology-innovations.md` (30.9KB, 2026-09-23)
- `wave298-p6-deep-innovations.md` (40.4KB, 2026-09-23)
- `wave326-crossdoc-metrics-snapshot.md` (20.6KB, 2026-09-23)
- `wave346-byte-page-fix.md` (8.7KB, 2026-09-25)
- `wave349-gap-audit.md` (14.4KB, 2026-09-25)
- `wave357-k4-saturation-scope.md` (29.6KB, 2026-09-25)
- `wave361-consolidated-results-index.md` (5.1KB, 2026-09-25)
- `wave373-inference-dynamics-positioning.md` (3.6KB, 2026-09-27)
- `wave375-image-feedback-path.md` (8.6KB, 2026-09-27)

**Historical (20 files, not cited by reviewer-facing surfaces):**

- `wave275-p3-flatten.md` (5.6KB, 2026-09-22)
- `wave281/p-partial-evidence.md` (1.5KB, 2026-09-22)
- `wave288-p1-honest-progress-summary.md` (51.1KB, 2026-09-23)
- `wave294-p1-re-inventory.md` (18.3KB, 2026-09-23)
- `wave294-p4-cross-verify.md` (24.0KB, 2026-09-23)
- `wave297-p8-cross-verify.md` (45.2KB, 2026-09-23)
- `wave298-p4-engineering-innovations.md` (35.0KB, 2026-09-23)
- `wave298-p5-literature-compare.md` (34.3KB, 2026-09-23)
- `wave335-self-check-verification.md` (17.1KB, 2026-09-23)
- `wave337-final-self-check-report.md` (14.5KB, 2026-09-23)
- `wave338-h7-cleanup.md` (10.0KB, 2026-09-23)
- `wave339-b6-fixes.md` (9.6KB, 2026-09-23)
- `wave339-h8-fixes.md` (6.3KB, 2026-09-23)
- `wave341-deep-audit.md` (52.5KB, 2026-09-25)
- `wave341-readme-cosine-vs-codim.md` (23.0KB, 2026-09-25)
- `wave358-index-maintenance-doc.md` (7.9KB, 2026-09-25)
- `wave374-final-typeset-check.md` (1.9KB, 2026-09-27)
- `wave380-mechanism-restructure.md` (1.7KB, 2026-09-27)
- `wave382-abstract-introduction-polish.md` (805B, 2026-09-27)
- `wave383-reformulation-positioning.md` (1.0KB, 2026-09-27)

---

## Maintenance

- **New audit file?** Place it under `docs/audit/<cluster>/waveNNN-*.md`; the cluster is determined by filename keyword scan (see `cluster_order` in `/tmp/regen_index.py`). Files at the top level are classified by filename + first-30-line content scan.
- **Active vs Historical flag?** Re-run citation-grep against the active surfaces list (see `ACTIVE_SURFACES` + `TNNLS_SURFACES` in `/tmp/regen_index.py`).
- **Cluster boundaries are heuristic.** If a file lands in the wrong cluster because its filename is generic, the filename keyword was the primary signal — content keywords were the fallback. Inspect the first 30 lines of the file to confirm.

_This file complements the per-wave `INDEX.md` table. The per-wave table is authoritative for *"what did Wave N do?"*; this topic-cluster index is authoritative for *"what does the project claim about X?"._
