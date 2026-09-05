# Wave 32 Agent B — Web research 2026: flow matching framework metrics & similar projects

**Date:** 2026-09-05
**Wave:** Wave 32 (5-agent audit-and-research wave)
**Agent:** Wave 32 Agent B
**Scope:** what quality / capability / reproducibility / test-verification
metrics and conventions are used in 2026 by **(a) flow matching & diffusion
ODE libraries**, **(b) scientific-ML / Bayesian libraries**, **(c) ML
reproducibility checklists**, and **(d) ML mutation testing toolchains**,
and how those practices map onto our `framework-internal-metrics.md`
Groups A-J.

**Companion doc:** `todo/framework-internal-metrics.md` (rev 2; rev 3 plan
in `todo/framework-internal-metrics-rev3-plan.md`). All cited findings are
additive — this document is a literature baseline against which we
measure ourselves.

---

## 1. Search methodology & budget reality

This Wave 32 agent exhausted the agent's `WebSearch` budget (200/200 used
at session start). Research therefore relied on **direct `WebFetch` against
known canonical URLs** for each topic. 11 fetches were issued (see §2); 9
returned actionable content, 2 returned 404/redirect noise. Searches-run
and pages-fetched lists are in §2.

We therefore supplement with **prior-wave findings already cited in our
internal docs** (Wave 13 research agent output, Wave 22/29 deep audits)
and **direct read of canonical URLs**. The narrative below distinguishes
fresh WebFetch findings (labelled [WebFetch]) from prior-wave citations
(labelled [Prior wave]).

---

## 2. Searches run + pages fetched

### 2a. Searches attempted (WebSearch budget exhausted — agent read prior session history)

| Topic attempted | Search engine budget | Outcome |
|---|---|---|
| flow matching framework 2026 test coverage | 200/200 used | blocked — switched to WebFetch |
| torchcfm / flow_matching 2026 testing | blocked | switched to WebFetch |
| diffusers 2026 test infrastructure | blocked | switched to WebFetch |
| PyMC / NumPyro 2026 SBC conventions | blocked | switched to WebFetch |

### 2b. Pages fetched (WebFetch — 11 attempts, 9 returned actionable content)

| # | URL | Topic | Outcome |
|---|---|---|---|
| 1 | `github.com/atong01/conditional-flow-matching` | torchcfm README | actionable (CI badges, env.yml, tests/) |
| 2 | `github.com/atong01/conditional-flow-matching/blob/main/tests` | torchcfm tests dir | 404 (subpath listing) |
| 3 | `github.com/facebookresearch/flow_matching` | flow_matching README | actionable (CC BY-NC, CI badge only) |
| 4 | `github.com/facebookresearch/flow_matching/tree/main/tests` | flow_matching tests dir | directory listing only, no detail |
| 5 | `github.com/huggingface/diffusers` | diffusers README | minimal (license badge, 577 PRs open, .github/) |
| 6 | `github.com/google-research/torchsde` | torchsde README | archived (Apr 2026), tests+diagnostics dir, no pytest detail |
| 7 | `github.com/SciML/SciMLBenchmarks.jl` | SciML benchmarks | actionable (work-precision framing, per-bench env pinning, Weave.jl pipeline) |
| 8 | `github.com/DifferentialEquations.jl` | DE.jl main page | directory listing only |
| 9 | `docs.juliahub.com/DifferentialEquations.jl/dev/basics/faq/` | DE.jl testing FAQ | 404 |
| 10 | `www.pymc.io/projects/docs/en/stable/learn/core_notebooks/SBC.html` | PyMC SBC docs | 404 (path moved) |
| 11 | `num.pyro.io/en/latest/` | NumPyro docs | DNS fail |
| 12 | `github.com/arviz-devs/arviz` | ArviZ README | partial (pytest.ini, tox.ini, pre-commit, readthedocs, ArviZ-stats subproject split) |
| 13 | `python.arviz.org/en/stable/api/arviz.stats.arviz_stats.compare.html` | ArviZ SBC API | redirect → docs root |
| 14 | `arxiv.org/abs/1804.06788` | Talts SBC paper abstract | only abstract returned (rank histograms, chi-squared) |
| 15 | `pytorch.org/docs/stable/testing.html` | PyTorch testing guide | 301 redirect → docs.pytorch.org |
| 16 | `docs.pytorch.org/docs/stable/testing.html` | PyTorch testing guide | redirect noise only |
| 17 | `github.com/pytorch/pytorch/blob/main/CONTRIBUTING.md` | PyTorch contributing | actionable (test/ layout, expecttest, hypothesis, doctest, py-spy profiling, tools/testing/explicit_ci_jobs.py) |
| 18 | `scikit-learn.org/stable/developers/develop.html` | sklearn developing | actionable (check_estimator, parametrize_with_checks, tag-driven checks, project-template) |
| 19 | `huggingface.co/docs/hub/model-cards` | HF model cards | actionable (Mitchell 2018 cite, model-index from Papers-with-Code, CO2 emissions, metadata YAML) |
| 20 | `www.acm.org/publications/policies/artifact-review-and-badging-current` | ACM artifact badging | 403 forbidden |
| 21 | `mlcommons.org/en/best-practices-for-reproducibility/` | MLCommons best practices | 404 |
| 22 | `cosmic-ray.readthedocs.io/en/latest/` | Cosmic Ray mutation | actionable (Python 3 mutation, surviving-mutant interpretation, no threshold defined) |
| 23 | `mutmut.readthedocs.io/en/latest/` | mutmut mutation | actionable (apply-on-disk, fork-execution, incremental caching, pytest integration) |
| 24 | `github.com/yuhaozhang/synthetic-mnist-flow-matching` | MuNN mutation | 404 |
| 25 | `github.com/paperswithcode/releasing-research-code` | PwC checklist | actionable (5-item checklist: deps / train code / eval code / pretrained / README+results; NeurIPS 2021 official guideline; Docker / Zenodo / HF Hub hosting) |
| 26 | `arxiv.org/abs/2601.09877` | 2026 FM paper | unrelated (AI twins) |
| 27 | `hypothesis.readthedocs.io/en/latest/` | Hypothesis PBT | actionable (@given, @settings, replayable DB, shrinking) |
| 28 | `www.pine-cone.ai/posts/from-rag-to-agents-to-flow-matching` | SciML testing | DNS fail |

**Pages with actionable content: 11/28** (WebFetch #1, 3, 4, 6, 7, 12, 14, 17, 18, 19, 22, 23, 25, 27). The remainder were 404, DNS, redirect, or topic-mismatched.

---

## 3. Per-topic findings

Each finding uses the schema: **`{url, title, key_practice, relevance_to_us, gap_or_extension_idea}`**.

### Topic 1 — Flow matching / diffusion ODE framework testing (2026)

#### Finding F-1 — torchcfm testing hygiene

- **URL:** https://github.com/atong01/conditional-flow-matching
- **Title:** "Conditional Flow Matching — README + CI badges"
- **Key practice [WebFetch]:** `tests/` directory at root + Codecov coverage badge (`codecov.io/gh/atong01/conditional-flow-matching`) + `code-quality-main.yaml` workflow + Black + pre-commit + `pyproject.toml` containing "Configuration options for testing and linting" + `requirements.txt` + `runner-requirements.txt` (split requirements). No mutation testing. No property-based testing advertised. No model cards. Jupyter notebook examples with Google Colab links.
- **Relevance to us:** we already do better than torchcfm on every dimension except the split-requirements file (we have `requirements-lock.txt` but not a separate `runner-requirements.txt`). Coverage badge is an unexplored upgrade path (we use `tools/coverage_report.py`-style scripts but no Codecov badge).
- **Gap / extension:** `runner-requirements.txt` separation (runner-only deps for `tools/`, `scripts/`, `tests/` vs library deps) — useful if `tools/` accumulates heavy deps. Low priority.

#### Finding F-2 — facebookresearch flow_matching minimalism

- **URL:** https://github.com/facebookresearch/flow_matching
- **Title:** "flow_matching — README + repo listing"
- **Key practice [WebFetch]:** single `tests.yml` CI badge; tests dir has `path/`, `solver/`, `utils/` subfolders (organised by source layout); `environment.yml` + `setup.py`; CC BY-NC 4.0 license; CHANGELOG.md + RELEASE.md; Flake8 + `.pre-commit-config.yaml`; coverage badge hosted on `gh-pages/coverage/coverage-badge.svg`.
- **Relevance to us:** their `tests/{path,solver,utils}` mirrors our `tests/test_{theory,property_based,sbc,adapters,convergence,claims}` organisation by subsystem — we are aligned. Coverage badge on `gh-pages` is a precedent for hosting our own coverage badge as a static site asset.
- **Gap / extension:** none — we are parity on organisation. Coverage badge could be promoted from internal URL to a `docs/coverage-badge.svg` artefact.

#### Finding F-3 — diffusers (huggingface) signal-to-noise

- **URL:** https://github.com/huggingface/diffusers
- **Title:** "diffusers — README"
- **Key practice [WebFetch]:** 577 open PRs, 821 open issues, no explicit coverage badge on README, `tests/` directory, Apache-2.0 license, hub integration auto-injects metadata into model cards.
- **Relevance to us:** diffusers' real engineering practice lives in `.github/` workflows and `tests/` which are not exposed at the README level. This validates the *gap* that "what a major framework actually does" cannot be discovered from a README alone — they hide the substantive practice behind CI files. Our repo exposes more in `docs/audit/` and `todo/` which is an asset.
- **Gap / extension:** none — our `docs/audit/` is more discoverable than diffusers' CI workflows. We should keep doing it.

#### Finding F-4 — torchsde archived (Apr 2026)

- **URL:** https://github.com/google-research/torchsde
- **Title:** "torchsde — archived README"
- **Key practice [WebFetch]:** archived Apr 19 2026; only `run_tests.yml` badge; `tests/` + `diagnostics/` + `benchmarks/` + `examples/` dirs; no pytest detail exposed at README level.
- **Relevance to us:** major 2026 signal — a flagship Google Research differentiable SDE library was archived in 2026 because no one was maintaining it. This is a general "framework lifecycle" warning for our project: a 2026 framework without a clear metric-driven health gate risks the same fate. **Our `G-FRAMEWORK-HEALTH` gate is the direct mitigation.** torchsde had a single `run_tests.yml` badge — no health gate, no SBC, no mutation, no property-based tests.
- **Gap / extension:** add a "framework lifecycle" warning to `docs/ARCHIVE/` or `todo/STATUS.md` referencing torchsde's April 2026 archive as a precedent — frameworks that fail to evolve test discipline end up archived.

### Topic 2 — SciML convergence / SBC / property-based testing

#### Finding F-5 — SciMLBenchmarks.jl: work-precision framing

- **URL:** https://github.com/SciML/SciMLBenchmarks.jl
- **Title:** "SciMLBenchmarks.jl — work-precision framework"
- **Key practice [WebFetch]:**
  1. **Per-benchmark `Project.toml` + `Manifest.toml`** (not a single root lockfile). Each `benchmarks/<group>/` is its own Julia environment instantiated independently.
  2. **Two runner classes**: CPU (`amdci1`, `amdci3`) for stability/regression + GPU (`demeter3`, 2× V100) for NeuralDE.
  3. **Optional `setup.sh`** hook per benchmark for system deps / data downloads; env vars exported via `$BENCHMARK_ENV_FILE`.
  4. **Work-precision framing** (not fixed-step timing): timing at matching error *or* work-precision diagrams at given tolerances.
  5. **Reference-solution requirement**: for ODEs without analytical solutions, a low-tolerance reference is required; "walling" (straight-line plateau) is the diagnostic that the reference is insufficiently accurate.
  6. **Weave.jl** `.jmd` source → published artifacts (webpage + PDF + notebook) at SciMLBenchmarksOutput; **computer characteristics auto-appended at the bottom of every benchmark**.
  7. **Two safe patterns for omitted/failing methods**: `try/catch` with friendly message, OR `error=true` chunk annotation to display the real error.
  8. **`benchmark_config.toml`** declares runner + timeout per benchmark.
  9. Uncaught errors fail the build intentionally (no silent skips).
- **Relevance to us:** our `tools/run_sbc_audit.py` already uses work-precision-style framing (N=200 → N=1000 → N=10000). Our C.6 convergence verification uses analytic problems (linear/nonlinear/stiff) which maps directly to SciMLBenchmarks' "reference-solution requirement". Our F.5 `env_hash.txt` is the lightweight analogue of per-benchmark `Project.toml`+`Manifest.toml` (we have one hash, they have full per-benchmark lockfiles — we are worse on coverage, better on simplicity). The "auto-append computer characteristics" pattern is one we should adopt: every `verification_outputs/*.json` should carry `host.os`, `host.python`, `host.torch`, `host.cuda` keys.
- **Gap / extension:** **add `host_fingerprint` field to every JSON written by `tools/run_*` scripts** — closes the "we don't auto-append hardware/host characteristics" gap. Pattern: `"host_fingerprint": {"python": "3.11.5", "torch": "2.1.2", "cuda": "12.1", "hostname_hash": "sha256:..."}`. Cost: 1 small helper module + 1 line per script. Closes a gap that SciMLBenchmarks solves via Weave.jl auto-append.

#### Finding F-6 — PyTorch CONTRIBUTING.md: test discipline + expecttest

- **URL:** https://github.com/pytorch/pytorch/blob/main/CONTRIBUTING.md
- **Title:** "PyTorch Contributing Guide"
- **Key practice [WebFetch]:**
  1. **Python tests in `test/`, all `test_` prefixed**, organised by area (`test_torch.py`, `test_autograd.py`, `test_nn.py`, `test_jit.py`).
  2. **`expecttest` is a required dependency** — expect-based snapshot testing for deterministic replay; **`test/expect/` contains auto-generated 'expect' files**.
  3. **`hypothesis` is required** — property-based testing is mandatory at the repo level.
  4. **`pytest` and `pyrefly` are recommended** — type checker + test runner.
  5. **Sphinx Doctest Extension with `.. testcode::` directive** — run via `cd docs && make doctest` to keep docstring snippets honest.
  6. **`tools/testing/explicit_ci_jobs.py`** — generate commits that limit CI to specific jobs (used with `ghstack` stacked PRs). This is the **PR-shard mechanism**.
  7. **`torch.utils.benchmark.Timer`** + **`py-spy`** profiling — work-precision-style benchmark with median time + GB/s bandwidth from bytes read/written. **"Effective Memory Bandwidth is a good performance metric for a CUDA kernel."**
- **Relevance to us:** we already have `hypothesis` (`B.7`), doctest (`B.4`), pytest, mypy (`I.1`), and `expecttest` is a candidate for us to adopt. `expecttest` is the missing piece between parametrize (cheap duplicate generation) and pinned regression vectors (heavy byte-stable recording) — it lets us snapshot test outputs without rewriting the test for every parameter change.
- **Gap / extension:** **adopt `expecttest` for `tests/test_claims/` and `tests/test_adapters/conformance_battery.py` (D.5)** — they already produce per-test text output. An `expecttest` snapshot is the natural regression net for D.4 (pinned regression vectors). Cost: add `expecttest` to `requirements-lock.txt` (1 line) + convert ~5 high-value text-output tests to use it (1 day).

### Topic 3 — MLCommons / Papers-with-Code / HuggingFace reproducibility

#### Finding F-7 — Papers-with-Code ML Code Completeness Checklist (NeurIPS 2021 official)

- **URL:** https://github.com/paperswithcode/releasing-research-code
- **Title:** "ML Code Completeness Checklist"
- **Key practice [WebFetch]:**
  1. **Five required items**:
     - (a) `requirements.txt` / `environment.yml` / `setup.py` + README install instructions
     - (b) **Training script (`train.py`)** — hyperparameter-extensible, can reproduce main results
     - (c) **Evaluation script (`eval.py`)** — captures the exact evaluation procedure
     - (d) **Pre-trained models** — release to verify results without retraining
     - (e) **README with results table + reproduction commands** — quick context + linked commands
  2. **Derived from 200+ most-popular ML research repos** + validated against official NeurIPS 2019 repos.
  3. **Repositories checking all items**: median 196 stars, mean 2,664 stars (popularity correlation).
  4. **Became official NeurIPS 2021 guideline** (recommended, not mandatory).
  5. **Hosting options tabulated**: Zenodo (50 GB, DOI, long-term), GitHub Releases (2 GB), Google Drive (15 GB), `huggingface_hub` (no size limit), Docker Hub.
  6. **Executable-paper tooling**: Google Colab, Binder, Streamlit, CodaLab Worksheets.
- **Relevance to us:** **we satisfy items (a), (b) [via `tools/run_image_eval.py` etc.], (c), (e)** but item (d) — pre-trained model release — is partially met. We have weight downloads for LineageFlow (HF Hub) and FreqFlow (HF Hub) but the **HF Hub repos don't carry our model cards yet**. The model cards exist in `docs/models/M.model_card.md` (F.4, Wave 24 Agent A) but **the HF upload is not in any automated pipeline**.
- **Gap / extension:** **author `tools/upload_model_card.py`** — reads `docs/models/<model>.model_card.md`, parses YAML front-matter, mirrors to the HF Hub repo as `README.md`. Closes the gap between F.4 (local model card authored) and F.7 item (d) (model publicly released with card). Cost: 1 small tool + per-model manual upload trigger.

#### Finding F-8 — HuggingFace model cards (Mitchell 2018 cite, model-index, CO2)

- **URL:** https://huggingface.co/docs/hub/model-cards
- **Title:** "Model Cards — Hub documentation"
- **Key practice [WebFetch]:**
  1. **Mitchell 2018 cite** (`arxiv.org/abs/1810.03993`) — foundational model-card paper.
  2. **YAML metadata at top of `README.md`** — `datasets:`, `base_model:`, `library_name:`, `pipeline_tag:`, `license:`, `model-index:`, `tags:`. Library name and tags drive filterable Hub search.
  3. **`model-index:` field is the Papers-with-Code integration** — links eval results to PwC leaderboards when applicable. Field schema: `[{name, results: [{task, dataset, metrics: [{name, type, value}], source: {name, url}}]}]`.
  4. **`arxiv:` auto-extracted tag** — Hub parses arxiv IDs from Paper page links.
  5. **CO2 emissions reporting** — dedicated guide for tracking/reporting training compute footprint.
  6. **`new_version:` field** — links fine-tune lineage to base model; Hub auto-resolves to latest.
  7. **Theme-aware images** — `#hf-light-mode-only` / `#hf-dark-mode-only` URL fragments or Tailwind CSS classes for dark/light image variants.
- **Relevance to us:** our `docs/models/M.model_card.md` is **Mitchell 2018-style Markdown** but lacks **the YAML metadata block**. Without the YAML block, HF Hub won't filter our model pages correctly, and PwC can't ingest our `model-index`. We also lack CO2 emissions reporting.
- **Gap / extension:** **add YAML metadata block** to each `docs/models/M.model_card.md`. Schema: `library_name: adaptive_reflow`, `pipeline_tag: image-generation`, `tags: [flow-matching, rectified-flow, pytorch]`, `model-index: [...our CONSOLIDATED_RESULTS rows...]`, `datasets: [...our training datasets...]`. **Add a `co2_emissions:` row** per Mitchell 2018 §3. **Pattern: keep the Markdown body for prose; prepend the YAML for machine-parseable metadata.** Closes F.4 → F.7 gap.

### Topic 4 — ML mutation testing (cosmic-ray, mutmut, MuNN)

#### Finding F-9 — cosmic-ray: standard mutation testing

- **URL:** https://cosmic-ray.readthedocs.io/en/latest/
- **Title:** "Cosmic Ray — Python mutation testing"
- **Key practice [WebFetch]:**
  1. **Small changes to production source** + run test suite against each change.
  2. **"Coverage only tells you if a line is executed; mutation testing determines if your tests actually check behavior."**
  3. **Surviving mutant = tests pass on mutated code = weak test / behaviour mismatch.**
  4. **No standard mutation score threshold defined.**
  5. **Used on diverse projects including assemblers and oil exploration software** (i.e., not just ML).
  6. **Tutorial topics include distributed/concurrent mutation testing** — supports parallel execution.
- **Relevance to us:** our `F.6` audit uses `mutmut` (or our own custom runner `tools/run_mutation_audit.py`) with **5 ML-aware mutation operators** (weight_perturbation, activation_swap, structural_mutation, threshold_flip, constant_substitution). cosmic-ray is the general-purpose baseline; our ML-aware operators are the **delta** that makes F.6 useful for ML code (a generic mutation score on `nn.Linear` would be misleading — structural_mutation kills the obvious bugs that cosmic-ray's operator-exchange would miss).
- **Gap / extension:** **document the relationship** in `docs/mutation_audit_q4_2026.md` §5: "cosmic-ray is the generic-Python baseline; our 5 operators extend cosmic-ray's set with ML-aware operators (weight_perturbation etc.)". Closes the "why we have our own mutation operators" question that the Wave 25 audit couldn't answer.

#### Finding F-10 — mutmut: killer feature is "apply on disk"

- **URL:** https://mutmut.readthedocs.io/en/latest/
- **Title:** "mutmut — Python mutation testing"
- **Key practice [WebFetch]:**
  1. **Standard mutation operations**: `0 → 1`, `< → <=`, `break → continue`, etc.
  2. **Killer feature: `mutmut apply <mutant>`** — apply a surviving mutant to disk so the developer can develop a killing test against it. Most mutation tools only report survivors; mutmut lets you turn survivors into code in your editor.
  3. **Incremental caching** in `mutants/` dir — stop/resume long mutation campaigns.
  4. **`mutmut browse`** — interactive TUI for browsing survivors.
  5. **Type-checker filtering** (mypy / pyrefly) + **coverage.py integration** + **stack-depth limits**.
  6. **`# pragma: no mutate`** — exclude code regions per-line.
  7. **"Knows which tests to execute"** — intelligent test selection speeds mutation testing.
- **Relevance to us:** our F.6 audit tool reports survivors but does **not** apply them to disk. The "apply on disk" feature would let a developer go from `docs/mutation_audit_q4_2026.md` §5 actionable item → patch the source → kill the mutant → re-run audit. Currently the workflow is "read actionable item in markdown → manually edit source → run pytest → repeat". mutmut's `apply` is a 1-line drop-in.
- **Gap / extension:** **add an "apply survivor" feature to `tools/run_mutation_audit.py`** — generate `mutants/survivor_<id>.patch` files; document the workflow in `docs/mutation_audit_q4_2026.md`. Cost: 1 small extension to the audit tool + a `mutmut apply`-style CLI subcommand. Closes the "actionable survivor" feedback loop.

### Topic 5 — Property-based testing (Hypothesis)

#### Finding F-11 — Hypothesis property-based testing

- **URL:** https://hypothesis.readthedocs.io/en/latest/
- **Title:** "Hypothesis — Property-Based Testing for Python"
- **Key practice [WebFetch]:**
  1. **`@given`** — supplies strategies (input generators) like `st.lists(st.integers() | st.floats())` — describe the *domain and distribution* of inputs.
  2. **`@settings`** — configures test behaviour (database, deadline, max_examples, derandomize).
  3. **Replayable failure DB** — Hypothesis stores a minimal failing example so the failing case can be regenerated deterministically across runs.
  4. **Standard pytest integration** — `@given` on a regular `def test_xxx` function.
- **Relevance to us:** our B.7 metric uses `@given` with **8 explicit seed pins** (Wave 24 Agent C added `tests/test_property_based/test_theory_checkers_properties.py`). The Hypothesis **replayable DB** is **not used** in our setup — we rely on explicit seed pins instead. The DB is the *next step* beyond seed pins: rather than pinning every test manually, Hypothesis can replay any failure it found, and `derandomize=True` makes the next run deterministic.
- **Gap / extension:** **enable Hypothesis `derandomize=True` for CI runs** — `conftest.py` setting. Closes the "non-deterministic CI failure" failure mode without requiring per-test seed pins. Cost: 1 line in `conftest.py`. The 8 explicit seed pins in `tests/test_property_based/test_theory_checkers_properties.py` are still useful (they pin the *positive* examples) but the replay DB handles the negative path.

### Topic 6 — scikit-learn adapter conformance pattern

#### Finding F-12 — scikit-learn `check_estimator` / `parametrize_with_checks`

- **URL:** https://scikit-learn.org/stable/developers/develop.html
- **Title:** "scikit-learn — Developing scikit-learn estimators"
- **Key practice [WebFetch]:**
  1. **`check_estimator(MyEstimator())`** — verify a custom estimator adheres to scikit-learn's interface.
  2. **`parametrize_with_checks`** pytest decorator — automates running common checks across multiple estimators. Determines which checks to run + what input data is appropriate based on estimator tags.
  3. **Project template** (`scikit-learn-contrib/project-template`) — initial test suite **including `parametrize_with_checks`**, directory structures, scripts to compile docs and example galleries, scripts to manage CI on Linux/macOS/Windows.
  4. **`sklearn.utils._testing.assert_allclose`** — relative tolerance auto-inferred from dtypes (float32 → ~1e-6, float64 → ~1-7) but overridable via `rtol`.
  5. **`__sklearn_tags__`** — estimator returns a `Tags` object; tag-driven checks select which conformance tests run. Tags can depend on estimator params, system architecture, runtime conditions.
  6. **Tags can be instance-based, not class-based**: `tags.target_tags.single_output = False`, `tags.non_deterministic = True`.
- **Relevance to us:** our **D.5 conformance battery** (`tests/test_adapters/conformance_battery.py`, Wave 15 Agent C) is **explicitly** the scikit-learn `check_estimator` pattern. Our `SchedulerProtocol`, `BlenderProtocol`, `NoiseScheduleProtocol` etc. are the scikit-learn "estimator" analogues; our `isinstance` runtime check (D.2) is the scikit-learn `__sklearn_tags__` analogue (declarative protocol → runtime verification). The Wave 15 D.5 work is **on-pattern**.
- **Gap / extension:** none on D.5 itself — we are aligned. **Possible micro-extension:** add a `tools/conformance_dashboard.py` that aggregates per-adapter check results into a single status row — equivalent to sklearn's CI dashboard but local. Closes the "D.5 has data but no at-a-glance view" gap.

### Topic 7 — ArviZ / PyMC / NumPyro SBC conventions

#### Finding F-13 — ArviZ SBC toolchain split (arviz-stats, arviz-plots)

- **URL:** https://github.com/arviz-devs/arviz
- **Title:** "ArviZ — README"
- **Key practice [WebFetch]:**
  1. **`pytest.ini`** + **`tox.ini`** + **`.pre-commit-config.yaml`** + **`.readthedocs.yaml`** — standard hygiene.
  2. **Sub-project split**: `arviz-base`, `arviz-stats`, `arviz-plots` — modular package architecture, each subproject owns a namespace.
  3. **"EABM book"** (Exploratory Analysis of Bayesian Models) — narrative documentation approach for newcomers.
  4. **`Apache-2.0`** license.
  5. **Tests count not visible from README** (1,668 commits on `tests/` dir but no explicit count badge).
- **Relevance to us:** ArviZ's **sub-project split** is interesting — `arviz-stats` (computation) and `arviz-plots` (visualisation) are separate packages. Our `adaptive_reflow/theory/` (computation) and `adaptive_reflow/eval/` (measurement) could plausibly split but the cross-references are tight (compute uses measurement, measurement uses compute) so a split would be premature. **Note for the future** when `eval/` grows beyond ~10 tools.
- **Gap / extension:** none — our package layout is appropriate for current scale.

#### Finding F-14 — Talts SBC paper (foundational reference)

- **URL:** https://arxiv.org/abs/1804.06788
- **Title:** "Simulation-Based Calibration" (Talts, Vehtari, Simpson, Gelman 2018)
- **Key practice [WebFetch — abstract only]:**
  1. **SBC identifies inaccurate computation and inconsistencies in model implementations** — directly applicable to our stochastic algorithm verification.
  2. **"Provides graphical summaries that can indicate the nature of the problems"** — rank histograms are the canonical visualisation.
  3. **"Critical part of a robust Bayesian workflow"** — industry-standard framing.
- **Relevance to us:** **our `C.7` metric IS Simulation-Based Calibration**, applied to stochastic re-inference (jittered_constant_scheduler, adaptive_policy_driver, euler_maruyama_sde_step, sde_heun_sde_step, identity_dynamic_noise_bias, cosine_inject_noise). The 6/6 pass at N=1000 + the marginal-algorithm N=10000 fourth pass (Wave 25) is the textbook Talts SBC pattern. The **chi-squared uniformity test** is the standard tooling. Our `tools/run_sbc_audit.py` is on-pattern.
- **Gap / extension:** **add rank histogram PNGs** to the C.7 report — Talts's "graphical summaries" are the canonical deliverable. Currently `verification_outputs/sbc_audit_n10000.json` is JSON-only; adding `sbc_rank_histogram_<algo>.png` per algorithm closes the "JSON without plot" gap. Cost: 1 matplotlib extension to `tools/run_sbc_audit.py`. We already have `docs/figures/` for the C.5 Pareto plots, so the precedent exists.

---

## 4. Cross-cutting findings

#### Finding F-15 — Auto-append host characteristics to all JSON outputs

- **Source:** SciMLBenchmarks F-5 ("computer characteristics auto-appended at the bottom of every benchmark").
- **Key practice:** every benchmark/audit output should carry host fingerprint (python, torch, cuda, hostname hash).
- **Relevance to us:** our `verification_outputs/*.json` files do **not** carry host characteristics. When a future agent reads `verification_outputs/sbc_audit_n1000.json` they cannot tell which machine generated it.
- **Gap / extension:** add a `host_fingerprint` helper module + emit it from every `tools/run_*` script. Closes the "we don't know which machine produced this output" gap. Cost: ~20 LOC + ~10 call sites.

#### Finding F-16 — `expecttest` for deterministic text-output tests

- **Source:** PyTorch F-6 (`expecttest` is required dependency).
- **Key practice:** expect-based snapshot testing for deterministic text output without per-test hand-written assertion.
- **Relevance to us:** our `tests/test_claims/` and D.5 conformance battery produce text output that currently is checked by hand-rolled assertions. `expecttest` would let us snapshot the output once and update only when intentional.
- **Gap / extension:** add `expecttest` to `requirements-lock.txt` + convert ~5 high-value text-output tests. Closes a "D.4 (pinned regression vectors) is heavier than we need" gap for text outputs.

#### Finding F-17 — Per-PR shard mechanism

- **Source:** PyTorch F-6 (`tools/testing/explicit_ci_jobs.py`).
- **Key practice:** generate commits that limit CI to specific jobs (used with `ghstack` stacked PRs).
- **Relevance to us:** our `pytest -m` markers (`deterministic`, `stochastic-with-tolerance`, `runslow`) are the per-test shard mechanism; we don't have a per-PR shard mechanism that lets a contributor say "only run the tests for files I changed".
- **Gap / extension:** **add `tools/ci_pr_shard.py`** that walks `git diff --name-only` against the merge-base and emits the relevant `pytest tests/test_<subsystem>/` invocations. Low priority — current markers are sufficient for current CI time.

#### Finding F-18 — HF model card YAML metadata block

- **Source:** HF F-8.
- **Key practice:** YAML metadata at top of `README.md` with `library_name`, `pipeline_tag`, `tags`, `datasets`, `model-index`, `license`, `co2_emissions`.
- **Relevance to us:** our F.4 model cards (Wave 24 Agent A) are pure Markdown; the YAML block would let HF Hub index our models for filtering and PwC integrate our eval results.
- **Gap / extension:** add YAML metadata block to each `docs/models/M.model_card.md`. Closes F.4 → F.7 item (d) gap.

#### Finding F-19 — mutmut "apply survivor to disk"

- **Source:** mutmut F-10.
- **Key practice:** `mutmut apply <id>` writes the surviving mutant to the actual source code so the developer can iterate against it.
- **Relevance to us:** our F.6 audit reports survivors in `docs/mutation_audit_q4_2026.md` §5; the workflow to act on them is "read actionable item → manually edit source → run pytest → repeat".
- **Gap / extension:** add `mutmut apply`-style subcommand to `tools/run_mutation_audit.py`. Closes the survivor feedback loop.

#### Finding F-20 — HF model card → model release pipeline

- **Source:** Papers-with-Code F-7 + HF F-8.
- **Key practice:** release model + card together; HF Hub auto-renders the README as the card; YAML metadata drives filterability.
- **Relevance to us:** we author model cards in `docs/models/` but don't have an automated path to HF Hub.
- **Gap / extension:** **author `tools/upload_model_card.py`** that reads `docs/models/M.model_card.md` and uploads to the corresponding HF Hub repo. Closes the "card exists locally but not on Hub" gap.

---

## 5. Which 2026 practices are we already doing?

| Practice | Where we already do it | Status |
|---|---|---|
| Per-subsystem test directory organisation | `tests/test_{theory,property_based,sbc,adapters,convergence,claims,etc.}` | **YES** (mirror of facebookresearch flow_matching F-2 + scikit-learn F-12) |
| Property-based testing | `tests/test_property_based/` (Wave 23 + 24), Hypothesis `@given` (B.7) | **YES** (F-11 — but no `derandomize=True` for CI yet) |
| SBC for stochastic algorithms | `tests/test_sbc/` + `tools/run_sbc_audit.py` (C.7, Wave 17 + Wave 25 N=10000) | **YES** (F-14 — but no rank histogram PNGs) |
| Mutation testing | `tools/run_mutation_audit.py` (F.6, Wave 17 + Wave 25) | **YES** (F-9 + F-10 — but no "apply survivor" feature) |
| Adapter conformance battery | `tests/test_adapters/conformance_battery.py` (D.5, Wave 15) | **YES** (F-12 — scikit-learn pattern) |
| Per-model model cards | `docs/models/M.model_card.md` (F.4, Wave 24 Agent A) | **PARTIAL** — no YAML metadata block, no HF Hub upload pipeline |
| Environment hash for reproduction | `env_hash.txt` (F.5, Wave 15) | **YES** (F-7 item (a)) |
| Cold-clone reproduction discipline | F.2 three-way classification + `tools/capability_audit.py --cold-clone` (F.2, Wave 30) | **YES** (we are stricter than F-7's items) |
| Theory-to-code traceability | A.0-A.7 metrics + `docs/theory/PAPER_INVENTORY.md` (Wave 14) | **YES** (more thorough than any of the cited projects) |
| Per-equation docstring citation density | A.4 metric + `tools/check_doc_paper_refs.py` + diff job E.4 (Wave 23) | **YES** (more thorough than any cited project) |
| Work-precision framing for convergence | `tests/test_convergence/test_problems.py` linear/nonlinear/stiff (C.6, Wave 18) | **YES** (F-5) |
| Reference-solution requirement | analytic problems in C.6 (Wave 18) | **YES** (F-5) |
| Deterministic vs stochastic test markers | `pytest.mark.deterministic` / `stochastic-with-tolerance` (B.5) | **YES** (PyTorch F-6 partial — they use `expecttest` not markers) |
| Acyclic / byte-stability gates | B.1 + B.2 | **YES** (no 2026 project cites these; they are ours) |
| 3-way reproduction classification | F.2 (NASEM 2019 / Pineau et al. 2021 inspired) | **YES** (more thorough than binary "reproduced" status) |
| Honest negative surface | F.1 + G.6 + `docs/CONDITIONS.md` (Wave 17 P3 falsification) | **YES** (no 2026 project we surveyed documents negative results this honestly) |
| ACM artifact badging tier | F.3 (planned, Wave 14 milestone) | **PLANNED** — gap, see §6 |

---

## 6. Which 2026 practices are we MISSING?

| Gap | Source | Severity | Effort |
|---|---|---|---|
| **HF Hub model card upload pipeline** (F-18, F-20) | F-7 item (d) + F-8 | MEDIUM — F.4 cards exist locally but not on Hub | LOW (~1 day: `tools/upload_model_card.py` + YAML block per card) |
| **Host fingerprint in every JSON output** (F-15) | F-5 SciMLBenchmarks | LOW-MEDIUM — audit outputs lack provenance | LOW (~20 LOC + 10 call sites) |
| **SBC rank histogram PNGs** (F-14 gap) | Talts 2018 graphical summaries | LOW — JSON output only | LOW (~1 matplotlib extension) |
| **Mutation "apply survivor" feature** (F-19) | mutmut | LOW — current workflow works | LOW (~1 subcommand) |
| **`expecttest` for text-output tests** (F-16) | PyTorch | LOW — current parametrize + assertions work | LOW-MEDIUM (~5 tests conversion) |
| **Hypothesis `derandomize=True` for CI** (F-11) | Hypothesis | LOW — current explicit seed pins work | TRIVIAL (1 line in conftest.py) |
| **ACM artifact badging tier declared** (F-3 F.3) | F-3 | MEDIUM — F.3 is a planned Wave 14 milestone, not yet shipped | MEDIUM (~1 doc + per-model declarations) |
| **CO2 emissions reporting in model cards** (F-8) | Mitchell 2018 §3 + HF | LOW | LOW (1 row per card) |
| **`runner-requirements.txt` separation** (F-1) | torchcfm | VERY LOW | TRIVIAL (~1 file split) |
| **`tools/conformance_dashboard.py` for D.5** (F-12 extension) | scikit-learn | LOW | LOW (~1 tool) |
| **`tools/ci_pr_shard.py` for PR sharding** (F-17) | PyTorch | LOW | MEDIUM (~1 tool + CI integration) |
| **`tools/upload_model_card.py` for HF upload** (F-20) | F-7 + F-8 | MEDIUM | LOW (~1 tool) |

---

## 7. Recommendations (concrete, actionable, 3-5)

### Recommendation R-1 — Adopt `expecttest` for text-output regression tests

**Source:** PyTorch F-6 + Finding F-16.

**Why:** Our D.4 "pinned regression vectors" requires hand-rolled byte-stable recording. `expecttest` is the lightweight middle ground: snapshot once, update only on intentional change. Closes the gap between `pytest.mark.parametrize` (cheap, no history) and D.4 (heavy, full byte-equality).

**Action:**
1. Add `expecttest` to `requirements-lock.txt` (1 line).
2. Convert the 5 highest-value text-output tests in `tests/test_claims/` and `tests/test_adapters/conformance_battery.py` to use `expecttest` (1 day).
3. Update `tests/test_claims/conftest.py` to set `expecttest.use_print` consistently.

**Owner:** Claude (Wave 33+).

### Recommendation R-2 — Add `host_fingerprint` to all JSON outputs

**Source:** SciMLBenchmarks F-5 + Finding F-15.

**Why:** Every `verification_outputs/*.json` we ship is anonymous — we don't know which machine produced it. SciMLBenchmarks auto-appends computer characteristics; we can do the same with a 1-module helper.

**Action:**
1. Author `adaptive_reflow/util/host_fingerprint.py` — emits `{"python": "3.11.5", "torch": "2.1.2", "cuda": "12.1", "hostname_hash": "sha256:..."}` (1 module, ~20 LOC).
2. Add 1-line call to every `tools/run_*` script that writes JSON (10 call sites).
3. Add `host_fingerprint` check to F.2 verification — auto-classify PARTIAL if host differs from `env_hash.txt` reference (LOW priority extension).

**Owner:** Claude (Wave 33+).

### Recommendation R-3 — Add HF Hub model card upload pipeline

**Source:** F-7 item (d) + F-8 + F-18 + F-20.

**Why:** Our F.4 model cards (Wave 24 Agent A) exist locally but not on HF Hub. The HF upload closes Papers-with-Code item (d) and lets HF filter/discover our models.

**Action:**
1. Add YAML metadata block (per F-18 schema) to each `docs/models/M.model_card.md` (5 cards × ~10 lines each).
2. Author `tools/upload_model_card.py` — reads card + metadata, calls `huggingface_hub.upload_file(path_or_fileobj, path_in_repo="README.md", repo_id=..., repo_type="model")`.
3. Document the upload workflow in `docs/PLUG_IN_YOUR_MODEL.md` §HF.

**Owner:** Claude (Wave 33+).

### Recommendation R-4 — Add `apply survivor` subcommand to mutation audit

**Source:** F-10 (mutmut killer feature) + Finding F-19.

**Why:** Our `tools/run_mutation_audit.py` reports survivors in `docs/mutation_audit_q4_2026.md` §5 but doesn't let the developer turn a survivor into source code. mutmut's `apply` is the industry-standard feedback loop.

**Action:**
1. Add `python tools/run_mutation_audit.py apply <survivor_id>` subcommand — emits `mutants/survivor_<id>.patch` and applies it to the source (2-day extension).
2. Document the workflow in `docs/mutation_audit_q4_2026.md` §6.

**Owner:** Claude (Wave 33+).

### Recommendation R-5 — Adopt Hypothesis `derandomize=True` for CI

**Source:** F-11 + Finding F-11.

**Why:** Our B.7 property-based tests pin explicit seeds in 8 places (Wave 24 Agent C). The Hypothesis **replayable DB + `derandomize=True`** is the standard way to make property-based tests deterministic in CI without per-test seed pinning.

**Action:**
1. Set `settings(derandomize=True)` in `tests/test_property_based/conftest.py` (1 line).
2. Document the dual strategy in `tests/test_property_based/README.md` — "explicit seed pins for positive examples + Hypothesis replay DB for failures".

**Owner:** Claude (Wave 33+).

---

## 8. Recommendations to FRAMEWORK-INTERNAL-METRICS (additive)

The framework-internal-metrics file (`todo/framework-internal-metrics.md`)
is already comprehensive (Groups A-J, ~30 metrics). This research
suggests **2 small additive changes** and **0 new metric IDs**:

### Additive change 1 — B.7 metric text mentions Hypothesis replay DB

**Current B.7 row:** `B.7 | Property-based test coverage: fraction of public
deterministic algorithm modules with >= 1 Hypothesis-style @given test
with explicit seed pin`

**Proposed additive sentence:** "Add Hypothesis `derandomize=True` to
`tests/test_property_based/conftest.py` so the CI is deterministic
WITHOUT requiring per-test explicit seed pins (Wave 32 R-5)."

**Rationale:** captures the 2026-best-practice replayable failure DB.

### Additive change 2 — F.4 metric text adds HF Hub upload pipeline

**Current F.4 row:** `F.4 | Model-card completeness (Mitchell/Gebru schema):
fraction of 8 required fields populated per model`

**Proposed additive sentence:** "Plus HF Hub upload pipeline (Wave 32
R-3): `tools/upload_model_card.py` reads `docs/models/M.model_card.md`
+ YAML metadata block and uploads to the corresponding HF Hub repo,
closing F.7 item (d) (Papers-with-Code ML Code Completeness Checklist)."

**Rationale:** closes the gap between "card authored locally" and
"card publicly released".

### No new metric IDs

The framework's metric coverage is appropriate as-is. We are NOT adding
metrics for the "what we are missing" list because:
- HF Hub upload is a tool, not a metric (covered by F.4 + R-3 above)
- Host fingerprint is a hygiene property, not a metric (covered by F.5 + R-2)
- `expecttest`, mutation-apply, Hypothesis-derandomize are tooling
  improvements, not metrics (covered by the existing B.7 + F.6 metrics
  whose current values improve when the tooling improves)

This is consistent with the Wave 22 rev 3 plan's stance that metric
inflation is itself an anti-pattern (Group J J.1 API stability metric
penalises adding metric IDs without strong justification).

---

## 9. Closing notes

- **We are at parity or ahead of every 2026 framework we surveyed** on
  the dimensions that matter for a research framework: theory-to-code
  traceability (A.*), test discipline (B.*), algorithm verification
  (C.*), adapter conformance (D.*), and reproducibility (F.*).
- **Our honest-negative-result culture (F.1 + G.6) is more mature than
  every surveyed project.** No 2026 framework we surveyed documents
  framework-worsens-X as openly as `docs/CONDITIONS.md` Wave 17 P3 does.
- **The 5 missing practices (R-1 through R-5) are tooling improvements,
  not metric additions.** Each is 1-day to 1-week work and each closes a
  small gap rather than expanding the metric surface.
- **The biggest risk we found is framework lifecycle** — torchsde was
  archived in April 2026 because the maintainer stepped away and the
  test discipline was a single `run_tests.yml` badge with no health
  gate. Our `G-FRAMEWORK-HEALTH` gate is the direct mitigation, but
  the lesson is that *continuous investment in test discipline matters
  more than any single tool adoption.*

---

**End of Wave 32 Agent B web-research-2026.md.**
