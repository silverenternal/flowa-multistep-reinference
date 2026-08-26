"""Self-test: the quarantined ``legacy`` subpackage must declare itself.

``adaptive_reflow/legacy/`` is a quarantine (torch + pocket_modules
bound, no public surface, retired file-by-file). This test pins the
three properties that make the quarantine machine-checkable rather than
prose-only:

1. the module-level ``__deprecation_marker__`` exists and names
   ARCHITECTURE.md as the authority;
2. a ``__deprecation_notice__`` string exists for the docs scanner and
   status tooling to pick up;
3. importing the package emits a ``DeprecationWarning`` and exposes no
   public symbols.

If someone quietly un-quarantines the package (drops the marker, adds
convenience re-exports), this test fails closed.
"""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest


def _reimport_legacy():
    """Import ``adaptive_reflow.legacy`` from scratch.

    The module-level warning only fires on first import, so a test that
    wants to observe it must evict the cached module first.
    """
    sys.modules.pop("adaptive_reflow.legacy", None)
    return importlib.import_module("adaptive_reflow.legacy")


class TestLegacyDeprecation:
    """The legacy subpackage must advertise its quarantine status."""

    def test_deprecation_marker_is_present(self) -> None:
        """``__deprecation_marker__`` must exist and be a non-empty string."""
        legacy = importlib.import_module("adaptive_reflow.legacy")
        marker = getattr(legacy, "__deprecation_marker__", None)
        assert isinstance(marker, str) and marker.strip(), (
            "adaptive_reflow.legacy must define a non-empty "
            "__deprecation_marker__ string"
        )

    def test_deprecation_marker_points_at_architecture_doc(self) -> None:
        """The marker must say "quarantine" and cite the governing doc."""
        legacy = importlib.import_module("adaptive_reflow.legacy")
        marker = legacy.__deprecation_marker__
        assert "quarantine" in marker.lower(), (
            f"marker must describe the package as a quarantine; got {marker!r}"
        )
        assert "ARCHITECTURE.md" in marker, (
            f"marker must cite ARCHITECTURE.md as the authority; got {marker!r}"
        )

    def test_deprecation_notice_is_present(self) -> None:
        """``__deprecation_notice__`` must exist for the docs scanner."""
        legacy = importlib.import_module("adaptive_reflow.legacy")
        notice = getattr(legacy, "__deprecation_notice__", None)
        assert isinstance(notice, str) and notice.strip(), (
            "adaptive_reflow.legacy must define a non-empty "
            "__deprecation_notice__ string"
        )
        assert "adaptive_reflow.legacy" in notice, (
            "the notice must name the package it describes"
        )

    def test_module_docstring_explains_the_quarantine(self) -> None:
        """The module docstring must explain why the package exists."""
        legacy = importlib.import_module("adaptive_reflow.legacy")
        doc = legacy.__doc__ or ""
        assert "quarantine" in doc.lower(), (
            "the legacy module docstring must describe the quarantine"
        )
        assert "ARCHITECTURE.md" in doc, (
            "the legacy module docstring must point readers at ARCHITECTURE.md"
        )

    def test_import_emits_deprecation_warning(self) -> None:
        """A fresh import of the package must emit a DeprecationWarning."""
        sys.modules.pop("adaptive_reflow.legacy", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.import_module("adaptive_reflow.legacy")
        messages = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert messages, (
            "importing adaptive_reflow.legacy must emit a DeprecationWarning"
        )
        assert any("adaptive_reflow.legacy" in m for m in messages), (
            f"the DeprecationWarning must name the package; got {messages!r}"
        )

    def test_package_exports_nothing(self) -> None:
        """``__all__`` must stay empty -- the quarantine has no public surface."""
        legacy = importlib.import_module("adaptive_reflow.legacy")
        assert legacy.__all__ == [], (
            "adaptive_reflow.legacy must not re-export any symbol; "
            f"got {legacy.__all__!r}"
        )

    @pytest.mark.parametrize(
        "attr",
        ["__deprecation_marker__", "__deprecation_notice__"],
    )
    def test_marker_attributes_survive_reimport(self, attr: str) -> None:
        """Both constants must be present on a from-scratch import too."""
        legacy = _reimport_legacy()
        assert hasattr(legacy, attr), (
            f"adaptive_reflow.legacy lost {attr} on re-import"
        )
