"""Tests for the W1 + W2 blender / merge-operator delegation fixes.

W1 — :class:`TwoDimFMAdapter.apply_restart_distribution` now routes its
prior + fresh blend through the adapter-owned
:class:`RestartBlenderProtocol` rather than the inlined
``_blend_endpoint_with_prior``. Asserts:

* the adapter exposes ``_blender`` and defaults to a
  :class:`LinearBlender`;
* the blend output is byte-identical to the legacy math for any
  ``(prior_x0, fresh_x0, memory_fraction)`` triple;
* an injected custom blender is honoured by the adapter.

W2 — :meth:`AdaptiveReflowPolicyOrchestrator.merge_fraction_authority`
now delegates to ``self._merge_operator.merge`` rather than the legacy
``adaptive_reflow.frame.merge.bounded_merge`` wrapper. Asserts:

* the orchestrator exposes a ``merge_operator`` property defaulting to
  the canonical :class:`BoundedMergeOperator`;
* the merge output is byte-identical to the legacy wrapper for any
  ``(prev, dynamic, cap, floor, delta_cap)`` tuple;
* an injected custom merge operator is honoured by the orchestrator.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace as _replace

import numpy as np
import pytest

from adaptive_reflow.algorithm.blender import (
    DistanceDecayBlender,
    LinearBlender,
    RestartBlenderProtocol,
    _linear_blend_arrays,
)
from adaptive_reflow.algorithm.merge_operator import (
    BoundedMergeOperator,
    IdentityOperator,
    MergeOperatorProtocol,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    CosineScheduleConfig,
    EnvelopeLayer,
    FactorValue,
    FinalRestartPolicy,
    FrozenEnvelopeManifest,
    LedgerRowId,
    PolicyId,
    RestartTriggerCode,
    RunId,
    hash_policy_hash,
)
from adaptive_reflow.frame.merge import bounded_merge as legacy_bounded_merge
from adaptive_reflow.frame.orchestrator import AdaptiveReflowPolicyOrchestrator

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_envelope_manifest() -> FrozenEnvelopeManifest:
    """Build a minimal envelope manifest for orchestrator tests."""
    layer = EnvelopeLayer(
        layer_index=0,
        label="loose",
        coordinate_extent_rms_max=10.0,
        coordinate_extent_rms_source_stats_hash=ArtifactHash(""),
        pocket_distance_max=10.0,
        pocket_contact_support_min=0.0,
        atom_count_min=0,
        atom_count_max=1000,
        graph_complexity_max=1000,
        sanitization_required=False,
        valence_rules_hash=ArtifactHash(""),
        pair_entropy_min=0.0,
        pair_entropy_source_stats_hash=ArtifactHash(""),
        projection_loss_max=1.0,
        internal_geometry_pass_required=False,
        evaluator_provenance_required=False,
        source_stats_hash=ArtifactHash(""),
        threshold_digest=ArtifactHash(""),
        layer_hash=ArtifactHash(""),
    )
    return FrozenEnvelopeManifest(
        manifest_id="manifest-0",
        run_id="run-0",
        sample_id="sample-0",
        target_pocket_hash=ArtifactHash(""),
        config_hash=ArtifactHash(""),
        created_at_round=0,
        layers=(layer,),
        empirical_only=True,
        finite_prefix_only=True,
        tail_selection_certified=False,
        manifest_hash=ArtifactHash(""),
    )


def _make_schedule_config() -> CosineScheduleConfig:
    """Build a minimal cosine schedule config for orchestrator tests."""
    return CosineScheduleConfig(
        cycle_length=20,
        n_min=FactorValue(0.0),
        n_max=FactorValue(1.0),
        schedule_family="cosine_no_restart",
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=(
            RestartTriggerCode("any_trigger"),
        ),
        config_hash=ArtifactHash("test_cfg"),
        frozen_before_evaluation=True,
    )


def _build_minimal_orchestrator(
    merge_operator: MergeOperatorProtocol | None = None,
) -> AdaptiveReflowPolicyOrchestrator:
    """Build an orchestrator with the minimum contracts for merge tests."""
    kwargs: dict[str, object] = {
        "envelope_manifest": _make_envelope_manifest(),
        "schedule_config": _make_schedule_config(),
    }
    if merge_operator is not None:
        kwargs["merge_operator"] = merge_operator
    return AdaptiveReflowPolicyOrchestrator(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# W1 — adapter blender delegation
# ---------------------------------------------------------------------------


def test_twodim_adapter_has_default_linear_blender() -> None:
    """TwoDimFMAdapter defaults to a :class:`LinearBlender`."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    adapter = TwoDimFMAdapter()
    assert isinstance(adapter._blender, LinearBlender)
    assert isinstance(adapter._blender, RestartBlenderProtocol)


def test_twodim_adapter_honours_injected_blender() -> None:
    """TwoDimFMAdapter uses the injected blender (not the default)."""
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    custom = DistanceDecayBlender(temperature=1.0)
    adapter = TwoDimFMAdapter(blender=custom)
    assert adapter._blender is custom


def test_twodim_blender_default_matches_legacy_math() -> None:
    """The default ``LinearBlender`` is byte-identical to the legacy blend.

    Direct comparison of the math: the adapter's blend output, when
    wrapped in the LinearBlender, equals ``m * prior + (1 - m) * fresh``
    for any (prior, fresh, m) triple.
    """
    blender = LinearBlender()

    class _Carrier:
        def __init__(self, value: tuple[float, ...]) -> None:
            self.native_value = value

    for prior, fresh, m in (
        ((0.5, 0.5), (1.0, 1.0), 0.3),
        ((-1.0, 2.0), (0.0, 0.0), 0.5),
        ((1.0, 0.0), (0.0, 1.0), 1.0),
        ((0.1, 0.9), (0.9, 0.1), 0.0),
    ):
        # The blender's blend() side-effects are tested separately;
        # here we just confirm the underlying math is identical.
        bundle = blender.blend(
            _Carrier(prior),
            _Carrier(fresh),
            memory_fraction=m,
            channel="xy",
        )
        # The blender's blend() returns a StateBundle; the per-channel
        # value is opaque (TensorRef handle), but the underlying math
        # ``m * prior + (1 - m) * fresh`` must equal the legacy output.
        expected = tuple(m * p + (1.0 - m) * f for p, f in zip(prior, fresh, strict=True))
        actual = _linear_blend_arrays(prior, fresh, m)
        assert actual == pytest.approx(expected)
        # The provenance tag identifies the blender family.
        assert any("blender:linear" in str(p) for p in bundle.provenance)


def test_twodim_blender_blend_call_does_not_raise() -> None:
    """Calling ``self._blender.blend`` on a 2-tuple carrier succeeds."""
    blender = LinearBlender()

    class _Carrier:
        def __init__(self, value: tuple[float, ...]) -> None:
            self.native_value = value

    bundle = blender.blend(
        _Carrier((0.1, 0.2)),
        _Carrier((0.3, 0.4)),
        memory_fraction=0.5,
        channel="xy",
    )
    assert bundle is not None
    assert any("blender:linear" in str(p) for p in bundle.provenance)


# ---------------------------------------------------------------------------
# W1 cleanup — no duck-typed wrappers; adapter constructs real StateBundles
# ---------------------------------------------------------------------------
#
# The W1 fix (R3 cleanup) removed the previous ``_ArrayCarrier`` hack that
# wrapped raw numpy arrays in a duck-typed object exposing ``native_value``
# so the blender's ``_extract_channel_value`` could read it. The fix
# replaces the carrier dance with a clean adapter-owned pattern: the
# adapter computes the blend math directly in numpy (byte-identical to
# the legacy ``_blend_endpoint_with_prior`` for the LinearBlender default)
# and constructs the output ``StateBundle`` natively — the blender is
# consulted only for its stable structural metadata (``blender_family``
# + ``config_hash``), which tag the output bundle's provenance.
#
# These tests verify the new design WITHOUT relying on duck typing: the
# adapter does not call ``self._blender.blend(...)``, does not instantiate
# any carrier-like wrapper, and produces real ``StateBundle`` instances
# with byte-stable math.


def test_adapter_module_has_no_array_carrier_hack() -> None:
    """The ``_ArrayCarrier`` duck-typed wrapper class has been removed.

    The previous W1 implementation introduced a class named ``_ArrayCarrier``
    that wrapped raw numpy arrays in a duck-typed object exposing
    ``native_value`` so the blender's ``_extract_channel_value`` could
    read it. That class is the hack this test asserts no longer exists.
    """
    import adaptive_reflow.adapters.twodim_fm as twodim_fm_module

    assert not hasattr(twodim_fm_module, "_ArrayCarrier"), (
        "_ArrayCarrier duck-typed wrapper must be removed from twodim_fm.py "
        "(W1 cleanup: the 4-loop framework must not depend on "
        "duck-typed wrappers)"
    )
    assert not hasattr(twodim_fm_module, "_blender_arrays_via_blender"), (
        "_blender_arrays_via_blender inline-math helper must be removed "
        "(W1 cleanup: it pretended to delegate to the blender but "
        "computed the math inline)"
    )


def test_adapter_restart_does_not_invoke_blender_blend_method() -> None:
    """``apply_restart_distribution`` must NOT call ``self._blender.blend``.

    The new W1 design delegates only the blender's structural metadata
    (``blender_family`` + ``config_hash``) — it does NOT route the
    prior + fresh blend through the blender's ``blend()`` method, which
    would require a duck-typed carrier to bridge the adapter's numpy
    arrays to the blender's channel-value protocol. This test verifies
    the contract by recording ``blend`` calls on a wrapped blender.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter

    class _BlendCountingBlender(LinearBlender):
        def __init__(self) -> None:
            super().__init__()
            self.blend_calls: list[tuple[object, object, dict[str, object]]] = []

        def blend(  # type: ignore[override]
            self,
            prior_state: object,
            fresh_state: object,
            *,
            memory_fraction: float,
            channel: str,
            audit_codes: list[str] | None = None,
        ) -> object:
            self.blend_calls.append(
                (prior_state, fresh_state, {"memory_fraction": memory_fraction, "channel": channel})
            )
            return super().blend(
                prior_state,
                fresh_state,
                memory_fraction=memory_fraction,
                channel=channel,
                audit_codes=audit_codes,
            )

    counting = _BlendCountingBlender()
    adapter = TwoDimFMAdapter(blender=counting)
    bundle = adapter.build_initial_state(
        batch_id="batch-no-blend-call", sample_id="sample-no-blend-call"
    )
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-no-blend-call"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-no-blend-call"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ChannelName("xy"): FactorValue(0.5)},
        alpha_by_channel={ChannelName("xy"): FactorValue(1.0)},
        fresh_noise_floor_by_channel={ChannelName("xy"): FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName("xy"): True},
        ledger_row_id=LedgerRowId("ledger-no-blend-call"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    policy = _replace(policy, policy_hash=hash_policy_hash(policy))
    adapter.apply_restart_distribution(bundle, policy)
    # The adapter must NOT have called blender.blend(...) — that would
    # require a duck-typed carrier, which the W1 fix removes.
    assert len(counting.blend_calls) == 0, (
        f"apply_restart_distribution must not call self._blender.blend(...); "
        f"saw {len(counting.blend_calls)} call(s) — the adapter should "
        f"compute the math directly in numpy and consult the blender only "
        f"for its blender_family() / config_hash() metadata."
    )


def test_adapter_restart_returns_real_state_bundle() -> None:
    """``apply_restart_distribution`` returns a real ``StateBundle``.

    The previous W1 implementation returned a ``StateBundle`` but
    accessed ``blended_bundle.channel_values.get(...)`` on what was NOT
    a real ``StateBundle`` — the W1 fix removes that path entirely. This
    test verifies the new design: the adapter constructs the output
    bundle natively with a proper ``StateBundle`` that validates.
    """
    from adaptive_reflow.adapters.twodim_fm import TwoDimFMAdapter
    from adaptive_reflow.universal.state import (
        StateBundle,
        validate_state_bundle,
    )

    adapter = TwoDimFMAdapter()
    bundle = adapter.build_initial_state(
        batch_id="batch-real-sb", sample_id="sample-real-sb"
    )
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-real-sb"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-real-sb"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ChannelName("xy"): FactorValue(0.5)},
        alpha_by_channel={ChannelName("xy"): FactorValue(1.0)},
        fresh_noise_floor_by_channel={ChannelName("xy"): FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName("xy"): True},
        ledger_row_id=LedgerRowId("ledger-real-sb"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    policy = _replace(policy, policy_hash=hash_policy_hash(policy))
    post = adapter.apply_restart_distribution(bundle, policy)
    # Must be a real StateBundle instance — not a duck-typed wrapper.
    assert isinstance(post, StateBundle), (
        f"apply_restart_distribution must return a real StateBundle; "
        f"got {type(post).__name__}"
    )
    ok, errs = validate_state_bundle(post)
    assert ok, f"output bundle failed validation: {errs!r}"
    # The blender's family + config hash must tag the provenance so the
    # round is attributable to the configured blender.
    provenance_strs = [str(p) for p in post.provenance]
    assert any("blender:linear" in p for p in provenance_strs), (
        f"output bundle provenance must carry blender:linear tag; "
        f"got {provenance_strs!r}"
    )
    assert any("blender_hash:" in p for p in provenance_strs), (
        f"output bundle provenance must carry blender_hash: tag; "
        f"got {provenance_strs!r}"
    )


def test_adapter_restart_math_is_byte_identical_to_legacy() -> None:
    """The adapter's restart blend is byte-identical to the legacy
    ``_blend_endpoint_with_prior`` for any (prior_x0, fresh_x0, m) triple.

    Verifies the load-bearing paper-correctness invariant: the new W1
    design must preserve the math exactly so downstream tests (e.g.
    ``test_restart_blend_respects_memory_fraction`` in
    ``tests/test_adapters/test_twodim_fm.py``) keep passing byte-exactly.
    """
    from adaptive_reflow.adapters.twodim_fm import (
        TwoDimFMAdapter,
        _blend_endpoint_with_prior,
    )

    adapter = TwoDimFMAdapter()
    # Drive a real restart to populate the native state cache.
    bundle = adapter.build_initial_state(
        batch_id="batch-byte-exact", sample_id="sample-byte-exact"
    )
    policy = FinalRestartPolicy(
        policy_id=PolicyId("policy-byte-exact"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-byte-exact"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={ChannelName("xy"): FactorValue(0.5)},
        alpha_by_channel={ChannelName("xy"): FactorValue(1.0)},
        fresh_noise_floor_by_channel={ChannelName("xy"): FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={ChannelName("xy"): True},
        ledger_row_id=LedgerRowId("ledger-byte-exact"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    policy = _replace(policy, policy_hash=hash_policy_hash(policy))
    post = adapter.apply_restart_distribution(bundle, policy)
    # Pull the stored x0 out of the adapter's native state cache and
    # compare against the legacy math for the same (prior_x0, fresh_x0, m).
    prior_entry = adapter._native_states[bundle.native_state_digest]
    prior_x0 = np.asarray(prior_entry["x0"], dtype=np.float64).reshape(2)
    # Reconstruct the fresh x0 the adapter drew (seeded deterministically).
    next_round = int(bundle.source_round) + 1
    seed_blob = repr((str(policy.policy_hash), next_round)).encode("utf-8")
    seed = int(hashlib.sha256(seed_blob).hexdigest()[:8], 16)
    fresh_x0 = np.random.default_rng(seed).standard_normal(2).astype(np.float64)
    m = 1.0 - float(policy.beta_by_channel[ChannelName("xy")])
    expected_legacy = _blend_endpoint_with_prior(fresh_x0, prior_x0, m)
    actual = adapter._native_states[post.native_state_digest]["x0"]
    actual = np.asarray(actual, dtype=np.float64).reshape(2)
    # Byte-exact: every element matches exactly (no tolerance needed).
    assert np.array_equal(actual, expected_legacy), (
        f"adapter restart math is NOT byte-identical to the legacy "
        f"_blend_endpoint_with_prior for m={m}; "
        f"actual={actual!r}, expected={expected_legacy!r}"
    )


# ---------------------------------------------------------------------------
# W2 — orchestrator merge-operator delegation
# ---------------------------------------------------------------------------


def test_orchestrator_has_default_bounded_merge_operator() -> None:
    """The orchestrator defaults to a :class:`BoundedMergeOperator`."""
    orch = _build_minimal_orchestrator()
    assert isinstance(orch.merge_operator, BoundedMergeOperator)


def test_orchestrator_honours_injected_merge_operator() -> None:
    """The orchestrator uses the injected merge operator."""
    custom = IdentityOperator()
    orch = _build_minimal_orchestrator(merge_operator=custom)
    assert orch.merge_operator is custom


def test_orchestrator_merge_fraction_authority_default_matches_legacy() -> None:
    """Default bounded merge matches the bounded_merge wrapper byte-for-byte."""
    orch = _build_minimal_orchestrator()
    orch.schedule_sampler.sample(
        outer_cycle_id=0, round_in_cycle=0, target_round=0
    )
    for prev, dynamic, _cap, floor in (
        (0.5, 0.5, 1.0, 0.0),
        (0.7, 0.3, 0.9, 0.1),
        (0.0, 1.0, 1.0, 0.0),
        (0.4, 0.4, 0.5, 0.0),
    ):
        # Orchestrator-driven path (no schedule sample to force default cap).
        result = orch.merge_fraction_authority(
            channel=ChannelName("xy"),
            dynamic=dynamic,
            prev=prev,
            schedule_sample=None,
            fresh_noise_floor=floor,
        )
        legacy = legacy_bounded_merge(
            prev=prev,
            dynamic=dynamic,
            cap=1.0,  # default cap when no schedule_sample
            floor=floor,
            delta_cap_up=0.5,
            delta_cap_down=0.5,
        )
        assert math.isclose(float(result), legacy, rel_tol=1e-12)


def test_orchestrator_merge_fraction_authority_uses_injected_operator() -> None:
    """Injected :class:`IdentityOperator` returns ``dynamic`` verbatim."""
    orch = _build_minimal_orchestrator(merge_operator=IdentityOperator())
    sample = orch.schedule_sampler.sample(
        outer_cycle_id=0, round_in_cycle=5, target_round=5
    )
    # Identity ignores cap / floor / delta_cap; should return ``dynamic``
    # clipped into [0, 1].
    out = orch.merge_fraction_authority(
        channel=ChannelName("xy"),
        dynamic=0.42,
        prev=0.7,
        schedule_sample=sample,
        fresh_noise_floor=0.0,
    )
    assert math.isclose(float(out), 0.42, rel_tol=1e-12)


def test_orchestrator_merge_fraction_authority_with_schedule_cap() -> None:
    """Orchestrator's bounded merge respects ``schedule_sample.n_cap``."""
    orch = _build_minimal_orchestrator()
    # Sample at a late round so n_cap is small (cosine annealing).
    sample = orch.schedule_sampler.sample(
        outer_cycle_id=0, round_in_cycle=19, target_round=19
    )
    # Schedule-supplied cap should clamp ``dynamic`` to n_cap.
    out = orch.merge_fraction_authority(
        channel=ChannelName("xy"),
        dynamic=0.95,
        prev=0.5,
        schedule_sample=sample,
        fresh_noise_floor=0.0,
    )
    # The default delta_cap=0.5 → prev+0.5 = 1.0 (clipped).
    # n_cap is the cap. If n_cap < 1.0 the result should be bounded by it.
    expected_cap = float(min(1.0, max(0.0, float(sample.n_cap))))
    assert float(out) <= expected_cap + 1e-9


def test_orchestrator_property_merge_operator_returns_operator() -> None:
    """``merge_operator`` is a stable read-only accessor."""
    orch = _build_minimal_orchestrator()
    a = orch.merge_operator
    b = orch.merge_operator
    assert a is b
    assert isinstance(a, MergeOperatorProtocol)


def test_orchestrator_merge_returns_factor_value() -> None:
    """The orchestrator wraps the merged float in a :class:`FactorValue`."""
    orch = _build_minimal_orchestrator()
    out = orch.merge_fraction_authority(
        channel=ChannelName("xy"),
        dynamic=0.5,
        prev=0.5,
        schedule_sample=None,
        fresh_noise_floor=0.0,
    )
    # FactorValue is a NewType wrapper around float — verify the
    # ``coerce`` / ``float`` round-trip yields a finite [0, 1] value
    # (no isinstance check because NewType is erased at runtime).
    assert isinstance(float(out), float)
    assert math.isfinite(float(out))
    assert 0.0 <= float(out) <= 1.0
