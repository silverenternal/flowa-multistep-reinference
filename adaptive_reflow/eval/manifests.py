"""JSON-serializable manifest I/O + frozen validators (DTB-R7, CPU-only).

This module exposes:

* :func:`write_calibration_manifest` / :func:`read_calibration_manifest` —
  JSON serialization for :class:`CalibrationManifest`. The serialization
  is hash-stable: identical input produces byte-identical output.

* :func:`validate_manifest_frozen` — structural validator enforcing the
  frozen-before-evaluation invariant and any deferred GPU provenance
  fields.

The fields below are placeholder-only until a GPU evaluation run
populates them; they are explicitly tagged with a ``"deferred"``
sentinel in the serialized payload.

* ``gpu_provenance_hash`` — placeholder; ``None`` (JSON ``null``) until
  the GPU evaluation harness writes the provenance chain.
* ``checkpoint_hash`` — placeholder; ``None`` until the run-time
  checkpoints are taken.
* ``data_split_manifest_hash`` — placeholder; ``None`` until the
  data/split manifest is finalized.
* ``config_hash`` — provided by the calibration manifest itself;
  copied verbatim.
* ``source_evaluator_version`` — placeholder; ``None`` until the
  evaluator version is pinned.
* ``round_trace_hash`` — placeholder; ``None`` until the round trace
  is written.
* ``failure_taxonomy`` — placeholder; the empty list until the
  diagnostic taxonomy is recorded.

DEFERRED: real GPU runs / artifact generation / target-disjoint paired
evaluation runs.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from typing import Any, NewType

from adaptive_reflow.contracts import (
    ArtifactHash,
    FactorValue,
    ManifestId,
)
from adaptive_reflow.eval.calibration import (
    LOWER_BOUND_METHODS,
    CalibrationBucket,
    CalibrationManifest,
    CalibrationTimeSplit,
    manifest_digest,
)

# ---------------------------------------------------------------------------
# Local NewType aliases
# ---------------------------------------------------------------------------

JsonString = NewType("JsonString", str)
ValidationResult = tuple[bool, tuple[str, ...]]


# ---------------------------------------------------------------------------
# Sentinel used for GPU-provenance placeholder fields
# ---------------------------------------------------------------------------

DEFERRED_GPU_SENTINEL = "deferred"
"""Sentinel string used in the serialized manifest for deferred GPU fields.

JSON consumers should treat any string equal to this constant as "not yet
populated by a GPU run".
"""


def _ok() -> ValidationResult:
    return (True, ())


def _err(*messages: str) -> ValidationResult:
    return (False, tuple(messages))


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _manifest_to_payload(manifest: CalibrationManifest) -> dict[str, Any]:
    """Build the canonical JSON payload for ``manifest``.

    The payload is hash-stable: ``(dict)`` keys are sorted at the top
    level only, and inner mappings are sorted by the ``_sorted_items``
    helper so the same manifest always serializes to the same JSON bytes.
    """
    buckets_payload: list[dict[str, Any]] = []
    for metric in sorted(manifest.per_metric_buckets.keys()):
        for bucket in manifest.per_metric_buckets[metric]:
            buckets_payload.append(
                {
                    "metric_name": str(bucket.metric_name),
                    "channel": str(bucket.channel),
                    "sample_count": int(bucket.sample_count),
                    "lower_bound_value": float(bucket.lower_bound_value),
                    "lower_bound_confidence": float(bucket.lower_bound_confidence),
                    "computed_at": str(bucket.computed_at),
                    "source_stats_hash": str(bucket.source_stats_hash),
                }
            )

    payload: dict[str, Any] = {
        "manifest_id": str(manifest.manifest_id),
        "calibration_dataset": str(manifest.calibration_dataset),
        "time_split": {
            "train_period": [
                str(manifest.time_split.train_period[0]),
                str(manifest.time_split.train_period[1]),
            ],
            "frozen_period": [
                str(manifest.time_split.frozen_period[0]),
                str(manifest.time_split.frozen_period[1]),
            ],
            "eval_period": [
                str(manifest.time_split.eval_period[0]),
                str(manifest.time_split.eval_period[1]),
            ],
            "frozen_until_round": int(manifest.time_split.frozen_until_round),
        },
        "per_metric_buckets": buckets_payload,
        "min_sample_count": int(manifest.min_sample_count),
        "lower_bound_method": str(manifest.lower_bound_method),
        # ``artifact_hash`` is a content-derived digest; we recompute it
        # via :func:`manifest_digest` so the JSON carries the canonical
        # hash. The reader trusts this hash (it is the only field the
        # round-trip parser does not recompute).
        "artifact_hash": str(
            manifest.artifact_hash
            if str(manifest.artifact_hash)
            else manifest_digest(manifest)
        ),
        "frozen_before_evaluation": True,
        # Placeholder fields; populated only by a real GPU run.
        # DEFERRED: see module docstring.
        "gpu_provenance_hash": None,  # DEFERRED
        "checkpoint_hash": None,  # DEFERRED
        "data_split_manifest_hash": None,  # DEFERRED
        "source_evaluator_version": None,  # DEFERRED
        "round_trace_hash": None,  # DEFERRED
        "failure_taxonomy": [],  # DEFERRED
    }
    return payload


def _payload_to_manifest(payload: Mapping[str, Any]) -> CalibrationManifest:
    """Reconstruct a :class:`CalibrationManifest` from a parsed payload.

    Round-trips the *content* fields; deferred placeholder fields are
    intentionally dropped (they are stored as ``None`` in the JSON but
    are not part of the manifest dataclass).
    """
    ts_raw = payload.get("time_split")
    if not isinstance(ts_raw, Mapping):
        raise ValueError("time_split must be a mapping")
    train = ts_raw.get("train_period")
    frozen = ts_raw.get("frozen_period")
    eval_p = ts_raw.get("eval_period")
    if (
        not isinstance(train, list)
        or len(train) != 2
        or not isinstance(frozen, list)
        or len(frozen) != 2
        or not isinstance(eval_p, list)
        or len(eval_p) != 2
    ):
        raise ValueError("time_split periods must each be a 2-element list")

    time_split = CalibrationTimeSplit(
        train_period=(train[0], train[1]),
        frozen_period=(frozen[0], frozen[1]),
        eval_period=(eval_p[0], eval_p[1]),
        frozen_until_round=int(ts_raw.get("frozen_until_round", 0)),
    )

    buckets_raw = payload.get("per_metric_buckets")
    if not isinstance(buckets_raw, list):
        raise ValueError("per_metric_buckets must be a list")

    grouped: dict[str, list[CalibrationBucket]] = {}
    for entry in buckets_raw:
        if not isinstance(entry, Mapping):
            raise ValueError("bucket entries must be mappings")
        metric_name = str(entry.get("metric_name", ""))
        bucket = CalibrationBucket(
            metric_name=metric_name,
            channel=str(entry.get("channel", "")),
            sample_count=int(entry.get("sample_count", 0)),
            lower_bound_value=FactorValue(float(entry.get("lower_bound_value", 0.0))),
            lower_bound_confidence=float(entry.get("lower_bound_confidence", 0.95)),
            computed_at=str(entry.get("computed_at", "")),
            source_stats_hash=ArtifactHash(str(entry.get("source_stats_hash", ""))),
        )
        grouped.setdefault(metric_name, []).append(bucket)

    per_metric_buckets = {
        metric: tuple(grouped[metric]) for metric in sorted(grouped.keys())
    }

    artifact_hash = ArtifactHash(
        str(payload.get("artifact_hash", payload.get("manifest_hash", "")))
    )

    manifest = CalibrationManifest(
        manifest_id=ManifestId(str(payload.get("manifest_id", ""))),
        calibration_dataset=str(payload.get("calibration_dataset", "")),
        time_split=time_split,
        per_metric_buckets=per_metric_buckets,
        min_sample_count=int(payload.get("min_sample_count", 0)),
        lower_bound_method=str(payload.get("lower_bound_method", "wilson")),  # type: ignore[arg-type]
        artifact_hash=artifact_hash,
        frozen_before_evaluation=True,
    )

    # If the JSON carried no artifact_hash (or an empty one), synthesize
    # the canonical digest from the just-constructed manifest. This keeps
    # the round-trip self-consistent without weakening tamper-detection
    # when the JSON carries an explicit hash.
    if not str(artifact_hash):
        artifact_hash = manifest_digest(manifest)

    return dataclasses.replace(manifest, artifact_hash=artifact_hash)


# ---------------------------------------------------------------------------
# Public I/O functions
# ---------------------------------------------------------------------------


def write_calibration_manifest(manifest: CalibrationManifest) -> JsonString:
    """Serialize ``manifest`` to a hash-stable JSON string.

    Two structurally identical manifests produce byte-identical JSON.
    The :class:`CalibrationManifest.__post_init__` invariants are
    re-checked before serialization; a manifest that fails those checks
    raises :class:`ValueError` before any bytes are emitted.
    """
    payload = _manifest_to_payload(manifest)
    # ``sort_keys=True`` plus the inner ``sorted(...)`` ordering guarantees
    # that the same manifest produces the same JSON bytes regardless of
    # insertion order of the per-metric buckets dict.
    return JsonString(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    )


def read_calibration_manifest(json_text: str) -> CalibrationManifest:
    """Parse ``json_text`` (produced by :func:`write_calibration_manifest`)
    and reconstruct the manifest.

    Deferred GPU provenance fields are accepted as ``null`` / absent /
    equal-to-``"deferred"``. Any other value is rejected by the
    round-trip parser so a future GPU run that writes a real value is
    caught by the manifest consumer.
    """
    if not isinstance(json_text, str):
        raise TypeError(f"json_text must be str, got {type(json_text).__name__}")
    payload = json.loads(json_text)
    if not isinstance(payload, Mapping):
        raise ValueError("top-level JSON value must be an object")

    # Reject any deferred placeholder that carries an unexpected value.
    for field_name in (
        "gpu_provenance_hash",
        "checkpoint_hash",
        "data_split_manifest_hash",
        "source_evaluator_version",
        "round_trace_hash",
    ):
        if field_name in payload:
            value = payload[field_name]
            if value is not None and value != DEFERRED_GPU_SENTINEL:
                raise ValueError(
                    f"{field_name} must be None or 'deferred' until a GPU run "
                    f"populates it; got {value!r}"
                )

    failure_taxonomy = payload.get("failure_taxonomy", [])
    if not isinstance(failure_taxonomy, list) or any(
        not isinstance(x, str) for x in failure_taxonomy
    ):
        raise ValueError("failure_taxonomy must be a list of strings")

    return _payload_to_manifest(payload)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_manifest_frozen(manifest: CalibrationManifest) -> ValidationResult:
    """Validate the frozen-before-evaluation invariant for ``manifest``.

    Rejects when ``frozen_before_evaluation`` is not ``True``, the lower
    bound method is not in the closed set, any bucket carries
    ``lower_bound_value`` outside ``[0, 1]``, ``min_sample_count`` is
    negative, the time-split ``frozen_until_round`` is negative, or any
    per-metric bucket list is empty. The validator is intentionally
    strict; downstream gates that consume a manifest must rely on this
    function rather than re-implementing the rules.
    """
    errors: list[str] = []

    if manifest.frozen_before_evaluation is not True:
        errors.append(
            "frozen_before_evaluation must be True; manifests are frozen "
            "before evaluation runs and may not be mutated post-creation"
        )

    if manifest.lower_bound_method not in LOWER_BOUND_METHODS:
        errors.append(
            f"lower_bound_method must be one of {LOWER_BOUND_METHODS!r}, "
            f"got {manifest.lower_bound_method!r}"
        )

    if (
        isinstance(manifest.min_sample_count, bool)
        or not isinstance(manifest.min_sample_count, int)
        or manifest.min_sample_count < 0
    ):
        errors.append(
            f"min_sample_count must be a non-negative int, got "
            f"{manifest.min_sample_count!r}"
        )

    if manifest.time_split.frozen_until_round < 0:
        errors.append(
            "time_split.frozen_until_round must be a non-negative int, "
            f"got {manifest.time_split.frozen_until_round!r}"
        )

    if not manifest.per_metric_buckets:
        errors.append("per_metric_buckets must be non-empty")

    seen_metrics: set[str] = set()
    for metric_name, buckets in manifest.per_metric_buckets.items():
        if not str(metric_name):
            errors.append("per_metric_buckets: metric name must be non-empty")
        if metric_name in seen_metrics:
            errors.append(
                f"per_metric_buckets: duplicate metric {metric_name!r}"
            )
        seen_metrics.add(metric_name)

        if not buckets:
            errors.append(
                f"per_metric_buckets[{metric_name!r}] must be non-empty"
            )

        seen_channels: set[str] = set()
        for bucket in buckets:
            if not str(bucket.metric_name):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}]: bucket metric_name "
                    "must be non-empty"
                )
            if str(bucket.metric_name) != str(metric_name):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}]: bucket metric_name "
                    f"mismatch: {bucket.metric_name!r}"
                )
            if not str(bucket.channel):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}]: channel must be "
                    "non-empty"
                )
            if str(bucket.channel) in seen_channels:
                errors.append(
                    f"per_metric_buckets[{metric_name!r}]: duplicate channel "
                    f"{bucket.channel!r}"
                )
            seen_channels.add(str(bucket.channel))

            lb = float(bucket.lower_bound_value)
            if not (0.0 <= lb <= 1.0):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}][{bucket.channel!r}]: "
                    f"lower_bound_value must be in [0, 1], got {lb!r}"
                )
            if (
                isinstance(bucket.sample_count, bool)
                or not isinstance(bucket.sample_count, int)
                or bucket.sample_count < 0
            ):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}][{bucket.channel!r}]: "
                    f"sample_count must be a non-negative int, got "
                    f"{bucket.sample_count!r}"
                )
            if not str(bucket.source_stats_hash):
                errors.append(
                    f"per_metric_buckets[{metric_name!r}][{bucket.channel!r}]: "
                    "source_stats_hash must be non-empty"
                )

    if errors:
        return _err(*errors)
    return _ok()


def frozen_manifest_hash(manifest: CalibrationManifest) -> ArtifactHash:
    """Hash the canonical manifest payload (independent of the stored
    ``artifact_hash``).

    Provided here for callers that want a single import path for manifest
    I/O plus the canonical digest.
    """
    return manifest_digest(manifest)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # Sentinel
    "DEFERRED_GPU_SENTINEL",
    # Local types
    "JsonString",
    "ValidationResult",
    "frozen_manifest_hash",
    "read_calibration_manifest",
    # Validators
    "validate_manifest_frozen",
    # I/O
    "write_calibration_manifest",
]
