# Xfail triage — twelve tests that cannot pass, labelled with the wrong reason

**Date:** 2026-10-29
**Scope:** the 12 `xfailed` tests in `tests/test_tools/`.
**Status:** reasons corrected, then resolved — ten deleted, two retargeted;
zero xfails remain. No metric, claim, status label, or verdict moved; no GPU
was used.

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

## 3. Why they could not be repaired in place

The tested module is a **byte-identical vendored tree** pinned by commit
`ccef84ad…` and enforced by submission-checklist row 13. Editing it to satisfy
the tests is not available.

That left two real options, both editorial:

1. **Retarget** the ten worker tests at
   `tools/run_lineageflow_n1000_foldability_omegafold.py`, which is where the
   sharding now lives, and the two eval tests at the current upstream CLI
   contract. This is the option that restores coverage.
2. **Delete** the twelve. They cannot pass, and a test that can never pass is
   not a test.

Neither was a mechanical fix, so both were put to the user rather than chosen
unilaterally: option 1 rewrites a thousand lines of subprocess-mocking tests
against a different module, and option 2 lowers the counted suite size. The
user asked for both halves — retarget where the contract still exists, delete
where it does not.

## 4. What changed (pass 1 — reasons)

The twelve reason strings now say what is actually true and point here:

```
asserts a workers_per_gpu sharding API that the byte-identical vendored
upstream does not provide; see docs/audit/xfail-triage.md

asserts the pre-Wave-275 --pfam-fastas-dir CLI contract of the vendored
upstream; see docs/audit/xfail-triage.md
```

## 4a. What changed (pass 2 — resolution)

**Ten deleted, ten replacements written.** The ten tests in
`tests/test_tools/test_workers_per_gpu.py` that imported the vendored
`foldability_omegafold.py` and asserted a `workers_per_gpu=` keyword were
removed (689 lines). The file's docstring now records the history and keeps
the three tests that never depended on the removed patch — the vendored
script's own default and its two length-balanced sharding helpers.

The capability they were reaching for is still tested, at the module that
actually owns it. `tests/test_tools/test_gpu_workers_detect.py` (new, 10
tests) pins `_detect_gpu_workers()` in
`tools/run_lineageflow_n1000_foldability_omegafold.py`:
`max(1, min(4, floor(free_gb / 4)))` over the *most-constrained* GPU, with
a default of 1 whenever `nvidia-smi` is missing, exits non-zero, prints
nothing, or prints rows that do not parse. This is the code the R1
wall-clock evidence runs on, so pinning it is strictly more useful than the
old assertions about a flag that no longer exists.

While writing those tests the wrapper's docstring heuristic table was found
to be missing its 12–16 GB row (it claimed 8–16 GB → 2 workers, while the
formula returns 3 for anything ≥ 12 GB). The table was corrected and the
formula named as the source of truth.

**Two retargeted, none deleted.** In `tests/test_tools/test_upstream_eval.py`
both `xfail` markers were removed:

- The `--pfam-fastas-dir` assertion now accepts either the vendored
  `pfam_fastas_clean/` directory or the Wave-275 synthesized tempdir whose
  basename starts `lineageflow_k7_pfam_`.
- The `kwargs=None` test asserted that omitting `kwargs` omits the flag.
  Under K7 that is no longer true — the K7 holdout tempdir is created by
  default — so the test now asserts the flag *is* present by default, and
  adds a second call with `restrict_novelty_to_target_db=False` to pin the
  behaviour the old assertion was reaching for.

Both files pass: `28 passed` across the three files, `15 passed / 0 xfailed`
for `test_upstream_eval.py` alone.

## 4b. What did not change

No metric, claim, status label, or verdict was touched. `docs/CLAIMS.md` was
not edited. The deleted tests asserted a code path that no longer exists in
the tree, so removing them removes no live coverage; the ten replacements
cover the path that replaced it.

## 5. Skips are not in this class

The 180 skips are environment-driven and self-describing (`torch not in venv`,
`pandas not in venv`, `hypothesis not installed`). Each one names the missing
package in its reason, so none of them can rot the way these xfails did.

## 6. Gates

| Gate | Result |
|---|---|
| `pytest tests/test_tools/test_workers_per_gpu.py tests/test_tools/test_upstream_eval.py tests/test_tools/test_gpu_workers_detect.py -q` | 28 passed, 0 xfailed |
| `pytest tests/test_tools/test_upstream_eval.py -q` | 15 passed, 0 xfailed (was 13 passed / 2 xfailed) |
| full `pytest tests/ --ignore=tests/test_tools/test_paper_metrics.py` (CPU) | **5553 passed / 180 skipped / 0 xfailed** in 646 s (was 5541 / 180 / 12) |
| `ruff check tests/ tools/` | 0 findings |
| 12-entry `todo.json` gate chain | all rc=0 |
| `mkdocs build --strict` | exit 0 |

The arithmetic of the new total: 5541 passed + 10 new tests + 2 tests that
stopped being xfailed = 5553; xfailed 12 − 10 deleted − 2 retargeted = 0;
skips unchanged at 180. Collected count is unchanged at 5733 because the ten
deletions and ten additions cancel.

## 7. Surfaces updated

The suite size appears on eleven live surfaces. All were updated in the same
commit, together with the `12 xfailed` clause:

`docs/code-release-checklist.md`, `docs/RELEASE-NOTES.md`,
`docs/environments.md` (also refreshed from the 2026-10-27 measurement:
5500 → 5553, 12m17s → 10m46s), `docs/cover-letter-tnnls.md` (×2),
`tnnls_submission/cover_letter.md` (×2), `tnnls_submission/data_availability.md`,
`tnnls_submission/submission_checklist.md`, `tnnls_submission/tables.md`,
`tnnls_submission/figures.md` (ASCII box, width-preserving 4→4 digit swap),
`tnnls_submission/MANIFEST.md` (×2, one of which was still on 5528), and
`todo.json`'s `gate_note`.

Historical audit records that quote the old numbers were **not** rewritten:
they are dated measurements, and changing them would falsify the record.

