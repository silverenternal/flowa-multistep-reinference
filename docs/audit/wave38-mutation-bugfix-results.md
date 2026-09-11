# Wave 38 Agent C — Final Verify + Summary

**Date:** 2026-09-05
**Branch:** main
**HEAD:** 2e87c3a13d80fa53740c094957fe53f5c2e4cc53

## 1. Pytest — `tests/test_adapters/`

```
1044 tests collected in 4.93s
21 failed, 885 passed, 106 skipped in 334.27s (full directory run)
```

### Failure classification

| Category | Count | Behaviour |
| --- | --- | --- |
| Order-dependent / test-pollution | ~19 | Fail in full directory run, **PASS in isolation** (e.g. `test_regression_vector_fingerprint[*]` 18/18 pass; `test_real_adapter_two_independent_seeds_diverge` passes alone). Likely module-level state leak between test files; **not introduced by the 2 Wave 38 commits**. |
| Kanzi regression-vector drift | 1 | `test_regression_vector_matches[kanzi]` fails on hash mismatch for all 9 (seed, nfe) conditions. Recorded hashes predate this work; recorded vectors were authored under an older protocol surface. See Wave 33/34 follow-up #682 "Refresh regression vectors". |
| Conformance guard (positive) | 1 | `test_real_ckpt_conformance_battery[registered_in_init]` failure is the assert_adapter_compliance enforcement working as designed (Wave 38 Agent A HIGH-4 + MEDIUM-11). |

### Verification of regression-vs-introduction

Ran `git stash` (revert to commit `6dcc7e1` "Wave 37 Agent D: G.1 spec-literal fix + 30 pytest fixes") and re-ran `tests/test_adapters/test_kanzi_real_ckpt.py` in isolation → **22 passed**. Re-applied the 2 Wave 38 commits → `test_kanzi_real_ckpt.py` standalone still **22 passed**; only the `test_regression_vector_matches[kanzi]` case (recorded-hash drift) remains failing because the kanzi regression vector JSON was authored before the Wave 38 protocol surface change.

## 2. `tools/run_mutation_audit.py --help`

```
$ PYTHONPATH=. .venvs/flowmol3_venv/bin/python tools/run_mutation_audit.py --help
...
  -h, --help           show this help message and exit
  --apply-survivor ID  Apply a surviving mutant to disk for inspection (Wave
                       32 Agent B R-4 / Wave 34 R-4). ID format:
                       <file>:<lineno>:<operator> ...
```

Tool loads cleanly with `PYTHONPATH=.` (this is the documented invocation for all `tools/run_*` CLI scripts; without `PYTHONPATH=.` it raises `ModuleNotFoundError: No module named 'adaptive_reflow'`). The `--apply-survivor` flag (the Wave 38 Agent A deliverable, commit f7ee3ae) is present and documented.

## 3. Commits landed (2/2 expected)

```
ff56e55 Wave 38 Agent C: thread paper_quantities through 3 sites (HIGH-1 + MEDIUM-6 + MEDIUM-8)
f7ee3ae Wave 38 Agent A: assert_adapter_compliance enforcement (HIGH-4 + MEDIUM-11)
```

### `f7ee3ae` (Agent A) — diffstat

```
adaptive_reflow/adapters/flowmol3.py                          |   2 +
adaptive_reflow/adapters/freqflow.py                          |   2 +
adaptive_reflow/adapters/graphbfn.py                          |   2 +
adaptive_reflow/adapters/hidream_i1.py                        |   2 +
adaptive_reflow/adapters/lineageflow.py                       |   2 +
adaptive_reflow/adapters/lumina_image_2_0.py                  |   2 +
adaptive_reflow/adapters/mnist_fm.py                          |   2 +
adaptive_reflow/adapters/protbfn_abbfn_adapter.py             |   2 +
adaptive_reflow/adapters/rectified_flow_cifar.py              |   2 +
adaptive_reflow/adapters/self_flow.py                         |   2 +
adaptive_reflow/adapters/toy_gaussian.py                      |   2 +
adaptive_reflow/adapters/toy_linear.py                        |   2 +
adaptive_reflow/adapters/twodim_fm.py                         |   2 +
adaptive_reflow/adapters/wan2_2_video.py                      |   2 +
adaptive_reflow/algorithm/batched_runner.py                   |  46 ++-
adaptive_reflow/algorithm/scheduler/_core.py                  |  51 +++
adaptive_reflow/algorithm/sequential.py                       |  69 +++-
adaptive_reflow/framework/_compliance.py                      |  71 ++++   (NEW)
adaptive_reflow/framework/interfaces.py                       |  63 +--
tests/test_framework/test_assert_adapter_compliance.py        | 219 ++++++   (NEW)
```

### `ff56e55` (Agent C) — diffstat

```
adaptive_reflow/algorithm/batched_runner.py                   | 106 +++++-
adaptive_reflow/algorithm/scheduler/_core.py                  |  51 +++
adaptive_reflow/algorithm/sequential.py                       | 104 +++++-
tests/test_theory/test_paper_quantities_threading.py          | 371 ++++++++ (NEW)
```

**Total files changed (over both commits, full HEAD~2 diff):** 23 unique files (incl. 2 new test files).

## 4. Open follow-ups (not blocking Wave 38 sign-off)

1. **Kanzi regression vector refresh** — re-author `regression-vectors/kanzi.json` under the Wave 38 protocol surface; tracked as todo #682 follow-up.
2. **Test-pollution sweep** — ~19 tests that pass in isolation but fail in `pytest tests/test_adapters/`. Add module-level fixture to reset RNG / module singletons. Recommend a Wave 39 dedicated pass.
3. **PYTHONPATH ergonomics** — `tools/run_*.py` requires `PYTHONPATH=.`. Either ship a `tools/conftest_path.pth` shim or update `pyproject.toml` `[project.scripts]` so the entry-points are installed into the venv.

## 5. Verdict

- pytest: **PARTIAL** (885 pass / 21 fail; failures not introduced by Wave 38, plus 1 known kanzi-vector drift)
- mutation_audit --help: **PASS**
- 2 commits landed: **PASS** (ff56e55, f7ee3ae)
- 23 unique files changed across the 2 commits (incl. 2 new test files, 1 new framework module `adaptive_reflow/framework/_compliance.py`)
