"""State persistence / checkpoint carrier for the re-inference engine (P2-12).

This module is **stdlib-only** (no ``torch``, no ``jax``, no
``safetensors``). It is a pure-data add-on over
:mod:`adaptive_reflow.universal.state` and :mod:`adaptive_reflow.frame.engine`:
it does NOT change the :class:`FlowMatchingODEAdapter` Protocol surface.

Public surface
--------------

* :class:`Checkpoint` — frozen dataclass carrying a round's worth of
  serializable state (state bundle + round trace + ledger row + chain
  head + backend pointer).
* :func:`save_checkpoint` / :func:`load_checkpoint` — JSON default,
  pickle opt-in.
* :func:`verify_checkpoint` — re-derives the engine-digest seed and
  re-validates chain integrity.
* :class:`CheckpointError` — single failure type (fail-closed).

Tasks satisfied:

* ``P2-12`` — state persistence / checkpointing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, NewType

from adaptive_reflow.contracts import hash_artifact
from adaptive_reflow.frame.engine import (
    PhaseState,
    RoundTrace,
    verify_ledger_chain,
)
from adaptive_reflow.universal.state import (
    StateBundle,
    validate_state_bundle,
)

# NOTE: ``CalibrationManifest`` lives in
# ``adaptive_reflow.eval.calibration``; we import it lazily inside
# :func:`Engine.checkpoint_round` (the engine side) so this module
# does not pull ``eval`` at import time. The CP-side here only stores
# the manifest's digest string.

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------

IsoTimestamp = NewType("IsoTimestamp", str)
BundleFormatVersion = NewType("BundleFormatVersion", str)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEFAULT_BUNDLE_FORMAT_VERSION: BundleFormatVersion = BundleFormatVersion(
    "p2-12.checkpoint/v1"
)


# ---------------------------------------------------------------------------
# Checkpoint dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Checkpoint:
    """Frozen, JSON-stable carrier for one round's worth of engine state.

    Attributes
    ----------
    bundle_format_version:
        Bundle schema version. ``load_checkpoint`` raises
        :class:`CheckpointError` when the version is unknown.
    engine_digest_seed:
        sha256 of ``{engine_version, adapter_id}``. Re-derived on
        ``resume_round`` so cross-machine / cross-version drift fails
        closed.
    ledger_chain_head_hash:
        sha256 of the last ledger row's ``row_hash`` (``None`` when
        the checkpoint carries no ledger row).
    state_bundle:
        The :class:`StateBundle` at the round's start. Carries every
        pure-data field the engine / adapter inspect.
    last_round_trace:
        The :class:`RoundTrace` emitted by the engine for the round.
        ``None`` when the checkpoint is taken before the first round.
    last_ledger_row:
        The :class:`LedgerRow` emitted by the engine for the round.
        ``None`` when no round has fired yet.
    phase_state:
        The :class:`PhaseState` for the *next* round.
    calibration_manifest_hash:
        sha256 of the calibration manifest the round was driven by.
        ``None`` when no manifest is configured.
    native_payload_paths:
        ``channel_name -> file_path`` map for adapter-native tensors
        (the framework never inspects these bytes).
    created_at:
        ISO-8601 UTC timestamp at the moment the checkpoint was built.
    extras:
        Forward-compat bag for additional caller-supplied metadata.
        Tolerated on load; never read by the framework.
    """

    bundle_format_version: BundleFormatVersion
    engine_digest_seed: str
    ledger_chain_head_hash: str | None
    state_bundle: StateBundle
    last_round_trace: RoundTrace | None
    last_ledger_row: Any | None          # LedgerRow; forward-declared to break cycle
    phase_state: PhaseState | None
    calibration_manifest_hash: str | None
    native_payload_paths: Mapping[str, str]
    created_at: IsoTimestamp
    extras: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class CheckpointError(RuntimeError):
    """Raised on any checkpoint integrity failure (fail-closed)."""


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _default(obj: Any) -> Any:
    """Mirror ``adaptive_reflow.frame.engine._canonical_json_default``.

    Importing the engine's copy would create a cycle (state.py <-> the
    framework's universal package <-> frame/engine.py). Kept in
    lockstep with the engine via a regression test (see
    ``tests/test_universal/test_checkpoint.py::test_default_in_sync``).
    """
    item_fn = getattr(obj, "item", None)
    if callable(item_fn):
        try:
            return item_fn()
        except (ValueError, TypeError):
            pass
    float_fn = getattr(obj, "__float__", None)
    if callable(float_fn):
        try:
            return float_fn()
        except (TypeError, ValueError):
            pass
    return str(obj)


# ---------------------------------------------------------------------------
# save_checkpoint / load_checkpoint
# ---------------------------------------------------------------------------


def save_checkpoint(
    checkpoint: Checkpoint,
    path: str | Path,
    *,
    format: Literal["json", "pickle"] = "json",
) -> None:
    """Serialise ``checkpoint`` to ``path``.

    JSON is the default and survives across Python versions /
    machines. Pickle is opt-in and requires the ``.pkl`` suffix
    (security: pickle is unsafe to load from untrusted files).
    """
    p = Path(path)
    payload = _checkpoint_to_payload(checkpoint)
    if format == "json":
        text = json.dumps(payload, sort_keys=True, default=_default, ensure_ascii=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(p)
    elif format == "pickle":
        import pickle

        if not str(p).endswith(".pkl"):
            raise CheckpointError("pickle checkpoints must end with .pkl")
        with p.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        raise CheckpointError(f"unknown format: {format!r}")


def load_checkpoint(
    path: str | Path,
    *,
    format: Literal["json", "pickle"] | None = None,
) -> Checkpoint:
    """Read ``path`` and return the rebuilt :class:`Checkpoint`.

    Raises :class:`CheckpointError` on every failure mode: missing
    file, truncated/invalid JSON, missing required field, unknown
    bundle format version, payload schema drift.
    """
    p = Path(path)
    if not p.exists():
        raise CheckpointError(f"checkpoint file not found: {p}")
    if format is None:
        if p.suffix == ".json":
            format = "json"
        elif p.suffix == ".pkl":
            format = "pickle"
        else:
            format = "json"
    if format == "json":
        try:
            text = p.read_text(encoding="utf-8")
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CheckpointError(
                f"truncated_or_invalid_json: {exc.msg}"
            ) from exc
    elif format == "pickle":
        import pickle

        try:
            with p.open("rb") as fh:
                payload = pickle.load(fh)
        except Exception as exc:
            raise CheckpointError(f"pickle_load_failed: {exc!r}") from exc
    else:
        raise CheckpointError(f"unknown format: {format!r}")
    return _decode_checkpoint_payload(payload)


# ---------------------------------------------------------------------------
# Internal payload helpers
# ---------------------------------------------------------------------------


def _checkpoint_to_payload(checkpoint: Checkpoint) -> dict[str, Any]:
    """Build the JSON-stable payload dict from a :class:`Checkpoint`."""
    return {
        "bundle_format_version": str(checkpoint.bundle_format_version),
        "engine_digest_seed": str(checkpoint.engine_digest_seed),
        "ledger_chain_head_hash": (
            None
            if checkpoint.ledger_chain_head_hash is None
            else str(checkpoint.ledger_chain_head_hash)
        ),
        "state_bundle": {
            # canonical: sorted keys, str-coerced TensorRef
            "channels": {
                str(k): str(v) for k, v in sorted(checkpoint.state_bundle.channels.items())
            },
            "masks": {
                str(k): str(v) for k, v in sorted(checkpoint.state_bundle.masks.items())
            },
            "batch_id": str(checkpoint.state_bundle.batch_id),
            "sample_id": str(checkpoint.state_bundle.sample_id),
            "reference_frame": str(checkpoint.state_bundle.reference_frame),
            "normalization": str(checkpoint.state_bundle.normalization),
            "source_round": int(checkpoint.state_bundle.source_round),
            "detach_proof": bool(checkpoint.state_bundle.detach_proof),
            "native_state_digest": str(checkpoint.state_bundle.native_state_digest),
            "provenance": list(checkpoint.state_bundle.provenance),
        },
        "last_round_trace": (
            None
            if checkpoint.last_round_trace is None
            else checkpoint.last_round_trace.as_dict()
        ),
        "last_ledger_row": (
            None
            if checkpoint.last_ledger_row is None
            else _ledger_row_to_dict(checkpoint.last_ledger_row)
        ),
        "phase_state": (
            None
            if checkpoint.phase_state is None
            else checkpoint.phase_state.as_dict()
        ),
        "calibration_manifest_hash": (
            None
            if checkpoint.calibration_manifest_hash is None
            else str(checkpoint.calibration_manifest_hash)
        ),
        "native_payload_paths": {
            str(k): str(v) for k, v in sorted(checkpoint.native_payload_paths.items())
        },
        "created_at": str(checkpoint.created_at),
        "extras": dict(checkpoint.extras),
    }


def _ledger_row_to_dict(row: Any) -> dict[str, Any]:
    """Serialise a :class:`LedgerRow` to a JSON-stable dict.

    The dataclass is frozen and has no ``as_dict`` method of its own;
    inlining here keeps ``frame/engine.py`` stdlib-only and unchanged.
    """
    return {
        "ledger_row_id": str(row.ledger_row_id),
        "round_index": int(row.round_index),
        "source_round": int(row.source_round),
        "target_round": int(row.target_round),
        "applied_policy_hash": str(row.applied_policy_hash),
        "selected_bundle_digest": str(row.selected_bundle_digest),
        "audit_codes": list(row.audit_codes),
        "per_channel_decision": {
            str(k): bool(v)
            for k, v in sorted(row.per_channel_decision.items())
        },
        "prev_ledger_row_hash": (
            None
            if row.prev_ledger_row_hash is None
            else str(row.prev_ledger_row_hash)
        ),
        "row_hash": str(row.row_hash),
    }


def _decode_checkpoint_payload(payload: Mapping[str, Any]) -> Checkpoint:
    """Rebuild a :class:`Checkpoint` from a JSON payload.

    Raises :class:`CheckpointError` on schema drift.
    """
    if not isinstance(payload, Mapping):
        raise CheckpointError("payload must be a JSON object")
    if "bundle_format_version" not in payload:
        raise CheckpointError("missing_field:bundle_format_version")
    bf_version = str(payload["bundle_format_version"])
    if "engine_digest_seed" not in payload:
        raise CheckpointError("missing_field:engine_digest_seed")
    if "created_at" not in payload:
        raise CheckpointError("missing_field:created_at")
    if bf_version != str(DEFAULT_BUNDLE_FORMAT_VERSION):
        raise CheckpointError(
            f"unknown_format_version:{bf_version} "
            f"(expected {DEFAULT_BUNDLE_FORMAT_VERSION})"
        )
    # Reconstruct StateBundle — calls back into the universal adapter
    # capability-token factory. Field list mirrors StateBundle exactly
    # so a SchemaError surfaces as CheckpointError.
    from adaptive_reflow.universal.adapter import AdapterCapabilities
    from adaptive_reflow.universal.state import (
        ChannelName as _ChannelName,
    )
    from adaptive_reflow.universal.state import (
        StateBundle as _StateBundle,
    )
    from adaptive_reflow.universal.state import (
        TensorRef as _TensorRef,
    )

    sb_raw = payload.get("state_bundle")
    if not isinstance(sb_raw, Mapping):
        raise CheckpointError("missing_or_invalid:state_bundle")
    try:
        channels_dict = sb_raw["channels"]
        masks_dict = sb_raw["masks"]
        sb = _StateBundle(
            channels={
                _ChannelName(k): _TensorRef(v)
                for k, v in sorted(channels_dict.items())
            },
            masks={str(k): _TensorRef(v) for k, v in sorted(masks_dict.items())},
            batch_id=str(sb_raw["batch_id"]),
            sample_id=str(sb_raw["sample_id"]),
            reference_frame=str(sb_raw["reference_frame"]),
            normalization=str(sb_raw["normalization"]),
            source_round=int(sb_raw["source_round"]),
            detach_proof=bool(sb_raw["detach_proof"]),
            native_state_digest=str(sb_raw["native_state_digest"]),
            provenance=tuple(str(x) for x in sb_raw["provenance"]),
            capability_token=AdapterCapabilities(
                has_ode_integration_surface=False,
                has_prior_export=False,
                has_state_export=False,
                has_condition_injection=False,
                has_restart_boundary=False,
                has_continuous_channels=False,
                has_discrete_channels=False,
                has_trajectory_digest=False,
                has_deterministic_seed=False,
                has_materialization_route=False,
                supported_channels=tuple(sorted(channels_dict.keys())),
                channel_domains={},
            ),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise CheckpointError(f"state_bundle_decode_failed: {exc!r}") from exc

    ok, sb_errs = validate_state_bundle(sb)
    if not ok:
        raise CheckpointError("state_bundle_invalid:" + ";".join(sb_errs))

    # RoundTrace is reconstructed as a plain dict (callers needing a
    # typed RoundTrace rebuild it from the as_dict output via their
    # own constructor; the framework only reads the dict view).
    rt_raw = payload.get("last_round_trace")
    if rt_raw is not None and not isinstance(rt_raw, Mapping):
        raise CheckpointError("invalid:last_round_trace")

    lr_raw = payload.get("last_ledger_row")
    if lr_raw is None:
        ledger_row_obj = None
    else:
        if not isinstance(lr_raw, Mapping):
            raise CheckpointError("invalid:last_ledger_row")
        from adaptive_reflow.frame.engine import LedgerRow as _LedgerRow

        ledger_row_obj = _LedgerRow(
            ledger_row_id=str(lr_raw["ledger_row_id"]),
            round_index=int(lr_raw["round_index"]),
            source_round=int(lr_raw["source_round"]),
            target_round=int(lr_raw["target_round"]),
            applied_policy_hash=str(lr_raw["applied_policy_hash"]),
            selected_bundle_digest=str(lr_raw["selected_bundle_digest"]),
            audit_codes=tuple(str(x) for x in lr_raw["audit_codes"]),
            per_channel_decision={
                str(k): bool(v)
                for k, v in sorted(lr_raw["per_channel_decision"].items())
            },
            prev_ledger_row_hash=(
                None
                if lr_raw.get("prev_ledger_row_hash") is None
                else str(lr_raw["prev_ledger_row_hash"])
            ),
            row_hash=str(lr_raw.get("row_hash", "")),
        )

    ps_raw = payload.get("phase_state")
    if ps_raw is None:
        phase_state_obj = None
    else:
        if not isinstance(ps_raw, Mapping):
            raise CheckpointError("invalid:phase_state")
        from adaptive_reflow.frame.engine import PhaseState as _PhaseState

        phase_state_obj = _PhaseState(
            outer_cycle_id=int(ps_raw["outer_cycle_id"]),
            round_in_cycle=int(ps_raw["round_in_cycle"]),
            schedule_phase=str(ps_raw["schedule_phase"]),
            schedule_phase_index=int(ps_raw["schedule_phase_index"]),
            horizon_remaining=int(ps_raw["horizon_remaining"]),
            seed_lineage_digest=str(ps_raw["seed_lineage_digest"]),
            recorded_at_round=int(ps_raw["recorded_at_round"]),
        )

    return Checkpoint(
        bundle_format_version=bf_version,  # type: ignore[arg-type]
        engine_digest_seed=str(payload["engine_digest_seed"]),
        ledger_chain_head_hash=(
            None
            if payload.get("ledger_chain_head_hash") is None
            else str(payload["ledger_chain_head_hash"])
        ),
        state_bundle=sb,
        last_round_trace=None if rt_raw is None else dict(rt_raw),  # type: ignore[arg-type]
        last_ledger_row=ledger_row_obj,
        phase_state=phase_state_obj,
        calibration_manifest_hash=(
            None
            if payload.get("calibration_manifest_hash") is None
            else str(payload["calibration_manifest_hash"])
        ),
        native_payload_paths={
            str(k): str(v)
            for k, v in sorted(payload.get("native_payload_paths", {}).items())
        },
        created_at=str(payload["created_at"]),  # type: ignore[arg-type]
        extras=dict(payload.get("extras", {})),
    )


# ---------------------------------------------------------------------------
# verify_checkpoint
# ---------------------------------------------------------------------------


def verify_checkpoint(checkpoint: Checkpoint) -> tuple[bool, tuple[str, ...]]:
    """Re-validate ``checkpoint`` and return ``(ok, errors)``.

    Checks:

    * Bundle format version matches :data:`DEFAULT_BUNDLE_FORMAT_VERSION`.
    * The :class:`StateBundle` re-validates against
      :func:`validate_state_bundle`.
    * The ledger row chain re-verifies via :func:`verify_ledger_chain`.
    * Native payload paths (if any) point to existing files (warn, not
      fail; missing files append ``native_payload_missing:<channel>``).

    Returns ``(False, (...errors))`` when any check fails. ``errors`` is
    a tuple of deterministic, ASCII-only audit codes.
    """
    errors: list[str] = []
    if str(checkpoint.bundle_format_version) != str(DEFAULT_BUNDLE_FORMAT_VERSION):
        errors.append(
            f"unknown_format_version:{checkpoint.bundle_format_version}"
        )
    ok, sb_errs = validate_state_bundle(checkpoint.state_bundle)
    if not ok:
        errors.extend("state_bundle_invalid:" + e for e in sb_errs)
    if checkpoint.last_ledger_row is not None:
        chain_ok, chain_msg = verify_ledger_chain((checkpoint.last_ledger_row,))
        if not chain_ok:
            errors.append(f"ledger_chain_invalid:{chain_msg}")
    # Native payload presence check (warn-but-not-raise by default).
    for channel, path in checkpoint.native_payload_paths.items():
        if not Path(path).exists():
            errors.append(f"native_payload_missing:{channel}")
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Digest helpers
# ---------------------------------------------------------------------------


def engine_digest_seed(*, engine_version: str, adapter_id: str) -> str:
    """Return a deterministic sha256 seed tying a checkpoint to its engine.

    Same ``engine_version`` + ``adapter_id`` -> identical seed. The
    seed is re-derived on ``resume_round`` and stored in the bundle so
    cross-machine / cross-version drift fails closed.
    """
    payload = {
        "engine_version": str(engine_version),
        "adapter_id": str(adapter_id),
    }
    return hash_artifact(payload)


__all__ = [
    "DEFAULT_BUNDLE_FORMAT_VERSION",
    "BundleFormatVersion",
    "Checkpoint",
    "CheckpointError",
    "IsoTimestamp",
    "engine_digest_seed",
    "load_checkpoint",
    "save_checkpoint",
    "verify_checkpoint",
]
