"""Test the generic :class:`EnvelopeCriterion` Protocol with arbitrary predicates.

The universal :class:`EnvelopeCriterion` Protocol must accept arbitrary
``Predicate`` callables — not just molecule-specific ones. This test
exercises a handful of generic predicate shapes (length, sum, max,
``any``-of-set) to confirm the protocol surface is domain-agnostic.

The molecule-specific :class:`adaptive_reflow.molecular.envelope.MoleculeEnvelopeLayer`
is exercised separately in :mod:`tests.test_molecular` (placeholder in
this phase). The tests below verify the universal surface only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from adaptive_reflow.universal import (
    ArtifactHash,
    BundleId,
    ComplementBlockerCode,
    EnvelopeClassification,
    EnvelopeCriterion,
    Predicate,
    validate_envelope_classification,
    validate_envelope_criterion,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _digest(label: str) -> ArtifactHash:
    import hashlib

    return ArtifactHash(hashlib.sha256(label.encode("utf-8")).hexdigest())


def _criterion(pred: Predicate, threshold: float, label: str) -> EnvelopeCriterion:
    return EnvelopeCriterion(
        predicate=pred,
        threshold=threshold,
        source_stats_hash=_digest(f"src::{label}"),
        threshold_digest=_digest(f"thr::{label}"),
    )


# ---------------------------------------------------------------------------
# Arbitrary generic predicates — none reference molecule vocabulary
# ---------------------------------------------------------------------------


def _length_le(limit: int) -> Predicate:
    """Predicate: True iff ``len(observables) <= limit``."""
    def _pred(observables: Mapping[str, float]) -> bool:
        return len(observables) <= limit
    return Predicate(_pred)


def _sum_above(threshold: float) -> Predicate:
    """Predicate: True iff ``sum(observables.values()) > threshold``."""
    def _pred(observables: Mapping[str, float]) -> bool:
        return sum(observables.values()) > threshold
    return Predicate(_pred)


def _max_above(threshold: float) -> Predicate:
    """Predicate: True iff ``max(observables.values()) > threshold``."""
    def _pred(observables: Mapping[str, float]) -> bool:
        return max(observables.values()) > threshold
    return Predicate(_pred)


def _all_keys_in(allowed: set[str]) -> Predicate:
    """Predicate: True iff every key in ``observables`` is in ``allowed``."""
    def _pred(observables: Mapping[str, float]) -> bool:
        return set(observables.keys()) <= allowed
    return Predicate(_pred)


def _any_above(threshold: float, key: str) -> Predicate:
    """Predicate: True iff ``observables[key] > threshold``."""
    def _pred(observables: Mapping[str, float]) -> bool:
        return observables.get(key, 0.0) > threshold
    return Predicate(_pred)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnvelopeCriterion:
    """The :class:`EnvelopeCriterion` dataclass must be constructible
    with arbitrary predicates."""

    def test_criterion_with_length_predicate(self) -> None:
        """A length-based predicate (no molecule vocab) must construct."""
        crit = _criterion(_length_le(4), 4.0, "len_4")
        assert crit.threshold == 4.0
        assert callable(crit.predicate)

    def test_criterion_with_sum_predicate(self) -> None:
        """A sum-based predicate must construct."""
        crit = _criterion(_sum_above(0.5), 0.5, "sum_above_05")
        assert crit.threshold == 0.5

    def test_criterion_with_max_predicate(self) -> None:
        """A max-based predicate must construct."""
        crit = _criterion(_max_above(0.9), 0.9, "max_above_09")
        assert crit.threshold == 0.9

    def test_criterion_with_set_membership_predicate(self) -> None:
        """A set-membership predicate must construct."""
        crit = _criterion(
            _all_keys_in({"x", "y", "z"}), 0.0, "keys_in_xyz"
        )
        # Evaluate the predicate to verify the behaviour.
        assert crit.predicate({"x": 0.1, "y": 0.2, "z": 0.3}) is True
        assert crit.predicate({"x": 0.1, "a": 0.2}) is False

    def test_criterion_with_named_key_predicate(self) -> None:
        """A named-key predicate must construct and evaluate correctly."""
        crit = _criterion(_any_above(0.5, "x"), 0.5, "x_above_05")
        assert crit.predicate({"x": 0.7}) is True
        assert crit.predicate({"x": 0.3}) is False
        assert crit.predicate({}) is False  # missing key treated as 0.0

    def test_criterion_with_non_molecule_observables(self) -> None:
        """The criterion must accept observable names that are not
        molecule-specific (no coordinate, charge, raw_pair, projected_pair)."""
        crit = _criterion(_any_above(0.0, "length"), 0.0, "length_above_0")
        # Generic observable names.
        assert crit.predicate({"length": 5.0, "mass": 1.0}) is True
        assert crit.predicate({"length": 0.0}) is False
        # The criterion's threshold is informational; the predicate
        # is the actual evaluation.
        assert crit.threshold == 0.0


class TestValidateEnvelopeCriterion:
    """``validate_envelope_criterion`` must enforce the documented invariants."""

    def test_accepts_well_formed_criterion(self) -> None:
        crit = _criterion(_length_le(4), 0.5, "ok")
        ok, errs = validate_envelope_criterion(crit)
        assert ok, errs
        assert errs == ()

    def test_rejects_non_callable_predicate(self) -> None:
        # Construct a malformed criterion by bypassing the type system.
        crit = EnvelopeCriterion(
            predicate="not_callable",  # type: ignore[arg-type]
            threshold=0.5,
            source_stats_hash=_digest("src"),
            threshold_digest=_digest("thr"),
        )
        ok, errs = validate_envelope_criterion(crit)
        assert not ok
        assert "predicate_must_be_callable" in errs

    def test_rejects_empty_source_stats_hash(self) -> None:
        crit = EnvelopeCriterion(
            predicate=_length_le(4),
            threshold=0.5,
            source_stats_hash=ArtifactHash(""),
            threshold_digest=_digest("thr"),
        )
        ok, errs = validate_envelope_criterion(crit)
        assert not ok
        assert "source_stats_hash_must_be_non_empty" in errs

    def test_rejects_empty_threshold_digest(self) -> None:
        crit = EnvelopeCriterion(
            predicate=_length_le(4),
            threshold=0.5,
            source_stats_hash=_digest("src"),
            threshold_digest=ArtifactHash(""),
        )
        ok, errs = validate_envelope_criterion(crit)
        assert not ok
        assert "threshold_digest_must_be_non_empty" in errs

    def test_rejects_bool_threshold(self) -> None:
        crit = EnvelopeCriterion(
            predicate=_length_le(4),
            threshold=True,  # type: ignore[arg-type]
            source_stats_hash=_digest("src"),
            threshold_digest=_digest("thr"),
        )
        ok, errs = validate_envelope_criterion(crit)
        assert not ok


class TestEnvelopeClassification:
    """The :class:`EnvelopeClassification` must be constructible
    with arbitrary observable names."""

    def test_classification_with_non_molecule_residuals(self) -> None:
        """The ``residual_extents`` mapping may use any key — including
        non-molecule names."""
        cls = EnvelopeClassification(
            bundle_id=BundleId("b1"),
            matched_layer_index=0,
            complement_blocker=None,
            within_layer_thresholds=True,
            residual_extents={
                "length_score": 0.1,
                "graph_density": 0.5,
                "spectral_gap": 0.05,
            },
        )
        ok, errs = validate_envelope_classification(cls)
        assert ok, errs

    def test_classification_with_molecule_residuals_works_too(self) -> None:
        """The ``residual_extents`` mapping may also use molecule
        channel names — the dataclass is domain-agnostic."""
        cls = EnvelopeClassification(
            bundle_id=BundleId("b1"),
            matched_layer_index=None,
            complement_blocker=ComplementBlockerCode("out_of_envelope"),
            within_layer_thresholds=False,
            residual_extents={
                "coordinate_extent_rms_max": 0.1,
                "atom_count_max": 0.5,
            },
        )
        ok, errs = validate_envelope_classification(cls)
        assert ok, errs

    def test_classification_with_missing_layer_index_works(self) -> None:
        """``matched_layer_index=None`` is a valid signal that the
        bundle passed every layer."""
        cls = EnvelopeClassification(
            bundle_id=BundleId("b1"),
            matched_layer_index=None,
            complement_blocker=None,
            within_layer_thresholds=True,
            residual_extents={"x": 0.1},
        )
        ok, errs = validate_envelope_classification(cls)
        assert ok

    def test_classification_rejects_empty_bundle_id(self) -> None:
        cls = EnvelopeClassification(
            bundle_id=BundleId(""),
            matched_layer_index=0,
            complement_blocker=None,
            within_layer_thresholds=True,
            residual_extents={},
        )
        ok, errs = validate_envelope_classification(cls)
        assert not ok
        assert "bundle_id_must_be_non_empty" in errs

    def test_classification_rejects_non_bool_within_layer(self) -> None:
        cls = EnvelopeClassification(
            bundle_id=BundleId("b1"),
            matched_layer_index=0,
            complement_blocker=None,
            within_layer_thresholds="yes",  # type: ignore[arg-type]
            residual_extents={},
        )
        ok, errs = validate_envelope_classification(cls)
        assert not ok
        assert "within_layer_thresholds_must_be_bool" in errs

    def test_classification_accepts_arbitrary_complement_blocker(self) -> None:
        """The ``complement_blocker`` is an opaque string. Any non-empty
        string is a valid code; the universal layer does not constrain
        it to a closed literal set (that constraint lives at the
        molecule / model-family layer)."""
        cls = EnvelopeClassification(
            bundle_id=BundleId("b1"),
            matched_layer_index=1,
            complement_blocker=ComplementBlockerCode("model_family_specific_code"),
            within_layer_thresholds=False,
            residual_extents={"x": 0.1},
        )
        ok, errs = validate_envelope_classification(cls)
        assert ok, errs
