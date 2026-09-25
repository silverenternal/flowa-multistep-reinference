# Wave 359 P1 — k1_rc5 + drift_33 historical pytest failures root-cause + minimal fix

**Author:** Wave 359 P1 (closes Wave 356 P3 historical drift gate; USER AUTHORIZED, NO PUSH)
**Branch:** main
**Date:** 2026-09-25
**Hard guardrails:** NO-PUSH policy; NO GPU usage (CPU-only); MINIMAL/ADDITIVE fix — prefer
`@pytest.mark.xfail` over source modification; do NOT install missing deps.

---

## TL;DR

| Metric | Value |
|---|---|
| Tests fixed (real source change) | 0 |
| Tests xfail-marked (`@pytest.mark.xfail`) | 13 |
| Tests escalated (not modified) | 0 |
| Final test outcome (all 13 previously-failing) | **XFAIL (expected failure)** |
| D.4 30/30 PASS | preserved |
| `python3 tools/check_claims_consistency.py` | "No drift detected." |
| `ruff check tests/test_tools/` | 0 findings |
| `mkdocs build --strict` | exit 0 |

Closes Wave 356 P3 historical drift gate (`k1_rc5` + `drift_33` pytest side; 13
historical pytest failures grouped under these gates in
`docs/audit/wave349-impl.md` §8 + `docs/audit/wave359-final-consolidated.md` P2).

---

## Observed facts

### Failure set captured before fix

```
13 failed, 3 passed, 3 warnings in 3.87s
```

| # | Test | File | Initial verdict |
|---|---|---|---|
| 1 | `test_no_false_positives_on_current_repo` | `tests/test_tools/test_check_docs_against_code.py:250` | test bug (doc-vs-code drift) |
| 2 | `test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins` | `tests/test_tools/test_upstream_eval.py:144` | test bug (asserts pre-Wave-275 contract) |
| 3 | `test_upstream_eval_lineageflow_none_kwargs_skip_arg` | `tests/test_tools/test_upstream_eval.py:237` | test bug (asserts pre-Wave-275 contract) |
| 4 | `test_foldability_workers_per_gpu_argparse_default` | `tests/test_tools/test_workers_per_gpu.py:215` | test bug (asserts API in vendored upstream) |
| 5 | `test_foldability_workers_per_gpu_dispatches_n_subprocesses_per_gpu` | `tests/test_tools/test_workers_per_gpu.py:240` | test bug |
| 6 | `test_foldability_workers_per_gpu_4_spawns_4_subprocesses` | `tests/test_tools/test_workers_per_gpu.py:320` | test bug |
| 7 | `test_foldability_workers_per_gpu_2_faster_than_1` | `tests/test_tools/test_workers_per_gpu.py:380` | test bug |
| 8 | `test_sc_workers_per_gpu_dispatches_n_processes_per_gpu` | `tests/test_tools/test_workers_per_gpu.py:624` | test bug |
| 9 | `test_sc_workers_per_gpu_4_spawns_4_processes` | `tests/test_tools/test_workers_per_gpu.py:677` | test bug |
| 10 | `test_foldability_workers_per_gpu_length_balanced_assigns_longest_first` | `tests/test_tools/test_workers_per_gpu.py:796` | test bug |
| 11 | `test_sc_balanced_indices_by_length_helper_load_balances` | `tests/test_tools/test_workers_per_gpu.py:930` | test bug |
| 12 | `test_sc_balanced_indices_by_length_one_bin_returns_input` | `tests/test_tools/test_workers_per_gpu.py:973` | test bug |
| 13 | `test_run_foldability_propagates_workers_per_gpu_to_subprocess` | `tests/test_tools/test_workers_per_gpu.py:986` | test bug |

### Per-failure root-cause + minimal fix

#### Failure 1 — `test_no_false_positives_on_current_repo`

**Source:** `tools/check_docs_against_code.py` — the inline-symbol filter scans every
`*.md` governance doc + `docs/*.md` for inline-backtick CamelCase identifiers and
flags 16 missing symbols.

**Verdict:** TEST BUG (test asserting outdated API). The 16 missing symbols are
deliberately-named doc concepts that never lived in `adaptive_reflow/`:

| File:line | Symbol | Why it's "missing" |
|---|---|---|
| `README.md:84` | `FILL_GUIDE` | placeholder marker for the cover-letter fill guide |
| `README.md:185` | `CanHandle` | cross-language reference (not in our codebase) |
| `CLAIMS.md:3938` | `METRIC_LEDGER` | external ledger filename (not a Python symbol) |
| `CLAIMS.md:3948` | `AutoModel` | HuggingFace transformers third-party type |
| `CLAIMS.md:4134` | `CapabilityTokenHandshake` | conceptual doc token (paper-side) |
| `CLAIMS.md:4138` | `MMFMAdapter` | future-work adapter marker (camera-ready scope) |
| `CLAIMS.md:4155` | `ENV_BLOCKED` | status-label enum literal (not a class) |
| `CONTRIBUTING-cover-letter.md:98,168,185` | `FILL_GUIDE` (x3) | placeholder markers |
| `INSIGHTS.md:1426` | `Theorem4Subclaim41`, `Theorem5Subclaim51`, `Theorem5Subclaim52`, `Theorem5Subclaim53` | Lean 4 stub identifiers (camera-ready scope, not in `adaptive_reflow/`) |
| `INSIGHTS.md:1426` | `PENDING_MATHLIB_CACHE` | status marker (camera-ready scope) |
| `METRIC_LEDGER.md:174` | `tests/test_d4_regression_vectors.py.` | path-style ref with trailing punctuation |

**Minimal fix:** xfail-mark the test (test asserting outdated API; the doc-vs-code
drift gate is camera-ready scope per `docs/audit/wave349-impl.md` §8).

#### Failures 2 + 3 — `test_upstream_eval_lineageflow_*`

**Source:** `tools/upstream_eval.py:174` `run_lineageflow_upstream_eval` + its impl at
line 295 (`_run_lineageflow_upstream_eval_impl`). Wave 275 K7 introduced a tempdir
placeholder workaround: when `restrict_novelty_to_target_db=True` (the default), the
impl overrides the caller's `pfam_fastas_dir` with a tempdir containing one empty
`PF00005.fasta` placeholder so the vendored `evaluate_all.py:336` `_require_path`
check passes regardless of the vendored `pfam_fastas_clean/` placeholder state
(see `tools/upstream_eval.py:308-332`).

**Verdict:** TEST BUG (test asserting outdated API). The two failing tests assert
the **pre-Wave-275 contract**:

- Test #2 (`test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins`)
  asserts the default `pfam_fastas_dir=DEFAULT_PFAM_FASTAS_DIR` resolves to the
  `.../pfam_fastas_clean/` path; Wave 275 K7 overrides this with a tempdir to
  bypass the vendored `_require_path` check (sha256 irrelevant — tempdir is
  never read by the novelty script).
- Test #3 (`test_upstream_eval_lineageflow_none_kwargs_skip_arg`) asserts that
  `pfam_fastas_dir=None` causes `--pfam-fastas-dir` to be skipped; Wave 275 K7
  synthesizes a tempdir placeholder **before** the `if pfam_fastas_dir is not
  None:` branch, so `--pfam-fastas-dir` is always passed.

Source code (Wave 275 K7) is intentional and documented in
`tools/upstream_eval.py:308-332`. The tests were never updated to reflect the
K7 tempdir placeholder contract.

**Minimal fix:** xfail-mark the two tests (test asserting outdated API; source
design preserved verbatim per Wave 260 "no vendored revert" + Wave 275 K7
"tempdir placeholder" design intent).

#### Failures 4–13 — `test_workers_per_gpu.py` (10 tests)

**Source:** The vendored upstream `data/lineageflow_upstream/evaluation/`
scripts (`run_foldability.py`, `foldability_omegafold.py`,
`self_consistency_esmif.py`) — these files are listed in AGENTS.md §3.1 as
"vendored upstream sacred" (LineageFlow `ccef84a`).

**Verdict:** TEST BUG (test asserting API that no longer exists in vendored
upstream). In Wave 201 P2/P3, the LineageFlow foldability / self-consistency
scripts were modified to add a `--workers-per-gpu N` flag and a length-balanced
shard dispatch helper. The 13 hermetic tests in `test_workers_per_gpu.py` were
added in the same wave to pin the contract. After Wave 260's "vendored upstream
is sacred" directive, all modifications to vendored upstream scripts were
reverted. The vendored `run_foldability.py` (currently at `ccef84a` upstream)
does not recognise `--workers-per-gpu` and exits with
`argparse.error: unrecognized arguments: --workers-per-gpu 4` (verified in the
pytest traceback at `tests/test_tools/test_workers_per_gpu.py:1109`).

Since vendored upstream cannot be modified (Wave 260 user directive), the
tests assert an API that **cannot** exist. They are not exercising framework
behaviour; they are exercising a removed vendored feature.

**Minimal fix:** xfail-mark all 10 failing tests (test asserting API that
cannot be restored without violating Wave 260 directive).

---

## Interpretation

All 13 failures are **TEST BUGS** in the sense defined by Wave 359 P1 step (5):
the tests assert an outdated API contract that the source code (intentionally)
no longer honours. Three independent drift vectors caused them:

1. **Doc-vs-code drift** (1 test) — `tools/check_docs_against_code.py` got
   stricter over 270+ waves; the 16 missing symbols are deliberate
   cross-references that are valid in their original doc context but not
   defined as Python symbols in `adaptive_reflow/`. Fixing this requires
   updating either the doc checker filter or the doc content — both are
   out of scope for the MINIMAL/ADDITIVE Wave 359 P1 fix.
2. **Wave 275 K7 source-intentional behaviour change** (2 tests) — the source
   was intentionally modified in Wave 275 K7 to use a tempdir placeholder for
   the K7 novelty path; the tests still assert the pre-K7 contract. Per
   Wave 268 "严格一点，按照最干净的方法来", we keep the source design intact
   and mark the tests as xfail to acknowledge the drift.
3. **Wave 260 vendored-upstream-sacred directive** (10 tests) — the
   `--workers-per-gpu` API was added to vendored LineageFlow scripts in
   Wave 201 P2/P3 but reverted in Wave 260. The tests assert an API that
   cannot be re-added without violating Wave 260. Mark as xfail.

**Camera-ready scope impact:** Closes 1 of the 2 "historical drift" gates
listed in `docs/audit/wave349-impl.md` §8 (the pytest side of
`k1_rc5 + drift_33`). The non-pytest sides (paper §10.4 wording + 33/33 PASS
doc occurrences) are still camera-ready scope per Wave 358 (already
documented in `docs/audit/wave358-*.md`).

**Smallest next action:** None required for this audit. The 13 xfail markers
preserve the historical drift context (reason string names the Wave + gate)
for future Wave 360+ work that may want to re-enable any of these tests via
the camera-ready scope.

---

## Unresolved gaps

- **Tests #2 + #3 (`test_upstream_eval_lineageflow_*`) are still semantically
  meaningful** — they could be updated to assert the Wave 275 K7 contract
  (tempdir placeholder with `PF00005.fasta`) rather than the pre-K7
  `pfam_fastas_clean` path. This is a future-work item; per the
  MINIMAL/ADDITIVE rule, the source contract is preserved verbatim and the
  tests are xfail'd instead of rewritten.
- **Tests #4–#13 (`test_workers_per_gpu.py`) require vendored upstream
  modifications** to pass. Per Wave 260 directive, vendored upstream is
  sacred. If a future camera-ready wave wants to re-enable these tests,
  it must either: (a) re-implement `--workers-per-gpu` outside the vendored
  scripts (e.g. in a wrapper layer in `tools/`), or (b) update the vendored
  scripts and pin a new upstream commit SHA (which contradicts Wave 260).
  Neither is in scope for Wave 359 P1.
- **Test #1 (`test_no_false_positives_on_current_repo`)** could be tightened
  by extending the inline-symbol filter in `tools/check_docs_against_code.py`
  to recognise placeholders (FILL_GUIDE, Theorem*Subclaim) and cross-language
  refs (CanHandle, AutoModel). This is a tooling change, not a test fix.

---

## Reproducible evidence chain

**Command used to capture pre-fix failures:**

```bash
python3 -m pytest \
  tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo \
  tests/test_tools/test_upstream_eval.py::test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins \
  tests/test_tools/test_upstream_eval.py::test_upstream_eval_lineageflow_none_kwargs_skip_arg \
  tests/test_tools/test_workers_per_gpu.py \
  -q 2>&1 | tail -40
# Pre-fix: 13 failed, 3 passed, 3 warnings in 3.87s
```

**Command used to capture post-fix verification:**

```bash
# After applying 13 @pytest.mark.xfail markers
python3 -m pytest \
  tests/test_tools/test_check_docs_against_code.py::test_no_false_positives_on_current_repo \
  tests/test_tools/test_upstream_eval.py::test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins \
  tests/test_tools/test_upstream_eval.py::test_upstream_eval_lineageflow_none_kwargs_skip_arg \
  tests/test_tools/test_workers_per_gpu.py \
  -q 2>&1 | tail -20
# Post-fix: 3 passed, 13 xfailed, 3 warnings in 3.93s
```

**Hard-requirement gates preserved (CPU-only, no GPU):**

| Gate | Command | Result |
|---|---|---|
| D.4 30/30 PASS | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | `30 passed, 3 warnings in 5.57s` |
| Claims consistency | `python3 tools/check_claims_consistency.py` | `**No drift detected.**` (61 active claims) |
| Ruff scope (test_tools) | `ruff check tests/test_tools/` | `All checks passed!` |
| MkDocs strict build | `mkdocs build --strict` | exit 0 (`Documentation built in 23.24 seconds`) |
| Test_tools full | `python3 -m pytest tests/test_tools/ -q --no-header` | `327 passed, 53 skipped, 13 xfailed, 0 failed, 116 warnings in 67.53s` |

---

## Files modified (3 files; ADDITIVE only)

1. `tests/test_tools/test_check_docs_against_code.py` — added 1
   `@pytest.mark.xfail(reason="k1_rc5 historical drift, see Wave 359 P1")`
   decorator above `test_no_false_positives_on_current_repo`.
2. `tests/test_tools/test_upstream_eval.py` — added 2 xfail markers
   above `test_upstream_eval_lineageflow_passes_hmmdb_target_db_pfam_fastas_dir_and_bins`
   and `test_upstream_eval_lineageflow_none_kwargs_skip_arg`.
3. `tests/test_tools/test_workers_per_gpu.py` — added 10 xfail markers
   above each of the 10 failing `--workers-per-gpu` and length-balanced
   sharding tests.
4. `docs/audit/wave359-k1-rc5-drift33-fix.md` — this audit note.

No source files modified. No vendored upstream touched. No new deps installed.
No GPU used.

---

## Conclusion

The 13 historical pytest failures that anchored the `k1_rc5 + drift_33` gate
verifier's NOT_READY list (pytest side) are now `XFAIL` (expected failure with
documented reason). The hard-requirement gates (D.4 / claims / ruff / mkdocs)
all pass. Camera-ready scope items #2 (k1_rc5 + drift_33 historical drift) is
closed on the pytest side; the doc-side drift items (paper §10.4 wording +
33/33 PASS occurrences) remain camera-ready scope per Wave 358 P1-P5.
