"""Stochastic Flow-Matching adapter (P0 #9 round-2; arXiv:2410.19814).

Implements the **encoder + stochastic flow matching** scheme from
NVIDIA's October 2024 paper on stochastic FM
(arXiv:2410.19814). The adapter exposes:

* a deterministic ``encoder`` sub-network that maps a base state to a
  small-scale deterministic component,
* a stochastic FM velocity that resolves the residual small-scale
  physics under an adaptive noise-scaled SDE, and
* an :class:`AdapterCapabilities` token that matches the existing
  synthetic-adapter surface so the framework engine can drive it
  end-to-end.

The adapter is stdlib-only (no ``torch``); the velocity is parameterised
by a closed-form linear combination of the current state and the
target mean, plus a noise-scaled residual that mimics the adaptive
stochastic correction. Quantitative target: on a stochastic-target
benchmark the framework's per-round W2 is at least ``25 %`` lower
than the deterministic adapter.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    ArtifactHash,
    ChannelDomain,
    FlowMatchingODEAdapter,
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
# Module-level constants
# ---------------------------------------------------------------------------

STOCHASTIC_FM_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("x_continuous"),
    ChannelName("x_stochastic"),
)
STOCHASTIC_FM_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = cast(
    Mapping[ChannelName, ChannelDomain],
    {
        ChannelName("x_continuous"): "continuous",
        ChannelName("x_stochastic"): "continuous",
    },
)
STOCHASTIC_FM_CONFIG_HASH: ArtifactHash = ArtifactHash("stochastic_fm:cfg:v1")
STOCHASTIC_FM_CONFIG_VERSION = "1.0.0"

DEFAULT_ENCODER_GAIN: float = 0.5
DEFAULT_DETERMINISTIC_TARGET: float = 0.0
DEFAULT_NOISE_SCALE: float = 0.05
DEFAULT_ADAPTIVE_NOISE_GAMMA: float = 1.0


def _digest(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic ``TensorRef`` from ``label`` and a parts dict."""
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"sfm:{hashlib.sha256(blob).hexdigest()[:16]}")


def _capabilities() -> AdapterCapabilities:
    """Return the canonical stochastic-FM capability token."""
    return AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=False,
        has_restart_boundary=True,
        has_continuous_channels=True,
        has_discrete_channels=False,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=tuple(STOCHASTIC_FM_CHANNELS),
        channel_domains=dict(STOCHASTIC_FM_CHANNEL_DOMAINS),
        native_config_hash=STOCHASTIC_FM_CONFIG_HASH,
        native_config_version=STOCHASTIC_FM_CONFIG_VERSION,
    )


def stochastic_velocity(
    t: float,
    y: np.ndarray,
    *,
    target: float,
    encoder_gain: float,
    noise_scale: float,
    adaptive_noise_gamma: float,
    seed: int,
) -> NDArray[np.float64]:
    """Compute the stochastic-FM velocity at time ``t`` for state ``y``.

    The velocity has two contributions:

    1. **Deterministic component** — linear field ``encoder_gain *
       (target - y)`` (the encoder's drift toward the target mean).
    2. **Stochastic residual** — noise-scaled Brownian motion whose
       scale is ``noise_scale * (1 + gamma * t)`` so the noise grows
       linearly with the time coordinate, matching the adaptive noise
       scaling of arXiv:2410.19814.

    Returns a ``(2,)`` float array; deterministic per ``(t, y, seed)``.
    """
    if not isinstance(y, np.ndarray) or y.shape != (2,):
        raise ValueError(f"y must have shape (2,), got {y.shape!r}")
    drift = encoder_gain * (target - y)
    sigma = noise_scale * (1.0 + adaptive_noise_gamma * t)
    rng = np.random.default_rng(int(seed) * 7919 + int(t * 1000))
    z = rng.standard_normal(y.shape)
    return drift + sigma * z


@dataclass
class StochasticFMAdapter(FlowMatchingODEAdapter):
    """Stochastic FM adapter with deterministic encoder + SDE residual."""

    target: float = DEFAULT_DETERMINISTIC_TARGET
    encoder_gain: float = DEFAULT_ENCODER_GAIN
    noise_scale: float = DEFAULT_NOISE_SCALE
    adaptive_noise_gamma: float = DEFAULT_ADAPTIVE_NOISE_GAMMA
    seed: int = 0
    n_steps: int = 4
    capability_overrides: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            isinstance(self.encoder_gain, bool)
            or not isinstance(self.encoder_gain, (int, float))
        ):
            raise ValueError(
                f"encoder_gain must be a real number, got {self.encoder_gain!r}"
            )
        if not math.isfinite(float(self.encoder_gain)):
            raise ValueError(
                f"encoder_gain must be finite, got {self.encoder_gain!r}"
            )
        if (
            isinstance(self.noise_scale, bool)
            or not isinstance(self.noise_scale, (int, float))
        ):
            raise ValueError(
                f"noise_scale must be a real number, got {self.noise_scale!r}"
            )
        sf = float(self.noise_scale)
        if not math.isfinite(sf) or sf < 0.0:
            raise ValueError(
                f"noise_scale must be finite and >= 0, got {sf!r}"
            )
        if not isinstance(self.n_steps, int) or isinstance(self.n_steps, bool):
            raise ValueError(f"n_steps must be int, got {self.n_steps!r}")
        if int(self.n_steps) < 1:
            raise ValueError(
                f"n_steps must be >= 1, got {self.n_steps!r}"
            )

    def capabilities(self) -> AdapterCapabilities:
        base = _capabilities()
        if not self.capability_overrides:
            return base
        return AdapterCapabilities(
            **{
                **{
                    f.name: getattr(base, f.name)
                    for f in base.__dataclass_fields__.values()
                    if not callable(getattr(base, f.name))
                },
                **self.capability_overrides,
            }
        )

    def build_initial_state(
        self, *, batch_id: str, sample_id: str
    ) -> StateBundle:
        channels: dict[str, TensorRef] = {
            str(ch): _make_tensor_ref(
                "initial",
                channel=str(ch),
                batch=batch_id,
                sample=sample_id,
            )
            for ch in STOCHASTIC_FM_CHANNELS
        }
        masks: dict[str, TensorRef] = {
            "freeze": _make_tensor_ref(
                "mask", batch=batch_id, sample=sample_id
            )
        }
        return StateBundle(
            channels=cast(Mapping[ChannelName, TensorRef], channels),
            masks=masks,
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="stochastic_fm",
            normalization="per_channel_std",
            source_round=0,
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "digest", batch=batch_id, sample=sample_id, r=0
            ),
            provenance=("StochasticFMAdapter.build_initial_state",),
            capability_token=self.capabilities(),
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        return state

    def detach_and_validate_endpoint(
        self, bundle: StateBundle
    ) -> StateBundle:
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise ValueError(f"invalid_state_bundle:{errs}")
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "detached", source=bundle.native_state_digest
            ),
            provenance=tuple(bundle.provenance)
            + ("StochasticFMAdapter.detach_and_validate_endpoint",),
            capability_token=self.capabilities(),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: RestartPolicy
    ) -> StateBundle:
        del policy
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        validate_state_bundle(bundle)
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        # Solve the 2-D stochastic ODE on a fixed time grid in [0, 1]
        # using forward-Euler with the stochastic FM velocity. The
        # state is independent of ``condition`` here because the
        # target is fixed by the adapter's ``target`` attribute.
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"seed must be int, got {seed!r}")
        # Deterministic base state: linear interpolation between 0
        # (origin) and the target mean.
        y0 = np.asarray([0.0, 0.0], dtype=np.float64)
        dt = 1.0 / float(self.n_steps)
        y = y0.copy()
        for step in range(int(self.n_steps)):
            t = step * dt
            v = stochastic_velocity(
                t,
                y,
                target=float(self.target),
                encoder_gain=float(self.encoder_gain),
                noise_scale=float(self.noise_scale),
                adaptive_noise_gamma=float(self.adaptive_noise_gamma),
                seed=int(seed) + step,
            )
            y = y + dt * v
        # Validate the input bundle.
        validate_state_bundle(state)
        return ODEIntegratorTrace(
            steps=int(self.n_steps),
            accept_rate=1.0,
            native_state_digest=_make_tensor_ref(
                "solve",
                source=state.native_state_digest,
                seed=int(seed),
                target=float(self.target),
                noise=float(self.noise_scale),
                y0=float(y[0]),
                y1=float(y[1]),
            ),
            integrator_config_hash=_make_tensor_ref(
                "config",
                target=float(self.target),
                gain=float(self.encoder_gain),
                noise=float(self.noise_scale),
                gamma=float(self.adaptive_noise_gamma),
                n=int(self.n_steps),
            ),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "observed", source=trace.native_state_digest
            ),
            provenance=tuple(state.provenance)
            + ("StochasticFMAdapter.observe_endpoint",),
            capability_token=self.capabilities(),
        )

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        raise NotImplementedError(
            "StochasticFMAdapter does not preserve a native trajectory"
        )


__all__ = [
    "DEFAULT_ADAPTIVE_NOISE_GAMMA",
    "DEFAULT_DETERMINISTIC_TARGET",
    "DEFAULT_ENCODER_GAIN",
    "DEFAULT_NOISE_SCALE",
    "STOCHASTIC_FM_CHANNELS",
    "STOCHASTIC_FM_CONFIG_HASH",
    "STOCHASTIC_FM_CONFIG_VERSION",
    "StochasticFMAdapter",
    "stochastic_velocity",
]
