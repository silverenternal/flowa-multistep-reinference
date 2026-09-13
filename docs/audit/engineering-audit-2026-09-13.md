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
