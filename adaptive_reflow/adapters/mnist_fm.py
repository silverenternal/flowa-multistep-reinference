"""Real CPU-runnable MNIST rectified flow adapter (EXP-1 — phase 1 runtime).

Implements the :class:`FlowMatchingODEAdapter` Protocol against a small
velocity-field UNet (~600K parameters) trained offline on MNIST 28x28
grayscale images. Source ``N(0, I_784)`` clamped to ``[-1, 1]``; target
the empirical MNIST digit distribution (10K test images from
``torchvision.datasets.MNIST`` or the offline ``MNIST/raw/*.gz`` cache).
RK4 is the byte-deterministic default integrator; restart semantics
blend the prior endpoint with fresh ``N(0, I_784)`` via memory fraction
``m = 1 - beta``.

This is the *runtime* counterpart to
:mod:`adaptive_reflow.adapters.mnist_fm_train` (the offline trainer
that produces the ``.npz`` weights files). It is the second NumPy
adapter under :mod:`adaptive_reflow.adapters` (the first being
:class:`TwoDimFMAdapter`).

State shape convention
----------------------

``state_shape = (784,)`` is the canonical surface the engine sees
(linear flat array of 784 pixels in ``[-1, 1]``). Internally the
adapter reshapes to ``(1, 28, 28)`` for the UNet forward and back to
``(784,)`` at the protocol boundary. This matches the
:class:`TwoDimFMAdapter` convention where ``state_shape = (2,)`` is a
flat surface over a 2D coordinate vector.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.blender import LinearBlender, RestartBlenderProtocol
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

from .mnist_fm_train import (  # noqa: E402 — runtime numpy dep, opt-in extra
    MNIST_FLAT_DIM,
    load_weights,
    velocity_field_forward,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


MNIST_FM_CHANNELS: tuple[ChannelName, ...] = (ChannelName("x"),)
MNIST_FM_CONFIG_HASH: str = "mnist_fm:cfg:v1"
MNIST_FM_CONFIG_VERSION: str = "0.1.0"
AUDIT_MNIST_FM_RESTART_BLEND: str = "mnist_fm_restart_blend"
ERR_MNIST_FM_INTEGRATOR_OVERFLOW: str = "mnist_fm_integrator_overflow"
AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED: str = "forward_noise_applied"

# Channel-domain declaration for the adapter's sole channel.
MNIST_FM_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("x"): "continuous",
}

# Default weights path resolution: data/ at the repo root.
MNIST_FM_DEFAULT_WEIGHTS: Path = Path("data/mnist_fm.npz")

# RK4 integration defaults.
MNIST_FM_NUM_STEPS: int = 50

# Pixel clamp on the trajectory (MNIST digits live in [-1, 1]).
MNIST_FM_CLAMP: float = 1.0

# Internal image shape (used for the UNet forward pass).
MNIST_FM_IMAGE_SHAPE: tuple[int, int, int] = (1, 28, 28)

#: Maximum size of the LRU-bounded ``_native_states`` cache (same bound
#: as :class:`TwoDimFMAdapter`).
MNIST_FM_NATIVE_STATES_MAXSIZE: int = 128

# Local type alias to keep numpy dependency off hot annotation paths.
ArrayF64: TypeAlias = NDArray[np.float64]

#: Default hidden width (informational; the trained UNet's width is
#: determined by the saved ``.npz`` at load time).
MNIST_FM_DEFAULT_BASE_CHANNELS: int = 16

#: Public re-export of the flat 784-dim surface alias (mirrors the
#: trainer module's :data:`MNIST_FLAT_DIM`).
MNIST_FM_FLAT_DIM: int = MNIST_FLAT_DIM


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _seed_from_ids(batch_id: str, sample_id: str, source_round: int) -> int:
    """Derive a deterministic 32-bit seed from ``(batch_id, sample_id, source_round)``."""
    blob = repr((str(batch_id), str(sample_id), int(source_round))).encode("utf-8")
    hex8 = hashlib.sha256(blob).hexdigest()[:8]
    return int(hex8, 16)


def _digest_state(payload: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 hex digest of a payload (sorted keys)."""
    blob = repr((sorted(payload.items(), key=lambda kv: str(kv[0])),)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic hash-stable :class:`TensorRef` from ``label`` + parts."""
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"mnist:x:{hashlib.sha256(blob).hexdigest()[:16]}")


def _unet_evaluate(weights: list[ArrayF64], x: ArrayF64, t: float) -> ArrayF64:
    """Evaluate the velocity UNet ``v_theta(x, t)`` with internal reshapes.

    ``x`` is a flat ``(784,)`` or batched ``(B, 784)`` array in
    ``[-1, 1]``; ``t`` is a scalar float. Returns ``(784,)`` for 1-D
    input or ``(B, 784)`` for 2-D input. The UNet forward reshapes
    internally to ``(B, 1, 28, 28)`` and back.
    """
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 1:
        if arr.shape[0] != MNIST_FLAT_DIM:
            raise ValueError("x_must_have_shape_784")
        arr = arr.reshape(1, MNIST_FLAT_DIM)
        v = velocity_field_forward(weights, arr, float(t))
        return np.asarray(v.reshape(MNIST_FLAT_DIM), dtype=np.float64)
    if arr.ndim == 2:
        if arr.shape[1] != MNIST_FLAT_DIM:
            raise ValueError("x_must_have_shape_b_784")
        v = velocity_field_forward(weights, arr, float(t))
        return np.asarray(v.reshape(arr.shape[0], MNIST_FLAT_DIM), dtype=np.float64)
    raise ValueError("x_must_have_shape_784_or_b_784")


def _integrate_rk4(
    weights: list[ArrayF64],
    x0: ArrayF64,
    t_grid: ArrayF64,
) -> ArrayF64:
    """Pure RK4 integration over ``t_grid``; returns ``(len(t_grid), 784)`` trajectory."""
    x0_arr = np.asarray(x0, dtype=np.float64).reshape(MNIST_FLAT_DIM)
    grid = np.asarray(t_grid, dtype=np.float64).reshape(-1)
    if grid.size < 2:
        raise ValueError("t_grid_must_have_at_least_two_points")
    traj = np.empty((grid.size, MNIST_FLAT_DIM), dtype=np.float64)
    traj[0] = x0_arr
    x_cur = x0_arr.copy()
    for i in range(1, grid.size):
        t0 = float(grid[i - 1])
        t1 = float(grid[i])
        dt = float(t1 - t0)
        k1 = _unet_evaluate(weights, x_cur, t0)
        k2 = _unet_evaluate(weights, x_cur + 0.5 * dt * k1, t0 + 0.5 * dt)
        k3 = _unet_evaluate(weights, x_cur + 0.5 * dt * k2, t0 + 0.5 * dt)
        k4 = _unet_evaluate(weights, x_cur + dt * k3, t1)
        x_cur = x_cur + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        # Numerical safety: clamp pixels to [-1, 1].
        np.clip(x_cur, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=x_cur)
        traj[i] = x_cur
    return traj


def _batched_integrate_rk4(
    weights: list[ArrayF64],
    x0_batch: ArrayF64,
    n_steps: int,
) -> ArrayF64:
    """Pure batched RK4 over ``x0_batch`` of shape ``(batch, 784)``.

    Returns the final ``(batch, 784)`` state after ``n_steps``
    evenly-spaced integration steps on ``[0, 1]``. Used for FID
    population generation.
    """
    if int(n_steps) < 1:
        raise ValueError("n_steps_must_be_positive")
    x0 = np.asarray(x0_batch, dtype=np.float64)
    if x0.ndim != 2 or x0.shape[1] != MNIST_FLAT_DIM:
        raise ValueError("x0_batch_must_have_shape_b_784")
    grid = np.linspace(0.0, 1.0, int(n_steps) + 1, dtype=np.float64)
    x_cur = x0.copy()
    t_cur = float(grid[0])
    for i in range(1, grid.size):
        t_next = float(grid[i])
        h = float(t_next - t_cur)
        k1 = _unet_evaluate(weights, x_cur, t_cur)
        k2 = _unet_evaluate(weights, x_cur + 0.5 * h * k1, t_cur + 0.5 * h)
        k3 = _unet_evaluate(weights, x_cur + 0.5 * h * k2, t_cur + 0.5 * h)
        k4 = _unet_evaluate(weights, x_cur + h * k3, t_next)
        x_cur = x_cur + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        np.clip(x_cur, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=x_cur)
        t_cur = t_next
    return np.asarray(x_cur, dtype=np.float64).reshape(x0.shape[0], MNIST_FLAT_DIM)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MnistFMCapabilities(AdapterCapabilities):
    """Capability surface of the :class:`MnistFmAdapter` (``"x"`` continuous)."""

    def __init__(self) -> None:  # noqa: D401 — dataclass __init__ override
        super().__init__(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            state_shape=(MNIST_FLAT_DIM,),
            supported_channels=MNIST_FM_CHANNELS,
            channel_domains=MNIST_FM_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=MNIST_FM_CONFIG_HASH,
            native_config_version=MNIST_FM_CONFIG_VERSION,
        )


class MnistFmAdapter(FlowMatchingODEAdapter):
    """MNIST 28x28 rectified flow adapter (CPU, NumPy)."""

    pinned_num_steps: int = MNIST_FM_NUM_STEPS
    """Default number of integration steps used by :meth:`solve_ode`."""

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        num_steps: int = MNIST_FM_NUM_STEPS,
        seed_offset: int = 0,
        blender: RestartBlenderProtocol | None = None,
    ) -> None:
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        self._weights_path = (
            Path(weights_path) if weights_path is not None else MNIST_FM_DEFAULT_WEIGHTS
        )
        self._weights: list[ArrayF64] = load_weights(self._weights_path)
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = MnistFMCapabilities()
        self._blender: RestartBlenderProtocol = (
            blender if blender is not None else LinearBlender()
        )

    # ------------------------------------------------------------------
    # 1. Capability handshake
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. LRU-bounded native_states helper
    # ------------------------------------------------------------------

    def _put_native_state(self, digest: str, entry: dict[str, Any]) -> None:
        """Insert ``entry`` under ``digest``; evict the oldest entry past maxsize."""
        if digest in self._native_states:
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > MNIST_FM_NATIVE_STATES_MAXSIZE:
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        """Remove ``digest`` from the cache if present."""
        self._native_states.pop(digest, None)

    # ------------------------------------------------------------------
    # 2. build_initial_state
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        seed = _seed_from_ids(
            str(batch_id),
            str(sample_id),
            int(self._seed_offset) + 0,
        )
        rng = np.random.default_rng(seed)
        x0 = rng.standard_normal(MNIST_FLAT_DIM).astype(np.float64)
        np.clip(x0, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=x0)
        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "x0_first8": [float(x0[i]) for i in range(8)],
                "x0_last8": [float(x0[i]) for i in range(MNIST_FLAT_DIM - 8, MNIST_FLAT_DIM)],
            }
        )
        self._put_native_state(
            digest,
            {
                "x0": np.asarray(x0, dtype=np.float64).reshape(MNIST_FLAT_DIM),
                "source_round": 0,
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("x"): _make_ref(
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="per_atom_std",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=("mnist_fm@v1",),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        beta_raw = policy.beta_by_channel.get(ChannelName("x"))  # type: ignore[call-overload]
        if beta_raw is None:
            beta = 0.5
            memory_fraction = 0.5
        else:
            beta = float(beta_raw)
            memory_fraction = 1.0 - beta
        prior_x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(MNIST_FLAT_DIM)
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x0 = np.random.default_rng(restart_seed).standard_normal(MNIST_FLAT_DIM).astype(
            np.float64
        )
        np.clip(fresh_x0, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=fresh_x0)

        m_clipped = max(0.0, min(1.0, float(memory_fraction)))
        blended_x0 = np.asarray(
            m_clipped * prior_x0 + (1.0 - m_clipped) * fresh_x0,
            dtype=np.float64,
        ).reshape(MNIST_FLAT_DIM)
        np.clip(blended_x0, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=blended_x0)

        # Compact digest payload: include the blended x0 head and tail so
        # the digest differs across beta values but stays deterministic.
        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_head": [float(blended_x0[i]) for i in range(8)],
                "blended_tail": [float(blended_x0[i]) for i in range(MNIST_FLAT_DIM - 8, MNIST_FLAT_DIM)],
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": np.asarray(blended_x0, dtype=np.float64).reshape(MNIST_FLAT_DIM),
                "source_round": next_round,
            },
        )
        blender_family = self._blender.blender_family()
        blender_hash = self._blender.config_hash()
        return StateBundle(
            channels={
                ChannelName("x"): _make_ref(
                    "restart",
                    src_digest=str(state.native_state_digest),
                    policy_hash=str(policy.policy_hash),
                    source_round=int(next_round),
                ),
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(next_digest),
            provenance=tuple(state.provenance)
            + (
                AUDIT_MNIST_FM_RESTART_BLEND,
                f"blender:{blender_family}",
                f"blender_hash:{blender_hash}",
            ),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        del bundle
        new_spec = dict(delta.delta_spec)
        new_spec.setdefault("target_distribution", "mnist")
        new_spec.setdefault("integrator_config_hash", MNIST_FM_CONFIG_HASH)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        del seed  # RK4 is deterministic from (weights, x0, t_grid) alone.
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior_entry = self._native_states.get(state.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=state.native_state_digest
            )
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)
        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(MNIST_FLAT_DIM)
        traj = _integrate_rk4(self._weights, x0, t_grid)
        traj_clamped = np.clip(traj, -MNIST_FM_CLAMP, MNIST_FM_CLAMP)
        overflowed = bool(np.any(np.abs(traj) > MNIST_FM_CLAMP))
        traj = traj_clamped
        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "integrator": "rk4",
                "num_steps": int(num_steps),
                "actual_steps": int(num_steps),
                "x0_head": [float(x0[i]) for i in range(8)],
            }
        )
        stored: dict[str, Any] = {
            "trajectory": traj,
            "t_grid": t_grid,
            "integrator": "rk4",
        }
        if overflowed:
            stored["_audit"] = ERR_MNIST_FM_INTEGRATOR_OVERFLOW
        self._put_native_state(traj_digest, stored)
        cfg_blob = repr(("mnist_fm_config", "rk4", int(num_steps), 0)).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(num_steps),
            accept_rate=1.0,
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        traj_entry = self._native_states.get(trace.native_state_digest)
        if traj_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=trace.native_state_digest
            )
        trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
        x_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(MNIST_FLAT_DIM)
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final_head": [float(x_final[i]) for i in range(8)],
                "t_final": 1.0,
            }
        )
        stored = {
            "x": np.asarray(x_final, dtype=np.float64).reshape(MNIST_FLAT_DIM),
            "t": 1.0,
        }
        if "_audit" in traj_entry:
            stored["_audit"] = traj_entry["_audit"]
        self._put_native_state(endpoint_digest, stored)
        next_round = int(state.source_round) + 1
        provenance = tuple(state.provenance) + ("mnist_fm_observed",)
        if "_audit" in traj_entry:
            provenance = provenance + (traj_entry["_audit"],)
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=endpoint_digest,
            provenance=provenance,
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> ArrayF64 | None:
        """Return the native ``(T, 784)`` trajectory for ``trace`` (or ``None``)."""
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        traj = entry.get("trajectory")
        if traj is None:
            return None
        return np.asarray(traj, dtype=np.float64)

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P0-7 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """Add ``injected`` to the bundle's prior ``x0`` (already a ``(784,)`` vector).

        Mirrors :meth:`RectifiedFlowCIFARAdapter.inject_forward_noise`:
        returns a new :class:`StateBundle` whose ``native_state_digest``
        is the SHA-256 of the perturbed x0's repr, with the
        ``AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED`` provenance tag.
        """
        prior_entry = self._native_states.get(bundle.native_state_digest)
        if prior_entry is None:
            raise CapabilityMissingError(
                "missing_native_state", context=bundle.native_state_digest
            )
        injected_arr = np.asarray(injected, dtype=np.float64).reshape(MNIST_FLAT_DIM)
        x0_old = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(MNIST_FLAT_DIM)
        x0_new = np.clip(x0_old + injected_arr, -MNIST_FM_CLAMP, MNIST_FM_CLAMP)
        next_round = int(bundle.source_round) + 1
        new_digest = _digest_state(
            {
                "kind": "forward_noise",
                "src_digest": bundle.native_state_digest,
                "x0_new_head": [float(x0_new[i]) for i in range(8)],
            }
        )
        self._put_native_state(
            new_digest,
            {
                "x0": np.asarray(x0_new, dtype=np.float64).reshape(MNIST_FLAT_DIM),
                "source_round": next_round,
            },
        )
        return StateBundle(
            channels={
                ChannelName("x"): _make_ref(
                    "forward_noise",
                    src_digest=str(bundle.native_state_digest),
                ),
            },
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=str(new_digest),
            provenance=tuple(bundle.provenance) + (AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 11. batched_inference — population generation for FID
    # ------------------------------------------------------------------

    def batched_inference(
        self,
        n_samples: int,
        *,
        n_steps: int | None = None,
        seed: int = 0,
    ) -> ArrayF64:
        """Generate ``(n_samples, 784)`` MNIST samples via batched RK4.

        Byte-deterministic for a fixed ``seed``: draws
        ``x0 ~ N(0, I_784)`` seeded by ``np.random.default_rng(seed)``
        and integrates the batch forward over the supplied step count
        (``MNIST_FM_NUM_STEPS`` by default).
        """
        if int(n_samples) < 1:
            raise ValueError("n_samples_must_be_positive")
        steps = int(n_steps) if n_steps is not None else int(self._num_steps)
        rng = np.random.default_rng(int(seed))
        x0 = rng.standard_normal((int(n_samples), MNIST_FLAT_DIM)).astype(np.float64)
        np.clip(x0, -MNIST_FM_CLAMP, MNIST_FM_CLAMP, out=x0)
        return _batched_integrate_rk4(self._weights, x0, steps)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_mnist_fm_adapter(
    *,
    weights_path: Path | None = None,
) -> MnistFmAdapter:
    """Return a fresh :class:`MnistFmAdapter` loaded from the canonical ``data/mnist_fm.npz``.

    The optional ``weights_path`` keyword overrides the default path;
    tests and external callers use it to point at a synthetic or
    randomized weights file when the canonical artefact is missing.
    """
    return MnistFmAdapter(weights_path=weights_path)


__all__ = [
    "AUDIT_MNIST_FM_FORWARD_NOISE_APPLIED",
    "AUDIT_MNIST_FM_RESTART_BLEND",
    "ERR_MNIST_FM_INTEGRATOR_OVERFLOW",
    "MNIST_FM_CHANNEL_DOMAINS",
    "MNIST_FM_CHANNELS",
    "MNIST_FM_CLAMP",
    "MNIST_FM_CONFIG_HASH",
    "MNIST_FM_CONFIG_VERSION",
    "MNIST_FM_DEFAULT_BASE_CHANNELS",
    "MNIST_FM_DEFAULT_WEIGHTS",
    "MNIST_FM_FLAT_DIM",
    "MNIST_FM_IMAGE_SHAPE",
    "MNIST_FM_NATIVE_STATES_MAXSIZE",
    "MNIST_FM_NUM_STEPS",
    "MnistFmAdapter",
    "MnistFMCapabilities",
    "default_mnist_fm_adapter",
]
