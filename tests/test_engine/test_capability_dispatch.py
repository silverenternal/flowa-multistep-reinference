"""Tests for capabilities advertisement dispatch check (P1-6).

Mirrors ``IExecutionProvider::CanHandle`` from ONNX Runtime: the engine
performs an explicit pre-dispatch handshake against
:meth:`FlowMatchingODEAdapter.capabilities` and fails closed with
:data:`ERR_CAPABILITY_UNSUPPORTED` when a channel the round is about to
route through is not in the adapter's advertised surface.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from adaptive_reflow.frame import (
    AdapterCapabilities,
    Engine,
    EngineRoundResult,
    ODEConditionDelta,
    PhaseState,
    StateBundle,
    TensorRef,
)
from adaptive_reflow.frame.engine import ERR_CAPABILITY_UNSUPPORTED

CONTINUOUS_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
)


def _tensor_ref(name: str) -> TensorRef:
    return TensorRef(f"test://{name}")


def _make_state_bundle(
    *,
    source_round: int = 0,
    channels: tuple[str, ...] = CONTINUOUS_CHANNELS,
    batch_id: str = "batch-1",
    sample_id: str = "sample-1",
) -> StateBundle:
    caps = _full_caps()
    return StateBundle(
        channels={name: _tensor_ref(name) for name in channels},
        masks={"freeze": _tensor_ref("freeze")},
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame="pocket_centered",
        normalization="per_atom_std",
        source_round=int(source_round),
        detach_proof=True,
        native_state_digest="native-digest-placeholder",
        provenance=("test_capability_dispatch",),
        capability_token=caps,
    )


def _full_caps() -> AdapterCapabilities:
    return AdapterCapabilities(
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
        supported_channels=CONTINUOUS_CHANNELS,
    )


def _make_phase_state() -> PhaseState:
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=8,
        seed_lineage_digest="seed-lineage-placeholder",
        recorded_at_round=0,
    )


def _make_final_policy() -> FinalRestartPolicy:
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-cap"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-cap"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ChannelName(k): FactorValue(0.0) for k in CONTINUOUS_CHANNELS},
        alpha_by_channel={ChannelName(k): FactorValue(1.0) for k in CONTINUOUS_CHANNELS},
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(0.0) for k in CONTINUOUS_CHANNELS
        },
        schedule_sample=None,
        freeze_admission_by_channel={
            ChannelName(k): True for k in CONTINUOUS_CHANNELS
        },
        ledger_row_id=LedgerRowId("ledger-policy-cap"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta() -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={"temperature": 1.0, "memory_fraction": 0.1},
        source="rest_memory",
        target_round=0,
        calibration_artifact_hash="calibration-artifact-placeholder",
    )


# ---------------------------------------------------------------------------
# Capabilities dispatch check (P1-6)
# ---------------------------------------------------------------------------


class TestCapabilityDispatchCheck:
    """P1-6: the engine's pre-dispatch capability check fails closed."""

    def test_unsupported_channel_triggers_capability_unsupported(self) -> None:
        """An adapter that doesn't advertise ``unknown_channel`` fails closed."""

        class _Adapter:
            """Adapter that declares a strict subset of channels."""

            def __init__(self) -> None:
                self._caps = AdapterCapabilities(
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
                    supported_channels=("coordinate",),
                )

            def capabilities(self):
                return self._caps

            # The protocol surface must be present; the engine must NOT
            # reach any of these methods when the capability check fails.
            def build_initial_state(self, **kwargs):
                raise AssertionError(
                    "engine must not dispatch build_initial_state when capability check fails"
                )

            def apply_restart_distribution(self, *args, **kwargs):
                raise AssertionError("engine must not dispatch apply_restart_distribution")

            def compose_condition(self, *args, **kwargs):
                raise AssertionError("engine must not dispatch compose_condition")

            def solve_ode(self, *args, **kwargs):
                raise AssertionError("engine must not dispatch solve_ode")

        engine = Engine()
        bundle = _make_state_bundle(
            channels=("coordinate", "unknown_channel")
        )
        result = engine.run_round(
            round_index=0,
            phase_state=_make_phase_state(),
            bundle=bundle,
            adapter=_Adapter(),
            policy=_make_final_policy(),
            condition_delta=_make_condition_delta(),
        )

        assert isinstance(result, EngineRoundResult)
        assert result.round_trace.audit_codes
        # The unsupported channel must surface ERR_CAPABILITY_UNSUPPORTED.
        assert any(
            code.startswith(ERR_CAPABILITY_UNSUPPORTED)
            for code in result.round_trace.audit_codes
        )
        # No native integration happened.
        assert result.round_trace.integrator_trace is None
        assert result.round_trace.detached is False

    def test_missing_op_capability_triggers_capability_unsupported(self) -> None:
        """When an adapter's capability surface declares a channel kind
        that conflicts with the bundle's domain (continuous vs discrete),
        the engine must fail closed with ``ERR_CAPABILITY_UNSUPPORTED``
        rather than dispatching the round to a wrong-kind channel."""

        class _AdapterDiscreteOnly:
            """Continuous-channel named, discrete-only advertised."""

            def __init__(self) -> None:
                self._caps = AdapterCapabilities(
                    has_ode_integration_surface=True,
                    has_prior_export=True,
                    has_state_export=True,
                    has_condition_injection=True,
                    has_restart_boundary=True,
                    has_continuous_channels=False,  # kind mismatch
                    has_discrete_channels=True,
                    has_trajectory_digest=True,
                    has_deterministic_seed=True,
                    has_materialization_route=True,
                    supported_channels=("charge",),
                    channel_domains={"charge": "discrete"},
                )

            def capabilities(self):
                return self._caps

            def build_initial_state(self, **kwargs):
                raise AssertionError(
                    "must not dispatch when capability check fails"
                )

            def apply_restart_distribution(self, *args, **kwargs):
                raise AssertionError(
                    "must not dispatch when capability check fails"
                )

            def compose_condition(self, *args, **kwargs):
                raise AssertionError(
                    "must not dispatch when capability check fails"
                )

            def solve_ode(self, *args, **kwargs):
                raise AssertionError(
                    "must not dispatch when capability check fails"
                )

        engine = Engine()
        # Bundle has 'coordinate' channel which is continuous by
        # default in the synthetic adapter; the discrete-only adapter
        # therefore cannot dispatch to it.
        result = engine.run_round(
            round_index=0,
            phase_state=_make_phase_state(),
            bundle=_make_state_bundle(),
            adapter=_AdapterDiscreteOnly(),
            policy=_make_final_policy(),
            condition_delta=_make_condition_delta(),
        )

        assert isinstance(result, EngineRoundResult)
        # The capability gate fires and emits ERR_CAPABILITY_UNSUPPORTED
        # for the channel-kind mismatch.
        assert any(
            code.startswith(ERR_CAPABILITY_UNSUPPORTED)
            for code in result.round_trace.audit_codes
        )
        # No native integration happened.
        assert result.round_trace.integrator_trace is None

    def test_capability_unsupported_lands_in_ledger_row(self) -> None:
        """The capability-unsupported code must also appear in the ledger row."""

        class _Adapter:
            def __init__(self) -> None:
                self._caps = AdapterCapabilities(
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
                    supported_channels=("coordinate",),
                )

            def capabilities(self):
                return self._caps

            def build_initial_state(self, **kwargs):
                raise AssertionError

            def apply_restart_distribution(self, *args, **kwargs):
                raise AssertionError

            def compose_condition(self, *args, **kwargs):
                raise AssertionError

            def solve_ode(self, *args, **kwargs):
                raise AssertionError

        engine = Engine()
        bundle = _make_state_bundle(channels=("coordinate", "unknown"))
        result = engine.run_round(
            round_index=0,
            phase_state=_make_phase_state(),
            bundle=bundle,
            adapter=_Adapter(),
            policy=_make_final_policy(),
            condition_delta=_make_condition_delta(),
        )
        assert any(
            code.startswith(ERR_CAPABILITY_UNSUPPORTED)
            for code in result.ledger_row.audit_codes
        )
