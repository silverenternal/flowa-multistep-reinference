"""1D Gaussian-mixture flow matching adapter (DTB-G1 worked example #2).

The :class:`ToyGaussianAdapter` is the *second* domain that proves the
universal layer is universal: a 1D Gaussian mixture flow whose ODE
``dx/dt = -x + target_mean`` admits a closed-form solution
``x(t) = (x_0 - target_mean) * exp(-t) + target_mean``. The adapter
exists **only** to demonstrate that the universal engine + universal
adapter Protocol carry a non-molecular domain end-to-end with zero
references to :mod:`adaptive_reflow.molecular`.

Stdlib-only. No ``torch``. No numpy. No molecule vocabulary.

This is the formal proof that the universal layer is universal: the
exact same engine + Protocol + capability handshake + ledger row
emission that drives Flow-A also drives a 1D Gaussian. The
``tests/test_universal/test_toy_gaussian.py::test_universal_imports_no_molecular``
test is the load-bearing assertion; if a future change re-introduces a
molecular import into the universal path, that test fires closed.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from adaptive_reflow.adapters._adapter_common import (
    digest_state,
    make_ref,
    seed_from_ids,
)
from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.framework.interfaces import implements
from adaptive_reflow.universal import (
    AdapterCapabilities,
    ArtifactHash,
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SUPPORTED_CHANNELS: tuple[ChannelName, ...] = (ChannelName("x"),)
CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {ChannelName("x"): "continuous"}
NATIVE_CONFIG_HASH: ArtifactHash = ArtifactHash("toy:gaussian:cfg:v1")
NATIVE_CONFIG_VERSION = "1.0.0"

# Initial Gaussian mixture defaults. Mirrored from the spec; kept as
# module-level constants so tests + adapters share the same anchor.
INITIAL_WEIGHTS: tuple[float, ...] = (0.5, 0.5)
INITIAL_MEANS: tuple[float, ...] = (-1.0, 1.0)
INITIAL_STDDEVS: tuple[float, ...] = (0.5, 0.5)

# Euler integration defaults.
EULER_NUM_STEPS: int = 4
EULER_DT: float = 0.25  # 4 steps of dt=0.25 covers t in [0, 1].


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def gauss_score(x: float, mean: float, stddev: float) -> float:
    """Standard normal PDF evaluated at ``x``.

    Uses :mod:`math` only — no numpy, no scipy. Kept as a public helper
    so tests + adapters can share the same anchor.
    """
    if stddev <= 0.0:
        raise ValueError("stddev_must_be_positive")
    z = (float(x) - float(mean)) / float(stddev)
    return math.exp(-0.5 * z * z) / (float(stddev) * math.sqrt(2.0 * math.pi))


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic hash-stable TensorRef from ``label`` + parts."""
    return make_ref("toy:gauss", label, **parts)


def _digest(*parts: Any) -> str:
    """Return a deterministic sha256 hex digest for ``parts``."""
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def _memory_fraction_from_policy(policy: RestartPolicy) -> float:
    """Extract the ``memory_fraction`` from a :class:`FinalRestartPolicy`.

    The canonical :class:`FinalRestartPolicy` does not expose a
    ``memory_fraction`` field directly; the convention adopted here is:

    * ``1.0 - beta_by_channel[x]`` is the fraction of the prior retained
      (beta=0 => retain all; beta=1 => retain none).

    Falls back to ``0.0`` (full restart) when the ``x`` channel is not
    present in the policy mapping.
    """
    beta = policy.beta_by_channel.get(cast(Any, ChannelName("x")))
    if beta is None:
        return 0.0
    return 1.0 - float(beta)


def _linear_blend(
    old: tuple[float, ...],
    fresh: tuple[float, ...],
    fraction: float,
) -> tuple[float, ...]:
    """Element-wise linear blend ``(1-fraction)*fresh + fraction*old``.

    When ``fraction`` is outside ``[0, 1]`` it is clamped; the function
    is total.
    """
    frac = max(0.0, min(1.0, float(fraction)))
    out: list[float] = []
    for o, f in zip(old, fresh, strict=False):
        out.append(frac * float(o) + (1.0 - frac) * float(f))
    return tuple(out)


def _euler_step(x: float, target_mean: float, dt: float) -> float:
    """One Euler step of ``dx/dt = -x + target_mean``.

    Returned ``x_{n+1} = x_n + dt * (-x_n + target_mean)``.
    """
    return float(x) + float(dt) * (-float(x) + float(target_mean))


def _analytic_endpoint(x_0: float, target_mean: float, t: float) -> float:
    """Closed-form ``x(t) = (x_0 - target_mean) * exp(-t) + target_mean``."""
    return (float(x_0) - float(target_mean)) * math.exp(-float(t)) + float(target_mean)


# ---------------------------------------------------------------------------
# Capabilities dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GaussianAdapterCapabilities(AdapterCapabilities):
    """Capability surface of the :class:`ToyGaussianAdapter`.

    Inherits every required capability flag from
    :class:`AdapterCapabilities` and pins the channel vocabulary to
    ``("x",)`` (one continuous scalar).
    """

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
            supported_channels=SUPPORTED_CHANNELS,
            channel_domains=CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=NATIVE_CONFIG_HASH,
            native_config_version=NATIVE_CONFIG_VERSION,
        )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@implements(FlowMatchingODEAdapter)
class ToyGaussianAdapter(FlowMatchingODEAdapter):
    """1D Gaussian-mixture Flow Matching ODE adapter.

    The adapter treats the single channel ``x`` as a scalar trajectory
    that flows under the ODE ``dx/dt = -x + target_mean`` toward a
    fixed target mean supplied by the condition delta's
    ``target_mean`` entry. The closed-form solution
    ``x(t) = (x_0 - target_mean) * exp(-t) + target_mean`` is used to
    populate the final endpoint, while a 4-step Euler integration is
    recorded in the integrator trace so the trajectory is observable
    in the round trace.

    Implements all eight methods of the
    :class:`FlowMatchingODEAdapter` Protocol. Stdlib-only. NOT
    molecule-aware. Exists ONLY to prove the universal layer works
    end-to-end on a non-molecular domain.
    """

    pinned_dt: float = EULER_DT
    """Euler step size used by :meth:`solve_ode`."""
    pinned_num_steps: int = EULER_NUM_STEPS
    """Number of Euler steps performed by :meth:`solve_ode`."""

    def __init__(
        self,
        *,
        dt: float = EULER_DT,
        num_steps: int = EULER_NUM_STEPS,
    ) -> None:
        if dt <= 0.0:
            raise ValueError("dt_must_be_positive")
        if num_steps <= 0:
            raise ValueError("num_steps_must_be_positive")
        self._dt = float(dt)
        self._num_steps = int(num_steps)
        # Native state is held on the adapter keyed by bundle digest so
        # the engine can stay opaque. The adapter never inspects the
        # contents of ``StateBundle.channels``; it only keys native
        # state by ``native_state_digest`` and ``trace.native_state_digest``.
        self._native_states: dict[str, dict[str, Any]] = {}
        self._caps = GaussianAdapterCapabilities()

    # ------------------------------------------------------------------
    # 1. Capability handshake (always required)
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps

    # ------------------------------------------------------------------
    # 2. build_initial_state (required by has_prior_export=True)
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        init_digest = _digest("gauss-init", batch_id, sample_id)
        native_state: dict[str, Any] = {
            "x": 0.0,
            "weights": INITIAL_WEIGHTS,
            "means": INITIAL_MEANS,
            "stddevs": INITIAL_STDDEVS,
        }
        self._native_states[init_digest] = native_state
        bundle = StateBundle(
            channels={
                ChannelName("x"): _make_ref(
                    "initial", batch=batch_id, sample=sample_id
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=init_digest,
            provenance=("toy_gaussian@v1",),
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
        # Look up the native state under the source bundle digest.
        prior = self._native_states.get(state.native_state_digest)
        if prior is None:
            raise CapabilityMissingError(
                "missing_native_state",
                context=state.native_state_digest,
            )
        memory_fraction = _memory_fraction_from_policy(policy)
        blended_weights = _linear_blend(
            prior["weights"], INITIAL_WEIGHTS, memory_fraction
        )
        blended_means = _linear_blend(
            prior["means"], INITIAL_MEANS, memory_fraction
        )
        blended_stddevs = _linear_blend(
            prior["stddevs"], INITIAL_STDDEVS, memory_fraction
        )
        next_native = {
            "x": prior["x"],
            "weights": blended_weights,
            "means": blended_means,
            "stddevs": blended_stddevs,
        }
        next_digest = _digest(
            "gauss-restart", state.native_state_digest, policy.policy_hash
        )
        self._native_states[next_digest] = next_native
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=next_digest,
            provenance=tuple(state.provenance) + ("toy_gaussian_restart",),
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
        del bundle  # unused; condition is a passthrough
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
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
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        prior = self._native_states.get(state.native_state_digest)
        if prior is None:
            raise CapabilityMissingError(
                "missing_native_state",
                context=state.native_state_digest,
            )
        # The condition delta carries ``target_mean`` (or defaults to
        # ``1.0`` for the canonical forward-flow contract). Both Euler
        # and analytic integration are deterministic — the seed affects
        # only the integrator trace hash, not the trajectory itself.
        target_mean = float(condition.delta_spec.get("target_mean", 1.0))
        x = float(prior["x"])
        euler_positions: list[float] = [x]
        for _ in range(self._num_steps):
            x = _euler_step(x, target_mean, self._dt)
            euler_positions.append(x)
        # Analytic endpoint at t = num_steps * dt. This is the value
        # the engine's round trace exposes as ``endpoint_digest``'s
        # source-of-truth; the Euler positions are recorded in the
        # trace for observability only.
        analytic_t = float(self._num_steps) * float(self._dt)
        analytic_x = _analytic_endpoint(float(prior["x"]), target_mean, analytic_t)
        trace_digest = _digest(
            "gauss-trace",
            state.native_state_digest,
            int(seed),
            self._num_steps,
            target_mean,
        )
        self._native_states[trace_digest] = {
            "x": analytic_x,
            "weights": prior["weights"],
            "means": prior["means"],
            "stddevs": prior["stddevs"],
            "_euler_positions": tuple(euler_positions),
        }
        return ODEIntegratorTrace(
            steps=self._num_steps,
            accept_rate=1.0,
            native_state_digest=trace_digest,
            integrator_config_hash=_digest(
                "gauss-config",
                "euler",
                self._num_steps,
                self._dt,
                target_mean,
            ),
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
        # Promote the trace-keyed native state to a new bundle digest.
        native = self._native_states.get(trace.native_state_digest)
        if native is None:
            raise CapabilityMissingError(
                "missing_native_state",
                context=trace.native_state_digest,
            )
        endpoint_digest = _digest(
            "gauss-endpoint", trace.native_state_digest, state.native_state_digest
        )
        self._native_states[endpoint_digest] = dict(native)
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=endpoint_digest,
            provenance=tuple(state.provenance) + ("toy_gaussian_observed",),
            capability_token=self.capabilities(),
        )

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> Any | None:
        """Return the native trajectory for ``trace`` (or ``None``).

        Closes P0-7: the runner used to reach into the adapter's
        private ``_native_states`` dict via ``getattr``; it now calls
        this public method. ``ToyGaussianAdapter`` does not preserve
        the trajectory by default (the native state is scalar /
        descriptor-only), so this returns ``None``.
        """
        return None

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): perturb the prior's scalar ``x`` by ``injected``.

        Delegates to the generic helper
        :func:`adaptive_reflow.adapters._inject_forward_noise.inject_forward_noise_into_state`.
        """
        from adaptive_reflow.adapters._inject_forward_noise import (
            inject_forward_noise_into_state,
        )

        return inject_forward_noise_into_state(
            adapter=self,
            bundle=bundle,
            injected=injected,
            state_key="x",
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def default_toy_gaussian_adapter() -> ToyGaussianAdapter:
    """Return a fresh :class:`ToyGaussianAdapter` for tests and the registry."""
    return ToyGaussianAdapter()


__all__ = [
    "EULER_DT",
    "EULER_NUM_STEPS",
    "GaussianAdapterCapabilities",
    "INITIAL_MEANS",
    "INITIAL_STDDEVS",
    "INITIAL_WEIGHTS",
    "SUPPORTED_CHANNELS",
    "ToyGaussianAdapter",
    "default_toy_gaussian_adapter",
    "gauss_score",
]
