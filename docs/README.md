# Documentation map for `flowa-multistep-reinference`

This page is the single discoverable entry point for the 150-file `docs/`
tree. Every entry below is a one-sentence pointer to a hand-authored or
peer-reviewed doc, grouped into six sections in the order a new reader
should approach them: start-here first, then architecture and governance,
algorithms and theory, evidence and results, quality gates, and finally
the survey archives. The auto-generated API reference for the
`adaptive_reflow` package (rendered from module docstrings + typed
signatures by mkdocstrings) is reachable from the repo root
[`README.md`](../README.md) link
"<https://silverenternal.github.io/flowa-multistep-reinference/>", or
directly at [`api/index.md`](api/index.md); the on-disk landing page is
the doc *map*, not the API *reference* — they are different surfaces for
different audiences.

## 1. Start here

| Doc | Read it for |
| --- | --- |
| [`TUTORIAL.md`](TUTORIAL.md) | Five-minute quickstart that loads `TwoDimFMAdapter`, runs the suite, and runs a 2-D rectified-flow experiment with one of the four canonical schedulers. |
| [`PLUG_IN_YOUR_MODEL.md`](PLUG_IN_YOUR_MODEL.md) | Adapter-author on-ramp: five steps from a `.npz` checkpoint to a baseline-vs-framework comparison table. |
| [`QUICKSTART.md`](../QUICKSTART.md) | Repo-root on-ramp: install, run the suite, walk one round against `ToyGaussianAdapter`, capture a golden, run the docs scanner. |
| [`FAQ.md`](../FAQ.md) | Top-20 short answers to the questions that come up most often during review and onboarding. |

## 2. Architecture and governance

| Doc | Read it for |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Package layout, dependency DAG, governance invariants, the four-step Adapter Protocol recipe for adding a new model, the full file inventory. |
| [STRATEGY_FRAMEWORK_SCOPE.md](STRATEGY_FRAMEWORK_SCOPE.md) | Framework scope strategy (2026-09-04 draft): why SOTA-model reproduction is the wrong validation strategy and what to do instead. |
| [ADAPTER_INTERFACE_SPEC.md](ADAPTER_INTERFACE_SPEC.md) | Authoritative adapter spec (DTB-G1): the eight-method `FlowMatchingODEAdapter` Protocol, capability handshake, hard rules, and a `ToyLinearAdapter` worked example. |
| [DEPRECATION.md](DEPRECATION.md) | Versioned deprecation table for `adaptive_reflow.legacy/` and friends, with replacement paths and sunset versions. |
| [RELEASING.md](RELEASING.md) | The PyPI release process for this research-stage package, including the dry-run workflow gated on paper acceptance. |
| [adr/](adr/) | 16 architecture-decision records — universal-vs-molecular split, typed-contracts core boundary, seven-step engine operation order, fail-closed audit-code policy, theorem-aligned FID per-round pattern, etc. |
| [review/B5-VERIFICATION.md](review/B5-VERIFICATION.md) | B5 batched-trajectories verification report (load-bearing design note). |
| [design/B5_BATCHED_TRAJECTORIES.md](design/B5_BATCHED_TRAJECTORIES.md) | B5 batched-trajectories design note (load-bearing design note). |

## 3. Algorithms and theory

| Doc | Read it for |
| --- | --- |
| [ALGORITHMS.md](ALGORITHMS.md) | Full catalog of every concrete operator: 16 schedulers, 5 drivers, 8 merge operators, 6 blenders, with paper grounding and copy-paste samples. |
| [schedule-theory.md](schedule-theory.md) | Theory behind the per-round `n_cap` schedule: cosine, polynomial, sigmoid, convergence-adaptive, codimension-sheet, sequential. |
| [sequential-protocol.md](sequential-protocol.md) | `SequentialScheduler` design: piecewise schedule shapes for regimes that want multi-phase composition by round range. |
| [defaults-matrix.md](defaults-matrix.md) | Default scheduler / driver / merge / blender choices per target distribution and per model family. |
| [distinguishing-from-reflow.md](distinguishing-from-reflow.md) | How this framework differs from a vanilla rectified-flow sampler at the algorithm-abstraction level (the four-axis `(scheduler, driver, merge, blender)` product). |
| [lean/](lean/) | Lean 4 formalization survey of the paper theorem-to-framework mappings (index at [lean/INDEX.md](lean/INDEX.md)); includes FLOWA_INTEGRATION.md, THEOREM_1_MAPPING.md, PAPER_QUANTITIES_MAPPING.md, VERIFICATION.md, and the open GAPS.md. |

## 5. Evidence and results

| Doc | Read it for |
| --- | --- |
| [CONSOLIDATED_RESULTS.md](CONSOLIDATED_RESULTS.md) | Single source of truth for every measured framework evidence record: 27 + 80 algorithm uplifts, SOTA 2-D RF + CIFAR-10 RF verifications, two toy framework comparisons, defensive engineering. |
| [CLAIMS.md](CLAIMS.md) | CLM-NNN claim ledger (governance document) — every substantive claim the framework makes, with `Asserted by` / `Disputed by` references verified by `tools/check_claims_consistency.py`. |
| [ABLATION.md](ABLATION.md) | 23-cell 2-D RF ablation (eight canonical configurations × two targets + three paper-grounded + two post-fix cells); every cell run with `seed=42`, 20 rounds, 30 RK4 steps. |
| [benchmark-uplifts.md](benchmark-uplifts.md) | Round-1 Phase-2 algorithm-uplift benchmark: 27 uplifts, before/after. |
| [benchmark-round2-uplifts.md](benchmark-round2-uplifts.md) | Round-2 comprehensive uplift benchmark: 83 framework-internal + framework-external uplifts, before/after. |
| [benchmark-deep-uplifts.md](benchmark-deep-uplifts.md) | Comprehensive P0/P1 deep-uplift benchmark across both internal and external algorithm surfaces. |
| [INSIGHTS.md](INSIGHTS.md) | Narrative insight document: how the algorithm layer maps to Li (2024) Theorem 1 (sheet-tube scaling, root-cell bound, physical-complement suppression, Proposition-3 normalisation). |
| [tables/](tables/) | Paper-ready tables: paper quantities (`tbl1`), algorithms (`tbl2`), state machines (`tbl3`), CIFAR ablation (`tbl4`). |
| [figures/](figures/) | Paper-ready figures: protocol diagram (`fig1`), four feedback loops (`fig2`), per-round selection ratio (`fig3`), CIFAR-10 FID curve (`fig4`). |

## 6. Quality gates

| Doc | Read it for |
| --- | --- |
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | The six test layers (unit, contract, integration, regression, golden, mutation), the gates each change has to clear before merge, and the AST-level guards that hold the load-bearing invariants. |
| [PERFORMANCE_BUDGETS.md](PERFORMANCE_BUDGETS.md) | Kernel p95 wall-clock budgets in microseconds, the bench runner, the regression gate (`tools/bench/check_budgets.py`) that fails CI on hot-path regressions. |
| [environments.md](environments.md) | Two-tier venv layout: one project venv (`<repo>/.venv`, stdlib-only framework, no CUDA) + four model-specific venvs under `<repo>/.venvs/` (torch + per-model CUDA build). |
| [governance/](governance/) | Six governance audit documents: code organisation (`01`), algorithm (`02`), framework (`03`), test/CI (`04`), fix plan (`05`), verification report (`06`). |
| [audit/](audit/) | Phase-4 docstring audit (PHASE4_DOCSTRING_AUDIT.md) and EPSILON_DIRECTION.md (regime-aware epsilon selector direction record). |

## 7. Survey archives

These three directories hold dozens of dated markdown files that capture
the experiment-by-experiment record of major research campaigns. A new
reader should reach for CONSOLIDATED_RESULTS.md first, then the
directory-level entry points below — the per-file documents are
intentionally archival and rot-tolerant.

- **`r4-survey/`** (23 documents) — SOTA-FM experiment log from
  2026-01 through 2026-04: 2-D + MNIST + CIFAR-10 experiments, weights
  acquisition, harness bugs, fix plans, code-review audits. Entry point:
  [`r4-survey/07-sota-experiment-protocol.md`](r4-survey/07-sota-experiment-protocol.md).
- **`r5-survey/`** (5 documents) — SOTA-FM candidate selection and the
  gate-fix research / plan. Entry point:
  [`r5-survey/01-sota-fm-candidates.md`](r5-survey/01-sota-fm-candidates.md).
- **`r17-survey/`** (16 documents) — Current paper-parity evidence chain
  (2026-09 state report), image-eval tier-2 progress, paper-table
  template, synthetic-oracle audit, algorithm-correctness-evidence
  walkthrough. Entry point:
  [`r17-survey/state-report.md`](r17-survey/state-report.md).
- **`ARCHIVE/`** holds historical context that is intentionally **not**
  part of the live mkdocs build (enforced by `mkdocs.yml` `exclude_docs`).
  It is preserved on disk for archaeology but is not maintained and is
  not reachable from the GitHub Pages navigation.

## Link-rot contract

Every path on this page is verified against the source tree by
[`tools/check_docs_against_code.py`](../tools/check_docs_against_code.py)
on every CI run. Renaming or archiving any doc will break CI at the
same time this page becomes stale — that is the intended behaviour, not
a bug. If a future PR moves a doc, this page must be updated in the
same PR.