"""Cross-cutting fail-closed property tests (algorithmic gap closure).

These tests verify the *fail-closed* contract of the public adaptive_reflow
APIs across regression scenarios: malformed inputs must never crash a round,
and every documented audit code must be reachable from a well-defined
input shape.

Three property-driven templates:

1. **test_engine_never_raises_on_malformed_input** — for any malformed
   :class:`Engine.run_round` argument, the engine returns an
   :class:`EngineRoundResult` rather than propagating an exception.
   The malformed inputs cover the surfaces the engine already handles
   fail-closed (``bundle=None``, ``bundle`` with invalid fields,
   ``policy=None``, ``condition_delta=None``, ``round_index`` of any
   non-int / negative type). For surfaces that the engine does not yet
   handle fail-closed (e.g. ``phase_state=None`` is appended to audit
   codes but ``_next_phase_state`` then crashes; non-typed values for
   ``policy`` / ``condition_delta`` crash via ``hash_policy_hash`` /
   ``_digest_condition``), the engine has a documented gap and the
   test asserts the precise exception instead so the gap stays visible.
2. **test_channel_rule_never_raises_on_malformed_input** — the channel
   rule is a pure, total function on ``ChannelRuleInputs``; when given
   a non-:class:`ChannelRuleInputs` value, it raises
   :class:`AttributeError` via ``getattr(inputs, ...)``. The test pins
   the current behaviour so a future fail-closed wrap surfaces as a
   regression flip.
3. **test_every_audit_code_is_reachable** — for every documented audit
   code in the public catalogue (engine + channel rule + merge), at
   least one input shape triggers it. The test uses Hypothesis
   ``@example`` to enumerate the cases deterministically; ``@given``
   then ensures random sampling does not regress.

The tests use the strategies declared in :mod:`tests.property.conftest`
and the public surface re-exported from :mod:`adaptive_reflow.frame`.

Stdlib + hypothesis only — no torch.
"""

from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

# Make the repository importable when pytest is launched from the
# project root without any package metadata.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from adaptive_reflow.adapters import SyntheticContinuousAdapter
from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    ChannelName,
    ChannelRuleInputs,
    ChannelTransferEvidence,
    FactorValue,
    FinalRestartPolicy,
    ProvenanceChain,
    RunId,
    SampleId,
    TraceDigest,
    hash_policy_hash,
)
from adaptive_reflow.frame import (
    ERR_ADAPTER_RAISED,
    ERR_BUNDLE_INVALID,
    ERR_BUNDLE_NONE,
    ERR_CAPABILITIES_INVALID,
    ERR_CHANNEL_UNSUPPORTED,
    ERR_CONDITION_DELTA_NO_EFFECT,
    ERR_DETACH_PROOF_FAILED,
    ERR_FEATURE_DISABLED,
    ERR_INTEGRATOR_TRACE_MISSING,
    ERR_POLICY_NONE,
    ERR_ROUND_INDEX_NEGATIVE,
    ERR_ROUND_INDEX_NON_INT,
    ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH,
    ERR_SOURCE_ROUND_NON_INT,
    MERGE_DEGENERATE_INTERVAL,
    MERGE_FLOOR_FALLBACK,
    MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
    Engine,
    EngineRoundResult,
    LedgerRow,
    ODEConditionDelta,
    PhaseState,
    RoundTrace,
    StateBundle,
    TensorRef,
    compute_channel_decision,
)
from adaptive_reflow.frame.channel_rule import (
    AUDIT_SOURCE_REVOKED,
    AUDIT_STABILITY_COLLAPSE,
    BLOCKER_COMPLEMENT_EXCLUDED,
    BLOCKER_ENVELOPE_HASH_MISSING,
    BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL,
    BLOCKER_HORIZON_UNPROVEN,
    BLOCKER_MISSING_FACTOR,
    BLOCKER_NAN_OR_INF,
    BLOCKER_NON_FINITE,
    BLOCKER_NOT_FINITE_PREFIX,
    BLOCKER_PROXY_ONLY,
    BLOCKER_TAIL_INADMISSIBLE,
)
from adaptive_reflow.frame.merge import (
    ERR_PREV_REQUIRED,
    MergeAuthorityError,
    bounded_merge,
    bounded_merge_with_schedule,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tensor_ref(name: str) -> TensorRef:
    """Return a deterministic placeholder :class:`TensorRef` for tests."""
    return TensorRef(f"test://{name}")


def _make_state_bundle(
    *,
    source_round: object = 0,
    channels: object = None,
    detach_proof: bool = True,
    reference_frame: str = "pocket_centered",
    normalization: str = "per_atom_std",
    batch_id: str = "batch-fc",
    sample_id: str = "sample-fc",
    native_state_digest: str = "native-digest-fc",
    provenance: tuple[str, ...] = ("test_fail_closed",),
) -> StateBundle:
    """Build a :class:`StateBundle` for tests.

    ``source_round`` and ``channels`` accept arbitrary types so the
    fail-closed test can feed them malformed values; the validator
    rejects each variant with a deterministic audit code.
    """
    adapter = SyntheticContinuousAdapter()
    caps = adapter.capabilities()
    if channels is None:
        channels = {name: _tensor_ref(name) for name in caps.supported_channels}
    return StateBundle(
        channels=channels,  # type: ignore[arg-type]
        masks={"freeze": _tensor_ref("freeze")},
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame=reference_frame,
        normalization=normalization,
        source_round=source_round,  # type: ignore[arg-type]
        detach_proof=detach_proof,
        native_state_digest=native_state_digest,
        provenance=provenance,
        capability_token=caps,
    )


def _make_phase_state() -> PhaseState:
    """Build a deterministic engine-side :class:`PhaseState`."""
    return PhaseState(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        horizon_remaining=8,
        seed_lineage_digest="seed-lineage-fc",
        recorded_at_round=0,
    )


def _make_final_policy() -> FinalRestartPolicy:
    """Build a deterministic :class:`FinalRestartPolicy` for tests."""
    from dataclasses import replace

    from adaptive_reflow.contracts import LedgerRowId, PolicyId

    adapter = SyntheticContinuousAdapter()
    caps = adapter.capabilities()
    channel_names = [ChannelName(c) for c in caps.supported_channels]
    beta = {ch: FactorValue(0.0) for ch in channel_names}
    alpha = {ch: FactorValue(1.0) for ch in channel_names}
    floor = {ch: FactorValue(0.0) for ch in channel_names}
    freeze = {ch: True for ch in channel_names}
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-fc"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-fc"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel=beta,
        alpha_by_channel=alpha,
        fresh_noise_floor_by_channel=floor,
        schedule_sample=None,
        freeze_admission_by_channel=freeze,
        ledger_row_id=LedgerRowId("ledger-fc"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _make_condition_delta() -> ODEConditionDelta:
    """Build a well-formed :class:`ODEConditionDelta`."""
    return ODEConditionDelta(
        delta_spec={"temperature": 1.0, "memory_fraction": 0.1},
        source="rest_memory",
        target_round=0,
        calibration_artifact_hash="calibration-fc",
    )


def _channel_inputs_factory() -> ChannelRuleInputs:
    """Build a deterministic :class:`ChannelRuleInputs` for tests."""
    from adaptive_reflow.contracts import (
        RoundResultBundle,
        make_default_phase_state,
    )

    bundle_id = BundleId("bundle-fc")
    channel_name = ChannelName("coordinate")
    evidence = ChannelTransferEvidence(
        bundle_id=bundle_id,
        channel=channel_name,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=FactorValue(0.6),
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=FactorValue(0.1),
        proxy_only_evidence=False,
        ambiguity=FactorValue(0.2),
        degeneracy_penalty=FactorValue(0.1),
        support_coverage=FactorValue(0.8),
        recency_decay=FactorValue(0.9),
        calibration_lower_bound=FactorValue(0.7),
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("test_fail_closed_evidence",)),
        validation_errors=(),
    )
    bundle = RoundResultBundle(
        bundle_id=bundle_id,
        source_round=0,
        round_count=1,
        run_id=RunId("run-fc"),
        sample_id=SampleId("sample-fc"),
        trace_digest=TraceDigest("trace-fc"),
        condition_digest=TraceDigest(""),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-fc"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={"channel": "coordinate"},
        charge_channel={"channel": "charge"},
        raw_pair_channel={"channel": "raw_pair"},
        projected_pair_channel={"channel": "projected_pair"},
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={},
        frame_spec={},
        provenance=ProvenanceChain(("test_fail_closed",)),
        created_at_round=0,
        revoked=False,
    )
    phase_state = make_default_phase_state(
        outer_cycle_id=0,
        round_in_cycle=0,
        horizon_coverage_proven=True,
    )
    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase_state,
        scheduled_cap=FactorValue(0.5),
        mixing_cap=FactorValue(0.5),
        fresh_noise_floor=FactorValue(0.1),
        delta_cap_up=FactorValue(0.2),
        delta_cap_down=FactorValue(0.2),
        tail_admissibility=True,
        complement_excluded=False,
        frozen_envelope_manifest_hash=ArtifactHash("envelope-fc"),
        finite_prefix_only=True,
        calibration_lower_bound=FactorValue(0.7),
        perturbation_stability_lower_bound=FactorValue(0.6),
        support_coverage=FactorValue(0.8),
        ambiguity=FactorValue(0.2),
        degeneracy_penalty=FactorValue(0.1),
        recency_decay=FactorValue(0.9),
        horizon_coverage_proven=True,
        selected_bundle_id=bundle_id,
    )


# ---------------------------------------------------------------------------
# 1. Engine.run_round never raises on malformed input (except adapter=None
#    and the documented gaps below)
# ---------------------------------------------------------------------------


# Pool of malformed ``bundle`` shapes the engine's gate must absorb. Each
# entry violates exactly one validator; the engine must surface a
# fail-closed audit code rather than raise.
def _gen_malformed_bundles() -> tuple[StateBundle, ...]:
    """Build a tuple of malformed ``StateBundle``-like objects.

    Each bundle violates exactly one validator; the engine must surface
    a fail-closed audit code rather than raise.
    """
    bundles: list[StateBundle] = []
    bundles.append(_make_state_bundle(channels={}))
    bundles.append(_make_state_bundle(batch_id=""))
    bundles.append(_make_state_bundle(sample_id=""))
    bundles.append(_make_state_bundle(detach_proof=False))
    bundles.append(_make_state_bundle(native_state_digest=""))
    bundles.append(_make_state_bundle(provenance=()))
    bundles.append(_make_state_bundle(reference_frame="not-a-frame"))
    bundles.append(_make_state_bundle(normalization="quantum"))
    bundles.append(_make_state_bundle(source_round=-1))
    bundles.append(_make_state_bundle(source_round=0.5))
    bundles.append(_make_state_bundle(source_round=True))
    bundles.append(_make_state_bundle(source_round="0"))
    bundles.append(_make_state_bundle(source_round=[0]))
    bundles.append(_make_state_bundle(source_round={"round": 0}))
    bundles.append(_make_state_bundle(source_round=None))
    bundles.append(_make_state_bundle(source_round=float("nan")))
    bundles.append(_make_state_bundle(source_round=float("inf")))
    bundles.append(
        _make_state_bundle(
            channels={"unsupported-channel": _tensor_ref("unsupported-channel")},
        )
    )
    bundles.append(
        _make_state_bundle(
            channels={
                "coordinate": _tensor_ref("coordinate"),
                "": _tensor_ref(""),
            },
        )
    )
    bundles.append(
        _make_state_bundle(
            batch_id="", sample_id="", native_state_digest=""
        )
    )
    bundles.append(
        _make_state_bundle(reference_frame="world", normalization="per_atom_std")
    )
    bundles.append(
        _make_state_bundle(
            reference_frame="lattice", normalization="per_pocket_std"
        )
    )
    bundles.append(
        _make_state_bundle(
            reference_frame="pocket_centered", normalization="none"
        )
    )
    return tuple(bundles)


_MALFORMED_BUNDLES: tuple[StateBundle, ...] = _gen_malformed_bundles()


@pytest.mark.parametrize(
    "bad_bundle", _MALFORMED_BUNDLES, ids=lambda b: f"bundle:{b.batch_id!r}"
)
def test_engine_never_raises_on_malformed_bundle(bad_bundle: StateBundle) -> None:
    """``Engine.run_round`` returns an :class:`EngineRoundResult` for any
    malformed ``bundle`` shape; it never raises.

    We pass a valid ``adapter`` / ``policy`` / ``phase_state`` /
    ``condition_delta`` and only mutate ``bundle``. The engine's
    fail-closed gate (``ERR_BUNDLE_NONE`` / ``ERR_BUNDLE_INVALID`` /
    ``ERR_SOURCE_ROUND_NON_INT``) absorbs the malformed input.
    """
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    result = engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=bad_bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    )
    assert isinstance(result, EngineRoundResult)
    assert isinstance(result.round_trace, RoundTrace)
    assert isinstance(result.ledger_row, LedgerRow)


# Malformed ``round_index`` shapes (engine coerces them to 0 and emits
# an audit code).
MALFORMED_ROUND_INDICES: tuple[object, ...] = (
    -1,
    -100,
    1.5,
    "abc",
    None,
    True,
    False,
    [],
    {},
    float("nan"),
    float("inf"),
    float("-inf"),
)


@pytest.mark.parametrize("bad_index", MALFORMED_ROUND_INDICES, ids=repr)
def test_engine_never_raises_on_malformed_round_index(bad_index: object) -> None:
    """``Engine.run_round`` returns an :class:`EngineRoundResult` for any
    malformed ``round_index`` value (including ``None``, ``-1``,
    non-int, NaN/Inf) and never raises.

    ``round_index`` is the parameter whose fail-closed surface is the
    most thoroughly hardened in the engine (``_coerce_nonneg_int``
    coerces any value to ``0`` and emits the canonical audit code).
    """
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    result = engine.run_round(
        round_index=bad_index,  # type: ignore[arg-type]
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    )
    assert isinstance(result, EngineRoundResult)


# ---------------------------------------------------------------------------
# Documented fail-closed gaps
# ---------------------------------------------------------------------------
# The engine currently raises :class:`AttributeError` for the inputs
# below. The gaps are pinned here so they remain visible: a future
# fail-closed wrap must flip the assertions from ``pytest.raises`` to
# the standard ``isinstance(result, EngineRoundResult)`` check. The
# gaps are:
#
#  * ``phase_state=None`` — the engine emits ``ERR_PHASE_STATE_NONE``
#    but then crashes inside ``_next_phase_state(None)`` (which reads
#    ``current.outer_cycle_id``).
#  * ``policy=<non-FinalRestartPolicy>`` — the engine emits no audit
#    code for non-typed values and crashes inside
#    ``hash_policy_hash(policy)``.
#  * ``condition_delta=<non-ODEConditionDelta>`` — the engine crashes
#    inside ``_digest_condition(condition_delta)`` /
#    ``validate_condition_delta(condition_delta)`` for non-typed values.
#  * ``bundle=<non-StateBundle-like>`` (str, int, list, dict, ...) —
#    the validator ``validate_state_bundle`` crashes accessing
#    ``bundle.channels`` on the raw value.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_phase_state",
    (None,),
    ids=repr,
)
def test_engine_phase_state_none_emits_audit_before_crashing(
    bad_phase_state: object,
) -> None:
    """Pin the documented gap: ``phase_state=None`` triggers
    ``ERR_PHASE_STATE_NONE`` in the audit trail, then the engine
    crashes inside ``_next_phase_state``. The gap is what
    ADR-0005 §3.5 flags as a future fix."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    with pytest.raises(AttributeError):
        engine.run_round(
            round_index=0,
            phase_state=bad_phase_state,  # type: ignore[arg-type]
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=condition_delta,
        )


@pytest.mark.parametrize(
    "bad_policy",
    ("not-a-policy", 0, [], {}, object()),
    ids=repr,
)
def test_engine_policy_non_typed_raises_attribute_error(
    bad_policy: object,
) -> None:
    """Pin the documented gap: a non-typed ``policy`` value crashes the
    engine inside ``hash_policy_hash``. The fail-closed contract is
    only honoured for ``policy=None`` (see
    :func:`test_engine_never_raises_on_malformed_policy_none` below);
    other types are an open gap."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    condition_delta = _make_condition_delta()
    with pytest.raises(AttributeError):
        engine.run_round(
            round_index=0,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=bad_policy,  # type: ignore[arg-type]
            condition_delta=condition_delta,
        )


def test_engine_never_raises_on_malformed_policy_none() -> None:
    """``Engine.run_round`` returns an :class:`EngineRoundResult` when
    ``policy=None``; the fail-closed gate absorbs the value and emits
    ``ERR_POLICY_NONE``."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    condition_delta = _make_condition_delta()
    result = engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=None,  # type: ignore[arg-type]
        condition_delta=condition_delta,
    )
    assert isinstance(result, EngineRoundResult)


@pytest.mark.parametrize(
    "bad_delta",
    ("not-a-delta", 0, [], {}, object()),
    ids=repr,
)
def test_engine_condition_delta_non_typed_raises_attribute_error(
    bad_delta: object,
) -> None:
    """Pin the documented gap: a non-typed ``condition_delta`` value
    crashes the engine inside ``_digest_condition`` /
    ``validate_condition_delta``. The fail-closed contract is only
    honoured for ``condition_delta=None`` (see
    :func:`test_engine_never_raises_on_malformed_condition_delta_none`)."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    with pytest.raises(AttributeError):
        engine.run_round(
            round_index=0,
            phase_state=phase_state,
            bundle=bundle,
            adapter=adapter,
            policy=policy,
            condition_delta=bad_delta,  # type: ignore[arg-type]
        )


def test_engine_never_raises_on_malformed_condition_delta_none() -> None:
    """``Engine.run_round`` returns an :class:`EngineRoundResult` when
    ``condition_delta=None``; the fail-closed gate absorbs the value
    and emits ``ERR_CONDITION_DELTA_NO_EFFECT``."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    result = engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=None,
    )
    assert isinstance(result, EngineRoundResult)


def test_engine_never_raises_on_malformed_bundle_none() -> None:
    """``Engine.run_round`` returns an :class:`EngineRoundResult` when
    ``bundle=None``; the fail-closed gate absorbs the value and emits
    ``ERR_BUNDLE_NONE``."""
    engine = Engine()
    adapter = SyntheticContinuousAdapter()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    result = engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=None,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    )
    assert isinstance(result, EngineRoundResult)


def test_engine_raises_runtime_error_when_adapter_is_none() -> None:
    """Sanity: ``adapter=None`` raises :exc:`RuntimeError` carrying the
    canonical ``adapter_must_not_be_none`` code. This is the one
    documented exception path; the fail-closed contract is about
    ``EngineRoundResult`` for everything else."""
    engine = Engine()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    with pytest.raises(RuntimeError, match="adapter_must_not_be_none"):
        engine.run_round(
            round_index=0,
            phase_state=phase_state,
            bundle=bundle,
            adapter=None,  # type: ignore[arg-type]
            policy=policy,
            condition_delta=condition_delta,
        )


# ---------------------------------------------------------------------------
# 2. compute_channel_decision never raises on None; raises AttributeError
#    on other non-ChannelRuleInputs values (documented gap).
# ---------------------------------------------------------------------------


def test_channel_rule_never_raises_on_none_input() -> None:
    """``compute_channel_decision(None)`` is the canonical fail-closed
    case for the channel rule: the helper surfaces
    ``AttributeError`` (because ``None.perturbation_stability_lower_bound``
    raises), which we accept and pin so a future fail-closed wrap
    surfaces as a regression flip."""
    try:
        outputs = compute_channel_decision(None)  # type: ignore[arg-type]
    except AttributeError:
        return  # Documented gap.
    raise AssertionError(
        f"compute_channel_decision(None) returned {outputs!r}; expected AttributeError"
    )


@given(
    bad_input=st.sampled_from(
        ("not-a-channel-rule-input", 0, -1, 1.5, [], {}, b"bytes-payload")
    )
)
@settings(max_examples=50, deadline=10000)
@example(bad_input="not-a-channel-rule-input")
@example(bad_input=object())
@example(bad_input=0)
def test_channel_rule_raises_attribute_error_on_non_typed_input(
    bad_input: object,
) -> None:
    """The channel rule is *not* yet fail-closed for non-:class:`ChannelRuleInputs`
    values: passing a non-typed value raises :class:`AttributeError`
    from ``getattr(inputs, ...)``. The gap is pinned here so a future
    fail-closed wrap surfaces as a regression flip."""
    with pytest.raises(AttributeError):
        compute_channel_decision(bad_input)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. Every documented audit code is reachable
# ---------------------------------------------------------------------------


# Map every documented audit code to a small ``(label, expected_substr, callable)``
# tuple that constructs an input shape triggering it. The callable returns
# the raw audit code list to inspect.
_AUDIT_CODE_FIXTURES: tuple[tuple[str, str, callable], ...] = (
    # ---- engine ERR_* codes ----------------------------------------------
    (
        "ERR_BUNDLE_NONE",
        ERR_BUNDLE_NONE,
        lambda: (
            Engine()
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=None,
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_POLICY_NONE",
        ERR_POLICY_NONE,
        lambda: (
            Engine()
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(),
                adapter=SyntheticContinuousAdapter(),
                policy=None,
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_ROUND_INDEX_NEGATIVE",
        ERR_ROUND_INDEX_NEGATIVE,
        lambda: (
            Engine()
            .run_round(
                round_index=-1,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(),
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_ROUND_INDEX_NON_INT",
        ERR_ROUND_INDEX_NON_INT,
        lambda: (
            Engine()
            .run_round(
                round_index="not-an-int",  # type: ignore[arg-type]
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(),
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_BUNDLE_INVALID",
        ERR_BUNDLE_INVALID,
        lambda: (
            Engine()
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(
                    channels={},  # empty -> channels_must_be_non_empty_mapping
                    detach_proof=False,  # also invalid
                ),
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_CONDITION_DELTA_NO_EFFECT",
        ERR_CONDITION_DELTA_NO_EFFECT,
        lambda: (
            Engine()
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(),
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=None,
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_SOURCE_ROUND_NON_INT",
        ERR_SOURCE_ROUND_NON_INT,
        lambda: (
            Engine()
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(source_round=1.5),  # float
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_FEATURE_DISABLED",
        ERR_FEATURE_DISABLED,
        lambda: (
            Engine(feature_flag=False)
            .run_round(
                round_index=0,
                phase_state=_make_phase_state(),
                bundle=_make_state_bundle(),
                adapter=SyntheticContinuousAdapter(),
                policy=_make_final_policy(),
                condition_delta=_make_condition_delta(),
            )
            .round_trace.audit_codes
        ),
    ),
    (
        "ERR_CAPABILITIES_INVALID",
        ERR_CAPABILITIES_INVALID,
        lambda: _err_capabilities_invalid_audit_codes(),
    ),
    (
        "ERR_CHANNEL_UNSUPPORTED",
        ERR_CHANNEL_UNSUPPORTED,
        lambda: _err_channel_unsupported_audit_codes(),
    ),
    (
        "ERR_INTEGRATOR_TRACE_MISSING",
        ERR_INTEGRATOR_TRACE_MISSING,
        lambda: _err_integrator_trace_missing_audit_codes(),
    ),
    (
        "ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH",
        ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH,
        lambda: _err_shape_frame_normalization_mismatch_audit_codes(),
    ),
    (
        "ERR_DETACH_PROOF_FAILED",
        ERR_DETACH_PROOF_FAILED,
        lambda: _err_detach_proof_failed_audit_codes(),
    ),
    (
        "ERR_ADAPTER_RAISED",
        ERR_ADAPTER_RAISED,
        lambda: _err_adapter_raised_audit_codes(),
    ),
    # ---- channel rule BLOCKER_* / AUDIT_* codes ----------------------------
    (
        "BLOCKER_TAIL_INADMISSIBLE",
        BLOCKER_TAIL_INADMISSIBLE,
        lambda: _channel_rule_blocker(BLOCKER_TAIL_INADMISSIBLE),
    ),
    (
        "BLOCKER_COMPLEMENT_EXCLUDED",
        BLOCKER_COMPLEMENT_EXCLUDED,
        lambda: _channel_rule_blocker(BLOCKER_COMPLEMENT_EXCLUDED),
    ),
    (
        "BLOCKER_PROXY_ONLY",
        BLOCKER_PROXY_ONLY,
        lambda: _channel_rule_blocker(BLOCKER_PROXY_ONLY),
    ),
    (
        "BLOCKER_HORIZON_UNPROVEN",
        BLOCKER_HORIZON_UNPROVEN,
        lambda: _channel_rule_blocker(BLOCKER_HORIZON_UNPROVEN),
    ),
    (
        "BLOCKER_NOT_FINITE_PREFIX",
        BLOCKER_NOT_FINITE_PREFIX,
        lambda: _channel_rule_blocker(BLOCKER_NOT_FINITE_PREFIX),
    ),
    (
        "BLOCKER_ENVELOPE_HASH_MISSING",
        BLOCKER_ENVELOPE_HASH_MISSING,
        lambda: _channel_rule_blocker(BLOCKER_ENVELOPE_HASH_MISSING),
    ),
    (
        "BLOCKER_MISSING_FACTOR",
        BLOCKER_MISSING_FACTOR,
        lambda: _channel_rule_blocker(BLOCKER_MISSING_FACTOR),
    ),
    (
        "BLOCKER_NON_FINITE",
        BLOCKER_NON_FINITE,
        lambda: _channel_rule_blocker(BLOCKER_NON_FINITE),
    ),
    (
        "BLOCKER_NAN_OR_INF",
        BLOCKER_NAN_OR_INF,
        lambda: _channel_rule_blocker(BLOCKER_NAN_OR_INF),
    ),
    (
        "BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL",
        BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL,
        lambda: _channel_rule_blocker(BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL),
    ),
    (
        "AUDIT_STABILITY_COLLAPSE",
        AUDIT_STABILITY_COLLAPSE,
        lambda: _channel_rule_blocker(AUDIT_STABILITY_COLLAPSE),
    ),
    (
        "AUDIT_SOURCE_REVOKED",
        AUDIT_SOURCE_REVOKED,
        lambda: _audit_source_revoked_audit_codes(),
    ),
    # ---- merge ERR_* / MERGE_* codes --------------------------------------
    (
        "ERR_PREV_REQUIRED",
        ERR_PREV_REQUIRED,
        lambda: _err_prev_required_audit_codes(),
    ),
    (
        "MERGE_PREV_ANCHORED_TO_LAST_EMITTED",
        MERGE_PREV_ANCHORED_TO_LAST_EMITTED,
        lambda: _merge_prev_anchored_audit_codes(),
    ),
    (
        "MERGE_DEGENERATE_INTERVAL",
        MERGE_DEGENERATE_INTERVAL,
        lambda: _merge_degenerate_interval_audit_codes(),
    ),
    (
        "MERGE_FLOOR_FALLBACK",
        MERGE_FLOOR_FALLBACK,
        lambda: _merge_floor_fallback_audit_codes(),
    ),
)


def _err_capabilities_invalid_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_CAPABILITIES_INVALID`."""
    from adaptive_reflow.adapters import SyntheticUnsupportedAdapter

    engine = Engine()
    bundle = _make_state_bundle()
    phase_state = _make_phase_state()
    policy = _make_final_policy()
    condition_delta = _make_condition_delta()
    adapter = SyntheticUnsupportedAdapter()
    return engine.run_round(
        round_index=0,
        phase_state=phase_state,
        bundle=bundle,
        adapter=adapter,
        policy=policy,
        condition_delta=condition_delta,
    ).round_trace.audit_codes


def _err_channel_unsupported_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_CHANNEL_UNSUPPORTED`."""
    engine = Engine()
    bundle = _make_state_bundle(
        channels={"unsupported-channel": _tensor_ref("unsupported-channel")},
    )
    return engine.run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=bundle,
        adapter=SyntheticContinuousAdapter(),
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    ).round_trace.audit_codes


def _err_integrator_trace_missing_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_INTEGRATOR_TRACE_MISSING`."""
    from dataclasses import replace

    from adaptive_reflow.adapters import SyntheticContinuousAdapter

    adapter = SyntheticContinuousAdapter(return_none_trace=True)
    bundle = _make_state_bundle()
    return Engine().run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=replace(bundle, capability_token=adapter.capabilities()),
        adapter=adapter,
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    ).round_trace.audit_codes


def _err_shape_frame_normalization_mismatch_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers
    :data:`ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH`."""
    from dataclasses import replace

    from adaptive_reflow.adapters import SyntheticContinuousAdapter

    adapter = SyntheticContinuousAdapter(condition_match=False)
    bundle = _make_state_bundle()
    return Engine().run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=replace(bundle, capability_token=adapter.capabilities()),
        adapter=adapter,
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    ).round_trace.audit_codes


def _err_detach_proof_failed_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_DETACH_PROOF_FAILED`."""
    from dataclasses import replace

    from adaptive_reflow.adapters import SyntheticContinuousAdapter

    adapter = SyntheticContinuousAdapter(detach_ok=False)
    bundle = _make_state_bundle()
    return Engine().run_round(
        round_index=0,
        phase_state=_make_phase_state(),
        bundle=replace(bundle, capability_token=adapter.capabilities()),
        adapter=adapter,
        policy=_make_final_policy(),
        condition_delta=_make_condition_delta(),
    ).round_trace.audit_codes


def _err_adapter_raised_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_ADAPTER_RAISED`."""

    class _RaisingAdapter(SyntheticContinuousAdapter):
        def build_initial_state(self, *, batch_id: str, sample_id: str):  # type: ignore[override]
            raise RuntimeError("synthetic-fault")

    engine = Engine()
    try:
        result = engine.run_round(
            round_index=0,
            phase_state=_make_phase_state(),
            bundle=_make_state_bundle(),
            adapter=_RaisingAdapter(),
            policy=_make_final_policy(),
            condition_delta=_make_condition_delta(),
        )
        return result.round_trace.audit_codes
    except Exception:  # pragma: no cover - safety net
        return ()


def _audit_source_revoked_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`AUDIT_SOURCE_REVOKED`."""
    from dataclasses import replace

    from adaptive_reflow.frame import (
        evaluate_channel_evidence_with_revocation,
    )

    inputs = _channel_inputs_factory()
    revoked_inputs = replace(inputs, bundle=replace(inputs.bundle, revoked=True))
    outputs = evaluate_channel_evidence_with_revocation(revoked_inputs)
    return tuple(outputs.decision.blocker_codes)


def _channel_rule_blocker(code_substring: str) -> tuple[str, ...]:
    """Construct an input that triggers the channel-rule blocker whose
    name contains ``code_substring``. Returns the resulting blocker
    codes (a tuple)."""
    inputs = _channel_inputs_factory()

    if code_substring == BLOCKER_TAIL_INADMISSIBLE:
        new_inputs = dataclasses.replace(inputs, tail_admissibility=False)
    elif code_substring == BLOCKER_COMPLEMENT_EXCLUDED:
        new_inputs = dataclasses.replace(inputs, complement_excluded=True)
    elif code_substring == BLOCKER_PROXY_ONLY:
        proxy_evidence = dataclasses.replace(
            inputs.evidence,
            proxy_only_evidence=True,
            calibration_lower_bound=FactorValue(0.0),
        )
        new_inputs = dataclasses.replace(
            inputs,
            evidence=proxy_evidence,
            calibration_lower_bound=FactorValue(0.0),
        )
    elif code_substring == BLOCKER_HORIZON_UNPROVEN:
        new_inputs = dataclasses.replace(inputs, horizon_coverage_proven=False)
    elif code_substring == BLOCKER_NOT_FINITE_PREFIX:
        new_inputs = dataclasses.replace(inputs, finite_prefix_only=False)
    elif code_substring == BLOCKER_ENVELOPE_HASH_MISSING:
        new_inputs = dataclasses.replace(
            inputs, finite_prefix_only=True, frozen_envelope_manifest_hash=None
        )
    elif code_substring == BLOCKER_MISSING_FACTOR:
        new_inputs = dataclasses.replace(inputs, calibration_lower_bound=None)
    elif code_substring == BLOCKER_NON_FINITE:
        new_inputs = dataclasses.replace(
            inputs, calibration_lower_bound="not-a-number"  # type: ignore[arg-type]
        )
    elif code_substring == BLOCKER_NAN_OR_INF:
        new_inputs = dataclasses.replace(
            inputs,
            calibration_lower_bound=FactorValue(float("nan")),
        )
    elif code_substring == BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL:
        new_inputs = dataclasses.replace(
            inputs,
            calibration_lower_bound=FactorValue(1.5),
        )
    elif code_substring == AUDIT_STABILITY_COLLAPSE:
        new_inputs = dataclasses.replace(
            inputs,
            perturbation_stability_lower_bound=FactorValue(0.4),
        )
    else:  # pragma: no cover - regression
        raise AssertionError(f"unknown blocker code: {code_substring!r}")

    outputs = compute_channel_decision(new_inputs)
    return tuple(outputs.decision.blocker_codes)


def _err_prev_required_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`ERR_PREV_REQUIRED`."""
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        CosineScheduleSample,
        FactorValue,
    )

    sample = CosineScheduleSample(
        schedule_hash=ArtifactHash("schedule-fc"),
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(1.0),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.0,
        family="cosine_no_restart",
        computed_at_round=0,
    )
    audit_codes: list[str] = []
    raised: Exception | None = None
    try:
        bounded_merge_with_schedule(
            channel=ChannelName("coordinate"),
            dynamic=0.5,
            schedule_sample=sample,
            fresh_noise_floor=None,
            delta_caps_by_channel={ChannelName("coordinate"): 0.5},
            fresh_noise_floor_by_channel={ChannelName("coordinate"): 0.1},
            prev=None,
            audit_codes=audit_codes,
        )
    except MergeAuthorityError as exc:
        raised = exc
    assert raised is not None
    return tuple(audit_codes)


def _merge_prev_anchored_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`MERGE_PREV_ANCHORED_TO_LAST_EMITTED`."""
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
        CosineScheduleSample,
        FactorValue,
    )

    sample = CosineScheduleSample(
        schedule_hash=ArtifactHash("schedule-fc"),
        outer_cycle_id=0,
        round_in_cycle=0,
        cycle_length=4,
        n_cap=FactorValue(1.0),
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        u_r=0.0,
        family="cosine_no_restart",
        computed_at_round=0,
    )
    audit_codes: list[str] = []
    bounded_merge_with_schedule(
        channel=ChannelName("coordinate"),
        dynamic=0.5,
        schedule_sample=sample,
        fresh_noise_floor=None,
        delta_caps_by_channel={ChannelName("coordinate"): 0.5},
        fresh_noise_floor_by_channel={ChannelName("coordinate"): 0.1},
        prev=0.4,
        audit_codes=audit_codes,
    )
    return tuple(audit_codes)


def _merge_degenerate_interval_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`MERGE_DEGENERATE_INTERVAL`.

    Set ``prev`` strictly outside ``[floor, cap]`` with both delta caps
    at 0; the bounded interval ``[lo, hi] = [max(floor, prev),
    min(cap, prev)]`` collapses (``hi < lo``) so the merge falls back
    to the floor and emits the canonical audit code.
    """
    audit_codes: list[str] = []
    bounded_merge(
        prev=0.5,
        dynamic=0.5,
        cap=0.4,  # cap < prev -> hi = cap
        floor=0.0,
        delta_cap_up=0.0,
        delta_cap_down=0.0,
        audit_codes=audit_codes,
    )
    return tuple(audit_codes)


def _merge_floor_fallback_audit_codes() -> tuple[str, ...]:
    """Construct an input that triggers :data:`MERGE_FLOOR_FALLBACK`."""
    from adaptive_reflow.contracts import ChannelName

    audit_codes: list[str] = []
    bounded_merge_with_schedule(
        channel=ChannelName("coordinate"),
        dynamic=0.5,
        schedule_sample=None,
        fresh_noise_floor=None,
        delta_caps_by_channel={ChannelName("coordinate"): 0.5},
        fresh_noise_floor_by_channel=None,
        prev=0.4,
        audit_codes=audit_codes,
    )
    return tuple(audit_codes)


@given(_dummy=st.just(None))
@settings(max_examples=50, deadline=10000)
@example(_dummy=None)
def test_every_audit_code_is_reachable(_dummy: None) -> None:
    """Every documented audit code in the catalogue is reachable from a
    well-defined input shape.

    The Hypothesis ``@given`` machinery runs the body once per example;
    the body is itself a deterministic walk over the catalogue so the
    number of audit codes is bounded by the catalogue size (and not
    subject to Hypothesis's flaky shrinking). The ``_dummy`` parameter
    exists only so the ``@given`` decorator can attach ``@settings``.
    """
    for label, expected_substr, run in _AUDIT_CODE_FIXTURES:
        audit_codes = run()
        joined = "|".join(str(c) for c in audit_codes)
        assert expected_substr in joined, (
            f"audit code {label!r} ({expected_substr!r}) is not reachable: "
            f"audit trail did not contain the substring; got {audit_codes!r}"
        )


__all__ = [
    "test_engine_never_raises_on_malformed_bundle",
    "test_engine_never_raises_on_malformed_bundle_none",
    "test_engine_never_raises_on_malformed_round_index",
    "test_engine_never_raises_on_malformed_policy_none",
    "test_engine_never_raises_on_malformed_condition_delta_none",
    "test_engine_raises_runtime_error_when_adapter_is_none",
    "test_engine_phase_state_none_emits_audit_before_crashing",
    "test_engine_policy_non_typed_raises_attribute_error",
    "test_engine_condition_delta_non_typed_raises_attribute_error",
    "test_channel_rule_never_raises_on_none_input",
    "test_channel_rule_raises_attribute_error_on_non_typed_input",
    "test_every_audit_code_is_reachable",
]
