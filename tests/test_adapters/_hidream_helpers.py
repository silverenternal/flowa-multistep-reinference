"""Shared helpers for the HiDream-I1 adapter test split (Wave 104 P1-B).

Centralises the helper builders (``_make_final_policy``, ``_make_phase_state``,
``_make_condition_delta``, ``_validate_round_trace``, ``_native_x0``,
``_endpoint_from_trace``) so that ``test_hidream_i1_smoke.py``,
``test_hidream_i1_conformance.py`` and ``test_hidream_i1_metrics.py`` can
all import them without duplication.

The filename starts with ``_`` so pytest's default
``python_files = ["test_*.py", "*_test.py"]`` collection rule does NOT
walk this module — it is import-only, not test-discovery.

Wave 104 P1-B: split of the original 771-LOC ``test_hidream_i1.py``
into ``test_smoke.py + test_conformance.py + test_metrics.py`` (pure
file-system refactor, no test_* deleted, no test renamed).
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


def _hash_bundle(bundle) -> str:
    """Return a deterministic SHA-256 digest of ``bundle``'s identity surface."""
    import hashlib

    h = hashlib.sha256()
    h.update(repr(sorted(bundle.channels.items(), key=lambda kv: str(kv[0]))).encode())
    h.update(b"|")
    h.update(str(bundle.batch_id).encode())
    h.update(b"|")
    h.update(str(bundle.sample_id).encode())
    h.update(b"|")
    h.update(str(bundle.source_round).encode())
    h.update(b"|")
    h.update(str(bundle.native_state_digest).encode())
    return h.hexdigest()


def _validate_round_trace(trace) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``trace`` passes every round-level gate."""
    errors: list[str] = []
    audit_codes = tuple(getattr(trace, "audit_codes", ()))
    if audit_codes:
        errors.append(f"non_empty_audit_codes:{list(audit_codes)}")
    if not bool(getattr(trace, "detached", False)):
        errors.append("endpoint_not_detached")
    if getattr(trace, "integrator_trace", None) is None:
        errors.append("integrator_trace_missing")
    endpoint_digest = str(getattr(trace, "endpoint_digest", ""))
    if not endpoint_digest:
        errors.append("endpoint_digest_empty")
    initial_state_digest = str(getattr(trace, "initial_state_digest", ""))
    if not initial_state_digest:
        errors.append("initial_state_digest_empty")
    return (not errors, tuple(errors))


def _make_final_policy(
    *,
    policy_id: str,
    run_id: str,
    beta: float,
    target_round: int = 0,
    beta_from_schedule: bool = False,
) -> object:  # FinalRestartPolicy
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    channel = ChannelName("image_latent")
    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={channel: FactorValue(float(beta))},
        alpha_by_channel={channel: FactorValue(1.0)},
        fresh_noise_floor_by_channel={channel: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={channel: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=bool(beta_from_schedule),
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_phase_state(*, horizon_remaining: int = 200) -> object:  # PhaseState
    from adaptive_reflow.frame import PhaseState

    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=int(horizon_remaining),
        seed_lineage_digest="hidream-i1-test-lineage",
        recorded_at_round=0,
    )


def _make_condition_delta(
    *,
    target_round: int,
    num_steps: int = 2,
    prompt: str = "a high-resolution photograph of a mountain landscape at sunset",
    cfg_scale: float | None = None,
    variant: str | None = None,
    source: str = "hidream_i1_test",
    calibration_artifact_hash: str = "cal-hidream-i1",
) -> object:  # ODEConditionDelta
    from adaptive_reflow.universal.state import ODEConditionDelta

    spec: dict[str, object] = {"num_steps": int(num_steps), "prompt": str(prompt)}
    if cfg_scale is not None:
        spec["cfg_scale"] = float(cfg_scale)
    if variant is not None:
        spec["variant"] = str(variant)
    return ODEConditionDelta(
        delta_spec=spec,
        source=source,
        target_round=int(target_round),
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _native_x0(adapter, digest: str) -> np.ndarray:
    """Return the ``x0`` stored under ``digest`` as a flat ``(16, 128, 128)`` array."""
    native = adapter._native_states[digest]  # noqa: SLF001 — test seam
    return np.asarray(native["x0"], dtype=np.float64).reshape((16, 128, 128))


def _endpoint_from_trace(adapter, trace) -> np.ndarray:
    """Return the final trajectory point stored under ``trace.native_state_digest``."""
    native = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    traj = np.asarray(native["trajectory"], dtype=np.float64)
    return np.asarray(traj[-1], dtype=np.float64).reshape((16, 128, 128))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hidream_adapter() -> object:  # HiDreamI1Adapter
    """Return a fresh :class:`HiDreamI1Adapter` in synthetic mode."""
    from adaptive_reflow.adapters.hidream_i1 import HiDreamI1Adapter

    return HiDreamI1Adapter(
        variant="full",
        weights_path=None,
        force_mode="synthetic",
        num_steps=2,
        synthetic_seed=42,
    )


__all__ = [
    "_hash_bundle",
    "_validate_round_trace",
    "_make_final_policy",
    "_make_phase_state",
    "_make_condition_delta",
    "_native_x0",
    "_endpoint_from_trace",
    "hidream_adapter",
]
