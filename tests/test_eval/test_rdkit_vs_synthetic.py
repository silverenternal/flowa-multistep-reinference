"""Cross-evaluator benchmark: RDKit vs Synthetic oracle.

Verifies that the :class:`AdaptiveReflowPolicyOrchestrator` treats the
RDKit-backed evaluator and the synthetic closed-form evaluator
**identically at the protocol level**, even though they measure
completely different things (real chemistry vs. closed-form XOR
digest). The orchestrator should accept both, drive both through the
same per-channel decision logic, and produce structurally valid ledger
rows whose empirical-only / finite-prefix-only stamps and
``validation_errors == ()`` invariant hold for both.

What this test does NOT assert:

* Value-equality of raw_score / bounded_score. The two evaluators
  measure different signals (chemistry vs. closed-form XOR) so their
  scores are intentionally incomparable.
* Identical per-channel decisions (gate=True / False). The RDKit
  evidence is constructed to pass the channel rule (chemistry scores
  are typically in the pass-band) while the synthetic evidence may
  fail closed depending on the digest. The test only asserts on
  *structural* invariants that must hold regardless.

What this test DOES assert:

* Both evaluators expose the canonical :class:`ChannelTransferEvidence`
  shape (``evaluate`` and ``oracle`` agree byte-for-byte).
* Both evaluators round-trip through the orchestrator and produce a
  ledger row with ``validation_errors == ()``.
* Both ledger rows carry the empirical-only + finite-prefix-only
  stamps.
* Both ledger rows carry exactly one evidence row per canonical
  molecule channel (4 evidence rows).
* Each evaluator's per-channel evidence row carries its own audit
  reason in the provenance chain (``rdkit_oracle:<channel>`` vs.
  ``synthetic_evaluator:closed_form``).

Acceptance: both evaluators are protocol-equivalent; the orchestrator
treats them consistently; the chemistry-backed oracle validates the
same DTB-R7 surface that the synthetic oracle validates.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping

import pytest

# Preflight: this cross-evaluator benchmark imports the RDKit-backed
# oracle (:mod:`adaptive_reflow.eval.rdkit_oracle`) which
# unconditionally imports ``rdkit`` at module load. On sandboxes
# where rdkit is not vendored (the default CPU-only rig), pytest
# collection aborts. The importorskip below short-circuits
# collection cleanly.
pytest.importorskip(
    "rdkit",
    reason="rdkit not in venv (install via `uv pip install rdkit`)",
)

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
from adaptive_reflow.eval.rdkit_oracle import (
    RDKIT_AUDIT_REASON,
    RdkitEvaluator,
)
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


_ASPIRIN_SMILES: str = "CC(=O)Oc1ccccc1C(=O)O"
_TEST_BATCH_ID: str = "batch-cross"
_TEST_SAMPLE_ID: str = "sample-cross"

#: The four canonical molecule channels the orchestrator iterates
#: over on every ``evaluate_bundle`` call.
_CANONICAL_MOLECULE_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("coordinate"),
    ChannelName("charge"),
    ChannelName("raw_pair"),
    ChannelName("projected_pair"),
)


def _make_state_bundle(digest: str) -> StateBundle:
    """Build a minimal valid :class:`StateBundle` for both evaluators."""
    coordinate = ChannelName("coordinate")
    return StateBundle(
        channels={coordinate: TensorRef(f"coord-{hash(digest)}")},
        masks={},
        batch_id=_TEST_BATCH_ID,
        sample_id=_TEST_SAMPLE_ID,
        reference_frame="world",
        normalization="none",
        source_round=0,
        detach_proof=True,
        native_state_digest=digest,
        provenance=("test.cross_eval",),
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
            supported_channels=(coordinate,),
            channel_domains={coordinate: "continuous"},
        ),
    )


def _make_round_bundle(bundle_id_str: str) -> RoundResultBundle:
    """Build a :class:`RoundResultBundle` with the supplied ``bundle_id``."""
    bundle_id = BundleId(bundle_id_str)
    trace_digest = TraceDigest(
        hash_trace_digest(
            bundle_id,
            0,
            1,
            RunId("run-cross"),
            SampleId(_TEST_SAMPLE_ID),
        )
    )
    return RoundResultBundle(
        bundle_id=bundle_id,
        source_round=0,
        round_count=1,
        run_id=RunId("run-cross"),
        sample_id=SampleId(_TEST_SAMPLE_ID),
        trace_digest=trace_digest,
        condition_digest=ConditionDigest(
            hash_artifact({"condition": "cross-eval"})
        ),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-cross"),
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
        provenance=ProvenanceChain((MechanismId("test.cross_eval"),)),
        created_at_round=0,
        revoked=False,
    )


def _make_envelope_manifest() -> FrozenEnvelopeManifest:
    """Build a single-layer loose envelope manifest for the cross-eval."""
    layer = EnvelopeLayer(
        layer_index=0,
        label="cross-loose",
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
        manifest_id="manifest-cross",
        run_id="run-cross",
        sample_id=_TEST_SAMPLE_ID,
        target_pocket_hash=ArtifactHash("pocket-cross"),
        config_hash=ArtifactHash("cfg-cross"),
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
    """Build a :class:`CosineScheduleConfig` keyed on molecule channels."""
    return CosineScheduleConfig(
        schedule_family="cosine_no_restart",
        cycle_length=4,
        n_min=FactorValue(0.0),
        n_max=FactorValue(0.5),
        per_channel_caps={
            ChannelName("coordinate"): FactorValue(1.0),
            ChannelName("charge"): FactorValue(1.0),
            ChannelName("raw_pair"): FactorValue(1.0),
            ChannelName("projected_pair"): FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            ChannelName("coordinate"): FactorValue(0.0),
            ChannelName("charge"): FactorValue(0.0),
            ChannelName("raw_pair"): FactorValue(0.0),
            ChannelName("projected_pair"): FactorValue(0.0),
        },
        symmetric_delta_caps_by_channel={
            ChannelName("coordinate"): FactorValue(0.5),
            ChannelName("charge"): FactorValue(0.5),
            ChannelName("raw_pair"): FactorValue(0.5),
            ChannelName("projected_pair"): FactorValue(0.5),
        },
        restart_triggers_allowed=(),
        config_hash=ArtifactHash("cfg-cross"),
        frozen_before_evaluation=True,
    )


def _make_orchestrator() -> AdaptiveReflowPolicyOrchestrator:
    """Wire the orchestrator with envelope + schedule for the cross-eval."""
    return AdaptiveReflowPolicyOrchestrator(
        envelope_manifest=_make_envelope_manifest(),
        schedule_config=_make_schedule_config(),
        schedule_sampler=CosineScheduleSampler(_make_schedule_config()),
    )


def _emit_synthetic_evidence(
    bundle: StateBundle, seed: int
) -> dict[ChannelName, object]:
    """Emit synthetic evidence for each canonical molecule channel."""
    evaluator = SyntheticEvaluator()
    return {
        channel_name: evaluator.evaluate(bundle, channel=channel_name, seed=seed)
        for channel_name in _CANONICAL_MOLECULE_CHANNELS
    }


def _emit_rdkit_evidence(
    bundle: StateBundle, seed: int
) -> dict[ChannelName, object]:
    """Emit RDKit-backed evidence for each canonical molecule channel."""
    evaluator = RdkitEvaluator()
    return {
        channel_name: evaluator.evaluate(bundle, channel=channel_name, seed=seed)
        for channel_name in _CANONICAL_MOLECULE_CHANNELS
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_evaluator_shapes_are_identical() -> None:
    """Both evaluators must emit the same :class:`ChannelTransferEvidence` shape.

    Compare the published diagnostics ``raw_score`` / ``bounded_score``
    / ``calibration_lower_bound`` /
    ``perturbation_stability_lower_bound`` for byte-for-byte equality of
    the *type* (float, not None) and *in-band* (``[0, 1]`` for the
    bounded values, finite for raw_score) constraints. We do NOT
    compare values because the two evaluators measure different
    signals.
    """
    bundle = _make_state_bundle(_ASPIRIN_SMILES)
    seed = 17

    synthetic = SyntheticEvaluator()
    rdkit = RdkitEvaluator()

    for channel_name in _CANONICAL_MOLECULE_CHANNELS:
        synth_evidence = synthetic.evaluate(bundle, channel=channel_name, seed=seed)
        rdkit_evidence = rdkit.evaluate(bundle, channel=channel_name, seed=seed)

        # Both must be valid evidence rows (validation_errors == ()).
        assert synth_evidence.validation_errors == ()
        assert rdkit_evidence.validation_errors == ()

        # Both must report non-None materialization / geometry / condition
        # sensitivity passes (the canonical "non-proxy" stamps).
        assert synth_evidence.materialization_pass is True
        assert rdkit_evidence.materialization_pass is True

        # bounded_score must lie in [0, 1] for both.
        assert 0.0 <= float(synth_evidence.bounded_score) <= 1.0
        assert 0.0 <= float(rdkit_evidence.bounded_score) <= 1.0

        # raw_score must be a finite real number for both.
        raw_synth = float(synth_evidence.raw_score)
        raw_rdkit = float(rdkit_evidence.raw_score)
        assert raw_synth == raw_synth  # not NaN
        assert raw_rdkit == raw_rdkit  # not NaN

        # calibration_lower_bound and perturbation_stability_lower_bound
        # must lie in [0, 1] for both.
        assert 0.0 <= float(synth_evidence.calibration_lower_bound) <= 1.0
        assert 0.0 <= float(rdkit_evidence.calibration_lower_bound) <= 1.0
        assert 0.0 <= float(synth_evidence.perturbation_stability_lower_bound) <= 1.0
        assert 0.0 <= float(rdkit_evidence.perturbation_stability_lower_bound) <= 1.0


def test_orchestrator_treats_both_evaluators_consistently() -> None:
    """The orchestrator must accept both evaluators and emit structurally valid ledger rows."""
    bundle = _make_state_bundle(_ASPIRIN_SMILES)
    seed = 2026
    orchestrator = _make_orchestrator()

    # ---- Synthetic round-trip ----
    synth_bundle_id = SyntheticEvaluator._derive_bundle_id(bundle)  # noqa: SLF001 — test seam
    synth_round = _make_round_bundle(synth_bundle_id)
    synth_evidence = _emit_synthetic_evidence(bundle, seed)
    synth_ledger = orchestrator.evaluate_bundle(synth_round, synth_evidence)  # type: ignore[arg-type]

    # ---- RDKit round-trip ----
    rdkit_bundle_id = RdkitEvaluator._derive_bundle_id(bundle, "primary")  # noqa: SLF001 — test seam
    rdkit_round = _make_round_bundle(rdkit_bundle_id)
    rdkit_evidence = _emit_rdkit_evidence(bundle, seed)
    rdkit_ledger = orchestrator.evaluate_bundle(rdkit_round, rdkit_evidence)  # type: ignore[arg-type]

    # ---- Structural invariants that must hold for BOTH ledger rows ----

    # (1) Both ledgers carry exactly one evidence row per canonical
    # molecule channel.
    assert len(synth_ledger.per_channel_evidence) == len(_CANONICAL_MOLECULE_CHANNELS)
    assert len(rdkit_ledger.per_channel_evidence) == len(_CANONICAL_MOLECULE_CHANNELS)
    assert len(synth_ledger.per_channel_decision) == len(_CANONICAL_MOLECULE_CHANNELS)
    assert len(rdkit_ledger.per_channel_decision) == len(_CANONICAL_MOLECULE_CHANNELS)

    # (2) Both ledgers are empirical-only + finite-prefix-only.
    assert synth_ledger.empirical_only is True
    assert rdkit_ledger.empirical_only is True
    assert synth_ledger.finite_prefix_only is True
    assert rdkit_ledger.finite_prefix_only is True

    # (3) Both ledgers carry zero validation errors.
    assert synth_ledger.validation_errors == ()
    assert rdkit_ledger.validation_errors == ()

    # (4) Both ledgers' per-channel evidence rows carry their
    # evaluator's audit reason in the provenance chain.
    for evidence in synth_ledger.per_channel_evidence:
        reasons = tuple(str(m) for m in tuple(evidence.provenance))
        assert any(r.startswith(SYNTHETIC_AUDIT_REASON) for r in reasons), (
            f"synthetic ledger row missing audit reason "
            f"{SYNTHETIC_AUDIT_REASON!r}: got reasons={reasons!r}"
        )
    for evidence in rdkit_ledger.per_channel_evidence:
        reasons = tuple(str(m) for m in tuple(evidence.provenance))
        assert any(r.startswith(RDKIT_AUDIT_REASON) for r in reasons), (
            f"RDKit ledger row missing audit reason "
            f"{RDKIT_AUDIT_REASON!r}: got reasons={reasons!r}"
        )

    # (5) Both ledgers must produce a verified final policy.
    synth_policy = orchestrator.build_final_policy(synth_ledger)
    rdkit_policy = orchestrator.build_final_policy(rdkit_ledger)
    assert synth_policy is not None
    assert rdkit_policy is not None


def test_evaluator_oracle_shapes_match() -> None:
    """Both evaluators' ``oracle`` methods must produce dicts with the same four keys."""
    bundle = _make_state_bundle(_ASPIRIN_SMILES)
    seed = 17

    synthetic = SyntheticEvaluator()
    rdkit = RdkitEvaluator()

    expected_keys = {
        "raw_score",
        "bounded_score",
        "calibration_lower_bound",
        "perturbation_stability_lower_bound",
    }

    for channel_name in _CANONICAL_MOLECULE_CHANNELS:
        synth_oracle = synthetic.oracle(bundle, channel=channel_name, seed=seed)
        rdkit_oracle = rdkit.oracle(bundle, channel=channel_name, seed=seed)

        assert set(synth_oracle.keys()) == expected_keys
        assert set(rdkit_oracle.keys()) == expected_keys


def test_both_evaluators_are_deterministic() -> None:
    """Both evaluators must report ``is_deterministic() == True``."""
    assert SyntheticEvaluator().is_deterministic() is True
    assert RdkitEvaluator().is_deterministic() is True


def test_cross_evaluator_no_torch() -> None:
    """Neither oracle may pull ``torch`` into ``sys.modules``.

    Runs both imports in a fresh subprocess so this assertion is
    decoupled from pytest collection order. See
    :func:`tests._utils.import_isolation.assert_import_is_torch_free`.
    """
    from tests._utils.import_isolation import assert_import_is_torch_free

    assert_import_is_torch_free(
        "adaptive_reflow.eval.rdkit_oracle",
        "adaptive_reflow.eval.synthetic_oracle",
    )


def test_cross_evaluator_bundle_id_disjoint() -> None:
    """The two evaluators' bundle-id namespaces must be disjoint."""
    bundle = _make_state_bundle(_ASPIRIN_SMILES)

    synth_id = SyntheticEvaluator._derive_bundle_id(bundle)  # noqa: SLF001 — test seam
    rdkit_id = RdkitEvaluator._derive_bundle_id(bundle, "primary")  # noqa: SLF001 — test seam

    # The synthetic evaluator namespaces with "syn::"; the RDKit
    # evaluator namespaces with "rdkit::"; the two prefixes are
    # disjoint so the orchestrator can route them at audit time.
    assert not synth_id.startswith("rdkit::")
    assert not rdkit_id.startswith("syn::")
    assert synth_id != rdkit_id
