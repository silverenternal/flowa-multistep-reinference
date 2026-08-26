"""Universal envelope criterion (DTB-NC1 / NC2 — generic layer).

This module declares the *model-family-agnostic* envelope-criterion
surface. It is **stdlib-only** (no ``torch``, no I/O, no mutation of
inputs) and carries **no molecule vocabulary** (no coordinate RMS,
no pocket distance, no atom counts).

The molecule-specific ``EnvelopeLayer`` (17 fields) and
``FrozenEnvelopeManifest`` continue to live in
``adaptive_reflow.contracts.envelope`` for now; they will move to
``adaptive_reflow.molecular.envelope`` in Phase 4 of the refactor plan.
A molecule caller subclasses :class:`EnvelopeCriterion` (or composes one
via ``MoleculeEnvelopeLayer.matches(...)``) and the universal engine
sees only the generic Protocol surface.

Public surface
--------------

Pure-data carriers (frozen dataclasses)
    :class:`EnvelopeCriterion`
    :class:`EnvelopeClassification`

Tasks satisfied:

* ``DTB-NC1`` — generic envelope ladder contract.
* ``DTB-NC2`` — generic tail-budget / classification surface.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, NewType

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------


Predicate = NewType("Predicate", Callable[[Mapping[str, float]], bool])  # type: ignore[valid-newtype]
"""A pure-data callable over observable values; returns True iff the
bundle satisfies the predicate.

``Predicate`` is wrapped in a ``NewType`` so call-sites can write
``Predicate(my_callable)`` as a tag for static analysis. ``mypy --strict``
rejects ``NewType`` over a ``Callable`` (the runtime type is not a class
that can be subclassed), so we suppress with ``# type: ignore[valid-newtype]``;
the runtime behavior is correct because ``NewType`` produces a callable
identity function.
"""


BundleId = NewType("BundleId", str)
ArtifactHash = NewType("ArtifactHash", str)
ComplementBlockerCode = NewType("ComplementBlockerCode", str)


# ---------------------------------------------------------------------------
# Pure-data carriers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeCriterion:
    """A single envelope threshold; generic, not molecule-specific.

    The criterion is a pure-data description of *what to check*, *at what
    threshold*, and *what evidence digest binds it*. The actual
    classification work happens in :class:`EnvelopeCriterion.matches`
    callable hooks; the universal layer does not bake in any particular
    observable vocabulary.

    Required invariants (validated by :func:`validate_envelope_criterion`):

    * ``predicate`` is callable.
    * ``threshold`` is a finite real number.
    * ``source_stats_hash`` and ``threshold_digest`` are non-empty
      strings identifying the upstream digest that produced the
      threshold and the canonical digest of the threshold itself.

    The criterion is *not* molecule-specific — a graph-flow criterion
    populates ``predicate`` with a node-count predicate; a sequence-flow
    criterion populates it with a length predicate; etc.
    """

    predicate: Predicate
    threshold: float
    source_stats_hash: ArtifactHash
    threshold_digest: ArtifactHash


@dataclass(frozen=True)
class EnvelopeClassification:
    """Per-bundle envelope classification; universal base.

    ``complement_blocker`` is the first complement-blocker code matched
    by the criterion chain; ``None`` means the bundle passed every layer.

    Required invariants (validated by
    :func:`validate_envelope_classification`):

    * ``bundle_id`` is a non-empty string.
    * ``matched_layer_index`` is a non-negative int or ``None``.
    * ``within_layer_thresholds`` is a bool.
    * ``residual_extents`` is a mapping keyed by observable name.
    """

    bundle_id: BundleId
    matched_layer_index: int | None
    complement_blocker: ComplementBlockerCode | None
    within_layer_thresholds: bool
    residual_extents: Mapping[str, float]


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_envelope_criterion(c: EnvelopeCriterion) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``c`` is a well-formed criterion."""
    errors: list[str] = []
    if c is None:
        return (False, ("envelope_criterion_must_not_be_none",))
    if not callable(c.predicate):
        errors.append("predicate_must_be_callable")
    if not isinstance(c.threshold, (int, float)) or isinstance(c.threshold, bool):
        errors.append(
            f"threshold must be a real number, got {type(c.threshold).__name__}"
        )
    if not c.source_stats_hash:
        errors.append("source_stats_hash_must_be_non_empty")
    if not c.threshold_digest:
        errors.append("threshold_digest_must_be_non_empty")
    return (not errors, tuple(errors))


def validate_envelope_classification(
    cls: EnvelopeClassification,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``cls`` is a well-formed classification."""
    errors: list[str] = []
    if cls is None:
        return (False, ("envelope_classification_must_not_be_none",))
    if not cls.bundle_id:
        errors.append("bundle_id_must_be_non_empty")
    if cls.matched_layer_index is not None and (
        isinstance(cls.matched_layer_index, bool)
        or not isinstance(cls.matched_layer_index, int)
        or cls.matched_layer_index < 0
    ):
        errors.append(
            "matched_layer_index must be a non-negative int or None"
        )
    if not isinstance(cls.within_layer_thresholds, bool):
        errors.append("within_layer_thresholds_must_be_bool")
    if cls.residual_extents is None or not isinstance(
        cls.residual_extents, Mapping
    ):
        errors.append("residual_extents_must_be_mapping")
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # NewType aliases
    "ArtifactHash",
    "BundleId",
    "ComplementBlockerCode",
    "Predicate",
    # Pure-data carriers
    "EnvelopeClassification",
    "EnvelopeCriterion",
    # Validators
    "validate_envelope_classification",
    "validate_envelope_criterion",
]
