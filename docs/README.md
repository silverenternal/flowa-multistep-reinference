# Documentation map for `flowa-multistep-reinference`

> **Paper A is ready for TNNLS submission (updated 2026-10-11).**
> Paper PDF: [`drafts/paper-A-final.pdf`](drafts/paper-A-final.pdf) — 11 pages, IEEEtran-journal double-column, sha256 `8bc37858a7e6cbdfcc74dfd41f355f036433d0dfa75376b13482d91e6da5d9b5`.
> Headline verdicts: **4 STRONG + 1 TIE + 6 PARTIAL/SUPPLEMENTARY** across the 11 cells.
> Acceptance gates ALL PASS: D.4 30/30 · contracts 195/195 · ruff 0 · claims no drift · mkdocs 0 warnings · vendored `data/` untouched · data integrity 6/149/0 · reproducibility 12/12.
> **Management surface:** [`../todo/WAVES.md`](../todo/WAVES.md) — the consolidated, increment-free project record (current state, phase history, evidence ledger, gates, decisions, risks).
> **Submission package:** [`../tnnls_submission/`](../tnnls_submission/) — 7 core files with real SHA-256 (the cover letter still needs its `[USER TO FILL]` fields).

This page is the discoverable entry point for the `docs/` tree. Every entry
below is a one-sentence pointer to a hand-authored or peer-reviewed document,
grouped into the order a new reader should approach them. The auto-generated
API reference for the `adaptive_reflow` package (rendered from module
docstrings + typed signatures by mkdocstrings) is at [`api/index.md`](api/index.md);
the on-disk landing page is the doc *map*, not the API *reference* — they serve
different audiences.

## Documentation layers

The tree has three layers. Knowing which layer a document belongs to tells you
whether to trust it as canonical, cite it as reference, or treat it as an
archival trace.

| Layer | What it is | Where it lives |
|---|---|---|
| **Canonical** | Single sources of truth that an external reviewer reads. When a number changes, these are updated first. | [`CLAIMS.md`](CLAIMS.md), [`CONSOLIDATED_RESULTS.md`](CONSOLIDATED_RESULTS.md), [METRIC_LEDGER.md](METRIC_LEDGER.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`drafts/paper-A-final.md`](drafts/paper-A-final.md), [`../todo/WAVES.md`](../todo/WAVES.md) |
| **Active reference** | Cited supporting docs (specs, theory, quality gates, surveys). | the numbered sections below |
| **Historical / archival** | Per-increment records and superseded material, retained for provenance and verification. Not actively maintained; not part of the mkdocs site. | [`audit/`](audit/), [`ARCHIVE/`](ARCHIVE/), the `r*-survey/` trees |

## 1. Start here

| Doc | Read it for |
| --- | --- |
| [`TUTORIAL.md`](TUTORIAL.md) | Five-minute quickstart that loads `TwoDimFMAdapter`, runs the suite, and runs a 2-D rectified-flow experiment with one of the four canonical schedulers. |
| [`PLUG_IN_YOUR_MODEL.md`](PLUG_IN_YOUR_MODEL.md) | Adapter-author on-ramp: five steps from a `.npz` checkpoint to a baseline-vs-framework comparison table. |
| [`../QUICKSTART.md`](../QUICKSTART.md) | Repo-root on-ramp: install, run the suite, walk one round against `ToyGaussianAdapter`, capture a golden, run the docs scanner. |
| [`../FAQ.md`](../FAQ.md) | Top-20 short answers to the questions that come up most often during review and onboarding. |

## 2. Architecture and governance

| Doc | Read it for |
| --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Package layout, dependency DAG, governance invariants, the four-step Adapter Protocol recipe, the full file inventory. |
| [`ADAPTER_INTERFACE_SPEC.md`](ADAPTER_INTERFACE_SPEC.md) | Authoritative adapter spec: the eight-method `FlowMatchingODEAdapter` Protocol, capability handshake, hard rules, and a `ToyLinearAdapter` worked example. |
| [`adapter-dependencies.md`](adapter-dependencies.md) | Per-adapter dependency map (which venv / package each adapter family needs). |
| [`STRATEGY_FRAMEWORK_SCOPE.md`](STRATEGY_FRAMEWORK_SCOPE.md) | Framework-scope strategy: why SOTA-model reproduction is the wrong validation strategy and what to do instead. |
| [FLOWA_WORKFLOW.md](FLOWA_WORKFLOW.md) | The working loop: evidence-first, one objective per increment, gate-checked, with machine-readable results. |
| [`DEPRECATION.md`](DEPRECATION.md) | Versioned deprecation table for `adaptive_reflow.legacy/` and friends, with replacement paths and sunset versions. |
| [`RELEASING.md`](RELEASING.md) | The PyPI release process for this research-stage package, gated on paper acceptance. |
| [`RELEASE-NOTES.md`](RELEASE-NOTES.md) | Release notes for the current source-tree freeze. |
| [`adr/`](adr/) | Architecture-decision records — universal-vs-molecular split, typed-contracts core boundary, seven-step engine operation order, fail-closed audit-code policy, theorem-aligned FID per-round pattern, etc. |
| [design/B5_BATCHED_TRAJECTORIES.md](design/B5_BATCHED_TRAJECTORIES.md) | B5 batched-trajectories design note (load-bearing). |
| [`review/B5-VERIFICATION.md`](review/B5-VERIFICATION.md) | B5 batched-trajectories verification report. |
| [`CONTRIBUTING-cover-letter.md`](CONTRIBUTING-cover-letter.md) | How the cover letter is composed (and where the user-gated fields go). |
| [`cover-letter-tnnls.md`](cover-letter-tnnls.md) | The TNNLS cover-letter draft. |
| [`submission-checklist-final.md`](submission-checklist-final.md) | Final editorial-requirements checklist for the submission. |
| [`push-ready-summary.md`](push-ready-summary.md) | Push-readiness summary (user-gated). |

## 3. Algorithms and theory

| Doc | Read it for |
| --- | --- |
| [`ALGORITHMS.md`](ALGORITHMS.md) | Full catalog of every concrete operator: schedulers, drivers, merge operators, blenders, with paper grounding and copy-paste samples. |
| [`schedule-theory.md`](schedule-theory.md) | Theory behind the per-round `n_cap` schedule: cosine, polynomial, sigmoid, convergence-adaptive, codimension-sheet, sequential. |
| [`sequential-protocol.md`](sequential-protocol.md) | `SequentialScheduler` design: piecewise schedule shapes for regimes that want multi-phase composition by round range. |
| [`defaults-matrix.md`](defaults-matrix.md) | Default scheduler / driver / merge / blender choices per target distribution and per model family. |
| [`distinguishing-from-reflow.md`](distinguishing-from-reflow.md) | How this framework differs from a vanilla rectified-flow sampler at the algorithm-abstraction level. |
| [`configs.md`](configs.md) | Configuration presets and their intended regimes. |
| [`算法实现说明.md`](算法实现说明.md) | Chinese-language algorithm-implementation notes. |
| [`theory/`](theory/) | Self-contained theoretical companion (theorem statement + lemmas) framed as one lens, not the framework's identity. |
| [`lean/`](lean/) | Lean 4 formalization survey of the theorem-to-framework mappings (index at [`lean/INDEX.md`](lean/INDEX.md)); includes mapping, verification, and open gaps. |

## 4. Evidence and results

| Doc | Read it for |
| --- | --- |
| [`CONSOLIDATED_RESULTS.md`](CONSOLIDATED_RESULTS.md) | **Single source of truth** for every measured framework evidence record: algorithm uplifts, SOTA 2-D + CIFAR-10 verifications, toy comparisons, defensive engineering. |
| [`CLAIMS.md`](CLAIMS.md) | Claim ledger (governance document) — every substantive claim, with `Asserted by` / `Disputed by` references verified by `tools/check_claims_consistency.py`. |
| [METRIC_LEDGER.md](METRIC_LEDGER.md) | Per-metric provenance: definition, source artifact, and canonical value for each reported number. |
| [`headline-evidence/`](headline-evidence/) | Per-cell byte-addressable evidence bundle (one `SOURCE.md` per headline cell) — the reviewer re-verification surface. |
| [`ABLATION.md`](ABLATION.md) | The 2-D RF ablation grid: canonical configurations × targets, each run with fixed seed / rounds / RK4 steps. |
| [`CONDITIONS.md`](CONDITIONS.md) | Operating-regime conditions and the Pareto cells counted by the honest-negative-surface gate. |
| [`benchmark-uplifts.md`](benchmark-uplifts.md) | Round-1 algorithm-uplift benchmark (before/after). |
| [`benchmark-round2-uplifts.md`](benchmark-round2-uplifts.md) | Round-2 comprehensive uplift benchmark. |
| [`benchmark-deep-uplifts.md`](benchmark-deep-uplifts.md) | P0/P1 deep-uplift benchmark across internal and external algorithm surfaces. |
| [`INSIGHTS.md`](INSIGHTS.md) | Narrative insight document: how the algorithm layer maps to the companion-paper theorem (sheet-tube scaling, root-cell bound, physical-complement suppression). |
| [`capability_g1_analysis.md`](capability_g1_analysis.md) | Capability-metric G.1 analysis (mean value score across integrated models). |
| [`baseline-audit-report.md`](baseline-audit-report.md) | Baseline audit report. |
| [`drafts/paper-A-final.md`](drafts/paper-A-final.md) | **Canonical manuscript source** (title + abstract inline). |
| [`drafts/paper-A-final.tex`](drafts/paper-A-final.tex) | IEEEtran build source for the submitted PDF. |
| [`paper-draft.md`](paper-draft.md) · [`paper-draft-anonymous.md`](paper-draft-anonymous.md) · [`paper-profile.md`](paper-profile.md) | Paper-draft variants and the venue profile. |
| [`tables/`](tables/) | Paper-ready tables (paper quantities, algorithms, state machines, CIFAR ablation). |
| [`figures/`](figures/) | Paper-ready figures (protocol diagram, feedback loops, per-round selection ratio, CIFAR-10 FID curve, evidence comparison). |

## 5. Quality gates and operations

| Doc | Read it for |
| --- | --- |
| [`GATES.md`](GATES.md) | The gate chain: what each acceptance gate verifies and how to run it. |
| [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) | The six test layers (unit, contract, integration, regression, golden, mutation), the merge gates, and the AST-level invariant guards. |
| [`mutation_audit_q4_2026.md`](mutation_audit_q4_2026.md) | Mutation-testing audit (do the tests actually detect breakage?). |
| [`PERFORMANCE_BUDGETS.md`](PERFORMANCE_BUDGETS.md) | Kernel p95 wall-clock budgets and the regression gate that fails CI on hot-path regressions. |
| [`environments.md`](environments.md) | The two-tier venv layout: one project venv (`.venv`, stdlib-only framework) + per-model venvs under `.venvs/`. |
| [`reproduce.md`](reproduce.md) | How to reproduce the headline results end-to-end. |
| [`reproducibility_record.md`](reproducibility_record.md) | The reproducibility record: environment hash, seeds, and per-cell recipes. |
| [`verification_outputs.md`](verification_outputs.md) | Guide to the byte-addressable `verification_outputs/` tree. |
| [`code-release-checklist.md`](code-release-checklist.md) | Pre-release checklist for the source tree. |
| [`governance/`](governance/) | Governance audit documents: code organisation, algorithm, framework, test/CI, fix plan, verification report. |
| [`audit/PHASE4_DOCSTRING_AUDIT.md`](audit/PHASE4_DOCSTRING_AUDIT.md) | Phase-4 docstring audit. |

## 6. Survey archives and historical material

These directories hold the experiment-by-experiment record of major research
campaigns. A new reader should reach for `CONSOLIDATED_RESULTS.md` first, then
the directory-level entry points below — the per-file documents are
intentionally archival and rot-tolerant.

- [`audit/`](audit/) — the topic-clustered audit record (catalogue at
  [`audit/INDEX.md`](audit/INDEX.md)). Useful for tracing how a specific result
  evolved; **historical**, not the management surface.
- **`r4-survey/`** — SOTA-FM experiment log: 2-D + MNIST + CIFAR-10 experiments,
  weights acquisition, harness bugs, fix plans. Entry point:
  [`r4-survey/07-sota-experiment-protocol.md`](r4-survey/07-sota-experiment-protocol.md).
- **`r5-survey/`** — SOTA-FM candidate selection and the gate-fix research.
  Entry point: [`r5-survey/01-sota-fm-candidates.md`](r5-survey/01-sota-fm-candidates.md).
- **`r17-survey/`** — paper-parity evidence chain, image-eval tier-2 progress,
  paper-table template, synthetic-oracle audit. Entry point:
  [`r17-survey/state-report.md`](r17-survey/state-report.md).
- [`paper-final-neurips.md`](paper-final-neurips.md) — superseded venue draft.
- [`ARCHIVE/`](ARCHIVE/) — historical context, intentionally **not** part of the
  live mkdocs build (enforced by `mkdocs.yml` `exclude_docs`). Preserved on disk
  for archaeology; not maintained and not reachable from the GitHub Pages nav.

## 7. Documentation management conventions

Rules for keeping the tree navigable. They apply to any new document.

**Where a new document goes.**

| If the document is… | Put it in | Examples |
|---|---|---|
| Reviewer-facing reference or a source of truth | `docs/` (top level or a topic dir) and register it in this map | specs, theory, gate docs |
| A per-increment working record | `docs/audit/` (topic-clustered) | close-out notes, sweep records |
| Project-level management state | [`../todo/`](../todo/) — prefer the consolidated [`../todo/WAVES.md`](../todo/WAVES.md) | status, decisions, risks |

**Naming.** New management and map documents are written at the level of
**project phases**, not individual work increments — do **not** introduce
numbered-work-increment identifiers into new management or map documents.
Increment identifiers may persist inside historical per-increment records and in
the artifact filenames they live in (see provenance rule below).

**Provenance retention.** Historical per-increment records and the artifact
filenames they carry are **load-bearing**: the claims ledger, the metric ledger,
and the submission evidence bundle cite them. Do **not** delete or rename them —
they are retained for verification even as the management narrative moves to
phase-level language.

**Canonical-first updates.** When a reported number changes, update the
canonical surfaces first ([`CLAIMS.md`](CLAIMS.md), [METRIC_LEDGER.md](METRIC_LEDGER.md),
[`CONSOLIDATED_RESULTS.md`](CONSOLIDATED_RESULTS.md)), then propagate to
[`../README.md`](../README.md), [`../todo/WAVES.md`](../todo/WAVES.md), and the
submission package, re-running `tools/check_claims_consistency.py` and refreshing
the SHA-256 column in [`../tnnls_submission/MANIFEST.md`](../tnnls_submission/MANIFEST.md).

## Link-rot contract

Every path on this page is verified against the source tree by
[`../tools/check_docs_against_code.py`](../tools/check_docs_against_code.py) on
every CI run. Renaming or archiving any doc will break CI at the same time this
page becomes stale — that is the intended behaviour, not a bug. If a future PR
moves a doc, this page must be updated in the same PR.
