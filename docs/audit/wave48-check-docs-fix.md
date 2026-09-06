# Wave 48 Agent A: `test_check_docs_against_code.py` push-blocker fix

**Date:** 2026-09-07
**Scope:** `tools/check_docs_against_code.py` (`PROSE_SYMBOL_DENYLIST` extension)
**Commit (no push):** see git log

## TL;DR

The two `tests/test_tools/test_check_docs_against_code.py` tests
(`test_no_false_positives_on_current_repo` and
`test_self_test_quiet_mode_returns_zero_exit`) were failing because
Wave 44 Agent D's paper Tier-3 writeup (`7fcabbe`) and Wave 45's
§15.13 followup introduced 23 inline-symbol references to 5 distinct
names that the AST symbol index cannot see (none of the 5 are
project-internal class / function names). Adding those 5 names to
`PROSE_SYMBOL_DENYLIST` fixes both tests with zero false positives.

## Background

The `tools/check_docs_against_code.py` doc-vs-code scanner walks every
markdown file under the repo (governance docs + `docs/`) and verifies
three kinds of claim:

1. Triple-backtick python fenced blocks (every ClassDef / FunctionDef /
   top-level assignment / ImportFrom alias mentioned in the snippet
   must be defined under `adaptive_reflow/`).
2. Path-style references (`adaptive_reflow/...` / `tests/...`) — the
   referenced file must exist on disk.
3. Inline-backtick CamelCase / SCREAMING_SNAKE_CASE identifiers whose
   payload looks like a project-internal class or constant.

The third class (inline-symbol) is verified against the AST symbol
index built by `_build_symbol_index`, which walks every `.py` file
under `adaptive_reflow/` + `tests/` + `tools/`. Anything in
`PROSE_SYMBOL_DENYLIST` is silently dropped before verification — this
set contains the typing stdlib names, common exceptions, third-party
ML model class names (`InceptionV3`, `FlowMol3`, `ProtBFNAbBFNModel`,
`Lumina`, `HiDream`, `Wan2`, `LineageFlowClassifier`), and assorted
prose / status-code pointers (`NOT_REPRODUCED`, `N_min`, `N_full`, ...).

## The 5 symbols introduced by Wave 44 / Wave 45

After running the failing test, the inline-symbol extractor reports
23 misses across 5 distinct names:

| Symbol | Occurrences | Source | Kind |
|---|---|---|---|
| `RUN_ERROR` | 11 | `tools/run_real_ckpt_eval.py:_aggregate_status` (inline return literal, not a top-level constant) + Wave 44 Agent D §15.12 + Wave 45 §15.13 + `README.md` Tier-3 paragraph | Status-code prose |
| `Long` | 6 | `torch.long` dtype, referenced as `Long`/`Int` token-id type in EsmModel encoder discussion | Third-party torch reference |
| `FloatTensor` | 2 | `torch.FloatTensor` (torch.Tensor subclass, `torch/_C/__init__.pyi:1952`), referenced in quoted PyTorch `RuntimeError` message | Third-party torch reference |
| `EsmModel` | 2 | HuggingFace `transformers.EsmModel`, referenced as the encoder that LineageFlowAdapter feeds `x_t` into | Third-party HF class |
| `Expected` | 2 | First word of the quoted PyTorch error message `"RuntimeError: Expected tensor for argument #1 'indices' to have one of the following scalar types: Long, Int; but got torch.FloatTensor instead (while checking arguments for embedding)"` | Prose sentence-starter |

Total: **23 inline-symbol misses → 5 distinct names to denylist.**

## Categorization

Each symbol was classified as one of:

* **(A) Real defined symbol that should be indexable** — would require
  extending `_build_symbol_index` roots (`collect_claims`). NONE of the
  5 fall in this bucket. `RUN_ERROR` is the closest candidate (it is
  a project-internal status code) but it lives only as an inline
  return literal inside `_aggregate_status()`; making it a top-level
  module constant would be a code change beyond the test-fix scope.
  All 5 are best handled by the existing `(B)` route.

* **(B) Ad-hoc prose / third-party / status-code that should be
  denylisted** — this is the fix path. All 5 symbols are added to
  `PROSE_SYMBOL_DENYLIST` in a single block at the end of the
  existing Wave 37 Agent D addition block, with a 22-line comment
  block explaining each entry's provenance and rationale (matches the
  pattern used by every prior wave's additions).

## Fix

`tools/check_docs_against_code.py:341` — append 5 entries to the
`PROSE_SYMBOL_DENYLIST` frozenset:

```python
"RUN_ERROR", "Long", "FloatTensor", "EsmModel", "Expected",
```

Each entry is preceded by a multi-line comment block explaining:

* `RUN_ERROR` — per-cell verdict status code returned inline by
  `tools/run_real_ckpt_eval.py:_aggregate_status`; denylisted
  alongside the existing `NOT_REPRODUCED` status-code entry.
* `Long` — `torch.long` dtype; third-party torch reference.
* `FloatTensor` — `torch.FloatTensor` tensor subclass
  (`torch/_C/__init__.pyi:1952`); third-party torch reference quoted
  inside a verbatim PyTorch error message.
* `EsmModel` — HuggingFace `transformers.EsmModel`; third-party HF
  class; denylisted alongside the existing `PreTrainedModel` /
  `PretrainedConfig` third-party entries.
* `Expected` — leading CamelCase word of a quoted PyTorch
  `RuntimeError` message; prose sentence-starter; denylisted alongside
  the existing `Today` / `Toward` / `Hence` / `Thereafter` /
  `Otherwise` prose-sentence-starter block.

No other file changes are needed. `collect_claims` already walks
`tools/` as a third symbol-index root (added by Wave 44 Group B to
fix the same pattern for `TIE_AT_SATURATION` and
`LineageFlowClassifier`), so denylist additions are sufficient.

## Verification

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_check_docs_against_code.py -q --tb=line

........                                                                 [100%]
8 passed, 2 warnings in 3.00s
```

Both target tests now pass:

* `test_no_false_positives_on_current_repo` — was reporting 23 missing
  claims; now reports 0.
* `test_self_test_quiet_mode_returns_zero_exit` — was returning exit
  code 1; now returns 0.

The remaining 6 tests in `tests/test_tools/test_check_docs_against_code.py`
were already passing and continue to pass (the denylist is purely
additive — no existing entries were removed or renamed).

## Files changed

* `tools/check_docs_against_code.py` — extended `PROSE_SYMBOL_DENYLIST`
  with 5 entries (`RUN_ERROR`, `Long`, `FloatTensor`, `EsmModel`,
  `Expected`) plus a 22-line comment block explaining each entry's
  rationale. Single-file diff, ~30 LOC added.
* `docs/audit/wave48-check-docs-fix.md` — this document.

No other files in the disjoint scope (other docs, `adaptive_reflow/`,
`tests/`, `tools/run_real_ckpt_eval.py`) were touched.

## Push readiness

This fix is part of the Wave 48 push-prep gate (4 pre-push pytest
failures). After this fix:

* `tests/test_tools/test_check_docs_against_code.py` — 8/8 passing
  (was 6/8 with 2 failures).
* Wave 48 Agent B / C / D own the remaining 2 push-blocker pytest
  failures (per Wave 48 orchestrator scope).

No code-under-test files (`adaptive_reflow/`, `tests/`, `tools/`
except `check_docs_against_code.py`) were modified — the fix is
limited to the doc-checker tool and its comment block, keeping the
blast radius minimal.