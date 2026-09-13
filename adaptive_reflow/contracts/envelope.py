"""Adaptive reflow typed contracts — envelope ladder (DTB-NC1/NC2).

.. note::
   This module historically declared the molecule-specific
   :class:`EnvelopeLayer`, :class:`FrozenEnvelopeManifest`,
   :class:`EnvelopeClassification`, and :class:`TailBudgetRow` dataclasses.
   They are 100% molecule vocabulary (coordinate_extent_rms_max,
   pocket_distance_max, atom_count_*, valence_rules_hash, ...); the
   canonical home is now :mod:`adaptive_reflow.molecular.envelope`,
   which re-exports them under both the ``Molecule*`` prefix and the
   historical names so existing imports keep working.

   This module re-exports the molecule dataclasses under the historical
   names for back-compat. The molecule import is now eager (the
   ``molecular → universal`` import cycle was severed by the local
   Protocol in ``molecular.calibration_protocols``); accessing any of
   the historical names emits a :class:`DeprecationWarning` pointing at
   the canonical home. New code should import from
   :mod:`adaptive_reflow.molecular.envelope` (or the
   :mod:`adaptive_reflow.molecular` package) directly.

   The universal :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion`
   Protocol and :class:`EnvelopeClassification` live in
   :mod:`adaptive_reflow.universal.envelope`.

Stdlib-only at module load: no torch, no eager ``adaptive_reflow``
imports other than the one-time ``molecular.envelope`` import.
"""
from __future__ import annotations

import warnings
from typing import Any

from adaptive_reflow.molecular.envelope import (  # noqa: F401
    EnvelopeClassification as _EnvelopeClassification,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    EnvelopeLayer as _EnvelopeLayer,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    FrozenEnvelopeManifest as _FrozenEnvelopeManifest,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    MoleculeEnvelopeClassification as _MoleculeEnvelopeClassification,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    MoleculeEnvelopeLayer as _MoleculeEnvelopeLayer,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    MoleculeEnvelopeManifest as _MoleculeEnvelopeManifest,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    MoleculeTailBudgetRow as _MoleculeTailBudgetRow,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    TailBudgetRow as _TailBudgetRow,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    validate_envelope_manifest as _validate_envelope_manifest,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    validate_molecule_envelope_manifest as _validate_molecule_envelope_manifest,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    validate_molecule_tail_budget_row as _validate_molecule_tail_budget_row,
)
from adaptive_reflow.molecular.envelope import (  # noqa: F401
    validate_tail_budget_row as _validate_tail_budget_row,
)

# ---------------------------------------------------------------------------
# DeprecationWarning re-exports — PEP 562 module-level shim pattern.
# ---------------------------------------------------------------------------
# ``EnvelopeLayer`` / ``FrozenEnvelopeManifest`` /
# ``EnvelopeClassification`` / ``TailBudgetRow`` (and the validators +
# ``Molecule*`` aliases) are canonical in
# ``adaptive_reflow.molecular.envelope``. Accessing them through this
# module (the historical ``adaptive_reflow.contracts.envelope`` path)
# emits a one-time :class:`DeprecationWarning` per name pointing at
# the canonical home. The warning is fired on the *attribute access*
# so static ``from adaptive_reflow.contracts import EnvelopeLayer``
# imports do NOT trigger the warning (they only bind the shim
# function); only callers that actually USE the symbol see the
# warning. This matches the existing
# ``eval.posterior_selection_evaluator`` shim idiom.
# ---------------------------------------------------------------------------


_CANONICAL_HOME = (
    "adaptive_reflow.molecular.envelope"
)


def _make_deprecated_alias(name: str, canonical_name: str, value: Any) -> Any:
    """Wrap ``value`` so the first *attribute access* emits a DeprecationWarning.

    ``from adaptive_reflow.contracts.envelope import X`` resolves to
    ``X`` as a module-level name; the warning only fires when the
    *caller* uses ``X`` (e.g. constructs it). The wrapper delegates
    ``__call__`` (for constructors / validators) and the regular
    attribute-access path through to the canonical value.
    """
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            (
                f"adaptive_reflow.contracts.envelope.{name} is deprecated; "
                f"import {canonical_name} from {_CANONICAL_HOME} instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return value(*args, **kwargs)

    _wrapper.__name__ = name
    _wrapper.__qualname__ = name
    _wrapper.__deprecated_name__ = name  # type: ignore[attr-defined]
    _wrapper.__canonical_name__ = canonical_name  # type: ignore[attr-defined]
    _wrapper.__wrapped__ = value  # type: ignore[attr-defined]
    return _wrapper


class _DeprecatedClassProxy:
    """Wraps a class so that construction emits a DeprecationWarning.

    Used for the molecule envelope dataclasses; constructing
    ``EnvelopeLayer(...)`` via the deprecated path emits the
    DeprecationWarning but still produces the canonical instance.
    """

    __slots__ = ("_name", "_canonical_name", "_wrapped")

    def __init__(self, name: str, canonical_name: str, wrapped: Any) -> None:
        self._name = name
        self._canonical_name = canonical_name
        self._wrapped = wrapped

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        warnings.warn(
            (
                f"adaptive_reflow.contracts.envelope.{self._name} is deprecated; "
                f"import {self._canonical_name} from {_CANONICAL_HOME} instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return self._wrapped(*args, **kwargs)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._wrapped, attr)

    def __repr__(self) -> str:
        return (
            f"<deprecated shim for {_CANONICAL_HOME}.{self._canonical_name}>"
        )


def _deprecated_class(
    name: str, canonical_name: str, value: Any
) -> _DeprecatedClassProxy:
    """Build a class-proxy that warns on construction."""
    return _DeprecatedClassProxy(name, canonical_name, value)


# Class shims — the canonical instances are reachable through the
# ``__getattr__`` proxy above; class-method access (e.g.
# ``EnvelopeLayer.__doc__``) is delegated.
EnvelopeLayer = _deprecated_class(
    "EnvelopeLayer", "MoleculeEnvelopeLayer", _EnvelopeLayer
)
EnvelopeManifest = _deprecated_class(
    "EnvelopeManifest", "MoleculeEnvelopeManifest", _MoleculeEnvelopeManifest
)
EnvelopeClassification = _deprecated_class(
    "EnvelopeClassification",
    "MoleculeEnvelopeClassification",
    _EnvelopeClassification,
)
TailBudgetRow = _deprecated_class(
    "TailBudgetRow", "MoleculeTailBudgetRow", _MoleculeTailBudgetRow
)
FrozenEnvelopeManifest = _deprecated_class(
    "FrozenEnvelopeManifest",
    "MoleculeEnvelopeManifest",
    _MoleculeEnvelopeManifest,
)
MoleculeEnvelopeLayer = _deprecated_class(
    "MoleculeEnvelopeLayer", "MoleculeEnvelopeLayer", _MoleculeEnvelopeLayer
)
MoleculeEnvelopeManifest = _deprecated_class(
    "MoleculeEnvelopeManifest",
    "MoleculeEnvelopeManifest",
    _MoleculeEnvelopeManifest,
)
MoleculeEnvelopeClassification = _deprecated_class(
    "MoleculeEnvelopeClassification",
    "MoleculeEnvelopeClassification",
    _MoleculeEnvelopeClassification,
)
MoleculeTailBudgetRow = _deprecated_class(
    "MoleculeTailBudgetRow", "MoleculeTailBudgetRow", _MoleculeTailBudgetRow
)


# Function shims — validators and other callables.
validate_envelope_manifest = _make_deprecated_alias(
    "validate_envelope_manifest",
    "validate_molecule_envelope_manifest",
    _validate_envelope_manifest,
)
validate_tail_budget_row = _make_deprecated_alias(
    "validate_tail_budget_row",
    "validate_molecule_tail_budget_row",
    _validate_tail_budget_row,
)
validate_molecule_envelope_manifest = _make_deprecated_alias(
    "validate_molecule_envelope_manifest",
    "validate_molecule_envelope_manifest",
    _validate_molecule_envelope_manifest,
)
validate_molecule_tail_budget_row = _make_deprecated_alias(
    "validate_molecule_tail_budget_row",
    "validate_molecule_tail_budget_row",
    _validate_molecule_tail_budget_row,
)


__all__ = [
    "EnvelopeClassification",
    "EnvelopeLayer",
    "EnvelopeManifest",
    "FrozenEnvelopeManifest",
    "MoleculeEnvelopeClassification",
    "MoleculeEnvelopeLayer",
    "MoleculeEnvelopeManifest",
    "MoleculeTailBudgetRow",
    "TailBudgetRow",
    "validate_envelope_manifest",
    "validate_molecule_envelope_manifest",
    "validate_molecule_tail_budget_row",
    "validate_tail_budget_row",
]
