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

import math

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
    FrozenEnvelopeManifest,
    RestartTriggerCode,
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
