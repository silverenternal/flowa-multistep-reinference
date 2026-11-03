# Documentation map for `flowa-multistep-reinference`

> Latest originality increment: [round6 conditional theory and limitations](audit/manuscript-originality-round6-2026-11-03.md). Candidate novelty remains unresolved.

> **2026-11-03 research review:** see the [Chinese v6 research draft](drafts/paper-A-zh-reviewed-round5-2026-11-03.md), [complete reviewer checklist](audit/manuscript-selfcheck-2026-11-02.md), and [round 5 audit](audit/manuscript-selfcheck-round5-2026-11-03.md). Current originality and external-confirmation gaps remain material; the frozen package below is a historical artifact, not a current submission-readiness finding.

> **Paper A is frozen at the TNNLS v3.1 package (2026-10-18).** Paper PDF:
> [`drafts/paper-A-final.pdf`](drafts/paper-A-final.pdf) — 12 pages,
> IEEEtran-journal double-column, sha256
> `f153903f3d401f9dbd65afcaea8caac7723aa083828b28c74a64886b6afb1da8`.
> **Current evidence state:** [`PAPER-EVIDENCE.md`](PAPER-EVIDENCE.md) is the
> single cell-level register (verdict, N/seeds, artifact, audit) and is
> generated from [`paper-evidence.json`](paper-evidence.json). It is current;
> the frozen manuscript and the 2026-10-19 evidence-grade table are historical.
> Where the two differ, the register wins and the difference is the v3.2
> refresh work, not a silent edit.
> **Management surface:** [`../todo.json`](../todo.json) — the single current-state record (gates, evidence ledger, open gaps). Replaced the retired `todo/` directory on 2026-10-13. A `todo/…` path still quoted in an older page records *where something was filed at the time*; it is not a live path. The full account is [`audit/todo-surface-reset.md`](audit/todo-surface-reset.md) §8.
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
| **Canonical** | Single sources of truth that an external reviewer reads. When a number changes, these are updated first. | [`CLAIMS.md`](CLAIMS.md), [`CONSOLIDATED_RESULTS.md`](CONSOLIDATED_RESULTS.md), [METRIC_LEDGER.md](METRIC_LEDGER.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`drafts/paper-A-final.md`](drafts/paper-A-final.md), [`../todo.json`](../todo.json) |
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
| [`RELEASE-NOTES.md`](RELEASE-NOTES.md) | Release notes — current tag `v3.1-tnnls-with-figure`, additive over the `v3.0-tnnls-ready` freeze. |
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
| [`PAPER-EVIDENCE.md`](PAPER-EVIDENCE.md) | **Current cell-level evidence register** (generated from [`paper-evidence.json`](paper-evidence.json)): one row per paper cell with its verdict, N/seeds, artifact, audit, and paper anchor. Read this before any other evidence table. |
| [`CONSOLIDATED_RESULTS.md`](CONSOLIDATED_RESULTS.md) | **Single source of truth** for every measured framework evidence record: algorithm uplifts, SOTA 2-D + CIFAR-10 verifications, toy comparisons, defensive engineering. |
| [`CLAIMS.md`](CLAIMS.md) | Claim ledger (governance document) — every substantive claim, with `Asserted by` / `Disputed by` references verified by `tools/check_claims_consistency.py`. |
| [METRIC_LEDGER.md](METRIC_LEDGER.md) | Per-metric provenance: definition, source artifact, and canonical value for each reported number. |
| [`headline-evidence/`](headline-evidence/) | Per-cell byte-addressable evidence bundle (one `SOURCE.md` per headline cell) — the reviewer re-verification surface. Uses the **legacy cell numbering**; use [`PAPER-EVIDENCE.md`](PAPER-EVIDENCE.md) for the canonical mapping. |
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
| [`paper-profile.md`](paper-profile.md) | Venue profile. The legacy EAAI-era and anonymous drafts moved to [`ARCHIVE/legacy-paper/`](ARCHIVE/legacy-paper/) on 2026-10-21; the live manuscript is [`drafts/paper-A-final.md`](drafts/paper-A-final.md). |
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
| [`reproducibility_record.md`](reproducibility_record.md) | **Historical** reproducibility record (2026-09-05); the current recipe is [`reproduce.md`](reproduce.md). |
| [`verification_outputs.md`](verification_outputs.md) | Guide to the byte-addressable `verification_outputs/` tree. |
| [`code-release-checklist.md`](code-release-checklist.md) | **Historical** release-archive checklist for tag `v1.0.1-paper-final` (2026-09-14); the current release process is [`RELEASING.md`](RELEASING.md). |
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
- [`ARCHIVE/legacy-paper/paper-final-neurips.md`](ARCHIVE/legacy-paper/paper-final-neurips.md) — superseded venue draft (moved 2026-10-21).
- **Superseded compiled PDFs** — [`ARCHIVE/legacy-paper/paper-final-neurips.pdf`](ARCHIVE/legacy-paper/paper-final-neurips.pdf) (NeurIPS-era), [`ARCHIVE/legacy-paper/paper-eaai.pdf`](ARCHIVE/legacy-paper/paper-eaai.pdf) (EAAI-era), [`ARCHIVE/legacy-paper/paper-tnnls.pdf`](ARCHIVE/legacy-paper/paper-tnnls.pdf) (byte-identical duplicate of `paper-eaai.pdf`). All three moved to `ARCHIVE/legacy-paper/` on 2026-10-21; the live PDF is [`drafts/paper-A-final.pdf`](drafts/paper-A-final.pdf).
- **Superseded top-level submission artifacts** — [`../cover_letter.md`](../cover_letter.md) (ICLR-2027 / NeurIPS-workshop era), [`../submission_checklist.md`](../submission_checklist.md) (ICLR-2027 era), and [`../supplementary.md`](../supplementary.md) (NeurIPS/ICML-era template) are **legacy and read by no current tooling** (each carries a top banner). The canonical TNNLS package is [`../tnnls_submission/`](../tnnls_submission/); the EAAI-era package is archived at [`../eaai_submission/`](../eaai_submission/).
- **Legacy / historical `docs/` documents** (each carries a top banner; full classification in [`audit/docs-legacy-inventory.md`](audit/docs-legacy-inventory.md)) — **legacy/superseded:** [`submission-checklist-final.md`](submission-checklist-final.md) (NeurIPS-era; → [`../tnnls_submission/submission_checklist.md`](../tnnls_submission/submission_checklist.md)), [`push-ready-summary.md`](push-ready-summary.md) (→ the retired `todo/` directory (`PUSH-READY.md`), removed 2026-10-13), [`STRATEGY_FRAMEWORK_SCOPE.md`](STRATEGY_FRAMEWORK_SCOPE.md) (2026-09-04 draft). **Historical records:** [`code-release-checklist.md`](code-release-checklist.md) (tag `v1.0.1-paper-final`), [`reproducibility_record.md`](reproducibility_record.md) (2026-09-05).
- [`ARCHIVE/legacy-paper/`](ARCHIVE/legacy-paper/) — **new 2026-10-21.** Every superseded
  manuscript body, compiled PDF and LaTeX intermediate (paper-draft.md,
  paper-draft-anonymous.md, paper-final-neurips.*, paper-eaai.pdf, paper-tnnls.pdf,
  the two `paper-draft-precut*.md.bak` snapshots, `paper-flat-ieeetran.*` and the
  `pdflatex-rerun*.log` iteration logs). Nothing here is read by tooling.
- [`ARCHIVE/audit-orphans/`](ARCHIVE/audit-orphans/) — **new 2026-10-21.** 25 audit
  records with zero inbound references (2026-09 paper-polish / cover-letter notes
  absorbed into `paper-A-final.*`). See `audit/INDEX.md` addendum.
- [`ARCHIVE/`](ARCHIVE/) — historical context, intentionally **not** part of the
  live mkdocs build (enforced by `mkdocs.yml` `exclude_docs`). Preserved on disk
  for archaeology; not maintained and not reachable from the GitHub Pages nav.

## 7. Documentation management conventions

Rules for keeping the tree navigable. They apply to any new document.

**Where a new document goes.**

| If the document is… | Put it in | Examples |
|---|---|---|
| Reviewer-facing reference or a source of truth | `docs/` (top level or a topic dir) and register it in this map | specs, theory, gate docs |
| A cell-level evidence verdict | [`paper-evidence.json`](paper-evidence.json), then regenerate [`PAPER-EVIDENCE.md`](PAPER-EVIDENCE.md) | WIN / OPEN / BLOCKED rows |
| A per-increment working record | `docs/audit/` (topic-clustered) | close-out notes, sweep records |
| Project-level management state | [`../todo.json`](../todo.json) | status, gates, gaps, assessment |

**One register, no parallel tables.** A new per-cell verdict goes into
`paper-evidence.json` (with an artifact, an audit, and a quote that the
validator checks) and is rendered into `PAPER-EVIDENCE.md`. Do **not** open a
new standalone evidence table: that is how the frozen manuscript, `CLAIMS.md`,
the 2026-10-19 evidence-grade table, and `todo.json` drifted apart.

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
[`../README.md`](../README.md), [`../todo.json`](../todo.json), and the
submission package, re-running `tools/check_claims_consistency.py` and refreshing
the SHA-256 column in [`../tnnls_submission/MANIFEST.md`](../tnnls_submission/MANIFEST.md).

## Link-rot contract

Every path on this page is verified against the source tree by
[`../tools/check_docs_against_code.py`](../tools/check_docs_against_code.py) on
every CI run. Renaming or archiving any doc will break CI at the same time this
page becomes stale — that is the intended behaviour, not a bug. If a future PR
moves a doc, this page must be updated in the same PR.
