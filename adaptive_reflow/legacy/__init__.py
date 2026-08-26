"""Quarantined legacy ``adaptive_reflow`` modules (torch + pocket_modules bound).

Why this package still exists
----------------------------
These modules predate the typed-contracts refactor. They are bound to
``torch`` and to the upstream ``pocket_modules`` package, so they cannot
be type-checked or linted under the same rules as the rest of the tree
(see the ``adaptive_reflow/legacy/**`` per-file-ignores in
``pyproject.toml``). They are kept only so existing callers and the
upstream binding keep working until the migration plan retires them.

This subpackage is a **quarantine**, which means:

* nothing else under ``adaptive_reflow/`` imports from here;
* nothing here is part of the public surface;
* the re-export list is intentionally empty -- importing this package
  gives you no symbols, only a deprecation warning. Submodules must be
  imported explicitly (``from adaptive_reflow.legacy import plan``) so
  every legacy dependency is visible at the import site.

How to migrate off it
---------------------
Each legacy module has a typed replacement in the post-refactor tree.
Move to the equivalent subpackage rather than adding new imports here:

* ``legacy.loop`` / ``legacy.loop_contract`` / ``legacy.orchestration``
  -> ``adaptive_reflow.schedule`` and ``adaptive_reflow.universal``
* ``legacy.plan`` / ``legacy.services`` -> ``adaptive_reflow.contracts``
* ``legacy.control_policy`` / ``legacy.metric_feedback``
  -> ``adaptive_reflow.policy`` and ``adaptive_reflow.eval``
* ``legacy.mechanism_adapter`` -> ``adaptive_reflow.adapters``
* ``legacy.restart_mixer`` -> ``adaptive_reflow.universal`` mixers

New code must not import from this package at all. The dependency
direction rules and the retirement plan are documented in
ARCHITECTURE.md.
"""

from __future__ import annotations

import warnings as _warnings

__deprecation_marker__: str = "quarantine — see ARCHITECTURE.md"
"""Machine-readable marker that this package is quarantined, not public.
The docs scanner and the self-test in
``tests/test_universal/test_legacy_deprecation.py`` read this attribute
to confirm the quarantine is still declared."""

__deprecation_notice__: str = (
    "adaptive_reflow.legacy is quarantined (torch + pocket_modules bound). "
    "Nothing under adaptive_reflow/ imports from it and it exports no public "
    "symbols. Do not import from it in new code; migrate to the typed "
    "replacement subpackage listed in ARCHITECTURE.md."
)
"""Human-readable one-paragraph notice. Kept as a module constant (rather
than only a docstring) so the docs scanner and any status tooling can pick
the text up verbatim instead of re-deriving it."""

_warnings.warn(
    __deprecation_notice__,
    DeprecationWarning,
    stacklevel=2,
)

# Re-export is intentionally empty: this package has no back-compat
# surface to preserve. Callers that still need a legacy module import it
# by name, which keeps every remaining dependency grep-able. Do NOT add
# convenience re-exports here -- that would re-create the public surface
# the quarantine exists to remove.
__all__: list[str] = []
