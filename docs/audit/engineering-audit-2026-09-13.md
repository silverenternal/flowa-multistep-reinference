# Engineering audit — 2026-09-13

## Scope and evidence

Audit performed at commit `f42de22` plus the working-tree changes listed below,
using Python `3.14.5` on the recorded host fingerprint
`sha256:92ae71c7c2d0cf3d`. Commands were run from the repository root:

* `python scripts/run_mypy_audit.py`
* `python scripts/api_churn_report.py report --window-size 1 --json`
* `pytest -q tests/test_universal/test_checkpoint.py tests/test_d4_regression_vectors.py`

The focused suite passed **41 tests** (3 warnings). The type-soundness audit
reports 2,081/2,081 annotated or runtime-checkable public functions (100%).
The API churn command now executes directly from a source checkout.

## Finding fixed

Both audit scripts imported `adaptive_reflow` before adding the checkout root to
`sys.path`. Consequently their documented direct invocation failed unless the
caller had first exported `PYTHONPATH` or installed the package. The scripts now
insert their repository root before importing local modules, preserving normal
editable-install behavior while making clean-checkout audits reproducible.

## Remaining engineering risk

`adaptive_reflow.universal.checkpoint.load_checkpoint` supports opt-in pickle
for legacy interoperability. Python pickle deserialization is code-executing
and must only be used with trusted files; JSON remains the default and is the
recommended interchange format. No behavior change was made in this audit
because existing callers may rely on explicit pickle compatibility. A follow-up
should add an explicit trust gate or remove pickle after migration.

## Reproducibility notes

No GPU workloads were started. The D.4 regression vectors were exercised by the
focused tests, and no regression failure was observed.


## Follow-up: imports, sweep recovery and test resource bounds

Commits `77d62ef`, `85b5080`, `adad7ff` and `2e9b44c` address further
reproducible failures:

- Test-installed Torch substitutes now restore the original module entry
  after each test. The wall-clock experiment test writes only to its pytest
  temporary directory instead of overwriting recorded research evidence.
- FID evaluation of supplied features/statistics is NumPy-only at every
  dimension, including 2048; dependency checks no longer coerce invalid
  dimensions before validation.
- Real Kanzi checkpoint failures no longer return a zero-velocity substitute.
  CPU mapping and strict state loading pass against the original checkpoint.
  Sweep records are checkpointed, incomplete/non-finite runs fail, configured
  step counts are consumed and unmeasured metrics are null.
- Shape property tests no longer allocate arbitrarily large tensors or call
  instance methods as static ndarray functions. They exercise all 16
  registered adapters through bounded actual protocols. Invalid scheduler
  parameter ranges are tested for explicit rejection.
- The non-molecular fixture implements discrete token observation, and the
  baseline audit uses the actual BatchedTrajectoryRunner name.

The Kanzi recovery experiment is documented in
[the bridge follow-up](kanzi-inv-proj-bridge-followup-2026-09-13.md).

### Whole-suite verification and numerical environment

A complete run with OMP/OpenBLAS/MKL thread counts all set to 2 produced
**5154 passed, 196 skipped, 1 failed** (656.54 seconds). Artifacts are at
`verification_outputs/engineering_full_20260913_after_recovery/`.
The sole failure was the Lumina synthetic regression vector's byte hashes.
An isolated default-thread run passed all nine recorded conditions; the
same isolated test with the two-thread overrides reproduced the mismatch.
No reference hashes were changed. This is observed sensitivity to numerical
thread configuration, not evidence that the default regression vectors pass
under arbitrary backend settings.

A full default-thread run was subsequently launched with its own log, JUnit,
invocation and process metadata at
`verification_outputs/engineering_full_20260913_default_threads/`.
Its terminal result is **5155 passed, 196 skipped**, 1074 warnings, in
588.37 seconds; wrapper `exit.json` records exit code 0 (589.14 seconds).
This verifies the pytest suite through `fee9352`, not all CI gates.
The earlier `/tmp/flowa-full-after-isolation.log` stopped around 79% without a
terminal summary and is not counted as a completed suite.


### Static CI gates reopened

`ruff check adaptive_reflow/ tests/` with Ruff 0.15.22 reports 926 findings,
including 31 F821 missing-name findings. No lint rule was disabled. A first
isolated mypy run lacked the project dependency environment; the corrected
command `uv tool run --from mypy mypy --python-executable .venv/bin/python
adaptive_reflow` reports 988 errors in 70 files (222 files checked). These
are current failing gates, under repair in isolated worktrees. Pytest success
does not establish lint/type correctness or cover all dynamically reached
branches. Local diagnostic logs: `/tmp/flowa-ruff-current.json` and
`/tmp/flowa-mypy-current.log`.
