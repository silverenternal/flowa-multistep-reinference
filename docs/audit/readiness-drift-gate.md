# The drift gate passed when its scan did not run

**Date:** 2026-10-31
**Surface:** `tools/verify_submission_readiness.py` gate 8 (`drift_33`), chain entry 1
**Fix:** six lines + two tests. No metric, claim or status label touched.

## Observed

`gate_drift_33` runs

```python
proc = subprocess.run(["grep", "-rn", "33/33 PASS", "docs/"], check=False)
raw_hits = proc.stdout.splitlines() if proc.returncode in (0, 1) else []
```

`grep` exits 1 when it finds nothing — the clean case — and 2 when the scan
could not run: unreadable `docs/`, missing binary, bad pattern. The expression
maps both non-zero statuses to `[]`, and `[]` is also what a clean scan
produces, so the gate reports

```
[ OK ] drift_33 : 0 unintended 33/33 occurrences outside Wave 149 audit trail
```

whether it looked or not. `grep` is present here and in CI, so the hole was
never exercised; it is still a gate whose passing output is indistinguishable
from its not-having-run output.

That is the same shape as `mypy_0`, which answered `SKIPPED` for months while
three reviewer-facing rows asserted `0 errors`
(`docs/audit/mypy-gate-restoration.md`), and as the six §6 commands that were
never executed (`docs/audit/repro-command-audit.md`). The project has now hit
this shape three times, which is why the fix is a fail-closed branch rather
than a comment.

## Changed

```python
if proc.returncode not in (0, 1):
    return GateResult(
        name="drift_33",
        passed=False,
        detail="drift scan did not run (grep failed), so this gate cannot pass",
        error=(proc.stderr.strip() or f"grep exited {proc.returncode}")[:200],
    )
```

`tests/test_tools/test_readiness_drift_gate.py` pins both branches: exit 1 is
`passed=True, skipped=False`, exit 2 is `passed=False` with grep's stderr in
the error field.

## Checked and left alone

The other eight readiness gates and the three exception handlers in the gate
tools:

* `check_data_integrity` turns an `OSError` while hashing into a `missing`
  mismatch, i.e. a failure.
* `paper_evidence._read` returns `""` on `OSError`; the quoted-number check
  then cannot find the quote, so it fails.
* `run_all_gates` wraps every gate in `try/except` and builds a `passed=False`
  result from the exception.

Only `drift_33` turned "I could not measure" into "clean".

## Verification

```
python3 tools/verify_submission_readiness.py   READY: all gates passed (9/9, 0 skips)
tests/test_tools/test_readiness_drift_gate.py  2 passed
ruff check tools/                               clean
```
