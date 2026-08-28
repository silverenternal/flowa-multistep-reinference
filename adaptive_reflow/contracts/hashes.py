"""Adaptive reflow typed contracts — deterministic sha256 hash helpers.

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, fields
from typing import TYPE_CHECKING, Any

from .types import ArtifactHash, BundleId, RunId, SampleId, TraceDigest

if TYPE_CHECKING:
    from .authority import FinalRestartPolicy
    from .phase import PhaseState

# ---------------------------------------------------------------------------
# Hash helpers (deterministic, stdlib-only)
# ---------------------------------------------------------------------------


def _canonical_json(payload: Any) -> str:
    """Serialize ``payload`` to a deterministic JSON string."""
    return json.dumps(payload, sort_keys=True, default=_json_default)


def _json_default(obj: Any) -> Any:
    """Fallback serializer for non-JSON-native types (dataclasses, etc.)."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Mapping):
        return {k: v for k, v in obj.items()}
    if isinstance(obj, (tuple, list)):
        return [v for v in obj]
    if isinstance(obj, set):
        return sorted(v for v in obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


def hash_artifact(payload: Any) -> ArtifactHash:
    """Return a deterministic sha256 hex digest for ``payload``.

    ``payload`` may be any JSON-serializable structure or dataclass. Dataclasses
    are converted via ``dataclasses.asdict`` first, then the result is
    JSON-encoded with sorted keys and UTF-8 bytes before hashing.
    """
    if dataclasses.is_dataclass(payload) and not isinstance(payload, type):
        payload = asdict(payload)
    serialized = _canonical_json(payload)
    return ArtifactHash(hashlib.sha256(serialized.encode("utf-8")).hexdigest())


def hash_bundle_id(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> ArtifactHash:
    """Return the content-derived sha256 hex for a bundle identity.

    The five input fields match the canonical recompute used by
    :func:`hash_trace_digest`; the function is exposed under a distinct name so
    callers can use it semantically as a "bundle id".
    """
    payload = _bundle_identity_payload(bundle_id, source_round, round_count, run_id, sample_id)
    return hash_artifact(payload)


def hash_trace_digest(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> TraceDigest:
    """Return the deterministic trace digest for a ``RoundResultBundle``.

    The recompute rule is exactly the five-tuple ``(bundle_id, source_round,
    round_count, run_id, sample_id)``. ``RoundResultBundle.trace_digest`` must
    match the result of this function when validated.
    """
    payload = _bundle_identity_payload(bundle_id, source_round, round_count, run_id, sample_id)
    return TraceDigest(hash_artifact(payload))


def _bundle_identity_payload(
    bundle_id: BundleId,
    source_round: int,
    round_count: int,
    run_id: RunId,
    sample_id: SampleId,
) -> dict:
    return {
        "bundle_id": str(bundle_id),
        "source_round": int(source_round),
        "round_count": int(round_count),
        "run_id": str(run_id),
        "sample_id": str(sample_id),
    }


def hash_phase_state_digest(phase: PhaseState) -> ArtifactHash:
    """Return the deterministic ``phase_state_digest`` for ``phase``.

    The digest is the sha256 of every field on the ``PhaseState`` *except*
    ``phase_state_digest`` itself (to avoid circular hash).
    """
    payload = {
        f.name: getattr(phase, f.name)
        for f in fields(phase)
        if f.name != "phase_state_digest"
    }
    return hash_artifact(payload)


def hash_policy_hash(policy: FinalRestartPolicy) -> ArtifactHash:
    """Return the deterministic ``policy_hash`` for ``policy``.

    Recomputes from the canonical field tuple
    ``(policy_id, writer_id, run_id, target_round, outer_cycle_id,
    beta_by_channel, alpha_by_channel, fresh_noise_floor_by_channel,
    freeze_admission_by_channel, beta_from_schedule,
    driver_computed_beta)``.

    ``beta_from_schedule`` (ADR-0010) is included so two policies that
    differ only by the schedule-driven override flag hash differently.
    ``driver_computed_beta`` (Contract 1.2) is included so a policy
    whose driver has mutated ``beta_by_channel`` hashes differently
    from a policy whose ``beta_by_channel`` is the caller's verbatim
    value, preserving the audit invariant that the hash uniquely
    identifies the policy surface.
    """
    payload = {
        "policy_id": str(policy.policy_id),
        "writer_id": str(policy.writer_id),
        "run_id": str(policy.run_id),
        "target_round": int(policy.target_round),
        "outer_cycle_id": int(policy.outer_cycle_id),
        "beta_by_channel": _sorted_items(policy.beta_by_channel),
        "alpha_by_channel": _sorted_items(policy.alpha_by_channel),
        "fresh_noise_floor_by_channel": _sorted_items(
            policy.fresh_noise_floor_by_channel
        ),
        "freeze_admission_by_channel": _sorted_items(
            {k: bool(v) for k, v in policy.freeze_admission_by_channel.items()}
        ),
        "beta_from_schedule": bool(policy.beta_from_schedule),
        "driver_computed_beta": bool(policy.driver_computed_beta),
    }
    return hash_artifact(payload)


def _sorted_items(mapping: Mapping[Any, Any]) -> list:
    """Return ``mapping`` as a sorted list of ``[key, value]`` pairs."""
    return [[str(k), v] for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0]))]
