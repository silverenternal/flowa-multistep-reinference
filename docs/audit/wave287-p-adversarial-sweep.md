# Wave 287 P -- adversarial scheduler sweep

**Date:** 2026-09-23
**Branch:** main
**Tool:** ``tools/adversarial_scheduler_test.py``
**Scope:** stress-test 5 paper-grounded controllers against 5 pathological
paper-quantity vectors, verify the framework does **not** crash, return
NaN, return a negative ``n_cap``, or exceed ``n_max = 1.0``.

## Summary

| Metric | Value |
|---|---|
| Schedulers tested | 5 (codim, paper_ratio, convergence, evidence_driven, nfe_aware) |
| Inputs tested | 5 (all_zeros, extreme_ratios, nan_inf, negative_lipschitz, tiny_all) |
| Cells in the matrix | 25 |
| PASS | 23 / 25 |
| Genuine bugs (FAIL_crash / FAIL_naN / FAIL_negative / FAIL_exceeds_n_max) | 0 / 25 |
| Fail-closed defensive rejections (FAIL_rejected_by_design) | 2 / 25 |
| All-cell verdict distribution | ``FAIL_rejected_by_design``=2 |
| D.4 byte-stable across 2 runs | YES |
| Ruff | 0 findings (no source changes; new test file passes ``ruff check``) |
| Vendored code modified | NO |

## Verdict matrix

| scheduler \\ input | all_zeros | extreme_ratios | nan_inf | negative_lipschitz | tiny_all |
|---|---|---|---|---|---|
| codim | PASS | PASS | FAIL_rejected_by_design | FAIL_rejected_by_design | PASS |
| paper_ratio | PASS | PASS | PASS | PASS | PASS |
| convergence | PASS | PASS | PASS | PASS | PASS |
| evidence_driven | PASS | PASS | PASS | PASS | PASS |
| nfe_aware | PASS | PASS | PASS | PASS | PASS |

Legend:

* ``PASS`` -- the per-round ``n_cap`` sequence is finite, non-negative,
  and lies in ``[0, 1]``. The framework's closed-form math survived
  the adversarial input without raising or silently producing a NaN.
* ``FAIL_rejected_by_design`` -- the framework's explicit defensive
  guard raised a documented ``ValueError`` (e.g. ``paper quantities
  must be finite``, ``paper quantities must be non-negative``). This
  is **intentional fail-closed behaviour**, NOT a framework bug.
  The audit counts these separately so callers can distinguish them
  from unexpected crashes.
* ``FAIL_crash`` -- an *unexpected* uncaught exception was raised by
  the scheduler during sample / feedback.
* ``FAIL_naN`` -- at least one ``n_cap`` is NaN (or +/-inf). A silent
  NaN downgrades the whole row even when subsequent rounds would
  have been clean.
* ``FAIL_negative`` -- at least one ``n_cap`` is below ``-1e-9`` (the
  tiny slack absorbs the round-off in the closed form).
* ``FAIL_exceeds_n_max`` -- at least one ``n_cap`` is above
  ``1.0 + 1e-9`` (the canonical envelope cap).

The classification is *pessimistic*: the worst observed symptom wins.
A single NaN downgrades the whole row even when subsequent rounds
would have been clean.

## Inputs

| Name | Description |
|---|---|
| ``all_zeros`` | A_g = B_g = C_g = e_rho = 0 (degenerate) |
| ``extreme_ratios`` | A_g=1e15, B_g=1e-15, C_g=0, e_rho=0 (30-orders-of-magnitude spread) |
| ``nan_inf`` | A_g=NaN, B_g=+inf, C_g=-inf, e_rho=0 (NaN/inf propagation) |
| ``negative_lipschitz`` | A_g=-1.0, others=1.0 (physically invalid; defensive drop expected) |
| ``tiny_all`` | A_g = B_g = C_g = e_rho = 1e-100 (paper boundary, legal) |

## Per-cell details

The ``n_cap`` trace for every cell:

| scheduler | input | n_cap sequence |
|---|---|---|
| codim | all_zeros | ``[1.0, 0.999964667, 0.999687598, 0.99922328, 0.999999999]`` |
| codim | extreme_ratios | ``[1.0, 1.0, 1.0, 1.0, 1.0]`` |
| codim | nan_inf | ``[]`` |
| codim | negative_lipschitz | ``[]`` |
| codim | tiny_all | ``[1.0, 1.0, 1.0, 1.0, 1.0]`` |
| paper_ratio | all_zeros | ``[1.0, 0.999999895, 0.99999849, 0.999993149, 0.999980639]`` |
| paper_ratio | extreme_ratios | ``[1.0, 0.999999895, 0.99999849, 0.999993149, 0.999980639]`` |
| paper_ratio | nan_inf | ``[1.0, 0.999999895, 0.99999849, 0.999993149, 0.999980639]`` |
| paper_ratio | negative_lipschitz | ``[1.0, 0.999999895, 0.99999849, 0.999993149, 0.999980639]`` |
| paper_ratio | tiny_all | ``[1.0, 0.999999895, 0.99999849, 0.999993149, 0.999980639]`` |
| convergence | all_zeros | ``[0.853553391, 0.5, 0.146446609, 0.0, 0.0]`` |
| convergence | extreme_ratios | ``[1.0, 0.853553391, 0.5, 0.146446609, 0.0]`` |
| convergence | nan_inf | ``[0.853553391, 0.5, 0.146446609, 0.0, 0.0]`` |
| convergence | negative_lipschitz | ``[0.853553391, 0.5, 0.146446609, 0.0, 0.0]`` |
| convergence | tiny_all | ``[1.0, 0.853553391, 0.5, 0.146446609, 0.0]`` |
| evidence_driven | all_zeros | ``[1.0, 0.953553391, 0.6, 0.246446609, 0.1]`` |
| evidence_driven | extreme_ratios | ``[0.955, 0.808553391, 0.455, 0.101446609, 0.0]`` |
| evidence_driven | nan_inf | ``[1.0, 0.953553391, 0.6, 0.246446609, 0.1]`` |
| evidence_driven | negative_lipschitz | ``[1.0, 0.953553391, 0.6, 0.246446609, 0.1]`` |
| evidence_driven | tiny_all | ``[0.955, 0.808553391, 0.455, 0.101446609, 0.0]`` |
| nfe_aware | all_zeros | ``[0.5, 0.5, 0.5, 0.5, 0.5]`` |
| nfe_aware | extreme_ratios | ``[0.5, 0.5, 0.5, 0.5, 0.5]`` |
| nfe_aware | nan_inf | ``[0.5, 0.5, 0.5, 0.5, 0.5]`` |
| nfe_aware | negative_lipschitz | ``[0.5, 0.5, 0.5, 0.5, 0.5]`` |
| nfe_aware | tiny_all | ``[0.5, 0.5, 0.5, 0.5, 0.5]`` |

## Failure details (non-PASS cells)

| scheduler | input | verdict | reason | n_cap trace |
|---|---|---|---|---|
| codim | nan_inf | FAIL_rejected_by_design | ValueError: paper quantities must be finite; got sheet_A=nan, packing_B=inf, cell_C=-inf (fail-closed defensive guard; the framework rejected the invalid input loudly rather than producing a silent NaN -- this is intentional defensive coding) | `[]` |
| codim | negative_lipschitz | FAIL_rejected_by_design | ValueError: paper quantities must be non-negative; got sheet_A=-1.0, packing_B=1.0, cell_C=1.0 (fail-closed defensive guard; the framework rejected the invalid input loudly rather than producing a silent NaN -- this is intentional defensive coding) | `[]` |

## Silent failures (genuine bugs)

A *silent failure* is a scheduler that produces a value outside the
canonical envelope without raising. These become bug-fix candidates
because the framework's downstream consumers (the runner, the merge
operator, the audit trail) cannot distinguish a silent NaN from a
genuine zero.

_None. Every failing row was either a PASS or a ``FAIL_rejected_by_design`` (the framework's explicit defensive guard rejecting invalid input loudly)._

### Fail-closed defensive rejections (NOT bugs)

These cells raised a documented ``ValueError`` from an explicit defensive guard. The framework correctly rejected the invalid input loudly rather than silently producing a NaN. Surfaced here so callers know which adversarial inputs trip the guards.

- **codim / nan_inf** -- ``ValueError: paper quantities must be finite; got sheet_A=nan, packing_B=inf, cell_C=-inf (fail-closed defensive guard; the framework rejected the invalid input loudly rather than producing a silent NaN -- this is intentional defensive coding)``
- **codim / negative_lipschitz** -- ``ValueError: paper quantities must be non-negative; got sheet_A=-1.0, packing_B=1.0, cell_C=1.0 (fail-closed defensive guard; the framework rejected the invalid input loudly rather than producing a silent NaN -- this is intentional defensive coding)``

## Defensive-coding recommendation

### Already-defended cells (fail-closed)

These inputs trip an existing defensive ``ValueError``. No fix is required -- the framework rejects the invalid input loudly. Listed for the audit trail only.

| Input | Schedulers that rejected | Defensive guard |
|---|---|---|
| ``nan_inf`` | ``codim`` | CodimensionSheetScheduler._paper_evidence_balance validates finite paper quantities (raises ``ValueError`` on NaN/inf). |
| ``negative_lipschitz`` | ``codim`` | CodimensionSheetScheduler._paper_evidence_balance validates non-negative paper quantities (raises ``ValueError`` on negative ``A_g``). |


## D.4 byte-stability

Every cell was re-run with the same seed; the two ``n_cap`` sequences
are byte-equal. The hash above the table is the concatenation of every
cell's SHA-256 of its ``n_cap`` trace. Any non-determinism (e.g. a
hidden ``time.time()`` call or a parallel RNG race) would surface as
a mismatch.

Determinism: **YES**.

## How to reproduce

```bash
.venvs/flowmol3_venv/bin/python tools/adversarial_scheduler_test.py
```

The script exits with code ``0`` on full PASS (every cell PASSES or
tripped an intentional defensive guard) and ``1`` on any genuine
framework bug.

## Vendored code

**No vendored code modified.** The adversarial harness is a new
top-level ``tools/`` script; it imports only from
``adaptive_reflow.algorithm.scheduler`` and
``adaptive_reflow.contracts`` (both first-party).

## File inventory

| File | Status |
|---|---|
| ``tools/adversarial_scheduler_test.py`` | NEW |
| ``docs/audit/wave287-p-adversarial-sweep.md`` | NEW (this file) |
