"""Versioned per-round provenance and condition-trace evidence (DTB-R5).

This module introduces the v3 condition-trace schema and a v2 reader. It is
the single source of truth for "what happened on this round" as far as
reproducibility is concerned. Every non-zero ``beta_by_channel`` consumed by
``flowa_core_runtime`` must be reproducible from the single
``DynamicRestartTransferLedger`` row recorded here; the writer that produced
the row is recorded in ``final_policy_writer``.

The module is stdlib-only: no torch, no IO, no imports from sibling adaptive_reflow
modules other than the dataclass carriers and validators in
``restart_memory_types``. Behaviour (orchestration, mixing) is downstream.

Versioning contract
-------------------

* v2 (legacy) — ``flowa_iterative_ode_condition_trace_schema_v2`` payload as
  produced by ``flowa_iterative_ode`` upstream. ``read_round_trace_v2()`` is
  the only reader; it does *not* mutate the v3 surface.
* v3 (this module) — adds per-round provenance + condition-trace evidence:
  per-factor raw/bounded splits, calibration hash, producer identity, dual-
  writer arbitration, and a stable canonical hash.

Hashing
-------

``round_trip_round_trace_v3`` recomputes the deterministic content hash over
the canonical field tuple and rejects traces whose embedded hash disagrees.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Schema version constants (single source of truth)
# ---------------------------------------------------------------------------

ROUND_TRACE_V2_SCHEMA_NAME = "flowa_iterative_ode_condition_trace_schema_v2"
ROUND_TRACE_V3_SCHEMA_NAME = "flowa_iterative_ode_condition_trace_schema_v3"

PRODUCER_MODES: tuple[str, ...] = (
    "diagnostic_only",
    "legacy_standalone",
    "adaptive_reflow_executable",
    "flowa_core_consumer",
)

FINAL_POLICY_WRITER_ADAPTIVE_REFLOW = "adaptive_reflow"
FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS = "noise_bias"
ALLOWED_FINAL_POLICY_WRITERS: tuple[str, ...] = (
    FINAL_POLICY_WRITER_ADAPTIVE_REFLOW,
    FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS,
)


# ---------------------------------------------------------------------------
# Carriers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundTraceV3:
    """Versioned per-round provenance and condition-trace evidence (DTB-R5).

    The schema is closed: any addition requires a new schema name. The fields
    below are exactly what is required by the v3 acceptance contract:

    * ``per_factor_raw`` / ``per_factor_bounded`` — the pre/post-calibration
      split for every factor that contributed to ``beta_by_channel``.
    * ``alpha_by_channel`` / ``beta_by_channel`` — the final, post-calibration
      restart distribution and per-channel restart weight.
    * ``fresh_noise_floor_by_channel`` — per-channel schedule or calibration
      floor that gates the restart write mass.
    * ``final_policy_writer`` — sole executable writer identity; the trace
      refuses to record two executable writers coexisting.
    * ``producer_id`` / ``producer_mode`` — which mechanism produced the
      trace row and under which authority mode.
    * ``hashes.content_hash`` — sha256 of every other field on the dataclass,
      round-trippable.
    """

    round_index: int
    source_bundle_id: str
    source_round: int
    selected_bundle_id: str | None
    rejected_bundle_ids: tuple[str, ...]
    per_factor_raw: Mapping[str, float]
    per_factor_bounded: Mapping[str, float]
    alpha_by_channel: Mapping[str, float]
    beta_by_channel: Mapping[str, float]
    fresh_noise_floor_by_channel: Mapping[str, float]
    calibration_artifact_hash: str
    feedback_mode: str
    producer_id: str
    producer_mode: Literal[
        "diagnostic_only",
        "legacy_standalone",
        "adaptive_reflow_executable",
        "flowa_core_consumer",
    ]
    was_adopted: bool
    final_policy_writer: Literal["adaptive_reflow", "noise_bias"]
    blockers: tuple[str, ...]
    acceptance_reason: str
    operation_order_version: str
    created_at_round: int
    schema_name: str = ROUND_TRACE_V3_SCHEMA_NAME
    hashes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # ``hashes`` is the only mutable-shaped default (Mapping). We accept
        # either a Mapping or a sequence of (key, value) pairs and normalise
        # it to a dict so callers using ``dataclasses.replace`` get a sane
        # field shape. The canonical hash payload sorts keys deterministically.
        if isinstance(self.hashes, Mapping):
            normalised = {str(k): str(v) for k, v in self.hashes.items()}
        else:
            try:
                normalised = {str(k): str(v) for k, v in self.hashes}
            except TypeError as exc:
                raise TypeError("hashes must be a Mapping or a sequence of pairs") from exc
        object.__setattr__(self, "hashes", normalised)
        if self.schema_name != ROUND_TRACE_V3_SCHEMA_NAME:
            raise ValueError(
                f"RoundTraceV3 schema_name must be {ROUND_TRACE_V3_SCHEMA_NAME!r}; "
                f"got {self.schema_name!r}"
            )
        if self.producer_mode not in PRODUCER_MODES:
            raise ValueError(
                f"producer_mode must be one of {PRODUCER_MODES}; got {self.producer_mode!r}"
            )
        if self.final_policy_writer not in ALLOWED_FINAL_POLICY_WRITERS:
            raise ValueError(
                f"final_policy_writer must be one of {ALLOWED_FINAL_POLICY_WRITERS}; "
                f"got {self.final_policy_writer!r}"
            )


# ---------------------------------------------------------------------------
# Canonical hashing
# ---------------------------------------------------------------------------


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, default=_json_default)


def _json_default(obj: Any) -> Any:
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


def _trace_payload_for_hash(trace: RoundTraceV3) -> dict[str, Any]:
    """Return the canonical, hashable payload for ``trace``.

    Excludes ``hashes`` itself so the digest can be embedded without a
    circular dependency, and coerces every Mapping field to a deterministic
    key-sorted representation.
    """

    def _coerce_mapping(mapping: Mapping[str, float]) -> list[list[Any]]:
        return [[str(k), float(v)] for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0]))]

    return {
        "round_index": int(trace.round_index),
        "source_bundle_id": str(trace.source_bundle_id),
        "source_round": int(trace.source_round),
        "selected_bundle_id": (
            None if trace.selected_bundle_id is None else str(trace.selected_bundle_id)
        ),
        "rejected_bundle_ids": [str(b) for b in trace.rejected_bundle_ids],
        "per_factor_raw": _coerce_mapping(trace.per_factor_raw),
        "per_factor_bounded": _coerce_mapping(trace.per_factor_bounded),
        "alpha_by_channel": _coerce_mapping(trace.alpha_by_channel),
        "beta_by_channel": _coerce_mapping(trace.beta_by_channel),
        "fresh_noise_floor_by_channel": _coerce_mapping(trace.fresh_noise_floor_by_channel),
        "calibration_artifact_hash": str(trace.calibration_artifact_hash),
        "feedback_mode": str(trace.feedback_mode),
        "producer_id": str(trace.producer_id),
        "producer_mode": str(trace.producer_mode),
        "was_adopted": bool(trace.was_adopted),
        "final_policy_writer": str(trace.final_policy_writer),
        "blockers": [str(b) for b in trace.blockers],
        "acceptance_reason": str(trace.acceptance_reason),
        "operation_order_version": str(trace.operation_order_version),
        "created_at_round": int(trace.created_at_round),
        "schema_name": str(trace.schema_name),
    }


def compute_round_trace_v3_content_hash(trace: RoundTraceV3) -> str:
    """Return the deterministic sha256 content digest of ``trace``.

    Stable across Python versions and independent of mapping ordering.
    """

    payload = _trace_payload_for_hash(trace)
    serialized = _canonical_json(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Round-trip helpers
# ---------------------------------------------------------------------------


def freeze_round_trace_v3(trace: RoundTraceV3) -> RoundTraceV3:
    """Return a copy of ``trace`` with its ``content_hash`` filled in.

    Deterministic: re-running the freeze over an already-frozen trace yields
    the same content_hash and does not re-mutate.
    """

    digest = compute_round_trace_v3_content_hash(trace)
    if dict(trace.hashes).get("content_hash") == digest:
        return trace
    return dataclasses.replace(trace, hashes={"content_hash": digest})


def round_trip_round_trace_v3(trace: RoundTraceV3) -> RoundTraceV3:
    """Validate and re-emit ``trace``.

    The trace must be fully populated (no missing fields), all numeric values
    must be finite, and the embedded ``content_hash`` must match the recomputed
    digest. Raises ``ValueError`` on any of these failures.
    """

    _validate_round_trace_v3(trace)
    expected = compute_round_trace_v3_content_hash(trace)
    embedded = dict(trace.hashes).get("content_hash")
    if embedded is not None and embedded != expected:
        raise ValueError(
            "round trace content_hash mismatch: "
            f"embedded={embedded!r} expected={expected!r}"
        )
    frozen = freeze_round_trace_v3(trace)
    return frozen


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


_REQUIRED_V3_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(RoundTraceV3) if f.name != "hashes"
)


def _all_finite(mapping: Mapping[str, float]) -> bool:
    return all(math.isfinite(float(v)) for v in mapping.values())


def _validate_round_trace_v3(trace: RoundTraceV3) -> None:
    errors: list[str] = []
    for name in _REQUIRED_V3_FIELDS:
        if name == "selected_bundle_id":
            continue  # selected_bundle_id is Optional; only enforced when adopted
        if getattr(trace, name, None) is None:
            errors.append(f"missing_field:{name}")
    if trace.round_index < 0:
        errors.append("round_index_negative")
    if trace.source_round < 0:
        errors.append("source_round_negative")
    if trace.created_at_round < 0:
        errors.append("created_at_round_negative")
    for mapping_name in (
        "per_factor_raw",
        "per_factor_bounded",
        "alpha_by_channel",
        "beta_by_channel",
        "fresh_noise_floor_by_channel",
    ):
        mapping = getattr(trace, mapping_name)
        if not isinstance(mapping, Mapping):
            errors.append(f"{mapping_name}_not_mapping")
            continue
        if not _all_finite(mapping):
            errors.append(f"{mapping_name}_non_finite")
    if not trace.beta_by_channel and not trace.blockers:
        errors.append("zero_beta_no_blocker")
    # If the trace declares the row was adopted, it must have selected a bundle
    # and named the adaptive_reflow writer explicitly (acceptance contract).
    if trace.was_adopted:
        if not trace.selected_bundle_id:
            errors.append("adopted_without_selected_bundle")
        if trace.final_policy_writer != FINAL_POLICY_WRITER_ADAPTIVE_REFLOW:
            errors.append(
                "adopted_with_non_adaptive_reflow_writer_"
                f"{trace.final_policy_writer}"
            )
    if not isinstance(trace.rejected_bundle_ids, tuple):
        errors.append("rejected_bundle_ids_not_tuple")
    if not isinstance(trace.blockers, tuple):
        errors.append("blockers_not_tuple")
    if errors:
        raise ValueError("round_trace_v3_rejected:" + ",".join(errors))


# ---------------------------------------------------------------------------
# v2 reader (legacy compatibility)
# ---------------------------------------------------------------------------


_V2_REQUIRED_FIELDS: tuple[str, ...] = (
    "round_index",
    "source_round",
    "selected_bundle_id",
    "rejected_bundle_ids",
    "alpha_by_channel",
    "beta_by_channel",
    "fresh_noise_floor_by_channel",
    "calibration_artifact_hash",
    "feedback_mode",
    "operation_order_version",
    "created_at_round",
)


def read_round_trace_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the v2 trace payload unchanged, after schema validation.

    This is a *reader*, not a writer; it does not synthesize v3 fields. It
    enforces the v2 schema surface and raises ``ValueError`` if the legacy
    fields are absent or the schema name is not v2.
    """

    if not isinstance(payload, Mapping):
        raise TypeError("v2 trace payload must be a Mapping")
    schema_name = payload.get("schema_name") or payload.get("schema_version")
    if schema_name != ROUND_TRACE_V2_SCHEMA_NAME:
        raise ValueError(
            f"v2 reader requires schema_name={ROUND_TRACE_V2_SCHEMA_NAME!r}; "
            f"got {schema_name!r}"
        )
    missing = [name for name in _V2_REQUIRED_FIELDS if name not in payload]
    if missing:
        raise ValueError("v2 trace missing fields: " + ",".join(missing))
    for mapping_name in (
        "alpha_by_channel",
        "beta_by_channel",
        "fresh_noise_floor_by_channel",
    ):
        mapping = payload.get(mapping_name)
        if not isinstance(mapping, Mapping):
            raise ValueError(f"v2 trace field {mapping_name!r} must be a Mapping")
        if not _all_finite(mapping):
            raise ValueError(f"v2 trace field {mapping_name!r} contains non-finite values")
    return dict(payload)


__all__ = [
    "ALLOWED_FINAL_POLICY_WRITERS",
    "FINAL_POLICY_WRITER_ADAPTIVE_REFLOW",
    "FINAL_POLICY_WRITER_LEGACY_NOISE_BIAS",
    "PRODUCER_MODES",
    "ROUND_TRACE_V2_SCHEMA_NAME",
    "ROUND_TRACE_V3_SCHEMA_NAME",
    "RoundTraceV3",
    "compute_round_trace_v3_content_hash",
    "freeze_round_trace_v3",
    "read_round_trace_v2",
    "round_trip_round_trace_v3",
]
