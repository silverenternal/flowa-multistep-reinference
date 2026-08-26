"""Molecule stratified candidate assignment (DTB-L3 — molecule half).

This module implements the molecule-specific half of the layered candidate
and uncertainty-ratio pruning gate. Endpoints are partitioned into
disjoint state-class strata (geometry, charge support, pair topology
support, materialization status, condition lineage). Different strata
MUST NOT mix into a single restart bundle; the gate's role is to refuse
such "Frankenstein" combinations and to provide a deterministic dominance
ratio per stratum that the :mod:`adaptive_reflow.policy.pruning` module
can use to decide whether to keep, prune, or preserve unordered branches.

Module boundary
---------------

* This is the molecule-specific concrete implementation. The math itself
  (the dominance ratio + the Frankenstein-mix rejection) is model-family-
  agnostic and is consumed unchanged by :mod:`adaptive_reflow.policy.pruning`.
  A non-molecular flow model that wants stratification declares its own
  closed enum and registers an :class:`UnorderedAuditResult` per stratum
  kind.
* Stdlib-only. No torch. No I/O. No mutation of inputs.
* All public dataclasses are ``frozen=True``.
* :class:`MoleculeStratum` is a closed string enum; no caller may register
  a new member.

Public surface
--------------

* :class:`MoleculeStratum` — closed enum of state-class strata.
* :class:`MoleculeStratumAssignment` — per-bundle stratum assignment with
  score gap and calibrated error.
* :func:`dominance_ratio` — dimensionless ``score_gap / calibrated_error``
  with a guard for ``calibrated_error == 0``.
* :func:`cross_stratum_mix_rejected` — predicate that detects mixed-strata
  bundle ids.

Forbidden behaviors
-------------------

* Returning a numeric ratio from :func:`dominance_ratio` when
  ``calibrated_error == 0`` and ``score_gap > 0`` (that would manufacture a
  deterministic prune from an unbounded noise floor).
* Allowing two assignments with the same ``bundle_id`` but different
  ``stratum`` to coexist in a single bundle set.

Tasks satisfied
---------------

* ``DTB-L3`` — layered candidates + uncertainty-ratio pruning gate (half).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from adaptive_reflow.contracts.types import BundleId, FactorValue

__all__ = [
    "MoleculeStratum",
    "MoleculeStratumAssignment",
    "Stratum",
    "StratumAssignment",
    "_validate_finite_nonneg",
    "cross_stratum_mix_rejected",
    "dominance_ratio",
]


# ---------------------------------------------------------------------------
# MoleculeStratum enum (frozen, closed)
# ---------------------------------------------------------------------------


class MoleculeStratum(Enum):
    """Closed enum of molecule state-class strata.

    The members and their string values are frozen at module load. The
    ``value`` strings are the wire format used in ledger rows and tests.

    * ``GEOMETRY`` — continuous geometry / reference frame state.
    * ``CHARGE`` — atom & formal-charge support state.
    * ``PAIR`` — pair/topology support state (raw + projected pair).
    * ``MATERIALIZATION`` — materialization status state.
    * ``LINEAGE`` — condition lineage state.
    """

    GEOMETRY = "continuous_geometry"
    CHARGE = "atom_charge_support"
    PAIR = "pair_topology_support"
    MATERIALIZATION = "materialization_status"
    LINEAGE = "condition_lineage"


_STRATUM_VALUE_SET: frozenset[str] = frozenset(m.value for m in MoleculeStratum)


# ---------------------------------------------------------------------------
# MoleculeStratumAssignment (frozen, dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MoleculeStratumAssignment:
    """A bundle's stratum assignment with its score gap and calibrated error.

    Attributes
    ----------
    bundle_id:
        Identifier of the source bundle being assigned. Must be non-empty.
    stratum:
        The stratum this bundle belongs to. One and only one.
    score_gap:
        Non-negative dominance gap (best - second-best) within the stratum.
        Must be finite and ``>= 0``. ``FactorValue`` wrapper.
    calibrated_error:
        Non-negative calibrated uncertainty radius. Must be finite and
        ``>= 0``. ``FactorValue`` wrapper. When ``0``, the dominance ratio
        is undefined (see :func:`dominance_ratio`).
    """

    bundle_id: BundleId
    stratum: MoleculeStratum
    score_gap: FactorValue
    calibrated_error: FactorValue


# Back-compat aliases: historical (un-prefixed) names map to the molecule
# classes. This keeps ``from adaptive_reflow.molecular import Stratum``
# working for legacy callers.
Stratum = MoleculeStratum
StratumAssignment = MoleculeStratumAssignment


def _validate_finite_nonneg(value: FactorValue, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            f"{name} must be a real number, got {type(value).__name__}"
        )
    fv = float(value)
    if not math.isfinite(fv):
        raise ValueError(f"{name} must be finite, got {fv!r}")
    if fv < 0.0:
        raise ValueError(f"{name} must be >= 0, got {fv!r}")


def _coerce_assignment(value: object) -> MoleculeStratumAssignment:
    """Defensive coercion used by public helpers.

    Re-validates the dataclass fields so a caller cannot smuggle in
    non-finite or negative values via ``dataclasses.replace``.
    """
    if not isinstance(value, MoleculeStratumAssignment):
        raise ValueError(
            f"expected MoleculeStratumAssignment, got {type(value).__name__}"
        )
    if not isinstance(value.stratum, MoleculeStratum):
        raise ValueError(
            f"stratum must be a MoleculeStratum member, got {value.stratum!r}"
        )
    if value.stratum.value not in _STRATUM_VALUE_SET:
        raise ValueError(
            f"stratum value {value.stratum.value!r} is not a registered member"
        )
    if not str(value.bundle_id):
        raise ValueError("bundle_id must be non-empty")
    _validate_finite_nonneg(value.score_gap, "score_gap")
    _validate_finite_nonneg(value.calibrated_error, "calibrated_error")
    return value


# ---------------------------------------------------------------------------
# dominance_ratio (gated for calibrated_error == 0)
# ---------------------------------------------------------------------------


def dominance_ratio(
    score_gap: FactorValue,
    calibrated_error: FactorValue,
) -> FactorValue:
    """Return the dimensionless ``score_gap / calibrated_error`` ratio.

    The gate is fail-closed:

    * If ``calibrated_error == 0`` and ``score_gap == 0`` the ratio is
      ``0.0`` (no gap to dominate, no uncertainty to bound it).
    * If ``calibrated_error == 0`` and ``score_gap > 0`` the ratio is
      ``+inf`` (an infinite dominance margin means the calibrated error is
      too small to bound it; downstream callers must NOT treat this as a
      deterministic prune — see :class:`pruning_gate.PruneGate`).
    * If either value is non-finite or negative, :class:`ValueError` is
      raised.
    * If both are zero, returns ``0.0``.

    The ``+inf`` branch is the load-bearing safeguard that prevents the
    prune gate from ever silently manufacturing a winner when the
    uncertainty floor is not pinned. Callers that wish to forbid this
    branch must check ``calibrated_error == 0`` before invoking.
    """
    _validate_finite_nonneg(score_gap, "score_gap")
    _validate_finite_nonneg(calibrated_error, "calibrated_error")

    gap = float(score_gap)
    err = float(calibrated_error)

    if err == 0.0:
        if gap == 0.0:
            return FactorValue(0.0)
        return FactorValue(math.inf)

    ratio = gap / err
    return FactorValue(ratio)


# ---------------------------------------------------------------------------
# cross_stratum_mix_rejected
# ---------------------------------------------------------------------------


def cross_stratum_mix_rejected(
    assignments: Iterable[MoleculeStratumAssignment | object]
    | Mapping[BundleId, MoleculeStratumAssignment | object],
) -> bool:
    """Return True iff the bundle set mixes different strata.

    The check accepts either an iterable of :class:`MoleculeStratumAssignment`
    objects or a mapping keyed by ``bundle_id``. The function:

    * Coerces each entry through :func:`_coerce_assignment` so partial or
      corrupted inputs are rejected with :class:`ValueError` instead of
      silently passing the gate.
    * Refuses duplicate ``bundle_id`` (the same bundle cannot belong to
      two strata).
    * Returns ``True`` if two assignments for the same ``bundle_id``
      disagree on ``stratum`` (cross-stratum Frankenstein mix).

    Returns ``False`` when the input is consistent: every ``bundle_id``
    appears at most once, and either all assignments live in a single
    stratum or the bundle ids are disjoint across strata.

    Note: ``True`` means "the input MUST be rejected — do not form a
    Frankenstein bundle out of these assignments".
    """
    seen_bundle_ids: dict[BundleId, MoleculeStratum] = {}

    if isinstance(assignments, Mapping):
        items = list(assignments.items())
        for bundle_id, raw in items:
            if not str(bundle_id):
                raise ValueError("bundle_id must be non-empty")
            coerced = _coerce_assignment(raw)
            if coerced.bundle_id != bundle_id:
                raise ValueError(
                    "mapping key bundle_id does not match "
                    f"assignment.bundle_id (key={bundle_id!r}, "
                    f"assignment={coerced.bundle_id!r})"
                )
            if _bundle_disagrees(bundle_id, coerced.stratum, seen_bundle_ids):
                return True
    else:
        for raw in assignments:
            coerced = _coerce_assignment(raw)
            if _bundle_disagrees(
                coerced.bundle_id, coerced.stratum, seen_bundle_ids
            ):
                return True

    return False


def _bundle_disagrees(
    bundle_id: BundleId,
    stratum: MoleculeStratum,
    seen: dict[BundleId, MoleculeStratum],
) -> bool:
    """Record ``(bundle_id, stratum)`` and return True iff it disagrees.

    Idempotent re-adds of the same (bundle_id, stratum) pair return False.
    """
    if bundle_id in seen:
        existing = seen[bundle_id]
        return existing is not stratum
    seen[bundle_id] = stratum
    return False
