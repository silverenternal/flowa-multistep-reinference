"""CLM-044: algorithm/ package is the largest subpackage.

Asserted by docs/CLAIMS.md:1568-1614.
The `adaptive_reflow/algorithm/` package owns the abstract algorithm
layer with the four substitution-point Protocols. CLM-044 claims the
package is the largest by file count (>= 25 modules, per the doc).

We pin:
    1. The package directory exists at the canonical path.
    2. The directory contains at least 25 .py modules (excluding
       `__pycache__` and `__init__.py`'s nothing-special case).
    3. The four substitution-point Protocols are importable from the
       canonical surfaces.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALGORITHM_DIR = ROOT / "adaptive_reflow" / "algorithm"


def test_claim_044_algorithm_package_exists() -> None:
    assert ALGORITHM_DIR.exists(), f"{ALGORITHM_DIR} missing"
    assert ALGORITHM_DIR.is_dir()


def test_claim_044_algorithm_package_has_at_least_25_modules() -> None:
    """CLM-044 claims the package is the largest with >= 25 modules."""
    py_files = [
        p for p in ALGORITHM_DIR.glob("*.py")
        if p.name != "__init__.py"
    ]
    assert len(py_files) >= 25, (
        f"algorithm/ has {len(py_files)} modules; expected >= 25"
    )


def test_claim_044_four_substitution_point_protocols_importable() -> None:
    """The four canonical Protocols are importable from their module
    surfaces (CLM-044 enumerates the algorithm layer's substitution
    axes)."""
    from adaptive_reflow.algorithm.blender import (  # noqa: F401
        RestartBlenderProtocol,
    )
    from adaptive_reflow.algorithm.merge_operator import (  # noqa: F401
        MergeOperatorProtocol,
    )
    from adaptive_reflow.algorithm.policy_driver import (  # noqa: F401
        PolicyDriverProtocol,
    )
    from adaptive_reflow.algorithm.scheduler._core import (  # noqa: F401
        SchedulerProtocol,
    )
    for cls in (
        SchedulerProtocol,
        MergeOperatorProtocol,
        PolicyDriverProtocol,
        RestartBlenderProtocol,
    ):
        assert cls is not None
