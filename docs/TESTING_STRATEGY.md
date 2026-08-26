# Testing Strategy

This document describes how `flowa-multistep-reinference` is tested. It is
the single source of truth for *what* we test, *how* the layers fit
together, and *what bars* (mutation score, benchmark budgets, doc
verification) a change has to clear before it merges.

For the *what* the project is, see
[ARCHITECTURE.md](../ARCHITECTURE.md). For the *hostile cases* the
adversarial layer exists to catch, see
[DESIGN_BOUNDARY.md](../DESIGN_BOUNDARY.md). For current metrics, see
[FINAL_STATUS.md](../FINAL_STATUS.md).

---

## 1. Executive summary

The `adaptive_reflow/` package is a **typed-contracts framework** for
governed, multi-step flow-matching inference (molecules today; other
flow-matching families via `universal/`). Because the contract
layer *is* the product, the test suite is built around the contracts
themselves, not around empirical model behaviour.

The suite is **CPU-only by design**: the package is stdlib-only
Python 3.11 -- no `torch`, no `numpy`, no I/O -- so every test runs
in plain Python and CI does not need GPU runners. The full suite
runs locally in well under a second (475 tests in ~0.65 s), which
keeps mutation testing (`mutmut`) and property-based testing
(`hypothesis`) practical as part of the normal suite, not a
nightly-only concern. The kernels (`bounded_merge`,
`compute_channel_decision`, `evaluate_claim_gate`, `engine_round_loop`)
are microsecond-scale pure functions, benchmarked with
`pytest-benchmark` and gated on a 20% regression threshold (see §5).

---

## 2. Test layers

The suite has six cooperating layers. Each one catches a different
*class* of defect; together they give a high-confidence "the contracts
behave as documented" guarantee without any model in the loop.

### 2.1 Unit tests (one module per subpackage)

Per-module black-box tests over the public surface. See §4 for the
file inventory. Highlights:

- `tests/test_frame/` covers the round frame (`test_engine.py`,
  `test_merge.py`, `test_trace.py`).
- `tests/test_eval/` covers the evaluator contract (claim gate,
  calibration, protocol).
- `tests/test_policy/` covers archive, stratification, pruning.
- `tests/test_universal/` covers protocol-conformance of any
  `RestartMixer` / `EnvelopeCriterion` implementer, the `legacy/`
  deprecation warning, and the **AST-level guard** that nothing under
  `universal/` may import from `molecular/` (the load-bearing test
  for the universal / molecular split).
- `tests/test_diagnostics/test_ledger.py` -- observation-only ledger
  never influences `beta` / claim / prune.
- `tests/test_writer/test_registry.py` -- candidate registry init.
- `tests/test_adapters/test_toy_linear.py` -- synthetic in-tree
  adapter for protocol tests.
- `tests/test_tools/test_check_docs_against_code.py` -- the doc
  scanner's own self-test (see §2.7).
- `tests/test_contracts/` -- the typed-contracts core (dataclass,
  `NewType`, hash helpers).

### 2.2 Property-based tests (`tests/property/`)

`hypothesis`-driven exploration of the bounded input envelopes. All
strategies are defined in `tests/property/conftest.py` and are
deliberately *small* (`[0, 1]` envelopes, capped sample sizes) so the
budgets stay bounded.

- `test_bounded_merge_invariants.py` -- monotonicity, idempotence,
  commutativity over random bounded inputs.
- `test_claim_gate_invariants.py` -- gate truth-table closure.
- `test_mixer_invariants.py` -- restart mixer is RMS-preserving under
  arbitrary mixes.
- `test_validators_invariants.py` -- validator rejection paths.
- `test_golden_replay.py` -- *property* + *golden* combined: replay
  every recorded input fixture and re-derive its invariants.

### 2.3 Adversarial / hostile-case tests (`tests/test_adversarial/`)

One test per class of failure listed in `DESIGN_BOUNDARY.md` §3.
These are *fail-closed*: a regression in any of them means the
envelope / gate can be talked into an unsafe state.

| Test                                  | Hostile case (DESIGN_BOUNDARY section 3)            |
|---------------------------------------|------------------------------------------------------|
| `test_geometry_failure_closes_gate_and_emits_geometry_failure_audit_code` | high GNINA + PoseBusters geometry fail       |
| `test_monotonic_uncertainty_closes_gate_when_stability_collapses` | confident point estimate, unstable perturbation |
| `test_duplicate_evidence_does_not_inflate_transfer_score_mass` | two metric rows from one `bundle_id`              |
| `test_cross_round_stitch_rejects_bundle_at_validation`             | `source_round=k-3` mixed with `source_round=k`    |
| `test_source_revocation_closes_subsequent_gate`                     | `revoked=True` after registration                 |
| `test_proxy_only_evidence_cannot_satisfy_calibration_lower_bound`   | `feedback_mode == "proxy_only"`                  |

### 2.4 Golden tests (`tests/golden/`)

Recorded input / output pairs checked in as JSON under
`tests/golden/<kernel>/`. The replay path is
`tests/property/test_golden_replay.py`; a new golden is generated by
`tools/generate_golden.py` and committed alongside the change.

### 2.5 Benchmark tests (`tests/perf/`)

`pytest-benchmark` decorated kernel benchmarks. Output is captured
to `docs/benchmarks.json` (see `tools/bench/runner.py`) and compared
against `tools/bench/budgets.json` by `tools/bench/check_budgets.py`.
The bench is **microsecond-scale**, deterministic, and stdlib-only.

Current budgets (microseconds, p95):

| Kernel                         | p95 budget |
|--------------------------------|-----------:|
| `bounded_merge`                | 50         |
| `compute_channel_decision`     | 200        |
| `evaluate_claim_gate`          | 100        |
| `engine_round_loop`            | 1000       |

Regression threshold: **+20% vs the recorded baseline**.

### 2.6 Mutation tests (`mutmut`, nightly)

`mutmut` runs across the contracts + universal core in
`.github/workflows/mutation-nightly.yml`. Surviving mutants are
triaged the next morning; surviving mutants in `contracts/` or
`universal/` are bugs by definition. Mutation score targets are in §7.

### 2.7 Doc-drift scanner (`tools/check_docs_against_code.py`)

Stdlib-only scanner that walks the five root governance docs plus
`docs/*.md`, extracts every concrete claim (CamelCase /
SCREAMING_SNAKE_CASE identifiers inside python fenced code blocks,
`adaptive_reflow/...` path references, inline-backtick class names),
and verifies each against an AST-built symbol index. Exits non-zero
on drift. Wired into CI; run locally with `PYTHONPATH=. python
tools/check_docs_against_code.py`.

---

## 3. Tools

| Tool              | Role                                              | Where it's invoked        |
|-------------------|---------------------------------------------------|---------------------------|
| `pytest`          | Test runner, strict markers, `--strict-markers`   | every CI workflow         |
| `hypothesis`      | Property-based test generation                    | `tests/property/`         |
| `pytest-benchmark`| Microsecond kernel benchmarking                   | `tests/perf/`             |
| `mutmut`          | Mutation testing, nightly only                    | `mutation-nightly.yml`    |
| `ruff`            | Lint (E/W/F/I/B/UP/SIM)                           | `cpu-tests.yml`, `docs-validate.yml` |
| `mypy --strict`   | Type check on `contracts/` and `universal/`       | manual gate (see FINAL_STATUS §4) |
| `tools/check_docs_against_code.py` | Doc-drift scanner              | `docs-validate.yml`       |

Project markers (see `pyproject.toml [tool.pytest.ini_options]`):
`slow`, `benchmark`, `property`. `--strict-markers` ensures a typo in
a marker name fails collection rather than silently filtering.

---

## 4. Files at a glance

| Path                                                  | Layer        | Purpose                                        |
|-------------------------------------------------------|--------------|------------------------------------------------|
| `tests/conftest.py`                                   | bootstrap    | Resolves `adaptive_reflow` import path         |
| `tests/_utils/asserters.py`                           | helper       | Shared assertion helpers                       |
| `tests/test_contracts/`                               | unit         | Typed-contracts core                           |
| `tests/test_frame/` (3 files)                         | unit         | Round frame, `bounded_merge`, trace            |
| `tests/test_eval/` (3 files)                          | unit         | Evaluator contract                             |
| `tests/test_policy/` (2 files)                        | unit         | Policy layer                                   |
| `tests/test_diagnostics/test_ledger.py`               | unit         | Diagnostics ledger (observation only)          |
| `tests/test_writer/test_registry.py`                  | unit         | Candidate registry                             |
| `tests/test_universal/` (6 files)                     | unit         | Protocol conformance + split guard + legacy    |
| `tests/test_adapters/test_toy_linear.py`              | unit         | Synthetic adapter for protocol tests           |
| `tests/test_adversarial/test_hostile_cases.py`        | adversarial  | Six hostile cases (DESIGN_BOUNDARY §3)         |
| `tests/test_tools/test_check_docs_against_code.py`    | unit         | Doc-drift scanner self-test                    |
| `tests/property/conftest.py` + 5 test files           | property     | `hypothesis` strategies + invariants           |
| `tests/property/test_golden_replay.py`                | golden       | Replay every recorded golden                   |
| `tests/golden/<kernel>/`                              | golden       | Recorded input / output JSON                   |
| `tests/perf/test_kernel_benchmarks.py`                | benchmark    | Kernel benchmarks                              |
| `tests/perf/synthetic_driver.py`                      | benchmark    | Synthetic bench driver                         |

---

## 5. CI workflows

All workflows live under `.github/workflows/`.

| Workflow              | Trigger                          | What it gates                                       |
|-----------------------|----------------------------------|-----------------------------------------------------|
| `cpu-tests.yml`       | push to main, every PR           | ruff + pytest (not slow/benchmark) + doc scanner   |
| `docs-validate.yml`   | push to main, every PR           | ruff + doc scanner + full pytest                    |
| `bench-regression.yml`| weekly Mon 04:00 UTC + manual    | `pytest --benchmark-only` + `tools/bench/check_budgets.py` |
| `mutation-nightly.yml`| nightly 03:00 UTC + manual       | `bash tools/mutate/run_mutmut.sh`; report uploaded |

The nightly / weekly jobs do not block PRs, but their artifacts are
expected to be triaged -- a failing mutation report is a follow-up
ticket; a failing bench-regression is a same-day fix.

---

## 6. Adding new tests -- convention

1. **Pick the layer that matches the defect class**: unit for a wrong
   return value on a known input; property for *some* input the author
   hasn't thought of; adversarial for a hostile-bypass path; benchmark
   for a cost regression; doc-scanner for a rename the prose hasn't
   caught up with.
2. **Place the file under the right `tests/` subdirectory.** Property
   tests go under `tests/property/`, benches under `tests/perf/`, and
   (if deterministic) record a golden under `tests/golden/<kernel>/`
   via `tools/generate_golden.py`. Unit tests live under the
   directory that mirrors the package they cover (for example,
   `tests/test_frame/test_merge.py` covers `adaptive_reflow.frame.merge`).
3. **Use existing `_utils/asserters.py` helpers** for envelope / hash
   / gate equality rather than re-implementing the predicate.
4. **Mark slow tests with `@pytest.mark.slow`** so `cpu-tests.yml`
   (`-m "not slow and not benchmark"`) keeps the PR loop fast.
5. **Update [ARCHITECTURE.md](../ARCHITECTURE.md)** if the change
   introduces a new public symbol; the doc scanner will refuse to
   merge otherwise.
6. **Run the full gate locally before pushing**:
   `pytest tests/ && python tools/check_docs_against_code.py &&
   ruff check adaptive_reflow/ tests/`.
7. **Per-file lint ignores** in `pyproject.toml` already cover the
   intentional re-exports in `__init__.py` and forward references in
   `contracts/` / `universal/` / `molecular/`. Do not add new
   `# noqa` comments without a comment explaining *why*.

---

## 7. Mutation score targets

`mutmut` runs across the typed-contracts core. Targets:

| Scope                                | Target mutation score |
|--------------------------------------|----------------------:|
| `adaptive_reflow/contracts/`         | **>= 90%** killed     |
| `adaptive_reflow/universal/`         | **>= 85%** killed     |
| `adaptive_reflow/molecular/`         | >= 70% killed (best-effort) |
| `adaptive_reflow/frame/`             | >= 75% killed         |

A surviving mutant in `contracts/` or `universal/` is, by definition,
either (a) an equivalent mutant (no behaviour change possible) or
(b) a missing test. (a) is annotated in `tools/mutate/`; (b) is filed
as a follow-up and blocks the PR that introduced it. Nightly score
trend is captured in the `mutmut-report` artifact from
`.github/workflows/mutation-nightly.yml`; the current snapshot is in
[FINAL_STATUS.md](../FINAL_STATUS.md), and a sustained drop below
the targets above is a release blocker.
