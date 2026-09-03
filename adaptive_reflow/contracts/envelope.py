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
   names for back-compat. The re-export is **lazy** (via ``__getattr__``)
   to keep this module free of eager ``adaptive_reflow`` imports; the
   ``contracts`` ↔ ``molecular`` import cycle is sidestepped by
   deferring the molecular lookup until first attribute access. New
   code should import from :mod:`adaptive_reflow.molecular.envelope`
   (or the :mod:`adaptive_reflow.molecular` package) directly.

   The universal :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion`
   Protocol and :class:`EnvelopeClassification` live in
   :mod:`adaptive_reflow.universal.envelope`.

Stdlib-only at module load: no torch, no eager ``adaptive_reflow``
imports, no IO. The lazy ``__getattr__`` is the only escape hatch.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Names re-exported lazily from ``adaptive_reflow.molecular.envelope``.
# Both the historical names (``EnvelopeLayer`` / ``FrozenEnvelopeManifest``
# / ``EnvelopeClassification`` / ``TailBudgetRow`` + their validators)
# and the molecule-prefixed aliases are resolved on first access.
_LAZY_ENVELOPE_NAMES = frozenset(
    {
        "EnvelopeClassification",
        "EnvelopeLayer",
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
    }
)


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised via re-export
    """Lazy-load the molecule envelope dataclasses / validators.

    The first attribute access on this module that names one of the
    re-exported symbols triggers the ``adaptive_reflow.molecular.envelope``
    import. After resolution the value is cached in ``globals()`` so
    subsequent lookups are cheap and the module attribute is
    consistent with what the type checker sees via the ``TYPE_CHECKING``
    branch below.
    """
    if name in _LAZY_ENVELOPE_NAMES:
        from adaptive_reflow.molecular import envelope as _mol_envelope

        value = getattr(_mol_envelope, name)
        globals()[name] = value
        return value
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


if TYPE_CHECKING:  # pragma: no cover - typing only
    from adaptive_reflow.molecular.envelope import (  # noqa: F401
        EnvelopeClassification,
        EnvelopeLayer,
        FrozenEnvelopeManifest,
        MoleculeEnvelopeClassification,
        MoleculeEnvelopeLayer,
        MoleculeEnvelopeManifest,
        MoleculeTailBudgetRow,
        TailBudgetRow,
        validate_envelope_manifest,
        validate_molecule_envelope_manifest,
        validate_molecule_tail_budget_row,
        validate_tail_budget_row,
    )


__all__ = [
    "EnvelopeClassification",
    "EnvelopeLayer",
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
