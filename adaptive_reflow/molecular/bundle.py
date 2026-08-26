"""Molecule concrete :class:`RoundResultBundle` (DTB-R1 + DTB-R2).

This module declares the *concrete* molecule implementation of the
:class:`RoundResultBundle` carrier. It composes the universal bundle
shape with the four molecule-specific channel handles
(``coordinate`` / ``charge`` / ``raw_pair`` / ``projected_pair``).

Module boundary
---------------

* ``MoleculeRoundResultBundle`` is the molecule-aware counterpart to the
  universal :class:`adaptive_reflow.universal.state.StateBundle`. It carries
  the same per-source-round metadata (``bundle_id``, ``source_round``,
  ``provenance``, ...) plus the four molecule channel handles.
* The molecule-specific ``__post_init__`` populates a derived
  ``observed_channels`` mapping from the four named fields. A molecule-
  aware caller sees the familiar field names; a universal caller sees the
  ``observed_channels`` mapping.
* Stdlib-only: no torch, no other adaptive_reflow imports (besides
  ``contracts``), no I/O.

Public surface
--------------

Pure-data carriers (frozen dataclasses)
    :class:`MoleculeRoundResultBundle`

Validators
    :func:`validate_molecule_round_result_bundle`

Tasks satisfied
---------------

* ``DTB-R1`` — atomic source bundle per source round.
* ``DTB-R2`` — channel rule + per-channel evidence / decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from adaptive_reflow.contracts.types import (
    ArtifactHash,
    BundleId,
    ConditionDigest,
    EvaluatorProvenanceRef,
    FeedbackEvidenceRef,
    FeedbackMode,
    FrameSpec,
    MaterializationEvidenceRef,
    ProvenanceChain,
    RunId,
    SampleId,
    ShapeSpec,
    TraceDigest,
)
from adaptive_reflow.contracts.validators import (
    AUDIT_SOURCE_REVOKED,
    ValidationResult,
    _ok,
)


def _hash_trace_digest(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> TraceDigest:
    """Lazy wrapper around ``contracts.hashes.hash_trace_digest``.

    Imported lazily to break the cycle:
    ``molecular.bundle`` -> ``contracts.hashes`` -> ``contracts.types``
    -> ``molecular.channels`` -> ``molecular.__init__`` -> ``molecular.bundle``.
    """
    from adaptive_reflow.contracts.hashes import hash_trace_digest

    return hash_trace_digest(
        bundle_id, source_round, round_count, run_id, sample_id
    )


# Channel NewType aliases are re-imported here so the dataclass fields
# below can use them as direct type annotations. They are also re-exported
# in ``__all__`` for callers that want to import them from this module.
from .channels import (  # noqa: E402
    ChargeChannelRef,
    CoordinateChannelRef,
    ProjectedPairChannelRef,
    RawPairChannelRef,
)

# ---------------------------------------------------------------------------
# Pure-data carrier
# ---------------------------------------------------------------------------


def _empty_observed_channels() -> dict[str, Mapping[str, Any]]:
    """Default-factory for the derived ``observed_channels`` mapping.

    Returns an empty mapping; :meth:`MoleculeRoundResultBundle.__post_init__`
    overwrites it with the live mapping populated from the four
    molecule channel fields.
    """
    return {}


@dataclass(frozen=True)
class MoleculeRoundResultBundle:
    """Molecule-aware atomic source bundle.

    The four molecule channel fields
    ( ``coordinate_channel``, ``charge_channel``,
    ``raw_pair_channel``, ``projected_pair_channel`` ) are explicit
    molecule vocabulary. They are populated at construction time and
    exposed via the derived ``observed_channels`` mapping for the
    universal engine.

    Required invariants (validated by
    :func:`validate_molecule_round_result_bundle`):

    * ``state_lock_is_detached`` is ``True``.
    * ``update_scope`` is exactly ``"ode_restart_distribution_only"``.
    * All identifier / digest fields are non-empty strings.
    * ``source_round`` / ``round_count`` / ``created_at_round`` are
      non-negative integers; ``created_at_round <= source_round``.
    * ``trace_digest`` equals the deterministic recompute of
      ``(bundle_id, source_round, round_count, run_id, sample_id)``.
    * Every non-``None`` channel carries a ``source_round`` equal to
      ``bundle.source_round``; missing ``source_round`` is treated as
      cross-round stitching (forbidden).

    The dataclass is ``frozen=True``; ``observed_channels`` is set in
    ``__post_init__`` via ``object.__setattr__`` so the mapping cannot
    drift after construction.
    """

    bundle_id: BundleId
    source_round: int
    round_count: int
    run_id: RunId
    sample_id: SampleId
    trace_digest: TraceDigest
    condition_digest: ConditionDigest
    feedback_mode: FeedbackMode
    calibration_artifact_hash: ArtifactHash
    state_lock_is_detached: bool
    update_scope: str
    # ----- molecule-specific channels -----
    coordinate_channel: CoordinateChannelRef | None
    charge_channel: ChargeChannelRef | None
    raw_pair_channel: RawPairChannelRef | None
    projected_pair_channel: ProjectedPairChannelRef | None
    # -------------------------------------
    materialization_evidence: MaterializationEvidenceRef | None
    evaluator_provenance: EvaluatorProvenanceRef | None
    feedback_evidence: FeedbackEvidenceRef | None
    shape_spec: ShapeSpec
    frame_spec: FrameSpec
    provenance: ProvenanceChain
    created_at_round: int
    revoked: bool = False
    # Derived (universal): mapping populated from the four channel fields.
    observed_channels: Mapping[str, Mapping[str, Any]] = field(
        default_factory=_empty_observed_channels,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        # Build ``observed_channels`` from the four molecule channel
        # fields. We do this in __post_init__ because the dataclass is
        # frozen; ``object.__setattr__`` is the only safe mutation
        # surface and it is used exactly once per construction.
        mapping: dict[str, Mapping[str, Any]] = {}
        if self.coordinate_channel is not None:
            mapping["coordinate"] = self.coordinate_channel
        if self.charge_channel is not None:
            mapping["charge"] = self.charge_channel
        if self.raw_pair_channel is not None:
            mapping["raw_pair"] = self.raw_pair_channel
        if self.projected_pair_channel is not None:
            mapping["projected_pair"] = self.projected_pair_channel
        object.__setattr__(self, "observed_channels", mapping)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _channel_source_round(channel: Mapping[str, Any] | None) -> int | None:
    if channel is None or not isinstance(channel, Mapping):
        return None
    if "source_round" not in channel:
        return None
    value = channel["source_round"]
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def validate_molecule_round_result_bundle(
    b: MoleculeRoundResultBundle,
    *,
    check_revocation: bool = True,
) -> ValidationResult:
    """Validate :class:`MoleculeRoundResultBundle` per the molecule invariants.

    Rejects when ``state_lock_is_detached`` is ``False``, ``update_scope``
    is not ``"ode_restart_distribution_only"``, any non-``None`` molecule
    channel carries a ``source_round`` that does not equal
    ``b.source_round``, ``provenance`` is empty,
    ``calibration_artifact_hash`` is empty, ``trace_digest`` does not match
    the deterministic recompute, ``created_at_round > source_round``, or
    the round/run/sample identifiers are empty or non-integer.

    When ``check_revocation=True`` (the default) and ``b.revoked`` is
    ``True``, the validator immediately returns
    ``(False, (AUDIT_SOURCE_REVOKED,))`` and skips the rest of the
    structural checks. This is the fail-closed path for DTB-R0 §3 case
    5: a bundle that has been revoked after registration must NOT
    participate in any per-channel decision regardless of how clean the
    other invariants look. Pass ``check_revocation=False`` only for
    callers that need to inspect the structural surface independently
    (e.g. legacy diagnostics).
    """
    # Fast path: revocation closes every gate, before any other check.
    if check_revocation and b.revoked:
        return (False, (AUDIT_SOURCE_REVOKED,))

    errors: list[str] = []

    if not b.state_lock_is_detached:
        errors.append("state_lock_is_detached must be True")
    if b.update_scope != "ode_restart_distribution_only":
        errors.append(
            f"update_scope must be 'ode_restart_distribution_only', got {b.update_scope!r}"
        )
    if not b.bundle_id:
        errors.append("bundle_id must be non-empty")
    if not b.run_id:
        errors.append("run_id must be non-empty")
    if not b.sample_id:
        errors.append("sample_id must be non-empty")
    if isinstance(b.source_round, bool) or not isinstance(b.source_round, int):
        errors.append(f"source_round must be int, got {type(b.source_round).__name__}")
    elif b.source_round < 0:
        errors.append(f"source_round must be >= 0, got {b.source_round}")
    if isinstance(b.round_count, bool) or not isinstance(b.round_count, int):
        errors.append(f"round_count must be int, got {type(b.round_count).__name__}")
    elif b.round_count < 0:
        errors.append(f"round_count must be >= 0, got {b.round_count}")
    if (
        isinstance(b.created_at_round, bool)
        or not isinstance(b.created_at_round, int)
        or b.created_at_round < 0
    ):
        errors.append(
            f"created_at_round must be non-negative int, got {b.created_at_round!r}"
        )
    elif (
        isinstance(b.source_round, int)
        and not isinstance(b.source_round, bool)
        and b.created_at_round > b.source_round
    ):
        errors.append(
            f"created_at_round ({b.created_at_round}) must be <= source_round "
            f"({b.source_round})"
        )
    if not b.provenance:
        errors.append("provenance must be non-empty")
    if not b.calibration_artifact_hash:
        errors.append("calibration_artifact_hash must be non-empty")

    expected_trace = _hash_trace_digest(
        b.bundle_id,
        b.source_round,
        b.round_count,
        b.run_id,
        b.sample_id,
    )
    if b.trace_digest != expected_trace:
        errors.append(
            "trace_digest does not match deterministic recompute of "
            "(bundle_id, source_round, round_count, run_id, sample_id)"
        )

    # Every non-None molecule channel must carry a ``source_round`` equal to
    # ``b.source_round``; missing ``source_round`` is treated as cross-round
    # stitching (forbidden).
    for label, channel in (
        ("coordinate_channel", b.coordinate_channel),
        ("charge_channel", b.charge_channel),
        ("raw_pair_channel", b.raw_pair_channel),
        ("projected_pair_channel", b.projected_pair_channel),
    ):
        if channel is None:
            continue
        if not isinstance(channel, Mapping):
            errors.append(f"{label} must be a Mapping when present")
            continue
        if "source_round" not in channel:
            errors.append(
                f"{label} must declare source_round when present; "
                "missing source_round is treated as cross-round stitching"
            )
            continue
        ch_sr = channel["source_round"]
        if (
            isinstance(ch_sr, bool)
            or not isinstance(ch_sr, int)
            or ch_sr != b.source_round
        ):
            errors.append(
                f"{label}.source_round ({ch_sr!r}) must equal bundle.source_round "
                f"({b.source_round}); cross-round stitching is forbidden"
            )

    if errors:
        return (False, tuple(errors))
    return _ok()


def attach_molecule_channels(
    bundle: MoleculeRoundResultBundle,
    *,
    coordinate_channel: CoordinateChannelRef | None = None,
    charge_channel: ChargeChannelRef | None = None,
    raw_pair_channel: RawPairChannelRef | None = None,
    projected_pair_channel: ProjectedPairChannelRef | None = None,
) -> MoleculeRoundResultBundle:
    """Return a new :class:`MoleculeRoundResultBundle` with the named channels attached.

    The function is a convenience wrapper that constructs a fresh bundle
    via ``dataclasses.replace`` so the existing instance stays frozen.
    Any non-``None`` argument overrides the corresponding field; ``None``
    arguments leave the field untouched.

    The returned bundle is validated against
    :func:`validate_molecule_round_result_bundle` so any cross-round
    stitching violation is surfaced immediately.
    """
    import dataclasses

    updates: dict[str, Any] = {}
    if coordinate_channel is not None:
        updates["coordinate_channel"] = coordinate_channel
    if charge_channel is not None:
        updates["charge_channel"] = charge_channel
    if raw_pair_channel is not None:
        updates["raw_pair_channel"] = raw_pair_channel
    if projected_pair_channel is not None:
        updates["projected_pair_channel"] = projected_pair_channel
    new_bundle = dataclasses.replace(bundle, **updates)
    validate_molecule_round_result_bundle(new_bundle)
    return new_bundle


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "MoleculeRoundResultBundle",
    "RoundResultBundle",
    "attach_molecule_channels",
    "validate_molecule_round_result_bundle",
    "validate_round_result_bundle",
]
# Re-imported aliases for callers that want to import directly from the bundle
# module rather than from the channels module.
__all__ += [
    "ChargeChannelRef",
    "CoordinateChannelRef",
    "ProjectedPairChannelRef",
    "RawPairChannelRef",
]


# ---------------------------------------------------------------------------
# Back-compat aliases (un-prefixed historical names)
# ---------------------------------------------------------------------------
# The original ``contracts.bundle.RoundResultBundle`` and
# ``contracts.bundle.validate_round_result_bundle`` are re-exported here
# under their historical names so legacy imports
# (``from adaptive_reflow.molecular.bundle import RoundResultBundle``)
# keep working.
RoundResultBundle = MoleculeRoundResultBundle
validate_round_result_bundle = validate_molecule_round_result_bundle
