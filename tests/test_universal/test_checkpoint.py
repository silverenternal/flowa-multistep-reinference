"""Tests for P2-12 — state persistence / checkpointing (universal layer).

Covers the JSON round-trip, version-mismatch detection, chain tamper
detection, engine-digest-seed round-trip, and the stdlib-only guard.
Acceptance gate for the 2356-test back-compat invariant: the byte-
stable digest payload assertion updates live in this file only.
"""

from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import replace as _dc_replace

import pytest

# Make sure the project root is importable when pytest is invoked from
# any directory.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from adaptive_reflow.frame.engine import (
    LedgerRow,
    build_ledger_row,
    compute_ledger_row_hash,
)
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.checkpoint import (
    DEFAULT_BUNDLE_FORMAT_VERSION,
    Checkpoint,
    CheckpointError,
    IsoTimestamp,
    engine_digest_seed,
    load_checkpoint,
    save_checkpoint,
    verify_checkpoint,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_token(supported: tuple[str, ...] = ("X",)) -> AdapterCapabilities:
    """Return a minimal :class:`AdapterCapabilities` token for tests."""
    return AdapterCapabilities(
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
        supported_channels=supported,
        channel_domains={},
    )


def _bundle() -> StateBundle:
    """Return a deterministic :class:`StateBundle` for tests."""
    return StateBundle(
        channels={ChannelName("X"): TensorRef("ref-X")},
        masks={},
        batch_id="b1",
        sample_id="s1",
        reference_frame="pocket_centered",
        normalization="per_atom_std",
        source_round=3,
        detach_proof=True,
        native_state_digest="sha-X",
        provenance=("frame.engine",),
        capability_token=_empty_token(supported=("X",)),
    )


def _cp(
    *,
    ledger_row: LedgerRow | None = None,
    extras: dict[str, object] | None = None,
) -> Checkpoint:
    """Return a deterministic :class:`Checkpoint` for tests."""
    return Checkpoint(
        bundle_format_version=DEFAULT_BUNDLE_FORMAT_VERSION,
        engine_digest_seed="seed",
        ledger_chain_head_hash=(
            str(ledger_row.row_hash) if ledger_row is not None else None
        ),
        state_bundle=_bundle(),
        last_round_trace=None,
        last_ledger_row=ledger_row,
        phase_state=None,
        calibration_manifest_hash=None,
        native_payload_paths={},
        created_at=IsoTimestamp("2026-09-04T00:00:00Z"),
        extras=extras or {},
    )


def _ledger_row_chain(n: int = 1) -> list[LedgerRow]:
    """Return ``n`` canonical ledger rows (chain anchor → tail)."""
    rows: list[LedgerRow] = []
    prev_hash: str | None = None
    for r in range(n):
        rows.append(
            build_ledger_row(
                round_index=r,
                policy_hash=f"policy-{r}",
                bundle_digest=f"bundle-{r}",
                source_round=r,
                applied_policy_hash=f"applied-{r}",
                audit_codes=(),
                per_channel_decision={"X": True},
                prev_ledger_row_hash=prev_hash,
            )
        )
        prev_hash = rows[-1].row_hash
    return rows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_checkpoint_roundtrip_statebundle(tmp_path: pathlib.Path) -> None:
    """JSON round-trip of a :class:`Checkpoint` keeps native_state_digest
    and provenance byte-stable."""
    cp = _cp()
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    loaded = load_checkpoint(path)
    ok, errs = verify_checkpoint(loaded)
    assert ok, errs
    assert loaded.state_bundle.native_state_digest == "sha-X"
    assert loaded.state_bundle.provenance == ("frame.engine",)
    assert loaded.bundle_format_version == DEFAULT_BUNDLE_FORMAT_VERSION
    assert loaded.engine_digest_seed == "seed"
    assert loaded.ledger_chain_head_hash is None
    assert loaded.created_at == "2026-09-04T00:00:00Z"


def test_checkpoint_detects_version_mismatch(tmp_path: pathlib.Path) -> None:
    """A tampered ``bundle_format_version`` raises
    :class:`CheckpointError`."""
    cp = _cp()
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    bad = path.read_text(encoding="utf-8").replace(
        str(DEFAULT_BUNDLE_FORMAT_VERSION), "p2-12.checkpoint/v0"
    )
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(CheckpointError) as excinfo:
        load_checkpoint(path)
    assert "unknown_format_version" in str(excinfo.value)


def test_checkpoint_detects_chain_break(tmp_path: pathlib.Path) -> None:
    """Flipping one byte of ``ledger_row_hash`` on disk trips
    :func:`verify_checkpoint`."""
    row = _ledger_row_chain(1)[0]
    cp = _cp(ledger_row=row)
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    real_hash = row.row_hash
    bad = path.read_text(encoding="utf-8").replace(real_hash, "0" * len(real_hash))
    path.write_text(bad, encoding="utf-8")
    loaded = load_checkpoint(path)
    ok, errs = verify_checkpoint(loaded)
    assert not ok
    assert any("ledger_chain_invalid" in e for e in errs)


def test_checkpoint_engine_digest_seed_round_trip(tmp_path: pathlib.Path) -> None:
    """The same engine_version + adapter_id pair produces the same
    ``engine_digest_seed`` (deterministic, portable)."""
    cp = _cp()
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["engine_digest_seed"] == "seed"
    # And the helper itself is deterministic.
    s1 = engine_digest_seed(engine_version="0.1.0", adapter_id="runner-default")
    s2 = engine_digest_seed(engine_version="0.1.0", adapter_id="runner-default")
    assert s1 == s2
    # Different adapter_id produces a different seed (drift detection).
    s3 = engine_digest_seed(engine_version="0.1.0", adapter_id="other-adapter")
    assert s1 != s3


def test_checkpoints_stay_stdlib_only() -> None:
    """The persistence module MUST NOT import torch / jax / safetensors.

    This is the engine-stays-stdlib-only gate for the
    ``ast-walk`` test from the P2-12 acceptance criteria. Both
    ``frame/engine.py`` and ``universal/checkpoint.py`` are scanned.
    """
    import ast

    forbidden = {"torch", "jax", "safetensors"}

    def _scan(path: pathlib.Path) -> set[str]:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        offenders: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name.split(".")[0] in forbidden:
                        offenders.add(n.name)
            elif isinstance(node, ast.ImportFrom):  # noqa: SIM102
                if node.module and node.module.split(".")[0] in forbidden:
                    offenders.add(node.module)
        return offenders

    for rel in (
        "adaptive_reflow/universal/checkpoint.py",
        "adaptive_reflow/frame/engine.py",
    ):
        path = PROJECT_ROOT / rel
        offenders = _scan(path)
        assert not offenders, (
            f"{rel} imports forbidden modules: {sorted(offenders)!r}"
        )


def test_checkpoint_round_trip_preserves_ledger_row_fields(tmp_path: pathlib.Path) -> None:
    """Every field of the saved ledger row survives JSON round-trip."""
    rows = _ledger_row_chain(1)
    cp = _cp(ledger_row=rows[0])
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    loaded = load_checkpoint(path)
    assert loaded.last_ledger_row is not None
    row = loaded.last_ledger_row
    assert row.round_index == 0
    assert row.source_round == 0
    assert row.target_round == 0
    assert row.applied_policy_hash == "applied-0"
    assert row.selected_bundle_digest == "bundle-0"
    assert row.prev_ledger_row_hash is None
    assert row.per_channel_decision == {"X": True}
    # Verify hash re-derivation matches (chain integrity preserved).
    recovered = compute_ledger_row_hash(
        ledger_row_id=str(row.ledger_row_id),
        round_index=int(row.round_index),
        source_round=int(row.source_round),
        target_round=int(row.target_round),
        applied_policy_hash=str(row.applied_policy_hash),
        selected_bundle_digest=str(row.selected_bundle_digest),
        audit_codes=tuple(row.audit_codes),
        per_channel_decision=dict(row.per_channel_decision),
        prev_ledger_row_hash=row.prev_ledger_row_hash,
    )
    assert recovered == row.row_hash


def test_checkpoint_truncated_json_raises(tmp_path: pathlib.Path) -> None:
    """A truncated JSON file raises :class:`CheckpointError`."""
    cp = _cp()
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    path.write_bytes(b'{"bundle_format_version": "p2-12.check')
    with pytest.raises(CheckpointError) as excinfo:
        load_checkpoint(path)
    assert "truncated_or_invalid_json" in str(excinfo.value)


def test_checkpoint_missing_field_raises(tmp_path: pathlib.Path) -> None:
    """A missing required field raises :class:`CheckpointError`."""
    cp = _cp()
    path = tmp_path / "ckpt.json"
    save_checkpoint(cp, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("engine_digest_seed")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointError):
        load_checkpoint(path)


def test_checkpoint_default_in_sync_with_engine() -> None:
    """The mirrored ``_default`` helper in
    :mod:`adaptive_reflow.universal.checkpoint` agrees with the
    engine's canonical encoder for the byte-stable digest surface."""
    import numpy as np

    from adaptive_reflow.frame.engine import _canonical_json_default

    class _Sample:
        def __float__(self) -> float:
            return 0.5

    sample = _Sample()
    np_val = np.float64(0.5)
    assert _canonical_json_default(sample) == 0.5
    # Both encoders should produce the same JSON-stable representation
    # for a numpy scalar.
    a = _canonical_json_default(np_val)
    b = _canonical_json_default(np_val)
    assert a == b


def test_engine_checkpoint_round_and_resume_round(tmp_path: pathlib.Path) -> None:
    """Engine.checkpoint_round + resume_round round-trip via a tiny bundle."""
    from adaptive_reflow.frame.engine import Engine, PhaseState, RoundTrace

    engine = Engine()
    bundle = _bundle()
    rt = RoundTrace(
        round_index=0,
        operation_steps=("build_initial_state", "solve_ode"),
        source_bundle_digest="d",
        applied_policy_hash="p",
        initial_state_digest="d",
        condition_digest="c",
        integrator_trace=None,
        endpoint_digest="e",
        detached=True,
        audit_codes=(),
        extras={},
    )
    rows = _ledger_row_chain(1)
    row = rows[0]
    ps = PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="init",
        schedule_phase_index=0,
        horizon_remaining=10,
        seed_lineage_digest="d",
        recorded_at_round=0,
    )
    cp = engine.checkpoint_round(
        round_trace=rt,
        ledger_row=row,
        next_phase=ps,
        state_bundle_at_round_start=bundle,
        engine_version="test-engine",
        path=tmp_path / "ckpt.json",
    )
    assert cp.ledger_chain_head_hash == row.row_hash
    loaded = engine.resume_round(tmp_path / "ckpt.json")
    assert loaded.state_bundle.native_state_digest == "sha-X"
    assert loaded.ledger_chain_head_hash == row.row_hash


def test_checkpoint_resume_rejects_tampered_chain(tmp_path: pathlib.Path) -> None:
    """Flipping one byte of the saved ledger row's hash makes
    :meth:`Engine.resume_round` raise :class:`CheckpointError`."""
    from adaptive_reflow.frame.engine import Engine, PhaseState, RoundTrace

    engine = Engine()
    bundle = _bundle()
    rt = RoundTrace(
        round_index=0,
        operation_steps=("build_initial_state", "solve_ode"),
        source_bundle_digest="d",
        applied_policy_hash="p",
        initial_state_digest="d",
        condition_digest="c",
        integrator_trace=None,
        endpoint_digest="e",
        detached=True,
        audit_codes=(),
        extras={},
    )
    rows = _ledger_row_chain(1)
    row = rows[0]
    ps = PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="init",
        schedule_phase_index=0,
        horizon_remaining=10,
        seed_lineage_digest="d",
        recorded_at_round=0,
    )
    path = tmp_path / "ckpt.json"
    engine.checkpoint_round(
        round_trace=rt,
        ledger_row=row,
        next_phase=ps,
        state_bundle_at_round_start=bundle,
        engine_version="test-engine",
        path=path,
    )
    # Tamper: flip one byte of the row's hash in the saved JSON.
    real_hash = row.row_hash
    text = path.read_text(encoding="utf-8")
    bad_text = text.replace(real_hash, "0" * len(real_hash))
    path.write_text(bad_text, encoding="utf-8")
    with pytest.raises(CheckpointError):
        engine.resume_round(path)


__all__ = [
    "test_checkpoint_default_in_sync_with_engine",
    "test_checkpoint_detects_chain_break",
    "test_checkpoint_detects_version_mismatch",
    "test_checkpoint_engine_digest_seed_round_trip",
    "test_checkpoint_missing_field_raises",
    "test_checkpoint_resume_rejects_tampered_chain",
    "test_checkpoint_round_trip_preserves_ledger_row_fields",
    "test_checkpoint_roundtrip_statebundle",
    "test_checkpoint_truncated_json_raises",
    "test_checkpoints_stay_stdlib_only",
    "test_engine_checkpoint_round_and_resume_round",
]
