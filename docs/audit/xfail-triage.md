# Xfail triage — twelve tests that cannot pass, labelled with the wrong reason

**Date:** 2026-10-29
**Scope:** the 12 `xfailed` tests in `tests/test_tools/`.
**Status:** reasons corrected; no test deleted; counts unchanged. No metric,
claim, status label, or verdict moved; no GPU was used.

---

## 1. The defect

Every xfail in the suite carried the same string:

```python
@pytest.mark.xfail(reason="k1_rc5 historical drift, see Wave 359 P1")
```

That is a copy-paste, and it is wrong. `k1_rc5` is the K1 disclosure-wording
gate in `tools/verify_submission_readiness.py` — a documentation check that
reads the manuscript. It has nothing to do with any of these twelve tests, and
it reports `[ OK ]` today. A reader who hits one of these xfails is pointed at
an audit document that explains a different problem.

Verified with `--runxfail`: all twelve still fail, for two reasons that the
label never mentioned.

## 2. What they actually assert

**Ten tests — `tests/test_tools/test_workers_per_gpu.py`.**
They load the *vendored* `data/lineageflow_upstream/evaluation/foldability_omegafold.py`
and assert that `run_omegafold_sharded` accepts `workers_per_gpu` (default 1)
and spawns `workers_per_gpu × |gpus|` subprocesses. The vendored signature is:

```
(*, records, pdb_dir, omegafold_bin, gpus: List[int], extra_args, force, log_every)
```

There is no `workers_per_gpu`. The capability exists — but in *our* wrapper
`tools/run_lineageflow_n1000_foldability_omegafold.py`, which exposes
`--workers-per-gpu` and a `_detect_gpu_workers()` auto mode. The tests were
written against a local fork of the upstream file that was later replaced by
the byte-identical vendor tree.

**Two tests — `tests/test_tools/test_upstream_eval.py`.**
They assert that the upstream eval command line carries
`--pfam-fastas-dir …/pfam_fastas_clean`. The contract moved at Wave 275 and the
argument no longer ends with that path.

## 3. Why they were not repaired here

The tested module is a **byte-identical vendored tree** pinned by commit
`ccef84ad…` and enforced by submission-checklist row 13. Editing it to satisfy
the tests is not available.

That leaves two real options, both editorial:

1. **Retarget** the ten worker tests at
   `tools/run_lineageflow_n1000_foldability_omegafold.py`, which is where the
   sharding now lives, and the two eval tests at the current upstream CLI
   contract. This is the option that restores coverage.
2. **Delete** the twelve. They cannot pass, and a test that can never pass is
   not a test.

Neither was chosen unilaterally: option 1 rewrites a thousand lines of
subprocess-mocking tests against a different module, and option 2 lowers the
counted suite size — both are decisions about what the suite is for, not
mechanical fixes.

## 4. What changed

The twelve reason strings now say what is actually true and point here:

```
asserts a workers_per_gpu sharding API that the byte-identical vendored
upstream does not provide; see docs/audit/xfail-triage.md

asserts the pre-Wave-275 --pfam-fastas-dir CLI contract of the vendored
upstream; see docs/audit/xfail-triage.md
```

Counts are unchanged (`12 xfailed`), so no other surface moved.

## 5. Skips are not in this class

The 180 skips are environment-driven and self-describing (`torch not in venv`,
`pandas not in venv`, `hypothesis not installed`). Each one names the missing
package in its reason, so none of them can rot the way these xfails did.

## 6. Gates

| Gate | Result |
|---|---|
| `pytest tests/test_tools/test_workers_per_gpu.py tests/test_tools/test_upstream_eval.py -rx` | 16 passed, 12 xfailed, reasons as above |
| `ruff check tests/` | 0 findings |
| 12-entry `todo.json` gate chain | all rc=0 |
