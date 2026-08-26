"""Tests for DTB-R7 calibration protocol (CPU-only).

Acceptance:

* Wilson lower bound pure function with known reference values.
* Beta lower bound pure function with known reference values.
* Bucket classification with the manifest's admission policy.
* Manifest JSON round-trip with hash stability.
* ``frozen_before_evaluation`` enforced: post-creation mutation is
  rejected.

No torch. No GPU. No real model load.
"""

from __future__ import annotations

import dataclasses
import json
import math

import pytest

import adaptive_reflow.contracts as rmt
import adaptive_reflow.eval.calibration as cp
import adaptive_reflow.eval.manifests as pm

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _bucket_kwargs(**overrides):
    base = {
        "metric_name": "binding_affinity_kcal",
        "channel": "coordinate",
        "sample_count": 128,
        "lower_bound_value": rmt.FactorValue(0.32),
        "lower_bound_confidence": 0.95,
        "computed_at": "2026-01-15T00:00:00Z",
        "source_stats_hash": rmt.ArtifactHash("stats-hash-001"),
    }
    base.update(overrides)
    return base


def _time_split(**overrides):
    base = {
        "train_period": ("2025-09-01T00:00:00Z", "2025-12-01T00:00:00Z"),
        "frozen_period": ("2025-12-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        "eval_period": ("2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z"),
        "frozen_until_round": 64,
    }
    base.update(overrides)
    return base


def _manifest_kwargs(**overrides):
    base = {
        "manifest_id": rmt.ManifestId("cal-manifest-001"),
        "calibration_dataset": cp.CalibrationDatasetId("dataset-A"),
        "time_split": cp.CalibrationTimeSplit(**_time_split()),
        "per_metric_buckets": {
            "binding_affinity_kcal": (
                cp.CalibrationBucket(**_bucket_kwargs()),
                cp.CalibrationBucket(
                    metric_name="binding_affinity_kcal",
                    channel="charge",
                    sample_count=128,
                    lower_bound_value=rmt.FactorValue(0.28),
                    lower_bound_confidence=0.95,
                    computed_at="2026-01-15T00:00:00Z",
                    source_stats_hash=rmt.ArtifactHash("stats-hash-002"),
                ),
            ),
            "qed": (
                cp.CalibrationBucket(
                    metric_name="qed",
                    channel="coordinate",
                    sample_count=256,
                    lower_bound_value=rmt.FactorValue(0.74),
                    lower_bound_confidence=0.95,
                    computed_at="2026-01-15T00:00:00Z",
                    source_stats_hash=rmt.ArtifactHash("stats-hash-003"),
                ),
            ),
        },
        "min_sample_count": 32,
        "lower_bound_method": "wilson",
        "artifact_hash": rmt.ArtifactHash("artifact-001"),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Wilson lower bound (pure function, known values)
# ---------------------------------------------------------------------------


def test_wilson_lower_bound_zero_trials_returns_zero():
    """Empty buckets must return 0 so the downstream gate stays fail-closed."""
    assert float(cp.wilson_lower_bound(0, 0)) == 0.0
    assert float(cp.wilson_lower_bound(0, 0, confidence=0.99)) == 0.0


def test_wilson_lower_bound_zero_success():
    """Wilson LB at s=0, n=1, conf=0.95 must be 0 (one-sided intuition)."""
    assert float(cp.wilson_lower_bound(0, 1)) == pytest.approx(0.0, abs=1e-12)


def test_wilson_lower_bound_full_success():
    """Wilson LB at s=n=10, conf=0.95 must be approximately 0.7225."""
    lb = float(cp.wilson_lower_bound(10, 10))
    assert lb == pytest.approx(0.7225, abs=1e-3)
    assert 0.0 < lb < 1.0


def test_wilson_lower_bound_half_success_matches_reference():
    """Wilson LB at s=5, n=10, conf=0.95 must be approximately 0.2366.

    Reference: standard Wilson score interval table at p=0.5, n=10.
    """
    lb = float(cp.wilson_lower_bound(5, 10))
    assert lb == pytest.approx(0.2366, abs=1e-3)


def test_wilson_lower_bound_monotonic_in_trials_at_fixed_rate():
    """Higher trial count (same success rate) yields a tighter (higher) LB."""
    s, n = 5, 10
    lb_small = float(cp.wilson_lower_bound(s, n))
    lb_large = float(cp.wilson_lower_bound(50, 100))
    assert lb_large > lb_small


def test_wilson_lower_bound_higher_confidence_lowers_bound():
    """At 99% the LB is more conservative than at 95%."""
    assert float(cp.wilson_lower_bound(5, 10, confidence=0.99)) < float(
        cp.wilson_lower_bound(5, 10, confidence=0.95)
    )


def test_wilson_lower_bound_rejects_bad_inputs():
    with pytest.raises(ValueError):
        cp.wilson_lower_bound(-1, 10)
    with pytest.raises(ValueError):
        cp.wilson_lower_bound(11, 10)
    with pytest.raises(ValueError):
        cp.wilson_lower_bound(5, 10, confidence=1.5)


def test_wilson_lower_bound_returns_factor_value_type():
    """The return type must be a FactorValue NewType wrapper around float."""
    out = cp.wilson_lower_bound(5, 10)
    # NewType wrappers are runtime-transparent: the value is a float.
    assert isinstance(out, float)
    assert 0.0 <= float(out) <= 1.0


# ---------------------------------------------------------------------------
# Beta lower bound (pure function, known values)
# ---------------------------------------------------------------------------


def test_beta_lower_bound_zero_trials_returns_zero():
    assert float(cp.beta_lower_bound(0, 0)) == 0.0


def test_beta_lower_bound_uniform_prior_at_zero_success():
    """Beta(1, 2) lower quantile at p=0.025 has the closed form
    ``x = 1 - sqrt(1 - 0.025) = 1 - sqrt(0.975) ~= 0.012580`` (one-sided).
    """
    lb = float(cp.beta_lower_bound(0, 1))
    expected = 1.0 - math.sqrt(0.975)
    assert lb == pytest.approx(expected, abs=1e-5)


def test_beta_lower_bound_symmetric_at_half_success():
    """Beta(6, 6) lower quantile at p=0.025 is ≈ 0.234 (the 2.5% lower
    tail of a symmetric Beta(6, 6) whose mode is at 0.5).
    """
    lb = float(cp.beta_lower_bound(5, 10))
    assert 0.22 < lb < 0.24
    assert lb == pytest.approx(0.234, abs=1e-2)


def test_beta_lower_bound_monotonic_in_trials():
    """At p=0.5 (s = n/2), larger n narrows the posterior; LB moves toward 0.5."""
    lb_small = float(cp.beta_lower_bound(5, 10))
    lb_large = float(cp.beta_lower_bound(50, 100))
    assert abs(lb_large - 0.5) < abs(lb_small - 0.5)


def test_beta_lower_bound_higher_confidence_lowers_bound():
    assert float(cp.beta_lower_bound(5, 10, confidence=0.99)) < float(
        cp.beta_lower_bound(5, 10, confidence=0.95)
    )


def test_beta_lower_bound_rejects_bad_inputs():
    with pytest.raises(ValueError):
        cp.beta_lower_bound(-1, 10)
    with pytest.raises(ValueError):
        cp.beta_lower_bound(11, 10)
    with pytest.raises(ValueError):
        cp.beta_lower_bound(5, 10, confidence=1.5)


def test_beta_lower_bound_returns_factor_value_type():
    out = cp.beta_lower_bound(5, 10)
    # NewType wrappers are runtime-transparent; the value is a float.
    assert isinstance(out, float)
    assert 0.0 <= float(out) <= 1.0


def test_beta_and_wilson_converge_for_large_n():
    """For large n the two lower bounds converge (same confidence)."""
    s, n = 500, 1000
    wilson = float(cp.wilson_lower_bound(s, n))
    beta = float(cp.beta_lower_bound(s, n))
    assert abs(beta - wilson) < 0.02


# ---------------------------------------------------------------------------
# Bucket classification
# ---------------------------------------------------------------------------


def test_classify_bucket_admits_above_min_sample():
    bucket = cp.CalibrationBucket(**_bucket_kwargs(sample_count=128))
    assert cp.classify_bucket(bucket, min_sample_count=32) == "admit"


def test_classify_bucket_rejects_below_min_sample():
    bucket = cp.CalibrationBucket(**_bucket_kwargs(sample_count=8))
    assert cp.classify_bucket(bucket, min_sample_count=32) == "reject_low_sample"


def test_classify_bucket_admits_at_exact_min_sample():
    bucket = cp.CalibrationBucket(**_bucket_kwargs(sample_count=32))
    assert cp.classify_bucket(bucket, min_sample_count=32) == "admit"


def test_bucket_constructor_rejects_empty_metric_name():
    with pytest.raises(ValueError):
        cp.CalibrationBucket(**_bucket_kwargs(metric_name=""))


def test_bucket_constructor_rejects_empty_source_stats_hash():
    with pytest.raises(ValueError):
        cp.CalibrationBucket(**_bucket_kwargs(source_stats_hash=rmt.ArtifactHash("")))


def test_bucket_constructor_rejects_negative_sample_count():
    with pytest.raises(ValueError):
        cp.CalibrationBucket(**_bucket_kwargs(sample_count=-1))


def test_bucket_constructor_rejects_lower_bound_out_of_range():
    with pytest.raises(ValueError):
        cp.CalibrationBucket(
            **_bucket_kwargs(lower_bound_value=rmt.FactorValue(1.5))
        )


# ---------------------------------------------------------------------------
# Manifest round-trip + hash stability
# ---------------------------------------------------------------------------


def test_manifest_round_trip_via_json():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    text = pm.write_calibration_manifest(manifest)
    parsed = json.loads(text)
    # Round-trip back to manifest.
    restored = pm.read_calibration_manifest(text)
    # Compare field-by-field (the round-tripped artifact_hash is recomputed
    # from the canonical payload, so it may differ from the original; we
    # check the canonical content fields instead).
    assert restored.manifest_id == manifest.manifest_id
    assert restored.calibration_dataset == manifest.calibration_dataset
    assert restored.time_split == manifest.time_split
    assert restored.min_sample_count == manifest.min_sample_count
    assert restored.lower_bound_method == manifest.lower_bound_method
    assert (
        restored.per_metric_buckets.keys()
        == manifest.per_metric_buckets.keys()
    )
    for metric in manifest.per_metric_buckets:
        orig = manifest.per_metric_buckets[metric]
        new = restored.per_metric_buckets[metric]
        assert len(orig) == len(new)
        for o, n in zip(orig, new, strict=False):
            assert o.metric_name == n.metric_name
            assert o.channel == n.channel
            assert o.sample_count == n.sample_count
            assert float(o.lower_bound_value) == float(n.lower_bound_value)
            assert o.lower_bound_confidence == n.lower_bound_confidence
            assert o.source_stats_hash == n.source_stats_hash
    # JSON contains the deferred sentinel fields set to None.
    assert parsed["gpu_provenance_hash"] is None
    assert parsed["checkpoint_hash"] is None
    assert parsed["data_split_manifest_hash"] is None
    assert parsed["source_evaluator_version"] is None
    assert parsed["round_trace_hash"] is None
    assert parsed["failure_taxonomy"] == []
    # frozen_before_evaluation is True in the serialized payload.
    assert parsed["frozen_before_evaluation"] is True


def test_manifest_round_trip_is_hash_stable():
    """Serializing the same manifest twice yields byte-identical JSON."""
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    first = pm.write_calibration_manifest(manifest)
    second = pm.write_calibration_manifest(manifest)
    assert first == second


def test_manifest_round_trip_with_unordered_buckets_is_hash_stable():
    """Two manifests built from differently-ordered bucket dicts must
    serialize to the same JSON bytes."""
    a_buckets = {
        "qed": (
            cp.CalibrationBucket(
                metric_name="qed",
                channel="coordinate",
                sample_count=256,
                lower_bound_value=rmt.FactorValue(0.74),
                lower_bound_confidence=0.95,
                computed_at="2026-01-15T00:00:00Z",
                source_stats_hash=rmt.ArtifactHash("stats-hash-003"),
            ),
        ),
        "binding_affinity_kcal": (
            cp.CalibrationBucket(**_bucket_kwargs()),
        ),
    }
    b_buckets = {
        "binding_affinity_kcal": (
            cp.CalibrationBucket(**_bucket_kwargs()),
        ),
        "qed": (
            cp.CalibrationBucket(
                metric_name="qed",
                channel="coordinate",
                sample_count=256,
                lower_bound_value=rmt.FactorValue(0.74),
                lower_bound_confidence=0.95,
                computed_at="2026-01-15T00:00:00Z",
                source_stats_hash=rmt.ArtifactHash("stats-hash-003"),
            ),
        ),
    }
    manifest_a = cp.CalibrationManifest(**_manifest_kwargs(per_metric_buckets=a_buckets))
    manifest_b = cp.CalibrationManifest(**_manifest_kwargs(per_metric_buckets=b_buckets))
    assert pm.write_calibration_manifest(manifest_a) == pm.write_calibration_manifest(
        manifest_b
    )


def test_read_manifest_rejects_non_deferred_gpu_field():
    """A JSON payload carrying a populated GPU field is rejected."""
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    text = pm.write_calibration_manifest(manifest)
    parsed = json.loads(text)
    parsed["gpu_provenance_hash"] = "not-deferred"
    tampered = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ValueError):
        pm.read_calibration_manifest(tampered)


def test_read_manifest_accepts_explicit_deferred_sentinel():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    text = pm.write_calibration_manifest(manifest)
    parsed = json.loads(text)
    parsed["checkpoint_hash"] = pm.DEFERRED_GPU_SENTINEL
    tampered = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    restored = pm.read_calibration_manifest(tampered)
    assert restored.manifest_id == manifest.manifest_id


# ---------------------------------------------------------------------------
# frozen_before_evaluation enforcement
# ---------------------------------------------------------------------------


def test_frozen_before_evaluation_default_is_true():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    assert manifest.frozen_before_evaluation is True


def test_manifest_rejects_post_creation_mutation():
    """``frozen=True`` + ``Literal[True]`` -> post-creation mutation fails."""
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    with pytest.raises(dataclasses.FrozenInstanceError):
        manifest.min_sample_count = 999  # type: ignore[misc]


def test_bucket_rejects_post_creation_mutation():
    bucket = cp.CalibrationBucket(**_bucket_kwargs())
    with pytest.raises(dataclasses.FrozenInstanceError):
        bucket.sample_count = 999  # type: ignore[misc]


def test_validator_rejects_non_true_frozen_flag():
    """``frozen_before_evaluation`` is Literal[True]; bypassing the
    dataclass via :func:`dataclasses.replace` would be the only way to set
    it False, and the validator catches it. We verify the validator directly
    on a synthetic manifest where we mutate after construction.
    """
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    # Force the flag to False via object.__setattr__ (the only path that
    # bypasses the frozen dataclass).
    object.__setattr__(manifest, "frozen_before_evaluation", False)
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is False
    assert any("frozen_before_evaluation" in e for e in errors)


def test_validator_accepts_valid_manifest():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is True
    assert errors == ()


def test_validator_rejects_empty_per_metric_buckets():
    manifest = cp.CalibrationManifest(**_manifest_kwargs(per_metric_buckets={}))
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is False
    assert any("per_metric_buckets" in e for e in errors)


def test_validator_rejects_negative_min_sample_count():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    # Bypass the dataclass's __post_init__ via object.__setattr__ so we
    # can exercise the validator on a manifest with a negative value.
    object.__setattr__(manifest, "min_sample_count", -1)
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is False
    assert any("min_sample_count" in e for e in errors)


def test_validator_rejects_invalid_lower_bound_method():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    object.__setattr__(manifest, "lower_bound_method", "bogus")
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is False
    assert any("lower_bound_method" in e for e in errors)


def test_validator_rejects_negative_frozen_until_round():
    manifest = cp.CalibrationManifest(**_manifest_kwargs())
    new_split = dataclasses.replace(
        manifest.time_split, frozen_until_round=-1
    )
    object.__setattr__(manifest, "time_split", new_split)
    ok, errors = pm.validate_manifest_frozen(manifest)
    assert ok is False
    assert any("frozen_until_round" in e for e in errors)


# ---------------------------------------------------------------------------
# Stability perturbation protocol
# ---------------------------------------------------------------------------


def test_stability_protocol_accepts_valid_inputs():
    proto = cp.StabilityPerturbationProtocol(
        seed_perturbations=(1, 2, 3),
        condition_perturbations=("shift-x", "shift-y", "shift-z"),
        per_target_min_samples=8,
    )
    assert proto.per_target_min_samples == 8


def test_stability_protocol_rejects_empty_seeds():
    with pytest.raises(ValueError):
        cp.StabilityPerturbationProtocol(
            seed_perturbations=(),
            condition_perturbations=("a",),
        )


def test_stability_protocol_rejects_empty_conditions():
    with pytest.raises(ValueError):
        cp.StabilityPerturbationProtocol(
            seed_perturbations=(1,),
            condition_perturbations=(),
        )


def test_stability_protocol_rejects_low_min_samples():
    with pytest.raises(ValueError):
        cp.StabilityPerturbationProtocol(
            seed_perturbations=(1,),
            condition_perturbations=("a",),
            per_target_min_samples=0,
        )
