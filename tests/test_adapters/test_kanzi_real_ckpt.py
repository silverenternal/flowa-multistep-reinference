"""Real-checkpoint integration test for the Kanzi protein flow-AE adapter (Wave 36).

This module extends the synthetic-mode smoke test in
:mod:`tests.test_adapters.test_kanzi` with a real-checkpoint
integration tier. It verifies that the :class:`KanziAdapter` can:

  1. Resolve the published Kanzi encoder weights path
     (``data/kanzi_ckpt/kanzi_encoder.pt`` — a 530 MB Zip-format
     ``torch.save`` artefact).
  2. Validate the SHA-256 of the checkpoint file against the
     recorded checksum in ``data/kanzi_ckpt/SHA256SUMS``.
  3. Construct the adapter in ``torch`` mode (gated on torch being
     importable in the test environment) and instantiate the
     PyTorch model shell that consumes the checkpoint state-dict.
  4. Run the full Protocol round-trip (build -> compose_condition
     -> solve_ode -> observe_endpoint -> export_trajectory) in
     ``torch`` mode and verify the trace is finite + shape-correct.
  5. Verify byte-stability: two consecutive rounds with the same
     seed produce byte-identical ``native_state_digest`` and
     ``integrator_config_hash``.
  6. Run the D.5 8-check conformance battery against the real-ckpt
     adapter.

Skip behaviour
--------------

The real-ckpt test tier is gated on **two** environmental conditions:

* ``torch`` importable in the test environment (CPU-only is fine;
  the test never moves tensors to a CUDA device).
* The Kanzi checkpoint exists at the resolved path with the
  recorded SHA-256.

When either condition is unmet the test is **skipped with a
documented reason** rather than failing — the synthetic-mode tests in
``test_kanzi.py`` are the canonical CPU-only path; the real-ckpt test
tier is an integration gate, not a unit test.

Expected environment
--------------------

The published Kanzi encoder (Shah et al. 2026, ICLR 2026,
``arXiv:2510.00351``) is a transformer-based flow-AE with
``L_z <= 128`` continuous latent tokens of dim ``d=64``. The
published checkpoint is hosted at
https://drive.google.com/uc?export=download&id=1ZOcqJ9E3aC-m6letqXR3iruNBMzMKAEm
(``cleaned_model.pt``; SHA-256
``c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270``).

The CKPT_DIR is ``data/kanzi_ckpt/``; ``kanzi_encoder.pt`` is a
symlink to ``cleaned_model.pt`` so both names resolve to the same
SHA-256.

16 tests; CPU-only when torch is importable, otherwise skip.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from adaptive_reflow.adapters.kanzi import (
    KANZI_AR_SEQ_LENGTH,
    KANZI_CHANNELS,
    KANZI_CONFIG_HASH,
    KANZI_LATENT_CLAMP,
    KANZI_LATENT_DIM,
    KANZI_STATE_SHAPE,
    KANZI_VOCAB_SIZE,
    KanziAdapter,
    KanziCapabilities,
    kanzi_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.universal import FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    StateBundle,
    validate_state_bundle,
)
from tests.test_adapters.conformance_battery import (
    CHECKS,
    check_adapter_byte_stable,
    check_adapter_default_mode_is_synthetic,
    check_adapter_handles_empty_batch,
    check_adapter_handles_zero_noise,
    check_adapter_has_velocity_field,
    check_adapter_protocol_surface_matches,
    check_adapter_registered_in_init,
    check_adapter_uses_abstract_interfaces,
)

# Canonical paths for the real-ckpt integration tier.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CKPT_DIR = REPO_ROOT / "data" / "kanzi_ckpt"
SHA256SUMS_PATH = CKPT_DIR / "SHA256SUMS"
KANZI_CKPT_FILENAME = "kanzi_encoder.pt"  # symlink -> cleaned_model.pt
KANZI_CKPT_REAL_FILENAME = "cleaned_model.pt"

# Recorded SHA-256 of the published Kanzi encoder (verified on
# 2026-09-05). The checksum is loaded from the SHA256SUMS file at
# test collection time; this constant is the canonical expected
# value used in the static fingerprint assertion.
EXPECTED_SHA256 = (
    "c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270"
)


# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_expected_sha256() -> str | None:
    """Load the recorded SHA-256 from the SHA256SUMS sidecar file.

    Returns the hex digest when the sidecar exists and parses; returns
    ``None`` otherwise. The :data:`EXPECTED_SHA256` constant is the
    canonical value used by the static fingerprint assertion.
    """
    if not SHA256SUMS_PATH.exists():
        return None
    for line in SHA256SUMS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Format is `<hex>  <filename>  (<comment>)`.
        head = line.split(None, 1)
        if len(head) >= 2 and head[0].lower().startswith(
            EXPECTED_SHA256.lower()[:8]
        ):
            return head[0].lower()
    return None


# Pre-compute the expected SHA-256 at collection time so the test
# body can use a single comparison.
EXPECTED_SHA256_FROM_SUMS: str | None = _load_expected_sha256()


# Conditions: torch + ckpt + checksum must all be present for the
# real-ckpt test tier to run. Build a single skip reason string that
# the fixtures can return.
def _build_skip_reason() -> str | None:
    if not torch_is_available():
        return (
            "real-ckpt test tier requires `torch` (CPU-only is fine); "
            "not installed in this environment"
        )
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not resolved.exists():
        return (
            f"real-ckpt test tier requires the Kanzi weights at "
            f"{CKPT_DIR / KANZI_CKPT_FILENAME} (or the GH release "
            f"filename `cleaned_model.pt`); none present"
        )
    if EXPECTED_SHA256_FROM_SUMS is None:
        return (
            f"real-ckpt test tier requires {SHA256SUMS_PATH} to "
            f"exist with a recorded SHA-256; missing"
        )
    return None


_REAL_CKPT_SKIP_REASON = _build_skip_reason()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def kanzi_real_ckpt_path() -> Path:
    """Resolve and return the real Kanzi checkpoint path."""
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None and resolved.exists(), (
        f"Kanzi weights not found at any candidate location under "
        f"{CKPT_DIR}; expected `{KANZI_CKPT_REAL_FILENAME}` or "
        f"`{KANZI_CKPT_FILENAME}` (symlink)"
    )
    return resolved


@pytest.fixture(scope="module")
def kanzi_real_ckpt_sha256(kanzi_real_ckpt_path: Path) -> str:
    """Compute the SHA-256 of the resolved real Kanzi checkpoint."""
    return _sha256_file(kanzi_real_ckpt_path)


@pytest.fixture(scope="module")
def kanzi_real_adapter() -> KanziAdapter:
    """Build a Kanzi adapter in ``torch`` mode (real-ckpt path).

    Skips the entire test module when torch is not importable, the
    ckpt is missing, or the recorded SHA-256 is unavailable.
    """
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    return KanziAdapter(
        weights_path=resolved,
        force_mode="torch",
        num_steps=2,
        family_id="PF00001.21",
    )


# ---------------------------------------------------------------------------
# 1. Resolution / checksum / path
# ---------------------------------------------------------------------------


def test_resolve_weights_path_finds_real_ckpt() -> None:
    """The adapter's path resolver finds the real Kanzi ckpt.

    This test does NOT require torch — it exercises the
    ``kanzi_resolve_weights_path`` lookup which is a stdlib-only
    filesystem probe.
    """
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None, (
        "kanzi_resolve_weights_path returned None; expected to find "
        f"{CKPT_DIR / KANZI_CKPT_FILENAME}"
    )
    assert resolved.exists(), f"resolved path {resolved} does not exist"
    # Resolved parent must equal the canonical CKPT_DIR (comparing
    # absolute paths so the default-relative `Path("data")` lookup
    # is normalised correctly).
    assert resolved.parent.resolve() == CKPT_DIR.resolve(), (
        f"resolved path {resolved} is not under {CKPT_DIR}"
    )


def test_real_ckpt_size_is_about_530mb() -> None:
    """The real ckpt is approximately 530 MB (matches GH release)."""
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not resolved.exists():
        pytest.skip("real Kanzi ckpt not on disk")
    size = resolved.stat().st_size
    # 530 MB ± 5 MB tolerance to accommodate future re-uploads.
    assert 500 * 1024 * 1024 <= size <= 560 * 1024 * 1024, (
        f"real Kanzi ckpt size {size} bytes is outside expected "
        f"500–560 MB window"
    )


def test_real_ckpt_sha256_matches_recorded() -> None:
    """The real ckpt's SHA-256 matches the recorded checksum.

    This is the load-bearing integrity check that proves the
    download was not corrupted; the recorded value lives in
    ``data/kanzi_ckpt/SHA256SUMS``.
    """
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not resolved.exists():
        pytest.skip("real Kanzi ckpt not on disk")
    if EXPECTED_SHA256_FROM_SUMS is None:
        pytest.skip(
            f"{SHA256SUMS_PATH} missing or unparseable; cannot verify "
            "SHA-256"
        )
    actual = _sha256_file(resolved)
    assert actual.lower() == EXPECTED_SHA256_FROM_SUMS.lower(), (
        f"SHA-256 mismatch: got {actual}, expected "
        f"{EXPECTED_SHA256_FROM_SUMS}"
    )
    # Belt-and-braces: also assert the constant matches the recorded
    # SHA-256 (defends against drift in either direction).
    assert EXPECTED_SHA256.lower() == EXPECTED_SHA256_FROM_SUMS.lower(), (
        f"EXPECTED_SHA256 constant {EXPECTED_SHA256} drifted from "
        f"recorded checksum {EXPECTED_SHA256_FROM_SUMS}"
    )


def test_sha256sums_file_format_is_standard() -> None:
    """The SHA256SUMS sidecar file uses the standard `sha256sum` format."""
    if not SHA256SUMS_PATH.exists():
        pytest.skip(f"{SHA256SUMS_PATH} does not exist")
    lines = SHA256SUMS_PATH.read_text(encoding="utf-8").splitlines()
    # At least one non-comment line.
    body_lines = [
        ln for ln in lines if ln.strip() and not ln.strip().startswith("#")
    ]
    assert body_lines, "SHA256SUMS has no body lines"
    # First body line must be `<hex><ws><filename>...`
    first = body_lines[0].split(None, 1)
    assert len(first) == 2, (
        f"first SHA256SUMS body line is malformed: {body_lines[0]!r}"
    )
    hex_part = first[0]
    assert len(hex_part) == 64 and all(
        c in "0123456789abcdef" for c in hex_part.lower()
    ), f"first body line hex part is not 64-char hex: {hex_part!r}"


# ---------------------------------------------------------------------------
# 2. Real-ckpt adapter instantiation
# ---------------------------------------------------------------------------


def test_real_adapter_in_torch_mode() -> None:
    """KanziAdapter constructs in ``torch`` mode when ckpt is on disk."""
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    adapter = KanziAdapter(
        weights_path=resolved,
        force_mode="torch",
        num_steps=2,
    )
    assert adapter._mode == "torch"
    assert adapter._model is not None, (
        "torch-mode adapter must populate _model with a non-None "
        "PyTorch module after construction"
    )
    assert adapter._torch_dtype is not None


def test_real_adapter_capabilities_match_synthetic() -> None:
    """The torch-mode adapter advertises the same capability surface."""
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    adapter = KanziAdapter(
        weights_path=resolved,
        force_mode="torch",
        num_steps=2,
    )
    caps = adapter.capabilities()
    assert isinstance(caps, KanziCapabilities)
    assert caps.has_ode_integration_surface
    assert caps.has_discrete_channels
    assert caps.has_continuous_channels
    # Wave 92 — capabilities reflect the per-instance state_shape
    # (real-mode: (64, 512)) rather than the module-level abstract.
    assert caps.state_shape == (64, 512)
    assert caps.state_shape == adapter.state_shape
    assert caps.supported_channels == KANZI_CHANNELS
    assert caps.native_config_hash == KANZI_CONFIG_HASH


def test_real_adapter_satisfies_runtime_protocol() -> None:
    """The torch-mode adapter satisfies the runtime Protocol."""
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    adapter = KanziAdapter(
        weights_path=resolved,
        force_mode="torch",
        num_steps=2,
    )
    assert isinstance(adapter, FlowMatchingODEAdapter)


# ---------------------------------------------------------------------------
# 3. Smoke round-trip in torch mode
# ---------------------------------------------------------------------------


def test_real_adapter_smoke_round_trip(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter runs build -> solve_ode -> observe_endpoint."""
    adapter = kanzi_real_adapter
    bundle = adapter.build_initial_state(batch_id="rc1", sample_id="rs1")
    ok, errs = validate_state_bundle(bundle)
    assert ok, errs
    assert bundle.detach_proof is True

    delta = ODEConditionDelta(
        delta_spec={
            "num_steps": 2,
            "sampler_id": "euler",
            "guidance_scale": 1.0,
            "family_id": "PF00001.21",
        },
        source="test_real_ckpt",
        target_round=1,
        calibration_artifact_hash=KANZI_CONFIG_HASH,
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=42)
    assert trace.steps == 2
    assert 0.0 <= trace.accept_rate <= 1.0
    assert trace.native_state_digest
    assert trace.integrator_config_hash

    endpoint = adapter.observe_endpoint(trace, bundle)
    ok, errs = validate_state_bundle(endpoint)
    assert ok, errs

    traj = adapter.export_trajectory(trace)
    assert traj is not None
    # Wave 92 — real-mode trajectory uses the ckpt-derived shape
    # (T, L_abstract, n_channels_decoder) = (3, 64, 512). Pre-Wave-92
    # the trajectory had shape ``(T, 64, 64)`` and the upstream DAE
    # decode call raised a shape mismatch on the first sample.
    assert traj.shape == (3, 64, 512)
    assert traj.shape == (3, *adapter.state_shape)
    import numpy as np
    assert np.isfinite(traj).all(), (
        "real-ckpt torch-mode trajectory must be finite everywhere"
    )
    assert np.abs(traj).max() <= KANZI_LATENT_CLAMP + 1e-9, (
        "real-ckpt torch-mode trajectory must respect latent clamp"
    )


def test_real_adapter_heun_solver_smoke(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter runs the Heun (2nd-order) integrator."""
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    adapter = kanzi_real_adapter
    bundle = adapter.build_initial_state(batch_id="rc2", sample_id="rs2")
    delta = ODEConditionDelta(
        delta_spec={
            "num_steps": 2,
            "sampler_id": "heun",
            "guidance_scale": 1.0,
            "family_id": "PF00001.21",
        },
        source="test_real_ckpt",
        target_round=1,
        calibration_artifact_hash=KANZI_CONFIG_HASH,
    )
    delta = adapter.compose_condition(bundle, delta)
    trace = adapter.solve_ode(bundle, delta, seed=7)
    assert trace.steps == 2
    import numpy as np
    traj = adapter.export_trajectory(trace)
    assert traj is not None
    # Wave 92 — Heun real-mode trajectory also uses ckpt shape.
    assert traj.shape == (3, 64, 512)
    assert np.isfinite(traj).all()


# ---------------------------------------------------------------------------
# 4. Byte-stability (deterministic with fixed seed)
# ---------------------------------------------------------------------------


def test_real_adapter_byte_stable(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter is byte-stable across two round-trips with
    identical (batch_id, sample_id, seed) inputs.
    """
    adapter = kanzi_real_adapter
    bundle_a = adapter.build_initial_state(
        batch_id="byte_real", sample_id="stable_real",
    )
    bundle_b = adapter.build_initial_state(
        batch_id="byte_real", sample_id="stable_real",
    )
    assert (
        bundle_a.native_state_digest == bundle_b.native_state_digest
    ), (
        "build_initial_state digest drifted across two calls; "
        "torch-mode is supposed to be deterministic with fixed seed"
    )

    delta_spec = {
        "num_steps": 2,
        "sampler_id": "euler",
        "guidance_scale": 1.0,
        "family_id": "PF00001.21",
    }
    delta_a = adapter.compose_condition(
        bundle_a,
        ODEConditionDelta(
            delta_spec=delta_spec,
            source="test_real_ckpt",
            target_round=1,
            calibration_artifact_hash=KANZI_CONFIG_HASH,
        ),
    )
    delta_b = adapter.compose_condition(
        bundle_b,
        ODEConditionDelta(
            delta_spec=delta_spec,
            source="test_real_ckpt",
            target_round=1,
            calibration_artifact_hash=KANZI_CONFIG_HASH,
        ),
    )
    trace_a = adapter.solve_ode(bundle_a, delta_a, seed=123)
    trace_b = adapter.solve_ode(bundle_b, delta_b, seed=123)
    assert (
        trace_a.native_state_digest == trace_b.native_state_digest
    ), "solve_ode native_state_digest drifted across two calls"
    assert (
        trace_a.integrator_config_hash == trace_b.integrator_config_hash
    ), "solve_ode integrator_config_hash drifted across two calls"


def test_real_adapter_two_independent_seeds_diverge(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter produces different digests for different seeds."""
    adapter = kanzi_real_adapter
    bundle = adapter.build_initial_state(
        batch_id="div", sample_id="seeds",
    )
    delta_spec = {
        "num_steps": 2,
        "sampler_id": "euler",
        "guidance_scale": 1.0,
        "family_id": "PF00001.21",
    }
    delta = adapter.compose_condition(
        bundle,
        ODEConditionDelta(
            delta_spec=delta_spec,
            source="test_real_ckpt",
            target_round=1,
            calibration_artifact_hash=KANZI_CONFIG_HASH,
        ),
    )
    trace_a = adapter.solve_ode(bundle, delta, seed=1)
    trace_b = adapter.solve_ode(bundle, delta, seed=2)
    assert (
        trace_a.native_state_digest != trace_b.native_state_digest
    ), (
        "different seeds must produce different native_state_digests"
    )


# ---------------------------------------------------------------------------
# 5. Conformance battery — 8 checks against the real-ckpt adapter
# ---------------------------------------------------------------------------


# The D.5 conformance battery defines 8 conformance checks; we run
# each against the real-ckpt (torch-mode) adapter to prove the
# real-ckpt tier preserves the framework-wide guarantees.
CONFORMANCE_CHECK_NAMES: tuple[str, ...] = tuple(name for name, _ in CHECKS)


@pytest.mark.parametrize("check_name", CONFORMANCE_CHECK_NAMES)
def test_real_ckpt_conformance_battery(
    check_name: str,
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Each of the 8 D.5 conformance checks passes against the
    torch-mode adapter (real-ckpt integration tier).

    The ``registered_in_init`` check expects the adapter to be
    discoverable in :data:`ADAPTER_REGISTRY`. Kanzi is registered
    via :func:`adaptive_reflow.adapters.build_adapter`, so the check
    passes when the default factory succeeds (it does in synthetic
    mode regardless of torch availability).
    """
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    check_fn = dict(CHECKS)[check_name]
    check_fn(kanzi_real_adapter)


# ---------------------------------------------------------------------------
# 6. Sanity: cross-tier coherence
# ---------------------------------------------------------------------------


def test_real_adapter_state_shape_matches_synthetic() -> None:
    """Wave 92 — abstract (synthetic) and real (ckpt-loaded) adapters
    advertise DIFFERENT state shapes. The synthetic adapter
    advertises the abstract ``(L, d) = (64, 64)`` (used by the
    framework-algorithm integration tier); the real adapter
    advertises the ckpt-derived ``(L_abstract, n_channels_decoder) =
    (64, 512)`` so the trajectory endpoint can be fed into the
    upstream :class:`DAE.decode` bridge.

    Pre-Wave-92 the real adapter inherited the abstract
    ``KANZI_STATE_SHAPE``; the upstream decode call expected
    ``(B, L, 512)`` and the shape mismatch made the framework-arm
    paper-metric unmeasurable at N=1000 (Wave 91 §3).
    """
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    real = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    synthetic = KanziAdapter(force_mode="synthetic", num_steps=2)
    # Synthetic mode: abstract shape preserved (no regression).
    assert synthetic.state_shape == KANZI_STATE_SHAPE == (64, 64)
    # Real mode: ckpt-derived shape; the latent dim matches the
    # upstream DAEConfig ``n_channels_decoder = 512``.
    assert real.state_shape == (64, 512)
    assert real.state_shape != synthetic.state_shape


def test_real_adapter_empty_batch_handled(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter handles minimal single-char batch ids."""
    bundle = kanzi_real_adapter.build_initial_state(batch_id="x", sample_id="y")
    assert isinstance(bundle, StateBundle)
    assert bundle.detach_proof is True


def test_real_adapter_zero_noise_boundary(
    kanzi_real_adapter: KanziAdapter,
) -> None:
    """Real-ckpt adapter handles ``num_steps=1`` (zero-noise boundary)."""
    bundle = kanzi_real_adapter.build_initial_state(batch_id="z", sample_id="n")
    delta = ODEConditionDelta(
        delta_spec={
            "num_steps": 1,
            "sampler_id": "euler",
            "guidance_scale": 1.0,
            "family_id": "PF00001.21",
        },
        source="test_real_ckpt",
        target_round=1,
        calibration_artifact_hash=KANZI_CONFIG_HASH,
    )
    delta = kanzi_real_adapter.compose_condition(bundle, delta)
    trace = kanzi_real_adapter.solve_ode(bundle, delta, seed=0)
    assert trace.steps >= 1


# ---------------------------------------------------------------------------
# 7. Wave 92 — ckpt model_cfg load + abstract-vs-real mode split
# ---------------------------------------------------------------------------


def test_load_ckpt_dims_round_trip() -> None:
    """Wave 92 — ``_load_ckpt_dims`` correctly extracts real dims from ckpt.

    The 3 WRONG constants
    (:data:`KANZI_LATENT_DIM = 64`,
    :data:`KANZI_VOCAB_SIZE = 64`,
    :data:`KANZI_AR_SEQ_LENGTH = 64`)
    previously claimed the Wave 36 ckpt had ``(64, 64, 64)`` shape.
    The ckpt's ``model_cfg`` actually specifies ``n_channels_decoder =
    512`` and ``levels = (8, 5, 5, 5)`` (codebook size 1000). This
    test asserts the load surfaces the correct values.
    """
    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    adapter = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    # After ``_load_ckpt_dims`` the four ``_real_*`` attributes are
    # populated from the ckpt's ``model_cfg`` (not the abstract
    # constants).
    assert adapter._real_latent_dim == 512
    assert adapter._real_vocab_size == 1000
    assert adapter._real_levels == (8, 5, 5, 5)
    # ``_real_seq_length`` is None (per-record backbone-dependent).
    assert adapter._real_seq_length is None
    assert adapter._abstract_mode is False


def test_state_shape_abstract_vs_real() -> None:
    """Wave 92 — abstract and real adapters return distinct state shapes.

    Abstract (synthetic / no-ckpt): ``(L, d) = (64, 64)``.
    Real (ckpt loaded): ``(L, n_channels_decoder) = (64, 512)``.
    """
    syn = KanziAdapter(force_mode="synthetic", num_steps=2)
    assert syn._abstract_mode is True
    assert syn.state_shape == (64, 64)
    assert syn._real_state_shape == (64, 64)

    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    assert resolved is not None
    real = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    assert real._abstract_mode is False
    assert real.state_shape == (64, 512)
    assert real._real_state_shape == (64, 512)


def test_abstract_constants_unchanged_for_back_compat() -> None:
    """Wave 92 — KANZI_LATENT_DIM / KANZI_VOCAB_SIZE / KANZI_AR_SEQ_LENGTH
    alias the ABSTRACT values so the 18+ existing synthetic-mode
    tests are byte-identical.

    The existing adapter constant names point at the abstract
    defaults (``(64, 64, 64)``). The real values are surfaced via
    :attr:`KanziAdapter._real_*` attributes and the new
    :data:`KANZI_DEFAULT_REAL_LATENT_DIM` /
    :data:`KANZI_DEFAULT_REAL_VOCAB_SIZE` module constants.
    """
    # Existing names: still point at abstract defaults.
    assert KANZI_LATENT_DIM == 64
    assert KANZI_VOCAB_SIZE == 64
    assert KANZI_AR_SEQ_LENGTH == 64
    assert KANZI_STATE_SHAPE == (64, 64)
    # New names: abstract / real split is explicit.
    from adaptive_reflow.adapters.kanzi import (
        KANZI_ABSTRACT_LATENT_DIM,
        KANZI_ABSTRACT_VOCAB_SIZE,
        KANZI_ABSTRACT_STATE_SHAPE,
        KANZI_DEFAULT_REAL_LATENT_DIM,
        KANZI_DEFAULT_REAL_VOCAB_SIZE,
    )
    assert KANZI_ABSTRACT_LATENT_DIM == 64
    assert KANZI_ABSTRACT_VOCAB_SIZE == 64
    assert KANZI_ABSTRACT_STATE_SHAPE == (64, 64)
    # Real defaults match the Wave 36 ckpt values.
    assert KANZI_DEFAULT_REAL_LATENT_DIM == 512
    assert KANZI_DEFAULT_REAL_VOCAB_SIZE == 1000


# ---------------------------------------------------------------------------
# 8. Wave 113.A — _KanziDAEShim.forward backbone-coord migration
# ---------------------------------------------------------------------------
#
# Replaces the Wave 112.C-2 fail-fast ``NotImplementedError`` placeholder
# (RC-2 option B, commit 87d46ec) with the real two-call upstream pipeline:
#   1. ``DAE.encode(x)``  → ``z_BLD`` (codebook-quantized latent)
#   2. ``DAE.net(x, t, z_BLD=z)`` → velocity field ``(B, L, d)``
#
# Acceptance: shim returns non-zero output, deterministic in eval mode,
# shape & device match the input contract used by _torch_velocity_field.


def test_kanzi_shim_real_dae_wired() -> None:
    """Wave 113.A — shim instance is the real ``_KanziDAEShim`` (not stub).

    The Wave 99 regression test at :func:`test_load_torch_model_returns_real_dae_for_real_ckpt`
    asserts the same property; this duplicate copy makes the Wave 113.A
    intent explicit and is the test name referenced in the audit doc.
    """
    import sys

    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not Path(resolved).exists():
        pytest.skip(_REAL_CKPT_SKIP_REASON or "ckpt missing")
    # The kanzi_venv may not be on sys.path in some CI shards — vendor it.
    _KANZI_SRC = REPO_ROOT / "data" / "kanzi_upstream" / "src"
    if str(_KANZI_SRC) not in sys.path:
        sys.path.insert(0, str(_KANZI_SRC))

    adapter = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    shim = adapter._model  # constructed in __init__ via _load_torch_model
    assert shim is not None
    # The real upstream DAE was wired in (not the random-weights stub).
    assert type(shim).__name__ == "_KanziDAEShim", (
        f"Expected _KanziDAEShim, got {type(shim).__name__}"
    )


def test_kanzi_shim_forward_returns_nonzero_output() -> None:
    """Wave 113.A — shim forward returns a non-zero tensor (real backbone work).

    The Wave 112.C-2 placeholder raised ``NotImplementedError`` (no work),
    so the framework arm was a silent no-op. After Wave 113.A, the shim
    runs the real ``DAE.encode`` + ``DAE.net`` pipeline, producing a
    non-zero velocity field whose ``abs().max() > 0`` and whose
    ``std() > 0.05`` distinguishes it from the constant-zeros stub.

    Note: input shape is ``(B=1, L=64, 3)`` — the upstream
    ``DAE.encode``/``DAE.net`` consume backbone coords with
    ``channels_in=3`` (``RnFlowMatcherConfig.channels_in=3`` default).
    The adapter's ``(L, n_channels_decoder) = (64, 512)`` state shape
    is the post-``project_out`` space and is the OUTPUT of ``DAE.net``,
    not the input — a projection bridge (``project_out⁻¹``) is a
    Wave 112.D follow-up.
    """
    import sys

    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not Path(resolved).exists():
        pytest.skip(_REAL_CKPT_SKIP_REASON or "ckpt missing")
    _KANZI_SRC = REPO_ROOT / "data" / "kanzi_upstream" / "src"
    if str(_KANZI_SRC) not in sys.path:
        sys.path.insert(0, str(_KANZI_SRC))

    import torch as _torch  # local — torch_is_available() is in skip guard

    adapter = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    shim = adapter._model  # constructed in __init__ via _load_torch_model
    assert shim is not None

    # Real backbone-coord-shaped input: (B=1, L=64, 3) backbone coords.
    _torch.manual_seed(0)
    x = _torch.randn(1, 64, 3)
    t = _torch.tensor([0.5])
    family = _torch.zeros(1, 1152)  # pair_embedder_dim — accepted, unused

    shim.eval()
    with _torch.no_grad():
        v = shim(x, t, family=family)

    # Acceptance #1: non-zero output (NOT zeros_like(x)).
    assert _torch.abs(v).max().item() > 0.0, (
        f"BUG REGRESSION: shim returned all-zeros velocity (abs.max=0). "
        "Backbone-coord migration is broken — DAE.encode + DAE.net "
        "did not run."
    )
    # Same threshold used by test_load_torch_model_returns_real_dae_for_real_ckpt
    assert v.std().item() > 0.05, (
        f"BUG REGRESSION: velocity field std={v.std().item():.6f} — "
        "shim is producing zeros / random noise, not a real upstream DAE forward."
    )


def test_kanzi_shim_forward_shape_and_device() -> None:
    """Wave 113.A — output shape and device match the input contract.

    Upstream ``DAE.net`` is a DiT with ``channels_in=3`` and the
    ``FinalLinear(n_channels, channels_in=3)`` projects the velocity
    field back to backbone-coord space — so input and output are both
    ``(B, L, 3)``. The Wave 112.C-3 device wire ensures tensors stay
    on CUDA when available.
    """
    import sys

    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not Path(resolved).exists():
        pytest.skip(_REAL_CKPT_SKIP_REASON or "ckpt missing")
    _KANZI_SRC = REPO_ROOT / "data" / "kanzi_upstream" / "src"
    if str(_KANZI_SRC) not in sys.path:
        sys.path.insert(0, str(_KANZI_SRC))

    import torch as _torch  # local — torch_is_available() is in skip guard

    adapter = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    shim = adapter._model  # constructed in __init__ via _load_torch_model
    assert shim is not None

    # Move shim to CUDA if available (matches Wave 112.A RC-1 fix).
    if _torch.cuda.is_available():
        shim = shim.to("cuda")

    x = _torch.randn(
        1, 64, 3,
        device=("cuda" if _torch.cuda.is_available() else "cpu"),
    )
    t = _torch.tensor(
        [0.5],
        device=("cuda" if _torch.cuda.is_available() else "cpu"),
    )
    family = _torch.zeros(
        1, 1152,
        device=("cuda" if _torch.cuda.is_available() else "cpu"),
    )

    shim.eval()
    with _torch.no_grad():
        v = shim(x, t, family=family)

    # Acceptance #2: shape (B, L, channels_in=3) = (1, 64, 3).
    assert tuple(v.shape) == (1, 64, 3), (
        f"Bad velocity shape: {tuple(v.shape)} — expected (1, 64, 3)"
    )
    # Acceptance #4: device matches input.
    assert v.device == x.device, (
        f"Device mismatch: shim returned {v.device} but input was {x.device}"
    )


def test_kanzi_shim_forward_deterministic_in_eval_mode() -> None:
    """Wave 113.A — same (x, t) yields identical output (eval mode determinism).

    The upstream ``DAE.encode`` uses FSQ (no stochastic sampling) and
    ``DAE.net`` is a deterministic DiT; in eval mode the shim must be
    deterministic across repeated calls with the same input.
    """
    import sys

    if _REAL_CKPT_SKIP_REASON is not None:
        pytest.skip(_REAL_CKPT_SKIP_REASON)
    resolved = kanzi_resolve_weights_path()
    if resolved is None or not Path(resolved).exists():
        pytest.skip(_REAL_CKPT_SKIP_REASON or "ckpt missing")
    _KANZI_SRC = REPO_ROOT / "data" / "kanzi_upstream" / "src"
    if str(_KANZI_SRC) not in sys.path:
        sys.path.insert(0, str(_KANZI_SRC))

    import torch as _torch  # local — torch_is_available() is in skip guard

    adapter = KanziAdapter(
        weights_path=resolved, force_mode="torch", num_steps=2,
    )
    shim = adapter._model  # constructed in __init__ via _load_torch_model
    assert shim is not None

    _torch.manual_seed(0)
    x = _torch.randn(1, 64, 3)
    t = _torch.tensor([0.5])
    family = _torch.zeros(1, 1152)

    shim.eval()
    with _torch.no_grad():
        v1 = shim(x, t, family=family)
        v2 = shim(x, t, family=family)

    # Acceptance #3: same x + same t → identical output (eval mode).
    assert _torch.allclose(v1, v2, atol=1e-6), (
        "shim is non-deterministic in eval mode — DAE.encode/DAE.net "
        "have an unwanted stochastic source (FSQ dropout? pair noise?)."
    )