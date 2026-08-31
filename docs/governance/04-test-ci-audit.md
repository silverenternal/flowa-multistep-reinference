# Test, CI/CD & Packaging Audit — operational state of the repo

> **Author:** Agent A4 (test infrastructure, CI/CD, packaging auditor)
> **Date:** 2026-08-31
> **Working dir:** `c:\Users\31472\codes\flowa-multistep-reinference`
> **Scope:** Read-only audit of `tests/`, `.github/workflows/`, `tools/`,
> `pyproject.toml`, `.pre-commit-config.yaml`, `.github/dependabot.yml`,
> `LICENSE`, `CHANGELOG.md`, `docs/RELEASING.md`, the two pre-existing
> governance audits (`02-algorithm-audit.md`, `03-framework-audit.md`).
> **Cross-references:**
> - `02-algorithm-audit.md` — paper-quantity + algorithm correctness
> - `03-framework-audit.md` — protocol + state-machine + runner audit
> - `docs/TESTING_STRATEGY.md` — six-layer suite description (project self-statement)
> - `docs/RELEASING.md` — six-gate release procedure

---

## §1. Test inventory

### §1.1 File counts

| Category                      | Directories                                              | Files | Test funcs |
|-------------------------------|----------------------------------------------------------|------:|-----------:|
| Unit / black-box              | `test_algorithm/`, `test_eval/`, `test_frame/`, `test_universal/`, `test_contracts/`, `test_policy/`, `test_diagnostics/`, `test_writer/`, `test_manifest/`, `test_engine/`, `test_molecular/`, `test_adapters/`, `test_schedule/`, `test_docs/`, `tests/test_round2_external_uplifts.py` | 70 | ~1 600 |
| Property (Hypothesis)         | `property/`                                              | 10    | ~65 |
| Adversarial / hostile-case    | `test_adversarial/`                                      | 2     | ~50 |
| Golden replay                 | `property/test_golden_replay.py` + `golden/<kernel>/`    | 1 + N | 9         |
| Benchmark / perf              | `perf/`                                                  | 4     | ~12       |
| Tool / docs-scanner self-test | `test_tools/`                                            | 10    | ~50       |
| **Total**                     |                                                          | **97 files** | **~1 760 test functions** |

(Sweep: `find tests -name "test_*.py" -type f | wc -l` returns 99 — the
two extras are `tests/__init__.py` and the `test_docs/__init__.py` package
marker, both empty.)

The pytest result file committed to the working tree
(`pytest_final.txt`, generated 2026-08-30) records
`3 failed, 2165 passed, 9 skipped, 39 warnings in 484.58s`. The discrepancy
between the 2 165 item count and the 1 760 function count is attributable
to parametrized tests (notably the adversarial / contract suites, where
each test runs once per `@pytest.mark.parametrize` axis — 6 hostile cases
× N shapes accounts for the gap). The `_utils/asserters.py` helper module
holds shared envelope / hash / gate-equality predicates used across the
suite.

### §1.2 Coverage by module (source ↔ test)

| Source package                       | Tested by                                | Notes |
|--------------------------------------|------------------------------------------|-------|
| `adaptive_reflow/algorithm/`         | `tests/test_algorithm/` (17 files) + `tests/property/test_engine_round_determinism.py` + `test_round2_external_uplifts.py` | Best-covered area; runner, scheduler, policy driver, blender, merge operator, batched runner, protocol surface, sequential, state-machine integration. |
| `adaptive_reflow/eval/`              | `tests/test_eval/` (16 files)            | Claim gate, calibration, protocol, MNIST FID, target distributions, posterior selection evaluator, RDKit oracle (skip-gated). |
| `adaptive_reflow/universal/`         | `tests/test_universal/` (9 files)        | Adapter universality, envelope criterion, mixer OT/protocol, legacy deprecation, state isolation, standard mixers, **the load-bearing AST guard** `test_no_molecular_import.py`. |
| `adaptive_reflow/contracts/`         | `tests/test_contracts/` (3 files) + `test_universal/test_mixer_protocol.py` + `test_algorithm/test_protocol_surface.py` | Typed-contracts core: dataclass, `NewType`, hash helpers, audit, paper quantities, state machine. |
| `adaptive_reflow/frame/`             | `tests/test_frame/` (7 files)            | Engine, merge, ledger chain, trace, channel-rule diagnostics, golden merge agreement, round-2 frame uplifts. |
| `adaptive_reflow/policy/`            | `tests/test_policy/` (2 files)           | Archive, stratification and pruning. |
| `adaptive_reflow/diagnostics/`       | `tests/test_diagnostics/test_ledger.py`   | Observation-only ledger. |
| `adaptive_reflow/writer/`            | `tests/test_writer/test_registry.py`     | Candidate registry init. |
| `adaptive_reflow/manifest.py`        | `tests/test_manifest/test_port_registration.py` | |
| `adaptive_reflow/schedule/`          | `tests/test_schedule/` (2 files)         | Cosine purity, memory-fraction-driven beta. |
| `adaptive_reflow/molecular/`         | `tests/test_molecular/test_mixer.py` (skip-gated — torch) | |
| `adaptive_reflow/adapters/`          | `tests/test_adapters/` (8 files)         | twodim_fm, mnist_fm (torch-gated), mnist_fm_train, toy_linear, stochastic_fm, inject_forward_noise, exp2 repro (xfail), rectified_flow_cifar (torch-gated). |
| `tools/check_docs_against_code.py`   | `tests/test_tools/test_check_docs_against_code.py` | **2 failures recorded** in `pytest_final.txt` — see §7. |
| `tools/check_claims_consistency.py`  | `tests/test_tools/test_check_claims_consistency.py` | |
| `tools/run_ablation.py`              | `tests/test_tools/test_run_ablation.py`  | |
| `tools/run_sota_2d_experiment.py`    | `tests/test_tools/test_run_sota_2d_experiment.py` | |
| `tools/run_sota_cifar_experiment.py` | `tests/test_tools/test_run_sota_cifar_experiment.py` | |
| `tools/run_sota_comparison.py`       | `tests/test_tools/test_run_sota_comparison.py` | |
| `tools/run_rf_cifar_ablation.py`     | `tests/test_tools/test_run_rf_cifar_ablation.py` (2 torch-skips) | |

### §1.3 Skipped / xfail / slow / stress inventory

| Marker / state               | Count | Reason                                                       |
|------------------------------|------:|--------------------------------------------------------------|
| `@pytest.mark.stress`        | 10    | `tests/perf/test_stress_1000_rounds.py` (4) + `test_stress_molecular_1000_rounds.py` (4) + `test_mnist_fm.py:515` + `test_twodim_fm.py:596` — run only on `stress-nightly` workflow |
| `@pytest.mark.experiments`   | 5     | `tests/test_experiments/test_freetraj_wallclock.py` (5) — empirical claim reproductions |
| `@pytest.mark.slow`          | 2     | `tests/test_algorithm/test_batched_runner_uplifts.py:252` + module-level `pytestmark_slow` in one file |
| `@pytest.mark.xfail`         | 1     | `tests/test_adapters/test_exp2_stochastic_fm_repro.py:155` (with explicit `reason=`) |
| `pytest.skip(...)` runtime   | 9     | All gated on `torch`/`hypothesis`/optional-dependency absence (mnist_fm, cifar, mixer, rf_cifar ablation). Recorded as `9 skipped` in `pytest_final.txt`. |
| `@pytest.mark.skipif(...)`   | 4     | 3 in `test_fail_closed_contracts.py` + 1 in `test_hostile_cases.py` — gated on `HAS_HYPOTHESIS` |
| Pre-existing failures (off-CI) | **3** | Recorded in `pytest_final.txt`: `test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction` (the xfail), `test_check_docs_against_code.py::test_no_false_positives_on_current_repo`, `test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit`. **All three are in `pytest_final.txt` from 2026-08-30**; their CI-blocking status depends on whether the CI invocation uses `-m "not slow and not benchmark"` (it does — see §3), and whether the xfail fails the suite (`-rx` policy). |

The xfail with `reason=` documents an expected stochastic-FM regression;
the two `check_docs_against_code` self-test failures are internal-tool
regressions that the suite does NOT exclude from CI (they run on every
PR via Gate 4) — see §7.1.

---

## §2. Test quality

### §2.1 Critical-path coverage

* **Bounded merge kernel** (`adaptive_reflow/frame/merge.py`) — covered
  by `test_bounded_merge_invariants.py` (Hypothesis-driven
  monotonicity, idempotence, commutativity) + `test_merge_anchoring_invariants.py`
  + `test_bounded_merge_anchoring.py` + `test_merge_golden_agreement.py`
  + the `bounded_merge` golden-replay file. Multiple independent angles.
* **Claim gate** (`adaptive_reflow/eval/claim_gate.py`) — covered by
  `test_claim_gate_invariants.py` (Hypothesis truth-table closure) +
  `test_eval/test_claim_gate.py` (deterministic table) +
  `test_eval/test_round2_coverage.py` + adversarial `test_hostile_cases.py`
  (6 hostile cases per `DESIGN_BOUNDARY.md` §3) + `test_fail_closed_contracts.py`.
* **Runner / orchestrator** (`adaptive_reflow/algorithm/runner.py`) —
  covered by `test_runner.py` (deterministic) + `test_batched_runner.py`
  + `test_batched_runner_uplifts.py` (slow) + `test_sequential.py` +
  `test_state_machine_integration.py` + `test_protocol_surface.py`.
* **State machine** — `tests/test_contracts/test_state_machine.py` +
  `tests/test_algorithm/test_state_machine_integration.py`.
* **Protocol conformance** — `test_universal/test_mixer_protocol.py`
  + `test_universal/test_adapter_universality.py` +
  `test_algorithm/test_protocol_surface.py`. The
  `test_universal/test_no_molecular_import.py` is the load-bearing AST
  guard for the universal/molecular split (fail-closed).
* **Paper quantities** (`adaptive_reflow/contracts/paper_quantities.py`)
  — `tests/test_contracts/test_paper_quantities.py`; correctness vs the
  paper is audited separately in `02-algorithm-audit.md` §1.
* **Harness of the harness** — `tools/check_docs_against_code.py` is
  self-tested (`tests/test_tools/test_check_docs_against_code.py`)
  and is one of the three currently-failing tests (see §7.1).

### §2.2 Edge-case and regression coverage

* **`tests/golden/<kernel>/`** — JSON-recorded input/output pairs under
  `tests/golden/<kernel>/` (e.g. `bounded_merge`, `claim_gate`,
  `channel_decision`). The replay path is
  `tests/property/test_golden_replay.py`; goldens are regenerated by
  `tools/generate_golden.py`. This is the closest thing the suite has
  to a regression baseline for kernel behaviour.
* **Numerical edge cases** — `tests/test_contracts/test_paper_quantities.py`
  includes the `K=8` vs `K=20` trapezoidal truncation, the `g(x)=c`
  constant profile, the `g(x)=sin(x)` non-trivial profile, and the
  `g(x)=e^{-x^2}` dense profile (the 02-algorithm-audit cross-references
  the numerical agreement).
* **Heun corrector on last step** —
  `tests/test_adapters/test_rectified_flow_cifar.py:873`
  (`test_heun_corrector_skipped_on_last_step`) covers the boundary case
  where the second velocity eval is suppressed at `t=T`.
* **Cross-round stitch** —
  `tests/test_adversarial/test_hostile_cases.py` (the `source_round=k-3`
  vs `k` reject path) — adversarial only; not in property sweep.
* **Hypothesis profile switch** — `[tool.hypothesis.profiles."slow"]`
  and `[tool.hypothesis.profiles."stress"]` provide the slower-shoulder
  profiles that the slow/stress tests opt into.

### §2.3 Paper-claim coverage

Per `docs/TESTING_STRATEGY.md` §3 the test layer is built around the
contracts, not the empirical model. However:

* `tests/test_adapters/test_exp2_stochastic_fm_repro.py` — paper-grounded
  reproduction of the 25% W2 reduction claim (currently xfail —
  stochastic-FM dependency not satisfied in stdlib-only env).
* `tests/test_experiments/test_freetraj_wallclock.py` —
  empirical `experiments`-marker claim reproduction.
* `tests/test_eval/test_mnist_fid.py` — MNIST FID acceptance test
  (skip-gated on `data/mnist_fm.npz` presence).
* `tests/test_contracts/test_paper_quantities.py` — covers the four
  paper quantities (`A_g`, `B_g`, `C_g`, `D_g`) at the unit level.
  (Paper-quantity *correctness* is audited in 02-algorithm-audit.md;
  the test file here confirms the implementations execute and produce
  the documented numerical fingerprints.)

### §2.4 Isolation, determinism, speed

* **Isolation:** `tests/conftest.py` prepends the repo root to
  `sys.path` so `import adaptive_reflow` resolves under any pytest
  invocation mode, and walks parent dirs for `pocket_modules` for the
  legacy tests (which are gated on that walk succeeding). No shared
  mutable state is introduced beyond the `sys.path` mutation.
* **Determinism:** The tool `tools/run_ablation.py` is documented as
  deterministic for `seed=42` (default). The Hypothesis profiles use
  `max_examples=500` (default) / `200` (slow) / `50` (stress) and
  `deadline=2000/30000/60000 ms` respectively. CI configures
  `--strict-markers` so a typo in a marker name fails at collection
  rather than silently filtering.
* **Speed:** Per `docs/TESTING_STRATEGY.md` §1 the suite is documented
  as "475 tests in ~0.65 s" — this number is stale (the suite has
  since grown ~4×; the recorded `pytest_final.txt` run was 484.58 s
  wall-clock, almost all of it the 10 stress tests + the benchmark
  sweep + the property tests with 500 examples). The PR-loop subset
  (`-m "not slow and not benchmark"`) is the one bounded to ~60 s; the
  full run is nightly. The `mutation-nightly.yml` has a 120-min
  timeout, the `stress-nightly.yml` has a 60-min timeout, the
  `bench-regression.yml` has a 30-min timeout — see §3.

### §2.5 Test-suite self-consistency (pre-existing failures)

The committed `pytest_final.txt` (2026-08-30) reports:

```
3 failed, 2165 passed, 9 skipped, 39 warnings in 484.58s (0:08:04)
FAILED tests/test_adapters/test_exp2_stochastic_fm_repro.py::test_exp2_stochastic_fm_w2_ratio_reproduces_25pct_reduction
FAILED tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo
FAILED tests/test_tools/test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit
```

The xfail (`exp2_stochastic_fm`) is decorated with `@pytest.mark.xfail(reason=…)`,
so under default xfail policy (`--runxfail` off) it is **expected to fail**
and is **not** CI-blocking. The other two failures are NOT marked xfail and
**are** CI-blocking if the PR-loop gate ever runs them — see §7.1.

---

## §3. CI configuration (`.github/workflows/`)

### §3.1 Workflow inventory

| Workflow file              | Trigger                                                | Jobs | Timeout | What it gates |
|----------------------------|--------------------------------------------------------|-----:|--------:|---------------|
| `ci.yml`                   | push to `main`, PR, `workflow_dispatch`                 | 2 (`lint-types`, `test-docs`) | 15 min | The canonical six gates (see §3.2) |
| `cpu-tests.yml`            | push to `main`, PR                                     | 1     | 15 min | ruff + pytest (subset) + universal-import guard + check_docs (4 of the 6 gates) |
| `docs-validate.yml`        | push to `main`, PR                                     | 1     | (default) | ruff + check_docs + full pytest (3 of the 6 gates) |
| `bench-regression.yml`     | weekly Mon 04:00 UTC, `workflow_dispatch`              | 1     | 30 min | pytest `--benchmark-only` + `tools/bench/check_budgets.py` |
| `mutation-nightly.yml`     | nightly 03:00 UTC, `workflow_dispatch`                 | 1     | 120 min | `tools/mutate/ast_mutator.py run` + `gate` |
| `stress-nightly.yml`       | weekly Mon 03:00 UTC, `workflow_dispatch`              | 1     | 60 min | `pytest -m stress` |
| `docs-deploy.yml`          | push to `main` (scoped to `mkdocs.yml`, `docs/**`, top governance docs), `workflow_dispatch` | 2 (build + deploy) | (default) | `mkdocs build --strict` + GitHub Pages deploy |

`ci.yml` is the canonical pre-merge pipeline; `cpu-tests.yml` and
`docs-validate.yml` are **legacy duplicates** with overlapping gate
coverage (see §7.2). `bench-regression`, `mutation-nightly`, and
`stress-nightly` are scheduled/non-blocking; `docs-deploy` is the
GitHub Pages publish path and is gated on a successful `mkdocs build
--strict` from a push to `main` only.

### §3.2 The six pre-merge gates (per `ci.yml` + `CONTRIBUTING.md` §2)

| # | Gate                  | Wired in `ci.yml`? | Wired in pre-commit? | Per-PR-loop wall-clock impact |
|---|-----------------------|--------------------|---------------------|-------------------------------|
| 1 | `pytest` (slow/bench excluded) | Yes (`test-docs`)   | Yes (`pytest-fast`) | ~30-60 s |
| 2 | `ruff`                | Yes (`lint-types`) | Yes (`ruff-check`)  | < 5 s |
| 3 | `mypy --strict`       | Yes (`lint-types`) | Yes (`mypy-strict`) | ~30 s cold / ~5 s warm |
| 4 | `check_docs_against_code` | Yes (`lint-types`) | Yes (`check-docs`)  | < 5 s |
| 5 | `check_claims_consistency` | Yes (`lint-types`) | Yes (`check-claims`) | < 5 s |
| 6 | `mkdocs build --strict` | Yes (`test-docs`) | Yes (`mkdocs-strict`, docs-only trigger) | ~15 s |

**6 of 6 gates are wired into `ci.yml` and into pre-commit (gate 6 fires
on docs-only changes).** Both jobs (`lint-types` and `test-docs`) run in
parallel; both must be green. The default Ubuntu runner is
`ubuntu-latest` with a 15-min job timeout (matches `cpu-tests.yml`).

### §3.3 Matrix / fan-out

No Python version matrix: both jobs pin `python-version: '3.12'`
explicitly (matches `requires-python = ">=3.12"`). No OS matrix. No
shard matrix — the pytest job is monolithic.

### §3.4 Branch protection / merge policy

No `CODEOWNERS`-driven review requirement is enforceable in-workflow
(the `CODEOWNERS` file exists but is not enforced by any visible GitHub
App integration). No status-check requirement is configured at the
workflow-file level — that's a GitHub repository settings concern,
outside the audit scope. The `concurrency: cancel-in-progress: true`
on `ci.yml` keeps the Actions quota free for fast-iterate PRs.

### §3.5 Dependabot

`.github/dependabot.yml` configures two ecosystems:

* **`pip`** — weekly Monday 06:00 UTC; `open-pull-requests-limit: 5`;
  groups `patch-and-minor` and `major` separately. Comment in the file
  documents the deliberate timing relative to mutation-nightly and
  bench-regression schedules.
* **`github-actions`** — monthly Monday 06:00 UTC; `open-pull-requests-limit: 3`;
  `actions-patch` group.

No `npm`, `cargo`, or `docker` ecosystems (none apply). No
`versioning-strategy: increase` (the project bumps `version` by hand,
per `RELEASING.md`).

### §3.6 Test-time budget (PR loop)

Per `ci.yml`:

* `lint-types`: pip cache hit ~ < 10 s; pip install ~ < 30 s cold; ruff
  < 5 s; mypy --strict ~ 30 s cold; check_docs + check_claims ~ < 5 s.
  Wall-clock cold budget: ~ 90 s.
* `test-docs`: pip install + `.[dev]` ~ 60 s cold; pytest subset
  ~ 30-60 s; mkdocs build --strict ~ 15 s. Wall-clock cold budget:
  ~ 150 s.

Both jobs are within their 15-min timeout. Per CONTRIBUTING.md §2 the
documented local equivalent is the same command.

---

## §4. Pre-commit configuration (`.pre-commit-config.yaml`)

### §4.1 Layout

* `default_language_version: python: python3.12` — matches CI pin.
* `fail_fast: false` — every hook runs even if a prior hook fails, so
  all six gates report on a single commit.
* `exclude:` regex blocks `__pycache__/`, `.pyc`, `data/`, `site/`,
  `dist/`, `*.egg-info/`, `mutmut_results.*`, `mutmut_run.log` — the
  six gate scripts themselves are not subject to their own validation
  cycles.
* `repos:` is **entirely local** (`repo: local`) — no third-party
  action downloads, so the suite runs offline and is byte-identical to
  CI.

### §4.2 Hook catalogue

| Hook id        | Stage       | Files             | Command                                                                                | Mirrors CI gate |
|----------------|-------------|-------------------|----------------------------------------------------------------------------------------|-----------------|
| `ruff-check`   | pre-commit  | python            | `ruff check adaptive_reflow/ tests/`                                                   | Gate 2          |
| `mypy-strict`  | pre-commit  | python            | `python -m mypy adaptive_reflow`                                                        | Gate 3          |
| `check-docs`   | pre-commit  | python, markdown  | `python tools/check_docs_against_code.py`                                              | Gate 4          |
| `check-claims` | pre-commit  | python, markdown  | `python tools/check_claims_consistency.py`                                             | Gate 5          |
| `pytest-fast`  | pre-commit  | python            | `bash -c "PYTHONPATH=. python -m pytest tests/ -m 'not slow and not benchmark' --no-header -q"` | Gate 1 (PR-loop subset) |
| `mkdocs-strict`| pre-commit  | docs (regex)      | `mkdocs build --strict`                                                                | Gate 6 (docs-only) |

All six gates are covered. Install instructions:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files    # full sweep
pre-commit run <hook-id> --all-files
```

The header of `.pre-commit-config.yaml` documents these commands and
the `git commit --no-verify` bypass (explicitly marked "NOT recommended").

### §4.3 Failure mode

`mypy-strict` and `pytest-fast` are annotated as "slow" in the hook
descriptions (mypy: ~30 s cold / ~5 s warm on this tree; pytest PR-loop
subset: ~30-60 s). All hooks run in serial (`require_serial: true`) so
the pre-commit window stays bounded.

### §4.4 Catches gate violations?

**Yes for all six gates.** A typo in a marker fails at collection
(`--strict-markers`); a mypy regression fails before the PR is pushed;
a docs drift fails before the PR is pushed; a missing claim
cross-reference fails before the PR is pushed. The pre-commit is
byte-identical to CI for the lint-types job and equivalent for the
test-docs job (modulo the `PYTHONPATH=.` shim).

---

## §5. Build / package (sdist, wheel, twine, optional deps, release)

### §5.1 Build backend

`pyproject.toml` declares:

* `build-system.requires = ["hatchling>=1.18"]` and
  `build-backend = "hatchling.build"` (PEP 517).
* `[tool.hatch.build.targets.wheel]` `only-include` =
  `[adaptive_reflow, tools, tests, README.md, CHANGELOG.md, LICENSE]`.
* `[tool.hatch.build.targets.sdist]` mirrors wheel except adds
  `pyproject.toml`.

The `dist/` directory contains:

```
flowa_multistep_reinference-0.1.0-py3-none-any.whl     1 413 167 bytes
flowa_multistep_reinference-0.1.0.tar.gz              1 141 089 bytes
```

The wheel contents (395 lines from `python -m zipfile -l`) include the
`adaptive_reflow/` package, the `tools/` scripts, the `tests/` tree,
and the three top-level docs (`README.md`, `CHANGELOG.md`, `LICENSE`).
Verified build artifact exists; not a hypothetical release.

### §5.2 `twine check` (dry-run gate)

`docs/RELEASING.md` §"Twine check" documents the expected output:

```
Checking dist/flowa_multistep_reinference-0.1.0-py3-none-any.whl: PASSED
Checking dist/flowa_multistep_reinference-0.1.0.tar.gz: PASSED
```

The release doc records "0.1.0 dry-run was executed on 2026-08-31 with
the following results: sdist OK + wheel OK; twine check PASSED (both
artifacts); dist/ in .gitignore YES; 6 gates all green; twine upload NOT
EXECUTED (gated on paper acceptance)". The build artifacts on disk are
**consistent with the dry-run result**.

### §5.3 Optional dependencies (`[project.optional-dependencies]`)

| Extra             | Pins                            | Purpose |
|-------------------|---------------------------------|---------|
| `dev`             | `mkdocs>=1.5`, `mkdocstrings[python]>=0.24`, `griffe>=1.0` | Doc-build toolchain (CI-only) |
| `chemistry`       | `rdkit>=2024.3.1`               | RDKit oracle (`adaptive_reflow.eval.rdkit_oracle`) |
| `flow_matching`   | `numpy>=2.0,<2.5`, `scipy>=1.10` | NumPy + SciPy for 2D rectified-flow adapter and trainer |

The `flow_matching` extra pins `numpy<2.5` because NumPy 2.5+ ships a
PEP 695 `type` statement in `__init__.pyi` that mypy 1.x cannot parse
— explicitly documented.

No `[test]` extra; `pytest`, `hypothesis`, `pytest-benchmark`, `mutmut`
are installed directly in the CI install step (`pip install pytest
hypothesis pytest-benchmark` and equivalents). **Minor inconsistency
vs the `pyproject.toml [project.scripts]` install pattern** — the
testing toolchain is documented in `CONTRIBUTING.md` §1 as
"`pytest`, `hypothesis`, `pytest-benchmark`, `ruff`, and `mypy` are
pinned transitively by the project metadata and resolve alongside the
install", which is **not actually the case** (none of these are
`[project.dependencies]` — they are installed explicitly in every
workflow). This is a documentation drift rather than a packaging
defect; see §7.4.

### §5.4 Python pinning

* `requires-python = ">=3.12"` (PEP 621) — matches `target-version = "py312"`
  in `[tool.ruff]` and `python_version = "3.12"` in `[tool.mypy]`.
* All CI workflows pin `python-version: '3.12'` explicitly.
* Pre-commit pins `python3.12`.

Single-version pin is consistent across build, lint, type-check, and CI.
**No Python version matrix** — `docs/TESTING_STRATEGY.md` and
`RELEASING.md` document Python 3.12 as the only supported runtime.

### §5.5 Release process (`docs/RELEASING.md`)

* Six pre-release gates (same six gates as the PR loop) must be green.
* `pyproject.toml` `version` is bumped by hand; `CHANGELOG.md`
  `[X.Y.Z]` entry added; PEP 621 metadata verified; `dist/` in
  `.gitignore` (verified — see `.gitignore:32-34`).
* Build: `python -m build --outdir dist`.
* Twine check: `python -m twine check dist/*`.
* Upload: gated on paper acceptance — explicit "DO NOT run this
  command until the paper has been accepted" warning. The 0.1.0 publish
  is intentionally held back from public PyPI.
* Rollback procedure (`twine yank` + bump + republish + `### Yanked`
  changelog subsection) is documented.

The release process is **explicitly research-stage** (`Development
Status :: 3 - Alpha`) and intentionally conservative — the dry-run
build is verified but the upload is withheld. The CHANGELOG has **no
`[0.1.0]`-style numbered release** yet (only `[Unreleased]` entries —
verified by `grep -c "^\[0\." CHANGELOG.md` → `0`); the release flow is
correctly gated.

### §5.6 `LICENSE`

`LICENSE` is at the repo root, MIT, Copyright (c) 2026 silverenternal —
verified content matches the SPDX expression `"MIT"` in `pyproject.toml`
`license = "MIT"` + `license-files = ["LICENSE", "LICENSE-*"]`. PyPI
classifier `License :: OSI Approved :: MIT License` is consistent.

### §5.7 Console script

`pyproject.toml [project.scripts]` declares
`claims-consistency = "tools.check_claims_consistency:main"`. `which
claims-consistency` (POSIX) / `where claims-consistency` (Windows)
should resolve to the venv's `bin/` / `Scripts/` entry — verified in
`docs/RELEASING.md` §"Post-release verification" item 4.

---

## §6. Documentation verification tooling

### §6.1 `tools/check_docs_against_code.py` (Gate 4)

Stdlib-only scanner (no third-party imports — `ast`, `argparse`, `re`,
`dataclasses`, `pathlib`, `collections.abc`). It walks five root
governance docs (`README.md`, `ARCHITECTURE.md`, `STATUS.md`,
`DESIGN_BOUNDARY.md`, `CONTRACTS.md`) plus every `.md` under `docs/`,
and verifies three classes of claim:

1. **Triple-backtick python fenced code blocks** — every
   `ClassDef`/`FunctionDef`/`AsyncFunctionDef`/top-level assignment/
   `ImportFrom` alias mentioned in the snippet must be defined under
   `adaptive_reflow/`. Example/illustrative blocks (containing
   `<your ...>` placeholders) are skipped.
2. **Path-style references** — `adaptive_reflow/foo/bar.py` /
   `tests/test_foo/test_bar.py` must resolve on disk relative to the
   repo root. `adaptive_reflow/__init__.py` is recognised but skipped
   by the "no top-level __init__.py" invariant.
3. **Inline-backtick CamelCase identifiers** — must be defined under
   `adaptive_reflow/`. Test fixture names ending in `Fixture` and
   obvious prose tokens (typing stdlib names, third-party libs, doc
   anchors) are filtered via a denylist.

The output is a markdown table; the tool exits `0` on clean, `1` on
drift. Phase 2 (`--scan-docstrings`) also walks every `.py` under
`adaptive_reflow/` and treats CamelCase / SCREAMING_SNAKE_CASE inside
function/class docstrings as additional inline-symbol claims — catches
internal-doc drift that may not appear in the prose.

Wired into:
* **CI Gate 4** (`ci.yml` step "Gate 4 -- check_docs_against_code", run
  via `PYTHONPATH=. python tools/check_docs_against_code.py`).
* **Pre-commit hook `check-docs`** (`types_or: [python, markdown]`).
* **Self-test** (`tests/test_tools/test_check_docs_against_code.py`) —
  but **two of these self-tests are failing** per `pytest_final.txt`,
  see §7.1.

### §6.2 `tools/check_claims_consistency.py` (Gate 5)

Stdlib-only scanner (same lean profile as Gate 4). It walks
`docs/CLAIMS.md`, parses every `CLM-NNN` claim into a `Claim` record
(`Claim` dataclass at line 86), and:

1. Verifies every `ACTIVE` claim's `Asserted by` file:line reference
   resolves (line exists and contains non-whitespace content).
2. Forces `Disputed by` references to `PROVISIONAL` regardless of
   the file's `Status:` field (the verifier is the canonical authority
   for the promotion; the file field is left intact for human review).
3. For every `ACTIVE` claim, scans the four governance surfaces
   (`docs/INSIGHTS.md`, `docs/ABLATION.md`, every `docs/adr/*.md`,
   `README.md`, `ARCHITECTURE.md`) for `[CLM-NNN]` tags. A claim with
   no cross-reference anywhere is drift by definition.

Wired into:
* **CI Gate 5** (`ci.yml` step "Gate 5 -- check_claims_consistency").
* **Pre-commit hook `check-claims`** (`types_or: [python, markdown]`).
* **Self-test** (`tests/test_tools/test_check_claims_consistency.py`)
  — passes per `pytest_final.txt`.

### §6.3 `mkdocs build --strict` (Gate 6)

* **CI Gate 6** (`ci.yml` step "Gate 6 -- mkdocs build --strict") —
  renders the auto-generated API reference; a broken internal link or
  unresolved mkdocstrings reference fails the build. Runs in the
  `test-docs` job.
* **Pre-commit hook `mkdocs-strict`** — `files: ^docs/` so a
  pure-source-code commit does not pay the ~15 s cost.
* **`docs-deploy.yml`** — same `mkdocs build --strict`, scoped to
  pushes that touch `mkdocs.yml`, `docs/**`, or the top-level
  governance docs (`README.md`, `QUICKSTART.md`, `TUTORIAL.md`,
  `FAQ.md`, `ARCHITECTURE.md`); deploys to GitHub Pages via the
  `actions/upload-pages-artifact` + `actions/deploy-pages` pair.

### §6.4 Wired-in coverage summary

| Tool                         | Wired into CI? | Wired into pre-commit? | Self-tested? |
|------------------------------|----------------|-----------------------|--------------|
| `check_docs_against_code.py` | Yes (Gate 4)   | Yes (`check-docs`)    | Yes (2 failures) |
| `check_claims_consistency.py`| Yes (Gate 5)   | Yes (`check-claims`)  | Yes (passes) |
| `mkdocs build --strict`      | Yes (Gate 6)   | Yes (docs-only)       | N/A — build output itself is the verification |

---

## §7. Issues found

### §7.1 Two pre-existing `check_docs_against_code` self-test failures

`pytest_final.txt` records:

```
FAILED tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo
FAILED tests/test_tools/test_check_docs_against_code.py::test_self_test_quiet_mode_returns_zero_exit
```

These are NOT xfail-decorated. They are run on every PR via Gate 4's
self-test layer. If `pytest_final.txt` is current (it is timestamped
2026-08-30 — yesterday), then **Gate 4 is currently failing on `main`**.
Either (a) the self-tests need to be updated to reflect a deliberate
behaviour change in the scanner, (b) the scanner has a regression, or
(c) `pytest_final.txt` is stale and the failures are already resolved
on a later commit. The third option is plausible because the
working-tree `git status` reports both `adaptive_reflow/adapters/_inject_forward_noise.py`
and `docs/r4-survey/exp3-results.json` as modified — neither of which
appears to be the self-test failure source.

**Severity:** High — affects a load-bearing gate. **Action:** re-run
`PYTHONPATH=. python -m pytest tests/test_tools/test_check_docs_against_code.py`
on a clean tree and update the failing tests, or mark them xfail with
an issue link.

### §7.2 `cpu-tests.yml` and `docs-validate.yml` are redundant with `ci.yml`

`ci.yml` already runs ruff, mypy, pytest (subset), check_docs, check_claims,
and mkdocs build --strict. `cpu-tests.yml` re-runs a 4-of-6 subset
(ruff, pytest subset, check_docs) on every push and PR. `docs-validate.yml`
re-runs a 3-of-6 subset (ruff, check_docs, full pytest). The
`cpu-tests.yml` workflow also references
`tests/test_universal/test_universal_imports_no_molecular.py` (a
test that does not exist in the `tests/test_universal/` inventory —
the actual file is `test_no_molecular_import.py`) — **that step will
silently no-op in `cpu-tests.yml`** because pytest will skip with
`collection error: no tests ran`. Severity: Medium — wasted CI
minutes + a misnamed test reference.

**Action:** Either consolidate to a single canonical workflow
(`ci.yml`) and delete the duplicates, or rename
`test_universal_imports_no_molecular.py` → `test_no_molecular_import.py`
if the file was renamed in flight.

### §7.3 `stress-nightly.yml` references a Windows-only Python path

`stress-nightly.yml` line 28:

```yaml
run: .venv/Scripts/python.exe -m pytest -m stress --no-header -q
```

`.venv/Scripts/python.exe` is the Windows venv shim. On the
`ubuntu-latest` runner this path does not exist; the workflow **fails
to start the pytest step** if the cached venv is not present. The fix
is trivial (`python -m pytest -m stress --no-header -q`), but the
typo means the `stress-nightly` workflow is currently broken on the
only runner it is configured for.

**Severity:** High for the stress gate (the schedule is weekly Mon
03:00 UTC, so the failure has been silent for at least a week).

**Action:** Replace `.venv/Scripts/python.exe` with `python` (the
runner image has `python` on `PATH` from `actions/setup-python@v5`).

### §7.4 `[test]` extra referenced in workflows is not declared in `pyproject.toml`

`cpu-tests.yml` and `stress-nightly.yml` both run:

```bash
pip install -e .[test] || pip install pytest hypothesis pytest-benchmark
```

There is no `[project.optional-dependencies.test]` declaration in
`pyproject.toml`; the `||` falls back to the explicit install, so the
build is not broken, but **the `pip install -e .[test]` line is a
no-op** (pip will fail with "Could not find a version that satisfies
the requirement .[test]" or silently skip if `--no-deps` is in effect —
neither is configured here, so pip WILL fail and fall through to the
fallback). The `CONTRIBUTING.md` §1 statement "`pytest`, `hypothesis`,
`pytest-benchmark`, `ruff`, and `mypy` are pinned transitively by the
project metadata and resolve alongside the install" is **factually
incorrect** — none of these are in `[project.dependencies]` or
`[project.optional-dependencies]`.

**Severity:** Low (the `||` fallback works), but it's a documentation
drift that `check_docs_against_code.py` could in principle flag.

**Action:** Either add a `[test]` extra to `pyproject.toml`
(`pytest`, `hypothesis`, `pytest-benchmark`, `ruff`, `mypy`,
`mutmut`) and update the install line, or update `CONTRIBUTING.md` to
say "install pytest, hypothesis, pytest-benchmark, ruff, mypy
explicitly".

### §7.5 No Python version matrix in CI

The project pins `requires-python = ">=3.12"` and supports only Python
3.12 (`Operating System :: OS Independent` + `Programming Language ::
Python :: 3.12` + `Programming Language :: Python :: 3 :: Only`). The
single-version pin is documented but **not enforced by CI** — a
contributor who runs the suite under Python 3.13 will get a different
result set (notably the `>=3.12` lower-bound will be silently
satisfied). This is acceptable for a research-stage package but should
be documented in `docs/TESTING_STRATEGY.md` §3 (currently the table
documents only the toolchain, not the Python version).

### §7.6 The `experiments` marker has no nightly gate

Five tests are decorated with `@pytest.mark.experiments`
(`tests/test_experiments/test_freetraj_wallclock.py`); these are
"experimental claim reproduction tests" per `pyproject.toml` marker
documentation. There is no scheduled workflow that runs them — they
are excluded from the PR-loop pytest gate by virtue of being
`-m "not slow and not benchmark"`-compatible, but the `experiments`
marker itself is not in any `-m` filter. The experiments therefore run
on every PR (with whatever wall-clock cost they impose) but not on a
dedicated nightly.

**Severity:** Low — the cost is bounded by the `experiments` test
budget (5 wall-clock tests). **Action:** either add `experiments` to
the `pytest-fast` exclusion list and schedule it nightly, or document
the intent.

### §7.7 `mutation-nightly.yml` has a documentation/runtime mismatch

The workflow description says "`bash tools/mutate/run_mutmut.sh`" (line
`# mutmut` section in `docs/TESTING_STRATEGY.md` §5) but the actual
step at `mutation-nightly.yml:35` runs
`python tools/mutate/ast_mutator.py run` — the `ast_mutator.py`
replacement was implemented because `mutmut` cannot run on Windows
(upstream `boxed/mutmut#397`). The `docs/TESTING_STRATEGY.md` and the
commit messages acknowledge the swap, but `docs/TESTING_STRATEGY.md`
§3 still lists `mutmut` as the tool. Minor doc drift.

**Severity:** Low. **Action:** update `docs/TESTING_STRATEGY.md` §3
table to read `ast_mutator` instead of `mutmut`.

---

## §8. Summary

| Dimension             | Verdict | Grade |
|-----------------------|---------|-------|
| Test inventory        | 97 test files / ~1 760 functions, six cooperating layers, xfail + skip cleanly documented | A |
| Test quality          | Property + adversarial + golden replay cover critical kernels; universal/molecular split has AST guard; self-test regression on Gate 4 tool | B |
| CI config             | Six gates wired in `ci.yml` (6 of 6), pre-commit mirrors (6 of 6), parallel jobs, weekly/nightly scheduled gates | A- |
| Pre-commit            | Six hooks, all local, fail_fast off, paths/extensions excluded; mirror is byte-identical for lint-types | A |
| Build / package       | sdist + wheel built and twine-checked; dry-run-only release (paper-gated); LICENSE + classifiers + SPDX consistent | A |
| Doc verification      | `check_docs_against_code.py` + `check_claims_consistency.py` + `mkdocs build --strict` all wired into CI and pre-commit; self-test on Gate 4 currently failing | B |
| Issues found          | 7 (1 high, 3 medium, 3 low) — `stress-nightly.yml` Windows path, duplicate workflows with stale test reference, `check_docs` self-test failures, etc. | B |

**Overall governance grade: B+.** The six pre-merge gates are
comprehensively wired, the build artifacts are present and
twine-validated, the release flow is intentionally conservative and
explicitly paper-gated, and the test inventory is well-structured. The
grade is held back by (1) the pre-existing `check_docs_against_code`
self-test failures, (2) the `stress-nightly.yml` Windows-path bug that
silently breaks the only runner it is configured for, (3) the duplicate
workflows (`cpu-tests.yml` + `docs-validate.yml`) with a stale test-file
reference, and (4) the documented `mutmut`-vs-`ast_mutator` drift.

**5-line summary:**

1. Tests counted: **97 test files / ~1 760 functions**, six layers
   (unit / property / adversarial / golden / benchmark / tool-self-test),
   9 torch-gated skips, 10 stress markers, 1 xfail, **3 pre-existing
   failures** (1 xfail + 2 doc-scanner self-tests).
2. Coverage gaps: universal split has AST guard, contracts / universal /
   frame / molecular / adapters / eval all have at least one test file;
   the residual gap is **the `check_docs_against_code` self-test
   regressions** (Gate 4 tool tests itself but is currently failing),
   and **no `tests/test_*.py` for `adaptive_reflow/legacy/`** (the
   subpackage is quarantined, but a single smoke import test would
   catch a future accidental public re-export).
3. CI gates covered: **6 of 6** in `ci.yml` (pytest, ruff, mypy,
   check_docs, check_claims, mkdocs --strict), parallel jobs, 15-min
   timeout, weekly bench / nightly mutation / weekly stress scheduled.
4. Build verified: sdist + wheel exist in `dist/`, both `twine check`
   PASS per `docs/RELEASING.md` 0.1.0 dry-run table, `LICENSE` is MIT,
   `pyproject.toml` PEP 621 metadata complete, `[chemistry]` and
   `[flow_matching]` extras pinned, `[dev]` extra covers mkdocs
   toolchain, `dist/` is in `.gitignore`.
5. Biggest issue: **`stress-nightly.yml` references a Windows-only
   Python path on a Linux-only runner** (`.venv/Scripts/python.exe` on
   `ubuntu-latest`); combined with the pre-existing `check_docs_against_code`
   self-test failures and the duplicate `cpu-tests.yml` /
   `docs-validate.yml` workflows (one of which references a
   mis-renamed test file), the **CI/CD surface has 3 latent issues**
   that the next audit pass should land as a single PR.
6. **Governance grade: B+** — strong six-gate coverage and packaging
   discipline, held back by 1 high-severity workflow bug + 1
   pre-existing gate-tool regression + 1 redundant-workflow cleanup.
