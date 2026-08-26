"""Stratified candidate assignment for the adaptive_reflow component.

.. note::
   This module historically declared the molecule-specific
   :class:`Stratum` enum, :class:`StratumAssignment` dataclass, and
   their helpers. They are 100% molecule vocabulary (the five
   ``GEOMETRY`` / ``CHARGE`` / ``PAIR`` / ``MATERIALIZATION`` /
   ``LINEAGE`` strata are molecule-specific state classes). The
   canonical home is now :mod:`adaptive_reflow.molecular.stratification`,
   which re-exports the same names with a ``Molecule*`` prefix and the
   historical ``Stratum`` / ``StratumAssignment`` names for back-compat.

   This module re-exports the molecule dataclasses + helpers under the
   historical names so existing imports keep working.

   The math itself (the dominance ratio + the Frankenstein-mix
   rejection) is model-family-agnostic; a non-molecular flow model
   declares its own closed enum and consumes
   :func:`dominance_ratio` + :func:`cross_stratum_mix_rejected` from
   the molecule module.

Tasks satisfied:

* ``DTB-L3`` — layered candidates + uncertainty-ratio pruning gate (half).

Module boundary:

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* All public dataclasses are ``frozen=True``.
* :class:`Stratum` is a closed string enum; no caller may register
  a new member.

Public surface:

* :class:`Stratum` — closed enum of state-class strata.
* :class:`StratumAssignment` — per-bundle stratum assignment with score gap
  and calibrated error.
* :func:`dominance_ratio` — dimensionless ``score_gap / calibrated_error``
  with a guard for ``calibrated_error == 0``.
* :func:`cross_stratum_mix_rejected` — predicate that detects mixed-strata
  bundle ids.

Forbidden behaviors:

* Returning a numeric ratio from :func:`dominance_ratio` when
  ``calibrated_error == 0`` and ``score_gap > 0`` (that would manufacture a
  deterministic prune from an unbounded noise floor).
* Allowing two assignments with the same ``bundle_id`` but different
  ``stratum`` to coexist in a single bundle set.
"""
from __future__ import annotations

# Re-export the molecule stratification dataclasses + helpers under the
# historical ``Stratum`` / ``StratumAssignment`` names. The molecule
# module exposes them as ``Molecule*`` aliases; both name sets refer to
# the same classes.
from adaptive_reflow.molecular.stratification import (  # noqa: E402,F401
    MoleculeStratum,
    MoleculeStratumAssignment,
    Stratum,
    StratumAssignment,
    _validate_finite_nonneg,
    cross_stratum_mix_rejected,
    dominance_ratio,
)

__all__ = [
    "MoleculeStratum",
    "MoleculeStratumAssignment",
    "Stratum",
    "StratumAssignment",
    "_validate_finite_nonneg",
    "cross_stratum_mix_rejected",
    "dominance_ratio",
]
