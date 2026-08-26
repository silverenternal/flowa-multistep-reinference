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
   names for back-compat. New code should import from
   :mod:`adaptive_reflow.molecular.envelope` (or the
   :mod:`adaptive_reflow.molecular` package) directly.

   The universal :class:`adaptive_reflow.universal.envelope.EnvelopeCriterion`
   Protocol and :class:`EnvelopeClassification` live in
   :mod:`adaptive_reflow.universal.envelope`.

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

# Re-export the molecule envelope dataclasses + validators under the
# historical names. The molecule module also exposes them as
# ``Molecule*`` aliases; both name sets refer to the same dataclasses.
from adaptive_reflow.molecular.envelope import (  # noqa: E402
    EnvelopeClassification,
    EnvelopeLayer,
    FrozenEnvelopeManifest,
    MoleculeEnvelopeClassification,  # noqa: F401  (re-export for completeness)
    MoleculeEnvelopeLayer,  # noqa: F401  (re-export for completeness)
    MoleculeEnvelopeManifest,  # noqa: F401  (re-export for completeness)
    MoleculeTailBudgetRow,  # noqa: F401  (re-export for completeness)
    TailBudgetRow,
    validate_envelope_manifest,
    validate_molecule_envelope_manifest,  # noqa: F401  (re-export)
    validate_molecule_tail_budget_row,  # noqa: F401  (re-export)
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
