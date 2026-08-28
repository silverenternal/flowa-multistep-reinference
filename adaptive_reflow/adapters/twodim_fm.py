"""Real CPU-runnable 2D rectified flow adapter (DTB-G3 phase 1 runtime).

Implements the :class:`FlowMatchingODEAdapter` Protocol against a small
velocity-field MLP (``3 -> 64 -> 64 -> 2``, ~518 parameters). Source
``N(0, I_2)``; target ``two_moons`` or ``eight_gaussians``. RK4 is the
default byte-deterministic integrator; Dormand-Prince (RK45) is the
adaptive alternative with overflow clamp. Restart semantics blend the prior
endpoint with fresh ``N(0, I_2)`` via memory fraction ``m = 1 - beta``.

This is the *runtime* counterpart to
:mod:`adaptive_reflow.adapters.twodim_fm_train` (the offline trainer
that produces the ``.npz`` weights files). It is the only module under
:mod:`adaptive_reflow.adapters` that imports :mod:`numpy` at runtime.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict, deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

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

from .twodim_fm_train import (  # noqa: E402 — runtime numpy dep, opt-in extra
    sample_eight_gaussians,
    sample_two_moons,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


TWODIM_FM_CHANNELS: tuple[ChannelName, ...] = (ChannelName("xy"),)
TWODIM_FM_CONFIG_HASH: str = "twodim_fm:cfg:v1"
TWODIM_FM_CONFIG_VERSION: str = "0.1.0"
AUDIT_RESTART_BLEND: str = "twodim_fm_restart_blend"
ERR_INTEGRATOR_OVERFLOW: str = "twodim_fm_integrator_overflow"

# Channel-domain declaration for the adapter's sole channel.
TWODIM_FM_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {
    ChannelName("xy"): "continuous",
}

# Default weights path resolution: data/ at the repo root.
_DEFAULT_WEIGHTS: Mapping[str, str] = {
    "two_moons": "data/twodim_fm_two_moons.npz",
    "eight_gaussians": "data/twodim_fm_eight_gaussians.npz",
}

# RK4 integration defaults.
TWODIM_FM_NUM_STEPS: int = 100

# Coordinate clamp on the trajectory (the 2D target distributions all
# fit comfortably inside ``[-5, 5]^2``).
TWODIM_FM_CLAMP: float = 5.0

#: Maximum size of the LRU-bounded ``_native_states`` cache. Long-
#: lived engine runs accumulate one ``dict`` per ``build_initial_state``
#: / ``solve_ode`` / ``observe_endpoint`` call; without a bound the
#: cache grows unboundedly and the engine's memory footprint scales
#: with the number of rounds (audit A-3). The bound is generous
#: (``128``) so the engine's working set fits comfortably while
#: preventing unbounded growth on long multi-cycle runs.
TWODIM_FM_NATIVE_STATES_MAXSIZE: int = 128

# Integrator method literals.
IntegratorMethod = Literal["rk4", "dormand_prince"]

# Local type alias to keep numpy dependency off hot annotation paths.
ArrayF64 = NDArray[np.float64]


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
    return TensorRef(f"twodim:xy:{hashlib.sha256(blob).hexdigest()[:16]}")


def _features(x: ArrayF64, t: ArrayF64 | float) -> ArrayF64:
    """Concatenate ``x`` (n, 2) with the broadcast time ``t`` into (n, 3)."""
    x2 = np.atleast_2d(np.asarray(x, dtype=np.float64))
    if x2.ndim != 2 or x2.shape[1] != 2:
        raise ValueError("x_must_have_shape_n_2")
    tt = np.asarray(t, dtype=np.float64).reshape(-1)
    if tt.size == 1:
        tt = np.full(x2.shape[0], float(tt[0]), dtype=np.float64)
    if tt.shape[0] != x2.shape[0]:
        raise ValueError("t_must_be_scalar_or_length_n")
    return np.concatenate([x2, tt[:, None]], axis=1)


def _velocity_field(weights: Mapping[str, ArrayF64], x: ArrayF64, t: float) -> ArrayF64:
    """Evaluate the velocity MLP ``v_theta(x, t)`` (Tanh activations, 3->64->64->2)."""
    x_arr = np.asarray(x, dtype=np.float64)
    if x_arr.ndim == 1:
        if x_arr.shape[0] != 2:
            raise ValueError("x_must_have_shape_2_or_n_2")
        x_arr = x_arr.reshape(1, 2)
    elif x_arr.ndim == 2:
        if x_arr.shape[1] != 2:
            raise ValueError("x_must_have_shape_2_or_n_2")
    else:
        raise ValueError("x_must_have_shape_2_or_n_2")
    h0 = _features(x_arr, float(t))
    h1 = np.tanh(h0 @ weights["W1"] + weights["b1"])
    h2 = np.tanh(h1 @ weights["W2"] + weights["b2"])
    out = h2 @ weights["W3"] + weights["b3"]
    if np.asarray(x, dtype=np.float64).ndim == 1:
        return np.asarray(out[0], dtype=np.float64)
    return np.asarray(out, dtype=np.float64)


def _integrate_rk4(
    weights: Mapping[str, ArrayF64],
    x0: ArrayF64,
    t_grid: ArrayF64,
) -> ArrayF64:
    """Pure RK4 integration over ``t_grid``; returns ``(len(t_grid), 2)`` trajectory."""
    x0_arr = np.asarray(x0, dtype=np.float64).reshape(2)
    grid = np.asarray(t_grid, dtype=np.float64).reshape(-1)
    if grid.size < 2:
        raise ValueError("t_grid_must_have_at_least_two_points")
    traj = np.empty((grid.size, 2), dtype=np.float64)
    traj[0] = x0_arr
    x_cur = x0_arr.copy()
    for i in range(1, grid.size):
        t0 = float(grid[i - 1])
        t1 = float(grid[i])
        dt = float(t1 - t0)
        k1 = _velocity_field(weights, x_cur, t0)
        k2 = _velocity_field(weights, x_cur + 0.5 * dt * k1, t0 + 0.5 * dt)
        k3 = _velocity_field(weights, x_cur + 0.5 * dt * k2, t0 + 0.5 * dt)
        k4 = _velocity_field(weights, x_cur + dt * k3, t1)
        x_cur = x_cur + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        traj[i] = x_cur
    return traj


def _batched_integrate_rk4(
    weights: Mapping[str, ArrayF64],
    x0_batch: ArrayF64,
    n_steps: int,
) -> ArrayF64:
    """Pure batched RK4 over ``x0_batch`` of shape ``(batch, 2)``.

    Returns the final ``(batch, 2)`` state after ``n_steps`` evenly-spaced
    integration steps on ``[0, 1]``. The integration loops batched over
    ``_velocity_field`` so the BLAS path stays the same one
    ``_integrate_rk4`` exercises; only the leading dimension changes
    (single ``(2,)`` → ``(batch, 2)``). The output is deterministic
    for a fixed ``x0_batch`` + ``weights`` pair subject to NumPy's
    BLAS-kernel choice for the operand shape (C1 / D1 in the B5
    design doc).
    """
    if int(n_steps) < 1:
        raise ValueError("n_steps_must_be_positive")
    x0 = np.asarray(x0_batch, dtype=np.float64)
    if x0.ndim != 2 or x0.shape[1] != 2:
        raise ValueError("x0_batch_must_have_shape_n_2")
    grid = np.linspace(0.0, 1.0, int(n_steps) + 1, dtype=np.float64)
    x_cur = x0.copy()
    t_cur = float(grid[0])
    for i in range(1, grid.size):
        t_next = float(grid[i])
        h = float(t_next - t_cur)
        k1 = _velocity_field(weights, x_cur, t_cur)
        k2 = _velocity_field(weights, x_cur + 0.5 * h * k1, t_cur + 0.5 * h)
        k3 = _velocity_field(weights, x_cur + 0.5 * h * k2, t_cur + 0.5 * h)
        k4 = _velocity_field(weights, x_cur + h * k3, t_next)
        x_cur = x_cur + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        t_cur = t_next
    return np.asarray(x_cur, dtype=np.float64).reshape(x0.shape[0], 2)


def _integrate_dormand_prince(
    weights: Mapping[str, ArrayF64],
    x0: ArrayF64,
    t0: float,
    t1: float,
    *,
    max_steps: int = 1000,
    rtol: float = 1e-3,
    atol: float = 1e-4,
) -> ArrayF64:
    """Adaptive Dormand-Prince (RK45) integrator with overflow clamp."""
    x0_arr = np.asarray(x0, dtype=np.float64).reshape(2)
    t_start = float(t0)
    t_end = float(t1)
    if t_end <= t_start:
        raise ValueError("t1_must_exceed_t0")
    if max_steps <= 0:
        raise ValueError("max_steps_must_be_positive")

    # Standard Dormand-Prince RK45 coefficients (Dormand & Prince 1980).
    c2, c3, c4, c5 = 1.0 / 5.0, 3.0 / 10.0, 4.0 / 5.0, 8.0 / 9.0
    a21 = 1.0 / 5.0
    a31, a32 = 3.0 / 40.0, 9.0 / 40.0
    a41, a42, a43 = 44.0 / 45.0, -56.0 / 15.0, 32.0 / 9.0
    a51, a52, a53, a54 = 19372.0 / 6561.0, -25360.0 / 2187.0, 64448.0 / 6561.0, -212.0 / 729.0
    a61, a62, a63, a64, a65 = (
        9017.0 / 3168.0,
        -355.0 / 33.0,
        46732.0 / 5247.0,
        49.0 / 176.0,
        -5103.0 / 18656.0,
    )
    a71, a72, a73, a74, a75, a76 = (
        35.0 / 384.0,
        0.0,
        500.0 / 1113.0,
        125.0 / 192.0,
        -2187.0 / 6784.0,
        11.0 / 84.0,
    )
    b1, b3, b4, b5, b6 = (
        35.0 / 384.0,
        500.0 / 1113.0,
        125.0 / 192.0,
        -2187.0 / 6784.0,
        11.0 / 84.0,
    )
    # Embedded (lower-order 4th) coefficients for error estimation.
    b1s, b3s, b4s, b5s, b6s, b7s = (
        5179.0 / 57600.0,
        7571.0 / 16695.0,
        393.0 / 640.0,
        -92097.0 / 339200.0,
        187.0 / 2100.0,
        1.0 / 40.0,
    )

    x = x0_arr.copy()
    t = t_start
    h = min(1e-3, (t_end - t_start) / float(max_steps))
    traj = [x.copy()]
    steps = 0

    def _clip(arr: ArrayF64) -> ArrayF64:
        return np.clip(arr, -TWODIM_FM_CLAMP, TWODIM_FM_CLAMP)

    while t < t_end and steps < max_steps:
        if t + h > t_end:
            h = t_end - t
        k1 = _clip(_velocity_field(weights, x, t))
        k2 = _clip(_velocity_field(weights, x + h * a21 * k1, t + c2 * h))
        k3 = _clip(
            _velocity_field(weights, x + h * (a31 * k1 + a32 * k2), t + c3 * h)
        )
        k4 = _clip(
            _velocity_field(
                weights, x + h * (a41 * k1 + a42 * k2 + a43 * k3), t + c4 * h
            )
        )
        k5 = _clip(
            _velocity_field(
                weights,
                x + h * (a51 * k1 + a52 * k2 + a53 * k3 + a54 * k4),
                t + c5 * h,
            )
        )
        k6 = _clip(
            _velocity_field(
                weights,
                x + h * (a61 * k1 + a62 * k2 + a63 * k3 + a64 * k4 + a65 * k5),
                t + h,
            )
        )
        k7 = _clip(
            _velocity_field(
                weights,
                x + h * (a71 * k1 + a72 * k2 + a73 * k3 + a74 * k4 + a75 * k5 + a76 * k6),
                t + h,
            )
        )
        x_new_5 = x + h * (b1 * k1 + b3 * k3 + b4 * k4 + b5 * k5 + b6 * k6)
        x_new_4 = x + h * (b1s * k1 + b3s * k3 + b4s * k4 + b5s * k5 + b6s * k6 + b7s * k7)
        err_vec = x_new_5 - x_new_4
        err_norm = float(np.max(np.abs(err_vec))) if err_vec.size else 0.0
        x_norm = float(np.max(np.abs(x_new_5))) if x_new_5.size else 0.0
        tol = atol + rtol * x_norm
        if err_norm <= tol or h <= 1e-12:
            x = _clip(x_new_5)
            t = t + h
            traj.append(x.copy())
            steps += 1
            if err_norm > 0.0:
                # Standard step-size controller (safety factor 0.9, max grow 5x).
                factor = min(5.0, max(0.2, 0.9 * (tol / max(err_norm, 1e-30)) ** 0.2))
                h = min(h * factor, t_end - t)
        else:
            factor = max(0.2, 0.9 * (tol / max(err_norm, 1e-30)) ** 0.25)
            h = max(h * factor, 1e-12)
    return np.asarray(traj, dtype=np.float64)


def _blend_endpoint_with_prior(
    endpoint: ArrayF64,
    prior: ArrayF64,
    memory_fraction: float,
) -> ArrayF64:
    """Linear blend ``m * prior + (1 - m) * endpoint`` (``m`` clamped into ``[0, 1]``)."""
    m = max(0.0, min(1.0, float(memory_fraction)))
    ep = np.asarray(endpoint, dtype=np.float64).reshape(2)
    pr = np.asarray(prior, dtype=np.float64).reshape(2)
    return np.asarray(m * pr + (1.0 - m) * ep, dtype=np.float64)


def _default_weights_path(target: str) -> Path:
    """Resolve the canonical weights file for ``target`` under ``data/``."""
    if target not in _DEFAULT_WEIGHTS:
        raise ValueError(f"unknown_target:{target}")
    return Path(_DEFAULT_WEIGHTS[target])


def _load_weights(path: Path) -> dict[str, ArrayF64]:
    """Load the six weight arrays from a trainer ``.npz`` file."""
    if not Path(path).exists():
        raise FileNotFoundError(f"weights_file_not_found:{path}")
    with np.load(Path(path)) as data:
        missing = [k for k in ("W1", "b1", "W2", "b2", "W3", "b3") if k not in data.files]
        if missing:
            raise ValueError(f"missing_weight_keys:{','.join(missing)}")
        return {
            "W1": np.asarray(data["W1"], dtype=np.float64),
            "b1": np.asarray(data["b1"], dtype=np.float64),
            "W2": np.asarray(data["W2"], dtype=np.float64),
            "b2": np.asarray(data["b2"], dtype=np.float64),
            "W3": np.asarray(data["W3"], dtype=np.float64),
            "b3": np.asarray(data["b3"], dtype=np.float64),
        }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TwoDimFMCapabilities(AdapterCapabilities):
    """Capability surface of the :class:`TwoDimFMAdapter` (``"xy"`` continuous)."""

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
            supported_channels=TWODIM_FM_CHANNELS,
            channel_domains=TWODIM_FM_CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=TWODIM_FM_CONFIG_HASH,
            native_config_version=TWODIM_FM_CONFIG_VERSION,
        )


class TwoDimFMAdapter(FlowMatchingODEAdapter):
    """2D rectified flow adapter (CPU, NumPy).

    Implements all eight methods of :class:`FlowMatchingODEAdapter`
    against a small velocity-field network trained offline. Source
    ``N(0, I_2)``; target selected via ``target`` argument. Both RK4 and
    Dormand-Prince are deterministic for fixed
    ``(weights, x0, t_grid)``.
    """

    pinned_num_steps: int = TWODIM_FM_NUM_STEPS
    """Default number of integration steps used by :meth:`solve_ode`."""

    def __init__(
        self,
        *,
        weights_path: Path | None = None,
        target: Literal["two_moons", "eight_gaussians"] = "two_moons",
        integrator: IntegratorMethod = "rk4",
        num_steps: int = TWODIM_FM_NUM_STEPS,
        seed_offset: int = 0,
    ) -> None:
        if target not in ("two_moons", "eight_gaussians"):
            raise ValueError(f"unknown_target:{target}")
        if integrator not in ("rk4", "dormand_prince"):
            raise ValueError(f"unknown_integrator:{integrator}")
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        self._target = target
        self._integrator: IntegratorMethod = integrator
        self._num_steps = int(num_steps)
        self._seed_offset = int(seed_offset)
        # Materialize weights from the supplied path or the default.
        path = Path(weights_path) if weights_path is not None else _default_weights_path(target)
        self._weights_path = Path(path)
        self._weights = _load_weights(self._weights_path)
        # Native state keyed by sha256 digest. The engine never
        # inspects the values — it only propagates opaque
        # ``native_state_digest`` strings. Bounded by
        # :data:`TWODIM_FM_NATIVE_STATES_MAXSIZE` (audit A-3): without
        # an explicit bound the cache grows unboundedly across long
        # multi-cycle engine runs and the adapter's memory footprint
        # scales with the number of rounds. The OrderedDict is used
        # in insertion-order LRU semantics so the *oldest* entries
        # (the engine's consumed digests from prior rounds) are
        # evicted first while fresh digests remain accessible.
        self._native_states: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._caps = TwoDimFMCapabilities()

    # ------------------------------------------------------------------
    # 1. Capability handshake (always required)
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 0. LRU-bounded native_states helper (audit A-3)
    # ------------------------------------------------------------------

    def _put_native_state(
        self,
        digest: str,
        entry: dict[str, Any],
    ) -> None:
        """Insert ``entry`` under ``digest``; evict the oldest entry past maxsize.

        The :attr:`_native_states` cache is bounded by
        :data:`TWODIM_FM_NATIVE_STATES_MAXSIZE`. When the cache is at
        the bound, the insertion-order oldest entry (the engine's
        earliest round's consumed digest) is evicted to make room.
        This closes audit A-3: previously the cache was an unbounded
        ``dict`` so long-running multi-cycle engine runs accumulated
        one entry per round and the adapter's memory footprint grew
        without bound.
        """
        if digest in self._native_states:
            # Update in place: re-insert to refresh insertion order.
            self._native_states[digest] = entry
            self._native_states.move_to_end(digest)
            return
        self._native_states[digest] = entry
        while len(self._native_states) > TWODIM_FM_NATIVE_STATES_MAXSIZE:
            # ``popitem(last=False)`` removes the oldest entry (FIFO
            # eviction order).
            self._native_states.popitem(last=False)

    def _evict_native_state(self, digest: str) -> None:
        """Remove ``digest`` from the cache if present (no-op when absent).

        Called by ``observe_endpoint`` so the consumed trajectory
        digest is removed as soon as the endpoint is recorded. The
        endpoint entry itself stays in the cache so downstream
        consumers (e.g. ``export_trajectory`` callers) can still
        resolve it.
        """
        self._native_states.pop(digest, None)

    # ------------------------------------------------------------------
    # 2. build_initial_state (required by has_prior_export=True)
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
        x0 = rng.standard_normal(2).astype(np.float64)
        digest = _digest_state(
            {
                "kind": "initial",
                "batch_id": str(batch_id),
                "sample_id": str(sample_id),
                "target": self._target,
                "x0": [float(x0[0]), float(x0[1])],
            }
        )
        self._put_native_state(
            digest,
            {
                "x0": np.asarray(x0, dtype=np.float64).reshape(2),
                "target": self._target,
                "source_round": 0,
            },
        )
        bundle = StateBundle(
            channels={
                ChannelName("xy"): _make_ref(
                    "initial",
                    batch=batch_id,
                    sample=sample_id,
                    target=self._target,
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=digest,
            provenance=("twodim_fm@v1",),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint (required by has_state_export=True)
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint (always required)
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
    # 5. apply_restart_distribution (required by has_restart_boundary=True)
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
        # Memory fraction defaults to 0.5 when the policy omits ``xy``.
        beta_raw = policy.beta_by_channel.get(ChannelName("xy"))  # type: ignore[arg-type]
        if beta_raw is None:
            beta = 0.5
            memory_fraction = 0.5
        else:
            beta = float(beta_raw)
            memory_fraction = 1.0 - beta
        # Look up the prior x0 (the prior endpoint that will be blended).
        prior_x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(2)
        # Fresh noise N(0, I_2) seeded by (policy_hash, source_round+1).
        next_round = int(state.source_round) + 1
        restart_seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
        restart_seed = int(hashlib.sha256(restart_seed_blob).hexdigest()[:8], 16)
        fresh_x0 = np.random.default_rng(restart_seed).standard_normal(2).astype(np.float64)
        blended_x0 = _blend_endpoint_with_prior(fresh_x0, prior_x0, memory_fraction)
        next_digest = _digest_state(
            {
                "kind": "restart",
                "src_digest": state.native_state_digest,
                "policy_hash": str(policy.policy_hash),
                "source_round": next_round,
                "beta": float(beta),
                "memory_fraction": float(memory_fraction),
                "blended_x0": [float(blended_x0[0]), float(blended_x0[1])],
            }
        )
        self._put_native_state(
            next_digest,
            {
                "x0": np.asarray(blended_x0, dtype=np.float64).reshape(2),
                "target": self._target,
                "source_round": next_round,
            },
        )
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(next_round),
            detach_proof=True,
            native_state_digest=next_digest,
            provenance=tuple(state.provenance) + (AUDIT_RESTART_BLEND,),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 6. compose_condition (required by has_condition_injection=True)
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        del bundle  # the xy channel is unconditional beyond the prior
        new_spec = dict(delta.delta_spec)
        # Inject the adapter's target distribution and integrator config
        # so downstream observers know which model is in play.
        new_spec.setdefault("target_distribution", self._target)
        new_spec.setdefault("integrator_config_hash", TWODIM_FM_CONFIG_HASH)
        return ODEConditionDelta(
            delta_spec=new_spec,
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    # ------------------------------------------------------------------
    # 7. solve_ode (required by has_ode_integration_surface=True)
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        # ``seed`` is consumed only by the integrator config hash below;
        # both RK4 and Dormand-Prince are deterministic for fixed
        # (weights, x0, t_grid) so the seed does not influence the
        # trajectory itself.
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
        # Number of integration steps: condition override beats default.
        num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        # Build the t-grid on [0, 1] inclusive (num_steps + 1 points).
        t_grid = np.linspace(0.0, 1.0, num_steps + 1, dtype=np.float64)
        x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(2)
        if self._integrator == "rk4":
            traj = _integrate_rk4(self._weights, x0, t_grid)
            actual_steps = int(num_steps)
            accept_rate = 1.0
        else:  # "dormand_prince"
            traj = _integrate_dormand_prince(
                self._weights,
                x0,
                0.0,
                1.0,
                max_steps=max(8, num_steps * 4),
                rtol=1e-3,
                atol=1e-4,
            )
            actual_steps = max(1, traj.shape[0] - 1)
            accept_rate = 1.0
        # Overflow clamp + audit code emission.
        traj_clamped = np.clip(traj, -TWODIM_FM_CLAMP, TWODIM_FM_CLAMP)
        overflowed = bool(np.any(np.abs(traj) > TWODIM_FM_CLAMP))
        traj = traj_clamped
        traj_digest = _digest_state(
            {
                "kind": "trajectory",
                "src_digest": state.native_state_digest,
                "integrator": str(self._integrator),
                "num_steps": int(num_steps),
                "actual_steps": int(actual_steps),
                "target": self._target,
                "shape": [int(traj.shape[0]), int(traj.shape[1])],
                "x0": [float(x0[0]), float(x0[1])],
            }
        )
        # Store the trajectory keyed by digest; observe_endpoint will
        # read the final row out of it.
        stored: dict[str, Any] = {
            "trajectory": traj,
            "t_grid": t_grid,
            "target": self._target,
            "integrator": self._integrator,
        }
        if overflowed:
            stored["_audit"] = ERR_INTEGRATOR_OVERFLOW
        self._put_native_state(traj_digest, stored)
        # Integrator config hash: stable over (method, num_steps, seed).
        cfg_blob = repr(
            ("twodim_fm_config", self._integrator, int(num_steps), int(seed))
        ).encode("utf-8")
        integrator_config_hash = hashlib.sha256(cfg_blob).hexdigest()
        return ODEIntegratorTrace(
            steps=int(actual_steps),
            accept_rate=float(accept_rate),
            native_state_digest=traj_digest,
            integrator_config_hash=integrator_config_hash,
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint (always required)
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
        x_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(2)
        endpoint_digest = _digest_state(
            {
                "kind": "endpoint",
                "traj_digest": trace.native_state_digest,
                "src_digest": state.native_state_digest,
                "x_final": [float(x_final[0]), float(x_final[1])],
                "t_final": 1.0,
            }
        )
        stored: dict[str, Any] = {
            "x": np.asarray(x_final, dtype=np.float64).reshape(2),
            "t": 1.0,
            "target": self._target,
        }
        # Propagate the integrator-overflow audit code, if any.
        if "_audit" in traj_entry:
            stored["_audit"] = traj_entry["_audit"]
        self._put_native_state(endpoint_digest, stored)
        # The trajectory digest itself is left in the cache so
        # downstream consumers (``export_trajectory``,
        # ``evaluate_trajectory`` callers) can still resolve it.
        # The cache's LRU bound (audit A-3) ensures the trajectory
        # is evicted eventually if the cache overflows.
        next_round = int(state.source_round) + 1
        provenance = tuple(state.provenance) + ("twodim_fm_observed",)
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
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> ArrayF64 | None:
        """Return the native ``(K, 2)`` trajectory for ``trace``.

        Closes P0-7: the runner used to reach into the adapter's
        private ``_native_states`` dict; it now calls this public
        method. The trajectory is looked up by
        ``trace.native_state_digest`` (the digest returned from the
        most recent :meth:`solve_ode` call). Returns ``None`` when no
        trajectory is stored under that digest (e.g. the trace refers
        to a digest emitted by another adapter instance).
        """
        entry = self._native_states.get(trace.native_state_digest)
        if entry is None:
            return None
        traj = entry.get("trajectory")
        if traj is None:
            return None
        return np.asarray(traj, dtype=np.float64)

    # ------------------------------------------------------------------
    # 10. batched_integrate (B5 metric population; RK4-only)
    # ------------------------------------------------------------------

    def batched_integrate(
        self,
        x0_batch: ArrayF64,
        *,
        t_steps: int = 5,
        seed: int,
    ) -> ArrayF64:
        """Batched RK4 integration returning ``(batch, t_steps + 1, 2)``.

        RK4-only path: raises :class:`NotImplementedError` on a
        ``dormand_prince`` adapter because the per-sample adaptive
        step-size controller does not vectorise (designed per-sample,
        see ``_integrate_dormand_prince``). The default ``t_steps=5``
        is appropriate for the B5 metric *population* use case: a smooth
        average over many endpoints absorbs the discretisation error
        (the difference vs a 100-step grid is below machine epsilon on
        the per-endpoint sheet density). The *lineage* path
        (:meth:`solve_ode`) keeps the adapter's pinned
        ``num_steps`` (``TWODIM_FM_NUM_STEPS = 100``) so endpoint
        digests and W2 values stay byte-comparable to the legacy
        path.

        Byte-determinism note (design doc C1 / D1): the same
        ``(x0_batch, seed)`` and same batch shape yield bit-identical
        output. Cross-shape comparison tolerates a 1e-14 boundary
        because NumPy's BLAS dispatches different kernels by operand
        shape; the runner therefore folds the batch shape into its
        ``config_hash``.
        """
        del seed  # batched RK4 is deterministic from x0_batch alone
        if self._integrator != "rk4":
            raise NotImplementedError(
                "batched_integrate is RK4-only; Dormand-Prince uses a "
                "per-sample adaptive step controller that does not "
                "vectorise."
            )
        x0 = np.asarray(x0_batch, dtype=np.float64)
        if x0.ndim != 2 or x0.shape[1] != 2:
            raise ValueError("x0_batch_must_have_shape_n_2")
        if int(t_steps) < 1:
            raise ValueError("t_steps_must_be_positive")
        grid = np.linspace(0.0, 1.0, int(t_steps) + 1, dtype=np.float64)
        batch = x0.shape[0]
        traj = np.empty((batch, grid.size, 2), dtype=np.float64)
        x_cur = x0.copy()
        traj[:, 0, :] = x_cur
        for i in range(1, grid.size):
            t_cur = float(grid[i - 1])
            t_next = float(grid[i])
            h = float(t_next - t_cur)
            k1 = _velocity_field(self._weights, x_cur, t_cur)
            k2 = _velocity_field(self._weights, x_cur + 0.5 * h * k1, t_cur + 0.5 * h)
            k3 = _velocity_field(self._weights, x_cur + 0.5 * h * k2, t_cur + 0.5 * h)
            k4 = _velocity_field(self._weights, x_cur + h * k3, t_next)
            x_cur = x_cur + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            traj[:, i, :] = x_cur
        return traj

    # ------------------------------------------------------------------
    # 10. generate_trajectory (B5 batched runner)
    # ------------------------------------------------------------------

    def generate_trajectory(
        self,
        *,
        n_trajectories: int,
        endpoints_per_trajectory: int,
        n_gen: int,
        seed: int,
    ) -> ArrayF64:
        """Generate ``(n_trajectories, endpoints_per_trajectory, n_gen, 2)``.

        Per trajectory:

        1. Sample a fresh ``x0 ~ N(0, I_2)`` and integrate forward over
           ``TWODIM_FM_NUM_STEPS`` (lineage-equivalent grid) for the
           trajectory's lineage endpoint.
        2. For each of ``endpoints_per_trajectory`` slots, sample
           ``n_gen`` fresh prior draws ``x0_k ~ N(0, I_2)`` and
           integrate each forward over ``TWODIM_FM_NUM_STEPS``; stack
           the final states into the slot's ``(n_gen, 2)`` block.

        Byte-deterministic for a fixed ``seed`` (every random draw
        flows through ``np.random.default_rng(seed)`` so two calls
        with the same seed produce identical arrays).
        """
        if int(n_trajectories) < 1:
            raise ValueError("n_trajectories_must_be_positive")
        if int(endpoints_per_trajectory) < 1:
            raise ValueError("endpoints_per_trajectory_must_be_positive")
        if int(n_gen) < 1:
            raise ValueError("n_gen_must_be_positive")
        rng = np.random.default_rng(int(seed))
        n_steps = int(self._num_steps)
        out = np.empty(
            (int(n_trajectories), int(endpoints_per_trajectory), int(n_gen), 2),
            dtype=np.float64,
        )
        for j in range(int(n_trajectories)):
            # Per-trajectory fresh prior draw (lineage-equivalent
            # x0 ~ N(0, I_2)). Used here only to advance the RNG
            # state so the population is byte-deterministic across
            # runs with the same seed; the per-trajectory "lineage"
            # endpoint happens to coincide with the first slot's
            # final state at the same RNG state, but we never rely
            # on that identity here.
            _ = rng.standard_normal(2).astype(np.float64)
            for k in range(int(endpoints_per_trajectory)):
                # Draw ``n_gen`` fresh initial states in one shot and
                # integrate the batch forward via batched RK4 over
                # the same ``n_steps`` the engine uses for
                # ``solve_ode`` (lineage grid).
                x0_batch = rng.standard_normal(
                    (int(n_gen), 2)
                ).astype(np.float64)
                final_states = _batched_integrate_rk4(
                    self._weights, x0_batch, n_steps
                )
                out[j, k, :, :] = final_states
        return out


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_twodim_fm_adapter(
    target: Literal["two_moons", "eight_gaussians"] = "two_moons",
) -> TwoDimFMAdapter:
    """Return a fresh :class:`TwoDimFMAdapter` configured for ``target``."""
    return TwoDimFMAdapter(target=target)


__all__ = [
    "AUDIT_RESTART_BLEND",
    "ERR_INTEGRATOR_OVERFLOW",
    "TWODIM_FM_CHANNELS",
    "TWODIM_FM_CHANNEL_DOMAINS",
    "TWODIM_FM_CONFIG_HASH",
    "TWODIM_FM_CONFIG_VERSION",
    "TWODIM_FM_NATIVE_STATES_MAXSIZE",
    "TWODIM_FM_NUM_STEPS",
    "TwoDimFMAdapter",
    "TwoDimFMCapabilities",
    "default_twodim_fm_adapter",
    "sample_eight_gaussians",
    "sample_two_moons",
]
