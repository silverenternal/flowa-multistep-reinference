# Audit Index

> **Per-wave curation table for `docs/audit/`.** Generated Wave 102 P1-A as part of
> `todo/planned/w101-fix-layer4-docs-config.md` (Layer-4 docs/config hygiene).

This index catalogs every wave deliverable in `docs/audit/`. Each row is one wave
(Wave 1 → Wave 101). The `audit/` directory holds 137 wave-prefixed files (Wave 100-136)
plus 50 cross-cutting / orphan docs. **Wave 34-99 audit docs were archived to
`docs/ARCHIVE/audit-waves-1-99/` in Wave 137 (2026-09-14)** — preserved for historical
reference, no longer cited by Tier-1 reviewer-facing docs.

**Legend**

- `canonical` — current authoritative deliverable for that wave. Read this first.
- `archive` — superseded by a later wave; preserved for historical reference only.
- `—` — wave has no audit doc (pre-Wave-32 era or no audit was produced).

**Column meanings**

- **Wave** — wave number (`waveNN` prefix in the audit doc filename).
- **Audit docs** — semicolon-separated list of doc filenames in `docs/audit/` for that wave.
- **Status** — `canonical`, `archive`, or `—` (no audit doc).
- **Linked fix plan** — pointer to `todo/planned/` or `todo/` plan doc if any. Empty if no formal plan.

---

## Per-wave table

| Wave | Audit docs | Status | Linked fix plan |
|------|------------|--------|-----------------|
| Wave 1 | — | — | — |
| Wave 2 | — | — | — |
| Wave 3 | — | — | — |
| Wave 4 | — | — | — |
| Wave 5 | — | — | — |
| Wave 6 | — | — | — |
| Wave 7 | — | — | — |
| Wave 8 | — | — | — |
| Wave 9 | — | — | — |
| Wave 10 | — | — | — |
| Wave 11 | — | — | — |
| Wave 12 | — | — | — |
| Wave 13 | — | — | — |
| Wave 14 | — | — | — |
| Wave 15 | — | — | — |
| Wave 16 | — | — | — |
| Wave 17 | — | — | — |
| Wave 18 | — | — | — |
| Wave 19 | — | — | — |
| Wave 20 | — | — | — |
| Wave 21 | — | — | — |
| Wave 22 | — | — | — |
| Wave 23 | — | — | — |
| Wave 24 | — | — | — |
| Wave 25 | — | — | — |
| Wave 26 | — | — | — |
| Wave 27 | — | — | — |
| Wave 28 | — | — | — |
| Wave 29 | — | — | — |
| Wave 30 | — | — | — |
| Wave 31 | — | — | — |
| Wave 34 | `wave34-final-status.md` | archive | — |
| Wave 35 | `wave35-saturation-results.md` | canonical | — |
| Wave 36 | `wave36-final-status.md`; `wave36-phas4-prep-results.md` | canonical | — |
| Wave 37 | `wave37-final-status.md` | canonical | — |
| Wave 38 | `wave38-algo-core-results.md`; `wave38-ci-infra-results.md`; `wave38-hf-pipeline-results.md`; `wave38-mutation-bugfix-results.md`; `wave38-tests-claims-results.md` | archive | todo/wf-d4-regression-vectors.md (D.4 vectors, E1 claims, expecttest) |
| Wave 39 | `wave39-cleanup-shims-results.md`; `wave39-cold-clone-capability-audit.md`; `wave39-framework-freeze-results.md`; `wave39-framework-freeze-synthesis.md`; `wave39-g1-pytest-fixes.md`; `wave39-kanzi-real-ckpt-forward.md`; `wave39-wave17-phase4-verify.md` | archive | todo/wf-stoch-fm-orphan.md + lineageflow-shim |
| Wave 40 | `wave40-blocker-unblock-synthesis.md`; `wave40-cold-clone-capability-audit.md`; `wave40-framework-freeze-results.md`; `wave40-kanzi-gpt-prior-monkey-patch.md`; `wave40-kanzi-real-eval-results.md`; `wave40-kanzi-real-eval-synthesis.md`; `wave40-lineageflow-real-ckpt-forward.md`; `wave40-synthesis.md`; `wave40-wave17-phase4-verify.md` | archive | todo/wf-framework-freeze-final.md |
| Wave 41 | `wave41-circular-import-fix.md`; `wave41-claim-close-synthesis.md`; `wave41-flowmol3-shrink.md`; `wave41-force-mode-real-results.md`; `wave41-kanzi-gpt-prior-e2e.md`; `wave41-kanzi-implements-fix.md`; `wave41-lineageflow-numerical-forward.md`; `wave41-numerical-forward-synthesis.md`; `wave41-paper-audit.md`; `wave41-synthesis.md`; `wave41-wallclock-analysis.md` | archive | todo/wf-claim-close.md + wf-warnings-research.md + wf-numerical-forward.md |
| Wave 42 | `wave42-claim-close-final-synthesis.md`; `wave42-kanzi-real-eval.md`; `wave42-lineageflow-real-eval.md`; `wave42-mnist-fm-shrink.md`; `wave42-must3-shrink-synthesis.md`; `wave42-paper-writeup-synthesis.md`; `wave42-paper-writeup.md`; `wave42-rectified-flow-cifar-shrink.md`; `wave42-self-flow-shrink.md`; `wave42-test-pollution-cleanup.md`; `wave42-tier3-synthesis.md`; `wave42-twodim-fm-shrink.md`; `wave42-value-surface-narrative.md` | archive | todo/wf-top-model-force-mode.md + wf-must3.md + wf-paper-writeup.md |
| Wave 43 | `wave43-cleanup-paper-synthesis.md`; `wave43-metric-layer-fix.md`; `wave43-metric-layer-synthesis.md`; `wave43-must3-finalize.md`; `wave43-paper-tier3-writeup.md`; `wave43-pfam-sidecar-install.md`; `wave43-problems-review.md`; `wave43-push-prep-summary.md`; `wave43-pytest-pollution-fix.md` | archive | todo/wf-compute-metric-fix.md + wf-pytest-pollution.md + wf-must3-finalize.md |
| Wave 44 | `wave44-d1-shrink-synthesis.md`; `wave44-flowmol3-v2-shrink.md`; `wave44-group-a-cold-import-fix.md`; `wave44-group-b-doc-regression-fix.md`; `wave44-hidream-i1-shrink.md`; `wave44-kanzi-shrink.md`; `wave44-metric-consume-trajectory.md`; `wave44-mnist-fm-core.md`; `wave44-must3-finalize-synthesis.md`; `wave44-observe-token-indices-api.md`; `wave44-paper-tier3-final.md`; `wave44-protbfn-abbfn-shrink.md`; `wave44-push-blockers-synthesis.md`; `wave44-rectified-flow-cifar-core.md`; `wave44-tier3-final-eval.md`; `wave44-twodim-fm-core.md` | archive | todo/wf-push-blockers.md + wf-tier3-metric-axis.md + wf-must3.md + wf-d1-shrink-4.md |
| Wave 45 | `wave45-entropy-helper.md`; `wave45-f1-fix.md`; `wave45-f2-fix.md`; `wave45-f3-fix.md`; `wave45-final-eval.md`; `wave45-kanzi-gpt-prior-restart.md`; `wave45-lineageflow-classifier-restart.md`; `wave45-lineageflow-entropy-metric.md`; `wave45-local-review.md`; `wave45-web-research-2026.md` | archive | todo/wave45-implementation-plan.md (F-1 + F-2 + F-3 + entropy + restart) |
| Wave 46 | `wave46-benchmark-design.md`; `wave46-local-review.md`; `wave46-web-research-2026.md` | canonical | todo/wave46-master-plan.md (Kanzi composite) |
| Wave 47 | `wave47-eval-pipeline-design.md`; `wave47-eval-pipeline-integration.md`; `wave47-glue-design.md`; `wave47-glue-impl-synthesis.md`; `wave47-lineageflow-f4-dtype-fix.md`; `wave47-lineageflow-glue-impl.md`; `wave47-lineageflow-review.md`; `wave47-lineageflow-upstream.md` | archive | todo/wave47-lineageflow-glue.md (LineageFlowGlue + composite) |
| Wave 48 | `wave48-benchmark-uplifts-fix.md`; `wave48-check-docs-fix.md`; `wave48-push-ready-summary.md` | canonical | todo/wave48-pytest-fixes.md (4 pre-push failures) |
| Wave 49 | `wave49-eval-pipeline-integration.md`; `wave49-flowmol3-adapter-ext.md`; `wave49-flowmol3-adapter.md`; `wave49-flowmol3-glue-impl.md`; `wave49-flowmol3-upstream.md`; `wave49-glue-design.md`; `wave49-glue-impl-synthesis.md`; `wave49-math-comparison.md` | archive | todo/wave49-flowmol3-glue.md (FlowMol3Glue + composite) |
| Wave 50 | `wave50-flowmol3-factory-fix.md`; `wave50-flowmol3-real-eval.md` | canonical | todo/wave50-flowmol3-factory.md (force_mode + real ckpt) |
| Wave 51 | `wave51-hidream-fix.md`; `wave51-rf-cifar-fix.md`; `wave51-synthetic-image-eval-fix.md` | canonical | todo/wave51-pytest-fixes.md (hidream + rf_cifar + synthetic) |
| Wave 52 | `wave52-baseline-comparison-impl.md`; `wave52-kanzi-composite-ablation-synthesis.md`; `wave52-kanzi-composite.md`; `wave52-lineageflow-baseline-comparison.md`; `wave52-paper-rewrite-synthesis.md`; `wave52-per-component-ablation.md`; `wave52-sota-baseline-comparison.md`; `wave52-sota-baselines-survey.md` | archive | todo/wave52-baselines.md (3 SOTA + ablation) |
| Wave 53 | `wave53-eval-pipeline-wiring-review.md`; `wave53-flowmol3-final-summary.md`; `wave53-flowmol3-metric-impl.md`; `wave53-flowmol3-metric-pattern-review.md` | canonical | todo/wave53-flowmol3-metric.md (real→torch + composite) |
| Wave 54 | `wave54-final-synthesis.md`; `wave54-fix-a-v1-protocol.md`; `wave54-fix-b-flowmol3-baselines.md`; `wave54-fix-c-v2-observation-dispatch.md`; `wave54-flowmol3-real-metric-impl.md`; `wave54-review-a-v1-v2.md`; `wave54-review-b-flowmol3-baselines.md`; `wave54-review-c-v2-observation-dispatch.md` | canonical | todo/wave54-paper-rewrite.md (§7.3 + §7.5 + §7.6 + §8.5) |
| Wave 56 | `wave56-final-synthesis.md` | canonical | todo/wave56-finalize.md (Wave 55 retry + Wave 51 retry) |
| Wave 57 | `wave57-flowmol3-restart-interaction.md`; `wave57-nfe-adaptive-research.md`; `wave57-pattern-investigation.md`; `wave57-synthesis-design.md` | canonical | todo/wave57-flowmol3-gap.md (NFE-adaptive + 3/9 + interaction) |
| Wave 58 | `wave58-kanzi-nfe-scan.md`; `wave58-nfe-adaptive-gate-impl.md`; `wave58-nfe-scan-aggregation.md` | canonical | todo/wave58-nfe-adaptive-plan.md (NFE gate + scan + §7.7) |
| Wave 59 | `wave59-ab-comparison.md`; `wave59-brai-impl.md`; `wave59-mfpqa-impl.md`; `wave59-perturbation-wired.md` | canonical | todo/wave59-integrator-perturbation.md (MFPQA + BRAI) |
| Wave 60 | `wave60-pytest-bloat-cleanup.md`; `wave60-pytest-bloat-diagnostic.md` | canonical | todo/wave60-pytest-bloat.md (215→150) |
| Wave 61 | `wave61-fix-summary.md`; `wave61-gate-wire.md`; `wave61-nfe-aware-scheduler.md` | canonical | todo/wave61-nfe-aware-scheduler.md (NFEAwareMemoryScheduler) |
| Wave 62 | `wave62-pytest-bloat-phase2.md` | canonical | todo/wave62-pytest-bloat-phase2.md (189→170) |
| Wave 63 | `wave63-root-cause.md`; `wave63-targeted-fix.md` | canonical | todo/wave63-nfe-root-cause.md |
| Wave 64 | `wave64-bug-a-fix.md` | canonical | todo/wave64-bug-a-fix.md |
| Wave 65 | `wave65-bug-c-root-cause.md`; `wave65-targeted-fix.md` | canonical | todo/wave65-bug-c-root-cause.md |
| Wave 66 | `wave66-v2-wire-result.md` | canonical | todo/wave66-v2-wire.md (FlowMol3 v2 force_mode=real) |
| Wave 67 | `wave67-plan.md` | canonical | todo/wave67-adapter-observation-plan.md |
| Wave 68 | `wave68-phase1.md`; `wave68-phase2.md`; `wave68-phase3.md`; `wave68-phase4.md`; `wave68-phase5.md` | canonical | todo/wave68-adapter-observation.md (5 phases) |
| Wave 69 | `wave69-phase1-audit.md`; `wave69-phase2-fix.md`; `wave69-phase3-sweep.md`; `wave69-phase4-cuda-upgrade.md`; `wave69-phase5-lineageflow-sweep.md`; `wave69-phase6-final.md` | canonical | todo/wave69-composite-cuda-nfe.md (composite wire + CUDA + NFE) |
| Wave 70 | `wave70-phase1-audit.md`; `wave70-phase2-install.md`; `wave70-phase3-export.md`; `wave70-phase4-wire.md`; `wave70-phase5-sweep.md`; `wave70-phase6-final.md` | canonical | todo/wave70-flowmol3-v2-gaps.md (export + 9-cell sweep) |
| Wave 71 | `wave71-phase1-analysis.md`; `wave71-phase2-fix.md`; `wave71-phase3-sweep.md`; `wave71-phase4-speedup.md`; `wave71-phase5-cross-model.md`; `wave71-phase6-final.md` | canonical | todo/wave71-nfe-saturation-speedup.md |
| Wave 72 | `wave72-phase1-audit.md`; `wave72-phase2-section1.md`; `wave72-phase3-ablation.md`; `wave72-phase4-section8.md`; `wave72-phase5-verification.md` | canonical | todo/wave72-paper-§1-§7.md |
| Wave 73 | `wave73-phase1-review.md`; `wave73-phase2-speedup.md`; `wave73-phase3-gap4-fix.md`; `wave73-phase4-sweep.md`; `wave73-phase5-paper.md`; `wave73-phase6-final.md` | canonical | todo/wave73-multi-tier-speedup.md |
| Wave 74 | `wave74-phase1-plan.md`; `wave74-phase2-f1.md`; `wave74-phase3-f2.md`; `wave74-phase4-env.md`; `wave74-phase5-sweep.md`; `wave74-phase6-final.md` | canonical | todo/wave74-flowmol3-closure.md (F1-F5) |
| Wave 75 | `wave75-phase1-audit.md`; `wave75-phase2-paper-metrics.md`; `wave75-phase3-paper-repro.md`; `wave75-phase4-framework-paper.md`; `wave75-phase5-paper-update.md`; `wave75-phase6-final.md` | canonical | todo/wave75-paper-metrics.md (4 paper metrics + reproduce) |
| Wave 79 | `wave79-phase1-audit.md`; `wave79-phase2-wire.md`; `wave79-phase3-sweep.md`; `wave79-phase4-verdict.md`; `wave79-phase5-paper.md`; `wave79-phase6-final.md` | canonical | todo/wave79-upstream-eval.md (Kanzi + LineageFlow) |
| Wave 80 | `wave80-phase1-audit.md`; `wave80-phase2-install.md`; `wave80-phase3-verify.md`; `wave80-phase4-final.md` | canonical | todo/wave80-install-paper-repro.md (Pfam + MMseqs2 + OmegaFold) |
| Wave 81 | `wave81-phase1-audit.md`; `wave81-phase3-sweep.md`; `wave81-phase4-final.md` | canonical | todo/wave81-lineageflow-upstream.md (--hmmdb + --target-db) |
| Wave 82 | `wave82-phase1-audit.md`; `wave82-phase3-sweep.md`; `wave82-phase4-final.md` | canonical | todo/wave82-flowmol3-pb-xtb.md (vendored YAML + xtb stub) |
| Wave 83 | `wave83-agent-b-codebook-metrics.md`; `wave83-phase1-audit.md`; `wave83-phase4-final.md` | canonical | todo/wave83-kanzi-codebook-metrics.md |
| Wave 84 | `wave84-phase1-install.md`; `wave84-phase2-sweep.md`; `wave84-phase3-final.md` | canonical | todo/wave84-python310-sidecar.md (LineageFlow foldability) |
| Wave 86 | `wave86-phase1-audit.md`; `wave86-phase3-sweep.md` | canonical | todo/wave86-framework-loop-bug.md (Path A framework-arm) |
| Wave 87 | `wave87-phase1-audit.md`; `wave87-phase2-impl.md`; `wave87-phase3-sweep.md`; `wave87-phase4-final.md` | canonical | todo/wave87-flowmol3-pb-xtb-real.md |
| Wave 88 | `wave88-phase1-audit.md`; `wave88-phase2-sweep.md`; `wave88-phase3-final.md` | canonical | todo/wave88-kanzi-framework-arm.md |
| Wave 89 | `wave89-phase1-final.md` | canonical | todo/wave89-final-synthesis.md |
| Wave 90 | `wave90-phase1-audit.md`; `wave90-phase2-sweep.md` | canonical | todo/wave90-path-c.md (xtb bridge + xtb real wire) |
| Wave 91 | `wave91-phase1-audit.md`; `wave91-phase2-bridge.md`; `wave91-phase4-eval.md`; `wave91-phase5-final.md` | canonical | todo/wave91-kanzi-latent-bridge.md (kanzi_latent_to_coord.py) |
| Wave 92 | `wave92a-kanzi-fix-constants.md`; `wave92c-n1000-sweep-real.md` | canonical | todo/wave92-kanzi-constants-fix.md (W92a) + N-samples-patch (W92b) + N=1000 (W92c) |
| Wave 93 | `wave93-phase2-final.md` | canonical | todo/wave93-statistical-power.md (12-cell N=100/1000) |
| Wave 95 | `wave95-phase3-kanzi-inverse-rerun.md`; `wave95-phase3-pin-probe.md` | canonical | todo/wave95-refresh-consolidated.md |
| Wave 96 | `wave96-status-reality-check.md`; `wave96-xtb-verification.md`; `wave96a-collapse-diagnosis.md`; `wave96c-fix-verification.md`; `wave96d-resweep.md`; `wave96e-final-synthesis.md`; `wave96e-n1000-final.md` | canonical | todo/wave96-framework-endpoint-collapse.md |
| Wave 97 | `wave97-routing-audit.md`; `wave97-routing-final.md` | canonical | todo/wave97-routing-consolidation.md |
| Wave 98 | `wave98-gpu-sota-final.md`; `wave98-gpu-watchdog-design.md`; `wave98-sota-config-audit.md` | canonical | todo/wave98-gpu-watchdog-sota.md |
| Wave 99 | `wave99-n1000-final.md`; `wave99b-n1000-verdict.md` | canonical | todo/wave99-kanzi-n1000-real.md |
| Wave 100 | `wave100-kanzi-load-torch-fix.md` | canonical | todo/wave100-kanzi-load-torch-fix.md |
| Wave 101 | `wave101-final-synthesis.md`; `wave101-review-layer1-adapters.md`; `wave101-review-layer2-algorithm-tools.md`; `wave101-review-layer3-tests.md`; `wave101-review-layer4-docs-config.md` | canonical | todo/w101-fix-layer4-docs-config.md (this fix) |

---

**Total waves**: 101 | **Waves with audit docs**: 62 | **Total audit .md files in `docs/audit/`**: 137 (Wave 100-136) | **Archived Wave 34-99 audit docs**: 261 (in `docs/ARCHIVE/audit-waves-1-99/`)

## Orphan (non-wave-prefixed) audit docs

These files in `docs/audit/` are NOT prefixed with `waveNN` — they are cross-cutting
audits, web-research reports, or root-cause analyses that span multiple waves.

| Filename | Purpose |
|----------|---------|
| `EPSILON_DIRECTION.md` | Direction of sign convention for ε (used in flow matching error analysis). |
| `PHASE4_DOCSTRING_AUDIT.md` | Phase-4 docstring audit (cross-cutting). |
| `ROOT_CAUSE_ANALYSIS.md` | Cross-cutting root-cause analysis (root-cause investigation). |
| `adapter-conformance-deep-dive.md` | Adapter conformance deep-dive audit (cross-cutting). |
| `algorithm-gap-investigation.md` | Algorithm gap investigation (Wave 33, cross-cutting). |
| `algorithm-saturation-review.md` | Algorithm saturation review (Wave 35, cross-cutting). |
| `closure-flowmol3-sweep.md` | Closure: FlowMol3 sweep verdict synthesis. |
| `closure-s7.4-s7.5.md` | Closure: paper §7.4 + §7.5 update synthesis. |
| `closure-s7.7.md` | Closure: paper §7.7 NFE-aware section synthesis. |
| `closure-state-none-fix.md` | Closure: state=None regression fix. |
| `closure-t3-final.md` | Closure: Tier 3 final synthesis. |
| `empirical-conditions.md` | Cross-cutting empirical conditions investigation. |
| `framework-code-review.md` | Cross-cutting framework code review (Wave 31). |
| `g1-spec-literal-review.md` | G.1 spec-literal review (Wave 37). |
| `gap-audit.md` | Cross-cutting gap audit (Wave 32). |
| `lineageflow-upstream-investigation.md` | LineageFlow upstream code investigation. |
| `metric-methodology.md` | Cross-cutting capability metric methodology (Wave 29). |
| `mm-fm-unblock-investigation.md` | MM-FM unblock investigation. |
| `per-adapter-value-verification.md` | Per-adapter cold-clone value verification (Wave 33). |
| `phase-4-blocker-investigation.md` | Phase-4 blocker investigation. |
| `phase-4-eval-pipeline.md` | Phase-4 eval pipeline design (Wave 32). |
| `pytest-failure-analysis.md` | Pytest failure analysis (Wave 37). |
| `saturation-improvement-plan.md` | Saturation improvement plan (Wave 35). |
| `theory-implementation-gap.md` | Theory/implementation gap (Wave 29). |
| `web-research-2026.md` | Web research 2026 (general FM literature). |
| `web-research-fm-restart-2026.md` | Web research 2026: FM restart-blend literature. |
| `web-research-robust-aggregators-2026.md` | Web research 2026: robust aggregators. |
| `web-research-saturation-2026.md` | Web research 2026: saturation efficiency. |

---

## How to use this index

1. **Find the current verdict for wave X**: read the doc marked `canonical` for that wave.
2. **Trace history**: read the `archive` docs in chronological order to see how the
   investigation evolved.
3. **Cross-cutting investigations**: see the orphan-files table above.
4. **Navigate to fix plans**: the `Linked fix plan` column points to `todo/planned/`.

## Era summary

The audit-rich era spans **Wave 32 → Wave 101** (70 waves), with the following eras:

| Era | Waves | Theme | Docs in era |
|-----|-------|-------|-------------|
| **Tier-3 closure era** | 32-50 | Tier 3 N=100/1000 reproduction + adapter conformance | ~80 docs |
| **Algorithm + NFE-aware era** | 51-70 | NFE-adaptive gate, saturation speedup, BRAI/MFPQA, FlowMol3 v2 | ~80 docs |
| **Paper-metric era** | 71-90 | Multi-tier speedup, paper-metric reproduction, §7 rewrite | ~80 docs |
| **Path C + statistical-power era** | 91-101 | Kanzi latent→coord bridge, N=1000 sweeps, statistical power, 4-layer review | ~50 docs |

## Supersession chains (high-level)

The audit docs trace the following supersession chains:

1. **Saturation speedup** — Wave 35 (initial review) → Wave 58 (NFE-adaptive gate) → Wave 61 (NFE-aware scheduler) → Wave 71 (cross-model saturation) → Wave 73 (multi-tier speedup).
2. **Tier 3 paper-metric reproduction** — Wave 42 (initial tier3-synthesis) → Wave 47 (LineageFlowGlue) → Wave 49 (FlowMol3Glue) → Wave 75 (4 paper metrics + reproduce) → Wave 79 (upstream-eval caveat) → Wave 81 (LineageFlow N=1000) → Wave 82 (FlowMol3 N=1000).
3. **Framework value surface** — Wave 42 (value-surface-narrative) → Wave 53 (FlowMol3 metric layer) → Wave 54 (paper rewrite with real numbers) → Wave 75 (paper-metric reproduction).
4. **Kanzi framework arm** — Wave 91 (latent→coord bridge) → Wave 92 (constants fix + N-samples patch) → Wave 95 (project_out⁻¹ architectural fix) → Wave 96 (endpoint collapse diagnosis) → Wave 99 (N=1000 real verdict).
5. **D.4 byte-stable regression vectors** — Wave 32 (D.4 first batch) → Wave 33 (D.4 batches 2-3) → Wave 34 (D.4 batch 4) → Wave 38 (final pinned regression vectors).
6. **Adapter conformance (MUST-3)** — Wave 42 (must3-shrink PARTIAL) → Wave 43 (must3-finalize) → Wave 44 (must3-finalize PARTIAL→PASS).

## Reading guide

- **New to the project**: start with `wave101-review-layer1-adapters.md` (Layer-1 hygiene), then `wave44-paper-tier3-final.md` (Tier 3 closure), then `wave73-phase6-final.md` (multi-tier speedup).
- **Investigating a specific bug**: search the table for the wave number when the bug was reported, then read both `canonical` and `archive` rows.
- **Tracing a paper claim**: see the paper-metric era (Waves 71-90) and the Kanzi framework arm chain.
- **Verifying framework health**: see `wave101-final-synthesis.md` and `baseline-audit-report.md`.

## Maintenance

- **Wave 102+**: when a new wave is launched, add a row to this table in the same PR.
- **When a wave is fully superseded**: flip its `Status` from `canonical` to `archive`
  and add a note in the canonical row of the superseding wave.
- **Wave 1-31**: no audit docs exist for these waves (pre-audit era). The `—` marker
  is correct.
- **Wave 55, 76-78, 85, 94**: these waves had planned audits that were never authored (skipped
  or rolled into adjacent waves). The table shows `—` for the wave row but `Wave 55`,
  `Wave 76-78`, `Wave 85`, and `Wave 94` are intentionally absent from the wave-prefixed
  file list because no `wave55-*`, `wave76-*`, `wave77-*`, `wave78-*`, `wave85-*`, or
  `wave94-*` files exist in `docs/audit/`.

---

_Generated Wave 102 P1-A as part of `todo/planned/w101-fix-layer4-docs-config.md`. Source: `ls docs/audit/ | sort` parsed into 62 wave buckets. 290+ audit docs across 70 waves._
