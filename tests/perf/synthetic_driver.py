"""SyntheticMechanismAdapter v2 — O(1) deterministic Flow-Matching adapter.

This module provides a stdlib-only, hash-stable
:class:`FlowMatchingODEAdapter` implementation used by the perf bench
suite and by any other tool that wants a deterministic, no-torch,
no-IO harness against the public engine contract.

The adapter is intentionally tiny and structurally faithful to the
:mod:`adaptive_reflow.frame.adapter` protocol so that all engine
``audit_codes`` checks pass on the happy path:

* It advertises every required capability (``has_ode_integration_surface``,
  ``has_prior_export``, ``has_state_export``, ``has_condition_injection``,
  ``has_restart_boundary``, ``has_trajectory_digest``,
  ``has_deterministic_seed``, ``has_materialization_route``).
* It exposes a single, continuous channel named ``"x"``.
* :meth:`build_initial_state` returns a fresh :class:`StateBundle`
  whose ``native_state_digest`` and ``provenance`` chain are derived
  purely from the ``batch_id`` / ``sample_id`` arguments.
* :meth:`solve_ode` increments the ``"x"`` channel's :class:`TensorRef`
  handle by a deterministic function of ``seed`` and the round index
  embedded in the supplied :class:`StateBundle`. The hash is sha256
  and the round-trip is byte-stable across runs.
* :meth:`apply_restart_distribution`, :meth:`compose_condition`,
  :meth:`observe_endpoint`, :meth:`export_endpoint` and
  :meth:`detach_and_validate_endpoint` all derive their outputs
  deterministically from the previous state — the adapter never
  depends on ambient time, RNG or I/O.

Public surface:

* :class:`SyntheticMechanismAdapter` — the v2 adapter.
* :data:`SYNTHETIC_CHANNEL` — ``"x"``.

Run from the repo root with::

    PYTHONPATH=. python -c "from tests.perf.synthetic_driver import SyntheticMechanismAdapter; \
        a = SyntheticMechanismAdapter(); \
        s = a.build_initial_state(batch_id='b0', sample_id='s0'); \
        print(a.observe_endpoint(a.solve_ode(s, a.compose_condition(s, a._empty_delta(seed=7)), seed=7), s))"
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from adaptive_reflow.contracts import FinalRestartPolicy
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    FlowMatchingODEAdapter,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: The single, continuous channel name this adapter carries.
SYNTHETIC_CHANNEL: str = "x"

#: Supported-channel tuple — single element, ``"x"``.
SUPPORTED_CHANNELS: tuple[str, ...] = (SYNTHETIC_CHANNEL,)

#: Reference frame used by the synthetic state bundle.
_REFERENCE_FRAME: str = "world"

#: Normalisation used by the synthetic state bundle.
_NORMALIZATION: str = "none"

#: Adapter version label written into provenance so replay tests can
#: detect mismatches between v2 fixtures and older snapshots.
ADAPTER_VERSION: str = "synthetic.v2"

#: Salt prefix used by the TensorRef handle factory so synthetic refs
#: are recognisable in debug logs.
_REF_PREFIX: str = "syn2://"

#: Salt prefix used by the digest helper so synthetic digests cannot
#: collide with the older ``syn:`` prefix used by the
#: :mod:`adaptive_reflow.adapters.synthetic` fixtures.
_DIGEST_PREFIX: str = "syn2:"


# ---------------------------------------------------------------------------
# Internal helpers (pure)
# ---------------------------------------------------------------------------


def _digest(*parts: Any) -> str:
    """Return a deterministic sha256 hex digest over the stringified parts."""
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"|")
    return f"{_DIGEST_PREFIX}{h.hexdigest()}"


def _tensor_ref(channel: str, *, salt: str) -> TensorRef:
    """Return a :class:`TensorRef` whose stringified form is hash-stable."""
    return TensorRef(f"{_REF_PREFIX}{channel}:{salt}")


def _empty_delta(*, seed: int, target_round: int = 0) -> ODEConditionDelta:
    """Return a structurally-valid :class:`ODEConditionDelta` for use in tests.

    The default ``delta_spec`` carries the seed so condition digests are
    deterministic across replays.
    """
    return ODEConditionDelta(
        delta_spec={"seed": int(seed), "kind": "synthetic.v2"},
        source="synthetic.v2",
        target_round=int(target_round),
        calibration_artifact_hash="syn2:calibration-artifact",
    )


# ---------------------------------------------------------------------------
# SyntheticMechanismAdapter
# ---------------------------------------------------------------------------


@dataclass
class SyntheticMechanismAdapter(FlowMatchingODEAdapter):
    """v2 synthetic :class:`FlowMatchingODEAdapter`.

    The adapter is fully deterministic: every output is derived from the
    supplied ``batch_id``, ``sample_id``, ``seed`` and the canonical
    provenance tag (``ADAPTER_VERSION``). It performs no I/O, depends
    only on stdlib and computes its outputs in O(1).

    Parameters
    ----------
    steps:
        Number of integrator steps emitted in
        :meth:`ODEIntegratorTrace.steps`. Defaults to ``1`` so the happy
        path stays a single, small step.
    accept_rate:
        Fixed :class:`ODEIntegratorTrace.accept_rate` returned by
        :meth:`solve_ode`. Must lie in ``[0, 1]``.
    detach_ok:
        When ``False`` the :meth:`detach_and_validate_endpoint` method
        sets ``detach_proof=False`` so the engine's
        ``endpoint_not_detached`` audit code fires. Defaults to ``True``
        so the happy-path bench round produces no audit codes.
    capability_overrides:
        Optional mapping of capability-flag overrides. Useful when a
        perf test wants to flip a single gate off without rebuilding
        the whole capabilities tuple.
    """

    steps: int = 1
    accept_rate: float = 1.0
    detach_ok: bool = True
    capability_overrides: dict[str, bool] | None = None

    def capabilities(self) -> AdapterCapabilities:
        """Return the static capability surface for the adapter."""
        base = AdapterCapabilities(
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
            channel_domains={SYNTHETIC_CHANNEL: "continuous"},
            native_config_hash="syn2:config-hash",
            native_config_version=ADAPTER_VERSION,
        )
        if not self.capability_overrides:
            return base
        # Apply only the bool overrides; ``supported_channels`` /
        # ``channel_domains`` remain intact so the consistency validator
        # keeps passing.
        return AdapterCapabilities(
            **{
                **{f.name: getattr(base, f.name) for f in base.__dataclass_fields__.values() if not callable(getattr(base, f.name))},
                **self.capability_overrides,
            }
        )

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        """Return a fresh prior state at t=0 with the ``"x"`` channel."""
        salt = f"{batch_id}:{sample_id}"
        channels = {
            SYNTHETIC_CHANNEL: _tensor_ref(SYNTHETIC_CHANNEL, salt=salt),
        }
        return StateBundle(
            channels=channels,
            masks={"freeze": _tensor_ref("freeze", salt=salt)},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame=_REFERENCE_FRAME,
            normalization=_NORMALIZATION,
            source_round=0,
            detach_proof=True,
            native_state_digest=_digest("init", batch_id, sample_id),
            provenance=(f"{ADAPTER_VERSION}.build_initial_state",),
            capability_token=self.capabilities(),
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Return a copy of ``state`` tagged with an ``export_endpoint`` step."""
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("endpoint", state.native_state_digest),
            provenance=tuple(state.provenance)
            + (f"{ADAPTER_VERSION}.export_endpoint",),
            capability_token=self.capabilities(),
        )

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        """Return the detached / validated endpoint bundle."""
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=bool(self.detach_ok),
            native_state_digest=_digest("detached", bundle.native_state_digest),
            provenance=tuple(bundle.provenance)
            + (f"{ADAPTER_VERSION}.detach_and_validate_endpoint",),
            capability_token=self.capabilities(),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        """Return ``state`` unchanged — the synthetic adapter has no prior beta."""
        del policy
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        """Pass the supplied condition delta through unchanged.

        The synthetic adapter does not modify the condition; the engine's
        shape / frame / normalization mismatch gate checks that
        ``composed.target_round`` and
        ``composed.calibration_artifact_hash`` round-trip identically,
        which they do here.
        """
        del bundle
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
        """Increment the ``"x"`` channel by a deterministic function of ``seed``.

        The increment is computed via :func:`_x_increment`; the
        returned :class:`ODEIntegratorTrace` carries a digest that
        binds it to the source bundle, the condition and the seed.
        The increment is also embedded in the digest payload so
        :meth:`observe_endpoint` can recover it without needing access
        to the condition.
        """
        steps = max(1, int(self.steps))
        # The increment is a pure function of (seed, source_round);
        # downstream code can reconstruct it by re-running the same
        # function on the same arguments.
        increment = _x_increment(int(seed), int(state.source_round))
        new_digest = _digest(
            "solve",
            state.native_state_digest,
            int(seed),
            int(condition.target_round),
            increment,
            steps,
        )
        return ODEIntegratorTrace(
            steps=steps,
            accept_rate=float(self.accept_rate),
            native_state_digest=new_digest,
            integrator_config_hash=_digest("config", ADAPTER_VERSION),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Return the observed endpoint bundle, with the incremented ``"x"`` handle.

        The increment is derived deterministically from the trace's
        digest (and the source bundle's source_round) so the call is
        hash-stable across replays; we never try to recover the
        original ``seed`` (which would require guessing
        ``target_round``). The mapping is a deterministic splitmix-
        style read of the first 16 hex characters of the trace digest,
        which matches the public surface of :func:`_x_increment`.
        """
        increment = _x_increment_from_trace(
            trace.native_state_digest, int(state.source_round)
        )
        x_ref_old = state.channels.get(SYNTHETIC_CHANNEL)
        x_ref_str = (
            str(x_ref_old)
            if x_ref_old is not None
            else f"{_REF_PREFIX}{SYNTHETIC_CHANNEL}:absent"
        )
        new_ref = TensorRef(f"{x_ref_str}+{increment}")
        new_channels = dict(state.channels)
        new_channels[SYNTHETIC_CHANNEL] = new_ref
        return StateBundle(
            channels=new_channels,
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round) + 1,
            detach_proof=True,
            native_state_digest=_digest("observed", trace.native_state_digest),
            provenance=tuple(state.provenance)
            + (f"{ADAPTER_VERSION}.observe_endpoint",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Internal pure helpers (O(1))
# ---------------------------------------------------------------------------


def _x_increment(seed: int, source_round: int) -> int:
    """Return a deterministic O(1) integer increment for ``(seed, source_round)``.

    The function is total, pure and depends only on its arguments. We
    avoid ``hash()`` (which is randomised across processes by default)
    and use a folded int xor instead so two runs in the same process
    produce identical handles and across-process replays produce
    identical bytes when the inputs match.
    """
    s = int(seed) & 0xFFFFFFFF
    r = int(source_round) & 0xFFFFFFFF
    # Splitmix-style mix; cheap and deterministic.
    z = (s + 0x9E3779B9 + (r * 0x85EBCA6B)) & 0xFFFFFFFF
    z = (((z ^ (z >> 16)) * 0xC2B2AE35) & 0xFFFFFFFF)
    z = ((z ^ (z >> 13)) * 0x85EBCA6B) & 0xFFFFFFFF
    z = z ^ (z >> 16)
    # Map to a small positive int so the resulting TensorRef string is
    # compact and human-readable.
    return 1 + (z % 1_000_003)


def _x_increment_from_trace(
    trace_digest: str,
    source_round: int,
) -> int:
    """Derive a deterministic ``"x"`` increment from a v2 trace digest.

    This routine is the observe_endpoint counterpart of
    :func:`_x_increment`. The trace digest is an opaque sha256 hex
    string of the form ``"syn2:<hex>"``; we read the first 16 hex
    characters (64 bits of entropy), fold them into the source_round
    via a splitmix-style mix, and map the result into the same
    ``[1, 1_000_003]`` range used by :func:`_x_increment`.

    The function is O(1), pure, and depends only on its arguments.
    It does NOT try to recover the original ``seed``; the bench
    harness cares only about hash-stability, not about recovering the
    seed verbatim.
    """
    # Strip the ``syn2:`` prefix if present; fall back to the raw
    # string for safety.
    raw = str(trace_digest)
    if raw.startswith(_DIGEST_PREFIX):
        raw = raw[len(_DIGEST_PREFIX):]
    # First 16 hex chars = 64-bit unsigned integer.
    truncated = raw[:16].ljust(16, "0")
    h = int(truncated, 16) & 0xFFFFFFFFFFFFFFFF
    r = int(source_round) & 0xFFFFFFFF
    # Splitmix-style mix (matches :func:`_x_increment` structure).
    z = (h + 0x9E3779B97F4A7C15 + (r * 0x85EBCA6B)) & 0xFFFFFFFFFFFFFFFF
    z = (((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF)
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    z = z ^ (z >> 31)
    return 1 + (z % 1_000_003)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ADAPTER_VERSION",
    "SUPPORTED_CHANNELS",
    "SYNTHETIC_CHANNEL",
    "SyntheticMechanismAdapter",
]
