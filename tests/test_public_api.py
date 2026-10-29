"""Every name in a module's ``__all__`` must actually resolve.

Two had drifted: ``adaptive_reflow.algorithm.__all__`` listed
``default_codimension_sheet_scheduler`` and
``adaptive_reflow.framework.interfaces.__all__`` listed ``AdapterCompliance``,
neither of which exists. Both were historical — the symbols were defined once
and later removed or replaced — and the second was even suppressed with
``# noqa: F822``, so ruff stayed quiet.

The cost is real: ``from module import *`` raises ``AttributeError``, and a
downstream reader who trusts ``__all__`` (or the docstring that described the
class) gets an ``ImportError``. Static ``__all__`` checking cannot see PEP 562
lazy re-exports, so this test imports each module and asks it directly.

Modules that need torch are skipped — the system interpreter has no torch, and
the suite already skips their tests for the same reason.
"""

from __future__ import annotations

import importlib
import pkgutil

import adaptive_reflow


def _walk():
    yield adaptive_reflow.__name__
    yield from (
        info.name
        for info in pkgutil.walk_packages(
            adaptive_reflow.__path__, prefix=adaptive_reflow.__name__ + "."
        )
    )


def test_every_all_entry_resolves() -> None:
    missing: list[str] = []
    imported = 0
    skipped = 0
    for name in _walk():
        try:
            module = importlib.import_module(name)
        except Exception:
            skipped += 1
            continue
        imported += 1
        missing.extend(
            f"{name}.{sym}" for sym in getattr(module, "__all__", ())
            if not hasattr(module, sym)
        )
    assert missing == [], missing
    assert imported > 150, imported
    assert skipped < 40, skipped
