# Project Audit Index

> **Topic-cluster map of every `docs/audit/*.md` record.** Generated — do not
> hand-edit. Refresh with `python3 tools/regen_audit_index.py`; the algorithm and
> the frozen cluster boundaries are described in
> [`INDEX_MAINTENANCE.md`](INDEX_MAINTENANCE.md). Reviewers can answer *"what does
> the project claim about X?"* by reading the cluster summary for X.

Records are grouped into 25 frozen topic clusters. A record
under `docs/audit/<cluster>/` is listed by bare filename. Placement is a
filename keyword scan; the five topic clusters may additionally read the
first 40 lines, and the per-model clusters never do. The `GAP-NN` series
goes to `governance` unless its filename names a model. Unmatched records
fall back to `governance`.

**Active** = cited by at least one of the 18 reviewer-facing
surfaces or any `tnnls_submission/*.md` file. **Historical** = not cited;
preserved for the per-wave audit trail.

---

## How to use this index

1. **Pick the cluster that matches your question** (CIFAR-10, Kanzi,
   LineageFlow, Algorithm / Theorem 1, Statistical methodology, ...).
2. **Read the cluster summary** — one paragraph, written without wave numbers,
   describing what the project claims and where the evidence lives.
3. **Open the active records first** — those are cited by reviewer-facing docs.
4. **Historical records** trace how a result evolved; skip them on a first read.

---

## Cluster map

| Cluster | Topic | Files | Active | Historical |
|---------|-------|------:|------:|-----------:|
| `cifar` | CIFAR-10 RF (Rectified Flow on CIFAR-10) | 7 | 5 | 2 |
| `kanzi` | Kanzi (protein flow autoencoder) | 10 | 9 | 1 |
| `flowmol3` | FlowMol3 (molecular 3D flow matching) | 7 | 4 | 3 |
| `lineageflow` | LineageFlow (protein flow matching, HMMER + foldability + novelty) | 23 | 17 | 6 |
| `freqflow` | FreqFlow + MM-FM (frequency / multimodal flow) | 3 | 3 | 0 |
| `mnist` | MNIST FM (MNIST flow matching) | 5 | 2 | 3 |
| `brai` | BRAI perturbation (Bounded-Range Adaptive Integration) | 0 | 0 | 0 |
| `2d_toy` | 2D toy FM (two-dim flow matching, 8gaussian) | 2 | 1 | 1 |
| `self_flow` | Self-Flow ICML 2026 (image FM) | 0 | 0 | 0 |
| `hidream` | HiDream-I1 (image diffusion) | 0 | 0 | 0 |
| `graphbfn` | GraphBFN (graph Bayesian flow network) | 0 | 0 | 0 |
| `lumina` | Lumina-Image-2.0 (image generation) | 0 | 0 | 0 |
| `protbfn_abbfn` | ProtBFN-AbBFN (antibody / protein BFN) | 0 | 0 | 0 |
| `wan2_2` | Wan2.2 video (video diffusion) | 0 | 0 | 0 |
| `web_research` | Web research 2026 (FM literature surveys) | 1 | 0 | 1 |
| `engineering` | Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree) | 126 | 76 | 50 |
| `reproducibility` | Reproducibility (reproducibility-record, preregistration, reproduce-script) | 13 | 6 | 7 |
| `data_packaging` | Data packaging + manifest (sha256, csv, metric-ledger) | 27 | 9 | 18 |
| `push_state` | Push state (push-ready, freeze, release, submission) | 10 | 6 | 4 |
| `algorithm_4arm` | Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency) | 39 | 18 | 21 |
| `sweep_eval` | Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability) | 107 | 90 | 17 |
| `stats_method` | Statistical methodology (R5/R6, p-value, bonferroni, TOST) | 43 | 21 | 22 |
| `paper_claims` | Paper + claims (paper packaging, claim audit, paper-update) | 49 | 26 | 23 |
| `final_verify` | Final-verify (per-wave close-out, pre-push hygiene) | 36 | 23 | 13 |
| `governance` | Governance (scope, audit, gap, condition, placeholder, cross-cutting) | 111 | 32 | 79 |
| **TOTAL** | — | **619** | **348** | **271** |

---

## Cluster details

### Cluster: `cifar` — CIFAR-10 RF (Rectified Flow on CIFAR-10)

**Files: 7** (active: 5, historical: 2)

CIFAR-10 RF (Rectified Flow on CIFAR-10). This cluster is part of the project's audit surface for cifar.

**Active (cited by at least one reviewer-facing surface):**

- `cifar-reference-availability.md`
- `cifar-v4-audit.md`
- `p6-cifar-rf-v4-honest-negative-curve.md`
- `wave280-p-cifar-sweep-result.md`
- `wave286-p-cifar-resweep-aggregated.md`

**Historical (2 files, not cited by reviewer-facing surfaces):**

- `p-cifar10-impl.md`
- `wave275-p4-cifar10-proposal.md`

---

### Cluster: `kanzi` — Kanzi (protein flow autoencoder)

**Files: 10** (active: 9, historical: 1)

Kanzi (protein flow autoencoder). This cluster is part of the project's audit surface for kanzi.

**Active (cited by at least one reviewer-facing surface):**

- `kanzi-fix.md`
- `kanzi-gpu-sweep.md`
- `kanzi-load-torch-fix.md`
- `kanzi-nfe-bug.md`
- `p1-kanzi-byte-stability-regression.md`
- `p2-kanzi-n30-sweep.md`
- `p2-kanzi-rerun.md`
- `p3-kanzi-n1000-framework-inv-proj.md`
- `p4-kanzi-full.md`

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `gap70-kanzi-latent.md`

---

### Cluster: `flowmol3` — FlowMol3 (molecular 3D flow matching)

**Files: 7** (active: 4, historical: 3)

FlowMol3 (molecular 3D flow matching). This cluster is part of the project's audit surface for flowmol3.

**Active (cited by at least one reviewer-facing surface):**

- `c-flowmol3-n1000.md`
- `p2-flowmol3-dgl-fix-or-sanity.md`
- `p3-flowmol3-n1000.md`
- `gap39-flowmol3-real-restart-blend.md`

**Historical (3 files, not cited by reviewer-facing surfaces):**

- `p-flowmol3-impl.md`
- `gap68-flowmol3-channels.md`
- `wave275-p4-flowmol3-proposal.md`

---

### Cluster: `lineageflow` — LineageFlow (protein flow matching, HMMER + foldability + novelty)

**Files: 23** (active: 17, historical: 6)

LineageFlow (protein flow matching, HMMER + foldability + novelty). This cluster is part of the project's audit surface for lineageflow.

**Active (cited by at least one reviewer-facing surface):**

- `hmmer-launch.md`
- `hmmer-collect.md`
- `hmmer-rederivation.md`
- `gap70-lineageflow-position-blend.md`
- `b-lineageflow-n1000-gpu.md`
- `lineageflow-hmmer-poc.md`
- `lineageflow-nfe-scan.md`
- `p3-lineageflow-n30-sweep.md`
- `p5-lineageflow-regression.md`
- `hmmer-launch.md`
- `novelty-diagnosis.md`
- `novelty-fix.md`
- `novelty-sweep-fixed.md`
- `novelty-sweep.md`
- `p1-pLDDT-inversion.md`
- `p2-foldability-sc-workers-per-gpu.md`
- `p3-run-foldability-propagate-workers-per-gpu.md`

**Historical (6 files, not cited by reviewer-facing surfaces):**

- `gap40-lineageflow-classifier-aware-restart.md`
- `gap69-lineageflow-profile.md`
- `lineageflow-real-forward-fix.md`
- `p-k7-impl.md`
- `p-lineageflow-impl.md`
- `wave275-p4-lineageflow-proposal.md`

---

### Cluster: `freqflow` — FreqFlow + MM-FM (frequency / multimodal flow)

**Files: 3** (active: 3, historical: 0)

FreqFlow + MM-FM (frequency / multimodal flow). This cluster is part of the project's audit surface for freqflow.

**Active (cited by at least one reviewer-facing surface):**

- `p3-freqflow-honest-disclosure.md`
- `p5-freqflow-n1000.md`
- `mm-fm-unblock-investigation.md`

---

### Cluster: `mnist` — MNIST FM (MNIST flow matching)

**Files: 5** (active: 2, historical: 3)

MNIST FM (MNIST flow matching). This cluster is part of the project's audit surface for mnist.

**Active (cited by at least one reviewer-facing surface):**

- `wave280-p-r5c-sweep-result.md`
- `wf334-r5c-regime-curve.md`

**Historical (3 files, not cited by reviewer-facing surfaces):**

- `mnist-gpu-backend.md`
- `p-mnist-impl.md`
- `wave275-p4-mnist-proposal.md`

---

### Cluster: `2d_toy` — 2D toy FM (two-dim flow matching, 8gaussian)

**Files: 2** (active: 1, historical: 1)

2D toy FM (two-dim flow matching, 8gaussian). This cluster is part of the project's audit surface for 2d_toy.

**Active (cited by at least one reviewer-facing surface):**

- `wave286-p-paper-quantity-ablation.md`

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `wave282-p-cosine-vs-paper-controllers.md`

---

### Cluster: `web_research` — Web research 2026 (FM literature surveys)

**Files: 1** (active: 0, historical: 1)

Web research 2026 (FM literature surveys). This cluster is part of the project's audit surface for web_research.

**Historical (1 files, not cited by reviewer-facing surfaces):**

- `INDEX_MAINTENANCE.md`

---

### Cluster: `engineering` — Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree)

**Files: 126** (active: 76, historical: 50)

Engineering hygiene (ruff, mkdocs, pytest, byte-stable, CI, working-tree). This cluster is part of the project's audit surface for engineering.

**Active (cited by at least one reviewer-facing surface):**

- `pdf-warning-zero.md`
- `docs-legacy-inventory.md`
- `engineering-audit-2026-09-13.md`
- `bridge-bug-design.md`
- `cli-pr-prep.md`
- `cli-verify.md`
- `doc-cleanup.md`
- `docstring-audit.md`
- `followup-w148.md`
- `followup.md`
- `headline-evidence.md`
- `impl.md`
- `inv-proj-final-fix.md`
- `mypy-fix.md`
- `number-consistency.md`
- `p1-setup-w184.md`
- `p2-verify.md`
- `p3-integration.md`
- `p3-journal-decision.md`
- `p3-tier-aware.md`
- `p4-plot.md`
- `p4-table-aggregate.md`
- `p5-gates.md`
- `p5-results.md`
- `pdf-warning-fixes.md`
- `polish-execute.md`
- `pr1-application.md`
- `primitive-cli-design.md`
- `push-and-fix.md`
- `push-w156c.md`
- `push-w158.md`
- `ruff-cleanup.md`
- `scripts-ruff-cleanup.md`
- `tier1-polish.md`
- `tmp-migration.md`
- `todo-refactor.md`
- `pdf-warning-reduction.md`
- `pdf-warning-reduction.md`
- `project-state-inventory.md`
- `pytest-order-dependence.md`
- `tables-inventory-provenance.md`
- `wave268-strict-clean.md`
- `wave290-p4-benchmark-fixed.md`
- `wave291-p1-hypothesis-redesign.md`
- `wave296-p1-architecture.md`
- `wave296-p2-cache.md`
- `wave297-p3-intro-rewritten.md`
- `wave297-p4-framework-rewritten.md`
- `wave297-p5-empirical-rewritten.md`
- `wave297-p7-readme-updated.md`
- `wave306-11-cell-alignment.md`
- `wave306-fix-plan.md`
- `wave307-data-archaeology.md`
- `wave310-restoration-execution.md`
- `wave311-restoration-execution.md`
- `wave322-restoration-execution.md`
- `wave347-final-4-gap-fix.md`
- `wave348-link-fix.md`
- `wave349-gpu-acceleration.md`
- `wave349-impl.md`
- `wave350-r1-materialize-status.md`
- `wave351-thm5-numerical.md`
- `wave352-framework-code-anchors.md`
- `wave352-l-local-appendix.md`
- `wave353-conclusion-takeaways.md`
- `wave355-capability-token-example.md`
- `wave355-supplementary-polish.md`
- `wave356-data-availability-polish.md`
- `wave356-highlights-polish.md`
- `wave357-ruff-w292-fix.md`
- `wave358-figures-md-polish.md`
- `wave361-figures-sha-crosscheck.md`
- `wave363-all-cell-recipes.md`
- `wave363-r1-recipe.md`
- `wave364-g38.md`
- `wave384-project-audit.md`

**Historical (50 files, not cited by reviewer-facing surfaces):**

- `cli-help-guard.md`
- `clone-reproducibility.md`
- `doc-link-audit.md`
- `docs-inventory-2026-10-21.md`
- `c3-fix-summary.md`
- `p3-number-verification.md`
- `p5-ground-truth-corrections.md`
- `review-layer4-docs-config.md`
- `manifest-hash-staleness.md`
- `portability-prefix-audit.md`
- `portable-paths.md`
- `readiness-verifier-repoint.md`
- `release-notes-v31-refresh.md`
- `repo-docs-maintenance-2.md`
- `repo-docs-maintenance.md`
- `scheduler-per-cell-summary.md`
- `wave275-p4-overview.md`
- `wave279-plan-complete.md`
- `wave279-user-decisions.md`
- `wave287-p-ci-hardening.md`
- `wave287-p-test-coverage.md`
- `wave290-p2-driver-microfix.md`
- `wave290-p5-workflow-paused-status.md`
- `wave292-p2-config-genealogy.md`
- `wave293-p3-fix-applied.md`
- `wave296-p5-activation-log.md`
- `wave296-p6-backward-compat.md`
- `wave296-p7-fid-comparison.md`
- `wave299-final-verification.md`
- `wave301-day0-prompt.md`
- `wave301-day2-execution-plan.md`
- `wave301-day3-execution-plan.md`
- `wave302-p2-exp-b1-smoke.md`
- `wave308-d3-review.md`
- `wave326-ci-design.md`
- `wave326-ci-redesign-execution.md`
- `wave326-readme-update.md`
- `wave334-reviewer-prediction.md`
- `wave338-phase2-mechanism.md`
- `wave340-readme-update.md`
- `wave351-cover-letter-helper.md`
- `wave352-cover-letter-interactive.md`
- `wave353-a2-placeholder-fill.md`
- `wave353-pseudocode-blocks.md`
- `wave359-final-consolidated.md`
- `wave360-verification-outputs-xref.md`
- `wave363-k4-recipe.md`
- `wave363-k7-recipe.md`
- `wave364-g3.md`
- `wave364-g34.md`

---

### Cluster: `reproducibility` — Reproducibility (reproducibility-record, preregistration, reproduce-script)

**Files: 13** (active: 6, historical: 7)

Reproducibility (reproducibility-record, preregistration, reproduce-script). This cluster is part of the project's audit surface for reproducibility.

**Active (cited by at least one reviewer-facing surface):**

- `item4-tex-rewrite.md`
- `wave298-p3-reproducibility-innovations.md`
- `wave324-d5-review.md`
- `wave353-ledger-examples.md`
- `wave358-tables-md-polish.md`
- `wave366-p2-reproducibility-manifest.md`

**Historical (7 files, not cited by reviewer-facing surfaces):**

- `reproduce-scripts-audit.md`
- `p5-experiment-setup.md`
- `p8-experiment-setup.md`
- `wave303-day0-prompt.md`
- `wave325-push-execution.md`
- `wave361-reproduce-scripts-verify.md`
- `wave363-p2-master-verifier.md`

---

### Cluster: `data_packaging` — Data packaging + manifest (sha256, csv, metric-ledger)

**Files: 27** (active: 9, historical: 18)

Data packaging + manifest (sha256, csv, metric-ledger). This cluster is part of the project's audit surface for data_packaging.

**Active (cited by at least one reviewer-facing surface):**

- `fix-design.md`
- `tier1-metric-alignment.md`
- `paper-packaging-2026-10-27.md`
- `todo-history.md`
- `wave297-p6-limitations-rewritten.md`
- `wave326-final-metrics-table.md`
- `wave328-freeze-survey.md`
- `wave331-data-fix.md`
- `wave344-supplementary-bundle.md`

**Historical (18 files, not cited by reviewer-facing surfaces):**

- `data-linkage-closure.md`
- `data-linkage-plan.md`
- `framework-inv-proj-re-run.md`
- `implementation-plan.md`
- `p1-data-gathering.md`
- `p5-metrics-patch.md`
- `evidence-hash-surfaces.md`
- `evidence-pin-audit.md`
- `r3-env-investigation.md`
- `todo-surface-reset.md`
- `wave275-p1-state-inventory.md`
- `wave275-p2-metric-ledger.md`
- `wave327-revised-q1-assessment.md`
- `wave342-readme-update.md`
- `wave354-manifest-sha256-refresh.md`
- `wave355-final-sha256-refresh.md`
- `wave355-verification-outputs-readme.md`
- `wave360-supplementary-bundle-verify.md`

---

### Cluster: `push_state` — Push state (push-ready, freeze, release, submission)

**Files: 10** (active: 6, historical: 4)

Push state (push-ready, freeze, release, submission). This cluster is part of the project's audit surface for push_state.

**Active (cited by at least one reviewer-facing surface):**

- `push-unblock-large-blob.md`
- `submission-polish.md`
- `submission-prep.md`
- `verify-submission-readiness.md`
- `wave356-submission-checklist-review.md`
- `wave358-submission-checklist-reaudit.md`

**Historical (4 files, not cited by reviewer-facing surfaces):**

- `submission-link-rot.md`
- `submission-package-refresh.md`
- `wave324-submission-prep.md`
- `wave365-submission-readiness.md`

---

### Cluster: `algorithm_4arm` — Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency)

**Files: 39** (active: 18, historical: 21)

Algorithm + 4-arm (Theorem 1, paper-quantity, A/B/C_g, efficiency). This cluster is part of the project's audit surface for algorithm_4arm.

**Active (cited by at least one reviewer-facing surface):**

- `algorithm-gap-investigation.md`
- `p-r6-impl.md`
- `p1-4arm-power-analysis.md`
- `p2-eval-w182.md`
- `p2-impl.md`
- `p2-progress.md`
- `p2-wallclock-fix.md`
- `p3-4arm-power.md`
- `p3-rerun.md`
- `p4-theorem1-power.md`
- `p6-boundary-framing.md`
- `p6-repo-naming.md`
- `push.md`
- `theory-audit.md`
- `push.md`
- `r1-3seed-real-ckpt-materialize.md`
- `wave311-path-a-lemma-1.md`
- `wave322-path-a-lemmas-2-3.md`

**Historical (21 files, not cited by reviewer-facing surfaces):**

- `p3-f-side-actual-values.md`
- `p3-post-hoc-sensitivity.md`
- `mechanism-core-driver.md`
- `plan-2026-10-23-win-requirement.md`
- `public-api-surface.md`
- `r1-d004-remeasure.md`
- `r1-d004b-attribution.md`
- `r1-d004b-remeasure.md`
- `todo-rewrite-2026-10-27.md`
- `wave292-p3-crosscheck.md`
- `wave293-p1-locate-sign.md`
- `wave294-p2-medium-fixed.md`
- `wave296-p3-a-class-wired.md`
- `wave296-p4-b-class-wired.md`
- `wave300-p3-resolution-plan.md`
- `wave302-p5-codim-deep-dive.md`
- `wave303-day0-14-plan.md`
- `wave336-r5b-mechanism.md`
- `wave353-limitations-vendor-note.md`
- `wave357-lean-sorry-discharge.md`
- `wave379-mechanism-synthesis.md`

---

### Cluster: `sweep_eval` — Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability)

**Files: 107** (active: 90, historical: 17)

Sweep / eval / ablation (N=1000/30/64 sweeps, novelty, foldability). This cluster is part of the project's audit surface for sweep_eval.

**Active (cited by at least one reviewer-facing surface):**

- `p1-design.md`
- `p2-eval.md`
- `p3-comparison.md`
- `p4-aggregate.md`
- `fasta-generation.md`
- `eval.md`
- `p1-setup.md`
- `r2-terminology-unification.md`
- `p3-comparison.md`
- `cross-model-nfe-curve.md`
- `cuda-fix-sweep-recovery.md`
- `dispatch-verification.md`
- `eval-w174.md`
- `eval.md`
- `fair-fasta-generation.md`
- `fasta-generation.md`
- `finish.md`
- `gpu-verify.md`
- `headline-evidence-audit.md`
- `item1-ablation.md`
- `item2-hp-sweep.md`
- `k1-rc5-launch-w156.md`
- `k1-rc5-launch.md`
- `k1-rc5-preflight.md`
- `k1-rerun.md`
- `k6-sweep-launch.md`
- `k6-verification.md`
- `n-rounds-flag.md`
- `nfe-curve.md`
- `nfe-flag.md`
- `nfe-real.md`
- `omegafold-provisioning.md`
- `p1-design-w178.md`
- `p1-design-w179.md`
- `p1-design.md`
- `p1-investigation.md`
- `p1-revert-all.md`
- `p1-setup-w181.md`
- `p1-setup-w182.md`
- `p1-setup-w186.md`
- `p1-setup.md`
- `p2-empirical-bl.md`
- `p2-eval.md`
- `p2-fasta-generation.md`
- `p2-generate-w183.md`
- `p2-generate-w184.md`
- `p2-generate.md`
- `p2-post-cd70821-2d-sweep.md`
- `p3-comparison.md`
- `p3-eval-w183.md`
- `p3-eval-w184.md`
- `p3-eval-w186.md`
- `p3-eval.md`
- `p3-fasta-ladder.md`
- `p3-sanity.md`
- `p3-tightness.md`
- `p4-aggregate-w183.md`
- `p4-aggregate.md`
- `p4-aggregation.md`
- `p4-cross-adapter-ablation.md`
- `p4-nfe-curve-w168.md`
- `p4-nfe-curve.md`
- `p5-plot.md`
- `p6-e2e-eval.md`
- `p6-paper.md`
- `rc4-ablation-fix.md`
- `restart-blend-analysis.md`
- `restart-over-application.md`
- `shape-fix-resweep.md`
- `sweeps-collect.md`
- `validation-experiment.md`
- `w2-n1000-reruns.md`
- `wave280-p-k1-sweep-result.md`
- `wave280-p-k4k5-sweep-result.md`
- `wave280-p-k7-sweep-result.md`
- `wave280-p-r1-sweep-result.md`
- `wave280-p-r3-sweep-result.md`
- `wave280-p-r6-sweep-result.md`
- `wave286-p-fid-gpu-fix.md`
- `wave286-p-fid-gpu-verify.md`
- `wave290-p1-bottleneck-confirmed.md`
- `wave290-p3-batched-harness.md`
- `wave291-p3-1seed-results.md`
- `wave291-p5-3seed-results.md`
- `wave307-archaeology-summary.md`
- `wave311-d1-review.md`
- `wave338-p5-r3-dgl-fix-and-sweep.md`
- `wave350-thm5.md`
- `wave353-h2h-ablation-refs.md`
- `wave357-k5-k6-camera-ready.md`

**Historical (17 files, not cited by reviewer-facing surfaces):**

- `b-config-scattering-audit.md`
- `framework-synth-sweep.md`
- `k1-rc5-3arm-preflight.md`
- `p1-restore-r4-r5.md`
- `p5-doc-consolidation.md`
- `wave287-p-adversarial-sweep.md`
- `wave291-p2-sweep-driver.md`
- `wave291-p4-regime-analysis.md`
- `wave293-p4-related-docs.md`
- `wave301-day1-execution-plan.md`
- `wave302-p1-regime-sweep-design.md`
- `wave330-zh-review-version.md`
- `wave356-archive-cleanup.md`
- `wave359-k1-rc5-drift33-fix.md`
- `wave359-lean-build-verify.md`
- `wave363-k1-recipe.md`
- `xfail-triage.md`

---

### Cluster: `stats_method` — Statistical methodology (R5/R6, p-value, bonferroni, TOST)

**Files: 43** (active: 21, historical: 22)

Statistical methodology (R5/R6, p-value, bonferroni, TOST). This cluster is part of the project's audit surface for stats_method.

**Active (cited by at least one reviewer-facing surface):**

- `p1-power-spec.md`
- `p1-r3-uplift.md`
- `p1-r5b-fix.md`
- `p1-r5c-underflow-fix.md`
- `p2-r-level-power.md`
- `p2-r2-re-audit.md`
- `p3-r3-cross-seed.md`
- `p3-r6-uplift.md`
- `p4-r-level-refresh.md`
- `p6-non-inferiority.md`
- `pr2-application.md`
- `wave234-p3-jonckheere.md`
- `wave310-r6-tier-aware-upgrade.md`
- `wave350-r5b-figure.md`
- `wave350-r6-live-attempt.md`
- `wave351-r3-vendor-fix-status.md`
- `wave351-r5a-n10.md`
- `wave352-claims-r5a-update.md`
- `wave357-r3-rdkit-blocker-doc.md`
- `wave362-r6-recipe.md`
- `wave363-r2-recipe.md`

**Historical (22 files, not cited by reviewer-facing surfaces):**

- `jt-variance-correction.md`
- `p1-fix-r2-numbers.md`
- `p3-r3-re-audit.md`
- `p4-r6-re-audit.md`
- `wave275-p4-r6-proposal.md`
- `wave302-p4-r6-replication.md`
- `wave347-r5a-ds-aggregation-clarification.md`
- `wave352-r6-status.md`
- `wave354-r5b-figure-verify.md`
- `wave357-r6-gpu-scope.md`
- `wave359-r6-gpu-scope-cuda0.md`
- `wave361-r-level-inventory-refresh.md`
- `wave361-r6-forensic-evidence-chain.md`
- `wave361-r6-launch-attempt.md`
- `wave361-r6-launch-discrepancy.md`
- `wave362-p1-r6-recipe.md`
- `wave362-p2-verify-r6-recipe.md`
- `wave363-r3-recipe.md`
- `wave363-r5a-recipe.md`
- `wave363-r5b-recipe.md`
- `wave363-r5c-recipe.md`
- `wave364-p1-gap-selection-memo.md`

---

### Cluster: `paper_claims` — Paper + claims (paper packaging, claim audit, paper-update)

**Files: 49** (active: 26, historical: 23)

Paper + claims (paper packaging, claim audit, paper-update). This cluster is part of the project's audit surface for paper_claims.

**Active (cited by at least one reviewer-facing surface):**

- `manuscript-defect-review-2.md`
- `manuscript-defect-review-3.md`
- `manuscript-defect-review-4.md`
- `manuscript-defect-review-5.md`
- `manuscript-defect-review-6.md`
- `manuscript-defect-review-7.md`
- `manuscript-defect-review-8.md`
- `manuscript-defect-review-9.md`
- `manuscript-defect-review.md`
- `agent3-pdf-generation.md`
- `d-paper-package-update.md`
- `p3-clm057-update.md`
- `wave297-p2-paper-design.md`
- `wave309-paper-a-restoration-plan.md`
- `wave323-typeset-execution.md`
- `wave343-paper-fixes.md`
- `wave345-cross-doc-fixes.md`
- `wave353-a1-theorem4-derivation.md`
- `wave354-p5-lean-subclaim-stubs.md`
- `wave354-paper-final-polish.md`
- `wave355-claims-deep-audit.md`
- `wave356-pdf-rebuild.md`
- `wave360-claims-status-summary.md`
- `wave364-paper-polish-gaps.md`
- `wave372-manuscript-claim-audit.md`
- `wave385-figures.md`

**Historical (23 files, not cited by reviewer-facing surfaces):**

- `cover-letter-fill-draft.md`
- `manuscript-citation-integrity.md`
- `manuscript-vs-new-evidence-2026-10-27.md`
- `paper-evidence-register-2026-10-27.md`
- `paper-refresh-2026-10-27.md`
- `paper-v32-data-refresh.md`
- `paper-v32-rewrite-preview.md`
- `paper-v32-verify-only-pass.md`
- `p4-paper-updates.md`
- `p6-paper-polish-audit.md`
- `wave293-p2-verify-direction.md`
- `wave294-p3-low-paper-fixed.md`
- `wave297-p1-paper-inventory.md`
- `wave298-p7-paper-append.md`
- `wave298-p8-claims-updated.md`
- `wave299-paper-a-outline.md`
- `wave299-paper-b-deferred.md`
- `wave323-d3-review.md`
- `wave328-freeze-manifest.md`
- `wave342-claims-fixes.md`
- `wave353-claims-consolidation.md`
- `wave364-g31.md`
- `wave364-g32.md`

---

### Cluster: `final_verify` — Final-verify (per-wave close-out, pre-push hygiene)

**Files: 36** (active: 23, historical: 13)

Final-verify (per-wave close-out, pre-push hygiene). This cluster is part of the project's audit surface for final_verify.

**Active (cited by at least one reviewer-facing surface):**

- `close-remaining-debt.md`
- `close-w150.md`
- `close-w151.md`
- `close-w152.md`
- `close-w153.md`
- `close-w154b.md`
- `close-w155.md`
- `close-w156c.md`
- `close-w157.md`
- `close-w158.md`
- `close-w159.md`
- `close-w160.md`
- `close.md`
- `final-synthesis.md`
- `finish-line.md`
- `p10-final-synthesis.md`
- `pre-freeze-hygiene.md`
- `status-reconciliation-2026-09-13.md`
- `todo-status-reconciliation-2026-09-13.md`
- `wave262-p2-verify.md`
- `wave297-final.md`
- `wave298-final.md`
- `wave352-sec10-9-close-out.md`

**Historical (13 files, not cited by reviewer-facing surfaces):**

- `p5-final-verify.md`
- `w276-final.md`
- `wave277-final.md`
- `wave278-final.md`
- `wave280-final.md`
- `wave286-final.md`
- `wave287-final.md`
- `wave291-final.md`
- `wave292-final.md`
- `wave293-final.md`
- `wave294-final.md`
- `wave300-final.md`
- `wave302-final.md`

---

### Cluster: `governance` — Governance (scope, audit, gap, condition, placeholder, cross-cutting)

**Files: 111** (active: 32, historical: 79)

Governance (scope, audit, gap, condition, placeholder, cross-cutting). This cluster is part of the project's audit surface for governance.

**Active (cited by at least one reviewer-facing surface):**

- `EPSILON_DIRECTION.md`
- `PHASE4_DOCSTRING_AUDIT.md`
- `framework-model-gap-cpu-2026-09-13.md`
- `gap14-novelty-differentiation.md`
- `gap19-q1-odds-alignment.md`
- `gap23-r2-paired-comparison-invalid.md`
- `gap31-r6-live-uplift.md`
- `gap79-r1-family-lever.md`
- `gap80-r5a-harness.md`
- `gap81-r3-sigma-dose.md`
- `gap84-inference-frontier.md`
- `gap92-kappa-bridge.md`
- `evidence-freetraj-blocker.md`
- `layer1-adapters-status.md`
- `p2-real-state-shape.md`
- `p3-build-initial-state.md`
- `p3-root-cause.md`
- `p4-velocity-field-noop.md`
- `jmaa-theory-applications.md`
- `todo-six-plan-status-2026-09-13.md`
- `wave287-p-scheduler-codepath-audit.md`
- `wave289-p1-honest-reframe.md`
- `wave292-p1-pipeline-inventory.md`
- `wave298-p1-code-innovations.md`
- `wave298-p2-methodology-innovations.md`
- `wave298-p6-deep-innovations.md`
- `wave326-crossdoc-metrics-snapshot.md`
- `wave346-byte-page-fix.md`
- `wave349-gap-audit.md`
- `wave357-k4-saturation-scope.md`
- `wave361-consolidated-results-index.md`
- `wave375-image-feedback-path.md`

**Historical (79 files, not cited by reviewer-facing surfaces):**

- `audit-index-refresh.md`
- `doc-anchor-audit.md`
- `empirical-conditions.md`
- `evidence-pointer-audit.md`
- `gap01-r6-live-wiring.md`
- `gap02-r3-n1000-resolved.md`
- `gap04-r5b-rounds.md`
- `gap09-reinference-diagnostic.md`
- `gap12-tuned-baseline.md`
- `gap15-venue-fit.md`
- `gap16-deferred-triage.md`
- `gap17-k2k6-disclosure.md`
- `gap23-r2-paired-comparison-fix.md`
- `gap24-boundary-law.md`
- `gap25-r1-blend-isolation.md`
- `gap26-r5b-regime.md`
- `gap27-r3-power.md`
- `gap28-r6-faithful.md`
- `gap30-r6-fresh-tier.md`
- `gap32-headtohead.md`
- `gap34-r1-init-dose.md`
- `gap35-cross-domain.md`
- `gap36-ablation-matrix.md`
- `gap37-statistical-power.md`
- `gap38-shared-prior-thorough.md`
- `gap41-r1-tier-aware-ncap.md`
- `gap41b-r1-nfe-fidelity.md`
- `gap42-scheduler-budget-conservation.md`
- `gap43-blend-positive-preregistration.md`
- `gap43-blend-positive-run.md`
- `gap44-p2-1-profile-residual.md`
- `gap45-r1-blend-off-wiring.md`
- `gap46-r5b-memory-fraction.md`
- `gap48-k7-two-arm-novelty.md`
- `gap49-compute-accounting.md`
- `gap50-evidence-grade-table.md`
- `gap52-charge-channel-preregistration.md`
- `gap52-charge-channel-run.md`
- `gap53-initial-condition-contraction.md`
- `gap55-code-level-hardening.md`
- `gap56-restart-t0-defect.md`
- `gap57-equal-nfe-regime-ladder.md`
- `gap58-r1-beta1-powered.md`
- `gap60-validity-novelty-tradeoff.md`
- `gap64-r5c-operating-regime.md`
- `gap65-dispersion-selector.md`
- `gap67-covariance-preservation.md`
- `gap70-r2-tempered-draw.md`
- `gap71-image-spectral.md`
- `gap72-r5c-mean-shift.md`
- `gap73-r5c-statistic.md`
- `gap74-conditional-mean-bound.md`
- `gap75-r5c-n1000-table.md`
- `gap76-restart-mean-bias.md`
- `gap77-restart-mechanism.md`
- `gap78-dispersion-gate.md`
- `gap90-optsteps-dose.md`
- `gap93-converged-lever.md`
- `gap94-standard-benchmark.md`
- `gap95-frontier-grids.md`
- `gap96-manuscript-compression.md`
- `governance-refresh-post-push.md`
- `vendored-pristine-gate.md`
- `wave275-p3-flatten.md`
- `p-partial-evidence.md`
- `wave288-p1-honest-progress-summary.md`
- `wave294-p1-re-inventory.md`
- `wave294-p4-cross-verify.md`
- `wave297-p8-cross-verify.md`
- `wave298-p4-engineering-innovations.md`
- `wave298-p5-literature-compare.md`
- `wave335-self-check-verification.md`
- `wave337-final-self-check-report.md`
- `wave338-h7-cleanup.md`
- `wave339-b6-fixes.md`
- `wave339-h8-fixes.md`
- `wave341-deep-audit.md`
- `wave341-readme-cosine-vs-codim.md`
- `wave380-mechanism-restructure.md`

---
