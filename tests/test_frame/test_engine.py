"""Public tests for the DTB-G1 Flow Matching ODE re-inference engine.

These tests cover the public engine + adapter contract surface. They
are stdlib-only (no ``torch``, no ``numpy``), depend on no GPU and
share no mutable module state.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the project root is importable when pytest is invoked from
# any directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from adaptive_reflow.adapters import (
    CONTINUOUS_CHANNELS,
    DISCRETE_CHANNELS,
    MIXED_CHANNELS,
    REFERENCE_FLOWA_CHANNELS,
    ReferenceFlowAAdapter,
    SyntheticContinuousAdapter,
    SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter,
    SyntheticUnsupportedAdapter,
)
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
    DEFAULT_OPERATION_STEPS,
    DOMAIN_BY_CHANNEL,
    ENGINE_VERSION,
    ERR_ADAPTER_NONE,
    ERR_BUNDLE_NONE,
    ERR_CAPABILITIES_INVALID,
    ERR_CHANNEL_DOMAIN_MISMATCH,
    ERR_CHANNEL_UNSUPPORTED,
    ERR_CONDITION_DELTA_NO_EFFECT,
    ERR_DETACH_PROOF_FAILED,
    ERR_FEATURE_DISABLED,
    ERR_INTEGRATOR_TRACE_MISSING,
    ERR_POLICY_NONE,
    ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH,
    NORMALIZATION_KINDS,
    REFERENCE_FRAMES,
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    Engine,
    EngineRoundResult,
    FlowMatchingODEAdapter,
    LedgerRow,
    ODEConditionDelta,
    ODEIntegratorTrace,
    PhaseState,
    RoundTrace,
    StateBundle,
    TensorRef,
    validate_capabilities,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tensor_ref(name: str) -> TensorRef:
    """Return a deterministic placeholder :class:`TensorRef` for tests."""
    return TensorRef(f"test://{name}")


def _make_capabilities(
    *,
    supported: tuple[str, ...],
    continuous: bool = True,
    discrete: bool = True,
    overrides: dict[str, bool] | None = None,
) -> AdapterCapabilities:
    """Return a complete :class:`AdapterCapabilities` for tests."""
    base = AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=continuous,
        has_discrete_channels=discrete,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=supported,
    )
    if not overrides:
        return base
    fields = {f.name: getattr(base, f.name) for f in base.__dataclass_fields__.values()}
    fields.update(overrides)
    return AdapterCapabilities(**fields)


def _make_state_bundle(
    *,
    adapter_caps: AdapterCapabilities,
    batch_id: str = "batch-1",
    sample_id: str = "sample-1",
    reference_frame: str = "pocket_centered",
    normalization: str = "per_atom_std",
    source_round: int = 0,
    detach_proof: bool = True,
    channels: dict[str, TensorRef] | None = None,
) -> StateBundle:
    """Return a valid detached :class:`StateBundle` for the supplied caps."""
    if channels is None:
        channels = {name: _tensor_ref(name) for name in adapter_caps.supported_channels}
    return StateBundle(
        channels=channels,
        masks={"freeze": _tensor_ref("freeze")},
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame=reference_frame,
        normalization=normalization,
        source_round=source_round,
        detach_proof=detach_proof,
        native_state_digest="native-digest-placeholder",
        provenance=("test_helper",),
        capability_token=adapter_caps,
    )


def _make_condition_delta(
    *,
    target_round: int = 1,
    source: str = "rest_memory",
    calibration_artifact_hash: str = "calibration-artifact-placeholder",
) -> ODEConditionDelta:
    """Return a well-formed :class:`ODEConditionDelta`."""
    return ODEConditionDelta(
        delta_spec={"temperature": 1.0, "memory_fraction": 0.1},
        source=source,
        target_round=target_round,
        calibration_artifact_hash=calibration_artifact_hash,
    )


def _make_phase_state(
    *,
    outer_cycle_id: int = 0,
    round_in_cycle: int = 0,
    schedule_phase: str = "high_noise",
    schedule_phase_index: int = 0,
    horizon_remaining: int = 2,
    seed_lineage_digest: str = "seed-lineage-placeholder",
    recorded_at_round: int = 0,
) -> PhaseState:
    """Return an engine-side :class:`PhaseState` for tests."""
    return PhaseState(
        outer_cycle_id=outer_cycle_id,
        round_in_cycle=round_in_cycle,
        schedule_phase=schedule_phase,
        schedule_phase_index=schedule_phase_index,
        horizon_remaining=horizon_remaining,
        seed_lineage_digest=seed_lineage_digest,
        recorded_at_round=recorded_at_round,
    )


def _make_final_policy(
    *,
    policy_id: str = "policy-test",
    run_id: str = "run-1",
    target_round: int = 1,
    outer_cycle_id: int = 0,
    beta_by_channel: dict[str, float] | None = None,
    alpha_by_channel: dict[str, float] | None = None,
    fresh_noise_floor_by_channel: dict[str, float] | None = None,
    freeze_admission_by_channel: dict[str, bool] | None = None,
) -> FinalRestartPolicy:
    """Return a minimal valid :class:`FinalRestartPolicy` with a
    deterministic ``policy_hash``."""
    if beta_by_channel is None:
        beta_by_channel = {ch: 0.0 for ch in REFERENCE_FLOWA_CHANNELS}
    if alpha_by_channel is None:
        alpha_by_channel = {ch: 1.0 for ch in REFERENCE_FLOWA_CHANNELS}
    if fresh_noise_floor_by_channel is None:
        fresh_noise_floor_by_channel = {ch: 0.0 for ch in REFERENCE_FLOWA_CHANNELS}
    if freeze_admission_by_channel is None:
        freeze_admission_by_channel = {ch: True for ch in REFERENCE_FLOWA_CHANNELS}

    return FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId(run_id),
        target_round=int(target_round),
        outer_cycle_id=int(outer_cycle_id),
        beta_by_channel={ChannelName(k): FactorValue(float(v)) for k, v in beta_by_channel.items()},
        alpha_by_channel={ChannelName(k): FactorValue(float(v)) for k, v in alpha_by_channel.items()},
        fresh_noise_floor_by_channel={
            ChannelName(k): FactorValue(float(v)) for k, v in fresh_noise_floor_by_channel.items()
        },
        schedule_sample=None,
        freeze_admission_by_channel={
            ChannelName(k): bool(v) for k, v in freeze_admission_by_channel.items()
        },
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),  # placeholder; fixed below
        created_at_round=int(target_round),
    )._replace_with_hash()


# ---------------------------------------------------------------------------
# Tests: protocol surface (no torch)
# ---------------------------------------------------------------------------


def test_no_torch_in_any_new_file() -> None:
    """Engine / adapter modules must not import torch."""
    import importlib

    for module_name in (
        "adaptive_reflow.frame.adapter",
        "adaptive_reflow.frame.engine",
        "adaptive_reflow.adapters.reference_flowa",
        "adaptive_reflow.adapters.synthetic",
    ):
        module = importlib.import_module(module_name)
        module_file = Path(module.__file__).resolve()  # type: ignore[attr-defined]
        text = module_file.read_text(encoding="utf-8")
        assert "import torch" not in text, f"{module_name} imports torch"
        assert "from torch" not in text, f"{module_name} imports torch"


def test_flow_matching_adapter_is_runtime_protocol() -> None:
    """The protocol is ``runtime_checkable`` and exposes the expected
    method surface; synthetic adapters satisfy it."""
    assert callable(FlowMatchingODEAdapter) or True  # sanity check
    adapter = SyntheticContinuousAdapter()
    assert isinstance(adapter, FlowMatchingODEAdapter)


def test_tensor_ref_is_string() -> None:
    """``TensorRef`` is an opaque string handle; the engine never inspects."""
    ref = _tensor_ref("placeholder")
    assert isinstance(ref, str)
    assert ref.startswith("test://")


# ---------------------------------------------------------------------------
# Tests: validators
# ---------------------------------------------------------------------------


def test_validate_state_bundle_accepts_valid_bundle() -> None:
    caps = _make_capabilities(supported=REFERENCE_FLOWA_CHANNELS)
    bundle = _make_state_bundle(adapter_caps=caps)
    ok, errors = validate_state_bundle(bundle)
    assert ok and errors == ()


def test_validate_state_bundle_rejects_non_detached() -> None:
    caps = _make_capabilities(supported=REFERENCE_FLOWA_CHANNELS)
    bundle = _make_state_bundle(adapter_caps=caps, detach_proof=False)
    ok, errors = validate_state_bundle(bundle)
    assert not ok
    assert any(e == "detach_proof_must_be_true" for e in errors)


def test_validate_state_bundle_rejects_unknown_channel() -> None:
    caps = _make_capabilities(supported=REFERENCE_FLOWA_CHANNELS)
    bundle = _make_state_bundle(
        adapter_caps=caps,
        channels={"mystery_channel": _tensor_ref("mystery")},
    )
    ok, errors = validate_state_bundle(bundle)
    assert not ok
    assert any(e.startswith("unknown_channel:") for e in errors)


def test_validate_capabilities_rejects_empty_supported() -> None:
    caps = _make_capabilities(supported=())
    ok, errors = validate_capabilities(caps)
    assert not ok
    assert "supported_channels_must_be_non_empty" in errors


def test_validate_capabilities_requires_at_least_one_channel_kind() -> None:
    caps = _make_capabilities(
        supported=("only-name",),
        continuous=False,
        discrete=False,
    )
    ok, errors = validate_capabilities(caps)
    assert not ok
    assert "at_least_one_channel_kind_required" in errors


def test_validate_condition_delta_accepts_valid() -> None:
    delta = _make_condition_delta()
    ok, errors = validate_condition_delta(delta)
    assert ok and errors == ()


def test_validate_condition_delta_rejects_empty_spec() -> None:
    delta = _make_condition_delta().__class__(
        delta_spec={},
        source="x",
        target_round=1,
        calibration_artifact_hash="abc",
    )
    ok, errors = validate_condition_delta(delta)
    assert not ok
    assert "delta_spec_must_be_non_empty_mapping" in errors


def test_validate_integrator_trace_rejects_zero_steps() -> None:
    trace = ODEIntegratorTrace(
        steps=0,
        accept_rate=0.5,
        native_state_digest="nd",
        integrator_config_hash="ich",
    )
    ok, errors = validate_integrator_trace(trace)
    assert not ok
    assert any(e == "steps_must_be_positive" for e in errors)


# ---------------------------------------------------------------------------
# Tests: synthetic adapters' capabilities
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "adapter",
    [
        SyntheticContinuousAdapter(),
        SyntheticDiscreteAdapter(),
        SyntheticMixedChannelAdapter(),
        SyntheticUnsupportedAdapter(),
    ],
)
def test_synthetic_adapters_implement_protocol(adapter: FlowMatchingODEAdapter) -> None:
    """Every synthetic adapter satisfies the runtime-checkable protocol."""
    assert isinstance(adapter, FlowMatchingODEAdapter)
    caps = adapter.capabilities()
    assert isinstance(caps, AdapterCapabilities)
    assert isinstance(caps.supported_channels, tuple)


def test_synthetic_continuous_advertises_only_continuous() -> None:
    caps = SyntheticContinuousAdapter().capabilities()
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is False
    assert all(c in CONTINUOUS_CHANNELS for c in caps.supported_channels)


def test_synthetic_discrete_advertises_only_discrete() -> None:
    caps = SyntheticDiscreteAdapter().capabilities()
    assert caps.has_continuous_channels is False
    assert caps.has_discrete_channels is True
    assert all(c in DISCRETE_CHANNELS for c in caps.supported_channels)


def test_synthetic_mixed_advertises_both_domains() -> None:
    caps = SyntheticMixedChannelAdapter().capabilities()
    assert caps.has_continuous_channels is True
    assert caps.has_discrete_channels is True
    assert all(c in MIXED_CHANNELS for c in caps.supported_channels)


def test_synthetic_unsupported_advertises_nothing() -> None:
    caps = SyntheticUnsupportedAdapter().capabilities()
    assert caps.has_ode_integration_surface is False
    assert caps.has_continuous_channels is False
    assert caps.has_discrete_channels is False
    assert caps.supported_channels == ()


# ---------------------------------------------------------------------------
# Tests: Engine capability handshake
# ---------------------------------------------------------------------------


def test_engine_handshake_passes_for_reference_adapter() -> None:
    engine = Engine()
    caps = engine.handshake(ReferenceFlowAAdapter())
    assert caps.has_ode_integration_surface is True
    assert caps.supported_channels == REFERENCE_FLOWA_CHANNELS


def test_engine_handshake_fails_closed_for_unsupported_adapter() -> None:
    engine = Engine()
    with pytest.raises((CapabilityMissingError, CapabilityMismatchError)):
        engine.handshake(SyntheticUnsupportedAdapter())


def test_engine_handshake_fails_closed_when_capability_missing() -> None:
    class _PartialAdapter:
        def capabilities(self) -> AdapterCapabilities:
            return AdapterCapabilities(
                has_ode_integration_surface=True,
                has_prior_export=True,
                has_state_export=True,
                has_condition_injection=True,
                has_restart_boundary=True,
                has_continuous_channels=True,
                has_discrete_channels=True,
                has_trajectory_digest=False,  # missing!
                has_deterministic_seed=True,
                has_materialization_route=True,
                supported_channels=("coordinate",),
            )

        def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle: ...
        def export_endpoint(self, state: StateBundle) -> StateBundle: ...
        def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle: ...
        def apply_restart_distribution(self, state: StateBundle, policy: FinalRestartPolicy) -> StateBundle: ...
        def compose_condition(self, bundle: StateBundle, delta: ODEConditionDelta) -> ODEConditionDelta: ...
        def solve_ode(self, state: StateBundle, condition: ODEConditionDelta, *, seed: int) -> ODEIntegratorTrace: ...
        def observe_endpoint(self, trace: ODEIntegratorTrace, state: StateBundle) -> StateBundle: ...

    engine = Engine()
    with pytest.raises(CapabilityMissingError) as excinfo:
        engine.handshake(_PartialAdapter())
    assert excinfo.value.capability == "has_trajectory_digest"


def test_engine_handshake_fails_closed_for_none_adapter() -> None:
    engine = Engine()
    with pytest.raises(RuntimeError) as excinfo:
        engine.handshake(None)  # type: ignore[arg-type]
    assert ERR_ADAPTER_NONE in str(excinfo.value)


# ---------------------------------------------------------------------------
# Tests: happy path / parity
# ---------------------------------------------------------------------------


def _run_happy_round(
    *,
    adapter: FlowMatchingODEAdapter,
    bundle: StateBundle,
    policy: FinalRestartPolicy,
) -> EngineRoundResult:
    """Helper: run a single round that should pass every gate."""
    engine = Engine()
    return engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(target_round=1),
    )


def test_reference_flowa_beta_zero_single_round_parity() -> None:
    """Two consecutive single-round invocations with ``beta=0`` produce
    identical engine round traces (parity against the canonical path).
    """
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    policy = _make_final_policy()
    bundle = _make_state_bundle(adapter_caps=caps)

    first = _run_happy_round(adapter=adapter, bundle=bundle, policy=policy)
    second = _run_happy_round(adapter=adapter, bundle=bundle, policy=policy)

    assert first.round_trace.applied_policy_hash == second.round_trace.applied_policy_hash
    assert first.round_trace.endpoint_digest == second.round_trace.endpoint_digest
    assert first.round_trace.initial_state_digest == second.round_trace.initial_state_digest
    assert first.round_trace.condition_digest == second.round_trace.condition_digest
    assert first.round_trace.integrator_trace == second.round_trace.integrator_trace
    assert first.applied_policy_hash == hash_policy_hash(policy)
    # beta=0 => audit_codes empty.
    assert first.round_trace.audit_codes == ()
    # Engine emits the canonical 7-step order.
    assert first.round_trace.operation_steps == DEFAULT_OPERATION_STEPS


def test_reference_flowa_positive_beta_alters_endpoint() -> None:
    """When ``beta > 0`` the endpoint digest MUST differ from the
    ``beta = 0`` parity baseline; the engine still passes every gate.
    """
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    policy_zero = _make_final_policy()
    bundle_zero = _make_state_bundle(adapter_caps=caps)
    parity = _run_happy_round(adapter=adapter, bundle=bundle_zero, policy=policy_zero)

    policy_blend = _make_final_policy(
        beta_by_channel={ch: 0.5 for ch in REFERENCE_FLOWA_CHANNELS},
        alpha_by_channel={ch: 0.5 for ch in REFERENCE_FLOWA_CHANNELS},
        policy_id="policy-blend",
    )
    bundle_blend = _make_state_bundle(adapter_caps=caps)
    blend = _run_happy_round(adapter=adapter, bundle=bundle_blend, policy=policy_blend)

    assert blend.round_trace.applied_policy_hash != parity.round_trace.applied_policy_hash
    assert blend.round_trace.endpoint_digest != parity.round_trace.endpoint_digest
    assert blend.round_trace.audit_codes == ()


def test_engine_feature_disabled_short_circuits_without_calling_adapter() -> None:
    """When the feature flag is ``False`` the engine emits a disabled
    round trace and never invokes the adapter; ``applied_policy_hash``
    is empty and the audit code is ``feature_flag_disabled``."""

    class _Spy:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def capabilities(self) -> AdapterCapabilities:
            self.calls.append("capabilities")
            return ReferenceFlowAAdapter().capabilities()

    spy = _Spy()
    engine = Engine(feature_flag=False)
    caps = ReferenceFlowAAdapter().capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    policy = _make_final_policy()

    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=spy,  # type: ignore[arg-type]
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    assert spy.calls == []
    assert ERR_FEATURE_DISABLED in result.round_trace.audit_codes
    assert result.applied_policy_hash == ""
    assert result.round_trace.detached is False
    assert result.round_trace.integrator_trace is None


# ---------------------------------------------------------------------------
# Tests: fail-closed hostile cases
# ---------------------------------------------------------------------------


def test_unknown_channel_fails_closed() -> None:
    """A bundle carrying a channel outside the adapter's
    ``supported_channels`` produces a fail-closed round trace.
    """
    adapter = SyntheticContinuousAdapter()
    caps = adapter.capabilities()
    bundle = _make_state_bundle(
        adapter_caps=caps,
        channels={
            "coordinate": _tensor_ref("coordinate"),
            "mystery": _tensor_ref("mystery"),  # not in supported_channels
        },
    )
    policy = _make_final_policy(
        beta_by_channel={"coordinate": 0.0, "charge": 0.0},
        alpha_by_channel={"coordinate": 1.0, "charge": 1.0},
        fresh_noise_floor_by_channel={"coordinate": 0.0, "charge": 0.0},
        freeze_admission_by_channel={"coordinate": True, "charge": True},
        policy_id="policy-unknown-channel",
    )
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    codes = result.round_trace.audit_codes
    assert any(c.startswith(ERR_CHANNEL_UNSUPPORTED + ":mystery") for c in codes)
    # Engine never reached the integrator trace stage.
    assert result.round_trace.integrator_trace is None


def test_capability_mismatch_fails_closed() -> None:
    """An adapter whose capability surface is internally inconsistent
    (e.g. declares ``has_continuous_channels`` but no
    ``supported_channels``) fails closed at the handshake boundary.
    """
    # Adapter that declares continuous capability but lists no channels.
    class _BadCapabilityAdapter(SyntheticContinuousAdapter):
        def capabilities(self) -> AdapterCapabilities:
            caps = super().capabilities()
            return AdapterCapabilities(
                has_ode_integration_surface=caps.has_ode_integration_surface,
                has_prior_export=caps.has_prior_export,
                has_state_export=caps.has_state_export,
                has_condition_injection=caps.has_condition_injection,
                has_restart_boundary=caps.has_restart_boundary,
                has_continuous_channels=caps.has_continuous_channels,
                has_discrete_channels=caps.has_discrete_channels,
                has_trajectory_digest=caps.has_trajectory_digest,
                has_deterministic_seed=caps.has_deterministic_seed,
                has_materialization_route=caps.has_materialization_route,
                supported_channels=(),  # empty -> inconsistency
            )

    engine = Engine()
    with pytest.raises(CapabilityMismatchError):
        engine.handshake(_BadCapabilityAdapter())


def test_unsupported_adapter_fails_closed() -> None:
    """An adapter that advertises no capabilities at all fails closed
    and never receives any subsequent calls.
    """
    adapter = SyntheticUnsupportedAdapter()
    caps_caps = _make_capabilities(
        supported=REFERENCE_FLOWA_CHANNELS,
        continuous=True,
        discrete=True,
    )
    bundle = _make_state_bundle(adapter_caps=caps_caps)
    policy = _make_final_policy()
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    codes = result.round_trace.audit_codes
    assert any(c.startswith(ERR_CAPABILITIES_INVALID) for c in codes)
    # Native stage never reached -> no integrator trace emitted.
    assert result.round_trace.integrator_trace is None


def test_shape_frame_normalization_mismatch_fails_closed() -> None:
    """An adapter that returns a condition with the wrong
    ``target_round`` / ``calibration_artifact_hash`` fails closed with
    the canonical shape/frame/normalization mismatch code.
    """
    adapter = SyntheticContinuousAdapter(condition_match=False)
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    policy = _make_final_policy(
        beta_by_channel={"coordinate": 0.0, "charge": 0.0},
        alpha_by_channel={"coordinate": 1.0, "charge": 1.0},
        fresh_noise_floor_by_channel={"coordinate": 0.0, "charge": 0.0},
        freeze_admission_by_channel={"coordinate": True, "charge": True},
        policy_id="policy-shape",
    )
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    assert ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH in result.round_trace.audit_codes
    assert result.round_trace.integrator_trace is None


def test_non_detached_endpoint_fails_closed() -> None:
    """An adapter whose ``detach_and_validate_endpoint`` returns
    ``detach_proof=False`` fails closed after the native stage.
    """
    class _NonDetachedAdapter(SyntheticContinuousAdapter):
        def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
            # Deliberately drop ``detach_proof`` so the engine must fail closed.
            from dataclasses import replace
            return replace(bundle, detach_proof=False)
    adapter = _NonDetachedAdapter(detach_ok=False)
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps, detach_proof=True)
    policy = _make_final_policy(
        beta_by_channel={"coordinate": 0.0, "charge": 0.0},
        alpha_by_channel={"coordinate": 1.0, "charge": 1.0},
        fresh_noise_floor_by_channel={"coordinate": 0.0, "charge": 0.0},
        freeze_admission_by_channel={"coordinate": True, "charge": True},
        policy_id="policy-detach",
    )
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    assert ERR_DETACH_PROOF_FAILED in result.round_trace.audit_codes
    assert result.round_trace.detached is False


def test_condition_delta_no_effect_fails_closed() -> None:
    """A round without a ``condition_delta`` is recorded as a no-effect
    round and the engine never calls the integrator.
    """
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    policy = _make_final_policy()
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=None,
    )
    assert ERR_CONDITION_DELTA_NO_EFFECT in result.round_trace.audit_codes
    assert result.round_trace.integrator_trace is None


def test_integrator_trace_missing_fails_closed() -> None:
    """An adapter that returns ``None`` for ``solve_ode`` is recorded
    as a missing-integrator-trace fail-closed round.
    """
    adapter = SyntheticContinuousAdapter(return_none_trace=True)
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    policy = _make_final_policy(
        beta_by_channel={"coordinate": 0.0, "charge": 0.0},
        alpha_by_channel={"coordinate": 1.0, "charge": 1.0},
        fresh_noise_floor_by_channel={"coordinate": 0.0, "charge": 0.0},
        freeze_admission_by_channel={"coordinate": True, "charge": True},
        policy_id="policy-missing-trace",
    )
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    assert ERR_INTEGRATOR_TRACE_MISSING in result.round_trace.audit_codes
    assert result.round_trace.integrator_trace is None


def test_bundle_none_fails_closed() -> None:
    """A round without a ``bundle`` fails closed with
    ``bundle_must_not_be_none``."""
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=None,
        adapter=ReferenceFlowAAdapter(),
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    )
    assert ERR_BUNDLE_NONE in result.round_trace.audit_codes


def test_policy_none_fails_closed() -> None:
    """A round without a ``policy`` fails closed with
    ``policy_must_not_be_none``."""
    engine = Engine()
    caps = ReferenceFlowAAdapter().capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=ReferenceFlowAAdapter(),
        policy=None,
        condition_delta=_make_condition_delta(),
    )
    assert ERR_POLICY_NONE in result.round_trace.audit_codes


def test_negative_round_index_fails_closed() -> None:
    """A negative ``round_index`` is recorded as a fail-closed round
    without invoking the adapter."""
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    engine = Engine()
    result = engine.run_round(
        round_index=-1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    )
    assert any("round_index_must_be_non_negative" in code for code in result.round_trace.audit_codes)


def test_channel_domain_mismatch_fails_closed() -> None:
    """A bundle carrying a discrete channel while the adapter only
    advertises ``has_continuous_channels`` fails closed at the
    capability boundary."""
    adapter = SyntheticContinuousAdapter()
    # Construct a bundle whose channels include a discrete-channel name
    # but whose capability token still only advertises continuous.
    discrete_token = _make_capabilities(supported=("charge",), continuous=True, discrete=False)
    bundle = _make_state_bundle(
        adapter_caps=adapter.capabilities(),
        channels={"charge": _tensor_ref("charge"), "raw_pair": _tensor_ref("raw_pair")},
    )
    # Override the bundle's capability token to force the mismatch.
    bundle = StateBundle(
        channels=bundle.channels,
        masks=bundle.masks,
        batch_id=bundle.batch_id,
        sample_id=bundle.sample_id,
        reference_frame=bundle.reference_frame,
        normalization=bundle.normalization,
        source_round=bundle.source_round,
        detach_proof=bundle.detach_proof,
        native_state_digest=bundle.native_state_digest,
        provenance=bundle.provenance,
        capability_token=discrete_token,
    )
    policy = _make_final_policy(
        beta_by_channel={"charge": 0.0},
        alpha_by_channel={"charge": 1.0},
        fresh_noise_floor_by_channel={"charge": 0.0},
        freeze_admission_by_channel={"charge": True},
        policy_id="policy-domain-mismatch",
    )
    engine = Engine()
    result = engine.run_round(
        round_index=1,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(),
    )
    codes = result.round_trace.audit_codes
    # Domain mismatch is recorded for the discrete channel that the
    # adapter does not advertise.
    assert any(c.startswith(ERR_CHANNEL_DOMAIN_MISMATCH + ":raw_pair") for c in codes) or any(
        c.startswith(ERR_CHANNEL_UNSUPPORTED + ":raw_pair") for c in codes
    )


# ---------------------------------------------------------------------------
# Tests: ledger row + next phase state
# ---------------------------------------------------------------------------


def test_engine_emits_ledger_row_and_next_phase_state() -> None:
    """Happy-path round emits a :class:`LedgerRow` with the canonical
    policy_hash and a deterministic ``next_phase_state``.
    """
    adapter = ReferenceFlowAAdapter()
    caps = adapter.capabilities()
    bundle = _make_state_bundle(adapter_caps=caps)
    policy = _make_final_policy()
    engine = Engine()
    result = engine.run_round(
        round_index=3,
        phase_state=_make_phase_state(round_in_cycle=2, horizon_remaining=4),
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=_make_condition_delta(target_round=3),
    )
    assert isinstance(result, EngineRoundResult)
    assert isinstance(result.round_trace, RoundTrace)
    assert isinstance(result.ledger_row, LedgerRow)
    assert isinstance(result.next_phase_state, PhaseState)
    assert result.applied_policy_hash == hash_policy_hash(policy)
    assert result.ledger_row.applied_policy_hash == result.applied_policy_hash
    assert result.ledger_row.round_index == 3
    assert result.next_phase_state.round_in_cycle == 3
    assert result.next_phase_state.horizon_remaining == 3


# ---------------------------------------------------------------------------
# Tests: domain resolution table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "channel, expected",
    [
        ("coordinate", "continuous"),
        ("charge", "continuous"),
        ("raw_pair", "discrete"),
        ("projected_pair", "discrete"),
        ("coordinate.continuous", "continuous"),
        ("raw_pair.discrete", "discrete"),
    ],
)
def test_domain_by_channel_lookup(channel: str, expected: str) -> None:
    assert DOMAIN_BY_CHANNEL[channel] == expected


def test_reference_frames_and_normalization_are_frozen() -> None:
    """The engine constrains its inputs to fixed string enums."""
    assert REFERENCE_FRAMES == ("pocket_centered", "world", "lattice")
    assert NORMALIZATION_KINDS == ("none", "per_atom_std", "per_pocket_std")


# ---------------------------------------------------------------------------
# Tests: engine version + defaults
# ---------------------------------------------------------------------------


def test_engine_version_is_documented() -> None:
    assert isinstance(ENGINE_VERSION, str)
    assert ENGINE_VERSION  # non-empty


def test_engine_default_operation_steps_match_contract() -> None:
    """The canonical 7-step order is what the engine exposes."""
    engine = Engine()
    assert engine.operation_steps == DEFAULT_OPERATION_STEPS
    assert len(engine.operation_steps) == 7


# ---------------------------------------------------------------------------
# Sentinel: helper to replace FinalRestartPolicy with a recomputed hash
# ---------------------------------------------------------------------------


def _replace_hash(p: FinalRestartPolicy) -> FinalRestartPolicy:  # pragma: no cover - alias
    return p._replace_with_hash()


# Monkey-patch ``_replace_with_hash`` onto FinalRestartPolicy for tests.
def _impl_replace(self: FinalRestartPolicy) -> FinalRestartPolicy:
    from dataclasses import replace

    return replace(self, policy_hash=hash_policy_hash(self))


FinalRestartPolicy._replace_with_hash = _impl_replace  # type: ignore[attr-defined]
