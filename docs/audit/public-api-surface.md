# Public API surface — two exports that never existed

**Date:** 2026-10-29
**Scope:** every module under `adaptive_reflow/` that declares `__all__`
(240 modules), plus the 31 scripts in `reproduce/`.
**Status:** closed. No metric, claim, status label, or verdict changed; no GPU
was used.

---

## 1. Observed facts

**Two `__all__` entries do not resolve.**

```
adaptive_reflow.algorithm.__all__            -> default_codimension_sheet_scheduler
adaptive_reflow.framework.interfaces.__all__ -> AdapterCompliance
```

Both are historical. `default_codimension_sheet_scheduler` was introduced by
`55c6c3a2` ("Wave 34 Agent C: default scheduler = paper-quantity-driven") and
later removed from the package while the `__all__` entry stayed. The section
header in `algorithm/__init__.py` still lists it beside
`default_cosine_scheduler`, `default_euler_solver` and the other `default_*`
factories — all of which do resolve.

`AdapterCompliance` was defined in `ebc05502` ("Wave 11") and replaced by the
`implements` decorator plus `assert_adapter_compliance`; the class is gone, the
`__all__` entry stayed, the module docstring still described it as a class, and
the entry carried `# noqa: F822` — so ruff was explicitly told not to report
the undefined name.

Consequence: `from adaptive_reflow.algorithm import *` raises
`AttributeError`. A reader who follows `__all__` (or the docstring) gets an
`ImportError` for a symbol the package never had in this revision.

**`reproduce/` is clean.** All 31 scripts pass `bash -n`; every `python3
<path>.py` they invoke exists; every `--flag` on those command lines appears in
the target file. No fix was needed — this is recorded so the next audit does
not have to re-derive it.

## 2. What changed

- `adaptive_reflow/algorithm/__init__.py` — removed the
  `default_codimension_sheet_scheduler` entry.
- `adaptive_reflow/framework/interfaces.py` — removed the `AdapterCompliance`
  entry (and its `# noqa: F822`), replaced the docstring bullet with the two
  functions that actually implement that responsibility, and corrected the
  section header that still said "AdapterCompliance".

Neither symbol was importable before, so no caller can depend on them: this
removes a broken promise rather than an API.

## 3. The gate

`tests/test_public_api.py` imports every module under `adaptive_reflow/`,
walks `__all__`, and asserts each name resolves. Modules that need torch are
skipped (the system interpreter has none), which is why the test also asserts
`imported > 150` and `skipped < 40` — a gate that silently imports nothing
must fail.

Static checking is not enough here: several subpackages re-export through PEP
562 `__getattr__` (`algorithm/runner`, `algorithm/perturbation`, `policy`,
`contracts`), so an AST-only scan reports 17 false positives. The runtime
import is the only honest check.

The 12 modules that cannot be imported in this environment were checked
statically instead (definitions, imports, and lazy-export string tables): no
further dangling names.

## 4. Gates

| Gate | Result |
|---|---|
| `pytest tests/test_public_api.py` | 1 passed (240 modules walked, 202 imported) |
| full `pytest` (CPU, `test_paper_metrics` excluded) | 5541 passed / 180 skipped / 12 xfailed |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| 12-entry `todo.json` gate chain | all rc=0 |
