# Twelve failures that were not metric failures

**Date:** 2026-10-30
**Scope:** `tests/test_tools/test_paper_metrics.py`; the exact CI selection
`pytest tests/ -m "not slow and not benchmark"`.
**Status:** closed. The twelve failures were a test-ordering defect; no metric,
threshold, or assertion value was changed. No GPU was used.

---

## 1. The observation

Two runs of the same file disagreed:

```
pytest tests/test_tools/test_paper_metrics.py -q
    -> 15 passed

pytest tests/ -m "not slow and not benchmark" -q
    -> 12 failed, 5536 passed, 179 skipped, 50 deselected   (577 s)
```

All twelve were in that one file, and all twelve were the same shape:

```
assert 0.0 == 0.75 ± 1.0e-09
assert 0.0 == 0.92 ± 1.0e-09
assert 0.0 == 0.27 ± 1.0e-09
assert 0.0 == 0.99 ± 1.0e-09
DID NOT RAISE ValueError
```

Each was preceded by
`flowmol3_metrics_upstream: upstream import failed. error_type=ModuleNotFoundError error=No module named 'torch'`.

The `0.0` is the module's documented sentinel for "upstream unavailable", so
the assertion values (`0.75`, `0.92`, `0.27`, `0.99`) were never in question —
the mock simply was not reaching the code.

## 2. The cause

`tools/paper_metrics.py:110-114` binds four names at import time:

```python
from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    FLOWMOL3_PINNED_COMMIT,
    FLOWMOL3_UPSTREAM_REPO,
    is_upstream_available,
)
```

The fixture swapped `sys.modules["adaptive_reflow.adapters.flowmol3_metrics_upstream"]`
for a fake. That reaches a consumer that imports **lazily** — `_UPSTREAM_MODULES`
is imported inside a function at line 1071, so that part worked. It does not
reach a consumer that has already bound the names at module level. In a
single-file run the fixture's swap happens before `tools.paper_metrics` is
imported, so the import picks up the fake. In a full run some earlier test
imports `tools.paper_metrics` first, the real `is_upstream_available` is
bound, it returns `False` without torch, and every helper returns its
sentinel.

Reproduced deterministically in one process:

```bash
PYTHONPATH=. python3 -c "
import adaptive_reflow.adapters.flowmol3_metrics_upstream
import tools.paper_metrics
import pytest, sys
sys.exit(pytest.main(['tests/test_tools/test_paper_metrics.py','-q','-p','no:cacheprovider']))"
# before: 12 failed, 3 passed
```

## 3. The fix

`_install_mock_flowmol` now also patches the three names the helpers actually
call (`is_upstream_available`, `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR`,
`FLOWMOL3_UPSTREAM_REPO`). `FLOWMOL3_PINNED_COMMIT` is re-exported through
`__all__` and never called by a helper, so it is not patched — patching it
would have been cargo cult.

The same reproduction now gives `15 passed`, and the exact CI selection gives
`0 failed, 5545 passed, 179 skipped, 50 deselected`.

## 4. A second, unrelated falsehood in the same file

Six docstrings and comments said the vendored PoseBusters config lives at
`data/FlowMol3/pb_config_with_energy_ratio.yaml`. It does not, and it must
not: `data/FlowMol3/` is a vendored upstream tree pinned to `77cae22` and
guardrail 1 forbids editing it. The file is
`tools/pb_config_with_energy_ratio.yaml` — `PB_CONFIG_WITH_ENERGY_RATIO_PATH`
at `tools/paper_metrics.py:145-147` resolves there, and the path exists. The
six references were corrected; nothing else about them changed.

## 5. What this says about the gate

The suite was green in every configuration anyone ran deliberately. The
defect only appeared under the selection CI uses, which is the one selection
nobody runs locally. That is the same failure mode as the symlink round
(`clone-reproducibility.md`): the environment that would have shown it was
not the environment being tested.

| Run | Before | After |
|---|---|---|
| `test_paper_metrics.py` alone | 15 passed | 15 passed |
| `tests/ -m "not slow and not benchmark"` | 12 failed, 5536 passed | 0 failed, 5554 passed |
| `tests/` full CPU suite | 5582 passed, 180 skipped, 0 failed | 5603 passed, 180 skipped, 0 failed |

The CI selection gains 18: the 12 that were failing, plus 6 tests for the new
`check_reviewer_pointers` gate (`evidence-pointer-audit.md`). The full suite
gains 21, because 5582 was measured with `--ignore=tests/test_tools/test_paper_metrics.py`
— the file's 15 cases are now included and green, plus the same 6.
