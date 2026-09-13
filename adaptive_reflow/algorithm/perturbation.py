"""Backward-compat shim — canonical module lives at :mod:`adaptive_reflow.algorithm.perturbation.perturbation`.

Wave 105 P2-C grouped the algorithm top-level into subpackages.
This shim preserves ``from adaptive_reflow.algorithm.perturbation import ...``
for downstream tools and tests.

Note: do not confuse this top-level shim with the
:mod:`adaptive_reflow.algorithm.perturbation` subpackage — both names exist
because Python's import system allows a module ``perturbation`` and a
subpackage ``perturbation/`` to coexist at the same level (the subpackage
takes precedence when imported as ``adaptive_reflow.algorithm.perturbation``).
"""

from __future__ import annotations

# Re-export from the canonical subpackage module. Downstream tools import
# the *top-level* ``adaptive_reflow.algorithm.perturbation`` shim (this file)
# while the framework itself uses the *subpackage* path
# ``adaptive_reflow.algorithm.perturbation.perturbation``. Because the
# subpackage name shadows the top-level module name in Python's import
# system, the canonical symbols are pulled from the subpackage via the
# bare module path.
from .perturbation import perturbation as _perturbation_module

# Forward *all* public names that downstream code references.
from .perturbation.perturbation import *  # noqa: F401,F403

# Forward helper submodules too (re-export their symbols at this top
# level so callers can continue using e.g.
# ``adaptive_reflow.algorithm.perturbation.UniformFreshPerturbation``).
from .perturbation.perturbation import (
    PaperQuantityAttractorInversion,
    UniformFreshPerturbation,
)

__all__ = getattr(_perturbation_module, "__all__", []) + [
    "UniformFreshPerturbation",
    "PaperQuantityAttractorInversion",
]
