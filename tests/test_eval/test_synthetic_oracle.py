"""Tests for the SyntheticEvaluator (DTB-R7 / DTB-R8 CPU oracle).

Acceptance
----------

* :meth:`SyntheticEvaluator.evaluate` and :meth:`SyntheticEvaluator.oracle`
  return byte-for-byte equal values for every input.
* :meth:`SyntheticEvaluator.evaluate` is fully deterministic across
  repeated calls.
* Evaluating the same bundle with adjacent seeds produces two
  distinct scores (the closed-form perturbation oracle).
* Monotonically incrementing the digest's low byte yields a
  monotonically increasing ``raw_score``.
* The module is torch-free: ``"torch" not in sys.modules``.
* Driving :meth:`AdaptiveReflowPolicyOrchestrator.evaluate_bundle`
  with synthetic evidence emits a non-empty ledger row whose per-
  channel decisions carry the synthetic audit reason in their
  provenance chain.

No torch. No GPU. No external oracle.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping

import pytest

from adaptive_reflow.contracts import (
    ArtifactHash,
    BundleId,
    ChannelName,
    ConditionDigest,
    EnvelopeLayer,
    FactorValue,
    FrameSpec,
    MechanismId,
    ProvenanceChain,
    RoundResultBundle,
    RunId,
    SampleId,
    ShapeSpec,
    TraceDigest,
    hash_artifact,
    hash_trace_digest,
)
from adaptive_reflow.envelope.manifest import FrozenEnvelopeManifest
from adaptive_reflow.eval.synthetic_oracle import (
    SYNTHETIC_AUDIT_REASON,
    SyntheticEvaluator,
)
from adaptive_reflow.frame import AdaptiveReflowPolicyOrchestrator
from adaptive_reflow.schedule import CosineScheduleSampler
from adaptive_reflow.schedule.cosine import CosineScheduleConfig
from adaptive_reflow.universal.adapter import AdapterCapabilities
from adaptive_reflow.universal.state import StateBundle, TensorRef

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


_COORDINATE = ChannelName("coordinate")
_COORDINATE_TENSOR = TensorRef("coord-tensor-ref-001")
_TEST_BATCH_ID: str = "batch-synthetic"
_TEST_SAMPLE_ID: str = "sample-synthetic"


def _make_state_bundle(
    digest: str = "abcdef0123456789",
    *,
    sample_id: str = _TEST_SAMPLE_ID,
    batch_id: str = _TEST_BATCH_ID,
) -> StateBundle:
    """Build a minimal valid :class:`StateBundle` for the synthetic evaluator.

    The bundle is wired with a single ``coordinate`` channel, a
    ``world`` reference frame and a ``none`` normalisation so it
    validates against :func:`validate_state_bundle` end-to-end. The
    caller picks the digest; the test harness uses this parameter
    to drive the monotonicity and perturbation tests.
    """
    return StateBundle(
        channels={_COORDINATE: _COORDINATE_TENSOR},
        masks={},
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.synthetic_oracle",),
        capability_token=AdapterCapabilities(
            has_ode_integration_surface=False,
            has_prior_export=False,
            has_state_export=False,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=(_COORDINATE,),
            channel_domains={_COORDINATE: "continuous"},
        ),
    )


def _make_round_bundle_for_synthetic(
    state_bundle: StateBundle,
) -> RoundResultBundle:
    """Build a :class:`RoundResultBundle` whose ``bundle_id`` matches the synthetic evaluator.

    The synthetic evaluator derives the bundle-id from
    ``native_state_digest``; the round-result bundle must use the
    same id so :meth:`AdaptiveReflowPolicyOrchestrator.evaluate_bundle`
    accepts the emitted evidence rows.
    """
    bundle_id_str = SyntheticEvaluator._derive_bundle_id(state_bundle)  # noqa: SLF001 — test seam
    bundle_id = BundleId(bundle_id_str)
    trace_digest = TraceDigest(
        hash_trace_digest(
            bundle_id,
            int(state_bundle.source_round),
            1,
            RunId("run-synthetic"),
            SampleId(state_bundle.sample_id),
        )
    )
    return RoundResultBundle(
        bundle_id=bundle_id,
        source_round=int(state_bundle.source_round),
        round_count=1,
        run_id=RunId("run-synthetic"),
        sample_id=SampleId(state_bundle.sample_id),
        trace_digest=trace_digest,
        condition_digest=ConditionDigest(
            hash_artifact({"condition": "synthetic-oracle"})
        ),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-synthetic"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={"source_round": 0, "channel": "coordinate"},
        charge_channel=None,
        raw_pair_channel=None,
        projected_pair_channel=None,
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec=ShapeSpec({}),
        frame_spec=FrameSpec({}),
        provenance=ProvenanceChain((MechanismId("test.synthetic_oracle"),)),
        created_at_round=0,
        revoked=False,
    )


def _make_envelope_manifest() -> FrozenEnvelopeManifest:
    """Build a single-layer frozen envelope manifest for the round-trip test.

    Constructed via direct :class:`FrozenEnvelopeManifest` instantiation
    (mirroring ``tests/test_frame/test_merge.py``) rather than the
    builder because the builder rejects empty ``ArtifactHash`` values
    on the layer's provenance fields, which the test manifest does
    not need.
    """
    layer = EnvelopeLayer(
        layer_index=0,
        label="synthetic-loose",
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
    manifest = FrozenEnvelopeManifest(
        manifest_id="manifest-synthetic",
        run_id="run-synthetic",
        sample_id=_TEST_SAMPLE_ID,
        target_pocket_hash=ArtifactHash("pocket-synthetic"),
        config_hash=ArtifactHash("cfg-synthetic"),
        created_at_round=0,
        layers=(layer,),
        empirical_only=True,
        finite_prefix_only=True,
        tail_selection_certified=False,
        manifest_hash=ArtifactHash(""),
    )
    payload = {
        "manifest_id": manifest.manifest_id,
        "layers": [
            {f.name: getattr(layer_, f.name) for f in layer.__dataclass_fields__.values()}
            for layer_ in manifest.layers
        ],
        "finite_prefix_only": manifest.finite_prefix_only,
        "empirical_only": manifest.empirical_only,
        "tail_selection_certified": manifest.tail_selection_certified,
    }
    digest = hash_artifact(payload)
    return FrozenEnvelopeManifest(
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        sample_id=manifest.sample_id,
        target_pocket_hash=manifest.target_pocket_hash,
        config_hash=manifest.config_hash,
        created_at_round=manifest.created_at_round,
        layers=manifest.layers,
        empirical_only=manifest.empirical_only,
        finite_prefix_only=manifest.finite_prefix_only,
        tail_selection_certified=manifest.tail_selection_certified,
        manifest_hash=digest,
    )


def _make_schedule_config() -> CosineScheduleConfig:
    """Build a :class:`CosineScheduleConfig` matching the test merge harness."""
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=4,
        n_min=FactorValue(0.0),
        n_max=FactorValue(0.5),
        per_channel_caps={
            _COORDINATE: FactorValue(1.0),
            ChannelName("charge"): FactorValue(1.0),
            ChannelName("raw_pair"): FactorValue(1.0),
            ChannelName("projected_pair"): FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            _COORDINATE: FactorValue(0.0),
            ChannelName("charge"): FactorValue(0.0),
            ChannelName("raw_pair"): FactorValue(0.0),
            ChannelName("projected_pair"): FactorValue(0.0),
        },
        symmetric_delta_caps_by_channel={
            _COORDINATE: FactorValue(0.5),
            ChannelName("charge"): FactorValue(0.5),
            ChannelName("raw_pair"): FactorValue(0.5),
            ChannelName("projected_pair"): FactorValue(0.5),
        },
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("cfg-synthetic"),
        frozen_before_evaluation=True,
    )


def _make_orchestrator() -> AdaptiveReflowPolicyOrchestrator:
    """Wire the orchestrator with envelope + schedule for the round-trip test."""
    envelope = _make_envelope_manifest()
    schedule = _make_schedule_config()
    return AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=envelope,
        schedule_config=schedule,
        schedule_sampler=CosineScheduleSampler(schedule),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_evaluator_equals_oracle_byte_for_byte() -> None:
    """``evaluate`` and ``oracle`` must return byte-for-byte equal values."""
    evaluator = SyntheticEvaluator()
    bundle = _make_state_bundle(digest="deadbeefcafe1234")
    seed = 17
    evidence = evaluator.evaluate(bundle, channel=_COORDINATE, seed=seed)
    oracle = evaluator.oracle(bundle, channel=_COORDINATE, seed=seed)

    # Byte-for-byte equality on every published diagnostic.
    assert float(evidence.raw_score) == oracle["raw_score"]
    assert float(evidence.bounded_score) == oracle["bounded_score"]
    assert float(evidence.calibration_lower_bound) == oracle[
        "calibration_lower_bound"
    ]
    assert float(evidence.perturbation_stability_lower_bound) == oracle[
        "perturbation_stability_lower_bound"
    ]

    # Same on a second (different) seed.
    seed2 = 99
    evidence2 = evaluator.evaluate(bundle, channel=_COORDINATE, seed=seed2)
    oracle2 = evaluator.oracle(bundle, channel=_COORDINATE, seed=seed2)
    assert float(evidence2.raw_score) == oracle2["raw_score"]
    assert float(evidence2.bounded_score) == oracle2["bounded_score"]
    assert float(evidence2.calibration_lower_bound) == oracle2[
        "calibration_lower_bound"
    ]
    assert float(evidence2.perturbation_stability_lower_bound) == oracle2[
        "perturbation_stability_lower_bound"
    ]


def test_evaluator_is_deterministic() -> None:
    """100 repeated calls must produce byte-identical evidence rows."""
    evaluator = SyntheticEvaluator()
    bundle = _make_state_bundle(digest="0123456789abcdef")
    seed = 1234

    first = evaluator.evaluate(bundle, channel=_COORDINATE, seed=seed)
    for _ in range(99):
        again = evaluator.evaluate(bundle, channel=_COORDINATE, seed=seed)
        assert again.raw_score == first.raw_score
        assert again.bounded_score == first.bounded_score
        assert again.calibration_lower_bound == first.calibration_lower_bound
        assert again.perturbation_stability_lower_bound == (
            first.perturbation_stability_lower_bound
        )
        # Bundle-id and channel must also be byte-identical across calls.
        assert again.bundle_id == first.bundle_id
        assert again.channel == first.channel
        assert again.provenance == first.provenance


def test_perturbation_oracle() -> None:
    """Adjacent seeds must produce distinct published diagnostics."""
    evaluator = SyntheticEvaluator()
    bundle = _make_state_bundle(digest="0123456789abcdef")
    base_seed = 0x1234

    base_evidence = evaluator.evaluate(
        bundle, channel=_COORDINATE, seed=base_seed
    )
    next_evidence = evaluator.evaluate(
        bundle, channel=_COORDINATE, seed=base_seed + 1
    )

    # The perturbation oracle: same bundle, adjacent seeds, distinct
    # outputs on every published diagnostic. The closed-form XOR with
    # seed means the values are guaranteed to differ for any digest
    # whose low 32 bits are not pinned to exactly the bit that flips
    # between ``base_seed`` and ``base_seed + 1``; even on that
    # pathological input the calibration + perturbation diagnostics
    # are computed with distinct XOR constants and must still differ.
    assert base_evidence.raw_score != next_evidence.raw_score
    assert base_evidence.calibration_lower_bound != (
        next_evidence.calibration_lower_bound
    )
    assert base_evidence.perturbation_stability_lower_bound != (
        next_evidence.perturbation_stability_lower_bound
    )


def test_monotonicity_oracle() -> None:
    """Incrementing the digest's low byte must increase ``raw_score``."""
    evaluator = SyntheticEvaluator()

    # Build 8 digest strings whose first 8 bytes are exactly the
    # little-endian sequence ``NUL*NUL + ASCII('a' + i)`` so the
    # uint64 increment is exactly ``+1`` between adjacent entries.
    # The high bytes (0x00) keep the high half stable; the low byte
    # moves through 0x61 .. 0x68, so the masked low-32-bit score
    # steps up by exactly ``1 / 2**32`` per digest.
    digests = [chr(ord("a") + i) + "\x00" * 7 for i in range(8)]
    bundles = [_make_state_bundle(digest=d) for d in digests]
    scores = [
        evaluator.oracle(b, channel=_COORDINATE, seed=0)["raw_score"]
        for b in bundles
    ]

    # Strict monotonicity across the full sequence: every step is
    # exactly ``1 / 2**32`` so we can assert equality rather than a
    # fuzzy > comparison.
    expected_step = 1.0 / float(1 << 32)
    for idx in range(len(scores) - 1):
        delta = scores[idx + 1] - scores[idx]
        assert delta == pytest.approx(expected_step, rel=0.0, abs=0.0), (
            f"step {idx}: expected {expected_step!r}, got {delta!r}"
        )


def test_no_torch_imported() -> None:
    """The synthetic oracle must not depend on ``torch`` at import time.

    Runs the import in a fresh subprocess so this assertion is
    decoupled from pytest collection order. See
    :func:`tests._utils.import_isolation.assert_import_is_torch_free`.
    """
    from tests._utils.import_isolation import assert_import_is_torch_free

    assert_import_is_torch_free("adaptive_reflow.eval.synthetic_oracle")


def test_dtb_r7_orchestrator_round_trip() -> None:
    """Drive :meth:`AdaptiveReflowPolicyOrchestrator.evaluate_bundle` with synthetic evidence."""
    evaluator = SyntheticEvaluator()
    state_bundle = _make_state_bundle(digest="feedfacefeedface")
    round_bundle = _make_round_bundle_for_synthetic(state_bundle)

    # Emit one evidence row per canonical channel so the orchestrator
    # can drive every channel decision.
    evidence_by_channel: dict[ChannelName, object] = {}
    for channel_name in (
        ChannelName("coordinate"),
        ChannelName("charge"),
        ChannelName("raw_pair"),
        ChannelName("projected_pair"),
    ):
        evidence_by_channel[channel_name] = evaluator.evaluate(
            state_bundle, channel=channel_name, seed=2026
        )

    orchestrator = _make_orchestrator()
    ledger = orchestrator.evaluate_bundle(round_bundle, evidence_by_channel)  # type: ignore[arg-type]

    # The ledger row must carry exactly one evidence row per channel.
    assert len(ledger.per_channel_evidence) == 4
    assert len(ledger.per_channel_decision) == 4

    # Every emitted evidence row must carry the synthetic audit reason
    # in its provenance chain (the evaluator's signature surface).
    for evidence in ledger.per_channel_evidence:
        assert MechanismId(SYNTHETIC_AUDIT_REASON) in tuple(evidence.provenance)

    # The ledger row must validate against the canonical contract:
    # it carries a finite-prefix-only, empirical-only stamp and
    # validation_errors is empty.
    assert ledger.finite_prefix_only is True
    assert ledger.empirical_only is True
    assert ledger.validation_errors == ()

    # And the orchestrator must be able to build a verified final
    # policy from the freshly emitted ledger row.
    policy = orchestrator.build_final_policy(ledger)
    assert policy is not None


# ---------------------------------------------------------------------------
# Auxiliary assertions (cheap; protect the public surface)
# ---------------------------------------------------------------------------


def test_is_deterministic_returns_true() -> None:
    """The evaluator must always report ``is_deterministic() == True``."""
    assert SyntheticEvaluator().is_deterministic() is True
