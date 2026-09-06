# Wave 44 Group B — doc-regression push-blocker fix

**Date:** 2026-09-07
**Agent:** Wave 44 Agent B
**Scope:** Wave 44 WF1 (push-blockers fix, Group B)
**Files touched:** `tools/run_real_ckpt_eval.py`, `tools/check_docs_against_code.py`
**Status:** DONE — both doc-regression tests in
`tests/test_tools/test_check_docs_against_code.py` now pass.

## Background

Wave 43 WF2 Agent C surfaced two doc-regression failures in
`tests/test_tools/test_check_docs_against_code.py`:

1. `TIE_AT_SATURATION` was used as a code-symbol claim in `README.md`,
   `CONSOLIDATED_RESULTS.md`, and `paper-draft.md`, but it existed only as
   a string literal inside `tools/run_real_ckpt_eval.py`. The inline
   extractor therefore could not find a project-internal symbol and
   flagged every reference as `missing`.

2. `LineageFlowClassifier` was referenced as a proper noun in
   `docs/CONSOLIDATED_RESULTS.md` §15.2 (the real-ckpt LineageFlow
   eval) but was not in the `PROSE_SYMBOL_DENYLIST`. The class is an
   *upstream* symbol imported by
   `tools/run_lineageflow_real_ckpt.py:94` (`from models.model import
   LineageFlowClassifier`), not a project-internal class.

These two failures together produced 11 missing claims across 3 docs
and 2 test functions.

## Fix

### 1. Promote `TIE_AT_SATURATION` to a module-level constant

In `tools/run_real_ckpt_eval.py`, added a module-level constant
alongside the existing `REPO_ROOT` / `ENV_HASH_FILE` / `CAPABILITY_AUDIT`
constants:

```python
#: Cell-level status literal used when both arms sit at the saturation
#: ceiling (...). Promoted to a module-level constant so the governance
#: docs and the inline symbol extractor see it as a real, defined
#: project symbol rather than a bare string literal.
TIE_AT_SATURATION: str = "TIE_AT_SATURATION"
```

Replaced the three string-literal uses with the constant reference
(lines 1133 / 1179 / 1269 — the per-cell status assignment, the
`n_tie_sat` count in `build_report`, and the `_overall_verdict`
fallback return).

The promotion alone is not enough: the inline symbol extractor only
indexes `adaptive_reflow/` and `tests/`, not `tools/`. So the
companion change in `tools/check_docs_against_code.py` was required.

### 2. Index `tools/` in the doc-verification symbol pass

In `tools/check_docs_against_code.py:collect_claims`, added
`REPO_ROOT / "tools"` as a third root passed to `_build_symbol_index`:

```python
tools_root_path = REPO_ROOT / "tools"
code_symbols = _build_symbol_index(
    CODE_ROOT, tests_root_path, tools_root_path
)
```

This is the structural fix that makes the symbol extractor see
module-level constants and class / function / assignment names defined
anywhere in `tools/`. It does not require every `tools/*.py` file to
be re-exported through `adaptive_reflow/`, and it does not require
manual denylisting for every new constant the doc prose wants to
reference inline.

This is the right fix rather than a denylist entry because the
constant is a real, defined project symbol — the denylist would mask
a genuine codebase claim.

### 3. Add `LineageFlowClassifier` to the `PROSE_SYMBOL_DENYLIST`

`LineageFlowClassifier` is *not* a project-internal class; it lives in
the upstream `github.com/Jinx-byebye/LineageFlow` package
(`models/model.py`). The `from models.model import
LineageFlowClassifier` in `tools/run_lineageflow_real_ckpt.py:94` is a
sys.path-based import, not a class definition. AST-walking
`_build_symbol_index` therefore cannot find the class definition, even
with the new `tools/` index. The denylist entry is the correct
mechanism for upstream / external model class names.

Added to the third-party model class block in `PROSE_SYMBOL_DENYLIST`:

```python
"LineageFlowClassifier",
```

The denylist entry sits next to `FlowMol3`, `ProtBFNAbBFNModel`,
`Lumina`, `HiDream`, `Wan2`, `Alpha`, `Image`, `MMseqs2`, `Heun`,
`Midpoint` — all the other upstream model / integrator names the
governance prose references as proper nouns.

## Verification

```text
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_tools/test_check_docs_against_code.py -q --tb=line
........                                                                 [100%]
8 passed, 2 warnings in 2.99s
```

Both `test_no_false_positives_on_current_repo` and
`test_self_test_quiet_mode_returns_zero_exit` now pass. The 6
earlier-passing tests still pass.

## Notes / caveats

* The other status strings (`BLOCKED`, `PENDING`, `REGRESSION`,
  `SUPPORTED`, `MEASURED`, `RUN_ERROR`, `TIE`) are *not* used as
  inline-symbol claims in the governance docs (only the saturation
  variant `TIE_AT_SATURATION` is), so they remain string literals.
  If a future doc claim references one of them, the same
  promote-to-constant + `tools/` index pattern will resolve it.
* `_build_symbol_index` only walks `ast.Assign`, `ast.AnnAssign`,
  `ast.ClassDef`, `ast.FunctionDef`, and `ast.AsyncFunctionDef` —
  it does not pick up `ast.ImportFrom` aliases. This is why
  `LineageFlowClassifier` (an `ImportFrom` alias) needed a denylist
  entry rather than a tools/-index entry.
* `tests/test_tools/test_check_docs_against_code.py` was not
  modified; both tests passed against the existing behavior
  contract.
